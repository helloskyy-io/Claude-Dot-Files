"""The Tracked Items §8 amendment-surface census.

**The acceptance test is a stated METHOD plus a tail, never a target count.**
The first draft of this requirement made the test *"a run on main must find the
10 live surfaces"*, where 10 was the line count of a grep for one phrase. That
number is a silent filter wearing the costume of a measurement: it missed an
entire file whose title is *"Surfaced Standards Changes — for Operator
Ratification"* and which contains the grepped phrase zero times, it missed a
second heading family, and it counted the plan's own correction notes, which are
not surfaces at all. It both under- and over-counted.

So the census has three parts, and each is checkable:

1. **A stated detection predicate**, structural rather than phrase-matched,
   scanned repo-wide, with every exclusion **stated** rather than silent —
   conventional ones in :mod:`planning_ui.plan_extractor.contract`, a repository's
   own in its ``corpus.toml``.
2. **The known-hard cases named**, so a narrow detector cannot pass its own
   acceptance test. Those cases are one corpus's content, so they live with
   that corpus's tests rather than in this module.
3. **An unclassifiable tail, reported with a count.** A census with no tail is
   asserting it found everything, and the pre-migration measurement found 95
   prose mentions no pattern could classify.

**No target figure appears anywhere in this module, deliberately.** The count is
whatever the method yields on the day it runs, and it is expected to FALL as the
backfill proceeds — which is the behaviour a fixed number would hide.

Nothing here converts a surface. Reporting is the whole requirement; migration
is corpus work with its own reviewer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import corpus_io
from .contract import Contract
from .fences import advance_fence, fenced_mask
from .model import (
    AMENDMENT_SECOND_SURFACE,
    AMENDMENT_SURFACE_SPENT,
    AMENDMENT_UNCLASSIFIABLE,
    SECTION_AMENDMENTS,
    SECTION_UNPARSED,
    UNPARSED_LINE,
    Collector,
    Provenance,
)

#: Stated exclusions. Each is named, and none is a silent filter.
#:
HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<text>.+?)\s*$")

#: A standards-amendment surface: a heading (or an H1, which makes the whole
#: FILE the surface) naming standards together with an amendment, implication,
#: change, seam or ratification.
AMENDMENT_HEADING_RE = re.compile(
    r"standards?[\s\-–—]*(amendment|implication|change|seam)"
    r"|surfaced\s+for\s+ratification"
    r"|ratification\s+queue",
    re.IGNORECASE,
)

#: Amendment-SHAPED but not classifiable by the predicate above. These are the
#: tail: surfaced-for-review headings whose class this tool cannot rule on.
TAIL_HEADING_RE = re.compile(
    r"surfaced\s+candidates?"
    r"|candidates?\s+surfaced"
    r"|surfaced\s*[\(—-]"
    r"|open\s+(questions?|decisions?)\s+surfaced",
    re.IGNORECASE,
)

#: A recorded ratification state. A surface whose items ALL carry one is
#: history, not an accumulating store, and is reported separately.
RATIFIED_RE = re.compile(
    r"\bRATIFIED\b|\bratified\b|\bamended\b|\bREJECTED\b|☑|\[x\]\s*ratif",
)
PENDING_RE = re.compile(
    r"\bPENDING\b|\bpending\b|☐|\bawaiting\b|\bNOT applied\b|\bnot auto-applied\b"
    r"|\bnot yet ratified\b|\bfor (operator|human) review\b|\bratification queue\b",
    re.IGNORECASE,
)

#: A section carries amendment ITEMS when it has list entries or table rows.
ITEM_RE = re.compile(r"^\s*(?:[-*]\s+|\|\s*\S)")


@dataclass(frozen=True)
class AmendmentSurface:
    file: str
    line: int
    heading: str
    live: bool
    item_count: int
    whole_file: bool


def _excluded(rel: str, contract: Contract) -> bool:
    return contract.excluded_from_census(rel)


def _section_bounds(lines: list[str], start: int, level: int, fenced: list[bool]) -> int:
    """Index one past the last line of the section opened at ``start``.

    ``fenced`` is consulted for the same reason the caller consults it: a
    heading-shaped line inside a fenced block — a shell comment, or a quoted
    example of the very convention this census measures — is not a section
    boundary, and treating it as one truncates the body the classifier reads.
    """
    for index in range(start + 1, len(lines)):
        if fenced[index]:
            continue
        heading = HEADING_RE.match(lines[index])
        if heading and len(heading.group("hashes")) <= level:
            return index
    return len(lines)


def _classify_section(body: list[str]) -> tuple[bool, int]:
    """Return ``(live, item_count)`` for a candidate section.

    ``live`` means the surface still owes a ruling. A surface is SPENT only when
    it records a ratification state and carries no pending marker — the
    conservative direction, because misreading a live surface as history is the
    failure that lets an amendment stop existing.
    """
    text = "\n".join(body)
    item_count = sum(1 for line in body if ITEM_RE.match(line))
    has_ratified = bool(RATIFIED_RE.search(text))
    has_pending = bool(PENDING_RE.search(text))
    live = has_pending or not has_ratified
    return live, item_count


def _report_unterminated_fence(rel: str, lines: list[str], collector: Collector) -> None:
    """A file that ends inside a fence swallowed everything below the opener.

    **Fired on the LOSS, never on the condition.** An unterminated fence that
    hides nothing amendment-shaped is a markdown defect somebody else's linter
    owns; one that hides a heading this census exists to find is a surface that
    stops existing, silently — and silence is indistinguishable from a file that
    genuinely has no surface. Four files on the live corpus carry an
    unterminated fence and none of them swallows a heading, so this reports
    nothing today and fires the day one does.

    The other walkers that consult :func:`~.fences.fenced_mask` need no
    equivalent: ``parse_roadmap`` and ``_collect_phases`` read a ``roadmap.md``,
    and :func:`~.dependencies.parse_declarations` already reports the
    unterminated fence against that same file and line (verified against a
    corpus carrying one). :func:`~.derivations.anchor_resolves_in` fails the
    other way — a swallowed heading makes an anchor UNRESOLVED, which raises a
    finding rather than hiding one.
    """
    # The MASK cannot answer this: it marks a delimiter line True whether that
    # delimiter opens or closes, so a file whose last line is its closing fence
    # looks identical to one that never closed. Walk the delimiters instead —
    # through `advance_fence`, so this walk cannot drift length-blind while the
    # mask beside it is length-aware.
    open_delimiter: str | None = None
    opened = 0
    for index, line in enumerate(lines):
        was_open = open_delimiter is not None
        open_delimiter, _ = advance_fence(line, open_delimiter)
        if open_delimiter is not None and not was_open:
            opened = index
    if open_delimiter is None:
        return
    swallowed = [
        index
        for index in range(opened, len(lines))
        if (heading := HEADING_RE.match(lines[index]))
        and (
            AMENDMENT_HEADING_RE.search(heading.group("text"))
            or TAIL_HEADING_RE.search(heading.group("text"))
        )
    ]
    if not swallowed:
        return
    collector.add_finding(
        UNPARSED_LINE,
        SECTION_UNPARSED,
        f"`{rel}` opens a code fence that is never closed, so "
        f"{len(swallowed)} amendment-shaped heading(s) below it were not read",
        Provenance(rel, opened + 1),
        expected="every fenced block closed by a matching ``` or ~~~",
        detail=(
            "The census would report this file as carrying no amendment surface, "
            "which is indistinguishable from a file that genuinely carries none. "
            f"First swallowed heading: line {swallowed[0] + 1}."
        ),
    )


def census(
    root: Path, collector: Collector, contract: Contract | None = None
) -> list[AmendmentSurface]:
    """Scan the checkout and report every amendment surface outside the store.

    Reports; resolves nothing.

    ``contract`` defaults to the conventions alone — the right answer for a
    corpus that states no local shape, and for a scratch corpus in a test.
    """
    contract = contract or Contract()
    surfaces: list[AmendmentSurface] = []
    tail = 0

    for rel in corpus_io.iter_markdown(root, collector=collector):
        if _excluded(rel, contract):
            continue
        lines = corpus_io.read_lines(root, rel, collector)
        if lines is None:
            continue  # reported by read_lines as FILE_UNREADABLE

        # A fenced block that QUOTES an amendment heading is prose about the
        # convention, not a surface that accumulates — the same ruling that
        # masks a marker inside a fence. Without this, the
        # census reports a file for showing the reader what a surface looks
        # like, and `tracked_items_standard.md` is excluded by name only
        # because it does exactly that.
        fenced = fenced_mask(lines)
        _report_unterminated_fence(rel, lines, collector)
        for index, line in enumerate(lines):
            if fenced[index]:
                continue
            heading = HEADING_RE.match(line)
            if not heading:
                continue
            text = heading.group("text")
            level = len(heading.group("hashes"))
            end = _section_bounds(lines, index, level, fenced)
            # Blanked, not dropped: `_classify_section` counts bullet- and
            # table-shaped lines, and a surface that PROPOSES verbatim standard
            # text puts that text in a fence. A phase doc that quotes a
            # proposed standard section in a ````markdown block is the case —
            # its "items" are lines of the quotation, and counting them tells a reader the
            # surface owes seven rulings when it owes none of those seven.
            body = ["" if masked else line for line, masked in zip(lines[index + 1 : end], fenced[index + 1 : end])]

            if AMENDMENT_HEADING_RE.search(text):
                live, item_count = _classify_section(body)
                whole_file = level == 1
                surface = AmendmentSurface(
                    file=rel,
                    line=index + 1,
                    heading=text,
                    live=live,
                    item_count=item_count,
                    whole_file=whole_file,
                )
                surfaces.append(surface)
                _report(collector, surface)
                continue

            if TAIL_HEADING_RE.search(text):
                tail += 1
                collector.add_finding(
                    AMENDMENT_UNCLASSIFIABLE,
                    SECTION_AMENDMENTS,
                    f"amendment-shaped heading this predicate cannot rule on: {text}",
                    Provenance(rel, index + 1),
                    expected=(
                        "a standards-amendment surface naming its target and anchor, "
                        "per Tracked Items §4.1"
                    ),
                    detail="Reported as tail; a census with no tail asserts it found everything.",
                )

    collector.add_finding(
        AMENDMENT_UNCLASSIFIABLE,
        SECTION_AMENDMENTS,
        f"unclassifiable tail: {tail} amendment-shaped heading(s) the predicate could not rule on",
        Provenance("tracked/standards"),
        expected="a count, never a clean number with no tail",
        detail=(
            "The tail is mandatory. The pre-migration measurement found 21 findable "
            "surfaces across 8 heading wordings plus 95 unclassifiable prose mentions, "
            "exactly one of which recorded a ratification state."
        ),
    )
    return surfaces


def _report(collector: Collector, surface: AmendmentSurface) -> None:
    scope = "whole file" if surface.whole_file else "heading"
    if surface.live:
        collector.add_finding(
            AMENDMENT_SECOND_SURFACE,
            SECTION_AMENDMENTS,
            f"§8 second surface ({scope}) still owing a ruling: {surface.heading}",
            Provenance(surface.file, surface.line),
            expected="tracked/standards/ — the one surface for standards amendments",
            detail=(
                f"{surface.item_count} amendment-shaped item(s) in the section. "
                "Reported only; converting a surface is corpus work with a separate "
                "reviewer and is explicitly out of scope for this phase."
            ),
        )
        return
    collector.add_finding(
        AMENDMENT_SURFACE_SPENT,
        SECTION_AMENDMENTS,
        f"§8 second surface ({scope}) whose entries all record a ratification state: {surface.heading}",
        Provenance(surface.file, surface.line),
        expected="tracked/standards/ — the one surface for standards amendments",
        detail=(
            "History rather than an accumulating store. Reported separately from a "
            "surface that still owes a ruling, per requirement 7's live/spent split."
        ),
    )

"""Reproduce the five founding measurements in the planning_ui roadmap's finding.

**For the three re-measured rows, "reproduce" means reproduce the stated METHOD
and report the figure it yields** — not match a number recorded there. Where a
figure differs, the reason is stated in the report; the roadmap is never edited.

**The two `Depends on:` rows are fed by the Dependency Contract's accounting**,
not by a scan of this module's own. One question, one derivation.

**The broken-link row is reproduced as an aggregate COUNT under its stated
method and is never enumerated**, with fenced code blocks and inline code
spans masked — see
:func:`count_broken_relative_links` for why that mask is an extension of an
already-ruled principle rather than a widened predicate, and for the companion
PR that amends the recorded method text in lockstep. The count is cheap; the
enumeration is
`doc-manager`'s, and keeping it a count is what holds this requirement inside the
scope boundary — this component owns exactly one link class, a planning-graph
edge that resolves to no node.

**The same walk reports every host-absolute link, enumerated.** That is a
second link class this tool owns: a link that resolves on one host and nowhere
else, whose symptom is graph edges present at one checkout and absent from
every other. One walk feeds both — a second sweep with its own mask would be a
second answer to "which links did you read".
"""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import posixpath

from . import corpus_io
from .dependencies import Declaration
from .model import (
    LINK_HOST_ABSOLUTE,
    MEASUREMENT_DIFFERS,
    SECTION_HOST_ABSOLUTE,
    SECTION_MEASUREMENTS,
    SECTION_UNPARSED,
    UNPARSED_LINE,
    Collector,
    Measurement,
    Provenance,
)
from .fences import advance_fence
from .roadmaps import Component, mask_code_spans
from .contract import Contract, canonical_checkout_for
from .safe_paths import (
    PathEscape,
    exists_in_root,
    is_external,
    is_host_absolute,
    resolve_within_root,
    split_anchor,
)
from .sprints import LINK_RE, SprintsDocument

DEV_UI_ROADMAP = "development/common/planning_ui/roadmap.md"

#: Excluded from the broken-link sweep, exactly as the recorded method states.

def host_absolute_method(contract: Contract) -> str:
    """The method, stated on the report beside the count so the population is
    a method and never a target number. Built from the corpus's own
    declarations — its canonical host path and what it excludes as not-corpus
    — rather than typed, so the report never describes one repository's
    method over another repository's figures."""
    prefix = contract.canonical_checkout or "(this corpus declares no canonical host path)"
    excluded = ", ".join(f"`{x}`" for x in contract.not_corpus) or "nothing"
    return (
        "every markdown link under the checkout whose target starts with "
        f"`{prefix}`, the corpus's declared canonical host path — the same walk, "
        f"mask and exclusions as the broken-link row ({excluded} excluded as "
        "not-corpus, the generator's own output never walked; links inside fenced "
        "blocks or code spans masked). One finding per FILE naming every line, with "
        "the relative form its first link would take. Nothing is rewritten."
    )


class _Masked(NamedTuple):
    """The result of :func:`_mask_fences` — the text, and what it swallowed."""

    #: ``text`` with every fenced block blanked, LINE COUNT PRESERVED.
    text: str
    #: 1-based line of a fence that never closed, or ``None`` when balanced.
    unterminated_at: int | None
    #: The RAW lines below that unterminated fence. Empty when balanced. Carried
    #: so the caller can say how much it did not read rather than assert that
    #: nothing was there.
    swallowed: str


def _mask_fences(text: str) -> _Masked:
    """``text`` with every fenced block blanked, LINE COUNT PRESERVED.

    An unterminated fence masks everything below it, which is the safe
    direction here: the sweep under-counts rather than counting a placeholder.

    **But under-counting silently is the failure this package is built against,
    and this sweep cannot borrow anyone else's report.** The dependency
    contract emits :data:`~.model.UNPARSED_LINE` for an unterminated fence in a
    ``roadmap.md`` — and that is the only file it ever opens, while this sweep
    reads EVERY markdown file under the root, and an unterminated fence is far
    likelier in a phase doc than in a roadmap. So the swallowed region is
    returned rather than discarded, and :func:`count_broken_relative_links`
    reports what it contained.
    """
    out: list[str] = []
    swallowed: list[str] = []
    open_delimiter: str | None = None
    opened_at = 0
    for index, line in enumerate(text.splitlines()):
        was_open = open_delimiter is not None
        open_delimiter, is_delimiter = advance_fence(line, open_delimiter)
        if is_delimiter and not was_open:
            opened_at = index + 1
            swallowed = []
            out.append("")
            continue
        if is_delimiter or was_open:
            # A run that did not close the block is CONTENT — a nested inner
            # fence — so it belongs in what the block swallowed, not beside it.
            if not is_delimiter:
                swallowed.append(line)
            out.append("")
            continue
        out.append(line)
    if open_delimiter is None:
        return _Masked("\n".join(out), None, "")
    return _Masked("\n".join(out), opened_at, "\n".join(swallowed))


def count_broken_relative_links(
    root: Path, collector: Collector | None = None, contract: Contract | None = None
) -> tuple[int, int]:
    """``(unique (file, target) pairs, total occurrences)`` that resolve to nothing.

    The stated method: unique ``(file, target)`` pairs, the corpus's declared
    not-corpus directories excluded, **and links inside fenced code blocks or
    inline code spans excluded**. **Aggregate only — never enumerated.**

    **The fence mask is the same ruling the dependency contract applies**: a
    marker inside a fenced block is prose about the convention rather than a
    use of it, and a link inside one is a placeholder rather than a reference.
    A corpus's own Documentation Standard shows the cross-reference form —
    link text, then a relative path in parentheses — inside a fence; counted
    literally, **the corpus's documentation of the convention inflates the
    figure the convention is measured by.** Inline code spans are masked for
    the same reason — masking fences alone leaves the tool under-excluding
    against its own stated method, which is the divergence the mask exists to
    prevent, pointing the other way.
    """
    unique: set[tuple[str, str]] = set()
    occurrences = 0
    contract = contract or Contract()
    for rel in corpus_io.iter_markdown(
        root, exclude_prefixes=contract.not_corpus, collector=collector
    ):
        text = corpus_io.read_text(root, rel, collector)
        if text is None:
            continue  # reported by read_text as FILE_UNREADABLE
        masked = _mask_fences(text)
        scan = _scan_links(root, rel, masked.text)
        for target in scan.broken:
            unique.add((rel, target))
            occurrences += 1
        if collector is not None:
            _report_host_absolute(root, rel, scan.host_absolute, collector)
        if masked.unterminated_at is None or collector is None:
            continue
        # An unterminated fence swallowed the rest of this file. Say what was in
        # there rather than leaving the row quietly short — the mask under-counts
        # by design, and a design that under-counts without saying so is the
        # "quietly widened its own predicate" defect wearing the other sign.
        missed = _scan_links(root, rel, masked.swallowed).broken
        if not missed:
            continue
        collector.add_finding(
            UNPARSED_LINE,
            SECTION_UNPARSED,
            f"`{rel}` opens a code fence that is never closed, so "
            f"{len(missed)} link(s) below it that resolve to nothing were not "
            "counted into the broken-link row",
            Provenance(rel, masked.unterminated_at),
            expected="every fenced block closed by a matching ``` or ~~~",
            detail=(
                "The mask cannot tell a placeholder from a reference below an "
                "unterminated fence, so it excludes both and reports the "
                "exclusion. Close the fence and the links rejoin the row."
            ),
        )
    return len(unique), occurrences


def _mask_spans(text: str) -> str:
    """``text`` with inline code spans blanked, LINE BY LINE.

    Per line, deliberately, and at the scope :mod:`~.roadmaps` already masks
    them at: :data:`~.roadmaps.CODE_SPAN_RE` is ``DOTALL``, so run over a whole
    document a single stray backtick pairs with the next one several pages away
    and blanks everything between. That is the silent-drop shape, arrived at
    while removing one.
    """
    return "\n".join(mask_code_spans(line) for line in text.split("\n"))


class _LinkScan(NamedTuple):
    """What one file's links yielded — two classes, one read."""

    #: Every relative link target that resolves to nothing, in document order.
    broken: list[str]
    #: ``(1-based line, target)`` for every link written against the canonical
    #: checkout's host path — the class that resolves on one host only.
    host_absolute: list[tuple[int, str]]


def _scan_links(root: Path, rel: str, text: str) -> _LinkScan:
    """Classify every link in ``text``: broken, host-absolute, or neither.

    Masks inline code spans, so the caller only has to hand it fence-masked
    text. Split out so the swallowed region below an unterminated fence is
    judged by exactly the predicate the row itself uses — a second, looser test
    there would report a "missed link" the row would never have counted anyway.

    Walks line by line because the host-absolute finding names a line; the
    fence mask preserves line count, so the index here is the file's own.
    """
    broken: list[str] = []
    host_absolute: list[tuple[int, str]] = []
    for index, line in enumerate(_mask_spans(text).split("\n")):
        for match in LINK_RE.finditer(line):
            target = match.group("target")
            if is_external(target):
                continue
            path_part, _anchor = split_anchor(target)
            if not path_part:
                continue
            if is_host_absolute(path_part, root):
                host_absolute.append((index + 1, target))
            try:
                resolved = resolve_within_root(root, rel, path_part)
            except PathEscape:
                broken.append(target)
                continue
            if exists_in_root(root, resolved):
                continue
            broken.append(target)
    return _LinkScan(broken, host_absolute)


def _report_host_absolute(
    root: Path, rel: str, links: list[tuple[int, str]], collector: Collector
) -> None:
    """One finding per FILE, naming every line, carrying the relative form to write.

    Per file rather than per link, and the reason is a ceiling rather than
    taste: enumerated per link, the 1,739 links measured on 2026-09-12 put the
    consistency report at 617 KiB, past the size at which GitHub stops
    rendering a markdown file — and a committed page nobody can read on the
    pull request fails the reason it is committed. Every line is still named,
    so nothing is dropped; the owner's unit of work is the file anyway.

    The remedy is computed and stated, never applied: this component is
    read-only outside its own folder, and the owner of the file rewrites it.
    """
    if not links:
        return
    first_line, first_target = links[0]
    path_part, anchor = split_anchor(first_target)
    # The resolver strips the prefix; the relative form is what a markdown
    # renderer would need from the source file's directory.
    repo_rel = posixpath.normpath(path_part[len(canonical_checkout_for(root)) :].lstrip("/") or ".")
    relative = posixpath.relpath(repo_rel, posixpath.dirname(rel) or ".")
    if anchor:
        relative = f"{relative}#{anchor}"
    lines = ", ".join(f"L{line}" for line, _target in links)
    collector.add_finding(
        LINK_HOST_ABSOLUTE,
        SECTION_HOST_ABSOLUTE,
        f"{len(links)} link(s) written as host-absolute paths, at {lines}",
        Provenance(rel, first_line),
        expected=(
            f"links relative to this file — L{first_line}'s `{first_target}` "
            f"would be `{relative}`"
        ),
        detail=(
            "Each resolves only on a host whose checkout sits at the canonical "
            "path. The graph reads through the prefix, so no edge is lost; the "
            "links themselves are the owner's to rewrite."
        ),
    )


def measure(
    root: Path,
    components: list[Component],
    sprints: SprintsDocument,
    shape_misses: int,
    derived_orphans: set[str],
    declared_orphans: set[str],
    declarations: list[Declaration],
    collector: Collector,
    contract: Contract | None = None,
) -> list[Measurement]:
    """The corpus's five structural figures, each under a stated method.

    Stated as method-plus-figure and never as a target: the population is the
    corpus's, it should move as the corpus is fixed, and a fixed number would
    hide that.

    The two `Depends on:` rows are derived from the DEPENDENCY CONTRACT's own
    parse rather than from a private re-scan. They were a second scan with a
    second definition — a contested row measured twice, in one process, by two
    pieces of code that could disagree.

    **Both rows count CONFORMING declarations only**, because that is what their
    stated method says: a roadmap.md carrying `**Depends on:**` at the start of
    a line. The parser deliberately reads more than that — a second spelling and
    a mid-paragraph marker — and those are reported as non-conforming rather
    than folded into a row whose method excludes them. A measurement that
    quietly widened its own predicate would be the defect these rows exist to
    catch.
    """
    total_roadmaps = len(components)
    conforming = [d for d in declarations if d.conforming]
    carrying = len({d.component for d in conforming})
    # The row's STATED method counts a link to a phase or a component node —
    # the 2026-08-27 definition. The graph has since admitted `standard` and
    # `artifact` nodes as targets (rule 9), and a declaration resolving only
    # through one is LINE_RESOLVES; counting it here would widen this row's
    # predicate under the same name, which is the defect these rows exist to
    # catch. So the row asks the node set directly, by the kinds its method
    # names.
    node_ids = collector.node_ids()
    resolvable = len(
        {
            d.component
            for d in conforming
            if any(
                link.node_id in node_ids
                and link.node_id.split(":", 1)[0] in ("phase", "component")
                for link in d.graph_links()
            )
        }
    )
    contract = contract or Contract()
    unique_pairs, occurrences = count_broken_relative_links(root, collector, contract)

    excluded = ", ".join(f"`{x}`" for x in contract.not_corpus) or "nothing"
    rows = [
        Measurement(
            name="Sprint work items failing the §6 item shape",
            method=(
                "count items failing §6 (no `L<n>`, `cross-cutting` in its place, or "
                "`NEEDS PLANNING` with no link), excluding the recurring close-out gate "
                "and § Sprint: Unplaced. The denominator is stated three ways because "
                "the file states none: "
                f"{sprints.total_checkbox_lines} checkbox lines, "
                f"{sprints.outside_unplaced} outside § Sprint: Unplaced, "
                f"{sprints.work_items} work items."
            ),
            derived=f"{shape_misses} misses",
        ),
        Measurement(
            name="Component roadmaps carrying a `Depends on:` line",
            method=(
                "a roadmap.md carrying `**Depends on:**` at the START of a line — rule 9's "
                "marker. A mid-line occurrence is prose about dependencies, not a "
                "declaration, and is reported in its own section."
            ),
            derived=f"{carrying} of {total_roadmaps}",
        ),
        Measurement(
            name="…of those, expressing a dependency as a resolvable link",
            method=(
                "a roadmap carrying at least one `**Depends on:**` line whose links "
                "resolve to a phase document or a component roadmap. A standard as a "
                "target (rule 9, satisfied by resolving) is deliberately not counted "
                "here, so the row measures dependencies on planned work."
            ),
            derived=f"{resolvable} of {total_roadmaps}",
        ),
        Measurement(
            name="Components with a roadmap that no sprint item links to",
            method=(
                "derived by link-path against the sprint body excluding § Sprint: "
                "Unplaced, with retired components and the section's stated "
                "exclusions suppressed. Each disagreement with the hand-maintained "
                "Unplaced list, in either direction, is a finding in its own section."
            ),
            derived=(
                f"{len(derived_orphans)} derived against the "
                f"{len(declared_orphans)} the hand-maintained list names"
            ),
        ),
        Measurement(
            name="Relative markdown links in the repo that resolve to nothing",
            method=(
                f"unique `(file, target)` pairs, {excluded} excluded as not-corpus, and "
                "**links inside fenced code blocks or inline code spans excluded** — "
                "such a link is a placeholder, not a reference. "
                "AGGREGATE ONLY — never enumerated: this tool owns exactly one link "
                "class, a planning-graph edge that resolves to no node, and the rest "
                "is doc hygiene. A host-absolute link is read off its text, so the "
                "figure derives the same from any checkout path; those links have "
                "their own section."
            ),
            derived=f"{unique_pairs} unique pairs across {occurrences} occurrences",
        ),
    ]

    for row in rows:
        if row.agrees:
            continue
        collector.add_finding(
            MEASUREMENT_DIFFERS,
            SECTION_MEASUREMENTS,
            f"{row.name}: derived {row.derived}, roadmap records {row.recorded}",
            Provenance(DEV_UI_ROADMAP),
            expected=row.method,
            detail=(
                row.note
                + " The roadmap is not edited: where a figure differs, the reason is "
                "stated here."
            ).strip(),
        )
    return rows

"""Parser for ``development/**/roadmap.md`` — one component per file.

Irregularities a corpus may carry, each handled explicitly:

* not every roadmap carries a ``**Status:**`` line;
* a retired component — declared by its ``**Lifecycle:**`` line, or by the
  legacy marker this reader still honours and reports — is suppressed from
  orphan findings **on the strength of that line**, never on the strength of
  its name;
* a nested ``roadmap.md`` under a retired component is admitted by the same
  classifier and may carry no status line at all, so the suppression cannot
  reach it. A component admitted with no status is its own finding.

Hour attribution states its method rather than inheriting one: a heading section
containing **exactly one** OWNED phase entry and at least one ``~Nh`` figure
attributes that figure to that phase. A section with two entries and one
figure is ambiguous and is counted, not guessed at; so is a figure beside a
link to another component's phase, which is not this roadmap's estimate to
make.

**This module owns the lexical shape of a roadmap line**, because SEVERAL
walkers read the same file for different things and a line each of them reads
differently is a line they disagree about. The inline code-span mask and the
``**Depends on:**`` marker therefore live here, and :mod:`~.dependencies`
imports them the same direction ``HEADING_RE`` and :func:`is_phase_link`
already travel.

**The fence delimiter does NOT live here**, and that is a correction rather
than an omission. It did, and :mod:`~.sprints` and :mod:`~.discovery` are both
imported BY this module, so neither could ask it. ``sprints`` spelled its own
``startswith`` toggle — length-blind like the four around :data:`FENCE_RE`,
which reads as agreement and is not — and ``discovery`` walked no fence at all,
reading a fenced ``## Requirements for completion`` as a real one. It now lives
in :mod:`~.fences`, a leaf that imports nothing from this package, so every
walk in it asks one answer. See that module for why the answer is length-aware.

**Four walkers read a ``roadmap.md``, not two**, and the count is written out
because a guard applied to "both" of them reached one:
:func:`parse_roadmap`'s status/label loop, :func:`_collect_phases`,
:func:`declaration_blocks` (called by :func:`~.dependencies.parse_declarations`)
and :func:`~.dependencies._attribute_sources`. Three of the four ask
:func:`~.fences.fenced_mask`; ``declaration_blocks`` keeps its own walk because
it REPORTS what an unterminated fence swallowed and a boolean mask cannot carry
that. It compiles no second delimiter and spells no second toggle: it advances
through :func:`~.fences.advance_fence`, so the single answer holds even where
the loop is not shared. The declaration-reading pair then partitions every
declaration line at ONE column: the dependency contract reads the marker
onward, this module reads what sits in front of it. Nothing is read twice and
nothing is dropped.

**The `**Implementation:**` line is read ONCE, here.** :func:`_collect_phases`
turns it into an owned :class:`PhaseRef` carrying its heading-section ordinal,
and the dependency contract binds a declaration to the entry above it through
that ordinal rather than re-reading the line. ``_attribute_sources`` used to
read it a second time, which made its idea of which section owns which phase a
separate answer from this module's.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path

from .model import (
    PATH_ESCAPES_ROOT,
    COMPONENT_NO_STATUS,
    HOURS_UNATTRIBUTED,
    PHASE_ANCHOR_MISSING,
    PHASE_CLAIMED_TWICE,
    SECTION_DEPENDS_GRAPH,
    SECTION_DERIVED,
    SECTION_UNCLASSIFIED,
    SECTION_UNPARSED,
    STATUS_COMPLETE,
    STATUS_DEPRECATED,
    STATUS_IN_PROGRESS,
    STATUS_NOT_SCHEDULED,
    STATUS_PLANNED,
    STATUS_UNCHECKED,
    Collector,
    Provenance,
)
from . import corpus_io
from .discovery import PHASE_FILENAME_RE
from .fences import advance_fence, fenced_mask
from .safe_paths import PathEscape, is_external, resolve_within_root, split_anchor
from .sprints import HOURS_RE, LINK_RE

STATUS_RE = re.compile(r"^\s*\*\*Status:\*\*\s*(?P<text>.+?)\s*$")
HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<text>.+?)\s*$")
#: `**Lifecycle:** retired <YYYY-MM-DD> — <why, and what the documents are
#: kept for>`, or `active`, or absent, which means active.
#:
#: **Whether a component is still worked is a DIFFERENT AXIS from its status**,
#: and it is DECLARED rather than derived. A status marker is derived from
#: checkboxes and stays derived; an abandoned experiment keeps whatever marker
#: its boxes give it. Retiring is an operator ruling, so nothing here writes
#: this line — it is only read.
COMPONENT_LEGACY_LIFECYCLE = "COMPONENT_LEGACY_LIFECYCLE"

LIFECYCLE_RE = re.compile(r"^\s*\*\*Lifecycle:\*\*\s*(?P<state>active|retired)\b(?P<rest>.*)$", re.I)

#: The marker that predates the lifecycle line. The standard defines FOUR
#: status markers and says there is no fifth, so a reader that silently
#: honoured this one was admitting a state from code. It is still recognised —
#: dropping it would strip a component of the suppression its roadmap relies
#: on — but it is now REPORTED, so the corpus converts rather than the
#: divergence persisting invisibly.
LEGACY_RETIRED_RE = re.compile(r"⚫|\bRETIRED\b")

#: An inline code span. Masked before the marker search for the same reason:
#: a roadmap may contain the sentence *"a `**Depends on:**` line under each
#: phase entry"*, which is prose ABOUT the marker, not a use of it.
#: Longest-delimiter-first, so ``` ``**Depends on:**`` ``` masks the whole span
#: rather than matching an empty one between the leading pair.
CODE_SPAN_RE = re.compile(r"(?P<t>`{1,3})(?:(?!(?P=t)).)*(?P=t)", re.DOTALL)

#: The two spellings a corpus uses, found ANYWHERE on a line that is not code.
#:
#: **The ruled format says line-initial ``**Depends on:**``, and a corpus that
#: does not obey it is read as written and REPORTED for the deviation** —
#: :func:`~.dependencies._report_non_conforming` emits the count. A
#: line-anchored, single-spelling parser silently drops every declaration in
#: the other spelling or mid-paragraph, and then puts their owners on the "go
#: author a dependency" worklist for dependencies they have already written.
#: **A rule its exemplars fail is a wrong rule**; the conformance question is
#: answered by a finding, not by refusing to read.
MARKER_RE = re.compile(r"\*\*(?P<marker>Depends on|Dependencies):\*\*")

#: A list item. A list beneath an EMPTY marker line is that declaration's
#: continuation — both walkers must agree on where the declaration ends.
LIST_ITEM_RE = re.compile(r"^\s*[-*]\s+\S")

#: The line a roadmap uses to say "this heading section IS that phase" —
#: rule 8's second line. Read HERE, once, and consumed by the dependency
#: contract through :attr:`PhaseRef.section`; it used to be read a second time
#: in :mod:`~.dependencies`, which made that module's idea of which section
#: owns which phase a separate answer from this one's.
IMPLEMENTATION_RE = re.compile(r"^\s*\*\*Implementation:\*\*")

#: Rule 8's four status markers, exactly as `sprints.md` § Status markers spells
#: them. **A bare `✅` is not one of them** and derives NO status: the standard
#: names four markers and a fifth reading would be a guess that renders as a
#: colour. Where a heading carries none, the phase's status is empty and any
#: edge onto it is UNDERIVABLE rather than silently unsatisfied.
STATUS_MARKER_RE = re.compile(
    r"(?P<marker>✅\s*COMPLETE|🟡\s*IN PROGRESS|🟠\s*PLANNED|🔵\s*NOT SCHEDULED)"
)
_STATUS_BY_EMOJI = {
    "✅": STATUS_COMPLETE,
    "🟡": STATUS_IN_PROGRESS,
    "🟠": STATUS_PLANNED,
    "🔵": STATUS_NOT_SCHEDULED,
}
#: Rule 5's `DEPRECATED` PREFIX — anchored, because a heading that merely
#: mentions the word (*"Retire the DEPRECATED resolver 🟠 PLANNED"*) is a live
#: phase, not a deprecated one.
DEPRECATED_RE = re.compile(r"^\s*DEPRECATED\b")

#: An explicit anchor id, rule 9's *"written by the author rather than derived
#: from the words"*. Accepted on the heading line itself (the shape rule 9
#: illustrates) and on the line immediately before it (the shape this
#: component's own roadmap already uses). A slug generated from the heading is
#: deliberately NOT an anchor: it changes when the heading is reworded and
#: every inbound link then dies silently.
ANCHOR_ID_RE = re.compile(r'<a\s+id="(?P<id>[^"]+)"\s*>\s*</a>')

#: The legacy checkbox-list entry rule 8 supersedes and REQUIRES tooling to keep
#: reading until the corpus finishes converting: `- [x] **Name** ([phaseN_x.md]
#: (./phaseN_x.md)) — prose`. `[~]` is rule 5's deprecated equivalent.
#: **Top-level only**: an INDENTED checkbox is a sub-item of the entry above
#: it, and one that cites a phase document is a reference to that phase, not
#: a second entry for it. Measured live: `service/github-automation:142`, a
#: sub-item citing `phase2…#d1`, was read as phase 2's entry and the real
#: entry two lines below it was silently deduplicated away.
ENTRY_CHECKBOX_RE = re.compile(r"^- \[(?P<mark>[ xX~])\]\s+(?P<body>.*)$")
_STATUS_BY_MARK = {" ": STATUS_UNCHECKED, "x": STATUS_COMPLETE, "X": STATUS_COMPLETE, "~": STATUS_DEPRECATED}

#: Entry shapes, named so a consumer can say which one it read.
SHAPE_IMPLEMENTATION = "implementation"
SHAPE_INLINE = "inline"
SHAPE_CHECKBOX = "checkbox"


@dataclass(frozen=True)
class DeclarationBlock:
    """One ``**Depends on:**`` marker and the lines that belong to it.

    ``index`` is the 0-based marker line; ``lines`` is that index plus, for an
    EMPTY line-initial marker, the list items beneath it; ``match`` is the
    marker match on the first line.
    """

    index: int
    match: re.Match[str]
    lines: tuple[int, ...]


def declaration_blocks(lines: list[str]) -> tuple[list[DeclarationBlock], int]:
    """Every declaration block in ``lines``, plus the unterminated-fence line.

    **One walk, two readers.** The dependency contract reads a roadmap's
    blocks into declarations; the phase-document reader reads a phase doc's
    blocks into one-carrier findings. A second copy of the extent rule — the
    marker onward, plus a list beneath an EMPTY marker line, never a list
    beneath a marker that already carries text — is a second answer to *where
    does a declaration end*, and the two would drift.

    The walk keeps its own fence state rather than asking
    :func:`~.fences.fenced_mask` because it REPORTS what an unterminated fence
    swallowed: the second value is the 1-based line an unclosed fence opened
    at, or ``0`` when every fence closed. It advances through
    :func:`~.fences.advance_fence`, so it compiles no second delimiter.
    """
    blocks: list[DeclarationBlock] = []
    index = 0
    open_delimiter: str | None = None
    fence_opened_at = 0
    while index < len(lines):
        line = lines[index]
        was_open = open_delimiter is not None
        open_delimiter, is_delimiter = advance_fence(line, open_delimiter)
        if is_delimiter or was_open:
            if open_delimiter is not None and not was_open:
                fence_opened_at = index + 1
            index += 1
            continue
        match = dependency_marker(line)
        if not match:
            index += 1
            continue
        rest = line[match.end() :].strip()
        line_initial = not line[: match.start()].strip()
        block = [index]
        if line_initial and not rest:
            # Only an EMPTY marker line takes the list beneath it. Grabbing a
            # list that follows a marker line which already carries text would
            # author edges nobody declared.
            probe = index + 1
            while probe < len(lines) and LIST_ITEM_RE.match(lines[probe]):
                block.append(probe)
                probe += 1
        blocks.append(DeclarationBlock(index=index, match=match, lines=tuple(block)))
        index = block[-1] + 1
    return blocks, (fence_opened_at if open_delimiter is not None else 0)


def mask_code_spans(line: str) -> str:
    """``line`` with code spans blanked, LENGTH PRESERVED.

    Length preservation is load-bearing: the marker's column in the masked line
    is used to slice the ORIGINAL line, so the declaration keeps its real text
    and the phase walker keeps the text in front of it.
    """
    return CODE_SPAN_RE.sub(lambda m: " " * len(m.group()), line)


def dependency_marker(line: str) -> re.Match[str] | None:
    """The ``**Depends on:**`` / ``**Dependencies:**`` marker on ``line``, if any.

    **One predicate, two readers.** :mod:`~.dependencies` asks it to find the
    declaration it parses; this module asks it to find the text it must NOT read
    as its own phase entries. A second copy would be a second answer, and the
    two walkers disagreeing about which lines are declarations is precisely the
    defect this predicate was extracted to close.
    """
    return MARKER_RE.search(mask_code_spans(line))


@dataclass
class PhaseRef:
    """A phase a roadmap OWNS (a phase entry) or merely REFERENCES (any other link).

    ``path`` is the repo-relative phase document, or ``""`` for a phase that
    lives inline in the roadmap — rule 8's *"small phase whose checkboxes live
    in the roadmap entry itself"* — whose identity is then its explicit anchor.
    """

    path: str
    line: int
    hours_low: int | None = None
    hours_high: int | None = None
    #: Which entry shape claimed it — one of the ``SHAPE_*`` names — or ``""``
    #: for a reference that is not an entry at all.
    shape: str = ""
    name: str = ""
    #: A ``STATUS_*`` value derived from the ENTRY — rule 8's heading marker or
    #: the legacy checkbox mark. ``""`` when the entry carries none, and that
    #: emptiness is load-bearing: it is what makes an edge onto this phase
    #: UNDERIVABLE rather than quietly unsatisfied. Never read from the phase
    #: document's own `**Status:**` line — the roadmap is the one carrier.
    status: str = ""
    #: The explicit anchor id the entry carries, if any.
    anchor: str = ""
    #: The heading-section ordinal the entry sits in, counted the way every
    #: walker in this package counts sections (unfenced ``HEADING_RE``), so the
    #: dependency contract binds a declaration to the entry above it without
    #: re-reading the `**Implementation:**` line.
    section: int = 0
    #: The roadmap the entry was read from — the inline node id needs it.
    roadmap: str = ""

    @property
    def inline(self) -> bool:
        return not self.path

    @property
    def node_id(self) -> str:
        """The graph node this phase is.

        A document is keyed on its path. An inline phase is keyed on its
        explicit anchor — the identity rule 9 protects. One with NO anchor is
        keyed on its line, a form no link can ever produce: it is in the graph
        (nothing is dropped) and un-targetable by construction, which is the
        truth about it until its owner writes the id.
        """
        if self.path:
            return f"phase:{self.path}"
        if self.anchor:
            return f"phase:{self.roadmap}#{self.anchor}"
        return f"phase:{self.roadmap}@L{self.line}"


@dataclass
class Component:
    """One component, identified by the directory its ``roadmap.md`` sits in.

    **Two phase sets, because one field was answering two questions.** ``owned``
    is what the roadmap's PHASE ENTRIES claim — the set a status is read off.
    ``referenced`` is every other phase-document link in the file, foreign or
    own — the set the coordination-document exception is built on, since that
    shape is *defined* by linking phases it does not own. Both are derived from
    the same walk and neither is authored anywhere a human edits.
    """

    path: str  # repo-relative directory, e.g. development/common/planning_ui
    roadmap: str  # repo-relative roadmap.md
    label: str
    status_text: str | None
    status_line: int
    retired: bool
    owned: list[PhaseRef] = field(default_factory=list)
    referenced: list[PhaseRef] = field(default_factory=list)
    #: Conforming phase documents in the component's OWN directory — discovery's
    #: `PHASE_DOC` class, set by the extractor after the walk. What ownership is
    #: measured against, and the second half of the coordination-document test:
    #: a component with documents of its own is never one, whatever its entries
    #: say, because the alternative is the hiding direction.
    on_disk: set[str] = field(default_factory=set)
    #: Explicit anchor id → phase node id, for every entry carrying one. An
    #: anchor on an entry WITH a phase document resolves to that document's
    #: node — the anchor names the entry and the entry IS the phase.
    anchors: dict[str, str] = field(default_factory=dict)
    #: Hour figures the stated method could not attribute to a single phase.
    #: Each is ALSO a named finding with its own file and line — this counter is
    #: the aggregate, not the record. It used to be the only trace, and it was
    #: read by nothing: a figure the tool saw and could not place then vanished
    #: from a report whose entire job is to be a worklist.
    unattributed_hours: int = 0

    @property
    def node_id(self) -> str:
        return f"component:{self.path}"

    def owns(self, path: str) -> bool:
        return path.startswith(self.path + "/")


def is_phase_link(rel: str) -> bool:
    """Whether a resolved path names a phase document.

    **Public because a second module consumes it.** The Dependency Contract
    attributes a `**Depends on:**` declaration to the phase entry it sits
    beneath, which means answering the same question this module asks — and a
    second copy of the predicate is a second answer waiting to drift.
    """
    name = rel.rsplit("/", 1)[-1]
    return bool(PHASE_FILENAME_RE.match(name)) or name.startswith("genesis-")


def parse_roadmap(root: Path, rel: str, collector: Collector) -> Component | None:
    """Parse one ``roadmap.md`` into a :class:`Component`.

    ``None`` when the file could not be read — reported by
    :func:`corpus_io.read_text`, never a crash and never an empty component
    silently standing in for a real one.
    """
    text = corpus_io.read_text(root, rel, collector)
    if text is None:
        return None
    lines = text.splitlines()
    directory = rel.rsplit("/", 1)[0]

    label = directory.rsplit("/", 1)[-1]
    status_text: str | None = None
    status_line = 0
    lifecycle_state: str | None = None

    # A fenced block is an ILLUSTRATION of a roadmap, not one. A roadmap that
    # shows `**Status:** ⚫ RETIRED` in a fence — the shape this component's
    # own documents use to describe the format — would otherwise be read as
    # retired, and a retired component is suppressed from the report entirely.
    # That is the same hiding direction, in the same file, as the exception the
    # phase-collection walker below was fixed for.
    fenced = fenced_mask(lines)
    for index, line in enumerate(lines):
        if fenced[index]:
            continue
        heading = HEADING_RE.match(line)
        if heading and heading.group("hashes") == "#" and label == directory.rsplit("/", 1)[-1]:
            label = heading.group("text").strip()
        status = STATUS_RE.match(line)
        if status and status_text is None:
            status_text = status.group("text")
            status_line = index + 1
        lifecycle = LIFECYCLE_RE.match(line)
        if lifecycle and lifecycle_state is None:
            lifecycle_state = lifecycle.group("state").lower()

    component = Component(
        path=directory,
        roadmap=rel,
        label=label,
        status_text=status_text,
        status_line=status_line,
        retired=lifecycle_state == "retired",
    )

    # A roadmap still declaring retirement through the old marker keeps its
    # suppression — stripping it would flood the report with findings its
    # roadmap explains why it does not want — but the divergence is NAMED.
    if lifecycle_state is None and status_text and LEGACY_RETIRED_RE.search(status_text):
        component = replace(component, retired=True)
        collector.add_finding(
            COMPONENT_LEGACY_LIFECYCLE,
            SECTION_UNCLASSIFIED,
            "declares retirement in its status marker, which the four-marker set "
            "does not define; retirement is a `**Lifecycle:**` line",
            Provenance(rel, status_line),
            expected="`**Lifecycle:** retired <YYYY-MM-DD> — <why the documents are kept>`",
        )

    if status_text is None:
        collector.add_finding(
            COMPONENT_NO_STATUS,
            SECTION_UNCLASSIFIED,
            "component admitted by the roadmap classifier carries no `**Status:**` line, "
            "so no status-based suppression can reach it",
            Provenance(rel),
            expected="`**Status:** …` near the top of the roadmap",
        )

    _collect_phases(root, rel, lines, fenced, component, collector)
    return component


@dataclass
class _Section:
    """One heading section's phase-relevant content, decided at flush."""

    ordinal: int
    line: int = 0
    text: str = ""
    anchor: str = ""
    status: str = ""
    has_marker: bool = False
    #: Phase links on `**Implementation:**` lines — (path, line).
    implementation: list[tuple[str, int]] = field(default_factory=list)
    #: Legacy checkbox entries — (path, line, mark, name, strong). ``strong``
    #: is whether the link sits IN the entry's bold run or immediately after
    #: it — the legacy shape — rather than deep in the bullet's prose, where a
    #: link is more often a citation of another phase than this entry's own.
    checkboxes: list[tuple[str, int, str, str, bool]] = field(default_factory=list)
    #: Every other phase link — (path, line).
    other: list[tuple[str, int]] = field(default_factory=list)
    hours: list[tuple[int, int | None, int]] = field(default_factory=list)


def _status_of(text: str) -> str:
    """The rule-8 status a heading's text carries, or ``""``.

    Several distinct markers on one heading — *"🟠 PLANNED (one half) ·
    🔵 NOT SCHEDULED (the other)"* is a shape a corpus uses — are joined
    rather than reduced: the value is then not equal to any single marker, and
    in particular not to ``COMPLETE``, which is the only comparison satisfaction
    makes. Nothing is guessed about which half a reader meant.
    """
    if DEPRECATED_RE.search(text):
        return STATUS_DEPRECATED
    seen: list[str] = []
    for match in STATUS_MARKER_RE.finditer(text):
        status = _STATUS_BY_EMOJI[match.group("marker")[0]]
        if status not in seen:
            seen.append(status)
    return " · ".join(seen)


#: The bold run a legacy checkbox entry opens with — `- [x] **Name** (…)` or
#: `- [x] **Phase 0 — [Name](file)**`. The entry's name is that run with any
#: link markup reduced to its text; where there is none, the link text.
_BOLD_RUN_RE = re.compile(r"^\s*\*\*(?P<name>.+?)\*\*")


def _link_name(text: str) -> str:
    return text.strip().strip("`*").strip()


def _entry_title(heading_text: str) -> str:
    """The NAME a rule-8 heading carries: its text before the status marker.

    Rule 8's shape is `### Name MARKER`, so the name is everything in front of
    the first marker, with any explicit anchor tag removed. It used to be the
    raw heading text, which put `🟠 PLANNED` into every inline node's label and
    into the "entry for `…`" clause of the one-carrier finding.
    """
    text = ANCHOR_ID_RE.sub("", heading_text)
    marker = STATUS_MARKER_RE.search(text)
    if marker:
        text = text[: marker.start()]
    return text.strip().rstrip("—-·:").strip()


def _entry_name(body: str, link_text: str) -> str:
    bold = _BOLD_RUN_RE.match(body)
    if bold is None:
        return _link_name(link_text)
    return LINK_RE.sub(lambda m: m.group("text"), bold.group("name")).strip().strip("`").strip()


#: What may sit between a legacy entry's bold run and its document link for
#: the link to be the ENTRY's: whitespace and an opening paren — the bold
#: name, then the document link in parentheses. Anything more is prose, and a
#: link in prose is a weak claim.
_ADJACENT_RE = re.compile(r"\s*\(?\s*")


def _claim_is_strong(body: str, link_start: int) -> bool:
    """Whether a checkbox line's phase link is where the legacy shape puts it.

    Strong: inside the bold run, or adjacent to it. Weak: deep in the prose,
    where three live roadmaps DO put their genuine entry link (`common/api:33`)
    but where an entry's bullet also cites OTHER phases (`common/temporal:30`
    cites phase 7 from the Harbor entry). A weak claim yields to a strong one
    on the same document whatever their order, so the citation never steals
    the entry.
    """
    bold = _BOLD_RUN_RE.match(body)
    if bold is None:
        return _ADJACENT_RE.fullmatch(body[:link_start]) is not None
    if link_start < bold.end():
        return True
    return _ADJACENT_RE.fullmatch(body[bold.end() : link_start]) is not None


def _heading_entry(section: _Section, rel: str, path: str, line_no: int, shape: str) -> PhaseRef:
    """One construction site for the two heading-keyed shapes, so the name,
    marker and anchor are read the same way whichever fired."""
    return PhaseRef(
        path=path,
        line=line_no,
        shape=shape,
        name=_entry_title(section.text),
        status=section.status,
        anchor=section.anchor,
        section=section.ordinal,
        roadmap=rel,
    )


def _collect_phases(
    root: Path,
    rel: str,
    lines: list[str],
    fenced: list[bool],
    component: Component,
    collector: Collector,
) -> None:
    """Walk heading sections; split phase links into OWNED and REFERENCED.

    **Ownership is read from a phase ENTRY, in every shape the corpus uses,
    and a link anywhere else is a reference.** Rule 8 names the ruled shape —
    a heading carrying the status marker, an `**Implementation:**` line
    beneath it — and REQUIRES tooling to keep accepting the checkbox-list form
    it superseded until the corpus finishes converting; keyed on the ruled
    shape alone this reader reports *zero phases* for every roadmap written the
    old way. **No other shape is admitted.** A heading whose text IS the phase
    link is not an entry shape: the ruling was that a corpus converts to rule
    8 rather than the standard growing a third form, so a phase link in a
    heading is what every other non-entry link is — a reference.

    A section is one shape or the other, never both. A section that carries a
    marker heading or an `**Implementation:**` line is a rule-8 entry, and any
    checkbox inside it is a completion criterion rather than a second entry:
    two of `common/planning_ui`'s sections link their own phase from a criterion
    bullet, and reading those as legacy entries would claim a phase twice with
    two different statuses. Only a section with neither signal is read in the
    legacy form.

    **A ``**Depends on:**`` line is read by neither set.** It names phases in
    OTHER components by definition, and reading its links here turned *"I
    depend on two components"* into *"I sequence two components"* — a roadmap
    with no phases of its own that follows the worklist's own advice was then
    excepted OUT of the report as a coordination document. The two walkers
    partition every declaration line at one column (see the module docstring).

    Hours attribute to a section containing exactly one OWNED phase entry —
    the roadmap's estimate for its own phase, which is what
    :func:`~.derivations.cross_check_hours` compares against the sprint
    file. A figure whose section owns no single phase is reported, never
    placed.
    """
    sections: list[_Section] = []
    current = _Section(ordinal=0)

    def resolve(target: str, line_no: int) -> str | None:
        if is_external(target):
            return None
        path_part, _anchor = split_anchor(target)
        if not path_part:
            return None
        try:
            resolved = resolve_within_root(root, rel, path_part)
        except PathEscape as exc:
            collector.add_finding(
                PATH_ESCAPES_ROOT,
                SECTION_UNCLASSIFIED,
                f"roadmap link escapes the checkout root: {exc.raw}",
                Provenance(rel, line_no),
                expected="a link target that resolves inside the checkout",
                detail="Reported and never opened.",
            )
            return None
        return resolved if is_phase_link(resolved) else None

    in_declaration_list = False
    for index, line in enumerate(lines):
        # Fenced blocks are skipped at the SAME scope every other walker skips
        # them, because they all now ask :func:`~.fences.fenced_mask`. `MDC-
        # Master-Planning#229` records a guard whose scope differed between two
        # walkers as a repeat defect; a shared mask is the only spelling of that
        # guard that cannot drift.
        if fenced[index]:
            # A fence delimiter is not a list item, so the dependency walker's
            # continuation lookahead stops dead at one. Resetting here keeps the
            # two walkers' idea of a declaration's EXTENT identical across a
            # fence boundary.
            in_declaration_list = False
            continue

        heading = HEADING_RE.match(line)
        if heading:
            sections.append(current)
            text = heading.group("text")
            current = _Section(ordinal=current.ordinal + 1, line=index + 1, text=text)
            anchor = ANCHOR_ID_RE.search(line)
            if anchor is None and index > 0:
                # The line immediately before, only when it is NOTHING but the
                # anchor tag: an anchor inside prose above a heading belongs to
                # that prose.
                above = lines[index - 1].strip()
                if above and ANCHOR_ID_RE.sub("", above).strip() == "":
                    anchor = ANCHOR_ID_RE.search(above)
            current.anchor = anchor.group("id") if anchor else ""
            unmarked = ANCHOR_ID_RE.sub("", text)
            current.status = _status_of(unmarked)
            current.has_marker = bool(STATUS_MARKER_RE.search(unmarked))
            first = LINK_RE.match(unmarked.strip())
            if first:
                # A heading that opens with a phase link is referencing that
                # phase. It used to be a third entry shape; the shape is gone
                # from the corpus, and the link is kept as a reference rather
                # than dropped with no trace.
                resolved = resolve(first.group("target"), index + 1)
                if resolved:
                    current.other.append((resolved, index + 1))
            # A heading carries its figure — `## Name — **~20h**` on four live
            # headings — so the heading line is read for hours like any other.
            for match in HOURS_RE.finditer(line):
                high = int(match.group("high")) if match.group("high") else None
                current.hours.append((int(match.group("low")), high, index + 1))
            continue

        # The declaration's own extent, mirrored from the dependency walker: the
        # marker onward on its line, plus a list beneath an EMPTY marker line.
        marker = dependency_marker(line)
        if marker is not None:
            linkable = line[: marker.start()]
            in_declaration_list = not linkable.strip() and not line[marker.end() :].strip()
        elif in_declaration_list and LIST_ITEM_RE.match(line):
            linkable = ""
        else:
            in_declaration_list = False
            linkable = line

        implementation = bool(IMPLEMENTATION_RE.match(linkable))
        checkbox = ENTRY_CHECKBOX_RE.match(linkable)
        claimed_here = False
        for match in LINK_RE.finditer(linkable):
            resolved = resolve(match.group("target"), index + 1)
            if resolved is None:
                continue
            if implementation:
                current.implementation.append((resolved, index + 1))
            elif checkbox and not claimed_here and component.owns(resolved):
                # The FIRST own-directory phase link on a checkbox line is the
                # entry's document; a second is a reference from it.
                claimed_here = True
                body = checkbox.group("body")
                name = _entry_name(body, match.group("text"))
                strong = _claim_is_strong(body, match.start() - checkbox.start("body"))
                current.checkboxes.append(
                    (resolved, index + 1, checkbox.group("mark"), name, strong)
                )
            else:
                current.other.append((resolved, index + 1))

        # Hours read the WHOLE line, deliberately, where links read only
        # `linkable`. An `~Nh` figure attaches to the heading SECTION, not to a
        # link, so a figure written beside a declaration ("blocked, ~20h once
        # unblocked") is this section's own estimate — there is no
        # dependency-owned phase here for it to attach to instead. The
        # asymmetry is also the safe direction: a figure whose section has no
        # single owned phase becomes UNATTRIBUTED and reported, never dropped.
        for match in HOURS_RE.finditer(line):
            high = int(match.group("high")) if match.group("high") else None
            current.hours.append((int(match.group("low")), high, index + 1))
    sections.append(current)

    owned: list[PhaseRef] = []
    weak_claims: set[int] = set()  # id() of a legacy entry whose link sits in prose
    references: list[tuple[str, int]] = []
    unattributed: list[tuple[int, str, int]] = []  # (line, figure, owned links in section)
    for section in sections:
        entries: list[PhaseRef] = []
        rule_8 = section.has_marker or bool(section.implementation)
        if rule_8:
            for path, line_no in section.implementation:
                if component.owns(path):
                    entries.append(
                        _heading_entry(section, rel, path, line_no, SHAPE_IMPLEMENTATION)
                    )
                else:
                    references.append((path, line_no))
            if not section.implementation:
                # Rule 8: a marker heading with no `Implementation:` line is a
                # phase whose checkboxes live in the entry itself.
                entries.append(_heading_entry(section, rel, "", section.line, SHAPE_INLINE))
                if not section.anchor:
                    collector.add_finding(
                        PHASE_ANCHOR_MISSING,
                        SECTION_DEPENDS_GRAPH,
                        f"inline phase `{entries[-1].name}` carries no explicit anchor id, "
                        "so nothing can depend on it safely",
                        Provenance(rel, section.line),
                        expected=(
                            '`<a id="…"></a>` on the heading line or the line before it — '
                            "rule 9: the id is the phase's identity and survives rewording"
                        ),
                        detail=(
                            "A slug generated from the words dies the next time the heading "
                            "is reworded, and every inbound link then dies silently. The "
                            "phase is in the graph under a line-keyed id no link can name; "
                            "it becomes a dependency target when its owner writes the id."
                        ),
                    )
            references.extend(section.other)
            for path, line_no, mark, name, strong in section.checkboxes:
                references.append((path, line_no))
        else:
            for path, line_no, mark, name, strong in section.checkboxes:
                entries.append(
                    PhaseRef(
                        path=path,
                        line=line_no,
                        shape=SHAPE_CHECKBOX,
                        name=name,
                        status=_STATUS_BY_MARK[mark],
                        section=section.ordinal,
                        roadmap=rel,
                    )
                )
                if not strong:
                    weak_claims.add(id(entries[-1]))
            references.extend(section.other)
            references.extend(section.implementation)

        if len(entries) == 1 and section.hours:
            low, high, _line = section.hours[0]
            entries[0].hours_low = low
            entries[0].hours_high = high
        elif section.hours:
            component.unattributed_hours += len(section.hours)
            for low, high, line_no in section.hours:
                figure = f"~{low}h" if high is None else f"~{low}-{high}h"
                unattributed.append((line_no, figure, len(entries)))
        owned.extend(entries)

    # An entry claims a document ONCE. A strong claim beats a weak one whatever
    # their order — a legacy bullet citing a LATER phase deep in its prose must
    # not steal that phase's entry — and among equals the first wins. A second
    # STRONG claim is a FINDING: two entries for one document is a corpus
    # defect, and the loser's status is the one nothing will ever read. A
    # losing weak claim is a citation, which is ordinary. The loser used to be
    # appended to `references`, where the dedupe below filtered it out as
    # already owned: dropped with no trace, in the module whose spine is that
    # nothing is.
    winner: dict[str, PhaseRef] = {}
    for claim in owned:
        if not claim.path:
            continue
        held = winner.get(claim.path)
        if held is None or (id(held) in weak_claims and id(claim) not in weak_claims):
            winner[claim.path] = claim
    owned_paths: set[str] = set()
    for claim in owned:
        if claim.path and winner[claim.path] is not claim:
            if id(claim) not in weak_claims:
                collector.add_finding(
                    PHASE_CLAIMED_TWICE,
                    SECTION_DERIVED,
                    f"phase document `{claim.path.rsplit('/', 1)[-1]}` is named by a second "
                    f"entry at L{claim.line}; the entry at L{winner[claim.path].line} "
                    "already owns it",
                    Provenance(rel, claim.line),
                    expected="each phase document named by exactly one phase entry",
                    detail=(
                        "The first entry's status is the one the graph reads; this entry's "
                        "is read by nothing. Reported rather than demoted to a reference, "
                        "because a reference to a document the roadmap owns is not a shape "
                        "the split admits. On a legacy checkbox-list roadmap a criterion "
                        "bullet that opens with a link to the phase is indistinguishable "
                        "from an entry; converting to rule 8 separates the two."
                    ),
                )
            continue
        if claim.path:
            owned_paths.add(claim.path)
        component.owned.append(claim)
        if claim.anchor:
            component.anchors[claim.anchor] = claim.node_id

    referenced_paths: set[str] = set()
    for path, line_no in references:
        if path in owned_paths or path in referenced_paths:
            continue
        referenced_paths.add(path)
        component.referenced.append(PhaseRef(path=path, line=line_no, roadmap=rel))

    if not unattributed:
        return
    # ONE row per roadmap, carrying every line — not one row per figure.
    #
    # These used to be counted into `component.unattributed_hours` and nothing
    # read that counter, so a figure the tool saw and could not place left no
    # trace at all: the never-silently-drop rule failing at the ATTRIBUTION
    # layer. Emitting them per-figure is the other failure — 75 rows on the
    # corpus as it stands, in the section the phase doc calls the spine, burying
    # the 13 unparsed lines that ARE the worklist. The phase doc makes exactly
    # this trade for the broken-link row ("reporting the whole set would bury
    # the finding that matters inside a hygiene sweep"); here the aggregate
    # still names every line, so nothing is dropped to buy the readability.
    lines_listed = ", ".join(f"L{line} {figure}" for line, figure, _n in unattributed)
    collector.add_finding(
        HOURS_UNATTRIBUTED,
        SECTION_UNPARSED,
        f"{len(unattributed)} hour figure(s) in this roadmap sit in a heading "
        f"section that does not contain exactly one owned phase entry, so the "
        f"stated attribution method cannot bind them to a phase",
        Provenance(rel, unattributed[0][0]),
        expected=(
            "a heading section containing exactly one owned phase entry and at "
            "least one `~Nh` figure — the method stated in this module's docstring"
        ),
        detail=(
            "Reported, never attributed: guessing which phase a figure belongs to "
            "would be authoring an hour figure, which this phase is forbidden to "
            "do. Every unattributed figure is named here with its line — "
            + lines_listed
        ),
    )


def parse_all_roadmaps(
    root: Path, roadmap_paths: list[str], collector: Collector
) -> list[Component]:
    parsed = (parse_roadmap(root, rel, collector) for rel in sorted(roadmap_paths))
    return [component for component in parsed if component is not None]

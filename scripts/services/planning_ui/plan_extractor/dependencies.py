"""The dependency contract — read ``**Depends on:**`` into edges, and account
for every roadmap that does not honour it.

**This module reads. It authors nothing.** A component's dependencies are a
planning judgement owned by that component, so a roadmap that records none is a
finding for its owner and never a line this tool writes. That is the phase's
spine and it is what makes the graph honestly incomplete rather than complete
and half-guessed.

The contract, stated once here and filed verbatim as a Documentation Standard
amendment in ``tracked/standards/`` (ratification is the operator's):

============  ================================================================
Marker        ``**Depends on:**`` at the start of a line, beneath the phase
              entry it belongs to in ``roadmap.md``. **The corpus also writes
              ``**Dependencies:**`` (11 roadmaps) and puts the marker
              mid-paragraph (2 more). Both are READ and both are reported as
              non-conforming** — see below
Dependency    a **markdown link** whose text is ``component/path · Phase Name``
              and whose target is the depended-on phase document, or the
              depended-on ``roadmap.md`` where no phase document exists
Separator     ``·`` between dependencies — read as prose, never parsed
Prose         permitted, encouraged and **ignored**. Sequencing notes,
              satisfied-already markers and conditionality all stay
Standalone    ``**Depends on:** NONE`` — the owner's positive statement that
              the entry depends on nothing. **Unqualified only**
Block form    ``**Depends on:**`` alone on its line, with a list beneath it.
              The parser reads the marker line AND that list
============  ================================================================

Four dispositions per roadmap and no fifth, tested in this order:

1. **Retired** — read from the component's own ``⚫``/``RETIRED`` status line,
   never from its name.
2. **Coordination document** — a roadmap with no phase documents of its own that
   sequences two or more OTHER components' phases. **The shape is tested BEFORE
   the worklists**, so a coordination document yields an exception rather than a
   finding.
3. **Owner-declared standalone** — every declaration on the roadmap is an
   unqualified ``NONE``.
4. **Resolves**, otherwise **one of the two worklists**.

Three decisions in here are judgement calls the phase doc does not settle
mechanically, so each is stated rather than buried:

**The coordination-document shape is the STRICT one, and it is the shape
``derivations.is_coordination_document`` already derives.** The phase doc's
implementation step abbreviates it to *"roadmap-with-no-phase-docs"*; its
requirement spells it out as *"a roadmap that indexes work owned elsewhere and
introduces no buildable phases of its own."* Those are different sets, and
measured on one corpus the abbreviation excepted seven components where the
full definition excepted one — the other six were ordinary unbuilt components
the abbreviation would have hidden. The direction of error is ruled: *"a wrong
exception hides a gap permanently while a wrong worklist entry merely annoys an
owner."* Reusing the existing derivation also keeps ONE answer to the question
*is this a coordination document* rather than two that can drift.

**A roadmap resolves only when EVERY declaration on it resolves.** A roadmap
commonly carries one resolving line alongside several prose ones. Rolling up
on *any* line resolving would report it as done and hide the unconverted
declarations behind the one that works, which reads healthier than the corpus
is. The conforming line is still
parsed into a real edge and still validates the format; the roadmap is still on
the worklist, with the lines that need converting named.

**A qualified ``NONE`` is not a standalone declaration.** ``**Depends on:**
nothing internal`` and ``**Depends on:** nothing inside this component`` state
something about internal dependencies and are silent about external ones. Only
an unqualified ``NONE`` — end of clause — is the positive record the
standalone class asks for.

**A deviation from the ruled format is a finding, never a reason to stop
reading.** ``**Dependencies:**`` and a mid-paragraph marker are both parsed into
real declarations and both raise
:data:`~.model.DEPENDENCY_MARKER_NON_CONFORMING`. The alternative — a
line-anchored, single-spelling parser — silently drops every declaration in
the other spelling or mid-paragraph, some of them carrying links that resolve,
and their owners are then reported as having recorded nothing. Measured on one
corpus that was more than half of all declarations. Two shapes are excluded
and they are exclusions rather than deviations: a marker inside a **fenced code
block** or an **inline code span** is prose ABOUT the marker (``common/planning_ui``'s
own roadmap contains *"a `**Depends on:**` line under each phase entry"*), and
reading it would have a document declaring a dependency by describing the
convention.

**What this parser does NOT look at**, stated so the next reader does not assume
coverage it lacks: a dependency written as a bare in-page anchor (``#some-
heading``); a **blank line between an empty marker line and its list**, which
ends the block (no live roadmap writes one, and tolerating it would have the
parser guess where a declaration stops); a list beneath a marker line that
already carries text (only a list
beneath an EMPTY marker line is read as a continuation, because grabbing an
unrelated list would author false edges); ``dependencies.md``, deliberately, so
a second edge source cannot disagree with the roadmap line; and a prose
dependency named by phase title alone, which the prose/link mismatch check
cannot see — that roadmap lands on the prose-only worklist instead.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from dataclasses import replace

from . import corpus_io
from .derivations import anchor_resolves_in, coordination_targets, is_coordination_document
from .model import (
    DEPENDENCY_CITES_BY_NUMBER,
    DEPENDENCY_CYCLE,
    DEPENDENCY_EDGE_BROKEN,
    DEPENDENCY_MARKER_NON_CONFORMING,
    DEPENDENCY_PROSE_LINK_MISMATCH,
    DEPENDENCY_PROSE_ONLY,
    DEPENDENCY_TARGET_UNDERIVABLE,
    DEPENDENCY_UNDECLARED,
    EDGE_BROKEN,
    EDGE_SATISFIED,
    EDGE_UNDERIVABLE,
    EDGE_UNSATISFIED,
    PATH_ESCAPES_ROOT,
    SECTION_DEPENDS_GRAPH,
    SECTION_DEPENDS_PROSE,
    SECTION_DEPENDS_UNDECLARED,
    SECTION_UNCLASSIFIED,
    SECTION_UNPARSED,
    STATUS_COMPLETE,
    STATUS_DEPRECATED,
    UNPARSED_LINE,
    Collector,
    Edge,
    Node,
    Provenance,
)
#: The marker, the fence delimiter, the list-continuation shape and the
#: declaration-block walk are :mod:`~.roadmaps`'s — one lexical answer for the
#: walkers that read the same file, imported the direction ``HEADING_RE``
#: already travels. They used to live here, which made this module's reading
#: of a declaration line invisible to the phase walker: it read the
#: declaration's links as phase entries of the component that DEPENDS on them.
from .fences import fenced_mask
from .roadmaps import (
    HEADING_RE,
    Component,
    declaration_blocks,
    is_phase_link,
)
from .safe_paths import PathEscape, exists_in_root, is_external, resolve_within_root, split_anchor
from .sprints import LINK_RE

#: The conforming spelling, per the ruled format.
CONFORMING_MARKER = "Depends on"

#: A link whose text is a phase NUMBER rather than a phase name: `Phase 0`,
#: `phase1`, `ansible Phase 4`, `Home Assistant Phase 1`, `phase10 §10.3`.
#: Rule 4 forbids the form in anything newly written because a number
#: survives a rename and a reader cannot tell which phase it was. ONE
#: definition, read by both walkers: it lived in :mod:`~.phase_docs` alone,
#: so the guard ran on the surface rule 9 exempts (a phase doc's line, which
#: is itself a finding) and never on the roadmap — the one carrier the rule
#: binds. Measured on the merged corpus: four roadmap declarations citing
#: five phases by number, none reported.
#:
#: The population the predicate stands in for is *every link text whose
#: target is identified by its number* — a text that ENDS in `phase N`, with
#: or without a trailing `§N.N` section citation (a section does not make a
#: number a name). Nothing before `phase` is constrained: it allowed one
#: prefix word, then a run of `[\w/.&+-]` words, and each spelling was blind
#: to a live shape — `Home Assistant Phase 1` (two-word component), then
#: `VM reconciler — Phase 7` (an em-dash is not a word character). Keying on
#: the suffix is what the class is; keying on the prefix's spelling
#: enumerates instances. What it deliberately does NOT admit: a name AFTER the
#: number (`Monitoring Roadmap Phase 2 — Configuration as Code` names the
#: phase) and a trailing annotation (`Phase 2 (planned)` — none is live; if
#: one appears, widen the tail here, not in a caller). Measured repo-wide over
#: every link text in 446 files: the widened form newly matches 123 distinct
#: texts / 216 occurrences against the one-word form, every one a phase cited
#: by number, no names.
BY_NUMBER_RE = re.compile(r"^.*\bphase\s*\d+[a-z]?(?:\s*§\s*[\d.]+)?\s*$", re.IGNORECASE)

#: Explicit anchor id → phase node id, per roadmap — the index a
#: ``roadmap.md#anchor`` or bare ``#anchor`` target resolves through. Built
#: from every :class:`~.roadmaps.Component`'s ``anchors`` after all roadmaps
#: are parsed, because a target can name an entry in ANY roadmap.
AnchorIndex = dict[str, dict[str, str]]

#: A standard's vendoring banner, as the Documentation Standard § Cross-ecosystem
#: vendored standards writes it. Its presence is what makes *"satisfied;
#: vendored and ratified, amendments go upstream"* a computed fact.
VENDORED_MARKER = "VENDORED — DO NOT EDIT LOCALLY"

#: An unqualified ``NONE`` — the token, then the end of the clause. ``NONE
#: internal`` and ``NONE inside this component`` deliberately do not match: a
#: qualifier makes the line a FINDING, not a declaration.
#:
#: **The token was ``nothing`` until 2026-09-07.** Documentation Standard rule 9
#: ratified ``NONE``, and the reason the token exists at all is the third state:
#: an absent line cannot distinguish a declaration from DAMAGE, so absence is a
#: finding and only a written token means *somebody assessed this*. Matching
#: stays case-insensitive — a human writing ``None`` means the token, and a
#: finding raised over capitalisation is noise that trains readers to ignore
#: findings.
NONE_RE = re.compile(r"^NONE\s*(?:[.;,)\]]|$)", re.IGNORECASE)

#: A component named in prose as ``<domain>/<name>``. Used only by the
#: prose/link mismatch check, and only against slugs that are real components.
#: Up to three segments: a component nested one level under another —
#: `<domain>/<name>/old` — is a real component, and a two-segment-only pattern
#: can never name it.
COMPONENT_SLUG_RE = re.compile(
    r"(?<![\w/-])(?P<slug>(?:common|service|workload)/[a-z0-9][a-z0-9_.-]*"
    r"(?:/[a-z0-9][a-z0-9_.-]*)?)"
)

# ---- per-declaration dispositions ----------------------------------------
LINE_RESOLVES = "line resolves"
LINE_STANDALONE = "standalone"
LINE_PROSE_ONLY = "prose only"

# ---- per-roadmap dispositions --------------------------------------------
RESOLVES = "resolves"
EXCEPTION_RETIRED = "exception — retired"
EXCEPTION_COORDINATION = "exception — coordination document"
EXCEPTION_STANDALONE = "exception — owner-declared standalone"
WORKLIST_PROSE_ONLY = "worklist — declares in prose only"
WORKLIST_UNDECLARED = "worklist — declares nothing"

EXCEPTIONS = frozenset({EXCEPTION_RETIRED, EXCEPTION_COORDINATION, EXCEPTION_STANDALONE})
WORKLISTS = frozenset({WORKLIST_PROSE_ONLY, WORKLIST_UNDECLARED})

#: Stated on the page beside the accounting table, so a reader can reproduce it.
ACCOUNTING_METHOD = (
    "each roadmap gets exactly one disposition, tested in order: RETIRED from its "
    "own ⚫/RETIRED status line; COORDINATION DOCUMENT from the shape `no phase "
    "documents of its own, and phase links into two or more other components`; "
    "OWNER-DECLARED STANDALONE when every `**Depends on:**` line on it is an "
    "unqualified `nothing`; RESOLVES when every line carries at least one link "
    "resolving to a node in the graph; the PROSE-ONLY worklist when any line does "
    "not; and the DECLARES-NOTHING worklist when the roadmap carries no line at "
    "all. Nothing is authored for any of them."
)


@dataclass(frozen=True)
class DependencyLink:
    """One link read from a declaration.

    ``node_id`` is ``""`` ONLY for a target outside the checkout — an
    ``https://`` link, or a path that resolved to nothing. Every target inside
    it is node-shaped: rule 9's table is *"a phase: its status marker; a
    standard **or other non-phase artifact**: whether it resolves"*, so a
    research paper, the sprint file, a guide page or a tracked item is an
    ``artifact:`` node satisfied by resolving. This docstring used to exclude
    those — and the phase doc that narrowed rule 9 to phases and standards has
    been corrected, because a phase doc never overrides a binding rule.

    ``anchor`` is the fragment the link carried. For a ``roadmap.md`` target it
    is what makes the link name a PHASE rather than a component.
    """

    text: str
    target: str
    resolved: str
    node_id: str
    line: int
    anchor: str = ""


@dataclass
class Declaration:
    """One ``**Depends on:**`` declaration and everything read from it."""

    component: str
    roadmap: str
    line: int
    rest: str
    prose: str
    #: ``Depends on`` or ``Dependencies`` — the spelling actually written.
    marker: str = CONFORMING_MARKER
    #: The ruled format: the conforming spelling, at the start of its line.
    conforming: bool = True
    #: The marker sits mid-paragraph. Tracked SEPARATELY from the spelling
    #: because a declaration can deviate on both axes at once — the live
    #: `common/vm_orchestration:85` does — and reporting only the first tells
    #: its owner about half the rewrite they owe.
    mid_paragraph: bool = False
    links: list[DependencyLink] = field(default_factory=list)
    source_id: str = ""
    source_kind: str = "component"
    disposition: str = LINE_PROSE_ONLY

    def graph_links(self) -> list[DependencyLink]:
        return [link for link in self.links if link.node_id]


@dataclass(frozen=True)
class Accounting:
    """One roadmap's disposition — the row that makes requirement 2 checkable."""

    component: str
    roadmap: str
    disposition: str
    reason: str
    declaration_lines: tuple[int, ...] = ()
    unresolved_lines: tuple[int, ...] = ()
    #: Declarations carrying at least one link that resolves to a real node.
    #: Distinct from `not unresolved_lines`: an owner-authored `nothing` line is
    #: neither unresolved nor a resolving LINK, and conflating the two would let
    #: a purely-standalone roadmap be counted as one expressing a dependency as
    #: a link.
    resolving_lines: tuple[int, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "component": self.component,
            "roadmap": self.roadmap,
            "disposition": self.disposition,
            "reason": self.reason,
            "declaration_lines": list(self.declaration_lines),
            "unresolved_lines": list(self.unresolved_lines),
            "resolving_lines": list(self.resolving_lines),
        }


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _node_id_for(resolved: str, anchor: str, anchors: AnchorIndex) -> str:
    """The graph node id a resolved link names, or ``""`` for a non-node target.

    Node-SHAPED, not node-EXISTS: an id naming no node is exactly the broken
    edge requirement 4 asks for, and it can only be reported if the edge is
    emitted.

    **A ``roadmap.md#anchor`` target names a PHASE, never its component.**
    Rule 9's target-form table gives a dependency three legal shapes, and the
    anchor form is how a roadmap that keeps its phases inline is depended on.
    The id is looked up in the owning roadmap's explicit-anchor index; an
    anchor that names no entry yields ``phase:<roadmap>#<anchor>``, an id no
    node carries, so the edge is emitted and reported BROKEN rather than
    silently collapsed onto the component's status line. This function used to
    discard the anchor — the same defect as wrong attribution, arriving
    through a different door.
    """
    if resolved.startswith("standards/"):
        return f"standard:{resolved}"
    if resolved.endswith("/roadmap.md"):
        if anchor:
            return anchors.get(resolved, {}).get(anchor, f"phase:{resolved}#{anchor}")
        return f"component:{resolved.rsplit('/', 1)[0]}"
    if is_phase_link(resolved):
        return f"phase:{resolved}"
    # A research paper, the sprint file, a guide page, a tracked item: rule 9's
    # *"other non-phase artifact"*, satisfied by resolving. Node-shaped, so a
    # missing one is a BROKEN edge — a node should exist and does not. This
    # used to return `""` and report UNDERIVABLE, which was the phase doc's
    # narrowing of the rule rather than the rule.
    return f"artifact:{resolved}"


def _links_in(
    root: Path,
    roadmap: str,
    line_no: int,
    text: str,
    collector: Collector,
    anchors: AnchorIndex,
) -> list[DependencyLink]:
    out: list[DependencyLink] = []
    for match in LINK_RE.finditer(text):
        target = match.group("target")
        path_part, anchor = split_anchor(target)
        if not path_part and anchor:
            # Rule 9's same-file form: a bare `#anchor` names a phase in THIS
            # roadmap. It used to fall through a `continue` with no finding —
            # the exact shape the never-silently-drop rule forbids.
            out.append(
                DependencyLink(
                    text=match.group("text"),
                    target=target,
                    resolved=roadmap,
                    node_id=_node_id_for(roadmap, anchor, anchors),
                    line=line_no,
                    anchor=anchor,
                )
            )
            continue
        if is_external(target) or not path_part:
            # An `https://` or `file://` target on a `**Depends on:**` line.
            # Rule 9: a dependency on another ecosystem's work IS an artifact
            # and stays — so it is carried, with no node, and reported by
            # :func:`derive_edges` as underivable. It used to be a bare
            # `continue`, the same silent drop the bare-anchor form was.
            out.append(
                DependencyLink(
                    text=match.group("text"),
                    target=target,
                    resolved="",
                    node_id="",
                    line=line_no,
                    anchor=anchor,
                )
            )
            continue
        try:
            resolved = resolve_within_root(root, roadmap, path_part)
        except PathEscape as exc:
            collector.add_finding(
                PATH_ESCAPES_ROOT,
                SECTION_UNCLASSIFIED,
                f"dependency link escapes the checkout root: {exc.raw}",
                Provenance(roadmap, line_no),
                expected="a link target that resolves inside the checkout",
                detail="Reported and never opened.",
            )
            continue
        out.append(
            DependencyLink(
                text=match.group("text"),
                target=target,
                resolved=resolved,
                node_id=_node_id_for(resolved, anchor, anchors),
                line=line_no,
                anchor=anchor,
            )
        )
    return out


def _strip_links(text: str) -> str:
    """The declaration's prose — link markdown removed, link TEXT removed too.

    The link text carries the component slug by convention (``[`common/ansible`
    · Root-Runnable …]``), so leaving it in would make every conforming line
    read as prose naming a component. The mismatch check needs what the prose
    says BESIDE the links.
    """
    return LINK_RE.sub(" ", text)


def parse_declarations(
    root: Path,
    component: Component,
    collector: Collector,
    anchors: AnchorIndex | None = None,
) -> list[Declaration]:
    """Every ``**Depends on:**`` declaration in one roadmap, with its links.

    A declaration's SOURCE is the phase entry it sits beneath, read from the
    entry :mod:`~.roadmaps` already parsed for that heading section. Otherwise
    the component node — stated rather than guessed, the same shape as this
    package's hour attribution and for the same reason.
    """
    lines = corpus_io.read_lines(root, component.roadmap, collector)
    if lines is None:
        return []  # reported by read_lines as FILE_UNREADABLE

    anchors = anchors if anchors is not None else {}
    declarations: list[Declaration] = []
    blocks, fence_opened_at = declaration_blocks(lines)
    for block in blocks:
        index, match = block.index, block.match
        line = lines[index]
        marker = match.group("marker")
        rest = line[match.end() :].strip()
        line_initial = not line[: match.start()].strip()
        # The declaration is the marker onward, never the sentence in front of
        # it — a mid-paragraph marker's preceding prose belongs to the paragraph,
        # and reading it would feed unrelated component names to the prose/link
        # mismatch check.
        raw = "\n".join([line[match.start() :]] + [lines[i] for i in block.lines[1:]])
        declarations.append(
            Declaration(
                component=component.path,
                roadmap=component.roadmap,
                line=index + 1,
                rest=rest,
                prose=_strip_links(raw),
                marker=marker,
                conforming=line_initial and marker == CONFORMING_MARKER,
                mid_paragraph=not line_initial,
                links=[
                    link
                    for i in block.lines
                    for link in _links_in(
                        root,
                        component.roadmap,
                        i + 1,
                        lines[i][match.start() :] if i == index else lines[i],
                        collector,
                        anchors,
                    )
                ],
            )
        )

    if fence_opened_at:
        # Everything after an unterminated fence was skipped. Silence here is
        # indistinguishable from a roadmap that genuinely declares nothing, and
        # this module's whole spine is that a thing it cannot read is a finding.
        collector.add_finding(
            UNPARSED_LINE,
            SECTION_UNPARSED,
            f"`{component.path}` opens a code fence that is never closed, so "
            f"{len(lines) - fence_opened_at} line(s) below it were not read for "
            "dependency declarations",
            Provenance(component.roadmap, fence_opened_at),
            expected="every fenced block closed by a matching ``` or ~~~",
            detail=(
                "Any `**Depends on:**` line below the opening fence is invisible to "
                "the parser, and the roadmap would be reported as declaring nothing "
                "for declarations it may already carry."
            ),
        )

    _report_non_conforming(declarations, collector)
    _report_by_number_citations(declarations, collector)
    _attribute_sources(component, lines, declarations)
    return declarations


def _report_by_number_citations(declarations: list[Declaration], collector: Collector) -> None:
    """One ``DEPENDENCY_CITES_BY_NUMBER`` row per declaration whose link text
    cites a phase by NUMBER — the same row :mod:`~.phase_docs` emits for a phase
    document's line, with the roadmap line as provenance."""
    for declaration in declarations:
        by_number = [link.text for link in declaration.links if BY_NUMBER_RE.match(link.text)]
        if not by_number:
            continue
        collector.add_finding(
            DEPENDENCY_CITES_BY_NUMBER,
            SECTION_DEPENDS_GRAPH,
            f"{len(by_number)} link(s) cite a phase by NUMBER — "
            + ", ".join(f"`{text.strip()}`" for text in by_number),
            Provenance(declaration.roadmap, declaration.line),
            expected="the phase cited by NAME (Documentation Standard rule 4)",
            detail=(
                "A number survives a rename and tells a reader nothing about which "
                "phase it was. The link still resolves and its edge still derives — "
                "this row is about the citation's text, which is one edit on its own."
            ),
        )


def _report_non_conforming(declarations: list[Declaration], collector: Collector) -> None:
    """One row per roadmap naming every declaration the ruled format does not sanction.

    **Read, then reported — never dropped.** The two deviations have the same
    remedy (rewrite the marker) and neither changes what the declaration means,
    so they are one row per roadmap rather than one per line: 13 roadmaps
    deviate on the live corpus, and one row each keeps the section readable
    while still naming every line.
    """
    off = [d for d in declarations if not d.conforming]
    if not off:
        return
    detail = ", ".join(
        f"L{d.line} (`**{d.marker}:**`"
        + (", mid-paragraph" if d.mid_paragraph else "")
        + ")"
        for d in off
    )
    collector.add_finding(
        DEPENDENCY_MARKER_NON_CONFORMING,
        SECTION_DEPENDS_GRAPH,
        f"`{off[0].component}` carries {len(off)} dependency declaration(s) the ruled "
        "format does not sanction — a second spelling, or a marker mid-paragraph",
        Provenance(off[0].roadmap, off[0].line),
        expected="`**Depends on:**` at the start of its line",
        detail=(
            "Read and counted as declarations regardless — refusing to read a "
            "recorded dependency to enforce a formatting preference would put its "
            "owner on the authoring worklist for work already done. Lines: "
            + detail
        ),
    )


def _attribute_sources(
    component: Component,
    lines: list[str],
    declarations: list[Declaration],
) -> None:
    """Bind each declaration to the phase ENTRY of its heading section.

    **The entry, and nothing looser.** The obvious rule — *the section's
    own-component phase link, when there is exactly one* — was written first
    and MEASURED WRONG on the live corpus in both directions. Two of the five
    sections in ``common/planning_ui``'s roadmap link a phase of their own in a
    criterion bullet as well as in their header, and one section that has no
    phase document at all links another phase in a bullet. The first case lost
    an attribution; the second INVENTED one, and produced a self-loop that the
    cycle check then reported as a real cycle in the plan. A false cycle is
    worse than no attribution: it sends an operator to re-sequence work that
    is correctly sequenced.

    The entry is whatever :mod:`~.roadmaps` read for the section — rule 8's
    `**Implementation:**` line, or an inline phase whose identity is its
    anchor, which is what lets a declaration beneath an inline heading belong
    to THAT phase (requirement 7). The `**Implementation:**` line is read once,
    there, and consumed here through :attr:`~.roadmaps.PhaseRef.section`.
    Where a section carries no entry the declaration is attributed to the
    component, and the report states how many were bound each way rather than
    implying the attribution was total.
    """
    if not declarations:
        return

    # HEADING_RE is roadmaps' own: these section boundaries must be the SAME
    # boundaries that module flushes phase sections on, or a declaration is
    # attributed against a section split nothing else in the package agrees with.
    # THAT INCLUDES THE FENCE GUARD. `HEADING_RE` matches `# install the thing`,
    # an ordinary shell comment, so a fenced bash example between an
    # `**Implementation:**` line and a declaration used to shift this counter
    # while `_collect_phases` ignored it. `fences.fenced_mask` is the same
    # answer both walkers now read.
    #
    # The mask is consulted, never used to SKIP: `section_of_line` is indexed by
    # line number and must stay aligned with `lines`, so a fenced line still
    # records the section it sits in.
    fenced = fenced_mask(lines)
    section_of_line: list[int] = []
    section = 0
    for index, line in enumerate(lines):
        if not fenced[index] and HEADING_RE.match(line):
            section += 1
        section_of_line.append(section)

    section_phase: dict[int, set[str]] = {}
    for ref in component.owned:
        section_phase.setdefault(ref.section, set()).add(ref.node_id)

    for declaration in declarations:
        owned = section_phase.get(section_of_line[declaration.line - 1], set())
        if len(owned) == 1:
            declaration.source_id = next(iter(owned))
            declaration.source_kind = "phase"
        else:
            declaration.source_id = f"component:{component.path}"
            declaration.source_kind = "component"


# ---------------------------------------------------------------------------
# Edges and dispositions
# ---------------------------------------------------------------------------


#: The node kinds :func:`document_nodes` emits — the targets rule 9 satisfies
#: by resolving. A standard additionally carries its vendoring banner.
DOCUMENT_NODE_KINDS = ("standard", "artifact")


def document_nodes(
    root: Path, declarations: list[Declaration], collector: Collector
) -> tuple[list[Node], dict[str, str]]:
    """A ``standard`` or ``artifact`` node for every document a declaration depends on.

    Only the documents SOMETHING depends on — the graph is a planning graph and
    a document enters it by being a target, not by existing. A target whose
    file is not there gets no node, so its edge is emitted onto nothing and
    reported BROKEN; a standard that IS there carries whether it wears the
    vendoring banner, which is the second half of rule 9's satisfaction rule
    for a standard. An artifact — a research paper, the sprint file, a guide
    page, a tracked item — has no banner to carry; rule 9 asks only whether it
    resolves.

    Returns the nodes and the text of each, keyed by path, so the anchor check
    in :func:`derive_edges` reads the same bytes rather than opening the file a
    second time with a throwaway collector.
    """
    texts: dict[str, str] = {}
    nodes: list[Node] = []
    node_ids = sorted(
        {
            link.node_id
            for declaration in declarations
            for link in declaration.links
            if link.node_id.split(":", 1)[0] in DOCUMENT_NODE_KINDS
        }
    )
    for node_id in node_ids:
        kind, path = node_id.split(":", 1)
        if not exists_in_root(root, path):
            continue
        text = corpus_io.read_text(root, path, collector)
        if text is None:
            continue  # reported as FILE_UNREADABLE by the read
        texts[path] = text
        attrs: dict[str, object] = {"path": path}
        if kind == "standard":
            attrs["vendored"] = VENDORED_MARKER in text
        nodes.append(
            Node(
                id=node_id,
                kind=kind,
                label=path.rsplit("/", 1)[-1],
                provenance=Provenance(path, 1),
                attrs=attrs,
            )
        )
    return nodes, texts


def derive_edges(
    declarations: list[Declaration],
    nodes_by_id: dict[str, Node] | None = None,
    document_texts: dict[str, str] | None = None,
    collector: Collector | None = None,
) -> list[Edge]:
    """One edge per graph-shaped link, each carrying its derived STATE.

    An edge whose target names no node is STILL emitted — that is what makes
    it reportable. Dropping it would leave a broken link reading as a satisfied
    dependency, which is the failure requirement 3 names.

    **Satisfaction derives from what the target IS, in this one pass, and is
    written nowhere else.** Rule 9's table, applied per target kind:

    * a **phase** — its owning entry's rule-8 status marker. ``COMPLETE`` is
      satisfied; any other marker is unsatisfied; NO marker is UNDERIVABLE and
      reported, because an entry with no marker is a rule-8 defect and a
      colour guessed for it would render as authority;
    * a **standard** — satisfied by resolving, plus its vendoring banner where
      it carries one; an anchor that no longer resolves in it is BROKEN;
    * any other **artifact** in the checkout — a research paper, the sprint
      file, a guide page, a tracked item — satisfied by resolving, exactly as
      a standard is and without the banner; a missing file or a rotted anchor
      is BROKEN. Rule 9: *"a standard or other non-phase artifact: whether it
      resolves"*;
    * a **component** — UNDERIVABLE and reported. A dependency points at a
      phase; a whole component has a free-text status line, not a marker;
    * a target that names **no node** — BROKEN, under its own code, with the
      reason the contract can state.

    A link with no node at all — an ``https://`` target, outside the checkout
    — is reported UNDERIVABLE and emits no edge: rule 9 makes every link on
    the line a dependency, and one the tool cannot resolve is a finding for
    its owner rather than a silent skip.

    Called without a node index (the older signature) it emits state-less
    edges, which is what the unit tests that build edges by hand rely on.
    """
    edges: list[Edge] = []
    for declaration in declarations:
        for link in declaration.links:
            if not link.node_id:
                if collector is not None:
                    _report_underivable(
                        declaration,
                        link,
                        collector,
                        f"`{link.target}` is outside this checkout — rule 9 keeps a "
                        "dependency on another ecosystem's artifact, and this tool cannot "
                        "resolve one",
                        "a link to the depended-on phase (its document or its anchor), or "
                        "to a standard or other artifact in this checkout",
                    )
                continue
            edge = Edge(
                source=declaration.source_id,
                target=link.node_id,
                kind="depends_on",
                provenance=Provenance(declaration.roadmap, link.line),
                target_path=link.resolved,
            )
            if nodes_by_id is not None and collector is not None:
                edge = replace(
                    edge,
                    state=_edge_state(declaration, link, nodes_by_id, document_texts or {}, collector),
                )
            edges.append(edge)
    return edges


def _edge_state(
    declaration: Declaration,
    link: DependencyLink,
    nodes_by_id: dict[str, Node],
    document_texts: dict[str, str],
    collector: Collector,
) -> str:
    node = nodes_by_id.get(link.node_id)
    kind = link.node_id.split(":", 1)[0]
    if node is None:
        if kind == "standard":
            reason = f"no standards document exists at `{link.resolved}`"
        elif kind == "artifact":
            reason = f"no such file exists at `{link.resolved}`"
        elif link.anchor and link.resolved.endswith("/roadmap.md"):
            reason = (
                f"anchor `#{link.anchor}` names no phase entry in `{link.resolved}` — "
                "an inline phase is addressed by the explicit `<a id>` its heading carries"
            )
        elif kind == "component":
            reason = f"no component has a roadmap at `{link.resolved}`"
        else:
            reason = f"no phase document exists at `{link.resolved}`"
        collector.add_finding(
            DEPENDENCY_EDGE_BROKEN,
            SECTION_DEPENDS_GRAPH,
            f"dependency edge `{declaration.source_id}` → `{link.node_id}` is BROKEN: {reason}",
            Provenance(declaration.roadmap, link.line),
            expected="a link target that resolves to a phase, a standard or another artifact in this checkout",
            detail=(
                "A broken edge is a defect in the corpus and an unsatisfied edge is work "
                "not yet done; rule 9 says the two must not render alike. The edge is "
                "emitted in the `broken` state so nothing downstream can mistake it for "
                "either."
            ),
        )
        return EDGE_BROKEN

    if kind in DOCUMENT_NODE_KINDS:
        # Rule 9: "a standard or other non-phase artifact: whether it resolves".
        # The file resolved (a node exists); the anchor must too.
        if link.anchor and not anchor_resolves_in(document_texts.get(link.resolved), link.anchor):
            collector.add_finding(
                DEPENDENCY_EDGE_BROKEN,
                SECTION_DEPENDS_GRAPH,
                f"dependency edge `{declaration.source_id}` → `{link.node_id}` is BROKEN: "
                f"anchor `{link.anchor}` no longer resolves in `{link.resolved}`",
                Provenance(declaration.roadmap, link.line),
                expected=f"a section or line that exists in the target {kind}",
                detail=(
                    f"The {kind} exists and the section it cites has moved or been renamed. "
                    "Reported rather than treated as resolving: a dependency on a section "
                    "that is not there is not satisfied by the file being there."
                ),
            )
            return EDGE_BROKEN
        return EDGE_SATISFIED

    if kind == "phase":
        status = node.attrs.get("status", "")
        if status == STATUS_COMPLETE:
            return EDGE_SATISFIED
        if status == STATUS_DEPRECATED:
            _report_underivable(
                declaration,
                link,
                collector,
                f"target phase `{node.label}` is DEPRECATED (rule 5), so it will never be "
                "satisfied and never be work in progress",
                "a dependency on a live phase, or the entry rewritten to depend on whatever "
                "superseded this one",
            )
            return EDGE_UNDERIVABLE
        if not status:
            owner = node.attrs.get("owner", "")
            _report_underivable(
                declaration,
                link,
                collector,
                (
                    f"target phase `{node.label}`'s entry carries no rule-8 status marker"
                    if owner
                    else f"no roadmap phase entry owns target phase `{node.label}`, so it "
                    "has no status to read"
                ),
                "the target's roadmap entry in rule 8's shape — a heading carrying one of "
                "the four status markers",
            )
            return EDGE_UNDERIVABLE
        return EDGE_UNSATISFIED

    # A component. Rule 9: a dependency points at a phase, and a phase is
    # addressed however it can be — its document, or its anchor.
    _report_underivable(
        declaration,
        link,
        collector,
        f"target `{link.node_id}` is a whole component; its `**Status:**` line is prose, "
        "not a rule-8 marker, and rule 9 derives satisfaction from a PHASE",
        "the depended-on phase named — its document, or `roadmap.md#<anchor>` where the "
        "phase lives inline",
    )
    return EDGE_UNDERIVABLE


def _report_underivable(
    declaration: Declaration,
    link: DependencyLink,
    collector: Collector,
    reason: str,
    expected: str,
) -> None:
    collector.add_finding(
        DEPENDENCY_TARGET_UNDERIVABLE,
        SECTION_DEPENDS_GRAPH,
        f"satisfaction of `{declaration.source_id}` → `{link.target}` cannot be derived: "
        + reason,
        Provenance(declaration.roadmap, link.line),
        expected=expected,
        detail=(
            "Reported rather than guessed. Rule 9: satisfaction derives from what the "
            "target IS — a phase from its status marker, a standard from resolving — and "
            "a value the tool made up for anything else would render as an authoritative "
            "colour."
        ),
    )


def classify_declarations(declarations: list[Declaration], node_ids: set[str]) -> None:
    """Set each declaration's disposition against the node set."""
    for declaration in declarations:
        if any(link.node_id in node_ids for link in declaration.graph_links()):
            declaration.disposition = LINE_RESOLVES
        elif NONE_RE.match(declaration.rest.strip().strip("*`").strip()):
            declaration.disposition = LINE_STANDALONE
        else:
            declaration.disposition = LINE_PROSE_ONLY


def account(
    root: Path,
    components: list[Component],
    by_component: dict[str, list[Declaration]],
) -> list[Accounting]:
    """One disposition per roadmap. See :data:`ACCOUNTING_METHOD`."""
    rows: list[Accounting] = []
    for component in sorted(components, key=lambda c: c.path):
        declarations = by_component.get(component.path, [])
        lines = tuple(d.line for d in declarations)
        unresolved = tuple(d.line for d in declarations if d.disposition == LINE_PROSE_ONLY)
        resolving = tuple(d.line for d in declarations if d.disposition == LINE_RESOLVES)

        def row(disposition: str, reason: str) -> Accounting:
            # One construction site. `unresolved` and `resolving` are adjacent
            # same-typed tuples, so six positional call sites is six chances to
            # transpose them and no type checker that would notice.
            return Accounting(
                component.path,
                component.roadmap,
                disposition,
                reason,
                lines,
                unresolved,
                resolving,
            )

        if component.retired:
            rows.append(
                row(
                    EXCEPTION_RETIRED,
                    f"its own status line reads `{(component.status_text or '')[:60]}`",
                )
            )
            continue
        if is_coordination_document(component):
            elsewhere = sorted(coordination_targets(component))
            rows.append(
                row(
                    EXCEPTION_COORDINATION,
                    "no phase documents of its own; sequences phases in "
                    + ", ".join(f"`{path.removeprefix('development/')}`" for path in elsewhere),
                )
            )
            continue
        if declarations and all(d.disposition == LINE_STANDALONE for d in declarations):
            rows.append(
                row(
                    EXCEPTION_STANDALONE,
                    "every `**Depends on:**` line on it is an owner-authored, "
                    "unqualified `nothing`",
                )
            )
            continue
        if not declarations:
            rows.append(row(WORKLIST_UNDECLARED, _undeclared_reason(root, component)))
            continue
        if unresolved:
            rows.append(
                row(
                    WORKLIST_PROSE_ONLY,
                    f"{len(unresolved)} of {len(declarations)} declaration(s) carry no link "
                    "the parser can resolve to a node",
                )
            )
            continue
        # Not every declaration here carries a LINK: an owner-authored `nothing`
        # is neither unresolved nor resolving, and saying "all N resolve" of a
        # roadmap mixing the two claims links that do not exist.
        standalone = len(declarations) - len(resolving)
        rows.append(
            row(
                RESOLVES,
                f"all {len(declarations)} declaration(s) accounted for — "
                f"{len(resolving)} resolving to a node"
                + (f", {standalone} owner-declared `NONE`" if standalone else ""),
            )
        )
    return rows


def _undeclared_reason(root: Path, component: Component) -> str:
    """The worklist entry's reason, naming the cheap close where one exists.

    A component carrying a ``dependencies.md`` has the answer already written by
    a human — its owner reads the matrix and writes the links. Naming the file
    costs nothing and turns a vague ask into a five-minute one.
    """
    if exists_in_root(root, f"{component.path}/dependencies.md"):
        return (
            "no `**Depends on:**` line anywhere in the roadmap — **cheap close**: "
            f"`{component.path}/dependencies.md` already records the answer in prose"
        )
    return "no `**Depends on:**` line anywhere in the roadmap"


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------


def report_worklists(rows: list[Accounting], collector: Collector) -> None:
    """Emit the two worklists — the phase's stated deliverable.

    Two codes and two sections because the two gaps have different remedies:
    **authoring** for a roadmap that declares nothing, **converting** for one
    whose prose already contains the answer.
    """
    for row in rows:
        if row.disposition == WORKLIST_UNDECLARED:
            collector.add_finding(
                DEPENDENCY_UNDECLARED,
                SECTION_DEPENDS_UNDECLARED,
                f"`{row.component}` records no dependency a parser can read",
                Provenance(row.roadmap),
                expected=(
                    "a `**Depends on:**` line beneath each phase entry, each dependency "
                    "a markdown link to the depended-on phase document — or an "
                    "unqualified `**Depends on:** nothing`"
                ),
                detail=(
                    row.reason
                    + ". Authored by the component's owner, never by this tool: whether "
                    "an absence is a gap or a true standalone cannot be recovered from "
                    "the corpus."
                ),
            )
        elif row.disposition == WORKLIST_PROSE_ONLY:
            collector.add_finding(
                DEPENDENCY_PROSE_ONLY,
                SECTION_DEPENDS_PROSE,
                f"`{row.component}` declares a dependency a reader can follow and the "
                f"parser cannot, on line(s) "
                + ", ".join(f"L{line}" for line in row.unresolved_lines),
                Provenance(row.roadmap, row.unresolved_lines[0] if row.unresolved_lines else 0),
                expected=(
                    "each dependency written as a markdown link to the phase "
                    "document — or, if the entry truly depends on nothing, the "
                    "unqualified line `**Depends on:** nothing` (the one word "
                    "that closes this entry; a qualified `nothing internal` "
                    "does not, because it is silent about external dependencies)"
                ),
                detail=(
                    row.reason
                    + ". The remedy is CONVERTING, not authoring — the prose already "
                    "contains the answer, and it stays after the links are added."
                ),
            )


def report_prose_link_mismatch(
    declarations: list[Declaration], component_paths: set[str], collector: Collector
) -> None:
    """Flag a declaration whose prose names a component its links omit.

    **Scoped to declarations that already resolve.** On a line with no
    resolvable link every prose name would fire, duplicating the prose-only
    worklist row for the same roadmap and telling its owner nothing new.

    Stated method: after link markdown is removed, a ``<domain>/<name>`` slug
    that is a real component directory and is not among the components the
    line's resolving links point into — **by a phase or component node**. A
    document that merely sits inside a component's directory (a research paper,
    an ``artifact:`` node since rule 9's *"other non-phase artifact"* became a
    target) is a link to that document, not to the component's plan, and does
    not credit the component. **It cannot see a dependency named by phase title
    alone** — that is the prose-only worklist's job.
    """
    for declaration in declarations:
        if declaration.disposition != LINE_RESOLVES:
            continue
        # Longest-prefix against the KNOWN components, never a positional
        # split: a nested component's `roadmap.md` sliced at [1:3] credits a
        # link into the nested component to its PARENT, and the prose
        # naming the parent then reads as satisfied by a link that is not it.
        linked = set()
        for link in declaration.graph_links():
            if link.node_id.split(":", 1)[0] in DOCUMENT_NODE_KINDS:
                # A research paper under `service/gamma/research/` resolves —
                # it is a satisfied `artifact:` edge — but it is not a link to
                # `service/gamma`'s plan. Crediting the component for it would
                # let prose naming the component read as linked when no phase
                # of it is, which is the exact hole this check exists to name.
                continue
            owners = [p for p in component_paths if link.resolved.startswith(p + "/")]
            if owners:
                # LONGEST, not every match. `workload/beta/old/x.md` is prefixed
                # by both `workload/beta` and `workload/beta/old`; taking both
                # credits the parent for a link into its child, which is the
                # defect the positional split had and is not an improvement on it.
                linked.add(max(owners, key=len).removeprefix("development/"))
        named = {
            match.group("slug")
            for match in COMPONENT_SLUG_RE.finditer(declaration.prose)
            if f"development/{match.group('slug')}" in component_paths
        }
        missing = sorted(named - linked)
        if not missing:
            continue
        collector.add_finding(
            DEPENDENCY_PROSE_LINK_MISMATCH,
            SECTION_DEPENDS_GRAPH,
            f"`**Depends on:**` prose names {', '.join(f'`{slug}`' for slug in missing)}, "
            "which the line's links do not",
            Provenance(declaration.roadmap, declaration.line),
            expected="every dependency the prose names also written as a resolving link",
            detail=(
                "Linked components on this line: "
                + (", ".join(f"`{slug}`" for slug in sorted(linked)) or "none")
                + ". Reported, never reconciled: which of the two the owner meant is a "
                "planning judgement. Named by phase title alone, a prose dependency is "
                "invisible to this check by construction."
            ),
        )


def detect_cycles(edges: list[Edge], collector: Collector) -> list[list[str]]:
    """Report cycles in the dependency graph, each naming its closing edge.

    Reported, never resolved. **A cycle is a real finding about the plan** and
    choosing which edge to remove is a sequencing decision that belongs to the
    operator in ``sprints.md``.

    Depth-first over a sorted adjacency, so the same corpus yields the same
    cycles in the same order. Each cycle is reported once — a three-node cycle
    is reachable from all three of its members, and three rows for one finding
    is how a section stops being read.

    **What it guarantees, precisely: an acyclic graph reports nothing, and a
    graph with any cycle reports at least one — so "the report is empty" always
    means "acyclic".** It does NOT enumerate every simple cycle, and the earlier
    wording of this docstring claimed it did. Two known and TESTED blind spots,
    both consequences of visiting each node once (the alternative is exponential
    in the worst case, for a report a human reads):

    * A cycle whose nodes were all finished before an edge into it is examined
      is not separately reported. Measured on the complete graph over
      ``{A, B, C}``: ``A↔B``, ``A→B→C``, and ``B↔C`` are reported and ``A↔C`` is
      not, though the ``A↔C`` edges are both named inside the reported rows.
    * The dedupe key is the cycle's NODE SET, so two distinct cycles over the
      same nodes — the same pair declared on two different roadmap lines —
      collapse to one row naming one closing edge.

    Neither weakens the phase's requirement, which is that the graph is acyclic
    or a cycle is named: an operator handed one cycle in a tangle re-sequences
    and re-runs, and the run is idempotent. Stated here because a reader
    building on "every cycle" would build on something untrue.
    """
    adjacency: dict[str, list[Edge]] = {}
    for edge in edges:
        if edge.kind != "depends_on":
            continue
        adjacency.setdefault(edge.source, []).append(edge)
    for bucket in adjacency.values():
        bucket.sort(key=lambda e: (e.target, e.provenance.file, e.provenance.line))

    seen: set[frozenset[str]] = set()
    cycles: list[list[str]] = []
    colour: dict[str, int] = {}  # 1 = on the stack, 2 = finished

    def walk(start: str) -> None:
        stack: list[tuple[str, int]] = [(start, 0)]
        path: list[str] = [start]
        colour[start] = 1
        while stack:
            node, position = stack[-1]
            bucket = adjacency.get(node, [])
            if position >= len(bucket):
                colour[node] = 2
                stack.pop()
                path.pop()
                continue
            stack[-1] = (node, position + 1)
            edge = bucket[position]
            target = edge.target
            if colour.get(target) == 1:
                cycle = path[path.index(target) :]
                key = frozenset(cycle)
                if key not in seen:
                    seen.add(key)
                    cycles.append(list(cycle))
                    _report_cycle(cycle, edge, collector)
                continue
            if colour.get(target) == 2:
                continue
            colour[target] = 1
            path.append(target)
            stack.append((target, 0))

    for node in sorted(adjacency):
        if colour.get(node) is None:
            walk(node)
    return cycles


def _report_cycle(cycle: list[str], closing: Edge, collector: Collector) -> None:
    collector.add_finding(
        DEPENDENCY_CYCLE,
        SECTION_DEPENDS_GRAPH,
        f"the dependency graph has a cycle, closed by `{closing.source}` → "
        f"`{closing.target}`",
        closing.provenance,
        expected="an acyclic dependency graph",
        detail=(
            "Cycle: "
            + " → ".join(f"`{node}`" for node in cycle + [cycle[0]])
            + ". Reported and never resolved — which edge to remove is a sequencing "
            "decision, and the sprint file is the operator's."
        ),
    )

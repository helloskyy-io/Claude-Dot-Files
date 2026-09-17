"""Data model for the plan extractor.

Every node, edge and finding carries the file and the line it was read from.
Provenance at node granularity is what makes a report a worklist rather than a
number — see the phase doc's requirement 1.

Nothing in this module imports Django. The extractor is a pure function of a
checkout (requirement 1: no service, no database, no network call), and keeping
the model importable without a settings module is what makes that testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


# ---------------------------------------------------------------------------
# Finding codes
# ---------------------------------------------------------------------------
#
# UPPER_SNAKE_CASE, mirroring the API Standard's reserved-error-code convention.
# A code is stable vocabulary: downstream phases (The Dependency Contract, The
# Decisions That Sit) filter on these, so renaming one is a contract change.

# -- Layer 1: nothing is silently dropped ----------------------------------
UNPARSED_LINE = "UNPARSED_LINE"
UNCLASSIFIED_FILE = "UNCLASSIFIED_FILE"
UNCLASSIFIED_PHASE_SHAPED = "UNCLASSIFIED_PHASE_SHAPED"
COMPONENT_SHAPED_NO_ROADMAP = "COMPONENT_SHAPED_NO_ROADMAP"
COMPONENT_NO_STATUS = "COMPONENT_NO_STATUS"
# A file the walk found and the reader could not open. Distinct from
# UNCLASSIFIED_FILE, which is a file that WAS read and matched no class: the
# remedies differ, and a downstream phase filtering on one must not catch the
# other.
FILE_UNREADABLE = "FILE_UNREADABLE"
# Two inputs derived the SAME node id, so one of them is invisible to every
# consumer that treats `id` as a primary key. Component and phase ids are keyed
# on a path and cannot collide; a sprint id is keyed on its heading text and can.
# A collision is the never-silently-drop rule failing at the NODE layer — the
# graph is smaller than the corpus and nothing says so.
NODE_ID_COLLISION = "NODE_ID_COLLISION"
# A roadmap heading section carries an `~Nh` figure that the stated attribution
# method cannot bind to a single phase. Reported with file and line and NEVER
# resolved: attributing it would be authoring an hour figure, which this phase
# is explicitly forbidden to do.
HOURS_UNATTRIBUTED = "HOURS_UNATTRIBUTED"

# -- Layer 2: the corpus disagrees with itself -----------------------------
ORPHAN_NOT_DECLARED = "ORPHAN_NOT_DECLARED"
DECLARED_NOT_ORPHAN = "DECLARED_NOT_ORPHAN"
SPRINT_MARKER_DISAGREES = "SPRINT_MARKER_DISAGREES"
HOURS_DISAGREE = "HOURS_DISAGREE"
EDGE_RESOLVES_TO_NO_NODE = "EDGE_RESOLVES_TO_NO_NODE"
PATH_ESCAPES_ROOT = "PATH_ESCAPES_ROOT"

# -- Layer 3: tracked stores ------------------------------------------------
TRACKED_CORE_FIELD_MISSING = "TRACKED_CORE_FIELD_MISSING"
TRACKED_ITEM_UNPARSEABLE = "TRACKED_ITEM_UNPARSEABLE"
TRACKED_ID_MALFORMED = "TRACKED_ID_MALFORMED"
TRACKED_COMPONENT_UNRESOLVED = "TRACKED_COMPONENT_UNRESOLVED"
TRACKED_ANCHOR_UNRESOLVED = "TRACKED_ANCHOR_UNRESOLVED"
TRACKED_TARGET_UNRESOLVED = "TRACKED_TARGET_UNRESOLVED"
TRACKED_DUPLICATE_FIELD = "TRACKED_DUPLICATE_FIELD"
# A whole store missing is a different remedy from one item being malformed —
# scaffold the folder vs fix the file — so it is a different code.
TRACKED_STORE_ABSENT = "TRACKED_STORE_ABSENT"
TRACKED_CONTRACT_MISMATCH = "TRACKED_CONTRACT_MISMATCH"

# -- Layer 4: the §8 amendment-surface census -------------------------------
AMENDMENT_SECOND_SURFACE = "AMENDMENT_SECOND_SURFACE"
AMENDMENT_SURFACE_SPENT = "AMENDMENT_SURFACE_SPENT"
AMENDMENT_UNCLASSIFIABLE = "AMENDMENT_UNCLASSIFIABLE"

# -- Layer 5: the five founding measurements --------------------------------
MEASUREMENT_DIFFERS = "MEASUREMENT_DIFFERS"
# A markdown link written against the canonical checkout's host path
# (the corpus's declared canonical checkout). It resolves on a host that follows
# the convention and nowhere else — a worktree, a runner, a clone. The resolver
# reads through the prefix so the GRAPH is correct from any checkout; the LINK
# is still wrong, and its owner fixes it. Reported with file and line, never
# rewritten: this component is read-only outside its own folder.
LINK_HOST_ABSOLUTE = "LINK_HOST_ABSOLUTE"

# -- Layer 6: the dependency contract ---------------------------------------
#
# The Dependency Contract reads `**Depends on:**` lines into edges. Its
# worklists are the phase's stated deliverable: a roadmap that declares no
# dependency, and one that declares it in prose the parser cannot read, have
# DIFFERENT remedies — authoring versus converting — so they are different codes
# and different sections. Collapsing them would hand one worklist to two
# audiences.
DEPENDENCY_UNDECLARED = "DEPENDENCY_UNDECLARED"
# A declaration the parser READ and the ruled format does not sanction — a
# second spelling (`**Dependencies:**`, 11 roadmaps) or a marker mid-paragraph
# (2 more roadmaps, one of them carrying a resolving link; 13 in total). Reported so the corpus
# converges on one shape, and NEVER dropped: refusing to read a recorded
# dependency in order to enforce a formatting preference is the worse of the two
# failures, and it would send those owners the "go author one" remedy for a
# dependency they already wrote.
DEPENDENCY_MARKER_NON_CONFORMING = "DEPENDENCY_MARKER_NON_CONFORMING"
DEPENDENCY_PROSE_ONLY = "DEPENDENCY_PROSE_ONLY"
# Prose naming a dependency the line's links omit. Reported only on a line that
# ALREADY resolves — on a line with no resolvable link every prose name would
# fire, duplicating the prose-only worklist row for the same roadmap.
DEPENDENCY_PROSE_LINK_MISMATCH = "DEPENDENCY_PROSE_LINK_MISMATCH"
# A cycle in the dependency graph, naming the two entries whose edge closes it.
# Reported, never resolved: choosing which edge to remove is a sequencing
# decision and it belongs to the operator in sprints.md.
DEPENDENCY_CYCLE = "DEPENDENCY_CYCLE"


# -- Layer 7: own phases, referenced phases and edge states ------------------
#
# Rule 9 derives satisfaction from what the TARGET is — a phase from its rule-8
# status marker — so a phase attributed to the wrong owner reads its status off
# the wrong entry. Every code here names a distinct remedy.
#
# A component's phase ENTRIES (rule 8's heading + `**Implementation:**` line, or
# the legacy checkbox-list form) disagree with the conforming phase documents on
# its own disk: a linked document that is not there, or a document nothing
# links. Reported per component, never absorbed — widening the ownership
# predicate until the number reads zero would delete the findings to tidy a
# count.
PHASE_OWNERSHIP_DISAGREES_WITH_DISK = "PHASE_OWNERSHIP_DISAGREES_WITH_DISK"
# An inline phase heading — rule-8 marker, no phase doc — carrying no explicit
# `<a id="…">`. Nothing can depend on it safely: a generated slug dies the next
# time the heading is reworded, and the standard makes the explicit id the
# phase's identity.
PHASE_ANCHOR_MISSING = "PHASE_ANCHOR_MISSING"
# A phase document named by MORE THAN ONE phase entry — two entries in one
# roadmap, or entries in two roadmaps. Ownership reads a status off exactly one
# entry, so the second claim is the one whose status is silently never read.
# The first claim (in file order, then roadmap order) wins and the row names
# both, so an owner can delete the one that is wrong.
PHASE_CLAIMED_TWICE = "PHASE_CLAIMED_TWICE"
# A dependency whose TARGET does not resolve — a file that is not there, an
# anchor naming no phase entry, a standard whose section has moved. **Its own
# code, distinct from an unsatisfied edge**, because the two have different
# owners: a broken edge is a defect in the corpus; an unsatisfied one is work
# not yet done. Rule 9: "the two must not render alike."
DEPENDENCY_EDGE_BROKEN = "DEPENDENCY_EDGE_BROKEN"
# A dependency whose target resolves but whose satisfaction rule 9 does not
# define — a whole component rather than a phase, or a phase whose entry carries
# no status marker. Reported rather than guessed: a satisfaction the tool made
# up would render as an authoritative colour.
DEPENDENCY_TARGET_UNDERIVABLE = "DEPENDENCY_TARGET_UNDERIVABLE"
# A `**Depends on:**` marker inside a PHASE DOCUMENT. Rule 9 names one carrier,
# the roadmap; the line is reported with the entry that should carry it, and it
# is NEVER read as an edge — parsing it would make the phase doc a second
# authoring surface, which is the drift rather than the fix.
DEPENDENCY_IN_PHASE_DOC = "DEPENDENCY_IN_PHASE_DOC"
# The standalone token with a qualifier — `Nothing hard`, `Nothing (greenfield)`
# — which is a scoped declaration wearing the standalone one's clothes.
DEPENDENCY_QUALIFIED_NONE = "DEPENDENCY_QUALIFIED_NONE"
# A dependency link whose text cites a phase by NUMBER (`Phase 0`), which rule 4
# forbids in anything newly written. Separate from the one-carrier finding on
# the same line: bundling hands an owner three decisions in one row.
DEPENDENCY_CITES_BY_NUMBER = "DEPENDENCY_CITES_BY_NUMBER"

# -- Edge states ------------------------------------------------------------
#
# Carried on a `depends_on` edge in the artifact and NOWHERE in the corpus.
# Rule 9: satisfaction "is never written on the edge" — the roadmap line — and
# a computed value in the artifact is admissible only because it is derived in
# the same pass from the same forward edges, never authored.
#
# Four states, and no consumer may collapse any pair of them. BROKEN and
# UNSATISFIED are the pair the phase exists to separate; UNDERIVABLE is the
# honest fourth, for a target the rule gives no derivation for.
EDGE_SATISFIED = "satisfied"
EDGE_UNSATISFIED = "unsatisfied"
EDGE_BROKEN = "broken"
EDGE_UNDERIVABLE = "underivable"
EDGE_STATES = frozenset({EDGE_SATISFIED, EDGE_UNSATISFIED, EDGE_BROKEN, EDGE_UNDERIVABLE})

# -- Phase status, as derived from the owning roadmap entry -------------------
#
# The four rule-8 markers, and two states the legacy checkbox form can express
# that the markers cannot. `DEPRECATED` is rule 5's `[~]` / `DEPRECATED` prefix.
# An entry with NO marker leaves the status empty, and an empty status is what
# makes an edge UNDERIVABLE rather than silently unsatisfied.
STATUS_COMPLETE = "COMPLETE"
STATUS_IN_PROGRESS = "IN PROGRESS"
STATUS_PLANNED = "PLANNED"
STATUS_NOT_SCHEDULED = "NOT SCHEDULED"
STATUS_DEPRECATED = "DEPRECATED"
#: The legacy `[ ]` — not complete, and the form cannot say which of the three
#: unfinished markers it would be. Unsatisfied either way.
STATUS_UNCHECKED = "UNCHECKED"


# Sections of the report, in emission order. The unparsed-input section is
# FIRST, deliberately — the phase doc calls it the spine.
SECTION_UNPARSED = "lines I could not parse"
SECTION_UNCLASSIFIED = "files I could not classify"
SECTION_DERIVED = "declarations that disagree with derivation"
SECTION_TRACKED = "tracked-store findings"
SECTION_AMENDMENTS = "amendment surfaces outside tracked/standards/"
SECTION_MEASUREMENTS = "the five founding measurements"
SECTION_LINKS = "graph edges that resolve to no node"
#: Sits BEFORE the unresolvable-edge section: a link that only resolves on one
#: host is the class those five vanishing edges were the symptom of.
SECTION_HOST_ABSOLUTE = "links written as host-absolute paths"
#: The dependency sections sit AFTER the unresolvable-link section, deliberately:
#: a worklist is only trustworthy once a link pointing at nothing is a named
#: finding, so the reader meets the broken links before the counts derived
#: against them.
SECTION_DEPENDS_GRAPH = "dependency-contract findings"
SECTION_DEPENDS_PROSE = "roadmaps declaring a dependency in prose only"
SECTION_DEPENDS_UNDECLARED = "roadmaps declaring no dependency a parser can read"


@dataclass(frozen=True, order=True)
class Provenance:
    """Where a thing was read from.

    ``line`` is 1-indexed. ``line == 0`` means "the file as a whole" — used for
    a finding about a file's existence or absence rather than about any line in
    it (a roadmap-less component directory, an unclassifiable file).
    """

    file: str
    line: int = 0

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.file}:{self.line}" if self.line else self.file


@dataclass(frozen=True)
class Finding:
    """One named disagreement, with the provenance that makes it actionable.

    ``expected`` states the shape the parser was looking for. Requirement 2
    binds it for unparsed input: a finding that says "could not parse" without
    saying what was expected is not a worklist entry.
    """

    code: str
    section: str
    summary: str
    provenance: Provenance
    expected: str = ""
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "section": self.section,
            "summary": self.summary,
            "file": self.provenance.file,
            "line": self.provenance.line,
            "expected": self.expected,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class Node:
    """A graph node — a component, a phase, a sprint or a sprint item."""

    id: str
    kind: str  # component | phase | standard | artifact | sprint | sprint_item
    label: str
    provenance: Provenance
    attrs: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "file": self.provenance.file,
            "line": self.provenance.line,
            "attrs": self.attrs,
        }


@dataclass(frozen=True)
class Edge:
    """A directed graph edge, carrying the line the link was read from.

    ``target_path`` is the repo-relative path the link resolved to, or ``""``
    when the link could not be resolved inside the checkout root. An edge whose
    ``target`` names no node is reported (requirement: the one link class this
    phase owns) — it is never dropped.
    """

    source: str
    target: str
    kind: str  # schedules | plans | references | contains | depends_on
    provenance: Provenance
    target_path: str = ""
    #: One of :data:`EDGE_STATES` on a ``depends_on`` edge, ``""`` on every
    #: other kind. Derived from what the target IS, in one pass, after every
    #: node exists — see :func:`~.dependencies.derive_edges`.
    state: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "kind": self.kind,
            "file": self.provenance.file,
            "line": self.provenance.line,
            "target_path": self.target_path,
            "state": self.state,
        }


@dataclass
class Collector:
    """Accumulates nodes, edges and findings during a run.

    A parser NEVER returns a shorter result in place of a finding — it appends
    the finding and carries on. That is the never-silently-drop discipline in
    one object.
    """

    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    _node_ids: set[str] = field(default_factory=set, repr=False)

    def add_node(self, node: Node) -> None:
        """Append a node, reporting a duplicate id rather than admitting it.

        The check is here, on the one door every node goes through, rather than
        on the one id derivation known to be collidable today. A future node
        kind whose id is derived from anything but a unique path inherits the
        guard instead of re-discovering the defect.
        """
        if node.id in self._node_ids:
            self.add_finding(
                NODE_ID_COLLISION,
                SECTION_UNPARSED,
                f"two inputs derive the same node id `{node.id}`; "
                f"the second is invisible to any consumer keyed on it",
                node.provenance,
                expected="a node id unique across the graph",
                detail=(
                    f"Node kind: {node.kind}. Both nodes are emitted — the collision "
                    "is reported rather than deduplicated, because which of the two "
                    "is the real one is a corpus question, not a parser one."
                ),
            )
        self._node_ids.add(node.id)
        self.nodes.append(node)

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)

    def add_finding(
        self,
        code: str,
        section: str,
        summary: str,
        provenance: Provenance,
        expected: str = "",
        detail: str = "",
    ) -> None:
        self.findings.append(
            Finding(
                code=code,
                section=section,
                summary=summary,
                provenance=provenance,
                expected=expected,
                detail=detail,
            )
        )

    def node_ids(self) -> set[str]:
        return {n.id for n in self.nodes}


@dataclass(frozen=True)
class Measurement:
    """One structural figure about a corpus, under a stated method.

    ``derived`` is what this run's ``method`` yields. A measurement is a
    method plus a figure-on-the-day and never a target: the population is the
    corpus's, it should move as the corpus is fixed, and a fixed number would
    hide that.

    ``recorded`` and ``agrees`` survive for a corpus that carries its own
    baseline to compare against — its planning may state a figure the tool
    then reproduces. The tool never edits a recorded figure and never authors
    a replacement for it.
    """

    name: str
    method: str
    derived: str
    recorded: str = ""
    agrees: bool = True
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

"""The extractor: a pure function of a checkout path.

No service, no database, no network call. ``git`` is invoked as a subprocess
against the checkout itself (see :mod:`.provenance`), which is reading the active
artifact rather than reaching out.

**Nothing is written here.** ``plan-graph.json`` is requirement 1's deliverable
as a SHAPE — :func:`extract` returns it, and ``cli.py`` writes it. One
derivation feeds all four committed artifacts (the graph, the consistency
report, the decisions page, the viewer's inputs) and the ``serve`` verb: the
result carries the parsed objects the pages render from, so no page walks the
corpus a second time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import (
    amendments,
    codified,
    contract,
    dependencies,
    derivations,
    discovery,
    measurements,
    phase_docs,
    provenance,
    roadmaps,
    sprints,
    tracked,
)
from .model import (
    EDGE_BROKEN,
    EDGE_SATISFIED,
    EDGE_UNDERIVABLE,
    EDGE_UNSATISFIED,
    PHASE_CLAIMED_TWICE,
    Collector,
    Edge,
    Finding,
    Measurement,
    Node,
    Provenance,
    SECTION_AMENDMENTS,
    SECTION_DEPENDS_GRAPH,
    SECTION_DEPENDS_PROSE,
    SECTION_DEPENDS_UNDECLARED,
    SECTION_DERIVED,
    SECTION_HOST_ABSOLUTE,
    SECTION_LINKS,
    SECTION_MEASUREMENTS,
    SECTION_TRACKED,
    SECTION_UNCLASSIFIED,
    SECTION_UNPARSED,
)

#: Report sections in emission order. The unparsed-input section is FIRST,
#: deliberately: a parser that skips what it does not understand produces a graph
#: that is quietly smaller than the corpus, and nothing downstream can tell "no
#: such edge" from "I could not read that line."
SECTION_ORDER: tuple[str, ...] = (
    SECTION_UNPARSED,
    SECTION_UNCLASSIFIED,
    SECTION_DERIVED,
    SECTION_TRACKED,
    SECTION_AMENDMENTS,
    codified.SECTION_CODIFIED,
    SECTION_MEASUREMENTS,
    SECTION_HOST_ABSOLUTE,
    SECTION_LINKS,
    SECTION_DEPENDS_GRAPH,
    SECTION_DEPENDS_PROSE,
    SECTION_DEPENDS_UNDECLARED,
)

#: Contract version of the emitted ``plan-graph.json`` shape. Distinct from the
#: Tracked Items §7 contract, which versions the STORES this tool reads.
#: Bumped to "2" by The Dependency Contract: the artifact gained `depends_on`
#: edges and a `dependency_accounting` block. A consumer pinned to "1" is
#: reading a graph that has no edges for two thirds of the corpus and no record
#: of which roadmaps those are.
#:
#: Bumped to "3" by Own Phases, Referenced Phases and Edge States: a component
#: node carries `owned_phases` and `referenced_phases`; a phase node carries
#: the `status` read off its owning entry; `standard` and `artifact` node
#: kinds and a `references` edge kind exist; every edge carries `state`, and on a
#: `depends_on` edge it is one of four values a consumer must not collapse. A
#: consumer pinned to "2" colours by a status it read off the wrong owner.
GRAPH_SCHEMA_VERSION = "3"


@dataclass
class ExtractionResult:
    #: The resolved checkout the run read. Carried so a consumer that resolves
    #: paths against it (the decisions page's anchor and component checks)
    #: reads the SAME root, rather than being handed one that may differ.
    root: Path
    graph: dict[str, Any]
    findings: list[Finding]
    rows: list[Measurement]
    halted: str
    counts: dict[str, int]
    # ---- the producer half of the seam The Decisions That Sit consumes -----
    #
    # This phase owns the READER; the page that renders what owes a ruling is
    # its own phase. Carrying the parsed objects on the result is what keeps
    # that ONE derivation: a consumer that re-parsed the stores, or re-derived
    # the orphan set, would put two answers to one question on one page — the
    # failure this package's own `_sprint_linked_paths` comment names.
    #
    # In-process objects, never serialised: `graph` remains the artifact shape.
    stores: tracked.TrackedStores = field(default_factory=tracked.TrackedStores)
    components: list[roadmaps.Component] = field(default_factory=list)
    sprint_doc: sprints.SprintsDocument | None = None
    derived_orphans: frozenset[str] = frozenset()
    declared_orphans: frozenset[str] = frozenset()
    #: One row per roadmap: resolves, excepted, or named on one of the two
    #: worklists. The requirement is that NOTHING falls through silently, and a
    #: table that covers every roadmap is the only shape in which that is
    #: checkable rather than asserted.
    dependency_accounting: list[dependencies.Accounting] = field(default_factory=list)
    dependency_declarations: list[dependencies.Declaration] = field(default_factory=list)

    def findings_by_section(self) -> dict[str, list[Finding]]:
        grouped: dict[str, list[Finding]] = {section: [] for section in SECTION_ORDER}
        for finding in self.findings:
            grouped.setdefault(finding.section, []).append(finding)
        return grouped


def _finding_sort_key(finding: Finding) -> tuple[int, str, int, str]:
    """Report order: section, then file, then line, then code.

    A finding with an unknown section sorts last rather than raising — an
    unknown section is itself a defect, and crashing the page over it would
    lose every other row.
    """
    section_rank = SECTION_ORDER.index(finding.section) if finding.section in SECTION_ORDER else 99
    return (section_rank, finding.provenance.file, finding.provenance.line, finding.code)


def _sprint_linked_paths(root: Path) -> tuple[frozenset[str], sprints.SprintsDocument, Collector]:
    """First pass over ``sprints.md``, so discovery can apply the phase-shape test.

    The sprint parser owns the read of what a sprint item links to. Discovery
    consumes it rather than computing its own — a second source of the same edge
    is how two answers to one question get into a graph.
    """
    scratch = Collector()
    document = sprints.parse_sprints(root, scratch)
    return frozenset(document.linked_paths), document, scratch


def extract(corpus_root: str | Path) -> ExtractionResult:
    """Read the planning corpus and derive the graph plus every finding."""
    root = Path(corpus_root).resolve()
    collector = Collector()

    linked_paths, sprint_doc, sprint_collector = _sprint_linked_paths(root)
    collector.findings.extend(sprint_collector.findings)

    # Read ONCE per derivation: the corpus states its own shape, and two

    # reads could disagree if the file changed underneath a long run.

    corpus_contract = contract.load(root)

    discovered = discovery.run_discovery(
        root, collector, sprint_linked=linked_paths, contract=corpus_contract
    )

    roadmap_paths = [d.path for d in discovered if d.classification == discovery.ROADMAP]
    phase_paths = {
        d.path
        for d in discovered
        if d.classification == discovery.PHASE_DOC or d.nearest == discovery.PHASE_DOC
    }

    components = roadmaps.parse_all_roadmaps(root, roadmap_paths, collector)
    # Conforming FILENAMES only — discovery's PHASE_DOC class, not its
    # phase-shaped tail — so a roadmap claiming a misnamed document is a
    # finding rather than a match. Set here because discovery owns the walk.
    conforming = {d.path for d in discovered if d.classification == discovery.PHASE_DOC}
    for component in components:
        component.on_disk = {p for p in conforming if p.rsplit("/", 1)[0] == component.path}

    # The entry that OWNS each phase, keyed by node id. A phase's status is
    # read off this entry and nowhere else — rule 9 derives satisfaction from
    # the target's rule-8 marker, and the whole point of the owned/referenced
    # split is that the marker is read off the RIGHT entry.
    entry_of: dict[str, tuple[roadmaps.Component, roadmaps.PhaseRef]] = {}
    for component in components:
        for ref in component.owned:
            first = entry_of.setdefault(ref.node_id, (component, ref))
            if first[0] is component:
                continue
            # Two ROADMAPS claim one document — `Component.owns` is a directory
            # prefix, so a parent roadmap can name a document under a nested
            # component's directory. The first roadmap in path order wins the
            # node's status; the second is a finding, not a silent loser.
            collector.add_finding(
                PHASE_CLAIMED_TWICE,
                SECTION_DERIVED,
                f"phase document `{ref.path.rsplit('/', 1)[-1]}` is named by an entry in "
                f"`{component.roadmap}` and by one in `{first[0].roadmap}:{first[1].line}`, "
                "which the graph reads the status off",
                Provenance(component.roadmap, ref.line),
                expected="each phase document named by exactly one phase entry, in one roadmap",
                detail=(
                    "Reported rather than resolved: which roadmap owns the document is the "
                    "owners' decision, and the graph must not pick by path order silently."
                ),
            )

    # ---- nodes -----------------------------------------------------------
    for component in components:
        collector.add_node(
            Node(
                id=component.node_id,
                kind="component",
                label=component.label,
                provenance=Provenance(component.roadmap, component.status_line or 1),
                attrs={
                    "status": component.status_text or "",
                    "retired": component.retired,
                    "path": component.path,
                    # Both DERIVED, both from the same walk, neither authored
                    # anywhere a human edits — which is the only reason a second
                    # field holding a computed value is admissible under rule 9.
                    "owned_phases": [ref.node_id for ref in component.owned],
                    "referenced_phases": [ref.node_id for ref in component.referenced],
                },
            )
        )
    for path in sorted(phase_paths):
        owner = entry_of.get(f"phase:{path}")
        collector.add_node(
            Node(
                id=f"phase:{path}",
                kind="phase",
                label=path.rsplit("/", 1)[-1],
                provenance=Provenance(path, 1),
                attrs={
                    "component": path.rsplit("/", 1)[0],
                    # Empty when no entry owns the document, or the owning
                    # entry carries no marker. Empty is a state, not a default:
                    # it is what makes an edge onto this phase UNDERIVABLE.
                    "status": owner[1].status if owner else "",
                    "owner": owner[0].path if owner else "",
                    "entry_line": owner[1].line if owner else 0,
                    "entry_shape": owner[1].shape if owner else "",
                },
            )
        )
    # A phase that lives inline in its roadmap — rule 8's small phase with no
    # document — is a node too, keyed on its explicit anchor, carrying its
    # heading's marker. That is what lets a dependency on it derive from the
    # PHASE's status rather than its component's status line.
    for component in components:
        for ref in component.owned:
            if not ref.inline:
                continue
            collector.add_node(
                Node(
                    id=ref.node_id,
                    kind="phase",
                    label=ref.name,
                    provenance=Provenance(component.roadmap, ref.line),
                    attrs={
                        "component": component.path,
                        "status": ref.status,
                        "owner": component.path,
                        "entry_line": ref.line,
                        "entry_shape": ref.shape,
                        "inline": True,
                        "anchor": ref.anchor,
                    },
                )
            )
    for sprint in sprint_doc.sprints:
        collector.add_node(
            Node(
                id=f"sprint:{sprint.name}",
                kind="sprint",
                label=sprint.name,
                provenance=Provenance(sprints.SPRINTS_REL, sprint.line),
                attrs={"marker": sprint.marker or "", "unplaced": sprint.is_unplaced},
            )
        )
        for index, item in enumerate(sprint.items):
            item_id = f"sprint_item:{sprint.name}#{index}"
            collector.add_node(
                Node(
                    id=item_id,
                    kind="sprint_item",
                    label=item.title,
                    provenance=Provenance(sprints.SPRINTS_REL, item.line),
                    attrs={
                        "checked": item.checked,
                        "layer": item.layer,
                        "hours_low": item.hours_low,
                        "hours_high": item.hours_high,
                        "needs_planning": item.needs_planning,
                        "cross_cutting": item.cross_cutting,
                        "close_out": item.is_close_out,
                        "unplaced": item.in_unplaced,
                    },
                )
            )
            collector.add_edge(
                Edge(
                    source=f"sprint:{sprint.name}",
                    target=item_id,
                    kind="contains",
                    provenance=Provenance(sprints.SPRINTS_REL, item.line),
                )
            )
            for path in item.link_paths:
                # A planning-graph edge points at a component or a phase. A
                # sprint item also links standards, guide pages and anchors;
                # those are references, not edges, and admitting them would turn
                # the one link class this phase owns into a prose-link sweep —
                # exactly the scope boundary the phase doc draws.
                if not path.startswith("development/"):
                    continue
                target = (
                    f"component:{path.rsplit('/', 1)[0]}"
                    if path.endswith("/roadmap.md")
                    else f"phase:{path}"
                )
                collector.add_edge(
                    Edge(
                        source=item_id,
                        target=target,
                        kind="schedules",
                        provenance=Provenance(sprints.SPRINTS_REL, item.line),
                        target_path=path,
                    )
                )

    for component in components:
        # `plans` is ownership; `references` is every other phase link the
        # roadmap carries. Both are in the artifact so the split is REVIEWABLE:
        # an attribution moving from one kind to the other shows in the diff,
        # which is what §1.1 committed the artifact for.
        for phase in component.owned:
            collector.add_edge(
                Edge(
                    source=component.node_id,
                    target=phase.node_id,
                    kind="plans",
                    provenance=Provenance(component.roadmap, phase.line),
                    target_path=phase.path,
                )
            )
        for phase in component.referenced:
            if not phase.path.startswith("development/"):
                continue
            collector.add_edge(
                Edge(
                    source=component.node_id,
                    target=phase.node_id,
                    kind="references",
                    provenance=Provenance(component.roadmap, phase.line),
                    target_path=phase.path,
                )
            )

    # ---- the dependency contract -----------------------------------------
    #
    # Ordered as the phase doc orders it: parse, then emit edges, then classify
    # against the node set, then account, and only THEN emit the worklists. A
    # worklist is trustworthy only once a link pointing at nothing is a named
    # finding rather than a silently-absent edge, and `report_unresolved_edges`
    # below is what makes it one.
    anchors: dependencies.AnchorIndex = {c.roadmap: c.anchors for c in components}
    declarations_by_component: dict[str, list[dependencies.Declaration]] = {}
    all_declarations: list[dependencies.Declaration] = []
    for component in components:
        parsed = dependencies.parse_declarations(root, component, collector, anchors)
        declarations_by_component[component.path] = parsed
        all_declarations.extend(parsed)
    documents, document_texts = dependencies.document_nodes(root, all_declarations, collector)
    for node in documents:
        collector.add_node(node)
    # Every node exists before any edge state is derived. Satisfaction is
    # computed here, once, from what each target IS — and never again.
    nodes_by_id = {node.id: node for node in collector.nodes}
    for edge in dependencies.derive_edges(
        all_declarations, nodes_by_id, document_texts, collector
    ):
        collector.add_edge(edge)

    node_ids = collector.node_ids()
    dependencies.classify_declarations(all_declarations, node_ids)
    accounting = dependencies.account(root, components, declarations_by_component)
    dependencies.report_worklists(accounting, collector)
    dependencies.report_prose_link_mismatch(
        all_declarations, {c.path for c in components}, collector
    )
    dependencies.detect_cycles(collector.edges, collector)

    # ---- derivations -----------------------------------------------------
    derivations.report_ownership_disagreements(components, collector)
    phase_docs_with_markers = phase_docs.report_phase_doc_markers(
        root, phase_paths, components, collector
    )
    derived_orphans, declared_orphans = derivations.derive_orphans(
        components, sprint_doc, collector
    )
    derivations.derive_sprint_markers(sprint_doc, phase_paths, collector)
    compared, unbacked = derivations.cross_check_hours(components, sprint_doc, collector)

    stores = tracked.read_stores(root, collector)
    if not stores.halted:
        derivations.check_tracked_disagreements(root, stores, collector)

    amendments.census(root, collector, corpus_contract)
    codified.check(root, collector, corpus_contract)

    # Count ITEMS that miss the §6 shape, by the flag the §6 parser sets on the
    # item itself. **Never by scanning the report for a finding code**: eight
    # sites in sprints.py emit UNPARSED_LINE and only four are §6 shape misses,
    # so "sprints.md is absent", "a checkbox sits outside every sprint" and "a
    # sprint carries no status marker" all used to inflate a row whose stated
    # method is "count items failing §6" — and a row that reports a false
    # disagreement tells a reader to go edit a human-only file to match a wrong
    # derivation. A measurement owns its predicate.
    shape_misses = sum(
        1 for sprint in sprint_doc.sprints for item in sprint.items if item.misses_shape
    )
    rows = measurements.measure(
        root,
        components,
        sprint_doc,
        shape_misses,
        derived_orphans,
        declared_orphans,
        all_declarations,
        collector,
        corpus_contract,
    )

    derivations.report_unresolved_edges(collector.edges, collector.node_ids(), collector)

    # ---- provenance ------------------------------------------------------
    inputs = sorted(
        {d.path for d in discovered}
        | {item.path for item in stores.all_items()}
        | {sprints.SPRINTS_REL}
    )
    commit = provenance.read_commit(root)

    # ONE ordering, used by both the emitted graph and the report. It was
    # written twice, two lines apart, and a tiebreaker added to one copy would
    # have made the artifact's finding order disagree with the report's while
    # both claimed to be the same worklist.
    ordered_findings = sorted(collector.findings, key=_finding_sort_key)

    graph: dict[str, Any] = {
        "schema_version": GRAPH_SCHEMA_VERSION,
        "provenance": {
            "commit": commit,
            "commit_date": provenance.read_commit_date(root),
            "input_digest": provenance.input_digest(root, inputs),
            "input_count": len(inputs),
            "tracked_contract_version": tracked.CONTRACT_VERSION,
            # ALSO in provenance, not only at the top of the graph. A consumer
            # that copies `graph["provenance"]` — `decisions/derive.py` does —
            # otherwise carries the tracked-store contract version and not the
            # one describing the shape it just copied, and the report header
            # renders provenance rather than the graph root.
            "schema_version": GRAPH_SCHEMA_VERSION,
        },
        "nodes": [node.to_dict() for node in sorted(collector.nodes, key=lambda n: n.id)],
        "edges": [
            edge.to_dict()
            for edge in sorted(
                collector.edges,
                key=lambda e: (e.source, e.target, e.kind, e.provenance.line),
            )
        ],
        "findings": [finding.to_dict() for finding in ordered_findings],
        "measurements": [row.to_dict() for row in rows],
        "dependency_accounting": [row.to_dict() for row in accounting],
        "halted": stores.halted,
    }

    counts = {
        "components": len(components),
        # Directories holding planning documents and no roadmap. A finding
        # where the corpus treats it as one; a count where it rules an
        # unplanned component conformant (contract).
        "unplanned_components": len(
            discovery.component_shaped_directories(root, [d.path for d in discovered])
        ),
        "phases": len(phase_paths),
        "sprints": len(sprint_doc.sprints),
        "sprint_items": sum(len(s.items) for s in sprint_doc.sprints),
        "checkbox_lines": sprint_doc.total_checkbox_lines,
        "outside_unplaced": sprint_doc.outside_unplaced,
        "work_items": sprint_doc.work_items,
        "tracked_items": len(stores.all_items()),
        "hour_pairs_compared": compared,
        "hour_pairs_without_roadmap_figure": unbacked,
        # The aggregate behind the per-roadmap HOURS_UNATTRIBUTED rows. Surfaced
        # because a counter no consumer reads is indistinguishable from a drop.
        "roadmap_hours_unattributed": sum(c.unattributed_hours for c in components),
        # ---- the dependency contract, as counted at build time ------------
        #
        # Neither recorded figure is inherited. The phase doc's own instruction
        # is that the count is "settled by measurement at build time".
        "dependency_declarations": len(all_declarations),
        "depends_on_edges": sum(1 for e in collector.edges if e.kind == "depends_on"),
        "roadmaps_resolving": sum(
            1 for r in accounting if r.disposition == dependencies.RESOLVES
        ),
        "roadmaps_excepted": sum(
            1 for r in accounting if r.disposition in dependencies.EXCEPTIONS
        ),
        "roadmaps_declaring_nothing": sum(
            1 for r in accounting if r.disposition == dependencies.WORKLIST_UNDECLARED
        ),
        "roadmaps_prose_only": sum(
            1 for r in accounting if r.disposition == dependencies.WORKLIST_PROSE_ONLY
        ),
        # How many declarations the parser could bind to a phase entry rather
        # than falling back to the component. Stated so the report describes the
        # coverage of the attribution rather than implying it was total.
        "declarations_attributed_to_a_phase": sum(
            1 for d in all_declarations if d.source_kind == "phase"
        ),
        # ---- own phases, referenced phases and edge states ----------------
        "phases_owned": sum(len(c.owned) for c in components),
        "phases_referenced": sum(len(c.referenced) for c in components),
        "phases_inline": sum(1 for c in components for r in c.owned if r.inline),
        "standards_depended_on": sum(1 for n in documents if n.kind == "standard"),
        "artifacts_depended_on": sum(1 for n in documents if n.kind == "artifact"),
        "edges_satisfied": sum(1 for e in collector.edges if e.state == EDGE_SATISFIED),
        "edges_unsatisfied": sum(1 for e in collector.edges if e.state == EDGE_UNSATISFIED),
        "edges_broken": sum(1 for e in collector.edges if e.state == EDGE_BROKEN),
        "edges_underivable": sum(1 for e in collector.edges if e.state == EDGE_UNDERIVABLE),
        "phase_docs_carrying_a_dependency_marker": phase_docs_with_markers,
        "findings": len(collector.findings),
    }

    return ExtractionResult(
        root=root,
        graph=graph,
        findings=ordered_findings,
        rows=rows,
        halted=stores.halted,
        counts=counts,
        stores=stores,
        components=components,
        sprint_doc=sprint_doc,
        derived_orphans=frozenset(derived_orphans),
        declared_orphans=frozenset(declared_orphans),
        dependency_accounting=accounting,
        dependency_declarations=all_declarations,
    )

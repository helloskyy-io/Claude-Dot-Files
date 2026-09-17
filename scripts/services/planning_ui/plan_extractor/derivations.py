"""Derivations — where the corpus disagrees with itself.

Three declarations the corpus currently makes BY HAND are re-derived here and
each disagreement is named: the ``sprints.md`` § Sprint: Unplaced orphan list,
each sprint's status marker, and each sprint item's hour figure against the
figure in its own component roadmap.

**The report finds disagreements; it never authors a figure.** A measurement the
tool computes from a method it states is the tool's own output. Asserting a
number whose basis is judgement — an hour estimate, a size, a status — is the
forbidden move, and that includes "helpfully" computing what an hour figure
ought to be.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import re
from pathlib import Path

from .model import (
    PATH_ESCAPES_ROOT,
    DECLARED_NOT_ORPHAN,
    EDGE_RESOLVES_TO_NO_NODE,
    HOURS_DISAGREE,
    ORPHAN_NOT_DECLARED,
    PHASE_OWNERSHIP_DISAGREES_WITH_DISK,
    SECTION_DERIVED,
    SECTION_LINKS,
    SECTION_TRACKED,
    SPRINT_MARKER_DISAGREES,
    TRACKED_ANCHOR_UNRESOLVED,
    TRACKED_COMPONENT_UNRESOLVED,
    TRACKED_TARGET_UNRESOLVED,
    Collector,
    Edge,
    Provenance,
)
from .fences import fenced_mask
from .roadmaps import Component
from . import corpus_io
if TYPE_CHECKING:  # pragma: no cover - typing only
    from .tracked import TrackedStores

from .safe_paths import PathEscape, exists_in_root, resolve_within_root
from .sprints import SPRINTS_REL, SprintsDocument

#: How the orphan set is derived, stated on the page.
ORPHAN_METHOD = (
    "a component is an orphan when no sprint item OUTSIDE § Sprint: Unplaced links "
    "to its roadmap.md by path. Three suppressions apply, each on the strength of a "
    "declaration or a shape rather than a name: a roadmap carrying a ⚫/RETIRED "
    "status line; a COORDINATION DOCUMENT — a roadmap with no phase documents of "
    "its own whose phase links point into two or more OTHER components; and the "
    "§ Sprint: Unplaced stated exclusions. The hand-maintained side of the "
    "comparison is the § Sprint: Unplaced `### Whole components` subsection alone "
    "— its sibling names phases inside components that ARE scheduled."
)


def is_coordination_document(component: Component) -> bool:
    """A roadmap that sequences OTHER components' phases and owns none itself.

    § Sprint: Unplaced states the exclusion and its reason: ``common/vm_orchestration``
    *"sequences Django, DAS and Lifecycle-Management phases into vertical slices
    and has no phases of its own. Listing it would create an entry that can never
    leave, and a queue containing items that cannot exit stops being read."*

    **The shape, not the name — and both halves of the shape are load-bearing.**

    * *No phase documents of its own* alone is not enough: ``service/logging``
      also has a roadmap and no phase docs, and it is **legitimately listed**.
      Suppressing on that clause alone would delete an entry the section
      deliberately carries.
    * *Two or more other components* is what "sequences X, Y and Z" means.
      ``common/resilience`` and ``service/monitoring`` each link exactly one
      other component's phase and are ordinary unbuilt components, not
      coordination documents.
    * ``common/gpu_operations`` links four other components' phases and is
      **not** one of these, because it owns two buildable phases of its own —
      which is exactly the distinction the section draws in prose.

    *Of its own* is read BOTH ways — claimed by an entry, or sitting in the
    directory. A roadmap whose documents no entry claims is an ownership
    finding, not a coordination document; excepting it would hide that gap
    behind the exception, which is the direction the phase doc rules against.
    """
    if component.owned or component.on_disk:
        return False
    return len(coordination_targets(component)) >= 2


def coordination_targets(component: Component) -> set[str]:
    """The OTHER components whose phases this roadmap sequences.

    **Reads the REFERENCED set, deliberately.** The coordination-document shape
    is *defined* by linking phases the roadmap does not own, so the split that
    moved foreign links out of ``owned`` had to leave them somewhere this
    predicate could still see — a fix that removed them would have stopped the
    exception firing and reported `common/vm_orchestration` as a gap that does
    not exist.

    Public because :func:`~.dependencies.account` renders these names as the
    exception's stated reason, and a second copy of the comprehension is a second
    answer that drifts the moment the threshold above moves.
    """
    return {
        p.path.rsplit("/", 1)[0]
        for p in component.referenced
        if not component.owns(p.path)
    }


def report_ownership_disagreements(components: list[Component], collector: Collector) -> None:
    """One row per component whose OWNED phases disagree with its own disk.

    ``Component.on_disk`` is the set of documents whose FILENAME matches the
    binding pattern — discovery's ``PHASE_DOC`` class, not its phase-shaped
    tail. That is what makes `common/genesis` a finding rather than a match:
    its entries claim `genesis-1a_k3s-0.md`, which discovery already reports
    as phase-shaped-and-misnamed, and ownership must not silently adopt a
    document the filename rule rejects.

    Both directions, in one row, because both are the same question — *does
    this roadmap's account of its phases match what is there* — and an owner
    fixes them in the same edit. A RETIRED component's unreferenced documents
    are expected, and the row SAYS so rather than being suppressed: suppression
    by status is how a live gap hides behind a retired label.
    """
    for component in sorted(components, key=lambda c: c.path):
        on_disk = component.on_disk
        owned_docs = {ref.path for ref in component.owned if ref.path}
        claimed_missing = sorted(owned_docs - on_disk)
        unclaimed = sorted(on_disk - owned_docs)
        if not claimed_missing and not unclaimed:
            continue
        parts: list[str] = []
        if claimed_missing:
            parts.append(
                f"{len(claimed_missing)} entry link(s) to no conforming phase document on "
                "disk: " + ", ".join(f"`{p.rsplit('/', 1)[-1]}`" for p in claimed_missing)
            )
        if unclaimed:
            parts.append(
                f"{len(unclaimed)} phase document(s) on disk that no entry claims: "
                + ", ".join(f"`{p.rsplit('/', 1)[-1]}`" for p in unclaimed)
            )
        first_line = min(
            [ref.line for ref in component.owned if ref.path in claimed_missing] or [1]
        )
        detail = (
            "Owned means named by a phase entry — rule 8's heading + `**Implementation:**` "
            "line, or the legacy checkbox-list form. A link elsewhere in the roadmap is a "
            "reference and claims nothing. Reported to the owner; never absorbed by "
            "widening the predicate."
        )
        if component.retired:
            detail = (
                "This component's status line reads RETIRED, so unreferenced documents are "
                "EXPECTED here — stated rather than suppressed, because suppression by "
                "status is how a live gap hides behind a retired label. " + detail
            )
        collector.add_finding(
            PHASE_OWNERSHIP_DISAGREES_WITH_DISK,
            SECTION_DERIVED,
            f"`{component.path.removeprefix('development/')}` owns "
            f"{len(owned_docs)} phase document(s) by its entries and "
            f"{len(on_disk)} sit on its disk — " + "; ".join(parts),
            Provenance(component.roadmap, first_line),
            expected=(
                "every conforming phase document in the directory named by exactly one "
                "phase entry, and every entry's document present"
            ),
            detail=detail,
        )

#: How a sprint's status marker is derived, per sprints.md §5.
MARKER_METHOD = (
    "🔵 NOT SCHEDULED when no item links to a phase document; 🟠 PLANNED when "
    "phase-linked items exist and none is checked; 🟡 IN PROGRESS when some are "
    "checked; ✅ COMPLETE when every item is. The recurring `Sprint close-out` gate "
    "is excluded — it is a constant in every sprint, not a work item."
)


def derive_orphans(
    components: list[Component],
    sprints: SprintsDocument,
    collector: Collector,
) -> tuple[set[str], set[str]]:
    """Derive the orphan set and report every disagreement in both directions."""
    body_links: set[str] = set()
    unplaced_links: set[str] = set()
    for sprint in sprints.sprints:
        for item in sprint.items:
            target = unplaced_links if item.in_unplaced else body_links
            target.update(item.link_paths)

    excluded = {path for path, _line in sprints.stated_exclusions}

    derived: set[str] = set()
    for component in components:
        if component.roadmap in body_links:
            continue
        if component.retired:
            continue
        if is_coordination_document(component):
            continue
        if any(component.path.endswith(suffix) for suffix in excluded):
            continue
        derived.add(component.path)

    # Only the "### Whole components" subsection. The sibling subsection —
    # "Individual phases inside components that ARE scheduled" — names phases,
    # not orphaned components, and its entries link the component roadmap for
    # navigation. Reading both as declared orphans manufactures a disagreement
    # in the second direction for every one of them.
    declared: set[str] = set()
    for item in sprints.unplaced_whole_components:
        for path in item.link_paths:
            if path.endswith("/roadmap.md"):
                declared.add(path.rsplit("/", 1)[0])

    by_path = {c.path: c for c in components}

    for path in sorted(derived - declared):
        component = by_path[path]
        collector.add_finding(
            ORPHAN_NOT_DECLARED,
            SECTION_DERIVED,
            f"component `{path}` is an orphan by derivation and the hand-maintained "
            "§ Sprint: Unplaced list does not name it",
            Provenance(component.roadmap, 1),
            expected="an entry in `development/sprints.md` § Sprint: Unplaced",
            detail=ORPHAN_METHOD,
        )

    for path in sorted(declared - derived):
        collector.add_finding(
            DECLARED_NOT_ORPHAN,
            SECTION_DERIVED,
            f"§ Sprint: Unplaced names `{path}` as unscheduled, but a sprint item "
            "outside that section links to its roadmap",
            Provenance(SPRINTS_REL, 1),
            expected="the hand-maintained list to agree with the derivation",
            detail=ORPHAN_METHOD,
        )

    return derived, declared


def derive_sprint_markers(
    sprints: SprintsDocument,
    phase_paths: set[str],
    collector: Collector,
) -> dict[str, str]:
    """Derive each sprint's marker from its items and report every disagreement."""
    derived: dict[str, str] = {}
    for sprint in sprints.sprints:
        if sprint.is_unplaced:
            continue
        items = [item for item in sprint.items if not item.is_close_out]
        phase_linked = [
            item
            for item in items
            if any(path in phase_paths for path in item.link_paths)
        ]
        if not phase_linked:
            marker = "NOT SCHEDULED"
        elif all(item.checked for item in items) and items:
            marker = "COMPLETE"
        elif any(item.checked for item in items):
            marker = "IN PROGRESS"
        else:
            marker = "PLANNED"
        derived[sprint.name] = marker

        if sprint.marker and sprint.marker != marker:
            collector.add_finding(
                SPRINT_MARKER_DISAGREES,
                SECTION_DERIVED,
                f"sprint `{sprint.name}` is marked {sprint.marker} and derives to {marker}",
                Provenance(SPRINTS_REL, sprint.marker_line or sprint.line),
                expected="a marker that follows from the items beneath it (sprints.md §5)",
                detail=MARKER_METHOD,
            )
    return derived


def _fmt_hours(low: int | None, high: int | None) -> str:
    if low is None:
        return "none"
    return f"~{low}h" if high is None else f"~{low}–{high}h"


def cross_check_hours(
    components: list[Component],
    sprints: SprintsDocument,
    collector: Collector,
) -> tuple[int, int]:
    """Compare each sprint item's hour figure with its roadmap's figure.

    Reports every pair that differs and **reports neither a corrected figure nor
    a new one**. Returns ``(pairs_compared, pairs_without_a_roadmap_figure)`` so
    the report can state the coverage of the check rather than imply it was
    total.
    """
    roadmap_hours: dict[str, tuple[int | None, int | None, str, int]] = {}
    for component in components:
        # OWNED only: the roadmap figure is the owning component's estimate for
        # its own phase — `HOURS_DISAGREE` says so in its `expected`. A figure
        # beside a foreign link was, before the split, the last roadmap parsed
        # winning a dict slot, which is not a method.
        for phase in component.owned:
            if phase.path and phase.hours_low is not None:
                roadmap_hours[phase.path] = (
                    phase.hours_low,
                    phase.hours_high,
                    component.roadmap,
                    phase.line,
                )

    compared = 0
    unbacked = 0
    for sprint in sprints.sprints:
        for item in sprint.items:
            if item.hours_low is None:
                continue
            if item.checked:
                # §6: "a delivered item carries its own stamp: `closed
                # YYYY-MM-DD · ~Nh`… the closed date and the ACTUAL hours ride
                # on the item itself." A closed item's figure is therefore what
                # the work COST; the roadmap's is what it was ESTIMATED at.
                # Those are two quantities, and reporting their difference as
                # "one figure, one home" is a false row — the rule this finding
                # enforces is about one ESTIMATE having one home.
                continue
            for path in item.link_paths:
                if path not in roadmap_hours:
                    if path.endswith(".md") and not path.endswith("/roadmap.md"):
                        unbacked += 1
                    continue
                low, high, roadmap_rel, roadmap_line = roadmap_hours[path]
                compared += 1
                if (low, high) == (item.hours_low, item.hours_high):
                    continue
                collector.add_finding(
                    HOURS_DISAGREE,
                    SECTION_DERIVED,
                    f"`{path}` carries {_fmt_hours(item.hours_low, item.hours_high)} in "
                    f"sprints.md and {_fmt_hours(low, high)} in its component roadmap",
                    Provenance(SPRINTS_REL, item.line),
                    expected="one figure, one home — hours are authored in the component roadmap",
                    detail=(
                        f"Roadmap figure read at {roadmap_rel}:{roadmap_line}. "
                        "Neither figure is corrected here and no third is authored: "
                        "authoring an hour estimate belongs to `plan-verify`."
                    ),
                )
    return compared, unbacked


def report_unresolved_edges(
    edges: list[Edge], node_ids: set[str], collector: Collector
) -> None:
    """Report a planning-graph edge that resolves to no node.

    **Scoped to graph edges only.** General prose link-rot is `doc-manager`'s;
    the corpus carries a few hundred unresolvable relative links and most of them
    are not graph edges either way. Reporting the whole set would bury the
    finding that matters inside a hygiene sweep.
    """
    # A missing SOURCE is a property of the node, not of each edge leaving it: one
    # `**Implementation:**` link pointing at a phase document that does not exist
    # yields one bad source shared by every declaration in that section. Reported
    # once, or the section fills with N rows naming one file. A missing TARGET
    # stays per-edge — each is a separately-authored link somebody must fix.
    reported_sources: set[str] = set()
    for edge in edges:
        # BOTH ends. A dependency edge's SOURCE is derived from its roadmap's
        # `**Implementation:**` link, which can itself point at a phase document
        # that does not exist — an edge leaving a node the graph does not have,
        # invisible to a target-only check.
        #
        # The TARGET end of a `depends_on` edge is NOT reported here. It is a
        # BROKEN EDGE under `DEPENDENCY_EDGE_BROKEN`, with the reason the
        # dependency contract can state (an anchor naming no entry, a standard
        # whose section moved) and this generic check cannot — and one defect
        # gets one row. The source end stays: it is a property of the roadmap's
        # own `**Implementation:**` link, not of the dependency.
        if edge.target not in node_ids and edge.kind != "depends_on":
            collector.add_finding(
                EDGE_RESOLVES_TO_NO_NODE,
                SECTION_LINKS,
                f"graph edge `{edge.source}` → `{edge.target}` has a target "
                f"(`{edge.target}`) that is no node",
                edge.provenance,
                expected="a link target that is a component or phase node in the graph",
                detail=(
                    f"Edge kind: {edge.kind}. Resolved path: "
                    f"{edge.target_path or '(unresolved)'}"
                ),
            )
        if edge.source not in node_ids and edge.source not in reported_sources:
            reported_sources.add(edge.source)
            collector.add_finding(
                EDGE_RESOLVES_TO_NO_NODE,
                SECTION_LINKS,
                f"graph edge `{edge.source}` → `{edge.target}` has a source "
                f"(`{edge.source}`) that is no node",
                edge.provenance,
                expected="an edge that leaves a component or phase node in the graph",
                # NOT `target_path` — that is the OTHER end's file, and a reader
                # sent to fix the source would be handed the target's path.
                detail=(
                    f"Edge kind: {edge.kind}. The source node is named by this "
                    "roadmap's `**Implementation:**` link and no document exists "
                    "at it; every edge leaving it shares the defect and it is "
                    "reported once."
                ),
            )


_SECTION_NUM_RE = re.compile(r"§\s*(\d+(?:\.\d+)*)")


def anchor_resolves(
    root: Path, target_rel: str, anchor: str, collector: Collector
) -> bool:
    """Whether ``anchor`` still resolves inside ``target_rel``.

    **Public because a second package consumes it.** The Decisions That Sit
    renders the ``target:``/``anchor:`` resolution as table 3's derived column,
    and it reached the single-underscore name across a package boundary — so a
    maintainer refactoring this module in isolation had no signal that anything
    outside it depended on the function. A cross-package dependency that is
    invisible until import time is a rename away from a broken page.
    """
    return anchor_resolves_in(
        corpus_io.read_text(root, target_rel, collector), anchor
    )


def anchor_resolves_in(text: str | None, anchor: str) -> bool:
    """:func:`anchor_resolves` against text a caller has ALREADY read.

    Split out so a consumer needing both the anchor check and something else
    from the same file — the vendored-mirror marker, say — reads it once. The
    two-read version passed a THROWAWAY collector to one of them, so a genuine
    read failure there was silently dropped and rendered as an ordinary result.

    Stated method: strip the leading ``§`` and any surrounding whitespace, then
    look for the literal remainder in the target's text; where the anchor is a
    bare section number (``§7``, ``§4.2``) look for that number preceded by ``§``
    anywhere in the file. A heading-anchor form (``#some-heading``) is matched
    against a slugified heading.

    **Every one of those reads is taken against the target with its fenced code
    blocks blanked.** A standard that quotes ``§7`` inside a fenced example, or
    illustrates a ``## Ratification Queue`` heading it does not have, would
    otherwise answer for an anchor that resolves to nothing — and the answer is
    ``True``, so the ``TRACKED_ANCHOR_UNRESOLVED`` finding is suppressed rather
    than raised. Measured on the live corpus before the mask was added: 16
    tracked anchors carry a resolvable target and NONE of them changes verdict,
    so this moves no figure and closes the shape.
    """
    if text is None:
        # Reported as FILE_UNREADABLE by whoever did the read. Returning False
        # here would emit TRACKED_ANCHOR_UNRESOLVED — a finding blaming the
        # anchor for a file nobody could open, which sends a reader to fix the
        # wrong thing.
        return True

    lines = text.splitlines()
    text = "\n".join(
        "" if masked else line for line, masked in zip(lines, fenced_mask(lines))
    )

    probe = anchor.strip().strip("`").lstrip("#").strip()
    if not probe:
        return False

    numbers = _SECTION_NUM_RE.findall(probe)
    if numbers and probe.lstrip("§").strip() == numbers[0]:
        return bool(re.search(rf"§\s*{re.escape(numbers[0])}\b", text))

    if probe in text:
        return True

    slug = probe.lower().replace(" ", "-")
    for line in text.splitlines():
        if not line.startswith("#"):
            continue
        heading_slug = re.sub(r"[^a-z0-9]+", "-", line.lstrip("#").strip().lower()).strip("-")
        if heading_slug == slug.strip("-"):
            return True
    return False


def check_tracked_disagreements(
    root: Path, stores: "TrackedStores", collector: Collector
) -> None:
    """Tracked-store findings that are corpus disagreements. Reports; resolves none."""
    for item in stores.items.get("candidates", []):
        raw = item.fields.get("component", "").strip().strip("`")
        if not raw:
            continue
        try:
            resolved = resolve_within_root(root, item.path, raw)
        except PathEscape as exc:
            collector.add_finding(
                PATH_ESCAPES_ROOT,
                SECTION_TRACKED,
                f"tracked candidate `component:` escapes the checkout root: {exc.raw}",
                Provenance(item.path, item.line_of("component")),
                expected="a path inside the checkout",
                detail="Reported and never opened.",
            )
            continue
        # A `component:` is authored repo-relative (`development/service/secrets`),
        # not relative to the item file. Try both readings before reporting.
        if exists_in_root(root, raw) or exists_in_root(root, resolved):
            continue
        collector.add_finding(
            TRACKED_COMPONENT_UNRESOLVED,
            SECTION_TRACKED,
            f"tracked candidate names component `{raw}`, which is not a path in the checkout",
            Provenance(item.path, item.line_of("component")),
            expected="an existing `development/<domain>/<name>` directory",
        )

    for item in stores.items.get("standards", []):
        target = item.fields.get("target", "").strip().strip("`")
        anchor = item.fields.get("anchor", "").strip().strip("`")
        if not target:
            continue
        if not exists_in_root(root, target):
            collector.add_finding(
                TRACKED_TARGET_UNRESOLVED,
                SECTION_TRACKED,
                f"tracked standards candidate targets `{target}`, which is not a file in the checkout",
                Provenance(item.path, item.line_of("target")),
                expected="an existing standards document",
            )
            continue
        if anchor and not anchor_resolves(root, target, anchor, collector):
            collector.add_finding(
                TRACKED_ANCHOR_UNRESOLVED,
                SECTION_TRACKED,
                f"tracked standards candidate anchor `{anchor}` no longer resolves in `{target}`",
                Provenance(item.path, item.line_of("anchor")),
                expected="a section or line that exists in the target standard",
                detail=(
                    "Tracked Items §4.1: an amendment with no named target and no "
                    "anchor cannot be acted on. Reported; not resolved."
                ),
            )

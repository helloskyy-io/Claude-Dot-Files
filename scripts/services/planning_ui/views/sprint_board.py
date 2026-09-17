"""The sprint board — Page 3's input: one sprint's items as nodes, and the
directed edges among them.

**Both halves of the page read this one structure.** The board draws
``items`` as nodes with ``edges`` among them; the rendered sprint beside it
lists the same ``items`` in file order, each with the line it was read from.
They cannot name different item sets because there is one list (requirement
3: *"two readings of one sprint that disagree about the item set is a defect
in the generator"*).

**An edge between two items is derived from what they schedule.** A sprint
item links a phase document and its component's roadmap; the extractor
records those as ``schedules`` edges. Item A → item B when a ``depends_on``
edge runs from something A schedules to something B schedules — and when two
items of one sprint schedule the same phase (a close-out entry that recurs,
or one phase split across two items), the edge attaches to EACH of them,
because an edge that lands on only the first of two equal readings is the
"two readings disagree" defect requirement 3 names:

- an item that schedules one or more PHASES stands for those phases;
- an item that schedules only a COMPONENT — a whole-component item — stands
  for that component;
- an item that schedules both stands for its phases only. A dependency on
  the whole component is not discharged by one of its phases, so it does not
  attach to a one-phase item.

The rolled-up edge carries the worst of its ``via`` states, as the
neighbourhood does. Nothing here decides satisfaction; it copies the state
the extractor derived.

**An item with no resolvable phase link is shown as such, never dropped.**
``linked`` is false when the item carries no ``schedules`` edge at all;
``unresolved`` lists every scheduled target that names no node. Both are
drawn distinctly by the board, because an item nothing can be derived about
is a different fact from an item with no dependencies.
"""
from __future__ import annotations

from typing import Any

from planning_ui.plan_extractor import ExtractionResult

from .neighbourhood import worst_state


def sprint_boards(result: ExtractionResult) -> dict[str, Any]:
    """Every sprint's board, keyed by sprint name, in file order."""
    graph = result.graph
    nodes_by_id = {n["id"]: n for n in graph["nodes"]}
    contains: dict[str, list[str]] = {}
    schedules: dict[str, list[dict[str, Any]]] = {}
    for edge in graph["edges"]:
        if edge["kind"] == "contains":
            contains.setdefault(edge["source"], []).append(edge["target"])
        elif edge["kind"] == "schedules":
            schedules.setdefault(edge["source"], []).append(edge)

    # The raw item line, for the rendered half of the page. The in-process
    # sprint document is the same derivation the graph's item nodes came from
    # (`extractor.py` builds both from `sprint_doc`); keyed the way the node id
    # is keyed so the two cannot be joined on anything but that derivation.
    raw_by_id: dict[str, str] = {}
    if result.sprint_doc is not None:
        for sprint in result.sprint_doc.sprints:
            for index, item in enumerate(sprint.items):
                raw_by_id[f"sprint_item:{sprint.name}#{index}"] = item.raw

    boards: dict[str, Any] = {}
    sprint_nodes = sorted(
        (n for n in graph["nodes"] if n["kind"] == "sprint"), key=lambda n: n["line"]
    )
    for sprint in sprint_nodes:
        item_ids = sorted(
            contains.get(sprint["id"], []), key=lambda i: nodes_by_id[i]["line"]
        )
        items = []
        scope: dict[str, set[str]] = {}
        for item_id in item_ids:
            node = nodes_by_id[item_id]
            targets = schedules.get(item_id, [])
            resolved = [e["target"] for e in targets if e["target"] in nodes_by_id]
            unresolved = [e["target"] for e in targets if e["target"] not in nodes_by_id]
            phases = [t for t in resolved if t.startswith("phase:")]
            components = [t for t in resolved if t.startswith("component:")]
            scope[item_id] = set(phases) if phases else set(components)
            items.append({
                "id": item_id,
                "label": node["label"],
                "raw": raw_by_id.get(item_id, ""),
                "line": node["line"],
                "checked": bool(node["attrs"].get("checked")),
                "layer": node["attrs"].get("layer"),
                "hours_low": node["attrs"].get("hours_low"),
                "hours_high": node["attrs"].get("hours_high"),
                "needs_planning": bool(node["attrs"].get("needs_planning")),
                "cross_cutting": bool(node["attrs"].get("cross_cutting")),
                "close_out": bool(node["attrs"].get("close_out")),
                "schedules": resolved,
                "unresolved": unresolved,
                "linked": bool(targets),
            })

        # Every item standing for a target, not the first: two items may
        # schedule one phase, and the edge belongs to both of them.
        items_for: dict[str, list[str]] = {}
        for item_id, targets in scope.items():
            for target in targets:
                items_for.setdefault(target, []).append(item_id)
        rolled: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for edge in graph["edges"]:
            if edge["kind"] != "depends_on":
                continue
            for source_item in items_for.get(edge["source"], ()):
                for target_item in items_for.get(edge["target"], ()):
                    if source_item == target_item:
                        continue
                    rolled.setdefault((source_item, target_item), []).append({
                        "source": edge["source"],
                        "target": edge["target"],
                        "state": edge["state"],
                        "file": edge["file"],
                        "line": edge["line"],
                    })

        boards[sprint["label"]] = {
            "id": sprint["id"],
            "name": sprint["label"],
            "marker": sprint["attrs"].get("marker", ""),
            "unplaced": bool(sprint["attrs"].get("unplaced")),
            "file": sprint["file"],
            "line": sprint["line"],
            "items": items,
            "edges": [
                {
                    "source": s,
                    "target": t,
                    "state": worst_state([v["state"] for v in vias]),
                    "via": vias,
                }
                for (s, t), vias in sorted(rolled.items())
            ],
        }
    return boards

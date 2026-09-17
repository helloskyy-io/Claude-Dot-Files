"""The component neighbourhood — Page 2's input, and the depth-limited query
over it.

**Component level, by roll-up.** The graph's ``depends_on`` edges run mostly
phase to phase. A reader asking *what does this component depend on* wants
them attributed to components, so every edge is rolled up: a phase endpoint
becomes the component that OWNS it (the phase node's ``attrs.owner``, which
Own Phases, Referenced Phases and Edge States derived so that a status is
never read off the wrong entry), a component endpoint stays itself, and a
standard or artifact endpoint stays itself under its own kind. The phase-level
edge is kept beneath the rolled-up one as ``via``, so the panel can say WHICH
phase's line the edge was read from.

**Three states a reader must not confuse, kept apart here and drawn apart in
the browser** (requirement 4):

- a component that **declares nothing** — the accounting row's disposition,
  carried on the node as ``declares``;
- an edge that **resolves to no node** — ``state: broken``; its target is
  emitted as a node of kind ``missing`` so the edge has something to be drawn
  to, and so the reader sees a hole rather than a dropped line;
- an edge whose **target is unfinished** — ``state: unsatisfied``.

The fourth edge state, ``underivable``, is carried unchanged: the extractor
refused to guess it and this module does not guess either.

**An edge from a component to itself** — one of its phases depending on
another — does not cross the component boundary and is not a neighbourhood
edge. It is kept on the node as ``internal`` so the panel can list it and so
the corpus-wide state counts still include it.
"""
from __future__ import annotations

from collections import deque
from typing import Any

from planning_ui.plan_extractor.dependencies import (
    EXCEPTIONS,
    RESOLVES,
    WORKLIST_PROSE_ONLY,
    WORKLIST_UNDECLARED,
)
from planning_ui.plan_extractor.model import (
    EDGE_BROKEN,
    EDGE_SATISFIED,
    EDGE_UNDERIVABLE,
    EDGE_UNSATISFIED,
)

#: The order a pair of rolled-up edges collapse in: one phase edge broken and
#: another satisfied between the same two components is a broken edge between
#: them. A reader chases the worst problem first, and the `via` list keeps the
#: rest.
STATE_SEVERITY = {EDGE_BROKEN: 0, EDGE_UNSATISFIED: 1, EDGE_UNDERIVABLE: 2, EDGE_SATISFIED: 3}

#: How a node's `declares` reads, from its accounting disposition. Stated as
#: a mapping so the browser matches on five words rather than on the
#: extractor's longer disposition strings.
DECLARES = {
    RESOLVES: "resolves",
    WORKLIST_UNDECLARED: "nothing",
    WORKLIST_PROSE_ONLY: "prose-only",
}


def worst_state(states: list[str]) -> str:
    return min(states, key=lambda s: STATE_SEVERITY.get(s, 99))


def _short(path: str) -> str:
    """A component's label is its path under ``development/`` — the way the
    sprint file and every roadmap name it (``common/planning_ui``)."""
    return path[len("development/"):] if path.startswith("development/") else path


def _roll_up(node_id: str, nodes: dict[str, dict]) -> str:
    """The component-level id an edge endpoint rolls up to, or the id itself."""
    node = nodes.get(node_id)
    if node is None:
        return node_id
    if node["kind"] == "phase":
        owner = node["attrs"].get("owner")
        return f"component:{owner}" if owner else node_id
    return node_id


def component_index(graph: dict[str, Any]) -> dict[str, Any]:
    """The component-level dependency graph, keyed by node id.

    Returns ``{"nodes": {id: node}, "edges": [edge], "phases": {id: phase}}``.
    Every component in the graph is a node whether or not any edge touches it
    — a component that declares nothing has no out-edges and is still the
    thing requirement 4 asks the page to count and to draw distinctly.
    ``phases`` carries the status of every phase node, read off its owning
    entry by the extractor, so the panel can list a component's own phases
    without a second read.
    """
    nodes_by_id = {n["id"]: n for n in graph["nodes"]}
    declares_by_component = {
        f"component:{row['component']}": row for row in graph["dependency_accounting"]
    }

    index_nodes: dict[str, dict[str, Any]] = {}
    for node in graph["nodes"]:
        if node["kind"] != "component":
            continue
        row = declares_by_component.get(node["id"])
        disposition = row["disposition"] if row else ""
        if disposition in EXCEPTIONS:
            declares = "excepted"
        else:
            declares = DECLARES.get(disposition, "")
        index_nodes[node["id"]] = {
            "id": node["id"],
            "kind": "component",
            "label": _short(node["attrs"].get("path", node["label"])),
            "file": node["file"],
            "line": node["line"],
            "status": node["attrs"].get("status", ""),
            "retired": bool(node["attrs"].get("retired")),
            "declares": declares,
            "disposition": disposition,
            "owned_phases": list(node["attrs"].get("owned_phases", [])),
            "internal": [],
        }

    rolled: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for edge in graph["edges"]:
        if edge["kind"] != "depends_on":
            continue
        source = _roll_up(edge["source"], nodes_by_id)
        target = _roll_up(edge["target"], nodes_by_id)
        via = {
            "source": edge["source"],
            "target": edge["target"],
            "state": edge["state"],
            "file": edge["file"],
            "line": edge["line"],
        }
        if source == target:
            if source in index_nodes:
                index_nodes[source]["internal"].append(via)
            continue
        rolled.setdefault((source, target), []).append(via)
        for endpoint in (source, target):
            if endpoint in index_nodes:
                continue
            node = nodes_by_id.get(endpoint)
            if node is None:
                # The edge's target names no node — a broken edge. It is drawn
                # to a `missing` node rather than dropped, so the reader sees
                # the hole where the target should be.
                index_nodes[endpoint] = {
                    "id": endpoint,
                    "kind": "missing",
                    "label": endpoint.split(":", 1)[-1],
                    "file": "",
                    "line": 0,
                    "status": "",
                    "retired": False,
                    "declares": "",
                    "disposition": "",
                    "owned_phases": [],
                    "internal": [],
                }
            else:
                index_nodes[endpoint] = {
                    "id": endpoint,
                    "kind": node["kind"],
                    "label": _short(node["attrs"].get("path", node["label"])),
                    "file": node["file"],
                    "line": node["line"],
                    "status": node["attrs"].get("status", ""),
                    "retired": False,
                    "declares": "",
                    "disposition": "",
                    "owned_phases": [],
                    "internal": [],
                }

    edges = [
        {
            "source": source,
            "target": target,
            "state": worst_state([v["state"] for v in vias]),
            "via": vias,
        }
        for (source, target), vias in sorted(rolled.items())
    ]
    phases = {
        n["id"]: {
            "label": n["label"],
            "file": n["file"],
            "line": n["line"],
            "status": n["attrs"].get("status", ""),
            "owner": n["attrs"].get("owner", ""),
        }
        for n in graph["nodes"]
        if n["kind"] == "phase"
    }
    return {"nodes": dict(sorted(index_nodes.items())), "edges": edges, "phases": phases}


def neighbourhood(index: dict[str, Any], component_id: str, depth: int) -> dict[str, Any]:
    """The nodes within ``depth`` edges of ``component_id``, in either
    direction, and every index edge among them.

    Breadth-first, so the returned ``order`` is nearest-first: a view that
    caps the node count keeps the nodes closest to the one the reader asked
    about. Each returned node carries its ``distance``. The browser's
    ``neighbourhood.mjs`` walks the same index the same way; this is the
    copy the tests hold to the hand-known answer.
    """
    if component_id not in index["nodes"]:
        raise KeyError(f"{component_id} is not in the neighbourhood index")
    adjacency: dict[str, set[str]] = {}
    for edge in index["edges"]:
        adjacency.setdefault(edge["source"], set()).add(edge["target"])
        adjacency.setdefault(edge["target"], set()).add(edge["source"])

    distance = {component_id: 0}
    order = [component_id]
    queue = deque([component_id])
    while queue:
        current = queue.popleft()
        if distance[current] >= depth:
            continue
        for neighbour in sorted(adjacency.get(current, ())):
            if neighbour in distance:
                continue
            distance[neighbour] = distance[current] + 1
            order.append(neighbour)
            queue.append(neighbour)

    edges = [
        e for e in index["edges"] if e["source"] in distance and e["target"] in distance
    ]
    return {"root": component_id, "depth": depth, "order": order, "distance": distance, "edges": edges}


def state_counts(graph: dict[str, Any]) -> dict[str, int]:
    """The corpus-wide counts the page states — requirement 4's three, and
    the neighbours a reader would otherwise ask about."""
    edges = [e for e in graph["edges"] if e["kind"] == "depends_on"]
    rows = graph["dependency_accounting"]
    return {
        "components": sum(1 for n in graph["nodes"] if n["kind"] == "component"),
        "components_declaring_nothing": sum(
            1 for r in rows if r["disposition"] == WORKLIST_UNDECLARED
        ),
        "components_prose_only": sum(1 for r in rows if r["disposition"] == WORKLIST_PROSE_ONLY),
        "edges_broken": sum(1 for e in edges if e["state"] == EDGE_BROKEN),
        "edges_unsatisfied": sum(1 for e in edges if e["state"] == EDGE_UNSATISFIED),
        "edges_satisfied": sum(1 for e in edges if e["state"] == EDGE_SATISFIED),
        "edges_underivable": sum(1 for e in edges if e["state"] == EDGE_UNDERIVABLE),
    }

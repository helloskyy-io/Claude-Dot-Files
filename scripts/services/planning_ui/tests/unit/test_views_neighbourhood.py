"""The component neighbourhood: roll-up, the three states, and the depth walk.

A miniature graph dict in the artifact's shape, built inline: the roll-up is
a pure function of that shape, and a fixture corpus would be testing the
extractor again rather than this.
"""
from __future__ import annotations

import pytest

import planning_ui.views.neighbourhood as nb


def _node(id_, kind, **attrs):
    return {"id": id_, "kind": kind, "label": id_.split(":")[-1], "file": "f.md", "line": 1, "attrs": attrs}


def _edge(source, target, state, kind="depends_on", line=1):
    return {"source": source, "target": target, "kind": kind, "state": state, "file": "r.md", "line": line, "target_path": ""}


@pytest.fixture()
def graph():
    """Three components. A owns two phases; A.p1 depends on B.p1 (satisfied)
    and on A.p2 (internal); A.p2 depends on a target that names no node
    (broken); B depends on C as a whole (underivable); C declares nothing."""
    return {
        "nodes": [
            _node("component:development/common/a", "component", path="development/common/a",
                  owned_phases=["phase:development/common/a/p1.md", "phase:development/common/a/p2.md"], status="s"),
            _node("component:development/common/b", "component", path="development/common/b", owned_phases=["phase:development/common/b/p1.md"]),
            _node("component:development/common/c", "component", path="development/common/c", owned_phases=[]),
            _node("phase:development/common/a/p1.md", "phase", owner="development/common/a", status="PLANNED"),
            _node("phase:development/common/a/p2.md", "phase", owner="development/common/a", status="COMPLETE"),
            _node("phase:development/common/b/p1.md", "phase", owner="development/common/b", status="COMPLETE"),
            _node("standard:standards/x.md", "standard"),
        ],
        "edges": [
            _edge("phase:development/common/a/p1.md", "phase:development/common/b/p1.md", "satisfied", line=10),
            _edge("phase:development/common/a/p1.md", "phase:development/common/a/p2.md", "satisfied", line=11),
            _edge("phase:development/common/a/p2.md", "phase:development/common/nowhere/p9.md", "broken", line=20),
            _edge("component:development/common/b", "component:development/common/c", "underivable", line=30),
            _edge("phase:development/common/a/p2.md", "standard:standards/x.md", "satisfied", line=21),
            _edge("component:development/common/a", "phase:development/common/a/p1.md", "", kind="plans"),
        ],
        "dependency_accounting": [
            {"component": "development/common/a", "disposition": "resolves"},
            {"component": "development/common/b", "disposition": "worklist — declares in prose only"},
            {"component": "development/common/c", "disposition": "worklist — declares nothing"},
        ],
    }


def test_phase_edges_roll_up_to_the_owning_component_and_keep_the_line(graph):
    index = nb.component_index(graph)
    a_to_b = [e for e in index["edges"] if e["source"] == "component:development/common/a" and e["target"] == "component:development/common/b"]
    assert len(a_to_b) == 1
    assert a_to_b[0]["state"] == "satisfied"
    assert a_to_b[0]["via"] == [{
        "source": "phase:development/common/a/p1.md", "target": "phase:development/common/b/p1.md",
        "state": "satisfied", "file": "r.md", "line": 10,
    }]


def test_an_edge_inside_one_component_is_internal_not_a_neighbourhood_edge(graph):
    index = nb.component_index(graph)
    a = index["nodes"]["component:development/common/a"]
    assert [v["line"] for v in a["internal"]] == [11]
    assert not any(e["source"] == e["target"] for e in index["edges"])


def test_a_broken_edge_is_drawn_to_a_missing_node_rather_than_dropped(graph):
    index = nb.component_index(graph)
    broken = [e for e in index["edges"] if e["state"] == "broken"]
    assert len(broken) == 1
    target = broken[0]["target"]
    assert target == "phase:development/common/nowhere/p9.md"
    assert index["nodes"][target]["kind"] == "missing"


def test_declares_is_read_off_the_accounting_row_never_guessed(graph):
    index = nb.component_index(graph)
    nodes = index["nodes"]
    assert nodes["component:development/common/a"]["declares"] == "resolves"
    assert nodes["component:development/common/b"]["declares"] == "prose-only"
    assert nodes["component:development/common/c"]["declares"] == "nothing"
    # a standard is not a component and carries no declaration state
    assert nodes["standard:standards/x.md"]["declares"] == ""
    # and the component's label is its path under development/
    assert nodes["component:development/common/a"]["label"] == "common/a"


def test_a_component_with_no_edges_is_still_a_node(graph):
    graph["edges"] = [e for e in graph["edges"] if "common/c" not in e["target"]]
    index = nb.component_index(graph)
    assert "component:development/common/c" in index["nodes"]


def test_the_worst_state_wins_when_two_phase_edges_roll_up_to_one(graph):
    graph["edges"].append(_edge("phase:development/common/a/p2.md", "phase:development/common/b/p1.md", "unsatisfied", line=12))
    index = nb.component_index(graph)
    a_to_b = next(e for e in index["edges"] if e["source"].endswith("/a") and e["target"].endswith("/b"))
    assert a_to_b["state"] == "unsatisfied"
    assert sorted(v["line"] for v in a_to_b["via"]) == [10, 12]
    assert nb.worst_state(["satisfied", "underivable", "broken", "unsatisfied"]) == "broken"


def test_the_walk_is_depth_limited_in_both_directions_and_nearest_first(graph):
    index = nb.component_index(graph)
    root = "component:development/common/a"
    assert nb.neighbourhood(index, root, 0)["order"] == [root]
    d1 = nb.neighbourhood(index, root, 1)
    assert set(d1["order"]) == {root, "component:development/common/b", "phase:development/common/nowhere/p9.md", "standard:standards/x.md"}
    assert all(d1["distance"][n] == 1 for n in d1["order"][1:])
    d2 = nb.neighbourhood(index, root, 2)
    assert "component:development/common/c" in d2["order"]
    assert d2["distance"]["component:development/common/c"] == 2
    assert d2["order"][0] == root and d2["order"].index("component:development/common/c") > d2["order"].index("component:development/common/b")
    # incoming direction: from c, b is one step away even though the edge points at c
    assert "component:development/common/b" in nb.neighbourhood(index, "component:development/common/c", 1)["order"]
    with pytest.raises(KeyError):
        nb.neighbourhood(index, "component:development/common/zzz", 1)


def test_the_walk_returns_only_edges_among_the_returned_nodes(graph):
    index = nb.component_index(graph)
    d1 = nb.neighbourhood(index, "component:development/common/a", 1)
    assert all(e["source"] in d1["distance"] and e["target"] in d1["distance"] for e in d1["edges"])
    assert not any(e["target"].endswith("/c") for e in d1["edges"])


def test_state_counts_are_the_three_states_and_their_neighbours(graph):
    counts = nb.state_counts(graph)
    assert counts == {
        "components": 3,
        "components_declaring_nothing": 1,
        "components_prose_only": 1,
        "edges_broken": 1,
        "edges_unsatisfied": 0,
        "edges_satisfied": 3,
        "edges_underivable": 1,
    }


def test_phases_carry_the_status_read_off_the_owning_entry(graph):
    index = nb.component_index(graph)
    assert index["phases"]["phase:development/common/a/p2.md"]["status"] == "COMPLETE"
    assert index["phases"]["phase:development/common/a/p2.md"]["owner"] == "development/common/a"

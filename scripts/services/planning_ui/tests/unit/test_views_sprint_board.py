"""The sprint board: one item list, edges from what items schedule, and an
item nothing can be derived about kept rather than dropped."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from planning_ui.views import sprint_board as sb


def _node(id_, kind, label="", line=1, **attrs):
    return {"id": id_, "kind": kind, "label": label or id_, "file": "development/sprints.md", "line": line, "attrs": attrs}


def _edge(source, target, kind, state="", line=1):
    return {"source": source, "target": target, "kind": kind, "state": state, "file": "r.md", "line": line, "target_path": ""}


@pytest.fixture()
def result():
    """One sprint, four items: #0 schedules phase a/p1; #1 schedules phase
    b/p1 (which a/p1 depends on, unsatisfied); #2 schedules component c as a
    whole (which b/p1 depends on); #3 links nothing. #0 also links a phase
    that is not in the graph."""
    graph = {
        "nodes": [
            _node("sprint:S", "sprint", "S", line=5, marker="PLANNED", unplaced=False),
            _node("sprint_item:S#0", "sprint_item", "x · A", line=10, checked=False, layer=1),
            _node("sprint_item:S#1", "sprint_item", "x · B", line=11, checked=True, layer=1),
            _node("sprint_item:S#2", "sprint_item", "x · C whole", line=12, checked=False, layer=2),
            _node("sprint_item:S#3", "sprint_item", "nothing linked", line=13, checked=False),
            _node("phase:development/common/a/p1.md", "phase", owner="development/common/a"),
            _node("phase:development/common/b/p1.md", "phase", owner="development/common/b"),
            _node("component:development/common/a", "component"),
            _node("component:development/common/b", "component"),
            _node("component:development/common/c", "component"),
        ],
        "edges": [
            _edge("sprint:S", "sprint_item:S#0", "contains"), _edge("sprint:S", "sprint_item:S#1", "contains"),
            _edge("sprint:S", "sprint_item:S#2", "contains"), _edge("sprint:S", "sprint_item:S#3", "contains"),
            _edge("sprint_item:S#0", "phase:development/common/a/p1.md", "schedules"),
            _edge("sprint_item:S#0", "component:development/common/a", "schedules"),
            _edge("sprint_item:S#0", "phase:development/common/a/p_missing.md", "schedules"),
            _edge("sprint_item:S#1", "phase:development/common/b/p1.md", "schedules"),
            _edge("sprint_item:S#1", "component:development/common/b", "schedules"),
            _edge("sprint_item:S#2", "component:development/common/c", "schedules"),
            _edge("phase:development/common/a/p1.md", "phase:development/common/b/p1.md", "depends_on", "unsatisfied", line=40),
            _edge("phase:development/common/b/p1.md", "component:development/common/c", "depends_on", "underivable", line=41),
            _edge("component:development/common/a", "component:development/common/b", "depends_on", "satisfied", line=42),
        ],
        "dependency_accounting": [],
        "provenance": {},
    }
    items = [SimpleNamespace(raw=f"- [ ] raw line {i}") for i in range(4)]
    sprint_doc = SimpleNamespace(sprints=[SimpleNamespace(name="S", items=items)])
    return SimpleNamespace(graph=graph, sprint_doc=sprint_doc)


def test_the_board_carries_every_item_in_file_order_with_its_raw_line(result):
    board = sb.sprint_boards(result)["S"]
    assert [i["id"] for i in board["items"]] == [f"sprint_item:S#{i}" for i in range(4)]
    assert [i["line"] for i in board["items"]] == [10, 11, 12, 13]
    assert board["items"][2]["raw"] == "- [ ] raw line 2"
    assert board["marker"] == "PLANNED" and board["line"] == 5


def test_edges_among_items_come_from_what_they_schedule(result):
    board = sb.sprint_boards(result)["S"]
    edges = {(e["source"], e["target"]): e for e in board["edges"]}
    # #0 → #1 through the phase edge, carrying its state and line
    assert edges[("sprint_item:S#0", "sprint_item:S#1")]["state"] == "unsatisfied"
    assert edges[("sprint_item:S#0", "sprint_item:S#1")]["via"][0]["line"] == 40
    # #1 → #2: b/p1 depends on component c, and #2 stands for c as a whole
    assert edges[("sprint_item:S#1", "sprint_item:S#2")]["state"] == "underivable"
    assert len(edges) == 2


def test_a_component_level_edge_does_not_attach_to_a_one_phase_item(result):
    """#0 schedules phase a/p1 AND component a; the component-level edge
    a → b must not become #0 → #1 a second time, because #0 stands for its
    phase, not for all of a."""
    board = sb.sprint_boards(result)["S"]
    e = next(e for e in board["edges"] if (e["source"], e["target"]) == ("sprint_item:S#0", "sprint_item:S#1"))
    assert [v["line"] for v in e["via"]] == [40]


def test_an_item_linking_nothing_is_kept_and_marked(result):
    board = sb.sprint_boards(result)["S"]
    unlinked = [i for i in board["items"] if not i["linked"]]
    assert [i["id"] for i in unlinked] == ["sprint_item:S#3"]
    assert unlinked[0]["schedules"] == [] and unlinked[0]["unresolved"] == []


def test_a_link_that_resolves_to_no_node_is_listed_not_dropped(result):
    board = sb.sprint_boards(result)["S"]
    first = board["items"][0]
    assert first["linked"] is True
    assert first["unresolved"] == ["phase:development/common/a/p_missing.md"]
    assert set(first["schedules"]) == {"phase:development/common/a/p1.md", "component:development/common/a"}


def test_two_items_scheduling_one_phase_both_carry_its_edges(result):
    """The live sprint file does this twice (a recurring close-out phase
    scheduled by two items of one sprint; one phase split across two items).
    A first-wins map gave the edge to whichever item the file listed first
    and nothing to the other — the second item then read as having no
    dependencies, which is a different fact from having them undrawn."""
    result.graph["nodes"].append(_node("sprint_item:S#4", "sprint_item", "x · B again", line=14, checked=False))
    result.graph["edges"].append(_edge("sprint:S", "sprint_item:S#4", "contains"))
    result.graph["edges"].append(_edge("sprint_item:S#4", "phase:development/common/b/p1.md", "schedules"))
    result.sprint_doc.sprints[0].items.append(SimpleNamespace(raw="- [ ] raw line 4"))
    board = sb.sprint_boards(result)["S"]
    edges = {(e["source"], e["target"]) for e in board["edges"]}
    # #0 depends on b/p1, which BOTH #1 and #4 stand for; b/p1 depends on c,
    # so both #1 and #4 depend on #2.
    assert edges == {
        ("sprint_item:S#0", "sprint_item:S#1"), ("sprint_item:S#0", "sprint_item:S#4"),
        ("sprint_item:S#1", "sprint_item:S#2"), ("sprint_item:S#4", "sprint_item:S#2"),
    }


def test_a_sprint_with_no_items_is_a_board_with_no_items(result):
    result.graph["nodes"].append(_node("sprint:Empty", "sprint", "Empty", line=99, marker="", unplaced=False))
    board = sb.sprint_boards(result)["Empty"]
    assert board["items"] == [] and board["edges"] == []


def test_the_board_survives_a_missing_sprint_document(result):
    result.sprint_doc = None
    board = sb.sprint_boards(result)["S"]
    assert board["items"][0]["raw"] == ""

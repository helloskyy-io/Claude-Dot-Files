"""Invariants the report's value rests on, asserted at the seam that owns each.

Every test here was written against a defect a review pass found on this PR, and
each is deliberately keyed on the CLASS rather than on the instance: the guard
that stops a symlink is asserted at the door every path goes through, the
node-id check at the door every node goes through, and the §6 measurement
against *any* unrelated emitter of the finding code it used to count.
"""

from __future__ import annotations

from pathlib import Path

from planning_ui.plan_extractor import extractor, provenance, sprints
from planning_ui.plan_extractor.model import (
    NODE_ID_COLLISION,
    SECTION_UNPARSED,
    Collector,
    Node,
    Provenance,
)


# ---------------------------------------------------------------------------
# A node id collision is reported, not admitted.
# ---------------------------------------------------------------------------
def test_two_nodes_deriving_one_id_is_a_named_finding():
    """Component and phase ids are path-keyed; a sprint id is heading-keyed.

    Duplicating a `## Sprint:` heading is exactly the corpus disagreement this
    phase exists to catch, and its effect — two nodes, one id — makes the second
    invisible to every consumer that treats `id` as a primary key.
    """
    collector = Collector()
    first = Node(id="sprint:Widget Work", kind="sprint", label="a", provenance=Provenance("s.md", 4))
    second = Node(id="sprint:Widget Work", kind="sprint", label="b", provenance=Provenance("s.md", 40))
    collector.add_node(first)
    collector.add_node(second)

    assert [f.code for f in collector.findings] == [NODE_ID_COLLISION]
    finding = collector.findings[0]
    assert finding.provenance.line == 40, "the finding points at the SECOND occurrence"
    assert finding.section == SECTION_UNPARSED
    # Both are emitted: which of the two is the real one is a corpus question.
    assert len(collector.nodes) == 2


def test_distinct_ids_produce_no_finding():
    """The negative half — the guard is on collision, not on adding nodes."""
    collector = Collector()
    for name in ("a", "b", "c"):
        collector.add_node(
            Node(id=f"sprint:{name}", kind="sprint", label=name, provenance=Provenance("s.md", 1))
        )
    assert collector.findings == []
    assert len(collector.nodes) == 3


# ---------------------------------------------------------------------------
# The §6-shape measurement owns its predicate.
# ---------------------------------------------------------------------------
_CONFORMANT = """# Implementation Plan

## Sprint: Alpha
🟡 IN PROGRESS

- [x] **common/widget · One** · L1 · ([roadmap](./common/widget/roadmap.md)) — done · **~2h**

## Sprint: Beta

- [x] **common/widget · Two** · L2 · ([roadmap](./common/widget/roadmap.md)) — done · **~2h**
"""


def _write_corpus(tmp_path: Path, sprints_text: str) -> Path:
    root = tmp_path / "corpus"
    (root / "development" / "common" / "widget").mkdir(parents=True)
    (root / "development" / "common" / "widget" / "roadmap.md").write_text(
        "# Widget\n\n**Status:** 🟡 IN PROGRESS\n"
    )
    (root / "development" / "sprints.md").write_text(sprints_text)
    return root


def test_a_sprint_with_no_status_marker_does_not_inflate_the_ss6_shape_row(tmp_path: Path):
    """The row's stated method is "count ITEMS failing §6". Nothing else.

    `sprints.py` emits `UNPARSED_LINE` from eight sites and only four are §6
    shape misses; the measurement used to count them all. `## Sprint: Beta`
    below carries no status marker — a real finding, and not a shape miss — and
    every item in this fixture is fully §6-conformant.
    """
    root = _write_corpus(tmp_path, _CONFORMANT)
    result = extractor.extract(root)

    unparsed = [f for f in result.findings if f.code == "UNPARSED_LINE"]
    assert unparsed, "the marker-less sprint must still be reported"
    assert any("no status marker" in f.summary for f in unparsed)

    shape_row = next(r for r in result.rows if "§6 item shape" in r.name)
    assert shape_row.derived == "0 misses", (
        "an unrelated UNPARSED_LINE emitter inflated the numerator: " + shape_row.derived
    )


def test_a_checkbox_outside_every_sprint_does_not_inflate_the_row_either(tmp_path: Path):
    """The same class, a different emitter — this is why the test is a pair."""
    stray = "# Implementation Plan\n\n- [ ] a checkbox with no sprint\n" + _CONFORMANT.split("\n", 1)[1]
    root = _write_corpus(tmp_path, stray)
    result = extractor.extract(root)

    assert any("outside every" in f.summary for f in result.findings)
    shape_row = next(r for r in result.rows if "§6 item shape" in r.name)
    assert shape_row.derived == "0 misses"


def test_a_genuine_ss6_miss_still_counts(tmp_path: Path):
    """The negative control: the row must not be stuck at zero."""
    missing_layer = _CONFORMANT.replace(
        "**common/widget · One** · L1 · ", "**common/widget · One** · "
    )
    root = _write_corpus(tmp_path, missing_layer)
    result = extractor.extract(root)
    shape_row = next(r for r in result.rows if "§6 item shape" in r.name)
    assert shape_row.derived == "1 misses"


def test_the_flag_and_the_finding_are_one_predicate(tmp_path: Path):
    """`misses_shape` is set by the same code path that emits the finding.

    Asserted so the two cannot drift into two definitions of "fails §6".
    """
    missing_layer = _CONFORMANT.replace(
        "**common/widget · One** · L1 · ", "**common/widget · One** · "
    )
    root = _write_corpus(tmp_path, missing_layer)
    collector = Collector()
    document = sprints.parse_sprints(root, collector)
    flagged = [i for s in document.sprints for i in s.items if i.misses_shape]
    assert len(flagged) == 1
    assert flagged[0].line in {f.provenance.line for f in collector.findings}


# ---------------------------------------------------------------------------
# One ordering, used by both the artifact and the report.
# ---------------------------------------------------------------------------
def test_the_graph_and_the_report_order_findings_identically(tmp_path: Path):
    """They were sorted by two copies of one lambda, two lines apart."""
    root = _write_corpus(tmp_path, _CONFORMANT)
    result = extractor.extract(root)
    assert [f["code"] for f in result.graph["findings"]] == [f.code for f in result.findings]
    assert [f["line"] for f in result.graph["findings"]] == [
        f.provenance.line for f in result.findings
    ]


# ---------------------------------------------------------------------------
# The provenance stamp cannot be fed bytes from outside the checkout.
# ---------------------------------------------------------------------------
def test_input_digest_refuses_a_path_that_escapes_the_root(tmp_path: Path):
    """The third member of the escape-guard class, and the least visible.

    `input_digest` opens whatever path list it is handed. Without the check, an
    escaping symlink that reached the input set would put bytes from outside the
    checkout into the stamp that claims to identify the checkout.
    """
    root = tmp_path / "corpus"
    root.mkdir()
    outside = tmp_path / "outside" / "secret.md"
    outside.parent.mkdir()
    outside.write_text("SENSITIVE\n")
    (root / "escaped.md").symlink_to(outside)
    (root / "inside.md").write_text("plain\n")

    with_escape = provenance.input_digest(root, ["escaped.md", "inside.md"])

    outside.write_text("SENSITIVE, but different\n")
    after_outside_change = provenance.input_digest(root, ["escaped.md", "inside.md"])

    assert with_escape == after_outside_change, (
        "content outside the checkout changed the stamp that identifies the checkout"
    )


def test_input_digest_still_tracks_a_file_inside_the_root(tmp_path: Path):
    """The negative half — the guard must not flatten every input to a constant."""
    root = tmp_path
    (root / "inside.md").write_text("one\n")
    before = provenance.input_digest(root, ["inside.md"])
    (root / "inside.md").write_text("two\n")
    assert provenance.input_digest(root, ["inside.md"]) != before


# ---------------------------------------------------------------------------
# The tracked stores are walked by the same door as every other tree.
# ---------------------------------------------------------------------------
def test_a_symlink_in_a_tracked_store_is_reported_and_never_opened(tmp_path: Path):
    """It was reported AND opened, in the same run, until this pass.

    `tracked.py` enumerated with its own `directory.glob("*.md")`, so the store
    the package treats as its most trustworthy input was the one surface the
    escape guard did not reach — the bypass least visible exactly where it
    mattered most.
    """
    from planning_ui.plan_extractor import tracked

    root = tmp_path / "corpus"
    store = root / "tracked" / "issues"
    store.mkdir(parents=True)
    for name in ("candidates", "operations", "standards"):
        (root / "tracked" / name).mkdir()

    outside = tmp_path / "outside" / "I-deadbeef.md"
    outside.parent.mkdir()
    outside.write_text(
        "---\nid: I-deadbeef\ntitle: SENSITIVE\nstatus: open\ncount: 1\n"
        "filed: 2026-01-01\nfiled_by: nobody\nrepo: x\n---\n"
    )
    (store / "I-deadbeef.md").symlink_to(outside)
    (store / "I-aaaaaaaa.md").write_text(
        "---\nid: I-aaaaaaaa\ntitle: real\nstatus: open\ncount: 1\n"
        "filed: 2026-01-01\nfiled_by: somebody\nrepo: x\n---\n"
    )

    collector = Collector()
    stores = tracked.read_stores(root, collector)

    titles = [item.fields.get("title") for item in stores.items["issues"]]
    assert "SENSITIVE" not in titles, "content from outside the checkout entered the report"
    assert titles == ["real"]
    assert "PATH_ESCAPES_ROOT" in [f.code for f in collector.findings]


def test_a_regular_tracked_item_is_still_read(tmp_path: Path):
    """The negative half: the store reader must not refuse everything."""
    from planning_ui.plan_extractor import tracked

    root = tmp_path / "corpus"
    for name in ("issues", "candidates", "operations", "standards"):
        (root / "tracked" / name).mkdir(parents=True)
    (root / "tracked" / "issues" / "I-aaaaaaaa.md").write_text(
        "---\nid: I-aaaaaaaa\ntitle: real\nstatus: open\ncount: 1\n"
        "filed: 2026-01-01\nfiled_by: somebody\nrepo: x\n---\n"
    )
    collector = Collector()
    stores = tracked.read_stores(root, collector)
    assert [i.fields["title"] for i in stores.items["issues"]] == ["real"]
    assert "PATH_ESCAPES_ROOT" not in [f.code for f in collector.findings]


# ---------------------------------------------------------------------------
# An hour figure the stated method cannot attribute is REPORTED, not counted
# into a field nothing reads.
# ---------------------------------------------------------------------------
def test_an_unattributable_hour_figure_is_named_with_its_line(tmp_path: Path):
    """It went into `Component.unattributed_hours`, which no consumer read.

    A figure the tool saw and could not place then left no trace at all — the
    never-silently-drop rule failing at the attribution layer.
    """
    from planning_ui.plan_extractor import roadmaps

    root = tmp_path / "corpus"
    (root / "development" / "common" / "widget").mkdir(parents=True)
    rel = "development/common/widget/roadmap.md"
    (root / rel).write_text(
        "# Widget\n\n**Status:** 🟡 IN PROGRESS\n\n"
        "## Phases\n\n"
        "- [ ] **One** (~5h) [phase1_a.md](./phase1_a.md)\n"
        "- [ ] **Two** (~7-9h) [phase2_b.md](./phase2_b.md)\n"
    )

    collector = Collector()
    component = roadmaps.parse_roadmap(root, rel, collector)

    hours = [f for f in collector.findings if f.code == "HOURS_UNATTRIBUTED"]
    assert len(hours) == 1, "one row per roadmap, carrying every line"
    assert hours[0].provenance.file == rel
    assert hours[0].provenance.line == 7
    # Every unattributed figure is named with its line inside the one row.
    assert "L7 ~5h" in hours[0].detail
    assert "L8 ~7-9h" in hours[0].detail
    assert component.unattributed_hours == 2


def test_an_attributable_hour_figure_produces_no_finding(tmp_path: Path):
    """The negative half: a section with exactly one phase link attributes."""
    from planning_ui.plan_extractor import roadmaps

    root = tmp_path / "corpus"
    (root / "development" / "common" / "widget").mkdir(parents=True)
    rel = "development/common/widget/roadmap.md"
    (root / rel).write_text(
        "# Widget\n\n**Status:** 🟡 IN PROGRESS\n\n"
        "## One\n\n- [ ] **One** (~5h) [phase1_a.md](./phase1_a.md)\n"
    )

    collector = Collector()
    component = roadmaps.parse_roadmap(root, rel, collector)
    assert [f for f in collector.findings if f.code == "HOURS_UNATTRIBUTED"] == []
    assert component.unattributed_hours == 0
    assert component.owned[0].hours_low == 5

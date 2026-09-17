"""Integration tests: the enumerate-then-classify walk over a real tree.

These walk a filesystem, so they are integration-weight by the Testing
Standard's own rule of thumb even though nothing external is standing. The tree
is the deliberately-malformed fixture corpus, not the live one — the corpus must
not be damaged to test the tool that reads it.

**The adversarial case is the point of this file**: a malformed sprint item must
appear in the report as a named finding with its file and its line, and the graph
must NOT be quietly smaller.
"""

from __future__ import annotations

import json

from planning_ui.plan_extractor import extract, render_markdown


def _codes(result) -> list[str]:
    return [f.code for f in result.findings]


def _findings(result, code):
    return [f for f in result.findings if f.code == code]


def test_a_malformed_sprint_item_is_reported_and_the_graph_is_not_smaller(fixture_corpus):
    """The spine, stated as an assertion.

    The fixture's third item carries `cross-cutting` in place of its layer AND
    links to nothing. Both are named findings — and the item is still a node, so
    nothing downstream has to distinguish "no such edge" from "I could not read
    that line."
    """
    result = extract(fixture_corpus)

    unparsed = _findings(result, "UNPARSED_LINE")
    assert {f.provenance.line for f in unparsed} == {13, 14}
    assert all(f.provenance.file == "development/sprints.md" for f in unparsed)
    assert all(f.expected for f in unparsed), "a finding with no expected shape is not a worklist entry"

    # The graph did not shrink: every checkbox outside the fence is a node.
    item_nodes = [n for n in result.graph["nodes"] if n["kind"] == "sprint_item"]
    assert len(item_nodes) == 7
    labels = {n["label"] for n in item_nodes}
    assert "common/widget · Third Thing" in labels


def test_the_fenced_template_never_becomes_a_sprint_item(fixture_corpus):
    """9 checkbox lines, 7 items — the difference is the two fenced examples.

    One fence sits before the first sprint heading and one sits INSIDE a sprint.
    The second is the case that matters and the fixture originally lacked it: a
    broken fence mask routes a pre-sprint fence to the "outside every sprint
    section" path, so it never reaches a sprint's item list and this assertion
    could not see the failure. Measured by mutation — predicted 4 red, observed
    3, and this was the missing one.
    """
    result = extract(fixture_corpus)
    assert result.counts["checkbox_lines"] == 9
    assert result.counts["sprint_items"] == 7
    labels = {n["label"] for n in result.graph["nodes"] if n["kind"] == "sprint_item"}
    assert "Component · Phase Name" not in labels
    assert "common/widget · Fenced Example" not in labels


def test_the_unparsed_section_is_emitted_first(fixture_corpus):
    """*Lines I could not parse* is the report's FIRST section, deliberately."""
    report = render_markdown(extract(fixture_corpus))
    assert report.index("## lines I could not parse") < report.index("## files I could not classify")
    assert report.index("## lines I could not parse") < report.index(
        "## declarations that disagree with derivation"
    )


def test_a_phase_shaped_file_matching_no_pattern_is_named_not_absent(fixture_corpus):
    result = extract(fixture_corpus)
    found = {f.provenance.file for f in _findings(result, "UNCLASSIFIED_PHASE_SHAPED")}
    assert found == {"development/common/widget/close_out.md"}
    # …and it is admitted as a phase node, so it is not missing from the graph.
    assert any(
        n["id"] == "phase:development/common/widget/close_out.md" for n in result.graph["nodes"]
    )


def test_a_roadmapless_planning_directory_is_named(fixture_corpus):
    result = extract(fixture_corpus)
    found = {f.provenance.file for f in _findings(result, "COMPONENT_SHAPED_NO_ROADMAP")}
    assert found == {"development/service/orphanage"}


def test_a_component_admitted_with_no_status_line_is_its_own_finding(fixture_corpus):
    result = extract(fixture_corpus)
    found = {f.provenance.file for f in _findings(result, "COMPONENT_NO_STATUS")}
    assert found == {"development/service/gadget/roadmap.md"}


def test_a_closed_items_hours_are_an_actual_and_are_never_compared(fixture_corpus):
    """§6: a delivered item's stamp carries the ACTUAL hours.

    The fixture's closed item says ~10h and its roadmap entry says ~12h. That
    is an actual beside an estimate — two quantities — and reporting their
    difference as "one figure, one home" is a false row. The `(finding,)`
    unpacking in the test below is this guard's control: remove the skip and a
    second HOURS_DISAGREE appears and that test fails.
    """
    result = extract(fixture_corpus)
    reported = {f.summary for f in _findings(result, "HOURS_DISAGREE")}
    assert not [s for s in reported if "phase1_first.md" in s], (
        "a closed item's actual hours were compared against its roadmap estimate"
    )


def test_hour_disagreement_reports_both_figures_and_authors_neither(fixture_corpus):
    result = extract(fixture_corpus)
    (finding,) = _findings(result, "HOURS_DISAGREE")
    assert "~20h" in finding.summary and "~25h" in finding.summary
    # No third figure is authored anywhere in the finding.
    assert "should be" not in finding.summary.lower()
    assert "~22" not in finding.summary and "~23" not in finding.summary


def test_a_sprint_marker_that_disagrees_with_its_checkboxes_is_reported(fixture_corpus):
    result = extract(fixture_corpus)
    (finding,) = _findings(result, "SPRINT_MARKER_DISAGREES")
    assert "Gadget Work" in finding.summary
    assert "COMPLETE" in finding.summary and "PLANNED" in finding.summary


def test_the_unplaced_whole_components_subsection_is_the_only_declared_side(fixture_corpus):
    """The sibling subsection names PHASES inside scheduled components.

    Reading both as declared orphans manufactures a disagreement for every
    entry in it — measured on the live corpus, four false findings.
    """
    result = extract(fixture_corpus)
    declared = _findings(result, "DECLARED_NOT_ORPHAN")
    assert len(declared) == 1
    assert "development/service/gadget" in declared[0].summary
    # `common/widget` sits in the sibling subsection and is NOT a false finding.
    assert not any("common/widget" in f.summary for f in declared)


def test_tracked_store_findings_carry_file_and_line(fixture_corpus):
    result = extract(fixture_corpus)
    missing = _findings(result, "TRACKED_CORE_FIELD_MISSING")
    assert [f.provenance.file for f in missing] == ["tracked/issues/I-bbbbbbbb.md"]
    assert "filed_by" in missing[0].summary

    (component,) = _findings(result, "TRACKED_COMPONENT_UNRESOLVED")
    assert component.provenance.line == 8

    (anchor,) = _findings(result, "TRACKED_ANCHOR_UNRESOLVED")
    assert "§99" in anchor.summary
    assert anchor.provenance.line == 9


def test_a_graph_edge_resolving_to_no_node_is_reported(fixture_corpus):
    result = extract(fixture_corpus)
    (edge,) = _findings(result, "EDGE_RESOLVES_TO_NO_NODE")
    assert "phase9_missing.md" in edge.summary
    assert edge.provenance.file == "development/common/widget/roadmap.md"


def test_the_amendment_census_always_reports_a_tail_with_a_count(fixture_corpus):
    """A census with no tail is asserting it found everything."""
    result = extract(fixture_corpus)
    tails = [f for f in _findings(result, "AMENDMENT_UNCLASSIFIABLE") if "unclassifiable tail" in f.summary]
    assert len(tails) == 1
    assert "0 amendment-shaped heading(s)" in tails[0].summary


def test_a_live_amendment_surface_is_reported_and_not_resolved(fixture_corpus):
    result = extract(fixture_corpus)
    (surface,) = _findings(result, "AMENDMENT_SECOND_SURFACE")
    assert surface.provenance.file == "development/service/gadget/phase1_only.md"
    assert "resolve" not in surface.summary.lower()
    assert "out of scope" in surface.detail


def test_running_twice_on_an_unchanged_tree_is_byte_identical(fixture_corpus):
    """Requirement: run twice, confirm byte-identical output.

    The digest is over the exact bytes read, and every collection is sorted, so
    a difference here means non-determinism in the tool rather than in the
    corpus.
    """
    first = json.dumps(extract(fixture_corpus).graph, indent=2, sort_keys=True)
    second = json.dumps(extract(fixture_corpus).graph, indent=2, sort_keys=True)
    assert first == second


def test_the_provenance_stamp_names_the_commit_and_the_input_digest(fixture_corpus):
    result = extract(fixture_corpus)
    prov = result.graph["provenance"]
    assert prov["input_digest"].startswith("sha256:")
    assert prov["input_count"] > 0
    assert prov["tracked_contract_version"] == "v1"
    # The fixture tree is inside example-app's checkout, so a commit resolves.
    assert prov["commit"]


def test_every_node_carries_the_file_and_line_it_was_read_from(fixture_corpus):
    """Requirement 1: provenance at node granularity is what makes a finding
    actionable."""
    result = extract(fixture_corpus)
    assert result.graph["nodes"]
    for node in result.graph["nodes"]:
        assert node["file"], node
        assert isinstance(node["line"], int)


def test_the_input_digest_changes_when_an_input_changes(fixture_corpus, tmp_path):
    """A digest that cannot change is not a digest.

    Copies the fixture tree, mutates one byte of one input, and asserts the
    stamp moves — otherwise the provenance stamp would be decoration.
    """
    import shutil

    copy = tmp_path / "corpus"
    shutil.copytree(fixture_corpus, copy)
    before = extract(copy).graph["provenance"]["input_digest"]

    target = copy / "development" / "common" / "widget" / "roadmap.md"
    target.write_text(target.read_text() + "\nAn added line.\n", encoding="utf-8")
    after = extract(copy).graph["provenance"]["input_digest"]

    assert before != after


def test_the_two_dependency_dispositions_reach_the_rendered_report(fixture_corpus):
    """End to end: a conforming declaration and a roadmap with none.

    `common/widget` carries the ruled format and resolves; `service/gadget`
    carries no line at all and lands on the declares-nothing worklist. The
    accounting table is asserted through the RENDERED report because that table
    is what makes "every roadmap is accounted for" visible to a human rather
    than merely true in a dataclass.
    """
    result = extract(fixture_corpus)
    by_component = {row.component: row for row in result.dependency_accounting}
    assert by_component["development/common/widget"].disposition == "resolves"
    assert (
        by_component["development/service/gadget"].disposition
        == "worklist — declares nothing"
    )

    (edge,) = [e for e in result.graph["edges"] if e["kind"] == "depends_on"]
    assert edge["source"] == "component:development/common/widget"
    assert edge["target"] == "phase:development/service/gadget/phase1_only.md"

    report = render_markdown(result)
    assert "## Every roadmap, accounted for" in report
    assert "development/service/gadget" in report
    assert "worklist — declares nothing" in report
    # The two worklists are separate sections with their own counts, because the
    # two gaps have different remedies.
    assert "## roadmaps declaring no dependency a parser can read — 1" in report
    assert "## roadmaps declaring a dependency in prose only — 0" in report

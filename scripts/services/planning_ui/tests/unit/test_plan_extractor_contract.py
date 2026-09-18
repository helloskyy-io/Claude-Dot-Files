"""The corpus contract — what makes a directory a planning repository.

One viewer serves one planning repository — the one its caller named — and
these hold the one predicate that decides whether a directory is one: a root
that fails is refused by the condition it failed, never read as an empty
corpus.
"""
from __future__ import annotations

from pathlib import Path

from planning_ui.plan_extractor import contract


def _repo(root: Path) -> Path:
    (root / "development").mkdir(parents=True)
    (root / "development" / "sprints.md").write_text("# s\n")
    return root


def test_a_corpus_satisfies_the_contract(tmp_path):
    assert contract.unmet_condition(_repo(tmp_path / "a")) is None
    assert contract.is_planning_repo(tmp_path / "a")


def test_each_missing_requirement_is_named_never_read_as_an_empty_corpus(tmp_path):
    """A missing `development/` is not zero components."""
    bare = tmp_path / "bare"
    bare.mkdir()
    assert "no `development/`" in contract.unmet_condition(bare)

    no_sprints = tmp_path / "no_sprints"
    (no_sprints / "development").mkdir(parents=True)
    assert "sprints.md" in contract.unmet_condition(no_sprints)

    assert "not a directory" in contract.unmet_condition(tmp_path / "absent")


def test_standards_and_tracked_are_not_required(tmp_path):
    """Their absence is a FINDING about a corpus, which is what this tool is
    for — refusing what it can report would turn a young planning repo away."""
    assert contract.unmet_condition(_repo(tmp_path / "young")) is None


def test_the_layer_requirement_is_the_corpus_s_to_declare(tmp_path):
    """`· L<n> ·` is MDC's sprints.md §6, from its Deployment Layer Model —
    not the Documentation Standard's item shape. A corpus that never had
    layers read every item as unparsed under a hard-coded requirement: 72
    findings about a rule it does not have. Declared, off by default."""
    from planning_ui.plan_extractor import contract as c
    from planning_ui.plan_extractor.model import Collector
    from planning_ui.plan_extractor.sprints import parse_sprints

    (tmp_path / "development").mkdir()
    (tmp_path / "development" / "sprints.md").write_text(
        "# Sprints\n\n## Sprint: One 🟠 PLANNED\n\n"
        "- [ ] **Alpha · Only** · ([roadmap](./common/alpha/roadmap.md)) — no layer\n"
    )
    without = Collector()
    parse_sprints(tmp_path, without, c.Contract())
    assert not [f for f in without.findings if "L<n>" in f.summary], "off by default"

    with_layer = Collector()
    parse_sprints(tmp_path, with_layer, c.Contract(sprint_layer_required=True))
    assert [f for f in with_layer.findings if "L<n>" in f.summary], "positive control"

    (tmp_path / "corpus.toml").write_text("[corpus]\nsprint_layer_required = true\n")
    assert c.load(tmp_path).sprint_layer_required is True


def test_a_component_record_can_be_declared_a_phase_document(tmp_path):
    """SkyyNet's sprint plan rules *"`<name>/<name>.md` is its phase doc"* —
    one per component, named after it, linked from sprint items as the phase.
    `{component}.md` under `phase_documents` makes exactly that shape a phase
    document: classified as one, and a link to it a phase link. Without the
    declaration the same file is unclassified, as before."""
    from planning_ui.plan_extractor import contract as c
    from planning_ui.plan_extractor import discovery
    from planning_ui.plan_extractor.roadmaps import is_phase_link

    declared = c.Contract(phase_documents=("{component}.md",))
    rel = "development/edge/temporal-integration/temporal-integration.md"
    assert declared.is_phase_document(rel)
    assert not declared.is_phase_document("development/edge/temporal-integration/other.md")
    assert discovery.classify(rel, declared) == discovery.PHASE_DOC
    assert discovery.classify(rel, c.Contract()) == discovery.UNCLASSIFIED

    (tmp_path / "corpus.toml").write_text('[corpus]\nphase_documents = ["{component}.md"]\n')
    assert c.load(tmp_path).phase_documents == ("{component}.md",)
    assert is_phase_link(rel, tmp_path)
    assert not is_phase_link(rel)


def test_a_name_in_not_a_node_can_still_be_the_component_pattern(tmp_path):
    """The same `{component}.md` pattern is admitted in `not_a_node` for a
    corpus whose `<name>/<name>.md` is a record and never a node; every match
    is one class."""
    from planning_ui.plan_extractor import contract as c
    from planning_ui.plan_extractor import discovery

    contract = c.Contract(not_a_node=c.CONVENTION_NOT_A_NODE + ("{component}.md",))
    assert contract.not_a_node_entry("development/edge/x/x.md") == "{component}.md"
    assert contract.not_a_node_entry("development/edge/x/y.md") is None
    assert discovery.classify("development/edge/x/x.md", contract) == discovery.COMPONENT_RECORD
    assert discovery.COMPONENT_RECORD in discovery.not_a_node_classes(contract)


def test_an_unplanned_component_is_a_finding_or_a_count_as_the_corpus_rules(tmp_path):
    """MDC reports a component directory with documents and no roadmap;
    SkyyNet rules it UNPLANNED, not non-conformant. The corpus decides, and
    the count is kept either way so nothing vanishes."""
    from planning_ui.plan_extractor import contract as c
    from planning_ui.plan_extractor import discovery
    from planning_ui.plan_extractor.model import Collector, COMPONENT_SHAPED_NO_ROADMAP

    d = tmp_path / "development" / "common" / "thing"
    d.mkdir(parents=True)
    (d / "notes.md").write_text("# notes\n")
    (tmp_path / "development" / "sprints.md").write_text("# Sprints\n")

    reported = Collector()
    discovery.run_discovery(tmp_path, reported, contract=c.Contract())
    assert [f for f in reported.findings if f.code == COMPONENT_SHAPED_NO_ROADMAP]

    counted = Collector()
    discovery.run_discovery(tmp_path, counted, contract=c.Contract(unplanned_components_conformant=True))
    assert not [f for f in counted.findings if f.code == COMPONENT_SHAPED_NO_ROADMAP]
    assert discovery.component_shaped_directories(tmp_path, ["development/common/thing/notes.md"]) == [
        "development/common/thing"
    ]


def test_a_not_corpus_directory_under_development_is_not_walked(tmp_path):
    """`not_corpus` used to reach only the link sweep and the census; discovery
    still classified everything under it and reported eleven review records
    as unclassified planning documents. It holds no corpus, so it is not walked."""
    from planning_ui.plan_extractor import contract as c
    from planning_ui.plan_extractor import discovery
    from planning_ui.plan_extractor.model import Collector

    (tmp_path / "development" / "common" / "reviews").mkdir(parents=True)
    (tmp_path / "development" / "common" / "reviews" / "review-2026-01-01.md").write_text("# r\n")
    (tmp_path / "development" / "sprints.md").write_text("# Sprints\n")

    walked = discovery.enumerate_markdown(tmp_path, contract=c.Contract())
    assert "development/common/reviews/review-2026-01-01.md" in walked, "positive control"
    skipped = discovery.enumerate_markdown(
        tmp_path, contract=c.Contract(not_corpus=("development/common/reviews/",))
    )
    assert "development/common/reviews/review-2026-01-01.md" not in skipped
    assert "development/sprints.md" in skipped

    collector = Collector()
    discovery.run_discovery(tmp_path, collector, contract=c.Contract(not_corpus=("development/common/reviews/",)))
    assert not [f for f in collector.findings if "reviews" in f.provenance.file]

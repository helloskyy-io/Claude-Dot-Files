"""Unit tests for enumerate-then-classify.

Pure functions over strings: no checkout walk, no filesystem, no git. The walk
itself is exercised by the integration tier, per the phase's test posture.

**Every assertion here was written after probing the real classifier**, not from
reading it — the ordering of the `research/`, `dependencies.md` and phase-pattern
rules is not obvious from the source, and a suite written from an attentive
reading encodes belief rather than behaviour.
"""

from __future__ import annotations

import pytest

from planning_ui.plan_extractor import discovery
from planning_ui.plan_extractor.contract import Contract


@pytest.mark.parametrize(
    "rel,expected",
    [
        # The two names that ARE classifiers.
        ("development/common/planning_ui/roadmap.md", discovery.ROADMAP),
        ("development/common/planning_ui/phase1_plan_extractor.md", discovery.PHASE_DOC),
        ("development/common/planning_ui/phase2a_sub_lettered.md", discovery.PHASE_DOC),
        ("development/sprints.md", discovery.SPRINTS),
        # Recognised-and-not-a-node classes. Without these the report carries
        # forty benign rows and the findings that matter are buried.
        ("development/sprints_archive_2026-06-10.md", discovery.SPRINTS_ARCHIVE),
        ("development/CLAUDE.md", discovery.REPO_INSTRUCTIONS),
        ("development/service/secrets/research/eso_project_health.md", discovery.RESEARCH),
        ("development/common/ansible/dependencies.md", discovery.DEPENDENCIES),
        ("development/common/ansible/requirements.md", discovery.REQUIREMENTS),
        ("development/common/ansible/review-resolutions.md", discovery.REVIEW_RESOLUTIONS),
        # NOT here: `surfaced_standards_changes.md`. It is a document name THIS
        # corpus recognises, declared in its `corpus.toml`, and the tool ships
        # no such convention — see the pair of tests below.
        # The live cases: neither matches the phase pattern, so neither may be
        # silently absent.
        ("development/common/genesis/genesis-1a_k3s-0.md", discovery.UNCLASSIFIED),
        ("development/service/example-app/networking.md", discovery.UNCLASSIFIED),
    ],
)
def test_classify_assigns_the_expected_class(rel, expected):
    assert discovery.classify(rel) == expected


def test_a_corpus_specific_document_name_is_unclassified_without_the_contract():
    """The negative control for the pair below.

    `surfaced_standards_changes.md` is not a convention, so a tool reading a
    corpus that never declared it must NOT quietly recognise it — that is the
    MDC-specific knowledge this module used to carry.
    """
    rel = "development/common/cp_migration/surfaced_standards_changes.md"
    assert discovery.classify(rel) == discovery.UNCLASSIFIED


def test_a_corpus_that_declares_the_name_gets_it_classified_by_its_own_stem():
    rel = "development/common/cp_migration/surfaced_standards_changes.md"
    declared = Contract(not_a_node=("surfaced_standards_changes.md",))
    assert discovery.classify(rel, declared) == "surfaced_standards_changes"
    assert "surfaced_standards_changes" in discovery.not_a_node_classes(declared)


def test_a_nested_sprints_file_is_not_the_sprint_plan():
    """`sprints.md` is the plan only at `development/sprints.md`.

    A component-level file of the same name would otherwise be parsed as a
    second sprint plan, which is the "two answers to one question" defect the
    single-source rule exists to prevent.
    """
    assert discovery.classify("development/common/widget/sprints.md") == discovery.UNCLASSIFIED


def test_phase_pattern_rejects_the_shapes_the_corpus_actually_carries():
    """The pattern is the Documentation Standard's hard external constraint.

    Each rejection below is a real filename in the corpus, so a loosened pattern
    would silently admit a non-conforming name instead of reporting it.
    """
    assert discovery.PHASE_FILENAME_RE.match("phase12_per_cluster_vault_scoping.md")
    assert discovery.PHASE_FILENAME_RE.match("phase2b_thing.md")
    assert not discovery.PHASE_FILENAME_RE.match("genesis-1a_k3s-0.md")
    assert not discovery.PHASE_FILENAME_RE.match("phase_no_number.md")
    assert not discovery.PHASE_FILENAME_RE.match("Phase1_capitalised.md")
    assert not discovery.PHASE_FILENAME_RE.match("phase1_Mixed_Case.md")


def test_component_shaped_directories_finds_a_roadmapless_planning_directory():
    """The live case: a component with planning docs and no roadmap.

    No glob reaches it — that is the whole point — so this is derived from the
    enumerated file list rather than from a directory scan.
    """
    enumerated = [
        "development/common/widget/roadmap.md",
        "development/common/widget/phase1_first.md",
        "development/service/example-app/networking.md",
        "development/service/example-app/production_deployment.md",
    ]
    found = discovery.component_shaped_directories(object(), enumerated)
    assert found == ["development/service/example-app"]


def test_component_shaped_test_does_not_admit_a_subdirectory_of_a_component():
    """A `.../old/` or `.../research/` directory is not a component.

    Admitting it would flood the report with exactly the benign rows the wide
    taxonomy exists to prevent, and the cheapest fix would then be a hardcoded
    suppression list — the glob's silent filter one layer up.
    """
    enumerated = [
        "development/workload/probe/roadmap.md",
        "development/workload/probe/old/roadmap.md",
        "development/service/secrets/research/eso_project_health.md",
    ]
    assert discovery.component_shaped_directories(object(), enumerated) == []


def test_not_a_node_classes_are_named_rather_than_suppressed():
    """Every recognised non-node class is enumerated in one place.

    If a class is dropped from this set it stops being *recognised* and starts
    being *unclassified*, which is the difference between a taxonomy and a
    hidden filter. Pinning the set makes that change visible in a diff.
    """
    assert discovery.NOT_A_NODE_CLASSES == frozenset(
        {
            discovery.SPRINTS_ARCHIVE,
            discovery.DEPENDENCIES,
            discovery.RESEARCH,
            discovery.REQUIREMENTS,
            discovery.REVIEW_RESOLUTIONS,
            discovery.SURFACED_STANDARDS,
            discovery.REPO_INSTRUCTIONS,
        }
    )
    assert discovery.ROADMAP not in discovery.NOT_A_NODE_CLASSES
    assert discovery.PHASE_DOC not in discovery.NOT_A_NODE_CLASSES

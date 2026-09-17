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

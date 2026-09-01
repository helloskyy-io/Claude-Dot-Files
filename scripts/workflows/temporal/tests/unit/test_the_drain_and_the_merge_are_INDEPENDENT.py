"""The two halves are not one transaction, and these tests are why that matters.

An intake is an ALREADY-RULED finding — `review-pr` ruled it when it filed it —
and the drain is GLOBAL, carrying intakes from other PRs including ones that will
never merge. There is no shared invariant, so there is no saga. Coupling them
would let a `gh` hiccup in an unrelated queue block a reviewed, green PR from
landing, or withhold ruled findings because someone else's merge failed.

The one place order DOES bind is inside the PR set, and the asymmetry decides it:
code merged with the record unmerged leaves a visible open PR; the record merged
without its code asserts work that is not in, silently.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules"))

from assistant.merge import merge_pr  # noqa: E402

REPO = Path("/nonexistent-by-design")


@pytest.fixture
def merges(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Everything clear; record which PRs actually reached `gh pr merge`."""
    called: list[str] = []
    monkeypatch.setattr(merge_pr, "refusals", lambda pr, root: [])
    monkeypatch.setattr(merge_pr, "merge_one",
                        lambda pr, root, dry_run=False: called.append(pr) or None)
    return called


def test_a_refusal_STOPS_THE_SET_rather_than_skipping_one_member(
        merges, monkeypatch) -> None:
    """THE ORDERING INVARIANT. The record must not land without its code.

    Merging the second member after the first refused produces exactly the
    silent-and-false state the ordering exists to prevent.
    """
    monkeypatch.setattr(merge_pr, "refusals",
                        lambda pr, root: ["CI is `red`, not green"] if pr == "1" else [])

    report = merge_pr.run_merge(["1", "2"], REPO)

    assert merges == [], "a member merged after an earlier one refused"
    assert report.merged == ()
    assert [pr for pr, _ in report.refused] == ["1", "2"]
    assert "not attempted" in dict(report.refused)["2"]


def test_the_set_merges_IN_THE_ORDER_GIVEN(merges) -> None:
    """The caller orders it; this function does not reorder, because it cannot
    tell the code PR from the record PR — only the caller knows."""
    merge_pr.run_merge(["7", "8", "9"], REPO)
    assert merges == ["7", "8", "9"]


def test_a_FAILED_DRAIN_does_not_block_the_merge(merges, monkeypatch, tmp_path) -> None:
    """The coupling this module refuses, asserted rather than described."""
    for store in ("issues", "candidates", "operations", "standards"):
        (tmp_path / "tracked" / store).mkdir(parents=True)

    def _boom(root, cwd=None, dry_run=False):
        raise RuntimeError("gh: rate limited")

    monkeypatch.setattr(merge_pr.intake, "harvest", _boom)

    report = merge_pr.run_merge(["1"], REPO, stores_root=tmp_path)

    assert merges == ["1"], "an unrelated queue failure blocked a cleared merge"
    assert report.merged == ("1",)
    assert "rate limited" in report.drain_error
    assert not report.ok, "a drain failure must still be reported as not-ok"


def test_a_REFUSED_merge_does_not_withhold_the_drain(monkeypatch, tmp_path) -> None:
    """Findings ruled on other PRs are not hostage to this one's merge."""
    for store in ("issues", "candidates", "operations", "standards"):
        (tmp_path / "tracked" / store).mkdir(parents=True)
    monkeypatch.setattr(merge_pr, "refusals", lambda pr, root: ["held"])
    monkeypatch.setattr(merge_pr.intake, "harvest",
                        lambda root, cwd=None, dry_run=False: ([(42, Path("x"))], []))

    report = merge_pr.run_merge(["1"], REPO, stores_root=tmp_path)

    assert report.merged == ()
    assert report.drained == (42,), "the drain was withheld because a merge failed"


def test_a_MISSING_store_is_named_rather_than_harvested_into(merges, tmp_path) -> None:
    """§5.1's shape: an actor told 'record it in X' that finds no X creates X."""
    report = merge_pr.run_merge(["1"], REPO, stores_root=tmp_path / "empty")
    assert "no tracked store at" in report.drain_error
    assert report.merged == ("1",), "the merge was blocked by a missing store"


def test_a_MALFORMED_intake_is_left_OPEN_and_reported(merges, monkeypatch, tmp_path) -> None:
    """Closing it would lose the finding to tidy the queue — the trade this
    design refuses everywhere else."""
    for store in ("issues", "candidates", "operations", "standards"):
        (tmp_path / "tracked" / store).mkdir(parents=True)
    monkeypatch.setattr(merge_pr.intake, "harvest",
                        lambda root, cwd=None, dry_run=False: ([], [(9, "no store key")]))
    report = merge_pr.run_merge(["1"], REPO, stores_root=tmp_path)
    assert "#9" in report.drain_error and "left OPEN" in report.drain_error

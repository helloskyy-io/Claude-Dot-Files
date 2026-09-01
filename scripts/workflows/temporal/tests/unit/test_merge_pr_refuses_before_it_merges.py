"""`merge-pr` is the only enforced gate on `main`, so its refusals are the product.

Branch protection is rejected permanently on this account (paid feature,
`cpi-decisions.md` 2026-08-16) and `tests.yml` runs on `pull_request` while
NOTHING enforces it — a red PR can be merged by hand today. So this activity's
precondition check IS required-status-checks, implemented where we can have it,
and every test below is about the direction it fails in.

THE INVARIANT UNDER TEST: an unreadable signal is a REFUSAL, never an all-clear.
A refusal costs one re-run; the other direction costs a merge nobody cleared.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules"))

from assistant import routing
from assistant.merge import merge_pr  # noqa: E402

REPO = Path("/nonexistent-by-design")


@pytest.fixture
def clear(monkeypatch: pytest.MonkeyPatch):
    """Every precondition satisfied. Each test then breaks exactly one."""
    monkeypatch.setattr(merge_pr, "thread_verdict", lambda pr, root: "MERGE")
    monkeypatch.setattr(merge_pr, "ci_verdict",
                        lambda pr, repo_root: (routing.CiVerdict.GREEN, []))
    monkeypatch.setattr(merge_pr, "_gh_json",
                        lambda args, root: {"state": "OPEN",
                                            "mergeStateStatus": "CLEAN"})


def test_all_preconditions_met_is_NO_refusals(clear) -> None:
    """THE CONTROL. A gate that refuses everything is not a gate."""
    assert merge_pr.refusals("1", REPO) == []


def test_a_verdict_that_cannot_be_READ_refuses(clear, monkeypatch) -> None:
    """None means 'could not determine', which must not read as 'not held'."""
    monkeypatch.setattr(merge_pr, "thread_verdict", lambda pr, root: None)
    why = merge_pr.refusals("1", REPO)
    assert any("no readable" in w for w in why), why


def test_a_HOLD_verdict_refuses(clear, monkeypatch) -> None:
    monkeypatch.setattr(merge_pr, "thread_verdict",
                        lambda pr, root: "HOLD - redispatch")
    assert any("not MERGE" in w for w in merge_pr.refusals("1", REPO))


@pytest.mark.parametrize("state", [s for s in routing.CiVerdict
                                   if s is not routing.CiVerdict.GREEN])
def test_EVERY_non_green_CI_state_refuses(clear, monkeypatch, state) -> None:
    """DERIVED FROM THE ENUM, not a list of the states someone thought of.

    A new `CiVerdict` member is covered on the day it is added. The states this
    must refuse include the unreadable ones — `UNREADABLE_POLICY`,
    `UNREADABLE_CHECKS`, `GATE_DID_NOT_RUN` — which are precisely the ones a
    `!= RED` check would have let through.
    """
    monkeypatch.setattr(merge_pr, "ci_verdict",
                        lambda pr, repo_root: (state, []))
    assert any("not green" in w for w in merge_pr.refusals("1", REPO)), state


def test_an_UNREADABLE_gh_view_refuses(clear, monkeypatch) -> None:
    monkeypatch.setattr(merge_pr, "_gh_json", lambda args, root: None)
    assert any("could not be read" in w for w in merge_pr.refusals("1", REPO))


@pytest.mark.parametrize("status", ["BLOCKED", "DIRTY", "BEHIND", "UNKNOWN"])
def test_any_mergeStateStatus_but_CLEAN_refuses(clear, monkeypatch, status) -> None:
    """`UNKNOWN` is in this list on purpose — GitHub has not computed it yet."""
    monkeypatch.setattr(merge_pr, "_gh_json",
                        lambda args, root: {"state": "OPEN",
                                            "mergeStateStatus": status})
    assert any("not CLEAN" in w for w in merge_pr.refusals("1", REPO))


def test_EVERY_reason_is_reported_not_just_the_first(clear, monkeypatch) -> None:
    """An operator fixing one blocker must not rediscover the next next run."""
    monkeypatch.setattr(merge_pr, "thread_verdict", lambda pr, root: None)
    monkeypatch.setattr(merge_pr, "ci_verdict",
                        lambda pr, repo_root: (routing.CiVerdict.RED, ["tests"]))
    monkeypatch.setattr(merge_pr, "_gh_json",
                        lambda args, root: {"state": "CLOSED",
                                            "mergeStateStatus": "DIRTY"})
    assert len(merge_pr.refusals("1", REPO)) == 3

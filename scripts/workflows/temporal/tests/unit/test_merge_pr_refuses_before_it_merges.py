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

import subprocess
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


# --- `UNKNOWN` is transient, and that is not the same as clean ----------------
#
# Found on the first real invocation, against PR #166: refused on `UNKNOWN`, then
# three consecutive `CLEAN` answers with nothing else changed. The query is what
# triggers GitHub to compute mergeability. A bare refusal would fire on most
# first invocations — the "stated failure that happens every time" shape this
# repo has now paid for three separate ways.


def test_an_UNKNOWN_status_is_RE_ASKED_and_the_later_answer_wins(monkeypatch) -> None:
    """THE FIX. One transient UNKNOWN must not cost the operator a re-run."""
    answers = [{"state": "OPEN", "mergeStateStatus": "UNKNOWN"},
               {"state": "OPEN", "mergeStateStatus": "CLEAN"}]
    monkeypatch.setattr(merge_pr, "_gh_json", lambda a, r: answers.pop(0))
    monkeypatch.setattr(merge_pr.time, "sleep", lambda s: None)
    assert merge_pr.pr_view("1", REPO) == {"state": "OPEN", "mergeStateStatus": "CLEAN"}


def test_a_PERSISTENT_unknown_still_REFUSES(monkeypatch, clear) -> None:
    """THE CONTROL, and the half that matters. Bounding the wait must not turn an
    unknown into a yes — exhausting the retries is not an all-clear."""
    monkeypatch.setattr(merge_pr, "_gh_json",
                        lambda a, r: {"state": "OPEN", "mergeStateStatus": "UNKNOWN"})
    monkeypatch.setattr(merge_pr.time, "sleep", lambda s: None)
    assert any("not CLEAN" in w for w in merge_pr.refusals("1", REPO))


def test_the_retry_is_BOUNDED(monkeypatch) -> None:
    """A poll with no ceiling is a hang, and this runs inside a merge path."""
    calls = []
    monkeypatch.setattr(merge_pr, "_gh_json",
                        lambda a, r: calls.append(1) or {"state": "OPEN",
                                                         "mergeStateStatus": "UNKNOWN"})
    monkeypatch.setattr(merge_pr.time, "sleep", lambda s: None)
    merge_pr.pr_view("1", REPO)
    assert len(calls) == merge_pr.UNKNOWN_RETRIES


def test_an_UNREADABLE_view_stops_retrying_immediately(monkeypatch) -> None:
    """None is a read FAILURE, not an unknown status — retrying it waits on
    nothing, and the refusal it produces is already correct."""
    calls = []
    monkeypatch.setattr(merge_pr, "_gh_json", lambda a, r: calls.append(1) or None)
    monkeypatch.setattr(merge_pr.time, "sleep", lambda s: None)
    assert merge_pr.pr_view("1", REPO) is None
    assert len(calls) == 1


def test_a_failed_BRANCH_DELETE_does_not_report_a_failed_MERGE(monkeypatch) -> None:
    """`gh pr merge --delete-branch` exits non-zero when the branch is checked
    out in a worktree — which it always is here, because the fleet dispatches
    from `.claude/worktrees/`. Measured on the first real invocation: #166 MERGED
    while this reported "merge failed". The outcome is asked, not the exit code
    trusted."""
    def _boom(*a, **k):
        raise subprocess.CalledProcessError(1, "gh", stderr="failed to delete local branch")

    monkeypatch.setattr(merge_pr.subprocess, "run", _boom)
    monkeypatch.setattr(merge_pr, "_gh_json", lambda a, r: {"state": "MERGED"})
    assert merge_pr.merge_one("1", REPO) is None


def test_a_GENUINELY_failed_merge_is_still_reported(monkeypatch) -> None:
    """THE CONTROL. Asking the outcome must not swallow a real failure."""
    def _boom(*a, **k):
        raise subprocess.CalledProcessError(1, "gh", stderr="not mergeable")

    monkeypatch.setattr(merge_pr.subprocess, "run", _boom)
    monkeypatch.setattr(merge_pr, "_gh_json", lambda a, r: {"state": "OPEN"})
    assert merge_pr.merge_one("1", REPO) == "not mergeable"

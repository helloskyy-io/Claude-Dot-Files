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


from modules.assistant import routing
from modules.assistant.merge import merge_pr  # noqa: E402
from common.journal.bag import open_bag
from common.journal.emit import Emitter, emitting_into
from common.journal.events import EVENTS_FILE, EventKind, decode_event

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
    # `GATE_NOT_YET_RUN` names the head, which is a real `gh` read against REPO.
    monkeypatch.setattr(merge_pr.act, "pr_head", lambda pr, root: "e6704875aabbccdd")
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


# --- CI not started yet is transient, and the refusal must say so -------------
#
# Skyy-Command #337, head `e6704875`, 2026-10-03: refused listing all seven
# declared checks and "this account cannot buy"; MDC-PM1 concluded the gate was
# defective; the same command minutes later merged. Zero runs existed yet.

_PM1_POLICY = ["bake-agreement", "bash-tier", "chart-verify", "constraints-authority",
               "master-test-tier", "schema-validate", "test-helm-charts"]


def _ci_not_yet_run(monkeypatch, *, head="e6704875aabbccdd", extra=None) -> None:
    """`extra` defaults to `[]`, which is what `ci_verdict` really returns. The
    absence test passes the whole declared policy instead, so it bites if the
    formatter ever starts listing `extra` for this state."""
    monkeypatch.setattr(merge_pr, "ci_verdict",
                        lambda pr, repo_root: (routing.CiVerdict.GATE_NOT_YET_RUN, extra or []))
    monkeypatch.setattr(merge_pr.act, "pr_head", lambda pr, root: head)
    monkeypatch.setattr(merge_pr, "_gh_json",
                        lambda args, root: {"state": "OPEN", "mergeStateStatus": "CLEAN"})


def test_the_NOT_YET_RUN_refusal_says_what_it_READ(clear, monkeypatch) -> None:
    """PM1: "'0 workflow runs found for `e6704875`' would have ended the
    investigation in one line." The count and the short sha are the line."""
    _ci_not_yet_run(monkeypatch)
    [ci] = [w for w in merge_pr.refusals("337", REPO) if "not green" in w]
    assert "0 check jobs" in ci and "`e6704875`" in ci, ci
    assert "Transient" in ci and "re-run" in ci, ci


def test_the_NOT_YET_RUN_refusal_carries_NOTHING_misleading(clear, monkeypatch) -> None:
    """THE ABSENCE HALF. A test that checked only the added text would pass with
    the permanent-property clause and the full policy still sitting beside it."""
    _ci_not_yet_run(monkeypatch, extra=_PM1_POLICY)
    [ci] = [w for w in merge_pr.refusals("337", REPO) if "not green" in w]
    assert "cannot buy" not in ci, ci
    assert not [n for n in _PM1_POLICY if n in ci], ci


def test_an_UNREAD_head_is_said_not_guessed(clear, monkeypatch) -> None:
    monkeypatch.setattr(merge_pr, "ci_verdict",
                        lambda pr, repo_root: (routing.CiVerdict.GATE_NOT_YET_RUN, []))
    monkeypatch.setattr(merge_pr.act, "pr_head", lambda pr, root: None)
    monkeypatch.setattr(merge_pr, "_gh_json",
                        lambda args, root: {"state": "OPEN", "mergeStateStatus": "CLEAN"})
    [ci] = [w for w in merge_pr.refusals("337", REPO) if "not green" in w]
    assert "head unread" in ci, ci


def test_GATE_DID_NOT_RUN_still_carries_the_account_clause_and_LABELS_the_absent_gate(
        clear, monkeypatch) -> None:
    """THE CONTROL: the other states' message is not quietly softened, and the
    names it lists say they are ABSENT rather than reading as failures."""
    monkeypatch.setattr(merge_pr, "ci_verdict",
                        lambda pr, repo_root: (routing.CiVerdict.GATE_DID_NOT_RUN, ["suite"]))
    [ci] = [w for w in merge_pr.refusals("1", REPO) if "not green" in w]
    assert "cannot buy" in ci and "declared blocking, none reported: suite" in ci, ci


def test_the_merge_path_does_NOT_wait_for_CI(clear, monkeypatch) -> None:
    """NO WAIT, SLEEP OR POLL ON THE NOT-YET-RUN PATH. A merge path that waits is
    one that can hang; a wait here is ruled into its own sitting with
    MDC-Master-Planning #338, and `wait_for_ci` keeps its own deadline semantics.

    Driven, then inventoried: the refusal is produced with `sleep` and
    `wait_for_ci` both rigged to explode, and the module's `time.sleep` call
    sites are pinned to the two bounded re-asks that predate this rule."""
    import ast
    _ci_not_yet_run(monkeypatch)

    def boom(*a, **k):
        raise AssertionError("the merge path waited")
    monkeypatch.setattr(merge_pr.time, "sleep", boom)
    monkeypatch.setattr(merge_pr.act, "wait_for_ci", boom)
    assert merge_pr.refusals("337", REPO)

    tree = ast.parse(Path(merge_pr.__file__).read_text())
    assert _sleep_sites(tree) == ["_merge_state", "pr_view"], _sleep_sites(tree)
    named = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {
        n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert "wait_for_ci" not in named, "the merge path names wait_for_ci"


def _sleep_sites(tree) -> list[str]:
    """The innermost function of every `time.sleep` / bare `sleep` call, sorted.

    Innermost, so a nested def is not double-counted; bare `sleep` so
    `from time import sleep` is seen."""
    import ast
    found: list[str] = []

    def visit(node, owner):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            owner = node.name
        if isinstance(node, ast.Call) and ast.unparse(node.func) in ("time.sleep", "sleep"):
            found.append(owner)
        for child in ast.iter_child_nodes(node):
            visit(child, owner)
    visit(tree, "<module>")
    return sorted(found)


@pytest.mark.parametrize("snippet, expected", [
    ("import time\ndef refusals():\n    time.sleep(5)\n", ["refusals"]),
    ("import time\ndef refusals():\n    return time.monotonic()\n", []),
    ("from time import sleep\ndef refusals():\n    sleep(5)\n", ["refusals"]),
    ("import time\ndef outer():\n    def inner():\n        time.sleep(5)\n", ["inner"]),
])
def test_the_sleep_inventory_SEES_a_sleep(snippet, expected) -> None:
    """THE PREDICATE'S OWN CONTROL: a sleep added to the refusal path must be
    counted, or the pin above stays green while the merge path waits."""
    import ast
    assert _sleep_sites(ast.parse(snippet)) == expected


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


def test_a_failed_BRANCH_DELETE_is_journaled_as_a_COMPLETED_write(
        monkeypatch, tmp_path: Path) -> None:
    """The merge LANDED, so the journal must say so — permanently and only once.

    ⚠ THE TWO TESTS ABOVE RUN WITH NO EMITTER REGISTERED, which is why this
    defect shipped past them. With the emit wired, `gh` exiting non-zero on a
    merge that succeeded made `paired_write` append a `store_write_failure` —
    and the journal is append-only, so the record said *this write did not
    happen* about a merge that had, uncorrectably. `applied_intents` then
    declines that intent forever and a Phase 4 rebuild concludes the merge never
    occurred, while `run_merge` reports it under `merged` in the same run. The
    record exists to be trusted over the report; a record that contradicts a
    correct report is worse than no record.

    The scenario is PR #166's, measured: `--delete-branch` cannot remove a branch
    checked out in a worktree, and this fleet always dispatches from one.
    """
    def _boom(*a, **k):
        raise subprocess.CalledProcessError(1, "gh",
                                            stderr="failed to delete local branch")

    monkeypatch.setattr(merge_pr.subprocess, "run", _boom)
    monkeypatch.setattr(merge_pr, "_gh_json", lambda a, r: {"state": "MERGED"})

    root = tmp_path / "journal"
    root.mkdir(mode=0o700, parents=True)
    bag = open_bag(root, "run-merge")
    emitter = Emitter.for_run(bag, writer=None, journal_root=root)
    with emitting_into(emitter):
        assert merge_pr.merge_one("1", REPO) is None

    lines = (emitter.writer_dir / EVENTS_FILE).read_text().splitlines()
    kinds = [decode_event(line).kind for line in lines]
    assert kinds == [EventKind.INTENT, EventKind.COMPLETION], (
        f"a merge that LANDED was journaled as {[k.value for k in kinds]}. The "
        f"exit code covers `--delete-branch` too, so the outcome has to be "
        f"resolved INSIDE `perform` — resolving it in a handler is one frame "
        f"too late, and the journal never forgets.")


def test_a_GENUINELY_failed_merge_is_still_journaled_as_a_FAILURE(
        monkeypatch, tmp_path: Path) -> None:
    """THE CONTROL FOR THE TEST ABOVE. Asking the outcome must not launder a real
    failure into a completion — that would be the same defect pointing the other
    way, and Phase 4 would then MATERIALISE a merge nobody performed."""
    def _boom(*a, **k):
        raise subprocess.CalledProcessError(1, "gh", stderr="not mergeable")

    monkeypatch.setattr(merge_pr.subprocess, "run", _boom)
    monkeypatch.setattr(merge_pr, "_gh_json", lambda a, r: {"state": "OPEN"})

    root = tmp_path / "journal"
    root.mkdir(mode=0o700, parents=True)
    bag = open_bag(root, "run-merge-failed")
    emitter = Emitter.for_run(bag, writer=None, journal_root=root)
    with emitting_into(emitter):
        assert merge_pr.merge_one("1", REPO) == "not mergeable"

    lines = (emitter.writer_dir / EVENTS_FILE).read_text().splitlines()
    kinds = [decode_event(line).kind for line in lines]
    assert kinds == [EventKind.INTENT, EventKind.STORE_WRITE_FAILURE]


def test_a_GENUINELY_failed_merge_is_still_reported(monkeypatch) -> None:
    """THE CONTROL. Asking the outcome must not swallow a real failure."""
    def _boom(*a, **k):
        raise subprocess.CalledProcessError(1, "gh", stderr="not mergeable")

    monkeypatch.setattr(merge_pr.subprocess, "run", _boom)
    monkeypatch.setattr(merge_pr, "_gh_json", lambda a, r: {"state": "OPEN"})
    assert merge_pr.merge_one("1", REPO) == "not mergeable"


# ---------------------------------------------------------------------------
# THE READ THAT RESOLVES THE OUTCOME. Moving "did it actually merge?" inside
# `perform` made the journal and the report derive from ONE answer — and left
# that answer resting on a single unretried call whose failure was silently
# spelled "not merged". `gh pr merge` exiting non-zero is the NORMAL case here,
# so the read sits on the ordinary path: one transient `gh` failure on it was
# enough to journal a merge that LANDED as a write that did not happen.


def test_a_TRANSIENTLY_unreadable_outcome_is_RE_ASKED_and_the_merge_COMPLETES(
        monkeypatch, tmp_path: Path) -> None:
    """A blip on the state read must not become a permanent wrong record.

    THE FIX IS THE RE-ASK, AND THIS IS THE TEST THAT MEASURES IT. With one
    attempt, the first `None` is read as "not merged" and `paired_write` appends
    a `store_write_failure` for a merge that landed — into an append-only
    journal, so `applied_intents` declines that intent forever.
    """
    def _boom(*a, **k):
        raise subprocess.CalledProcessError(1, "gh",
                                            stderr="failed to delete local branch")

    answers = [None, None, {"state": "MERGED"}]
    monkeypatch.setattr(merge_pr.subprocess, "run", _boom)
    monkeypatch.setattr(merge_pr, "_gh_json", lambda a, r: answers.pop(0))
    monkeypatch.setattr(merge_pr.time, "sleep", lambda s: None)

    root = tmp_path / "journal"
    root.mkdir(mode=0o700, parents=True)
    bag = open_bag(root, "run-merge-transient")
    emitter = Emitter.for_run(bag, writer=None, journal_root=root)
    with emitting_into(emitter):
        assert merge_pr.merge_one("1", REPO) is None

    assert answers == [], "the re-ask stopped before the answer arrived"
    lines = (emitter.writer_dir / EVENTS_FILE).read_text().splitlines()
    kinds = [decode_event(line).kind for line in lines]
    assert kinds == [EventKind.INTENT, EventKind.COMPLETION], (
        f"a landed merge was journaled as {[k.value for k in kinds]} because the "
        f"outcome read was not re-asked. The journal is append-only; this record "
        f"cannot be corrected later.")


def test_an_UNREAD_outcome_does_not_present_GH_S_STDERR_as_the_verdict(
        monkeypatch) -> None:
    """The verdict was never read, and the detail must say that rather than
    quoting `gh pr merge`'s cleanup error as though it were the answer.

    `failed to delete local branch` is a sentence about the BRANCH DELETE. Handed
    back as the merge outcome it reads as "the PR did not merge", which is the
    one thing this read exists to establish and the one thing nobody established.
    """
    def _boom(*a, **k):
        raise subprocess.CalledProcessError(1, "gh",
                                            stderr="failed to delete local branch")

    monkeypatch.setattr(merge_pr.subprocess, "run", _boom)
    monkeypatch.setattr(merge_pr, "_gh_json", lambda a, r: None)
    monkeypatch.setattr(merge_pr.time, "sleep", lambda s: None)

    detail = merge_pr.merge_one("1", REPO)
    assert detail is not None
    assert detail.startswith(merge_pr.UNRESOLVED_MERGE_PREFIX), (
        f"an unread verdict was reported as {detail!r} — indistinguishable from "
        f"a merge that was read and found not to have happened.")
    # The stderr is still CARRIED, because an operator needs it. What changed is
    # that it is attributed rather than presented as the verdict.
    assert "failed to delete local branch" in detail


def test_a_verdict_that_WAS_read_is_NOT_reported_as_unread(monkeypatch) -> None:
    """THE DISCRIMINATION CONTROL. A prefix that appears on every failed merge
    tells an operator nothing: the whole value of `UNRESOLVED_MERGE_PREFIX` is
    that a genuinely-refused merge does NOT carry it."""
    def _boom(*a, **k):
        raise subprocess.CalledProcessError(1, "gh", stderr="not mergeable")

    monkeypatch.setattr(merge_pr.subprocess, "run", _boom)
    monkeypatch.setattr(merge_pr, "_gh_json", lambda a, r: {"state": "OPEN"})
    monkeypatch.setattr(merge_pr.time, "sleep", lambda s: None)

    detail = merge_pr.merge_one("1", REPO)
    assert detail == "not mergeable"
    assert merge_pr.UNRESOLVED_MERGE_PREFIX not in detail


def test_a_reply_that_PARSES_but_carries_no_state_is_UNREAD_not_an_answer(
        monkeypatch) -> None:
    """`{}` decodes cleanly and `.get("state")` on it returns the same `None` an
    unreadable call does. Reading a missing field as an answer is the same
    conflation one level in."""
    monkeypatch.setattr(merge_pr, "_gh_json", lambda a, r: {})
    monkeypatch.setattr(merge_pr.time, "sleep", lambda s: None)
    assert merge_pr._merge_state("1", REPO) is None


def test_a_gh_READ_rides_out_a_TRANSIENT_failure(monkeypatch) -> None:
    """`_gh_json` was the one `gh` read in `modules/` that bypassed the fleet's
    bounded wrapper, so a 503 on any of its three callers was one attempt and a
    `None`. Driven through `gh_attempt`'s own retry loop rather than asserting
    which function is called."""
    replies = [
        subprocess.CompletedProcess(["gh"], 1, stdout="",
                                    stderr="HTTP 503: No server is currently "
                                           "available to service your request."),
        subprocess.CompletedProcess(["gh"], 0, stdout='{"state": "MERGED"}',
                                    stderr=""),
    ]
    monkeypatch.setattr(merge_pr.act, "run_bounded", lambda *a, **k: replies.pop(0))
    monkeypatch.setattr(merge_pr.act.time, "sleep", lambda s: None)

    assert merge_pr._gh_json(["pr", "view", "1", "--json", "state"],
                             REPO) == {"state": "MERGED"}
    assert replies == [], "the transient reply was not retried past"

"""The parent reads the CI verdict, so MERGE is unreachable on a red tree.

WHY THIS IS IN THE PARENT AND NOT A PROMPT. Telling the review agent to check
and withhold MERGE is a convention, and an agent can reason past a convention —
"unrelated failure, proceeding" is the exact shape being guarded against. In the
parent the agent never gets a verdict to give.

WHY IT MATTERS HERE. Branch protection was removed from this repo on 2026-08-09
because it was available on 12 of 33 org repos and could not be replicated on
the two that matter most. `suite` has run on every PR since and nothing consumed
its verdict, so `gh pr merge` succeeded on red. This closes that.

THE THIRD STATE IS THE ONE THAT GETS FUDGED. "No checks reported" is NOT green,
and a silent skip is the filtered-gate defect wearing different clothes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from modules.assistant.build import build_activities as act  # noqa: E402
from modules.assistant.build.build_activities import POLICY_PATH, CiVerdict  # noqa: E402


def _gh(monkeypatch, payload, *, stdout=None):
    """Stand in for `gh pr checks --json name,state`."""
    class R:
        def __init__(self): self.stdout = stdout if stdout is not None else json.dumps(payload)
    monkeypatch.setattr(act.subprocess, "run", lambda *a, **k: R())


@pytest.fixture
def repo(tmp_path):
    """A target repo declaring `suite` blocking and CodeQL advisory."""
    d = tmp_path / POLICY_PATH
    d.parent.mkdir(parents=True, exist_ok=True)
    d.write_text("blocking:\n  - suite\nadvisory:\n  - name: CodeQL\n    reason: default setup\n")
    return tmp_path


def test_this_repo_declares_its_own_policy_and_it_names_a_blocking_check():
    """Guards every test below AND this repo's own gate.

    An empty or absent declaration routes everything to NO_CHECKS, which would
    make the tests below pass vacuously and would silently un-gate this repo.
    """
    import yaml
    path = Path(__file__).resolve().parents[5] / POLICY_PATH
    assert path.is_file(), f"{POLICY_PATH} is missing — this repo declares no gate"
    doc = yaml.safe_load(path.read_text())
    assert doc.get("blocking"), "the blocking list is empty — the gate cannot block anything"
    assert "suite" in doc["blocking"], "the test runner is not declared blocking"


def test_a_failing_blocking_check_is_RED_and_names_it(monkeypatch, repo):
    _gh(monkeypatch, [{"name": "suite", "state": "FAILURE"}])
    verdict, failed = act.ci_verdict("1", repo_root=repo)
    assert verdict is CiVerdict.RED
    assert failed == ["suite"], "the runway must name which check failed"


def test_all_green_is_GREEN(monkeypatch, repo):
    _gh(monkeypatch, [{"name": "suite", "state": "SUCCESS"}])
    assert act.ci_verdict("1", repo_root=repo)[0] is CiVerdict.GREEN


def test_an_ADVISORY_check_failing_does_NOT_block(monkeypatch, repo):
    """The carve-out, pinned. `gh pr checks` reports JOB STATUS: a CodeQL job
    failure means the scan did not COMPLETE, not that it FOUND something.
    Gating on it would let the scanner breaking halt the fleet."""
    _gh(monkeypatch, [
        {"name": "suite", "state": "SUCCESS"},
        {"name": "CodeQL", "state": "FAILURE"},
        {"name": "Analyze (python)", "state": "FAILURE"},
    ])
    assert act.ci_verdict("1", repo_root=repo)[0] is CiVerdict.GREEN


def test_an_advisory_check_alone_is_GATE_DID_NOT_RUN(monkeypatch, repo):
    """If the gating check did not run at all, advisory checks passing must not
    be read as a pass — that is the substitution this whole gate exists to stop.

    This asserted NO_CHECKS until 2026-08-13. The `repo` fixture DECLARES `suite`
    blocking, so "no gating check reported" here means the declared gate did not
    run — which is the state that must stop the fleet, not the one that means
    "this repo has no gate".
    """
    _gh(monkeypatch, [{"name": "CodeQL", "state": "SUCCESS"}])
    verdict, missing = act.ci_verdict("1", repo_root=repo)
    assert verdict is CiVerdict.GATE_DID_NOT_RUN
    assert missing == ["suite"], "the runway must name which declared gate is absent"


def test_no_gating_check_reported_is_GATE_DID_NOT_RUN(monkeypatch, repo):
    _gh(monkeypatch, [])
    assert act.ci_verdict("1", repo_root=repo)[0] is CiVerdict.GATE_DID_NOT_RUN


def test_empty_output_is_UNREADABLE_CHECKS_not_a_silent_gate(monkeypatch, repo):
    """Empty stdout means `gh` FAILED — it writes errors to stderr.

    THIS TEST USED TO EXPECT GATE_DID_NOT_RUN, and that expectation cost PR #92
    three rebuilds on 2026-08-14. Its original point stands and is unchanged:
    an empty reply is NOT green. What it got wrong is which not-green state.

    `gh pr checks` prints a JSON array when it can answer — `[]` when a PR has
    no checks. Empty STDOUT is the shape of a failure, and reading it as "the
    gate reported nothing" routes an environment failure to HOLD_REDISPATCH,
    which rebuilds. It rebuilt three times against a PR that was OPEN,
    MERGEABLE and green on all four checks throughout.
    """
    _gh(monkeypatch, None, stdout="")
    assert act.ci_verdict("1", repo_root=repo)[0] is CiVerdict.UNREADABLE_CHECKS


def test_a_repo_that_declares_NO_gate_is_NO_CHECKS(monkeypatch, tmp_path):
    """THE CONTROL, and the whole reason the split is two states rather than one.

    A repo with an empty blocking list has no gate to wait for, and holding it
    forever would be wrong. The three tests above and this one differ ONLY in
    whether a gate was declared — which is exactly the distinction that was
    missing, and the one that let two PRs proceed on a gate that never ran.
    """
    d = tmp_path / POLICY_PATH
    d.parent.mkdir(parents=True, exist_ok=True)
    d.write_text("blocking: []\nadvisory:\n  - name: CodeQL\n    reason: default setup\n")
    _gh(monkeypatch, [])
    assert act.ci_verdict("1", repo_root=tmp_path)[0] is CiVerdict.NO_CHECKS


def test_unreadable_output_fails_into_the_state_that_STOPS(monkeypatch, repo):
    """Malformed JSON is not a pass. Fail into the state that reports, never
    into the one that proceeds silently."""
    _gh(monkeypatch, None, stdout="not json at all")
    verdict = act.ci_verdict("1", repo_root=repo)[0]
    # `is not GREEN` was the whole assertion here, and it did not pin the
    # docstring above it: NO_CHECKS satisfies it and PROCEEDS — it appears in no
    # HOLD branch in `build_workflow`. So unparseable CI output could reach a
    # MERGE verdict on a repo that declares a gate, while a green suite reported
    # this test as covering it. Name the state that actually stops.
    assert verdict is CiVerdict.UNREADABLE_CHECKS, (
        f"unparseable CI output produced {verdict}, which does not HOLD"
    )


@pytest.mark.parametrize("state", ["SUCCESS", "SKIPPED", "NEUTRAL"])
def test_non_failing_states_do_not_block(monkeypatch, repo, state):
    _gh(monkeypatch, [{"name": "suite", "state": state}])
    assert act.ci_verdict("1", repo_root=repo)[0] is CiVerdict.GREEN


@pytest.mark.parametrize("state", ["FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "PENDING"])
def test_anything_that_is_not_a_pass_blocks(monkeypatch, repo, state):
    """Deliberately inclusive: an unrecognised state must block rather than pass.
    A new state GitHub adds later must not silently become green."""
    _gh(monkeypatch, [{"name": "suite", "state": state}])
    assert act.ci_verdict("1", repo_root=repo)[0] is CiVerdict.RED


# --- The declaration itself: two states that did not exist before -------------


def test_a_malformed_declaration_STOPS_rather_than_skipping(monkeypatch, tmp_path):
    """A declaration that EXISTS and cannot be read is a different fact from no
    declaration. Collapsing them is how the skip path becomes the new exit."""
    d = tmp_path / POLICY_PATH
    d.parent.mkdir(parents=True, exist_ok=True)
    d.write_text("blocking: [unclosed\n  - broken: : :\n")
    _gh(monkeypatch, [{"name": "suite", "state": "SUCCESS"}])
    assert act.ci_verdict("1", repo_root=tmp_path)[0] is CiVerdict.UNREADABLE_POLICY


def test_a_declaration_that_is_not_a_mapping_is_unreadable(monkeypatch, tmp_path):
    d = tmp_path / POLICY_PATH
    d.parent.mkdir(parents=True, exist_ok=True)
    d.write_text("- just\n- a\n- list\n")
    _gh(monkeypatch, [{"name": "suite", "state": "SUCCESS"}])
    assert act.ci_verdict("1", repo_root=tmp_path)[0] is CiVerdict.UNREADABLE_POLICY


def test_an_absent_declaration_is_NO_CHECKS_not_unreadable(monkeypatch, tmp_path):
    """A repo may legitimately have no gate. That is a skip, not a stop."""
    _gh(monkeypatch, [{"name": "suite", "state": "SUCCESS"}])
    assert act.ci_verdict("1", repo_root=tmp_path)[0] is CiVerdict.NO_CHECKS


def test_a_DIFFERENT_repos_check_name_gates_it(monkeypatch, tmp_path):
    """The finding that produced this change: a hardcoded ("suite",) meant the
    MDC side's `master-test-tier` matched nothing and every PR skipped."""
    d = tmp_path / POLICY_PATH
    d.parent.mkdir(parents=True, exist_ok=True)
    d.write_text("blocking:\n  - master-test-tier\n")
    _gh(monkeypatch, [{"name": "master-test-tier", "state": "FAILURE"}])
    v, failed = act.ci_verdict("1", repo_root=tmp_path)
    assert v is CiVerdict.RED and failed == ["master-test-tier"]


def test_a_check_declared_NEITHER_way_is_reported_by_name(monkeypatch, repo):
    """The Testing Standard admits no third state. An undeclared check is
    surfaced, never silently gated: it must not halt the fleet, and must not
    hide either."""
    _gh(monkeypatch, [
        {"name": "suite", "state": "SUCCESS"},
        {"name": "brand-new-scanner", "state": "SUCCESS"},
    ])
    v, undeclared = act.ci_verdict("1", repo_root=repo)
    assert v is CiVerdict.GREEN
    assert undeclared == ["brand-new-scanner"]


# ---------------------------------------------------------------------------
# THE RACE. Settled is not the same as present, and conflating them cost a
# build its entire loop budget on 2026-08-14.
# ---------------------------------------------------------------------------


def _gh_sequence(monkeypatch, payloads):
    """`gh pr checks` returning a different payload on each successive call."""
    calls = {"n": 0}

    class R:
        def __init__(self, body): self.stdout = body

    def run(*a, **k):
        i = min(calls["n"], len(payloads) - 1)
        calls["n"] += 1
        return R(json.dumps(payloads[i]))

    monkeypatch.setattr(act.subprocess, "run", run)
    monkeypatch.setattr(act.time, "sleep", lambda *_: None)
    return calls


def test_wait_for_ci_keeps_waiting_while_the_DECLARED_gate_is_ABSENT(monkeypatch, repo):
    """An empty check list seconds after a push is NOT settled.

    THE BUG THIS PINS. `wait_for_ci` returned True the instant no PENDING
    appeared, and an empty payload contains no PENDING. GitHub had simply not
    created the run yet. That was harmless while an absent gate merely warned
    and proceeded; once an absent gate became a HOLD, the same race became:
    push, see nothing, hold, loop back, push, see nothing — three times, then
    the loop budget was spent, with the PR green and clean by the time a human
    looked.
    """
    calls = _gh_sequence(monkeypatch, [
        [],                                          # run not created yet
        [{"name": "CodeQL", "state": "SUCCESS"}],    # advisory arrives first
        [{"name": "CodeQL", "state": "SUCCESS"},
         {"name": "suite", "state": "SUCCESS"}],     # the gate finally reports
    ])
    assert act.wait_for_ci("1", repo_root=repo) is True
    assert calls["n"] >= 3, (
        f"returned after {calls['n']} poll(s) — it stopped before the declared "
        f"gate appeared, which is the race this test exists for"
    )


def test_wait_for_ci_returns_immediately_when_the_gate_HAS_reported(monkeypatch, repo):
    """THE CONTROL. Waiting for presence must not become waiting always."""
    calls = _gh_sequence(monkeypatch, [[{"name": "suite", "state": "SUCCESS"}]])
    assert act.wait_for_ci("1", repo_root=repo) is True
    assert calls["n"] == 1, f"polled {calls['n']} times for an already-reported gate"


def test_wait_for_ci_without_a_policy_still_settles_on_absence(monkeypatch):
    """A repo that declares no gate has nothing to wait for and must not hang."""
    calls = _gh_sequence(monkeypatch, [[]])
    assert act.wait_for_ci("1") is True
    assert calls["n"] == 1


def test_GATE_DID_NOT_RUN_does_not_also_report_its_gate_as_UNDECLARED(monkeypatch, repo):
    """The two messages contradicted each other on one run.

    `ci_verdict` returns the ABSENT gate's names as its second value so the
    runway can name them. The UNDECLARED-CHECKS branch reads that same value as
    "checks that ran and are unclassified" — so a single run reported `suite`
    as unclassified and as declared-blocking in consecutive lines.
    """
    _gh(monkeypatch, [])
    verdict, names = act.ci_verdict("1", repo_root=repo)
    assert verdict is CiVerdict.GATE_DID_NOT_RUN
    assert names == ["suite"], "the absent gate must be named for the runway"
    # The guard lives in the workflow; assert it is present rather than re-deriving it.
    wf = (Path(__file__).resolve().parents[2] / "modules" / "assistant" / "build"
          / "build" / "build_workflow.py").read_text()
    assert "CiVerdict.GATE_DID_NOT_RUN)" in wf and "if extra and verdict_state not in" in wf, (
        "the UNDECLARED-CHECKS branch no longer excludes GATE_DID_NOT_RUN, so an "
        "absent gate will again be reported as an unclassified check that ran"
    )


# ---------------------------------------------------------------------------
# A FAILED READ IS NOT AN ABSENT GATE. Conflating them turned a green PR into
# three rebuilds on 2026-08-14.
# ---------------------------------------------------------------------------


class _Reply:
    """One `gh pr checks` invocation, including the channels the old code ignored."""

    def __init__(self, stdout: str, stderr: str = "", returncode: int = 0) -> None:
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode


def _gh_replies(monkeypatch, replies, *, max_wait: float = 60.0):
    """`gh` returning each reply in turn, against a FAKE clock.

    The clock is fake because these tests must reach the DEADLINE, and the real
    one is 600 seconds. `sleep` advances it instead of blocking, so a test that
    exercises deadline expiry costs nothing.
    """
    calls = {"n": 0}
    clock = {"t": 0.0}

    def run(*_a, **_k):
        reply = replies[min(calls["n"], len(replies) - 1)]
        calls["n"] += 1
        return reply

    monkeypatch.setattr(act.subprocess, "run", run)
    monkeypatch.setattr(act.time, "monotonic", lambda: clock["t"])
    monkeypatch.setattr(act.time, "sleep", lambda s: clock.__setitem__("t", clock["t"] + max(s, 1.0)))
    monkeypatch.setattr(act, "CI_MAX_WAIT_SECONDS", max_wait)
    return calls


def test_an_unreadable_gh_reply_is_not_mistaken_for_settled_CI(monkeypatch):
    """The defect that cost PR #92 three rebuilds.

    `gh pr checks` exits non-zero whenever checks are FAILING or PENDING, so the
    return code cannot separate a red pipeline from a broken `gh`. The old code
    tested `"PENDING" not in result.stdout.upper()` BEFORE parsing, so an empty
    stdout — every failed invocation — read as "settled", then parsed to an empty
    name set, which read as "the declared gate has not appeared yet".

    A failed read was therefore INDISTINGUISHABLE from a missing gate: it burned
    the full deadline, returned False, and the caller turned that into a HOLD and
    a rebuild. Measured against a PR that was OPEN, MERGEABLE and green on all
    four checks throughout.

    THE VERDICT ITSELF IS NOT THIS FUNCTION'S JOB — `ci_verdict` classifies an
    unreadable read as UNREADABLE_CHECKS, and `build_workflow` states the rule
    this one obeys: "HOLD, never `exit 1`: killing the run discards a diff two
    passes just built." This function only waits, and must not report a failed
    read as a finished pipeline.
    """
    calls = _gh_replies(monkeypatch, [
        _Reply("", stderr="gh: could not resolve to a Repository", returncode=1),
    ])
    assert act.wait_for_ci("1") is False, (
        "a repo that declares no gate took the `if not blocking: return True` "
        "path the instant the settled test passed — and the settled test ran on "
        "RAW STDOUT before parsing, so an empty reply from a FAILED `gh` read as "
        "settled. A broken read reported CI as done."
    )
    assert calls["n"] > 1, (
        f"gave up after {calls['n']} call — an unreadable reply is retried, "
        f"because a transient `gh` failure is not an answer about CI"
    )


def test_a_TRANSIENT_read_failure_is_retried_rather_than_fatal(monkeypatch, repo):
    """One bad reply is a blip; the deadline is what makes it fatal.

    Separated from the test above deliberately — 'raises when it never works'
    and 'recovers when it works later' are different guarantees, and a single
    test covering only the first would pass a version that gave up instantly.
    """
    calls = _gh_replies(monkeypatch, [
        _Reply("", stderr="gh: API rate limit exceeded", returncode=1),
        _Reply(json.dumps([{"name": "suite", "state": "SUCCESS"}])),
    ])
    assert act.wait_for_ci("1", repo_root=repo) is True
    assert calls["n"] == 2, f"expected one retry, got {calls['n']} call(s)"


def test_a_READABLE_reply_whose_gate_never_appears_still_returns_False(monkeypatch, repo):
    """THE CONTROL. Raising must not swallow the answer `False` already carried.

    A gate that genuinely never reports — the usual cause being a conflicted PR
    whose merge ref cannot be computed — is a real, informative outcome that the
    caller handles with --ci-unsettled. If this ever raises, the fix above has
    eaten a legitimate verdict.
    """
    _gh_replies(monkeypatch, [_Reply(json.dumps([{"name": "CodeQL", "state": "SUCCESS"}]))])
    assert act.wait_for_ci("1", repo_root=repo) is False


def test_an_IN_PROGRESS_check_is_NOT_settled(monkeypatch, repo):
    """`gh` says IN_PROGRESS, and the settled test asked about PENDING.

    OBSERVED 2026-08-16 while polling PR #94: `IN_PROGRESS  suite`, with `suite`
    the declared blocking gate. Under `"PENDING" not in states` that reads as
    settled AND the gate is present, so the wait returns True and the review
    proceeds against a pipeline still running — the same false-green removed
    from three other controls over the preceding two days.

    THE FIX IS AN ALLOW-LIST, and that is the point rather than an
    implementation detail. Testing for one non-terminal name asks what the guard
    looks FOR and never what it is blind to; `gh` also emits QUEUED, and a state
    GitHub adds later is unknown. Unknown must mean keep waiting.
    """
    calls = _gh_replies(monkeypatch, [
        _Reply(json.dumps([{"name": "suite", "state": "IN_PROGRESS"}])),
        _Reply(json.dumps([{"name": "suite", "state": "SUCCESS"}])),
    ])
    assert act.wait_for_ci("1", repo_root=repo) is True
    assert calls["n"] == 2, (
        f"returned after {calls['n']} poll(s) — an IN_PROGRESS gate was read as "
        f"settled, so the review would run against unfinished CI"
    )


def test_an_unknown_check_state_is_NOT_settled(monkeypatch, repo):
    """A state nobody has seen must hold, not proceed.

    Split from the test above deliberately: that one pins a state `gh` emits
    today, this one pins the CLOSED-SET property that makes the guard survive
    GitHub adding another.
    """
    calls = _gh_replies(monkeypatch, [
        _Reply(json.dumps([{"name": "suite", "state": "SOME_FUTURE_STATE"}])),
        _Reply(json.dumps([{"name": "suite", "state": "SUCCESS"}])),
    ])
    assert act.wait_for_ci("1", repo_root=repo) is True
    assert calls["n"] == 2, "an unrecognised state was treated as terminal"

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

import ast
import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from modules.assistant import assistant_activities as shared  # noqa: E402
# `act` IS THE SHARED ACTIVITIES MODULE NOW. The CI reads were promoted out of
# `build/build_activities.py` per §10.1 rule 3 when their consumer count reached
# six across three families; the pure half (`POLICY_PATH`, `CiVerdict`,
# `ci_gate`) went to `routing`. The alias is kept so the ~40 activity-driving
# tests below read unchanged — what moved is the address, not the behaviour.
from modules.assistant import assistant_activities as act  # noqa: E402
from modules.assistant import routing  # noqa: E402
from modules.assistant.routing import POLICY_PATH, CiVerdict, Verdict  # noqa: E402


def _gh(monkeypatch, payload, *, stdout=None, stderr="", returncode=0):
    """Stand in for `gh pr checks --json name,state`.

    IT CARRIES ALL THREE CHANNELS because `ci_verdict` now reads this through
    `gh_attempt`, which classifies on `returncode` and `stderr` before handing
    the reply back unjudged. A fake with only `stdout` was enough while the call
    was a bare `subprocess.run`; it is not enough to model one that can retry,
    and a fake that cannot express a transient failure cannot test one.
    """
    body = stdout if stdout is not None else json.dumps(payload)
    monkeypatch.setattr(
        act.subprocess, "run",
        lambda *a, **k: subprocess.CompletedProcess(
            a[0] if a else [], returncode, stdout=body, stderr=stderr))


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

    Empty STDOUT is the shape of a failure, and reading it as "the gate reported
    nothing" routes an environment failure to HOLD_REDISPATCH, which rebuilds. It
    rebuilt three times against a PR that was OPEN, MERGEABLE and green on all
    four checks throughout.

    THIS DOCSTRING ALSO USED TO CLAIM `gh` "prints a JSON array when it can
    answer — `[]` when a PR has no checks", AND THAT IS FALSE. On a branch with
    no checks at all it prints `no checks reported on the '<branch>' branch` to
    STDERR and leaves stdout empty — the same shape as a failure. The claim was
    never tested, and the case it got wrong is the one below. What keeps THIS
    test honest is the empty stderr: with nothing on either channel, unreadable
    remains the only correct reading.
    """
    _gh(monkeypatch, None, stdout="")
    assert act.ci_verdict("1", repo_root=repo)[0] is CiVerdict.UNREADABLE_CHECKS


# `gh`'s exact reply on a branch with no checks, verbatim from the MDC run.
_NO_CHECKS_STDERR = "no checks reported on the 'plan-draft/mdc-rollout-phase-docs' branch"


def test_a_repo_with_NO_CI_AT_ALL_is_not_mistaken_for_an_unreadable_reply(
        monkeypatch, tmp_path):
    """The block that cost MDC a $19 planning run its disposition.

    `mdc-master-planning` has an empty `.github/workflows/` — correctly, it is a
    documentation repo. Every `gh pr checks` reply was "no checks reported",
    every reply read as unparseable, `wait_for_ci` burned its 600-second
    deadline, `ci_verdict` returned UNREADABLE_CHECKS and the gate held with
    "more passes cannot produce a human decision". `review-pr` never ran.

    IT IS DETERMINISTIC, WHICH IS WHAT MAKES IT A BLOCK RATHER THAN A HICCUP: the
    condition is permanent absence, so every future run holds the same way. Four
    of six repos on that host have no CI, and `plan` is the workflow they need
    most — they are planning-heavy and code-light.

    NO POLICY HERE, DELIBERATELY. `tmp_path` carries no `check-policy.yaml`, which
    is the shape of a repo that declares no gate, and NO_CHECKS is then the right
    answer. The companion test below covers the repo that DOES declare one.
    """
    _gh(monkeypatch, None, stdout="", stderr=_NO_CHECKS_STDERR, returncode=1)
    verdict, _extra = act.ci_verdict("1", repo_root=tmp_path)
    assert verdict is CiVerdict.NO_CHECKS, (
        f"a repo with no CI read as {verdict}. There is nothing to gate on and "
        f"nothing a human can rule on — holding here blocks every planning run "
        f"on every repo without a pipeline, permanently."
    )


def test_a_DECLARED_gate_that_reports_NOTHING_still_holds(monkeypatch, repo):
    """The other half, and the reason this is not a fail-open.

    Same `gh` reply as the test above, against a repo whose `check-policy.yaml`
    names `suite` blocking. Absence now means the declared gate did not run —
    the conflicted-merge-ref case — and that must still stop the run. Reading
    "no checks reported" as a pass everywhere would weaken the gate for repos
    that HAVE CI in order to unblock repos that do not.
    """
    _gh(monkeypatch, None, stdout="", stderr=_NO_CHECKS_STDERR, returncode=1)
    verdict, extra = act.ci_verdict("1", repo_root=repo)
    assert verdict is CiVerdict.GATE_DID_NOT_RUN, (
        f"a declared-but-absent gate read as {verdict} — the repo expects `suite` "
        f"and nothing reported it")
    assert extra == ["suite"], f"the runway cannot name the absent gate: {extra}"


def test_a_repo_with_NO_CI_stops_polling_on_the_FIRST_reply(monkeypatch, tmp_path):
    """600 seconds spent on an answer the first call already contained.

    The poll is what made this expensive rather than merely wrong. `parse_checks`
    returning `[]` makes the reply a READ, so the settled test sees an empty
    state set, `blocking` is empty, and the loop returns on iteration one.

    THE CALL COUNT IS THE ASSERTION, not the elapsed time: a wall-clock test
    would pass on a slow machine that polled twice, and polling twice is the
    defect in miniature.
    """
    calls = []

    def one_reply(*a, **k):
        calls.append(a[0] if a else [])
        return subprocess.CompletedProcess([], 1, stdout="", stderr=_NO_CHECKS_STDERR)

    monkeypatch.setattr(act.subprocess, "run", one_reply)
    monkeypatch.setattr(act.time, "sleep", lambda *_: None)
    assert act.wait_for_ci("1", repo_root=tmp_path) is True, (
        "a repo with no CI and no declared gate has nothing to settle — the wait "
        "must return, not spend the deadline")
    assert len(calls) == 1, (
        f"`gh pr checks` was called {len(calls)} times for an answer that was "
        f"complete on the first reply")


def test_a_transient_503_on_the_gate_read_is_RIDDEN_OUT_not_turned_into_a_HOLD(
    monkeypatch, repo,
):
    """THE ONE-SHOT READ THAT DECIDES A MERGE, AND IT HAD NO RETRY.

    `wait_for_ci` re-reads inside its own deadline loop, so a blip there heals
    itself. This call has no loop at all: one transient 503 leaves stdout empty,
    which parses as nothing, which is UNREADABLE_CHECKS, which `build_workflow`
    routes to a HOLD a human has to clear. That is the exact harm the `gh` retry
    was built for, on the highest-consequence `gh` read in the fleet, and it sat
    two files away from the fix.

    THE VERDICT IS THE ASSERTION, NOT THE ATTEMPT COUNT. What matters to the
    operator is that a blip no longer stops the run; the attempt count is
    asserted beside it only so a fake that never failed cannot pass this
    vacuously.
    """
    replies = [
        subprocess.CompletedProcess([], 1, stdout="",
                                    stderr="HTTP 503: No server is currently available"),
        subprocess.CompletedProcess([], 0, stdout=json.dumps(
            [{"name": "suite", "state": "SUCCESS"}]), stderr=""),
    ]
    calls = {"n": 0}

    def run(*_a, **_k):
        r = replies[min(calls["n"], len(replies) - 1)]
        calls["n"] += 1
        return r

    monkeypatch.setattr(act.subprocess, "run", run)
    monkeypatch.setattr(shared.time, "sleep", lambda _s: None)

    assert act.ci_verdict("1", repo_root=repo)[0] is CiVerdict.GREEN, (
        "one transient 503 still turns a green PR into a HOLD")
    assert calls["n"] == 2, (
        f"the gate read was attempted {calls['n']} times — 1 means the retry "
        f"never fired and this test proves nothing")


def test_a_merely_RED_pr_still_costs_exactly_one_gate_read(monkeypatch, repo):
    """THE NEGATIVE CONTROL FOR THE TEST ABOVE, and the reason routing this
    call through `gh_attempt` is safe at all.

    `gh pr checks` exits NON-ZERO whenever checks are failing or pending — that
    is why this function classifies by parsing rather than by exit code. If the
    retry read the exit code the way a naive one would, every red PR would pay
    the full backoff before reporting what it already knew. It does not: a red
    reply carries no HTTP status, so the classifier calls it terminal and spends
    one attempt.
    """
    calls = {"n": 0}

    def run(*_a, **_k):
        calls["n"] += 1
        return subprocess.CompletedProcess(
            [], 1, stdout=json.dumps([{"name": "suite", "state": "FAILURE"}]),
            stderr="")

    monkeypatch.setattr(act.subprocess, "run", run)
    monkeypatch.setattr(shared.time, "sleep", lambda _s: None)

    verdict, failed = act.ci_verdict("1", repo_root=repo)
    assert verdict is CiVerdict.RED and failed == ["suite"]
    assert calls["n"] == 1, (
        f"a legitimately red PR spent {calls['n']} gate reads and the full "
        f"backoff — the retry is reading the exit code, which this function "
        f"documents as meaningless here")


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


def test_wait_for_ci_without_a_policy_still_settles_on_absence(monkeypatch, tmp_path):
    """A repo that declares no gate has nothing to wait for and must not hang.

    `tmp_path` IS A REAL TREE THAT DECLARES NOTHING, which is a different input
    from the `wait_for_ci("1")` this used to be. `repo_root` became REQUIRED on
    2026-08-20 — see `ci_verdict` — so "no policy" is now expressed by handing it
    a tree with no `check-policy.yaml` in it, not by withholding the tree. The
    behaviour under test is untouched: `read_check_policy` finds no file, returns
    an empty blocking list, and the `if not blocking: return True` path is the
    one that runs.
    """
    calls = _gh_sequence(monkeypatch, [[]])
    assert act.wait_for_ci("1", repo_root=tmp_path) is True
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
    # DRIVEN, NOT GREPPED. This used to assert two substrings were present in
    # `build_workflow.py`, which is a claim resting on prose that can be reworded
    # — and it broke the moment the cascade was promoted to `helper.ci_gate` for
    # `build_minor` to share, while the property it names was untouched. Calling
    # the decision is strictly stronger and now covers BOTH parents at once.
    hold, notes = routing.ci_gate(verdict, names, pr="1", repo_target=None)
    assert hold is Verdict.HOLD_REDISPATCH
    undeclared = [n for n in notes if "UNDECLARED CHECKS" in n]
    assert not undeclared, (
        "the UNDECLARED-CHECKS branch no longer excludes GATE_DID_NOT_RUN, so an "
        f"absent gate is again reported as an unclassified check that ran: {undeclared}"
    )
    assert any("declares suite blocking" in n for n in notes), (
        "the absent gate must still be named to the operator"
    )


def _dispatches_review_ungated(source: str) -> bool:
    """Does this module dispatch `review-pr` without reading the CI verdict?

    SPLIT OUT SO A CONTROL CAN DRIVE IT on source the tree does not contain —
    the walk below is floored, and a floor stays green over a predicate that has
    silently begun answering `False` for everything.
    """
    calls = {n.func.attr if isinstance(n.func, ast.Attribute) else
             getattr(n.func, "id", "")
             for n in ast.walk(ast.parse(source))
             if isinstance(n, ast.Call)}
    return "run_review" in calls and "ci_gate" not in calls


def test_the_UNGATED_PARENT_predicate_discriminates_on_a_literal() -> None:
    """Positive control for the walk below, on source that is not in the tree."""
    assert _dispatches_review_ungated(
        "def f(x):\n    return review_pr.run_review(x)\n"
    ), "the predicate no longer reports a parent that dispatches review with no gate"
    assert not _dispatches_review_ungated(
        "def f(x):\n    h, n = routing.ci_gate(x)\n    return review_pr.run_review(x)\n"
    ), "the predicate now reports a correctly gated parent, so it would fail on good code"
    assert not _dispatches_review_ungated(
        "def f(x):\n    return x\n"
    ), "the predicate fires on a module that dispatches no review at all"


#: Every module under `modules/assistant` that dispatches `review-pr`, discovered
#: rather than listed. `review_pr_workflow.py` is excluded because it IS the
#: reviewer — it does not dispatch itself.
def _review_dispatchers() -> list[Path]:
    root = Path(__file__).resolve().parents[2] / "modules" / "assistant"
    out = []
    for p in sorted(root.rglob("*_workflow.py")):
        if p.name == "review_pr_workflow.py":
            continue
        if "run_review" in p.read_text():
            out.append(p)
    return out


REVIEW_DISPATCHERS = _review_dispatchers()


def test_the_review_dispatcher_census_reaches_ALL_THREE_FAMILIES() -> None:
    """Vacuity floor, and it names the two families the old population MISSED.

    The predecessor of the guard below globbed
    `modules/assistant/build/*/[a-z]*_workflow.py` — TWO files — while its own
    docstring promised it would catch "a `plan`/`research` parent that grows a
    gate". That promise was false for as long as it stood, and it is exactly the
    window in which four parents dispatched `review-pr` on an unread verdict.
    A count alone would not have caught it (two IS a non-zero count), so this
    floor asserts the FAMILIES, which is the thing that was missing.
    """
    assert len(REVIEW_DISPATCHERS) >= 5, (   # 6 -> 5: `research_refresh_parent` merged away 2026-08-28
        f"only {len(REVIEW_DISPATCHERS)} review dispatchers discovered; the walk "
        f"has stopped matching and the guard below is vacuous: "
        f"{[p.name for p in REVIEW_DISPATCHERS]}"
    )
    families = {p.relative_to(p.parents[2]).parts[0] for p in REVIEW_DISPATCHERS}
    assert {"build", "plan", "research"} <= families, (
        f"the population no longer reaches all three families (saw {sorted(families)}). "
        f"A glob that stops matching `plan/` or `research/` returns this guard to "
        f"the build-only scope that let four ungated parents ship."
    )


@pytest.mark.parametrize("path", REVIEW_DISPATCHERS, ids=lambda p: p.name)
def test_no_parent_dispatches_review_on_an_UNREAD_CI_VERDICT(path: Path) -> None:
    """A parent that dispatches `review-pr` without reading CI can MERGE on red.

    THE CLASS, NOT THE INSTANCE, AND THIS IS THE SECOND TIME THAT PHRASE HAD TO
    BE EARNED. `routing.ci_gate` landed in `build_workflow` on 2026-08-09 and
    `build_minor_workflow` was never updated, so the light tier reached
    `review-pr` with the verdict unread. The guard written for THAT defect was
    headed "the class" and scoped to `build/*/` — so when the identical hole was
    found in one `plan` parent and three `research` parents, the guard was green
    over all four. A population narrower than the claim is a guard that certifies
    the gap it was written to close.

    Keyed on the CALL, over every `*_workflow.py` under `modules/assistant` that
    dispatches a review — so a seventh parent fails here on the day it is written
    instead of on the day someone re-runs the sweep.

    WHAT THIS DOES NOT LOOK AT — three things, stated because a guard that scans
    a tree is exactly the shape that passes vacuously:
      * ORDER. It asserts both calls are present in the module, not that the gate
        runs BEFORE the dispatch. An AST call-set cannot see control flow, and
        the ordering is pinned by the activity-driving tests above instead.
      * `repo_root=`. Since 2026-08-20 the parameter is REQUIRED on both CI
        reads, so a parent that omits it fails at the call rather than degrading
        to "this repo declares no gate" — but that failure surfaces only when the
        parent RUNS, and five of the six parents have no end-to-end test. See
        `test_every_gated_parent_passes_repo_root_to_BOTH_CI_READS` below, which
        is the arm that reads the argument statically.
      * A dispatcher that reaches `run_review` through an alias or a variable.
        The predicate matches the attribute/name of the call, so
        `f = review_pr.run_review; f(...)` is invisible to it.
    """
    assert not _dispatches_review_ungated(path.read_text()), (
        f"{path.name} dispatches review-pr without reading the CI verdict through "
        f"routing.ci_gate, so MERGE is reachable on a red tree. Add "
        f"`wait_for_ci` / `ci_verdict` / `routing.ci_gate` immediately before the "
        f"`run_review` call and return the hold when one comes back — the shape "
        f"all six parents now use."
    )


@pytest.mark.parametrize("path", REVIEW_DISPATCHERS, ids=lambda p: p.name)
def test_every_gated_parent_passes_repo_root_to_BOTH_CI_READS(path: Path) -> None:
    """`repo_root` is what lets a CI read find the repo's own gate declaration.

    WITHOUT IT THE GATE FORGAVE EVERYTHING, SILENTLY, and the tense is the
    point. `read_check_policy` used to be reached only when `repo_root is not
    None`; with it absent, `ci_verdict` returned NO_CHECKS on every repo that
    declares a gate and `wait_for_ci` stopped waiting for a gate it did not know
    to expect. The cascade then reported "SKIPPED — no check declared blocking",
    which is not a HOLD, on a tree that may be red.

    THAT PATH IS NOW CLOSED AT THE SIGNATURE — `repo_root` is a required
    parameter on both reads as of 2026-08-20 — AND THIS GUARD IS NOT THEREFORE
    REDUNDANT. A missing keyword is a TypeError only when the parent EXECUTES,
    and `plan_project` is the one parent in the tree driven end-to-end by a test;
    the other five would ship the failure and discover it in production. This arm
    reads the argument out of the source, so it fails at test time for all six.

    `build_minor` was reading the policy without it until PR #124, which is why
    this is a guard and not a comment.
    """
    source = path.read_text()
    for name in ("wait_for_ci", "ci_verdict"):
        for call in [n for n in ast.walk(ast.parse(source))
                     if isinstance(n, ast.Call)
                     and (n.func.attr if isinstance(n.func, ast.Attribute)
                          else getattr(n.func, "id", "")) == name]:
            assert any(kw.arg == "repo_root" for kw in call.keywords), (
                f"{path.name} calls {name}() without repo_root=, which is now a "
                f"REQUIRED parameter — this parent will raise TypeError the next "
                f"time it runs, and it is caught here rather than in production "
                f"because five of the six parents have no end-to-end test. Pass "
                f"the tree the PR lives in, so the read can find {POLICY_PATH}."
            )


def _discards_the_gate_hold(source: str) -> bool:
    """Does this module compute a `ci_gate` hold and then NOT return it?

    THE GATE'S EFFECT, NOT ITS PRESENCE, AND THE DIFFERENCE WAS MEASURED. The
    call-set predicate above is satisfied the moment `ci_gate` appears anywhere
    in a module. Deleting `if hold is not None: return hold` from
    `research_workflow` — which leaves the parent computing a verdict, appending
    the operator note that says review-pr was NOT dispatched, and then
    dispatching it anyway — produced ZERO failures across the whole unit suite.
    A parent can merge on red with the gate fully wired and every existing arm
    green.

    Only `plan_project` had behavioural cover for this
    (`test_plan_project_loop.test_a_RED_tree_HOLDS_before_review_pr_is_ever_
    dispatched`), and it is the only parent in the tree driven end-to-end by a
    test. Writing five more loop-test modules is the wrong shape for a property
    five parents state in four identical lines; the shape is a structural check
    on those lines.

    SPLIT OUT SO A LITERAL CONTROL CAN DRIVE IT, for the reason
    `_dispatches_review_ungated` above records: a walk over the tree stays green
    over a predicate that has silently begun answering `False` for everything.

    A module with NO `ci_gate` call answers `False` — there is no hold to
    discard. That case is not forgiven, it is somebody else's: the ungated-parent
    arm above fails it.
    """
    tree = ast.parse(source)
    for fn in [n for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        for stmt in ast.walk(fn):
            if not isinstance(stmt, ast.Assign):
                continue
            call = stmt.value
            if not isinstance(call, ast.Call):
                continue
            if (call.func.attr if isinstance(call.func, ast.Attribute)
                    else getattr(call.func, "id", "")) != "ci_gate":
                continue
            target = stmt.targets[0]
            if not (isinstance(target, ast.Tuple) and target.elts
                    and isinstance(target.elts[0], ast.Name)):
                return True          # the hold is not even bound to a name
            hold = target.elts[0].id
            returned = any(
                isinstance(node, ast.If)
                and isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Name)
                and node.test.left.id == hold
                and any(isinstance(op, ast.IsNot) for op in node.test.ops)
                and any(isinstance(b, ast.Return) and isinstance(b.value, ast.Name)
                        and b.value.id == hold for b in node.body)
                for node in ast.walk(fn)
            )
            if not returned:
                return True
    return False


def test_the_DISCARDED_HOLD_predicate_discriminates_on_a_literal() -> None:
    """Positive control for the walk below, on source the tree does not contain.

    Four arms, because three of the four ways this predicate can rot are silent:
    answering `True` for everything, answering `False` for everything, matching
    a `return` of some OTHER name, and accepting a bare `if hold:` whose body
    returns nothing.
    """
    gated = ("def f(x):\n"
             "    hold, notes = routing.ci_gate(x)\n"
             "    if hold is not None:\n"
             "        return hold\n"
             "    return review_pr.run_review(x)\n")
    assert not _discards_the_gate_hold(gated), (
        "the predicate reports a parent that DOES return its hold, so it would "
        "fail on correct code")
    assert _discards_the_gate_hold(
        "def f(x):\n"
        "    hold, notes = routing.ci_gate(x)\n"
        "    return review_pr.run_review(x)\n"
    ), "the predicate no longer reports a gate whose hold is computed and dropped"
    assert _discards_the_gate_hold(
        "def f(x):\n"
        "    hold, notes = routing.ci_gate(x)\n"
        "    if hold is not None:\n"
        "        return other\n"
        "    return review_pr.run_review(x)\n"
    ), "the predicate accepts a branch that returns something OTHER than the hold"
    assert not _discards_the_gate_hold(
        "def f(x):\n    return review_pr.run_review(x)\n"
    ), "the predicate fires on a module that computes no gate at all — that is the "\
       "ungated-parent arm's finding, not this one"


@pytest.mark.parametrize("path", REVIEW_DISPATCHERS, ids=lambda p: p.name)
def test_every_gated_parent_RETURNS_the_hold_it_computes(path: Path) -> None:
    """A gate whose hold is dropped is a gate that changed nothing.

    WHY THIS ARM EXISTS AND WHAT IT COST TO FIND. The two arms above assert that
    the gate is CALLED and CALLED CORRECTLY. Neither asserts it has any effect,
    and the docstring above says so about ordering — but the effect gap is wider
    than ordering: deleting the four-line hold-return from `research_workflow`
    failed NOTHING in the unit suite. Five of the six parents have no
    behavioural test at all; `plan_project` is the only one driven end-to-end.

    WHAT THIS DOES NOT LOOK AT — and the first bullet is why the behavioural
    test still earns its place:
      * ORDER, still. A parent that returns its hold AFTER dispatching review
        satisfies this. `test_plan_project_loop.test_a_RED_tree_HOLDS_before_
        review_pr_is_ever_dispatched` is the arm that sees that, for the one
        parent a test drives.
      * A hold propagated by any shape other than `if <hold> is not None:
        return <hold>` — an early `return hold or ...`, a raise, a caller that
        inspects the tuple. All are legitimate and all fail here. That is
        deliberate: six parents write the identical four lines today, and a
        guard that admits every equivalent shape admits the broken ones too.
      * WHAT THE CALLER DOES WITH THE RETURNED HOLD. This ends at the function
        boundary.
    """
    assert not _discards_the_gate_hold(path.read_text()), (
        f"{path.name} computes a CI hold and does not return it, so the gate runs, "
        f"writes its operator note saying review-pr was NOT dispatched, and then "
        f"dispatches review-pr anyway — MERGE stays reachable on a red tree with "
        f"every other arm of this module green. Add `if hold is not None: return "
        f"hold` immediately after `notes.extend(gate_notes)`."
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


def test_an_unreadable_gh_reply_is_not_mistaken_for_settled_CI(monkeypatch, tmp_path):
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
    assert act.wait_for_ci("1", repo_root=tmp_path) is False, (
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


# ---------------------------------------------------------------------------
# THE PROPERTY. A NON-HOLDING GATE RESULT IS UNREACHABLE WITHOUT A POLICY READ.
#
# Every test above drives ONE function and asserts ONE verdict. The defect that
# produced this block was invisible to all ~50 of them because it lived in the
# JOIN: `ci_verdict` returned a state that is correct in isolation (`NO_CHECKS`
# genuinely means "no blocking check reported"), `ci_gate` routed that state
# correctly (a repo with no gate proceeds), and the composition let a red tree
# through — because nobody had established that reaching the non-holding state
# requires having LOOKED for a policy at all.
#
# Measured 2026-08-20 on PR #124: `ci_verdict("1", repo_root=None)` over
# `[{"name": "suite", "state": "FAILURE"}]` returned `NO_CHECKS`, and
# `ci_gate` returned `hold=None`, which every parent reads as PROCEED.
#
# So these two guard the PROPERTY, not the two functions. `repo_root` being
# required is the CURRENT mechanism; the property is what must survive the next
# person deciding a different mechanism is nicer.
# ---------------------------------------------------------------------------


def _counting_policy_reader(monkeypatch):
    """Count `read_check_policy` calls WITHOUT changing what it returns.

    The count is the whole instrument: "a policy was read" is not observable
    from the verdict, because `NO_CHECKS` is what you get both from a tree that
    declares nothing AND from a tree nobody looked at. Those are the two facts
    this fleet has now collapsed three separate times, and the enum cannot tell
    them apart by construction — see `CiVerdict`'s own docstring on
    `UNREADABLE_POLICY`.
    """
    real = act.read_check_policy
    calls = {"n": 0}

    def counted(repo_root):
        calls["n"] += 1
        return real(repo_root)

    monkeypatch.setattr(act, "read_check_policy", counted)
    return calls


def _tree_cases(tmp_path):
    """Every tree shape a caller can hand the gate, INCLUDING the one that shipped.

    `None` IS IN THIS LIST ON PURPOSE AND IS THE REASON THE LIST EXISTS. It is
    the input that used to skip the policy read, and a case list that quietly
    omits it is a guard that cannot see the hole come back — which is exactly
    how the defect reached a sixth review pass.

    SELF-CONTAINED, sharing no fixture with the `repo` fixture the rest of this
    module uses. A control that shares a fixture with the code under mutation
    over-fires and stops discriminating.
    """
    declares = tmp_path / "declares"
    (declares / POLICY_PATH).parent.mkdir(parents=True)
    (declares / POLICY_PATH).write_text("blocking:\n  - suite\n")

    broken = tmp_path / "broken"
    (broken / POLICY_PATH).parent.mkdir(parents=True)
    (broken / POLICY_PATH).write_text("blocking: [unclosed\n  - broken: : :\n")

    silent = tmp_path / "silent"
    silent.mkdir()

    return [
        ("no tree at all", None),
        ("declares a gate", declares),
        ("declaration is broken", broken),
        ("declares nothing", silent),
    ]


def test_a_NON_HOLDING_gate_is_unreachable_without_a_policy_READ(monkeypatch, tmp_path):
    """Over a RED check list, every tree shape either REFUSES or reads a policy.

    THE ASSERTION IS THE IMPLICATION, not a list of expected verdicts: if the
    gate let the run PROCEED, then `read_check_policy` ran. That is what makes
    this survive a future change to how the requirement is enforced — swap the
    required parameter for a stopping verdict and this still passes, because a
    stopping verdict is a hold and the implication never ranges over it; delete
    the requirement altogether and it goes red on the `None` case.

    THAT SENTENCE IS DRIVEN AND NOT ASSERTED, because the sentence it replaces
    was neither. The version this file shipped on 2026-08-20 scoped the read
    assertion to EVERY return rather than to the non-holding ones, so
    implementing the stopping verdict — the alternative the brief named and
    this fix declined — turned it RED, while its own docstring promised it
    would not. Both halves are now measured: `repo_root: Path | None = None`
    plus `if repo_root is None: return UNREADABLE_POLICY` leaves this GREEN
    (that state is a HOLD, `routing.ci_gate`), and re-adding the skip branch
    turns it RED. A guard whose prose outran its assertions is the class this
    whole PR exists to close, so it does not get to survive inside the fix.

    The check list is RED throughout, so any outcome that is not a hold is a
    demonstrated fail-open rather than a theoretical one.

    WHAT THIS DOES NOT LOOK AT, stated because a guard that loops over cases is
    the shape that passes vacuously:
      * WHICH hold. `HOLD_REDISPATCH` versus `HOLD_NEEDS_ASSISTANCE` is routed by
        `ci_gate` and pinned by the cascade tests above. This asks only that a
        hold came back.
      * `wait_for_ci`. It returns a settled bool, not a verdict, so it has no
        holding/non-holding outcome for this implication to range over. Its half
        of the requirement is pinned by the signature guard below — which now
        drives an explicit `repo_root=None` against BOTH reads. It did not until
        this correction, and the two guards each named the other as the one that
        looked, so `wait_for_ci(pr, repo_root=None)` had no cover at all.
      * THE POLICY'S CONTENT. `read_check_policy` is counted, not inspected —
        `DO NOT TOUCH read_check_policy` is a standing constraint on this gate
        and its parsing is covered by the declaration tests above.
      * A TREE THAT IS WRONG RATHER THAN ABSENT. `repo_root=/some/other/repo`
        reads a policy and passes here. Which tree is correct is
        `test_every_gh_the_fleet_launches_is_ANCHORED`'s question, and that guard
        says in its own words that it does not answer it either.
    """
    _gh(monkeypatch, [{"name": "suite", "state": "FAILURE"}])
    reads = _counting_policy_reader(monkeypatch)

    examined = refused = holds = 0
    proceeded: list[str] = []
    for label, tree in _tree_cases(tmp_path):
        examined += 1
        before = reads["n"]
        try:
            verdict, extra = act.ci_verdict("1", repo_root=tree)
        except TypeError:
            # REFUSED, AND THIS ARM DELIBERATELY DOES NOT CARE WHERE FROM —
            # that is the mechanism's business, and pinning it here is what
            # made the previous version go red on a correct alternative. A
            # verdict that never existed cannot be a non-holding one, so the
            # implication holds for this case however the refusal arrived.
            #
            # The two refusals are NOT the same, and the sentence that used to
            # sit here ("the call shape itself is refused") was false for the
            # one this list actually produces. An OMITTED `repo_root` is
            # rejected at the call boundary; an explicit `None` — which is what
            # `_tree_cases` hands over — is accepted by the signature, reaches
            # `read_check_policy`, and dies on `None / POLICY_PATH`.
            # `test_neither_CI_READ_can_be_called_without_a_tree` drives both
            # shapes against both reads.
            refused += 1
            continue

        hold, _notes = routing.ci_gate(verdict, extra, pr="1", repo_target=None)
        if hold is None:
            proceeded.append(label)
            # THE PROPERTY, AND THE ONLY PLACE IT IS ASSERTED. Scoped to the
            # non-holding outcome on purpose: a gate that STOPS has broken
            # nothing, whether or not it read a policy first, and asserting
            # over every return instead pinned the mechanism rather than the
            # property.
            assert reads["n"] > before, (
                f"[{label}] ci_verdict returned {verdict} over a RED check list "
                f"without ever calling read_check_policy, and `ci_gate` let the "
                f"run PROCEED on it. The verdict describes a policy nobody "
                f"looked for — which is how a red tree reached review-pr on "
                f"2026-08-20."
            )
        else:
            holds += 1

    # --- Vacuity floors. Each names the specific way this could stop meaning
    #     anything while still printing green.
    assert examined == 4, (
        f"the case list examined {examined} trees, not 4 — a case was dropped, "
        f"and the one that matters is `None`"
    )
    assert refused <= 1, (
        f"{refused} of the 4 cases raised instead of returning a verdict. At most "
        f"one can legitimately: handing the gate no tree at all. More than that "
        f"and this is measuring a crash in the fixture rather than the property — "
        f"every extra refusal is a case that skipped the assertion. It is `<=` and "
        f"not `== 1` because a stopping verdict for the no-tree case would make it "
        f"0 and would be a correct implementation; what may not happen is a tree "
        f"PROCEEDING, which the floor below pins by name."
    )
    assert holds >= 2, (
        f"only {holds} tree(s) produced a hold over a RED check list — the "
        f"implication 'proceeded => a policy was read' is trivially satisfiable "
        f"by a fixture that never reaches the gate at all"
    )
    assert proceeded == ["declares nothing"], (
        f"the trees that let the run PROCEED over a RED check list were "
        f"{proceeded}, and exactly one may: the repo that genuinely declares no "
        f"gate — a ruled decision (routing.CiVerdict, 2026-08-13), not an "
        f"oversight. An EMPTY list means nothing reached the assertion above and "
        f"the implication is trivially satisfied by everything holding. ANY OTHER "
        f"tree in it is the 2026-08-20 defect back: a gate that proceeds on a red "
        f"list without having looked for a policy."
    )
    assert reads["n"] >= 3, (
        f"read_check_policy ran {reads['n']} time(s) across {examined} cases — "
        f"the counter is not wired to the function the gate actually calls, so "
        f"the assertion above can never fire"
    )


def test_neither_CI_READ_can_be_called_without_a_tree():
    """The default cannot be quietly restored — on EITHER read.

    THE MECHANISM ARM. The test above pins the property; this pins the thing
    currently delivering it, because the property test's `None` case only fails
    loudly while `repo_root` has no default. Restoring `= None` on `ci_verdict`
    reopens the exact 2026-08-20 hole, and a reviewer scanning a signature line
    is unlikely to reconstruct why the default is absent.

    BOTH READS, because the requirement is symmetric by decision rather than by
    accident: `wait_for_ci` returns a settled bool rather than the gate verdict,
    so it is the lower-stakes half — and an unanchored poll still reads no
    policy, stops waiting for a gate it does not know to expect, and can burn the
    full 600-second deadline against a tree nobody chose.

    IT ALSO DRIVES THE EXPLICIT `None`, ON BOTH READS, and that arm is here
    because the version of this file shipped on 2026-08-20 did not have it and
    said it did. This docstring claimed the explicit `None` was "covered from
    the other side — the property test hands exactly that value to the real
    function", and the property test's own docstring pointed back here for
    `wait_for_ci`. Both were half true: the property test drives ONLY
    `ci_verdict`, so `wait_for_ci(pr, repo_root=None)` was named by two guards
    and looked at by neither. A mutual "covered elsewhere" that nobody drove is
    the defect class this whole PR exists to close.

    THE TWO SHAPES ARE DIFFERENT REFUSALS and both are asserted, because only
    one of them is the signature's doing. Omitting `repo_root` is rejected at
    the call boundary. An explicit `None` satisfies the signature — annotations
    do not check — reaches `read_check_policy`, and dies on
    `None / POLICY_PATH`. The second is what a caller with an
    `Optional[Path]` in hand actually produces, and it is the shape a
    `wait_for_ci`-only shortcut (`if repo_root is None: return True`) would
    silently reopen.
    """
    for name in ("ci_verdict", "wait_for_ci"):
        param = inspect.signature(getattr(act, name)).parameters["repo_root"]
        assert param.default is inspect.Parameter.empty, (
            f"`{name}` has grown a default for `repo_root` again ({param.default!r}). "
            f"With one, the CI reads skip {POLICY_PATH} entirely: `blocking` stays "
            f"empty, a FAILING check returns NO_CHECKS, and `ci_gate` answers that "
            f"with hold=None — a red tree dispatched to review-pr. Measured on "
            f"PR #124, 2026-08-20."
        )
        assert param.kind is inspect.Parameter.KEYWORD_ONLY, (
            f"`{name}` now takes `repo_root` positionally ({param.kind}); the six "
            f"parents all pass it by keyword and the static arm in "
            f"test_every_gated_parent_passes_repo_root_to_BOTH_CI_READS only "
            f"inspects keywords"
        )

    for name in ("ci_verdict", "wait_for_ci"):
        read = getattr(act, name)
        with pytest.raises(TypeError):
            read("1")                      # omitted: refused at the call
        with pytest.raises(TypeError):
            read("1", repo_root=None)      # explicit: refused inside the read

    # NEITHER CALL ABOVE REACHES `gh`, AND NOTHING IS MONKEYPATCHED HERE ON
    # PURPOSE. `read_check_policy(repo_root)` is the first statement of both
    # reads, so both die before any subprocess and before `wait_for_ci`'s
    # 600-second deadline starts. A fake would only be able to hide a
    # regression that moved the policy read after the first `gh` call.

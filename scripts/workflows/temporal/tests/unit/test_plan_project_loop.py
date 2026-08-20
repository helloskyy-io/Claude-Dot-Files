"""plan-project routes on the verdict, and loops up to `routing.MAX_LOOPS` times.

WHY THIS EXISTS. `plan-sprint` ran twice with no parent, so its output reached
the operator UNJUDGED — on the only autonomous write to `sprint.md`. This parent
is the judge, and the property that matters is not that it calls `review-pr`; it
is that it calls it the RIGHT NUMBER OF TIMES for each verdict.

AND SINCE THE SPLIT, IN THE RIGHT ORDER. `triage-candidates` rules the
candidates and `plan-sprint` places what they ruled, and the ORDER between them
is the whole reason the split happened: sprint maintenance running first meant
hour totals landed ahead of the estimates they depend on, and nothing could be
sequenced between the two jobs while they shared one dispatch. Order is not
something a reader can check by looking — both calls are present either way — so
it is pinned here.

All three children are stubbed. The parent calls no model by design, so a test
that exercised the real children would be testing them, not the routing — and the
routing is the whole content of a parent.

The loop bound is a MEASURED constant, not a preference: self-correction
plateaus at 3-5 passes, and one PR on this fleet reached eight review passes
with pass 8 reviewing the same tree as pass 7. A regression that raised
MAX_LOOPS would be invisible without these.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.assistant import routing
from modules.assistant.plan.plan_project import plan_project_workflow as pm
from modules.assistant.review_pr.review_pr_helper import ReviewResult

PR_URL = "https://github.com/o/r/pull/43"
BASE_SHA = "0123456789abcdef0123456789abcdef01234567"


class _Calls:
    """Counts what the parent actually dispatched, per child.

    `order` is the sequence of child names as the parent actually called them.
    The per-child counters answer "how many times"; only this answers "in what
    order", and after the split the order IS the property.
    """

    def __init__(self) -> None:
        self.triage = 0
        self.sprint = 0
        self.review = 0
        self.order: list[str] = []
        self.correction_passes: list[bool] = []
        self.research_pools: list[Path] = []
        self.sprint_pools: list[Path] = []
        # Every `component` the plan-feature child was handed. REPO-ROOTED by the
        # child's contract, which is the half of this seam worth asserting: the
        # parent holds a WORKTREE path and every other child takes one, so the
        # re-anchoring is a place a correct-looking call is silently wrong.
        self.planned: list[Path] = []
        # Every `component` the plan-verify child was handed, same contract and
        # asserted for the same reason. The two are recorded SEPARATELY rather
        # than as one counter: they run back to back on one component, so a bug
        # that dispatched the judge against a DIFFERENT path than the author is
        # invisible to a combined count and is exactly what re-anchoring gets
        # wrong.
        self.verified: list[Path] = []
        # (tree, argv, children dispatched SO FAR) for every git read the parent
        # makes. The third element is what turns "it pinned a base" into "it
        # pinned it before anything could move".
        self.git_calls: list[tuple[Path, tuple[str, ...], tuple[str, ...]]] = []
        # Every `base_ref` Step 2's sweep was actually given.
        self.sweep_bases: list[object] = []
        # Every positional argument pair Step 1b's scaffolder was called with.
        self.scaffold_args: list[tuple[object, ...]] = []
        # (function, pr, repo_root, reviews-so-far) for every CI read `_dispose`
        # made. `repo_root` is recorded rather than merely counted because
        # without it the reads cannot find `testing/check-policy.yaml` and the
        # gate silently forgives everything — a gate that is present and inert.
        # The review count is the ordering evidence; see `fake_wait_for_ci`.
        self.ci_reads: list[tuple[str, str, object, int]] = []


@pytest.fixture
def wired(monkeypatch: pytest.MonkeyPatch) -> _Calls:
    """Stub every child and isolation; the parent's own logic is untouched."""
    calls = _Calls()

    def fake_triage(**kw: object) -> str:
        calls.triage += 1
        calls.order.append("triage")
        return PR_URL

    def fake_sprint(**kw: object) -> str:
        calls.sprint += 1
        calls.order.append("sprint")
        calls.correction_passes.append(bool(kw.get("correction_pass", False)))
        # `component`, not `research_dir`. The child was rebuilt on 2026-08-19 to
        # act on ONE PLANNED COMPONENT — it no longer reads a research pool or a
        # candidates file, and `sprint_pools` recorded a parameter that no longer
        # exists. What the assertions want now is WHICH COMPONENT each dispatch
        # was handed, which is also what makes the one-per-component fan-out
        # visible rather than a bare count.
        calls.sprint_pools.append(kw["component"])
        return PR_URL

    def fake_write(**kw: object) -> str:
        calls.research_pools.append(kw["research_dir"])
        calls.order.append("research")
        return PR_URL

    def fake_feature(**kw: object) -> str:
        calls.planned.append(kw["component"])
        calls.order.append("feature")
        return PR_URL

    def fake_plan_verify(**kw: object) -> str:
        calls.verified.append(kw["component"])
        calls.order.append("plan-verify")
        return PR_URL

    monkeypatch.setattr(pm.feature, "run_plan_feature", fake_feature)
    monkeypatch.setattr(pm.plan_verify, "run_plan_verify", fake_plan_verify)
    monkeypatch.setattr(pm.triage, "run_triage_candidates", fake_triage)
    monkeypatch.setattr(pm.sprint, "run_plan_sprint", fake_sprint)
    monkeypatch.setattr(pm.act, "worktree_add", lambda *a, **k: Path("/tmp/wt"))
    # THE BASE THIS RUN IS CUT FROM, stubbed for the same reason `repo_slug`
    # below is: it asks `gh`, and this loop is driven against a fake repo path.
    # It answers "HEAD" only here — production resolves the DEFAULT BRANCH, and
    # `test_a_new_branch_STARTS_FROM_THE_DEFAULT_BRANCH` is what holds that.
    monkeypatch.setattr(pm.act, "base_ref", lambda pr, repo_root: "HEAD")
    # The parent pins the commit its worktree started from, so Step 2 asks "what
    # did THIS run add" rather than "what has this branch accumulated". Faked at
    # its boundary — the worktree above is a path, not a repository — and
    # recorded, because a base taken at the WRONG moment is the whole defect and
    # is invisible unless the call is observed.
    def fake_git_output(tree: Path, cmd: list[str], _why: str) -> str:
        calls.git_calls.append((tree, tuple(cmd), tuple(calls.order)))
        return f"{BASE_SHA}\n"

    monkeypatch.setattr(pm.act, "git_output", fake_git_output)
    # THE CI GATE IS FAKED AT ITS BOUNDARY, GREEN, and it must be faked at ALL:
    # `_dispose` now reads the CI verdict before dispatching review, and both
    # reads shell out to `gh`. Left real they cost ~5s per test against the live
    # API and make the outcome depend on a network — the gate's own cascade is
    # exercised by `test_ci_gate.py`, which drives the activity directly.
    # `calls.ci_reads` records the pair so the ordering tests can see that the
    # gate ran BEFORE the review dispatch, which is the property this parent was
    # missing entirely until PR #124.
    def fake_wait_for_ci(pr: str, **kw: object) -> bool:
        # THE FOURTH ELEMENT IS THE REVIEW COUNT AT THE MOMENT OF THE READ, and
        # it is what makes "the gate ran first" checkable. A snapshot of `order`
        # was the obvious choice and is VACUOUS here — `order` records child
        # dispatches and `run_review` is not one of them, so `"review" not in
        # order` is true whatever the parent does. `calls.review` is incremented
        # by the review fake itself, so it cannot be true by construction.
        # `order` is deliberately left unperturbed: the ordering tests assert it
        # exactly, and the gate is not a child.
        calls.ci_reads.append(("wait_for_ci", pr, kw.get("repo_root"), calls.review))
        return True

    def fake_ci_verdict(pr: str, **kw: object) -> tuple[routing.CiVerdict, list[str]]:
        calls.ci_reads.append(("ci_verdict", pr, kw.get("repo_root"), calls.review))
        return routing.CiVerdict.GREEN, []

    monkeypatch.setattr(pm, "wait_for_ci", fake_wait_for_ci)
    monkeypatch.setattr(pm, "ci_verdict", fake_ci_verdict)
    # The parent reads its own repo slug BEFORE the triage child, so the number
    # it takes out of the child's URL can be checked against the repository the
    # dispatch is operating in. It is a `gh` call; faked at its boundary.
    monkeypatch.setattr(pm._shared, "repo_slug", lambda repo_root: "o/r")
    monkeypatch.setattr(pm.write, "run_write", fake_write)
    monkeypatch.setattr(pm.verify, "run_verify", lambda **kw: PR_URL)
    # No new sections by default: the research fan-out is opt-in per test, and a
    # real `git diff` against a fake worktree would fail for the wrong reason.
    def no_sections(*a: object, **k: object) -> list[str]:
        calls.sweep_bases.append(k.get("base_ref"))
        return []

    monkeypatch.setattr(pm.own, "new_sprint_sections", no_sections)
    # `component_dir` IS NOT STUBBED. It was, to a constant `.../development/x`,
    # which meant every fan-out test asserted against a path the code under test
    # had not computed — and it hid the slug-versus-heading mismatch that made the
    # two research signals fail to de-duplicate. It is pure path arithmetic and
    # there is nothing in it to isolate.
    #
    # Step 1b scaffolds nothing by default, for the same reason the sweep above
    # returns nothing: it reads and WRITES a real tree, and the worktree here is
    # a bare path. Faked at its boundary and recorded — which component list the
    # parent hands the research step is exactly what the fan-out tests assert on.
    def no_scaffold(*a: object, **k: object) -> pm.own.Scaffolded:
        calls.scaffold_args.append(a)
        return pm.own.Scaffolded(created=[], resumed=[], extends=[], unnamed=[],
                                 not_a_feature=[], unsized=[])

    monkeypatch.setattr(pm.own, "scaffold_candidate_components", no_scaffold)
    return calls


def _plans_one(monkeypatch: pytest.MonkeyPatch, calls: _Calls, name: str = "alpha") -> None:
    """Make the sweep find ONE component, so the per-component children fire.

    NEEDED SINCE 2026-08-19 AND NOT BEFORE. `plan-sprint` used to walk
    `candidates.md` and ran once whether or not anything had been planned, so a
    fixture with an empty sweep still exercised it. It now acts on ONE PLANNED
    COMPONENT — a parent that plans nothing sprints nothing — which is correct
    behaviour and makes an empty sweep the wrong fixture for any assertion about
    the sprint child.

    The fan-out tests keep the empty default deliberately: what they assert is
    which components the research step is handed, and seeding one here would put
    a component in every one of those lists.
    """
    def one(*a: object, **k: object) -> list[str]:
        calls.sweep_bases.append(k.get("base_ref"))
        return [name]

    monkeypatch.setattr(pm.own, "new_sprint_sections", one)


def _verdicts(monkeypatch: pytest.MonkeyPatch, calls: _Calls, *sequence: routing.Verdict) -> None:
    """Make review-pr return each verdict in turn, then repeat the last."""
    def fake_review(review_input: object, repo_root: Path) -> ReviewResult:
        v = sequence[min(calls.review, len(sequence) - 1)]
        calls.review += 1
        return ReviewResult(pr_number="43", verdict=v, this_pass=calls.review, notes=[])

    monkeypatch.setattr(pm.review_pr, "run_review", fake_review)


def _run(**kw: object) -> tuple[str, routing.Verdict, int, list[str]]:
    return pm.run_plan_project(
        repo_root=Path("/repo"), worktree_name="wt",
        sprint_path=Path("/repo/docs/development/sprint.md"),
        candidates_path=Path("/repo/c.md"), research_dir=Path("/repo/r"), **kw,
    )


def test_merge_runs_one_of_each_child(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """The happy path spends exactly three child dispatches, never four."""
    _plans_one(monkeypatch, wired)
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    url, verdict, loops, _notes = _run()
    assert (url, verdict, loops) == (PR_URL, routing.Verdict.MERGE, 0)
    assert (wired.triage, wired.sprint, wired.review) == (1, 1, 1)


def test_triage_runs_BEFORE_the_sprint_plan_is_touched(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """THE ORDERING IS THE SPLIT, and nothing else here would catch it reversed.

    Both children are called either way, and both counters read 1 either way —
    so a parent that placed before it ruled would pass every other assertion in
    this file. The defect that ordering fixes is concrete: `plan-sprint` used to
    run first, which put its hour totals in the plan ahead of anything that
    estimates the work those totals are of, and left no position in which
    feature planning could run at all.
    """
    _plans_one(monkeypatch, wired)
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    _run()
    assert wired.order == ["triage", "research", "feature", "plan-verify", "sprint"], (
        f"the parent dispatched its children as {wired.order}. Triage rules the "
        f"candidates and plan-sprint places what they ruled — reversed, the "
        f"sprint plan is written from rulings that have not been made yet."
    )


def test_research_sits_BETWEEN_triage_and_the_sprint_plan(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """The gap is the whole point of the split, so its position is pinned.

    `plan-candidates` and `plan-feature` were the work the gap was made for, and
    both have now landed in it — `plan-candidates` as an activity ahead of the
    research step, `plan-feature` as a child behind it. If the research fan-out
    drifted to either end, the position they occupy would quietly stop existing.

    **`plan-feature` sits between research and the sprint plan, and BOTH sides of
    that are load-bearing.** Ahead of research it would plan a component from a
    pool that is still a one-line seed. Behind `plan-sprint` it would restore the
    ordering defect the split existed to fix: the sprint plan updated before
    anything had decomposed the work it sequences.

    **`plan-verify` SITS BETWEEN THEM, AND ITS POSITION IS PINNED FROM BOTH SIDES
    TOO.** Ahead of `plan-feature` there is no plan to read and it refuses. Behind
    `plan-sprint` it would leave the sprint maintainer running before the only
    thing that estimates the work — the very defect `plan_sprint_workflow`'s
    docstring records, which had been latent rather than fixed because until this
    child landed there were no estimates for the sprint plan to be ahead of.
    """
    _plans_one(monkeypatch, wired)
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    _with_sections(monkeypatch, "Alpha")
    _run()
    assert wired.order == ["triage", "research", "feature", "plan-verify",
                           "sprint"], (
        f"the parent dispatched {wired.order} — component research must run "
        f"after the rulings exist, the component must be planned from the "
        f"research that just landed, the plan must be sized before anything "
        f"totals it, and the sprint plan must be maintained last"
    )
    assert wired.verified == wired.planned, (
        f"the judge was dispatched against {wired.verified} while the author "
        f"wrote {wired.planned}. They run back to back on ONE component and the "
        f"path is re-anchored from the worktree to the repo for both; a judge "
        f"pointed at a different component reads a plan nobody just wrote"
    )


def test_redispatch_loops_to_the_bound_then_stops(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """A permanently-redispatching reviewer must NOT loop forever.

    This is the regression that matters: the verdict never becomes MERGE, so
    only the loop bound stops it.
    """
    _plans_one(monkeypatch, wired)
    _verdicts(monkeypatch, wired, routing.Verdict.HOLD_REDISPATCH)
    _url, verdict, loops, notes = _run()
    assert loops == routing.MAX_LOOPS, (
        f"looped {loops} times against a bound of {routing.MAX_LOOPS}. Asserting a "
        f"LITERAL here made the operator's 1->3 ramp look like a regression."
    )
    assert verdict is routing.Verdict.HOLD_REDISPATCH
    # One initial pass plus one per loop-back. Derived, so the operator's ramp
    # does not read as a regression.
    expected = 1 + routing.MAX_LOOPS
    assert (wired.sprint, wired.review) == (expected, expected)
    assert any("SPENT" in n for n in notes)


def test_the_loop_back_does_NOT_re_run_triage(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """Triage is spent after one pass, however many times the reviewer holds.

    Every candidate carries a decision once triage has run, so a second triage
    would re-litigate rulings rather than close the runway the reviewer wrote —
    and it would spend a full opus dispatch per loop to do it. The loop-back
    goes to plan-sprint alone, which is also the last producer and sees the
    whole PR.
    """
    _verdicts(monkeypatch, wired, routing.Verdict.HOLD_REDISPATCH)
    _run()
    assert wired.triage == 1, (
        f"triage ran {wired.triage} times across {routing.MAX_LOOPS} loop-backs. "
        f"Rulings are made once; re-running it re-opens settled dispositions and "
        f"costs a full dispatch per pass to do so."
    )


def test_the_loop_back_is_a_correction_pass_not_a_fresh_placement(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """The loop-back closes the reviewer's runway; it does not re-plan.

    The first plan-sprint pass is fresh; every loop-back after it is a
    correction.
    """
    _plans_one(monkeypatch, wired)
    _verdicts(monkeypatch, wired, routing.Verdict.HOLD_REDISPATCH)
    _run()
    assert wired.correction_passes == [False] + [True] * routing.MAX_LOOPS


def test_a_loop_back_that_earns_merge_stops_there(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """The loop is spent on success too — it does not keep going after MERGE."""
    _plans_one(monkeypatch, wired)
    _verdicts(monkeypatch, wired, routing.Verdict.HOLD_REDISPATCH, routing.Verdict.MERGE)
    _url, verdict, loops, _notes = _run()
    assert (verdict, loops) == (routing.Verdict.MERGE, 1)
    # TWO, and deliberately NOT `1 + routing.MAX_LOOPS` as its siblings use: this
    # run EARNS MERGE on its first loop-back and stops, so the bound is never
    # reached and a bound-relative count here would be wrong in both directions —
    # green today by coincidence, red the moment the ramp moves.
    assert (wired.sprint, wired.review) == (2, 2)
    # And triage is still spent exactly once, whatever the sprint child did.
    assert wired.triage == 1


def test_needs_assistance_never_loops(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """A human ruling is not something more passes can produce.

    Distinct from the redispatch case: this one has loop budget REMAINING and
    must still decline to spend it.
    """
    _plans_one(monkeypatch, wired)
    _verdicts(monkeypatch, wired, routing.Verdict.HOLD_NEEDS_ASSISTANCE)
    _url, verdict, loops, notes = _run()
    assert (verdict, loops) == (routing.Verdict.HOLD_NEEDS_ASSISTANCE, 0)
    assert (wired.triage, wired.sprint, wired.review) == (1, 1, 1)
    # THE NOTE STATES THE LOOP DECISION AND NOTHING ELSE. It used to say
    # "review-pr found at least one item only a human can rule on", and this
    # assertion PINNED that sentence — which is why the suite was green over it.
    # Wiring the CI gate into `_dispose` gave this parent a second path to the
    # same verdict, and on that path the sentence is false: the gate's own note
    # ends "review-pr was NOT dispatched". See
    # `test_convergence.test_the_needs_assistance_note_CLAIMS_NO_CAUSE`.
    assert any("more passes cannot produce a human decision" in n for n in notes)
    assert not any("review-pr found" in n for n in notes), (
        "the note names a cause this layer did not detect")


def test_a_RED_tree_HOLDS_before_review_pr_is_ever_dispatched(
    wired: _Calls, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MERGE must be unreachable on a red tree, and the parent is where that holds.

    THIS PARENT HAD NO GATE AT ALL until PR #124, and its `_dispose` docstring
    argued it needed none — "this family changes markdown only, so there is no
    build to settle". That is false about this repo: `.github/workflows/tests.yml`
    carries no `paths:` filter by deliberate choice and the suite greps prompts
    and docs, so a planning PR that edits only `.md` runs the full suite and can
    turn it red.

    THE ORDERING IS THE PROPERTY, and it is the one thing the static class guard
    in `test_ci_gate.py` explicitly says it cannot see: an AST call-set proves
    both calls exist in the module, not that the gate runs FIRST. A gate that
    runs after the dispatch has already let the reviewer produce a verdict.
    """
    _plans_one(monkeypatch, wired)
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    monkeypatch.setattr(pm, "ci_verdict",
                        lambda pr, **kw: (routing.CiVerdict.RED, ["suite"]))
    _url, verdict, loops, notes = _run()

    assert verdict is routing.Verdict.HOLD_REDISPATCH, (
        "a red tree reached a MERGE verdict — the gate did not hold")
    assert wired.review == 0, (
        f"review-pr was dispatched {wired.review} time(s) on a red tree; the gate "
        f"runs AFTER the dispatch, so the reviewer still got a verdict to give")
    assert any("blocking checks failed: suite" in n for n in notes), (
        f"the operator is not told WHICH check failed: {notes}")


def test_the_gate_reads_CI_with_repo_root_and_before_any_review(
    wired: _Calls, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both reads happen, both are repo-anchored, and both precede the dispatch.

    `repo_root` IS ASSERTED AND NOT ASSUMED. `read_check_policy` used to be
    reached only when it was present; without it `ci_verdict` returned NO_CHECKS
    on a repo that declares a gate and `ci_gate` reported "SKIPPED — no check
    declared blocking", which is not a HOLD. The gate would be present and inert
    — the exact shape `build_minor` shipped until PR #124, and the reason this
    asserts the argument rather than the call.

    THE PARAMETER BECAME REQUIRED ON 2026-08-20 and this assertion still earns
    its place: the fakes here take `**kw`, so a parent that dropped the keyword
    would sail past a signature that no longer permits it in production. What
    this arm pins is that the parent passes THE RIGHT TREE — `Path("/repo")`, not
    merely something.
    """
    _plans_one(monkeypatch, wired)
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    _run()

    assert [r[0] for r in wired.ci_reads] == ["wait_for_ci", "ci_verdict"], (
        f"the gate did not make exactly one settle-then-read pair: {wired.ci_reads}")
    assert wired.review == 1, "the review fake did not run, so the ordering arm is vacuous"
    for name, pr, repo_root, reviews_before in wired.ci_reads:
        assert pr == "43", f"{name} was given PR {pr!r}, not the PR under review"
        assert repo_root == Path("/repo"), (
            f"{name} was called without repo_root, so it cannot find "
            f"testing/check-policy.yaml and the gate forgives everything")
        assert reviews_before == 0, (
            f"{name} ran after {reviews_before} review dispatch(es) — the gate is "
            f"downstream of the verdict it is supposed to withhold")


def test_merge_still_says_it_is_not_an_unattended_merge(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """MERGE means the judge found nothing to correct — not "merge it".

    The sprint plan is the operator's surface and direction.md rows are
    by construction rulings no automated pass can make, so a clean verdict
    must not read as authorisation.
    """
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    _url, _verdict, _loops, notes = _run()
    assert any("does NOT mean" in n for n in notes)


def test_the_parent_judges_against_PLANNING_criteria(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """Reviewing a planning PR against BUILD criteria would judge the wrong thing.

    `review-pr` defaults to BUILD; this family must override it explicitly.
    """
    seen: list[object] = []

    def capture(review_input: object, repo_root: Path) -> ReviewResult:
        seen.append(review_input.review_type)
        return ReviewResult(pr_number="43", verdict=routing.Verdict.MERGE, this_pass=1, notes=[])

    monkeypatch.setattr(pm.review_pr, "run_review", capture)
    _run()
    assert seen and seen[0] is pm.ReviewType.PLANNING


def test_isolation_is_established_once_by_the_parent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two actors creating the same named worktree is `fatal: already exists`.

    The parent adds it; the children receive the path. Even across a loop-back,
    exactly one worktree is created.
    """
    added: list[str] = []
    monkeypatch.setattr(pm.act, "worktree_add",
                        lambda repo, name, ref: added.append(name) or Path("/tmp/wt"))
    monkeypatch.setattr(pm.own, "new_sprint_sections", lambda *a, **k: [])
    monkeypatch.setattr(
        pm.own, "scaffold_candidate_components",
        lambda *a, **k: pm.own.Scaffolded(created=[], resumed=[], extends=[],
                                          unnamed=[], not_a_feature=[], unsized=[]))
    monkeypatch.setattr(pm.act, "git_output", lambda *a, **k: BASE_SHA)
    monkeypatch.setattr(pm._shared, "repo_slug", lambda repo_root: "o/r")
    monkeypatch.setattr(pm.act, "base_ref", lambda pr, repo_root: "HEAD")
    monkeypatch.setattr(pm.triage, "run_triage_candidates", lambda **kw: PR_URL)
    monkeypatch.setattr(pm.sprint, "run_plan_sprint", lambda **kw: PR_URL)
    # This test wires its own stubs rather than taking `wired`, so the CI gate
    # has to be faked here too — left real it shells out to `gh` per loop.
    monkeypatch.setattr(pm, "wait_for_ci", lambda pr, **kw: True)
    monkeypatch.setattr(pm, "ci_verdict", lambda pr, **kw: (routing.CiVerdict.GREEN, []))
    monkeypatch.setattr(pm.review_pr, "run_review",
                        lambda ri, rr: ReviewResult(pr_number="43",
                                                    verdict=routing.Verdict.HOLD_REDISPATCH,
                                                    this_pass=1, notes=[]))
    _run()
    assert added == ["wt"], f"expected exactly one worktree, got {added}"


# THE REAL `component_dir` AND THE REAL `component_slug` ARE USED, DELIBERATELY.
# These helpers used to monkeypatch `component_dir` to `name.lower()`, and that
# single line is what made the both-signals dedup test below assert nothing: the
# two signals differ precisely in that one returns a SLUG and the other a raw
# heading, and a stub that lower-cases erases the difference the test exists to
# find. Both functions are pure path arithmetic with no I/O, so there was never
# anything to stub.


def _with_sections(monkeypatch: pytest.MonkeyPatch, *names: str) -> None:
    monkeypatch.setattr(pm.own, "new_sprint_sections", lambda *a, **k: list(names))


def _with_scaffolded(monkeypatch: pytest.MonkeyPatch, *names: str) -> None:
    """`names` are what the activity CREATED — always slugs, as it returns directory names."""
    monkeypatch.setattr(
        pm.own, "scaffold_candidate_components",
        lambda *a, **k: pm.own.Scaffolded(created=list(names), resumed=[],
                                          extends=[], unnamed=[],
                                          not_a_feature=[], unsized=[]))


def test_no_new_sections_means_no_research(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """The common case. A triage that adds no section must spend nothing on research."""
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    _run()
    assert wired.research_pools == []


# --- Step 1b: plan-candidates, and the input it restored ---------------------

def test_plan_candidates_runs_AFTER_triage_and_BEFORE_research(
        wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """Both halves of the ordering are load-bearing and they fail differently.

    Before triage there are no `ship` rulings to act on, so it would scaffold
    nothing. After research it would be scaffolding a component the research step
    has already been asked to research — which is the ordering `workflows.md`
    drew, and it describes a step researching something that does not exist yet.
    """
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    _with_scaffolded(monkeypatch, "Alpha")
    _run()
    assert wired.order[:3] == ["triage", "research", "feature"], (
        f"expected triage, then the scaffolded component's research, then its "
        f"plan written from that research, got {wired.order}")


def test_the_scaffolded_components_ARE_the_research_step_input(
        wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """THE POINT OF THE WHOLE CHANGE, and it is why this assertion is not about a note.

    The research step's only signal was "a sprint section this run added", and
    with plan-sprint sequenced behind it nothing ahead of it added one — the step
    was inert by construction and `plan_project`'s own docstring said so. A
    scaffolded component is now a real signal reaching it.
    """
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    _with_scaffolded(monkeypatch, "Alpha", "Beta")
    _run()
    assert wired.research_pools == [
        Path("/tmp/wt/docs/development/alpha/research"),
        Path("/tmp/wt/docs/development/beta/research"),
    ], "a scaffolded component did not reach the research step"


def test_a_component_reached_by_BOTH_signals_is_researched_ONCE(
        wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """The two signals are unioned, and a duplicate costs a full research cycle.

    Not hypothetical once `plan-feature` lands: a component can be scaffolded
    here AND gain a sprint section in the same dispatch, and each entry in this
    list is a `research-write` plus a `research-verify` dispatch.

    **THE SPELLINGS ARE DIFFERENT ON PURPOSE, AND THAT IS THE WHOLE TEST.** The
    scaffolder returns the directory name it made — a SLUG — while
    `new_sprint_sections` returns the heading as the operator typed it. An
    earlier version of this test passed the identical string down both paths and
    stubbed `component_dir` to lower-case it, so it proved only that
    `dict.fromkeys` de-duplicates equal strings, and stayed green while the real
    pair (`fleet-reliability` / `Fleet Reliability`) both survived the union.
    """
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    _with_scaffolded(monkeypatch, "fleet-reliability")
    _with_sections(monkeypatch, "Fleet Reliability")
    _run()
    assert wired.research_pools == [
        Path("/tmp/wt/docs/development/fleet-reliability/research")], (
        f"researched twice under two spellings of one component: {wired.research_pools}")


def test_the_SCAFFOLDED_brief_wins_when_a_component_arrives_down_both_signals(
        wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """Dedup decides HOW MANY; this decides WHICH BRIEF, and only one of them is true.

    A scaffolded component's brief points at the seeded synthesis; the sprint
    brief tells the child to read a sprint section. If the sprint signal won,
    the child would be sent to read a section that `plan-candidates` never wrote
    and `sprint.md` never gained — the false premise the branch exists to avoid.
    """
    contexts: list[str] = []
    monkeypatch.setattr(pm.write, "run_write",
                        lambda **kw: contexts.append(str(kw["context"])) or PR_URL)
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    _with_scaffolded(monkeypatch, "fleet-reliability")
    _with_sections(monkeypatch, "Fleet Reliability")
    _run()

    assert len(contexts) == 1
    assert "scaffolded from a shipped research candidate" in contexts[0]
    assert "sprint section" not in contexts[0].replace("NO sprint section", "")


def test_the_scaffolder_is_given_the_WORKTREE_copy_of_the_candidates_file(
        wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """It WRITES, so a repo-root path would put the scaffolding outside the PR.

    `candidates_path` arrives repo-root-absolute — the convention every sibling
    follows — and the triage child re-anchors it the same way. A scaffolder
    handed `/repo/c.md` would read the pre-triage rulings from the main checkout
    and create directories that no branch carries and no review ever sees.
    """
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    _run()
    assert wired.scaffold_args == [(Path("/tmp/wt"), Path("/tmp/wt/c.md"))], (
        f"scaffolder was given {wired.scaffold_args}")


def test_EVERY_field_of_Scaffolded_REACHES_THE_OPERATOR_as_its_own_note(
        wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """The claim `Scaffolded` was widened FOR, asserted over the whole type.

    Its docstring says a bare list of created slugs "is what made three separate
    failures silent" — an extending candidate, an abandoned pool and a filer typo
    all read as "created nothing", and that note reads as health. The parent
    answers with one note per entry. **Nothing asserted any of it**: every test
    here checked dispatch counts and brief text, so the three quiet outcomes —
    the whole reason the return type has four lists — were untested.

    KEYED ON THE TYPE'S FIELDS RATHER THAN ON FOUR EXAMPLES. A fifth bucket added
    later fails here until the parent gives it a note, which is the property
    worth holding: the failure mode is a list nobody prints, and a test naming
    today's four lists cannot see it.

    IT COUNTS THE NOTES RATHER THAN LOOKING FOR ONE, AND THE FIRST VERSION DID
    NOT — which a mutation caught and a reading would not have. `created` and
    `resumed` feed the research fan-out, so their slugs ALSO appear in "New
    component `x` — researching before it is planned". A presence test therefore
    stayed green with the whole `resumed` note loop deleted: the slug was still
    in the notes, under a sentence that says something else entirely. The
    expected count is derived from `to_research` rather than hard-coded per
    field, so a bucket that starts or stops feeding research adjusts with it.
    """
    scaffolded = pm.own.Scaffolded(
        created=["alpha"], resumed=["beta"],
        extends=[("C-001", "gamma")], unnamed=[("C-002", "···")],
        # The two DECLINE reasons the `size` column added. Populated here because
        # this test's whole claim is that no field reaches the operator as a bare
        # count — a field left empty makes its own assertion vacuous, which is
        # what the guard below says out loud.
        not_a_feature=[("C-003", "phase")], unsized=[("C-004", "unsized")])
    monkeypatch.setattr(pm.own, "scaffold_candidate_components",
                        lambda *a, **k: scaffolded)
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    _url, _verdict, _loops, notes = _run()

    feeds_research = set(scaffolded.to_research)
    for field in pm.own.Scaffolded._fields:
        entries = getattr(scaffolded, field)
        assert entries, f"the fixture left {field} empty, so its assertion is vacuous"
        for entry in entries:
            # A row-keyed list carries `(id, name)`; a component-keyed one a bare
            # slug. Both have to be findable in the notes by what identifies them.
            for token in (entry if isinstance(entry, tuple) else (entry,)):
                # One note for the disposition, plus one for the research
                # dispatch if this bucket feeds it.
                want = 2 if token in feeds_research else 1
                got = sum(1 for n in notes if token in n)
                assert got >= want, (
                    f"`Scaffolded.{field}` carried {token!r} and {got} note(s) "
                    f"mention it, not {want} — that outcome is invisible to the "
                    f"operator, or is visible only under another step's sentence, "
                    f"which is exactly what this type was widened to prevent. "
                    f"Notes: {notes}")

    assert not any("empty working set" in n for n in notes), (
        "the parent reported an empty working set while four rows were disposed of")


def test_the_research_brief_for_a_SCAFFOLDED_component_claims_no_sprint_section(
        wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """A FALSE PREMISE handed to a model is worse than a thin one.

    The brief for a sprint-section component tells the child to read that section
    first. A scaffolded component has none — `sprint.md` is the operator's file
    and nothing in this pipeline writes it — so reusing that wording would send
    the child looking for something that does not exist and cannot be created.
    It gets pointed at the seeded synthesis instead.
    """
    contexts: list[str] = []
    monkeypatch.setattr(pm.write, "run_write",
                        lambda **kw: contexts.append(str(kw["context"])) or PR_URL)
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    _with_scaffolded(monkeypatch, "Alpha")
    _run()

    assert len(contexts) == 1
    assert "synthesis.md" in contexts[0], "the child was not pointed at its actual brief"
    assert "NO sprint section" in contexts[0]
    assert "was just added to" not in contexts[0], (
        "the scaffolded component was told a sprint section was added for it")


def test_each_new_section_is_researched_into_its_OWN_pool(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """Per-component pools, not one shared one.

    Research Standard §1 puts a component pool inside its component; two
    components sharing a pool would give each the other's evidence.
    """
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    _with_sections(monkeypatch, "Alpha", "Beta")
    _run()
    assert wired.research_pools == [
        Path("/tmp/wt/docs/development/alpha/research"),
        Path("/tmp/wt/docs/development/beta/research"),
    ]


def test_the_research_fanout_does_not_hijack_the_product_pool(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """REGRESSION. The loop originally rebound `research_dir`, the parameter
    naming the PRODUCT pool the planning children work from — so after
    researching one component, the loop-back would hand plan-sprint that
    component's pool instead. A shadowed parameter is a silent wrong-argument
    bug: nothing raises, and the child simply reads the wrong evidence.
    """
    product_pool = Path("/repo/r")
    _verdicts(monkeypatch, wired, routing.Verdict.HOLD_REDISPATCH)
    _with_sections(monkeypatch, "Alpha")
    _run()
    # One pool per plan-sprint dispatch — the initial pass plus one per
    # loop-back. The COUNT is incidental to this regression; what matters is
    # that EVERY entry is the product pool, so it is derived from the bound
    # rather than pinned at two.
    # THE REGRESSION THIS GUARDS MOVED, AND THE ASSERTION MOVED WITH IT. It read
    # `sprint_pools == [product_pool] * (1 + MAX_LOOPS)` — the loop-back must not
    # rebind `research_dir` to a component pool. `plan-sprint` no longer takes a
    # research pool at all since 2026-08-19, so the parameter that could be
    # rebound is gone and that half is unfalsifiable rather than merely passing.
    #
    # What survives is the property the regression was about: **every loop-back
    # hands the SAME target as the first pass.** Now the target is the component,
    # so a loop-back that drifted onto a different one is the same defect wearing
    # a different parameter name, and this catches it.
    assert len(set(wired.sprint_pools)) == 1, (
        f"plan-sprint was handed {wired.sprint_pools} — the loop-back must still "
        f"receive the PRODUCT pool, not a component's"
    )


def test_the_component_sweep_is_based_on_THIS_RUN_not_on_the_branch(
        wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """Step 2 asks what THIS DISPATCH added, and `origin/main` answers otherwise.

    The sweep's `base_ref` defaulted to `origin/main`, which reports everything
    the BRANCH has accumulated since it forked. On the `--pr` redispatch path
    both entrypoints document, the worktree is cut from a branch that already
    carries a `## Sprint:` heading an earlier pass added AND researched — so
    that section reads as new a second time and buys a second full
    research-write plus research-verify cycle for a component that already has
    a pool. Nothing raises; the run simply costs twice.

    Asserting on the VALUE rather than merely on "a base was passed": a base
    that is present and wrong is exactly the state this replaced.
    """
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    # The redispatch path specifically: it is the one where the branch already
    # carries an earlier pass's sections. `pr_branch` is a `gh` call, stubbed at
    # its boundary like every other one in this module.
    monkeypatch.setattr(pm.act, "pr_branch", lambda pr, repo_root: "some/branch")
    _run(pr_number="43")
    assert wired.sweep_bases == [BASE_SHA], (
        f"the sweep was based on {wired.sweep_bases}; it must be the commit the "
        f"worktree started from ({BASE_SHA}), never `origin/main` and never a "
        f"symbolic ref that moves while the run is in flight")


def test_the_base_is_pinned_BEFORE_any_child_can_move_it(
        wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """WHEN, not merely whether. A base read after triage commits is the bug.

    `HEAD` is a moving target inside a run: the triage child commits to this
    same worktree. Pinning after Step 1 would silently exclude anything triage
    itself wrote, and the resulting sweep would be empty for a reason nobody
    could see. The recorded third element is the children dispatched so far,
    which is the only way to assert ordering from outside.
    """
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    _run()
    pins = [c for c in wired.git_calls if c[1] == ("git", "rev-parse", "HEAD")]
    assert len(pins) == 1, f"expected exactly one base pin, got {pins}"
    assert pins[0][2] == (), (
        f"the base was pinned after {pins[0][2]} had already run. It must be "
        f"read before any child writes to the worktree, or it is not the "
        f"commit this dispatch started from.")
    assert pins[0][0] == Path("/tmp/wt"), (
        f"the base was read from {pins[0][0]}; it must be read from the "
        f"WORKTREE — the repo's HEAD is a different commit and is not what "
        f"Step 2 diffs against")


# --- the sweep's real logic, against a real repository -------------------------
#
# Every test above stubs `new_sprint_sections`, which is correct for routing —
# but it left the function's own parsing exercised by nothing. It splits on an
# em-dash, strips a marker, and reads a `git diff`, and all three are the kind of
# thing that is right until a heading is written slightly differently.

def _git(repo: Path, *args: str) -> str:
    import subprocess
    return subprocess.run(["git", *args], cwd=repo, check=True,
                          capture_output=True, text=True).stdout


def _sha(repo: Path) -> str:
    """The literal commit, never the string "HEAD".

    `HEAD` moves with the next commit, so a base captured as the symbol is the
    same commit as the tip by the time the diff runs and the sweep reads empty.
    That is precisely the defect these tests were added for, and writing it into
    the test first is how it got noticed here rather than in production.
    """
    return _git(repo, "rev-parse", "HEAD").strip()


@pytest.fixture
def real_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "r"
    (repo / "docs" / "development").mkdir(parents=True)
    _git(repo.parent, "init", "-q", "r")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "docs" / "development" / "sprint.md").write_text("# Sprint\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    return repo


def test_the_sweep_reads_ADDED_headings_and_not_edited_ones(real_repo: Path) -> None:
    """The real parse, against a real diff. Added is a new component; edited is not.

    Researching a component because its prose moved spends a full research cycle
    on nothing, and the difference between the two cases is a single leading
    `+` in a diff — invisible in any test that stubs this function out.
    """
    from modules.assistant.plan.plan_project import plan_project_activities as own

    base = _sha(real_repo)
    sprint = real_repo / "docs" / "development" / "sprint.md"
    sprint.write_text("# Sprint\n\n## Sprint: Fleet Reliability — 40h\n\nbody\n")
    _git(real_repo, "commit", "-aqm", "add a section")

    rel = "docs/development/sprint.md"
    assert own.new_sprint_sections(real_repo, rel, base_ref=base) == \
        ["Fleet Reliability"], "an ADDED heading is a new component"

    after_add = _sha(real_repo)
    sprint.write_text("# Sprint\n\n## Sprint: Fleet Reliability — 40h\n\nreworded\n")
    _git(real_repo, "commit", "-aqm", "edit the body")
    assert own.new_sprint_sections(real_repo, rel, base_ref=after_add) == [], (
        "a section whose BODY changed carries no added `## Sprint:` line and "
        "must not be researched again")


def test_a_heading_with_no_name_FAILS_LOUDLY_rather_than_slugging_to_nothing(
        real_repo: Path) -> None:
    """`## Sprint: — 40h` yields no folder name, and silence would be worse.

    The alternative — skipping it — would drop a real component from the sweep
    with nothing said, which is the failure mode this whole family is built
    against. The raise names the section, so the operator can see which heading
    is malformed. The cost is a crash mid-pipeline after Step 1 has opened a PR;
    that is the correct trade, and it is written down here so the next reader
    does not "fix" it into a silent skip.
    """
    from modules.assistant.plan.plan_project import plan_project_activities as own

    base = _sha(real_repo)
    sprint = real_repo / "docs" / "development" / "sprint.md"
    sprint.write_text("# Sprint\n\n## Sprint: — 40h\n")
    _git(real_repo, "commit", "-aqm", "malformed heading")

    names = own.new_sprint_sections(real_repo, "docs/development/sprint.md",
                                    base_ref=base)
    assert names == [""], f"the sweep read {names}"
    with pytest.raises(ValueError, match="sprint section .* yields no folder name"):
        own.component_dir(real_repo, names[0], source="sprint section")


def test_component_dir_slugs_the_way_the_tree_is_already_named(real_repo: Path) -> None:
    """The convention applied in code: a mismatch is invisible to every walk."""
    from modules.assistant.plan.plan_project import plan_project_activities as own

    assert own.component_dir(real_repo, "Fleet Reliability", source="sprint section") == \
        real_repo / "docs" / "development" / "fleet-reliability"
    assert own.component_dir(real_repo, "Memory Management Framework",
                             source="sprint section") == \
        real_repo / "docs" / "development" / "memory-management-framework"

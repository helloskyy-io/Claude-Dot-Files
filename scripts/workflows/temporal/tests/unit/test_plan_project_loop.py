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


@pytest.fixture
def wired(monkeypatch: pytest.MonkeyPatch) -> _Calls:
    """Stub all three children and isolation; the parent's own logic is untouched."""
    calls = _Calls()

    def fake_triage(**kw: object) -> str:
        calls.triage += 1
        calls.order.append("triage")
        return PR_URL

    def fake_sprint(**kw: object) -> str:
        calls.sprint += 1
        calls.order.append("sprint")
        calls.correction_passes.append(bool(kw.get("correction_pass", False)))
        calls.sprint_pools.append(kw["research_dir"])
        return PR_URL

    def fake_write(**kw: object) -> str:
        calls.research_pools.append(kw["research_dir"])
        calls.order.append("research")
        return PR_URL

    monkeypatch.setattr(pm.triage, "run_triage_candidates", fake_triage)
    monkeypatch.setattr(pm.sprint, "run_plan_sprint", fake_sprint)
    monkeypatch.setattr(pm.act, "worktree_add", lambda *a, **k: Path("/tmp/wt"))
    # The parent reads its own repo slug BEFORE the triage child, so the number
    # it takes out of the child's URL can be checked against the repository the
    # dispatch is operating in. It is a `gh` call; faked at its boundary.
    monkeypatch.setattr(pm._shared, "repo_slug", lambda repo_root: "o/r")
    monkeypatch.setattr(pm.write, "run_write", fake_write)
    monkeypatch.setattr(pm.verify, "run_verify", lambda **kw: PR_URL)
    # No new sections by default: the research fan-out is opt-in per test, and a
    # real `git diff` against a fake worktree would fail for the wrong reason.
    monkeypatch.setattr(pm.own, "new_sprint_sections", lambda *a, **k: [])
    monkeypatch.setattr(pm.own, "component_dir",
                        lambda root, name: Path("/tmp/wt/docs/development/x"))
    return calls


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
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    _run()
    assert wired.order == ["triage", "sprint"], (
        f"the parent dispatched its children as {wired.order}. Triage rules the "
        f"candidates and plan-sprint places what they ruled — reversed, the "
        f"sprint plan is written from rulings that have not been made yet."
    )


def test_research_sits_BETWEEN_triage_and_the_sprint_plan(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """The gap is the whole point of the split, so its position is pinned.

    `plan-candidates` and `plan-feature` land in this same gap later. If the
    research fan-out drifted to either end, the position they are meant to
    occupy would quietly stop existing.
    """
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    _with_sections(monkeypatch, "Alpha")
    _run()
    assert wired.order == ["triage", "research", "sprint"], (
        f"the parent dispatched {wired.order} — component research must run "
        f"after the rulings exist and before the plan is written from them"
    )


def test_redispatch_loops_to_the_bound_then_stops(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """A permanently-redispatching reviewer must NOT loop forever.

    This is the regression that matters: the verdict never becomes MERGE, so
    only the loop bound stops it.
    """
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
    _verdicts(monkeypatch, wired, routing.Verdict.HOLD_REDISPATCH)
    _run()
    assert wired.correction_passes == [False] + [True] * routing.MAX_LOOPS


def test_a_loop_back_that_earns_merge_stops_there(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """The loop is spent on success too — it does not keep going after MERGE."""
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
    _verdicts(monkeypatch, wired, routing.Verdict.HOLD_NEEDS_ASSISTANCE)
    _url, verdict, loops, notes = _run()
    assert (verdict, loops) == (routing.Verdict.HOLD_NEEDS_ASSISTANCE, 0)
    assert (wired.triage, wired.sprint, wired.review) == (1, 1, 1)
    assert any("only a human can rule" in n for n in notes)


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
    monkeypatch.setattr(pm._shared, "repo_slug", lambda repo_root: "o/r")
    monkeypatch.setattr(pm.triage, "run_triage_candidates", lambda **kw: PR_URL)
    monkeypatch.setattr(pm.sprint, "run_plan_sprint", lambda **kw: PR_URL)
    monkeypatch.setattr(pm.review_pr, "run_review",
                        lambda ri, rr: ReviewResult(pr_number="43",
                                                    verdict=routing.Verdict.HOLD_REDISPATCH,
                                                    this_pass=1, notes=[]))
    _run()
    assert added == ["wt"], f"expected exactly one worktree, got {added}"


def _with_sections(monkeypatch: pytest.MonkeyPatch, *names: str) -> None:
    monkeypatch.setattr(pm.own, "new_sprint_sections", lambda *a, **k: list(names))
    monkeypatch.setattr(pm.own, "component_dir",
                        lambda root, name: Path("/tmp/wt/docs/development") / name.lower())


def test_no_new_sections_means_no_research(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """The common case. A triage that adds no section must spend nothing on research."""
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    _run()
    assert wired.research_pools == []


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
    assert wired.sprint_pools == [product_pool] * (1 + routing.MAX_LOOPS), (
        f"plan-sprint was handed {wired.sprint_pools} — the loop-back must still "
        f"receive the PRODUCT pool, not a component's"
    )

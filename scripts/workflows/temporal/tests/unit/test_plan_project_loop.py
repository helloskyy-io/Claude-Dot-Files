"""plan-project routes on the verdict, and loops exactly once.

WHY THIS EXISTS. `plan-sprint` ran twice with no parent, so its output reached
the operator UNJUDGED — on the only autonomous write to `sprint.md`. This parent
is the judge, and the property that matters is not that it calls `review-pr`; it
is that it calls it the RIGHT NUMBER OF TIMES for each verdict.

Both children are stubbed. The parent calls no model by design, so a test that
exercised the real children would be testing them, not the routing — and the
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
    """Counts what the parent actually dispatched, per child."""

    def __init__(self) -> None:
        self.triage = 0
        self.review = 0
        self.correction_passes: list[bool] = []
        self.research_pools: list[Path] = []
        self.triage_pools: list[Path] = []


@pytest.fixture
def wired(monkeypatch: pytest.MonkeyPatch) -> _Calls:
    """Stub both children and isolation; the parent's own logic is untouched."""
    calls = _Calls()

    def fake_triage(**kw: object) -> str:
        calls.triage += 1
        calls.correction_passes.append(bool(kw.get("correction_pass", False)))
        calls.triage_pools.append(kw["research_dir"])
        return PR_URL

    def fake_write(**kw: object) -> str:
        calls.research_pools.append(kw["research_dir"])
        return PR_URL

    monkeypatch.setattr(pm.sprint, "run_plan_sprint", fake_triage)
    monkeypatch.setattr(pm.act, "worktree_add", lambda *a, **k: Path("/tmp/wt"))
    # The parent reads its own repo slug BEFORE the triage child, so the number
    # it takes out of the child's URL can be checked against the repository the
    # dispatch is operating in. It is a `gh` call; faked at its boundary.
    monkeypatch.setattr(pm._shared, "repo_slug", lambda repo_root: "o/r")
    monkeypatch.setattr(pm.write, "run_write", fake_write)
    monkeypatch.setattr(pm.verify, "run_verify", lambda **kw: PR_URL)
    # No new sections by default: the research fan-out is opt-in per test, and a
    # real `git diff` against a fake worktree would fail for the wrong reason.
    monkeypatch.setattr(pm.act, "new_sprint_sections", lambda *a, **k: [])
    monkeypatch.setattr(pm.act, "component_dir",
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


def test_merge_runs_one_triage_and_one_review(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """The happy path spends exactly two child dispatches, never three."""
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    url, verdict, loops, _notes = _run()
    assert (url, verdict, loops) == (PR_URL, routing.Verdict.MERGE, 0)
    assert (wired.triage, wired.review) == (1, 1)


def test_redispatch_loops_exactly_once_then_stops(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """A permanently-redispatching reviewer must NOT loop forever.

    This is the regression that matters: the verdict never becomes MERGE, so
    only the loop bound stops it. Two triages and two reviews, then done.
    """
    _verdicts(monkeypatch, wired, routing.Verdict.HOLD_REDISPATCH)
    _url, verdict, loops, notes = _run()
    assert loops == 1
    assert verdict is routing.Verdict.HOLD_REDISPATCH
    assert (wired.triage, wired.review) == (2, 2)
    assert any("SPENT" in n for n in notes)


def test_the_loop_back_is_a_correction_pass_not_a_fresh_triage(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """Re-triaging would re-litigate rulings the first pass already made.

    Every candidate carries a decision after pass 1; the second pass exists to
    close the reviewer's runway, not to reconsider the dispositions.
    """
    _verdicts(monkeypatch, wired, routing.Verdict.HOLD_REDISPATCH)
    _run()
    assert wired.correction_passes == [False, True]


def test_a_loop_back_that_earns_merge_stops_there(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """The loop is spent on success too — it does not keep going after MERGE."""
    _verdicts(monkeypatch, wired, routing.Verdict.HOLD_REDISPATCH, routing.Verdict.MERGE)
    _url, verdict, loops, _notes = _run()
    assert (verdict, loops) == (routing.Verdict.MERGE, 1)
    assert (wired.triage, wired.review) == (2, 2)


def test_needs_assistance_never_loops(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """A human ruling is not something more passes can produce.

    Distinct from the redispatch case: this one has loop budget REMAINING and
    must still decline to spend it.
    """
    _verdicts(monkeypatch, wired, routing.Verdict.HOLD_NEEDS_ASSISTANCE)
    _url, verdict, loops, notes = _run()
    assert (verdict, loops) == (routing.Verdict.HOLD_NEEDS_ASSISTANCE, 0)
    assert (wired.triage, wired.review) == (1, 1)
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
    monkeypatch.setattr(pm.act, "new_sprint_sections", lambda *a, **k: [])
    monkeypatch.setattr(pm._shared, "repo_slug", lambda repo_root: "o/r")
    monkeypatch.setattr(pm.sprint, "run_plan_sprint", lambda **kw: PR_URL)
    monkeypatch.setattr(pm.review_pr, "run_review",
                        lambda ri, rr: ReviewResult(pr_number="43",
                                                    verdict=routing.Verdict.HOLD_REDISPATCH,
                                                    this_pass=1, notes=[]))
    _run()
    assert added == ["wt"], f"expected exactly one worktree, got {added}"


def _with_sections(monkeypatch: pytest.MonkeyPatch, *names: str) -> None:
    monkeypatch.setattr(pm.act, "new_sprint_sections", lambda *a, **k: list(names))
    monkeypatch.setattr(pm.act, "component_dir",
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
    naming the PRODUCT pool that plan-sprint triages — so after researching one
    component, the loop-back would hand plan-sprint that component's pool
    instead. A shadowed parameter is a silent wrong-argument bug: nothing
    raises, and the triage simply reads the wrong evidence.
    """
    product_pool = Path("/repo/r")
    _verdicts(monkeypatch, wired, routing.Verdict.HOLD_REDISPATCH)
    _with_sections(monkeypatch, "Alpha")
    _run()
    assert wired.triage_pools == [product_pool, product_pool], (
        f"plan-sprint was handed {wired.triage_pools} — the loop-back must still "
        f"receive the PRODUCT pool, not a component's"
    )

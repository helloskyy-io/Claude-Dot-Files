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
        self.scaffold = 0
        self.sprint = 0
        self.review = 0
        self.order: list[str] = []
        self.correction_passes: list[bool] = []
        self.research_pools: list[Path] = []
        self.sprint_pools: list[Path] = []
        # (tree, argv, children dispatched SO FAR) for every git read the parent
        # makes. The third element is what turns "it pinned a base" into "it
        # pinned it before anything could move".
        self.git_calls: list[tuple[Path, tuple[str, ...], tuple[str, ...]]] = []
        # Every `base_ref` Step 2's sweep was actually given.
        self.sweep_bases: list[object] = []


@pytest.fixture
def wired(monkeypatch: pytest.MonkeyPatch) -> _Calls:
    """Stub all three children and isolation; the parent's own logic is untouched."""
    calls = _Calls()

    def fake_triage(**kw: object) -> str:
        calls.triage += 1
        calls.order.append("triage")
        return PR_URL

    def fake_scaffold(**kw: object) -> str:
        calls.scaffold += 1
        calls.order.append("scaffold")
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
    monkeypatch.setattr(pm.scaffold, "run_plan_candidates", fake_scaffold)
    monkeypatch.setattr(pm.sprint, "run_plan_sprint", fake_sprint)
    monkeypatch.setattr(pm.act, "worktree_add", lambda *a, **k: Path("/tmp/wt"))
    # The parent pins the commit its worktree started from, so Step 2 asks "what
    # did THIS run add" rather than "what has this branch accumulated". Faked at
    # its boundary — the worktree above is a path, not a repository — and
    # recorded, because a base taken at the WRONG moment is the whole defect and
    # is invisible unless the call is observed.
    def fake_git_output(tree: Path, cmd: list[str], _why: str) -> str:
        calls.git_calls.append((tree, tuple(cmd), tuple(calls.order)))
        return f"{BASE_SHA}\n"

    monkeypatch.setattr(pm.act, "git_output", fake_git_output)
    # The parent reads its own repo slug BEFORE the triage child, so the number
    # it takes out of the child's URL can be checked against the repository the
    # dispatch is operating in. It is a `gh` call; faked at its boundary.
    monkeypatch.setattr(pm._shared, "repo_slug", lambda repo_root: "o/r")
    monkeypatch.setattr(pm.write, "run_write", fake_write)
    monkeypatch.setattr(pm.verify, "run_verify", lambda **kw: PR_URL)
    # No new components by default: the research fan-out is opt-in per test, and
    # a real `git diff` against a fake worktree would fail for the wrong reason.
    def no_components(*a: object, **k: object) -> list[str]:
        calls.sweep_bases.append(k.get("base_ref"))
        return []

    monkeypatch.setattr(pm.own, "scaffolded_components", no_components)
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
    """The happy path spends exactly four child dispatches, never five."""
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    url, verdict, loops, _notes = _run()
    assert (url, verdict, loops) == (PR_URL, routing.Verdict.MERGE, 0)
    assert (wired.triage, wired.scaffold, wired.sprint, wired.review) == (1, 1, 1, 1)


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
    assert wired.order == ["triage", "scaffold", "sprint"], (
        f"the parent dispatched its children as {wired.order}. Triage rules the "
        f"candidates and plan-sprint places what they ruled — reversed, the "
        f"sprint plan is written from rulings that have not been made yet."
    )


def test_scaffolding_sits_BETWEEN_triage_and_research(
        wired: _Calls, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The ordering the whole chain depends on, and it is not checkable by eye.

    Research is commissioned INTO a component pool, so the component has to exist
    and to mean something before the research child runs. This diagram was drawn
    the other way round in `docs/guide/workflows.md` until 2026-08-13 —
    `research(component)` ahead of `[plan-candidates]` — and that ordering is
    precisely what made the research step inert: a step drawn before the thing
    that produces its input has no input.

    Every call is present in either order, so nothing else in this file would
    catch it reversed.
    """
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    _with_components(monkeypatch, tmp_path, "alpha")
    _run()
    assert wired.order == ["triage", "scaffold", "research", "sprint"], (
        f"the parent dispatched {wired.order} — scaffolding must produce the "
        f"component before research is commissioned into it, and both must run "
        f"before the plan is written from them"
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


def test_the_loop_back_re_runs_NEITHER_child_ahead_of_plan_sprint(
        wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """Both earlier children are spent after one pass, however often the reviewer holds.

    Every candidate carries a decision once triage has run, so a second triage
    would re-litigate rulings rather than close the runway the reviewer wrote —
    and it would spend a full opus dispatch per loop to do it. The same argument
    reaches plan-candidates and more strongly: a second scaffolding pass would
    re-examine a structural decision the reviewer is holding the PR ON, and a
    component directory is durable in a way a table row is not.

    Both are asserted, not just triage. Adding a child to the front of a pipeline
    whose loop-back deliberately skips the front is exactly where a second
    dispatch per loop gets added without anyone noticing the bill.
    """
    _verdicts(monkeypatch, wired, routing.Verdict.HOLD_REDISPATCH)
    _run()
    assert (wired.triage, wired.scaffold) == (1, 1), (
        f"triage ran {wired.triage} times and plan-candidates {wired.scaffold} "
        f"across {routing.MAX_LOOPS} loop-backs. Both are one-shot: re-running "
        f"either re-opens a settled decision and costs a full dispatch per pass."
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
    # And both one-shot children are still spent exactly once, whatever the
    # sprint child did.
    assert (wired.triage, wired.scaffold) == (1, 1)


def test_needs_assistance_never_loops(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """A human ruling is not something more passes can produce.

    Distinct from the redispatch case: this one has loop budget REMAINING and
    must still decline to spend it.
    """
    _verdicts(monkeypatch, wired, routing.Verdict.HOLD_NEEDS_ASSISTANCE)
    _url, verdict, loops, notes = _run()
    assert (verdict, loops) == (routing.Verdict.HOLD_NEEDS_ASSISTANCE, 0)
    assert (wired.triage, wired.scaffold, wired.sprint, wired.review) == (1, 1, 1, 1)
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
    monkeypatch.setattr(pm.own, "scaffolded_components", lambda *a, **k: [])
    monkeypatch.setattr(pm.act, "git_output", lambda *a, **k: BASE_SHA)
    monkeypatch.setattr(pm._shared, "repo_slug", lambda repo_root: "o/r")
    monkeypatch.setattr(pm.triage, "run_triage_candidates", lambda **kw: PR_URL)
    monkeypatch.setattr(pm.scaffold, "run_plan_candidates", lambda **kw: PR_URL)
    monkeypatch.setattr(pm.sprint, "run_plan_sprint", lambda **kw: PR_URL)
    monkeypatch.setattr(pm.review_pr, "run_review",
                        lambda ri, rr: ReviewResult(pr_number="43",
                                                    verdict=routing.Verdict.HOLD_REDISPATCH,
                                                    this_pass=1, notes=[]))
    _run()
    assert added == ["wt"], f"expected exactly one worktree, got {added}"


def _with_components(monkeypatch: pytest.MonkeyPatch, tmp: Path, *slugs: str) -> None:
    """Pretend `plan-candidates` chartered these components.

    `component_pool` is stubbed onto a REAL tmp directory rather than left live,
    because the parent `mkdir`s what it returns: a stub pointing into `/tmp/wt`
    would have the routing tests writing directories outside any fixture, which
    is a side effect nothing in this module asked for.
    """
    monkeypatch.setattr(pm.own, "scaffolded_components", lambda *a, **k: list(slugs))
    monkeypatch.setattr(pm.own, "component_pool",
                        lambda tree, slug: tmp / "docs" / "development" / slug / "research")


def test_no_new_components_means_no_research(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """The common case, and it is the DESIGNED one.

    `plan-candidates` chartering nothing is its most frequent correct outcome —
    a ruled candidate that extends an existing component needs no new structure —
    so the pipeline must spend nothing on research when that happens.
    """
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    _run()
    assert wired.research_pools == []


def test_each_new_component_is_researched_into_its_OWN_pool(
        wired: _Calls, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Per-component pools, not one shared one.

    Research Standard §1 puts a component pool inside its component; two
    components sharing a pool would give each the other's evidence.
    """
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    _with_components(monkeypatch, tmp_path, "alpha", "beta")
    _run()
    assert wired.research_pools == [
        tmp_path / "docs" / "development" / "alpha" / "research",
        tmp_path / "docs" / "development" / "beta" / "research",
    ]


def test_a_runaway_scaffolding_pass_RESEARCHES_NOTHING_and_says_why(
        wired: _Calls, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The ceiling on the fan-out, and each iteration past it is two opus runs.

    This loop was written while the sweep was empty by construction, so its cost
    was zero however wrong its input was; `plan-candidates` made it live.
    Chartering is designed to be the RARE outcome, so a pass that charters many
    components has made a placement error — and researching it multiplies that
    error by a full research-write plus research-verify cycle each.
    """
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    over = [f"c{n}" for n in range(pm.MAX_NEW_COMPONENTS + 1)]
    _with_components(monkeypatch, tmp_path, *over)
    _, _, _, notes = _run()
    assert wired.research_pools == [], (
        f"{len(over)} components were researched over a ceiling of "
        f"{pm.MAX_NEW_COMPONENTS}; the cap is not bounding the fan-out")
    assert any("over a ceiling" in n for n in notes), (
        "the fan-out was capped SILENTLY. A step that stops without saying so "
        "is indistinguishable from one that had nothing to do, which is the "
        "exact confusion the note this replaces existed to prevent")


def test_a_fanout_AT_the_ceiling_still_researches(
        wired: _Calls, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """DISCRIMINATOR: without it the cap could be zero and every assertion above
    would still pass, while no component was ever researched again.

    THE FLOOR IS ASSERTED SEPARATELY AND THAT IS NOT BELT-AND-BRACES. Sizing the
    fixture from `MAX_NEW_COMPONENTS` makes the rest of this test VACUOUS at a
    ceiling of zero — `range(0)` is empty, no component is researched, and
    `0 == 0` passes while the step is dead. Found by mutating the constant to 0
    after writing it, which is the only way that shape shows up.
    """
    assert pm.MAX_NEW_COMPONENTS >= 1, (
        "the ceiling is below one, so plan-project can never research a "
        "component it just chartered — the step is off, not bounded")
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    at = [f"c{n}" for n in range(pm.MAX_NEW_COMPONENTS)]
    _with_components(monkeypatch, tmp_path, *at)
    _run()
    assert len(wired.research_pools) == pm.MAX_NEW_COMPONENTS


def test_the_research_fanout_does_not_hijack_the_product_pool(
        wired: _Calls, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """REGRESSION. The loop originally rebound `research_dir`, the parameter
    naming the PRODUCT pool the planning children work from — so after
    researching one component, the loop-back would hand plan-sprint that
    component's pool instead. A shadowed parameter is a silent wrong-argument
    bug: nothing raises, and the child simply reads the wrong evidence.
    """
    product_pool = Path("/repo/r")
    _verdicts(monkeypatch, wired, routing.Verdict.HOLD_REDISPATCH)
    _with_components(monkeypatch, tmp_path, "alpha")
    _run()
    # One pool per plan-sprint dispatch — the initial pass plus one per
    # loop-back. The COUNT is incidental to this regression; what matters is
    # that EVERY entry is the product pool, so it is derived from the bound
    # rather than pinned at two.
    assert wired.sprint_pools == [product_pool] * (1 + routing.MAX_LOOPS), (
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
# Every test above stubs `scaffolded_components`, which is correct for routing —
# but it leaves the function's own parsing exercised by nothing. It splits a
# path, counts its segments, and reads a `git diff` under a filter, and all three
# are the kind of thing that is right until a file lands one directory deeper.

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


def _charter(repo: Path, slug: str, body: str = "# C\n") -> Path:
    d = repo / "docs" / "development" / slug
    d.mkdir(parents=True, exist_ok=True)
    f = d / "roadmap.md"
    f.write_text(body)
    return f


def test_the_sweep_reads_ADDED_charters_and_not_edited_ones(real_repo: Path) -> None:
    """The real parse, against a real diff. Added is a new component; edited is not.

    Researching a component because its charter's prose moved spends a full
    research-write plus research-verify cycle on nothing, and the difference
    between the two cases is `--diff-filter=A` — invisible in any test that stubs
    this function out.
    """
    from modules.assistant.plan.plan_project import plan_project_activities as own

    base = _sha(real_repo)
    charter = _charter(real_repo, "fleet-reliability")
    _git(real_repo, "add", "-A")
    _git(real_repo, "commit", "-qm", "charter a component")

    assert own.scaffolded_components(real_repo, base_ref=base) == \
        ["fleet-reliability"], "an ADDED roadmap.md is a new component"

    after_add = _sha(real_repo)
    charter.write_text("# C\n\nreworded\n")
    _git(real_repo, "commit", "-aqm", "edit the charter")
    assert own.scaffolded_components(real_repo, base_ref=after_add) == [], (
        "a charter whose body changed is not a new component and must not be "
        "researched again")


def test_the_sweep_ignores_EVERY_OTHER_FILE_the_pipeline_writes_under_a_component(
        real_repo: Path) -> None:
    """DISCRIMINATOR, and the failure it prevents is a runaway research loop.

    The research children write a whole pool into `<component>/research/` on this
    same branch, and `plan-feature` will write phase docs beside the charter. A
    sweep that matched any added file under `docs/development/` would read every
    one of those as a NEW COMPONENT — including files the research step itself
    just created, which is a fan-out that grows what it feeds on.

    The nested `roadmap.md` is the sharp case: it is the right FILENAME at the
    wrong DEPTH, so a check keyed on the name alone passes it and a check keyed
    on the path shape does not.
    """
    from modules.assistant.plan.plan_project import plan_project_activities as own

    base = _sha(real_repo)
    comp = real_repo / "docs" / "development" / "alpha"
    (comp / "research" / "raw").mkdir(parents=True)
    (comp / "research" / "synthesis.md").write_text("# S\n")
    (comp / "research" / "raw" / "topic.md").write_text("# T\n")
    (comp / "research" / "roadmap.md").write_text("# not a charter\n")
    (comp / "phase1_first.md").write_text("# P\n")
    _git(real_repo, "add", "-A")
    _git(real_repo, "commit", "-qm", "everything except a charter")

    assert own.scaffolded_components(real_repo, base_ref=base) == [], (
        "the sweep matched something other than `<component>/roadmap.md`; a "
        "research pool it reads as a new component is a fan-out that feeds itself")


def test_the_pool_path_follows_the_convention_the_tree_is_already_named_by(
        real_repo: Path) -> None:
    """The convention applied in code: a mismatch is invisible to every walk.

    Research Standard §1 puts a component's pool INSIDE the component, so this
    is also what keeps two components from sharing evidence.
    """
    from modules.assistant.plan.plan_project import plan_project_activities as own

    assert own.component_pool(real_repo, "fleet-reliability") == \
        real_repo / "docs" / "development" / "fleet-reliability" / "research"

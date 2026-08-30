"""plan-project routes on the verdict, and loops up to `routing.MAX_LOOPS` times.

WHY THIS EXISTS. `triage-candidates` rules every candidate in the store and its
rulings reach the operator as a PR. Left parentless, that output arrived UNJUDGED
— the one place in the fleet where `author != judge` was not honoured. This
parent is the judge, and the property that matters is not that it calls
`review-pr`; it is that it calls it the RIGHT NUMBER OF TIMES for each verdict.

THE PARENT IS NARROW ON PURPOSE, AND THAT IS ITSELF A TESTED PROPERTY. It used to
research each scaffolded component and then plan, size and sprint it — five
children behind one dispatch — because no parent existed to hold those steps.
`research` and `plan` do now, so the steps left. `test_the_parent_dispatches_NO_
research_and_NO_planning_child` is what keeps them gone: every one of them was
added by a reasonable-looking commit, and nothing structural stopped the next.

Both children are stubbed. The parent calls no model by design, so a test that
exercised the real children would be testing them, not the routing — and the
routing is the whole content of a parent.

The loop bound is a MEASURED constant, not a preference: self-correction
plateaus at 3-5 passes, and one PR on this fleet reached eight review passes
with pass 8 reviewing the same tree as pass 7. A regression that raised
MAX_LOOPS would be invisible without these.
"""

from __future__ import annotations

import ast
import inspect
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
    order".
    """

    def __init__(self) -> None:
        self.triage = 0
        self.review = 0
        self.order: list[str] = []
        # The `pr_number` every triage dispatch was handed. The first pass may
        # carry the operator's `--pr` or None; every loop-back must carry the PR
        # step 1 opened, or the correction lands on a second PR nobody reviews.
        self.triage_prs: list[object] = []
        # Every positional argument pair the scaffolder was called with.
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
        calls.triage_prs.append(kw.get("pr_number"))
        return PR_URL

    monkeypatch.setattr(pm.triage, "run_triage_candidates", fake_triage)
    monkeypatch.setattr(pm.act, "worktree_add", lambda *a, **k: Path("/tmp/wt"))
    # THE BASE THIS RUN IS CUT FROM, stubbed for the same reason `repo_slug`
    # below is: it asks `gh`, and this loop is driven against a fake repo path.
    # It answers "HEAD" only here — production resolves the DEFAULT BRANCH, and
    # `test_a_new_branch_STARTS_FROM_THE_DEFAULT_BRANCH` is what holds that.
    monkeypatch.setattr(pm.act, "base_ref", lambda pr, repo_root: "HEAD")
    # THE CI GATE IS FAKED AT ITS BOUNDARY, GREEN, and it must be faked at ALL:
    # `_dispose` reads the CI verdict before dispatching review, and both reads
    # shell out to `gh`. Left real they cost ~5s per test against the live API
    # and make the outcome depend on a network — the gate's own cascade is
    # exercised by `test_ci_gate.py`, which drives the activity directly.
    def fake_wait_for_ci(pr: str, **kw: object) -> bool:
        # THE FOURTH ELEMENT IS THE REVIEW COUNT AT THE MOMENT OF THE READ, and
        # it is what makes "the gate ran first" checkable. A snapshot of `order`
        # was the obvious choice and is VACUOUS here — `order` records child
        # dispatches and `run_review` is not one of them, so `"review" not in
        # order` is true whatever the parent does. `calls.review` is incremented
        # by the review fake itself, so it cannot be true by construction.
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

    # The scaffolder scaffolds nothing by default: it reads and WRITES a real
    # tree, and the worktree here is a bare path. Faked at its boundary and
    # recorded — which paths the parent hands it is its own assertion below.
    def no_scaffold(*a: object, **k: object) -> pm.own.Scaffolded:
        calls.scaffold_args.append(a)
        calls.order.append("scaffold")
        return pm.own.Scaffolded(created=[], resumed=[], extends=[], unnamed=[],
                                 not_a_feature=[], unsized=[])

    monkeypatch.setattr(pm.own, "scaffold_candidate_components", no_scaffold)
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
        candidates_path=Path("/repo/c.md"), research_dir=Path("/repo/r"), **kw,
    )


def test_merge_runs_one_of_each_child(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """The happy path spends exactly one triage and one review, never two."""
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    url, verdict, loops, _notes = _run()
    assert (url, verdict, loops) == (PR_URL, routing.Verdict.MERGE, 0)
    assert (wired.triage, wired.review) == (1, 1)


def test_the_scaffold_runs_AFTER_triage(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """It acts on `ship` rulings, and before triage there are none.

    Both steps happen either way and neither counter would notice the swap, so
    the order is pinned here or nowhere. Reversed, the scaffolder reads the
    pre-triage file and creates directories for candidates nobody has ruled.
    """
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    _run()
    assert wired.order == ["triage", "scaffold"], (
        f"the parent ran {wired.order}. The scaffolder acts on rulings; running "
        f"it first means it acts on a file that carries none."
    )


def _child_workflow_imports(tree: ast.Module) -> set[str]:
    """The local names a module binds to child workflow modules.

    Keyed on the `_workflow` suffix every child module in this fleet carries, and
    reading the ALIAS where there is one, because that is what the call sites use
    — `from ..plan_sprint import plan_sprint_workflow as sprint` binds `sprint`,
    and a set of source module names would not match what a reader greps for.

    IT TAKES A PARSED TREE, NOT SOURCE, AND THAT IS NOT A STYLE CHOICE. The
    census in `test_a_census_guard_proves_its_own_predicate.py` recognises a
    tree-walking guard by `ast.parse(<something>.read_text(...))` appearing as one
    expression. Taking source here would move the only `ast.parse` inside this
    helper, out of the reading path — and the guard would silently drop out of
    the population it belongs to, auditing nothing while looking green. That
    census's own docstring records the same correction being forced on
    `test_a_new_branch_STARTS_FROM_THE_DEFAULT_BRANCH`.
    """
    return {
        alias.asname or alias.name.split(".")[-1]
        for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        for alias in node.names
        if alias.name.endswith("_workflow")
    }


@pytest.mark.parametrize("source,expected", [
    # THE NARROW SHAPE — exactly what the parent imports today.
    ("from ..triage_candidates import triage_candidates_workflow as triage\n"
     "from ...review_pr import review_pr_workflow as review_pr\n"
     "from .. import plan_activities as act\n",
     {"triage", "review_pr"}),
    # THE SHAPE THIS GUARD EXISTS TO CATCH — a research child pulled back in.
    ("from ..triage_candidates import triage_candidates_workflow as triage\n"
     "from ...review_pr import review_pr_workflow as review_pr\n"
     "from ...research.research_draft import research_draft_workflow as write\n",
     {"triage", "review_pr", "write"}),
    # A module that imports no child at all — the recogniser must not invent one.
    ("from pathlib import Path\nfrom .. import plan_activities as act\n", set()),
])
def test_the_import_recogniser_answers_correctly_on_a_literal(
        source: str, expected: set[str]) -> None:
    """The predicate above, exercised against snippets rather than only the tree.

    A walk over the production tree passes trivially if the recogniser stops
    recognising anything — the guard would report "no forbidden imports" on a
    parent that had every one of them back. These three literals are what make
    the assertion above mean something: one satisfying case, one violating case,
    and one with nothing to find.
    """
    assert _child_workflow_imports(ast.parse(source)) == expected


def test_the_parent_dispatches_NO_research_and_NO_planning_child(
        wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """The narrowing, held structurally rather than by anybody remembering it.

    This parent used to call `research-draft`, `research-refine`, `plan-draft`,
    `plan-refine` and `plan-sprint` inline — five children behind one dispatch,
    one worktree carrying all of their work into one review, and a failure
    anywhere orphaning everything behind it. Each arrived in a commit that looked
    reasonable on its own; what was missing was anything that noticed the shape.

    ASSERTED OVER THE IMPORTS RATHER THAN OVER A RUN, and that is the point. A
    dispatch-count assertion only sees a child on the path the fixture happens to
    take, so a step reintroduced behind a condition — exactly how the research
    step was added, and how it then sat inert for weeks — passes it. An import is
    unconditional and is the thing a reintroduction cannot avoid.

    `review-pr` and `triage-candidates` ARE the permitted set. It is stated as an
    exact set rather than a denylist so a SIXTH child cannot be added silently:
    the test fails on anything new, and whoever adds it has to say why here.
    """
    imported = _child_workflow_imports(
        ast.parse(Path(inspect.getfile(pm)).read_text(encoding="utf-8")))
    assert imported == {"triage", "review_pr"}, (
        f"plan-project imports the child workflows {sorted(imported)}. It is a "
        f"first-level parent: it rules candidates, gives the shipped ones a home, "
        f"and stops. Researching a scaffolded component is `research`'s run and "
        f"planning it is `plan`'s — both are parents in their own right, and "
        f"pulling either back in here rebuilds the five-deep pipeline this was "
        f"narrowed out of."
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
    assert (wired.triage, wired.review) == (expected, expected)
    assert any("SPENT" in n for n in notes)


def test_the_loop_back_RE_RUNS_triage(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """The correction pass goes to the only child that wrote anything.

    THIS ASSERTION IS THE REVERSE OF THE ONE IT REPLACES, and the reversal is the
    narrowing rather than a change of mind. It used to read `triage == 1`, on the
    argument that re-triaging "re-opens settled dispositions" and that the
    loop-back belonged to `plan-sprint` — the last producer, which "sees the whole
    PR". That argument picks between producers, and after the narrowing there is
    exactly one: `plan-sprint` left with the research and planning children, and
    `plan-candidates` is an activity with no model in it to correct.

    THE RE-LITIGATION RISK IT NAMED IS REAL AND THE CHILD IS WHAT ANSWERS IT.
    `_working_set` branches on the counted file: at zero untriaged it stops
    issuing a working set and tells the run its job is to REVISE — close the
    runway a reviewer wrote, change nothing else. Triage raises if it leaves any
    row untriaged, so every loop-back arrives at zero by construction and takes
    that branch. The guarantee lives in the artifact, which is why no
    `correction_pass` flag was added to carry it.
    """
    _verdicts(monkeypatch, wired, routing.Verdict.HOLD_REDISPATCH)
    _run()
    assert wired.triage == 1 + routing.MAX_LOOPS, (
        f"triage ran {wired.triage} times across {routing.MAX_LOOPS} loop-backs. "
        f"It is the only producing child left; a loop-back that dispatches "
        f"nothing spends a review pass on an unchanged tree."
    )


def test_the_loop_back_targets_the_OPEN_pr_and_not_a_fresh_one(
        wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """A correction that opens its own PR is a correction nobody reviews.

    The first dispatch may carry the operator's `--pr` or None — that is the
    caller's business. Every loop-back after it must carry the number step 1's
    URL yielded, or the child branches to "open a new PR" and the runway the
    reviewer wrote stays open on a PR that now has a sibling.
    """
    _verdicts(monkeypatch, wired, routing.Verdict.HOLD_REDISPATCH)
    _run()
    assert wired.triage_prs == [None] + ["43"] * routing.MAX_LOOPS, (
        f"triage was dispatched with {wired.triage_prs}. Every loop-back has to "
        f"land on the PR step 1 opened."
    )


def test_a_loop_back_that_earns_merge_stops_there(wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """The loop is spent on success too — it does not keep going after MERGE."""
    _verdicts(monkeypatch, wired, routing.Verdict.HOLD_REDISPATCH, routing.Verdict.MERGE)
    _url, verdict, loops, _notes = _run()
    assert (verdict, loops) == (routing.Verdict.MERGE, 1)
    # TWO, and deliberately NOT `1 + routing.MAX_LOOPS` as its siblings use: this
    # run EARNS MERGE on its first loop-back and stops, so the bound is never
    # reached and a bound-relative count here would be wrong in both directions —
    # green today by coincidence, red the moment the ramp moves.
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

    `direction.md` rows are by construction rulings no automated pass can make,
    so a clean verdict must not read as authorisation.
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
    monkeypatch.setattr(
        pm.own, "scaffold_candidate_components",
        lambda *a, **k: pm.own.Scaffolded(created=[], resumed=[], extends=[],
                                          unnamed=[], not_a_feature=[], unsized=[]))
    monkeypatch.setattr(pm._shared, "repo_slug", lambda repo_root: "o/r")
    monkeypatch.setattr(pm.act, "base_ref", lambda pr, repo_root: "HEAD")
    monkeypatch.setattr(pm.triage, "run_triage_candidates", lambda **kw: PR_URL)
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
    answers with one note per entry.

    KEYED ON THE TYPE'S FIELDS RATHER THAN ON FOUR EXAMPLES. A fifth bucket added
    later fails here until the parent gives it a note, which is the property
    worth holding: the failure mode is a list nobody prints, and a test naming
    today's six lists cannot see it.
    """
    scaffolded = pm.own.Scaffolded(
        created=["alpha"], resumed=["beta"],
        extends=[("C-d1uhacwn", "gamma")], unnamed=[("C-p5qvm3e7", "···")],
        # The two DECLINE reasons the `size` column added. Populated here because
        # this test's whole claim is that no field reaches the operator as a bare
        # count — a field left empty makes its own assertion vacuous, which is
        # what the guard below says out loud.
        not_a_feature=[("C-q65w30xm", "phase")], unsized=[("C-c5y9uqhk", "unsized")])
    monkeypatch.setattr(pm.own, "scaffold_candidate_components",
                        lambda *a, **k: scaffolded)
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    _url, _verdict, _loops, notes = _run()

    for field in pm.own.Scaffolded._fields:
        entries = getattr(scaffolded, field)
        assert entries, f"the fixture left {field} empty, so its assertion is vacuous"
        for entry in entries:
            # A row-keyed list carries `(id, name)`; a component-keyed one a bare
            # slug. Both have to be findable in the notes by what identifies them.
            for token in (entry if isinstance(entry, tuple) else (entry,)):
                assert any(token in n for n in notes), (
                    f"`Scaffolded.{field}` carried {token!r} and no note mentions "
                    f"it — that outcome is invisible to the operator, which is "
                    f"exactly what this type was widened to prevent. Notes: {notes}")

    assert not any("empty working set" in n for n in notes), (
        "the parent reported an empty working set while six rows were disposed of")


def test_a_scaffolded_component_NAMES_THE_TWO_DISPATCHES_that_take_it_forward(
        wired: _Calls, monkeypatch: pytest.MonkeyPatch) -> None:
    """The handoff surface, and the one thing the narrowing put on the operator.

    This parent used to research and plan a scaffolded component itself. It now
    stops at the seeded synthesis, and NOTHING downstream of this run picks the
    component up until `research` and then `plan` are dispatched at it —
    `feature-manager` will drive that pair, and until it exists the hop is
    manual. An operator reading only the verdict has no way to know that: the run
    succeeded, the PR is clean, and a component is sitting unresearched.

    ASSERTED ON BOTH `created` AND `resumed`, because they are the two buckets
    that leave a real directory behind. The other four either changed nothing or
    named something that already exists, and telling the operator to dispatch
    against those would be worse than saying nothing.
    """
    scaffolded = pm.own.Scaffolded(
        created=["alpha"], resumed=["beta"], extends=[], unnamed=[],
        not_a_feature=[], unsized=[])
    monkeypatch.setattr(pm.own, "scaffold_candidate_components",
                        lambda *a, **k: scaffolded)
    _verdicts(monkeypatch, wired, routing.Verdict.MERGE)
    _url, _verdict, _loops, notes = _run()

    for slug in ("alpha", "beta"):
        note = next(n for n in notes if slug in n)
        assert "research.sh" in note and "plan.sh" in note, (
            f"the note for `{slug}` does not name the two dispatches that take it "
            f"forward: {note!r}. The run stops here and the component does not "
            f"move until somebody fires them."
        )
        assert f"docs/development/{slug}" in note, (
            f"the note for `{slug}` does not carry a path the operator can paste: "
            f"{note!r}")


def _git(repo: Path, *args: str) -> str:
    import subprocess
    return subprocess.run(["git", *args], cwd=repo, check=True,
                          capture_output=True, text=True).stdout


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


def test_a_name_that_slugs_to_NOTHING_fails_loudly(real_repo: Path) -> None:
    """A `component` cell of `···` yields no folder name, and silence would be worse.

    The alternative — skipping it — would drop a shipped candidate from the
    scaffold with nothing said, which is the failure mode this whole family is
    built against. The raise names the SURFACE the name came from, so the
    operator opens the right file: `source` exists for that and has no default,
    because a default is the wrong answer a new caller inherits by saying nothing.
    """
    from modules.assistant.plan.plan_project import plan_project_activities as own

    with pytest.raises(ValueError, match="yields no folder name"):
        own.component_dir(real_repo, "···", source="`component` cell in candidates.md")


def test_component_dir_slugs_the_way_the_tree_is_already_named(real_repo: Path) -> None:
    """The convention applied in code: a mismatch is invisible to every walk."""
    from modules.assistant.plan.plan_project import plan_project_activities as own

    assert own.component_dir(real_repo, "Fleet Reliability",
                             source="`component` cell in candidates.md") == \
        real_repo / "docs" / "development" / "fleet-reliability"
    assert own.component_dir(real_repo, "Memory Management Framework",
                             source="`component` cell in candidates.md") == \
        real_repo / "docs" / "development" / "memory-management-framework"

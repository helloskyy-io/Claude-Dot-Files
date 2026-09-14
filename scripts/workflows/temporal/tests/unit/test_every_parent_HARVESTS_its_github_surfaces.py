"""Phase 10 requirement 4 — the STANDING CHECK for the model-issued half.

THE BUILD DECISION, STATED. The phase doc offers two shapes and requires one:
an enumerating sweep asserting that every workflow which posts to a GitHub
surface invokes the harvest into its own bag, or a per-run reconciliation
counting store-side comments against harvested completions. **This file is the
sweep, and it is the standing check.** The reconciliation is ALSO built —
`harvest.reconcile_surface`, driven by `scripts/reconcile_harvest.py` — because
r3(c) needs it to measure the window; but a reconciliation runs when an
operator points it at a bag, and a sweep runs on every push. The failure r4
names is *"a harvest which quietly stops working looks exactly like a run that
posted nothing"*, and the cheapest place to catch the commonest cause of that —
an entrypoint that never calls the harvest — is here, at authoring time, in the
family `test_every_parent_opens_a_run_bag` established.

WHY EVERY ENTRYPOINT AND NOT A SUBSET. The requirement says *"every workflow
which posts to a GitHub surface"*. Enumerated 2026-09-12 from the tree: every
`run_*.py` in the population ends in a pull-request URL or a review verdict
posted to one — `grep -l "pr_url\\|url = wf\\.\\|url, verdict\\|result.pr_number"
scripts/run_*.py` matched 16 of 16 (an earlier spelling of this command matched
on the bare substring `url`, which every file contains, and enumerated
nothing) — and Phase 3's inventory has no workflow that writes only to a file
store. So the swept population IS the posting population, and a future
entrypoint that posts nowhere is a classification this sweep would force
someone to state rather than assume — the same discipline `NON_STARTING_FILES`
applies one level up.

THE FOUR PROPERTIES, EACH ITS OWN TEST:

  1. PRESENCE — every entrypoint calls `harvest_github_surfaces`, once.
  2. EVERY PATH — the call sits in the `finally` of a `try` whose body IS the
     workflow handoff. THE WINDOW OPENS AT CHILD EXIT, NOT AT THE WORKFLOW'S
     RETURN: a child that posted and then had its parent raise still wrote to
     GitHub, and the failed runs are the ones an operator reconstructs. The
     first cut of this sweep asserted line ORDER only — handoff line < harvest
     line — which every entrypoint satisfied while the harvest sat on the
     success path alone, so a workflow that raised after posting harvested
     nothing and recorded no gap. Found in review 2026-09-12; the `finally` is
     the structural form of "after the child exits, whatever happened".
  3. ORDER — the guarding `try` comes AFTER bag-open, because the harvest
     writes into that bag and would refuse the run without it (r2).
  4. THE REFS ARE THE RIGHT ONES — the call passes `ctx.pr_number` (the PR the
     run was dispatched against) and a second expression that CONSUMES the
     value the handoff assigned (the PR the child reported), pre-bound to
     `None` ABOVE the `try` so the `finally` can read it on the failure path.
     An entrypoint whose child never creates a PR passes a literal `None` and
     is DECLARED in `SINGLE_SURFACE_ENTRYPOINTS` with the reason — a second
     expression that silently duplicated the first was the earlier shape.
  5. THE INTAKES TRAIL THE PAIR — every entrypoint whose workflow RUNS THE
     REVIEWER (`review_pr.run_review`, directly or through the workflow it
     hands off to) splices the intakes that reviewer reported filing after
     the two refs, starred, reading an `issue_urls` the handoff assigned.
     THE POPULATION IS DERIVED, NOT DECLARED, AND THE DECLARATION WAS THE
     MISS: this file listed `run_review_pr.py` alone while five parents
     embed the same reviewer, so a build whose reviewer filed
     `skyynet-master-planning#32` carried the reviewer's "handed to the
     harvest" NOTE up to its banner and dropped the URL at
     `_refine_then_dispose`'s return — bag 74802cb7 holds PR #192 and no
     event for #32, and no gap, because a ref never handed over is not a
     surface the harvest failed to read. A list is a claim somebody made
     once; the derivation is re-made on every push.

⚠ WHAT THIS DOES NOT COVER, stated here AND in the failure messages:

  * A source grep proves the CALL IS WRITTEN, not that it EXECUTES or that it
    captured anything. `test_journal_harvest.py` proves the mechanism against
    a fake `gh`; `tests/integration/test_a_real_harvest.py` proves it against a
    real pull request; and the reconciliation proves, per run, that what the
    surface held at harvest time is in the bag. Four guards, four questions.
  * A run started from outside `scripts/workflows/temporal/scripts/run_*.py`
    is invisible here, exactly as it is to the bag-open sweep.
  * `--dry-run` returns before the call, deliberately — a rehearsal posts
    nothing, so there is nothing to harvest, and the ordering test below
    places the call after bag-open, which every dry run already returns
    before.
  * Whether the second ref expression is CORRECT for that entrypoint's result
    shape. The sweep can see that it consumes the handoff's target; it cannot
    know that `result.pr_url` is the field the workflow fills. The entrypoint
    tests that stub the workflow and assert on the harvest call's arguments
    own that per file.
  * A `KeyboardInterrupt` during the workflow now runs the harvest before the
    process exits — bounded (`harvest.GH_TIMEOUT_SECONDS` per request) and
    interruptible by a second interrupt. Named rather than special-cased.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from journal_entrypoint_facts import (BAG_OPEN, ENTRYPOINTS_DIR,  # noqa: E402
                                      entrypoints as _entrypoints)

HARVEST = "harvest_github_surfaces"
FIRST_REF = "ctx.pr_number"

#: Entrypoints whose child creates no pull request, so the dispatched PR is the
#: ONLY surface and the second ref is a literal `None`. Declared with the
#: reason, in the family's style, so a new entrypoint that passes `None` out of
#: laziness is a red test rather than a quiet half-harvest.
SINGLE_SURFACE_ENTRYPOINTS = {
    "run_review_pr.py":
        "a review is dispatched AGAINST a PR and posts its verdict there; the "
        "child cuts no branch and opens no PR. `ReviewResult.pr_number` is "
        "`task.pr_number` passed through — the same value as `ctx.pr_number` — "
        "and passing it as the second ref read as multi-surface support the "
        "workflow does not have. The intakes its child FILES are a different "
        "surface and trail the pair — see `runs_the_reviewer`.",
}

# The reviewer's entry function. An entrypoint that calls it, or hands off to
# a workflow module that calls it, has a child that FILES INTAKES (`FILED-
# INTAKE:` lines and the block's `filed_intakes:`, #185) — a surface beyond
# the PR pair, which its harvest call must be handed.
REVIEWER = "run_review"
# The field every result shape carries the reported intakes on:
# `ReviewResult.issue_urls`, `BuildResult.issue_urls`, the plan tuples' last
# element, the research dict's key. The trailing ref must READ it by name.
INTAKES_FIELD = "issue_urls"

MODULES_DIR = ENTRYPOINTS_DIR.parent / "modules"


def _workflow_modules(path: Path) -> set[Path]:
    """The `*_workflow` module files `path` imports, absolute or relative.

    Two spellings, because the fleet has two: an entrypoint does
    `from modules.assistant.build.build.build_workflow import run_build` or
    `from modules.assistant.research.research import research_workflow as rw`;
    a workflow does `from ...review_pr import review_pr_workflow as review_pr`.
    Both resolve to a file under `modules/`, or to nothing when the target is
    not a workflow module — a helper, an activities module — which the walk
    below does not descend into: the reviewer is reached through workflows.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[Path] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level:
            base = path.parent
            for _ in range(node.level - 1):
                base = base.parent
        elif node.module and node.module.startswith("modules."):
            base = MODULES_DIR.parent
        else:
            continue
        package = base.joinpath(*(node.module or "").split(".")) if node.module else base
        if package.name.endswith("_workflow") and package.with_suffix(".py").is_file():
            found.add(package.with_suffix(".py"))
        for alias in node.names:
            candidate = package / f"{alias.name}.py"
            if alias.name.endswith("_workflow") and candidate.is_file():
                found.add(candidate)
    return found


def calls_the_reviewer(tree: ast.AST) -> bool:
    """Does this module CALL `run_review` — `wf.run_review(...)` or bare?"""
    return any(isinstance(node, ast.Call)
               and getattr(node.func, "attr", getattr(node.func, "id", None)) == REVIEWER
               for node in ast.walk(tree))


def runs_the_reviewer(entrypoint: Path) -> bool:
    """Does this entrypoint's run include a review pass — anywhere down the handoff?

    TRANSITIVE over `*_workflow` modules, because the reviewer is one hop down
    today (`run_build.py` → `build_workflow.py` → `review_pr.run_review`) and
    a guard that stops at one hop is a guard the next refactor walks out of.
    ⚠ NOT SEEN: a reviewer reached through a module that is not named
    `*_workflow`, or invoked by a spelling that is not a call to `run_review`.
    """
    seen: set[Path] = set()
    frontier = [entrypoint]
    while frontier:
        module = frontier.pop()
        if module in seen:
            continue
        seen.add(module)
        if calls_the_reviewer(ast.parse(module.read_text(encoding="utf-8"),
                                        filename=str(module))):
            return True
        frontier.extend(_workflow_modules(module) - seen)
    return False


def reviewer_running_entrypoints() -> list[str]:
    return sorted(p.name for p in _entrypoints(ENTRYPOINTS_DIR) if runs_the_reviewer(p))


def harvest_calls(tree: ast.AST) -> list[ast.Call]:
    """Every call to the harvest activity in one module, by NAME.

    An attribute call (`harvest.harvest_github_surfaces(...)`) or a bare one;
    the alias the entrypoint bound the module to is irrelevant, which is what
    lets a future entrypoint spell its import differently and still be seen.
    """
    return [node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and getattr(node.func, "attr", getattr(node.func, "id", None)) == HARVEST]


def bag_open_lines(tree: ast.AST) -> list[int]:
    return [node.lineno for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and getattr(node.func, "attr", getattr(node.func, "id", None)) == BAG_OPEN]


def refs_argument(call: ast.Call) -> list[str] | None:
    """The `refs=(...)` keyword's elements, unparsed, or None when absent."""
    for keyword in call.keywords:
        if keyword.arg == "refs" and isinstance(keyword.value, (ast.Tuple, ast.List)):
            return [ast.unparse(e) for e in keyword.value.elts]
    return None


def guarding_try(tree: ast.AST) -> ast.Try | None:
    """The `try` whose `finally` holds the harvest call, or None.

    THE `finally` IS THE PROPERTY. A harvest that runs only when the workflow
    returns is a harvest that skips every run whose parent raised after the
    child posted — and `finally` is the one construct that runs on the return,
    the raise and the interrupt alike. The `try` body is the handoff by
    construction: whatever the parent was doing when the child could have
    written is what the `finally` covers.
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        for stmt in node.finalbody:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call) \
                    and stmt.value in harvest_calls(stmt):
                return node
    return None


def handoff_lines(try_node: ast.Try) -> set[int]:
    """The calls the `try` body makes — what the `finally` is guarding."""
    return {node.lineno for stmt in try_node.body for node in ast.walk(stmt)
            if isinstance(node, ast.Call)}


def assigned_in(stmts: list[ast.stmt]) -> set[str]:
    """Every name bound by an assignment among `stmts`, tuple targets unpacked."""
    names: set[str] = set()
    for stmt in stmts:
        if not isinstance(stmt, ast.Assign):
            continue
        for target in stmt.targets:
            elts = target.elts if isinstance(target, ast.Tuple) else [target]
            names |= {ast.unparse(e) for e in elts}
    return names


def none_bound_before(tree: ast.AST, try_node: ast.Try) -> set[str]:
    """Names bound to a literal `None` at any line above the guarding `try`.

    The `finally` reads the handoff's target on the FAILURE path too, where the
    assignment never ran; a name not pre-bound is a `NameError` raised while
    handling the workflow's exception, which would hide it.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and node.lineno < try_node.lineno \
                and isinstance(node.value, ast.Constant) and node.value.value is None:
            for target in node.targets:
                names.add(ast.unparse(target))
    return names


def base_name(expr: str) -> str:
    """`result.pr_url if result is not None else None` → `result`.

    A STARRED element unparses as `*(result.issue_urls if … else ())`; the star
    and its opening paren are stripped first so the name underneath is read.
    """
    return (expr.lstrip("*").lstrip("(")
            .split(" if ")[0].split(".")[0].split("[")[0].split("(")[0].strip())


def _sources() -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in _entrypoints(ENTRYPOINTS_DIR)}


# --- 1. presence ------------------------------------------------------------

def test_every_entrypoint_INVOKES_the_harvest() -> None:
    sources = _sources()
    assert len(sources) >= 10, (
        f"found {len(sources)} entrypoints under {ENTRYPOINTS_DIR}; a sweep "
        f"over a handful has scoped itself wrongly")
    missing = sorted(name for name, src in sources.items()
                     if not harvest_calls(ast.parse(src, filename=name)))
    assert not missing, (
        f"these entrypoints never invoke `{HARVEST}`, so the PR body, decision "
        f"log and reflection their child posts are recorded NOWHERE — the "
        f"emit rule's headline claim is false of prose for every run they "
        f"start: {missing}. Add the call in a `finally` around the workflow "
        f"handoff, passing `refs=({FIRST_REF}, <the URL the workflow returned>)`.\n"
        f"SCOPE: {ENTRYPOINTS_DIR.relative_to(Path(__file__).resolve().parents[5])}"
        f"/run_*.py and nothing else — a run started elsewhere is invisible here.")


# --- 2. every path ----------------------------------------------------------

@pytest.mark.parametrize("name", sorted(_sources()))
def test_the_harvest_runs_on_EVERY_path_out_of_the_workflow(name: str) -> None:
    """The call is in the `finally` of a `try` whose body is the handoff.

    A child that posted its PR body, its decision log and its reflection and
    then had its parent raise — a verdict that would not parse, a URL that
    could not be extracted, a worktree that would not cut — still wrote to
    GitHub, and the record of that is the one an operator opens first. Line
    order cannot see this: the first cut of this sweep passed on all sixteen
    entrypoints with the harvest on the success path alone.
    """
    tree = ast.parse(_sources()[name], filename=name)
    calls = harvest_calls(tree)
    assert calls, f"{name} has no harvest call — presence test owns this"
    guard = guarding_try(tree)
    assert guard is not None, (
        f"{name}: the harvest at line {min(c.lineno for c in calls)} is not in the "
        f"`finally` of a `try` around the workflow handoff, so a workflow that "
        f"raises AFTER its child posted never harvests, records no gap, and the "
        f"bag reads as a run that posted nothing. Wrap the handoff: "
        f"`<target> = None; try: <target> = <workflow>(...) finally: {HARVEST}(...)`.")
    assert handoff_lines(guard), (
        f"{name}: the guarded `try` body at line {guard.lineno} makes no call, so "
        f"the `finally` guards nothing — the handoff is elsewhere")
    assert len(calls) == 1, (
        f"{name}: {len(calls)} harvest calls; one run harvests once, in the finally")


# --- 3. order ---------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(_sources()))
def test_the_harvest_comes_AFTER_bag_open(name: str) -> None:
    """It writes into the bag the run opened; before bag-open it refuses (r2)."""
    tree = ast.parse(_sources()[name], filename=name)
    guard = guarding_try(tree)
    assert guard is not None, f"{name}: every-path test owns this"
    opens = bag_open_lines(tree)
    assert opens and min(opens) < guard.lineno, (
        f"{name}: the guarded handoff at line {guard.lineno} precedes bag-open "
        f"({opens}); the harvest would find no bag and refuse the run (r2)")


# --- 4. the refs ------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(_sources()))
def test_the_harvest_is_handed_BOTH_the_dispatched_PR_and_the_reported_one(
        name: str) -> None:
    """`refs=(ctx.pr_number, <what the handoff assigned>)` — two, not one.

    A `--pr` correction pass posts to the PR it was dispatched against; a fresh
    pass posts to the PR its child created. One expression covers one of the
    two, and a run that harvested only `ctx.pr_number` would record nothing for
    every first pass in the fleet. The second expression must CONSUME the
    handoff's own target — the sweep cannot know the field is right, but it
    can know the value came from the workflow and not from thin air — and that
    target must be bound to `None` above the `try`, or the `finally` raises
    `NameError` on exactly the failure path it exists for.
    """
    tree = ast.parse(_sources()[name], filename=name)
    guard = guarding_try(tree)
    assert guard is not None, f"{name}: every-path test owns this"
    refs = refs_argument(harvest_calls(tree)[0])
    assert refs is not None, (
        f"{name}: the harvest call passes no literal `refs=(...)` tuple; the "
        f"sweep cannot see which surfaces it will read")
    assert refs[0] == FIRST_REF, (
        f"{name}: the first ref is {refs[0]!r}, not `{FIRST_REF}` — the PR the "
        f"run was dispatched against would not be harvested on a `--pr` pass")
    assert len(refs) >= 2, (
        f"{name}: the harvest is handed only the dispatched PR ({refs}); the "
        f"PR the child CREATED on a first pass would never be harvested")
    second = refs[1]
    if name in SINGLE_SURFACE_ENTRYPOINTS:
        assert second == "None", (
            f"{name} is declared single-surface ({SINGLE_SURFACE_ENTRYPOINTS[name]!r}) "
            f"but passes {second!r} as a second ref — either the declaration is "
            f"stale or the ref is a duplicate of the first dressed as a second")
        return
    assert second != FIRST_REF and second != "None", (
        f"{name}: the second ref is {second!r} — the PR the child CREATED is "
        f"never harvested. If this entrypoint's child truly creates no PR, "
        f"declare it in SINGLE_SURFACE_ENTRYPOINTS with the reason.")
    target = base_name(second)
    assert target in assigned_in(guard.body), (
        f"{name}: the second ref {second!r} does not consume anything the guarded "
        f"handoff assigns ({sorted(assigned_in(guard.body))}); the value the "
        f"harvest reads did not come from the workflow")
    assert target in none_bound_before(tree, guard), (
        f"{name}: `{target}` is not bound to None above the `try` at line "
        f"{guard.lineno}; on the failure path the `finally` would raise NameError "
        f"while handling the workflow's exception and hide it")


@pytest.mark.parametrize("name", reviewer_running_entrypoints())
def test_an_entrypoint_whose_run_FILES_INTAKES_hands_them_to_the_harvest(name: str) -> None:
    """`refs=(ctx.pr_number, <pair>, *(<target>.issue_urls if <target> is not None else ()))`.

    THREE PROPERTIES, EACH WITH A FAILURE THE OTHERS CANNOT SEE. The trailing
    ref must exist at all — the two-ref test above returns satisfied on the
    pair and would keep passing if the intakes were dropped, WHICH IS WHAT
    HAPPENED on the five parents that embed the reviewer. It must be STARRED:
    an unstarred `result.issue_urls` is one ref holding a list, which
    `parse_ref` turns into `str(list)` and REFUSES, and the refusal lands in
    the `finally` of every run that filed anything. And it must consume the
    handoff's own None-bound target, for the reason the two-ref test gives —
    on the failure path an unbound name is a NameError raised while the
    workflow's exception is in flight.
    """
    tree = ast.parse(_sources()[name], filename=name)
    guard = guarding_try(tree)
    assert guard is not None, f"{name}: every-path test owns this"
    refs = refs_argument(harvest_calls(tree)[0])
    assert refs is not None and len(refs) >= 3, (
        f"{name}: its run includes a review pass, and the harvest is handed "
        f"{refs} — no trailing ref, so every intake that reviewer files is "
        f"harvested NOWHERE and no gap records it. Splice "
        f"`*(<handoff target>.{INTAKES_FIELD} if <target> is not None else ())` "
        f"after the pair, and carry `{INTAKES_FIELD}` out of the workflow beside "
        f"its notes.")
    for expr in refs[2:]:
        assert expr.startswith("*"), (
            f"{name}: trailing ref {expr!r} is not starred; a sequence passed as "
            f"one ref is `str(list)` to `parse_ref`, which refuses it")
        assert INTAKES_FIELD in expr, (
            f"{name}: trailing ref {expr!r} does not read `{INTAKES_FIELD}` — the "
            f"field every result shape carries the filed intakes on")
        target = base_name(expr)
        assert target in assigned_in(guard.body), (
            f"{name}: trailing ref {expr!r} reads `{target}`, which the guarded "
            f"handoff does not assign ({sorted(assigned_in(guard.body))}); the "
            f"value the harvest reads did not come from the workflow")
        assert target in none_bound_before(tree, guard), (
            f"{name}: `{target}` is not bound to None above the `try` at line "
            f"{guard.lineno}; the `finally` would raise NameError on the failure path")


def test_the_reviewer_running_population_is_DERIVED_and_not_a_handful() -> None:
    """The vacuity guard on the derivation — and the record of the miss.

    The standalone reviewer is in it by construction (it calls `run_review`
    itself); the draft children are out by construction (a draft posts a PR
    and disposes nothing). And it is LARGER THAN ONE: one was the size of the
    declared list this replaced, and one is the number of parents that hand
    their intakes over when six run a reviewer.
    """
    population = reviewer_running_entrypoints()
    assert "run_review_pr.py" in population, population
    assert "run_build_draft.py" not in population, population
    assert len(population) >= 6, (
        f"the derivation found {population}; six entrypoints ran a reviewer "
        f"when this was written, and a shrink is a walk that stopped seeing")


def test_every_declared_single_surface_entrypoint_EXISTS() -> None:
    """A declaration for a file that is gone is a reason nobody reads."""
    stale = sorted(set(SINGLE_SURFACE_ENTRYPOINTS) - set(_sources()))
    assert not stale, (
        f"SINGLE_SURFACE_ENTRYPOINTS names entrypoints that do not exist: {stale}")


# --- the control: the predicate against literal source --------------------------

_COMPLIANT = '''
def main():
    ctx = build()
    journal.open_run_bag(run_id=ctx.run_id)
    pr_url = None
    try:
        pr_url = run_thing(task)
    finally:
        harvest.harvest_github_surfaces(run_id=ctx.run_id, repo_root=repo_root,
                                        refs=(ctx.pr_number, pr_url),
                                        journal_root=ctx.journal_root)
'''

# THE SHAPE THE FIRST CUT OF THIS SWEEP ACCEPTED: line order right, no `finally`.
_SUCCESS_PATH_ONLY = '''
def main():
    ctx = build()
    journal.open_run_bag(run_id=ctx.run_id)
    pr_url = run_thing(task)
    harvest.harvest_github_surfaces(run_id=ctx.run_id, repo_root=repo_root,
                                    refs=(ctx.pr_number, pr_url),
                                    journal_root=ctx.journal_root)
'''

_UNBOUND_ON_FAILURE = '''
def main():
    ctx = build()
    journal.open_run_bag(run_id=ctx.run_id)
    try:
        pr_url = run_thing(task)
    finally:
        harvest.harvest_github_surfaces(run_id=ctx.run_id, repo_root=repo_root,
                                        refs=(ctx.pr_number, pr_url),
                                        journal_root=ctx.journal_root)
'''

_ONE_REF = '''
def main():
    ctx = build()
    journal.open_run_bag(run_id=ctx.run_id)
    pr_url = None
    try:
        pr_url = run_thing(task)
    finally:
        harvest.harvest_github_surfaces(run_id=ctx.run_id, repo_root=repo_root,
                                        refs=(ctx.pr_number,),
                                        journal_root=ctx.journal_root)
'''


# The reviewer's shape: the PR pair, then the intakes its child filed, starred.
_TRAILING_STARRED = '''
def main():
    ctx = build()
    journal.open_run_bag(run_id=ctx.run_id)
    result = None
    try:
        result = run_thing(task)
    finally:
        harvest.harvest_github_surfaces(run_id=ctx.run_id, repo_root=repo_root,
                                        refs=(ctx.pr_number, None,
                                              *(result.issue_urls if result is not None else ())),
                                        journal_root=ctx.journal_root)
'''


def test_the_predicates_DISCRIMINATE_on_literal_source() -> None:
    """The control `test_a_census_guard_proves_its_own_predicate` requires.

    Each helper above is driven on a snippet that satisfies the property and
    one that violates it, so an AST-shape change that made a helper answer
    unconditionally would go red here rather than leaving the sweep green over
    a fleet it had stopped examining.
    """
    good = ast.parse(_COMPLIANT)
    assert len(harvest_calls(good)) == 1
    assert bag_open_lines(good) == [4]
    assert refs_argument(harvest_calls(good)[0]) == ["ctx.pr_number", "pr_url"]
    guard = guarding_try(good)
    assert guard is not None and guard.lineno == 6
    assert handoff_lines(guard) == {7}
    assert assigned_in(guard.body) == {"pr_url"}
    assert none_bound_before(good, guard) == {"pr_url"}
    assert min(bag_open_lines(good)) < guard.lineno

    assert harvest_calls(ast.parse("def main():\n    return 1\n")) == []

    # Line order right, no `finally`: no guard is located, which is what the
    # every-path test fails on.
    assert guarding_try(ast.parse(_SUCCESS_PATH_ONLY)) is None

    # A `finally` whose target was never pre-bound raises NameError on the
    # failure path; the helper must report the name as unbound.
    unbound = ast.parse(_UNBOUND_ON_FAILURE)
    assert none_bound_before(unbound, guarding_try(unbound)) == set()

    assert refs_argument(harvest_calls(ast.parse(_ONE_REF))[0]) == ["ctx.pr_number"]

    assert base_name("result.pr_url if result is not None else None") == "result"
    assert base_name('result.get("pr_url") if result is not None else None') == "result"
    assert base_name("pr_url") == "pr_url"

    # The starred trailing ref unparses with `*(` in front of the name; the
    # helper reads through it, and the ref list shows the star so the
    # intakes test can hold it.
    starred = refs_argument(harvest_calls(ast.parse(_TRAILING_STARRED))[0])
    assert starred == ["ctx.pr_number", "None",
                       "*(result.issue_urls if result is not None else ())"]
    assert base_name(starred[2]) == "result"

    # The reviewer predicate reads CALLS, attribute or bare, and not the name
    # in any other position — a module that merely imports or defines
    # `run_review` does not run one.
    assert calls_the_reviewer(ast.parse("v = review_pr.run_review(x)"))
    assert calls_the_reviewer(ast.parse("v = run_review(x)"))
    assert not calls_the_reviewer(ast.parse("def run_review(x):\n    return x\n"))
    assert not calls_the_reviewer(ast.parse("from a import run_review\n"))


def test_the_reviewer_walk_RESOLVES_both_import_spellings(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An absolute `modules.…` import in an entrypoint, a relative one in a
    workflow, and a reviewer two hops down — the walk reaches it; a sibling
    tree whose workflow never calls the reviewer is not reached into."""
    modules = tmp_path / "modules" / "assistant"
    (modules / "outer").mkdir(parents=True)
    (modules / "inner").mkdir()
    (modules / "review_pr").mkdir()
    (modules / "review_pr" / "review_pr_workflow.py").write_text(
        "def run_review(task):\n    return task\n", encoding="utf-8")
    (modules / "inner" / "inner_workflow.py").write_text(
        "from ..review_pr import review_pr_workflow as review_pr\n"
        "def run_inner():\n    return review_pr.run_review(1)\n", encoding="utf-8")
    (modules / "outer" / "outer_workflow.py").write_text(
        "from ..inner import inner_workflow as inner\n"
        "def run_outer():\n    return inner.run_inner()\n", encoding="utf-8")
    (modules / "outer" / "quiet_workflow.py").write_text(
        "def run_quiet():\n    return 1\n", encoding="utf-8")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "run_outer.py").write_text(
        "from modules.assistant.outer.outer_workflow import run_outer\n"
        "run_outer()\n", encoding="utf-8")
    (scripts / "run_quiet.py").write_text(
        "from modules.assistant.outer import quiet_workflow as qw\n"
        "qw.run_quiet()\n", encoding="utf-8")
    monkeypatch.setitem(globals(), "MODULES_DIR", tmp_path / "modules")
    assert runs_the_reviewer(scripts / "run_outer.py")
    assert not runs_the_reviewer(scripts / "run_quiet.py")

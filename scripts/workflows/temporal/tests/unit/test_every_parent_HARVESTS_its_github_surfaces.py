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
        "child cuts no branch and opens nothing. `ReviewResult.pr_number` is "
        "`task.pr_number` passed through — the same value as `ctx.pr_number` — "
        "and passing it as the second ref read as multi-surface support the "
        "workflow does not have.",
}


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
    """`result.pr_url if result is not None else None` → `result`."""
    return expr.split(" if ")[0].split(".")[0].split("[")[0].split("(")[0].strip()


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

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
posted to one — `grep -l "pr_url\\|url\\|pr_number" scripts/run_*.py` matches
all of them, and Phase 3's inventory has no workflow that writes only to a
file store. So the swept population IS the posting population, and a future
entrypoint that posts nowhere is a classification this sweep would force
someone to state rather than assume — the same discipline `NON_STARTING_FILES`
applies one level up.

THE THREE PROPERTIES, EACH ITS OWN TEST:

  1. PRESENCE — every entrypoint calls `harvest_github_surfaces`.
  2. ORDER — the call comes AFTER the workflow handoff, because it reads the
     PR the child made, and AFTER bag-open, because it writes into that bag.
  3. THE REFS ARE THE RIGHT ONES — the call passes `ctx.pr_number` (the PR the
     run was dispatched against) and a second expression (the PR the child
     reported). A harvest of only one of the two misses the other.

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
    shape. The sweep can see that a second expression exists; it cannot know
    that `result.pr_url` is the field the workflow fills. The entrypoint tests
    that stub the workflow and assert on the harvest call's arguments own that
    per file.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from journal_entrypoint_facts import (BAG_OPEN, ENTRYPOINTS_DIR,  # noqa: E402
                                      entrypoints as _entrypoints,
                                      side_effect_lines as _side_effect_lines)

HARVEST = "harvest_github_surfaces"
FIRST_REF = "ctx.pr_number"


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


def handoff_lines(tree: ast.AST, refs: list[str]) -> set[int]:
    """Where the workflow was handed off to — the lines the harvest must follow.

    Two recognisers. `side_effect_lines` sees a by-name `*_workflow` call and
    `act.worktree_add`; this adds *the assignment whose target the harvest's
    own `refs` then consumes* — `pr_url = run_draft(...)` followed by
    `refs=(ctx.pr_number, pr_url)` — which is what reaches the aliased-module
    handoffs (`rw.run_research`, `wf.run_review`) the first cannot see.
    """
    lines = set(_side_effect_lines(tree))
    consumed = {r.split(".")[0].split("[")[0] for r in refs} - {"ctx"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            targets = {ast.unparse(t) for t in node.targets}
            targets |= {ast.unparse(e) for t in node.targets
                        if isinstance(t, ast.Tuple) for e in t.elts}
            if targets & consumed:
                lines.add(node.lineno)
    return lines


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
        f"start: {missing}. Add the call after the workflow returns, passing "
        f"`refs=({FIRST_REF}, <the URL the workflow returned>)`.\n"
        f"SCOPE: {ENTRYPOINTS_DIR.relative_to(Path(__file__).resolve().parents[5])}"
        f"/run_*.py and nothing else — a run started elsewhere is invisible here.")


# --- 2. order ---------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(_sources()))
def test_the_harvest_comes_AFTER_the_workflow_and_AFTER_bag_open(name: str) -> None:
    """It reads the PR the child made and writes into the bag the run opened.

    THE WORKFLOW HANDOFF IS FOUND TWO WAYS, and the second is the one
    `journal_entrypoint_facts.side_effect_lines` cannot see. That helper
    recognises a by-name call to a `*_workflow` import and `act.worktree_add`;
    the two entrypoints it names as `ORDERING_UNCOVERED` reach their workflow
    through an aliased module (`rw.run_research`, `wf.run_review`). Here the
    handoff is ALSO recognised as *the assignment whose value is a call and
    whose target the harvest's `refs` then names* — `pr_url = run_draft(...)`
    followed by `refs=(ctx.pr_number, pr_url)`. That closes the two, because
    the harvest call itself says which value it consumes.
    """
    src = _sources()[name]
    tree = ast.parse(src, filename=name)
    calls = harvest_calls(tree)
    assert calls, f"{name} has no harvest call — presence test owns this"
    harvest_line = min(c.lineno for c in calls)

    opens = bag_open_lines(tree)
    assert opens and min(opens) < harvest_line, (
        f"{name}: the harvest at line {harvest_line} precedes bag-open "
        f"({opens}); it would find no bag and refuse the run (r2)")

    refs = refs_argument(calls[0]) or []
    handoffs = handoff_lines(tree, refs)
    assert handoffs, (
        f"{name}: no workflow handoff could be located, so the order claim "
        f"below would be vacuous — the harvest's refs are {refs}")
    assert max(handoffs) < harvest_line, (
        f"{name}: the harvest at line {harvest_line} runs BEFORE the workflow "
        f"handoff at {sorted(handoffs)} — it would harvest a PR that does not "
        f"exist yet, record a gap, and miss everything the child then posts")


# --- 3. the refs ------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(_sources()))
def test_the_harvest_is_handed_BOTH_the_dispatched_PR_and_the_reported_one(
        name: str) -> None:
    """`refs=(ctx.pr_number, <what the workflow returned>)` — two, not one.

    A `--pr` correction pass posts to the PR it was dispatched against; a fresh
    pass posts to the PR its child created. One expression covers one of the
    two, and a run that harvested only `ctx.pr_number` would record nothing for
    every first pass in the fleet.
    """
    tree = ast.parse(_sources()[name], filename=name)
    refs = refs_argument(harvest_calls(tree)[0])
    assert refs is not None, (
        f"{name}: the harvest call passes no literal `refs=(...)` tuple; the "
        f"sweep cannot see which surfaces it will read")
    assert refs[0] == FIRST_REF, (
        f"{name}: the first ref is {refs[0]!r}, not `{FIRST_REF}` — the PR the "
        f"run was dispatched against would not be harvested on a `--pr` pass")
    assert len(refs) >= 2 and refs[1] != FIRST_REF, (
        f"{name}: the harvest is handed only the dispatched PR ({refs}); the "
        f"PR the child CREATED on a first pass would never be harvested")


# --- the control: the predicate against literal source --------------------------

_COMPLIANT = '''
def main():
    ctx = build()
    journal.open_run_bag(run_id=ctx.run_id)
    pr_url = run_thing(task)
    harvest.harvest_github_surfaces(run_id=ctx.run_id, repo_root=repo_root,
                                    refs=(ctx.pr_number, pr_url),
                                    journal_root=ctx.journal_root)
'''

_INVERTED = '''
def main():
    ctx = build()
    journal.open_run_bag(run_id=ctx.run_id)
    harvest.harvest_github_surfaces(run_id=ctx.run_id, repo_root=repo_root,
                                    refs=(ctx.pr_number, pr_url),
                                    journal_root=ctx.journal_root)
    pr_url = run_thing(task)
'''

_ONE_REF = '''
def main():
    ctx = build()
    journal.open_run_bag(run_id=ctx.run_id)
    pr_url = run_thing(task)
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

    assert harvest_calls(ast.parse("def main():\n    return 1\n")) == []

    assert handoff_lines(good, ["ctx.pr_number", "pr_url"]) == {5}
    assert max(handoff_lines(good, ["ctx.pr_number", "pr_url"])) < \
        harvest_calls(good)[0].lineno

    inverted = ast.parse(_INVERTED)
    assert handoff_lines(inverted, ["ctx.pr_number", "pr_url"]) == {8}
    assert max(handoff_lines(inverted, ["ctx.pr_number", "pr_url"])) > \
        harvest_calls(inverted)[0].lineno, "the inverted snippet must invert"
    # A refs tuple naming NOTHING the module assigns locates no handoff — the
    # vacuity the order test asserts against rather than passing over.
    assert handoff_lines(good, ["ctx.pr_number"]) == set()

    assert refs_argument(harvest_calls(ast.parse(_ONE_REF))[0]) == ["ctx.pr_number"]

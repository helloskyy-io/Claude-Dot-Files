"""A read that gates a run must happen BEFORE the worktree is cut, not after.

THE FAILURE THIS HOLDS. `act.worktree_add` registers a worktree with git and
completes a `git fetch`. Anything after it that can raise leaves both behind —
the stranded worktree `preflight.py`'s own header says the dispatch boundary
exists to prevent. Two instances shipped, one call apart in the same function:

  * `task_text(task, repo_root)` was evaluated inside the `run_draft(...)`
    argument list, so a `--task-file` naming no file raised AFTER the cut. A
    typo cost a registered worktree.
  * `act.repo_slug(repo_root)` — a `gh` round trip, network AND auth, the most
    failure-prone call in the sequence — sat immediately below the cut in five
    functions. It depends on nothing the worktree provides.

THE SECOND SURVIVED THE FIX FOR THE FIRST, WHICH IS THE WHOLE ARGUMENT FOR THIS
FILE. One pass hoisted `task_text` above the cut in four runners, wrote the
reasoning into a comment, and left `repo_slug` three lines below it. A review
found three of the five surviving sites by reading; a sweep found five. Nobody
was careless — the fix was applied to the instances that had been named, which
is what happens whenever the check is a person rather than a predicate.

WHAT THE POPULATION IS. Every function anywhere in this fleet that calls
`worktree_add`, derived from the tree. There were 17 when this was written and
the floor below says so.

WHAT `_READS_THAT_MUST_PRECEDE_THE_CUT` IS, and why it is written by hand. It
names the reads that GATE the run: they can raise, they decide whether the run
should proceed at all, and none of them takes the worktree as an argument. That
last property is what makes hoisting free, and it cannot be derived from a call
site — `act.commit_all(worktree, ...)` also raises and plainly must not move.
The list is short, closed by inspection of the activity surface, and held in
BOTH directions: `test_no_name_in_the_list_is_GONE` fails if an entry stops
being called anywhere, which is the dead-key defect this suite has now measured
three times in three different registries.

WHAT THIS DOES NOT LOOK AT:

  * **A read spelled some other way.** `subprocess.run(["gh", ...])` inline
    after a cut is the same defect and is invisible here. The fleet routes every
    `gh` call through `assistant_activities` (`test_every_gh_the_fleet_launches_
    is_ANCHORED` owns that), which is what makes a name list sufficient today.
  * **Whether the hoisted call is CORRECT.** This is an ordering property. That
    `repo_slug` returns the right slug is somebody else's assertion.
  * **Calls after the CHILD.** A `gh` failure there costs a worktree too, but the
    run has already spent the model time, so the trade is different and the
    remedy is disposal rather than ordering. Out of scope, deliberately.
  * **A nested function's body.** `_calls_in_own_scope` stops at a nested `def`
    or `lambda`, because a closure's calls do not execute where they are written
    and reporting them at that position would be a false positive. A gating read
    inside a closure that the enclosing function calls after cutting is
    therefore invisible. Nothing in the population does this today.
"""

from __future__ import annotations

import ast
from pathlib import Path

TEMPORAL = Path(__file__).resolve().parents[2]

#: Where a cut can happen: the entrypoints and the workflow modules.
_SOURCES = sorted(set(TEMPORAL.glob("scripts/*.py"))
                  | set((TEMPORAL / "modules").rglob("*.py")))

#: Reads that GATE the run and take no worktree. See the docstring: hand-written
#: because "does this depend on the worktree" is a property of the callee, and
#: held in both directions by the staleness check below.
_READS_THAT_MUST_PRECEDE_THE_CUT = frozenset({
    "repo_slug",   # a `gh` round trip: network and auth
    "task_text",   # resolves `--task-file`/`--phase`, raises on a bad path
    "base_ref",    # resolves the base a `--pr` run starts from
})


def _called_name(node: ast.Call) -> str | None:
    return getattr(node.func, "attr", None) or getattr(node.func, "id", None)


_NESTED = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)


def _calls_in_own_scope(function: ast.AST) -> list[ast.Call]:
    """Every call in one function's OWN body, not in a function nested inside it.

    ORDERING IS A PROPERTY OF ONE SEQUENCE OF STATEMENTS. A nested function's
    body does not run where it is written — it runs when it is called, which may
    be before the cut, after it, or never. `ast.walk` recurses into nested
    definitions, so a gating read inside a closure would be attributed to the
    enclosing function's ordering and reported at a position it never executes
    at. Nothing in the current population nests one; scoped rather than disclosed
    because a false report from a guard is what gets the guard deleted.
    """
    calls: list[ast.Call] = []
    stack = list(ast.iter_child_nodes(function))
    while stack:
        node = stack.pop()
        if isinstance(node, _NESTED):
            continue
        if isinstance(node, ast.Call):
            calls.append(node)
        stack += list(ast.iter_child_nodes(node))
    return calls


def _gating_reads_after_the_cut(tree: ast.AST) -> list[tuple[str, int, str]]:
    """THE PREDICATE. `(function, lineno, name)` for every gating read below a cut.

    A module-level function taking an already-parsed tree, so the control below
    drives THIS code against a literal snippet rather than re-implementing it —
    a control that re-implements its predicate stops describing it the moment
    either moves, which this suite has measured twice.
    """
    found: list[tuple[str, int, str]] = []
    for function in ast.walk(tree):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        calls = _calls_in_own_scope(function)
        cuts = [node.lineno for node in calls if _called_name(node) == "worktree_add"]
        if not cuts:
            continue
        cut = min(cuts)
        found += [(function.name, node.lineno, _called_name(node))
                  for node in calls
                  if node.lineno > cut
                  and _called_name(node) in _READS_THAT_MUST_PRECEDE_THE_CUT]
    return found


def _functions_that_cut() -> list[str]:
    cutting = []
    for path in _SOURCES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if any(_called_name(node) == "worktree_add"
                   for node in _calls_in_own_scope(function)):
                cutting.append(f"{path.name}::{function.name}")
    return sorted(cutting)


def test_no_GATING_READ_happens_after_the_worktree_is_cut() -> None:
    """THE REQUIREMENT. Everything that can refuse the run runs before the cut."""
    offenders: list[str] = []
    for path in _SOURCES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        offenders += [f"{path.name}:{lineno} {name}() in {function}()"
                      for function, lineno, name in _gating_reads_after_the_cut(tree)]

    assert not offenders, (
        "a read that GATES the run happens after `worktree_add`, so a failure "
        "there strands a registered worktree and a completed fetch: "
        + "; ".join(sorted(offenders))
        + ". Hoist it above the `base_ref`/`worktree_add` pair — none of these "
          "takes the worktree, so nothing is lost by reading them earlier, and "
          "the run still refuses before it has created anything.")


def test_the_sweep_found_the_functions_that_CUT() -> None:
    """VACUITY FLOOR. Every assertion above is over a list that is empty when the
    walk stops walking, and a green sweep over nothing is the class this suite
    keeps catching in itself.
    """
    cutting = _functions_that_cut()
    # 17 functions called `worktree_add` when this floor was set — 11 runners,
    # 5 workflow parents and `review_pr_workflow.run_review`. The floor sits
    # below the measurement because the count moves whenever a workflow is added.
    assert len(cutting) >= 12, (
        f"only {len(cutting)} functions cut a worktree; there were 17 when this "
        f"floor was set: {cutting}. A walk that has stopped walking passes "
        f"vacuously.")


def test_no_name_in_the_list_is_GONE() -> None:
    """THE OTHER DIRECTION, and it is the one that fails silently.

    A name that is no longer called anywhere contributes no coverage while
    reading exactly like coverage — the dead-registry-row defect this suite has
    now measured in `_ARGV_SHAPE`, in the prose-figure registry, and here in
    advance. An entry survives a rename only by being renamed with it.
    """
    called = {name for path in _SOURCES
              for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
              if isinstance(node, ast.Call) and (name := _called_name(node))}
    orphaned = sorted(_READS_THAT_MUST_PRECEDE_THE_CUT - called)
    assert not orphaned, (
        f"{orphaned} are listed as gating reads but nothing in the fleet calls "
        f"them. A renamed or deleted activity leaves its entry behind, and an "
        f"entry matching no call site protects nothing.")


def test_THE_PREDICATE_CATCHES_THE_SHAPE_THAT_SHIPPED() -> None:
    """NEGATIVE CONTROL, on literal snippets — the arrangement that shipped, the
    arrangement that replaced it, and the two shapes that must NOT fire.
    """
    shipped = (
        "def run_build(task, repo_root, worktree_name):\n"
        "    ref = act.base_ref(task.pr_number, repo_root)\n"
        "    worktree = act.worktree_add(repo_root, worktree_name, ref)\n"
        "    slug = act.repo_slug(repo_root)\n"
        "    return run_draft(worktree=worktree, prefer_repo=slug)\n")
    assert [name for _fn, _ln, name in _gating_reads_after_the_cut(ast.parse(shipped))] \
        == ["repo_slug"], "the predicate must flag the arrangement that shipped"

    fixed = (
        "def run_build(task, repo_root, worktree_name):\n"
        "    slug = act.repo_slug(repo_root)\n"
        "    ref = act.base_ref(task.pr_number, repo_root)\n"
        "    worktree = act.worktree_add(repo_root, worktree_name, ref)\n"
        "    return run_draft(worktree=worktree, prefer_repo=slug)\n")
    assert _gating_reads_after_the_cut(ast.parse(fixed)) == [], (
        "the corrected arrangement must not fire — a guard that flags its own "
        "fix leaves no conforming way to write the function")

    # A function that never cuts is not in the population, however it reads.
    never_cuts = "def f(repo_root):\n    return act.repo_slug(repo_root)\n"
    assert _gating_reads_after_the_cut(ast.parse(never_cuts)) == []

    # A NESTED FUNCTION IS ITS OWN SCOPE. `ast.walk` would attribute the inner
    # `repo_slug` to the outer function's ordering and report a position it
    # never executes at — a false positive, which is how a guard gets deleted.
    nested = (
        "def outer(repo_root, name, ref):\n"
        "    worktree = act.worktree_add(repo_root, name, ref)\n"
        "    def later():\n"
        "        return act.repo_slug(repo_root)\n"
        "    return later\n")
    assert _gating_reads_after_the_cut(ast.parse(nested)) == [], (
        "a call inside a nested definition must not be attributed to the "
        "enclosing function's ordering")
    # …and the inner function is judged on its OWN body, which does not cut.
    assert [fn for fn, _ln, _n in _gating_reads_after_the_cut(ast.parse(nested))] == []

    # A call that legitimately NEEDS the worktree must not be flagged. This is
    # why the list is names and not "anything that can raise".
    needs_it = (
        "def f(repo_root, name, ref):\n"
        "    worktree = act.worktree_add(repo_root, name, ref)\n"
        "    return act.commit_all(worktree, 'msg')\n")
    assert _gating_reads_after_the_cut(ast.parse(needs_it)) == []

"""A worktree name is RECEIVED, never assembled where the worktree is cut.

THE DEFECT, MEASURED 2026-08-28 AND RE-MEASURED 2026-09-01. Eleven sites built a
per-run worktree name for themselves, in THREE spellings:

  * eight runners        `f"<key>-{int(time.time())}"`
  * two build runners    `f"build-{int(__import__('time').time())}"`
  * one workflow module  `f"review-pr-{pr}-{int(time.time())}"`, INLINE, with no
                         assignment for a guard to key on

and `run_build_minor` had already DRIFTED — `workflow_key="build-minor"` beside a
worktree named `build-…`, so its trees were indistinguishable on disk from the
`build` parent's. `review-pr` cost more than duplication: `run_review_pr.py`
recorded `worktree_name=None` in the run bag, commenting *"the ONE workflow that
cuts no worktree"*, while `review_pr_workflow` cut one on the very next call.

WHY THIS KEYS ON THE CALL SITE AND NOT ON THE NAME'S SPELLING. `assistant_
activities.base_ref` is the same consolidation, done once already, and its
docstring records the outcome: the first guard written to replace the hand sweep
keyed on `ref = ...`, which is how ten of eleven sites happened to be written,
and the eleventh passed its value INLINE and walked straight past. The same
shape is here — `grep -n "int(time.time())"` returned nine of these eleven and
missed the two `__import__('time')` ones outright, because that string does not
occur in them. A check keyed on today's three spellings passes a twelfth site
written in a fourth. `worktree_add`'s CALL SITES are a population a parser can
enumerate, and a new caller cannot avoid calling it.

⚠ MATCH ON THE FUNCTION NAME, NEVER ON THE MODULE ALIAS. `review_pr_workflow`
reaches it as `_shared.worktree_add` while everything else says `act.`
`test_isolation_invariants._classify` keys on the literal `"act.worktree_add("`
and is BLIND to that file today — it classifies `review_pr_workflow` as a child
while the module cuts a worktree. That is the one site this guard most needs to
see, so it reads the callee's NAME off the AST and ignores what it arrived as.

WHAT THIS DOES NOT LOOK AT, said plainly so nobody over-reads it:

  * IT HOLDS ONE VALUE AT ONE CALL-SITE SHAPE. "A run-scoped derived value is a
    field on the run context" stays a judgement in general; this makes it
    checkable for the value that was measurably scattered. A SECOND value that
    scatters later needs its own call-site check — the rule is enforced per
    value, not as a class.
  * IT DOES NOT CHECK THAT THE NAME IS RIGHT, only that it was received. A
    context whose `worktree_name` field computed nonsense passes here and fails
    in `test_dispatch_context.py`.
  * IT CANNOT SEE A NAME THREADED THROUGH A DATA STRUCTURE — a dict, a dataclass
    field assigned three functions away. That is invisible to any source-level
    check, as it is to the head-base guard beside this one.
  * IT SAYS NOTHING ABOUT `worktree_add`'s FETCH BEHAVIOUR or about where the
    worktree is cut FROM. Those are `test_a_new_branch_STARTS_FROM_THE_DEFAULT_
    BRANCH.py`'s, and they are a different guarantee.
"""

from __future__ import annotations

import ast
from pathlib import Path

FLEET = Path(__file__).resolve().parents[2]
SEARCH = [FLEET / "scripts", FLEET / "modules"]

#: The name the run context carries the value under. A call site must reference
#: it — as `<anything>.worktree_name`, or as a PARAMETER of the enclosing
#: function called `worktree_name`. Keying on the receiving side rather than on
#: the offending side is deliberate: the receiving side is what we author, and a
#: twelfth site that invents a different spelling fails LOUD here rather than
#: sliding past, which is the safe direction for a false positive to point.
FIELD = "worktree_name"


def _fleet_sources() -> list[Path]:
    found = [p for root in SEARCH for p in root.rglob("*.py")
             if "tests" not in p.parts]
    assert len(found) > 20, (
        f"only {len(found)} fleet modules found under {SEARCH} — the walk is "
        f"wrong, and every assertion below would pass vacuously")
    return found


def _params(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    a = fn.args
    names = {arg.arg for arg in (*a.posonlyargs, *a.args, *a.kwonlyargs)}
    for extra in (a.vararg, a.kwarg):
        if extra is not None:
            names.add(extra.arg)
    return names


def _name_argument(call: ast.Call) -> ast.expr | None:
    """`worktree_add(repo_root, NAME, ref)` — positional 1, or the `name=` kwarg."""
    if len(call.args) > 1:
        return call.args[1]
    return next((k.value for k in call.keywords if k.arg == "name"), None)


def _assembled_names(tree: ast.Module) -> list[tuple[int, str]]:
    """Every `worktree_add` call whose name argument was NOT received.

    TAKES A PARSED TREE so a control can drive the predicate on a literal — the
    convention `_bases_in_tree` uses one file over, and it is load-bearing: the
    census guard recognises a tree-walker by an `ast.parse` of a file read and a
    CONTROL by an `ast.parse` of anything else, so splitting on the source
    string would drop this module out of that population instead of adding a
    control to it.

    RECEIVED MEANS ONE OF TWO THINGS, and the second is not a weakening. Either
    the argument reaches an attribute called `worktree_name` — `ctx.worktree_name`
    — or it references a PARAMETER of the enclosing function of that name. The
    second admits `f"{worktree_name}-review-{this_pass}"`, which is
    `review_pr_workflow` deriving a PER-PASS tree from the run's own name: the
    tree it cuts is not run-scoped (a loop-back cuts one per pass) so it cannot
    BE a frozen field, but its stem is received rather than invented. What the
    rule refuses is an argument built only out of values the enclosing function
    was never handed — every one of the eleven sites, in all three spellings.

    ⚠ A LOCAL ASSIGNMENT IS NOT A PARAMETER, and that distinction is the whole
    guard. `worktree_name = f"plan-{int(time.time())}"` followed by
    `worktree_add(repo_root, worktree_name, ref)` is exactly what eight runners
    did, and reading only the argument's spelling would call it received.
    """
    hits: list[tuple[int, str]] = []

    def walk(node: ast.AST, received: frozenset[str]) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            received = received | _params(node)
        if isinstance(node, ast.Call):
            fn = node.func
            callee = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if callee == "worktree_add":
                arg = _name_argument(node)
                if arg is None:
                    hits.append((node.lineno, "worktree_add(...) with no name argument"))
                else:
                    inner = list(ast.walk(arg))
                    by_attribute = any(isinstance(n, ast.Attribute) and n.attr == FIELD
                                       for n in inner)
                    by_parameter = FIELD in received and any(
                        isinstance(n, ast.Name) and n.id == FIELD for n in inner)
                    if not (by_attribute or by_parameter):
                        hits.append((node.lineno,
                                     f"worktree_add(..., {ast.unparse(arg)}, ...)"))
        for child in ast.iter_child_nodes(node):
            walk(child, received)

    walk(tree, frozenset())
    return hits


def _calls_in(tree: ast.Module) -> int:
    """How many `worktree_add` calls the predicate actually examined."""
    return sum(1 for n in ast.walk(tree)
               if isinstance(n, ast.Call)
               and (getattr(n.func, "attr", None) == "worktree_add"
                    or getattr(n.func, "id", None) == "worktree_add"))


def _trees() -> list[tuple[Path, ast.Module]]:
    out = []
    for path in _fleet_sources():
        try:
            out.append((path, ast.parse(path.read_text(encoding="utf-8"))))
        except SyntaxError:  # a module that will not parse is a different failure
            continue
    return out


def test_no_call_site_ASSEMBLES_the_name_it_cuts_a_worktree_with() -> None:
    offenders = [(p, ln, what) for p, tree in _trees()
                 for ln, what in _assembled_names(tree)]
    assert not offenders, (
        "these calls build the worktree name where the worktree is cut, instead "
        "of taking it from the run context:\n"
        + "\n".join(f"  {p.relative_to(FLEET)}:{ln}  {what}"
                    for p, ln, what in offenders)
        + f"\n\nThe name is a FIELD — `RunContext.worktree_name`, derived once at "
          f"the dispatch boundary from the workflow key. Take `{FIELD}` from the "
          f"context, or receive it as a parameter of this function. Measured "
          f"2026-08-28: eleven sites in three spellings, one already drifted from "
          f"the workflow key it was supposed to follow."
    )


def test_THE_WALK_EXAMINED_A_POPULATION() -> None:
    """THE VACUITY FLOOR, and it is not optional for an absence assertion.

    The assertion above is phrased as an absence, so a walk that found no files —
    a moved directory, a renamed package — or a predicate that recognised no
    calls passes it while checking nothing. Two things are proved: that calls
    were actually examined, and that the file whose ALIAS defeats the existing
    `act.`-keyed predicates is among them.
    """
    trees = _trees()
    examined = sum(_calls_in(tree) for _, tree in trees)
    assert examined >= 10, (
        f"the predicate recognised only {examined} `worktree_add` calls across "
        f"{len(trees)} fleet modules — it was written against eleven production "
        f"call sites plus the definition, so it is no longer reading the tree "
        f"it claims to")

    seen = {p.name for p, tree in trees if _calls_in(tree)}
    for expected in ("review_pr_workflow.py", "build_workflow.py",
                     "plan_workflow.py", "run_plan_draft.py"):
        assert expected in seen, (
            f"{expected} holds a `worktree_add` call and this walk did not see "
            f"it, so the guard is narrower than its docstring claims")

    # THE ALIAS, ASSERTED RATHER THAN HOPED FOR. `review_pr_workflow` calls it as
    # `_shared.worktree_add`, and a predicate keyed on `act.` — which is what
    # `test_isolation_invariants._classify` still uses — reads zero calls here.
    alias_file = next(t for p, t in trees if p.name == "review_pr_workflow.py")
    assert _calls_in(alias_file) >= 1, (
        "the predicate cannot see `_shared.worktree_add` — it has been rewritten "
        "to key on a module alias, which is the exact blindness this guard was "
        "written to avoid")


def test_THE_DETECTOR_FIRES_on_every_spelling_the_defect_TOOK() -> None:
    """A POSITIVE CONTROL ON THE DETECTOR, not on the fleet.

    THE FOURTH SPELLING IS THE ONE THAT MATTERS. The first three are the shapes
    that were actually in the tree; `datetime` is a spelling nobody has written
    yet, and it is here because the whole argument for keying on the call site
    rather than on `time.time()` is that a spelling nobody anticipated must still
    fail. A control that only exercised the three shapes already fixed would
    prove the detector works on the population it can already see.
    """
    cases = {
        # spelling 1 — eight runners, via a local assignment
        "local_assign.py":
            'def m(repo_root, ref):\n'
            '    worktree_name = f"plan-{int(time.time())}"\n'
            '    act.worktree_add(repo_root, worktree_name, ref)\n',
        # spelling 2 — the two build runners; contains no `time.time()` substring
        "dunder_import.py":
            'def m(repo_root, ref):\n'
            '    wt = f"build-{int(__import__(\'time\').time())}"\n'
            '    act.worktree_add(repo_root, wt, ref)\n',
        # spelling 3 — inline, no assignment, reached through a DIFFERENT alias
        "inline_via_alias.py":
            'def m(task, worktree, pr):\n'
            '    _shared.worktree_add(worktree, f"review-pr-{task.pr_number}-'
            '{int(time.time())}", pr)\n',
        # a fourth spelling nobody has written — the point of the call-site key
        "fourth_spelling.py":
            'def m(repo_root, ref):\n'
            '    act.worktree_add(repo_root, "plan-" + str(datetime.now().timestamp()), ref)\n',
        # bare call, no module qualifier at all
        "bare_call.py":
            'def m(repo_root, ref):\n'
            '    worktree_add(repo_root, f"plan-{stamp()}", ref)\n',
        # the `name=` keyword form
        "kwarg_form.py":
            'def m(repo_root, ref):\n'
            '    act.worktree_add(repo_root, name=f"plan-{stamp()}", ref=ref)\n',
        # ⚠ A PARAMETER OF THE RIGHT NAME IS NOT ENOUGH — the ARGUMENT has to use
        # it. This is the half-migration shape: signature updated, call was not.
        "param_present_but_unused.py":
            'def m(repo_root, worktree_name, ref):\n'
            '    act.worktree_add(repo_root, f"plan-{stamp()}", ref)\n',
        # ⚠ AND REFERENCING *SOME* PARAMETER IS NOT ENOUGH EITHER. This is
        # exactly `review_pr_workflow`'s old line, which reads `task` — a real
        # parameter — while inventing the whole name.
        "references_a_different_param.py":
            'def m(task, worktree, ref):\n'
            '    _shared.worktree_add(worktree, f"review-pr-{task.pr_number}-{stamp()}", ref)\n',
    }
    for name, src in cases.items():
        assert _assembled_names(ast.parse(src)), f"the detector missed {name}: {src!r}"


def test_THE_DETECTOR_IS_SILENT_on_code_that_is_already_correct() -> None:
    """A NEGATIVE CONTROL. A guard that fails a fixed tree gets deleted, rightly."""
    clean = {
        "from_the_context.py":
            'def m(repo_root, ctx, ref):\n'
            '    act.worktree_add(repo_root, ctx.worktree_name, ref)\n',
        "received_as_a_parameter.py":
            'def m(repo_root, worktree_name, ref):\n'
            '    act.worktree_add(repo_root, worktree_name, ref)\n',
        "per_pass_tree_from_the_received_stem.py":
            'def m(worktree, worktree_name, this_pass, ref):\n'
            '    _shared.worktree_add(worktree, f"{worktree_name}-review-{this_pass}", ref)\n',
        "kwarg_from_the_context.py":
            'def m(repo_root, ctx, ref):\n'
            '    act.worktree_add(repo_root, name=ctx.worktree_name, ref=ref)\n',
        "closure_over_an_enclosing_parameter.py":
            'def outer(worktree_name):\n'
            '    def inner(repo_root, ref):\n'
            '        act.worktree_add(repo_root, worktree_name, ref)\n',
        # An unrelated function of the same shape must not be swept up.
        "not_worktree_add.py":
            'def m(repo_root, ref):\n'
            '    act.branch_add(repo_root, f"plan-{stamp()}", ref)\n',
    }
    for name, src in clean.items():
        assert not _assembled_names(ast.parse(src)), (
            f"the detector fires on {name}, which is CORRECT code — it would fail "
            f"a fixed tree and teach the next reader to weaken it")

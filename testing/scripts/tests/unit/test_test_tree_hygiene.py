"""Properties of the TEST TREE itself, gated on the class rather than per file.

WHY THIS LIVES BESIDE `test_mutate.py` AND NOT IN A COMPONENT. The property below
is repo-wide, and the reason it matters is the harness in this same directory:
`mutate.sh` cannot distinguish a collection failure from a caught mutation
(issue #72 — it exits 2 and prints MUTATION DEMONSTRATED). So a latent
`ImportError` at collection sits underneath every mutation-based guard in the
repo, reporting the guards as working while nothing ran. A gate scoped to one
component would not have seen the coupling that produced this file, because that
coupling was between two files in a component that had no such gate.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]

# This repo's own worktrees live under `.claude/`; scanning them would count
# another branch's files as this branch's. RELATIVE parts, not absolute — an
# absolute-path match skips every file when the suite runs from inside a
# worktree, which is a scan that visits nothing and reports a clean tree.
SKIP_PARTS = {".git", ".claude", "__pycache__", "node_modules", ".venv"}


def _test_modules() -> list[Path]:
    return [
        path for path in sorted(REPO_ROOT.rglob("test_*.py"))
        if not SKIP_PARTS & set(path.relative_to(REPO_ROOT).parts)
    ]


def _module_stems_named_in_call_arguments(tree: ast.AST) -> list[tuple[int, str]]:
    """`(lineno, stem)` for every module name a call argument spells LITERALLY.

    THIS IS THE PREDICATE, AND IT IS A MODULE-LEVEL FUNCTION SO THAT THE TEST
    DECLARING ITS RESIDUAL CAN CALL IT. For one revision it was typed inline in
    the check below AND typed again inside
    `test_an_ASSEMBLED_module_path_is_the_residual_this_gate_does_NOT_see`,
    which meant that test asserted a property of Python's `ast` module rather
    than a property of this gate. Its own contract says it must go red if the
    gate ever grows past literals — MEASURED, it did not: teaching the real
    check to resolve `ast.BinOp` concatenation left the residual test green,
    so the docstring paragraph claiming the gate cannot see an assembled path
    would have become false with nothing reporting it. That is exactly the rot
    the contract exists to prevent, and the identical defect was caught twice
    in the sibling markdown module during the same pull request.

    A trailing `.py` is stripped so a filename and a stem are the same answer;
    `Path(...).with_name("test_x.py")` and `import_module("test_x")` are the
    same coupling.
    """
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for arg in [*node.args, *(k.value for k in node.keywords)]:
            if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
                continue
            value = arg.value
            found.append((node.lineno, value[:-3] if value.endswith(".py") else value))
    return found


def test_no_test_module_imports_another_test_module() -> None:
    """A TEST MODULE IS NOT AN IMPORTABLE SURFACE, and the failure is at collection.

    `test_convergence.py` imported four underscore-private helpers out of
    `test_exit_record.py` in nine places. Three things were wrong and none was
    loud:

      * the `_` prefix said "private to this file" while the names were a
        contract between two files with no declared owner, so an edit made for
        one module's reasons broke the other with a traceback naming neither;
      * it resolved only under pytest's DEFAULT `prepend` import mode, which
        `pytest.ini` does not pin. `--import-mode=importlib` — the modern
        recommendation — breaks every such import at once;
      * the break is an `ImportError` AT COLLECTION, and issue #72 records that
        `mutate.sh` reads a collection failure as a caught mutation. The guard
        evidence for a whole phase can rest on a loop that never ran.

    A second live trigger, already on the plan: `test_exit_record.py` is ~1400
    lines and named as a split target. Splitting it breaks a DIFFERENT file.

    THE GATE IS ON THE CLASS. It does not name the two files that were coupled;
    it fails for any `test_*.py` importing any `test_*.py`, anywhere in the repo,
    including a pair nobody has written yet. The remedy is always the same and it
    is what this repo now does: a component-prefixed helper module (Testing
    Standard § test-helper module names) or a `conftest.py` fixture.
    """
    modules = _test_modules()
    assert len(modules) > 10, (
        f"only {len(modules)} test modules found under {REPO_ROOT} — this gate is "
        f"reporting on a tree it did not read"
    )
    names = {path.stem for path in modules}

    offenders: list[str] = []
    for path in modules:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                target = (node.module or "").split(".")[0]
            elif isinstance(node, ast.Import):
                target = next(
                    (a.name.split(".")[0] for a in node.names
                     if a.name.split(".")[0] in names), "",
                )
            else:
                continue
            if target in names and target != path.stem:
                offenders.append(
                    f"{path.relative_to(REPO_ROOT)}:{node.lineno} imports {target}"
                )

    assert not offenders, (
        "a test module imports another test module: "
        + "; ".join(offenders)
        + ". A test module is collected, not imported — the coupling has no "
          "declared owner, it resolves only under pytest's default `prepend` "
          "import mode, and it breaks at COLLECTION, which `mutate.sh` reads as "
          "a caught mutation (issue #72). Move the shared names into a "
          "component-prefixed helper module or a conftest.py fixture."
    )


def test_no_test_module_LOADS_another_test_module_DYNAMICALLY() -> None:
    """The same coupling by a spelling the check above cannot see.

    THE GATE ABOVE SAYS IT IS "ON THE CLASS" AND IT WAS NOT — it walks
    `ast.Import` and `ast.ImportFrom`, so it sees a coupling written as an
    import statement and is blind to the identical coupling written as a
    function call. MEASURED: a correction pass on PR #96 reached four private
    scanning helpers out of `test_candidates_prose_matches_the_table.py` via
    `importlib.util.spec_from_file_location(...,
    Path(__file__).with_name("test_candidates_prose_matches_the_table.py"))`.
    Every cost in the docstring above applied — unowned private-name contract,
    ImportError at COLLECTION that `mutate.sh` reads as a caught mutation — and
    this file stayed green through it. Two reviewers found it; no gate did.

    So the population here is CALL ARGUMENTS, not import statements: any string
    literal passed to any call that names another test module, by stem or by
    filename. That covers `spec_from_file_location`, `import_module`,
    `__import__`, and a `Path(...).with_name(...)` feeding any of them, without
    this gate needing to know which function is being called.

    WHAT IT DOES NOT LOOK AT, and it is the same shape one level down: a path
    ASSEMBLED from parts (`"test_" + name + ".py"`, or a stem read from a
    directory listing) carries no literal for this to match. That residual is
    real and unexercised — held by
    `test_an_ASSEMBLED_module_path_is_the_residual_this_gate_does_NOT_see`. It
    is disclosed rather than chased because the alternative is dataflow
    analysis, and the failure this gate exists to stop is the CONVENIENT
    spelling, not a determined one.
    """
    modules = _test_modules()
    names = {path.stem for path in modules}

    offenders: list[str] = []
    for path in modules:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for lineno, target in _module_stems_named_in_call_arguments(tree):
            if target in names and target != path.stem:
                offenders.append(
                    f"{path.relative_to(REPO_ROOT)}:{lineno} loads {target}"
                )

    assert not offenders, (
        "a test module names another test module in a call argument, which is "
        "how a dynamic load of a collected module is spelled: "
        + "; ".join(sorted(set(offenders)))
        + ". This is the same coupling the check above forbids and the same "
          "remedy applies — move the shared names into a component-prefixed "
          "helper module. Referring to another test module in PROSE is fine; "
          "this only reads call arguments."
    )


def test_an_ASSEMBLED_module_path_is_the_residual_this_gate_does_NOT_see() -> None:
    """A literal is matchable; a concatenation is not. Held so the limit is real.

    IF THIS TEST EVER GOES RED NOTHING IS BROKEN — it means the gate above grew
    past literals. Delete this test and the matching docstring paragraph
    together, so the two cannot disagree.

    IT CALLS `_module_stems_named_in_call_arguments` ITSELF, and for one
    revision it did not — it re-typed the extraction inline, so it asserted a
    property of `ast` rather than of the gate and could not honour the contract
    in the paragraph above. MEASURED: teaching the real check to resolve
    `ast.BinOp` concatenation left this test green while the residual it
    declares stopped being real. A residual test that reimplements the
    predicate stops describing the predicate the moment either one moves,
    which makes it worse than no test — it reads as coverage.
    """
    source = 'import importlib\nname = "test_" + "mutate" + ".py"\nimportlib.import_module(name)\n'
    stems = [stem for _lineno, stem in
             _module_stems_named_in_call_arguments(ast.parse(source))]

    assert "test_mutate" not in stems, (
        "the gate now resolves an ASSEMBLED module path, so it is stronger "
        "than the docstring paragraph above claims. Nothing is broken — delete "
        f"this test and that paragraph in one commit. (Saw: {stems})"
    )


def _docstring_only_tests(tree: ast.AST) -> list[tuple[int, str]]:
    """THE PREDICATE. `(lineno, name)` for every `test_*` whose body is a docstring.

    A MODULE-LEVEL FUNCTION SO THE CONTROL BELOW CAN CALL IT, for the reason the
    residual test one function up states at length: a control that re-types the
    extraction asserts a property of `ast` rather than of this gate.

    `pass` and `...` are stripped alongside the docstring. They are the two other
    spellings of "no statements", and a rule that caught one but not the others
    would be satisfied by the shortest possible edit to the file it fired on.
    """
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue
        body = list(node.body)
        if body and isinstance(body[0], ast.Expr) \
                and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            body = body[1:]
        body = [statement for statement in body
                if not isinstance(statement, ast.Pass)
                and not (isinstance(statement, ast.Expr)
                         and isinstance(statement.value, ast.Constant)
                         and statement.value.value is Ellipsis)]
        if not body:
            found.append((node.lineno, node.name))
    return found


def test_no_TEST_IN_THIS_SUITE_ASSERTS_NOTHING() -> None:
    """A test whose whole body is its docstring passes by examining nothing.

    THE DEFECT THIS HOLDS, measured 2026-09-02. A new guard was inserted BETWEEN
    `test_every_runner_with_a_repo_path_is_exercised`'s docstring and its body,
    in `scripts/workflows/temporal/tests/unit/
    test_an_entrypoint_REFUSES_an_escaping_operator_path.py`. The result was two
    defects from one edit: that test kept its name, its docstring and its green
    tick while asserting nothing, and its `unshaped` assertion ran under the
    other test's name — so the two independent properties short-circuited and a
    change that both orphaned a key and added an unshaped runner would have
    reported only the first.

    IT IS THE CLASS AND NOT THE INSTANCE THAT IS HELD HERE, because the instance
    was found by a reviewer reading a diff, which does not scale to 1696 test
    functions and did not catch it in the pass that wrote it. The file it landed
    in is the same file that builds vacuity FLOORS for its own sweeps; a floor
    protects a guard that runs, and nothing protected the guard that did not.

    WHAT THIS DOES NOT LOOK AT, stated because a sweep is its predicate:

      * **A body that runs but asserts nothing.** `validate(cfg, hooks)  # must
        not raise` is a deliberate and legitimate shape — seven live tests use
        it, each saying so — and the not-raising IS the assertion. Demanding an
        `assert` keyword would require an exemption list of seven correct tests,
        and an exemption list is the mechanism whose rot this repo has measured
        twice. The docstring-only body has no legitimate use, so it needs none.
      * **A body whose assertions cannot fail.** `assert True` passes here.
        `test_a_census_guard_proves_its_own_predicate` holds the tree-walking
        subset of that question; the general case is what review is for.
    """
    offenders: list[str] = []
    for path in _test_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        offenders += [f"{path.relative_to(REPO_ROOT)}:{lineno} {name}"
                      for lineno, name in _docstring_only_tests(tree)]

    assert not offenders, (
        "these test functions have a docstring and no statements, so they pass "
        "by examining nothing: " + "; ".join(sorted(offenders))
        + ". Either the body was displaced — check whether the function below "
          "it grew an assertion that belongs here — or the test was never "
          "finished. A named green tick over nothing is worse than no test."
    )


def test_THE_VACUITY_SWEEP_READ_THE_TREE_AND_CATCHES_THE_SHAPE() -> None:
    """CONTROL, both halves: the walk found tests, and the predicate discriminates.

    The floor is asserted because every assertion above is over a list that is
    empty when the walk stops walking — a moved `REPO_ROOT`, a changed glob, a
    `SKIP_PARTS` entry that swallows the tree — and a green sweep over nothing
    is indistinguishable from a green sweep over 1696 functions.
    """
    # 1696 test functions across the tree when this floor was set; the floor sits
    # well below it because the count moves with every ordinary test added or
    # removed, and a floor pinned to its own measurement fails on the next edit.
    counted = sum(
        1 for path in _test_modules()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_"))
    assert counted >= 800, (
        f"the sweep found only {counted} test functions under {REPO_ROOT}; "
        f"there were 1696 when this floor was set. A walk that has stopped "
        f"walking passes vacuously.")

    # THE PREDICATE, against literal sources — the shape that shipped, the two
    # other spellings of an empty body, and the three shapes that must NOT fire.
    shipped = ('def test_every_runner_is_exercised() -> None:\n'
               '    """A new runner must fail HERE, not be skipped."""\n'
               'def test_no_entry_names_a_runner_that_is_gone() -> None:\n'
               '    assert not orphaned\n')
    assert [name for _lineno, name in _docstring_only_tests(ast.parse(shipped))] \
        == ["test_every_runner_is_exercised"], (
        "the predicate must flag the docstring-only body that actually shipped")

    for empty in ('def test_x():\n    pass\n',
                  'def test_x():\n    """doc"""\n    ...\n',
                  'def test_x():\n    """doc"""\n    pass\n'):
        assert _docstring_only_tests(ast.parse(empty)), (
            f"an empty body spelled another way must still fire: {empty!r}")

    for holds in ('def test_x():\n    """doc"""\n    validate(cfg)\n',
                  'def test_x():\n    """doc"""\n    assert 1\n',
                  'def helper():\n    """doc"""\n'):
        assert not _docstring_only_tests(ast.parse(holds)), (
            f"this must NOT fire — a guard that flags correct code gets "
            f"deleted: {holds!r}")

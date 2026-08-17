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
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for arg in [*node.args, *(k.value for k in node.keywords)]:
                if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
                    continue
                target = arg.value[:-3] if arg.value.endswith(".py") else arg.value
                if target in names and target != path.stem:
                    offenders.append(
                        f"{path.relative_to(REPO_ROOT)}:{node.lineno} loads {target}"
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
    """
    source = 'import importlib\nname = "test_" + "mutate" + ".py"\nimportlib.import_module(name)\n'
    tree = ast.parse(source)

    literals = [
        arg.value
        for node in ast.walk(tree) if isinstance(node, ast.Call)
        for arg in [*node.args, *(k.value for k in node.keywords)]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
    ]
    assert "test_mutate" not in literals and "test_mutate.py" not in literals, (
        "an assembled module path is now visible as a call-argument literal; "
        "the gate above may have grown stronger than its docstring claims"
    )

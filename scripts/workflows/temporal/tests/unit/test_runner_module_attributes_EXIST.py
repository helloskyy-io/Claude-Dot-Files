"""Every `<alias>.<name>` a runner calls must exist on the module it aliases.

WHY THIS EXISTS, and it is a lesson about the guard rather than about the bug.
PR #115 fixed four runners that opened their worktree on `main` during a `--pr`
pass. Its guard asserted the OLD STRING was gone:

    assert 'worktree_add(repo_root, worktree_name, "HEAD")' not in src

That is a shape check. The replacement expression called `act.branch_of(...)`,
which does not exist on `plan_activities` — the real function is
`assistant_activities.pr_branch`, and `branch_of` is a one-line alias defined
only in `research_activities`. So 1831 tests passed, the PR merged, and the
first live `--pr` run died on `AttributeError` before reaching the model.

**A guard that checks the shape of a fix cannot see whether the fix runs.** This
one imports the module each runner aliases and asserts every attribute it reaches
for is really there — which is the property the shape check was standing in for.

WHAT IT DOES NOT COVER, so it is not over-read: it checks that a NAME resolves,
never that the call is correct. Wrong argument order, a wrong `pr_number`, a
function that returns the wrong thing — all invisible here and all still need a
test that runs the path. The narrow claim is that no runner can ship a call to a
function that does not exist.
"""
from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

import pytest

TEMPORAL = Path(__file__).resolve().parents[2]
SCRIPTS = TEMPORAL / "scripts"
if str(TEMPORAL) not in sys.path:
    sys.path.insert(0, str(TEMPORAL))


def _aliases(tree: ast.AST) -> dict[str, str]:
    """`from modules.x import y as act` -> {"act": "modules.x.y"}."""
    out = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module:
            for a in n.names:
                if a.asname:
                    out[a.asname] = f"{n.module}.{a.name}"
    return out


def _runners() -> list[Path]:
    found = sorted(SCRIPTS.glob("run_*.py"))
    assert len(found) > 5, (
        f"only {len(found)} runners found under {SCRIPTS} — the glob is wrong, "
        f"and a guard that inspects nothing passes silently"
    )
    return found


@pytest.mark.parametrize("runner", _runners(), ids=lambda p: p.name)
def test_every_aliased_attribute_a_runner_calls_EXISTS(runner: Path) -> None:
    tree = ast.parse(runner.read_text())
    aliases = _aliases(tree)
    missing = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)):
            continue
        mod_path = aliases.get(node.value.id)
        if not mod_path:
            continue                       # a local name, not an aliased module
        try:
            mod = importlib.import_module(mod_path)
        except ImportError:                # a module this environment cannot load
            continue                       # is a different failure, not this one
        if not hasattr(mod, node.attr):
            missing.append(f"{node.value.id}.{node.attr}  (line {node.lineno}) "
                           f"-> {mod_path} has no such attribute")
    assert not missing, (
        f"{runner.name} calls attributes that do not exist on the module it "
        f"imports, so the line raises AttributeError the first time it runs:\n  "
        + "\n  ".join(sorted(set(missing)))
    )


def test_the_guard_can_actually_FAIL(tmp_path: Path) -> None:
    """The #115 regression, reproduced, so the failing path runs every time.

    `act.branch_of` is the exact call that shipped. It exists on
    `research_activities` and NOT on `plan_activities`, which is what made it
    read as plausible in review.
    """
    src = ("from modules.assistant.plan import plan_activities as act\n"
           "x = act.branch_of('1', None)\n")
    tree = ast.parse(src)
    aliases = _aliases(tree)
    assert aliases == {"act": "modules.assistant.plan.plan_activities"}
    mod = importlib.import_module(aliases["act"])
    assert not hasattr(mod, "branch_of"), "the regression is no longer reproducible"
    assert hasattr(mod, "pr_branch"), "the correct name is gone — the fix regressed"

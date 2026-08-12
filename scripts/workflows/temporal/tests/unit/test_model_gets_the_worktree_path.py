"""A prompt must hand the model a path anchored to the worktree it runs in.

THE DEFECT THIS EXISTS TO CATCH, observed twice. `run_research*.py` builds the
pool path as `repo_root / <arg>` — absolute, into the MAIN CHECKOUT — and every
research workflow separately re-anchors it with `act.in_worktree()` into a local
named `pool`. All four then rendered the *un-anchored* `research_dir` into
`${RESEARCH_DIR}`, so the model was told to write to the main checkout while its
worktree sat elsewhere. PR #84 and PR #86 both wrote a paper into the main
checkout; both were caught only by the workflow's mandated pre-commit
`git status`, which is a backstop and not a guarantee.

`in_worktree`'s own docstring already names the failure — "one logical path, two
filesystem locations, in one dispatch" — for the values DERIVED from the path.
The value handed to the model was never covered, which is why the helper existed
and the bug happened anyway.

This asserts over every research workflow found on disk rather than a hardcoded
list, so a fifth one added later is covered on the day it lands.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

RESEARCH = Path(__file__).resolve().parents[2] / "modules" / "assistant" / "research"
KEY = "RESEARCH_DIR"
ANCHORED = "pool"
UNANCHORED = "research_dir"


def _workflows() -> list[Path]:
    found = sorted(RESEARCH.glob("*/[a-z]*_workflow.py"))
    assert found, f"no research workflows under {RESEARCH} — the glob is wrong"
    return found


def _rendered_path_expr(tree: ast.AST) -> ast.expr | None:
    """The expression assigned to the `RESEARCH_DIR` key of any dict literal."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if isinstance(key, ast.Constant) and key.value == KEY:
                return value
    return None


def _names_in(expr: ast.expr) -> set[str]:
    return {n.id for n in ast.walk(expr) if isinstance(n, ast.Name)}


@pytest.mark.parametrize("path", _workflows(), ids=lambda p: p.parent.name)
def test_the_model_is_given_the_worktree_anchored_path(path: Path) -> None:
    tree = ast.parse(path.read_text())
    expr = _rendered_path_expr(tree)
    if expr is None:
        pytest.skip(f"{path.name} renders no {KEY}")

    names = _names_in(expr)
    assert ANCHORED in names, (
        f"{path.name} renders {KEY} from {sorted(names)}, which does not include "
        f"`{ANCHORED}`. The model would be pointed at the main checkout. Use the "
        f"`act.in_worktree()` result that this module already computes."
    )
    assert UNANCHORED not in names, (
        f"{path.name} renders {KEY} from the un-anchored `{UNANCHORED}`. That path "
        f"resolves into the MAIN CHECKOUT, not this run's worktree."
    )


def test_every_workflow_that_renders_the_key_also_anchors_it() -> None:
    """The guard above skips a workflow with no key — prove that never hides all of them."""
    rendering = [p for p in _workflows() if _rendered_path_expr(ast.parse(p.read_text()))]
    assert len(rendering) >= 4, (
        f"only {len(rendering)} research workflows render {KEY}; four did when this "
        f"check was written. If one legitimately stopped, lower the floor deliberately "
        f"— do not let the parametrised check pass by skipping everything."
    )

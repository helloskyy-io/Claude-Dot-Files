"""A `--dry-run` must preview the prompt the live run dispatches, not a copy of it.

THE CLASS, AND WHY IT IS CHECKED STRUCTURALLY RATHER THAN PER RUNNER. A runner's
`--dry-run` branch and its workflow's `run_*` function both have to fill the same
prompt placeholders. Whenever the runner assembles its own dict, the two drift —
silently, because a preview that is wrong looks exactly like a preview that is
right, and the artifact an operator checked is not the artifact a model received.

**This family has shipped that bug.** `plan_sprint_workflow.correction_note`'s
docstring records a dry run rendering only half of `CORRECTION_NOTE` and
previewing text no model would ever see. It was fixed by patching the runner's
copy, which closed the instance and left the shape — and the shape is what
reproduces. Two of three runners still carried a hand-built dict afterwards, and
a third was written with one.

So the check keys on the SHAPE: no runner may pass a dict literal to `render`.
A new runner that copies the pattern fails here on the day it is written, rather
than on the day somebody adds a placeholder to one side of the pair.

WHAT THIS DOES NOT PROVE. It cannot show the two dicts hold equal VALUES — the
live path needs a worktree, a repo and a model. It proves there is only one dict,
which is the property that makes equality unnecessary.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_RUNNERS = sorted((Path(__file__).resolve().parents[2] / "scripts").glob("run_*.py"))


def test_the_sweep_finds_the_runners() -> None:
    """VACUITY FLOOR. An assertion over an empty set is indistinguishable from
    full coverage, and this suite has already been bitten by exactly that."""
    assert len(_RUNNERS) >= 8, f"the runner sweep found only {[p.name for p in _RUNNERS]}"


def _render_calls(tree: ast.AST) -> list[ast.Call]:
    """Every `render(...)` call, however the module spells the qualifier."""
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and (getattr(n.func, "attr", None) == "render"
                 or getattr(n.func, "id", None) == "render")]


@pytest.mark.parametrize("runner", _RUNNERS, ids=lambda p: p.name)
def test_a_runner_never_hand_ASSEMBLES_the_prompt_values(runner: Path) -> None:
    """The values a runner renders must come from a CALL, never a literal.

    A call is the workflow's own assembly — `wf.prompt_values(...)` in all three
    runners that render today. A `{...}` here is a second copy of a dict that
    already exists, and the copy is what drifts.
    """
    for call in _render_calls(ast.parse(runner.read_text())):
        if len(call.args) < 2:
            continue
        values = call.args[1]
        assert not isinstance(values, ast.Dict), (
            f"{runner.name} line {values.lineno} builds its own prompt values "
            f"dict. Call the workflow's `prompt_values(...)` instead — a dry run "
            f"that assembles its own copy previews a prompt that is not the one "
            f"dispatched, which this family has already shipped once.")


@pytest.mark.parametrize("runner", _RUNNERS, ids=lambda p: p.name)
def test_a_runner_that_renders_calls_a_workflow_level_ASSEMBLER(runner: Path) -> None:
    """And the call it makes must be the workflow's, not a local helper.

    A module-local `_values()` in the runner satisfies the check above while
    being the same second copy one indirection down — the shape this whole file
    exists to keep out. Asserted by qualifier: the callee must be an attribute of
    something imported, which is how every runner names its workflow module.
    """
    for call in _render_calls(ast.parse(runner.read_text())):
        if len(call.args) < 2:
            continue
        values = call.args[1]
        if not isinstance(values, ast.Call):
            continue
        assert isinstance(values.func, ast.Attribute), (
            f"{runner.name} line {values.lineno} fills the prompt from a "
            f"module-local call. The assembler must live with the workflow that "
            f"dispatches the prompt, so both paths reach the same one.")

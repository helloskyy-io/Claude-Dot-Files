"""A dispatch that names a PR must never be handed a prompt that opens one.

TWO AXES, AND CONFLATING THEM ABANDONS THE PR. `plan_path` (or any future
task-shape argument) says WHAT SHAPE the task has; `pr_number` says WHERE the work
lands. `build_draft` selected its template on the first axis alone —

    if plan_path:
        template = act.shared_prompt("build_from_plan")

— so `run_build.py --pr 124 --phase <doc>`, the exact shape an operator used on
PR #124, got `build_from_plan.md`: *"You are executing the BUILD-PHASE workflow on
a new branch"*, *"Create a new PR using `gh pr create`"*, no `${PR_NUMBER}`, and no
mention of the PR at all. Meanwhile the parent had already cut the worktree from
`origin/<PR 124's branch>`. The child therefore sits on a branch that already has
an open PR and is instructed to open one: either `gh pr create` fails and the
dispatch dies with *"produced no PR URL"*, or a second PR opens and #124's runway,
review history and CI record are abandoned.

FOUND BY RENDERING, NOT BY READING, WHICH IS THE POINT OF THIS FILE. Four review
contexts read that handoff — a draft pass, a refine pass and two of its agents —
and none asked what happens when both inputs are set. A ~15-line probe that mocks
`run_claude` and looks at the first line of the rendered prompt found it in one
run. A guard on a prompt SELECTOR has to render prompts; asserting about the
source is asserting about the wrong artifact.

THE POPULATION IS THE CLASS, NOT THE TWO MODULES THAT REGRESSED. Every workflow
whose `prompts/` directory holds BOTH `update_pr.md` and `new_branch.md` is one
that chooses between updating a PR and creating one, and that choice is what this
polices. Three qualify today; a fourth is covered on the day it lands. The minor
tier had carried the latent form since it was written — it has always passed
`plan_path` — and one predicate fixed both, which is why nothing here is
parametrised on the tier that happened to be reported.

`test_axis_CENSUS` IS WHAT MAKES THIS A CLASS CHECK RATHER THAN A CASE LIST. The
cross-product below can only cover the axes it knows about, so a new selector
parameter appearing on any member of the population reds the census with an
instruction to extend the product. Without it this file would silently degrade
into a test of `pr_number` × `plan_path` on the day a third axis arrived, which is
exactly how the defect it exists to catch was introduced.

WHAT THIS DOES NOT LOOK AT:

  * **Whether the model OBEYS.** It asserts the instruction assembled is the right
    one, never that it was followed.
  * **What the PARENT passes.** These are the children; a parent that stops
    forwarding `pr_number` is a different wiring fact, pinned by
    `test_a_correction_pass_RESTATES_no_task.py`'s reader of the draft call.
  * **The refine children.** They take `pr_number` as REQUIRED and have no
    create-a-PR wrapper to select, so the choice this polices does not exist there.
  * **Whether `${PLAN_PATH}` is rendered.** Giving that up when a PR is named is
    the deliberate trade — it restores the pre-2026-08-19 behaviour exactly, and
    the plan doc's CONTENTS still reach the model as `DESCRIPTION` via `task_text`.
"""

from __future__ import annotations

import inspect
import itertools
from pathlib import Path
from unittest import mock

import pytest

from modules import assistant  # noqa: F401  — anchors the package for the imports below
from modules.assistant import assistant_activities as act

_ASSISTANT = Path(act.__file__).resolve().parent

# Arguments that do NOT change which prompt is selected: the task's text, where it
# runs, and how loud it is. Everything else is an axis.
# `prefer_repo` is a NON-AXIS, and the distinction is the point of this set: it is
# consulted AFTER the child has run, to pick this dispatch's own PR out of a run
# that legitimately opened one in another repo too (a phase build flips checkboxes
# in the planning repo). It never reaches `render`, so it cannot change which
# wrapper is selected or what the child is told. Added 2026-09-01.
_NON_AXIS = frozenset({"description", "repo_root", "worktree", "context", "verbose",
                       "prefer_repo"})

# The axes this file's cross-product knows how to vary, and a value for each that
# is distinguishable in a rendered prompt.
_AXIS_VALUES: dict[str, str] = {
    "pr_number": "124",
    "plan_path": "docs/development/x/phase2_scratch.md",
    "task_file": "docs/development/x/brief_scratch.md",
}

_PR_NUMBER = _AXIS_VALUES["pr_number"]


def _selecting_workflows() -> list[Path]:
    """DERIVED: a module holding both wrappers is one that makes the choice."""
    found = sorted(
        p for p in _ASSISTANT.rglob("*_workflow.py")
        if (p.parent / "prompts" / "update_pr.md").is_file()
        and (p.parent / "prompts" / "new_branch.md").is_file()
    )
    assert found, (
        f"no workflow under {_ASSISTANT} holds both `prompts/update_pr.md` and "
        f"`prompts/new_branch.md` — the derivation is wrong and every check below "
        f"is asserting over an empty set."
    )
    return found


def _entrypoint(path: Path):
    """The module's `run_*` callable, imported by its dotted package path."""
    # Rooted at the `modules` package's PARENT, so the dotted name is the same
    # `modules.assistant....` the fleet itself imports by.
    dotted = ".".join(path.relative_to(_ASSISTANT.parents[1]).with_suffix("").parts)
    module = __import__(dotted, fromlist=["_"])
    runners = [v for n, v in vars(module).items()
               if n.startswith("run_") and inspect.isfunction(v)
               and v.__module__ == module.__name__]
    assert len(runners) == 1, (
        f"{path.name} exposes {len(runners)} `run_*` functions; this reader "
        f"assumes exactly one entrypoint per workflow module."
    )
    return module, runners[0]


def _axes_of(fn) -> list[str]:
    params = inspect.signature(fn).parameters
    return [n for n in params if n not in _NON_AXIS]


def _render(module, fn, kwargs: dict[str, str]) -> str:
    """Run the entrypoint far enough to capture the prompt, and no further.

    `run_claude` is the outermost side effect and returns the string the caller
    parses for a PR URL, so mocking it there yields the fully-rendered prompt while
    the workflow still believes it succeeded. `pr_branch` is mocked because it
    shells out to `gh`; its VALUE is irrelevant here and deliberately not the PR
    number, so a prompt that contains "124" contains it because `${PR_NUMBER}` was
    bound rather than because the branch name leaked it in.

    PATCHED ON THE MODULE'S OWN `act` ALIAS, NOT ON `assistant_activities`. The two
    are not the same object across this population: the build children alias the
    shared module directly, while `plan_revision` aliases `plan_activities`, which
    re-exports. Patching the shared module let the real `run_claude` through and it
    tried to open a run log under a repo root that does not exist — which is a
    LOUD failure here and would have been a silent skip in a laxer harness.
    """
    captured: dict[str, str] = {}

    def _capture(prompt: str, **_kw) -> str:
        captured["prompt"] = prompt
        return "https://github.com/o/r/pull/9"

    assert hasattr(module, "act"), (
        f"{module.__name__} has no `act` alias, so this harness cannot intercept "
        f"its side effects and would dispatch a real run.")

    with mock.patch.object(module.act, "run_claude", _capture), \
            mock.patch.object(module.act, "pr_branch", lambda n, r: "a-branch-name"):
        fn(description="the task", repo_root=Path("/main/checkout"),
           worktree=Path("/tmp/wt"), **kwargs)

    assert "prompt" in captured, (
        f"{fn.__name__} never called `run_claude`, so nothing was rendered and the "
        f"assertions below would pass over an empty capture."
    )
    return captured["prompt"]


def _combinations(fn) -> list[dict[str, str]]:
    """Every on/off combination of this entrypoint's axes, with `pr_number` ON.

    Only the `pr_number`-set half is generated: the property is about what a run
    that NAMES a PR is told, and the other half is the discriminator below.

    AN AXIS THE PRODUCT DOES NOT KNOW IS SKIPPED HERE AND CAUGHT BY THE CENSUS,
    deliberately. This ran off `_AXIS_VALUES[a]` directly, so an unknown axis raised
    a `KeyError` during COLLECTION — which took the whole module down, including the
    census test written to explain what to do about it. Loud, but it reported a
    KeyError where the actionable message was one test away from firing.
    """
    others = [a for a in _axes_of(fn) if a != "pr_number" and a in _AXIS_VALUES]
    out = []
    for mask in itertools.product([False, True], repeat=len(others)):
        kwargs = {"pr_number": _PR_NUMBER}
        kwargs |= {a: _AXIS_VALUES[a] for a, on in zip(others, mask) if on}
        out.append(kwargs)
    return out


def _cases() -> list[tuple[Path, dict[str, str]]]:
    cases = []
    for path in _selecting_workflows():
        _module, fn = _entrypoint(path)
        cases += [(path, kw) for kw in _combinations(fn)]
    return cases


def _case_id(case: tuple[Path, dict[str, str]]) -> str:
    path, kwargs = case
    on = "+".join(sorted(k for k in kwargs if k != "pr_number")) or "pr-only"
    return f"{path.parent.name}[{on}]"


# --- the census, which is what keeps this a CLASS check ------------------------

@pytest.mark.parametrize("path", _selecting_workflows(), ids=lambda p: p.parent.name)
def test_axis_CENSUS_no_selector_argument_is_unknown_to_the_cross_product(
        path: Path) -> None:
    """A new axis must RED here rather than silently escape the product below.

    This is the check that survives the next change. The defect this file exists
    to catch was a second axis being consulted by the selector while the guard —
    and every reader — still thought in terms of one.
    """
    _module, fn = _entrypoint(path)
    unknown = [a for a in _axes_of(fn) if a not in _AXIS_VALUES]
    assert not unknown, (
        f"{path.parent.name}.{fn.__name__} takes {unknown}, which the cross-product "
        f"in this file does not know how to vary. If it can influence which prompt "
        f"is selected or what is rendered, add it to `_AXIS_VALUES` — the product "
        f"then covers it automatically. If it genuinely cannot, add it to "
        f"`_NON_AXIS` and say why. Do NOT leave it out of both: an axis known to "
        f"neither set is an axis this guard is blind to, which is the exact shape "
        f"of the defect it was written for."
    )


def test_the_derivation_found_every_selector() -> None:
    """VACUITY FLOOR, pinned by name so a vanished member is visible."""
    found = {p.parent.name for p in _selecting_workflows()}
    assert found == {"build_draft", "build_draft_minor"}, (
        f"the workflows choosing between creating and updating a PR are "
        f"{sorted(found)}. If a fourth was added it is now covered — extend this "
        f"expectation. If one vanished, the checks below assert over less than "
        f"they claim."
    )


# --- the property ---------------------------------------------------------------

@pytest.mark.parametrize("case", _cases(), ids=_case_id)
def test_a_run_given_a_PR_is_TOLD_ABOUT_IT_and_never_told_to_create_one(
        case: tuple[Path, dict[str, str]]) -> None:
    """THE GATE, over every combination of every axis, with `pr_number` set."""
    path, kwargs = case
    module, fn = _entrypoint(path)
    prompt = _render(module, fn, kwargs)

    assert "gh pr create" not in prompt, (
        f"{path.parent.name} with {sorted(kwargs)} renders a prompt telling the "
        f"model to CREATE a PR, while `pr_number={_PR_NUMBER}` says the work "
        f"belongs on an existing one. The parent cuts the worktree from that PR's "
        f"branch, so the child would open a second PR against a branch that "
        f"already has one — abandoning the first PR's runway, review history and "
        f"CI record. The destination axis must win the wrapper selection."
    )
    assert _PR_NUMBER in prompt, (
        f"{path.parent.name} with {sorted(kwargs)} renders a prompt that never "
        f"names PR #{_PR_NUMBER}, so `${{PR_NUMBER}}` was not bound and the model "
        f"has no way to find the work it was sent to correct."
    )


@pytest.mark.parametrize("path", _selecting_workflows(), ids=lambda p: p.parent.name)
def test_a_run_with_NO_pr_is_still_told_to_create_one(path: Path) -> None:
    """THE DISCRIMINATOR, and without it the gate above is satisfiable by silence.

    A workflow that rendered an empty prompt, or one that never mentioned PRs at
    all, would pass every assertion above. This asserts the opposite verdict on
    the opposite input, so the two together show the selector actually branches.
    """
    module, fn = _entrypoint(path)
    prompt = _render(module, fn, {})

    assert "gh pr create" in prompt, (
        f"{path.parent.name} with no `pr_number` renders a prompt that does NOT "
        f"tell the model to create a PR. Either the new-branch path stopped "
        f"working — nothing would open a PR and the run dies on its completion "
        f"contract — or this reader is looking at the wrong artifact, in which "
        f"case the gate above is passing for free."
    )
    assert _PR_NUMBER not in prompt, (
        f"{path.parent.name} rendered PR #{_PR_NUMBER} without being given one, "
        f"so the number is hardcoded somewhere in the chain and the gate above "
        f"proves nothing."
    )

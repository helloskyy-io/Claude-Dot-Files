"""`--pr <n>` alone is a complete build dispatch, and the plan reaches the child.

TWO PROPERTIES, ONE FILE, because they are the same handoff seen from both ends:
what a `--pr` run is TOLD to do, and what a `--phase` run's plan is USED for. Both
were broken in the same expression, and both were found by running the fleet.

--- 1. A CORRECTION PASS RESTATES NOTHING -------------------------------------

MEASURED 2026-08-19:

    $ run_build.py --pr 124 --repo <path>
    build: error: exactly one task source is required — description, --task-file or --phase

The dispatch had to be re-issued with the original `--phase` repeated. That is not
a safety property. A `--pr` pass is a correction of work already described ON THAT
PR, and re-supplying the brief creates a SECOND copy of a runway that can disagree
with the one on the thread — while the thread is the copy every child in this
family is required to read (`fidelity_read_and_compare.md` makes
`gh pr view --json body,comments` mandatory and warns that the bare form
truncates).

THE SWEEP, BEFORE GENERALISING. `run_research_minor.py` and `run_plan_feature.py`
impose no task-source rule at all. Only `BuildInput` did, and exactly two runners
share it — `run_build.py` and `run_build_minor.py`. `run_plan_revision.py` has the
same SYMPTOM through a different mechanism (a required positional `description`)
and is deliberately NOT changed here: nobody has measured it, and relaxing a
required positional is a CLI contract change on a runner that reported no problem.
It is surfaced rather than swept in.

WHAT IS STILL REFUSED, and this is the half the original check was written for: a
run with neither a task source NOR a `--pr` — the empty-PR case — and a run with
TWO task sources, which has no way to say which one it obeyed.

--- 2. THE PLAN REACHES THE DRAFT CHILD ---------------------------------------

FOUND WHILE FIXING THE ABOVE, in the same expression. `build_draft.run_draft`
branches on `plan_path` to select the `build_from_plan` / `stages_1_to_4_from_plan`
pair. `build_minor_workflow` passed it; `build_workflow` did NOT — so the MAJOR
tier's `--phase` runs never reached the plan-driven prompts at all, and
`${PLAN_PATH}` never reached the model. `test_build_prompt_variants_do_not_fork.py`
opened by describing that pair as the one used *whenever* a run is launched with
`--phase` — true of one tier of two, and corrected in that file on 2026-08-20 to
state the two-axis condition the selector now uses. That file compares the two
prompts' CONTENTS and is structurally blind to whether either is reachable, which
is why the fork guard was green over this the whole time.

WHAT THIS DOES NOT LOOK AT:

  * **Whether the PR actually carries a runway.** Nothing here reaches GitHub. An
    empty thread is the child's finding to report, not this layer's to predict.
  * **Whether the model OBEYS the instruction.** It checks the instruction is
    assembled and reachable, never that it worked.
  * **The `--pr` rule on any runner that does not build a `BuildInput`.** Derived
    from the tree below, so a third one is covered when it is written — but
    `run_plan_revision.py` is out of scope by the ruling above, not by oversight.
  * **The INTERACTION between `pr_number` and `plan_path`, which is where §2's fix
    went wrong.** Passing `plan_path` from the major parent was correct and stays;
    what it exposed is that the draft children selected their template on
    `plan_path` ALONE, so `--pr <n> --phase <doc>` reached `build_from_plan.md` —
    "on a new branch", "create a new PR using `gh pr create`", no `${PR_NUMBER}` —
    while the parent had cut the worktree from that PR's own branch. Nothing in
    this module could have seen it: the reader below asserts a WIRING fact from the
    source, and the defect was in what the rendered PROMPT said.
    `test_a_run_given_a_PR_is_never_told_to_CREATE_one.py` owns that axis, renders
    the prompts, and carries a census so a THIRD axis cannot slip past it the way
    the second slipped past this one.
  * **What the rendered `${PLAN_PATH}` points at.** An in-repo absolute `--phase`
    used to render a main-checkout path to a model running in the worktree;
    `test_no_prompt_hands_the_model_a_MAIN_CHECKOUT_path.py` owns that.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from modules.assistant.build import build_activities as build_act
from modules.assistant.build.build_inputs import BuildInput
from modules.assistant.build.build import build_workflow
from modules.assistant.build.build_minor import build_minor_workflow

_TEMPORAL = Path(__file__).resolve().parents[2]
_RUNNERS = sorted((_TEMPORAL / "scripts").glob("run_*.py"))


# --- 1. the task a `--pr` run is given ----------------------------------------

def test_a_PR_ALONE_yields_a_task_that_points_at_the_PR() -> None:
    """The substance, not merely that something non-empty came back.

    A placeholder sentence would satisfy "it returned a string" and leave the
    child with no idea where its work is. Each assertion below names a property
    the instruction must have for the run to be able to proceed at all.
    """
    text = build_act.task_text(BuildInput(pr_number="124"), Path("/nonexistent"))
    assert "124" in text, "the child must be told WHICH PR carries its runway"
    assert "gh pr view" in text, "…and how to fetch it"
    assert "comments" in text, (
        "…and that the runway is in the COMMENTS. The PR body carries the original "
        "brief; the review comment carries the findings this pass exists to close.")
    assert "${" not in text, (
        "this string is substituted into DESCRIPTION, which `render` treats as "
        "OPAQUE so an operator's task text cannot be re-scanned (issue #46). A "
        "`${...}` here would therefore reach the model literally.")


def test_the_PR_number_is_substituted_and_not_left_as_a_TEMPLATE() -> None:
    """`.format` on a template with the wrong field name fails silently-ish.

    Asserted against a DIFFERENT number from the docstring's example, so a
    hardcoded 124 anywhere in the chain cannot pass this.
    """
    text = build_act.task_text(BuildInput(pr_number="987"), Path("/nonexistent"))
    assert "987" in text and "{pr}" not in text


@pytest.mark.parametrize("kwargs,expected", [
    pytest.param({"description": "do the thing"}, "do the thing", id="description-wins"),
    pytest.param({"description": "do the thing", "pr_number": "9"}, "do the thing",
                 id="an-explicit-task-beats-the-PR-runway"),
])
def test_an_explicit_task_source_is_NOT_displaced_by_a_pr(kwargs, expected) -> None:
    """The relaxation must not quietly change what a fully-specified run does.

    An operator who supplies BOTH a description and `--pr` is correcting a PR with
    a specific new brief, and the brief must win. If `--pr` took precedence, every
    existing correction dispatch in the guide would silently start doing something
    else.
    """
    assert build_act.task_text(BuildInput(**kwargs), Path("/nonexistent")) == expected


@pytest.mark.parametrize("field,flag", [
    pytest.param("task_file", "--task-file", id="task-file-beats-the-PR-runway"),
    pytest.param("plan_path", "--phase", id="phase-beats-the-PR-runway"),
])
def test_a_FILE_task_source_also_beats_the_pr_runway(tmp_path, field, flag) -> None:
    """The other two sources, which the parametrization above could not reach.

    THE PRECEDENCE QUESTION IS NEW HERE AND THAT IS WHY IT NEEDS PINNING. Before
    `--pr` became a task source, `--task-file` + `--pr` was already a legal
    combination and `pr_number` was never consulted for text, so there was nothing
    to order. Making `--pr` sufficient created a real fork: the file and the PR
    thread can now BOTH claim to say what the run is for, and they can disagree.

    THE FILE WINS, DELIBERATELY. `PR_RUNWAY_TASK` is a DEFAULT — the thing to do
    when the operator said nothing else — not an override. An operator who passes
    both has narrowed the correction on purpose, and the child still reads the
    thread anyway: `fidelity_read_and_compare.md` makes `gh pr view --json
    body,comments` mandatory on every `--pr` run, so nothing is lost by the file
    taking the description slot. Documented in `docs/guide/workflows.md` § V2 for
    the operator, and asserted here so the two cannot drift.
    """
    source = tmp_path / "brief.md"
    source.write_text("the narrower brief")
    task = BuildInput(**{field: str(source)}, pr_number="9")

    text = build_act.task_text(task, tmp_path)
    assert text == "the narrower brief", (
        f"{flag} did not win over --pr. If this now returns the PR runway, an "
        f"existing dispatch that passes both has silently changed what it does.")
    assert "CORRECTION PASS on PR" not in text


def test_task_text_REFUSES_the_state_its_dataclass_refuses() -> None:
    """Defence in depth at the layer that would otherwise dispatch an empty task.

    Reached only if `BuildInput.__post_init__` is ever widened. It raises rather
    than returning "" so that widening surfaces here instead of as an empty PR.
    """
    empty = BuildInput.__new__(BuildInput)   # bypass __post_init__ deliberately
    object.__setattr__(empty, "description", None)
    for field in ("task_file", "plan_path", "pr_number", "repo_target"):
        object.__setattr__(empty, field, None)
    with pytest.raises(ValueError, match="no task source and no --pr"):
        build_act.task_text(empty, Path("/nonexistent"))


def _runners_building_a_build_input() -> list[Path]:
    """DERIVED FROM THE TREE. A third tier is covered when it is written."""
    return [p for p in _RUNNERS if "BuildInput(" in p.read_text()]


def test_the_derivation_found_the_build_runners() -> None:
    """VACUITY FLOOR for the parametrization below."""
    found = {p.name for p in _runners_building_a_build_input()}
    assert found == {"run_build.py", "run_build_minor.py"}, (
        f"the runners constructing a BuildInput are {sorted(found)}. If a tier was "
        f"added, extend the expectation; if one vanished, the check below is "
        f"asserting over less than it claims.")


@pytest.mark.parametrize("runner", _runners_building_a_build_input(),
                         ids=lambda p: p.name)
def test_a_build_entrypoint_ACCEPTS_pr_alone(runner: Path, capsys) -> None:
    """Driven through the real `parse_args`, which is where the rejection happened.

    `parse_args` converts the dataclass's ValueError into `parser.error`, so a
    unit test on `BuildInput` alone would not have seen the measured failure —
    that path exits the process. This drives the CLI.
    """
    module = __import__(runner.stem)
    task = module.parse_args(["--pr", "124", "--repo", "/opt/x"])
    assert task.pr_number == "124"
    assert not (task.description or task.task_file or task.plan_path)


@pytest.mark.parametrize("runner", _runners_building_a_build_input(),
                         ids=lambda p: p.name)
def test_a_build_entrypoint_STILL_REFUSES_a_dispatch_with_no_task_at_all(
        runner: Path) -> None:
    """CONTROL FOR THE TEST ABOVE. The relaxation must not become "anything goes".

    `--repo` alone is a run with a target and nothing to do, which is the empty-PR
    case the original rule was written for and the case it must still catch.
    """
    module = __import__(runner.stem)
    with pytest.raises(SystemExit):
        module.parse_args(["--repo", "/opt/x"])


# --- 2. the plan reaches the draft child --------------------------------------

def _draft_call_keywords(parent) -> set[str]:
    """The keyword names of the `run_draft*` call in a build parent, from its AST.

    READ FROM THE SOURCE rather than by monkeypatching and dispatching, because a
    dispatch reaches `worktree_add` and `gh` before it reaches the child. What is
    being asserted is a wiring fact and the source is where a wiring fact lives.
    """
    tree = ast.parse(inspect.getsource(parent))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and getattr(node.func, "attr", "").startswith("run_draft")):
            return {kw.arg for kw in node.keywords}
    return set()


@pytest.mark.parametrize("parent", [build_workflow, build_minor_workflow],
                         ids=["build", "build-minor"])
def test_both_tiers_hand_the_draft_child_the_PLAN_PATH(parent) -> None:
    """THE GUARD. Without it, `--phase` selects a prompt family that never runs."""
    keywords = _draft_call_keywords(parent)
    assert keywords, (
        f"no `run_draft*` call found in {parent.__name__} — the reader broke, and "
        f"an empty set would make the assertion below vacuous.")
    assert "plan_path" in keywords, (
        f"{parent.__name__} does not pass `plan_path` to its draft child, so a "
        f"`--phase` run silently gets the generic prompt instead of "
        f"`build_from_plan` / `stages_1_to_4_from_plan`, and `${{PLAN_PATH}}` "
        f"never reaches the model. Measured on the major tier, where the minor "
        f"tier had always passed it.")


@pytest.mark.parametrize("parent", [build_workflow, build_minor_workflow],
                         ids=["build", "build-minor"])
def test_the_reader_is_LOOKING_AT_the_call_it_claims_to_read(parent) -> None:
    """CONTROL ON THE READER, and it is the load-bearing one.

    `_draft_call_keywords` returns a set. If the AST walk matched the wrong node —
    or nothing — the test above would either be vacuous or assert about some other
    call. `description` is a keyword BOTH draft children have required since the
    family was written, so its presence proves the reader found the right call
    rather than merely finding something.
    """
    keywords = _draft_call_keywords(parent)
    assert {"description", "repo_root", "worktree"} <= keywords, (
        f"the reader returned {sorted(keywords)} for {parent.__name__}, which is "
        f"not the shape of a draft-child call. Fix the reader; the check above is "
        f"asserting against whatever this found.")


def test_the_reader_FINDS_NOTHING_in_a_module_with_no_draft_call() -> None:
    """The other half of the reader's control: it must not match indiscriminately."""
    assert not _draft_call_keywords(build_act), (
        "`_draft_call_keywords` matched something in build_activities.py, which "
        "dispatches no draft child. A reader that matches anything would make "
        "every assertion above pass for free.")

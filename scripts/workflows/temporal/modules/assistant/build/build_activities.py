"""External I/O for the build workflow — Layer 3.

Everything BUILD-SPECIFIC that touches the outside world lives here. The CI
reads that used to sit alongside `run_child` were promoted to
`assistant_activities` when their consumer count reached six across three
families (§10.1 rule 3) — a plan or research parent could not reach them here
without importing the build family, and four of them consequently dispatched
`review-pr` on a verdict nobody read. Under step 3 these gain
`@activity.defn` and nothing else changes; that is the whole reason for putting
them in their own module now rather than inlining them in the workflow.

IDEMPOTENCY WARNING, carried from the addendum (§A1). `run_child` is NOT
idempotent — the children it invokes push commits and open PRs. Under Temporal a
retry is therefore a NEW ATTEMPT, not a replay of the same work, and these must
be registered with a retry policy that reflects that. Do not let a default
policy silently re-run a child that already opened a PR.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .. import assistant_activities as shared
from .build_inputs import BuildInput, ChildResult


def run_child(script: Path, args: list[str], *, stream: bool = True) -> ChildResult:
    """Invoke a child workflow and capture its output.

    Streams to the operator's terminal while capturing, because the output is
    both a live progress signal and the handoff channel — the child's terminal
    line carries the PR URL or the verdict token.
    """
    if not script.exists():
        raise FileNotFoundError(f"child workflow not found: {script}")

    proc = subprocess.Popen(
        [str(script), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    captured: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        captured.append(line)
        if stream:
            sys.stdout.write(line)
            sys.stdout.flush()

    return ChildResult(exit_code=proc.wait(), output="".join(captured))


# PORTED AT THE MERGE WITH PHASE 2, WHICH EMPTIED THIS MODULE AROUND THEM.
# `ci_verdict`, `wait_for_ci` and `read_check_policy` moved to
# `assistant_activities`, and `POLICY_PATH`/`CiVerdict` to `routing`, so this
# file is no longer the build family's junk drawer. These two stayed: both are
# about turning an OPERATOR ARGUMENT into something a child can use, which is
# this module's remaining job and nobody else's.
# What a `--pr` run is told to do when the operator supplied no other task
# source. NOT a placeholder sentence: it is the instruction that makes `--pr`
# alone a complete dispatch, and it points at the copy of the runway every child
# in this family already reads.
#
# `${...}` IS DELIBERATELY NOT USED. This string is substituted into
# `DESCRIPTION`, which `render` treats as OPAQUE precisely so an operator's task
# text cannot be re-scanned for placeholders (issue #46). A `${PR}` in here would
# therefore reach the model literally.
#
# A STRING LITERAL AND NOT A `prompts/*.md`, RULED RATHER THAN DEFAULTED, because
# `workflow-scripts.md` § File Conventions says *"prompts live in files, never in
# string literals"* and this is the reasoning that says the rule does not reach
# here. THIS IS NOT A PROMPT — it is a TASK. It occupies the `DESCRIPTION` slot,
# the operator-content channel, and it is structurally the same thing an operator
# types on the command line or supplies via `--task-file`; nobody would file an
# operator's `--task-file` text under `prompts/`. It is never `render`ed, which is
# what the standard's rationale (diffable prose, brace hazards) is about. The
# concrete cost of moving it is also real rather than hypothetical: there is no
# `build/prompts/` today, and three fleet-wide guards enumerate `ASSISTANT.rglob(
# "prompts/*.md")` — `test_prompt_completeness`, `test_prompt_blocks_are_shared_
# not_copied` and `test_tier_siblings_do_not_DRIFT_by_a_sentence`, the last of
# which derives its minor/major tier pairing from those directories' names. A new
# prompts directory at the FAMILY level enters all three populations to relocate
# ten lines that are not a prompt.
PR_RUNWAY_TASK = (
    "This is a CORRECTION PASS on PR #{pr}, and the operator supplied no separate "
    "task because the task is already on the PR. READ IT THERE BEFORE ANYTHING "
    "ELSE:\n\n"
    "    gh pr view {pr} --json title,body,comments > /tmp/pr-{pr}.json\n\n"
    "then read that file. Do not use the bare invocation — it TRUNCATES silently "
    "on any PR with real review history, so the runway you were sent for is simply "
    "absent from the output with no error.\n\n"
    "The PR BODY carries the original brief. The most recent review or disposition "
    "COMMENT carries the runway — the specific findings this pass exists to close. "
    "Execute that runway.\n\n"
    "If the thread carries no runway at all, say so plainly and stop. Do not invent "
    "one: a correction pass with nothing to correct that rewrites the PR anyway is "
    "the failure this instruction exists to prevent."
)


def task_text(task: BuildInput, repo_root: Path) -> str:
    """The task statement this run executes, from whichever source supplied it.

    PROMOTED BECAUSE IT WAS BYTE-IDENTICAL IN BOTH PARENTS — §10.1 rule 3, consumer
    count decides. `build_workflow` and `build_minor_workflow` each held
    `task.description or Path(task.task_file or task.plan_path).read_text()`, and
    that one expression carried both defects this function exists to fix: it read
    the path against the CWD, and it assumed a task source always exists.

    HERE AND NOT IN `build_helper`, which is the more obvious home: that module's
    binding property is that it performs NO I/O, and this reads a file.
    """
    if task.description:
        return task.description
    if task.task_file:
        return shared.resolve_task_source(repo_root, task.task_file,
                                          "--task-file").read_text()
    if task.plan_path:
        return shared.resolve_task_source(repo_root, task.plan_path,
                                          "--phase").read_text()
    if task.pr_number:
        return PR_RUNWAY_TASK.format(pr=task.pr_number)
    # Unreachable through `BuildInput`, which refuses this combination at the
    # boundary. Raised rather than returning "" so a future widening of that rule
    # surfaces here instead of dispatching a child with an empty task.
    raise ValueError(
        "BuildInput carries no task source and no --pr; `__post_init__` should "
        "have refused it. Nothing was dispatched.")


def path_for_the_model(repo_root: Path, arg: str | None) -> str | None:
    """An operator PATH as the MODEL should see it — never a main-checkout path.

    NAMED FOR THE CLASS RATHER THAN FOR `--phase`, because the rule is about any
    path a parent RENDERS into a child's prompt and `plan_path` is merely the only
    one that does so today. `test_no_prompt_hands_the_model_a_MAIN_CHECKOUT_path.py`
    derives the set of rendered parameters from the children's own dict literals
    and requires each to arrive through this function, so a second one is caught
    the day it is wired rather than the day it misfires.

    THE DEFECT, verified by rendering the prompt rather than by reading it. The
    major tier began rendering `${PLAN_PATH}` on 2026-08-19 (before that the value
    never reached a prompt at all), and it rendered the RAW operator string. With
    `--repo /main/checkout --phase /main/checkout/docs/development/x/phase2.md`
    the child was handed

        Plan document: /main/checkout/docs/development/x/phase2.md

    while running inside `/tmp/wt`. The model then reads the MAIN CHECKOUT's copy
    of the plan doc rather than its branch's, so a correction pass on a branch that
    revised its own phase doc builds against the superseded spec, and any edit it
    makes to that doc lands outside the worktree and outside the PR. That is the
    class `test_model_gets_the_worktree_path.py` was written for — PR #84 and #86
    wrote papers into the main checkout this way — and that guard sweeps
    `modules/assistant/research/*/` only, so the build family's new render arrived
    uncovered.

    THE RULE: in-repo becomes REPO-RELATIVE, out-of-repo is passed verbatim.

      * A relative string resolves correctly wherever the model is standing, which
        is precisely why a relative `--phase` already worked. Handing the model the
        same relative form the operator could have typed is the whole fix.
      * A genuinely out-of-repo plan doc has no worktree-local copy to point at, and
        rewriting it would be inventing an answer. An ABSOLUTE one is passed through
        unchanged. This is NOT the unmade containment ruling: nothing here refuses
        anything, and `resolve_task_source`'s docstring still owns that question.
      * A RELATIVE argument that CLIMBS OUT (`--phase ../shared/notes.md`) is the
        third case, and "pass it verbatim" is wrong for it — which is this same
        defect one input over, found by review on the fix rather than on the
        original. `resolve_task_source` explicitly supports the input (*"a relative
        one that climbs out is resolved and read without complaint"*), and it is
        anchored at the REPO ROOT for reading — but a relative string rendered into
        a prompt is read from the WORKTREE, which is not a sibling of the repo. With
        `repo_root=/main/checkout` and `worktree=/tmp/wt`, `../shared/notes.md`
        would be opened as `/tmp/shared/notes.md` while the fleet anchored it at
        `/main/shared/notes.md`. So an escaping RELATIVE argument is rendered as its
        RESOLVED ABSOLUTE path: the one form that means the same thing from both
        directories.

    NOT `resolve_task_source`, WHICH IS THE ADJACENT AND WRONG HOME. That function
    answers "which file do I READ", and reading is correctly done against the
    resolved ABSOLUTE path — `task_text` calls it and must keep doing so. This one
    answers "which string do I SHOW the model", and the two answers differ by
    design. Both parents call this; neither spells the rule itself.
    """
    if not arg:
        return arg
    resolved = shared.anchor_task_source(repo_root, arg)
    try:
        # `repo_root.resolve()` on BOTH sides: `anchor_task_source` resolves, so
        # comparing against an unresolved root would report "outside the repo" for
        # every repo reached through a symlink — and the outside branch does not
        # relativise, which would silently be the un-anchored behaviour this exists
        # to remove.
        return str(resolved.relative_to(repo_root.resolve()))
    except ValueError:
        # OUTSIDE THE REPO. An absolute argument already means the same thing from
        # every directory, so it is passed through untouched. A RELATIVE one does
        # not — it was anchored at the repo root and the model reads from the
        # worktree — so it is rendered resolved. See the docstring's third bullet.
        return arg if Path(arg).is_absolute() else str(resolved)

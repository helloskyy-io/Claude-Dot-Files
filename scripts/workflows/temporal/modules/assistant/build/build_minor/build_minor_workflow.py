"""The build-minor parent — the light tier.

Identical sequence to `build`, with lighter children:

    draft-minor  ->  refine-minor  ->  review-pr  ->  [one loop-back]  ->  done

A parent calls no model. Every branch is a pure decision from the promoted
helper; every side effect is an activity or a child workflow.

WHY A SEPARATE PARENT RATHER THAN A FLAG ON `build`. The tiers differ in model,
turn cap and prompt substance — the minor prompts are self-contained where the
major ones compose shared blocks. A `--minor` flag would put those differences
inside conditionals in one file, which is the shape that produced 398 diverged
lines between the two bash tiers before the split. Two parents sharing one
promoted trio keeps the difference visible and the shared part single-sourced.
"""

from __future__ import annotations

from pathlib import Path

from .. import build_helper as helper
from ..build_activities import (path_for_the_model, task_text,
                                wait_for_ci)
from ..build_inputs import BuildInput, BuildResult, Verdict
from ..build_draft_minor import build_draft_minor_workflow as draft
from ..build_refine_minor import build_refine_minor_workflow as refine
from ... import assistant_activities as act
from ...review_pr import review_pr_workflow as review_pr
from ...review_pr.review_pr_helper import ReviewInput, ReviewType


def run_build_minor(task: BuildInput, repo_root: Path, worktree_name: str) -> BuildResult:
    """Draft, refine, disposition, and route on the verdict."""
    notes: list[str] = []
    description = task_text(task, repo_root)

    # ISOLATION IS ESTABLISHED ONCE, HERE. Children receive the path and never
    # create one — two children creating the same named worktree is a
    # `fatal: already exists` that killed the draft->refine handoff.
    ref = f"origin/{act.pr_branch(task.pr_number, repo_root)}" if task.pr_number else "HEAD"
    worktree = act.worktree_add(repo_root, worktree_name, ref)

    # Read BEFORE the child, for the reason its sibling parent states.
    slug = act.repo_slug(repo_root)

    # `path_for_the_model`, for the reason its sibling parent states at the
    # same call: what the model is SHOWN and what the fleet READS are two answers,
    # and an in-repo absolute `--phase` shown verbatim points outside this worktree.
    pr_url = draft.run_draft_minor(
        description=description, repo_root=repo_root,
        worktree=worktree, pr_number=task.pr_number,
        plan_path=path_for_the_model(repo_root, task.plan_path),
        verbose=task.verbose,
    )
    pr = helper.pr_number_from_url(pr_url, expected_repo=slug)

    loops = 0
    verdict = _refine_then_dispose(task, description, pr, repo_root,
                                   worktree, notes, correction=False)

    # Same bound as the major tier and for the same reason: self-correction
    # plateaus at roughly 3-5 passes, and past it the model justifies rather than
    # corrects. COUNTED from `helper.MAX_LOOPS`, never asserted — this note said
    # "looping back ONCE" while that bound has been 3 since `b89f7f5`.
    while helper.should_loop_back(verdict, loops):
        loops += 1
        notes.append(f"HOLD (redispatch): loop-back {loops} of {helper.MAX_LOOPS}."
                     + (" The last automated pass."
                        if loops == helper.MAX_LOOPS else ""))
        verdict = _refine_then_dispose(task, description, pr, repo_root, worktree,
                                       notes, correction=True,
                                       loops_left=helper.MAX_LOOPS - loops)

    if verdict is Verdict.HOLD_NEEDS_ASSISTANCE:
        notes.append("review-pr found an item only a human can rule on; no loop-back "
                     "was attempted, because more passes cannot produce a human decision.")
    elif verdict is Verdict.HOLD_REDISPATCH:
        notes.append(f"The automated loop is SPENT — {helper.MAX_LOOPS} "
                     f"loop-back(s) is the cap.")

    return BuildResult(pr_number=pr, pr_url=pr_url, verdict=verdict,
                       loops_used=loops, notes=notes)


def _refine_then_dispose(task: BuildInput, description: str, pr: str,
                         repo_root: Path, worktree: Path,
                         notes: list[str], *, correction: bool,
                         loops_left: int = 0) -> Verdict:
    ci_settled = wait_for_ci(pr, repo=task.repo_target)
    if not ci_settled:
        notes.append("CI had not settled before refine; the child was told so.")

    refine.run_refine_minor(
        description=description, pr_number=pr, repo_root=repo_root,
        worktree=worktree, correction_pass=correction, loops_left=loops_left,
        ci_unsettled=not ci_settled, verbose=task.verbose,
    )

    wait_for_ci(pr, repo=task.repo_target)
    result = review_pr.run_review(
        ReviewInput(pr_number=pr, repo_target=task.repo_target,
                    verbose=task.verbose, review_type=ReviewType.BUILD),
        repo_root,
    )
    notes.extend(result.notes)
    return Verdict(result.verdict.value)

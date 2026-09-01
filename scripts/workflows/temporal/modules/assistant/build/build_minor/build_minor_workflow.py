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
from ..build_activities import path_for_the_model, task_text
from ..build_inputs import BuildInput, BuildResult, Verdict
from ..build_draft_minor import build_draft_minor_workflow as draft
from ..build_refine_minor import build_refine_minor_workflow as refine
from ... import assistant_activities as act
from ...assistant_activities import ci_verdict, wait_for_ci
from ... import routing
from ...review_pr import review_pr_workflow as review_pr
from ...review_pr.review_pr_helper import ReviewInput, ReviewType


def _spend(repo_root, started) -> str:
    """What this run has cost so far, for a note at a decision point.

    NOT "this chain" — see `chain_cost_usd`. It sums every run logged since this
    parent started, so a concurrent dispatch is counted too. Over-reporting is
    the safe direction for a spend figure and the wording says so.
    """
    dollars, runs = act.chain_cost_usd(repo_root, started)
    if not runs:
        return ""
    return f" Spent since this run started: ${dollars:.2f} across {runs} run(s)."


def run_build_minor(task: BuildInput, repo_root: Path, worktree_name: str) -> BuildResult:
    """Draft, refine, disposition, and route on the verdict."""
    notes: list[str] = []
    started = act.clock_now()
    description = task_text(task, repo_root)

    # ISOLATION IS ESTABLISHED ONCE, HERE. Children receive the path and never
    # create one — two children creating the same named worktree is a
    # `fatal: already exists` that killed the draft->refine handoff.
    ref = act.base_ref(task.pr_number, repo_root)
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
                                   worktree, worktree_name, notes, correction=False)

    # Same bound as the major tier and for the same reason: self-correction
    # plateaus at roughly 3-5 passes, and past it the model justifies rather than
    # corrects. COUNTED from `helper.MAX_LOOPS`, never asserted — this note said
    # "looping back ONCE" while that bound has been 3 since `b89f7f5`.
    while helper.should_loop_back(verdict, loops):
        loops += 1
        notes.append(_spend(repo_root, started) + f"HOLD (redispatch): loop-back {loops} of {helper.MAX_LOOPS}."
                     + (" The last automated pass."
                        if loops == helper.MAX_LOOPS else ""))
        verdict = _refine_then_dispose(task, description, pr, repo_root, worktree,
                                       worktree_name, notes, correction=True,
                                       loops_left=helper.MAX_LOOPS - loops)

    if verdict is Verdict.HOLD_NEEDS_ASSISTANCE:
        # THIS NOTE STATES THE LOOP DECISION AND NOTHING ELSE, for the reason its
        # sibling `build/build_workflow.py` records at length: TWO paths return
        # this verdict and BOTH already wrote their own cause — the CI gate
        # appends a note ending "review-pr was NOT dispatched", and the review
        # path does `notes.extend(result.notes)`. A third sentence from here,
        # which detects neither, can only be a guess, and on PR #124 the guess
        # landed directly beneath the note saying review-pr had not run.
        notes.append(_spend(repo_root, started) + "No loop-back was attempted: more passes cannot produce a "
                     "human decision. The cause is in the note above.")
    elif verdict is Verdict.HOLD_REDISPATCH:
        notes.append(_spend(repo_root, started) + f"The automated loop is SPENT — {helper.MAX_LOOPS} "
                     f"loop-back(s) is the cap.")

    return BuildResult(pr_number=pr, pr_url=pr_url, verdict=verdict,
                       loops_used=loops, notes=notes)


def _refine_then_dispose(task: BuildInput, description: str, pr: str,
                         repo_root: Path, worktree: Path, worktree_name: str,
                         notes: list[str], *, correction: bool,
                         loops_left: int = 0) -> Verdict:
    ci_settled = wait_for_ci(pr, repo_root=repo_root)
    if not ci_settled:
        notes.append("CI had not settled before refine; the child was told so.")

    refine.run_refine_minor(
        description=description, pr_number=pr, repo_root=repo_root,
        worktree=worktree, correction_pass=correction, loops_left=loops_left,
        ci_unsettled=not ci_settled, verbose=task.verbose,
    )

    # THE SAME GATE ITS SIBLING RUNS, and it was absent here for six weeks. The
    # cascade landed in `build_workflow` alone and this parent was never updated,
    # so the light tier reached `review-pr` with the CI verdict never read and
    # could return MERGE on a red tree — the hole removing branch protection
    # opened, closed on one tier only. See `routing.ci_gate`.
    wait_for_ci(pr, repo_root=repo_root)
    verdict_state, extra = ci_verdict(pr, repo_root=repo_root)
    hold, gate_notes = routing.ci_gate(verdict_state, extra, pr=pr,
                                      repo_target=task.repo_target)
    notes.extend(gate_notes)
    if hold is not None:
        return hold

    # THREADED FROM THE RUN'S CONTEXT, NOT REBUILT. `run_review` cuts a
    # per-pass tree on the PR's branch and takes the run's own worktree name
    # as its stem, so the tree it makes is traceable to the run the bag
    # recorded. See `review_pr_workflow.run_review`.
    result = review_pr.run_review(
        ReviewInput(pr_number=pr, repo_target=task.repo_target,
                    verbose=task.verbose, review_type=ReviewType.BUILD),
        repo_root, worktree_name=worktree_name,
    )
    notes.extend(result.notes)
    return Verdict(result.verdict.value)

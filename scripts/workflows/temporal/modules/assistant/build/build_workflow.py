"""The build parent — Layer 1 orchestration.

A parent calls no model. It decides IF, WHEN and WHAT to call, and holds no
process code. Every branch is a pure decision from the helper; every side effect
is an activity or a child workflow.

    draft  ->  refine  ->  review-pr  ->  [one loop-back]  ->  done

Children are resolved as imports, not paths. Child-ness is a call-graph
property, not a location — `review_pr` is SHARED: several parents call it and it
stays independently dispatchable against any returned PR.

EXACTLY ONE loop-back. Not a knob, and deliberately not configurable.
Self-correction plateaus at roughly 3-5 passes: the same model carries the same
blind spots, and past the plateau it stops correcting and starts justifying.
Watched directly on this fleet -- one PR reached EIGHT review passes, and pass 8
reviewed the same tree as pass 7 with no commits between them.

Counting correction passes across the PIPELINE, not within any one child:

    refine = 1 . review-pr = 2 . [loop] refine = 3 . review-pr = 4

One loop-back lands at four, inside the band. Two would reach six, past it. Zero
would discard the passes that genuinely improve the work -- the plateau is a
ceiling, not an argument against the first climb.
"""

from __future__ import annotations

from pathlib import Path

from . import build_helper as helper
from .build_activities import wait_for_ci
from .build_inputs import BuildInput, BuildResult, Verdict
from ..review_pr import review_pr_workflow as review_pr
from ..review_pr.review_pr_helper import ReviewInput
from ..build_draft import build_draft_workflow as draft
from ..build_refine import build_refine_workflow as refine


def run_build(task: BuildInput, repo_root: Path, worktree_name: str) -> BuildResult:
    """Draft, refine, disposition, and route on the verdict."""
    notes: list[str] = []
    description = task.description or Path(task.task_file).read_text()

    # --- Step 1: DRAFT -----------------------------------------------------
    # The PR URL is both the handoff and the child's completion contract; the
    # child raises if it produced none, so `exit 0` cannot mean unfinished.
    pr_url = draft.run_draft(
        description=description, repo_root=repo_root, worktree_name=worktree_name,
        pr_number=task.pr_number, task_file=task.task_file, verbose=task.verbose,
    )
    pr = helper.pr_number_from_url(pr_url)

    # --- Steps 2 & 3: REFINE then DISPOSITION, with one bounded loop-back --
    loops = 0
    verdict = _refine_then_dispose(task, description, pr, repo_root,
                                   worktree_name, notes, correction=False)

    while helper.should_loop_back(verdict, loops):
        loops += 1
        notes.append("HOLD (redispatch): the runway closes with a scoped fix. "
                     "Looping back ONCE — this is the last automated pass.")
        verdict = _refine_then_dispose(task, description, pr, repo_root,
                                       worktree_name, notes, correction=True)

    if verdict is Verdict.HOLD_NEEDS_ASSISTANCE:
        notes.append("review-pr found at least one item only a human can rule on. No "
                     "loop-back was attempted: more passes cannot produce a human decision.")
    elif verdict is Verdict.HOLD_REDISPATCH:
        notes.append("The automated loop is SPENT — one loop-back is the cap, because "
                     "passes beyond it produce justification rather than correction.")

    return BuildResult(pr_number=pr, pr_url=pr_url, verdict=verdict,
                          loops_used=loops, notes=notes)


def _refine_then_dispose(task: BuildInput, description: str, pr: str,
                         repo_root: Path, worktree_name: str,
                         notes: list[str], *, correction: bool) -> Verdict:
    """One refine pass followed by one disposition pass."""
    ci_settled = wait_for_ci(pr, repo=task.repo_target)
    if not ci_settled:
        notes.append("CI had not settled before refine; the child was told so.")

    refine.run_refine(
        description=description, pr_number=pr, repo_root=repo_root,
        worktree_name=worktree_name, task_file=task.task_file,
        correction_pass=correction, ci_unsettled=not ci_settled, verbose=task.verbose,
    )

    wait_for_ci(pr, repo=task.repo_target)
    result = review_pr.run_review(
        ReviewInput(pr_number=pr, repo_target=task.repo_target, verbose=task.verbose),
        repo_root,
    )
    notes.extend(result.notes)
    return Verdict(result.verdict.value)

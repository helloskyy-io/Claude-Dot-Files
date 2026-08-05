"""The research parent.

    write  ->  verify  ->  review-pr  ->  [one loop-back]  ->  done

Same shape as `build`, different nouns. A parent calls no model; every branch is
a pure decision, every side effect a child or an activity.

WHAT THIS DECOMPOSITION FIXES, beyond resumability:

  * The synthesis was written by the run that wrote the papers, and NOTHING
    verified it — while §4 gives it a paper's full sourcing burden and makes it
    the only artifact the standup consumes.
  * §4's trace-to-all-dependents rule had no stage that executed it.
  * A research PR had no disposition at all. Roughly 36 candidates across three
    PRs were routed only because a human happened to discuss them.
"""

from __future__ import annotations

from pathlib import Path

from .. import research_activities as act
from ..research_write import research_write_workflow as write
from ..research_verify import research_verify_workflow as verify
from ...review_pr import review_pr_workflow as review_pr
from ...review_pr.review_pr_helper import ReviewInput, ReviewType, Verdict
from ...assistant_activities import extract_pr_url


MAX_LOOPS = 1


def run_research(*, research_dir: Path, repo_root: Path, worktree_name: str,
                 context: str = "", pr_number: str | None = None,
                 verbose: bool = False) -> dict:
    """Produce, verify, disposition. Returns a typed result."""
    notes: list[str] = []

    # Isolation once, at the parent. Children receive the path.
    ref = f"origin/{act.branch_of(pr_number, repo_root)}" if pr_number else "HEAD"
    worktree = act.worktree_add(repo_root, worktree_name, ref)

    pr_url = write.run_write(
        research_dir=research_dir, repo_root=repo_root, worktree=worktree,
        context=context, pr_number=pr_number, verbose=verbose,
    )
    pr = pr_url.rstrip("/").rsplit("/", 1)[-1]

    loops = 0
    verdict = _verify_then_dispose(research_dir, pr, repo_root, worktree,
                                   notes, verbose, correction=False)

    # ONE loop-back. Self-correction plateaus at 3-5 passes; past it the model
    # justifies rather than corrects. Counting across the pipeline:
    # verify=1 . review-pr=2 . [loop] verify=3 . review-pr=4.
    while verdict is Verdict.HOLD_REDISPATCH and loops < MAX_LOOPS:
        loops += 1
        notes.append("HOLD (redispatch): looping back ONCE — the last automated pass.")
        verdict = _verify_then_dispose(research_dir, pr, repo_root, worktree,
                                       notes, verbose, correction=True)

    if verdict is Verdict.HOLD_NEEDS_ASSISTANCE:
        notes.append("review-pr found an item only a human can rule on; no loop-back "
                     "was attempted, because more passes cannot produce a human decision.")
    elif verdict is Verdict.HOLD_REDISPATCH:
        notes.append("The automated loop is SPENT — one loop-back is the cap.")

    return {"pr_number": pr, "pr_url": pr_url, "verdict": verdict,
            "loops_used": loops, "notes": notes}


def _verify_then_dispose(research_dir: Path, pr: str, repo_root: Path,
                         worktree: Path, notes: list[str], verbose: bool,
                         *, correction: bool) -> Verdict:
    verify.run_verify(
        research_dir=research_dir, pr_number=pr, repo_root=repo_root,
        worktree=worktree, correction_pass=correction, verbose=verbose,
    )
    # --type research: candidates are CARGO, not findings. A clean research PR
    # returns MERGE with zero findings, and that is the expected outcome.
    result = review_pr.run_review(
        ReviewInput(pr_number=pr, verbose=verbose, review_type=ReviewType.RESEARCH),
        repo_root,
    )
    notes.extend(result.notes)
    return result.verdict

"""The research-refresh parent.

    [free date gate]  ->  refresh  ->  verify  ->  review-pr  ->  [one loop-back]

Children 2 and 3 are SHARED with `research` unchanged — the fork-vs-parameterize
question resolved by evidence: one differing produce child, two shared.
"""

from __future__ import annotations

from pathlib import Path

from .. import research_activities as act
from ..research_refresh import research_refresh_workflow as refresh
from ..research_verify import research_verify_workflow as verify
from ...review_pr import review_pr_workflow as review_pr
from ...review_pr.review_pr_helper import ReviewInput, ReviewType, Verdict

MAX_LOOPS = 1


def run_research_refresh(*, research_dir: Path, repo_root: Path,
                         worktree_name: str, verbose: bool = False) -> dict:
    """Revalidate due papers, verify, disposition."""
    # THE GATE IS FREE. Nothing due means no model spend at all — the property
    # that makes this cron-able where `research` never could be.
    due = refresh.due_papers(research_dir)
    if not due:
        return {"verdict": None, "notes": [f"No papers due in {research_dir} — clean no-op."],
                "due": 0, "pr_url": None}

    notes = [f"{len(due)} paper(s) due: " + ", ".join(p.name for p in due)]
    worktree = act.worktree_add(repo_root, worktree_name, "HEAD")

    pr_url = refresh.run_refresh(research_dir=research_dir, repo_root=repo_root,
                                 worktree=worktree, due=due, verbose=verbose)
    pr = pr_url.rstrip("/").rsplit("/", 1)[-1]

    loops = 0
    verdict = _verify_then_dispose(research_dir, pr, repo_root, worktree, notes, verbose, False)
    while verdict is Verdict.HOLD_REDISPATCH and loops < MAX_LOOPS:
        loops += 1
        notes.append("HOLD (redispatch): looping back ONCE — the last automated pass.")
        verdict = _verify_then_dispose(research_dir, pr, repo_root, worktree, notes, verbose, True)

    return {"pr_number": pr, "pr_url": pr_url, "verdict": verdict,
            "loops_used": loops, "due": len(due), "notes": notes}


def _verify_then_dispose(research_dir, pr, repo_root, worktree, notes, verbose, correction):
    verify.run_verify(research_dir=research_dir, pr_number=pr, repo_root=repo_root,
                      worktree=worktree, correction_pass=correction, verbose=verbose)
    result = review_pr.run_review(
        ReviewInput(pr_number=pr, verbose=verbose, review_type=ReviewType.RESEARCH), repo_root)
    notes.extend(result.notes)
    return result.verdict

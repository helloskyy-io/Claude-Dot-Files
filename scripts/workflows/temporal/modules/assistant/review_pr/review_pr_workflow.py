"""The review-pr disposition engine — Layer 1 orchestration.

DECIDE-ONLY. It merges nothing, closes nothing, fixes nothing, dispatches
nothing. Its output is one disposition comment plus a terminal VERDICT line —
plus the single write authority it holds: filing GitHub Issues for qualifying
deferred work. That exception exists because it is the only actor with no scope
of its own to offload; everything else stays decide-only.

    gather → render → dispose → verdict

Every decision below comes from the helper; every side effect is an activity.
"""

from __future__ import annotations

from pathlib import Path

from . import review_pr_activities as act
from . import review_pr_helper as helper
from .review_pr_helper import ReviewInput, ReviewResult, ReviewType

_HERE = Path(__file__).resolve().parent
_BASH_FLEET = _HERE.parents[3]

# Single-consumer prompt: stays in this workflow's folder per §10.1 rule 3.
PROMPT_PATH = _HERE / "prompts" / "disposition.md"

# Shared fragment: several workflows use it, so it promotes to a parent level
# once the second consumer ports. Read from the bash original until then.
SHARED_PROMPTS = _BASH_FLEET / "common" / "shared-prompts.sh"


def run_review(task: ReviewInput, worktree: Path) -> ReviewResult:
    """Disposition one PR and return its typed verdict."""
    notes: list[str] = []

    if task.review_type is not ReviewType.BUILD:
        # Commit 2 wires the type-specific criteria. Until then, say so out loud
        # rather than silently applying build criteria to a research PR — which
        # is the failure that cost another repo nine days on a research PR.
        notes.append(
            f"--type {task.review_type.value} was requested but type-specific "
            f"criteria are not yet implemented; BUILD criteria were applied."
        )

    pr = act.fetch_pr(task.pr_number, worktree)
    this_pass, prior_pass = helper.pass_numbers(
        act.count_prior_passes(task.pr_number, worktree)
    )

    prompt = helper.render_prompt(
        act.load_prompt(PROMPT_PATH),
        pr_number=task.pr_number,
        pr_branch=pr["headRefName"],
        this_pass=this_pass,
        prior_pass=prior_pass,
        headless_guard=act.load_shared_block("HEADLESS_EXECUTION_GUARD", SHARED_PROMPTS),
    )

    output = act.run_disposition(
        prompt, worktree, helper.MODEL_KEY, helper.COMPLETION_PATTERN, task.verbose
    )

    verdict, parseable = helper.parse_verdict(output)
    if not parseable:
        notes.append(
            f"review-pr produced no parseable VERDICT line on PR #{task.pr_number}. "
            f"Routed to needs-assistance — inspect by hand."
        )

    return ReviewResult(
        pr_number=task.pr_number, verdict=verdict, this_pass=this_pass,
        parseable=parseable, notes=notes,
    )

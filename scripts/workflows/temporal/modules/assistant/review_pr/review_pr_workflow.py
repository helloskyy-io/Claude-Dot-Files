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

import time
from pathlib import Path

from . import review_pr_activities as act
from . import review_pr_helper as helper
from .review_pr_helper import ReviewInput, ReviewResult, ReviewType

_HERE = Path(__file__).resolve().parent
_BASH_FLEET = _HERE.parents[3]

# Single-consumer prompt: stays in this workflow's folder per §10.1 rule 3.
PROMPTS = _HERE / "prompts"
PROMPT_PATH = PROMPTS / "disposition.md"

# The prompt is ASSEMBLED, not branched. Core + universal addenda + exactly one
# type-criteria file. This is what the port bought: a mode is a different file,
# not an `if` inside a 43KB string. Adding a fourth type means adding one file.
CORE_ADDENDA = ["core_corpus_rule.md"]

# Shared fragment: several workflows use it, so it promotes to a parent level
# once the second consumer ports. Read from the bash original until then.
SHARED_PROMPTS = _BASH_FLEET / "common" / "shared-prompts.sh"


def assemble_prompt(review_type: ReviewType) -> str:
    """Core + universal addenda + exactly ONE type-criteria file.

    Both the real path and --dry-run call this. An earlier version rendered only
    the core in the dry run, so every type produced an identical byte count and
    the dry run could not have detected a broken assembly — the same shape as the
    bug where a render-only check missed a path resolved at invocation time.
    """
    criteria = PROMPTS / f"criteria_{review_type.value}.md"
    if not criteria.exists():
        raise FileNotFoundError(
            f"no criteria file for --type {review_type.value}: {criteria}. "
            f"A review type without criteria would silently apply another type's."
        )
    return "\n\n".join(
        [act.load_prompt(PROMPT_PATH)]
        + [act.load_prompt(PROMPTS / a) for a in CORE_ADDENDA]
        + [act.load_prompt(criteria)]
    )


def run_review(task: ReviewInput, worktree: Path) -> ReviewResult:
    """Disposition one PR and return its typed verdict."""
    notes: list[str] = []

    pr = act.fetch_pr(task.pr_number, worktree)
    this_pass, prior_pass = helper.pass_numbers(
        act.count_prior_passes(task.pr_number, worktree)
    )

    # CAP (binding): exactly two things vary by type — the scope boundary and
    # the blocking-defect checklist — and both live in the criteria file. Type
    # MUST NOT be consulted anywhere else in this workflow. Without that cap the
    # fourth type gets added by copy-pasting a branch, which reproduces the
    # 398-diverged-lines problem inside one file where it is harder to see.
    assembled = assemble_prompt(task.review_type)
    notes.append(f"Reviewed as --type {task.review_type.value}.")

    prompt = helper.render_prompt(
        assembled,
        pr_number=task.pr_number,
        pr_branch=pr["headRefName"],
        this_pass=this_pass,
        prior_pass=prior_pass,
        headless_guard=act.load_shared_block("HEADLESS_EXECUTION_GUARD", SHARED_PROMPTS),
    )

    # The reviewer must read the PR's branch, not the repo's checkout.
    pr_tree = _shared.worktree_add(
        worktree, f"review-pr-{task.pr_number}-{int(time.time())}",
        f"origin/{pr['headRefName']}",
    )
    output = act.run_disposition(
        prompt, worktree, helper.MODEL_KEY, helper.COMPLETION_PATTERN,
        worktree=pr_tree, verbose=task.verbose,
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

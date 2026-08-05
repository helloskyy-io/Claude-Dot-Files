"""The revision parent — Layer 1 orchestration.

A parent calls no model. It decides IF, WHEN and WHAT to call, and holds no
process code. Every branch below is a pure decision from the helper; every side
effect is an activity. Nothing in this module does I/O directly, which is what
makes it eligible to become a `@workflow.defn` unchanged.

    draft  ->  refine  ->  review-pr  ->  [one loop-back]  ->  done

EXACTLY ONE loop-back. Not a tuning knob, and deliberately not configurable.
Self-correction plateaus at roughly 3-5 passes: the same model carries the same
blind spots, and past the plateau it stops correcting and starts justifying.
Watched directly on this fleet -- one PR reached EIGHT review passes, and pass 8
reviewed the same tree as pass 7 with no commits between them, re-issuing the
same runway.

Counting correction passes across the PIPELINE rather than within any one child:

    refine = 1 . review-pr = 2 . [loop] refine = 3 . review-pr = 4

One loop-back lands at four, inside the band. Two would reach six, past it. Zero
would discard the passes that genuinely do improve the work -- the plateau is a
ceiling, not an argument against the first climb. The bound comes from the
research, not from a budget guard, and a knob would only invite tuning past the
point where extra passes produce justification instead of correction.
"""

from __future__ import annotations

from pathlib import Path

from . import revision_helper as helper
from .revision_activities import run_child, wait_for_ci
from .revision_inputs import RevisionInput, RevisionResult, Verdict

# Children are resolved by name, not by folder tier -- child-ness is a call graph
# property, not a location. `review_pr` is SHARED: several parents call it, and it
# is independently dispatchable against any returned PR.
_BASH_FLEET = Path(__file__).resolve().parents[5]
DRAFT = _BASH_FLEET / "children" / "revision-draft.sh"
REFINE = _BASH_FLEET / "children" / "revision-refine.sh"
REVIEW_PR = _BASH_FLEET / "children" / "review-pr.sh"


def run_revision(task: RevisionInput) -> RevisionResult:
    """Draft, refine, disposition, and route on the verdict."""
    notes: list[str] = []

    # --- Step 1: DRAFT -----------------------------------------------------
    # The child's terminal PR URL IS the handoff and IS its completion contract.
    # draft_handoff raises with the operator-facing reason if either fails.
    draft = run_child(DRAFT, helper.draft_args(task))
    pr_url = helper.draft_handoff(draft)
    pr = helper.pr_number_from_url(pr_url)

    # --- Step 2: REFINE (fresh context, same task, against the draft's PR) --
    ci_settled = wait_for_ci(pr, repo=task.repo_target)
    if not ci_settled:
        notes.append("CI had not settled before refine; the child was told so.")

    refined = run_child(
        REFINE,
        helper.refine_args(task, pr, correction_pass=False, ci_unsettled=not ci_settled),
    )
    if not refined.ok:
        raise RuntimeError(
            f"revision-refine FAILED on PR #{pr}. The PR EXISTS and is UNREVIEWED — "
            f"it must not be merged as-is. Re-run just the review step:\n"
            f"    {REFINE} --pr {pr} <the same task>"
        )

    # --- Step 3: DISPOSITION, then route -----------------------------------
    verdict, loops = _disposition(task, pr, notes), 0

    while helper.should_loop_back(verdict, loops):
        loops += 1
        notes.append("HOLD (redispatch): the runway closes with a scoped fix. "
                     "Looping back ONCE — this is the last automated pass.")

        ci_settled = wait_for_ci(pr, repo=task.repo_target)
        corrected = run_child(
            REFINE,
            helper.refine_args(task, pr, correction_pass=True, ci_unsettled=not ci_settled),
        )
        if not corrected.ok:
            raise RuntimeError(f"revision-refine FAILED on the correction pass for PR #{pr}.")

        verdict = _disposition(task, pr, notes)

    if verdict is Verdict.HOLD_NEEDS_ASSISTANCE:
        notes.append(
            "review-pr found at least one item only a human can rule on. No loop-back "
            "was attempted: more passes cannot produce a human decision."
        )
    elif verdict is Verdict.HOLD_REDISPATCH:
        notes.append(
            "The automated loop is SPENT — one loop-back is the cap, because passes "
            "beyond it produce justification rather than correction. This PR needs you."
        )

    return RevisionResult(
        pr_number=pr, pr_url=pr_url, verdict=verdict, loops_used=loops, notes=notes
    )


def _disposition(task: RevisionInput, pr: str, notes: list[str]) -> Verdict:
    """Run review-pr and parse its routing token."""
    reviewed = run_child(REVIEW_PR, helper.review_args(task, pr))
    if not reviewed.ok:
        raise RuntimeError(
            f"review-pr FAILED on PR #{pr}. The PR was drafted and refined but NOT "
            f"dispositioned. Run it by hand:\n    {REVIEW_PR} --pr {pr}"
        )

    verdict, parseable = helper.parse_verdict(reviewed.output)
    if not parseable:
        notes.append(
            f"review-pr produced no parseable VERDICT line on PR #{pr}. "
            f"Routed to needs-assistance — inspect by hand."
        )
    return verdict

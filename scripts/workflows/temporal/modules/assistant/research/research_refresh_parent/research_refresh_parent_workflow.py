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
from ... import routing
from ...assistant_activities import ci_verdict, repo_slug, wait_for_ci

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
    # THE ELEVENTH CALL SITE, and the one the first sweep of this missed —
    # it passes its base INLINE rather than through a `ref = ...` line, so a
    # guard keyed on the assignment could not see it. This parent takes no
    # `--pr` at all (a refresh always opens its own PR), so the base is
    # unconditionally the default branch.
    worktree = act.worktree_add(repo_root, worktree_name,
                                act.base_ref(None, repo_root))

    # Read BEFORE the child, for the reason its sibling parent states.
    slug = repo_slug(repo_root)

    pr_url = refresh.run_refresh(research_dir=research_dir, repo_root=repo_root,
                                 worktree=worktree, due=due, verbose=verbose)
    # THROUGH THE OWNER, not a string split — see the sibling parent. This is
    # the same expression, and the phase doc that found it named only one of the
    # two, which is why the gate below it is on the SHAPE and not on the sites.
    pr = routing.pr_number_from_url(pr_url, expected_repo=slug)

    loops = 0
    verdict = _verify_then_dispose(research_dir, pr, repo_root, worktree, notes, verbose, False)
    while verdict is Verdict.HOLD_REDISPATCH and loops < MAX_LOOPS:
        loops += 1
        notes.append("HOLD (redispatch): looping back ONCE — the last automated pass.")
        verdict = _verify_then_dispose(research_dir, pr, repo_root, worktree, notes, verbose, True)

    # THE LOOP DECISION AND NOTHING ELSE, and until the CI gate was wired above
    # this parent said nothing at all — a run could end HOLD_NEEDS_ASSISTANCE
    # with no note explaining why no loop-back was tried. TWO paths reach this
    # verdict and both already wrote their own cause: the gate appends a note
    # ending "review-pr was NOT dispatched", and the review path does
    # `notes.extend(result.notes)`. A third sentence from here would be a guess.
    if verdict is Verdict.HOLD_NEEDS_ASSISTANCE:
        notes.append("No loop-back was attempted: more passes cannot produce a "
                     "human decision. The cause is in the note above.")
    elif verdict is Verdict.HOLD_REDISPATCH:
        # THE OTHER HALF OF THE SAME OMISSION. A run that exhausted its one
        # loop-back left the operator with a HOLD and no sentence saying the
        # automated budget was gone, while both sibling research parents say it
        # in these exact words. `MAX_LOOPS` really is 1 here, so the flat wording
        # is true rather than asserted — see `test_loop_cap_prose_is_counted`.
        notes.append("The automated loop is SPENT — one loop-back is the cap.")

    return {"pr_number": pr, "pr_url": pr_url, "verdict": verdict,
            "loops_used": loops, "due": len(due), "notes": notes}


def _verify_then_dispose(research_dir, pr, repo_root, worktree, notes, verbose, correction):
    verify.run_verify(research_dir=research_dir, pr_number=pr, repo_root=repo_root,
                      worktree=worktree, correction_pass=correction, verbose=verbose)

    # --- THE GATE: the parent reads the verdict, so MERGE is unreachable on red
    # THE SAME CASCADE THE BUILD PARENTS RUN — `routing.ci_gate`, pure, six
    # consumers. It was absent from this family because it lived under `build/`
    # and reaching it from here would have been a layering inversion, so this
    # parent dispatched `review-pr` with the CI verdict never read and could
    # return MERGE on a red tree.
    #
    # A MARKDOWN-ONLY PR IS NOT AN UNGATED ONE. This repo's `tests.yml` carries
    # no `paths:` filter by deliberate choice, and the suite greps prompts and
    # docs, so a research edit can and does turn the tree red.
    #
    # `repo_root=repo_root` ON BOTH, and the parameter is REQUIRED rather than
    # merely conventional: omitting it used to make every read degrade to "this
    # repo declares no gate", so the gate was present and forgave everything.
    # That omission was live in `build_minor` until PR #124; the default was
    # dropped on 2026-08-20 so the degrade path no longer exists.
    wait_for_ci(pr, repo_root=repo_root)
    verdict_state, extra = ci_verdict(pr, repo_root=repo_root)
    hold, gate_notes = routing.ci_gate(verdict_state, extra, pr=pr, repo_target=None)
    notes.extend(gate_notes)
    if hold is not None:
        return hold

    result = review_pr.run_review(
        ReviewInput(pr_number=pr, verbose=verbose, review_type=ReviewType.RESEARCH), repo_root)
    notes.extend(result.notes)
    return result.verdict

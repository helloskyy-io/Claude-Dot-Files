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
from ..research_draft import research_draft_workflow as draft
from ..research_refine import research_refine_workflow as verify
from ...review_pr import review_pr_workflow as review_pr
from ...review_pr.review_pr_helper import ReviewInput, ReviewType, Verdict
from ...assistant_activities import (ci_verdict, extract_pr_url, repo_slug,
                                     wait_for_ci)
from ... import routing


MAX_LOOPS = 1


def run_research(*, research_dir: Path, repo_root: Path, worktree_name: str,
                 context: str = "", pr_number: str | None = None,
                 verbose: bool = False) -> dict:
    """Produce, verify, disposition. Returns a typed result."""
    notes: list[str] = []

    # Isolation once, at the parent. Children receive the path.
    ref = act.base_ref(pr_number, repo_root)
    worktree = act.worktree_add(repo_root, worktree_name, ref)

    # Read BEFORE the child, so a `gh` failure costs a dispatch that has
    # produced nothing rather than one that has already written a paper.
    slug = repo_slug(repo_root)

    pr_url = draft.run_research_draft(
        research_dir=research_dir, repo_root=repo_root, worktree=worktree,
        context=context, pr_number=pr_number, verbose=verbose,
    )
    # THROUGH THE OWNER, not a string split. `rstrip("/").rsplit("/", 1)[-1]`
    # is the PR-URL parse with NO validation whatsoever — it returns the last
    # path segment of whatever it is handed, so a child that printed a bare
    # sentence yields a word and it reaches `gh` as a PR number.
    pr = routing.pr_number_from_url(pr_url, expected_repo=slug)

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
        # THE LOOP DECISION AND NOTHING ELSE. Wiring the CI gate above gave this
        # parent a SECOND path to this verdict, and the gate writes its own cause
        # ending "review-pr was NOT dispatched" — so the old sentence here,
        # "review-pr found an item only a human can rule on", now lands directly
        # beneath a note saying review-pr never ran. That exact contradiction was
        # measured on PR #124 in the build family, and it cost a log sweep to tell
        # UNREVIEWED from reviewed-and-held. The layer that DETECTS a condition
        # reports it; this layer detects neither.
        notes.append("No loop-back was attempted: more passes cannot produce a "
                     "human decision. The cause is in the note above.")
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

    # --type research: candidates are CARGO, not findings. A clean research PR
    # returns MERGE with zero findings, and that is the expected outcome.
    result = review_pr.run_review(
        ReviewInput(pr_number=pr, verbose=verbose, review_type=ReviewType.RESEARCH),
        repo_root,
    )
    notes.extend(result.notes)
    return result.verdict

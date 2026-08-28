"""`plan` — the planning PARENT for ONE component, research through disposition.

WHAT IT IS FOR. A component that already exists and already has a plan needs
that plan re-checked, re-sized and reconciled onto the sprint. Before this
existed there was no parent that did it: `plan_project` chains the same children
but takes no component argument — it triages the candidate store, scaffolds NEW
components and plans only those — so a re-plan of an existing component meant
dispatching four children by hand, in order, eight times over one PR. That is
what this replaces.

WHY A PARENT AND NOT A LONGER CHILD. The chain's value is that each link reads
what the previous one wrote WITHOUT its context: `plan-verify` judges a plan it
did not author, and `review-pr` disposes a PR it did not write. Collapsing them
into one run would make the judge share the producer's context, which is the one
thing the split exists to prevent — the same argument that keeps
`research-verify` and `build-refine` separate runs.

THE STEP ORDER IS NOT STYLISTIC AND IS RECORDED IN THE CHILDREN THEMSELVES.
`plan-verify` must run before `plan-sprint`, because `plan_sprint_workflow`'s own
docstring records the defect that ordering fixes — *"the sprint plan used to be
updated BEFORE anything estimated the work, so its hour totals landed ahead of
the estimates they depend on."* This parent cannot express the wrong order.

THE LOOP RE-RUNS THE CORRECTION AND THE JUDGEMENT, NEVER THE AUTHORING — the
same shape every other parent in this fleet uses. `plan-write` drafts once; a
HOLD loops back through `plan-write --pr`, `plan-verify` and `plan-sprint`
because a correction that edits a roadmap changes what must be sized and what
must be totalled, and re-entering below those two lands phase edits that nothing
re-sizes and nothing re-totals. That is not hypothetical: it is `C-umoesnbh`,
measured in both repos on 2026-08-28, and it is why `review-pr`'s disposition
table now names all three children in order rather than a single revision tool.
"""

from __future__ import annotations

from pathlib import Path

from ... import assistant_activities as act
from ... import routing
from ...assistant_activities import ci_verdict, wait_for_ci
from ...review_pr import review_pr_workflow as review_pr
from ...review_pr.review_pr_helper import ReviewInput, ReviewType
from ..plan_feature import plan_feature_workflow as plan_write
from ..plan_sprint import plan_sprint_workflow as sprint
from ..plan_verify import plan_verify_workflow as plan_verify


def run_plan(*, component: Path, repo_root: Path, worktree_name: str,
             sprint_path: Path, candidates_path: Path,
             context: str = "", pr_number: str | None = None,
             repo_target: str | None = None,
             verbose: bool = False) -> tuple[str, routing.Verdict, list[str]]:
    """Plan ONE component end to end. Returns (pr_url, verdict, notes).

    THE PARENT ESTABLISHES ISOLATION ONCE AND PASSES IT DOWN — a child never
    cuts its own worktree. Taking a NAME rather than a path is what makes that
    true here: the four children below all receive the same `worktree`, so they
    read what the previous one wrote, and a child handed a path could not be
    given a different one by accident.
    """
    notes: list[str] = []
    pr = pr_number
    ref = act.base_ref(pr_number, repo_root)
    worktree = act.worktree_add(repo_root, worktree_name, ref)

    # --- Step 1: WRITE the plan (or correct it, when handed a PR) -----------
    # EACH CHILD RETURNS ITS OWN PR URL. The first call is what opens the PR
    # when none was given, so its return value is the only place the number
    # exists — `plan-project` resolves it the same way, one line after its own
    # first child.
    pr_url = plan_write.run_plan_feature(
        repo_root=repo_root, worktree=worktree, component=component,
        candidates_path=candidates_path, pr_number=pr,
        context=context, verbose=verbose,
    )
    if pr is None:
        pr = routing.pr_number_from_url(pr_url, expected_repo=repo_target)
        notes.append(f"plan-write opened PR #{pr}.")

    verdict = _verify_size_and_dispose(
        component=component, repo_root=repo_root, worktree=worktree,
        sprint_path=sprint_path, candidates_path=candidates_path, pr=pr,
        repo_target=repo_target, notes=notes, verbose=verbose,
    )

    # --- Step 2: the bounded loop-back --------------------------------------
    # THE WHOLE CHAIN BELOW THE AUTHOR, never one child. See the module
    # docstring: re-entering below `plan-verify` lands roadmap edits that
    # nothing re-sizes and nothing re-totals.
    loops = 0
    while routing.should_loop_back(verdict, loops):
        loops += 1
        notes.append(f"HOLD (redispatch): loop-back {loops} of {routing.MAX_LOOPS}.")
        plan_write.run_plan_feature(
            repo_root=repo_root, worktree=worktree, component=component,
            candidates_path=candidates_path, pr_number=pr,
            context=context, verbose=verbose,
        )
        verdict = _verify_size_and_dispose(
            component=component, repo_root=repo_root, worktree=worktree,
            sprint_path=sprint_path, candidates_path=candidates_path, pr=pr,
            repo_target=repo_target, notes=notes, verbose=verbose,
        )

    # THE LOOP DECISION AND NOTHING ELSE — the loop is the only thing this
    # function knows. Both paths to NEEDS_ASSISTANCE already wrote their own
    # cause: the CI gate appends a note ending "review-pr was NOT dispatched",
    # and the review path carries `review-pr`'s own explanation through
    # `notes.extend(result.notes)`. A third sentence guessing WHY would land
    # directly beneath one of those and contradict it — measured on PR #124 in
    # the build family, where it cost a log sweep to tell UNREVIEWED from
    # reviewed-and-held.
    if verdict is routing.Verdict.HOLD_NEEDS_ASSISTANCE:
        notes.append("No loop-back was attempted: more passes cannot produce a "
                     "human decision. The cause is in the note above.")
    elif verdict is routing.Verdict.HOLD_REDISPATCH:
        notes.append(f"The automated loop is SPENT — {routing.MAX_LOOPS} loop-back(s) "
                     f"is the cap. What remains needs a human or a scoped redispatch.")

    return pr_url, verdict, notes


def _verify_size_and_dispose(*, component: Path, repo_root: Path, worktree: Path,
                             sprint_path: Path, candidates_path: Path, pr: str,
                             repo_target: str | None, notes: list[str],
                             verbose: bool) -> routing.Verdict:
    """`plan-verify` -> `plan-sprint` -> CI gate -> `review-pr`, as one unit.

    ONE UNIT BECAUSE THE LOOP RE-RUNS ALL OF IT. A correction changes what must
    be sized, which changes what must be totalled, which changes what the
    reviewer is judging. Splitting them into separately-looped stages would let a
    review nitpick skip the re-size that its own fix invalidated.
    """
    plan_verify.run_plan_verify(
        repo_root=repo_root, worktree=worktree, component=component,
        candidates_path=candidates_path, pr_number=pr, verbose=verbose,
    )
    sprint.run_plan_sprint(
        repo_root=repo_root, worktree=worktree, sprint_path=sprint_path,
        component=component, pr_number=pr, verbose=verbose,
    )

    # THE GATE: the parent reads the verdict, so MERGE is unreachable on red.
    # A planning PR edits markdown and this repo's `tests.yml` carries NO
    # `paths:` filter — the suite greps prompts, docs and `config.yaml` — so a
    # markdown-only diff can and does turn the tree red.
    wait_for_ci(pr, repo_root=repo_root)
    verdict_state, extra = ci_verdict(pr, repo_root=repo_root)
    hold, gate_notes = routing.ci_gate(verdict_state, extra, pr=pr,
                                       repo_target=repo_target)
    notes.extend(gate_notes)
    if hold is not None:
        return hold

    result = review_pr.run_review(
        ReviewInput(pr_number=pr, repo_target=repo_target,
                    review_type=ReviewType.PLANNING, verbose=verbose),
        repo_root,
    )
    notes.extend(result.notes)
    return result.verdict

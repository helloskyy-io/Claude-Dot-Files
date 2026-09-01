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

from .. import build_helper as helper
from ..build_activities import path_for_the_model, task_text
from ..build_inputs import BuildInput, BuildResult, Verdict
from ... import assistant_activities as act
from ...assistant_activities import ci_verdict, wait_for_ci
from ... import routing
from ...review_pr import review_pr_workflow as review_pr
from ...review_pr.review_pr_helper import ReviewInput
from ..build_draft import build_draft_workflow as draft
from ..build_refine import build_refine_workflow as refine
from ..build_refine_minor import build_refine_minor_workflow as refine_minor


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


def run_build(task: BuildInput, repo_root: Path, worktree_name: str) -> BuildResult:
    """Draft, refine, disposition, and route on the verdict."""
    notes: list[str] = []
    started = act.clock_now()
    description = task_text(task, repo_root)

    # ISOLATION IS ESTABLISHED ONCE, HERE. Children receive the path and never
    # create one — two children creating the same named worktree is a
    # `fatal: already exists` that killed the draft->refine handoff.
    ref = act.base_ref(task.pr_number, repo_root)
    worktree = act.worktree_add(repo_root, worktree_name, ref)

    # READ BEFORE THE CHILD RUNS, DELIBERATELY. `repo_slug` is a `gh` round trip
    # and it gates a value the child produces — but taken here, a `gh` failure
    # costs a dispatch that has produced nothing, while taken after the draft it
    # would sit between a completed multi-hour child and the PR it opened.
    slug = act.repo_slug(repo_root)

    # --- Step 1: DRAFT -----------------------------------------------------
    # The PR URL is both the handoff and the child's completion contract; the
    # child raises if it produced none, so `exit 0` cannot mean unfinished.
    # `plan_path` IS PASSED, and its absence here was a defect rather than a tier
    # difference. `build_draft` branches on it to select the `build_from_plan` /
    # `stages_1_to_4_from_plan` pair, `build_minor_workflow` has always passed it,
    # and `test_build_prompt_variants_do_not_fork.py` described that pair as the
    # one used whenever a run is launched with `--phase`. It was not: the major
    # tier handed the child the plan doc's CONTENTS as a description and the
    # generic prompt, so `build --phase` never saw the plan-driven stages at all
    # and `${PLAN_PATH}` never reached it. That guard's opening was corrected on
    # 2026-08-20 — the pair is selected on `--phase` AND no `--pr`, both here and
    # on the minor tier.
    #
    # ANCHORED FOR THE MODEL, NOT THE RAW OPERATOR STRING. `PLAN_PATH` is rendered
    # into the prompt and read by a model running INSIDE THE WORKTREE, so a
    # repo-relative string is what anchors correctly there — the same `in_worktree`
    # discipline `test_model_gets_the_worktree_path.py` pins for the research
    # family. This passed the raw string, which was right about a RELATIVE `--phase`
    # and wrong about an ABSOLUTE one: `--phase /main/checkout/docs/.../phase2.md`
    # rendered that main-checkout path verbatim to a model standing in the worktree.
    # `path_for_the_model` states the in-repo/out-of-repo rule once, for both
    # tiers. The resolved absolute path is used for READING the file, in
    # `task_text`, and nowhere else.
    pr_url = draft.run_draft(
        description=description, repo_root=repo_root, worktree=worktree,
        # The slug this dispatch is operating in, so the handoff picks THIS
        # repo's PR out of a run that legitimately opened one elsewhere too.
        prefer_repo=slug,
        pr_number=task.pr_number,
        plan_path=path_for_the_model(repo_root, task.plan_path),
        verbose=task.verbose,
    )
    pr = helper.pr_number_from_url(pr_url, expected_repo=slug)

    # --- Steps 2 & 3: REFINE then DISPOSITION, bounded by helper.MAX_LOOPS ---
    loops = 0
    verdict = _refine_then_dispose(task, description, pr, repo_root,
                                   worktree, worktree_name, notes, correction=False)

    while helper.should_loop_back(verdict, loops):
        loops += 1
        # COUNTED, not asserted. This said "Looping back ONCE — this is the last
        # automated pass" while `helper.MAX_LOOPS` is `routing.MAX_LOOPS` = 3, so
        # it was false on two passes of three and told the operator the runway had
        # closed when it had not.
        notes.append(_spend(repo_root, started) + f"HOLD (redispatch): the runway closes with a scoped fix. "
                     f"Loop-back {loops} of {helper.MAX_LOOPS}."
                     + (" This is the last automated pass."
                        if loops == helper.MAX_LOOPS else ""))
        verdict = _refine_then_dispose(task, description, pr, repo_root, worktree,
                                       worktree_name, notes, correction=True,
                                       loops_left=helper.MAX_LOOPS - loops)

    if verdict is Verdict.HOLD_NEEDS_ASSISTANCE:
        # THIS NOTE STATES THE LOOP DECISION AND NOTHING ELSE, because the loop is
        # the only thing this function knows. TWO paths return this verdict and
        # BOTH already wrote their own cause: the CI gate appends a note ending
        # "review-pr was NOT dispatched", and the review path does
        # `notes.extend(result.notes)`, carrying review-pr's own explanation.
        #
        # It used to add a third sentence — "review-pr found at least one item
        # only a human can rule on" — which it had no way to know. On PR #124 the
        # CI gate fired, and that sentence landed directly beneath "review-pr was
        # NOT dispatched". Two operator-facing sentences contradicting each
        # other, and the false one read like the answer: it took grepping every
        # review-pr log to establish the PR was UNREVIEWED rather than
        # reviewed-and-held, which are different states needing different actions.
        #
        # The first fix taught this line to DETECT the cause by string-matching a
        # note written elsewhere in this file. That is the same defect wearing a
        # remedy: a claim resting on prose that can be reworded. The layer that
        # detects a condition reports it, and this layer detects neither.
        notes.append(_spend(repo_root, started) + "No loop-back was attempted: more passes cannot produce a "
                     "human decision. The cause is in the note above.")
    elif verdict is Verdict.HOLD_REDISPATCH:
        notes.append(_spend(repo_root, started) + f"The automated loop is SPENT — {helper.MAX_LOOPS} loop-back(s) "
                     f"is the cap, because passes beyond it produce justification "
                     f"rather than correction.")

    return BuildResult(pr_number=pr, pr_url=pr_url, verdict=verdict,
                          loops_used=loops, notes=notes)


def _refine_then_dispose(task: BuildInput, description: str, pr: str,
                         repo_root: Path, worktree: Path, worktree_name: str,
                         notes: list[str], *, correction: bool,
                         loops_left: int = 0) -> Verdict:
    """One refine pass followed by one disposition pass."""
    ci_settled = wait_for_ci(pr, repo_root=repo_root)
    if not ci_settled:
        notes.append("CI had not settled before refine; the child was told so.")

    # THE CORRECTION LOOP USES THE MINOR REFINE CHILD, and that is the whole
    # saving. Pass 1 needs the full tier: two review agents over an unreviewed
    # diff, 250 turns, 11.3 KB of stage prompt. A LOOP-BACK does not — `review-pr`
    # has already written the runway naming which findings, what to change and
    # what not to touch, so re-dispatching the full finding apparatus re-discovers
    # a conclusion that already exists. The minor child is 2.9 KB of stages, ONE
    # review agent and 100 turns, and its own prompt describes exactly this job:
    # "a scoped correction, reviewed by one lens".
    #
    # It is not a new child. `build_minor` already runs it, so a change here
    # reaches both callers — which is the point, and also the risk worth naming.
    if correction:
        # A correction executes the runway on the PR thread rather than the
        # operator's original brief, and neither refine child takes a task file:
        # `description` already IS that brief's text, read once by the caller.
        refine_minor.run_refine_minor(
            description=description, pr_number=pr, repo_root=repo_root,
            worktree=worktree, correction_pass=True, loops_left=loops_left,
            ci_unsettled=not ci_settled, verbose=task.verbose,
        )
    else:
        refine.run_refine(
            description=description, pr_number=pr, repo_root=repo_root,
            worktree=worktree,
            correction_pass=False, loops_left=loops_left,
            ci_unsettled=not ci_settled, verbose=task.verbose,
        )

    # --- THE GATE: the parent reads the verdict, so MERGE is unreachable on red
    # The cascade itself is `routing.ci_gate` — pure, and SHARED with the five
    # other parents that dispatch `review-pr`, none of which had a gate until it
    # was promoted out of this family. Read that function for why the gate lives
    # in a parent rather than a prompt, and why every state HOLDs instead of
    # exiting.
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
        ReviewInput(pr_number=pr, repo_target=task.repo_target, verbose=task.verbose),
        repo_root, worktree_name=worktree_name,
    )
    notes.extend(result.notes)
    return Verdict(result.verdict.value)

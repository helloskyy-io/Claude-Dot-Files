"""The plan-project parent — Layer 1 orchestration for project-level planning.

A parent calls no model. It decides IF, WHEN and WHAT to call, and holds no
process code. Every branch is a pure decision from `routing`; every side effect
is an activity or a child workflow.

    triage-candidates -> plan-candidates -> review-pr
                         [activity, no model]  [loop-back to triage]

IT RULES CANDIDATES AND GIVES THE SHIPPED ONES A HOME. That is the whole job.
It does not research those components and it does not plan them: `research`
researches a component pool and `plan` plans a component, both are parents in
their own right, and both are dispatched at a scaffolded component AFTER this
run lands. `feature-manager` is what will drive that pair per component; until
it exists the hop is the operator's, and the scaffold notes below name it.

THIS PARENT USED TO DO ALL OF IT — research each new component, plan it, size
it, maintain the sprint entry — and that was five children deep behind one
dispatch. It grew those steps when no parent existed to hold them, which stopped
being true once `research` and `plan` landed. A first-level parent that invokes
two other families inline is a pipeline wearing a parent's name: one worktree
carrying five children's work into one review, where a failure anywhere orphans
everything behind it.

`plan-candidates` IS AN ACTIVITY, NOT A CHILD, AND IT IS THE ONLY STEP HERE THAT
IS NOT. It calls no model because it needs no judgement: triage already decided
which candidates ship and the filer already named where each one goes, so the
whole job is creating the directory and seeding the first document from what the
row already says. **§3.1/§3.3** is the layering rule — Layer 1 orchestrates and
holds no process code, Layer 3a holds the I/O, which is why the function lives in
`plan_project_activities.py` rather than inline here. **§3.4** supplies the other
half: *"manufacturing children for their own sake adds dispatch overhead for no
gain"*.

WHY review-pr AND NOT A DEDICATED REVIEWER. `review-pr` is a SHARED child — it
already takes `--type planning` with its own criteria, and it stays
independently dispatchable against any returned PR. Child-ness is a call-graph
property, not a location.

WHY A JUDGE AT ALL. `triage-candidates` rules every candidate and its rulings
reach the operator as a merged PR. Every other family has its judge — build is
draft -> refine -> review-pr, research is write -> verify -> review-pr — and
this one had nothing, which made it the single place where `author != judge` was
not being honoured. The child cannot call `review-pr` itself: a parent calls no
model and both of them call one.
"""

from __future__ import annotations

from pathlib import Path

from .. import plan_activities as act
from . import plan_project_activities as own
from ... import assistant_activities as _shared
from ...assistant_activities import ci_verdict, wait_for_ci
from ... import routing
from ...review_pr import review_pr_workflow as review_pr
from ...review_pr.review_pr_helper import ReviewInput, ReviewType
from ..triage_candidates import triage_candidates_workflow as triage


def run_plan_project(*, repo_root: Path, worktree_name: str,
                     candidates_path: Path, research_dir: Path,
                     pr_number: str | None = None, repo_target: str | None = None,
                     verbose: bool = False) -> tuple[str, routing.Verdict, int, list[str]]:
    """Triage the candidates, scaffold the shipped ones, judge the result.

    Returns (pr_url, verdict, loops_used, notes). A HOLD is a RESULT, not a
    failure — the caller branches on the verdict, which is the entire point of
    returning a typed value rather than an exit code.
    """
    notes: list[str] = []

    # ISOLATION IS ESTABLISHED ONCE, HERE. The child receives the path and never
    # creates one — two actors creating the same named worktree is a
    # `fatal: already exists` that has killed a handoff before.
    ref = act.base_ref(pr_number, repo_root)
    worktree = act.worktree_add(repo_root, worktree_name, ref)

    # Read BEFORE the triage child, so a `gh` failure costs a dispatch that has
    # produced nothing rather than one that has already triaged a sprint.
    slug = _shared.repo_slug(repo_root)

    # --- Step 1: TRIAGE ----------------------------------------------------
    # The PR URL is both the handoff and the child's completion contract; the
    # child raises if it produced none AND if it left any candidate untriaged,
    # so `exit 0` cannot mean unfinished.
    pr_url = triage.run_triage_candidates(
        repo_root=repo_root, worktree=worktree,
        candidates_path=candidates_path, research_dir=research_dir,
        pr_number=pr_number, verbose=verbose,
    )
    pr = routing.pr_number_from_url(pr_url, expected_repo=slug)

    # --- Step 2: SCAFFOLD each shipped candidate that has no home yet -------
    # AN ACTIVITY, NOT A CHILD. No worktree of its own, no PR of its own, no
    # model: it runs inline on the branch step 1 just opened, and its output
    # lands in the same commit range under the same review.
    #
    # IT RUNS AFTER TRIAGE FOR THE OBVIOUS REASON — it acts on `ship` rulings,
    # and before triage there are none. On a `--pr` redispatch the rulings are
    # already there from an earlier pass, and the exists-check is what keeps that
    # from re-scaffolding them.
    scaffolded = own.scaffold_candidate_components(
        worktree, worktree / candidates_path.relative_to(repo_root))

    # EVERY OUTCOME GETS A NOTE, NOT ONLY THE PRODUCTIVE ONE. A step that reports
    # only what it created cannot be told apart from a step that saw nothing, and
    # the quiet outcomes are the ones worth reading: a candidate extending a live
    # component is the design working, a resumed pool is a previous run that died
    # half-way, and an unusable name is a filer typo nobody else will notice.
    #
    # NOT `slug` for the loop variable — that name is already bound to the
    # REPOSITORY slug above and is what step 1's PR-number lookup was given.
    #
    # THE CREATED AND RESUMED NOTES NAME THE NEXT DISPATCH, and that is this
    # parent's handoff surface rather than a courtesy. Nothing downstream of here
    # researches or plans a scaffolded component: this run ends at the review,
    # and the component sits at a seeded synthesis until `research` then `plan`
    # are pointed at it. An operator reading only the verdict would not know that.
    for component in scaffolded.created:
        notes.append(f"Scaffolded `docs/development/{component}/research/` from a "
                     f"shipped candidate. NOT researched and NOT planned by this "
                     f"run — dispatch `research.sh docs/development/{component}/research` "
                     f"and then `plan.sh docs/development/{component}` to take it "
                     f"forward.")
    for component in scaffolded.resumed:
        notes.append(f"`docs/development/{component}/research/` was seeded by an "
                     f"earlier pass and still holds no research. Same two dispatches "
                     f"take it forward: `research.sh docs/development/{component}/research` "
                     f"then `plan.sh docs/development/{component}`.")
    # NOT "which already holds research" — that was a claim about the pool's
    # CONTENTS over a check of the directory's EXISTENCE, and it is false for most
    # of the tree: most components hold either a `research/` with nothing rolled
    # up or no `research/` at all. An operator acting on the old sentence believed
    # research existed that did not. The note says what was actually checked.
    for cid, component in scaffolded.extends:
        notes.append(f"`{cid}` names `docs/development/{component}/`, which already "
                     f"exists — the candidate extends something already planned, so "
                     f"nothing was scaffolded. Whether that component has research "
                     f"is a separate question this step does not ask.")
    for cid, raw in scaffolded.unnamed:
        notes.append(f"`{cid}`'s `component` cell reads {raw!r}, which yields no "
                     f"folder name. Nothing scaffolded; the cell needs a real name "
                     f"or a blank.")
    # THE TWO SIZE-DRIVEN DECLINES, REPORTED SEPARATELY because the operator does
    # something different about each. Neither is an error and neither is silent.
    for cid, size in scaffolded.not_a_feature:
        notes.append(f"`{cid}` is sized `{size}`, so nothing was scaffolded — it "
                     f"is work INSIDE a component rather than a component of its "
                     f"own, and the run that plans that component is where it "
                     f"lands. This is the correct outcome for a {size}-sized "
                     f"candidate, not a skip. Whether the component its "
                     f"`component` cell names is already planned is a separate "
                     f"question this step does not ask.")
    for cid, marker in scaffolded.unsized:
        notes.append(f"`{cid}` is `{marker}` — ruled `ship` and carrying no `size`, "
                     f"so nothing "
                     f"here can route it. Sizing is `triage-candidates`' second "
                     f"ruling; this row predates the column or the triage pass that "
                     f"ruled it did not size it. It waits for a triage pass — "
                     f"reported rather than guessed at, because a guess would "
                     f"scaffold a component nobody asked for.")
    if not (scaffolded.created or scaffolded.resumed):
        notes.append(
            "No component was scaffolded: no shipped candidate named a component "
            "whose directory was missing. That is an empty working set, not a "
            "skipped step. Any candidate that WAS seen and declined is named in "
            "its own note above."
        )

    # --- Step 3: DISPOSITION, with one bounded loop-back -------------------
    loops = 0
    verdict = _dispose(pr, repo_root, repo_target, notes, verbose)

    while routing.should_loop_back(verdict, loops):
        loops += 1
        # COUNTED, not asserted. This said "Looping back ONCE — this is the last
        # automated pass" while `routing.MAX_LOOPS` is 3, so it was false on two
        # passes out of three and told the operator the runway had closed when it
        # had not. `test_loop_cap_prose_is_counted.py` fails any new hard-coded
        # claim.
        notes.append(f"HOLD (redispatch): the runway closes with a scoped fix. "
                     f"Loop-back {loops} of {routing.MAX_LOOPS}."
                     + (" This is the last automated pass."
                        if loops == routing.MAX_LOOPS else ""))
        # THE LOOP-BACK GOES TO TRIAGE, WHICH REVERSES WHAT THIS COMMENT USED TO
        # SAY, AND THE REVERSAL IS THE NARROWING RATHER THAN A CHANGE OF MIND. It
        # used to go to `plan-sprint` on the argument that plan-sprint was the
        # LAST producer and "sees the whole PR", explicitly rejecting triage
        # because "re-triaging would re-litigate rulings rather than close the
        # runway". That argument only picks between producers, and there is now
        # exactly one: `plan-sprint` and the research/plan children left with the
        # narrowing, and `plan-candidates` is an activity with no model to correct.
        #
        # THE RE-LITIGATION OBJECTION IS REAL AND THE CHILD ALREADY ANSWERS IT,
        # WITH NO FLAG FROM HERE. `_working_set` branches on the counted file: at
        # zero untriaged it stops issuing a working set and tells the run its job
        # is to REVISE — "close the runway a reviewer wrote... re-litigating
        # settled dispositions is the failure this sentence exists to prevent."
        # Step 1 raises if it leaves any row untriaged, so every loop-back arrives
        # at zero by construction and takes that branch.
        #
        # NO `correction_pass` PARAMETER WAS ADDED, and that is the finding rather
        # than an omission. The sibling children carry one because their artifact
        # does not show the state; this one's does, and a flag would be a second
        # source for a fact already proven by the file — the exact shape this
        # parent's own rule refuses, that a parent must not trust an account when
        # the artifact is right there.
        triage.run_triage_candidates(
            repo_root=repo_root, worktree=worktree,
            candidates_path=candidates_path, research_dir=research_dir,
            pr_number=pr, verbose=verbose,
        )
        verdict = _dispose(pr, repo_root, repo_target, notes, verbose)

    if verdict is routing.Verdict.HOLD_NEEDS_ASSISTANCE:
        # THE LOOP DECISION AND NOTHING ELSE. Wiring the CI gate into `_dispose`
        # gave this parent a SECOND path to this verdict, and the gate writes its
        # own cause ending "review-pr was NOT dispatched" — so the old sentence
        # here, "review-pr found at least one item only a human can rule on",
        # would land directly beneath a note saying review-pr never ran.
        notes.append("No loop-back was attempted: more passes cannot produce a "
                     "human decision. The cause is in the note above.")
    elif verdict is routing.Verdict.HOLD_REDISPATCH:
        # COUNTED from the same source the loop reads. This said "one loop-back
        # is the cap" twenty-two lines below the fix above it, and the false one
        # understates the automated budget the operator is deciding against by 3x.
        notes.append(f"The automated loop is SPENT — {routing.MAX_LOOPS} loop-back(s) "
                     f"is the cap, because passes beyond it produce justification "
                     f"rather than correction.")

    # A planning PR ALWAYS needs the operator, even at MERGE. `direction.md`
    # rows are by construction rulings no automated pass can make. MERGE here
    # means "the judge found nothing to correct", never "merge it unattended".
    if verdict is routing.Verdict.MERGE:
        notes.append("MERGE means the judge found nothing to correct. It does NOT mean "
                     "merge unattended: any direction.md rows are rulings only the "
                     "operator can make.")

    return pr_url, verdict, loops, notes


def _dispose(pr: str, repo_root: Path, repo_target: str | None,
             notes: list[str], verbose: bool) -> routing.Verdict:
    """One disposition pass, judged against the PLANNING criteria, behind the gate.

    THIS USED TO SAY "No CI wait: this family changes markdown only, so there is
    no build to settle", AND THAT REASONING WAS WRONG ABOUT THIS REPO. Markdown
    is not outside the gate here: `.github/workflows/tests.yml` carries NO
    `paths:` filter — deliberately, its own comment saying a filtered gate "can
    only ever skip something it should have caught" — and the suite greps
    prompts, docs and `config.yaml`. A planning PR that edits only `.md` runs the
    full suite and can turn it red, at which point an ungated `run_review` could
    return MERGE on it. The whole job is ~20 seconds, so the timeout it was
    protecting against is not the one that exists.
    """
    # --- THE GATE: the parent reads the verdict, so MERGE is unreachable on red
    # `routing.ci_gate` — the same pure cascade the build parents run. It was
    # absent here because it lived under `build/`, and reaching it from the plan
    # family would have been a layering inversion.
    #
    # `repo_root=repo_root` ON BOTH, and the parameter is REQUIRED rather than
    # merely conventional: omitting it used to make every read degrade to "this
    # repo declares no gate", so the gate was present and forgave everything.
    # The default was dropped on 2026-08-20 so the degrade path no longer exists.
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

"""The plan parent — Layer 1 orchestration for the planning family.

A parent calls no model. It decides IF, WHEN and WHAT to call, and holds no
process code. Every branch is a pure decision from `routing`; every side effect
is an activity or a child workflow.

    triage-candidates  ->  research(per NEW component)  ->  plan-sprint  ->  review-pr
                             write -> verify                                  [loop-back]

TRIAGE AT THE FRONT, SPRINT MAINTENANCE AT THE BACK. Until the split, one child
did both and nothing could be sequenced between them. Feature planning and
scaffolding belong in that gap, and while the two jobs shared a dispatch that was
structurally impossible rather than merely unbuilt.

IT FIXED AN ORDERING DEFECT ON ITS OWN. `plan-sprint` used to run FIRST, so the
sprint plan — hour totals included — was updated before anything estimated the
work those totals are of. Running it last means it reads what the middle of the
pipeline produced instead of predicting it.

WHAT IS NOT HERE YET, AND WHAT THAT COSTS TODAY. `plan-candidates` and
`plan-feature` are the two children that belong between triage and plan-sprint.
Until they land, THE RESEARCH STEP IN THE MIDDLE CANNOT FIRE: its input is
`new_sprint_sections`, read from the sprint diff, and no child ahead of it can
add a sprint section any more — plan-sprint, the only workflow that adds one,
now runs after it. That is stated rather than papered over. The alternative was
to invent a different NEW-component signal for a gap two planned children are
about to fill, and a signal invented for an interim outlives the interim. The
parent emits a note saying so when the sweep comes back empty, so an operator
reading the run's output is told rather than left to infer it from a step that
silently did nothing.

WHY THIS EXISTS AT ALL. `plan-sprint` shipped and ran twice with no parent, so
its output reached the operator UNJUDGED — and it is the only autonomous run
authorised to write `sprint.md`, the file the governing rule exists to protect.
Every other family has its judge: build is draft -> refine -> review-pr,
research is write -> verify -> review-pr. This one had nothing, which made it
the single place where `author != judge` was not being honoured.

Neither child could simply call `review-pr` itself: a parent calls no model and
both of them call one. Bolting the judge onto a child would have made it a
model-calling orchestrator, which is the exact shape decomposition removes.

WHY review-pr AND NOT A DEDICATED REVIEWER. `review-pr` is a SHARED child — it
already takes `--type planning` with its own criteria, and it stays
independently dispatchable against any returned PR. Child-ness is a call-graph
property, not a location.

WHY THE RESEARCH CHILDREN AND NOT THE RESEARCH PARENT. `run_research` is itself
a parent: it establishes its own worktree and opens its own PR. Calling it here
would give one flow two worktrees and two PRs, and its verify loop would gate a
sprint triage that was already fine. Calling `research_write` and
`research_verify` directly keeps ONE worktree and ONE PR, and reuses the same
children the research parent uses. Same children, two callers.

`plan-phase` — writing the phase doc for a new sprint section — is also still
being ported from `plan-revision.sh`. It slots between plan-sprint and review-pr
and needs no change to the shape below.
"""

from __future__ import annotations

from pathlib import Path

from .. import plan_activities as act
from ... import assistant_activities as _shared
from ... import routing
from ...review_pr import review_pr_workflow as review_pr
from ...review_pr.review_pr_helper import ReviewInput, ReviewType
from ...research.research_write import research_write_workflow as write
from ...research.research_verify import research_verify_workflow as verify
from ..plan_sprint import plan_sprint_workflow as sprint
from ..triage_candidates import triage_candidates_workflow as triage


def run_plan_project(*, repo_root: Path, worktree_name: str, sprint_path: Path,
                    candidates_path: Path, research_dir: Path,
                    pr_number: str | None = None, repo_target: str | None = None,
                    verbose: bool = False) -> tuple[str, routing.Verdict, int, list[str]]:
    """Triage, plan, judge, and route on the verdict.

    Returns (pr_url, verdict, loops_used, notes). A HOLD is a RESULT, not a
    failure — the caller branches on the verdict, which is the entire point of
    returning a typed value rather than an exit code.
    """
    notes: list[str] = []

    # ISOLATION IS ESTABLISHED ONCE, HERE. The child receives the path and never
    # creates one — two actors creating the same named worktree is a
    # `fatal: already exists` that has killed a handoff before.
    ref = f"origin/{act.pr_branch(pr_number, repo_root)}" if pr_number else "HEAD"
    worktree = act.worktree_add(repo_root, worktree_name, ref)

    # Read BEFORE the triage child, so a `gh` failure costs a dispatch that has
    # produced nothing rather than one that has already triaged a sprint.
    slug = _shared.repo_slug(repo_root)

    # --- Step 1: TRIAGE ----------------------------------------------------
    # FIRST, and this is the ordering the split bought. The PR URL is both the
    # handoff and the child's completion contract; the child raises if it
    # produced none AND if it left any candidate untriaged, so `exit 0` cannot
    # mean unfinished.
    pr_url = triage.run_triage_candidates(
        repo_root=repo_root, worktree=worktree,
        candidates_path=candidates_path, research_dir=research_dir,
        pr_number=pr_number, verbose=verbose,
    )
    pr = routing.pr_number_from_url(pr_url, expected_repo=slug)

    # --- Step 2: RESEARCH each NEW component -------------------------------
    # Read from the diff, never asked of the triage child: the parent must not
    # trust an account when the artifact is right there. An edited section shows
    # no added heading, so a component is researched only when it is genuinely
    # new — researching one because its prose moved spends a full cycle on
    # nothing.
    #
    # The research CHILDREN are called, not the research PARENT. That parent
    # would establish a second worktree and open a second PR, and its verify
    # loop would then gate a triage pass that was already fine. Same children,
    # two callers — which is the whole point of child-ness being a call-graph
    # property rather than a location.
    #
    # THIS SWEEP IS EMPTY BY CONSTRUCTION TODAY. See the module docstring: with
    # plan-sprint moved behind this step, nothing ahead of it adds a sprint
    # section, so there is no added `## Sprint:` heading in the diff to find.
    # `plan-candidates` and `plan-feature` are what will fill this position. The
    # call stays because the wiring is correct and only its INPUT is missing —
    # deleting it would mean rebuilding it, and inventing a different signal
    # would mean maintaining one past the interim it was for.
    new_sections = act.new_sprint_sections(worktree, str(sprint_path.relative_to(repo_root)))
    if not new_sections:
        notes.append(
            "No component research ran. With plan-sprint sequenced AFTER this step, "
            "nothing ahead of it can add a sprint section, so this step's signal is "
            "empty by construction until plan-candidates and plan-feature land. This "
            "is the known interim state, not a silent skip."
        )
    for section in new_sections:
        notes.append(f"New component `{section}` — researching before it is planned.")
        # NOT `research_dir` — that parameter is the PRODUCT pool the triage and
        # sprint children work from, and rebinding it here would hand the
        # loop-back below the wrong pool. A shadowed parameter is a silent
        # wrong-argument bug.
        component_pool = act.component_dir(worktree, section) / "research"
        component_pool.mkdir(parents=True, exist_ok=True)

        # The sprint section IS the brief. It states the milestones, and the
        # research child's Stage 1 already reads the destination's planning docs
        # to drive its topics — so a hand-written task file would be restating
        # what it is about to read.
        context = (
            f"A new sprint section `{section}` was just added to "
            f"{sprint_path.relative_to(repo_root)} and has no phase doc yet. "
            f"Research it BEFORE it is planned. Read that section first — it is "
            f"your brief, and its milestones are what this pool must inform."
        )
        write.run_write(research_dir=component_pool, repo_root=repo_root,
                        worktree=worktree, context=context, pr_number=pr,
                        verbose=verbose)
        verify.run_verify(research_dir=component_pool, pr_number=pr,
                          repo_root=repo_root, worktree=worktree, verbose=verbose)

    # --- Step 3: MAINTAIN THE SPRINT PLAN ----------------------------------
    # LAST of the producing children, which is the second thing the split
    # bought. It reads what steps 1 and 2 put in the tree — the rulings and any
    # component evidence — rather than being written before either existed. Its
    # own guard fails the run if it wrote the `decision` column, which is now
    # `triage-candidates`'s alone.
    #
    # `pr_number=pr`: the PR is already open. Step 1 opened it, and both children
    # land their work on the one branch, in the one worktree, under the one
    # review.
    sprint.run_plan_sprint(
        repo_root=repo_root, worktree=worktree, sprint_path=sprint_path,
        candidates_path=candidates_path, research_dir=research_dir,
        pr_number=pr, verbose=verbose,
    )

    # --- Step 4: DISPOSITION, with one bounded loop-back -------------------
    loops = 0
    verdict = _dispose(pr, repo_root, repo_target, notes, verbose)

    while routing.should_loop_back(verdict, loops):
        loops += 1
        # COUNTED, not asserted. This said "Looping back ONCE — this is the last
        # automated pass" while `routing.MAX_LOOPS` is 3, so it was false on two
        # passes out of three and told the operator the runway had closed when it
        # had not. The same stale sentence survives in six other workflows that
        # this change does not touch; it is surfaced rather than swept.
        notes.append(f"HOLD (redispatch): the runway closes with a scoped fix. "
                     f"Loop-back {loops} of {routing.MAX_LOOPS}."
                     + (" This is the last automated pass."
                        if loops == routing.MAX_LOOPS else ""))
        # THE LOOP-BACK GOES TO plan-sprint, NOT TO TRIAGE, and it is a
        # correction pass. Every candidate already carries a decision, so
        # re-triaging would re-litigate rulings rather than close the runway the
        # reviewer wrote — the reason this was a correction pass before the
        # split, and it did not change. plan-sprint is also the LAST producer and
        # sees the whole PR, so a runway naming either child's work is
        # addressable from here; sending each loop through both children would
        # double the cost of every pass to reach a set of rulings that are, by
        # construction, already made.
        sprint.run_plan_sprint(
            repo_root=repo_root, worktree=worktree, sprint_path=sprint_path,
            candidates_path=candidates_path, research_dir=research_dir,
            pr_number=pr, correction_pass=True, verbose=verbose,
        )
        verdict = _dispose(pr, repo_root, repo_target, notes, verbose)

    if verdict is routing.Verdict.HOLD_NEEDS_ASSISTANCE:
        notes.append("review-pr found at least one item only a human can rule on. No "
                     "loop-back was attempted: more passes cannot produce a human decision.")
    elif verdict is routing.Verdict.HOLD_REDISPATCH:
        notes.append("The automated loop is SPENT — one loop-back is the cap, because "
                     "passes beyond it produce justification rather than correction.")

    # A planning PR ALWAYS needs the operator, even at MERGE. `direction.md`
    # rows are by construction rulings no automated pass can make, and the
    # sprint plan is the operator's own surface. MERGE here means "the judge
    # found nothing to correct", never "merge it unattended".
    if verdict is routing.Verdict.MERGE:
        notes.append("MERGE means the judge found nothing to correct. It does NOT mean "
                     "merge unattended: any direction.md rows are rulings only the "
                     "operator can make, and the sprint plan is the operator's surface.")

    return pr_url, verdict, loops, notes


def _dispose(pr: str, repo_root: Path, repo_target: str | None,
             notes: list[str], verbose: bool) -> routing.Verdict:
    """One disposition pass, judged against the PLANNING criteria.

    No CI wait: this family changes markdown only, so there is no build to
    settle. Adding one would spend a timeout per pass to observe nothing.
    """
    result = review_pr.run_review(
        ReviewInput(pr_number=pr, repo_target=repo_target,
                    review_type=ReviewType.PLANNING, verbose=verbose),
        repo_root,
    )
    notes.extend(result.notes)
    return result.verdict

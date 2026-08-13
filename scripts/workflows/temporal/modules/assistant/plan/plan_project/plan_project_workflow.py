"""The plan parent — Layer 1 orchestration for the planning family.

A parent calls no model. It decides IF, WHEN and WHAT to call, and holds no
process code. Every branch is a pure decision from `routing`; every side effect
is an activity or a child workflow.

    triage-candidates  ->  plan-candidates  ->  research(per NEW component)  ->  plan-sprint  ->  review-pr
                                                  write -> verify                                  [loop-back]

TRIAGE AT THE FRONT, SPRINT MAINTENANCE AT THE BACK. Until the split, one child
did both and nothing could be sequenced between them. Feature planning and
scaffolding belong in that gap, and while the two jobs shared a dispatch that was
structurally impossible rather than merely unbuilt.

IT FIXED AN ORDERING DEFECT ON ITS OWN. `plan-sprint` used to run FIRST, so the
sprint plan — hour totals included — was updated before anything estimated the
work those totals are of. Running it last means it reads what the middle of the
pipeline produced instead of predicting it.

THE RESEARCH STEP'S INPUT IS REACHABLE AGAIN, AND `plan-candidates` IS WHY. The
sweep used to read added `## Sprint:` headings out of the sprint diff, which the
split made unreachable: `plan-sprint` is the only workflow that adds a heading
and it now runs behind this step, so the signal was empty by construction and the
parent emitted a note saying so. `plan-candidates` charters a component — a
`docs/development/<slug>/roadmap.md` — and that file IS the signal, read from the
diff by the same discipline: the parent reads the artifact rather than trusting a
child's account of it. It is also a strictly better brief than the heading was.
A sprint heading is a name; a charter states what the component is, what it is
not, and which differentiator it serves, which is what a research pool needs to
be scoped against.

WHAT IS STILL NOT HERE. `plan-feature` belongs between the research pair and
`plan-sprint`: it plans the roadmap's phases and estimates the hours per phase,
which is why `plan-sprint` runs after it and reads those estimates rather than
predicting them. Until it lands, a chartered component reaches `plan-sprint` with
research and no phases. That is a smaller gap than the one this commit closed —
nothing is inert, and every step's input exists — but it is stated rather than
papered over, and the note below says so on any run that charters a component.

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
from . import plan_project_activities as own
from ... import assistant_activities as _shared
from ... import routing
from ...review_pr import review_pr_workflow as review_pr
from ...review_pr.review_pr_helper import ReviewInput, ReviewType
from ...research.research_write import research_write_workflow as write
from ...research.research_verify import research_verify_workflow as verify
from ..plan_candidates import plan_candidates_workflow as scaffold
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

    # THE COMMIT THIS DISPATCH STARTED FROM, pinned before any child can write.
    # Step 2's sweep asks "which sections did THIS RUN add", and only a base
    # taken here answers it: on a `--pr` redispatch the branch already carries
    # sections an earlier pass added and researched, so a diff against
    # `origin/main` would re-research every one of them. Same rule the snapshot
    # comparators state — snapshot around the run, never diff against the base.
    base_sha = act.git_output(
        worktree, ["git", "rev-parse", "HEAD"],
        "The parent cannot pin the commit this dispatch started from, so it "
        "cannot tell the sections IT added from ones an earlier pass added.",
    ).strip()

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

    # --- Step 2: SCAFFOLD what the rulings need ----------------------------
    # BETWEEN THE RULING AND THE WORK. A `ship` row is a decision that something
    # should be built, not a place to build it, and both children after this need
    # a place before they can run: research is commissioned per component pool,
    # and `plan-feature` plans phases INTO a component. This child charters the
    # components that do not exist and — the outcome it is designed to reach most
    # often — reports that the rest of the ruled set extends something that does.
    #
    # Its own guard fails the run if it planned phases or estimated hours: that
    # is `plan-feature`'s job, and structure-versus-substance is the boundary the
    # whole child is defined by.
    #
    # `pr_number=pr`: the PR is already open. Step 1 opened it, and every child
    # lands its work on the one branch, in the one worktree, under the one review.
    scaffold.run_plan_candidates(
        repo_root=repo_root, worktree=worktree,
        candidates_path=candidates_path, research_dir=research_dir,
        pr_number=pr, verbose=verbose,
    )

    # --- Step 3: RESEARCH each NEW component -------------------------------
    # Read from the diff, never asked of the scaffolding child: the parent must
    # not trust an account when the artifact is right there. Only ADDED charters
    # count, so a component is researched when it is genuinely new — researching
    # one because a paragraph in its charter moved spends a full cycle on nothing.
    #
    # THE SIGNAL THAT MAKES THIS STEP FIRE AGAIN. It used to read added
    # `## Sprint:` headings out of the sprint diff, which the triage split made
    # unreachable — `plan-sprint` is the only workflow that adds one and it now
    # runs behind this step. Step 2's charter is the artifact that replaced it,
    # and it is a better brief besides: a heading is a name, a charter states the
    # component's scope and its boundary.
    #
    # The research CHILDREN are called, not the research PARENT. That parent
    # would establish a second worktree and open a second PR, and its verify
    # loop would then gate a triage pass that was already fine. Same children,
    # two callers — which is the whole point of child-ness being a call-graph
    # property rather than a location.
    new_components = own.scaffolded_components(worktree, base_ref=base_sha)
    if not new_components:
        notes.append(
            "No component research ran: plan-candidates chartered no new component, "
            "which is its most common correct outcome — a ruled candidate that "
            "extends something that already exists needs no new structure. Read its "
            "placement table in the PR to see where the ruled set landed."
        )
    for slug_name in new_components:
        notes.append(f"New component `{slug_name}` — researching before it is planned. "
                     f"`plan-feature` does not exist yet, so it will reach plan-sprint "
                     f"with research and no phases.")
        # NOT `research_dir` — that parameter is the PRODUCT pool the triage and
        # sprint children work from, and rebinding it here would hand the
        # loop-back below the wrong pool. A shadowed parameter is a silent
        # wrong-argument bug.
        component_pool = own.component_pool(worktree, slug_name)
        component_pool.mkdir(parents=True, exist_ok=True)

        # THE CHARTER IS THE BRIEF, and it is written to be one: what the
        # component is, what it is not, and which differentiator it serves. The
        # research child's Stage 1 already reads the destination's planning docs
        # to drive its topics, so a hand-written task file would be restating
        # what it is about to read.
        context = (
            f"A new component `{slug_name}` was just chartered at "
            f"docs/development/{slug_name}/roadmap.md and has no "
            f"phase doc yet. Research it BEFORE it is planned. Read that charter "
            f"first — it is your brief. Its 'What this is NOT' section is the "
            f"scope boundary this pool must stay inside."
        )
        write.run_write(research_dir=component_pool, repo_root=repo_root,
                        worktree=worktree, context=context, pr_number=pr,
                        verbose=verbose)
        verify.run_verify(research_dir=component_pool, pr_number=pr,
                          repo_root=repo_root, worktree=worktree, verbose=verbose)

    # --- Step 4: MAINTAIN THE SPRINT PLAN ----------------------------------
    # LAST of the producing children, which is the second thing the split
    # bought. It reads what steps 1 to 3 put in the tree — the rulings, the
    # charters and any component evidence — rather than being written before any
    # of it existed. Its own guard fails the run if it wrote the `decision`
    # column, which is now `triage-candidates`'s alone.
    sprint.run_plan_sprint(
        repo_root=repo_root, worktree=worktree, sprint_path=sprint_path,
        candidates_path=candidates_path, research_dir=research_dir,
        pr_number=pr, verbose=verbose,
    )

    # --- Step 5: DISPOSITION, with one bounded loop-back -------------------
    loops = 0
    verdict = _dispose(pr, repo_root, repo_target, notes, verbose)

    while routing.should_loop_back(verdict, loops):
        loops += 1
        # COUNTED, not asserted. This said "Looping back ONCE — this is the last
        # automated pass" while `routing.MAX_LOOPS` is 3, so it was false on two
        # passes out of three and told the operator the runway had closed when it
        # had not. The whole class is now counted — the four build-family sites
        # too, two of which were telling a MODEL it was the last pass — and
        # `test_loop_cap_prose_is_counted.py` fails any new hard-coded claim. The
        # research family keeps its own `MAX_LOOPS = 1`, so its identical wording
        # is TRUE and is left alone.
        notes.append(f"HOLD (redispatch): the runway closes with a scoped fix. "
                     f"Loop-back {loops} of {routing.MAX_LOOPS}."
                     + (" This is the last automated pass."
                        if loops == routing.MAX_LOOPS else ""))
        # THE LOOP-BACK GOES TO plan-sprint, NOT TO ANY EARLIER CHILD, and it is
        # a correction pass. Every candidate already carries a decision, so
        # re-triaging would re-litigate rulings rather than close the runway the
        # reviewer wrote — the reason this was a correction pass before the
        # split, and it did not change. The same argument reaches
        # plan-candidates, and more strongly: re-running it would re-examine a
        # scaffolding decision the reviewer is holding the PR ON, and a component
        # directory is durable in a way a table row is not. plan-sprint is also
        # the LAST producer and sees the whole PR, so a runway naming any child's
        # work is addressable from here; sending each loop through every child
        # would multiply the cost of every pass to reach decisions that are, by
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
        # COUNTED from the same source the loop reads. This said "one loop-back
        # is the cap" twenty-two lines below the fix above it, so a spent runway
        # emitted "Loop-back 3 of 3" and then "one loop-back is the cap" in one
        # run's notes — and the false one understates the automated budget the
        # operator is deciding against by 3x.
        notes.append(f"The automated loop is SPENT — {routing.MAX_LOOPS} loop-back(s) "
                     f"is the cap, because passes beyond it produce justification "
                     f"rather than correction.")

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

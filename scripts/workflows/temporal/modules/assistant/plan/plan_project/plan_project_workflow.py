"""The plan parent — Layer 1 orchestration for the planning family.

A parent calls no model. It decides IF, WHEN and WHAT to call, and holds no
process code. Every branch is a pure decision from `routing`; every side effect
is an activity or a child workflow.

    triage-candidates  ->  plan-candidates  ->  research(per NEW component)  ->  plan-sprint  ->  review-pr
                           [activity, no model]    write -> verify                                  [loop-back]

TRIAGE AT THE FRONT, SPRINT MAINTENANCE AT THE BACK. Until the split, one child
did both and nothing could be sequenced between them. Feature planning and
scaffolding belong in that gap, and while the two jobs shared a dispatch that was
structurally impossible rather than merely unbuilt.

`plan-candidates` IS AN ACTIVITY, NOT A CHILD, AND IT IS THE ONLY STEP HERE THAT
IS NOT. It calls no model because it needs no judgement: triage already decided
which candidates ship and the filer already named where each one goes, so the
whole job is creating the directory and seeding the first document from what the
row already says. A parent calling an activity directly is the shape §3.4
prescribes for exactly this — deterministic work belongs in code, and this runs
for free.

IT FIXED AN ORDERING DEFECT ON ITS OWN. `plan-sprint` used to run FIRST, so the
sprint plan — hour totals included — was updated before anything estimated the
work those totals are of. Running it last means it reads what the middle of the
pipeline produced instead of predicting it.

WHAT IS NOT HERE YET. `plan-feature` — placing a shipped candidate inside an
existing sprint or phase doc, and writing the `roadmap.md` and phase docs a new
component gets — is still to come. It slots after the research step.

THE RESEARCH STEP CAN FIRE AGAIN, AND `plan-candidates` IS WHAT FIXED IT. Its
input was `new_sprint_sections` alone, read from the sprint diff, and with
plan-sprint sequenced behind it nothing ahead of it added a sprint section — so
the step was inert by construction. It was left wired rather than deleted or
given an invented interim signal, on the grounds that a signal invented for an
interim outlives the interim. `plan-candidates` supplies the real one: the
components it scaffolds ARE the new components, named by the filer and ruled by
triage, and no diff heuristic is involved. Both signals are read and unioned —
`new_sprint_sections` stays because it is still the correct answer to *"did this
run add a sprint section"*, and it will start returning rows again the moment
anything ahead of this step writes one.

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

    # --- Step 1b: SCAFFOLD each shipped candidate that has no home yet ------
    # AN ACTIVITY, NOT A CHILD. No worktree of its own, no PR of its own, no
    # model: it runs inline on the branch step 1 just opened, and its output
    # lands in the same commit range under the same review.
    #
    # IT RUNS AFTER TRIAGE FOR THE OBVIOUS REASON — it acts on `ship` rulings,
    # and before triage there are none. On a `--pr` redispatch the rulings are
    # already there from an earlier pass, and the directory-exists check is what
    # keeps that from re-scaffolding them.
    # NOT `slug` — that name is already bound to the REPOSITORY slug above and
    # is what step 1's PR-number lookup was given. Rebinding it in a loop here
    # is the shadowing bug `component_dir`'s caller comment names, one scope up.
    scaffolded = own.scaffold_candidate_components(
        worktree, worktree / candidates_path.relative_to(repo_root))
    for component in scaffolded:
        notes.append(f"Scaffolded `docs/development/{component}/research/` "
                     f"from a shipped candidate — researching it next.")

    # --- Step 2: RESEARCH each NEW component -------------------------------
    # TWO SIGNALS, UNIONED, AND NEITHER IS ASKED OF A CHILD. The parent must not
    # trust an account when the artifact is right there.
    #
    #   * what step 1b just scaffolded — a `ship` candidate whose component the
    #     FILER named and whose directory did not exist. This is the live signal.
    #   * a `## Sprint:` heading THIS RUN added — read from the diff. An edited
    #     section shows no added heading, so a component is researched only when
    #     it is genuinely new; researching one because its prose moved spends a
    #     full cycle on nothing.
    #
    # THE SECOND WAS THE ONLY SIGNAL AND THAT MADE THIS STEP INERT. With
    # plan-sprint sequenced behind it, nothing ahead of it adds a sprint section,
    # so the sweep could not return anything. It is kept rather than replaced
    # because it is still the correct answer to the question it asks, and it
    # starts returning rows the moment anything ahead of this step writes one.
    #
    # Order matters only for reading the notes: scaffolded components first,
    # because that is the path a candidate actually travels today.
    #
    # The research CHILDREN are called, not the research PARENT. That parent
    # would establish a second worktree and open a second PR, and its verify
    # loop would then gate a triage pass that was already fine. Same children,
    # two callers — which is the whole point of child-ness being a call-graph
    # property rather than a location.
    new_sections = own.new_sprint_sections(
        worktree, str(sprint_path.relative_to(repo_root)), base_ref=base_sha)
    # De-duplicated, order-preserving: a component can reach this step down both
    # paths at once, and researching it twice would buy a second full cycle for
    # nothing. `dict.fromkeys` rather than a set — the note order above is the
    # order an operator reads.
    to_research = list(dict.fromkeys(scaffolded + new_sections))
    if not to_research:
        notes.append(
            "No component research ran: no shipped candidate named a component "
            "that needed scaffolding, and this run added no sprint section. That "
            "is an empty working set, not a skipped step."
        )
    for section in to_research:
        notes.append(f"New component `{section}` — researching before it is planned.")
        # NOT `research_dir` — that parameter is the PRODUCT pool the triage and
        # sprint children work from, and rebinding it here would hand the
        # loop-back below the wrong pool. A shadowed parameter is a silent
        # wrong-argument bug.
        component_pool = own.component_dir(worktree, section) / "research"
        component_pool.mkdir(parents=True, exist_ok=True)

        # THE BRIEF DEPENDS ON WHICH SIGNAL BROUGHT THE COMPONENT HERE, and
        # getting that wrong hands the model a FALSE PREMISE. A scaffolded
        # component has no sprint section — `sprint.md` is the operator's file
        # and nothing in this pipeline writes it — so telling the child to "read
        # that section first" would send it to look for something that does not
        # exist and cannot be created. It gets pointed at the seeded synthesis
        # instead, which is where its actual brief was just written.
        #
        # In both cases the child's Stage 1 already reads the destination's
        # planning docs to drive its topics, so a hand-written task file would
        # be restating what it is about to read.
        if section in scaffolded:
            context = (
                f"A new component `{section}` was just scaffolded from a shipped "
                f"research candidate and has no research and no phase doc yet. "
                f"Read `{component_pool.relative_to(worktree)}/synthesis.md` first "
                f"— it names the candidate this came from and carries the summary "
                f"as filed, and it is your brief. It has NO sprint section: "
                f"planning follows this research, not the other way round."
            )
        else:
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
        # had not. The whole class is now counted — the four build-family sites
        # too, two of which were telling a MODEL it was the last pass — and
        # `test_loop_cap_prose_is_counted.py` fails any new hard-coded claim. The
        # research family keeps its own `MAX_LOOPS = 1`, so its identical wording
        # is TRUE and is left alone.
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

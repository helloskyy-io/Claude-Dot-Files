"""plan-verify — read ONE component's plan COLD, size it, and say where it is weakest.

Folder holds this file plus its own I/O (§10.1 rules 3 and 6); the family's
shared capability lives in `plan_activities`.

**This is the READ half of the planning split, and it completes a pattern the
other two families finished first.** Research is `research-draft` ->
`research-verify` because *"a separate fresh-context run verifies it… the run
that wrote an artifact defends it"*; build is `build-draft` -> `build-refine`
because *"the fresh context is the point, not an implementation detail."*
`plan-draft` shipped as the write half with its judge named and unbuilt — its
docstring said outright that this workflow *did not exist yet*. This is that
reviewer, and that sentence is now corrected at all three places `plan-draft`
made it, rather than left standing as the quotation it used to be here. A
quotation attributed to a file it no longer appears in is the defect C-gbclnzsq
proposes gating; repeating it to justify this module would have created one.

IT IS A SEPARATE WORKFLOW AND NOT A STAGE, on the argument that made
`triage-candidates` its own run: a judge inside the producing dispatch shares the
producer's context, which is the one property it exists not to have. Adding a
sixth stage to `plan-draft` would have produced a review written by the run
that had just talked itself into the decomposition.

THE FIVE QUESTIONS, AND THE FIFTH IS THE ONE THE PRODUCER CANNOT ANSWER:

  1. **Sizing** — an hour estimate per phase, from the phase's complexity.
  2. **Does each phase end at ONE verifiable outcome?** A phase ends where
     something can be demonstrated, not where the author ran out of scope.
  3. **Did a producer ship without its consumer?** A phase that builds a thing
     nothing yet reads is a phase that cannot be demonstrated.
  4. **Does the cited evidence actually support the phase?** Following a citation
     into the pool is work the author, who chose it, will not do again.
  5. **Where is this plan WEAKEST?** `plan-draft`'s own prompt requires its
     report to ask this — *"where is this plan weakest, and what would a reader
     who has not read your research most likely challenge?"* — and structurally
     cannot answer it, because the reader who has not read the research is the
     one thing the author is not.

HOURS LIVE IN `roadmap.md` AND NOWHERE ELSE, which is a decision this workflow
makes rather than one it inherits. Two arguments, and the second is the harder
one:

  * **Coverage.** `plan-draft` writes a roadmap entry and NO phase doc for a
    phase gated on something outside the component. A phase-doc-only sizing
    therefore cannot size a gated phase — the phase whose cost an operator most
    needs before deciding whether to unblock it.
  * **One figure, one home.** A number restated in two places with nothing
    deriving it is the class this repo has paid for repeatedly; `candidates.md`
    C-523klr8n names it and `test_measurement_figures_are_cited.py` is the gate built
    after four consecutive passes each corrected a figure at its source and left
    a copy standing. The enforcement here is not a second scanner — it is the
    write grant, which reaches `roadmap.md` and no other file in the component.

**AND THE HANDOFF TO `plan-sprint` DOES NOT WORK TODAY. This is stated in code
because it is the kind of fact a reader will otherwise assume.** `plan-sprint`
sizes against a 160-hour calibration precisely because no per-phase figure
existed; now one does, and it still cannot see it. Its prompt says *"You never
open a phase doc"*, its `EXISTING_WORK` block enumerates component directories,
research syntheses, pool papers and open issues — never a `roadmap.md` — and
neither `plan_sprint_workflow` nor `plan_activities` contains a reader for an
hour figure. Wherever these estimates were written, that workflow would not pick
them up. Closing it is a change to `plan-sprint`, which is deliberately NOT made
here: one workflow's fix becoming another's regression is exactly what a silent
edit to a neighbour produces.

WHAT IT DELIBERATELY DOES NOT DO:

  * **It does not re-plan.** It writes no phase doc, merges no phases, invents
    none. A decomposition it judges wrong is a FINDING, and the runway a finding
    opens is `plan-draft`'s to close.
  * **It does not write `sprint.md`.** That file is the operator's cross-domain
    sequencing surface and `plan-sprint` carries the single bounded override.
  * **It renames and renumbers nothing.** A phase number is IDENTITY.
  * **It touches ONE component.** Everything else under `docs/development/` is
    forbidden, and so is this component's own `research/` — that pool is the
    evidence question 4 is asked against, and a reviewer who edits the evidence
    has made the evidence agree with the review.

WHY IT IS SEPARATELY DISPATCHABLE. The same shape and the same reason as
`triage_candidates` and `plan_draft`: a shim, a runner, and a workflow function
a parent calls. Two of this repo's component directories carry a `roadmap.md`
today — measured with `find docs/development -maxdepth 2 -name roadmap.md` — so
running this child alone against one is both the cheap test and real work.

NOT IDEMPOTENT (§7.1): it pushes commits and opens PRs. Under Temporal a retry is
a NEW ATTEMPT, not a replay.
"""

from __future__ import annotations

import re
from pathlib import Path

from ... import routing

from .. import plan_activities as act
from . import plan_verify_activities as own

_HERE = Path(__file__).resolve().parent
PROMPTS = _HERE / "prompts"

MODEL_KEY = "plan-verify"

# An ESTIMATE, stated as one — nothing has measured this workflow. The basis and
# the revise-from-measurement note live with the value in config.yaml.
WORKFLOW_KEY = "plan-verify"   # NOT MODEL_KEY -- see run_claude's docstring
MAX_TURNS = act.max_turns(WORKFLOW_KEY)

COMPLETION_PATTERN = routing.PR_URL_COMPLETION_ERE

# --- THE PATH BOUNDARY, DECLARED WHERE THE PROMPT'S TABLE CAN BE READ AGAINST IT
#
# Every path-scoped `You MAY NOT` row in `prompts/plan_verify.md`, as a pattern.
# `docs/development/` is denied WHOLESALE and one file is granted back below,
# which is the only ordering that makes a reviewer's boundary say what it means:
# an allowlist alone would say nothing about the sibling components, and
# `sprint.md` lives in that same directory.
#
# THIS TUPLE IS NOW BYTE-IDENTICAL TO `plan_draft`'s AND `triage_candidates`',
# AND IT IS DELIBERATELY NOT PROMOTED. A review pass raised it as §10.1 rule 3 —
# three consumers, consumer count decides — and the disposition is REJECTED, with
# the reasoning recorded here so it is not re-derived every time somebody counts
# to three.
#
# The rule promotes what more than one workflow USES. These three do not use one
# thing: each DERIVES its own boundary from its own prompt's `You MAY NOT` table,
# and the three tables currently happen to forbid the same paths. `plan_sprint`'s
# is already a different two-pattern set, for a reason specific to it — it holds
# the family's only override to write `sprint.md`. Promoting the coincidence would
# make a reword of one prompt's table silently change three workflows'
# authorization boundaries, which is a strictly worse failure than the
# three-lockstep-edits it avoids: the edits at least appear in a diff.
#
# The mechanism that keeps these honest is `MAY_NOT_OBSERVERS`, which is keyed by
# each row's exact prompt text and fails when a row is reworded. That is the
# coupling worth having, and it is per-workflow by construction.
FORBIDDEN_PATHS = (
    r"^docs/development/",      # "Edit a phase doc, or anything under another component"
    r"(^|/)sprints?\.md$",      # "WRITE or edit `sprint.md`" — also caught above,
                                #   stated separately because the prohibition is
                                #   about the FILE and outlives this directory
    r"^docs/standards/",        # "...or anything else under `docs/standards/`"
    # THE TRACKED STORES, ADDED 2026-08-26 WITH THE FLIP, AND IT RESTORES A
    # PROPERTY RATHER THAN ADDING ONE. `candidates.md` used to live under
    # `docs/standards/architecture/research/`, so it was already inside a
    # forbidden tree and `permitted_paths` was a CARVE-OUT of it. The store is
    # root-relative now — that is what lets one implementation serve every repo
    # — and `tracked/` matches neither prefix above, so the flip silently took
    # all four stores OUTSIDE the boundary. A planning run could have written
    # `tracked/operations/`, which Tracked Items §1.2 reserves to humans, and
    # nothing here would have seen it. Forbidding the tree and granting one pool
    # back is exactly the shape this boundary had before the move.
    r"^tracked/",
)


def permitted_paths(component_rel: Path, candidates_rel: Path) -> tuple[str, ...]:
    """The two grants this run holds, BOTH computed from this run's own arguments.

    A FUNCTION AND NOT A CONSTANT, for the reason `plan_draft.permitted_paths`
    states: half of this boundary is an argument, so a module-level tuple would
    either grant every component at once — deleting the boundary — or hard-code
    one, which is worse.

    BOTH HALVES ARE ARGUMENTS, and the second one used to be a literal. The
    candidates file is an operator input — `--candidates` is a documented flag on
    every runner in this family, and it is the flag a DIFFERENT repository is
    targeted through, since `--repo` points at a tree whose pool need not sit at
    this repo's path. A hard-coded grant made that flag guarantee failure: the
    prompt was handed `CANDIDATES_PATH` and told to append a proposal there,
    while `boundary_crossings` — which the operator's path still matches, because
    `^docs/standards/` denies the whole tree — read the model obeying its
    instructions as a boundary crossing and failed a correct run at the last
    guard, after all the work. The grant now follows the same path the prompt and
    the column guards already do, so the three cannot disagree.

    THE GRANT IS ONE FILE, NOT A SHAPE, AND THAT IS THE WHOLE DIFFERENCE FROM THE
    WRITE HALF. `plan-draft`'s grant is `<component>/[^/]+\\.md$` because it
    writes a roadmap and N phase docs; this workflow writes one file. Expressing
    it as `roadmap\\.md$` rather than as a shape is what makes *hours live in one
    place* enforced by the boundary check that already exists, instead of by a
    second scanner sweeping the files this run cannot reach anyway. A reviewer
    that may edit a phase doc is a reviewer that can quietly rewrite the plan it
    was sent to judge.

    `re.escape` ON THE COMPONENT SEGMENT, and it is a correctness requirement
    rather than hygiene: the segment is an operator-supplied directory name on
    the standalone path, where nothing slugs it. A component named
    `v2.1-migration` interpolated raw makes `.` match any character, so the grant
    reaches `v2x1-migration/roadmap.md` too — the boundary silently widening to a
    sibling is the one failure this module exists to prevent.

    The `candidates.md` grant is the shared `decision_log_and_reflection`
    instruction's rather than this workflow's own: every producing run is
    required to PLACE a proposal it surfaces instead of leaving it in a PR body
    to die at merge. It comes with the column guards below.
    """
    return (
        # WIDENED 2026-08-19 from `roadmap.md` alone to every top-level markdown
        # file in the component — the same grant `plan_draft.permitted_paths`
        # holds, and for a reason the two now share. This run may CORRECT a
        # determined defect in a phase doc; it may not RE-PLAN. Those were one
        # prohibition enforced by this grant, and separating them moves the
        # enforcement to the observers that were always the real check:
        # `roadmap_phase_links` for add/merge/split/drop, `ids_deleted` over
        # `phase_docs_of` for a disappearance, and `plan_boxes` below for a
        # ticked or reworded checkbox. The grant was never what stopped a
        # re-plan; it stopped ALL editing, which is what parked a one-sentence
        # fix as a fifteen-hundred-byte candidate row.
        rf"^{re.escape(component_rel.as_posix())}/[^/]+\.md$",
        # THE CANDIDATES POOL IS A DIRECTORY since the 2026-08-26 flip, so the
        # grant covers the ITEMS in it. A run places its proposal as one file
        # there; an exact match on the directory would grant a path nothing
        # writes and fail every correct placement at the last guard. Same shape
        # as the component grant above, and `[^/]+` for the same reason.
        # THE CANDIDATES GRANT IS GONE, 2026-08-26, BY OPERATOR RULING. This
        # workflow used to write `tracked/candidates/` directly, under a
        # "proposals only" carve-out in the vendored Documentation Standard. The
        # carve-out was written on 2026-08-09 for one reason: `review-pr` is
        # decide-only and could not write a FILE surface at all, so the producing
        # run was the only actor who could. **INTAKE removed that constraint**,
        # and a workaround outliving its cause is the thing this repo keeps
        # paying for.
        #
        # THE RULE IS NOW ONE RULE WITH NO EXCEPTION: a producing run SURFACES a
        # finding in its report and stops; `review-pr` files it. Two of the three
        # autonomous stores already worked that way — `issues/` and `standards/`
        # were never reachable from here — and candidates was the odd one out.
        #
        # WHY THE REVIEWER AND NOT THE AUTHOR, in the operator's own framing: the
        # second set of eyes is not invested in defending the suggestion. And the
        # cost is asymmetric in a way the old design missed — if the reviewer can
        # only HOLD the PR, rejecting a bad candidate costs a correction dispatch
        # and a re-review; if the reviewer is the filer, a bad candidate costs
        # nothing, because it is simply never written.
    )


def prompt_values(rel_component: Path, rel_candidates: Path, tree: Path,
                  pr_number: str | None, context: str = "") -> dict[str, str]:
    """Every placeholder the prompt takes, assembled ONCE for both callers.

    THE DRY RUN AND THE REAL RUN MUST RENDER THE SAME PROMPT, and this exists so
    they cannot drift. `plan_sprint.correction_note`'s docstring records this
    family shipping exactly that bug: a runner assembling its own copy of a
    workflow's values dict previewed a prompt that was not the one dispatched,
    and an operator checking the wrong artifact is worse than checking none.
    `test_dry_run_previews_the_dispatched_prompt.py` holds the shape.

    `tree` IS THE TREE THE COUNTS ARE TAKEN FROM: the worktree on the live path,
    the repo on the dry-run path, where no worktree exists yet.
    """
    component = tree / rel_component
    return {
        "COMPONENT_PATH": rel_component.as_posix(),
        "COMPONENT_NAME": rel_component.name,
        "CANDIDATES_PATH": rel_candidates.as_posix(),
        "PLAN_INVENTORY": own.plan_inventory(component, tree),
        # The tree-wide pointer, alongside the component-scoped one above. It
        # teaches the pool convention and names the thesis; `PLAN_INVENTORY` says
        # which plan is THIS run's, which the shared block cannot know.
        "EVIDENCE_BLOCK": act.evidence_block(tree),
        # OPAQUE, rendered verbatim. Before this existed `--pr` changed where a
        # run PUSHED and nothing else, so a correction pass could not be told why
        # it was re-running — the same gap `plan-draft` had until 2026-08-19.
        "TASK_CONTEXT": (
            "## OPERATOR CONTEXT FOR THIS RUN\n\n"
            "**This is authoritative and overrides your own reading where they "
            "disagree** — it is the operator speaking, not another run's account. "
            "Verify any FACT it asserts about the tree before building on it.\n\n"
            + context if context.strip() else ""
        ),
        "FILING_A_CANDIDATE_ROW": act.shared_prompt("filing_a_candidate_row"),
        "SUBMIT_PROMPT": act.submit_prompt(
            pr_number, f"plan-verify: size and judge {rel_component.name}"),
        "WORKTREE_IS_COMPARED_TO_A_SNAPSHOT": act.shared_prompt("worktree_is_compared_to_a_snapshot"),
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
        "HEADLESS_EXECUTION_GUARD": act.shared_prompt("headless_execution_guard"),
        "SWEEP_THE_CLASS": act.shared_prompt("resolve_sweep_the_class"),
    }


# --- EVERY `You MAY NOT` ROW, AND WHAT OBSERVES IT ---------------------------
#
# See `triage_candidates_workflow.MAY_NOT_OBSERVERS` for why this map exists and
# why it is keyed by the row's exact text — CITED rather than restated, which is
# the convention `plan_sprint_workflow` and `plan_draft_workflow` both follow,
# so a correction to the argument lands in one place instead of drifting across
# four copies. `test_authorization_is_observed.py` compares these keys against
# the rendered table, over a DISCOVERED set of workflows, and `JUDGEMENT` is a
# legitimate answer that must say why the property has no artifact.
#
# WHAT WRITING THIS TABLE ACTUALLY PRODUCED, since that is the argument for it
# rather than a claim about it: the honest answer to *what observes "re-plan the
# component"?* was **nothing**. Every other prohibition here is a path the
# boundary check already sees, and that one happens entirely inside the single
# file this workflow's grant opens — where `boundary_crossings` is blind by
# construction. `own.roadmap_phase_links` exists because the row would not
# otherwise have been allowed to say anything true.
MAY_NOT_OBSERVERS: dict[str, str] = {
    "**Write an hour estimate anywhere but `roadmap.md`** — one figure, one home":
        "the same mechanism, and the grant IS the enforcement rather than a "
        "scanner beside it: `roadmap.md` is the only file in the component this "
        "run can reach, so a figure has nowhere else to go. own.roadmap_hours "
        "then proves it went there",
    "**Rename, renumber or delete a phase doc** — the number is IDENTITY":
        "FORBIDDEN_PATHS `^docs/development/` for the EDIT, plus act.ids_deleted "
        "over own.phase_docs_of either side of the run for the DISAPPEARANCE. "
        "The second is not redundant with the first: a vanished doc does reach "
        "boundary_crossings through act.worktree_state's ABSENT sentinel, but "
        "that is the LAST guard, and a run that also under-sized reached the "
        "sizing message first — a true failure naming the wrong cause, which is "
        "the defect this file already reorders one guard to avoid",
    "**WRITE or edit `sprint.md`** — read it (Stage 1), never touch it":
        "FORBIDDEN_PATHS, via act.worktree_state / act.boundary_crossings",
    "Write or edit anything under ANOTHER component, or under this one's `research/`":
        "FORBIDDEN_PATHS `^docs/development/` less permitted_paths, which grants "
        "one named file and so reaches no sibling and no subdirectory",
    "**Tick a completion checkbox** — nothing has been built":
        "act.plan_boxes — act.checked_boxes over EVERY top-level doc the grant "
        "permits, not the roadmap alone — counted either side and compared in "
        "BOTH directions. Widened with the grant: a phase doc shipping with its "
        "steps pre-ticked is the likelier mistake now that phase docs are "
        "writable, since that is where the implementation checklist lives",
    "**Reword a completion criterion** — a checkbox is the author's sentence":
        "act.plan_boxes is a Counter keyed by the box's TEXT, so a reworded "
        "criterion presents as one text gone and one text arrived — caught by "
        "the same both-directions comparison, without a second mechanism",
    "**RE-PLAN the component** — add, merge, split or drop a phase, or change what one delivers":
        "own.roadmap_phase_links counted either side and compared in BOTH "
        "directions for add/merge/split/drop, plus act.ids_deleted over "
        "own.phase_docs_of for a phase that vanished. JUDGEMENT for the last "
        "clause: prose inside a granted file cannot be told from a correction "
        "by any comparator, and it is held by the report's integrity clause — "
        "every correction named, with whether it moved an estimate",
    "Write ANY `tracked/` store — you surface, `review-pr` files":
        "FORBIDDEN_PATHS `^tracked/` with NO grant carved back, via "
        "act.worktree_state / act.boundary_crossings — the whole tree is a "
        "crossing now. The four per-field comparators this row used to name "
        "(act.decisions_this_run_had_no_right_to and its siblings) answered a "
        "narrower question: did a run that MAY write the store change a field "
        "it does not own. This workflow may not write the store at all, so the "
        "path check answers it one altitude up and the field checks have no "
        "subject here. Operator ruling 2026-08-26: a producing run surfaces and "
        "`review-pr` files, for all three autonomous stores, no exception",
    "Edit `problem-statement.md`, `architectural_standard.md`, or anything else under `docs/standards/`":
        "FORBIDDEN_PATHS `^docs/standards/` less permitted_paths, same mechanism",
    "**Delete anything** — a phase doc or the roadmap":
        "act.ids_deleted over the candidate id snapshots for a ROW, "
        "act.ids_deleted over own.phase_docs_of for a PHASE DOC, and "
        "act.grants_that_vanished over permitted_paths for the two files this "
        "run may write — one comparator per altitude, because the message each "
        "has to produce is different",
    "Decide WHEN this component gets built, or where it sits against other work":
        "JUDGEMENT — a total this workflow produces is an INPUT to sequencing and "
        "the sequencing itself leaves no artifact distinct from the report it is "
        "required to write. The file that would carry the decision is "
        "`sprint.md`, and that one IS observed; what cannot be separated "
        "mechanically is a report that sizes the work from one that schedules it, "
        "since both are prose about the same hours.",
}

# --- EVERY BEFORE/AFTER SNAPSHOT, AND WHAT WATCHES IT FOR ABSENCE ------------
#
# See `triage_candidates_workflow.DISAPPEARANCE_OBSERVERS` for the class and why
# it is keyed by the SNAPSHOT rather than by the prohibition — cited, not
# restated. `test_disappearance_is_observed.py` discovers every `before*` local
# by AST, so a snapshot added later has no entry and fails the suite until
# somebody answers "what watches this one for absence?"
DISAPPEARANCE_OBSERVERS: dict[str, str] = {
    "before_phases": (
        "act.ids_deleted against own.phase_docs_of read again after the run, "
        "checked AHEAD of the sizing guard. This snapshot is read for its COUNT "
        "— the deliverable's floor — and registering it forced the second "
        "question the count alone never asks: a phase doc deleted while the "
        "roadmap's reference to it survives moves neither of the two guards "
        "above, and reaches only the boundary check at the very end, by which "
        "time the sizing message has already blamed the wrong thing."),
    "before_links": (
        "own.roadmap_phase_links compared in BOTH directions — and here the "
        "disappearing direction is the PRIMARY one rather than a corner case: a "
        "judge that quietly drops a phase it disagreed with removes a link, and "
        "Counter subtraction one way round reports nothing at all. A roadmap "
        "deleted outright yields an empty Counter, which is why "
        "act.grants_that_vanished runs ahead of this."),
    "before_decision": (
        "act.ids_deleted against the after-snapshot of the same column, checked "
        "BEFORE the column comparisons because a vanished row is in neither "
        "intersection those judge"),
    "before_size": (
        "act.ids_deleted on the SAME id set, by the coupling registered against "
        "before_status — one parse, one id set"),
    "before_status": (
        "act.ids_deleted on the SAME id set, already run against before_decision "
        "— act.candidate_decisions, act.candidate_sizes, act.candidate_statuses and "
        "act.candidate_components are all built from act.candidate_rows, so a row "
        "cannot be absent from one map and present in another. Registered rather "
        "than left implicit because that coupling is the whole reason a second "
        "deletion check here would be dead code, and the coupling itself is held "
        "by test_the_two_candidate_READERS_ALWAYS_KEY_THE_SAME_ROWS."),
    "before_component": (
        "act.ids_deleted on the SAME id set, by the same coupling registered "
        "against before_status — one parse, one id set, four columns"),
    "before_boxes": (
        "act.plan_boxes over EVERY top-level doc the grant permits — widened with "
        "the grant on 2026-08-19, since a phase doc shipping with its steps "
        "pre-ticked is the likelier mistake once phase docs are writable — "
        "counted either side and compared in "
        "BOTH directions — so an ERASED tick is an offence exactly as an added "
        "one is. A plan reporting work nobody built is bad; a plan that has "
        "forgotten work somebody did is worse, because nothing downstream will "
        "ask for it again."),
    "before_tree": (
        "act.grants_that_vanished over permitted_paths for the two files this run "
        "may write; act.boundary_crossings for every other path, where a deletion "
        "already reads as a content change via the ABSENT sentinel"),
}


def run_plan_verify(*, repo_root: Path, worktree: Path, component: Path,
                    candidates_path: Path, pr_number: str | None = None,
                    context: str = "", verbose: bool = False) -> str:
    """Read ONE component's plan cold, size it, judge it. Returns the PR URL."""
    # Paths arrive rooted at the REPO because that is where they are configured,
    # but the run reads and writes inside the WORKTREE. Resolve once, read what
    # the model will actually see, and later re-read what it actually wrote.
    rel_component = component.relative_to(repo_root)
    rel_candidates = candidates_path.relative_to(repo_root)
    wt_component = worktree / rel_component
    wt_candidates = worktree / rel_candidates
    permitted = permitted_paths(rel_component, rel_candidates)

    # THE DELIVERABLE'S FLOOR, READ BEFORE THE MODEL RUNS. Every phase doc is a
    # phase and every phase needs an estimate. A phase that is GATED has a
    # roadmap entry and no doc, so this count is a FLOOR rather than the true
    # number — narrower than the rule, which is the safe direction for a guard:
    # it cannot fail a correct run, and the prompt carries the rest.
    #
    # THE SAME SNAPSHOT IS ALSO THE IDENTITY BASELINE, which is why it is named
    # `before_` and carries a `DISAPPEARANCE_OBSERVERS` row. One read, two
    # questions: *how many phases must be sized* and *are they all still here*.
    before_phases = own.phase_docs_of(wt_component)

    # SNAPSHOTTED AROUND THE MODEL, never diffed against `origin/main`: this
    # workflow runs after two siblings on the same branch inside `plan-project`,
    # and a diff against the base would attribute their legitimate edits to it.
    before_links = own.roadmap_phase_links(wt_component)
    before_decision = act.candidate_decisions(wt_candidates)
    before_size = act.candidate_sizes(wt_candidates)
    before_status = act.candidate_statuses(wt_candidates)
    before_component = act.candidate_components(wt_candidates)
    before_boxes = act.plan_boxes(wt_component)
    before_tree = act.worktree_state(worktree)

    values = prompt_values(rel_component, rel_candidates, worktree, pr_number,
                           context)

    output = act.run_claude(
        act.render(act.load_prompt(PROMPTS / "plan_verify.md"), values,
                   opaque=frozenset({"TASK_CONTEXT"})),
        model_key=MODEL_KEY, workflow_key=WORKFLOW_KEY,
        completion_pattern=COMPLETION_PATTERN,
        repo_root=repo_root, worktree=worktree,
        max_turns=MAX_TURNS, verbose=verbose,
    )

    url = act.extract_pr_url(output)
    if not url:
        raise RuntimeError(
            f"plan-verify produced no PR URL for `{rel_component}`. Its judgement "
            f"is UNSUBMITTED and this component is UNSIZED — whatever the exit "
            f"code says, nothing downstream may treat this plan as reviewed. "
            f"Inspect the worktree before re-dispatching; the work may be there."
        )

    after_tree = act.worktree_state(worktree)

    # A WRITE GRANT IS NOT A DELETE GRANT, and this is checked before every
    # READER below, because each of those assumes the file it parses is still
    # there. Deleting the roadmap would otherwise surface as an empty Counter
    # from the sizing guard — a true failure naming the wrong cause, and the
    # cause it names ("you sized nothing") is one a run would try to fix by
    # writing the file back, which is not the same file.
    vanished = act.grants_that_vanished(before_tree, after_tree, permitted)
    if vanished:
        raise RuntimeError(
            f"plan-verify made {len(vanished)} file(s) it may WRITE cease to "
            f"exist: {', '.join(vanished)}. The permission covers editing them and "
            f"nothing further. `roadmap.md` is the component's whole plan — every "
            f"phase doc is reachable only through it — and `candidates.md` is the "
            f"running proposal list every workflow in this family appends to — "
            f"see {url}"
        )

    # RE-PLANNING, WHICH IS THE ONE PROHIBITION THAT HAPPENS INSIDE THE GRANTED
    # FILE. `boundary_crossings` exempts `roadmap.md` unconditionally — it must,
    # since writing it is the job — so a judge that dropped a phase it disagreed
    # with, merged two it thought redundant, or invented one it thought missing
    # would return a PR URL and a green run. Compared in BOTH directions: a phase
    # ADDED is a plan this run wrote rather than judged, and a phase REMOVED
    # destroys the only pointer to a document that still exists on disk.
    #
    # CHECKED BEFORE THE SIZING GUARD, WHICH IS A REORDERING AND NOT AN ACCIDENT.
    # The sizing floor counts phase DOCS, and dropping a phase's roadmap entry
    # takes its estimate with it — so the commonest re-planning offence ALSO
    # trips the deliverable guard, and with that one first the operator was told
    # "you sized nothing" about a run that had deleted a phase. That is a true
    # failure naming the wrong cause, and the remedy its message suggests — add
    # an estimate — leaves the dropped phase dropped. The write half shipped the
    # identical defect (its identity message was unreachable behind a generic
    # grant check) and this is that lesson applied at authoring time rather than
    # after a review. Nothing is weakened by the swap: this guard parses only the
    # roadmap, which `grants_that_vanished` above has already proven still exists.
    # COMPARED AS SETS, NOT AS COUNTS, AND THAT DISTINCTION IS THE WHOLE GUARD.
    # The prohibition is *do not add, merge, split or drop a PHASE* — a question
    # about WHICH phases the roadmap references, never HOW MANY TIMES each is
    # mentioned. `roadmap_phase_links` returns a Counter, so subtracting the
    # Counters compared multiplicity: a run that added two cross-references to a
    # phase already referenced six times was reported as having ADDED it twice.
    #
    # MEASURED ON PR #144, AND THE RUN SAW IT COMING. `plan-verify` wrote a
    # sizing note that legitimately linked a sibling phase, took Phase 2 from 6
    # references to 8, and failed here with the phase set IDENTICAL — nothing
    # added, merged, split or dropped, exactly as it self-reported. Its own
    # reflection had already reasoned it out: *"if the check is count-based
    # rather than set-based it will fail runs for doing the right thing... I
    # kept the cross-references and accepted the risk rather than dropping a
    # useful link to game a check."* A guard that punishes the correct choice
    # teaches runs to degrade their output, which is worse than no guard.
    #
    # AND IT BROKE THE CHAIN, not just the run: `plan_project` calls this child
    # unguarded, so the raise propagated and `plan-sprint` was never reached.
    after_links = own.roadmap_phase_links(wt_component)
    added = sorted(set(after_links) - set(before_links))
    dropped = sorted(set(before_links) - set(after_links))
    if added or dropped:
        raise RuntimeError(
            f"plan-verify changed which phases `{rel_component}/roadmap.md` "
            f"references: "
            + "; ".join([f"ADDED {n}" for n in added]
                        + [f"DROPPED {n}" for n in dropped])
            + f". You judge the decomposition; you do not rewrite it. A phase "
            f"boundary you believe is wrong is a FINDING — say so in your report "
            f"and let `plan-draft` close the runway, because the phase docs are "
            f"its output and you hold no grant over them. A dropped reference is "
            f"the worse half: the document is still on disk with nothing pointing "
            f"at it — see {url}"
        )

    # A PHASE DOC THAT VANISHED, CHECKED BEFORE SIZING FOR THE SAME REASON THE
    # RE-PLANNING GUARD IS. Deleting a phase doc while leaving the roadmap's
    # reference to it standing is invisible to BOTH guards above:
    # `grants_that_vanished` watches only the two files this run may write, and
    # `roadmap_phase_links` reads a roadmap that did not change. It reaches
    # `boundary_crossings`, which is the LAST guard — so a run that also
    # under-sized was told "you sized nothing" about a run that had deleted a
    # phase, and the remedy that message suggests leaves the document deleted.
    # That is the identical misdirection this file already reorders the sizing
    # guard to avoid, arriving by a second route; the write half runs exactly
    # this comparison as its FIRST guard for the same reason.
    #
    # `ids_deleted` AND NOT A CONTENT COMPARE: a phase doc EDITED is a boundary
    # crossing and the last guard names it correctly. Only DISAPPEARANCE needs
    # its own message, because only disappearance is what the generic message
    # gets wrong.
    after_phases = own.phase_docs_of(wt_component)
    lost = act.ids_deleted(before_phases, after_phases)
    if lost:
        raise RuntimeError(
            f"plan-verify made {len(lost)} phase doc(s) in `{rel_component}` "
            f"cease to exist: {', '.join(lost)}. You hold NO grant over a phase "
            f"doc — not to edit one, and least of all to remove one. A phase "
            f"number is IDENTITY, so a deleted doc is not a phase re-scoped, it "
            f"is a phase erased, and `roadmap.md` may still point at it. A "
            f"decomposition you judge wrong is a FINDING for `plan-draft` to "
            f"act on — see {url}"
        )

    # THE DELIVERABLE, OBSERVED RATHER THAN ASSERTED, and it is keyed on STATE
    # rather than on a delta — the opposite of every PROHIBITION guard in this
    # family, deliberately. A `--pr` correction pass that leaves the previous
    # pass's estimates exactly where they are has written no new hours and is
    # entirely correct; a delta-shaped guard would fail precisely the pass most
    # likely to be the last one anybody reads. The prohibitions around it stay
    # deltas, because those ask what THIS RUN DID.
    #
    # WHAT THIS GUARD DOES NOT LOOK AT, STATED FIRST, because a floor that reads
    # as a per-phase check is worse than one that reads as what it is. It
    # compares a TOTAL COUNT of estimates against a COUNT of phases. It has no
    # idea WHICH phase any given estimate sits beside, so two figures written
    # against one phase cover a phase with none — and the prompt permits *"a
    # short sizing note beside an estimate"*, which is one plausible way to write
    # a second. **The guard is a NECESSARY condition on the deliverable and not a
    # sufficient one**, the reviewer reading the report is the sufficient one,
    # and the failure message below says so rather than reporting SIZED-or-not.
    #
    # A PER-PHASE ASSOCIATION WAS ATTEMPTED AND IS BLOCKED BY THE CORPUS, twice
    # over, which is why the floor stays a floor rather than being tightened:
    #   * Chunking the roadmap by phase HEADING needs a heading grammar the
    #     Documentation Standard does not fix, and its own worked example puts
    #     the estimate IN the heading — above the link, so a chunk keyed on the
    #     link attributes it to the previous phase and fails a correct run.
    #   * Requiring an estimate on each phase-REFERENCE line fails a correct run
    #     outright: `roadmap_phase_links` matches CROSS-COMPONENT references by
    #     design (the memory-management-framework roadmap carries three of
    #     persistent-memory-protocol's), and those are not this component's
    #     phases to size. That over-count is a defect this file already fixed
    #     once, in `plan_inventory`; re-introducing it as a guard is worse.
    # Narrower is the safe direction for a guard — it cannot fail a correct run —
    # and the residual is named here and pinned by a test rather than assumed.
    #
    # THE FLOOR IS ALSO THE PHASE-DOC COUNT, WHICH IS NARROWER STILL. A GATED
    # phase has a roadmap entry and no doc, and it still needs sizing — the
    # prompt says so and this cannot count it.
    #
    # AND NARROWER HAS A BOTTOM, WHICH THE ARGUMENT ABOVE DID NOT REACH. Every
    # sentence of it is true while there is at least one phase doc; at ZERO —
    # the all-gated component, the shape the roadmap-as-home decision was MADE
    # for — `sum < 0` is unsatisfiable and the guard is not narrow, it is
    # absent. `own.sizing_floor` owns the threshold now, states that class in
    # full, and keeps the floor at one when a plan exists.
    hours = own.roadmap_hours(wt_component)
    floor = own.sizing_floor(wt_component, before_phases)
    if sum(hours.values()) < floor:
        found = own.hour_citations(wt_component, worktree) or ["(none)"]
        basis = (f"{len(before_phases)} phase doc(s)" if before_phases else
                 "a `roadmap.md` whose phases are ALL GATED — every one of them "
                 "still gets an estimate, and one is the least this can prove")
        raise RuntimeError(
            f"plan-verify left `{rel_component}` UNSIZED: its `roadmap.md` carries "
            f"{sum(hours.values())} hour estimate(s) against a floor of {floor}, "
            f"from {basis}. What is there:\n  "
            + "\n  ".join(found)
            + f"\nSizing is this workflow's whole load-bearing output — "
            f"`plan-draft` writes no hours and FAILS ITS RUN on one, so until "
            f"this lands the number does not exist anywhere. The estimates go in "
            f"`roadmap.md` and nowhere else: it is the only file in the component "
            f"this run may write, it is the only place a GATED phase (a roadmap "
            f"entry with no doc) can be sized at all, and one figure with one home "
            f"cannot drift from its copy — see {url}"
        )

    # THE FOUR CANDIDATE COLUMNS, none of which is this workflow's. The grant on
    # that file is to APPEND a proposal — a new row, blank `decision`, blank
    # `size`, `status: open`, and the `component` cell named on THAT row and no
    # other.
    #
    # DELETION FIRST, for the reason stated in the registry: both comparators
    # below judge only ids present on BOTH sides, so a row that is simply gone is
    # invisible to them.
    after_decision = act.candidate_decisions(wt_candidates)
    gone = act.ids_deleted(before_decision, after_decision)
    if gone:
        raise RuntimeError(
            f"plan-verify deleted {len(gone)} candidate row(s): {', '.join(gone)}. "
            f"No workflow deletes a row — a candidate ruled `reject` stays in the "
            f"file precisely so the next research cycle does not re-propose it, and "
            f"a row that merely disappears is indistinguishable from one that was "
            f"never proposed — see {url}"
        )

    ruled = act.decisions_this_run_had_no_right_to(before_decision, after_decision)
    if ruled:
        raise RuntimeError(
            f"plan-verify changed the `decision` column on {len(ruled)} "
            f"candidate(s): "
            + ", ".join(f"{cid} {before_decision[cid]!r}->{after_decision[cid]!r}"
                        for cid in ruled)
            + f". That column is `triage-candidates`' alone. A proposal you append "
            f"leaves `decision` BLANK, because blank means untriaged and untriaged "
            f"is the truth — judging a plan does not rule the candidates that come "
            f"out of it — see {url}"
        )

    after_size = act.candidate_sizes(wt_candidates)
    sized = act.sizes_this_run_had_no_right_to(before_size, after_size)
    if sized:
        raise RuntimeError(
            f"plan-verify set or changed the `size` column on {len(sized)} "
            f"pre-existing candidate(s): "
            + ", ".join(f"{cid} {before_size[cid]!r}->{after_size[cid]!r}"
                        for cid in sized)
            + f". `size` is `triage-candidates`' SECOND ruling and it belongs to "
            f"triage alone — this run read a plan and put a number beside each "
            f"phase, which is the closest thing to sizing that is not sizing, and "
            f"so the shortest step to writing it down. And the value does not stay "
            f"a cell: `plan-candidates` routes on it, so a `phase` written here "
            f"scaffolds a whole component for work that belongs inside one. A "
            f"proposal you append leaves `size` BLANK, because sizing is a ruling "
            f"and filing is not making it — see {url}"
        )

    after_status = act.candidate_statuses(wt_candidates)
    flipped = act.statuses_this_run_had_no_right_to(before_status, after_status)
    if flipped:
        raise RuntimeError(
            f"plan-verify changed the `status` column on {len(flipped)} "
            f"candidate(s): "
            + ", ".join(f"{cid} {before_status[cid]!r}->{after_status[cid]!r}"
                        for cid in flipped)
            + f". `status` belongs to the build that COMPLETES the item, and this "
            f"run has built nothing — it read a plan for work nobody has started "
            f"and put a number beside each phase — see {url}"
        )

    after_component = act.candidate_components(wt_candidates)
    named = act.components_this_run_had_no_right_to(before_component, after_component)
    if named:
        raise RuntimeError(
            f"plan-verify set or changed the `component` column on {len(named)} "
            f"pre-existing candidate(s): "
            + ", ".join(f"{cid} {before_component[cid]!r}->{after_component[cid]!r}"
                        for cid in named)
            + f". That column belongs to whoever FILED the row, because only they "
            f"know where the proposal goes — from a one-line summary anything else "
            f"is guessing. And the guess does not stay a cell: `plan-candidates` "
            f"turns a component name into a committed `docs/development/<name>/`. "
            f"Naming the component on a row YOU appended is permitted and required; "
            f"naming it on somebody else's is not — see {url}"
        )

    # A CHECKBOX MEANS *SHIPPED AND VALIDATED*, and this run has validated
    # nothing — it is reviewing the plan for work nobody has started. Scoped to
    # the roadmap because that is the only file it may write; a tick anywhere
    # else in the component is already a boundary crossing. Compared in BOTH
    # directions: erasing a tick is the same prohibition and the worse half.
    after_boxes = act.plan_boxes(wt_component)
    ticked = sorted((after_boxes - before_boxes).elements())
    erased = sorted((before_boxes - after_boxes).elements())
    if ticked or erased:
        raise RuntimeError(
            f"plan-verify flipped {len(ticked) + len(erased)} completion "
            f"checkbox(es) in `{rel_component}/{own.ROADMAP}`: "
            + "; ".join([f"TICKED {t!r}" for t in ticked]
                        + [f"ERASED {e!r}" for e in erased])
            + f". *Built is not proven* — a box marks work DEMONSTRATED, and "
            f"sizing a phase is the clearest possible case of not having built "
            f"it — see {url}"
        )

    # THE WHOLE DECLARED BOUNDARY, OBSERVED. One roadmap and the candidates file;
    # every phase doc, every sibling component, this component's own `research/`,
    # `sprint.md` and the standards tree are somebody else's.
    crossed = act.boundary_crossings(before_tree, after_tree,
                                     FORBIDDEN_PATHS, permitted)
    if crossed:
        raise RuntimeError(
            f"plan-verify edited {len(crossed)} file(s) outside its "
            f"authorization: {', '.join(crossed)}. This workflow READS one "
            f"component's plan and writes one line per phase into its roadmap. A "
            f"phase doc is `plan-draft`'s output — correcting it here would make "
            f"the artifact agree with the review, which is the whole reason the "
            f"author and the judge are separate runs. Its `research/` is the "
            f"evidence you are judging the citations against, and a sprint entry "
            f"is the operator's — see {url}"
        )
    return url

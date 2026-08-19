"""plan-feature — write ONE component's `roadmap.md` and its phase docs. Nothing else.

Folder holds this file plus its own I/O (§10.1 rules 3 and 6); the family's
shared capability lives in `plan_activities`.

WHY THIS IS ITS OWN WORKFLOW, AND WHY THE PLAN FAMILY IS THE LAST TO GET ONE.
The other two families were deconstructed and said why in their own words:
research is `research-write` -> `research-verify` because *"a separate
fresh-context run verifies it… the run that wrote an artifact defends it"*, and
build is `build-draft` -> `build-refine` on the same argument — *"the fresh
context is the point, not an implementation detail."* Planning never was:
`plan-revision` does ASSESS, PLAN, REVISE, PEER REVIEW and RESOLVE in ONE
context, so the run that wrote the decomposition is the run that reviews it.

**This is the WRITE half of that split, and `plan-verify` — the read half — NOW
EXISTS.** This paragraph used to say it did not, and that stopped being true the
day `plan_verify_workflow` landed: `plan_project._plan_one` calls
`plan_verify.run_plan_verify` immediately after this workflow, so a reference to
it here IS a dependency at the parent's altitude. It still is not one at THIS
module's — nothing in this file imports it, and this workflow remains separately
dispatchable with `review-pr --type planning` as its judge on that path.

*(Left as a correction rather than a rewrite because the false version was
load-bearing: this same claim was stated in three places — here, in
`prompts/plan_feature.md`, and in `run_plan_feature.py`'s completion banner — and
the PR that built `plan-verify` falsified all three and updated none.
`test_no_prose_claims_a_shipped_workflow_is_UNBUILT` is what fails now instead of
a reviewer noticing.)*

WHAT IT DOES NOT DO, AND EACH IS A DECISION RATHER THAN AN OMISSION:

  * **It estimates no hours.** Sizing is `plan-verify`'s, deliberately: an author
    sizing their own decomposition is defending it, and a fresh reader sizing it
    is a second opinion. Same `author != judge` rule, applied to a number — and
    the one prohibition here whose violation is a property of PROSE, which is why
    `own.hour_estimates` keys on estimate shape rather than on the word *hours*.
  * **It writes no `sprint.md`.** That file is the operator's cross-domain
    sequencing surface; `plan-sprint` carries the single bounded override for it
    and this workflow carries none. A component that needs a sprint entry is
    something to REPORT.
  * **It renames and renumbers nothing.** A phase number is IDENTITY — it names
    the phase for life, the way a ticket number does — and order lives in two
    mutable places instead: the roadmap's ordering within the component, and the
    sprint file's ordering across components. A phase ships first or last without
    its filename changing. This is stated because the opposite is an easy and
    expensive inference: this repo came within one dispatch of renaming sixteen
    phase files across forty-three references to buy a freedom it already had.
  * **It touches ONE component.** The whole of `docs/development/` outside its own
    directory is forbidden, and so is its own `research/` — that pool is evidence
    and is read-only here.

THE ASYMMETRY WITH SPRINTS IS THE RULE, NOT AN INCONSISTENCY.
[Documentation Standard § Sprint Structure](../../../../../../../docs/standards/documentation/documentation_standard.md)
binds *component sprints are named, never numbered*, because there an ordinal
encodes a judgement the plan exists to revise. **Phases are identities; sprints
are sequences.**

WHY IT IS SEPARATELY DISPATCHABLE. The same shape and the same reason as
`triage_candidates`: a shim, a runner, and a workflow function a parent calls.
Fourteen of this repo's sixteen component directories hold no roadmap and no
phase docs — measured, not asserted, with `find docs/development -maxdepth 2
-name roadmap.md` — so running this child alone against a real one is both the
cheap test and real work. A workflow runnable only inside `plan-project` would
cost a full planning cycle to exercise once.

`plan-revision` IS NOT REFACTORED AND MUST NOT BE. It works, it is standalone,
and its scope is broader than this one's — roadmaps, requirements, epics and
free-text descriptions, not one component's docs. This repo's answer to
near-duplication is stated and consistent: `build_draft` and `build_draft_minor`
are separate workflows for jobs closer together than these two. Distinct job,
distinct workflow, shared fragments, and never a flag switching one workflow
between two behaviours.

NOT IDEMPOTENT (§7.1): it pushes commits and opens PRs. Under Temporal a retry is
a NEW ATTEMPT, not a replay.
"""

from __future__ import annotations

import re
from pathlib import Path

from ... import routing

from .. import plan_activities as act
from . import plan_feature_activities as own

_HERE = Path(__file__).resolve().parent
PROMPTS = _HERE / "prompts"

MODEL_KEY = "plan-feature"

# An ESTIMATE, stated as one — nothing has measured this workflow. The basis and
# the revise-from-measurement note live with the value in config.yaml.
WORKFLOW_KEY = "plan-feature"   # NOT MODEL_KEY -- see run_claude's docstring
MAX_TURNS = act.max_turns(WORKFLOW_KEY)

COMPLETION_PATTERN = routing.PR_URL_COMPLETION_ERE

# --- THE PATH BOUNDARY, DECLARED WHERE THE PROMPT'S TABLE CAN BE READ AGAINST IT
#
# Every path-scoped `You MAY NOT` row in `prompts/plan_feature.md`, as a pattern.
# `docs/development/` is denied WHOLESALE and the component is granted back below,
# which is the only ordering that makes a one-component workflow's boundary say
# what it means: an allowlist alone would say nothing about the fifteen sibling
# components, and `sprint.md` lives in that same directory.
FORBIDDEN_PATHS = (
    r"^docs/development/",      # "Write or edit ANY file under another component"
    r"(^|/)sprints?\.md$",      # "WRITE or edit `sprint.md`" — also caught above,
                                #   stated separately because the prohibition is
                                #   about the FILE and outlives this directory
    r"^docs/standards/",        # "...or anything else under `docs/standards/`"
)


def permitted_paths(component_rel: Path, candidates_rel: Path) -> tuple[str, ...]:
    """The two grants this run holds, BOTH computed from this run's own arguments.

    A FUNCTION AND NOT A CONSTANT, because half of this boundary is an argument.
    This workflow's whole subject is *which component*, so a module-level tuple
    would either grant every component at once — deleting the boundary — or hard-
    code one, which is worse.

    BOTH HALVES ARE ARGUMENTS, AND THE SECOND ONE USED TO BE A LITERAL. That is a
    reachable failure of a CORRECT run, not a style point: `--candidates` is a
    documented flag on this runner and it is the flag through which a DIFFERENT
    repository's pool is targeted, since `--repo` points at a tree whose pool need
    not sit at this repo's path. With the grant hard-coded, the prompt was handed
    `CANDIDATES_PATH` and told to append a proposal there, `^docs/standards/`
    denied the whole tree, and `boundary_crossings` read the model obeying its own
    instructions as a crossing — failing the run at the LAST guard, after every
    turn had been spent, and presenting as *"the flag is broken"* rather than as
    *"the grant is a literal"*. The grant now follows the same path the prompt and
    the column guards already do, so the three cannot disagree.

    `re.escape` ON THE COMPONENT SEGMENT, the same way `plan_sprint` escapes its
    sprint path, and it is a correctness requirement rather than hygiene: the
    segment is an operator-supplied directory name on the standalone path, where
    nothing slugs it. A component named `v2.1-migration` interpolated raw makes
    `.` match any character, so the grant reaches `v2x1-migration/` too — the
    boundary silently widening to a sibling is the one failure this whole module
    exists to prevent. Inside `plan-project` the name has been through
    `component_slug` and cannot carry a metacharacter; the standalone dispatch is
    a documented, supported mode and has no such filter.

    `[^/]+\\.md$` IS THE LOAD-BEARING HALF OF THE FIRST GRANT. It permits files
    sitting DIRECTLY in the component directory — `roadmap.md` and the phase docs,
    which is the entire output — and by construction it permits nothing in a
    subdirectory. `research/` is the subdirectory that matters: it is this run's
    PRIMARY EVIDENCE and it is read-only, because a planning run that edits the
    evidence it is planning from has made the evidence agree with the plan.
    Expressed as a shape rather than as a second deny rule so the two cannot drift
    apart — there is no rule to forget to update when a component grows a
    directory.

    The `candidates.md` grant is the shared `decision_log_and_reflection`
    instruction's, not this workflow's own: every producing run is required to
    PLACE a proposal it surfaces rather than leave it in a PR body to die at
    merge. It comes with the column guards below, which are the same ones
    `plan-sprint` carries for the same grant.
    """
    return (
        rf"^{re.escape(component_rel.as_posix())}/[^/]+\.md$",
        rf"^{re.escape(candidates_rel.as_posix())}$",
    )


def prompt_values(rel_component: Path, rel_candidates: Path, tree: Path,
                  pr_number: str | None, context: str = "") -> dict[str, str]:
    """Every placeholder the prompt takes, assembled ONCE for both callers.

    THE DRY RUN AND THE REAL RUN MUST RENDER THE SAME PROMPT, and this exists so
    they cannot drift. The runner's `--dry-run` branch hand-assembled its own
    copy of this dict, which is the exact shape of a bug this family has already
    shipped and fixed once: `plan_sprint`'s `correction_note` docstring records a
    dry run previewing a DIFFERENT prompt from the one dispatched, because the
    values were built twice. A preview that is not the artifact is worse than no
    preview — it is an operator checking the wrong thing and concluding.

    `tree` IS THE TREE THE COUNTS ARE TAKEN FROM: the worktree on the live path,
    the repo on the dry-run path, where no worktree exists yet. Same reason
    `evidence_block`'s parameter carries that name.
    """
    component = tree / rel_component
    return {
        "COMPONENT_PATH": rel_component.as_posix(),
        "COMPONENT_NAME": rel_component.name,
        "CANDIDATES_PATH": rel_candidates.as_posix(),
        "PLANNING_STATE": own.planning_state(component, tree),
        "RESEARCH_INVENTORY": own.research_inventory(component, tree),
        # The tree-wide pointer, alongside the component-scoped one above. It
        # teaches the pool convention and names the thesis; `RESEARCH_INVENTORY`
        # says which pool is THIS run's, which the shared block cannot know.
        "EVIDENCE_BLOCK": act.evidence_block(tree),
        "SUBMIT_PROMPT": act.submit_prompt(
            pr_number, f"plan-feature: plan {rel_component.name}"),
        # OPAQUE, and rendered verbatim. Before this existed `--pr` could push to
        # a branch and could not be TOLD why it was re-running, so this child had
        # no correction path at all: `plan_project`'s loop-back goes to
        # `plan-sprint`, which cannot edit a roadmap or a phase doc. A producer
        # nothing can instruct is a producer whose only repair is a full re-plan.
        "TASK_CONTEXT": (
            "## OPERATOR CONTEXT FOR THIS RUN\n\n"
            "**This is authoritative and overrides your own reading where they "
            "disagree** — it is the operator speaking, not another run's account. "
            "Verify any FACT it asserts about the tree before building on it, the "
            "same as any other claim.\n\n" + context
            if context.strip() else ""
        ),
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
        "HEADLESS_EXECUTION_GUARD": act.shared_prompt("headless_execution_guard"),
    }


# --- EVERY `You MAY NOT` ROW, AND WHAT OBSERVES IT ---------------------------
#
# See `triage_candidates_workflow.MAY_NOT_OBSERVERS` for why this map exists and
# why it is keyed by the row's exact text — CITED rather than restated, which is
# the convention `plan_sprint_workflow` already follows, so a correction to the
# argument lands in one place instead of drifting across three copies.
# `test_authorization_is_observed.py` compares these keys against the rendered
# table, over a DISCOVERED set of workflows, and `JUDGEMENT` is a legitimate
# answer that must say why the property has no artifact.
#
# WHAT IS NEW HERE RATHER THAN INHERITED: three of this workflow's prohibitions
# are properties of FILENAMES and one is a property of PROSE, so several entries
# below name a reader in `plan_feature_activities` rather than a comparator the
# family shares. Every one of those readers is scoped by `own.plan_docs` — the
# write grant's own set — because a guard narrower than the grant leaves a file
# the run may write and nothing inspects, which is this map's failure mode
# arriving one layer down.
MAY_NOT_OBSERVERS: dict[str, str] = {
    "**Estimate hours, or size the work in any unit of time** — that is `plan-verify`'s":
        "own.hour_hits counted either side of the run over own.plan_docs, so what "
        "is judged is the estimates THIS RUN wrote and not the ones it inherited; "
        "keyed on estimate SHAPE (`~30 hrs`, `(8h)`, `Est: 8 hours`) and never on "
        "the word `hours` — this repo's planning docs hold three prose uses of it "
        "and zero estimates, so a word-keyed pattern would fail correct runs. "
        "own.hour_estimates then cites the delta by file and line",
    "**Rename, renumber or delete an existing phase doc** — the number is IDENTITY":
        "own.phase_docs snapshotted either side of the run, compared by "
        "act.ids_deleted — a rename and a renumber are both a filename that "
        "vanished, which is what makes one comparator answer both",
    "Give a NEW phase doc a name outside `phaseN_<name>.md`":
        "own.malformed_phase_docs over both own.plan_docs snapshots, judging "
        "only names this run added — the Documentation Standard's own "
        "recommended CI lint, applied at authoring time, and scoped to the WRITE "
        "GRANT rather than to names beginning `phase`, so that dropping the "
        "number entirely (`the_run_bag.md`) is caught and not only the tidy "
        "near-misses",
    "Give a NEW phase a number already used in this component":
        "own.reused_phase_numbers over both snapshots — a gap is not a free "
        "number, because references to a retired phase survive elsewhere — and "
        "over the new files AGAINST EACH OTHER by own.phase_identity, so two "
        "docs written in the same dispatch cannot both be phase 5 while "
        "`phase5a_` + `phase5b_` planned together stays legal",
    "**WRITE or edit `sprint.md`** — read it, never touch it":
        "FORBIDDEN_PATHS, via act.worktree_state / act.boundary_crossings — which "
        "compares CONTENT either side of the run, so it observes every write and "
        "is blind to a read BY CONSTRUCTION. That is the right instrument for the "
        "reworded rule: the run is now told to READ the sprint (Stage 1 item 9) "
        "because it must name the entry this component needs, and a proposal into "
        "a sequence nobody has seen is a guess. Reading leaves no artifact, so "
        "nothing here needs to permit it and nothing can mistake it for a write.",
    "Write or edit anything under ANOTHER component, or under your own `research/`":
        "FORBIDDEN_PATHS `^docs/development/` less permitted_paths, whose first "
        "grant is `<component>/[^/]+\\.md$` and so reaches no subdirectory",
    "**Tick a completion checkbox** — you have built nothing":
        "own.plan_boxes — act.checked_boxes over every top-level doc the grant "
        "permits — counted either side of the run and compared in BOTH "
        "directions",
    "Set `decision`, `status`, or another filer's `component` in the candidates file":
        "act.candidate_decisions, act.candidate_statuses and "
        "act.candidate_components snapshotted either side of the run, compared by "
        "act.statuses_this_run_had_no_right_to and "
        "act.components_this_run_had_no_right_to",
    "Edit `problem-statement.md`, `architectural_standard.md`, or anything else under `docs/standards/`":
        "FORBIDDEN_PATHS `^docs/standards/` less permitted_paths, same mechanism",
    "**Delete anything** — a candidate row, a phase doc, or a planning file":
        "act.ids_deleted over the candidate id snapshots and over the phase-doc "
        "snapshots, and act.grants_that_vanished over permitted_paths for the "
        "files themselves",
    "Decide WHEN this component gets built, or where it sits against other work":
        "JUDGEMENT — sequencing leaves no artifact distinct from the report this "
        "workflow is required to write. Its report MUST name the sprint entry the "
        "component needs, so the observable that would separate proposing a "
        "sequence from reporting one is the prose itself. The FILE that would "
        "carry a sequencing decision is `sprint.md`, and that one is observed.",
}

# --- EVERY BEFORE/AFTER SNAPSHOT, AND WHAT WATCHES IT FOR ABSENCE ------------
#
# See `triage_candidates_workflow.DISAPPEARANCE_OBSERVERS` for the class and why
# it is keyed by the SNAPSHOT rather than by the prohibition — cited, not
# restated, matching `plan_sprint_workflow`. `test_disappearance_is_observed.py`
# discovers every `before*` local by AST, so a snapshot added later has no entry
# and fails the suite until somebody answers "what watches this one for absence?"
DISAPPEARANCE_OBSERVERS: dict[str, str] = {
    "before_phase": (
        "act.ids_deleted against the after-snapshot of the same map — and here "
        "deletion is not a corner case but the PRIMARY guard: renaming, "
        "renumbering and deleting a phase doc are one observable, because all "
        "three are a filename that was there before this run and is not there "
        "after it."),
    "before_decision": (
        "act.ids_deleted against the after-snapshot of the same column, checked "
        "BEFORE the column comparisons because a vanished row is in neither "
        "intersection those judge"),
    "before_status": (
        "act.ids_deleted on the SAME id set, already run against before_decision "
        "— act.candidate_decisions, act.candidate_statuses and "
        "act.candidate_components are all built from act.candidate_rows, so a row "
        "cannot be absent from one map and present in another. Registered rather "
        "than left implicit because that coupling is the whole reason a second "
        "deletion check here would be dead code, and the coupling itself is held "
        "by test_the_two_candidate_READERS_ALWAYS_KEY_THE_SAME_ROWS."),
    "before_component": (
        "act.ids_deleted on the SAME id set, by the same coupling registered "
        "against before_status — one parse, one id set, three columns"),
    "before_plan": (
        "act.grants_that_vanished over permitted_paths, which covers this "
        "snapshot EXACTLY rather than approximately: own.plan_docs enumerates "
        "every top-level markdown file in the component and the first grant is "
        "`<component>/[^/]+\\.md$`, so the two sets are equal by construction. "
        "That equality is the point of the reader — a guard scoped more narrowly "
        "than the grant leaves a file the run may write and nothing watches."),
    "before_hours": (
        "own.hour_hits over the same own.plan_docs set, and the SUBTRACTION is "
        "the observation: `after - before` reports only what this run added, so "
        "an estimate that DISAPPEARED is deliberately not an offence. Removing an "
        "hour figure moves the plan toward the state this workflow is required to "
        "leave it in, and the run cannot reach any file outside the grant to "
        "remove one from — which is what makes the asymmetry with before_boxes "
        "correct rather than an oversight, since an erased CHECKBOX destroys a "
        "record of work done and an erased ESTIMATE destroys nothing."),
    "before_boxes": (
        "own.plan_boxes, over the same own.plan_docs set, counted either side of "
        "the run and compared in BOTH directions — so an ERASED tick is an "
        "offence exactly as an added one is. A plan reporting work nobody built "
        "is bad; a plan that has forgotten work somebody did is worse, because "
        "nothing downstream will ask for it again."),
    "before_tree": (
        "act.grants_that_vanished over permitted_paths for the files this run may "
        "write; act.boundary_crossings for every other path, where a deletion "
        "already reads as a content change via the ABSENT sentinel"),
}


def run_plan_feature(*, repo_root: Path, worktree: Path, component: Path,
                     candidates_path: Path, pr_number: str | None = None,
                     context: str = "", verbose: bool = False) -> str:
    """Plan ONE component: its roadmap and its phase docs. Returns the PR URL."""
    # Paths arrive rooted at the REPO because that is where they are configured,
    # but the run reads and writes inside the WORKTREE. Resolve once, count what
    # the model will actually see, and later re-count what it actually wrote.
    rel_component = component.relative_to(repo_root)
    rel_candidates = candidates_path.relative_to(repo_root)
    wt_component = worktree / rel_component
    wt_candidates = worktree / rel_candidates
    permitted = permitted_paths(rel_component, rel_candidates)

    # SNAPSHOTTED AROUND THE MODEL, never diffed against `origin/main`: this
    # workflow can be re-dispatched onto a branch that already carries work, and
    # a diff against the base would attribute somebody else's edit to this run.
    before_phase = own.phase_docs(wt_component)
    before_plan = own.plan_docs(wt_component)
    before_decision = act.candidate_decisions(wt_candidates)
    before_status = act.candidate_statuses(wt_candidates)
    before_component = act.candidate_components(wt_candidates)
    before_boxes = own.plan_boxes(wt_component)
    before_hours = own.hour_hits(wt_component)
    before_tree = act.worktree_state(worktree)

    values = prompt_values(rel_component, rel_candidates, worktree, pr_number,
                           context)

    output = act.run_claude(
        act.render(act.load_prompt(PROMPTS / "plan_feature.md"), values,
                   opaque=frozenset({"TASK_CONTEXT"})),
        model_key=MODEL_KEY, workflow_key=WORKFLOW_KEY,
        completion_pattern=COMPLETION_PATTERN,
        repo_root=repo_root, worktree=worktree,
        max_turns=MAX_TURNS, verbose=verbose,
    )

    url = act.extract_pr_url(output)
    if not url:
        raise RuntimeError(
            f"plan-feature produced no PR URL for `{rel_component}`. Its plan is "
            f"UNREVIEWED and unsubmitted — whatever the exit code says, nothing "
            f"downstream may treat this component as planned. Inspect the worktree "
            f"before re-dispatching; the work may be there."
        )

    after_tree = act.worktree_state(worktree)
    after_phase = own.phase_docs(wt_component)
    after_plan = own.plan_docs(wt_component)

    # THE NUMBER IS IDENTITY, so a phase doc that is GONE is the offence, and
    # renaming, renumbering and deleting are all the same observation. Checked
    # before the two name guards below because those judge only names this run
    # ADDED: a renumber is an add and a delete together, and reporting only the
    # added half would say `phase3_x.md` is malformed while staying silent about
    # `phase2_x.md` having ceased to exist.
    #
    # AND CHECKED BEFORE `grants_that_vanished`, WHICH IS A REORDERING AND NOT AN
    # ACCIDENT. The write grant is `<component>/[^/]+\.md$`, so every phase doc is
    # also a granted path: a renumber therefore satisfies BOTH guards, and with
    # the generic one first this specific message — the one that exists for
    # exactly this case and is the only place the identity rule is explained —
    # was unreachable in practice. The operator got "a file you may write ceased
    # to exist" for the one failure the workflow was built to name. Nothing is
    # weakened by the swap: this guard parses no file, so the reason
    # `grants_that_vanished` runs early still holds against every READER below.
    lost = act.ids_deleted(before_phase, after_phase)
    if lost:
        raise RuntimeError(
            f"plan-feature removed {len(lost)} existing phase doc(s): "
            f"{', '.join(lost)}. A phase number NAMES the phase for life, the way "
            f"a ticket number does — it is not the order. If a phase's position in "
            f"the rollout changed, the line moves in `roadmap.md` and the file does "
            f"not move. Renaming to express order costs a cross-reference sweep "
            f"across the corpus to buy a freedom the roadmap already had — "
            f"see {url}"
        )

    # A WRITE GRANT IS NOT A DELETE GRANT, and this is checked before every
    # READER below, because each of those assumes the file it parses is still
    # there. Deleting `candidates.md` outright would otherwise surface as a parse
    # error from the column readers — a true failure naming the wrong cause,
    # which is the shape that gets a guard "fixed" by making the reader tolerant.
    vanished = act.grants_that_vanished(before_tree, after_tree, permitted)
    if vanished:
        raise RuntimeError(
            f"plan-feature made {len(vanished)} file(s) it may WRITE cease to "
            f"exist: {', '.join(vanished)}. The permission covers creating and "
            f"editing them and nothing further. Both grants are load-bearing and "
            f"the message names the paths above rather than guessing which: a "
            f"planning file deleted is a plan somebody wrote and nothing now "
            f"records, and `candidates.md` deleted is the running proposal list "
            f"every workflow in this family appends to — see {url}"
        )

    # THE DELIVERABLE, OBSERVED RATHER THAN ASSERTED. The run reports what it
    # wrote; this reads the tree. A run that plans nothing and reports a plan is
    # the failure worth catching, because the PR looks like a planned component
    # and the next step in the chain proceeds on it.
    if not (wt_component / own.ROADMAP).is_file():
        raise RuntimeError(
            f"plan-feature produced no `{rel_component}/roadmap.md`. That file IS "
            f"the deliverable — it is what a PM or a new reader opens first, and "
            f"every phase doc is reachable only through it — see {url}"
        )
    if not after_phase:
        raise RuntimeError(
            f"plan-feature produced no phase doc in `{rel_component}/`. A roadmap "
            f"with no phases is an overview of nothing: the roadmap says what each "
            f"phase achieves and links to it, and there is nothing to link to — "
            f"see {url}"
        )

    # OVER THE `plan_docs` SNAPSHOTS, i.e. over the write grant's own set, and
    # not over the phase-shaped one. This run writes exactly two kinds of file, so
    # any NEW top-level markdown that is neither `roadmap.md` nor a conformant
    # phase doc is the offence — including `the_run_bag.md`, which drops the
    # number altogether and is the standard's first-named failure mode. Judged on
    # `phase_docs` this guard could only see names that already began with
    # `phase`, so it caught the tidy near-misses and missed the plain one.
    malformed = own.malformed_phase_docs(before_plan, after_plan)
    if malformed:
        raise RuntimeError(
            f"plan-feature wrote {len(malformed)} plan file(s) whose names are not "
            f"valid: {', '.join(malformed)}. This workflow writes exactly two kinds "
            f"of file: one `roadmap.md`, and one `phaseN_<snake_case>.md` per phase "
            f"— no unnumbered `phase_<name>.md`, no bare `<name>.md`, no "
            f"parenthetical disambiguation, no version suffix. An unnumbered phase "
            f"doc has no identity, so nothing can cite it stably — see {url}"
        )

    reused = own.reused_phase_numbers(before_phase, after_phase)
    if reused:
        raise RuntimeError(
            f"plan-feature reused {len(reused)} phase number(s) already taken in "
            f"`{rel_component}/`: "
            + ", ".join(f"{name} (phase {num})" for name, num in reused)
            + f". A new phase takes `max(existing) + 1`, and a GAP IS NOT A FREE "
            f"NUMBER: a retired phase's number stays retired because commit "
            f"messages, code comments and the sprint plan may still point at it, "
            f"and reusing it makes those references silently ambiguous. This "
            f"covers two docs you wrote in THIS run colliding with each other, "
            f"not only with one that was already there — `phase5a_` and "
            f"`phase5b_` planned together are one phase in two chunks and are "
            f"fine; two bare `phase5_` files are two phases with one name — "
            f"see {url}"
        )

    # A DELTA, LIKE EVERY OTHER PROHIBITION HERE, and it was the one guard keyed
    # on post-run STATE instead. A component that already carried an estimate —
    # one `plan-revision` wrote, or a human did — failed this on every future
    # dispatch, permanently and with a message that named this run as the author.
    # `docs/development/reviews/` carries two such strings today.
    new_hours = own.hour_hits(wt_component) - before_hours
    hours = own.hour_estimates(wt_component, worktree, only=new_hours)
    if hours:
        raise RuntimeError(
            f"plan-feature wrote {len(hours)} hour estimate(s) into the plan:\n  "
            + "\n  ".join(hours)
            + f"\nSizing is NOT this workflow's, and that is a design decision "
            f"rather than a division of labour: an author sizing their own "
            f"decomposition is defending it, and a fresh reader sizing it is a "
            f"second opinion. Say what each phase DELIVERS and let the reviewer "
            f"say what it costs — see {url}"
        )

    # A CHECKBOX MEANS *SHIPPED AND VALIDATED*, and this run has validated
    # nothing — it is writing the plan for work nobody has started. Compared in
    # BOTH directions: erasing a tick is the same prohibition, and it is the
    # worse half, because nothing downstream asks again for work the plan has
    # forgotten somebody did.
    after_boxes = own.plan_boxes(wt_component)
    ticked = after_boxes - before_boxes
    erased = before_boxes - after_boxes
    if ticked or erased:
        raise RuntimeError(
            f"plan-feature changed {sum((ticked + erased).values())} completion "
            f"checkbox(es) in `{rel_component}/`: "
            + "; ".join(
                [f"TICKED {text!r}" for text in sorted(ticked)]
                + [f"ERASED {text!r}" for text in sorted(erased)])
            + f". Every box this workflow writes is UNCHECKED. *Built is not "
            f"proven* — a box marks work demonstrated, and this run has "
            f"demonstrated nothing — see {url}"
        )

    # THE THREE CANDIDATE COLUMNS, none of which is this workflow's. The grant on
    # that file is to APPEND a proposal — a new row, blank `decision`, `status:
    # open`, and the `component` cell named on THAT row and no other.
    #
    # DELETION FIRST, for the reason stated in the registry: both comparators
    # below judge only ids present on BOTH sides, so a row that is simply gone is
    # invisible to them.
    after_decision = act.candidate_decisions(wt_candidates)
    gone = act.ids_deleted(before_decision, after_decision)
    if gone:
        raise RuntimeError(
            f"plan-feature deleted {len(gone)} candidate row(s): {', '.join(gone)}. "
            f"No workflow deletes a row — a candidate ruled `reject` stays in the "
            f"file precisely so the next research cycle does not re-propose it, and "
            f"a row that merely disappears is indistinguishable from one that was "
            f"never proposed — see {url}"
        )

    ruled = act.statuses_this_run_had_no_right_to(before_decision, after_decision)
    if ruled:
        raise RuntimeError(
            f"plan-feature changed the `decision` column on {len(ruled)} "
            f"candidate(s): "
            + ", ".join(f"{cid} {before_decision[cid]!r}->{after_decision[cid]!r}"
                        for cid in ruled)
            + f". That column is `triage-candidates`' alone. A proposal you append "
            f"leaves `decision` BLANK, because blank means untriaged and untriaged "
            f"is the truth — planning a component does not rule the candidates that "
            f"come out of it — see {url}"
        )

    after_status = act.candidate_statuses(wt_candidates)
    flipped = act.statuses_this_run_had_no_right_to(before_status, after_status)
    if flipped:
        raise RuntimeError(
            f"plan-feature changed the `status` column on {len(flipped)} "
            f"candidate(s): "
            + ", ".join(f"{cid} {before_status[cid]!r}->{after_status[cid]!r}"
                        for cid in flipped)
            + f". Planning work is not doing it. `status` belongs to the build that "
            f"completes the item, and writing a phase doc for something is the "
            f"clearest possible case of having not built it — see {url}"
        )

    after_component = act.candidate_components(wt_candidates)
    named = act.components_this_run_had_no_right_to(before_component, after_component)
    if named:
        raise RuntimeError(
            f"plan-feature set or changed the `component` column on {len(named)} "
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

    # THE WHOLE DECLARED BOUNDARY, OBSERVED. One component's top-level markdown
    # and the candidates file; everything else under `docs/development/` and
    # `docs/standards/` is somebody else's, and `sprint.md` is the operator's.
    crossed = act.boundary_crossings(before_tree, after_tree,
                                     FORBIDDEN_PATHS, permitted)
    if crossed:
        raise RuntimeError(
            f"plan-feature edited {len(crossed)} file(s) outside its "
            f"authorization: {', '.join(crossed)}. This workflow plans ONE "
            f"component. Its own `research/` is evidence and is read-only — a plan "
            f"that edits the evidence it is planning from has made the evidence "
            f"agree with the plan. A sibling component that looks like it needs "
            f"work is something to REPORT, and a sprint entry is the operator's — "
            f"see {url}"
        )
    return url

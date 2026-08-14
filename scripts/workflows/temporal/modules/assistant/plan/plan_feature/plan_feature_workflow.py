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

**This is the WRITE half of that split.** `plan-verify` is the fresh-context
reviewer, and it DOES NOT EXIST YET — it is named here as the handoff this
workflow's report is addressed to, and nothing in this tree calls it. Do not read
any reference to it as a dependency.

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

from collections import Counter
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
    r"(^|/)sprints?\.md$",      # "Touch `sprint.md` at all" — also caught above,
                                #   stated separately because the prohibition is
                                #   about the FILE and outlives this directory
    r"^docs/standards/",        # "...or anything else under `docs/standards/`"
)


def permitted_paths(component_rel: Path) -> tuple[str, ...]:
    """The two grants this run holds, one of them computed from its own component.

    A FUNCTION AND NOT A CONSTANT, because half of this boundary is an argument.
    `triage-candidates` writes two fixed files and can name them at module level;
    this workflow's whole subject is *which component*, so a module-level tuple
    would either grant every component at once — deleting the boundary — or hard-
    code one, which is worse.

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
        rf"^{component_rel.as_posix()}/[^/]+\.md$",
        r"^docs/standards/architecture/research/candidates\.md$",
    )


# --- EVERY `You MAY NOT` ROW, AND WHAT OBSERVES IT ---------------------------
#
# THE CLASS THIS SITS INSIDE. A prohibition a model is told is checked, and which
# nothing checks, is worse than an unstated one: it buys compliance on the
# strength of a claim that is false. Keyed by the row's exact text so that
# REWORDING a row breaks this map — the question "what observes this?" has to be
# answered again whenever the prohibition changes, and a new row has no answer at
# all until somebody writes one. `test_authorization_is_observed.py` compares
# these keys against the rendered table, over a DISCOVERED set of workflows.
#
# `JUDGEMENT` is a legitimate answer and must say WHY the property has no
# artifact. It is not a waiver — it is the difference between "nothing checks
# this" being a decision and being an oversight.
MAY_NOT_OBSERVERS: dict[str, str] = {
    "**Estimate hours, or size the work in any unit of time** — that is `plan-verify`'s":
        "own.hour_estimates over the roadmap and every phase doc after the run, "
        "keyed on estimate SHAPE (`~30 hrs`, `(8h)`, `Est: 8 hours`) and never on "
        "the word `hours` — this repo's planning docs hold three prose uses of it "
        "and zero estimates, so a word-keyed pattern would fail correct runs",
    "**Rename, renumber or delete an existing phase doc** — the number is IDENTITY":
        "own.phase_docs snapshotted either side of the run, compared by "
        "act.ids_deleted — a rename and a renumber are both a filename that "
        "vanished, which is what makes one comparator answer both",
    "Give a NEW phase doc a name outside `phaseN_<name>.md`":
        "own.malformed_phase_docs over both snapshots, judging only names this "
        "run added — the Documentation Standard's own recommended CI lint, "
        "applied at authoring time",
    "Give a NEW phase a number already used in this component":
        "own.reused_phase_numbers over both snapshots — a gap is not a free "
        "number, because references to a retired phase survive elsewhere",
    "**Touch `sprint.md` at all** — you hold no authorization over it":
        "FORBIDDEN_PATHS, via act.worktree_state / act.boundary_crossings",
    "Write or edit anything under ANOTHER component, or under your own `research/`":
        "FORBIDDEN_PATHS `^docs/development/` less permitted_paths, whose first "
        "grant is `<component>/[^/]+\\.md$` and so reaches no subdirectory",
    "**Tick a completion checkbox** — you have built nothing":
        "act.checked_boxes counted over the roadmap and every phase doc either "
        "side of the run and compared in BOTH directions",
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
# THE SECOND CLASS, AND IT IS NOT THE ONE ABOVE. Every comparator this family
# owns reports ADDITION and MUTATION; none of them reports DISAPPEARANCE.
# `statuses_this_run_had_no_right_to` judges `before.keys() & after.keys()`, so a
# deleted id is in neither intersection; `boundary_crossings` exempts a permitted
# path unconditionally, so the files an override exists FOR are the ones whose
# removal is invisible; `Counter` subtraction discards removals outright.
#
# Keyed by the SNAPSHOT rather than by the prohibition, because that is what the
# blindness is a property of. `test_disappearance_is_observed.py` discovers every
# `before*` local by AST, so a snapshot added later has no entry and fails the
# suite until somebody answers "what watches this one for absence?"
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
    "before_boxes": (
        "act.checked_boxes, via _plan_boxes, counted either side of the run and "
        "compared in BOTH directions — so an ERASED tick is an offence exactly as "
        "an added one is. A plan reporting work nobody built is bad; a plan that "
        "has forgotten work somebody did is worse, because nothing downstream "
        "will ask for it again."),
    "before_tree": (
        "act.grants_that_vanished over permitted_paths for the files this run may "
        "write; act.boundary_crossings for every other path, where a deletion "
        "already reads as a content change via the ABSENT sentinel"),
}


def run_plan_feature(*, repo_root: Path, worktree: Path, component: Path,
                     candidates_path: Path, pr_number: str | None = None,
                     verbose: bool = False) -> str:
    """Plan ONE component: its roadmap and its phase docs. Returns the PR URL."""
    # Paths arrive rooted at the REPO because that is where they are configured,
    # but the run reads and writes inside the WORKTREE. Resolve once, count what
    # the model will actually see, and later re-count what it actually wrote.
    rel_component = component.relative_to(repo_root)
    rel_candidates = candidates_path.relative_to(repo_root)
    wt_component = worktree / rel_component
    wt_candidates = worktree / rel_candidates
    permitted = permitted_paths(rel_component)

    # SNAPSHOTTED AROUND THE MODEL, never diffed against `origin/main`: this
    # workflow can be re-dispatched onto a branch that already carries work, and
    # a diff against the base would attribute somebody else's edit to this run.
    before_phase = own.phase_docs(wt_component)
    before_decision = act.candidate_decisions(wt_candidates)
    before_status = act.candidate_statuses(wt_candidates)
    before_component = act.candidate_components(wt_candidates)
    before_boxes = _plan_boxes(wt_component)
    before_tree = act.worktree_state(worktree)

    values = {
        "COMPONENT_PATH": str(rel_component),
        "COMPONENT_NAME": rel_component.name,
        "CANDIDATES_PATH": str(rel_candidates),
        "PLANNING_STATE": own.planning_state(wt_component, worktree),
        "RESEARCH_INVENTORY": own.research_inventory(wt_component, worktree),
        # The tree-wide pointer, alongside the component-scoped one above. It
        # teaches the pool convention and names the thesis; `RESEARCH_INVENTORY`
        # says which pool is THIS run's, which the shared block cannot know.
        "EVIDENCE_BLOCK": act.evidence_block(worktree),
        "SUBMIT_PROMPT": act.submit_prompt(
            pr_number, f"plan-feature: plan {rel_component.name}"),
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
        "HEADLESS_EXECUTION_GUARD": act.shared_prompt("headless_execution_guard"),
    }

    output = act.run_claude(
        act.render(act.load_prompt(PROMPTS / "plan_feature.md"), values),
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

    # A WRITE GRANT IS NOT A DELETE GRANT, and this is checked FIRST because every
    # reader below assumes the files it parses are still there. Deleting
    # `candidates.md` outright would otherwise surface as a parse error from the
    # column readers — a true failure naming the wrong cause, which is the shape
    # that gets a guard "fixed" by making the reader tolerant.
    after_tree = act.worktree_state(worktree)
    vanished = act.grants_that_vanished(before_tree, after_tree, permitted)
    if vanished:
        raise RuntimeError(
            f"plan-feature made {len(vanished)} file(s) it may WRITE cease to "
            f"exist: {', '.join(vanished)}. The permission covers creating and "
            f"editing them and nothing further — `candidates.md` is the running "
            f"proposal list this run appends to, and a planning file it deleted is "
            f"a plan somebody wrote and nothing now records — see {url}"
        )

    # THE DELIVERABLE, OBSERVED RATHER THAN ASSERTED. The run reports what it
    # wrote; this reads the tree. A run that plans nothing and reports a plan is
    # the failure worth catching, because the PR looks like a planned component
    # and the next step in the chain proceeds on it.
    after_phase = own.phase_docs(wt_component)
    if not (wt_component / "roadmap.md").is_file():
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

    # THE NUMBER IS IDENTITY, so a phase doc that is GONE is the offence, and
    # renaming, renumbering and deleting are all the same observation. Checked
    # before the two name guards below because those judge only names this run
    # ADDED: a renumber is an add and a delete together, and reporting only the
    # added half would say `phase3_x.md` is malformed while staying silent about
    # `phase2_x.md` having ceased to exist.
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

    malformed = own.malformed_phase_docs(before_phase, after_phase)
    if malformed:
        raise RuntimeError(
            f"plan-feature wrote {len(malformed)} phase doc(s) whose names are not "
            f"valid: {', '.join(malformed)}. The binding form is "
            f"`phaseN_<snake_case>.md` — no unnumbered `phase_<name>.md`, no "
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
            f"and reusing it makes those references silently ambiguous — see {url}"
        )

    hours = own.hour_estimates(wt_component, worktree)
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
    after_boxes = _plan_boxes(wt_component)
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


def _plan_boxes(component: Path) -> Counter:
    """Every completion checkbox in the component's PLAN, as one Counter.

    THE ROADMAP AND THE PHASE DOCS TOGETHER, because the prohibition is about the
    plan and not about a file. `act.checked_boxes` reads one path; this workflow's
    output is one roadmap plus N phase docs, and a guard scoped to `roadmap.md`
    alone would be blind to a phase doc shipping with its steps pre-ticked —
    which is the likelier mistake, since a phase doc is where the implementation
    checklist lives.

    `research/` is deliberately outside the sweep, for the same reason it is
    outside the write grant: a synthesis' own checkboxes are not this plan's.
    """
    boxes: Counter = Counter()
    if not component.is_dir():
        return boxes
    for path in sorted(component.iterdir()):
        if path.is_file() and (path.name == "roadmap.md"
                               or path.name.lower().startswith("phase")):
            boxes += act.checked_boxes(path)
    return boxes

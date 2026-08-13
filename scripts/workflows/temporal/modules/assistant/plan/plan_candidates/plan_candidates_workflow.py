"""plan-candidates — give a ruled candidate somewhere to be built. Nothing else.

WHAT THIS IS FOR. `triage-candidates` decides that something should be built. A
`ship` row is a DECISION, not a place — and the two children after it both need a
place before they can run at all: `research-write` needs a destination pool and a
brief, and `plan-feature` needs a component to plan phases into. This workflow is
the step between the ruling and the work.

THE BOUNDARY THAT DEFINES IT, AND IT IS STRUCTURE VERSUS SUBSTANCE. `plan-feature`
owns roadmap and phase CONTENT — the epics, the milestones, the hour estimates.
This workflow owns the component's CHARTER: what the domain is, what it
explicitly is not, which `C-NNN` rows it derives from, which differentiator it
serves, and what it depends on. A run that writes a phase breakdown has built the
wrong child, and the check for it is `own.phase_planning_in` rather than a
sentence in the prompt.

WHY A CHARTER IS BINDING CONTENT AND NOT A STUB, which is the objection the
[Documentation Standard § 0](../../../../../../docs/standards/documentation/documentation_standard.md)
raises and the reason this workflow does not simply mkdir a folder. That section
is explicit that every planning doc is a new component or a new phase of one,
with no third category and no standalone design doc, and its rule 1 is that *"a
file exists only when it carries binding content."* A charter carries the one
piece of content nothing downstream can supply for itself: the scope boundary
that decides which candidates belong in this component and which do not.
`plan-feature` cannot derive it — it plans phases INSIDE a scope, it does not
choose the scope — and research cannot, because research is commissioned per
component pool and therefore needs the component to already mean something.

THE FILENAME IS AN OPEN QUESTION AND THIS RUN DID NOT SETTLE IT — READ THIS
BEFORE COPYING THE SHAPE. Two documents in this repo disagree about what the
first file of a new component is called, and this workflow picked one without
the disagreement being visible:

  * `docs/guide/workflows.md` and the vendored [Documentation Standard § 0]
    describe the component layer as `<slug>/roadmap.md` + `phase{N}_*.md`, which
    is what this workflow writes;
  * `docs/development/sprint.md` — the OPERATOR'S OWN file, which no dispatch may
    edit — says *"A component is a folder, not a file. `<name>/<name>.md` is its
    phase doc"* and *"A component that outgrows one phase gets its own
    `roadmap.md`… One phase needs no roadmap; do not create one to be tidy."*

Eleven of this repo's sixteen components follow `sprint.md`. A component being
chartered has no phase count yet — that is `plan-feature`'s to determine — so
`roadmap.md` quietly pre-decides *"this will outgrow one phase"*, and
`shells_without_a_charter` below fails any run that writes the `sprint.md` shape
instead. **This is flagged for an operator ruling rather than resolved here:**
resolving it means either amending `sprint.md`, which is human-only, or changing
this workflow's primary artifact against the two documents that specify it.
`component_inventory` marks a component defined by its own `<slug>.md` as
ALREADY DEFINED and tells the run not to charter it, so nothing is duplicated
while the question is open.

THAT GAP IS MEASURED, NOT ARGUED. `docs/development/fleet-reliability/` holds
five verified research papers and a synthesis, and no planning document at all.
The parent's research step created the directory with a `mkdir` because nothing
ahead of it wrote what the component was. Five papers were commissioned into a
component that no document defines.

MOST `ship` ROWS SCAFFOLD NOTHING, and saying so is part of the job rather than a
failure of it. A candidate that extends a component which already exists needs no
new structure — the row plus a named target is enough, and `plan-feature` writes
the phase doc and the roadmap row when it runs. The prompt makes that a
first-class outcome precisely so the run does not invent a domain to have
something to create.

WHY IT IS SEPARATELY DISPATCHABLE. Same reason `triage-candidates` is, and the
same shape: shim, runner, and a workflow function a parent calls. There are 27
rows already ruled `ship` in this repo, so running this child alone against the
real file is both the cheap test and real work; runnable only inside
`plan-project`, every defect in it would be debugged through three other stages
and cost a full planning cycle to see once.
"""

from __future__ import annotations

from pathlib import Path

from ... import routing

from .. import plan_activities as act
from . import plan_candidates_activities as own

_HERE = Path(__file__).resolve().parent
PROMPTS = _HERE / "prompts"

MODEL_KEY = "plan-candidates"

# An ESTIMATE, stated as one — nothing has measured this workflow. The basis and
# the revise-from-measurement note live with the value in config.yaml.
WORKFLOW_KEY = "plan-candidates"   # NOT MODEL_KEY -- see run_claude's docstring
MAX_TURNS = act.max_turns(WORKFLOW_KEY)

COMPLETION_PATTERN = routing.PR_URL_COMPLETION_ERE

# --- THE PATH BOUNDARY, DECLARED WHERE THE PROMPT'S TABLE CAN BE READ AGAINST IT
#
# Every path-scoped `You MAY NOT` row in `prompts/plan_candidates.md`, as a
# pattern. This workflow's boundary is unusual in the family: it is the only one
# that legitimately CREATES a file under `docs/development/`. That is handled by
# EXEMPTING the one file it writes, NOT by narrowing the directory rule — and the
# difference is not cosmetic.
#
# IT WAS WRITTEN THE OTHER WAY FIRST, AND THE NARROW RULE WAS A FALSE
# ENFORCEMENT CLAIM. The pattern was `^docs/development/[^/]+/phase[^/]*\.md$`,
# which matches exactly SIX files in this repo (the `memory-management-framework`
# phase docs) and leaves the rest of the layer open: `cpi-decisions.md`, the
# ELEVEN component docs actually named `<slug>/<slug>.md` — which ARE this
# repo's phase docs, per `sprint.md`'s stated convention — every review artifact,
# and every component's research pool. The prompt told the model that row was
# mechanically checked, and for most of the files it names nothing checked it.
# `triage-candidates`, running one step earlier in the same worktree, forbids
# `^docs/development/` outright; this is that rule, less this workflow's output.
FORBIDDEN_PATHS = (
    r"(^|/)sprints?\.md$",   # "Touch `sprint.md` at all"
    r"^docs/development/",   # "Write or edit any phase doc" — and anything else there
    r"^docs/standards/",     # "...or anything else under `docs/standards/`"
)

# The ONE file under a forbidden root this workflow may write, and it is not one
# it exists for: `decision_log_and_reflection.md` instructs every producing run
# to place a proposal it surfaced into `candidates.md` with `decision` blank, so
# a path rule forbidding the file outright would make an instruction this
# workflow is under unfollowable. Its two columns are guarded separately below,
# so permitting the PATH does not permit a RULING.
#
# `direction.md` is deliberately absent: appending to it is `triage-candidates`'s
# alone, and the mechanism for that prohibition is the absence of an exception.
#
# THE SECOND ENTRY IS THIS WORKFLOW'S ONLY OUTPUT, and it is narrow on purpose. A
# component's `roadmap.md` sits one directory level under the component root and
# nowhere else, so `plan-feature`'s phase docs beside it stay forbidden and a
# `roadmap.md` nested deeper — inside a `research/` pool, say — is not exempt.
#
# A COMPONENT'S `research/` POOL IS DELIBERATELY *NOT* PERMITTED, and the reason
# is a timing fact worth stating because the obvious objection is wrong: the
# parent's research children do write into that pool on this same branch and in
# this same worktree, but they run AFTER this child returns. Both snapshots here
# are taken around THIS workflow's own model call, so a later step's writes are
# outside the window entirely. Permitting the pool would buy nothing and would
# leave this run free to rewrite evidence it did not gather.
PERMITTED_PATHS = (
    r"^docs/standards/architecture/research/candidates\.md$",
    r"^docs/development/[^/]+/roadmap\.md$",
)

# --- EVERY `You MAY NOT` ROW, AND WHAT OBSERVES IT ---------------------------
#
# See `triage_candidates_workflow.MAY_NOT_OBSERVERS` for why this map exists and
# why it is keyed by the row's exact text. `test_authorization_is_observed.py`
# compares these keys against the rendered table, so a new prohibition fails the
# suite until somebody answers "what observes this?" — including by answering
# JUDGEMENT, with a reason.
#
# TWO ROWS HERE HAVE NO ANALOGUE IN EITHER SIBLING, and they are the ones that
# matter: this is the only workflow in the family that creates a file under
# `docs/development/`, so "edit a roadmap that already exists" and "plan phases
# into the roadmap you just created" are boundaries a path rule structurally
# cannot see. Both got a mechanism rather than a JUDGEMENT for that reason.
MAY_NOT_OBSERVERS: dict[str, str] = {
    "**Touch `sprint.md` at all** — you hold no authorization over it":
        "FORBIDDEN_PATHS, via act.worktree_state / act.boundary_crossings",
    "Write or edit any phase doc — `plan-feature` writes those":
        "FORBIDDEN_PATHS `^docs/development/` less the one `roadmap.md` exception "
        "in PERMITTED_PATHS, same mechanism. Stated as the whole directory "
        "because a `phase`-prefixed pattern covered 6 files here and left the 11 "
        "component docs named `<slug>/<slug>.md` — the phase docs this row is "
        "actually about — unwatched",
    "**Edit a `roadmap.md` that already exists** — you create one, you never revise one":
        "own.component_roadmaps read from DISK either side of the run, compared "
        "by own.roadmaps_edited. A path rule cannot see this: `worktree_state` "
        "reports a created roadmap and an edited one identically",
    "Write phases, epics, milestones or hour estimates into anything":
        "own.phase_planning_in over own.roadmaps_created — the created roadmap "
        "is this workflow's own output, so only its CONTENT is observable",
    "Leave a component directory with no `roadmap.md` in it":
        "own.shells_without_a_charter over the component-directory sets either "
        "side of the run, against the after-side roadmap map",
    "Set `decision` on ANY candidate — that is `triage-candidates`'s alone":
        "act.candidate_decisions snapshotted either side of the run, compared by "
        "act.rulings_this_run_had_no_right_to",
    "Set `status` in the candidates file — that is a later process's":
        "act.candidate_statuses snapshotted either side of the run, compared by "
        "act.statuses_this_run_had_no_right_to",
    "Append to or edit `direction.md`":
        "FORBIDDEN_PATHS `^docs/standards/`, and deliberately NOT in "
        "PERMITTED_PATHS — the mechanism is the absence of an exception",
    "Edit `problem-statement.md`, `architectural_standard.md`, or anything else under `docs/standards/`":
        "FORBIDDEN_PATHS `^docs/standards/` less PERMITTED_PATHS, same mechanism",
    "Decide WHICH sprint or phase a component belongs in":
        "JUDGEMENT — a placement and an observation about a placement are the "
        "same prose in the same report, and the charter this run writes is "
        "REQUIRED to say what the component depends on. The observable that "
        "would separate the two is the sprint plan, which this workflow cannot "
        "reach at all, so what is left is a reviewer reading the report.",
    "**Delete anything** — a candidate row, a roadmap, or any file":
        "act.ids_deleted over both the candidate-row and the roadmap snapshots; "
        "act.grants_that_vanished over PERMITTED_PATHS for the two files this "
        "workflow may write; and act.boundary_crossings for everything else "
        "under a forbidden root, where a deletion reads as a content change via "
        "the ABSENT sentinel. The third clause is what covers a research pool or "
        "a component doc — the first two are blind to both",
}

# --- EVERY BEFORE/AFTER SNAPSHOT, AND WHAT WATCHES IT FOR ABSENCE ------------
#
# See `triage_candidates_workflow.DISAPPEARANCE_OBSERVERS` for the class this
# closes and why it is keyed by the snapshot rather than by the prohibition:
# every comparator in this family reports ADDITION and MUTATION and is blind to
# a key, or a whole file, that is simply GONE.
DISAPPEARANCE_OBSERVERS: dict[str, str] = {
    "before_decisions":
        "act.ids_deleted, called inside act.rulings_this_run_had_no_right_to",
    "before_status":
        "act.ids_deleted on the SAME id set, via "
        "act.rulings_this_run_had_no_right_to on `before_decisions` — "
        "act.candidate_statuses and act.candidate_decisions are both built from "
        "act.candidate_rows, so a row cannot be absent from one map and present "
        "in the other",
    "before_roadmaps":
        "act.ids_deleted against the after-snapshot of the same map, checked "
        "BEFORE own.roadmaps_edited because that comparison judges only keys "
        "present on both sides and a deleted roadmap is in neither",
    "before_dirs":
        "act.boundary_crossings over before_tree/after_tree, where FORBIDDEN_PATHS "
        "covers `^docs/development/` and a deleted file reads as a content change "
        "via the ABSENT sentinel. own.shells_without_a_charter judges only "
        "directories that APPEARED and is blind to a removal by construction. "
        "This entry previously delegated to act.ids_deleted over before_roadmaps "
        "on the argument that `a component with no roadmap to lose is one this "
        "workflow could not have created` — TRUE about creation and irrelevant to "
        "deletion: 15 of this repo's 16 components have no roadmap, so razing any "
        "of them moved no key in that map and nothing saw it. The argument also "
        "could not have run — act.ids_deleted takes two dicts and before_dirs is "
        "a set",
    "before_tree":
        "act.grants_that_vanished over PERMITTED_PATHS for the candidates file; "
        "act.boundary_crossings for every other path, where a deletion already "
        "reads as a content change via the ABSENT sentinel",
}


def run_plan_candidates(*, repo_root: Path, worktree: Path,
                        candidates_path: Path, research_dir: Path,
                        pr_number: str | None = None,
                        verbose: bool = False) -> str:
    """Scaffold what the ruled candidates need and nothing more. Returns the PR URL."""
    # Paths arrive rooted at the REPO because that is where they are configured,
    # but the run reads and writes inside the WORKTREE. Count what the model will
    # actually see, and later re-read what it actually wrote.
    rel_candidates = candidates_path.relative_to(repo_root)
    rel_research = research_dir.relative_to(repo_root)
    wt_candidates = worktree / rel_candidates

    # Counted in code so the report cannot assert a working set it invented.
    before_decisions = act.candidate_decisions(wt_candidates)

    # WHAT THIS RUN MUST NOT MOVE, snapshotted before it can move it. Both
    # candidate columns belong to somebody else, an existing roadmap is
    # `plan-feature`'s, and the paths outside its authorization are not its to
    # reach at all.
    #
    # Snapshotted AROUND THE MODEL, never diffed against `origin/main`: this
    # workflow runs SECOND on a branch `triage-candidates` has already written
    # to, so a diff against the base would report triage's legitimate
    # `direction.md` row as this run's forbidden edit.
    before_status = act.candidate_statuses(wt_candidates)
    before_roadmaps = own.component_roadmaps(worktree)
    before_dirs = own.component_dirs(worktree)
    before_tree = act.worktree_state(worktree)

    values = {
        "CANDIDATES_PATH": str(rel_candidates),
        "RESEARCH_DIR": str(rel_research),
        "WORKING_SET": own.shipped_working_set(before_decisions),
        "COMPONENT_INVENTORY": own.component_inventory(worktree),
        # THE WORKTREE, not the repo. Every read in this dict is
        # worktree-anchored: this workflow runs on a branch a child ahead of it
        # has already written to, and an enumeration anchored at the repo would
        # describe a tree the model cannot see.
        "EXISTING_WORK": act.existing_work(worktree, worktree / rel_research),
        "SUBMIT_PROMPT": act.submit_prompt(pr_number, "plan-candidates: scaffold what the ruled candidates need"),
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
        "HEADLESS_EXECUTION_GUARD": act.shared_prompt("headless_execution_guard"),
    }

    output = act.run_claude(
        act.render(act.load_prompt(PROMPTS / "plan_candidates.md"), values),
        model_key=MODEL_KEY, workflow_key=WORKFLOW_KEY,
        completion_pattern=COMPLETION_PATTERN,
        repo_root=repo_root, worktree=worktree,
        max_turns=MAX_TURNS, verbose=verbose,
    )

    url = act.extract_pr_url(output)
    if not url:
        raise RuntimeError(
            "plan-candidates produced no PR URL. Any component it scaffolded is "
            "UNREVIEWED — and the children after it research and plan INTO those "
            "components, so an unreviewed structure is one the rest of the "
            "pipeline builds on."
        )

    # A WRITE GRANT IS NOT A DELETE GRANT, and this is checked FIRST because
    # every reader below assumes the file it parses is still there. Deleting
    # `candidates.md` outright would otherwise surface as a FileNotFoundError
    # from the decision reader — a true failure naming the wrong cause, which is
    # the shape that gets a guard "fixed" by making the reader tolerant.
    after_tree = act.worktree_state(worktree)
    vanished = act.grants_that_vanished(before_tree, after_tree, PERMITTED_PATHS)
    if vanished:
        raise RuntimeError(
            f"plan-candidates made {len(vanished)} file(s) it may WRITE cease to "
            f"exist: {', '.join(vanished)}. The permission covers appending a "
            f"proposal row to `candidates.md` and nothing further — that file is "
            f"the running list every planning workflow reads its working set "
            f"from — see {url}"
        )

    after_roadmaps = own.component_roadmaps(worktree)

    # DELETION BEFORE MUTATION, for the reason `roadmaps_edited` states: it
    # judges only keys present on BOTH sides, so a roadmap that is simply gone is
    # invisible to it. A component's charter is the document the rest of the
    # pipeline reads to know what that component IS; removing one silently
    # unmoors every phase doc and research pool beneath it.
    razed = act.ids_deleted(before_roadmaps, after_roadmaps)
    if razed:
        raise RuntimeError(
            f"plan-candidates deleted {len(razed)} component charter(s): "
            f"{', '.join(razed)}. This workflow CREATES a roadmap and never "
            f"removes one. A component whose charter is gone still has its phase "
            f"docs and its research pool, and nothing left saying what any of it "
            f"is for — see {url}"
        )

    # THE BOUNDARY AGAINST `plan-feature`, HALF ONE: an existing roadmap is not
    # this run's to revise. Its phases, its milestones and its hour estimates are
    # somebody else's output, and its scope is a decision somebody else made.
    revised = own.roadmaps_edited(before_roadmaps, after_roadmaps)
    if revised:
        raise RuntimeError(
            f"plan-candidates edited {len(revised)} roadmap(s) that already "
            f"existed: {', '.join(revised)}. This workflow charters a component "
            f"that has none; revising one is `plan-feature`'s, and rewriting a "
            f"component's scope is a decision that was already made. If an "
            f"existing charter is wrong, SAY SO in the report — see {url}"
        )

    # HALF TWO, AND NO PATH RULE CAN REACH IT. The roadmap this run created is
    # its own output, so nothing outside its content distinguishes a charter from
    # a plan. Phases, epics and hour estimates are `plan-feature`'s whole job.
    created = own.roadmaps_created(before_roadmaps, after_roadmaps)
    planned = own.phase_planning_in(worktree, created)
    if planned:
        detail = "; ".join(f"{rel} [{', '.join(lines)}]" for rel, lines in planned.items())
        raise RuntimeError(
            f"plan-candidates planned phases or estimated hours in "
            f"{len(planned)} roadmap(s) it created: {detail}. A charter says "
            f"what the component IS and what it is NOT; the phase breakdown and "
            f"the hour estimate per phase are `plan-feature`'s output, and it "
            f"runs after this with the research this run's charter commissioned "
            f"— see {url}"
        )

    # THE STANDARD'S RULE 1, ONE LEVEL UP FROM A FILE. A directory that reads as
    # a component and holds nothing anyone can act on is the reserved name the
    # Documentation Standard forbids — and the pipeline has already produced one
    # by mkdir'ing a research pool under a component nothing had chartered.
    shells = own.shells_without_a_charter(before_dirs, own.component_dirs(worktree),
                                          after_roadmaps)
    if shells:
        raise RuntimeError(
            f"plan-candidates created {len(shells)} component director(ies) with "
            f"no `roadmap.md` in them: {', '.join(shells)}. An empty component "
            f"folder is the stub the Documentation Standard § 0 rule 1 forbids — "
            f"it reads as a home and holds nothing the children after this can "
            f"read. Either write the charter or do not create the directory — "
            f"see {url}"
        )

    # OBSERVE, DO NOT ASSERT. `decision` is `triage-candidates`'s output alone.
    # A run that has just decided a candidate needs no component of its own is
    # one plausible step from recording that conclusion in the column beside it.
    after_decisions = act.candidate_decisions(wt_candidates)
    moved = sorted(act.rulings_this_run_had_no_right_to(before_decisions, after_decisions))
    if moved:
        raise RuntimeError(
            f"plan-candidates changed the `decision` column on {len(moved)} "
            f"candidate(s): "
            + ", ".join(f"{cid} {before_decisions.get(cid, '<absent>')!r}->"
                        f"{after_decisions.get(cid, '<absent>')!r}" for cid in moved)
            + f". That column is `triage-candidates`'s alone, and this workflow "
              f"runs directly after it — a ruling revised here is one no triage "
              f"pass agreed to and no reviewer was told to look for — see {url}"
        )

    # THE SAME ARGUMENT, ONE COLUMN OVER. `status` is neither workflow's, and
    # building somewhere for a candidate is conspicuously not finishing it — a
    # run that has just created the component is one step from marking the row
    # handled.
    after_status = act.candidate_statuses(wt_candidates)
    flipped = act.statuses_this_run_had_no_right_to(before_status, after_status)
    if flipped:
        raise RuntimeError(
            f"plan-candidates changed the `status` column on {len(flipped)} "
            f"candidate(s): "
            + ", ".join(f"{cid} {before_status[cid]!r}->{after_status[cid]!r}"
                        for cid in flipped)
            + f". `status` belongs to a later process — `plan-feature`, or the "
              f"build that completes the item. Creating somewhere for work to "
              f"happen is not the work happening — see {url}"
        )

    # THE REST OF THE DECLARED BOUNDARY. This is the only workflow in the family
    # that legitimately creates a file under `docs/development/`, so the phase-doc
    # pattern is narrow by necessity and the edge beside it is observed rather
    # than trusted.
    crossed = act.boundary_crossings(before_tree, after_tree,
                                     FORBIDDEN_PATHS, PERMITTED_PATHS)
    if crossed:
        raise RuntimeError(
            f"plan-candidates edited {len(crossed)} file(s) outside its "
            f"authorization: {', '.join(crossed)}. It charters components; it "
            f"writes no sprint plan, no phase doc, no standard and no "
            f"`direction.md` row. A candidate that looks like it needs a sprint "
            f"section is something to REPORT — `plan-sprint` runs later in this "
            f"pipeline and carries the only override — see {url}"
        )
    return url

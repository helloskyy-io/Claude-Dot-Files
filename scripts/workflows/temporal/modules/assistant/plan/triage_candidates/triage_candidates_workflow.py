"""triage-candidates — rule every untriaged research candidate. Nothing else.

Folder holds only this file (§10.1 rule 6); the family's shared capability lives
in `plan_activities`.

WHY THIS IS ITS OWN WORKFLOW. `plan-sprint` did two jobs in one run — its own
docstring said so, *"triage research candidates and keep the sprint plan
current"* — and NOTHING COULD BE SEQUENCED BETWEEN THEM. Feature planning and
scaffolding belong after triage and before the sprint plan is updated, and while
both jobs sat inside one dispatch that was structurally impossible, not merely
unimplemented.

It also fixed an ordering defect for free: the sprint plan used to be updated
BEFORE anything estimated the work, so its hour totals landed ahead of the
estimates they depend on.

THE AUTHORITY CAME WITH THE JOB, AND IT DID NOT WIDEN. `decision` on a candidate
is this workflow's output alone — transferred from `plan-sprint` explicitly, in
every document that names the writer, when the split landed. `status` is still
NOT ours and never becomes ours: deciding to do something does not do it. On a
`direction.md` row, `status` is the operator's alone.

WHAT IT DELIBERATELY DOES NOT DO. It does not touch `sprint.md` — that is
`plan-sprint`'s, and this workflow holds no sprint-file authorization at all. It
does not open a phase doc. It reads `problem-statement.md` and never writes it:
that document is the thesis everything else derives from, and the judgement in
it is not delegable.

WHY IT IS SEPARATELY DISPATCHABLE. Same reason `plan-sprint` is, and the same
shape: shim, runner, and a workflow function a parent calls. Triage runnable only
inside `plan-project` would cost a full planning cycle to test once, and every
defect in it would be debugged through three other stages.
"""

from __future__ import annotations

from pathlib import Path

from ... import routing

from .. import plan_activities as act
from . import triage_candidates_activities as own

_HERE = Path(__file__).resolve().parent
PROMPTS = _HERE / "prompts"

MODEL_KEY = "triage-candidates"

# An ESTIMATE, stated as one — nothing has measured this workflow. The basis and
# the revise-from-measurement note live with the value in config.yaml.
WORKFLOW_KEY = "triage-candidates"   # NOT MODEL_KEY -- see run_claude's docstring
MAX_TURNS = act.max_turns(WORKFLOW_KEY)

COMPLETION_PATTERN = routing.PR_URL_COMPLETION_ERE

# --- THE PATH BOUNDARY, DECLARED WHERE THE PROMPT'S TABLE CAN BE READ AGAINST IT
#
# Every path-scoped `You MAY NOT` row in `prompts/triage_candidates.md`, as a
# pattern. Not taking a `sprint_path` parameter constrains the SIGNATURE; the run
# holds the whole worktree either way, so the boundary is observed rather than
# assumed. Matched on the NAME for the sprint plan because this workflow is given
# no sprint path and a guard that needed one would reintroduce the parameter the
# boundary is defined by — the cost being that a repo calling its plan something
# else is not covered, which is cheap to widen when a second consumer exists.
FORBIDDEN_PATHS = (
    r"(^|/)sprints?\.md$",      # "Touch `sprint.md` at all"
    r"^docs/development/",      # "Write or edit any phase doc"
    r"^docs/standards/",        # "...or anything else under `docs/standards/`"
)

# The two files this workflow EXISTS to write. Both live under `docs/standards/`,
# so without the exception the forbidden pattern above fails every correct run.
# `direction.md` is the operator's inbox rather than a standard, which is why the
# prompt names it as the one exception to the standards-directory rule.
PERMITTED_PATHS = (
    r"^docs/standards/architecture/research/candidates\.md$",
    r"^docs/standards/architecture/research/direction\.md$",
)

# --- EVERY `You MAY NOT` ROW, AND WHAT OBSERVES IT ---------------------------
#
# THE CLASS THIS CLOSES. The split built a real mechanism for one prohibition and
# left the others on prose — including one the prompt asserted was enforced. A
# prohibition a model is told is checked, and which nothing checks, is worse than
# an unstated one: it buys compliance on the strength of a claim that is false.
#
# Keyed by the row's exact text so that REWORDING a row breaks this map. That is
# the point rather than a cost: the question "what observes this?" has to be
# answered again whenever the prohibition changes, and a new row has no answer at
# all until someone writes one. `test_authorization_is_observed.py` compares
# these keys against the rendered table.
#
# `JUDGEMENT` is a legitimate answer and must say WHY the property has no
# artifact. It is not a waiver — it is the difference between "nothing checks
# this" being a decision and being an oversight.
MAY_NOT_OBSERVERS: dict[str, str] = {
    "Set `status` in the candidates file — that is a later process's":
        "act.candidate_statuses snapshotted either side of the run, compared by "
        "act.statuses_this_run_had_no_right_to",
    "Set `status` on a `direction.md` row — that is the operator's":
        "own.direction_statuses snapshotted either side of the run, through the "
        "same comparator",
    "Set or change `component` on a candidate row that already existed — that is the FILER's":
        "act.candidate_components snapshotted either side of the run, compared by "
        "act.components_this_run_had_no_right_to — which judges only ids present "
        "on both sides, so the appended-row grant in the MAY column is the same "
        "exemption rather than a second rule",
    "**Touch `sprint.md` at all** — you hold no authorization over it":
        "FORBIDDEN_PATHS, via act.worktree_state / act.boundary_crossings",
    "Write or edit any phase doc":
        "FORBIDDEN_PATHS `^docs/development/`, same mechanism",
    "Design *how* anything gets built":
        "JUDGEMENT — design leaves no artifact distinct from the report this "
        "workflow is required to write. Its report MUST say what it noticed "
        "about a shipped candidate, so the observable that would separate "
        "designing from reporting is the prose itself.",
    "Edit `problem-statement.md`, `architectural_standard.md`, or anything else under `docs/standards/`":
        "FORBIDDEN_PATHS `^docs/standards/` less PERMITTED_PATHS, same mechanism",
    "**Delete anything** — a candidate row, a `direction.md` row, or either file":
        "act.ids_deleted over both id snapshots, and act.grants_that_vanished "
        "over PERMITTED_PATHS for the files themselves",
}

# --- EVERY BEFORE/AFTER SNAPSHOT, AND WHAT WATCHES IT FOR ABSENCE ------------
#
# THE SECOND CLASS, AND IT IS NOT THE ONE ABOVE. Every comparator this family
# owns reports ADDITION and MUTATION; none of them reported DISAPPEARANCE.
# `statuses_this_run_had_no_right_to` judges `before.keys() & after.keys()`, so a
# deleted id is in neither intersection; `boundary_crossings` exempts a permitted
# path unconditionally, so the file an override exists FOR is the one file whose
# removal is invisible. Both were demonstrated by execution rather than argued: a
# run deleted an operator-ruled `direction.md` row and returned a PR URL.
#
# Keyed by the SNAPSHOT rather than by the prohibition, because that is what the
# blindness is a property of. `test_disappearance_is_observed.py` discovers every
# `before*` local by AST, so a snapshot added later has no entry and fails the
# suite until somebody answers "what watches this one for absence?"
DISAPPEARANCE_OBSERVERS: dict[str, str] = {
    "before_status":
        "act.ids_deleted against the after-snapshot of the same column",
    "before_component":
        "act.ids_deleted on the SAME id set, already run against before_status — "
        "act.candidate_statuses and act.candidate_components are both built from "
        "act.candidate_rows, so a row cannot be absent from one map and present "
        "in the other. Registered rather than left implicit because that coupling "
        "is the whole reason a second deletion check here would be dead code.",
    "before_direction":
        "act.ids_deleted against the after-snapshot of the same column, checked "
        "BEFORE the status comparison because a vanished row is in neither "
        "intersection that comparison judges",
    "before_tree":
        "act.grants_that_vanished over PERMITTED_PATHS for the two files this "
        "workflow writes; act.boundary_crossings for every other path, where a "
        "deletion already reads as a content change via the ABSENT sentinel",
}


def run_triage_candidates(*, repo_root: Path, worktree: Path,
                          candidates_path: Path, research_dir: Path,
                          pr_number: str | None = None,
                          verbose: bool = False) -> str:
    """Rule every untriaged candidate, hand the open questions up. Returns the PR URL."""
    # Paths arrive rooted at the REPO because that is where they are configured,
    # but the run reads and writes inside the WORKTREE. Count what the model will
    # actually see, and later re-count what it actually wrote.
    rel_candidates = candidates_path.relative_to(repo_root)
    rel_research = research_dir.relative_to(repo_root)
    wt_candidates = worktree / rel_candidates

    # Counted in code so the report cannot assert a total it invented.
    counts = act.candidate_counts(wt_candidates)

    # THE COLUMNS THIS RUN MUST NOT MOVE, and the paths it must not reach.
    # `decision` is ours; `status` is a later process's on a candidate and the
    # OPERATOR'S on a direction row, and neither becomes ours — deciding to do
    # something does not do it.
    #
    # Snapshotted AROUND THE MODEL, never diffed against `origin/main`: this
    # workflow can be re-dispatched onto a branch that already carries work, and
    # a diff against the base would attribute somebody else's edit to this run.
    before_status = act.candidate_statuses(wt_candidates)
    # `component` is nobody's here either — it belongs to whoever FILED the row.
    # It is the one column whose guess does not stay a guess: `plan-candidates`
    # runs in the parent immediately after this child and turns a component name
    # into a committed `docs/development/<name>/` on this same branch.
    before_component = act.candidate_components(wt_candidates)
    before_direction = own.direction_statuses(worktree / rel_research)
    before_tree = act.worktree_state(worktree)

    values = {
        "CANDIDATES_PATH": str(rel_candidates),
        "RESEARCH_DIR": str(rel_research),
        "WORKING_SET": _working_set(counts),
        "DIRECTION_CEILING": own.direction_ceiling(worktree / rel_research),
        # THE WORKTREE, like the line above it. Every other read in this dict is
        # already worktree-anchored; this one was the odd repo-rooted read out,
        # sitting one line from its correct neighbour.
        "EXISTING_WORK": act.existing_work(worktree, worktree / rel_research),
        "SUBMIT_PROMPT": act.submit_prompt(pr_number, "triage-candidates: rule the untriaged candidates"),
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
        "HEADLESS_EXECUTION_GUARD": act.shared_prompt("headless_execution_guard"),
    }

    output = act.run_claude(
        act.render(act.load_prompt(PROMPTS / "triage_candidates.md"), values),
        model_key=MODEL_KEY, workflow_key=WORKFLOW_KEY,
        completion_pattern=COMPLETION_PATTERN,
        repo_root=repo_root, worktree=worktree,
        max_turns=MAX_TURNS, verbose=verbose,
    )

    url = act.extract_pr_url(output)
    if not url:
        raise RuntimeError(
            "triage-candidates produced no PR URL. Its triage is UNREVIEWED — the "
            "candidates file must not be trusted as ruled."
        )

    # A WRITE GRANT IS NOT A DELETE GRANT, and this is checked FIRST because
    # every reader below assumes the file it parses is still there. Deleting
    # `candidates.md` outright would otherwise surface as a FileNotFoundError
    # from the counter — a true failure naming the wrong cause, which is the
    # shape that gets a guard "fixed" by making the reader tolerant.
    after_tree = act.worktree_state(worktree)
    vanished = act.grants_that_vanished(before_tree, after_tree, PERMITTED_PATHS)
    if vanished:
        raise RuntimeError(
            f"triage-candidates made {len(vanished)} file(s) it may WRITE cease "
            f"to exist: {', '.join(vanished)}. The permission covers editing "
            f"them and nothing further. `candidates.md` is the running list this "
            f"workflow reads its working set from, and `direction.md` is the "
            f"operator's inbox — every open question in it is one nobody has "
            f"answered yet — see {url}"
        )

    # OBSERVE, DO NOT ASSERT. The run reports its own triage counts; this reads
    # the file it actually wrote. A partial triage that reports as complete is
    # the failure mode worth catching — the PR looks ruled and is not, and the
    # untriaged rows are invisible until the next cycle re-proposes them.
    #
    # This post-condition MOVED here with the job. It was `plan-sprint`'s while
    # `plan-sprint` triaged; leaving a copy behind would have made a workflow
    # that no longer sets `decision` raise about a column it cannot write.
    after = act.candidate_counts(wt_candidates)
    if after["untriaged"]:
        raise RuntimeError(
            f"triage-candidates left {after['untriaged']} of {counts['untriaged']} candidates "
            f"untriaged: {', '.join(after['untriaged_ids'])}. Every row must reach "
            f"ship / requires review / reject — see {url}"
        )

    after_status = act.candidate_statuses(wt_candidates)

    # A ROW THAT VANISHED PASSES THE POST-CONDITION ABOVE, which counts blank
    # `decision` cells: deleting an untriaged row drops the count exactly as
    # ruling it would, so a run could report a complete triage over a candidate
    # that no longer exists. The file's promise is that a rejected candidate
    # stays visibly rejected instead of being re-proposed by the next cycle, and
    # that promise was carried by one prompt sentence. Checked BEFORE the columns
    # below, because both status guards judge only ids present on both sides and
    # would report nothing about a row that is gone.
    gone = act.ids_deleted(before_status, after_status)
    if gone:
        raise RuntimeError(
            f"triage-candidates deleted {len(gone)} candidate row(s): "
            f"{', '.join(gone)}. No workflow deletes a row — a candidate ruled "
            f"`reject` stays in the file precisely so the next research cycle "
            f"does not re-propose it, and a row that merely disappears is "
            f"indistinguishable from one that was never proposed — see {url}"
        )

    # THE WHOLE DECLARED BOUNDARY, OBSERVED. `sprint.md` is the operator's own
    # sequencing surface, phase docs belong to nothing this workflow runs, and
    # `docs/standards/` is off-limits but for the two research files this
    # workflow exists to write. The prompt hands the model the exact trigger for
    # the first of those — "if a candidate you ship looks like it needs a sprint
    # section, say so" — one step short of writing the section instead.
    crossed = act.boundary_crossings(before_tree, after_tree,
                                     FORBIDDEN_PATHS, PERMITTED_PATHS)
    if crossed:
        raise RuntimeError(
            f"triage-candidates edited {len(crossed)} file(s) outside its "
            f"authorization: {', '.join(crossed)}. This workflow rules candidates "
            f"and files direction rows; it writes no sprint plan, no phase doc and "
            f"no standard. A shipped candidate that looks like it needs a sprint "
            f"section is something to REPORT — `plan-sprint` runs after this and "
            f"carries the only override — see {url}"
        )

    flipped = act.statuses_this_run_had_no_right_to(before_status, after_status)
    if flipped:
        raise RuntimeError(
            f"triage-candidates changed the `status` column on {len(flipped)} "
            f"candidate(s): {', '.join(flipped)}. Ruling a candidate is not doing it. "
            f"`status` belongs to a later process — `plan-feature`, or the build that "
            f"completes the item — and it did not move in the split — see {url}"
        )

    named = act.components_this_run_had_no_right_to(
        before_component, act.candidate_components(wt_candidates))
    if named:
        raise RuntimeError(
            f"triage-candidates set or changed the `component` column on "
            f"{len(named)} pre-existing candidate(s): {', '.join(named)}. That "
            f"column belongs to whoever FILED the row, because only they know "
            f"where the proposal goes — from a one-line summary anything "
            f"downstream is guessing. And the guess does not stay a cell: "
            f"`plan-candidates` runs immediately after this child and turns a "
            f"component name into a committed `docs/development/<name>/` on this "
            f"branch. Naming the component on a row YOU appended is permitted and "
            f"required; naming it on somebody else's is not — see {url}"
        )

    # THE SAME PAIR OF COMPARATORS, ON THE HIGHER-STAKES COLUMN. Read ONCE into
    # a local and used by both: a second inline call would re-parse the file for
    # a value that cannot have changed between them, which is the triple-read
    # this workflow's sibling already had removed.
    after_direction = own.direction_statuses(worktree / rel_research)

    # DELETION FIRST, for the reason the candidates-side check is ordered that
    # way: `statuses_this_run_had_no_right_to` judges only ids present on BOTH
    # sides, so it would report nothing whatever about a row that is gone. A
    # missing `direction.md` on both sides is `{}` vs `{}` and stays legitimate.
    lost = act.ids_deleted(before_direction, after_direction)
    if lost:
        raise RuntimeError(
            f"triage-candidates deleted {len(lost)} `direction.md` row(s): "
            f"{', '.join(lost)}. Nobody but `/standup` rotates a row out. An "
            f"`open` row is a question this workflow filed FOR the operator and "
            f"nobody has answered; a ruled one is the RECEIPT for an answer they "
            f"gave, and `direction.md` § Rotation is explicit that the reasoning "
            f"must be durable elsewhere before the row goes — otherwise the same "
            f"recommendation comes back round next cycle with nothing recording "
            f"that it was already settled — see {url}"
        )

    # `applied` and `rejected` on a direction row are rulings only the operator
    # can make, and once one is recorded `/standup` rotates the row out and the
    # receipt is gone — so a wrongly-set flag is not merely wrong, it is
    # unrecoverable. Only PRE-EXISTING rows are judged, because the prompt
    # REQUIRES a newly appended row to carry `status: open`.
    ruled = act.statuses_this_run_had_no_right_to(before_direction, after_direction)
    if ruled:
        raise RuntimeError(
            f"triage-candidates changed the `status` column on {len(ruled)} "
            f"`direction.md` row(s): {', '.join(ruled)}. That flag is the "
            f"OPERATOR'S ALONE — `applied` and `rejected` are the rulings this "
            f"workflow files a row to ask for, and it may not answer its own "
            f"question. Appending a row with `status: open` is the whole of this "
            f"workflow's part in it — see {url}"
        )
    return url


def _working_set(counts: dict) -> str:
    """The counted working set, and what an EMPTY one means.

    Zero untriaged is not an error and not a no-op: a `--pr` re-dispatch against
    a returned PR finds every row already ruled, and its job is then to close the
    reviewer's runway by REVISING a ruling — not to re-triage a set that has
    none. Said in code because the distinction decides what the run does next,
    and a model reading `0 untriaged` with no further instruction reasonably
    concludes there is nothing to do and stops.
    """
    if not counts["untriaged"]:
        return (
            f"**Counted in code, authoritative — do not recount:** {counts['total']} "
            f"candidates, **0 untriaged**, {counts['triaged']} already ruled.\n\n"
            f"**THERE IS NO FRESH WORKING SET, and that is a state rather than a "
            f"fault.** You are on a re-dispatch against an already-triaged file. Your "
            f"job is to REVISE — close the runway a reviewer wrote, or correct a "
            f"ruling new evidence overturns — and to change nothing else. A ruling "
            f"you merely disagree with is not yours to revisit; re-litigating settled "
            f"dispositions is the failure this sentence exists to prevent. If nothing "
            f"needs revising, say so plainly and change no rows."
        )
    return (
        f"**Counted in code, authoritative — do not recount:** {counts['total']} "
        f"candidates, **{counts['untriaged']} untriaged**, {counts['triaged']} already ruled.\n\n"
        f"The untriaged rows are your ENTIRE working set: "
        f"{', '.join(counts['untriaged_ids'])}. A row that already carries a "
        f"`decision` is settled — leave it alone unless new evidence overturns it, "
        f"and say so explicitly if it does."
    )

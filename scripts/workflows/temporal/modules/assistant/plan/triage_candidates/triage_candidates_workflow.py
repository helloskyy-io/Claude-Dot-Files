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

    # THE COLUMN THIS RUN MUST NOT MOVE. `decision` is ours; `status` is a later
    # process's and never becomes ours — deciding to do something does not do it.
    before_status = act.candidate_statuses(wt_candidates)

    values = {
        "CANDIDATES_PATH": str(rel_candidates),
        "RESEARCH_DIR": str(rel_research),
        "WORKING_SET": _working_set(counts),
        "DIRECTION_CEILING": own.direction_ceiling(worktree / rel_research),
        "EXISTING_WORK": act.existing_work(repo_root, research_dir),
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

    # THE MIRROR OF plan-sprint's GUARD, and the split had left this side on prose
    # alone. `sprint.md` is the operator's own sequencing surface, this workflow
    # holds no override for it, and the prompt hands the model the exact trigger:
    # "if a candidate you ship looks like it needs a sprint section, say so." Not
    # taking a `sprint_path` parameter constrains the signature, never the run.
    touched = own.sprint_files_touched(worktree)
    if touched:
        raise RuntimeError(
            f"triage-candidates edited the sprint plan: {', '.join(touched)}. That "
            f"file is the operator's cross-domain sequencing surface and this "
            f"workflow holds NO authorization over it — `plan-sprint` carries the "
            f"only override, and it runs after this. A shipped candidate that looks "
            f"like it needs a sprint section is something to REPORT, never to "
            f"write — see {url}"
        )

    flipped = act.statuses_this_run_had_no_right_to(before_status,
                                                    act.candidate_statuses(wt_candidates))
    if flipped:
        raise RuntimeError(
            f"triage-candidates changed the `status` column on {len(flipped)} "
            f"candidate(s): {', '.join(flipped)}. Ruling a candidate is not doing it. "
            f"`status` belongs to a later process — `plan-feature`, or the build that "
            f"completes the item — and it did not move in the split — see {url}"
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

"""plan-sprint — keep the sprint plan current against the ruled candidates.

Folder holds only this file (§10.1 rule 6); the family's shared capability is
promoted to `plan_activities`.

WHAT THIS IS FOR. Candidates get ruled `ship` and then have to land somewhere.
This workflow places what is placeable in the sprint plan, reconciles sections
the research has since corrected, and reports what the three planning documents
say about each other. It is the sprint plan's maintainer.

IT NO LONGER TRIAGES, AND THAT IS THE POINT OF THE SPLIT. This workflow used to
do two jobs in one run — its own docstring said *"triage research candidates and
keep the sprint plan current"* — and nothing could be sequenced between them.
`triage_candidates` now owns the ruling, runs ahead of this, and **`decision` is
its output alone.** The post-condition that every row reach a disposition went
with it: a workflow that no longer writes the column must not raise about it.

That split also fixed an ordering defect for free. The sprint plan used to be
updated BEFORE anything estimated the work, so its hour totals landed ahead of
the estimates they depend on. `plan_project` now runs this LAST.

WHAT IT DELIBERATELY DOES NOT DO. It does not rule a candidate, it does not file
a `direction.md` row, and it does not write a phase doc. It reads
`problem-statement.md` and never writes it — that document is the thesis
everything else derives from, and the judgement in it is not delegable.

IT IS AUTHORISED TO EDIT THE SPRINT FILE, which is otherwise forbidden. The
governing rule's override covers exactly this case and rests on the PR being
human-reviewed before merge. **That authorization did not transfer to
`triage_candidates` and must not** — one workflow writes `sprint.md`, and it is
this one. The scope limits live in the prompt, where the model reading them can
be bound by them.
"""

from __future__ import annotations

from ... import routing

from pathlib import Path

from .. import plan_activities as act

_HERE = Path(__file__).resolve().parent
PROMPTS = _HERE / "prompts"

MODEL_KEY = "plan-sprint"

# An ESTIMATE, stated as one — this workflow has never been measured. The basis
# and the revise-from-measurement note live with the value in config.yaml.
WORKFLOW_KEY = "plan-sprint"   # NOT MODEL_KEY -- see run_claude's docstring
MAX_TURNS = act.max_turns(WORKFLOW_KEY)

COMPLETION_PATTERN = routing.PR_URL_COMPLETION_ERE


def run_plan_sprint(*, repo_root: Path, worktree: Path, sprint_path: Path,
                    candidates_path: Path, research_dir: Path,
                    pr_number: str | None = None, correction_pass: bool = False,
                    verbose: bool = False) -> str:
    """Place the ruled candidates, reconcile, sequence, report. Returns the PR URL."""
    # Paths arrive rooted at the REPO because that is where they are configured,
    # but the run reads and writes inside the WORKTREE. Count what the model will
    # actually see, and later re-read what it actually wrote.
    rel_candidates = candidates_path.relative_to(repo_root)
    rel_research = research_dir.relative_to(repo_root)
    wt_candidates = worktree / rel_candidates

    # Counted in code so the report cannot assert a total it invented.
    counts = act.candidate_counts(wt_candidates)

    # THE COLUMN THIS RUN MUST NOT MOVE, snapshotted before it can move it.
    before = act.candidate_decisions(wt_candidates)

    values = {
        "SPRINT_PATH": str(sprint_path.relative_to(repo_root)),
        "CANDIDATES_PATH": str(rel_candidates),
        "RESEARCH_DIR": str(rel_research),
        "CORRECTION_NOTE": (
            "\nThis is a CORRECTION PASS. A prior review returned HOLD with a scoped "
            "runway; close it. This is the last automated pass."
            if correction_pass else
            f"\n**Counted in code, authoritative — do not recount:** "
            f"{counts['total']} candidates, {counts['triaged']} ruled, "
            f"{counts['untriaged']} still untriaged.\n\n"
            f"{_untriaged_note(counts)}"
        ),
        "EXISTING_WORK": act.existing_work(repo_root, research_dir),
        "SUBMIT_PROMPT": act.submit_prompt(pr_number, "plan-sprint: place the ruled candidates and update the sprint plan"),
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
        "HEADLESS_EXECUTION_GUARD": act.shared_prompt("headless_execution_guard"),
    }

    output = act.run_claude(
        act.render(act.load_prompt(PROMPTS / "plan_sprint.md"), values),
        model_key=MODEL_KEY, workflow_key=WORKFLOW_KEY,
        completion_pattern=COMPLETION_PATTERN,
        repo_root=repo_root, worktree=worktree,
        max_turns=MAX_TURNS, verbose=verbose,
    )

    url = act.extract_pr_url(output)
    if not url:
        raise RuntimeError(
            "plan-sprint produced no PR URL. Its sprint edits are UNREVIEWED — the "
            "sprint plan must not be trusted as current."
        )

    # OBSERVE, DO NOT ASSERT. The prompt forbids writing `decision`; this reads
    # the file to check it did not. An authority transfer stated only in prose is
    # a convention a model can reason past — this is the mechanism.
    after = act.candidate_decisions(wt_candidates)
    moved = sorted(_rulings_this_run_had_no_right_to(before, after))
    if moved:
        raise RuntimeError(
            f"plan-sprint changed the `decision` column on {len(moved)} candidate(s): "
            + ", ".join(f"{cid} {before.get(cid, '<absent>')!r}->{after.get(cid, '<absent>')!r}"
                        for cid in moved)
            + ". That column is `triage-candidates`'s output alone. A ruling made "
              f"here is one no triage pass agreed to and no reviewer was told to "
              f"look for — see {url}"
        )
    return url


def _rulings_this_run_had_no_right_to(before: dict[str, str],
                                      after: dict[str, str]) -> list[str]:
    """Ids whose `decision` this run must not have touched, and did.

    Three ways to offend and ONE way not to, and the exemption is why this is a
    named function rather than a set comparison:

      * a ruling CHANGED  — re-litigating a triage pass's output
      * a row DISAPPEARED — the file's own rule is that nobody deletes a row
      * a NEW row arrives already RULED — triage, by another route

      * a NEW row arrives with a BLANK decision — **legitimate, and the naive
        comparison forbade it.** `decision_log_and_reflection.md` instructs
        EVERY producing run to place a proposal it surfaced into `candidates.md`
        with `decision` blank, and this workflow is a producing run. Diffing the
        two id sets outright made the shared placement instruction unfollowable:
        the run would place a proposal exactly as told and then fail its own
        post-condition. Blank is the absence of a ruling, so placing one is not
        ruling anything.
    """
    offences: list[str] = []
    for cid in before.keys() | after.keys():
        was, now = before.get(cid), after.get(cid)
        if cid not in after:
            offences.append(cid)            # deleted
        elif cid not in before:
            if now:                          # appended ALREADY ruled
                offences.append(cid)
        elif was != now:
            offences.append(cid)             # ruling rewritten
    return offences


def _untriaged_note(counts: dict) -> str:
    """What an untriaged row means to THIS workflow: nothing it may act on.

    Standalone, this workflow can meet a file `triage_candidates` has not been
    run against. The honest instruction is not "triage them" — that authority
    moved — and not silence either, because a model that sees blank cells in a
    column it is reading will fill them.
    """
    if not counts["untriaged"]:
        return ("Every row carries a decision. The `ship` rows are the set you "
                "place from.")
    return (
        f"**{counts['untriaged']} rows are UNTRIAGED and they are NOT YOURS: "
        f"{', '.join(counts['untriaged_ids'])}.** A blank `decision` means nothing "
        f"has ruled on that candidate yet, and ruling is `triage-candidates`'s job, "
        f"not this workflow's. **Do not set `decision` on any row, for any reason.** "
        f"Work only from the rows already marked `ship`; note the untriaged count in "
        f"your report so the operator can see triage has not caught up, and move on."
    )

"""plan-sprint — triage research candidates and keep the sprint plan current.

Folder holds only this file (§10.1 rule 6); the family's shared capability is
promoted to `plan_activities`.

WHAT THIS IS FOR. Research produces candidates and nothing routed them. Roughly
36 accumulated across four cycles, and the ones that got acted on got acted on
because a human happened to discuss them in a chat window. Seven ended up parked
on the standup tracker because no other surface would hold them, which that
tracker's own rules forbid. This workflow is the routing step that was missing.

WHAT IT DELIBERATELY DOES NOT DO. It decides; it does not design and it does not
build. It sets `decision` on a candidate and never `status`, because deciding to
do something does not do it. It may add a sprint section, never a phase doc. It
reads `problem-statement.md` and never writes it — that document is the thesis
everything else derives from, and the judgement in it is not delegable.

IT IS AUTHORISED TO EDIT THE SPRINT FILE, which is otherwise forbidden. The
governing rule's override covers exactly this case and rests on the PR being
human-reviewed before merge. The scope limits live in the prompt, where the
model reading them can be bound by them.
"""

from __future__ import annotations

from pathlib import Path

from .. import plan_activities as act

_HERE = Path(__file__).resolve().parent
PROMPTS = _HERE / "prompts"

MODEL_KEY = "plan-sprint"

# 250. NOT derived — this workflow has no V1 to read a constant out of, so the
# usual v1_constant() discipline does not apply and this is an estimate, stated
# as one. Basis: `research_write` does a comparable amount of reading-then-
# writing at 250 and peaks near 90 in practice. REVISE FROM MEASUREMENT after
# the first real runs; a cap set below an observed successful run has already
# cost a full budget once.
MAX_TURNS = 250

COMPLETION_PATTERN = r"https://github\.com/[^ )]+/pull/[0-9]+"


def run_plan_sprint(*, repo_root: Path, worktree: Path, sprint_path: Path,
                    candidates_path: Path, research_dir: Path,
                    pr_number: str | None = None, correction_pass: bool = False,
                    verbose: bool = False) -> str:
    """Triage candidates, sequence the sprint, report. Returns the PR URL."""
    # Counted in code so the report cannot assert a total it invented.
    counts = act.candidate_counts(candidates_path)

    values = {
        "SPRINT_PATH": str(sprint_path.relative_to(repo_root)),
        "CANDIDATES_PATH": str(candidates_path.relative_to(repo_root)),
        "RESEARCH_DIR": str(research_dir.relative_to(repo_root)),
        "CORRECTION_NOTE": (
            "\nThis is a CORRECTION PASS. A prior review returned HOLD with a scoped "
            "runway; close it. This is the last automated pass."
            if correction_pass else
            f"\n**Counted in code, authoritative — do not recount:** "
            f"{counts['total']} candidates, {counts['untriaged']} untriaged, "
            f"{counts['triaged']} already ruled."
        ),
        "EXISTING_WORK": act.existing_work(repo_root, research_dir),
        "SUBMIT_PROMPT": act.submit_prompt(pr_number, "plan-sprint: triage candidates and update the sprint plan"),
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
        "HEADLESS_EXECUTION_GUARD": act.shared_prompt("headless_execution_guard"),
    }

    output = act.run_claude(
        act.render(act.load_prompt(PROMPTS / "plan_sprint.md"), values),
        model_key=MODEL_KEY, completion_pattern=COMPLETION_PATTERN,
        repo_root=repo_root, worktree=worktree,
        max_turns=MAX_TURNS, verbose=verbose,
    )

    url = act.extract_pr_url(output)
    if not url:
        raise RuntimeError(
            "plan-sprint produced no PR URL. Its triage is UNREVIEWED — the "
            "candidates file and sprint plan must not be trusted as ruled."
        )
    return url

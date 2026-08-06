"""build-refine — FRESH context: did this deliver what was asked, then review and fix.

Folder holds only this file (§10.1 rule 6) — the family's trio is promoted to
`assistant_activities.py`.

The fresh context is the point, not an implementation detail: the run that
authored a change defends it, so refine never inherits draft's context. What
crosses is git plus the ORIGINAL TASK, which is why it can ask *did this deliver
what was asked* rather than merely *is this code good*.
"""

from __future__ import annotations

from pathlib import Path

from ... import assistant_activities as act

_HERE = Path(__file__).resolve().parent
PROMPTS = _HERE / "prompts"

MODEL_KEY = "build-refine"
V1_SCRIPT = "build-refine.sh"
COMPLETION_PATTERN = r"https://github\.com/[^ )]+/pull/[0-9]+"


def run_refine(*, description: str, pr_number: str, repo_root: Path,
               worktree: Path, task_file: str | None = None,
               correction_pass: bool = False, ci_unsettled: bool = False,
               verbose: bool = False) -> str:
    """Review and correct the draft's PR. Returns its PR URL."""
    values = {
        "DESCRIPTION": description,
        "STAGES_2_TO_4": act.load_prompt(PROMPTS / "stages_2_to_4.md"),
        "RULES": act.shared_prompt("rules"),
        "PR_NUMBER": pr_number,
        "PR_BRANCH": act.pr_branch(pr_number, repo_root),
        # Both notes are always substituted — empty when not applicable, so the
        # prompt never carries a literal ${...} and never needs a branch here.
        "CORRECTION_NOTE": (
            "This is a CORRECTION PASS. A prior review returned HOLD with a scoped "
            "runway; close it. This is the last automated pass."
            if correction_pass else ""
        ),
        "CI_STATUS_NOTE": (
            "CI had NOT settled when this pass started — treat check results as "
            "provisional and say so in your report."
            if ci_unsettled else ""
        ),
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
        "HEADLESS_EXECUTION_GUARD": act.shared_prompt("headless_execution_guard"),
    }

    output = act.run_claude(
        act.render(act.load_prompt(PROMPTS / "refine.md"), values),
        model_key=MODEL_KEY, completion_pattern=COMPLETION_PATTERN,
        repo_root=repo_root, worktree=worktree,
        max_turns=int(act.v1_constant(V1_SCRIPT, "MAX_TURNS")), verbose=verbose,
    )

    url = act.extract_pr_url(output)
    if not url:
        raise RuntimeError(
            f"build-refine produced no PR URL on PR #{pr_number}. "
            f"The PR EXISTS and is UNREVIEWED — it must not be merged as-is."
        )
    return url

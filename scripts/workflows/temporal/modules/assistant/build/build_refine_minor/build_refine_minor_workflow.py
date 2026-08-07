"""build-refine-minor — the light tier's review: ONE revision pass, fresh context.

Folder holds only this file (§10.1 rule 6). Fresh context is the point: the run
that authored a change defends it, so refine never inherits draft's context.
What crosses is git plus the original task.
"""

from __future__ import annotations

from pathlib import Path

from ... import assistant_activities as act

_HERE = Path(__file__).resolve().parent
PROMPTS = _HERE / "prompts"

MODEL_KEY = "build-refine-minor"
V1_SCRIPT = "build-refine-minor.sh"
COMPLETION_PATTERN = r"https://github\.com/[^ )]+/pull/[0-9]+"


def run_refine_minor(*, description: str, pr_number: str, repo_root: Path,
                     worktree: Path, correction_pass: bool = False,
                     ci_unsettled: bool = False, verbose: bool = False) -> str:
    """Review and correct the draft's PR. Returns its PR URL."""
    branch = act.pr_branch(pr_number, repo_root)
    values = {
        "DESCRIPTION": description,
        "STAGES_2_TO_4": act.load_prompt(PROMPTS / "stages_2_to_4.md"),
        "PR_NUMBER": pr_number,
        "PR_BRANCH": branch,
        "RULES": act.shared_prompt("rules"),
        # Always substituted — empty when not applicable, so no literal ${...}
        # can reach the model and no branch is needed here.
        "CORRECTION_NOTE": (
            "This is a CORRECTION PASS. A prior review returned HOLD with a scoped "
            "runway; close it. This is the last automated pass." if correction_pass else ""
        ),
        "CI_STATUS_NOTE": (
            "CI had NOT settled when this pass started — treat check results as "
            "provisional and say so in your report." if ci_unsettled else ""
        ),
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
        "HEADLESS_EXECUTION_GUARD": act.shared_prompt("headless_execution_guard"),
    }
    output = act.run_claude(
        act.render(act.load_prompt(PROMPTS / "refine.md"), values,
                   opaque=frozenset({"DESCRIPTION"})),
        model_key=MODEL_KEY, completion_pattern=COMPLETION_PATTERN,
        repo_root=repo_root, worktree=worktree,
        max_turns=int(act.v1_constant(V1_SCRIPT, "MAX_TURNS")),
        verbose=verbose,
    )
    url = act.extract_pr_url(output)
    if not url:
        raise RuntimeError(
            f"build-refine-minor produced no PR URL on PR #{pr_number}. "
            f"The PR EXISTS and is UNREVIEWED — it must not be merged as-is."
        )
    return url

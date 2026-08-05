"""build-draft-minor — the light tier's draft: one scoped change, one PR.

Folder holds only this file (§10.1 rule 6): the family's trio is promoted to the
purpose level. Its prompts are self-contained — unlike the major tier they pull
in neither RULES nor the headless guard, which is why they are larger.
"""

from __future__ import annotations

from pathlib import Path

from ... import assistant_activities as act

_HERE = Path(__file__).resolve().parent
PROMPTS = _HERE / "prompts"

MODEL_KEY = "build-draft-minor"
V1_SCRIPT = "build-draft-minor.sh"          # constants DERIVED, never re-declared
COMPLETION_PATTERN = r"https://github\.com/[^ )]+/pull/[0-9]+"


def run_draft_minor(*, description: str, repo_root: Path, worktree: Path,
                    pr_number: str | None = None, verbose: bool = False) -> str:
    """Draft a scoped change. Returns the PR URL — the handoff to refine."""
    template = act.load_prompt(PROMPTS / ("update_pr.md" if pr_number else "new_branch.md"))
    values = {
        "DESCRIPTION": description,
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
    }
    if pr_number:
        values |= {"PR_NUMBER": pr_number, "PR_BRANCH": act.pr_branch(pr_number, repo_root)}

    output = act.run_claude(
        act.render(template, values),
        model_key=MODEL_KEY, completion_pattern=COMPLETION_PATTERN,
        repo_root=worktree,
        max_turns=int(act.v1_constant(V1_SCRIPT, "MAX_TURNS")),
        verbose=verbose,
    )
    url = act.extract_pr_url(output)
    if not url:
        raise RuntimeError(
            "build-draft-minor produced no PR URL — cannot hand off to refine. "
            "The draft step must open (or update) a PR and print its URL as its final line."
        )
    return url

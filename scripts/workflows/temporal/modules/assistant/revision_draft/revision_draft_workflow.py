"""revision-draft — writes the change and opens an UNREVIEWED PR.

Folder holds only this file, which §10.1 rule 6 states is conformant: draft and
refine are a family sharing one promoted trio (`assistant_activities.py`), so
each member keeps just its workflow.

Its completion contract is the PR URL on the final line. `exit 0` without one
means the run did not finish, whatever it claims.
"""

from __future__ import annotations

from pathlib import Path

from .. import assistant_activities as act

_HERE = Path(__file__).resolve().parent
PROMPTS = _HERE / "prompts"

MODEL_KEY = "revision-draft"
COMPLETION_PATTERN = r"https://github\.com/[^ )]+/pull/[0-9]+"


def run_draft(*, description: str, repo_root: Path, worktree_name: str,
              pr_number: str | None = None, task_file: str | None = None,
              verbose: bool = False) -> str:
    """Draft the change. Returns the PR URL — the handoff to refine."""
    # Two prompts, two paths: updating an existing PR is a different task from
    # opening one, and the bash original branched the same way.
    template = act.load_prompt(PROMPTS / ("update_pr.md" if pr_number else "new_branch.md"))

    values = {
        "DESCRIPTION": description,
        "RULES": act.shared_prompt("rules"),
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
        "HEADLESS_EXECUTION_GUARD": act.shared_prompt("headless_execution_guard"),
    }
    if pr_number:
        values |= {"PR_NUMBER": pr_number, "PR_BRANCH": act.pr_branch(pr_number, repo_root)}

    output = act.run_claude(
        act.render(template, values),
        model_key=MODEL_KEY, completion_pattern=COMPLETION_PATTERN,
        repo_root=repo_root, worktree_name=None if pr_number else worktree_name,
        verbose=verbose,
    )

    url = act.extract_pr_url(output)
    if not url:
        raise RuntimeError(
            "revision-draft produced no PR URL — cannot hand off to refine. "
            "The draft step must open (or update) a PR and print its URL as its final line."
        )
    return url

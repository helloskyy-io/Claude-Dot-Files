"""build-draft — writes the change and opens an UNREVIEWED PR.

Folder holds only this file, which §10.1 rule 6 states is conformant: draft and
refine are a family sharing one promoted trio (`assistant_activities.py`), so
each member keeps just its workflow.

Its completion contract is the PR URL on the final line. `exit 0` without one
means the run did not finish, whatever it claims.
"""

from __future__ import annotations

from pathlib import Path

from ... import assistant_activities as act

_HERE = Path(__file__).resolve().parent
PROMPTS = _HERE / "prompts"

MODEL_KEY = "build-draft"
# Derived from V1, never re-declared — see assistant_activities.v1_constant.
V1_SCRIPT = "build-draft.sh"
COMPLETION_PATTERN = r"https://github\.com/[^ )]+/pull/[0-9]+"


def run_draft(*, description: str, repo_root: Path, worktree: Path,
              pr_number: str | None = None, task_file: str | None = None,
              plan_path: str | None = None, context: str = "",
              verbose: bool = False) -> str:
    """Draft the change. Returns the PR URL — the handoff to refine."""
    # Two prompts, two paths: updating an existing PR is a different task from
    # opening one, and the bash original branched the same way.
    # THE ONLY PLACE plan-vs-description is consulted. One axis: where the task
    # comes from. A plan run reads a doc and extracts success criteria to verify
    # against; a description run has the sentence as its only criterion.
    if plan_path:
        wrapper, stages = "from_plan.md", "stages_1_to_4_from_plan.md"
    else:
        wrapper = "update_pr.md" if pr_number else "new_branch.md"
        stages = "stages_1_to_4.md"
    template = act.load_prompt(PROMPTS / wrapper)

    values = {
        "DESCRIPTION": description,
        "STAGES_1_TO_4": act.load_prompt(PROMPTS / stages),
        "PLAN_PATH": plan_path or "",
        "CONTEXT_BLOCK": context,
        "RULES": act.shared_prompt("rules"),
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
        "HEADLESS_EXECUTION_GUARD": act.shared_prompt("headless_execution_guard"),
    }
    if pr_number:
        values |= {"PR_NUMBER": pr_number, "PR_BRANCH": act.pr_branch(pr_number, repo_root)}

    # ISOLATION IS ESTABLISHED ONCE, BY THE PARENT, and this child RECEIVES the
    # worktree path. An earlier version had every child call worktree_add with
    # the same parent-supplied name, so draft created it and refine died on
    # `fatal: ... already exists` — the fix was right in principle and applied at
    # the wrong altitude. A child that creates its own isolation cannot know
    # whether a sibling already did.
    output = act.run_claude(
        act.render(template, values),
        model_key=MODEL_KEY, completion_pattern=COMPLETION_PATTERN,
        repo_root=repo_root, worktree=worktree,
        max_turns=int(act.v1_constant(V1_SCRIPT, "MAX_TURNS")),
        verbose=verbose,
    )

    url = act.extract_pr_url(output)
    if not url:
        raise RuntimeError(
            "build-draft produced no PR URL — cannot hand off to refine. "
            "The draft step must open (or update) a PR and print its URL as its final line."
        )
    return url

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
                    pr_number: str | None = None, plan_path: str | None = None,
                    context: str = "", verbose: bool = False) -> str:
    """Draft a scoped change. Returns the PR URL — the handoff to refine."""
    # Same single axis as the major tier. Scope is what makes this the minor
    # tier — a 100-turn cap — not the information source. A small fix scoped to
    # a phase still benefits from that phase's success criteria to verify against.
    if plan_path:
        wrapper, stages = "from_plan.md", "stages_1_to_4_from_plan.md"
    else:
        wrapper = "update_pr.md" if pr_number else "new_branch.md"
        stages = None
    template = act.load_prompt(PROMPTS / wrapper)
    values = {
        "DESCRIPTION": description,
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
    }
    if stages:
        values |= {
            "STAGES_1_TO_4": act.load_prompt(PROMPTS / stages),
            "RULES": act.shared_prompt("rules"),
            "HEADLESS_EXECUTION_GUARD": act.shared_prompt("headless_execution_guard"),
            "PLAN_PATH": plan_path, "CONTEXT_BLOCK": context,
        }
    if pr_number:
        values |= {"PR_NUMBER": pr_number, "PR_BRANCH": act.pr_branch(pr_number, repo_root)}

    output = act.run_claude(
        act.render(template, values,
                   opaque=frozenset({"DESCRIPTION"})),
        model_key=MODEL_KEY, completion_pattern=COMPLETION_PATTERN,
        repo_root=repo_root, worktree=worktree,
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

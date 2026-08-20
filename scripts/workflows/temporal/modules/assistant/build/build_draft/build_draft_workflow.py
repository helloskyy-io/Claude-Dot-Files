"""build-draft — writes the change and opens an UNREVIEWED PR.

Folder holds only this file, which §10.1 rule 6 states is conformant: draft and
refine are a family sharing one promoted trio (`assistant_activities.py`), so
each member keeps just its workflow.

Its completion contract is the PR URL on the final line. `exit 0` without one
means the run did not finish, whatever it claims.
"""

from __future__ import annotations

from ... import routing

from pathlib import Path

from ... import assistant_activities as act

_HERE = Path(__file__).resolve().parent
PROMPTS = _HERE / "prompts"

MODEL_KEY = "build-draft"
WORKFLOW_KEY = "build-draft"   # the run log's per-workflow bin; see run_log.py
MAX_TURNS_KEY = WORKFLOW_KEY
COMPLETION_PATTERN = routing.PR_URL_COMPLETION_ERE


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
    # BOTH plan-driven prompts are SHARED with build_draft_minor — the two tiers
    # differ in turn budget and review depth, not in how a plan is read. They
    # were byte-identical copies until §10.1's promotion rule was applied to
    # prose; edit them at modules/assistant/prompts/.
    #
    # TWO AXES, NOT ONE, AND CONFLATING THEM ABANDONED THE PR. `plan_path`
    # selects the TASK SHAPE; `pr_number` selects the DESTINATION. This read
    # `if plan_path:` alone, so `--pr 124 --phase <doc>` — the exact shape the
    # operator used on PR #124 — selected `build_from_plan.md`, which opens
    # "on a new branch", says "create a new PR using gh pr create", binds no
    # ${PR_NUMBER} and never names the PR. The parent has already cut the
    # worktree from `origin/<PR 124's branch>`, so the child sits on a branch
    # that already has an open PR and is told to open one: either `gh pr create`
    # fails and the dispatch dies with "produced no PR URL", or a second PR
    # opens and #124's runway, review history and CI record are abandoned.
    # The destination wins. What the combination gives up is `${PLAN_PATH}` and
    # the from-plan stages — which is exactly the pre-2026-08-20 behaviour, so
    # nothing regresses; the plan doc's CONTENTS still reach the model, because
    # `task_text` reads `plan_path` and supplies it as DESCRIPTION.
    if plan_path and not pr_number:
        template = act.shared_prompt("build_from_plan")
        stages_body = act.shared_prompt("stages_1_to_4_from_plan")
    else:
        wrapper = "update_pr.md" if pr_number else "new_branch.md"
        template = act.load_prompt(PROMPTS / wrapper)
        stages_body = act.load_prompt(PROMPTS / "stages_1_to_4.md")

    values = {
        "DESCRIPTION": description,
        "STAGES_1_TO_4": stages_body,
        "PLAN_PATH": plan_path or "",
        "CONTEXT_BLOCK": context,
        "RULES": act.shared_prompt("rules"),
        # SHARED because it was forked and drifted — see prompts/mutation_discipline.md.
        "MUTATION_DISCIPLINE": act.shared_prompt("mutation_discipline"),
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
        act.render(template, values,
                   opaque=frozenset({"DESCRIPTION"})),
        model_key=MODEL_KEY, workflow_key=WORKFLOW_KEY,
        completion_pattern=COMPLETION_PATTERN,
        repo_root=repo_root, worktree=worktree,
        max_turns=act.max_turns(MAX_TURNS_KEY),
        verbose=verbose,
    )

    url = act.extract_pr_url(output)
    if not url:
        raise RuntimeError(
            "build-draft produced no PR URL — cannot hand off to refine. "
            "The draft step must open (or update) a PR and print its URL as its final line."
        )
    return url

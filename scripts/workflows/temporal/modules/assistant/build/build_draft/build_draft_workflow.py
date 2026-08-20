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
              pr_number: str | None = None,
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
    if plan_path:
        template = act.shared_prompt("build_from_plan")
        stages_body = act.shared_prompt("stages_1_to_4_from_plan")
    else:
        wrapper = "update_pr.md" if pr_number else "new_branch.md"
        template = act.load_prompt(PROMPTS / wrapper)
        stages_body = act.load_prompt(PROMPTS / "stages_1_to_4.md")

    values = {
        "DESCRIPTION": description,
        # TIER IDENTITY, DERIVED FROM `WORKFLOW_KEY` AND NEVER RE-TYPED. The
        # shared plan template used to hardcode `BUILD-PHASE` / `feat:` /
        # `build-phase:`, so every plan-driven run of EITHER tier was told it
        # was a workflow that exists only in the FROZEN bash fleet — which
        # `config/rules/personal-tooling.md` forbids depending on and which the
        # operator deletes when it stops being needed. `tier-identity` is
        # TIER_SCOPED in `tests/unit/fork_vs_parameterize.py`, naming the
        # commit-message prefix explicitly, so the ruling was already made:
        # parameterise it rather than share it.
        "WORKFLOW_LABEL": WORKFLOW_KEY.upper(),
        "TIER_PREFIX": f"{WORKFLOW_KEY}:",
        "STAGES_1_TO_4": stages_body,
        "PLAN_PATH": plan_path or "",
        "CONTEXT_BLOCK": context,
        "VERIFY_THE_TASKS_ASSERTED_FACTS": act.shared_prompt("verify_the_tasks_asserted_facts"),
        "RULES": act.shared_prompt("rules"),
        # SHARED because it was forked and drifted — see prompts/mutation_discipline.md.
        "MUTATION_DISCIPLINE": act.shared_prompt("mutation_discipline"),
        "GITIGNORE_COLLISION_CHECK": act.shared_prompt("gitignore_collision_check"),
        # UNCONDITIONAL because BOTH bodies reference it now. This tier held a
        # TRUNCATED inline copy — the antecedent sentence naming the measured
        # case had been lost, so "the four real defects it did find" referred to
        # nothing — while the plan body carried the rule on no path at all.
        # `evidence-discipline` is TIER_INVARIANT, so a path without it is a
        # dispatch running a different rule.
        "CHARACTERIZE_BY_EXECUTION": act.shared_prompt("characterize_by_execution"),
        "STAGE_ORDER_IS_MANDATORY": act.shared_prompt("stage_order_is_mandatory"),
        "VERIFICATION_IS_BY_FETCH": act.shared_prompt("verification_is_by_fetch"),
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

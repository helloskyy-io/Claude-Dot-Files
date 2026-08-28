"""build-refine-minor — the light tier's review: ONE revision pass, fresh context.

Folder holds only this file (§10.1 rule 6). Fresh context is the point: the run
that authored a change defends it, so refine never inherits draft's context.
What crosses is git plus the original task.
"""

from __future__ import annotations

from ... import routing

from pathlib import Path

from ... import assistant_activities as act
from .. import build_helper as helper

_HERE = Path(__file__).resolve().parent
PROMPTS = _HERE / "prompts"

MODEL_KEY = "build-refine-minor"
WORKFLOW_KEY = "build-refine-minor"   # the run log's per-workflow bin; see run_log.py
MAX_TURNS_KEY = WORKFLOW_KEY
COMPLETION_PATTERN = routing.PR_URL_COMPLETION_ERE


def run_refine_minor(*, description: str, pr_number: str, repo_root: Path,
                     worktree: Path, correction_pass: bool = False,
                     loops_left: int = 0, ci_unsettled: bool = False,
                     verbose: bool = False) -> str:
    """Review and correct the draft's PR. Returns its PR URL."""
    branch = act.pr_branch(pr_number, repo_root)
    values = {
        "DESCRIPTION": description,
        "STAGES_2_TO_4": act.load_prompt(PROMPTS / "stages_2_to_4.md"),
        # SHARED WITH build_refine — the values dict below IS the count. See that
        # workflow, which
        # carries the note on why the last five arrived by drift. What stays
        # local here is only what the ONE-lens tier says differently.
        "FIDELITY_PREMISE": act.shared_prompt("fidelity_premise"),
        "FIDELITY_READ_AND_COMPARE": act.shared_prompt("fidelity_read_and_compare"),
        "FIDELITY_NEEDS_A_SEPARATE_RUN": act.shared_prompt("fidelity_needs_a_separate_run"),
        "FIDELITY_EVIDENCE_DISCIPLINE": act.shared_prompt("fidelity_evidence_discipline"),
        "FIDELITY_MUTATE_WHAT_YOU_ADDED": act.shared_prompt("fidelity_mutate_what_you_added"),
        "RESOLVE_DISPOSITION_AUTHORITY": act.shared_prompt("resolve_disposition_authority"),
        "RESOLVE_REJECTIONS_MUST_BE_EXECUTED": act.shared_prompt("resolve_rejections_must_be_executed"),
        "RESOLVE_CLOSED_DISPOSITION_LIST": act.shared_prompt("resolve_closed_disposition_list"),
        "RESOLVE_DISPOSITION_DEFINITIONS": act.shared_prompt("resolve_disposition_definitions"),
        "RESOLVE_FIX_BY_DEFAULT_AND_SUMMARY": act.shared_prompt("resolve_fix_by_default_and_summary"),
        "VERIFY_AND_CI_GATE": act.shared_prompt("verify_and_ci_gate"),
        "SUBMIT_AND_PUSH": act.shared_prompt("submit_and_push"),
        "PR_NUMBER": pr_number,
        "PR_BRANCH": branch,
        "RULES": act.shared_prompt("rules"),
        # Always substituted — empty when not applicable, so no literal ${...}
        # can reach the model and no branch is needed here.
        "CORRECTION_NOTE": (
            "This is a CORRECTION PASS, and what that means is the load-bearing part: "
            "a prior pass looked at this work and believed it complete, and a reviewer "
            "found this anyway. **Treat every runway item as an INSTANCE, not as the whole.**\n\n"
            "For each item: name the CLASS it belongs to, search the tree for every other "
            "member of that class, and fix them together. Then leave a check that matches "
            "the CLASS — not the instances you happened to find — so the next member FAILS "
            "rather than being discovered by a later pass.\n\n"
            "**Why this and not simply \'fix what was listed\':** measured across three "
            "independent controls upstream, each correction pass closed one spelling and the "
            "next pass found a structurally ADJACENT one — five passes, five spellings; four "
            "passes, four spellings; one pass closed a step-level bypass and the next found its "
            "twin one indentation away. Enumerating instances does not converge. Changing what "
            "the check keys on does. Measured locally the same week: a drift guard written as a "
            "class-check caught its own authors twice within one afternoon, which no number of "
            "further review passes would have done.\n\n"
            "If an item genuinely has no class — a true one-off — say so explicitly and say how "
            "you established it. " + helper.finality_note(loops_left)
            if correction_pass else ""
        ),
        "CI_STATUS_NOTE": (
            "CI had NOT settled when this pass started — treat check results as "
            "provisional and say so in your report." if ci_unsettled else ""
        ),
        "STAGE_ORDER_IS_MANDATORY": act.shared_prompt("stage_order_is_mandatory"),
        "ORCHESTRATOR_EXECUTES_AGENTS_READ": act.shared_prompt("orchestrator_executes_agents_read"),
        "RESOLVE_APPLY_THE_REMEDY_YOU_WROTE": act.shared_prompt("resolve_apply_the_remedy_you_wrote"),
        "SWEEP_THE_CLASS": act.shared_prompt("resolve_sweep_the_class"),
        "RESOLVE_REJECTING_IS_LEGITIMATE": act.shared_prompt("resolve_rejecting_is_legitimate"),
        "RESOLVE_YOUR_OWN_DISPOSITIONS_TOO": act.shared_prompt("resolve_your_own_dispositions_too"),
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
        "HEADLESS_EXECUTION_GUARD": act.shared_prompt("headless_execution_guard"),
    }
    output = act.run_claude(
        act.render(act.load_prompt(PROMPTS / "refine.md"), values,
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
            f"build-refine-minor produced no PR URL on PR #{pr_number}. "
            f"The PR EXISTS and is UNREVIEWED — it must not be merged as-is."
        )
    return url

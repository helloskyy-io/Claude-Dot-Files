"""build-refine — FRESH context: did this deliver what was asked, then review and fix.

Folder holds only this file (§10.1 rule 6) — the family's trio is promoted to
`assistant_activities.py`.

The fresh context is the point, not an implementation detail: the run that
authored a change defends it, so refine never inherits draft's context. What
crosses is git plus the ORIGINAL TASK, which is why it can ask *did this deliver
what was asked* rather than merely *is this code good*.
"""

from __future__ import annotations

from ... import routing

from pathlib import Path

from ... import assistant_activities as act
from .. import build_helper as helper

_HERE = Path(__file__).resolve().parent
PROMPTS = _HERE / "prompts"

MODEL_KEY = "build-refine"
WORKFLOW_KEY = "build-refine"   # the run log's per-workflow bin; see run_log.py
MAX_TURNS_KEY = WORKFLOW_KEY
COMPLETION_PATTERN = routing.PR_URL_COMPLETION_ERE


def run_refine(*, description: str, pr_number: str, repo_root: Path,
               worktree: Path, task_file: str | None = None,
               correction_pass: bool = False, loops_left: int = 0,
               ci_unsettled: bool = False, verbose: bool = False) -> str:
    """Review and correct the draft's PR. Returns its PR URL."""
    values = {
        "DESCRIPTION": description,
        "STAGES_2_TO_4": act.load_prompt(PROMPTS / "stages_2_to_4.md"),
        # SIX FRAGMENTS SHARED WITH build_refine_minor. The two tiers differ in
        # how many review lenses they run, never in what a refine pass IS — so
        # the fidelity premise, the closed disposition list and the verify gate
        # are one text. §10.1: consumer count decides. Edit them under prompts/.
        "FIDELITY_PREMISE": act.shared_prompt("fidelity_premise"),
        "FIDELITY_NEEDS_A_SEPARATE_RUN": act.shared_prompt("fidelity_needs_a_separate_run"),
        "RESOLVE_DISPOSITION_AUTHORITY": act.shared_prompt("resolve_disposition_authority"),
        "RESOLVE_CLOSED_DISPOSITION_LIST": act.shared_prompt("resolve_closed_disposition_list"),
        "RESOLVE_FIX_BY_DEFAULT": act.shared_prompt("resolve_fix_by_default"),
        "VERIFY_AND_CI_GATE": act.shared_prompt("verify_and_ci_gate"),
        "RULES": act.shared_prompt("rules"),
        "PR_NUMBER": pr_number,
        "PR_BRANCH": act.pr_branch(pr_number, repo_root),
        # Both notes are always substituted — empty when not applicable, so the
        # prompt never carries a literal ${...} and never needs a branch here.
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
            "provisional and say so in your report."
            if ci_unsettled else ""
        ),
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
        "HEADLESS_EXECUTION_GUARD": act.shared_prompt("headless_execution_guard"),
    }

    output = act.run_claude(
        act.render(act.load_prompt(PROMPTS / "refine.md"), values,
                   opaque=frozenset({"DESCRIPTION"})),
        model_key=MODEL_KEY, workflow_key=WORKFLOW_KEY,
        completion_pattern=COMPLETION_PATTERN,
        repo_root=repo_root, worktree=worktree,
        max_turns=act.max_turns(MAX_TURNS_KEY), verbose=verbose,
    )

    url = act.extract_pr_url(output)
    if not url:
        raise RuntimeError(
            f"build-refine produced no PR URL on PR #{pr_number}. "
            f"The PR EXISTS and is UNREVIEWED — it must not be merged as-is."
        )
    return url

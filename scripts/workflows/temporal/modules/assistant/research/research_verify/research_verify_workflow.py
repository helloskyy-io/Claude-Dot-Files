"""research-verify — FRESH context: verify the papers, fix, trace, verify the synthesis.

Folder holds only this file (§10.1 rule 6).

Three jobs the monolith never separated:
  1. verify each paper (this existed, as stage 4)
  2. trace every correction through to the synthesis (§4 binding rule, never executed)
  3. verify the SYNTHESIS itself (never existed at all)

Job 3 is why this child exists. The synthesis carries a paper's full sourcing
burden per §4 and is the only artifact the standup consumes — and nothing
checked it. A wrong count in one cycle's synthesis propagated into the next
cycle's dispatch prompts and mis-instructed two analysts.
"""

from __future__ import annotations

from pathlib import Path

from .. import research_activities as act

_HERE = Path(__file__).resolve().parent
PROMPTS = _HERE / "prompts"

MODEL_KEY = "research"
# Its own key, not `research` — see research_write for why the cap is keyed by
# workflow rather than by model. Measurement lives with the value in config.yaml.
MAX_TURNS = act.max_turns("research-verify")

COMPLETION_PATTERN = r"https://github\.com/[^ )]+/pull/[0-9]+"


def run_verify(*, research_dir: Path, pr_number: str, repo_root: Path,
               worktree: Path, correction_pass: bool = False,
               verbose: bool = False) -> str:
    """Verify, correct, trace, and re-verify. Returns the PR URL."""
    currency, _due = act.paper_currency(research_dir)
    values = {
        "RESEARCH_DIR": str(research_dir),
        "PR_NUMBER": pr_number,
        "PR_BRANCH": act.branch_of(pr_number, repo_root),
        "CURRENCY_BLOCK": currency,
        "CORRECTION_NOTE": (
            "This is a CORRECTION PASS. A prior disposition returned HOLD with a "
            "scoped runway; close it. This is the last automated pass."
            if correction_pass else ""
        ),
        "SUBMIT_PROMPT": act.submit_prompt(pr_number, f"research-verify: {research_dir}"),
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
    }
    output = act.run_claude(
        act.render(act.load_prompt(PROMPTS / "verify.md"), values),
        model_key=MODEL_KEY, completion_pattern=COMPLETION_PATTERN,
        repo_root=repo_root, worktree=worktree, max_turns=MAX_TURNS, verbose=verbose,
    )
    from ...assistant_activities import extract_pr_url
    url = extract_pr_url(output)
    if not url:
        raise RuntimeError(
            f"research-verify produced no PR URL on PR #{pr_number}. The pool and "
            f"synthesis are UNVERIFIED — the PR must not be merged as-is."
        )
    return url

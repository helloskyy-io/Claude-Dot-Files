"""research-write — produce the pool and a DRAFT synthesis, open the PR.

Folder holds only this file (§10.1 rule 6): the family's shared capability is
promoted to `research_activities`.

Completion contract: the PR URL on the final line.

The synthesis it writes is explicitly a DRAFT. A separate fresh-context run
verifies the papers, applies corrections and traces each one through to it —
because the run that wrote an artifact defends it.
"""

from __future__ import annotations

from pathlib import Path

from .. import research_activities as act

_HERE = Path(__file__).resolve().parent
PROMPTS = _HERE / "prompts"

MODEL_KEY = "research"
V1_SCRIPT = "../research.sh"

# MEASURED: cycle 4 used 43. The prior 250 came from the MONOLITH's 89-turn peak, before the split
# existed — decomposition changes the shape, so a pre-split number does not transfer.
MAX_TURNS = 150

COMPLETION_PATTERN = r"https://github\.com/[^ )]+/pull/[0-9]+"


def run_write(*, research_dir: Path, repo_root: Path, worktree: Path,
              context: str = "", pr_number: str | None = None,
              verbose: bool = False) -> str:
    """Discover, size, research, draft the synthesis, submit. Returns the PR URL."""
    currency, _due = act.paper_currency(research_dir)
    values = {
        "RESEARCH_DIR": str(research_dir),
        "CONTEXT_BLOCK": f"{context}\n\n{currency}" if context else currency,
        "SUBMIT_PROMPT": act.submit_prompt(pr_number, f"research: {research_dir}"),
        "CANDIDATE_CEILING": act.candidate_ceiling(research_dir),
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
        "HEADLESS_EXECUTION_GUARD": act.shared_prompt("headless_execution_guard"),
    }
    output = act.run_claude(
        act.render(act.load_prompt(PROMPTS / "write.md"), values),
        model_key=MODEL_KEY, completion_pattern=COMPLETION_PATTERN,
        repo_root=repo_root, worktree=worktree, max_turns=MAX_TURNS, verbose=verbose,
    )
    from ...assistant_activities import extract_pr_url
    url = extract_pr_url(output)
    if not url:
        raise RuntimeError(
            "research-write produced no PR URL — cannot hand off to verify. "
            "The run must open (or update) a PR and print its URL as its final line."
        )
    return url

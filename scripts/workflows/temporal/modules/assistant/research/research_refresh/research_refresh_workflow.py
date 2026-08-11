"""research-refresh — the produce leg for revalidation.

The ONLY child that differs from `research`'s pipeline. Two things vary, which
is why this is a separate workflow rather than a flag on research_write:

  1. the AGENT — `research-currency` diffs an existing paper against a fresh
     sweep, rather than `research-analyst` writing a new one
  2. the WORK LIST — a mechanical date gate computed in code, not a sizing
     rubric applied by a model

Two axes means a flag would fail the cap we hold elsewhere. Children 2 and 3
(`research_verify`, `review_pr`) are SHARED with `research` unchanged.
"""

from __future__ import annotations

from ... import routing

from pathlib import Path

from .. import research_activities as act
from ...assistant_activities import extract_pr_url

_HERE = Path(__file__).resolve().parent
PROMPTS = _HERE / "prompts"

MODEL_KEY = "research-refresh"
# ⚠ This value and research-refresh.sh's disagreed (250 vs 200) with no reason
# recorded on either side. Converged upward in config.yaml on 2026-08-10 and
# FLAGGED THERE for review — it is a safe default, not a measurement.
MAX_TURNS = act.max_turns("research-refresh")
COMPLETION_PATTERN = routing.PR_URL_COMPLETION_ERE


def due_papers(research_dir: Path) -> list[Path]:
    """The mechanical gate — computed in code, BEFORE any model spend.

    This is what lets a refresh cost nothing when nothing is due: no papers due
    means a clean no-op exit, which `research` can never do because it always
    spends. It is also the pruning half of the loop — `research-currency` is the
    only agent that re-examines whether a topic is still the right question.
    """
    _table, due = act.paper_currency(research_dir)
    return due


def run_refresh(*, research_dir: Path, repo_root: Path, worktree: Path,
                due: list[Path], pr_number: str | None = None,
                verbose: bool = False) -> str:
    """Revalidate the due papers and draft the synthesis diff. Returns the PR URL."""
    if not due:
        raise ValueError("run_refresh called with no due papers — the gate should have exited first")

    # Same altitude split as research-write, and for the same reason: a
    # component pool that grows its own candidates.md and direction.md forks
    # the operator's inbox. Derived from the path, never declared.
    level = act.altitude(research_dir, repo_root)
    fragment = "altitude_product.md" if level == "PRODUCT" else "altitude_component.md"

    values = {
        "RESEARCH_DIR": str(research_dir),
        "DUE_LIST": "\n".join(f"- {p}" for p in due),
        "SUBMIT_PROMPT": act.submit_prompt(pr_number, f"research-refresh: {research_dir}"),
        "ALTITUDE_BLOCK": act.load_prompt(PROMPTS / fragment),
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
        "HEADLESS_EXECUTION_GUARD": act.shared_prompt("headless_execution_guard"),
    }
    if level == "PRODUCT":
        values["CANDIDATE_CEILING"] = act.candidate_ceiling(research_dir)
    output = act.run_claude(
        act.render(act.load_prompt(PROMPTS / "refresh.md"), values),
        model_key=MODEL_KEY, completion_pattern=COMPLETION_PATTERN,
        repo_root=repo_root, worktree=worktree, max_turns=MAX_TURNS, verbose=verbose,
    )
    url = extract_pr_url(output)
    if not url:
        raise RuntimeError("research-refresh produced no PR URL — cannot hand off to verify.")
    return url

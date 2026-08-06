"""Shared I/O for the planning family — promoted per §10.1 rule 3.

Sits at module level because `plan_sprint` and `plan_tech_stack` will both use
it. Today it has one consumer; the second is why it is here rather than inside
plan_sprint/, and the promotion rule is satisfied the moment that lands.

NOT IDEMPOTENT (§7.1): these push commits and open PRs. Under Temporal a retry
is a NEW ATTEMPT, not a replay.
"""

from __future__ import annotations

import re
from pathlib import Path

from .. import assistant_activities as shared

load_prompt = shared.load_prompt
shared_prompt = shared.shared_prompt
render = shared.render
run_claude = shared.run_claude
worktree_add = shared.worktree_add
extract_pr_url = shared.extract_pr_url
observe_outcome = shared.observe_outcome

# A candidate row: | C-001 | title | source | `decision` | `status` | note |
_ROW = re.compile(r"^\|\s*(C-\d{3})\s*\|.*?\|.*?\|\s*(.*?)\s*\|\s*(.*?)\s*\|", re.M)


def candidate_counts(candidates_path: Path) -> dict[str, int]:
    """Count rows by triage state — computed in code, never asked of a model.

    Arithmetic is not delegated: a model once marked four of eight papers past
    window when one was, every flag internally consistent against a date it had
    invented. The same rule applies to any count a prompt or a report asserts.
    """
    if not candidates_path.exists():
        raise FileNotFoundError(
            f"candidates file not found: {candidates_path}. "
            f"plan-sprint triages candidates; without the file there is nothing to triage."
        )
    rows = _ROW.findall(candidates_path.read_text())
    untriaged = sum(1 for _id, dec, _st in rows if dec.strip() in ("", "—"))
    return {
        "total": len(rows),
        "untriaged": untriaged,
        "triaged": len(rows) - untriaged,
    }


def submit_prompt(pr_number: str | None, label: str) -> str:
    if pr_number:
        return (f"- Stage and commit your changes with message `{label}`\n"
                f"- Push to the PR branch and report PR #{pr_number}'s URL as your FINAL line")
    return (f"- Stage and commit your changes with message `{label}`\n"
            f"- Push the branch and open a PR; report its URL as your FINAL line")

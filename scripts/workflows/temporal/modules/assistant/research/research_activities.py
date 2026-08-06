"""Shared I/O for the research family — promoted per §10.1 rule 3.

Two workflows use it (`research` and `research_refresh`), so consumer count
puts it here rather than in either workflow's folder.

NOT IDEMPOTENT (§7.1 / addendum §A1): these push commits and open PRs. Under
Temporal a retry is a NEW ATTEMPT, not a replay.
"""

from __future__ import annotations

import re
import subprocess
from datetime import date, datetime
from pathlib import Path

from .. import assistant_activities as shared

# Re-exported so the research workflows use one name regardless of where a
# capability is implemented.
load_prompt = shared.load_prompt
shared_prompt = shared.shared_prompt
render = shared.render
run_claude = shared.run_claude
worktree_add = shared.worktree_add
observe_outcome = shared.observe_outcome
gh = shared.gh

_WORKFLOWS = Path(__file__).resolve().parents[3]

# Header contract from the Research Standard §3.
_LAST_VALIDATED = re.compile(r"^Last validated:\s*(\d{4}-\d{2}-\d{2})", re.M)
_REVALIDATE = re.compile(r"^Revalidate:\s*.*?(\d+)\s*(week|month)", re.M | re.I)
_RETIRED = re.compile(r"^Revalidate:\s*retired", re.M | re.I)


def paper_currency(research_dir: Path, today: date | None = None) -> tuple[str, list[Path]]:
    """Compute staleness in code and return (rendered table, due papers).

    ARITHMETIC IS NEVER DELEGATED TO A MODEL. A model once marked four of eight
    papers past window when one was — and every flag was internally consistent
    against a "today" it had invented. Correct arithmetic, wrong anchor, and the
    error was invisible because the reasoning looked sound.

    The same rule the refresh gate uses, so the two mechanisms cannot disagree
    about the same pool.
    """
    today = today or date.today()
    rows, due = [], []
    for paper in sorted((research_dir / "raw").glob("*.md")):
        text = paper.read_text()
        if _RETIRED.search(text):
            rows.append(f"| `{paper.name}` | — | retired | **RETIRED** — provenance, not input |")
            continue
        lv, iv = _LAST_VALIDATED.search(text), _REVALIDATE.search(text)
        if not lv or not iv:
            rows.append(f"| `{paper.name}` | ? | ? | **UNPARSEABLE HEADER** — does not meet §3 |")
            due.append(paper)
            continue
        validated = datetime.strptime(lv.group(1), "%Y-%m-%d").date()
        days = int(iv.group(1)) * (30 if iv.group(2).lower().startswith("month") else 7)
        due_date = validated + __import__("datetime").timedelta(days=days)
        if today > due_date:
            rows.append(f"| `{paper.name}` | {validated} | {iv.group(1)} {iv.group(2)}s | **PAST WINDOW** (due {due_date}) |")
            due.append(paper)
        else:
            rows.append(f"| `{paper.name}` | {validated} | {iv.group(1)} {iv.group(2)}s | current (due {due_date}) |")

    table = "\n".join([
        "--- paper currency (computed in code — AUTHORITATIVE) ---",
        f"Today is {today}. {len(due)} of {len(rows)} papers are past their revalidation window.",
        "", "| Paper | Last validated | Interval | Status |", "|---|---|---|---|", *rows, "",
        "**Use these verdicts verbatim. Do NOT recompute them.** A paper marked `current` is",
        "current — do not caveat its claims for age. A prior synthesis is a CONSUMABLE, not an",
        "authority: where it disagrees with this table, the table wins.",
        "--- end paper currency ---",
    ])
    return table, due


def candidate_ceiling(research_dir: Path) -> str:
    """The highest C-NNN in use, computed in code and handed over.

    A run that guesses the next ID collides with an existing one or skips a
    block; either way the file's promise — that an ID is stable and never
    reused — breaks silently. Same discipline as every other count here.
    """
    f = research_dir / "candidates.md"
    if not f.exists():
        return ("`candidates.md` does NOT exist yet — create it and start at `C-001`.")
    ids = sorted(re.findall(r"^\|\s*C-(\d{3})\s*\|", f.read_text(), re.M))
    if not ids:
        return "`candidates.md` exists but holds no rows — start at `C-001`."
    return (f"`candidates.md` holds **{len(ids)} rows**, highest ID **C-{ids[-1]}**. "
            f"A NEW candidate starts at **C-{int(ids[-1]) + 1:03d}**. "
            f"A restatement of an existing candidate REUSES its ID — do not mint a new one.")


def submit_prompt(pr_number: str | None, label: str) -> str:
    """The SUBMIT stage's two shapes — new PR versus updating one."""
    if pr_number:
        return (f"- Stage and commit remaining changes with message `{label}`\n"
                f"- Push to the PR branch and report PR #{pr_number}'s URL as your FINAL line")
    return (f"- Stage and commit all changes with message `{label}`\n"
            f"- Push the branch and open a PR; report its URL as your FINAL line")


def branch_of(pr_number: str, repo_root: Path) -> str:
    return shared.pr_branch(pr_number, repo_root)


def v1_max_turns(script: str) -> int:
    """Derived from V1 while the bash script still exists."""
    return int(shared.v1_constant(script, "MAX_TURNS"))

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


# Research Standard §1 names TWO altitudes and one location each. The product
# pool is a single known path; everything else is a component pool.
PRODUCT_POOL = Path("docs/standards/architecture/research")


def altitude(research_dir: Path, repo_root: Path) -> str:
    """PRODUCT or COMPONENT, DERIVED from the path — never declared twice.

    The invocation already states the altitude by naming the directory, so a
    flag would be a second source of truth for one fact (`derive != declare`).
    Asking the model to infer it is worse again: altitude decides the write
    boundary, and a wrong inference puts a component's findings in the pool
    that drives the whole product.
    """
    try:
        rel = research_dir.resolve().relative_to(repo_root.resolve())
    except ValueError:
        raise ValueError(
            f"research dir {research_dir} is not inside the repo {repo_root} — "
            f"altitude cannot be derived, and it decides the write boundary."
        ) from None
    return "PRODUCT" if rel == PRODUCT_POOL else "COMPONENT"


def upstream_block(research_dir: Path, repo_root: Path) -> str:
    """POINT a component run at the product pool. Deliberately not inlined.

    Without this a component run re-derives what the product pool already
    settled and produces a second answer that can drift from the first.

    A POINTER, not the content: inlining the synthesis cost 48k characters and
    tripled the prompt, and it is inconsistent with how the rest of this prompt
    works — the research standard, `topics.md` and the existing papers are all
    pointed at and read in Stage 1. Only COMPUTED values are inlined, because
    those are the ones a run cannot obtain by reading. The counts below are
    computed for exactly that reason: they make an unread pool visible.
    """
    if altitude(research_dir, repo_root) == "PRODUCT":
        return ""
    synthesis = repo_root / PRODUCT_POOL / "synthesis.md"
    if not synthesis.exists():
        return ("--- upstream product research ---\n"
                "The product pool has NO synthesis yet, so you have no upstream evidence. "
                "Do not invent any, and state the absence in your PR body.\n"
                "--- end upstream product research ---")
    papers = sorted((repo_root / PRODUCT_POOL / "raw").glob("*.md"))
    return "\n".join([
        "--- upstream product research (READ-ONLY) ---",
        f"The product pool holds **{len(papers)} papers** and a synthesis of them:",
        "",
        f"  {PRODUCT_POOL}/synthesis.md   <- READ THIS IN STAGE 1, BEFORE YOU SIZE",
        f"  {PRODUCT_POOL}/raw/           <- the pool behind it; open a paper only when a topic needs it",
        "",
        "Counted in code and authoritative: " + ", ".join(f"`{p.name}`" for p in papers),
        "",
        "**Cite it, never re-derive it, and never write to it.** A topic settled upstream",
        "does not need a second paper in your component pool — cite the upstream paper and",
        "move on. Your sizing in Stage 2 must state which topics upstream already covers.",
        "--- end upstream product research ---",
    ])


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

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
max_turns = shared.max_turns

_WORKFLOWS = Path(__file__).resolve().parents[3]

# Header contract from the Research Standard §3.
_LAST_VALIDATED = re.compile(r"^Last validated:\s*(\d{4}-\d{2}-\d{2})", re.M)
_REVALIDATE = re.compile(r"^Revalidate:\s*.*?(\d+)\s*(week|month)", re.M | re.I)
_RETIRED = re.compile(r"^Revalidate:\s*retired", re.M | re.I)


def in_worktree(research_dir: Path, repo_root: Path, worktree: Path) -> Path:
    """`research_dir` re-anchored to the worktree the run actually executes in.

    THE ANCHOR MISMATCH THIS EXISTS TO REMOVE. `run_research.py` builds the pool
    path as `repo_root / <arg>` — an absolute path into the MAIN CHECKOUT — and
    hands it to workflows that separately receive `worktree`. Everything computed
    from it (currency, altitude, upstream) therefore described the main checkout,
    while the prompt told the model to read the same relative path inside the
    worktree. One logical path, two filesystem locations, in one dispatch.

    Identical whenever the worktree is cut from the same ref and the main
    checkout is clean — which is why it survived, and why it is worth fixing:
    the failure is silent and the divergence is invisible in the output. Reported
    from the portfolio project after THREE consecutive passes flagged the same
    confusion; the cost was never a wrong figure, it was that no pass could tell
    which copy a figure came from.
    """
    if not research_dir.is_absolute():
        return worktree / research_dir
    try:
        return worktree / research_dir.relative_to(repo_root)
    except ValueError:
        return research_dir      # already outside the repo; leave it alone


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
        "",
        "**CURRENCY AND CONFORMANCE ARE DIFFERENT AXES AND THIS TABLE SETTLES ONLY THE"
        " FIRST.** `current` means *not yet stale*. It does NOT mean the paper conforms to"
        " §3 — a header can carry a parseable `Revalidate:` and still be non-conformant in"
        " every other respect, which is exactly how a run inherits a defect while quoting"
        " this table as its authority. Check conformance separately; never read `current`"
        " as clearance.",
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


def upstream_block(research_dir: Path, repo_root: Path, *,
                   read_directive: str = "READ THIS IN STAGE 1, BEFORE YOU SIZE",
                   coverage_directive: str = (
                       "Your sizing in Stage 2 must state which topics upstream "
                       "already covers.")) -> str:
    """POINT a component run at the product pool. Deliberately not inlined.

    Without this a component run re-derives what the product pool already
    settled and produces a second answer that can drift from the first.

    A POINTER, not the content: inlining the synthesis cost 48k characters and
    tripled the prompt, and it is inconsistent with how the rest of this prompt
    works — the research standard, `topics.md` and the existing papers are all
    pointed at and read in Stage 1. Only COMPUTED values are inlined, because
    those are the ones a run cannot obtain by reading. The counts below are
    computed for exactly that reason: they make an unread pool visible.

    THE TWO DIRECTIVES ARE CALLER-SUPPLIED BECAUSE THEY NAME THE CALLER'S OWN
    STAGES, and this block is now injected into two prompts with different ones.
    Both defaults are `research_write`'s original text verbatim, so the full
    cycle's prompt is byte-unchanged. `research_write_minor` has no sizing stage
    at all — it is a one-paper cycle — so hard-coding "your sizing in Stage 2"
    here sent it an instruction its prompt explicitly forbids obeying. That is a
    cross-file prose claim going stale the moment a second consumer appears,
    which is the failure class `candidates.md` C-065 names.
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
        f"  {PRODUCT_POOL}/synthesis.md   <- {read_directive}",
        f"  {PRODUCT_POOL}/raw/           <- the pool behind it; open a paper only when a topic needs it",
        "",
        "Counted in code and authoritative: " + ", ".join(f"`{p.name}`" for p in papers),
        "",
        "**Cite it, never re-derive it, and never write to it.** A topic settled upstream",
        "does not need a second paper in your component pool — cite the upstream paper and",
        f"move on. {coverage_directive}",
        "",
        "**MINE THIS POOL FOR ANSWERS, NOT ONLY FOR OVERLAP — they are different searches and",
        " the second one is the cheap one.** Asking *\"which of my question does upstream",
        " already cover?\"* only opens a paper whose TITLE resembles your question. Asking",
        " *\"has anyone here already solved the mechanism I need?\"* opens the ones that do not.",
        " **Papers about a COMPARABLE SYSTEM are the highest-yield and the least obviously",
        " relevant** — a nearest-neighbour assessment is where a shipped answer to your",
        " problem is most likely to be sitting under a title that mentions neither.",
        "",
        "**MEASURED, 2026-08-12, and it is why this paragraph exists.** A component run",
        " researched how a workflow hands state to its next child. The pool held a paper on",
        " the nearest comparable system that specified a typed per-step return contract, a",
        " content-addressed store, and offline hash-based re-verification — ranked Tier 1,",
        " costed S, and described in its own words as *\"the item with the shortest path from",
        " read about it to we are using it\"*. **The run never opened it**, because nothing in",
        " the title suggested overlap, and the fleet then spent a day bounding by hand the",
        " exact cost that paper had already solved mechanically.",
        "",
        f"  {PRODUCT_POOL.parent}/problem-statement.md   <- READ THIS TOO",
        "",
        "**It is the thesis every other document derives from, and it names the nearest",
        " comparable systems by name.** You are building a component of a project that",
        " exists for a reason; a paper written without that reason in view answers a",
        " well-posed question that nobody needed answered. **Read-only, always** — you never",
        " edit it and you never propose edits to it inside a paper.",
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


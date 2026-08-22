"""Shared I/O for the research family — promoted per §10.1 rule 3.

Two workflows use it (`research` and `research_refresh`), so consumer count
puts it here rather than in either workflow's folder.

NOT IDEMPOTENT (§7.1 / addendum §A1): these push commits and open PRs. Under
Temporal a retry is a NEW ATTEMPT, not a replay.
"""

from __future__ import annotations

import re
import secrets
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


_ID_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"
_ID_LEN = 8
_IDS_OFFERED = 3

# EVERY id in the file, whatever its shape. The corpus carries exactly one shape
# today, but a reader keyed to `\d{8}` would stop seeing the legacy `C-\d{3}`
# rows the moment one survived a migration — and an allocator that cannot SEE an
# id cannot avoid it. Match the separator and the run, not the alphabet.
_ANY_ID = re.compile(r"^\|\s*(C-[0-9a-z]+)\s*\|", re.M)


def candidate_ceiling(research_dir: Path) -> str:
    """Fresh candidate ids, MINTED HERE and handed to the run ready to use.

    THERE IS NO CEILING ANY MORE, and the name is kept only because two
    workflows render it into `CANDIDATE_CEILING`. What it used to compute was
    `max + 1`, read from the branch's own snapshot of `candidates.md` — and
    that is the whole defect. Two branches read the same snapshot, both take the
    same "next free" id, and git merges two rows added at different positions
    with NO conflict. Nothing is red; the file simply now holds one address
    naming two proposals. Measured on this file: nine renumbering events across
    seven rows, then six more collisions, three of them on a single PR.

    A RANDOM id needs no coordination, which is the entire point: there is no
    "next" to race for. At 36**8 the space is ~2.8e12, so at the thousands this
    file will ever hold the chance of any collision is under one in a million —
    and `test_candidate_ids_are_unique.py` still catches the case that does not
    happen, because a guard that only fires on the impossible is cheap.

    OFFERED IN A BATCH, AND UNUSED ONES ARE SIMPLY DISCARDED. That is only
    possible because they are random: a skipped sequential id is a permanent hole
    someone later has to explain in prose, which is exactly the prose this file
    used to carry. Here, an id nobody writes down never existed.
    """
    f = research_dir / "candidates.md"
    taken = set(_ANY_ID.findall(f.read_text())) if f.exists() else set()

    fresh: list[str] = []
    while len(fresh) < _IDS_OFFERED:
        new = "C-" + "".join(secrets.choice(_ID_ALPHABET) for _ in range(_ID_LEN))
        if new not in taken and new not in fresh:
            fresh.append(new)

    offer = ", ".join(f"`{i}`" for i in fresh)
    if not f.exists():
        return (f"`candidates.md` does NOT exist yet — create it. "
                f"Use these ids, in order, for the candidates you file: {offer}.")
    return (f"`candidates.md` holds **{len(taken)} rows**. "
            f"**Ids are RANDOM, never sequential — do not compute one.** Use these, "
            f"in order, for the candidates you file: {offer}. Unused ids are discarded, "
            f"so take only what you need. "
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


COMPONENT_ROOT = Path("docs/development")


def component_pools_block(research_dir: Path, repo_root: Path) -> str:
    """POINT a product run at the component pools. The mirror of `upstream_block`.

    THE GAP THIS CLOSES. `upstream_block` sends a component run up to the
    product pool and returns "" at product altitude — so the traffic was
    one-way. A full cycle re-derives what a feature investigation already
    settled, and worse, can publish a product-level finding that contradicts a
    component paper nobody told it about. The component pools are where the
    concrete, already-paid-for evidence lives.

    A POINTER, not the content, for the same reason `upstream_block` is one:
    inlining a pool tripled a prompt once and the papers are readable in place.
    The counts are computed because an unread pool is otherwise invisible.

    Empty pools are listed WITH their zero. A component with a research
    directory and no papers is a real signal — it says the topic was scoped and
    never investigated — and silently dropping those rows would let a product
    run believe the feature had been researched.
    """
    if altitude(research_dir, repo_root) != "PRODUCT":
        return ""
    root = repo_root / COMPONENT_ROOT
    if not root.is_dir():
        return ""
    pools = sorted(p for p in root.glob("*/research") if p.is_dir())
    if not pools:
        return ""
    rows, total = [], 0
    for pool in pools:
        papers = sorted((pool / "raw").glob("*.md"))
        total += len(papers)
        names = ", ".join(f"`{x.name}`" for x in papers) if papers else "— none yet"
        rows.append(f"  {pool.relative_to(repo_root)}  ({len(papers)}): {names}")
    return "\n".join([
        "--- component research pools (READ-ONLY) ---",
        f"**{len(pools)} feature pools hold {total} papers between them.** Counted in code:",
        "",
        *rows,
        "",
        "**MINE THESE, AND RESPECT THEM — two separate obligations.**",
        "",
        "**MINE:** a feature investigation is concrete, already paid for, and usually closer to",
        "a working mechanism than anything you will find in the field. Ask *\"has this fleet",
        "already established the thing I am about to research?\"* before you search outward. A",
        "pool whose NAME does not resemble your question is exactly where an unnoticed answer",
        "sits — the same miss that cost a full day on 2026-08-12, in the other direction.",
        "",
        "**RESPECT:** these papers were verified by the same critic gate you are subject to.",
        "If your product-level finding CONTRADICTS a component paper, that is a real result and",
        "you state it explicitly — naming the paper, the claim, and why the wider evidence",
        "overturns it. What you must NOT do is publish the contradiction silently, leaving two",
        "verified papers disagreeing with nothing recording which one the project believes.",
        "",
        "**Never write to a component pool.** A product run that edits a feature's research is",
        "reaching into a scope it does not own; surface the implication and let planning route it.",
        "--- end component research pools ---",
    ])


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
    which is the failure class `candidates.md` C-zwzepum0 names.
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


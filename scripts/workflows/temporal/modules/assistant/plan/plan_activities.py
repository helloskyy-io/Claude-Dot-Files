"""Shared I/O for the planning family — promoted per §10.1 rule 3.

Sits at module level because more than one workflow uses it: `plan_sprint` and
`plan_revision` today, `plan_tech_stack` when it lands. The promotion rule was
anticipatory when this file was written and is now satisfied outright.

The triage helpers below (`candidate_counts`, `direction_ceiling`,
`existing_work`) remain single-consumer — `plan_sprint` only. They are here
because this file is the family's shared surface, not because a second caller
exists; if one never appears they belong back inside plan_sprint/.

NOT IDEMPOTENT (§7.1): these push commits and open PRs. Under Temporal a retry
is a NEW ATTEMPT, not a replay.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .. import assistant_activities as shared

load_prompt = shared.load_prompt
shared_prompt = shared.shared_prompt
render = shared.render
run_claude = shared.run_claude
worktree_add = shared.worktree_add
pr_branch = shared.pr_branch
extract_pr_url = shared.extract_pr_url
observe_outcome = shared.observe_outcome
max_turns = shared.max_turns

# A candidate row: | C-001 | title | source | `decision` | `status` | note |
_ROW = re.compile(r"^\|\s*(C-\d{3})\s*\|.*?\|.*?\|\s*(.*?)\s*\|\s*(.*?)\s*\|", re.M)

# A direction row: | D-001 | recommendation | why | source | `status` |
_DIRECTION_ID = re.compile(r"^\|\s*`?D-(\d{3})`?\s*\|", re.M)

_BLANK = ("", "—", "-")

# Strips the leading marker so a section name is just its name.
_SECTION_NAME = re.compile(r"^## Sprint:\s*")


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
    untriaged = [i for i, dec, _st in rows if dec.strip().strip("`") in _BLANK]
    return {
        "total": len(rows),
        "untriaged": len(untriaged),
        "triaged": len(rows) - len(untriaged),
        "untriaged_ids": untriaged,
    }


def direction_ceiling(research_dir: Path) -> str:
    """The next free D-NNN, computed in code and handed over.

    Same discipline as `candidate_ceiling` in the research family: a run that
    guesses the next ID collides with an existing row or skips a block, and
    either way the file's promise that an ID is stable breaks silently.
    """
    f = research_dir / "direction.md"
    if not f.exists():
        return ("`direction.md` does NOT exist yet — create it with the header row "
                "and start at `D-001`.")
    ids = sorted(_DIRECTION_ID.findall(f.read_text()))
    if not ids:
        return "`direction.md` exists but holds no rows — start at `D-001`."
    return (f"`direction.md` holds **{len(ids)} rows**, highest ID **D-{ids[-1]}**. "
            f"A NEW recommendation starts at **D-{int(ids[-1]) + 1:03d}**. "
            f"Never renumber an existing row.")


def existing_work(repo_root: Path, research_dir: Path) -> str:
    """Enumerate what a candidate might ALREADY have a home in.

    Deliberately NOT included: `cpi-decisions.md`. It is the tooling-improvement
    loop and the home for deferrals carrying watch-criteria — a different concern
    from product trajectory. Feeding it to a triage pass invites the run to
    re-decide things outside its remit.

    Computed in code and handed over, rather than asked of the model: a triage
    that ships a candidate already tracked as an open issue creates two homes for
    one item, which is the duplication the candidates file exists to prevent.
    """
    import subprocess

    lines: list[str] = []

    comps = sorted(d for d in (repo_root / "docs" / "development").iterdir()
                   if d.is_dir() and d.name != "reviews")
    lines.append("**Existing components** (a candidate may belong inside one rather than needing its own sprint section):")
    for c in comps:
        syn = c / "research" / "synthesis.md"
        mark = " — **HAS COMPONENT RESEARCH**: `" + str(syn.relative_to(repo_root)) + "`" if syn.exists() else ""
        lines.append(f"  - `docs/development/{c.name}/`{mark}")

    withres = [c for c in comps if (c / "research" / "synthesis.md").exists()]
    if withres:
        lines.append(
            f"\n**{len(withres)} component(s) carry their own research synthesis, listed above and counted in code.** "
            f"Each one is evidence about a sprint section that ALREADY EXISTS, and it is almost always NEWER than the "
            f"section it backs — research is commissioned after a sprint item is written, so the section states what "
            f"was believed BEFORE the evidence arrived. **Read every one of them in Stage 1** and reconcile its "
            f"sprint section against it in Stage 4. A synthesis nobody reads back into the plan is a paper we paid "
            f"for and did not use."
        )

    papers = sorted(p.name for p in (research_dir / "raw").glob("*.md"))
    lines.append(f"\n**Research pool** — {len(papers)} papers. A significant finding with no home in the "
                 f"sprint plan is a Stage 4 coherence finding:")
    lines += [f"  - `{n}`" for n in papers]

    r = subprocess.run(["gh", "issue", "list", "--state", "open", "--limit", "50",
                        "--json", "number,title"], cwd=str(repo_root),
                       capture_output=True, text=True)
    if r.returncode == 0:
        import json
        issues = json.loads(r.stdout)
        lines.append(f"\n**Open issues** — {len(issues)}. **A candidate matching one of these is ALREADY tracked**; "
                     f"say so and do not create a second home for it:")
        lines += [f"  - #{i['number']} {i['title']}" for i in issues]
    else:
        lines.append("\n**Open issues: COULD NOT BE READ.** Do not assume there are none — "
                     "say in your report that this check did not run.")

    return "\n".join(lines)


def new_sprint_sections(worktree: Path, sprint_rel: str, base_ref: str = "origin/main") -> list[str]:
    """Sprint sections this branch ADDED — read from the diff, in code.

    A NON-MODEL OBSERVABLE. The parent must know which components are new so it
    can research and plan only those, and asking the triage child to report them
    would make the parent trust an account rather than read the artifact. `git`
    already knows, and a diff is not something a model can be wrong about.

    Matched on the added-heading form specifically: a section merely EDITED
    shows as a changed body with no added `## Sprint:` line, and researching an
    existing component because its prose moved would spend a full cycle on
    nothing.
    """
    out = subprocess.run(
        ["git", "diff", f"{base_ref}...HEAD", "--", sprint_rel],
        cwd=str(worktree), capture_output=True, text=True,
    )
    if out.returncode != 0:
        raise RuntimeError(
            f"could not diff {sprint_rel} against {base_ref} in {worktree}: "
            f"{out.stderr.strip()}. The parent cannot tell which components are "
            f"new, and guessing would research the wrong ones."
        )
    return [
        _SECTION_NAME.sub("", line[1:]).split("—")[0].strip()
        for line in out.stdout.splitlines()
        if line.startswith("+## Sprint:")
    ]


def component_dir(repo_root: Path, section_name: str) -> Path:
    """`Fleet Reliability` -> `docs/development/fleet-reliability`.

    The convention the whole tree already follows, applied in code rather than
    asked of a model — a component whose folder name does not match its sprint
    section is invisible to every reconciliation that walks one against the other.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", section_name.lower()).strip("-")
    if not slug:
        raise ValueError(f"sprint section {section_name!r} yields no folder name")
    return repo_root / "docs" / "development" / slug


PROBLEM_STATEMENT = Path("docs/standards/architecture/problem-statement.md")
PRODUCT_POOL = Path("docs/standards/architecture/research")
COMPONENT_ROOT = Path("docs/development")


def evidence_block(repo_root: Path) -> str:
    """POINT a planning run at the thesis and the pools, PRIMARY first.

    THE GAP THIS CLOSES. `plan_revision` consumes research only when the
    dispatch brief happens to hand it over — its prompt's research checks are
    both conditional ("if your inputs include research artifacts"). So a plan
    designed against evidence the fleet already paid for depended on whoever
    wrote the brief remembering to name it. `plan_sprint` reads the problem
    statement; `plan_revision` had no pointer to anything.

    That is the same failure that cost a full research cycle on 2026-08-12, one
    layer up: a brief named four files, the run read exactly those four, and the
    paper that already answered the question sat unopened in the pool.

    ORDERED, NOT DUMPED. `plan_revision` is the GENERIC planning child — unlike
    its siblings it is told no file structure and infers its target from a
    free-text description. A flat list of every pool makes the run guess which
    one is its own, so the block teaches the convention instead: a feature's own
    pool is the PRIMARY evidence, and the project pool is there for how it all
    fits together. Product-first ordering had the emphasis exactly backwards.

    A POINTER, never the content. Counts are computed because an unread pool is
    otherwise invisible, and empty pools are listed WITH their zero — a pool with
    no papers says the topic was scoped and never investigated, which a planner
    needs to know before assuming coverage.
    """
    def _pool(pool: Path) -> tuple[Path, int, str]:
        papers = sorted((pool / "raw").glob("*.md"))
        syn = "synthesis.md" if (pool / "synthesis.md").is_file() else "NO synthesis"
        return pool.relative_to(repo_root), len(papers), syn

    features = [_pool(d) for d in sorted((repo_root / COMPONENT_ROOT).glob("*/research")) if d.is_dir()]
    product = _pool(repo_root / PRODUCT_POOL) if (repo_root / PRODUCT_POOL).is_dir() else None
    has_thesis = (repo_root / PROBLEM_STATEMENT).is_file()
    if not (features or product or has_thesis):
        return ""

    lines = ["--- evidence available to this plan (READ-ONLY, you never write to any of it) ---", ""]
    lines += [
        "**THE CONVENTION, because this workflow is told no file structure and must not guess it:**",
        "every feature under `docs/development/<feature>/` may hold its own `research/` pool —",
        "`raw/` for the papers and `synthesis.md` rolled up. **The pool belonging to the feature you",
        "are planning is your PRIMARY evidence**, and a synthesis is written to be consumed by",
        "exactly this step.",
        "",
    ]
    if features:
        lines.append("**FEATURE POOLS — start here. Counted in code:**")
        lines.append("")
        lines += [f"  {rel}  ({n} papers, {syn})" for rel, n, syn in features]
        lines += [
            "",
            "**A plan that re-derives what its own pool already settled has spent a research cycle",
            "twice, and may reach a different answer the second time.** Cite the paper you relied on.",
            "**Say plainly when the relevant pool is EMPTY rather than assuming the topic was",
            "covered** — a zero above means the topic was scoped and never investigated.",
            "",
        ]
    if product:
        rel, n, syn = product
        lines += [
            "**PROJECT POOL — secondary, for how it all fits together:**",
            "",
            f"  {rel}  ({n} papers, {syn})",
            "",
            "Reach for it when your feature has to cohere with the whole — a cross-cutting decision,",
            "a shared substrate, or a comparable system. **The pool whose name least resembles your",
            "task is the one most likely to hold an already-solved mechanism**; that miss is",
            "documented and it cost a full day.",
            "",
        ]
    if has_thesis:
        lines += [
            f"  {PROBLEM_STATEMENT}   <- the thesis this plan must serve.",
            "",
            "**Read it for WHY this component exists.** A plan that does not serve the thesis is a",
            "well-formed plan for something nobody needed. **READ-ONLY — never edited, and never",
            "proposed for edit from inside a plan.**",
        ]
    return "\n".join([*lines, "--- end evidence available to this plan ---"])


def submit_prompt(pr_number: str | None, label: str) -> str:
    if pr_number:
        return (f"- Stage and commit your changes with message `{label}`\n"
                f"- Push to the PR branch and report PR #{pr_number}'s URL as your FINAL line")
    return (f"- Stage and commit your changes with message `{label}`\n"
            f"- Push the branch and open a PR; report its URL as your FINAL line")

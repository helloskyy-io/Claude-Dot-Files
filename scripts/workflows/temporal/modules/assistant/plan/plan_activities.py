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
v1_constant = shared.v1_constant

# A candidate row: | C-001 | title | source | `decision` | `status` | note |
_ROW = re.compile(r"^\|\s*(C-\d{3})\s*\|.*?\|.*?\|\s*(.*?)\s*\|\s*(.*?)\s*\|", re.M)

# A direction row: | D-001 | recommendation | why | source | `status` |
_DIRECTION_ID = re.compile(r"^\|\s*`?D-(\d{3})`?\s*\|", re.M)

_BLANK = ("", "—", "-")


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

    Deliberately NOT included: `cpi-decisions.md` and `loose_ends.md`. The first
    is the tooling-improvement loop, a different concern from product trajectory;
    the second is thematic deferrals, not a work queue. Feeding either to a
    triage pass invites it to re-decide things outside its remit.

    Computed in code and handed over, rather than asked of the model: a triage
    that ships a candidate already tracked as an open issue creates two homes for
    one item, which is the duplication the candidates file exists to prevent.
    """
    import subprocess

    lines: list[str] = []

    comps = sorted(d.name for d in (repo_root / "docs" / "development").iterdir()
                   if d.is_dir() and d.name != "reviews")
    lines.append("**Existing components** (a candidate may belong inside one rather than needing its own sprint section):")
    lines += [f"  - `docs/development/{c}/`" for c in comps]

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


def submit_prompt(pr_number: str | None, label: str) -> str:
    if pr_number:
        return (f"- Stage and commit your changes with message `{label}`\n"
                f"- Push to the PR branch and report PR #{pr_number}'s URL as your FINAL line")
    return (f"- Stage and commit your changes with message `{label}`\n"
            f"- Push the branch and open a PR; report its URL as your FINAL line")

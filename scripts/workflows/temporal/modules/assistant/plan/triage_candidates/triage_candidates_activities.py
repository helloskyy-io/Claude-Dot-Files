"""triage-candidates' own I/O — one consumer each, so §10.1 rule 3 puts them here.

`direction_ceiling` sat on the planning family's shared surface while its single
caller was `plan_sprint`; the split moved the caller, not the count.
[`workflow-scripts.md` § Location](../../../../../../docs/standards/workflow-scripts.md)
restates §10.1 rule 3 as BINDING and mechanical — *"consumer count decides, never
taste"* — and rule 6 gives a one-file workflow folder its place to grow a helper
it has earned.

`sprint_files_touched` is new and is the answer to an asymmetry: the split built
a real mechanism for one boundary and left the mirror-image one on prose. See its
docstring.

NOT IDEMPOTENT (§7.1) is not in play here — this module only reads.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

# A direction row: | D-001 | recommendation | why | source | `status` |
_DIRECTION_ID = re.compile(r"^\|\s*`?D-(\d{3})`?\s*\|", re.M)

# Any path whose file IS a sprint plan, wherever a repo keeps it. Matched on the
# NAME rather than a configured path deliberately: this workflow is not given a
# sprint path (see `test_triage_is_given_no_sprint_authority`), and a guard that
# needed one would reintroduce the parameter the boundary is defined by.
_SPRINT_FILE = re.compile(r"(^|/)sprints?\.md$")


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


def sprint_files_touched(worktree: Path, base_ref: str = "origin/main") -> list[str]:
    """Sprint files this run changed — the boundary observed, not merely stated.

    THE SPLIT BUILT A MECHANISM FOR ONE BOUNDARY AND LEFT ITS MIRROR ON PROSE.
    `plan_sprint` re-reads the `decision` column after its run because *"an
    authority transfer stated only in prose is a convention a model can reason
    past"*. That argument does not stop at one column: `sprint.md` is the
    operator's own cross-domain sequencing surface, this workflow holds no
    override for it, and its prompt hands the model the exact trigger — *"if a
    candidate you ship looks like it needs a sprint section, say so"* — one step
    away from writing the section instead of saying so. Not taking a
    `sprint_path` parameter constrains the SIGNATURE; the run has the whole
    worktree either way.

    Both halves of the tree are read. A committed edit shows in the diff against
    `base_ref`; an uncommitted one shows in the status. Either is an edit that
    happened, and the run must not report success over it.

    RAISES rather than returning empty when git cannot answer, mirroring
    `new_sprint_sections`: a guard that cannot observe must not be read as
    having observed nothing.
    """
    seen: list[str] = []
    for argv in (["git", "diff", "--name-only", f"{base_ref}...HEAD"],
                 ["git", "status", "--porcelain"]):
        out = subprocess.run(argv, cwd=str(worktree), capture_output=True, text=True)
        if out.returncode != 0:
            raise RuntimeError(
                f"could not read the worktree state in {worktree} via "
                f"`{' '.join(argv)}`: {out.stderr.strip()}. This run cannot show it "
                f"left the sprint plan alone, and an unobservable boundary is not a "
                f"kept one."
            )
        for line in out.stdout.splitlines():
            # `git status --porcelain` prefixes a two-column state; a rename
            # reads `R  old -> new`, and the destination is the edited path.
            path = line[3:] if argv[1] == "status" else line
            path = path.split(" -> ")[-1].strip().strip('"')
            if path and _SPRINT_FILE.search(path) and path not in seen:
                seen.append(path)
    return seen

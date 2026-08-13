"""plan-project's own I/O — one consumer each, so §10.1 rule 3 puts them here.

Both functions read the tree so the PARENT can decide which components are new
and where their research pool belongs. Nothing else in the family calls either,
and [`workflow-scripts.md` § Location](../../../../../../docs/standards/workflow-scripts.md)
restates §10.1 rule 3 as BINDING and mechanical — *"consumer count decides,
never taste"*. Rule 6 gives a one-file workflow folder its place to grow the
helper it has earned.

THEY SAT ON THE FAMILY'S SHARED SURFACE UNTIL THE SPLIT AUDIT WAS FINISHED
PROPERLY. `plan_activities`'s docstring listed five functions it had checked
against rule 3 and moved two of them out; these two were single-consumer the
whole time and were simply not in the list, so a file whose stated invariant is
*"shared by definition"* held two functions that were not. Counted this time
rather than eyeballed.

NOT IDEMPOTENT (§7.1) is not in play here — this module only reads.
"""

from __future__ import annotations

import re
from pathlib import Path

from .. import plan_activities as act

# Strips the leading marker so a section name is just its name.
_SECTION_NAME = re.compile(r"^## Sprint:\s*")


def new_sprint_sections(worktree: Path, sprint_rel: str, *, base_ref: str) -> list[str]:
    """Sprint sections THIS DISPATCH added — read from the diff, in code.

    A NON-MODEL OBSERVABLE. The parent must know which components are new so it
    can research and plan only those, and asking the triage child to report them
    would make the parent trust an account rather than read the artifact. `git`
    already knows, and a diff is not something a model can be wrong about.

    `base_ref` IS REQUIRED AND HAS NO DEFAULT, deliberately. It defaulted to
    `origin/main`, which answers a different question — *what has this BRANCH
    accumulated* rather than *what has THIS RUN added* — and the two diverge on
    exactly the path the entrypoints document: a `--pr` redispatch cuts its
    worktree from a branch that already carries a `## Sprint:` heading an
    earlier pass added and researched, so the section reads as new again and
    buys a second full research cycle for it. `plan_activities.py`'s snapshot
    comparators state the same rule for the same reason — *snapshot around the
    run, never diff against the base* — and a caller cannot inherit the wrong
    base by saying nothing.

    Matched on the added-heading form specifically: a section merely EDITED
    shows as a changed body with no added `## Sprint:` line, and researching an
    existing component because its prose moved would spend a full cycle on
    nothing.
    """
    out = act.git_output(
        worktree, ["git", "diff", f"{base_ref}...HEAD", "--", sprint_rel],
        "The parent cannot tell which components are new, and guessing would "
        "research the wrong ones.",
    )
    return [
        _SECTION_NAME.sub("", line[1:]).split("—")[0].strip()
        for line in out.splitlines()
        if line.startswith("+## Sprint:")
    ]


def component_dir(tree: Path, section_name: str) -> Path:
    """`Fleet Reliability` -> `docs/development/fleet-reliability`.

    The convention the whole tree already follows, applied in code rather than
    asked of a model — a component whose folder name does not match its sprint
    section is invisible to every reconciliation that walks one against the other.

    `tree`, not `repo_root`: the only caller passes its WORKTREE, because the
    research pool this returns is written on the branch. The parameter was named
    `repo_root` and the call was correct anyway, which is the combination that
    survives review and breaks on the second caller.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", section_name.lower()).strip("-")
    if not slug:
        raise ValueError(f"sprint section {section_name!r} yields no folder name")
    return tree / "docs" / "development" / slug

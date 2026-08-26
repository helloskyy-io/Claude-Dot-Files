"""triage-candidates' own I/O — one consumer each, so §10.1 rule 3 puts them here.

[`workflow-scripts.md` § Location](../../../../../../../docs/standards/workflow-scripts.md)
restates §10.1 rule 3 as BINDING and mechanical — *"consumer count decides, never
taste"* — and rule 6 gives a one-file workflow folder its place to grow a helper
it has earned.

`direction.md` IS GONE, 2026-08-26, AND SO ARE ITS THREE READERS. It was a
second queue holding the `requires review` disposition, and the operator's
account of it is the one that settles it: a temporary file opened so a machine
could be rebooted, which then persisted. Every row it held pointed at a source
candidate that still exists carrying `decision: requires review, status: open`
— which IS the "a human owes a ruling" signal, in a store that already has a
triage cadence. The second surface added a `D-` id and nothing else, so nothing
was migrated when it was deleted.

**A `requires review` candidate is now simply a candidate carrying that
decision.** No row to append, no `D-` series, no second `status` column whose
writer had to be argued about.

THE SPRINT GUARD IS NOT HERE ANY MORE and that is a promotion, not a deletion.
`sprint_files_touched` was a single-purpose observer of one forbidden path;
`plan_activities.worktree_state` / `boundary_crossings` observe the whole
declared boundary for both workflows, so the mechanism has two consumers and
lives on the shared surface. Its argument survives unchanged in
`triage_candidates_workflow.FORBIDDEN_PATHS`: not taking a `sprint_path`
parameter constrains the SIGNATURE, and the run holds the whole worktree either
way.

NOT IDEMPOTENT (§7.1) is not in play here — this module only reads.
"""

from __future__ import annotations

import re
from pathlib import Path

from .. import plan_activities as act

# The operator's inbox, inside whatever `--research` names. Named rather than
def sized_without_shipping(candidates_path: Path) -> list[str]:
    """Ids carrying a `size` on a row this run did not rule `ship`.

    THE TWO CELLS ARE READ FROM ONE ROW, which is the whole point. Checking each
    column alone would pass a table where every row is sized and none is shipped —
    both columns individually legal, the pairing nonsense. The prompt asks two
    questions IN ORDER, and a run that answers the second for a row that failed
    the first has stopped reading its own first answer.

    Blank is always legal: a `ship` awaiting a size is UNSIZED, which
    `plan-candidates` skips deliberately rather than guessing at.
    """
    return sorted(row.id for row in act.candidate_rows(
        candidates_path,
        missing_hint="Without it there are no rows to check size against decision.")
        if row.size and row.decision != "ship")

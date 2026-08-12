"""plan-sprint's own I/O — one consumer, so §10.1 rule 3 puts it here.

`candidate_decisions` sat on the planning family's shared surface while it had a
single caller. [`workflow-scripts.md` § Location](../../../../../../docs/standards/workflow-scripts.md)
restates §10.1 rule 3 as BINDING and states the test mechanically: a helper moves
out of a workflow folder *"if and only if more than one workflow uses it.
Consumer count decides, never taste."* One consumer, so it lives with its
consumer — and rule 6 is explicit that a one-file workflow folder growing its own
helper is the correct outcome rather than a defect.

The row parsing itself stays in `plan_activities`: it IS shared, and one
definition of what a cell means is what this file's own guard depends on.

NOT IDEMPOTENT (§7.1) is not in play here — this module only reads.
"""

from __future__ import annotations

from pathlib import Path

from .. import plan_activities as act


def candidate_decisions(candidates_path: Path) -> dict[str, str]:
    """Every row's `decision`, normalised, keyed by id — the transferred column.

    THIS IS THE AUTHORITY TRANSFER, ENFORCED RATHER THAN ASSERTED. `decision` was
    `plan-sprint`'s output until triage became its own workflow; it is now
    `triage-candidates`'s alone. Prose in nine documents says so, and prose is
    not a mechanism: `plan_sprint` still READS this file, still has write access
    to it in its worktree, and a model that has just decided a candidate is too
    small for a sprint section is one plausible step from recording that
    conclusion in the column next to it.

    So `plan_sprint` snapshots this before its run and compares after. Same
    discipline as `candidate_counts`: OBSERVE what the run wrote, never ask it
    what it wrote.

    Normalised via `plan_activities.normalise_cell` — backticks and the several
    spellings of empty all collapse — so a row reformatted from `` `ship` `` to
    `ship` does not read as a ruling changed. The comparison must fire on
    MEANING, not on markup, and it must fire on the SAME meaning the counter
    sees: two hand-written normalisations had already drifted apart once.
    """
    return {cid: dec for cid, dec, _st in act.candidate_rows(
        candidates_path,
        missing_hint="Without it there is no `decision` column to hold anything to.")}

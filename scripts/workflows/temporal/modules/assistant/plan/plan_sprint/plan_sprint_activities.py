"""plan-sprint's own I/O — one consumer each, so §10.1 rule 3 puts them here.

`candidate_decisions` sat on the planning family's shared surface while it had a
single caller. [`workflow-scripts.md` § Location](../../../../../../docs/standards/workflow-scripts.md)
restates §10.1 rule 3 as BINDING and states the test mechanically: a helper moves
out of a workflow folder *"if and only if more than one workflow uses it.
Consumer count decides, never taste."* One consumer, so it lives with its
consumer — and rule 6 is explicit that a one-file workflow folder growing its own
helper is the correct outcome rather than a defect.

`checked_boxes` is here for the same reason and it is genuinely single-consumer,
not merely single-consumer-today. `triage-candidates` carries the identical
prohibition, but it cannot reach a checkbox: every checkbox-bearing file in this
tree is a sprint plan or a phase doc, and its path boundary forbids both
outright. Promoting this to the shared surface would give it a phantom second
consumer — a mechanism registered against a prohibition it can never fire for,
which is the same unobserved-row defect the registry exists to catch, built into
the thing meant to close it.

The row parsing itself stays in `plan_activities`: it IS shared, and one
definition of what a cell means is what this file's own guard depends on.

NOT IDEMPOTENT (§7.1) is not in play here — this module only reads.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .. import plan_activities as act

# A completed checkbox in any of the markdown dialects this tree writes.
_CHECKED = re.compile(r"^\s*[-*]\s*\[[xX]\]\s*(.+?)\s*$", re.M)


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


def checked_boxes(sprint_path: Path) -> Counter:
    """The completed checkboxes in the sprint plan, counted by their text.

    A CHECKBOX MEANS *SHIPPED AND VALIDATED*, and this workflow has validated
    nothing — it places work that was decided elsewhere and will be built later
    still. The prohibition is stated in the prompt and in the Documentation
    Standard's *"built is not proven"* rule, and until now it was stated ONLY
    there. A run that ticks a box it merely planned makes the plan report work
    that does not exist, in the one file the operator reads to know what is done.

    COUNTED BY TEXT rather than diffed by line number, because this workflow is
    legitimately allowed to re-order sections: a positional comparison would fire
    on a box that simply moved. Adding an UNCHECKED milestone is legitimate and
    invisible here; adding a checked one is not, and shows up as a new entry.
    A Counter rather than a set so that ticking the second of two identically
    worded milestones is still seen.

    A missing file is an empty Counter on both sides. This workflow does not
    create the sprint plan, so the case only arises in a tree that never had one,
    and it is not this guard's business to complain about that.
    """
    if not sprint_path.exists():
        return Counter()
    return Counter(_CHECKED.findall(sprint_path.read_text()))

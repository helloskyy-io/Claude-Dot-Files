"""plan-sprint's own I/O — one consumer, so §10.1 rule 3 puts it here.

`candidate_decisions` LIVED HERE AND HAS GONE BACK to `plan_activities`, which is
rule 3 working in the direction people forget it has. It moved down here when the
triage split left it with a single caller; `plan_candidates` may not set
`decision` either, so it acquired a genuine second consumer and moved back up
with the comparator built on it. [`workflow-scripts.md` § Location](../../../../../../docs/standards/workflow-scripts.md)
restates §10.1 rule 3 as BINDING and states the test mechanically: a helper moves
out of a workflow folder *"if and only if more than one workflow uses it.
Consumer count decides, never taste."* That is a count, not a ratchet.

`checked_boxes` stays, and it is genuinely single-consumer rather than merely
single-consumer-today. `triage-candidates` and `plan-candidates` carry the
identical prohibition, but neither can reach a checkbox: every checkbox-bearing
file in this tree is a sprint plan or a phase doc, and both path boundaries
forbid both outright. Promoting this to the shared surface would give it a
phantom second consumer — a mechanism registered against a prohibition it can
never fire for, which is the same unobserved-row defect the registry exists to
catch, built into the thing meant to close it.

The row parsing itself stays in `plan_activities`: it IS shared, and one
definition of what a cell means is what this file's own guard depends on.

NOT IDEMPOTENT (§7.1) is not in play here — this module only reads.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

# A completed checkbox in any of the markdown dialects this tree writes.
_CHECKED = re.compile(r"^\s*[-*]\s*\[[xX]\]\s*(.+?)\s*$", re.M)


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

    A missing file is an empty Counter, and that reading is deliberate and must
    not change: it is what lets a tree with no plan yet run at all. THIS IS
    THEREFORE NOT AN EXISTENCE CHECK, and reading it as one is how the sprint
    plan came to be deletable — an empty Counter after a deleted file compares
    identically to an empty Counter after an untouched empty one.
    `plan_activities.grants_that_vanished` is the existence check, and it runs
    ahead of this one for exactly that reason.

    The COMPARISON is symmetric even though this reader is not: the caller takes
    the difference in both directions, because "flip a checkbox" is a
    prohibition on erasing a tick as much as on adding one.
    """
    if not sprint_path.exists():
        return Counter()
    return Counter(_CHECKED.findall(sprint_path.read_text()))

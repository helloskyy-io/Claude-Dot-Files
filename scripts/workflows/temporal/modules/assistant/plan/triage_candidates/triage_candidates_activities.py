"""triage-candidates' own I/O — one consumer each, so §10.1 rule 3 puts them here.

`direction_ceiling` sat on the planning family's shared surface while its single
caller was `plan_sprint`; the split moved the caller, not the count.
[`workflow-scripts.md` § Location](../../../../../../../docs/standards/workflow-scripts.md)
restates §10.1 rule 3 as BINDING and mechanical — *"consumer count decides, never
taste"* — and rule 6 gives a one-file workflow folder its place to grow a helper
it has earned.

`direction_statuses` is the reader the operator's own column needed and did not
have. `direction.md` is `triage-candidates`'s to APPEND to and nobody's to RULE
on: `applied` and `rejected` are the operator's, and
[`standards-governance.md`](../../../../../../../config/rules/standards-governance.md)
calls that flag *"the ruling this rule exists to protect"*. The split built a
before/after comparison for `candidates.md`'s `status` and left the
higher-stakes column next door on prose — while both prompts told the model it
was enforced. Both read through `plan_activities.normalise_cell`, so markup is
not meaning on either file.

Both build on `direction_rows`, for the reason `candidate_rows` exists on the
shared surface: two hand-written parses of one table drift, and this family has
already paid for that once (see `normalise_cell`).

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
# spelled inline because THREE consumers test for it — the two readers below and
# the workflow's write grant — and the grant drifting from the readers is how a
# run is authorised to write one file and reads another.
DIRECTION = "direction.md"

# A direction row: | D-001 | recommendation | why | source | `status` |
_ROW = re.compile(r"^\|\s*`?(D-\d{3})`?\s*\|.*?\|.*?\|.*?\|\s*(.*?)\s*\|", re.M)


def direction_rows(research_dir: Path) -> list[tuple[str, str]]:
    """Every `(D-NNN, status)` in `direction.md`, normalised. One parse, one place.

    A MISSING FILE IS AN EMPTY LIST, NOT AN ERROR, and both callers need that
    reading. `direction_ceiling` is asked what the next free id is on a repo that
    has never filed a direction row, and the status guard must let a run CREATE
    the file — a run that appends the first `D-001` must not fail for having
    created the thing it was told to create. Empty on both sides of the snapshot
    is the same answer as unchanged.
    """
    f = research_dir / DIRECTION
    if not f.exists():
        return []
    return [(did, act.normalise_cell(st)) for did, st in _ROW.findall(f.read_text())]


def direction_ceiling(research_dir: Path) -> str:
    """The next free D-NNN, computed in code and handed over.

    Same discipline as `candidate_ceiling` in the research family: a run that
    guesses the next ID collides with an existing row or skips a block, and
    either way the file's promise that an ID is stable breaks silently.
    """
    if not (research_dir / DIRECTION).exists():
        return ("`direction.md` does NOT exist yet — create it with the header row "
                "and start at `D-001`.")
    # Sliced, not split: `_ROW` already fixes the id at `D` plus three digits, so
    # the offset is guaranteed by the pattern that produced the string. A split
    # here would be a second, weaker parse of a shape already parsed once — and
    # `test_no_module_derives_a_path_segment_from_a_url_by_splitting` is a census
    # over exactly that habit.
    ids = sorted(int(did[2:]) for did, _st in direction_rows(research_dir))
    if not ids:
        return "`direction.md` exists but holds no rows — start at `D-001`."
    return (f"`direction.md` holds **{len(ids)} rows**, highest ID **D-{ids[-1]:03d}**. "
            f"A NEW recommendation starts at **D-{ids[-1] + 1:03d}**. "
            f"Never renumber an existing row.")


def direction_statuses(research_dir: Path) -> dict[str, str]:
    """Every direction row's `status`, keyed by id — the operator's own column.

    Fed to `plan_activities.statuses_this_run_had_no_right_to` UNCHANGED rather
    than compared here. That function already judges only PRE-EXISTING rows,
    which is exactly the contract this column needs: the prompt REQUIRES a newly
    appended `D-NNN` to carry `status: open`, so a new row's status is prescribed
    by another rule and is not this guard's business. A second hand-written
    before/after comparison would be the drift `normalise_cell` documents.

    WHAT AN UNGUARDED FLIP COSTS, since it is not obvious from the column: a run
    that writes `applied` on a row the operator never ruled leaves a green run
    and a ruling indistinguishable from a genuine one, after which `/standup`
    rotates the row out and the receipt is gone.
    """
    return dict(direction_rows(research_dir))


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

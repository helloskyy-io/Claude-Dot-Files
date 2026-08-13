"""Every tool in `scripts/helpers/measure/` is listed, and names who reads it.

THIS IS PHASE 6'S OWN FINDING, ONE LEVEL UP. The phase exists because three
parent-written observables shipped with no reader; `README.md` in that directory
already states the defence against the same failure for the readers themselves —
*"A `Read by` column with nothing in it is this directory's own finding, one
level up. A tool nobody reads is the thing Phase 6 exists to stop; a tool whose
row cannot name a consumer is the same defect wearing a table."* — and nothing
enforced it. A rule stated in prose beside a hand-kept table is the shape that
let `run_resources` ship unread in the first place.

TWO PROPERTIES, AND THE FIRST IS THE ONE THAT WOULD HAVE FIRED. A tool absent
from the table entirely is invisible to any check on the table's contents, and
that is how a tool arrives with no stated consumer: not by leaving a cell blank,
but by never adding the row. So the population is read off DISK and compared
against the table, rather than the table being checked against itself.

`run_log.py` is excluded BY NAME and its exclusion is asserted, because it is a
declaration module rather than a replay tool — the README and
`docs/file_structure.txt` both say so. An exclusion that is not named is a hole.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]
_MEASURE = _REPO / "scripts" / "helpers" / "measure"
_README = _MEASURE / "README.md"

# NOT A REPLAY TOOL, so it has no question and no consumer of its own: it is the
# run-log surface's declaration, loaded BY the tools rather than run beside them.
NOT_A_TOOL = frozenset({"run_log.py"})


def _rows() -> list[list[str]]:
    """The `| Tool | Answers | Read by |` table's body rows, cells stripped."""
    rows = []
    for line in _README.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 3:
            rows.append(cells)
    return rows


def _tool_of(cell: str) -> str | None:
    found = re.match(r"`([^`]+\.py)`", cell)
    return found.group(1) if found else None


def test_every_tool_on_disk_has_a_ROW() -> None:
    """A tool with no row is the failure; a blank cell is only its symptom.

    Read off disk rather than out of the table, because a table checked against
    itself cannot see the tool that was never added to it — which is the exact
    shape of the finding this whole phase is the remedy for.
    """
    on_disk = {p.name for p in _MEASURE.glob("*.py")} - set(NOT_A_TOOL)
    assert on_disk, f"no tools found under {_MEASURE} — this gate read nothing"
    listed = {t for t in (_tool_of(r[0]) for r in _rows()) if t}
    assert on_disk <= listed, (
        f"tools in {_MEASURE.name}/ with no row in README.md: "
        f"{sorted(on_disk - listed)}. A tool nobody reads is what this directory "
        f"exists to stop producing; a tool nobody LISTS is how one gets there."
    )
    assert listed <= on_disk, (
        f"README.md lists tools that are not on disk: {sorted(listed - on_disk)}"
    )


def test_every_row_NAMES_A_CONSUMER() -> None:
    """The `Read by` cell is the rule the README already states in prose."""
    empty = [r[0] for r in _rows() if not r[2] or r[2] in {"-", "—"}]
    assert not empty, (
        f"rows with an empty `Read by` column: {empty}. Name the phase, "
        f"candidate, direction row or issue that reads this tool's output, or "
        f"the tool is a one-shot and does not belong in a directory whose "
        f"README says every tool here answers a standing question."
    )


def test_run_log_is_excluded_BY_NAME_and_is_still_where_the_exclusion_says() -> None:
    """The exclusion is a claim about the tree, so it is checked against the tree.

    If `run_log.py` were ever renamed or removed, `NOT_A_TOOL` would silently
    excuse a file that no longer exists while the real declaration module went
    unlisted — an exclusion outliving its subject is how a gate stops covering
    the thing it names.
    """
    for name in NOT_A_TOOL:
        assert (_MEASURE / name).is_file(), (
            f"{name} is excluded from the tool table but is not in {_MEASURE}. "
            f"Either the exclusion is stale or the declaration module moved."
        )
    assert "run_log.py" in _README.read_text(encoding="utf-8"), (
        "README.md no longer explains why run_log.py is in this directory "
        "without a row, so its absence from the table reads as an omission"
    )

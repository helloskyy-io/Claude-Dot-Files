"""A component's `Status:` marker is one of the four, or it is invented.

WHAT HAPPENED, AND IT IS THE WHOLE REASON THIS EXISTS. On 2026-08-16 a run
finished a component and marked its roadmap `**Status: 🗄️ RETIRED**` — a word
no standard defines, in a field every reader treats as a controlled vocabulary.
It carried a second clause, *"these documents are not maintained,"* which is
what stranded seven operator rulings in that file for three weeks (issue #97).

**Nothing refused it for ten days.** It surfaced only when `plan-sprint` ran
against that component and found a marker its own legend does not have — and
that run was doing something else entirely. A vocabulary enforced by a workflow
tripping over it is not enforced.

THE ROOT CAUSE WAS A MISSING INSTRUCTION, NOT A MISSING CHECK, and the fix
shipped alongside this: `plan_draft.md` writes the roadmap and said only
*"current status marked clearly at the top"*, naming no set. A writer told to
mark a status with no list to choose from composes one. **This test is the
backstop, not the fix** — it catches the writers the prompt does not bind:
`plan-refine` also edits roadmaps, so do hand edits, so will whatever ships next.

THE LEGEND IS READ, NEVER RESTATED. The four markers live in `sprint.md`'s
status table and nowhere else. Copying them into this file would create exactly
the second-source drift the corpus keeps paying for — a fifth marker would then
need adding in two places, and the day they disagree this test is asserting
about a vocabulary nobody uses. So the legend is parsed, and a change to it is a
deliberate edit to the file that defines it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
import sys as _s, pathlib as _p  # noqa: E402
_s.path.insert(0, str(_p.Path(__file__).resolve().parents[4]
                     / "scripts" / "workflows" / "temporal" / "tests"))
from planning_corpus import PLANNING_ROOT  # noqa: E402

import sys as _cg_sys  # noqa: E402
from pathlib import Path as _cg_Path  # noqa: E402
_cg_sys.path.insert(0, str(_cg_Path(__file__).resolve().parents[4]
                           / "scripts" / "workflows" / "temporal" / "tests"))
from planning_corpus import require_planning_corpus  # noqa: E402


# sprints.md (plural) in the planning repo, and components are bucketed by edge.
SPRINT = PLANNING_ROOT / "development" / "sprints.md"
COMPONENTS = PLANNING_ROOT / "development" / "edge-assistant"

#: `**Status: <marker> <words>**` at the head of a roadmap. Anchored to the line
#: start so a marker QUOTED inside prose — which several roadmaps do when
#: explaining a derivation — is not read as the file's own status.
_STATUS = re.compile(r"^\*\*Status:\s*(\S+)", re.M)

#: A legend row: `| ✅ COMPLETE | means | placed by | derived as |`. The marker is
#: the leading non-word token of the first cell.
_LEGEND_ROW = re.compile(r"^\|\s*([^\sA-Za-z|][^\s|]*)\s+[A-Z]", re.M)


def _legend() -> set[str]:
    """The markers `sprint.md` defines, parsed rather than copied."""
    return set(_LEGEND_ROW.findall(SPRINT.read_text()))


def _roadmaps() -> list[Path]:
    return sorted(COMPONENTS.glob("*/roadmap.md"))


def test_the_legend_is_PARSEABLE_before_anything_is_checked_against_it() -> None:
    """A GUARD WHOSE INPUT CAN VANISH IS A GUARD ITS INPUT CAN SWITCH OFF.

    If the legend table is reshaped and this parser stops matching, the set
    comes back empty — and an empty set makes every check below vacuous while
    reporting green. Asserted separately so that failure names ITSELF rather
    than arriving as "no roadmap has a legal marker", which reads as the
    opposite problem.
    """
    require_planning_corpus()
    assert SPRINT.is_file(), f"{SPRINT} is missing — it defines the vocabulary"
    markers = _legend()
    assert len(markers) >= 4, (
        f"parsed {sorted(markers)} out of sprint.md's status legend, expected at "
        f"least four. The table shape changed and this parser no longer matches "
        f"it — every check in this module is vacuous until that is fixed."
    )


def test_there_are_roadmaps_to_check() -> None:
    """The second half of the same vacuity floor: no roadmaps, no coverage."""
    require_planning_corpus()
    assert _roadmaps(), f"no component roadmap found under {COMPONENTS}"


@pytest.mark.parametrize("roadmap", _roadmaps(), ids=lambda p: p.parent.name)
def test_a_roadmap_STATUS_marker_is_one_the_legend_defines(roadmap: Path) -> None:
    """The closed set, enforced on the artifact whoever wrote it.

    A roadmap with NO `Status:` line passes — this asserts that a status, where
    one is stated, is a legal one. Requiring the line is a different rule with a
    different owner, and pretending otherwise here would fail a correct roadmap
    for a convention nothing has ratified.
    """
    found = _STATUS.findall(roadmap.read_text())
    if not found:
        return

    legal = _legend()
    illegal = [m for m in found if m not in legal]
    assert not illegal, (
        f"{roadmap.relative_to(REPO)} carries status marker(s) {illegal}, which "
        f"`sprint.md`'s legend does not define. It defines {sorted(legal)}.\n\n"
        f"THE SET IS CLOSED. A component whose work is done is COMPLETE; where "
        f"its FUTURE work now lives is a sentence beside the marker, never a new "
        f"marker. If a fifth state is genuinely needed, add it to the legend "
        f"first — that file is the definition, and this check reads it."
    )


@pytest.mark.parametrize("roadmap", _roadmaps(), ids=lambda p: p.parent.name)
def test_no_roadmap_DECLARES_ITSELF_UNMAINTAINED(roadmap: Path) -> None:
    """THE CLAUSE THAT DID THE ACTUAL DAMAGE, and it is not the marker.

    `RETIRED` was a wrong word. *"These documents are not maintained"* was a
    wrong INSTRUCTION: readers obeyed it. Seven standards-amendment rulings sat
    unread in that roadmap for three weeks because the file told everyone it was
    dead, and the only thing that noticed was a workflow reading it for an
    unrelated reason.

    A completed component's docs are maintained like any other's. If something
    genuinely should not be read any more, the answer is to delete it — not to
    leave it in the tree wearing a sign.
    """
    text = roadmap.read_text().lower()
    for phrase in ("are not maintained", "is not maintained", "no longer maintained"):
        assert phrase not in text, (
            f"{roadmap.relative_to(REPO)} declares itself unmaintained "
            f"({phrase!r}). A document in the tree is read; one that should not "
            f"be read is deleted. Measured: this exact clause stranded seven "
            f"operator rulings for three weeks (issue #97)."
        )

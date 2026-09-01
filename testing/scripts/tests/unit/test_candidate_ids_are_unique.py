"""A `C-NNN` addresses exactly one proposal, and nothing was checking that.

`candidates.md` states its own rule — ids are never reused and never renumbered —
and the id is the ADDRESS: `triage-candidates` triages by it, phase docs cite it, and a
finding's whole disposition can be the sentence "see C-45bhs5cm". An id that names two
different proposals makes one of them unaddressable, and it does so silently.

THE ID SPACE IS ALLOCATED BY READING THE CURRENT MAXIMUM, which is safe exactly
as long as one run at a time is doing it. **It is not, and the collision has
already happened three ways.** On 2026-08-11, within about forty minutes: two
open PRs each appended a `C-xhb460zu` for unrelated proposals, and a THIRD — already
merged to `main` by then — had taken `C-xhb460zu`, `C-abieu0fg` and `C-ijmjaqrs` for a fourth
set. The branch that wrote this check had to renumber its own row to `C-skkjo6jn`
after the merge, having allocated correctly against a `main` that moved
underneath it.

Git raises a conflict on the summary paragraph the PRs rewrite, and that is the
whole of the accidental protection — **the natural resolution of that conflict
keeps both rows**, so duplicate ids survive it in exactly the case where a human
is already busy reconciling prose. Nothing in `testing/` or `scripts/` would
have said so.

WHAT THIS FAILING LOOKS LIKE, stated up front so it is not mistaken for flakiness:
if two branches each allocating the same id are both merged, this goes RED on the
default branch and names the duplicate. **That is the intended behaviour and it
is the cheap end of the trade** — the alternative is a queue in which one of two
proposals is silently unreachable by the only handle anything uses to reach it.
The remedy is always the same: the LATER allocation renumbers to the next free
id, and its summary paragraph moves with it.

THE FOURTH CHECK OF ITS SHAPE IN THIS REPO — a population read off disk against a
declaration kept by hand. See `test_file_structure_map_covers_the_tree.py`, which
names the other three. Each was written after its own surface had already
drifted; this one is written after the drift and before anybody has had to pay
for it, which is the only difference.
"""

from __future__ import annotations

import collections
import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]
import sys as _s, pathlib as _p  # noqa: E402
_s.path.insert(0, str(_p.Path(__file__).resolve().parents[4]
                     / "scripts" / "workflows" / "temporal" / "tests"))
from planning_corpus import PLANNING_ROOT  # noqa: E402

import sys as _cg_sys  # noqa: E402
from pathlib import Path as _cg_Path  # noqa: E402
_cg_sys.path.insert(0, str(_cg_Path(__file__).resolve().parents[4]
                           / "scripts" / "workflows" / "temporal" / "tests"))
from planning_corpus import require_planning_corpus  # noqa: E402


_CANDIDATES = PLANNING_ROOT / "tracked" / "candidates"

# THE ID NOW LIVES IN TWO PLACES AND BOTH ARE CHECKED: the filename, which §2
# makes authoritative, and the item's own `id` field. The filesystem refuses two
# files with one name, so a duplicate FILENAME cannot occur — but a file COPIED
# and edited without its `id` changed reads as its neighbour to every consumer
# keyed by id, and that is what this gate still catches.
#
# `[0-9a-z]{8}` AND NOT `\d+`: ids are eight random base36 characters. A
# digits-only key would silently stop seeing every id containing a letter, which
# is all but a vanishing fraction of them — and a uniqueness check that cannot
# SEE an id reports "all unique" over the handful it can, which is the
# wrong-confidence shape this suite exists to refuse.
_ID_FIELD = re.compile(r"^id:\s*(C-[0-9a-z]+)\s*$", re.M)


def _ids() -> list[str]:
    """Every id the store DECLARES, read from the frontmatter rather than the name.

    Deliberately not `[p.stem for p in ...]`: reading the filenames would make
    this check tautological, since the filesystem already guarantees those are
    unique. The declared id is the one that can collide.
    """
    found = []
    for path in sorted(_CANDIDATES.glob("*.md")):
        m = _ID_FIELD.search(path.read_text())
        if m:
            found.append(m.group(1))
    return found


def test_the_candidates_store_is_where_it_is_declared_to_be() -> None:
    """If it moves, every assertion below passes against nothing."""
    require_planning_corpus()
    assert _CANDIDATES.is_dir(), (
        f"{_CANDIDATES} does not exist. finding-routing.md §7 sends every "
        f"producing run's proposal here; a moved store means this check has "
        f"been asserting about an empty list."
    )


def test_there_are_enough_items_for_this_check_to_mean_anything() -> None:
    """A vacuity floor: uniqueness over zero ids holds trivially."""
    require_planning_corpus()
    assert len(_ids()) > 30


def test_every_candidate_id_is_ALLOCATED_ONCE() -> None:
    """The whole point. Two rows, one address, one unreachable proposal."""
    counts = collections.Counter(_ids())
    duplicated = {i: n for i, n in counts.items() if n > 1}
    assert not duplicated, (
        f"these ids are allocated more than once: "
        f"{', '.join(f'{i} x{n}' for i, n in sorted(duplicated.items()))}. "
        f"Two proposals sharing an id means one of them cannot be addressed — "
        f"`triage-candidates` triages by id and a disposition can be the words 'see "
        f"C-0NN'. Renumber the LATER allocation to the next free id, and move "
        f"its § Where things stand sentence with it. Ids are never reused and "
        f"never renumbered otherwise, which is this file's own rule."
    )


def test_every_candidate_id_uses_THE_SAME_SHAPE() -> None:
    """`C-66` and `C-xhb460zu` are two spellings of one address.

    Cheap to hold and expensive to lose: a grep for one misses the other, and a
    reader who finds neither concludes the candidate was never placed.

    THE SHAPE CHANGED ON 2026-08-21 and the OLD one is not accepted here. Ids
    were `C-` plus three digits, allocated as `max + 1` from the branch's own
    snapshot — so two branches took the same "next free" id and git merged both
    rows with no conflict, because they sat at different positions. Nine
    renumbering events, then six more collisions, three on one PR. Random ids
    need no coordination, so there is no next to race for.

    Every existing row was migrated, deliberately: the operator ruled against
    carrying two shapes. That is why this asserts ONE form rather than allowing
    a legacy one — a tolerated second shape is how the grep-misses-it failure
    above gets reintroduced by a run that copies the older neighbour.
    """
    odd = sorted({i for i in _ids() if not re.fullmatch(r"C-[0-9a-z]{8}", i)})
    assert not odd, (
        f"these ids are not `C-` plus eight base36 characters: {odd}. Ids are "
        f"MINTED by `research_activities.candidate_ceiling` and handed to the run; "
        f"nothing computes one."
    )

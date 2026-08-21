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
_CANDIDATES = _REPO / "docs" / "standards" / "architecture" / "research" / \
    "candidates.md"

# A row: `| C-skkjo6jn | <finding> | <source> | <decision> | `status` | <note> |`.
# Anchored at line start so an id merely CITED inside another row's prose —
# which happens constantly, and is not an allocation — is not read as one.
#
# `[0-9a-z]+` AND NOT `\d+`: ids are eight random base36 characters. A digits-only
# key would silently stop seeing every id containing a letter, which is all but a
# vanishing fraction of them — and a uniqueness check that cannot SEE an id
# reports "all unique" over the handful it can, which is the wrong-confidence
# shape this suite exists to refuse.
_ROW = re.compile(r"^\|\s*(C-[0-9a-z]+)\s*\|", re.M)


def _ids() -> list[str]:
    return _ROW.findall(_CANDIDATES.read_text())


def test_the_candidates_file_is_where_it_is_declared_to_be() -> None:
    """If it moves, every assertion below passes against nothing."""
    assert _CANDIDATES.is_file(), (
        f"{_CANDIDATES} does not exist. finding-routing.md §4 sends every "
        f"producing run's proposal here; a moved file means this check has "
        f"been asserting about an empty string."
    )


def test_there_are_enough_rows_for_this_check_to_mean_anything() -> None:
    """A vacuity floor: uniqueness over zero ids holds trivially."""
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

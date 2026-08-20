"""A planning directory must be SUMMARISED in the map, never listed file by file.

THE DEFECT THIS PINS, C-113, measured three times on independent runs.

  * PR #111 — `plan-feature` added four phase docs to `workflow-decomposition/`;
    `test_a_directory_the_map_ENUMERATES_is_enumerated_COMPLETELY` went red; an
    operator hand-patched `docs/file_structure.txt`.
  * The correction pass on that PR filed C-113 for the general form.
  * PR #123 — the next `plan-feature` run, on `persistent-memory-protocol/`,
    added ONE phase doc and hit the identical wall.

THE MECHANISM IS A BOUNDARY, NOT A CARELESS RUN, which is why a check belongs
here rather than a note in a prompt. Writing a phase doc is `plan-feature`'s
ENTIRE JOB. Its write grant is `docs/development/<component>/[^/]+\\.md` plus the
candidates file, and `docs/file_structure.txt` is in neither — its dispatch prompt
names the map as out of scope explicitly. So a correct run makes the map
incomplete and is structurally forbidden to repair it, and the NEXT component
planned lands red for the same reason. Neither side is wrong; the pair is.

THE ROLL-UP REMEDY RATHER THAN A WIDER GRANT, and the two are genuinely different
rulings. A per-file map row for a phase doc RESTATES what the component's own
`roadmap.md` already says, and it is maintained by an actor that structurally
cannot read it — two sources of truth where one is blind, which is the shape that
produced this. Widening the grant instead makes a planning workflow responsible
for a repo-wide artifact in order to satisfy a check about its own directory, and
leaves the duplication in place. The map's own failure message already offered
this exit: *"if the directory should be summarised instead — remove the per-file
lines so it is rolled up honestly rather than listed incompletely."*

SCOPED TO PLANNING DIRECTORIES AND NOWHERE ELSE. The map's per-file detail is
load-bearing across `scripts/`, `testing/` and the prompt tree, and this is not a
licence to summarise the tree. A planning directory is DERIVED — a directory
directly under `docs/development/` holding a `roadmap.md` and at least one
`phase<N>_*.md` — so a fourth component is covered on the day it is planned rather
than on the day someone remembers to add it to a list. That derivation is the
whole guard: a hardcoded list of three would go stale exactly when it mattered.

WHAT THIS DOES NOT LOOK AT, so it is not read as covering more than it does:

  * **Components on the one-file shape.** `<name>/<name>.md` with no roadmap is
    not a planning directory here and gets no opinion from this module either way.
  * **`research/` subdirectories.** They are their own directory, so a row for
    `research/` enumerates nothing in the component directory. Untouched.
  * **Whether the ANNOTATION on the surviving component row is true.** Same blind
    spot every check on this map has, and stated for the same reason.
  * **Any directory outside `docs/development/`.** A `roadmap.md` elsewhere in the
    tree is invisible to `_planning_directories` by construction.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# THE PARSE COMES FROM THE HELPER, NOT FROM THE SIBLING TEST MODULE.
# `test_file_structure_map_covers_the_tree.py` asserts the other end of this same
# rule and both need the identical grammar — but
# `test_test_tree_hygiene.test_no_test_module_imports_another_test_module` forbids
# a test module importing a test module, for three reasons its docstring sets out,
# the sharpest being that such an import resolves only under pytest's default
# `prepend` mode and fails at COLLECTION otherwise, which `mutate.sh` reads as a
# caught mutation (issue #72). `file_structure_map.py` is the remedy that rule
# names, and it is why there is no third copy of this regex in the repo.
from file_structure_map import (  # noqa: E402
    MAP,
    map_paths,
    partially_listed,
    tracked,
)

_DEVELOPMENT = "docs/development"
_PHASE_DOC = re.compile(r"^phase\d+_.*\.md$")
_ROADMAP = "roadmap.md"


def _planning_directories(tracked: list[str]) -> set[str]:
    """Directories directly under `docs/development/` on the roadmap+phases shape.

    PURE, over a list of repo-relative path strings, so the discriminator below
    can feed it a self-contained sample instead of the real tree. A control that
    shares a fixture with the code under test over-fires and proves nothing.
    """
    by_dir: dict[str, set[str]] = {}
    for path in tracked:
        parent, _, name = path.rpartition("/")
        # Directly under docs/development/, one level deep — `<name>/research/…`
        # is a different directory and is deliberately not one of these.
        if not parent.startswith(_DEVELOPMENT + "/") or parent.count("/") != 2:
            continue
        by_dir.setdefault(parent, set()).add(name)
    return {d for d, names in by_dir.items()
            if _ROADMAP in names and any(_PHASE_DOC.match(n) for n in names)}


def _per_file_rows(map_paths: set[str], directories: set[str],
                   tracked: list[str]) -> dict[str, list[str]]:
    """For each planning directory, the FILES in it that the map lists by name."""
    listed: dict[str, list[str]] = {}
    for path in tracked:
        parent, _, name = path.rpartition("/")
        if parent in directories and path in map_paths:
            listed.setdefault(parent, []).append(name)
    return {d: sorted(names) for d, names in listed.items()}


_TRACKED = [str(p) for p in tracked()]
_PLANNING = _planning_directories(_TRACKED)


def test_the_derivation_FOUND_planning_directories() -> None:
    """VACUITY FLOOR. Every assertion below is scoped by this set.

    If `_planning_directories` breaks — the map moves, `git ls-files` is read
    wrong, the naming convention changes — it returns the empty set, there is
    nothing to examine, and the guard goes green while reporting on nothing. The
    count of things EXAMINED is asserted, not only the count of things found.
    """
    assert len(_PLANNING) >= 3, (
        f"the derivation found {sorted(_PLANNING)} — fewer than the three "
        f"components known to be on the roadmap+phases shape. Fix the reader; do "
        f"not weaken this. A zero here would make every check below vacuous.")
    assert all(p.startswith(_DEVELOPMENT + "/") for p in _PLANNING)


def test_a_planning_directory_has_NO_per_file_row_in_the_map() -> None:
    """THE GUARD. One per-file row flips the directory back to enumerated."""
    offenders = _per_file_rows(map_paths(MAP.read_text()), _PLANNING, _TRACKED)
    assert not offenders, (
        "docs/file_structure.txt lists these planning-directory files by name:\n"
        + "\n".join(f"  {d}: {', '.join(n)}" for d, n in sorted(offenders.items()))
        + "\n\nOne such row is enough to make the directory ENUMERATED, and "
          "`test_a_directory_the_map_ENUMERATES_is_enumerated_COMPLETELY` then "
          "demands a row for every phase doc in it — including the ones "
          "`plan-feature` has not written yet and is not permitted to add here "
          "(C-113). Delete the row. The per-phase detail belongs in that "
          "component's roadmap.md, which is the only copy anyone maintains.")


def test_every_planning_directory_is_still_REACHABLE_through_the_map() -> None:
    """Rolled up is not the same as absent, and the difference is the whole point.

    Deleting the per-file rows must leave the component's OWN row behind. Without
    this, "roll it up" and "drop it from the map" are indistinguishable to the
    check above, and the cheapest way to make that one pass would be to delete the
    directory entirely.
    """
    mapped = map_paths(MAP.read_text())
    missing = sorted(d for d in _PLANNING if d not in mapped)
    assert not missing, (
        f"these planning directories have no row of their own in "
        f"docs/file_structure.txt at all: {missing}. Rolled up means SUMMARISED, "
        f"not omitted — the directory keeps its annotated line and loses only the "
        f"per-file ones.")


# --- the controls ------------------------------------------------------------

def test_the_detector_FIRES_on_a_map_that_ENUMERATES_a_planning_directory() -> None:
    """DISCRIMINATOR, on a SELF-CONTAINED sample rather than the real map.

    Derived from what this module claims about itself — that it detects a
    per-file row in a planning directory — and not from whatever is easy to
    break. The negative half is the shape the map now uses, without which a
    detector that flagged every row would satisfy the positive case and fail the
    whole tree.
    """
    tracked = [
        "docs/development/widget/roadmap.md",
        "docs/development/widget/phase1_first.md",
        "docs/development/widget/phase2_second.md",
        "docs/development/widget/research/raw/topic.md",
        "docs/development/one-pager/one-pager.md",   # not the roadmap+phases shape
        "scripts/helpers/thing.sh",
    ]
    planning = _planning_directories(tracked)
    assert planning == {"docs/development/widget"}, (
        f"the derivation returned {planning}. It must find the roadmap+phases "
        f"component and must NOT claim the one-file component or a research "
        f"subdirectory.")

    enumerated = (
        "claude-dot-files/\n"
        "├── docs/\n"
        "│   ├── development/\n"
        "│   │   ├── widget/                          # a component\n"
        "│   │   │   ├── roadmap.md                   # listed by name\n"
        "│   │   │   ├── phase1_first.md              # listed by name\n"
        "│   │   │   └── research/                    # rolled up\n"
    )
    assert _per_file_rows(map_paths(enumerated), planning, tracked) == {
        "docs/development/widget": ["phase1_first.md", "roadmap.md"]
    }, ("the detector did not report the per-file rows this sample plainly has, "
        "so every green result above is unproven.")

    rolled_up = (
        "claude-dot-files/\n"
        "├── docs/\n"
        "│   ├── development/\n"
        "│   │   ├── widget/                          # a component\n"
        "│   │   │   └── research/                    # rolled up\n"
    )
    assert not _per_file_rows(map_paths(rolled_up), planning, tracked), (
        "the detector fired on the shape the map now uses — a component row plus "
        "a research/ subdirectory row and nothing else. A guard that cannot tell "
        "that from the defect would be turned off within a week.")
    assert "docs/development/widget" in map_paths(rolled_up), (
        "the rolled-up sample must still REACH the component, or the "
        "reachability check above is asserting against a parser that lost it.")


def test_ADDING_A_PHASE_DOC_LEAVES_THE_COMPLETENESS_CHECK_GREEN() -> None:
    """THE DEFECT, REPRODUCED — and this is the assertion that proves the fix.

    Everything above asserts the map's SHAPE. This drives the predicate that
    actually went red, `file_structure_map.partially_listed`, which is the SAME
    function `test_a_directory_the_map_ENUMERATES_is_enumerated_COMPLETELY` calls
    — not a copy of it — against the real map and the real tree plus a phase doc
    added to EVERY planning directory at once. A fix for a red-on-add defect that
    is never exercised by ADDING is not verified.

    ALL OF THEM, not one. The defect was measured on `workflow-decomposition/`
    (PR #111) and then again on `persistent-memory-protocol/` (PR #123), which is
    the evidence that a per-directory fix is the wrong shape.

    Paired with its control below: green here means nothing unless the same
    predicate can still go red on a directory the map really does enumerate.
    """
    added = [Path(d) / "phase99_added_by_a_planning_run.md" for d in sorted(_PLANNING)]
    assert added, "the vacuity floor should have caught this"

    tree = [Path(p) for p in _TRACKED] + added
    holes = partially_listed(map_paths(MAP.read_text()), tree)
    assert not holes, (
        f"adding a phase doc to a planning directory still leaves the map "
        f"partially listed: {holes}. The roll-up did not take — check that no "
        f"per-file row survived in those directories.")


def test_THE_SAME_PREDICATE_STILL_GOES_RED_on_a_genuinely_enumerated_directory() -> None:
    """CONTROL FOR THE TEST ABOVE, and it is what makes that one evidence.

    The check above could be green because the roll-up works, or because
    `partially_listed` stopped seeing anything. Adding an unlisted file to a
    directory the map really does enumerate must still be reported — the map's
    per-file detail is untouched everywhere outside `docs/development/`, and this
    is what says so.

    THE TARGET IS DERIVED, NOT NAMED. A hardcoded directory silently stops being
    enumerated one day and this control passes for the wrong reason ever after.
    """
    mapped = map_paths(MAP.read_text())
    enumerated = sorted({
        parent for path in _TRACKED
        if (parent := path.rpartition("/")[0]).startswith("scripts/")
        and path in mapped
    })
    assert enumerated, ("no directory under scripts/ is enumerated in the map any "
                        "more — this control has nothing to fire on and proves "
                        "nothing. Pick another still-enumerated subtree.")

    victim = Path(enumerated[0]) / "not_in_the_map.py"
    holes = partially_listed(mapped, [Path(p) for p in _TRACKED] + [victim])
    assert holes.get(enumerated[0]) == ["not_in_the_map.py"], (
        f"the predicate did not report the hole this control plainly creates in "
        f"{enumerated[0]}; it returned {holes.get(enumerated[0])!r}. Every green "
        f"result above is therefore unproven.")

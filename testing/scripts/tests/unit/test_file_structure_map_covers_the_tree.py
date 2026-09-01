"""`docs/file_structure.txt` is an ENUMERATION of a derivable set, so derive it.

`CLAUDE.md` calls this map authoritative — "This is an orientation sketch, not the
exhaustive map — `docs/file_structure.txt` is that, and it is authoritative." A
reader or a dispatch that cannot find a file through it does not conclude the map
is stale; it concludes the file does not exist. Every silent miss spends a little
of the map's standing as a source, and nothing was checking.

THIS IS THE FOURTH SURFACE IN THIS REPO WITH THE SAME SHAPE — a hand-kept
declaration of a population that is sitting on disk — and the first three each
acquired their check separately, after each had drifted:

  * the run log's member set against `_append_run_event`'s call sites
    (`test_run_log.py`);
  * the roadmap's phase labels against the phase docs
    (`test_measurement_figures_are_cited.py`);
  * `scripts/helpers/measure/README.md`'s tool table against the tools on disk
    (`test_measure_readme_names_a_consumer.py`).

A table checked against itself cannot see the entry that was never added to it.
So the population here is read from `git ls-files` and the map is compared
against THAT, in the only direction that matters: the map may summarise, but it
may not silently omit.

WHAT IS AND IS NOT ASSERTED, because the map is a MAP and not a file listing. It
deliberately rolls up: `raw/<topic>.md` stands for a directory of research
papers, and `modules/assistant/` stands for a whole family under one annotated
line. Forcing every tracked file to have its own line would delete the thing that
makes the map readable. So the rule follows the map's own convention:

  * WHERE IT ENUMERATES, IT ENUMERATES COMPLETELY. If any file in a directory has
    its own entry, every tracked file in that directory must — a partially-listed
    directory is the shape that reads as complete and is not. This is the half
    that found 27 missing files, four of them test modules in a directory whose
    other nineteen are all listed individually.
  * WHERE IT ROLLS UP, IT MUST STILL REACH. Every tracked file must be reachable
    through some ancestor directory that the map names, so a whole new subtree
    cannot appear with no mention anywhere.

MATCHED BY RECONSTRUCTED PATH, NOT BY LEAF NAME, and the difference decided what
this check demands. A full path never appears on any one line of the map — the
tree renders it across nested lines — so the obvious implementations both fail in
opposite directions: grepping for the path reads 0 against a correctly nested
entry, and matching bare leaf names counts a directory as enumerated because some
UNRELATED directory elsewhere in the map happens to list a file of the same name.
The second is not hypothetical: under leaf matching, two `prompts/` directories
the map deliberately rolls up were scored as enumerated on the strength of a
`rules.md` entry sitting under `docs/standards/`, and the check demanded that the
whole `modules/assistant/` family be expanded file by file — deleting the roll-up
the map is built on. So the indentation is parsed back into paths, and a directory
is enumerated only when a file at that ACTUAL path has a line.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# THE PARSE, THE TREE AND THE HOLE FINDER LIVE IN A HELPER MODULE, not here.
# `test_planning_directories_are_ROLLED_UP_in_the_map.py` asserts the opposite end
# of the same rule and needs the identical parse, and
# `test_test_tree_hygiene.test_no_test_module_imports_another_test_module` forbids
# it importing this file to get it. `file_structure_map.py` is the remedy that
# rule names. Every docstring explaining WHY the parse works the way it does moved
# with the code rather than being left behind pointing at nothing.
from file_structure_map import (  # noqa: E402
    EXCLUDED_NAMES,
    MAP,
    REPO,
    TEMPLATE,
    map_entries,
    map_paths,
    partially_listed,
    tracked,
)



def _mapped_entries() -> dict[str, bool]:
    """The live map, parsed. See `file_structure_map.map_entries` for the grammar."""
    return map_entries(MAP.read_text())


def _mapped_paths() -> set[str]:
    return map_paths(MAP.read_text())


def test_the_exclusion_list_is_only_what_it_says_it_is() -> None:
    """The control on the control: an exclusion that grows silently is a hole."""
    excluded = {p for p in tracked() if p.name in EXCLUDED_NAMES}
    assert excluded, "no .gitkeep is tracked any more — drop the exclusion"
    assert all(p.name == ".gitkeep" for p in excluded)


def test_the_map_PARSES_into_paths_that_actually_exist() -> None:
    """The control on the parser, and it is the load-bearing one.

    Every assertion below is vacuous if the indentation parse silently produces
    nonsense: a map that reconstructs to paths nobody has ever had would report
    zero enumerated directories and pass. So most of what it produces has to
    resolve on disk, and there has to be a lot of it.
    """
    paths = _mapped_paths()
    assert len(paths) > 150, "the map parsed into too few entries to be the map"
    resolves = [p for p in paths if (REPO / p).exists()]
    assert len(resolves) > 0.9 * len(paths), (
        f"only {len(resolves)} of {len(paths)} reconstructed paths exist on "
        f"disk — the indentation parse is wrong, or the map has drifted far "
        f"enough that this check is measuring the wrong thing. Sample of "
        f"non-resolving entries: {sorted(set(paths) - set(resolves))[:8]}"
    )


def test_every_FILE_ENTRY_in_the_map_NAMES_A_FILE_THAT_EXISTS() -> None:
    """The other direction: the map may summarise, but it may not INVENT.

    Every check above reads `git ls-files` and asks whether the map reaches it.
    None of them reads the map and asks whether what it says is true, so a row
    naming a file that has never existed at that path is green under all of
    them — and it is worse than a missing row, because a reader who cannot find
    a file through the map concludes the file does not exist, while a reader who
    CAN find it goes to the wrong bucket and finds nothing there either.

    THE MEASURED RECURRENCE, which is why this keys on the class rather than on
    the two rows that were wrong. Of the two PRs that promoted a shared prompt
    fragment and added a row for it — #91 (`altitude_product.md`) and #99
    (`mutation_discipline.md`) — BOTH put the row under `docs/guide/`, where
    neither file has ever lived; both live in the shared prompt pool at
    `scripts/workflows/temporal/modules/assistant/prompts/`, which the map
    deliberately rolls up. Two for two is not a slip, it is the default outcome
    of adding a row by eye.

    WHY THE EXISTING PARSE CONTROL DID NOT CATCH IT.
    `test_the_map_PARSES_into_paths_that_actually_exist` tolerates 10%
    non-resolving paths ON PURPOSE — it is asserting that the INDENTATION PARSE
    works, and a control that demanded perfection would fail on the template row
    below and stop being a parser control. Its slack absorbed both rows for
    months. This is the reconciliation the slack was never meant to cover, and
    it is a separate test rather than a tightening of that one for exactly that
    reason.

    NOTE WHAT THIS DOES NOT LOOK AT: it checks that a named path EXISTS, never
    that the annotation beside it is true. A row that files a real file under a
    plausible-but-wrong description is invisible here, as it is everywhere else.
    """
    ghosts, bad_templates = [], []
    for path, is_dir in sorted(_mapped_entries().items()):
        if is_dir:
            continue                       # rolled-up directories are checked above
        if TEMPLATE.search(path):
            # `raw/<topic>.md` stands for a naming CONVENTION, so no such file
            # exists or should. The claim it still makes is that the directory
            # holding them does, and that is what gets checked.
            if not (REPO / path).parent.is_dir():
                bad_templates.append(path)
            continue
        if not (REPO / path).exists():
            ghosts.append(path)
    assert not ghosts, (
        "docs/file_structure.txt — which CLAUDE.md calls authoritative — has rows "
        "naming files that do not exist at the path the row reconstructs to:\n  "
        + "\n  ".join(ghosts)
        + "\n\nDelete the row, or move it under the directory the file is really "
          "in. Before moving it, check whether that directory is ROLLED UP: adding "
          "a per-file row to a rolled-up directory flips it to enumerated and "
          "`test_a_directory_the_map_ENUMERATES_is_enumerated_COMPLETELY` will then "
          "demand a row for every one of its files."
    )
    assert not bad_templates, (
        "these map rows are templates (`<…>` stands for a variable segment), so "
        "the file is not expected to exist — but the directory holding them does "
        "not exist either, which means the row points nowhere at all:\n  "
        + "\n  ".join(bad_templates)
    )


def test_the_TEMPLATE_exemption_is_only_what_it_says_it_is() -> None:
    """The control on the exemption above — it may not quietly become a hole.

    `<…>` is the map's own convention for a variable path segment, and it is the
    one shape that legitimately names no file. If a future row picked up angle
    brackets for some other reason, it would inherit the exemption silently, so
    the exempted set is pinned by name.
    """
    exempt = sorted(p for p in _mapped_paths() if TEMPLATE.search(p))
    # EMPTY since the research pools moved to the planning repo with the rest of
    # the prose. An empty exemption is the strictest state this can be in — every
    # row must name a real file — so it is pinned at `[]` rather than deleted:
    # the pin is what makes a NEW template row a decision instead of a default.
    assert exempt == [], (
        f"the set of template rows in the map changed: {exempt}. Each one is "
        f"exempt from the file-exists assertion, so a new member is a new hole — "
        f"confirm it really is a naming convention and not a typo, then add it here."
    )


def test_a_directory_the_map_ENUMERATES_is_enumerated_COMPLETELY() -> None:
    """A partially-listed directory reads as complete, and that is the defect.

    Nineteen of the twenty-three test modules under
    `scripts/workflows/temporal/tests/unit/` had their own annotated line; four
    did not, including one this PR modifies and names in a phase-doc checkbox. A
    reader scanning that block has no way to tell it is short.
    """
    holes = partially_listed(_mapped_paths(), tracked())
    assert not holes, (
        "docs/file_structure.txt enumerates these directories file by file and "
        "is missing entries in them:\n"
        + "\n".join(f"  {d}: {', '.join(m)}" for d, m in holes.items())
        + "\nAdd a line with an annotation in the voice of its neighbours, or — "
          "if the directory should be summarised instead — remove the per-file "
          "lines so it is rolled up honestly rather than listed incompletely."
    )


def test_every_tracked_file_is_REACHABLE_through_the_map() -> None:
    """The rolled-up half: a new subtree cannot appear with no mention at all."""
    mapped = _mapped_paths()
    unreachable = [
        str(p) for p in tracked()
        if p.name not in EXCLUDED_NAMES
        and str(p) not in mapped
        and not any(str(parent) in mapped for parent in p.parents
                    if str(parent) != ".")
    ]
    assert not unreachable, (
        "no entry in docs/file_structure.txt reaches these files — not their own "
        "line and not any ancestor directory:\n  " + "\n  ".join(unreachable)
    )


@pytest.mark.parametrize("path", [
    "docs/file_structure.txt",
    "CLAUDE.md",
])
def test_the_map_and_the_document_that_declares_it_authoritative_both_exist(
        path: str) -> None:
    """If either moves, this whole module is asserting against nothing."""
    assert (REPO / path).is_file()

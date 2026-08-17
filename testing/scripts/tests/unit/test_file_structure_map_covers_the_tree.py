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

import collections
import re
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[4]
_MAP = _REPO / "docs" / "file_structure.txt"

# A tree line's leaf: `│   ├── run_log.py    # annotation`. The captured PREFIX
# is what gives the depth — the map indents four characters per level — and the
# name carries a trailing slash on directory entries, stripped so `tests/`
# composes into a path segment.
#
# THIS GRAMMAR IS PARSED A SECOND TIME, and this note is the price of keeping
# the two parsers separate. `test_retired_vocabulary_is_gone_from_live_surfaces.py`
# reads the same map with its own copy of `_LEAF` and `_MAP_INDENT`, because it
# needs per-entry line numbers and leaf-plus-continuation joined text where this
# module needs only a `set` of paths. A change to the map's rendering — the
# indent width, the tree glyphs — has to move in BOTH. This file is the older
# and more discoverable of the two, so it is the one someone opens first.
_LEAF = re.compile(r"^(.*?)[├└]──\s+(\S+)")
_INDENT = 4

# `.gitkeep` holds an otherwise-empty directory open in git. The map documents
# the DIRECTORY, which is the thing a reader is looking for; a line for the
# placeholder would document the mechanism instead. Asserted below rather than
# assumed, so this exclusion cannot quietly grow.
_EXCLUDED_NAMES = frozenset({".gitkeep"})


def _tracked() -> list[Path]:
    out = subprocess.run(["git", "ls-files"], cwd=_REPO,
                         capture_output=True, text=True, check=True)
    return [Path(line) for line in out.stdout.split()]


def _mapped_paths() -> set[str]:
    """Every entry in the map, as a repo-relative path.

    The root line (`claude-dot-files/`) carries no `──` and is therefore not a
    level — which is what makes the reconstructed paths repo-relative and
    directly comparable to `git ls-files` output.
    """
    stack: dict[int, str] = {}
    paths = set()
    for line in _MAP.read_text().splitlines():
        found = _LEAF.match(line)
        if not found:
            continue
        level = len(found.group(1)) // _INDENT
        stack[level] = found.group(2).rstrip("/")
        for deeper in [k for k in stack if k > level]:
            del stack[deeper]
        paths.add("/".join(stack[k] for k in sorted(stack)))
    return paths


def test_the_exclusion_list_is_only_what_it_says_it_is() -> None:
    """The control on the control: an exclusion that grows silently is a hole."""
    excluded = {p for p in _tracked() if p.name in _EXCLUDED_NAMES}
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
    resolves = [p for p in paths if (_REPO / p).exists()]
    assert len(resolves) > 0.9 * len(paths), (
        f"only {len(resolves)} of {len(paths)} reconstructed paths exist on "
        f"disk — the indentation parse is wrong, or the map has drifted far "
        f"enough that this check is measuring the wrong thing. Sample of "
        f"non-resolving entries: {sorted(set(paths) - set(resolves))[:8]}"
    )


def test_a_directory_the_map_ENUMERATES_is_enumerated_COMPLETELY() -> None:
    """A partially-listed directory reads as complete, and that is the defect.

    Nineteen of the twenty-three test modules under
    `scripts/workflows/temporal/tests/unit/` had their own annotated line; four
    did not, including one this PR modifies and names in a phase-doc checkbox. A
    reader scanning that block has no way to tell it is short.
    """
    mapped = _mapped_paths()
    by_dir: dict[str, list[Path]] = collections.defaultdict(list)
    for path in _tracked():
        if path.name in _EXCLUDED_NAMES:
            continue
        by_dir[str(path.parent)].append(path)

    holes: dict[str, list[str]] = {}
    for directory, paths in sorted(by_dir.items()):
        listed = [p for p in paths if str(p) in mapped]
        missing = [p.name for p in paths if str(p) not in mapped]
        if listed and missing:
            holes[directory] = sorted(missing)
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
        str(p) for p in _tracked()
        if p.name not in _EXCLUDED_NAMES
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
    assert (_REPO / path).is_file()

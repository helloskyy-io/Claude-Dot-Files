"""Reading `docs/file_structure.txt` — the grammar, the tree, and the hole finder.

A HELPER MODULE AND NOT A TEST MODULE, because two test modules need this and
`test_test_tree_hygiene.test_no_test_module_imports_another_test_module` forbids
one importing the other. Its docstring states the remedy this file IS: *"a
component-prefixed helper module (Testing Standard § test-helper module names) or
a `conftest.py` fixture."* A fixture was the wrong shape — `map_paths` is a pure
function over text, and the discriminator controls in both consumers need to call
it on SYNTHETIC input rather than on whatever a fixture handed them.

THE TWO CONSUMERS AND WHY THEY ARE SEPARATE:

  * `test_file_structure_map_covers_the_tree.py` — the map may summarise but it
    may not silently OMIT, and where it enumerates it enumerates completely.
  * `test_planning_directories_are_ROLLED_UP_in_the_map.py` — a planning directory
    must be summarised rather than enumerated, so that a `plan-draft` run adding
    a phase doc cannot make the first module go red (C-pky2l2b6).

They are opposite ends of the same rule and both need the same parse, which is
exactly the consumer count that decides a promotion here.

THIS GRAMMAR IS STILL PARSED TWICE IN THE REPO, and the note that used to live in
the coverage module belongs here now. `test_retired_vocabulary_is_gone_from_live_
surfaces.py` reads the same map with its OWN copy of the leaf pattern and indent,
because it needs per-entry line numbers and leaf-plus-continuation joined text
where this module needs only paths. A change to the map's rendering — the indent
width, the tree glyphs — has to move in BOTH. This file is the more discoverable
of the two and is the one someone opens first.
"""

from __future__ import annotations

import collections
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
MAP = REPO / "docs" / "file_structure.txt"

import sys as _s  # noqa: E402
_s.path.insert(0, str(REPO / "scripts" / "workflows" / "temporal" / "tests"))
from planning_corpus import PLANNING_ROOT  # noqa: E402

#: The planning repo's own map. Each repo maps ITS OWN tree — the planning
#: directories this gate is about live there, so the gate reads that map.
PLANNING_MAP = PLANNING_ROOT / "docs" / "file_structure.txt"

# A tree line's leaf: `│   ├── run_log.py    # annotation`. The captured PREFIX is
# what gives the depth — the map indents four characters per level — and the name
# carries a trailing slash on directory entries, stripped so `tests/` composes
# into a path segment.
LEAF = re.compile(r"^(.*?)[├└]──\s+(\S+)")
INDENT = 4

# `.gitkeep` holds an otherwise-empty directory open in git. The map documents the
# DIRECTORY, which is the thing a reader is looking for; a line for the
# placeholder would document the mechanism instead. Asserted by its consumer
# rather than assumed, so this exclusion cannot quietly grow.
EXCLUDED_NAMES = frozenset({".gitkeep"})

# The map's own convention for a variable path segment: `raw/<topic>.md` names a
# naming rule, not a file.
TEMPLATE = re.compile(r"<[^>]+>")


def planning_tracked() -> list[str]:
    """`git ls-files` for the planning repo, as repo-relative strings."""
    out = subprocess.run(["git", "ls-files"], cwd=PLANNING_ROOT,
                         capture_output=True, text=True, check=True).stdout
    return [line for line in out.split("\n") if line]


def tracked() -> list[Path]:
    """Every file git tracks, as repo-relative paths.

    THE POPULATION IS READ FROM `git ls-files` AND NOT FROM THE MAP, which is the
    whole method: a table checked against itself cannot see the entry that was
    never added to it.
    """
    out = subprocess.run(["git", "ls-files"], cwd=REPO,
                         capture_output=True, text=True, check=True)
    return [Path(line) for line in out.stdout.split()]


def map_entries(text: str) -> dict[str, bool]:
    """Every entry in the map, as a repo-relative path -> "is a directory".

    TAKES TEXT RATHER THAN READING THE FILE, so a discriminator control can feed
    it a self-contained sample. A control that shares a fixture with the code
    under test over-fires and proves nothing about either.

    The root line (`claude-dot-files/`) carries no `──` and is therefore not a
    level — which is what makes the reconstructed paths repo-relative and directly
    comparable to `git ls-files` output.

    DIRECTORY-NESS COMES FROM THE TRAILING SLASH the map writes, not from what is
    on disk, because one consumer is precisely about entries whose disk
    counterpart does not exist. Measured on the whole map: 254 file entries and 60
    directory entries, with ZERO disagreements against disk on the entries that do
    resolve — so the convention is reliable enough to key an assertion on.

    MATCHED BY RECONSTRUCTED PATH, NOT BY LEAF NAME, and the difference decided
    what these checks demand. A full path never appears on any one line of the map
    — the tree renders it across nested lines — so the obvious implementations
    both fail in opposite directions: grepping for the path reads 0 against a
    correctly nested entry, and matching bare leaf names counts a directory as
    enumerated because some UNRELATED directory elsewhere happens to list a file
    of the same name. The second is not hypothetical: under leaf matching, two
    `prompts/` directories the map deliberately rolls up were scored as enumerated
    on the strength of a `rules.md` entry sitting under `docs/standards/`. So the
    indentation is parsed back into paths, and a directory is enumerated only when
    a file at that ACTUAL path has a line.
    """
    stack: dict[int, str] = {}
    entries: dict[str, bool] = {}
    for line in text.splitlines():
        found = LEAF.match(line)
        if not found:
            continue
        level = len(found.group(1)) // INDENT
        leaf = found.group(2)
        stack[level] = leaf.rstrip("/")
        for deeper in [k for k in stack if k > level]:
            del stack[deeper]
        entries["/".join(stack[k] for k in sorted(stack))] = leaf.endswith("/")
    return entries


def map_paths(text: str) -> set[str]:
    """Every entry in the map, as a repo-relative path."""
    return set(map_entries(text))


def partially_listed(mapped: set[str], files: list[Path]) -> dict[str, list[str]]:
    """Directories the map lists SOME of, keyed to the names it is missing.

    A partially-listed directory reads as complete, and that is the defect. Pure
    over both inputs so a caller can drive it with a synthetic tree — which is how
    the roll-up guard reproduces C-pky2l2b6's red-on-add without touching the repo.
    """
    by_dir: dict[str, list[Path]] = collections.defaultdict(list)
    for path in files:
        if path.name in EXCLUDED_NAMES:
            continue
        by_dir[str(path.parent)].append(path)

    holes: dict[str, list[str]] = {}
    for directory, paths in sorted(by_dir.items()):
        listed = [p for p in paths if str(p) in mapped]
        missing = [p.name for p in paths if str(p) not in mapped]
        if listed and missing:
            holes[directory] = sorted(missing)
    return holes

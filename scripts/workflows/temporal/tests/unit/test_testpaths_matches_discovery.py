"""`pytest.ini`'s `testpaths` must list every component `tests/` directory
`testing/suites/python.sh` discovers.

WHY THIS EXISTS. `testpaths` is a hand-maintained mirror of what `python.sh`
finds by walking the tree, and nothing asserted they agreed — this PR is what
turned it from a single entry into a list, which is exactly when a mirror
starts drifting. When a third component grows a `tests/` directory, a bare
`pytest` invocation silently covers LESS than `run-all.sh` while both report
green, and this repo's own PR bodies lean on bare `pytest` reporting the same
total as `run-all.sh` as corroborating evidence — a drifted `testpaths` would
falsify that check too, without anything noticing.

WHY DISCOVERY IS RE-IMPLEMENTED HERE RATHER THAN SHELLED OUT TO python.sh.
`python.sh` only reports the directories it discovers as a side effect of
actually RUNNING pytest against them, which would mean nesting a nested pytest
invocation over the whole real repo just to read a file list — slow, and
coupled to every suite's runtime rather than to discovery. `test_runner_discovery.py`
takes that cost on purpose because its property (a rejected orphan) is a
behaviour of the bash script itself. This property is a relationship between
two on-disk lists; scanning the real tree directly, mirroring `python.sh`'s
own prune rules, is precedented by `test_model_keys_resolve.py`, which compares
`config.yaml` against a live sweep of the assistant tree the same way.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
PYTEST_INI = REPO_ROOT / "pytest.ini"

# Mirrors testing/suites/python.sh's PRUNE array. Anchored the same way that
# file anchors it: a mismatch here would make this test disagree with the
# runner about what the tree contains, which is the exact failure this test
# exists to catch, one level up.
_PRUNE_DIR_NAMES = {".git", ".claude", "archive", "__pycache__", "node_modules", "site-packages", ".venv", "venv"}
_CATEGORIES = ("unit", "integration", "e2e")


def _discovered_component_test_dirs() -> set[str]:
    """Every component `tests/` directory holding a `unit/`, `integration/`,
    or `e2e/` subdirectory — i.e. what `python.sh` discovers, one level up
    from the category directories it globs for.
    """
    found: set[str] = set()
    for path in REPO_ROOT.rglob("tests"):
        if not path.is_dir():
            continue
        if any(part in _PRUNE_DIR_NAMES for part in path.relative_to(REPO_ROOT).parts):
            continue
        if any((path / category).is_dir() for category in _CATEGORIES):
            found.add(path.relative_to(REPO_ROOT).as_posix())
    return found


def _declared_testpaths(ini_text: str) -> set[str]:
    """Parses the `testpaths` value out of an ini file's `[pytest]` section.

    A dumb line scanner, in the same spirit as `_extract_patterns` in the
    block-dangerous test suite: `testpaths` is a multi-line ini value, one
    path per line, indented under the key.
    """
    paths: set[str] = set()
    in_testpaths = False
    for line in ini_text.splitlines():
        if re.match(r"^testpaths\s*=", line):
            in_testpaths = True
            _, _, rest = line.partition("=")
            rest = rest.strip()
            if rest:
                paths.add(rest)
            continue
        if in_testpaths:
            if line.strip() and not line[:1].isspace():
                in_testpaths = False
                continue
            stripped = line.strip()
            if stripped:
                paths.add(stripped)
    return paths


def test_pytest_ini_is_findable_from_the_test_suite() -> None:
    """Guards the path, not the content — see test_config_is_findable_from_the_test_suite
    in test_model_keys_resolve.py for why this class of guard exists."""
    assert PYTEST_INI.is_file(), f"{PYTEST_INI} is missing — pytest.ini moved"


def test_at_least_one_component_test_dir_was_discovered() -> None:
    """Positive control on the scanner.

    A prune rule that swallowed everything would make the main test below
    vacuously pass — no discovered dirs means no possible mismatch. This repo
    has component test directories today; the assertion is only that the scan
    finds SOME, so adding or removing a component does not make this test
    wrong.
    """
    assert _discovered_component_test_dirs(), (
        "no component tests/ directories were discovered under "
        f"{REPO_ROOT} — the scan is inert, which is indistinguishable from "
        "testpaths correctly covering everything"
    )


def test_declared_testpaths_parses_the_known_entries() -> None:
    """Positive control on the parser, independent of the live file's content.

    Pins the parser against a synthetic ini fragment so a change to pytest.ini
    itself cannot make this test wrong in the direction of hiding a parser
    bug — see test_a_missing_key_is_actually_detected in
    test_model_keys_resolve.py for the same reasoning applied to a predicate.
    """
    sample = (
        "[pytest]\n"
        "testpaths =\n"
        "    scripts/workflows/temporal/tests\n"
        "    testing/config-hooks/tests\n"
        "python_files = test_*.py\n"
    )
    assert _declared_testpaths(sample) == {
        "scripts/workflows/temporal/tests",
        "testing/config-hooks/tests",
    }


def test_testpaths_covers_every_directory_python_sh_discovers() -> None:
    """The binding property: nothing `python.sh` discovers may be absent from
    `pytest.ini`'s `testpaths`.

    A bare `pytest` invocation only sees `testpaths`. If this test is red, a
    contributor's local `pytest` run — and any CI step that runs bare
    `pytest` instead of `run-all.sh` — silently covers less than the master
    runner while both report green.
    """
    discovered = _discovered_component_test_dirs()
    declared = _declared_testpaths(PYTEST_INI.read_text())
    missing = sorted(discovered - declared)
    assert not missing, (
        f"{missing} hold test categories that testing/suites/python.sh "
        f"discovers, but are not listed in pytest.ini's testpaths. A bare "
        f"`pytest` invocation will silently cover less than `run-all.sh` "
        f"while both report green. Add the missing path(s) to testpaths."
    )

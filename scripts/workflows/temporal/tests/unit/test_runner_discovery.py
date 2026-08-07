"""The pytest suite runner refuses to run while an orphaned test file exists.

Testing Standard § Discovery completeness (ratified 2026-07-24): a test that
exists outside `run-all.sh` discovery is a defect. § Purpose says the same thing
about orphaned test files directly.

The runner discovers `*/tests/<category>/` and nothing else, so a `test_*.py`
one directory too high is not merely unrun — it is unreported. The file count
the runner prints excludes it, the summary table says PASS, and a reader has no
signal that anything was skipped. `tests/test_build_helper.py` and
`tests/test_v1_parity.py` sat in exactly that state on `main`.

WHY THIS TEST SHELLS OUT. The property is a behaviour of a bash script, so
inspecting its source would only prove the text is present, not that the run
FAILS. Every check below therefore executes the real runner against a synthetic
tree — the guard is demonstrated, not asserted about. The tree is synthetic
rather than this repo's own because the runner derives its root from its own
location: copied into `tmp_path`, its root IS `tmp_path`, so nothing it sees can
depend on the state of the checkout the test happens to run in.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
RUNNER = REPO_ROOT / "testing" / "suites" / "python.sh"

_TRIVIAL_TEST = "def test_ok() -> None:\n    assert True\n"


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    """A minimal tree holding the real runner and one properly-placed unit test.

    Only the runner is copied. Copying the whole repo would make the fixture's
    behaviour depend on whatever else the checkout contains, which is the
    coupling this test exists to avoid.
    """
    suites = tmp_path / "testing" / "suites"
    suites.mkdir(parents=True)
    shutil.copy2(RUNNER, suites / "python.sh")

    unit = tmp_path / "component" / "tests" / "unit"
    unit.mkdir(parents=True)
    (unit / "test_placed_correctly.py").write_text(_TRIVIAL_TEST)

    return tmp_path


# Wall-clock backstop. Each sandbox run is a bash script plus a one-file pytest
# invocation — sub-second in practice. The bound exists because this call spawns
# a NESTED pytest: without it, a hang in the child (a stuck import, a prompt for
# input on a tty-less runner) wedges the parent suite indefinitely rather than
# failing it, and this suite is what gates autonomous dispatch.
_RUNNER_TIMEOUT_S = 120


def _run(sandbox: Path, category: str = "unit") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(sandbox / "testing" / "suites" / "python.sh"), category],
        capture_output=True,
        text=True,
        check=False,
        cwd=sandbox,
        timeout=_RUNNER_TIMEOUT_S,
    )


def test_the_runner_under_test_is_the_one_this_repo_ships() -> None:
    """Guards the fixture, not the runner.

    If `python.sh` is ever moved or renamed, every check below would otherwise
    fail with a copy error that says nothing about discovery.
    """
    assert RUNNER.is_file(), f"{RUNNER} is missing — the suite runner moved"


def test_a_correctly_placed_tree_passes(sandbox: Path) -> None:
    """Negative control: the guard does not fire on a conforming tree.

    Without this, a guard that rejected EVERY tree would pass the orphan check
    below while making the runner useless.
    """
    result = _run(sandbox)
    assert result.returncode == 0, (
        f"a conforming tree was rejected (exit {result.returncode}):\n"
        f"{result.stdout}\n{result.stderr}"
    )
    assert "sit outside" not in result.stderr


def test_an_orphaned_test_file_fails_the_run(sandbox: Path) -> None:
    """The binding property: a test one directory too high makes the run FAIL."""
    orphan = sandbox / "component" / "tests" / "test_orphaned.py"
    orphan.write_text(_TRIVIAL_TEST)

    result = _run(sandbox)

    assert result.returncode == 1, (
        f"an orphaned test file did not fail the run (exit {result.returncode}). "
        "Silent exclusion is the whole defect: the summary reports PASS while the "
        f"file never executes.\n{result.stdout}\n{result.stderr}"
    )
    assert "component/tests/test_orphaned.py" in result.stderr, (
        "the run failed but did not name the orphan — an operator cannot act on "
        f"a failure that does not say which file:\n{result.stderr}"
    )


def test_an_orphan_fails_even_when_it_is_the_only_test(tmp_path: Path) -> None:
    """The orphan check must precede the exit-3 "nothing to run" return.

    Ordered after it, a tree whose ONLY test files are orphaned would report
    SKIP — the most misleading outcome available, because SKIP is how the runner
    truthfully says "this repo has no integration tier".
    """
    suites = tmp_path / "testing" / "suites"
    suites.mkdir(parents=True)
    shutil.copy2(RUNNER, suites / "python.sh")

    tests_dir = tmp_path / "component" / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_only_and_orphaned.py").write_text(_TRIVIAL_TEST)

    result = _run(tmp_path)

    assert result.returncode == 1, (
        f"expected exit 1, got {result.returncode} — exit 3 here would surface as "
        f"SKIP in the summary table while a real test file went unrun.\n{result.stderr}"
    )


@pytest.mark.skipif(
    os.geteuid() == 0,
    reason="root bypasses the permission bits this test uses to make find fail; "
    "the property is real but cannot be exercised as root",
)
def test_a_partial_tree_walk_fails_the_run(sandbox: Path) -> None:
    """A `find` that cannot finish must not be reported as a completed scan.

    Process substitution (`mapfile -t X < <(find ...)`) discards the subshell's
    exit status, so an unreadable directory used to yield a PARTIAL walk that
    both scans treated as the whole tree. The dangerous half is the suite scan:
    truncated to empty, it takes the exit-3 "nothing to run" path, which the
    master runner renders as SKIP — "nothing to run" printed over tests that
    exist, which is the same silent green the orphan guard above exists to stop.
    """
    unreadable = sandbox / "component" / "unreadable"
    unreadable.mkdir(parents=True)
    unreadable.chmod(0o000)
    try:
        result = _run(sandbox)
    finally:
        # Restore before pytest's tmp_path cleanup, which cannot remove 0o000.
        unreadable.chmod(0o755)

    assert result.returncode == 1, (
        f"a partial tree walk did not fail the run (exit {result.returncode}). "
        "A scan that could not finish must never be reported as a completed one.\n"
        f"{result.stdout}\n{result.stderr}"
    )
    assert "could not walk the tree" in result.stderr, (
        "the run failed but did not say the walk was partial, so an operator "
        f"would chase the wrong cause:\n{result.stderr}"
    )


def test_a_test_file_in_another_category_is_not_an_orphan(sandbox: Path) -> None:
    """The scan asks "inside ANY category directory", never "inside THIS one".

    A category-scoped scan would flag every unit test during the integration
    pass, and the guard would be untrustworthy enough to be disabled.
    """
    integration = sandbox / "component" / "tests" / "integration"
    integration.mkdir(parents=True)
    (integration / "test_elsewhere.py").write_text(_TRIVIAL_TEST)

    result = _run(sandbox, category="unit")

    assert result.returncode == 0, (
        "an integration-tier test was treated as an orphan during the unit pass:\n"
        f"{result.stderr}"
    )

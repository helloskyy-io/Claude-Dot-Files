"""`run-all.sh` reports the truth about whether anything actually passed.

WHY THIS EXISTS. `run-all.sh` is the single thing that decides PASSED or FAILED
for the whole repo, and it is what issue #30's merge gate will call. Its own
source records that the wrong form of this logic already shipped once:

    `|| true` runs a simple command, which resets PIPESTATUS to (0), so every
    failing suite reads back as exit 0. This runner shipped that bug for exactly
    one test run and reported "RESULT: PASSED" over a red pytest suite.

A green report over a red suite is the worst failure this repo can have, because
every downstream gate trusts it. Tier 2's runner got a six-test harness for this
same reason (`test_runner_discovery.py`); until now Tier 1 had none, and its
three result branches were verified only by a one-off demonstration in a PR
body. A demonstration that happened once in a log is the convention-not-a-gate
shape this repo keeps rejecting.

WHY THIS SHELLS OUT. The property is a behaviour of a bash script. Inspecting
its source would prove the text is present, not that the run FAILS — and the
PIPESTATUS bug above was a case where the text looked right. Every check
executes the real runner against a synthetic tree.

WHY THE TREE IS SYNTHETIC. `run-all.sh` derives its root from its own location,
so a copy in `tmp_path` roots there. Nothing it sees depends on the state of the
checkout the test happens to run in — the same isolation `test_runner_discovery`
uses, and for the same reason.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
MASTER = REPO_ROOT / "testing" / "run-all.sh"
SUITE = REPO_ROOT / "testing" / "suites" / "python.sh"

_PASSING_TEST = "def test_ok() -> None:\n    assert True\n"
_FAILING_TEST = "def test_red() -> None:\n    assert False, 'deliberately red'\n"

# Wall-clock backstop. Each run is two bash scripts plus a one-file pytest
# invocation — sub-second in practice. The bound exists because this spawns a
# NESTED pytest: without it a wedged child hangs the parent suite indefinitely
# rather than failing it, and this suite is what gates autonomous dispatch.
_TIMEOUT_S = 180


def _tree(tmp_path: Path, *, tests: dict[str, str] | None = None) -> Path:
    """A minimal tree holding both real runners and whatever tests are asked for.

    Only the runners are copied. Copying the repo would make every assertion
    depend on what else the checkout contains, which is the coupling this
    fixture exists to avoid.
    """
    suites = tmp_path / "testing" / "suites"
    suites.mkdir(parents=True)
    shutil.copy2(MASTER, tmp_path / "testing" / "run-all.sh")
    shutil.copy2(SUITE, suites / "python.sh")

    for rel, body in (tests or {}).items():
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
    return tmp_path


def _run(tree: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(tree / "testing" / "run-all.sh"), *args],
        capture_output=True, text=True, check=False, cwd=tree, timeout=_TIMEOUT_S,
    )


def test_the_runners_under_test_are_the_ones_this_repo_ships() -> None:
    """Guards the fixture, not the runner.

    If either script moves, the checks below would otherwise fail with a copy
    error that says nothing about result reporting.
    """
    assert MASTER.is_file(), f"{MASTER} is missing — the master runner moved"
    assert SUITE.is_file(), f"{SUITE} is missing — the suite runner moved"


def test_a_green_tree_reports_passed(tmp_path: Path) -> None:
    """Negative control.

    Without this, a runner that reported FAILED unconditionally would satisfy
    the red-suite check below while being useless.
    """
    tree = _tree(tmp_path, tests={"component/tests/unit/test_ok.py": _PASSING_TEST})
    result = _run(tree, "unit")
    assert result.returncode == 0, f"a green tree was reported as failing:\n{result.stdout}\n{result.stderr}"
    assert "RESULT: PASSED" in result.stdout


def test_a_red_suite_reports_failed_and_exits_nonzero(tmp_path: Path) -> None:
    """THE regression test. This is the bug that actually shipped.

    A failing pytest run must reach the summary as FAIL and the process must
    exit non-zero. The PIPESTATUS form that shipped satisfied neither while
    printing a clean summary table.
    """
    tree = _tree(tmp_path, tests={"component/tests/unit/test_red.py": _FAILING_TEST})
    result = _run(tree, "unit")
    assert result.returncode != 0, (
        f"a RED suite exited 0 — this is the PIPESTATUS bug returning:\n{result.stdout}"
    )
    assert "RESULT: PASSED" not in result.stdout, "a red suite was reported as passed"
    assert "RESULT: FAILED" in result.stdout
    assert "FAIL" in result.stdout, "the red suite did not reach the summary table as FAIL"


def test_a_tree_with_no_tests_is_fatal_not_green(tmp_path: Path) -> None:
    """Every suite skipped must FAIL, never report a green run.

    Exiting zero here would report full green for a repo in which nothing
    executed — the failure Testing Standard § Tier Enforcement names directly.
    """
    result = _run(_tree(tmp_path), "unit")
    assert result.returncode != 0, f"a tree with no tests at all exited 0:\n{result.stdout}"
    assert "FATAL: no test suite actually ran" in result.stderr
    assert "RESULT: PASSED" not in result.stdout


def test_an_absent_category_reports_skip_and_does_not_count_as_a_run(tmp_path: Path) -> None:
    """A skip is reported, and a skip alone is not a pass.

    The suite runner's exit 3 means "category absent". It must surface as SKIP
    in the table — a silent skip and a pass look identical to a reader — and it
    must not satisfy the did-anything-run check on its own.
    """
    tree = _tree(tmp_path, tests={"component/tests/unit/test_ok.py": _PASSING_TEST})
    result = _run(tree, "integration")
    assert "SKIP" in result.stdout, f"an absent category was not reported as SKIP:\n{result.stdout}"
    assert result.returncode != 0, "a run where only skips occurred reported success"
    assert "FATAL: no test suite actually ran" in result.stderr


def test_a_red_suite_is_not_masked_by_a_green_one(tmp_path: Path) -> None:
    """One failure anywhere fails the whole run.

    The loop collects results rather than aborting, so the risk is the opposite
    of an early exit: a later green suite overwriting an earlier red verdict.
    """
    tree = _tree(tmp_path, tests={
        "alpha/tests/unit/test_red.py": _FAILING_TEST,
        "beta/tests/unit/test_ok.py": _PASSING_TEST,
    })
    result = _run(tree, "unit")
    assert result.returncode != 0, f"a red suite was masked by a green one:\n{result.stdout}"
    assert "RESULT: FAILED" in result.stdout

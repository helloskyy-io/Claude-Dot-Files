"""Preconditions fail BEFORE anything is created.

Two failures shared one shape: the run got far enough to create a worktree and
then died, leaving it orphaned on disk with nothing pointing at it.

  A missing dependency crashed mid-run, and the traceback named an import
  rather than the invocation (#49).

  Six of seven entrypoints rooted on `Path.cwd()`, so invoking from a
  subdirectory put `.claude/worktrees/` and `.claude/logs/` inside it, where
  cleanup never looks and a later sweep deletes the logs with the workspace
  (#48).

Both are cheapest to catch before the first side effect, which is what this
module exists to guarantee.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from preflight import preflight, require_dependencies, resolve_repo_root

REPO_ROOT = Path(__file__).resolve().parents[5]


def test_a_subdirectory_resolves_to_the_repo_root() -> None:
    """THE #48 regression. `Path.cwd()` would return the subdirectory."""
    deep = REPO_ROOT / "scripts" / "workflows" / "temporal" / "scripts"
    assert deep.is_dir(), "fixture path moved"
    assert resolve_repo_root(str(deep)) == REPO_ROOT


def test_the_repo_root_resolves_to_itself() -> None:
    """Negative control: the common case must not be broken by the fix."""
    assert resolve_repo_root(str(REPO_ROOT)) == REPO_ROOT


def test_outside_a_repository_raises_with_a_usable_message(tmp_path: Path) -> None:
    """It must say what to do, not just that something went wrong.

    An operator reading this has passed the wrong `--repo` or is standing in
    the wrong directory; both are one action away from fixed.
    """
    with pytest.raises(RuntimeError) as exc:
        resolve_repo_root(str(tmp_path))
    assert "not inside a git repository" in str(exc.value)
    assert "--repo" in str(exc.value), "the message does not name the remedy"


def test_a_missing_dependency_raises_before_anything_runs() -> None:
    """THE #49 regression, checked on a package that cannot exist."""
    with pytest.raises(RuntimeError) as exc:
        require_dependencies(("a_package_that_does_not_exist_anywhere",))
    assert "missing required package" in str(exc.value)
    assert "Nothing was created" in str(exc.value)


def test_the_real_dependencies_are_present() -> None:
    """Positive control. A check that always raised would pass the test above."""
    require_dependencies()


def test_dependencies_are_checked_BEFORE_the_repository(tmp_path: Path) -> None:
    """Order matters: fail on the cheaper, more actionable problem first.

    Outside a repo AND missing a package, the operator should be told about the
    package — it needs no repository to fix, so reporting the other first makes
    them solve two things one at a time.
    """
    import preflight as pf
    original = pf._REQUIRED
    pf._REQUIRED = ("a_package_that_does_not_exist_anywhere",)
    try:
        with pytest.raises(RuntimeError) as exc:
            preflight(str(tmp_path))
        assert "missing required package" in str(exc.value)
    finally:
        pf._REQUIRED = original


def test_every_entrypoint_actually_calls_preflight() -> None:
    """The fix is worthless in the six files that forget it.

    Discovered rather than listed — a new entrypoint is covered the day it
    lands, which is the same reason the isolation net stopped being a hand list.
    """
    scripts = sorted((REPO_ROOT / "scripts" / "workflows" / "temporal" / "scripts").glob("run_*.py"))
    assert scripts, "no entrypoints discovered — the sweep is inert"
    missing = [s.name for s in scripts if "preflight(" not in s.read_text()]
    assert not missing, f"entrypoints that can still strand a worktree: {missing}"


def test_no_entrypoint_roots_on_the_invocation_directory() -> None:
    """`Path.cwd()` as a repo root is the #48 defect itself."""
    scripts = sorted((REPO_ROOT / "scripts" / "workflows" / "temporal" / "scripts").glob("run_*.py"))
    offenders = [s.name for s in scripts
                 if "repo_root = Path(" in s.read_text() and "Path.cwd()" in s.read_text()]
    assert not offenders, f"these root on the invocation dir rather than the repo: {offenders}"

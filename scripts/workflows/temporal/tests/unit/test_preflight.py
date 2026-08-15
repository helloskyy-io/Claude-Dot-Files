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

import ast
import subprocess
from pathlib import Path

import pytest

from preflight import (preflight, require_dependencies, resolve_operator_paths,
                       resolve_repo_root)

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


def test_no_entrypoint_INLINES_the_operator_path_escape_check() -> None:
    """THE CLASS: a path-escape check on operator input has ONE implementation.

    KEYED ON THE CHECK, NOT ON THE TWO RUNNERS THAT HAPPENED TO CARRY IT. Two
    entrypoints held this block byte-identically — resolve against the repo,
    refuse what is not `is_relative_to` it, refuse what does not exist. Listing
    those two and calling it done leaves the third copy to be written by whoever
    adds the next runner, and it will be written from one of the two rather than
    from whichever has been hardened since.

    THE DRIFT IS ONE-DIRECTIONAL AND INVISIBLE, which is what makes this worth a
    sweep rather than a review note. Symlink resolution, a denylist, a `.git`
    check — every future tightening lands in the entrypoint the author had open.
    The other keeps accepting what the first now refuses, both files still read
    as careful, and no diff shows the divergence because neither changed.

    WHAT THIS DOES NOT LOOK AT, so it is not read as covering more than it does:

      * It does not check that the entrypoint validates the RIGHT paths. A
        runner that resolves `component` and forgets `--candidates` passes here;
        `resolve_operator_paths` is a mechanism, not a policy.
      * It does not reach `is_relative_to` anywhere but the entrypoints. A
        workflow module doing its own escape check is a different question, and
        `boundary_crossings` is the mechanism for that altitude.
      * It cannot see a runner that takes an operator path and checks NOTHING.
        That is the more dangerous state and it is invisible to this sweep,
        because the absence of a check has no syntax.

    READ BY AST, NOT BY SUBSTRING, AND THAT IS NOT FASTIDIOUSNESS. This check
    was first written as `"is_relative_to" in text and "resolve_operator_paths"
    not in text`, and a mutation control put the inline block back into
    `run_plan_feature.py` and the sweep STAYED GREEN — because the comment above
    the call still said *"see `resolve_operator_paths` for why two copies of a
    boundary check drift"*. The prose explaining the rule satisfied the check for
    the rule. A guard reading a region that includes its own documentation
    reports on the documentation, and it does so silently.
    """
    scripts_dir = REPO_ROOT / "scripts" / "workflows" / "temporal" / "scripts"
    scripts = sorted(scripts_dir.glob("run_*.py"))
    assert scripts, "no entrypoints discovered — the sweep is inert"

    def inlines_the_check(path: Path) -> bool:
        tree = ast.parse(path.read_text())
        uses = any(isinstance(n, ast.Attribute) and n.attr == "is_relative_to"
                   for n in ast.walk(tree))
        calls = any(isinstance(n, ast.Call)
                    and (getattr(n.func, "id", None) == "resolve_operator_paths"
                         or getattr(n.func, "attr", None) == "resolve_operator_paths")
                    for n in ast.walk(tree))
        return uses and not calls

    offenders = [s.name for s in scripts if inlines_the_check(s)]
    assert not offenders, (
        f"these entrypoints inline their own operator-path escape check instead "
        f"of calling `preflight.resolve_operator_paths`: {offenders}. §10.1 rule "
        f"3 is mechanical — the consumer count decides — and a second copy of a "
        f"boundary check is the shape that drifts with nothing in a diff to show "
        f"for it.")


def test_the_shared_resolver_refuses_an_escape_and_a_missing_path(tmp_path: Path) -> None:
    """The promotion PINNED, so it is a behaviour rather than a refactor.

    Both messages are asserted because they are the diagnostics: an operator who
    typed `../../elsewhere` needs to be told it escaped, not that it is missing.
    """
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "c.md").write_text("x")

    with pytest.raises(RuntimeError) as escape:
        resolve_operator_paths(tmp_path, {"component": "../outside"})
    assert "resolves outside the repo" in str(escape.value)
    assert "component ../outside" in str(escape.value), "the message must echo the ARGUMENT"

    with pytest.raises(RuntimeError) as missing:
        resolve_operator_paths(tmp_path, {"candidates": "docs/nope.md"})
    assert "candidates not found" in str(missing.value)

    with pytest.raises(RuntimeError) as not_a_dir:
        resolve_operator_paths(tmp_path, {"component": "docs/c.md"},
                               directories=("component",))
    assert "component is not a directory" in str(not_a_dir.value)

    ok = resolve_operator_paths(tmp_path, {"component": "docs", "candidates": "docs/c.md"},
                                directories=("component",))
    assert ok == {"component": tmp_path / "docs", "candidates": tmp_path / "docs" / "c.md"}


def test_an_ESCAPE_is_reported_before_a_MISSING_path(tmp_path: Path) -> None:
    """The three passes run in order, and the order is operator-facing.

    An escaping path does not exist either, so a resolver that checked existence
    first would report `not found` for `../../elsewhere` — sending the operator
    to create a directory rather than to fix the argument. Both entrypoints
    ordered it this way and the promotion has to keep it.
    """
    with pytest.raises(RuntimeError) as exc:
        resolve_operator_paths(tmp_path, {"component": "../outside/nothing"})
    assert "resolves outside the repo" in str(exc.value)
    assert "not found" not in str(exc.value)

"""Checks every entrypoint runs BEFORE it cuts a worktree or spends a token.

Promoted here because seven entrypoints needed the same two checks and one of
them had already implemented both correctly. Consumer count decides.

NOTHING HERE CALLS A MODEL. These are the cheapest possible failures: a bad
invocation should cost a second and a clear message, never a stranded worktree
or a burned budget.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

__all__ = ["resolve_repo_root", "require_dependencies", "preflight",
           "resolve_operator_paths"]

# Every workflow imports these. A missing one is not a crash mid-run — it is a
# crash AFTER the worktree exists, which is how a stranded worktree happens.
_REQUIRED = ("yaml",)


def resolve_repo_root(repo_target: str | None) -> Path:
    """The repository ROOT, never the directory the operator happened to be in.

    V1 did `REPO_ROOT="$(git rev-parse --show-toplevel)"; cd "$REPO_ROOT"` and
    USED the answer rather than just its exit code. Six of seven V2 entrypoints
    dropped that and kept `Path.cwd()`.

    It matters because everything downstream hangs off this path: `.claude/
    worktrees/` and `.claude/logs/` both do. Invoked from a subdirectory — say
    `scripts/workflows/temporal/` — a cwd-rooted run scatters worktrees and logs
    into that subdirectory, where `/cleanup-merged-worktrees` never looks and
    where a later cleanup deletes the logs along with the workspace. Cost
    accounting for those runs is then unrecoverable.
    """
    invoked_from = Path(repo_target) if repo_target else Path.cwd()
    probe = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=str(invoked_from), capture_output=True, text=True,
    )
    if probe.returncode != 0:
        raise RuntimeError(
            f"not inside a git repository: {invoked_from}\n"
            f"Run from a repo, or pass --repo <path-to-repo>."
        )
    return Path(probe.stdout.strip())


def require_dependencies(names: tuple[str, ...] | None = None) -> None:
    """Fail on a missing import BEFORE anything is created.

    A dependency that is missing surfaces halfway through a run — after the
    worktree exists, after the branch is cut — and the traceback names an import
    rather than the invocation. The worktree is then orphaned on disk with
    nothing pointing at it.

    Checked by spec lookup rather than by importing: this must not execute
    module-level code as a side effect of a precondition check.
    """
    # Read at CALL time, not bound as a default: a default argument is
    # evaluated once at definition, which made the module-level list
    # impossible to override and the function impossible to test.
    names = _REQUIRED if names is None else names
    missing = [n for n in names if importlib.util.find_spec(n) is None]
    if missing:
        raise RuntimeError(
            f"missing required package(s): {', '.join(missing)}\n"
            f"Install them into the interpreter running this workflow "
            f"({sys.executable}), then re-run. Nothing was created."
        )


def resolve_operator_paths(repo_root: Path, paths: dict[str, str],
                           directories: tuple[str, ...] = ()) -> dict[str, Path]:
    """Resolve free-form operator paths against the repo, and refuse the escapes.

    PROMOTED HERE BECAUSE TWO ENTRYPOINTS CARRIED IT BYTE-IDENTICALLY, which is
    the whole test §10.1 rule 3 applies — *"if and only if more than one workflow
    uses it… the consumer count decides, never taste."* It is not a tidiness
    promotion: this block is what stops `../../elsewhere` sending a run to write
    outside the tree it was pointed at, and **two copies of a boundary check
    drift in one direction only**. The next hardening — symlink resolution, a
    denylist, a `.git` check — lands in whichever entrypoint the author had open,
    and the other keeps accepting what the first now refuses, with nothing in any
    diff to show for it.

    THE ORDER OF THE THREE PASSES IS OPERATOR-FACING BEHAVIOUR, not an
    implementation detail, so it is preserved exactly: every escape is reported
    before any absence, and the directory check comes last. An operator who
    passed two bad paths gets told about the more serious problem with both of
    them rather than about the first one twice.

    RAISES `RuntimeError` LIKE ITS NEIGHBOURS, so a caller can catch this and
    `preflight` in one clause and print one way. The messages are the diagnostics
    and are carried over verbatim from the entrypoints — rewording them would
    make a behaviour-preserving promotion a behaviour change.

    `directories` NAMES THE LABELS THAT MUST BE A DIRECTORY, rather than being
    inferred from the name: `component` is a directory and `candidates` is a
    file, and a helper that guessed from the label would be wrong the first time
    somebody passes `--research`.
    """
    resolved = {label: (repo_root / arg).resolve() for label, arg in paths.items()}

    for label, arg in paths.items():
        if not resolved[label].is_relative_to(repo_root):
            raise RuntimeError(
                f"{label} {arg} resolves outside the repo: {resolved[label]}")
    for label, path in resolved.items():
        if not path.exists():
            raise RuntimeError(f"{label} not found: {path}")
    for label in directories:
        if not resolved[label].is_dir():
            raise RuntimeError(f"{label} is not a directory: {resolved[label]}")
    return resolved


def preflight(repo_target: str | None) -> Path:
    """Both checks, in the order that fails cheapest first. Returns repo_root.

    Dependencies before git: a missing package is a one-line fix and needs no
    repository at all, so discovering it first saves the operator from fixing
    two things one at a time.
    """
    require_dependencies()
    return resolve_repo_root(repo_target)

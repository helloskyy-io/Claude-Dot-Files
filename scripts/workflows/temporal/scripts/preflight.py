"""Checks every entrypoint runs BEFORE it cuts a worktree or spends a token.

Promoted here because seven entrypoints needed the same two checks and one of
them had already implemented both correctly. Consumer count decides.

NOTHING HERE CALLS A MODEL. These are the cheapest possible failures: a bad
invocation should cost a second and a clear message, never a stranded worktree
or a burned budget.
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

__all__ = ["resolve_repo_root", "require_dependencies", "preflight",
           "resolve_operator_paths", "RepoPathParser"]

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
                           directories: tuple[str, ...] = (),
                           optional: tuple[str, ...] = ()) -> dict[str, Path]:
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

    `optional` NAMES THE LABELS EXEMPT FROM THE EXISTENCE PASS, AND ONLY FROM
    THAT ONE. The escape pass still runs on them — it is the pass that matters,
    and exempting a path from it would be the defect. The exemption exists
    because the research family's pool argument is legitimately allowed not to
    exist yet: `run_research.py` never `mkdir`s and its dry run reports `0 due
    papers` for an absent pool rather than failing, so requiring existence here
    would turn *"escape-check the research runners too"* into a behaviour change
    to a family this PR is not otherwise touching. Per-path strictness was
    already a property of this function (`directories` is the same idea); what is
    new is a second axis, not a weaker rule.
    """
    resolved = {label: (repo_root / arg).resolve() for label, arg in paths.items()}

    for label, arg in paths.items():
        if not resolved[label].is_relative_to(repo_root):
            raise RuntimeError(
                f"{label} {arg} resolves outside the repo: {resolved[label]}")
    for label, path in resolved.items():
        if label not in optional and not path.exists():
            raise RuntimeError(f"{label} not found: {path}")
    for label in directories:
        # An optional path that is absent has already been allowed through the
        # pass above; asking `is_dir()` about it here would deny by the back door
        # what the exemption just permitted, and the message would say "is not a
        # directory" about a path that simply is not there yet.
        if label in optional and not resolved[label].exists():
            continue
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


class RepoPathParser(argparse.ArgumentParser):
    """A parser where DECLARING a repo path and CHECKING it are the same act.

    WHY THE CHECK MOVED INTO THE DECLARATION, AND NOT JUST INTO MORE CALLERS.
    `resolve_operator_paths` was correct and had two callers; five other runners
    joined their operator paths onto `repo_root` unchecked, and three of those
    accepted `../../../../tmp/...` and read through it under
    `--dangerously-skip-permissions`. Adding five more hand-written calls closes
    those five and leaves the shape that produced them — **a check each runner
    must remember, against a hand-written dict of its own path arguments.** The
    eleventh runner still omits it, and the sweep that should catch that says in
    its own docstring that it cannot: *"the absence of a check has no syntax."*

    So the registry is DERIVED FROM WHAT WAS DECLARED. `add_repo_path` is the
    only way to declare one, and it writes the dest into `_repo_paths`;
    `parse_with_preflight` resolves every dest in that mapping and no other. A
    runner cannot accept a repo path through this parser and skip the check,
    because there is no step between the two to forget.

    WHY POST-PARSE AND NOT AN ARGPARSE `type=` CALLABLE, which would be the
    obvious shape. `repo_root` comes from `preflight(a.repo_target)`, so it does
    not exist until `--repo` has been parsed — a `type=` callable runs during
    parsing and has nothing to validate against. The resolution is therefore
    ordered after the parse; what this class makes structural is not the timing
    but the SET: it is read off the declarations rather than retyped.

    WHAT THIS DOES NOT DO, stated so it is not read as more than it is:

      * It cannot stop a runner declaring a path with plain `add_argument` and
        joining it by hand. Nothing in argparse can. That residue is what
        `test_no_runner_joins_an_UNRESOLVED_operator_path.py` exists for, and it
        is the half of the property with syntax to grep: the omission is now
        VISIBLE as a join, where before it was an absence.
      * It says nothing about paths that are deliberately outside the repo.
        `--task-file` and `--phase` are read from wherever the operator points
        them, on purpose, and are declared with `add_argument` for that reason.
      * It does not make the paths SAFE, only contained. What a run may write
        inside the tree is `permitted_paths` and `boundary_crossings`, one
        altitude up.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # dest -> (is a directory, must already exist)
        self._repo_paths: dict[str, tuple[bool, bool]] = {}

    def add_repo_path(self, *names: str, kind: str = "file",
                      must_exist: bool = True, **kwargs) -> argparse.Action:
        """Declare an argument whose value is a path INSIDE the target repo.

        Takes the same arguments as `add_argument` and returns the same action,
        so a positional (`component`) and a flag (`--candidates`) are declared
        the same way — the difference between them is argparse's business, and
        the containment rule does not care which one it is holding.
        """
        if kind not in ("file", "dir"):
            raise ValueError(
                f"kind must be 'file' or 'dir', not {kind!r} — the value decides "
                f"whether the resolver asserts `is_dir()`, and a third spelling "
                f"would silently assert neither.")
        action = self.add_argument(*names, **kwargs)
        self._repo_paths[action.dest] = (kind == "dir", must_exist)
        return action

    def parse_with_preflight(
            self, argv: list[str] | None = None,
    ) -> tuple[argparse.Namespace, Path, dict[str, Path]]:
        """Parse, preflight, and resolve EVERY declared repo path. Or raise.

        Returns `(args, repo_root, paths)`. `paths` is keyed by dest and holds
        absolute, `..`-collapsed paths proven to be inside `repo_root`; the raw
        strings are still on `args` and are the ones the error messages echo,
        because an operator needs to be told about the argument they typed.

        RAISES `RuntimeError` LIKE `preflight` AND `resolve_operator_paths`, so
        every caller keeps the one `except RuntimeError` clause it already had
        and prints the message the layer that knew what failed wrote.
        """
        a = self.parse_args(argv)
        if self._repo_paths and not hasattr(a, "repo_target"):
            # Loud, because the failure is otherwise a silent fallback to the
            # invocation directory — which is #48, the defect `resolve_repo_root`
            # exists to prevent, reintroduced one layer up.
            raise RuntimeError(
                f"{self.prog} declares repo paths but no `--repo` argument with "
                f"dest='repo_target'. The repo root is what a repo path is "
                f"resolved against; without it there is nothing to contain them.")
        repo_root = preflight(getattr(a, "repo_target", None))

        # A declared-but-unsupplied optional path (`default=None`) is not a path
        # the operator gave, so there is nothing to contain. Resolving `None`
        # would raise a TypeError three frames from anything naming the cause.
        declared = {dest: getattr(a, dest) for dest in self._repo_paths
                    if getattr(a, dest) is not None}
        resolved = resolve_operator_paths(
            repo_root, declared,
            directories=tuple(d for d in declared if self._repo_paths[d][0]),
            optional=tuple(d for d in declared if not self._repo_paths[d][1]),
        )
        return a, repo_root, resolved

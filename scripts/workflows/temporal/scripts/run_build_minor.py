"""Kickoff entrypoint for the build workflow.

Lives in scripts/ because it is a launch concern, not a workflow concern. When
the Temporal path exists this is replaced by a client that starts the workflow
on a task queue; the workflow module itself does not change.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import preflight  # noqa: E402

from modules.journal import journal_activities as journal  # noqa: E402
from modules.assistant.build.build_inputs import BuildInput  # noqa: E402
from modules.assistant.build.build_minor.build_minor_workflow import run_build_minor  # noqa: E402

BANNER = "=" * 64


def parse_args(argv: list[str] | None = None) -> BuildInput:
    parser = argparse.ArgumentParser(
        prog="build-minor",
        description="Draft, refine and disposition a change as a reviewed PR.",
    )
    parser.add_argument("description", nargs="?", help="what to revise")
    parser.add_argument("--task-file", help="read the task from a file (bypasses shell parsing)")
    parser.add_argument("--phase", dest="plan_path",
                        help="path to a plan doc — extract success criteria and verify against them")
    parser.add_argument("--pr", dest="pr_number", help="update an existing PR instead of opening one")
    parser.add_argument("--repo", dest="repo_target", help="target repo (never derived from cwd)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    # BuildInput validates the exactly-one-task-source rule and raises with a
    # readable message; converting it to argparse's error path keeps the CLI
    # contract in one place.
    try:
        return BuildInput(
            description=args.description,
            task_file=args.task_file,
            plan_path=args.plan_path,
            pr_number=args.pr_number,
            repo_target=args.repo_target,
            verbose=args.verbose,
        )
    except ValueError as exc:
        parser.error(str(exc))


def main(argv: list[str] | None = None) -> int:
    task = parse_args(argv)

    try:
        try:
            repo_root = preflight(task.repo_target)
        except RuntimeError as exc:
            # Nothing has been created yet — that is the point of preflight.
            print(f"\n✗ {exc}", file=sys.stderr)
            return 1
        # REQUIREMENT 11 — the run's bag is opened BEFORE the first side
        # effect, and a root that will not resolve stops the run here (r9). Why
        # this is not a helper each file remembers to call, and what the sweep
        # that enforces it can and cannot see: `journal_activities.py`'s module
        # docstring and `tests/unit/test_every_parent_opens_a_run_bag.py`. Said
        # once there rather than eleven times here.
        # The name is computed here rather than below so the bag can record it.
        # It is a pure string — nothing is created until `run_build_minor` — so
        # this does not move a side effect ahead of the bag.
        worktree_name = f"build-{int(__import__('time').time())}"
        journal.open_run_bag(run_id=journal.mint_run_id(), repo_root=repo_root,
                             workflow_key="build-minor", worktree_name=worktree_name)

        result = run_build_minor(task, repo_root, worktree_name)
    except (RuntimeError, FileNotFoundError) as exc:
        # These carry operator-facing recovery instructions from the layer that
        # knew what failed. Do not wrap or reformat them.
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1

    print()
    print(BANNER)
    if result.ready_to_merge:
        headline = f"BUILD COMPLETE — PR #{result.pr_number} dispositioned MERGE"
        if result.loops_used:
            headline += f" after {result.loops_used} correction loop"
    else:
        headline = f"BUILD COMPLETE — PR #{result.pr_number} HELD ({result.verdict.value})"
    print(f"  {headline}")
    print(BANNER)
    print()
    print(f"  {result.pr_url}")
    print()
    for note in result.notes:
        print(f"  {note}")
    if result.notes:
        print()
    print("To clean up when done:")
    print("  /cleanup-merged-worktrees    (one worktree per child run)")
    print()

    # Exit 0 for both MERGE and HOLD: the workflow completed and produced a
    # verdict either way. A HOLD is a result, not a failure — the caller reads
    # `verdict`, which is the point of returning a typed result at all.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

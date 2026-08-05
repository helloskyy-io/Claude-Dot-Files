"""Kickoff entrypoint for the revision workflow.

Lives in scripts/ because it is a launch concern, not a workflow concern. When
the Temporal path exists this is replaced by a client that starts the workflow
on a task queue; the workflow module itself does not change.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.assistant.revision.revision.revision_inputs import RevisionInput  # noqa: E402
from modules.assistant.revision.revision.revision_workflow import run_revision  # noqa: E402

BANNER = "=" * 64


def parse_args(argv: list[str] | None = None) -> RevisionInput:
    parser = argparse.ArgumentParser(
        prog="revision",
        description="Draft, refine and disposition a change as a reviewed PR.",
    )
    parser.add_argument("description", nargs="?", help="what to revise")
    parser.add_argument("--task-file", help="read the task from a file (bypasses shell parsing)")
    parser.add_argument("--pr", dest="pr_number", help="update an existing PR instead of opening one")
    parser.add_argument("--repo", dest="repo_target", help="target repo (never derived from cwd)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    # RevisionInput validates the exactly-one-task-source rule and raises with a
    # readable message; converting it to argparse's error path keeps the CLI
    # contract in one place.
    try:
        return RevisionInput(
            description=args.description,
            task_file=args.task_file,
            pr_number=args.pr_number,
            repo_target=args.repo_target,
            verbose=args.verbose,
        )
    except ValueError as exc:
        parser.error(str(exc))


def main(argv: list[str] | None = None) -> int:
    task = parse_args(argv)

    try:
        result = run_revision(task)
    except (RuntimeError, FileNotFoundError) as exc:
        # These carry operator-facing recovery instructions from the layer that
        # knew what failed. Do not wrap or reformat them.
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1

    print()
    print(BANNER)
    if result.ready_to_merge:
        headline = f"REVISION COMPLETE — PR #{result.pr_number} dispositioned MERGE"
        if result.loops_used:
            headline += f" after {result.loops_used} correction loop"
    else:
        headline = f"REVISION COMPLETE — PR #{result.pr_number} HELD ({result.verdict.value})"
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

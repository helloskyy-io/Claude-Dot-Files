"""Kickoff entrypoint for the plan-master workflow.

Lives in scripts/ because it is a launch concern, not a workflow concern. When
the Temporal path exists this is replaced by a client that starts the workflow
on a task queue; the workflow module itself does not change.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import preflight  # noqa: E402

from modules.assistant import routing  # noqa: E402
from modules.assistant.plan.plan_master.plan_master_workflow import run_plan_master  # noqa: E402

BANNER = "=" * 64

# Defaults, not derivations. These are the repo's own surfaces; a different repo
# passes its own. Stated here rather than inside the workflow so the workflow
# stays repo-agnostic and the launch concern owns the convention.
DEFAULT_SPRINT = "docs/development/sprint.md"
DEFAULT_RESEARCH = "docs/standards/architecture/research"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="plan-master",
        description="Triage research candidates into the sprint plan, then judge the result.",
    )
    p.add_argument("--sprint", default=DEFAULT_SPRINT, help=f"sprint plan (default: {DEFAULT_SPRINT})")
    p.add_argument("--research", default=DEFAULT_RESEARCH, help=f"product research pool (default: {DEFAULT_RESEARCH})")
    p.add_argument("--pr", dest="pr_number", help="update an existing planning PR instead of opening one")
    p.add_argument("--repo", dest="repo_target", help="target repo — a FILESYSTEM PATH, never a gh slug")
    p.add_argument("--verbose", "-v", action="store_true")
    a = p.parse_args(argv)

    try:

        repo_root = preflight(a.repo_target)

    except RuntimeError as exc:

        # Nothing has been created yet — that is the point of preflight.

        print(f"\n✗ {exc}", file=sys.stderr)

        return 1
    research_dir = repo_root / a.research

    try:
        url, verdict, loops, notes = run_plan_master(
            repo_root=repo_root,
            worktree_name=f"plan-master-{int(time.time())}",
            sprint_path=repo_root / a.sprint,
            candidates_path=research_dir / "candidates.md",
            research_dir=research_dir,
            pr_number=a.pr_number, repo_target=a.repo_target, verbose=a.verbose,
        )
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        # These carry operator-facing recovery instructions from the layer that
        # knew what failed. Do not wrap or reformat them.
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1

    print()
    print(BANNER)
    headline = f"PLAN COMPLETE — {url.rsplit('/', 1)[-1] and 'PR #' + url.rsplit('/', 1)[-1]}"
    if verdict is routing.Verdict.MERGE:
        headline += " dispositioned MERGE"
        if loops:
            headline += f" after {loops} correction loop"
    else:
        headline += f" HELD ({verdict.value})"
    print(f"  {headline}")
    print(BANNER)
    print()
    print(f"  {url}")
    print()
    for note in notes:
        print(f"  {note}")
    if notes:
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

"""Kickoff entrypoint for plan-revision.

Lives in scripts/ because it is a launch concern, not a workflow concern. It
owns the CLI contract, the input validation V1 did inline, and the ONE worktree
the run executes in — the workflow itself is a child and receives that path.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.assistant.plan import plan_activities as act  # noqa: E402
from modules.assistant.plan.plan_revision import plan_revision_workflow as wf  # noqa: E402

BANNER = "=" * 64

EPILOG = """\
Examples (flags FIRST, positionals LAST — protects positionals from
line-wrap and keeps options visible):
  plan_revision.sh "update roadmap to reflect Phase 4 completion"
  plan_revision.sh "add ADR for switching from REST to gRPC" "focus on performance rationale"
  plan_revision.sh --pr 18 --task-file /tmp/context.md "revise Phase 5 requirements"
  plan_revision.sh --verbose "realign roadmap milestones"

This workflow is for PLANNING doc builds — not code changes.
For code changes, use build_minor.sh (light fixes) or build.sh (reviewed rework) instead.
"""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="plan-revision",
        description="Revise existing planning docs — roadmaps, phase docs, "
                    "requirements, ADRs, epics. A PLANNING build, not a code change.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("description", help="what planning changes are needed (required)")
    p.add_argument("context", nargs="?", default="",
                   help="additional context (optional positional — short text only)")
    p.add_argument("--task-file",
                   help="read additional context from a file — use this for multi-paragraph "
                        "context or anything with quotes, newlines or special characters that "
                        "would break command-line parsing. Preserves content literally. "
                        "Mutually exclusive with the positional context.")
    p.add_argument("--pr", dest="pr_number",
                   help="update an existing PR instead of creating a new one")
    p.add_argument("--repo", dest="repo_target",
                   help="target repo — a FILESYSTEM PATH, never a gh slug")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="stream formatted Claude output live")
    a = p.parse_args(argv)

    # V1 rejected both-at-once rather than silently preferring one. Preferring
    # either would drop context the operator supplied, and they would find out
    # from the plan, not from the run.
    if a.context and a.task_file:
        p.error("cannot use both a positional context and --task-file")
    return a


def _read_task_file(path_str: str) -> str:
    """Load --task-file, distinguishing missing from unreadable as V1 did.

    Two messages, not one: 'not found' sends the operator to their path, and
    'not readable' sends them to permissions. Collapsing them costs a wrong
    diagnosis at the only moment the run is cheap to fix.
    """
    path = Path(path_str)
    if not path.is_file():
        raise FileNotFoundError(f"task file not found: {path_str}")
    try:
        return path.read_text()
    except OSError as exc:
        raise RuntimeError(f"task file not readable: {path_str} ({exc})") from exc


def main(argv: list[str] | None = None) -> int:
    a = parse_args(argv)
    repo_root = Path(a.repo_target) if a.repo_target else Path.cwd()

    try:
        # V1's own precondition. Checked here rather than left to git: without a
        # repo there is no worktree to create, and the failure would otherwise
        # surface as a `git worktree add` error that names neither the cause nor
        # the fix.
        if subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=str(repo_root),
                          capture_output=True, text=True).returncode != 0:
            print(f"\n✗ not inside a git repository: {repo_root}", file=sys.stderr)
            return 1

        context = _read_task_file(a.task_file) if a.task_file else a.context

        print(BANNER)
        print("  PLAN-REVISION WORKFLOW")
        print(BANNER)
        print(f"  Description : {a.description}")
        if context:
            # First line only, capped: a --task-file body is routinely pages
            # long and echoing it buries the rest of the banner.
            head = context.splitlines()[0][:80]
            print(f"  Context     : {head}{'…' if context.strip() != head else ''}")
        print(f"  Target      : {f'PR #{a.pr_number} (updating existing)' if a.pr_number else 'new branch and PR'}")
        print(BANNER)
        print()

        # ISOLATION IS ESTABLISHED HERE, ONCE, and handed to the child. On the
        # --pr path the worktree is cut from the PR branch, matching V1; on the
        # new-branch path from HEAD.
        ref = f"origin/{act.pr_branch(a.pr_number, repo_root)}" if a.pr_number else "HEAD"
        worktree = act.worktree_add(repo_root, f"plan-revision-{int(time.time())}", ref)

        url = wf.run_plan_revision(
            description=a.description, repo_root=repo_root, worktree=worktree,
            context=context, pr_number=a.pr_number, verbose=a.verbose,
        )
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        # These carry operator-facing recovery instructions from the layer that
        # knew what failed. Do not wrap or reformat them.
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1

    print(f"\n{BANNER}\n  {url}\n{BANNER}")
    print("\nTo clean up when done:\n  /cleanup-merged-worktrees    (after the PR is merged or closed)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

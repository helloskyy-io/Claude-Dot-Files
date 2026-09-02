"""Kickoff entrypoint for build-draft-minor — the light tier's draft.

THE FAMILY RULING FOR ALL SIX OF THIS PHASE'S ADAPTERS IS IN
`run_build_draft.py`'s module docstring, and is not restated here. Read it there
before changing anything in this file; it is one ruling, not six.

Differs from `run_build_draft.py` because the minor tier's core function takes
no `prefer_repo`: `run_draft_minor` never disambiguates which repo's PR a run
opened, so there is no `repo_slug` round trip to make. Nothing else about this
runner is a deliberate variant, and anything else that differs is a defect.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import preflight, refuse  # noqa: E402
from dispatch_identity import add_identity_arguments, resolve_identity  # noqa: E402
from dispatch_context import RunContext  # noqa: E402

from modules.journal import journal_activities as journal  # noqa: E402
from modules.assistant import assistant_activities as act  # noqa: E402
from modules.assistant.build.build_activities import path_for_the_model, task_text  # noqa: E402
from modules.assistant.build.build_inputs import BuildInput  # noqa: E402
from modules.assistant.build.build_draft_minor.build_draft_minor_workflow import (  # noqa: E402
    run_draft_minor)

BANNER = "=" * 64

WORKFLOW_KEY = "build-draft-minor"


def parse_args(argv: list[str] | None = None) -> tuple[BuildInput, bool]:
    parser = argparse.ArgumentParser(
        prog="build-draft-minor",
        description="Write ONE scoped change and open an UNREVIEWED PR. No "
                    "review pass runs — this is build-minor's first child, "
                    "invoked alone.")
    parser.add_argument("description", nargs="?", help="the scoped change to make")
    parser.add_argument("--task-file", help="read the task from a file (bypasses shell parsing)")
    parser.add_argument("--phase", dest="plan_path",
                        help="path to a plan doc — extract success criteria and verify against them")
    parser.add_argument("--pr", dest="pr_number", help="update an existing PR instead of opening one")
    parser.add_argument("--repo", dest="repo_target", help="target repo (never derived from cwd)")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="state what this run derived; no model, no worktree, no spend")
    add_identity_arguments(parser)
    args = parser.parse_args(argv)

    try:
        task = BuildInput(
            description=args.description,
            task_file=args.task_file,
            plan_path=args.plan_path,
            pr_number=args.pr_number,
            repo_target=args.repo_target,
            verbose=args.verbose,
        )
    except ValueError as exc:
        parser.error(str(exc))
    return task, args.dry_run


def main(argv: list[str] | None = None) -> int:
    task, dry_run = parse_args(argv)

    try:
        repo_root = preflight(task.repo_target)
    except RuntimeError as exc:
        return refuse(exc)

    if dry_run:
        print(f"{BANNER}\n  DRY RUN — nothing invoked, nothing posted\n{BANNER}")
        print(RunContext.for_dry_run(repo_root=repo_root, workflow_key=WORKFLOW_KEY,
                                     pr_number=task.pr_number, target=None).render())
        return 0

    try:
        ctx = RunContext.build(identity=resolve_identity(argv), repo_root=repo_root,
                               workflow_key=WORKFLOW_KEY, pr_number=task.pr_number)
        ctx.echo()
        journal.open_run_bag(run_id=ctx.run_id, writer=ctx.writer,
                             repo_root=ctx.repo_root,
                             workflow_key=ctx.workflow_key,
                             worktree_name=ctx.worktree_name,
                             journal_root=ctx.journal_root)

        ref = act.base_ref(task.pr_number, repo_root)
        worktree = act.worktree_add(repo_root, ctx.worktree_name, ref)

        pr_url = run_draft_minor(
            description=task_text(task, repo_root), repo_root=repo_root,
            worktree=worktree, pr_number=task.pr_number,
            plan_path=path_for_the_model(repo_root, task.plan_path),
            verbose=task.verbose,
        )
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        return refuse(exc)

    print(f"\n{BANNER}\n  BUILD-DRAFT-MINOR COMPLETE — the PR is UNREVIEWED\n{BANNER}",
          file=sys.stderr)
    print("  refine it with:  ./build_refine_minor.sh --pr <n> <the same task>\n"
          "  clean up with :  /cleanup-merged-worktrees", file=sys.stderr)
    print(pr_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

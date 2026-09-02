"""Kickoff entrypoint for build-refine — FRESH context over an existing PR.

THE FAMILY RULING FOR ALL SIX OF THIS PHASE'S ADAPTERS IS IN
`run_build_draft.py`'s module docstring, and is not restated here.

Differs from `run_build_draft.py` because `--pr` is REQUIRED. `run_refine` takes
`pr_number: str`, not optional: a refine pass reviews and corrects work that
already exists, so there is no PR for it to open and nothing for it to do without
one. Making it a required flag turns an unusable invocation into an argparse
error costing a second, rather than a `TypeError` after a worktree exists.

Differs a second time in what it DOES NOT expose. `run_refine` also takes
`loops_left` and `ci_unsettled`, and neither is offered on this CLI because
neither is the operator's to supply: `loops_left` renders the parent's "this is
the last automated pass" finality note and is bookkeeping for a loop that does
not exist when this child runs alone, and `ci_unsettled` is the parent's own CI
read handed down. A standalone caller inventing values for them would be
asserting facts about a chain that is not running. `--correction-pass` IS
exposed, because re-running refine over a reviewer's findings is the single most
common reason to invoke this child by hand — which is the phase's whole point.
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
from modules.assistant.build.build_activities import task_text  # noqa: E402
from modules.assistant.build.build_inputs import BuildInput  # noqa: E402
from modules.assistant.build.build_refine.build_refine_workflow import run_refine  # noqa: E402

BANNER = "=" * 64

WORKFLOW_KEY = "build-refine"


def parse_args(argv: list[str] | None = None) -> tuple[BuildInput, bool, bool]:
    parser = argparse.ArgumentParser(
        prog="build-refine",
        description="Review and correct an existing PR in FRESH context. The run "
                    "that authored a change never defends it.")
    parser.add_argument("description", nargs="?",
                        help="the ORIGINAL task, so this pass can ask whether the "
                             "work delivered what was asked. Omit it and the PR's "
                             "own runway is the task.")
    parser.add_argument("--task-file", help="read the original task from a file")
    parser.add_argument("--phase", dest="plan_path", help="the plan doc the work was built from")
    parser.add_argument("--pr", dest="pr_number", required=True,
                        help="the PR to review and correct (REQUIRED — a refine "
                             "pass has nothing to open)")
    parser.add_argument("--repo", dest="repo_target", help="target repo (never derived from cwd)")
    parser.add_argument("--correction-pass", action="store_true",
                        help="a reviewer already found something here — treat every "
                             "runway item as an INSTANCE of a class, not as the whole")
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
    return task, args.correction_pass, args.dry_run


def main(argv: list[str] | None = None) -> int:
    task, correction_pass, dry_run = parse_args(argv)

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

        # `base_ref` reads `origin/<the PR's branch>` because `--pr` is set, which
        # is the tree this pass must correct. It is never the operator's checkout
        # position — three of eight open PRs once carried another PR's commits
        # because the inline form used `HEAD`.
        ref = act.base_ref(task.pr_number, repo_root)
        worktree = act.worktree_add(repo_root, ctx.worktree_name, ref)

        pr_url = run_refine(
            description=task_text(task, repo_root), pr_number=task.pr_number,
            repo_root=repo_root, worktree=worktree,
            correction_pass=correction_pass, verbose=task.verbose,
        )
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        return refuse(exc)

    print(f"\n{BANNER}\n  BUILD-REFINE COMPLETE — PR #{task.pr_number} reviewed "
          f"and corrected\n{BANNER}", file=sys.stderr)
    print("  disposition it with:  ./review_pr.sh --pr <n>\n"
          "  clean up with      :  /cleanup-merged-worktrees", file=sys.stderr)
    print(pr_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

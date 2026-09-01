#!/usr/bin/env python3
"""`plan` — the planning PARENT: plan-draft -> plan-refine -> plan-sprint -> review-pr.

WHY THIS EXISTS. `plan_project.sh` chains the same four children but takes no
component: it triages the candidate store, scaffolds NEW components and plans
only those. Re-planning an EXISTING component therefore meant dispatching four
children by hand, in order — done eight times over one PR on 2026-08-28, and
the one time the chain was short-circuited, three defects reached `review-pr`
that `plan-refine` would have caught.

THE PARENT CALLS NO MODEL, so it has no `config.yaml` entry — the same as
`build` and `research`. Every figure the run spends belongs to a child.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import RepoPathParser  # noqa: E402
from dispatch_identity import add_identity_arguments, resolve_identity  # noqa: E402
from dispatch_context import RunContext  # noqa: E402
from modules.assistant import assistant_activities as act  # noqa: E402
from modules.journal import journal_activities as journal  # noqa: E402
from modules.assistant.plan.plan.plan_workflow import run_plan  # noqa: E402

BANNER = "=" * 64
DEFAULT_CANDIDATES = "tracked/candidates"
DEFAULT_SPRINT = "development/sprints.md"


def _parser() -> RepoPathParser:
    p = RepoPathParser(prog="plan",
                       description="Plan ONE component end to end: write, verify, size, "
                                   "reconcile the sprint, disposition.")
    p.add_repo_path("component", kind="dir",
                    help="the component directory, e.g. development/<edge>/<name>")
    p.add_argument("--repo", dest="repo_target",
                   help="target repo — a FILESYSTEM PATH, never a gh slug")
    p.add_repo_path("--candidates", default=DEFAULT_CANDIDATES)
    p.add_repo_path("--sprint", default=DEFAULT_SPRINT)
    p.add_argument("--pr", dest="pr_number", help="update an existing planning PR")
    p.add_argument("--task-file", dest="task_file",
                   help="a brief the run reads as its task context")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--dry-run", action="store_true",
                   help="resolve and print the chain; no child runs, no spend")
    add_identity_arguments(p)
    return p


def main(argv: list[str] | None = None) -> int:
    p = _parser()
    try:
        # ONE CALL, NOT THREE. `parse_with_preflight` runs preflight, RESOLVES
        # every declared repo path against the repo root and refuses one that
        # escapes it. Doing those by hand is what broke this runner on its first
        # live run: the component arrived repo-RELATIVE, went to the children
        # as-is, and their `relative_to(repo_root)` raised
        # "not in the subpath of ..." — a failure naming the wrong cause.
        a, repo_root, resolved = p.parse_with_preflight(argv)
        # READ INSIDE THIS try, so a bad `--task-file` prints the same one-line
        # diagnostic as a bad `--repo` rather than a traceback. Both are
        # operator input and neither has created anything yet.
        context = act.task_context(repo_root, a.task_file)
    except RuntimeError as exc:
        # Nothing has been created yet — that is the point of preflight.
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1
    component, cands, sprint = (resolved["component"], resolved["candidates"],
                                resolved["sprint"])

    target = str(component.relative_to(repo_root))

    if a.dry_run:
        print(f"{BANNER}\n  DRY RUN — no child runs, nothing posted\n{BANNER}")
        # THE SAME OBJECT THE LIVE RUN PRINTS, rendered by the same method. A
        # rehearsal that assembled its own copy would preview something that is
        # not what runs, which is the bug this family has already shipped once.
        print(RunContext.for_dry_run(repo_root=repo_root, workflow_key="plan",
                                     pr_number=a.pr_number, target=target).render())
        print(f"  Sprint     : {sprint.relative_to(repo_root)}")
        print(f"  Candidates : {cands.relative_to(repo_root)}")
        print(f"  Context    : {len(context.encode())} bytes from --task-file"
              if context else "  Context    : none")
        print("  Chain      : plan-draft → plan-refine → plan-sprint → CI gate → review-pr")
        print(f"  Loop-back  : the whole chain below the author, up to 3 times\n")
        return 0

    try:
        # EVERYTHING THIS RUN DERIVED, BUILT ONCE, AND SAID OUT LOUD BEFORE THE
        # BAG OPENS. The worktree name is a field on it rather than an expression
        # here; see `dispatch_context.py` for why eleven copies of that
        # expression were the defect. The echo precedes bag-open, the worktree
        # and every `gh` call.
        #
        # ⚠ INSIDE THE `try`, WHICH IT WAS NOT. This block sat above the handler
        # in this one file of eleven, so `resolve_identity`'s refusal of a bad
        # `--run-id` and `open_run_bag`'s refusal of a full journal — both
        # `RuntimeError`s carrying operator-facing remedies — reached the
        # operator as a traceback here and as a one-line diagnostic everywhere
        # else. Resolving the journal root at the boundary added a THIRD raise
        # to the unguarded region, which is what made a latent gap worth closing.
        ctx = RunContext.build(identity=resolve_identity(argv), repo_root=repo_root,
                               workflow_key="plan", pr_number=a.pr_number,
                               target=target)
        ctx.echo()
        journal.open_run_bag(run_id=ctx.run_id, writer=ctx.writer,
                             repo_root=ctx.repo_root, workflow_key=ctx.workflow_key,
                             worktree_name=ctx.worktree_name,
                             journal_root=ctx.journal_root)

        pr_url, verdict, notes = run_plan(
            component=component, repo_root=repo_root, worktree_name=ctx.worktree_name,
            sprint_path=sprint, candidates_path=cands,
            context=context, pr_number=a.pr_number, repo_target=a.repo_target,
            verbose=a.verbose,
        )
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        # These carry operator-facing recovery instructions from the layer that
        # knew what failed. Do not wrap or reformat them.
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1

    print(f"\n{BANNER}")
    print(f"  PLAN COMPLETE — {component.name} dispositioned {verdict.value}")
    print(f"{BANNER}\n\n  {pr_url}\n")
    for note in notes:
        print(f"  {note}")
    print("\nTo clean up when done:\n  /cleanup-merged-worktrees\n")

    # Exit 0 for MERGE and HOLD alike: the chain completed and produced a
    # verdict either way. A HOLD is a result, not a failure.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

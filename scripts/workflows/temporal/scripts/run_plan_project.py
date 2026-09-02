"""Kickoff entrypoint for the plan-project workflow.

Lives in scripts/ because it is a launch concern, not a workflow concern. When
the Temporal path exists this is replaced by a client that starts the workflow
on a task queue; the workflow module itself does not change.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import RepoPathParser, refuse  # noqa: E402
from dispatch_identity import add_identity_arguments, resolve_identity  # noqa: E402
from dispatch_context import RunContext  # noqa: E402

from modules.journal import journal_activities as journal  # noqa: E402
from modules.assistant import routing  # noqa: E402
from modules.assistant.plan.plan_project.plan_project_workflow import run_plan_project  # noqa: E402

BANNER = "=" * 64

# Defaults, not derivations. These are the repo's own surfaces; a different repo
# passes its own. Stated here rather than inside the workflow so the workflow
# stays repo-agnostic and the launch concern owns the convention.
DEFAULT_RESEARCH = "research"


def main(argv: list[str] | None = None) -> int:
    p = RepoPathParser(
        prog="plan-project",
        description="Rule the research candidates and give the shipped ones a home, then judge the result.",
    )
    # DECLARED AS A REPO PATH, WHICH IS WHAT INSTALLS THE CHECK. This runner
    # joined its paths onto `repo_root` unchecked and tested none of them, so an
    # escaping `--research` reached the parent as an absolute path containing
    # `..` and took the whole pipeline with it. Demonstrated by execution with
    # the dispatch stubbed, since this entrypoint has no `--dry-run`.
    #
    # THE EXISTENCE CHECK IS A DELIBERATE BEHAVIOUR CHANGE. This was the one
    # runner in the family that validated nothing, so a typo'd path used to
    # surface after the worktree was cut — the orphaned-worktree class (#48/#49)
    # that `preflight` exists to close, reached through an argument `preflight`
    # did not see.
    #
    # `--sprint` IS GONE RATHER THAN DEFAULTED. It fed `plan-sprint`, which this
    # parent no longer dispatches: sizing a sprint entry needs the component's
    # roadmap, and this run stops before anything writes one. `plan.sh` owns that
    # step and takes the sprint path itself.
    p.add_repo_path("--research", kind="dir", default=DEFAULT_RESEARCH,
                    help=f"product research pool (default: {DEFAULT_RESEARCH})")
    p.add_argument("--pr", dest="pr_number", help="update an existing planning PR instead of opening one")
    p.add_argument("--repo", dest="repo_target", help="target repo — a FILESYSTEM PATH, never a gh slug")
    p.add_argument("--verbose", "-v", action="store_true")

    add_identity_arguments(p)
    try:
        a, repo_root, resolved = p.parse_with_preflight(argv)
    except RuntimeError as exc:
        # Nothing has been created yet — that is the point of preflight.
        return refuse(exc)
    research_dir = resolved["research"]

    try:
        # REQUIREMENT 11 — the run's bag is opened BEFORE the first side
        # effect, and a root that will not resolve stops the run here (r9). Why
        # this is not a helper each file remembers to call, and what the sweep
        # that enforces it can and cannot see: `journal_activities.py`'s module
        # docstring and `tests/unit/test_every_parent_opens_a_run_bag.py`. Said
        # once there rather than eleven times here.
        # EVERYTHING THIS RUN DERIVED, BUILT ONCE AND SAID OUT LOUD BEFORE THE
        # BAG OPENS, THE WORKTREE IS CUT OR ANY `gh` CALL RUNS. Identity comes
        # from outside the process (Phase 9 r2/r4, `dispatch_identity.py`); the
        # worktree name is a FIELD rather than an expression here, because
        # eleven copies of that expression in three spellings was the defect
        # (`dispatch_context.py`).
        # `target=None` — this runner takes NO component. It triages the
        # candidate store and plans whatever it scaffolds, so there is nothing
        # the operator pointed it at and the field says so rather than being
        # handed a stand-in.
        ctx = RunContext.build(identity=resolve_identity(argv), repo_root=repo_root,
                               workflow_key="plan-project", pr_number=a.pr_number)
        ctx.echo()
        journal.open_run_bag(run_id=ctx.run_id, writer=ctx.writer,
                             repo_root=ctx.repo_root,
                             workflow_key=ctx.workflow_key,
                             worktree_name=ctx.worktree_name,
                             journal_root=ctx.journal_root)

        url, verdict, loops, notes = run_plan_project(
            repo_root=repo_root,
            worktree_name=ctx.worktree_name,
            # DERIVED FROM AN ALREADY-CONTAINED PATH, so it needs no declaration
            # of its own: `repo_root` is proven by preflight and two literal
            # segments cannot walk back out of it. This is not an operator path.
            # Root-relative rather than under the research tree, because the
            # store is root-relative in EVERY repo that adopts the contract —
            # that is what makes one implementation possible (Tracked Items §1).
            candidates_path=repo_root / "tracked" / "candidates",
            research_dir=research_dir,
            pr_number=a.pr_number, repo_target=a.repo_target, verbose=a.verbose,
        )
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        # These carry operator-facing recovery instructions from the layer that
        # knew what failed. Do not wrap or reformat them.
        return refuse(exc)

    print()
    print(BANNER)
    # THROUGH THE OWNER, not a string split. This is display-only, so the
    # consequence of the old `url.rsplit('/', 1)[-1]` was a banner rather than a
    # route — but it was the THIRD ad-hoc PR-number derivation in the tree, and
    # a gate on the shape cannot make an exception for the one that only prints.
    # It cannot raise here: `plan_project_workflow` already ran the same parse
    # over this value before returning it, so an unparseable URL failed above.
    #
    # `expected_repo=None` IS A STATEMENT, NOT A SKIP. That same earlier parse
    # ran WITH the dispatch's slug (`plan_project_workflow:83`), so identity is
    # already established on this exact string; re-establishing it here would
    # mean a second `gh repo view` for a banner. This is the one call site in
    # the tree entitled to None and the reason is that another site checked.
    headline = f"PLAN COMPLETE — PR #{routing.pr_number_from_url(url, expected_repo=None)}"
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

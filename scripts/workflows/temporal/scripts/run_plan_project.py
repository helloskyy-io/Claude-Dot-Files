"""Kickoff entrypoint for the plan-project workflow.

Lives in scripts/ because it is a launch concern, not a workflow concern. When
the Temporal path exists this is replaced by a client that starts the workflow
on a task queue; the workflow module itself does not change.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import RepoPathParser  # noqa: E402
from dispatch_identity import add_identity_arguments, resolve_identity  # noqa: E402

from modules.journal import journal_activities as journal  # noqa: E402
from modules.assistant import routing  # noqa: E402
from modules.assistant.plan.plan_project.plan_project_workflow import run_plan_project  # noqa: E402

BANNER = "=" * 64

# Defaults, not derivations. These are the repo's own surfaces; a different repo
# passes its own. Stated here rather than inside the workflow so the workflow
# stays repo-agnostic and the launch concern owns the convention.
DEFAULT_SPRINT = "docs/development/sprint.md"
DEFAULT_RESEARCH = "docs/standards/architecture/research"


def main(argv: list[str] | None = None) -> int:
    p = RepoPathParser(
        prog="plan-project",
        description="Triage research candidates into the sprint plan, then judge the result.",
    )
    # DECLARED AS REPO PATHS, WHICH IS WHAT INSTALLS THE CHECK. This runner
    # joined both onto `repo_root` unchecked and tested NEITHER, so an escaping
    # `--research` reached the parent as an absolute path containing `..` and
    # took the whole three-child pipeline with it. Demonstrated by execution with
    # the dispatch stubbed, since this entrypoint has no `--dry-run`.
    #
    # THE EXISTENCE CHECK IS NEW HERE AND IS A DELIBERATE BEHAVIOUR CHANGE. This
    # was the one runner in the family that validated nothing, so a typo'd
    # `--sprint` used to surface after the worktree was cut — the orphaned-
    # worktree class (#48/#49) that `preflight` exists to close, reached through
    # the one argument `preflight` did not see.
    p.add_repo_path("--sprint", default=DEFAULT_SPRINT, help=f"sprint plan (default: {DEFAULT_SPRINT})")
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
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1
    research_dir = resolved["research"]

    try:
        # REQUIREMENT 11 — the run's bag is opened BEFORE the first side
        # effect, and a root that will not resolve stops the run here (r9). Why
        # this is not a helper each file remembers to call, and what the sweep
        # that enforces it can and cannot see: `journal_activities.py`'s module
        # docstring and `tests/unit/test_every_parent_opens_a_run_bag.py`. Said
        # once there rather than eleven times here.
        worktree_name = f"plan-project-{int(time.time())}"
        # PHASE 9 r2 and r4 — the run's NAME arrives from outside this
        # process, and `writer` says whether this invocation IS the run or
        # is part of one. Why both, and where a name comes from when no
        # orchestrator supplies it: `dispatch_identity.py`. Said once there.
        identity = resolve_identity(argv)
        journal.open_run_bag(run_id=identity.run_id, writer=identity.writer,
                             repo_root=repo_root,
                             workflow_key="plan-project",
                             worktree_name=worktree_name)

        url, verdict, loops, notes = run_plan_project(
            repo_root=repo_root,
            worktree_name=worktree_name,
            sprint_path=resolved["sprint"],
            # DERIVED FROM AN ALREADY-CONTAINED PATH, so it needs no declaration
            # of its own: `research_dir` is proven inside the repo and a literal
            # segment cannot walk back out of it. This is not an operator path.
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

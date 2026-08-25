"""Kickoff entrypoint for research-minor — ONE topic, ONE paper, plus a synthesis.

A SEPARATE ENTRY RATHER THAN A `--minor` FLAG ON `run_research.py`, for the same
reason `run_build_minor.py` sits beside `run_build.py`: the two dispatch
different parents with different children, different model keys and different
turn budgets. A flag would put one CLI in front of two workflows and make the
shape a runtime branch — which is the coupling the sibling shape exists to
avoid. `--refresh` on `run_research.py` is not a counter-example: refresh is the
same pool being revalidated, not a different pool shape.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import RepoPathParser  # noqa: E402
from dispatch_identity import add_identity_arguments, resolve_identity  # noqa: E402
from modules.assistant import assistant_activities as act_shared  # noqa: E402
from modules.journal import journal_activities as journal  # noqa: E402
from modules.assistant.research.research_minor import research_minor_workflow as rm  # noqa: E402
from modules.assistant.research import research_activities as act  # noqa: E402

BANNER = "=" * 64


def main(argv=None) -> int:
    p = RepoPathParser(
        prog="research-minor",
        description="Research ONE topic as ONE paper, plus the synthesis a planner reads. No topic list, no fan-out.",
    )
    # DECLARED AS A REPO PATH, with `must_exist=False`. See `run_research.py` for
    # both halves: the pool was joined onto `repo_root` unchecked, and this family
    # legitimately accepts a pool that does not exist yet.
    p.add_repo_path("research_dir", kind="dir", must_exist=False,
                    help="research folder, relative to the repo root")
    # NOT a repo path, deliberately — operator context from wherever they wrote it.
    p.add_argument("--task-file", dest="task_file", help="context from a file")
    p.add_argument("--repo", dest="repo_target", help="target repo — a FILESYSTEM PATH, never a gh slug")
    p.add_argument("--pr", dest="pr_number", help="update an existing research PR")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="compute the gate and render; no model, no spend")

    add_identity_arguments(p)
    try:
        a, repo_root, resolved = p.parse_with_preflight(argv)
        # READ HERE, INSIDE THIS try, so a bad `--task-file` prints the same
        # one-line diagnostic as a bad `--repo` instead of a traceback. Both
        # are operator input and neither has created anything yet.
        context = act_shared.task_context(repo_root, a.task_file)
    except RuntimeError as exc:
        # Nothing has been created yet — that is the point of preflight.
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1

    research_dir = resolved["research_dir"]
    import time
    wt = f"research-minor-{int(time.time())}"

    try:
        if a.dry_run:
            table, due = act.paper_currency(research_dir)
            print(f"{BANNER}\n  DRY RUN — nothing invoked, nothing posted\n{BANNER}")
            # THE TREE THE COUNTS CAME FROM, NAMED RATHER THAN LEFT TO BE
            # ASSUMED. No worktree exists on a dry run, so every figure below is
            # read off THIS checkout — while a `--pr` run cuts its worktree from
            # `origin/<the PR's branch>` and reads nothing else. Two trees, and
            # on the correction pass a `--pr` dry run exists for, they routinely
            # differ: the work being corrected is on the branch and need not be
            # in this checkout at all.
            #
            # THIS IS THE MINIMUM AND IT IS KNOWN TO BE — issue #134, operator
            # ruling 2026-08-24, on measured evidence. The stronger remedy reads
            # `origin/<branch>` so the preview is an actual preview, and earns
            # itself when real operator use appears.
            print(f"  Counted in : this checkout ({repo_root}) — a dry run cuts no worktree")
            print("  Mode      : research-minor (ONE topic -> ONE paper + synthesis)")
            print(f"  Pool      : {research_dir}")
            print(f"  Existing  : {len(due)} of the papers present are past their window")
            for d in due:
                print(f"    - {d.name}")
            return 0
        # REQUIREMENT 11 — the run's bag is opened BEFORE the first side
        # effect, and a root that will not resolve stops the run here (r9). Why
        # this is not a helper each file remembers to call, and what the sweep
        # that enforces it can and cannot see: `journal_activities.py`'s module
        # docstring and `tests/unit/test_every_parent_opens_a_run_bag.py`. Said
        # once there rather than eleven times here.
        # PHASE 9 r2 and r4 — the run's NAME arrives from outside this
        # process, and `writer` says whether this invocation IS the run or
        # is part of one. Why both, and where a name comes from when no
        # orchestrator supplies it: `dispatch_identity.py`. Said once there.
        identity = resolve_identity(argv)
        journal.open_run_bag(run_id=identity.run_id, writer=identity.writer,
                             repo_root=repo_root,
                             workflow_key="research-minor", worktree_name=wt)

        result = rm.run_research_minor(
            research_dir=research_dir, repo_root=repo_root, worktree_name=wt,
            context=context, pr_number=a.pr_number, verbose=a.verbose,
        )
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1

    print()
    print(BANNER)
    v = result.get("verdict")
    print(f"  {result.get('pr_url') or 'no PR'} — {v.value if v else 'no verdict'}")
    print(BANNER)
    for n in result.get("notes", []):
        print(f"  {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

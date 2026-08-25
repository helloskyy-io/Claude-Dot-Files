"""Kickoff entrypoint for the research family."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import RepoPathParser  # noqa: E402
from dispatch_identity import add_identity_arguments, resolve_identity  # noqa: E402
from modules.assistant import assistant_activities as act_shared  # noqa: E402
from modules.journal import journal_activities as journal  # noqa: E402
from modules.assistant.research.research import research_workflow as rw  # noqa: E402
from modules.assistant.research.research_refresh_parent import research_refresh_parent_workflow as rr  # noqa: E402
from modules.assistant.research import research_activities as act  # noqa: E402

BANNER = "=" * 64

def main(argv=None) -> int:
    p = RepoPathParser(prog="research", description="Produce or revalidate a research pool.")
    # DECLARED AS A REPO PATH — the argument's own help says *"relative to the
    # repo root"*, and nothing enforced it: the pool was joined onto `repo_root`
    # unchecked, so `research ../../../../tmp/x` researched into `/tmp` under
    # `--dangerously-skip-permissions`.
    #
    # `must_exist=False` PRESERVES THIS FAMILY'S BEHAVIOUR EXACTLY, and the
    # exemption is from the existence pass only — the escape pass, which is the
    # one this closes, still runs. Nothing in the research family `mkdir`s its
    # pool, and its `--dry-run` reports `0 due papers` for an absent one rather
    # than failing, so requiring existence would make an escape fix into a
    # behaviour change for a family this PR is not otherwise touching.
    p.add_repo_path("research_dir", kind="dir", must_exist=False,
                    help="research folder, relative to the repo root")
    p.add_argument("--refresh", action="store_true", help="revalidate DUE papers instead of researching new topics")
    # NOT a repo path, deliberately: a task file is context the operator supplies
    # from wherever they wrote it, routinely /tmp, and is read rather than
    # written. `--phase` on the build runners is the same case. A RELATIVE one is
    # still anchored to the repo root — `act_shared.anchor_task_source` — which is
    # a base, not a boundary, and is why the read below sits inside the preflight
    # try rather than beside the workflow call.
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
    wt = f"research-{int(time.time())}"

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
            print(f"  Mode      : {'refresh' if a.refresh else 'research'}")
            print(f"  Pool      : {research_dir}")
            print(f"  Due papers: {len(due)}" + (" — clean no-op exit" if a.refresh and not due else ""))
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
                             workflow_key="research", worktree_name=wt)

        result = rr.run_research_refresh(research_dir=research_dir, repo_root=repo_root,
                                         worktree_name=wt, verbose=a.verbose) if a.refresh \
            else rw.run_research(research_dir=research_dir, repo_root=repo_root, worktree_name=wt,
                                 context=context, pr_number=a.pr_number, verbose=a.verbose)
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1

    print()
    print(BANNER)
    v = result.get("verdict")
    print(f"  {result.get('pr_url') or 'no PR'} — {v.value if v else 'no papers due'}")
    print(BANNER)
    for n in result.get("notes", []):
        print(f"  {n}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

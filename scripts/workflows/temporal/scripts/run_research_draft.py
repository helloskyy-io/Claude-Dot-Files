"""Kickoff entrypoint for research-draft — one topic, one paper, one PR.

THE FAMILY RULING FOR ALL SIX OF THIS PHASE'S ADAPTERS IS IN
`run_build_draft.py`'s module docstring, and is not restated here.

Differs from `run_build_draft.py` because the pool is a REPO PATH and is declared
through `RepoPathParser.add_repo_path` rather than `add_argument`. A research
pool is a directory inside the tree the run was pointed at, and joining an
operator string onto `repo_root` unchecked is what let `research
../../../../tmp/x` research into `/tmp` under `--dangerously-skip-permissions`.
The build four have no equivalent argument: their task source is deliberately
read from wherever the operator wrote it, routinely /tmp.

`must_exist=False` MIRRORS `run_research.py` EXACTLY, and the exemption is from
the existence pass only — the escape pass, which is the one that matters, still
runs. Nothing in the research family `mkdir`s its pool. Diverging from the parent
here would mean this child accepted a pool its own parent refuses, or refused one
its parent accepts.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import RepoPathParser, refuse  # noqa: E402
from dispatch_identity import add_identity_arguments, resolve_identity  # noqa: E402
from dispatch_context import RunContext  # noqa: E402

from modules.journal import journal_activities as journal  # noqa: E402
from modules.assistant import assistant_activities as act  # noqa: E402
from modules.assistant.research.research_draft.research_draft_workflow import (  # noqa: E402
    run_research_draft)

BANNER = "=" * 64

WORKFLOW_KEY = "research-draft"


def main(argv: list[str] | None = None) -> int:
    p = RepoPathParser(
        prog="research-draft",
        description="Research one topic, write the paper and the synthesis, and "
                    "open a PR. Nothing verifies it — this is research's first "
                    "child, invoked alone.")
    p.add_repo_path("research_dir", kind="dir", must_exist=False,
                    help="research folder, relative to the repo root")
    # NOT a repo path, deliberately: context is supplied from wherever the
    # operator wrote it, routinely /tmp, and is read rather than written. A
    # RELATIVE one is still anchored to the repo root by `anchor_task_source` —
    # a base, not a boundary.
    p.add_argument("--task-file", dest="task_file", help="context from a file")
    p.add_argument("--repo", dest="repo_target",
                   help="target repo — a FILESYSTEM PATH, never a gh slug")
    p.add_argument("--pr", dest="pr_number", help="update an existing research PR")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--dry-run", action="store_true",
                   help="state what this run derived; no model, no worktree, no spend")
    add_identity_arguments(p)

    try:
        a, repo_root, resolved = p.parse_with_preflight(argv)
        # READ INSIDE THIS try, so a bad `--task-file` prints the same one-line
        # diagnostic as a bad `--repo` instead of a traceback. Both are operator
        # input and neither has created anything yet.
        context = act.task_context(repo_root, a.task_file)
    except RuntimeError as exc:
        # Nothing has been created yet — that is the point of preflight.
        return refuse(exc)

    research_dir = resolved["research_dir"]
    target = str(research_dir.relative_to(repo_root))

    if a.dry_run:
        print(f"{BANNER}\n  DRY RUN — nothing invoked, nothing posted\n{BANNER}")
        print(RunContext.for_dry_run(repo_root=repo_root, workflow_key=WORKFLOW_KEY,
                                     pr_number=a.pr_number, target=target).render())
        return 0

    try:
        ctx = RunContext.build(identity=resolve_identity(argv), repo_root=repo_root,
                               workflow_key=WORKFLOW_KEY, pr_number=a.pr_number,
                               target=target)
        ctx.echo()
        journal.open_run_bag(run_id=ctx.run_id, writer=ctx.writer,
                             repo_root=ctx.repo_root,
                             workflow_key=ctx.workflow_key,
                             worktree_name=ctx.worktree_name,
                             journal_root=ctx.journal_root)

        ref = act.base_ref(a.pr_number, repo_root)
        worktree = act.worktree_add(repo_root, ctx.worktree_name, ref)

        pr_url = run_research_draft(
            research_dir=research_dir, repo_root=repo_root, worktree=worktree,
            context=context, pr_number=a.pr_number, verbose=a.verbose,
        )
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        return refuse(exc)

    print(f"\n{BANNER}\n  RESEARCH-DRAFT COMPLETE — the papers are UNVERIFIED\n{BANNER}",
          file=sys.stderr)
    print("  verify it with:  ./research_refine.sh <pool> --pr <n>\n"
          "  clean up with :  /cleanup-merged-worktrees", file=sys.stderr)
    print(pr_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

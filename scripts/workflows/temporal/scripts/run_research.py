"""Kickoff entrypoint for the research family."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import RepoPathParser  # noqa: E402
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
    # written. `--phase` on the build runners is the same case.
    p.add_argument("--task-file", dest="task_file", help="context from a file")
    p.add_argument("--repo", dest="repo_target", help="target repo — a FILESYSTEM PATH, never a gh slug")
    p.add_argument("--pr", dest="pr_number", help="update an existing research PR")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="compute the gate and render; no model, no spend")

    try:
        a, repo_root, resolved = p.parse_with_preflight(argv)
    except RuntimeError as exc:
        # Nothing has been created yet — that is the point of preflight.
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1
    research_dir = resolved["research_dir"]
    context = Path(a.task_file).read_text() if a.task_file else ""
    import time
    wt = f"research-{int(time.time())}"

    try:
        if a.dry_run:
            table, due = act.paper_currency(research_dir)
            print(f"{BANNER}\n  DRY RUN — nothing invoked, nothing posted\n{BANNER}")
            print(f"  Mode      : {'refresh' if a.refresh else 'research'}")
            print(f"  Pool      : {research_dir}")
            print(f"  Due papers: {len(due)}" + (" — clean no-op exit" if a.refresh and not due else ""))
            for d in due:
                print(f"    - {d.name}")
            return 0
        # REQUIREMENT 11 — the run's bag is opened BEFORE the first side effect.
        # Not a helper this file is asked to remember: the sweep in
        # tests/unit/test_every_parent_opens_a_run_bag.py fails when an
        # entrypoint lacks this call, which is what makes the journal
        # structurally present rather than merely available. Nothing writes into
        # the bag until Phase 3; a root that will not resolve stops the run here
        # (r9), before a worktree exists and before a token is spent.
        journal.open_run_bag(run_id=journal.mint_run_id(), repo_root=repo_root,
                             workflow_key="research")

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

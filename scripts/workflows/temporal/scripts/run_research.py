"""Kickoff entrypoint for the research family."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import preflight  # noqa: E402
from modules.assistant.research.research import research_workflow as rw  # noqa: E402
from modules.assistant.research.research_refresh_parent import research_refresh_parent_workflow as rr  # noqa: E402
from modules.assistant.research import research_activities as act  # noqa: E402

BANNER = "=" * 64

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="research", description="Produce or revalidate a research pool.")
    p.add_argument("research_dir", help="research folder, relative to the repo root")
    p.add_argument("--refresh", action="store_true", help="revalidate DUE papers instead of researching new topics")
    p.add_argument("--task-file", dest="task_file", help="context from a file")
    p.add_argument("--repo", dest="repo_target", help="target repo — a FILESYSTEM PATH, never a gh slug")
    p.add_argument("--pr", dest="pr_number", help="update an existing research PR")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="compute the gate and render; no model, no spend")
    a = p.parse_args(argv)

    try:

        repo_root = preflight(a.repo_target)

    except RuntimeError as exc:

        # Nothing has been created yet — that is the point of preflight.

        print(f"\n✗ {exc}", file=sys.stderr)

        return 1
    research_dir = repo_root / a.research_dir
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

"""Kickoff entrypoint for research-minor — ONE paper, no synthesis.

A SEPARATE ENTRY RATHER THAN A `--minor` FLAG ON `run_research.py`, for the same
reason `run_build_minor.py` sits beside `run_build.py`: the two dispatch
different parents with different children, different model keys and different
turn budgets. A flag would put one CLI in front of two workflows and make the
shape a runtime branch — which is the coupling the sibling shape exists to
avoid. `--refresh` on `run_research.py` is not a counter-example: refresh is the
same pool being revalidated, not a different pool shape.
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import preflight  # noqa: E402
from modules.assistant.research.research_minor import research_minor_workflow as rm  # noqa: E402
from modules.assistant.research import research_activities as act  # noqa: E402

BANNER = "=" * 64


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="research-minor",
        description="Research ONE question as ONE paper. No topic list, no synthesis.",
    )
    p.add_argument("research_dir", help="research folder, relative to the repo root")
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
    wt = f"research-minor-{int(time.time())}"

    try:
        if a.dry_run:
            table, due = act.paper_currency(research_dir)
            print(f"{BANNER}\n  DRY RUN — nothing invoked, nothing posted\n{BANNER}")
            print("  Mode      : research-minor (ONE paper, no synthesis)")
            print(f"  Pool      : {research_dir}")
            print(f"  Existing  : {len(due)} of the papers present are past their window")
            for d in due:
                print(f"    - {d.name}")
            return 0
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

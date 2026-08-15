"""Kickoff entrypoint for plan-sprint."""
from __future__ import annotations
import argparse, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import preflight  # noqa: E402
from modules.assistant.plan import plan_activities as act  # noqa: E402
from modules.assistant.plan.plan_sprint import plan_sprint_workflow as wf  # noqa: E402

BANNER = "=" * 64

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="plan-sprint",
        description="Place the ruled candidates and keep the sprint plan current. "
                    "Places; does not rule (that is triage_candidates.sh) and does not design.")
    p.add_argument("--repo", dest="repo_target", help="target repo — a FILESYSTEM PATH, never a gh slug")
    p.add_argument("--sprint", default="docs/development/sprint.md")
    p.add_argument("--candidates", default="docs/standards/architecture/research/candidates.md")
    p.add_argument("--research", default="docs/standards/architecture/research")
    p.add_argument("--pr", dest="pr_number", help="update an existing plan-sprint PR")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="count and render; no model, no spend")
    a = p.parse_args(argv)

    try:
        repo_root = preflight(a.repo_target)
    except RuntimeError as exc:
        # Nothing has been created yet — that is the point of preflight.
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1

    sprint, cands = repo_root / a.sprint, repo_root / a.candidates
    research = repo_root / a.research
    for label, path in (("sprint", sprint), ("candidates", cands), ("research", research)):
        if not path.exists():
            print(f"\n✗ {label} not found: {path}", file=sys.stderr)
            return 1

    try:
        counts = act.candidate_counts(cands)
        if a.dry_run:
            print(f"{BANNER}\n  DRY RUN — nothing invoked, nothing posted\n{BANNER}")
            print(f"  Sprint     : {sprint.relative_to(repo_root)}")
            print(f"  Candidates : {counts['total']} total · {counts['triaged']} ruled (your set) · {counts['untriaged']} untriaged (NOT yours)")
            print(f"  Max turns  : {wf.MAX_TURNS} (estimate — no V1 to derive from)")
            # THE SAME ASSEMBLY THE LIVE RUN USES, called rather than copied.
            # This branch used to hand-build the dict, and the hand-built copy is
            # how this workflow shipped a dry run that previewed a DIFFERENT
            # prompt from the one dispatched (see `wf.correction_note`). Patching
            # the copy fixed the instance and left the shape; calling the live
            # assembly removes it.
            rendered = act.render(
                act.load_prompt(wf.PROMPTS / "plan_sprint.md"),
                wf.prompt_values(str(sprint.relative_to(repo_root)),
                                 cands.relative_to(repo_root),
                                 research.relative_to(repo_root),
                                 repo_root, counts, False, None))
            print(f"  Prompt     : {len(rendered.encode())} bytes rendered, 0 placeholders remaining")
            return 0

        worktree = act.worktree_add(repo_root, f"plan-sprint-{int(time.time())}", "HEAD")
        url = wf.run_plan_sprint(repo_root=repo_root, worktree=worktree, sprint_path=sprint,
                                 candidates_path=cands, research_dir=research,
                                 pr_number=a.pr_number, verbose=a.verbose)
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1

    print(f"\n{BANNER}\n  {url}\n{BANNER}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

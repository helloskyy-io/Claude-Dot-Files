"""Kickoff entrypoint for triage-candidates."""
from __future__ import annotations
import argparse, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import preflight  # noqa: E402
from modules.assistant.plan import plan_activities as act  # noqa: E402
from modules.assistant.plan.triage_candidates import triage_candidates_activities as own  # noqa: E402
from modules.assistant.plan.triage_candidates import triage_candidates_workflow as wf  # noqa: E402

BANNER = "=" * 64

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="triage-candidates",
        description="Rule every untriaged research candidate. Decides; does not place or design.")
    p.add_argument("--repo", dest="repo_target", help="target repo — a FILESYSTEM PATH, never a gh slug")
    p.add_argument("--candidates", default="docs/standards/architecture/research/candidates.md")
    p.add_argument("--research", default="docs/standards/architecture/research")
    p.add_argument("--pr", dest="pr_number", help="update an existing triage-candidates PR")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="count and render; no model, no spend")
    a = p.parse_args(argv)

    try:
        repo_root = preflight(a.repo_target)
    except RuntimeError as exc:
        # Nothing has been created yet — that is the point of preflight.
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1

    cands, research = repo_root / a.candidates, repo_root / a.research
    for label, path in (("candidates", cands), ("research", research)):
        if not path.exists():
            print(f"\n✗ {label} not found: {path}", file=sys.stderr)
            return 1

    try:
        counts = act.candidate_counts(cands)
        if a.dry_run:
            print(f"{BANNER}\n  DRY RUN — nothing invoked, nothing posted\n{BANNER}")
            print(f"  Candidates : {counts['total']} total · {counts['untriaged']} UNTRIAGED · {counts['triaged']} ruled")
            print(f"  Max turns  : {wf.MAX_TURNS} (estimate — nothing has measured this workflow)")
            rendered = act.render(act.load_prompt(wf.PROMPTS / "triage_candidates.md"), {
                "CANDIDATES_PATH": a.candidates, "RESEARCH_DIR": a.research,
                "WORKING_SET": wf._working_set(counts),
                "DIRECTION_CEILING": own.direction_ceiling(research),
                "EXISTING_WORK": act.existing_work(repo_root, research),
                "SUBMIT_PROMPT": act.submit_prompt(None, "x"),
                "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
                "HEADLESS_EXECUTION_GUARD": act.shared_prompt("headless_execution_guard")})
            print(f"  Prompt     : {len(rendered)} bytes rendered, 0 placeholders remaining")
            return 0

        worktree = act.worktree_add(repo_root, f"triage-candidates-{int(time.time())}", "HEAD")
        url = wf.run_triage_candidates(repo_root=repo_root, worktree=worktree,
                                       candidates_path=cands, research_dir=research,
                                       pr_number=a.pr_number, verbose=a.verbose)
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1

    print(f"\n{BANNER}\n  {url}\n{BANNER}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

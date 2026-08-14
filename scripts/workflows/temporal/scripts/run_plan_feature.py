"""Kickoff entrypoint for plan-feature.

Lives in scripts/ because it is a launch concern, not a workflow concern. When
the Temporal path exists this is replaced by a client that starts the workflow
on a task queue; the workflow module itself does not change.
"""
from __future__ import annotations
import argparse, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import preflight  # noqa: E402
from modules.assistant.plan import plan_activities as act  # noqa: E402
from modules.assistant.plan.plan_feature import plan_feature_activities as own  # noqa: E402
from modules.assistant.plan.plan_feature import plan_feature_workflow as wf  # noqa: E402

BANNER = "=" * 64

# A default, not a derivation — the repo's own surface. A different repo passes
# its own. Stated here rather than in the workflow so the workflow stays
# repo-agnostic and the launch concern owns the convention.
DEFAULT_CANDIDATES = "docs/standards/architecture/research/candidates.md"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="plan-feature",
        description="Write ONE component's roadmap.md and phase docs from its research. "
                    "Writes no sprint entry and estimates no hours.")
    p.add_argument("component",
                   help="the component directory, e.g. docs/development/fleet-reliability")
    p.add_argument("--repo", dest="repo_target", help="target repo — a FILESYSTEM PATH, never a gh slug")
    p.add_argument("--candidates", default=DEFAULT_CANDIDATES)
    p.add_argument("--pr", dest="pr_number", help="update an existing plan-feature PR")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="count and render; no model, no spend")
    a = p.parse_args(argv)

    try:
        repo_root = preflight(a.repo_target)
    except RuntimeError as exc:
        # Nothing has been created yet — that is the point of preflight.
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1

    # RESOLVED AGAINST THE REPO, and rejected if it escapes. `--repo` and a
    # component path are two independent operator inputs, and `../../elsewhere`
    # would otherwise plan a directory outside the tree the run is reviewing.
    component = (repo_root / a.component).resolve()
    cands = repo_root / a.candidates
    if not component.is_relative_to(repo_root):
        print(f"\n✗ component {a.component} resolves outside the repo: {component}",
              file=sys.stderr)
        return 1
    for label, path in (("component", component), ("candidates", cands)):
        if not path.exists():
            print(f"\n✗ {label} not found: {path}", file=sys.stderr)
            return 1
    if not component.is_dir():
        print(f"\n✗ component is not a directory: {component}", file=sys.stderr)
        return 1

    try:
        if a.dry_run:
            rel = component.relative_to(repo_root)
            print(f"{BANNER}\n  DRY RUN — nothing invoked, nothing posted\n{BANNER}")
            print(f"  Component  : {rel}")
            print(f"  Phase docs : {len(own.phase_docs(component))} · "
                  f"roadmap.md {'present' if (component / 'roadmap.md').is_file() else 'ABSENT'}")
            print(f"  Max turns  : {wf.MAX_TURNS} (estimate — nothing has measured this workflow)")
            print(f"  Grants     : {', '.join(wf.permitted_paths(rel))}")
            rendered = act.render(act.load_prompt(wf.PROMPTS / "plan_feature.md"), {
                "COMPONENT_PATH": str(rel), "COMPONENT_NAME": rel.name,
                "CANDIDATES_PATH": a.candidates,
                "PLANNING_STATE": own.planning_state(component, repo_root),
                "RESEARCH_INVENTORY": own.research_inventory(component, repo_root),
                "EVIDENCE_BLOCK": act.evidence_block(repo_root),
                "SUBMIT_PROMPT": act.submit_prompt(None, "x"),
                "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
                "HEADLESS_EXECUTION_GUARD": act.shared_prompt("headless_execution_guard")})
            print(f"  Prompt     : {len(rendered)} bytes rendered, 0 placeholders remaining")
            return 0

        worktree = act.worktree_add(repo_root, f"plan-feature-{int(time.time())}", "HEAD")
        url = wf.run_plan_feature(repo_root=repo_root, worktree=worktree,
                                  component=component, candidates_path=cands,
                                  pr_number=a.pr_number, verbose=a.verbose)
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        # These carry operator-facing recovery instructions from the layer that
        # knew what failed. Do not wrap or reformat them.
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1

    print(f"\n{BANNER}\n  {url}\n{BANNER}")
    print("\nNOT SIZED — `plan-verify` estimates the phases, and it does not exist yet.")
    print("NO SPRINT ENTRY — the PR body names the one this component needs; it lands by operator edit.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

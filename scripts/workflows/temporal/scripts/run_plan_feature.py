"""Kickoff entrypoint for plan-feature.

Lives in scripts/ because it is a launch concern, not a workflow concern. When
the Temporal path exists this is replaced by a client that starts the workflow
on a task queue; the workflow module itself does not change.
"""
from __future__ import annotations
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import RepoPathParser  # noqa: E402
from modules.assistant.plan import plan_activities as act  # noqa: E402
from modules.assistant.plan.plan_feature import plan_feature_activities as own  # noqa: E402
from modules.assistant.plan.plan_feature import plan_feature_workflow as wf  # noqa: E402

BANNER = "=" * 64

# A default, not a derivation — the repo's own surface. A different repo passes
# its own. Stated here rather than in the workflow so the workflow stays
# repo-agnostic and the launch concern owns the convention.
DEFAULT_CANDIDATES = "docs/standards/architecture/research/candidates.md"


def main(argv=None) -> int:
    p = RepoPathParser(prog="plan-feature",
        description="Write ONE component's roadmap.md and phase docs from its research. "
                    "Writes no sprint entry and estimates no hours.")
    # DECLARED AS REPO PATHS, WHICH IS WHAT INSTALLS THE CHECK. `--repo` and a
    # component path are two independent operator inputs, and `../../elsewhere`
    # would otherwise plan a directory outside the tree the run is reviewing.
    # BOTH ARE DECLARED, not only the component one. `--candidates` is as
    # free-form as the component argument, and the two paths through this script
    # disagreed about it: the live run relativises it against the repo while the
    # dry run printed the raw argument, so an absolute `--candidates` previewed
    # one prompt and dispatched another — the exact drift `wf.prompt_values`
    # exists to make impossible. Resolved once, so both branches read the same
    # value and an escape is refused before either runs.
    #
    # AND DECLARED RATHER THAN RESOLVED BY HAND. This file called
    # `resolve_operator_paths` correctly, with a dict it retyped from its own
    # arguments — and five sibling runners had no such call at all. A check a
    # runner must remember is one the next runner omits, invisibly; a
    # declaration that IS the check has nothing to omit.
    p.add_repo_path("component", kind="dir",
                    help="the component directory, e.g. docs/development/fleet-reliability")
    p.add_argument("--repo", dest="repo_target", help="target repo — a FILESYSTEM PATH, never a gh slug")
    p.add_repo_path("--candidates", default=DEFAULT_CANDIDATES)
    p.add_argument("--pr", dest="pr_number", help="update an existing plan-feature PR")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="count and render; no model, no spend")

    try:
        a, repo_root, resolved = p.parse_with_preflight(argv)
    except RuntimeError as exc:
        # Nothing has been created yet — that is the point of preflight.
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1
    component, cands = resolved["component"], resolved["candidates"]

    try:
        if a.dry_run:
            rel = component.relative_to(repo_root)
            print(f"{BANNER}\n  DRY RUN — nothing invoked, nothing posted\n{BANNER}")
            print(f"  Component  : {rel}")
            print(f"  Phase docs : {len(own.phase_docs(component))} · "
                  f"roadmap.md {'present' if (component / 'roadmap.md').is_file() else 'ABSENT'}")
            print(f"  Max turns  : {wf.MAX_TURNS} (estimate — nothing has measured this workflow)")
            print(f"  Grants     : {', '.join(wf.permitted_paths(rel, cands.relative_to(repo_root)))}")
            # THE SAME ASSEMBLY THE LIVE RUN USES, called rather than copied. A
            # dry run that builds its own values dict previews a prompt that is
            # not the one dispatched — the family has shipped that bug once
            # already (see `plan_sprint`'s `correction_note`), and an operator
            # checking the wrong artifact is worse than checking none.
            rendered = act.render(
                act.load_prompt(wf.PROMPTS / "plan_feature.md"),
                wf.prompt_values(rel, cands.relative_to(repo_root), repo_root, None))
            print(f"  Prompt     : {len(rendered.encode())} bytes rendered, 0 placeholders remaining")
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
    print("\nNOT SIZED — `plan-verify` estimates the phases. Run plan_verify.sh against")
    print("this component next; `plan-project` already runs it here.")
    print("NO SPRINT ENTRY — the PR body names the one this component needs; it lands by operator edit.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Kickoff entrypoint for plan-sprint."""
from __future__ import annotations
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import RepoPathParser  # noqa: E402
from modules.journal import journal_activities as journal  # noqa: E402
from modules.assistant.plan import plan_activities as act  # noqa: E402
from modules.assistant.plan.plan_sprint import plan_sprint_workflow as wf  # noqa: E402

BANNER = "=" * 64

def main(argv=None) -> int:
    p = RepoPathParser(prog="plan-sprint",
        description="Place the ruled candidates and keep the sprint plan current. "
                    "Places; does not rule (that is triage_candidates.sh) and does not design.")
    p.add_argument("--repo", dest="repo_target", help="target repo — a FILESYSTEM PATH, never a gh slug")
    # ALL THREE DECLARED AS REPO PATHS. This runner used to join them onto
    # `repo_root` unchecked and then test only `.exists()` — and `.exists()`
    # FOLLOWS `..`, so `--candidates ../../../../tmp/x/candidates.md` passed it,
    # was handed to the prompt, and was read and written by a run executing under
    # `--dangerously-skip-permissions`. Demonstrated by execution on 2026-08-15,
    # not argued.
    #
    # `Path.relative_to` WOULD NOT HAVE CAUGHT IT EITHER, which is why the fix is
    # a resolver and not an extra `if`: it is lexical, so `repo_root/"../../x"`
    # still reads as being under `repo_root`. The `..` has to be collapsed first,
    # which is `.resolve()`'s job and `resolve_operator_paths`' whole subject.
    p.add_repo_path("--sprint", default="docs/development/sprint.md")
    p.add_repo_path("--candidates", default="docs/standards/architecture/research/candidates.md")
    p.add_repo_path("--research", kind="dir", default="docs/standards/architecture/research")
    p.add_argument("--pr", dest="pr_number", help="update an existing plan-sprint PR")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="count and render; no model, no spend")

    try:
        a, repo_root, resolved = p.parse_with_preflight(argv)
    except RuntimeError as exc:
        # Nothing has been created yet — that is the point of preflight.
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1

    sprint, cands, research = resolved["sprint"], resolved["candidates"], resolved["research"]

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

        # REQUIREMENT 11 — the run's bag is opened BEFORE the first side effect.
        # Not a helper this file is asked to remember: the sweep in
        # tests/unit/test_every_parent_opens_a_run_bag.py fails when an
        # entrypoint lacks this call, which is what makes the journal
        # structurally present rather than merely available. Nothing writes into
        # the bag until Phase 3; a root that will not resolve stops the run here
        # (r9), before a worktree exists and before a token is spent.
        journal.open_run_bag(run_id=journal.mint_run_id(), repo_root=repo_root,
                             workflow_key="plan-sprint")

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

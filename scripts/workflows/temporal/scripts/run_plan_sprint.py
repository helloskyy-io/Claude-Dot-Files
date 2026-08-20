"""Kickoff entrypoint for plan-sprint."""
from __future__ import annotations
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import RepoPathParser  # noqa: E402
from modules.assistant import assistant_activities as act_shared  # noqa: E402
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
    p.add_repo_path("component", kind="dir",
                    help="the planned component, e.g. docs/development/workflow-decomposition")
    p.add_repo_path("--sprint", default="docs/development/sprint.md")
    p.add_argument("--pr", dest="pr_number", help="update an existing plan-sprint PR")
    p.add_argument("--task-file", dest="task_file",
                   help="operator context or a correction runway, from a file")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="count and render; no model, no spend")

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

    sprint, component = resolved["sprint"], resolved["component"]

    try:
        sizing = act.phase_sizing(component)
        if a.dry_run:
            print(f"{BANNER}\n  DRY RUN — nothing invoked, nothing posted\n{BANNER}")
            print(f"  Component  : {component.relative_to(repo_root)}")
            print(f"  Sprint     : {sprint.relative_to(repo_root)}")
            print(f"  Phases     : {len(sizing.rows)} · {len(sizing.unsized)} unsized")
            print(f"  TOTAL      : {sizing.total:g} h  (summed in code, not by the model)")
            print(f"  Max turns  : {wf.MAX_TURNS} (estimate — no V1 to derive from)")
            print(f"  Grants     : {', '.join(wf.permitted_paths(str(sprint.relative_to(repo_root))))}")
            rendered = act.render(
                act.load_prompt(wf.PROMPTS / "plan_sprint.md"),
                wf.prompt_values(str(sprint.relative_to(repo_root)),
                                 component.relative_to(repo_root), repo_root, False, None, context),
                opaque=frozenset({"TASK_CONTEXT"}))
            print(f"  Prompt     : {len(rendered.encode())} bytes rendered, 0 placeholders remaining")
            return 0

        # REQUIREMENT 11 — the run's bag is opened BEFORE the first side
        # effect, and a root that will not resolve stops the run here (r9). Why
        # this is not a helper each file remembers to call, and what the sweep
        # that enforces it can and cannot see: `journal_activities.py`'s module
        # docstring and `tests/unit/test_every_parent_opens_a_run_bag.py`. Said
        # once there rather than eleven times here.
        worktree_name = f"plan-sprint-{int(time.time())}"
        journal.open_run_bag(run_id=journal.mint_run_id(), repo_root=repo_root,
                             workflow_key="plan-sprint",
                             worktree_name=worktree_name)

        # A `--pr` PASS MUST START FROM THE WORK IT IS CORRECTING. Hard-coding
        # "HEAD" put the run on `main`, so a correction pass opened a worktree
        # with none of the PR's files in it. Measured on plan-feature's first
        # correction pass: the counted-in-code block reported "0 phase doc(s)"
        # — true of the worktree it was handed, false of the four docs it was
        # told to correct — and the run spent turns fetching and checking out
        # the branch itself before it could begin. All four `--pr`-accepting
        # plan runners had the same line; `research_minor_workflow.py` already
        # had the right one and is where this expression comes from.
        ref = act.base_ref(a.pr_number, repo_root)
        worktree = act.worktree_add(repo_root, worktree_name, ref)
        url = wf.run_plan_sprint(repo_root=repo_root, worktree=worktree,
                                 sprint_path=sprint, component=component,
                                 pr_number=a.pr_number, context=context,
                                 verbose=a.verbose)
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1

    print(f"\n{BANNER}\n  {url}\n{BANNER}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

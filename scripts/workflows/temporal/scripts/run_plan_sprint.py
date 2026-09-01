"""Kickoff entrypoint for plan-sprint."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import RepoPathParser  # noqa: E402
from dispatch_identity import add_identity_arguments, resolve_identity  # noqa: E402
from dispatch_context import RunContext  # noqa: E402
from modules.assistant.review_pr import review_pr_activities as review_act  # noqa: E402
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
                    help="the planned component, e.g. /opt/skyy-net/skyynet-master-planning/development/edge-assistant/workflow-decomposition")
    p.add_repo_path("--sprint", default="development/sprints.md")
    p.add_argument("--pr", dest="pr_number", help="update an existing plan-sprint PR")
    p.add_argument("--task-file", dest="task_file",
                   help="operator context or a correction runway, from a file")
    # THE PARENT COULD SET THIS AND AN OPERATOR COULD NOT, WHICH MADE A
    # HAND-DISPATCHED CORRECTION SILENTLY RUN THE DEFAULT JOB. `disposition.md`
    # tells an operator to dispatch this child by hand against a held PR; the
    # flag drives a real prompt substitution (`${CORRECTION_NOTE}`) and was
    # reachable only from `plan_workflow`. Measured on MDC #204: dispatched at a
    # PR carrying nine findings, the run re-derived its estimates, concurred with
    # all of them, reported success, and closed nothing — $8.60 and 64 turns, and
    # the failure was invisible because the run was correct for the pass it was
    # actually given. The documented workaround was to write "THIS IS A
    # CORRECTION PASS" into a `--task-file`, which is this flag wearing a costume.
    p.add_argument("--correction-pass", dest="correction_pass", action="store_true",
                   help="a prior disposition returned HOLD with a scoped runway; close it")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="count and render; no model, no spend")

    add_identity_arguments(p)
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

    # A HELD PR DISPATCHED WITHOUT `--correction-pass` IS ALMOST ALWAYS THE FLAG
    # BEING FORGOTTEN, and the run that follows is the expensive-and-invisible one
    # `--correction-pass` above describes. REFUSED rather than warned: a wrong
    # refusal costs one re-invocation with a flag this message names, and a wrong
    # PROCEED was measured at $8.60, 64 turns, nine findings left open, and a
    # success report on top. Asked in preflight, before any worktree exists, per
    # the standard's "validate arguments before doing anything destructive".
    #
    # AN UNREADABLE THREAD IS NOT A CLEAN ONE. `unclosed_hold` answers None when
    # it could not read, which degrades to a warning: an offline machine or a
    # rate limit must not block work, and must not read as all-clear either.
    if a.pr_number and not a.correction_pass:
        held = review_act.unclosed_hold(a.pr_number, repo_root)
        if held is None:
            print(f"  ! could not read PR {a.pr_number}'s thread, so an open hold "
                  f"cannot be ruled out; proceeding with the default pass.",
                  file=sys.stderr)
        elif held:
            print(f"\n\u2717 PR {a.pr_number} carries {len(held)} finding(s) still on "
                  f"`disposition: hold`: {', '.join(held)}.\n"
                  f"  This run would do its DEFAULT job, close none of them, and "
                  f"report success.\n"
                  f"  Re-run with --correction-pass to close the runway, or pass "
                  f"--task-file if you meant something else.", file=sys.stderr)
            return 1

    try:
        sizing = act.phase_sizing(component)
        if a.dry_run:
            print(f"{BANNER}\n  DRY RUN — nothing invoked, nothing posted\n{BANNER}")
            # THE TREE THE COUNTS CAME FROM, NAMED RATHER THAN LEFT TO BE
            # ASSUMED. No worktree exists on a dry run, so every figure below is
            # read off THIS checkout — while a `--pr` run cuts its worktree from
            # `origin/<the PR's branch>` and reads nothing else. Two trees, and
            # on the correction pass a `--pr` dry run exists for, they routinely
            # differ: the work being corrected is on the branch and need not be
            # in this checkout at all. In that state the figures below read `0`
            # for artifacts that are fully written.
            #
            # THIS IS THE MINIMUM AND IT IS KNOWN TO BE. Issue #134 offered two
            # remedies and the operator ruled the smaller one on 2026-08-24, on
            # measured evidence: `--dry-run` appears ZERO times in the operator's
            # shell history and is documented in no guide, skill or command —
            # all 32 uses in the run logs are dispatches verifying these runners
            # while building them. The stronger remedy — read `origin/<branch>`
            # so the preview is an actual preview — needs the count helpers to
            # take a tree rather than a path, and earns itself when real use
            # appears. Same line as `run_plan_refine.py`, which shipped it first.
            # THE SAME OBJECT THE LIVE RUN PRINTS, rendered by the same method. A
            # rehearsal that assembles its own copy previews something that is not
            # what runs, which is the bug this family has already shipped once.
            print(RunContext.for_dry_run(repo_root=repo_root, workflow_key="plan-sprint",
                                         pr_number=a.pr_number,
                                         target=str(component.relative_to(repo_root))).render())
            print(f"  Counted in : this checkout ({repo_root}) — a dry run cuts no worktree")
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
        # EVERYTHING THIS RUN DERIVED, BUILT ONCE AND SAID OUT LOUD BEFORE THE
        # BAG OPENS, THE WORKTREE IS CUT OR ANY `gh` CALL RUNS. Identity comes
        # from outside the process (Phase 9 r2/r4, `dispatch_identity.py`); the
        # worktree name is a FIELD rather than an expression here, because
        # eleven copies of that expression in three spellings was the defect
        # (`dispatch_context.py`).
        ctx = RunContext.build(identity=resolve_identity(argv), repo_root=repo_root,
                               workflow_key="plan-sprint", pr_number=a.pr_number,
                               target=str(component.relative_to(repo_root)))
        ctx.echo()
        journal.open_run_bag(run_id=ctx.run_id, writer=ctx.writer,
                             repo_root=ctx.repo_root,
                             workflow_key=ctx.workflow_key,
                             worktree_name=ctx.worktree_name,
                             journal_root=ctx.journal_root)

        # A `--pr` PASS MUST START FROM THE WORK IT IS CORRECTING. Hard-coding
        # "HEAD" put the run on `main`, so a correction pass opened a worktree
        # with none of the PR's files in it. Measured on plan-draft's first
        # correction pass: the counted-in-code block reported "0 phase doc(s)"
        # — true of the worktree it was handed, false of the four docs it was
        # told to correct — and the run spent turns fetching and checking out
        # the branch itself before it could begin. All four `--pr`-accepting
        # plan runners had the same line, and so did the research and build
        # families — ELEVEN call sites in all. The expression now lives once,
        # in `base_ref`, because a fix applied by hand to a list of eleven is a
        # fix applied to ten: the eleventh passed its base inline and the first
        # sweep of this did not see it.
        ref = act.base_ref(a.pr_number, repo_root)
        worktree = act.worktree_add(repo_root, ctx.worktree_name, ref)
        url = wf.run_plan_sprint(repo_root=repo_root, worktree=worktree,
                                 sprint_path=sprint, component=component,
                                 pr_number=a.pr_number, context=context,
                                 verbose=a.verbose,
                                 correction_pass=a.correction_pass)
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1

    print(f"\n{BANNER}\n  {url}\n{BANNER}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

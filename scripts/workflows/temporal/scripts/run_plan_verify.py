"""Kickoff entrypoint for plan-verify.

Lives in scripts/ because it is a launch concern, not a workflow concern. When
the Temporal path exists this is replaced by a client that starts the workflow
on a task queue; the workflow module itself does not change.
"""
from __future__ import annotations
import subprocess
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import RepoPathParser  # noqa: E402
from modules.journal import journal_activities as journal  # noqa: E402
from modules.assistant.plan import plan_activities as act  # noqa: E402
from modules.assistant.plan.plan_verify import plan_verify_activities as own  # noqa: E402
from modules.assistant.plan.plan_verify import plan_verify_workflow as wf  # noqa: E402

BANNER = "=" * 64

# A default, not a derivation — the repo's own surface. A different repo passes
# its own. Stated here rather than in the workflow so the workflow stays
# repo-agnostic and the launch concern owns the convention.
DEFAULT_CANDIDATES = "docs/standards/architecture/research/candidates.md"


def main(argv=None) -> int:
    p = RepoPathParser(prog="plan-verify",
        description="Read ONE component's roadmap and phase docs COLD, size every phase "
                    "in hours, and say where the plan is weakest. Writes no phase doc.")
    # DECLARED AS REPO PATHS, WHICH IS WHAT INSTALLS THE CHECK. `--repo` and a
    # component path are two independent operator inputs, and `../../elsewhere`
    # would otherwise size a plan outside the tree the run is reviewing. BOTH are
    # declared, not only the component one — `--candidates` is as free-form, and
    # the sibling runner shipped a drift where the live path relativised it and
    # the dry run printed the raw argument.
    #
    # THIS FILE USED TO CALL `resolve_operator_paths` BY HAND, correctly, with a
    # dict it retyped from its own arguments. That was right and it was not the
    # property: five sibling runners had no such call at all, and a check a
    # runner must remember cannot be missing in a way anything can read. The
    # declaration is now the check, so the dict has no author to forget it.
    p.add_repo_path("component", kind="dir",
                    help="the component directory, e.g. docs/development/fleet-reliability")
    p.add_argument("--repo", dest="repo_target", help="target repo — a FILESYSTEM PATH, never a gh slug")
    p.add_repo_path("--candidates", default=DEFAULT_CANDIDATES)
    p.add_argument("--pr", dest="pr_number", help="update an existing plan-verify PR")
    # NOT a repo path, deliberately — operator context from wherever they wrote it,
    # the same contract run_research_minor.py and run_plan_feature.py use. Without
    # it a `--pr` pass can push and cannot be TOLD why it is re-running.
    p.add_argument("--task-file", dest="task_file",
                   help="operator context or a correction runway, from a file")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="count and render; no model, no spend")

    try:
        a, repo_root, resolved = p.parse_with_preflight(argv)
    except RuntimeError as exc:
        # Nothing has been created yet — that is the point of preflight.
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1
    component, cands = resolved["component"], resolved["candidates"]
    context = Path(a.task_file).read_text() if a.task_file else ""

    # REFUSED BEFORE ANYTHING IS CREATED, not diagnosed after a dispatch. There
    # is nothing here to verify without a plan, and the failure a run would
    # otherwise reach is the UNSIZED post-condition — which says "you sized
    # nothing", a message whose obvious remedy is to write the plan this
    # workflow is forbidden to write. Preflight is the right altitude for a
    # precondition, per the class issue #49 records: a dead run must leave no
    # orphaned worktree behind it.
    # ON A `--pr` PASS THE PLAN LIVES ON THE PR'S BRANCH, NOT IN THIS CHECKOUT,
    # and asking the local tree is asking the wrong one. Measured 2026-08-19: PR
    # #130 carried a roadmap and six phase docs written minutes earlier, and this
    # refused the run because `main` had none — the exact plan it was pointed at,
    # declared missing. Third instance of the same class this week: PR #115 fixed
    # a worktree based on HEAD rather than the PR branch, and plan-verify's own
    # dry run counts from the repo for want of a worktree.
    #
    # `git cat-file -e` asks the branch the worktree will actually be built from,
    # which is the tree the run reads. A failure to resolve is treated as ABSENT
    # rather than as an error: an unreadable ref is a different problem, and the
    # message below names the one thing a caller can act on.
    plan_exists = (component / own.ROADMAP).is_file()
    if a.pr_number and not plan_exists:
        rel = (component / own.ROADMAP).relative_to(repo_root).as_posix()
        try:
            branch = act.pr_branch(a.pr_number, repo_root)
            probe = subprocess.run(
                ["git", "cat-file", "-e", f"origin/{branch}:{rel}"],
                cwd=repo_root, capture_output=True, text=True, timeout=30)
            plan_exists = probe.returncode == 0
        except (OSError, subprocess.SubprocessError, RuntimeError):
            pass
    if not plan_exists:
        print(f"\n✗ {component.relative_to(repo_root)} has no {own.ROADMAP}"
              + (f" — not here and not on PR #{a.pr_number}'s branch" if a.pr_number else "")
              + f": there is no plan to verify. Run plan_feature.sh against this "
              f"component first — writing the plan is its job and this workflow "
              f"holds no grant over a phase doc.", file=sys.stderr)
        return 1

    try:
        rel = component.relative_to(repo_root)
        if a.dry_run:
            phases = own.phase_docs_of(component)
            print(f"{BANNER}\n  DRY RUN — nothing invoked, nothing posted\n{BANNER}")
            print(f"  Component  : {rel}")
            # TWO DIFFERENT NUMBERS, LABELLED AS SUCH. A roadmap may link a
            # sibling component's phase docs — three of the MMF roadmap's nine
            # references are `persistent-memory-protocol`'s — so the reference
            # count runs ahead of the phase count on a correct plan, and an
            # operator reading them as one figure sees three missing files.
            print(f"  Phase docs : {len(phases)} of its own · "
                  f"{len(own.roadmap_phase_links(component))} phase-doc "
                  f"reference(s) in the roadmap, cross-component links included")
            # THE FLOOR FROM THE SAME FUNCTION THE GUARD USES, not `len(phases)`
            # recomputed here. The two disagree on an all-gated component — the
            # guard's floor is one, a phase-doc count is zero — and a dry run
            # printing a floor the live run does not enforce is the preview-is-
            # not-the-artifact drift `prompt_values` exists to prevent, one line
            # over.
            print(f"  Sized now  : {sum(own.roadmap_hours(component).values())} "
                  f"estimate(s) in {own.ROADMAP} "
                  f"(floor is {own.sizing_floor(component, phases)})")
            print(f"  Max turns  : {wf.MAX_TURNS} (estimate — nothing has measured this workflow)")
            print(f"  Grants     : "
                  f"{', '.join(wf.permitted_paths(rel, cands.relative_to(repo_root)))}")
            # THE SAME ASSEMBLY THE LIVE RUN USES, called rather than copied. A
            # dry run that builds its own values dict previews a prompt that is
            # not the one dispatched — the family has shipped that bug once
            # already (see `plan_sprint`'s `correction_note`), and an operator
            # checking the wrong artifact is worse than checking none.
            rendered = act.render(
                act.load_prompt(wf.PROMPTS / "plan_verify.md"),
                wf.prompt_values(rel, cands.relative_to(repo_root), repo_root,
                                 a.pr_number, context),
                opaque=frozenset({"TASK_CONTEXT"}))
            # BYTES, VIA `.encode()`, AND NOT `len(str)`. The prompt-budget gate
            # measures with `path.stat().st_size`, so an operator comparing this
            # line against a budget is comparing two different units — and this
            # prompt is 80 bytes wider than it is long, because the house style
            # is full of em-dashes. The budget table in
            # `test_prompt_budgets.py` shipped this exact confusion once and
            # says so in a comment; printing it again one file over would be the
            # same defect in the diagnostic that is supposed to catch it.
            print(f"  Prompt     : {len(rendered.encode())} bytes rendered, "
                  f"0 placeholders remaining")
            return 0

        # REQUIREMENT 11 — the run's bag is opened BEFORE the first side
        # effect, and a root that will not resolve stops the run here (r9). Why
        # this is not a helper each file remembers to call, and what the sweep
        # that enforces it can and cannot see: `journal_activities.py`'s module
        # docstring and `tests/unit/test_every_parent_opens_a_run_bag.py`. Said
        # once there rather than eleven times here.
        worktree_name = f"plan-verify-{int(time.time())}"
        journal.open_run_bag(run_id=journal.mint_run_id(), repo_root=repo_root,
                             workflow_key="plan-verify",
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
        ref = (f"origin/{act.pr_branch(a.pr_number, repo_root)}"
               if a.pr_number else "HEAD")
        worktree = act.worktree_add(repo_root, worktree_name, ref)
        url = wf.run_plan_verify(repo_root=repo_root, worktree=worktree, context=context,
                                 component=component, candidates_path=cands,
                                 pr_number=a.pr_number, verbose=a.verbose)
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        # These carry operator-facing recovery instructions from the layer that
        # knew what failed. Do not wrap or reformat them.
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1

    print(f"\n{BANNER}\n  {url}\n{BANNER}")
    print(f"\nSIZED — the estimates are in {rel}/{own.ROADMAP} and nowhere else.")
    print("`plan-sprint` does NOT read them today: its prompt states it never opens a")
    print("phase doc, and nothing in it reads a roadmap or an hour figure. Closing that")
    print("handoff is a change to plan-sprint and is not made from here.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

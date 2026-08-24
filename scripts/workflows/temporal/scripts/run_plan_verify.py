"""Kickoff entrypoint for plan-verify.

Lives in scripts/ because it is a launch concern, not a workflow concern. When
the Temporal path exists this is replaced by a client that starts the workflow
on a task queue; the workflow module itself does not change.
"""
from __future__ import annotations
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import RepoPathParser  # noqa: E402
from dispatch_identity import add_identity_arguments, resolve_identity  # noqa: E402
from modules.assistant import assistant_activities as act_shared  # noqa: E402
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
    component, cands = resolved["component"], resolved["candidates"]

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
    # IT ASKS THE BRANCH THE WORKTREE WILL ACTUALLY BE BUILT FROM, and it FETCHES
    # first: the ref has to be local before any query can read it, and this runs
    # before the worktree helper that would otherwise do the fetching.
    #
    # ON A `--pr` PASS THAT BRANCH IS THE ANSWER, NOT ONE HALF OF AN `or`. This
    # was written as "absent in both trees" and that is a DIFFERENT question from
    # the one the precondition asks, because the two trees are two objects: the
    # invocation checkout, and `origin/<the PR's branch>`, which is the ref
    # `act.worktree_add` cuts the worktree from and therefore the only tree the
    # run ever reads. (NAMED BY SYMBOL, NOT BY LINE: this citation was written as
    # "line 212", was already wrong when introduced, and drifted 251 -> 323 ->
    # 293 -> 329 while the text stayed put. A number restores the claim only
    # until the next edit, and a diagnostic claiming more than anything holds is
    # this PR's whole subject.) A
    # roadmap sitting in the operator's checkout — merged earlier, edited
    # locally, left by another branch — satisfied the check and the run then
    # dispatched against a worktree that did not have it, burning the model call
    # and stranding the worktree the check exists to prevent (issue #49). What
    # the local tree says is now REPORTED, so the refusal can tell the operator
    # which of the two states they are in, and it does not VOTE.
    #
    # THE COST OF ASKING EVERY TIME IS ONE `ls-tree`, and that was measured
    # rather than assumed: `pr_branch` was already called unconditionally below
    # to build `ref`, and `worktree_add` already runs this same `git fetch` — so
    # the branch is resolved ONCE here and reused, and the fetch is the
    # idempotent one that was happening anyway. A lookup that fails here would
    # have failed there too, forty lines later, AFTER the run bag was opened.
    # Failing before the first side effect is the whole point of preflight.
    #
    # `git_output`'s first parameter is named `worktree` and these two calls hand
    # it `repo_root`, which is not a worktree and deliberately so — none exists
    # yet, since the point of this check is to run before one is cut. The name is
    # that helper's, in a module this pass may not edit; it is flagged here so a
    # reader tracing the argument does not go looking for a bug.
    #
    # `ls-tree` RATHER THAN `cat-file -e`, DELIBERATELY. `cat-file -e` answers by
    # exit code, so "the ref is unreadable" and "the file is not there" arrive as
    # the same nonzero — and swallowing that into `plan_exists = False` would
    # report an UNKNOWN as a confident "there is no plan", which is the exact
    # class of bug this precondition was changed to fix. `ls-tree` exits 0 either
    # way and puts the answer in its OUTPUT, so a nonzero exit can only mean the
    # query genuinely failed, and `git_output` raises rather than guessing.
    #
    # THE REFUSAL IS INSIDE THE `try` AND THE HANDLER IS BELOW IT, which is a
    # placement rather than an accident. Both `pr_branch` and `git_output` raise,
    # and this block sits BETWEEN main's two try statements — so before this,
    # either raise left `main` as a Python traceback with no `✗` line and no exit
    # code of its own, while every other failure path in this file answers the
    # operator in one line. The handler cannot live around the lookup alone:
    # `test_the_PREFLIGHT_asks_the_PR_BRANCH_...` reads this file as TEXT, from
    # the assignment below to the refusal that follows it, and asserts no
    # `except` in that span — because an `except` there is how the lookup would
    # swallow its own failure into a confident "no plan". Putting the refusal
    # inside the `try` ends that span at the refusal, so the handler sits outside
    # it, and the property the test holds stays true: this handler STOPS the run
    # rather than continuing with a guess. Four behavioural tests hold the same
    # property by execution, which a source-grep cannot.
    #
    # (This paragraph names neither anchor VERBATIM, deliberately. That test
    # slices from the FIRST occurrence of its anchor in the file, and a comment
    # quoting it exactly moves the slice onto prose — its own docstring records
    # that happening once, and writing this note reproduced it a second time.)
    branch = None
    plan_exists = (component / own.ROADMAP).is_file()
    try:
        where = ""
        # THE DEFAULT REMEDY IS "WRITE IT", which is true of every path that
        # reaches the refusal without a `--pr` answer: no tree this run can see
        # carries a plan, so writing one is the only move.
        remedy = ("Run plan_feature.sh against this component first — writing "
                  "the plan is its job and this workflow holds no grant over a "
                  "phase doc.")
        if a.pr_number:
            rel = (component / own.ROADMAP).relative_to(repo_root).as_posix()
            branch = act.pr_branch(a.pr_number, repo_root)
            act.git_output(repo_root, ["git", "fetch", "-q", "origin", branch],
                           "the PR's branch could not be brought local.")
            # THE LOCAL ANSWER IS SPENT ON THE MESSAGE AND NOWHERE ELSE — AND ON
            # BOTH OF ITS SENTENCES. Which one is true is the operator's whole
            # diagnosis: "write the plan" and "push the plan you already wrote"
            # are different remedies, so the ACTIONABLE sentence branches with
            # the diagnostic one. It did not, for one commit: the diagnostic said
            # "it IS in this checkout" while a fixed tail underneath it told the
            # operator to run the workflow that had already succeeded. A remedy
            # is the only part of a refusal anyone ACTS on, so a correct
            # diagnosis over a wrong remedy is worse than no message at all.
            if plan_exists:
                where = (f" — it IS in this checkout, but not on PR #{a.pr_number}'s "
                         f"branch, which is the tree this run is cut from")
                remedy = (f"Commit it to that branch and push, then re-run — this "
                          f"run reads the branch and never this checkout, so a "
                          f"plan that is only here is a plan it cannot see.")
            else:
                where = f" — not here and not on PR #{a.pr_number}'s branch"
            plan_exists = bool(act.git_output(
                repo_root, ["git", "ls-tree", "-r", "--name-only", f"origin/{branch}", "--", rel],
                "the PR's tree could not be listed.").strip())
        if not plan_exists:
            print(f"\n✗ {component.relative_to(repo_root)} has no {own.ROADMAP}"
                  f"{where}: there is no plan to verify. {remedy}", file=sys.stderr)
            return 1
    # `FileNotFoundError` TOO, because `run_bounded` does not catch it: a host
    # with no `gh` on PATH reaches `pr_branch` and escapes as a traceback by a
    # second route. `ValueError` is deliberately NOT caught here — nothing in
    # this block raises one except `relative_to` on a component preflight has
    # already proved is inside the repo, so a `ValueError` means an invariant
    # broke and the traceback IS the right report for that.
    except (RuntimeError, FileNotFoundError) as exc:
        # THE HINT IS APPLIED HERE, NOT PASSED TO ONE CALLEE. It was `git_output`'s
        # `cannot_hint` on both queries and therefore unreachable on the
        # `pr_branch` failure — the one an operator with a bad `--pr` actually
        # hits. Stated at the boundary it is true of whichever call raised: this
        # precondition could not answer its question.
        print(f"\n✗ {exc} — this run cannot tell whether PR #{a.pr_number} carries "
              f"a plan, and 'I cannot see it' must not be delivered as 'it is "
              f"not there'.", file=sys.stderr)
        return 1

    try:
        component_rel = component.relative_to(repo_root)
        if a.dry_run:
            phases = own.phase_docs_of(component)
            print(f"{BANNER}\n  DRY RUN — nothing invoked, nothing posted\n{BANNER}")
            print(f"  Component  : {component_rel}")
            # THE TREE THE COUNTS CAME FROM, NAMED RATHER THAN LEFT TO BE
            # ASSUMED. No worktree exists on a dry run, so every figure below is
            # read off THIS checkout — while a `--pr` run cuts its worktree from
            # `origin/<the PR's branch>` and reads nothing else. Two trees, and
            # on the correction pass that a `--pr` dry run exists for, they
            # routinely differ. `prompt_values`' `tree` parameter documents the
            # same split one module over; this is the runner saying it out loud.
            print(f"  Counted in : this checkout ({repo_root}) — a dry run cuts no worktree")
            # AND WHERE THIS CHECKOUT DEMONSTRABLY IS NOT THAT TREE, SAY SO
            # BEFORE THE NUMBERS. The precondition above has just proved the
            # ROADMAP is on the PR's branch; where it is absent HERE, the three
            # figures that read it — `roadmap_phase_links`, `roadmap_hours` and
            # `sizing_floor` — come out 0 for a plan that is fully written, and a
            # preview that is wrong looks exactly like a preview that is right.
            # Printing the caveat ABOVE the counts is the placement: an operator
            # scanning top-down meets the reason before the zeros they would
            # otherwise believe.
            #
            # THREE OF THE FOUR, NOT ALL FOUR, AND THE TRIGGER IS THE ROADMAP AND
            # NOT THE PLAN. `phase_docs_of` reads the component DIRECTORY and
            # never the roadmap, so it keeps printing this checkout's own count
            # and the caveat names it as such instead of sweeping it in. The
            # first draft of this claim did sweep it in — it called the checkout
            # "a tree WITHOUT the plan" and said "the counts below will be 0"
            # over all of them — and a component whose phase docs are here while
            # its roadmap is on the branch, hand-laid-out with its roadmap
            # written later by `plan-feature` (this runner's own target
            # workflow), printed `Phase docs : 4 of its own` one line under a
            # warning saying that number would be 0. An operator meeting a
            # warning and then a number it said would not exist reads the warning
            # as inapplicable, and takes the local count for the branch's. A
            # diagnostic that over-claims is discounted whole on its first false
            # instance, so it must assert only what its own code guarantees —
            # and this paragraph is the specification a later edit reads, so it
            # must not restate a claim the string below no longer makes.
            #
            # WHAT THE CAVEAT DOES NOT CATCH, stated so its SILENCE is not
            # over-read: it keys on the roadmap being ABSENT here, not on this
            # checkout's copy AGREEING with the branch's. A stale local roadmap
            # at the same path prints no caveat and still counts a tree the run
            # will not read. That is why the `Counted in` line above is
            # UNCONDITIONAL — it is the honesty floor, true of every dry run,
            # and the caveat is only the loud case sitting on top of it.
            #
            # COUNTING FROM THE BRANCH INSTEAD is the larger fix — `git ls-tree`
            # / `git show` against `origin/<branch>` — and it is issue #134's,
            # for all four `--pr`-accepting runners at once, not this file's
            # alone.
            #
            # `branch` IS THE ONE THE PRECONDITION ALREADY RESOLVED. A second
            # `act.pr_branch` call here would be two round-trips for one fact
            # with nothing guaranteeing the answers agree — removing exactly that
            # duplicate was this file's previous change, and reinstating it in a
            # diagnostic would undo it. The local re-`stat` is not the same
            # trade: it is one syscall against no network, and reading it here
            # rather than threading it out of the precondition keeps this edit
            # outside the span a source-grep slices.
            if a.pr_number and not (component / own.ROADMAP).is_file():
                print(f"  ⚠ NOT HERE : this checkout does NOT carry {component_rel}/{own.ROADMAP}, so every "
                      f"figure below that is READ FROM THE ROADMAP — the phase-doc reference "
                      f"count, the estimates and the floor — is 0 because the roadmap is absent "
                      f"here, not because the plan is unwritten. The phase-doc count left of the "
                      f"· is this checkout's own files and may differ from the branch's. The run "
                      f"itself reads origin/{branch}, which is where the precondition found it.")
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
                  f"{', '.join(wf.permitted_paths(component_rel, cands.relative_to(repo_root)))}")
            # THE SAME ASSEMBLY THE LIVE RUN USES, called rather than copied. A
            # dry run that builds its own values dict previews a prompt that is
            # not the one dispatched — the family has shipped that bug once
            # already (see `plan_sprint`'s `correction_note`), and an operator
            # checking the wrong artifact is worse than checking none.
            rendered = act.render(
                act.load_prompt(wf.PROMPTS / "plan_verify.md"),
                wf.prompt_values(component_rel, cands.relative_to(repo_root), repo_root,
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
        # PHASE 9 r2 and r4 — the run's NAME arrives from outside this
        # process, and `writer` says whether this invocation IS the run or
        # is part of one. Why both, and where a name comes from when no
        # orchestrator supplies it: `dispatch_identity.py`. Said once there.
        identity = resolve_identity(argv)
        journal.open_run_bag(run_id=identity.run_id, writer=identity.writer,
                             repo_root=repo_root,
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
        # THE BRANCH THE PRECONDITION ALREADY RESOLVED, not a second `gh pr view`.
        # Two calls meant two round-trips for one fact, doubling the exposure to
        # a rate-limited or flaky `gh` on the path this file just added, and
        # nothing guaranteed the two answers agreed.
        # NOT `act.base_ref` ON THE `--pr` ARM, and that is the one deviation in
        # the fleet. `base_ref` would call `gh pr view` a second time for a fact
        # the precondition above already resolved into `branch`; the paragraph
        # above says why one round-trip beats two here. The NO-PR arm takes the
        # shared answer, because "wherever the operator's checkout is sitting"
        # was never a defensible base — see `base_ref`'s docstring for what that
        # cost on three of eight open PRs.
        ref = f"origin/{branch}" if a.pr_number else act.base_ref(None, repo_root)
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
    print(f"\nSIZED — the estimates are in {component_rel}/{own.ROADMAP} and nowhere else.")
    print("`plan-sprint` does NOT read them today: its prompt states it never opens a")
    print("phase doc, and nothing in it reads a roadmap or an hour figure. Closing that")
    print("handoff is a change to plan-sprint and is not made from here.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

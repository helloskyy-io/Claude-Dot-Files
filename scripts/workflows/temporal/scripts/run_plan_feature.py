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
from dispatch_identity import add_identity_arguments, resolve_identity  # noqa: E402
from modules.assistant import assistant_activities as act_shared  # noqa: E402
from modules.journal import journal_activities as journal  # noqa: E402
from modules.assistant.plan import plan_activities as act  # noqa: E402
from modules.assistant.plan.plan_feature import plan_feature_activities as own  # noqa: E402
from modules.assistant.plan.plan_feature import plan_feature_workflow as wf  # noqa: E402

BANNER = "=" * 64

# A default, not a derivation — the repo's own surface. A different repo passes
# its own. Stated here rather than in the workflow so the workflow stays
# repo-agnostic and the launch concern owns the convention.
DEFAULT_CANDIDATES = "tracked/candidates"


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
    # NOT a repo path, deliberately — operator context from wherever they wrote it,
    # the same contract `run_research_minor.py` uses. Without this the `--pr` path
    # could push to a branch and could not be TOLD why it was re-running.
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

    try:
        if a.dry_run:
            rel = component.relative_to(repo_root)
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
            # appears. Same line as `run_plan_verify.py`, which shipped it first.
            print(f"  Counted in : this checkout ({repo_root}) — a dry run cuts no worktree")
            print(f"  Component  : {rel}")
            print(f"  Phase docs : {len(own.phase_docs(component))} · "
                  f"roadmap.md {'present' if (component / 'roadmap.md').is_file() else 'ABSENT'}")
            print(f"  Max turns  : {wf.MAX_TURNS} (estimate — nothing has measured this workflow)")
            print(f"  Grants     : {', '.join(wf.permitted_paths(rel, cands.relative_to(repo_root)))}")
            print(f"  Context    : {len(context.encode())} bytes from --task-file"
                  if context else "  Context    : none (--task-file not given)")
            # THE SAME ASSEMBLY THE LIVE RUN USES, called rather than copied. A
            # dry run that builds its own values dict previews a prompt that is
            # not the one dispatched — the family has shipped that bug once
            # already (see `plan_sprint`'s `correction_note`), and an operator
            # checking the wrong artifact is worse than checking none.
            rendered = act.render(
                act.load_prompt(wf.PROMPTS / "plan_feature.md"),
                wf.prompt_values(rel, cands.relative_to(repo_root), repo_root,
                                 a.pr_number, context),
                opaque=frozenset({"TASK_CONTEXT"}))
            print(f"  Prompt     : {len(rendered.encode())} bytes rendered, 0 placeholders remaining")
            return 0

        # REQUIREMENT 11 — the run's bag is opened BEFORE the first side
        # effect, and a root that will not resolve stops the run here (r9). Why
        # this is not a helper each file remembers to call, and what the sweep
        # that enforces it can and cannot see: `journal_activities.py`'s module
        # docstring and `tests/unit/test_every_parent_opens_a_run_bag.py`. Said
        # once there rather than eleven times here.
        worktree_name = f"plan-feature-{int(time.time())}"
        # PHASE 9 r2 and r4 — the run's NAME arrives from outside this
        # process, and `writer` says whether this invocation IS the run or
        # is part of one. Why both, and where a name comes from when no
        # orchestrator supplies it: `dispatch_identity.py`. Said once there.
        identity = resolve_identity(argv)
        journal.open_run_bag(run_id=identity.run_id, writer=identity.writer,
                             repo_root=repo_root,
                             workflow_key="plan-feature",
                             worktree_name=worktree_name)

        # A `--pr` PASS MUST START FROM THE WORK IT IS CORRECTING. Hard-coding
        # "HEAD" put the run on `main`, so a correction pass opened a worktree
        # with none of the PR's files in it. Measured on plan-feature's first
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
        worktree = act.worktree_add(repo_root, worktree_name, ref)
        url = wf.run_plan_feature(repo_root=repo_root, worktree=worktree,
                                  component=component, candidates_path=cands,
                                  pr_number=a.pr_number, context=context,
                                  verbose=a.verbose)
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

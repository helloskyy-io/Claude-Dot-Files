"""Kickoff entrypoint for the research family."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import RepoPathParser, refuse  # noqa: E402
from dispatch_identity import add_identity_arguments, resolve_identity  # noqa: E402
from dispatch_context import RunContext  # noqa: E402
from modules.assistant import assistant_activities as act_shared  # noqa: E402
from modules.journal import journal_activities as journal  # noqa: E402
from modules.journal import harvest_activities as harvest  # noqa: E402
from modules.assistant.research.research import research_workflow as rw  # noqa: E402
from modules.assistant.research import research_activities as act  # noqa: E402
from modules.assistant.research.capture_cited_sources import capture_cited_sources  # noqa: E402

BANNER = "=" * 64

def main(argv=None) -> int:
    p = RepoPathParser(prog="research", description="Produce or revalidate a research pool.")
    # DECLARED AS A REPO PATH — the argument's own help says *"relative to the
    # repo root"*, and nothing enforced it: the pool was joined onto `repo_root`
    # unchecked, so `research ../../../../tmp/x` researched into `/tmp` under
    # `--dangerously-skip-permissions`.
    #
    # `must_exist=False` PRESERVES THIS FAMILY'S BEHAVIOUR EXACTLY, and the
    # exemption is from the existence pass only — the escape pass, which is the
    # one this closes, still runs. Nothing in the research family `mkdir`s its
    # pool, and its `--dry-run` reports `0 due papers` for an absent one rather
    # than failing, so requiring existence would make an escape fix into a
    # behaviour change for a family this PR is not otherwise touching.
    p.add_repo_path("research_dir", kind="dir", must_exist=False,
                    help="research folder, relative to the repo root")
    # NOT a repo path, deliberately: a task file is context the operator supplies
    # from wherever they wrote it, routinely /tmp, and is read rather than
    # written. `--phase` on the build runners is the same case. A RELATIVE one is
    # still anchored to the repo root — `act_shared.anchor_task_source` — which is
    # a base, not a boundary, and is why the read below sits inside the preflight
    # try rather than beside the workflow call.
    p.add_argument("--task-file", dest="task_file", help="context from a file")
    p.add_argument("--repo", dest="repo_target", help="target repo — a FILESYSTEM PATH, never a gh slug")
    p.add_argument("--pr", dest="pr_number", help="update an existing research PR")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="compute the gate and render; no model, no spend")

    add_identity_arguments(p)
    try:
        a, repo_root, resolved = p.parse_with_preflight(argv)
        # READ HERE, INSIDE THIS try, so a bad `--task-file` prints the same
        # one-line diagnostic as a bad `--repo` instead of a traceback. Both
        # are operator input and neither has created anything yet.
        context = act_shared.task_context(repo_root, a.task_file)
    except RuntimeError as exc:
        # Nothing has been created yet — that is the point of preflight.
        return refuse(exc)
    research_dir = resolved["research_dir"]
    target = str(research_dir.relative_to(repo_root))

    try:
        if a.dry_run:
            table, due = act.paper_currency(research_dir)
            print(f"{BANNER}\n  DRY RUN — nothing invoked, nothing posted\n{BANNER}")
            # THE TREE THE COUNTS CAME FROM, NAMED RATHER THAN LEFT TO BE
            # ASSUMED. No worktree exists on a dry run, so every figure below is
            # read off THIS checkout — while a `--pr` run cuts its worktree from
            # `origin/<the PR's branch>` and reads nothing else. Two trees, and
            # on the correction pass a `--pr` dry run exists for, they routinely
            # differ: the work being corrected is on the branch and need not be
            # in this checkout at all.
            #
            # THIS IS THE MINIMUM AND IT IS KNOWN TO BE — issue #134, operator
            # ruling 2026-08-24, on measured evidence. The stronger remedy reads
            # `origin/<branch>` so the preview is an actual preview, and earns
            # itself when real operator use appears.
            # THE SAME OBJECT THE LIVE RUN PRINTS, rendered by the same
            # method. A rehearsal that assembles its own copy previews something
            # that is not what runs, which is the bug this family has already
            # shipped once.
            print(RunContext.for_dry_run(repo_root=repo_root, workflow_key="research",
                                         pr_number=a.pr_number, target=target).render())
            print(f"  Counted in : this checkout ({repo_root}) — a dry run cuts no worktree")
            print(f"  Due papers: {len(due)}"
                  + ("" if due else " — nothing to revalidate this cycle"))
            for d in due:
                print(f"    - {d.name}")
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
                               workflow_key="research", pr_number=a.pr_number,
                               target=target)
        ctx.echo()
        # NO --refresh BRANCH. Revalidation is not a mode of this parent any
        # more: the write child computes the due set in code and routes each
        # due topic to `research-currency` itself, so one run covers new topics
        # and expired ones together instead of two runs over one pool.
        bag = journal.open_run_bag(run_id=ctx.run_id, writer=ctx.writer,
                                   repo_root=ctx.repo_root,
                                   workflow_key=ctx.workflow_key,
                                   worktree_name=ctx.worktree_name,
                                   journal_root=ctx.journal_root)

        result = None
        try:
            result = rw.run_research(research_dir=research_dir, repo_root=repo_root,
                                     worktree_name=ctx.worktree_name, context=context,
                                     pr_number=a.pr_number, verbose=a.verbose)
        finally:
            # PHASE 10 r7 — THE POST-EXIT HARVEST, in a `finally` because the window
            # OPENS AT CHILD EXIT, not at the workflow's return: a child that posted
            # and then had its parent raise still wrote to GitHub, and the runs an
            # operator reconstructs are the ones that failed. Only the parent holds
            # both the run's identity and the PR its child reported; on the failure
            # path the second is unknown and `None` harvests nothing, recorded as
            # such. A harvest that raises here chains the workflow's own error as
            # its `__context__`, which `preflight.refuse` prints beneath it. What
            # the sweep enforcing this can and cannot see:
            # `harvest_activities.py`'s docstring and
            # `tests/unit/test_every_parent_HARVESTS_its_github_surfaces.py`.
            harvest.harvest_github_surfaces(run_id=ctx.run_id, repo_root=repo_root,
                                            refs=(ctx.pr_number,
                                                  result.get("pr_url") if result is not None else None),
                                            journal_root=ctx.journal_root)

        # --- IN-WINDOW SOURCE CAPTURE ----------------------------------
        # HERE RATHER THAN INSIDE THE WORKFLOW, because this is where the run's
        # bag is open — threading a bag through the parent to reach the fetcher
        # would put the store on the workflow's import path for no gain.
        #
        # AFTER the paper settles and BEFORE the run exits. A correction pass can
        # add, repair or drop a citation, so the artifact worth capturing is the
        # paper that MERGES; capturing an intermediate draft would store bytes for
        # citations the paper no longer makes.
        #
        # ⚠ IT CANNOT FAIL THE RUN. The paper is the deliverable; the capture is
        # evidence about it. `capture_cited_sources` catches every per-citation
        # error itself, and this call is guarded too — a defect in the sweep must
        # not cost a completed research run either.
        try:
            report = capture_cited_sources(pool_dir=research_dir, bag=bag,
                                           stage="research")
            result.setdefault("notes", []).append(report.as_note())
        except Exception as exc:                  # noqa: BLE001 - see above
            result.setdefault("notes", []).append(
                f"source capture: NOT RUN — the sweep itself failed ({exc}). "
                f"The paper is unaffected.")
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        return refuse(exc)

    print()
    print(BANNER)
    v = result.get("verdict")
    print(f"  {result.get('pr_url') or 'no PR'} — {v.value if v else 'no papers due'}")
    print(BANNER)
    for n in result.get("notes", []):
        print(f"  {n}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

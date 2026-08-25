"""Kickoff entrypoint for triage-candidates."""
from __future__ import annotations
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import RepoPathParser  # noqa: E402
from dispatch_identity import add_identity_arguments, resolve_identity  # noqa: E402
from modules.journal import journal_activities as journal  # noqa: E402
from modules.assistant.plan import plan_activities as act  # noqa: E402
from modules.assistant.plan.triage_candidates import triage_candidates_workflow as wf  # noqa: E402

BANNER = "=" * 64

def main(argv=None) -> int:
    p = RepoPathParser(prog="triage-candidates",
        description="Rule every untriaged research candidate. Decides; does not place or design.")
    p.add_argument("--repo", dest="repo_target", help="target repo — a FILESYSTEM PATH, never a gh slug")
    # BOTH DECLARED AS REPO PATHS. This runner used to join them onto `repo_root`
    # unchecked and test only `.exists()` — which follows `..`, so an escaping
    # `--candidates` passed, was rendered into the prompt, and was ruled on by a
    # run holding `--dangerously-skip-permissions`. Demonstrated by execution.
    p.add_repo_path("--candidates", default="docs/standards/architecture/research/candidates.md")
    p.add_repo_path("--research", kind="dir", default="docs/standards/architecture/research")
    p.add_argument("--pr", dest="pr_number", help="update an existing triage-candidates PR")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="count and render; no model, no spend")

    add_identity_arguments(p)
    try:
        a, repo_root, resolved = p.parse_with_preflight(argv)
    except RuntimeError as exc:
        # Nothing has been created yet — that is the point of preflight.
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1

    cands, research = resolved["candidates"], resolved["research"]

    try:
        counts = act.candidate_counts(cands)
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
            # appears. Same line as `run_plan_verify.py`, which shipped it first.
            print(f"  Counted in : this checkout ({repo_root}) — a dry run cuts no worktree")
            print(f"  Candidates : {counts['total']} total · {counts['untriaged']} UNTRIAGED · {counts['triaged']} ruled")
            print(f"  Max turns  : {wf.MAX_TURNS} (estimate — nothing has measured this workflow)")
            # THE SAME ASSEMBLY THE LIVE RUN USES, called rather than copied — a
            # hand-built copy here is how the sibling `plan-sprint` shipped a dry
            # run previewing a prompt no model would receive.
            rendered = act.render(
                act.load_prompt(wf.PROMPTS / "triage_candidates.md"),
                wf.prompt_values(cands.relative_to(repo_root),
                                 research.relative_to(repo_root),
                                 repo_root, counts, None))
            print(f"  Prompt     : {len(rendered.encode())} bytes rendered, 0 placeholders remaining")
            return 0

        # REQUIREMENT 11 — the run's bag is opened BEFORE the first side
        # effect, and a root that will not resolve stops the run here (r9). Why
        # this is not a helper each file remembers to call, and what the sweep
        # that enforces it can and cannot see: `journal_activities.py`'s module
        # docstring and `tests/unit/test_every_parent_opens_a_run_bag.py`. Said
        # once there rather than eleven times here.
        worktree_name = f"triage-candidates-{int(time.time())}"
        # PHASE 9 r2 and r4 — the run's NAME arrives from outside this
        # process, and `writer` says whether this invocation IS the run or
        # is part of one. Why both, and where a name comes from when no
        # orchestrator supplies it: `dispatch_identity.py`. Said once there.
        identity = resolve_identity(argv)
        journal.open_run_bag(run_id=identity.run_id, writer=identity.writer,
                             repo_root=repo_root,
                             workflow_key="triage-candidates",
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

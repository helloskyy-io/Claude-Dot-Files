"""Kickoff entrypoint for research-refine — verify what a draft PR ships.

THE FAMILY RULING FOR ALL SIX OF THIS PHASE'S ADAPTERS IS IN
`run_build_draft.py`'s module docstring, and is not restated here.

Differs from `run_research_draft.py` because `--pr` is REQUIRED. `run_verify`
takes `pr_number: str`, not optional: it verifies work that already exists on a
PR, so there is nothing for it to do without one. Required at the parser rather
than checked later, so an unusable invocation costs a second and an argparse
message instead of a `TypeError` after a worktree exists.

Differs from `run_build_refine.py` only in taking the pool as a repo path — the
reason `run_research_draft.py` gives — and in the module it calls. The
`--correction-pass` flag is the same flag for the same reason: re-running verify
over a reviewer's findings is the most common reason to invoke this child alone.

⚠ THIS IS THE CHILD THE PHASE WAS WRITTEN FOR. `research_verify` — the name this
module carried until `7040c84` renamed it `research_refine` — needed three fix
rounds the week the ruling was made, each one re-run through a full parent chain,
while `plan-feature` was corrected standalone in one. That measurement is the
phase's argument, and this file is the part of it that pays back first.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import RepoPathParser, refuse  # noqa: E402
from dispatch_identity import add_identity_arguments, resolve_identity  # noqa: E402
from dispatch_context import RunContext  # noqa: E402

from modules.journal import journal_activities as journal  # noqa: E402
from modules.assistant import assistant_activities as act  # noqa: E402
from modules.assistant.research.research_refine.research_refine_workflow import (  # noqa: E402
    run_verify)

BANNER = "=" * 64

WORKFLOW_KEY = "research-refine"


def main(argv: list[str] | None = None) -> int:
    p = RepoPathParser(
        prog="research-refine",
        description="Verify every claim a research PR ships, correct it, and "
                    "re-verify. Nothing dispositions it — this is research's "
                    "second child, invoked alone.")
    p.add_repo_path("research_dir", kind="dir", must_exist=False,
                    help="research folder, relative to the repo root")
    p.add_argument("--repo", dest="repo_target",
                   help="target repo — a FILESYSTEM PATH, never a gh slug")
    p.add_argument("--pr", dest="pr_number", required=True,
                   help="the research PR to verify (REQUIRED — a verify pass has "
                        "nothing to open)")
    p.add_argument("--correction-pass", dest="correction_pass", action="store_true",
                   help="a reviewer already found something here — treat every "
                        "runway item as an INSTANCE of a class, not as the whole")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--dry-run", action="store_true",
                   help="state what this run derived; no model, no worktree, no spend")
    add_identity_arguments(p)

    try:
        a, repo_root, resolved = p.parse_with_preflight(argv)
    except RuntimeError as exc:
        # Nothing has been created yet — that is the point of preflight.
        return refuse(exc)

    research_dir = resolved["research_dir"]
    target = str(research_dir.relative_to(repo_root))

    if a.dry_run:
        print(f"{BANNER}\n  DRY RUN — nothing invoked, nothing posted\n{BANNER}")
        print(RunContext.for_dry_run(repo_root=repo_root, workflow_key=WORKFLOW_KEY,
                                     pr_number=a.pr_number, target=target).render())
        return 0

    try:
        ctx = RunContext.build(identity=resolve_identity(argv), repo_root=repo_root,
                               workflow_key=WORKFLOW_KEY, pr_number=a.pr_number,
                               target=target)
        ctx.echo()
        journal.open_run_bag(run_id=ctx.run_id, writer=ctx.writer,
                             repo_root=ctx.repo_root,
                             workflow_key=ctx.workflow_key,
                             worktree_name=ctx.worktree_name,
                             journal_root=ctx.journal_root)

        # `origin/<the PR's branch>`, because `--pr` is set and required. Never
        # the operator's checkout position.
        ref = act.base_ref(a.pr_number, repo_root)
        worktree = act.worktree_add(repo_root, ctx.worktree_name, ref)

        pr_url = run_verify(
            research_dir=research_dir, pr_number=a.pr_number, repo_root=repo_root,
            worktree=worktree, correction_pass=a.correction_pass, verbose=a.verbose,
        )
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        return refuse(exc)

    print(f"\n{BANNER}\n  RESEARCH-REFINE COMPLETE — PR #{a.pr_number} verified "
          f"and corrected\n{BANNER}", file=sys.stderr)
    print("  disposition it with:  ./review_pr.sh --pr <n> --type research\n"
          "  clean up with      :  /cleanup-merged-worktrees", file=sys.stderr)
    print(pr_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

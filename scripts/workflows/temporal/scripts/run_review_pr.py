"""Kickoff entrypoint for the review-pr workflow.

Lives in scripts/ because launching is a launch concern, not a workflow
concern. When the Temporal path exists this becomes a client that starts the
workflow on a task queue; the workflow module itself does not change.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import preflight, refuse  # noqa: E402
from dispatch_identity import add_identity_arguments, resolve_identity  # noqa: E402
from dispatch_context import RunContext  # noqa: E402

from modules.journal import journal_activities as journal  # noqa: E402
from modules.assistant.review_pr import review_pr_activities as act  # noqa: E402
from modules.assistant.review_pr import review_pr_helper as helper  # noqa: E402
from modules.assistant.review_pr import review_pr_workflow as wf  # noqa: E402
from modules.assistant.review_pr.review_pr_helper import ReviewInput, ReviewType  # noqa: E402

BANNER = "=" * 64


def parse_args(argv: list[str] | None = None) -> tuple[ReviewInput, bool]:
    parser = argparse.ArgumentParser(
        prog="review-pr",
        description="Disposition a PR: decide-only, ending in MERGE or HOLD.",
    )
    parser.add_argument("--pr", dest="pr_number", required=True, help="PR number (required)")
    parser.add_argument("--repo", dest="repo_target",
                        help="target repo — explicit identity, never derived from cwd")
    parser.add_argument("--type", dest="review_type", default=ReviewType.BUILD.value,
                        choices=[t.value for t in ReviewType],
                        help="what KIND of artifact is under review (default: build)")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="render the prompt and exit — no model call, no comment, no spend")
    add_identity_arguments(parser)
    args = parser.parse_args(argv)

    try:
        task = ReviewInput(
            pr_number=args.pr_number,
            repo_target=args.repo_target,
            verbose=args.verbose,
            review_type=ReviewType(args.review_type),
        )
    except ValueError as exc:
        parser.error(str(exc))
    return task, args.dry_run


def _dry_run(task: ReviewInput, repo_root: Path, ctx: RunContext) -> int:
    """Prove the plumbing without invoking the model.

    Everything the real path does up to the model call: fetch the PR, count
    prior passes, load both prompt sources, render, and check for leftovers.

    EVERY ARGUMENT THE REAL PATH PASSES, THIS PATH PASSES TOO. `run_review`'s own
    docstring records the dry-run and real paths diverging once before; adding
    `invocation_id` (then spelled `run_id`) to `render_prompt` recreated it, and
    because the divergence is a TypeError rather than a wrong result, the only
    zero-spend way to check the
    plumbing died with a traceback instead of a message. The nonce is real
    (`uuid4`) rather than a placeholder so the rendered byte count is what a live
    run would produce.
    """
    pr = act.fetch_pr(task.pr_number, repo_root)
    this_pass, prior_pass = helper.pass_numbers(
        act.count_prior_passes(task.pr_number, repo_root)
    )
    rendered = helper.render_prompt(
        wf.assemble_prompt(task.review_type),
        pr_number=task.pr_number,
        pr_branch=pr["headRefName"],
        this_pass=this_pass,
        prior_pass=prior_pass,
        headless_guard=act.load_shared_block("HEADLESS_EXECUTION_GUARD", wf.SHARED_PROMPTS),
        invocation_id=uuid.uuid4().hex,
    )
    print(f"{BANNER}\n  DRY RUN — nothing was invoked, nothing was posted\n{BANNER}")
    # THE SAME OBJECT THE LIVE RUN PRINTS, rendered by the same method — the
    # rehearsal receives the context rather than assembling a second copy of it.
    print(ctx.render())
    print(f"  Branch   : {pr['headRefName']} — {pr['state']}")
    print(f"  Title    : {pr['title']}")
    print(f"  Pass     : {this_pass} (prior: {prior_pass})")
    print(f"  Type     : {task.review_type.value}")
    print(f"  Model key: {helper.MODEL_KEY}")
    print(f"  Prompt   : {len(rendered.encode())} bytes rendered, 0 placeholders remaining")
    return 0


def main(argv: list[str] | None = None) -> int:
    task, dry = parse_args(argv)
    # --repo is a FILESYSTEM PATH (never a gh OWNER/NAME slug). gh is then run
    # with this as its cwd, which keeps repo identity explicit without parsing a
    # remote URL — see assistant_activities.gh.
    try:
        repo_root = preflight(task.repo_target)
    except RuntimeError as exc:
        # Nothing has been created yet — that is the point of preflight.
        return refuse(exc)
    try:
        if dry:
            return _dry_run(task, repo_root,
                            RunContext.for_dry_run(repo_root=repo_root,
                                                   workflow_key="review-pr",
                                                   pr_number=task.pr_number))

        # EVERYTHING THIS RUN DERIVED, BUILT ONCE AND SAID OUT LOUD BEFORE THE
        # BAG OPENS, THE WORKTREE IS CUT OR ANY `gh` CALL RUNS. Identity comes
        # from outside the process (Phase 9 r2/r4, `dispatch_identity.py`).
        #
        # ⚠ THIS RUN DOES CUT A WORKTREE, AND THIS ARGUMENT USED TO SAY IT DID
        # NOT. `worktree_name=None` sat here with the comment *"the ONE workflow
        # that cuts no worktree — it reviews a PR in place"*, while
        # `review_pr_workflow` cut `review-pr-<n>-<ts>` through the same
        # `worktree_add` whose docstring opens "ISOLATION IS AN INVARIANT, NOT A
        # PARAMETER". Nothing was lying: the two halves were written in two
        # places and only one of them was updated. The bag now records the stem
        # the tree is actually named from — a review PASS appends its pass
        # number, because a loop-back cuts one tree per pass.
        #
        # `target=None`: a review is pointed at a PR, which `pr_number` carries.
        ctx = RunContext.build(identity=resolve_identity(argv), repo_root=repo_root,
                               workflow_key="review-pr", pr_number=task.pr_number)
        ctx.echo()
        journal.open_run_bag(run_id=ctx.run_id, writer=ctx.writer,
                             repo_root=ctx.repo_root,
                             workflow_key=ctx.workflow_key,
                             worktree_name=ctx.worktree_name,
                             journal_root=ctx.journal_root)

        worktree = repo_root
        result = wf.run_review(task, worktree, worktree_name=ctx.worktree_name)
    # OSError covers the log-path freshness guard's FileExistsError, which is a
    # runtime state with an operator-facing message, not a programming error.
    # TypeError is deliberately NOT caught: a signature mismatch should traceback
    # rather than be reported as a workflow failure.
    except (RuntimeError, FileNotFoundError, ValueError, OSError) as exc:
        return refuse(exc)

    print()
    print(BANNER)
    print(f"  PR #{result.pr_number} — pass {result.this_pass} — {result.verdict.value}")
    print(BANNER)
    for note in result.notes:
        print(f"  {note}")
    print()
    print(f"VERDICT: {result.verdict.value}")

    # Exit 0 for MERGE and HOLD alike: the workflow completed and produced a
    # verdict either way. A HOLD is a result, not a failure — the caller reads
    # the verdict, which is why it is returned typed.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

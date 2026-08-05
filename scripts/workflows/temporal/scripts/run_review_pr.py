"""Kickoff entrypoint for the review-pr workflow.

Lives in scripts/ because launching is a launch concern, not a workflow
concern. When the Temporal path exists this becomes a client that starts the
workflow on a task queue; the workflow module itself does not change.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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


def _dry_run(task: ReviewInput) -> int:
    """Prove the plumbing without invoking the model.

    Everything the real path does up to the model call: fetch the PR, count
    prior passes, load both prompt sources, render, and check for leftovers.
    """
    pr = act.fetch_pr(task.pr_number, task.repo_target)
    this_pass, prior_pass = helper.pass_numbers(
        act.count_prior_passes(task.pr_number, task.repo_target)
    )
    rendered = helper.render_prompt(
        act.load_prompt(wf.PROMPT_PATH),
        pr_number=task.pr_number,
        pr_branch=pr["headRefName"],
        this_pass=this_pass,
        prior_pass=prior_pass,
        headless_guard=act.load_shared_block("HEADLESS_EXECUTION_GUARD", wf.SHARED_PROMPTS),
    )
    print(f"{BANNER}\n  DRY RUN — nothing was invoked, nothing was posted\n{BANNER}")
    print(f"  PR       : #{task.pr_number} ({pr['headRefName']}) — {pr['state']}")
    print(f"  Title    : {pr['title']}")
    print(f"  Pass     : {this_pass} (prior: {prior_pass})")
    print(f"  Type     : {task.review_type.value}")
    print(f"  Model key: {helper.MODEL_KEY}")
    print(f"  Prompt   : {len(rendered)} bytes rendered, 0 placeholders remaining")
    return 0


def main(argv: list[str] | None = None) -> int:
    task, dry = parse_args(argv)
    try:
        if dry:
            return _dry_run(task)

        # The worktree is the repo root today; a caller that isolates provides
        # its own. Kept explicit rather than derived — same doctrine as --repo.
        worktree = Path(task.repo_target) if task.repo_target else Path.cwd()
        result = wf.run_review(task, worktree)
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1

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

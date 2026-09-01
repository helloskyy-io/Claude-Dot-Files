#!/usr/bin/env python3
"""Land a reviewed PR set and drain the intake. THE OPERATOR ENTRY POINT.

The job itself is `modules/assistant/merge_pr.py`, an ACTIVITY — deterministic,
idempotent, no model, no dispatch cost. This file is the operator's way in; a
parent calls the same activity directly, so there is ONE implementation with two
callers rather than two implementations.

Same shape as `harvest-intake.py`, and deliberately NOT under
`scripts/workflows/temporal/scripts/run_*.py`: that prefix is the entrypoint
namespace those guards enumerate, and this is not a workflow.

    python3 scripts/helpers/merge-pr.py 162 --stores ../skyynet-master-planning
    python3 scripts/helpers/merge-pr.py 162 4 --record-repo ../skyynet-master-planning

RUNNING THIS IS THE APPROVAL. There is no `--yes`, because naming a PR and
invoking this IS the human act that authorises it — the same contract every
auto-merge system in the industry uses, where the bot decides WHEN and a human
has already decided WHETHER. `--dry-run` is for looking, not for consent.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workflows/temporal"))

from modules.assistant.merge import merge_pr  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="merge-pr",
        description="Merge a reviewed PR set in order, then drain the tracked-item "
                    "intake. The two are independent: neither blocks the other.")
    ap.add_argument("prs", nargs="+",
                    help="PR numbers IN MERGE ORDER — the code PR first, the "
                         "record PR (checkbox flips in the planning repo) second")
    ap.add_argument("--repo", type=Path, default=Path("."),
                    help="repo holding the first PR (default: cwd)")
    ap.add_argument("--record-repo", type=Path, default=None,
                    help="repo holding the trailing record PR, when the set spans "
                         "two repos")
    ap.add_argument("--stores", type=Path, default=None,
                    help="repo whose tracked/ receives the drained intakes; omit "
                         "to merge without draining")
    ap.add_argument("--issues-repo", type=Path, default=None,
                    help="repo whose tracked-intake issues are drained "
                         "(default: --repo)")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would happen; merge nothing, close nothing")
    a = ap.parse_args(argv)

    # A SET SPANNING TWO REPOS IS THE NORMAL CASE, not an edge one: a phase build
    # opens its code PR here and its checkbox flips in the planning repo, and the
    # two must land together or the record lies in one direction or the other.
    if a.record_repo and len(a.prs) < 2:
        print("\n✗ --record-repo given with a single PR. The record PR is the "
              "SECOND member of the set; pass both numbers in merge order.",
              file=sys.stderr)
        return 1

    tag = "DRY RUN — nothing merged, nothing closed" if a.dry_run else "MERGING"
    print(f"  {tag}")

    report = merge_pr.run_merge(
        [a.prs[0]], a.repo.resolve(), dry_run=a.dry_run,
        stores_root=a.stores.resolve() if a.stores else None,
        issues_repo=a.issues_repo.resolve() if a.issues_repo else None)

    # The trailing members land in their own repo, and ONLY if the first did —
    # `run_merge`'s refusal rule inside a repo, applied across the boundary.
    tail = a.prs[1:]
    if tail:
        if report.refused:
            for pr in tail:
                print(f"  ✗ #{pr}: not attempted — #{a.prs[0]} did not merge")
        else:
            tail_repo = (a.record_repo or a.repo).resolve()
            tail_report = merge_pr.run_merge(tail, tail_repo, dry_run=a.dry_run)
            report = merge_pr.MergeReport(
                merged=report.merged + tail_report.merged,
                refused=report.refused + tail_report.refused,
                drained=report.drained, drain_error=report.drain_error)

    for pr in report.merged:
        print(f"  ✓ #{pr} merged")
    for pr, why in report.refused:
        print(f"  ✗ #{pr} refused: {why}", file=sys.stderr)
    if report.drained:
        print(f"  ✓ drained {len(report.drained)} intake(s): "
              f"{', '.join('#' + str(n) for n in report.drained)}")
    if report.drain_error:
        print(f"  ! drain: {report.drain_error}", file=sys.stderr)

    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

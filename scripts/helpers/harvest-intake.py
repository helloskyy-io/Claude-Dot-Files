#!/usr/bin/env python3
"""Drain the tracked-item intake into the stores. THE NAMED CADENCE.

`Tracked Items Standard` §5.0 exempts a GitHub issue used purely as an intake
from §5's retirement of GitHub Issues — **conditionally**, and the first
condition is that *"a named harvest cadence exists and moves items into
`tracked/<store>/`, closing the intake issue as it goes."* **This script is that
cadence.** `/standup` runs it; a human may run it any time.

WITHOUT THIS RUNNING, THE EXEMPTION LAPSES AND THE INTAKE BECOMES A SECOND
STORE, which §8 names a violation rather than a grey area. That is why this is a
first-class entry point with its own name, and not a step buried inside another
workflow where its absence would be invisible.

IT WRITES FILES AND DOES NOT COMMIT. The caller commits — `/standup` does, and a
human running it by hand sees the changes in `git status` like any other edit.
Committing here would put a git write inside a step that is also called from a
read-only context, and the surprise is not worth the keystroke.

    python3 scripts/helpers/harvest-intake.py [--repo-root .] [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workflows/temporal"))

from modules.assistant.tracked import intake, tracked_items  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="harvest-intake",
        description="Move every open tracked-item intake issue into its store "
                    "and close it. The named harvest cadence of §5.0.")
    ap.add_argument("--repo-root", default=".", type=Path,
                    help="repo whose tracked/ directory receives the items")
    # TWO REPOS, BECAUSE THE STORES AND THE INTAKES STOPPED BEING IN ONE.
    # `review-pr` files against the repo whose PR it reviewed; the four stores
    # moved to the planning repo on 2026-08-31. With a single `--repo-root` the
    # harvest reads issues from the same place it writes files, so pointing it at
    # the tooling repo fails ("no tracked store") and pointing it at the planning
    # repo never sees the intakes at all — 15 sat undrained for four days, which
    # is exactly the "an intake with no harvest is a second store" state §5.0
    # names as a violation rather than a grey area.
    ap.add_argument("--issues-repo", type=Path, default=None,
                    help="repo whose tracked-intake issues are drained "
                         "(default: --repo-root, which is the one-repo case)")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would move without writing or closing")
    args = ap.parse_args(argv)

    root = (args.repo_root / tracked_items.TRACKED_ROOT).resolve()
    if not root.is_dir():
        # NAMED, NOT ASSUMED. A missing store is the shape §5.1 warns about: an
        # actor that reads "record it in X" and finds no X creates X. Say where
        # it should be rather than silently harvesting into a fresh directory.
        print(f"no tracked store at {root} — expected the four stores of "
              f"Tracked Items Standard §1. Nothing harvested.", file=sys.stderr)
        return 2

    issues_repo = args.issues_repo or args.repo_root
    moved, failed = intake.harvest(root, cwd=issues_repo, dry_run=args.dry_run)

    verb = "would move" if args.dry_run else "harvested"
    for number, path in moved:
        print(f"  {verb}: #{number} -> {path}")
    for number, why in failed:
        print(f"  LEFT OPEN #{number}: {why}", file=sys.stderr)

    if not moved and not failed:
        print("  intake is empty.")

    # A MALFORMED INTAKE IS A NON-ZERO EXIT, deliberately. It carries a finding
    # that has already left the run that produced it, so there is no second copy
    # anywhere and a quiet skip loses it. The issue stays OPEN and a human is
    # told; the well-formed items in the same pass still moved.
    if failed:
        print(f"\n{len(failed)} intake issue(s) could not be harvested and are "
              f"still open. Each carries a finding with no other copy — fix the "
              f"body and re-run.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

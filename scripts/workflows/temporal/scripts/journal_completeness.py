#!/usr/bin/env python3
"""Is every run's record WHOLE — the question `validate_bag.py` does not answer.

    journal_completeness.py                  # the configured journal root
    journal_completeness.py <journal-root>   # or one named root
    journal_completeness.py <bag-dir>        # or one bag
    journal_completeness.py --since 2026-09-15   # only bags at or after a date

Exit 1 when any bag in scope is incomplete, 0 otherwise — this one IS a verdict,
unlike `validate_bag.py`, whose exit code deliberately answers integrity alone.
The two are separate on purpose and the BagIt Profiles specification is why:
structural validation and profile conformance are different questions, checked
alongside each other rather than folded together.

The contract it checks is `modules/journal/profile.py`, which the journal owns.
A reader that needs the same answer imports `assess_completeness`; it does not re-derive it.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.journal.profile import assess_completeness, COMPLETE            # noqa: E402
from modules.journal.bag import BAG_INFO_FILE                   # noqa: E402
from modules.journal.journal_activities import load_journal_config  # noqa: E402
from modules.journal.root import resolve_journal_root           # noqa: E402


def _bags(target: Path) -> list[Path]:
    if (target / BAG_INFO_FILE).is_file():
        return [target]
    return sorted(d for d in target.iterdir() if d.is_dir() and (d / BAG_INFO_FILE).is_file())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="journal_completeness")
    ap.add_argument("target", nargs="?", type=Path,
                    help="a journal root or one bag; default is the configured root")
    ap.add_argument("--since", metavar="YYYY-MM-DD",
                    help="skip bags modified before this date — the reliability "
                         "floor, below which a gap is the mechanism's wiring "
                         "window rather than a defect")
    a = ap.parse_args(argv)

    target = a.target or resolve_journal_root(config=load_journal_config(), create=False)
    if not target.is_dir():
        print(f"not a directory: {target}", file=sys.stderr)
        return 2
    floor = (_dt.datetime.fromisoformat(a.since).timestamp() if a.since else None)

    bags = _bags(target)
    if not bags:
        print(f"no bags under {target} — this run verified nothing", file=sys.stderr)
        return 2

    incomplete = []
    considered = 0
    for bag in bags:
        if floor is not None and bag.stat().st_mtime < floor:
            continue
        considered += 1
        result = assess_completeness(bag)
        if result.verdict != COMPLETE:
            incomplete.append(result)

    for result in incomplete:
        print(f"{result.verdict.upper()}  {result.run_id}  {result.workflow or '?'}")
        for reason in result.reasons:
            print(f"    {reason}")
        for log in result.orphaned_logs:
            print(f"    orphaned log: {log}")

    scope = f" at or after {a.since}" if a.since else ""
    if considered == 0:
        # A sweep that examined nothing must not report green: "0/0 complete"
        # reads exactly like a pass and is the failure this whole check exists
        # to catch, one level up.
        print(f"no bags in scope{scope} — this run verified nothing "
              f"({len(bags)} present in total)", file=sys.stderr)
        return 2
    print(f"\n{considered - len(incomplete)}/{considered} bags complete{scope} "
          f"({len(bags)} present in total)")
    return 1 if incomplete else 0


if __name__ == "__main__":
    raise SystemExit(main())

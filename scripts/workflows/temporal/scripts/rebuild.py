#!/usr/bin/env python3
"""Rebuild the tracked stores from the journal — snapshot, check, restore.

    rebuild.py snapshot --stores <tracked-dir> [--journal <root>]
    rebuild.py check    --stores <tracked-dir> [--journal <root>] [--scratch <dir>]
    rebuild.py restore  --stores <tracked-dir> --store <name> [--apply] [--journal <root>]

THE OPERATOR-FACING HALF OF PMP PHASE 4. The test suite is where the rebuild is
GATED (`tests/unit/test_rebuild_*.py` against the committed fixture, and the
integration tier against this host's journal); this is where a human asks it a
question, takes the starting snapshot requirement 2 needs, or — requirement 8 —
regenerates a store on purpose. `restore` is a DRY RUN unless `--apply` is
given, and nothing here detects corruption or restores on its own.

`--stores` NAMES THE `tracked/` DIRECTORY AND IS REQUIRED. The planning repo is a
sibling on every machine that holds both, but "the sibling" is a convention the
tests derive and a CLI should not guess: a restore that resolved its
destination from a heuristic would be the path-join bug the phase doc warns
about, one layer up. Name it.

EXIT CODES, kept apart so an operator typo and a short journal never share a
number: 0 the test set matches (or the snapshot / restore succeeded) · 1 a
covered store MISMATCHES, or events could not be read · 2 usage or a refusal
(no journal, no snapshot, a disallowed store, a containment failure) · 3 no
mismatch but at least one covered store is GAPPED — the diff was reported and
not ruled, per requirement 7.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import refuse  # noqa: E402
from modules.assistant.tracked import rebuild as rb  # noqa: E402
from modules.journal.journal_activities import load_journal_config  # noqa: E402
from modules.journal.root import resolve_journal_root  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rebuild.py",
        description="Rebuild the tracked stores from the journal — snapshot, "
                    "check, restore (PMP Phase 4).")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--stores", required=True, type=Path,
                       help="the tracked/ directory holding the four stores")
        p.add_argument("--journal", type=Path, default=None,
                       help="journal root (default: the configured root, read-only)")

    snap = sub.add_parser("snapshot", help="record each covered store into the journal")
    common(snap)
    check = sub.add_parser("check", help="replay from the snapshot and diff the test set")
    common(check)
    check.add_argument("--scratch", type=Path, default=None,
                       help="replay into this directory instead of a temporary one")
    rest = sub.add_parser("restore", help="regenerate one store from the journal")
    common(rest)
    rest.add_argument("--store", required=True,
                      help=f"one of: {', '.join(sorted(rb.RESTORE_ALLOWLIST))}")
    rest.add_argument("--apply", action="store_true",
                      help="write the changes (default is a dry run)")
    return parser


def _journal_root(given: Path | None) -> Path:
    if given is not None:
        return given
    # `create=False`: a diagnostic must not bring the thing it is diagnosing
    # into existence — the same rule validate_bag.py applies.
    return resolve_journal_root(config=load_journal_config(), create=False)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(sys.argv[1:] if argv is None else argv)
    try:
        journal = _journal_root(args.journal)
        if args.command == "snapshot":
            path = rb.take_snapshot(journal, args.stores)
            print(f"snapshot written: {path}")
            return 0
        if args.command == "check":
            report = rb.rebuild(journal, args.stores, scratch=args.scratch)
            print(rb.render_report(report))
            if not report.ok:
                return 1
            return 3 if any(v.verdict == "gapped" for v in report.stores.values()) else 0
        report = rb.restore(journal, args.stores, args.store, apply=args.apply)
        print(rb.render_restore(report))
        return 0
    except RuntimeError as exc:
        return refuse(exc, exit_code=2)


if __name__ == "__main__":
    raise SystemExit(main())

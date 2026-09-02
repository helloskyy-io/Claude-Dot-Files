#!/usr/bin/env python3
"""Re-check every citation in a bag, from the stored bytes alone. No network.

    verify_citations.py <bag-dir>                     # one run
    verify_citations.py <journal-root>                # every bag directly under it
    verify_citations.py                               # the configured root, read-only
    verify_citations.py --repo <path> <bag-dir>       # also resolve `git:` citations

THE OPERATOR-FACING HALF OF REQUIREMENTS 2, 3 AND 4, and the sibling of
`validate_bag.py` beside it: that tool answers *do the bag's bytes match its
manifest*, this one answers *do the claims in it still stand against the sources
they were made from*. Two questions, two tools, because a bag can be perfectly
intact and hold a citation whose quote was never in its source.

EXIT CODE NAMES THE OUTCOME CLASS, WHICH IS WHY THERE ARE FOUR AND NOT A BOOLEAN:

    0  every citation verified
    2  usage, or a citation record that could not be parsed at all
    3  missing    — nothing stored under that digest; the check could not be MADE
    4  tampered   — stored bytes do not hash to their own name; the STORE failed
    5  span-miss  — bytes intact, quote absent; the CITATION was wrong when made

A run with several classes exits on the most severe, ordered by how much of the
report it invalidates: tampered, then missing, then span-missing.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import refuse  # noqa: E402
from modules.journal import verify  # noqa: E402
from modules.journal.journal_activities import load_journal_config  # noqa: E402
from modules.journal.root import resolve_journal_root  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    # WHETHER A TARGET WAS NAMED IS ASKED OF THE PARSER, NOT OF THE RAW ARGV.
    # This filtered the argument list itself and counted `--repo`'s own VALUE as
    # a target, so `verify_citations.py --repo <path>` printed a usage message
    # instead of verifying the configured root. `verify.split_args` is the one
    # parse both this file and `verify.main` now use.
    try:
        _, targets = verify.split_args(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return verify.EXIT_USAGE

    # `create=False` for the reason `validate_bag.py` gives: a diagnostic must
    # not bring the thing it is diagnosing into existence. An operator whose
    # root is missing needs to be told so, not handed a fresh empty directory.
    if not targets:
        try:
            root = resolve_journal_root(config=load_journal_config(), create=False)
        except RuntimeError as exc:
            return refuse(exc, exit_code=verify.EXIT_USAGE)
        args = args + [str(root)]
    return verify.main(args)


if __name__ == "__main__":
    raise SystemExit(main())

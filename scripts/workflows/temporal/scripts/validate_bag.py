#!/usr/bin/env python3
"""Validate one run bag, or every bag under a journal root.

    validate_bag.py <bag-dir>            # one run
    validate_bag.py <journal-root>       # every bag directly under it
    validate_bag.py                      # the configured root, resolved read-only

THE OPERATOR-FACING HALF OF REQUIREMENTS 5 AND 8. The test suite is where the
validator is *gated*; this is where a human asks it a question — which is the
recovery path when the journal itself is what has gone wrong, and r9's whole
argument is that such a path must not need a working journal to exist.

EXIT CODE ANSWERS INTEGRITY, NOT STATE. A redacted or incomplete bag whose bytes
match its manifest exits 0, because `redacted` and `incomplete` describe what
happened to the run while `ok` describes the bytes. Collapsing those is the
failure mode requirement 8 exists to prevent, and it would be reintroduced here
by an exit code that treated a flag as a failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import refuse  # noqa: E402
from modules.journal import validate  # noqa: E402
from modules.journal.journal_activities import load_journal_config  # noqa: E402
from modules.journal.root import resolve_journal_root  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        # `create=False`: a diagnostic must not bring the thing it is diagnosing
        # into existence. An operator running this against a machine whose root
        # is missing needs to be TOLD that, not handed a fresh empty directory.
        try:
            root = resolve_journal_root(config=load_journal_config(), create=False)
        except RuntimeError as exc:
            return refuse(exc, exit_code=2)
        args = [str(root)]
    return validate.main(args)


if __name__ == "__main__":
    raise SystemExit(main())

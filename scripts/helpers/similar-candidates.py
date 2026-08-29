#!/usr/bin/env python3
"""Which existing items should you read before filing this one?

WHY THIS IS A COMMAND AND NOT A PROMPT VALUE. `CANDIDATE_CEILING` and the other
counted blocks are rendered once, before the model is called, because their
answer does not depend on anything the run produces. This one does: the ranking
needs the TEXT of the finding being filed, which exists only mid-run. So it is a
tool the model invokes, not a fact it is handed.

WHAT IT DOES NOT DO, and the whole design rests on this: **it never says "this is
a duplicate."** It answers *which few of these hundred-odd items are worth reading
first*, and stops. Deciding two findings are the same finding is a judgement made
from the items' BODIES — titles state a consequence and therefore read alike
across genuinely different items. Measured upstream: a title-driven pass
nominated four items for merging and one of four survived reading them.

    python3 scripts/helpers/similar-candidates.py "the finding, in your words"
    python3 scripts/helpers/similar-candidates.py --store standards \\
        --target docs/standards/workflow-scripts.md --anchor '§ Composition' "..."

WHY IT EXISTS AT ALL. `recurrence.py` shipped 2026-08-26 with the ranking and the
rendered block, and the prompts shipped the same day telling every filer to
"search the store and read the two or three closest items in full" — with nothing
between them. A run then faced 122 files and a hand search. Both `plan-draft`
and `review-pr` flagged it independently on PR #144. The capability existed and
was unreachable; this is the wire.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workflows/temporal"))

from modules.assistant.tracked import recurrence, tracked_items  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="similar-candidates",
        description="Rank the existing tracked items closest to a finding you are "
                    "about to file. Ranks; never rules.")
    ap.add_argument("text", help="the finding in your own words — its subject, "
                                 "not its title")
    ap.add_argument("--store", default="candidates",
                    choices=sorted(tracked_items.STORES),
                    help="which store to search (default: candidates)")
    ap.add_argument("--repo-root", default=".", type=Path)
    ap.add_argument("--limit", type=int, default=5)
    # THE KEY FIELDS, PASSED WHEN THEY EXIST. `standards` is the one store with a
    # field pair that IDENTIFIES rather than narrows: two items naming the same
    # target and anchor are two proposals to change one place. Supplying them
    # promotes an exact match above every text hit and labels it as such.
    ap.add_argument("--target", help="standards store: the standard being amended")
    ap.add_argument("--anchor", help="standards store: the section, precisely")
    ap.add_argument("--component", help="candidates store: the owning component")
    args = ap.parse_args(argv)

    root = (args.repo_root / tracked_items.TRACKED_ROOT).resolve()
    if not root.is_dir():
        print(f"no tracked store at {root} — expected the four stores of Tracked "
              f"Items Standard §1.", file=sys.stderr)
        return 2

    key = {k: v for k, v in (("target", args.target), ("anchor", args.anchor),
                             ("component", args.component)) if v}
    print(recurrence.recurrence_block(
        root, tracked_items.STORES[args.store], args.text,
        key=key, limit=args.limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

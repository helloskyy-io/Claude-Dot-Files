#!/usr/bin/env python3
"""Measure one run's harvest window against what its GitHub surfaces hold NOW.

    reconcile_harvest.py <bag-dir> [--repo <checkout>]

PMP PHASE 10 r3(c) AND THE PER-RUN HALF OF r4. The harvest captured what each
surface held at `harvested_at`; this re-reads the surface and reports, per
surface and with the denominator:

    in record     — comments on the surface now that the bag holds
    late          — posted AFTER the harvest: the window's cost, counted
    missed        — posted BEFORE it and not in the bag: a HARVEST DEFECT
    deleted since — in the bag, gone from the surface
    edited since  — in the bag, changed on the surface (the bag holds the earlier text)

EXIT CODE ANSWERS THE DEFECT, NOT THE WINDOW. A run whose surfaces grew after
the harvest exits 0 with the late count printed — that is the window doing
exactly what the phase says it does, and it is the number that decides whether
interception ever gets built. A run with a `missed` comment exits 1: something
that was there to be read was not captured, which is the failure r4 exists to
make visible. Usage errors exit 2, kept apart from 1 for the reason
`validate_bag.py` gives — a typo and a broken harvest need opposite remedies.

READS THE INDEX, NOT THE EVENTS. `harvest/index.json` names every comment id
the harvest saw and the event it landed on; re-deriving that from `events.jsonl`
would be a second reader of one fact. The LATEST index in the bag is the one
compared, because the latest harvest saw everything the earlier ones did.

`--repo` IS A CHECKOUT, NEVER A SLUG, exactly as everywhere else in this fleet:
it is only the directory `gh` runs from. The surface is addressed by the
repository slug the index recorded, so any checkout — or none — will do; the
default is this repository's own root.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import refuse  # noqa: E402
# THE READER IS IMPORTED BY NAME, which is what makes this tool a member of
# `test_journal_operator_tools_separate_typo_from_finding.py`'s population —
# that sweep keys membership on a bag reader imported by name, never on a
# module, so `from modules.journal import harvest` would have left the fourth
# operator tool outside the check that holds its usage/finding split.
from modules.journal.harvest import (SurfaceRef, SurfaceUnreadable,  # noqa: E402
                                     fetch_surface, read_harvest_indexes,
                                     reconcile_surface, render_reconciliation)
from modules.journal.bag import BAGIT_FILE  # noqa: E402

_FLEET_ROOT = Path(__file__).resolve().parents[4]


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    repo_root = _FLEET_ROOT
    if "--repo" in args:
        at = args.index("--repo")
        if at + 1 >= len(args):
            print("usage: reconcile_harvest.py <bag-dir> [--repo <checkout>]",
                  file=sys.stderr)
            return 2
        repo_root = Path(args[at + 1]).expanduser()
        del args[at:at + 2]
    if len(args) != 1:
        print("usage: reconcile_harvest.py <bag-dir> [--repo <checkout>]",
              file=sys.stderr)
        return 2
    bag_path = Path(args[0]).expanduser()
    if not (bag_path / BAGIT_FILE).is_file():
        print(f"not a bag: {bag_path}", file=sys.stderr)
        return 2
    if not repo_root.is_dir():
        print(f"not a directory: {repo_root}", file=sys.stderr)
        return 2

    indexes = read_harvest_indexes(bag_path)
    if not indexes:
        print(f"no harvest index in {bag_path} — this run was never harvested, "
              f"or its harvest died before writing one", file=sys.stderr)
        return 2
    latest = indexes[-1]
    print(f"bag       : {bag_path}")
    print(f"harvests  : {len(indexes)} (comparing the latest, ran {latest['ran_at']})")
    print()

    shortfall = False
    for entry in latest["surfaces"]:
        if not entry.get("captured"):
            print(f"{entry['url']}\n  NOT READ at harvest time — recorded as a gap; "
                  f"nothing to reconcile\n")
            shortfall = True
            continue
        ref = SurfaceRef(repo=entry["repo"], kind=entry["kind"], number=entry["number"])
        try:
            now = fetch_surface(ref, cwd=repo_root)
        except SurfaceUnreadable as exc:
            return refuse(exc, exit_code=2)
        rec = reconcile_surface(entry, now)
        print(render_reconciliation(rec))
        print()
        shortfall = shortfall or not rec.ok
    return 1 if shortfall else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""The journal — one folder tree per edge, one BagIt bag per run, never edited.

THIS PACKAGE IS PHASE 1 OF THE PERSISTENT MEMORY PROTOCOL, and it is exactly the
scope that phase claims: WHERE a run's record goes and WHAT SHAPE it takes, plus
a checker that says whether a given folder is a well-formed one. **Nothing here
writes a run's content into a bag** — the emit rule is Phase 3's and belongs
there. If something in this package finds itself specifying what a run writes
rather than where it lands and how it is read, it is in the wrong phase.

  `root.py`                — resolving the root, and the properties it must have
  `bag.py`                 — the bag itself: layout, manifest, lifecycle, redaction
  `validate.py`            — re-hash the payload; report integrity and all three states
  `journal_activities.py`  — the activity a run invokes before anything else

DEPENDENCY-FREE ON THE WORKFLOW TREE, on purpose. Nothing here imports
`modules.assistant`, so the validator can be loaded by a measurement helper or a
future CPI sweep without dragging in the workflow modules — the same discipline
`convergence.py` and `run_log.py` already keep.

WHY `modules/journal/` AND NOT `scripts/` BESIDE `preflight.py`, since that is
the closest existing "every entrypoint needs it" module and a reader will ask.
`preflight.py` is a helper: it computes paths and validates arguments, and it
touches the filesystem only to look. This package does I/O that has to be
recorded and retried — it CREATES the directory a run's whole record lives in —
and the Temporal Standard §3 puts I/O in the activities layer, which lives under
`modules/`. Requirement 11's entire argument is that bag-open is an ACTIVITY and
not a library function, so putting it in `scripts/` would contradict the thing it
is built to be. It is a top-level sibling of `modules/assistant/` rather than a
child of it because it belongs to no edge: `assistant/` is one domain, and the
journal is fleet-wide. That placement is what the sweep's
`test_the_journal_package_imports_no_workflow_module` pins.

NO DATABASE, AND IT IS A DECISION WITH A REVISIT TRIGGER RATHER THAN AN OMISSION
(requirement 10). The `state_passing` research paper's format table has one empty
row — *queries over accumulated history* — and the reflex is to fill it with
SQLite (OpenClaw ships exactly that). A per-run folder tree with a checksum
manifest answers the questions we actually have, and because Phase 4 makes the
journal able to REBUILD any store, a database would be one more thing it
rebuilds: adding one later is install-and-import with no refactor cost, so
nothing here has to change to allow it.

  **Revisit trigger: a real query the tree cannot serve** — not a feeling that a
  record ought to live in a database. The first such query is already scheduled:
  Phase 6's CPI sweep is a cross-run query over accumulated history, which is
  precisely that empty row, and Phase 6 carries its measured wall-clock against
  journal size as a requirement so the trigger fires on evidence rather than as
  a mid-build surprise.

The full reasoning for every decision this package implements is in
`docs/development/persistent-memory-protocol/phase1_the_run_bag.md`, which is the
authority; the docstrings here carry the half a reader of the code needs.
"""

from __future__ import annotations

from .bag import (JOURNAL_SCHEMA_VERSION, Bag, BagError, open_bag,
                  read_tag_file, utc_now)
from .journal_activities import (load_journal_config, mint_run_id,
                                 open_run_bag)
from .root import JournalRootError, resolve_journal_root
from .validate import BagReport, render_report, validate_bag

__all__ = [
    "JOURNAL_SCHEMA_VERSION", "Bag", "BagError", "BagReport",
    "JournalRootError", "load_journal_config", "mint_run_id", "open_bag",
    "open_run_bag", "read_tag_file", "render_report", "resolve_journal_root",
    "utc_now", "validate_bag",
]

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
  `config_digest.py`       — what configuration a run absorbed, over the
                             installer's own symlink set (Workflow
                             Decomposition Phase 5)

PHASE 2 ADDS THE CONTENT STORE, and it is five more files under this same package
rather than a new child of `modules/`. That placement is a deliberate answer to a
question the roadmap flagged as this phase's trigger: whether `modules/<capability>/`
is an admitted shape beside `modules/<edge>/`. Keeping the store here means the
precedent stays a single case and the operator's ruling is not forced by a build.
It also matches what the code IS — the store lives inside a bag's payload, so it
is the journal's own storage rather than a capability sitting beside it.

  `content_store.py`       — bytes filed under their own checksum; the one read path
  `citations.py`           — what was claimed, against which bytes, under which guarantee
  `source_fetch.py`        — the fetch policy: https only, every hop re-checked, capped
  `content_activities.py`  — capture and resolve as the store's two I/O boundaries
  `verify.py`              — the read-path invariant run in bulk, with four exit codes

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

The full reasoning is in the phase docs under
`/opt/skyy-net/skyynet-master-planning/development/edge-assistant/persistent-memory-protocol/`,
which are the authority; the docstrings here carry the half a reader of the code
needs. TWO of them apply, and naming only the first left half this package's
decisions with no reachable authority:

  `phase1_the_run_bag.md`      — the bag, its root, its states, its validator
  `phase2_content_store.md`    — the store's shape (r7a), its path derivation
                                 (r7b), its fetch policy (r7c), its single read
                                 path (r7d), and the capture-provenance ruling
"""

from __future__ import annotations

from .bag import (JOURNAL_SCHEMA_VERSION, Bag, BagError, open_bag,
                  read_tag_file, utc_now)
from .citations import (CAPTURE_HARVEST, CAPTURE_READ_TIME, Citation,
                        CitationError, evidence_set_hash, new_citation,
                        read_citations, record_citation,
                        stage_evidence_hashes)
# ⚠ THE FUNCTION `config_digest` IS DELIBERATELY NOT RE-EXPORTED HERE, and it is
# the only public name in this package that is not. It shares its name with its
# own submodule, and `from .config_digest import config_digest` REBINDS the
# package attribute the import machinery just set to the module — so
# `import modules.journal as j; j.config_digest.ConfigDigestError` would raise
# `AttributeError` on a function object, which is how every other submodule in
# this package can be reached. Callers take it by its full path:
# `from modules.journal.config_digest import config_digest`.
from .config_digest import (LABEL_CONFIG_DIGEST, ConfigDigest,
                            ConfigDigestError, installer_targets,
                            parse_tag_value, unavailable_tag_value)
from .content_activities import (capture_code_citation, capture_fetched_source,
                                 capture_source, resolve_citation)
from .content_store import (ContentStoreError, digest_of_bytes, load_object,
                            object_relpath, store_bytes)
from .journal_activities import (load_journal_config, mint_run_id,
                                 open_run_bag)
from .root import JournalRootError, resolve_journal_root
from .source_fetch import FetchPolicy, FetchRefused, fetch_source
from .validate import BagReport, render_report, validate_bag
from .verify import CitationResult, VerifyReport, verify_bag, verify_citation

__all__ = [
    "CAPTURE_HARVEST", "CAPTURE_READ_TIME", "JOURNAL_SCHEMA_VERSION",
    "LABEL_CONFIG_DIGEST", "Bag", "BagError", "BagReport", "Citation",
    "CitationError", "CitationResult", "ConfigDigest", "ConfigDigestError",
    "ContentStoreError", "FetchPolicy", "FetchRefused", "JournalRootError",
    "VerifyReport", "capture_code_citation", "capture_fetched_source",
    "capture_source", "digest_of_bytes", "evidence_set_hash", "fetch_source",
    "installer_targets", "load_journal_config", "load_object", "mint_run_id",
    "new_citation", "object_relpath", "open_bag", "open_run_bag",
    "parse_tag_value", "read_citations", "read_tag_file", "record_citation",
    "render_report", "resolve_citation", "resolve_journal_root",
    "stage_evidence_hashes", "store_bytes", "unavailable_tag_value", "utc_now",
    "validate_bag", "verify_bag", "verify_citation",
]

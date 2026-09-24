"""Rebuildability is a test — replay the journal and diff it against the stores.

PMP PHASE 4. Phase 3 promises that everything a run writes to a `tracked/`
store also lands in the journal; this module is the machine that checks the
promise. Read the journal from a starting snapshot forward, write out what it
says the stores should hold, compare that to the stores as they are. A store
file the journal cannot produce is a write that never emitted — and now a test
says so instead of somebody finding out six weeks later.

PLACED BESIDE THE STORE WRITERS, NOT IN THE JOURNAL PACKAGE, for the reason the
package docstring gives about placement: everything under `modules/journal/`
writes INTO a bag, and this writes into a store. It also needs the store
contract — `tracked_items.STORES`, `parse_text`, the id shape — and the journal
package may not import a workflow module. The snapshot artifact, which is a
journal-root file Phase 5 retains and budgets, is the one piece that lives on
the other side (`modules/journal/snapshot.py`), and it takes the store contents
as data so the import stays one-way.

REQUIREMENT 5's ENUMERATION IS THE SINGLE STATEMENT, AND EVERYTHING ELSE HERE IS
DERIVED FROM IT. `STORE_COVERAGE` classifies every one of `tracked_items.STORES`
— a store the table does not classify fails
`tests/unit/test_rebuild_replays_the_test_set.py` — and from it come the test set, the snapshot's covered set, and the restore
allowlist. The phase doc's warning is exact: *"two lists that must agree will
eventually disagree, so requirement 5's enumeration is the single statement and
the guard is derived from it."* A restore that could reach `tracked/operations/`
would be an autonomous write into the one store reserved to the operator, so
the allowlist is derived from the same rows that say why that store cannot be
rebuilt.

THE OUT-OF-RUN RULING (requirement 5) IS PHASE 3's, NOT THIS BUILD's. Phase 4
§ *Which stores are in the test set* offers exactly two answers: Phase 3
specifies an ingest for out-of-run writes, or requirement 1 is scoped to
RUN-AUTHORED content and the exclusion is recorded. **Phase 3 took the second
on 2026-09-10 (§ *The write-path inventory*): hand edits are excluded from
REPLAY and included in the RECORD by their existing binding, the git commit,
so a second copy would be a second carrier of one fact.** This build conforms
to that ruling; it does not re-open it. Consequences, stated rather than
normalised away:

  * `tracked/operations/` — in the test set as the NEGATIVE CONTROL — is
    reported as an exclusion with its live item count, never diffed. If a
    replay ever produces it, the test is measuring nothing and the exclusion
    row is what says so.
  * A hand edit to a covered store shows up as a MISMATCH. Replay cannot tell
    an operator's correction from a missing emit — both are content the journal
    does not hold — so the report says "mismatch: a missing emit OR an
    out-of-run write" and names the file. Silently discarding the difference is
    the one answer the phase doc forbids.
  * A restore OVERWRITES a hand-EDITED item with the journal's last write —
    the edit is reverted — and leaves a hand-CREATED item in place, because
    that file is one the journal does not know and deleting it would be replay
    reverting the highest-value content in the stores. Both halves are said:
    the dry run lists every overwrite with "REVERTS" beside it before anything
    is written, and the operator who meant the edit takes a new snapshot. The
    first draft's prose said only the second half, which documented the
    opposite of the tool's behaviour for exactly the case the roadmap warns
    about (someone edits an item and watches the edit disappear).

THE NORMALISATION SET IS EMPTY, and that is a stated ruling, not an omission.
Requirement 1 permits a normalisation if it is stated and justified; the two
the phase doc anticipated — YAML key order and a trailing newline — do not
arise, because every tracked-store event carries the WHOLE file as the writer
wrote it (`tracked_items._write_item` emits `text` verbatim) and the store is
file-per-item. A rebuilt file is therefore the writer's bytes, and the live
file is either those bytes or something that changed after the write — which is
content, and *"a normalisation may discard formatting; it may never discard
content."* Adding one is a change to this docstring reviewers see.

REPLAY IS A PURE EVENT→TREE FUNCTION (requirement 4's containment contract).
No shell, no template, no exec, no network, no credentials: `_apply` takes
events and writes files, and the file's PATH is composed from the store name
(a key of `STORES`, resolved through `STORE_COVERAGE`) and the item id parsed
out of the event's own frontmatter (`_ITEM_ID_RE`, a closed shape with no
separator in it) — **never from the event's `destination.address`**, which is a
path some other machine wrote. `contained_target` then re-checks the composed
path AFTER full normalisation: absolute refused, `..` refused, a symlink at any
component refused, a symlinked root refused. Two layers, both tested, because
the doc's argument is that at Phase 7 the events may arrive from another
machine and a path-join bug becomes reachable by anything that can write to the
shared bucket.

THE SNAPSHOT BOUNDARY IS ONE LINE, AND EVERYTHING THAT READS THE JOURNAL
STANDS ON THE SAME SIDE OF IT. `taken_at` is stamped BEFORE the stores are read
(`take_snapshot`), so the materialisation reflects every write that landed
before it and possibly some that landed after. Replay then applies every write
whose COMPLETION is recorded at or after `taken_at` — the completion, not the
intent, because the completion is the event that asserts the write landed and
the intent only says it was about to: a write whose intent predates the stamp
but that landed after the store was read is otherwise in neither half, and the
rebuild reports a mismatch that is nothing but the snapshot's own race.
Re-applying a write the materialisation already holds is harmless (whole-file
events, same bytes). The first draft filtered on the intent and stamped the
snapshot after the read — both caught in review, both now tested.

THE STORE CONTRACT IS COMPARED, NOT MERELY RECORDED (requirement 1). A snapshot
taken under Tracked Items §7 `v1` and replayed by code that writes `v2` would
report every shape difference as an ordinary MISMATCH — the unattributable diff
the requirement exists to prevent — so a `store_contract` that is not this
build's `CONTRACT_VERSION` is refused, naming the upcast that has to exist
first. Same rule as `snapshot_version` and `decode_event`: refused, not guessed.

GAPS ARE AN INPUT TO THE TEST, NOT A FAILURE OF IT (requirement 7). A bag whose
`Journal-Incomplete` flag is set, or that carries a gap event, is counted
against the bags replayed and reported with what each gap covered — EVERY bag,
before or after the snapshot, because the count is the honesty figure and a
rotated-out gap is exactly what Phase 5 carries forward to keep it honest. A
gap recorded AT OR AFTER `taken_at` whose destination is a covered store makes
that store's verdict `gapped`: its diff is still REPORTED — the operator wants
to see it — but it is not RULED green or red, because the journal has said it
is short there. A gap BEFORE the snapshot does not rule the store: whatever it
lost is already reflected (or not) in a materialisation read straight off the
live store, and a verdict that stayed `gapped` for the lifetime of the journal
would refuse every restore for an incident the baseline has absorbed. It is
still counted and still named, with "before the snapshot" beside it. A gap
elsewhere (the transcript, a GitHub surface) counts at the bag level only.
Applied intents from a gapped bag are still applied: a completion is the
journal's proof that the write landed, and the gap is about the writes that did
not. Counting is dedupe-on-`run_id`, per § *Measurement*.

ORDER ACROSS RUNS IS BY COMPLETION TIME AT SECOND PRECISION, AND A TIE IS
REPORTED. Every tracked-store event replaces the whole file, so when two runs
write the same item the last one wins outright. `utc_now` is second-precision
by design (`bag.py`), and nothing in a version-1 event totally orders writes
across runs — `sequence` is per writer. Two runs completing writes to one item
within the same second therefore have no recorded order, and replay would pick
one lexically. Rather than pick silently, `_apply` reports the tie
(`ambiguous_order`): the diff still says whether the bytes match, and the
report says the order was not the journal's to know. A cross-run total order
is a Phase 3 event-schema addition, surfaced in the producing PR rather than
faked here.

PROVENANCE SURVIVES THE REBUILD (requirement 9). Every rebuilt file carries a
`FileProvenance` record in the report: `snapshot` origin with the snapshot id,
or `journal` origin with the producing event's `run_id`, `edge_id`, trust class
and `key_epoch`. It is carried in the REPORT rather than written into the file,
because a rebuilt file that differed from the writer's bytes would fail the very
diff this module exists to run. Phase 8's poller is the consumer that filters
on it.
"""

from __future__ import annotations

import os
import posixpath
import re
import stat
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from ...journal.bag import (BAG_INFO_FILE, MANIFEST_FILE,
                            FILE_MODE, DIR_MODE, bag_state, events_files, journal_bags,
                            read_tag_file, utc_now)
from ...journal.events import (EventError, EventKind,
                               JournalEvent, applied_intents, decode_event,
                               dedupe_on_identity)
from ...journal.snapshot import (Snapshot, SnapshotError, latest_snapshot,
                                 write_snapshot)
from . import tracked_items as ti

__all__ = ["Coverage", "STORE_COVERAGE", "TEST_SET", "RESTORE_ALLOWLIST",
           "RebuildError", "ContainmentError", "BagRead", "FileProvenance",
           "StoreVerdict", "RebuildReport", "RestoreReport",
           "NOT_THE_JOURNALS", "store_name_of", "contained_target", "read_bags", "read_store",
           "take_snapshot", "rebuild", "restore", "render_report",
           "render_restore", "SCRATCH_FORBIDDEN_SEGMENTS"]


class RebuildError(RuntimeError):
    """A rebuild could not run or could not be trusted. Every message names the remedy."""


class ContainmentError(RebuildError):
    """A replay target would land outside the replay root. Refused, never rewritten."""


# ---------------------------------------------------------------------------
# Requirement 5 — the enumeration. ONE statement; everything below derives.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Coverage:
    """One store's row in § *Stores not covered* — or its reason for being covered."""

    store: str
    in_test_set: bool
    rebuildable: bool
    reason: str


# Tracked Items §1.2 grants the machine-writable pools back to the fleet's
# write guards and names `operations/` as the operator's alone. This is the
# store-side statement of that rule, and `tests/unit/test_rebuild_replays_the_
# test_set.py` holds it against `STORES` — a fifth store with no row here is a
# red test, not a store nobody thought of.
STORE_COVERAGE: dict[str, Coverage] = {
    "candidates": Coverage(
        store="candidates", in_test_set=True, rebuildable=True,
        reason="POSITIVE CONTROL. The highest-volume machine-written store; "
               "every fleet write reaches it through `tracked_items._write_item`, "
               "which emits a paired intent/completion carrying the whole file."),
    "operations": Coverage(
        store="operations", in_test_set=True, rebuildable=False,
        reason="NEGATIVE CONTROL. Tracked Items §1.2 makes it human-in-the-loop "
               "only — no workflow, dispatch or agent writes it — so no "
               "run-authored event for it exists BY CONSTRUCTION, and out-of-run "
               "writes are RULED (Phase 3 § The write-path inventory, 2026-09-10): "
               "excluded from replay, recorded by their git commit — so there is "
               "no ingest to build and no rebuild target."),
    "issues": Coverage(
        store="issues", in_test_set=False, rebuildable=True,
        reason="OUT OF THE TEST SET: shares §3's core, §4.2's prune rule and the "
               "file-per-item shape with `candidates/` and adds no writer axis. "
               "Rebuildable through the same `_write_item` path; not snapshotted "
               "at Phase 4, so not restorable until a snapshot covers it."),
    "standards": Coverage(
        store="standards", in_test_set=False, rebuildable=True,
        reason="OUT OF THE TEST SET for the reason `issues/` is. `ratification` "
               "is the operator's alone (§4) and is an out-of-run write like "
               "every other hand edit — reported as a mismatch, never normalised."),
}

TEST_SET: tuple[str, ...] = tuple(
    name for name, cov in STORE_COVERAGE.items() if cov.in_test_set)

#: Stores the snapshot materialises and a replay applies: in the test set AND
#: rebuildable. Also the ONLY destinations a restore may write — derived here,
#: stated nowhere else.
COVERED: tuple[str, ...] = tuple(
    name for name, cov in STORE_COVERAGE.items()
    if cov.in_test_set and cov.rebuildable)
RESTORE_ALLOWLIST: frozenset[str] = frozenset(COVERED)

#: `Destination.store` for a tracked store is `tracked_<name>` (`_write_item`).
_DESTINATION_PREFIX = "tracked_"
#: `write_path` for a tracked store is `tracked:<name>:<verb>`; a `Journal-Gap`
#: tag line opens with the timestamp (`Bag.mark_incomplete`: `utc_now()`, a
#: space, the write path), then this write path. Both are captured: the stamp
#: places the gap against the snapshot boundary, the store attributes it.
_GAP_LABEL_RE = re.compile(r"\A(\S+)\s+tracked:([a-z]+):")
#: Any `Journal-Gap` line's stamp, whatever write path follows it.
_GAP_STAMP_RE = re.compile(r"\A(\S+)\s")

#: §2's id shape, as a WHOLE-STRING match. The one value that reaches a
#: filename, and it admits no separator, no dot and no line breaker — which is
#: what lets `contained_target` be a second check rather than the only one.
_ITEM_ID_RE = re.compile(r"\A([A-Z])-([0-9a-z]{8})\Z")

#: A scratch root under any of these is refused: CI uploads `testing/logs/` as
#: a downloadable artifact, and a rebuilt store is verbatim store content.
SCRATCH_FORBIDDEN_SEGMENTS: tuple[tuple[str, ...], ...] = (("testing", "logs"),)

#: What a live file the journal cannot reproduce IS — stated once, rendered
#: wherever the report names one (a MISSING line, a restore's `~` and `?`
#: lines). Replay cannot tell the two apart (requirement 5's ruling, module
#: docstring), and a carrier that said only one half would document the
#: opposite of the tool's behaviour for the other.
NOT_THE_JOURNALS = "an out-of-run write or a missing emit (requirement 5 ruling)"


def store_name_of(destination_store: str) -> str | None:
    """`tracked_candidates` → `candidates`; anything else → `None`.

    `None` and not a raise: a journal holds events for the transcript, the run
    log and GitHub surfaces, none of which are stores this module rebuilds, and
    a replay that refused them would refuse every real bag.
    """
    if not destination_store.startswith(_DESTINATION_PREFIX):
        return None
    return destination_store[len(_DESTINATION_PREFIX):]


# ---------------------------------------------------------------------------
# Requirement 4/8 — containment. Binds EVERY replay target, scratch or live.
# ---------------------------------------------------------------------------

def _real_root(root: Path, *, what: str) -> Path:
    """The replay root, proven to be a real, absolute, non-symlinked directory."""
    if not root.is_absolute():
        raise ContainmentError(
            f"{what} {root} is not absolute. A relative root resolves against "
            f"whatever directory the process was started from, which is the "
            f"defect `preflight.resolve_repo_root` exists to prevent.")
    normalised = Path(os.path.normpath(str(root)))
    try:
        info = os.lstat(normalised)
    except OSError as exc:
        raise ContainmentError(
            f"{what} {normalised} does not exist ({exc.strerror}). A replay "
            f"root is created by the caller, deliberately, so a missing one is "
            f"a wrong path rather than a first run.") from exc
    if stat.S_ISLNK(info.st_mode):
        raise ContainmentError(
            f"{what} {normalised} is a symlink. A symlinked root is refused "
            f"because the TARGET is what receives verbatim store content, and "
            f"every containment check below would be checking the wrong path.")
    if not stat.S_ISDIR(info.st_mode):
        raise ContainmentError(f"{what} {normalised} is not a directory.")
    real = Path(os.path.realpath(str(normalised)))
    if real != normalised:
        raise ContainmentError(
            f"{what} {normalised} resolves through a symlink to {real}. "
            f"Point at the real path.")
    return normalised


def contained_target(root: Path, store: str, filename: str) -> Path:
    """`root/<store>/<filename>`, proven to stay under `root` after full normalisation.

    THE STORE IS A KEY OF `STORE_COVERAGE` AND THE FILENAME IS `<id>.md` WITH
    THE ID PROVEN BY `_ITEM_ID_RE`; this function re-proves both rather than
    trusting its callers, because the phase doc's containment contract binds
    every target and a contract enforced by caller discipline is prose.

    LEXICAL FIRST, THEN THE FILESYSTEM. `posixpath.normpath` collapses `.` and
    `..`; the result must equal the composition exactly, so any escape by
    degrees is refused as one. Then every component from the root down is
    `lstat`ed: a symlink planted at `root/<store>` — or at the file itself —
    would send the write through to wherever it points, and `is_dir()` follows
    links. The final `realpath` comparison closes the case where a component
    above the root moved between checks.
    """
    root = _real_root(root, what="replay root")
    if store not in STORE_COVERAGE:
        raise ContainmentError(
            f"{store!r} is not a store this module enumerates "
            f"({', '.join(STORE_COVERAGE)}). The store directory is resolved "
            f"through the enumeration and never taken from an event.")
    match = _ITEM_ID_RE.match(filename[:-3]) if filename.endswith(".md") else None
    if match is None:
        raise ContainmentError(
            f"{filename!r} is not `<store-prefix>-<8 base36>.md`, the only "
            f"filename a tracked item may have (Tracked Items §2). A replay "
            f"target's name is derived from the item's own id and nothing "
            f"else; a name this shape cannot carry a separator.")
    if match.group(1) != ti.STORES[store].prefix[0]:
        raise ContainmentError(
            f"{filename!r} carries prefix {match.group(1)}- but the {store} "
            f"store's prefix is {ti.STORES[store].prefix}. An item filed under "
            f"another store's prefix is a corrupt event, not a file to write.")

    composed = f"{store}/{filename}"
    if posixpath.isabs(composed) or posixpath.normpath(composed) != composed:
        raise ContainmentError(
            f"{composed!r} does not normalise to itself — refused rather than "
            f"rewritten, because the caller asking for it has a different bug "
            f"than the one a rewrite would hide.")

    target = root / store / filename
    for component in (root / store, target):
        try:
            info = os.lstat(component)
        except FileNotFoundError:
            continue                      # not there yet: a create, not a follow
        if stat.S_ISLNK(info.st_mode):
            raise ContainmentError(
                f"{component} is a symlink. A replay writes through no link: "
                f"the target of a link is a path this contract never checked.")
    real = Path(os.path.realpath(str(target)))
    if real != target:
        raise ContainmentError(
            f"{target} resolves to {real}, outside the replay root {root}.")
    return target


def _refuse_scratch_under_uploaded_logs(scratch: Path) -> None:
    parts = Path(os.path.realpath(str(scratch))).parts
    for forbidden in SCRATCH_FORBIDDEN_SEGMENTS:
        width = len(forbidden)
        for i in range(len(parts) - width + 1):
            if tuple(parts[i:i + width]) == forbidden:
                raise RebuildError(
                    f"scratch root {scratch} sits under "
                    f"{'/'.join(forbidden)}/, which CI uploads as a downloadable "
                    f"artifact. A rebuilt store is verbatim store content; use "
                    f"a temporary directory.")


# ---------------------------------------------------------------------------
# Reading the journal — every bag once, deduped on run_id, gaps attributed.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BagRead:
    """One bag as replay sees it: its events, and what it says it lost."""

    run_id: str
    path: Path
    incomplete: bool
    gap_labels: tuple[str, ...]
    events: tuple[JournalEvent, ...]
    undecodable: tuple[str, ...]
    events_bytes: int

    @property
    def gap_events(self) -> tuple[JournalEvent, ...]:
        return tuple(e for e in self.events if e.kind is EventKind.GAP)

    @property
    def gapped(self) -> bool:
        return self.incomplete or bool(self.gap_events)

    def gapped_stores(self, *, since: str = "") -> set[str]:
        """The covered stores this bag's gaps are addressed to, from both records.

        BOTH THE EVENT AND THE FLAG, because either can land without the other
        (`Emitter.record_gap`): the event goes in the writer's `events.jsonl`,
        the flag and its `Journal-Gap` line in `bag-info.txt`. The label carries
        the write path (`tracked:<store>:<verb>`), the event carries the
        destination (`tracked_<store>`); a store named by either is gapped.

        `since` IS THE SNAPSHOT BOUNDARY: only a gap recorded at or after it
        rules a store (module docstring). Both records carry the stamp — the
        event's `recorded_at`, the label's first token — in `utc_now`'s one
        spelling, so the comparison is the same string comparison replay makes.
        """
        stores: set[str] = set()
        for event in self.gap_events:
            name = store_name_of(event.destination.store)
            if name and event.recorded_at >= since:
                stores.add(name)
        for label in self.gap_labels:
            match = _GAP_LABEL_RE.match(label)
            if match and match.group(1) >= since:
                stores.add(match.group(2))
        return stores

    def gapped_before(self, boundary: str) -> bool:
        """True when every gap this bag records predates `boundary`."""
        stamps = [e.recorded_at for e in self.gap_events]
        for label in self.gap_labels:
            match = _GAP_STAMP_RE.match(label)
            stamps.append(match.group(1) if match else label)
        return bool(stamps) and all(stamp < boundary for stamp in stamps)

    def describe_gaps(self) -> tuple[str, ...]:
        """What each gap covered — write path, class and byte count, never content."""
        lines = [f"event: {e.write_path} ({e.gap_class.value if e.gap_class else '?'}, "
                 f"{e.content_bytes} bytes lost, → {e.destination.store})"
                 for e in self.gap_events]
        lines += [f"flag: {label}" for label in self.gap_labels]
        return tuple(lines)


def _read_events_file(path: Path) -> tuple[list[JournalEvent], list[str]]:
    events: list[JournalEvent] = []
    undecodable: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                events.append(decode_event(line))
            except (EventError, ValueError, KeyError, TypeError) as exc:
                # REPORTED, NOT SKIPPED. A line the decoder refuses — a schema
                # version with no upcaster, a torn write — is a write this
                # replay could not apply, and a rebuild that stepped over it
                # silently would be short by exactly the amount nobody counted.
                undecodable.append(f"{path}:{number}: {type(exc).__name__}: {exc}")
    return events, undecodable


def read_bags(journal_root: Path) -> list[BagRead]:
    """Every bag directly under the root, once each, in run-id order.

    A BAG IS A DIRECTORY CARRYING `bagit.txt`; anything else under the root — the
    `edge-id` file, a snapshot, a staging directory `open_bag` is still renaming
    — is not a bag and is not read. The run id is the directory name, re-proven
    through `validated_run_id` before it is used as a key, so a directory that
    could not have been opened by `open_bag` cannot be counted as a run.

    EVERY WRITER'S `events.jsonl` IS READ. A parent writes `data/events.jsonl`;
    each member writes `data/<writer>/events.jsonl`; the harvest writes
    `data/harvest/events.jsonl`. `os.walk(followlinks=False)` under the payload
    finds them all and NEVER descends a symlinked directory — stated in the
    call rather than left to `Path.rglob`, whose symlink behaviour changed at
    3.13 and which this containment claim must not depend on. The payload
    contract forbids a link; this is what holds if one is planted anyway
    (Phase 7: a bag may have arrived from another machine).
    """
    bags: dict[str, BagRead] = {}
    # WHICH DIRECTORIES ARE BAGS, AND WHICH FILES ARE THEIR EVENTS, are
    # `bag.journal_bags` and `bag.events_files` — shared with the Self
    # Improvement reader, whose gapped figure is this one.
    for child in journal_bags(journal_root):
        run_id = child.name
        if run_id in bags:               # dedupe on run_id (§ Measurement)
            continue
        entries = read_tag_file(child / BAG_INFO_FILE) if (child / BAG_INFO_FILE).is_file() else []
        state = bag_state(manifest_exists=(child / MANIFEST_FILE).is_file(),
                          info_entries=entries)
        events: list[JournalEvent] = []
        undecodable: list[str] = []
        total = 0
        for events_file in events_files(child):
            total += events_file.stat().st_size
            found, refused = _read_events_file(events_file)
            events.extend(found)
            undecodable.extend(refused)
        bags[run_id] = BagRead(run_id=run_id, path=child,
                               incomplete=state.incomplete,
                               gap_labels=state.gaps,
                               events=tuple(events),
                               undecodable=tuple(undecodable),
                               events_bytes=total)
    return [bags[k] for k in sorted(bags)]


# ---------------------------------------------------------------------------
# Reading a store — the live side of the diff, and the snapshot's input.
# ---------------------------------------------------------------------------

def read_store(stores_root: Path, store: str) -> dict[str, str]:
    """`{filename: text}` for every item file in one store. Missing dir → empty."""
    directory = stores_root / store
    if not directory.is_dir():
        return {}
    files: dict[str, str] = {}
    for path in sorted(directory.glob("*.md")):
        if path.is_symlink() or not path.is_file():
            continue
        files[path.name] = path.read_text(encoding="utf-8")
    return files


def take_snapshot(journal_root: Path, stores_root: Path) -> Path:
    """Requirement 2: record each covered store into the journal, once.

    ONLY THE COVERED STORES ARE MATERIALISED; the rest are NAMED as excluded
    with their reason (Phase 5 r1). `bags_at_snapshot` is counted here so the
    "rotated out behind the snapshot" denominator exists before anything
    rotates.

    `taken_at` IS THE FIRST LINE, before a single store file or bag is read.
    A write that lands during the read is then applied again by replay (same
    bytes, harmless); stamped after the read it would be in neither half.
    """
    taken_at = utc_now()
    stores_root = _real_root(stores_root, what="stores root")
    materialisation = {name: read_store(stores_root, name) for name in COVERED}
    excluded = {name: cov.reason for name, cov in STORE_COVERAGE.items()
                if name not in COVERED}
    return write_snapshot(journal_root, taken_at=taken_at,
                          store_contract=ti.CONTRACT_VERSION,
                          store_materialisation=materialisation,
                          excluded_stores=excluded,
                          bags_at_snapshot=len(read_bags(journal_root)))


# ---------------------------------------------------------------------------
# Replay — the pure event→tree function, and the report it produces.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FileProvenance:
    """Where one rebuilt file came from — requirement 9's carried-forward field."""

    origin: str                          # "snapshot" | "journal"
    source_id: str                       # snapshot_id | event_id
    run_id: str = ""
    edge_id: str = ""
    provenance: str = ""                 # events.Provenance value
    key_epoch: str = ""
    recorded_at: str = ""


@dataclass
class StoreVerdict:
    """One store's answer. `verdict` is DERIVED from the evidence, never stored."""

    store: str
    covered: bool
    reason: str
    live_files: int = 0
    rebuilt_files: int = 0
    missing_from_rebuild: tuple[str, ...] = ()   # live has it, journal cannot produce it
    extra_in_rebuild: tuple[str, ...] = ()       # journal produces it, live lacks it
    mismatched: tuple[str, ...] = ()
    gapped_bags: tuple[str, ...] = ()
    provenance: dict[str, FileProvenance] = field(default_factory=dict)

    @property
    def differs(self) -> bool:
        return bool(self.missing_from_rebuild or self.extra_in_rebuild or self.mismatched)

    @property
    def verdict(self) -> str:
        if not self.covered:
            return "excluded"
        if self.gapped_bags:
            return "gapped"
        return "mismatch" if self.differs else "match"


@dataclass
class RebuildReport:
    """The whole answer. Two facts, not one: the emits that exist are complete
    (or not), AND this fraction of the record has holes and here is where."""

    store_contract: str
    snapshot_id: str
    snapshot_taken_at: str
    snapshot_edge_id: str
    bags_seen: int
    bags_gapped: int
    gapped: dict[str, tuple[str, ...]]           # run_id → what each gap covered
    gapped_before_snapshot: tuple[str, ...]      # counted above; rules no store
    ambiguous_order: tuple[str, ...]             # same file, same second, two runs
    events_read: int
    events_after_dedupe: int
    intents_after_snapshot: int                  # every paired intent past the boundary, any destination
    intents_applied: int                         # of those, the writes to a COVERED store — replay's own count
    intents_unapplied: int                       # intent with no completion
    store_write_failures: int
    undecodable: tuple[str, ...]
    applied_to_excluded: tuple[str, ...]         # a fleet write to a store it may not write
    outside_test_set: tuple[str, ...]            # a permitted write to a store the phase does not diff
    events_bytes: int
    wall_clock_s: float
    stores: dict[str, StoreVerdict]

    @property
    def ok(self) -> bool:
        """No covered test-set store is `mismatch`. A `gapped` store is neither
        green nor red — see the module docstring — and an excluded one is a
        reported fact. Undecodable events are a failure: a replay that could not
        read part of its input cannot vouch for the whole."""
        if self.undecodable or self.applied_to_excluded:
            return False
        return not any(v.verdict == "mismatch" for v in self.stores.values())

    @property
    def has_gaps(self) -> bool:
        return self.bags_gapped > 0


def _item_filename(event: JournalEvent, store: str) -> str:
    """The filename an event's content would be written under — from its `id:` only."""
    try:
        fields, _body = ti.parse_text(event.content, source=f"event {event.event_id}")
    except ValueError as exc:
        raise RebuildError(
            f"event {event.event_id} (run {event.run_id}, {event.write_path}) "
            f"carries content that is not a tracked item: {exc}") from exc
    item_id = fields.get("id", "")
    if not _ITEM_ID_RE.match(item_id):
        raise RebuildError(
            f"event {event.event_id} (run {event.run_id}) carries id {item_id!r}, "
            f"which is not Tracked Items §2's `<PREFIX>-<8 base36>` shape. The "
            f"filename is derived from the id, so an id that is not one cannot "
            f"become a path.")
    if not item_id.startswith(ti.STORES[store].prefix):
        raise RebuildError(
            f"event {event.event_id} addresses tracked_{store} but its item id "
            f"{item_id} carries another store's prefix.")
    return f"{item_id}.md"


@dataclass
class Applied:
    """What `_apply` produced: the tree it wrote, and every intent it did not apply, named."""

    rebuilt: dict[str, dict[str, str]] = field(default_factory=dict)
    provenance: dict[str, dict[str, FileProvenance]] = field(default_factory=dict)
    refused: list[str] = field(default_factory=list)          # the negative control
    outside_test_set: list[str] = field(default_factory=list) # rebuildable, not tested
    ambiguous: list[str] = field(default_factory=list)
    applied: int = 0                                          # writes to a covered store


def _apply(snapshot: Snapshot, intents: Iterable[JournalEvent],
           scratch: Path, *, landed_at: dict[str, str]) -> Applied:
    """Section (a), then every applied intent in order, into `scratch`.

    RETURNS WHAT IT WROTE rather than having the caller re-read the tree, so
    the diff compares the bytes replay produced and not bytes something else
    put there. The tree is still written — that is the artifact an operator
    inspects and the thing restore copies from.

    THREE ARMS FOR A TRACKED-STORE INTENT, AND THE ENUMERATION DECIDES WHICH,
    ROW BY ROW: a store `STORE_COVERAGE` says no run writes (`rebuildable=False`)
    is REFUSED — the negative control firing, and the rebuild fails; a store
    that is rebuildable but outside the test set (`issues`, `standards`) is
    neither applied nor refused — COUNTED and named (by filename when its
    content parses, by the parse failure when it does not; it never aborts
    the rebuild), because the fleet is permitted to write it and the phase
    simply does not diff it yet; a covered store is applied, and there a
    malformed event IS an abort (`_item_filename`), because a file replay
    cannot name is a diff it cannot run. The first draft keyed the refusal on `COVERED`, so the
    first harvested issue on a host accused the fleet of a write the
    enumeration permits — a predicate that disagreed with the rows it consumed.

    `landed_at` is each intent's COMPLETION stamp (the caller's sort key). Two
    intents from different runs landing on one file with the same stamp have no
    recorded order; the second is applied — the caller's order — and the tie is
    returned in `ambiguous`, never silently resolved (module docstring).
    """
    scratch = _real_root(scratch, what="replay root")
    out = Applied()
    last_writer: dict[tuple[str, str], tuple[str, str]] = {}

    for store in COVERED:
        (scratch / store).mkdir(mode=DIR_MODE, exist_ok=True)
        out.rebuilt[store] = {}
        out.provenance[store] = {}
        for filename, text in sorted(snapshot.store_materialisation.get(store, {}).items()):
            target = contained_target(scratch, store, filename)
            _write(target, text)
            out.rebuilt[store][filename] = text
            out.provenance[store][filename] = FileProvenance(
                origin="snapshot", source_id=snapshot.snapshot_id,
                edge_id=snapshot.edge_id, recorded_at=snapshot.taken_at)

    for event in intents:
        store = store_name_of(event.destination.store)
        if store is None:
            continue                                 # not a tracked store
        if store not in STORE_COVERAGE:
            out.refused.append(f"event {event.event_id} addresses unknown store "
                               f"{event.destination.store!r}")
            continue
        if not STORE_COVERAGE[store].rebuildable:
            # A FLEET WRITE INTO A STORE THE ENUMERATION SAYS NO RUN WRITES.
            # Not applied and not ignored: it is the negative control firing.
            out.refused.append(f"event {event.event_id} (run {event.run_id}) is a "
                               f"run-authored write to tracked/{store}/, which "
                               f"STORE_COVERAGE rules no run writes")
            continue
        if store not in COVERED:
            # REBUILDABLE BUT NOT IN THE TEST SET: a permitted write the phase
            # does not diff. Named so the figure exists; never a refusal — and
            # never an abort: content this arm cannot parse is named with the
            # reason rather than raised, because raising would take the
            # covered stores' verdict down with an event replay never applies.
            try:
                filename = _item_filename(event, store)
            except RebuildError as exc:
                filename = f"? (content is not a tracked item: {exc})"
            out.outside_test_set.append(
                f"tracked/{store}/{filename} (run {event.run_id})")
            continue
        filename = _item_filename(event, store)
        target = contained_target(scratch, store, filename)
        stamp = landed_at[event.event_id]
        previous = last_writer.get((store, filename))
        if previous and previous[0] == stamp and previous[1] != event.run_id:
            out.ambiguous.append(
                f"tracked/{store}/{filename}: runs {previous[1]} and "
                f"{event.run_id} both completed a write at {stamp}; the "
                f"journal records no order between them and {event.run_id} "
                f"was applied last")
        last_writer[(store, filename)] = (stamp, event.run_id)
        _write(target, event.content)
        out.applied += 1
        out.rebuilt[store][filename] = event.content
        out.provenance[store][filename] = FileProvenance(
            origin="journal", source_id=event.event_id, run_id=event.run_id,
            edge_id=event.edge_id, provenance=event.provenance.value,
            key_epoch=event.key_epoch, recorded_at=event.recorded_at)
    return out


def _write(target: Path, text: str) -> None:
    fd = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW,
                 FILE_MODE)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)


def _diff(live: dict[str, str], rebuilt: dict[str, str]) -> tuple[tuple[str, ...],
                                                                 tuple[str, ...],
                                                                 tuple[str, ...]]:
    """Byte-identical, under the empty normalisation set (module docstring)."""
    missing = tuple(sorted(set(live) - set(rebuilt)))
    extra = tuple(sorted(set(rebuilt) - set(live)))
    mismatched = tuple(sorted(name for name in set(live) & set(rebuilt)
                              if live[name] != rebuilt[name]))
    return missing, extra, mismatched


def _attribute_gaps(bags: list[BagRead], taken_at: str
                    ) -> tuple[dict[str, tuple[str, ...]], tuple[str, ...],
                               dict[str, list[str]]]:
    """Every gapped bag with what it lost; which of them predate the snapshot;
    and, per covered store, the bags whose gaps AT OR AFTER the snapshot are
    addressed to it — the only ones that rule a verdict (module docstring)."""
    gapped: dict[str, tuple[str, ...]] = {}
    before: list[str] = []
    by_store: dict[str, list[str]] = {name: [] for name in STORE_COVERAGE}
    for bag in bags:
        if not bag.gapped:
            continue
        gapped[bag.run_id] = bag.describe_gaps()
        if bag.gapped_before(taken_at):
            before.append(bag.run_id)
        for store in bag.gapped_stores(since=taken_at):
            if store in by_store:
                by_store[store].append(bag.run_id)
    return gapped, tuple(before), by_store


def rebuild(journal_root: Path, stores_root: Path, *,
            scratch: Path | None = None,
            snapshot: Snapshot | None = None) -> RebuildReport:
    """Requirement 1: replay from the snapshot forward and diff the test set.

    `snapshot=None` LOADS THE LATEST FROM THE ROOT AND REFUSES IF THERE IS NONE.
    A replay with no baseline reproduces a store that starts empty and never
    matches — the exact weakening the phase doc describes as the likely silent
    resolution — so the refusal names the command that takes one.

    `scratch=None` USES A TEMPORARY DIRECTORY AND REMOVES IT. The report
    carries every byte replay produced, so nothing needs the tree afterwards —
    and a rebuilt store is verbatim store content, which is not left lying in
    `/tmp` once per invocation (the first draft leaked one per call: 504 on the
    build host). A caller that wants the tree passes its own scratch, which is
    left in place; it may not be under `testing/logs/`.
    """
    started = time.monotonic()
    stores_root = _real_root(stores_root, what="stores root")
    if snapshot is None:
        try:
            snapshot = latest_snapshot(journal_root)
        except SnapshotError as exc:
            raise RebuildError(f"the latest snapshot under {journal_root} could "
                               f"not be read: {exc}") from exc
        if snapshot is None:
            raise RebuildError(
                f"no snapshot under {journal_root}, so there is no baseline to "
                f"replay from — the stores predate the journal and a replay "
                f"from nothing reproduces an empty store that never matches. "
                f"Take one: python3 -m modules.assistant.tracked.rebuild snapshot --stores {stores_root}")
    if snapshot.store_contract != ti.CONTRACT_VERSION:
        raise RebuildError(
            f"snapshot {snapshot.snapshot_id} was taken under Tracked Items §7 "
            f"contract {snapshot.store_contract!r} and this build writes "
            f"{ti.CONTRACT_VERSION!r}. No upcaster exists between them, and a "
            f"replay across the change would report every shape difference as "
            f"an ordinary mismatch — the unattributable diff requirement 1 "
            f"forbids. Write the upcast, or take a new snapshot under the "
            f"current contract: python3 -m modules.assistant.tracked.rebuild snapshot --stores {stores_root}")

    if scratch is not None:
        _refuse_scratch_under_uploaded_logs(scratch)
        return _rebuild_into(journal_root, stores_root, scratch, snapshot, started)
    with tempfile.TemporaryDirectory(prefix="rebuild-") as temporary:
        return _rebuild_into(journal_root, stores_root, Path(temporary),
                             snapshot, started)


def _rebuild_into(journal_root: Path, stores_root: Path, scratch: Path,
                  snapshot: Snapshot, started: float) -> RebuildReport:
    bags = read_bags(journal_root)
    all_events = [e for bag in bags for e in bag.events]
    deduped = dedupe_on_identity(all_events)
    # THE COMPLETION'S STAMP IS WHEN THE WRITE IS KNOWN TO HAVE LANDED, and it
    # is the boundary comparison and the order key (module docstring). An
    # intent with no completion is not in `applied_intents` and so never here.
    landed_at = {e.event_id: e.recorded_at for e in deduped
                 if e.kind is EventKind.COMPLETION}
    intents = [e for e in applied_intents(deduped)
               if landed_at[e.event_id] >= snapshot.taken_at]
    intents.sort(key=lambda e: (landed_at[e.event_id], e.run_id,
                                e.write_path, e.sequence))
    unapplied = sum(1 for e in deduped
                    if e.kind is EventKind.INTENT and e.event_id not in landed_at)
    failures = sum(1 for e in deduped if e.kind is EventKind.STORE_WRITE_FAILURE)

    applied = _apply(snapshot, intents, scratch, landed_at=landed_at)
    rebuilt, provenance = applied.rebuilt, applied.provenance
    gapped, before_snapshot, gapped_by_store = _attribute_gaps(
        bags, snapshot.taken_at)

    stores: dict[str, StoreVerdict] = {}
    for name in TEST_SET:
        cov = STORE_COVERAGE[name]
        live = read_store(stores_root, name)
        verdict = StoreVerdict(store=name, covered=name in COVERED,
                               reason=cov.reason, live_files=len(live))
        if name in COVERED:
            missing, extra, mismatched = _diff(live, rebuilt[name])
            verdict.rebuilt_files = len(rebuilt[name])
            verdict.missing_from_rebuild = missing
            verdict.extra_in_rebuild = extra
            verdict.mismatched = mismatched
            verdict.gapped_bags = tuple(gapped_by_store[name])
            verdict.provenance = provenance[name]
        stores[name] = verdict

    return RebuildReport(
        store_contract=snapshot.store_contract,
        snapshot_id=snapshot.snapshot_id,
        snapshot_taken_at=snapshot.taken_at,
        snapshot_edge_id=snapshot.edge_id,
        bags_seen=len(bags),
        bags_gapped=len(gapped),
        gapped=gapped,
        gapped_before_snapshot=before_snapshot,
        ambiguous_order=tuple(applied.ambiguous),
        events_read=len(all_events),
        events_after_dedupe=len(deduped),
        # TWO POPULATIONS, TWO NAMES. `intents` is every paired intent past the
        # boundary — a `gh_attempt` PR comment is one — and replay applies only
        # the tracked-store subset; the first draft labelled the former as the
        # latter and § Measurement's honesty figure over-counted from the first
        # fleet-code GitHub write after a snapshot.
        intents_after_snapshot=len(intents),
        intents_applied=applied.applied,
        intents_unapplied=unapplied,
        store_write_failures=failures,
        undecodable=tuple(u for bag in bags for u in bag.undecodable),
        applied_to_excluded=tuple(applied.refused),
        outside_test_set=tuple(applied.outside_test_set),
        events_bytes=sum(bag.events_bytes for bag in bags),
        wall_clock_s=time.monotonic() - started,
        stores=stores,
    )


def render_report(report: RebuildReport) -> str:
    """Every figure with its denominator — § *Measurement*'s rule, applied here."""
    lines = [
        f"rebuild: contract {report.store_contract} · snapshot "
        f"{report.snapshot_id} taken {report.snapshot_taken_at} on "
        f"{report.snapshot_edge_id}",
        f"  bags replayed: {report.bags_seen} · gapped: {report.bags_gapped}/"
        f"{report.bags_seen}",
        f"  events: {report.events_read} read, {report.events_after_dedupe} after "
        f"dedupe, {report.intents_after_snapshot} paired intents after the "
        f"snapshot, {report.intents_applied} of them applied to a covered store, "
        f"{report.intents_unapplied} intents with no completion, "
        f"{report.store_write_failures} store-write failures, "
        f"{len(report.undecodable)} undecodable",
        f"  intents to stores outside the test set: "
        f"{len(report.outside_test_set)}"
        + (" (" + ", ".join(sorted(set(report.outside_test_set))) + ")"
           if report.outside_test_set else ""),
        f"  wall-clock: {report.wall_clock_s:.3f}s over {report.events_bytes} "
        f"event bytes in {report.bags_seen} bags",
        f"  stores in test set: {len(report.stores)}/{len(STORE_COVERAGE)} "
        f"enumerated · covered: {len(COVERED)}/{len(STORE_COVERAGE)}",
    ]
    for run_id, what in sorted(report.gapped.items()):
        before = " (before the snapshot — counted, rules no store)" \
            if run_id in report.gapped_before_snapshot else ""
        lines.append(f"  gapped bag {run_id}:{before}")
        lines.extend(f"    {w}" for w in what)
    for line in report.ambiguous_order:
        lines.append(f"  ORDER NOT RECORDED {line}")
    for line in report.undecodable:
        lines.append(f"  UNDECODABLE {line}")
    for line in report.applied_to_excluded:
        lines.append(f"  REFUSED {line}")
    for name, v in report.stores.items():
        lines.append(f"  tracked/{name}/: {v.verdict.upper()} — live {v.live_files} "
                     f"files, rebuilt {v.rebuilt_files}")
        if not v.covered:
            lines.append(f"    excluded: {v.reason}")
            continue
        by_origin: dict[str, int] = {}
        for prov in v.provenance.values():
            by_origin[prov.origin] = by_origin.get(prov.origin, 0) + 1
        lines.append("    provenance: " + ", ".join(
            f"{k}={n}" for k, n in sorted(by_origin.items())) if by_origin
            else "    provenance: (no files)")
        if v.gapped_bags:
            lines.append(f"    gapped by {len(v.gapped_bags)} bag(s): "
                         f"{', '.join(v.gapped_bags)} — diff reported, not ruled")
        for f in v.missing_from_rebuild:
            lines.append(f"    MISSING from rebuild: {f} — {NOT_THE_JOURNALS}")
        for f in v.extra_in_rebuild:
            lines.append(f"    EXTRA in rebuild: {f} — deleted from the live "
                         f"store outside a run")
        for f in v.mismatched:
            lines.append(f"    MISMATCH: {f} — bytes differ from the last "
                         f"journalled write")
    lines.append("result: " + ("PASS" if report.ok else "FAIL")
                 + (f" (with {report.bags_gapped}/{report.bags_seen} gapped bags)"
                    if report.has_gaps else ""))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Requirement 8 — restore. Same replay; destination through the allowlist.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RestoreReport:
    store: str
    applied: bool
    created: tuple[str, ...]
    overwritten: tuple[str, ...]
    unchanged: tuple[str, ...]
    left_in_place: tuple[str, ...]        # live files the journal does not know
    provenance: dict[str, FileProvenance]
    rebuild: RebuildReport


def restore(journal_root: Path, stores_root: Path, store: str, *,
            apply: bool = False) -> RestoreReport:
    """Regenerate one store from the journal, into the working tree.

    NOT AUTOMATIC. A human decides a store is wrong and runs this; nothing
    detects corruption. `apply=False` — the default — computes and reports
    every change and writes nothing.

    THE DESTINATION IS RESOLVED THROUGH `RESTORE_ALLOWLIST` AND NEVER TAKEN
    FROM AN EVENT. `store` is checked against the allowlist before anything is
    read; `contained_target` composes the path from the store name and the
    item id. `tracked/operations/` cannot be named here, by derivation from the
    same enumeration that says why it cannot be rebuilt.

    A GAPPED STORE IS REFUSED. The journal has said it is short there; a
    restore would write a store the journal cannot vouch for and call it
    regenerated. There is no override at Phase 4 — an operator who wants the
    partial content has the scratch tree from `rebuild()`.

    FILES THE JOURNAL DOES NOT KNOW ARE LEFT IN PLACE, per the requirement 5
    ruling in the module docstring: they are out-of-run content or a missing
    emit, and in either case deleting them would be replay reverting the
    highest-value content in the store. FILES THE JOURNAL DOES KNOW ARE MADE
    THE JOURNAL'S BYTES: a live file whose content differs from the last
    journalled write is overwritten — and that difference is `NOT_THE_JOURNALS`,
    an out-of-run edit OR a missing emit, which restore cannot tell apart any
    more than the diff can. Applying REVERTS the live content either way. The
    dry run names each such file with that word, so an operator rules on it
    before choosing `apply`.
    """
    if store not in RESTORE_ALLOWLIST:
        raise RebuildError(
            f"tracked/{store}/ is not restorable: "
            f"{STORE_COVERAGE[store].reason if store in STORE_COVERAGE else 'not a store this module enumerates'} "
            f"Restorable: {', '.join(sorted(RESTORE_ALLOWLIST))}.")
    stores_root = _real_root(stores_root, what="stores root")
    with tempfile.TemporaryDirectory(prefix="restore-") as temporary:
        return _restore_from(journal_root, stores_root, store, Path(temporary),
                             apply=apply)


def _restore_from(journal_root: Path, stores_root: Path, store: str,
                  scratch: Path, *, apply: bool) -> RestoreReport:
    plan = rebuild(journal_root, stores_root, scratch=scratch)
    verdict = plan.stores[store]
    if verdict.verdict == "gapped":
        raise RebuildError(
            f"tracked/{store}/ is gapped by {len(verdict.gapped_bags)} bag(s) "
            f"({', '.join(verdict.gapped_bags)}); a restore would write a store "
            f"the journal cannot vouch for. Inspect the rebuild first.")
    if plan.undecodable or plan.applied_to_excluded:
        raise RebuildError(
            "the rebuild reported events it could not read or refused; a "
            "restore from a partially-read journal is refused. Run `check`.")

    live = read_store(stores_root, store)
    # The bytes come off the scratch tree replay just wrote, through the same
    # `contained_target` that placed them — so what restore copies is what
    # replay produced, re-proven on the way out as it was on the way in.
    rebuilt = {filename: contained_target(scratch, store, filename)
               .read_text(encoding="utf-8")
               for filename in verdict.provenance}

    created = tuple(sorted(f for f in rebuilt if f not in live))
    overwritten = tuple(sorted(f for f in rebuilt if f in live and live[f] != rebuilt[f]))
    unchanged = tuple(sorted(f for f in rebuilt if f in live and live[f] == rebuilt[f]))
    left = tuple(sorted(f for f in live if f not in rebuilt))

    if apply:
        (stores_root / store).mkdir(mode=DIR_MODE, exist_ok=True)
        for filename in created + overwritten:
            target = contained_target(stores_root, store, filename)
            _write(target, rebuilt[filename])

    return RestoreReport(store=store, applied=apply, created=created,
                         overwritten=overwritten, unchanged=unchanged,
                         left_in_place=left,
                         provenance=verdict.provenance,
                         rebuild=plan)


def render_restore(report: RestoreReport) -> str:
    mode = "APPLIED" if report.applied else "DRY RUN — nothing written"
    lines = [f"restore tracked/{report.store}/: {mode}",
             f"  create {len(report.created)} · overwrite {len(report.overwritten)} "
             f"· unchanged {len(report.unchanged)} · left in place "
             f"{len(report.left_in_place)} (not the journal's to remove)"]
    for f in report.created:
        p = report.provenance[f]
        lines.append(f"  + {f}  [{p.origin}:{p.source_id} run={p.run_id or '-'} "
                     f"edge={p.edge_id} class={p.provenance or 'snapshot'}]")
    for f in report.overwritten:
        p = report.provenance[f]
        lines.append(f"  ~ {f}  [{p.origin}:{p.source_id} run={p.run_id or '-'} "
                     f"edge={p.edge_id} class={p.provenance or 'snapshot'}] "
                     f"— live bytes differ from the journal's last write: "
                     f"{NOT_THE_JOURNALS}; applying REVERTS the live content")
    for f in report.left_in_place:
        lines.append(f"  ? {f}  left in place — {NOT_THE_JOURNALS}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """`python3 -m modules.assistant.tracked.rebuild snapshot --stores <tracked/>`

    The one operator verb: after a DELIBERATE out-of-run edit to a covered
    store — a hand ruling on a candidate — take a new snapshot so replay starts
    from the edited bytes. The rebuild test names this command in its failure
    message; a message naming a command that does not exist sends the operator
    to a `-m` invocation that exits 0 having done nothing.
    """
    import argparse
    from ...journal.journal_activities import load_journal_config
    from ...journal.root import resolve_journal_root
    ap = argparse.ArgumentParser(prog="rebuild")
    sub = ap.add_subparsers(dest="verb", required=True)
    snap = sub.add_parser("snapshot", help="record the covered stores into the journal, once")
    snap.add_argument("--stores", type=Path, required=True, help="the planning repo's tracked/ directory")
    a = ap.parse_args(argv)
    journal = resolve_journal_root(config=load_journal_config(), create=False)
    path = take_snapshot(journal, a.stores.resolve())
    print(f"snapshot → {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

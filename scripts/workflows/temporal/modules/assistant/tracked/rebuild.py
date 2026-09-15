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

THE OUT-OF-RUN RULING (requirement 5). Phase 4 § *Which stores are in the test
set* offers exactly two answers: Phase 3 specifies an ingest for out-of-run
writes, or requirement 1 is scoped to RUN-AUTHORED content and the exclusion is
recorded. **This build takes the second, because the first is a Phase 3
amendment in the planning repo and no dispatch writes one.** Consequences,
stated rather than normalised away:

  * `tracked/operations/` — in the test set as the NEGATIVE CONTROL — is
    reported as an exclusion with its live item count, never diffed. If a
    replay ever produces it, the test is measuring nothing and the exclusion
    row is what says so.
  * A hand edit to a covered store shows up as a MISMATCH. Replay cannot tell
    an operator's correction from a missing emit — both are content the journal
    does not hold — so the report says "mismatch: a missing emit OR an
    out-of-run write" and names the file. Silently discarding the difference is
    the one answer the phase doc forbids.
  * A restore leaves such files IN PLACE and says so. Reverting operator
    rulings — the highest-value content in the stores — is the failure the
    ruling exists to prevent, and a restore that deleted what the journal does
    not know would be exactly that.

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

GAPS ARE AN INPUT TO THE TEST, NOT A FAILURE OF IT (requirement 7). A bag whose
`Journal-Incomplete` flag is set, or that carries a gap event, is counted
against the bags replayed and reported with what each gap covered. A gap whose
destination is one of the covered stores makes that store's verdict `gapped`:
its diff is still REPORTED — the operator wants to see it — but it is not RULED
green or red, because the journal has said it is short there. A gap elsewhere
(the transcript, a GitHub surface) counts at the bag level only. Applied
intents from a gapped bag are still applied: a completion is the journal's
proof that the write landed, and the gap is about the writes that did not.
Counting is dedupe-on-`run_id`, per § *Measurement*.

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

from ...journal.bag import (BAGIT_FILE, BAG_INFO_FILE, MANIFEST_FILE,
                            PAYLOAD_DIR, FILE_MODE, DIR_MODE, BagError,
                            bag_state, read_tag_file, validated_run_id)
from ...journal.events import (EVENTS_FILE, EventError, EventKind,
                               JournalEvent, applied_intents, decode_event,
                               dedupe_on_identity)
from ...journal.snapshot import (Snapshot, SnapshotError, latest_snapshot,
                                 write_snapshot)
from . import tracked_items as ti

__all__ = ["Coverage", "STORE_COVERAGE", "TEST_SET", "RESTORE_ALLOWLIST",
           "RebuildError", "ContainmentError", "BagRead", "FileProvenance",
           "StoreVerdict", "RebuildReport", "RestoreReport",
           "store_name_of", "contained_target", "read_bags", "read_store",
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
               "writes have no ingest (Phase 3 § out-of-run writes is open). "
               "What would change that: Phase 3 specifying the git commit as the "
               "emit for the file binding."),
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
#: tag line opens with the timestamp, then this write path.
_GAP_LABEL_RE = re.compile(r"\A\S+\s+tracked:([a-z]+):")

#: §2's id shape, as a WHOLE-STRING match. The one value that reaches a
#: filename, and it admits no separator, no dot and no line breaker — which is
#: what lets `contained_target` be a second check rather than the only one.
_ITEM_ID_RE = re.compile(r"\A([A-Z])-([0-9a-z]{8})\Z")

#: A scratch root under any of these is refused: CI uploads `testing/logs/` as
#: a downloadable artifact, and a rebuilt store is verbatim store content.
SCRATCH_FORBIDDEN_SEGMENTS: tuple[tuple[str, ...], ...] = (("testing", "logs"),)


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

    def gapped_stores(self) -> set[str]:
        """The covered stores this bag's gaps are addressed to, from both records.

        BOTH THE EVENT AND THE FLAG, because either can land without the other
        (`Emitter.record_gap`): the event goes in the writer's `events.jsonl`,
        the flag and its `Journal-Gap` line in `bag-info.txt`. The label carries
        the write path (`tracked:<store>:<verb>`), the event carries the
        destination (`tracked_<store>`); a store named by either is gapped.
        """
        stores: set[str] = set()
        for event in self.gap_events:
            name = store_name_of(event.destination.store)
            if name:
                stores.add(name)
        for label in self.gap_labels:
            match = _GAP_LABEL_RE.match(label)
            if match:
                stores.add(match.group(1))
        return stores

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
    `data/harvest/events.jsonl`. `rglob` under the payload finds them all, and
    a symlink is not followed into (the payload contract forbids one).
    """
    bags: dict[str, BagRead] = {}
    for child in sorted(journal_root.iterdir()):
        if child.is_symlink() or not child.is_dir():
            continue
        if not (child / BAGIT_FILE).is_file():
            continue
        try:
            run_id = validated_run_id(child.name)
        except BagError:
            continue
        if run_id in bags:               # dedupe on run_id (§ Measurement)
            continue
        entries = read_tag_file(child / BAG_INFO_FILE) if (child / BAG_INFO_FILE).is_file() else []
        state = bag_state(manifest_exists=(child / MANIFEST_FILE).is_file(),
                          info_entries=entries)
        events: list[JournalEvent] = []
        undecodable: list[str] = []
        total = 0
        payload = child / PAYLOAD_DIR
        if payload.is_dir():
            for events_file in sorted(payload.rglob(EVENTS_FILE)):
                if events_file.is_symlink() or not events_file.is_file():
                    continue
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
    """
    stores_root = _real_root(stores_root, what="stores root")
    materialisation = {name: read_store(stores_root, name) for name in COVERED}
    excluded = {name: cov.reason for name, cov in STORE_COVERAGE.items()
                if name not in COVERED}
    return write_snapshot(journal_root, store_contract=ti.CONTRACT_VERSION,
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
    events_read: int
    events_after_dedupe: int
    intents_applied: int
    intents_unapplied: int                       # intent with no completion
    store_write_failures: int
    undecodable: tuple[str, ...]
    applied_to_excluded: tuple[str, ...]         # a fleet write to a store it may not write
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


def _apply(snapshot: Snapshot, intents: Iterable[JournalEvent],
           scratch: Path) -> tuple[dict[str, dict[str, str]],
                                   dict[str, dict[str, FileProvenance]],
                                   list[str]]:
    """Section (a), then every applied intent in order, into `scratch`.

    RETURNS WHAT IT WROTE rather than having the caller re-read the tree, so
    the diff compares the bytes replay produced and not bytes something else
    put there. The tree is still written — that is the artifact an operator
    inspects and the thing restore copies from.
    """
    scratch = _real_root(scratch, what="replay root")
    rebuilt: dict[str, dict[str, str]] = {}
    provenance: dict[str, dict[str, FileProvenance]] = {}
    refused: list[str] = []

    for store in COVERED:
        (scratch / store).mkdir(mode=DIR_MODE, exist_ok=True)
        rebuilt[store] = {}
        provenance[store] = {}
        for filename, text in sorted(snapshot.store_materialisation.get(store, {}).items()):
            target = contained_target(scratch, store, filename)
            _write(target, text)
            rebuilt[store][filename] = text
            provenance[store][filename] = FileProvenance(
                origin="snapshot", source_id=snapshot.snapshot_id,
                edge_id=snapshot.edge_id, recorded_at=snapshot.taken_at)

    for event in intents:
        store = store_name_of(event.destination.store)
        if store is None:
            continue                                 # not a tracked store
        if store not in STORE_COVERAGE:
            refused.append(f"event {event.event_id} addresses unknown store "
                           f"{event.destination.store!r}")
            continue
        if store not in COVERED:
            # A FLEET WRITE INTO A STORE THE ENUMERATION SAYS NO RUN WRITES.
            # Not applied and not ignored: it is the negative control firing.
            refused.append(f"event {event.event_id} (run {event.run_id}) is a "
                           f"run-authored write to tracked/{store}/, which "
                           f"STORE_COVERAGE rules no run writes")
            continue
        filename = _item_filename(event, store)
        target = contained_target(scratch, store, filename)
        _write(target, event.content)
        rebuilt[store][filename] = event.content
        provenance[store][filename] = FileProvenance(
            origin="journal", source_id=event.event_id, run_id=event.run_id,
            edge_id=event.edge_id, provenance=event.provenance.value,
            key_epoch=event.key_epoch, recorded_at=event.recorded_at)
    return rebuilt, provenance, refused


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


def rebuild(journal_root: Path, stores_root: Path, *,
            scratch: Path | None = None,
            snapshot: Snapshot | None = None) -> RebuildReport:
    """Requirement 1: replay from the snapshot forward and diff the test set.

    `snapshot=None` LOADS THE LATEST FROM THE ROOT AND REFUSES IF THERE IS NONE.
    A replay with no baseline reproduces a store that starts empty and never
    matches — the exact weakening the phase doc describes as the likely silent
    resolution — so the refusal names the command that takes one.

    `scratch=None` USES A FRESH TEMPORARY DIRECTORY. A caller may pass one to
    inspect the tree afterwards; it may not pass one under `testing/logs/`.
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
                f"Take one: rebuild.py snapshot --stores {stores_root}")

    if scratch is None:
        scratch = Path(tempfile.mkdtemp(prefix="rebuild-"))
    _refuse_scratch_under_uploaded_logs(scratch)

    bags = read_bags(journal_root)
    all_events = [e for bag in bags for e in bag.events]
    deduped = dedupe_on_identity(all_events)
    intents = [e for e in applied_intents(all_events)
               if e.recorded_at >= snapshot.taken_at]
    intents.sort(key=lambda e: (e.recorded_at, e.run_id, e.write_path, e.sequence))
    completed = {e.event_id for e in deduped if e.kind is EventKind.COMPLETION}
    unapplied = sum(1 for e in deduped
                    if e.kind is EventKind.INTENT and e.event_id not in completed)
    failures = sum(1 for e in deduped if e.kind is EventKind.STORE_WRITE_FAILURE)

    rebuilt, provenance, refused = _apply(snapshot, intents, scratch)

    gapped_by_store: dict[str, list[str]] = {name: [] for name in STORE_COVERAGE}
    gapped: dict[str, tuple[str, ...]] = {}
    for bag in bags:
        if bag.gapped:
            gapped[bag.run_id] = bag.describe_gaps()
            for store in bag.gapped_stores():
                if store in gapped_by_store:
                    gapped_by_store[store].append(bag.run_id)

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
        events_read=len(all_events),
        events_after_dedupe=len(deduped),
        intents_applied=len(intents),
        intents_unapplied=unapplied,
        store_write_failures=failures,
        undecodable=tuple(u for bag in bags for u in bag.undecodable),
        applied_to_excluded=tuple(refused),
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
        f"dedupe, {report.intents_applied} intents applied, "
        f"{report.intents_unapplied} intents with no completion, "
        f"{report.store_write_failures} store-write failures, "
        f"{len(report.undecodable)} undecodable",
        f"  wall-clock: {report.wall_clock_s:.3f}s over {report.events_bytes} "
        f"event bytes in {report.bags_seen} bags",
        f"  stores in test set: {len(report.stores)}/{len(STORE_COVERAGE)} "
        f"enumerated · covered: {len(COVERED)}/{len(STORE_COVERAGE)}",
    ]
    for run_id, what in sorted(report.gapped.items()):
        lines.append(f"  gapped bag {run_id}:")
        lines.extend(f"    {w}" for w in what)
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
            lines.append(f"    MISSING from rebuild: {f} — a missing emit OR an "
                         f"out-of-run write (requirement 5 ruling)")
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
    highest-value content in the store.
    """
    if store not in RESTORE_ALLOWLIST:
        raise RebuildError(
            f"tracked/{store}/ is not restorable: "
            f"{STORE_COVERAGE[store].reason if store in STORE_COVERAGE else 'not a store this module enumerates'} "
            f"Restorable: {', '.join(sorted(RESTORE_ALLOWLIST))}.")
    stores_root = _real_root(stores_root, what="stores root")
    scratch = Path(tempfile.mkdtemp(prefix="restore-"))
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
                     f"edge={p.edge_id} class={p.provenance or 'snapshot'}]")
    for f in report.left_in_place:
        lines.append(f"  ? {f}  left in place — out-of-run content or a missing emit")
    return "\n".join(lines)

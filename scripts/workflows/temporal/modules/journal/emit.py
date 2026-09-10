"""The emit — an ACTIVITY the orchestrator invokes, not a helper call sites remember.

REQUIREMENT 12, AND IT IS THE SAME ARGUMENT PHASE 1 r11 MAKES, APPLIED WHERE THE
FAILURE WOULD ACTUALLY HAPPEN. As a library, the emit rule is advice; this fleet
has already lost three observables and one cross-fleet gate to advice. Made
structural, the emit's ordering guarantee — the intent event *before* its paired
store write — is something the boundary enforces rather than something a call
site gets right.

⚠ AND THIS IS PRECISELY WHERE THE ACTIVITY BOUNDARY STOPS HELPING, so the limit
is stated rather than assumed. A wrapper reaches **fleet-code writes**: a call
site in `scripts/` that writes to a store. It does not reach **model-issued
writes** at all — when the child itself runs `gh pr comment`, there is no call
site to wrap, and the mechanism for those is Phase 10's post-exit harvest rather
than anything here. It does not reach a write path nobody wrapped in the first
place; **Phase 4's rebuild test is the guard for that class**, and the two are
complementary rather than redundant.

WHAT AN ACTIVITY *IS* HERE IS A BOUNDARY THE TEMPORAL PORT ALSO OWNS. What this
phase states is what it NEEDS — a recorded, retried step whose failure stops the
run at a named boundary — rather than the mechanism. `events.event_identity` is
the other half of that seam: an activity executes AT LEAST ONCE, so the journal
is a side effect the port has to hold for, and dedupe-on-identity is what
discharges Temporal Standard §7.1's idempotency rule here. **Layer placement,
invocation and fail-stop are buildable today; orchestrator-driven retry and
recorded execution are port-time**, exactly as `journal_activities.py` says of
bag-open.

---

## The rule: a gap may exist; a silent gap may not

Requirement 4, four cases, ordered because the first prevents most of the others.

**(a) The root cannot be resolved, at the start of the run → the run does not
start.** Phase 1 r9 owns this and it is already built (`root.resolve_journal_root`
plus `open_run_bag`'s `OSError` boundary). Nothing here re-implements it; the
cheapest failure is the one that already exists.

**(b) A write that has a paired store write → the intent goes FIRST, and a
failed intent means the store write does not happen.** `paired_write` below. This
is the ordering that makes requirement 1's invariant self-enforcing: order the
intent before the store write and a journal failure means NEITHER happened, so
the invariant holds because both sides are absent. Order it after and the store
has something the record does not, which is the state the component exists to
prevent. The run then stops at that boundary with a named terminal state —
`EmitFailed` — rather than continuing, because every subsequent step's record
would be conditioned on a write nobody can see. *(This is a write-ahead log,
which is what an append-only record that other stores are regenerated from is.
Naming it is worth a sentence: the ordering constraint is not an invention of
this plan.)*

**(c) A write with no pairable store write → a typed gap event, and the bag is
marked `incomplete`.** `unpairable_write` below. Write-ahead ordering has nothing
to offer here — the content already exists and the only question is whether it
lands — so the failure is RECORDED rather than prevented.

**⚠ The transcript is the one member of case (c) that is not merely a
completeness problem.** It is the fleet's only record of what commands ran, this
fleet runs with permissions bypassed, and a run can itself create the disk-full
condition that drops it. Losing it while the run proceeds to completion is
evidence loss wearing a routine defect's clothes. So a failed transcript write is
treated as case (b) — the run stops — via `stop_on_failure=True`, which is a
PARAMETER rather than a special case inside the function, because the caller is
what knows which member it is holding.

**(d) The bootstrap case — the journal is unwritable, so the gap event cannot go
in the journal either.** `unwritable_journal_report` below. It surfaces on two
channels that are not the journal, and the second is why the first is not enough:
the typed exit record plus a non-zero exit status carry it out of the process,
**and both are invocation state — read within seconds and then gone.** The
durable half is a pull-request comment: durable, addressable, and outside the
journal root by construction. **Not the standup tracker** — that surface is
`tracked/operations/`, which Tracked Items §1.2 makes human-in-the-loop only with
no autonomous write ever, and offering it here would put a binding-standard
violation on the one path that exists to report this component being broken.

**⚠ CASE (d)'s DURABLE REPORT IS THE ONE STATED EXCEPTION TO REQUIREMENT 1's
INVARIANT AND TO CASE (b)'s ORDERING.** The durable report is a STORE WRITE. Case
(b) says a store write does not happen unless its intent landed first — and in
case (d) the journal is unwritable by definition, so the intent can never land.
Read literally, this component's own ordering rule suppresses the only durable
signal that the component is broken. So: **the case-(d) failure report is the
single store write permitted with no preceding emit, because the emit is
precisely the thing that failed.** It is not a hole in the invariant; it is the
invariant's boundary condition, and a build that implements case (b) as an
unconditional wrapper without this exception ships the failure path silently
broken. `unwritable_journal_report` does NOT route through `paired_write`, and
that is why.

**⚠ And case (d) is uncountable from the journal, by construction.** Phase 6 r6
counts gaps by reading gap events; a run in case (d) produced no gap event, no
bag and nothing to count. That is a stated limit of that measurement rather than
a defect in it.

## Requirement 11 — each signal ships with its reader, in this change

The exit-record field has a named parent branch that reads it and the
working-record line has a named consumer that surfaces it. Adding a field to a
channel and leaving the reading to somebody later is how this fleet has already
lost three observables, and the one channel this component's failure path depends
on is the last place to repeat it. Both readers are `unwritable_journal_report`
and `unwritable_journal_in_text` at the bottom of this module, and
`test_the_unwritable_journal_signal_HAS_a_reader.py` is what holds them to the
producers rather than this paragraph.
"""

from __future__ import annotations

import errno
import os
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from ..vocabulary import TerminalState
from .bag import FILE_MODE, Bag, BagError
from .capture_filter import filter_capture
from .edge_id import NO_CREDENTIAL_EPOCH, resolve_edge_id
from .events import (EVENTS_FILE, Destination, EventKind, GapClass,
                     JournalEvent, Lineage, Provenance, encode_event,
                     event_identity, gap_event, redaction_placeholder_event)

__all__ = ["Emitter", "EmitFailed", "JournalUnwritable", "StoreWriteFailed",
           "UNWRITABLE_JOURNAL_MARKER", "unwritable_journal_report",
           "unwritable_journal_in_text", "gap_class_for", "register_emitter",
           "current_emitter", "emitting_into"]

T = TypeVar("T")

#: The literal a durable working-record line carries, and the literal its reader
#: greps for. ONE DECLARATION, because a producer and a consumer that each spell
#: the marker themselves are two declarations of one contract — the defect
#: `exit-protocol.md` §6 exists to forbid, and the one this fleet committed at
#: `as_prose_verdict`. Distinctive enough not to appear in ordinary prose, and
#: plain enough that a human scanning a PR thread sees it.
UNWRITABLE_JOURNAL_MARKER = "JOURNAL-UNWRITABLE"


class EmitFailed(RuntimeError):
    """Case (b): the intent did not land, so the store write did not happen.

    `RuntimeError` so it joins the `except RuntimeError` clause every entrypoint
    already carries. THE RUN STOPS HERE — it does not retry indefinitely and it
    does not carry on to the next step, because every subsequent step's record
    would be conditioned on a write nobody can see.

    ⚠ SEPARATE FROM `JournalUnwritable` AND THE SEPARATION IS THE REMEDY. This
    one means the journal refused one write at a known boundary and the store
    write was withheld — re-running the run is a correct response. That one
    means the root itself is gone, and re-running writes nothing.
    """

    terminal_state = TerminalState.EMIT_FAILED


class StoreWriteFailed(RuntimeError):
    """The intent landed and the store write did not — a POSITIVE record exists.

    Raised after a `store_write_failure` event has been appended, so a caller
    catching this knows the journal already says the write did not land. That
    asymmetry is what `events.applied_intents` reads: a `store_write_failure`
    does NOT satisfy an intent, so replay leaves it unapplied — and a reader can
    tell "the store write failed" from "the run died between the two events",
    which are both unapplied but only one of which is a defect in this component.
    """

    terminal_state = TerminalState.STORE_WRITE_FAILED


class JournalUnwritable(RuntimeError):
    """Case (d): the journal is gone, so even the gap event cannot be written.

    NOT STARTUP-ONLY. Case (a) catches the startup instance at
    `resolve_journal_root`; this covers any point at which the journal stops
    being writable mid-run.
    """

    terminal_state = TerminalState.JOURNAL_UNWRITABLE


def gap_class_for(exc: OSError) -> GapClass:
    """An `OSError` as one of four closed classes — never as its message.

    THE MESSAGE IS DELIBERATELY DISCARDED. A gap event reports that content was
    lost; a `why` carrying `exc.strerror` or `exc.filename` would put the failing
    path — and, for some filesystems, a fragment of what was being written — into
    the record that exists to say those bytes were dropped. Four classes, a byte
    count and a timestamp cost a few hundred bytes and cannot leak.

    THE OPERATOR STILL GETS THE MESSAGE — on stderr, and in the exception this
    module raises. What is bounded is what reaches the DURABLE record, which is
    the surface Phase 7 syncs to object storage and Phase 4 replays.
    """
    if exc.errno in (errno.ENOSPC, errno.EDQUOT):
        return GapClass.DISK_FULL
    if exc.errno in (errno.EROFS, errno.EACCES, errno.EPERM):
        return GapClass.READ_ONLY
    if exc.errno in (errno.ENOENT, errno.ENOTDIR, errno.ESTALE):
        return GapClass.PATH_GONE
    return GapClass.WRITE_FAILED


@dataclass
class Emitter:
    """One run-and-writer's emit boundary. Every event this fleet writes goes here.

    NOT FROZEN, unlike `Bag`, because it carries the per-write-path sequence
    counters that make `event_identity` deterministic. The bag's identity is its
    path and does not move; an emitter's whole job is to advance.

    ONE EMITTER PER (bag, writer), AND THE WRITER'S SUBFOLDER IS THE ISOLATION.
    Phase 1 r3 gives each writer its own payload directory precisely so no two
    writers share a file, and this appends into that directory — so two
    concurrent children each hold their own `events.jsonl` and neither can
    interleave into the other's. The one file they DO share is `bag-info.txt`,
    which `bag._tag_file_lock` now serialises.

    THE SEQUENCE COUNTER IS THREAD-GUARDED AND PROCESS-LOCAL. Two threads in one
    process emitting on one write path would otherwise derive one identity for
    two writes — which dedupe would then collapse to one, losing a write
    silently. Two PROCESSES cannot collide because they hold different writer
    subfolders. A lock is cheap and the failure it prevents is the one this
    component is named after.
    """

    bag: Bag
    writer_dir: Path
    run_id: str
    edge_id: str
    key_epoch: str = NO_CREDENTIAL_EPOCH
    _sequences: dict[str, int] = None  # type: ignore[assignment]
    _lock: threading.Lock = None       # type: ignore[assignment]

    def __post_init__(self) -> None:
        self._sequences = {}
        self._lock = threading.Lock()

    # --- construction --------------------------------------------------------

    @classmethod
    def for_run(cls, bag: Bag, *, writer: str | None,
                journal_root: Path | None = None,
                key_epoch: str = NO_CREDENTIAL_EPOCH) -> Emitter:
        """Build the emitter for one invocation of one run.

        `writer` HAS THE SAME MEANING IT HAS AT `open_run_bag` AND IS PASSED THE
        SAME WAY — never inferred. `None` means this invocation IS the run and
        its events go in a `parent` subfolder; a name means this invocation is a
        MEMBER of the run and its events go in that member's own subfolder.
        Inferring it from the environment is how a child silently becomes its own
        run, which is one of the two wrong answers Phase 9 rejects.

        ⚠ A MEMBER GETS A SUBFOLDER; AN INVOCATION THAT *IS* THE RUN DOES NOT.
        `writer=None` emits into the payload root itself, because Phase 9 already
        ruled that *"an invocation that IS the run takes no writer subfolder —
        its records are the run's, not one member's"*, and
        `test_a_STANDALONE_CHILD_produces_exactly_one_bag_and_NO_ORPHAN` holds
        it. There is no contention: a parent writes `data/events.jsonl` and each
        member writes `data/<writer>/events.jsonl`, so no two writers share a
        file — which is the property `writer_dir` exists for.

        ⚠ AND FOR A MEMBER IT ALLOCATES RATHER THAN ADOPTING, exactly as
        `open_run_bag` did, so a retry of one member emits into `w-2` rather
        than into the directory a concurrent sibling is writing. The cost is a
        subfolder per attempt, visible in the bag rather than silent — and
        dedupe-on-identity is what makes the duplicate events across the two
        harmless on read.

        THE EDGE ID IS RESOLVED FROM THE ROOT, WHICH IS THE BAG'S PARENT. It is
        per-MACHINE state (requirement 6), so it lives beside the bags and not
        inside one; taking `journal_root` explicitly lets a caller that already
        resolved it — every entrypoint does, via `RunContext` — avoid resolving
        it twice and disagreeing.
        """
        root = journal_root if journal_root is not None else bag.path.parent
        return cls(bag=bag,
                   writer_dir=bag.writer_dir(writer) if writer else bag.payload_dir,
                   run_id=bag.run_id,
                   edge_id=resolve_edge_id(root),
                   key_epoch=key_epoch)

    # --- the append boundary -------------------------------------------------

    @property
    def events_path(self) -> Path:
        return self.writer_dir / EVENTS_FILE

    def _next_sequence(self, write_path: str) -> int:
        with self._lock:
            nxt = self._sequences.get(write_path, 0)
            self._sequences[write_path] = nxt + 1
            return nxt

    def _append(self, event: JournalEvent) -> None:
        """The one place a byte reaches the journal root. Raises, never swallows.

        `O_APPEND` AND NOT `write_payload`. A payload file is written once and
        `Bag.write_payload` carries `O_EXCL` to hold that; this file GROWS, one
        JSON line per emit, so it is a different operation with a different
        guarantee. Conflating them behind one method is how the append path would
        silently acquire a truncate.

        THE MODE IS `FILE_MODE` AT CREATION, for the reason every other writer in
        this package sets it there: an `open()` then `chmod` leaves a window in
        which a world-readable file holding authored content — including
        transcript bytes — exists on a multi-user host.

        `flush` + `fsync` BEFORE RETURNING, AND THIS IS WHAT MAKES WRITE-AHEAD
        ORDERING REAL RATHER THAN NOMINAL. Without it the intent sits in the
        page cache while the store write goes out over the network, and a power
        loss between them leaves exactly the state case (b) exists to forbid: the
        store has content the record does not. Ordering two writes means nothing
        if the first has not reached the disk.
        """
        line = encode_event(event) + "\n"
        fd = os.open(str(self.events_path),
                     os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW,
                     FILE_MODE)
        with os.fdopen(fd, "a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())

    def _build(self, *, kind: EventKind, write_path: str, sequence: int,
               destination: Destination, content: str,
               provenance: Provenance, lineage: Lineage) -> JournalEvent:
        """Filter at capture, then construct. THE ORDER IS REQUIREMENT 10.

        The filter runs BEFORE any byte reaches the journal root — not before the
        bag is sealed, which under write-ahead ordering would leave unfiltered
        bytes in appended event files for the life of the run, and not AT seal,
        which would change written events and is what requirement 8 forbids.

        WHEN IT FIRES, TWO EVENTS EXIST AND NOT ONE. The filtered content goes on
        the real event, and a `redaction_placeholder` event records the FACT and
        the byte count — so the record stays complete about the removal rather
        than silently shorter. The placeholder gets its own sequence, because two
        events sharing an identity is what an intent/completion PAIR means and a
        placeholder is not one.
        """
        result = filter_capture(content)
        if result.fired:
            placeholder = redaction_placeholder_event(
                run_id=self.run_id, edge_id=self.edge_id,
                key_epoch=self.key_epoch, write_path=write_path,
                sequence=self._next_sequence(write_path),
                destination=destination, removed_bytes=result.removed_bytes,
                rule=",".join(result.rules_fired), provenance=provenance)
            self._append(placeholder)
        return JournalEvent(
            kind=kind,
            event_id=event_identity(run_id=self.run_id, write_path=write_path,
                                    sequence=sequence),
            run_id=self.run_id, edge_id=self.edge_id, key_epoch=self.key_epoch,
            provenance=provenance, write_path=write_path, sequence=sequence,
            destination=destination, content=result.text,
            content_bytes=len(result.text.encode("utf-8")), lineage=lineage)

    # --- case (b): the paired write -----------------------------------------

    def paired_write(self, *, write_path: str, destination: Destination,
                     content: str, perform: Callable[[], T],
                     address_of: Callable[[T], str] = lambda _r: "",
                     provenance: Provenance = Provenance.FLEET_AUTHORED,
                     lineage: Lineage | None = None) -> T:
        """One unit, two events: intent → the store write → completion.

        THE INVARIANT IS *IF ANY STORE GETS IT, THE JOURNAL GETS IT*, AND THIS
        ORDERING IS WHAT MAKES IT SELF-ENFORCING. A journal failure means
        `perform` is never called, so NEITHER side happened and the invariant
        holds because both are absent.

        `perform` IS A CALLABLE AND NOT A RESULT, WHICH IS THE WHOLE POINT. Taking
        an already-performed result would mean the store write had already
        happened by the time this function ran — the exact inversion case (b)
        forbids, arriving as an API shape rather than as a bug. It cannot be
        called wrongly, because there is no way to call it that performs the
        write first.

        `address_of` EXTRACTS THE STORE-ASSIGNED ADDRESS FROM THE RESULT. A
        GitHub comment has no id or URL until after it is created, and
        requirement 8 forbids changing the written intent — so the address lands
        on the COMPLETION. That is the third thing one event per write cannot
        carry.

        THE STORE WRITE DERIVES ITS IDEMPOTENCY KEY FROM THE SAME IDENTITY the
        two events share, and that identity is returned to the caller through
        `perform`'s closure rather than passed in — a caller that needs it reads
        `event_identity(run_id=…, write_path=…, sequence=…)` for the same inputs
        and gets the same value, which is what "deterministic" buys. **A retry is
        then a no-op on BOTH sides rather than on one**, which is the failure
        row `events.applied_intents` cannot fix by itself: dedupe covers the
        journal, and only an idempotency key covers the store.

        ⚠ A FAILED STORE WRITE IS RECORDED AND RE-RAISED, never swallowed. The
        `store_write_failure` event is what stops Phase 4 replaying an intent
        into content nobody published — *the rebuild is supposed to restore what
        happened, not complete what did not.*
        """
        sequence = self._next_sequence(write_path)
        intent = self._build(kind=EventKind.INTENT, write_path=write_path,
                             sequence=sequence, destination=destination,
                             content=content, provenance=provenance,
                             lineage=lineage or Lineage())
        try:
            self._append(intent)
        except OSError as exc:
            raise EmitFailed(
                f"the intent event for {write_path} could not be written to "
                f"{self.events_path} — {exc.strerror}. The store write was NOT "
                f"performed, so neither side of this write happened and the "
                f"record is short but not wrong.\n"
                f"  the run stops here rather than continuing: every later "
                f"step's record would be conditioned on a write nobody can see."
            ) from exc

        try:
            result = perform()
        except Exception as exc:
            failure = JournalEvent(
                kind=EventKind.STORE_WRITE_FAILURE, event_id=intent.event_id,
                run_id=self.run_id, edge_id=self.edge_id,
                key_epoch=self.key_epoch, provenance=provenance,
                write_path=write_path, sequence=sequence,
                destination=destination,
                terminal_state=TerminalState.STORE_WRITE_FAILED)
            try:
                self._append(failure)
            except OSError:
                # THE ORIGINAL FAILURE IS WHAT THE CALLER NEEDS, and a second
                # exception raised from this handler would mask it. So the bag
                # is marked instead — the record then says a write is missing
                # even though it could not say which.
                try:
                    self.bag.mark_incomplete(
                        write_path, "store write failed and its failure event "
                                    "could not be written")
                except (OSError, BagError):
                    # NAMED, NOT SWALLOWED SILENTLY: what is ignored is a failed
                    # `incomplete` flag while already handling a failed store
                    # write AND a failed failure-event. At that point the journal
                    # is gone, `StoreWriteFailed` below is what the caller needs
                    # to see, and case (d) reporting is the caller's to do from
                    # the exception it is about to receive.
                    pass
            raise StoreWriteFailed(
                f"the store write for {write_path} failed after its intent "
                f"landed: {exc}. A store-write-failure event was recorded, so "
                f"replay will not apply the intent — Phase 4 rebuilds what "
                f"happened, not what did not."
            ) from exc

        completion = JournalEvent(
            kind=EventKind.COMPLETION, event_id=intent.event_id,
            run_id=self.run_id, edge_id=self.edge_id, key_epoch=self.key_epoch,
            provenance=provenance, write_path=write_path, sequence=sequence,
            destination=Destination(store=destination.store,
                                    address=address_of(result)),
            terminal_state=TerminalState.COMPLETED, lineage=intent.lineage)
        try:
            self._append(completion)
        except OSError as exc:
            # ⚠ THE STORE WRITE HAS ALREADY HAPPENED, so stopping the run would
            # not un-happen it. What matters is that the record does not claim an
            # applied write it cannot prove — and an intent with no completion is
            # exactly that claim withheld. The gap is recorded and the run stops,
            # because the journal has just refused a write and every later step
            # would be conditioned on it.
            self._record_gap(write_path=write_path, exc=exc,
                             destination=destination,
                             lost_bytes=len(content.encode("utf-8")))
            raise EmitFailed(
                f"the completion event for {write_path} could not be written — "
                f"{exc.strerror}. The store write DID land; the journal cannot "
                f"prove it, so replay will not apply the intent and the bag is "
                f"marked incomplete."
            ) from exc
        return result

    # --- case (c): the unpairable write -------------------------------------

    def unpairable_write(self, *, write_path: str, destination: Destination,
                         content: str,
                         provenance: Provenance = Provenance.FLEET_AUTHORED,
                         lineage: Lineage | None = None,
                         stop_on_failure: bool = False) -> None:
        """A write with no store write to withhold — recorded, not prevented.

        The CLI transcript, the execution facts and Phase 10's post-exit harvest
        are this case: the content already exists and the only question is
        whether it lands, so write-ahead ordering has nothing to offer. A failure
        produces a typed gap event and marks the bag `incomplete`, and everything
        downstream then treats that bag as a known-gap input rather than a clean
        one — Phase 4 reports gapped bags with a count and its denominator rather
        than diffing them as complete, Phase 6 says so in its own report, and
        Phase 7 ships the marking with the bag.

        ⚠ `stop_on_failure` IS THE TRANSCRIPT'S ARM AND IT IS A PARAMETER RATHER
        THAN A BRANCH INSIDE THIS FUNCTION. The transcript is the fleet's only
        record of what commands ran, this fleet runs with permissions bypassed,
        and a run can itself create the disk-full condition that drops it. Losing
        it while the run proceeds to completion is evidence loss wearing a
        routine defect's clothes, so a failed transcript write is treated as case
        (b) — the run stops. The other two members (execution facts, post-exit
        harvest) are gaps and the run continues. **The caller is what knows which
        member it is holding**, so the caller passes the flag; deciding it in
        here would need this function to pattern-match on `write_path`, which is
        a rule about strings rather than about content.

        THE MODEL-ISSUED HALF OF THE INVENTORY IS THIS CASE BY CONSTRUCTION, and
        the docs must not imply otherwise: when the child runs `gh pr comment`
        itself, the content exists before the fleet sees it, so the harvest emits
        a COMPLETION WITH NO PRIOR INTENT — a legitimate typed shape rather than a
        hole. That half is protected by *"a gap event names what was lost"*, not
        by *"neither side is written"*, and it is a materially weaker guarantee.
        """
        sequence = self._next_sequence(write_path)
        event = self._build(kind=EventKind.COMPLETION, write_path=write_path,
                            sequence=sequence, destination=destination,
                            content=content, provenance=provenance,
                            lineage=lineage or Lineage())
        try:
            self._append(event)
        except OSError as exc:
            self._record_gap(write_path=write_path, exc=exc,
                             destination=destination,
                             lost_bytes=len(content.encode("utf-8")))
            if stop_on_failure:
                raise EmitFailed(
                    f"{write_path} could not be written to the journal — "
                    f"{exc.strerror} — and this write path stops the run. It is "
                    f"the fleet's only record of what commands ran, under "
                    f"bypassed permissions; continuing past it would be evidence "
                    f"loss wearing a routine defect's clothes."
                ) from exc

    def _record_gap(self, *, write_path: str, exc: OSError,
                    destination: Destination, lost_bytes: int) -> None:
        """Case (c)'s record, and case (d) is what happens when even this fails.

        TWO WRITES, AND EITHER CAN FAIL. The gap EVENT goes in the writer's own
        `events.jsonl`; the `incomplete` FLAG plus its record go in
        `bag-info.txt`. They are separate files with separate failure modes, and
        the flag is the more important of the two — it is what Phase 4, Phase 6
        and Phase 7 branch on — so it is attempted even when the event could not
        be written.

        **If BOTH fail, the journal is unwritable and this is case (d)**:
        `JournalUnwritable` is raised, and the caller reports it on the two
        channels that are not the journal. That is the case that makes (c)
        circular if it is not answered.
        """
        gap = gap_event(run_id=self.run_id, edge_id=self.edge_id,
                        key_epoch=self.key_epoch, write_path=write_path,
                        sequence=self._next_sequence(write_path),
                        gap_class=gap_class_for(exc), lost_bytes=lost_bytes,
                        destination=destination)
        event_written = True
        try:
            self._append(gap)
        except OSError:
            event_written = False

        try:
            self.bag.mark_incomplete(
                write_path, f"emit failed: {gap_class_for(exc).value}")
        except (OSError, BagError) as flag_exc:
            if not event_written:
                raise JournalUnwritable(
                    f"{UNWRITABLE_JOURNAL_MARKER}: the journal cannot be "
                    f"written and neither can the record of that. "
                    f"{write_path} failed with {exc.strerror}, and the "
                    f"gap event and the `incomplete` flag both failed after it.\n"
                    f"  bag: {self.bag.path}\n"
                    f"  this is requirement 4 case (d). It is reported on the "
                    f"typed exit record and on a durable working-record surface, "
                    f"because the journal is not available to report it."
                ) from flag_exc


# ---------------------------------------------------------------------------
# Requirement 11 — the two channels case (d) reports on, WITH their readers.
# ---------------------------------------------------------------------------

def unwritable_journal_report(exc: JournalUnwritable, *,
                              bag_path: Path | None = None) -> dict[str, str]:
    """PRODUCER for both channels: the exit-record field and the durable line.

    ONE FUNCTION FOR BOTH so the two cannot disagree about what happened. The
    exit record is read within seconds and then gone; the durable half is a
    pull-request comment, which is durable, addressable, and outside the journal
    root by construction. **Both are needed and neither is sufficient** — the
    first because a parent has to route on it in-process, the second because
    every consumer this component builds reads the record long after the process
    is gone.

    `terminal_state` IS `TerminalState.JOURNAL_UNWRITABLE`, from
    `modules/vocabulary.py` — the same declaration the journal event's own
    `terminal_state` comes from. That is requirement 3 doing its job on the one
    field that crosses both contracts on the failure path.

    ⚠ THE THIRD CHANNEL IS THE PROCESS EXIT, AND IT IS ALREADY WIRED BY
    INHERITANCE RATHER THAN BY THIS FUNCTION. `JournalUnwritable` subclasses
    `RuntimeError`, so every entrypoint's existing `except RuntimeError: return
    refuse(exc)` prints its message and exits non-zero — and the message now
    LEADS with `UNWRITABLE_JOURNAL_MARKER`, so `unwritable_journal_in_text`
    reads the process's own output as well as a PR comment. One declared
    literal, three surfaces, and no entrypoint edited to get it.
    """
    return {
        "terminal_state": TerminalState.JOURNAL_UNWRITABLE.value,
        "marker": UNWRITABLE_JOURNAL_MARKER,
        "bag": str(bag_path) if bag_path is not None else "",
        "detail": str(exc).splitlines()[0] if str(exc) else "",
    }


def unwritable_journal_in_text(text: str) -> bool:
    """READER of the durable half. The named consumer requirement 11 demands.

    A SUBSTRING TEST AGAINST THE ONE DECLARED MARKER, and it is deliberately not
    a parse. The durable channel is a PR comment written by a run whose journal
    has just failed; a structured format there would be one more thing that can
    fail on the path that exists to report a failure. The marker is distinctive
    enough not to occur in ordinary prose and plain enough for a human scanning
    the thread.

    ⚠ WHAT IT DOES NOT LOOK AT: whether the line was written by the run it names,
    or by a person quoting one. A PR thread is an open surface — the same
    property that makes `review_pr_helper` anchor its `pr_review:` block on a
    fence rather than on a substring — so this answers *does this text report an
    unwritable journal*, and never *did this run's journal fail*. The
    authoritative answer to the second is the exit record's `terminal_state`,
    which is in-process and unforgeable by a thread participant.
    """
    return UNWRITABLE_JOURNAL_MARKER in text


# ---------------------------------------------------------------------------
# The run's emit boundary, reachable from a write path that has no bag argument.
# ---------------------------------------------------------------------------

_CURRENT: Emitter | None = None
_CURRENT_LOCK = threading.Lock()


def register_emitter(emitter: Emitter | None) -> None:
    """Make `emitter` the one every write path in this process emits through.

    ⚠ THIS IS PROCESS-SCOPED STATE AND THAT IS A DELIBERATE TRADE, NOT AN
    OVERSIGHT. Requirement 12 says the emit is *"an ACTIVITY, not a library call
    each workflow remembers to make"* — and the fleet's write paths
    (`assistant_activities.gh_attempt`, `tracked_items`) are reached from dozens
    of call sites that hold no bag. The alternatives were each worse:

      * **Thread a `Bag` through every caller.** Forty-odd signatures change, and
        every one of them can be called without it — which is the optional
        control this component's whole thesis says is a skipped control. It also
        does not survive a new call site, which is the case that matters.
      * **Have each write path open its own bag.** Two bags for one run, keyed by
        the same `run_id`, with `open_bag` refusing the second. Worse than
        ambient state: it fails at runtime rather than at review.

    So the boundary is registered ONCE, by `open_run_bag`, where Phase 1 r11
    already put the run's first I/O step — and a write path that finds no
    registered emitter is a write path running OUTSIDE a run, which is a real
    state (a unit test, a helper script, `validate_bag`) and not an error.

    ⚠ WHAT THIS DOES NOT REACH, restated because ambient state invites the
    assumption that it reaches everything: a MODEL-ISSUED write. When the child
    process runs `gh pr comment` itself there is no call site in this process at
    all, so no registry can see it. That half is Phase 10's post-exit harvest.

    `None` UNREGISTERS, and a test that registers must unregister — otherwise one
    test's emitter receives another test's writes, into a `tmp_path` that has
    already been removed. `emitting_into` below is the context manager that makes
    that automatic.
    """
    global _CURRENT
    with _CURRENT_LOCK:
        _CURRENT = emitter


def current_emitter() -> Emitter | None:
    """The registered emitter, or `None` outside a run.

    `None` IS A LEGITIMATE ANSWER AND IS NOT DEFAULTED PAST. A caller wraps its
    write when there is an emitter and performs it unwrapped when there is not —
    which is what lets `gh` be called from a helper script with no journal at
    all. Manufacturing a throwaway emitter here would write a bag for a process
    that is not a run, under a `run_id` nobody minted.
    """
    with _CURRENT_LOCK:
        return _CURRENT


class emitting_into:
    """Register an emitter for the duration of a block, then restore.

    Lower-case because it reads as a statement at the call site, the same
    convention `contextlib.suppress` uses. RESTORES THE PREVIOUS VALUE rather
    than clearing, so a nested block — a helper that opens a second bag inside a
    run — leaves the outer run's boundary intact instead of silently detaching
    every later write path in the process.
    """

    def __init__(self, emitter: Emitter | None) -> None:
        self._emitter = emitter
        self._previous: Emitter | None = None

    def __enter__(self) -> Emitter | None:
        self._previous = current_emitter()
        register_emitter(self._emitter)
        return self._emitter

    def __exit__(self, exc_type, exc, tb) -> bool:
        register_emitter(self._previous)
        return False

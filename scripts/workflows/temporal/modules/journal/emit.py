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
in the journal either.** `unwritable_journal_report` below builds the payload;
`CASE_D_CHANNELS` above declares which surfaces actually carry it, and
`test_the_case_d_CHANNEL_TABLE_matches_the_tree` derives that table from the tree
rather than from this paragraph. **Read that table, not this sentence** — an
earlier version of this paragraph named the two channels that have no producer
and omitted the one that does.

The DESIGN calls for three, and the reasoning is why the table has three rows:
the typed exit record plus a non-zero exit status carry it out of the process,
**and both are invocation state — read within seconds and then gone**, so a
durable half is needed too, and that is a pull-request comment: durable,
addressable, and outside the journal root by construction. **Not the standup
tracker** — that surface is `tracked/operations/`, which Tracked Items §1.2 makes
human-in-the-loop only with no autonomous write ever, and offering it here would
put a binding-standard violation on the one path that exists to report this
component being broken.

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

## Requirement 11 — each signal that SHIPPED shipped with its reader

Adding a field to a channel and leaving the reading to somebody later is how this
fleet has already lost three observables, and the one channel this component's
failure path depends on is the last place to repeat it. So the rule here is the
inverse of the usual one: a channel ships only WITH its reader, and a channel
whose reader would have to be written elsewhere does not ship at all.

**ONE of the three channels ships in this change and the other two do not**, per
`CASE_D_CHANNELS` above. The process exit carries the signal — `JournalUnwritable`
subclasses `RuntimeError`, so every entrypoint's existing handler prints a message
LEADING with `UNWRITABLE_JOURNAL_MARKER` — and `unwritable_journal_in_text` is its
committed reader. The durable working-record line has its producer built
(`gh_attempt(case_d_report=True)`) and **no caller**; the exit-record field is not
built at all, because it needs a parent branch outside this change and a field
with no branch is precisely the observable-with-no-reader this requirement forbids.

`test_journal_emit.py` holds the shipped half to its reader rather than this
paragraph — see `test_the_marker_is_ONE_declaration_shared_by_producer_and_reader`
and the case-(d) tests beside it.
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
           "UNWRITABLE_JOURNAL_MARKER", "CASE_D_CHANNELS",
           "case_d_channel_sentence", "unwritable_journal_report",
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

#: THE THREE CHANNELS CASE (d) COULD REPORT ON, AND WHICH OF THEM ACTUALLY HAS A
#: PRODUCER — declared once, as data, because stating it in prose drifted at five
#: sites on one branch. Every one of them said case (d) *"is reported on the typed
#: exit record and on a durable working-record surface"*; NEITHER of those has a
#: live producer, and the channel that does — the process exit — was the one none
#: of them named. On the single failure path where this component cannot speak for
#: itself, that sent an operator to two surfaces carrying nothing and away from the
#: one carrying the signal, so they conclude the report was lost.
#:
#: THE SECOND FIELD IS DERIVED FROM THE TREE BY
#: `test_the_case_d_CHANNEL_TABLE_matches_the_tree`, not asserted here. That is
#: the point: the day somebody wires the exit-record field or gives
#: `case_d_report=True` a production caller, the test goes red against this table
#: and the message below changes with it — rather than five paragraphs quietly
#: becoming true one at a time while nobody re-reads them.
CASE_D_CHANNELS: tuple[tuple[str, bool], ...] = (
    ("the process exit — a non-zero status whose message leads with "
     f"`{UNWRITABLE_JOURNAL_MARKER}`, which `unwritable_journal_in_text` reads",
     True),
    ("a durable working-record surface — a pull-request comment via "
     "`gh_attempt(case_d_report=True)`",
     False),
    ("the typed exit record — a `CHILD_SCHEMA` field a parent branches on",
     False),
)


def case_d_channel_sentence() -> str:
    """The case-(d) message's channel paragraph, COMPOSED from `CASE_D_CHANNELS`.

    Composed rather than written out, so the operator-facing sentence and the
    declared table cannot disagree. The unwired channels are NAMED rather than
    omitted: an operator who has read the phase doc knows both are planned, and a
    message that simply left them out would read as "the report went somewhere I
    have not been told about" — which is the same dead end by a quieter route.
    """
    live = [name for name, wired in CASE_D_CHANNELS if wired]
    dead = [name for name, wired in CASE_D_CHANNELS if not wired]
    if live:
        sentence = "reported on " + "; and on ".join(live)
    else:
        sentence = "NOT REPORTED ANYWHERE — every declared channel is unbuilt"
    if dead:
        sentence += (". NOT on " + "; nor on ".join(dead) +
                     " — both are declared by requirement 11 and NEITHER has a "
                     "producer yet, so nothing will appear on them")
    return sentence


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


#: What the append boundary converts into a typed case rather than letting
#: escape. `OSError` is the DISK; `UnicodeError` is the CONTENT — a lone
#: surrogate reaching `encode` raises `UnicodeEncodeError`, which is a
#: `ValueError` and therefore joins none of this module's `except OSError`
#: clauses. It escaped `paired_write` as an untyped crash, past all four cases
#: and past every entrypoint's `except RuntimeError`, until a probe raised it on
#: this branch. `edge_id.read_edge_id` had already met the same trap from the
#: decode side, which is why it names `UnicodeDecodeError` separately.
APPEND_FAILURES = (OSError, UnicodeError)


def failure_detail(exc: BaseException) -> str:
    """One line naming what failed, FOR AN EXCEPTION MESSAGE and never for the record.

    `strerror` when there is one, the type and text when there is not — a
    `UnicodeEncodeError` has no `strerror`, and reading the attribute off it
    would raise a second exception out of the handler for the first.

    THE RECORD STILL GETS NEITHER. `gap_class_for` below is what reaches the
    journal, and it is a closed set for the reason stated there; this is the
    operator-facing half the module docstring promises on stderr.

    ⚠ THE TYPE AND THE TEXT ARE JOINED BY AN EM DASH, NOT BY A COLON, and that
    is not cosmetic: `test_journal_tag_lines` sweeps this package for
    `f"{value}: …"` and refuses any such composition whose value is not proven
    unable to fold a tag line. This value is free text from an exception and CAN
    carry a newline — it simply never reaches a tag line. Spelling it as a
    label/value pair would either forge a false positive forever or need an
    exemption row, and an exemption is the thing this package has learned not to
    hand out: five forging escapes had exactly that shape.
    """
    detail = getattr(exc, "strerror", None)
    return detail if detail else f"{type(exc).__name__} — {exc}"


def utf8_len(text: str) -> int:
    """Byte length that cannot itself raise, for use on the failure path.

    `errors="replace"` because this is called while ALREADY handling a failed
    write — including one caused by content that cannot be encoded at all. A
    plain `.encode()` here would raise out of the handler and lose the gap
    record, which is the silent loss this component exists to prevent. The
    number is a report of magnitude, not a checksum.
    """
    return len(text.encode("utf-8", "replace"))


def gap_class_for(exc: BaseException) -> GapClass:
    """A failed append as one of four closed classes — never as its message.

    THE MESSAGE IS DELIBERATELY DISCARDED. A gap event reports that content was
    lost; a `why` carrying `exc.strerror` or `exc.filename` would put the failing
    path — and, for some filesystems, a fragment of what was being written — into
    the record that exists to say those bytes were dropped. Four classes, a byte
    count and a timestamp cost a few hundred bytes and cannot leak.

    THE OPERATOR STILL GETS THE MESSAGE — on stderr, and in the exception this
    module raises. What is bounded is what reaches the DURABLE record, which is
    the surface Phase 7 syncs to object storage and Phase 4 replays.
    """
    code = getattr(exc, "errno", None)
    if code in (errno.ENOSPC, errno.EDQUOT):
        return GapClass.DISK_FULL
    if code in (errno.EROFS, errno.EACCES, errno.EPERM):
        return GapClass.READ_ONLY
    if code in (errno.ENOENT, errno.ENOTDIR, errno.ESTALE):
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
        # ⚠ `_build` IS INSIDE THE GUARD, NOT ABOVE IT, AND THAT PLACEMENT IS THE
        # FIX FOR A REAL ESCAPE. `_build` appends a redaction placeholder of its
        # own whenever the capture filter fires, and it encodes the content to
        # count its bytes — so it performs I/O and it encodes, and BOTH can fail.
        # Built above the `try`, a filter that fired on a read-only mount raised a
        # bare `PermissionError` straight out of this function: no `EmitFailed`,
        # no gap, no `incomplete` flag, and past every entrypoint's
        # `except RuntimeError`. Demonstrated on this branch, against a real bag,
        # with the same call succeeding as `EmitFailed` when the filter did not
        # fire — which is what made the placeholder append the only difference.
        try:
            intent = self._build(kind=EventKind.INTENT, write_path=write_path,
                                 sequence=sequence, destination=destination,
                                 content=content, provenance=provenance,
                                 lineage=lineage or Lineage())
            self._append(intent)
        except APPEND_FAILURES as exc:
            raise EmitFailed(
                f"the intent event for {write_path} could not be written to "
                f"{self.events_path} — {failure_detail(exc)}. The store write "
                f"was NOT "
                f"performed, so neither side of this write happened and the "
                f"record is short but not wrong.\n"
                f"  the run stops here rather than continuing: every later "
                f"step's record would be conditioned on a write nobody can see."
            ) from exc

        try:
            result = perform()
        except Exception as exc:
            recorded = "a store-write-failure event was recorded"
            # INSIDE THE GUARD, same class as the completion below and the intent
            # above: `JournalEvent.__post_init__` is an admission gate that
            # raises, and this construction sits in a handler that is ALREADY
            # recovering from one failure — an exception escaping here would
            # replace the store failure the caller's handlers are written against
            # with an untyped crash. `except Exception` for the reason the
            # completion block gives: every failure to record this has one
            # outcome, so they get one handler.
            try:
                failure = JournalEvent(
                    kind=EventKind.STORE_WRITE_FAILURE,
                    event_id=intent.event_id,
                    run_id=self.run_id, edge_id=self.edge_id,
                    key_epoch=self.key_epoch, provenance=provenance,
                    write_path=write_path, sequence=sequence,
                    destination=destination,
                    terminal_state=TerminalState.STORE_WRITE_FAILED)
                self._append(failure)
            except Exception:
                # THE ORIGINAL FAILURE IS WHAT THE CALLER NEEDS, and a second
                # exception raised from this handler would mask it. So the bag
                # is marked instead — the record then says a write is missing
                # even though it could not say which.
                recorded = ("its store-write-failure event could NOT be written "
                            "and the bag was marked incomplete instead")
                try:
                    self.bag.mark_incomplete(
                        write_path, "store write failed and its failure event "
                                    "could not be written")
                except (OSError, BagError):
                    # ⚠ NEITHER THE EVENT NOR THE FLAG LANDED, so nothing in the
                    # journal says this write is missing — which is case (d)
                    # reached from the store-failure path. `StoreWriteFailed` is
                    # still what the caller needs (its handlers are written
                    # against the store failure), so the journal's death is
                    # carried OUT on this message rather than replacing it, and
                    # it LEADS with the one declared marker so
                    # `unwritable_journal_in_text` reads it on the process
                    # channel exactly as it reads a durable comment. Swallowing
                    # it — which this did — left the single case where the
                    # journal is gone and no surface says so.
                    recorded = (f"{UNWRITABLE_JOURNAL_MARKER}: neither the "
                                f"store-write-failure event nor the incomplete "
                                f"flag could be written, so the journal says "
                                f"nothing about this write at all")
            raise StoreWriteFailed(
                f"the store write for {write_path} failed after its intent "
                f"landed: {exc}. {recorded}, so "
                f"replay will not apply the intent — Phase 4 rebuilds what "
                f"happened, not what did not."
            ) from exc

        # ⚠ THE COMPLETION IS BUILT INSIDE THE GUARD FOR THE REASON THE INTENT IS,
        # AND THIS SITE WAS THE ASYMMETRIC HALF OF THAT PAIR. `address_of` is
        # CALLER-SUPPLIED — it parses a store reply — so it can raise anything,
        # and `JournalEvent.__post_init__` is an admission gate that raises
        # `EventError`. Evaluated above the `try`, either escaped `paired_write`
        # bare, AFTER the store write had already landed and was therefore
        # unrecoverable: no `EmitFailed`, no gap event, no `incomplete` flag, and
        # — for an `address_of` raising `IndexError` or a JSON `ValueError` —
        # past every entrypoint's `except RuntimeError` as well. The four callers
        # this branch ships are all defensive, so the invariant held by their
        # good manners rather than by construction; a fifth write path whose
        # `address_of` parses a store reply is where that stops being true.
        #
        # `except Exception` AND NOT `APPEND_FAILURES`, DELIBERATELY. Once
        # `perform()` has returned, every failure in this block has ONE outcome —
        # the store write landed and the record cannot prove it — so they get one
        # handler. Narrowing it to the append's own exception set is what left
        # the caller-supplied callable outside the taxonomy in the first place.
        try:
            completion = JournalEvent(
                kind=EventKind.COMPLETION, event_id=intent.event_id,
                run_id=self.run_id, edge_id=self.edge_id,
                key_epoch=self.key_epoch,
                provenance=provenance, write_path=write_path, sequence=sequence,
                destination=Destination(store=destination.store,
                                        address=address_of(result)),
                terminal_state=TerminalState.COMPLETED, lineage=intent.lineage)
            self._append(completion)
        except Exception as exc:
            # ⚠ THE STORE WRITE HAS ALREADY HAPPENED, so stopping the run would
            # not un-happen it. What matters is that the record does not claim an
            # applied write it cannot prove — and an intent with no completion is
            # exactly that claim withheld. The gap is recorded and the run stops,
            # because the journal has just refused a write and every later step
            # would be conditioned on it.
            self._record_gap(write_path=write_path, exc=exc,
                             destination=destination,
                             lost_bytes=utf8_len(content))
            raise EmitFailed(
                f"the completion event for {write_path} could not be written — "
                f"{failure_detail(exc)}. The store write DID land; the journal "
                f"cannot "
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
        # INSIDE THE GUARD for the reason `paired_write` states — and it matters
        # more here, because this case has no store write to withhold. A
        # placeholder append that escaped uncaught would lose the content AND the
        # gap record, which is the silent gap this whole component is named after.
        try:
            event = self._build(kind=EventKind.COMPLETION, write_path=write_path,
                                sequence=sequence, destination=destination,
                                content=content, provenance=provenance,
                                lineage=lineage or Lineage())
            self._append(event)
        except APPEND_FAILURES as exc:
            self._record_gap(write_path=write_path, exc=exc,
                             destination=destination,
                             lost_bytes=utf8_len(content))
            if stop_on_failure:
                raise EmitFailed(
                    f"{write_path} could not be written to the journal — "
                    f"{failure_detail(exc)} — and this write path stops the run. "
                    f"It is "
                    f"the fleet's only record of what commands ran, under "
                    f"bypassed permissions; continuing past it would be evidence "
                    f"loss wearing a routine defect's clothes."
                ) from exc

    def _record_gap(self, *, write_path: str, exc: BaseException,
                    destination: Destination, lost_bytes: int) -> None:
        """Case (c)'s record, and case (d) is what happens when even this fails.

        TWO WRITES, AND EITHER CAN FAIL. The gap EVENT goes in the writer's own
        `events.jsonl`; the `incomplete` FLAG plus its record go in
        `bag-info.txt`. They are separate files with separate failure modes, and
        the flag is the more important of the two — it is what Phase 4, Phase 6
        and Phase 7 branch on — so it is attempted even when the event could not
        be written.

        **IF THE FLAG FAILS, THIS IS CASE (d) — whether or not the event
        landed**: `JournalUnwritable` is raised, and it carries itself out on
        whichever channels are not the journal — `CASE_D_CHANNELS` is the
        authority on which of the three those are, and the message composes its
        own answer from that table rather than naming them here. That is a SIXTH
        site: the five that named the two channels with no producer were all
        prose asserting the same unbuilt fact. That is the case that makes (c)
        circular if it is not answered. The raise is NOT conditioned on the event
        also having failed, because nothing downstream reads a writer's
        `events.jsonl` to decide whether a bag is clean — a gap event beside a
        missing flag is a bag that lost data and reads as complete, which is the
        outcome this function exists to prevent.
        """
        # ONE DERIVATION, READ TWICE. Computed once so the event's class and the
        # flag's reason cannot disagree about what happened — two calls agree
        # today only because the function is pure, which is agreement by
        # accident rather than by construction.
        gap_class = gap_class_for(exc)
        event_written = True
        # THE EVENT IS BUILT INSIDE THE GUARD, third member of the same class as
        # the two sites in `paired_write`. `gap_event` constructs a
        # `JournalEvent`, whose `__post_init__` raises `EventError` — and this
        # function's whole job is to run on the failure path, so an exception
        # escaping it loses the gap record AND masks the failure it was called to
        # record. `gap_class_for` stays outside because it cannot raise and the
        # flag below reads the same derivation (ONE derivation, read twice).
        try:
            gap = gap_event(run_id=self.run_id, edge_id=self.edge_id,
                            key_epoch=self.key_epoch, write_path=write_path,
                            sequence=self._next_sequence(write_path),
                            gap_class=gap_class, lost_bytes=lost_bytes,
                            destination=destination)
            self._append(gap)
        except Exception:
            event_written = False

        try:
            self.bag.mark_incomplete(
                write_path, f"emit failed: {gap_class.value}")
        except (OSError, BagError) as flag_exc:
            # ⚠ A FAILED FLAG RAISES WHETHER OR NOT THE EVENT LANDED, and the
            # earlier `if not event_written` guard here was the one hole in *a
            # gap may exist; a silent gap may not*. The flag is the MORE
            # important of the two writes — Phase 4, Phase 6 and Phase 7 branch
            # on it, and none of them reads a writer's `events.jsonl` to decide
            # whether a bag is clean. So a gap event that landed beside a flag
            # that did not produced a bag which LOST DATA AND READS AS COMPLETE,
            # returning normally with no signal to any caller: exactly the
            # outcome Phase 1's four-state design exists to prevent, reached
            # through the function that exists to prevent it.
            landed = ("the gap event landed but nothing downstream reads it to "
                      "decide a bag is clean"
                      if event_written else
                      "neither the gap event nor the flag landed")
            raise JournalUnwritable(
                f"{UNWRITABLE_JOURNAL_MARKER}: the journal cannot be "
                f"written and neither can the record of that. "
                f"{write_path} failed with {failure_detail(exc)}, and the "
                f"`incomplete` flag failed after it with "
                f"{failure_detail(flag_exc)} — {landed}.\n"
                f"  bag: {self.bag.path}\n"
                f"  this is requirement 4 case (d), and it is "
                f"{case_d_channel_sentence()}."
            ) from flag_exc


# ---------------------------------------------------------------------------
# Requirement 11 — the case-(d) signal and its reader. `CASE_D_CHANNELS` above
# is the authority on WHICH channels carry it; exactly one does today, and this
# section builds the payload and the reader for all three so that wiring the
# other two is a call site rather than a contract.
# ---------------------------------------------------------------------------

def unwritable_journal_report(exc: JournalUnwritable, *,
                              bag_path: Path | None = None) -> dict[str, str]:
    """The case-(d) payload, in the one shape all three channels would carry.

    ONE FUNCTION FOR ALL OF THEM so no two channels can disagree about what
    happened. **It has NO PRODUCTION CALLER TODAY, and that is stated rather than
    implied**: `CASE_D_CHANNELS` above is the authority, and the only channel with
    a live producer is the process exit — which is wired by INHERITANCE (see the
    warning below) and does not call this function. This exists so that wiring
    either remaining channel is a call site rather than a contract.

    The design needs all three and none is sufficient alone: the exit record
    because a parent has to route on it in-process, the durable pull-request
    comment because every consumer this component builds reads the record long
    after the process is gone, and the exit status because it is the only one
    that needs nothing built.

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
    """READER for every channel that carries the marker — the named consumer
    requirement 11 demands, and today that is the PROCESS OUTPUT rather than the
    durable half, because the durable half has no producer (`CASE_D_CHANNELS`).

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

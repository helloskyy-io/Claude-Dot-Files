"""The journal event — one contract, four admission fields, never mutated.

THIS IS PHASE 3's CONTRACT AND IT IS SEPARATE FROM THE TYPED EXIT RECORD'S, for
a reason that is a standard rather than a preference. `exit-protocol.md` §2 says
*"no field is added on behalf of a consumer that does not exist"* and §2.5 bounds
that record's fixed part at 4096 bytes. Requirement 7 adds event identity, a
credential epoch and a provenance class; requirements 1, 5 and 6 add destination,
lineage and `edge_id`. **No parent branches on any of the six**, so the first rule
rejects every one of them — and an event carries authored content verbatim, which
one measured `research_minor` cycle put at 39,772 bytes against a 4096-byte bound.
An extension is therefore not available; two contracts sharing one vocabulary is.
`modules/vocabulary.py` is that vocabulary and this module imports it rather than
respelling anything in it.

THE DESTINATION IS A FIELD, NOT A FORMAT (requirement 2). git, SQLite, a GitHub
object, an MQTT topic on an edge with no repo — the event is byte-identical in
shape whichever it was, because that is what makes a record portable across edges
and it is what Phase 7 depends on. `Destination` below carries the store's name
and its address; nothing about the event's serialisation varies with it.

AN EVENT RECORDS AN INTENT, AND A SECOND EVENT RECORDS THE FACT. Write-ahead
ordering protects exactly one of the three ways a paired write can break, and the
phase doc's § *Why one event per write is not enough* names the other two: a
store write that fails after a successful emit makes the journal claim content
the store never got — and Phase 4 would then REPLAY it, materialising unpublished
content nobody approved — and a retried activity re-runs both side effects. A
third thing one event cannot carry is the store's own address, which a GitHub
comment does not have until after it exists and which requirement 8 forbids
adding by editing the event. So a paired write is ONE UNIT WITH TWO EVENTS
sharing one identity, and `applied_intents` below is the replay rule that makes
the first two failures visible: **an intent with no completion is not applied**.

EVERY EVENT CARRIES A SCHEMA VERSION AND NO WRITTEN EVENT IS EVER CHANGED
(requirement 8). The version is `bag.JOURNAL_SCHEMA_VERSION`, declared there in
Phase 1 and honoured here — not a second constant. A journal written under v1
must still replay under v3 forever; the settled answer is version every event,
never mutate a written one, upcast on read. The upcaster's mechanism is open
(roadmap § *Open inputs* item 2) and this module does not close it — but an
unversioned v1 event is unrecoverable, so the field ships now.

⚠ `edge_id` IS SELF-REPORTED AND IS NOT AN ATTRIBUTION CONTROL. Requirement 7(b)
is explicit: the target is an id assigned by an authenticating authority and
bound at ingest, and there is no ingest tier in this design — Phase 7 syncs
sealed bags straight to object storage and a receiver cannot rebind a field
inside a sealed bag without invalidating its manifest. So until an authenticating
ingest exists, any holder of a valid credential can author events attributed to
another edge, and this doc says so rather than stating a guarantee nothing
enforces. The control that DOES exist in this topology is Phase 7 r5's: a
per-machine storage credential scoped to that machine's own prefix, with origin
derived from the prefix and a prefix/`edge_id` disagreement reported as a
finding. The field stays on the event because a reader needs something to filter
on and because a later ingest tier can begin binding it with no schema change.

⚠ AND NO EVENT EVER CARRIES A KEY OR A VALUE DERIVED FROM ONE. `key_epoch` is an
opaque non-secret label — requirement 7(c) — explicitly not derived from the key
it names. `hash(api_key)` is ruled out twice over: it changes on rotation, which
is the bug `edge_id` exists to prevent, and a stored hash of a live credential is
an offline confirmation oracle. `edge_id.py` holds that constraint at the point
of derivation; this module holds it at the point of admission.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from ..vocabulary import Outcome, TerminalState
from .bag import JOURNAL_SCHEMA_VERSION, utc_now

__all__ = ["EventKind", "Provenance", "Destination", "Lineage", "JournalEvent",
           "EventError", "event_identity", "dedupe_on_identity",
           "applied_intents", "gap_event", "redaction_placeholder_event",
           "EVENTS_FILE", "encode_event", "decode_event", "GapClass"]


#: The file one writer appends its events to, inside its own payload subfolder.
#: JSON Lines: one event per line, appended, never rewritten. A line-oriented
#: format is what makes "append-only" a property of the WRITE rather than a
#: promise about the writer — a re-serialised array would rewrite every prior
#: event on every append, which is exactly what requirement 8 forbids.
EVENTS_FILE = "events.jsonl"


class EventError(RuntimeError):
    """An event could not be constructed or admitted.

    `RuntimeError` for the reason `BagError` and `JournalRootError` are: every
    entrypoint already carries `except RuntimeError` around its preconditions,
    and the message is the diagnostic.
    """


class EventKind(str, Enum):
    """What kind of record this event is. Five, and the set is closed.

    `INTENT` and `COMPLETION` are the two halves of one paired write, sharing one
    identity. `STORE_WRITE_FAILURE` takes the completion's place when the store
    write failed after its intent landed — it is what stops Phase 4 replaying an
    intent into content nobody published.

    `GAP` is requirement 4 case (c): a write with no pairable store write whose
    emit failed. It is a CLOSED TYPED FIELD SET and never free text — see
    `gap_event` for why that is a security property and not a style rule.

    `REDACTION_PLACEHOLDER` is requirement 10's: capture-time filtering removed
    bytes before they reached the journal root, and the record stays complete
    about the FACT of the removal rather than being silently shorter.
    """

    INTENT = "intent"
    COMPLETION = "completion"
    STORE_WRITE_FAILURE = "store_write_failure"
    GAP = "gap"
    REDACTION_PLACEHOLDER = "redaction_placeholder"


class Provenance(str, Enum):
    """What kind of thing this content is BY ORIGIN — requirement 7(d).

    Three trust classes enter the journal and without a field every downstream
    reader sees one undifferentiated stream. **Phase 8's poller is the consumer
    that makes this sharp** — it reads a row and *starts work*, so the field it
    filters on has to exist on the event and survive Phase 4's rebuild.

    `FETCHED` is the one that carries the actual risk: bytes from the internet
    arrive via tool results in the transcript and wholesale via Phase 2's content
    store, and a poller that cannot tell them from fleet-authored prose is a
    poller that can be instructed by a web page.

    A field absent from version-1 events is absent forever, which is why this
    lands here rather than at the phase that first needs it.
    """

    FLEET_AUTHORED = "fleet_authored"
    OPERATOR_AUTHORED = "operator_authored"
    FETCHED = "fetched"


class GapClass(str, Enum):
    """Why a gap happened, as a closed set — never an exception message.

    THE CLOSED SET IS THE SECURITY PROPERTY. A gap event reports that content was
    lost; if its `why` were derived from the content or from an exception string,
    the report would become a side channel for exactly the bytes it exists to say
    were dropped — and a gap event is written on the failure path, which is the
    least-reviewed path there is. Five classes, a byte count and a timestamp cost
    a few hundred bytes and cannot leak.
    """

    DISK_FULL = "disk_full"
    READ_ONLY = "read_only"
    PATH_GONE = "path_gone"
    WRITE_FAILED = "write_failed"
    # PHASE 10 ADDS THE FIFTH, AND IT IS A CLASS OF *READ* FAILURE. The four
    # above say why an APPEND did not land; the post-exit harvest can fail one
    # step earlier, when the GitHub surface it was sent to read could not be
    # read at all — a 404 on a PR that was never opened, a timed-out `gh`, a
    # reply that is not JSON. Phase 10 r5: *"a failed harvest appends a typed
    # gap event NAMING THE SURFACE it could not read"* — the surface is the
    # event's `destination`, this is the why, and the closed set still holds:
    # no message, no URL fragment the run did not already know, no bytes.
    SURFACE_UNREADABLE = "surface_unreadable"


@dataclass(frozen=True)
class Destination:
    """WHERE the content went. Requirement 2 — a field, never a format.

    `store` names the surface (`github`, `tracked_issues`, `git`, `filesystem`);
    `address` is what identifies the object within it, and it is EMPTY ON AN
    INTENT by construction. A GitHub comment has no id or URL until after it is
    created, and requirement 8 forbids changing a written event — which is the
    third reason a paired write needs two events rather than one.
    """

    store: str
    address: str = ""


@dataclass(frozen=True)
class Lineage:
    """Which input item produced this output item — requirement 5.

    n8n's `pairedItem`, which records which output came from which input by
    index. **A decision was made in session that this did not transfer, and it
    was reversed against the evidence:** the argument was that our children run
    in sequence, and the 2026-08-12 verify round dispatched two critics 21
    seconds apart. Fan-out is real today, so *"which output came from which
    input"* is a question about our own runs that we currently cannot answer.

    `input_ref` is the identity of the producing event (or the opaque id of a
    non-event input such as a task file); `input_index` is its position in the
    fan-out, which is what makes a round traceable output-to-input rather than
    merely output-to-parent. Both are optional because a run's FIRST emit has no
    producing input, and a required field nobody can fill is the self-inflicted
    absence `exit_record.CHILD_SCHEMA` already documents.
    """

    input_ref: str | None = None
    input_index: int | None = None


def event_identity(*, run_id: str, write_path: str, sequence: int) -> str:
    """The deterministic identity every event carries — requirement 7(a).

    AGAINST AN AT-LEAST-ONCE EXECUTION MODEL. Temporal executes an activity at
    least once, which is why Temporal Standard §7.1 requires every activity to be
    idempotent — a retried activity re-runs its side effects. An append-only
    journal fed by retried activities accumulates duplicate events, and Phase 4's
    replay then rebuilds a store with duplicated rows, or worse passes under a
    normalisation that hides them.

    DERIVED FROM `(run_id, write_path, sequence)` AND NOTHING ELSE — deliberately
    NOT from the content. A content hash would give two identical comments posted
    to two different PRs the same identity, and would give one comment re-authored
    with a typo fix a different one; neither is the question. The question is
    *which write of which run is this*, and the retry that this defends against
    re-runs the same write of the same run, so it re-derives the same identity.

    `sequence` IS PER `(run_id, write_path)`, NOT GLOBAL. A global counter would
    need a single writer across a fan-out — precisely what `Bag.writer_dir`
    exists to avoid — and would make two concurrent children's identities depend
    on which one got there first, so a retry of either would mint a new identity
    rather than re-deriving its own.

    ⚠ WHAT THIS DOES NOT ESTABLISH, AND THE CONSEQUENCE IS WORSE THAN "UNORDERED".
    This paragraph used to say only that two children each emitting `seq=1` are
    unordered relative to each other. They are — and they also derive the SAME
    `event_id`, because the material is `(run_id, write_path, sequence)` and a
    writer contributes nothing to it. `dedupe_on_identity` keys on
    `(event_id, kind)` and keeps the FIRST, so on replay the second writer's
    distinct, successfully-written completion is DROPPED: not an ambiguity about
    order, real data loss, and precisely the silent gap cases (b) and (c) exist to
    forbid. The counter is per-`Emitter` (`Emitter._sequences`), and
    `Bag.writer_dir` gives each writer its own `events.jsonl` — so within one
    writer this cannot happen and across two it is unguarded.

    IT IS UNREACHABLE TODAY AND NOTHING ENFORCES THAT, which is also stated rather
    than left implied. It needs two concurrent writers in ONE run emitting on the
    SAME `write_path`; today parallel children are read-only critics and a single
    analyst writes, so no second writer performs a store write at all. That is a
    property of the current wiring, not an invariant this module holds.
    **Trigger: the second concurrent writer that performs a store write.** The
    remedy is a sequence number that spans writers — or a writer key in the
    identity material — and it is a schema question, so it is named here rather
    than reached for now.
    """
    if sequence < 0:
        raise EventError(
            f"sequence must be non-negative, got {sequence}. A negative "
            f"sequence would let two writes of one path derive one identity, "
            f"which is the duplicate this field exists to make impossible.")
    material = f"{run_id}\x00{write_path}\x00{sequence}".encode()
    return hashlib.sha256(material).hexdigest()[:32]


@dataclass(frozen=True)
class JournalEvent:
    """One entry in the journal. Appended, never changed.

    THE FOUR ADMISSION FIELDS ARE ONE DECISION, NOT FOUR (requirement 7):
    `event_id` (identity, against at-least-once execution), `edge_id`
    (authority — self-reported today, and stated as such), `key_epoch`
    (credential epoch, so compromise has a boundary) and `provenance` (trust
    class by origin). They land together in version-1 events because a field
    absent from version-1 events is absent forever.

    ⚠ `key_epoch` IS THE ONE ADMISSION FIELD WITH NO CONSUMER TODAY, and it is
    stated the way Phase 1 r7's classification slot is rather than left to look
    like an oversight. Its consumer is *a replay scoped to exclude an epoch*,
    which nothing needs until a credential is known to have leaked.
    **Trigger: the first credential revocation.** It lands now anyway because an
    epoch that starts being recorded on the day of a leak cannot bound the events
    written before it. Phase 6 r3's producer/consumer table records this as a
    knowingly-empty cell WITH its trigger, not as a blank one.

    `content` IS VERBATIM AND `content_bytes` IS ITS LENGTH AS WRITTEN. The two
    are separate because a redaction placeholder replaces `content` and must
    still report how much was dropped — a record that got shorter with no number
    beside it is the silent gap this component exists to prevent.
    """

    kind: EventKind
    event_id: str
    run_id: str
    edge_id: str
    key_epoch: str
    provenance: Provenance
    write_path: str
    sequence: int
    destination: Destination
    content: str = ""
    content_bytes: int = 0
    lineage: Lineage = field(default_factory=Lineage)
    outcome: Outcome | None = None
    terminal_state: TerminalState | None = None
    recorded_at: str = field(default_factory=utc_now)
    schema_version: int = JOURNAL_SCHEMA_VERSION
    gap_class: GapClass | None = None

    def __post_init__(self) -> None:
        """Admission, at construction, so an inadmissible event cannot be written.

        THE CHECKS ARE THE CONTRACT'S TEETH. Requirement 7 is *"the event
        admission contract is SPECIFIED"* — and this component's own argument,
        made three times in the phase doc, is that a rule written only as prose
        has not once prevented the thing it forbids. Every one of these is a
        rule the doc states; they are here rather than in a validator because a
        validator runs on a bag that already contains the bad event.
        """
        if not self.run_id:
            raise EventError(
                "an event with no run_id cannot be joined to anything. The "
                "journal is keyed by run id (Phase 1 r2), so this event would "
                "land in a bag and be unreachable from the run that wrote it.")
        if not self.edge_id:
            raise EventError(
                "an event with no edge_id cannot be filtered by origin. "
                "Requirement 6: every event carries a stable edge_id. Absent "
                "from a version-1 event, it is absent forever.")
        if not self.key_epoch:
            raise EventError(
                "an event with no key_epoch cannot be excluded from a replay "
                "scoped past a leaked credential (requirement 7c). Pass "
                "`edge_id.NO_CREDENTIAL_EPOCH` to state that this edge "
                "authenticates to nothing — that is a value, not an absence.")
        if self.content_bytes < 0:
            raise EventError(
                f"content_bytes must be non-negative, got {self.content_bytes}")
        if self.kind is EventKind.INTENT and self.destination.address:
            raise EventError(
                f"an intent event carries no store address, and this one carries "
                f"{self.destination.address!r}. The store object does not exist "
                f"yet — that is the whole reason a paired write needs a second "
                f"event (see the module docstring). An address here means the "
                f"emit ran AFTER its store write, which inverts write-ahead "
                f"ordering and is the state requirement 1's invariant forbids.")
        if self.kind is EventKind.GAP and self.gap_class is None:
            raise EventError(
                "a gap event names why it happened, from `GapClass`. Free text "
                "is refused here rather than sanitised: the gap event reports "
                "that content was lost, and a `why` derived from that content "
                "or from an exception message is a side channel for the very "
                "bytes it says were dropped.")
        if self.kind is not EventKind.GAP and self.gap_class is not None:
            raise EventError(
                f"only a gap event carries a gap_class; this is a "
                f"{self.kind.value}. A non-gap event reporting a gap class would "
                f"be counted by Phase 6 r6's gap accounting as a loss that did "
                f"not happen.")


def encode_event(event: JournalEvent) -> str:
    """One event as one JSON line, ready to append.

    `sort_keys` SO TWO EMITS OF ONE EVENT ARE BYTE-IDENTICAL. Dedupe is on
    identity rather than on bytes, so this is not what makes a retry safe — what
    it makes possible is a human diffing two bags and seeing a difference that is
    a difference. An unordered mapping would put field-ordering noise on every
    line of a Phase 4 rebuild diff.

    `ensure_ascii=False` BECAUSE THE CONTENT IS VERBATIM. Escaping non-ASCII
    would store a different string from the one the run authored, and requirement
    1's word is *verbatim*. The file is declared UTF-8 by the bag's own
    `Tag-File-Character-Encoding`, so there is nothing to escape for.
    """
    payload: dict[str, Any] = asdict(event)
    for key in ("kind", "provenance", "outcome", "terminal_state", "gap_class"):
        value = payload.get(key)
        if isinstance(value, Enum):
            payload[key] = value.value
    return json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))


def decode_event(line: str) -> JournalEvent:
    """One JSON line back into an event, upcasting nothing yet.

    ⚠ THE UPCASTER IS OPEN AND THIS IS NOT IT. Roadmap § *Open inputs* item 2
    carries the mechanism; requirement 8's rule — version every event, never
    mutate a written one, upcast on read — ships now because an unversioned v1
    event is unrecoverable, and the mechanism follows. What this function does
    today is REFUSE a version it has no code for, rather than reading a v2 event
    with v1 field meanings and returning something that looks right.
    """
    raw = json.loads(line)
    version = raw.get("schema_version")
    if version != JOURNAL_SCHEMA_VERSION:
        raise EventError(
            f"event schema version {version!r} is not {JOURNAL_SCHEMA_VERSION}, "
            f"and no upcaster exists yet (roadmap § Open inputs, item 2). "
            f"Refusing rather than reading it with this version's field "
            f"meanings — a v2 event read as v1 is confidently wrong, which is "
            f"worse than unreadable.")
    return JournalEvent(
        kind=EventKind(raw["kind"]),
        event_id=raw["event_id"],
        run_id=raw["run_id"],
        edge_id=raw["edge_id"],
        key_epoch=raw["key_epoch"],
        provenance=Provenance(raw["provenance"]),
        write_path=raw["write_path"],
        sequence=raw["sequence"],
        destination=Destination(**raw["destination"]),
        content=raw.get("content", ""),
        content_bytes=raw.get("content_bytes", 0),
        lineage=Lineage(**raw.get("lineage", {})),
        outcome=Outcome(raw["outcome"]) if raw.get("outcome") else None,
        terminal_state=(TerminalState(raw["terminal_state"])
                        if raw.get("terminal_state") else None),
        recorded_at=raw["recorded_at"],
        schema_version=raw["schema_version"],
        gap_class=GapClass(raw["gap_class"]) if raw.get("gap_class") else None,
    )


def dedupe_on_identity(events: list[JournalEvent]) -> list[JournalEvent]:
    """Replay's dedupe rule — requirement 7(a), and it is what makes a retry safe.

    FIRST OCCURRENCE WINS, KEYED ON `(event_id, kind)`. Not on `event_id` alone:
    an intent and its completion deliberately SHARE one identity — that is what
    makes them one unit — so keying on the id alone would silently drop every
    completion in the journal and turn `applied_intents` below into a function
    that applies nothing.

    FIRST RATHER THAN LAST because the journal is append-only and the first write
    is the one that happened; a later duplicate is a retry re-running a side
    effect, not a correction. Requirement 8 forbids corrections outright.
    """
    seen: set[tuple[str, str]] = set()
    kept: list[JournalEvent] = []
    for event in events:
        key = (event.event_id, event.kind.value)
        if key in seen:
            continue
        seen.add(key)
        kept.append(event)
    return kept


def applied_intents(events: list[JournalEvent]) -> list[JournalEvent]:
    """The intents a replay applies: exactly those that have a completion.

    THIS ONE RULE IS WHAT MAKES TWO OF THE THREE PAIRED-WRITE FAILURES VISIBLE
    RATHER THAN SILENTLY WRONG. Without it, an intent whose store write failed
    replays into content the store never got — Phase 4 would MATERIALISE
    unpublished content into the store, turning a failed write into a delayed
    successful one that no run and no human approved. The rebuild is supposed to
    restore what happened, not complete what did not.

    A `STORE_WRITE_FAILURE` event does NOT satisfy an intent, and the asymmetry
    is the point: it is a positive record that the write did not land, so the
    intent stays unapplied AND a reader can tell "the store write failed" from
    "the run died between the two events". Both are unapplied; only one is a
    defect in this component.

    DEDUPE FIRST, ALWAYS. A retried activity appends both events twice, and
    counting completions without deduping would report two applications of one
    write — the same red diff in the opposite direction from the row above.
    """
    deduped = dedupe_on_identity(events)
    completed = {e.event_id for e in deduped if e.kind is EventKind.COMPLETION}
    return [e for e in deduped
            if e.kind is EventKind.INTENT and e.event_id in completed]


def gap_event(*, run_id: str, edge_id: str, key_epoch: str, write_path: str,
              sequence: int, gap_class: GapClass, lost_bytes: int,
              destination: Destination,
              provenance: Provenance = Provenance.FLEET_AUTHORED) -> JournalEvent:
    """Requirement 4 case (c): the write did not land, and the record says so.

    A CLOSED TYPED FIELD SET — write-path id, byte count, error class, timestamp
    — and never free text derived from the content or from an exception message.
    It costs a few hundred bytes and cannot become a side channel for the very
    bytes it is reporting the loss of.

    THE CALLER MARKS THE BAG `incomplete`; this only builds the record. The two
    are separate because `Bag.mark_incomplete` is idempotent on the flag and
    append-only on the gaps — a run that loses three writes carries three gap
    records and one flag — and folding the flag in here would make the event
    constructor do I/O.
    """
    return JournalEvent(
        kind=EventKind.GAP,
        event_id=event_identity(run_id=run_id, write_path=write_path,
                                sequence=sequence),
        run_id=run_id, edge_id=edge_id, key_epoch=key_epoch,
        provenance=provenance, write_path=write_path, sequence=sequence,
        destination=destination, content="", content_bytes=lost_bytes,
        gap_class=gap_class, terminal_state=TerminalState.EMIT_FAILED)


def redaction_placeholder_event(*, run_id: str, edge_id: str, key_epoch: str,
                                write_path: str, sequence: int,
                                destination: Destination, removed_bytes: int,
                                rule: str,
                                provenance: Provenance) -> JournalEvent:
    """Requirement 10: capture-time filtering fired, and the record says so.

    THE RECORD STAYS COMPLETE ABOUT THE *FACT* OF A REDACTION rather than
    silently shorter. `rule` names WHICH filter matched — not what it matched,
    which would be the secret — so an operator can tell a credential pattern from
    an over-broad rule eating legitimate content without the event carrying
    either.

    DISTINCT FROM PHASE 1's REDACTION EVENT CLASS, which is the after-the-fact
    complement for what gets through. This one fires BEFORE any byte reaches the
    journal root; that one replaces a payload file already sealed into a
    manifest. Conflating them would make a filter working normally look like an
    incident.
    """
    return JournalEvent(
        kind=EventKind.REDACTION_PLACEHOLDER,
        event_id=event_identity(run_id=run_id, write_path=write_path,
                                sequence=sequence),
        run_id=run_id, edge_id=edge_id, key_epoch=key_epoch,
        provenance=provenance, write_path=write_path, sequence=sequence,
        destination=destination, content=f"[FILTERED AT CAPTURE: {rule}]",
        content_bytes=removed_bytes)

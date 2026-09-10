"""The emit boundary — PMP Phase 3 requirements 1, 4, 10, 11, 12.

DRIVEN AGAINST REAL BAGS ON A REAL FILESYSTEM, never against a mocked writer.
The phase's whole argument for answering *what happens when the write fails* is
that the answer decides whether Phase 4's guarantee means anything — and a mocked
`open()` proves the code branches, not that the bag ends up in the state the
branch claims. Every failure below is induced by making the filesystem refuse:
a read-only directory, a path that is not there, a file where a directory should
be. The assertion is always on the BAG AFTERWARDS.

⚠ AND THE FAILURES ARE INDUCED BY MODE, WHICH DOES NOT BIND ROOT. `test_journal_
bag.py` already skips its mode assertions under root for this reason; the two
here that need a refusing filesystem carry the same skip rather than passing
vacuously on a CI image that runs as uid 0.

WHAT THIS FILE DOES NOT ASSERT: the contract itself. `test_journal_events.py`
owns admission, identity and the two replay rules, and keeping them apart is what
stops a contract written wrongly and exercised wrongly from agreeing with itself.
"""

from __future__ import annotations

import ast
import json
import os
import pathlib
from pathlib import Path
from unittest import mock

import pytest

from modules.journal import emit as emitmod
from modules.journal.bag import LABEL_GAP, open_bag, read_tag_file
from modules.journal.edge_id import NO_CREDENTIAL_EPOCH
from modules.journal.emit import (EmitFailed, Emitter, JournalUnwritable,
                                  StoreWriteFailed, current_emitter,
                                  emitting_into, gap_class_for,
                                  unwritable_journal_in_text,
                                  unwritable_journal_report)
from modules.journal.events import (EVENTS_FILE, Destination, EventKind,
                                    GapClass, Provenance, decode_event)
from modules.assistant.review_pr import exit_record
from modules.vocabulary import TerminalState

ROOT_SKIP = pytest.mark.skipif(
    os.geteuid() == 0,
    reason="a mode-induced write refusal does not bind uid 0, so this would "
           "assert nothing rather than assert something weaker")


@pytest.fixture()
def bag(tmp_path: Path):
    root = tmp_path / "journal"
    # `open_bag` stages the bag in a hidden sibling directory and renames it into
    # place (Phase 9 r7), so the ROOT has to exist first. In the fleet
    # `resolve_journal_root` creates it; here nothing has, and the failure it
    # produces — a `FileNotFoundError` out of `tempfile` — points at the staging
    # code rather than at the missing root.
    root.mkdir(mode=0o700, parents=True)
    return open_bag(root, "run-1")


@pytest.fixture()
def emitter(bag) -> Emitter:
    return Emitter.for_run(bag, writer=None, journal_root=bag.path.parent)


def _events(emitter: Emitter) -> list:
    if not emitter.events_path.is_file():
        return []
    return [decode_event(line) for line
            in emitter.events_path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _make_unwritable(emitter: Emitter) -> None:
    """Make every append fail, the way a full disk or a lost mount does.

    THE DIRECTORY IS SEALED, NOT THE FILE. Removing the file would be caught by
    `O_CREAT` and the append would succeed; a `0500` directory refuses the
    creation itself, which is the shape `ENOSPC`/`EROFS` present at this call.
    """
    emitter.writer_dir.chmod(0o500)


# --- the boundary itself ----------------------------------------------------

def test_a_parent_emits_at_the_payload_ROOT_and_a_member_in_its_own_subfolder(
        bag) -> None:
    """Phase 9 ruled that an invocation which IS the run takes no writer subfolder.

    Its records are the run's, not one member's. There is no contention either
    way: a parent writes `data/events.jsonl` and each member writes
    `data/<writer>/events.jsonl`, so no two writers share a file — the property
    `writer_dir` exists for.
    """
    parent = Emitter.for_run(bag, writer=None, journal_root=bag.path.parent)
    member = Emitter.for_run(bag, writer="critic", journal_root=bag.path.parent)
    assert parent.events_path == bag.payload_dir / EVENTS_FILE
    assert member.events_path == bag.payload_dir / "critic" / EVENTS_FILE


def test_an_edge_id_is_minted_once_and_reused(bag) -> None:
    first = Emitter.for_run(bag, writer=None, journal_root=bag.path.parent)
    second = Emitter.for_run(bag, writer="w", journal_root=bag.path.parent)
    assert first.edge_id == second.edge_id
    assert first.edge_id.startswith("edge-")
    assert first.key_epoch == NO_CREDENTIAL_EPOCH


# --- requirement 4 case (b): the paired write -------------------------------

def test_a_paired_write_emits_the_INTENT_BEFORE_the_store_write(
        emitter: Emitter) -> None:
    """Write-ahead ordering, asserted by observing the journal FROM the store write.

    ⚠ THIS IS THE ASSERTION THAT ACTUALLY CHECKS ORDER. Reading the file
    afterwards and finding two events in order proves the WRITE order, not the
    ordering relative to the side effect — the intent could have been written
    after `perform` returned and still land first in the file. Asking the
    question from INSIDE `perform` is the only place the distinction is visible.
    """
    seen: list[str] = []

    def _perform() -> str:
        seen.extend(e.kind.value for e in _events(emitter))
        return "https://example/1"

    emitter.paired_write(write_path="gh:pr:comment",
                         destination=Destination(store="github"),
                         content="the body", perform=_perform,
                         address_of=lambda url: url)
    assert seen == ["intent"], (
        "the store write ran before its intent was on disk, so a journal failure "
        "would leave the store holding content the record does not")


def test_a_completed_pair_shares_ONE_identity_and_carries_the_address(
        emitter: Emitter) -> None:
    emitter.paired_write(write_path="gh:pr:comment",
                         destination=Destination(store="github"),
                         content="the body", perform=lambda: "https://example/1",
                         address_of=lambda url: url)
    intent, done = _events(emitter)
    assert intent.event_id == done.event_id, "a pair is ONE unit with two events"
    assert intent.destination.address == ""
    assert done.destination.address == "https://example/1"
    assert done.terminal_state is TerminalState.COMPLETED


def test_the_content_is_carried_VERBATIM(emitter: Emitter) -> None:
    """Requirement 1's word. A summary here is the whole component failing quietly."""
    body = "## Decision Log\n\n- **[High]** kept the phase whole — em dash —\n"
    emitter.paired_write(write_path="gh:pr:comment",
                         destination=Destination(store="github"),
                         content=body, perform=lambda: "u")
    assert _events(emitter)[0].content == body


@ROOT_SKIP
def test_a_FAILED_INTENT_means_the_store_write_does_NOT_happen(
        emitter: Emitter) -> None:
    """Case (b), and the invariant holds because BOTH sides are absent.

    This is the ordering's whole payoff: *if any store gets it, the journal gets
    it*. A journal failure means neither happened, so the record is SHORT rather
    than WRONG — and short is recoverable while wrong is not.
    """
    performed: list[int] = []
    _make_unwritable(emitter)
    with pytest.raises(EmitFailed, match="store write was NOT performed"):
        emitter.paired_write(write_path="gh:pr:comment",
                             destination=Destination(store="github"),
                             content="body",
                             perform=lambda: performed.append(1))
    assert performed == [], "the store write ran after its intent failed"


def test_a_FAILED_STORE_WRITE_records_a_failure_event_and_re_raises(
        emitter: Emitter) -> None:
    """The intent landed and the store write did not — a POSITIVE record exists.

    Without it Phase 4's replay materialises unpublished content into the store,
    turning a failed write into a delayed successful one that no run and no human
    approved.
    """
    def _boom() -> None:
        raise RuntimeError("gh exited 1")

    with pytest.raises(StoreWriteFailed, match="replay will not apply"):
        emitter.paired_write(write_path="gh:pr:comment",
                             destination=Destination(store="github"),
                             content="body", perform=_boom)
    kinds = [e.kind for e in _events(emitter)]
    assert kinds == [EventKind.INTENT, EventKind.STORE_WRITE_FAILURE]


def test_a_RAISING_address_of_is_a_GAP_and_not_an_untyped_CRASH(
        emitter: Emitter, bag) -> None:
    """`address_of` is CALLER-SUPPLIED, so it is inside the guard like the intent.

    IT PARSES A STORE REPLY, which is the one input at this boundary the fleet
    does not author — `gh_attempt` reads `stdout.splitlines()[-1]`, and the
    obvious next write path parses JSON. Evaluated above the `try` (as it was),
    an `IndexError` or a `JSONDecodeError` escaped `paired_write` bare: no
    `EmitFailed`, no gap event, no `incomplete` flag, and — since neither is a
    `RuntimeError` — past every entrypoint's handler as well. AFTER the store
    write had landed and was therefore unrecoverable.

    THE EXCEPTION CHOSEN HERE IS DELIBERATELY NOT A `RuntimeError`. A
    `RuntimeError` would be caught by the entrypoints even on the broken code, so
    it would not discriminate; `IndexError` is what an empty `gh` stdout actually
    raises, and it is the shape that escaped everything.
    """
    def _address(_result: None) -> str:
        raise IndexError("gh printed nothing, so stdout.splitlines()[-1] blew up")

    with pytest.raises(EmitFailed, match="store write DID land"):
        emitter.paired_write(write_path="gh:pr:comment",
                             destination=Destination(store="github"),
                             content="body", perform=lambda: None,
                             address_of=_address)
    kinds = [e.kind for e in _events(emitter)]
    assert kinds == [EventKind.INTENT, EventKind.GAP], (
        f"a raising `address_of` produced {kinds}; the record must carry the "
        f"intent and a typed gap, so replay sees an intent with no completion "
        f"and declines to apply a write it cannot prove")
    assert bag.incomplete, (
        "the bag reads as complete after a write whose completion was lost — "
        "the outcome Phase 1's four-state design exists to prevent")


def test_a_RETRIED_paired_write_appends_a_deduplicable_pair_per_attempt(
        emitter: Emitter) -> None:
    """An activity executes AT LEAST ONCE, so the journal must survive a retry.

    ⚠ THE APPEND IS NOT SUPPRESSED — the journal is append-only, so a retry
    genuinely writes again. What makes it safe is that both attempts derive the
    SAME identity, so `dedupe_on_identity` collapses them on read. Suppressing
    the append would require the emitter to remember what it wrote, which is
    state a retried process does not have.
    """
    from modules.journal.events import applied_intents

    for _ in range(2):
        retried = Emitter(bag=emitter.bag, writer_dir=emitter.writer_dir,
                          run_id=emitter.run_id, edge_id=emitter.edge_id)
        retried.paired_write(write_path="gh:pr:comment",
                             destination=Destination(store="github"),
                             content="body", perform=lambda: "u",
                             address_of=lambda u: u)

    assert len(_events(emitter)) == 4, "an append-only journal appends"
    assert len(applied_intents(_events(emitter))) == 1, (
        "replay applied the retried write twice — the duplicate-row failure "
        "dedupe-on-identity exists to prevent")


# --- requirement 4 case (c): the unpairable write ---------------------------

def test_an_unpairable_write_emits_a_COMPLETION_with_no_prior_intent(
        emitter: Emitter) -> None:
    """The content already exists, so there is nothing to withhold.

    This is also the shape Phase 10's post-exit harvest emits for a model-issued
    write — a completion with no intent is a legitimate typed shape rather than
    a hole, and the docs must not imply otherwise.
    """
    emitter.unpairable_write(write_path="transcript",
                             destination=Destination(store="filesystem"),
                             content="tool calls")
    assert [e.kind for e in _events(emitter)] == [EventKind.COMPLETION]


@ROOT_SKIP
def test_a_FAILED_unpairable_write_marks_the_bag_incomplete_and_continues(
        emitter: Emitter, bag) -> None:
    """Case (c): the failure is RECORDED rather than prevented, and the run goes on.

    Everything downstream then treats the bag as a known-gap input rather than a
    clean one — Phase 4 reports it with a count and its denominator, Phase 6 says
    so in its report, and Phase 7 ships the marking with the bag.
    """
    _make_unwritable(emitter)
    emitter.unpairable_write(write_path="run-facts",
                             destination=Destination(store="filesystem"),
                             content="x" * 100)
    assert bag.incomplete, "a gap that leaves the bag reading clean is a SILENT gap"
    gaps = [v for label, v in read_tag_file(bag.info_path) if label == LABEL_GAP]
    assert len(gaps) == 1 and "run-facts" in gaps[0]


@ROOT_SKIP
def test_the_TRANSCRIPT_arm_STOPS_the_run_where_an_ordinary_gap_does_not(
        emitter: Emitter, bag) -> None:
    """The one member of case (c) that is not merely a completeness problem.

    The transcript is the fleet's only record of what commands ran, this fleet
    runs with permissions bypassed, and a run can itself create the disk-full
    condition that drops it. Losing it while the run proceeds to completion is
    evidence loss wearing a routine defect's clothes.
    """
    _make_unwritable(emitter)
    with pytest.raises(EmitFailed, match="stops the run"):
        emitter.unpairable_write(write_path="transcript",
                                 destination=Destination(store="filesystem"),
                                 content="tool calls", stop_on_failure=True)
    assert bag.incomplete, "stopping must not cost the gap record"


@pytest.mark.parametrize("errno_name,expected", [
    ("ENOSPC", GapClass.DISK_FULL),
    ("EROFS", GapClass.READ_ONLY),
    ("ENOENT", GapClass.PATH_GONE),
    ("EIO", GapClass.WRITE_FAILED),
])
def test_an_OSError_becomes_a_CLOSED_class_and_never_its_message(
        errno_name: str, expected: GapClass) -> None:
    """The message is discarded on purpose.

    A `why` carrying `strerror` or `filename` would put the failing path — and on
    some filesystems a fragment of what was being written — into the record that
    exists to say those bytes were dropped. The operator still gets the message,
    on stderr and in the raised exception; what is bounded is what reaches the
    DURABLE record Phase 7 syncs and Phase 4 replays.
    """
    import errno as errno_mod
    assert gap_class_for(OSError(getattr(errno_mod, errno_name), "x")) is expected


# --- requirement 4 case (d): the bootstrap case -----------------------------

@ROOT_SKIP
def test_case_d_raises_when_even_the_GAP_RECORD_cannot_be_written(
        emitter: Emitter, bag) -> None:
    """The case that makes (c) circular if it is not answered.

    Both the gap event and the `incomplete` flag fail, so the journal cannot
    record that the journal failed — and the report has to leave on channels that
    are not the journal.
    """
    # ⚠ THE TAG FILE IS SEALED AT THE FILE, NOT THE DIRECTORY, AND THAT
    # CORRECTION IS THE FINDING. A `0500` directory refuses CREATION and nothing
    # else: `bag-info.txt` already exists, so `_append_tag_line`'s
    # `O_WRONLY|O_APPEND` on it still succeeds and the `incomplete` flag lands —
    # which is why the first version of this test asserted case (d) and observed
    # case (c). A read-only mount refuses the write itself, which is `0400` here.
    _make_unwritable(emitter)
    bag.info_path.chmod(0o400)
    try:
        with pytest.raises(JournalUnwritable, match="cannot be written and neither"):
            emitter.unpairable_write(write_path="run-facts",
                                     destination=Destination(store="filesystem"),
                                     content="x")
    finally:
        bag.info_path.chmod(0o600)


# --- what escaped the taxonomy entirely, until it was probed for -------------

#: A credential shape `capture_filter` matches, so `_build` appends a redaction
#: placeholder BEFORE the event it was called to construct. That second append is
#: the one the failure taxonomy did not cover.
_FILTERED_SHAPE = "ghp_" + "A" * 24


@ROOT_SKIP
def test_a_FILTERED_paired_write_on_a_dead_journal_still_raises_EmitFailed(
        emitter: Emitter, bag) -> None:
    """⚠ THE PLACEHOLDER APPEND USED TO ESCAPE EVERY ONE OF THE FOUR CASES.

    `_build` appends a redaction placeholder of its own whenever the filter
    fires, and it was called ABOVE the `try` that catches a failed append. On a
    read-only mount a filtered write therefore raised a bare `PermissionError`
    straight out of `paired_write`: no `EmitFailed`, no gap, no `incomplete`
    flag — and past every entrypoint's `except RuntimeError`, because `OSError`
    is not one.

    ⚠ THE CONTROL IS THE PAIR, NOT THIS ASSERTION ALONE.
    `test_a_FAILED_INTENT_means_the_store_write_does_NOT_happen` above drives the
    identical call with content the filter ignores and gets `EmitFailed`. The
    only difference between the two is whether the placeholder was appended, so
    the pair is what localises the escape to it.
    """
    performed = []
    _make_unwritable(emitter)
    with pytest.raises(EmitFailed):
        emitter.paired_write(write_path="gh:pr:comment",
                             destination=Destination(store="github"),
                             content=f"token {_FILTERED_SHAPE} leaked",
                             perform=lambda: performed.append(1))
    assert performed == [], (
        "the store write ran even though the journal refused the intent — the "
        "invariant is that a journal failure means NEITHER side happened")


@ROOT_SKIP
def test_a_FILTERED_unpairable_write_on_a_dead_journal_still_MARKS_THE_BAG(
        emitter: Emitter, bag) -> None:
    """The same escape on the case with no store write to withhold, where it costs more.

    Here the placeholder's `OSError` did not merely skip a typed exception: it
    skipped `_record_gap`, so the content was lost AND nothing recorded the loss.
    A bag that lost data and reads as complete is the outcome the four-state
    design exists to prevent, reached through the function that exists to
    prevent it.
    """
    _make_unwritable(emitter)
    emitter.unpairable_write(write_path="transcript",
                             destination=Destination(store="filesystem"),
                             content=f"a transcript holding {_FILTERED_SHAPE}")
    assert bag.incomplete, (
        "a filtered write that could not land left the bag reading as complete")
    gaps = [v for label, v in read_tag_file(bag.info_path) if label == LABEL_GAP]
    assert len(gaps) == 1 and "transcript" in gaps[0]


def test_CONTENT_that_cannot_be_ENCODED_fails_as_EmitFailed_not_as_a_crash(
        emitter: Emitter) -> None:
    """`UnicodeEncodeError` is a `ValueError`, so it joined no `except OSError`.

    A lone surrogate — which reaches this fleet from `surrogateescape`-decoded
    filenames and from tool output — raised out of `paired_write` untyped,
    exactly as the placeholder append did, and for the same reason: the failure
    set was written as "the disk" when it is "the disk OR the bytes".
    `edge_id.read_edge_id` already names the same trap from the decode side.

    THE STORE WRITE IS WITHHELD, which is the correct answer rather than an
    incidental one: the journal cannot record this write, so it does not happen.
    """
    performed = []
    with pytest.raises(EmitFailed):
        emitter.paired_write(write_path="gh:pr:comment",
                             destination=Destination(store="github"),
                             content="a lone surrogate \ud800 in the body",
                             perform=lambda: performed.append(1))
    assert performed == []


@ROOT_SKIP
def test_a_failed_FLAG_is_case_d_even_when_the_gap_event_LANDED(
        emitter: Emitter, bag) -> None:
    """⚠ THE ONE HOLE IN *a gap may exist; a silent gap may not*.

    `_record_gap` raised `JournalUnwritable` only when BOTH writes failed. With
    the gap event landing and the flag failing, it returned normally and told
    nobody — and nothing downstream reads a writer's `events.jsonl` to decide
    whether a bag is clean. Phase 4, Phase 6 and Phase 7 all branch on the flag,
    so that bag lost data and read as complete.

    ⚠ THE FIXTURE HAS TO FAIL ONE WRITE AND NOT THE OTHER, which a mode cannot
    do — both events go to one file. So the CONTENT is what fails: a lone
    surrogate cannot be encoded, while the gap event that reports it carries no
    content at all and lands normally. `bag-info.txt` is read-only at the FILE,
    because a `0500` directory refuses creation and `events.jsonl` already
    exists — the correction this file's case-(d) test already records.
    """
    bag.info_path.chmod(0o400)
    try:
        with pytest.raises(JournalUnwritable, match="the gap event landed"):
            emitter.unpairable_write(write_path="run-facts",
                                     destination=Destination(store="filesystem"),
                                     content="run facts with \ud800 in them")
    finally:
        bag.info_path.chmod(0o600)
    kinds = [e.kind for e in _events(emitter)]
    assert EventKind.GAP in kinds, (
        "the fixture did not reach the case it names — the gap event has to "
        "LAND for this to be the event-landed/flag-failed arm")


@ROOT_SKIP
def test_a_store_failure_whose_record_ALSO_dies_names_the_unwritable_journal(
        emitter: Emitter, bag) -> None:
    """The third place a failed `incomplete` flag was swallowed with no signal.

    The store write fails, its `store_write_failure` event cannot be written,
    and the flag cannot either — so nothing in the journal says this write is
    missing. `StoreWriteFailed` is still what the caller needs, because its
    handlers are written against the store failure; what changed is that the
    journal's death now leaves on that message, LEADING with the one declared
    marker so `unwritable_journal_in_text` reads it on the process channel.

    The message also used to assert *"a store-write-failure event was
    recorded"* unconditionally — on the path where recording it had just failed.
    """
    def _die() -> None:
        # AT THE FILE, NOT THE DIRECTORY: the intent has already created
        # `events.jsonl`, so a `0500` directory would refuse nothing and the
        # failure event would land. Same correction the case-(d) test above
        # carries, and the same trap.
        emitter.events_path.chmod(0o400)
        bag.info_path.chmod(0o400)
        raise RuntimeError("the store refused it")

    try:
        with pytest.raises(StoreWriteFailed) as caught:
            emitter.paired_write(write_path="gh:pr:comment",
                                 destination=Destination(store="github"),
                                 content="a comment", perform=_die)
    finally:
        emitter.events_path.chmod(0o600)
        bag.info_path.chmod(0o600)
    assert unwritable_journal_in_text(str(caught.value)), (
        "the journal died while recording a store-write failure and no channel "
        "said so — this is the exception's only surface")


def test_the_case_d_PAYLOAD_is_ONE_shape_for_every_channel() -> None:
    """One payload builder, so no two channels can disagree about what happened.

    ⚠ THIS TEST USED TO BE NAMED `test_case_d_reports_on_the_exit_record_AND_a_
    durable_surface`, AND THE NAME WAS FALSE — neither of those channels has a
    producer. A green test asserting a channel is wired is the strongest possible
    form of the drift `CASE_D_CHANNELS` was declared to stop, because a test name
    reads as proof rather than as prose. What this actually holds is the payload's
    SHAPE; which channels carry it is
    `test_the_case_d_CHANNEL_TABLE_matches_the_tree` below.
    """
    report = unwritable_journal_report(JournalUnwritable("root is gone"),
                                       bag_path=Path("/j/run-1"))
    assert report["terminal_state"] == TerminalState.JOURNAL_UNWRITABLE.value
    assert report["bag"] == "/j/run-1"
    assert report["marker"] == emitmod.UNWRITABLE_JOURNAL_MARKER


def test_the_case_d_signal_HAS_a_committed_reader() -> None:
    """Requirement 11, and it is the one thing this phase must not get wrong.

    Adding a field to a channel and leaving the reading to somebody later is how
    this fleet has already lost three observables, and the one channel this
    component's failure path depends on is the last place to repeat it.

    THE READER IS CHANNEL-BLIND, WHICH IS WHY IT SHIPS AHEAD OF TWO OF THE THREE.
    It is a substring test against the one declared marker, so it reads the
    process output that IS wired today and a pull-request comment on the day that
    channel acquires a producer. A comment body is used here as the input BECAUSE
    the durable channel is the unbuilt one — the reader is ready and the writer is
    not, which is the correct half of that pair to ship first.
    """
    report = unwritable_journal_report(JournalUnwritable("root is gone"))
    comment = f"### Run failed\n\n{report['marker']}: {report['detail']}\n"
    assert unwritable_journal_in_text(comment)
    assert not unwritable_journal_in_text(
        "### Run failed\n\nthe worktree was dirty\n"), (
        "the reader answers true for ordinary prose, so it reports every run as "
        "having an unwritable journal")


@ROOT_SKIP
def test_the_RAISED_case_d_exception_is_readable_by_the_same_reader(
        emitter: Emitter, bag) -> None:
    """The THIRD channel — the process's own exit — carries the same marker.

    `JournalUnwritable` subclasses `RuntimeError`, so every entrypoint's existing
    `except RuntimeError: return refuse(exc)` prints this message and exits
    non-zero. Leading with the declared marker means the reader that greps a PR
    comment reads the process output too, with no entrypoint edited and no second
    literal. Without it the exit channel would carry a failure nothing could
    recognise — a signal with no reader, on the one path this component's failure
    reporting depends on.
    """
    _make_unwritable(emitter)
    bag.info_path.chmod(0o400)
    try:
        with pytest.raises(JournalUnwritable) as raised:
            emitter.unpairable_write(write_path="run-facts",
                                     destination=Destination(store="filesystem"),
                                     content="x")
    finally:
        bag.info_path.chmod(0o600)
    assert unwritable_journal_in_text(str(raised.value))


def _passes_case_d_report_true(tree: ast.AST) -> bool:
    """Does this module CALL something with `case_d_report=True`?

    Asked of the AST and not of the text, for the reason every guard in this
    package learned the hard way: a docstring explaining the flag mentions its
    name, and a substring scan reads the explanation as the wiring.
    """
    return any(
        isinstance(node, ast.Call)
        and any(kw.arg == "case_d_report"
                and isinstance(kw.value, ast.Constant) and kw.value.value is True
                for kw in node.keywords)
        for node in ast.walk(tree))


def _derive_case_d_wiring() -> tuple[bool, ...]:
    """Which of `CASE_D_CHANNELS` has a live producer — READ FROM THE TREE.

    One derivation per row, in the table's order. Each answers *is there a
    producer*, never *is there a plan*, because the whole defect this replaces was
    prose describing the plan in the present tense.
    """
    fleet = pathlib.Path(__file__).resolve().parents[2]

    # (0) THE PROCESS EXIT — wired by INHERITANCE and by nothing else. Every
    # entrypoint already carries `except RuntimeError`, so a `JournalUnwritable`
    # that subclasses it reaches the operator with no entrypoint edited. Break
    # that inheritance and the channel is gone, silently, which is why the
    # derivation is the inheritance rather than a count of handlers.
    process_exit = issubclass(JournalUnwritable, RuntimeError)

    # (1) THE DURABLE WORKING-RECORD COMMENT — its producer is the `case_d_report`
    # bypass, so the channel is live exactly when some PRODUCTION file calls it.
    # Tests are excluded deliberately: a test exercising the bypass proves the
    # mechanism works, not that anything reports through it.
    durable = any(
        _passes_case_d_report_true(ast.parse(path.read_text(encoding="utf-8",
                                                            errors="replace")))
        for path in sorted(fleet.rglob("*.py"))
        if "tests" not in path.parts)

    # (2) THE TYPED EXIT RECORD — live when its schema declares somewhere for the
    # terminal state to go. Asked of `CHILD_SCHEMA` itself, which
    # `exit-protocol.md` §2 makes the single declaration of that record's shape.
    exit_record_field = TerminalState.JOURNAL_UNWRITABLE.value in json.dumps(
        exit_record.CHILD_SCHEMA)

    return (process_exit, durable, exit_record_field)


def test_the_case_d_CHANNEL_TABLE_matches_the_tree() -> None:
    """`CASE_D_CHANNELS` says which channels carry case (d). THE TREE DECIDES.

    THIS TEST EXISTS BECAUSE THE PROSE VERSION DRIFTED AT SEVEN SITES ON ONE
    BRANCH — `emit.py`'s module docstring twice, `_record_gap`'s docstring, its
    raised message, `unwritable_journal_report`'s docstring, `journal/__init__.py`
    and a TEST NAME — every one of them asserting that case (d) reports on the
    typed exit record and on a durable working-record surface. Neither had a
    producer. The channel that did — the process exit — was named by none of them,
    so on the single failure path where this component cannot speak for itself the
    operator was sent to two empty surfaces and away from the full one.

    Correcting seven paragraphs does not converge; the eighth gets written next
    pass. So the claim became DATA with a derivation behind it, and this is that
    derivation. The day somebody gives `case_d_report=True` a production caller or
    adds the field to `CHILD_SCHEMA`, this goes red against the table — and the
    message `case_d_channel_sentence` composes changes with it, because that
    sentence reads the same table.
    """
    declared = tuple(wired for _, wired in emitmod.CASE_D_CHANNELS)
    derived = _derive_case_d_wiring()
    assert declared == derived, (
        f"`CASE_D_CHANNELS` declares {declared} and the tree says {derived}. A "
        f"channel that gained a producer must be flipped to True here — and the "
        f"prose citing this table re-read — because the case-(d) message names "
        f"exactly the rows this table calls wired."
    )


def test_the_case_d_SENTENCE_agrees_with_the_table_it_reads() -> None:
    """The table test above never reads the SENTENCE, and that was the gap.

    `case_d_channel_sentence` composed the channel NAMES from `CASE_D_CHANNELS`
    and then spelled the COUNT by hand — *"both are declared … NEITHER has a
    producer … appear on them"*. Driven with a one-dead-channel table that is
    three false plurals about a single channel, and
    `test_the_case_d_CHANNEL_TABLE_matches_the_tree` stays green throughout,
    because it compares the table against the tree.

    THAT IS NOT A FUTURE PROBLEM. The table flips the day somebody wires the
    durable line or adds the `CHILD_SCHEMA` field — which is what the deriver
    above exists to force — and the operator-facing message on the one path where
    this component cannot speak for itself would start asserting an unbuilt fact
    in the present tense.

    Driven at every cardinality the table can hold, because the defect was
    invisible at the ONE cardinality the tree happens to have today.
    """
    def sentence_for(table):
        with mock.patch.object(emitmod, "CASE_D_CHANNELS", table):
            return emitmod.case_d_channel_sentence()

    one_dead = sentence_for((('A', True), ('B', False)))
    assert "both are" not in one_dead and "NEITHER" not in one_dead, (
        f"a one-dead-channel table produced a plural: {one_dead!r}")
    assert "appear on them" not in one_dead, (
        f"a one-dead-channel table produced a plural pronoun: {one_dead!r}")
    assert "has NO producer yet" in one_dead, (
        f"the negation did not survive the singular: {one_dead!r}")

    two_dead = sentence_for((('A', True), ('B', False), ('C', False)))
    assert "both are declared" in two_dead and "NEITHER has a producer" in two_dead

    three_dead = sentence_for((('A', False), ('B', False), ('C', False)))
    assert "all 3 are declared" in three_dead and "NONE has a producer" in three_dead

    none_dead = sentence_for((('A', True), ('B', True)))
    assert "NOT on" not in none_dead, (
        f"a fully-wired table still names dead channels: {none_dead!r}")


def test_the_channel_DERIVATION_discriminates() -> None:
    """A deriver that answered True to everything would agree with any table.

    Both directions on the one row that is decided by a code shape rather than by
    a class relationship: a call carrying the flag is seen, and a docstring
    MENTIONING it is not — which is the substring bug this package has already met
    twice, once in the journal-isolation guard and once in `gh_attempt` itself,
    where reading the flag off the content skipped the journal entirely.
    """
    assert _passes_case_d_report_true(ast.parse(
        "gh_attempt(['gh', 'pr', 'comment'], root, case_d_report=True)"))
    assert not _passes_case_d_report_true(ast.parse(
        '''def f():\n    """Pass `case_d_report=True` to bypass the emit."""\n'''))
    assert not _passes_case_d_report_true(ast.parse(
        "gh_attempt(['gh', 'pr', 'view'], root, case_d_report=False)"))


def test_the_marker_is_ONE_declaration_shared_by_producer_and_reader() -> None:
    """A producer and a consumer that each spell the marker are two declarations.

    That is the defect `exit-protocol.md` §6 exists to forbid, and the one this
    fleet already committed at `as_prose_verdict`. Mutating the constant must
    break neither side — which is only true if neither side re-types it.
    """
    import ast
    import pathlib
    source = (pathlib.Path(__file__).resolve().parents[2] / "modules" /
              "journal" / "emit.py").read_text(encoding="utf-8")
    literals = [n.value for n in ast.walk(ast.parse(source))
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
                and n.value == emitmod.UNWRITABLE_JOURNAL_MARKER]
    assert len(literals) == 1, (
        f"the marker literal appears {len(literals)} times in emit.py; the "
        f"reader must reference the constant rather than respell it")


# --- requirement 10: capture-time filtering ---------------------------------

def test_a_secret_is_FILTERED_before_any_byte_reaches_the_root(
        emitter: Emitter) -> None:
    """AT APPEND, not at seal. Capture is the only cheap point in the lifecycle.

    After Phase 4 wires the rebuild test to a gate, removing a payload file is a
    gate change; after Phase 7 it is a bucket-wide purge. And filtering at SEAL
    would change written events, which requirement 8 forbids outright.
    """
    secret = "ghp_" + "A" * 36
    emitter.paired_write(write_path="gh:pr:comment",
                         destination=Destination(store="github"),
                         content=f"token is {secret}", perform=lambda: "u")
    on_disk = emitter.events_path.read_text(encoding="utf-8")
    assert secret not in on_disk, "the secret reached the journal root"
    assert "[FILTERED:github-token]" in on_disk


def test_the_filter_emits_a_PLACEHOLDER_so_the_record_is_not_silently_shorter(
        emitter: Emitter) -> None:
    """The record stays complete about the FACT of the removal."""
    emitter.paired_write(write_path="gh:pr:comment",
                         destination=Destination(store="github"),
                         content="token " + "ghp_" + "A" * 36,
                         perform=lambda: "u")
    placeholders = [e for e in _events(emitter)
                    if e.kind is EventKind.REDACTION_PLACEHOLDER]
    assert len(placeholders) == 1
    assert placeholders[0].content_bytes == 40, "the byte count is what was removed"
    assert "github-token" in placeholders[0].content
    assert "ghp_" not in placeholders[0].content, (
        "the placeholder names the RULE and never the match")


# --- requirement 12: the boundary is registered, not remembered -------------

def test_no_registered_emitter_is_a_REAL_state_and_not_an_error() -> None:
    """A unit test, a helper script and `validate_bag` all run outside a run.

    Manufacturing an emitter for them would write a bag for a process that is not
    a run, under a `run_id` nobody minted.
    """
    assert current_emitter() is None


def test_emitting_into_RESTORES_the_previous_boundary(emitter: Emitter) -> None:
    """A nested block must not detach every later write path in the process."""
    assert current_emitter() is None
    with emitting_into(emitter):
        assert current_emitter() is emitter
        with emitting_into(None):
            assert current_emitter() is None
        assert current_emitter() is emitter, (
            "the inner block cleared the outer run's boundary, so every write "
            "after it would silently stop emitting")
    assert current_emitter() is None


def test_the_provenance_class_survives_onto_the_event(emitter: Emitter) -> None:
    """Requirement 7(d). Phase 8's poller reads a row and STARTS WORK.

    So the field it filters on has to exist on the event and survive Phase 4's
    rebuild — and a field absent from version-1 events is absent forever.
    """
    emitter.unpairable_write(write_path="fetched-page",
                             destination=Destination(store="content_store"),
                             content="<html>", provenance=Provenance.FETCHED)
    assert _events(emitter)[0].provenance is Provenance.FETCHED


def test_every_event_a_run_emits_carries_the_run_and_the_edge(
        emitter: Emitter) -> None:
    emitter.paired_write(write_path="gh:pr:comment",
                         destination=Destination(store="github"),
                         content="body", perform=lambda: "u")
    for event in _events(emitter):
        assert event.run_id == "run-1"
        assert event.edge_id == emitter.edge_id
        assert event.key_epoch == NO_CREDENTIAL_EPOCH


def test_no_event_carries_a_key_or_a_key_derived_value(emitter: Emitter) -> None:
    """Requirement 6's constraint, which rides on the buildable half deliberately.

    The `edge_id` is an identifier and appears in every event; the key is a
    secret and appears in none. `hash(api_key)` is ruled out twice over — it
    changes on rotation, and a stored hash of a live credential is an offline
    confirmation oracle.
    """
    import re
    emitter.paired_write(write_path="gh:pr:comment",
                         destination=Destination(store="github"),
                         content="body", perform=lambda: "u")
    for event in _events(emitter):
        assert not re.fullmatch(r"[0-9a-f]{32}|[0-9a-f]{40}|[0-9a-f]{64}",
                                event.edge_id), (
            "the edge id has the shape of a bare digest, which is what a "
            "key-derived id looks like")
        assert event.key_epoch == NO_CREDENTIAL_EPOCH

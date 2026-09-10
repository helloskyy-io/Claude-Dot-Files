"""The journal event contract — PMP Phase 3 requirements 2, 3, 5, 7, 8.

WHAT THIS FILE ASSERTS AND WHAT IT DELIBERATELY DOES NOT. It owns the CONTRACT:
what an event is, what makes it admissible, and the two replay rules. It owns no
I/O — `test_journal_emit.py` drives the write-failure cases against real bags,
and keeping them apart is what stops a contract written wrongly and exercised
wrongly from agreeing with itself.

THE ADMISSION CHECKS ARE ASSERTED AS REFUSALS, NEVER AS DOCUMENTATION. Every one
of them is a rule the phase doc states in prose, and this component's own thesis
— stated three times in that doc — is that a rule written only as prose has not
once prevented the thing it forbids. A test that constructed an admissible event
and checked its fields would leave every refusal untested while looking thorough.
"""

from __future__ import annotations

import json

import pytest

from modules.journal.bag import JOURNAL_SCHEMA_VERSION
from modules.journal.events import (Destination, EventError, EventKind,
                                    GapClass, JournalEvent, Lineage,
                                    Provenance, applied_intents, decode_event,
                                    dedupe_on_identity, encode_event,
                                    event_identity, gap_event,
                                    redaction_placeholder_event)
from modules.vocabulary import Disposition, HoldKind, Outcome, TerminalState

EDGE = "edge-test"
EPOCH = "none"


def _admissible(**overrides) -> JournalEvent:
    """A minimal admissible event. Every test varies ONE thing from this.

    NOT NAMED `_event`, DELIBERATELY. `test_prose_NAMES_a_symbol_that_RESOLVES.py`
    carries a `_DECLARED` row saying `_event` is a DICT KEY in
    `replay_run_resources.py` and never an identifier — and a helper by that name
    makes the symbol real, so prose about the dict key would resolve to this
    function and mean something else. Caught by that guard; renamed rather than
    deleting the exemption, because the exemption is still true.
    """
    fields = dict(
        kind=EventKind.INTENT,
        event_id=event_identity(run_id="r", write_path="w", sequence=0),
        run_id="r", edge_id=EDGE, key_epoch=EPOCH,
        provenance=Provenance.FLEET_AUTHORED,
        write_path="w", sequence=0,
        destination=Destination(store="github"),
        content="body", content_bytes=4)
    fields.update(overrides)
    return JournalEvent(**fields)


# --- requirement 7: admission ----------------------------------------------

@pytest.mark.parametrize("field,value,expected", [
    ("run_id", "", "run_id"),
    ("edge_id", "", "edge_id"),
    ("key_epoch", "", "key_epoch"),
    ("content_bytes", -1, "content_bytes"),
])
def test_an_event_missing_an_admission_field_is_REFUSED_at_construction(
        field: str, value, expected: str) -> None:
    """Requirement 7's four fields are checked where an event is BUILT.

    NOT IN A VALIDATOR, and the difference is the whole point: a validator runs
    over a bag that already contains the inadmissible event, and requirement 8
    forbids changing a written one. By then the only remedy is a redaction.
    """
    with pytest.raises(EventError, match=expected):
        _admissible(**{field: value})


def test_an_INTENT_carrying_a_store_address_is_REFUSED() -> None:
    """An address on an intent means the emit ran AFTER its store write.

    That inverts write-ahead ordering, which is what makes requirement 1's
    invariant self-enforcing — order the intent first and a journal failure
    means NEITHER side happened. This refusal is what stops a caller building
    the inverted shape by hand.
    """
    with pytest.raises(EventError, match="intent event carries no store address"):
        _admissible(destination=Destination(store="github", address="https://x/1"))


def test_a_COMPLETION_carries_the_store_assigned_address() -> None:
    """The third thing one event per write cannot carry.

    A GitHub comment has no id or URL until after it is created, and requirement
    8 forbids changing the written intent — so the address lands here or nowhere.
    """
    done = _admissible(kind=EventKind.COMPLETION,
                  destination=Destination(store="github", address="https://x/1"))
    assert done.destination.address == "https://x/1"


def test_a_gap_event_with_no_gap_class_is_REFUSED() -> None:
    """A gap names why it happened, from a CLOSED set.

    Free text is refused rather than sanitised because a gap event reports that
    content was LOST — a `why` derived from that content or from an exception
    message would be a side channel for the very bytes it says were dropped, on
    the least-reviewed path there is.
    """
    with pytest.raises(EventError, match="gap event names why"):
        _admissible(kind=EventKind.GAP)


def test_a_NON_gap_event_carrying_a_gap_class_is_REFUSED() -> None:
    """The other direction, and it is not symmetry for its own sake.

    Phase 6 r6 counts gaps by reading gap events. A completion carrying a
    `gap_class` would be counted as a loss that did not happen, which is worse
    than an uncounted one: the measurement would report the component failing
    where it worked.
    """
    with pytest.raises(EventError, match="only a gap event carries a gap_class"):
        _admissible(kind=EventKind.COMPLETION, gap_class=GapClass.DISK_FULL)


# --- requirement 7(a): identity --------------------------------------------

def test_identity_is_DETERMINISTIC_over_run_write_path_and_sequence() -> None:
    """A retried activity re-derives the SAME identity, which is what dedupe needs.

    Temporal executes an activity at least once (Temporal Standard §7.1), so the
    retry re-runs the same write of the same run — and therefore re-derives this.
    """
    first = event_identity(run_id="r", write_path="gh:pr:comment", sequence=3)
    again = event_identity(run_id="r", write_path="gh:pr:comment", sequence=3)
    assert first == again


@pytest.mark.parametrize("kwargs", [
    {"run_id": "other", "write_path": "gh:pr:comment", "sequence": 3},
    {"run_id": "r", "write_path": "gh:pr:create", "sequence": 3},
    {"run_id": "r", "write_path": "gh:pr:comment", "sequence": 4},
])
def test_identity_DISCRIMINATES_on_each_of_its_three_inputs(kwargs) -> None:
    """Each input alone changes the identity.

    Without this the deterministic test above passes for a constant, which is
    the vacuity that would make dedupe collapse every event in a bag to one.
    """
    base = event_identity(run_id="r", write_path="gh:pr:comment", sequence=3)
    assert event_identity(**kwargs) != base


def test_identity_is_NOT_derived_from_the_content() -> None:
    """The question is *which write of which run*, not *what did it say*.

    A content hash would give two identical comments posted to two different PRs
    one identity, and would give one comment re-authored with a typo fix a
    different one. Neither is the question dedupe asks.
    """
    one = _admissible(content="a")
    two = _admissible(content="b")
    assert one.event_id == two.event_id


def test_a_negative_sequence_is_REFUSED() -> None:
    with pytest.raises(EventError, match="non-negative"):
        event_identity(run_id="r", write_path="w", sequence=-1)


# --- the two replay rules ---------------------------------------------------

def test_dedupe_keeps_the_FIRST_of_two_identical_appends() -> None:
    """A retried activity appends twice; replay applies it once.

    FIRST rather than last because the journal is append-only and the first
    write is the one that happened — a later duplicate is a retry re-running a
    side effect, not a correction. Requirement 8 forbids corrections outright.
    """
    first = _admissible(content="original")
    duplicate = _admissible(content="original")
    assert [e.content for e in dedupe_on_identity([first, duplicate])] == ["original"]


def test_dedupe_keys_on_KIND_TOO_so_a_pair_survives_it() -> None:
    """An intent and its completion SHARE one identity — that is what makes them one unit.

    ⚠ THIS IS THE ONE THAT WOULD SILENTLY DESTROY THE CONTRACT. Keyed on
    `event_id` alone, dedupe drops every completion in the journal and
    `applied_intents` then applies nothing — a replay that rebuilds an empty
    store while every assertion about dedupe still passes.
    """
    intent = _admissible(kind=EventKind.INTENT)
    done = _admissible(kind=EventKind.COMPLETION,
                  destination=Destination(store="github", address="u"))
    assert len(dedupe_on_identity([intent, done])) == 2


def test_replay_applies_an_intent_ONLY_when_a_completion_exists() -> None:
    """The rule that makes a failed store write visible rather than silently wrong.

    Without it, an intent whose store write failed replays into content the store
    never got — Phase 4 would MATERIALISE unpublished content that no run and no
    human approved. The rebuild restores what happened; it does not complete what
    did not.
    """
    applied = _admissible(write_path="a")
    applied_done = _admissible(write_path="a", kind=EventKind.COMPLETION,
                          destination=Destination(store="github", address="u"))
    orphan = _admissible(write_path="b",
                    event_id=event_identity(run_id="r", write_path="b", sequence=0))
    kept = applied_intents([applied, applied_done, orphan])
    assert [e.write_path for e in kept] == ["a"]


def test_a_store_write_FAILURE_does_not_satisfy_its_intent() -> None:
    """The asymmetry is the diagnosis, not an oversight.

    A `store_write_failure` is a POSITIVE record that the write did not land, so
    the intent stays unapplied AND a reader can tell it apart from a run that
    died between the two events. Both are unapplied; only one is a defect in this
    component.
    """
    intent = _admissible()
    failure = _admissible(kind=EventKind.STORE_WRITE_FAILURE,
                     terminal_state=TerminalState.STORE_WRITE_FAILED)
    assert applied_intents([intent, failure]) == []


def test_a_retried_PAIR_is_applied_ONCE_not_twice() -> None:
    """Dedupe and the completion rule composed, which is the real replay path.

    Counting completions without deduping first reports two applications of one
    write — the same red diff as the row above, in the opposite direction.
    """
    intent, done = _admissible(), _admissible(kind=EventKind.COMPLETION,
                                    destination=Destination(store="github",
                                                            address="u"))
    assert len(applied_intents([intent, done, intent, done])) == 1


# --- requirement 8: versioning ---------------------------------------------

def test_every_event_carries_the_schema_version() -> None:
    assert _admissible().schema_version == JOURNAL_SCHEMA_VERSION
    assert json.loads(encode_event(_admissible()))["schema_version"] == \
        JOURNAL_SCHEMA_VERSION


def test_an_event_of_an_UNKNOWN_version_is_REFUSED_rather_than_read() -> None:
    """No upcaster exists yet, so a v2 event is refused, not read as v1.

    A v2 event read with v1 field meanings is CONFIDENTLY WRONG, which is worse
    than unreadable — and the roadmap carries the upcaster mechanism as an open
    input rather than as something this phase closes.
    """
    raw = json.loads(encode_event(_admissible()))
    raw["schema_version"] = JOURNAL_SCHEMA_VERSION + 1
    with pytest.raises(EventError, match="no upcaster exists"):
        decode_event(json.dumps(raw))


def test_an_event_round_trips_through_json_unchanged() -> None:
    """Requirement 1's word is VERBATIM, so the round trip is the assertion."""
    original = _admissible(kind=EventKind.COMPLETION,
                      destination=Destination(store="sqlite", address="row/7"),
                      content="…em dash, ünïcode, and a \"quote\"",
                      lineage=Lineage(input_ref="src-1", input_index=2),
                      outcome=Outcome.HOLD,
                      terminal_state=TerminalState.COMPLETED)
    assert decode_event(encode_event(original)) == original


def test_the_encoding_does_NOT_escape_non_ascii() -> None:
    """Escaping would store a different string from the one the run authored."""
    assert "ünïcode" in encode_event(_admissible(content="ünïcode"))


# --- requirement 2: the destination is a field, not a format ----------------

@pytest.mark.parametrize("store", ["github", "git", "sqlite", "mqtt",
                                   "tracked_issues", "planning_corpus"])
def test_the_event_SHAPE_is_identical_whatever_the_destination(store: str) -> None:
    """Requirement 2, asserted as the key set rather than as a sentence.

    That property is not stylistic: it is what makes the record portable across
    edges, and it is what Phase 7 depends on — a second edge of any type sources
    the same data from the protocol rather than from a repo.
    """
    baseline = set(json.loads(encode_event(_admissible())))
    other = set(json.loads(encode_event(
        _admissible(destination=Destination(store=store)))))
    assert other == baseline


# --- requirement 5: lineage -------------------------------------------------

def test_lineage_records_WHICH_INPUT_produced_this_output() -> None:
    """n8n's `pairedItem`. Fan-out is real today — two critics 21 seconds apart."""
    fanned = _admissible(lineage=Lineage(input_ref="finding-3", input_index=2))
    assert json.loads(encode_event(fanned))["lineage"] == {
        "input_ref": "finding-3", "input_index": 2}


def test_lineage_is_OPTIONAL_because_a_runs_FIRST_emit_has_no_input() -> None:
    """A required field nobody can fill is a self-inflicted absence.

    `exit_record.CHILD_SCHEMA` documents that class from measurement: an
    over-constrained required field produces SILENCE rather than an error.
    """
    assert _admissible().lineage == Lineage(None, None)


# --- the two typed constructors --------------------------------------------

def test_a_gap_event_carries_a_CLOSED_class_and_a_byte_count_and_no_content() -> None:
    """What was lost, when, why and how much — and never what."""
    gap = gap_event(run_id="r", edge_id=EDGE, key_epoch=EPOCH,
                    write_path="transcript", sequence=1,
                    gap_class=GapClass.DISK_FULL, lost_bytes=4096,
                    destination=Destination(store="filesystem"))
    assert gap.gap_class is GapClass.DISK_FULL
    assert gap.content_bytes == 4096
    assert gap.content == "", (
        "a gap event carrying content would be the side channel for the very "
        "bytes it reports as lost")


def test_a_redaction_placeholder_names_the_RULE_and_never_the_match() -> None:
    """An operator can tell a credential pattern from an over-broad rule.

    Neither the placeholder nor its event ever carries the matched text, which
    is the secret. `removed_bytes` is what makes the record complete about the
    FACT of the removal rather than silently shorter.
    """
    placeholder = redaction_placeholder_event(
        run_id="r", edge_id=EDGE, key_epoch=EPOCH, write_path="w", sequence=1,
        destination=Destination(store="github"), removed_bytes=40,
        rule="github-token", provenance=Provenance.FLEET_AUTHORED)
    assert placeholder.content == "[FILTERED AT CAPTURE: github-token]"
    assert placeholder.content_bytes == 40


# --- requirement 3: one vocabulary, two contracts ---------------------------

def test_the_shared_vocabulary_is_ONE_declaration_not_two() -> None:
    """The exit record's `Outcome` and the journal's are the SAME OBJECT.

    ⚠ IDENTITY, NOT EQUALITY OF VALUES. Two enums spelled identically compare
    unequal member-to-member in Python, so a rebuild diffing a journal event's
    outcome against an exit record's would report a difference that is not one —
    which is exactly the drift requirement 3 exists to prevent, and it would be
    invisible to a test that only compared `.value`.
    """
    from modules.assistant.review_pr import exit_record as er
    assert er.Outcome is Outcome
    assert er.HoldKind is HoldKind


def test_the_exit_records_disposition_enum_is_DERIVED_from_the_declaration() -> None:
    """The schema's enum is read off `vocabulary.Disposition`, never re-typed.

    Three consumers spell this vocabulary — the schema, the `pr_review:` block,
    and `convergence.py`'s open/closed partition — and a journal event replaying
    a finding row is a fourth. `memory-model.md` §4.1 records the partition, and
    a row spelled differently from it is a row the partition silently drops.
    """
    from modules.assistant.review_pr import exit_record as er
    declared = sorted(m.value for m in Disposition)
    in_schema = er.CHILD_SCHEMA["properties"]["findings"]["items"][
        "properties"]["disposition"]["enum"]
    assert sorted(in_schema) == declared


def test_the_journal_package_does_not_import_the_exit_record() -> None:
    """The vocabulary is a LEAF both sides import; the edge runs neither way.

    `modules/journal/` importing `modules.assistant` would drag `temporalio` in
    behind it and break Phase 6's reader; `exit_record.py` importing the journal
    package would execute its whole `__init__` from a module that is
    dependency-free by design. A leaf at `modules/` is the only placement that
    leaves both properties intact, and this is what holds it.
    """
    import ast
    import pathlib
    source = (pathlib.Path(__file__).resolve().parents[2] / "modules" /
              "journal" / "events.py").read_text(encoding="utf-8")

    # ⚠ ASKED OF THE IMPORT STATEMENTS, NEVER OF THE FILE'S TEXT. A substring
    # check flags the DOCSTRING — this module explains, in prose, why the exit
    # record's contract cannot be extended, and naming the thing it is separate
    # from is the explanation. Measured: the substring form of this assertion
    # went red on a correct file, which is the assertion's population including
    # the text that makes the claim about it.
    imported: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            imported.append(f"{'.' * node.level}{node.module or ''}")
    assert imported, "no imports parsed — this check would pass vacuously"
    assert not [m for m in imported if "assistant" in m or "exit_record" in m], (
        f"`modules/journal/` must import no workflow module; found {imported}")
    assert "..vocabulary" in imported, (
        "the shared vocabulary must be IMPORTED rather than respelled — this "
        "assertion is what stops the test above passing because both sides "
        f"happen to agree today. Imports: {imported}")

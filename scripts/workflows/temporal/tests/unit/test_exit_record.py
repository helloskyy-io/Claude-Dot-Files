"""The typed exit record: its schema, its fail-safe contract, and the shadow.

`docs/standards/exit-protocol.md` §4 requires each of the four absence
conditions — absence, unparseability, staleness, unknown `schema_version` — to
route explicitly and to have ITS OWN TEST. This module is that requirement,
plus the two rules that sit outside it (the safety rule R1 and the residual
arm R9) and the shadow comparison that Phase 3 runs both channels for.

EVERY GUARD HERE CARRIES A NEGATIVE CONTROL, per §6 (*a guard ships with a
demonstration that it fails when the property is violated*) and the Testing
Standard's mutation-evidence rule. The shape that matters: a contract test that
cannot fail is worse than no test, because it manufactures confidence. Where a
test asserts something routes to the human arm, a sibling asserts the SAME
input shape with the defect removed routes somewhere else — otherwise a router
that returned `undetermined` unconditionally would pass every case below.

THE STALE CASE IS WRITTEN DELIBERATELY. A first-invocation-only test passes
despite it: with one invocation there is no prior record to be stale, so the
comparison is trivially satisfied and the rule is never exercised.
"""

from __future__ import annotations

import ast
import json
import re
import pathlib
from pathlib import Path

import pytest

from modules.assistant.review_pr import exit_record as er
from modules.assistant import routing
from modules.assistant.review_pr import review_pr_helper as helper

# The shared fakes, moved out of this file so `test_convergence.py` stops
# importing another TEST module for them. Names unchanged, so no call site
# below moved — see `review_run_fakes` for why the coupling was a defect.
from review_run_fakes import (  # noqa: E402

    EXPECTED_REF, REPO_SLUG, RUN_ID, _FakeWorkflow, _nonce_in, _no_sleep, _record,
    _with_comments,
)

# ANCHORED ON THIS FILE, NOT ON A MODULE. These were computed as
# `Path(er.__file__).parents[N]`, which silently shifts by one the moment the
# module moves — and `exit_record` moved into `review_pr/` on 2026-08-11,
# offsetting five paths at once. A test file's own location is stable by
# construction: `tests/unit/<file>.py` is where these live and where they stay.
_TEMPORAL = pathlib.Path(__file__).resolve().parents[2]      # …/temporal
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[5]     # the repository
_ASSISTANT = _TEMPORAL / "modules" / "assistant"
_MODULES = _TEMPORAL / "modules"


def _envelope(record: dict | None = ..., denials: list | None = None) -> dict:
    """A CLI `result` event. `record=None` omits the key entirely.

    Sentinel default rather than None, because "no structured_output key" is
    the state under test in one of these and must be expressible.
    """
    event = {"type": "result", "subtype": "success", "is_error": False,
             "permission_denials": denials if denials is not None else []}
    if record is not ...:
        if record is not None:
            event["structured_output"] = record
    else:
        event["structured_output"] = _record()
    return event


# ---------------------------------------------------------------------------
# The four absence conditions, one test each, plus the valid case they are
# measured against.
# ---------------------------------------------------------------------------

def test_a_valid_record_routes_as_the_record_says() -> None:
    """The control every case below is a mutation of.

    Without this, a router that returned `undetermined` unconditionally would
    satisfy every other test in this file.
    """
    routed = er.route(_envelope(), expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    assert routed.routed_outcome is er.RoutedOutcome.MERGE
    assert routed.undetermined_reason is None
    assert routed.outcome is er.Outcome.MERGE
    assert helper.verdict_from_record(routed) is routing.Verdict.MERGE


def test_a_hold_routes_on_its_sub_kind_not_on_hold_alone() -> None:
    """B6/P3/P5 branch on the sub-kind; `hold` alone does not route."""
    for kind, expected in (("redispatch", routing.Verdict.HOLD_REDISPATCH),
                           ("needs_ruling", routing.Verdict.HOLD_NEEDS_ASSISTANCE)):
        routed = er.route(
            _envelope(_record(outcome="hold", hold_kind=kind)),
            expected_run_id=RUN_ID, expected_ref=EXPECTED_REF,
        )
        assert routed.routed_outcome is er.RoutedOutcome.HOLD
        assert routed.hold_kind is er.HoldKind(kind)
        assert helper.verdict_from_record(routed) is expected


@pytest.mark.parametrize(
    "outcome,hold_kind,expected_route,expected_reason",
    [
        ("merge", None, er.RoutedOutcome.MERGE, None),
        ("merge", "redispatch", er.RoutedOutcome.UNDETERMINED,
         er.UndeterminedReason.UNMATCHED),
        ("merge", "needs_ruling", er.RoutedOutcome.UNDETERMINED,
         er.UndeterminedReason.UNMATCHED),
        ("hold", None, er.RoutedOutcome.UNDETERMINED, er.UndeterminedReason.UNMATCHED),
        ("hold", "redispatch", er.RoutedOutcome.HOLD, None),
        ("hold", "needs_ruling", er.RoutedOutcome.HOLD, None),
    ],
)
def test_every_outcome_by_hold_kind_cell_routes_deliberately(
    outcome, hold_kind, expected_route, expected_reason,
) -> None:
    """R6-R9 over the WHOLE product, not the three cells the prose reasoned about.

    `CHILD_SCHEMA` deliberately does not bind `hold_kind` to `outcome` — an
    `if/then` would be a required-field constraint the child can fail to satisfy,
    and E2(c) measured that as silence on a clean run. The schema being relaxed
    on purpose is exactly why the ROUTER owns the whole conditional, and why the
    cells have to be enumerated rather than argued about.

    `merge` + a `hold_kind` is the cell that shipped wrong: it validated, passed
    R1-R5 and routed MERGE, so a record whose own author said a human must decide
    was auto-merged — with the prose shadow agreeing, because `merge` renders
    `MERGE`. It belongs to R9, which `exit-protocol.md` §4 says exists precisely
    because R6-R8 do not exhaust this product.
    """
    record = _record(outcome=outcome)
    if hold_kind is not None:
        record["hold_kind"] = hold_kind
    assert er._validate(record, er.CHILD_SCHEMA, "structured_output") is None, (
        "the cell must be REACHABLE — a record the schema rejects would be "
        "caught at R3 and would prove nothing about R6-R9"
    )
    routed = er.route(_envelope(record), expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    assert routed.routed_outcome is expected_route
    assert routed.undetermined_reason is expected_reason


def test_record_absent_routes_to_the_human_arm() -> None:
    """R2 — and the run it fires on did not necessarily die."""
    routed = er.route(_envelope(record=None), expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    assert routed.routed_outcome is er.RoutedOutcome.UNDETERMINED
    assert routed.undetermined_reason is er.UndeterminedReason.RECORD_ABSENT


def test_record_absent_fires_on_a_clean_success_run() -> None:
    """The measured case Phase 1 E2 found, asserted as its own state.

    A run where the model declines to call the `StructuredOutput` tool exits 0
    with `subtype: success`, `is_error: false` and a populated `.result`. Every
    signal the fleet reads says clean. R2 must fire on it ANYWAY — a contract
    reading "absent record implies the run died" would be wrong exactly here.
    """
    clean = {"type": "result", "subtype": "success", "is_error": False,
             "result": "I can't call the tool with that value — could you clarify?",
             "permission_denials": []}
    routed = er.route(clean, expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    assert routed.undetermined_reason is er.UndeterminedReason.RECORD_ABSENT


@pytest.mark.parametrize("mutation", [
    pytest.param({"outcome": "BANANA"}, id="value-outside-the-closed-vocabulary"),
    pytest.param({"findings": "not-a-list"}, id="wrong-type"),
    pytest.param({"completion_ref": {"substrate": "github"}}, id="missing-required-subfield"),
    pytest.param({"surprise": "field"}, id="additional-property"),
])
def test_record_unparseable_routes_to_the_human_arm(mutation: dict) -> None:
    """R3 — four separate ways to fail validation, each routed the same.

    Parametrised rather than written once because the validator walks
    CHILD_SCHEMA and each keyword it implements is a separate branch: one
    passing case would leave three unexercised.
    """
    routed = er.route(_envelope(_record(**mutation)), expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    assert routed.routed_outcome is er.RoutedOutcome.UNDETERMINED
    assert routed.undetermined_reason is er.UndeterminedReason.RECORD_UNPARSEABLE


def test_a_missing_required_top_level_field_is_unparseable() -> None:
    record = _record()
    del record["run_id"]
    routed = er.route(_envelope(record), expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    assert routed.undetermined_reason is er.UndeterminedReason.RECORD_UNPARSEABLE


def test_record_stale_routes_to_the_human_arm() -> None:
    """R5 — a WELL-FORMED record from a different invocation.

    This is the case a first-invocation-only test passes despite: the record
    validates, its version is supported, and every field is present. Only the
    identity comparison distinguishes it, and only because the parent issued the
    nonce rather than reading one out of the record.
    """
    routed = er.route(_envelope(_record(run_id="a-previous-invocation")),
                      expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    assert routed.routed_outcome is er.RoutedOutcome.UNDETERMINED
    assert routed.undetermined_reason is er.UndeterminedReason.RECORD_STALE


def test_unknown_schema_version_routes_to_the_human_arm() -> None:
    """R4 — parses cleanly, means something else."""
    routed = er.route(_envelope(_record(schema_version="99")), expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    assert routed.routed_outcome is er.RoutedOutcome.UNDETERMINED
    assert routed.undetermined_reason is er.UndeterminedReason.SCHEMA_VERSION_UNKNOWN


def test_an_unknown_version_is_ruled_before_identity() -> None:
    """R4 sits before R5, and the ordering is asserted rather than assumed.

    A record with BOTH defects must report the version, because a record whose
    version is unknown has no guaranteed typing and its `run_id` is not yet a
    value one may compare. Swap the two rules and this goes red.
    """
    routed = er.route(_envelope(_record(schema_version="99", run_id="other")),
                      expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    assert routed.undetermined_reason is er.UndeterminedReason.SCHEMA_VERSION_UNKNOWN


# ---------------------------------------------------------------------------
# R1 (safety) and R9 (the residual arm).
# ---------------------------------------------------------------------------

def test_a_permission_denial_routes_to_the_human_arm_and_never_to_redispatch() -> None:
    """R1, first in the order so nothing can reach past it.

    The record here says `merge`. It is not consulted: auto-redispatching a
    child that just tripped the fleet's only in-run safety control would be an
    unbounded retry loop against the one control there is, and merging on its
    word is worse.
    """
    denial = {"tool_name": "Bash", "tool_use_id": "toolu_01CsEb",
              "tool_input": {"command": "sudo ls /root"}}
    routed = er.route(_envelope(denials=[denial]), expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    assert routed.routed_outcome is er.RoutedOutcome.UNDETERMINED
    assert routed.undetermined_reason is er.UndeterminedReason.PERMISSION_DENIED


def test_a_denial_is_ruled_before_an_absent_record() -> None:
    """R1 sits ahead of R2, and only a two-condition input proves the ORDER.

    Both existing denial tests carry a valid record, so a router with R1 second
    would pass them. Safety dominates routing: a child that tripped the control
    is never redispatched, whatever else is true of its output.
    """
    envelope = _envelope(record=None, denials=[{"tool_name": "Bash",
                                                "tool_use_id": "toolu_01CsEb"}])
    routed = er.route(envelope, expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    assert routed.undetermined_reason is er.UndeterminedReason.PERMISSION_DENIED


def test_an_absent_denials_key_is_not_read_as_an_empty_list() -> None:
    """The contract must be total over its OWN inputs, not just over the record.

    "I could not check whether the safety control fired" gets the same ROUTING
    as "it fired" and a DIFFERENT REASON — see the sibling test below for why
    the difference is the instrument rather than a nicety.
    """
    envelope = _envelope()
    del envelope["permission_denials"]
    routed = er.route(envelope, expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    assert routed.routed_outcome is er.RoutedOutcome.UNDETERMINED
    assert routed.undetermined_reason is er.UndeterminedReason.DENIALS_UNREADABLE


def test_a_denials_key_that_is_not_a_list_is_unreadable_rather_than_a_denial() -> None:
    """Total one level up from the entries: the key's own TYPE can be wrong.

    A CLI that changed `permission_denials` from a list to an object or a count
    lands here. It is the unreadable case, not the fired case — the parent could
    not check, and saying it fired would be an assertion about a control that
    was never read.
    """
    routed = er.route(_envelope(denials={"count": 0}), expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    assert routed.routed_outcome is er.RoutedOutcome.UNDETERMINED
    assert routed.undetermined_reason is er.UndeterminedReason.DENIALS_UNREADABLE


def test_R1s_two_branches_report_DIFFERENT_reasons() -> None:
    """The reason is the payload, and this asserts the field they disagree ON.

    THE PREVIOUS VERSION OF THIS GUARD ASSERTED ONLY THE ARM, so it was green
    under both the correct and the conflated implementation — the identical
    shape that let `route(None)` report `permission_denied` one rule below.

    Consequence if these ever share a bin: the computed abstention arm's rate is
    `undetermined` GROUPED BY reason, so a CLI that renames or drops
    `permission_denials` bins 100% of runs as `permission_denied`. An operator
    reads a fleet-wide safety-control trip where nothing fired, and Phase 4's
    per-reason rate has no way to separate "the control asserted" from "the
    parent could not check."
    """
    unreadable = _envelope()
    del unreadable["permission_denials"]
    fired = _envelope(denials=[{"tool_name": "Bash", "tool_use_id": "toolu_01CsEb"}])

    a = er.route(unreadable, expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    b = er.route(fired, expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)

    assert a.routed_outcome is b.routed_outcome is er.RoutedOutcome.UNDETERMINED, (
        "the SPLIT MUST NOT MOVE THE ROUTING — safety still dominates, and both "
        "arms are still the human"
    )
    assert a.undetermined_reason is not b.undetermined_reason, (
        "the two R1 conditions share a bin again — the computed arm cannot "
        "separate a safety trip from an unreadable key"
    )


def test_a_denial_entry_that_is_not_an_object_does_not_crash_the_contract() -> None:
    """Total over its own inputs, one level down.

    R1 can check that `permission_denials` is a list; it cannot check what is IN
    the list. A CLI that changed the entry shape would raise AttributeError from
    inside the routing contract — and the caller's handler does not catch it, so
    the operator would get a traceback instead of a routed record.
    """
    routed = er.route(_envelope(denials=["Bash"]), expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    assert routed.undetermined_reason is er.UndeterminedReason.PERMISSION_DENIED
    assert len(routed.permission_denials) == 1, "an unreadable entry is still an entry"


# ---------------------------------------------------------------------------
# THE TOTALITY CLAIM, MADE CHECKABLE RATHER THAN ASSERTED.
#
# Two functions in `exit_record` carry the sentence "TOTAL OVER ITS OWN
# INPUT(S)" in their docstrings, and for one pass exactly one of them was. The
# child (`_redact`) was fixed while the parent (`route`) — the function that IS
# the contract — kept the claim and not the property, which is verbatim the
# defect class this component was built to close: *"every gate here was written
# at the depth of the instance its author was imagining, while its docstring
# claimed the class."*
#
# So the claim is no longer prose that a reviewer has to re-derive. The gate
# below DISCOVERS every claimant by reading docstrings, probes each with every
# type it must survive, and — the half that makes it a class gate rather than
# two more instances — FAILS WHEN A THIRD CLAIMANT APPEARS WITHOUT A PROBE.
# Same shape as the shared-regex enumeration further down, and for the same
# stated reason: a gate whose scope is a hand-kept list retires itself the
# moment it passes.
# ---------------------------------------------------------------------------

TOTALITY_CLAIM = "TOTAL OVER ITS OWN INPUT"

# Every type a value can arrive as instead of the one the annotation promises.
# `bool` is listed separately from `int` deliberately: it is the one that slips
# through an `isinstance(x, int)` written as a type guard.
NON_CONFORMING = ([], "x", 5, True, 0.5, (), set(), object())

# name -> a probe that feeds each non-conforming value in at that function's
# own boundary. A probe returns nothing; it must simply not raise.
TOTALITY_PROBES = {
    # `route`'s own parameter. The annotation says `dict | None`; the values
    # below are what actually arrives when a CLI changes the envelope's shape.
    "route": lambda v: er.route(v, expected_run_id=RUN_ID, expected_ref=EXPECTED_REF),
    # `_redact`'s parameter is a `list` (R1 guarantees that much), so its own
    # inputs are the ENTRIES — which R1 cannot check. Probing it with a non-list
    # would test a contract it does not make.
    "_redact": lambda v: er._redact([v]),
}


@pytest.mark.parametrize("name", sorted(TOTALITY_PROBES))
@pytest.mark.parametrize("value", NON_CONFORMING, ids=lambda v: type(v).__name__)
def test_every_function_claiming_totality_is_total(name: str, value) -> None:
    """A function claiming totality does not raise from inside the contract.

    RAISING IS THE FAILURE MODE, not returning something odd. An
    `AttributeError` or `TypeError` out of here escapes into a caller whose
    error handler does not catch it, so the operator gets a traceback where the
    contract promised a routed record.
    """
    try:
        TOTALITY_PROBES[name](value)
    except Exception as exc:  # noqa: BLE001 — the assertion IS "no exception"
        raise AssertionError(
            f"exit_record.{name} claims {TOTALITY_CLAIM!r} in its docstring and "
            f"raises {type(exc).__name__} on a {type(value).__name__}: {exc}. "
            f"The claim is false at the boundary, and a caller's error handler "
            f"does not catch this."
        ) from exc


def test_route_bins_an_UNREADABLE_ENVELOPE_apart_from_an_absent_record() -> None:
    """Not raising is half of it; landing in an honest bin is the other half.

    The gate above would be satisfied by folding every non-dict envelope into
    `record_absent` — and that is the measurement failure this enum has now
    ruled against three times. `record_absent` is the highest-frequency
    machinery failure there is (a run killed mid-stream), so a CLI that stopped
    emitting an object would report as a fleet dying mid-stream on 100% of runs.
    """
    routed = er.route([], expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    assert routed.routed_outcome is er.RoutedOutcome.UNDETERMINED
    assert routed.undetermined_reason is er.UndeterminedReason.ENVELOPE_UNREADABLE, (
        "an unreadable envelope shares a bin with another condition again — the "
        "computed arm's per-reason rate cannot separate them"
    )
    assert er.route(None, expected_run_id=RUN_ID, expected_ref=EXPECTED_REF).undetermined_reason \
        is er.UndeterminedReason.RECORD_ABSENT, (
        "negative control: a genuinely absent event must NOT have moved bins"
    )


def test_the_totality_ENUMERATION_is_complete() -> None:
    """A third function carrying the claim fails here until it carries a probe.

    WITHOUT THIS THE GATE ABOVE ONLY EVER COVERS WHAT SOMEBODY REMEMBERED, and
    the measured failure was exactly that: two functions carried the sentence,
    one was probed, and the unprobed one was the contract itself. The next
    function to write this sentence cannot write it falsely.
    """
    claimants = {
        name for name, value in vars(er).items()
        if callable(value) and (value.__doc__ or "") and TOTALITY_CLAIM in value.__doc__
    }
    assert claimants == set(TOTALITY_PROBES), (
        f"the totality claim and its probes have diverged — claimed but "
        f"unprobed: {sorted(claimants - set(TOTALITY_PROBES))}; probed but no "
        f"longer claiming: {sorted(set(TOTALITY_PROBES) - claimants)}. Add a "
        f"probe at that function's own boundary, or drop the claim from its "
        f"docstring — an unprobed claim is the defect this gate exists for."
    )


def test_the_totality_DISCOVERY_actually_discriminates() -> None:
    """Positive control for the discovery predicate above.

    The predicate reads docstring text, so a reworded sentence would silently
    empty the claimant set and turn the completeness assertion into a permanent
    pass against a permanently-empty table — the hollow-green this whole module
    is written against. This proves it still separates claimants from
    non-claimants, and that it is not merely matching every function.
    """
    assert TOTALITY_CLAIM in (er.route.__doc__ or "")
    assert TOTALITY_CLAIM in (er._redact.__doc__ or "")
    assert TOTALITY_CLAIM not in (er.routes_to_redispatch.__doc__ or ""), (
        "the discovery predicate is matching a function that makes no totality "
        "claim — it has stopped discriminating"
    )


def test_no_result_event_at_all_is_an_ABSENT_record_not_a_denial() -> None:
    """A log with no `result` event. No event implies no key, so R2 fires.

    THE REASON IS THE PAYLOAD, and this test asserts it because the version that
    asserted only the arm was green while the code reported the wrong one. Both
    reasons route to a human, so routing cannot distinguish them — but a run
    killed mid-stream (turn cap, SIGTERM, crash) is the most frequent machinery
    failure there is, and reporting it as `permission_denied` sends an operator
    hunting a denied tool call that never happened and mis-bins every one of
    them in step 4's per-reason rate.
    """
    routed = er.route(None, expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    assert routed.routed_outcome is er.RoutedOutcome.UNDETERMINED
    assert routed.undetermined_reason is er.UndeterminedReason.RECORD_ABSENT


def test_an_undetermined_route_cannot_be_built_without_its_reason() -> None:
    """The residual arm is a NAMED state that is recorded — enforced, not documented.

    The `iff` was stated on `UndeterminedReason` and held by nothing, which left
    the reason-reporting path one None away from an AttributeError raised inside
    the code that exists to explain machinery failures.
    """
    with pytest.raises(ValueError, match="must name its reason"):
        er.ExitRecord(er.RoutedOutcome.UNDETERMINED)
    with pytest.raises(ValueError, match="belongs only to the computed"):
        er.ExitRecord(er.RoutedOutcome.MERGE, er.UndeterminedReason.UNMATCHED)


def test_the_residual_arm_is_reachable_and_named() -> None:
    """R9 — and it is not decoration.

    A `hold` with no `hold_kind` validates against CHILD_SCHEMA (the sub-kind is
    conditionally required by prose, not by the schema, precisely so the child
    can always fill the schema) and matches none of R6-R8.
    """
    routed = er.route(_envelope(_record(outcome="hold")), expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    assert routed.routed_outcome is er.RoutedOutcome.UNDETERMINED
    assert routed.undetermined_reason is er.UndeterminedReason.UNMATCHED


def test_tool_input_is_dropped_at_read_time_and_has_no_copy_to_leak() -> None:
    """Redaction is not a render-time filter; the field never enters the record.

    Entries carry literal command lines and absolute worktree paths. A field
    that exists in the routing copy and is filtered on the way out is one edit
    away from being published by a renderer that does not know why.

    THE INPUT IS THE MEASURED ENTRY, not the design table's. The version of this
    test that shipped built its fixture with a `matched_rule` key, because it
    was written from `exit-protocol.md` §2.2 rather than from
    `phase1_measure_the_channel.md`'s one observed denial — which is
    `{tool_name, tool_use_id, tool_input}` and carries no `matched_rule` at all.
    A fixture invented from the field list cannot notice that a published field
    is always empty on the real envelope, which is exactly what happened.
    """
    denial = {"tool_name": "Bash", "tool_use_id": "toolu_01CsEb",
              "tool_input": {"command": "sudo ls /root/.ssh"}}
    routed = er.route(_envelope(denials=[denial]), expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    assert routed.permission_denials == (
        {"tool_name": "Bash", "tool_use_id": "toolu_01CsEb"},)
    assert "sudo ls /root/.ssh" not in json.dumps(routed.permission_denials)


def test_a_denial_field_that_is_not_a_string_does_not_crash_the_CONSUMER() -> None:
    """Total over the FIELDS, not only over the entries — the level below.

    `test_a_denial_entry_that_is_not_an_object_...` guards the entry type and is
    green whether or not the fields are guarded, so it could not catch this.
    `review_pr_workflow` builds `sorted({d["tool_name"] for d in ...})` and joins
    it, so an unhashable `tool_name` raises `TypeError` from inside the routing
    contract and `run_review_pr.main` does not catch it — a traceback where a
    routed record was promised. Asserting the redacted values are strings is the
    property; asserting the consumer's own operations succeed is the proof.
    """
    routed = er.route(
        _envelope(denials=[{"tool_name": {"nested": "dict"}, "tool_use_id": 7}]),
        expected_run_id=RUN_ID, expected_ref=EXPECTED_REF,
    )
    assert all(isinstance(v, str) for d in routed.permission_denials for v in d.values())
    # The two operations the consumer actually performs, run here rather than described.
    assert ", ".join(sorted({d["tool_name"] for d in routed.permission_denials}))


# ---------------------------------------------------------------------------
# The schema itself: one declaration, and a size bound that is a real constraint.
# ---------------------------------------------------------------------------

def test_the_schema_argument_is_serialised_from_the_object_the_router_validates() -> None:
    """§6's one-declaration rule, asserted rather than asserted-in-prose.

    If the string handed to `--json-schema` were built separately, the producer
    and the consumer could disagree with every test in both green — which is
    exactly how `parse_verdict` came to be typed twice.
    """
    assert json.loads(er.schema_argument()) == er.CHILD_SCHEMA


def test_the_schema_fits_the_size_bound_it_declares() -> None:
    """The schema crosses a process boundary as an argument VALUE.

    Its size is a build-time cost for every caller — the constraint Phase 1
    E1(g) surfaced and the availability framing missed. An over-large schema
    fails at the process boundary with an error that names neither the schema
    nor the field that grew it.
    """
    assert len(er.schema_argument().encode()) <= er.SCHEMA_BYTE_BOUND


def test_the_child_schema_cannot_express_the_computed_abstention_arm() -> None:
    """The split is enforced by the schema, not by convention.

    `undetermined` is the parent's word. A child that could assert it would
    collapse the two arms back into one member and neither would be countable.
    """
    outcomes = er.CHILD_SCHEMA["properties"]["outcome"]["enum"]
    assert er.RoutedOutcome.UNDETERMINED.value not in outcomes
    assert set(outcomes) == {o.value for o in er.Outcome}


def test_the_working_record_reference_is_not_typed_as_a_url() -> None:
    """A component whose work product is not code in git has no PR to point at.

    The guard is that the reference carries a `substrate` discriminator and an
    opaque string id — not that any particular field name exists. A record whose
    id were an integer would force every consumer to cast, and both consumers
    hold it as a string today (`routing.py`'s `match.group(1)`, bash's
    `${PR_URL##*/}`).
    """
    ref = er.CHILD_SCHEMA["properties"]["completion_ref"]
    assert "substrate" in ref["required"]
    assert ref["properties"]["id"]["type"] == "string"


# ---------------------------------------------------------------------------
# The shadow comparison. A comparison that cannot fail records a protection that
# does not exist, so this mutates the record until the two channels disagree.
# ---------------------------------------------------------------------------


def _review(monkeypatch, tmp_path, record, prose, denials=None,
            block=_FakeWorkflow.DEFAULT_BLOCK, prior_blocks=0, posts_block=True):
    from modules.assistant.review_pr.review_pr_helper import ReviewInput
    fake = _FakeWorkflow(record, prose, denials, block, prior_blocks, posts_block)
    wf = fake.install(monkeypatch, tmp_path)
    return wf.run_review(ReviewInput(pr_number="67"), tmp_path)


def test_both_channels_agreeing_routes_and_records_the_agreement(monkeypatch, tmp_path) -> None:
    """The control. Without it, a `raise` on every path would pass the next test."""
    result = _review(monkeypatch, tmp_path,
                     _record(run_id="@ISSUED@"), "VERDICT: MERGE\n")
    assert result.verdict is routing.Verdict.MERGE
    assert result.record is not None
    assert result.record.routed_outcome is er.RoutedOutcome.MERGE
    assert any("Prose shadow agreed" in n for n in result.notes)


def test_the_log_is_NAMED_with_the_nonce_the_parent_issued(monkeypatch, tmp_path) -> None:
    """The allocation is bound to run identity, not to a shared constant.

    `MODEL_KEY` is one string for every PR this workflow reviews and the log
    directory is the repo root's, so a name built from the model key and a
    stamp collides between concurrent dispatches. Passing the nonce is what
    makes the name unique BY CONSTRUCTION — and it is the same nonce that
    reaches the child in the prompt and comes back in the record, so the log's
    filename greps against the record inside it.
    """
    from modules.assistant.review_pr.review_pr_helper import ReviewInput
    fake = _FakeWorkflow(_record(run_id="@ISSUED@"), "VERDICT: MERGE\n")
    wf = fake.install(monkeypatch, tmp_path)

    seen: dict = {}

    def _alloc(repo_root, model_key, *, run_id):
        seen.update(repo_root=repo_root, model_key=model_key, run_id=run_id)
        return tmp_path / "run.jsonl"

    monkeypatch.setattr(wf._shared, "claude_log_path", _alloc)
    wf.run_review(ReviewInput(pr_number="67"), tmp_path)

    assert seen.get("run_id"), "the allocation got no run identity — the name is shared again"
    assert seen["run_id"] == fake.run_id, (
        "the log's nonce and the nonce in the prompt differ, so the filename no "
        "longer locates the record it carries"
    )


def test_the_shadow_comparison_actually_fires(monkeypatch, tmp_path, capsys) -> None:
    """Mutate the typed record so the two channels disagree; assert it is SURFACED.

    This is the test the requirement names explicitly, and it is the one that
    proves the shadow is a protection rather than a decoration.

    IT ASSERTS THE SIGNAL, NOT A RAISE — ruled 2026-08-11. The comparison used
    to throw, and the throw destroyed completed reviews at a measured 2-in-8
    rate with the channels agreeing about the review in BOTH firings. The
    protection was never the exception; it is that the divergence is impossible
    to miss and is durably recorded. So this asserts the run SURVIVES, the
    banner is emitted, and `channels_agree` is false in the log — a test that
    demanded the raise would re-introduce the defect the moment someone made it
    pass.
    """
    result = _review(monkeypatch, tmp_path,
                     _record(run_id="@ISSUED@", outcome="hold", hold_kind="redispatch"),
                     "VERDICT: MERGE\n")

    banner = capsys.readouterr().out
    assert "CHANNEL DIVERGENCE" in banner, "a divergence must be impossible to miss"
    assert "RECORDED, NOT FATAL" in banner
    assert result is not None, "the review must survive a divergence, not be destroyed by it"


def test_an_absent_record_against_a_confident_prose_merge_fails_loud(monkeypatch, tmp_path) -> None:
    """The dangerous shape: the typed channel is silent and the prose says MERGE.

    Under the prose-only incumbent this run merges. Under the typed contract it
    reaches a human, and during Phase 3 it raises — which is what running both
    channels on one pair exists to surface.
    """
    with pytest.raises(RuntimeError, match="record_absent"):
        _review(monkeypatch, tmp_path, None, "VERDICT: MERGE\n")


def test_a_stale_record_is_caught_even_though_it_is_well_formed(monkeypatch, tmp_path) -> None:
    """The record validates; only the nonce betrays it."""
    with pytest.raises(RuntimeError, match="record_stale"):
        _review(monkeypatch, tmp_path,
                _record(run_id="0" * 32), "VERDICT: MERGE\n")


def test_a_denial_is_surfaced_without_its_command_line(monkeypatch, tmp_path, capsys) -> None:
    """R1 end to end, with the redaction holding across the whole path.

    ASSERTS THE PROPERTY, NOT THE MECHANISM. This required a RuntimeError until
    2026-08-11, when a `permission_denied` divergence was demoted from a raise
    to a loud note — the raise was destroying completed reviews at a measured
    2-in-8 rate. **Requirement 5 is unchanged and is what this guards**:
    `permission_denials[]` is surfaced on EVERY run regardless of any routing
    ruling, and the command line never travels with it. Both halves must hold
    on whichever channel carries the news, so this reads the operator-facing
    output rather than an exception type.
    """
    denial = {"tool_name": "Bash", "tool_use_id": "toolu_01CsEb",
              "tool_input": {"command": "sudo cat /etc/shadow"}}

    _review(monkeypatch, tmp_path, _record(run_id="@ISSUED@"),
            "VERDICT: MERGE\n", denials=[denial])

    surfaced = capsys.readouterr().out
    assert "permission_denied" in surfaced, (
        "requirement 5: a denial must reach the operator on every run"
    )
    assert "/etc/shadow" not in surfaced, (
        "the denied command line must never travel with the denial"
    )


# ---------------------------------------------------------------------------
# The render <-> record invariant. Co-authoring persists for the three prose
# regions that have no field, so the two copies are CHECKED rather than trusted.
# ---------------------------------------------------------------------------

def test_a_finding_only_in_the_record_fails_loud(monkeypatch, tmp_path) -> None:
    """A finding the operator never sees.

    The typed record carries it, so Phase 5 counts it and the parent routes on
    it — and the durable record, which is the only copy that outlives the run,
    does not mention it.
    """
    with pytest.raises(RuntimeError, match="Only in the record"):
        _review(monkeypatch, tmp_path, _record(run_id="@ISSUED@"), "VERDICT: MERGE\n",
                block="pr_review:\n  findings: []\n")


def test_a_finding_only_in_the_block_fails_loud(monkeypatch, tmp_path) -> None:
    """A finding Phase 5's stopping predicate will never count.

    The other direction, and it is not symmetrical in consequence: this one
    makes a convergence rule read a smaller finding set than the operator does,
    so it stops early on work that is still open.
    """
    block = (_FakeWorkflow.DEFAULT_BLOCK
             + "    - id: an-invented-finding\n      disposition: noted\n")
    with pytest.raises(RuntimeError, match="Only in the block"):
        _review(monkeypatch, tmp_path, _record(run_id="@ISSUED@"), "VERDICT: MERGE\n",
                block=block)


def test_a_redispositioned_finding_fails_loud(monkeypatch, tmp_path) -> None:
    """Same ids, different disposition — and the id-only check could not see it.

    `disposition.md` promises the child that ids AND dispositions are identical
    in both copies and that the caller fails loud on a mismatch. It is also the
    field Phase 5's stopping predicate keys on, so a block reading `deferred`
    against a record reading `fixed` makes the operator and the convergence rule
    disagree about whether the work is closed.
    """
    block = ("pr_review:\n  pr: 67\n  findings:\n"
             "    - id: a-stable-slug\n      disposition: deferred\n")
    with pytest.raises(RuntimeError, match="Only in the record"):
        _review(monkeypatch, tmp_path, _record(run_id="@ISSUED@"), "VERDICT: MERGE\n",
                block=block)


def test_a_quoted_finding_id_is_not_a_disagreement(monkeypatch, tmp_path) -> None:
    """`- id: "a-slug"` is valid yaml for `a-slug`, and the raw capture kept the quotes.

    A guard that fails on semantically-correct input trains its reader to ignore
    it — the same argument the block parser uses to avoid a strict YAML parser.
    """
    block = ('pr_review:\n  pr: 67\n  findings:\n'
             '    - id: "a-stable-slug"\n      disposition: "fixed"\n')
    result = _review(monkeypatch, tmp_path, _record(run_id="@ISSUED@"),
                     "VERDICT: MERGE\n", block=block)
    assert result.verdict is routing.Verdict.MERGE


def test_a_missing_block_fails_loud(monkeypatch, tmp_path) -> None:
    """The typed half landed and the durable half did not.

    This is arrangement A's characteristic failure: the outcome survives and its
    reasoning does not.
    """
    with pytest.raises(RuntimeError, match="no\n?\\s*(new )?`?pr_review:`? block"):
        _review(monkeypatch, tmp_path, _record(run_id="@ISSUED@"), "VERDICT: MERGE\n",
                block=None, posts_block=False)


def test_pass_two_posting_nothing_does_not_pass_against_pass_ones_block(
        monkeypatch, tmp_path) -> None:
    """The invariant must read THIS pass's block, and it used to read any.

    `disposition.md` INVARIANT 1 requires every prior finding to be carried
    forward, so identical id sets ACROSS passes is the norm rather than a
    coincidence. A pass 2 that produced a valid record and then failed to post
    its comment — `gh` erroring, the `@claude` guard tripping — was therefore
    compared against pass 1's still-matching block, matched, and reported the
    invariant satisfied: silently passing in exactly the case it exists for.

    The block here is pass 1's and it MATCHES the record; only the unchanged
    block count betrays the missing post.
    """
    with pytest.raises(RuntimeError, match="posted no new"):
        _review(monkeypatch, tmp_path, _record(run_id="@ISSUED@"), "VERDICT: MERGE\n",
                block=_FakeWorkflow.DEFAULT_BLOCK, prior_blocks=1, posts_block=False)


def test_pass_two_that_does_post_is_accepted(monkeypatch, tmp_path) -> None:
    """The negative control for the test above: pass 2 must still be able to pass."""
    result = _review(monkeypatch, tmp_path, _record(run_id="@ISSUED@"),
                     "VERDICT: MERGE\n", prior_blocks=1, posts_block=True)
    assert result.this_pass == 2
    assert result.verdict is routing.Verdict.MERGE


# ---------------------------------------------------------------------------
# A VERIFICATION THAT COULD NOT RUN MUST NOT DESTROY A DECISION THAT ALREADY DID.
#
# This check runs AFTER the child posted its comment and AFTER the route was
# persisted, so for one pass a 5xx or a rate limit on a READ-ONLY `gh` call
# discarded a ~40-minute review at real budget and killed the parent's build
# loop with it. The reads are retried; on exhaustion the run completes with the
# check reported as unperformed. Sleeps are pinned to zero throughout — the
# backoff durations are not what these tests are about.
#
# AND "TRANSIENT" IS A SHAPE, NOT A FEELING. The first version of the retry
# caught `RuntimeError` because that is what a non-zero `gh` exit raises — while
# the readers it wrapped parsed stdout themselves, so a zero-exit reply with a
# truncated or non-JSON body raised `json.JSONDecodeError` instead. A `ValueError`
# is caught by nothing on this path, so that shape skipped the retry at ZERO
# attempts and crashed the parent build loop, which is the exact outcome the
# retry was built to prevent, reached through the sibling exception type. The
# normalisation now lives at `gh_json`, so the two tests below cover BOTH ends:
# that the shape raises the retryable type, and that a run meeting it survives.
# ---------------------------------------------------------------------------


def _flaky_reader(fails: int, real):
    """A reader that raises a transient `gh` error `fails` times, then works."""
    calls = {"n": 0}

    def _read(*a, **k):
        calls["n"] += 1
        if calls["n"] <= fails:
            raise RuntimeError("gh pr view failed: API rate limit exceeded")
        return real(*a, **k)

    return _read


@pytest.mark.parametrize("body", ["", "<html>502 Bad Gateway</html>", '{"comments": ['],
                         ids=["empty", "error_page", "truncated"])
def test_a_zero_exit_gh_reply_that_is_not_JSON_raises_the_RETRYABLE_type(
        monkeypatch, tmp_path, body: str) -> None:
    """The gap, closed at the boundary that knows it can happen.

    `gh` validates the exit code and nothing about stdout, so each of these
    bodies used to reach `json.loads` in the caller and come back out as a
    `ValueError` — a family no guard on this path catches. `gh_json` is where a
    caller stops needing to know that: one call, one exception family, and the
    retry above keeps working without enumerating parse errors it cannot foresee.

    The raw body must survive into the message. "Expecting value at line 1
    column 1" is true of all three cases above and tells an operator which one
    it was in none of them.
    """
    from modules.assistant import assistant_activities as shared
    monkeypatch.setattr(shared, "gh", lambda *a, **k: body)
    with pytest.raises(RuntimeError, match="did not return JSON") as caught:
        shared.gh_json(["pr", "view", "67", "--json", "comments"], tmp_path,
                       expect=shared.GH_JSON_SHAPES)
    assert repr(body[:200]) in str(caught.value), (
        "the reply was swallowed — an operator cannot tell an error page from a "
        "truncated body from an empty one"
    )
    assert not isinstance(caught.value, ValueError), (
        "still a ValueError, so the retry and the parent build loop both miss it"
    )


def test_a_MALFORMED_gh_REPLY_degrades_like_any_other_blip(
        monkeypatch, tmp_path) -> None:
    """The same case end-to-end, through the REAL reader rather than a fake one.

    THIS IS THE ONE THAT WOULD HAVE CAUGHT IT. Every other test in this section
    fakes `thread_snapshot` and raises `RuntimeError` from the fake — so
    they assert the retry handles the error the fake chose to throw, and are
    green against a reader that could throw a second family. Here the real
    reader runs and only `gh` is faked, which is where the shape actually
    enters.
    """
    from modules.assistant.review_pr import review_pr_activities as act
    from modules.assistant.review_pr.review_pr_helper import ReviewInput
    real_reader = act.thread_snapshot  # captured BEFORE the fake installs

    fake = _FakeWorkflow(_record(run_id="@ISSUED@"), "VERDICT: MERGE\n")
    wf = fake.install(monkeypatch, tmp_path)
    slept = _no_sleep(monkeypatch)
    monkeypatch.setattr(act, "thread_snapshot", real_reader)
    monkeypatch.setattr(act._shared, "gh", lambda *a, **k: "<html>502 Bad Gateway</html>")

    result = wf.run_review(ReviewInput(pr_number="67"), tmp_path)

    assert result.verdict is routing.Verdict.MERGE, (
        "a malformed reply killed the run — it took the pre-fix path, where the "
        "exception family is the only thing that differs from a rate limit"
    )
    assert len(slept) == len(wf._THREAD_READ_BACKOFF_SECONDS), (
        "the malformed reply was not retried like every other transient shape"
    )
    unchecked = [n for n in result.notes if "NOT CHECKED" in n]
    assert len(unchecked) == 1, f"the unperformed check was not reported: {result.notes}"
    assert "did not return JSON" in unchecked[0], "the real cause was swallowed"


def test_a_transient_thread_read_is_retried_and_the_review_survives(
        monkeypatch, tmp_path) -> None:
    """THE HEADLINE CASE: a blip must not discard a completed, already-routed review.

    The first read fails the way a rate limit or a 5xx fails; the retry
    succeeds; the invariant then runs for real and agrees. The run must reach
    its verdict with no could-not-check note at all — a retry that "worked" but
    still degraded the result would be the fix in name only.
    """
    from modules.assistant.review_pr import review_pr_activities as act
    from modules.assistant.review_pr.review_pr_helper import ReviewInput
    fake = _FakeWorkflow(_record(run_id="@ISSUED@"), "VERDICT: MERGE\n")
    wf = fake.install(monkeypatch, tmp_path)
    slept = _no_sleep(monkeypatch)

    monkeypatch.setattr(act, "thread_snapshot",
                        _flaky_reader(1, lambda *a, **k: (1, [fake.block])))

    result = wf.run_review(ReviewInput(pr_number="67"), tmp_path)

    assert result.verdict is routing.Verdict.MERGE
    assert slept, "the read was not retried — it failed on the first attempt"
    assert not any("NOT CHECKED" in n for n in result.notes), (
        "the retry succeeded but the run still reported the check as unperformed"
    )


def test_a_PERSISTENT_thread_read_failure_completes_the_run_and_says_so(
        monkeypatch, tmp_path) -> None:
    """Exhausted retries record the check as UNPERFORMED. They do not raise.

    The route was persisted before this check ran, so the evidence survives
    either way — and a run that dies here throws away work that already
    succeeded, for a reason with nothing to do with the review.

    The note must be LOUD: an invariant that silently did not run is
    indistinguishable from one that held, which is the very thing this check
    exists to make non-silent.
    """
    from modules.assistant.review_pr import review_pr_activities as act
    from modules.assistant.review_pr.review_pr_helper import ReviewInput
    fake = _FakeWorkflow(_record(run_id="@ISSUED@"), "VERDICT: MERGE\n")
    wf = fake.install(monkeypatch, tmp_path)
    slept = _no_sleep(monkeypatch)

    def _boom(*a, **k):
        raise RuntimeError("gh pr view failed: API rate limit exceeded")

    monkeypatch.setattr(act, "thread_snapshot", _boom)

    result = wf.run_review(ReviewInput(pr_number="67"), tmp_path)

    assert result.verdict is routing.Verdict.MERGE, (
        "a failed READ changed the routing — the policy question was supposed "
        "to be untouched"
    )
    unchecked = [n for n in result.notes if "NOT CHECKED" in n]
    assert len(unchecked) == 1, f"the unperformed check was not recorded: {result.notes}"
    assert "not a disagreement" in unchecked[0]
    assert "rate limit" in unchecked[0], "the real `gh` error was swallowed"
    assert len(slept) == len(wf._THREAD_READ_BACKOFF_SECONDS), (
        "the retry budget is not the declared one"
    )


def test_the_route_is_PERSISTED_even_when_the_check_never_runs(
        monkeypatch, tmp_path) -> None:
    """The claim the fix rests on, asserted rather than reasoned about.

    "Let the run complete, the evidence survives either way" is only true if the
    parent stratum is already on disk when the check fails. If the ordering ever
    inverted, this degrades from "the check did not run" to "the run produced no
    countable record", which is the thing Phase 4 most needs counted.
    """
    from modules.assistant.review_pr import review_pr_activities as act
    from modules.assistant.review_pr.review_pr_helper import ReviewInput
    fake = _FakeWorkflow(_record(run_id="@ISSUED@"), "VERDICT: MERGE\n")
    wf = fake.install(monkeypatch, tmp_path)
    _no_sleep(monkeypatch)
    monkeypatch.setattr(act, "thread_snapshot", _flaky_reader(99, lambda *a, **k: (0, [])))

    wf.run_review(ReviewInput(pr_number="67"), tmp_path)

    events = [json.loads(line) for line in
              (tmp_path / "run.jsonl").read_text().splitlines() if line.strip()]
    routes = [e for e in events if e.get("type") == "parent_route"]
    assert len(routes) == 1, "the parent stratum was not persisted"
    assert routes[0]["routed_outcome"] == "merge"


def test_a_REAL_disagreement_still_raises_after_a_transient_read(
        monkeypatch, tmp_path) -> None:
    """Negative control for the whole retry section.

    Softening the could-not-check path must not soften the path it sits beside.
    A retry that succeeded and then found the two copies genuinely disagreeing
    still fails loud — otherwise the section above would have converted a real
    finding into a note.
    """
    from modules.assistant.review_pr import review_pr_activities as act
    from modules.assistant.review_pr.review_pr_helper import ReviewInput
    fake = _FakeWorkflow(_record(run_id="@ISSUED@"), "VERDICT: MERGE\n")
    wf = fake.install(monkeypatch, tmp_path)
    _no_sleep(monkeypatch)

    wrong = "pr_review:\n  findings:\n    - id: a-different-slug\n      disposition: fixed\n"
    monkeypatch.setattr(act, "thread_snapshot",
                        _flaky_reader(1, lambda *a, **k: (1, [wrong])))

    with pytest.raises(RuntimeError, match="disagree on findings"):
        wf.run_review(ReviewInput(pr_number="67"), tmp_path)


def test_the_invariant_is_not_run_when_there_was_no_record_to_compare(
        monkeypatch, tmp_path) -> None:
    """An UNDETERMINED route has no ids, so re-reporting it says nothing new.

    Also the negative control for the three tests above: without this, an
    invariant that raised unconditionally would satisfy all of them.
    """
    result = _review(monkeypatch, tmp_path, None, "VERDICT: HOLD - needs-assistance\n",
                     block=None)
    assert result.record.undetermined_reason is er.UndeterminedReason.RECORD_ABSENT
    assert result.verdict is routing.Verdict.HOLD_NEEDS_ASSISTANCE


def test_finding_ids_are_read_from_both_archive_indents() -> None:
    """Two-space and four-space indents both occur in the archive.

    A parser matching only one would report a spurious disagreement on half the
    corpus — a check that fails on valid input is worse than no check, because
    it trains its reader to ignore it.
    """
    block = ("pr_review:\n  findings:\n  - id: two-space\n"
             "    disposition: fixed\n    - id: four-space\n")
    assert helper.finding_ids_in_block(block) == frozenset({"two-space", "four-space"})


# ---------------------------------------------------------------------------
# The WORKING-RECORD ADDRESS — §6's rule covers it too, and this is the measured defect.
# ---------------------------------------------------------------------------

def test_the_typed_vocabulary_is_declared_in_exactly_one_module() -> None:
    """§6's one-declaration rule, checked by CLAIM SHAPE rather than by value.

    Not a list of the strings that are wrong today — a list like that retires
    itself the moment it passes, and would be blind to the NEXT member added.
    This enumerates the vocabulary FROM the enums and asserts that no other
    module under `modules/` spells any member as a literal. A second copy passes
    every test in both copies while diverging; that is how `parse_verdict` came
    to be typed twice, and the copy that decided merges had zero tests.

    SCOPE, STATED: `modules/**/*.py`. Deliberately outside it — the prompt
    files, where the emit instruction legitimately names members (§6 makes
    prompt-borne emission part of the conformance surface, and the render tests
    cover that a placeholder has a supplier), and the frozen V1 bash fleet,
    which has no typed vocabulary at all.
    """
    members = {m.value for enum in (er.HoldKind, er.RoutedOutcome, er.UndeterminedReason)
               for m in enum}
    # `merge`, `hold` and `redispatch` are also prose-vocabulary substrings, and
    # `routing.py` legitimately declares those. The typed-only members are the
    # ones whose spelling exists nowhere else by construction.
    typed_only = {m for m in members if m not in {"merge", "hold", "redispatch"}}
    assert typed_only, "the vocabulary lost every member unique to the typed channel"

    modules = _ASSISTANT
    offenders: list[str] = []
    for path in modules.rglob("*.py"):
        if path.name == "exit_record.py" or "tests" in path.parts:
            continue
        text = path.read_text()
        for member in sorted(typed_only):
            if f'"{member}"' in text or f"'{member}'" in text:
                offenders.append(f"{path.relative_to(modules)}: {member!r}")
    assert not offenders, (
        "the typed vocabulary is spelled outside exit_record.py: " + "; ".join(offenders)
    )


def test_a_comment_merely_mentioning_the_key_is_not_a_record() -> None:
    """Issue #68, as a test.

    Both pass-counters matched any comment containing the string, so a
    Post-Run Reflection or a brief quoting the wire format was counted as a
    review pass — writing a wrong `pass:` into the DURABLE record. Measured
    across 39 PRs: 18 matches against 15 real blocks.
    """
    mention = "The reviewer posts a `pr_review:` yaml block on each pass."
    assert helper.PR_REVIEW_BLOCK.search(mention) is None


def test_a_fenced_block_is_a_record() -> None:
    """The negative control for the test above.

    An anchored predicate that matched nothing would pass it while making every
    pass count zero — which is the same wrong number from the other direction.
    """
    body = "Here is the block:\n\n```yaml\npr_review:\n  pr: 67\n  pass: 1\n```\n"
    assert helper.PR_REVIEW_BLOCK.search(body) is not None


def test_count_prior_passes_no_longer_counts_a_mention(monkeypatch, tmp_path) -> None:
    """The consumer-side half of issue #68, at its own call site.

    `PR_REVIEW_BLOCK` being anchored is necessary and not sufficient — the
    counter has to USE it. This ran as `"pr_review:" in body` until this phase.
    """
    act = _with_comments(monkeypatch, [
        "## Post-Run Reflection\nThe `pr_review:` block spec was clear.",
        "```yaml\npr_review:\n  run_id: 0123456789abcdef0123456789abcdef\n  pr: 66\n  pass: 1\n```",
    ])
    assert act.count_prior_passes("66", tmp_path) == 1


def test_the_window_reader_puts_the_LAST_block_LAST(monkeypatch, tmp_path) -> None:
    """§6.2's ordering rule: comment creation order, last wins.

    A correction pass reading the FIRST block would reconcile against a
    superseded record and not know it did.
    """
    act = _with_comments(monkeypatch, [
        "```yaml\npr_review:\n  run_id: 0123456789abcdef0123456789abcdef\n  pass: 1\n  findings:\n    - id: old\n```",
        "unrelated chatter mentioning pr_review: in passing",
        "```yaml\npr_review:\n  run_id: 0123456789abcdef0123456789abcdef\n  pass: 2\n  findings:\n    - id: new\n```",
    ])
    block = act.pr_review_blocks("66", tmp_path)[-1]
    assert helper.finding_ids_in_block(block) == frozenset({"new"})


def test_the_window_reader_takes_the_LAST_block_WITHIN_a_comment_too(
    monkeypatch, tmp_path,
) -> None:
    """LAST WINS is a property of blocks, and the comment is not the unit.

    The version that shipped used `PR_REVIEW_BLOCK.search` — the FIRST block per
    comment — so "last wins" held only across comments. `replay_pr_review_blocks`
    has always used `findall`, so two of the three readers of this address
    disagreed about what "the latest block" means, and the test above could not
    see it because each of its comments carries exactly one block.

    THE SHAPE IS ONE THE PROMPT INVITES, not a contrived one. `disposition.md`
    INVARIANT 1 requires each pass to carry every prior finding forward, so a
    disposition that quotes the block it supersedes above its own is ordinary
    model behaviour. Under `search` this returned the QUOTED, superseded block —
    and the render↔record invariant then compared this pass's typed record
    against the previous pass's findings and raised on a correct run, after the
    comment had already been posted. The failure was loud, wrong, and unrecoverable.
    """
    act = _with_comments(monkeypatch, [
        "```yaml\npr_review:\n  run_id: 0123456789abcdef0123456789abcdef\n  pass: 1\n  findings:\n    - id: old\n```",
        "Superseding the previous disposition, quoted here for continuity:\n\n"
        "```yaml\npr_review:\n  run_id: 0123456789abcdef0123456789abcdef\n  pass: 1\n  findings:\n    - id: old\n```\n\n"
        "This pass:\n\n"
        "```yaml\npr_review:\n  run_id: 0123456789abcdef0123456789abcdef\n  pass: 2\n  findings:\n    - id: new\n```",
    ])
    block = act.pr_review_blocks("66", tmp_path)[-1]
    assert helper.finding_ids_in_block(block) == frozenset({"new"})


def test_a_block_without_a_32_hex_run_id_is_NOT_a_pass(monkeypatch, tmp_path) -> None:
    """Fence-anchoring was right about its trigger and silent about this one.

    Issue #68 anchored the predicate so PROSE mentioning `pr_review:` stopped
    counting. What arrived instead was a BUILD run posting a genuine fenced
    block for its own decision log — nothing tells a build run that key is the
    review workflow's address, so it borrowed it, and every reader counted it.

    MEASURED on PR #94: `run_id: build-refine-correction-1786880277` and
    `verdict: READY`, which is not in the review enum. Across seven PRs, 11 of
    12 real blocks carry a 32-hex nonce and the one that does not is that build
    comment — so the nonce discriminates on something real passes already have,
    which is why the fix is here and not a prompt line asking build runs to
    remember a different key.
    """
    act = _with_comments(monkeypatch, [
        "```yaml\npr_review:\n  run_id: 0123456789abcdef0123456789abcdef\n  pass: 1\n```",
        "# build-refine — Decision Log\n"
        "```yaml\npr_review:\n  run_id: build-refine-correction-1786880277\n"
        "  verdict: READY\n```",
    ])
    assert act.count_prior_passes("94", tmp_path) == 1, (
        "a build run's decision log carried a fenced `pr_review:` block and was "
        "counted as a review pass — the durable `pass:` number it inflates is "
        "read by the convergence predicate"
    )


def test_count_prior_passes_counts_COMMENTS_even_when_one_quotes_another(
    monkeypatch, tmp_path,
) -> None:
    """The asymmetry with the WINDOW reader, asserted so it survives.

    That one moved to `finditer` because it selects BLOCKS. This one must
    NOT: it counts PASSES, one pass posts one comment however many blocks it
    quotes, and `review_pr_workflow`'s `posted <= prior_pass` delta reads it. A
    tidying edit that made the two symmetric would count the quoting comment
    twice and break the delta in a new way — so the difference is a test, not a
    comment.
    """
    act = _with_comments(monkeypatch, [
        "```yaml\npr_review:\n  run_id: 0123456789abcdef0123456789abcdef\n  pass: 1\n```",
        # The quoted block carries the FIRST pass's nonce, because that is what
        # quoting means; "mine" carries this pass's own. Both are 32-hex, so the
        # run_id filter is not what makes this comment count once — the
        # one-comment-one-pass rule is.
        "Quoting the prior block:\n"
        "```yaml\npr_review:\n  run_id: 0123456789abcdef0123456789abcdef\n  pass: 1\n```\n"
        "and mine:\n"
        "```yaml\npr_review:\n  run_id: fedcba9876543210fedcba9876543210\n  pass: 2\n```",
    ])
    assert act.count_prior_passes("66", tmp_path) == 2, (
        "two comments carry a block, so two passes have posted — the second "
        "comment carrying two blocks does not make it two passes"
    )


def test_the_window_is_EMPTY_on_a_fresh_pr(monkeypatch, tmp_path) -> None:
    """Negative control: a thread of mentions is a thread with no record."""
    act = _with_comments(monkeypatch, ["no block here", "pr_review: mentioned only"])
    assert act.pr_review_blocks("66", tmp_path) == []


def test_the_archive_shape_that_produced_the_wrong_pass_number() -> None:
    """PR #66's actual shape: two reflections, then one block.

    The unanchored predicate counted 3 and the block was labelled `pass: 3`.
    It is pass 1.
    """
    comments = [
        "## Post-Run Reflection\nNo friction. The `pr_review:` block spec was clear.",
        "build-refine summary — the pr_review: key is the wire format, unchanged.",
        "```yaml\npr_review:\n  run_id: 0123456789abcdef0123456789abcdef\n  pr: 66\n  pass: 1\n```",
    ]
    assert sum(1 for c in comments if helper.PR_REVIEW_BLOCK.search(c)) == 1
    assert sum(1 for c in comments if "pr_review:" in c) == 3   # the defect, reproduced


# ---------------------------------------------------------------------------
# §6 — ONE DECLARATION. Both gates below are on the CLASS, not on the instance
# that was found: each one fails when a NEW second declaration appears, not only
# when the known one comes back.
# ---------------------------------------------------------------------------

# The working-record shared parse, ENUMERATED rather than asserted one name at a time.
# A table because the failure this gates is *a pair that nobody added an
# assertion for*: the first version of this gate named two pairs and the two the
# same commit introduced went ungated and had already drifted (`\s` vs `[ \t]`),
# with both suites green. Adding a shared regex is now a row here, and
# `test_the_shared_parse_ENUMERATION_is_complete` fails until it is.
SHARED_WORKING_RECORD_PATTERNS = (
    ("PR_REVIEW_BLOCK", "FENCE"),
    ("_FINDING_ID", "FINDING_ID"),
    ("_FINDING_ITEM", "FINDING_ENTRY"),
    ("_DISPOSITION", "DISPOSITION"),
    # Added when Phase 5 gave the workflow a consumer for the incumbent
    # convergence flag. It was one-sided until then, and the enumeration gate
    # below is what forced the pairing rather than a reviewer remembering: the
    # workflow's shadow agreement count and the archive replay's now read the
    # same field, so a divergence would make the two disagree about how often
    # the model-asserted flag and the computed signal match, with both suites
    # green.
    ("CONVERGED_FLAG", "CONVERGED"),
    # Added when a review pass measured that `- id:` is NOT unique to a finding:
    # the shipped prompt gives the child `dispatch_context: |` and `precheck: |`
    # block scalars whose documented content is *"which findings to fix"*, in the
    # same block, after `findings:`. Both readers now anchor the finding scan to
    # the `findings:` section, and they must anchor IDENTICALLY — otherwise the
    # live path's render↔record invariant and this tool's convergence
    # denominator disagree about what a finding is, which is the divergence the
    # pairs above exist to catch, one region up.
    ("_FINDINGS_SECTION", "FINDINGS_SECTION"),
)

# Regexes that exist on ONE side only, with the reason. These are not shared
# parse — they read fields the other side has no consumer for — so pairing them
# would be inventing a coupling rather than gating one. Listed explicitly so
# that a genuinely shared regex cannot hide in the gap.
REPLAY_ONLY_PATTERNS = frozenset({
    "PASS", "ATTEMPT", "VERDICT",                 # block-level measurement fields
    "CATEGORY",                                   # finding-level, measurement only
})

# The mirror of the set above, and it exists for the same reason: a regex that
# is genuinely one-sided must be DECLARED one-sided, or the enumeration gate
# below cannot tell it from one somebody forgot to pair.
HELPER_ONLY_PATTERNS = frozenset({
    # Phase 4's run nonce in the durable block. One-sided because
    # `replay_pr_review_blocks` has no consumer for it — it measures the archive,
    # where no block carries the field, and it never has to answer "which of
    # these is THIS pass's" because it is not inside a pass. The moment that
    # tool acquires a reader, this belongs in the paired table above and this
    # entry is what has to be deleted to put it there.
    "RUN_ID_IN_BLOCK",
})


def _load_replay_module():
    """The measurement tool, loaded by path rather than imported.

    It reads the fleet from OUTSIDE the workflow, so a real import would invert
    the dependency — which is the reason these declarations are gated instead of
    shared.
    """
    import importlib.util

    replay = Path(__file__).resolve().parents[4] / "helpers" / "measure" / \
        "replay_pr_review_blocks.py"
    assert replay.exists(), f"the second declaration moved: {replay}"
    spec = importlib.util.spec_from_file_location("_replay", replay)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("helper_name,replay_name", SHARED_WORKING_RECORD_PATTERNS)
def test_the_working_record_SHARED_PARSE_is_one_declaration_across_both_python_readers(
    helper_name: str, replay_name: str,
) -> None:
    """§6 covers the record's schema AND ITS ADDRESS, and the address is the
    measured half — three incompatible declarations wrote a wrong durable
    `pass:` onto 2 of 8 archived PRs (issue #68).

    THE GATE COVERS THE SHARED PARSE, NOT ONLY THE ADDRESS. The block marker
    locates the record; `_FINDING_ITEM`/`_DISPOSITION` attribute a disposition
    to a finding, and those feed two different consumers — Phase 5's stopping
    predicate reads them through `replay_pr_review_blocks`, the render↔record
    invariant reads them through `review_pr_helper`. If the two ever attribute a
    disposition differently, the convergence rule and the write-time guard
    disagree about whether work is closed, with both suites green. That is the
    same failure the address half was widened for, one field down.

    Two Python declarations survive by design: `review_pr_helper` (the workflow)
    and `replay_pr_review_blocks` (the measurement tool that reads the fleet
    from outside it, so importing across that boundary would invert the
    dependency). Coupling them by IMPORT is wrong; leaving them free to drift
    silently is also wrong. This is the third option — a gate.

    `children/review-pr.sh:142` and `/standup` are the other two and are NOT
    gated here: the first is the frozen V1 fleet, the second is a prompt file,
    and both are surfaced for Phase 4's fleet-wide sweep.

    THE COMPARISON IS (pattern, flags), AND THE FLAGS HALF IS NOT DECORATION.
    The first version of this gate compared `.pattern` alone, which reads only
    the axis a reader is looking at while the semantics live on both. Every pair
    in the table depends on its flags: `PR_REVIEW_BLOCK`/`FENCE` need `DOTALL`
    so a block body may span lines, `_FINDING_ITEM`/`FINDING_ENTRY` need
    `MULTILINE|DOTALL` for the `^` anchor and the lookahead. Drop `DOTALL` on
    ONE side and the pattern strings still compare equal — while `(.*?)` stops
    at the first newline, every finding body reads empty, and every
    `disposition:` resolves to `""`. That is the gate's own stated failure —
    two readers attributing dispositions differently with both suites green —
    reachable through the one axis the gate did not read.
    """
    module = _load_replay_module()
    ours, theirs = getattr(helper, helper_name), getattr(module, replay_name)
    assert (ours.pattern, ours.flags) == (theirs.pattern, theirs.flags), (
        f"the working-record shared parse is declared two ways again: "
        f"review_pr_helper.{helper_name} != replay_pr_review_blocks.{replay_name} "
        f"— pattern differs: {ours.pattern != theirs.pattern}, "
        f"flags differ: {ours.flags != theirs.flags} "
        f"({ours.flags!r} vs {theirs.flags!r}) — the defect §6 exists to prevent"
    )


def test_the_shared_parse_ENUMERATION_is_complete() -> None:
    """A regex added to either reader is covered by the table or ruled out of it.

    WITHOUT THIS THE TABLE ABOVE ONLY EVER GATES WHAT SOMEBODY REMEMBERED. The
    measured failure was exactly that: two pairs gated, two pairs added in the
    same commit ungated and already divergent. A gate whose scope is a hand-kept
    list retires itself the moment it passes.
    """
    module = _load_replay_module()
    helper_gated = {h for h, _ in SHARED_WORKING_RECORD_PATTERNS}
    replay_gated = {r for _, r in SHARED_WORKING_RECORD_PATTERNS}

    helper_patterns = {n for n, v in vars(helper).items() if isinstance(v, re.Pattern)}
    replay_patterns = {n for n, v in vars(module).items() if isinstance(v, re.Pattern)}

    assert helper_patterns == helper_gated | HELPER_ONLY_PATTERNS, (
        f"review_pr_helper's regexes are no longer exactly the gated set plus "
        f"the declared one-sided ones — ungated: "
        f"{sorted(helper_patterns - helper_gated - HELPER_ONLY_PATTERNS)}, "
        f"stale: {sorted((helper_gated | HELPER_ONLY_PATTERNS) - helper_patterns)}. "
        f"Add the pair to SHARED_WORKING_RECORD_PATTERNS, or state why it is one-sided."
    )
    assert replay_patterns == replay_gated | REPLAY_ONLY_PATTERNS, (
        f"replay_pr_review_blocks' regexes are no longer exactly the gated set "
        f"plus the declared one-sided ones — ungated: "
        f"{sorted(replay_patterns - replay_gated - REPLAY_ONLY_PATTERNS)}, "
        f"stale: {sorted((replay_gated | REPLAY_ONLY_PATTERNS) - replay_patterns)}"
    )


def test_protocol_SS4s_reason_column_is_exactly_the_shipped_vocabulary() -> None:
    """§4's rule table is a SECOND DECLARATION of the abstention vocabulary.

    §6's one-declaration rule is written about the schema and the address, and
    the reason strings are neither — but the mechanism is identical and it has
    now fired twice on this component, both times with every test green:

    - `route(None)` reported `permission_denied` where §4's R2 row said
      `record_absent` (caught by the refine pass);
    - §4 asserted *"only the reason string distinguishes them"* for R1's two
      conditions while the code returned one string for both (caught by the
      review pass).

    BOTH WERE THE DOCUMENT AND THE CODE DISAGREEING, NOT EITHER BEING WRONG
    ALONE, and no check compared them. This is that check. It gates the
    VOCABULARY, not the row-to-rule mapping — a row moving between rules is a
    prose edit, but a reason string existing in one artifact and not the other
    means an operator is reading §4 for a bin the code never writes, or binning
    into one §4 does not document.
    """
    protocol = Path(__file__).resolve().parents[5] / "docs" / "standards" / \
        "exit-protocol.md"
    assert protocol.exists(), f"the protocol moved: {protocol}"

    # §4's rows are the only ones whose first cell is `**R<n>**`. The reason is
    # the 4th column, backticked, or an em-dash where the rule routes to a
    # non-abstaining outcome and carries no reason.
    rows = re.findall(
        r"^\|\s*\*\*R[0-9a-z]+\*\*\s*\|[^|]*\|[^|]*\|\s*([^|]*?)\s*\|",
        protocol.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    assert len(rows) >= 9, (
        f"§4's rule table did not parse — {len(rows)} rows found. The gate is "
        f"reporting on a table it did not read."
    )
    documented = {cell.strip("`") for cell in rows if cell != "—"}
    shipped = {member.value for member in er.UndeterminedReason}

    assert documented == shipped, (
        f"the protocol and the enum disagree about the abstention vocabulary — "
        f"documented but not shipped: {sorted(documented - shipped)}; shipped "
        f"but not documented: {sorted(shipped - documented)}. The computed arm's "
        f"rate is grouped by this field, so a reason the operator cannot look up "
        f"is a bin nobody can read."
    )


def test_parse_verdict_is_declared_exactly_once_in_the_whole_tree() -> None:
    """The merge-deciding parser has ONE body, and a third retype fails here.

    §6's own words: *"that is how `parse_verdict` came to be typed twice, and
    the copy that decided merges had zero tests."* Issue **#34** named both
    copies — `build_helper` and `review_pr_helper` — and was **closed on a
    half-fix**, with only `build_helper` re-exporting. The retype survived in
    the module whose shadow comparator exists to notice when two channels
    disagree, which made the comparator the divergence it was built to detect.

    SO THIS GATE IS AN AST SCAN OF THE TREE RATHER THAN TWO IDENTITY CHECKS.
    An identity check per known re-exporter closes the instances that were
    found; it says nothing about the third copy, and a third copy is exactly
    what #34's closure produced. Any `def parse_verdict` anywhere outside
    `routing.py` fails this — including one in a module nobody has written yet.
    """
    import ast

    repo_root = Path(__file__).resolve().parents[5]
    owner = repo_root / "scripts" / "workflows" / "temporal" / "modules" / \
        "assistant" / "routing.py"
    assert owner.exists(), f"the owning declaration moved: {owner}"

    # RELATIVE parts, not absolute: this repo's own worktrees live under
    # `.claude/`, so an absolute-path match skips every file when the test runs
    # from inside one — a scan that visits nothing and reports a clean tree.
    skip = {".git", "node_modules", "__pycache__", ".claude", ".venv"}
    definitions, scanned = [], 0
    for path in repo_root.rglob("*.py"):
        if skip & set(path.relative_to(repo_root).parts):
            continue
        scanned += 1
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        definitions.extend(
            path for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "parse_verdict"
        )

    assert scanned > 50, (
        f"the scan visited only {scanned} files from {repo_root} — the gate is "
        f"reporting on a tree it did not read"
    )
    assert definitions == [owner], (
        f"`parse_verdict` is declared {len(definitions)} times, in "
        f"{sorted(str(p.relative_to(repo_root)) for p in definitions)}. It has "
        f"exactly one owner ({owner.relative_to(repo_root)}) which carries the "
        f"fail-safe rationale and the LAST-match-wins rule; every other consumer "
        f"re-exports it. A second body stays green in its own tests while the "
        f"rule applied to the owner never reaches it — issue #34, twice."
    )


def test_every_consumer_of_parse_verdict_holds_the_owning_object() -> None:
    """Negative control's other half: re-export, not re-implementation.

    The AST gate above cannot see a copy assembled at runtime — a `lambda`, a
    `functools.partial`, a wrapper that re-derives the verdict. Identity is what
    makes "one declaration" mean the object and not merely the name.
    """
    from modules.assistant.build import build_helper

    assert helper.parse_verdict is routing.parse_verdict
    assert build_helper.parse_verdict is routing.parse_verdict


def test_the_shipped_prompt_asks_for_exactly_the_fields_the_parent_reads() -> None:
    """§6's last bullet: prompt-borne emission is part of the conformance surface.

    *"a check must verify the emit instruction still corresponds to the field the
    parent reads."* The record is MODEL-AUTHORED, so `disposition.md`'s Stage 6a
    table is a third statement of `CHILD_SCHEMA` — after the module and the
    protocol — and nothing bound them.

    The failure this catches is not a loud one. E2(c) measured that a schema the
    model cannot satisfy produces SILENCE on a clean run: exit 0, subtype
    success, no `structured_output`. So adding a required field to the schema
    without editing the prompt routes every conforming run to a human with no
    error naming the cause.
    """
    prompt = (Path(helper.__file__).resolve().parent / "prompts" / "disposition.md").read_text()
    # Scoped to Stage 6 as a whole, NOT to the 6a/6b heading that happened to
    # carry the table when this was written. The two sub-stages were SWAPPED on
    # 2026-08-09 — the verdict now prints first, because calling the tool is a
    # terminal action and a run died having emitted the record without ever
    # printing its verdict. This test failed on that swap while the property it
    # guards was untouched, which is the tell that it was bound to a heading
    # rather than to the field table.
    stage_6 = prompt.split("## Stage 6:")[1].split("\n## ")[0]
    asked = set(re.findall(r"^\| `([a-z_]+)` \|", stage_6, re.MULTILINE))
    declared = set(er.CHILD_SCHEMA["properties"])
    assert asked == declared, (
        f"the prompt and the schema disagree on the field list. Only asked for: "
        f"{sorted(asked - declared)}. Only declared: {sorted(declared - asked)}"
    )
    assert set(er.CHILD_SCHEMA["required"]) <= asked


# ---------------------------------------------------------------------------
# §10.1 rule 3 — PARENT-LEVEL PLACEMENT. Also a gate on the CLASS: it fails when
# a THIRD single-consumer module appears at the parent level, and equally when a
# declared deviation acquires its second consumer and the entry goes stale.
# ---------------------------------------------------------------------------

# Modules at `modules/assistant/` that are consumed by exactly ONE workflow
# folder, each a stated deviation from `temporal_standard.md` §10.1 rule 3 — *a
# module is promoted to the parent level IF AND ONLY IF more than one workflow
# uses it; the consumer count decides, never taste* — with the checkbox where the
# deviation expires.
#
# WHY A SET AND NOT A COMMENT IN A PHASE DOC. `phase4_fleet_migration.md:76`
# already carries the expiry ruling, and its own prose says why prose is not
# enough: *"an honest deviation becomes an unmarked violation the moment nobody
# is left who remembers it was one."* It named `exit_record.py` alone while a
# second module qualified, and no test could tell. This is the check that makes
# the omission loud.
SINGLE_CONSUMER_PARENT_MODULES = {
    # Phase 5, and the reason is an OUT-OF-TREE consumer this scan cannot see:
    # `scripts/helpers/measure/replay_convergence_predicate.py` loads it via
    # `importlib.util` from its path, because replaying the SHIPPED predicate is
    # the entire point of that tool and a pinned copy would validate itself.
    # Rule 3 counts workflow folders; a path-loader is invisible to it, so this
    # entry records a consumer that exists rather than an exemption.
    "convergence": "an out-of-tree path-loader; expires if that tool imports normally or is retired",
}

# `exit_record` WAS here and is gone: Phase 4 migrated no second consumer, its
# placement-expiry condition fired, and it moved to `review_pr/` on 2026-08-11.
# It had NO out-of-tree consumer -- checked, unlike the two greps before it that
# matched docstring prose and nearly produced the opposite answer twice.


def _workflow_folder_consumers(module_stem: str, assistant: Path) -> set[str]:
    """Which workflow folders under `assistant/` import `module_stem`.

    AST rather than a substring scan: `"import convergence" in text` matches a
    docstring, a comment, or `import convergence_helper`, and a placement gate
    that counts prose is a placement gate that reports whatever is written about
    the module rather than what depends on it.
    """
    # FACADE-MEDIATED SHARING IS STILL SHARING, and the folder scan cannot see
    # it. `assistant_activities` is imported by every workflow folder, so a
    # module it depends on is reachable from all of them — `resource_telemetry`
    # is used through `run_claude`, which is the single correct integration
    # point for it and deliberately not duplicated per folder.
    #
    # THIS DOES NOT WIDEN THE GATE. A module imported by no folder AND not by
    # the facade still counts zero and still fails; the positive control below
    # proves that. What it stops is the opposite error — recording a genuinely
    # shared module as a "deviation", which would put a false entry in a list
    # whose whole value is that its entries are true.
    facade = assistant / "assistant_activities.py"
    if facade.is_file() and module_stem != facade.stem:
        for node in ast.walk(ast.parse(facade.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and module_stem in {a.name for a in node.names}:
                # The folders that reach it, named truthfully — every folder
                # importing the facade can reach what the facade imports. A
                # synthetic "<facade>" token would have counted ONE and made a
                # universally-reachable module look single-consumer, which is
                # the opposite of the fact.
                return (_workflow_folder_consumers_direct(facade.stem, assistant)
                        | _workflow_folder_consumers_direct(module_stem, assistant))

    return _workflow_folder_consumers_direct(module_stem, assistant)


def _workflow_folder_consumers_direct(module_stem: str, assistant: Path) -> set[str]:
    """Workflow folders importing `module_stem` DIRECTLY."""
    consumers: set[str] = set()
    for folder in sorted(p for p in assistant.iterdir() if p.is_dir()):
        if folder.name.startswith("__") or folder.name == "prompts":
            continue
        for path in folder.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    names = {a.name for a in node.names}
                    if node.module == module_stem or module_stem in names:
                        consumers.add(folder.name)
                elif isinstance(node, ast.Import):
                    if any(a.name.split(".")[-1] == module_stem for a in node.names):
                        consumers.add(folder.name)
    return consumers


def test_the_placement_gate_still_fails_an_unshared_module(tmp_path: Path) -> None:
    """Positive control for the facade allowance above.

    Without this, widening the scan to follow the facade could quietly turn the
    gate into a permanent pass and nothing would signal that it stopped looking
    — which is the exact failure mode the deviation list exists to prevent.
    """
    (tmp_path / "assistant_activities.py").write_text("from . import something_else\n")
    (tmp_path / "orphan.py").write_text("x = 1\n")
    (tmp_path / "afolder").mkdir()
    (tmp_path / "afolder" / "w.py").write_text("from .. import assistant_activities\n")

    assert _workflow_folder_consumers("orphan", tmp_path) == set(), (
        "a module imported by neither the facade nor any folder must still count zero"
    )
    assert _workflow_folder_consumers("something_else", tmp_path) == {"afolder"}, (
        "a facade-imported module must report the folders that can REACH it"
    )


def test_every_parent_level_module_is_shared_or_a_DECLARED_deviation() -> None:
    """§10.1 rule 3's payoff is that parent level MEANS shared — checked, not assumed.

    The standard's own reason for the rule: *"anything at a parent level is
    shared by definition, so a reader never has to open a file to learn its
    scope."* Two single-consumer modules already sit there. That is defensible as
    a stated deviation and indefensible as an unmarked one, and the difference
    between the two is entirely whether something says so.

    THE GATE IS ON THE CLASS IN BOTH DIRECTIONS, which is what a checkbox in a
    phase doc cannot be:

    - a THIRD single-consumer module placed at the parent level fails here, even
      though `phase4_fleet_migration.md`'s checkbox names neither of the two;
    - a declared deviation that acquires a SECOND consumer also fails, because
      the deviation has expired on its own and an entry that outlives its reason
      is how a gate widens into a place to park an inconvenient module.

    It does NOT rule on where the modules should live — that is Phase 4's ruling
    and this test must not pre-empt it. It rules only that the count and the
    record agree.
    """
    assistant = _ASSISTANT
    modules = sorted(p.stem for p in assistant.glob("*.py")
                     if p.name != "__init__.py")
    assert len(modules) >= 3, (
        f"only {modules} found at {assistant} — the gate is reporting on a "
        f"directory it did not read"
    )

    counts = {m: _workflow_folder_consumers(m, assistant) for m in modules}
    single = {m for m, c in counts.items() if len(c) == 1}

    assert single == set(SINGLE_CONSUMER_PARENT_MODULES), (
        f"parent-level placement and its record have diverged. Single-consumer "
        f"and undeclared: "
        f"{ {m: sorted(counts[m]) for m in sorted(single - set(SINGLE_CONSUMER_PARENT_MODULES))} }"
        f" — each is an unmarked §10.1 rule-3 violation unless the deviation is "
        f"stated with where it expires. Declared but no longer single-consumer: "
        f"{ {m: sorted(counts[m]) for m in sorted(set(SINGLE_CONSUMER_PARENT_MODULES) - single)} }"
        f" — those deviations have expired on their own; remove the entry."
    )
    # And the modules that are NOT deviations really are shared, so the assertion
    # above is not satisfied by a scan that found no consumers anywhere.
    for module in modules:
        if module not in SINGLE_CONSUMER_PARENT_MODULES:
            assert len(counts[module]) > 1, (
                f"{module} has {sorted(counts[module])} consumers — the import "
                f"scan is not finding them"
            )


# ---------------------------------------------------------------------------
# R5b — REFERENCE IDENTITY. `phase4_fleet_migration.md` requirement 6: the PR URL
# survives the migration as a VALIDATED field, and the validation is an IDENTITY
# check rather than a shape check.
# ---------------------------------------------------------------------------

def test_a_record_naming_another_REPOSITORY_routes_to_the_human_arm() -> None:
    """The threat requirement 6 actually names, and the anchored pattern's blind spot.

    `https://github\\.com/[^\\s)]+/pull/(\\d+)`'s `[^\\s)]+` IS the owner/repo
    segment, so this URL passes it and yields `12`. That number then reaches
    `gh pr view`, `gh pr comment` and `--pr` on a downstream child that checks
    out and commits to that PR's branch — in a repository this dispatch was
    never pointed at. No adversarial child is needed: children are instructed to
    read prior PR comments, which routinely carry other PRs' URLs.
    """
    elsewhere = _record(completion_ref={
        "substrate": "github", "kind": "pull", "id": "67",
        "uri": "https://github.com/someone-else/other-repo/pull/67",
    })
    routed = er.route(_envelope(elsewhere), expected_run_id=RUN_ID,
                      expected_ref=EXPECTED_REF)
    assert routed.routed_outcome is er.RoutedOutcome.UNDETERMINED
    assert routed.undetermined_reason is er.UndeterminedReason.COMPLETION_REF_MISMATCH


def test_a_record_naming_another_PR_IN_THIS_REPO_routes_to_the_human_arm() -> None:
    """Same repo, wrong PR — the half a repo-only check would miss.

    A comparison that only pinned the owner/repo would accept a review attached
    to a different PR of ours, which is the more likely accident: the child is
    reading THIS repo's comment threads.
    """
    other_pr = _record(completion_ref={
        "substrate": "github", "kind": "pull", "id": "99",
        "uri": "https://github.com/owner/repo/pull/99",
    })
    routed = er.route(_envelope(other_pr), expected_run_id=RUN_ID,
                      expected_ref=EXPECTED_REF)
    assert routed.undetermined_reason is er.UndeterminedReason.COMPLETION_REF_MISMATCH


@pytest.mark.parametrize("field,wrong", [
    ("id", "99"),
    ("kind", "issue"),
    # `substrate` is NOT here, and that is a statement rather than an omission:
    # `CHILD_SCHEMA` closes its enum at `github`, so a wrong substrate is caught
    # by R3 as unparseable before R5b sees it. Listing it would assert the wrong
    # reason and hide which rule is actually doing the work.
])
def test_EACH_reference_field_is_compared_on_its_own(field: str, wrong: str) -> None:
    """MEASURED GAP, not a completeness ritual — the `id` comparison had no test.

    Mutating `_ref_matches` to compare only `substrate` and `kind` was predicted
    to turn two tests red and turned NONE red: every mismatch fixture moved the
    `id` and the `uri` together, so the `uri` comparison caught all of them and
    the `id` comparison was doing nothing observable.

    That is not academic. `completion_ref.id` is what the parent would hand to
    `gh` if a later consumer read the field directly instead of re-parsing the
    uri, and a record whose `id` and `uri` disagree with EACH OTHER is precisely
    the shape a model produces when it copies one of the two from a comment
    body. Each field is now moved alone, so each comparison has a test that
    fails when it is removed.
    """
    ref = dict(EXPECTED_REF)
    ref[field] = wrong
    routed = er.route(_envelope(_record(completion_ref=ref)),
                      expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    assert routed.undetermined_reason is er.UndeterminedReason.COMPLETION_REF_MISMATCH, (
        f"a record whose completion_ref.{field} is {wrong!r} while every other "
        f"field matches routed as though it were the record this run is about"
    )


def test_a_matching_reference_routes_NORMALLY() -> None:
    """The control. Without it a router that returned UNDETERMINED on every
    record would pass both tests above."""
    routed = er.route(_envelope(), expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    assert routed.routed_outcome is er.RoutedOutcome.MERGE
    assert routed.undetermined_reason is None


@pytest.mark.parametrize("uri", [
    "https://github.com/owner/repo/pull/67/",
    "https://github.com/owner/repo/pull/67/files",
    "see https://github.com/owner/repo/pull/67 — the PR under review",
])
def test_the_uri_compares_by_IDENTITY_and_not_byte_for_byte(uri: str) -> None:
    """A guard that fails on correct input is not a guard.

    A trailing slash, a `/files` suffix or a sentence around it are the SAME
    PULL REQUEST. Byte equality would route a correct, already-posted review to
    a human over formatting — and the cost of that is a ~40-minute review at
    real budget plus an operator's attention, spent on nothing.
    """
    routed = er.route(_envelope(_record(completion_ref={
        "substrate": "github", "kind": "pull", "id": "67", "uri": uri,
    })), expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    assert routed.routed_outcome is er.RoutedOutcome.MERGE, (
        f"{uri!r} names the PR under review and was rejected on formatting"
    )


def test_a_uri_that_is_not_a_pr_url_at_all_routes_to_the_human_arm() -> None:
    """FAIL-SAFE WHEN IT CANNOT PARSE, which is the direction the contract takes
    everywhere else. An unparseable reference is not a matching one."""
    routed = er.route(_envelope(_record(completion_ref={
        "substrate": "github", "kind": "pull", "id": "67", "uri": "not a url",
    })), expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    assert routed.undetermined_reason is er.UndeterminedReason.COMPLETION_REF_MISMATCH


def test_staleness_is_ruled_BEFORE_reference_identity() -> None:
    """R5 before R5b, and the two reasons must not share a bin.

    They answer different questions — *from which invocation* versus *about
    which record* — and the computed arm's instrument is `undetermined` GROUPED
    BY the reason. A record from a previous invocation of the SAME PR is a
    worktree-skew problem; one from this invocation naming ANOTHER PR is a child
    that attached its review to the wrong thing. Sending an operator to the
    wrong one of those is the whole cost of a shared bin, which this enum
    already argues three times.
    """
    both_wrong = _record(run_id="a-previous-invocation", completion_ref={
        "substrate": "github", "kind": "pull", "id": "99",
        "uri": "https://github.com/someone-else/other-repo/pull/99",
    })
    routed = er.route(_envelope(both_wrong), expected_run_id=RUN_ID,
                      expected_ref=EXPECTED_REF)
    assert routed.undetermined_reason is er.UndeterminedReason.RECORD_STALE, (
        "a record whose identity is unknown has no reference worth comparing"
    )


def test_the_mismatch_carries_the_ref_the_child_NAMED() -> None:
    """The payload an operator acts on. Knowing that R5b fired says the machinery
    stopped something; knowing WHICH record the child attached itself to is what
    tells them whether a wrong PR was nearly written to."""
    elsewhere = {"substrate": "github", "kind": "pull", "id": "67",
                 "uri": "https://github.com/someone-else/other-repo/pull/67"}
    routed = er.route(_envelope(_record(completion_ref=elsewhere)),
                      expected_run_id=RUN_ID, expected_ref=EXPECTED_REF)
    assert routed.completion_ref == elsewhere
    note = helper.completion_ref_mismatch_note(routed, EXPECTED_REF)
    assert note is not None and "someone-else/other-repo" in note
    assert helper.completion_ref_mismatch_note(
        er.route(_envelope(), expected_run_id=RUN_ID, expected_ref=EXPECTED_REF),
        EXPECTED_REF,
    ) is None, "the note must be silent when R5b did not fire"


def test_the_R5b_payload_REACHES_AN_OPERATOR_on_the_case_R5b_is_FOR(
        monkeypatch, tmp_path) -> None:
    """THE ORDERING, as a property. Every other R5b test calls `route()` or the
    note helper directly, and all of them were green while the note was
    unreachable in the one scenario it was written for.

    The scenario: a child attaches its review to a FOREIGN record and prints
    `VERDICT: MERGE`. R5b routes `undetermined`, which collapses to
    `HOLD - needs-assistance`, so the prose channel disagrees and `run_review`
    RAISES — above the notes block where the note used to be built. The
    operator got "could not be evaluated" and never the two references.
    """
    elsewhere = {"substrate": "github", "kind": "pull", "id": "67",
                 "uri": "https://github.com/someone-else/other-repo/pull/67"}
    with pytest.raises(RuntimeError) as exc:
        _review(monkeypatch, tmp_path,
                _record(run_id="@ISSUED@", completion_ref=elsewhere),
                "VERDICT: MERGE\n")
    message = str(exc.value)
    assert "completion_ref_mismatch" in message, "the raise did not come from R5b"
    assert "someone-else/other-repo" in message, (
        "the operator was told the channels disagreed and NOT which record the "
        "child attached itself to — the whole payload of R5b, lost to ordering"
    )


# The module-level functions `review_pr_workflow` carries, as an EXACT SET.
# Its docstring records a STATED DEVIATION — pure `ExitRecord`/assessment-to-
# string logic living in the orchestration layer, deferred on the trigger
# `phase4_fleet_migration.md` step 2 names — and the docstring's own count is
# what is supposed to make "extract three and leave two" unavailable.
_WORKFLOW_MODULE_FUNCTIONS = {
    "assemble_prompt",              # prompt assembly, not record-to-string
    "run_review",                   # the orchestration itself
    "_convergence_event",           # Phase 5, deferred
    "_convergence_notes",           # Phase 5, deferred
    "_read_thread_for_invariant",   # an activity call with a retry, not pure
    "_thread_unreadable_note",      # Phase 3, deferred
    "_assert_block_matches_record",  # Phase 3, deferred
    # NOT a record-to-string function and NOT deferred work: it writes the
    # run log's `parent_route` row, which is an ACTIVITY CALL with the
    # orchestration's own identifiers. It belongs to the layer that knows
    # `run_id`, the PR and the expected ref, and it exists at module level
    # rather than inline because BOTH the success path and the failure path
    # must run identical code — see its docstring and C-060.
    "_append_shadow_pair",
}


def test_the_workflow_layers_DEFERRED_SET_is_a_test_and_not_a_docstring_count() -> None:
    """A COUNT IN PROSE IS NOT A TRIGGER, which this repo has now measured twice.

    `review_pr_workflow`'s docstring names FIVE deferred pure functions so that
    the extraction, when its trigger fires, is atomic. Nothing enforced that: a
    sixth site added inline would not appear in the count, and the extraction
    would move five and leave one — which is the exact failure the count exists
    to prevent, and it nearly happened in Phase 4 (the positional-fallback note
    shipped inline before being moved into the helper).

    The same shape as `SINGLE_CONSUMER_PARENT_MODULES`: an EXACT SET, failing in
    both directions. A new function here must be a deliberate edit to this set,
    at which point whoever adds it decides whether it belongs in the helper.
    """
    import ast as _ast

    from modules.assistant.review_pr import review_pr_workflow as _wf
    path = Path(_wf.__file__)
    parsed = _ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    present = {n.name for n in parsed.body
               if isinstance(n, (_ast.FunctionDef, _ast.AsyncFunctionDef))}
    assert present == _WORKFLOW_MODULE_FUNCTIONS, (
        f"the workflow layer's function set moved: "
        f"added {sorted(present - _WORKFLOW_MODULE_FUNCTIONS)}, "
        f"removed {sorted(_WORKFLOW_MODULE_FUNCTIONS - present)}. If this is a "
        f"new pure record-to-string function, it belongs in `review_pr_helper` "
        f"— see the docstring's stated deviation and step 2's trigger. If it is "
        f"genuinely orchestration, add it here with a one-line reason."
    )


def test_the_parents_OWN_reference_is_validated_when_it_is_BUILT() -> None:
    """An unparseable EXPECTED ref is a PARENT fault and must not wear the
    child's label.

    `expected_completion_ref` interpolates `repo_slug` unchecked, so an empty or
    unexpected `gh repo view` reply yields `https://github.com//pull/67`, which
    `routing.PR_URL` correctly refuses. Without this check that parent-side bug
    reaches `_ref_matches`, fails to parse, returns False, and routes EVERY run
    of the dispatch to the human arm as `completion_ref_mismatch` — reporting
    the parent's own bug as the child naming a different record, which is the
    shared-bin defect `UndeterminedReason` argues against three times.
    """
    with pytest.raises(ValueError, match="not a github PR URL"):
        helper.expected_completion_ref("67", "")
    # The ceiling: a real slug still builds, and builds what R5b compares against.
    assert helper.expected_completion_ref("67", "owner/repo") == EXPECTED_REF


def test_expected_ref_None_states_that_the_caller_CANNOT_check() -> None:
    """`None` is a caller with no reference, not a caller opting out quietly.

    The parameter has no default precisely so this is written at the call site,
    and the gate below is what keeps the production caller from becoming one of
    these by accident.
    """
    elsewhere = _record(completion_ref={
        "substrate": "github", "kind": "pull", "id": "99",
        "uri": "https://github.com/someone-else/other-repo/pull/99",
    })
    routed = er.route(_envelope(elsewhere), expected_run_id=RUN_ID, expected_ref=None)
    assert routed.routed_outcome is er.RoutedOutcome.MERGE


def test_route_cannot_be_called_without_STATING_an_expected_ref() -> None:
    """A keyword with a default of None is a check that skips itself.

    Every rule in `exit_record` exists because a check that skips itself is
    indistinguishable from one that passed, and this parameter is the one most
    likely to acquire a convenience default at the second call site.
    """
    import inspect

    param = inspect.signature(er.route).parameters["expected_ref"]
    assert param.default is inspect.Parameter.empty, (
        "`expected_ref` acquired a default — a caller that cannot check identity "
        "must SAY SO at the call site, which is the only thing that makes the "
        "gate below meaningful"
    )
    with pytest.raises(TypeError):
        er.route(_envelope(), expected_run_id=RUN_ID)


def test_every_production_caller_of_route_states_its_expected_ref() -> None:
    """And the one that exists passes a real one, not None.

    THE GATE IS ON THE TREE, so a second parent added by a later phase fails
    here rather than silently inheriting the unchecked path. Phase 4's own
    ruling defers the other nine children, which is exactly the condition under
    which a rule with one caller rots unnoticed.
    """
    import ast as _ast

    tree_root = _MODULES
    callers: list[str] = []
    scanned = 0
    for path in sorted(tree_root.rglob("*.py")):
        scanned += 1
        parsed = _ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in _ast.walk(parsed):
            if not (isinstance(node, _ast.Call)
                    and isinstance(node.func, _ast.Attribute)
                    and node.func.attr == "route"):
                continue
            kwargs = {k.arg: k.value for k in node.keywords}
            assert "expected_ref" in kwargs, (
                f"{path.name}:{node.lineno} calls route() without stating an "
                f"expected_ref — the parameter has no default, so this is a "
                f"positional call that will break, or a different `route`"
            )
            value = kwargs["expected_ref"]
            assert not (isinstance(value, _ast.Constant) and value.value is None), (
                f"{path.name}:{node.lineno} passes expected_ref=None. A parent "
                f"that dispatched against a PR knows which one; passing None "
                f"there disables rule R5b for the only caller that has it."
            )
            callers.append(f"{path.name}:{node.lineno}")

    assert scanned > 20, f"the scan visited only {scanned} files — it read nothing"
    assert callers, "no production caller of route() was found — the scan is blind"


# ---------------------------------------------------------------------------
# The prompt is part of the conformance surface — requirement 3, the half that
# is about the DURABLE block rather than the typed record.
# ---------------------------------------------------------------------------

def _disposition_prompt() -> str:
    return (Path(helper.__file__).resolve().parent / "prompts" / "disposition.md").read_text()


def test_the_prompt_asks_for_the_run_nonce_the_parent_matches_blocks_BY() -> None:
    """A parser and a prompt are two artifacts, and this one binds them.

    `RUN_ID_IN_BLOCK` is shape-pinned to 32 lowercase hex characters. The prompt
    tells the child to copy `${RUN_ID}` verbatim and unquoted. If either moves —
    the prompt starts asking for it quoted, or the parent starts issuing a
    different nonce shape — nothing raises: the match simply never happens, the
    selection falls back to position, and the property this phase added goes
    quietly back to what it replaced.
    """
    prompt = _disposition_prompt()
    assert re.search(r"^\s*run_id:\s*\$\{RUN_ID\}", prompt, re.MULTILINE), (
        "the durable `pr_review:` block spec no longer asks for `run_id`; the "
        "parent's block selection has nothing to match on"
    )
    # The rendered article, matched by the shipped parser — not a hand-written
    # example of what it might look like.
    rendered = helper.render_prompt(
        prompt, pr_number="67", pr_branch="b", this_pass=1, prior_pass=0,
        headless_guard="g", run_id="0123456789abcdef0123456789abcdef",
    )
    assert helper.run_id_in_block(rendered) == "0123456789abcdef0123456789abcdef", (
        "the prompt's rendered `run_id:` line is not what RUN_ID_IN_BLOCK reads"
    )


def test_the_prompt_never_points_at_a_STAGE_THAT_DOES_NOT_EXIST() -> None:
    """The 6a/6b defect class, as a check rather than as a memory.

    `fb85c3e` swapped Stage 6's two halves — the verdict prints first, because a
    tool call is terminal and a run died having emitted the record and never
    printed its verdict. Two cross-references were not swapped with it: Stage 5
    told the child the record is emitted "in Stage 6a" (it is 6b), and 6a's own
    body said the verdict "must correspond to 6a" — pointing at itself. Both
    were live in the shipped prompt for a day.

    Neither is catchable by reading, and neither is loud: the child follows the
    surrounding instruction and the stale pointer just quietly stops meaning
    anything. This asserts every `Stage <n>` / `<n><letter>` reference resolves
    to a heading the file actually has.
    """
    prompt = _disposition_prompt()
    headings = set(re.findall(r"^#+\s*Stage (\d+[a-z]?)", prompt, re.MULTILINE))
    headings |= set(re.findall(r"^#+\s*(\d+[a-z])\s+—", prompt, re.MULTILINE))
    assert len(headings) >= 6, (
        f"only {sorted(headings)} parsed as stage headings — the gate is "
        f"reporting on a document it did not read"
    )
    referenced = set(re.findall(r"\bStage (\d+[a-z]?)\b", prompt))
    dangling = referenced - headings
    assert dangling == set(), (
        f"the prompt points at stage(s) {sorted(dangling)} that it does not "
        f"contain. Headings present: {sorted(headings)}."
    )


def test_the_stage_reference_check_can_FAIL() -> None:
    """Verified negative control for the DANGLING half.

    ITS FIXTURE IS ITS OWN, not the live prompt with one phrase swapped. The
    first version mutated a sentence out of `disposition.md`; a mutation run
    then edited that same sentence for a DIFFERENT control and turned this test
    red as collateral — one extra failure that looked like a second guard firing
    and was a fixture coupling. A control whose input can be changed by an
    unrelated edit reports on the edit rather than on the property.
    """
    fixture = (
        "## Stage 6: PRINT THEN EMIT\n"
        "### 6a — Print the verdict line\n"
        "correspond to the record you emit at Stage 6c\n"
        "### 6b — Call the tool\n"
    )
    headings = set(re.findall(r"^#+\s*Stage (\d+[a-z]?)", fixture, re.MULTILINE))
    headings |= set(re.findall(r"^#+\s*(\d+[a-z])\s+—", fixture, re.MULTILINE))
    referenced = set(re.findall(r"\bStage (\d+[a-z]?)\b", fixture))
    assert headings == {"6", "6a", "6b"}, headings
    assert referenced - headings == {"6c"}, (
        "the stage-reference check does not see a dangling reference"
    )


# Which sub-stage of Stage 6 owns which channel, identified by the thing it
# instructs rather than by its number — which is the point, since the numbers
# swapped. A reference to "the record you emit in Stage <n>" must name the stage
# that instructs the tool call; a reference to the verdict must name the other.
_STAGE_6_OWNERS = (
    ("StructuredOutput", "the typed record"),
    ("VERDICT: MERGE", "the verdict line"),
)


def _stage_6_sections() -> dict[str, str]:
    """`{"6a": body, "6b": body}` from the shipped prompt."""
    stage_6 = _disposition_prompt().split("## Stage 6:")[1].split("\n## ")[0]
    parts = re.split(r"^### (\d+[a-z]) —", stage_6, flags=re.MULTILINE)
    return dict(zip(parts[1::2], parts[2::2]))


def test_no_sub_stage_of_stage_6_POINTS_AT_ITSELF() -> None:
    """The defect that actually shipped, and the dangling check cannot see it.

    `fb85c3e` swapped 6a and 6b. Two cross-references did not move with it, and
    NEITHER was dangling — both named a stage that exists:

      * 6a's body said the verdict "must correspond to 6a", pointing at itself;
      * Stage 5 said the record is emitted "in Stage 6a", which is now 6b.

    A gate on unresolvable references is green on both. So this one is on the
    RELATION: a sub-stage may not cite itself, because the only reason to cite a
    stage from inside a stage is to point at the other channel.
    """
    offenders = [
        f"{name} cites itself" for name, body in _stage_6_sections().items()
        if re.search(rf"\b(?:Stage )?{name}\b", body)
    ]
    assert offenders == [], (
        f"{offenders} — a sub-stage citing its own number is the shape that "
        f"shipped when 6a and 6b were swapped: the sentence still reads as an "
        f"instruction and points at nothing useful"
    )


@pytest.mark.parametrize("marker,what", _STAGE_6_OWNERS)
def test_a_cross_channel_reference_names_the_stage_that_OWNS_that_channel(
    marker: str, what: str,
) -> None:
    """Bound to what each stage INSTRUCTS, not to its number — the numbers moved.

    This is the check that would have caught Stage 5's *"the typed exit record
    you emit in Stage 6a"* on the day `fb85c3e` landed: 6a stopped being the
    stage that instructs the tool call, and nothing said so.
    """
    sections = _stage_6_sections()
    owners = [name for name, body in sections.items() if marker in body]
    assert len(owners) == 1, (
        f"{marker!r} appears in {owners or 'no'} sub-stage(s) of Stage 6 — the "
        f"gate cannot say which one owns {what}"
    )
    owner = owners[0]
    prompt = _disposition_prompt()
    if what == "the typed record":
        cited = set(re.findall(r"typed exit record you emit in Stage (\d+[a-z])", prompt))
        # A SUBSET ASSERTION IS SATISFIED BY THE EMPTY SET, so the check below
        # reports clean the moment the prompt stops carrying the phrase it
        # reads — a rewording, not a deletion, and the wording HAS moved before
        # (`fb85c3e`, which this gate exists to catch). Pin the reading first:
        # the gate must fail because the reference is wrong, never because it
        # went looking and found nothing.
        assert cited, (
            "the prompt no longer says 'the typed exit record you emit in "
            "Stage <N><x>' anywhere, so this gate read nothing and its subset "
            "assertion below passes vacuously. If the sentence was reworded, "
            "move this pattern with it; if the cross-reference was deleted on "
            "purpose, delete this gate and say so."
        )
        assert cited <= {owner}, (
            f"the prompt says the record is emitted in Stage {sorted(cited)} "
            f"while Stage {owner} is the one that instructs the tool call"
        )


# ---------------------------------------------------------------------------
# The run nonce, end to end — `phase4_fleet_migration.md` step 2's third
# checkbox: select this pass's block by identity rather than by position.
# ---------------------------------------------------------------------------

def test_a_later_foreign_block_does_NOT_become_this_passs_block(monkeypatch, tmp_path) -> None:
    """THE RACE THE NONCE CLOSES, and the reason it needed a schema field.

    A third party posting a fenced `pr_review:` example between the child's
    comment and the parent's read is not a pass. Under positional selection the
    parent takes the LAST block, compares this pass's typed record against the
    stranger's findings, and hard-fails a review that is already posted and
    already routed — a ~40-minute run at real budget destroyed by someone else's
    comment. Ordering could never see the difference; the nonce can.

    The foreign block carries a DIFFERENT finding set on purpose. Were it
    identical, the invariant would pass under both selections and the fixture
    would be symmetric under the defect — proving nothing.
    """
    foreign = ("pr_review:\n  pr: 67\n  findings:\n"
               "    - id: someone-elses-finding\n      disposition: hold\n")
    from modules.assistant.review_pr.review_pr_helper import ReviewInput
    fake = _FakeWorkflow(_record(run_id="@ISSUED@"), "VERDICT: MERGE\n",
                         block_carries_nonce=True, after_blocks=(foreign,))
    wf = fake.install(monkeypatch, tmp_path)
    result = wf.run_review(ReviewInput(pr_number="67"), tmp_path)

    assert result.verdict is routing.Verdict.MERGE
    assert not any("selected BY POSITION" in n for n in result.notes), (
        "the block carried the nonce and the parent still fell back to position"
    )


def test_the_SAME_fixture_fails_when_the_nonce_is_not_echoed(monkeypatch, tmp_path) -> None:
    """The discriminator for the test above — one variable changed, nothing else.

    Identical thread, identical record, identical prose. The only difference is
    that this pass's durable block does not carry the nonce, so the selection
    falls back to position and picks the stranger's block. The invariant then
    raises on a finding set that was never this pass's.

    Predicted before running: exactly this one test goes red if the fallback is
    removed, and exactly the test above goes red if the nonce match is removed.
    """
    foreign = ("pr_review:\n  pr: 67\n  findings:\n"
               "    - id: someone-elses-finding\n      disposition: hold\n")
    from modules.assistant.review_pr.review_pr_helper import ReviewInput
    fake = _FakeWorkflow(_record(run_id="@ISSUED@"), "VERDICT: MERGE\n",
                         block_carries_nonce=False, after_blocks=(foreign,))
    wf = fake.install(monkeypatch, tmp_path)
    with pytest.raises(RuntimeError, match="disagree on findings"):
        wf.run_review(ReviewInput(pr_number="67"), tmp_path)




def test_the_positional_FALLBACK_says_so_in_the_operator_notes(monkeypatch, tmp_path) -> None:
    """A check that quietly stopped checking is indistinguishable from one that held.

    Every block in the archive predates the nonce, so the fallback is the shape
    a mid-thread PR hits at merge and it must not be silent. This is the
    ordinary pre-Phase-4 thread: one block, no nonce, correct findings — the
    review completes, and the note names the degradation.
    """
    result = _review(monkeypatch, tmp_path, _record(run_id="@ISSUED@"),
                     "VERDICT: MERGE\n")
    assert result.verdict is routing.Verdict.MERGE
    assert any("selected BY POSITION" in n for n in result.notes), (
        "the selection fell back to position and told nobody"
    )


def test_two_CONFLICTING_blocks_claiming_ONE_nonce_is_refused() -> None:
    """One run has one rendering, and choosing between two DIFFERENT ones is not
    this code's job. Resolving by position would be the positional inference
    wearing the nonce's name — the identity check reporting a decision it did
    not make.
    """
    nonce = "0123456789abcdef0123456789abcdef"
    one = f"pr_review:\n  run_id: {nonce}\n  verdict: MERGE\n"
    other = f"pr_review:\n  run_id: {nonce}\n  verdict: HOLD\n"
    with pytest.raises(RuntimeError, match="DIFFERING"):
        helper.this_pass_block([one, other], nonce)


def test_two_IDENTICAL_blocks_claiming_one_nonce_resolve_SILENTLY() -> None:
    """A retried `gh pr comment` must not destroy the review it succeeded at.

    THE CASE IS REACHABLE AND BENIGN: `gh pr comment` timing out at the network
    layer *after* the server accepted it, and the child retrying, leaves two
    byte-identical renderings of one run. The first version of this rule raised
    on any duplicate nonce — which would have destroyed a correct,
    already-posted, already-routed review over two copies of one answer, the
    exact loss `_this_pass_index`'s no-nonce fallback exists to refuse. There is
    no inference to get wrong when the candidates are identical.

    THE INDEX IS THE FIRST MATCH, and the complement is what makes that matter:
    `prior_pass_blocks` is `window[:index]`, so selecting the LATER duplicate
    would put the earlier one into the convergence history as a phantom prior
    pass — every id in it would read as restated, which is the perfectly
    conforming, perfectly stalled loop `convergence_history` warns about.
    """
    nonce = "0123456789abcdef0123456789abcdef"
    prior = "pr_review:\n  run_id: ffffffffffffffffffffffffffffffff\n"
    stamped = f"pr_review:\n  run_id: {nonce}\n  verdict: MERGE\n"
    window = [prior, stamped, stamped]
    assert helper.this_pass_block(window, nonce) == stamped
    assert helper.this_pass_selected_by_identity(window, nonce) is True
    assert helper.prior_pass_blocks(window, nonce) == (prior,), (
        "the later duplicate leaked into the prior-pass history as a phantom pass"
    )


# ---------------------------------------------------------------------------
# C-060 — the instrument could not see the runs that mattered.
# ---------------------------------------------------------------------------


def test_the_pair_is_RECORDED_when_the_completion_gate_kills_the_run(monkeypatch, tmp_path):
    """The typed record succeeded, the prose channel did not, and the run died.

    THE SHAPE THAT WENT UNRECORDED. `run-claude.sh` fails a run whose final
    result carries no PR URL — and the PR URL is printed by the PROSE channel.
    `run_claude` raises, so this parent's recording code never ran, and
    `channels_agree` could only ever be written on runs where the channel it
    exists to RETIRE had already succeeded. Every run where the typed record
    outperformed prose was structurally invisible, so the metric could only
    ever look like agreement. More runs do not fix a biased instrument.

    MEASURED: Phase 3's run set was nine dispatches and the instrument recorded
    eight. The ninth is this shape — a valid typed record and no prose
    `VERDICT:` line — and it is the single most informative run in the set.

    The row must exist, and it must say the channels DISAGREED. A missing row
    and an agreeing row are the two wrong answers.
    """
    from modules.assistant.review_pr.review_pr_helper import ReviewInput
    from modules.assistant.review_pr import review_pr_activities as act

    rows: list[dict] = []
    fake = _FakeWorkflow(_record(run_id="@ISSUED@"), "")   # valid record, NO prose verdict
    wf = fake.install(monkeypatch, tmp_path)
    monkeypatch.setattr(wf._shared, "append_parent_route",
                        lambda _log, row: rows.append(row))

    def _gate_fails(prompt, *a, **k):
        fake.run_id = _nonce_in(prompt)
        raise RuntimeError("review-pr FAILED (exit 1). completion pattern not found")

    monkeypatch.setattr(act, "run_disposition", _gate_fails)

    with pytest.raises(RuntimeError, match="completion pattern not found"):
        wf.run_review(ReviewInput(pr_number="67"), tmp_path)

    assert rows, (
        "the run died and NOTHING was recorded — this is exactly C-060: the pair "
        "is only ever written when the prose channel already worked, so the "
        "agreement metric is conditioned on the channel it exists to retire"
    )
    row = rows[-1]
    assert row["channels_agree"] is False, (
        f"recorded channels_agree={row['channels_agree']!r} on a run where the "
        f"prose channel produced no verdict at all — an absent prose verdict is "
        f"a DISAGREEMENT, not an agreement"
    )
    assert row["run_id"] == fake.run_id, "the row is not joinable to the run that produced it"


def test_the_completion_gate_still_FAILS_the_run(monkeypatch, tmp_path):
    """THE CONTROL. Recording the evidence must not rescue the run.

    Exit 0 must mean done. Buying a datapoint by swallowing the failure would
    trade a real guarantee for a number — so the pair is recorded AND the
    original error still reaches the caller, unchanged.
    """
    from modules.assistant.review_pr.review_pr_helper import ReviewInput
    from modules.assistant.review_pr import review_pr_activities as act

    fake = _FakeWorkflow(_record(run_id="@ISSUED@"), "")
    wf = fake.install(monkeypatch, tmp_path)
    monkeypatch.setattr(wf._shared, "append_parent_route", lambda *a, **k: None)

    def _boom(prompt, *a, **k):
        fake.run_id = _nonce_in(prompt)
        raise RuntimeError("the original failure, verbatim")

    monkeypatch.setattr(act, "run_disposition", _boom)

    with pytest.raises(RuntimeError, match="the original failure, verbatim"):
        wf.run_review(ReviewInput(pr_number="67"), tmp_path)


def test_an_UNREADABLE_log_does_not_stack_a_second_failure(monkeypatch, tmp_path):
    """A log too damaged to read a pair from is a missing row, never a new error.

    The failure path runs when something already went wrong. If recording threw,
    the operator would be shown a parsing error instead of the real cause.
    """
    from modules.assistant.review_pr.review_pr_helper import ReviewInput
    from modules.assistant.review_pr import review_pr_activities as act

    fake = _FakeWorkflow(_record(run_id="@ISSUED@"), "")
    wf = fake.install(monkeypatch, tmp_path)

    def _unreadable(*a, **k):
        raise ValueError("log is truncated")

    monkeypatch.setattr(wf._shared, "result_event", _unreadable)

    def _boom(prompt, *a, **k):
        fake.run_id = _nonce_in(prompt)
        raise RuntimeError("the original failure")

    monkeypatch.setattr(act, "run_disposition", _boom)

    with pytest.raises(RuntimeError, match="the original failure"):
        wf.run_review(ReviewInput(pr_number="67"), tmp_path)

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

import json
import re
from pathlib import Path

import pytest

from modules.assistant import exit_record as er
from modules.assistant import routing
from modules.assistant.review_pr import review_pr_helper as helper


RUN_ID = "aaaabbbbccccdddd"


def _record(**overrides) -> dict:
    """A record that routes cleanly. Every test below mutates ONE thing."""
    base = {
        "schema_version": er.SCHEMA_VERSION,
        "run_id": RUN_ID,
        "outcome": "merge",
        "completion_ref": {
            "substrate": "github", "kind": "pull", "id": "67",
            "uri": "https://github.com/owner/repo/pull/67",
        },
        "findings": [{"id": "a-stable-slug", "disposition": "fixed"}],
    }
    base.update(overrides)
    return base


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
    routed = er.route(_envelope(), expected_run_id=RUN_ID)
    assert routed.routed_outcome is er.RoutedOutcome.MERGE
    assert routed.undetermined_reason is None
    assert routed.outcome is er.Outcome.MERGE
    assert helper.verdict_from_record(routed) is routing.Verdict.MERGE


def test_a_hold_routes_on_its_sub_kind_not_on_hold_alone() -> None:
    """B6/P3/P5 branch on the sub-kind; `hold` alone does not route."""
    for kind, expected in (("redispatch", routing.Verdict.HOLD_REDISPATCH),
                           ("needs_ruling", routing.Verdict.HOLD_NEEDS_ASSISTANCE)):
        routed = er.route(
            _envelope(_record(outcome="hold", hold_kind=kind)), expected_run_id=RUN_ID
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
    routed = er.route(_envelope(record), expected_run_id=RUN_ID)
    assert routed.routed_outcome is expected_route
    assert routed.undetermined_reason is expected_reason


def test_record_absent_routes_to_the_human_arm() -> None:
    """R2 — and the run it fires on did not necessarily die."""
    routed = er.route(_envelope(record=None), expected_run_id=RUN_ID)
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
    routed = er.route(clean, expected_run_id=RUN_ID)
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
    routed = er.route(_envelope(_record(**mutation)), expected_run_id=RUN_ID)
    assert routed.routed_outcome is er.RoutedOutcome.UNDETERMINED
    assert routed.undetermined_reason is er.UndeterminedReason.RECORD_UNPARSEABLE


def test_a_missing_required_top_level_field_is_unparseable() -> None:
    record = _record()
    del record["run_id"]
    routed = er.route(_envelope(record), expected_run_id=RUN_ID)
    assert routed.undetermined_reason is er.UndeterminedReason.RECORD_UNPARSEABLE


def test_record_stale_routes_to_the_human_arm() -> None:
    """R5 — a WELL-FORMED record from a different invocation.

    This is the case a first-invocation-only test passes despite: the record
    validates, its version is supported, and every field is present. Only the
    identity comparison distinguishes it, and only because the parent issued the
    nonce rather than reading one out of the record.
    """
    routed = er.route(_envelope(_record(run_id="a-previous-invocation")),
                      expected_run_id=RUN_ID)
    assert routed.routed_outcome is er.RoutedOutcome.UNDETERMINED
    assert routed.undetermined_reason is er.UndeterminedReason.RECORD_STALE


def test_unknown_schema_version_routes_to_the_human_arm() -> None:
    """R4 — parses cleanly, means something else."""
    routed = er.route(_envelope(_record(schema_version="99")), expected_run_id=RUN_ID)
    assert routed.routed_outcome is er.RoutedOutcome.UNDETERMINED
    assert routed.undetermined_reason is er.UndeterminedReason.SCHEMA_VERSION_UNKNOWN


def test_an_unknown_version_is_ruled_before_identity() -> None:
    """R4 sits before R5, and the ordering is asserted rather than assumed.

    A record with BOTH defects must report the version, because a record whose
    version is unknown has no guaranteed typing and its `run_id` is not yet a
    value one may compare. Swap the two rules and this goes red.
    """
    routed = er.route(_envelope(_record(schema_version="99", run_id="other")),
                      expected_run_id=RUN_ID)
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
    routed = er.route(_envelope(denials=[denial]), expected_run_id=RUN_ID)
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
    routed = er.route(envelope, expected_run_id=RUN_ID)
    assert routed.undetermined_reason is er.UndeterminedReason.PERMISSION_DENIED


def test_an_absent_denials_key_is_not_read_as_an_empty_list() -> None:
    """The contract must be total over its OWN inputs, not just over the record.

    "I could not check whether the safety control fired" gets the same ROUTING
    as "it fired" and a DIFFERENT REASON — see the sibling test below for why
    the difference is the instrument rather than a nicety.
    """
    envelope = _envelope()
    del envelope["permission_denials"]
    routed = er.route(envelope, expected_run_id=RUN_ID)
    assert routed.routed_outcome is er.RoutedOutcome.UNDETERMINED
    assert routed.undetermined_reason is er.UndeterminedReason.DENIALS_UNREADABLE


def test_a_denials_key_that_is_not_a_list_is_unreadable_rather_than_a_denial() -> None:
    """Total one level up from the entries: the key's own TYPE can be wrong.

    A CLI that changed `permission_denials` from a list to an object or a count
    lands here. It is the unreadable case, not the fired case — the parent could
    not check, and saying it fired would be an assertion about a control that
    was never read.
    """
    routed = er.route(_envelope(denials={"count": 0}), expected_run_id=RUN_ID)
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

    a = er.route(unreadable, expected_run_id=RUN_ID)
    b = er.route(fired, expected_run_id=RUN_ID)

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
    routed = er.route(_envelope(denials=["Bash"]), expected_run_id=RUN_ID)
    assert routed.undetermined_reason is er.UndeterminedReason.PERMISSION_DENIED
    assert len(routed.permission_denials) == 1, "an unreadable entry is still an entry"


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
    routed = er.route(None, expected_run_id=RUN_ID)
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
    routed = er.route(_envelope(_record(outcome="hold")), expected_run_id=RUN_ID)
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
    routed = er.route(_envelope(denials=[denial]), expected_run_id=RUN_ID)
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
        expected_run_id=RUN_ID,
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


def test_the_kind_one_reference_is_not_typed_as_a_url() -> None:
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

class _FakeWorkflow:
    """The `run_review` collaborators, replaced at their real boundaries.

    Nothing here fakes `route` or `parse_verdict` — those are the code under
    test. What is faked is the I/O: `gh`, the worktree, the model invocation and
    the log the record arrives in.
    """

    # The durable block the child is presumed to have posted. Default renders
    # the same one finding `_record()` carries — id AND disposition, because the
    # invariant compares pairs — so it holds unless a test deliberately breaks it.
    DEFAULT_BLOCK = ("pr_review:\n  pr: 67\n  findings:\n"
                     "    - id: a-stable-slug\n      disposition: fixed\n")

    def __init__(self, record: dict | None, prose: str, denials: list | None = None,
                 block: str | None = DEFAULT_BLOCK, prior_blocks: int = 0,
                 posts_block: bool = True):
        self.record = record
        self.prose = prose
        self.denials = denials if denials is not None else []
        self.block = block
        self.run_id: str | None = None
        # THE THREAD IS STATEFUL, and modelling that is the point. The invariant
        # asks whether THIS pass posted a block, so a fake returning one constant
        # count could not express "pass 2 ran and posted nothing" — which is the
        # case the invariant exists to catch and the case it used to pass.
        self.prior_blocks = prior_blocks
        self.posts_block = posts_block
        self.ran = False

    def install(self, monkeypatch, tmp_path: Path):
        from modules.assistant.review_pr import review_pr_activities as act
        from modules.assistant.review_pr import review_pr_workflow as wf

        monkeypatch.setattr(act, "fetch_pr", lambda *a, **k: {"headRefName": "build/x"})
        monkeypatch.setattr(act, "count_prior_passes", lambda *a, **k: self._blocks())
        monkeypatch.setattr(act, "load_shared_block", lambda *a, **k: "guard")
        monkeypatch.setattr(wf._shared, "worktree_add",
                            lambda *a, **k: tmp_path / "pr-tree")
        monkeypatch.setattr(wf._shared, "claude_log_path",
                            lambda *a, **k: tmp_path / "run.jsonl")

        def _run(prompt, *a, **k):
            # The nonce is issued by the parent and reaches the child ONLY
            # through the prompt, so capturing it here is the same path the
            # real child reads it on. `prompt` is the REAL disposition.md
            # rendered, so this also proves `${RUN_ID}` is in the shipped prompt
            # and gets substituted — not just that the helper accepts a kwarg.
            self.run_id = _nonce_in(prompt)
            self.ran = True
            return ""

        monkeypatch.setattr(act, "run_disposition", _run)
        monkeypatch.setattr(act, "latest_pr_review_block", lambda *a, **k: self.block)
        monkeypatch.setattr(wf._shared, "result_event",
                            lambda *a, **k: self._envelope())
        monkeypatch.setattr(wf._shared, "assistant_text", lambda *a, **k: self.prose)
        return wf

    def _blocks(self) -> int:
        """Blocks on the thread now: one more once this pass posted its own."""
        return self.prior_blocks + (1 if self.ran and self.posts_block else 0)

    def _envelope(self) -> dict:
        event = {"type": "result", "subtype": "success",
                 "permission_denials": self.denials}
        if self.record is not None:
            record = dict(self.record)
            if record.get("run_id") == "@ISSUED@":
                record["run_id"] = self.run_id
            event["structured_output"] = record
        return event


def _nonce_in(prompt: str) -> str:
    """The 32-hex nonce `render_prompt` substituted into the prompt."""
    import re
    m = re.search(r"\b[0-9a-f]{32}\b", prompt)
    assert m, "the parent did not substitute a run_id into the prompt"
    return m.group(0)


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


def test_the_shadow_comparison_actually_fires(monkeypatch, tmp_path) -> None:
    """Mutate the typed record so the two channels disagree; assert the failure.

    This is the test the requirement names explicitly, and it is the one that
    proves the shadow is a protection rather than a decoration.
    """
    with pytest.raises(RuntimeError, match="exit-record disagreement"):
        _review(monkeypatch, tmp_path,
                _record(run_id="@ISSUED@", outcome="hold", hold_kind="redispatch"),
                "VERDICT: MERGE\n")


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


def test_a_denial_is_surfaced_without_its_command_line(monkeypatch, tmp_path) -> None:
    """R1 end to end, with the redaction holding across the whole path."""
    denial = {"tool_name": "Bash", "tool_use_id": "toolu_01CsEb",
              "tool_input": {"command": "sudo cat /etc/shadow"}}
    with pytest.raises(RuntimeError) as excinfo:
        _review(monkeypatch, tmp_path, _record(run_id="@ISSUED@"),
                "VERDICT: MERGE\n", denials=[denial])
    assert "permission_denied" in str(excinfo.value)
    assert "/etc/shadow" not in str(excinfo.value)


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


def test_a_thread_read_failure_is_reported_as_could_not_check(monkeypatch, tmp_path) -> None:
    """A flaky `gh` is not a disagreement between the two copies.

    Reporting it as one sends the operator to compare two documents that are
    fine. The distinction the module draws everywhere else — could-not-check
    versus a real finding — has to hold in the check's own error path too.
    """
    from modules.assistant.review_pr import review_pr_activities as act
    fake = _FakeWorkflow(_record(run_id="@ISSUED@"), "VERDICT: MERGE\n")
    wf = fake.install(monkeypatch, tmp_path)

    def _boom(*a, **k):
        raise RuntimeError("gh pr view failed: API rate limit exceeded")

    monkeypatch.setattr(act, "latest_pr_review_block", _boom)
    from modules.assistant.review_pr.review_pr_helper import ReviewInput
    with pytest.raises(RuntimeError, match="could not be CHECKED"):
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
# The Kind 1 ADDRESS — §6's rule covers it too, and this is the measured defect.
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

    modules = Path(er.__file__).resolve().parent
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


def _with_comments(monkeypatch, bodies: list[str]):
    """Replace `gh` at its own boundary; everything above it is the code under test."""
    from modules.assistant.review_pr import review_pr_activities as act
    monkeypatch.setattr(
        act._shared, "gh",
        lambda *a, **k: json.dumps({"comments": [{"body": b} for b in bodies]}),
    )
    return act


def test_count_prior_passes_no_longer_counts_a_mention(monkeypatch, tmp_path) -> None:
    """The consumer-side half of issue #68, at its own call site.

    `PR_REVIEW_BLOCK` being anchored is necessary and not sufficient — the
    counter has to USE it. This ran as `"pr_review:" in body` until this phase.
    """
    act = _with_comments(monkeypatch, [
        "## Post-Run Reflection\nThe `pr_review:` block spec was clear.",
        "```yaml\npr_review:\n  pr: 66\n  pass: 1\n```",
    ])
    assert act.count_prior_passes("66", tmp_path) == 1


def test_latest_pr_review_block_takes_the_LAST_one(monkeypatch, tmp_path) -> None:
    """§6.2's ordering rule: comment creation order, last wins.

    A correction pass reading the FIRST block would reconcile against a
    superseded record and not know it did.
    """
    act = _with_comments(monkeypatch, [
        "```yaml\npr_review:\n  pass: 1\n  findings:\n    - id: old\n```",
        "unrelated chatter mentioning pr_review: in passing",
        "```yaml\npr_review:\n  pass: 2\n  findings:\n    - id: new\n```",
    ])
    block = act.latest_pr_review_block("66", tmp_path)
    assert helper.finding_ids_in_block(block) == frozenset({"new"})


def test_latest_pr_review_block_is_None_on_a_fresh_pr(monkeypatch, tmp_path) -> None:
    """Negative control: a thread of mentions is a thread with no record."""
    act = _with_comments(monkeypatch, ["no block here", "pr_review: mentioned only"])
    assert act.latest_pr_review_block("66", tmp_path) is None


def test_the_archive_shape_that_produced_the_wrong_pass_number() -> None:
    """PR #66's actual shape: two reflections, then one block.

    The unanchored predicate counted 3 and the block was labelled `pass: 3`.
    It is pass 1.
    """
    comments = [
        "## Post-Run Reflection\nNo friction. The `pr_review:` block spec was clear.",
        "build-refine summary — the pr_review: key is the wire format, unchanged.",
        "```yaml\npr_review:\n  pr: 66\n  pass: 1\n```",
    ]
    assert sum(1 for c in comments if helper.PR_REVIEW_BLOCK.search(c)) == 1
    assert sum(1 for c in comments if "pr_review:" in c) == 3   # the defect, reproduced


# ---------------------------------------------------------------------------
# §6 — ONE DECLARATION. Both gates below are on the CLASS, not on the instance
# that was found: each one fails when a NEW second declaration appears, not only
# when the known one comes back.
# ---------------------------------------------------------------------------

# The Kind 1 shared parse, ENUMERATED rather than asserted one name at a time.
# A table because the failure this gates is *a pair that nobody added an
# assertion for*: the first version of this gate named two pairs and the two the
# same commit introduced went ungated and had already drifted (`\s` vs `[ \t]`),
# with both suites green. Adding a shared regex is now a row here, and
# `test_the_shared_parse_ENUMERATION_is_complete` fails until it is.
SHARED_KIND_ONE_PATTERNS = (
    ("PR_REVIEW_BLOCK", "FENCE"),
    ("_FINDING_ID", "FINDING_ID"),
    ("_FINDING_ITEM", "FINDING_ENTRY"),
    ("_DISPOSITION", "DISPOSITION"),
)

# Regexes that exist on ONE side only, with the reason. These are not shared
# parse — they read fields the other side has no consumer for — so pairing them
# would be inventing a coupling rather than gating one. Listed explicitly so
# that a genuinely shared regex cannot hide in the gap.
REPLAY_ONLY_PATTERNS = frozenset({
    "PASS", "ATTEMPT", "VERDICT", "CONVERGED",   # block-level measurement fields
    "CATEGORY",                                   # finding-level, measurement only
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


@pytest.mark.parametrize("helper_name,replay_name", SHARED_KIND_ONE_PATTERNS)
def test_the_kind_one_SHARED_PARSE_is_one_declaration_across_both_python_readers(
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
        f"the Kind 1 shared parse is declared two ways again: "
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
    helper_gated = {h for h, _ in SHARED_KIND_ONE_PATTERNS}
    replay_gated = {r for _, r in SHARED_KIND_ONE_PATTERNS}

    helper_patterns = {n for n, v in vars(helper).items() if isinstance(v, re.Pattern)}
    replay_patterns = {n for n, v in vars(module).items() if isinstance(v, re.Pattern)}

    assert helper_patterns == helper_gated, (
        f"review_pr_helper's regexes are no longer exactly the gated set — "
        f"ungated: {sorted(helper_patterns - helper_gated)}, "
        f"stale rows: {sorted(helper_gated - helper_patterns)}. Add the pair to "
        f"SHARED_KIND_ONE_PATTERNS, or state why it is one-sided."
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
    stage_6a = prompt.split("### 6a")[1].split("### 6b")[0]
    asked = set(re.findall(r"^\| `([a-z_]+)` \|", stage_6a, re.MULTILINE))
    declared = set(er.CHILD_SCHEMA["properties"])
    assert asked == declared, (
        f"the prompt and the schema disagree on the field list. Only asked for: "
        f"{sorted(asked - declared)}. Only declared: {sorted(declared - asked)}"
    )
    assert set(er.CHILD_SCHEMA["required"]) <= asked

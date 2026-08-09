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
    denial = {"tool_name": "Bash", "matched_rule": "sudo",
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
                                                "matched_rule": "sudo"}])
    routed = er.route(envelope, expected_run_id=RUN_ID)
    assert routed.undetermined_reason is er.UndeterminedReason.PERMISSION_DENIED


def test_an_absent_denials_key_is_not_read_as_an_empty_list() -> None:
    """The contract must be total over its OWN inputs, not just over the record.

    "I could not check whether the safety control fired" and "it fired" get the
    same treatment; only the reason string is for a human.
    """
    envelope = _envelope()
    del envelope["permission_denials"]
    routed = er.route(envelope, expected_run_id=RUN_ID)
    assert routed.undetermined_reason is er.UndeterminedReason.PERMISSION_DENIED


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
    """
    denial = {"tool_name": "Bash", "matched_rule": "sudo",
              "tool_input": {"command": "sudo ls /root/.ssh"}}
    routed = er.route(_envelope(denials=[denial]), expected_run_id=RUN_ID)
    assert routed.permission_denials == ({"tool_name": "Bash", "matched_rule": "sudo"},)
    assert "sudo ls /root/.ssh" not in json.dumps(routed.permission_denials)


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
    denial = {"tool_name": "Bash", "matched_rule": "sudo",
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


def test_the_kind_one_ADDRESS_is_one_declaration_across_both_python_readers() -> None:
    """§6 covers the record's schema AND ITS ADDRESS, and the address is the
    measured half — three incompatible declarations wrote a wrong durable
    `pass:` onto 2 of 8 archived PRs (issue #68).

    This PR shipped a mechanical gate for the VOCABULARY half and none for the
    address, leaving the exact defect §6 was widened for un-gated in the exact
    place it was measured. Two Python declarations survive by design:
    `review_pr_helper` (the workflow) and `replay_pr_review_blocks` (the
    measurement tool that reads the fleet from outside it, so importing across
    that boundary would invert the dependency). Coupling them by IMPORT is
    wrong; leaving them free to drift silently is also wrong. This is the third
    option — a gate, using the same technique the shipped-jq tests use.

    `children/review-pr.sh:142` and `/standup` are the other two and are NOT
    gated here: the first is the frozen V1 fleet, the second is a prompt file,
    and both are surfaced for Phase 4's fleet-wide sweep.
    """
    import importlib.util

    replay = Path(__file__).resolve().parents[4] / "helpers" / "measure" / \
        "replay_pr_review_blocks.py"
    assert replay.exists(), f"the second declaration moved: {replay}"
    spec = importlib.util.spec_from_file_location("_replay", replay)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert helper.PR_REVIEW_BLOCK.pattern == module.FENCE.pattern, (
        "the Kind 1 block marker is declared two ways again — the defect §6's "
        "address half exists to prevent"
    )
    assert helper._FINDING_ID.pattern == module.FINDING_ID.pattern


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

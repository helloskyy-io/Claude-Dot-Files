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
    assert routed.needs_human is False


def test_a_hold_routes_on_its_sub_kind_not_on_hold_alone() -> None:
    """B6/P3/P5 branch on the sub-kind; `hold` alone does not route."""
    for kind, expected_human in (("redispatch", False), ("needs_ruling", True)):
        routed = er.route(
            _envelope(_record(outcome="hold", hold_kind=kind)), expected_run_id=RUN_ID
        )
        assert routed.routed_outcome is er.RoutedOutcome.HOLD
        assert routed.hold_kind is er.HoldKind(kind)
        assert routed.needs_human is expected_human


def test_record_absent_routes_to_the_human_arm() -> None:
    """R2 — and the run it fires on did not necessarily die."""
    routed = er.route(_envelope(record=None), expected_run_id=RUN_ID)
    assert routed.routed_outcome is er.RoutedOutcome.UNDETERMINED
    assert routed.undetermined_reason is er.UndeterminedReason.RECORD_ABSENT
    assert routed.needs_human


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
    assert routed.routed_outcome is not er.RoutedOutcome.MERGE


def test_an_absent_denials_key_is_not_read_as_an_empty_list() -> None:
    """The contract must be total over its OWN inputs, not just over the record.

    "I could not check whether the safety control fired" and "it fired" get the
    same treatment; only the reason string is for a human.
    """
    envelope = _envelope()
    del envelope["permission_denials"]
    routed = er.route(envelope, expected_run_id=RUN_ID)
    assert routed.undetermined_reason is er.UndeterminedReason.PERMISSION_DENIED


def test_no_result_event_at_all_routes_to_the_human_arm() -> None:
    """A log with no `result` event. No event implies no key."""
    routed = er.route(None, expected_run_id=RUN_ID)
    assert routed.routed_outcome is er.RoutedOutcome.UNDETERMINED


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
    # the same one finding `_record()` carries, so the invariant holds unless a
    # test deliberately breaks it.
    DEFAULT_BLOCK = "pr_review:\n  pr: 67\n  findings:\n    - id: a-stable-slug\n"

    def __init__(self, record: dict | None, prose: str, denials: list | None = None,
                 block: str | None = DEFAULT_BLOCK):
        self.record = record
        self.prose = prose
        self.denials = denials if denials is not None else []
        self.block = block
        self.run_id: str | None = None

    def install(self, monkeypatch, tmp_path: Path):
        from modules.assistant import assistant_activities as shared
        from modules.assistant.review_pr import review_pr_activities as act
        from modules.assistant.review_pr import review_pr_workflow as wf

        monkeypatch.setattr(act, "fetch_pr", lambda *a, **k: {"headRefName": "build/x"})
        monkeypatch.setattr(act, "count_prior_passes", lambda *a, **k: 0)
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
            return ""

        monkeypatch.setattr(act, "run_disposition", _run)
        monkeypatch.setattr(act, "latest_pr_review_block", lambda *a, **k: self.block)
        monkeypatch.setattr(wf._shared, "result_event",
                            lambda *a, **k: self._envelope())
        monkeypatch.setattr(wf._shared, "assistant_text", lambda *a, **k: self.prose)
        return wf

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
            block=_FakeWorkflow.DEFAULT_BLOCK):
    from modules.assistant.review_pr.review_pr_helper import ReviewInput
    fake = _FakeWorkflow(record, prose, denials, block)
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
    block = _FakeWorkflow.DEFAULT_BLOCK + "    - id: an-invented-finding\n"
    with pytest.raises(RuntimeError, match="Only in the block"):
        _review(monkeypatch, tmp_path, _record(run_id="@ISSUED@"), "VERDICT: MERGE\n",
                block=block)


def test_a_missing_block_fails_loud(monkeypatch, tmp_path) -> None:
    """The typed half landed and the durable half did not.

    This is arrangement A's characteristic failure: the outcome survives and its
    reasoning does not.
    """
    with pytest.raises(RuntimeError, match="no\n?\\s*`?pr_review:`? block"):
        _review(monkeypatch, tmp_path, _record(run_id="@ISSUED@"), "VERDICT: MERGE\n",
                block=None)


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

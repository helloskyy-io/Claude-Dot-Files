"""What *owes a ruling* means, per store — the judgement this phase adds.

Each test pins one of the five definitions AND its negative half, because a
predicate that says yes to everything is indistinguishable from one that works
until the day something is finally ruled on.

**The field-state trichotomy is asserted directly.** A §4 extension field can be
present-and-set, present-and-blank, or absent from the file entirely, and the
operator ruled on 2026-09-02 that the third must never be coerced onto the
second: absent is a conformance defect the reader already reports, and rendering
it as an ordinary blank hides the defect the page exists to expose.
"""

from __future__ import annotations

import pytest

from planning_ui.decisions import rules
from planning_ui.plan_extractor.tracked import TrackedItem


def item(store: str, **fields: str) -> TrackedItem:
    return TrackedItem(store=store, path=f"tracked/{store}/X-00000000.md", fields=dict(fields))


# ---------------------------------------------------------------------------
# The three field states are never conflated
# ---------------------------------------------------------------------------
def test_absent_blank_and_set_are_three_distinct_states():
    present = item("candidates", decision="ship")
    blank = item("candidates", decision="   ")
    absent = item("candidates")

    assert rules.field_state(present, "decision") == "ship"
    assert rules.field_state(blank, "decision") == rules.BLANK
    assert rules.field_state(absent, "decision") == rules.ABSENT

    # Both unset states owe the same ruling…
    assert rules.unset(rules.BLANK) and rules.unset(rules.ABSENT)
    # …and describe themselves differently, so the conformance defect survives.
    assert "absent from the file" in rules.describe("decision", rules.ABSENT)
    assert "blank" in rules.describe("decision", rules.BLANK)
    assert rules.describe("decision", rules.ABSENT) != rules.describe("decision", rules.BLANK)


# ---------------------------------------------------------------------------
# Table 1 · candidates — three orthogonal asks of two actors
# ---------------------------------------------------------------------------
def test_a_blank_decision_owes_triage_and_only_triage_candidates_may_rule_it():
    owed = rules.candidate_owed(item("candidates", decision="", size="", component="dev/x"))
    assert [o.kind for o in owed] == ["triage"]
    assert owed[0].actor == "triage-candidates"


def test_an_absent_decision_owes_triage_too_and_says_which_state_it_is_in():
    owed = rules.candidate_owed(item("candidates", component="dev/x"))
    assert [o.kind for o in owed] == ["triage"]
    assert "absent from the file" in owed[0].reason


def test_ship_with_no_size_owes_sizing():
    owed = rules.candidate_owed(item("candidates", decision="ship", size="", component="dev/x"))
    assert [o.kind for o in owed] == ["sizing"]
    assert owed[0].actor == "triage-candidates"


def test_a_blank_component_owes_placement_and_only_the_operator_may_fill_it():
    owed = rules.candidate_owed(item("candidates", decision="ship", size="M", component=""))
    assert [o.kind for o in owed] == ["placement"]
    assert owed[0].actor == "operator"


def test_one_item_can_owe_two_rulings_from_two_actors():
    """Collapsing them into one yes/no tells a reader nothing about what to do."""
    owed = rules.candidate_owed(item("candidates", decision="", size="", component=""))
    assert {o.kind for o in owed} == {"triage", "placement"}
    assert {o.actor for o in owed} == {"triage-candidates", "operator"}


def test_a_fully_ruled_candidate_owes_nothing():
    assert rules.candidate_owed(item("candidates", decision="ship", size="M", component="dev/x")) == []


# ---------------------------------------------------------------------------
# Table 2 · issues — status: open and nothing else
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("status,owes", [("open", True), ("resolved", False), ("rejected", False)])
def test_an_issue_owes_disposition_only_while_open(status: str, owes: bool):
    assert bool(rules.issue_owed(item("issues", status=status))) is owes


# ---------------------------------------------------------------------------
# Table 3 · standards — ratification, and the flip is the operator's alone
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "ratification,owes",
    [("pending", True), ("", True), ("ratified", False), ("amended", False), ("rejected", False)],
)
def test_a_standards_candidate_owes_until_ratification_is_terminal(ratification: str, owes: bool):
    assert bool(rules.standards_owed(item("standards", ratification=ratification))) is owes


def test_the_ratification_flip_is_attributed_to_the_operator():
    owed = rules.standards_owed(item("standards", ratification="pending"))
    assert owed[0].actor == "operator"


def test_a_standards_items_terminal_state_is_ratification_not_status():
    """§4 gives this store its terminal states on the operator's own field.

    A `status: applied` with a non-terminal `ratification:` is a live shape in
    the corpus, and reading `status:` as the carrier would render four amendments
    as settled while the operator has ruled on none of them.
    """
    applied = item("standards", status="applied", ratification="")
    assert rules.is_terminal(applied) == ""
    assert rules.standards_owed(applied)

    ratified = item("standards", status="open", ratification="ratified")
    assert rules.is_terminal(ratified) == "ratified"


# ---------------------------------------------------------------------------
# Table 4 · operations — the cross-field reading no file states
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "status,ready,blocked_on,reading",
    [
        ("queued", "ready", "none", rules.READING_AUTHORISED),
        ("queued", "not-ready", "none", rules.READING_NOT_ITS_TURN),
        ("in-progress", "ready", "none", rules.READING_IN_MOTION),
        ("blocked", "not-ready", "PM2 guide restructure merge", rules.READING_BLOCKED),
        ("blocked", "not-ready", "none", rules.READING_STALE_BLOCK),
        ("blocked", "ready", "", rules.READING_STALE_BLOCK),
    ],
)
def test_the_cross_field_reading(status: str, ready: str, blocked_on: str, reading: str):
    assert (
        rules.operations_reading(
            item("operations", status=status, ready=ready, blocked_on=blocked_on)
        )
        == reading
    )


def test_ready_not_ready_does_not_mean_stuck_and_blocked_does_not_mean_owing():
    """§4: *`ready:` is an authorisation to act, not a statement about blockedness.*

    Both halves matter. An item can be entirely unblocked and still `not-ready`
    because it is not its turn — that owes nobody anything. And a genuinely
    blocked item owes the operator nothing either; it is waiting on its named
    condition, not on a ruling.
    """
    not_its_turn = item("operations", status="queued", ready="not-ready", blocked_on="none")
    genuinely_blocked = item(
        "operations", status="blocked", ready="not-ready", blocked_on="the date"
    )
    assert rules.operations_owed(not_its_turn) == []
    assert rules.operations_owed(genuinely_blocked) == []


def test_only_the_two_cross_field_readings_owe_the_operator_anything():
    authorised = item("operations", status="queued", ready="ready", blocked_on="none")
    stale = item("operations", status="blocked", ready="not-ready", blocked_on="none")
    assert [o.kind for o in rules.operations_owed(authorised)] == [rules.READING_AUTHORISED]
    assert [o.kind for o in rules.operations_owed(stale)] == [rules.READING_STALE_BLOCK]


def test_a_prose_blocked_on_is_never_judged():
    """Deciding whether a prose condition has been met would be RULING.

    The page rules on nothing, so only a `blocked_on:` that SAYS nothing blocks
    it is read as a stale block. Anything else is left alone.
    """
    for condition in ("T-19, then PM1 bandwidth", "the date", "Temporal SDK installed"):
        blocked = item("operations", status="blocked", ready="not-ready", blocked_on=condition)
        assert rules.operations_reading(blocked) == rules.READING_BLOCKED


# ---------------------------------------------------------------------------
# §4.2 terminal states and the prune windows they key
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "store,status,terminal",
    [
        ("candidates", "adopted", "adopted"),
        ("candidates", "rejected", "rejected"),
        ("candidates", "open", ""),
        ("issues", "resolved", "resolved"),
        ("operations", "resolved", "resolved"),
        ("operations", "blocked", ""),
    ],
)
def test_terminal_states_per_store(store: str, status: str, terminal: str):
    assert rules.is_terminal(item(store, status=status)) == terminal


def test_the_prune_window_is_fourteen_days_except_for_rejected():
    """§4.2: six months for `rejected`, so a rejection is not re-proposed in a fortnight."""
    assert rules.PRUNE_DAYS["adopted"] == 14
    assert rules.PRUNE_DAYS["ratified"] == 14
    assert rules.PRUNE_DAYS["resolved"] == 14
    assert rules.PRUNE_DAYS["rejected"] == 182


def test_every_store_has_a_rule_and_none_falls_through_to_a_default():
    """A store the reader knows and this module does not would render unjudged.

    The dispatch table is asserted against the reader's own store list rather
    than a literal, so adding a fifth store to `tracked.STORES` fails here
    instead of silently producing a table that rules on nothing.
    """
    from planning_ui.plan_extractor.tracked import STORES

    assert set(rules.OWED_BY_STORE) == set(STORES)
    assert set(rules.OWES_DEFINITION_BY_STORE) == set(STORES)

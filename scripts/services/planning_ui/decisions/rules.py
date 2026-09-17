"""What *owes a ruling* means, per store — the judgement half of this phase.

The phrase means something different in each of the five sources, and collapsing
them into one yes/no tells a reader nothing about what to do next. Each rule
below states its condition, the actor who rules it, and the §-reference it comes
from; all three are rendered on the page.

**Three field states, never conflated.** A §4 extension field can be *present
and set*, *present and blank*, or *absent from the file entirely*. The reader in
:mod:`plan_extractor.tracked` already reports the third as a named finding, and
this module keeps the distinction in the rendered cell rather than defaulting
one onto another. Coercing them together would make a conformance defect render
as an ordinary untriaged row — which is the display-level smoothing the operator
ruled out on 2026-09-02.

**Nothing here rules on anything.** It reports what owes a ruling and names who
owes it. It sets no ``decision:``, ``size:``, ``component:``, ``ready:`` or
``ratification:``.
"""

from __future__ import annotations

from dataclasses import dataclass

from planning_ui.plan_extractor.tracked import TrackedItem

#: Field is absent from the file altogether — a §4 conformance defect, already a
#: named finding from the reader. Distinguished from blank in every cell.
ABSENT = "absent"
#: Field is present and empty.
BLANK = "blank"

#: What a cell shows when the value is unknown. One glyph, one meaning.
DASH = "—"


# ---------------------------------------------------------------------------
# Shared item accessors
# ---------------------------------------------------------------------------
#
# These live HERE, beside the field semantics they read, rather than in the
# module that happened to need them first. Both `tables` and `crossings` use
# them, and the second consumer originally reached across for the first's
# single-underscore names — a private symbol treated as a shared API is a rename
# away from breaking a sibling with no local signal that anything depends on it.


def sorted_items(items: list[TrackedItem]) -> list[TrackedItem]:
    """§3.1 ordering: `count` first, then oldest-filed, then id.

    *"Recurrence outranks age. A `count: 3` item filed last week is more real
    than a `count: 1` filed in June — one is a pattern, the other may be noise.
    Triage sorts by count first."* The third key is there only so two items with
    the same count and filing date order identically across runs.
    """

    def key(item: TrackedItem) -> tuple[int, str, str]:
        try:
            count = int(item.fields.get("count", "").strip() or 0)
        except ValueError:
            count = 0
        return (-count, item.fields.get("filed", "").strip(), item.fields.get("id", item.path))

    return sorted(items, key=key)


def count_cell(item: TrackedItem) -> str:
    return item.fields.get("count", "").strip() or DASH


def title_cell(item: TrackedItem) -> str:
    return item.fields.get("title", "").strip() or "(no title)"


def field_state(item: TrackedItem, name: str) -> str:
    """``ABSENT``, ``BLANK``, or the field's value."""
    if name not in item.fields:
        return ABSENT
    value = item.fields[name].strip()
    return value or BLANK


def unset(state: str) -> bool:
    """Whether a field state means "nobody has put a value here"."""
    return state in (ABSENT, BLANK)


def describe(name: str, state: str) -> str:
    """One wording for a field state, used in every cell that reports one."""
    if state == ABSENT:
        return f"`{name}:` absent from the file (§4 field missing)"
    if state == BLANK:
        return f"`{name}:` blank"
    return f"`{name}: {state}`"


@dataclass(frozen=True)
class Owed:
    """One ruling an item owes, and who owes it."""

    kind: str
    actor: str
    reason: str


# ---------------------------------------------------------------------------
# Terminal states, per §4
# ---------------------------------------------------------------------------
#
# The field carrying terminal-ness differs by store, and that is not an
# inconsistency to paper over: §4 gives Candidates and Issues their terminal
# states on `status:`, while a standards candidate's terminal state is the
# operator's `ratification:` — the field §4 singles out as the operator's alone.

TERMINAL_STATUS: dict[str, frozenset[str]] = {
    "candidates": frozenset({"adopted", "rejected"}),
    "issues": frozenset({"resolved", "rejected"}),
    "operations": frozenset({"resolved"}),
    # A standards candidate's `status:` is not the carrier — see below.
    "standards": frozenset(),
}

TERMINAL_RATIFICATION = frozenset({"ratified", "amended", "rejected"})

# **Where a contradiction can actually arise, and where it cannot.**
#
# For issues, standards and operations the terminal-state field and the field
# the owed-gate reads are THE SAME FIELD, so `is_terminal(item)` and
# `<store>_owed(item)` are the identical boolean computed twice and can never
# both be true. `tables._contradiction` is therefore unreachable for those three
# **by construction, not by coincidence** — it is retained at those call sites so
# a future change that stops gating an owed-predicate on terminal-ness starts
# reporting instead of silently admitting a contradictory row.
#
# `candidates` is the live case: `is_terminal` reads `status:`, while
# `candidate_owed` reasons about the INDEPENDENT `decision:`/`size:`/
# `component:` fields. An item can hold `status: adopted` with `decision:` still
# unset, and that is exactly the shape the operator ruled must surface.
#
# A post-terminal reference going stale — a `resolved` issue whose `repo:` no
# longer resolves, a `ratified` amendment whose anchor has rotted — is NOT this
# finding. Requirement 1 filters terminal rows out before either resolution
# check runs, and table 3 is titled *awaiting* ratification for that reason. It
# is a separate surface, not a gap in this one.

#: §4.2. The clock runs from LAST ACTIVITY, and a `count` increment resets it.
PRUNE_DAYS: dict[str, int] = {
    "resolved": 14,
    "adopted": 14,
    "ratified": 14,
    "amended": 14,
    "rejected": 182,
}


def is_terminal(item: TrackedItem) -> str:
    """The terminal state an item holds, or ``""``.

    Returns the state itself rather than a boolean, because the §4.2 prune clock
    is keyed on which terminal state it is — 14 days for `resolved`/`adopted`/
    `ratified`, six months for `rejected`.
    """
    if item.store == "standards":
        ratification = field_state(item, "ratification").lower()
        return ratification if ratification in TERMINAL_RATIFICATION else ""
    status = field_state(item, "status").lower()
    return status if status in TERMINAL_STATUS.get(item.store, frozenset()) else ""


# ---------------------------------------------------------------------------
# Table 1 · Proposals awaiting triage — tracked/candidates/
# ---------------------------------------------------------------------------

CANDIDATES_OWES = (
    "Three orthogonal asks of two different actors, kept separate because "
    "collapsing them into one yes/no tells a reader nothing about what to do "
    "next. **Triage** — `decision:` is unset; ruled by `triage-candidates`, and "
    "only it. **Sizing** — `decision: ship` with `size:` unset; ruled by "
    "`triage-candidates`. **Placement** — `component:` is unset, meaning nothing "
    "is scaffolded for it; ruled by the **operator**, and nothing automated may "
    "fill it. An item owing more than one is listed once, with all of them named."
)


def candidate_owed(item: TrackedItem) -> list[Owed]:
    owed: list[Owed] = []
    decision = field_state(item, "decision")
    size = field_state(item, "size")
    component = field_state(item, "component")

    if unset(decision):
        owed.append(Owed("triage", "triage-candidates", describe("decision", decision)))
    elif decision.lower() == "ship" and unset(size):
        owed.append(Owed("sizing", "triage-candidates", describe("size", size)))
    if unset(component):
        owed.append(Owed("placement", "operator", describe("component", component)))
    return owed


# ---------------------------------------------------------------------------
# Table 2 · Defects awaiting disposition — tracked/issues/
# ---------------------------------------------------------------------------

ISSUES_OWES = (
    "`status: open`, and nothing else. The §4 terminal states are `resolved` and "
    "`rejected`; the triage cadence is **sprint close-out** and the runner is "
    "**the sprint's owner**."
)


def issue_owed(item: TrackedItem) -> list[Owed]:
    status = field_state(item, "status").lower()
    if status in TERMINAL_STATUS["issues"]:
        return []
    return [Owed("disposition", "the sprint's owner", describe("status", status))]


# ---------------------------------------------------------------------------
# Table 3 · Standards amendments awaiting ratification — tracked/standards/
# ---------------------------------------------------------------------------

STANDARDS_OWES = (
    "`ratification:` holds none of the §4 terminal states — `ratified`, `amended` "
    "or `rejected`. **The flip is the operator's alone** (§4, per Standards "
    "Governance): autonomous work may FILE a standards candidate and may never "
    "rule one. `pending`, blank and absent all owe the same ruling and are "
    "reported distinctly, because only one of the three is also a §4 conformance "
    "defect. **This page reports; it never rules.**"
)


def standards_owed(item: TrackedItem) -> list[Owed]:
    ratification = field_state(item, "ratification")
    if ratification.lower() in TERMINAL_RATIFICATION:
        return []
    return [Owed("ratification", "operator", describe("ratification", ratification))]


# ---------------------------------------------------------------------------
# Table 4 · The operator's own agenda — tracked/operations/
# ---------------------------------------------------------------------------

OPERATIONS_OWES = (
    "**Not `status:` alone, and that is the subtlety.** §4 is explicit that "
    "`ready:` is *\"an authorisation to act, not a statement about blockedness — "
    "an item can be entirely unblocked and still `not-ready` because it is not "
    "its turn\"*. So `status: blocked` does not mean it owes the operator "
    "anything, and `ready: not-ready` does not mean it is stuck. The rows that "
    "owe something are the cross-field ones: **authorised and waiting** "
    "(`ready: ready` with `status: queued` — actionable now) and **stale block** "
    "(`status: blocked` whose `blocked_on:` names nothing that blocks it). "
    "Neither reading is stated in any file."
)

#: `blocked_on:` values that assert nothing is blocking. §4 gives no vocabulary
#: for this field — it is free prose — so only a value that SAYS there is no
#: blocker is read as one. Anything else is left alone; guessing whether a prose
#: condition has been met would be ruling, which this page does not do.
_NO_BLOCKER = frozenset({"none", "nothing", "-", "n/a", "na"})

#: The four readings, one of which every operations item gets.
READING_AUTHORISED = "authorised and waiting"
READING_STALE_BLOCK = "stale block"
READING_IN_MOTION = "in motion"
READING_BLOCKED = "blocked"
READING_NOT_ITS_TURN = "not its turn"


def operations_reading(item: TrackedItem) -> str:
    """The cross-field reading, stated as one value. §4's `ready:`/`status:` pair."""
    status = field_state(item, "status").lower()
    ready = field_state(item, "ready").lower()
    blocked_on = field_state(item, "blocked_on").lower()

    if status == "blocked":
        if unset(blocked_on) or blocked_on in _NO_BLOCKER:
            return READING_STALE_BLOCK
        return READING_BLOCKED
    if status == "in-progress":
        return READING_IN_MOTION
    if status == "queued":
        return READING_AUTHORISED if ready == "ready" else READING_NOT_ITS_TURN
    return READING_NOT_ITS_TURN


#: The two readings that owe the operator something.
OPERATIONS_OWING_READINGS = frozenset({READING_AUTHORISED, READING_STALE_BLOCK})


def operations_owed(item: TrackedItem) -> list[Owed]:
    if field_state(item, "status").lower() in TERMINAL_STATUS["operations"]:
        return []
    reading = operations_reading(item)
    if reading not in OPERATIONS_OWING_READINGS:
        return []
    return [Owed(reading, "operator", reading)]


# ---------------------------------------------------------------------------
# Table 5 · Unplaced components owing schedule-or-retire — sprints.md
# ---------------------------------------------------------------------------

UNPLACED_OWES = (
    "**The section states it itself:** *\"every entry owes a ruling: schedule it, "
    "or retire it.\"* So every listed entry owes one by definition, and a table "
    "that only re-lists them adds nothing. What the reader cannot get from the "
    "file is **which entries are stale and how long each has sat** — those are "
    "the two derived columns, and they are the reason this table exists. "
    "`sprints.md` is the operator's surface: a stale entry is **reported here and "
    "edited there**, never by this page."
)


#: Which per-store rule applies. One dispatch table, so a new store cannot be
#: added to the reader and silently rendered by a default that rules on nothing.
OWED_BY_STORE = {
    "candidates": candidate_owed,
    "issues": issue_owed,
    "standards": standards_owed,
    "operations": operations_owed,
}

OWES_DEFINITION_BY_STORE = {
    "candidates": CANDIDATES_OWES,
    "issues": ISSUES_OWES,
    "standards": STANDARDS_OWES,
    "operations": OPERATIONS_OWES,
}

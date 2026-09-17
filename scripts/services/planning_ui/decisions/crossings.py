"""The cross-store readings — why this is one page and not five views.

Each of the five tables is worth having. **The page's value is what none of them
can produce alone**, and these four are the readings that make it a surface
rather than a directory listing:

* **`count` before age** (§3.1) — ranking across four stores by a per-item
  integer is arithmetic nobody does today;
* **the prune clock** (§4.2) — which terminal items fall due, from LAST ACTIVITY
  rather than the terminal date, with a `count` increment resetting it;
* **the exit test** (§0) — an item that has survived three consecutive triage
  passes without a ruling is itself a finding. It requires history across
  passes, which no item file records, and **nothing derives it today**;
* **conformance of the stores themselves** (§0) — the three-properties test
  applied to the stores rather than to their items. A store's own guarantee
  against becoming the ledger it replaced is currently unmeasured.
"""

from __future__ import annotations

from datetime import date

from planning_ui.plan_extractor.model import Finding, Provenance
from planning_ui.plan_extractor.tracked import TrackedItem, TrackedStores

from . import rules
from .history import History
from .model import (
    EXIT_TEST_FAILED,
    SECTION_DECISIONS,
    STORE_CADENCE_ABSENT,
    Column,
    Row,
    Table,
)
from .rules import DASH, count_cell, sorted_items, title_cell

#: §0's exit test, verbatim in its threshold: three consecutive passes.
EXIT_TEST_THRESHOLD = 3

#: §1 admission tests and §4 cadences, quoted from the standard so the
#: conformance table states the property it is measuring against rather than
#: asserting a verdict a reader cannot check.
STORE_PROPERTIES: dict[str, tuple[str, str, str]] = {
    "candidates": (
        "a PROPOSAL — not a defect, and not a research question",
        "`triage-candidates` · PM3",
        "`adopted` · `rejected`",
    ),
    "issues": (
        "a DEFECT found while building something unrelated — never one inside the "
        "current build's scope",
        "sprint close-out · the sprint's owner",
        "`resolved` · `rejected`",
    ),
    "standards": (
        "a proposed amendment to a NAMED standard, with an anchor precise enough "
        "to act on (§4.1 refuses one without)",
        "standards pass · PM3 + operator",
        "`ratified` · `amended` · `rejected`",
    ),
    "operations": (
        "a human's note-to-self with no done-state — **nothing a machine files** (§1.2)",
        "every standup · the operator",
        "`resolved`",
    ),
}


def _owed(item: TrackedItem) -> list[rules.Owed]:
    rule = rules.OWED_BY_STORE.get(item.store)
    return rule(item) if rule else []


# ---------------------------------------------------------------------------
# Reading 1 · The unified triage queue — count before age
# ---------------------------------------------------------------------------

TRIAGE_ORDER_METHOD = (
    "§3.1: *\"Recurrence outranks age. A `count: 3` item filed last week is more "
    "real than a `count: 1` filed in June — one is a pattern, the other may be "
    "noise. **Triage sorts by count first.**\"* `count` is a per-item integer and "
    "ranking across four stores by it is arithmetic no single store does. Ties "
    "break on the oldest `filed:` date, then on id so two runs order identically."
)


def triage_queue(stores: TrackedStores, history: History, as_of: date) -> Table:
    owing = [item for item in stores.all_items() if _owed(item)]
    table = Table(
        key="triage_queue",
        title="Every item owing a ruling, across all four stores — `count` before age",
        source="tracked/candidates/ · issues/ · standards/ · operations/",
        owes_definition=TRIAGE_ORDER_METHOD,
        columns=[
            Column("count", "count"),
            Column("store", "Store"),
            Column("id", "Id"),
            Column("title", "Title"),
            Column("owes", "Owes", derived=True),
            Column("filed", "Filed"),
            Column("age", "Days since last activity", derived=True),
        ],
        scanned=len(stores.all_items()),
    )
    for item in sorted_items(owing):
        days = history.item_age_days(item.path, as_of)
        table.rows.append(
            Row(
                cells={
                    "count": count_cell(item),
                    "store": item.store,
                    "id": item.fields.get("id", DASH),
                    "title": title_cell(item),
                    "owes": " · ".join(o.kind for o in _owed(item)),
                    "filed": item.fields.get("filed", "").strip() or DASH,
                    "age": DASH if days is None else str(days),
                },
                source=Provenance(item.path, 1),
            )
        )
    table.suppressed = table.scanned - len(table.rows)
    return table


# ---------------------------------------------------------------------------
# Reading 2 · The §4.2 prune clock
# ---------------------------------------------------------------------------

PRUNE_METHOD = (
    "§4.2: terminal items are deleted and git history is the archive — 14 days "
    "for `resolved`/`adopted`/`ratified`, six months for `rejected`. **The clock "
    "runs from LAST ACTIVITY, not from the terminal date, and a `count` "
    "increment is activity that resets it** — otherwise an item that keeps being "
    "re-proposed gets deleted while it is actively recurring. Last activity is "
    "the newest commit touching the item's own file, read from the checkout. "
    "**An empty table is a pass, not a skip**: it means no item currently holds a "
    "terminal state."
)


def prune_clock(stores: TrackedStores, history: History, as_of: date) -> Table:
    table = Table(
        key="prune_clock",
        title="Terminal items and when they fall due",
        source="tracked/ — the §4.2 clock, from last activity",
        owes_definition=PRUNE_METHOD,
        columns=[
            Column("store", "Store"),
            Column("id", "Id"),
            Column("title", "Title"),
            Column("terminal", "Terminal state"),
            Column("last_activity", "Last activity", derived=True),
            Column("due", "Days until deletion", derived=True),
        ],
        scanned=len(stores.all_items()),
    )
    for item in sorted_items(stores.all_items()):
        terminal = rules.is_terminal(item)
        if not terminal:
            continue
        window = rules.PRUNE_DAYS.get(terminal)
        activity = history.item_activity.get(item.path)
        elapsed = history.days_since(activity, as_of)
        if window is None or elapsed is None or activity is None:
            last, due = DASH, DASH
        else:
            remaining = window - elapsed
            last = activity.day
            due = f"{remaining}" if remaining > 0 else f"**overdue by {-remaining}**"
        table.rows.append(
            Row(
                cells={
                    "store": item.store,
                    "id": item.fields.get("id", DASH),
                    "title": title_cell(item),
                    "terminal": terminal,
                    "last_activity": last,
                    "due": due,
                },
                source=Provenance(item.path, 1),
            )
        )
    table.suppressed = table.scanned - len(table.rows)
    return table


# ---------------------------------------------------------------------------
# Reading 3 · The §0 exit test
# ---------------------------------------------------------------------------

EXIT_TEST_METHOD = (
    "§0's third property: *\"An item that survives three consecutive triage "
    "passes without a ruling is itself a finding, reported at the next standup — "
    "not carried silently a fourth time.\"* It requires history across passes, "
    "which no item file records. **A pass is a commit that MODIFIED or DELETED "
    "an item already in the store and did not touch this item** — somebody went "
    "through the store and ruled on something, and this item was not it. A "
    "commit that only ADDS items is filing, not triage, and counting it would "
    "inflate every score in a store being harvested into. That is the closest a "
    "checkout can come to the standard's wording, and it is stated here rather "
    "than left for a reader to assume."
)


def exit_test(stores: TrackedStores, history: History, findings: list[Finding]) -> Table:
    table = Table(
        key="exit_test",
        title=f"Items that have survived {EXIT_TEST_THRESHOLD} or more triage passes unruled",
        source="tracked/ — the §0 exit test, measured",
        owes_definition=EXIT_TEST_METHOD,
        columns=[
            Column("store", "Store"),
            Column("id", "Id"),
            Column("title", "Title"),
            Column("owes", "Owes", derived=True),
            Column("passes", "Passes survived", derived=True),
        ],
        scanned=len(stores.all_items()),
    )
    if not history.available:
        table.notes.append(
            "**Not measured** — the checkout carries no readable history, so pass "
            "counts are unknown. An empty table here means *unmeasured*, not *clean*."
        )
        return table

    for item in sorted_items(stores.all_items()):
        owed = _owed(item)
        if not owed:
            continue
        passes = history.passes_since_activity(item.store, item.path)
        if passes is None or passes < EXIT_TEST_THRESHOLD:
            continue
        table.rows.append(
            Row(
                cells={
                    "store": item.store,
                    "id": item.fields.get("id", DASH),
                    "title": title_cell(item),
                    "owes": " · ".join(o.kind for o in owed),
                    "passes": str(passes),
                },
                source=Provenance(item.path, 1),
            )
        )
        findings.append(
            Finding(
                code=EXIT_TEST_FAILED,
                section=SECTION_DECISIONS,
                summary=(
                    f"tracked {item.store} item has survived {passes} triage passes "
                    f"without a ruling and still owes: {', '.join(o.kind for o in owed)}"
                ),
                provenance=Provenance(item.path, 1),
                expected=(
                    "a ruling within three triage passes, per the §0 exit test — the "
                    "third of the three properties that separate a store from the "
                    "banned ledger"
                ),
                detail=(
                    "§0 binds this to be *\"reported at the next standup — not carried "
                    "silently a fourth time.\"* Reported here; the ruling itself belongs "
                    "to the actor named in the item's own table."
                ),
            )
        )
    table.suppressed = table.scanned - len(table.rows)
    return table


# ---------------------------------------------------------------------------
# Reading 4 · §0 applied to the stores rather than to their items
# ---------------------------------------------------------------------------

CONFORMANCE_METHOD = (
    "§0's three properties — **an admission test**, **a triage cadence with a "
    "named runner**, and **an exit** — applied to the stores themselves. The "
    "first two are quoted from §1 and §4, which is where they are stated. The "
    "third is MEASURED, because a store can carry the words and still have no "
    "exit in fact: *\"a store missing any of the three is out of conformance, and "
    "the correct response is to fix the store or delete it, never to keep filing "
    "into it.\"*"
)


def store_conformance(
    stores: TrackedStores,
    history: History,
    close_out_open: bool,
    findings: list[Finding],
) -> Table:
    table = Table(
        key="store_conformance",
        title="The §0 three-properties test, applied to the stores",
        source="tracked/ — measured against Tracked Items Standard §0",
        owes_definition=CONFORMANCE_METHOD,
        columns=[
            Column("store", "Store"),
            Column("items", "Items", derived=True),
            Column("owing", "Owing a ruling", derived=True),
            Column("admission", "§0.1 admission test"),
            Column("cadence", "§0.2 cadence · runner"),
            Column("exit", "§0.3 exit — measured", derived=True),
        ],
        scanned=len(STORE_PROPERTIES),
    )
    for store in sorted(STORE_PROPERTIES):
        items = stores.items.get(store, [])
        owing = [item for item in items if _owed(item)]
        admission, cadence, terminal_states = STORE_PROPERTIES[store]

        stuck = [
            item
            for item in owing
            if (history.passes_since_activity(store, item.path) or 0) >= EXIT_TEST_THRESHOLD
        ]
        if not history.available:
            exit_cell = f"unmeasured — no history. Terminal states: {terminal_states}"
        elif stuck:
            exit_cell = (
                f"**{len(stuck)} item(s) past {EXIT_TEST_THRESHOLD} passes unruled** — "
                f"terminal states {terminal_states} exist but are not being reached"
            )
        else:
            exit_cell = f"holding — no item past {EXIT_TEST_THRESHOLD} passes. {terminal_states}"

        if store == "issues" and not close_out_open:
            cadence = f"**no open close-out gate** — stated cadence is {cadence}"
            findings.append(
                Finding(
                    code=STORE_CADENCE_ABSENT,
                    section=SECTION_DECISIONS,
                    summary=(
                        "tracked/issues/ has no open `Sprint close-out` gate, so the §4 "
                        "cadence that triages it cannot run"
                    ),
                    provenance=Provenance("development/sprints.md"),
                    expected="at least one unchecked `Sprint close-out` item in sprints.md",
                    detail=(
                        "§0 requires a triage cadence with a named runner. Every close-out "
                        "being checked means the store has the words and no cadence in fact."
                    ),
                )
            )

        table.rows.append(
            Row(
                cells={
                    "store": f"tracked/{store}/",
                    "items": str(len(items)),
                    "owing": str(len(owing)),
                    "admission": admission,
                    "cadence": cadence,
                    "exit": exit_cell,
                },
                source=Provenance(f"tracked/{store}"),
            )
        )
    return table

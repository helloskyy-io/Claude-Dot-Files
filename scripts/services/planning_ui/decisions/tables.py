"""The five tables — one per repo-resident store whose entries accumulate unruled.

Four are folders of uniform §3 frontmatter. **The fifth is a section inside
`sprints.md`** — a different shape, hand-maintained by the operator, and
therefore the one that most needs the derived columns: the four uniform stores
can be trusted to describe themselves and this section cannot.

**Every table shows only rows that can be ruled on** (requirement 1) and states
how many items it scanned and how many it suppressed. A short table and an empty
store are otherwise indistinguishable, and only one of them is good news.

**Every table carries at least one column its source document cannot**
(requirement 2). Without it the page is a re-render of files a reader could
already open.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from planning_ui.plan_extractor import corpus_io, derivations
from planning_ui.plan_extractor.model import Collector, Finding, Provenance
from planning_ui.plan_extractor.roadmaps import Component
from planning_ui.plan_extractor.safe_paths import exists_in_root
from planning_ui.plan_extractor.sprints import SPRINTS_REL, SprintItem, SprintsDocument
from planning_ui.plan_extractor.tracked import TrackedItem, TrackedStores

from . import rules
from .history import History
from .model import (
    DECISION_CONTRADICTION,
    SECTION_DECISIONS,
    UNPLACED_STALENESS_UNDERIVABLE,
    Column,
    Row,
    Table,
)

#: Re-exported so `tables` and `crossings` share one glyph and one meaning.
DASH = rules.DASH


def _age_cell(history: History, path: str, as_of: date) -> str:
    activity = history.item_activity.get(path)
    days = history.days_since(activity, as_of)
    if activity is None or days is None:
        return DASH
    return f"{days}d (last activity {activity.day})"


def _passes_cell(history: History, store: str, path: str) -> str:
    passes = history.passes_since_activity(store, path)
    return DASH if passes is None else str(passes)


def _contradiction(
    item: TrackedItem, terminal: str, owed: list[rules.Owed], findings: list[Finding]
) -> None:
    """A §4 terminal state held while a ruling is still owed.

    **Reported, never smoothed.** The operator ruled on 2026-09-02 that a
    contradictory row erroring — or appearing as a named finding — is the DESIRED
    behaviour, because it points at the broken record. `decision:` is set
    autonomously by `triage-candidates` from code, so an item in this state is
    evidence of a tooling defect or of hand-editing that predates the standards
    now governing these files. The remedy is at the SOURCE: the item's own file
    is manually reset so it gets a fresh evaluation. A display-layer rule mapping
    the contradiction onto "owing triage" would hide exactly the defect this page
    exists to expose, and would let pre-standards residue render tidily forever.
    """
    if not terminal or not owed:
        return
    prune = rules.PRUNE_DAYS.get(terminal)
    findings.append(
        Finding(
            code=DECISION_CONTRADICTION,
            section=SECTION_DECISIONS,
            summary=(
                f"tracked {item.store} item holds the §4 terminal state `{terminal}` "
                f"while still owing: {', '.join(o.kind for o in owed)}"
            ),
            provenance=Provenance(item.path, 1),
            expected="a terminal state only once every ruling the item owes has been made",
            detail=(
                f"The §4.2 prune clock is running on it — deletion {prune} days after last "
                "activity — while a ruling nobody has made is still outstanding. Reported, "
                "not resolved: the fix belongs in the item's own file, reset so it gets a "
                "fresh evaluation. If the state was written by tooling, that is a tooling "
                "defect and a handback, not a display-layer rule."
            ),
        )
    )


# ---------------------------------------------------------------------------
# Table 1 · Proposals awaiting triage — tracked/candidates/
# ---------------------------------------------------------------------------

#: Stated on the page beside the derived column, so a reader knows what each of
#: its three outcomes means without opening the standard.
COMPONENT_RESOLUTION_METHOD = (
    "`component:` is resolved against the checkout two ways — repo-relative, and "
    "relative to the item file — and the three outcomes mean different things. "
    "**resolves**: the proposal extends an existing component. **names a "
    "component to be scaffolded**: legitimate, and exactly what `plan-candidates` "
    "consumes. **unset**: nobody has named where it goes, and only the operator "
    "may fill it. The file cannot tell you which, because it does not read the "
    "filesystem."
)


def build_candidates(
    root: Path,
    stores: TrackedStores,
    history: History,
    as_of: date,
    findings: list[Finding],
) -> Table:
    items = stores.items.get("candidates", [])
    table = Table(
        key="candidates",
        title="Table 1 · Proposals awaiting triage",
        source="tracked/candidates/",
        owes_definition=rules.CANDIDATES_OWES,
        columns=[
            Column("id", "Id"),
            Column("title", "Title"),
            Column("count", "count"),
            Column("owes", "Owes", derived=True),
            Column("who", "Ruled by", derived=True),
            Column("component", "Does `component:` resolve?", derived=True),
            Column("age", "How long it has sat", derived=True),
            Column("passes", "Triage passes survived", derived=True),
        ],
        scanned=len(items),
        notes=[COMPONENT_RESOLUTION_METHOD],
    )
    for item in rules.sorted_items(items):
        owed = rules.candidate_owed(item)
        _contradiction(item, rules.is_terminal(item), owed, findings)
        if not owed:
            continue
        raw = item.fields.get("component", "").strip().strip("`")
        if not raw:
            resolution = "unset — nobody has named where it goes"
        elif exists_in_root(root, raw):
            resolution = f"resolves — `{raw}`"
        else:
            resolution = f"names a component to be scaffolded — `{raw}`"
        table.rows.append(
            Row(
                cells={
                    "id": item.fields.get("id", DASH),
                    "title": rules.title_cell(item),
                    "count": rules.count_cell(item),
                    "owes": " · ".join(f"{o.kind} ({o.reason})" for o in owed),
                    "who": " · ".join(sorted({o.actor for o in owed})),
                    "component": resolution,
                    "age": _age_cell(history, item.path, as_of),
                    "passes": _passes_cell(history, "candidates", item.path),
                },
                source=Provenance(item.path, 1),
            )
        )
    table.suppressed = table.scanned - len(table.rows)
    return table


# ---------------------------------------------------------------------------
# Table 2 · Defects awaiting disposition — tracked/issues/
# ---------------------------------------------------------------------------

REPO_RESOLUTION_METHOD = (
    "`repo:` records where the work lands, and Tracked Items §4.0 binds its FORM — "
    "the bare directory name as the checkout has it, never `owner/name` and never a "
    "path — because the field is matched on, not read. That form is what this column "
    "checks. Whether a repository of that name EXISTS cannot be known from this "
    "checkout alone: the page used to enumerate the git repositories beside the "
    "checkout, which made the answer depend on where the checkout sat (a worktree saw "
    "its sibling worktrees, a pull-request runner saw only itself), and a committed "
    "page cannot carry an answer that changes with its path. No hardcoded repo list "
    "replaces it."
)

#: Tracked Items §4.0's binding form for `repo:`: the bare directory name as
#: the checkout has it. Lowercase, no separator that would make it a path or
#: an `owner/name`.
REPO_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

CLOSE_OUT_METHOD = (
    "§4 gives this store's cadence as **sprint close-out**, run by the sprint's "
    "owner — but no file says WHICH close-out. It is the first `Sprint close-out` "
    "gate in `sprints.md` document order that is still unchecked, and resolving "
    "that against the sprint body is arithmetic no item file can do. **If every "
    "close-out is checked, nothing triages this store** — which is a §0 cadence "
    "failure, and is reported as one."
)


def repo_field_cell(raw: str) -> str:
    """The `repo:` column, from the field's text alone.

    Path-independent by construction — see :data:`REPO_RESOLUTION_METHOD` for
    what the previous, sibling-enumerating check cost. Three outcomes, never a
    blank: unset, well-formed, malformed.
    """
    if not raw:
        return "unset — the item names no repo"
    if REPO_NAME_RE.match(raw):
        return f"well-formed — `{raw}`"
    return f"malformed — `{raw}` is not a bare directory name (§4.0)"


def next_close_out(sprint_doc: SprintsDocument | None) -> tuple[str, int]:
    """The first still-unchecked ``Sprint close-out`` gate: ``(sprint name, line)``."""
    if sprint_doc is None:
        return "", 0
    for sprint in sprint_doc.sprints:
        if sprint.is_unplaced:
            continue
        for item in sprint.items:
            if item.is_close_out and not item.checked:
                return sprint.name, item.line
    return "", 0


def build_issues(
    stores: TrackedStores,
    sprint_doc: SprintsDocument | None,
    history: History,
    as_of: date,
    findings: list[Finding],
) -> Table:
    items = stores.items.get("issues", [])
    close_out_name, close_out_line = next_close_out(sprint_doc)
    owner = (
        f"`{close_out_name}` close-out (sprints.md:{close_out_line})"
        if close_out_name
        else "no open close-out gate — nothing triages this store"
    )
    notes = [REPO_RESOLUTION_METHOD, CLOSE_OUT_METHOD]

    table = Table(
        key="issues",
        title="Table 2 · Defects awaiting disposition",
        source="tracked/issues/",
        owes_definition=rules.ISSUES_OWES,
        columns=[
            Column("id", "Id"),
            Column("title", "Title"),
            Column("count", "count"),
            Column("repo", "Is `repo:` §4.0-formed?", derived=True),
            Column("close_out", "Which close-out owns it", derived=True),
            Column("age", "How long it has sat", derived=True),
            Column("passes", "Triage passes survived", derived=True),
        ],
        scanned=len(items),
        notes=notes,
    )
    for item in rules.sorted_items(items):
        owed = rules.issue_owed(item)
        _contradiction(item, rules.is_terminal(item), owed, findings)
        if not owed:
            continue
        table.rows.append(
            Row(
                cells={
                    "id": item.fields.get("id", DASH),
                    "title": rules.title_cell(item),
                    "count": rules.count_cell(item),
                    "repo": repo_field_cell(item.fields.get("repo", "").strip().strip("`")),
                    "close_out": owner,
                    "age": _age_cell(history, item.path, as_of),
                    "passes": _passes_cell(history, "issues", item.path),
                },
                source=Provenance(item.path, 1),
            )
        )
    table.suppressed = table.scanned - len(table.rows)
    return table


# ---------------------------------------------------------------------------
# Table 3 · Standards amendments awaiting ratification — tracked/standards/
# ---------------------------------------------------------------------------

ANCHOR_RESOLUTION_METHOD = (
    "**Does the amendment's `target:` file exist, and does its `anchor:` still "
    "resolve inside it?** §4.1 makes both admissible-or-not at the door, so they "
    "are a lookup rather than a heading sweep — but standards documents keep "
    "being edited and **a surfaced amendment whose anchor has rotted cannot be "
    "ratified as written**. Nothing today notices. A target carrying a "
    "`VENDORED — DO NOT EDIT LOCALLY` marker is called out separately: it is a "
    "mirror of a standard owned in another repo, so **its text moves without "
    "this checkout seeing the commit** and a resolving anchor here is weaker "
    "evidence than it looks."
)

VENDORED_MARKER = "VENDORED — DO NOT EDIT LOCALLY"


def build_standards(
    root: Path,
    stores: TrackedStores,
    history: History,
    as_of: date,
    collector: Collector,
    findings: list[Finding],
) -> Table:
    items = stores.items.get("standards", [])
    table = Table(
        key="standards",
        title="Table 3 · Standards amendments awaiting ratification",
        source="tracked/standards/",
        owes_definition=rules.STANDARDS_OWES,
        columns=[
            Column("id", "Id"),
            Column("title", "Title"),
            Column("count", "count"),
            Column("owes", "Ratification state"),
            Column("anchor", "Does `target:`/`anchor:` still resolve?", derived=True),
            Column("age", "How long it has sat", derived=True),
            Column("passes", "Triage passes survived", derived=True),
        ],
        scanned=len(items),
        notes=[ANCHOR_RESOLUTION_METHOD],
    )
    for item in rules.sorted_items(items):
        owed = rules.standards_owed(item)
        _contradiction(item, rules.is_terminal(item), owed, findings)
        if not owed:
            continue
        target = item.fields.get("target", "").strip().strip("`")
        anchor = item.fields.get("anchor", "").strip().strip("`")
        table.rows.append(
            Row(
                cells={
                    "id": item.fields.get("id", DASH),
                    "title": rules.title_cell(item),
                    "count": rules.count_cell(item),
                    "owes": owed[0].reason,
                    "anchor": _anchor_cell(root, target, anchor, collector),
                    "age": _age_cell(history, item.path, as_of),
                    "passes": _passes_cell(history, "standards", item.path),
                },
                source=Provenance(item.path, 1),
            )
        )
    table.suppressed = table.scanned - len(table.rows)
    return table


def _anchor_cell(root: Path, target: str, anchor: str, collector: Collector) -> str:
    """The target/anchor resolution, from ONE read of the target file.

    Both questions this cell answers — does the anchor still resolve, and is the
    target a vendored mirror — are answered from the same bytes. They used to be
    two reads, and the vendored-marker read passed a THROWAWAY collector: a
    genuine read failure there was discarded and rendered as an ordinary
    "no vendored marker", which is a page reporting a fact it did not establish.

    The read goes through the corpus reader rather than opening the file here,
    so the single within-root path guard still covers it.
    """
    if not target:
        return "no `target:` — §4.1 refuses an amendment with no named target"
    if not exists_in_root(root, target):
        return f"target missing — `{target}` is not a file in this checkout"

    text = corpus_io.read_text(root, target, collector)
    if text is None:
        # Reported as FILE_UNREADABLE by the read. Saying so is the point: the
        # anchor is not blamed for a file nobody could open.
        return f"target unreadable — `{target}` was enumerated and could not be read"

    vendored = (
        " · **vendored mirror — its target moves outside this repo**"
        if VENDORED_MARKER in text
        else ""
    )
    if not anchor:
        return f"target resolves, no `anchor:`{vendored}"
    if derivations.anchor_resolves_in(text, anchor):
        return f"resolves — `{target}` § `{anchor}`{vendored}"
    return f"**anchor rotted** — `{anchor}` no longer resolves in `{target}`{vendored}"


# ---------------------------------------------------------------------------
# Table 4 · The operator's own agenda — tracked/operations/
# ---------------------------------------------------------------------------
#
# READ-ONLY, and structurally so. This module opens no file for writing and
# imports nothing that does; `test_decisions_read_only.py` proves it by scanning
# the package's syntax tree rather than by trusting this comment. §1.2 reserves
# this store to humans — "no workflow, dispatch or agent writes into it, ever" —
# and §1.2 also records that moving `tracked/` to the repo root took the store
# OUT of every path-prefix write guard silently, so the protection is prose.
# Requirement 6 is not decoration.

OPERATIONS_READING_METHOD = (
    "The cross-field reading no file states, from §4's `status:`/`ready:` pair. "
    "**authorised and waiting** — `ready: ready` with `status: queued`, "
    "actionable now. **stale block** — `status: blocked` whose `blocked_on:` "
    "names nothing that blocks it. **in motion**, **blocked**, **not its turn** — "
    "rows that owe nothing, suppressed from the table and counted below it. "
    "A `blocked_on:` carrying a prose condition is left alone: judging whether "
    "that condition has been met would be ruling, and this page rules on nothing."
)


def build_operations(
    stores: TrackedStores,
    history: History,
    as_of: date,
    findings: list[Finding],
) -> Table:
    items = stores.items.get("operations", [])
    table = Table(
        key="operations",
        title="Table 4 · The operator's own agenda",
        source="tracked/operations/ — rendered, never written (§1.2)",
        owes_definition=rules.OPERATIONS_OWES,
        columns=[
            Column("id", "Id"),
            Column("title", "Title"),
            Column("reading", "Cross-field reading", derived=True),
            Column("state", "`status:` · `ready:`"),
            Column("blocked_on", "`blocked_on:`"),
            Column("age", "How long it has sat", derived=True),
            Column("passes", "Standups survived", derived=True),
        ],
        scanned=len(items),
        notes=[OPERATIONS_READING_METHOD],
    )
    for item in rules.sorted_items(items):
        owed = rules.operations_owed(item)
        _contradiction(item, rules.is_terminal(item), owed, findings)
        if not owed:
            continue
        table.rows.append(
            Row(
                cells={
                    "id": item.fields.get("id", DASH),
                    "title": rules.title_cell(item),
                    "reading": owed[0].kind,
                    "state": (
                        f"{rules.field_state(item, 'status')} · "
                        f"{rules.field_state(item, 'ready')}"
                    ),
                    "blocked_on": item.fields.get("blocked_on", "").strip() or DASH,
                    "age": _age_cell(history, item.path, as_of),
                    "passes": _passes_cell(history, "operations", item.path),
                },
                source=Provenance(item.path, 1),
            )
        )
    table.suppressed = table.scanned - len(table.rows)
    return table


# ---------------------------------------------------------------------------
# Table 5 · Unplaced components owing schedule-or-retire — sprints.md
# ---------------------------------------------------------------------------

STALENESS_METHOD = (
    "**Is the entry still true?** Checked against the orphan set the plan "
    "extractor derives by path — one derivation, consumed here rather than "
    "repeated. **The two subsections are checked differently, and conflating "
    "them manufactures a false stale row for every entry in the second.** Under "
    "`### Whole components`, an entry naming a component that IS now "
    "sprint-referenced is **stale and owes deletion, not a ruling**. Under "
    "`### Individual phases inside components that ARE scheduled`, the component "
    "is *expected* to be sprint-referenced — the claim is about a PHASE, so the "
    "check needs a phase-document link, and an entry that carries none says "
    "**not derivable** rather than claiming to be current. The reverse direction "
    "— an orphan the derivation finds and the list omits — is reported beneath "
    "the table."
)

#: The § Sprint: Unplaced subsection whose entries name whole unscheduled
#: components. Its sibling names phases inside components that ARE scheduled.
WHOLE_COMPONENTS = "whole components"

AGE_METHOD = (
    "From `git blame` on `sprints.md` in the checkout: the commit that last set "
    "**this entry's own line**. Recomputed per run, nothing stored. This is the "
    "column the section was built to make visible — *\"an entry that sits here "
    "across several standups without either is the thing this section was built "
    "to stop.\"*"
)


def build_unplaced(
    sprint_doc: SprintsDocument | None,
    components: list[Component],
    derived_orphans: frozenset[str],
    declared_orphans: frozenset[str],
    history: History,
    as_of: date,
    findings: list[Finding],
) -> Table:
    table = Table(
        key="unplaced",
        title="Table 5 · Unplaced components owing schedule-or-retire",
        source=f"{SPRINTS_REL} § Sprint: Unplaced — the operator's surface, reported never edited",
        owes_definition=rules.UNPLACED_OWES,
        columns=[
            Column("entry", "Entry"),
            Column("subsection", "Listed under"),
            Column("still_true", "Is it still true?", derived=True),
            Column("age", "How long it has sat", derived=True),
        ],
        notes=[STALENESS_METHOD, AGE_METHOD, _exclusions_note(components, derived_orphans)],
    )
    if sprint_doc is None:
        return table

    entries = sprint_doc.unplaced_entries
    table.scanned = len(entries)
    scheduled = scheduled_paths(sprint_doc)
    underivable: list[int] = []
    for item in entries:
        whole_component = WHOLE_COMPONENTS in item.unplaced_section.lower()
        still_true = _still_true(item, derived_orphans, scheduled, whole_component)
        if still_true is None:
            still_true = (
                "**not derivable** — the entry links no phase document, and its "
                "component is scheduled as the subsection says it is"
                if not whole_component
                else "**not derivable** — the entry links no component roadmap"
            )
            underivable.append(item.line)

        activity = history.sprint_line_activity.get(item.line)
        days = history.days_since(activity, as_of)
        age = DASH if activity is None or days is None else f"{days}d (set {activity.day})"

        table.rows.append(
            Row(
                cells={
                    "entry": item.title,
                    "subsection": item.unplaced_section or DASH,
                    "still_true": still_true,
                    "age": age,
                },
                source=Provenance(SPRINTS_REL, item.line),
            )
        )

    if underivable:
        # ONE finding carrying every line, not one per entry. The same call
        # `roadmaps.py` makes for unattributed hours: per-entry rows would put a
        # dozen near-identical lines into a section a reader then learns to skim,
        # and the defect is a property of the SECTION's shape, not of each line.
        findings.append(
            Finding(
                code=UNPLACED_STALENESS_UNDERIVABLE,
                section=SECTION_DECISIONS,
                summary=(
                    f"{len(underivable)} § Sprint: Unplaced entries link no document the "
                    "staleness check can resolve, so whether each is still true is "
                    "unknown rather than confirmed"
                ),
                provenance=Provenance(SPRINTS_REL, underivable[0]),
                expected=(
                    "a `[phase](…)` link on an entry under `### Individual phases`, or a "
                    "`[roadmap](…)` link on one under `### Whole components`"
                ),
                detail=(
                    "Lines: "
                    + ", ".join(str(line) for line in underivable)
                    + ". The section is swept by PATH rather than by name, precisely "
                    "because the previous version matched on prose and could not tell a "
                    "mention from a link. An entry linking nothing checkable inherits "
                    "that defect, and the column says so rather than reading `current`."
                ),
            )
        )

    missing = sorted(derived_orphans - set(declared_orphans))
    if missing:
        table.notes.append(
            "**Orphans the derivation finds and this list omits — each owes an "
            "entry:** " + ", ".join(f"`{p}`" for p in missing) + ". Reported here "
            "and edited in `sprints.md`, by the operator."
        )

    # Every entry owes a ruling by the section's own words, so nothing is
    # suppressed here — the suppression this table performs is on the DERIVATION
    # side, and it is stated in the exclusions note.
    table.suppressed = 0
    return table


def _still_true(
    item: SprintItem,
    derived_orphans: frozenset[str],
    scheduled_paths: frozenset[str],
    whole_component: bool,
) -> str | None:
    """The staleness reading, or ``None`` when the entry links nothing checkable."""
    if whole_component:
        paths = [p.rsplit("/", 1)[0] for p in item.link_paths if p.endswith("/roadmap.md")]
        if not paths:
            return None
        stale = [p for p in paths if p not in derived_orphans]
        if stale:
            return (
                "**stale — owes deletion, not a ruling**: "
                + ", ".join(f"`{p}`" for p in stale)
                + " is sprint-referenced outside § Sprint: Unplaced"
            )
        return "current — no sprint item outside § Sprint: Unplaced links its roadmap"

    # The second subsection's claim is about a PHASE inside a component that IS
    # scheduled, so the component being sprint-referenced proves nothing — it is
    # the subsection's stated premise. Only a phase-document link is checkable,
    # and an entry carrying none is reported as unknown rather than as current.
    phases = [p for p in item.link_paths if p.endswith(".md") and not p.endswith("/roadmap.md")]
    if not phases:
        return None
    stale = [p for p in phases if p in scheduled_paths]
    if stale:
        return (
            "**stale — owes deletion, not a ruling**: "
            + ", ".join(f"`{p}`" for p in stale)
            + " is now linked by a sprint item outside § Sprint: Unplaced"
        )
    return "current — no sprint item outside § Sprint: Unplaced links " + ", ".join(
        f"`{p}`" for p in phases
    )


def scheduled_paths(sprint_doc: SprintsDocument | None) -> frozenset[str]:
    """Every path a sprint item OUTSIDE § Sprint: Unplaced links to.

    The same predicate `derivations.derive_orphans` uses for its `body_links`,
    at phase granularity rather than component granularity. It is recomputed
    here rather than threaded through because it is a one-line projection of the
    parsed document, not a second derivation of a judgement.
    """
    if sprint_doc is None:
        return frozenset()
    out: set[str] = set()
    for sprint in sprint_doc.sprints:
        for item in sprint.items:
            if not item.in_unplaced:
                out.update(item.link_paths)
    return frozenset(out)


def _exclusions_note(components: list[Component], derived_orphans: frozenset[str]) -> str:
    """State the two structural suppressions, and name what they caught.

    § *Deliberately NOT listed* states two exclusions with reasons, and **a
    derivation that surfaces either is wrong.** The table honours them on the
    strength of the stated reason rather than by a hardcoded list:

    * **retired** — from the component's own `⚫`/`RETIRED` status line, which is
      what `plan_extractor.roadmaps` already reads;
    * **a coordination document** — a component with a roadmap, **no phase
      documents of its own**, and phase links pointing INTO other components.
      That last clause is load-bearing: `service/logging` also has a roadmap and
      no phase docs, and it IS legitimately listed, so "no phase docs" alone
      would suppress an entry the section deliberately carries.
    """
    retired = sorted(c.path for c in components if c.retired)
    coordination = sorted(
        c.path for c in components if derivations.is_coordination_document(c)
    )
    return (
        "**Structural suppressions, never a hardcoded list.** Retired components "
        "are suppressed on the strength of their own `⚫`/`RETIRED` status line: "
        + (", ".join(f"`{p}`" for p in retired) or "none in this checkout")
        + ". Coordination documents — a roadmap with no phase documents of its own "
        "whose phase links point into two or more OTHER components — are "
        "suppressed on that shape: "
        + (", ".join(f"`{p}`" for p in coordination) or "none in this checkout")
        + ". Both clauses are load-bearing: `service/logging` also has no phase "
        "docs and is legitimately listed, and `common/gpu_operations` links four "
        "other components' phases but owns two of its own."
    )

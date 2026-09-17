"""The five tables, against corpora built to carry the shapes the phase names.

Each corpus here is a whole miniature checkout rather than a hand-built object
graph, because the thing under test is what the page derives FROM A CHECKOUT —
requirement 5 — and a test that hands the builders pre-parsed items would skip
the half of the pipeline that most often breaks.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from planning_ui.decisions import derive
from planning_ui.decisions.model import (
    DECISION_CONTRADICTION,
    UNPLACED_STALENESS_UNDERIVABLE,
)

AS_OF = date(2026, 9, 2)

ROADMAP = "# {name}\n\n**Status:** 🟠 PLANNED\n"


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def candidate(id_: str, **fields: str) -> str:
    base = {
        "id": id_,
        "title": f"candidate {id_}",
        "status": "open",
        "count": "1",
        "filed": "2026-08-01",
        "filed_by": "review-pr",
        "component": "development/common/widget",
        "size": "M",
        "decision": "ship",
    }
    base.update(fields)
    body = "\n".join(f"{key}: {value}" for key, value in base.items())
    return f"---\n{body}\n---\n\nBody.\n"


def minimal_corpus(root: Path) -> None:
    """A checkout with all four stores, one component and a sprints.md."""
    write(root, "development/common/widget/roadmap.md", ROADMAP.format(name="Widget"))
    write(root, "development/common/widget/phase1_first.md", "# Phase 1\n")
    write(
        root,
        "development/sprints.md",
        "# Implementation Plan\n\n"
        "## Sprint: Alpha\n"
        "🟠 PLANNED\n\n"
        "- [ ] **common/widget · One** · L1 · "
        "([roadmap](./common/widget/roadmap.md) · [phase](./common/widget/phase1_first.md)) — **~2h**\n"
        "- [ ] **Sprint close-out** — recurring checks run\n\n"
        "## Sprint: Unplaced — every entry owes a ruling\n"
        "🔵 NOT SCHEDULED\n\n"
        "### Whole components — planning exists, nothing schedules it\n\n"
        "- [ ] **Widget — everything** · ([roadmap](./common/widget/roadmap.md)) — declared\n\n"
        "### Individual phases inside components that ARE scheduled\n\n"
        "- [ ] **Widget — a later phase** · ([roadmap](./common/widget/roadmap.md)) — a phase\n\n"
        "### Deliberately NOT listed\n\n"
        "**`common/nothing/`** is retired and a sweep that flags it is wrong.\n",
    )
    for store, prefix, extra in (
        ("issues", "I", "repo: example-app"),
        ("operations", "O", "ownership: operator\nblocked_on: none\nready: not-ready"),
        ("standards", "S", "target: development/sprints.md\nanchor: Sprint\nratification: ratified"),
    ):
        write(
            root,
            f"tracked/{store}/{prefix}-00000000.md",
            f"---\nid: {prefix}-00000000\ntitle: t\nstatus: resolved\ncount: 1\n"
            f"filed: 2026-08-01\nfiled_by: operator\n{extra}\n---\n\nBody.\n",
        )
    write(root, "tracked/candidates/C-00000000.md", candidate("C-00000000"))


# ---------------------------------------------------------------------------
# Step 4's contradiction: a terminal state held while a ruling is still owed
# ---------------------------------------------------------------------------
def test_adopted_with_a_blank_size_is_a_named_finding_and_is_never_smoothed(tmp_path: Path):
    """The operator's 2026-09-02 ruling, in code.

    `decision:` is set autonomously by `triage-candidates` from code, so an item
    in this state is evidence of a tooling defect or of hand-editing predating
    the standards now governing these files. **The fix belongs at the source**,
    and a display-layer rule mapping the contradiction onto "owing triage" would
    hide the very defect the page exists to expose. So: a finding, and the row
    still appears with its owed sizing named.

    Zero instances exist in the live corpus today — the six that prompted the
    step were reverted on 2026-08-28 (`5e185bc`) — so this pins the behaviour for
    when the next real triage pass recreates the state.
    """
    root = tmp_path / "corpus"
    minimal_corpus(root)
    write(
        root,
        "tracked/candidates/C-11111111.md",
        candidate("C-11111111", status="adopted", decision="ship", size=""),
    )

    page = derive(root, as_of=AS_OF)
    contradictions = [f for f in page.findings if f.code == DECISION_CONTRADICTION]
    assert len(contradictions) == 1
    assert "adopted" in contradictions[0].summary
    assert "sizing" in contradictions[0].summary
    assert contradictions[0].provenance.file == "tracked/candidates/C-11111111.md"
    # …and the prune clock is named as the consequence, which is the reason the
    # contradiction matters rather than merely being untidy.
    assert "prune clock" in contradictions[0].detail

    # The row is NOT suppressed and NOT normalised: it still owes sizing.
    candidates_table = next(t for t in page.tables if t.key == "candidates")
    row = next(r for r in candidates_table.rows if r.cells["id"] == "C-11111111")
    assert "sizing" in row.cells["owes"]


def test_a_terminal_item_owing_nothing_produces_no_contradiction(tmp_path: Path):
    """The negative half — the finding is about the CONTRADICTION, not about adoption."""
    root = tmp_path / "corpus"
    minimal_corpus(root)
    write(
        root,
        "tracked/candidates/C-22222222.md",
        candidate("C-22222222", status="adopted", decision="ship", size="M"),
    )
    page = derive(root, as_of=AS_OF)
    assert [f for f in page.findings if f.code == DECISION_CONTRADICTION] == []


# ---------------------------------------------------------------------------
# Requirement 1: no row appears that cannot be ruled on
# ---------------------------------------------------------------------------
def test_a_fully_ruled_store_renders_no_rows_and_says_how_many_it_read(tmp_path: Path):
    """A short table and an empty store must stay distinguishable.

    Only one of them is good news, and a table that shows a row count without a
    scanned count cannot tell them apart.
    """
    root = tmp_path / "corpus"
    minimal_corpus(root)
    page = derive(root, as_of=AS_OF)

    issues = next(t for t in page.tables if t.key == "issues")
    assert issues.rows == []
    assert issues.scanned == 1
    assert issues.suppressed == 1


def test_every_table_carries_at_least_one_derived_column(tmp_path: Path):
    """Requirement 2, asserted structurally rather than by reading the page.

    Without a derived column the page is a re-render of files a reader could
    already open, which the roadmap's page rule forbids.
    """
    root = tmp_path / "corpus"
    minimal_corpus(root)
    page = derive(root, as_of=AS_OF)
    for table in page.tables + page.crossings:
        assert any(c.derived for c in table.columns), table.key


def test_every_table_states_its_own_owes_a_ruling_definition(tmp_path: Path):
    """Requirement 1: the phrase means something different in each of the five."""
    root = tmp_path / "corpus"
    minimal_corpus(root)
    page = derive(root, as_of=AS_OF)
    definitions = [t.owes_definition for t in page.tables]
    assert all(len(d) > 80 for d in definitions)
    assert len(set(definitions)) == len(definitions), "two tables share one definition"


# ---------------------------------------------------------------------------
# Requirement 4: non-conformance is a named finding, never a silent omission
# ---------------------------------------------------------------------------
def test_an_item_missing_a_core_field_is_a_finding_not_a_shorter_table(
    fixture_corpus: Path,
):
    """The §3 shared-core check, verified through this page rather than assumed.

    The implementation step asks to point the page at a fixture item missing a
    core field and observe a **named finding rather than a shorter table**. The
    fixture's `I-bbbbbbbb` is missing `filed_by:`, and it must still appear as a
    row in table 2 — dropping it would be the silent omission.
    """
    page = derive(fixture_corpus, as_of=AS_OF)
    missing = [
        f
        for f in page.findings
        if f.code == "TRACKED_CORE_FIELD_MISSING"
        and f.provenance.file == "tracked/issues/I-bbbbbbbb.md"
    ]
    assert missing, "the malformed item produced no finding"
    assert "filed_by" in missing[0].summary

    issues = next(t for t in page.tables if t.key == "issues")
    assert {row.cells["id"] for row in issues.rows} == {"I-aaaaaaaa", "I-bbbbbbbb"}


# ---------------------------------------------------------------------------
# Table 5: the two subsections are checked differently
# ---------------------------------------------------------------------------
def test_a_whole_component_entry_that_is_now_scheduled_reads_as_stale(tmp_path: Path):
    root = tmp_path / "corpus"
    minimal_corpus(root)
    page = derive(root, as_of=AS_OF)
    unplaced = next(t for t in page.tables if t.key == "unplaced")
    whole = next(r for r in unplaced.rows if "everything" in r.cells["entry"])
    assert "stale — owes deletion" in whole.cells["still_true"]


def test_a_phase_entry_is_not_read_as_stale_merely_because_its_component_is_scheduled(
    tmp_path: Path,
):
    """The subsection's own premise is that the component IS scheduled.

    Applying the whole-component check to it manufactures a false stale row for
    every entry in the second subsection — seven of them on the live corpus.
    """
    root = tmp_path / "corpus"
    minimal_corpus(root)
    page = derive(root, as_of=AS_OF)
    unplaced = next(t for t in page.tables if t.key == "unplaced")
    phase_entry = next(r for r in unplaced.rows if "later phase" in r.cells["entry"])
    assert "stale" not in phase_entry.cells["still_true"]
    assert "not derivable" in phase_entry.cells["still_true"]


def test_an_unresolvable_entry_produces_one_finding_carrying_every_line(tmp_path: Path):
    """One finding for the section's shape, not one per entry.

    Per-entry rows would put a dozen near-identical lines into a section a reader
    then learns to skim, and the defect is a property of the section rather than
    of each line — the same call `roadmaps.py` makes for unattributed hours.
    """
    root = tmp_path / "corpus"
    minimal_corpus(root)
    page = derive(root, as_of=AS_OF)
    underivable = [f for f in page.findings if f.code == UNPLACED_STALENESS_UNDERIVABLE]
    assert len(underivable) == 1
    assert "Lines:" in underivable[0].detail


# ---------------------------------------------------------------------------
# The § Sprint: Unplaced exclusions are STRUCTURAL, not a name list
# ---------------------------------------------------------------------------
def _coordination_corpus(root: Path, with_stated_exclusions: bool) -> None:
    """A checkout with a retired component, a coordination document and a logger.

    The three shapes the exclusions have to tell apart:

    * ``workload/gone`` — retired, suppressible from its own status line;
    * ``common/sequencer`` — a roadmap with no phase docs of its own linking two
      OTHER components' phases: a coordination document;
    * ``service/quiet`` — a roadmap with no phase docs and no external links,
      which is an ordinary unbuilt component and MUST still be reported.
    """
    write(root, "development/common/widget/roadmap.md", ROADMAP.format(name="Widget"))
    write(root, "development/common/widget/phase1_first.md", "# Phase 1\n")
    write(root, "development/common/other/roadmap.md", ROADMAP.format(name="Other"))
    write(root, "development/common/other/phase1_first.md", "# Phase 1\n")
    write(
        root,
        "development/workload/gone/roadmap.md",
        "# Gone\n\n**Status:** ⚫ **RETIRED 2026-08-21.** No sale.\n",
    )
    write(
        root,
        "development/common/sequencer/roadmap.md",
        "# Sequencer\n\n**Status:** 🟠 PLANNED\n\n"
        "It sequences [widget phase](../widget/phase1_first.md) and "
        "[other phase](../other/phase1_first.md) into vertical slices.\n",
    )
    write(root, "development/service/quiet/roadmap.md", ROADMAP.format(name="Quiet"))

    exclusions = (
        "\n### Deliberately NOT listed\n\n"
        "**`workload/gone/`** is retired.\n\n"
        "**`common/sequencer/`** is a coordination document.\n"
        if with_stated_exclusions
        else ""
    )
    write(
        root,
        "development/sprints.md",
        "# Implementation Plan\n\n"
        "## Sprint: Alpha\n"
        "🟠 PLANNED\n\n"
        "- [ ] **common/widget · One** · L1 · "
        "([roadmap](./common/widget/roadmap.md) · [phase](./common/widget/phase1_first.md)) — **~2h**\n"
        "- [ ] **common/other · One** · L1 · "
        "([roadmap](./common/other/roadmap.md) · [phase](./common/other/phase1_first.md)) — **~2h**\n\n"
        "## Sprint: Unplaced — every entry owes a ruling\n"
        "🔵 NOT SCHEDULED\n\n"
        "### Whole components — planning exists, nothing schedules it\n\n"
        "- [ ] **Quiet — everything** · ([roadmap](./service/quiet/roadmap.md)) — unscheduled\n"
        + exclusions,
    )
    for store, prefix in (("issues", "I"), ("operations", "O"), ("standards", "S"), ("candidates", "C")):
        write(
            root,
            f"tracked/{store}/{prefix}-00000000.md",
            f"---\nid: {prefix}-00000000\ntitle: t\nstatus: resolved\ncount: 1\n"
            f"filed: 2026-08-01\nfiled_by: operator\n---\n\nBody.\n",
        )


@pytest.mark.parametrize("with_stated_exclusions", [True, False])
def test_the_exclusions_hold_without_the_stated_list(tmp_path: Path, with_stated_exclusions: bool):
    """The implementation step's actual demand.

    *"Verify `workload/probe` and `common/vm_orch` are absent from the
    output, and that the suppression derives from the retired status line and the
    no-phase-docs shape rather than from a hardcoded list."*

    So the corpus is built twice — once with the § *Deliberately NOT listed*
    prose and once without it — and both must suppress. Only a structural test
    can pass the second parametrisation.
    """
    root = tmp_path / "corpus"
    _coordination_corpus(root, with_stated_exclusions)
    page = derive(root, as_of=AS_OF)
    unplaced = next(t for t in page.tables if t.key == "unplaced")
    note = " ".join(unplaced.notes)

    assert "development/workload/gone" in note
    assert "development/common/sequencer" in note
    # Neither is reported as an orphan owing an entry…
    missing_note = next((n for n in unplaced.notes if "owes an entry" in n), "")
    assert "workload/gone" not in missing_note
    assert "common/sequencer" not in missing_note


def test_an_ordinary_component_with_no_phase_docs_is_still_reported(tmp_path: Path):
    """The clause that keeps the suppression from eating a legitimate entry.

    `service/quiet` has a roadmap and no phase docs — the same shape as a
    coordination document minus the external links — and it is declared in the
    list. "No phase docs" alone would suppress it, and the live corpus carries
    exactly this case in `service/logging`.
    """
    root = tmp_path / "corpus"
    _coordination_corpus(root, with_stated_exclusions=False)
    page = derive(root, as_of=AS_OF)
    unplaced = next(t for t in page.tables if t.key == "unplaced")
    quiet = next(r for r in unplaced.rows if "Quiet" in r.cells["entry"])
    assert quiet.cells["still_true"].startswith("current")


def test_the_page_describes_the_mechanism_it_actually_has(fixture_corpus: Path):
    """Phase 6 requirement 5, for the second page: it used to say *"Derived per
    request from the checkout … nothing committed"*. It is committed."""
    from planning_ui.decisions import render_markdown

    text = render_markdown(derive(fixture_corpus, as_of=AS_OF))
    assert "per request" not in text
    assert "nothing committed" not in text
    assert "committed at `development/derived/`" in text


@pytest.mark.parametrize(
    "raw,prefix",
    [
        ("example-app", "well-formed"),
        ("example-planning", "well-formed"),
        ("", "unset"),
        # The three spellings §4.0 records as drift on 2026-09-10.
        ("helloskyy-io/Claude-Dot-Files", "malformed"),
        ("Skyy-Command", "malformed"),
        ("example-app/backend", "malformed"),
    ],
)
def test_the_repo_column_checks_the_binding_form_from_the_text_alone(raw: str, prefix: str):
    """Phase 6: the column must answer the same from any checkout location.

    It used to enumerate the git repositories BESIDE the checkout — so a
    worktree under `.claude/worktrees/` answered "does not resolve" for every
    item, a pull-request runner answered "resolves" only for the repository it
    was checking out, and the committed page went STALE on the first CI run.
    §4.0 binds the field's FORM because it is matched on; that is checkable
    from the text.
    """
    from planning_ui.decisions.tables import repo_field_cell

    assert repo_field_cell(raw).startswith(prefix), repo_field_cell(raw)

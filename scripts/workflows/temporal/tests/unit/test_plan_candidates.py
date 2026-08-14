"""`plan-candidates` — the scaffolder, and the four conditions that gate it.

WHY THIS IS AN ACTIVITY AND NOT A CHILD, WHICH IS WHY THESE TESTS EXIST AT ALL.
The job is to move what triage already decided to where the next step reads
from: create `docs/development/<component>/research/` and seed `synthesis.md`
from the candidate's own summary. Triage ruled `ship`; the filer named the
component. Nothing is left to judge, so nothing needs a model — and a
deterministic activity is testable in-process, at no dispatch cost, which a
prompt is not.

An earlier attempt built the same job as a model child: 1,605 lines, a 173-line
prompt, and eight review holds every one of which was a consequence of it being
a dispatch. It was closed rather than repaired. The test file for that shape
could not have existed.

WHAT THE FOUR SKIPS ACTUALLY PROTECT, since three of them look alike:

  * not `ship` — triage has not agreed, or has refused.
  * not `open` — already handled.
  * blank `component` — an UNANSWERED QUESTION. The filer knows and did not say;
    guessing from a one-line summary is exactly what this code must not do.
  * directory exists — the candidate EXTENDS something already planned. Seeding
    a synthesis on top of a live component's research pool would overwrite real
    findings with a one-line proposal, and that is the expensive one.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from modules.assistant.plan import plan_activities as act  # noqa: E402
from modules.assistant.plan.plan_project import plan_project_activities as own  # noqa: E402

_HEADER = (
    "| ID | Candidate | `component` | Source | `decision` | `status` | Note |\n"
    "|---|---|---|---|---|---|---|\n"
)


def _table(*rows: tuple[str, str, str, str, str]) -> str:
    """Rows as `(id, title, component, decision, status)`, in the real shape."""
    body = "".join(f"| {r[0]} | {r[1]} | {r[2]} | PR #1 | {r[3]} | {r[4]} | note |\n"
                   for r in rows)
    return "# Action candidates\n\n" + _HEADER + body


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    (tmp_path / "docs" / "development").mkdir(parents=True)
    return tmp_path


def _write(tree: Path, content: str) -> Path:
    f = tree / "candidates.md"
    f.write_text(content)
    return f


# --- vacuity floor --------------------------------------------------------

def test_a_shipped_open_named_row_IS_scaffolded(tree: Path) -> None:
    """The floor: if this does not fire, every skip assertion below is vacuous."""
    f = _write(tree, _table(
        ("C-001", "A thing worth building", "fleet-reliability", "`ship`", "`open`")))
    assert own.scaffold_candidate_components(tree, f) == ["fleet-reliability"]
    pool = tree / "docs" / "development" / "fleet-reliability" / "research"
    assert pool.is_dir(), "the research pool is the whole deliverable"
    assert (pool / "synthesis.md").is_file()


# --- the four skips -------------------------------------------------------

@pytest.mark.parametrize("decision", ["", "`requires review`", "`reject`"])
def test_only_a_SHIP_row_is_scaffolded(tree: Path, decision: str) -> None:
    """Blank is untriaged, not permission. `reject` is a decision, not an absence."""
    f = _write(tree, _table(("C-001", "t", "some-component", decision, "`open`")))
    assert own.scaffold_candidate_components(tree, f) == []
    assert not (tree / "docs" / "development" / "some-component").exists()


def test_a_CLOSED_row_is_not_scaffolded(tree: Path) -> None:
    """`closed` means the work is done. Scaffolding it would re-open finished work."""
    f = _write(tree, _table(("C-001", "t", "some-component", "`ship`", "`closed`")))
    assert own.scaffold_candidate_components(tree, f) == []
    assert not (tree / "docs" / "development" / "some-component").exists()


@pytest.mark.parametrize("blank", ["", " ", "—", "-", "  —  ", "` — `"])
def test_a_BLANK_component_scaffolds_NOTHING_and_fails_NOTHING(
        tree: Path, blank: str) -> None:
    """A blank is an unanswered question, and answering it is not this code's job.

    EVERY SPELLING OF EMPTY, because `normalise_cell` exists precisely because two
    hand-written normalisations drifted and a row read as ruled to one reader and
    blank to the other. An em dash reaching the filesystem would create
    `docs/development/-/`, and a directory named for the absence of an answer is
    worse than no directory: it exists, so the exists-check skips it forever.
    """
    f = _write(tree, _table(("C-001", "t", blank, "`ship`", "`open`")))
    assert own.scaffold_candidate_components(tree, f) == []
    made = sorted(p.name for p in (tree / "docs" / "development").iterdir())
    assert made == [], f"a blank component created {made}"


def test_an_EXISTING_component_directory_is_left_completely_alone(tree: Path) -> None:
    """The expensive skip: an existing name means the candidate EXTENDS that component.

    The failure this prevents is not a wasted directory — it is a one-line
    proposal overwriting a pool that already holds real research. Asserted on the
    CONTENT, not on the return value, because a scaffolder that returned `[]` and
    wrote the file anyway would pass a return-value-only check.
    """
    pool = tree / "docs" / "development" / "memory-management-framework" / "research"
    pool.mkdir(parents=True)
    (pool / "synthesis.md").write_text("REAL RESEARCH, twenty-five papers deep\n")

    f = _write(tree, _table(
        ("C-001", "t", "memory-management-framework", "`ship`", "`open`")))
    assert own.scaffold_candidate_components(tree, f) == []
    assert (pool / "synthesis.md").read_text() == "REAL RESEARCH, twenty-five papers deep\n"


# --- what the seeded document has to carry --------------------------------

def test_the_seed_names_the_candidate_it_came_from(tree: Path) -> None:
    """The `C-NNN` id is the only link back from the folder to the row that authorised it.

    Without it a reader finding this folder cannot tell scaffolding from
    abandoned work — and the summary alone does not say it is a proposal.
    """
    f = _write(tree, _table(
        ("C-042", "Automate the fleet's deployment", "fleet-deploy", "`ship`", "`open`")))
    own.scaffold_candidate_components(tree, f)
    seed = (tree / "docs" / "development" / "fleet-deploy" / "research"
            / "synthesis.md").read_text()

    assert "C-042" in seed, "no link back to the authorising row"
    assert "Automate the fleet's deployment" in seed, "the candidate summary was dropped"
    assert "project-wide planning" in seed, "provenance is the point of the seed"
    assert "candidate for inclusion" in seed


def test_the_seed_does_NOT_claim_research_or_planning_that_does_not_exist(tree: Path) -> None:
    """It is a HANDOFF, and a handoff that reads as findings is worse than none.

    `plan-candidates` writes no `roadmap.md` and no phase docs — `plan-feature`
    does — and it does no research. A seeded file that did not say so would be
    read by the next pass as a thin synthesis rather than an empty one.
    """
    f = _write(tree, _table(("C-001", "t", "new-thing", "`ship`", "`open`")))
    own.scaffold_candidate_components(tree, f)
    seed = (tree / "docs" / "development" / "new-thing" / "research"
            / "synthesis.md").read_text()

    assert "No research has been done yet" in seed
    assert "roadmap.md" in seed and "plan-feature" in seed, (
        "the seed must say who writes the roadmap, or the gap reads as an omission")
    assert not (tree / "docs" / "development" / "new-thing" / "roadmap.md").exists(), (
        "plan-candidates wrote a roadmap; that is plan-feature's and is out of scope")


def test_it_creates_the_research_pool_and_NOTHING_else(tree: Path) -> None:
    """Scope, asserted against the filesystem rather than against the docstring."""
    f = _write(tree, _table(("C-001", "t", "new-thing", "`ship`", "`open`")))
    own.scaffold_candidate_components(tree, f)
    root = tree / "docs" / "development" / "new-thing"
    assert sorted(p.name for p in root.iterdir()) == ["research"]
    assert sorted(p.name for p in (root / "research").iterdir()) == ["synthesis.md"]


# --- shape and convergence ------------------------------------------------

def test_a_component_NAME_is_slugged_to_the_convention_the_tree_follows(
        tree: Path) -> None:
    """`Fleet Reliability` -> `fleet-reliability`, via the same `component_dir`.

    A filer typing a display name rather than a folder name must not produce a
    directory that every reconciliation walking `docs/development/` misses.
    """
    f = _write(tree, _table(("C-001", "t", "Fleet Reliability", "`ship`", "`open`")))
    assert own.scaffold_candidate_components(tree, f) == ["fleet-reliability"]
    assert (tree / "docs" / "development" / "fleet-reliability").is_dir()


def test_a_second_run_over_an_unchanged_file_is_a_NO_OP(tree: Path) -> None:
    """CONVERGENT, not idempotent — and under Temporal a retry is a new attempt.

    The exists-check is what makes a replay safe. Asserted on the seed CONTENT
    too: a second run that re-wrote the file would silently discard whatever the
    research child had put there between the two attempts.
    """
    f = _write(tree, _table(("C-001", "t", "new-thing", "`ship`", "`open`")))
    assert own.scaffold_candidate_components(tree, f) == ["new-thing"]

    seed = tree / "docs" / "development" / "new-thing" / "research" / "synthesis.md"
    seed.write_text("the research child has since written this\n")

    assert own.scaffold_candidate_components(tree, f) == []
    assert seed.read_text() == "the research child has since written this\n"


def test_every_eligible_row_is_scaffolded_not_just_the_first(tree: Path) -> None:
    """A loop that returned on its first hit would pass every test above."""
    f = _write(tree, _table(
        ("C-001", "t", "alpha", "`ship`", "`open`"),
        ("C-002", "t", "", "`ship`", "`open`"),
        ("C-003", "t", "beta", "`reject`", "`open`"),
        ("C-004", "t", "gamma", "`ship`", "`open`"),
    ))
    assert own.scaffold_candidate_components(tree, f) == ["alpha", "gamma"]


def test_two_rows_naming_the_SAME_component_scaffold_it_once(tree: Path) -> None:
    """The second row extends the first, which is the exists-check doing its job.

    It fires WITHIN a single run, not just across runs — the directory the first
    row created is on disk by the time the second row is read.
    """
    f = _write(tree, _table(
        ("C-001", "first", "shared", "`ship`", "`open`"),
        ("C-002", "second", "shared", "`ship`", "`open`"),
    ))
    assert own.scaffold_candidate_components(tree, f) == ["shared"]
    seed = (tree / "docs" / "development" / "shared" / "research"
            / "synthesis.md").read_text()
    assert "C-001" in seed and "C-002" not in seed, (
        "the FIRST row scaffolded it; the second must not overwrite the seed")


def test_a_MISSING_candidates_file_raises_and_says_what_is_now_unknown(
        tree: Path) -> None:
    """Loud, not empty. An empty list here is indistinguishable from 'nothing eligible'.

    In production the triage child reads the same file first and would raise
    before this runs — but the parent must not depend on a sibling's failure to
    surface its own missing input.
    """
    with pytest.raises(FileNotFoundError) as exc:
        own.scaffold_candidate_components(tree, tree / "nope.md")
    assert "nothing to scaffold" in str(exc.value)


# --- the parse the whole thing rests on -----------------------------------

def test_the_row_parse_survives_UNESCAPED_PIPES_IN_THE_NOTE(tree: Path) -> None:
    """Measured on the live file 2026-08-13: four rows of 76 carry pipes in the Note.

    Anything that splits a row on `|` and re-joins reads a different cell count
    per row and mis-assigns every column after the stray pipe. The regex stops
    each cell at the next pipe and never reaches the Note, so a Note may contain
    anything at all. This is the property the column insertion depended on.
    """
    f = _write(tree, _table(("C-001", "t", "piped", "`ship`", "`open`")))
    f.write_text(f.read_text().replace(
        "| note |", "| a | b | c note with | pipes | in it |"))

    rows = act.candidate_rows(f, missing_hint="x")
    assert len(rows) == 1
    assert (rows[0].id, rows[0].component, rows[0].decision, rows[0].status) == (
        "C-001", "piped", "ship", "open")
    assert own.scaffold_candidate_components(tree, f) == ["piped"]


def test_the_parse_is_NAMED_so_a_widened_row_cannot_silently_shift_a_guard() -> None:
    """`component` was inserted between `Candidate` and `Source` and moved two columns.

    Three call sites unpack this — two of them are AUTHORIZATION GUARDS that
    prove a run did not write a column it does not own. A positional tuple would
    have re-pointed them by one and still returned a clean dict over the wrong
    field, which is invisible exactly where invisibility costs most.
    """
    assert act.CandidateRow._fields == (
        "id", "title", "component", "decision", "status")

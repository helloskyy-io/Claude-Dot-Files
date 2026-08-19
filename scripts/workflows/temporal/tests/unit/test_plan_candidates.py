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

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from modules.assistant.plan import plan_activities as act  # noqa: E402
from modules.assistant.plan.plan_project import plan_project_activities as own  # noqa: E402

_HEADER = (
    "| ID | Candidate | `component` | Source | `decision` | `size` | `status` | Note |\n"
    "|---|---|---|---|---|---|---|---|---|\n"
)


def _table(*rows: tuple[str, ...]) -> str:
    """Rows as `(id, title, component, decision, status[, size])`, in the real shape.

    `size` DEFAULTS TO `feature` HERE, and that is the opposite of the default in
    `test_triage_candidates_split.py`. The subject of this module is scaffolding,
    and only a `feature` scaffolds — so every pre-existing assertion about *does
    this row scaffold* is about a feature-sized row whether it said so or not.
    Defaulting to blank would have made all of them assert the new skip path
    instead, which is a different test wearing the old name.
    """
    body = "".join(
        f"| {r[0]} | {r[1]} | {r[2]} | PR #1 | {r[3]} | "
        f"{r[5] if len(r) > 5 else 'feature'} | {r[4]} | note |\n"
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


# ASSERTED AGAINST THE WHOLE RESULT, NOT AGAINST `.created`. Every skip below
# says a row produced no directory; comparing only `created` would pass equally
# for a row that landed in the wrong OTHER bucket — an `extends` reported as an
# `unnamed` is a different fact about the file and a different note to the
# operator. `_replace` names the one field a test expects to differ.
_NOTHING = own.Scaffolded(created=[], resumed=[], extends=[], unnamed=[])


# --- vacuity floor --------------------------------------------------------

def test_a_shipped_open_named_row_IS_scaffolded(tree: Path) -> None:
    """The floor: if this does not fire, every skip assertion below is vacuous."""
    f = _write(tree, _table(
        ("C-001", "A thing worth building", "fleet-reliability", "`ship`", "`open`")))
    assert own.scaffold_candidate_components(tree, f).created == ["fleet-reliability"]
    pool = tree / "docs" / "development" / "fleet-reliability" / "research"
    assert pool.is_dir(), "the research pool is the whole deliverable"
    assert (pool / "synthesis.md").is_file()


# --- the four skips -------------------------------------------------------

@pytest.mark.parametrize("decision", ["", "`requires review`", "`reject`"])
def test_only_a_SHIP_row_is_scaffolded(tree: Path, decision: str) -> None:
    """Blank is untriaged, not permission. `reject` is a decision, not an absence."""
    f = _write(tree, _table(("C-001", "t", "some-component", decision, "`open`")))
    assert own.scaffold_candidate_components(tree, f) == _NOTHING
    assert not (tree / "docs" / "development" / "some-component").exists()


def test_a_CLOSED_row_is_not_scaffolded(tree: Path) -> None:
    """`closed` means the work is done. Scaffolding it would re-open finished work."""
    f = _write(tree, _table(("C-001", "t", "some-component", "`ship`", "`closed`")))
    assert own.scaffold_candidate_components(tree, f) == _NOTHING
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
    assert own.scaffold_candidate_components(tree, f) == _NOTHING
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
    assert own.scaffold_candidate_components(tree, f) == _NOTHING._replace(
        extends=[("C-001", "memory-management-framework")])
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
    assert own.scaffold_candidate_components(tree, f).created == ["fleet-reliability"]
    assert (tree / "docs" / "development" / "fleet-reliability").is_dir()


def test_a_second_run_over_an_unchanged_file_is_a_NO_OP(tree: Path) -> None:
    """IDEMPOTENT (§7.1) by check-then-act — and under Temporal a retry is a new attempt.

    The exists-check is what makes a replay safe. Asserted on the seed CONTENT
    too: a second run that re-wrote the file would silently discard whatever the
    research child had put there between the two attempts.
    """
    f = _write(tree, _table(("C-001", "t", "new-thing", "`ship`", "`open`")))
    assert own.scaffold_candidate_components(tree, f).created == ["new-thing"]

    seed = tree / "docs" / "development" / "new-thing" / "research" / "synthesis.md"
    seed.write_text("the research child has since written this\n")

    assert own.scaffold_candidate_components(tree, f) == _NOTHING._replace(
        extends=[("C-001", "new-thing")])
    assert seed.read_text() == "the research child has since written this\n"


def test_every_eligible_row_is_scaffolded_not_just_the_first(tree: Path) -> None:
    """A loop that returned on its first hit would pass every test above."""
    f = _write(tree, _table(
        ("C-001", "t", "alpha", "`ship`", "`open`"),
        ("C-002", "t", "", "`ship`", "`open`"),
        ("C-003", "t", "beta", "`reject`", "`open`"),
        ("C-004", "t", "gamma", "`ship`", "`open`"),
    ))
    assert own.scaffold_candidate_components(tree, f).created == ["alpha", "gamma"]


def test_two_rows_naming_the_SAME_component_scaffold_it_once(tree: Path) -> None:
    """The second row EXTENDS the first, and the bucket is the assertion.

    It fires WITHIN a single run, not just across runs — the directory the first
    row created is on disk by the time the second row is read.

    THIS ASSERTED `.created` ALONE, WHICH IS THE ONE FIELD THAT WAS RIGHT. The
    second row's directory exists but its `synthesis.md` still carries the marker
    this same loop wrote a moment earlier, so `_is_unresearched` said yes and the
    slug landed in `resumed` as well: `created=['shared'], resumed=['shared']`,
    `to_research` carrying it twice, and the parent emitting two contradictory
    notes — "scaffolded from a shipped candidate" and "seeded by an earlier pass
    and never researched" — of which the second is false. Every other test in this
    module compares the WHOLE result against `_NOTHING._replace(...)` for exactly
    this reason (see its comment); this one opted out on the single test where the
    bucket was wrong.
    """
    f = _write(tree, _table(
        ("C-001", "first", "shared", "`ship`", "`open`"),
        ("C-002", "second", "shared", "`ship`", "`open`"),
    ))
    assert own.scaffold_candidate_components(tree, f) == own.Scaffolded(
        created=["shared"], resumed=[], extends=[("C-002", "shared")], unnamed=[]), (
        "the second row must EXTEND the component the first created — a `resumed` "
        "here tells the operator a previous run died, and duplicates the research")
    seed = (tree / "docs" / "development" / "shared" / "research"
            / "synthesis.md").read_text()
    assert "C-001" in seed and "C-002" not in seed, (
        "the FIRST row scaffolded it; the second must not overwrite the seed")


@pytest.mark.parametrize("label,pre_seed", [
    ("both rows create it in this run", False),
    ("both rows resume a pool a PREVIOUS run seeded and abandoned", True),
], ids=["created+created", "resumed+resumed"])
def test_to_research_NEVER_NAMES_A_COMPONENT_TWICE(
        tree: Path, label: str, pre_seed: bool) -> None:
    """THE PROPERTY, NOT ONE EXAMPLE OF IT — and the sibling path is why.

    The previous pass found two rows naming one component landing in `created`
    AND `resumed`, fixed it with `if slug in result.created`, and wrote a test
    asserting the created+created pair. That closed one half of a symmetric pair
    and left the other open: two rows naming a component a PREVIOUS run seeded
    and never researched both pass the exists-check, both see the marker, and
    both append — `resumed=['shared', 'shared']`, reproduced before the fix.

    So this asserts the INVARIANT `to_research` has to satisfy however a slug
    got there — no component named twice — parametrized over both paths into it.
    A third bucket feeding research later inherits the assertion rather than
    needing its own test, which is the whole difference between closing a
    spelling and closing the class.

    `extends` deliberately DOES repeat: it names ROWS, and two rows extending one
    component are two facts about the file, each with its own `C-NNN` for the
    operator's note.
    """
    if pre_seed:
        first = _write(tree, _table(("C-000", "seeded earlier", "shared", "`ship`", "`open`")))
        assert own.scaffold_candidate_components(tree, first).created == ["shared"]

    f = _write(tree, _table(
        ("C-001", "first", "shared", "`ship`", "`open`"),
        ("C-002", "second", "shared", "`ship`", "`open`"),
    ))
    result = own.scaffold_candidate_components(tree, f)

    assert len(set(result.to_research)) == len(result.to_research), (
        f"{label}: to_research is {result.to_research} — one component named "
        f"twice is two operator notes and two research dispatches for one pool")
    assert result.to_research == ["shared"]
    assert result.extends == [("C-002", "shared")], (
        f"{label}: the row that lost the race must be reported as extending the "
        f"component, naming its own id — got {result.extends}")


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
    """The Note is the ONLY cell that may carry a pipe, and rows in the live file do.

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
    assert own.scaffold_candidate_components(tree, f).created == ["piped"]


# --- the shape check, keyed on the CLASS ----------------------------------
#
# ONE FAILURE, THREE DOORS INTO IT: a row that reads as TRIAGED without anybody
# having ruled it, or a row that is not there at all. Either way it leaves the
# untriaged working set, `triage-candidates` reports a complete pass over it, and
# nothing is red.
#
# THE FIRST VERSION OF THIS TEST PASSED WHILE THE GUARD DID NOT FIRE, and that is
# why the parametrization below is over SHAPES rather than one example. The guard
# was `if _HEADER not in text` — a whole-file substring test — and this test's
# fixture held exactly ONE table, so the two agreed by construction. The real
# file holds NINE candidate tables: reverting one of them and leaving the other
# eight correct satisfied the guard, and the untriaged count fell from 33 to 25
# with nothing raised. A single-table fixture cannot see a whole-file check's
# scope error; `_nine_tables` is what makes the difference visible.

_SIX_COL = ("| ID | Candidate | Source | `decision` | `status` | Note |\n"
            "|---|---|---|---|---|---|\n")


def _nine_tables(bad: str) -> str:
    """Eight well-formed candidate tables and one `bad` one, as the real file is shaped."""
    good = "".join(
        f"\n## Cycle {n}\n\n{_HEADER}| C-{n:03d} | t | c | PR #1 | `ship` | feature | `open` | n |\n"
        for n in range(1, 9))
    return "# Action candidates\n" + good + "\n## Cycle 9\n\n" + bad


@pytest.mark.parametrize("label,bad", [
    # A whole table left in the old shape. `_ROW` needs only five cells after the
    # id, so every field lands one column left: `decision` reads the status.
    ("a table still in the six-column shape",
     _SIX_COL + "| C-009 | a thing | PR #1 |  | `open` | n |\n"),
    # ONE row carrying a pipe in its first five cells. Markdown's own escape for a
    # literal pipe is `\\|`, and the cell pattern treats that pipe as a boundary —
    # so a CORRECTLY escaped title shifts the row and nothing else on the page.
    ("one row with a pipe in its title",
     _HEADER + "| C-009 | Make `a | b` share a pool | c | PR #1 |  |  | `open` | n |\n"),
    # An id the parser does not match at all: absent from the working set, from
    # every authorization snapshot, and from the deletion check.
    ("an id that is not three digits",
     _HEADER + "| C-1009 | a thing | c | PR #1 | `ship` | feature | `open` | n |\n"),
    # TWO ROWS SHARING ONE ID — the door that has actually opened, five times.
    # Both rows parse; every reader is a dict keyed by id, so the second silently
    # overwrites the first and one candidate stops existing. `C-001` is reused
    # from the fixture's own first table on purpose: the collision that happens in
    # production is across TABLES, when two branches allocate against one base.
    ("one id allocated to two rows",
     _HEADER + "| C-001 | a different thing | c | PR #1 | `ship` | feature | `open` | n |\n"),
], ids=["six-column-table", "pipe-in-a-cell", "wrong-id-width", "duplicate-id"])
def test_a_row_READ_WRONGLY_or_LOST_RAISES_rather_than_reading_as_triaged(
        tree: Path, label: str, bad: str) -> None:
    """Every departure from the assumed shape is loud, whatever the door.

    Loud beats a clean-looking answer: the whole point is that an empty-ish result
    from this parser is indistinguishable from a genuinely quiet file.

    THE ERROR MUST NAME THE OFFENDING ROW, which is asserted rather than assumed.
    A raise that says only "the file is malformed" over an eighty-row file leaves
    the operator with the same search this check was supposed to do for them, and
    each door here reaches the raise by a different route.
    """
    f = _write(tree, _nine_tables(bad))
    with pytest.raises(ValueError) as exc:
        act.candidate_rows(f, missing_hint="x")
    offender = "C-001" if label.startswith("one id") else (
        "C-1009" if "three digits" in label else "C-009")
    assert offender in str(exc.value), (
        f"{label} raised without naming {offender}: {exc.value}")


def test_EIGHT_GOOD_TABLES_DO_NOT_EXCUSE_A_NINTH(tree: Path) -> None:
    """THE NEGATIVE CONTROL ON THE CHECK'S SCOPE, not on its subject.

    Without this, a check that reads the file as a whole passes for the wrong
    reason and no assertion above can tell. Nine well-formed tables must parse
    clean — so when the parametrized cases go red it is the ninth table that did
    it, not the fixture.
    """
    rows = act.candidate_rows(
        _write(tree, _nine_tables(
            _HEADER + "| C-009 | a thing | c | PR #1 |  |  | `open` | n |\n")),
        missing_hint="x")
    assert len(rows) == 9, f"the nine-table fixture itself does not parse: {rows}"
    assert [r.id for r in rows if not r.decision] == ["C-009"], (
        "the untriaged row must survive the parse — losing it silently is the "
        "entire failure this check exists to prevent")


def test_the_REAL_candidates_file_parses_and_every_cell_is_in_vocabulary() -> None:
    """RUN AGAINST THE ARTIFACT, because a fixture agrees with whatever it was built from.

    Every check above builds its own table, so all of them would stay green if the
    live `candidates.md` drifted out of the shape they assume. This is the one
    assertion that reads what the pipeline will actually read.
    """
    # parents[5]: unit -> tests -> temporal -> workflows -> scripts -> repo root.
    real = (Path(__file__).resolve().parents[5] / "docs" / "standards"
            / "architecture" / "research" / "candidates.md")
    assert real.is_file(), f"{real} is gone; this check would assert against nothing"
    rows = act.candidate_rows(real, missing_hint="x")
    assert len(rows) > 30, "too few rows parsed for this to mean anything"


def test_an_UNUSABLE_component_name_is_REPORTED_not_raised(tree: Path) -> None:
    """`candidates.md` § `component`: "Nothing is scaffolded for a blank row and nothing fails because of one".

    `normalise_cell`'s blank set is `""`, `-` and `—`. An EN dash, `--`, or any
    other punctuation-only cell is non-blank to it and slugs to nothing, and
    letting `component_dir` raise on that aborted the whole parent run — after
    triage's dispatch had already been paid for — over one filer typo.
    """
    for raw in ("–", "--", "···", "***"):
        f = _write(tree, _table(("C-001", "t", raw, "`ship`", "`open`")))
        assert own.scaffold_candidate_components(tree, f) == _NOTHING._replace(
            unnamed=[("C-001", raw)]), f"{raw!r} was not reported as unusable"
        assert sorted(p.name for p in (tree / "docs" / "development").iterdir()) == []


def test_a_SEEDED_but_UNRESEARCHED_pool_is_RESUMED_not_skipped_forever(
        tree: Path) -> None:
    """The redispatch hole: "exists" conflated a live component with an abandoned one.

    `research-write` commits the seed; if `research-verify` then fails, the
    documented `--pr` recovery redispatch would hit the exists-check, skip, and
    report "an empty working set, not a skipped step" over a candidate that is
    stranded forever. A pool still carrying the seed marker is unfinished work,
    not a component somebody owns.
    """
    f = _write(tree, _table(("C-001", "t", "half-built", "`ship`", "`open`")))
    assert own.scaffold_candidate_components(tree, f).created == ["half-built"]

    second = own.scaffold_candidate_components(tree, f)
    assert second == _NOTHING._replace(resumed=["half-built"])
    assert second.to_research == ["half-built"], "a resumed pool must reach research"


def test_a_pool_the_research_child_REWROTE_is_never_resumed(tree: Path) -> None:
    """The marker is what separates the two, and a rewrite removes it.

    Without this the resume path would re-research every component forever. It
    is the same assertion as the no-op test one level up, stated against the
    signal rather than against the return value.
    """
    f = _write(tree, _table(("C-001", "t", "researched", "`ship`", "`open`")))
    own.scaffold_candidate_components(tree, f)
    seed = tree / "docs" / "development" / "researched" / "research" / "synthesis.md"
    assert own._UNRESEARCHED in seed.read_text()

    seed.write_text("# researched — synthesis\n\nTwenty-five papers deep.\n")
    assert own.scaffold_candidate_components(tree, f) == _NOTHING._replace(
        extends=[("C-001", "researched")])


def test_the_seed_asks_the_next_writer_to_CARRY_THE_ID_FORWARD(tree: Path) -> None:
    """`research_write` fully rewrites this file, so writing the id down is not keeping it.

    Its prompt says *"write (or fully rewrite) synthesis.md"* and its synthesis
    contract has no provenance field. The id the docstring calls the load-bearing
    part would live for exactly one pipeline step unless something asks for it.
    """
    f = _write(tree, _table(("C-042", "t", "carried", "`ship`", "`open`")))
    own.scaffold_candidate_components(tree, f)
    seed = (tree / "docs" / "development" / "carried" / "research"
            / "synthesis.md").read_text()
    assert "carry the `C-042` line above into what you write" in seed


def test_a_run_may_NOT_name_a_component_on_a_row_it_did_not_file(tree: Path) -> None:
    """`component` is the FILER's, and it is the one column whose guess gets BUILT.

    `decision` and `status` each have a snapshot comparator and a MAY NOT row;
    `component` had neither, while `plan-candidates` turns whatever it says into
    a committed directory in the next step of the same parent. An APPENDED row is
    exempt, because filing a proposal requires naming where it goes.
    """
    before = {"C-001": "", "C-002": "alpha"}
    after = {"C-001": "guessed", "C-002": "alpha", "C-003": "filed-by-this-run"}
    assert act.components_this_run_had_no_right_to(before, after) == ["C-001"], (
        "either the guess was missed or the appended row was wrongly flagged")


def test_the_parse_is_NAMED_so_a_widened_row_cannot_silently_shift_a_guard() -> None:
    """`component` was inserted between `Candidate` and `Source` and moved two columns.

    Three call sites unpack this — two of them are AUTHORIZATION GUARDS that
    prove a run did not write a column it does not own. A positional tuple would
    have re-pointed them by one and still returned a clean dict over the wrong
    field, which is invisible exactly where invisibility costs most.
    """
    # `size` joined between `decision` and `status` on 2026-08-19 — the SECOND
    # widening this test exists for, and the reason it is an equality against the
    # whole tuple rather than a membership check: a widened row shifts every
    # positional caller silently, and only naming all of them catches it.
    assert act.CandidateRow._fields == (
        "id", "title", "component", "decision", "size", "status")


# --- what the loop meets in a pool it did not write ------------------------

def test_a_pool_whose_synthesis_IS_NOT_VALID_UTF8_does_not_abort_the_run(
        tree: Path) -> None:
    """The one file this loop reads and did not write, read while holding built state.

    Every other anomaly here is REPORTED — a blank `component`, a punctuation-only
    one — for a stated reason: raising aborts the parent after step 1's model
    dispatch has already been paid for. `_is_unresearched` was the exception, and
    not deliberately: it opened a PRE-EXISTING `synthesis.md` with a strict UTF-8
    decode, so one component pool written in some other encoding took the whole
    `plan-project` run down, after earlier rows in the same loop had already
    created directories on disk.

    The classification is EXACT rather than degraded, which is why replacing the
    undecodable byte is allowed: `_UNRESEARCHED` is pure ASCII and this activity
    writes it itself, so a file that fails to decode cannot be one this pipeline
    seeded. `False` — "not ours, leave it alone" — is the right answer, and it is
    the answer this asserts rather than merely asserting no exception.
    """
    pool = tree / "docs" / "development" / "foreign" / "research"
    pool.mkdir(parents=True)
    (pool / "synthesis.md").write_bytes(
        b"# foreign - synthesis\n\nlatin-1 dashes: \xd0 \xff\n")

    f = _write(tree, _table(("C-001", "t", "foreign", "`ship`", "`open`")))
    assert own.scaffold_candidate_components(tree, f) == _NOTHING._replace(
        extends=[("C-001", "foreign")]), (
        "an undecodable synthesis in somebody else's pool must classify as "
        "`extends`, not abort a run that has already paid for a dispatch")


def test_A_ROW_LATER_IN_THE_FILE_still_runs_after_an_undecodable_pool(
        tree: Path) -> None:
    """THE COST OF THE RAISE, NOT JUST THE RAISE — asserted from the far side.

    The test above would pass on any implementation that swallowed the error and
    returned nothing at all. What the loop actually owes is that one unreadable
    pool costs exactly one row: the rows after it are still scaffolded, in the
    same run, in file order.
    """
    pool = tree / "docs" / "development" / "foreign" / "research"
    pool.mkdir(parents=True)
    (pool / "synthesis.md").write_bytes(b"\xff\xfe not utf-8 at all")

    f = _write(tree, _table(
        ("C-001", "t", "foreign", "`ship`", "`open`"),
        ("C-002", "a thing worth building", "downstream", "`ship`", "`open`"),
    ))
    result = own.scaffold_candidate_components(tree, f)
    assert result.created == ["downstream"], (
        f"the row after the unreadable pool was lost: {result}")
    assert result.extends == [("C-001", "foreign")]


# --- the property the exists-check's SAFETY rests on ------------------------

@pytest.mark.parametrize("raw", [
    "sprint.md", "cpi-decisions.md", "../../etc", "a/b", "Fleet Reliability",
    "burn-test-intake-2026-08-02.md", ".", "..", "a.b.c", "x\ty",
])
def test_a_SLUG_IS_ONLY_LOWERCASE_ALPHANUMERICS_AND_HYPHENS(raw: str) -> None:
    """No dot, no separator — and BOTH halves of that are load-bearing.

    The no-separator half is path traversal: `component_slug`'s docstring claims
    *"`../../etc` becomes `etc` rather than escaping the tree"*, and this is what
    holds the claim. The value comes straight out of a markdown cell that any
    filing run writes, and it is turned into a `mkdir(parents=True)`.

    THE NO-DOT HALF IS WHY THE EXISTS-CHECK MAY ASK `.exists()` RATHER THAN
    `.is_dir()`. A review raised that a non-directory sharing a component's name
    would be reported as `extends` — the candidate "extends something already
    planned" — which is a false note. The remedy is unavailable and would be
    worse: `.is_dir()` sends the same row on to `mkdir(parents=True)` under a
    file, turning a silent misreport into a crash. It is also unreachable, and
    THIS is the reason: every non-directory entry under `docs/development/`
    carries a `.md` suffix, and a slug cannot contain a dot. That argument is
    a property of this function, so it is pinned here rather than asserted in a
    review comment — if a slug ever grows a dot, the rejection stops being true
    and this goes red.
    """
    slug = own.component_slug(raw)
    assert re.fullmatch(r"[a-z0-9-]*", slug), f"{raw!r} slugged to {slug!r}"
    assert own.component_slug(slug) == slug, "slugging is not idempotent"

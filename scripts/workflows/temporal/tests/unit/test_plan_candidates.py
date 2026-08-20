"""`plan-candidates` — the scaffolder, and the conditions that gate it.

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

WHAT THE SKIPS ACTUALLY PROTECT, since several of them look alike:

  * not `ship` — triage has not agreed, or has refused.
  * not `open` — already handled.
  * blank `component` — an UNANSWERED QUESTION. The filer knows and did not say;
    guessing from a one-line summary is exactly what this code must not do.
  * `size` is not `feature` — a `phase` or `checkboxes` candidate is work INSIDE
    a component rather than a component, and a blank `size` has not been ruled
    on at all. Neither may be scaffolded; both are reported.
  * directory exists — the candidate EXTENDS something already planned. Seeding
    a synthesis on top of a live component's research pool would overwrite real
    findings with a one-line proposal, and that is the expensive one.

NO COUNT OF THEM IS WRITTEN HERE. This docstring said "four" in two places from
the day it was written until `size` added a fifth condition — and it said it in
the file that tests the code whose own docstring was corrected for exactly that,
in the same PR, without this one being looked at. The enumeration is the whole
of what a reader needs; the number is what goes stale.
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
    "|---|---|---|---|---|---|---|---|\n"
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
_NOTHING = own.Scaffolded(created=[], resumed=[], extends=[], unnamed=[],
                          not_a_feature=[], unsized=[])


# --- vacuity floor --------------------------------------------------------

def test_a_shipped_open_named_row_IS_scaffolded(tree: Path) -> None:
    """The floor: if this does not fire, every skip assertion below is vacuous."""
    f = _write(tree, _table(
        ("C-001", "A thing worth building", "fleet-reliability", "`ship`", "`open`")))
    assert own.scaffold_candidate_components(tree, f).created == ["fleet-reliability"]
    pool = tree / "docs" / "development" / "fleet-reliability" / "research"
    assert pool.is_dir(), "the research pool is the whole deliverable"
    assert (pool / "synthesis.md").is_file()


# --- the skips -------------------------------------------------------------

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
        created=["shared"], resumed=[], extends=[("C-002", "shared")], unnamed=[],
        not_a_feature=[], unsized=[]), (
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

# THE SHAPE A STALLED MIGRATION LEAVES, which `_SIX_COL` is not. `component` took
# the table from six columns to seven and `size` took it from seven to eight, so
# the table that exists half-migrated TODAY is the seven-column one — and it is
# the dangerous one, because seven cells satisfy the row parser and six do not.
_SEVEN_COL = ("| ID | Candidate | `component` | Source | `decision` | `status` | Note |\n"
              "|---|---|---|---|---|---|---|\n")


def _nine_tables(bad: str) -> str:
    """Eight well-formed candidate tables and one `bad` one, as the real file is shaped."""
    good = "".join(
        f"\n## Cycle {n}\n\n{_HEADER}| C-{n:03d} | t | c | PR #1 | `ship` | feature | `open` | n |\n"
        for n in range(1, 9))
    return "# Action candidates\n" + good + "\n## Cycle 9\n\n" + bad


@pytest.mark.parametrize("label,bad", [
    # A whole table left in the old shape. `_ROW` needs six cells after the id, so
    # a six-column row does not parse AT ALL and is caught as an unparsed row.
    ("a table still in the six-column shape",
     _SIX_COL + "| C-009 | a thing | PR #1 |  | `open` | n |\n"),
    # ONE row carrying a pipe in a cell before the Note. Markdown's own escape for a
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
    # A TABLE LEFT IN THE SEVEN-COLUMN SHAPE — the one a STALLED migration
    # actually leaves, and the case none of the four above reaches. `_SIX_COL` is
    # two columns short, so its rows do not parse and land on the unparsed-row
    # arm; a seven-column row parses PERFECTLY and every field lands one column
    # left. `size` reads the status, `status` reads the Note.
    #
    # THE NOTE IS `closed` ON PURPOSE, AND THAT IS THE WHOLE FIXTURE. Write any
    # ordinary note there and the displaced text fails the `status` vocabulary,
    # so the row raises whether or not `size` is checked — the fixture would read
    # identically with the defect present and could not see it. A note that
    # happens to read as a status word (this file's notes are terse) lands every
    # displaced cell on an ADMITTED value except one: `` `open` ``, sitting in
    # `size`. Under the condition as it shipped, this row parses clean, reads as
    # triaged, and drops out of the untriaged working set with nothing raised.
    ("a table still in the seven-column shape",
     _SEVEN_COL + "| C-009 | a thing | c | PR #1 | `ship` | `open` | closed |\n"),
], ids=["six-column-table", "pipe-in-a-cell", "wrong-id-width", "duplicate-id",
        "seven-column-table"])
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


@pytest.mark.parametrize("size", ["phase", "checkboxes", ""])
def test_an_UNUSABLE_component_name_is_REPORTED_AT_EVERY_SIZE(
        tree: Path, size: str) -> None:
    """The typo above is a typo whatever triage sized the row. It was not.

    THE SIZE BRANCH SHIPPED AHEAD OF THE NAME CHECK, so `component_slug` was
    reached only for a `feature`. Every row the test above pins is feature-sized,
    because `_table` defaults it that way — so the whole `unnamed` bucket went
    unasked for the three sizes that skip scaffolding, and nothing noticed.

    WHAT THAT COST IS A FALSE NOTE, NOT A MISSING ONE, which is why it is worth a
    test rather than a shrug. `plan_project_workflow` turns a `not_a_feature`
    entry into *"`C-001` is sized `phase`, so nothing was scaffolded — it is work
    INSIDE a component rather than a component of its own"*, and refers the
    operator on to *"the component its `component` cell names"*. For a cell
    reading `--` there is no such component: the sentence talks about a name that
    does not exist. The operator is told the row is correctly parked when it is
    actually unroutable, and the `unnamed` note that would have said so — *"the
    cell needs a real name or a blank"* — never fires. A `phase` still has to say
    WHICH component it is a phase of.

    THE BLANK SIZE IS IN THE PARAMETRISATION ON PURPOSE. It reaches `unsized`
    rather than `not_a_feature`, a different bucket down a different branch of
    the same expression, and a fix that reordered only one of them would leave
    the other exactly as it was.
    """
    for raw in ("–", "--", "···", "***"):
        f = _write(tree, _table(("C-001", "t", raw, "`ship`", "`open`", size)))
        assert own.scaffold_candidate_components(tree, f) == _NOTHING._replace(
            unnamed=[("C-001", raw)]), (
            f"a {size or 'blank'}-sized row whose `component` reads {raw!r} was "
            f"not reported as unusable — the name check must not sit behind the "
            f"size branch, or the operator is told an unroutable row is parked "
            f"correctly")
        assert sorted(p.name for p in (tree / "docs" / "development").iterdir()) == []


@pytest.mark.parametrize("size,bucket", [
    ("phase", "not_a_feature"),
    ("checkboxes", "not_a_feature"),
    ("", "unsized"),
], ids=["phase", "checkboxes", "unsized"])
def test_a_ROUTABLE_name_at_a_NON_FEATURE_size_is_DECLINED_and_REPORTED(
        tree: Path, size: str, bucket: str) -> None:
    """The size branch's POSITIVE path, which nothing above reaches.

    THE TEST ABOVE PROVES ORDERING AND NOT THIS. Every one of its rows carries a
    `component` cell that slugs to nothing, so each `continue`s at the name check
    one line ABOVE the size branch — the branch this asserts on is never entered.
    That left the routing itself uncovered in both directions: a dropped
    `continue` would scaffold a whole component for a `phase`, and swapped
    buckets would send the operator the wrong note, and the suite would stay
    green through either.

    ASSERTED AGAINST THE WHOLE `Scaffolded` AND AGAINST THE DISK, because the two
    failures look different. A wrong bucket is visible only in the value; a
    missing `continue` is visible only on disk, where a directory the operator
    never asked for now exists and the research fan-out will pick it up.
    """
    f = _write(tree, _table(
        ("C-001", "A thing worth building", "fleet-reliability", "`ship`",
         "`open`", size)))
    assert own.scaffold_candidate_components(tree, f) == _NOTHING._replace(
        **{bucket: [("C-001", size or "unsized")]}), (
        f"a {size or 'blank'}-sized row naming a perfectly usable component was "
        f"not declined into `{bucket}` — `size` is what decides whether this "
        f"scaffolds, and a row that routes on it wrongly either invents a "
        f"component or reaches the operator under the wrong note")
    assert sorted(p.name for p in (tree / "docs" / "development").iterdir()) == [], (
        "nothing may be created for a candidate that is not feature-sized")


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


# --- the fixture's own shape ----------------------------------------------

def test_THE_FIXTURE_HEADER_AND_ITS_DELIMITER_AGREE() -> None:
    """The delimiter row must have one cell per header column. It had one too many.

    A FIXTURE DEFECT IS NOT A COSMETIC ONE, because everything below asserts
    against this string. `_HEADER` shipped with an eight-column header over a
    NINE-cell delimiter row, which means the table every test in this module
    parses is not the table `candidates.md` renders — and the one guard whose
    whole job is "your table is the wrong shape" was being exercised against a
    fixture that was itself the wrong shape.

    It survived because nothing reads the delimiter: `_ROW` matches rows and
    `_HEADER in text` matches the header line, so a malformed separator changes
    no assertion and breaks no parse. It changes what a HUMAN reads the fixture
    to mean, and it renders as a broken table in any markdown viewer — which is
    how the real file's own migration was checked.

    ASSERTED AGAINST THE HEADER RATHER THAN AGAINST A LITERAL EIGHT. A pinned
    number here would have to be edited by the next column, which is the drift
    that produced this defect and the one `plan_activities._CONSTRAINED_CELLS`
    now refuses on the production side.
    """
    header, delimiter = _HEADER.strip("\n").split("\n")
    columns = header.strip().strip("|").split("|")
    cells = delimiter.strip().strip("|").split("|")
    assert len(cells) == len(columns), (
        f"the fixture header declares {len(columns)} columns "
        f"{[c.strip() for c in columns]} and its delimiter row has {len(cells)} "
        f"cells. Every table in this module is built from this string, so a "
        f"fixture that is not the shape it claims tests the parser against a "
        f"table `candidates.md` does not render.")
    assert all(set(cell.strip()) == {"-"} for cell in cells), (
        f"a delimiter cell is not all dashes: {cells}")


def test_the_fixture_header_IS_the_one_the_parser_looks_for() -> None:
    """And the header line is the production constant, not a copy of it.

    The `shape` half of the foreign-cell message fires on `_HEADER in text`. A
    fixture whose header differs from `plan_activities._HEADER` by a space would
    make every raise in this module carry the "no table has the expected header"
    sentence, and the tests asserting on that message would pass for the wrong
    reason.
    """
    assert _HEADER.strip("\n").split("\n")[0] == act._HEADER


# --- `size` is a closed vocabulary, like the two flags beside it ------------

@pytest.mark.parametrize("cell", ["huge", "`Feature`", "phase-ish", "3", "small"])
def test_a_FOREIGN_size_RAISES_rather_than_reading_as_a_ruling(
        tree: Path, cell: str) -> None:
    """`size` admits four values and admitted anything.

    `_SIZES` was declared for this check and had no reader in the whole tree, so
    the third ruled column was the one column a shift could displace text into
    unobserved. It is the column that ROUTES: `plan-candidates` scaffolds a whole
    `docs/development/<name>/` for a `feature` and correctly declines for the
    other two, so an unrecognised value is a row that either scaffolds nothing
    with no complaint or is routed on a string nobody defined.

    THE MESSAGE MUST NAME `size`. The three ruled columns fail through one raise,
    and an operator told only "row C-009 is unreadable" over a file with three
    closed vocabularies has the same search this check exists to do for them.
    """
    f = _write(tree, _table(("C-009", "t", "c", "`ship`", "`open`", cell)))
    with pytest.raises(ValueError) as exc:
        act.candidate_rows(f, missing_hint="x")
    message = str(exc.value)
    assert "C-009" in message, f"the raise did not name the row: {message}"
    assert "size" in message, (
        f"the raise did not name the column that was wrong: {message}")
    assert act.normalise_cell(cell) in message, (
        f"the raise did not render the offending value {cell!r}: {message}")


@pytest.mark.parametrize("cell", ["", "—", "feature", "phase", "checkboxes",
                                  "`feature`", " phase "])
def test_every_size_the_FILE_ADMITS_still_parses(tree: Path, cell: str) -> None:
    """THE NEGATIVE HALF, and without it the assertion above is a blanket ban.

    A condition that rejected every non-empty `size` would satisfy every case in
    the test above and break the column entirely. Backtick and padding variants
    are here because `normalise_cell` is what makes them equal, and a check
    written against the RAW cell would reject a correctly-formatted row.
    """
    f = _write(tree, _table(("C-009", "t", "c", "`ship`", "`open`", cell)))
    assert [r.id for r in act.candidate_rows(f, missing_hint="x")] == ["C-009"]


def test_THE_REAL_CANDIDATES_FILE_PARSES_UNDER_THE_TIGHTENED_CHECK() -> None:
    """The production file, read as the fleet reads it. Not a fixture.

    A vocabulary tightened against fixtures alone is a guess about the live file,
    and this one gates every planning workflow: if `candidates.md` stopped
    parsing, `triage-candidates`, `plan-feature`, `plan-verify` and
    `plan-candidates` all raise before doing anything. The row count is asserted
    non-zero rather than pinned — a pinned figure goes stale on the next filing,
    and the failure this guards against is the parse returning nothing.
    """
    # `parents[5]` is the repo root from `tests/unit/`, the idiom this suite
    # already uses in eight modules — see `journal_entrypoint_facts.REPO_ROOT`.
    real = Path(__file__).resolve().parents[5] / (
        "docs/standards/architecture/research/candidates.md")
    assert real.is_file(), f"the production candidates file moved: {real}"
    rows = act.candidate_rows(real, missing_hint="x")
    assert rows, "the production file parsed to zero rows"


# --- `Scaffolded` carries no shared mutable default -------------------------

def test_NO_Scaffolded_FIELD_HAS_A_MUTABLE_DEFAULT() -> None:
    """A `NamedTuple` default is built ONCE, at class creation, and shared.

    `not_a_feature` and `unsized` shipped as `= []`. That is one list object on
    the class, handed to every instance that omits the field — so
    `s.not_a_feature.append(row)` on a default-constructed value writes into the
    class, and the next default-constructed `Scaffolded` in the same process
    starts life already holding the previous one's rows. The parent turns each
    entry into an operator note, so the visible failure is one run reporting
    another run's declines.

    ASKED OF THE CLASS, NOT OF THE TWO FIELDS THAT HAD IT. A field added later
    with `= []` is the same defect, and naming today's two would let the next one
    through. `= ()` would satisfy a narrower "is it mutable" reading and is
    equally wrong here for a reason `Scaffolded`'s own comment states: these
    tests compare whole values, and a tuple does not equal a list.
    """
    offenders = {name: default
                 for name, default in own.Scaffolded._field_defaults.items()
                 if isinstance(default, (list, dict, set, bytearray))}
    assert offenders == {}, (
        f"these `Scaffolded` fields carry a shared mutable default: {offenders}. "
        f"On a NamedTuple the default is one object built at class creation and "
        f"handed to every instance that omits the field, so mutating it through "
        f"any instance edits the class. Drop the default and require the field.")


def test_the_two_DECLINE_REASONS_are_required_at_construction() -> None:
    """And a caller that omits them fails LOUDLY rather than getting a shared list.

    THE POSITIVE CONTROL ON THE RULE ABOVE. `_field_defaults` being empty is one
    way to satisfy it; the field having vanished is another, and the assertion
    above cannot tell those apart. This pins the direction: both fields exist,
    and neither may be omitted.

    Every list on `Scaffolded` answers "what happened to the rows I did not
    scaffold?", and the class's whole argument is that "nothing happened" must
    never be reachable by omission. A caller that has not thought about the two
    decline reasons should fail at construction rather than report an empty one.
    """
    assert {"not_a_feature", "unsized"} <= set(own.Scaffolded._fields)
    with pytest.raises(TypeError):
        own.Scaffolded(created=[], resumed=[], extends=[], unnamed=[])


# --- the diagnostics name the shape that is actually out there -------------

def test_THE_SHAPE_DIAGNOSTIC_NAMES_THE_SHAPE_A_STALLED_MIGRATION_LEAVES(
        tree: Path) -> None:
    """"six-column" was the shape before LAST migration, not this one.

    The message exists to point an operator at a table. `component` took the
    table from six columns to seven and `size` took it from seven to eight, so
    the half-migrated table sitting in the tree today is SEVEN-column — and a
    message naming the six-column shape sends the reader looking for a table that
    has not existed since before the previous migration. Worse, the two shapes
    fail differently: six columns do not parse at all, seven parse perfectly and
    shift every field one column left, which is the case that reaches here.
    """
    f = _write(tree, _nine_tables(
        _SEVEN_COL + "| C-009 | a thing | c | PR #1 | `ship` | `open` | closed |\n"))
    with pytest.raises(ValueError) as exc:
        act.candidate_rows(f, missing_hint="x")
    message = str(exc.value)
    assert "seven-column" in message, (
        f"the diagnostic does not name the shape it is describing: {message}")
    assert "six-column" not in message, (
        f"the diagnostic still names the shape before last: {message}")


def test_the_diagnostic_CELL_COUNT_is_derived_from_the_header() -> None:
    """And the count it prints is the count the parser actually enforces.

    THE FIGURE HAS BEEN WRONG THROUGH TWO COLUMN ADDITIONS. It read "first five
    cells", which was true of the six-column table it was written against, went
    stale when `component` landed and was still stale when `size` did. Asserted
    against `_HEADER` rather than against a literal, because a literal here is
    the same hand-kept figure one layer up — it would need editing by the next
    column, which is precisely what did not happen twice.

    The parser constrains every column but the Note: `_ROW`'s pattern brackets
    them with one pipe more than there are cells, and the Note is the only cell
    permitted to hold a pipe of its own.
    """
    columns = act._HEADER.strip().strip("|").split("|")
    assert [c.strip() for c in columns][-1] == "Note", (
        f"the last column is no longer the Note: {columns}")
    assert act._CONSTRAINED_CELLS == len(columns) - 1, (
        f"the parser is described as constraining {act._CONSTRAINED_CELLS} "
        f"cells; the header declares {len(columns)} columns of which the Note is "
        f"the only unconstrained one.")
    assert act._ROW.pattern.count("\\|") == len(columns), (
        f"`_ROW` brackets {act._ROW.pattern.count(chr(92) + '|')} pipes over a "
        f"{len(columns)}-column header — the regex and the header disagree about "
        f"the table's shape, so `_CONSTRAINED_CELLS` describes neither.")

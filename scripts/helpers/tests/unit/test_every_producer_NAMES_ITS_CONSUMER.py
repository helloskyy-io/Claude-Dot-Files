"""Every producer names its consumer, across every surface ruled in.

WORKFLOW DECOMPOSITION PHASE 6. A surface written by one part of the system and
read by no other part is not neutral: it costs the run that produces it, it looks
like coverage to a reader, and nothing goes red when it stops being correct —
because nothing was ever checking. Measured twice here. Three parent-written
observables shipped with no reader at all; and the directory that governs the
measurement tools stated its own *"a `Read by` column with nothing in it is a
finding"* rule **in prose**, one level up from the tools it governs — nothing
enforced it, and a tool shipped unread anyway.

THE DEFINITION (requirement 1), stated once, here, because this is where the
check is built from it:

    A PRODUCER is a surface one part of the system writes for another part to
    read. It is CONFORMANT when its consumer is NAMED; and, when the surface
    ACCUMULATES items awaiting disposition, when that consumer is additionally
    invoked on a NAMED CADENCE by a NAMED RUNNER.

    The keying is on *something is meant to read this*, never on *this writes a
    file*. A check keyed on the second catches every temp file in the tree and
    gets disabled within a month.

    DELIBERATELY EXCLUDED, and each exclusion is asserted BY NAME below because
    an exclusion that is not named is a hole:

      * A DECLARATION MODULE — code defining a surface's shape, loaded by the
        tools rather than run beside them. `measure/run_log.py` is the one.
      * A SURFACE WHOSE ONLY LEGITIMATE CONSUMER IS A HUMAN — `tracked/
        operations/`. No check can assert that a person read something, and a
        proxy like file mtime is routed around within a month.
      * TESTS — `scripts/helpers/tests/` is read by the runner, not by the
        system.
      * A TRANSIENT ARTIFACT — a temp file, a log, a build output written for
        the writer's own use. `_is_transient` is the rule; unlike the three
        above it is NOT asserted against the tree, because a transient
        artifact's absence is the normal case.

(This file supersedes `test_measure_readme_names_a_consumer.py`, deleted in the
same change. All three of its properties — the population read off disk in both
directions, every row naming a consumer, and `run_log.py`'s exclusion asserted
against the tree — are carried below, with `measure/` as one row of `SURFACES`
rather than a gate of its own.)

WHY THE CADENCE CLAUSE IS CONDITIONAL (requirement 2, RULED 2026-09-10). The
three properties were borrowed from `Tracked Items Standard` §0, which governs
STORES — surfaces that accumulate items awaiting a decision — and whose exit
clause is about items reaching a terminal state. This phase generalises them to
PRODUCERS, a wider class containing members nothing accumulates in.
`scripts/workflows/temporal/scripts/compare_run_config.py` is the worked test
case: a named machine reader, invoked on demand, over bags that are never edited
after sealing. Requiring a cadence of it would mean inventing a schedule to
satisfy a check, which is how a gate gets routed around. So an ON-DEMAND READER
IS A CONFORMANT CONSUMER, and the cadence clause binds accumulating surfaces
only. `tracked/` is the accumulating surface here and carries the stronger check.

*(§0 governs stores and says nothing about generalising. The generalisation is
this phase's claim to defend — do not cite §0 as though it already ruled the
fleet.)*

WHAT THIS GATE DOES NOT LOOK AT. Stated here so nobody over-reads a green suite:

  * It does not check that a consumer is any GOOD. Naming a reader is a much
    weaker claim than the reader being correct, and only the weaker one is made.
  * It does not check that a named invoker's ARGUMENTS are right, that the code
    path is ever taken at runtime, or that anyone reads the output once produced.
  * It does not reach producers outside the three surfaces declared in
    `SURFACES`. Workflow prompts, agent definitions, hooks, `config/skills/` and
    the run bag are all unruled — the phase's own boundary is that ruling a
    surface in is done one at a time with the reason recorded, not wholesale.
  * It does not DELETE an unread producer. Finding one is the output; ruling
    what happens to it is a separate decision with its own criteria.
  * On a clone with no sibling planning repo the `tracked/` surface SKIPS. That
    is a real coverage gap rather than a neutral fallback (`C-8z8v04wk`); CI
    has both repos side by side, which is where this is green.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from typing import Callable
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[4]

# ONE IMPLEMENTATION OF "WHERE IS THE PLANNING REPO", NOT A SECOND ONE. The walk
# is the part that is easy to get wrong: under a worktree the repo root's parent
# is `.claude/worktrees/`, not the directory the two repos share, so a naive
# `_REPO.parent / "skyynet-master-planning"` resolves to nothing on exactly the
# checkouts every dispatch runs in.
sys.path.insert(0, str(_REPO / "scripts" / "workflows" / "temporal" / "tests"))
from planning_corpus import PLANNING_ROOT  # noqa: E402

def _is_transient(p: Path) -> bool:
    """The docstring's fourth exclusion class, in code rather than in prose.

    A transient artifact is written for its writer's own use and is gitignored;
    it has no consumer to name and no row to carry. It is NOT asserted against
    the tree the way a named exclusion is — its absence is the normal case, so
    a check that its subject still exists would fail on a clean checkout.

    THIS IS WHY THE GATE WAS GREEN LOCALLY AND RED ON CI. `__pycache__` appears
    under `scripts/helpers/` the moment anything imports a module from it, which
    `test_the_standards_index_is_ACTUALLY_CLEAN.py` does. The authoring shell had
    `PYTHONDONTWRITEBYTECODE=1` and the runner's did not, so the off-disk
    subdirectory read asserted something true only of the machine that wrote it.
    """
    return p.name == "__pycache__" or p.name.startswith(".")


#: A map mentions every file in the repo, so accepting it as an invoker would
#: make every row pass trivially. Named, not inferred, so a reader can see the
#: hole was considered rather than missed.
NOT_AN_INVOKER = frozenset({"docs/file_structure.txt"})

#: Subdirectories of `scripts/helpers/` that are NOT their own producer surface.
#: Checked against disk below, so a third directory appearing fails rather than
#: escaping both the surface list and this one.
NOT_A_SURFACE = {
    "tests": "the tools' tests — read by the runner, not by the system",
}

#: Tools with no invoker anywhere, frozen so the finding cannot grow silently.
#: The ratchet below runs BOTH ways: a new uninvoked tool fails, and a baselined
#: tool that gains a real invoker fails until its line is deleted here. Freezing
#: rather than fixing is the phase's own boundary — inventing an invoker to make
#: a check green is how a gate gets routed around. Reasons are in
#: `scripts/helpers/README.md` § *The two tools nothing invokes*.
UNREAD = {
    "merge-pr.py": "only mention outside its own docstring is a workflow-tree "
                   "diagram in the planning repo's `puma-temp-workflows.md`",
    "sibling_checkouts.py": "landed 2026-09-08 and was never wired to anything",
}

#: The marker a baselined row must carry, so a reader of the table sees the same
#: fact the gate does rather than having to open this file.
UNREAD_MARKER = "NOBODY"


@dataclass(frozen=True)
class Surface:
    """One ruled-in producer population and the table that names its consumers."""

    name: str
    root: Path
    readme: Path
    #: How the population is read OFF DISK. Never a hand-kept list: a table
    #: checked against itself cannot see the member that was never added to it,
    #: which is the exact shape of the finding this phase is the remedy for.
    members: Callable[[Path], set]
    #: `True` when the surface accumulates items awaiting disposition, which is
    #: what makes the cadence-and-runner clause bind (requirement 2's ruling).
    accumulates: bool
    #: NOT A MEMBER AT ALL. name -> reason. Subtracted from the population, and
    #: a row for one is a FAILURE — the surface's own README says these are not
    #: rows, so permitting one would let the table contradict its own prose.
    exclusions: dict = field(default_factory=dict)
    #: A MEMBER, with a row, exempt from the CADENCE clause only. Distinct from
    #: the above and the distinction is load-bearing: `tracked/operations/` is a
    #: real store that must appear in its table — what cannot be checked is
    #: whether a person emptied it, not whether it exists.
    cadence_exempt: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        # THE TWO DICTS MEAN OPPOSITE THINGS and are merged in the exclusion
        # check, where a name in both would let one silently win. Nothing
        # populates both today; this is what keeps that true.
        both = set(self.exclusions) & set(self.cadence_exempt)
        assert not both, (
            f"{self.name}: {sorted(both)} is declared NOT A MEMBER and also a "
            f"member merely exempt from the cadence clause. Pick one."
        )


def _files(root: Path) -> set[str]:
    return {p.name for p in root.iterdir() if p.is_file() and not _is_transient(p)}


def _py(root: Path) -> set[str]:
    return {p.name for p in root.glob("*.py") if not _is_transient(p)}


def _dirs(root: Path) -> set[str]:
    return {p.name for p in root.iterdir() if p.is_dir() and not _is_transient(p)}


SURFACES = [
    Surface(
        name="scripts/helpers/measure/",
        root=_REPO / "scripts" / "helpers" / "measure",
        readme=_REPO / "scripts" / "helpers" / "measure" / "README.md",
        members=_py,
        accumulates=False,
        exclusions={
            "run_log.py": "declaration module — the one declaration of what the "
                          "run-log surface holds, loaded BY the tools rather "
                          "than run beside them",
        },
    ),
    Surface(
        name="scripts/helpers/",
        root=_REPO / "scripts" / "helpers",
        readme=_REPO / "scripts" / "helpers" / "README.md",
        members=_files,
        accumulates=False,
        exclusions={
            "README.md": "the table itself — the surface's declaration, not a "
                         "member of it. A check whose population includes the "
                         "text making the claim can be satisfied by its own "
                         "row, which is not a claim about anything",
        },
    ),
    Surface(
        name="tracked/",
        root=PLANNING_ROOT / "tracked",
        readme=PLANNING_ROOT / "tracked" / "README.md",
        members=_dirs,
        accumulates=True,
        cadence_exempt={
            "operations": "human-in-the-loop only (Tracked Items §1.2) — its "
                          "consumer is a person and no check can assert that a "
                          "person read something",
        },
    ),
]

_BY_NAME = {s.name: s for s in SURFACES}


def _rows(surface: Surface) -> list[list[str]]:
    """The three-column table's body rows, cells stripped.

    One parser for every surface, because three copies of a markdown-table
    reader is three places for the column index to drift.
    """
    rows = []
    for line in surface.readme.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `") and not line.startswith("| ["):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 3:
            rows.append(cells)
    return rows


def _member_of(cell: str) -> str | None:
    """The first backticked token in the subject cell, `/` stripped."""
    found = re.search(r"`([^`]+)`", cell)
    return found.group(1).rstrip("/") if found else None


def _listed(surface: Surface) -> dict[str, str]:
    """member -> consumer cell, for the rows this surface's table carries."""
    out = {}
    for row in _rows(surface):
        member = _member_of(row[0])
        if member:
            out[member] = row[2]
    return out


def _population(surface: Surface) -> set[str]:
    return set(surface.members(surface.root)) - set(surface.exclusions)


def _skip_if_absent(surface: Surface) -> None:
    if not surface.root.is_dir():
        pytest.skip(
            f"{surface.name} is not on this checkout (looked for "
            f"{surface.root}); with no population there is nothing to assert"
        )


def _paths_in(cell: str) -> list[str]:
    """Backticked tokens in a consumer cell that look like repo-relative paths."""
    return [t for t in re.findall(r"`([^`]+)`", cell)
            if "/" in t and re.search(r"\.(py|sh|md|ya?ml|txt)$", t)]


def test_the_ABSENT_SURFACE_SKIP_fires_ONLY_when_the_root_is_missing() -> None:
    """The one failing path in this file that no control covered, and it is the
    one that turns a whole surface green-by-absence.

    Every other failing path here got a self-contained control because a path
    nobody has seen run is a path nobody has seen work. This one was missed:
    the sibling planning repo is present on every machine this suite is known to
    run on, so `tracked/` has never actually skipped, and a typo in the skip
    reason or a wrong `PLANNING_ROOT` fallback would go unnoticed until the day
    coverage silently dropped from three surfaces to two.
    """
    def _probe(root: Path) -> Surface:
        return Surface(name="probe", root=root, readme=root / "README.md",
                       members=_files, accumulates=False)

    _skip_if_absent(_probe(_REPO))  # a real directory must NOT skip

    with pytest.raises(pytest.skip.Exception) as raised:
        _skip_if_absent(_probe(_REPO / "__no_such_surface__"))
    assert "__no_such_surface__" in str(raised.value), (
        "the skip reason must name the path it looked for, or a reader cannot "
        "tell a missing sibling repo from a renamed directory"
    )


@pytest.fixture(params=[s.name for s in SURFACES])
def surface(request) -> Surface:
    s = _BY_NAME[request.param]
    _skip_if_absent(s)
    return s


# --- the two properties every ruled-in surface carries --------------------------

#: Cells that name nobody while looking like they name something.
_NAMES_NOBODY = frozenset({"", "-", "—", "n/a", "TBD"})


def _unlisted(on_disk: set, listed: set) -> set:
    """Members on disk with no row. The failure; a blank cell is its symptom."""
    return on_disk - listed


def _phantom(on_disk: set, listed: set) -> set:
    """Rows for something that is not a member.

    STRICTLY `listed - on_disk`, with no slack for the excluded names. An
    excluded name is one the surface's README says is NOT a row — `run_log.py`
    is a declaration module, `README.md` is the table itself — so forgiving a
    row for one would let the table contradict the prose the exclusion rests on,
    and silently permitting a stray row is the drift this phase exists to catch.
    A store that IS a member and merely cannot be cadence-checked is
    `cadence_exempt`, not this.
    """
    return listed - on_disk


def _unnamed(listed: dict) -> list:
    return [m for m, cell in listed.items() if cell.strip() in _NAMES_NOBODY]


def test_every_member_on_disk_has_a_ROW(surface: Surface) -> None:
    """Read off disk rather than out of the table.

    A table checked against itself cannot see the member that was never added to
    it, which is the exact shape of the finding this phase is the remedy for.
    """
    on_disk = _population(surface)
    assert on_disk, f"no members found under {surface.root} — this gate read nothing"
    listed = set(_listed(surface))
    assert not _unlisted(on_disk, listed), (
        f"{surface.name} holds members with no row in {surface.readme.name}: "
        f"{sorted(_unlisted(on_disk, listed))}. A surface nobody reads is what "
        f"this gate exists to stop producing; one nobody LISTS is how one gets "
        f"there."
    )
    assert not _phantom(on_disk, listed), (
        f"{surface.readme.name} has rows for things that are not members of "
        f"{surface.name}: {sorted(_phantom(on_disk, listed))}"
    )


def test_every_row_NAMES_A_CONSUMER(surface: Surface) -> None:
    """The weaker claim, made of every surface: somebody is named."""
    empty = _unnamed(_listed(surface))
    assert not empty, (
        f"{surface.name} rows with no named consumer: {empty}. Name what reads "
        f"this, or the member does not belong in a surface whose table claims "
        f"every entry answers a standing question."
    )


def test_the_TWO_BASE_checks_fire_on_the_two_ways_to_be_wrong() -> None:
    """Live controls for requirement 5's two shapes, on self-contained samples.

    Both were also demonstrated by real mutation at authoring time — a tool
    added to `scripts/helpers/` with no row, and a row whose cell was `—`; each
    turned the suite red in exactly the predicted test. Those mutations ran once,
    by hand, in a session nobody can re-open. These run on every CI run, so the
    failing path stays exercised rather than remembered.

    The samples are BUILT HERE rather than borrowed from a live surface: a
    control sharing a fixture with the code under mutation over-fires and proves
    nothing about the check.
    """
    assert _unlisted({"a.py"}, {"a.py"}) == set(), "fires on a listed member"
    assert _unlisted({"a.py", "orphan.py"}, {"a.py"}), \
        "a member with NO ROW AT ALL is invisible — requirement 5, shape one"
    assert _phantom({"a.py"}, {"a.py", "ghost.py"}), \
        "a row for something not on disk is invisible"
    assert _unnamed({"a.py": "`config/commands/standup.md`"}) == [], \
        "fires on a row that names a consumer"
    for nobody in ("", "  ", "-", "—", "n/a", "TBD"):
        assert _unnamed({"a.py": nobody}), (
            f"an EMPTY consumer cell {nobody!r} is invisible — requirement 5, "
            f"shape two"
        )


def test_an_EXCLUSION_still_has_its_subject_and_its_reason(surface: Surface) -> None:
    """An exclusion outliving its subject is how a gate stops covering it.

    Two halves, and the second is the one prose can lose: the name must still be
    on disk, AND the README must still explain why it has no row — otherwise its
    absence from the table reads as an omission to the next person.
    """
    named = {**surface.exclusions, **surface.cadence_exempt}
    if not named:
        pytest.skip(f"{surface.name} excludes nothing by name")
    text = surface.readme.read_text(encoding="utf-8")
    for name, reason in named.items():
        target = surface.root / name
        assert target.exists(), (
            f"{name} is excluded from {surface.name} ({reason}) but is not "
            f"there. Either the exclusion is stale or its subject moved."
        )
        assert name.rstrip("/") in text, (
            f"{surface.readme} no longer explains why {name} has no row, so "
            f"its absence from the table reads as an omission"
        )


# --- the cadence clause, which binds ACCUMULATING surfaces only -----------------

def _cadence_gaps(listed: dict, excluded) -> list[tuple[str, str]]:
    """Rows that name a cadence or a runner but not both. Excluded rows skipped."""
    return [(m, cell) for m, cell in listed.items()
            if m not in excluded
            and not (cell.partition("·")[0].strip() and cell.partition("·")[2].strip())]


def test_an_ACCUMULATING_surface_names_a_cadence_AND_a_runner(surface: Surface) -> None:
    """Requirement 2's ruling, in code: a store must say who empties it, when.

    A surface with a reader nobody runs is the failure the borrowed §0 property
    sees and the older `does a reader exist` question does not. It binds stores
    because a store accumulates items awaiting disposition; it does not bind an
    on-demand reader, which never builds a backlog to drain.
    """
    if not surface.accumulates:
        pytest.skip(
            f"{surface.name} does not accumulate items awaiting disposition, so "
            f"the cadence clause does not bind it (requirement 2, ruled "
            f"2026-09-10: an on-demand reader is a conformant consumer)"
        )
    gaps = _cadence_gaps(_listed(surface), surface.cadence_exempt)
    assert not gaps, (
        f"{surface.name} rows that do not name a cadence AND a runner separated "
        f"by `·`: {gaps}. A store whose triage has no named runner is out of "
        f"conformance with Tracked Items §0."
    )


def test_the_CADENCE_check_fires_on_a_half_filled_cell() -> None:
    """Live control for the check above, on a SELF-CONTAINED sample.

    The real accumulating surface is `tracked/` in the SIBLING PLANNING REPO,
    which this repo must not edit — so the mutation that would prove this check
    discriminates cannot be performed on its own population. The sample below is
    built here rather than borrowed from that surface, because a control sharing
    a fixture with the code under mutation over-fires and proves nothing.

    THE PROPERTY UNDER TEST IS *BOTH HALVES*, not `the cell is non-empty` —
    `test_every_row_NAMES_A_CONSUMER` already makes the weaker claim, and a
    control that only distinguished empty from non-empty would be testing that
    one instead.
    """
    both = {"issues": "sprint close-out · the sprint's owner"}
    assert _cadence_gaps(both, set()) == [], "the check fires on a conformant row"
    assert _cadence_gaps({"issues": "sprint close-out"}, set()), \
        "a cadence with NO NAMED RUNNER is invisible to this check"
    assert _cadence_gaps({"issues": "· the sprint's owner"}, set()), \
        "a runner with NO CADENCE is invisible to this check"
    assert _cadence_gaps({"operations": ""}, {"operations"}) == [], \
        "the human-only exclusion is not honoured — requirement 4"


# --- the stronger claim, on `scripts/helpers/`: the named invoker OPENS ---------

# WHY ONLY `scripts/helpers/` CARRIES THE STRONGER CLAIM, and it is a property of
# the cells rather than an oversight. That table's consumer cell names a PATH IN
# THIS REPO, which is a claim a check can open. `measure/`'s `Read by` names
# phases, candidates and open decisions in the planning corpus — prose addressed
# to a human — and `tracked/`'s names a cadence and a runner, one of which is a
# person. Opening those would mean asserting a proxy for "somebody read it",
# which is the shape § *The one exclusion the stores force* rules out.
def test_a_named_invoker_RESOLVES_and_MENTIONS_the_tool() -> None:
    """The cell names a path, and the path is opened.

    `harvest-intake.py` is why this is stronger than name-only. It is a stated
    CONDITION of an exemption, invoked by one line of prose in
    `config/commands/standup.md`; if that line is dropped the intake keeps
    accepting, nothing empties it, and under a name-only check no suite goes red.
    """
    surface = _BY_NAME["scripts/helpers/"]
    checked = 0
    for tool, cell in _listed(surface).items():
        if tool in UNREAD:
            continue
        paths = _paths_in(cell)
        assert paths, (
            f"{tool}'s `Invoked by` cell names no backticked path ending in "
            f"one of .py/.sh/.md/.yml/.yaml/.txt — widen `_paths_in` if the "
            f"invoker is a real file of another kind: {cell!r}"
        )
        rejected = [p for p in paths if p in NOT_AN_INVOKER]
        assert not rejected, (
            f"{tool} names {rejected} as its invoker, which is excluded by "
            f"name: a map mentions every file in the repo, so accepting it "
            f"would make every row pass trivially."
        )
        for rel in paths:
            target = _REPO / rel
            assert target.is_file(), (
                f"{tool}'s named invoker {rel} does not exist. Either the "
                f"invoker moved or the tool is no longer invoked."
            )
            assert tool in target.read_text(encoding="utf-8"), (
                f"{rel} is named as {tool}'s invoker and does not mention it. "
                f"This is the failure the cell exists to catch: the invocation "
                f"was dropped and the table still claims it."
            )
            checked += 1
    # MEASURED AGAINST DISK, NOT AGAINST THE TABLE. Comparing against
    # `_listed()` — the same dict the loop just walked — cannot fail: every row
    # that survived `assert paths` above already incremented `checked`. Read off
    # disk it CAN fail, and the case it catches is the one that matters: a
    # README whose table stops parsing yields zero rows, an empty loop, and a
    # green result from a check that opened nothing.
    assert checked >= len(_population(surface)) - len(UNREAD), (
        f"only {checked} invocations were opened for {len(_population(surface))} "
        f"tools on disk — this check scoped itself to nothing and would pass "
        f"vacuously"
    )


# --- the ratchet, both ways -----------------------------------------------------

def test_a_BASELINED_tool_is_still_on_disk_and_still_declares_itself() -> None:
    """Half one: the frozen list cannot outlive its subjects or go unsaid.

    A baselined row must carry the marker in its own cell, so a reader of the
    table learns the tool is uninvoked without opening this file.
    """
    surface = _BY_NAME["scripts/helpers/"]
    listed = _listed(surface)
    for tool, reason in UNREAD.items():
        assert (surface.root / tool).is_file(), (
            f"{tool} is baselined as uninvoked ({reason}) but is not on disk. "
            f"Delete the baseline entry."
        )
        assert UNREAD_MARKER in listed.get(tool, ""), (
            f"{tool} is baselined as uninvoked, and its row does not say so. "
            f"Its `Invoked by` cell must carry {UNREAD_MARKER!r}."
        )


def _regained(listed: dict) -> list[tuple[str, list[str]]]:
    """Baselined tools whose cell now names an invoker that resolves and mentions them."""
    out = []
    for tool, cell in listed.items():
        if tool not in UNREAD:
            continue
        live = [p for p in _paths_in(cell)
                if p not in NOT_AN_INVOKER
                and (_REPO / p).is_file()
                and tool in (_REPO / p).read_text(encoding="utf-8")]
        if live:
            out.append((tool, live))
    return out


def test_the_RATCHET_fires_when_a_baselined_tool_is_wired_up() -> None:
    """Live control: the shrink path runs on every CI run, not once by hand.

    A ratchet whose failing path has never run is a ratchet nobody has seen
    work, and this one's failing path CANNOT occur in the live table — a
    baselined row's cell says NOBODY by construction, so the check above is
    vacuous against real data forever. The sample is self-contained.

    IT ALSO PINS THE `docs/file_structure.txt` REJECTION, which is the hole that
    would make the whole ratchet meaningless: the map names every file in the
    repo, so if it counted as an invoker every baselined tool would read as
    wired-up the moment it was added to the map.
    """
    tool = next(iter(UNREAD))
    assert _regained({tool: "**NOBODY — baselined below.**"}) == [], \
        "the ratchet fires on a correctly-baselined row"
    assert _regained({tool: "`config/commands/standup.md`"}) == [], \
        "a named invoker that does NOT mention the tool must not clear it"
    assert _regained({tool: "`docs/file_structure.txt`"}) == [], \
        "the repo map cleared a baselined tool — it is named as NOT an invoker"
    assert _regained({tool: f"`scripts/helpers/{tool}`"}), \
        "a real, resolving, tool-mentioning invoker did not force the line out"


def test_a_baselined_tool_that_GAINS_an_invoker_forces_its_line_out() -> None:
    """Half two — what makes the list shrink instead of becoming an excuse list.

    Wiring a baselined tool up is the fix path, and the fix path fails until the
    entry is deleted. Without this the baseline is permanent by construction.
    """
    regained = _regained(_listed(_BY_NAME["scripts/helpers/"]))
    assert not regained, (
        f"these tools are baselined as uninvoked and now name a real invoker: "
        f"{regained}. Delete their lines from UNREAD and from the README's "
        f"baseline section — the ratchet only shrinks."
    )


def _ruled_in_under(root: Path) -> set[str]:
    """Surfaces that ARE a subdirectory of `root`, matched by resolved path.

    MATCHED ON THE PATH, NEVER ON THE LAST SEGMENT OF THE NAME. `scripts/
    helpers/` and `tracked/` end in `helpers` and `tracked`, and neither is
    rooted under this directory — so a name-keyed membership test would treat a
    local `scripts/helpers/tracked/` as already ruled in by a surface that has
    never looked at it, with no README, no gate and no recorded reason. That is
    the exact hole the check below exists to close, one level up.
    """
    return {s.root.name for s in SURFACES if s.root.parent == root}


def test_the_RULED_IN_SET_is_matched_by_path_not_by_name() -> None:
    """Live control for the collision above, on the real `SURFACES` list.

    Two of the three surfaces have a last segment that could legally appear as
    a subdirectory of `scripts/helpers/`, so this is a hole with two members
    rather than a hypothetical.
    """
    under = _ruled_in_under(_REPO / "scripts" / "helpers")
    assert under == {"measure"}, (
        f"only `measure/` is a surface rooted under scripts/helpers/, got {under}"
    )
    for collision in ("helpers", "tracked"):
        assert collision not in under, (
            f"a directory named {collision!r} under scripts/helpers/ would read "
            f"as ruled in by a surface rooted somewhere else entirely"
        )


def test_a_TRANSIENT_ARTIFACT_is_not_a_member_of_any_population() -> None:
    """Live control for the exclusion class that made this gate host-coupled.

    The failure it pins is a REGRESSION THIS FILE SHIPPED: `__pycache__` under
    `scripts/helpers/` turned the surface-list check red on CI while it stayed
    green on a shell exporting `PYTHONDONTWRITEBYTECODE=1`. It cannot be
    demonstrated by creating the directory here — a test that writes into the
    tree it is grading is the coupling one level up — so the predicate is driven
    directly, which is what every population read below calls.
    """
    assert _is_transient(_REPO / "scripts" / "helpers" / "__pycache__"), \
        "bytecode caches are a member of the population — the CI-red shape"
    assert _is_transient(_REPO / ".git"), "dot-directories are tool state"
    assert not _is_transient(_REPO / "scripts" / "helpers" / "measure"), \
        "a real surface was filtered out as transient, which hides it entirely"
    assert not _is_transient(_REPO / "scripts" / "helpers" / "merge-pr.py"), \
        "a real tool was filtered out as transient, which hides it entirely"


def test_the_SURFACE_LIST_itself_is_read_off_disk() -> None:
    """A hand-kept list of surfaces is the hole one level up from a hand-kept row.

    Every subdirectory of `scripts/helpers/` is either its own ruled-in surface
    or excluded by name with a reason. A third directory appearing fails here
    rather than escaping both lists silently.
    """
    root = _REPO / "scripts" / "helpers"
    subdirs = _dirs(root)
    assert subdirs, f"no subdirectories under {root} — this check read nothing"
    unruled = subdirs - _ruled_in_under(root) - set(NOT_A_SURFACE)
    assert not unruled, (
        f"subdirectories of scripts/helpers/ that are neither a ruled-in "
        f"producer surface nor excluded by name: {sorted(unruled)}. Rule each "
        f"one in or out and record the reason — an unexplained exclusion is the "
        f"hole this phase exists to close."
    )

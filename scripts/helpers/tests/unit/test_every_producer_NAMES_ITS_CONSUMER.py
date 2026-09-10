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
        the writer's own use. It falls out of the keying above rather than
        needing a rule.

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
    members: object
    #: `True` when the surface accumulates items awaiting disposition, which is
    #: what makes the cadence-and-runner clause bind (requirement 2's ruling).
    accumulates: bool
    #: name -> reason. Each is asserted present on disk AND explained in the
    #: README, because an exclusion outliving its subject is how a gate stops
    #: covering the thing it names.
    exclusions: dict = field(default_factory=dict)


def _files(root: Path) -> set[str]:
    return {p.name for p in root.iterdir() if p.is_file()}


def _py(root: Path) -> set[str]:
    return {p.name for p in root.glob("*.py")}


def _dirs(root: Path) -> set[str]:
    return {p.name for p in root.iterdir() if p.is_dir()}


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
        exclusions={
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


@pytest.fixture(params=[s.name for s in SURFACES])
def surface(request) -> Surface:
    s = _BY_NAME[request.param]
    _skip_if_absent(s)
    return s


# --- the two properties every ruled-in surface carries --------------------------

def test_every_member_on_disk_has_a_ROW(surface: Surface) -> None:
    """A member with no row is the failure; a blank cell is only its symptom.

    Read off disk rather than out of the table, because a table checked against
    itself cannot see the member that was never added to it.
    """
    on_disk = _population(surface)
    assert on_disk, f"no members found under {surface.root} — this gate read nothing"
    listed = set(_listed(surface))
    assert on_disk <= listed, (
        f"{surface.name} holds members with no row in {surface.readme.name}: "
        f"{sorted(on_disk - listed)}. A surface nobody reads is what this gate "
        f"exists to stop producing; one nobody LISTS is how one gets there."
    )
    assert listed <= on_disk | set(surface.exclusions), (
        f"{surface.readme.name} lists members that are not on disk: "
        f"{sorted(listed - on_disk - set(surface.exclusions))}"
    )


def test_every_row_NAMES_A_CONSUMER(surface: Surface) -> None:
    """The weaker claim, made of every surface: somebody is named."""
    empty = [m for m, cell in _listed(surface).items()
             if not cell or cell in {"-", "—", "n/a", "TBD"}]
    assert not empty, (
        f"{surface.name} rows with no named consumer: {empty}. Name what reads "
        f"this, or the member does not belong in a surface whose table claims "
        f"every entry answers a standing question."
    )


def test_an_EXCLUSION_still_has_its_subject_and_its_reason(surface: Surface) -> None:
    """An exclusion outliving its subject is how a gate stops covering it.

    Two halves, and the second is the one prose can lose: the name must still be
    on disk, AND the README must still explain why it has no row — otherwise its
    absence from the table reads as an omission to the next person.
    """
    if not surface.exclusions:
        pytest.skip(f"{surface.name} excludes nothing by name")
    text = surface.readme.read_text(encoding="utf-8")
    for name, reason in surface.exclusions.items():
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
    gaps = _cadence_gaps(_listed(surface), surface.exclusions)
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
        assert paths, f"{tool}'s `Invoked by` cell names no path: {cell!r}"
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
    assert checked >= len(_listed(surface)) - len(UNREAD), (
        f"only {checked} invocations were opened — this check scoped itself to "
        f"nothing and would pass vacuously"
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


def test_the_SURFACE_LIST_itself_is_read_off_disk() -> None:
    """A hand-kept list of surfaces is the hole one level up from a hand-kept row.

    Every subdirectory of `scripts/helpers/` is either its own ruled-in surface
    or excluded by name with a reason. A third directory appearing fails here
    rather than escaping both lists silently.
    """
    root = _REPO / "scripts" / "helpers"
    subdirs = {p.name for p in root.iterdir() if p.is_dir()}
    assert subdirs, f"no subdirectories under {root} — this check read nothing"
    ruled_in = {s.name.rstrip("/").rsplit("/", 1)[-1] for s in SURFACES}
    unruled = subdirs - ruled_in - set(NOT_A_SURFACE)
    assert not unruled, (
        f"subdirectories of scripts/helpers/ that are neither a ruled-in "
        f"producer surface nor excluded by name: {sorted(unruled)}. Rule each "
        f"one in or out and record the reason — an unexplained exclusion is the "
        f"hole this phase exists to close."
    )

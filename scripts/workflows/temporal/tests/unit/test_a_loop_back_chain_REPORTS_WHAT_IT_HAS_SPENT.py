"""A parent that can loop back says what the loop has cost, at every decision point.

WHY THIS EXISTS, MEASURED TWICE. Each run prints its own `cost=$X` as it
finishes, and `run-claude.sh` prints a calendar-MONTH rollup beside it. So the
two figures an operator can see are *this one leg* and *everything since the
1st*. The number that decides whether to keep going — what THIS chain has spent
— was reported nowhere.

  * `Skyy-Command#272`: **$111 across 11 invocations**, and the sibling CPI
    report records it was found *"only by adding it up afterwards — after the
    spend"*.
  * This repo, 2026-08-24: a single `build.sh --phase` chain reached **$82.13
    across 5 runs within two hours**, `build-draft` alone at $37.75 for 224
    turns, while the operator was away studying. Nothing surfaced it.

WHAT IS ASSERTED HERE IS THE REPORTING, NOT A LIMIT. No threshold stops a run;
the loop-back bound is still the only stopping authority. A figure an operator
never sees cannot inform a decision, and that is the whole defect being closed.
Whether spend should GATE the loop is a separate ruling, logged in
`cpi-decisions.md` with watch-criteria rather than decided here.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from modules.assistant import assistant_activities as act

# The component root — the directory holding `modules/` — which is what
# `tests/conftest.py` puts on `sys.path`. Anchored two levels up rather than
# counted to the repo root, because the shorter walk cannot drift when the
# component moves.
COMPONENT = Path(__file__).resolve().parents[2]
_BUILD = COMPONENT / "modules" / "assistant" / "build"

# The parents that can loop back. `build_minor` composes the same shape with
# lighter children, so both spend without bound and both owe the figure.
_PARENTS = {
    "build": _BUILD / "build" / "build_workflow.py",
    "build_minor": _BUILD / "build_minor" / "build_minor_workflow.py",
}


def test_the_parents_this_checks_are_actually_there() -> None:
    """If a path moves, every assertion below passes against nothing."""
    for name, path in _PARENTS.items():
        assert path.is_file(), f"{name}: {path} is where this module's subject lives"


# --- the figure itself -------------------------------------------------------

def _log(tmp_path: Path, name: str, cost: float | None, *, result: bool = True) -> Path:
    logs = tmp_path / ".claude" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    f = logs / f"{name}.jsonl"
    lines = [json.dumps({"type": "assistant", "text": "working"})]
    if result:
        event: dict = {"type": "result", "num_turns": 10}
        if cost is not None:
            event["total_cost_usd"] = cost
        lines.append(json.dumps(event))
    f.write_text("\n".join(lines) + "\n")
    return f


def test_it_SUMS_every_run_logged_since_the_marker(tmp_path: Path) -> None:
    _log(tmp_path, "build-draft-1", 37.75)
    _log(tmp_path, "build-refine-1", 15.32)
    _log(tmp_path, "review-pr-1", 4.10)
    dollars, runs = act.chain_cost_usd(tmp_path, 0)
    assert runs == 3, f"expected three priced runs, counted {runs}"
    assert dollars == pytest.approx(57.17), dollars


def test_a_run_with_NO_RESULT_EVENT_is_not_counted_as_free(tmp_path: Path) -> None:
    """A killed run has no `result` event. It is EXCLUDED from the run count,
    not counted at zero — a chain that reports `4 runs` when five fired is a
    figure the operator has to distrust, and the count is what makes the dollars
    legible."""
    _log(tmp_path, "build-draft-1", 12.00)
    _log(tmp_path, "build-refine-1", None, result=False)
    dollars, runs = act.chain_cost_usd(tmp_path, 0)
    assert (dollars, runs) == (12.0, 1)


def test_a_result_event_with_NO_COST_FIELD_is_skipped(tmp_path: Path) -> None:
    """`total_cost_usd` absent is not `0.0`. Reading a missing key as free is how
    a rollup silently under-reports, which is the one direction a spend figure
    must not err in."""
    _log(tmp_path, "build-draft-1", 12.00)
    _log(tmp_path, "build-refine-1", None)      # result event, no cost key
    assert act.chain_cost_usd(tmp_path, 0) == (12.0, 1)


def test_logs_OLDER_than_the_marker_are_excluded(tmp_path: Path) -> None:
    import os
    old = _log(tmp_path, "build-draft-old", 99.99)
    os.utime(old, (1_000_000, 1_000_000))
    _log(tmp_path, "build-draft-new", 5.00)
    dollars, runs = act.chain_cost_usd(tmp_path, 2_000_000)
    assert (dollars, runs) == (5.0, 1), "a prior chain's spend leaked into this one"


@pytest.mark.parametrize("label,root", [
    ("no .claude/logs at all", "missing"),
    ("logs is a file, not a directory", "file"),
])
def test_an_UNREADABLE_LOG_DIR_returns_zero_rather_than_raising(
        tmp_path: Path, label: str, root: str) -> None:
    """A cost figure is an OBSERVATION. A parent must not fail a run that
    succeeded because it could not price it — the failure mode of raising here
    is losing the work, which is strictly worse than losing the number."""
    if root == "file":
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "logs").write_text("not a directory")
    assert act.chain_cost_usd(tmp_path, 0) == (0.0, 0), label


# --- and it reaches the operator ---------------------------------------------

# --- the predicate, lifted out so a LITERAL can be driven through it ---------

def _note_appends(tree: ast.Module) -> list[ast.Call]:
    """Every `notes.append(...)` in an already-parsed module.

    TAKES A TREE RATHER THAN SOURCE, and that is not a style choice.
    `test_a_census_guard_proves_its_own_predicate.py` recognises a tree-walking
    guard by BEHAVIOUR — a literal `ast.parse(<x>.read_text())` — and recognises
    its control the same way, by an `ast.parse` of a snippet. An earlier revision
    of this module took `source: str` and parsed inside, which hid BOTH calls
    behind a helper and dropped this module out of the audited population
    entirely. It was locally tidier and globally unauditable.
    """
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "append"
            and isinstance(n.func.value, ast.Name)
            and n.func.value.id == "notes"]


def _mentions_spend(call: ast.Call) -> bool:
    """Does this call reach `_spend(...)` anywhere inside it?"""
    return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
               and n.func.id == "_spend" for n in ast.walk(call))


def test_the_PREDICATE_discriminates_on_a_literal_snippet() -> None:
    """POSITIVE CONTROL. A census guard that never exercises its own recogniser
    reports green over an accumulating defect the moment the recogniser stops
    matching — issue #103's whole subject, and the reason this repo pins a
    controlled-guard count at all.

    Both directions, because the failures are asymmetric: a recogniser that stops
    SEEING notes makes the population empty and every assertion trivially true,
    while one that reads any append as carrying the figure makes the check
    unfalsifiable. Two snippets, one of each.
    """
    carrying = "notes.append(_spend(repo_root, started) + f\"HOLD: {n} of {m}.\")"
    bare = "notes.append(f\"HOLD: {n} of {m}.\")"
    other = "results.append(_spend(repo_root, started))"

    found = _note_appends(ast.parse(carrying))
    assert len(found) == 1, "the recogniser stopped seeing a `notes.append` call at all"
    assert _mentions_spend(found[0]), "a call that plainly carries `_spend` read as not carrying it"

    found = _note_appends(ast.parse(bare))
    assert len(found) == 1, "the recogniser missed a bare `notes.append`"
    assert not _mentions_spend(found[0]), (
        "a note with no `_spend` read as carrying the figure — the check would pass "
        "over exactly the defect it exists to catch")

    assert not _note_appends(ast.parse(other)), (
        "`results.append` read as a note. The population is `notes.append` "
        "specifically; widening it silently admits calls no operator ever reads.")


@pytest.mark.parametrize("name", sorted(_PARENTS))
def test_every_DECISION_POINT_note_carries_the_spend(name: str) -> None:
    """The figure has to sit where a human reads a decision, not in a log.

    A parent's decision points are the three notes it appends: the loop-back, the
    needs-assistance stop, and the exhausted-runway stop. Each is a moment the
    operator either authorises more spend or does not, so each carries what has
    been spent already. Asserted structurally rather than by string, so a
    reworded note cannot silently drop the figure.
    """
    appends = _note_appends(ast.parse(_PARENTS[name].read_text()))
    assert len(appends) >= 3, f"{name}: found {len(appends)} notes.append calls, expected the decision points"
    carrying = [c for c in appends if _mentions_spend(c)]
    assert len(carrying) >= 3, (
        f"{name}: only {len(carrying)} of {len(appends)} `notes.append` calls carry "
        f"`_spend(...)`. Every note an operator reads at a decision point owes the "
        f"figure — a chain that reports its verdict without its cost asks for a "
        f"ruling while withholding the number the ruling turns on.")


@pytest.mark.parametrize("name", sorted(_PARENTS))
def test_the_CLOCK_is_read_in_an_ACTIVITY_not_in_workflow_code(name: str) -> None:
    """`temporal_standard.md` §3: non-deterministic reads go behind an activity.

    Wall clock is the textbook member — replayed workflow code calling
    `time.time()` gets a different answer than it did the first time and the
    history diverges. Nothing here runs under a worker yet; keeping the
    discipline now makes the port a move rather than a hunt.
    """
    source = _PARENTS[name].read_text()
    assert "act.clock_now()" in source, f"{name}: the start marker must come from the activity"
    assert "time.time()" not in source, (
        f"{name}: a wall-clock read in workflow code. Use `act.clock_now()` — on "
        f"replay this returns a different value and the history diverges.")

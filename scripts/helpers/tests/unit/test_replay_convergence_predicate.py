"""Unit tests for the convergence-predicate replay tool.

`phase5_convergence_stopping.md` step 6 quotes this tool's numbers as the
evidence that the predicate may eventually be trusted to gate. Three properties
make those numbers mean what the doc says they mean, and each is asserted here
with an input that breaks it:

  * it replays THE SHIPPED PREDICATE, not a copy of it — a pinned copy would
    certify a rule nobody runs;
  * the denominator includes every block the predicate would have SEEN, not
    only the ones it could rule on, so "fired 2 of 12" cannot quietly become
    "2 of 2";
  * a CONVERGED assessment against a HOLD verdict is counted as an EARLY fire,
    which is the number that would cancel the phase if it were non-zero.

Flat comment-delimited functions, matching the sibling test modules in this
directory.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_TOOL = Path(__file__).resolve().parents[3] / "helpers" / "measure" / \
    "replay_convergence_predicate.py"


def _tool():
    spec = importlib.util.spec_from_file_location("_replay_convergence", _TOOL)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_replay_convergence"] = module
    spec.loader.exec_module(module)
    return module


def _block(pass_no, verdict, converged, findings):
    return {"pass": pass_no, "verdict": verdict, "converged": converged,
            "findings": [{"id": i, "disposition": d} for i, d in findings],
            "finding_ids": [i for i, _ in findings]}


# --- it replays the SHIPPED predicate ----------------------------------------

def test_the_tool_loads_the_LIVE_predicate_and_not_a_copy() -> None:
    """The whole reason this tool imports rather than pins.

    `replay_completion_predicate.py` deliberately COPIES the rule it replays,
    because it measures a historical miss rate that must stay reproducible. This
    tool validates a candidate before it is trusted, so a copy here would
    validate the copy — the exact `derive != declare` seam that produced two
    `parse_verdict` declarations, one of which decided merges and had no tests.
    """
    tool = _tool()
    shipped = tool._load(tool._CONVERGENCE, "_shipped_probe")
    assert shipped.CLOSED_DISPOSITIONS  # loaded something real
    assert tool._CONVERGENCE.is_file(), "the predicate's declaration site moved"
    assert "modules/assistant/convergence.py" in tool._CONVERGENCE.as_posix()


def test_a_path_loaded_module_is_registered_before_execution() -> None:
    """The `sys.modules` line in `_load` is load-bearing, not tidiness.

    `@dataclass` resolves its own module from `sys.modules[cls.__module__]`; an
    unregistered path-loaded module makes that None and the decorator dies with
    an `AttributeError` naming neither the dataclass nor the loader. This is the
    negative control for that line: the load simply must not raise.
    """
    tool = _tool()
    module = tool._load(tool._CONVERGENCE, "_registration_probe")
    assert sys.modules.get("_registration_probe") is module
    # The dataclass is the thing that would have failed.
    assert module.ConvergenceAssessment(module.ConvergenceState.CONVERGED)


# --- the denominator ---------------------------------------------------------

def test_pass_ONE_is_counted_in_the_denominator_and_lands_in_the_residual_arm() -> None:
    """Reporting only assessable positions would shrink the denominator silently.

    The honest denominator is "blocks the predicate would have seen". A tool
    that dropped pass 1 would turn a 2-of-12 firing count into 2-of-2 without
    anyone editing a number.
    """
    tool = _tool()
    convergence = tool._load(tool._CONVERGENCE, "_c1")
    archive = [{"pr": 1, "blocks": [
        _block(1, "HOLD", False, [("a", "hold")]),
        _block(2, "MERGE", True, [("a", "fixed")]),
    ]}]
    rows = tool.replay(archive, convergence)["rows"]
    assert len(rows) == 2, "a block the predicate would have seen was not counted"
    assert rows[0]["state"] == "indeterminate"
    assert rows[0]["reason"] == "no_prior_pass"
    assert rows[1]["state"] == "converged"


def test_the_index_and_not_the_LABEL_determines_sequence() -> None:
    """PR #66's only block is labelled `pass: 3` and is pass 1 (issue #68).

    A replay keyed on the producer-written label would treat that block as
    having two predecessors it does not have. Both values are reported so the
    divergence is visible rather than resolved silently.
    """
    tool = _tool()
    convergence = tool._load(tool._CONVERGENCE, "_c2")
    archive = [{"pr": 66, "blocks": [_block(3, "HOLD", False, [("a", "hold")])]}]
    row = tool.replay(archive, convergence)["rows"][0]
    assert row["index"] == 1 and row["labelled_pass"] == 3
    assert row["reason"] == "no_prior_pass", (
        "the label was used as the sequence — a block with no predecessor was "
        "assessed as though it had two"
    )


# --- the number that would cancel the phase ----------------------------------

def test_a_CONVERGED_assessment_against_a_HOLD_verdict_is_reported_as_EARLY(
        capsys) -> None:
    """The early-fire count is the one that would cancel gating, so it must fire.

    A stopping rule that fires early ends productive work SILENTLY — there is no
    failing test, just a shorter run. This is the only place that failure has an
    alarm, and a report that could not produce a non-zero here would be
    manufacturing the reassurance the phase rests on.
    """
    tool = _tool()
    convergence = tool._load(tool._CONVERGENCE, "_c3")
    archive = [{"pr": 9, "blocks": [
        _block(1, "HOLD", False, [("a", "hold")]),
        # Converged by the predicate, HOLD by the reviewer: an early stop.
        _block(2, "HOLD", False, [("a", "fixed")]),
    ]}]
    tool.report(tool.replay(archive, convergence), convergence)
    out = capsys.readouterr().out
    assert "Would have FIRED           : 1 of 1" in out
    assert "Would have fired EARLY     : 1" in out


def test_the_early_count_is_ZERO_when_the_reviewer_agreed(capsys) -> None:
    """Negative control — `early` must discriminate, not count every fire.

    Identical input except the verdict. Without this, a report that labelled
    every fire early would satisfy the test above and the phase's headline
    "0 early fires" would be an artifact of the counter.
    """
    tool = _tool()
    convergence = tool._load(tool._CONVERGENCE, "_c4")
    archive = [{"pr": 9, "blocks": [
        _block(1, "HOLD", False, [("a", "hold")]),
        _block(2, "MERGE", True, [("a", "fixed")]),
    ]}]
    tool.report(tool.replay(archive, convergence), convergence)
    out = capsys.readouterr().out
    assert "Would have FIRED           : 1 of 1" in out
    assert "Would have fired EARLY     : 0" in out


def test_a_disagreement_with_the_incumbent_flag_is_counted(capsys) -> None:
    """E7 treats `converged` as a label the computation should reproduce.

    A cross-tab that could only ever report agreement would make that claim
    unfalsifiable. Here the block asserts convergence while a finding is still
    open.
    """
    tool = _tool()
    convergence = tool._load(tool._CONVERGENCE, "_c5")
    archive = [{"pr": 9, "blocks": [
        _block(1, "HOLD", False, [("a", "hold")]),
        _block(2, "MERGE", True, [("a", "hold")]),
    ]}]
    tool.report(tool.replay(archive, convergence), convergence)
    out = capsys.readouterr().out
    assert "DISAGREEMENTS: 1" in out


def test_a_block_predating_the_flag_is_neither_agreement_nor_disagreement(
        capsys) -> None:
    """`None` stays distinct from `False`, or the rate counts old blocks as wrong.

    Absence dates a block to before `converged:` shipped. Folding it into
    `false` would score every pre-flag block as a disagreement with whatever the
    computation said.
    """
    tool = _tool()
    convergence = tool._load(tool._CONVERGENCE, "_c6")
    archive = [{"pr": 9, "blocks": [
        _block(1, "HOLD", None, [("a", "hold")]),
        _block(2, "MERGE", None, [("a", "fixed")]),
    ]}]
    tool.report(tool.replay(archive, convergence), convergence)
    out = capsys.readouterr().out
    assert "DISAGREEMENTS: 0" in out
    assert "asserted=n/a" in out


def test_a_finding_with_no_parseable_disposition_is_treated_as_OPEN(capsys) -> None:
    """The extractor yields `None` for an absent `disposition:`; it must not close.

    A block predating the field, or a hand-edited one, would otherwise EMPTY the
    open set and report convergence that was never observed — the one error
    direction this predicate cannot afford.
    """
    tool = _tool()
    convergence = tool._load(tool._CONVERGENCE, "_c7")
    archive = [{"pr": 9, "blocks": [
        _block(1, "HOLD", False, [("a", "hold")]),
        {"pass": 2, "verdict": "MERGE", "converged": True,
         "findings": [{"id": "a", "disposition": None}], "finding_ids": ["a"]},
    ]}]
    rows = tool.replay(archive, convergence)["rows"]
    assert rows[1]["state"] == "not_converged", (
        "an unparseable disposition emptied the open set"
    )


# --- the tool does not invent its own extractor ------------------------------

def test_the_tool_delegates_extraction_rather_than_re_declaring_the_address() -> None:
    """A fourth declaration of the `pr_review:` marker is exactly issue #68.

    The block address and the per-finding disposition parse are owned by
    `replay_pr_review_blocks.py` and gated against `review_pr_helper` by
    `test_exit_record.py`. This tool must shell out to that one, not carry its
    own regex.
    """
    source = _TOOL.read_text()
    assert "replay_pr_review_blocks.py" in source
    assert "re.compile" not in source, (
        "the replay tool grew its own parser — that is a fourth declaration of "
        "the Kind 1 address, which already has an open issue for having three"
    )

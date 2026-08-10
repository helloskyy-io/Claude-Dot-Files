"""The parent reads the CI verdict, so MERGE is unreachable on a red tree.

WHY THIS IS IN THE PARENT AND NOT A PROMPT. Telling the review agent to check
and withhold MERGE is a convention, and an agent can reason past a convention —
"unrelated failure, proceeding" is the exact shape being guarded against. In the
parent the agent never gets a verdict to give.

WHY IT MATTERS HERE. Branch protection was removed from this repo on 2026-08-09
because it was available on 12 of 33 org repos and could not be replicated on
the two that matter most. `suite` has run on every PR since and nothing consumed
its verdict, so `gh pr merge` succeeded on red. This closes that.

THE THIRD STATE IS THE ONE THAT GETS FUDGED. "No checks reported" is NOT green,
and a silent skip is the filtered-gate defect wearing different clothes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from modules.assistant.build import build_activities as act  # noqa: E402
from modules.assistant.build.build_activities import BLOCKING_CHECKS, CiVerdict  # noqa: E402


def _gh(monkeypatch, payload, *, stdout=None):
    """Stand in for `gh pr checks --json name,state`."""
    class R:
        def __init__(self): self.stdout = stdout if stdout is not None else json.dumps(payload)
    monkeypatch.setattr(act.subprocess, "run", lambda *a, **k: R())


def test_the_blocking_set_is_not_empty():
    """Guards every test below: an empty set would make them pass vacuously by
    routing everything to NO_CHECKS."""
    assert BLOCKING_CHECKS, "BLOCKING_CHECKS is empty — the gate cannot block anything"


def test_a_failing_blocking_check_is_RED_and_names_it(monkeypatch):
    _gh(monkeypatch, [{"name": "suite", "state": "FAILURE"}])
    verdict, failed = act.ci_verdict("1")
    assert verdict is CiVerdict.RED
    assert failed == ["suite"], "the runway must name which check failed"


def test_all_green_is_GREEN(monkeypatch):
    _gh(monkeypatch, [{"name": "suite", "state": "SUCCESS"}])
    assert act.ci_verdict("1")[0] is CiVerdict.GREEN


def test_an_ADVISORY_check_failing_does_NOT_block(monkeypatch):
    """The carve-out, pinned. `gh pr checks` reports JOB STATUS: a CodeQL job
    failure means the scan did not COMPLETE, not that it FOUND something.
    Gating on it would let the scanner breaking halt the fleet."""
    _gh(monkeypatch, [
        {"name": "suite", "state": "SUCCESS"},
        {"name": "CodeQL", "state": "FAILURE"},
        {"name": "Analyze (python)", "state": "FAILURE"},
    ])
    assert act.ci_verdict("1")[0] is CiVerdict.GREEN


def test_an_advisory_check_alone_is_NO_CHECKS_not_green(monkeypatch):
    """If the gating check did not run at all, advisory checks passing must not
    be read as a pass — that is the substitution this whole gate exists to stop."""
    _gh(monkeypatch, [{"name": "CodeQL", "state": "SUCCESS"}])
    assert act.ci_verdict("1")[0] is CiVerdict.NO_CHECKS


def test_no_checks_at_all_is_NO_CHECKS(monkeypatch):
    _gh(monkeypatch, [])
    assert act.ci_verdict("1")[0] is CiVerdict.NO_CHECKS


def test_empty_output_is_NO_CHECKS_not_green(monkeypatch):
    _gh(monkeypatch, None, stdout="")
    assert act.ci_verdict("1")[0] is CiVerdict.NO_CHECKS


def test_unreadable_output_fails_into_the_state_that_STOPS(monkeypatch):
    """Malformed JSON is not a pass. Fail into the state that reports, never
    into the one that proceeds silently."""
    _gh(monkeypatch, None, stdout="not json at all")
    assert act.ci_verdict("1")[0] is not CiVerdict.GREEN


@pytest.mark.parametrize("state", ["SUCCESS", "SKIPPED", "NEUTRAL"])
def test_non_failing_states_do_not_block(monkeypatch, state):
    _gh(monkeypatch, [{"name": "suite", "state": state}])
    assert act.ci_verdict("1")[0] is CiVerdict.GREEN


@pytest.mark.parametrize("state", ["FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "PENDING"])
def test_anything_that_is_not_a_pass_blocks(monkeypatch, state):
    """Deliberately inclusive: an unrecognised state must block rather than pass.
    A new state GitHub adds later must not silently become green."""
    _gh(monkeypatch, [{"name": "suite", "state": state}])
    assert act.ci_verdict("1")[0] is CiVerdict.RED

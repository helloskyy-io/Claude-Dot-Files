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
from modules.assistant.build.build_activities import POLICY_PATH, CiVerdict  # noqa: E402


def _gh(monkeypatch, payload, *, stdout=None):
    """Stand in for `gh pr checks --json name,state`."""
    class R:
        def __init__(self): self.stdout = stdout if stdout is not None else json.dumps(payload)
    monkeypatch.setattr(act.subprocess, "run", lambda *a, **k: R())


@pytest.fixture
def repo(tmp_path):
    """A target repo declaring `suite` blocking and CodeQL advisory."""
    d = tmp_path / POLICY_PATH
    d.parent.mkdir(parents=True, exist_ok=True)
    d.write_text("blocking:\n  - suite\nadvisory:\n  - name: CodeQL\n    reason: default setup\n")
    return tmp_path


def test_this_repo_declares_its_own_policy_and_it_names_a_blocking_check():
    """Guards every test below AND this repo's own gate.

    An empty or absent declaration routes everything to NO_CHECKS, which would
    make the tests below pass vacuously and would silently un-gate this repo.
    """
    import yaml
    path = Path(__file__).resolve().parents[5] / POLICY_PATH
    assert path.is_file(), f"{POLICY_PATH} is missing — this repo declares no gate"
    doc = yaml.safe_load(path.read_text())
    assert doc.get("blocking"), "the blocking list is empty — the gate cannot block anything"
    assert "suite" in doc["blocking"], "the test runner is not declared blocking"


def test_a_failing_blocking_check_is_RED_and_names_it(monkeypatch, repo):
    _gh(monkeypatch, [{"name": "suite", "state": "FAILURE"}])
    verdict, failed = act.ci_verdict("1", repo_root=repo)
    assert verdict is CiVerdict.RED
    assert failed == ["suite"], "the runway must name which check failed"


def test_all_green_is_GREEN(monkeypatch, repo):
    _gh(monkeypatch, [{"name": "suite", "state": "SUCCESS"}])
    assert act.ci_verdict("1", repo_root=repo)[0] is CiVerdict.GREEN


def test_an_ADVISORY_check_failing_does_NOT_block(monkeypatch, repo):
    """The carve-out, pinned. `gh pr checks` reports JOB STATUS: a CodeQL job
    failure means the scan did not COMPLETE, not that it FOUND something.
    Gating on it would let the scanner breaking halt the fleet."""
    _gh(monkeypatch, [
        {"name": "suite", "state": "SUCCESS"},
        {"name": "CodeQL", "state": "FAILURE"},
        {"name": "Analyze (python)", "state": "FAILURE"},
    ])
    assert act.ci_verdict("1", repo_root=repo)[0] is CiVerdict.GREEN


def test_an_advisory_check_alone_is_NO_CHECKS_not_green(monkeypatch, repo):
    """If the gating check did not run at all, advisory checks passing must not
    be read as a pass — that is the substitution this whole gate exists to stop."""
    _gh(monkeypatch, [{"name": "CodeQL", "state": "SUCCESS"}])
    assert act.ci_verdict("1", repo_root=repo)[0] is CiVerdict.NO_CHECKS


def test_no_checks_at_all_is_NO_CHECKS(monkeypatch, repo):
    _gh(monkeypatch, [])
    assert act.ci_verdict("1", repo_root=repo)[0] is CiVerdict.NO_CHECKS


def test_empty_output_is_NO_CHECKS_not_green(monkeypatch, repo):
    _gh(monkeypatch, None, stdout="")
    assert act.ci_verdict("1", repo_root=repo)[0] is CiVerdict.NO_CHECKS


def test_unreadable_output_fails_into_the_state_that_STOPS(monkeypatch, repo):
    """Malformed JSON is not a pass. Fail into the state that reports, never
    into the one that proceeds silently."""
    _gh(monkeypatch, None, stdout="not json at all")
    assert act.ci_verdict("1", repo_root=repo)[0] is not CiVerdict.GREEN


@pytest.mark.parametrize("state", ["SUCCESS", "SKIPPED", "NEUTRAL"])
def test_non_failing_states_do_not_block(monkeypatch, repo, state):
    _gh(monkeypatch, [{"name": "suite", "state": state}])
    assert act.ci_verdict("1", repo_root=repo)[0] is CiVerdict.GREEN


@pytest.mark.parametrize("state", ["FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "PENDING"])
def test_anything_that_is_not_a_pass_blocks(monkeypatch, repo, state):
    """Deliberately inclusive: an unrecognised state must block rather than pass.
    A new state GitHub adds later must not silently become green."""
    _gh(monkeypatch, [{"name": "suite", "state": state}])
    assert act.ci_verdict("1", repo_root=repo)[0] is CiVerdict.RED


# --- The declaration itself: two states that did not exist before -------------


def test_a_malformed_declaration_STOPS_rather_than_skipping(monkeypatch, tmp_path):
    """A declaration that EXISTS and cannot be read is a different fact from no
    declaration. Collapsing them is how the skip path becomes the new exit."""
    d = tmp_path / POLICY_PATH
    d.parent.mkdir(parents=True, exist_ok=True)
    d.write_text("blocking: [unclosed\n  - broken: : :\n")
    _gh(monkeypatch, [{"name": "suite", "state": "SUCCESS"}])
    assert act.ci_verdict("1", repo_root=tmp_path)[0] is CiVerdict.UNREADABLE_POLICY


def test_a_declaration_that_is_not_a_mapping_is_unreadable(monkeypatch, tmp_path):
    d = tmp_path / POLICY_PATH
    d.parent.mkdir(parents=True, exist_ok=True)
    d.write_text("- just\n- a\n- list\n")
    _gh(monkeypatch, [{"name": "suite", "state": "SUCCESS"}])
    assert act.ci_verdict("1", repo_root=tmp_path)[0] is CiVerdict.UNREADABLE_POLICY


def test_an_absent_declaration_is_NO_CHECKS_not_unreadable(monkeypatch, tmp_path):
    """A repo may legitimately have no gate. That is a skip, not a stop."""
    _gh(monkeypatch, [{"name": "suite", "state": "SUCCESS"}])
    assert act.ci_verdict("1", repo_root=tmp_path)[0] is CiVerdict.NO_CHECKS


def test_a_DIFFERENT_repos_check_name_gates_it(monkeypatch, tmp_path):
    """The finding that produced this change: a hardcoded ("suite",) meant the
    MDC side's `master-test-tier` matched nothing and every PR skipped."""
    d = tmp_path / POLICY_PATH
    d.parent.mkdir(parents=True, exist_ok=True)
    d.write_text("blocking:\n  - master-test-tier\n")
    _gh(monkeypatch, [{"name": "master-test-tier", "state": "FAILURE"}])
    v, failed = act.ci_verdict("1", repo_root=tmp_path)
    assert v is CiVerdict.RED and failed == ["master-test-tier"]


def test_a_check_declared_NEITHER_way_is_reported_by_name(monkeypatch, repo):
    """The Testing Standard admits no third state. An undeclared check is
    surfaced, never silently gated: it must not halt the fleet, and must not
    hide either."""
    _gh(monkeypatch, [
        {"name": "suite", "state": "SUCCESS"},
        {"name": "brand-new-scanner", "state": "SUCCESS"},
    ])
    v, undeclared = act.ci_verdict("1", repo_root=repo)
    assert v is CiVerdict.GREEN
    assert undeclared == ["brand-new-scanner"]

"""The journal's completeness contract, and every rule that makes it able to fail.

`validate.py` answers integrity and says so in its own header; nothing answered
completeness, so the first two derivations of it disagreed — a file count called
a harvest-index-only bag populated and called an honestly-empty harvest
incomplete. `profile.assess` is the one definition, and these are its controls.

Every rule below has a POSITIVE CONTROL: the same fixture with the rule's
condition removed must flip the verdict. A completeness checker that cannot be
made to fail is the defect it was written to detect, one level up.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from common.journal import profile as pf


_UNSET = object()


def _bag(tmp: Path, *, events: str | None = '{"a":1}\n',
         surfaces: list | None = [], harvest_events: str | None = None,
         repo: str | None = _UNSET, worktree: str = "build-minor-1",
         name: str = "run") -> Path:
    if repo is _UNSET:                       # a joinable repo with no child logs
        joinable = tmp / "repo-none"
        (joinable / ".claude" / "logs").mkdir(parents=True, exist_ok=True)
        repo = str(joinable)
        pf._LOG_INDEX.clear()
    bag = tmp / name
    (bag / "data" / "harvest").mkdir(parents=True)
    lines = ["External-Identifier: " + name, "Journal-Workflow: build-minor"]
    if repo is not None:
        lines.append(f"Journal-Origin-Repo: {repo}")
        lines.append(f"Journal-Worktree: {worktree}")
    (bag / "bag-info.txt").write_text("\n".join(lines) + "\n")
    if events is not None:
        (bag / "data" / "events.jsonl").write_text(events)
    if surfaces is not None:
        (bag / "data" / "harvest" / "index.json").write_text(
            json.dumps({"schema": 1, "surfaces": surfaces}))
    if harvest_events is not None:
        (bag / "data" / "harvest" / "events.jsonl").write_text(harvest_events)
    return bag


def _repo_with_log(tmp: Path, worktree: str, session: str, name: str = "child") -> Path:
    repo = tmp / f"repo-{name}"
    logs = repo / ".claude" / "logs"
    logs.mkdir(parents=True)
    (logs / f"{name}.jsonl").write_text(json.dumps(
        {"type": "system", "cwd": f"{repo}/.claude/worktrees/{worktree}",
         "session_id": session}) + "\n")
    pf._LOG_INDEX.clear()
    return repo


def test_the_full_shape_is_complete(tmp_path: Path) -> None:
    bag = _bag(tmp_path, surfaces=[{"pr": 1}], harvest_events='{"e":1}\n')
    assert pf.assess_completeness(bag).verdict == pf.COMPLETE


def test_an_empty_harvest_population_is_COMPLETE(tmp_path: Path) -> None:
    """`surfaces: []` with no events file is the harvest reporting it ran over
    nothing — the proof-of-run discipline, not a missing part."""
    assert pf.assess_completeness(_bag(tmp_path, surfaces=[])).verdict == pf.COMPLETE


def test_the_control_a_NAMED_surface_with_no_events_file_is_incomplete(tmp_path: Path) -> None:
    result = pf.assess_completeness(_bag(tmp_path, surfaces=[{"pr": 1}], harvest_events=None))
    assert result.verdict == pf.INCOMPLETE
    assert any("names 1 surface" in r for r in result.reasons)


def test_events_and_harvest_index_are_each_required(tmp_path: Path) -> None:
    no_events = pf.assess_completeness(_bag(tmp_path, events=None, name="a"))
    assert no_events.verdict == pf.INCOMPLETE
    assert any("emitted nothing" in r for r in no_events.reasons)
    no_index = pf.assess_completeness(_bag(tmp_path, surfaces=None, name="b"))
    assert no_index.verdict == pf.INCOMPLETE
    assert any("no evidence the harvest ran" in r for r in no_index.reasons)


def test_an_empty_events_file_does_not_pass_as_present(tmp_path: Path) -> None:
    assert pf.assess_completeness(_bag(tmp_path, events="")).verdict == pf.INCOMPLETE


def test_harvest_events_without_a_surface_is_a_disagreement(tmp_path: Path) -> None:
    result = pf.assess_completeness(_bag(tmp_path, surfaces=[], harvest_events='{"e":1}\n'))
    assert result.verdict == pf.INCOMPLETE
    assert any("disagree" in r for r in result.reasons)


def test_a_child_log_the_bag_does_not_hold_is_an_ORPHAN(tmp_path: Path) -> None:
    """The defect measured on 2026-09-18: a completed child, a valid empty bag."""
    repo = _repo_with_log(tmp_path, "build-minor-1", "aaaaaaaa-1111")
    bag = _bag(tmp_path, events='{"content":"{\\"session_id\\":\\"bbbbbbbb-2222\\"}"}\n',
               surfaces=[], repo=str(repo))
    result = pf.assess_completeness(bag)
    assert result.verdict == pf.INCOMPLETE
    assert len(result.orphaned_logs) == 1
    assert any("record did not land" in r for r in result.reasons)


def test_the_control_a_child_log_the_bag_HOLDS_is_not_an_orphan(tmp_path: Path) -> None:
    repo = _repo_with_log(tmp_path, "build-minor-1", "aaaaaaaa-1111")
    bag = _bag(tmp_path, events='{"content":"{\\"session_id\\":\\"aaaaaaaa-1111\\"}"}\n',
               surfaces=[], repo=str(repo))
    result = pf.assess_completeness(bag)
    assert result.orphaned_logs == ()
    assert result.verdict == pf.COMPLETE


def test_a_log_that_only_MENTIONS_the_worktree_is_not_joined(tmp_path: Path) -> None:
    """The join is the log's own `cwd`. A later run that prints the path — a
    worktree listing, a reviewer reading the tree — mentions it without being
    it, and joining on mention attributes another run's work to this bag."""
    repo = _repo_with_log(tmp_path, "somewhere-else", "cccccccc-3333")
    (repo / ".claude" / "logs" / "mentions.jsonl").write_text(
        json.dumps({"cwd": f"{repo}/.claude/worktrees/somewhere-else",
                    "session_id": "cccccccc-3333",
                    "text": "inspected .claude/worktrees/build-minor-1"}) + "\n")
    pf._LOG_INDEX.clear()
    bag = _bag(tmp_path, surfaces=[], repo=str(repo), worktree="build-minor-1")
    assert pf.assess_completeness(bag).orphaned_logs == ()


def test_an_unjoinable_bag_is_UNVERIFIABLE_not_proven(tmp_path: Path) -> None:
    """No origin repo means the witness cannot be consulted. That is not
    evidence of completeness and must not read as a pass."""
    result = pf.assess_completeness(_bag(tmp_path, surfaces=[], repo=None))
    assert result.verdict == pf.INCOMPLETE
    assert any("UNVERIFIABLE" in r for r in result.reasons)


def test_a_bag_with_no_info_file_is_unreadable_not_complete(tmp_path: Path) -> None:
    empty = tmp_path / "nothing"
    empty.mkdir()
    assert pf.assess_completeness(empty).verdict == pf.UNREADABLE


def test_integrity_and_completeness_stay_separate_tools() -> None:
    """`validate.py`'s contract is integrity-only and states so. If that header
    ever stops saying it, the two questions have been merged and this profile's
    reason for existing has changed."""
    header = (Path(__file__).resolve().parents[2] / "scripts" / "validate_bag.py").read_text()
    assert "ANSWERS INTEGRITY, NOT STATE" in header

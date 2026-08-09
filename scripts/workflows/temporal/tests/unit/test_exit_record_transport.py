"""The transport seam: what the CLI actually emits, and who reads it.

THE FIXTURE IS MEASURED, NOT WRITTEN. `tests/fixtures/schema_declared_run.jsonl`
is a real `claude -p` run on CLI 2.1.224 (2026-08-09, host
`puma-workstation-mint`), reduced to the events under test. It was produced by
asking for prose ending in a VERDICT line AND a structured-output tool call —
the exact shape `review-pr` produces — and it carries the finding that changed
this phase's build:

    declaring `--json-schema` REPLACES `.result` with the serialised structured
    output, so the model's prose, and with it the completion signal, survives
    ONLY in the stream's assistant text blocks.

`run-claude.sh`'s § Completion contract reads `.result`. A caller that added
`--json-schema` without moving that read would have deleted the fleet's only
write-time gate in the same change that added the typed record — silently, and
on every conforming run. These tests are that finding, executable.

AND MOVING THE READ IS NOT ENOUGH ON ITS OWN. The gate's job is catching a run
that ENDED early, which `.result` supplied for free by being the final message.
A filter over every assistant block finds the signal — and finds it in a run
that printed it at turn 20 and then stopped mid-work. So the assistant-side
tests come in a pair: one that the signal is found, one that a NON-FINAL signal
is rejected. Only the second can tell a correct gate from a widened one.

WHY THE BASH FILTER IS EXTRACTED AND RUN RATHER THAN RESTATED. A test carrying
its own copy of the jq program would pass forever against a script whose
expression had drifted — the duplicated-vocabulary defect, one layer down. The
expression under test is pulled out of the shipped file and executed.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from modules.assistant import assistant_activities as act

_TESTS = Path(__file__).resolve().parents[1]
_WORKFLOWS = Path(__file__).resolve().parents[3]      # …/scripts/workflows
RUN_CLAUDE = _WORKFLOWS / "activities" / "run-claude.sh"
FIXTURE = _TESTS / "fixtures" / "schema_declared_run.jsonl"


def test_the_fixture_is_the_shape_this_phase_measured() -> None:
    """Guards the fixture itself: if it stops carrying the finding, say so.

    A regression test built on a fixture that quietly lost the property it
    demonstrates is a green test asserting nothing.
    """
    events = [json.loads(line) for line in FIXTURE.read_text().splitlines()]
    result = next(e for e in events if e["type"] == "result")
    assert result["subtype"] == "success"
    assert "structured_output" in result
    # The finding, stated as an assertion: the prose is NOT in `.result`.
    assert "VERDICT:" not in result["result"]
    assert json.loads(result["result"]) == result["structured_output"]


# ---------------------------------------------------------------------------
# The Python readers.
# ---------------------------------------------------------------------------

def test_assistant_text_finds_the_verdict_the_result_key_no_longer_carries() -> None:
    text = act.assistant_text(FIXTURE)
    assert "VERDICT: MERGE" in text


def test_result_event_returns_the_envelope_with_its_structured_output() -> None:
    event = act.result_event(FIXTURE)
    assert event is not None
    assert event["structured_output"]["outcome"] == "merge"


def test_a_log_with_no_result_event_reads_as_None(tmp_path: Path) -> None:
    """The negative control, and a real state: a run killed before it finished."""
    log = tmp_path / "partial.jsonl"
    log.write_text('{"type":"assistant","message":{"content":[]}}\n')
    assert act.result_event(log) is None
    assert act.assistant_text(log) == ""


def test_a_missing_log_reads_as_None_rather_than_raising(tmp_path: Path) -> None:
    assert act.result_event(tmp_path / "never-written.jsonl") is None


def test_malformed_lines_are_skipped_rather_than_killing_the_read(tmp_path: Path) -> None:
    """The stream interleaves non-JSON, and a routing read must survive it.

    Losing the record to a stray stderr line would route a clean run to a human
    for a reason that has nothing to do with the run.
    """
    log = tmp_path / "noisy.jsonl"
    log.write_text(
        "warning: something on stderr\n"
        '{"type":"assistant","message":{"content":[{"type":"text","text":"VERDICT: MERGE"}]}}\n'
        "{not json at all\n"
        '{"type":"result","subtype":"success","permission_denials":[]}\n'
    )
    assert act.result_event(log)["subtype"] == "success"
    assert act.assistant_text(log) == "VERDICT: MERGE"


# ---------------------------------------------------------------------------
# The channel's freshness property, which is BUILT rather than closed.
# ---------------------------------------------------------------------------

class _FrozenClock:
    """Pins the timestamp so a collision under test is deterministic.

    Without this every case below would depend on two calls landing in the same
    wall-clock second, which is exactly the flakiness the allocation exists to
    make irrelevant. It is a CLOCK ONLY — it deliberately does not pin the
    nonce, because the whole point of the current design is that a shared stamp
    is no longer sufficient for a collision.
    """

    STAMP = "20260809-010203"

    def now(self):
        return self

    def strftime(self, _fmt: str) -> str:
        return self.STAMP


def test_two_dispatches_in_the_SAME_SECOND_get_different_paths(
        tmp_path: Path, monkeypatch) -> None:
    """The measured defect, at its real granularity.

    `MODEL_KEY` is a constant shared by every PR the workflow reviews, and the
    log directory is the repo root's — `run_review_pr` sets `worktree =
    repo_root` and `build_workflow` passes `repo_root` — so it is SHARED ACROSS
    CONCURRENT DISPATCHES rather than per-worktree. With a name of
    `{model_key}-{second-granular stamp}` two dispatches entering in one second
    produced ONE path, both saw no file, and one truncated the other's log. The
    clock is frozen here to reproduce that second exactly.
    """
    monkeypatch.setattr(act, "datetime", _FrozenClock())
    first = act.claude_log_path(tmp_path, "review-pr", run_id="a" * 32)
    second = act.claude_log_path(tmp_path, "review-pr", run_id="b" * 32)

    assert first != second, (
        "two same-second dispatches of one model key landed on one path — the "
        "name is not unique by construction and one run will truncate the other"
    )
    assert first.name.startswith("review-pr-20260809-010203-")


def test_the_path_is_RESERVED_not_merely_checked(tmp_path: Path) -> None:
    """Check-then-create reserved nothing, and that was the defect one level up.

    The file is created later, by a DIFFERENT PROCESS, at `run-claude.sh`'s
    `> "$LOG_FILE"` (`O_TRUNC`). A guard that returns a name it has not claimed
    leaves the whole gap between allocation and that redirect open, whatever the
    name looks like. This asserts the claim exists on disk when the call returns.
    """
    path = act.claude_log_path(tmp_path, "review-pr", run_id="c" * 32)
    assert path.exists(), (
        "the allocation returned a name it did not reserve — the TOCTOU window "
        "between this call and run-claude.sh's O_TRUNC redirect is still open"
    )
    assert path.read_text() == "", "the reservation must not carry content"


def test_a_reused_nonce_is_refused_rather_than_truncated(
        tmp_path: Path, monkeypatch) -> None:
    """The residual collision FAILS LOUD instead of silently truncating.

    Unique-by-construction naming and atomic reservation are two independent
    fixes and this is the second one: with the clock AND the nonce both pinned,
    the only honest outcome is a refusal. `build_workflow` invoking `review-pr`
    twice in one run is the in-process shape of this; a reused nonce is the
    residual one.
    """
    monkeypatch.setattr(act, "datetime", _FrozenClock())
    act.claude_log_path(tmp_path, "review-pr", run_id="d" * 32)
    with pytest.raises(FileExistsError, match="refusing to reuse"):
        act.claude_log_path(tmp_path, "review-pr", run_id="d" * 32)


def test_a_fresh_path_is_allocated_when_nothing_is_there(tmp_path: Path) -> None:
    """Negative control: the guard must not refuse every allocation."""
    path = act.claude_log_path(tmp_path, "review-pr", run_id="e" * 32)
    assert path.parent == tmp_path / ".claude" / "logs"
    assert path.suffix == ".jsonl"


def test_an_empty_reservation_reads_as_an_ABSENT_record_not_a_crash(
        tmp_path: Path) -> None:
    """Reserving creates a file, and every reader here already handles an empty one.

    This is the consequence check on fix 2, not a restatement of it: the
    reservation makes `log_file.exists()` true from allocation onward, so a run
    that dies before `run-claude.sh` writes anything now presents an EMPTY log
    where it previously presented a MISSING one. Both must route `record_absent`
    — if the empty case raised or yielded garbage, the fix would have moved the
    failure rather than removed it.
    """
    path = act.claude_log_path(tmp_path, "review-pr", run_id="f" * 32)
    assert list(act._log_events(path)) == []
    assert act.result_event(path) is None
    assert act.assistant_text(path) == ""


# ---------------------------------------------------------------------------
# The bash half, extracted from the shipped script and executed.
# ---------------------------------------------------------------------------

# THE WHOLE COMMAND SUBSTITUTION IS EXTRACTED AND EXECUTED, not the jq program
# inside it. Extracting only the filter and re-running it under a hand-written
# `jq -rs` meant the test supplied its OWN invocation, so everything about how
# the shipped line reaches jq — the slurp, the prefilter, the redirections —
# was outside the assertion. That is how a gate that aborts on one malformed
# log line shipped green: the Python reader beside it has a test proving such
# lines occur, and the bash reader was never run over one.
# ANCHORED ON THE SURROUNDING BASH, NOT ON THE COMMAND'S SHAPE. Both gates are
# matched by their position in the if/else, so any invocation shape extracts:
# one jq, two piped, a prefilter added or removed. Pinning the shape instead
# would make a behavioural regression surface as "run-claude.sh no longer
# carries a gate", which is the wrong red — the reader would go looking for a
# deleted line that is still there. The properties are held by the tests below;
# this only has to hand them what actually ships.
_ASSISTANT_GATE = re.compile(
    r"""final_result=\$\((.*?)\)\n\s*else\b""", re.DOTALL)
_RESULT_GATE = re.compile(
    r"""final_result=\$\((jq -r 'select\(\.type == "result"\).*?)\)\n""", re.DOTALL)


def _run_shipped(gate: str, log: Path) -> str:
    """Run one extracted command substitution with `$LOG_FILE` bound to `log`."""
    out = subprocess.run(["bash", "-c", gate], capture_output=True, text=True,
                         env={**os.environ, "LOG_FILE": str(log)})
    assert out.returncode == 0, out.stderr
    return out.stdout


def _shipped_assistant_gate() -> str:
    m = _ASSISTANT_GATE.search(RUN_CLAUDE.read_text())
    assert m, "run-claude.sh no longer carries an assistant-text completion gate"
    return m.group(1)


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq is a hard dependency of the fleet")
def test_the_shipped_assistant_gate_finds_the_completion_signal() -> None:
    """The schema-declared branch of the completion gate, run as shipped."""
    assert "VERDICT: MERGE" in _run_shipped(_shipped_assistant_gate(), FIXTURE)


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq is a hard dependency of the fleet")
def test_the_gate_survives_the_malformed_lines_the_stream_actually_carries(
    tmp_path: Path,
) -> None:
    """THE CONTROL THAT WAS MISSING, and its absence deleted the gate silently.

    `assistant_activities._log_events` states the stream interleaves non-JSON
    and that a reader MUST skip it, and
    `test_malformed_lines_are_skipped_rather_than_killing_the_read` above proves
    the Python reader does. The bash reader of the SAME FILE used `jq -s`, which
    must parse the entire input before emitting anything — so one stray stderr
    line made `final_result` empty and the gate announced "RUN ENDED WITHOUT
    COMPLETING" for a run that had completed. Every fixture the bash tests used
    was clean, so nothing was red.

    This log is that log: the conforming stream with exactly the two noise lines
    the Python-side fixture already uses. A correct gate still finds the verdict.
    """
    log = tmp_path / "noisy.jsonl"
    log.write_text(
        "warning: something on stderr\n"
        + FIXTURE.read_text()
        + "{not json at all\n"
    )
    assert "VERDICT: MERGE" in _run_shipped(_shipped_assistant_gate(), log)


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq is a hard dependency of the fleet")
def test_the_shipped_result_gate_would_have_MISSED_it() -> None:
    """The negative control, and it is the whole finding.

    This is the branch V1 still uses, run against a schema-declaring log. It
    must come back WITHOUT the completion signal — if it ever starts finding
    one, the CLI changed its `.result` behaviour and the branch above is no
    longer needed. Either way this test is the thing that says so.
    """
    m = _RESULT_GATE.search(RUN_CLAUDE.read_text())
    assert m, "run-claude.sh no longer carries a .result completion gate"
    assert "VERDICT: MERGE" not in _run_shipped(m.group(1), FIXTURE)


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq is a hard dependency of the fleet")
def test_the_gate_still_REJECTS_a_verdict_that_is_not_the_final_word(tmp_path: Path) -> None:
    """THE MUTATION EVIDENCE FOR THE GATE ITSELF, which is what it exists to be.

    The gate's whole job is catching a headless early-stop: a run that ended a
    turn with text while work was outstanding. `.result` gave that for free by
    being the FINAL message. Moving the read to the assistant blocks had to keep
    it, and a filter over every block would not — it changes the predicate from
    "the run finished with a verdict" to "the run ever mentioned a verdict",
    readmitting exactly the failure the gate was built for.

    A test asserting only that the filter FINDS a verdict cannot tell the two
    apart: it passes under both. This log is the discriminator — the verdict is
    printed at turn 1 and the run then stops mid-work, so a correct gate comes
    back without it.
    """
    log = tmp_path / "early-stop.jsonl"
    log.write_text(
        '{"type":"assistant","parent_tool_use_id":null,"message":{"content":'
        '[{"type":"text","text":"Draft: VERDICT: MERGE"}]}}\n'
        '{"type":"assistant","parent_tool_use_id":null,"message":{"content":'
        '[{"type":"text","text":"Let me confirm the comment posted."}]}}\n'
    )
    out = _run_shipped(_shipped_assistant_gate(), log)
    assert "VERDICT: MERGE" not in out
    assert "Let me confirm" in out, "the filter must still read the LAST block"


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq is a hard dependency of the fleet")
def test_the_gate_ignores_a_verdict_line_from_a_sub_agent(tmp_path: Path) -> None:
    """A nested Task agent's terminal line is not this run's completion signal.

    Sub-agent assistant events carry a `parent_tool_use_id`; the top-level
    model's carry null (verified on a live CLI 2.1.224 stream). Without the
    filter a sub-agent could satisfy its parent's gate.
    """
    log = tmp_path / "subagent.jsonl"
    log.write_text(
        '{"type":"assistant","parent_tool_use_id":null,"message":{"content":'
        '[{"type":"text","text":"Dispatching a reviewer."}]}}\n'
        '{"type":"assistant","parent_tool_use_id":"toolu_1","message":{"content":'
        '[{"type":"text","text":"VERDICT: MERGE"}]}}\n'
    )
    assert "VERDICT: MERGE" not in _run_shipped(_shipped_assistant_gate(), log)


def test_the_json_schema_flag_is_gated_on_the_caller_declaring_one() -> None:
    """The FROZEN V1 fleet's command line must be unchanged, byte for byte.

    A structural check, because the alternative is invoking the CLI. The
    positive control is the second assertion: the flag must actually be there
    for a caller that does declare a schema, or this would pass against a script
    that had dropped the feature entirely.
    """
    source = RUN_CLAUDE.read_text()
    gate = re.search(
        r'if \[\[ -n "\$\{EXIT_RECORD_SCHEMA:-\}" \]\]; then\s*\n\s*'
        r'claude_cmd\+=\(--json-schema "\$EXIT_RECORD_SCHEMA"\)', source)
    assert gate, "--json-schema is no longer gated on EXIT_RECORD_SCHEMA"
    # Positive control: exactly one EXECUTABLE line adds the flag, and it is the
    # one inside the gate. Comment lines are excluded — the header documents the
    # variable, and a doc mention is not a second code path.
    executable = [ln for ln in source.splitlines()
                  if "--json-schema" in ln and not ln.lstrip().startswith("#")]
    assert len(executable) == 1, executable
    assert 'EXIT_RECORD_SCHEMA' in executable[0]

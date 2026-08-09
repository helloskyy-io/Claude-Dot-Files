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

`run-claude.sh:201-204` reads `.result` for the completion contract. A caller
that added `--json-schema` without moving that read would have deleted the
fleet's only write-time gate in the same change that added the typed record —
silently, and on every conforming run. These tests are that finding, executable.

WHY THE BASH FILTER IS EXTRACTED AND RUN RATHER THAN RESTATED. A test carrying
its own copy of the jq program would pass forever against a script whose
expression had drifted — the duplicated-vocabulary defect, one layer down. The
expression under test is pulled out of the shipped file and executed.
"""

from __future__ import annotations

import json
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

def test_a_reused_log_path_is_refused_rather_than_truncated(tmp_path: Path, monkeypatch) -> None:
    """`build_workflow` invokes `review-pr` twice in one run.

    The stamp is second-granular and the model key repeats, so a collision is
    reachable. Truncating would destroy the first run's record; leaving it would
    hand this run a stale one. Neither is acceptable, so it raises.
    """
    path = act.claude_log_path(tmp_path, "review-pr")
    path.write_text("{}\n")
    monkeypatch.setattr(act, "datetime", _FrozenClock(path.name))
    with pytest.raises(FileExistsError, match="refusing to reuse"):
        act.claude_log_path(tmp_path, "review-pr")


class _FrozenClock:
    """Pins the timestamp so the collision under test is deterministic.

    Without this the test would depend on two calls landing in the same second,
    which is exactly the flakiness the guard exists to make impossible.
    """

    def __init__(self, filename: str) -> None:
        self._stamp = filename.removeprefix("review-pr-").removesuffix(".jsonl")

    def now(self):
        return self

    def strftime(self, _fmt: str) -> str:
        return self._stamp


def test_a_fresh_path_is_returned_when_nothing_is_there(tmp_path: Path) -> None:
    """Negative control: the guard must not refuse every allocation."""
    path = act.claude_log_path(tmp_path, "review-pr")
    assert not path.exists()
    assert path.parent == tmp_path / ".claude" / "logs"


# ---------------------------------------------------------------------------
# The bash half, extracted from the shipped script and executed.
# ---------------------------------------------------------------------------

_ASSISTANT_FILTER = re.compile(
    r'''final_result=\$\(jq -rs '(\[ \.\[\].*?)'\s''', re.DOTALL)
_RESULT_FILTER = re.compile(
    r'''final_result=\$\(jq -r '(select\(\.type == "result"\).*?)'\s''', re.DOTALL)


def _jq(program: str, log: Path, *, slurp: bool = False) -> str:
    out = subprocess.run(["jq", "-rs" if slurp else "-r", program, str(log)],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout


def _shipped_assistant_filter() -> str:
    m = _ASSISTANT_FILTER.search(RUN_CLAUDE.read_text())
    assert m, "run-claude.sh no longer carries an assistant-text completion filter"
    return m.group(1)


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq is a hard dependency of the fleet")
def test_the_shipped_assistant_filter_finds_the_completion_signal() -> None:
    """The schema-declared branch of the completion gate, run as shipped."""
    assert "VERDICT: MERGE" in _jq(_shipped_assistant_filter(), FIXTURE, slurp=True)


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq is a hard dependency of the fleet")
def test_the_shipped_result_filter_would_have_MISSED_it() -> None:
    """The negative control, and it is the whole finding.

    This is the branch V1 still uses, run against a schema-declaring log. It
    must come back WITHOUT the completion signal — if it ever starts finding
    one, the CLI changed its `.result` behaviour and the branch above is no
    longer needed. Either way this test is the thing that says so.
    """
    source = RUN_CLAUDE.read_text()
    m = _RESULT_FILTER.search(source)
    assert m, "run-claude.sh no longer carries a .result completion filter"
    assert "VERDICT: MERGE" not in _jq(m.group(1), FIXTURE)


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
    out = _jq(_shipped_assistant_filter(), log, slurp=True)
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
    assert "VERDICT: MERGE" not in _jq(_shipped_assistant_filter(), log, slurp=True)


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

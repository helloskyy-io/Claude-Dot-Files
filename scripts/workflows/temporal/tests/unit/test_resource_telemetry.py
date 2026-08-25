"""Resource accounting: the numbers are real, THERE IS NO CEILING, gaps are countable.

Guards the mechanism added after 2026-08-10, when a 31 GiB host livelocked under
two dispatches and three sessions. The outage was recoverable; the absence of
evidence was not — no OOM report meant nobody could establish what held the
memory, and three sessions argued for hours from inference.

**THE ATTRIBUTION OF THAT OUTAGE TO A SUB-AGENT FAN-OUT IS RETRACTED, AND ITS
CAUSE REMAINS UNIDENTIFIED.** Sub-agents run in-process, so the per-process
arithmetic behind the original case was counting processes that do not exist.
Every ceiling was reverted at `6725111`; `resource_limits` holds one lowercase
key, so `wrap()` emits no systemd property at all. This docstring previously
described a fan-out ceiling as a live mechanism, and a cap believed-in but absent
is worse than none because nobody looks for it.

So the tests here are about the OBSERVABILITY holding, and about the ABSENCE of a
cap staying true: an unmeasured run must stay countable, a peak must not be
silently zero, the sub-agent counter must count the tool the CLI actually emits,
and `test_wrap_creates_a_scope_and_applies_no_ceiling` fails in both directions —
if the scope or slice is dropped, and if a ceiling silently reappears.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import yaml

from modules.assistant import resource_telemetry as rt

REPO_ROOT = Path(__file__).resolve().parents[5]
CONFIG = REPO_ROOT / "config.yaml"
GUARD_MD = REPO_ROOT / "scripts/workflows/temporal/modules/assistant/prompts/headless_execution_guard.md"
GUARD_SH = REPO_ROOT / "scripts/workflows/common/shared-prompts.sh"


def _limits() -> dict:
    return yaml.safe_load(CONFIG.read_text())["resource_limits"]


# --- 1. The sub-agent counter counts the tool the CLI actually emits ----------
#
# THIS SECTION HEADER USED TO READ "the fan-out ceiling is ONE number, in three
# places that must agree" AND HAD NO TESTS UNDER IT — the ceiling it named was
# reverted at `6725111` and the section was left as an empty promise. What
# belongs here is the property that replaced it: the counter this module's own
# docstring calls half of its purpose has to be able to move.

def test_the_subagent_counter_matches_the_tool_the_CLI_SPAWNS(tmp_path: Path) -> None:
    """`Agent`, not `Task`, and the miss was total rather than partial.

    Measured 2026-08-11 over the 153-log archive: 272 `"name":"Agent"`
    invocations, ZERO `"name":"Task"`, and `subagents_spawned` sitting at 0 on 13
    of 13 emitted records. That is not "no run spawned a sub-agent" — it is the
    same defect as printing "0 throttling events" where no threshold exists, on
    the field that answers whether footprint is driven by sub-agent COUNT or by
    content VOLUME.

    BOTH SPELLINGS ARE ASSERTED. The CLI renamed the tool; dropping the old name
    would silently re-lose every archived run at the next rename.
    """
    log = tmp_path / "run.jsonl"
    log.write_text(
        '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Agent"}]}}\n'
        '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Task"}]}}\n'
        '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Bash"}]}}\n'
    )
    _, spawned = rt.from_log(log)
    assert spawned == 2, (
        "the sub-agent counter missed a spawn. If it read 0, the pattern is "
        "matching a tool name the CLI does not emit — which is what shipped."
    )


def test_a_run_with_no_subagents_reports_zero_rather_than_None(tmp_path: Path) -> None:
    """The FLOOR half of the bound above.

    A counter that can only ever return 0 passes the test above trivially if that
    test is the only one; this is the other side — a genuine zero must still be a
    zero, so the pair discriminates "counted none" from "could not count".
    """
    log = tmp_path / "run.jsonl"
    log.write_text(
        '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Bash"}]}}\n'
    )
    _, spawned = rt.from_log(log)
    assert spawned == 0


# --- 2. Measurement produces REAL numbers, not plausible zeros ----------------

@pytest.mark.skipif(not rt.scope_available()[0], reason="no user scope available here")
def test_a_scoped_child_reports_memory_it_actually_allocated() -> None:
    """End-to-end against the kernel, with a child that allocates a KNOWN amount.

    ASYMMETRIC ON PURPOSE: the child allocates ~64 MiB and the assertion floor
    is 16 MiB. A test that asserted "peak > 0" would pass on an interpreter that
    allocated nothing, which is exactly the failure this guards — a report full
    of zeros looks identical to a report that was never taken.
    """
    # HOLDS the allocation for longer than two sample intervals, deliberately.
    # `peak_anon` has no kernel high-water mark and is only as good as the
    # sampling, so a child that allocates and exits inside one tick can be
    # missed entirely. An earlier version of this test did exactly that and
    # passed on timing — a green result that proved nothing.
    argv = ["python3", "-c",
            "import time; x = bytearray(64 * 1024 * 1024); "
            "x[::4096] = b'\\x01' * len(x[::4096]); "
            f"time.sleep({rt.SAMPLE_INTERVAL_S * 2.5})"]
    unit = f"claude-test-{id(argv)}.scope"
    wrapped = rt.wrap(argv, unit=unit, limits=_limits())
    proc = subprocess.Popen(wrapped, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    sampler = rt.measure(proc, unit=unit)
    proc.wait()
    report = rt.finish(sampler, limits=_limits())

    assert report.measured, f"scope produced no samples: {report.unmeasured_reason}"
    assert sampler is not None and sampler.cgroup.name == unit, (
        f"sampled {sampler.cgroup if sampler else None}, which is not the scope we "
        "created — this is the migration race, and it reads the PARENT session"
    )
    assert report.peak_anon and report.peak_anon > 16 * 1024 * 1024, (
        f"peak_anon {report.peak_anon} is below the 16 MiB floor for a child that "
        "allocated 64 MiB — the sampler is not seeing real memory"
    )
    # THE CEILING IS THE HALF THAT WAS MISSING, and its absence shipped a bug.
    # A floor catches "measured nothing". Only a ceiling catches "measured
    # EVERYTHING" — the first version read the caller's own session cgroup and
    # sailed past a 16 MiB floor on numbers in the gigabytes, reporting three
    # different children at an identical 21525 MiB. Plausible wrong numbers are
    # worse than none, and one-sided assertions cannot see them.
    assert report.peak_anon < 512 * 1024 * 1024, (
        f"peak_anon {report.peak_anon} is far above what a 64 MiB child can use — "
        "this is the session cgroup, not the child's scope"
    )
    assert report.pids_peak and 1 <= report.pids_peak < 50, (
        f"pids_peak {report.pids_peak} is not a plausible task count for one "
        "python child — a number in the hundreds means the whole session"
    )


def test_an_unmeasured_run_is_recorded_rather_than_dropped() -> None:
    """"No data" and "data showing nothing" are different facts.

    If an unmeasured run produced an empty report indistinguishable from a quiet
    one, the size of the blind spot would itself be invisible — and the incident
    that created this module was precisely a blind spot nobody could measure.
    """
    report = rt.finish(None, limits={}, unmeasured_reason="no session bus")
    assert report.measured is False
    assert report.unmeasured_reason == "no session bus"
    assert report.peak_anon is None, "an unmeasured run must not report a number"


def test_scope_availability_states_a_reason_when_false() -> None:
    ok, reason = rt.scope_available()
    assert ok or reason, "an unavailable scope must say why, or the gap is unexplainable"


# --- 3. The wrapper composes the flags it claims to ---------------------------

def test_wrap_creates_a_scope_and_applies_no_ceiling() -> None:
    """Measurement needs the scope; it does not need a limit.

    The scope is what makes the kernel account for the child. Limits were
    reverted 2026-08-10 after the outage that justified them was attributed
    elsewhere — so this asserts the scope exists AND that nothing is being
    capped, because a limit reappearing silently is the thing to catch.
    """
    argv = rt.wrap(["true"], unit="u.scope", limits=_limits())
    assert argv[0] == "systemd-run" and "--scope" in argv
    assert "--slice" in argv and _limits()["slice"] in argv, (
        "children must share a slice so a future aggregate cap has an anchor"
    )
    assert not any(a.startswith(("Memory", "Tasks", "CPU")) for a in argv), (
        f"a resource ceiling has reappeared in {argv} — this is measurement-only "
        "until the real cause of the 2026-08-10 outage is identified"
    )
    assert argv[-1] == "true" and "--" in argv


def test_wrap_omits_flags_that_are_not_configured() -> None:
    """An absent limit is unbounded, never a silently invented default."""
    argv = rt.wrap(["true"], unit="u.scope", limits={"MemoryMax": "1G"})
    assert "MemoryMax=1G" in " ".join(argv)
    assert "MemoryHigh" not in " ".join(argv)
    assert "--slice" not in argv



# --- 3c. Records are identifiable and orderable -------------------------------

def test_every_record_carries_identity_and_time() -> None:
    """A rate over a population needs records that can be told apart and ordered.

    Shipped without these and caught in review the same day. The omission is
    invisible at the single-record level — one report looks complete — and
    makes every AGGREGATE reading unsound, which is the only reading this data
    exists for.
    """
    r = rt.finish(None, limits={}, unmeasured_reason="x", invocation_id="abc", model_key="review-pr")
    # THE PARAMETER IS `invocation_id`, THE FIELD IS `run_id`, AND THAT SEAM IS
    # DELIBERATE (Phase 9 r1): the field name is written straight into
    # `.claude/logs/*.jsonl` by `asdict`, where three replay readers read it
    # out of records that already exist. Asserting across the seam is what
    # keeps both halves honest.
    assert r.run_id == "abc" and r.model_key == "review-pr"
    assert r.started_at and r.ended_at, "a record with no time cannot be ordered"
    from datetime import datetime
    for stamp in (r.started_at, r.ended_at):
        parsed = datetime.fromisoformat(stamp)
        assert parsed.tzinfo is not None, (
            f"{stamp} is timezone-naive — compared across hosts or a DST boundary "
            "it orders records wrongly and silently"
        )


def test_an_unmeasured_record_is_still_attributable() -> None:
    """The blind spot must be breakable down by workflow, not just countable."""
    r = rt.finish(None, limits={}, unmeasured_reason="no session bus", model_key="research")
    assert r.measured is False and r.model_key == "research" and r.started_at


# --- 4. Log-derived fields survive the run that matters most ------------------

def test_tool_result_bytes_and_subagents_are_counted(tmp_path: Path) -> None:
    log = tmp_path / "run.jsonl"
    log.write_text(
        '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Task"}]}}\n'
        '{"type":"user","message":{"content":[{"type":"tool_result","content":"' + "x" * 500 + '"}]}}\n'
        '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Task"}]}}\n'
    )
    total, spawned = rt.from_log(log)
    assert spawned == 2, f"expected 2 Task calls, got {spawned}"
    assert total and total >= 500, f"expected >=500 tool-result bytes, got {total}"


def test_a_truncated_log_still_yields_numbers(tmp_path: Path) -> None:
    """A KILLED run writes a half-line, and that is the run worth measuring.

    If a malformed final line aborted parsing, the runs whose numbers matter
    most — the ones that hit the cap — would be exactly the ones reporting
    nothing.
    """
    log = tmp_path / "run.jsonl"
    log.write_text(
        '{"type":"user","message":{"content":[{"type":"tool_result","content":"' + "y" * 300 + '"}]}}\n'
        '{"type":"assistant","message":{"content":[{"type":"tool_u'
    )
    total, spawned = rt.from_log(log)
    assert total and total >= 300, "a truncated tail discarded the valid lines before it"
    assert spawned == 0


def test_a_missing_log_reports_unknown_rather_than_zero(tmp_path: Path) -> None:
    """Zero bytes read and no log to read are different, and 0 would lie."""
    assert rt.from_log(tmp_path / "absent.jsonl") == (None, None)


# --- 5. The human line never claims numbers it does not have ------------------

def test_human_line_says_so_when_unmeasured() -> None:
    line = rt.human(rt.finish(None, limits={}, unmeasured_reason="no session bus"))
    assert "NOT MEASURED" in line and "no session bus" in line


def test_human_line_renders_every_magnitude_including_gigabytes() -> None:
    """A formatter that zeroes the largest values hides exactly the runs that matter.

    The first version divided by a bound rather than a divisor, with `inf` as
    the last bound — so every value >= 1 GiB printed "0.00GiB". It concealed a
    12.89 GiB build-draft peak, the largest measurement in the fleet, at the
    moment that number was the most interesting thing on the page.
    """
    cases = {512: "512B", 300_000: "293KiB", 628_500_000: "599.4MiB",
             13_841_739_776: "12.89GiB"}
    for value, expected in cases.items():
        line = rt.human(rt.ResourceReport(measured=True, peak_anon=value))
        assert expected in line, f"{value} rendered as {line!r}, expected {expected}"
    # and the specific regression: no magnitude may render as zero
    for value in (1073741824, 13_841_739_776, 99_000_000_000):
        line = rt.human(rt.ResourceReport(measured=True, peak_anon=value))
        assert "0.00GiB" not in line, f"{value} zeroed out: {line!r}"


def test_human_line_surfaces_throttling_as_a_warning() -> None:
    report = rt.ResourceReport(measured=True, peak_anon=1048576, high_events=3)
    assert "⚠" in rt.human(report) and "throttled 3x" in rt.human(report)

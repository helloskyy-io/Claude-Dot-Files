"""Resource accounting: the numbers are real, the ceiling is one number, gaps are countable.

Guards the mechanism added after 2026-08-10, when a 31 GiB host livelocked under
two dispatches and three sessions. The outage was recoverable; the absence of
evidence was not — no OOM report meant nobody could establish what held the
memory, and three sessions argued for hours from inference.

So the tests here are mostly about the OBSERVABILITY holding, not the cap: an
unmeasured run must stay countable, a peak must not be silently zero, and the
fan-out ceiling must exist in exactly one value even though prompts carry it as
literal text.
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


# --- 1. The fan-out ceiling is ONE number, in three places that must agree ----

def test_the_ceiling_is_configured() -> None:
    """Vacuity guard: every check below reads this key."""
    limits = _limits()
    ceiling = limits.get("max_parallel_agents")
    assert isinstance(ceiling, int) and 1 <= ceiling <= 16, (
        f"max_parallel_agents must be a small positive int, got {ceiling!r}"
    )


@pytest.mark.parametrize("path", [GUARD_MD, GUARD_SH], ids=["python-fleet", "bash-fleet"])
def test_both_fleets_state_the_configured_ceiling(path: Path) -> None:
    """Prompts carry the number LITERALLY, because a prompt is text and cannot
    read config. That makes drift possible, so this test is the binding.

    Both fleets are checked: an earlier turn-cap migration found the bash half
    free to drift back to a literal while the Python half stayed correct, and
    the two would have disagreed with both suites green.
    """
    ceiling = _limits()["max_parallel_agents"]
    text = path.read_text()
    assert f"NEVER dispatch more than {ceiling} sub-agents concurrently" in text, (
        f"{path.name} does not state the configured ceiling of {ceiling}. "
        "config.yaml and the prompts must agree — update both or neither."
    )


def test_the_two_shared_prompt_copies_are_identical() -> None:
    """One contract, two files. They are mirrors and must stay so."""
    block = re.search(r"- \*\*NEVER dispatch more than \d+ sub-agents.*?rests on\.",
                      GUARD_MD.read_text(), re.S)
    assert block, "the ceiling block is missing from the Python-fleet guard"
    assert block.group(0) in GUARD_SH.read_text(), (
        "the bash-fleet copy has drifted from the Python-fleet copy"
    )


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

def test_wrap_applies_every_configured_limit_and_the_shared_slice() -> None:
    argv = rt.wrap(["true"], unit="u.scope", limits=_limits())
    joined = " ".join(argv)
    for key in ("MemoryHigh", "MemoryMax", "TasksMax"):
        assert f"{key}={_limits()[key]}" in joined, f"{key} was not applied"
    assert "--slice" in argv and _limits()["slice"] in argv, (
        "children must join the SHARED slice — per-dispatch caps do not compose "
        "across sessions, which is how the 2026-08-10 host was lost"
    )
    assert argv[-1] == "true" and "--" in argv, "the wrapped command must survive intact"


def test_wrap_omits_flags_that_are_not_configured() -> None:
    """An absent limit is unbounded, never a silently invented default."""
    argv = rt.wrap(["true"], unit="u.scope", limits={"MemoryMax": "1G"})
    assert "MemoryMax=1G" in " ".join(argv)
    assert "MemoryHigh" not in " ".join(argv)
    assert "--slice" not in argv


# --- 3b. The cap KILLS. Presence of a flag is not enforcement -----------------

@pytest.mark.skipif(not rt.scope_available()[0], reason="no user scope available here")
def test_the_configured_cap_actually_kills_an_overrunning_child() -> None:
    """MUTATION TEST, because a flag in argv is not a cap in force.

    `MemoryMax` ALONE IS DECORATIVE: cgroup v2 bounds RAM and silently spills
    the remainder to swap, so an overrunning child THRASHES instead of dying —
    reproducing in miniature the exact livelock this whole mechanism exists to
    prevent. Verified 2026-08-10: 400 MB under a 24 MB MemoryMax returned exit
    0 and printed its success; adding MemorySwapMax=0 produced exit 137.

    So this asserts the EFFECT, not the flag. Testing that the argv contains
    `MemoryMax=8G` would have passed against a cap that stops nothing, which is
    the same one-sided mistake that let the migration race ship.
    """
    limits = _limits()
    assert limits.get("MemorySwapMax") == 0, (
        "MemorySwapMax must be 0 or the cap only throttles into swap"
    )
    # The band is scaled to the SHIPPED ratio (7G/8G = 87.5%), not invented.
    # A wide band does not kill — it throttles the runaway inside the band and
    # it grinds forever, which is the livelock in miniature. Measured: under a
    # 24M Max, High=16M (67%) ran past a 25s timeout; High=21M died at once.
    assert int(str(limits["MemoryHigh"]).rstrip("G")) / int(str(limits["MemoryMax"]).rstrip("G")) >= 0.8, (
        f'MemoryHigh {limits["MemoryHigh"]} is far below MemoryMax {limits["MemoryMax"]} — '
        "that gap is a throttle band a runaway can grind in indefinitely instead of dying"
    )
    tight = {**limits, "MemoryMax": "24M", "MemoryHigh": "21M"}
    argv = rt.wrap(
        ["python3", "-c", "x = bytearray(400 * 1024 * 1024); "
                          "x[::4096] = b'\\x01' * len(x[::4096]); print('ALLOCATED')"],
        unit=f"claude-captest-{id(tight)}.scope", limits=tight)
    result = subprocess.run(argv, capture_output=True, text=True, timeout=60)

    assert result.returncode != 0, (
        f"a 400 MB child survived a 24 MB cap (exit {result.returncode}) — the cap "
        f"is decorative. stdout={result.stdout!r}"
    )
    assert "ALLOCATED" not in result.stdout, "the child completed its allocation despite the cap"


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


def test_human_line_surfaces_throttling_as_a_warning() -> None:
    report = rt.ResourceReport(measured=True, peak_anon=1048576, high_events=3)
    assert "⚠" in rt.human(report) and "throttled 3x" in rt.human(report)

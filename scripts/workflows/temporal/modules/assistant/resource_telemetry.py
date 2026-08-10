"""Per-run memory and task accounting, measured by the kernel rather than estimated.

WHY THIS EXISTS. On 2026-08-10 a 31 GiB VM went from idle to unrecoverable in
seven minutes and stayed that way for hours. No OOM report was ever produced:
with several processes growing together and ~22 GiB of reclaimable page cache to
chew through first, the kernel kept reclaiming instead of selecting a victim.
That is a LIVELOCK, not a crash — the box does not die, it stops responding, and
only a hard reset ends it.

The cost of the livelock was not the outage. It was that **the evidence never
existed**: three sessions spent hours arguing about which workload held the
memory, and the honest answer was that nobody could know. A run that dies inside
a cgroup is diagnosable — the kernel names it and logs its RSS. A run that
livelocks the host leaves nothing to read.

SO THE CAP AND THE MEASUREMENT ARE ONE MECHANISM, deliberately. Putting a child
in a scope to bound it is what makes the kernel account for it, and the same
files answer both questions. Building either one gets the other free.

WHAT THIS IS FOR, and it is not primarily safety. The open question is which
knob actually governs a run's footprint: the NUMBER of subagents, or the VOLUME
of content each pulls into context. An agent's memory is its conversation, and
every tool result stays resident for the rest of the run — so a run reading five
PDFs through the shell and a run with five subagents can reach the same peak by
different routes, and the fixes are opposite. `peak_anon` alone cannot tell them
apart. That is why `tool_result_bytes` and `subagents_spawned` are recorded
beside it: across enough runs the question stops being an argument and becomes a
regression.

SIZE ON `anon`, NOT ON `memory.peak`. `memory.peak` includes page cache, which
is reclaimable and does not pressure a host the way anonymous memory does. A
research child reading many files inflates the total while costing the machine
comparatively little. Sizing fan-out off the total silently undersizes it.

MEASUREMENT MAY BE ABSENT, AND THAT IS RECORDED RATHER THAN SKIPPED. A user
scope needs a session D-Bus, which a headless cron context may not have. When it
is unavailable the child still runs and `measured: false` is written with the
reason — an unmeasured run must be COUNTABLE, because "we have no data" and "we
have data showing nothing happened" are different facts and collapsing them is
how a gap becomes invisible.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Sampling interval. `memory.peak` and `pids.peak` are monotonic so the cadence
# does not affect them, but `anon` has no kernel-maintained high-water mark and
# is only as good as the sampling — a slow tick misses a spike that a fast one
# catches. Two seconds costs a handful of small reads per minute against runs
# that last tens of minutes.
SAMPLE_INTERVAL_S = 2.0

# LIMITATION, stated because it is invisible otherwise: `peak_total` and
# `pids_peak` are kernel-maintained high-water marks and are exact regardless of
# cadence. `peak_anon` is NOT — the kernel keeps no anon high-water mark, so it
# is only as good as the sampling, and a child living less than one interval can
# report a low or absent peak. Real dispatches run for minutes, so this is
# immaterial in production; it matters when reading short runs, where a low
# `peak_anon` beside a large `peak_total` may be undersampling rather than a
# genuinely cache-heavy run.


@dataclass
class ResourceReport:
    """One run's resource facts. Every field is nullable when unmeasured."""

    measured: bool = False
    unmeasured_reason: str | None = None

    # Kernel-accounted, from the scope's cgroup.
    peak_anon: int | None = None        # bytes — the number to size fan-out on
    peak_total: int | None = None       # bytes — includes reclaimable page cache
    mean_total: int | None = None       # bytes — mean of the samples
    pids_peak: int | None = None        # max tasks; the second axis alongside memory
    high_events: int | None = None      # times MemoryHigh throttled — the EARLY WARNING
    oom_kills: int | None = None        # times MemoryMax killed something

    # Derived from the run's own stream log.
    tool_result_bytes: int | None = None   # content volume pulled into context
    subagents_spawned: int | None = None   # Task invocations — NOT concurrency, see below

    samples: int = 0
    limits: dict = field(default_factory=dict)


def _read_int(path: Path) -> int | None:
    try:
        return int(path.read_text().strip())
    except (OSError, ValueError):
        return None


def _read_anon(cgroup: Path) -> int | None:
    """Anonymous memory from `memory.stat` — the non-reclaimable part."""
    try:
        for line in (cgroup / "memory.stat").read_text().splitlines():
            if line.startswith("anon "):
                return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        return None
    return None


def _read_events(cgroup: Path) -> tuple[int | None, int | None]:
    """(high, oom_kill) from `memory.events`."""
    high = oom = None
    try:
        for line in (cgroup / "memory.events").read_text().splitlines():
            key, _, value = line.partition(" ")
            if key == "high":
                high = int(value)
            elif key == "oom_kill":
                oom = int(value)
    except (OSError, ValueError):
        pass
    return high, oom


def cgroup_of(pid: int) -> Path | None:
    """The cgroup v2 path for `pid`, or None if it cannot be resolved.

    Read from the process rather than composed from a unit name: the
    user.slice/user@UID.service/app.slice prefix is not guaranteed stable across
    systemd versions or delegation setups, and a composed path that silently
    misses produces a measured-looking run with no numbers in it.
    """
    try:
        for line in Path(f"/proc/{pid}/cgroup").read_text().splitlines():
            if line.startswith("0::"):
                rel = line[3:].strip()
                path = Path("/sys/fs/cgroup") / rel.lstrip("/")
                return path if path.is_dir() else None
    except OSError:
        return None
    return None


class _Sampler(threading.Thread):
    """Polls a cgroup until it disappears, keeping the last good reading.

    THE TEARDOWN RACE IS WHY THIS KEEPS LAST-GOOD RATHER THAN READING AT EXIT.
    The scope's cgroup is removed the moment the process exits, so a single read
    after `wait()` returns finds nothing. Because `memory.peak` and `pids.peak`
    are monotonic, the final successful sample IS the run's peak — no separate
    end-of-run read is needed, and none would be reliable.
    """

    def __init__(self, cgroup: Path) -> None:
        super().__init__(daemon=True)
        self.cgroup = cgroup
        self.stop_flag = threading.Event()
        self.peak_anon = 0
        self.peak_total: int | None = None
        self.pids_peak: int | None = None
        self.high: int | None = None
        self.oom: int | None = None
        self._total_sum = 0
        self.samples = 0

    def run(self) -> None:
        while not self.stop_flag.is_set():
            if not self.cgroup.is_dir():
                break
            anon = _read_anon(self.cgroup)
            current = _read_int(self.cgroup / "memory.current")
            if anon is not None:
                self.peak_anon = max(self.peak_anon, anon)
            if current is not None:
                self._total_sum += current
                self.samples += 1
            for attr, name in (("peak_total", "memory.peak"), ("pids_peak", "pids.peak")):
                value = _read_int(self.cgroup / name)
                if value is not None:
                    setattr(self, attr, value)
            high, oom = _read_events(self.cgroup)
            if high is not None:
                self.high = high
            if oom is not None:
                self.oom = oom
            self.stop_flag.wait(SAMPLE_INTERVAL_S)

    @property
    def mean_total(self) -> int | None:
        return self._total_sum // self.samples if self.samples else None


def scope_available() -> tuple[bool, str | None]:
    """Whether a user scope can be created here. Returns (ok, reason_if_not)."""
    if not shutil.which("systemd-run"):
        return False, "systemd-run not on PATH"
    if not Path("/sys/fs/cgroup/cgroup.controllers").exists():
        return False, "cgroup v2 not mounted"
    # A --user scope talks to the session bus; a headless cron context often has
    # neither. Checked explicitly because the failure is otherwise a confusing
    # D-Bus error from inside the dispatch.
    if not (os.environ.get("XDG_RUNTIME_DIR") or os.environ.get("DBUS_SESSION_BUS_ADDRESS")):
        return False, "no user session bus (XDG_RUNTIME_DIR/DBUS_SESSION_BUS_ADDRESS unset)"
    return True, None


def wrap(argv: list[str], *, unit: str, limits: dict) -> list[str]:
    """`argv` wrapped in a transient user scope carrying `limits`.

    The scope joins a SHARED SLICE. Per-dispatch caps do not compose: three
    sessions each running a correctly-capped 8 GiB child still sum past a 31 GiB
    box, which is exactly how the 2026-08-10 incident happened — two dispatches
    and three interactive sessions, each individually reasonable. A slice cap
    bounds the TOTAL regardless of how many sessions fire, so the ceiling is a
    property of the host rather than of anyone's discipline.
    """
    args = ["systemd-run", "--user", "--scope", "-q", "--unit", unit]
    if slice_name := limits.get("slice"):
        args += ["--slice", slice_name]
    # EVERY systemd property in the map, not a hardcoded list. A fixed tuple
    # silently drops a limit somebody added to config and believes is in force
    # -- and a cap believed-in but absent is worse than none, because nobody
    # looks for it. `MemorySwapMax` was exactly that: added to config and
    # dropped here, it would have left the cap decorative while reading as set.
    # Keys are systemd property names (CamelCase); ours are lowercase.
    for key, value in limits.items():
        if key[:1].isupper() and value is not None:
            args += ["-p", f"{key}={value}"]
    return [*args, "--", *argv]


# How long to wait for systemd to migrate the child into its scope.
MIGRATION_TIMEOUT_S = 5.0


def measure(proc: subprocess.Popen, *, unit: str) -> _Sampler | None:
    """Start sampling `proc`'s scope once it is IN the scope. None if it never is.

    THE MIGRATION RACE, AND IT SHIPPED WRONG ONCE. `systemd-run --user --scope`
    returns before systemd has moved the process into the new cgroup — measured
    here at roughly one second. Reading `/proc/PID/cgroup` immediately therefore
    resolves the PARENT: the caller's own session scope.

    That is not a small error, it is the worst possible one. It does not fail —
    it returns large, plausible numbers for the whole session, identical across
    every child, and they look like measurements. The first shipped run reported
    three different children at exactly 21525 MiB and 1199 tasks, which was the
    editor session, and the only reason it was caught is that three identical
    totals are obviously impossible.

    So this waits for the child to appear in the cgroup NAMED `unit`, and
    returns None rather than measuring whatever it happens to find. An unmeasured
    run is recorded with its reason; a run measured against the wrong cgroup
    silently poisons every number derived from it afterwards.
    """
    deadline = time.monotonic() + MIGRATION_TIMEOUT_S
    while time.monotonic() < deadline:
        cgroup = cgroup_of(proc.pid)
        if cgroup is not None and cgroup.name == unit:
            sampler = _Sampler(cgroup)
            sampler.start()
            return sampler
        if proc.poll() is not None:
            return None            # exited before it was ever measurable
        time.sleep(0.05)
    return None


def finish(sampler: _Sampler | None, *, limits: dict,
           unmeasured_reason: str | None = None) -> ResourceReport:
    if sampler is None:
        return ResourceReport(
            measured=False,
            unmeasured_reason=unmeasured_reason or "cgroup could not be resolved for the child",
            limits=limits,
        )
    sampler.stop_flag.set()
    sampler.join(timeout=SAMPLE_INTERVAL_S * 2)
    return ResourceReport(
        measured=sampler.samples > 0,
        unmeasured_reason=None if sampler.samples else "cgroup vanished before the first sample",
        peak_anon=sampler.peak_anon or None,
        peak_total=sampler.peak_total,
        mean_total=sampler.mean_total,
        pids_peak=sampler.pids_peak,
        high_events=sampler.high,
        oom_kills=sampler.oom,
        samples=sampler.samples,
        limits=limits,
    )


# `Task` is the subagent-spawning tool. Counted from the log because the cgroup
# cannot distinguish a subagent's processes from the parent's.
_TASK_CALL = re.compile(r'"name"\s*:\s*"Task"')


def from_log(log_file: Path) -> tuple[int | None, int | None]:
    """(tool_result_bytes, subagents_spawned) parsed from the run's stream log.

    `subagents_spawned` IS NOT CONCURRENCY and must not be read as it. It counts
    Task invocations over the whole run; five sequential subagents and five
    simultaneous ones produce the same number. `pids_peak` is the concurrency
    signal, and it comes from the kernel. Naming this `max_concurrent` would
    have asserted a measurement nothing here performs.
    """
    if not log_file.is_file():
        return None, None
    total = spawned = 0
    try:
        with log_file.open(errors="replace") as fh:
            for line in fh:
                spawned += len(_TASK_CALL.findall(line))
                if '"tool_result"' not in line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    # A truncated final line is normal for a killed run — the
                    # whole point is to still get numbers out of one.
                    continue
                total += _tool_result_bytes(event)
    except OSError:
        return None, None
    return total, spawned


def _tool_result_bytes(event: object) -> int:
    """Bytes of `tool_result` content anywhere in a decoded stream event."""
    if isinstance(event, dict):
        if event.get("type") == "tool_result":
            content = event.get("content")
            return len(content) if isinstance(content, str) else len(json.dumps(content or ""))
        return sum(_tool_result_bytes(v) for v in event.values())
    if isinstance(event, list):
        return sum(_tool_result_bytes(v) for v in event)
    return 0


def report_dict(report: ResourceReport) -> dict:
    return asdict(report)


def human(report: ResourceReport) -> str:
    """One line for the operator, printed at the end of a run."""
    if not report.measured:
        return f"resources: NOT MEASURED ({report.unmeasured_reason})"
    def mib(n: int | None) -> str:
        """Adaptive, because rounding 284 KiB to '0MiB' misreports the one field
        whose entire job is comparing content volume across runs."""
        if not n:
            return "0" if n == 0 else "?"
        for limit, unit, places in ((1024, "B", 0), (1048576, "KiB", 0),
                                    (1073741824, "MiB", 1), (float("inf"), "GiB", 2)):
            if n < limit:
                return f"{n / (limit / 1024):.{places}f}{unit}"
        return f"{n}B"
    warn = ""
    if report.high_events:
        warn = f"  ⚠ throttled {report.high_events}x at MemoryHigh"
    if report.oom_kills:
        warn += f"  ⚠ {report.oom_kills} OOM KILL(S)"
    return (f"resources: anon {mib(report.peak_anon)} peak · total {mib(report.peak_total)} peak "
            f"/ {mib(report.mean_total)} mean · {report.pids_peak} tasks · "
            f"{mib(report.tool_result_bytes)} tool results · "
            f"{report.subagents_spawned} subagents{warn}")

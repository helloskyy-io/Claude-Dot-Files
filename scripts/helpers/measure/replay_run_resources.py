#!/usr/bin/env python3
"""Replay the `run_resources` events in the run log and produce four figures.

WHY THIS EXISTS. `run_resources` shipped on 2026-08-10 with no reader and no
placed candidate, which is the admission failure
`phase6_read_what_it_writes.md` § 4 Clause B was written to stop: an observable
ships with its reader in the same change, or with a placed candidate carrying a
named trigger, and there is no third option. This is the reader. The alternative
arm — deleting the emission — loses because the instrument was built for a
livelock that produced NO EVIDENCE AT ALL, and deleting it restores the state
where nobody can establish what held the memory.

EVERY FIGURE CARRIES ITS DENOMINATOR AND NAMES ITS EXCLUSIONS, which is
`README.md`'s standing rule for this directory and is the reason it is worth
re-running rather than quoting. Three of the four figures have a denominator that
starts at a named commit, because the record's shape changed underneath them.

WHAT IT DELIBERATELY DOES NOT PRINT. The run log is CO-RESIDENT with the CLI's
own transcript, so this emits derived figures, `run_id`s and log file names, and
never a value whose text came from the model or a tool. `run_log.assert_publishable`
enforces it on the row about to be printed rather than in a docstring.

IT PINS NOTHING AND IMPORTS NO PREDICATE. Per `README.md`'s discriminator — pin
when the number must stay reproducible, import when the rule must be the one that
ships — this reports facts about archived runs rather than validating a candidate
rule, so it reads the log format and executes nothing from the fleet.

Usage:  python3 scripts/helpers/measure/replay_run_resources.py [LOG_DIR]
"""

from __future__ import annotations

import importlib.util
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _run_log():
    """`run_log.py` by path, so this tool needs no package context."""
    spec = importlib.util.spec_from_file_location("_run_log", _HERE / "run_log.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["_run_log"] = module
    spec.loader.exec_module(module)
    return module


rl = _run_log()

GIB = 1024 ** 3
MIB = 1024 ** 2


def gib(n: int | None) -> str:
    return "?" if n is None else f"{n / GIB:.3f}G"


# --- classification ----------------------------------------------------------

def classify(path: Path, event: dict, by_model: dict) -> dict:
    """One record plus everything a figure needs to decide whether to count it.

    THE EXCLUSIONS ARE DERIVED FROM A STATED CUTOVER, NOT FROM THE NUMBERS. A
    record measured before `a623c25` sampled the CALLER'S SESSION SCOPE rather
    than the child's, so it is not this fleet's telemetry at all — it is the
    editor session, and it is large and plausible. Excluding it because the
    number looks wrong would be exactly the reasoning that shipped it; excluding
    it because the code that wrote it was known-wrong is a fact about the tree.
    """
    session_scope = rl.before(path, "child_scope_measured")
    workflow = event.get("workflow_key")
    source = "payload workflow_key"
    if not workflow:
        model = event.get("model_key") or rl.model_key_of(path)
        candidates = by_model.get(model or "", [])
        if len(candidates) == 1:
            workflow, source = candidates[0], f"inferred from model_key {model!r}"
        else:
            workflow, source = None, (
                f"AMBIGUOUS — model_key {model!r} maps to {candidates or 'nothing'}"
            )
    limits = event.get("limits") or {}
    row = {
        "log": path.name,
        "run_id": event.get("run_id"),
        "workflow": workflow,
        "workflow_source": source,
        "session_scope_suspect": session_scope,
        "measured": bool(event.get("measured")),
        "unmeasured_reason": event.get("unmeasured_reason"),
        "peak_anon": event.get("peak_anon"),
        "peak_total": event.get("peak_total"),
        "mean_total": event.get("mean_total"),
        "pids_peak": event.get("pids_peak"),
        "tool_result_bytes": event.get("tool_result_bytes"),
        "subagents_emitted": event.get("subagents_spawned"),
        "subagents_recomputed": rl.subagents_in(path),
        "started_at": event.get("started_at"),
        "ended_at": event.get("ended_at"),
        "samples": event.get("samples"),
        # `high_events`/`oom_kills` count crossings of thresholds that may not
        # exist. Applicability is per-record because the archive spans a period
        # when they DID exist: `limits` on a 2026-08-10 record carries
        # MemoryHigh=4G and MemoryMax=8G, and on a later one carries only the
        # slice. Reporting "0 throttling events" across both states says
        # NOTHING WAS THROTTLED when the truth for most of the corpus is that
        # no threshold existed to throttle against.
        "high_applicable": "MemoryHigh" in limits,
        "oom_applicable": "MemoryMax" in limits,
        "high_events": event.get("high_events"),
        "oom_kills": event.get("oom_kills"),
    }
    # CHECKED WHERE THE ROW IS BUILT, which is where both sibling readers check
    # it. An earlier version smuggled the raw event forward under a `_event` key
    # for `report()` to pop — so the un-redacted payload rode inside the rows
    # list, and a `--json` dump added later by copying `replay_convergence_
    # predicate.py`'s shape would have serialised it verbatim. The row is the
    # output; nothing else needs to travel with it.
    rl.assert_publishable("run_resources", event, row)
    return row


def _overlaps(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Peak concurrent footprint over runs whose wall-clock windows intersect.

    THE FIGURE THE 2026-08-10 FAILURE ACTUALLY NEEDS, and the one no per-run
    record yields alone: a host dies of the SUM, and every cap that has ever
    been proposed for this fleet was a per-UNIT cap. Its denominator starts at
    `b8d7aa7`, which added the window, and is zero before it.

    Computed as a sweep over window boundaries rather than pairwise, so three
    runs overlapping at one instant are summed once rather than three times.

    Returns `(peaks, dropped)`. A window this sweep cannot place is DROPPED AND
    COUNTED rather than skipped, because a record silently missing from a sweep
    is indistinguishable from one that overlapped nothing — the same collapse
    figure 1 exists to prevent, one figure over.
    """
    windows = []
    dropped: list[dict] = []
    for r in rows:
        if not (r["started_at"] and r["ended_at"] and r["peak_anon"]):
            continue
        try:
            start = datetime.fromisoformat(r["started_at"])
            end = datetime.fromisoformat(r["ended_at"])
        except ValueError:
            dropped.append(r)
            continue
        # A DEGENERATE WINDOW BREAKS THE SWEEP, NOT JUST THE FIGURE. Boundaries
        # sort with the close before the open at an equal instant — deliberately,
        # so two runs meeting exactly at a boundary do not read as concurrent —
        # and a run whose own end is not after its own start therefore has its
        # close processed before its open, is never removed from `live`, and
        # inflates every later sum for the rest of the sweep. Unreachable today
        # (the sampler's cadence guarantees a real interval), which is why it is
        # excluded by name rather than left to be found by a wrong number.
        if end <= start:
            dropped.append(r)
            continue
        windows.append((start, end, r))
    events: list[tuple[datetime, int, dict]] = []
    for start, end, r in windows:
        events.append((start, 1, r))
        events.append((end, -1, r))
    events.sort(key=lambda e: (e[0], e[1]))
    live: list[dict] = []
    peaks: list[dict] = []
    for _, delta, r in events:
        if delta == 1:
            live.append(r)
            if len(live) > 1:
                peaks.append({
                    "concurrent": len(live),
                    # PEAKS ARE SUMMED, WHICH IS AN UPPER BOUND AND IS LABELLED
                    # AS ONE. Two runs overlapping in wall-clock time did not
                    # necessarily hit their peaks in the same second, so this
                    # over-states the true concurrent footprint. It is the
                    # honest direction for a headroom question and the report
                    # says so rather than presenting it as a measurement.
                    "summed_peak_anon": sum(x["peak_anon"] for x in live),
                    "logs": [x["log"] for x in live],
                })
        else:
            live = [x for x in live if x is not r]
    return peaks, dropped


# --- report ------------------------------------------------------------------

def report(rows: list[dict], total_logs: int, log_dir: Path) -> None:
    print("# run_resources replay — the run log's measurement record")
    print()
    print(f"Log directory              : {log_dir}")
    print(f"Logs in archive            : {total_logs}")
    print(f"Carrying a run_resources   : {len(rows)}  <- THE DENOMINATOR for figure 1")
    print(f"Emission starts at         : 0feacc3 (2026-08-10); every earlier log has none")
    print()

    suspect = [r for r in rows if r["session_scope_suspect"]]
    unplaceable = [r for r in rows if r["session_scope_suspect"] is None]
    sound = [r for r in rows if r["session_scope_suspect"] is False]
    print("## Exclusions, named rather than dropped")
    print(f"  measured the CALLER'S SESSION SCOPE (log stamped before "
          f"{rl.CUTOVERS['child_scope_measured'][0]}): {len(suspect)}")
    for r in suspect:
        print(f"    {r['log']}  pids_peak={r['pids_peak']} peak_total={gib(r['peak_total'])}")
    if suspect:
        pids = {r["pids_peak"] for r in suspect}
        totals = {r["peak_total"] for r in suspect}
        print(f"    corroboration (not the criterion): pids_peak in {sorted(pids)}, "
              f"peak_total in {[gib(t) for t in sorted(totals)]} — "
              f"{'IDENTICAL across different children, which is the signature a623c25 names' if len(totals) == 1 else 'differing, so the cutover is the only evidence here'}")
    print(f"  log name carries no stamp, so it cannot be placed either side: {len(unplaceable)}")
    print(f"  SOUND records, used by figures 2-4: {len(sound)}")
    print()

    # --- FIGURE 1 ------------------------------------------------------------
    unmeasured = [r for r in rows if not r["measured"]]
    print("## Figure 1 — the `measured: false` rate, with its reasons")
    print("   Denominator: EVERY run_resources record, including the excluded ones —")
    print("   an unmeasured run must be countable whatever else was wrong with it.")
    print(f"   unmeasured: {len(unmeasured)} of {len(rows)}"
          + (f"  ({100 * len(unmeasured) / len(rows):.1f}%)" if rows else ""))
    reasons = Counter(r["unmeasured_reason"] for r in unmeasured)
    print(f"   reasons   : {dict(reasons) or 'none — every record carries numbers'}")
    print("   (`unmeasured_reason` is a module-authored enum, so publishing it is")
    print("    inside this surface's classification; it is not transcript text.)")
    print()

    # --- FIGURE 2 ------------------------------------------------------------
    print("## Figure 2 — `peak_anon` distribution by WORKFLOW")
    ambiguous = [r for r in sound if r["workflow"] is None]
    placeable = [r for r in sound if r["workflow"] is not None]
    print(f"   Denominator: {len(placeable)} of {len(sound)} sound records.")
    print(f"   Excluded as model_key-AMBIGUOUS: {len(ambiguous)}"
          + (f" — {[r['log'] for r in ambiguous]}" if ambiguous else ""))
    from_payload = sum(1 for r in placeable if r["workflow_source"] == "payload workflow_key")
    print(f"   Attributed by payload `workflow_key`: {from_payload} of {len(placeable)};")
    print(f"   the rest are INFERRED from an unambiguous model_key. The figure is")
    print(f"   complete from the workflow-key addition forward, not before it.")
    by_workflow: dict[str, list[int]] = defaultdict(list)
    for r in placeable:
        if r["peak_anon"]:
            by_workflow[r["workflow"]].append(r["peak_anon"])
    print(f"   {'workflow':<20} {'n':>3}  {'min':>8} {'median':>8} {'max':>8}")
    for workflow, peaks in sorted(by_workflow.items()):
        print(f"   {workflow:<20} {len(peaks):>3}  {gib(min(peaks)):>8} "
              f"{gib(int(statistics.median(peaks))):>8} {gib(max(peaks)):>8}")
    print("   NO CEILING EXISTS TO CHECK THESE AGAINST — `resource_limits` holds only")
    print("   `slice`. This figure's use is establishing whether a per-workflow ceiling")
    print("   is warranted at all, not verifying one that is in force.")
    print()

    # --- FIGURE 3 ------------------------------------------------------------
    print("## Figure 3 — the knob question: subagent COUNT vs content VOLUME")
    print("   The question `resource_telemetry.py` names as its purpose. A run reading")
    print("   five PDFs and a run with five subagents can reach the same peak by")
    print("   different routes, and the fixes are opposite.")
    stale = [r for r in sound if r["subagents_emitted"] != r["subagents_recomputed"]]
    zeros = [r for r in sound if not r["subagents_emitted"]]
    print(f"   Denominator: {len(sound)} sound records.")
    print(f"   `subagents_spawned` AS EMITTED reads 0 on {len(zeros)} of {len(sound)} and")
    print(f"   UNDERCOUNTS on {len(stale)}: the emitter matched the tool name `Task` while")
    print("   this CLI spawns `Agent`, so the counter could not move at all. The column")
    print("   below is RECOMPUTED from each log's own `tool_use` blocks; the emitted value")
    print("   is shown beside it so the gap is visible rather than silently repaired.")
    print(f"   {'log':<46} {'emit':>4} {'recomp':>6} {'tool_result':>12} {'peak_anon':>10}")
    for r in sorted(sound, key=lambda x: -(x["peak_anon"] or 0)):
        print(f"   {r['log'][:46]:<46} {str(r['subagents_emitted']):>4} "
              f"{r['subagents_recomputed']:>6} "
              f"{(r['tool_result_bytes'] or 0) / MIB:>10.2f}Mi {gib(r['peak_anon']):>10}")
    spawning = [r for r in sound if r["subagents_recomputed"] > 0]
    plain = [r for r in sound if r["subagents_recomputed"] == 0]
    print(f"   runs that spawned at least one subagent: {len(spawning)} of {len(sound)}")
    if spawning and plain:
        print(f"     median peak_anon WITH subagents   : "
              f"{gib(int(statistics.median([r['peak_anon'] or 0 for r in spawning])))} "
              f"(n={len(spawning)})")
        print(f"     median peak_anon WITHOUT subagents: "
              f"{gib(int(statistics.median([r['peak_anon'] or 0 for r in plain])))} "
              f"(n={len(plain)})")
    print("   THIS IS NOT A RATE AND THIS TOOL DOES NOT QUOTE ONE. At this n the two")
    print("   medians cannot separate the two knobs; what the figure establishes today")
    print("   is that the axis EXISTS in the corpus, which it did not while the counter")
    print("   was reading zero.")
    # THE OUTLIER IS NAMED, because it is the thing a summary statistic hides
    # and because neither knob explains it. Its cause is unlocatable from this
    # record: the sampler keeps a peak and a mean out of every sample and throws
    # the series away, so a spike has no timestamp.
    #
    # COMPARED ONLY AGAINST RECORDS THAT CARRY A PEAK, and the guard is a real
    # crash rather than a tidy-up. `sound` includes `measured: false` records,
    # whose `peak_anon` is None and read as 0 here — so a corpus of one measured
    # run beside any number of unmeasured ones gave `max(others) == 0`, passed
    # the `> 4 * 0` test for any positive peak, and divided by zero on the very
    # next line. The tool died mid-report, losing figure 4 and the applicability
    # section, on precisely the corpus shape figure 1 exists to report on.
    with_peak = [r for r in sound if r["peak_anon"]]
    if with_peak:
        worst = max(with_peak, key=lambda r: r["peak_anon"])
        others = [r["peak_anon"] for r in with_peak if r is not worst]
        if others and worst["peak_anon"] > 4 * max(others):
            print(f"   OUTLIER, NAMED: {worst['log']} peaked at {gib(worst['peak_anon'])} "
                  f"with {worst['subagents_recomputed']} subagents and "
                  f"{(worst['tool_result_bytes'] or 0) / MIB:.2f}MiB of tool results —")
            print(f"   {worst['peak_anon'] / max(others):.0f}x the next highest, and NEITHER")
            print("   knob explains it. It is not locatable from this record: the sampler keeps")
            print("   a peak and a mean out of every sample and discards the series, so the")
            print("   spike has no timestamp. Carried as a candidate rather than designed")
            print("   around — see `phase6_read_what_it_writes.md`.")
    print()

    # --- FIGURE 4 ------------------------------------------------------------
    windowed = [r for r in sound if r["started_at"] and r["ended_at"]]
    peaks, undrawable = _overlaps(windowed)
    print("## Figure 4 — the AGGREGATE: summed peak of runs whose windows overlap")
    print(f"   Denominator: {len(windowed)} of {len(sound)} sound records carry a window.")
    print(f"   Zero before {rl.CUTOVERS['identity_fields'][0]}, which added "
          f"`started_at`/`ended_at`; the change is additive and no earlier record has one.")
    if undrawable:
        print(f"   NAMED AS EXCLUDED FROM THE SWEEP — a window this sweep cannot place "
              f"(unparseable, or ending at or before its own start): {len(undrawable)} of "
              f"{len(windowed)}")
        for r in undrawable:
            print(f"     {r['log']}  {r['started_at']} -> {r['ended_at']}")
    if not peaks:
        print("   NO OVERLAPPING PAIR IN THE CORPUS. That is a fact about the corpus, not")
        print("   a bound: it means every windowed run in it ran alone, so this archive")
        print("   cannot say what a concurrent fleet costs. The 2026-08-10 host died")
        print("   under two dispatches and three interactive sessions, and interactive")
        print("   sessions are outside this instrument entirely.")
    else:
        worst = max(peaks, key=lambda p: p["summed_peak_anon"])
        print(f"   overlapping intervals observed: {len(peaks)}")
        print(f"   worst: {worst['concurrent']} concurrent, summed peak_anon "
              f"{gib(worst['summed_peak_anon'])} (UPPER BOUND — peaks need not coincide)")
        for p in peaks:
            print(f"     {p['concurrent']}x  {gib(p['summed_peak_anon'])}  {p['logs']}")
    print()

    # --- the fields that cannot move ----------------------------------------
    print("## `high_events` and `oom_kills` — applicability, not zeros")
    high_na = [r for r in rows if not r["high_applicable"]]
    oom_na = [r for r in rows if not r["oom_applicable"]]
    print(f"   high_events NOT APPLICABLE — no MemoryHigh in that record's `limits`: "
          f"{len(high_na)} of {len(rows)}")
    print(f"   oom_kills   NOT APPLICABLE — no MemoryMax in that record's `limits`: "
          f"{len(oom_na)} of {len(rows)}")
    fired_high = [r for r in rows if r["high_applicable"] and r["high_events"]]
    fired_oom = [r for r in rows if r["oom_applicable"] and r["oom_kills"]]
    print(f"   of the records where a threshold DID exist, high fired on {len(fired_high)}"
          f" and oom on {len(fired_oom)}")
    print("   Reported this way because '0 throttling events over N runs' states that")
    print("   nothing was throttled, when the truth for most of this corpus is that no")
    print("   threshold existed to throttle against — figure 1's own collapse, one field")
    print("   over.")


def main(argv: list[str]) -> int:
    log_dir = Path(argv[0]) if argv else rl.default_log_dir()
    if not log_dir.is_dir():
        print(f"no log directory at {log_dir}", file=sys.stderr)
        return 1
    by_model = rl.workflow_keys_by_model_key(rl.REPO_ROOT)
    found = rl.events(log_dir, "run_resources")
    rows = [classify(path, event, by_model) for path, event in found]
    if not rows:
        print(f"no run_resources events under {log_dir}", file=sys.stderr)
        return 1
    report(rows, total_logs=len(rl.logs(log_dir)), log_dir=log_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

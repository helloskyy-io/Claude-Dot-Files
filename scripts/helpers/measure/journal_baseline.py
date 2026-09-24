#!/usr/bin/env python3
"""The baseline — what the fleet's runs cost and how they end, as distributions.

    journal_baseline.py                          # configured root, trailing 30 days
    journal_baseline.py --since 2026-09-15 --until 2026-09-24
    journal_baseline.py --root <journal-root>

Self Improvement Phase 1 (`phase1_the_reader.md`). Over every bag the journal
holds, per child and per dated window: F1 turns, F2 cost, F3 wall-clock and API
time, F4 tool errors, and the three trajectory figures of r10 beside them; for
`review-pr`, F5 outcome rates, F6 findings per pass and disposition mix, and F7
asserted-vs-computed agreement. It computes over the journal bags what
`review-runs.sh` computed by hand over `.claude/logs/`, and it retires nothing.

EVERY FIGURE IS A DISTRIBUTION WITH ITS WINDOW (r2). A number without its
spread cannot be told from a good day; a number without its window cannot be
compared with another. `Distribution` and `Proportion` REFUSE CONSTRUCTION with
any of median, IQR, n or window dates missing, and `render` prints nothing
else — so the tool cannot print a bare number, rather than merely not doing so.

  * A NUMERIC figure (turns, cost, time, counts per run) is median, IQR and n.
  * A CATEGORICAL figure (an outcome rate, a disposition share, an agreement
    rate) is k of n with its 95% Wilson interval. A median and IQR of a 0/1
    indicator are each 0 or 1 and say nothing, so the categorical form carries
    the count, the denominator and the window instead — the same four-part
    refusal, fitted to what the figure is — and the interval is its spread:
    two rates whose intervals overlap are not a change (synthesis finding 2).
    WILSON, not the normal approximation, because the rates this fleet
    produces sit at or near 0% and 100%, where the normal interval
    collapses to zero width and claims a certainty n cannot support.

THE RUN FLOOR IS 20 AND IT IS THE PAPER'S. A child under it is listed with its
count and no figures, and the floor is printed beside it.

NO WINDOW REACHES BEFORE 2026-09-15, the reliability floor (roadmap § Data
reliability floor). An earlier `--since` is CLAMPED there and the report says
it was — a distribution over wiring-window bags is noise, not a baseline.

THIS MODULE NEVER SEES A PATH. It reads `Unit`s through `journal_evidence`,
the read interface, and `test_journal_baseline.py` asserts by AST that no
path, glob or directory semantics appear here. It writes nothing: the report
goes to stdout and is derived on demand (r6) — a committed copy would be a
second carrier of a derived fact.

UNTRUSTED INPUT (r5). What it prints is numbers, dates, run ids, repo and
child keys, and values from declared vocabularies. A disposition or an outcome
outside the vocabulary is counted as `unrecognised`; its text is never echoed.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import math
import statistics
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass

import journal_evidence as je

#: The reliability floor — roadmap § Data reliability floor (measured 2026-09-22).
RELIABILITY_FLOOR = "2026-09-15"
#: The paper's run floor. Below it an IQR is not a statement about the child.
RUN_FLOOR = 20
DEFAULT_WINDOW_DAYS = 30
REVIEW_PR = "review-pr"
ROUTED_OUTCOMES = ("merge", "hold:redispatch", "hold:needs_ruling", "undetermined")
ASSERTED_OUTCOMES = ("merge", "hold:redispatch", "hold:needs_ruling")
AGREEMENT = ("agree", "disagree")
#: Children whose F1–F3 mostly measure the brief they were handed, until the
#: task identifier (Claude-Dot-Files #200) lets a figure condition on the task.
PLANNING_PREFIX = "plan-"


class FigureIncomplete(ValueError):
    """A figure was built without one of the parts it may not be printed without."""


@dataclass(frozen=True)
class Window:
    start: str
    end: str
    requested_start: str

    @property
    def clamped(self) -> bool:
        return self.requested_start < self.start

    def holds(self, date: str) -> bool:
        return self.start <= date <= self.end


def make_window(since: str | None, until: str | None, today: _dt.date) -> Window:
    end = _date_arg("--until", until or today.isoformat())
    requested = _date_arg("--since", since or (
        _dt.date.fromisoformat(end) - _dt.timedelta(days=DEFAULT_WINDOW_DAYS)).isoformat())
    start = max(requested, RELIABILITY_FLOOR)
    if start > end:
        raise ValueError(f"window {start}..{end} is empty — --until precedes the "
                         f"reliability floor {RELIABILITY_FLOOR} or --since")
    return Window(start, end, requested)


def _date_arg(label: str, value: str) -> str:
    """`value` if it is EXACTLY `YYYY-MM-DD`, else a ValueError naming the flag.

    Not "anything `fromisoformat` parses": the window compares dates AS
    STRINGS (`Window.holds`, the floor clamp), which is only sound within one
    spelling. Since 3.11 `fromisoformat` also accepts `20260917` and
    `2026-W39-3`, and `'-'` sorts below every digit — so a compact
    `--until 20260917` admitted every later run under a label saying it had
    not. The round trip refuses every spelling but the canonical one.
    """
    try:
        if _dt.date.fromisoformat(value).isoformat() == value:
            return value
    except ValueError:
        pass  # not a date at all — refused below with the same message as a non-canonical one
    raise ValueError(f"{label} {value!r} is not a YYYY-MM-DD date")


def _require(figure: str, **parts) -> None:
    absent = [k for k, v in parts.items() if v is None or v == ""]
    if absent:
        raise FigureIncomplete(f"{figure}: refusing to build a figure without {absent}")


@dataclass(frozen=True)
class Distribution:
    """A numeric figure: median, IQR, n, the window, and the observed run span."""

    figure: str
    median: float
    q1: float
    q3: float
    n: int
    window: Window
    first: str
    last: str
    excluded: int = 0            # runs in the population that lacked the field

    def __post_init__(self) -> None:
        _require(self.figure, median=self.median, q1=self.q1, q3=self.q3,
                 n=self.n or None, window=self.window, first=self.first, last=self.last)


@dataclass(frozen=True)
class Proportion:
    """A categorical figure: k of n, the window, and the observed run span."""

    figure: str
    count: int
    n: int
    window: Window
    first: str
    last: str

    def __post_init__(self) -> None:
        _require(self.figure, count=self.count, n=self.n or None, window=self.window,
                 first=self.first, last=self.last)


def distribution(figure: str, values: list[tuple[float | None, str]], window: Window) -> Distribution | None:
    """`values` is (value, date) per run in the population. None if nothing carries it."""
    kept = [(v, d) for v, d in values if v is not None]
    if not kept:
        return None
    numbers = sorted(v for v, _ in kept)
    if len(numbers) == 1:
        q1 = q3 = numbers[0]
    else:
        q1, _, q3 = statistics.quantiles(numbers, n=4, method="inclusive")
    dates = sorted(d for _, d in kept)
    return Distribution(figure, statistics.median(numbers), q1, q3, len(numbers), window,
                        dates[0], dates[-1], excluded=len(values) - len(kept))


#: The two-sided 95% normal quantile the Wilson interval is taken at.
_Z95 = 1.959963984540054


def wilson(count: int, n: int, z: float = _Z95) -> tuple[float, float]:
    """The Wilson score interval for `count` of `n`, as fractions in [0, 1]."""
    p = count / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def _fmt(value: float) -> str:
    return f"{value:,.2f}" if abs(value) < 100 and value != int(value) else f"{value:,.0f}"


def render(fig: Distribution | Proportion) -> str:
    if not isinstance(fig, (Distribution, Proportion)):
        raise TypeError(f"not a figure: {type(fig).__name__} — nothing prints a bare number")
    span = f"window {fig.window.start}..{fig.window.end}, runs {fig.first}..{fig.last}"
    if isinstance(fig, Distribution):
        extra = f" ({fig.excluded} lacked the field)" if fig.excluded else ""
        return (f"{fig.figure:<34} median {_fmt(fig.median):>9}  IQR {_fmt(fig.q1)}–{_fmt(fig.q3)}"
                f"  n={fig.n}{extra}  {span}")
    pct = 100.0 * fig.count / fig.n
    lo, hi = wilson(fig.count, fig.n)
    return (f"{fig.figure:<34} {fig.count}/{fig.n} ({pct:.0f}%, 95% CI {100 * lo:.0f}–{100 * hi:.0f}%)"
            f"  {span}")


# --- the report -----------------------------------------------------------------

@dataclass(frozen=True)
class Sweep:
    units: list
    rotated: object
    source: str
    seconds: float


def sweep(journal: je.JournalEvidence) -> Sweep:
    """Read every unit once and time it — r9's figure is this wall-clock."""
    started = time.monotonic()
    units = [journal.read(ref) for ref in journal.units()]
    rotated = journal.rotated_out({u.run_id for u in units})
    return Sweep(units, rotated, journal.label, time.monotonic() - started)


def report(s: Sweep, window: Window) -> list[str]:
    out: list[str] = []
    in_window = [u for u in s.units if window.holds(u.date)]
    runs = child_runs(s.units, window)

    out.append("# Self-improvement baseline — the journal's run records, as distributions")
    out.append("")
    out.append(f"reads   : journal root {s.source} (every bag's events and tags; the latest snapshot)")
    out.append("          and, through assess_completeness, each origin repo's .claude/logs/")
    out.append("writes  : nothing — this report is stdout only, derived on demand")
    clamp = (f"  (requested start {window.requested_start} CLAMPED to the reliability floor)"
             if window.clamped else "")
    out.append(f"window  : {window.start}..{window.end}{clamp}")
    out.append(f"floor   : a child needs >= {RUN_FLOOR} runs in the window for figures")
    out.append("")

    out += _repos(s.units, in_window)
    out += _coverage(in_window)
    out += _incomplete(in_window, runs)
    out += _gapped(s)
    out += _children(runs, window)
    out += _review_pr(runs, window)
    total_bytes = sum(u.bytes for u in s.units)
    out.append("## Sweep cost (r9 — the no-database decision's revisit trigger reads this)")
    out.append(f"  {s.seconds:.2f}s wall-clock over {len(s.units)} bags, {total_bytes:,} bytes "
               f"({total_bytes / 2**20:,.1f} MiB)")
    return out


def child_runs(units, window: Window) -> list:
    """Every child run in the window, windowed by ITS OWN date.

    Bag-level sections (coverage, incompleteness) window on the bag; a figure
    windows on the run, because a bag's children can fall on two dates. The
    bag must still start on or after the reliability floor — a run inside a
    bag opened during the wiring window is that bag's evidence, and the floor
    is about bags.
    """
    return [c for u in units if u.date >= RELIABILITY_FLOOR
            for c in u.children if c.date and window.holds(c.date)]


def _repos(units, in_window) -> list[str]:
    everywhere = Counter(u.repo or "(no origin repo tag)" for u in units)
    windowed = Counter(u.repo or "(no origin repo tag)" for u in in_window)
    out = [f"## Repos found — derived from the bags, never given ({len(everywhere)} repos, "
           f"{len(units)} bags; {len(in_window)} in window)"]
    for repo, n in sorted(everywhere.items(), key=lambda kv: (-kv[1], kv[0])):
        out.append(f"  {repo:<40} {n:>5} bags  {windowed.get(repo, 0):>5} in window")
    return out + [""]


def _coverage(in_window) -> list[str]:
    read = sum(u.has_events for u in in_window)
    complete = [u for u in in_window if u.completeness == "complete"]
    out = ["## Coverage (assess_completeness — the journal's contract, imported, not re-derived)",
           f"  bags read / bags that should exist : {read}/{len(in_window)}",
           f"  complete by the contract           : {len(complete)}/{len(in_window)}"]
    for u in in_window:
        if u.completeness == "complete":
            continue
        out.append(f"  {u.completeness.upper():<11} {u.run_id[:8]}  {u.workflow or '?'}  {u.repo or '?'}")
        for reason in u.completeness_reasons:
            out.append(f"      {reason}")
    return out + [""]


def _incomplete(in_window, runs) -> list[str]:
    no_result = [c for c in runs if c.has_transcript and not c.has_result]
    no_transcript = [c for c in runs if not c.has_transcript]
    undated = [c for u in in_window for c in u.children if not c.date]
    out = ["## Incomplete records in the window — counted, never a silently smaller denominator",
           f"  child runs                          : {len(runs)}",
           f"  ... transcript with no result event : {len(no_result)}"
           + _by_child(no_result),
           f"  ... run-log events, no transcript   : {len(no_transcript)}" + _by_child(no_transcript),
           f"  child runs with no dated event      : {len(undated)} (no window can hold them)"
           + _by_child(undated),
           f"  bags with no events.jsonl           : {sum(not u.has_events for u in in_window)}",
           f"  gap events                          : {sum(u.gap_events for u in in_window)}"
           f" in {sum(u.gap_events > 0 for u in in_window)} bags",
           f"  Journal-Gap labels                  : {sum(u.gap_labels for u in in_window)}",
           f"  bags flagged Journal-Incomplete     : {sum(u.incomplete_flag for u in in_window)}",
           f"  event lines the decoder refused     : {sum(u.undecodable for u in in_window)}",
           f"  redaction placeholders              : {sum(u.redactions for u in in_window)}",
           f"  harvested surface items             : {sum(u.harvested for u in in_window)}"]
    return out + [""]


def _by_child(runs) -> str:
    if not runs:
        return ""
    counts = Counter(c.child for c in runs)
    return "  (" + ", ".join(f"{k} {n}" for k, n in sorted(counts.items())) + ")"


def _gapped(s: Sweep) -> list[str]:
    on_disk = {u.run_id for u in s.units if u.gapped}
    gapped = on_disk | set(s.rotated.carried_gap_run_ids)
    denominator = len(s.units) + len(s.rotated.carried_run_ids)
    snap = s.rotated.snapshot or "none under the root"
    return ["## Gapped bags, whole journal (PMP Phase 4 r7 — deduped on run_id)",
            f"  {len(gapped)}/{denominator}  (bags on disk {len(s.units)} + rotated out behind "
            f"the snapshot {len(s.rotated.carried_run_ids)}; snapshot: {snap})", ""]


def _children(runs, window: Window) -> list[str]:
    by_child: dict[str, list] = defaultdict(list)
    for c in runs:
        by_child[c.child].append((c, c.date))
    out = ["## F1–F4 and the trajectory figures, per child"]
    for child, runs in sorted(by_child.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        done = [(c, d) for c, d in runs if c.has_result]
        head = f"### {child} — {len(runs)} runs in window, {len(done)} with a result event"
        if len(done) < RUN_FLOOR:
            out.append(f"{head}; below the run floor of {RUN_FLOOR} — no figures")
            continue
        out.append(head)
        if child.startswith(PLANNING_PREFIX):
            out.append("  (a planning child: without the task identifier, Claude-Dot-Files #200, "
                       "F1–F3 here mostly measure the briefs it was handed)")
        for fig in child_figures(done, window):
            out.append("  " + render(fig))
    return out + [""]


def child_figures(done, window: Window) -> list[Distribution]:
    specs = [
        ("F1 turns per run", lambda c: c.num_turns),
        ("F2 cost per run (USD)", lambda c: c.total_cost_usd),
        ("F3 wall-clock per run (s)", lambda c: None if c.duration_ms is None else c.duration_ms / 1000),
        ("F3 API time per run (s)", lambda c: None if c.duration_api_ms is None else c.duration_api_ms / 1000),
        ("F4 tool errors per run", lambda c: c.tool_errors),
        ("T1 read-before-edit refusals/run", lambda c: c.read_before_edit),
        ("T2 repeated reads of one file/run", lambda c: c.repeated_reads),
        ("T3 sub-agents per run", lambda c: c.subagents),
    ]
    figs = [distribution(name, [(get(c), d) for c, d in done], window) for name, get in specs]
    return [f for f in figs if f is not None]


def _review_pr(all_runs, window: Window) -> list[str]:
    runs = [(c, c.date) for c in all_runs if c.child == REVIEW_PR]
    # THE FLOOR COUNTS EVERY review-pr RUN, result or not — unlike F1–F4's,
    # which counts runs with a result. F5's routed rate and F7 read the
    # parent's records, which exist without a result; each figure below
    # states its own denominator.
    out = ["## F5–F7 — review-pr only",
           f"  population: {len(runs)} review-pr runs in window, "
           f"{sum(c.has_result for c, _ in runs)} with a result event (the floor counts all of them)"]
    if len(runs) < RUN_FLOOR:
        return out + [f"  below the run floor of {RUN_FLOOR} — no figures", ""]
    for fig_lines in (_f5(runs, window), _f6(runs, window), _f7(runs, window)):
        out += fig_lines
    return out + [""]


def _proportions(prefix: str, labelled: list[tuple[str, str]], labels, window: Window) -> list[Proportion]:
    """One Proportion per label over `labelled` = (label, date), plus `unrecognised`."""
    if not labelled:
        return []
    dates = sorted(d for _, d in labelled)
    counts = Counter(label if label in labels else "unrecognised" for label, _ in labelled)
    keys = list(labels) + (["unrecognised"] if counts.get("unrecognised") else [])
    return [Proportion(f"{prefix} {k}", counts.get(k, 0), len(labelled), window, dates[0], dates[-1])
            for k in keys]


def _f5(runs, window: Window) -> list[str]:
    routed = [(c.routed_outcome, d) for c, d in runs if c.has_parent_route]
    asserted = [(c.asserted_outcome, d) for c, d in runs if c.has_structured_output]
    out = [f"  F5 outcome rates — routed by the parent over {len(routed)} runs with parent_route "
           f"({len(runs) - len(routed)} without); asserted by the child over {len(asserted)} with "
           f"structured_output ({len(runs) - len(asserted)} without)"]
    out += ["    " + render(p) for p in _proportions("F5 routed", routed, ROUTED_OUTCOMES, window)]
    out += ["    " + render(p) for p in _proportions("F5 asserted", asserted, ASSERTED_OUTCOMES, window)]
    return out


def _f6(runs, window: Window) -> list[str]:
    passes = [(c, d) for c, d in runs if c.has_structured_output]
    out = [f"  F6 findings — over {len(passes)} passes with structured_output"]
    fig = distribution("F6 findings per pass", [(len(c.dispositions), d) for c, d in passes], window)
    if fig is not None:
        out.append("    " + render(fig))
    findings = [(disp, d) for c, d in passes for disp in c.dispositions]
    out += ["    " + render(p) for p in _proportions("F6 disposition", findings, je.DISPOSITIONS, window)]
    return out


def _f7(runs, window: Window) -> list[str]:
    routes = [(c, d) for c, d in runs if c.has_parent_route]
    parseable = [(c, d) for c, d in routes if c.shadow_parseable is True]
    false_ = sum(c.shadow_parseable is False for c, _ in routes)
    absent = len(routes) - len(parseable) - false_
    out = [f"  F7 channels_agree — over shadow_parseable: true only: {len(parseable)} of "
           f"{len(routes)} parent_route records; EXCLUDED {len(routes) - len(parseable)} "
           f"(shadow_parseable false {false_}, absent {absent}) — over all records the figure "
           f"measures how often the prose sentinel was omitted, not whether the channels differ"]
    agree = [("agree" if c.channels_agree else "disagree", d) for c, d in parseable
             if c.channels_agree is not None]
    out += ["    " + render(p) for p in _proportions("F7 channels", agree, AGREEMENT, window)]
    convs = [(c, d) for c, d in runs if c.has_convergence]
    computable = [("agree" if c.convergence_agrees else "disagree", d) for c, d in convs
                  if c.convergence_agrees is not None]
    out.append(f"  F7 convergence.agrees — over {len(computable)} of {len(convs)} convergence "
               f"records where the parent could compute a state; EXCLUDED "
               f"{len(convs) - len(computable)} indeterminate")
    out += ["    " + render(p) for p in _proportions("F7 convergence", computable, AGREEMENT, window)]
    return out


def main(argv: list[str] | None = None, *, today: _dt.date | None = None) -> int:
    ap = argparse.ArgumentParser(prog="journal_baseline", description=__doc__.split("\n")[0])
    ap.add_argument("--root", help="a journal root; default is the configured one")
    ap.add_argument("--since", metavar="YYYY-MM-DD",
                    help=f"window start; default {DEFAULT_WINDOW_DAYS} days before --until; "
                         f"never earlier than {RELIABILITY_FLOOR}")
    ap.add_argument("--until", metavar="YYYY-MM-DD", help="window end, inclusive; default today (UTC)")
    a = ap.parse_args(argv)
    try:
        window = make_window(a.since, a.until, today or _dt.datetime.now(_dt.timezone.utc).date())
    except ValueError as exc:
        print(f"journal_baseline: bad window — {exc}", file=sys.stderr)
        return 2
    try:
        journal = je.open_journal(a.root)
        s = sweep(journal)
    except je.JournalEvidenceError as exc:
        print(f"journal_baseline: {exc}", file=sys.stderr)
        return 2
    if not s.units:
        # "0 bags" printed as a report would read exactly like a quiet journal.
        print(f"journal_baseline: no bags under {s.source} — this run measured nothing", file=sys.stderr)
        return 2
    print("\n".join(report(s, window)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

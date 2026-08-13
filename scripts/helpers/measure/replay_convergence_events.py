#!/usr/bin/env python3
"""Read the run log's `convergence` events, and print Phase 5's gate conditions.

THIS IS CANDIDATE C-059. `phase5_convergence_stopping.md` emitted a
`{"type": "convergence"}` event on every dispatch, placed the reader as a
candidate with the trigger *the first question only the live corpus can answer*,
and shipped. This is that reader, and the trigger has fired: two facts the
GitHub `pr_review:` archive is STRUCTURALLY UNABLE to produce have no denominator
without it —

  * the `pass_not_evaluable` and `history_unreadable` rates. The archive replay
    hands `pass_evaluable=True` to every block as a stated ASSUMPTION, because no
    archived block carries a typed exit record; only the live path knows whether
    the pass actually routed.
  * the typed term the LIVE predicate reads. The replay's most recent pass comes
    from a prose block; the live one comes from the typed record.

IT IS A SECOND CORPUS, NOT A BIGGER ONE, and conflating the two is a mistake the
phase doc records being made once. `replay_convergence_predicate.py` replays the
GitHub archive and answers *would the predicate have fired*. This answers *what
did the predicate actually say, on the runs that happened*. Neither denominator
substitutes for the other.

§ PHASE 5 GATE CONDITIONS. `phase6_read_what_it_writes.md` § Phase 5's un-owned
activation makes conditions 1 and 2 tool output rather than a number a human must
remember to re-derive. Condition 1 is scored on the ARCHIVE and needs `gh`, so it
is printed only with `--archive`; without it the section says NOT TAKEN rather
than implying a zero. **Condition 3 is a RULING and is deliberately absent — this
tool prints numbers and does not propose a pass count.** Condition 4 has fired
and is recorded in Phase 5.

WHAT IT DOES NOT PRINT. `convergence` events carry `open_ids`, `opened`,
`closed`, `added_ids` and `escalated_open` — lists of MODEL-AUTHORED finding
slugs. This emits their LENGTHS. `run_log.assert_publishable` enforces it on the
row about to be printed.

Usage:  python3 scripts/helpers/measure/replay_convergence_events.py [LOG_DIR]
        python3 scripts/helpers/measure/replay_convergence_events.py --archive [OWNER/REPO]
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PREDICATE_REPLAY = _HERE / "replay_convergence_predicate.py"


def _run_log():
    spec = importlib.util.spec_from_file_location("_run_log", _HERE / "run_log.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["_run_log"] = module
    spec.loader.exec_module(module)
    return module


rl = _run_log()

# The two guards Phase 5 § What would let this gate condition 2 asks for field
# evidence of. Named here rather than derived from `IndeterminateReason`, and the
# distinction matters: condition 2 is about the two guards that defend against a
# BIASED WRITER, not about every residual-arm reason. `no_prior_pass` is the
# archive's most common outcome and guards nothing.
BIAS_GUARDS = ("prior_findings_dropped", "oscillating_findings")


def rows(log_dir: Path) -> list[dict]:
    out = []
    for path, event in rl.events(log_dir, "convergence"):
        row = {
            "log": path.name,
            "run_id": event.get("run_id"),
            "pr": event.get("pr"),
            "state": event.get("state"),
            "reason": event.get("reason"),
            "passes": event.get("passes"),
            "stalled": event.get("stalled"),
            "asserted_converged": event.get("asserted_converged"),
            "agrees": event.get("agrees"),
        }
        # LENGTHS, never the slugs.
        row["n_open"] = len(event.get("open_ids") or ())
        row["n_added"] = len(event.get("added_ids") or ())
        row["n_escalated_open"] = len(event.get("escalated_open") or ())
        row["n_unknown_dispositions"] = len(event.get("unknown_dispositions") or ())
        rl.assert_publishable("convergence", event, row)
        out.append(row)
    return out


def _archive_report(repo: str | None) -> str | None:
    """The sibling archive replay's stdout, or None if it could not be taken.

    SHELLED OUT RATHER THAN IMPORTED. That tool imports the SHIPPED predicate
    and prints the scorable denominator condition 1 is written in; re-deriving
    either here would be a second implementation of a number the phase doc
    quotes, which is the duplicated-parser defect this component exists to
    remove.
    """
    argv = [sys.executable, str(_PREDICATE_REPLAY)] + ([repo] if repo else [])
    done = subprocess.run(argv, capture_output=True, text=True)
    if done.returncode != 0:
        print(f"   archive replay FAILED (exit {done.returncode}): "
              f"{done.stderr.strip()[:400] or '<no stderr>'}", file=sys.stderr)
        return None
    return done.stdout


def _line(report: str, prefix: str) -> str | None:
    for line in report.splitlines():
        if line.strip().startswith(prefix):
            return line.strip()
    return None


def report(live: list[dict], log_dir: Path, total_logs: int,
           archive: str | None, archive_requested: bool) -> None:
    print("# convergence run-log events — the LIVE corpus (candidate C-059)")
    print()
    print(f"Log directory            : {log_dir}")
    print(f"Logs in archive          : {total_logs}")
    print(f"Carrying a convergence   : {len(live)}  <- THE DENOMINATOR for every live figure")
    print("Emission starts at Phase 5 (2026-08-09); every earlier log has none.")
    print()

    states = Counter(r["state"] for r in live)
    reasons = Counter(r["reason"] for r in live if r["reason"])
    print("## What the predicate actually said")
    print(f"   states : {dict(states)}  of {len(live)}")
    print(f"   residual-arm reasons: {dict(reasons)}")
    print()

    print("## The two facts the GitHub archive structurally cannot produce")
    not_evaluable = sum(1 for r in live if r["reason"] == "pass_not_evaluable")
    unreadable = sum(1 for r in live if r["reason"] == "history_unreadable")
    print(f"   pass_not_evaluable : {not_evaluable} of {len(live)}")
    print(f"   history_unreadable : {unreadable} of {len(live)}")
    print("   The archive replay hands `pass_evaluable=True` to every block as a stated")
    print("   assumption — no archived block carries a typed exit record — so these two")
    print("   rates exist only here. This is the answer C-059's trigger named.")
    print()

    print("## Shadow against the model's asserted `converged:` flag, on the LIVE path")
    scorable = [r for r in live if r["agrees"] is not None]
    disagree = [r for r in scorable if r["agrees"] is False]
    print(f"   comparable events: {len(scorable)} of {len(live)}"
          f"  (the rest are indeterminate or predate the flag)")
    print(f"   DISAGREEMENTS   : {len(disagree)}"
          + (f" — {[r['run_id'] for r in disagree]}" if disagree else " — none"))
    print()

    # --- PHASE 5 GATE CONDITIONS --------------------------------------------
    print("=" * 74)
    print("§ Phase 5 § What would let this gate — conditions 1 and 2, with denominators")
    print("=" * 74)
    print()

    print("## Condition 1 — the scorable-fire bound, in the OBSERVED counter's units")
    print("   A scorable fire is a CONVERGED assessment with at least one LATER pass on")
    print("   the same PR. Phase 5 § Measurement derives the bound: roughly 60 scorable")
    print("   fires to put the observed early-fire rate under 5% with 95% confidence.")
    if archive is None:
        print("   NOT TAKEN. This figure is scored on the GitHub `pr_review:` archive and")
        print("   needs `gh`. Re-run with `--archive` to take it. It is reported as NOT")
        print("   TAKEN rather than as zero, because those are different facts and this")
        print("   whole surface exists because collapsing them hides a gap."
              if not archive_requested else
              "   The archive replay was requested and FAILED; see stderr above.")
    else:
        for prefix in ("PRs in archive", "Blocks assessed", "Blocks with a prior pass",
                       "Would have FIRED", "Fired EARLY (observed)", "... unfalsifiable"):
            got = _line(archive, prefix)
            if got:
                print(f"   {got}")
        print("   The SCORABLE denominator is the `Fired EARLY (observed)` line's `of N`.")
        print("   While every fire lands on its PR's last block, N stays 0 and the")
        print("   condition is further away than block count suggests: what has to change")
        print("   is the SHAPE of the corpus — PRs that keep being reviewed AFTER a pass")
        print("   closed everything — not its size.")
    print()

    print("## Condition 2 — at least one archived instance of each guard firing")
    print("   The two guards that defend against a biased writer. Phase 5 recorded ZERO")
    print("   field instances of both and asked for one each, or an explicit statement")
    print("   that there is none.")
    for guard in BIAS_GUARDS:
        n_live = sum(1 for r in live if r["reason"] == guard)
        if archive is None:
            archive_note = "archive NOT TAKEN"
        else:
            residual = _line(archive, "Residual-arm reasons") or ""
            archive_note = f"archive: {'FIRED' if guard in residual else 'never fired'}"
        verdict = "HAS FIRED on real data" if n_live else "has NEVER fired on real data"
        print(f"   {guard:<24} live: {n_live} of {len(live)}   {archive_note}   -> {verdict}")
    print("   A guard with mutation evidence and no field evidence is still a guard; the")
    print("   difference is recorded rather than smoothed over, which is what condition 2")
    print("   asks for.")
    print()

    print("## Condition 3 — NOT PRINTED, and that is deliberate")
    print("   *What would convergence gate* is a RULING, not a measurement. It is the")
    print("   operator's, jointly with Autonomous Operation where the cross-dispatch case")
    print("   lives. This tool prints numbers; it proposes no pass count and enables")
    print("   nothing. Condition 4 fired on 2026-08-10 and is recorded in Phase 5.")
    print()

    print("Per-event:")
    header = ("run_id", "pr", "state", "reason", "passes", "open", "added",
              "esc", "stalled", "asserted", "agrees")
    print("  " + " | ".join(header))
    for r in live:
        print("  " + " | ".join(str(x) for x in (
            (r["run_id"] or "?")[:8], r["pr"], r["state"], r["reason"] or "-",
            r["passes"], r["n_open"], r["n_added"], r["n_escalated_open"],
            r["stalled"], r["asserted_converged"], r["agrees"],
        )))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log_dir", nargs="?", type=Path, default=None)
    parser.add_argument("--archive", nargs="?", const="", default=None,
                        metavar="OWNER/REPO",
                        help="also take condition 1 from the GitHub pr_review: archive")
    args = parser.parse_args(argv)

    log_dir = args.log_dir or rl.default_log_dir()
    if not log_dir.is_dir():
        print(f"no log directory at {log_dir}", file=sys.stderr)
        return 1
    live = rows(log_dir)
    archive = None
    if args.archive is not None:
        archive = _archive_report(args.archive or None)
    report(live, log_dir, len(rl.logs(log_dir)), archive,
           archive_requested=args.archive is not None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Read the run log's `parent_route` events: the abstention arm, and the shadow.

WHY THIS EXISTS RATHER THAN A RULING THAT `parent_route` NEEDS NO READER.
`phase6_read_what_it_writes.md` step 2 asks this member to be RULED either way,
and the honest ruling is that it has two questions nothing else can answer:

  1. **The computed abstention rate, grouped by reason.**
     `phase3_typed_exit_record.md` step 4 specifies both arms of the fail-safe
     contract as predicates over a run's events. The ASSERTED arm reads
     `structured_output.hold_kind`, which the child writes. The COMPUTED arm
     reads `routed_outcome` grouped by `undetermined_reason` — the arm the
     protocol calls the RELIABLE one — and `append_parent_route` exists precisely
     because nothing else writes it durably. Nothing reads it either, until here.

  2. **The channel-agreement rate, with its denominator.**
     `phase4_fleet_migration.md` carries an unchecked box — the prose shadow
     stays until `channels_agree` has agreed across *a stated run count with its
     denominator*. That figure was derived by hand from eight runs. This is the
     instrument that prints it, and it prints the limit with it: **C-060** says
     `channels_agree` can only be written on runs where the incumbent prose
     channel already SUCCEEDED, because a completion-gate failure raises before
     `route()` and before this event. So the agreement figure is conditioned on
     the very thing it measures, and no larger N removes that.

WHAT IT DOES NOT PRINT. `parent_route`'s payload is all typed values the parent
computed — enums, booleans and a PR number — so the publish check passes trivially
today. It is still applied, because the payload is the one that grows.

Usage:  python3 scripts/helpers/measure/replay_parent_route.py [LOG_DIR]
"""

from __future__ import annotations

import importlib.util
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _run_log():
    spec = importlib.util.spec_from_file_location("_run_log", _HERE / "run_log.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["_run_log"] = module
    spec.loader.exec_module(module)
    return module


rl = _run_log()


def rows(log_dir: Path) -> list[dict]:
    out = []
    for path, event in rl.events(log_dir, "parent_route"):
        row = {
            "log": path.name,
            "run_id": event.get("run_id"),
            "pr": event.get("pr"),
            "routed_outcome": event.get("routed_outcome"),
            "undetermined_reason": event.get("undetermined_reason"),
            "hold_kind": event.get("hold_kind"),
            "shadow_verdict": event.get("shadow_verdict"),
            "shadow_parseable": event.get("shadow_parseable"),
            "channels_agree": event.get("channels_agree"),
        }
        rl.assert_publishable("parent_route", event, row)
        out.append(row)
    return out


def report(rows_: list[dict], log_dir: Path, total_logs: int) -> None:
    print("# parent_route run-log events — the computed arm, and the shadow")
    print()
    print(f"Log directory            : {log_dir}")
    print(f"Logs in archive          : {total_logs}")
    print(f"Carrying a parent_route  : {len(rows_)}  <- THE DENOMINATOR for every figure below")
    print("Emission starts at Phase 3 (2026-08-09); every earlier log has none.")
    print()

    outcomes = Counter(r["routed_outcome"] for r in rows_)
    undetermined = [r for r in rows_ if r["routed_outcome"] == "undetermined"]
    reasons = Counter(r["undetermined_reason"] for r in undetermined)
    print("## The COMPUTED abstention arm — `routed_outcome`, grouped by reason")
    print(f"   routed_outcome: {dict(outcomes)}  of {len(rows_)}")
    print(f"   abstained     : {len(undetermined)} of {len(rows_)}"
          + (f"  ({100 * len(undetermined) / len(rows_):.1f}%)" if rows_ else ""))
    print(f"   reasons       : {dict(reasons) or 'none'}")
    print("   GROUPED BY REASON RATHER THAN COUNTED, per `exit-protocol.md` §4's R1a/R2")
    print("   split: a `gh` rate limit must not be counted as a degraded review.")
    print()

    comparable = [r for r in rows_ if r["channels_agree"] is not None]
    agree = [r for r in comparable if r["channels_agree"]]
    disagree = [r for r in comparable if not r["channels_agree"]]
    print("## The prose SHADOW against the typed record")
    print(f"   comparable : {len(comparable)} of {len(rows_)}")
    print(f"   agreed     : {len(agree)} of {len(comparable)}")
    print(f"   disagreed  : {len(disagree)} of {len(comparable)}")
    if disagree:
        # THE DISAGREEMENTS ARE BROKEN DOWN, because a raw count reads as a
        # channel defect and the archive's have all been something else: the
        # parent applying a safety rule the model could not see (R1), which is
        # the machinery working rather than the channels differing.
        by_outcome = Counter(r["routed_outcome"] for r in disagree)
        print(f"   disagreements by routed_outcome: {dict(by_outcome)}")
        r1 = [r for r in disagree if r["routed_outcome"] == "undetermined"]
        print(f"     of which the PARENT abstained (R1 — a safety rule the model could")
        print(f"     not see, not a channel disagreement): {len(r1)} of {len(disagree)}")
        print(f"     genuine channel disagreements: {len(disagree) - len(r1)}")
    unparseable = [r for r in rows_ if r["shadow_parseable"] is False]
    print(f"   prose channel UNPARSEABLE: {len(unparseable)} of {len(rows_)}")
    print("   `shadow_parseable` is recorded separately from `shadow_verdict` because")
    print("   `parse_verdict` fails safe: an unparseable channel and one that genuinely")
    print("   said `HOLD - needs-assistance` yield the same token.")
    print()

    print("## THE DENOMINATOR'S OWN LIMIT — C-060 is FIXED, and here is what remains")
    print("   THIS SECTION USED TO SAY NO N REMOVED THE LIMIT. That was true until")
    print("   2026-08-14 and is not now. `append_parent_route` sat AFTER")
    print("   `run_claude`'s completion gate, so a dispatch whose child emitted a")
    print("   valid typed record and no prose `VERDICT:` line raised at that gate")
    print("   and never became a row — the instrument was blind to prose's own")
    print("   failure mode, which is the one it exists to weigh.")
    print("   `review_pr_workflow._append_shadow_pair` is now called on BOTH paths:")
    print("   inside the `except` the gate raises through, and on success. A run")
    print("   that fails the gate becomes a row.")
    print("   WHAT REMAINS IS SMALLER AND IS NOT A CONDITIONING: no run since the")
    print("   fix has failed its completion gate, so the newly-recordable case has")
    print("   not yet fired. The figures above are a RATE, not a conditional — but")
    print("   the path that makes them one is proven by reading the code rather")
    print("   than by having watched it happen.")
    print()

    print("Per-event:")
    header = ("run_id", "pr", "routed_outcome", "undetermined_reason", "hold_kind",
              "shadow_verdict", "parseable", "agree")
    print("  " + " | ".join(header))
    for r in rows_:
        print("  " + " | ".join(str(x) for x in (
            (r["run_id"] or "?")[:8], r["pr"], r["routed_outcome"],
            r["undetermined_reason"] or "-", r["hold_kind"] or "-",
            r["shadow_verdict"] or "-", r["shadow_parseable"], r["channels_agree"],
        )))


def main(argv: list[str]) -> int:
    log_dir = Path(argv[0]) if argv else rl.default_log_dir()
    if not log_dir.is_dir():
        print(f"no log directory at {log_dir}", file=sys.stderr)
        return 1
    found = rows(log_dir)
    if not found:
        print(f"no parent_route events under {log_dir}", file=sys.stderr)
        return 1
    report(found, log_dir, len(rl.logs(log_dir)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

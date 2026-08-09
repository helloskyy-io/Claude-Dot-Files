#!/usr/bin/env python3
"""Replay archived run logs through the fleet's completion predicates.

WHY THIS IS KEPT (and not deleted as a one-shot): open direction row `D-007`
(`docs/standards/architecture/research/direction.md`) rules on whether the
VERDICT-token-on-stdout completion contract stands, gains a write-time gate, or
is replaced. Its evidence is the miss rate of the incumbent grep, and a miss
rate over 14 review-pr logs is a different claim from the same rate over 140.
The denominator grows every time the fleet runs. Re-run this rather than
re-deriving the method.

Measured for Memory Management Framework Phase 1, experiment E5.

The fleet declares completion patterns in TWO places with DIFFERENT surfaces,
and this script measures both because they can disagree:

  1. CHILD-SIDE, over the result envelope. `run-claude.sh`'s § Completion
     contract extracts `.result` from the JSONL and applies
     `grep -qE "$COMPLETION_PATTERN"`. This is the write-time gate that already
     exists. NOTE: a caller that declares EXIT_RECORD_SCHEMA reads the last
     assistant text block instead, because declaring a schema replaces
     `.result` with the serialised structured output; this script measures the
     `.result` surface, which is what the V1 fleet still runs.
  2. PARENT-SIDE, over the child's console output. `build.sh:277` and
     `build-minor.sh:281` apply `grep -oE '^VERDICT: …' | tail -1` to the
     tee'd stdout+stderr of the child process — a WIDER surface that includes
     every streamed assistant message, not just the final result.

Surface 2's input is not archived; the JSONL is. What IS reconstructible from
the JSONL is the union of assistant text turns, which is what the console
carries, so this script reconstructs it and flags where the two surfaces differ.

Usage:  python3 scripts/helpers/measure/replay_completion_predicate.py [LOG_DIR]

PASS LOG_DIR EXPLICITLY WHEN RUNNING FROM A WORKTREE, which is the fleet's
normal dispatch shape. The default resolves three parents up from this file,
which inside `.claude/worktrees/<name>/` is the WORKTREE root -- and `.claude/`
is globally gitignored, so no `logs/` exists there. The run then reports an
empty corpus, which is loud but diagnoses badly. The archive lives in the main
checkout: `<main checkout>/.claude/logs`.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

# Verbatim from review-pr.sh:186 (the ERE the child's own gate compiles) and
# review_pr_helper.py:70. NOT byte-identical to routing.py:43, which spells the
# inner alternation non-capturing; the difference is invisible to `.search()`
# and visible to `.findall()`, so every extraction below goes through
# `finditer()` + `group(0)` rather than `findall()`.
#
# DELIBERATELY COPIED, NOT IMPORTED. A replay tool pins the predicate it
# replays: importing the live `routing._VERDICT` would make a re-run in a year
# silently measure a CHANGED rule against the SAME archived logs and report the
# result as the same number. The drift this copy risks is loud (a test asserts
# parity with the shipped ERE); the drift an import risks is silent.
STRICT_VERDICT = re.compile(
    r"^VERDICT: (MERGE|HOLD - (redispatch|needs-assistance))$", re.MULTILINE
)
# Deliberately looser, per E5's stated adjudication procedure: unanchored, and
# tolerant of the markdown emphasis and leading whitespace a model actually
# emits. The DIFFERENCE between the two sets is what gets adjudicated by hand.
LOOSE_VERDICT = re.compile(r"VERDICT:?\s*\**\s*(MERGE|HOLD)", re.IGNORECASE)

# Verbatim from build.sh:198 / build-minor.sh:202 and the 16 pull-only
# COMPLETION_PATTERN declarations across both fleets (8 bash, 8 Python).
PR_URL = re.compile(r"https://github\.com/[^ )]+/pull/[0-9]+")

# `plan-revision` and `plan-new` declare a WIDER pattern: they may legitimately
# complete by opening a STOP **issue** instead of a PR, and their gates say so
# (`plan-revision.sh:220`, `plan-new.sh:245`,
# `plan_revision_workflow.py:49` -> `/(pull|issues)/`). Replaying those logs
# against the pull-only pattern would score a lawful issue-URL completion as a
# miss and inflate exactly the number this tool exists to report honestly.
# E6's P6 row documents the same path from the parent's side.
PR_OR_ISSUE_URL = re.compile(r"https://github\.com/[^ )]+/(?:pull|issues)/[0-9]+")

VERDICT_WORKFLOWS = ("review-pr",)
ISSUE_ALTERNATIVE_WORKFLOWS = ("plan-revision", "plan-new")

# Workflows that declare NO `COMPLETION_PATTERN` at all. They have no completion
# contract to replay, so scoring them against ANY pattern manufactures misses:
# the tool would report a workflow as failing a gate it never claimed to have.
#
# This is the same defect the ISSUE_ALTERNATIVE carve-out above fixes, one step
# further out — that one scored a lawful issue-URL completion against a
# pull-only pattern; this one scored a workflow with no pattern against a
# pull-only pattern. The sibling was left behind when the first was fixed.
#
# MEASURED: with `review-runs` bucketed as `pr_url`, a re-run reported 8 strict
# negatives where the honest in-scope figure is 2 — five of the eight were
# artifacts of this bucketing, in a tool whose entire purpose is to report that
# number honestly.
#
# Derived by exhaustive check, not by guess: every `scripts/workflows/*.sh` and
# `scripts/workflows/children/*.sh` was grepped for `COMPLETION_PATTERN` and
# `review-runs.sh` is the only file with none. If a second appears, it belongs
# here in the same change that creates it.
PATTERNLESS_WORKFLOWS = ("review-runs",)


def workflow_of(path: Path) -> str:
    """`review-pr-20260808-110753.jsonl` -> `review-pr`."""
    return re.sub(r"-\d{8}-\d{6}$", "", path.stem)


def last_whole_match(pattern: re.Pattern, text: str) -> str | None:
    """The last WHOLE match, as a string, whatever groups the pattern carries.

    `findall()` cannot do this job: it returns group tuples for a pattern with
    capturing groups and strings for one without, so the same output field
    would carry two shapes depending on which predicate produced it.
    STRICT_VERDICT has capturing groups (verbatim from the shipped ERE); the
    URL patterns do not.
    """
    matches = [m.group(0) for m in pattern.finditer(text)]
    return matches[-1] if matches else None


def read_log(path: Path) -> tuple[dict | None, list[str], int]:
    """Return (result envelope or None, assistant text turns, unparseable count).

    The third element exists because a silently-dropped line is indistinguishable
    from a line that was never there. A truncated FINAL line is the expected,
    benign case (the run was still writing); a malformed line anywhere else is
    real corruption that would quietly shrink the reconstructed console stream
    and change a count with no trace. The caller reports the number either way.
    """
    envelope, turns, unparseable = None, [], 0
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            unparseable += 1
            continue
        if not isinstance(ev, dict):
            unparseable += 1
            continue
        if ev.get("type") == "result":
            envelope = ev
        elif ev.get("type") == "assistant":
            for block in ev.get("message", {}).get("content", []) or []:
                if isinstance(block, dict) and block.get("type") == "text":
                    turns.append(block.get("text", ""))
    return envelope, turns, unparseable


def main(log_dir: Path) -> int:
    logs = sorted(log_dir.glob("*.jsonl"))
    if not logs:
        print(f"no logs under {log_dir}", file=sys.stderr)
        return 1

    by_workflow = Counter(workflow_of(p) for p in logs)
    rows = []

    for path in logs:
        wf = workflow_of(path)
        envelope, turns, unparseable = read_log(path)
        result = "" if envelope is None else (envelope.get("result") or "")
        console = "\n".join(turns)
        if wf in VERDICT_WORKFLOWS:
            pattern_kind = "verdict"
            strict, loose = STRICT_VERDICT, LOOSE_VERDICT
        elif wf in ISSUE_ALTERNATIVE_WORKFLOWS:
            pattern_kind = "pr_or_issue_url"
            strict = loose = PR_OR_ISSUE_URL
        elif wf in PATTERNLESS_WORKFLOWS:
            # Recorded, never scored. `None` is distinct from "did not match" and
            # the consumer must not collapse them — a workflow with no contract
            # cannot miss one.
            pattern_kind = "none"
            strict = loose = None
        else:
            pattern_kind = "pr_url"
            strict = loose = PR_URL

        rows.append(
            {
                "log": path.name,
                "workflow": wf,
                "pattern": pattern_kind,
                # `result` key absent is DISTINCT from result present-but-empty
                # — E1 measured that every error subtype drops the key entirely.
                "envelope": "missing" if envelope is None else "present",
                "result_key": (
                    "absent"
                    if envelope is None or "result" not in envelope
                    else "present"
                ),
                "subtype": None if envelope is None else envelope.get("subtype"),
                "strict_result": None if strict is None else bool(strict.search(result)),
                "loose_result": None if loose is None else bool(loose.search(result)),
                "strict_console": None if strict is None else bool(strict.search(console)),
                "loose_console": None if loose is None else bool(loose.search(console)),
                "strict_matches_console": None if strict is None else sum(1 for _ in strict.finditer(console)),
                "last_strict_result": None if strict is None else last_whole_match(strict, result),
                "unparseable_lines": unparseable,
            }
        )

    print(f"# corpus: {len(logs)} JSONL under {log_dir}")
    for wf, n in sorted(by_workflow.items()):
        print(f"#   {wf}: {n}")
    in_flight = [r["log"] for r in rows if r["envelope"] == "missing"]
    if in_flight:
        # A log with no `result` event is most often the CURRENTLY-RUNNING
        # dispatch — including the one invoking this tool. It is not a fleet
        # failure and must not be counted as a strict-negative without saying
        # so; E5 recorded one of these as a "truncated log" before it finished.
        print(f"# no result envelope ({len(in_flight)}) — in-flight or truncated,")
        print("#   adjudicate each before counting it as a miss:")
        for name in in_flight:
            print(f"#     {name}")
    unscored = [r["log"] for r in rows if r["pattern"] == "none"]
    if unscored:
        # Named explicitly: a silently-excluded row is indistinguishable from a
        # row that passed, which is the failure this whole tool exists to avoid.
        print(f"# NOT SCORED ({len(unscored)}) — the workflow declares no")
        print("#   COMPLETION_PATTERN, so it has no contract to miss:")
        for name in unscored:
            print(f"#     {name}")
    total_unparseable = sum(r["unparseable_lines"] for r in rows)
    print(f"# unparseable JSONL lines across corpus: {total_unparseable}")
    print()
    print(json.dumps(rows, indent=1))
    return 0


if __name__ == "__main__":
    default = Path(__file__).resolve().parents[3] / ".claude" / "logs"
    raise SystemExit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else default))

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

  1. CHILD-SIDE, over the result envelope. `run-claude.sh:201-204` extracts
     `.result` from the JSONL and applies `grep -qE "$COMPLETION_PATTERN"`.
     This is the write-time gate that already exists.
  2. PARENT-SIDE, over the child's console output. `build.sh:277` and
     `build-minor.sh:281` apply `grep -oE '^VERDICT: …' | tail -1` to the
     tee'd stdout+stderr of the child process — a WIDER surface that includes
     every streamed assistant message, not just the final result.

Surface 2's input is not archived; the JSONL is. What IS reconstructible from
the JSONL is the union of assistant text turns, which is what the console
carries, so this script reconstructs it and flags where the two surfaces differ.

Usage:  python3 scripts/helpers/measure/replay_completion_predicate.py [LOG_DIR]
        (LOG_DIR defaults to <repo root>/.claude/logs)
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

# Verbatim from review-pr.sh:186 / routing.py:43 / review_pr_helper.py:70.
STRICT_VERDICT = re.compile(
    r"^VERDICT: (MERGE|HOLD - (redispatch|needs-assistance))$", re.MULTILINE
)
# Deliberately looser, per E5's stated adjudication procedure: unanchored, and
# tolerant of the markdown emphasis and leading whitespace a model actually
# emits. The DIFFERENCE between the two sets is what gets adjudicated by hand.
LOOSE_VERDICT = re.compile(r"VERDICT:?\s*\**\s*(MERGE|HOLD)", re.IGNORECASE)

# Verbatim from build.sh:198 / build-minor.sh:202 and the six workflows that
# declare it as their COMPLETION_PATTERN.
PR_URL = re.compile(r"https://github\.com/[^ )]+/pull/[0-9]+")

VERDICT_WORKFLOWS = ("review-pr",)


def workflow_of(path: Path) -> str:
    """`review-pr-20260808-110753.jsonl` -> `review-pr`."""
    return re.sub(r"-\d{8}-\d{6}$", "", path.stem)


def read_log(path: Path) -> tuple[dict | None, list[str]]:
    """Return (result envelope or None, assistant text turns in order)."""
    envelope, turns = None, []
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            # A truncated final line is itself an observation, not an error to
            # swallow silently — the caller sees it as a missing envelope.
            continue
        if not isinstance(ev, dict):
            continue
        if ev.get("type") == "result":
            envelope = ev
        elif ev.get("type") == "assistant":
            for block in ev.get("message", {}).get("content", []) or []:
                if isinstance(block, dict) and block.get("type") == "text":
                    turns.append(block.get("text", ""))
    return envelope, turns


def main(log_dir: Path) -> int:
    logs = sorted(log_dir.glob("*.jsonl"))
    if not logs:
        print(f"no logs under {log_dir}", file=sys.stderr)
        return 1

    by_workflow = Counter(workflow_of(p) for p in logs)
    rows = []

    for path in logs:
        wf = workflow_of(path)
        envelope, turns = read_log(path)
        result = "" if envelope is None else (envelope.get("result") or "")
        console = "\n".join(turns)
        pattern_kind = "verdict" if wf in VERDICT_WORKFLOWS else "pr_url"
        strict = STRICT_VERDICT if pattern_kind == "verdict" else PR_URL
        loose = LOOSE_VERDICT if pattern_kind == "verdict" else PR_URL

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
                "strict_result": bool(strict.search(result)),
                "loose_result": bool(loose.search(result)),
                "strict_console": bool(strict.search(console)),
                "loose_console": bool(loose.search(console)),
                "strict_matches_console": len(strict.findall(console)),
                "last_strict_result": (
                    strict.findall(result)[-1] if strict.search(result) else None
                ),
            }
        )

    print(f"# corpus: {len(logs)} JSONL under {log_dir}")
    for wf, n in sorted(by_workflow.items()):
        print(f"#   {wf}: {n}")
    print()
    print(json.dumps(rows, indent=1))
    return 0


if __name__ == "__main__":
    default = Path(__file__).resolve().parents[3] / ".claude" / "logs"
    raise SystemExit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else default))

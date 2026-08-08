#!/usr/bin/env python3
"""Replay the `pr_review:` blocks archived in PR comments.

WHY THIS IS KEPT: Phase 5 of the Memory Management Framework builds a computed
convergence signal whose predicate is "the finding-id delta between consecutive
passes is empty". Whether that predicate ever fires is a rate over a corpus that
grows with every reviewed PR, and Phase 5 depends outright on the stable-id
convention holding. Both are re-measurable, not one-shot.

Measured for Memory Management Framework Phase 1, experiment E7 (and E3's
verdict-vs-PR-state cross-tab, which reads the same corpus).

Reads only `gh` output. Writes nothing.

Usage:  python3 scripts/helpers/measure/replay_pr_review_blocks.py [OWNER/REPO]
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

DEFAULT_REPO = "helloskyy-io/Claude-Dot-Files"

# The block is posted inside a ```yaml fence by review-pr.sh Stage 5. Parsed by
# regex rather than a YAML library on purpose: the archived blocks predate any
# schema and some are hand-edited, so a strict parser would drop exactly the
# malformed ones this experiment most wants to see counted.
FENCE = re.compile(r"```ya?ml\s*\n(pr_review:.*?)\n```", re.DOTALL)
PASS = re.compile(r"^\s*pass:\s*(\d+)", re.MULTILINE)
ATTEMPT = re.compile(r"^\s*attempt:\s*(\d+)", re.MULTILINE)
VERDICT = re.compile(r"^\s*verdict:\s*([A-Za-z]+)", re.MULTILINE)
CONVERGED = re.compile(r"^\s*converged:\s*(true|false)", re.MULTILINE)
# `- id: <slug>` under `findings:`; two-space and four-space indents both occur.
FINDING_ID = re.compile(r"^\s*-\s*id:\s*([^\s#]+)", re.MULTILINE)


def gh(*args: str) -> str:
    return subprocess.run(
        ["gh", *args], capture_output=True, text=True, check=True
    ).stdout


def main(repo: str) -> int:
    prs = json.loads(
        gh(
            "pr", "list", "--repo", repo, "--state", "all", "--limit", "300",
            "--json", "number,title,state,mergedAt",
        )
    )
    out = []
    for pr in sorted(prs, key=lambda p: p["number"]):
        n = pr["number"]
        data = json.loads(
            gh("pr", "view", str(n), "--repo", repo, "--json", "comments")
        )
        blocks = []
        for c in data.get("comments", []):
            for body in FENCE.findall(c.get("body", "")):
                p = PASS.search(body)
                v = VERDICT.search(body)
                cv = CONVERGED.search(body)
                at = ATTEMPT.search(body)
                blocks.append(
                    {
                        "pass": int(p.group(1)) if p else None,
                        "attempt": int(at.group(1)) if at else None,
                        "verdict": v.group(1) if v else None,
                        # `None` means the key is absent — DISTINCT from false,
                        # because absence dates the block to before the flag
                        # shipped and that is what makes a denominator honest.
                        "converged": (cv.group(1) == "true") if cv else None,
                        "finding_ids": FINDING_ID.findall(body),
                        "created": c.get("createdAt"),
                    }
                )
        blocks.sort(key=lambda b: (b["pass"] if b["pass"] is not None else 0, b["created"] or ""))
        out.append(
            {
                "pr": n,
                "title": pr["title"],
                "state": pr["state"],
                "merged": pr["mergedAt"] is not None,
                "n_blocks": len(blocks),
                "blocks": blocks,
            }
        )
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_REPO))

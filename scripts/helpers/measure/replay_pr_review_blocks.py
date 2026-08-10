#!/usr/bin/env python3
"""Replay the `pr_review:` blocks archived in PR comments.

WHY THIS IS KEPT: Phase 5 of the Memory Management Framework builds a computed
convergence signal whose predicate is "the finding-id delta between consecutive
passes is empty". Whether that predicate ever fires is a rate over a corpus that
grows with every reviewed PR, and Phase 5 depends outright on the stable-id
convention holding. Both are re-measurable, not one-shot.

Measured for Memory Management Framework Phase 1, experiment E7 (and E3's
verdict-vs-PR-state cross-tab, which reads the same corpus).

THE BLOCK IS CUMULATIVE, AND EVERY DELTA COMPUTED OVER IT MUST ACCOUNT FOR THAT.
`review-pr.sh:221` instructs each pass to reuse every prior finding's id slug
verbatim, and the archived blocks do: pass N restates every id pass N-1 carried
and updates its `disposition` in place (`hold` -> `fixed`/`deferred`/`rejected`).
So the id set is monotonically growing BY CONSTRUCTION. Two consequences a
consumer of this tool must not get wrong:

  * "no id was ever dropped" is a property of the reporting shape, not a
    measurement of reviewer behaviour. It cannot come out any other way.
  * a delta over ALL ids therefore cannot go empty either. The subset that
    carries meaning is the OPEN one -- findings whose `disposition` is still
    `hold` -- which is why this tool extracts `disposition` per finding rather
    than ids alone.

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
# One finding entry: its id, plus everything up to the next `- id:` (or EOF).
# Per-finding fields are read from that span so a `disposition:` belonging to
# finding N is never attributed to finding N-1.
#
# `[ \t]` rather than `\s`, matching `review_pr_helper._FINDING_ITEM` BYTE FOR
# BYTE — the gate in `test_exit_record.py` compares the two patterns and this is
# the spelling both sides settled on. `\s` also matches a newline, which lets
# the anchor and the lookahead straddle a blank line; the two are equivalent on
# every archived block (verified by re-running this module's own tests over the
# archive) and only one of them is defensible.
FINDING_ENTRY = re.compile(
    r"^[ \t]*-[ \t]*id:[ \t]*([^\s#]+)(.*?)(?=^[ \t]*-[ \t]*id:|\Z)",
    re.MULTILINE | re.DOTALL,
)
DISPOSITION = re.compile(r"^[ \t]*disposition:[ \t]*([^\s#]+)", re.MULTILINE)
CATEGORY = re.compile(r"^\s*category:\s*([^\s#]+)", re.MULTILINE)
# The `findings:` mapping value — from the key to the next key at the SAME
# indent, or the end of the block. `- id:` IS NOT UNIQUE TO A FINDING, and the
# shipped prompt is what makes it not unique: `disposition.md:292` gives the
# child a `dispatch_context: |` block scalar whose documented content is "which
# findings to fix", and `:295` a `precheck: |` beside it. Both are free text in
# the same block, after `findings:`. A reviewer enumerating findings there —
# which the prompt asks for — injects entries indistinguishable from real ones,
# and they carry no `disposition:`, so `open_ids` counts every one of them OPEN
# and the convergence rate this tool measures is silently wrong.
#
# BYTE-IDENTICAL to `review_pr_helper._FINDINGS_SECTION` and paired in
# `SHARED_KIND_ONE_PATTERNS`, because both readers now anchor: the live path's
# render↔record invariant and this tool's denominator would otherwise disagree
# about what a finding is, which is the drift that gate exists to catch.
#
# NUMBER-NEUTRAL WHEN INTRODUCED, and that was measured rather than assumed:
# 0 of the 27 archived blocks across 14 PRs carry a `- id:` outside `findings:`,
# so no published figure moves. It bounds what a future re-run can conclude.
FINDINGS_SECTION = re.compile(
    r"^([ \t]*)findings:[ \t]*$(.*?)(?=^\1[A-Za-z_][A-Za-z0-9_]*:|\Z)",
    re.MULTILINE | re.DOTALL,
)


def findings_section(block: str) -> str:
    """The block's `findings:` value, or `""` when it declares none."""
    match = FINDINGS_SECTION.search(block)
    return match.group(2) if match else ""


# The dispositions that mean "this finding needs nothing further". Measured
# vocabulary across the archive (all 195 archived findings carry one):
#   hold 37 · fixed 74 · deferred 58 · rejected 21 · noted 3 · escalated 2
# `hold` and `escalated` both leave work outstanding, which is why this is
# spelled as a CLOSED set rather than as `== "hold"`: a hold-only reading would
# score the two `escalated` findings as closed, and that sixth value was not in
# the vocabulary when this measurement was first taken.
# NOTE there is no `severity` field on ANY of the 195; `category` (8 values) and
# `disposition` (6) are what the fleet actually emits.
CLOSED_DISPOSITIONS = frozenset({"fixed", "deferred", "rejected", "noted"})


def open_ids(finding_entries: list[dict]) -> set[str]:
    """The ids still carrying outstanding work in one block.

    This -- not the full id set -- is what a convergence delta must be computed
    over, because the full set cannot shrink (see the module docstring).

    UNKNOWN COUNTS AS OPEN, deliberately. A finding whose `disposition` is
    absent or carries a value this vocabulary does not know is a finding whose
    state nobody established, and the failure mode of the other choice is the
    expensive one: an unrecognised disposition would empty the open set and
    report convergence that was never observed. Every archived finding carries
    a known disposition today, so this changes no current number -- it bounds
    what a future re-run can silently conclude.
    """
    return {
        f["id"]
        for f in finding_entries
        if f.get("disposition") not in CLOSED_DISPOSITIONS
    }


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
                findings = []
                section = findings_section(body)
                for m in FINDING_ENTRY.finditer(section):
                    span = m.group(2)
                    d = DISPOSITION.search(span)
                    cat = CATEGORY.search(span)
                    findings.append(
                        {
                            "id": m.group(1),
                            # `None` means the finding carried no such key —
                            # kept distinct from any value so a block predating
                            # the field is not silently counted as closed.
                            "disposition": d.group(1) if d else None,
                            "category": cat.group(1) if cat else None,
                        }
                    )
                blocks.append(
                    {
                        "pass": int(p.group(1)) if p else None,
                        "attempt": int(at.group(1)) if at else None,
                        "verdict": v.group(1) if v else None,
                        # `None` means the key is absent — DISTINCT from false,
                        # because absence dates the block to before the flag
                        # shipped and that is what makes a denominator honest.
                        "converged": (cv.group(1) == "true") if cv else None,
                        "finding_ids": FINDING_ID.findall(section),
                        "findings": findings,
                        # The delta that can actually go empty. The full
                        # `finding_ids` set cannot — see the module docstring.
                        "open_ids": sorted(open_ids(findings)),
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

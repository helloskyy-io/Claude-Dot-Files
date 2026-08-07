"""The routing vocabulary every parent branches on — declared ONCE.

Promoted here per §10.1 rule 3: three consumers (`build`, `review_pr`,
`plan_project`), and the promotion rule is consumer count, never taste.

WHY IT MOVED. `Verdict` and its parser were typed twice — byte-identical
members, byte-identical regex, differing only in docstring prose — and issue #34
recorded the consequence: the copy that decides whether a PR MERGES had zero
tests while its twin had twenty. `build` bridged the two with
`Verdict(result.verdict.value)`, converting an enum into an identical enum,
which is the `derive != declare` seam failing in plain sight. Adding a third
parent would have made it three copies.

This module is deliberately dependency-free — no I/O, no imports from siblings —
so any workflow may import it without pulling in a family it does not belong to.
"""

from __future__ import annotations

import re
from enum import Enum

__all__ = ["Verdict", "MAX_LOOPS", "parse_verdict", "should_loop_back", "pr_number_from_url"]


class Verdict(str, Enum):
    """The routing token `review-pr` emits on its terminal line.

    THIS IS THE INTERFACE between the disposition child and any caller. The
    child aggregates per-finding `hold_kind` values into one token so a caller
    never re-derives a judgement the reviewer already made.
    """

    MERGE = "MERGE"
    HOLD_REDISPATCH = "HOLD - redispatch"
    HOLD_NEEDS_ASSISTANCE = "HOLD - needs-assistance"


# Anchored and exhaustive: an unanchored match would find the token inside prose
# quoting a previous verdict, and a run that discusses its own history would
# route on the sentence it wrote about itself.
_VERDICT = re.compile(
    r"^VERDICT: (MERGE|HOLD - (?:redispatch|needs-assistance))$",
    re.MULTILINE,
)

# EXACTLY ONE loop-back, for every parent. Not a knob, and deliberately not
# configurable. Self-correction plateaus at roughly 3-5 passes: the same model
# carries the same blind spots, and past the plateau it stops correcting and
# starts justifying. Watched directly on this fleet — one PR reached EIGHT
# review passes, and pass 8 reviewed the same tree as pass 7 with no commits
# between them. Counting correction passes across the PIPELINE rather than
# within any one child, one loop-back lands at four, inside the band.
MAX_LOOPS = 1


def parse_verdict(output: str) -> tuple[Verdict, bool]:
    """Return (verdict, was_parseable).

    FAILS SAFE TO THE HUMAN BRANCH. An unparseable verdict becomes
    HOLD_NEEDS_ASSISTANCE, never MERGE and never a redispatch — the routing
    contract's rule is that ambiguity routes to the branch requiring a person,
    because the cost of wrongly merging is unbounded and the cost of wrongly
    asking is one message.

    The LAST match wins: a disposition comment may quote an earlier pass's
    verdict while reaching a different one of its own.

    The boolean is returned rather than logged here so the caller can report the
    degradation; a helper that printed would not be pure.
    """
    matches = _VERDICT.findall(output)
    if not matches:
        return Verdict.HOLD_NEEDS_ASSISTANCE, False
    return Verdict(matches[-1]), True


def should_loop_back(verdict: Verdict, loops_used: int) -> bool:
    """Only a redispatch verdict loops, and only while the budget holds.

    needs-assistance never loops at any count: a human ruling is not something
    more passes can produce, so spending them is pure waste.
    """
    return verdict is Verdict.HOLD_REDISPATCH and loops_used < MAX_LOOPS


def pr_number_from_url(url: str) -> str:
    """The PR number a child reported, as its caller's handoff key.

    Raises rather than returning a sentinel: a parent that cannot identify the
    PR cannot review it, and a silent empty string would surface later as a
    confusing `gh` error against PR number ''.
    """
    match = re.search(r"/pull/(\d+)", url)
    if not match:
        raise ValueError(
            f"no PR number in child output: {url!r}. The child's completion "
            f"contract requires a PR URL on its final line."
        )
    return match.group(1)

"""Pure compiler for the review-pr workflow — Layer 2.

BINDING: no I/O. No subprocess, no network, no filesystem read at call time, no
clock. Every function is a deterministic map from inputs to a value.

Input models live here rather than in a separate `review_pr_inputs.py`, per
temporal_standard.md §11.2: models live in the helper by default and extract
only when the helper grows unwieldy. Presence or absence is not a conformance
signal.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class Verdict(str, Enum):
    """review-pr's terminal routing token.

    The caller branches on this rather than re-deriving a judgement the
    reviewer already made.
    """

    MERGE = "MERGE"
    HOLD_REDISPATCH = "HOLD - redispatch"
    HOLD_NEEDS_ASSISTANCE = "HOLD - needs-assistance"


class ReviewType(str, Enum):
    """What KIND of artifact is under review.

    Explicit, never inferred — same doctrine run-claude.sh enforces for
    --model: identity is an input, not something derived from context. Commit 2
    adds the type-specific criteria; commit 1 defines the axis and defaults to
    BUILD so behaviour is unchanged.
    """

    BUILD = "build"
    RESEARCH = "research"
    PLANNING = "planning"


@dataclass(frozen=True)
class ReviewInput:
    pr_number: str
    repo_target: str | None = None
    verbose: bool = False
    review_type: ReviewType = ReviewType.BUILD

    def __post_init__(self) -> None:
        # Fail loud at the boundary: a non-numeric PR number reaches `gh` as a
        # confusing error several layers down.
        if not str(self.pr_number).isdigit():
            raise ValueError(f"--pr must be a number, got {self.pr_number!r}")


@dataclass
class ReviewResult:
    pr_number: str
    verdict: Verdict
    this_pass: int
    parseable: bool = True
    notes: list[str] = field(default_factory=list)

    @property
    def ready_to_merge(self) -> bool:
        return self.verdict is Verdict.MERGE


# Anchored and exhaustive: an unanchored match would find the token inside prose
# discussing it. MULTILINE because the line sits in a stream of output.
_VERDICT = re.compile(
    r"^VERDICT: (MERGE|HOLD - (?:redispatch|needs-assistance))$",
    re.MULTILINE,
)

# The completion contract. `exit 0` means finished only if output matches this.
COMPLETION_PATTERN = r"^VERDICT: (MERGE|HOLD - (redispatch|needs-assistance))$"

MODEL_KEY = "review-pr"


def parse_verdict(output: str) -> tuple[Verdict, bool]:
    """Return (verdict, was_parseable).

    FAILS SAFE TO THE HUMAN BRANCH. An unparseable verdict becomes
    HOLD_NEEDS_ASSISTANCE — never MERGE, never a redispatch. The routing
    contract's rule: ambiguity routes to the branch requiring a person, because
    wrongly merging costs an unbounded amount and wrongly asking costs one
    message.
    """
    matches = _VERDICT.findall(output)
    if not matches:
        return Verdict.HOLD_NEEDS_ASSISTANCE, False
    return Verdict(matches[-1]), True


def pass_numbers(prior_pass_count: int) -> tuple[int, int]:
    """(this_pass, prior_pass) from the count of prior disposition comments.

    Pass numbering is 1-based; prior_pass is 0 on a fresh PR, which the prompt
    reads as "no prior pass to reconcile against."
    """
    if prior_pass_count < 0:
        raise ValueError(f"prior pass count cannot be negative: {prior_pass_count}")
    return prior_pass_count + 1, prior_pass_count


def render_prompt(template: str, *, pr_number: str, pr_branch: str,
                  this_pass: int, prior_pass: int, headless_guard: str) -> str:
    """Substitute the prompt's five placeholders.

    Deliberately NOT str.format() or an f-string: the prompt is 283 lines of
    markdown containing JSON examples, yaml blocks and shell snippets, all full
    of literal braces. Brace-based templating would either raise or silently
    interpolate them. Explicit replacement of `${NAME}` has no such surface —
    the same reasoning that moved the prompt out of a shell string.
    """
    values = {
        "PR_NUMBER": str(pr_number),
        "PR_BRANCH": pr_branch,
        "THIS_PASS": str(this_pass),
        "PRIOR_PASS": str(prior_pass),
        "HEADLESS_EXECUTION_GUARD": headless_guard,
    }
    rendered = template
    for name, value in values.items():
        rendered = rendered.replace("${" + name + "}", value)

    # An unsubstituted placeholder is a silent defect — it reaches the model as
    # literal `${FOO}` and reads as an instruction about a variable. Fail loud.
    leftover = re.findall(r"\$\{[A-Z_]+\}", rendered)
    if leftover:
        raise ValueError(f"unsubstituted prompt placeholders: {sorted(set(leftover))}")
    return rendered

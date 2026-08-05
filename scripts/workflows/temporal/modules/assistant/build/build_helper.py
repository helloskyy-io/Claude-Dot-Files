"""Pure compiler for the build workflow — Layer 2.

BINDING PROPERTY: nothing in this module performs I/O. No subprocess, no
network, no filesystem, no clock. Every function is a deterministic map from
inputs to a value, which is what makes it unit-testable with no mocks and what
makes the workflow above it replayable once Temporal arrives.

Everything here was inline in `build.sh`. The bash version was already
correct about the boundary — its own comment says the verdict parsing and URL
extraction "deliberately stay HERE ... pure string to decision, no I/O, and they
ARE the if/then a parent exists to hold." This module is that paragraph made
executable.
"""

from __future__ import annotations

import re

from .build_inputs import ChildResult, BuildInput, Verdict

# The draft child's completion contract: it must open (or update) a PR and print
# its URL. A run that produced no URL did not finish, whatever it exited with.
_PR_URL = re.compile(r"https://github\.com/[^\s)]+/pull/(\d+)")

# review-pr's terminal line. Anchored and exhaustive on purpose: an unanchored
# match would find the token inside prose discussing it.
_VERDICT = re.compile(
    r"^VERDICT: (MERGE|HOLD - (?:redispatch|needs-assistance))$",
    re.MULTILINE,
)

# Exactly one loop-back. Not a knob, and deliberately not configurable — see
# build_workflow for why the bound comes from the plateau rather than a budget.
MAX_LOOPS = 1


def extract_pr_url(output: str) -> str | None:
    """Last PR URL in the child's output, or None.

    Last rather than first: a child may mention an existing PR before opening
    the one it is responsible for.
    """
    matches = [m.group(0) for m in _PR_URL.finditer(output)]
    return matches[-1] if matches else None


def pr_number_from_url(url: str) -> str:
    """The trailing number. Raises rather than guessing on a malformed URL."""
    match = _PR_URL.search(url)
    if not match:
        raise ValueError(f"not a PR URL: {url!r}")
    return match.group(1)


def parse_verdict(output: str) -> tuple[Verdict, bool]:
    """Return (verdict, was_parseable).

    FAILS SAFE TO THE HUMAN BRANCH. An unparseable verdict becomes
    HOLD_NEEDS_ASSISTANCE, never MERGE and never a redispatch — the routing
    contract's rule is that ambiguity routes to the branch requiring a person,
    because the cost of wrongly merging is unbounded and the cost of wrongly
    asking is one message.

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


def child_args(task: BuildInput) -> list[str]:
    """Flags every child receives. Flags first, positional last.

    Positional-in-the-middle gets stepped on by terminal line-wrap, which is why
    the convention exists.
    """
    args: list[str] = []
    if task.repo_target:
        args += ["--repo", task.repo_target]
    if task.verbose:
        args.append("--verbose")
    return args


def task_args(task: BuildInput) -> list[str]:
    """The task itself, as the child expects to receive it.

    --task-file bypasses shell parsing entirely, so quotes, newlines and
    backticks pass through literally. Preferred for anything multi-paragraph.
    """
    if task.task_file:
        return ["--task-file", task.task_file]
    return [task.description or ""]


def draft_args(task: BuildInput) -> list[str]:
    args = child_args(task)
    if task.pr_number:
        args += ["--pr", task.pr_number]
    return args + task_args(task)


def refine_args(task: BuildInput, pr: str, *, correction_pass: bool, ci_unsettled: bool) -> list[str]:
    args = child_args(task)
    if correction_pass:
        args.append("--correction-pass")
    if ci_unsettled:
        args.append("--ci-unsettled")
    return args + ["--pr", pr] + task_args(task)


def review_args(task: BuildInput, pr: str) -> list[str]:
    return child_args(task) + ["--pr", pr]


def draft_handoff(result: ChildResult) -> str:
    """Validate the draft child's completion contract and return its PR URL.

    Raises with the operator-facing reason. The bash version printed and exited;
    raising lets the workflow decide how to report, which is the layer that
    should own that.
    """
    if not result.ok:
        raise RuntimeError(
            "build-draft FAILED — stopping before refine. Nothing was reviewed."
        )
    url = extract_pr_url(result.output)
    if not url:
        raise RuntimeError(
            "build-draft produced no PR URL — cannot hand off to refine. "
            "The draft step must open (or update) a PR and print its URL as its final line."
        )
    return url

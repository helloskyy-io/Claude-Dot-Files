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

from .. import routing
from .build_inputs import ChildResult, BuildInput, Verdict

# The draft child's completion contract: it must open (or update) a PR and print
# its URL. A run that produced no URL did not finish, whatever it exited with.
_PR_URL = re.compile(r"https://github\.com/[^\s)]+/pull/(\d+)")

# review-pr's terminal line. Anchored and exhaustive on purpose: an unanchored
# match would find the token inside prose discussing it.


def extract_pr_url(output: str) -> str | None:
    """Last PR URL in the child's output, or None.

    Last rather than first: a child may mention an existing PR before opening
    the one it is responsible for.
    """
    matches = [m.group(0) for m in _PR_URL.finditer(output)]
    return matches[-1] if matches else None


# Routing vocabulary lives in `..routing` — ONE definition, three consumers
# (§10.1). Re-exported under the names this module already published so no
# caller changes, and so there is exactly one place a verdict is parsed.
pr_number_from_url = routing.pr_number_from_url
parse_verdict = routing.parse_verdict
should_loop_back = routing.should_loop_back
MAX_LOOPS = routing.MAX_LOOPS


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

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

from .. import routing
from .build_inputs import ChildResult, BuildInput, Verdict

# The draft child's completion contract: it must open (or update) a PR and print
# its URL. A run that produced no URL did not finish, whatever it exited with.
#
# RE-EXPORTED FROM `..routing`, NOT RE-TYPED. This file held a byte-identical
# anchored copy of the pattern beside a re-export of the UNANCHORED
# `pr_number_from_url` — two strengths of one address in one module. Issue #34
# was the same shape for `parse_verdict` and was closed on a half-fix; the gate
# for this one is on the class (`test_the_pr_url_address_is_declared_exactly_once
# _in_the_whole_tree`), not on the two copies that were found.


# Routing vocabulary lives in `..routing` — ONE definition, three consumers
# (§10.1). Re-exported under the names this module already published so no
# caller changes, and so there is exactly one place a verdict is parsed.
extract_pr_url = routing.extract_pr_url
pr_identity = routing.pr_identity
pr_number_from_url = routing.pr_number_from_url
parse_verdict = routing.parse_verdict
should_loop_back = routing.should_loop_back
MAX_LOOPS = routing.MAX_LOOPS


def finality_note(loops_left: int) -> str:
    """What a correction pass is told about how much runway is behind it.

    COUNTED, NOT ASSERTED, and this exists because the assertion was false. Both
    refine prompts told the model *"This is the last automated pass"* on every
    correction pass, while `MAX_LOOPS` has been 3 since `b89f7f5` — so on passes
    1 and 2 of 3 the model disposed its findings believing no further pass would
    run. That is a false statement changing MODEL behaviour, not merely operator
    perception, and it is the reason this is a function rather than a constant
    string: the number is read from the caller's own loop state.

    The instruction does not soften when passes remain. A finding left for a
    later pass costs a full review cycle to rediscover, and the run holding the
    context is the cheap place to close it — which is true whether it is the last
    pass or the first.
    """
    if loops_left <= 0:
        return ("**This is the last automated pass**, so anything you leave as an "
                "instance leaves with it.")
    passes = "pass" if loops_left == 1 else "passes"
    return (f"**{loops_left} further automated {passes} may run after this one, and "
            f"you must not plan around {'it' if loops_left == 1 else 'them'}** — a "
            f"correction cycle costs a full review pass to rediscover what you had "
            f"loaded, so anything you leave as an instance is paid for twice.")


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

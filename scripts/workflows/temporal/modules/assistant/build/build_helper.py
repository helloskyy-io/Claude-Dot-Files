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
from .build_activities import POLICY_PATH, CiVerdict
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


def ci_gate(state: CiVerdict, extra: list[str], *, pr: str,
            repo_target: str | None) -> tuple[Verdict | None, list[str]]:
    """Map a settled CI read to a HOLD (or None) plus the operator-facing notes.

    PURE, AND SHARED BY BOTH BUILD PARENTS, which is the whole reason it is here
    rather than inline. The cascade below lived in `build_workflow` only, so
    `build_minor` reached `review-pr` with the CI verdict never read — the light
    tier could return MERGE on a red tree, which is exactly the hole removing
    branch protection opened and which this gate was written to close. One parent
    got the gate and its sibling was never updated: a whole block present in one
    copy and absent from its sibling, the reportable drift pattern under
    `tests/unit/fork_vs_parameterize.py` S3, in the category that module's own
    contract calls `operational-safety` — *a cheaper run is not a run permitted
    to be less careful*.

    WHY THE GATE IS IN A PARENT AND NOT A PROMPT: telling a review agent to check
    and withhold MERGE is a convention, and an agent can reason past a convention
    — "unrelated failure, proceeding" is the shape being guarded against. Here the
    agent never gets a verdict to give.

    HOLD, NEVER `exit 1`: killing the run discards a diff two passes just built.
    HOLD keeps the work and hands the failure back in the format the pipeline
    already consumes.

    Returns `(None, notes)` when the gate does not stop the run — the notes may
    still be non-empty, because two non-blocking states are reported out loud
    rather than passed silently.
    """
    where = f" in {repo_target}" if repo_target else ""
    if state is CiVerdict.UNREADABLE_CHECKS:
        # NEEDS_ASSISTANCE, NOT REDISPATCH, AND THE DIFFERENCE IS THE WHOLE
        # POINT. A gate that did not RUN is usually a conflicted PR, and sending
        # an engineer back to resolve it is right. CI that cannot be READ is an
        # environment failure — a redispatch cannot fix it and can only spend the
        # loop budget rediscovering that. Which is exactly what happened: a failed
        # `gh pr checks` read as GATE_DID_NOT_RUN and PR #92 rebuilt three times
        # while it was OPEN, MERGEABLE and green throughout.
        return Verdict.HOLD_NEEDS_ASSISTANCE, [
            f"CI GATE: HOLD — the CI status of PR {pr} could not be READ{where} "
            "(`gh pr checks` returned nothing parseable). This is NOT the same "
            "as the gate not running, and a redispatch cannot fix it: check `gh "
            "auth status`, rate limits, and network. review-pr was NOT dispatched."
        ]

    if state is CiVerdict.UNREADABLE_POLICY:
        # A declaration that EXISTS and cannot be read is a different fact from
        # no declaration, and collapsing them is how the skip path becomes the
        # new exit. Same discipline the JSON parse already follows: unreadable
        # input fails into the state that STOPS.
        return Verdict.HOLD_NEEDS_ASSISTANCE, [
            f"CI GATE: HOLD — {POLICY_PATH} exists and could not be parsed. "
            "A broken declaration is not the same as no declaration; fix the file. "
            "review-pr was NOT dispatched."
        ]

    notes: list[str] = []
    # GATE_DID_NOT_RUN is excluded because its `extra` carries the names of the
    # gate that is ABSENT, not of checks that ran. Reading it here reported
    # `suite` as unclassified in the same breath as the branch below reported it
    # as declared blocking — two contradictory lines from one run, on 2026-08-14.
    if extra and state not in (CiVerdict.RED, CiVerdict.GATE_DID_NOT_RUN):
        # A check that ran and is declared NEITHER blocking nor advisory is the
        # third state the Testing Standard says does not exist. Reported by name,
        # never silently gated — a check the repo has not classified must not halt
        # the fleet, and must not hide either.
        notes.append(
            f"CI GATE: UNDECLARED CHECKS — {', '.join(extra)} ran and appear in neither "
            f"the blocking nor the advisory list of {POLICY_PATH}. The Testing Standard "
            "admits no third state; classify them."
        )

    if state is CiVerdict.RED:
        notes.append(
            f"CI GATE: HOLD — blocking checks failed: {', '.join(extra)}. "
            "review-pr was NOT dispatched; a red tree cannot produce a MERGE verdict. "
            "Fix the checks and redispatch; the diff is intact on the branch."
        )
        return Verdict.HOLD_REDISPATCH, notes

    if state is CiVerdict.GATE_DID_NOT_RUN:
        notes.append(
            f"CI GATE: HOLD — {POLICY_PATH} declares {', '.join(extra)} blocking, and "
            f"NONE of them reported on PR {pr}{where}. The gate exists and produced "
            "nothing, which is not a pass. review-pr was NOT dispatched. The usual "
            "cause is a CONFLICTED PR: `pull_request` workflows run against the merge "
            "ref, GitHub cannot compute one for a conflicted PR, so no run is created "
            "at all — check `git ls-remote origin refs/pull/<N>/merge` against the "
            "current head. Resolve, push, and let the checks run before redispatching; "
            "the diff is intact on the branch."
        )
        return Verdict.HOLD_REDISPATCH, notes

    if state is CiVerdict.NO_CHECKS:
        # NOT green, and named rather than silent. A repo with no workflows, or a
        # PR whose workflows were all path-filtered out, reports nothing — and
        # "no checks reported" reading as pass is how a filtered gate would get
        # here. The run says so out loud; it does not stop on it, because a repo
        # may legitimately have none.
        notes.append(
            f"CI GATE: SKIPPED — no check declared blocking in {POLICY_PATH} "
            f"reported on PR {pr}{where}. This is NOT a pass. Either the repo has "
            "no such gate, or its workflows were filtered out of this change."
        )

    return None, notes

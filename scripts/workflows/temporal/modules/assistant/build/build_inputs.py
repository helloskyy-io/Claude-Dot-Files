"""Typed inputs and results for the build workflow.

Layer boundary note: these are plain dataclasses with no Temporal import. Under
the port's step 3 they become the payloads on `execute_activity` calls; today
they are ordinary values. Nothing here changes when Temporal arrives, which is
the point of defining them now.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .. import routing
from enum import Enum


# ONE definition, in `..routing`. It was typed here AND in review_pr_helper --
# byte-identical members, byte-identical parser -- and build bridged the two
# with `Verdict(result.verdict.value)`, converting an enum into an identical
# enum. Issue #34 recorded the cost: the copy deciding whether a PR MERGES
# had zero tests while its twin had twenty.
Verdict = routing.Verdict


@dataclass(frozen=True)
class BuildInput:
    """What the operator asked for. Immutable for the life of the run."""

    description: str | None = None
    task_file: str | None = None
    plan_path: str | None = None
    pr_number: str | None = None
    repo_target: str | None = None
    verbose: bool = False

    def __post_init__(self) -> None:
        # Fail fast and loud at the boundary: NEVER TWO task sources. A run that
        # reaches the draft child with no task produces an empty PR that still
        # costs a full review cycle to discover, and a run with two has no way to
        # say which one it obeyed.
        sources = [bool(self.description), bool(self.task_file), bool(self.plan_path)]
        if sum(sources) > 1:
            raise ValueError(
                "at most one task source — description, --task-file or --phase "
                f"(got description={self.description!r}, task_file={self.task_file!r}, "
                f"plan_path={self.plan_path!r})"
            )
        # `--pr` IS A TASK SOURCE, and this used to demand one alongside it.
        #
        # MEASURED 2026-08-19: a correction dispatch on PR #124 ran
        # `run_build.py --pr 124 --repo <path>` and was rejected with "exactly one
        # task source is required", so the operator re-issued it with the original
        # `--phase` repeated. Restating a task the PR already carries is not a
        # safety property — it is a second copy of the runway that can DISAGREE
        # with the one on the thread, and the thread is the copy every child reads
        # (`fidelity_read_and_compare.md` makes `gh pr view --json body,comments`
        # mandatory). `run_research_minor.py` and `run_plan_draft.py` never
        # imposed this; only the two runners sharing this dataclass did.
        #
        # WHAT IS STILL REFUSED: a run with neither a task source NOR a PR. That
        # is the empty-PR case this check was written for, and it is untouched.
        if not any(sources) and not self.pr_number:
            raise ValueError(
                "a task source is required — description, --task-file, --phase, or "
                "--pr <n> for a correction pass whose runway is already on the PR "
                f"(got description={self.description!r}, task_file={self.task_file!r}, "
                f"plan_path={self.plan_path!r}, pr_number={self.pr_number!r})"
            )


@dataclass(frozen=True)
class ChildResult:
    """What a child run returned.

    `exit_code == 0` is necessary but NOT sufficient — a child must also satisfy
    its completion contract, which is a pattern in its terminal output. That is
    checked in the helper, not here, because it is a pure predicate.
    """

    exit_code: int
    output: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


@dataclass
class BuildResult:
    """The workflow's own typed return.

    This replaces the bash version's exit code plus stdout scraping. A caller
    branches on `verdict` in code rather than grepping prose — the piece the
    roadmap calls typed handoff between runs.
    """

    pr_number: str
    pr_url: str
    verdict: Verdict
    loops_used: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def ready_to_merge(self) -> bool:
        return self.verdict is Verdict.MERGE

    @property
    def needs_human(self) -> bool:
        return not self.ready_to_merge

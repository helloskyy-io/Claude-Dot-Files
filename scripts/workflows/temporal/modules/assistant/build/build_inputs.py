"""Typed inputs and results for the build workflow.

Layer boundary note: these are plain dataclasses with no Temporal import. Under
the port's step 3 they become the payloads on `execute_activity` calls; today
they are ordinary values. Nothing here changes when Temporal arrives, which is
the point of defining them now.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Verdict(str, Enum):
    """The routing token review-pr emits on its terminal line.

    This IS the interface between the disposition child and its caller. The
    child aggregates per-finding hold_kind values into one token so the caller
    never re-derives a judgement the reviewer already made.
    """

    MERGE = "MERGE"
    HOLD_REDISPATCH = "HOLD - redispatch"
    HOLD_NEEDS_ASSISTANCE = "HOLD - needs-assistance"


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
        # Fail fast and loud at the boundary: exactly one task source, never both,
        # never neither. A run that reaches the draft child with no task produces
        # an empty PR that still costs a full review cycle to discover.
        sources = [bool(self.description), bool(self.task_file), bool(self.plan_path)]
        if sum(sources) != 1:
            raise ValueError(
                "exactly one task source is required — description, --task-file or --phase "
                f"(got description={self.description!r}, task_file={self.task_file!r}, "
                f"plan_path={self.plan_path!r})"
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

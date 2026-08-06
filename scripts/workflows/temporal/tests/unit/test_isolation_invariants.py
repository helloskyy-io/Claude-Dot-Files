"""Isolation is UNCONDITIONAL, and a negative outcome is OBSERVED, never asserted.

Two production failures are encoded here.

The first: `worktree_name=None if pr_number else worktree_name` put a `--pr` run
on the operator's live working tree with no discard path. Isolation is
established ONCE BY THE PARENT and passed down — two children creating the same
named worktree is `fatal: already exists`, which killed the draft->refine
handoff. The round-1 fix was right in principle and applied at the wrong
altitude, so both halves are asserted: children must NOT create one, parents
MUST.

The second: a failure banner claimed nothing was pushed when 9 files had landed
(+798/-111, on the PR branch). The operator read the banner, concluded the work
was lost, and dispatched a second full-budget run against work that was already
there. A false negative on the failure path is worse than a crash — a crash is
obviously wrong, while a confident wrong answer gets acted on.

These are structural (source-inspection) checks, so each predicate carries a
positive control per Testing Standard § Structural tests need a positive control.
"""

from __future__ import annotations

import inspect

import pytest

from modules.assistant import assistant_activities as act
from modules.assistant.build.build import build_workflow as parent
from modules.assistant.build.build_draft import build_draft_workflow as draft
from modules.assistant.build.build_minor import build_minor_workflow as parent_minor
from modules.assistant.build.build_refine import build_refine_workflow as refine

CHILDREN = [
    pytest.param(draft, id="build_draft"),
    pytest.param(refine, id="build_refine"),
]

PARENTS = [
    pytest.param(parent, id="build"),
    pytest.param(parent_minor, id="build_minor"),
]


def _creates_a_worktree(source: str) -> bool:
    """True when the source CALLS worktree_add — a call, not a mention in prose."""
    return "act.worktree_add(" in source


def _receives_a_worktree_path(source: str) -> bool:
    return "worktree: Path" in source


def _conditionally_skips_isolation(source: str) -> bool:
    """The exact ternary that put a --pr run on the operator's live working tree."""
    return "None if pr_number" in source


# --- children: isolation is received, never created and never skipped ---------

@pytest.mark.parametrize("module", CHILDREN)
def test_child_does_not_create_its_own_worktree(module) -> None:
    assert not _creates_a_worktree(inspect.getsource(module)), (
        f"{module.__name__} calls worktree_add. Isolation is established once by "
        "the parent and passed down; a second child creating the same named "
        "worktree is `fatal: already exists`, which killed the draft->refine handoff."
    )


@pytest.mark.parametrize("module", CHILDREN)
def test_child_receives_a_worktree_path(module) -> None:
    assert _receives_a_worktree_path(inspect.getsource(module)), (
        f"{module.__name__} no longer takes a `worktree: Path` parameter — if it "
        "does not receive isolation it will either run unisolated or create its own."
    )


@pytest.mark.parametrize("module", CHILDREN)
def test_child_does_not_conditionally_skip_isolation(module) -> None:
    assert not _conditionally_skips_isolation(inspect.getsource(module)), (
        f"{module.__name__} reintroduced the `None if pr_number` ternary. That put "
        "a --pr run directly on the operator's live working tree, where a run "
        "dying mid-write leaves a dirty tree on a foreign branch with no discard path."
    )


# --- parents: isolation is established exactly here ---------------------------

@pytest.mark.parametrize("module", PARENTS)
def test_parent_establishes_isolation(module) -> None:
    assert _creates_a_worktree(inspect.getsource(module)), (
        f"{module.__name__} no longer calls worktree_add. If the parent stops "
        "establishing isolation, every child below it runs on whatever tree it was given."
    )


def test_isolation_predicates_positive_control() -> None:
    """Positive control: each predicate must fire on a violating sample.

    Without this, a rename (`act.worktree_add` -> `wt.add`) silently turns every
    assertion above into a permanent pass — the checks would still be green with
    the invariant gone.
    """
    assert _creates_a_worktree("wt = act.worktree_add(repo_root, name, ref)") is True
    # The trailing `(` IS the discriminator: a CALL, not a mention in prose. A
    # child's docstring may legitimately explain that its parent calls
    # worktree_add, and that must not read as the child calling it.
    assert _creates_a_worktree("# the parent calls act.worktree_add for us") is False
    assert _creates_a_worktree("wt = passed_in_worktree") is False

    assert _receives_a_worktree_path("def run(*, worktree: Path) -> str:") is True
    assert _receives_a_worktree_path("def run(*, worktree) -> str:") is False

    assert _conditionally_skips_isolation("name = None if pr_number else name") is True
    assert _conditionally_skips_isolation("name = worktree_name") is False


# --- a negative outcome must be OBSERVED, never asserted ----------------------

def test_observe_outcome_reads_git_log() -> None:
    assert '"log"' in inspect.getsource(act.observe_outcome), (
        "observe_outcome no longer reads `git log` — it cannot report what landed "
        "without reading HEAD, and the banner it feeds would go back to guessing."
    )


def test_observe_outcome_reads_git_status() -> None:
    assert '"status"' in inspect.getsource(act.observe_outcome), (
        "observe_outcome no longer reads `git status` — uncommitted work would be "
        "invisible in the failure report."
    )


def test_observe_outcome_refuses_to_guess_when_it_cannot_read() -> None:
    """If it cannot determine the state it must SAY SO. It never reports a
    negative it did not verify.
    """
    source = inspect.getsource(act.observe_outcome)
    assert "cannot determine" in source or "do not assume" in source, (
        "observe_outcome lost its I-cannot-tell branch. A function that always "
        "produces a confident answer will produce a confident WRONG answer the "
        "first time git is unreadable — which is the failure that cost a duplicate run."
    )


def test_failure_path_reports_observed_state() -> None:
    assert "observed git state" in inspect.getsource(act.run_claude), (
        "run_claude's failure path no longer reports observed git state. A "
        "turn-cap exit may have committed and pushed real work; asserting "
        "otherwise costs a duplicate full-budget run."
    )

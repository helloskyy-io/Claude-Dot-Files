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

These are structural (source-inspection) checks, so EVERY predicate below carries
a positive control per Testing Standard § Structural tests need a positive
control.

The limit of the technique, stated so nobody reads more into a green run than is
there: a source-grep catches DRIFT — a guard removed, a call reshaped, a ternary
reintroduced. It does NOT prove the module runs, and it does not prove
`observe_outcome` produces a CORRECT report; only that it still reads the two
things it must read. Proving the behaviour needs a real git repo in `tmp_path`,
which is integration-tier and does not exist yet. That gap is tracked at issue
#36, which carries the ranked list — NOT in a PR body, because a PR body stops
being reachable the moment the PR merges.
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


def _reads_git_subcommand(source: str, subcommand: str) -> bool:
    """The QUOTED argv token, not the bare word.

    `"log"` is how the subcommand reaches `subprocess`; the bare word `log`
    appears in prose, in `log_file`, and in `logging` — matching it unquoted
    would keep passing after the call itself was deleted.
    """
    return f'"{subcommand}"' in source


def _refuses_to_guess(source: str) -> bool:
    return "cannot determine" in source or "do not assume" in source


def _reports_observed_state(source: str) -> bool:
    return "observed git state" in source


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


def test_observation_predicates_positive_control() -> None:
    """Positive control for the observed-outcome checks below.

    Each is a literal-membership check, which is exactly the shape that decays
    into a permanent pass when the surrounding text changes for an unrelated
    reason. These samples prove the predicates still discriminate.
    """
    assert _reads_git_subcommand('run(["git", "log", "--oneline"])', "log") is True
    # The bare word appears in `log_file`, in `logging`, and in prose. If the
    # quoted argv token stopped being the discriminator, this check would keep
    # passing after the `git log` call itself was deleted.
    assert _reads_git_subcommand("log_file = repo_root / 'run.log'", "log") is False
    assert _reads_git_subcommand('run(["git", "status", "-s"])', "status") is True
    assert _reads_git_subcommand('run(["git", "log"])', "status") is False

    assert _refuses_to_guess("notes.append('cannot determine push state')") is True
    assert _refuses_to_guess("notes.append('do not assume work was lost')") is True
    assert _refuses_to_guess("notes.append('nothing was pushed')") is False

    assert _reports_observed_state("banner += f'observed git state: {obs}'") is True
    assert _reports_observed_state("banner += 'the run failed'") is False


# --- a negative outcome must be OBSERVED, never asserted ----------------------

def test_observe_outcome_reads_git_log() -> None:
    assert _reads_git_subcommand(inspect.getsource(act.observe_outcome), "log"), (
        "observe_outcome no longer reads `git log` — it cannot report what landed "
        "without reading HEAD, and the banner it feeds would go back to guessing."
    )


def test_observe_outcome_reads_git_status() -> None:
    assert _reads_git_subcommand(inspect.getsource(act.observe_outcome), "status"), (
        "observe_outcome no longer reads `git status` — uncommitted work would be "
        "invisible in the failure report."
    )


def test_observe_outcome_refuses_to_guess_when_it_cannot_read() -> None:
    """If it cannot determine the state it must SAY SO. It never reports a
    negative it did not verify.
    """
    assert _refuses_to_guess(inspect.getsource(act.observe_outcome)), (
        "observe_outcome lost its I-cannot-tell branch. A function that always "
        "produces a confident answer will produce a confident WRONG answer the "
        "first time git is unreadable — which is the failure that cost a duplicate run."
    )


def test_failure_path_reports_observed_state() -> None:
    assert _reports_observed_state(inspect.getsource(act.run_claude)), (
        "run_claude's failure path no longer reports observed git state. A "
        "turn-cap exit may have committed and pushed real work; asserting "
        "otherwise costs a duplicate full-budget run."
    )

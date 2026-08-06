"""The delegated contract: what `run-claude.sh` demands, and in what order.

`run_claude` delegates model invocation, logging and the completion-contract
check to the existing bash activity rather than reimplementing them — one
implementation of the contract, not two that can disagree mid-migration. That
delegation only works if the Python side satisfies the bash side's preconditions
exactly, and each assertion below is a precondition that was once violated:

- `run-claude.sh` asserts LOG_FILE, MAX_TURNS, VERBOSE, FORMATTER and MODEL_KEY
  with `: "${VAR:?…}"` at SOURCE time. An earlier version sourced first and
  assigned after, tripped the guard, and exited 127 — the delegation did not
  satisfy the contract it delegated to.
- Logs written inside a worktree vanish with it, which made cost accounting
  impossible for two of five pipeline legs.
- `capture_output=True` produced a 70-minute run with zero visible output, so
  `--verbose` did nothing and an operator could not distinguish a working run
  from a hung one. The reported symptom was "it's not working" when it was.

These are structural (source-inspection) checks, so the predicates carry a
positive control per Testing Standard § Structural tests need a positive control.
"""

from __future__ import annotations

import inspect

import pytest

from modules.assistant import assistant_activities as act
from modules.assistant.review_pr import review_pr_workflow as rpw

RUN_CLAUDE_SOURCE = inspect.getsource(act.run_claude)
REVIEW_PR_SOURCE = inspect.getsource(rpw)

# The five variables run-claude.sh asserts at source time with `: "${VAR:?…}"`.
DELEGATED_ENV_VARS = ["LOG_FILE", "MAX_TURNS", "VERBOSE", "FORMATTER", "MODEL_KEY"]


def _supplies_env_var(source: str, var: str) -> bool:
    return f'"{var}"' in source


def _builds_env_before_sourcing(source: str) -> bool:
    """The env dict must be assembled before the `source "{runner}"` line."""
    if "LOG_FILE" not in source or 'source "{runner}"' not in source:
        return False
    return source.index("LOG_FILE") < source.index('source "{runner}"')


@pytest.mark.parametrize("var", DELEGATED_ENV_VARS)
def test_run_claude_supplies_the_delegated_env_var(var: str) -> None:
    assert _supplies_env_var(RUN_CLAUDE_SOURCE, var), (
        f"run_claude no longer exports {var}. run-claude.sh asserts it with "
        f'`: "${{{var}:?…}}"` at source time, so its absence is an exit 127 before '
        "a single turn runs."
    )


def test_env_is_built_before_the_source_line() -> None:
    assert _builds_env_before_sourcing(RUN_CLAUDE_SOURCE), (
        "run_claude assembles its environment after sourcing run-claude.sh. The "
        "bash side asserts its five variables AT SOURCE TIME — assigning "
        "afterwards trips the guard and exits 127."
    )


def test_run_claude_refuses_a_worktree_as_its_log_root() -> None:
    """Logs must never be written inside a worktree — they vanish with it, which
    made cost accounting impossible for two of five pipeline legs.
    """
    assert ".claude/worktrees" in RUN_CLAUDE_SOURCE, (
        "run_claude lost its guard against a worktree being passed as repo_root. "
        "repo_root is where LOGS live and must be the real repository; the "
        "worktree is only where the model EXECUTES."
    )


def test_run_claude_separates_exec_dir_from_log_dir() -> None:
    assert "cwd = worktree or repo_root" in RUN_CLAUDE_SOURCE, (
        "run_claude no longer distinguishes where it EXECUTES from where it LOGS. "
        "An earlier version passed the worktree as repo_root and buried every V2 log."
    )


def test_run_claude_streams_rather_than_capturing_silently() -> None:
    """A CALL, not prose: Popen plus a read loop over stdout."""
    assert "Popen" in RUN_CLAUDE_SOURCE and "for line in proc.stdout" in RUN_CLAUDE_SOURCE, (
        "run_claude went back to capturing output silently. That produced a "
        "70-minute run with zero visible output where --verbose did nothing and "
        "an operator could not tell a working run from a hung one."
    )


def test_review_pr_checks_out_the_pr_branch() -> None:
    """review-pr must read the PR's branch, not the repo's checkout.

    V1 does `git worktree add -f … origin/$PR_BRANCH` for exactly this reason:
    reviewing the wrong tree produces a confident verdict about code that is not
    under review.
    """
    assert "worktree_add(" in REVIEW_PR_SOURCE and "headRefName" in REVIEW_PR_SOURCE, (
        "review_pr no longer resolves the PR's head branch and checks it out. "
        "It would review whatever the repo currently has checked out and emit a "
        "verdict on the wrong tree."
    )


def test_delegated_contract_predicates_positive_control() -> None:
    """Positive control: both predicates must fire on a violating sample.

    Without this, a quoting change (`"LOG_FILE"` -> `'LOG_FILE'`) turns every
    assertion above into a permanent pass while the contract is unenforced.
    """
    assert _supplies_env_var('env = {"LOG_FILE": str(log_file)}', "LOG_FILE") is True
    assert _supplies_env_var("env = {}", "LOG_FILE") is False

    ordered = 'env = {"LOG_FILE": p}\nsubprocess.run(f\'source "{runner}"\')'
    reversed_ = 'subprocess.run(f\'source "{runner}"\')\nenv = {"LOG_FILE": p}'
    assert _builds_env_before_sourcing(ordered) is True
    assert _builds_env_before_sourcing(reversed_) is False
    assert _builds_env_before_sourcing("no contract here at all") is False

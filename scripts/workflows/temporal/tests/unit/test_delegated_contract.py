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

These are structural (source-inspection) checks, so EVERY predicate below carries
a positive control per Testing Standard § Structural tests need a positive
control — proving the predicate still distinguishes a violating sample from a
conforming one, rather than having quietly become a permanent pass.

WHAT A SOURCE-GREP CAN AND CANNOT PROVE. It detects DRIFT: a guard deleted, a
call reshaped, an ordering inverted, a variable dropped from the env dict. It
cannot prove the module EXECUTES — a name that does not resolve, a signature
that no longer matches its caller are invisible to it, because the offending
token is present and spelled correctly. That gap was not hypothetical: this
module's checks stayed green against a `review_pr_workflow` that used
`_shared.worktree_add` with no import for `_shared`, and the resulting NameError
crashed the last leg of a 40-minute pipeline.

The undefined-name half of that gap is now CLOSED, and not by the integration
tier — `test_v1_parity.py` § 3 runs a ruff F821 sweep over `modules/`,
`scripts/` and `tests/`, which resolves every name in every branch without
executing anything. It is unit-tier, it is cheap, and it catches the whole class
rather than the one instance. The import it was written for is present today
(`review_pr_workflow.py:19`).

What remains outside reach of both a grep and a name resolver is BEHAVIOUR: a
signature that drifted from its caller, an argument passed in the wrong order, a
branch that raises at runtime. Closing that needs a test that imports and RUNS
the workflow, which is integration-tier and does not exist yet. Tracked at issue
#36 alongside the rest of the ranked coverage gaps.
"""

from __future__ import annotations

import inspect
from typing import Callable

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


def _guards_worktree_as_log_root(source: str) -> bool:
    return ".claude/worktrees" in source


def _separates_exec_dir_from_log_dir(source: str) -> bool:
    return "cwd = worktree or repo_root" in source


def _streams_output(source: str) -> bool:
    """Popen PLUS a read loop. Popen alone still permits `proc.communicate()`,
    which buffers to completion and reproduces the silent-run symptom exactly.
    """
    return "Popen" in source and "for line in proc.stdout" in source


def _checks_out_the_pr_branch(source: str) -> bool:
    """Resolves the PR's head ref AND creates a tree from it. Either half alone
    is insufficient: reading `headRefName` without checking it out reviews the
    wrong tree just as thoroughly as not reading it at all.
    """
    return "worktree_add(" in source and "headRefName" in source


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
    assert _guards_worktree_as_log_root(RUN_CLAUDE_SOURCE), (
        "run_claude lost its guard against a worktree being passed as repo_root. "
        "repo_root is where LOGS live and must be the real repository; the "
        "worktree is only where the model EXECUTES."
    )


def test_run_claude_separates_exec_dir_from_log_dir() -> None:
    assert _separates_exec_dir_from_log_dir(RUN_CLAUDE_SOURCE), (
        "run_claude no longer distinguishes where it EXECUTES from where it LOGS. "
        "An earlier version passed the worktree as repo_root and buried every V2 log."
    )


def test_run_claude_streams_rather_than_capturing_silently() -> None:
    """A CALL, not prose: Popen plus a read loop over stdout."""
    assert _streams_output(RUN_CLAUDE_SOURCE), (
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
    assert _checks_out_the_pr_branch(REVIEW_PR_SOURCE), (
        "review_pr no longer resolves the PR's head branch and checks it out. "
        "It would review whatever the repo currently has checked out and emit a "
        "verdict on the wrong tree."
    )


# Positive controls: EVERY predicate above must still distinguish a violating
# sample from a conforming one. Without them, a quoting change
# (`"LOG_FILE"` -> `'LOG_FILE'`) turns the assertion that depends on a predicate
# into a permanent pass while the contract it names goes unenforced — and
# nothing signals that the check stopped looking.
#
# Enumerated at COLLECTION time, one case per (predicate, sample) pair, for the
# same reason test_prompt_completeness.py enumerates its pairs: a single bundled
# test body aborts at the first failing assert, so a SECOND predicate that also
# went blind is masked until the first is fixed and the suite re-run. A control
# that can hide a regression is the failure mode controls exist to prevent.
PREDICATE_CONTROLS = [
    ("supplies_env_var/present", lambda s: _supplies_env_var(s, "LOG_FILE"),
     'env = {"LOG_FILE": str(log_file)}', True),
    ("supplies_env_var/absent", lambda s: _supplies_env_var(s, "LOG_FILE"),
     "env = {}", False),

    ("builds_env_before_sourcing/ordered", _builds_env_before_sourcing,
     'env = {"LOG_FILE": p}\nsubprocess.run(f\'source "{runner}"\')', True),
    ("builds_env_before_sourcing/reversed", _builds_env_before_sourcing,
     'subprocess.run(f\'source "{runner}"\')\nenv = {"LOG_FILE": p}', False),
    ("builds_env_before_sourcing/neither", _builds_env_before_sourcing,
     "no contract here at all", False),

    ("guards_worktree_as_log_root/guarded", _guards_worktree_as_log_root,
     'if ".claude/worktrees" in str(repo_root):', True),
    ("guards_worktree_as_log_root/unguarded", _guards_worktree_as_log_root,
     "log_dir = repo_root / 'logs'", False),

    ("separates_exec_dir_from_log_dir/separated", _separates_exec_dir_from_log_dir,
     "cwd = worktree or repo_root", True),
    ("separates_exec_dir_from_log_dir/merged", _separates_exec_dir_from_log_dir,
     "cwd = repo_root", False),

    # Popen alone must NOT satisfy it: `communicate()` buffers to completion and
    # is the exact shape that produced the 70-minute silent run.
    ("streams_output/read-loop", _streams_output,
     "proc = Popen(...)\nfor line in proc.stdout:", True),
    ("streams_output/communicate", _streams_output,
     "proc = Popen(...)\nout = proc.communicate()", False),
    ("streams_output/capture_output", _streams_output,
     "subprocess.run(cmd, capture_output=True)", False),

    # Likewise each half alone is insufficient — reading the ref without checking
    # it out reviews the wrong tree just as surely as never reading it.
    ("checks_out_the_pr_branch/both-halves", _checks_out_the_pr_branch,
     'worktree_add(root, name, pr["headRefName"])', True),
    ("checks_out_the_pr_branch/reads-only", _checks_out_the_pr_branch,
     'branch = pr["headRefName"]', False),
    ("checks_out_the_pr_branch/wrong-ref", _checks_out_the_pr_branch,
     "worktree_add(root, name, 'origin/main')", False),
]


@pytest.mark.parametrize(
    ("predicate", "sample", "expected"),
    [pytest.param(p, s, e, id=label) for label, p, s, e in PREDICATE_CONTROLS],
)
def test_delegated_contract_predicate_positive_control(
    predicate: Callable[[str], bool], sample: str, expected: bool
) -> None:
    assert predicate(sample) is expected, (
        f"the predicate no longer distinguishes this sample — it returned "
        f"{not expected} for {sample!r}. The assertion that depends on it has "
        f"become a permanent pass, and the contract it names is unenforced."
    )

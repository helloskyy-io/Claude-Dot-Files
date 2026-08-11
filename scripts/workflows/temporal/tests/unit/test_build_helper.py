"""Layer-2 tests for the build helper. No mocks, no I/O, no fixtures — that is
the point.

If any test here needs a mock, the helper is doing something it should not and
the layer boundary has leaked.

Import path comes from `tests/conftest.py`.
"""

from __future__ import annotations

import pytest

from modules.assistant.build import build_helper as helper
from modules.assistant.build.build_inputs import BuildInput, ChildResult, Verdict


# --- completion contract -----------------------------------------------------

def test_extract_pr_url_takes_the_last_url() -> None:
    """Last, not first: a run may mention an existing PR before opening its own."""
    output = "opened https://github.com/o/r/pull/12\nfinal https://github.com/o/r/pull/42\n"
    assert helper.extract_pr_url(output) == "https://github.com/o/r/pull/42", (
        "extract_pr_url returned a URL other than the last one in the output — "
        "a run mentioning a pre-existing PR would hand off the wrong PR number"
    )


def test_extract_pr_url_returns_none_when_there_is_no_url() -> None:
    assert helper.extract_pr_url("nothing here") is None, (
        "extract_pr_url invented a URL from output containing none"
    )


def test_pr_number_from_url_takes_the_trailing_number() -> None:
    assert helper.pr_number_from_url(
        "https://github.com/o/r/pull/42", expected_repo="o/r") == "42"


# --- verdict parsing, and the fail-safe --------------------------------------

@pytest.mark.parametrize(
    ("output", "expected"),
    [
        pytest.param("VERDICT: MERGE", (Verdict.MERGE, True), id="merge"),
        pytest.param(
            "noise\nVERDICT: HOLD - redispatch\n",
            (Verdict.HOLD_REDISPATCH, True),
            id="redispatch-surrounded-by-noise",
        ),
        pytest.param(
            "the run died",
            (Verdict.HOLD_NEEDS_ASSISTANCE, False),
            id="UNPARSEABLE-FAILS-SAFE-TO-HUMAN",
        ),
    ],
)
def test_parse_verdict(output: str, expected: tuple[Verdict, bool]) -> None:
    """An unparseable verdict must become HOLD_NEEDS_ASSISTANCE, never MERGE and
    never a redispatch: ambiguity routes to the branch requiring a person,
    because wrongly merging costs an unbounded amount and wrongly asking costs
    one message.
    """
    got = helper.parse_verdict(output)
    assert got == expected, (
        f"parse_verdict({output!r}) routed to {got!r}, expected {expected!r} — "
        "a wrong route here either merges unreviewed work or burns a redispatch"
    )


def test_prose_mentioning_the_token_does_not_match() -> None:
    """The pattern is anchored on purpose: an unanchored match would find the
    token inside prose discussing it, and a reviewer writing about verdicts
    would accidentally emit one.
    """
    _, parseable = helper.parse_verdict("we could emit VERDICT: MERGE here")
    assert parseable is False, (
        "verdict matched inside prose — the pattern lost its line anchors, so a "
        "reviewer merely DISCUSSING a merge verdict now issues one"
    )


def test_last_verdict_wins_on_a_re_review() -> None:
    """A re-review appends; the terminal line is the ruling that stands."""
    verdict, _ = helper.parse_verdict("VERDICT: HOLD - redispatch\nVERDICT: MERGE")
    assert verdict is Verdict.MERGE, (
        f"a re-review's superseded first verdict won over its final one (got {verdict!r})"
    )


# --- routing -----------------------------------------------------------------

@pytest.mark.parametrize(
    ("verdict", "loops_used", "expected"),
    [
        pytest.param(Verdict.HOLD_REDISPATCH, 0, True, id="redispatch-loops-once"),
        pytest.param(Verdict.HOLD_REDISPATCH, 1, False, id="budget-spent"),
        pytest.param(Verdict.HOLD_NEEDS_ASSISTANCE, 0, False, id="needs-assistance-NEVER-loops"),
        pytest.param(Verdict.MERGE, 0, False, id="merge-never-loops"),
    ],
)
def test_should_loop_back(verdict: Verdict, loops_used: int, expected: bool) -> None:
    """needs-assistance never loops at any count: a human ruling is not something
    more passes can produce, so spending them is pure waste.
    """
    got = helper.should_loop_back(verdict, loops_used)
    assert got is expected, (
        f"should_loop_back({verdict!r}, loops_used={loops_used}) returned {got}, "
        f"expected {expected} — wrong routing spends a full child run or drops one that was owed"
    )


# --- input validation at the boundary ----------------------------------------

@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param({}, id="no-task-source-rejected"),
        pytest.param(
            {"description": "x", "task_file": "/tmp/y"},
            id="both-task-sources-rejected",
        ),
    ],
)
def test_build_input_requires_exactly_one_task_source(kwargs: dict) -> None:
    """A run that reaches the draft child with no task produces an empty PR that
    still costs a full review cycle to discover.
    """
    with pytest.raises(ValueError, match="exactly one task source"):
        BuildInput(**kwargs)


# --- arg compilation ---------------------------------------------------------

def test_draft_args_puts_flags_first_and_the_positional_last() -> None:
    """Positional-in-the-middle gets stepped on by terminal line-wrap, which is
    why the convention exists.
    """
    task = BuildInput(description="fix auth", repo_target="/opt/x", verbose=True)
    assert helper.draft_args(task) == ["--repo", "/opt/x", "--verbose", "fix auth"]


def test_refine_args_carries_both_correction_flags() -> None:
    task = BuildInput(description="fix auth", repo_target="/opt/x", verbose=True)
    assert helper.refine_args(task, "42", correction_pass=True, ci_unsettled=True) == [
        "--repo", "/opt/x", "--verbose", "--correction-pass", "--ci-unsettled", "--pr", "42", "fix auth",
    ]


def test_task_file_bypasses_shell_parsing() -> None:
    """--task-file passes quotes, newlines and backticks through literally."""
    assert helper.task_args(BuildInput(task_file="/tmp/t.md")) == ["--task-file", "/tmp/t.md"]


# --- handoff validation ------------------------------------------------------

def test_nonzero_exit_is_rejected_even_when_a_url_is_present() -> None:
    """exit 0 is necessary but not sufficient, and so is a URL. A child that
    died having printed a URL did not finish.
    """
    with pytest.raises(RuntimeError, match="build-draft FAILED"):
        helper.draft_handoff(ChildResult(exit_code=1, output="https://github.com/o/r/pull/1"))


def test_exit_zero_without_a_url_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="no PR URL"):
        helper.draft_handoff(ChildResult(exit_code=0, output="done, no url"))


def test_valid_handoff_returns_the_url() -> None:
    got = helper.draft_handoff(ChildResult(exit_code=0, output="https://github.com/o/r/pull/7"))
    assert got == "https://github.com/o/r/pull/7"

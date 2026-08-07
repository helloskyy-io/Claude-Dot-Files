"""plan-revision's pure logic and its CLI contract.

Two pure functions and an argument parser — no mocks, no I/O beyond a tmp_path
file, because there is nothing else in the port that is not prompt text. Prompt
fidelity is asserted in `test_plan_revision_v1_parity.py`; this module covers
the parts a reader could get wrong by hand.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from modules.assistant.plan.plan_revision import plan_revision_workflow as wf

# The entrypoint lives outside `modules/`, so it needs the scripts dir on the
# path. The component root is already there via tests/conftest.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import run_plan_revision as cli  # noqa: E402


# --- context_block -----------------------------------------------------------

def test_no_context_produces_no_block() -> None:
    """Empty means EMPTY, not an empty pair of delimiters.

    A bare `--- additional context ---` header with nothing under it reads to
    the model as context that was meant to be there and went missing, which is
    strictly worse than no header — it invites the run to go looking.
    """
    assert wf.context_block("") == ""


def test_context_is_wrapped_in_v1s_delimiters_exactly() -> None:
    assert wf.context_block("focus on Q3") == (
        "\n--- additional context ---\nfocus on Q3\n--- end additional context ---\n"
    )


def test_context_content_is_preserved_literally() -> None:
    """--task-file exists so multi-paragraph text with quotes and backticks
    survives; a block that reflowed or escaped it would defeat the flag."""
    messy = 'line one\n\n  "quoted" and `backticked` and $DOLLAR\n'
    assert messy in wf.context_block(messy)


# --- completion_url ----------------------------------------------------------

@pytest.mark.parametrize(
    ("output", "expected"),
    [
        pytest.param("opened https://github.com/o/r/pull/7\n",
                     "https://github.com/o/r/pull/7", id="pr"),
        pytest.param("first https://github.com/o/r/pull/3\nfinal https://github.com/o/r/pull/9\n",
                     "https://github.com/o/r/pull/9", id="last-pr-wins"),
        pytest.param("STOPPED https://github.com/o/r/issues/44\n",
                     "https://github.com/o/r/issues/44", id="stop-issue"),
        pytest.param("nothing at all", None, id="neither"),
    ],
)
def test_completion_url(output: str, expected: str | None) -> None:
    assert wf.completion_url(output) == expected


def test_a_completed_run_outranks_the_issue_its_pr_body_cites() -> None:
    """A PR body routinely says `Closes` with a full issue URL while it is being
    written — and Stage 6 then mandates the PR URL as the run's FINAL line, so
    the PR still comes last. Returning the issue here would report a completed
    plan as a STOP and route the operator to research the plan did not need.
    """
    output = (
        "opened https://github.com/o/r/pull/7\n"
        "body: Closes https://github.com/o/r/issues/44\n"
        "https://github.com/o/r/pull/7\n"
    )
    assert wf.completion_url(output) == "https://github.com/o/r/pull/7"


def test_a_stop_outranks_a_pr_it_merely_quoted() -> None:
    """The mirror case, and the reason the rule is positional rather than
    type-priority.

    A planning run reads docs and PR bodies full of PR URLs before it decides
    anything. If Stage 1 then STOPs — research required, or evidence
    structurally faulty — it files an issue and prints THAT as its final line.
    A rule that always preferred a PR would hand back a PR this run never
    opened, reporting a correct ~$2 gate as a finished plan and inviting a
    re-dispatch straight past it.
    """
    output = (
        "the phase doc cites https://github.com/o/r/pull/12 as prior art\n"
        "STOPPING: research required. Filed:\n"
        "https://github.com/o/r/issues/44\n"
    )
    assert wf.completion_url(output) == "https://github.com/o/r/issues/44"


# --- the CLI contract --------------------------------------------------------

@pytest.mark.parametrize("argv", [
    pytest.param([], id="omitted"),
    pytest.param([""], id="empty-string"),
    pytest.param(["   "], id="whitespace-only"),
])
def test_description_is_required(argv: list[str]) -> None:
    """V1 printed usage and exited 1 on a bare invocation. A run with no task
    still costs a worktree and a model call to discover it has nothing to do.

    The empty-string cases are the ones argparse alone does NOT catch: its
    required-positional check fires only on OMISSION, so `plan_revision.sh ""`
    parsed cleanly and dispatched against a blank task.
    """
    with pytest.raises(SystemExit):
        cli.parse_args(argv)


def test_positional_context_and_task_file_are_mutually_exclusive() -> None:
    """V1 rejected both rather than preferring one. Preferring either drops
    context the operator supplied, and they find out from the plan."""
    with pytest.raises(SystemExit):
        cli.parse_args(["desc", "ctx", "--task-file", "/tmp/x.md"])


@pytest.mark.parametrize(
    ("argv", "field", "expected"),
    [
        pytest.param(["desc"], "description", "desc", id="description"),
        pytest.param(["desc", "ctx"], "context", "ctx", id="positional-context"),
        pytest.param(["desc", "--pr", "18"], "pr_number", "18", id="pr"),
        pytest.param(["desc", "--repo", "/r"], "repo_target", "/r", id="repo"),
        pytest.param(["desc", "-v"], "verbose", True, id="verbose-short"),
        pytest.param(["desc", "--verbose"], "verbose", True, id="verbose-long"),
        pytest.param(["desc", "--task-file", "/t.md"], "task_file", "/t.md", id="task-file"),
        pytest.param(["--pr", "18", "desc"], "description", "desc", id="flags-before-positionals"),
    ],
)
def test_every_v1_argument_is_accepted(argv: list[str], field: str, expected) -> None:
    """The bash script documents flags-FIRST invocation, so that ordering has to
    parse — the shim passes arguments through untouched and cannot reorder them."""
    assert getattr(cli.parse_args(argv), field) == expected


def test_an_unknown_option_is_rejected() -> None:
    with pytest.raises(SystemExit):
        cli.parse_args(["desc", "--not-a-flag"])


def test_a_missing_task_file_raises_rather_than_running_on_empty_context(
    tmp_path: Path,
) -> None:
    """A typo'd path must not degrade to "no context" — the run would proceed on
    a bare description and produce a plan missing everything the file held."""
    with pytest.raises(FileNotFoundError, match="task file not found"):
        cli._read_task_file(str(tmp_path / "absent.md"))


def test_a_task_file_is_read_literally(tmp_path: Path) -> None:
    body = 'para one\n\n  "quoted" and `backticked`\n'
    f = tmp_path / "ctx.md"
    f.write_text(body)
    assert cli._read_task_file(str(f)) == body


# --- main(): the repo root is the ANSWER git gives, not the invocation dir ----

def _stub_git_toplevel(monkeypatch: pytest.MonkeyPatch, *, returncode: int, stdout: str) -> None:
    """Stand in for the one `git rev-parse --show-toplevel` main() runs."""
    monkeypatch.setattr(cli.subprocess, "run", lambda argv, **_: subprocess.CompletedProcess(
        argv, returncode, stdout=stdout, stderr="not a git repository" if returncode else ""))


def _must_not_run(*_a, **_k):
    raise AssertionError("a worktree was created for a directory that is not a repo")


def test_the_repo_root_is_normalised_to_the_git_toplevel(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """V1 did `REPO_ROOT="$(git rev-parse --show-toplevel)"; cd "$REPO_ROOT"` —
    it USED the answer. An earlier version of this port ran the same command
    purely as a pass/fail gate and threw the output away, leaving repo_root as
    the invocation directory.

    Everything hangs off repo_root: `.claude/worktrees/` and `.claude/logs/`
    both. Dispatching from a subdirectory would scatter worktrees and logs into
    it, where /cleanup-merged-worktrees does not look and the operator does not
    either.
    """
    toplevel = tmp_path / "repo"
    subdir = toplevel / "docs" / "development"
    subdir.mkdir(parents=True)

    _stub_git_toplevel(monkeypatch, returncode=0, stdout=f"{toplevel}\n")

    seen: dict[str, Path] = {}

    def fake_worktree_add(root: Path, name: str, ref: str) -> Path:
        seen["worktree_root"] = root
        return Path("/wt")

    def fake_run(**kwargs) -> str:
        seen["workflow_root"] = kwargs["repo_root"]
        return "https://github.com/o/r/pull/7"

    monkeypatch.setattr(cli.act, "worktree_add", fake_worktree_add)
    monkeypatch.setattr(cli.wf, "run_plan_revision", fake_run)
    monkeypatch.chdir(subdir)

    assert cli.main(["bump the roadmap"]) == 0
    assert seen["worktree_root"] == toplevel, (
        f"worktree would be cut under {seen['worktree_root']}, not the repo root {toplevel}"
    )
    assert seen["workflow_root"] == toplevel, (
        "the workflow was handed the invocation directory, so its logs would land there"
    )


def test_a_directory_outside_a_repo_is_refused_before_anything_is_created(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """The precondition still has to FAIL when it should. Normalising the happy
    path is worthless if the unhappy one stopped being detected."""
    _stub_git_toplevel(monkeypatch, returncode=128, stdout="")
    monkeypatch.setattr(cli.act, "worktree_add", _must_not_run)
    monkeypatch.chdir(tmp_path)

    assert cli.main(["bump the roadmap"]) == 1

"""The turn-cap banner reports the worktree's ACTUAL state, or says it cannot.

THE DEFECT (issue #65). On `"subtype":"error_max_turns"`, `run-claude.sh`
printed two sentences it had never checked:

    Work is uncommitted at: .../worktrees/build-1786206125
    NOTHING was committed or pushed.

On PR #56's redispatch that was false in both halves. The cap fired while the
run was printing the PR URL — the last step — with every deliverable pushed and
CI green. The consequence is worse than a wrong message: an operator who trusts
it goes to salvage a worktree with nothing in it, and may re-dispatch work that
is already merge-ready, paying a second full budget and opening a conflicting
branch. A wrong claim about state sends someone somewhere; an absent one sends
them to look.

THE FUNCTION IS EXECUTED AS SHIPPED, extracted from `run-claude.sh` — the same
technique and the same reason as `test_exit_record_transport.py`'s gate tests: a
test that re-typed the git invocations would pass forever against a script whose
invocations had changed.

AND IT IS RUN UNDER `set -euo pipefail`, which is the CALLER'S shape. Every V1
child sets it and calls `run_claude` unguarded, so a non-zero exit anywhere in
this function kills the workflow inside the banner that exists to explain why it
died. A test invoking the function under a permissive shell could not see that.

BOTH DIRECTIONS, PER ARM. Each state that produces a report is driven with a
real git repository built for it, and the fully-pushed arm — the one the
original banner got wrong — is asserted to still make its claim. A banner that
never claims anything is not a fix.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
RUN_CLAUDE = REPO_ROOT / "scripts" / "workflows" / "activities" / "run-claude.sh"

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git is required")

# Anchored on the function's own boundaries. Extracting by position in the
# banner instead would break the moment the banner is reworded, which is the
# wrong red: the reader would go looking for a deleted reader that is still
# there.
_STATE_FN = re.compile(r"^worktree_delivery_state\(\) \{\n.*?\n\}$",
                       re.DOTALL | re.MULTILINE)


def _shipped_state_reader() -> str:
    m = _STATE_FN.search(RUN_CLAUDE.read_text())
    assert m, "run-claude.sh no longer defines worktree_delivery_state"
    body = m.group(0)
    # Positive control on the EXTRACTOR, not on the function: a regex that
    # matched an empty or truncated span would make every assertion below run
    # against nothing and pass the negative ones.
    assert body.count("\n") > 20, f"the extraction is too short to be the reader:\n{body}"
    return body


def _describe(wt: Path | str) -> str:
    """Run the shipped reader under the callers' `set -euo pipefail`."""
    out = subprocess.run(
        ["bash", "-c", f"set -euo pipefail\n{_shipped_state_reader()}\n"
                       'worktree_delivery_state "$1"', "_", str(wt)],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, (
        f"the reader exited {out.returncode} under errexit — every V1 child "
        f"calls run_claude unguarded, so this kills the workflow inside its own "
        f"failure banner:\n{out.stderr}"
    )
    return out.stdout


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t", *args],
        capture_output=True, text=True, check=True,
    ).stdout


@pytest.fixture
def pushed_tree(tmp_path: Path) -> Path:
    """A branch with one commit, pushed to a bare remote and tracking it.

    This is PR #56's shape — the state the banner described as unsalvaged work.
    """
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    wt = tmp_path / "wt"
    subprocess.run(["git", "init", "-q", "-b", "work", str(wt)], check=True)
    (wt / "a.txt").write_text("a\n")
    _git(wt, "add", "-A")
    _git(wt, "commit", "-qm", "deliverable")
    _git(wt, "remote", "add", "origin", str(remote))
    _git(wt, "push", "-q", "-u", "origin", "work")
    return wt


# ---------------------------------------------------------------------------
# The state that produced the false report.
# ---------------------------------------------------------------------------

def test_a_fully_pushed_tree_is_NOT_reported_as_unsalvaged_work(pushed_tree: Path) -> None:
    """PR #56, reproduced. Nothing here may claim work is uncommitted or unpushed."""
    out = _describe(pushed_tree)
    assert "fully pushed" in out
    assert "CHECK THE PR BEFORE REDISPATCHING" in out, (
        "the pushed arm has to send the operator to the PR — telling them to "
        "salvage the tree is what cost a second budget"
    )
    assert "UNCOMMITTED" not in out and "NOT pushed" not in out, out


# ---------------------------------------------------------------------------
# The states the report legitimately describes.
# ---------------------------------------------------------------------------

def test_uncommitted_changes_are_reported_with_a_count(pushed_tree: Path) -> None:
    """The banner's original claim, now made only when it is true."""
    (pushed_tree / "b.txt").write_text("b\n")
    out = _describe(pushed_tree)
    assert re.search(r"✗ 1 path\(s\) carry UNCOMMITTED changes", out), out


def test_committed_but_unpushed_commits_are_reported_with_a_count(pushed_tree: Path) -> None:
    """The middle state the one-sentence banner had no way to express.

    UNCOMMITTED AND UNPUSHED ARE INDEPENDENT: this tree is clean AND has work
    the remote does not have, and the report says both.
    """
    (pushed_tree / "c.txt").write_text("c\n")
    _git(pushed_tree, "add", "-A")
    _git(pushed_tree, "commit", "-qm", "second")
    out = _describe(pushed_tree)
    assert re.search(r"✗ 1 commit\(s\) on 'work' are NOT pushed to 'origin/work'", out), out
    assert "Working tree is clean" in out, out


def test_uncommitted_AND_unpushed_are_reported_SEPARATELY(pushed_tree: Path) -> None:
    """The shape a single sentence cannot carry, and the reason there are two.

    THE FIXTURE VARIES IN SHAPE, not in a value: both facts are true at once, so
    a reader that derived one from the other — however it spelled the derivation
    — comes back with one line here instead of two.
    """
    (pushed_tree / "c.txt").write_text("c\n")
    _git(pushed_tree, "add", "-A")
    _git(pushed_tree, "commit", "-qm", "second")
    (pushed_tree / "d.txt").write_text("d\n")
    out = _describe(pushed_tree)
    assert "UNCOMMITTED changes" in out and "are NOT pushed" in out, out


# ---------------------------------------------------------------------------
# The third state: no local answer. Each of these is its own arm, because
# collapsing any of them into "nothing was pushed" rebuilds the defect.
# ---------------------------------------------------------------------------

def test_a_worktree_that_is_gone_is_UNDETERMINED_not_clean(tmp_path: Path) -> None:
    out = _describe(tmp_path / "removed-after-the-run")
    assert "NOT on disk" in out, out
    assert "cannot be determined" in out, out


def test_a_branch_with_no_upstream_is_UNDETERMINED_not_unpushed(tmp_path: Path) -> None:
    """`git log <upstream>..HEAD` has no meaning here, so no count is invented."""
    wt = tmp_path / "solo"
    subprocess.run(["git", "init", "-q", "-b", "solo", str(wt)], check=True)
    (wt / "a.txt").write_text("a\n")
    _git(wt, "add", "-A")
    _git(wt, "commit", "-qm", "x")
    out = _describe(wt)
    assert "has no upstream ref" in out and "cannot be" in out, out
    assert "NOT pushed" not in out, out


def test_a_detached_HEAD_is_UNDETERMINED(pushed_tree: Path) -> None:
    """A worktree dispatch can leave a detached HEAD; there is no branch to
    compare, and guessing one is how a wrong count gets printed."""
    _git(pushed_tree, "checkout", "-q", "--detach", "HEAD")
    out = _describe(pushed_tree)
    assert "detached" in out and "no local answer" in out, out


def test_a_leftover_directory_does_not_get_the_PARENT_repo_s_answer(pushed_tree: Path) -> None:
    """THE ARM THE ISSUE DID NOT NAME, found by asking what the check does not
    look at.

    Fleet worktrees live at `<repo>/.claude/worktrees/<name>`, INSIDE the parent
    repository. So a leftover directory there — a partially-failed
    `git worktree remove`, a stale mkdir — is still a path `git -C` answers for,
    by walking up. That answer is the MAIN CHECKOUT's branch and the main
    checkout's dirt, printed as this run's: the same defect this function was
    written to remove, reached past the on-disk test.
    """
    leftover = pushed_tree / ".claude" / "worktrees" / "build-1786206125"
    leftover.mkdir(parents=True)
    out = _describe(leftover)
    assert "is not a worktree root" in out, out
    assert "cannot be determined" in out, out
    assert "fully pushed" not in out, "it answered with the parent repository's state"


def test_a_directory_that_is_not_in_any_repository_is_UNDETERMINED(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    out = _describe(plain)
    assert "not a readable git worktree" in out or "not a worktree root" in out, out


# ---------------------------------------------------------------------------
# The banner itself: every claim about delivery comes from the reader.
# ---------------------------------------------------------------------------

def _turn_cap_block() -> str:
    source = RUN_CLAUDE.read_text()
    start = source.index('if grep -q \'"subtype":"error_max_turns"\'')
    end = source.index("Completion contract", start)
    block = source[start:end]
    assert block.count("echo") >= 5, f"the block scan read {block!r} — it is not reading the block"
    return block


def test_the_banner_makes_no_delivery_claim_of_its_OWN() -> None:
    """SHAPE-MATCHED, NOT VALUE-MATCHED — this is the point of the check.

    Asserting that the two known-wrong sentences are gone would retire the guard
    the moment it passed: it could only ever catch the instance already found.
    The property is *the banner does not talk about commit or push state except
    through the reader*, so the scan is for that vocabulary anywhere in the
    block's executable lines. A NEW unchecked sentence is caught by this; a
    reworded old one is too.

    Comment lines are excluded deliberately: the block's header explains the
    defect, and a naive substring scan reds on the prose documenting the fix —
    the same distinction `test_the_denial_surface_ROUTES_NOTHING` draws.
    """
    claim_words = re.compile(r"commit|push|uncommitted|salvage", re.IGNORECASE)
    offenders = []
    for line in _turn_cap_block().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "worktree_delivery_state" in stripped:
            continue
        if claim_words.search(stripped):
            offenders.append(stripped)
    assert not offenders, (
        f"the turn-cap banner states delivery facts it did not read: {offenders} "
        f"— every such claim belongs in worktree_delivery_state, which looks"
    )


def test_the_banner_actually_CALLS_the_reader() -> None:
    """The mirror of the test above, and without it that one passes against a
    banner that says nothing at all — a report with no content is not a fix."""
    assert 'worktree_delivery_state "$wt"' in _turn_cap_block()

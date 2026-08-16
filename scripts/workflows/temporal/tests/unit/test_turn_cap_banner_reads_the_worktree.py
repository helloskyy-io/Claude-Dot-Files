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

AND IT IS RUN UNDER BOTH CALLERS' SHELL OPTIONS, BECAUSE THERE ARE TWO AND THEY
DIFFER. An earlier version of this file ran only `set -euo pipefail` and called
that "the CALLER's shape" — singular. It is V1's: each of the five children sets
it and calls `run_claude` unguarded, so a non-zero exit anywhere in this function
kills the workflow inside the banner that exists to explain why it died. But the
V2 Python fleet — the one the migration is moving toward — sources this file with
NO options at all (`assistant_activities.py`: `bash -c 'source "$runner";
run_claude "$1"'`), and `run-claude.sh` sets none itself. That gap was not
cosmetic: under it, `x=$(git ... | wc -l)` takes `wc`'s exit status, and `wc -l`
on empty stdin succeeds printing `0`, so a FAILED git read as "zero commits
ahead" and the function claimed `✓ fully pushed` — issue #65's defect rebuilt
inside issue #65's fix, on the only fleet with a future. Every case below runs
under both shapes, so a regression reachable from only one of them cannot pass.

BOTH DIRECTIONS, PER ARM. Each state that produces a report is driven with a
real git repository built for it, and the fully-pushed arm — the one the
original banner got wrong — is asserted to still make its claim. A banner that
never claims anything is not a fix.
"""

from __future__ import annotations

import os
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
# The reader delegates its four no-local-answer arms to this helper, so the
# extraction has to carry it. Pulled by its own boundaries rather than by a
# widened span, so that a reader which stopped delegating still extracts.
_UNDETERMINED_FN = re.compile(r"^_wds_undetermined\(\) \{\n.*?\n\}$",
                              re.DOTALL | re.MULTILINE)

# The two caller shapes, by name. `run-claude.sh` sets no options itself, so
# whatever the caller set is what this function runs under.
#   v1 — the five bash children, all `set -euo pipefail`
#   v2 — the Python fleet's `bash -c 'source ...; run_claude "$1"'`, no options
_CALLER_SHAPES = {"v1_errexit_pipefail": "set -euo pipefail", "v2_no_options": ""}


def _shipped_state_reader() -> str:
    source = RUN_CLAUDE.read_text()
    m = _STATE_FN.search(source)
    assert m, "run-claude.sh no longer defines worktree_delivery_state"
    body = m.group(0)
    # Positive control on the EXTRACTOR, not on the function: a regex that
    # matched an empty or truncated span would make every assertion below run
    # against nothing and pass the negative ones.
    assert body.count("\n") > 20, f"the extraction is too short to be the reader:\n{body}"
    helper = _UNDETERMINED_FN.search(source)
    assert helper, "run-claude.sh no longer defines _wds_undetermined"
    return f"{helper.group(0)}\n{body}"


@pytest.fixture(params=sorted(_CALLER_SHAPES), ids=sorted(_CALLER_SHAPES))
def describe(request: pytest.FixtureRequest):
    """The shipped reader, run under ONE caller's shell options.

    Parametrized rather than defaulted: a helper that picks a shape has a shape
    it does not run, and the untested one is where the defect lived.
    """
    preamble = _CALLER_SHAPES[request.param]

    def run(wt: Path | str) -> str:
        out = subprocess.run(
            ["bash", "-c", f"{preamble}\n{_shipped_state_reader()}\n"
                           'worktree_delivery_state "$1"', "_", str(wt)],
            capture_output=True, text=True,
        )
        assert out.returncode == 0, (
            f"the reader exited {out.returncode} under {request.param} — every "
            f"V1 child calls run_claude unguarded, so this kills the workflow "
            f"inside its own failure banner:\n{out.stderr}"
        )
        return out.stdout

    return run


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

def test_a_fully_pushed_tree_is_NOT_reported_as_unsalvaged_work(pushed_tree: Path, describe) -> None:
    """PR #56, reproduced. Nothing here may claim work is uncommitted or unpushed."""
    out = describe(pushed_tree)
    assert "fully pushed" in out
    assert "CHECK THE PR BEFORE REDISPATCHING" in out, (
        "the pushed arm has to send the operator to the PR — telling them to "
        "salvage the tree is what cost a second budget"
    )
    assert "UNCOMMITTED" not in out and "NOT pushed" not in out, out


# ---------------------------------------------------------------------------
# The states the report legitimately describes.
# ---------------------------------------------------------------------------

def test_uncommitted_changes_are_reported_with_a_count(pushed_tree: Path, describe) -> None:
    """The banner's original claim, now made only when it is true."""
    (pushed_tree / "b.txt").write_text("b\n")
    out = describe(pushed_tree)
    assert re.search(r"✗ 1 path\(s\) carry UNCOMMITTED changes", out), out


def test_committed_but_unpushed_commits_are_reported_with_a_count(pushed_tree: Path, describe) -> None:
    """The middle state the one-sentence banner had no way to express.

    UNCOMMITTED AND UNPUSHED ARE INDEPENDENT: this tree is clean AND has work
    the remote does not have, and the report says both.
    """
    (pushed_tree / "c.txt").write_text("c\n")
    _git(pushed_tree, "add", "-A")
    _git(pushed_tree, "commit", "-qm", "second")
    out = describe(pushed_tree)
    assert re.search(r"✗ 1 commit\(s\) on 'work' are NOT pushed to 'origin/work'", out), out
    assert "Working tree is clean" in out, out


def test_uncommitted_AND_unpushed_are_reported_SEPARATELY(pushed_tree: Path, describe) -> None:
    """The shape a single sentence cannot carry, and the reason there are two.

    THE FIXTURE VARIES IN SHAPE, not in a value: both facts are true at once, so
    a reader that derived one from the other — however it spelled the derivation
    — comes back with one line here instead of two.
    """
    (pushed_tree / "c.txt").write_text("c\n")
    _git(pushed_tree, "add", "-A")
    _git(pushed_tree, "commit", "-qm", "second")
    (pushed_tree / "d.txt").write_text("d\n")
    out = describe(pushed_tree)
    assert "UNCOMMITTED changes" in out and "are NOT pushed" in out, out


# ---------------------------------------------------------------------------
# The third state: no local answer. Each of these is its own arm, because
# collapsing any of them into "nothing was pushed" rebuilds the defect.
# ---------------------------------------------------------------------------

def test_a_worktree_that_is_gone_is_UNDETERMINED_not_clean(tmp_path: Path, describe) -> None:
    out = describe(tmp_path / "removed-after-the-run")
    assert "NOT on disk" in out, out
    assert "cannot be determined" in out, out


def test_a_branch_with_no_upstream_is_UNDETERMINED_not_unpushed(tmp_path: Path, describe) -> None:
    """`git log <upstream>..HEAD` has no meaning here, so no count is invented."""
    wt = tmp_path / "solo"
    subprocess.run(["git", "init", "-q", "-b", "solo", str(wt)], check=True)
    (wt / "a.txt").write_text("a\n")
    _git(wt, "add", "-A")
    _git(wt, "commit", "-qm", "x")
    out = describe(wt)
    assert "has no upstream ref" in out and "cannot be" in out, out
    assert "NOT pushed" not in out, out


def test_a_detached_HEAD_is_UNDETERMINED(pushed_tree: Path, describe) -> None:
    """A worktree dispatch can leave a detached HEAD; there is no branch to
    compare, and guessing one is how a wrong count gets printed."""
    _git(pushed_tree, "checkout", "-q", "--detach", "HEAD")
    out = describe(pushed_tree)
    assert "detached" in out and "no local answer" in out, out


def test_a_leftover_directory_does_not_get_the_PARENT_repo_s_answer(pushed_tree: Path, describe) -> None:
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
    out = describe(leftover)
    assert "is not a worktree root" in out, out
    assert "cannot be determined" in out, out
    assert "fully pushed" not in out, "it answered with the parent repository's state"


def test_a_directory_that_is_not_in_any_repository_is_UNDETERMINED(tmp_path: Path, describe) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    out = describe(plain)
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


def test_the_banner_makes_no_delivery_claim_of_its_OWN(describe) -> None:
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


def test_the_banner_actually_CALLS_the_reader(describe) -> None:
    """The mirror of the test above, and without it that one passes against a
    banner that says nothing at all — a report with no content is not a fix."""
    assert 'worktree_delivery_state "$wt"' in _turn_cap_block()


# ---------------------------------------------------------------------------
# The arm that was caller-shape dependent, driven directly.
# ---------------------------------------------------------------------------

# EVERY subcommand that could implement the ahead-count, not the one that does.
# Keying the shim on `rev-list` alone made this test implementation-coupled:
# mutating the reader back to the broken `git log ... | wc -l` form simply moved
# it out of the shim's way, so the test went red for "rev-list is gone" instead
# of for the property it names — and it went red under BOTH shapes, hiding the
# very divergence it exists to pin. Measured: predicted 1 failure, observed 2.
_AHEAD_COUNT_SUBCOMMANDS = ("rev-list", "log", "cherry")


def _describe_with_failing_push_check(
    wt: Path, shim_dir: Path, preamble: str,
) -> str:
    """Run the reader with a `git` that fails for any ahead-count subcommand.

    A SHIM RATHER THAN A CORRUPTED REPO, and that is the point of it. The states
    that make `git rev-list` fail for real — a pruned object behind a live ref,
    a half-written pack — are hard to build and harder to keep stable across git
    versions, so a test that tried would be testing git. What has to be pinned is
    THIS function's behaviour when its own check fails, which is a property of
    how the exit status is captured, not of why git failed. Everything else git
    is asked here still answers truthfully, so the other arms are unaffected and
    the reader reaches the push check with a real branch and a real upstream.
    """
    real = shutil.which("git")
    assert real, "git is required"
    shim = shim_dir / "git"
    cases = "|".join(_AHEAD_COUNT_SUBCOMMANDS)
    shim.write_text(
        "#!/usr/bin/env bash\n"
        f'for a in "$@"; do case "$a" in {cases}) exit 128 ;; esac; done\n'
        f'exec {real} "$@"\n'
    )
    shim.chmod(0o755)
    out = subprocess.run(
        ["bash", "-c", f"{preamble}\n{_shipped_state_reader()}\n"
                       'worktree_delivery_state "$1"', "_", str(wt)],
        capture_output=True, text=True,
        env={**os.environ, "PATH": f"{shim_dir}{os.pathsep}{os.environ['PATH']}"},
    )
    assert out.returncode == 0, out.stderr
    return out.stdout


@pytest.mark.parametrize("shape", sorted(_CALLER_SHAPES), ids=sorted(_CALLER_SHAPES))
def test_a_FAILED_push_check_is_reported_unknown_under_EITHER_caller(
    pushed_tree: Path, tmp_path: Path, shape: str,
) -> None:
    """The residual instance of issue #65, inside issue #65's own fix.

    `unpushed=$(git log ... | wc -l) || unpushed=""` takes the PIPELINE's exit
    status, which is `wc`'s — and `wc -l` on empty stdin SUCCEEDS printing `0`.
    Under `set -o pipefail` (V1) that is masked, because pipefail promotes git's
    failure. Under the V2 caller's optionless shell it is not, so a git that
    could not answer produced `unpushed="0"` and the reader printed
    `✓ fully pushed` — a delivery claim manufactured by a check that FAILED,
    which is the exact defect this file exists to close.

    The shipped form is `git rev-list --count`: ONE command, so the status the
    `||` sees is git's own and the arm is correct under both shapes. This test
    is parametrized over both because under only V1 it passed against the broken
    version too.
    """
    shim_dir = tmp_path / f"shim-{shape}"
    shim_dir.mkdir()
    out = _describe_with_failing_push_check(
        pushed_tree, shim_dir, _CALLER_SHAPES[shape]
    )
    assert "pushed state unknown" in out, out
    assert "fully pushed" not in out, (
        f"under {shape} the reader claimed the work was pushed from a git "
        f"invocation that FAILED:\n{out}"
    )

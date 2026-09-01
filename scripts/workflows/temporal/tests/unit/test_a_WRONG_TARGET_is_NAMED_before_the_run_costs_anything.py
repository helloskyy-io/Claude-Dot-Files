"""Point a run at the wrong component and it says so, before it spends anything.

THIS IS THE DEMONSTRATION, NOT AN ASSERTION ABOUT THE CODE. Workflow
Decomposition Phase 4 requirement 5 says a wrong derivation must be DEMONSTRATED
to be visible, and explicitly that it is not to be established by reading the
implementation. So this drives a real entrypoint's `main()` on the LIVE path,
with a real repository on disk, pointed at a component that is not the one
intended, and reads what actually came out of stderr.

WHY THE TARGET AND NOT SOME OTHER FIELD. Every other value on the run context
fails loudly somewhere: a bad `--repo` is refused by preflight, an unusable
journal root stops the run, a wrong `--pr` fails at `gh`. A wrong TARGET does
none of that. The run reads real files, plans a real component, opens a real
pull request, and nothing anywhere goes red — the operator finds out when they
read the PR. That asymmetry is the entire reason the echo exists.

WHAT "BEFORE THE RUN COSTS ANYTHING" IS PINNED TO HERE. The first side effect on
a run's WORK is the bag directory, then the worktree, then `gh`, then the model.
This drives the entrypoint with bag-open replaced by a raise, so reaching the
echo proves it precedes all four. One thing does happen earlier and is stated
rather than hidden: resolving the journal root creates it at 0700 if it is
absent, because the echo NAMES that root and cannot name what has not been
resolved. Nothing is spent, nothing is dispatched, and nothing is posted.

⚠ WHAT THIS DOES NOT PROVE. It shows the echo reaches stderr on one entrypoint's
live path. That every entrypoint builds and echoes a context is a separate,
population-wide sweep in `test_dispatch_context.py`; that no call site re-derives
the worktree name is `test_a_worktree_NAME_comes_from_the_RUN_CONTEXT.py`.

THE TRANSCRIPT, CAPTURED VERBATIM ON 2026-09-01 from a shell, against a scratch
repository holding two components — `RIGHT` and `WRONG` — with the wrong one
asked for and `open_run_bag` replaced by a raise so the run stops at its first
side effect. This is the output, not a reconstruction of it:

    $ python3 -c '<stub open_run_bag>; run_plan_draft.main(
        ["development/edge-assistant/WRONG", "--repo", "/tmp/demo-wrong-target"])'
    journal: run id 6d563e5c4fa84609895c711c9102b57e (minted here — pass `--run-id 6d563e5c4fa84609895c711c9102b57e` to retry this run into the same bag)
    run context — derived here, before anything is created:
      run       : 6d563e5c4fa84609895c711c9102b57e
      workflow  : plan-draft
      repo root : /tmp/demo-wrong-target
      journal   : /tmp/demo-journal-root/journal
      worktree  : plan-draft-1788242234
      target    : development/edge-assistant/WRONG
      pr        : (a new one will be opened)

    ✗ STOPPED HERE BY THE DEMONSTRATION — nothing was cut, nothing was posted
    (exit 1)

The `target` line is the whole point: it is the last moment before the run cuts a
worktree and starts spending, and it names the component in the operator's own
vocabulary rather than leaving it in a path three call frames down. `.claude/
worktrees/` did not exist in that repository afterwards, and no `gh` process ran.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

FLEET = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(FLEET / "scripts"))

import run_plan_draft  # noqa: E402

RIGHT = "development/edge-assistant/fleet-reliability"
WRONG = "development/edge-assistant/workflow-decomposition"


class _FirstSideEffect(RuntimeError):
    """Raised in place of bag-open, so anything after it is provably unreached."""


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A real repository holding two components, one of which is the wrong one."""
    for name in (RIGHT, WRONG):
        (tmp_path / name).mkdir(parents=True)
        (tmp_path / name / "roadmap.md").write_text("# roadmap\n", encoding="utf-8")
    (tmp_path / "tracked" / "candidates").mkdir(parents=True)
    for cmd in (["git", "init", "-q"],
                ["git", "config", "user.email", "t@example.com"],
                ["git", "config", "user.name", "t"],
                ["git", "add", "-A"],
                ["git", "commit", "-qm", "seed"]):
        subprocess.run(cmd, cwd=tmp_path, check=True, capture_output=True)
    return tmp_path


def test_a_run_pointed_at_the_WRONG_component_NAMES_IT_on_stderr(
        repo: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """The live path — not `--dry-run`, which is the mode where nothing is at stake."""
    monkeypatch.setattr(
        run_plan_draft.journal, "open_run_bag",
        lambda **kw: (_ for _ in ()).throw(_FirstSideEffect("bag would open here")))

    exit_code = run_plan_draft.main([WRONG, "--repo", str(repo)])

    err = capsys.readouterr().err
    assert exit_code == 1, "the stand-in for the first side effect did not stop the run"
    assert "run context" in err, (
        f"the live run said nothing about what it derived:\n{err}")
    assert WRONG in err, (
        f"the run derived {WRONG!r} and never named it — an operator watching "
        f"this could not tell it from a run against {RIGHT!r}:\n{err}")
    assert "plan-draft-" in err, "the derived worktree name is not in the echo"


def test_THE_ECHO_PRECEDES_the_first_side_effect(
        repo: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """Ordering, read off the output rather than argued from the source.

    The stand-in for bag-open writes its own marker. If the echo appeared after
    it — or not at all — the marker would come first, which is the failure this
    orders against: an echo *somewhere in the transcript* is not an echo *before
    the run commits*.
    """
    def refuse(**kw):
        print("FIRST-SIDE-EFFECT", file=sys.stderr, flush=True)
        raise _FirstSideEffect("bag would open here")

    monkeypatch.setattr(run_plan_draft.journal, "open_run_bag", refuse)
    run_plan_draft.main([WRONG, "--repo", str(repo)])

    err = capsys.readouterr().err
    assert "FIRST-SIDE-EFFECT" in err, "the stand-in never ran, so nothing is ordered"
    assert err.index("run context") < err.index("FIRST-SIDE-EFFECT"), (
        f"the context was stated AFTER the run's first side effect:\n{err}")


def test_NOTHING_WAS_CUT_and_NOTHING_WAS_POSTED(
        repo: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """The demonstration must itself be free — otherwise it is not a demonstration.

    A worktree on disk or a `gh` invocation would mean the echo arrived after the
    run had already committed to something, which is the property under test
    inverted. Both are replaced by raising stand-ins: reaching either is a
    failure, and neither is reached.
    """
    reached: list[str] = []

    def forbid(label):
        def stub(*a, **k):
            reached.append(label)
            raise AssertionError(f"{label} ran before the echo could matter")
        return stub

    monkeypatch.setattr(run_plan_draft.act, "worktree_add", forbid("worktree_add"))
    monkeypatch.setattr(run_plan_draft.act_shared, "gh", forbid("gh"))
    monkeypatch.setattr(
        run_plan_draft.journal, "open_run_bag",
        lambda **kw: (_ for _ in ()).throw(_FirstSideEffect("bag would open here")))

    run_plan_draft.main([WRONG, "--repo", str(repo)])

    assert reached == [], f"the run reached {reached} before it was stopped"
    assert not (repo / ".claude" / "worktrees").exists(), \
        "a worktree was cut before the operator could read the echo"
    assert WRONG in capsys.readouterr().err

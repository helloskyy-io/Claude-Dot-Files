"""`merge-pr` merges the base into a stale planning PR, regenerates, verifies, pushes — then REFUSES.

`development/derived/*` carry an input digest over the whole corpus and CI
checks them against the MERGE REF, so every commit on `main` makes every open
planning PR stale. The `regenerate-on-merge` githook regenerates correctly but
only locally; GitHub merges server-side with no hooks. Measured on skyynet #67:
nine days, three hand merges, and the order that works is merge FIRST,
regenerate SECOND.

EVERYTHING HERE IS REAL GIT against a local bare `origin`, with the REAL hook
and the REAL launcher from this tooling checkout — the only fake is the one
`gh pr view` that names the PR's head and base. A model of `git merge` would
pass while the hook's veto-then-commit shape silently broke.

The user's git config is masked so a `core.hooksPath` or `commit.gpgsign` on
the developer's machine cannot make these pass or fail for an unstated reason.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from modules.assistant.merge import merge_pr

HOOK = (merge_pr.PLANNING_UI.parent / "planning_ui" / "githooks" / "regenerate-on-merge")

ROADMAP = """# {name}

**Status:** 🟠 PLANNED — {note}

## Only Phase 🟠 PLANNED — **~5h**

**Implementation:** [`phase1_only.md`](phase1_only.md)

**Depends on:** NONE
"""

SPRINTS = """# Sprints

## Sprint: One 🟡 IN PROGRESS

- [ ] **common/alpha · Only Phase** · L0 · ([roadmap](./common/alpha/roadmap.md) · [phase](./common/alpha/phase1_only.md)) — x · **~5h**
"""


@pytest.fixture(autouse=True)
def _masked_git(monkeypatch: pytest.MonkeyPatch) -> None:
    """`run_bounded` inherits the environment, so the masking is set there."""
    monkeypatch.delenv("PYTHONPATH", raising=False)
    for k, v in dict(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
                     GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                     GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t").items():
        monkeypatch.setenv(k, v)


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                          text=True, check=check, timeout=60)


def _generate(repo: Path) -> None:
    subprocess.run([str(merge_pr.PLANNING_UI)], cwd=repo, capture_output=True,
                   text=True, check=True, timeout=120)


def _roadmap(repo: Path, component: str, note: str) -> None:
    folder = repo / "development" / "common" / component
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "roadmap.md").write_text(ROADMAP.format(name=component.title(), note=note))
    (folder / "phase1_only.md").write_text(f"# {component} phase\n")


def _land(seed: Path, component: str, note: str, message: str) -> None:
    """Edit a roadmap, regenerate, commit, push — what every planning lane does."""
    _roadmap(seed, component, note)
    _generate(seed)
    _git(seed, "add", "-A")
    _git(seed, "commit", "-qm", message)
    _git(seed, "push", "-q", "origin", "HEAD")


@pytest.fixture
def repos(tmp_path: Path) -> dict[str, Path]:
    """A bare `origin`, a `seed` clone that plays everyone else, and the
    operator's `local` clone that `merge-pr` runs in. The PR branch `lane`
    starts at `main`'s tip; each test moves `main` (or not) itself."""
    origin, seed, local = tmp_path / "origin.git", tmp_path / "seed", tmp_path / "local"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    subprocess.run(["git", "clone", "-q", str(origin), str(seed)], check=True,
                   capture_output=True)
    (seed / ".gitattributes").write_text("development/derived/* merge=binary\n")
    _roadmap(seed, "alpha", "base")
    _roadmap(seed, "beta", "base")
    (seed / "development" / "sprints.md").write_text(SPRINTS)
    for store in ("candidates", "issues", "operations", "standards"):
        (seed / "tracked" / store).mkdir(parents=True)
        (seed / "tracked" / store / ".keep").write_text("")
    _generate(seed)
    _git(seed, "add", "-A")
    _git(seed, "commit", "-qm", "corpus and artifacts")
    _git(seed, "push", "-q", "origin", "main")

    _git(seed, "checkout", "-qb", "lane")
    _land(seed, "alpha", "edited on the PR", "the PR's change")
    _git(seed, "checkout", "-q", "main")

    subprocess.run(["git", "clone", "-q", str(origin), str(local)], check=True,
                   capture_output=True)
    return {"origin": origin, "seed": seed, "local": local}


def _register(repo: Path, *, driver: bool = True) -> None:
    """The per-clone registration the hook's header records. `driver=False`
    leaves the derived/ conflict WHOLE, which is the path that takes the base's
    side before the pre-commit hook regenerates."""
    if driver:
        _git(repo, "config", "merge.binary.driver", "true")
    hooks = repo / ".git" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    for name in ("pre-merge-commit", "pre-commit"):
        (hooks / name).symlink_to(HOOK)


@pytest.fixture
def gh(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """The one GitHub read: which branch the PR is, onto which base."""
    calls: list[list[str]] = []

    def view(args, root):
        calls.append(args)
        return {"headRefName": "lane", "baseRefName": "main", "isCrossRepository": False}
    monkeypatch.setattr(merge_pr, "_gh_json", view)
    return calls


def _remote(repo: Path, ref: str) -> str:
    return _git(repo, "ls-remote", "origin", f"refs/heads/{ref}").stdout.split()[0]


def _no_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    """THE NO-WAIT PROPERTY, DRIVEN. `test_the_merge_path_does_NOT_wait_for_CI`
    pins the module's sleep sites; this proves the refresh path reaches none."""
    def boom(*a, **k):
        raise AssertionError("the refresh path waited")
    monkeypatch.setattr(merge_pr.time, "sleep", boom)
    monkeypatch.setattr(merge_pr.act, "wait_for_ci", boom)


# --- the positive control: an unmoved base does NOTHING ----------------------


def test_an_UNMOVED_base_does_NOTHING(repos, gh, monkeypatch) -> None:
    """THE CONTROL FOR EVERYTHING BELOW. Without it the refresh could fire on
    every merge and still pass the tests that matter. No worktree, no merge, no
    regeneration, no push — and the existing gates then run unchanged."""
    _register(repos["local"])
    before = _remote(repos["local"], "lane")

    def no_worktree(*a, **k):
        raise AssertionError("an unmoved base created a worktree")
    monkeypatch.setattr(merge_pr.tempfile, "mkdtemp", no_worktree)

    assert merge_pr.refresh_against_base("1", repos["local"]) is None
    assert _remote(repos["local"], "lane") == before


def test_an_UNMOVED_base_lets_run_merge_proceed_to_the_merge(repos, gh, monkeypatch) -> None:
    """…and through `run_merge`, the PR reaches `merge_one` exactly as before."""
    _register(repos["local"])
    monkeypatch.setattr(merge_pr, "refusals", lambda pr, root: [])
    merged: list[str] = []
    monkeypatch.setattr(merge_pr, "merge_one",
                        lambda pr, root, dry_run=False: merged.append(pr))
    report = merge_pr.run_merge(["1"], repos["local"])
    assert report.merged == ("1",) and merged == ["1"], report


def test_a_repo_with_NO_derived_dir_is_never_touched(tmp_path, gh) -> None:
    """`claude-dot-files` merges are untouched: not even the `gh` read happens."""
    assert merge_pr.refresh_against_base("1", tmp_path) is None
    assert gh == []


# --- main moved: merge, regenerate, verify, push, REFUSE ---------------------


@pytest.mark.parametrize("driver", [True, False],
                         ids=["driver-and-hooks: the veto path",
                              "hooks-only: a derived-only conflict, base's side taken"])
def test_a_MOVED_base_is_merged_regenerated_verified_PUSHED_and_REFUSED(
        repos, gh, monkeypatch, driver) -> None:
    _land(repos["seed"], "beta", "moved on main", "main moves")
    _register(repos["local"], driver=driver)
    _no_wait(monkeypatch)
    main_tip = _remote(repos["local"], "main")

    why = merge_pr.refresh_against_base("1", repos["local"])

    assert why and "pushed" in why and "Not merged" in why, why
    pushed = _remote(repos["local"], "lane")
    # The new head descends from main's tip: merged FIRST…
    _git(repos["local"], "fetch", "-q", "origin")
    assert _git(repos["local"], "merge-base", "--is-ancestor", main_tip, pushed,
                check=False).returncode == 0
    # …and its artifacts are current against the merged corpus: regenerated SECOND.
    fresh = repos["local"].parent / "fresh"
    _git(repos["local"], "worktree", "add", "-q", "--detach", str(fresh), pushed)
    check = subprocess.run([str(merge_pr.PLANNING_UI), "--repo-root", str(fresh), "--check"],
                           capture_output=True, text=True, timeout=120)
    assert check.returncode == 0, check.stdout + check.stderr
    for note in ("edited on the PR", "moved on main"):
        assert note in "".join(p.read_text() for p in
                               (fresh / "development" / "common").glob("*/roadmap.md"))
    # The throwaway worktree is gone; only the one this test made remains.
    assert len(_git(repos["local"], "worktree", "list").stdout.splitlines()) == 2


def test_a_refresh_REFUSES_even_when_the_gate_has_not_seen_the_push(
        repos, gh, monkeypatch) -> None:
    """The gate reads GitHub; GitHub may answer for the OLD head for a moment
    after the push and find nothing wrong. The refusal must not depend on it —
    otherwise `gh pr merge` would land a head CI never ran on."""
    _land(repos["seed"], "beta", "moved on main", "main moves")
    _register(repos["local"])
    monkeypatch.setattr(merge_pr, "refusals", lambda pr, root: [])

    def must_not(*a, **k):
        raise AssertionError("merged a freshly pushed head")
    monkeypatch.setattr(merge_pr, "merge_one", must_not)

    report = merge_pr.run_merge(["1"], repos["local"])
    assert report.merged == () and len(report.refused) == 1, report
    assert "pushed" in report.refused[0][1]


def test_a_DRY_RUN_on_a_moved_base_pushes_nothing(repos, gh) -> None:
    _land(repos["seed"], "beta", "moved on main", "main moves")
    _register(repos["local"])
    before = _remote(repos["local"], "lane")
    why = merge_pr.refresh_against_base("1", repos["local"], dry_run=True)
    assert why and "would merge" in why, why
    assert _remote(repos["local"], "lane") == before


# --- the refusals that protect main ------------------------------------------


def test_a_conflict_OUTSIDE_derived_is_ABORTED_and_named(repos, gh) -> None:
    """A real content conflict is a human's. Never auto-resolved toward either side."""
    _land(repos["seed"], "alpha", "a rival edit on main", "main edits the same roadmap")
    _register(repos["local"])
    before = _remote(repos["local"], "lane")

    why = merge_pr.refresh_against_base("1", repos["local"])

    assert why and "development/common/alpha/roadmap.md" in why, why
    assert "nothing was pushed" in why
    assert _remote(repos["local"], "lane") == before


def test_a_FAILED_check_pushes_NOTHING(repos, gh) -> None:
    """THE ONE THAT PROTECTS MAIN. An unregistered clone stops on the whole-file
    derived/ conflict; the base's side is taken and nothing regenerates over it,
    so the merged corpus and its artifacts disagree — and `--check` says so."""
    _land(repos["seed"], "beta", "moved on main", "main moves")
    before = _remote(repos["local"], "lane")

    why = merge_pr.refresh_against_base("1", repos["local"])

    assert why and "--check` exited" in why and "NOTHING WAS PUSHED" in why, why
    assert _remote(repos["local"], "lane") == before

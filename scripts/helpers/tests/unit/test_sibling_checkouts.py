"""Work left in a repo the dispatch was not pointed at, and the sweep that finds it.

WHY THIS EXISTS. Every instrument a dispatch has watches ONE repo: the diff, the PR,
the CI gate, the review. A run that changes code in one repo and planning docs in a
sibling leaves the second half visible to none of them. Measured the day it landed:
`mdc-master-planning` sat on a local branch with ten unpushed commits.

THE VACUITY ARM IS THE ONE THAT MATTERS. A sweep pointed at a directory with no
checkouts finds nothing and would otherwise print a clean bill of health for a
question it never asked.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[3] / "helpers" / "sibling_checkouts.py"


def _repo(root: Path, name: str) -> Path:
    """A checkout with an `origin` that has a real default branch."""
    origin = root / f"{name}.git"
    # `-b main` ON THE ORIGIN, because that is what the clone inherits. Without
    # it the local branch comes from the CLONING MACHINE's `init.defaultBranch`,
    # so this fixture built a checkout on `master` on any host that had not been
    # configured — the sweep then correctly reported it as off its default
    # branch and the POSITIVE control failed. Green on the author's box, red on
    # every GitHub runner: the fixture was asserting a fact about the host.
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    d = root / name
    subprocess.run(["git", "clone", "-q", str(origin), str(d)], check=True)
    # ⚠ THE LOCAL BRANCH IS NAMED EXPLICITLY, BECAUSE `init.defaultBranch` IS A
    # PROPERTY OF THE MACHINE. Cloning an empty bare repo leaves an unborn
    # branch named by the host's git config — `main` on a workstation that sets
    # it, `master` on a stock GitHub runner. This fixture then pushed `HEAD:main`
    # and set origin's head to `main`, so on the runner the checkout WAS off its
    # default branch and the sweep correctly reported it: `test_a_CLEAN_
    # WORKSPACE_PASSES` failed on every CI run while passing locally. The test
    # was asserting a fact about the author's git config.
    subprocess.run(["git", "-C", str(d), "symbolic-ref", "HEAD",
                    "refs/heads/main"], check=True)
    subprocess.run(["git", "-C", str(d), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(d), "config", "user.name", "t"], check=True)
    (d / "f.txt").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(d), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(d), "commit", "-qm", "init"], check=True)
    subprocess.run(["git", "-C", str(d), "push", "-q", "-u", "origin", "HEAD:main"], check=True)
    subprocess.run(["git", "-C", str(d), "remote", "set-head", "origin", "main"], check=True)
    return d


def _run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOL), "--root", str(root), "--check"],
                          capture_output=True, text=True)


def test_a_CLEAN_WORKSPACE_PASSES(tmp_path: Path) -> None:
    """The positive control. Without it every assertion below is satisfied by a
    sweep that flags everything."""
    _repo(tmp_path, "alpha")
    r = _run(tmp_path)
    assert r.returncode == 0, r.stdout
    assert "clean" in r.stdout


def test_A_CHECKOUT_OFF_ITS_DEFAULT_BRANCH_IS_REPORTED(tmp_path: Path) -> None:
    """THE MUTATION, and the exact live shape: parked on a feature branch with work on it."""
    d = _repo(tmp_path, "alpha")
    subprocess.run(["git", "-C", str(d), "checkout", "-qb", "side"], check=True)
    (d / "g.txt").write_text("y\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(d), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(d), "commit", "-qm", "stranded"], check=True)

    r = _run(tmp_path)
    assert r.returncode == 1, r.stdout
    assert "on `side`, not `main`" in r.stdout and "1 unpushed" in r.stdout


def test_AN_EXCLUDED_REPO_IS_NOT_REPORTED(tmp_path: Path) -> None:
    """The dispatch's OWN repo is expected to be mid-work — reporting it every run is
    how a sweep teaches its reader to skip it."""
    d = _repo(tmp_path, "alpha")
    subprocess.run(["git", "-C", str(d), "checkout", "-qb", "side"], check=True)
    r = subprocess.run([sys.executable, str(TOOL), "--root", str(tmp_path),
                        "--exclude", "alpha", "--check"], capture_output=True, text=True)
    assert "alpha" not in r.stdout.split("WORK OUTSIDE")[-1]


def test_A_SWEEP_WITH_NO_CHECKOUTS_REFUSES_RATHER_THAN_PASSING(tmp_path: Path) -> None:
    """⚠ THE VACUITY CONTROL. A sweep whose population is empty found nothing because
    it looked at nothing, and `clean` would be a claim it has no basis for. The
    mutation is the empty directory itself — the state a wrong `--root` produces.
    """
    (tmp_path / "not-a-repo").mkdir()
    r = _run(tmp_path)
    assert r.returncode == 1, r.stdout
    assert "asserts nothing" in r.stdout
    assert "clean" not in r.stdout, (
        f"an empty sweep must not report clean — that is an absent check wearing a "
        f"green result: {r.stdout}")

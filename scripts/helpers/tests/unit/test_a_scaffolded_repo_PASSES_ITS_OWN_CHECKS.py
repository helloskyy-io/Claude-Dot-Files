"""A repo `init-project.sh` creates must be green on the checks it scaffolds.

WHY THIS IS THE TEST AND NOT "the workflow file exists". A scaffold that ships a
CI workflow its own output FAILS is worse than one shipping none: the first thing
a new project does is go red, and the first thing its owner learns is that this
repo's CI is noise. Measured while building it — the scaffolded map carried two
continuation lines and the map check the same scaffold installs rejected them.

IT RUNS THE REAL SCRIPT AND THE REAL CHECKS. A test that re-implemented what
`init-project.sh` writes would agree with itself while the script drifted.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HELPERS = Path(__file__).resolve().parents[2]
INIT = HELPERS / "init-project.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None or not INIT.is_file(),
    reason="needs git and init-project.sh")


#: THE IDENTITY IS SUPPLIED, NOT ASSUMED. `init-project.sh` ends in a `git
#: commit`, which needs an author; a machine with no configured identity fails
#: it with exit 128 after the scaffold is already written. That is git's
#: behaviour and not this test's subject — what these tests assert is that a
#: scaffolded repo is GREEN ON THE CHECKS IT SHIPS. Without this the fixture
#: quietly asserted that the running host had a global git identity, which is
#: true of a workstation and false of every clean CI runner.
_IDENTITY = {
    "GIT_AUTHOR_NAME": "scaffold probe",
    "GIT_AUTHOR_EMAIL": "probe@example.invalid",
    "GIT_COMMITTER_NAME": "scaffold probe",
    "GIT_COMMITTER_EMAIL": "probe@example.invalid",
}


@pytest.fixture(scope="module")
def scaffold(tmp_path_factory) -> Path:
    d = tmp_path_factory.mktemp("scaffold") / "probe-repo"
    d.mkdir()
    r = subprocess.run(["bash", str(INIT), "probe-repo", "--skip-remote"],
                       cwd=d, capture_output=True, text=True, timeout=180,
                       env={**os.environ, **_IDENTITY})
    assert r.returncode == 0, f"init-project.sh failed:\n{r.stdout}\n{r.stderr}"
    return d


def test_IT_REFUSES_BEFORE_WRITING_ANYTHING_WHEN_GIT_HAS_NO_IDENTITY(tmp_path: Path) -> None:
    """The preflight refuses on an EMPTY directory, not after scaffolding.

    Before this guard the script wrote ~16 files and only THEN failed at the
    commit (git's exit 128), leaving a half-built repo with no commit. The
    preflight checks `git var GIT_AUTHOR_IDENT` before Step 1, so a host with no
    identity exits 1 having touched nothing. This also pins the probe against the
    regression that shipped once: `git config user.name` cannot see the
    GIT_AUTHOR_* env the fixture above supplies, so it would refuse an identity
    `git commit` accepts. `git var GIT_AUTHOR_IDENT` reads the same source the
    commit will, so the two never disagree.
    """
    d = tmp_path / "no-identity-repo"
    d.mkdir()
    # Remove EVERY identity source: the author/committer env vars, and the global
    # and system config files, so git genuinely cannot determine an author.
    env = {k: v for k, v in os.environ.items()
           if k not in {"GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL",
                        "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"}}
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_SYSTEM"] = os.devnull
    r = subprocess.run(["bash", str(INIT), "no-identity-repo", "--skip-remote"],
                       cwd=d, capture_output=True, text=True, timeout=180, env=env)
    assert r.returncode == 1, (
        f"expected the identity preflight to refuse with exit 1 (not git's late "
        f"exit 128), got {r.returncode}:\n{r.stdout}\n{r.stderr}")
    wrote = list(d.iterdir())
    assert not wrote, (
        f"the preflight let the script write before refusing — a half-scaffolded "
        f"repo is the exact defect it exists to prevent: {[p.name for p in wrote]}")


def test_IT_SCAFFOLDS_A_WORKFLOW_AND_ITS_POLICY_TOGETHER(scaffold: Path) -> None:
    """Neither exists without the other. `testing/README.md` states the rule — a
    policy with no workflow reports "declares a policy and none of it reported",
    which is false on every run — and scaffolding both is how it stops depending
    on anyone remembering.
    """
    wf = scaffold / ".github" / "workflows" / "checks.yml"
    policy = scaffold / "testing" / "check-policy.yaml"
    assert wf.is_file(), "no CI workflow scaffolded — the checks have no cadence"
    assert policy.is_file(), (
        "a workflow was scaffolded with no check-policy.yaml, so the build parent "
        "cannot learn which checks gate a merge")

    text = policy.read_text(encoding="utf-8")
    assert "blocking:" in text and "advisory:" in text, (
        "the policy declares neither list, and the Testing Standard admits no "
        "third state for a check that can fail")


def test_THE_FRESH_REPO_IS_GREEN_ON_THE_CHECKS_IT_SHIPS(scaffold: Path) -> None:
    """⚠ THE ONE THAT MATTERS. A scaffold whose own CI fails on day one teaches
    its owner that this repo's CI is noise — and it caught exactly that while
    being written: the scaffolded repo map carried two continuation lines, and the
    map check the same scaffold installs rejected them.
    """
    r = subprocess.run(
        [sys.executable, str(HELPERS / "file_structure_check.py"),
         "--repo-root", str(scaffold), "--check"],
        capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, (
        f"a freshly scaffolded repo fails the map check it ships with:\n{r.stdout}")


def test_THE_CHECKS_THAT_HAVE_NOTHING_TO_LOOK_AT_SAY_SO(scaffold: Path) -> None:
    """A step that stays silent on an empty population reads as a pass it never
    earned. A new repo legitimately has no standards, vendors none and has no
    suite — so each of those steps has to REPORT that rather than exit quietly.
    """
    wf = (scaffold / ".github" / "workflows" / "checks.yml").read_text(encoding="utf-8")
    for phrase in ("nothing to audit", "vendors no standards", "has no suite"):
        assert phrase in wf, (
            f"the workflow has no branch saying {phrase!r}, so a step with an "
            f"empty population would pass silently")
    assert wf.count("nothing asserted") >= 3, (
        "each empty-population branch must say nothing was asserted, or a green "
        "run is indistinguishable from a run that checked something")

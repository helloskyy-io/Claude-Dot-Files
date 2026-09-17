"""A repo `init-project.sh` scaffolds, given a corpus, derives its planning
views, is green on the viewer's `--check`, and goes RED on one edited line.

THIS IS THE END CONDITION OF HOSTING THE VIEWER IN THE TOOLING. The viewer
used to live inside the one planning repository it described; now it is
`scripts/services/planning-ui.sh` here, run from any planning repository by
path — the scaffolded CI step, the merge hook and an operator all use that
one entry point. So the proof is not "the package imports" but the whole
shape end to end: the real scaffold, the real launcher, a corpus a planning
dispatch would write, the artifacts committed, the gate green, and the gate
red the moment the corpus moves — because a `--check` that cannot go red is
not a gate.

What makes a repo a planning repo is the corpus contract's predicate — a
`development/sprints.md` — not anything this scaffold writes, so the same
scaffold yields a product repo the viewer REFUSES BY NAME. Asserted too:
the scaffolded CI step gates on that predicate, and a product repo's step
says it asserted nothing rather than failing.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

HELPERS = Path(__file__).resolve().parents[2]
INIT = HELPERS / "init-project.sh"
LAUNCHER = HELPERS.parent / "services" / "planning-ui.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None or not INIT.is_file() or not LAUNCHER.is_file(),
    reason="needs git, init-project.sh and planning-ui.sh")

_IDENTITY = {
    "GIT_AUTHOR_NAME": "scaffold probe",
    "GIT_AUTHOR_EMAIL": "probe@example.invalid",
    "GIT_COMMITTER_NAME": "scaffold probe",
    "GIT_COMMITTER_EMAIL": "probe@example.invalid",
}

#: The smallest corpus a planning dispatch writes: one component, one
#: roadmap, one phase doc, one sprint line placing the phase.
ROADMAP = """# Alpha

**Status:** 🟠 PLANNED — {note}

## Only Phase 🟠 PLANNED — **~5h**

**Implementation:** [`phase1_only.md`](phase1_only.md)

**Depends on:** NONE
"""

PHASE = """# Only Phase

**Status:** 🟠 PLANNED

- [ ] the one requirement
"""

SPRINTS = """# Sprints

## Sprint: One 🟡 IN PROGRESS

- [ ] **common/alpha · Only Phase** · L0 · ([roadmap](./common/alpha/roadmap.md) · [phase](./common/alpha/phase1_only.md)) — x · **~5h**
"""


def _env() -> dict[str, str]:
    # The user's git config masked, so a hooksPath or gpgsign on the host
    # cannot decide the outcome; NO PYTHONPATH, so the launcher's own
    # self-location is what is exercised.
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull, **_IDENTITY)
    return env


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          env=_env(), check=True, timeout=60)


def _viewer(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(LAUNCHER), "--repo-root", str(repo), *args], capture_output=True,
                          text=True, env=_env(), check=False, timeout=120)


def _scaffold(where: Path, name: str) -> Path:
    d = where / name
    d.mkdir()
    r = subprocess.run(["bash", str(INIT), name, "--skip-remote"], cwd=d, capture_output=True,
                       text=True, timeout=180, env=_env())
    assert r.returncode == 0, f"init-project.sh failed:\n{r.stdout}\n{r.stderr}"
    return d


@pytest.fixture(scope="module")
def planning_repo(tmp_path_factory) -> Path:
    """The scaffold, then the corpus a planning dispatch would write, committed."""
    repo = _scaffold(tmp_path_factory.mktemp("scaffold"), "probe-planning")
    component = repo / "development" / "common" / "alpha"
    component.mkdir(parents=True)
    (component / "roadmap.md").write_text(ROADMAP.format(note="as scaffolded"))
    (component / "phase1_only.md").write_text(PHASE)
    (repo / "development" / "sprints.md").write_text(SPRINTS)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "the corpus")
    return repo


def test_THE_SCAFFOLD_MARKS_THE_DERIVED_ARTIFACTS_NEVER_TEXT_MERGED(planning_repo: Path) -> None:
    """`.gitattributes` is written by the scaffold, not by the first person
    to hit the conflict: two lanes that both regenerated cannot three-way
    merge a whole-file JSON, and a hunk-merged artifact agrees with neither
    side's corpus."""
    attrs = (planning_repo / ".gitattributes").read_text(encoding="utf-8")
    assert "development/derived/* merge=binary" in attrs.splitlines(), attrs


def test_THE_FRESH_REPO_GENERATES_AND_ITS_CHECK_IS_GREEN(planning_repo: Path) -> None:
    """⚠ THE ONE THAT MATTERS, first half. The launcher, run by path from the
    tooling with no environment, derives five artifacts into the scaffolded
    repo; committed, the same launcher's `--check` finds nothing drifted."""
    gen = _viewer(planning_repo)
    assert gen.returncode == 0, f"generate failed:\n{gen.stdout}\n{gen.stderr}"
    derived = planning_repo / "development" / "derived"
    written = sorted(p.name for p in derived.iterdir())
    assert written == sorted([
        "consistency-report.md", "decisions.md", "plan-graph.json",
        "view-inputs.json", "view-stores.json",
    ]), written
    _git(planning_repo, "add", "-A")
    _git(planning_repo, "commit", "-qm", "the derived views")

    check = _viewer(planning_repo, "--check")
    assert check.returncode == 0, (
        f"a freshly generated and committed repo fails its own gate:\n{check.stdout}\n{check.stderr}")


def test_ONE_EDITED_ROADMAP_LINE_TURNS_THE_CHECK_RED(planning_repo: Path) -> None:
    """⚠ THE ONE THAT MATTERS, second half. A gate that cannot go red is not a
    gate. One line of one roadmap changes; `--check` exits 1 and names what
    drifted, writing nothing — the committed artifacts are untouched."""
    roadmap = planning_repo / "development" / "common" / "alpha" / "roadmap.md"
    before = {p.name: p.read_bytes() for p in (planning_repo / "development" / "derived").iterdir()}
    roadmap.write_text(ROADMAP.format(note="one line edited after generation"))

    check = _viewer(planning_repo, "--check")
    assert check.returncode == 1, (
        f"the corpus moved and the gate stayed green (exit {check.returncode}):\n"
        f"{check.stdout}\n{check.stderr}")
    assert "plan-graph.json" in check.stdout, check.stdout
    after = {p.name: p.read_bytes() for p in (planning_repo / "development" / "derived").iterdir()}
    assert after == before, "--check wrote to the artifacts; it must only compare"

    _git(planning_repo, "checkout", "--", str(roadmap))
    assert _viewer(planning_repo, "--check").returncode == 0, "positive control: reverting the edit restores green"


def test_THE_SCAFFOLDED_CI_RUNS_THE_SAME_CHECK_ON_FULL_HISTORY(planning_repo: Path) -> None:
    """The gate a developer runs is the gate CI runs — the scaffolded step
    invokes the same launcher — and CI checks out FULL history, because the
    decisions page reads `git log` for item ages and a depth-1 clone derives
    every age wrong, reporting drift that is not there."""
    wf = (planning_repo / ".github" / "workflows" / "checks.yml").read_text(encoding="utf-8")
    assert "planning-ui.sh --repo-root . --check" in wf, wf
    assert "fetch-depth: 0" in wf, "the checkout is shallow; item ages would derive wrong"
    assert "not a planning repository" in wf, (
        "a product repo's step would fail or stay silent instead of saying it asserted nothing")


def test_A_PRODUCT_REPO_FROM_THE_SAME_SCAFFOLD_IS_REFUSED_BY_NAME(tmp_path: Path) -> None:
    """The predicate is the corpus contract's, not the scaffold's: without a
    `development/sprints.md` the same scaffold is a product repo, and the
    viewer refuses it by name rather than deriving an empty graph."""
    repo = _scaffold(tmp_path, "probe-product")
    assert not (repo / "development" / "sprints.md").exists(), "positive control: no corpus"
    r = _viewer(repo, "--check")
    assert r.returncode == 2, f"expected the contract refusal (exit 2), got {r.returncode}:\n{r.stdout}\n{r.stderr}"
    assert "REFUSED" in r.stdout and "not a planning repository" in r.stdout, r.stdout

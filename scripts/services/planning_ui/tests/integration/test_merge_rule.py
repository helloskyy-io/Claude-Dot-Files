"""Two lanes that each regenerated the artifacts merge by regeneration, not by hand.

Phase 6 requirement 6. The scratch repository below is a two-component
corpus and NOTHING ELSE — the package stays where it is hosted, in the
tooling, and the scratch clone reaches it the way a real clone does: the
launcher by path, and the hook by a symlink into the tooling checkout. Two
branches each edit a different roadmap and regenerate, then merge. Three things are asserted, each against a
real ``git merge`` rather than a model of one:

* **Unregistered, the conflict is left WHOLE.** ``.gitattributes`` marks the
  artifacts ``merge=binary``, so a clone without the driver stops on a
  whole-file conflict — never a hunk-merged artifact that agrees with neither
  side's corpus.
* **Registered, the merge resolves by regeneration.** The driver keeps the
  merge from stopping on the artifacts; the hook under its ``pre-merge-commit``
  name vetoes the automatic commit when the merged tree derives differently
  from the committed artifacts — the generator's own ``--check`` is the
  predicate, so every input class it reads counts, link-target existence
  included —
  and under its ``pre-commit`` name regenerates from the merged tree — with
  ``MERGE_HEAD`` written, so the merged HISTORY is readable — and stages the
  result into the ``git commit`` that records the merge.
* **The merged artifacts equal a fresh regeneration from the merged inputs** —
  ``--check`` exits 0 on the merge commit, and the merged digest is neither
  parent's. Asserted for the inputs the decisions page reads history for too
  (a ``tracked/`` item and an Unplaced entry filed on the incoming lane): a
  regeneration that saw only ``HEAD``'s ancestry produced a page the merge
  commit then disagreed with — measured, and the reason the hook is two hooks.
* **A merge that stops on a conflict elsewhere** is finished by ``git commit``,
  which is the same ``pre-commit`` path — the artifacts are regenerated there
  rather than silently kept at OUR side by the driver.
* **Unregistered, the manual rule works mid-merge:** regenerate over the
  whole-file conflict, ``git add``, ``git commit`` — and the page is derived
  with the merged history because ``MERGE_HEAD`` exists at that point.

Every ``git`` call runs with the user's global and system config masked, so a
``core.hooksPath`` or ``commit.gpgsign`` on the developer's machine cannot make
the test pass or fail for a reason the test does not state.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from planning_ui import cli

PACKAGE = Path(__file__).resolve().parent.parent.parent
#: The service's one entry point, and the hook it registers. Both are run FROM
#: THE TOOLING, never copied: a copy would pass while the hosted shape — the
#: hook finding the launcher through its own real path, the launcher finding
#: the package through its own — silently broke.
LAUNCHER = PACKAGE.parent / "planning-ui.sh"
HOOK = PACKAGE / "githooks" / "regenerate-on-merge"
#: Taken from the module's own constants rather than typed here: an artifact
#: added without the merge rule covering it would otherwise pass this suite
#: silently — and an artifact outside the rule is one two lanes hunk-merge
#: into a page that agrees with neither side's corpus.
ARTIFACTS = cli.ARTIFACT_NAMES

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


def _env() -> dict[str, str]:
    """The user's git config masked, and NO PYTHONPATH: the launcher and the
    hook must find the package on their own, because a registered clone's
    `git merge` runs the hook with whatever environment the shell has."""
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env.update(
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_SYSTEM=os.devnull,
        GIT_AUTHOR_NAME="t",
        GIT_AUTHOR_EMAIL="t@t",
        GIT_COMMITTER_NAME="t",
        GIT_COMMITTER_EMAIL="t@t",
    )
    return env


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, env=_env(), check=check, timeout=60,
    )


def _generate(repo: Path) -> None:
    subprocess.run(
        [str(LAUNCHER)], cwd=repo, env=_env(),
        capture_output=True, text=True, check=True, timeout=120,
    )


def _check(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(LAUNCHER), "--check"], cwd=repo, env=_env(),
        capture_output=True, text=True, check=False, timeout=120,
    )


def _write_roadmap(repo: Path, component: str, note: str) -> None:
    folder = repo / "development" / "common" / component
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "roadmap.md").write_text(ROADMAP.format(name=component.title(), note=note))
    (folder / "phase1_only.md").write_text(f"# {component} phase\n")


ISSUE = """---
id: I-aaaaaaaa
title: something broke
status: open
count: 1
filed: 2026-09-01
filed_by: review-pr
repo: example-app
---

## Consequence

x

## Proposed action

y
"""

UNPLACED = """
## Sprint: Unplaced

### Whole components

- [ ] **common/beta** · ([roadmap](./common/beta/roadmap.md)) — parked
"""


def _file_history_inputs(repo: Path) -> None:
    """The two inputs the decisions page reads git HISTORY for, filed and
    committed on the current lane: a tracked item and an Unplaced entry."""
    (repo / "tracked" / "issues" / "I-aaaaaaaa.md").write_text(ISSUE)
    sprints = repo / "development" / "sprints.md"
    sprints.write_text(sprints.read_text() + UNPLACED)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "file an item and park a component")


def _history_columns(repo: Path) -> tuple[str, str]:
    """The item's age cell and the Unplaced entry's age cell, off the page."""
    page = (repo / "development" / "derived" / "decisions.md").read_text()
    item = next(line for line in page.splitlines() if line.startswith("| I-aaaaaaaa |"))
    parked = next(line for line in page.splitlines() if line.startswith("| common/beta |"))
    return item.split("|")[-3].strip(), parked.split("|")[-2].strip()


def _digest(repo: Path) -> str:
    import json

    return json.loads((repo / "development" / "derived" / "plan-graph.json").read_text())[
        "provenance"
    ]["input_digest"]


@pytest.fixture()
def scratch(tmp_path: Path) -> Path:
    """A git repository carrying this package, a two-component corpus, and two
    branches that each edited one roadmap and regenerated."""
    repo = tmp_path / "scratch"
    repo.mkdir()
    # The one line `init-project` writes into every repository it scaffolds.
    (repo / ".gitattributes").write_text("development/derived/* merge=binary\n")
    _write_roadmap(repo, "alpha", "base")
    _write_roadmap(repo, "beta", "base")
    (repo / "development" / "sprints.md").write_text(SPRINTS)
    for store in ("candidates", "issues", "operations", "standards"):
        (repo / "tracked" / store).mkdir(parents=True)
        (repo / "tracked" / store / ".keep").write_text("")

    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "corpus")
    _generate(repo)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base artifacts")

    _git(repo, "checkout", "-qb", "lane-a")
    _write_roadmap(repo, "alpha", "edited on lane A")
    _generate(repo)
    _git(repo, "commit", "-qam", "lane A regenerates")

    _git(repo, "checkout", "-q", "main")
    _git(repo, "checkout", "-qb", "lane-b")
    _write_roadmap(repo, "beta", "edited on lane B")
    _generate(repo)
    _git(repo, "commit", "-qam", "lane B regenerates")
    return repo


def _register(repo: Path) -> None:
    """The three per-clone lines the hook's header records — the symlinks
    pointing INTO THE TOOLING, which is the whole of a registration."""
    _git(repo, "config", "merge.binary.driver", "true")
    hooks = Path(_git(repo, "rev-parse", "--git-path", "hooks").stdout.strip())
    if not hooks.is_absolute():
        hooks = repo / hooks
    hooks.mkdir(parents=True, exist_ok=True)
    for name in ("pre-merge-commit", "pre-commit"):
        (hooks / name).symlink_to(HOOK)


def test_unregistered_the_merge_stops_on_a_whole_file_conflict(scratch: Path):
    """The fallback every clone has: both sides intact, no hunks picked."""
    merge = _git(scratch, "merge", "lane-a", check=False)
    assert merge.returncode != 0, merge.stdout + merge.stderr

    status = _git(scratch, "status", "--porcelain").stdout
    conflicted = {line[3:] for line in status.splitlines() if line.startswith("UU ")}
    assert conflicted == {f"development/derived/{name}" for name in ARTIFACTS}, status

    # Whole, not hunk-merged: the working copy is OUR side's bytes exactly, and
    # carries no conflict marker.
    for name in ARTIFACTS:
        rel = f"development/derived/{name}"
        ours = _git(scratch, "show", f"HEAD:{rel}").stdout
        assert (scratch / rel).read_text() == ours, rel
        assert "<<<<<<<" not in ours


def _lane_digest(repo: Path, ref: str) -> str:
    import json

    return json.loads(_git(repo, "show", f"{ref}:development/derived/plan-graph.json").stdout)[
        "provenance"
    ]["input_digest"]


def test_registered_the_merge_resolves_by_regeneration(scratch: Path):
    """The driver lets the merge through the artifacts; the merge hook vetoes
    the automatic commit; the commit hook regenerates into `git commit`, whose
    artifacts equal a fresh run."""
    _register(scratch)
    before_b = _digest(scratch)

    merge = _git(scratch, "merge", "lane-a", check=False)
    # The merge hook vetoed the AUTOMATIC commit and said why.
    assert merge.returncode != 0
    assert "Run `git commit`" in merge.stderr, merge.stderr
    status = _git(scratch, "status", "--porcelain").stdout
    assert "UU " not in status, status
    assert (scratch / ".git" / "MERGE_HEAD").exists(), "the merge is still in progress"

    commit = _git(scratch, "commit", "-qm", "merge lane A")
    assert "regenerated development/derived/ from the merged tree" in commit.stderr, commit.stderr

    # Requirement 6's second half: the merge commit's artifacts ARE a fresh
    # regeneration from the merged inputs. `--check` is that comparison.
    check = _check(scratch)
    assert check.returncode == 0, check.stdout
    merged = _digest(scratch)
    assert merged != before_b
    assert merged != _lane_digest(scratch, "lane-a")
    # And both lanes' edits are in the merged corpus the page was derived from.
    roadmap_a = (scratch / "development" / "common" / "alpha" / "roadmap.md").read_text()
    roadmap_b = (scratch / "development" / "common" / "beta" / "roadmap.md").read_text()
    assert "edited on lane A" in roadmap_a and "edited on lane B" in roadmap_b


def test_registered_a_merge_that_touches_no_input_commits_untouched(scratch: Path):
    """The hook's short-circuit: a merge whose merged tree derives the SAME
    artifacts leaves them alone and the automatic merge commit proceeds.

    ``NOTES.txt`` is not an input because nothing links it or its directory —
    not because it is not markdown. A file's suffix says nothing about whether
    the derivation reads it: the derivation also reads whether a link's TARGET
    exists, so a non-markdown file can be an input whenever a roadmap links
    the directory it is the last member of (the next test)."""
    _register(scratch)
    _git(scratch, "checkout", "-qb", "lane-c", "main")
    (scratch / "NOTES.txt").write_text("not markdown, not an input\n")
    _git(scratch, "add", "NOTES.txt")
    _git(scratch, "commit", "-qm", "a note")
    _git(scratch, "checkout", "-q", "lane-b")

    merge = _git(scratch, "merge", "lane-c", check=False)
    assert merge.returncode == 0, merge.stdout + merge.stderr
    assert not (scratch / ".git" / "MERGE_HEAD").exists()


def test_registered_a_merge_that_deletes_a_linked_directorys_last_file_regenerates(
    scratch: Path,
):
    """A lane that deletes the only file of a directory a roadmap links —
    not markdown, so a predicate keyed on file suffix calls it "not an
    input". It is one: the derivation reads whether the link's target EXISTS
    (`measurements._scan_links` → `safe_paths.exists_in_root`), and git drops the now-empty
    directory with its last file, so the link resolves to nothing in the
    merged tree. The merge commit must carry a page that says so — the hook
    asks the generator (`--check`) rather than guessing from paths."""
    _register(scratch)
    _git(scratch, "checkout", "-q", "main")
    evidence = scratch / "development" / "common" / "alpha" / "evidence"
    evidence.mkdir()
    (evidence / "run.log").write_text("measured\n")
    roadmap = scratch / "development" / "common" / "alpha" / "roadmap.md"
    roadmap.write_text(roadmap.read_text() + "\nSee [the evidence](evidence/).\n")
    _git(scratch, "add", "-A")
    _git(scratch, "commit", "-qm", "link a directory whose only file is not markdown")
    _generate(scratch)
    _git(scratch, "commit", "-qam", "regenerate")
    assert _check(scratch).returncode == 0

    _git(scratch, "checkout", "-qb", "lane-d")
    _git(scratch, "rm", "-q", "development/common/alpha/evidence/run.log")
    _git(scratch, "commit", "-qm", "delete the evidence — no markdown touched")
    _git(scratch, "checkout", "-q", "main")
    # main moves too, on something nothing links, so the merge is a real merge
    # (a fast-forward runs no hook) and the only input-relevant change it
    # carries is the deletion.
    (scratch / "NOTES.txt").write_text("not linked by anything\n")
    _git(scratch, "add", "NOTES.txt")
    _git(scratch, "commit", "-qm", "a note on main")

    merge = _git(scratch, "merge", "lane-d", check=False)
    assert merge.returncode != 0 and "Run `git commit`" in merge.stderr, (
        merge.stdout + merge.stderr
    )
    commit = _git(scratch, "commit", "-qm", "merge lane D")
    assert "regenerated development/derived/ from the merged tree" in commit.stderr, commit.stderr

    check = _check(scratch)
    assert check.returncode == 0, check.stdout
    assert not evidence.exists()


def test_registered_the_merge_commit_carries_the_incoming_lanes_history(scratch: Path):
    """The inputs the decisions page reads HISTORY for, filed on the incoming
    lane. The page the merge commit carries must give the item the age the
    merge commit's own log gives it — which a regeneration made before
    MERGE_HEAD was written could not (it saw HEAD's ancestry alone, rendered
    the item ageless, and `--check` on the merge commit reported the page
    STALE)."""
    _register(scratch)
    _file_history_inputs(scratch)  # on lane-b, which is checked out
    _generate(scratch)
    _git(scratch, "commit", "-qam", "lane B regenerates after filing")
    _git(scratch, "checkout", "-q", "lane-a")

    merge = _git(scratch, "merge", "lane-b", check=False)
    assert merge.returncode != 0 and "Run `git commit`" in merge.stderr, merge.stderr
    _git(scratch, "commit", "-qm", "merge lane B")

    check = _check(scratch)
    assert check.returncode == 0, check.stdout
    age, parked = _history_columns(scratch)
    assert age.startswith("0d (last activity "), age
    assert parked.startswith("0d (set "), parked


def test_registered_a_merge_that_stopped_on_a_conflict_elsewhere_regenerates_at_commit(
    scratch: Path,
):
    """`pre-merge-commit` never runs for a merge that stopped on a conflict; the
    operator resolves and runs `git commit`, and THAT is where the artifacts
    are regenerated — not silently kept at our side by the driver."""
    _register(scratch)
    _git(scratch, "checkout", "-qb", "lane-c", "main")
    _write_roadmap(scratch, "beta", "edited on lane C, conflicting")
    _generate(scratch)
    _git(scratch, "commit", "-qam", "lane C regenerates")
    _git(scratch, "checkout", "-q", "lane-b")

    merge = _git(scratch, "merge", "lane-c", check=False)
    assert merge.returncode != 0
    status = _git(scratch, "status", "--porcelain").stdout
    conflicted = {line[3:] for line in status.splitlines() if line.startswith("UU ")}
    assert conflicted == {"development/common/beta/roadmap.md"}, status

    _write_roadmap(scratch, "beta", "resolved by hand")
    _git(scratch, "add", "development/common/beta/roadmap.md")
    commit = _git(scratch, "commit", "-qm", "merge lane C, resolved")
    assert "regenerated development/derived/ from the merged tree" in commit.stderr, commit.stderr

    check = _check(scratch)
    assert check.returncode == 0, check.stdout
    assert _digest(scratch) not in {_lane_digest(scratch, "lane-c"), _lane_digest(scratch, "lane-b~1")}


def test_unregistered_regenerating_over_the_conflict_reads_the_merged_history(scratch: Path):
    """The manual rule, on a clone with nothing registered: regenerate over the
    whole-file conflict, add, commit. MERGE_HEAD exists at that point, so the
    page is derived with the incoming lane's history and `--check` agrees with
    the merge commit."""
    _file_history_inputs(scratch)  # on lane-b
    _generate(scratch)
    _git(scratch, "commit", "-qam", "lane B regenerates after filing")
    _git(scratch, "checkout", "-q", "lane-a")

    merge = _git(scratch, "merge", "lane-b", check=False)
    assert merge.returncode != 0
    status = _git(scratch, "status", "--porcelain").stdout
    assert all(f"UU development/derived/{name}" in status for name in ARTIFACTS), status

    _generate(scratch)
    _git(scratch, "add", "development/derived")
    _git(scratch, "commit", "-qm", "merge lane B, regenerated by hand")

    check = _check(scratch)
    assert check.returncode == 0, check.stdout
    age, parked = _history_columns(scratch)
    assert age.startswith("0d (last activity "), age
    assert parked.startswith("0d (set "), parked

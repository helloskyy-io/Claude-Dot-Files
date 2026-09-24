"""The history derivation — how long a thing has sat, across how many passes.

Driven against a REAL git repository built in ``tmp_path``, not a mocked
subprocess. The whole point of these functions is what ``git log --name-status``
and ``git blame --line-porcelain`` actually emit, and a mock would assert the
shape this module already assumes.

**The distinction under test is filing versus triage.** A commit that only ADDS
items is not a triage pass, and counting it as one inflates every item's score in
a store being harvested into — which is the state `tracked/candidates/` was in
when this was written, after 34 intake issues landed in it on one day.
"""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

import pytest

from planning_ui.decisions.history import read_history

STORES = ("candidates", "issues", "operations", "standards")
SPRINTS = "development/sprints.md"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _commit(root: Path, message: str, when: str) -> None:
    env = {
        "GIT_AUTHOR_DATE": when,
        "GIT_COMMITTER_DATE": when,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(root),
    }
    subprocess.run(
        ["git", "-C", str(root), "commit", "-m", message],
        check=True,
        capture_output=True,
        env=env,
    )


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A checkout with three commits: file two items, rule on one, rule again."""
    root = tmp_path / "corpus"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")

    # Commit 1 — FILING. Two candidates added; nothing is ruled on.
    _write(root, "tracked/candidates/C-aaaaaaaa.md", "---\nid: C-aaaaaaaa\ndecision:\n---\na\n")
    _write(root, "tracked/candidates/C-bbbbbbbb.md", "---\nid: C-bbbbbbbb\ndecision:\n---\nb\n")
    _write(root, SPRINTS, "# Plan\n\n## Sprint: Unplaced\n\n- [ ] one\n")
    _git(root, "add", "-A")
    _commit(root, "file two candidates", "2026-01-01T00:00:00+00:00")

    # Commit 2 — TRIAGE. One candidate modified; the other is passed over.
    _write(root, "tracked/candidates/C-aaaaaaaa.md", "---\nid: C-aaaaaaaa\ndecision: ship\n---\na\n")
    _git(root, "add", "-A")
    _commit(root, "rule on C-aaaaaaaa", "2026-01-10T00:00:00+00:00")

    # Commit 3 — TRIAGE again, and another FILING in the same commit.
    _write(root, "tracked/candidates/C-aaaaaaaa.md", "---\nid: C-aaaaaaaa\ndecision: ship\nsize: M\n---\na\n")
    _write(root, "tracked/candidates/C-cccccccc.md", "---\nid: C-cccccccc\ndecision:\n---\nc\n")
    _git(root, "add", "-A")
    _commit(root, "size C-aaaaaaaa and file C-cccccccc", "2026-01-20T00:00:00+00:00")

    # Commit 4 — FILING ONLY. Must NOT count as a pass for anything.
    _write(root, "tracked/candidates/C-dddddddd.md", "---\nid: C-dddddddd\ndecision:\n---\nd\n")
    _git(root, "add", "-A")
    _commit(root, "harvest one more candidate", "2026-01-30T00:00:00+00:00")
    return root


def test_last_activity_is_the_newest_commit_touching_the_item(repo: Path):
    history = read_history(repo, STORES, SPRINTS)
    assert history.available
    assert history.item_activity["tracked/candidates/C-aaaaaaaa.md"].day == "2026-01-20"
    assert history.item_activity["tracked/candidates/C-bbbbbbbb.md"].day == "2026-01-01"
    assert history.item_activity["tracked/candidates/C-dddddddd.md"].day == "2026-01-30"


def test_days_since_counts_back_to_the_reference_date(repo: Path):
    history = read_history(repo, STORES, SPRINTS)
    assert history.item_age_days("tracked/candidates/C-bbbbbbbb.md", date(2026, 1, 31)) == 30
    assert history.item_age_days("tracked/candidates/C-aaaaaaaa.md", date(2026, 1, 31)) == 11


def test_a_filing_only_commit_is_not_a_triage_pass(repo: Path):
    """The property the §0 exit test rests on.

    `C-bbbbbbbb` was filed in commit 1 and passed over by the two commits that
    modified a sibling — that is two passes. Commit 4 added a file and ruled on
    nothing, so it is filing, and counting it would make an untouched store look
    like a triaged one.
    """
    history = read_history(repo, STORES, SPRINTS)
    assert history.passes_since_activity("candidates", "tracked/candidates/C-bbbbbbbb.md") == 2


def test_an_item_does_not_count_the_pass_that_ruled_on_it(repo: Path):
    """`C-aaaaaaaa` was last modified by the newest triage commit, so it has survived none."""
    history = read_history(repo, STORES, SPRINTS)
    assert history.passes_since_activity("candidates", "tracked/candidates/C-aaaaaaaa.md") == 0


def test_an_item_filed_by_a_triage_commit_starts_at_zero(repo: Path):
    """`C-cccccccc` arrived in a commit that also ruled on a sibling.

    The commit touched it, so it is excluded from its own count — filing and
    triage happening in one commit must not credit the new item with a pass.
    """
    history = read_history(repo, STORES, SPRINTS)
    assert history.passes_since_activity("candidates", "tracked/candidates/C-cccccccc.md") == 0


def test_a_deletion_counts_as_a_pass(tmp_path: Path):
    """§4.2 pruning follows a ruling, so a delete is evidence of triage."""
    root = tmp_path / "corpus"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    _write(root, "tracked/issues/I-aaaaaaaa.md", "---\nid: I-aaaaaaaa\n---\na\n")
    _write(root, "tracked/issues/I-bbbbbbbb.md", "---\nid: I-bbbbbbbb\n---\nb\n")
    _git(root, "add", "-A")
    _commit(root, "file two", "2026-02-01T00:00:00+00:00")
    (root / "tracked/issues/I-bbbbbbbb.md").unlink()
    _git(root, "add", "-A")
    _commit(root, "prune I-bbbbbbbb", "2026-02-20T00:00:00+00:00")

    history = read_history(root, STORES, SPRINTS)
    assert history.passes_since_activity("issues", "tracked/issues/I-aaaaaaaa.md") == 1


def test_a_rename_is_not_a_triage_pass(tmp_path: Path):
    """A reorganising commit rules on nothing, and must credit nobody.

    Under `--no-renames` git spells a rename as a DELETE of the old path plus an
    ADD of the new one, and the delete half satisfies the modified-or-deleted
    rule — so ONE `git mv` inside a store credited EVERY OTHER item in it with a
    pass it never received, inflating the §0 exit test, which is this page's
    headline derivation. This PR's own fixture move is the live demonstration
    that renames happen here.
    """
    root = tmp_path / "corpus"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    _write(root, "tracked/candidates/C-aaaaaaaa.md", "---\nid: C-aaaaaaaa\n---\n" + "a\n" * 40)
    _write(root, "tracked/candidates/C-bbbbbbbb.md", "---\nid: C-bbbbbbbb\n---\n" + "b\n" * 40)
    _git(root, "add", "-A")
    _commit(root, "file two", "2026-04-01T00:00:00+00:00")

    _git(root, "mv", "tracked/candidates/C-bbbbbbbb.md", "tracked/candidates/C-cccccccc.md")
    _commit(root, "renumber C-bbbbbbbb", "2026-04-10T00:00:00+00:00")

    history = read_history(root, STORES, SPRINTS)
    assert history.passes_since_activity("candidates", "tracked/candidates/C-aaaaaaaa.md") == 0


def test_a_path_needing_quoting_still_reaches_history(tmp_path: Path):
    """Git C-quotes an awkward path unless told not to.

    A quoted path fails every `tracked/<store>/<id>.md` shape test, so the item
    silently drops out of history and renders as though nothing were known about
    it — indistinguishable, in that one row, from history being unavailable.
    """
    root = tmp_path / "corpus"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    awkward = "tracked/issues/I-café0000.md"
    _write(root, awkward, "---\nid: I-café0000\n---\na\n")
    _git(root, "add", "-A")
    _commit(root, "file an awkwardly-named item", "2026-05-01T00:00:00+00:00")

    history = read_history(root, STORES, SPRINTS)
    assert awkward in history.item_activity


def test_an_uncommitted_sprints_line_is_not_dated_to_now(tmp_path: Path):
    """Blame reports the all-zero sha for a working-tree line.

    Recording it would date the entry to *now* and render an uncommitted local
    edit as a freshly-touched entry — the same "reads as freshly triaged"
    failure this module refuses for the whole-history-unavailable case.
    """
    root = tmp_path / "corpus"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    _write(root, SPRINTS, "# Plan\n\n## Sprint: Unplaced\n\n- [ ] committed\n")
    _write(root, "tracked/issues/I-aaaaaaaa.md", "---\nid: I-aaaaaaaa\n---\na\n")
    _git(root, "add", "-A")
    _commit(root, "commit sprints", "2026-06-01T00:00:00+00:00")

    _write(root, SPRINTS, "# Plan\n\n## Sprint: Unplaced\n\n- [ ] committed\n- [ ] uncommitted\n")

    history = read_history(root, STORES, SPRINTS)
    assert history.blame_available
    assert 5 in history.sprint_line_activity, "the committed line keeps its real date"
    assert 6 not in history.sprint_line_activity, "the uncommitted line is not dated at all"


def test_blame_failure_is_recorded_separately_from_log_failure(tmp_path: Path):
    """`sprints.md` absent while `tracked/` has history is the asymmetric case.

    Table 5's age column would be entirely dashed while every other table's is
    populated — which reads as "nobody has touched § Sprint: Unplaced recently",
    the opposite of "we could not find out".
    """
    root = tmp_path / "corpus"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    _write(root, "tracked/issues/I-aaaaaaaa.md", "---\nid: I-aaaaaaaa\n---\na\n")
    _git(root, "add", "-A")
    _commit(root, "file one, no sprints.md", "2026-07-01T00:00:00+00:00")

    history = read_history(root, STORES, SPRINTS)
    assert history.available is True
    assert history.blame_available is False


def test_passes_are_scoped_to_the_items_own_store(tmp_path: Path):
    """Triaging `standards/` is not a pass over `issues/`.

    §4 gives each store its own cadence and its own runner. A shared counter
    would report an item as stuck because a *different* store was being worked.
    """
    root = tmp_path / "corpus"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    _write(root, "tracked/issues/I-aaaaaaaa.md", "---\nid: I-aaaaaaaa\n---\na\n")
    _write(root, "tracked/standards/S-aaaaaaaa.md", "---\nid: S-aaaaaaaa\n---\ns\n")
    _git(root, "add", "-A")
    _commit(root, "file one of each", "2026-03-01T00:00:00+00:00")
    _write(root, "tracked/standards/S-aaaaaaaa.md", "---\nid: S-aaaaaaaa\nratification: ratified\n---\ns\n")
    _git(root, "add", "-A")
    _commit(root, "ratify", "2026-03-10T00:00:00+00:00")

    history = read_history(root, STORES, SPRINTS)
    assert history.passes_since_activity("issues", "tracked/issues/I-aaaaaaaa.md") == 0


def test_sprint_line_ages_come_from_blame_per_line(repo: Path):
    """Table 5's age column is per ENTRY, not per file.

    A file-level mtime would make every § Sprint: Unplaced entry the same age as
    the most recent edit anywhere in `sprints.md` — which is exactly the signal
    the section was built to expose, erased.
    """
    history = read_history(repo, STORES, SPRINTS)
    assert history.sprint_line_activity
    assert history.sprint_line_activity[5].day == "2026-01-01"


def test_a_checkout_with_no_history_reports_unavailable_rather_than_zero(tmp_path: Path):
    """A zero here would read as "freshly triaged" — the opposite of the truth."""
    root = tmp_path / "plain"
    (root / "tracked" / "issues").mkdir(parents=True)
    history = read_history(root, STORES, SPRINTS)
    assert history.available is False
    assert history.passes_since_activity("issues", "tracked/issues/I-aaaaaaaa.md") is None
    assert history.item_age_days("tracked/issues/I-aaaaaaaa.md", date(2026, 1, 1)) is None


def test_an_item_added_but_not_yet_committed_is_dated_from_its_filed_field(repo: Path):
    """I-x7pv3ke2: the hook regenerates from the tree being committed.

    POSITIVE CONTROL: the committed item must still take its date from GIT,
    not from `filed:`. Without that, a fallback that ran unconditionally would
    pass this test while silently overriding every real commit date.
    """
    from planning_ui.decisions.history import read_history
    from planning_ui.plan_extractor.tracked import TrackedItem

    committed = "tracked/issues/I-committed.md"
    (repo / committed).parent.mkdir(parents=True, exist_ok=True)
    (repo / committed).write_text(
        "---\nid: I-committed\nstatus: open\ncount: 1\nfiled: 2020-01-01\n---\n\nbody\n"
    )
    _git(repo, "add", committed)
    _git(repo, "commit", "-m", "file the committed one")

    staged = "tracked/issues/I-staged.md"
    (repo / staged).write_text(
        "---\nid: I-staged\nstatus: open\ncount: 1\nfiled: 2026-09-24\n---\n\nbody\n"
    )

    history = read_history(repo, ("issues",), "development/sprints.md")
    assert staged not in history.item_activity, "precondition: git cannot see it yet"
    before = history.item_activity[committed]

    history.seed_uncommitted([
        TrackedItem(store="issues", path=committed, fields={"filed": "2020-01-01"}),
        TrackedItem(store="issues", path=staged, fields={"filed": "2026-09-24"}),
    ])

    assert history.item_activity[staged].day == "2026-09-24"
    assert history.item_activity[committed] == before, (
        "the committed item's real commit date was overwritten by its frontmatter"
    )


def test_an_unparseable_filed_field_leaves_the_age_absent(repo: Path):
    """An unknowable age renders as absent, never as today."""
    from planning_ui.decisions.history import read_history
    from planning_ui.plan_extractor.tracked import TrackedItem

    history = read_history(repo, ("issues",), "development/sprints.md")
    for bad in ("", "soon", "2026-13-99"):
        history.seed_uncommitted(
            [TrackedItem(store="issues", path="tracked/issues/I-bad.md",
                         fields={"filed": bad})]
        )
        assert "tracked/issues/I-bad.md" not in history.item_activity, bad

"""The file layer of the never-silently-drop rule.

The phase doc calls the file layer *the more dangerous of the two* — "a dropped
line is one finding, a dropped file is a whole component or phase absent from
the graph with nothing to indicate it." Before ``corpus_io`` existed, nine read
sites carried three different policies for a file that cannot be read, two of
which were the silent drop. These tests assert the one policy that replaced
them, at the layer that now owns it.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from planning_ui.plan_extractor import corpus_io
from planning_ui.plan_extractor.model import (
    FILE_UNREADABLE,
    PATH_ESCAPES_ROOT,
    Collector,
)


def test_an_unreadable_file_is_a_named_finding_and_not_an_empty_string(tmp_path: Path):
    """The silent-drop shape wearing a different type is still the silent drop.

    ``read_text`` returns ``None`` rather than ``""`` precisely so a caller
    cannot carry on against an empty file believing it read one.
    """
    victim = tmp_path / "unreadable.md"
    victim.write_text("# real content\n")
    victim.chmod(0o000)
    if os.access(victim, os.R_OK):  # running as root — the chmod means nothing
        pytest.skip("cannot make a file unreadable as this user")

    collector = Collector()
    try:
        result = corpus_io.read_text(tmp_path, "unreadable.md", collector)
    finally:
        victim.chmod(0o644)

    assert result is None
    codes = [f.code for f in collector.findings]
    assert codes == [FILE_UNREADABLE]
    assert collector.findings[0].provenance.file == "unreadable.md"
    assert collector.findings[0].expected


def test_a_missing_file_is_reported_rather_than_silently_skipped(tmp_path: Path):
    collector = Collector()
    assert corpus_io.read_text(tmp_path, "never-existed.md", collector) is None
    assert [f.code for f in collector.findings] == [FILE_UNREADABLE]


def test_read_lines_returns_none_rather_than_an_empty_list(tmp_path: Path):
    """An empty list is falsy and would read as "a file with no lines"."""
    collector = Collector()
    assert corpus_io.read_lines(tmp_path, "absent.md", collector) is None


def test_a_symlink_leaving_the_root_is_reported_and_never_opened(tmp_path: Path):
    """The escape guard applied to the ENUMERATED SOURCE, not only to link text.

    ``safe_paths`` reports an escape for a path *authored in the corpus* and
    never opens it. A symlink physically under the corpus whose target is
    outside walked straight past that guard, and the file it pointed at was then
    read — the same invariant failing at the other end of the pipe.
    """
    root = tmp_path / "corpus"
    (root / "development").mkdir(parents=True)
    outside = tmp_path / "outside" / "secret.md"
    outside.parent.mkdir()
    outside.write_text("content from outside the checkout\n")
    (root / "development" / "escaped.md").symlink_to(outside)
    (root / "development" / "honest.md").write_text("# fine\n")

    collector = Collector()
    found = corpus_io.iter_markdown(root, "development", collector=collector)

    assert found == ["development/honest.md"], "the escaping symlink must not be returned"
    escapes = [f for f in collector.findings if f.code == PATH_ESCAPES_ROOT]
    assert len(escapes) == 1
    assert escapes[0].provenance.file == "development/escaped.md"
    assert "never opened" in escapes[0].detail


def test_a_symlink_that_stays_inside_the_root_is_admitted(tmp_path: Path):
    """The negative half: the guard must discriminate, not blanket-reject links."""
    root = tmp_path / "corpus"
    (root / "development").mkdir(parents=True)
    (root / "development" / "real.md").write_text("# fine\n")
    (root / "development" / "alias.md").symlink_to(root / "development" / "real.md")

    collector = Collector()
    found = corpus_io.iter_markdown(root, "development", collector=collector)

    assert found == ["development/alias.md", "development/real.md"]
    assert collector.findings == []


def test_one_defect_met_by_three_overlapping_walks_is_one_row(tmp_path: Path):
    """Discovery, the census and the link sweep all walk overlapping trees.

    A reader who sees the same path three times in one section learns to skim
    the section, which is how a report stops being a worklist.
    """
    root = tmp_path / "corpus"
    (root / "development").mkdir(parents=True)
    outside = tmp_path / "outside" / "secret.md"
    outside.parent.mkdir()
    outside.write_text("x\n")
    (root / "development" / "escaped.md").symlink_to(outside)

    collector = Collector()
    corpus_io.iter_markdown(root, "development", collector=collector)
    corpus_io.iter_markdown(root, collector=collector)
    corpus_io.iter_markdown(root, collector=collector)

    assert [f.code for f in collector.findings] == [PATH_ESCAPES_ROOT]


def test_exclude_prefixes_is_a_stated_parameter_not_a_hardcoded_filter(tmp_path: Path):
    """The broken-link sweep's ``backup/``/``assets/`` exclusion is the caller's.

    A walk that hardcodes one caller's exclusions silently applies them to every
    other caller — the glob-as-silent-filter defect one layer up.
    """
    root = tmp_path
    for name in ("keep.md", "backup/dropped.md", "assets/dropped.md"):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x\n")

    collector = Collector()
    assert corpus_io.iter_markdown(root, collector=collector) == [
        "assets/dropped.md",
        "backup/dropped.md",
        "keep.md",
    ]
    assert corpus_io.iter_markdown(
        root, collector=collector, exclude_prefixes=("backup/", "assets/")
    ) == ["keep.md"]


def test_the_escape_guard_is_on_the_read_and_not_only_on_the_walk(tmp_path: Path):
    """A path that never went through the walk is still guarded.

    The guard used to live only in ``iter_markdown``, so the invariant held for
    callers that happened to enumerate through this module and silently did not
    for the ones that reached ``read_text`` with a path from anywhere else — a
    tracked store's own glob, a corpus-authored ``target:``. A guard with a
    caller list is not a guard.
    """
    root = tmp_path / "corpus"
    root.mkdir()
    outside = tmp_path / "outside" / "secret.md"
    outside.parent.mkdir()
    outside.write_text("SENSITIVE\n")
    (root / "escaped.md").symlink_to(outside)

    collector = Collector()
    assert corpus_io.read_text(root, "escaped.md", collector) is None
    assert [f.code for f in collector.findings] == [PATH_ESCAPES_ROOT]


def test_an_inside_the_root_symlink_is_still_admitted(tmp_path: Path):
    """The negative half: the guard is on ESCAPING, not on being a symlink."""
    root = tmp_path / "corpus"
    (root / "real").mkdir(parents=True)
    (root / "real" / "doc.md").write_text("# inside\n")
    (root / "link.md").symlink_to(root / "real" / "doc.md")

    collector = Collector()
    assert corpus_io.read_text(root, "link.md", collector) == "# inside\n"
    assert collector.findings == []


def test_the_generators_own_output_is_never_walked(tmp_path: Path):
    """A fixed-point guard, not an input exclusion.

    The committed pages render amendment-shaped tables and enumerate link
    targets. A walk that read them derived pages that differed from the ones it
    read — measured the first time they were committed, as a §8 second-surface
    finding against the decisions page — and `--check` could never agree with
    `generate`. Positive control beside it: a sibling directory IS walked.
    """
    root = tmp_path / "corpus"
    (root / "development" / "derived").mkdir(parents=True)
    (root / "development" / "derived" / "decisions.md").write_text("# page\n")
    # Positive control: a SIBLING of the derived folder, under the same walked
    # parent. The exclusion must be that one path and not `development/`.
    (root / "development" / "common").mkdir(parents=True)
    (root / "development" / "common" / "note.md").write_text("# note\n")
    (root / "development" / "sprints.md").write_text("# s\n")

    walked = corpus_io.iter_markdown(root, collector=Collector())
    assert "development/derived/decisions.md" not in walked
    assert "development/common/note.md" in walked
    assert "development/sprints.md" in walked

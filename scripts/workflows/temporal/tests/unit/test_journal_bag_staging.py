"""A crash inside `open_bag` leaves a staging directory that NO reader counts as a run.

`open_bag` writes `bagit.txt` and `bag-info.txt` into a hidden staging directory
before renaming it onto `<root>/<run_id>`, so a hard kill between the two leaves
a directory that looks like a bag. Its name is what keeps it out of every run
count: `STAGING_MARK` is outside `RUN_ID_PERMITTED`, and `journal_bags` admits
only names `validated_run_id` accepts. Each reader of the journal root is
asserted here, because a reader that re-derives "which directories are bags"
is how the phantom run would come back.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from modules.assistant.tracked import rebuild as rb
from modules.journal import bag as bag_mod
from modules.journal.bag import (BAG_INFO_FILE, BAGIT_FILE, BagError, RUN_ID_PERMITTED,
                                 STAGING_MARK, journal_bags, open_bag, staging_prefix,
                                 validated_run_id)

_COMPLETENESS = Path(__file__).resolve().parents[2] / "scripts" / "journal_completeness.py"


def _crash_inside_open_bag(root: Path, run_id: str, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Imitate a hard kill between the staging writes and the rename: the rename
    raises and the best-effort cleanup is a no-op. Returns the left directory."""
    def _killed(*_a, **_k):
        raise RuntimeError("process killed before the rename")

    with monkeypatch.context() as m:
        m.setattr(bag_mod.os, "rename", _killed)
        m.setattr(bag_mod.shutil, "rmtree", lambda *_a, **_k: None)
        with pytest.raises(RuntimeError):
            open_bag(root, run_id)
    left = [p for p in root.iterdir() if p.is_dir()]
    assert len(left) == 1, f"the imitated crash left {left}, not one staging directory"
    return left[0]


def test_STAGING_MARK_is_outside_the_permitted_run_id_set() -> None:
    assert STAGING_MARK not in RUN_ID_PERMITTED, (
        "journal_bags excludes a crash-left staging directory ONLY because "
        "validated_run_id refuses STAGING_MARK; admitting it to RUN_ID_PERMITTED "
        "makes every crash-left staging directory a phantom run")
    with pytest.raises(BagError):
        validated_run_id(staging_prefix("run-abc") + "x1y2z3")


def test_a_crash_left_staging_directory_is_enumerated_by_NO_reader(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "journal"
    root.mkdir()
    staged = _crash_inside_open_bag(root, "run-abc", monkeypatch)

    # The real shape: hidden, named from the run id, and already bag-looking.
    assert staged.name.startswith(staging_prefix("run-abc"))
    assert (staged / BAGIT_FILE).is_file() and (staged / BAG_INFO_FILE).is_file()

    assert journal_bags(root) == []
    assert rb.read_bags(root) == []

    spec = importlib.util.spec_from_file_location("journal_completeness", _COMPLETENESS)
    completeness = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(completeness)
    assert completeness._bags(root) == []


def test_the_run_opened_after_a_crash_is_the_only_run_counted(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "journal"
    root.mkdir()
    _crash_inside_open_bag(root, "run-abc", monkeypatch)
    opened = open_bag(root, "run-abc")
    assert journal_bags(root) == [opened.path]
    assert [b.path for b in rb.read_bags(root)] == [opened.path]
    # The staging directory is still on disk: it is excluded, not reclaimed.
    assert len([p for p in root.iterdir() if p.name.startswith(".")]) == 1

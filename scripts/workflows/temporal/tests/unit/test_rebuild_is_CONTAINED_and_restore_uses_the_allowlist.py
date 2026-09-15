"""PMP Phase 4 requirements 4 (containment) and 8 (restore).

The containment contract binds EVERY replay target after full normalisation —
absolute rejected, `..` rejected, a symlink at any component rejected, a
symlinked root refused — and it binds the restore's live destination exactly as
it binds the test's scratch root, because the working tree is where a
`destination` of `config/hooks/` would be a file that gets executed.

TWO LAYERS, TESTED SEPARATELY. `contained_target` is fed hostile values
directly, because a contract enforced only by "callers never pass those" is
prose. Then the same escapes are fed THROUGH an event — as the item id in its
frontmatter — to show the id shape refuses them before the path is even
composed, and that the event's own `destination.address` is never consulted.

RESTORE: dry-run by default and writes nothing; `--apply` creates and
overwrites through the allowlist; files the journal does not know are left in
place; `tracked/operations/` cannot be named; a gapped store is refused.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest

from modules.assistant.tracked import rebuild as rb
from modules.assistant.tracked import tracked_items as ti
from modules.journal.bag import open_bag
from modules.journal.emit import Emitter, emitting_into
from modules.journal.events import Destination, GapClass
from rebuild_fixture import RUN_PREFIX, build


@pytest.fixture
def fixture(tmp_path: Path) -> tuple[Path, Path]:
    return build(tmp_path / "fixture")


@pytest.fixture
def replay_root(tmp_path: Path) -> Path:
    root = tmp_path / "scratch"
    root.mkdir()
    return root


# --- contained_target, fed directly ------------------------------------------------

ESCAPES = [
    "/etc/passwd.md",
    "../C-fixt0001.md",
    "candidates/../../C-fixt0001.md",
    "C-fixt0001.md/../../x.md",
    "C-fixt0001",                 # no .md
    "C-fixt00011.md",             # nine chars
    "C-FIXT0001.md",              # uppercase in the base36 part
    "C-fixt0001.md\n",            # trailing newline
    "..",
    ".",
    "",
]


@pytest.mark.parametrize("filename", ESCAPES, ids=repr)
def test_every_escape_in_the_battery_is_REFUSED(replay_root: Path, filename: str) -> None:
    with pytest.raises(rb.ContainmentError):
        rb.contained_target(replay_root, "candidates", filename)
    assert not any(replay_root.rglob("*")), "a refusal wrote something"


def test_an_ABSOLUTE_filename_is_refused_and_the_root_is_NOT_discarded(
        replay_root: Path) -> None:
    """`Path("/root") / "/etc/x"` DISCARDS the base — the worst shape of this
    class. The refusal must happen before any join could."""
    with pytest.raises(rb.ContainmentError, match="not `<store-prefix>"):
        rb.contained_target(replay_root, "candidates", "/etc/x.md")


def test_a_store_outside_the_enumeration_is_refused(replay_root: Path) -> None:
    with pytest.raises(rb.ContainmentError, match="not a store this module enumerates"):
        rb.contained_target(replay_root, "hooks", "C-fixt0001.md")


def test_a_prefix_from_ANOTHER_store_is_refused(replay_root: Path) -> None:
    with pytest.raises(rb.ContainmentError, match="carries prefix O-"):
        rb.contained_target(replay_root, "candidates", "O-fixt0001.md")


def test_a_SYMLINKED_ROOT_is_refused(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    with pytest.raises(rb.ContainmentError, match="is a symlink"):
        rb.contained_target(link, "candidates", "C-fixt0001.md")


def test_a_symlinked_STORE_DIRECTORY_is_refused(replay_root: Path, tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (replay_root / "candidates").symlink_to(elsewhere)
    with pytest.raises(rb.ContainmentError, match="is a symlink"):
        rb.contained_target(replay_root, "candidates", "C-fixt0001.md")
    assert not (elsewhere / "C-fixt0001.md").exists()


def test_a_symlinked_TARGET_FILE_is_refused(replay_root: Path, tmp_path: Path) -> None:
    victim = tmp_path / "victim.md"
    victim.write_text("precious")
    (replay_root / "candidates").mkdir()
    (replay_root / "candidates" / "C-fixt0001.md").symlink_to(victim)
    with pytest.raises(rb.ContainmentError, match="is a symlink"):
        rb.contained_target(replay_root, "candidates", "C-fixt0001.md")
    assert victim.read_text() == "precious"


def test_a_RELATIVE_root_is_refused(replay_root: Path, monkeypatch) -> None:
    monkeypatch.chdir(replay_root.parent)
    with pytest.raises(rb.ContainmentError, match="is not absolute"):
        rb.contained_target(Path("scratch"), "candidates", "C-fixt0001.md")


def test_what_is_genuinely_inside_is_ACCEPTED_and_normalised(replay_root: Path) -> None:
    target = rb.contained_target(replay_root, "candidates", "C-fixt0001.md")
    assert target == replay_root / "candidates" / "C-fixt0001.md"
    assert not target.exists()                      # it only composes


# --- the same escapes THROUGH an event: the id shape refuses them first ----------

# A trailing newline is NOT in this list on purpose: the frontmatter parser
# splits on lines and strips, so `id: C-fixt0001\n` folds to a legitimate id
# before `_ITEM_ID_RE` sees it. The direct battery above covers that shape.
@pytest.mark.parametrize("item_id", ["C-../../x", "/etc/C-fixt0001",
                                     "C-fixt0001/../../x", "C-FIXT0001"], ids=repr)
def test_an_event_whose_item_id_is_not_an_id_is_REFUSED_before_any_path(
        fixture, tmp_path: Path, item_id: str) -> None:
    journal, stores = fixture
    bag = open_bag(journal, f"{RUN_PREFIX}hostile")
    emitter = Emitter.for_run(bag, writer=None, journal_root=journal)
    text = ti.render({"id": item_id, "title": "hostile", "status": "open",
                      "count": "1", "filed": "2026-09-14", "filed_by": "x"}, "\nx\n")
    emitter.paired_write(write_path="tracked:candidates:file",
                         destination=Destination(store="tracked_candidates"),
                         content=text, perform=lambda: "written")
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    with pytest.raises(rb.RebuildError, match="not Tracked Items §2"):
        rb.rebuild(journal, stores, scratch=scratch)
    written = [p for p in scratch.rglob("*") if p.is_file()]
    # Section (a) may have landed before the refusal; nothing escaped it.
    assert all(p.is_relative_to(scratch / "candidates") for p in written)
    assert not (tmp_path / "x").exists()


def test_the_event_ADDRESS_is_never_where_the_file_lands(fixture, tmp_path: Path) -> None:
    """A completion whose address names a path outside every root — the shape
    Phase 7 makes reachable from another machine — lands where the STORE NAME
    and the ITEM ID say, and nowhere else."""
    journal, stores = fixture
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    bag = open_bag(journal, f"{RUN_PREFIX}addr")
    emitter = Emitter.for_run(bag, writer=None, journal_root=journal)
    text = ti.render({"id": "C-fixt0010", "title": "addressed elsewhere",
                      "status": "open", "count": "1", "filed": "2026-09-14",
                      "filed_by": "x"}, "\naddressed\n")
    emitter.paired_write(write_path="tracked:candidates:file",
                         destination=Destination(store="tracked_candidates"),
                         content=text, perform=lambda: "ok",
                         address_of=lambda _r: str(elsewhere / "C-fixt0010.md"))
    (stores / "candidates" / "C-fixt0010.md").write_text(text)   # the live copy
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    report = rb.rebuild(journal, stores, scratch=scratch)
    assert report.stores["candidates"].verdict == "match"
    assert (scratch / "candidates" / "C-fixt0010.md").read_text() == text
    assert not any(elsewhere.iterdir())


def test_a_scratch_under_the_UPLOADED_LOGS_directory_is_refused(fixture, tmp_path) -> None:
    journal, stores = fixture
    scratch = tmp_path / "testing" / "logs" / "scratch"
    scratch.mkdir(parents=True)
    with pytest.raises(rb.RebuildError, match="testing/logs/"):
        rb.rebuild(journal, stores, scratch=scratch)


def test_replay_is_a_PURE_event_to_tree_function() -> None:
    """No shell, no template, no exec, no network: the module imports none of
    the means. A future import of any of these is a change reviewers see."""
    import ast
    source = Path(rb.__file__).read_text(encoding="utf-8")
    imported = {
        (alias.name if isinstance(node, ast.Import) else node.module or "")
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in (node.names if isinstance(node, ast.Import) else [None])
    }
    forbidden = {"subprocess", "shlex", "socket", "urllib", "urllib.request",
                 "http", "http.client", "string", "jinja2", "importlib"}
    assert not (imported & forbidden), imported & forbidden
    assert "exec(" not in source and "eval(" not in source
    assert "os.system" not in source and "popen" not in source


# --- requirement 8: restore -----------------------------------------------------------

def test_restore_is_a_DRY_RUN_by_default_and_writes_nothing(fixture) -> None:
    journal, stores = fixture
    (stores / "candidates" / "C-fixt0005.md").unlink()               # "corruption"
    before = {p.name: p.read_text() for p in (stores / "candidates").glob("*.md")}
    report = rb.restore(journal, stores, "candidates")
    assert not report.applied
    assert report.created == ("C-fixt0005.md",)
    assert report.overwritten == ()
    after = {p.name: p.read_text() for p in (stores / "candidates").glob("*.md")}
    assert after == before
    assert "DRY RUN — nothing written" in rb.render_restore(report)


def test_restore_APPLY_regenerates_the_store_and_leaves_unknown_files_in_place(
        fixture) -> None:
    journal, stores = fixture
    (stores / "candidates" / "C-fixt0005.md").unlink()
    corrupted = stores / "candidates" / "C-fixt0001.md"
    corrupted.write_text("garbage")
    hand_filed = stores / "candidates" / "C-fixt0099.md"
    hand_filed.write_text("---\nid: C-fixt0099\n---\nfiled by hand\n")

    report = rb.restore(journal, stores, "candidates", apply=True)
    assert report.applied
    assert report.created == ("C-fixt0005.md",)
    assert report.overwritten == ("C-fixt0001.md",)
    assert report.left_in_place == ("C-fixt0099.md",)
    assert hand_filed.read_text().endswith("filed by hand\n")
    assert (stores / "candidates" / "C-fixt0005.md").is_file()
    assert corrupted.read_text() != "garbage"
    # Provenance rides along (requirement 9): the restored rows say where from.
    assert report.provenance["C-fixt0005.md"].origin == "journal"
    assert report.provenance["C-fixt0001.md"].origin == "snapshot"
    assert rb.rebuild(journal, stores).stores["candidates"].missing_from_rebuild == (
        "C-fixt0099.md",)


def test_restore_CANNOT_name_operations(fixture) -> None:
    journal, stores = fixture
    with pytest.raises(rb.RebuildError, match="not restorable"):
        rb.restore(journal, stores, "operations", apply=True)
    assert sorted(p.name for p in (stores / "operations").glob("*.md")) == [
        "O-fixt0001.md", "O-fixt0002.md"]


def test_restore_refuses_a_store_the_allowlist_does_not_know(fixture) -> None:
    journal, stores = fixture
    with pytest.raises(rb.RebuildError, match="not restorable"):
        rb.restore(journal, stores, "hooks", apply=True)


def test_restore_REFUSES_a_gapped_store(fixture) -> None:
    journal, stores = fixture
    bag = open_bag(journal, f"{RUN_PREFIX}gap")
    Emitter.for_run(bag, writer=None, journal_root=journal).record_gap(
        write_path="tracked:candidates:file", gap_class=GapClass.WRITE_FAILED,
        destination=Destination(store="tracked_candidates"), lost_bytes=100)
    with pytest.raises(rb.RebuildError, match="is gapped by 1 bag"):
        rb.restore(journal, stores, "candidates", apply=True)


def test_restore_refuses_a_SYMLINKED_stores_root(fixture, tmp_path: Path) -> None:
    journal, stores = fixture
    link = tmp_path / "stores-link"
    link.symlink_to(stores)
    with pytest.raises(rb.ContainmentError, match="is a symlink"):
        rb.restore(journal, link, "candidates")


def test_restore_writes_through_NO_symlink_in_the_live_store(fixture, tmp_path) -> None:
    journal, stores = fixture
    (stores / "candidates" / "C-fixt0005.md").unlink()
    victim = tmp_path / "victim.md"
    victim.write_text("precious")
    (stores / "candidates" / "C-fixt0005.md").symlink_to(victim)
    with pytest.raises(rb.ContainmentError, match="is a symlink"):
        rb.restore(journal, stores, "candidates", apply=True)
    assert victim.read_text() == "precious"


def test_the_written_files_carry_the_journal_FILE_MODE(fixture) -> None:
    journal, stores = fixture
    (stores / "candidates" / "C-fixt0005.md").unlink()
    rb.restore(journal, stores, "candidates", apply=True)
    mode = os.stat(stores / "candidates" / "C-fixt0005.md").st_mode & 0o777
    from modules.journal.bag import FILE_MODE
    assert mode == FILE_MODE


def test_a_live_write_AFTER_the_restore_still_needs_its_emit(fixture) -> None:
    """Requirement 9's third consequence: a write to a rebuilt store is a write
    to the journal. Filing into the restored store WITH the emit rebuilds;
    without it, the next rebuild reports the file."""
    journal, stores = fixture
    rb.restore(journal, stores, "candidates", apply=True)
    bag = open_bag(journal, f"{RUN_PREFIX}after")
    with emitting_into(Emitter.for_run(bag, writer=None, journal_root=journal)):
        ti.file_item(stores, ti.STORES["candidates"], title="after restore",
                     filed_by="t", status="open", body="\nafter\n",
                     today=date(2026, 9, 14), item_id="C-fixt0011")
    assert rb.rebuild(journal, stores).stores["candidates"].verdict == "match"

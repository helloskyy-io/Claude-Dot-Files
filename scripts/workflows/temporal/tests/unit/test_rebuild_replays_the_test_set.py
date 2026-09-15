"""PMP Phase 4 requirements 1, 2, 3, 5 and 9 — the mechanism arm, on the merge path.

Replay reproduces the test set from a starting snapshot forward; the snapshot
has two sections and a version; deleting one emit from a write path makes the
test go RED; every store is enumerated and `tracked/operations/` is a reported,
non-empty exclusion; a rebuilt file is distinguishable by origin.

TWO INPUTS, BOTH SYNTHETIC. Most tests build the fixture fresh under `tmp_path`
through the real writers (`rebuild_fixture.build`), because the negative test
needs the write path LIVE — it deletes the emit from it and watches the rebuild
go red. The last group replays the COMMITTED copy under `tests/fixtures/rebuild/`,
which is what the merge path has, and asserts no real journal byte is in it.

WHAT THIS TIER DOES NOT PROVE, stated so a green run is not over-read: that the
REAL emits on a real host are complete. That is requirement 4's other arm,
`tests/integration/test_the_journal_rebuilds_the_test_set.py`, and it reads the
live journal.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from modules.assistant.tracked import rebuild as rb
from modules.assistant.tracked import tracked_items as ti
from modules.journal import emit as journal_emit
from modules.journal import snapshot as snap
from modules.journal.bag import open_bag
from modules.journal.emit import Emitter, emitting_into
from modules.journal.events import (Destination, EventKind, JournalEvent,
                                    Provenance, event_identity)
from modules.journal.snapshot import Snapshot, SnapshotError, latest_snapshot
from rebuild_fixture import COMMITTED, FIXTURE_EDGE, RUN_PREFIX, build


@pytest.fixture
def fixture(tmp_path: Path) -> tuple[Path, Path]:
    return build(tmp_path / "fixture")


# --- requirement 1: replay reproduces the test set ---------------------------------

def test_replay_from_the_snapshot_forward_REPRODUCES_candidates(fixture) -> None:
    journal, stores = fixture
    report = rb.rebuild(journal, stores)
    verdict = report.stores["candidates"]
    assert verdict.verdict == "match", rb.render_report(report)
    assert verdict.live_files == verdict.rebuilt_files == 7
    assert report.ok


def test_the_rebuild_RECORDS_the_contract_version_it_rebuilt_against(fixture) -> None:
    journal, stores = fixture
    report = rb.rebuild(journal, stores)
    assert report.store_contract == ti.CONTRACT_VERSION == "v1"


def test_a_retried_member_write_is_deduped_and_a_failed_store_write_is_not_applied(
        fixture) -> None:
    """Run B appended its pair twice across two writer folders; run C's intent
    has a store-write failure and no completion. Predicted from the fixture:
    13 read, 11 after dedupe, 4 applied, 1 unapplied, 1 failure."""
    journal, stores = fixture
    report = rb.rebuild(journal, stores)
    assert (report.events_read, report.events_after_dedupe) == (13, 11)
    assert report.intents_applied == 4
    assert report.intents_unapplied == 1
    assert report.store_write_failures == 1
    assert not (stores / "candidates" / "C-fixt0007.md").exists()
    assert "C-fixt0007.md" not in report.stores["candidates"].provenance


def test_the_diff_is_BYTE_IDENTICAL_under_the_empty_normalisation_set(fixture) -> None:
    """A trailing newline is content here, not formatting — the ruling in the
    module docstring — so adding one to a live file is a MISMATCH."""
    journal, stores = fixture
    target = stores / "candidates" / "C-fixt0001.md"
    target.write_text(target.read_text() + "\n")
    report = rb.rebuild(journal, stores)
    assert report.stores["candidates"].mismatched == ("C-fixt0001.md",)
    assert report.stores["candidates"].verdict == "mismatch"
    assert not report.ok


def _paired(emitter: Emitter, *, item_id: str, body: str, run_id: str,
            intent_at: str, completion_at: str) -> None:
    """Append an intent/completion pair with CHOSEN stamps, through the
    emitter's own append — the one place a byte reaches the journal — so the
    on-disk shape is the writer's and only the timestamps are the test's."""
    text = ti.render({"id": item_id, "title": f"stamped {item_id}",
                      "status": "open", "count": "1", "filed": "2026-09-14",
                      "filed_by": run_id}, body)
    common = dict(event_id=event_identity(run_id=run_id,
                                          write_path="tracked:candidates:file",
                                          sequence=0),
                  run_id=run_id, edge_id=emitter.edge_id,
                  key_epoch=emitter.key_epoch,
                  provenance=Provenance.FLEET_AUTHORED,
                  write_path="tracked:candidates:file", sequence=0,
                  content=text, content_bytes=len(text.encode()))
    emitter._append(JournalEvent(kind=EventKind.INTENT, recorded_at=intent_at,
                                 destination=Destination(store="tracked_candidates"),
                                 **common))
    emitter._append(JournalEvent(kind=EventKind.COMPLETION, recorded_at=completion_at,
                                 destination=Destination(store="tracked_candidates",
                                                         address=f"{item_id}.md"),
                                 **common))


def test_a_write_whose_INTENT_predates_the_snapshot_but_LANDED_after_is_applied(
        fixture) -> None:
    """The snapshot's own race. `taken_at` is stamped, then the stores are
    read; a write whose intent was recorded just before the stamp can land
    after the read. It is in neither half unless the boundary is judged by the
    COMPLETION — the event that says the write landed — so that is the rule."""
    journal, stores = fixture
    taken_at = latest_snapshot(journal).taken_at
    before = "2000-01-01T00:00:00Z"
    after = "2999-01-01T00:00:00Z"
    bag = open_bag(journal, f"{RUN_PREFIX}race")
    emitter = Emitter.for_run(bag, writer=None, journal_root=journal)
    body = "\nlanded after the store was read\n"
    _paired(emitter, item_id="C-fixt0030", body=body, run_id=bag.run_id,
            intent_at=before, completion_at=after)
    text = ti.render({"id": "C-fixt0030", "title": "stamped C-fixt0030",
                      "status": "open", "count": "1", "filed": "2026-09-14",
                      "filed_by": bag.run_id}, body)
    (stores / "candidates" / "C-fixt0030.md").write_text(text)   # it landed
    assert before < taken_at < after
    report = rb.rebuild(journal, stores)
    assert report.stores["candidates"].verdict == "match", rb.render_report(report)
    assert report.stores["candidates"].provenance["C-fixt0030.md"].origin == "journal"


def test_a_write_that_COMPLETED_before_the_snapshot_is_the_materialisations_to_hold(
        fixture) -> None:
    """The other side of the boundary: completed before `taken_at`, so the
    store read already saw it (or its absence is a real gap). Not re-applied."""
    journal, stores = fixture
    bag = open_bag(journal, f"{RUN_PREFIX}old")
    emitter = Emitter.for_run(bag, writer=None, journal_root=journal)
    _paired(emitter, item_id="C-fixt0031", body="\nold\n", run_id=bag.run_id,
            intent_at="2000-01-01T00:00:00Z", completion_at="2000-01-01T00:00:01Z")
    report = rb.rebuild(journal, stores)
    assert "C-fixt0031.md" not in report.stores["candidates"].provenance
    assert report.stores["candidates"].verdict == "match"


def test_two_runs_completing_a_write_to_ONE_item_in_the_same_second_is_REPORTED(
        fixture) -> None:
    """`utc_now` is second-precision and `sequence` is per writer, so two runs
    landing on one file in one second have no recorded order. Replay applies
    one and SAYS the order was not the journal's to know — never silently."""
    journal, stores = fixture
    stamp = "2999-01-01T00:00:00Z"
    texts = {}
    for name in ("tie-a", "tie-b"):
        bag = open_bag(journal, f"{RUN_PREFIX}{name}")
        emitter = Emitter.for_run(bag, writer=None, journal_root=journal)
        _paired(emitter, item_id="C-fixt0032", body=f"\nby {name}\n",
                run_id=bag.run_id, intent_at=stamp, completion_at=stamp)
        texts[name] = ti.render({"id": "C-fixt0032", "title": "stamped C-fixt0032",
                                 "status": "open", "count": "1",
                                 "filed": "2026-09-14", "filed_by": bag.run_id},
                                f"\nby {name}\n")
    (stores / "candidates" / "C-fixt0032.md").write_text(texts["tie-b"])
    report = rb.rebuild(journal, stores)
    assert len(report.ambiguous_order) == 1
    assert "C-fixt0032.md" in report.ambiguous_order[0]
    assert f"{RUN_PREFIX}tie-a" in report.ambiguous_order[0]
    assert f"{RUN_PREFIX}tie-b" in report.ambiguous_order[0]
    assert "ORDER NOT RECORDED" in rb.render_report(report)
    # Two runs, DIFFERENT seconds: an order exists and nothing is reported.
    bag = open_bag(journal, f"{RUN_PREFIX}later")
    _paired(Emitter.for_run(bag, writer=None, journal_root=journal),
            item_id="C-fixt0032", body="\nlater\n", run_id=bag.run_id,
            intent_at="2999-01-01T00:00:01Z", completion_at="2999-01-01T00:00:01Z")
    assert rb.rebuild(journal, stores).ambiguous_order == report.ambiguous_order


# --- requirement 3: deleting one emit makes the test fail -------------------------

def test_a_write_that_reaches_the_journal_is_reproduced(tmp_path: Path) -> None:
    """The positive half of the negative test: the same write, WITH its emit."""
    journal, stores = build(tmp_path / "f")
    bag = open_bag(journal, f"{RUN_PREFIX}e")
    with emitting_into(Emitter.for_run(bag, writer=None, journal_root=journal)):
        ti.file_item(stores, ti.STORES["candidates"], title="Nine, emitted",
                     filed_by="t", status="open", body="\nnine\n",
                     today=date(2026, 9, 14), item_id="C-fixt0009")
    report = rb.rebuild(journal, stores)
    assert report.stores["candidates"].verdict == "match"
    assert report.stores["candidates"].provenance["C-fixt0009.md"].origin == "journal"


def test_DELETING_the_emit_from_the_write_path_makes_the_rebuild_RED(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Requirement 3, in-suite. The store write is performed with its emit
    removed — `_write_item` sees no emitter and writes unwrapped — and the
    rebuild reports the file the journal cannot produce. The source-level
    demonstration (mutate `_write_item` itself) is in the PR's decision log."""
    journal, stores = build(tmp_path / "f")
    bag = open_bag(journal, f"{RUN_PREFIX}e")
    emitter = Emitter.for_run(bag, writer=None, journal_root=journal)
    with emitting_into(emitter):
        monkeypatch.setattr(journal_emit, "current_emitter", lambda: None)
        ti.file_item(stores, ti.STORES["candidates"], title="Nine, NOT emitted",
                     filed_by="t", status="open", body="\nnine\n",
                     today=date(2026, 9, 14), item_id="C-fixt0009")
    assert not emitter.events_path.exists(), "the emit was supposed to be deleted"
    report = rb.rebuild(journal, stores)
    verdict = report.stores["candidates"]
    assert verdict.verdict == "mismatch"
    assert verdict.missing_from_rebuild == ("C-fixt0009.md",)
    assert not report.ok
    assert "MISSING from rebuild: C-fixt0009.md" in rb.render_report(report)


# --- requirement 2: the snapshot's shape -------------------------------------------

def test_the_snapshot_has_two_named_sections_and_a_version(fixture) -> None:
    journal, stores = fixture
    paths = snap.snapshot_paths(journal)
    assert len(paths) == 1
    raw = json.loads(paths[0].read_text(encoding="utf-8"))
    assert raw["snapshot_version"] == snap.SNAPSHOT_VERSION == 1
    assert set(raw["store_materialisation"]) == set(rb.COVERED) == {"candidates"}
    assert raw["carried_events"] == []
    assert raw["store_contract"] == ti.CONTRACT_VERSION
    assert raw["edge_id"] == FIXTURE_EDGE
    assert raw["bags_at_snapshot"] == 0          # taken before any run wrote
    # Phase 5 r1: a store that cannot be rebuilt is NAMED, not silently absent.
    assert "operations" in raw["excluded_stores"]
    assert "§1.2" in raw["excluded_stores"]["operations"]


def test_the_snapshot_is_STAMPED_before_the_stores_are_read(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`taken_at` first, then the reads. Stamped after them, a write landing
    during the read is in neither the materialisation nor the replay. The
    order of two calls is the invariant, so the order of two calls is what is
    asserted."""
    journal, stores = build(tmp_path / "f")
    for path in snap.snapshot_paths(journal):
        path.unlink()
    calls: list[str] = []
    real_read_store, real_read_bags = rb.read_store, rb.read_bags
    monkeypatch.setattr(rb, "utc_now", lambda: (calls.append("stamp"), "2026-09-15T00:00:00Z")[1])
    monkeypatch.setattr(rb, "read_store", lambda *a, **k: (calls.append("read_store"), real_read_store(*a, **k))[1])
    monkeypatch.setattr(rb, "read_bags", lambda *a, **k: (calls.append("read_bags"), real_read_bags(*a, **k))[1])
    rb.take_snapshot(journal, stores)
    assert calls[0] == "stamp", calls
    assert "read_store" in calls and "read_bags" in calls
    assert latest_snapshot(journal).taken_at == "2026-09-15T00:00:00Z"


def test_a_snapshot_under_ANOTHER_store_contract_is_REFUSED_not_diffed(fixture) -> None:
    """Requirement 1: a contract change is an upcast on read, never an
    unattributable diff. Until the upcast exists the replay refuses."""
    journal, stores = fixture
    path = snap.snapshot_paths(journal)[0]
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["store_contract"] = "v0"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(rb.RebuildError, match="contract 'v0' and this build writes 'v1'"):
        rb.rebuild(journal, stores)


def test_replay_applies_section_a_and_NEVER_section_b(fixture, tmp_path: Path) -> None:
    """A carried-forward journal-meta event addressed to a covered store is not
    materialised. It carries no content (the constructor refuses one that
    does), and even its presence must not create a file."""
    journal, stores = fixture
    base = latest_snapshot(journal)
    carried = Snapshot(
        snapshot_version=base.snapshot_version, snapshot_id=base.snapshot_id,
        taken_at=base.taken_at, edge_id=base.edge_id,
        journal_schema_version=base.journal_schema_version,
        store_contract=base.store_contract,
        bags_at_snapshot=base.bags_at_snapshot,
        store_materialisation=base.store_materialisation,
        excluded_stores=base.excluded_stores,
        carried_events=({"kind": "gap", "run_id": "fixture-run-rotated",
                         "destination": {"store": "tracked_candidates"},
                         "write_path": "tracked:candidates:file"},))
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    report = rb.rebuild(journal, stores, snapshot=carried, scratch=scratch)
    assert report.stores["candidates"].verdict == "match"
    assert sorted(p.name for p in (scratch / "candidates").iterdir()) == sorted(
        report.stores["candidates"].provenance)


def test_a_carried_event_CARRYING_CONTENT_is_refused_at_construction(fixture) -> None:
    journal, _ = fixture
    base = latest_snapshot(journal)
    with pytest.raises(SnapshotError, match="carries store content"):
        Snapshot(**{**base.__dict__,
                    "carried_events": ({"kind": "gap", "content": "---\nid: C-x\n"},)})


def test_an_unknown_snapshot_version_is_REFUSED_not_guessed(fixture) -> None:
    journal, stores = fixture
    path = snap.snapshot_paths(journal)[0]
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["snapshot_version"] = 2
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(rb.RebuildError, match="version 2 is not 1"):
        rb.rebuild(journal, stores)


def test_no_snapshot_is_a_refusal_that_NAMES_the_command(tmp_path: Path) -> None:
    journal, stores = build(tmp_path / "f")
    for path in snap.snapshot_paths(journal):
        path.unlink()
    with pytest.raises(rb.RebuildError, match=r"rebuild\.py snapshot --stores"):
        rb.rebuild(journal, stores)


def test_a_snapshot_needs_an_edge_that_has_run(tmp_path: Path) -> None:
    """A root with no `edge-id` has had no run; snapshotting it would mint an
    identity outside the one place that mints them."""
    journal = tmp_path / "journal"
    journal.mkdir(mode=0o700)
    stores = tmp_path / "tracked"
    stores.mkdir()
    with pytest.raises(SnapshotError, match="no edge-id"):
        rb.take_snapshot(journal, stores)


# --- requirement 5: every store enumerated; operations is a non-empty exclusion ---

def test_rebuild_enumerates_every_store_the_contract_declares() -> None:
    assert set(rb.STORE_COVERAGE) == set(ti.STORES)
    for name, cov in rb.STORE_COVERAGE.items():
        assert cov.store == name
        assert cov.reason.strip(), f"{name} has no stated reason"
    assert rb.TEST_SET == ("candidates", "operations")
    assert rb.COVERED == ("candidates",)
    assert rb.RESTORE_ALLOWLIST == {"candidates"}
    assert not rb.STORE_COVERAGE["operations"].rebuildable


def test_operations_is_REPORTED_as_a_non_empty_exclusion_never_a_green_diff(
        fixture) -> None:
    journal, stores = fixture
    report = rb.rebuild(journal, stores)
    verdict = report.stores["operations"]
    assert verdict.verdict == "excluded"
    assert verdict.live_files == 2 and verdict.rebuilt_files == 0
    assert "§1.2" in verdict.reason
    rendered = rb.render_report(report)
    assert "tracked/operations/: EXCLUDED — live 2 files, rebuilt 0" in rendered


def test_a_RUN_AUTHORED_write_to_operations_is_refused_and_fails_the_rebuild(
        fixture) -> None:
    """The negative control firing: if a run ever emits into the store the
    enumeration says no run writes, the rebuild neither applies it nor lets it
    pass — the enumeration is wrong or the fleet is, and either is red."""
    journal, stores = fixture
    bag = open_bag(journal, f"{RUN_PREFIX}rogue")
    emitter = Emitter.for_run(bag, writer=None, journal_root=journal)
    text = ti.render({"id": "O-fixt0003", "title": "rogue", "status": "open",
                      "count": "1", "filed": "2026-09-14", "filed_by": "rogue"},
                     "\nrogue\n")
    emitter.paired_write(write_path="tracked:operations:file",
                         destination=Destination(store="tracked_operations"),
                         content=text, perform=lambda: "written")
    report = rb.rebuild(journal, stores)
    assert len(report.applied_to_excluded) == 1
    assert "tracked/operations/" in report.applied_to_excluded[0]
    assert not report.ok
    assert not (stores / "operations" / "O-fixt0003.md").exists()


# --- requirement 9: provenance survives the rebuild -------------------------------

def test_a_rebuilt_row_is_DISTINGUISHABLE_by_origin(fixture) -> None:
    journal, stores = fixture
    report = rb.rebuild(journal, stores)
    prov = report.stores["candidates"].provenance
    assert prov["C-fixt0001.md"].origin == "snapshot"
    assert prov["C-fixt0001.md"].source_id == report.snapshot_id
    assert prov["C-fixt0001.md"].edge_id == FIXTURE_EDGE
    filed = prov["C-fixt0005.md"]
    assert filed.origin == "journal"
    assert filed.run_id == f"{RUN_PREFIX}a"
    assert filed.edge_id == FIXTURE_EDGE
    assert filed.provenance == Provenance.FLEET_AUTHORED.value
    assert filed.key_epoch
    # C-fixt0002 was in the snapshot AND incremented afterwards: the later
    # write wins and the row's origin says so.
    assert prov["C-fixt0002.md"].origin == "journal"
    assert prov["C-fixt0002.md"].run_id == f"{RUN_PREFIX}a"
    origins = {p.origin for p in prov.values()}
    assert origins == {"snapshot", "journal"}


# --- requirement 4: the committed synthetic fixture -------------------------------

def test_the_COMMITTED_fixture_replays_to_a_match() -> None:
    """The merge path's input. If a writer's on-disk format changes, this goes
    red until the fixture is regenerated on purpose (`rebuild_fixture.py`)."""
    assert COMMITTED.is_dir(), f"no committed fixture at {COMMITTED}"
    report = rb.rebuild(COMMITTED / "journal", COMMITTED / "tracked")
    assert report.ok, rb.render_report(report)
    assert report.stores["candidates"].verdict == "match"
    assert report.stores["operations"].verdict == "excluded"
    assert report.bags_seen == 4 and report.bags_gapped == 1


def test_the_committed_fixture_holds_NO_REAL_JOURNAL_BYTES() -> None:
    """Every run id, edge id and item id is recognisably synthetic. A real bag
    copied in — or a real event pasted into one — fails here by its id."""
    bags = rb.read_bags(COMMITTED / "journal")
    assert bags, "the fixture holds no bags — the check examined nothing"
    events = [e for bag in bags for e in bag.events]
    assert events, "the fixture holds no events — the check examined nothing"
    for bag in bags:
        assert bag.run_id.startswith(RUN_PREFIX), bag.run_id
    for event in events:
        assert event.run_id.startswith(RUN_PREFIX), event.event_id
        assert event.edge_id == FIXTURE_EDGE, event.event_id
    for store in ("candidates", "operations"):
        for name in rb.read_store(COMMITTED / "tracked", store):
            assert "fixt" in name, name
    assert (COMMITTED / "journal" / "edge-id").read_text().strip() == FIXTURE_EDGE

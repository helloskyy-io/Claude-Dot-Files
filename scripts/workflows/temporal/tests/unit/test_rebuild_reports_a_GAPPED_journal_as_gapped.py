"""PMP Phase 4 requirement 7 — a journal with holes is reported as gapped, never diffed as complete.

THE NAIVE IMPLEMENTATION FAILS IN BOTH DIRECTIONS, and each direction has a
test here. Diffing a gapped bag like a clean one turns the test red for a reason
that has nothing to do with a missing emit; tolerating the mismatch turns it
green over a record that is genuinely short. So a gap is an INPUT: the bag is
counted against the bags replayed, what each gap covered is named, and a store
a gap was addressed to is `gapped` — its diff reported, not ruled.

BOTH RECORDS OF A GAP ARE READ. `Emitter.record_gap` writes the gap EVENT into
the writer's `events.jsonl` and the `incomplete` FLAG plus a `Journal-Gap` line
into `bag-info.txt`, and either can land without the other. A bag is gapped if
either says so, and the store is attributed from whichever record names it.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from modules.assistant.tracked import rebuild as rb
from common.journal.bag import BAG_INFO_FILE, BAGIT_FILE, open_bag, staging_prefix
from common.journal.emit import Emitter, gap_flag_label
from common.journal.events import Destination, GapClass, gap_event
from common.journal.snapshot import latest_snapshot
from rebuild_fixture import RUN_PREFIX, build


@pytest.fixture
def fixture(tmp_path: Path) -> tuple[Path, Path]:
    return build(tmp_path / "fixture")


def _gap_bag(journal: Path, name: str, *, write_path: str, store: str,
             flag_only: bool = False) -> None:
    bag = open_bag(journal, f"{RUN_PREFIX}{name}")
    if flag_only:
        bag.mark_incomplete(write_path, gap_flag_label(GapClass.WRITE_FAILED))
        return
    Emitter.for_run(bag, writer=None, journal_root=journal).record_gap(
        write_path=write_path, gap_class=GapClass.WRITE_FAILED,
        destination=Destination(store=store), lost_bytes=321)


def test_the_fixture_counts_its_one_transcript_gap_with_its_denominator(fixture) -> None:
    journal, stores = fixture
    report = rb.rebuild(journal, stores)
    assert (report.bags_gapped, report.bags_seen) == (1, 4)
    assert set(report.gapped) == {f"{RUN_PREFIX}d"}
    what = report.gapped[f"{RUN_PREFIX}d"]
    assert any("cli-transcript" in w and "disk_full" in w and "4096" in w for w in what)
    assert "gapped: 1/4" in rb.render_report(report)
    assert "result: PASS (with 1/4 gapped bags)" in rb.render_report(report)


def test_a_gap_NOT_addressed_to_a_covered_store_leaves_that_store_RULED(fixture) -> None:
    journal, stores = fixture
    report = rb.rebuild(journal, stores)
    assert report.stores["candidates"].verdict == "match"
    assert report.stores["candidates"].gapped_bags == ()


def test_a_gap_addressed_to_candidates_makes_the_store_GAPPED_not_red(fixture) -> None:
    """The live store has a file the journal lost. Without the gap the verdict
    would be `mismatch`; with it, the mismatch is reported and NOT ruled."""
    journal, stores = fixture
    (stores / "candidates" / "C-fixt0020.md").write_text("---\nid: C-fixt0020\n---\nlost\n")
    _gap_bag(journal, "g1", write_path="tracked:candidates:file",
             store="tracked_candidates")
    report = rb.rebuild(journal, stores)
    verdict = report.stores["candidates"]
    assert verdict.verdict == "gapped"
    assert verdict.gapped_bags == (f"{RUN_PREFIX}g1",)
    assert verdict.missing_from_rebuild == ("C-fixt0020.md",)     # still REPORTED
    assert report.ok                                              # not RULED red
    assert (report.bags_gapped, report.bags_seen) == (2, 5)
    rendered = rb.render_report(report)
    assert "tracked/candidates/: GAPPED" in rendered
    assert "diff reported, not ruled" in rendered
    assert "MISSING from rebuild: C-fixt0020.md" in rendered


def test_a_gapped_store_is_NOT_diffed_as_complete_even_when_it_would_match(
        fixture) -> None:
    """The other direction: a gap with no visible mismatch is still not a
    green. `gapped` is its own verdict."""
    journal, stores = fixture
    _gap_bag(journal, "g2", write_path="tracked:candidates:increment",
             store="tracked_candidates")
    report = rb.rebuild(journal, stores)
    assert not report.stores["candidates"].differs
    assert report.stores["candidates"].verdict == "gapped"
    assert report.stores["candidates"].verdict != "match"


def test_a_FLAG_ONLY_gap_is_read_from_bag_info_and_attributed_by_write_path(
        fixture) -> None:
    """`record_gap`'s event can fail to land while the flag does. The flag's
    `Journal-Gap` line carries the write path, which names the store."""
    journal, stores = fixture
    _gap_bag(journal, "g3", write_path="tracked:candidates:file",
             store="tracked_candidates", flag_only=True)
    report = rb.rebuild(journal, stores)
    assert f"{RUN_PREFIX}g3" in report.gapped
    assert any(w.startswith("flag: ") for w in report.gapped[f"{RUN_PREFIX}g3"])
    assert report.stores["candidates"].gapped_bags == (f"{RUN_PREFIX}g3",)
    assert report.stores["candidates"].verdict == "gapped"


def test_a_gap_BEFORE_the_snapshot_is_COUNTED_but_rules_no_store(fixture) -> None:
    """The baseline was read straight off the live store after the gap, so
    whatever the gap lost is already reflected there. The bag is still
    counted against the denominator and named as before the snapshot; the
    store is RULED (match here) and a restore is not refused for it. A verdict
    that stayed `gapped` for the journal's lifetime would block requirement 8
    for an incident the snapshot absorbed."""
    journal, stores = fixture
    taken_at = latest_snapshot(journal).taken_at
    bag = open_bag(journal, f"{RUN_PREFIX}g0")
    emitter = Emitter.for_run(bag, writer=None, journal_root=journal)
    old = dataclasses.replace(
        gap_event(run_id=bag.run_id, edge_id=emitter.edge_id,
                  key_epoch=emitter.key_epoch, write_path="tracked:candidates:file",
                  sequence=0, gap_class=GapClass.WRITE_FAILED, lost_bytes=321,
                  destination=Destination(store="tracked_candidates")),
        recorded_at="2000-01-01T00:00:00Z")
    assert old.recorded_at < taken_at
    emitter._append(old)
    report = rb.rebuild(journal, stores)
    assert (report.bags_gapped, report.bags_seen) == (2, 5)          # counted
    assert report.gapped_before_snapshot == (f"{RUN_PREFIX}g0",)
    assert report.stores["candidates"].gapped_bags == ()               # rules nothing
    assert report.stores["candidates"].verdict == "match"
    rendered = rb.render_report(report)
    assert f"gapped bag {RUN_PREFIX}g0: (before the snapshot" in rendered
    assert "gapped: 2/5" in rendered
    rb.restore(journal, stores, "candidates")                          # not refused


def test_a_FLAG_ONLY_gap_before_the_snapshot_is_placed_by_the_labels_own_stamp() -> None:
    """The `Journal-Gap` line opens with `utc_now()`; that stamp, not the
    bag's, decides which side of the boundary the gap is on."""
    bag = rb.BagRead(run_id="x", path=Path("/x"), incomplete=True,
                     gap_labels=("2000-01-01T00:00:00Z tracked:candidates:file — emit failed",
                                 "2999-01-01T00:00:00Z tracked:candidates:increment — emit failed"),
                     events=(), undecodable=(), events_bytes=0)
    assert bag.gapped_stores(since="2026-01-01T00:00:00Z") == {"candidates"}
    assert bag.gapped_stores(since="2999-06-01T00:00:00Z") == set()
    assert bag.gapped_stores() == {"candidates"}
    assert not bag.gapped_before("2026-01-01T00:00:00Z")
    assert bag.gapped_before("3000-01-01T00:00:00Z")


def test_a_gap_addressed_to_an_EXCLUDED_store_counts_at_the_bag_level_only(
        fixture) -> None:
    journal, stores = fixture
    _gap_bag(journal, "g4", write_path="tracked:operations:file",
             store="tracked_operations")
    report = rb.rebuild(journal, stores)
    assert f"{RUN_PREFIX}g4" in report.gapped
    assert report.stores["candidates"].verdict == "match"
    assert report.stores["operations"].verdict == "excluded"


def test_gapped_bags_are_counted_ONCE_per_run_id(fixture) -> None:
    """Two gaps in one bag are one gapped bag with two records."""
    journal, stores = fixture
    bag = open_bag(journal, f"{RUN_PREFIX}g5")
    emitter = Emitter.for_run(bag, writer=None, journal_root=journal)
    for path in ("cli-transcript", "run-log:convergence"):
        emitter.record_gap(write_path=path, gap_class=GapClass.DISK_FULL,
                           destination=Destination(store="filesystem"), lost_bytes=1)
    report = rb.rebuild(journal, stores)
    assert (report.bags_gapped, report.bags_seen) == (2, 5)
    assert len([w for w in report.gapped[f"{RUN_PREFIX}g5"] if w.startswith("event: ")]) == 2


def test_an_UNDECODABLE_event_line_fails_the_rebuild_and_is_named(fixture) -> None:
    """A line the decoder refuses is a write replay could not apply. Stepping
    over it would leave the rebuild short by an amount nobody counted."""
    journal, stores = fixture
    events = journal / f"{RUN_PREFIX}a" / "data" / "events.jsonl"
    events.write_text(events.read_text() + '{"schema_version": 99, "kind": "intent"}\n')
    report = rb.rebuild(journal, stores)
    assert len(report.undecodable) == 1
    assert "schema version 99" in report.undecodable[0]
    assert not report.ok
    assert "UNDECODABLE" in rb.render_report(report)


def test_a_bag_still_being_STAGED_or_a_non_bag_directory_is_not_a_bag(fixture) -> None:
    journal, stores = fixture
    (journal / "not-a-bag").mkdir()
    # open_bag's REAL staging shape: named by `staging_prefix` and already holding
    # the tag files, as a crash before the rename leaves it. A bare empty directory
    # would pass whatever the enumeration did with staging.
    staged = journal / f"{staging_prefix(RUN_PREFIX + 'crashed')}k3j9x2ab"
    staged.mkdir()
    (staged / BAGIT_FILE).write_text("BagIt-Version: 1.0\n")
    (staged / BAG_INFO_FILE).write_text("")
    report = rb.rebuild(journal, stores)
    assert report.bags_seen == 4

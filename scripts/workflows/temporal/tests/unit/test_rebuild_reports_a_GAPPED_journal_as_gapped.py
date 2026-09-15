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

from pathlib import Path

import pytest

from modules.assistant.tracked import rebuild as rb
from modules.journal.bag import open_bag
from modules.journal.emit import Emitter
from modules.journal.events import Destination, GapClass
from rebuild_fixture import RUN_PREFIX, build


@pytest.fixture
def fixture(tmp_path: Path) -> tuple[Path, Path]:
    return build(tmp_path / "fixture")


def _gap_bag(journal: Path, name: str, *, write_path: str, store: str,
             flag_only: bool = False) -> None:
    bag = open_bag(journal, f"{RUN_PREFIX}{name}")
    if flag_only:
        bag.mark_incomplete(write_path, f"emit failed: {GapClass.WRITE_FAILED.value}")
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
    (journal / ".staging-something").mkdir()
    report = rb.rebuild(journal, stores)
    assert report.bags_seen == 4

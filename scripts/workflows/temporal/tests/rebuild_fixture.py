"""The synthetic rebuild fixture — a journal plus stores, built by the REAL writers.

PMP PHASE 4 REQUIREMENT 4's mechanism arm needs a journal on the merge path,
and a runner has none. The two bad answers are ruled out in the phase doc: a
skip that verifies nothing, or a committed copy of a real journal — verbatim
transcripts and whatever secrets they carry, in git history forever, in a repo
whose CI publishes `testing/logs/` as a downloadable artifact. This is the third
answer: a journal built here, from fixture text, by the same code that writes
the real one.

BUILT BY THE WRITERS, NOT HAND-WRITTEN AS JSON. `open_bag`, `Emitter`,
`tracked_items.file_item` / `increment`, `record_gap` and `mark_incomplete` —
the fixture exercises the same call shape a dispatch does, so the on-disk format
the replay reads is whatever those writers produce today. A hand-written
`events.jsonl` would be a second statement of the event format that drifts.

ONE HELPER SERVES THREE CONSUMERS, which is why it is a module beside
`planning_corpus.py` and not a test: the unit tier builds it fresh under
`tmp_path` (the negative test needs the real write path, live); the committed
copy under `tests/fixtures/rebuild/` is what the merge path replays; and the
integration tier uses that copy when it runs on the merge path. A test module
importing another test module is a hygiene violation
(`test_test_tree_hygiene.py`), so the shared code lives here.

EVERY IDENTIFIER IS RECOGNISABLY SYNTHETIC. Run ids carry the `fixture-` prefix,
the edge is `fixture-edge`, and item ids are `X-fixt000N`. `test_rebuild_fixture
_is_synthetic` reads the committed copy and fails on any run id or edge id
outside that shape — that is the "no real journal bytes are ever committed"
constraint as a check rather than a promise.

WHAT THE FIXTURE CONTAINS, and why each part is there:

  snapshot   candidates: C-fixt0001 (open, untouched afterwards), C-fixt0002
             (open, then incremented by run A), C-fixt0003 (adopted, recent —
             terminal-and-recent), C-fixt0004 (rejected, old — terminal-and-
             past-its-window). The retention axis, inside the positive control.
  run A      files C-fixt0005 and increments C-fixt0002. Clean.
  run B      files C-fixt0006 and then RETRIES the same write — the events are
             appended twice; dedupe-on-identity must keep one.
  run C      an intent for C-fixt0007 whose store write FAILED — a
             `store_write_failure` follows it, and the live store never has it.
             `applied_intents` must not apply it.
  run D      a clean tracked write (C-fixt0008) AND a gap on the transcript
             write path — the bag is `incomplete`, counted 1/4, but no covered
             store is gapped, so the candidates verdict is still ruled.
  operations O-fixt0001, O-fixt0002 in the live store, NEVER in the journal.
             The negative control: replay must report them as an exclusion.
"""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

from modules.assistant.tracked import rebuild as rb
from modules.assistant.tracked import tracked_items as ti
from common.journal.bag import DIR_MODE, open_bag
from common.journal.edge_id import adopt_edge_id
from common.journal.emit import Emitter, emitting_into
from common.journal.events import Destination, GapClass

FIXTURE_EDGE = "fixture-edge"
RUN_PREFIX = "fixture-run-"
ITEM_STEM = "fixt"

#: Where the committed copy lives. Regenerate with `regenerate_committed()`
#: when a writer changes its on-disk format — deliberately, in a reviewed diff.
COMMITTED = Path(__file__).resolve().parent / "fixtures" / "rebuild"


def _body(n: int) -> str:
    return (f"\n**Synthetic item {n} for the rebuild fixture.** It says nothing "
            f"about any real run; its only job is to be bytes the journal can "
            f"reproduce.\n")


def _seed_store(stores: Path) -> None:
    """The live stores as they stood at snapshot time — written UNWRAPPED
    (no emitter registered), because they predate the journal by construction."""
    cand = ti.STORES["candidates"]
    ops = ti.STORES["operations"]
    ti.file_item(stores, cand, title="Fixture candidate one, open",
                 filed_by="fixture", status="open", body=_body(1),
                 today=date(2026, 1, 10), item_id="C-fixt0001")
    ti.file_item(stores, cand, title="Fixture candidate two, open then recurred",
                 filed_by="fixture", status="open", body=_body(2),
                 today=date(2026, 1, 11), item_id="C-fixt0002")
    ti.file_item(stores, cand, title="Fixture candidate three, adopted recently",
                 filed_by="fixture", status="adopted", body=_body(3),
                 extras={"decision": "ship"},
                 today=date(2026, 9, 1), item_id="C-fixt0003")
    ti.file_item(stores, cand, title="Fixture candidate four, rejected long ago",
                 filed_by="fixture", status="rejected", body=_body(4),
                 extras={"decision": "reject"},
                 today=date(2025, 12, 1), item_id="C-fixt0004")
    ti.file_item(stores, ops, title="Fixture operation one, operator-only",
                 filed_by="operator", status="open", body=_body(11),
                 extras={"state": "queued"},
                 today=date(2026, 2, 1), item_id="O-fixt0001")
    ti.file_item(stores, ops, title="Fixture operation two, operator-only",
                 filed_by="operator", status="open", body=_body(12),
                 extras={"state": "queued"},
                 today=date(2026, 2, 2), item_id="O-fixt0002")


def _run(journal: Path, name: str) -> tuple:
    bag = open_bag(journal, f"{RUN_PREFIX}{name}",
                   info={"Journal-Workflow": "fixture"})
    return bag, Emitter.for_run(bag, writer=None, journal_root=journal)


def build(root: Path) -> tuple[Path, Path]:
    """Build the whole fixture under `root`; return `(journal_root, stores_root)`.

    The stores are seeded, the snapshot is taken, and THEN the runs write —
    that order is what makes the fixture a replay-from-snapshot-forward case
    rather than a replay-from-nothing one.
    """
    journal = root / "journal"
    stores = root / "tracked"
    root.mkdir(parents=True, exist_ok=True)
    journal.mkdir(mode=DIR_MODE)
    stores.mkdir(mode=DIR_MODE)
    adopt_edge_id(journal, FIXTURE_EDGE, source="fixture")

    _seed_store(stores)
    rb.take_snapshot(journal, stores)
    cand = ti.STORES["candidates"]

    # run A — clean: one file, one increment.
    bag, emitter = _run(journal, "a")
    with emitting_into(emitter):
        ti.file_item(stores, cand, title="Fixture candidate five, filed by run A",
                     filed_by="fixture-run-a", status="open", body=_body(5),
                     today=date(2026, 9, 10), item_id="C-fixt0005")
        ti.increment(stores / "candidates" / "C-fixt0002.md",
                     "seen again by run A", today=date(2026, 9, 10))
    bag.seal()

    # run B — the same write, retried AS A MEMBER: each attempt is a fresh
    # emitter under its own writer subfolder (`filer`, then `filer-2`), so the
    # second attempt cannot see the first's `events.jsonl`, re-derives the same
    # identity, and appends a duplicate pair. That is the case the write-side
    # append-once index cannot reach and `dedupe_on_identity` exists for.
    bag, _ = _run(journal, "b")
    text_path = stores / "candidates" / "C-fixt0006.md"
    for attempt in (1, 2):
        retry = Emitter.for_run(bag, writer="filer", journal_root=journal)
        with emitting_into(retry):
            if text_path.exists():
                # `file_item` refuses an existing id (ids are never reused), so
                # the retry re-performs the WRITE the way a retried activity
                # would: same content, same identity.
                fields, body = ti.parse(text_path)
                ti._write_item(text_path, ti.render(fields, body),
                               write_path="tracked:candidates:file",
                               store_name="candidates")
            else:
                ti.file_item(stores, cand,
                             title="Fixture candidate six, filed twice by run B",
                             filed_by="fixture-run-b", status="open",
                             body=_body(6), today=date(2026, 9, 11),
                             item_id="C-fixt0006")
    bag.seal()

    # run C — an intent whose store write failed. Nothing lands in the store.
    bag, emitter = _run(journal, "c")
    doomed = ti.render({"id": "C-fixt0007", "title": "Fixture candidate seven, "
                        "whose store write failed", "status": "open",
                        "count": "1", "filed": "2026-09-12",
                        "filed_by": "fixture-run-c"}, _body(7))

    def _fail() -> Path:
        raise OSError("fixture: the store refused the write")

    try:
        emitter.paired_write(write_path="tracked:candidates:file",
                             destination=Destination(store="tracked_candidates"),
                             content=doomed, perform=_fail)
    except RuntimeError:
        pass                           # StoreWriteFailed — the record is the point
    bag.seal()

    # run D — one clean tracked write, then a gap on the transcript path.
    bag, emitter = _run(journal, "d")
    with emitting_into(emitter):
        ti.file_item(stores, cand, title="Fixture candidate eight, filed by run D",
                     filed_by="fixture-run-d", status="open", body=_body(8),
                     today=date(2026, 9, 13), item_id="C-fixt0008")
    emitter.record_gap(write_path="cli-transcript", gap_class=GapClass.DISK_FULL,
                       destination=Destination(store="filesystem"),
                       lost_bytes=4096)
    bag.seal()
    return journal, stores


def regenerate_committed() -> None:
    """Rebuild `tests/fixtures/rebuild/` from scratch. Run deliberately."""
    if COMMITTED.exists():
        shutil.rmtree(COMMITTED)
    COMMITTED.mkdir(parents=True)
    build(COMMITTED)


if __name__ == "__main__":
    regenerate_committed()
    print(f"regenerated {COMMITTED}")

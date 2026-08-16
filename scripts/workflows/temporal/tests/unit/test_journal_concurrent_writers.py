"""Two concurrent writers, one valid bag, no collision — requirement 3.

WHY THIS IS A SEPARATE FILE FROM `test_journal_bag.py`. That file checks the
layout API's contract; this one checks the property the contract exists FOR, and
it can only be checked by racing. The two failure modes are different: an API
that hands two callers the same directory fails here and nowhere else.

STRUCTURAL, OVER THE LAYOUT API — the live fan-out demonstration belongs to
Phase 3, because nothing emits until then. What is provable today is that the
allocation primitive cannot hand two callers one directory, and that a bag built
by concurrent writers seals and validates.

THE CONCURRENCY IS REAL AND NOT SIMULATED. Threads contend on the same
filesystem through the same syscalls a fan-out would; the GIL does not serialise
`os.mkdir`, which is where the race lives. A test that called `writer_dir` twice
in sequence would pass against a check-then-create implementation — which is
exactly the implementation this requirement exists to rule out.

WHAT THIS DOES NOT PROVE, so the simplification is checked rather than assumed:

  * It does not establish a global ORDER across writers. Subfolders remove
    contention; they do not sequence anything. The day a workflow needs two
    children's writes ordered against each other is the day this needs a
    sequence number, and that day has a trigger rather than a date: a workflow
    giving two concurrent children write access to one store.
  * It does not reach an EXTERNAL store. Two children mutating one GitHub
    resource is untouched by any of this. Today parallel children are read-only
    critics and a single analyst writes, which is why that is a named trigger
    and not a defect.
  * It uses threads, not processes. A process-level race across two dispatches
    sharing one root exercises the same `os.mkdir` atomicity, but proving that
    needs two interpreters and belongs with the live demonstration.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from modules.journal.bag import DIR_MODE, open_bag
from modules.journal.validate import validate_bag

WRITERS = 16
_BARRIER_TIMEOUT_S = 30


@pytest.fixture
def root(tmp_path: Path) -> Path:
    journal = tmp_path / "journal"
    journal.mkdir(mode=DIR_MODE)
    return journal


def test_sixteen_writers_racing_on_ONE_NAME_get_sixteen_directories(root: Path) -> None:
    """The collision case, forced.

    Every thread asks for the SAME name and they are released together by a
    barrier, so the allocation is genuinely contended rather than merely
    concurrent. Sixteen distinct directories is the property; anything fewer
    means two writers were handed one place to write.
    """
    bag = open_bag(root, "raced")
    barrier = threading.Barrier(WRITERS, timeout=_BARRIER_TIMEOUT_S)
    allocated: list[Path] = []
    failures: list[BaseException] = []
    lock = threading.Lock()

    def claim() -> None:
        try:
            barrier.wait()
            directory = bag.writer_dir("research-critic")
            with lock:
                allocated.append(directory)
        except BaseException as exc:                 # noqa: BLE001 — reported, not swallowed
            with lock:
                failures.append(exc)

    threads = [threading.Thread(target=claim) for _ in range(WRITERS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=_BARRIER_TIMEOUT_S)

    assert not failures, f"a writer failed to allocate: {failures}"
    assert len(allocated) == WRITERS
    assert len(set(allocated)) == WRITERS, (
        f"two writers were handed the same directory: "
        f"{sorted(p.name for p in allocated)}")


def test_concurrent_writers_produce_ONE_bag_that_seals_and_validates(root: Path) -> None:
    """The end-to-end property r3 is actually for.

    Each writer writes its own file into its own directory; the bag then seals
    over all of them and validates clean. A bag that raced and then failed
    validation would mean the manifest was generated against a moving tree.
    """
    bag = open_bag(root, "fanout")
    barrier = threading.Barrier(WRITERS, timeout=_BARRIER_TIMEOUT_S)

    def write(index: int) -> None:
        barrier.wait()
        directory = bag.writer_dir("child")
        (directory / "record.jsonl").write_text(f'{{"writer": {index}}}\n')

    threads = [threading.Thread(target=write, args=(i,)) for i in range(WRITERS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=_BARRIER_TIMEOUT_S)

    bag.seal()
    report = validate_bag(bag.path)

    assert report.ok, report
    assert report.lifecycle == "sealed"
    assert report.payload_files == WRITERS, (
        f"{report.payload_files} of {WRITERS} writers' files reached the manifest")
    assert len({p.name for p in bag.payload_dir.iterdir()}) == WRITERS


def test_no_two_writers_share_a_FILE_which_is_the_actual_requirement(root: Path) -> None:
    """r3's wording is about files, not directories, and the difference matters.

    Distinct directories is the mechanism; "no two writers ever share a file" is
    the property. Asserting the mechanism alone would stay green under a change
    that handed out distinct directories inside a shared file — nonsense today,
    and precisely the kind of thing a later "optimisation" produces.
    """
    bag = open_bag(root, "files")
    owners: dict[Path, int] = {}
    for index in range(WRITERS):
        directory = bag.writer_dir("child")
        target = directory / "record.jsonl"
        assert target not in owners, f"writer {index} was given writer {owners[target]}'s file"
        target.write_text(f"{index}\n")
        owners[target] = index

    assert len(owners) == WRITERS

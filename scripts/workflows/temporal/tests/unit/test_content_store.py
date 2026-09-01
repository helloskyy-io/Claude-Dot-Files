"""The content store: a path is a function of the digest, and a read re-hashes.

TWO PROPERTIES CARRY THIS MODULE AND EVERYTHING ELSE HERE IS SUPPORT. r7(b) says
the on-disk path derives from the computed digest ALONE, because the store sits
under the journal root beside the bags and a source-controlled string reaching
the path writes outside it. r7(d) says every read re-hashes and fails closed,
because a store checked only when somebody invokes a checker is checked never.

WHAT THIS FILE DOES NOT LOOK AT, named because a guard that does not say so
invites being read as complete: it never opens a socket, so nothing here says
anything about the fetch policy (`test_source_fetch.py`), and it never reads a
citation, so nothing here says whether a QUOTE still occurs in the bytes
(`test_verify_citations.py`). It answers only where bytes go and what comes back.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from modules.journal.bag import PAYLOAD_DIR, open_bag
from modules.journal.content_store import (CONTENT_STORE_DIR, DIGEST_ALGORITHM,
                                           ContentStoreError, digest_of_bytes,
                                           has_object, load_object,
                                           object_path, object_relpath,
                                           store_bytes, store_dir,
                                           stored_digests, validated_digest)

SAMPLE = b"the bytes a claim was made against\n"
SAMPLE_DIGEST = hashlib.sha256(SAMPLE).hexdigest()


@pytest.fixture
def bag(root: Path):
    return open_bag(root, "run-content-store")


# --- r7(b): the path is a function of the digest and of nothing else ------------

def test_the_digest_is_the_only_input_to_the_path() -> None:
    """Same digest, same path, every time — and no other argument exists to give.

    The signature IS the guarantee: `object_relpath` takes one parameter, so a
    URL, a filename or a `Content-Disposition` header has nowhere to enter. A
    test that only checked the OUTPUT would pass against a function that also
    accepted a name and ignored it today.
    """
    assert object_relpath(SAMPLE_DIGEST) == (
        f"{PAYLOAD_DIR}/{CONTENT_STORE_DIR}/{DIGEST_ALGORITHM}/"
        f"{SAMPLE_DIGEST[:2]}/{SAMPLE_DIGEST[2:]}")
    assert object_relpath.__code__.co_argcount == 1


@pytest.mark.parametrize("hostile", [
    "../../../../etc/passwd",
    "/etc/passwd",
    "..",
    "ab/../../../etc/passwd",
    SAMPLE_DIGEST.upper(),
    SAMPLE_DIGEST[:-1],
    SAMPLE_DIGEST + "0",
    "",
    "sha256:" + SAMPLE_DIGEST,
    # A TRAILING NEWLINE, because `$` does not mean end-of-string. This gate
    # was `re.compile(r"^…$")` and returned for this value — composing it onto
    # a path in the function whose docstring says such a value is refused
    # rather than composed. `test_journal_regex_anchors.py` holds the CLASS
    # (no `^`/`$` anywhere in `modules/journal/`); this row is the instance,
    # here in the battery a reader extending "what is not a digest" will open.
    SAMPLE_DIGEST + "\n",
    "\n" + SAMPLE_DIGEST,
])
def test_a_value_that_is_not_a_digest_never_reaches_a_path(hostile: str) -> None:
    """The gate is on the WAY IN, so no traversal has to be contained on the way out.

    Uppercase hex is refused rather than folded: a digest in the wrong case did
    not come from this module's own hashing, and normalising it would hide that
    the store had acquired two naming conventions.
    """
    with pytest.raises(ContentStoreError):
        object_relpath(hostile)
    with pytest.raises(ContentStoreError):
        validated_digest(hostile)


def test_a_stored_object_lands_under_the_bags_payload(bag) -> None:
    """r7(a) RULED PER-RUN: the store is INSIDE `data/`, so the bag's manifest covers it.

    This is the assertion the whole r7(a)/Phase-7/Phase-5 reconciliation rests
    on. If the object landed beside the bag rather than inside it, a shipped bag
    would validate clean at a destination with its cited bytes absent, and
    retention deleting a run folder would leave its bytes behind.
    """
    digest = store_bytes(bag.path, SAMPLE)
    target = object_path(bag.path, digest)
    assert target.is_file()
    assert target.read_bytes() == SAMPLE
    assert bag.payload_dir in target.parents
    assert store_dir(bag.path).name == CONTENT_STORE_DIR


def test_the_bags_own_manifest_covers_every_stored_object(bag) -> None:
    """Sealing the bag hashes the store's objects too — no second mechanism needed.

    THE DERIVED HALF OF THE RULING. Phase 7 requirement 2 wants a shipped bag's
    referenced objects to travel with it; because the store is payload, they are
    already in `manifest-sha256.txt` and `validate_bag` already re-hashes them.
    """
    digest = store_bytes(bag.path, SAMPLE)
    bag.seal()
    manifest = bag.manifest_path.read_text(encoding="utf-8")
    assert object_relpath(digest) in manifest
    assert digest in manifest


# --- r7(d): one read path, and it fails closed ----------------------------------

def test_a_round_trip_returns_exactly_what_was_stored(bag) -> None:
    digest = store_bytes(bag.path, SAMPLE)
    assert digest == SAMPLE_DIGEST == digest_of_bytes(SAMPLE)
    assert load_object(bag.path, digest) == SAMPLE


def test_an_absent_object_is_MISSING_and_says_so(bag) -> None:
    """`missing` and `tampered` carry different words because they exit differently."""
    with pytest.raises(ContentStoreError) as caught:
        load_object(bag.path, SAMPLE_DIGEST)
    assert "MISSING" in str(caught.value)
    assert "TAMPERED" not in str(caught.value)
    assert not has_object(bag.path, SAMPLE_DIGEST)


def test_an_ALTERED_STORED_BYTE_is_detected_on_read(bag) -> None:
    """THE PHASE'S OWN CHECKLIST ITEM: change one byte, the read refuses.

    A single byte, not a rewrite — the whole argument for naming an object by
    its checksum is that the name changes if ONE byte does, and a test that
    replaced the whole file would pass against a length check.
    """
    digest = store_bytes(bag.path, SAMPLE)
    target = object_path(bag.path, digest)
    data = bytearray(target.read_bytes())
    data[0] ^= 0x01
    target.write_bytes(bytes(data))

    assert has_object(bag.path, digest), "the file is still there — that is the point"
    with pytest.raises(ContentStoreError) as caught:
        load_object(bag.path, digest)
    assert "TAMPERED" in str(caught.value)
    assert digest_of_bytes(bytes(data)) in str(caught.value), (
        "the refusal must name what the bytes DO hash to, or an operator cannot "
        "tell a corrupted object from one filed under the wrong name")


def test_storing_the_same_bytes_twice_is_one_object(bag) -> None:
    """Content addressing makes idempotency a property rather than a code path."""
    first = store_bytes(bag.path, SAMPLE)
    second = store_bytes(bag.path, SAMPLE)
    assert first == second
    assert stored_digests(bag.path) == [first]


def test_the_store_refuses_text(bag) -> None:
    """Encoding is the caller's decision, because the digest is over the bytes.

    Choosing an encoding here would change the digest a citation was made
    against, which is the one value in this design that must not be this
    module's opinion.
    """
    with pytest.raises(ContentStoreError) as caught:
        store_bytes(bag.path, "not bytes")
    assert "bytes" in str(caught.value)


def test_stored_digests_ignores_a_file_that_is_not_an_object(bag) -> None:
    """A stray file must not be able to impersonate an object.

    Derived by walking rather than by reading an index, so the walk has to say
    what it will and will not count — otherwise a hand-dropped file appears in
    an inventory that other code treats as authoritative.
    """
    digest = store_bytes(bag.path, SAMPLE)
    stray = store_dir(bag.path) / DIGEST_ALGORITHM / SAMPLE_DIGEST[:2] / "README"
    stray.write_text("not an object")
    assert stored_digests(bag.path) == [digest]


def test_an_empty_store_enumerates_to_nothing_rather_than_failing(bag) -> None:
    assert stored_digests(bag.path) == []


# --- the anchor, and the staging name -------------------------------------------

@pytest.mark.parametrize("digest", [
    SAMPLE_DIGEST + "\n",
    SAMPLE_DIGEST + "\r",
    "\n" + SAMPLE_DIGEST,
])
def test_a_digest_with_a_LINE_BREAK_is_refused(digest) -> None:
    """⚠ `^…$` ACCEPTED `"a"*64 + "\\n"` AND COMPOSED IT ONTO A PATH.

    `$` matches before a trailing newline, so the function whose docstring says
    "a value that is not 64 lowercase hex characters is refused here rather than
    composed onto a path" was composing one. `bag._RUN_ID_RE` states the
    `\\A`/`\\Z` rule twelve lines above the function this module reuses; this
    module did not reach for it.

    The leading case is here because `\\A` and `^` differ there too, and the
    hostile parametrization above enumerates seven neighbours and misses all
    three of these.
    """
    with pytest.raises(ContentStoreError):
        validated_digest(digest)
    with pytest.raises(ContentStoreError):
        object_relpath(digest)


def test_two_captures_of_ONE_source_on_two_threads_both_land(tmp_path, monkeypatch) -> None:
    """⚠ THE STAGING NAME CARRIED ONLY THE PID, WHICH IS NOT UNIQUE ACROSS THREADS.

    A Temporal worker runs sync activities on a thread pool — the shape this
    package says the port carries — so two threads capturing the same bytes in
    one process collided on one staging name. The loser's `O_EXCL` raised, and
    its handler then unlinked the file the WINNER was still writing, so
    `os.replace` failed for both and NEITHER capture landed. Both callers got a
    `ContentStoreError` for a store that was working correctly.

    The window is widened deterministically rather than raced for: `os.write` is
    made slow, so the second thread is guaranteed to be inside `store_bytes`
    while the first still holds its staging file.
    """
    import threading
    import time
    from modules.journal import content_store as store_mod

    bag_path = tmp_path / "bag"
    (bag_path / "data").mkdir(parents=True)
    payload = b"one source, two concurrent captures"

    real_write = store_mod.os.write

    def slow_write(fd, data):
        time.sleep(0.15)
        return real_write(fd, data)

    monkeypatch.setattr(store_mod.os, "write", slow_write)

    start = threading.Barrier(4)
    results: list[object] = []
    lock = threading.Lock()

    def capture() -> None:
        start.wait(timeout=10)
        try:
            outcome = store_bytes(bag_path, payload)
        except Exception as exc:               # noqa: BLE001 — the finding IS the exception
            outcome = exc
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=capture) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    failures = [r for r in results if isinstance(r, Exception)]
    assert not failures, f"concurrent captures of one source failed: {failures}"
    assert set(results) == {digest_of_bytes(payload)}
    assert load_object(bag_path, digest_of_bytes(payload)) == payload
    # No staging file survives — the cleanup removed only each call's own.
    leftovers = [p.name for p in bag_path.rglob(".*.part")]
    assert not leftovers, f"staging files left behind: {leftovers}"


def test_the_three_read_failures_are_three_TYPES_not_three_sentences(tmp_path) -> None:
    """⚠ `verify` CLASSIFIED THESE BY SUBSTRING AND A LEGAL RUN ID BROKE IT.

    The outcome class is a fact about WHAT FAILED, so it has to survive the
    message being reworded — and the message embeds the store path, which embeds
    the run id, which `RUN_ID_PERMITTED` lets contain the word `TAMPERED`.
    """
    from modules.journal.content_store import (ObjectCorrupt, ObjectMissing,
                                               ObjectUnreadable)
    bag_path = tmp_path / "bag"
    (bag_path / "data").mkdir(parents=True)

    digest = store_bytes(bag_path, b"the bytes as received")
    absent = digest_of_bytes(b"never stored")

    with pytest.raises(ObjectMissing):
        load_object(bag_path, absent)

    target = object_path(bag_path, digest)
    target.write_bytes(b"different bytes under the same name")
    with pytest.raises(ObjectCorrupt):
        load_object(bag_path, digest)

    # Present and unreadable: a directory where the object should be. NOT
    # `ObjectMissing` — "re-capture the source" is destructive advice for bytes
    # that are merely behind a failing disk or a permission.
    target.unlink()
    target.mkdir()
    with pytest.raises(ObjectUnreadable):
        load_object(bag_path, digest)

    # And every one of them is still a `ContentStoreError`, so a caller that
    # does not care which stays correct.
    assert issubclass(ObjectMissing, ContentStoreError)
    assert issubclass(ObjectCorrupt, ContentStoreError)
    assert issubclass(ObjectUnreadable, ContentStoreError)

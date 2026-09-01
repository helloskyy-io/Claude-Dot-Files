"""The byte cache: sources filed under their own checksum, and read back by it.

PHASE 2 REQUIREMENTS 1, 7(a), 7(b) AND 7(d). What a citation points AT lives
here; what a citation SAYS lives in `citations.py`; how bytes are obtained lives
in `source_fetch.py`. Three files because they fail differently: a store defect
is corruption, a citation defect is a wrong claim, and a fetch defect is a
network policy hole.

r7(a) IS RULED PER-RUN, AND THE STORE SITS INSIDE THE BAG'S PAYLOAD. The draft
implied both shapes and they are not compatible without an answer, so here is the
answer and its cost.

  * **What per-run buys.** A bag stays self-contained. Because the store is under
    `data/`, every stored object is covered by the bag's own
    `manifest-sha256.txt` — so `validate_bag` already re-hashes the cited bytes,
    and Phase 7's requirement 2 ("the content-store objects the bag references
    ship with it") is satisfied by construction rather than by a second sync
    mechanism nobody has written. Phase 5's retention deletes whole run folders,
    which reclaims the cited bytes with them, so its conditional reachability
    pass is a **no-op** and the reason is recorded rather than discovered later.
  * **What per-run costs, stated rather than glossed.** One source cited by many
    runs is stored once per run. That is real duplication and it is the reason
    the shared shape was tempting. It is the cheaper trade here because the
    journal has a size budget measured over the whole root and a reclamation pass
    for a shared store is unbuilt work in a phase that has not started, whereas
    duplicated text sources are bounded by `MAX_SOURCE_BYTES` per object and are
    reclaimed by a deletion that already exists.

  The revisit trigger is a measurement, not a preference: **cited bytes becoming
  a material fraction of the journal budget.** Phase 5's pass reports what it
  could not reclaim, so the evidence arrives on its own.

r7(b) — THE PATH COMES FROM THE COMPUTED DIGEST AND FROM NOTHING ELSE. Not from
the URL, not from a filename, not from a `Content-Disposition` header, not from a
content type. Those are source-controlled strings and the store sits under the
journal root beside the bags, so a crafted URL or a redirect that reached the
path would write outside the store. `object_relpath` takes a digest and only a
digest, and it re-validates the digest's shape before composing — a function that
cannot be handed a name cannot be tricked into one. Human-facing names travel in
the citation record, which is data and never a path component.

THE ALGORITHM IS A PATH PREFIX FOR A REASON. `sha256/` sits above the fan-out so
a future second algorithm gets its own namespace instead of colliding with this
one. Two digests of different algorithms that happen to share a prefix would
otherwise land in the same directory and the store would have no way to say which
function produced a name.

r7(d) — EVERY READ RE-HASHES, AND THERE IS ONE READ. `load_object` is the only
way bytes leave this store, and it fails closed: bytes whose digest is not the
name they are filed under raise rather than return. A store checked only when
somebody remembers to invoke a checker is checked never, so `verify` is this
function run over everything rather than a separate implementation of the same
idea — which is also why there is no second code path for it to drift from.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

from .bag import (DIR_MODE, FILE_MODE, PAYLOAD_DIR, BagError,
                  contained_relpath)

__all__ = ["CONTENT_STORE_DIR", "DIGEST_ALGORITHM", "DIGEST_HEX_LENGTH",
           "FANOUT", "ContentStoreError", "digest_of_bytes", "validated_digest",
           "object_relpath", "store_dir", "object_path", "store_bytes",
           "load_object", "has_object", "stored_digests"]

# Under `data/`, so the bag's own payload manifest covers every stored object.
# The name is hyphenated because it is a directory in a payload, not a Python
# module — `bag.payload_files` walks it like any other payload subtree.
CONTENT_STORE_DIR = "content-store"

DIGEST_ALGORITHM = "sha256"
DIGEST_HEX_LENGTH = 64

# Two hex characters of fan-out. A single flat directory of objects is the shape
# that degrades once a journal accumulates, and one level is enough at this
# scale: a second level buys nothing until an edge holds far more objects than
# the journal's size budget permits.
FANOUT = 2

_HEX_DIGEST_RE = re.compile(r"^[0-9a-f]{%d}$" % DIGEST_HEX_LENGTH)


class ContentStoreError(BagError):
    """A stored object could not be written, found, or trusted.

    A `BagError` — and therefore a `RuntimeError` — for the reason every other
    error in this package is one: entrypoints already print these and the
    message is the diagnostic. A distinct type so a caller can tell a store
    problem from a bag problem without parsing prose.
    """


def digest_of_bytes(data: bytes) -> str:
    """The lowercase hex sha256 of `data`. The store's naming function, in one place."""
    return hashlib.sha256(data).hexdigest()


def validated_digest(digest: str) -> str:
    """`digest` proven to be a lowercase hex sha256, or a refusal.

    THE GATE THAT MAKES r7(b) MECHANICAL RATHER THAN ASPIRATIONAL. Path
    derivation is safe because the only input to it is a value with this shape,
    and this is where the shape is proven. Uppercase is refused rather than
    normalised: a digest arriving in the wrong case came from somewhere that is
    not this module's `digest_of_bytes`, and silently folding it would hide that
    the store has two naming conventions.
    """
    if not isinstance(digest, str) or not _HEX_DIGEST_RE.match(digest):
        raise ContentStoreError(
            f"not a {DIGEST_ALGORITHM} digest: {digest!r}. The content store "
            f"derives every path from the digest it computed and from nothing "
            f"else, so a value that is not {DIGEST_HEX_LENGTH} lowercase hex "
            f"characters is refused here rather than composed onto a path.")
    return digest


def object_relpath(digest: str) -> str:
    """The bag-relative path for `digest`: `data/content-store/sha256/ab/cdef…`.

    A PURE FUNCTION OF THE DIGEST. It takes no name, no URL and no content type,
    which is what makes "a source-controlled string cannot enter the path" a
    property of the code rather than a rule someone has to remember. The return
    is composed from validated hex and from module constants only, so it has no
    traversal to contain.
    """
    safe = validated_digest(digest)
    return "/".join((PAYLOAD_DIR, CONTENT_STORE_DIR, DIGEST_ALGORITHM,
                     safe[:FANOUT], safe[FANOUT:]))


def store_dir(bag_path: Path) -> Path:
    """`<bag>/data/content-store/` — the root of one run's store."""
    return bag_path / PAYLOAD_DIR / CONTENT_STORE_DIR


def object_path(bag_path: Path, digest: str) -> Path:
    """Where `digest`'s bytes live in this bag's store.

    THE JOIN GOES THROUGH `contained_relpath` EVEN THOUGH `object_relpath` IS
    ALREADY A PURE FUNCTION OF VALIDATED HEX. Belt and braces is not the reason —
    uniformity is. This package has produced four containment escapes, each in a
    join whose author could explain why it was safe, and the remedy it settled on
    was one rule applied everywhere rather than a per-site argument. A join that
    opts out on the grounds of being obviously fine is how the next one gets
    written.
    """
    return bag_path / contained_relpath(object_relpath(digest))


def has_object(bag_path: Path, digest: str) -> bool:
    """Whether an object file exists for `digest`. Says nothing about its bytes.

    Deliberately separate from `load_object`, and callers must not read it as a
    verdict: `verify` distinguishes *missing* from *tampered* precisely because
    a file being present is not the same as its bytes being right, and a
    convenience that conflated them would collapse two exit codes into one.
    """
    return object_path(bag_path, digest).is_file()


def store_bytes(bag_path: Path, data: bytes) -> str:
    """Write `data` into this bag's store under its own digest. Returns the digest.

    IDEMPOTENT, AND THE SECOND WRITE IS SKIPPED RATHER THAN REDONE. Two captures
    of the same source inside one run produce the same digest and therefore the
    same path; re-writing identical bytes would be harmless but would also
    rewrite a file the bag may already have sealed over. Content addressing is
    what makes "already there" mean "already correct", and `load_object` is what
    checks that claim on the way out.

    MODES ARE SET AT CREATION for the reason `root._create_with_mode` gives: a
    `mkdir` followed by a `chmod` leaves a readable window on a multi-user host,
    and stored sources are as sensitive as the transcripts beside them.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise ContentStoreError(
            f"the content store holds bytes, not {type(data).__name__}. Encode "
            f"text at the boundary that knows its encoding — the store must "
            f"hash exactly what was received, and choosing an encoding here "
            f"would change the digest the citation was made against.")

    payload = bytes(data)
    digest = digest_of_bytes(payload)
    target = object_path(bag_path, digest)
    if target.is_file():
        return digest

    parent = target.parent
    missing = []
    probe = parent
    while not probe.exists():
        missing.append(probe)
        probe = probe.parent
    for directory in reversed(missing):
        try:
            os.mkdir(directory, DIR_MODE)
        except FileExistsError:
            # Another writer in this run won the race; the directory is the one
            # we wanted either way. Same reasoning as `Bag.writer_dir`.
            continue
        except OSError as exc:
            raise ContentStoreError(
                f"cannot create {directory} for the content store "
                f"({exc.strerror}). The store lives inside the bag's payload, "
                f"so this is the same failure as being unable to write the run's "
                f"record at all.") from exc

    # Written to a temporary name in the same directory and renamed, so a reader
    # never sees a partial object under a digest that promises complete bytes.
    # `os.replace` is atomic within a filesystem, and the temp name carries the
    # pid so two writers in one run cannot collide on it.
    staging = parent / f".{digest}.{os.getpid()}.part"
    try:
        handle = os.open(str(staging), os.O_WRONLY | os.O_CREAT | os.O_EXCL, FILE_MODE)
        try:
            os.write(handle, payload)
        finally:
            os.close(handle)
        os.replace(str(staging), str(target))
    except OSError as exc:
        try:
            staging.unlink()
        except OSError:
            # The staging file could not be removed. Named rather than passed
            # over: it is leftover bytes under a dot-name, not a correctness
            # problem, and the write failure below is the finding.
            pass
        raise ContentStoreError(
            f"cannot write content-store object {digest} into {parent} "
            f"({exc.strerror}).") from exc
    return digest


def load_object(bag_path: Path, digest: str) -> bytes:
    """The bytes filed under `digest`, re-hashed on the way out. Fails closed.

    THE ONLY READ PATH, WHICH IS r7(d). Every consumer — `verify`, a resolve
    activity, anything Phase 6 later adds — comes through here, so re-hashing is
    not a mode that can be switched off and there is no second implementation to
    drift from. The cost is one hash per read of an object bounded by
    `MAX_SOURCE_BYTES`; the alternative is a store whose integrity is asserted.

    THE TWO FAILURES ARE DIFFERENT TYPES OF EVENT AND CARRY DIFFERENT WORDS,
    because `verify`'s exit codes are built on the distinction: an absent object
    means the check could not be made, and a mismatched one means the store
    itself is not to be trusted.
    """
    target = object_path(bag_path, digest)
    try:
        data = target.read_bytes()
    except FileNotFoundError:
        raise ContentStoreError(
            f"content-store object {digest} is MISSING from {store_dir(bag_path)}. "
            f"Nothing was stored under that digest in this bag, so the citation "
            f"naming it cannot be checked at all.") from None
    except OSError as exc:
        raise ContentStoreError(
            f"content-store object {digest} could not be read from {target} "
            f"({exc.strerror}).") from exc

    actual = digest_of_bytes(data)
    if actual != digest:
        raise ContentStoreError(
            f"content-store object {digest} is TAMPERED: its bytes hash to "
            f"{actual}. An object is named by its own checksum, so a mismatch "
            f"means the stored bytes were changed after they were filed — the "
            f"store, not the citation, is the thing that failed.")
    return data


def stored_digests(bag_path: Path) -> list[str]:
    """Every digest this bag's store holds, sorted. Names only; nothing is read.

    Derived by walking the store rather than by reading an index, because an
    index is a second statement of the same fact and this package's whole thesis
    is that two statements of one fact diverge. A file whose name is not a valid
    digest is skipped: it did not come from `store_bytes`, and reporting it as an
    object would let a stray file impersonate one.
    """
    root = store_dir(bag_path) / DIGEST_ALGORITHM
    if not root.is_dir():
        return []
    found = []
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        prefix = path.parent.name
        candidate = f"{prefix}{path.name}"
        if _HEX_DIGEST_RE.match(candidate):
            found.append(candidate)
    return sorted(found)

"""One run's folder: a BagIt bag, its lifecycle, and the writes that change it.

WHY BAGIT AND NOT A HAND-ROLLED MANIFEST. Without a per-run manifest declaring
what is in the folder, deciphering a run degrades into guessing by file
extension and every new artifact kind silently breaks every existing reader.
BagIt (RFC 8493) describes itself as "a filesystem convention, not a
serialization format", which is this phase's own thesis in the standard's words,
and it discharges three requirements of later phases for free: the manifest IS
checksums (so validating a bag is re-hashing its payload), `bag-info.txt` is the
defined home for arbitrary bag metadata, and bags transfer as loose directory
trees or serialized.

WHAT THE MANIFEST DOES NOT GIVE, so it is not over-read: it is regenerable by
anyone who can write the bag. It proves integrity against accident and transport
corruption; it proves nothing against a party with write access — and every run
this fleet dispatches executes as the same user that owns the root, with
permissions bypassed. **Append-only here is a convention the fleet keeps, not a
property the filesystem enforces.** That is stated rather than left for a reader
to assume "immutable" is a guarantee.

FOUR STATES, TWO FIELDS, AND COLLAPSING THEM IS THE FAILURE MODE:

  * `lifecycle` is `open` or `sealed`. A run in flight has no manifest yet, and
    validation must report that as *open*, not as *failed* — a crashed run
    leaving an open bag is the case the design most cares about.
  * `redacted` and `incomplete` are INDEPENDENT FLAGS on top of it. Both leave a
    bag whose payload differs from what was first written and both regenerate
    the manifest, so a single field would make a bag that lost data to a full
    disk indistinguishable from one a human deliberately redacted. The first is
    a defect to investigate; the second is the system working.

WHY THERE IS NO `tagmanifest-sha256.txt`, which RFC 8493 permits and which the
obvious reading of "check everything" would add. Tag files are not covered by
the payload manifest, and this design DEPENDS on that: every lifecycle event
after sealing — a redaction tombstone, a gap record — is an append to
`bag-info.txt`. Under a tag manifest each of those would invalidate the bag
until the tag manifest were regenerated too, which converts a one-line append
into a two-file transaction with a window where the bag reads as corrupt. The
payload is what needs proving; the tag files are what record why.

THE BAG-LEVEL SCHEMA VERSION IS A SUMMARY, NOT THE AUTHORITY. Phase 3 puts
`schema_version` on every event and that is the value an upcaster reads: a bag
can span a schema change, and an event aggregated to object storage travels away
from its bag entirely.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

__all__ = ["JOURNAL_SCHEMA_VERSION", "BAGIT_VERSION", "TAG_FILE_ENCODING",
           "PAYLOAD_DIR", "MANIFEST_FILE", "BAGIT_FILE", "BAG_INFO_FILE",
           "DIR_MODE", "FILE_MODE", "REDACTION_MARKER", "BagError", "Bag",
           "open_bag", "read_tag_file", "utc_now", "payload_files", "sha256_of"]

# THE EVENT SCHEMA VERSION. Bumping it is a deliberate act with a written rule
# beside it (see the module docstring and the phase doc's § Schema versioning):
# version every event, never mutate a written one, upcast on read. A v1 event
# written without a version field is unrecoverable, which is why this exists in
# Phase 1 rather than waiting for the upcaster mechanism to be designed.
JOURNAL_SCHEMA_VERSION = 1

# RFC 8493 requires `bagit.txt` to consist of EXACTLY these two lines. Anything
# else there makes the bag non-conforming and forfeits the entire reason BagIt
# was chosen, which is why the schema version lives in `bag-info.txt` instead.
BAGIT_VERSION = "1.0"
TAG_FILE_ENCODING = "UTF-8"

PAYLOAD_DIR = "data"
MANIFEST_FILE = "manifest-sha256.txt"
BAGIT_FILE = "bagit.txt"
BAG_INFO_FILE = "bag-info.txt"

DIR_MODE = 0o700
FILE_MODE = 0o600

# What a redacted payload file is replaced BY. A marker rather than a deletion:
# a deleted file would leave the bag reporting a missing payload file, which is
# indistinguishable from data loss and turns the integrity signal into noise.
REDACTION_MARKER = (
    "[REDACTED]\n"
    "This payload file was replaced under the one stated exception to the "
    "journal's immutability rule. The bag's bag-info.txt carries a "
    "Journal-Redaction record naming what was replaced, when, and why.\n"
)

# Tag-file labels this fleet defines beyond RFC 8493's reserved set. Each is
# repeatable except where noted; readers must treat repetition as meaningful.
LABEL_SCHEMA_VERSION = "Event-Schema-Version"      # exactly one
LABEL_REDACTION = "Journal-Redaction"              # zero or more; presence => redacted
LABEL_INCOMPLETE = "Journal-Incomplete"            # zero or one; "true" => incomplete
LABEL_GAP = "Journal-Gap"                          # zero or more; what was lost
LABEL_SEALED_AT = "Journal-Sealed-At"              # exactly one, once sealed

_LABEL_RE = re.compile(r"^([^:\s][^:]*):\s?(.*)$")
_SAFE_SEGMENT_RE = re.compile(r"[^A-Za-z0-9._-]+")


class BagError(RuntimeError):
    """A bag could not be opened or changed as asked.

    `RuntimeError` for the same reason `JournalRootError` is: every entrypoint
    already prints these, and the message is the diagnostic.
    """


def utc_now() -> str:
    """One spelling of "now" for every tag record this module writes.

    Second precision and an explicit `Z`. Tag files are read by humans as often
    as by tools, and a redaction tombstone whose timestamp needs a library to
    interpret is a tombstone nobody reads.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_tag_file(path: Path, lines: list[str]) -> None:
    """Write a tag file at `FILE_MODE`, with the mode set at creation.

    Same discipline as the root's directory mode: an `open()` followed by a
    `chmod` leaves a window in which a world-readable file holding transcript
    metadata exists on a multi-user host.
    """
    body = "".join(line if line.endswith("\n") else line + "\n" for line in lines)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, FILE_MODE)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(body)


def _append_tag_line(path: Path, label: str, value: str) -> None:
    """Append one `Label: value` line to an existing tag file.

    NEWLINES IN A VALUE ARE REFUSED RATHER THAN FOLDED. RFC 8493 permits
    continuation lines, and this module reads them, but writing one would let a
    caller's free text (a redaction reason, a gap description) forge a new label
    — a `reason` containing "\\nJournal-Incomplete: true" would silently set a
    flag no caller asked for. Refusing at the write is cheaper than sanitising,
    and it makes the caller's mistake visible where it is made.
    """
    if "\n" in value or "\r" in value:
        raise BagError(
            f"tag value for {label} contains a newline: {value!r}. A multi-line "
            f"value would fold into what reads as a second label, so free text "
            f"is refused here rather than sanitised.")
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"{label}: {value}\n")


def _set_tag_line(path: Path, label: str, value: str) -> None:
    """Replace a SINGLE-VALUED tag label in place, or append it if absent.

    NOT `_append_tag_line`, AND THE DIFFERENCE IS RFC CONFORMANCE. `Payload-Oxum`
    and `Bagging-Date` are reserved elements that describe the bag as it stands;
    a redaction and a gap both reseal, so appending would leave a bag carrying
    three `Payload-Oxum` lines with no rule saying which one is current. Found by
    running a redaction against a real bag, not by reading the RFC — the first
    seal looked perfectly correct.

    The line is rewritten WHERE IT WAS rather than moved to the end, so a bag's
    tag file keeps a stable shape across reseals and a diff between two bags
    shows the value that changed rather than the ordering that did.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    replacement = f"{label}: {value}"
    kept: list[str] = []
    written = False
    for line in lines:
        match = _LABEL_RE.match(line)
        if match is not None and match.group(1).strip() == label:
            if written:
                continue          # drop a duplicate written before this rule existed
            kept.append(replacement)
            written = True
            continue
        kept.append(line)
    if not written:
        kept.append(replacement)
    _write_tag_file(path, kept)


def read_tag_file(path: Path) -> list[tuple[str, str]]:
    """`(label, value)` in file order, with RFC 8493 continuation lines folded in.

    A LIST AND NOT A DICT, because every label this fleet defines except the
    schema version is repeatable and a dict would silently keep one redaction
    record out of three. `Journal-Redaction` repeating is the normal case.
    """
    entries: list[tuple[str, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        if raw[0] in " \t" and entries:
            label, value = entries[-1]
            entries[-1] = (label, f"{value} {raw.strip()}")
            continue
        match = _LABEL_RE.match(raw)
        if match is None:
            raise BagError(
                f"{path} line is not a `Label: value` tag line and does not "
                f"continue one: {raw!r}")
        entries.append((match.group(1).strip(), match.group(2).strip()))
    return entries


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def payload_files(bag_path: Path) -> list[Path]:
    """Every regular file under `data/`, sorted, as bag-relative paths.

    Sorted so a manifest is byte-stable across regenerations — a manifest whose
    line order depended on directory iteration order would show a spurious diff
    on every reseal and make a real change hard to see.
    """
    payload = bag_path / PAYLOAD_DIR
    found = [p for p in payload.rglob("*") if p.is_file()]
    return sorted(p.relative_to(bag_path) for p in found)


@dataclass(frozen=True)
class Bag:
    """One run's folder. Frozen: the path is the identity, and it does not move."""

    path: Path
    run_id: str

    # --- reading -------------------------------------------------------------

    @property
    def payload_dir(self) -> Path:
        return self.path / PAYLOAD_DIR

    @property
    def manifest_path(self) -> Path:
        return self.path / MANIFEST_FILE

    @property
    def info_path(self) -> Path:
        return self.path / BAG_INFO_FILE

    @property
    def lifecycle(self) -> str:
        """`sealed` once a manifest exists, `open` until then. Never a third value."""
        return "sealed" if self.manifest_path.is_file() else "open"

    def info(self) -> list[tuple[str, str]]:
        return read_tag_file(self.info_path)

    # --- writing -------------------------------------------------------------

    def writer_dir(self, name: str) -> Path:
        """Allocate a payload subfolder no other writer can be handed.

        THIS IS REQUIREMENT 3, AND THE ALLOCATION IS THE MECHANISM. The
        event-sourcing literature warns that without a sequence number and a
        single writer per aggregate, events get reordered; this fleet fans out
        (a verify round has dispatched two critics 21 seconds apart), so
        concurrent writers are real today. Giving each writer its own directory
        removes the contention entirely, because no two writers share a file.

        COLLISION IS RESOLVED BY `os.mkdir` WINNING OR LOSING, not by a
        check-then-create. `os.mkdir` is atomic, so two processes asking for the
        same name cannot both be told yes: the loser gets `FileExistsError` and
        takes the next ordinal. A `if not exists: mkdir` would hand both the same
        directory under precisely the concurrency this exists to survive.

        WHAT THIS DOES NOT DO, so the simplification is checked rather than
        assumed: it does not establish a global ORDER across writers, and it does
        not help if two children mutate the same EXTERNAL store. Today neither
        matters — parallel children are read-only critics and a single analyst
        writes — so the day a workflow gives two concurrent children write access
        to one store is the day this needs a sequence number. Cheap to add now,
        unrecoverable in old data.
        """
        slug = _SAFE_SEGMENT_RE.sub("-", name).strip("-") or "writer"
        for ordinal in range(1, 10_000):
            candidate = self.payload_dir / (slug if ordinal == 1 else f"{slug}-{ordinal}")
            try:
                os.mkdir(str(candidate), DIR_MODE)
            except FileExistsError:
                continue
            return candidate
        raise BagError(
            f"could not allocate a payload subfolder for {name!r} in "
            f"{self.payload_dir}: 9999 names are taken. That is not a collision, "
            f"it is a loop writing one directory per iteration.")

    def seal(self) -> Path:
        """Write `manifest-sha256.txt` over the payload. The bag becomes `sealed`.

        Also records `Payload-Oxum` and `Bagging-Date`, both RFC 8493 reserved
        labels: the Oxum ("octetcount.streamcount") is the standard's own cheap
        completeness check and it is what lets a reader spot a truncated
        transfer without re-hashing anything.

        RE-SEALING REGENERATES rather than refusing, because regeneration is
        exactly what a redaction and a gap require. What must never happen is
        re-OPENING a sealed bag, and that is refused in `open_bag`.

        THE THREE TAG VALUES ARE SET, NOT APPENDED. They describe the bag as it
        currently stands, so a reseal must replace them; appending is what the
        first draft did and it produced a bag carrying three `Payload-Oxum` lines
        after one redaction and one gap. `Journal-Sealed-At` is separate from
        `Bagging-Date` because RFC 8493 specifies the latter as `YYYY-MM-DD`, and
        a day is not enough to order two seals of the same bag.
        """
        files = payload_files(self.path)
        lines = [f"{sha256_of(self.path / rel)}  {rel.as_posix()}" for rel in files]
        _write_tag_file(self.manifest_path, lines)

        octets = sum((self.path / rel).stat().st_size for rel in files)
        sealed_at = utc_now()
        _set_tag_line(self.info_path, "Payload-Oxum", f"{octets}.{len(files)}")
        _set_tag_line(self.info_path, "Bagging-Date", sealed_at[:10])
        _set_tag_line(self.info_path, LABEL_SEALED_AT, sealed_at)
        return self.manifest_path

    def redact(self, payload_relpath: str, reason: str) -> None:
        """Replace one payload file with a marker and record the tombstone.

        THE ONE SANCTIONED CHANGE TO AN OTHERWISE-IMMUTABLE RECORD, and it is
        designed here rather than invented during an incident. Three of this
        component's rules compose into a trap: the transcript goes in and is not
        optional, authored content goes in verbatim, and no written event is
        mutated. The fleet runs with permissions bypassed, so a transcript
        carries the literal input of every Bash call — and the first time a
        token or a bearer credential lands in one, it is sealed into a
        manifest-covered payload file.

        A REDACTION IS THEREFORE A SUPERSEDING APPEND, NOT A DELETION: the file
        is replaced by a marker, the tombstone names what and why, and the
        manifest is regenerated so the bag stays honestly valid rather than
        quietly broken. Nothing is silently edited — the record stays complete
        about the FACT of the redaction, which is what keeps it separately
        auditable from a gap.
        """
        # Containment before existence: a tag file exists, so asking `is_file()`
        # first would let `bag-info.txt` reach the "no such payload file" branch
        # and be reported as a typo rather than as the category error it is.
        if Path(payload_relpath).parts[:1] != (PAYLOAD_DIR,):
            raise BagError(
                f"cannot redact {payload_relpath}: only payload files under "
                f"{PAYLOAD_DIR}/ are redactable. A tag file is the record OF the "
                f"redaction and cannot also be its subject.")
        target = self.path / payload_relpath
        if not target.is_file():
            raise BagError(
                f"cannot redact {payload_relpath}: no such payload file in "
                f"{self.path}. A redaction names a file that exists; naming one "
                f"that does not is either a typo or a bag that already lost it, "
                f"and those need different answers.")

        _write_tag_file(target, [REDACTION_MARKER.rstrip("\n")])
        _append_tag_line(self.info_path, LABEL_REDACTION,
                         f"{utc_now()} {payload_relpath} — {reason}")
        if self.lifecycle == "sealed":
            self.seal()

    def mark_incomplete(self, what: str, why: str) -> None:
        """Record that a write into this bag FAILED, and what was lost.

        PHASE 3 OWNS WHEN THIS IS CALLED — its rule is *a gap may exist; a silent
        gap may not*. Phase 1 owns only the place the fact is recorded, because a
        bag's states have to be enumerated before anything writes into it.

        `incomplete` IS NOT `open`. `open` means nobody has sealed this yet,
        which is normal; `incomplete` means a write was attempted and did not
        land, which never is. It is also not `redacted`: both leave a bag whose
        payload differs from what was first written, and conflating them makes a
        disk-full data loss look like a deliberate human act.

        IDEMPOTENT ON THE FLAG, APPEND-ONLY ON THE GAPS. A run that loses three
        writes carries three gap records and one flag — the flag answers "is
        this bag missing something", the records answer "what".
        """
        if not self.incomplete:
            _append_tag_line(self.info_path, LABEL_INCOMPLETE, "true")
        _append_tag_line(self.info_path, LABEL_GAP, f"{utc_now()} {what} — {why}")
        if self.lifecycle == "sealed":
            self.seal()

    # --- flags ---------------------------------------------------------------

    @property
    def redacted(self) -> bool:
        return any(label == LABEL_REDACTION for label, _ in self.info())

    @property
    def incomplete(self) -> bool:
        return any(label == LABEL_INCOMPLETE and value.strip().lower() == "true"
                   for label, value in self.info())


def open_bag(root: Path, run_id: str, *, info: dict[str, str] | None = None) -> Bag:
    """Create (or adopt) `<root>/<run_id>/` as an open BagIt bag.

    KEYED BY `run_id`, NEVER BY PATH — requirement 2, and it is the one place
    this design deliberately does NOT copy Claude Code, whose store keys by
    mangled project path. This fleet runs everything in worktrees, so every
    worktree would become its own project and one logical run would scatter
    across several folders, unassemblable.

    IDEMPOTENT PER §7.1, WHICH IS WHAT MAKES IT AN ACTIVITY. Called twice for one
    `run_id` it adopts the existing open bag rather than rewriting its tag files
    — a rewritten `bag-info.txt` would drop a tombstone or a gap record, which is
    exactly the silent loss the whole component exists to prevent. Under Temporal
    a retry is a new attempt, and this is what makes that safe.

    RE-OPENING A SEALED BAG IS REFUSED. A sealed bag's manifest is a statement
    about a finished run; appending to it under the same `run_id` would make that
    statement false with nothing recording that it had been.
    """
    if not run_id or "/" in run_id or os.sep in run_id or run_id in (".", ".."):
        raise BagError(
            f"run_id {run_id!r} is not usable as a folder name. It is the bag's "
            f"identity and its only address; a separator or a relative segment "
            f"would put the bag somewhere other than under the root.")

    bag_path = root / run_id
    if bag_path.exists():
        if not bag_path.is_dir():
            raise BagError(f"{bag_path} exists and is not a directory")
        bag = Bag(path=bag_path, run_id=run_id)
        if bag.lifecycle == "sealed":
            raise BagError(
                f"bag {run_id} is already SEALED at {bag_path}. Its manifest is a "
                f"statement about a finished run; re-opening it under the same "
                f"run_id would make that statement false with nothing recording "
                f"that it had been. Mint a new run_id.")
        return bag

    os.mkdir(str(bag_path), DIR_MODE)
    os.mkdir(str(bag_path / PAYLOAD_DIR), DIR_MODE)

    # EXACTLY TWO LINES. RFC 8493 §2.1.1 requires it, and requirement 6 turns on
    # it: anything else here makes the bag non-conforming, which is why the
    # schema version goes in bag-info.txt instead.
    _write_tag_file(bag_path / BAGIT_FILE, [
        f"BagIt-Version: {BAGIT_VERSION}",
        f"Tag-File-Character-Encoding: {TAG_FILE_ENCODING}",
    ])

    entries = {
        "External-Identifier": run_id,
        LABEL_SCHEMA_VERSION: str(JOURNAL_SCHEMA_VERSION),
        "Bag-Software-Agent": "claude-dot-files journal (Persistent Memory Protocol Phase 1)",
    }
    entries.update(info or {})
    _write_tag_file(bag_path / BAG_INFO_FILE,
                    [f"{label}: {value}" for label, value in entries.items()])

    return Bag(path=bag_path, run_id=run_id)

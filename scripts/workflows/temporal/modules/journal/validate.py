"""Does this folder hold a well-formed bag, and what happened to the run in it?

TWO QUESTIONS, AND THE REPORT NEVER COLLAPSES THEM INTO ONE LABEL.

  * `ok` answers *do the bytes on disk match the manifest*. It is an integrity
    verdict and nothing else.
  * `lifecycle` / `redacted` / `incomplete` answer *what happened to this run*.
    All three are reported ALWAYS, on every report, whatever their values.

REQUIREMENT 8 IS THE "ALWAYS", NOT THE FIELDS. Three consumers depend on this
output — Phase 4's gap accounting, Phase 5 r9 and Phase 7 r4 — and a validator
that printed `redacted` where `sealed` was also true would strand all three. A
redaction only ever applies to a bag that was sealed, and `incomplete` can
accompany either, so a single collapsed label would make a bag that lost data to
a full disk indistinguishable from one a human deliberately redacted. The first
is a defect to investigate; the second is the system working.

AN OPEN BAG IS NOT A FAILED BAG. RFC 8493 requires every file listed in a payload
manifest to be present for a bag to be *complete*, which makes the naive reading
— a bag either validates or it does not — wrong three times over. A run in flight
has no manifest yet. A crashed run leaving an open bag is the case this design
most cares about, so `open` is a first-class state and not an error.

MISSING IS NOT MISMATCHED IS NOT UNLISTED, and the distinction is the diagnosis:

  * `missing`    — the manifest lists it, the filesystem does not have it. Data
                   loss, or a truncated transfer.
  * `mismatched` — present, and its bytes are not the bytes that were hashed.
                   Corruption, or an edit to a record that must not be edited.
  * `unlisted`   — on disk under `data/` and absent from the manifest. A write
                   that landed after the seal, which is the immutability rule
                   being broken from the other direction and is invisible to any
                   check that only walks the manifest.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from . import bag as bagmod
from .bag import (BAGIT_FILE, BAG_INFO_FILE, MANIFEST_FILE, PAYLOAD_DIR,
                  BagError, contained_relpath, payload_files, payload_symlinks,
                  sha256_of, read_tag_file)

__all__ = ["BagReport", "validate_bag", "render_report", "main"]


@dataclass(frozen=True)
class BagReport:
    """The full answer about one bag. Every field is populated on every report."""

    path: Path
    lifecycle: str                                    # "open" | "sealed"
    redacted: bool
    incomplete: bool
    structural: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    mismatched: tuple[str, ...] = ()
    unlisted: tuple[str, ...] = ()
    payload_files: int = 0
    payload_bytes: int = 0
    redactions: tuple[str, ...] = ()
    gaps: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        """DERIVED, NEVER STORED — a `PASS` printed above a missing file is the
        single worst output an integrity tool can produce, and a stored field
        makes it constructible. `ok` is the conjunction of the four evidence
        tuples and nothing else, so a report cannot be built that disagrees with
        its own contents. The flags are deliberately absent from it: `redacted`
        and `incomplete` describe what happened to the RUN, `ok` describes the
        BYTES, and a redacted bag whose payload matches its manifest is valid.
        """
        return not (self.structural or self.missing or self.mismatched or self.unlisted)


def _parse_manifest(text: str, path: Path) -> dict[str, str]:
    """`{payload-relative-path: checksum}` from a `manifest-sha256.txt`.

    RFC 8493 §2.1.3 separates the checksum from the filename by whitespace; this
    module writes two spaces (the `sha256sum` convention) and reads any amount,
    because a bag may have been written by a different BagIt implementation and
    refusing one on spacing would be a compatibility bug wearing a strictness
    costume.

    THE CHECKSUM'S SHAPE IS CHECKED, AND A MUTATION IS WHY. Splitting on
    whitespace alone accepts any two tokens, so `this is not a manifest line`
    parsed as checksum `this` over path `is not a manifest line` — and the bag
    came back reporting one missing file and one unlisted file rather than a
    corrupt manifest. Both halves of that report were true and neither was the
    diagnosis. A `manifest-sha256.txt` entry is 64 hex characters by definition,
    so the shape is asserted and a garbage manifest says so.

    A REPEATED PATH IS ALSO REFUSED. Two lines naming one file is a manifest
    that does not decide what the file's checksum is, and a plain dict
    assignment would silently keep the last one.

    ⚠ THE PATH IS CONTAINED, AND WITHOUT THIS THE VALIDATOR CERTIFIED A LIE.
    `manifest-sha256.txt` is untrusted input — it is a file on disk that this
    module did not necessarily write — and `validate_bag` joined its second field
    straight onto the bag's path. Demonstrated against a real bag: a bag with an
    EMPTY `data/` and the single line
    `<sha256 of /etc/hostname>  ../../../../etc/hostname` reported `result: PASS`,
    because the escaped file existed and hashed correctly, `missing` was empty,
    and `unlisted` could not see it (`present` held nothing). An absolute entry
    is worse still: `Path("/j/run") / "/etc/hostname"` DISCARDS the base entirely.
    This is the same class `Bag._contained_payload_target` was hardened against
    one module over, which is why both now call `contained_relpath`.

    NORMALISING ALSO FIXES A FALSE FAILURE, and the two are one edit because they
    are one omission. A foreign bag written with the `sha256sum` convention
    `./data/x.txt` previously reported that file as present-and-matching AND as
    `unlisted` — `ok=False` on a healthy bag — which contradicted this
    docstring's own stated tolerance for other BagIt implementations.
    """
    entries: dict[str, str] = {}
    for lineno, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        parts = raw.split(None, 1)
        if len(parts) != 2:
            raise BagError(f"{path}:{lineno} is not `<checksum> <path>`: {raw!r}")
        checksum, listed_name = parts[0].lower(), parts[1].strip()
        if len(checksum) != 64 or any(c not in "0123456789abcdef" for c in checksum):
            raise BagError(
                f"{path}:{lineno} does not begin with a 64-character sha256 "
                f"checksum: {raw!r}")
        try:
            name = contained_relpath(listed_name)
        except BagError as exc:
            raise BagError(f"{path}:{lineno} names a path this bag cannot "
                           f"contain: {exc}") from exc
        if name in entries:
            raise BagError(
                f"{path}:{lineno} lists {name} a second time, with a different "
                f"checksum than line above it claimed" if entries[name] != checksum
                else f"{path}:{lineno} lists {name} twice")
        entries[name] = checksum
    return entries


def validate_bag(bag_path: Path) -> BagReport:
    """Re-hash the payload and report integrity plus all three state fields.

    RE-HASHES RATHER THAN TRUSTING THE OXUM. `Payload-Oxum` is a cheap
    completeness check and this bag writes one, but a byte count that happens to
    match proves nothing about content — and content is the property a journal
    that is the sole authority for a rebuilt store actually needs.

    STRUCTURAL PROBLEMS ARE COLLECTED, NOT RAISED. A caller sweeping a journal of
    a thousand bags wants a report per bag, not an exception on the first
    malformed one; and a bag that is structurally broken still has a lifecycle
    worth reporting.

    ⚠ AND THAT INCLUDES A FILESYSTEM ERROR, which is the half the sentence above
    promised before the code delivered it. Only `BagError` was collected; every
    `read_text`, `stat`, `rglob` and `open` here could raise `OSError` straight
    out of the function. The reachable case is not exotic — Phase 3 writes into
    bags while they exist, so a sweep over a live journal meets a file that
    vanished between `rglob` and `stat`, and one such bag killed the whole sweep.
    """
    structural: list[str] = []
    entries: list[tuple[str, str]] = []
    on_disk: list[Path] = []
    payload_bytes = 0
    missing: list[str] = []
    mismatched: list[str] = []
    unlisted: list[str] = []

    # THE STATE FIELDS ARE NEVER DERIVED HERE — `bag.bag_state` is the one place
    # a `bag-info.txt` label becomes one of them, and this function's copy of that
    # rule is the defect that produced the shared function. Re-derived at each
    # point new information arrives, so a partial report still carries everything
    # known at the point it stopped.
    state = bagmod.bag_state(manifest_exists=False, info_entries=())

    if not bag_path.is_dir():
        return BagReport(path=bag_path, lifecycle=state.lifecycle,
                         redacted=state.redacted, incomplete=state.incomplete,
                         structural=(f"{bag_path} is not a directory",))

    manifest_path = bag_path / MANIFEST_FILE

    try:
        bagit = bag_path / BAGIT_FILE
        if not bagit.is_file():
            structural.append(f"{BAGIT_FILE} is missing — RFC 8493 requires it")
        else:
            lines = [ln for ln in bagit.read_text(encoding="utf-8").splitlines() if ln.strip()]
            if len(lines) != 2:
                structural.append(
                    f"{BAGIT_FILE} has {len(lines)} lines; RFC 8493 §2.1.1 requires "
                    f"exactly two (BagIt-Version, Tag-File-Character-Encoding)")
            elif not lines[0].startswith("BagIt-Version:") or \
                    not lines[1].startswith("Tag-File-Character-Encoding:"):
                structural.append(
                    f"{BAGIT_FILE} does not declare BagIt-Version then "
                    f"Tag-File-Character-Encoding, in that order")

        info_path = bag_path / BAG_INFO_FILE
        if not info_path.is_file():
            structural.append(
                f"{BAG_INFO_FILE} is missing — it is where this fleet's schema "
                f"version, redaction tombstones and gap records live")
        else:
            try:
                entries = read_tag_file(info_path)
            except BagError as exc:
                structural.append(str(exc))
                entries = []
            if not any(label == bagmod.LABEL_SCHEMA_VERSION for label, _ in entries):
                structural.append(
                    f"{BAG_INFO_FILE} carries no {bagmod.LABEL_SCHEMA_VERSION} — an "
                    f"event written without a version is unrecoverable on read")

        # BOTH INPUTS ARE NOW KNOWN, so the state is derived once, HERE, and
        # before the payload walk rather than after it. A bag whose payload
        # cannot be read still reports the lifecycle and flags its tag files
        # already told us — under the old ordering an `OSError` on the walk
        # returned `open` for a bag that was plainly sealed, which is the report
        # collapsing under exactly the partial-read case it promises to survive.
        # `entries` is `[]` when `bag-info.txt` is missing or unparseable, which
        # is what makes the flags false rather than unknown; the missing file is
        # already a structural finding, so the report says both.
        state = bagmod.bag_state(manifest_exists=manifest_path.is_file(),
                                 info_entries=entries)

        if not (bag_path / PAYLOAD_DIR).is_dir():
            structural.append(f"{PAYLOAD_DIR}/ is missing — a bag has a payload directory")

        # A SYMLINK IN A PAYLOAD IS A STRUCTURAL PROBLEM, NOT A FILE TO HASH. BagIt
        # bags transfer as directory trees and a link's target does not travel with
        # one, so the receiving end gets a dangling pointer where the manifest
        # promised bytes. `payload_files` excludes them; without this they would be
        # silently uncovered by the manifest instead of reported.
        for link in payload_symlinks(bag_path):
            structural.append(
                f"{link.as_posix()} is a symlink — a bag holds bytes, not pointers to "
                f"bytes outside it, which do not survive a transfer")

        on_disk = payload_files(bag_path) if (bag_path / PAYLOAD_DIR).is_dir() else []
        payload_bytes = sum((bag_path / rel).stat().st_size for rel in on_disk)

        if state.lifecycle == "sealed":
            try:
                listed = _parse_manifest(manifest_path.read_text(encoding="utf-8"),
                                         manifest_path)
            except BagError as exc:
                structural.append(str(exc))
                listed = {}

            present = {rel.as_posix() for rel in on_disk}
            for name, checksum in sorted(listed.items()):
                # `name` came through `contained_relpath`, so this join cannot
                # leave the bag. That is the ONLY reason this line is safe, and
                # it was not safe before that call existed.
                target = bag_path / name
                if not target.is_file():
                    missing.append(name)
                    continue
                if sha256_of(target) != checksum:
                    mismatched.append(name)
            unlisted = sorted(present - set(listed))
    except OSError as exc:
        structural.append(
            f"could not be read: {exc.strerror} at "
            f"{getattr(exc, 'filename', None) or bag_path}. The report below is "
            f"partial — everything after this point was not examined.")

    return BagReport(
        path=bag_path, lifecycle=state.lifecycle, redacted=state.redacted,
        incomplete=state.incomplete,
        structural=tuple(structural), missing=tuple(missing),
        mismatched=tuple(mismatched), unlisted=tuple(unlisted),
        payload_files=len(on_disk), payload_bytes=payload_bytes,
        redactions=state.redactions, gaps=state.gaps)


def render_report(report: BagReport) -> str:
    """Human-readable, and it ALWAYS prints all three state fields.

    The always is the contract. An operator reading `redacted: false` learns
    something; an operator reading a report that simply omits the line cannot
    tell whether the bag is un-redacted or the validator did not look.
    """
    lines = [
        f"bag        : {report.path}",
        f"result     : {'PASS' if report.ok else 'FAIL'}",
        f"lifecycle  : {report.lifecycle}",
        f"redacted   : {str(report.redacted).lower()}",
        f"incomplete : {str(report.incomplete).lower()}",
        f"payload    : {report.payload_files} files, {report.payload_bytes} bytes",
    ]
    for label, items in (("structural", report.structural),
                         ("missing", report.missing),
                         ("mismatched", report.mismatched),
                         ("unlisted", report.unlisted),
                         ("redactions", report.redactions),
                         ("gaps", report.gaps)):
        for item in items:
            lines.append(f"  {label}: {item}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Validate one bag or every bag directly under one journal root.

    Exit 0 only if every bag validated. A flag is NOT a failure — a redacted or
    incomplete bag whose bytes match its manifest exits 0, because those flags
    describe the run and `ok` describes the bytes.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("usage: validate_bag.py <bag-dir-or-journal-root> [...]", file=sys.stderr)
        return 2

    reports: list[BagReport] = []
    for raw in args:
        target = Path(raw).expanduser()
        if (target / BAGIT_FILE).is_file() or not target.is_dir():
            reports.append(validate_bag(target))
            continue
        children = sorted(p for p in target.iterdir() if p.is_dir())
        if not children:
            print(f"no bags under {target}", file=sys.stderr)
            return 2
        reports.extend(validate_bag(child) for child in children)

    for report in reports:
        print(render_report(report))
        print()

    failed = [r for r in reports if not r.ok]
    print(f"{len(reports) - len(failed)}/{len(reports)} bags valid")
    return 1 if failed else 0

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
import posixpath
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# The `LABEL_*` names are part of the public surface, not implementation detail:
# `validate.py` reads all four lifecycle labels to build its report and the tests
# assert against them. Omitting them here understated the contract that Phase 6's
# reader and Phase 7's sync will both bind to.
__all__ = ["JOURNAL_SCHEMA_VERSION", "BAGIT_VERSION", "TAG_FILE_ENCODING",
           "PAYLOAD_DIR", "MANIFEST_FILE", "BAGIT_FILE", "BAG_INFO_FILE",
           "DIR_MODE", "FILE_MODE", "REDACTION_MARKER", "BagError", "Bag",
           "open_bag", "read_tag_file", "utc_now", "payload_files",
           "payload_symlinks", "sha256_of", "contained_relpath",
           "RUN_ID_PERMITTED", "RUN_ID_PERMITTED_DESCRIPTION",
           "safe_payload_segment",
           "RUN_ID_MAX_LENGTH", "validated_run_id", "folds_a_tag_line",
           "LABEL_SCHEMA_VERSION", "LABEL_REDACTION", "LABEL_INCOMPLETE",
           "LABEL_GAP", "LABEL_SEALED_AT", "BagState", "bag_state",
           "lifecycle_of"]

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


def contained_relpath(relpath: str, *, subdir: str = PAYLOAD_DIR) -> str:
    """A caller-supplied bag-relative path, normalised and proven to stay under `subdir`.

    ONE NAME FOR A RULE THIS PACKAGE HAD THREE COPIES AND ONE HOLE OF, and the
    hole is why it exists rather than tidiness. The shape is always the same — an
    externally-supplied string composed onto a trusted base path — and three
    review passes each found one instance of it:

      * `redact()`'s first-segment check, which `Path("data/../../x").parts[:1]`
        walks straight through;
      * a symlink under `data/`, which `is_file()` follows;
      * `validate.py`'s manifest join, where `bag_path / name` with `name` read
        out of an untrusted `manifest-sha256.txt` hashed a file OUTSIDE the bag
        and reported the bag as PASS with an empty payload.

    Three correct hand-written implementations and one missing one is what a rule
    kept as prose produces. `test_journal_containment.py` is the other half: it
    sweeps this package for entry points that take a caller-supplied path and
    fails when one is not covered here.

    LEXICAL ONLY, AND THAT SPLIT IS DELIBERATE. This resolves `.` and `..` and
    refuses an absolute path or an escape — the half every caller needs. It does
    NOT touch the filesystem, because the two callers need opposite things from a
    symlink: `Bag._contained_payload_target` must REFUSE one before writing
    through it, while `validate_bag` must REPORT one and keep going. Doing that
    here would force one of those two to be wrong.

    Returns the normalised POSIX path, which is also what a manifest should have
    been written with — so a foreign bag using the `sha256sum` convention
    (`./data/x.txt`) normalises to the same key this module writes rather than
    being reported as both present and unlisted.
    """
    if not relpath or not relpath.strip():
        raise BagError(
            f"empty bag-relative path: {relpath!r}. A path into a bag names a "
            f"file; naming nothing is a caller bug, not an empty selection.")

    if os.path.isabs(relpath) or posixpath.isabs(relpath):
        raise BagError(
            f"{relpath!r} is an absolute path. A bag-relative path is composed "
            f"onto the bag's own directory, so an absolute one addresses a file "
            f"the bag does not contain — and joining it would silently DISCARD "
            f"the bag's path entirely rather than escape it by degrees.")

    normalised = posixpath.normpath(relpath.replace(os.sep, "/"))
    if normalised != subdir and not normalised.startswith(f"{subdir}/"):
        raise BagError(
            f"{relpath!r} normalises to {normalised!r}, which is not under "
            f"{subdir}/ — it addresses a file outside this bag. A path that "
            f"leaves the payload directory is refused rather than rewritten, "
            f"because the caller asking for it has a different bug than the one "
            f"a rewrite would hide.")
    return normalised


# --- run identity: ONE statement of what a run id may be -------------------------
#
# THE PERMITTED SET, STATED AS WHAT IS ALLOWED. Phase 9 r6. Every other guard in
# this module that predates it is a DENY-list, and § *And the rule stayed prose*
# of the Phase 1 doc is the measurement that says why that shape keeps failing
# here: four instances of one forging defect, three fixed correctly against the
# operand that had been exploited, and the fourth arriving through the operand
# nobody had enumerated. An allowlist inverts the default — a character nobody
# thought of is refused rather than admitted by omission.
RUN_ID_PERMITTED = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ" "abcdefghijklmnopqrstuvwxyz" "0123456789" "._-")

# THE ONE PROSE SPELLING OF THE SET ABOVE, and the reason it is a constant rather
# than a sentence is that it was written out twice — once in this module's
# refusal message and once in `dispatch_identity`'s `--run-id` help text — while
# r6 says the permitted set is expressed in ONE place. Two hand-written copies of
# a rule is the shape this whole requirement exists to end, one altitude up.
# `test_journal_tag_lines.py` expands this string and asserts it is exactly
# `RUN_ID_PERMITTED`, so the prose cannot drift from the set it describes.
RUN_ID_PERMITTED_DESCRIPTION = "A-Z a-z 0-9 . _ -"

# 128 is a bound, not a measurement, and it is stated as one. Today's ids are 32
# hex characters; the ceiling exists so a pathological name cannot become a path
# component that a filesystem, an object key or an operator report has to
# truncate — truncation is how two ids become one name.
RUN_ID_MAX_LENGTH = 128

# `\A` and `\Z`, NEVER `^` and `$`. `$` matches immediately before a trailing
# newline, so `re.match(r"^[A-Za-z0-9._-]+$", "abc\n")` SUCCEEDS — an anchor that
# admits the exact character this requirement exists to refuse. Named here
# because it is the same class of hole as the deny-list it replaces, one layer
# down, and a reader tightening this regex later needs to know why it is spelled
# this way.
_RUN_ID_RE = re.compile(r"\A[A-Za-z0-9._-]+\Z")


def safe_payload_segment(name: str) -> str:
    """A caller-supplied name reduced to ONE payload directory segment.

    EXTRACTED FROM `Bag.writer_dir` WHEN THE CONTENT STORE NEEDED THE SAME RULE.
    It is the same shape `contained_relpath` was extracted for: a rule this
    package would otherwise hold two hand-written copies of, which is how the
    four containment escapes already found here were produced. Every character
    outside `[A-Za-z0-9._-]` maps to `-`, so no separator survives and no
    segment can be a bare `..` that `mkdir` would follow; an input that reduces
    to nothing yields `writer` rather than an empty component.

    ⚠ THE DOTS-ONLY CASE IS EXPLICIT BECAUSE THE ALLOWLIST ADMITS `.`, AND THAT
    HOLE WAS LIVE. `[A-Za-z0-9._-]` permits a dot, so `writer_dir("..")` slugged
    to a bare `..` and joined onto the payload directory — the containment
    declaration for that join said "no segment can be a bare `..`", and it was
    describing a rule the code did not have. Nothing escaped in practice only
    because `os.mkdir` fails on a directory that already exists and the caller
    took the next ordinal; that is luck, not the rule. A dots-only name is not a
    usable directory name in any case, so it takes the same fallback an empty
    one does.
    """
    slug = _SAFE_SEGMENT_RE.sub("-", name).strip("-")
    if not slug or set(slug) == {"."}:
        return "writer"
    return slug


def validated_run_id(run_id: str) -> str:
    """A caller-supplied run id, proven to be usable by ALL FIVE of its consumers.

    THE ONE PLACE THE PERMITTED SET IS EXPRESSED (Phase 9 r6), on the model of
    `contained_relpath` — and for the same measured reason. The rule this
    replaces was `if not run_id or "/" in run_id or os.sep in run_id or run_id in
    (".", "..")`, which is a list of the separators an author happened to think
    of. It refuses `a/b` and admits `a\\nJournal-Incomplete: true`.

    WHY THE FORGING CASE IS REAL RATHER THAN THEORETICAL. The id is written into
    a tag-line composer as `f"{label}: {value}"`, and `open_bag` places
    `External-Identifier` straight into its module-owned `entries` dict — the
    `_refuse_folded_value` loop iterates `info`, the CALLER-supplied half, so the
    run id never reached that check at all. Before Phase 9 r2 the id was minted
    inside this package from a fixed alphabet, so nothing could exploit it. r2 is
    what makes the value external, and this is the check that lands with it.

    THE SET IS RULED AGAINST FIVE CONSUMERS, NOT AGAINST THE FOLDER NAME ALONE.
    A character admitted into v1 bag names cannot be withdrawn afterwards, so
    each consumer's constraint is written down rather than assumed:

      * a DIRECTORY NAME under the journal root — so no `/`, no `\\0`, and
        neither `.` nor `..`, which are refused below by name because they pass
        the character check;
      * a `bag-info.txt` TAG VALUE — so nothing `_LABEL_RE` reads as a label
        (`:`), nothing that can start a continuation line (leading whitespace),
        and no character `read_tag_file`'s parser treats as a line break;
      * an input to that same tag-file READER — the round trip is the property,
        and `test_journal_tag_lines.py` asserts it rather than reasoning about it;
      * a string rendered into the OPERATOR-FACING validator report — so no
        control characters and no ANSI introducer, both of which would let a run
        id rewrite a report about itself;
      * a PHASE 7 OBJECT KEY — `[A-Za-z0-9._-]` is a
        strict subset of the S3 "safe characters" set, so a bag name never needs
        percent-encoding on the way to object storage. `%` is deliberately OUT
        for the same reason: a key that is already encoded and a key that needs
        encoding are indistinguishable once written.

    AND IT ADMITS THE FLEET'S FUTURE NAMES, which is why it is not `[0-9a-f]`.
    Phase 9 § *The identity is a joint design* leaves open that the run id may
    become whatever the orchestrator calls a dispatch. A set ruled against
    today's `uuid4().hex` would be trivially hex and would refuse
    `build-2026-08-24-a1b2c3`, a Temporal workflow id, or a slug — every shape
    the joint design is likely to produce. This set is also EXACTLY the alphabet
    `_SAFE_SEGMENT_RE` already slugifies writer subfolder names to, so one bag's
    directory and its subdirectories share one alphabet rather than two.

    ⚠ THIS IS A CONVENTION AMONG COOPERATING CALLERS, NOT AN ATTESTATION
    (Phase 9 r1). Nothing here verifies that the caller supplying an id is the
    fleet's naming authority — this module's own docstring already says the
    manifest "proves nothing against a party with write access". A later phase
    must not read `External-Identifier` as attested rather than declared.

    Returns the id unchanged. It never rewrites: a caller handing over a name
    that needs fixing has a different bug from one handing over a valid name, and
    a rewrite would file the run's record under a name the caller does not know.
    """
    if not isinstance(run_id, str):
        raise BagError(
            f"run_id must be a string, not {type(run_id).__name__}: {run_id!r}. "
            f"It is the bag's folder name and a tag value; anything else is "
            f"stringified by accident somewhere downstream, under a name nobody "
            f"chose.")
    if not run_id:
        raise BagError(
            "run_id is empty. It is the bag's identity and its only address; an "
            "empty name would file the run's record under the journal root "
            "itself.")
    if len(run_id) > RUN_ID_MAX_LENGTH:
        raise BagError(
            f"run_id is {len(run_id)} characters, over the {RUN_ID_MAX_LENGTH} "
            f"ceiling: {run_id[:64]!r}…. A name long enough to be truncated by a "
            f"filesystem, an object key or a report is a name that can collide "
            f"with another run's after truncation.")
    if run_id in (".", ".."):
        raise BagError(
            f"run_id {run_id!r} is a relative path segment. Every character in "
            f"it is permitted, which is exactly why this is checked by name — "
            f"joined onto the journal root it addresses the root or its parent "
            f"rather than a bag inside it.")
    if not _RUN_ID_RE.match(run_id):
        refused = sorted({c for c in run_id if c not in RUN_ID_PERMITTED})
        raise BagError(
            f"run_id {run_id!r} contains {len(refused)} character(s) outside the "
            f"permitted set: {[repr(c) for c in refused]}.\n"
            f"  permitted: {RUN_ID_PERMITTED_DESCRIPTION}\n"
            f"  failing property: a run id is a directory name, a bag-info.txt "
            f"tag value, an input to the tag-file reader, a string in the "
            f"operator's validator report AND an object key. This is an "
            f"ALLOWLIST rather than a list of forbidden separators, so a "
            f"character nobody enumerated is refused by default — which is the "
            f"failure the deny-list it replaced had four times.\n"
            f"  remedy: name the run with the permitted set. Every shape the "
            f"fleet uses fits it — a hex nonce, a dated slug, an orchestrator's "
            f"workflow id.")
    return run_id


def utc_now() -> str:
    """One spelling of "now" for every tag record this module writes.

    Second precision and an explicit `Z`. Tag files are read by humans as often
    as by tools, and a redaction tombstone whose timestamp needs a library to
    interpret is a tombstone nobody reads.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def folds_a_tag_line(text: str) -> bool:
    """True when `read_tag_file` would see more than one line where one was written.

    ASKED OF THE PARSER, NEVER OF A LIST OF LINE TERMINATORS. This replaced
    `"\\n" in value or "\\r" in value`, which is an author's list — and it was
    LEAKIER THAN IT READ. `read_tag_file` parses with `str.splitlines()`, which
    also breaks on `\\v`, `\\f`, `\\x1c`, `\\x1d`, `\\x1e`, `\\x85`, `\\u2028` and
    `\\u2029`. A value carrying any of those eight passed the deny-list, was
    written as one physical line, and **read back as two entries** — the second
    forging a lifecycle flag, which is the identical defect the newline check was
    written to close. Eight spellings survived a check aimed at two.

    So the question is put to `str.splitlines()` itself. Whatever that method
    treats as a break, this refuses — including any break a future CPython adds,
    without this function being edited. That is the whole reason it is a
    derivation rather than a constant: enumerating the set is the move that has
    already failed here.

    THE TRAILING-WHITESPACE HALF IS THE SAME PROPERTY, not a tidiness rule.
    `read_tag_file` returns `match.group(2).strip()`, so a value with surrounding
    space reads back as a DIFFERENT STRING from the one written. The stated
    property is that reading a tag file returns exactly the entries written, and
    a silently-stripped value breaks it just as a folded one does — it simply
    fails quietly instead of loudly.

    An EMPTY value is legal and folds nothing: `f"{label}: "` reads back through
    `_LABEL_RE` as `(label, "")`, which is the value that was written.
    """
    if text == "":
        return False
    return text.splitlines() != [text] or text.strip() != text


def _refuse_forged_label(label: str) -> None:
    """The LABEL is composed onto the same line as its value, so it forges the same way.

    THIS IS THE VALUE CHECK'S MISSING HALF, and it survived a pass that fixed the
    value because the fix was written against the one parameter that had been
    exploited. `open_bag` passes a caller-supplied `label` straight through to
    `f"{label}: {value}"`, so `{"X\\nJournal-Incomplete: true": "y"}` forges the
    flag exactly as the value case did. Every fleet call site passes a literal
    today, which is precisely why nothing caught it.

    The four refusals are `_LABEL_RE`'s own requirements read back as a writer's
    contract: a label that cannot be parsed back out of the file it was written
    into is a label that silently changes meaning on read.
    """
    if not label or label != label.strip():
        raise BagError(
            f"tag label {label!r} is empty or carries surrounding whitespace. A "
            f"line starting with whitespace is a CONTINUATION of the label above "
            f"it under RFC 8493, so this would append to a record it does not own.")
    if folds_a_tag_line(label):
        raise BagError(
            f"tag label {label!r} does not survive a round trip through "
            f"`read_tag_file`. It is written onto the same line as its value, so "
            f"a label carrying anything `str.splitlines()` breaks on forges a "
            f"second record. This asks the parser rather than listing newlines — "
            f"see `folds_a_tag_line`, and the eight terminators the list missed.")
    if ":" in label:
        raise BagError(
            f"tag label {label!r} contains a colon, which separates a label from "
            f"its value. Written out and read back, everything after the first "
            f"colon becomes the value and the record means something else.")


def _refuse_folded_value(label: str, value: str) -> None:
    """A tag value carrying a newline would fold into what reads as a NEW LABEL.

    ONE RULE, ONE PLACE, BECAUSE HAVING IT IN ONLY ONE OF TWO WRITERS IS HOW IT
    WAS BYPASSED. `_append_tag_line` refused newlines from the start; the
    bag-info file written at creation did not, so a caller passing
    `{"Journal-Worktree": "wt\\nJournal-Incomplete: true"}` set a flag nobody
    asked for — demonstrated against a real bag.

    THE THREE TAG-LINE COMPOSERS CALL THIS: `_append_tag_line`, `_set_tag_line`
    and `open_bag`'s creation loop. `_write_tag_file` deliberately does NOT — it
    also writes `manifest-sha256.txt` and the redaction marker, neither of which
    is a tag line, so a per-line tag check there would refuse correct output.
    Stated because an earlier version of this docstring claimed "both writers"
    when there were three and one of them did not call it.
    """
    _refuse_forged_label(label)
    if folds_a_tag_line(value):
        raise BagError(
            f"tag value for {label} does not survive a round trip through "
            f"`read_tag_file`: {value!r}. A value carrying anything "
            f"`str.splitlines()` breaks on folds into what reads as a second "
            f"label, and one carrying surrounding whitespace reads back stripped "
            f"— a different string from the one written. Free text is refused "
            f"here rather than sanitised, so the caller's mistake is visible "
            f"where it is made.\n"
            f"  the check asks `str.splitlines()` rather than listing line "
            f"terminators: the list this replaced named `\\n` and `\\r`, and "
            f"EIGHT more characters that method breaks on went through it.")


def _write_tag_file(path: Path, lines: list[str]) -> None:
    """Write a tag file at `FILE_MODE`, with the mode set at creation.

    Same discipline as the root's directory mode: an `open()` followed by a
    `chmod` leaves a window in which a world-readable file holding transcript
    metadata exists on a multi-user host.

    `O_NOFOLLOW` BECAUSE NOTHING THIS MODULE WRITES IS EVER LEGITIMATELY A
    SYMLINK. A tag file and a redaction marker both belong to the bag; if the
    path is a link, the bytes would land in a file the bag does not own. The
    callers already refuse symlinked targets — this closes the window between
    that check and this write rather than trusting it.
    """
    body = "".join(line if line.endswith("\n") else line + "\n" for line in lines)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, FILE_MODE)
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
    _refuse_folded_value(label, value)
    # `O_NOFOLLOW` FOR THE SAME REASON `_write_tag_file` CARRIES IT — nothing
    # this module writes is ever legitimately a symlink. This site appends to a
    # file that function created, so the MODE is already right; only the follow
    # was open. Found by a correction pass sweeping the class after
    # `record_citation` was caught creating a file with neither rule, and fixed
    # here rather than reported, because a sweep that names a second member and
    # leaves it is not a sweep.
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW,
                 FILE_MODE)
    with os.fdopen(fd, "a", encoding="utf-8") as handle:
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

    ⚠ IT DOES NOT UNDERSTAND CONTINUATION LINES. The scan is line-by-line, so a
    folded value's continuation is preserved verbatim as an unrelated line rather
    than replaced with its label. Harmless for every label this is called with —
    `Payload-Oxum`, `Bagging-Date` and `Journal-Sealed-At` are all short
    single-token values that cannot fold — and stated so a future caller does not
    reach for it with a free-text label whose value could.
    """
    _refuse_folded_value(label, value)
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


@dataclass(frozen=True)
class BagState:
    """The three fields requirement 8 says are reported TOGETHER, always.

    `lifecycle` is `open` or `sealed` — one field with two values. `redacted` and
    `incomplete` are INDEPENDENT flags on top of it, because a redaction only
    applies to a bag that was sealed and `incomplete` can accompany either. A
    single collapsed label would make a bag that lost data to a full disk
    indistinguishable from one a human deliberately redacted.

    `redactions` and `gaps` carry the records behind the two flags, so a reader
    that wants "what was lost" does not have to walk the tag entries again with
    its own idea of which label means what — which is the duplication this type
    exists to end.

    `unreadable` is what the derivation could NOT honour: a lifecycle tag line
    whose value it does not understand. It exists so that "the flag is false"
    and "the flag could not be read" stop being the same answer — the same
    distinction the whole component draws between *no gap* and *a gap nobody
    recorded*. `validate_bag` turns each entry into a structural finding; a
    caller that ignores it is no worse off than before.
    """

    lifecycle: str
    redacted: bool
    incomplete: bool
    redactions: tuple[str, ...] = ()
    gaps: tuple[str, ...] = ()
    unreadable: tuple[str, ...] = ()


def lifecycle_of(manifest_exists: bool) -> str:
    """`sealed` once a manifest exists, `open` until then. Never a third value.

    THE ONE PLACE THE TWO LIFECYCLE STRINGS ARE PRODUCED. Trivial, and named
    anyway: `Bag.lifecycle` and `validate_bag` each derived it from
    `manifest-sha256.txt` existing, so "sealed" meant whatever two functions
    independently agreed it meant.
    """
    return "sealed" if manifest_exists else "open"


def bag_state(*, manifest_exists: bool,
              info_entries: Sequence[tuple[str, str]]) -> BagState:
    """THE ONE PLACE `bag-info.txt` labels become the three state fields.

    WHY THIS FUNCTION EXISTS, AS THE MEASUREMENT RATHER THAN AS A PRINCIPLE. The
    rule was typed twice — `Bag.redacted`/`Bag.incomplete` read the labels one
    way and `validate_bag` read them another, down to an independently retyped
    `.strip().lower() == "true"`. Both copies were correct on the day they were
    written, which is exactly why the defect is invisible in review: nothing is
    wrong until one of them is edited. **When they drift, `Bag.incomplete`
    disagrees with `BagReport.incomplete` about the same bag** — the state
    collapse requirement 8 exists to forbid, arriving by drift instead of by
    design, and arriving in the direction that matters: a bag that lost bytes
    reported as one a human redacted, or as neither.

    THE TRIGGER IS PHASE 3, WHICH IS WHY IT IS CLOSED NOW. Phase 3 adds emitters
    and with them the third reader, and a third hand-written copy is how a rule
    kept in prose gets a hole in it — this package has already paid that once,
    for containment (see `contained_relpath`).

    A VALUE IS `true` OR IT IS NOT THE FLAG. The comparison is deliberately
    strict-after-normalising: `bag-info.txt` is written by this module, which
    writes the literal `true`, so accepting `yes`/`1`/`on` would be inventing a
    dialect no writer produces. Case and surrounding space ARE forgiven, because
    a folded or hand-edited tag line is a realistic way for the same intent to
    arrive differently spelled.

    ⚠ ANY OTHER VALUE — `false`, `unknown`, a typo — LEAVES THE FLAG FALSE AND
    IS REPORTED IN `unreadable`, and the second half is what makes the first
    half safe. Guessing `true` would assert a gap that may not exist; guessing
    `false` silently would be this component's own worst outcome, an operator
    reading `incomplete: false` off a line the code could not parse. So the
    boolean stays honest and the line is surfaced, rather than one of the two
    being chosen. `Journal-Incomplete` is written only when a write has already
    failed, so an unparseable one means something is already wrong here.
    """
    redactions = tuple(value for label, value in info_entries
                       if label == LABEL_REDACTION)
    gaps = tuple(value for label, value in info_entries if label == LABEL_GAP)
    flags = [value for label, value in info_entries if label == LABEL_INCOMPLETE]
    incomplete = any(value.strip().lower() == "true" for value in flags)
    unreadable = tuple(f"{LABEL_INCOMPLETE}: {value}" for value in flags
                       if value.strip().lower() != "true")
    return BagState(lifecycle=lifecycle_of(manifest_exists),
                    redacted=bool(redactions), incomplete=incomplete,
                    redactions=redactions, gaps=gaps, unreadable=unreadable)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def payload_symlinks(bag_path: Path) -> list[Path]:
    """Every symlink under `data/`, sorted, as bag-relative paths.

    Reported separately rather than silently skipped, because a symlink in a
    payload is never benign here: a bag is meant to be a self-contained folder
    that transfers as a directory tree, and a link's target does not travel with
    it. The validator turns this into a structural finding.
    """
    payload = bag_path / PAYLOAD_DIR
    if not payload.is_dir():
        return []
    found = [p for p in payload.rglob("*") if p.is_symlink()]
    return sorted(p.relative_to(bag_path) for p in found)


def payload_files(bag_path: Path) -> list[Path]:
    """Every regular NON-SYMLINK file under `data/`, sorted, as bag-relative paths.

    Sorted so a manifest is byte-stable across regenerations — a manifest whose
    line order depended on directory iteration order would show a spurious diff
    on every reseal and make a real change hard to see.

    SYMLINKS ARE EXCLUDED, AND IT IS A CORRECTNESS RULE RATHER THAN A FILTER.
    `Path.is_file()` follows links, so a symlink under `data/` pointing at
    `~/.bashrc` would previously be hashed into the manifest as though it were
    payload — and `redact()` would then follow it and truncate the target. Two
    separate consequences, one cause: a bag must contain BYTES, not pointers to
    bytes that live outside it and do not travel with the directory tree.
    `payload_symlinks` reports them so the validator can say so out loud rather
    than leaving them silently uncovered.
    """
    payload = bag_path / PAYLOAD_DIR
    found = [p for p in payload.rglob("*") if p.is_file() and not p.is_symlink()]
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
        """`sealed` once a manifest exists, `open` until then. Never a third value.

        DELIBERATELY NOT ROUTED THROUGH `state`, which would read `bag-info.txt`.
        `open_bag` asks a bag its lifecycle while adopting one whose tag files a
        racing creator may not have written yet (see `open_bag`'s last warning),
        and `read_tag_file` raises on a file that is not there — so making the
        cheap question depend on the expensive one would turn a documented
        survivable race into a crash. The RULE still lives in one place.
        """
        return lifecycle_of(self.manifest_path.is_file())

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
        slug = safe_payload_segment(name)
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

    def _contained_payload_target(self, payload_relpath: str) -> Path:
        """`<bag>/<payload_relpath>`, proven to still be inside the payload dir.

        THE FIRST-SEGMENT CHECK IS NOT CONTAINMENT, AND TREATING IT AS ONE COST
        THIS MODULE TWO ESCAPES. `Path("data/../../x").parts[:1]` is `("data",)`,
        so a `..` walk passed the caller-facing guard and `self.path / relpath`
        landed outside the bag — and separately, a SYMLINK under `data/` passed
        `is_file()` (which follows links), so the write landed on the link's
        target. Both were demonstrated against a real bag, not reasoned about.

        This is the same containment technique `root.py` already applies one
        layer up — normalise, resolve, then prove the result is still inside the
        directory it is supposed to be inside — applied here because the input is
        the same class: a caller-supplied string composed onto a trusted path.

        EVERY SEGMENT IS CHECKED FOR A LINK, not only the leaf, because a
        symlinked intermediate directory relocates everything beneath it just as
        effectively as a symlinked file does.

        THE LEXICAL HALF IS NOW `contained_relpath`, SHARED WITH THE VALIDATOR.
        This function keeps the two halves the validator must not have: refusing
        a symlinked segment (the validator reports one instead) and the realpath
        re-check, which is defence in depth against a link planted between the
        lexical check and the write.
        """
        target = self.path / contained_relpath(payload_relpath)
        payload = self.payload_dir

        for segment in (target, *target.parents):
            if segment == self.path:
                break
            if segment.is_symlink():
                raise BagError(
                    f"cannot redact {payload_relpath}: {segment} is a symlink. A "
                    f"bag holds bytes, not pointers to bytes that live outside it "
                    f"— following one would write to a file this bag does not own.")

        resolved = Path(os.path.realpath(str(target)))
        payload_resolved = Path(os.path.realpath(str(payload)))
        if resolved != payload_resolved and payload_resolved not in resolved.parents:
            raise BagError(
                f"cannot redact {payload_relpath}: it resolves to {resolved}, "
                f"which is outside this bag's payload directory "
                f"({payload_resolved}). A relative segment that escapes the bag is "
                f"refused rather than normalised, because the caller asking for it "
                f"has a different bug than the one a rewrite would hide.")
        return target

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
        target = self._contained_payload_target(payload_relpath)
        if not target.is_file():
            raise BagError(
                f"cannot redact {payload_relpath}: no such payload file in "
                f"{self.path}. A redaction names a file that exists; naming one "
                f"that does not is either a typo or a bag that already lost it, "
                f"and those need different answers.")

        # COMPOSED AND VALIDATED BEFORE THE PAYLOAD IS TOUCHED, because the
        # refusal below is the one that fires on free text. Written the other way
        # round — marker first, tag line second — a `reason` that does not survive
        # `read_tag_file` left the payload REPLACED and no `Journal-Redaction`
        # record naming it, on the one sanctioned path for scrubbing a leaked
        # credential. The marker's own text asserts that such a record exists, so
        # the bag did not merely lose the tombstone: it asserted a false one.
        # `_refuse_folded_value` is idempotent and `_append_tag_line` calls it
        # again below — the rule still lives in exactly one place.
        tombstone = f"{utc_now()} {payload_relpath} — {reason.strip()}"
        _refuse_folded_value(LABEL_REDACTION, tombstone)

        _write_tag_file(target, [REDACTION_MARKER.rstrip("\n")])
        # `reason` IS STRIPPED, AND ONLY `reason` — the composed line still goes
        # through `_refuse_folded_value`, which refuses anything `str.splitlines()`
        # breaks on. Surrounding whitespace on a free-text reason carries no
        # meaning, and `read_tag_file` strips it back off on the way out, so
        # refusing the whole redaction over a trailing space would fail the ONE
        # sanctioned way to scrub a leaked credential — at the moment it is most
        # urgent — over a difference nobody could observe in the record. A run id
        # and a label are the opposite case and are refused rather than trimmed:
        # there the surrounding space is part of a name somebody chose.
        _append_tag_line(self.info_path, LABEL_REDACTION, tombstone)
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
        # COMPOSED AND VALIDATED BEFORE THE FLAG IS SET, for the reason `redact`
        # validates before it overwrites. The flag says "this bag is missing
        # something" and the gap record says WHAT; setting the flag first and then
        # refusing the record leaves a bag that reports a loss it cannot describe
        # — and the `BagError` propagates out of the handler that was recording a
        # lost write, masking the original failure with a second one.
        gap = f"{utc_now()} {what.strip()} — {why.strip()}"
        _refuse_folded_value(LABEL_GAP, gap)

        # Stripped for the reason `redact` strips its `reason` — and it matters
        # more here. This is the path that records a write having been LOST, so a
        # `BagError` raised out of it over a trailing space would destroy the gap
        # record while the run was already handling a failure, which is the exact
        # silent loss this component exists to prevent.
        if not self.incomplete:
            _append_tag_line(self.info_path, LABEL_INCOMPLETE, "true")
        _append_tag_line(self.info_path, LABEL_GAP, gap)
        if self.lifecycle == "sealed":
            self.seal()

    # --- flags ---------------------------------------------------------------

    @property
    def state(self) -> BagState:
        """All three state fields, from the one function that derives them.

        Reads `bag-info.txt` on every access rather than caching: a bag is a
        folder other processes write into, so a cached answer would be a
        statement about when this object was built rather than about the bag.
        """
        return bag_state(manifest_exists=self.manifest_path.is_file(),
                         info_entries=self.info())

    # ⚠ ONE FIELD PER READ. Each of these takes its own snapshot, so a caller
    # that wants a CONSISTENT triple must read `.state` once and destructure it
    # — reading two properties of a folder another process is writing into can
    # straddle a write. Harmless today (nothing emits until Phase 3) and stated
    # here because `BagState` promises the three fields "together" and these two
    # convenience properties are the one place that promise does not hold.
    @property
    def redacted(self) -> bool:
        return self.state.redacted

    @property
    def incomplete(self) -> bool:
        return self.state.incomplete


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

    ⚠ WHAT IDEMPOTENT DOES NOT MEAN HERE: creating a bag is three syscalls, not
    one, so a second caller that loses the `mkdir` race can observe the bag
    directory between its creation and its tag files being written, and will
    adopt a bag whose `bag-info.txt` does not exist yet. Sequential retry — the
    case Temporal actually produces — is fully safe, because the first attempt
    either finished or left a directory the second completes reading. A true
    simultaneous race is not, and closing it needs a lock or a
    create-then-rename, neither of which is worth building before anything writes
    into a bag. Named rather than papered over.

    ⚠ AND PHASE 9 IS WHAT MAKES THAT RACE REACHABLE, so the paragraph above is a
    LIVE gap rather than a historical note. Phase 9 r4 makes sharing one run id
    across concurrent invocations the DESIGNED CONTRACT: a person may dispatch
    two children with the same `--run-id` and no parent having opened the bag
    first, at which point both openers race here. It does not need Temporal —
    the nearer clock is Workflow Decomposition Phase 3, which has none in it.

    THE WRITE CASE IS WORSE THAN THE READ CASE. The loser of the `mkdir` race
    adopts, appends a tag line through `_append_tag_line` — mode `"a"`, which
    CREATES the file — and the winner's `_write_tag_file` then runs with
    `O_TRUNC`, destroying it. A `Journal-Redaction` or `Journal-Gap` record lost
    that way is precisely the silent loss this component exists to prevent.

    MUTUAL EXCLUSION IS PHASE 9 r7 AND IS DELIBERATELY NOT DELIVERED HERE. Its
    mechanism — a lock, a create-then-rename, or a compare-and-swap — is ruled
    with the identity design, in whichever carrier candidate `C-zhdm5gh1`
    resolves to; that carrier does not exist yet, so r7 cannot close and nothing
    in this module should read as though it had. What r3 delivers, and what
    `test_journal_bag.py` demonstrates, is the SEQUENTIAL property only.
    """
    # VALIDATED AGAINST THE STATED PERMITTED SET, not against a list of
    # separators (Phase 9 r6). What stood here refused `/`, `os.sep`, `.` and
    # `..` — and admitted a newline, which forges a lifecycle flag in the tag
    # file this function writes three lines below. `validated_run_id` is the one
    # place the permitted set is expressed; the sweep in
    # `tests/unit/test_journal_tag_lines.py` is what keeps a new caller-supplied
    # string from reaching a tag-line composer around it.
    run_id = validated_run_id(run_id)

    bag_path = root / run_id

    def _adopt() -> Bag:
        if not bag_path.is_dir():
            raise BagError(f"{bag_path} exists and is not a directory")
        existing = Bag(path=bag_path, run_id=run_id)
        if existing.lifecycle == "sealed":
            raise BagError(
                f"bag {run_id} is already SEALED at {bag_path}. Its manifest is a "
                f"statement about a finished run; re-opening it under the same "
                f"run_id would make that statement false with nothing recording "
                f"that it had been. Mint a new run_id.")
        return existing

    if bag_path.exists():
        return _adopt()

    # ⚠ CALLER METADATA IS VALIDATED BEFORE THE FIRST `mkdir`, AND THE ORDER IS
    # THE POINT. Validated after it — which is how this was written — a refused
    # `info` entry raised with `<root>/<run_id>/` and `bagit.txt` already on disk
    # and `bag-info.txt` never written. That directory is not merely litter: the
    # `bag_path.exists()` fast path above means every LATER open of the same
    # run id ADOPTS it, and an adopted bag with no `bag-info.txt` raises
    # `FileNotFoundError` from `.info()`, `.state`, `.redacted` and `.incomplete`
    # — so one refused label poisons that run id permanently. Nothing is created
    # until every caller-supplied value has been accepted.
    #
    # SAME SHAPE AS `redact` AND `mark_incomplete`, AND ALL THREE ARE SWEPT by
    # `tests/unit/test_a_refused_bag_mutation_CHANGES_NOTHING.py`. The review that
    # found this class named the other two; this one was found by asking the tree
    # which OTHER functions here mutate before they validate.
    entries = {
        "External-Identifier": run_id,
        LABEL_SCHEMA_VERSION: str(JOURNAL_SCHEMA_VERSION),
        "Bag-Software-Agent": "claude-dot-files journal (Persistent Memory Protocol Phase 1)",
    }

    # CALLER METADATA IS UNTRUSTED INPUT, and it is the only untrusted input on
    # this path. A caller cannot overwrite a label this module owns — the schema
    # version in particular, since a bag claiming the wrong version is a bag an
    # upcaster reads wrongly forever — and cannot set a LIFECYCLE label at
    # creation, because `redacted` and `incomplete` are facts about what happened
    # to a run and never something its opener declares.
    reserved = set(entries) | {LABEL_REDACTION, LABEL_INCOMPLETE, LABEL_GAP,
                               LABEL_SEALED_AT, "Payload-Oxum", "Bagging-Date"}
    for label, value in (info or {}).items():
        if label in reserved:
            raise BagError(
                f"cannot set {label!r} when opening a bag: it is written by this "
                f"module and a caller-supplied value would either contradict the "
                f"bag's own record or declare a lifecycle fact that has not "
                f"happened. Reserved: {', '.join(sorted(reserved))}.")
        _refuse_folded_value(label, str(value))
        entries[label] = value

    # CREATE BY WINNING OR LOSING A `mkdir`, NEVER BY CHECK-THEN-CREATE. The
    # `exists()` above is a fast path, not the guard: two concurrent calls for one
    # `run_id` — precisely the duplicate delivery Temporal §7.1 idempotency exists
    # for — both see it as False and race here. Without this catch the loser
    # crashed with `FileExistsError` instead of adopting the winner's bag, which
    # is the opposite of the idempotency this docstring promises. `writer_dir` and
    # `root._create_with_mode` already use this pattern; this was the one place
    # that did not.
    try:
        os.mkdir(str(bag_path), DIR_MODE)
    except FileExistsError:
        return _adopt()
    try:
        os.mkdir(str(bag_path / PAYLOAD_DIR), DIR_MODE)
    except FileExistsError:
        pass

    # EXACTLY TWO LINES. RFC 8493 §2.1.1 requires it, and requirement 6 turns on
    # it: anything else here makes the bag non-conforming, which is why the
    # schema version goes in bag-info.txt instead.
    _write_tag_file(bag_path / BAGIT_FILE, [
        f"BagIt-Version: {BAGIT_VERSION}",
        f"Tag-File-Character-Encoding: {TAG_FILE_ENCODING}",
    ])

    _write_tag_file(bag_path / BAG_INFO_FILE,
                    [f"{label}: {value}" for label, value in entries.items()])

    return Bag(path=bag_path, run_id=run_id)

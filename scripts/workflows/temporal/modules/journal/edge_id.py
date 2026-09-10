"""The machine's stable name, persisted, and independent of every credential.

REQUIREMENT 6, AND THE HALF OF IT THAT IS BUILDABLE IN THIS REPO TODAY. The
requirement was SPLIT at review because its two halves have different evidence
bars: a stable, persisted `edge_id` independent of any credential is buildable
here and closes on its own; the **key→id mapping** lives in the upstream
Django/Temporal pair, a system outside this repo with no edge API key in this
fleet's configuration to point at, so it can only be closed by assertion. That
half is deferred on the named trigger *"the upstream pair authenticates an
edge."* The no-key-in-events constraint rides on the buildable half, deliberately
— which is why `NO_CREDENTIAL_EPOCH` below is a real value rather than an absence.

⚠ AN API KEY IS A CREDENTIAL, NOT AN IDENTIFIER, AND THIS IS THE WHOLE POINT.
The upstream pair has to know every edge, and the API key already associated with
one is the natural carrier — it is how the edge authenticates today. But
credentials rotate, and **a journal keyed by API key orphans an edge's entire
history the day the key is rotated.** The key authenticates; it MAPS TO a stable
edge id that never rotates. One line of design now, an unrecoverable
data-modelling mess later.

THIS IS A BINDING RULE RATHER THAN THIS COMPONENT'S PREFERENCE. Temporal Standard
§7.5 *Identities are explicit, never derived* states it generally — wherever a
resource is located or targeted by an identity, the identity is an explicit
input, not a derivation — and `edge_id` is one instance of it.

⚠ AND `hash(api_key)` IS RULED OUT TWICE OVER, so nobody re-derives it as the
clever answer. It changes on rotation, which is the orphaning bug above; and a
stored hash of a live credential is an offline confirmation oracle. An event
carrying a key, or a value derived from one in a way that survives rotation, is a
defect and not a convenience. `_refuse_credential_derived` below is that rule as
code rather than as this paragraph.

WHAT THIS MODULE DOES NOT DECIDE — the SHAPE. Whether the identity is a UUID, a
host-scoped name, an operator-assigned label or something the orchestrator
already issues is a JOINT design with the Temporal Integration component, which
addresses workers, task queues and schedules and has its own reasons to name a
machine. That component names no machine or edge id today, so the question is
open on both sides and gets settled once rather than twice. **What this component
needs is three constraints and they are all it needs:** stable across credential
rotation, never derived from a key, present on every event. A generated UUID
satisfies all three and commits to nothing — `adopt_edge_id` below is the seam
where an operator-assigned or orchestrator-issued value replaces it with no
schema change and no orphaned history.

⚠ AND STABILITY IS NOT TRUSTWORTHINESS. These three constraints make an identity
DURABLE; they say nothing about whether it is trustworthy. `events.py` states the
other half: `edge_id` is SELF-REPORTED until an authenticating ingest exists, and
no amount of stability fixes that. Two separate properties; this file supplies
only the first.
"""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

__all__ = ["EDGE_ID_FILE", "NO_CREDENTIAL_EPOCH", "EdgeIdError",
           "resolve_edge_id", "adopt_edge_id", "read_edge_id",
           "EDGE_ID_PERMITTED"]

#: Where the id is persisted: at the journal root, beside the bags rather than
#: inside any of them. AT THE MACHINE, which is what requirement 6 says — a file
#: inside a bag would be per-run, and an id that changed per run is not an id.
#: The root is already resolved once per run, already proven writable and
#: correctly-moded by `root.py`, and already the one place this fleet keeps
#: per-machine state, so putting it anywhere else would introduce a second
#: machine-state location for one value.
EDGE_ID_FILE = "edge-id"

#: The `key_epoch` an edge with no credential carries. A VALUE, NOT AN ABSENCE,
#: and `JournalEvent` refuses an empty one so this cannot be skipped by accident.
#: Requirement 7(c) needs every event to answer *under which credential epoch was
#: this authored*, and "none" is a real answer for this fleet today — it
#: authenticates to no upstream pair. An empty string would be indistinguishable
#: from a field somebody forgot to fill, which is the state a replay scoped past
#: a leaked credential cannot act on.
NO_CREDENTIAL_EPOCH = "none"

#: `\A…\Z` and not `^…$`, for the reason `bag._RUN_ID_RE` states: `$` also
#: matches before a trailing newline, so an anchored-looking validator silently
#: accepts one. `test_journal_regex_anchors.py` fails on any `^`/`$` added
#: anywhere in this package.
EDGE_ID_PERMITTED = re.compile(r"\A[A-Za-z0-9._-]{1,128}\Z")

#: The three digest lengths a key-derived id would arrive as — md5, sha1,
#: sha256 rendered hex. COMPILED TO A CONSTANT rather than inlined at the call,
#: because `test_journal_regex_anchors.py` sweeps this package for `\A…\Z`
#: anchoring and can only see patterns it can find; an inline `re.fullmatch(r"…")`
#: is invisible to it. Anchoring is supplied by `fullmatch` here rather than by
#: the pattern, which is why the sweep has to be able to read it and rule.
_DIGEST_SHAPE_RE = re.compile(r"[0-9a-fA-F]{32}|[0-9a-fA-F]{40}|[0-9a-fA-F]{64}")

#: File mode for the id. Not a secret — it appears in every event — but the
#: journal root is `0700` and a `0644` file inside it would be the one
#: inconsistency a reader has to stop and think about.
_EDGE_ID_MODE = 0o600


class EdgeIdError(RuntimeError):
    """The edge id could not be read, created or adopted.

    `RuntimeError` so it joins the `except RuntimeError` clause every entrypoint
    already carries around its preconditions, exactly as `JournalRootError` and
    `BagError` do.
    """


def _refuse_credential_derived(value: str, *, source: str) -> None:
    """Refuse an id that looks like it was derived from a secret.

    ⚠ THIS IS A SHAPE CHECK AND IT CANNOT PROVE THE NEGATIVE — stated here rather
    than left for a reader to over-read. Nothing can look at a 64-character hex
    string and know whether it is `sha256(api_key)` or a random token; what this
    catches is the SHAPE somebody reaches for when they implement the ruled-out
    answer, which is a bare hex digest of a standard digest length. A determined
    caller can defeat it by base64-ing the same hash.

    So why have it at all: because the failure mode is not an attacker, it is a
    future implementer who reads *"the key maps to a stable id"*, reaches for
    `hashlib.sha256(key).hexdigest()` as the obvious mapping, and ships it. That
    person is stopped by an error that names the rule; they are not stopped by a
    paragraph in a docstring, and this component's own thesis — stated three
    times in the phase doc — is that a rule written only as prose has not once
    prevented the thing it forbids.

    WHAT IT DOES NOT LOOK AT: the id already persisted at this machine. This runs
    on ADOPTION, which is the moment a value arrives from outside; re-checking a
    value already written would make a machine whose id happens to be 64 hex
    characters unable to start, and the remedy for that is not available to the
    run that hits it.
    """
    if _DIGEST_SHAPE_RE.fullmatch(value):
        raise EdgeIdError(
            f"refusing an edge id from {source} that has the shape of a bare "
            f"digest ({len(value)} hex characters). Requirement 6 rules out a "
            f"key-derived id twice over: it changes on rotation, which orphans "
            f"this edge's entire history the day the key rotates, and a stored "
            f"hash of a live credential is an offline confirmation oracle.\n"
            f"  if this is genuinely a random token rather than a digest, "
            f"prefix or hyphenate it so it does not read as one — the shape is "
            f"what a later reader will judge it by.")


def _validate(value: str, *, source: str) -> str:
    """The id's own contract: non-empty, single-line, and safe in a path or a tag.

    THE SAME CHARACTER SET `validated_run_id` USES, and for one of the same
    reasons plus one more. It goes into `bag-info.txt` as a tag value, so
    anything `str.splitlines()` breaks on would fold the line into what reads as
    a second label — the forging class `bag.folds_a_tag_line` exists to close.
    And it goes into every event, where a value that reads back differently from
    the value written breaks the one property the journal has.
    """
    stripped = value.strip()
    if not stripped:
        raise EdgeIdError(
            f"the edge id from {source} is empty. Every event carries one "
            f"(requirement 6), and a field absent from version-1 events is "
            f"absent forever — so there is no recovering this later.\n"
            f"  an EMPTY FILE here means a previous run was killed between "
            f"creating it and writing it. The value cannot be guessed: every "
            f"event this machine has written carries the one that belongs in "
            f"it. Remedy: if this root holds bags, copy the `edge_id` from any "
            f"event in one into the file; if it holds none, delete the file and "
            f"the next run mints a new id.")
    if stripped != value:
        raise EdgeIdError(
            f"the edge id from {source} carries surrounding whitespace: "
            f"{value!r}. It is written into `bag-info.txt` as a tag value and "
            f"read back stripped, so it would be a DIFFERENT string from the "
            f"one written. Refused rather than trimmed: the space is part of a "
            f"name somebody chose, and choosing for them is how a machine gets "
            f"two ids.")
    if not EDGE_ID_PERMITTED.match(stripped):
        raise EdgeIdError(
            f"the edge id from {source} is not `[A-Za-z0-9._-]{{1,128}}`: "
            f"{value!r}. It appears in a tag line and in every event, so the "
            f"permitted set is the intersection of what survives both.")
    return stripped


def read_edge_id(root: Path) -> str | None:
    """The id persisted at this root, or `None` if this machine has none yet.

    `None` IS NOT AN ERROR AND IS NOT A DEFAULT. It means *not yet minted*, which
    is the true state of a machine on its first run, and it is the caller's to
    resolve — `resolve_edge_id` mints, and a read-only consumer (a validator, a
    Phase 6 sweep) wants to know the difference between "this edge has no id" and
    "I made one up". Returning a fresh UUID from a READ would give every such
    consumer a different answer for one machine.
    """
    path = root / EDGE_ID_FILE
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except UnicodeDecodeError as exc:
        # NAMED SEPARATELY BECAUSE `UnicodeDecodeError` IS A `ValueError`, not an
        # `OSError` — so an `except OSError` alone catches the failure everybody
        # thinks of and lets this one escape while LOOKING handled. This file is
        # written by this module and holds ASCII, so a non-UTF-8 byte in it means
        # a hand-edit or a corrupted filesystem, and neither is recoverable by
        # guessing an encoding: every event this machine ever wrote carries the
        # value that is supposed to be in here.
        raise EdgeIdError(
            f"the edge id at {path} is not valid UTF-8 ({exc.reason} at byte "
            f"{exc.start}). It was written by this module as ASCII, so this is a "
            f"hand-edit or a corrupted file — and it cannot be guessed, because "
            f"every event under this root carries the value it should hold.") from exc
    except OSError as exc:
        raise EdgeIdError(
            f"the edge id at {path} could not be read — {exc.strerror}. The "
            f"journal root is resolved and proven writable before this point, "
            f"so a failure here is the root becoming unusable mid-run, which is "
            f"requirement 4 case (d) and not a missing id.") from exc
    return _validate(raw.strip("\n"), source=str(path))


def resolve_edge_id(root: Path) -> str:
    """This machine's id, minted on first call and stable for every call after.

    MINTED AS A UUID4 WITH AN `edge-` PREFIX. The prefix is not decoration: it is
    what keeps a generated id from reading as the bare digest
    `_refuse_credential_derived` refuses, and it makes an id greppable in a
    journal full of other 32-character hex identities (`event_id` is one).

    CREATE-EXCLUSIVE, SO TWO CONCURRENT FIRST RUNS CANNOT MINT TWO IDS. `O_EXCL`
    means the loser of the race gets `FileExistsError` and re-reads the winner's
    value rather than overwriting it. This is the same failure this fleet already
    survives at `Bag.writer_dir` by letting `os.mkdir` win or lose — and it is
    reachable here for the same reason: a parent and its children can start
    within the same second on a machine that has never run before.

    ⚠ THE RE-READ CAN STILL FIND THE FILE EMPTY IF THE WINNER HAS CREATED IT AND
    NOT YET WRITTEN IT. That window is one `os.write` wide, and the answer is to
    REFUSE with a remedy rather than to loop: a retry loop would spin forever on
    the durable version of the same state — a previous run killed between create
    and write — which no run can clear. `read_edge_id` raises that refusal, and
    it is the same refusal either way because the two states are indistinguishable
    from here and have the same fix.
    """
    existing = read_edge_id(root)
    if existing is not None:
        return existing

    minted = f"edge-{uuid.uuid4().hex}"
    path = root / EDGE_ID_FILE
    try:
        fd = os.open(str(path),
                     os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     _EDGE_ID_MODE)
    except FileExistsError:
        # THE RACE'S LOSER RE-READS THE WINNER'S VALUE rather than overwriting
        # it. `read_edge_id` raises rather than returning `None` for a file that
        # exists and is empty — which is the one-`os.write`-wide window between
        # the winner's create and its write, and also the durable state a killed
        # run leaves. Its message names the remedy, so there is nothing to add
        # here; an `if raced is None` arm would be unreachable code carrying a
        # second copy of that message.
        return read_edge_id(root)  # type: ignore[return-value]
    except OSError as exc:
        raise EdgeIdError(
            f"the edge id could not be written at {path} — {exc.strerror}. The "
            f"root was proven writable before this point, so this is the root "
            f"becoming unusable (requirement 4 case (d)), not a permissions "
            f"misconfiguration.") from exc
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(minted + "\n")
    return minted


def adopt_edge_id(root: Path, value: str, *, source: str = "caller") -> str:
    """Take an id assigned from outside — the seam the joint design lands on.

    THIS IS WHERE AN OPERATOR-ASSIGNED LABEL OR AN ORCHESTRATOR-ISSUED NAME
    REPLACES THE MINTED UUID, and it exists now so that landing it later is a
    call rather than a migration. The Temporal Integration component has its own
    reasons to name a machine; whichever of the two is being built when the
    question comes up settles it, and the other cites it.

    ⚠ IT REFUSES TO REPLACE AN ID THIS MACHINE HAS ALREADY USED, and that refusal
    is the requirement rather than caution. Every event already written carries
    the old value; adopting a new one would split this machine's history into two
    edges that look like two machines, which is the exact orphaning failure the
    no-credential rule exists to prevent — arriving through the front door
    instead. Adopting the SAME value is a no-op and returns it, so a caller that
    passes the configured id on every run is correct and idempotent.
    """
    candidate = _validate(value, source=source)
    _refuse_credential_derived(candidate, source=source)

    existing = read_edge_id(root)
    if existing is not None and existing != candidate:
        raise EdgeIdError(
            f"this machine is already {existing!r} and cannot become "
            f"{candidate!r}. Every event under {root} carries the first value, "
            f"so adopting the second would split one machine's history into two "
            f"edges — the same orphaned-history failure a credential-derived id "
            f"causes, reached deliberately instead of by rotation.\n"
            f"  remedy: an edge that must be renamed is a migration over the "
            f"existing bags, not a write to this file.")
    if existing == candidate:
        return existing

    path = root / EDGE_ID_FILE
    try:
        fd = os.open(str(path),
                     os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     _EDGE_ID_MODE)
    except OSError as exc:
        raise EdgeIdError(
            f"the adopted edge id could not be written at {path} — "
            f"{exc.strerror}") from exc
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(candidate + "\n")
    return candidate

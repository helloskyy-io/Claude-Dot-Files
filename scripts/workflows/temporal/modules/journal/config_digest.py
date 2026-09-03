"""What configuration a run absorbed, as one digest over the installer's set.

WORKFLOW DECOMPOSITION PHASE 5, REQUIREMENTS 1-3. A dispatch reads its agents,
skills, rules and hooks from `~/.claude/` on the machine it runs on. Those are
symlinks into a repository, which is what makes them syncable and also what makes
them editable mid-flight: an interactive session adjusts a rule at 14:00 and every
dispatch after 14:00 behaves differently from every dispatch before it, with
nothing recording that it changed. This module computes the value that makes the
difference visible after the fact, and `journal_activities` writes it into the
run's bag beside the five facts already there.

WHAT THE DIGEST COVERS, STATED HERE AND RESTATED IN THE TAG ITSELF (requirement
2). It covers exactly the items `install.sh` symlinks into `~/.claude/` — the
`SYMLINK_TARGETS` array, READ from that file at digest time. For a file target
the bytes are hashed; for a directory target every regular file beneath it is
hashed, path-relative and sorted. Anything that is not a regular file — a FIFO,
a device node, a socket — is recorded by KIND and never opened, because opening
one can block forever and this runs before the run has a bag to say so in.

THE DECLARED POPULATION IS ITSELF PART OF THE DIGEST, not merely reported beside
it. Two installers declaring different sets over one tree must not produce the
same value, and they did while the manifest held only the targets' byte-effects:
a declared target that is present-and-empty contributes no line, so `{agents}`
and `{agents, plugins}` hashed identically and the reader answered SAME.

WHAT IT DELIBERATELY EXCLUDES, BY NAME. Everything else under `~/.claude/`, which
is machine-local state rather than absorbed configuration: `.credentials.json`,
`projects/`, `history.jsonl`, `sessions/`, `cache/`, `backups/`, `downloads/`,
`file-history/`, `ide/`, `plans/`, `plugins/`, `session-env/`,
`shell-snapshots/` and `telemetry/`. That list is CLAUDE.md's own
"NOT synced (machine-local)" set. A digest over the whole tree changes on every
run and answers nothing; a digest over the synced set answers the question the
phase asks. The exclusion is expressed as a complement — *not in `targets=`* —
which is why the tag carries the population rather than only the hash.

⚠ THE POPULATION IS READ, NEVER COPIED, AND THAT IS THE WHOLE POINT. A
hand-copied list of seven is a hand-kept population: it cannot see the target
that was added to `install.sh` and never added here, so the digest would answer
confidently about a set nobody syncs. Two open candidates propose changing that
set — `C-idwrru3n` (per-file granularity in the installer's targets) and
`C-7ymfdw28` (point the symlinks at a pinned worktree), constrained to be ruled
together — so this is a live path rather than a hypothetical one. If the parse
below ever becomes awkward, that awkwardness is a finding about where the set is
declared; it is not a licence to copy it.

FAILING TO ESTABLISH THE POPULATION IS RECORDED, NOT GUESSED AND NOT FATAL. When
`install.sh` is absent, unparseable, or declares an empty array, this module
raises `ConfigDigestError` and the caller records `unavailable reason=<slug>` in
the tag. It does not fall back to a default set: a digest over a guessed
population is the confidently-wrong answer this whole component exists to
prevent. It does not stop the run either — the population being unestablishable
is a fact about the machine, not a reason a dispatch may not proceed, and the bag
records it so a later reader is told rather than left to infer from a missing
tag.

WHERE THE TREE IS, VERSUS WHAT IS IN IT. `install.sh` declares WHICH items are
linked; it hardcodes `$HOME/.claude` as WHERE. The Claude Code CLI honours
`CLAUDE_CONFIG_DIR`, so a run with that variable set absorbs a different tree
than the one the installer wrote to. This module honours it for the same reason
the population is read rather than copied: the tag claims to name what the run
absorbed, and recording the installer's directory when the CLI read another one
would be the confidently-wrong shape again. The two sources answer different
questions and neither is inferred from the other.

NO DECISION IS MADE FROM THIS VALUE, HERE OR ANYWHERE (the phase's own boundary).
The digest answers *were these the same*, never *which one was right*. Which
configuration should have been in force is a policy question, and the tier design
that would answer it is the successor tracked at `C-mq7v3z8k`.
"""

from __future__ import annotations

import hashlib
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path

# ONE CHUNKED SHA-256 IN THIS PACKAGE, NOT TWO. `bag.sha256_of` is byte-for-byte
# the loop this module had its own copy of, and `bag.py` imports nothing from
# this package, so the dependency runs one way only.
from .bag import sha256_of

__all__ = ["ConfigDigestError", "ConfigTreeError", "ConfigDigest",
           "DIGEST_ALGORITHM", "FIELD_ORDER",
           "LABEL_CONFIG_DIGEST", "UNAVAILABLE", "claude_config_dir",
           "config_digest", "installer_targets", "parse_symlink_targets",
           "parse_tag_value", "unavailable_tag_value"]

DIGEST_ALGORITHM = "sha256"
LABEL_CONFIG_DIGEST = "Journal-Config-Digest"

#: The tag's list-valued fields, in the order they are composed and rendered.
#: DECLARED ONCE AND IMPORTED BY THE READER, because the writer and the operator
#: tool spelled these three names independently: `ConfigDigest.tag_value` built
#: them into an f-string and `compare_run_config._render` iterated its own
#: literal tuple. `parse_tag_value` is generic over `key=value`, so nothing
#: related the two — a fourth field added to the tag would simply never appear in
#: the only tool an operator reads it with, and no test would say so. That is a
#: silent loss of a fact the tag went to some trouble to record.
FIELD_ORDER = ("targets", "absent", "unreadable")

#: What a field with nothing to say records. The bag's contract is that a value
#: is written once and never edited, and that a field with nothing to say says so
#: rather than being omitted — `Journal-Origin-Remote` already writes `-` on a
#: repo with no origin. This is that convention with a machine-readable reason
#: attached, because "the population could not be established" and "the tree was
#: empty" are different facts and a bare `-` collapses them.
UNAVAILABLE = "unavailable"

#: The sentinel for an empty list inside the tag value. A literal empty
#: `absent=` would be ambiguous with a truncated line. NOT named `NONE`: it is a
#: serialized string, and `else NONE` / `else None` look alike while composing
#: differently, so a one-character slip would produce plausible wrong output.
EMPTY = "none"

# `SYMLINK_TARGETS=(` … `)` in install.sh. The `^` anchor here is a LINE anchor
# under `re.MULTILINE` and is declared as such in `test_journal_regex_anchors.py`:
# it exists so a mention of the name inside a comment or a
# `"${SYMLINK_TARGETS[@]}"` expansion cannot be mistaken for the declaration, and
# `\A` would defeat that by anchoring to the start of the whole file instead.
#
# ⚠ THE CLOSING PAREN IS NOT LINE-ANCHORED, AND ANCHORING IT REFUSED A LEGAL
# INSTALLER. This pattern used to end at `^\)`, which requires the array to span
# several physical lines with the paren first on a line of its own. So
# `SYMLINK_TARGETS=(agents rules)` — the one-line form quoted immediately below as
# the very thing the bare-word branch exists to support — matched NOTHING, and the
# whole component degraded to `unavailable` against an installer declaring its set
# in plain view. `[^)]*` ends at the first `)` instead, which admits the inline
# form, the indented-paren form and the original multi-line form alike. A `)`
# inside an entry would truncate the body, but `)` is outside `_SEGMENT_RE`'s
# allowlist, so such an entry is refused BY NAME below rather than dropped quietly.
_ARRAY_RE = re.compile(r"^SYMLINK_TARGETS=\(([^)]*)\)", re.MULTILINE)

# `SYMLINK_TARGETS+=(` … `)`, which this module REFUSES rather than reads.
#
# ⚠ IT USED TO BE INVISIBLE, AND THAT IS THE ONE FAILURE THIS COMPONENT MAY NOT
# HAVE. `_ARRAY_RE` matches `SYMLINK_TARGETS=(`; an append block begins
# `SYMLINK_TARGETS+=(`, so a platform-conditional continuation was not matched, not
# reported and not included. The parse returned the FIRST block's entries alone and
# the digest was then computed — confidently — over a population missing everything
# the installer appended, with nothing going red: no exception, no `unavailable`,
# no hole recorded in the tag. That is exactly the confidently-wrong answer the
# read-never-copy design exists to rule out, reached from the other direction.
# REFUSED rather than concatenated: supporting `+=` would GENERALISE the grammar
# this module reads, and "the population could not be established" is a fact it
# already knows how to record truthfully.
_APPEND_RE = re.compile(r"^SYMLINK_TARGETS\+=\(", re.MULTILINE)

# QUOTED *AND* BARE ENTRIES, AND THE BARE HALF WAS MISSING. `SYMLINK_TARGETS=(
# agents hooks )` is legal, idiomatic bash and the installer's own array could be
# rewritten that way tomorrow. While this matched only quoted entries such an
# array yielded zero of them and was reported as *"declares SYMLINK_TARGETS as an
# EMPTY array"* — false when it declares seven, and a diagnostic that actively
# misdirects is worse than one that is merely unhelpful. `(` and `)` are excluded
# from the bare alternative so the array's own delimiters cannot become entries.
_ENTRY_RE = re.compile(r'"([^"\n]+)"|\'([^\'\n]+)\'|([^\s"\'()]+)')

# Anything bash would expand before the installer ever sees it as a name. A
# STATIC READ CANNOT RESOLVE THESE, and pretending otherwise would put a
# literal `$EXTRA` in the population. Refused with its own message rather
# than through the segment gate below, because the two facts have different
# remedies: one is a typo, the other is an installer this module cannot read.
_EXPANDS_RE = re.compile(r"[$`\\*?\[\]{}~!]")

# A target name is one path segment. The installer joins it onto `$CLAUDE_DIR`,
# so anything that escapes a segment would make the digest walk a tree the
# installer never links.
#
# ⚠ A LEADING DOT IS ALLOWED, AND REFUSING IT WAS A LIVE DEFECT RATHER THAN
# CAUTION. The stated purpose above is to refuse a value that ESCAPES a path
# segment; `.mcp.json` does not, and it is a real Claude Code config file and an
# obvious future entry in `SYMLINK_TARGETS`. While the class demanded a leading
# alphanumeric, adding it would have made `parse_symlink_targets` raise for the
# WHOLE array, `_config_digest_value` swallow that, and EVERY bag on EVERY
# machine record `unavailable` — with nothing going red. That inverts this
# module's central argument: reading the population is supposed to be what stops
# a newly-added target being missed.
#
# What genuinely escapes a segment is `.` and `..`, and those are refused by
# name. `none` is refused for a different reason and it is not a path rule: it is
# the `EMPTY` sentinel, so a target or a reason slug spelled `none` does not
# round-trip through `parse_tag_value` — the reader would decode a one-item list
# as the empty one. Both live here because this is the one gate every value
# composed into the tag passes through.
#
# `EMPTY` IS INTERPOLATED RATHER THAN RESPELLED. Two literals kept in agreement
# by a test is a test standing between two spellings; the f-string makes the
# drift impossible instead of detected. The anchors stay in the pattern's
# CONSTANT segments, which is what `test_journal_regex_anchors._literal_parts`
# reads — an expression that sweep cannot read is a finding there, not a skip.
#
# ⚠ `\A`/`\Z`, NEVER `^`/`$`, AND THIS ONE WAS A LIVE DEFECT RATHER THAN A
# STYLE POINT. `$` also matches BEFORE a trailing newline, so the anchored-
# looking `^…$` form accepted `"no-installer\n"` — and this same pattern gates
# `unavailable_tag_value`, whose output is composed straight into a
# `bag-info.txt` line. A reason ending in a newline would therefore have forged
# a second tag, which is exactly the lifecycle-flag forgery `bag._refuse_folded_value`
# exists to stop. Caught by `test_journal_regex_anchors.py`.
_SEGMENT_RE = re.compile(
    rf"\A(?!\.\.?\Z)(?!{re.escape(EMPTY)}\Z)[A-Za-z0-9.][A-Za-z0-9._-]*\Z")


class ConfigDigestError(RuntimeError):
    """The digest's population could not be established from the installer.

    A `RuntimeError` so it joins the class every entrypoint's precondition
    handler already prints, matching `JournalRootError` and `BagError`. Callers
    that want the run to continue catch it and record `unavailable`.
    """


class ConfigTreeError(ConfigDigestError):
    """WHERE the run's configuration tree is could not be established.

    A SEPARATE CLASS BECAUSE IT IS A SEPARATE FACT, and collapsing it was caught
    by a control rather than by review. The module docstring is explicit that
    `install.sh` answers *which items* while `CLAUDE_CONFIG_DIR`/`HOME` answer
    *which tree*, and that neither is inferred from the other — so a run that
    could not locate the tree recording `reason=installer-set-unreadable` sends
    an operator to a file that is perfectly fine. Different facts, different
    remedies, different slugs; the same split `absent` and `unreadable` already
    have one level down.

    It SUBCLASSES `ConfigDigestError` so every existing caller keeps its
    fail-soft behaviour unchanged: the run still proceeds, it just records the
    right thing.
    """


@dataclass(frozen=True)
class ConfigDigest:
    """One run's absorbed configuration: the value, its population, its holes.

    `targets` is the installer's set, sorted — the population the digest was
    computed over, carried so a reader can recompute it without this module.
    `absent` and `unreadable` are the subsets that contributed no bytes, kept
    APART because they are different facts: a target that was never installed and
    a target the run could not read are diagnosed differently, and collapsing
    them is the silent-degradation shape the fleet's rules forbid.
    """

    digest: str
    targets: tuple[str, ...]
    absent: tuple[str, ...]
    unreadable: tuple[str, ...]

    def tag_value(self) -> str:
        """The single tag line's value. Single-line by construction.

        The bag refuses a value containing a newline — it would forge a second
        tag — and every field here is either a hex digest or a path segment that
        `_SEGMENT_RE` has already proven has no newline in it. So this composes
        rather than escapes, and the guarantee is upstream where it can be
        checked once.
        """
        fields = {"targets": self.targets, "absent": self.absent,
                  "unreadable": self.unreadable}
        # Composed from FIELD_ORDER rather than from a second literal spelling,
        # so the reader's render and this line cannot drift apart silently.
        return " ".join([f"{DIGEST_ALGORITHM}:{self.digest}"]
                        + [f"{key}={_join(fields[key])}" for key in FIELD_ORDER])


def _join(items: tuple[str, ...]) -> str:
    return ",".join(items) if items else EMPTY


def unavailable_tag_value(reason: str) -> str:
    """The tag value for a run whose population could not be established.

    `reason` is a slug from a fixed set rather than free text, deliberately. A
    message composed from an exception string could carry a newline and forge a
    tag line; a slug from a closed vocabulary cannot, so the refusal in
    `bag._refuse_folded_value` is never the thing standing between this and a
    corrupted `bag-info.txt`.
    """
    if not _SEGMENT_RE.match(reason):
        raise ConfigDigestError(
            f"not a reason slug: {reason!r}. The tag value is composed, not "
            f"escaped, so this field takes a closed vocabulary rather than an "
            f"exception's text.")
    return f"{UNAVAILABLE} reason={reason}"


def parse_tag_value(value: str) -> tuple[str | None, dict[str, tuple[str, ...]]]:
    """`(digest, fields)` from a tag value, or `(None, …)` when unavailable.

    THE READER'S HALF OF REQUIREMENT 2, and the reason the population lives in
    the value at all: a bag written by an older build, on a machine this one has
    never seen, is parseable by anything holding this function. `digest` is
    `None` exactly when the run recorded that it had nothing to say.
    """
    head, _, rest = value.strip().partition(" ")
    fields: dict[str, tuple[str, ...]] = {}
    for token in rest.split():
        key, sep, raw = token.partition("=")
        if not sep:
            continue
        fields[key] = () if raw == EMPTY else tuple(raw.split(","))
    if head == UNAVAILABLE:
        return None, fields
    algorithm, sep, digest = head.partition(":")
    if not sep or algorithm != DIGEST_ALGORITHM:
        return None, fields
    return digest, fields


def parse_symlink_targets(text: str) -> list[str]:
    """The `SYMLINK_TARGETS` entries declared in `install.sh`'s source.

    SPLIT OUT FROM THE FILE READ so the parse is testable against a source string
    with no installer on disk, and so the sweep that proves this module holds no
    copied list has one function to point at.
    """
    if _APPEND_RE.search(text):
        raise ConfigDigestError(
            "install.sh appends to SYMLINK_TARGETS with `+=`, and this module "
            "reads the single `SYMLINK_TARGETS=( … )` declaration only. Reading "
            "the first block alone would digest a population missing every "
            "appended entry with nothing going red, so the population is "
            "recorded as unestablishable rather than guessed at.")
    match = _ARRAY_RE.search(text)
    if match is None:
        raise ConfigDigestError(
            "install.sh declares no SYMLINK_TARGETS=( … ) array. The digest's "
            "population is READ from the installer and is never defaulted, "
            "because a digest over a guessed set answers confidently about a "
            "set nobody syncs.")
    body = match.group(1)
    # Strip comments before extracting entries: a commented-out `# "plugins"`
    # inside the array is a target the installer does NOT link, and admitting it
    # would put a file in the population that no symlink puts in `~/.claude/`.
    lines = [line.split("#", 1)[0] for line in body.splitlines()]
    stripped = "\n".join(lines)
    entries = [m.group(1) or m.group(2) or m.group(3)
               for m in _ENTRY_RE.finditer(stripped)]
    if not entries:
        # TWO DIFFERENT FACTS, AND THEY USED TO SHARE ONE MESSAGE. "The array is
        # empty" and "the array has content this parser could not read" have
        # different remedies, and reporting the second as the first tells an
        # operator their installer declares nothing when it declares seven
        # things. Same silent-degradation shape the `absent`/`unreadable` split
        # exists to refuse, one function over.
        if stripped.strip():
            raise ConfigDigestError(
                f"install.sh declares SYMLINK_TARGETS with no entries this "
                f"parser could read: {stripped.strip()!r}. The population is "
                f"read from the installer and never guessed, so an array whose "
                f"contents cannot be extracted is recorded as unavailable "
                f"rather than treated as empty.")
        raise ConfigDigestError(
            "install.sh declares SYMLINK_TARGETS as an EMPTY array. An empty "
            "population is refused rather than digested: the hash of nothing is "
            "a real value, and writing it would claim a run absorbed no "
            "configuration when what actually happened is that the installer "
            "could not be read for its set.")
    for entry in entries:
        if entry == EMPTY:
            # A DIFFERENT RULE FROM THE ONE BELOW, SO IT GETS A DIFFERENT
            # SENTENCE. `_SEGMENT_RE` refuses this too, but telling an operator
            # that `none` "is not a single path segment" is false and would send
            # them looking for a slash. It is refused because it is the tag's
            # own empty-list sentinel.
            raise ConfigDigestError(
                f"SYMLINK_TARGETS entry collides with the tag's empty-list "
                f"sentinel: {entry!r}. `{EMPTY}` is what a field with nothing in "
                f"it records, so a target of that name would be read back by "
                f"`parse_tag_value` as a population of zero targets rather than "
                f"of one.")
        if _EXPANDS_RE.search(entry):
            # ⚠ AN ARRAY BASH COMPUTES AT RUNTIME CANNOT BE READ STATICALLY, AND
            # SAYING THAT IS A DIFFERENT FACT FROM "THIS IS NOT A PATH SEGMENT".
            # `SYMLINK_TARGETS=( $EXTRA )` is legal bash; the bare-word
            # alternative above extracts `$EXTRA` verbatim, which is not what the
            # installer links. Refusing the whole array is correct — the
            # population is READ and never guessed — but the segment message sent
            # the reader looking for a slash. The suite's independent bash-oracle
            # check catches this if it ever reaches the real installer; this is
            # what an operator sees if it does not.
            raise ConfigDigestError(
                f"SYMLINK_TARGETS entry is computed by the shell rather than "
                f"literal: {entry!r}. The population is read from the "
                f"installer's source and never expanded, so an array whose "
                f"contents depend on the environment is recorded as unavailable "
                f"rather than digested against a value this parser guessed at.")
        if not _SEGMENT_RE.match(entry):
            raise ConfigDigestError(
                f"SYMLINK_TARGETS entry is not a single path segment: {entry!r}. "
                f"The installer joins each entry onto $CLAUDE_DIR, so a value "
                f"that escapes a segment would walk a tree the installer never "
                f"links.")
    return sorted(set(entries))


def installer_targets(install_sh: Path) -> list[str]:
    """`SYMLINK_TARGETS` read off the installer at `install_sh`."""
    try:
        text = install_sh.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigDigestError(
            f"install.sh could not be read: {install_sh} — {exc.strerror}. The "
            f"digest's population comes from the installer and from nothing "
            f"else, so this is recorded as unavailable rather than guessed."
        ) from exc
    except UnicodeDecodeError as exc:
        # ⚠ NOT AN `OSError`, WHICH IS WHY IT NEEDS ITS OWN CLAUSE. It is a
        # `ValueError`, so the clause above never saw it and it escaped this
        # module entirely — past `_config_digest_value`'s `except
        # ConfigDigestError` and out of `open_run_bag`, which means one bad byte
        # in `install.sh` stopped EVERY dispatch on the machine before any of
        # them could open a bag. The design says an unestablishable population
        # is one unknown fact and never a reason a run may not proceed; this
        # clause is what makes that true rather than merely stated.
        raise ConfigDigestError(
            f"install.sh is not valid UTF-8: {install_sh} — {exc.reason} at "
            f"byte {exc.start}. The population cannot be read from a file that "
            f"cannot be decoded, and it is never guessed, so this is recorded "
            f"as unavailable."
        ) from exc
    return parse_symlink_targets(text)


def claude_config_dir(env: dict[str, str] | None = None) -> Path:
    """The tree a run actually absorbed: `$CLAUDE_CONFIG_DIR`, else `~/.claude`.

    See the module docstring — the installer answers *which items*, this answers
    *which tree*, and inferring either from the other is how a tag ends up
    naming a directory the run never read.
    """
    environ = os.environ if env is None else env
    override = environ.get("CLAUDE_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    home = environ.get("HOME")
    if home:
        return Path(home) / ".claude"
    try:
        return Path.home() / ".claude"
    except RuntimeError as exc:
        # ⚠ `Path.home()` RAISES A **BARE** `RuntimeError`, AND
        # `ConfigDigestError` SUBCLASSES `RuntimeError` — SO THE CALLER'S
        # `except ConfigDigestError` DOES NOT CATCH ITS OWN PARENT. With `HOME`
        # unset and the uid absent from `/etc/passwd` (an ordinary container
        # shape), that bare error escaped this module, escaped
        # `_config_digest_value`, and refused the dispatch with a five-word
        # message and no remedy — for a condition this module's contract says is
        # one unknown fact and never a reason a run may not proceed. Re-raised as
        # `ConfigDigestError` so it takes the `unavailable reason=` path with
        # everything else that cannot establish the population.
        raise ConfigTreeError(
            f"the tree a run absorbs could not be located: neither "
            f"CLAUDE_CONFIG_DIR nor HOME is set and the account has no home "
            f"directory — {exc}. Which tree was read is not guessed, so this "
            f"run records that it could not be established."
        ) from exc



def _lines_for_target(root: Path, target: str) -> tuple[list[str], str | None]:
    """Manifest lines for one target, and its status when it contributed none.

    Returns `(lines, status)` where `status` is `"absent"`, `"unreadable"` or
    `None`. A target that exists and is simply empty returns no lines and no
    status — it is present, it contributed nothing, and that is neither of the
    two holes the tag reports.

    `"unreadable"` means AT LEAST ONE file OR DIRECTORY under the target could
    not be read, not that all of them failed. A directory with one unreadable
    file has a hole in its digest, and reporting it only when every file failed
    would let the common case — one root-owned file in an otherwise readable
    tree — pass as clean.
    """
    path = root / target
    try:
        if not path.exists():
            return [], "absent"
        if path.is_file():
            return [f"{target}\0{sha256_of(path)}"], None
    except OSError:
        # A line, not an empty list: a target we could not even stat must still
        # change the digest, or a machine that hides `hooks/` behind a
        # permission wall hashes identically to one that never had it.
        return [f"{target}\0unreadable"], "unreadable"

    lines: list[str] = []
    unreadable = False
    unlistable: list[str] = []

    def _record_unlistable(exc: OSError) -> None:
        """A directory that could not be LISTED is a hole, never a silence.

        ⚠ THIS WAS `onerror=lambda _e: None` AND IT WAS A LIVE DEFECT, not a
        style point. `os.walk` reports a directory it cannot open through this
        callback and then yields NOTHING for it, so discarding the error made a
        permission-walled directory contribute exactly what an empty one
        contributes. Measured before the fix: a tree whose `agents/private/`
        held two files at mode 000 hashed IDENTICALLY to a tree with no
        `agents/private/` at all, and `unreadable=` reported none — which is the
        very case the docstring three frames up promises to tell apart, one
        level below where it was being handled.

        `exc.filename` is made tree-relative below so the manifest line is the
        same on two machines whose journal roots differ. A failure with no
        filename at all still records the target, because contributing nothing
        is the one thing this callback exists to stop.
        """
        unlistable.append(getattr(exc, "filename", None) or str(path))

    # `followlinks=False`: the TARGET itself is a symlink into the repo and
    # `os.walk` follows it as the starting point regardless, which is what we
    # want. A symlink NESTED inside it is a different matter — following those
    # admits a cycle, and a digest that hangs is worse than one that is coarse.
    # Nested symlinked directories are recorded by name below so their presence
    # is visible rather than silently dropped.
    for dirpath, dirnames, filenames in os.walk(path, followlinks=False,
                                                onerror=_record_unlistable):
        here = Path(dirpath)
        # NOT SORTED HERE, AND THAT IS DELIBERATE. The manifest is sorted once,
        # in `config_digest` below, and that single sort is the whole of the
        # order-independence property. Sorting again at each level looked like
        # belt-and-braces and was worse than useless: it put a `sorted(...)` on
        # the line a reader would mutate to test the property, where deleting it
        # changes nothing — which is precisely how a control ends up unable to
        # fail. One property, one place.
        skip: list[str] = []
        for name in dirnames:
            rel = (here / name).relative_to(path)
            try:
                linked = (here / name).is_symlink()
            except OSError:
                # ⚠ `is_symlink()` LSTATS, AND LSTAT NEEDS SEARCH PERMISSION ON
                # THE PARENT. A directory at mode 444 is LISTABLE — `os.scandir`
                # returns its children's names straight off `readdir`, and their
                # `d_type` says which are directories without any stat — so the
                # walk hands us a name whose `lstat` then raises EACCES. That
                # call sat outside every handler here, so the whole exception
                # left the module and `open_run_bag` re-raised it as
                # `JournalRootError`, blaming free space under the JOURNAL root
                # for a permission bit on the CONFIG tree. Mode 000 on the same
                # directory was handled correctly the whole time; the shape one
                # bit over was fatal.
                unreadable = True
                lines.append(f"{target}/{rel}\0unreadable")
                skip.append(name)
                continue
            if linked:
                lines.append(f"{target}/{rel}\0symlinked-dir")
                skip.append(name)
        dirnames[:] = [n for n in dirnames if n not in skip]
        for name in filenames:
            entry = here / name
            rel = entry.relative_to(path)
            try:
                mode = entry.stat().st_mode
            except OSError:
                unreadable = True
                lines.append(f"{target}/{rel}\0unreadable")
                continue
            if not stat.S_ISREG(mode):
                # ⚠ ONLY REGULAR FILES ARE OPENED, AND A PLAIN `open()` ON THE
                # ALTERNATIVE IS WHY. `os.walk` puts FIFOs, device nodes and
                # sockets into `filenames`, and `sha256_of` opens what it is
                # given — an `open()` on a FIFO with no writer BLOCKS FOREVER,
                # and this call runs before the bag exists, so the run parks
                # with no record of itself. That is the one failure the journal
                # cannot describe. Verified before this check existed: a FIFO
                # under a target took the whole digest to a `timeout 8` exit.
                #
                # It is recorded rather than skipped — the line changes the
                # digest, so a machine with a FIFO under `hooks/` is
                # distinguishable from one without. It is NOT counted in
                # `unreadable`: nothing failed to be read. `stat()` follows
                # links deliberately, so a symlink to a regular file is still
                # hashed (its bytes are what the run absorbed) while a symlink
                # to a FIFO is not opened.
                #
                # ⚠ NAMED RESIDUAL RISK — THIS CHECK IS TOCTOU AND IS NOT
                # CLOSED. The `stat()` above and `sha256_of`'s `open()` below
                # resolve the SAME PATH BY NAME at two different moments. An
                # entry replaced by a FIFO in that window is opened with a plain
                # `open()` and the dispatch parks forever — the same consequence
                # this check exists to prevent, reached through the gap between
                # the check and the act rather than through the missing check.
                # Named rather than closed because both structural remedies cost
                # more than the risk: hashing from an `O_NONBLOCK` descriptor
                # would put a SECOND chunked sha256 in this package, which this
                # file's import comment refuses by name, and changing
                # `bag.sha256_of`'s open semantics would alter a contract
                # `bag.manifest` and `validate.py` depend on — for a race that
                # needs write access to `~/.claude/` mid-walk. A config tree
                # rewritten underneath its own dispatch is a different problem
                # from the one this module solves. Stated so the next reader
                # inherits a known gap rather than an assumed guarantee.
                lines.append(
                    f"{target}/{rel}\0not-a-regular-file:{stat.filemode(mode)[0]}")
                continue
            try:
                lines.append(f"{target}/{rel}\0{sha256_of(entry)}")
            except OSError:
                unreadable = True
                lines.append(f"{target}/{rel}\0unreadable")

    for name in unlistable:
        unreadable = True
        try:
            rel = Path(name).relative_to(path)
        except ValueError:
            # A filename `os.walk` reported from outside the target — it should
            # not happen, and recording the target rather than dropping the
            # line is the same choice made everywhere else in this function.
            lines.append(f"{target}\0unlistable")
            continue
        lines.append(f"{target}\0unlistable" if str(rel) == "."
                     else f"{target}/{rel}\0unlistable")
    return lines, ("unreadable" if unreadable else None)


def config_digest(*, claude_dir: Path | None = None,
                  install_sh: Path) -> ConfigDigest:
    """The digest of the configuration a run on this machine absorbs.

    DETERMINISTIC AND ORDER-FREE. The manifest is sorted before hashing, so two
    machines that hold the same bytes under the same names produce the same
    value whatever order their filesystems enumerate in — which is the property
    the whole tag rests on, since a digest that varies by directory-read order
    would report every pair of runs as divergent.

    ABSENCE CHANGES THE DIGEST. A target that is not installed contributes the
    line `<target>\\0absent` rather than contributing nothing, so a machine
    missing `hooks/` is distinguishable from a machine whose `hooks/` is empty.
    Contributing nothing would have made those two hash identically, and they are
    the two cases an operator most needs told apart.
    """
    root = claude_config_dir() if claude_dir is None else claude_dir
    targets = installer_targets(install_sh)

    # ⚠ THE DIGEST COVERS ITS OWN DECLARED POPULATION, NOT ONLY THAT
    # POPULATION'S BYTE-EFFECTS — AND OMITTING THIS LINE WAS A LIVE DEFECT.
    # Every other line here is an effect of a target: bytes, an absence, a hole.
    # A target that is declared and happens to be PRESENT-AND-EMPTY produces no
    # line at all, so an installer declaring `{agents}` and one declaring
    # `{agents, plugins}` over the same tree hashed IDENTICALLY — and
    # `compare_run_config` then printed SAME and exited 0 while rendering the two
    # different `targets:` lists two lines below it. That is the confidently
    # wrong answer this component exists to remove, reproduced inside the reader
    # built to remove it. The population is what the tag claims to be about, so
    # it is hashed rather than merely reported beside the hash.
    #
    # `\0` LEADS THE LINE so it cannot collide with a target's own lines, which
    # are `<target>\0…` and whose target names `_SEGMENT_RE` has already proven
    # are non-empty. No migration is needed and none should be written: the tag
    # is introduced by the change that introduces this line, so no bag in
    # existence carries a digest computed without it.
    lines: list[str] = [f"\0targets\0{','.join(targets)}"]
    absent: list[str] = []
    unreadable: list[str] = []
    for target in targets:
        target_lines, status = _lines_for_target(root, target)
        if status == "absent":
            absent.append(target)
            lines.append(f"{target}\0absent")
            continue
        if status == "unreadable":
            # No extra target-level line: the per-file lines already carry
            # `\0unreadable` for each file that failed, and adding a second
            # record of the same fact would make the manifest's shape depend on
            # how the hole was reported rather than on what was read.
            unreadable.append(target)
        lines.extend(target_lines)

    manifest = "\n".join(sorted(lines)) + "\n"
    return ConfigDigest(
        # ⚠ `surrogateescape`, BECAUSE A FILENAME IS BYTES AND NOT TEXT. A file
        # whose name is not valid UTF-8 reaches this string as a lone surrogate
        # (that is how `os.fsdecode` represents the undecodable bytes), and a
        # plain `.encode("utf-8")` raises `UnicodeEncodeError` on it — a
        # `ValueError`, so it escaped `_config_digest_value`'s
        # `except ConfigDigestError`, escaped `open_run_bag`'s `except OSError`,
        # and stopped every dispatch on the machine with a raw traceback and no
        # bag. The manifest is only ever hashed and never decoded again, so
        # round-tripping the original bytes is both correct and stable: the same
        # filename produces the same digest on every machine that holds it.
        digest=hashlib.sha256(
            manifest.encode("utf-8", "surrogateescape")).hexdigest(),
        targets=tuple(targets),
        absent=tuple(sorted(absent)),
        unreadable=tuple(sorted(unreadable)),
    )

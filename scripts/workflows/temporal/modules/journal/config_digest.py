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
hashed, path-relative and sorted. The declared target SET is itself part of what
is hashed, so two runs whose installers declare different populations never
compare equal however similar the trees are. Anything beneath a target that is
not a regular file — a FIFO, a device node, a nested symlinked directory — is
recorded BY KIND rather than opened, because opening it is at best meaningless
and at worst a hang.

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

__all__ = ["ConfigDigestError", "ConfigDigest", "DIGEST_ALGORITHM",
           "LABEL_CONFIG_DIGEST", "UNAVAILABLE", "claude_config_dir",
           "config_digest", "installer_targets", "parse_symlink_targets",
           "parse_tag_value", "unavailable_tag_value"]

DIGEST_ALGORITHM = "sha256"
LABEL_CONFIG_DIGEST = "Journal-Config-Digest"

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

# `SYMLINK_TARGETS=(` … `)` in install.sh. The `^` anchors here are LINE anchors
# under `re.MULTILINE` and are declared as such in `test_journal_regex_anchors.py`:
# they exist so a mention of the name inside a comment or a
# `"${SYMLINK_TARGETS[@]}"` expansion cannot be mistaken for the declaration, and
# `\A` would defeat that by anchoring to the start of the whole file instead.
_ARRAY_RE = re.compile(r"^SYMLINK_TARGETS=\((.*?)^\)", re.MULTILINE | re.DOTALL)

# One array entry: double-quoted, single-quoted, or a BARE WORD.
#
# ⚠ THE BARE-WORD BRANCH IS A FIX, NOT A GENERALISATION. Without it this pattern
# matched only quoted entries, so an UNQUOTED bash array — legal, idiomatic, and
# what a maintainer writing `SYMLINK_TARGETS=(agents rules)` would produce —
# yielded zero entries and was reported as *"declares SYMLINK_TARGETS as an EMPTY
# array"*. That message is false when the array declares seven, and its own
# stated reasoning ("the installer could not be read for its set") does not apply
# to a set that is sitting right there. Admitting bare words makes the digest
# work for that installer instead of merely diagnosing it better, and anything a
# bare word admits that is NOT a target name — `$FOO`, `${OTHER[@]}` — is refused
# by `_SEGMENT_RE` below with a message that names the offending entry.
_ENTRY_RE = re.compile(r'"([^"\n]+)"|\'([^\'\n]+)\'|(\S+)')

# A target name is one path segment. The installer joins it onto `$CLAUDE_DIR`,
# so anything that escapes a segment would make the digest walk a tree the
# installer never links.
#
# ⚠ A LEADING DOT IS ALLOWED, AND FORBIDDING IT SILENTLY DISABLED THE WHOLE
# COMPONENT. This pattern used to demand a leading alphanumeric, though the only
# thing it is here to refuse is a value that ESCAPES a path segment — which `.`
# and `..` do and `.mcp.json` does not. `.mcp.json` is a real Claude Code config
# file and an obvious future entry in `SYMLINK_TARGETS`; adding it made
# `parse_symlink_targets` raise for the WHOLE array, `_config_digest_value`
# swallowed that into `unavailable`, and every bag on every machine recorded no
# digest with nothing going red. That inverts this module's central argument —
# that READING the population is what stops a newly-added target being missed.
# So the two escaping values are refused by name and the rest of the segment
# grammar is unchanged.
#
# ⚠ `\A`/`\Z`, NEVER `^`/`$`, AND THIS ONE WAS A LIVE DEFECT RATHER THAN A
# STYLE POINT. `$` also matches BEFORE a trailing newline, so the anchored-
# looking `^…$` form accepted `"no-installer\n"` — and this same pattern gates
# `unavailable_tag_value`, whose output is composed straight into a
# `bag-info.txt` line. A reason ending in a newline would therefore have forged
# a second tag, which is exactly the lifecycle-flag forgery `bag._refuse_folded_value`
# exists to stop. Caught by `test_journal_regex_anchors.py`.
_SEGMENT_RE = re.compile(r"\A(?!\.\.?\Z)[A-Za-z0-9.][A-Za-z0-9._-]*\Z")


class ConfigDigestError(RuntimeError):
    """The digest's population could not be established from the installer.

    A `RuntimeError` so it joins the class every entrypoint's precondition
    handler already prints, matching `JournalRootError` and `BagError`. Callers
    that want the run to continue catch it and record `unavailable`.
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
        return (f"{DIGEST_ALGORITHM}:{self.digest}"
                f" targets={_join(self.targets)}"
                f" absent={_join(self.absent)}"
                f" unreadable={_join(self.unreadable)}")


def _join(items: tuple[str, ...]) -> str:
    return ",".join(items) if items else EMPTY


def _refuse_reserved(value: str, what: str) -> None:
    """Refuse a value that collides with the tag's own empty-list sentinel.

    `EMPTY` is the string a field with no members serializes to, so a member
    literally named `none` does not round-trip: `parse_tag_value` reads
    `targets=none` back as the EMPTY TUPLE, and a reader would be told a run
    absorbed nothing when it absorbed one target called `none`. The collision is
    a property of the serialization, so it is refused at both places a value
    enters it rather than at one of them.
    """
    if value == EMPTY:
        raise ConfigDigestError(
            f"{what} may not be {EMPTY!r}: that is the sentinel this tag's "
            f"list fields use for 'no members', so the value does not survive "
            f"a round trip through `parse_tag_value` and would be read back as "
            f"an empty list.")


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
    _refuse_reserved(reason, "a reason slug")
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
    entries = [m.group(1) or m.group(2) or m.group(3)
               for m in _ENTRY_RE.finditer("\n".join(lines))]
    if not entries:
        raise ConfigDigestError(
            "install.sh declares SYMLINK_TARGETS as an EMPTY array. An empty "
            "population is refused rather than digested: the hash of nothing is "
            "a real value, and writing it would claim a run absorbed no "
            "configuration when what actually happened is that the installer "
            "could not be read for its set.")
    for entry in entries:
        if not _SEGMENT_RE.match(entry):
            raise ConfigDigestError(
                f"SYMLINK_TARGETS entry is not a single path segment: {entry!r}. "
                f"The installer joins each entry onto $CLAUDE_DIR, so a value "
                f"that escapes a segment would walk a tree the installer never "
                f"links.")
        _refuse_reserved(entry, "a SYMLINK_TARGETS entry")
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
    # ⚠ `Path.home()` RAISES A **BARE** `RuntimeError`, AND THAT IS WHY IT NEEDS
    # A WRAPPER RATHER THAN BEING LEFT ALONE. With `HOME` unset and the uid
    # absent from `/etc/passwd` — an ordinary container shape — `pwd.getpwuid`
    # fails and `Path.home()` raises `RuntimeError("Could not determine home
    # directory.")`. `ConfigDigestError` SUBCLASSES `RuntimeError`, so the
    # caller's `except ConfigDigestError` does not catch its own parent: the
    # five-word message escaped `open_run_bag` and refused the dispatch outright,
    # which is the one thing this module's contract says an unestablishable
    # population must never do. Re-raised as the module's own class so the
    # existing `unavailable reason=` path handles it like every other hole.
    try:
        return Path.home() / ".claude"
    except RuntimeError as exc:
        raise ConfigDigestError(
            f"the tree a run absorbs could not be located: neither "
            f"CLAUDE_CONFIG_DIR nor HOME is set and this uid has no home "
            f"directory on record — {exc}. The population is recorded as "
            f"unavailable rather than guessed at a path nobody read."
        ) from exc


def _file_status(entry: Path) -> str | None:
    """`None` when `entry`'s bytes may be hashed, else the token that stands in.

    ⚠ A FIFO UNDER A TARGET PARKED THE DISPATCH FOREVER, BEFORE IT HAD A BAG.
    `os.walk` sorts FIFOs, device nodes and sockets into `filenames`, and
    `sha256_of` opened them with a plain `open()` — which on a FIFO with no
    writer BLOCKS, with no timeout anywhere in the chain. Verified by execution:
    `timeout 8` on `config_digest()` over a tree holding one FIFO exited 124.
    The module docstring has always promised that *every REGULAR file* beneath a
    target is hashed; this is the check that makes the code say what the prose
    said. A time-based bound is deliberately NOT the remedy — it would make the
    digest depend on machine speed and destroy the cross-machine agreement the
    tag exists for. That question is separate and is tracked upstream.

    A SYMLINK TO A FILE IS STILL HASHED, and that asymmetry with `symlinked-dir`
    is the reviewed decision rather than an oversight. A symlinked DIRECTORY is
    not descended, so without a marker its whole subtree would vanish silently;
    a symlinked FILE is read, and its bytes ARE what the run absorbed. The
    `lstat` here is what stops the hang, not a change to that ruling — so a
    symlink is followed one hop with `stat()` and hashed only when what it points
    at is itself a regular file.

    `"unreadable"` rather than a kind token when the entry cannot be stat-ed at
    all, including a dangling symlink: nothing about it is knowable, which is a
    hole in the digest. A live non-regular entry is NOT a hole — it is recorded
    by kind so the digest still changes, but the run did not fail to read
    anything, so it does not set `unreadable=`. Same reasoning as `symlinked-dir`
    beside it.
    """
    try:
        mode = entry.lstat().st_mode
        if stat.S_ISLNK(mode):
            mode = entry.stat().st_mode
    except OSError:
        return "unreadable"
    return None if stat.S_ISREG(mode) else "not-a-regular-file"


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
        # ⚠ `is_symlink()` RE-RAISES `EACCES`, AND IT WAS CALLED TWICE OUTSIDE
        # ANY HANDLER. A directory at mode 444 is LISTABLE (read) but not
        # SEARCHABLE (no execute), so `os.walk` happily reports its children and
        # the `lstat` behind `Path.is_symlink()` on any of them raises
        # `PermissionError`. That escaped this module, was caught by
        # `open_run_bag`'s `except OSError`, and came back to the operator as
        # `JournalRootError` blaming free space under the JOURNAL ROOT — a false
        # diagnosis for a permission bit on a config tree. Mode 000 on the same
        # directory was handled correctly all along, via `_record_unlistable`;
        # the adjacent shape one bit over was fatal.
        #
        # One classification per name, in one place: the second `is_symlink()`
        # call that built `dirnames[:]` is gone, so a name cannot be recorded as
        # a link and then descended into (or vice versa) if the answer changes
        # between the two calls.
        #
        # ⚠ AND A SYMLINKED DIRECTORY IS NO LONGER PRUNED FROM `dirnames`, WHICH
        # IS A DELETION RATHER THAN AN OMISSION. `followlinks=False` above ALREADY
        # holds *do not descend into a nested link* — verified by execution, not
        # assumed — so the prune was a second copy of a property the walk itself
        # enforces. It was measured to carry nothing: mutating it away left the
        # test written for that property GREEN, which is the same defect as the
        # inner `sorted(filenames)` this function used to have. One property, one
        # place, and the mutation that tests it is now `followlinks`.
        #
        # The UNSTAT-ABLE branch below still prunes, and for an unrelated reason:
        # `os.walk` would try to descend into it, fail, and record it a SECOND
        # time through `_record_unlistable`, making the manifest's shape depend
        # on how a hole was reported rather than on what was read.
        unstatable: set[str] = set()
        for name in dirnames:
            rel = (here / name).relative_to(path)
            try:
                linked = (here / name).is_symlink()
            except OSError:
                # Not stat-able, so neither its kind nor its contents are
                # knowable. A line, not a silence — same choice as everywhere
                # else in this function.
                unreadable = True
                lines.append(f"{target}/{rel}\0unreadable")
                unstatable.add(name)
                continue
            if linked:
                lines.append(f"{target}/{rel}\0symlinked-dir")
        dirnames[:] = [n for n in dirnames if n not in unstatable]
        for name in filenames:
            entry = here / name
            rel = entry.relative_to(path)
            status = _file_status(entry)
            if status is None:
                try:
                    lines.append(f"{target}/{rel}\0{sha256_of(entry)}")
                except OSError:
                    unreadable = True
                    lines.append(f"{target}/{rel}\0unreadable")
                continue
            if status == "unreadable":
                unreadable = True
            lines.append(f"{target}/{rel}\0{status}")

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

    lines: list[str] = []
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

    # ⚠ THE DECLARED POPULATION IS PART OF THE MANIFEST, AND LEAVING IT OUT MADE
    # THE READER CONFIDENTLY WRONG. Every line above records a target's
    # BYTE-EFFECTS; none of them records the SET the digest was computed over. So
    # two installers declaring `{agents}` and `{agents, plugins}` over one tree,
    # with `plugins/` present and empty, produced the IDENTICAL digest — measured
    # — and `compare_run_config` printed SAME and exited 0 while rendering the two
    # different `targets:` lists two lines below it. That is the confidently-wrong
    # shape this whole component exists to remove, reproduced inside the reader
    # built to remove it, and it defeats requirement 2's reason for carrying the
    # population at all. The line leads with `\0` so it sorts ahead of every
    # target line, and no target name can contain `,` or `\0` because
    # `_SEGMENT_RE` has already refused both.
    #
    # NO MIGRATION, DELIBERATELY: the tag is introduced by the unmerged change
    # that also fixes this, so no bag in existence carries a digest computed the
    # old way and there is nothing to be compatible with.
    manifest = "\n".join(["\0targets\0" + ",".join(targets)] + sorted(lines)) + "\n"
    return ConfigDigest(
        # `surrogateescape`, and this was a live halt rather than a nicety. A
        # filename under a target that is not valid UTF-8 comes back from
        # `os.walk` carrying lone surrogates, which `str.encode("utf-8")` refuses
        # with `UnicodeEncodeError` — a `ValueError`, so it sailed past the
        # caller's `except ConfigDigestError` and out of `open_run_bag`, and the
        # run died with a raw traceback before it had a bag to record the death
        # in. The manifest is only ever hashed and never decoded, so encoding the
        # surrogates back to the original bytes is lossless and keeps the digest
        # stable across machines that see the same undecodable name.
        digest=hashlib.sha256(
            manifest.encode("utf-8", "surrogateescape")).hexdigest(),
        targets=tuple(targets),
        absent=tuple(sorted(absent)),
        unreadable=tuple(sorted(unreadable)),
    )

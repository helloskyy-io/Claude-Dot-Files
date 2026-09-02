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
hashed, path-relative and sorted.

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
from dataclasses import dataclass
from pathlib import Path

__all__ = ["ConfigDigestError", "ConfigDigest", "DIGEST_ALGORITHM",
           "LABEL_CONFIG_DIGEST", "UNAVAILABLE", "claude_config_dir",
           "config_digest", "installer_targets", "parse_symlink_targets",
           "parse_tag_value"]

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
#: `absent=` would be ambiguous with a truncated line.
NONE = "none"

# `SYMLINK_TARGETS=(` … `)` in install.sh. Anchored at line start so a mention of
# the name inside a comment or a `"${SYMLINK_TARGETS[@]}"` expansion cannot be
# mistaken for the declaration.
_ARRAY_RE = re.compile(r"^SYMLINK_TARGETS=\((.*?)^\)", re.MULTILINE | re.DOTALL)
_ENTRY_RE = re.compile(r'"([^"\n]+)"|\'([^\'\n]+)\'')

# A target name is one path segment. The installer joins it onto `$CLAUDE_DIR`,
# so anything that escapes a segment would make the digest walk a tree the
# installer never links.
_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


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
    return ",".join(items) if items else NONE


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
        fields[key] = () if raw == NONE else tuple(raw.split(","))
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
    entries = [m.group(1) or m.group(2)
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
    return (Path(home) if home else Path.home()) / ".claude"


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _lines_for_target(root: Path, target: str) -> tuple[list[str], str | None]:
    """Manifest lines for one target, and its status when it contributed none.

    Returns `(lines, status)` where `status` is `"absent"`, `"unreadable"` or
    `None`. A target that exists and is simply empty returns no lines and no
    status — it is present, it contributed nothing, and that is neither of the
    two holes the tag reports.

    `"unreadable"` means AT LEAST ONE file under the target could not be read,
    not that all of them failed. A directory with one unreadable file has a hole
    in its digest, and reporting it only when every file failed would let the
    common case — one root-owned file in an otherwise readable tree — pass as
    clean.
    """
    path = root / target
    try:
        if not path.exists():
            return [], "absent"
        if path.is_file():
            return [f"{target}\0{_hash_file(path)}"], None
    except OSError:
        # A line, not an empty list: a target we could not even stat must still
        # change the digest, or a machine that hides `hooks/` behind a
        # permission wall hashes identically to one that never had it.
        return [f"{target}\0unreadable"], "unreadable"

    lines: list[str] = []
    unreadable = False
    # `followlinks=False`: the TARGET itself is a symlink into the repo and
    # `os.walk` follows it as the starting point regardless, which is what we
    # want. A symlink NESTED inside it is a different matter — following those
    # admits a cycle, and a digest that hangs is worse than one that is coarse.
    # Nested symlinked directories are recorded by name below so their presence
    # is visible rather than silently dropped.
    for dirpath, dirnames, filenames in os.walk(path, followlinks=False,
                                                onerror=lambda _e: None):
        here = Path(dirpath)
        for name in sorted(dirnames):
            if (here / name).is_symlink():
                rel = (here / name).relative_to(path)
                lines.append(f"{target}/{rel}\0symlinked-dir")
        dirnames[:] = sorted(n for n in dirnames
                             if not (here / n).is_symlink())
        for name in sorted(filenames):
            entry = here / name
            rel = entry.relative_to(path)
            try:
                lines.append(f"{target}/{rel}\0{_hash_file(entry)}")
            except OSError:
                unreadable = True
                lines.append(f"{target}/{rel}\0unreadable")
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

    manifest = "\n".join(sorted(lines)) + "\n"
    return ConfigDigest(
        digest=hashlib.sha256(manifest.encode("utf-8")).hexdigest(),
        targets=tuple(targets),
        absent=tuple(sorted(absent)),
        unreadable=tuple(sorted(unreadable)),
    )

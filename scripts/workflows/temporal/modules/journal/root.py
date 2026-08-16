"""Where the journal lives, and the properties the directory must have.

THE ROOT IS A CONFIG VALUE (Phase 1 r1). Nothing here reads `$HOME` unless the
configured deployment shape is the one that is defined in terms of a home
directory, and that shape is a documented default rather than a fallback: an
unset root under a shape with no derivable default is a REFUSAL, not a guess.
The distinction is the whole requirement — a silent fallback to a home directory
is how the second edge (which may have no user account at all) would discover
its journal in the wrong place months later, with the records already written.

RESOLUTION FAILS THE RUN (Phase 1 r9). This is deliberately the earliest and
cheapest of the three write-failure cases the component rules on: the root is
resolved once, before a worktree is cut or a token is spent, so a missing path, a
read-only mount or a wrong-mode directory costs a second and a message. A run
that starts anyway and finds its journal unwritable an hour in has already spent
the hour, and the record of what it spent it on is the thing that cannot be
written.

`JournalRootError` SUBCLASSES `RuntimeError` ON PURPOSE. Every entrypoint in this
fleet already carries `except RuntimeError` around its preconditions and prints
the message the layer that knew what failed wrote. Subclassing means bag-open
joins that clause with no edit to the handler, and the message stays the
diagnostic — the same contract `preflight.py` holds one directory up.

WHAT THE MESSAGES MUST CARRY, and it is a requirement rather than a courtesy:
the resolved path and the exact failing property. Once the journal is mandatory,
a full or misconfigured root stops every run INCLUDING the one an operator would
use to diagnose it, so the refusal itself has to be the diagnosis.
"""

from __future__ import annotations

import os
import stat
from collections.abc import Mapping
from pathlib import Path

__all__ = ["JournalRootError", "DEPLOYMENT_SHAPES", "APP_DIR_NAME",
           "JOURNAL_DIR_NAME", "journal_config", "default_root_for",
           "resolve_journal_root"]

# The directory name under whichever state root the deployment shape supplies.
# Not the repo name and not `.claude` — this is state belonging to THIS fleet,
# and `.claude/` is Claude Code's own machine-local store which we deliberately
# do not key by (see the phase doc's § Key by `run_id`).
APP_DIR_NAME = "claude-dot-files"
JOURNAL_DIR_NAME = "journal"

# The three shapes the plan names. A fourth is a config change plus a row here,
# and an unrecognised value is refused rather than defaulted — a shape nobody
# chose would put verbatim transcripts somewhere nobody looked.
DEPLOYMENT_SHAPES = ("user", "systemd", "container")

# The root holds verbatim CLI transcripts, which include the literal input of
# every Bash call the fleet made. Two of the three deployment shapes are
# multi-user, so the mode is part of the contract rather than left to umask.
ROOT_MODE = 0o700

_MODE_BITS = 0o777


class JournalRootError(RuntimeError):
    """The journal root could not be resolved to a directory fit to write into.

    A `RuntimeError` so every entrypoint's existing precondition handler catches
    it unchanged; a distinct type so a caller that wants to tell a root problem
    from any other precondition failure can.
    """


def journal_config(config: Mapping[str, object] | None) -> tuple[str | None, str]:
    """`(root, deployment)` out of a loaded `config.yaml`, without defaulting root.

    Returns `None` for the root when the key is absent, null, or an empty string.
    All three spellings mean the same thing to an operator editing YAML and it
    would be a poor trap to have them mean different things here; what none of
    them means is "pick something sensible", which is `resolve_journal_root`'s
    job and is a documented default rather than a fallback.
    """
    section = (config or {}).get("journal") or {}
    if not isinstance(section, Mapping):
        raise JournalRootError(
            f"config.yaml `journal:` must be a mapping, not {type(section).__name__}. "
            f"Expected keys: `root:` (absolute path or empty) and "
            f"`deployment:` (one of {', '.join(DEPLOYMENT_SHAPES)}).")

    raw_root = section.get("root")
    root = str(raw_root).strip() if raw_root is not None else ""

    shape = str(section.get("deployment") or "user").strip()
    if shape not in DEPLOYMENT_SHAPES:
        raise JournalRootError(
            f"config.yaml `journal.deployment: {shape}` is not a known deployment "
            f"shape. Expected one of: {', '.join(DEPLOYMENT_SHAPES)}. Each shape "
            f"names a different documented default root; an unrecognised one has "
            f"no default and must not be guessed.")
    return (root or None), shape


def default_root_for(shape: str, env: Mapping[str, str]) -> Path:
    """The documented default root for one deployment shape, or a refusal.

    `user` follows the XDG Base Directory Specification, which defines
    `XDG_STATE_HOME` (default `~/.local/state`) for state that persists between
    restarts, explicitly including logs, and describes it as "analogous to
    /var/lib". That is precisely this journal, so the systemd shape uses
    `/var/lib` directly rather than inventing a second convention.

    `container` HAS NO DEFAULT AND SAYS SO. A container's persistent volume is
    wherever the operator mapped it; there is no path this code could derive
    that would not be a guess, and a guessed root inside a container's ephemeral
    layer is the failure mode where a journal silently evaporates on restart.
    Refusing is the honest answer and it names the one-line remedy.
    """
    if shape == "systemd":
        return Path("/var/lib") / APP_DIR_NAME / JOURNAL_DIR_NAME

    if shape == "container":
        raise JournalRootError(
            "journal.deployment: container has no derivable default root — a "
            "container's persistent volume is wherever it was mapped, and a "
            "guess would land the journal in the ephemeral layer where it "
            "disappears on restart. Set `journal.root:` in config.yaml to the "
            "mapped volume's path.")

    # shape == "user". XDG first; the home-derived path is XDG's OWN documented
    # default for that variable, which is what makes it a documented default
    # rather than the silent home-directory fallback r1 forbids.
    xdg = (env.get("XDG_STATE_HOME") or "").strip()
    if xdg:
        return Path(xdg) / APP_DIR_NAME / JOURNAL_DIR_NAME

    home = (env.get("HOME") or "").strip()
    if not home:
        raise JournalRootError(
            "journal.deployment: user, but neither XDG_STATE_HOME nor HOME is "
            "set, so the XDG default (~/.local/state) cannot be resolved. Set "
            "`journal.root:` in config.yaml to an absolute path. This refusal "
            "exists because the alternative — inventing a home directory — is "
            "how a journal ends up somewhere nobody reads.")
    return Path(home) / ".local" / "state" / APP_DIR_NAME / JOURNAL_DIR_NAME


def _refuse(path: Path, prop: str, remedy: str) -> JournalRootError:
    """Every refusal names the RESOLVED PATH and the EXACT failing property.

    Not a formatting nicety: once Phase 3 lands, this message is what an
    operator has instead of a working journal, so it carries both what was
    wrong and what to do about it.
    """
    return JournalRootError(
        f"journal root unusable: {path}\n  failing property: {prop}\n  remedy: {remedy}")


def _inside_a_git_working_tree(path: Path) -> Path | None:
    """The nearest ancestor of `path` (inclusive) that holds a `.git`, or None.

    WHY THIS IS A RESOLUTION RULE AND NOT ADVICE. The root is a config value and
    every build run this fleet dispatches edits repo config routinely, so a run
    can point the journal at its own worktree — at which point verbatim
    transcripts land somewhere that gets committed and pushed. Stating "it does
    not belong in the repo" as intent has no enforcement; refusing at resolution
    does.

    Checked by walking rather than by `git rev-parse`, because the root may not
    exist yet and `git` answers about the process's cwd, not about a path. `.git`
    is matched as either a directory (a checkout) or a file (a worktree's
    gitdir pointer) — a worktree is precisely the case that motivates this.
    """
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _create_with_mode(path: Path) -> None:
    """Create `path` and any missing ancestors, each at `ROOT_MODE` at creation.

    MODE AT CREATION, NEVER CHMOD-AFTER. A `mkdir` followed by a `chmod` leaves a
    window in which a world-readable directory holding transcripts exists on a
    multi-user host. `os.mkdir(path, mode)` sets the mode in the same syscall.

    ANCESTORS ARE WALKED RATHER THAN LEFT TO `os.makedirs`, which applies its
    `mode` argument only to the final component and creates intermediates with
    the process default. `<state>/claude-dot-files/journal` has an intermediate,
    and a 0755 `claude-dot-files/` around a 0700 `journal/` is not the contract.
    """
    missing = []
    probe = path
    while not probe.exists():
        missing.append(probe)
        if probe.parent == probe:
            break
        probe = probe.parent

    for directory in reversed(missing):
        try:
            os.mkdir(directory, ROOT_MODE)
        except FileExistsError:
            # Another run of this fleet won the race. Harmless: the loser adopts
            # the directory and the checks below verify it either way, which is
            # why they run against the resulting directory rather than against
            # our own creation of it.
            continue
        except OSError as exc:
            raise _refuse(
                directory, f"cannot be created ({exc.strerror})",
                "create it by hand with mode 0700, or set `journal.root:` in "
                "config.yaml to a path this user can create.") from exc


def resolve_journal_root(
        *,
        config: Mapping[str, object] | None = None,
        env: Mapping[str, str] | None = None,
        create: bool = True,
) -> Path:
    """The journal root, proven writable and correctly-moded, or a refusal.

    THE ORDER OF THE CHECKS IS OPERATOR-FACING BEHAVIOUR, same discipline as
    `preflight.resolve_operator_paths`: configuration errors before filesystem
    ones (they need no filesystem to fix), containment before permissions (a
    root in the wrong PLACE is a worse problem than one with the wrong mode, and
    fixing the mode of a path you should not be using wastes the operator's
    time).

    `create=False` EXISTS FOR CALLERS THAT WANT THE ANSWER WITHOUT THE SIDE
    EFFECT — a dry run, a diagnostic, a test. It is not a softer mode: every
    property below is still checked against whatever is on disk, and a
    non-existent root under `create=False` is refused rather than returned.
    """
    env = os.environ if env is None else env

    configured, shape = journal_config(config)
    candidate = Path(configured) if configured else default_root_for(shape, env)

    if not candidate.is_absolute():
        raise _refuse(
            candidate, "is not an absolute path",
            "set `journal.root:` in config.yaml to an absolute path — a "
            "relative root would resolve against whatever directory the run "
            "happened to be invoked from, which is the defect "
            "`preflight.resolve_repo_root` exists to prevent, one layer down.")

    # Lexical `..` collapse first, so the symlink comparison below compares two
    # normalised paths rather than reporting `/a/b/../b` as a symlink escape.
    candidate = Path(os.path.normpath(str(candidate)))

    real = Path(os.path.realpath(str(candidate)))
    if real != candidate:
        raise _refuse(
            candidate, f"resolves through a symlink to {real}",
            "point `journal.root:` at the real path. A symlinked root is "
            "refused because the target is what actually receives verbatim "
            "transcripts, and it is the target's location, ownership and mode "
            "that the rest of this contract would then be checking the wrong "
            "path for.")

    repo = _inside_a_git_working_tree(candidate)
    if repo is not None:
        raise _refuse(
            candidate, f"resolves inside the git working tree at {repo}",
            "set `journal.root:` to a path outside any repository. The journal "
            "is state, not source: inside a checkout it gets committed and "
            "pushed (verbatim transcripts and all), or gitignored — which hides "
            "it somewhere that is deleted along with the clone.")

    if create:
        _create_with_mode(candidate)

    if not candidate.is_dir():
        raise _refuse(
            candidate,
            "does not exist" if not candidate.exists() else "is not a directory",
            "create it with mode 0700, or set `journal.root:` in config.yaml.")

    info = candidate.stat()

    if info.st_uid != os.geteuid():
        raise _refuse(
            candidate, f"is owned by uid {info.st_uid}, not by this process (uid {os.geteuid()})",
            "chown it to the fleet user, or set `journal.root:` to a path this "
            "user owns. Ownership is part of the contract because the mode "
            "rules below only mean anything if this user is the owner they "
            "grant access to.")

    mode = stat.S_IMODE(info.st_mode)
    if mode != ROOT_MODE:
        # THE SPEC'S EXPLICIT REFUSAL IS THE WRITABLE HALF; THIS CHECKS THE WHOLE
        # MODE, and the difference is deliberate. The hazard the phase doc names
        # is READ access — "any local account reads every run" — and a 0755 root
        # is not group- or world-writable while being exactly that hazard. A
        # root that is not 0700 was not created under this contract, so it is
        # refused as a whole rather than sampled for two bits.
        offence = ("is group- or world-writable" if mode & 0o022
                   else "is group- or world-readable" if mode & 0o044
                   else "does not have the required owner access")
        raise _refuse(
            candidate, f"has mode {mode:04o}, not {ROOT_MODE:04o} — it {offence}",
            f"chmod {ROOT_MODE:o} it. The root holds verbatim CLI transcripts "
            f"including every Bash command line the fleet ran, and two of the "
            f"three deployment shapes are multi-user hosts.")

    if not os.access(candidate, os.W_OK | os.X_OK):
        raise _refuse(
            candidate, "is not writable by this process (read-only mount, or a full or immutable filesystem)",
            "make it writable, or set `journal.root:` to a writable path. This "
            "check is why the run stops here rather than an hour in, with the "
            "record of what it spent unwritable.")

    return candidate

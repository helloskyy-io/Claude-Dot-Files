#!/usr/bin/env python3
"""check_settings.py — validate config/settings.json.

CATCHES: a malformed settings.json, and a hook path that points at a file
which is not there. Nothing anywhere else parses this file as a check —
install.sh only symlinks it. It configures the permission model and the
hooks, so a broken one can mean the hooks never load at all, silently
removing the only control that operates during an autonomous run. The
hook-path assertion is worth more than the parse: install.sh symlinks
~/.claude/hooks -> config/hooks, so every "$HOME/.claude/hooks/x.sh" command
must resolve to an executable config/hooks/x.sh here. The zero-references
guard is the same principle as the master runner's "nothing ran at all"
exit: a check that silently verified nothing after a restructure looks
healthiest of all.

WHY IT TOKENISES INSTEAD OF SUBSTRING-MATCHING: a hook `command` is a shell
command line, not a path. Splitting on a literal "$HOME/..." prefix gets it
wrong in BOTH directions — a quoted "$HOME/.../x.sh" carries the closing
quote into the path and goes RED for a file that is fine, while a hook
written `~/.claude/hooks/x.sh` or `${HOME}/...` matches no prefix at all and
is silently skipped, which is the false green this whole file argues
against. shlex + expandvars/expanduser handles every spelling, and every
token that looks like a hooks/*.sh path is checked, so an `a.sh && b.sh`
command cannot hide its second half.

WHY `checked == total` RATHER THAN `checked > 0`: a bare non-zero guard only
catches the case where ALL hooks became unreadable. With two hooks and one
rewritten to an unrecognised form, `checked` is 1, the step would be green,
and one hook went unverified. Requiring every hook command to resolve
closes the partial case by construction — and it catches the half of
hook-scripts.md's "Always reference via $HOME/.claude/hooks/ (symlinked
path), never the source repo path" that actually breaks the deployment
model: a source-repo path now fails loudly instead of being quietly
ignored. Stated precisely, because the other half is NOT enforced —
`~/.claude/hooks/x.sh` expands to the same file and passes here, so this
does not police the spelling, only that every hook command reaches an
executable file under config/hooks/.

DOES NOT CATCH: whether the permission globs mean what their author
intended, or whether a hook does the right thing when it does load.

RELOCATED, NOT REWRITTEN. This carried the same algorithm inline in
`.github/workflows/tests.yml` — moved here so it is invoked by
`scripts/helpers/check-settings.sh` (locally runnable, matching
`lint-prompts.sh`'s shape) and so the eleven negative-control cases (NC-A
through NC-K) that proved this parse logic correct are a committed,
re-runnable pytest at `scripts/helpers/tests/unit/test_check_settings.py`
instead of prose in a PR body. Testing Standard § Mutation evidence: "a
guard ships with a demonstration that it fails when the property is
violated" — this was, until this move, the one guard in the repo whose
demonstration could not be committed or re-run.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

# Any token ending in a hooks/<name>.sh path, however $HOME is spelled.
HOOKISH = re.compile(r"(?:^|/)\.claude/hooks/([^/\s]+\.sh)$")
CANONICAL = "$HOME/.claude/hooks/"


class SettingsError(Exception):
    """Raised when config/settings.json fails validation."""


def load_settings(path: Path) -> dict:
    """Parse `path` as JSON, raising SettingsError (not json's own type) on failure."""
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SettingsError(f"not valid JSON ({exc})") from exc


def _hookish_tokens(cmd: str) -> list[str]:
    """Tokenise `cmd` and return every `.claude/hooks/<name>.sh` basename it names.

    Expands every spelling of $HOME to one canonical form, then tokenises so
    args, redirects and `&&` chains cannot corrupt the path the way a
    substring split does.
    """
    resolved = os.path.expanduser(os.path.expandvars(cmd.replace("${HOME}", "$HOME")))
    tokens = shlex.split(resolved)
    return [m.group(1) for m in (HOOKISH.search(t) for t in tokens) if m]


def validate(cfg: dict, hooks_dir: Path) -> str:
    """Validate `cfg`'s hooks block against `hooks_dir`.

    Returns the success message. Raises SettingsError, with every problem
    found accumulated into one message, on failure.
    """
    total, checked, bad = 0, 0, []
    for event, entries in cfg.get("hooks", {}).items():
        if not isinstance(entries, list):
            raise SettingsError(f"{event}: expected a list of hook entries, got {type(entries).__name__}")
        for entry in entries:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                total += 1
                try:
                    hits = _hookish_tokens(cmd)
                except ValueError as exc:
                    bad.append(f"{event}: {cmd!r} is not a parseable command line ({exc})")
                    continue
                if not hits:
                    bad.append(
                        f"{event}: {cmd!r} references no .claude/hooks/*.sh path — "
                        f"hook-scripts.md requires {CANONICAL}<name>.sh"
                    )
                    continue
                checked += 1
                for name in hits:
                    local = hooks_dir / name
                    if not local.is_file():
                        bad.append(f"{event}: {cmd} -> {local} does not exist")
                    elif not os.access(local, os.X_OK):
                        bad.append(f"{event}: {cmd} -> {local} is not executable")

    if not total:
        raise SettingsError("no hook commands found at all — this check verified nothing")
    if bad:
        raise SettingsError("; ".join(bad))
    if checked != total:
        # Defensive, not reachable today: every path above that skips the
        # `checked` increment also appends to `bad`, which raises first.
        # Kept as a guard against a future edit decoupling the two counters.
        raise SettingsError(f"only {checked} of {total} hook commands were resolvable — refusing to report clean")
    return f"valid JSON; all {checked} hook command(s) resolve to executable files in {hooks_dir}"


def main(argv: list[str]) -> int:
    settings_path = Path(argv[1]) if len(argv) > 1 else Path("config/settings.json")
    hooks_dir = Path(argv[2]) if len(argv) > 2 else Path("config/hooks")
    try:
        cfg = load_settings(settings_path)
        message = validate(cfg, hooks_dir)
    except SettingsError as exc:
        print(f"{settings_path}: {exc}", file=sys.stderr)
        return 1
    print(f"{settings_path}: {message}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

"""The managed floor declares the safety hook at a path the installer places.

WORKFLOW DECOMPOSITION PHASE 7. `config/managed-settings.d/claude-dot-files.json`
is placed by `install.sh` under `/etc/claude-code/` as a root-owned copy, where
Claude Code ranks it above every user, project and CLI setting. It declares the
fleet's safety hook by an ABSOLUTE path under that same directory — the
root-owned copy of `config/hooks/block-dangerous.sh` the installer also places —
so nothing in `~/.claude/` can edit the script the floor runs.

WHY A SEPARATE FILE FROM `test_the_safety_hook_is_wired.py`. That module guards
the USER-tier declaration and reads its mapping out of `SYMLINK_TARGETS`. The
floor is deliberately NOT a symlink target (a symlink from /etc into a checkout
the operator can edit is a floor the operator can lower), so it has its own
mapping — `MANAGED_FLOOR` and `MANAGED_DIR` in `install.sh` — and this module
reads that one. Both files ask the same three questions of their tier: is the
hook DECLARED, does its command RESOLVE to a shipped executable, and does the
tier stay one the flag cannot strip.

THE TWO KEYS THIS FLOOR MUST NOT SET, and why each is a guard rather than a
preference:

  * `allowManagedHooksOnly` — the phase checklist names it. MEASURED 2026-09-18
    (`scripts/helpers/managed-tier-probe/probe.sh` trial T5, CLI 2.1.275): with
    it set, a hook declared in the user tier does not run. The fleet's other two
    hooks (`block-detached-dispatch.sh`, `notify-done.sh`), every project hook
    and every hook the operator adds live in that tier, and the 2026-09-18
    ruling keeps the user tier extensible. The key would silence a guard to
    protect a guard that needs no protecting: the docs say `disableAllHooks`
    outside managed settings never reaches a managed hook.
  * `permissions.disableBypassPermissionsMode` — the fleet's autonomous mode
    IS bypass mode. Setting it from the floor, where nothing below can undo it,
    stops every dispatch on every machine at once.

WHAT THIS DOES NOT LOOK AT. Whether `/etc/claude-code/` on any host carries
this file (a property of the host — asked conditionally below, never required),
and whether Claude Code READS a hook from there under
`--dangerously-skip-permissions`. The second is the fact the whole phase turns
on and it is a host-run measurement, not a unit test: `probe.sh` trials T1, T1d
and T2, results recorded beside it.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
INSTALL = REPO_ROOT / "install.sh"
CONFIG = REPO_ROOT / "config"
USER_SETTINGS = CONFIG / "settings.json"

SAFETY_EVENT = "PreToolUse"
SAFETY_MATCHER = "Bash"
SAFETY_SCRIPT = "block-dangerous.sh"

# Keys whose presence in the floor is a defect, each with the consequence.
FORBIDDEN_TOP_LEVEL = {
    "allowManagedHooksOnly": "silences every user-tier hook (probe trial T5) — two fleet hooks and the operator's own",
    "disableAllHooks": "from the managed tier this disables the floor's own hook as well",
}
FORBIDDEN_PERMISSIONS = {
    "disableBypassPermissionsMode": "the fleet runs under --dangerously-skip-permissions; this halts every dispatch",
    "defaultMode": "a managed defaultMode is read from the highest source only and would override every user tier",
}

_ARRAY = re.compile(r"^MANAGED_FLOOR=\((.*?)^\)", re.S | re.M)
_MANAGED_DIR = re.compile(r'^MANAGED_DIR="\$\{CDF_MANAGED_DIR:-([^}]+)\}"', re.M)


def _floor_entries() -> list[tuple[str, str, str]]:
    """`(source-rel-config, dest-rel-managed, mode)` per MANAGED_FLOOR entry,
    comments stripped first — the same reason `_symlink_targets` gives."""
    block = _ARRAY.search(INSTALL.read_text())
    assert block, "install.sh no longer declares MANAGED_FLOOR=( ... ); the floor's mapping is gone"
    body = re.sub(r"#[^\n]*", "", block.group(1))
    entries = [tuple(q.split(":")) for q in re.findall(r'"([^"]+)"', body)]
    assert entries, "MANAGED_FLOOR is empty — nothing is placed and every assertion here is vacuous"
    assert all(len(e) == 3 for e in entries), entries
    return entries  # type: ignore[return-value]


def _managed_dir() -> Path:
    m = _MANAGED_DIR.search(INSTALL.read_text())
    assert m, ('install.sh no longer sets MANAGED_DIR="${CDF_MANAGED_DIR:-/etc/...}"; '
               "this test reads the default out of it and cannot tell where the floor goes")
    path = Path(m.group(1))
    assert path.is_absolute(), path
    return path


def _floor_files() -> list[Path]:
    return [CONFIG / src for src, dst, _ in _floor_entries() if dst.endswith(".json")]


def _floor() -> dict:
    files = _floor_files()
    assert len(files) == 1, f"expected exactly one managed drop-in in MANAGED_FLOOR, found {files}"
    return json.loads(files[0].read_text())


def _hooks(cfg: dict) -> list[tuple[str, str, dict]]:
    return [
        (event, group.get("matcher", "*"), hook)
        for event, groups in (cfg.get("hooks") or {}).items()
        for group in groups
        for hook in group.get("hooks", [])
    ]


def test_the_floor_parses_and_is_the_file_install_sh_places() -> None:
    cfg = _floor()
    assert isinstance(cfg, dict) and cfg.get("hooks"), "the floor declares no hooks"


def test_the_safety_hook_is_DECLARED_in_the_floor_on_Bash() -> None:
    matches = [
        h for event, matcher, h in _hooks(_floor())
        if event == SAFETY_EVENT and matcher == SAFETY_MATCHER and SAFETY_SCRIPT in h.get("command", "")
    ]
    assert matches, (
        f"the managed floor declares no {SAFETY_EVENT} hook on {SAFETY_MATCHER!r} running "
        f"{SAFETY_SCRIPT}. The floor exists to carry that hook where ~/.claude/ cannot loosen it.")


def test_every_floor_hook_RESOLVES_to_a_shipped_executable_under_the_managed_dir() -> None:
    """The command is an absolute path under MANAGED_DIR, that path is one the
    installer places, and the repo file it is placed from exists and is
    executable. A `$HOME` here would point the floor back at the user-writable
    symlink, which is the loosening the floor exists to prevent."""
    managed = _managed_dir()
    placed = {managed / dst: (CONFIG / src, mode) for src, dst, mode in _floor_entries()}
    broken = []
    for event, matcher, hook in _hooks(_floor()):
        command = hook.get("command", "").strip()
        if not command:
            broken.append(f"{event}/{matcher}: no command")
            continue
        target = Path(command.split()[0])
        if "$" in command or "~" in command or not target.is_absolute():
            broken.append(f"{event}/{matcher}: {command!r} is not an absolute path — a floor hook "
                          f"must not resolve through $HOME or ~, which the user tier controls")
            continue
        if target not in placed:
            broken.append(f"{event}/{matcher}: {target} is not a path install.sh's MANAGED_FLOOR places")
            continue
        source, mode = placed[target]
        if not source.is_file():
            broken.append(f"{event}/{matcher}: {target} is placed from {source}, which does not exist")
            continue
        if mode != "0755" or not os.access(source, os.X_OK):
            broken.append(f"{event}/{matcher}: {source.relative_to(REPO_ROOT)} is not shipped executable "
                          f"(mode {mode}); the floor's hook would never run")
        # Declared, never left to the harness default, and bounded: a floor
        # hook that hangs holds every Bash call on every host at once. 120 s
        # is a ceiling, not a target — the shipped value is 10.
        if hook.get("timeout") is None or hook["timeout"] > 120:
            broken.append(f"{event}/{matcher}: timeout {hook.get('timeout')!r} — must be declared and bounded")
    assert not broken, "\n  ".join(["a floor hook that does not resolve never runs:"] + broken)


def test_the_floor_runs_the_SAME_script_the_user_tier_runs() -> None:
    """Two tiers, one guard. The floor is the un-loosenable copy of the user
    tier's hook, not a different hook — a divergence here is two controls with
    two semantics, the shape retired on 2026-08-15."""
    floor_scripts = {Path(h["command"].split()[0]).name for _, _, h in _hooks(_floor())}
    user = json.loads(USER_SETTINGS.read_text())
    user_scripts = {Path(os.path.expandvars(h["command"].split()[0])).name for _, _, h in _hooks(user)}
    assert SAFETY_SCRIPT in floor_scripts and SAFETY_SCRIPT in user_scripts, (floor_scripts, user_scripts)
    assert floor_scripts <= user_scripts, (
        f"the floor declares {floor_scripts - user_scripts}, which the user tier does not — "
        f"a host without the floor would be missing a guard the fleet relies on")


def test_the_floor_is_THIN_and_sets_no_key_that_silences_or_halts() -> None:
    cfg = _floor()
    bad = [f"{k}: {why}" for k, why in FORBIDDEN_TOP_LEVEL.items() if k in cfg]
    bad += [f"permissions.{k}: {why}" for k, why in FORBIDDEN_PERMISSIONS.items()
            if k in (cfg.get("permissions") or {})]
    assert not bad, "the managed floor sets a key that must stay out of it:\n  " + "\n  ".join(bad)
    # Thin by the ruling: the hook and the deny set, nothing else.
    assert set(cfg) <= {"permissions", "hooks"}, (
        f"the floor carries {sorted(set(cfg) - {'permissions', 'hooks'})}; the 2026-09-18 ruling "
        f"puts only the safety hook and the deny set in the managed tier")
    assert set(cfg.get("permissions") or {}) <= {"deny"}, (
        "the floor's permissions block may carry deny rules only — an allow here is not a floor")


def test_the_floor_deny_set_is_what_the_repo_says_it_is() -> None:
    """Empty by the 2026-08-15 ruling that retired the 49-rule list. This is
    where a rule goes when the operator rules one back in; the test pins the
    current answer so a rule cannot appear here without the ruling being re-read."""
    deny = (_floor().get("permissions") or {}).get("deny")
    assert deny == [], (
        f"the managed deny set is {deny!r}. It has been empty since the 2026-08-15 ruling "
        f"(block-dangerous.sh, 'The deny list is now empty; this is the only control'). "
        f"Adding a managed deny rule is an operator ruling — update this test with it.")


def test_the_installed_floor_matches_the_repo_where_an_installation_exists() -> None:
    """Host-coupled and CONDITIONAL, like the user-tier check: where
    /etc/claude-code carries this repo's floor, it must be the repo's floor. A
    machine without it is not a defect in the commit; a stale one is a floor
    enforcing something other than what the repo says."""
    managed = _managed_dir()
    stale = []
    for src, dst, mode in _floor_entries():
        target = managed / dst
        if not target.exists():
            continue
        if target.read_bytes() != (CONFIG / src).read_bytes():
            stale.append(f"{target} differs from config/{src} — re-run ./install.sh")
        elif mode == "0755" and not os.access(target, os.X_OK):
            stale.append(f"{target} is not executable — re-run ./install.sh")
    assert not stale, "\n  ".join(["the placed managed floor is stale:"] + stale)

"""Background dispatches are not reaped under memory pressure — declared, and held.

Claude Code kills backgrounded shells when it judges the machine under memory
pressure. Per machine, not per account, and silently: a `run_in_background`
dispatch simply stops. Measured 2026-09-13 across the PMs' sessions: three
consecutive background tasks killed, one of them a `sleep` loop; after
`CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1` landed in `config/settings.json`,
zero kills across six PMs running twenty-plus dispatches and agent fan-outs at
once. That setting is what lets the fleet run at that width.

HOW IT REACHES EVERY MACHINE, so nothing else needs adding. `install.sh` symlinks
`~/.claude/settings.json` to `config/settings.json`, so a `git pull` on any
machine carries it, and a headless child reads user-scope settings like any
session — the strip tripwire in `test_the_safety_hook_is_wired.py` holds the
flags that would take user scope away. What was missing was this: an edit to
`settings.json` that dropped the key would go green everywhere and the kills
would come back as "flaky dispatches".
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SETTINGS = REPO_ROOT / "config" / "settings.json"

REAPER_OFF = "CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP"


def test_the_background_shell_reaper_is_DISABLED_in_the_declared_settings() -> None:
    env = json.loads(SETTINGS.read_text(encoding="utf-8")).get("env")
    assert isinstance(env, dict), "settings.json declares no `env` block — the reaper is on"
    assert env.get(REAPER_OFF) == "1", (
        f"`env.{REAPER_OFF}` is {env.get(REAPER_OFF)!r}, not \"1\". Claude Code will "
        "kill background dispatches under memory pressure again, per machine and "
        "silently — the failure that capped the fleet at one PM.")

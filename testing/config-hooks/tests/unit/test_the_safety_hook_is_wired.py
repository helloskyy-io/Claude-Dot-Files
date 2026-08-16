"""The safety hook is the ONLY live control in a headless run, so its wiring is tested.

WHY THIS IS DIFFERENT FROM EVERY OTHER HOOK TEST HERE. `test_block_dangerous.py`
asks whether the hook makes the right decision. This asks whether it is ever
CONSULTED. A hook that is perfect and unreachable blocks nothing, and nothing in
the system says so out loud — the tool call simply succeeds.

WHAT MAKES IT THE ONLY CONTROL. Autonomous dispatches run with
`--dangerously-skip-permissions`, which is what lets them proceed without a human
at the prompt. That flag disables the permission system; it does NOT disable
hooks. On 2026-08-16 the 49-rule `permissions.deny` list was removed as a
compensating control and the hook itself was narrowed from 59 patterns to 5. Both
were the right calls, and together they mean there is no second control left.

THE THREE FAILURE MODES, none of which is loud:

  1. The hook is not DECLARED — an edit to `settings.json` drops the entry.
  2. The command does not RESOLVE — `install.sh` did not link `hooks/`, or the
     script was renamed. The path is a string in JSON; nothing checks it points
     at anything.
  3. A dispatch STRIPS user settings — `--setting-sources project,local` excludes
     the user-level file the hook is declared in. No runner passes it today, and
     the Managed Configuration sprint has it as a live proposal, so this test is
     the tripwire on that change rather than a claim about current code.

Mode 2 is the one worth stating plainly: the hook's own tests pass whether or not
the file is reachable from a dispatch, because they invoke it by path directly.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SETTINGS = REPO_ROOT / "config" / "settings.json"

# The event and matcher the safety hook must sit on. A `PreToolUse` hook on
# `Bash` is the only placement that sees a command BEFORE it runs; anything else
# observes damage rather than preventing it.
SAFETY_EVENT = "PreToolUse"
SAFETY_MATCHER = "Bash"
SAFETY_SCRIPT = "block-dangerous.sh"


def _hooks() -> list[tuple[str, str, dict]]:
    """Every configured hook as (event, matcher, hook_dict)."""
    cfg = json.loads(SETTINGS.read_text())
    return [
        (event, group.get("matcher", "*"), hook)
        for event, groups in cfg.get("hooks", {}).items()
        for group in groups
        for hook in group.get("hooks", [])
    ]


def _resolve(command: str) -> Path:
    """The filesystem path a hook command points at.

    Commands are shell strings; ours are a bare path to a script, optionally
    with `$HOME`. Expanding only the variable — rather than running the string —
    keeps this a static check that cannot itself execute a hook.
    """
    return Path(os.path.expandvars(command.strip().split()[0])).expanduser()


def test_the_safety_hook_is_DECLARED_on_Bash() -> None:
    """Failure mode 1: the entry is gone and every dispatch runs uncontrolled."""
    matches = [
        h for event, matcher, h in _hooks()
        if event == SAFETY_EVENT
        and matcher == SAFETY_MATCHER
        and SAFETY_SCRIPT in h.get("command", "")
    ]
    assert matches, (
        f"No {SAFETY_EVENT} hook on {SAFETY_MATCHER!r} runs {SAFETY_SCRIPT}. "
        f"Autonomous runs pass --dangerously-skip-permissions and the deny list "
        f"was removed on 2026-08-16, so this hook is the only remaining control "
        f"over what a headless dispatch may execute."
    )


def test_every_hook_command_RESOLVES_to_an_executable_script_in_the_repo() -> None:
    """Failure mode 2, half one: the path is a string nobody checks.

    CHECKED AGAINST `config/hooks/`, THE SOURCE OF TRUTH, NOT AGAINST `~/.claude/`.
    The original version asserted the installed path existed, which is true on a
    workstation where `install.sh` has run and false on every clone — so it
    turned the merge gate RED for the whole repo while passing for the person who
    wrote it. That is the signature of a host-coupled test: it asserted something
    about one machine, not about the code.

    The half this half covers is the one a clone CAN answer: the command names a
    script that exists in this repo and is executable. A rename, a typo or a
    deleted script fails here, on every runner. The other half — whether
    `install.sh` actually linked it on THIS machine — is the test below, which
    can only run where an install exists.

    Checked for EVERY hook rather than only the safety one. A broken `Stop` hook
    is a lesser problem, but it is the same defect and the same silence.
    """
    hooks_dir = REPO_ROOT / "config" / "hooks"
    broken = []
    for event, matcher, hook in _hooks():
        target = _resolve(hook.get("command", ""))
        source = hooks_dir / target.name
        if not source.is_file():
            broken.append(
                f"{event}/{matcher}: command points at {target}, whose basename "
                f"{target.name!r} is not a script in config/hooks/")
        elif not os.access(source, os.X_OK):
            broken.append(f"{event}/{matcher}: {source} is not executable")
    assert not broken, (
        "A hook command that does not resolve never runs, and nothing reports it "
        "— the tool call simply succeeds:\n  " + "\n  ".join(broken)
    )


def test_the_INSTALLED_hook_paths_resolve_where_an_install_exists() -> None:
    """Failure mode 2, half two: `install.sh` did not link `hooks/`.

    SKIPPED WHERE THERE IS NO INSTALL, WHICH IS NOT THE SAME AS PASSING. A CI
    runner and a fresh clone have no `~/.claude/hooks/`, and there is nothing
    honest to assert about a link that was never meant to exist there. A skip
    says "not measured"; a pass would say "checked and fine", and those are
    different facts.

    Where an install DOES exist — every machine that actually dispatches — this
    is the check that catches a stale or missing symlink, which is the failure
    the whole file is about.
    """
    installed_dir = Path(os.path.expanduser("~/.claude/hooks"))
    if not installed_dir.exists():
        pytest.skip(f"no install at {installed_dir} — install.sh has not run here")

    broken = []
    for event, matcher, hook in _hooks():
        target = _resolve(hook.get("command", ""))
        if not target.is_file():
            broken.append(f"{event}/{matcher}: {target} does not exist")
        elif not os.access(target, os.X_OK):
            broken.append(f"{event}/{matcher}: {target} is not executable")
    assert not broken, (
        "This machine has an install, and a declared hook does not resolve into "
        "it — re-run install.sh:\n  " + "\n  ".join(broken)
    )


def test_no_runner_STRIPS_the_settings_file_the_safety_hook_lives_in() -> None:
    """Failure mode 3: a tripwire on a change that is actively proposed.

    `--setting-sources project,local` excludes user-level settings, which is
    where the hook is declared. The Managed Configuration sprint carries that
    flag as a candidate mechanism, and its own checkbox says the safety blocker
    must be resolved BEFORE the flag is touched. This is what makes that
    ordering enforceable instead of remembered.
    """
    offenders = []
    for path in (REPO_ROOT / "scripts").rglob("*.py"):
        if "__pycache__" in path.parts or "/tests/" in path.as_posix():
            continue
        for n, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue          # a comment discussing the flag is not passing it
            if re.search(r"--setting-sources", line):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{n}: {line.strip()[:90]}")
    assert not offenders, (
        "A runner restricts settings sources, which drops the user-level file the "
        "safety hook is declared in. Resolve the safety blocker first — give the "
        "hook another supply route — then change this test with it:\n  "
        + "\n  ".join(offenders)
    )

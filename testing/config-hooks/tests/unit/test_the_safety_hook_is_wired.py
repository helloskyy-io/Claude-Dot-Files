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

REPO_ROOT = Path(__file__).resolve().parents[4]
SETTINGS = REPO_ROOT / "config" / "settings.json"

# `install.sh` symlinks `config/hooks/` wholesale to `~/.claude/hooks/`, and the
# commands in `settings.json` name the INSTALLED path. Both ends are checked
# below, and they are different questions: the repo end is a property of the
# CODE, the installed end is a property of THIS MACHINE.
REPO_HOOKS = REPO_ROOT / "config" / "hooks"
INSTALLED_HOOKS = Path.home() / ".claude" / "hooks"

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


def test_every_hook_command_RESOLVES_to_an_executable_file() -> None:
    """Failure mode 2: the path is a string nobody checks points at anything.

    Checked for EVERY hook rather than only the safety one. A broken `Stop` hook
    is a lesser problem, but it is the same defect and the same silence, and a
    check that covers one path while the next one over is unchecked is the shape
    this repo has been bitten by before.

    ASKED AT BOTH ENDS, BECAUSE THEY ARE DIFFERENT QUESTIONS — and the first
    version of this test asked only the second, which made it **host-coupled**:
    it asserted that `~/.claude/hooks/block-dangerous.sh` exists, which is true
    on a machine where `install.sh` has run and false on every clean runner. It
    passed on its author's workstation and was red on `main` for three
    consecutive pushes, reporting a missing safety control that was not missing.

      * **The REPO end is a property of the code** and is checked always: the
        command must name a script under the directory `install.sh` links, and
        that script must be shipped here and executable. This is what fails on a
        rename, a deletion, or a `chmod` — every way the wiring can break in a
        commit, which is what a merge gate can act on.
      * **The INSTALLED end is a property of this machine** and is checked only
        where there is an installation to check. On a workstation this still
        catches `install.sh` never having been run, or the link having been
        clobbered.

    WHAT IT NO LONGER LOOKS AT, stated so the narrowing is visible: on a machine
    with no `~/.claude/hooks/` at all it cannot tell you the hook is unlinked —
    because on that machine nothing was ever linked, and that is not a defect in
    anything this repo ships. The three failure modes in the module docstring
    are all still reachable; only the *"you personally have not installed it"*
    reading is gone.
    """
    broken = []
    for event, matcher, hook in _hooks():
        target = _resolve(hook.get("command", ""))
        if target.parent != INSTALLED_HOOKS:
            broken.append(
                f"{event}/{matcher}: {target} is not under {INSTALLED_HOOKS}, "
                f"which is the only directory install.sh links — nothing puts a "
                f"script there"
            )
            continue
        source = REPO_HOOKS / target.name
        if not source.is_file():
            broken.append(
                f"{event}/{matcher}: {target} is configured, but this repo "
                f"ships no {source.relative_to(REPO_ROOT)} for install.sh to "
                f"link — renamed or deleted"
            )
        elif not os.access(source, os.X_OK):
            broken.append(
                f"{event}/{matcher}: {source.relative_to(REPO_ROOT)} is not "
                f"executable, so the link resolves and the hook still never runs"
            )
        elif INSTALLED_HOOKS.is_dir() and not target.is_file():
            broken.append(
                f"{event}/{matcher}: {INSTALLED_HOOKS} exists but {target} does "
                f"not — install.sh has not been run since this hook was added, "
                f"or the link was clobbered"
            )
    assert not broken, (
        "A hook command that does not resolve never runs, and nothing reports it "
        "— the tool call simply succeeds:\n  " + "\n  ".join(broken)
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

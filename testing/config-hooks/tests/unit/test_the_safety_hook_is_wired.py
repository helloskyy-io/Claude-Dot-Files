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

THE THREE MODES ARE NOT THIS FILE'S INVENTION — they are the three breakage
shapes `workflow-scripts.md` § *The safety-layer invariant* names in one
sentence: *"adding, narrowing or reordering `--setting-sources`, moving hook
configuration between scopes, or changing what `install.sh` symlinks."* That
mapping is written down here because the first two passes over this file each
closed the instance in front of them without pulling up the standard that
already enumerated the full set, and the coverage that resulted was one shape
guarded blind, one guarded against a hardcoded assumption, and one not guarded
at all. Every test below names the shape it holds, so the next pass can check
the list rather than rediscover it.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SETTINGS = REPO_ROOT / "config" / "settings.json"
INSTALL = REPO_ROOT / "install.sh"

# `install.sh` symlinks `config/<item>` to `~/.claude/<item>`, and the commands
# in `settings.json` name the INSTALLED path. Both ends are checked below, and
# they are different questions: the repo end is a property of the CODE, the
# installed end is a property of THIS MACHINE.
#
# NEITHER DIRECTORY IS WRITTEN DOWN HERE — both are read out of install.sh by
# `_install_dirs`, because hardcoding them is what let the third breakage shape
# the standard names go unguarded.

# The two entries of `install.sh`'s SYMLINK_TARGETS this wiring rests on: the
# directory the hook script is linked from, and the file the hook is DECLARED
# in. Named here so the tests below can ask install.sh rather than assume it.
HOOKS_TARGET = "hooks"
SETTINGS_TARGET = "settings.json"

_SYMLINK_TARGETS = re.compile(r"^SYMLINK_TARGETS=\((.*?)^\)", re.S | re.M)

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


def _symlink_targets() -> list[str]:
    """What `install.sh` links into `~/.claude/`, read out of `install.sh`.

    DERIVED RATHER THAN ASSUMED, and that is the whole point of this helper.
    The installed path used to be the literal `Path.home() / ".claude" /
    "hooks"`, which encodes install.sh's behaviour as a constant — so the third
    breakage shape the standard names, *changing what `install.sh` symlinks*,
    could land and every test here would stay green on a clean runner, where the
    installed-end branch never executes at all.
    """
    block = _SYMLINK_TARGETS.search(INSTALL.read_text())
    assert block, (
        f"{INSTALL.name} no longer declares a SYMLINK_TARGETS=( ... ) array, so "
        f"nothing here can tell what it links. The install mechanism changed "
        f"shape; these tests read it and must change with it."
    )
    return re.findall(r'"([^"]+)"', block.group(1))


def _install_dirs() -> tuple[Path, Path]:
    """`(<repo>/config, ~/.claude)` — BOTH sides of install.sh's mapping, read
    out of install.sh.

    The mapping used to be spelled twice as a constant: `REPO_ROOT / "config"`
    here and `~/.claude/` in the resolver. Two hardcoded halves of one fact that
    install.sh already states, which is what makes *"changing what `install.sh`
    symlinks"* — the third breakage shape `workflow-scripts.md` § *The
    safety-layer invariant* names — unguardable: rename either directory in
    install.sh and every test here keeps passing against the old names.
    """
    text = INSTALL.read_text()
    found = {}
    for name in ("CONFIG_DIR", "CLAUDE_DIR"):
        assign = re.search(rf'^{name}="([^"]*)"', text, re.M)
        assert assign, (
            f"install.sh no longer assigns {name}, so nothing here can tell "
            f"which directories it maps between. The install mechanism changed "
            f"shape; these tests read it and must change with it."
        )
        found[name] = assign.group(1)
    config = Path(found["CONFIG_DIR"].replace("$REPO_DIR", str(REPO_ROOT)))
    claude = Path(found["CLAUDE_DIR"].replace("$HOME", str(Path.home())))
    return config, claude


def _installed_hooks() -> Path:
    """The directory `install.sh` puts `config/hooks/` at on an installed box."""
    targets = _symlink_targets()
    assert HOOKS_TARGET in targets, (
        f"install.sh's SYMLINK_TARGETS is {targets}, which no longer contains "
        f"{HOOKS_TARGET!r} — so nothing links config/hooks/ into ~/.claude/, and "
        f"every hook command in settings.json names a path install.sh will never "
        f"create. This is the 'changing what install.sh symlinks' shape."
    )
    return _install_dirs()[1] / HOOKS_TARGET


def _resolve(command: str) -> Path:
    """The INSTALLED filesystem path a hook command names.

    Commands are shell strings; ours are a bare path to a script, optionally
    with `$HOME`. Expanding only the variable — rather than running the string —
    keeps this a static check that cannot itself execute a hook.

    THIS IS A PARSE, NOT A JUDGEMENT. It says where the command points; whether
    that is a place install.sh links, and whether a repo file backs it, are
    `_repo_source` and the test below.
    """
    return Path(os.path.expandvars(command.strip().split()[0])).expanduser()


def _repo_source(target: Path) -> Path | None:
    """The repo file `target` names through install.sh's mapping, or None.

    ⚠ THE PROPERTY ASSERTED HERE IS THE COMMIT'S, NOT THE MACHINE'S, AND THE
    FIRST VERSION OF THIS FILE GOT THAT WRONG. It expanded
    `$HOME/.claude/hooks/block-dangerous.sh` and asserted the file existed —
    true on a workstation where `install.sh` has run, false everywhere else. It
    put `main` red three times before anyone read the log, because the suite is
    green locally by construction: the property it asserted was true of the
    machine running it, never of the commit.

    `install.sh` symlinks `<repo>/config/<item>` -> `~/.claude/<item>`, so a
    command naming a path under the linked directory names a repo file through
    that mapping. **Both ends of the mapping are read out of install.sh** by
    `_install_dirs` rather than written here, so renaming either directory is
    caught instead of silently re-baselined.

    WHAT THIS DOES NOT LOOK AT: whether `install.sh` has actually run on any
    given machine, and therefore whether the symlink is present at runtime. That
    is a property of a host, not of a commit, and it needs a deployment check
    rather than a unit test — see `C-100`, which covers exactly that gap. The
    test below still asks it where an installation exists, which costs a clean
    runner nothing and keeps a workstation honest.
    """
    config, claude = _install_dirs()
    try:
        relative = target.relative_to(claude)
    except ValueError:
        return None
    return config / relative


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
    installed_hooks = _installed_hooks()
    broken = []
    for event, matcher, hook in _hooks():
        target = _resolve(hook.get("command", ""))
        if target.parent != installed_hooks:
            broken.append(
                f"{event}/{matcher}: {target} is not under {installed_hooks}, "
                f"which is the only directory install.sh links — nothing puts a "
                f"script there"
            )
            continue
        source = _repo_source(target)
        if source is None:
            broken.append(
                f"{event}/{matcher}: {target} is not under the directory "
                f"install.sh maps from, so no repo file backs it"
            )
        elif not source.is_file():
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
        elif installed_hooks.is_dir() and not target.is_file():
            broken.append(
                f"{event}/{matcher}: {installed_hooks} exists but {target} does "
                f"not — install.sh has not been run since this hook was added, "
                f"or the link was clobbered"
            )
    assert not broken, (
        "A hook command that does not resolve never runs, and nothing reports it "
        "— the tool call simply succeeds:\n  " + "\n  ".join(broken)
    )


def test_the_hook_is_declared_in_the_file_install_sh_puts_at_USER_scope() -> None:
    """The 'moving hook configuration between scopes' shape.

    Mode 3 below is specifically about a dispatch dropping the USER tier. That
    only bites while the hook is declared in the file that BECOMES the user
    tier — `config/settings.json`, via install.sh's `settings.json` target. Move
    the declaration into a project- or local-scope settings file and mode 3's
    tripwire still passes while the hook has silently changed which tiers it
    depends on.

    WHAT THIS DOES NOT LOOK AT. It cannot see a SECOND settings file taking
    precedence at run time — there is exactly one settings file in this repo
    today (`config/settings.json`; verified: no other `settings*.json` is
    tracked), so a precedence question has nothing to be asked about yet. If a
    project-scope settings file is ever added, this test is the one that has to
    grow, and that is why the gap is written down rather than left to be
    rediscovered.
    """
    targets = _symlink_targets()
    assert SETTINGS_TARGET in targets, (
        f"install.sh's SYMLINK_TARGETS is {targets}, which no longer contains "
        f"{SETTINGS_TARGET!r} — so {SETTINGS.relative_to(REPO_ROOT)} no longer "
        f"becomes the USER-tier settings file, and the hook declared in it is "
        f"not in the tier the tripwire below is guarding."
    )
    assert SETTINGS.is_file(), (
        f"{SETTINGS.relative_to(REPO_ROOT)} is gone, so the hook is declared "
        f"somewhere this test does not know about"
    )


def _swept_sources() -> list[Path]:
    """The files the settings-source tripwire reads.

    EVERY FILE UNDER `scripts/`, AT ANY EXTENSION, and the absence of an
    extension filter is the fix rather than an oversight. This was
    `rglob("*.py")` until 2026-08-16 — 82 Python files and none of the 37 shell
    files — while the one file in the whole tree that invokes `claude -p` with
    `--dangerously-skip-permissions` is `workflows/activities/run-claude.sh`.
    The tripwire on the fleet's only remaining safety control could not see the
    file the flag would be added to. Measured, not reasoned: appending
    `--setting-sources project,local` to that line left this test green and all
    2046 tests green.

    An extension is a PROXY for "a file that dispatches claude", and widening
    the proxy to `*.py` + `*.sh` would only move the blind spot to the next
    language. So the population is not filtered by extension at all, and
    `test_the_settings_source_sweep_SEES_every_file_that_DISPATCHES_claude`
    below checks the population against the property instead.

    BIASED TOWARD A FALSE ALARM, deliberately. A prose mention of the flag in a
    `scripts/**/*.md` prompt would trip this, because a prompt is not a comment
    and nothing here can tell prose from argv. That is the right way round for a
    safety tripwire: a false alarm costs one line to resolve, and silence costs
    destructive-command blocking on every autonomous run. No file under
    `scripts/` mentions the flag today.
    """
    return [
        p for p in sorted((REPO_ROOT / "scripts").rglob("*"))
        if p.is_file()
        and "__pycache__" not in p.parts
        and "/tests/" not in p.as_posix()
    ]


# A `claude` invocation as it appears in ARGV, rather than in prose about one.
# The backtick lookarounds are the entire discriminator and they are load-
# bearing: this repo discusses `--dangerously-skip-permissions` in 33 files and
# PASSES it in one, and every discussion of it writes it inside backticks.
_DISPATCHES_CLAUDE = re.compile(
    r"(?<!`)(?:(?:^|[\s;&|(])claude\s+(?:-p|--print)"
    r"|--dangerously-skip-permissions)(?!`)"
)


def _dispatchers() -> list[str]:
    """Every tracked file that INVOKES the claude CLI, discovered not listed.

    Deliberately a different instrument, and a different corpus, than
    `_swept_sources`: this reads `git ls-files` across the WHOLE repo, so it can
    see a dispatcher that has moved out of `scripts/` entirely. A check that
    re-used the swept set's own glob to validate the swept set would be an
    identity, not a check.
    """
    tracked = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files"],
        capture_output=True, text=True, check=True,
    ).stdout.split("\n")
    found = []
    for relative in tracked:
        # Prose surfaces, at the two altitudes they occur: `docs/` is written
        # ABOUT the fleet, and a `.md` anywhere is read by a model rather than
        # by a shell. Tests are fixtures — one that spawned a dispatch would be
        # a different problem with a different guard.
        if not relative or relative.startswith("docs/") or relative.endswith(".md"):
            continue
        if relative.startswith("testing/") or "/tests/" in relative:
            continue
        try:
            text = (REPO_ROOT / relative).read_text(errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            if line.lstrip().startswith("#"):
                continue
            if _DISPATCHES_CLAUDE.search(line):
                found.append(relative)
                break
    return found


def test_no_runner_STRIPS_the_settings_file_the_safety_hook_lives_in() -> None:
    """Failure mode 3: a tripwire on a change that is actively proposed.

    `--setting-sources project,local` excludes user-level settings, which is
    where the hook is declared. The Managed Configuration sprint carries that
    flag as a candidate mechanism, and its own checkbox says the safety blocker
    must be resolved BEFORE the flag is touched. This is what makes that
    ordering enforceable instead of remembered.
    """
    offenders = []
    for path in _swept_sources():
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        for n, line in enumerate(text.splitlines(), 1):
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


def test_the_settings_source_sweep_SEES_every_file_that_DISPATCHES_claude() -> None:
    """The population anchor — what the tripwire above is worth is what it READS.

    The tripwire's defect was never its pattern; it was its corpus. So this
    asserts the corpus against the PROPERTY that defines it — a file that
    invokes the claude CLI — rather than against the extension that used to
    stand in for it. Narrow the glob back, move the runner to a language nobody
    thought of, or relocate it out of `scripts/`, and this goes red naming the
    file the tripwire stopped watching.

    WHAT THIS DOES NOT LOOK AT, so a green run is not read as more than it is:

      * **A flag that is never written as a literal.** A runner assembling
        `--setting` + `-sources`, or reading the flag out of `config.yaml`, is
        invisible to both this and the tripwire.
      * **Whether the dispatcher is REACHED.** It says the file is in the swept
        corpus, never that anything calls it.
      * **Prose surfaces.** `docs/`, every `.md`, and every test are excluded by
        construction — a dispatcher written in one of those would be missed. The
        exclusion is what keeps this from firing on the 33 files that DISCUSS
        the flag, and it is the boundary this check trades away to be readable.
      * **The other direction.** It proves the corpus is not too NARROW. Nothing
        here says a non-dispatcher in the corpus is harmless — that is the
        false-alarm bias `_swept_sources` states.
    """
    dispatchers = _dispatchers()
    assert dispatchers, (
        "no tracked file was found invoking the claude CLI, which means this "
        "check read nothing — a gate reporting a clean tree and a gate reading "
        "nothing look identical. Either the discovery pattern stopped matching "
        "or `git ls-files` returned nothing from this worktree."
    )
    swept = {p.relative_to(REPO_ROOT).as_posix() for p in _swept_sources()}
    missed = sorted(set(dispatchers) - swept)
    assert not missed, (
        "a file DISPATCHES claude and the settings-source tripwire above does "
        "not read it, so `--setting-sources` could be added there and every "
        "test would stay green — which is exactly what happened on 2026-08-16 "
        "when the sweep was scoped to `*.py` and the only dispatcher was "
        "shell:\n  " + "\n  ".join(missed)
    )

"""The safety hook is the ONLY live control in a headless run, so its wiring is tested.

WHY THIS IS DIFFERENT FROM EVERY OTHER HOOK TEST HERE. `test_block_dangerous.py`
asks whether the hook makes the right decision. This asks whether it is ever
CONSULTED. A hook that is perfect and unreachable blocks nothing, and nothing in
the system says so out loud — the tool call simply succeeds.

WHAT MAKES IT THE ONLY CONTROL. Autonomous dispatches run with
`--dangerously-skip-permissions`, which is what lets them proceed without a human
at the prompt. That flag skips every prompt and ignores allow rules; it does NOT
disable hooks, and — measured 2026-09-18, `scripts/helpers/managed-tier-probe/`
trial T6 — it does not disable deny rules either. On 2026-08-16 the 49-rule
`permissions.deny` list was removed as a compensating control and the hook itself
was narrowed from 59 patterns to 5. Both were the right calls, and together they
mean there is no second control left.

THE HOOK NOW HAS A SECOND SUPPLY ROUTE, AND THIS FILE STILL GUARDS THE FIRST.
Since Workflow Decomposition Phase 7 the same script is also declared in the
managed floor (`config/managed-settings.d/claude-dot-files.json`, placed root-
owned under `/etc/claude-code/` by `install.sh`), which the user tier cannot
loosen and which fires under the flag (probe trials T1, T2). That route is
guarded by `test_the_managed_floor_is_wired.py`. The user-tier declaration is
KEPT, and this file keeps guarding it, because a host where `install.sh` could
not place the floor has only this route — the fleet is never left without a
firing guard on the way to the un-loosenable one.

THE THREE FAILURE MODES, none of which is loud:

  1. The hook is not DECLARED — an edit to `settings.json` drops the entry.
  2. The command does not RESOLVE — `install.sh` did not link `hooks/`, or the
     script was renamed. The path is a string in JSON; nothing checks it points
     at anything.
  3. A dispatch STRIPS user settings — `--setting-sources project,local` excludes
     the user-level file the hook is declared in, and `--safe-mode`,
     `--restricted` and `--bare` each leave the hook not running by their own
     route (`_HOOK_STRIPPING_FLAGS`). No runner passes any of them today, and
     the Managed Configuration sprint has the first as a live proposal, so the
     test is the tripwire on that change rather than a claim about current code.

Mode 2 is the one worth stating plainly: the hook's own tests pass whether or not
the file is reachable from a dispatch, because they invoke it by path directly.

THE MODES ARE NOT THE STANDARD'S SHAPES, AND CONFLATING THEM COSTS A PASS. The
modes above are how the wiring FAILS; `workflow-scripts.md` § *The safety-layer
invariant* names how it BREAKS — *"adding, narrowing or reordering
`--setting-sources`, moving hook configuration between scopes, or changing what
`install.sh` symlinks."* Those are different lists that happen to be the same
length, and an earlier revision of this docstring asserted they were the same
list. They are not: mode 1 corresponds to no shape at all, and shape (b) is held
by a test that is not one of the modes. The correspondence, so the next pass
checks it rather than rediscovering it:

  | Shape (`workflow-scripts.md` § The safety-layer invariant) | Held by |
  |---|---|
  | (a) adding, narrowing or reordering `--setting-sources` | `test_no_runner_STRIPS_the_settings_file_the_safety_hook_lives_in`, with `test_the_settings_source_sweep_SEES_every_file_that_DISPATCHES_claude` as its anchor |
  | (b) moving hook configuration between scopes | `test_the_hook_is_declared_in_the_file_install_sh_puts_at_USER_scope` |
  | (c) changing what `install.sh` symlinks | `test_every_hook_command_RESOLVES_to_an_executable_file`, via `_symlink_targets` and `_install_dirs` reading both directories OUT of install.sh |
  | *(no shape — the declaration itself)* | `test_the_safety_hook_is_DECLARED_on_Bash`, mode 1 |

The right-hand column is CHECKED, not asserted — see
`test_the_shape_to_test_MAPPING_above_names_tests_that_exist` at the bottom of
this file. A prose table naming code is a second copy of a fact the module
already owns, and a renamed test would leave it pointing at nothing while every
test here stayed green. That is the same defect class as a hand-typed count.

That mapping is written down because the first two passes over this file each
closed the instance in front of them without pulling up the standard that
already enumerated the full set, and the coverage that resulted was one shape
guarded blind, one guarded against a hardcoded assumption, and one not guarded
at all.
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
    # COMMENTS ARE STRIPPED FIRST, and that is not tidiness. Deleting a target
    # is how a reader imagines this shape breaking; COMMENTING IT OUT is how
    # bash is actually edited — `# "hooks"` while debugging, never restored.
    # Reading the raw array body finds the quoted string inside the comment, so
    # install.sh links nothing into `~/.claude/hooks/`, every hook command in
    # settings.json names a path that will never exist, and every assertion
    # below stays green. That is the third breakage shape landing silently in
    # the file written to catch it.
    return re.findall(r'"([^"]+)"', re.sub(r"#[^\n]*", "", block.group(1)))


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
    # `${REPO_DIR}` AND `$REPO_DIR` ARE THE SAME SHELL, and a `.replace()` on
    # the brace-less spelling only handles one of them. Rewrite install.sh's
    # line to the equally idiomatic `CONFIG_DIR="${REPO_DIR}/config"` and the
    # substitution silently does nothing: `config` becomes the literal relative
    # path `${REPO_DIR}/config`, and the caller's `Path.relative_to(REPO_ROOT)`
    # then raises `ValueError` — so the suite reports a broken TEST rather than
    # broken hook wiring, on the module guarding the fleet's only live control.
    def _expand(raw: str, var: str, value: str) -> str:
        return re.sub(rf"\$\{{{var}\}}|\${var}\b", value.replace("\\", "\\\\"), raw)

    config = Path(_expand(found["CONFIG_DIR"], "REPO_DIR", str(REPO_ROOT)))
    claude = Path(_expand(found["CLAUDE_DIR"], "HOME", str(Path.home())))
    # FAIL HERE, NAMING THE UNEXPANDED VALUE, rather than letting an unexpanded
    # `$VAR` travel into a caller that reports a confusing error about a path.
    for name, resolved, raw in (
        ("CONFIG_DIR", config, found["CONFIG_DIR"]),
        ("CLAUDE_DIR", claude, found["CLAUDE_DIR"]),
    ):
        assert "$" not in str(resolved) and resolved.is_absolute(), (
            f"install.sh's {name}={raw!r} did not expand to an absolute path "
            f"(got {str(resolved)!r}). It uses a shell construction this parse "
            f"does not know — teach `_expand` that spelling; do not work around "
            f"it downstream, because every check here rests on this mapping."
        )
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
    rather than a unit test — see `C-8z8v04wk`, which covers exactly that gap. The
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
        where there is an installation to check — which is asked with
        `os.path.lexists`, about the LINK, not with `is_dir()`, which follows it
        and so answers a question that is already the answer. On a workstation
        this still catches `install.sh` never having been run, or the link
        having been clobbered — including the dangling-link case, which is what
        a repo move after installation leaves behind.

    WHAT IT NO LONGER LOOKS AT, stated so the narrowing is visible: on a machine
    with no `~/.claude/hooks/` at all it cannot tell you the hook is unlinked —
    because on that machine nothing was ever linked, and that is not a defect in
    anything this repo ships. The three failure modes in the module docstring
    are all still reachable; only the *"you personally have not installed it"*
    reading is gone.
    """
    installed_hooks = _installed_hooks()
    # `is_dir()` FOLLOWS SYMLINKS, and every installation here IS a symlink, so
    # asking it "does an installation exist?" answers "does the link still
    # resolve?" — which is the very breakage the branch below is for. Move or
    # rename the repo after `install.sh` ran and `~/.claude/hooks` is a DANGLING
    # link: `is_dir()` is False, the check is skipped, and the test passes on a
    # machine where the safety hook genuinely does not resolve. `lexists` asks
    # about the link itself, which is the question actually being put.
    is_installed = os.path.lexists(installed_hooks)
    broken = []
    for event, matcher, hook in _hooks():
        command = hook.get("command", "")
        if not command.strip():
            # A hook entry with no command cannot be resolved, and `_resolve`
            # would raise `IndexError` on the empty split rather than say so.
            broken.append(
                f"{event}/{matcher}: the hook entry declares no `command`, so "
                f"nothing runs on this event and no path can be checked"
            )
            continue
        target = _resolve(command)
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
        elif is_installed and not target.is_file():
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
    precedence at run time. There IS one now — the managed floor at
    `config/managed-settings.d/claude-dot-files.json`, which outranks this
    file — and what it declares is held by `test_the_managed_floor_is_wired.py`
    rather than here. The precedence question between the two was answered by
    measurement, not by a test: both tiers' hooks run and the managed one
    decides first (`scripts/helpers/managed-tier-probe/` trial T7). If a
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
    destructive-command blocking on every autonomous run. No runner under
    `scripts/` mentions the flag today.

    TWO FILES ARE EXEMPT BY EXACT PATH: THE INSTRUMENT THAT MEASURES THESE
    FLAGS, AND THE README THAT RECORDS THE MEASUREMENT.
    `scripts/helpers/managed-tier-probe/probe.sh` passes every one of them, on
    purpose, to the operator's real binary inside a throwaway container with
    the MANAGED floor mounted, to observe whether that floor's hook still
    fires (trials T8–T11, 2026-09-19: it does), and its README is the table
    of what was observed. Neither is a runner — nothing in the fleet
    dispatches through the probe, a person invokes it — and a tripwire that
    fired on the measurement of its own hazard would have to be silenced by
    deleting the measurement. `test_the_strip_exemption_NAMES_the_instrument_
    and_nothing_else` holds the exemption to those two files and to the
    property that earns it.
    """
    return [
        p for p in sorted((REPO_ROOT / "scripts").rglob("*"))
        if p.is_file()
        and "__pycache__" not in p.parts
        and "/tests/" not in p.as_posix()
        and p.relative_to(REPO_ROOT).as_posix() not in _MEASURES_THE_FLAGS
    ]


#: The instrument that passes the hook-stripping flags in order to MEASURE
#: them, in a container, against the managed floor, and the README that
#: records what it measured — exempt from the tripwire by exact path, never
#: by glob. See `_swept_sources`.
_MEASURES_THE_FLAGS = (
    "scripts/helpers/managed-tier-probe/probe.sh",
    "scripts/helpers/managed-tier-probe/README.md",
)


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


#: Every CLI flag known to leave the user-scope hook not running. The list is
#: OPEN — it is what has been looked at, not a closed set — and its one carrier
#: is the phase doc's Hazard vectors table; `test_the_strip_sweep_COVERS_every_
#: hazard_vector_the_corpus_names` holds this tuple to it.
_HOOK_STRIPPING_FLAGS = ("--setting-sources", "--safe-mode", "--restricted", "--bare")
_STRIPS_THE_HOOK = re.compile(
    r"(?<![\w-])(?:" + "|".join(re.escape(f) for f in _HOOK_STRIPPING_FLAGS) + r")(?![\w-])")


def test_no_runner_STRIPS_the_settings_file_the_safety_hook_lives_in() -> None:
    """Failure mode 3: a tripwire on a change that is actively proposed.

    `--setting-sources project,local` excludes user-level settings, which is
    where the hook is declared. The Managed Configuration sprint carries that
    flag as a candidate mechanism, and its own checkbox says the safety blocker
    must be resolved BEFORE the flag is touched. This is what makes that
    ordering enforceable instead of remembered.

    IT WAS WRITTEN AGAINST THAT ONE FLAG, and three others do the same job by
    their own route — `--safe-mode` disables hooks outright, `--restricted`
    ignores the user settings file (and `--tools Bash` hands the code-running
    tool back), `--bare` skips hooks. Measured from the CLI's own help text
    (I-pymkwrl4); all four trip this now.
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
            if _STRIPS_THE_HOOK.search(line):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{n}: {line.strip()[:90]}")
    assert not offenders, (
        "A runner passes a flag that leaves the user-scope safety hook not running "
        f"({', '.join(_HOOK_STRIPPING_FLAGS)}). Resolve the safety blocker first — "
        "give the hook another supply route — then change this test with it:\n  "
        + "\n  ".join(offenders)
    )


def test_the_strip_sweep_MATCHES_each_flag_it_claims_to() -> None:
    """Positive control for the tripwire's predicate, per flag.

    The sweep is green today because no runner passes any of these — which is
    indistinguishable from a pattern that matches none of them. So each flag is
    shown to trip it in the shape a runner would write, and a lookalike is shown
    not to, so the boundary is not doing the matching.
    """
    for flag in _HOOK_STRIPPING_FLAGS:
        assert _STRIPS_THE_HOOK.search(f'claude -p "$TASK" {flag} project,local --verbose'), flag
        assert _STRIPS_THE_HOOK.search(f"  {flag}"), flag
        assert not _STRIPS_THE_HOOK.search(f"{flag}-metrics"), f"{flag}: prefix matched a longer flag"


def test_the_strip_sweep_COVERS_every_hazard_vector_the_corpus_names() -> None:
    """The flag list is DERIVED from the phase doc that enumerates the hazard
    vectors, not restated beside it — a vector added there and not here is the
    hole the corpus already warned about (its list is open by its own words).
    """
    import sys
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "workflows" / "temporal" / "tests"))
    import planning_corpus
    planning_corpus.require_planning_corpus()
    doc = (planning_corpus.planning_root() / "development" / "edge-assistant"
           / "workflow-decomposition" / "phase5_configuration_a_run_absorbed.md")
    assert doc.exists(), f"the hazard-vector carrier moved: {doc}"
    section = doc.read_text(encoding="utf-8").split("### Hazard vectors", 1)[1].split("\n### ", 1)[0]
    named = set(re.findall(r"^\|\s*`(--[a-z-]+)", section, re.M))
    assert named, "the Hazard vectors table did not parse — this read nothing"
    missing = sorted(named - set(_HOOK_STRIPPING_FLAGS))
    assert not missing, (
        f"the corpus names hazard vector(s) the strip sweep does not watch for: {missing}")


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
    # The instrument dispatches claude (into a container) and is exempt from
    # the tripwire by name; it is held to its exemption by its own test below.
    missed = sorted(set(dispatchers) - swept - set(_MEASURES_THE_FLAGS))
    assert not missed, (
        "a file DISPATCHES claude and the settings-source tripwire above does "
        "not read it, so `--setting-sources` could be added there and every "
        "test would stay green — which is exactly what happened on 2026-08-16 "
        "when the sweep was scoped to `*.py` and the only dispatcher was "
        "shell:\n  " + "\n  ".join(missed)
    )


def test_the_strip_exemption_NAMES_the_instrument_and_nothing_else() -> None:
    """The control on the exemption. The exempt set is exactly the probe and
    its README (the only things that have earned it); both must exist; the
    probe must run its trials in a container rather than on the host and must
    actually pass the flags — an exemption for a file that stopped measuring
    them is a hole waiting for a runner to be created at that path."""
    probe = "scripts/helpers/managed-tier-probe/probe.sh"
    assert _MEASURES_THE_FLAGS == (probe, "scripts/helpers/managed-tier-probe/README.md"), (
        "the settings-source tripwire's exempt set changed; that is a ruling, "
        "not an edit — the probe earned it by measuring the flags, in a "
        f"container, against the managed floor: {_MEASURES_THE_FLAGS}")
    for relative in _MEASURES_THE_FLAGS:
        assert (REPO_ROOT / relative).is_file(), f"exempt path does not exist: {relative}"
    argv_lines = [line for line in (REPO_ROOT / probe).read_text(errors="replace").splitlines()
                  if not line.lstrip().startswith("#")]
    assert any("docker run" in line for line in argv_lines), (
        f"{probe} is exempt as a container-run instrument and no longer runs docker")
    for flag in _HOOK_STRIPPING_FLAGS:
        if flag == "--bare":
            continue  # unmeasurable on OAuth auth (exits 1 `Not logged in`, phase 5 doc); ruled against in roadmap.md
        assert any(_STRIPS_THE_HOOK.search(line) for line in argv_lines if flag in line), (
            f"{probe} is exempt for measuring {flag} and no longer passes it")


def test_the_shape_to_test_MAPPING_above_names_tests_that_exist() -> None:
    """The module docstring's shape table is a claim about this file; check it.

    A prose table mapping the standard's breakage shapes onto the tests that
    hold them is a SECOND declaration of a fact this module already owns, and
    the one thing it cannot do is notice when it stops being true. Rename any
    test below and the table quietly points at nothing while all five tests
    stay green — the reader who checks *"is shape (b) covered?"* against a
    stale name concludes it is not, or worse, concludes it is when the test it
    names was deleted.

    This is the same defect class as a hand-typed count and it has the same
    remedy: derive the check rather than restate the fact. What it does NOT
    look at is whether the test a row names actually holds that shape — that is
    a judgement, and it lives in each test's own docstring.
    """
    source = Path(__file__).read_text(encoding="utf-8")
    docstring = source.split('"""')[1]
    named = set(re.findall(r"`(test_[A-Za-z0-9_]+)`", docstring))
    assert named, (
        "the docstring names no test at all — the shape-to-test table was "
        "removed or reformatted, and this check now reads nothing"
    )
    defined = set(re.findall(r"^def (test_[A-Za-z0-9_]+)", source, re.M))
    missing = sorted(named - defined)
    assert not missing, (
        "the module docstring's shape table names tests this file does not "
        "define: " + ", ".join(missing)
        + ". Either the test was renamed and the table was not, or a shape is "
          "recorded as covered by something that no longer exists."
    )

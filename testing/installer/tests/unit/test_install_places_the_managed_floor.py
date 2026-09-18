"""`install.sh` places the managed floor, and REFUSES LOUDLY when it cannot.

WORKFLOW DECOMPOSITION PHASE 7, requirement 4: *"The installer ... is reworked
to also place (or verify) the managed-tier floor, with a stated behaviour when
it lacks the privilege to write the OS-level path (refuse loudly, name the path
— never silently skip the floor)."*

WHY THE REFUSAL IS THE TEST WORTH HAVING. The floor's whole value is that
`~/.claude/` cannot loosen it, and that value is exactly zero on a machine
where the installer reported success without placing it. A silent skip is the
failure the phase names by name, and it is the natural shape for this code to
decay into — one `|| true` on the sudo line. So the refusal is asserted on its
CONTENT (the resolved path, the privilege lacked, sudo's own reason) and its
EXIT CODE, not merely on the run being red.

HOW ROOT IS AVOIDED. `install.sh` reads `CDF_MANAGED_DIR` as the managed
directory (default `/etc/claude-code`, the only path Claude Code reads). These
tests point it at temp directories: a writable one to exercise placement, an
unwritable one plus a stub `sudo` that refuses to exercise the refusal, and an
unwritable one plus a stub `sudo` that grants to exercise the privileged path.
The stubs stand in for `claude`, `yq` and `sudo` on PATH; the real `jq`,
`install`, `cmp` and `stat` are what the installer actually runs.

AND HOW ROOT OWNERSHIP IS STILL VERIFIED. The installer refuses a floor that
is not owned by root or that a non-root user can write (review-pr finding F4
on PR #205: the byte check alone let a user-placed floor earn the banner). A
test cannot make a file root-owned without root, so under `CDF_MANAGED_DIR`
the installer also reads `CDF_MANAGED_OWNER_UID` — the owner the test can
produce — and `_run` sets it to this process's uid by default. The default in
the installer stays root, on the live path unconditionally and under the
override when the variable is unset, which is what the ownership control here
runs against: the same writable-directory placement that earns the banner
with the seam is REFUSED without it, naming the path and the owner.

WHAT THESE DO NOT LOOK AT, stated so the coverage is not read as more than it
is:

  * Whether `/etc/claude-code/` on THIS machine carries the floor. That is a
    property of a host, not of a commit; `test_the_managed_floor_is_wired.py`
    asks it conditionally, where an installation exists.
  * Whether Claude Code READS what was placed. That is
    `scripts/helpers/managed-tier-probe/probe.sh`, a host-run verification
    against the real binary, and it is not a unit test.
  * The interactive `sudo` prompt path. Every run here is `--non-interactive`,
    which is the path a dispatch or a CI job takes and the one where a silent
    skip would go unnoticed longest.
"""
from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
INSTALL = REPO_ROOT / "install.sh"
CONFIG = REPO_ROOT / "config"

SUDO_REFUSES = "#!/bin/sh\necho 'sudo: a password is required' >&2\nexit 1\n"
# A `sudo` that "grants": logs its argv, makes the locked directory writable
# for the duration of the command, and runs it. The only way to exercise the
# privileged branch without being root.
SUDO_GRANTS = """#!/bin/sh
printf '%s\\n' "$*" >> "$SUDO_LOG"
[ "$1" = "-n" ] && shift
chmod u+w "$LOCKED_DIR"
"$@"; rc=$?
chmod u-w "$LOCKED_DIR"
exit $rc
"""
STUB = "#!/bin/sh\necho stub\n"


def _floor_entries() -> list[tuple[str, str, str]]:
    """`MANAGED_FLOOR` as bash itself reads it, so the expectation is DERIVED
    from the installer and not restated here."""
    script = (
        "set -euo pipefail\nMANAGED_FLOOR=()\n"
        f'eval "$(sed -n "/^MANAGED_FLOOR=(/,/^)/p" {INSTALL})"\n'
        'printf "%s\\n" "${MANAGED_FLOOR[@]}"\n'
    )
    out = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                         timeout=30, check=True)
    entries = [tuple(line.split(":")) for line in out.stdout.splitlines() if line]
    assert entries, "install.sh declares no MANAGED_FLOOR entries — every test here would be vacuous"
    assert all(len(e) == 3 for e in entries), entries
    return entries  # type: ignore[return-value]


@pytest.fixture
def sandbox(tmp_path: Path):
    """A fake HOME, a stub PATH, and a place for the managed dir to go."""
    home = tmp_path / "home"
    binp = tmp_path / "bin"
    home.mkdir()
    binp.mkdir()
    for name in ("claude", "yq"):
        (binp / name).write_text(STUB)
        (binp / name).chmod(0o755)
    return tmp_path


def _run(sandbox: Path, managed_dir: Path | str, *args: str, sudo: str = SUDO_REFUSES,
         env_extra: dict | None = None, owner_uid: int | None = os.getuid()) -> subprocess.CompletedProcess:
    (sandbox / "bin" / "sudo").write_text(sudo)
    (sandbox / "bin" / "sudo").chmod(0o755)
    env = {
        **os.environ,
        "HOME": str(sandbox / "home"),
        "PATH": f"{sandbox / 'bin'}:{os.environ['PATH']}",
        "CDF_MANAGED_DIR": str(managed_dir),
        "SUDO_LOG": str(sandbox / "sudo.log"),
        "LOCKED_DIR": str(managed_dir),
    }
    env.pop("CDF_MANAGED_OWNER_UID", None)
    if owner_uid is not None:
        env["CDF_MANAGED_OWNER_UID"] = str(owner_uid)
    env.update(env_extra or {})
    return subprocess.run([str(INSTALL), "--non-interactive", *args],
                          capture_output=True, text=True, timeout=120, env=env)


def _placed_paths(managed_dir: Path) -> list[tuple[Path, Path, str]]:
    return [(CONFIG / src, managed_dir / dst, mode) for src, dst, mode in _floor_entries()]


def test_the_floor_is_placed_byte_for_byte_when_the_directory_is_writable(sandbox: Path) -> None:
    managed = sandbox / "etc"
    run = _run(sandbox, managed)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "Managed floor verified" in run.stdout
    placed = _placed_paths(managed)
    for source, target, mode in placed:
        assert target.is_file(), f"{target} was not placed\n{run.stdout}"
        assert target.read_bytes() == source.read_bytes(), f"{target} differs from {source}"
        if mode == "0755":
            assert os.access(target, os.X_OK), f"{target} is a hook copy and is not executable"
    # The population control: a floor with nothing in it verifies nothing.
    assert len(placed) >= 2, placed
    # The user tier was placed too — the floor is IN ADDITION, never instead.
    assert (sandbox / "home" / ".claude" / "settings.json").is_symlink()


def test_a_second_run_reports_already_placed_and_changes_nothing(sandbox: Path) -> None:
    managed = sandbox / "etc"
    assert _run(sandbox, managed).returncode == 0
    before = {t: t.stat().st_mtime_ns for _, t, _ in _placed_paths(managed)}
    run = _run(sandbox, managed)
    assert run.returncode == 0, run.stdout + run.stderr
    assert run.stdout.count("already placed") == len(before), run.stdout
    assert {t: t.stat().st_mtime_ns for t in before} == before, "an idempotent run rewrote the floor"


def test_a_stale_copy_is_re_placed(sandbox: Path) -> None:
    managed = sandbox / "etc"
    assert _run(sandbox, managed).returncode == 0
    _, target, _ = _placed_paths(managed)[0]
    target.write_text("{}\n")  # a floor enforcing something other than the repo says
    run = _run(sandbox, managed)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "re-placed (was stale)" in run.stdout
    source = _placed_paths(managed)[0][0]
    assert target.read_bytes() == source.read_bytes()


def test_a_hook_copy_that_lost_its_x_bit_is_re_placed(sandbox: Path) -> None:
    """Byte-identical and not executable is a hook that never runs — stale, not placed."""
    managed = sandbox / "etc"
    assert _run(sandbox, managed).returncode == 0
    hooks = [t for _, t, mode in _placed_paths(managed) if mode == "0755"]
    assert hooks, "no executable entry in MANAGED_FLOOR — the x-bit check has nothing to test"
    hooks[0].chmod(hooks[0].stat().st_mode & ~(stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
    run = _run(sandbox, managed)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "re-placed (was stale)" in run.stdout
    assert os.access(hooks[0], os.X_OK)


def test_a_floor_the_user_OWNS_is_refused_naming_path_and_owner(sandbox: Path) -> None:
    """F4's scenario exactly: a non-root user with a writable managed directory
    places the floor through the direct-write branch, the bytes match — and
    without the owner seam the required owner is root, so the banner must not
    appear. The refusal names the path and the failing property."""
    managed = sandbox / "etc"
    run = _run(sandbox, managed, owner_uid=None)
    out = run.stdout + run.stderr
    assert run.returncode == 1, f"exit {run.returncode}: a user-owned floor earned the banner\n{out}"
    assert "Managed floor verified" not in out, out
    assert "REWRITABLE FROM BELOW" in out, out
    assert f"owned by uid {os.getuid()}, not uid 0" in out, out
    for _, target, _ in _placed_paths(managed):
        assert str(target) in out, f"the refusal does not name {target}\n{out}"
    # The population control on the check itself: the same placement WITH the
    # seam is the green path the other tests take, so ownership is what refused.
    assert _run(sandbox, managed).returncode == 0


def test_a_world_writable_copy_is_re_placed_and_a_world_writable_directory_is_refused(sandbox: Path) -> None:
    """Writability from below, both shapes. A placed file that gains a write
    bit for group or other is re-placed (install -m resets the mode, as it does
    for a stale copy); a managed DIRECTORY that does is refused — a user who
    can write the directory can rename their own copy over the floor, and the
    installer does not silently chmod a directory it did not create."""
    managed = sandbox / "etc"
    assert _run(sandbox, managed).returncode == 0
    _, target, _ = _placed_paths(managed)[0]
    target.chmod(target.stat().st_mode | stat.S_IWOTH)
    run = _run(sandbox, managed)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "re-placed (was stale)" in run.stdout, run.stdout
    assert not target.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH), oct(target.stat().st_mode)

    dropin_dir = target.parent
    dropin_dir.chmod(dropin_dir.stat().st_mode | stat.S_IWOTH)
    try:
        run = _run(sandbox, managed)
    finally:
        dropin_dir.chmod(dropin_dir.stat().st_mode & ~stat.S_IWOTH)
    out = run.stdout + run.stderr
    assert run.returncode == 1, f"exit {run.returncode}: a world-writable managed directory earned the banner\n{out}"
    assert "Managed floor verified" not in out
    assert f"{dropin_dir} — directory REWRITABLE FROM BELOW" in out, out
    assert "group- or world-writable" in out, out


def test_the_owner_seam_is_REFUSED_on_the_live_path_before_anything_is_written(sandbox: Path) -> None:
    """The seam must not be a way to weaken a live install: against the real
    managed directory it is refused outright — before sudo, before any write."""
    run = _run(sandbox, "/etc/claude-code", owner_uid=os.getuid())
    out = run.stdout + run.stderr
    assert run.returncode == 1, out
    assert "MANAGED FLOOR NOT PLACED" in out and "not configurable" in out, out
    assert "CDF_MANAGED_OWNER_UID" in out and "/etc/claude-code" in out, out
    assert "sudo: a password is required" not in out, "the refusal came AFTER an escalation attempt"
    assert not (sandbox / "sudo.log").exists()
    assert "Managed floor verified" not in out


def test_it_REFUSES_LOUDLY_naming_path_and_privilege_when_it_cannot_write(sandbox: Path) -> None:
    """THE REQUIREMENT. Unwritable directory, sudo refuses: non-zero exit and a
    message a human can act on — the resolved path and the privilege lacked."""
    locked = sandbox / "ro"
    locked.mkdir()
    locked.chmod(0o555)
    try:
        run = _run(sandbox, locked)
    finally:
        locked.chmod(0o755)
    assert run.returncode == 1, f"exit {run.returncode}; a refusal must be non-zero\n{run.stdout}{run.stderr}"
    out = run.stdout + run.stderr
    assert "MANAGED FLOOR NOT PLACED" in out
    first_target = _placed_paths(locked)[0][1]
    assert str(first_target) in out, f"the refusal does not name the resolved path {first_target}\n{out}"
    assert "needs: root" in out, out
    assert "sudo: a password is required" in out, "sudo's own reason was dropped from the refusal"
    assert not first_target.exists()
    # The success banner must not appear alongside the refusal.
    assert "Managed floor verified" not in out
    # And the user tier — the guard that DOES fire on such a host — is in place.
    assert (sandbox / "home" / ".claude" / "hooks").is_symlink()


def test_it_uses_sudo_when_the_directory_is_not_writable(sandbox: Path) -> None:
    """The privileged branch is actually reached, with `-n` in non-interactive
    mode so a missing password cannot hang a dispatch."""
    locked = sandbox / "ro"
    locked.mkdir()
    locked.chmod(0o555)
    try:
        run = _run(sandbox, locked, sudo=SUDO_GRANTS)
        log = (sandbox / "sudo.log").read_text() if (sandbox / "sudo.log").exists() else ""
    finally:
        locked.chmod(0o755)
    assert run.returncode == 0, run.stdout + run.stderr
    assert log, "sudo was never invoked, yet the directory was unwritable"
    for line in log.splitlines():
        assert line.startswith("-n install -D -m "), f"unexpected sudo invocation: {line}"
    for source, target, _ in _placed_paths(locked):
        assert target.read_bytes() == source.read_bytes()


# Everything install.sh --non-interactive execs by name when placing the floor.
# Enumerated so the no-sudo test can build a PATH that has all of these and
# NOT sudo; a missing name here shows up as a "command not found" in that test.
_INSTALLER_TOOLS = ("bash", "dirname", "basename", "date", "mkdir", "readlink",
                    "ln", "mv", "cmp", "install", "stat", "id", "which", "jq", "uname")


def test_it_REFUSES_when_sudo_is_not_installed_at_all(sandbox: Path) -> None:
    """A minimal VM image with no sudo must not be read as 'nothing to escalate'."""
    binp = sandbox / "bin"
    for name in _INSTALLER_TOOLS:
        real = shutil.which(name)
        assert real, f"{name} is missing on this host; the installer cannot run here"
        (binp / name).symlink_to(real)
    locked = sandbox / "ro"
    locked.mkdir()
    locked.chmod(0o555)
    env = {"HOME": str(sandbox / "home"), "PATH": str(binp), "CDF_MANAGED_DIR": str(locked)}
    try:
        run = subprocess.run([str(INSTALL), "--non-interactive"], capture_output=True,
                             text=True, timeout=120, env=env)
    finally:
        locked.chmod(0o755)
    out = run.stdout + run.stderr
    assert "command not found" not in out, out
    assert run.returncode == 1, out
    assert "MANAGED FLOOR NOT PLACED" in out and "sudo is not installed" in out, out
    assert str(locked) in out


def test_the_explicit_opt_out_is_loud_and_places_nothing(sandbox: Path) -> None:
    managed = sandbox / "etc"
    run = _run(sandbox, managed, "--without-managed-floor")
    assert run.returncode == 0, run.stdout + run.stderr
    assert "MANAGED FLOOR NOT PLACED — by --without-managed-floor" in run.stdout
    assert not managed.exists()
    assert "Managed floor verified" not in run.stdout


def test_an_override_directory_is_named_as_one_claude_code_will_not_read(sandbox: Path) -> None:
    """The test hook itself must not be mistakable for a live install."""
    managed = sandbox / "etc"
    run = _run(sandbox, managed)
    assert run.returncode == 0
    assert "CDF_MANAGED_DIR overrides the managed directory" in run.stdout
    assert "/etc/claude-code" in run.stdout


def test_the_declared_floor_is_thin_and_its_sources_exist() -> None:
    """The 2026-09-18 ruling: a THIN floor. Every source must be a real file in
    config/, and the list is the safety hook plus the drop-in — a third entry is
    a scope change that needs the ruling re-read, not a silent widening."""
    entries = _floor_entries()
    for src, dst, mode in entries:
        assert (CONFIG / src).is_file(), f"MANAGED_FLOOR names config/{src}, which does not exist"
        assert mode in ("0644", "0755"), (src, mode)
        assert not dst.startswith("/"), f"destination must be relative to the managed dir: {dst}"
    names = sorted(src for src, _, _ in entries)
    assert names == ["hooks/block-dangerous.sh", "managed-settings.d/claude-dot-files.json"], (
        f"the floor is {names}; the ruling put exactly the safety hook and the "
        f"drop-in there. Widening it is an operator ruling, not an edit.")


def test_the_hook_script_is_placed_BEFORE_the_drop_in_that_declares_it() -> None:
    """Entries are placed in array order and a failure on entry N leaves the
    earlier ones on disk, root-owned. So every hook script must precede every
    drop-in: a partial run may leave a script nothing declares (harmless), never
    a declaration of a script that is not there — which Claude Code would read
    from the managed tier on every Bash call on that host."""
    entries = _floor_entries()
    kinds = ["dropin" if dst.endswith(".json") else "hook" for _, dst, _ in entries]
    assert "hook" in kinds and "dropin" in kinds, kinds
    first_dropin = kinds.index("dropin")
    assert "hook" not in kinds[first_dropin:], (
        f"MANAGED_FLOOR order is {[dst for _, dst, _ in entries]}: a hook script is listed "
        f"after a drop-in, so a partial placement can leave a root-owned declaration of a "
        f"script that was never placed. Hooks first.")


def test_a_missing_source_writes_NOTHING_not_a_partial_floor(sandbox: Path, tmp_path: Path) -> None:
    """A copy of the installer whose MANAGED_FLOOR names a source that does not
    exist: the run refuses before the first write, so no entry — in particular
    no drop-in declaring a script — reaches the managed directory. The copy
    sits in a scratch checkout whose `config/` is a symlink to the real one, so
    the user-tier step still has something to link."""
    scratch = tmp_path / "scratch-repo"
    scratch.mkdir()
    (scratch / "config").symlink_to(CONFIG)
    text = INSTALL.read_text()
    marker = "MANAGED_FLOOR=(\n"
    assert text.count(marker) == 1, "install.sh no longer declares MANAGED_FLOOR=( on its own line"
    mutated = text.replace(marker, marker + '    "hooks/does-not-exist.sh:hooks/does-not-exist.sh:0755"\n')
    assert mutated != text
    copy = scratch / "install.sh"
    copy.write_text(mutated)
    copy.chmod(0o755)
    managed = sandbox / "etc"
    (sandbox / "bin" / "sudo").write_text(SUDO_REFUSES)
    (sandbox / "bin" / "sudo").chmod(0o755)
    env = {**os.environ, "HOME": str(sandbox / "home"),
           "PATH": f"{sandbox / 'bin'}:{os.environ['PATH']}", "CDF_MANAGED_DIR": str(managed)}
    run = subprocess.run([str(copy), "--non-interactive"], capture_output=True, text=True,
                         timeout=120, env=env)
    out = run.stdout + run.stderr
    assert run.returncode == 1, out
    assert "source missing from config/" in out and "Nothing was written" in out, out
    assert not managed.exists(), f"a partial floor was written despite a missing source:\n{out}"


def test_a_trailing_slash_on_the_managed_dir_is_normalised(sandbox: Path) -> None:
    """`/etc/claude-code/` must be recognised as `/etc/claude-code`, not warned
    about as a test override — and no placed path may carry a `//`."""
    managed = sandbox / "etc"
    # A raw string: `Path` would strip the slash before the installer ever saw it.
    run = _run(sandbox, str(managed) + "/")
    assert run.returncode == 0, run.stdout + run.stderr
    assert "//" not in run.stdout.replace("://", ""), run.stdout
    assert f"Managed floor verified at {managed}." in run.stdout, run.stdout


def test_sudo_stub_shape_matches_what_this_host_has() -> None:
    """The control on the control: the stubs replace tools by NAME on PATH, so
    if install.sh stopped calling `sudo` and called `doas`, every refusal test
    above would pass against a tool that was never consulted."""
    # The NAME only. Whether it is invoked with `-n` is behaviour, and
    # `test_it_uses_sudo_when_the_directory_is_not_writable` proves that by
    # running it; a grep for the flag here would be a second copy of that claim.
    assert re.search(r"\bsudo\b", INSTALL.read_text()), "install.sh no longer names sudo; the stubs guard nothing"
    assert shutil.which("cmp") and shutil.which("install"), "the installer's real tools are missing on this host"

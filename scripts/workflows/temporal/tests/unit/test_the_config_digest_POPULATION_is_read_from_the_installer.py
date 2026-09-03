"""The digest's population comes off `install.sh`, and is never a copy of it.

WORKFLOW DECOMPOSITION PHASE 5 r2, AND THE CHECK THE PHASE ASKS FOR BY NAME:
*"add the check that fails when the digest's population and the installer's
disagree."*

⚠ THE OBVIOUS VERSION OF THAT CHECK CANNOT FAIL, AND SAYING SO IS THE POINT.
`config_digest` READS `SYMLINK_TARGETS` at digest time, so comparing "what the
module used" against "what the installer declares" compares one value with
itself — a test that can only ever pass. The disagreement the phase is worried
about is a FUTURE one: a maintainer replacing the read with a literal list
because the parse felt awkward. So the check that can actually go red is
`test_this_module_HOLDS_NO_COPY_of_the_installer_set`, which reads the digest
module's own source and fails if the seven target names appear in it as
literals, plus the independent re-derivation below which parses the installer a
second way and compares.

WHAT THESE GUARDS DO NOT LOOK AT, stated because a control that never names its
blind spot reads as broader than it is:

  * They do not check that `~/.claude/` actually CONTAINS what `install.sh`
    links. A machine where the installer was never run digests seven absent
    targets and these tests pass — correctly, because *absent* is a fact the tag
    records rather than an error.
  * They do not check that the installer's set is the RIGHT set. Two open
    candidates (`C-idwrru3n`, `C-7ymfdw28`) propose changing it; whichever wins,
    these tests follow it silently, which is the whole design.
  * They say nothing about the CONTENT of any hashed file.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "workflows" / "temporal"))

from modules.journal.config_digest import (  # noqa: E402
    DIGEST_ALGORITHM, ConfigDigestError, claude_config_dir, config_digest,
    installer_targets, parse_symlink_targets, parse_tag_value,
    unavailable_tag_value)

INSTALL_SH = REPO_ROOT / "install.sh"
DIGEST_MODULE = (REPO_ROOT / "scripts" / "workflows" / "temporal" / "modules"
                 / "journal" / "config_digest.py")


def _targets_via_bash() -> list[str]:
    """The installer's set, re-derived by BASH ITSELF rather than by our regex.

    A SECOND, INDEPENDENT DERIVATION. Comparing our parser against our parser
    proves nothing; sourcing the array in the shell that actually consumes it is
    the only reading with authority, because bash is what `install.sh` runs
    under. If the two ever disagree, our regex is wrong about the file the
    installer is really using.
    """
    script = (f'set -euo pipefail\n'
              f'SYMLINK_TARGETS=()\n'
              f'eval "$(sed -n "/^SYMLINK_TARGETS=(/,/^)/p" {INSTALL_SH})"\n'
              f'printf "%s\\n" "${{SYMLINK_TARGETS[@]}}"\n')
    out = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                         timeout=30)
    assert out.returncode == 0, f"bash could not read the array: {out.stderr}"
    return sorted(line for line in out.stdout.splitlines() if line)


def test_the_installer_set_is_READ_and_matches_bash_s_own_reading() -> None:
    ours = installer_targets(INSTALL_SH)
    theirs = _targets_via_bash()
    assert ours, "an empty population would make every later assertion vacuous"
    assert ours == theirs, (
        f"the digest's population and the installer's disagree.\n"
        f"  parsed here : {ours}\n"
        f"  parsed by bash: {theirs}\n"
        f"The population is READ from install.sh and never copied, so a "
        f"mismatch means this module's parser is wrong about the file the "
        f"installer actually runs.")


def test_this_module_HOLDS_NO_COPY_of_the_installer_set() -> None:
    """The one guard here that a future edit can actually turn red.

    It fails when a maintainer replaces the read with a literal list — the
    hand-kept-population defect the phase forbids by name. The docstring names
    the targets in prose, deliberately, so the check looks for the QUOTED
    literal form a Python list would use rather than for the bare words.
    """
    source = DIGEST_MODULE.read_text(encoding="utf-8")
    targets = installer_targets(INSTALL_SH)
    # NON-ZERO COUNT EXAMINED. A sweep whose population is empty passes while
    # inspecting nothing, and would then certify a module it never opened.
    assert len(targets) >= 2, (
        f"only {len(targets)} target(s) to look for — this guard would pass "
        f"vacuously")
    assert source.strip(), "the digest module's source was not read"
    quoted = [t for t in targets
              if f'"{t}"' in source or f"'{t}'" in source]
    assert not quoted, (
        f"config_digest.py contains the installer's target names as string "
        f"literals: {quoted}. The population is READ from install.sh; a copy "
        f"cannot see a target added to the installer and never added here, "
        f"which makes the digest answer confidently about a set nobody syncs.")


def test_the_parse_REFUSES_a_file_with_no_array() -> None:
    with pytest.raises(ConfigDigestError, match="no SYMLINK_TARGETS"):
        parse_symlink_targets("#!/usr/bin/env bash\nCLAUDE_DIR=$HOME/.claude\n")


def test_the_parse_REFUSES_an_empty_array_rather_than_digesting_nothing() -> None:
    """An empty population is refused, not hashed.

    The hash of nothing is a real value, so digesting an empty set would write a
    confident-looking tag claiming a run absorbed no configuration — when what
    actually happened is that the set could not be established.
    """
    with pytest.raises(ConfigDigestError, match="EMPTY array"):
        parse_symlink_targets('SYMLINK_TARGETS=(\n)\n')


def test_a_COMMENTED_OUT_entry_is_not_in_the_population() -> None:
    """A target the installer does not link must not be in the digest.

    `# "plugins"` inside the array is a decision NOT to sync something. Hashing
    it would put files in the population that no symlink puts in `~/.claude/`.
    """
    parsed = parse_symlink_targets(
        'SYMLINK_TARGETS=(\n    "agents"\n    # "plugins"\n    "rules"\n)\n')
    assert parsed == ["agents", "rules"]


def test_the_parse_REFUSES_an_entry_that_ESCAPES_a_path_segment() -> None:
    with pytest.raises(ConfigDigestError, match="single path segment"):
        parse_symlink_targets('SYMLINK_TARGETS=(\n    "../../etc"\n)\n')


def test_a_MISSING_installer_is_refused_rather_than_defaulted() -> None:
    with pytest.raises(ConfigDigestError, match="could not be read"):
        installer_targets(REPO_ROOT / "install.sh.does-not-exist")


# --------------------------------------------------------------------------
# The digest itself
# --------------------------------------------------------------------------

INSTALLER = 'SYMLINK_TARGETS=(\n    "settings.json"\n    "agents"\n)\n'


@pytest.fixture()
def fixture(tmp_path: Path) -> tuple[Path, Path]:
    """A self-contained installer + config tree.

    SELF-CONTAINED ON PURPOSE. A control that shares a fixture with the code it
    mutates over-fires: breaking the shared thing fails tests that were never
    about it. Nothing here reads the repo's own `install.sh` or `~/.claude`.
    """
    install_sh = tmp_path / "install.sh"
    install_sh.write_text(INSTALLER)
    cdir = tmp_path / "claude"
    (cdir / "agents").mkdir(parents=True)
    (cdir / "settings.json").write_text('{"model":"opus"}')
    (cdir / "agents" / "reviewer.md").write_text("you review code")
    return install_sh, cdir


def test_the_same_bytes_produce_the_SAME_digest(fixture) -> None:
    install_sh, cdir = fixture
    first = config_digest(claude_dir=cdir, install_sh=install_sh)
    second = config_digest(claude_dir=cdir, install_sh=install_sh)
    assert first.digest == second.digest
    assert first.targets == ("agents", "settings.json")
    assert first.absent == () and first.unreadable == ()


def test_ONE_CHANGED_BYTE_changes_the_digest(fixture) -> None:
    install_sh, cdir = fixture
    before = config_digest(claude_dir=cdir, install_sh=install_sh).digest
    (cdir / "agents" / "reviewer.md").write_text("you review codE")
    after = config_digest(claude_dir=cdir, install_sh=install_sh).digest
    assert before != after, (
        "an edit to a synced file must change the digest — that is the entire "
        "property the tag exists to record")


def test_a_file_ADDED_under_a_target_changes_the_digest(fixture) -> None:
    """The mid-flight edit this phase was written about is usually an ADD."""
    install_sh, cdir = fixture
    before = config_digest(claude_dir=cdir, install_sh=install_sh).digest
    (cdir / "agents" / "new-agent.md").write_text("you do something new")
    assert config_digest(claude_dir=cdir, install_sh=install_sh).digest != before


def test_ABSENT_and_EMPTY_are_DISTINGUISHABLE(fixture) -> None:
    """The two cases an operator most needs told apart must not collide.

    A target that was never installed and a target installed but empty would
    hash identically if absence contributed nothing to the manifest.
    """
    install_sh, cdir = fixture
    for child in (cdir / "agents").iterdir():
        child.unlink()
    empty = config_digest(claude_dir=cdir, install_sh=install_sh)
    (cdir / "agents").rmdir()
    absent = config_digest(claude_dir=cdir, install_sh=install_sh)

    assert empty.absent == () and empty.digest
    assert absent.absent == ("agents",)
    assert empty.digest != absent.digest, (
        "an absent target and an empty one produced the same digest — a "
        "machine missing agents/ would be indistinguishable from one whose "
        "agents/ is empty")


def test_a_run_with_NO_readable_configuration_still_gets_a_real_digest(
        tmp_path: Path) -> None:
    """Phase 5's *"records that rather than omitting"*, at the digest layer.

    Nothing installed at all is still a describable state: every target absent.
    """
    install_sh = tmp_path / "install.sh"
    install_sh.write_text(INSTALLER)
    result = config_digest(claude_dir=tmp_path / "nothing-here",
                           install_sh=install_sh)
    assert result.absent == ("agents", "settings.json")
    assert len(result.digest) == 64
    assert "absent=agents,settings.json" in result.tag_value()


def _unreadable_here(path: Path) -> bool:
    """True when this account really cannot open `path` after chmod 000.

    THE FILE-LEVEL TWIN OF `_hidden()` BELOW, and it exists for the same reason:
    a skip predicate must be a statement about the MACHINE. Root opens a mode-000
    file happily, so the skip is real on a root runner and must not be reachable
    on any other — and the only way to know which is to drive the syscall on the
    actual path rather than to read back what the code under test concluded.
    """
    try:
        path.read_bytes()
    except OSError:
        return True
    return False


def test_an_UNREADABLE_file_is_recorded_as_a_hole_not_skipped(fixture) -> None:
    """One unreadable file makes the whole target a reported hole.

    Reporting it only when EVERY file failed would let the common case — one
    root-owned file in an otherwise readable tree — pass as clean.

    ⚠ THE SKIP USED TO BE PREDICATED ON THE CODE'S OWN OUTPUT — `if
    result.unreadable == (): pytest.skip("running as … root")` — WHICH IS WORSE
    THAN VACUOUS. Deleting `unreadable = True` from `_lines_for_target`'s per-file
    `except OSError` turned this guard into `1 skipped` with a reason claiming
    this account can read mode-000 files, measured as uid 1001, where it could
    not. A regression that stops reporting unreadable files would have shipped
    green. The machine is probed instead, exactly as `_hidden()` below does for
    the directory cases, so the only thing that can turn this yellow is a fact
    about the machine and the only thing that can turn it green is the assertion.
    """
    install_sh, cdir = fixture
    locked = cdir / "agents" / "reviewer.md"
    locked.chmod(0o000)
    try:
        if not _unreadable_here(locked):
            pytest.skip("running as a user that can read mode-000 files (root)")
        result = config_digest(claude_dir=cdir, install_sh=install_sh)
    finally:
        locked.chmod(0o644)
    assert result.unreadable == ("agents",)
    assert "unreadable=agents" in result.tag_value()


def test_CLAUDE_CONFIG_DIR_names_the_tree_the_run_actually_absorbed(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "elsewhere"))
    assert claude_config_dir() == tmp_path / "elsewhere"
    monkeypatch.delenv("CLAUDE_CONFIG_DIR")
    monkeypatch.setenv("HOME", str(tmp_path))
    assert claude_config_dir() == tmp_path / ".claude"


# --------------------------------------------------------------------------
# The tag value — requirement 2's "written down BESIDE the tag"
# --------------------------------------------------------------------------

def test_the_tag_value_CARRIES_its_own_population(fixture) -> None:
    """A reader must recover the inputs without holding this module's source."""
    install_sh, cdir = fixture
    value = config_digest(claude_dir=cdir, install_sh=install_sh).tag_value()
    digest, fields = parse_tag_value(value)
    assert digest and len(digest) == 64
    assert fields["targets"] == ("agents", "settings.json")
    assert fields["absent"] == () and fields["unreadable"] == ()
    assert value.startswith(f"{DIGEST_ALGORITHM}:")


def test_the_tag_value_IS_ONE_LINE(fixture) -> None:
    """A value with a newline forges a second tag line in `bag-info.txt`."""
    install_sh, cdir = fixture
    (cdir / "agents" / "odd name with spaces.md").write_text("x")
    value = config_digest(claude_dir=cdir, install_sh=install_sh).tag_value()
    assert "\n" not in value and "\r" not in value


def test_the_UNAVAILABLE_value_takes_a_SLUG_and_refuses_free_text() -> None:
    """A reason composed from an exception's text could forge a tag line."""
    assert parse_tag_value(unavailable_tag_value("no-installer")) == (
        None, {"reason": ("no-installer",)})
    with pytest.raises(ConfigDigestError, match="reason slug"):
        unavailable_tag_value("could not read it\nJournal-Incomplete: true")
    # ⚠ THE TRAILING-NEWLINE CASE IS THE ONE THAT WAS LIVE, and the case above
    # does NOT exercise it: without `re.MULTILINE` a `$` does not match at an
    # INTERIOR newline, so the `^…$` form this pattern used to have refused that
    # string too and the test passed against the defect. `$` DOES match before a
    # trailing newline, which is what `\A`/`\Z` closes. Written after the
    # mutation of `_SEGMENT_RE` failed to turn this test red.
    with pytest.raises(ConfigDigestError, match="reason slug"):
        unavailable_tag_value("no-installer\n")


def test_a_tag_value_from_an_UNKNOWN_algorithm_reads_as_no_digest() -> None:
    """Forward compatibility: a future algorithm is UNKNOWN, never a match.

    Reading an unparseable head as a digest would let two bags written under
    different algorithms compare equal on their raw text.
    """
    digest, _ = parse_tag_value("md5:abc targets=agents absent=none")
    assert digest is None


def test_the_MANIFEST_does_not_depend_on_directory_read_ORDER(
        fixture, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sorted before hashing, or every pair of runs reports as divergent.

    ⚠ THIS TEST USED TO BUILD TWO TREES, creating the same names in opposite
    orders, and it was VACUOUS — measured, not suspected. Deleting
    `sorted(filenames)` from the walk left it green, because ext4 enumerates a
    directory by name-hash rather than by creation order, so both trees came
    back in the same order and the test never saw an unsorted one. The fixture
    was symmetric under the very defect it was written for.

    So the read order is now IMPOSED rather than hoped for: `os.walk` is wrapped
    to hand back reversed filenames, and the digest must be unchanged. That
    tests the property the code claims — *sorted before hashing* — instead of
    testing what this filesystem happens to do.
    """
    install_sh, cdir = fixture
    for name in ("a.md", "b.md", "c.md", "d.md"):
        (cdir / "agents" / name).write_text(name)

    natural = config_digest(claude_dir=cdir, install_sh=install_sh).digest

    real_walk = os.walk

    def reversed_walk(*args, **kwargs):
        for dirpath, dirnames, filenames in real_walk(*args, **kwargs):
            yield dirpath, dirnames, list(reversed(filenames))

    # Patched on `os` itself: the module under test does `import os` and
    # calls `os.walk`, so this is the same object it resolves.
    monkeypatch.setattr(os, "walk", reversed_walk)
    imposed = config_digest(claude_dir=cdir, install_sh=install_sh).digest

    assert imposed == natural, (
        "the digest changed when the directory was enumerated in a different "
        "order. Two machines holding identical bytes would then report as "
        "divergent on every comparison.")


def test_the_regex_reads_the_DECLARATION_not_an_EXPANSION() -> None:
    """`"${SYMLINK_TARGETS[@]}"` in a loop is not a declaration.

    install.sh mentions the name three times; only the first is the array.
    """
    assert len(re.findall(r"SYMLINK_TARGETS",
                          INSTALL_SH.read_text(encoding="utf-8"))) > 1
    assert installer_targets(INSTALL_SH) == _targets_via_bash()


# --------------------------------------------------------------------------
# The holes the walk itself can fall into — added by the build-refine pass
# --------------------------------------------------------------------------

def _hidden(path: Path) -> bool:
    """True when this account really cannot list `path` after chmod 000.

    ⚠ A SKIP WHOSE REASON IS DERIVED, SO IT IS DERIVED FROM THE ACTUAL TREE. Root
    reads a mode-000 directory happily, and a skip asserting "this machine cannot"
    while the machine can is a green result that checked nothing. This drives the
    real syscall on the real path rather than inspecting `os.geteuid()`.
    """
    try:
        os.listdir(path)
    except OSError:
        return True
    return False


def test_an_UNLISTABLE_TARGET_is_a_hole_and_not_an_empty_directory(
        fixture) -> None:
    """⚠ THE CASE THE MODULE'S OWN DOCSTRING NAMES, AND IT USED TO COLLIDE.

    `os.walk` reports a directory it cannot open through `onerror` and then
    yields nothing for it. While that callback discarded the error, a target
    behind a permission wall contributed exactly what an empty one contributes
    — so *"a machine that hides `hooks/` behind a permission wall hashes
    identically to one that never had it"* was true of the code that promised
    the opposite. Measured, not suspected: both digests were
    `01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b`.
    """
    install_sh, cdir = fixture
    (cdir / "agents" / "secret.md").write_text("something is in here")
    (cdir / "agents").chmod(0o000)
    try:
        if not _hidden(cdir / "agents"):
            pytest.skip("running as a user that can list mode-000 directories")
        walled = config_digest(claude_dir=cdir, install_sh=install_sh)
    finally:
        (cdir / "agents").chmod(0o755)

    for child in (cdir / "agents").iterdir():
        child.unlink()
    empty = config_digest(claude_dir=cdir, install_sh=install_sh)

    assert walled.unreadable == ("agents",), (
        "a target that could not be LISTED must be reported as a hole — "
        "reporting only unreadable FILES leaves the whole-directory case silent")
    assert empty.unreadable == ()
    assert walled.digest != empty.digest, (
        "a permission-walled target hashed identically to an empty one — the "
        "exact collision this module's docstring promises to prevent")


def test_an_UNLISTABLE_SUBDIRECTORY_is_a_hole_and_not_an_absence(
        fixture) -> None:
    """The same defect one level down, where it is likelier and quieter.

    A whole subtree vanishing from the manifest reads as *this machine never had
    that directory* — and nothing in `absent=` or `unreadable=` said otherwise.
    """
    install_sh, cdir = fixture
    private = cdir / "agents" / "private"
    private.mkdir()
    (private / "one.md").write_text("s1")
    (private / "two.md").write_text("s2")
    private.chmod(0o000)
    try:
        if not _hidden(private):
            pytest.skip("running as a user that can list mode-000 directories")
        walled = config_digest(claude_dir=cdir, install_sh=install_sh).digest
        holes = config_digest(claude_dir=cdir, install_sh=install_sh).unreadable
    finally:
        private.chmod(0o755)
    for child in private.iterdir():
        child.unlink()
    private.rmdir()
    without = config_digest(claude_dir=cdir, install_sh=install_sh).digest

    assert holes == ("agents",)
    assert walled != without, (
        "a subdirectory the run could not enter hashed identically to one that "
        "was never there")


def test_a_NON_UTF8_INSTALLER_is_a_ConfigDigestError_and_not_a_ValueError(
) -> None:
    """⚠ `UnicodeDecodeError` IS A `ValueError`, SO `except OSError` NEVER SAW IT.

    It escaped this module, escaped `_config_digest_value`'s
    `except ConfigDigestError`, and came out of `open_run_bag` — meaning one bad
    byte in `install.sh` stopped every dispatch on the machine before any of them
    could open a bag. The design says an unestablishable population is one
    unknown fact and never a reason a run may not proceed; this asserts that
    rather than trusting the docstring which already said it.
    """
    import tempfile
    bad = Path(tempfile.mkdtemp()) / "install.sh"
    bad.write_bytes(b'SYMLINK_TARGETS=(\n    "agents"\xff\n)\n')
    with pytest.raises(ConfigDigestError, match="not valid UTF-8"):
        installer_targets(bad)


# --------------------------------------------------------------------------
# The exception classes NO handler named — added by the correction pass.
#
# The refine pass before this one fixed three undesigned error paths and the
# review that followed reproduced four more of the identical shape by execution.
# The meta-pattern is the finding: the DESIGNED failures (absent target,
# unreadable file, missing installer) were covered thoroughly and the undesigned
# ones were covered not at all, so each fix below is paired with a case that
# drives it rather than a docstring that asserts it.
# --------------------------------------------------------------------------

def _surrogate_name() -> str:
    """A filename that is real on disk and is not valid UTF-8.

    `os.walk` hands undecodable names back with lone surrogates in them, which
    is what `str.encode("utf-8")` refuses. Built from the bytes rather than
    written as a literal so the test is about the encoding boundary rather than
    about this file's own encoding.
    """
    return b"bad_\xff.md".decode("utf-8", "surrogateescape")


def test_a_NON_UTF8_FILENAME_under_a_target_is_HASHED_and_does_not_raise(
        fixture) -> None:
    """⚠ IT RAISED `UnicodeEncodeError`, WHICH IS A `ValueError`, SO NOTHING CAUGHT IT.

    Measured before the fix: `config_digest()` over a tree holding one such file
    raised out of this module, past `_config_digest_value`'s
    `except ConfigDigestError`, past `open_run_bag`'s `except OSError`, and past
    the entrypoints' `(RuntimeError, FileNotFoundError)` — a raw traceback and no
    bag written, for a filename. The contract says an unestablishable population
    is one unknown fact and never a reason a run may not proceed; a file the run
    genuinely CAN read is not even that, so it must simply be hashed.
    """
    install_sh, cdir = fixture
    before = config_digest(claude_dir=cdir, install_sh=install_sh).digest
    (cdir / "agents" / _surrogate_name()).write_bytes(b"an undecodable name")

    result = config_digest(claude_dir=cdir, install_sh=install_sh)
    assert len(result.digest) == 64
    assert result.unreadable == (), (
        "the file is readable — only its NAME is undecodable, and treating that "
        "as a hole would report a fault where there is none")
    assert result.digest != before, (
        "a file added under a target must change the digest whatever its name "
        "decodes to")
    assert config_digest(claude_dir=cdir, install_sh=install_sh).digest == \
        result.digest, "the surrogate round-trip must be stable across calls"


def test_a_LISTABLE_BUT_UNSEARCHABLE_directory_is_a_HOLE_and_not_a_raise(
        fixture) -> None:
    """Mode 444: readable, so `os.walk` lists it; not searchable, so `lstat` fails.

    ⚠ THE ADJACENT PERMISSION SHAPE ONE BIT OVER WAS ALREADY CORRECT, WHICH IS
    WHAT MAKES THIS A DEFECT RATHER THAN A JUDGEMENT CALL. Mode 000 on the same
    directory is reported as `unreadable=agents` through `_record_unlistable`.
    At 444 `os.walk` succeeded, reported the children, and the unguarded
    `Path.is_symlink()` on one of them raised `PermissionError` — which
    `open_run_bag`'s `except OSError` then rewrote into a `JournalRootError`
    about free space under the JOURNAL ROOT. A false diagnosis, pointing at a
    different filesystem from the one with the problem.
    """
    install_sh, cdir = fixture
    walled = cdir / "agents" / "half-open"
    (walled / "inner").mkdir(parents=True)
    (walled / "inner" / "one.md").write_text("s1")
    walled.chmod(0o444)
    try:
        if _listable_but_unsearchable(walled) is not True:
            pytest.skip("this account can search a mode-444 directory (root)")
        result = config_digest(claude_dir=cdir, install_sh=install_sh)
    finally:
        walled.chmod(0o755)

    assert result.unreadable == ("agents",), (
        "a child that could not be stat-ed is a hole in the digest and must be "
        "reported as one — the alternative measured here was an exception that "
        "aborted the whole dispatch")


def _listable_but_unsearchable(path: Path) -> bool:
    """True when this account can list `path` at 444 but cannot stat its children.

    THE MACHINE IS PROBED, NEVER THE RESULT — the rule `_hidden()` states and the
    one this file's skip predicate broke. Root satisfies neither half, so it skips
    on the fact rather than on the outcome of the code under test.
    """
    try:
        children = os.listdir(path)
    except OSError:
        return False
    for name in children:
        try:
            (path / name).lstat()
        except OSError:
            return True
    return False


def test_the_TREE_LOCATION_being_unknowable_is_the_MODULE_S_OWN_ERROR_CLASS(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """⚠ `ConfigDigestError` SUBCLASSES `RuntimeError`, SO IT CANNOT CATCH ITS PARENT.

    With `HOME` unset and the uid absent from `/etc/passwd` — an ordinary
    container shape — `Path.home()` raises a BARE `RuntimeError("Could not
    determine home directory.")`. The caller's `except ConfigDigestError` does not
    catch it, so the dispatch was refused with a five-word message and no remedy.
    The inheritance direction is the whole trap and it is the reason this is
    tested rather than reasoned about.
    """
    def no_home() -> Path:
        raise RuntimeError("Could not determine home directory.")

    monkeypatch.setattr(Path, "home", staticmethod(no_home))
    with pytest.raises(ConfigDigestError) as exc:
        claude_config_dir(env={})
    assert "unavailable" in str(exc.value)
    assert not type(exc.value) is RuntimeError, (
        "a BARE RuntimeError is what escaped the caller's handler; the point of "
        "the fix is that the class is this module's own")


def test_a_FIFO_under_a_target_does_not_PARK_the_walk(tmp_path: Path) -> None:
    """⚠ VERIFIED BY EXECUTION AS `timeout 8` -> EXIT 124, i.e. it never returned.

    `os.walk` sorts FIFOs, device nodes and sockets into `filenames`, and
    `sha256_of` opened them with a plain `open()`. A FIFO with no writer blocks
    forever and there is no timeout anywhere in the chain — so a run parked
    before it had opened its bag, which is the one failure the journal cannot
    describe. The module docstring already promised only *"every regular file"*.

    RUN IN A SUBPROCESS WITH A TIMEOUT, deliberately: an in-process regression
    would HANG this suite rather than fail it, and a guard that converts a defect
    into an unbounded wait is not a guard.
    """
    install_sh = tmp_path / "install.sh"
    install_sh.write_text(INSTALLER)
    cdir = tmp_path / "claude"
    (cdir / "agents").mkdir(parents=True)
    (cdir / "settings.json").write_text("{}")
    (cdir / "agents" / "real.md").write_text("a regular file")

    plain = _digest_in_a_subprocess(cdir, install_sh)
    os.mkfifo(cdir / "agents" / "pipe")
    with_fifo = _digest_in_a_subprocess(cdir, install_sh)

    assert with_fifo != plain, (
        "a FIFO appearing under a target must change the digest — it is part of "
        "what is there, even though its bytes are not read")


def test_a_DANGLING_SYMLINK_is_a_hole_and_a_SYMLINK_TO_A_FILE_is_hashed(
        fixture) -> None:
    """The two halves of the regularity check, which pull in opposite directions.

    A symlink to a file IS read and its bytes ARE what the run absorbed, so it is
    hashed — that asymmetry with `symlinked-dir` was re-examined at review and
    stands. A symlink pointing at nothing can be stat-ed no further, so nothing
    about it is knowable and it is a hole. A single `S_ISREG` check on `lstat`
    alone would have got the first of these wrong.
    """
    install_sh, cdir = fixture
    (cdir / "elsewhere.md").write_text("borrowed content")
    (cdir / "agents" / "link.md").symlink_to(cdir / "elsewhere.md")
    linked = config_digest(claude_dir=cdir, install_sh=install_sh)
    assert linked.unreadable == ()

    (cdir / "elsewhere.md").write_text("borrowed content, edited")
    assert config_digest(claude_dir=cdir, install_sh=install_sh).digest != \
        linked.digest, "a symlinked file's BYTES are what the run absorbed"

    (cdir / "agents" / "dangling.md").symlink_to(cdir / "no-such-file.md")
    dangling = config_digest(claude_dir=cdir, install_sh=install_sh)
    assert dangling.unreadable == ("agents",), (
        "a symlink pointing at nothing cannot be read and cannot be classified, "
        "so it is a hole rather than a silence")


def _digest_in_a_subprocess(cdir: Path, install_sh: Path) -> str:
    """`config_digest(...).digest`, computed where a hang is a FAILURE."""
    source = (
        "import sys; sys.path.insert(0, %r)\n"
        "from pathlib import Path\n"
        "from modules.journal.config_digest import config_digest\n"
        "print(config_digest(claude_dir=Path(%r), install_sh=Path(%r)).digest)\n"
        % (str(REPO_ROOT / "scripts" / "workflows" / "temporal"),
           str(cdir), str(install_sh)))
    out = subprocess.run([sys.executable, "-c", source], capture_output=True,
                         text=True, timeout=30)
    assert out.returncode == 0, f"{out.stdout}{out.stderr}"
    return out.stdout.strip()


# --------------------------------------------------------------------------
# The DECLARED POPULATION is part of what is hashed
# --------------------------------------------------------------------------

def test_TWO_INSTALLERS_over_ONE_TREE_do_not_produce_the_same_digest(
        tmp_path: Path) -> None:
    """⚠ THEY DID, AND THE READER THEN PRINTED `SAME` WHILE RENDERING THE DIFFERENCE.

    The manifest recorded each target's byte-effects and never the declared SET,
    so `{agents}` and `{agents, plugins}` over one tree — with `plugins/` present
    and empty — hashed identically. `compare_run_config` compares digests alone,
    so it exited 0 and printed SAME two lines above its own `targets:` lines
    showing the two different populations. That defeats requirement 2's reason
    for carrying the population at all.

    THE FIXTURE IS ASYMMETRIC UNDER THE DEFECT ON PURPOSE: `plugins/` is present
    and EMPTY, which is the only shape in which the byte-effects of the two
    populations coincide. An absent or non-empty `plugins/` would have differed
    for the wrong reason and the test would have passed against the defect.
    """
    cdir = tmp_path / "claude"
    (cdir / "agents").mkdir(parents=True)
    (cdir / "agents" / "reviewer.md").write_text("you review code")
    (cdir / "plugins").mkdir()

    narrow = tmp_path / "narrow.sh"
    narrow.write_text('SYMLINK_TARGETS=(\n    "agents"\n)\n')
    wide = tmp_path / "wide.sh"
    wide.write_text('SYMLINK_TARGETS=(\n    "agents"\n    "plugins"\n)\n')

    a = config_digest(claude_dir=cdir, install_sh=narrow)
    b = config_digest(claude_dir=cdir, install_sh=wide)
    assert a.targets == ("agents",) and b.targets == ("agents", "plugins")
    assert a.digest != b.digest, (
        "two runs whose installers declared different populations produced the "
        "same digest — the reader compares digests alone, so it would call them "
        "SAME while printing the two different target lists")


# --------------------------------------------------------------------------
# What the installer may legally declare
# --------------------------------------------------------------------------

def test_a_DOTFILE_target_is_a_LEGAL_SEGMENT_and_dot_and_dotdot_are_not() -> None:
    """⚠ REFUSING A LEADING DOT SILENTLY DISABLED THE COMPONENT FLEET-WIDE.

    `_SEGMENT_RE` demanded a leading alphanumeric although the only thing it is
    there to refuse is a value that ESCAPES a path segment. `.mcp.json` is a real
    Claude Code config file and an obvious future entry; adding it made
    `parse_symlink_targets` raise for the WHOLE array, `_config_digest_value`
    swallowed that, and every bag on every machine recorded `unavailable` with
    nothing going red. The two values that genuinely escape a segment are refused
    by name, which is what the stated justification actually supports.
    """
    assert parse_symlink_targets(
        'SYMLINK_TARGETS=(\n    ".mcp.json"\n    "agents"\n)\n') == \
        [".mcp.json", "agents"]
    for escaping in (".", ".."):
        with pytest.raises(ConfigDigestError, match="single path segment"):
            parse_symlink_targets(f'SYMLINK_TARGETS=(\n    "{escaping}"\n)\n')


def test_an_UNQUOTED_bash_array_is_READ_rather_than_called_EMPTY() -> None:
    """An unquoted array is legal, idiomatic bash, and it read as seven-is-zero.

    The entry pattern matched only quoted entries, so `SYMLINK_TARGETS=(agents
    rules)` yielded nothing and was reported as *"declares SYMLINK_TARGETS as an
    EMPTY array"* — false when it declares two, and the message's own reasoning
    ("the installer could not be read for its set") does not apply to a set
    sitting in plain view. A truly empty array still says so.
    """
    assert parse_symlink_targets(
        'SYMLINK_TARGETS=(\n    agents\n    rules\n)\n') == ["agents", "rules"]
    assert parse_symlink_targets(
        "SYMLINK_TARGETS=(\n    'agents'\n    'rules'\n)\n") == ["agents", "rules"]
    with pytest.raises(ConfigDigestError, match="EMPTY array"):
        parse_symlink_targets("SYMLINK_TARGETS=(\n)\n")
    # A bare word that is NOT a segment is now REACHED rather than skipped, and
    # the message names it instead of claiming the array is empty.
    with pytest.raises(ConfigDigestError, match="single path segment"):
        parse_symlink_targets('SYMLINK_TARGETS=(\n    "${OTHER[@]}"\n)\n')


def test_a_value_named_none_is_REFUSED_because_it_does_not_ROUND_TRIP() -> None:
    """`none` is the sentinel a list field with no members serializes to.

    A target actually called `none` would compose to `targets=none`, which
    `parse_tag_value` reads back as the EMPTY tuple — so a reader would be told a
    run absorbed nothing when it absorbed one target. Refused at both places a
    value enters the serialization, because the collision belongs to the format
    rather than to either caller.
    """
    with pytest.raises(ConfigDigestError, match="sentinel"):
        parse_symlink_targets('SYMLINK_TARGETS=(\n    "none"\n)\n')
    with pytest.raises(ConfigDigestError, match="sentinel"):
        unavailable_tag_value("none")


def test_a_target_DECLARED_TWICE_is_counted_once() -> None:
    """`sorted(set(...))`, driven. A duplicated entry is a maintenance accident,
    not a second population member, and hashing it twice would make the digest
    depend on how many times somebody typed a line."""
    assert parse_symlink_targets(
        'SYMLINK_TARGETS=(\n    "agents"\n    "rules"\n    "agents"\n)\n') == \
        ["agents", "rules"]


# --------------------------------------------------------------------------
# Where the tree is
# --------------------------------------------------------------------------

def test_CLAUDE_CONFIG_DIR_is_EXPANDED_rather_than_taken_literally(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """`~/elsewhere` names a directory; a literal `./~/elsewhere` names nothing.

    An unexpanded override would send the walk somewhere that does not exist, and
    every target would be reported absent — a confident tag about a tree nobody
    read, which is the shape this module exists to refuse.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "~/elsewhere")
    assert claude_config_dir() == tmp_path / "elsewhere"


def test_the_tree_falls_back_to_the_ACCOUNT_S_HOME_when_no_variable_is_set(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Neither variable set: the account's own home, from the passwd database."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "fromapasswd"))
    assert claude_config_dir(env={}) == tmp_path / "fromapasswd" / ".claude"


def test_claude_config_dir_READS_THE_MAPPING_IT_IS_GIVEN() -> None:
    """The `env=` parameter is the injectable seam and it must actually inject.

    Every other test here reaches it through `monkeypatch.setenv`, so nothing
    exercised the parameter itself — and a future caller passing `env=` while the
    body silently read `os.environ` would get an answer about the wrong process.
    """
    assert claude_config_dir(env={"CLAUDE_CONFIG_DIR": "/somewhere/injected"}) == \
        Path("/somewhere/injected")


# --------------------------------------------------------------------------
# The holes the walk itself can fall into — the paths whose handlers exist
# --------------------------------------------------------------------------

def test_a_CONFIG_ROOT_that_cannot_be_STATTED_is_a_hole_for_every_target(
        fixture) -> None:
    """The target-level `except OSError`, which nothing drove.

    A config root the account cannot search fails `path.exists()` for every
    target with `PermissionError`. Contributing an empty list there would make a
    permission-walled machine hash identically to one with nothing installed —
    the same collision as the directory case one level down, at the top.
    """
    install_sh, cdir = fixture
    absent = config_digest(claude_dir=cdir.parent / "nothing-here",
                           install_sh=install_sh)
    cdir.chmod(0o000)
    try:
        if not _hidden(cdir):
            pytest.skip("running as a user that can search mode-000 directories")
        walled = config_digest(claude_dir=cdir, install_sh=install_sh)
    finally:
        cdir.chmod(0o755)

    assert walled.unreadable == ("agents", "settings.json")
    assert walled.absent == (), (
        "a target that could not be stat-ed is UNREADABLE, not ABSENT — the two "
        "are different facts and are diagnosed differently")
    assert walled.digest != absent.digest, (
        "a config root behind a permission wall hashed identically to one where "
        "nothing was ever installed")


def test_a_SYMLINKED_SUBDIRECTORY_is_RECORDED_and_NOT_DESCENDED(
        fixture, tmp_path: Path) -> None:
    """Both halves, because each alone would hide the other.

    RECORDED: without a marker line the whole subtree vanishes from the manifest
    and reads as a directory this machine never had. NOT DESCENDED: following
    nested links admits a cycle, and a digest that hangs is worse than one that
    is coarse. A test asserting only the marker would pass while the walk
    descended; one asserting only the non-descent would pass while the link
    vanished.

    ⚠ THE SECOND HALF IS HELD BY `followlinks=False`, AND NOWHERE ELSE — which
    this test is the reason we know. The walk also carried a `dirnames[:]`
    comprehension dropping symlinked directories, and mutating that away left
    this test green: `os.walk` was already refusing to follow them, so the
    comprehension asserted a property it did not hold. It has been deleted, the
    way the inner `sorted(filenames)` was deleted before it, and the mutation
    that falsifies this case is now `followlinks=True`.
    """
    install_sh, cdir = fixture
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "one.md").write_text("original")

    plain = config_digest(claude_dir=cdir, install_sh=install_sh).digest
    (cdir / "agents" / "linked").symlink_to(outside, target_is_directory=True)
    with_link = config_digest(claude_dir=cdir, install_sh=install_sh).digest
    assert with_link != plain, (
        "a symlinked subdirectory that changes nothing in the manifest is a "
        "subtree that vanished silently")

    (outside / "one.md").write_text("edited behind the link")
    (outside / "two.md").write_text("and a new file too")
    assert config_digest(claude_dir=cdir, install_sh=install_sh).digest == \
        with_link, (
        "the walk followed a nested symlink — the marker records that the link "
        "is there, and its CONTENTS are deliberately outside the population")


def test_the_PRODUCTION_SHAPE_where_the_TARGET_ITSELF_is_a_symlink(
        tmp_path: Path) -> None:
    """What `install.sh` actually creates, which no other fixture here builds.

    Every target in `~/.claude/` is a symlink into the repo's `config/`. The walk
    must follow the target as its starting point — `followlinks=False` governs
    NESTED links only — or the digest on every real machine would be seven
    `symlinked-dir` markers and no content at all, and nothing here would have
    noticed.
    """
    repo_config = tmp_path / "repo" / "config"
    (repo_config / "agents").mkdir(parents=True)
    (repo_config / "agents" / "reviewer.md").write_text("you review code")
    (repo_config / "settings.json").write_text('{"model":"opus"}')

    cdir = tmp_path / "claude"
    cdir.mkdir()
    (cdir / "agents").symlink_to(repo_config / "agents", target_is_directory=True)
    (cdir / "settings.json").symlink_to(repo_config / "settings.json")

    install_sh = tmp_path / "install.sh"
    install_sh.write_text(INSTALLER)

    linked = config_digest(claude_dir=cdir, install_sh=install_sh)
    assert linked.absent == () and linked.unreadable == ()

    (repo_config / "agents" / "reviewer.md").write_text("you review code, v2")
    assert config_digest(claude_dir=cdir, install_sh=install_sh).digest != \
        linked.digest, (
        "an edit inside the repo the symlinks point at must change the digest — "
        "that mid-flight edit is the entire reason this tag exists")

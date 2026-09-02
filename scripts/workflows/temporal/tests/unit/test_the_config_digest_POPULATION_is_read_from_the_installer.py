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


def test_an_UNREADABLE_file_is_recorded_as_a_hole_not_skipped(fixture) -> None:
    """One unreadable file makes the whole target a reported hole.

    Reporting it only when EVERY file failed would let the common case — one
    root-owned file in an otherwise readable tree — pass as clean.
    """
    install_sh, cdir = fixture
    locked = cdir / "agents" / "reviewer.md"
    locked.chmod(0o000)
    try:
        result = config_digest(claude_dir=cdir, install_sh=install_sh)
    finally:
        locked.chmod(0o644)
    if result.unreadable == ():
        pytest.skip("running as a user that can read mode-000 files (root)")
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

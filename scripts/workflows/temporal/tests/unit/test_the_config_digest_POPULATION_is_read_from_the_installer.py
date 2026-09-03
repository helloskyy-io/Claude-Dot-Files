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

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "workflows" / "temporal"))

from modules.journal.config_digest import (  # noqa: E402
    DIGEST_ALGORITHM, EMPTY, ConfigDigestError, _SEGMENT_RE, claude_config_dir,
    config_digest, installer_targets, parse_symlink_targets, parse_tag_value,
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


# --------------------------------------------------------------------------
# Machine probes — the ONLY thing a skip in this file may be guarded by
# --------------------------------------------------------------------------
#
# ⚠ A SKIP PREDICATE READ FROM THE RESULT OF THE CODE UNDER TEST IS WORSE THAN A
# VACUOUS TEST, and this file shipped one. `if result.unreadable == ():
# pytest.skip("running as a user that can read mode-000 files (root)")` asked the
# digest whether it had reported a hole, and skipped when it had not — so
# DELETING the line that reports holes turned the guard into `35 passed, 1
# skipped`, with a stated reason that was false: the account was uid 1001 and
# could not read the file at all. A vacuous test asserts nothing; this converted
# a hard failure into a green skip carrying a confident explanation. The rule the
# file already stated for the two directory cases, in `_hidden`'s own docstring —
# *"a skip asserting 'this machine cannot' while the machine can is a green
# result that checked nothing"* — was simply not applied here.
#
# The rule, rather than a third correctly-written probe: a skip in this file
# whose reason is a claim about the MACHINE is guarded by a call that drives the
# real syscall on the real path. `test_every_SKIP_in_this_file_probes_the_MACHINE`
# holds that for the class, so the next one fails when it is written.


def _hidden(path: Path) -> bool:
    """True when this account really cannot list `path` after chmod 000.

    Drives the real syscall on the real path rather than inspecting
    `os.geteuid()`, because the question is what this account can do to THIS
    tree — a bind mount, an ACL or a container uid map can make the two answers
    differ.
    """
    try:
        os.listdir(path)
    except OSError:
        return True
    return False


def _sealed(path: Path) -> bool:
    """True when this account really cannot READ `path` after chmod 000.

    The file-level twin of `_hidden`, and the probe the unreadable-file case
    needed all along. Opening for read is the operation the digest performs, so
    it is the operation the skip asks about.
    """
    try:
        with open(path, "rb"):
            return False
    except OSError:
        return True


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
        if not _sealed(locked):
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
# The class checks — added by the correction pass, keyed on the SHAPE
# --------------------------------------------------------------------------

#: The probes a skip in this file may be guarded by. Each drives a real syscall
#: on a real path, so the reason it prints is a fact about the machine rather
#: than an inference from the result of the code under test.
_MACHINE_PROBES = frozenset({"_hidden", "_sealed"})

#: The files this sweep covers. Named rather than globbed: the shape exists
#: repo-wide and this check does NOT reach it, which is stated here rather than
#: left to be discovered. Elsewhere in `tests/unit/` a `pytest.skip` guarded by
#: a property of the INPUT — "this runner prints no tree-derived figure", "this
#: prompt orders no mutation" — is legitimate and different: it claims something
#: true and checkable about the fixture, not something false about the machine.
_SWEPT = ("test_the_config_digest_POPULATION_is_read_from_the_installer.py",
          "test_a_bag_RECORDS_what_configuration_the_run_absorbed.py")


def _skip_guards(tree: ast.Module) -> list[tuple[int, str]]:
    """`(lineno, description)` of the condition guarding each `pytest.skip`."""
    parents = {child: node for node in ast.walk(tree)
               for child in ast.iter_child_nodes(node)}
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "skip"):
            continue
        walker = parents.get(node)
        while walker is not None and not isinstance(walker, ast.If):
            walker = parents.get(walker)
        if walker is None:
            found.append((node.lineno, "<unguarded>"))
            continue
        test = walker.test
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            test = test.operand
        found.append((node.lineno, ast.unparse(test)))
    return found


def _probes_the_machine(condition: str) -> bool:
    """True when the condition is exactly a call to a declared machine probe."""
    try:
        expr = ast.parse(condition, mode="eval").body
    except SyntaxError:
        return False
    return (isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name)
            and expr.func.id in _MACHINE_PROBES)


@pytest.mark.parametrize("name", _SWEPT)
def test_every_SKIP_in_this_file_probes_the_MACHINE_not_the_RESULT(
        name: str) -> None:
    """⚠ THE CHECK THAT KEYS ON THE CLASS, BECAUSE FIXING THE INSTANCE DID NOT.

    This file shipped `if result.unreadable == (): pytest.skip("running as a
    user that can read mode-000 files (root)")` — a predicate read from the
    output of the code under test. Deleting `unreadable = True` from
    `_lines_for_target`'s per-file handler turned the guard into `35 passed, 1
    skipped` as uid 1001, with a stated reason that was false. Two directory
    cases in the same file, written by the same pass, used `_hidden` and failed
    loudly under the equivalent mutation — so the rule was known, written down,
    and not applied one function away. Enumerating skips does not converge;
    keying the check on the shape does.

    THE RULE: a `pytest.skip` here is guarded by a call to a declared probe and
    by nothing else. That is stricter than "does not mention the result", and
    deliberately so — a condition nobody can name is a condition nobody checks.
    """
    path = Path(__file__).with_name(name)
    guards = _skip_guards(ast.parse(path.read_text(encoding="utf-8")))
    offenders = [(lineno, cond) for lineno, cond in guards
                 if not _probes_the_machine(cond)]
    assert not offenders, (
        f"{name} guards a skip with something other than a machine probe: "
        f"{offenders}.\nA skip whose reason claims 'this machine cannot' must "
        f"ask the machine. Reading it off the result of the code under test "
        f"converts a hard failure into a green skip carrying a false "
        f"explanation. Declared probes: {sorted(_MACHINE_PROBES)}.")


def test_the_skip_sweep_EXAMINES_something() -> None:
    """A sweep whose population emptied is green while inspecting nothing.

    Asserted over the UNION rather than per file: one of the two swept files
    legitimately contains no skip today, and requiring one in each would either
    fail on that file or invite a decorative skip to satisfy the guard.
    """
    total = sum(len(_skip_guards(ast.parse(
        Path(__file__).with_name(n).read_text(encoding="utf-8"))))
        for n in _SWEPT)
    assert total >= 3, (
        f"only {total} pytest.skip call(s) across {list(_SWEPT)} — either they "
        f"moved or the recogniser went blind")


def test_the_skip_sweep_RECOGNISES_the_shape_it_was_built_for() -> None:
    """The recogniser, on snippets neither swept file contains."""
    result_derived = ("def t():\n"
                      "    if result.unreadable == ():\n"
                      "        pytest.skip('root')\n")
    machine = "def t():\n    if not _hidden(p):\n        pytest.skip('root')\n"
    undeclared = "def t():\n    if os.geteuid() == 0:\n        pytest.skip('root')\n"

    assert not _probes_the_machine(_skip_guards(ast.parse(result_derived))[0][1])
    assert _probes_the_machine(_skip_guards(ast.parse(machine))[0][1])
    # `geteuid()` is a machine fact and still fails: it is not a DECLARED probe,
    # and `_hidden`'s own docstring says why the syscall beats the uid check.
    assert not _probes_the_machine(_skip_guards(ast.parse(undeclared))[0][1])
    # A skip with no enclosing `if` is reported rather than silently passing.
    assert _skip_guards(ast.parse("def t():\n    pytest.skip('x')\n")) == \
        [(2, "<unguarded>")]


def test_every_DECLARED_probe_actually_exists_in_this_file() -> None:
    """A probe name nobody defines makes the sweep above exempt everything."""
    missing = sorted(n for n in _MACHINE_PROBES if n not in globals())
    assert not missing, f"declared machine probes that do not exist: {missing}"


def test_the_SEGMENT_gate_refuses_the_tag_s_own_empty_sentinel() -> None:
    """`none` is spelled in two places and they must not drift apart.

    `EMPTY` is what a field with nothing in it records, and `_SEGMENT_RE` refuses
    that spelling so no target or reason slug can round-trip through
    `parse_tag_value` as a population of zero. The pattern carries the literal
    (a string literal is what `test_journal_regex_anchors.py` can see); this is
    the check that the two agree.
    """
    assert _SEGMENT_RE.match(EMPTY) is None, (
        f"`_SEGMENT_RE` accepts {EMPTY!r}, the tag's own empty-list sentinel — "
        f"a target of that name would be read back as zero targets rather than "
        f"one")
    with pytest.raises(ConfigDigestError, match="empty-list sentinel"):
        parse_symlink_targets(f'SYMLINK_TARGETS=(\n    "{EMPTY}"\n)\n')
    with pytest.raises(ConfigDigestError, match="not a reason slug"):
        unavailable_tag_value(EMPTY)


# --------------------------------------------------------------------------
# The error paths, DRIVEN — the handlers this module wrote, exercised
# --------------------------------------------------------------------------
#
# ⚠ WHY THIS BLOCK EXISTS. A mutation run over this module found twelve
# surviving mutants, and every one of them was in a fail-safe path: the
# stat-level handler, the symlink recording and its prune, the `expanduser`, the
# `Path.home()` fallback, the dedup, the single-quote alternative. The DESIGNED
# behaviours were all genuinely held. The pattern is not laziness — it is that a
# handler is written the moment its failure is imagined, and imagining a failure
# feels like having tested it. A path with no control is a path a refactor
# deletes without turning anything red, and this module's whole argument is that
# the fail-safe half is the half that matters.


def test_a_config_ROOT_that_cannot_be_STATTED_is_a_hole_not_an_absence(
        fixture) -> None:
    """The stat-level handler, which nothing drove.

    `Path.exists()` swallows ENOENT but re-raises EACCES, so a config directory
    the account cannot search reaches `_lines_for_target`'s outer handler. It
    must record `unreadable` — a machine that hides the whole tree behind a
    permission bit is not a machine that never had one.
    """
    install_sh, cdir = fixture
    present = config_digest(claude_dir=cdir, install_sh=install_sh)
    cdir.chmod(0o000)
    try:
        if not _hidden(cdir):
            pytest.skip("running as a user that can list mode-000 directories")
        walled = config_digest(claude_dir=cdir, install_sh=install_sh)
    finally:
        cdir.chmod(0o755)
    missing = config_digest(claude_dir=cdir / "never-installed",
                            install_sh=install_sh)

    assert walled.unreadable == ("agents", "settings.json")
    assert walled.absent == ()
    assert missing.absent == ("agents", "settings.json")
    assert walled.digest not in (present.digest, missing.digest), (
        "a config tree behind a permission wall hashed identically to one that "
        "is readable or to one that is not there")


def test_a_FILE_TARGET_that_cannot_be_OPENED_is_a_hole(fixture) -> None:
    """The same handler reached through `sha256_of` rather than through `stat`."""
    install_sh, cdir = fixture
    locked = cdir / "settings.json"
    locked.chmod(0o000)
    try:
        if not _sealed(locked):
            pytest.skip("running as a user that can read mode-000 files (root)")
        result = config_digest(claude_dir=cdir, install_sh=install_sh)
    finally:
        locked.chmod(0o644)
    assert result.unreadable == ("settings.json",)
    assert result.absent == ()


def test_a_NON_UTF8_FILENAME_does_not_stop_the_run(fixture) -> None:
    """⚠ A FILENAME IS BYTES, AND `manifest.encode("utf-8")` RAISED ON ONE.

    The undecodable bytes reach the manifest as lone surrogates, and a plain
    encode raises `UnicodeEncodeError` — a `ValueError`, so it escaped
    `_config_digest_value`'s handler and out of `open_run_bag`, stopping every
    dispatch on the machine. The digest must be produced, and it must be STABLE:
    the same filename hashes the same way twice, which is what makes the tag
    comparable across machines at all.
    """
    install_sh, cdir = fixture
    (cdir / "agents" / os.fsdecode(b"bad_\xff.md")).write_bytes(b"content")
    first = config_digest(claude_dir=cdir, install_sh=install_sh)
    second = config_digest(claude_dir=cdir, install_sh=install_sh)
    assert len(first.digest) == 64
    assert first.digest == second.digest
    assert first.unreadable == () and first.absent == ()


def test_an_UNSEARCHABLE_DIRECTORY_is_a_hole_and_does_not_raise(fixture) -> None:
    """Mode 444: listable, and its children are not `lstat`-able.

    `os.scandir` reads the names straight off `readdir` and `d_type` says which
    are directories with no stat at all — so the walk hands us a name whose
    `is_symlink()` then raises EACCES. That call sat outside every handler, and
    `open_run_bag` re-raised the escape as `JournalRootError`, blaming free space
    under the JOURNAL root for a permission bit on the CONFIG tree. Mode 000 one
    bit away was handled correctly the whole time.
    """
    install_sh, cdir = fixture
    outer = cdir / "agents" / "outer"
    outer.mkdir()
    (outer / "inner").mkdir()
    (outer / "inner" / "deep.md").write_text("hidden")
    outer.chmod(0o444)
    try:
        if not _hidden(outer / "inner"):
            pytest.skip("running as a user that can search mode-444 directories")
        result = config_digest(claude_dir=cdir, install_sh=install_sh)
    finally:
        outer.chmod(0o755)
    assert result.unreadable == ("agents",), (
        "a directory the run could not enter must be a reported hole")
    assert len(result.digest) == 64


def test_a_FIFO_under_a_target_is_RECORDED_and_never_OPENED(fixture) -> None:
    """⚠ `open()` ON A FIFO WITH NO WRITER BLOCKS FOREVER.

    `os.walk` classifies FIFOs, device nodes and sockets as filenames, and this
    call runs before the bag exists — so the run parked with no record of itself,
    which is the one failure the journal cannot describe. Verified before the fix
    by `timeout 8` returning 124. The FIFO is recorded rather than skipped, so a
    machine with one is distinguishable from a machine without.
    """
    install_sh, cdir = fixture
    before = config_digest(claude_dir=cdir, install_sh=install_sh)
    os.mkfifo(cdir / "agents" / "pipe")
    after = config_digest(claude_dir=cdir, install_sh=install_sh)

    assert len(after.digest) == 64
    assert after.digest != before.digest, (
        "a FIFO under a target left the digest unchanged — its presence is part "
        "of what the run absorbed")
    # Nothing failed to be READ, so it is not a hole.
    assert after.unreadable == () and after.absent == ()


def test_the_DECLARED_POPULATION_is_part_of_the_digest(tmp_path: Path) -> None:
    """⚠ TWO INSTALLERS, ONE TREE, AND THEY HASHED THE SAME.

    Every other manifest line is an EFFECT of a target — bytes, an absence, a
    hole. A declared target that is present-and-empty produces no line, so
    `{agents}` and `{agents, plugins}` over one tree were identical, and
    `compare_run_config` printed SAME and exited 0 while rendering the two
    different `targets:` lists two lines below. The population the tag claims to
    be about is hashed, not merely reported beside the hash.
    """
    cdir = tmp_path / "claude"
    (cdir / "agents").mkdir(parents=True)
    (cdir / "agents" / "a.md").write_text("x")
    (cdir / "plugins").mkdir()

    narrow = tmp_path / "narrow.sh"
    narrow.write_text('SYMLINK_TARGETS=(\n    "agents"\n)\n')
    wide = tmp_path / "wide.sh"
    wide.write_text('SYMLINK_TARGETS=(\n    "agents"\n    "plugins"\n)\n')

    a = config_digest(claude_dir=cdir, install_sh=narrow)
    b = config_digest(claude_dir=cdir, install_sh=wide)
    assert a.targets == ("agents",) and b.targets == ("agents", "plugins")
    assert a.digest != b.digest, (
        "two installers declaring different populations over one tree produced "
        "the same digest — the reader then reports SAME for runs that absorbed "
        "different configuration")


def test_a_DOTTED_target_is_a_valid_segment_and_a_TRAVERSAL_is_not() -> None:
    """`.mcp.json` is a real config file and an obvious future target.

    While a leading dot was refused, adding one to `SYMLINK_TARGETS` made the
    parse raise for the WHOLE array, `_config_digest_value` swallow it, and every
    bag on every machine record `unavailable` — with nothing going red. That
    inverts the module's central argument for reading the population at all.
    """
    assert parse_symlink_targets(
        'SYMLINK_TARGETS=(\n    ".mcp.json"\n    "agents"\n)\n'
    ) == [".mcp.json", "agents"]
    for escape in (".", "..", "a/b", "../etc"):
        with pytest.raises(ConfigDigestError, match="single path segment"):
            parse_symlink_targets(f'SYMLINK_TARGETS=(\n    "{escape}"\n)\n')


def test_an_UNQUOTED_array_is_PARSED_rather_than_called_empty() -> None:
    """`SYMLINK_TARGETS=( agents hooks )` is legal, idiomatic bash.

    While only quoted entries matched, such an array yielded zero of them and
    was reported as *"declares SYMLINK_TARGETS as an EMPTY array"* — false when
    it declares two, and a diagnostic that actively misdirects is worse than one
    that is merely unhelpful.
    """
    assert parse_symlink_targets(
        "SYMLINK_TARGETS=(\n    agents\n    hooks\n)\n") == ["agents", "hooks"]
    assert parse_symlink_targets(
        "SYMLINK_TARGETS=(\n    'agents'\n    \"hooks\"\n)\n") == ["agents", "hooks"]


def test_an_UNREADABLE_array_and_an_EMPTY_one_are_DIFFERENT_facts() -> None:
    """Two facts with different remedies must not share one message."""
    with pytest.raises(ConfigDigestError, match="EMPTY array"):
        parse_symlink_targets("SYMLINK_TARGETS=(\n)\n")
    with pytest.raises(ConfigDigestError, match="no entries this parser could read"):
        parse_symlink_targets('SYMLINK_TARGETS=(\n    ""\n)\n')


def test_the_population_is_DEDUPLICATED_and_sorted() -> None:
    """One target named twice is one target, and order is not the installer's."""
    assert parse_symlink_targets(
        'SYMLINK_TARGETS=(\n    "hooks"\n    "agents"\n    "hooks"\n)\n'
    ) == ["agents", "hooks"]


def test_a_SYMLINKED_SUBDIRECTORY_is_recorded_and_not_descended(fixture) -> None:
    """Both halves: the record, and the prune that stops a cycle.

    A nested symlinked directory is named in the manifest so its presence is
    visible, and it is NOT followed — following admits a cycle, and a digest
    that hangs is worse than one that is coarse. Dropping either half was a
    surviving mutant.
    """
    install_sh, cdir = fixture
    elsewhere = cdir.parent / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "linked.md").write_text("not part of the population")

    before = config_digest(claude_dir=cdir, install_sh=install_sh)
    (cdir / "agents" / "link").symlink_to(elsewhere, target_is_directory=True)
    after = config_digest(claude_dir=cdir, install_sh=install_sh)

    assert after.digest != before.digest, (
        "a symlinked subdirectory vanished from the manifest — its presence is "
        "part of what the run absorbed")

    # The prune: the LINKED-TO file's bytes must not be in the population. If
    # the walk descended, changing them would change the digest.
    (elsewhere / "linked.md").write_text("changed on the other side of the link")
    unchanged = config_digest(claude_dir=cdir, install_sh=install_sh)
    assert unchanged.digest == after.digest, (
        "the walk followed a nested symlink — the digest now depends on bytes "
        "outside the installer's population, and can cycle")


def test_the_TARGET_ITSELF_may_be_a_symlink_which_is_what_the_installer_makes(
        tmp_path: Path) -> None:
    """⚠ THE PRODUCTION SHAPE, WHICH NO FIXTURE BUILT.

    `install.sh` links each target INTO the repo, so on a real machine every
    target under `~/.claude/` is itself a symlink. `os.walk(followlinks=False)`
    still follows the starting point, so this must hash the same bytes as the
    equivalent real directory — and the prune above must not have broken it.
    """
    repo = tmp_path / "repo" / "config"
    (repo / "agents").mkdir(parents=True)
    (repo / "agents" / "reviewer.md").write_text("you review code")
    (repo / "settings.json").write_text('{"model":"opus"}')

    install_sh = tmp_path / "install.sh"
    install_sh.write_text(INSTALLER)

    linked = tmp_path / "claude-linked"
    linked.mkdir()
    (linked / "agents").symlink_to(repo / "agents", target_is_directory=True)
    (linked / "settings.json").symlink_to(repo / "settings.json")

    real = tmp_path / "claude-real"
    (real / "agents").mkdir(parents=True)
    (real / "agents" / "reviewer.md").write_text("you review code")
    (real / "settings.json").write_text('{"model":"opus"}')

    via_links = config_digest(claude_dir=linked, install_sh=install_sh)
    direct = config_digest(claude_dir=real, install_sh=install_sh)
    assert via_links.absent == () and via_links.unreadable == ()
    assert via_links.digest == direct.digest, (
        "the shape the installer actually creates digested differently from the "
        "equivalent real tree")


def test_CLAUDE_CONFIG_DIR_is_EXPANDED_and_HOME_is_the_fallback(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """`~` in the override, and the two-step fallback beneath it."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "~/somewhere")
    assert claude_config_dir() == tmp_path / "somewhere"
    monkeypatch.delenv("CLAUDE_CONFIG_DIR")
    assert claude_config_dir() == tmp_path / ".claude"


def test_the_env_PARAMETER_is_the_seam_it_looks_like() -> None:
    """A caller passing `env=` must not silently get `os.environ`.

    It reads as the injectable seam while every other test uses `monkeypatch`,
    so a future caller would have no control proving it is wired.
    """
    assert claude_config_dir({"CLAUDE_CONFIG_DIR": "/tmp/injected"}) == \
        Path("/tmp/injected")
    assert claude_config_dir({"HOME": "/tmp/injected-home"}) == \
        Path("/tmp/injected-home/.claude")


def test_an_UNLOCATABLE_HOME_is_recorded_rather_than_refusing_the_run(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """⚠ `Path.home()` RAISES A **BARE** `RuntimeError`, AND THAT IS THE TRAP.

    `ConfigDigestError` SUBCLASSES `RuntimeError`, so `except ConfigDigestError`
    does not catch its own parent. With `HOME` unset and the uid absent from
    `/etc/passwd` — an ordinary container shape — the bare error escaped the
    module and refused the dispatch with a five-word message and no remedy, for
    a condition the contract says is one unknown fact.
    """
    def _no_home(*_args, **_kwargs):
        raise RuntimeError("Could not determine home directory.")

    monkeypatch.setattr(Path, "home", staticmethod(_no_home))
    with pytest.raises(ConfigDigestError, match="could not be located"):
        claude_config_dir({})


def test_the_UNMOCKED_home_fallback_lands_under_dot_claude(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """⚠ THE ONE BRANCH EVERY OTHER TEST MOCKS PAST.

    Two tests drive `Path.home()` — one deletes both variables and makes it
    RAISE, one supplies `HOME` so it is never called. Nothing exercised the
    success path, so `return Path.home()` with the `/ ".claude"` dropped, or
    `Path.cwd()` substituted for `Path.home()`, passed the whole file. That is
    the same untested-fallback shape the error-path block above exists to close,
    one line further down the same function.
    """
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    monkeypatch.delenv("HOME", raising=False)
    assert claude_config_dir({}) == Path.home() / ".claude"
    assert claude_config_dir({}).name == ".claude"


def test_an_array_the_SHELL_COMPUTES_is_refused_by_its_own_name() -> None:
    """`SYMLINK_TARGETS=( $EXTRA "agents" )` is legal bash and unreadable here.

    The bare-word alternative extracts `$EXTRA` verbatim, which is not what the
    installer links — so refusing the whole array is right, and the population
    is recorded as unavailable rather than guessed. What the diagnostic must not
    do is call it "not a single path segment", which sends the reader looking
    for a slash that is not there.
    """
    for computed in ("$EXTRA", "${EXTRA}", "*.md", "~/elsewhere", "a`id`b"):
        with pytest.raises(ConfigDigestError, match="computed by the shell"):
            parse_symlink_targets(
                f'SYMLINK_TARGETS=(\n    {computed}\n    "agents"\n)\n')
    # And the two messages stay distinct: a real segment escape is still a
    # segment escape, not a shell expansion.
    with pytest.raises(ConfigDigestError, match="single path segment"):
        parse_symlink_targets('SYMLINK_TARGETS=(\n    "a/b"\n)\n')

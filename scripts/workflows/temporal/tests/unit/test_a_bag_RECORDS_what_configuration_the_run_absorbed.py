"""The sixth `Journal-` tag, and the reader that compares two of them.

WORKFLOW DECOMPOSITION PHASE 5 r1, r3 AND r4. The bag already carried five facts
about a run — its workflow key, its origin repo, that repo's remote and commit,
and its worktree. None of them named the CONFIGURATION the run absorbed, so two
runs on either side of a mid-flight rule edit were indistinguishable from their
records. These tests hold the sixth fact and its consumer.

WHAT THESE GUARDS DO NOT LOOK AT:

  * They do not check that the DIGEST is right — that is
    `test_the_config_digest_POPULATION_is_read_from_the_installer.py`. Here the
    digest is just a value that must reach `bag-info.txt` intact and come back
    out of it.
  * They do not check that any real entrypoint calls `open_run_bag`. That is
    `test_every_parent_opens_a_run_bag.py`, and this file would pass unchanged if
    every entrypoint stopped calling it.
  * They say nothing about what happens when configuration changes DURING a run.
    The bag is append-only by design and the tag describes the moment the run
    began; a mid-run change is a separate finding the phase does not own.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
TEMPORAL = REPO_ROOT / "scripts" / "workflows" / "temporal"
sys.path.insert(0, str(TEMPORAL))

from modules.journal import journal_activities as ja  # noqa: E402
from modules.journal.config_digest import (  # noqa: E402
    LABEL_CONFIG_DIGEST, parse_tag_value)

READER = TEMPORAL / "scripts" / "compare_run_config.py"

#: The five facts the bag carried before this phase, verbatim. Named here so the
#: assertion below is about the sixth JOINING them rather than about a count —
#: a count would pass if a tag were renamed, and `Journal-Redaction`,
#: `Journal-Incomplete`, `Journal-Gap` and `Journal-Sealed-At` are a SEPARATE
#: lifecycle set that this phase does not join and must not be counted with.
PRE_EXISTING = ("Journal-Workflow", "Journal-Origin-Repo",
                "Journal-Origin-Remote", "Journal-Origin-Commit",
                "Journal-Worktree")

INSTALLER = 'SYMLINK_TARGETS=(\n    "settings.json"\n    "agents"\n)\n'


def _make_config(root: Path, agent_text: str) -> Path:
    (root / "agents").mkdir(parents=True, exist_ok=True)
    (root / "settings.json").write_text('{"model":"opus"}')
    (root / "agents" / "reviewer.md").write_text(agent_text)
    return root


@pytest.fixture()
def rig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A journal root and a config tree, with the fleet pointed at both.

    SELF-CONTAINED: it patches `INSTALL_SH_PATH` to a fixture installer rather
    than reading the repo's own, so a mutation of the real `install.sh` cannot
    make these tests fail for a reason they are not about.
    """
    installer = tmp_path / "install.sh"
    installer.write_text(INSTALLER)
    monkeypatch.setattr(ja, "INSTALL_SH_PATH", installer)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude"))
    _make_config(tmp_path / "claude", "v1")
    root = tmp_path / "journal"
    root.mkdir()
    return root


def _open(root: Path, run_id: str):
    return ja.open_run_bag(run_id=run_id, writer=None, repo_root=REPO_ROOT,
                           workflow_key="test-workflow", worktree_name=None,
                           journal_root=root)


def _tag(bag) -> str:
    values = [v for label, v in bag.info() if label == LABEL_CONFIG_DIGEST]
    assert len(values) == 1, f"expected exactly one tag, got {values}"
    return values[0]


def test_the_sixth_tag_JOINS_the_five_that_were_already_there(rig: Path) -> None:
    """r1: written in the same call, at the same point in the run."""
    bag = _open(rig, "runsix")
    labels = [label for label, _ in bag.info()]
    for label in PRE_EXISTING:
        assert label in labels, f"{label} disappeared — this phase ADDS, it does not replace"
    assert LABEL_CONFIG_DIGEST in labels
    digest, fields = parse_tag_value(_tag(bag))
    assert digest and len(digest) == 64
    assert fields["targets"] == ("agents", "settings.json")


def test_the_tag_is_WRITTEN_ONCE_and_a_re_open_does_not_edit_it(rig: Path) -> None:
    """r4, against the bag's OWN contract rather than a convention invented here.

    `open_bag` is idempotent: called twice for one run id it ADOPTS the existing
    bag rather than rewriting its tag files. So a retry — the case Temporal
    actually produces — must not change what the first attempt recorded, even
    when the configuration has changed underneath it in the meantime.
    """
    first = _open(rig, "runadopt")
    before = _tag(first)

    config = Path(str(rig.parent / "claude"))
    (config / "agents" / "reviewer.md").write_text("edited at 14:00")

    second = _open(rig, "runadopt")
    assert second.path == first.path
    assert _tag(second) == before, (
        "re-opening the bag rewrote the configuration tag. The bag is "
        "append-only and the tag describes the moment the run began; a "
        "mid-run change is a separate finding, not a reason to rewrite it.")


def test_a_run_with_NO_readable_configuration_still_produces_a_bag(
        rig: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """r4's second half: it records that it had nothing to say."""
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(rig.parent / "nothing-here"))
    bag = _open(rig, "runbare")
    digest, fields = parse_tag_value(_tag(bag))
    assert digest, "every target being absent is still a describable state"
    assert fields["absent"] == ("agents", "settings.json")


def test_an_UNREADABLE_INSTALLER_records_unavailable_and_does_not_stop_the_run(
        rig: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The asymmetry with `JournalRootError`, asserted rather than assumed.

    An unusable journal root stops the run — there is nowhere to record
    anything. An unestablishable configuration population does NOT: the bag
    still opens and still records the other five facts, and this one records
    WHY it is empty rather than being omitted.
    """
    monkeypatch.setattr(ja, "INSTALL_SH_PATH", rig.parent / "no-installer-here.sh")
    bag = _open(rig, "runnoinst")
    digest, fields = parse_tag_value(_tag(bag))
    assert digest is None
    assert fields["reason"] == ("installer-set-unreadable",)
    assert [label for label, _ in bag.info() if label == "Journal-Workflow"], (
        "the other five facts must still be recorded — the digest failing is "
        "one unknown fact, not a reason the run has no record")


# --------------------------------------------------------------------------
# The reader — r3
# --------------------------------------------------------------------------

def _read(*bags: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(READER), *map(str, bags)],
                          capture_output=True, text=True, timeout=60)


def test_the_reader_answers_SAME_and_DIFFERENT_from_bags_alone(rig: Path) -> None:
    """r3, and the phase's own verification step: two real bags, a real change.

    The configuration is changed between the two runs and then RESTORED for a
    third, so the fixture is not symmetric under the defect — a reader that
    always said DIFFERENT, or always said SAME, fails one of the two pairs.
    """
    config = rig.parent / "claude"
    first = _open(rig, "runone")
    (config / "agents" / "reviewer.md").write_text("v2 — an operator edited it")
    second = _open(rig, "runtwo")
    (config / "agents" / "reviewer.md").write_text("v1")
    third = _open(rig, "runthree")

    differed = _read(first.path, second.path)
    assert differed.returncode == 1, differed.stdout + differed.stderr
    assert differed.stdout.startswith("DIFFERENT")

    matched = _read(first.path, third.path)
    assert matched.returncode == 0, matched.stdout + matched.stderr
    assert matched.stdout.startswith("SAME")


def test_the_reader_REPORTS_THE_POPULATION_it_compared(rig: Path) -> None:
    """r2 reaches the operator, not just the file. A verdict with no population
    cannot be checked by the person reading it."""
    bag = _open(rig, "runpop")
    out = _read(bag.path, bag.path).stdout
    assert "targets: agents, settings.json" in out
    assert "absent: none" in out


def test_the_reader_SEPARATES_unknown_from_different(rig: Path,
                                                     monkeypatch) -> None:
    """Exit 3, not exit 1. "I cannot tell" is not "they differed".

    Collapsing them would report an unknown as a divergence — the
    confidently-wrong shape the digest was built to remove.
    """
    good = _open(rig, "rungood")
    monkeypatch.setattr(ja, "INSTALL_SH_PATH", rig.parent / "absent.sh")
    blind = _open(rig, "runblind")
    result = _read(good.path, blind.path)
    assert result.returncode == 3, result.stdout + result.stderr
    assert "UNKNOWN" in result.stdout


def test_the_reader_REFUSES_a_directory_that_is_not_a_bag(rig: Path) -> None:
    bag = _open(rig, "runreal")
    result = _read(bag.path, rig.parent)
    assert result.returncode == 2
    assert "not a run bag" in result.stderr


def test_the_reader_REFUSES_the_wrong_number_of_arguments(rig: Path) -> None:
    bag = _open(rig, "runargs")
    assert _read(bag.path).returncode == 2
    assert _read(bag.path, bag.path, bag.path).returncode == 2


def test_the_reader_reads_NOTHING_but_the_two_bags(rig: Path,
                                                   monkeypatch) -> None:
    """No network and no live filesystem read of the configuration.

    The configuration tree is DELETED before the reader runs. A reader that
    re-read `~/.claude/` would be answering *what is installed now*, which is a
    different question and one that changes after the runs it is comparing.
    """
    config = rig.parent / "claude"
    first = _open(rig, "runa")
    second = _open(rig, "runb")

    for child in sorted(config.rglob("*"), reverse=True):
        child.unlink() if child.is_file() else child.rmdir()
    config.rmdir()

    result = _read(first.path, second.path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.startswith("SAME")


# --------------------------------------------------------------------------
# The error paths that were not the DESIGNED ones — added by the build-refine
# pass. The designed failures (absent, unreadable file, missing installer) were
# covered; these are the classes the handlers did not anticipate.
# --------------------------------------------------------------------------

def test_a_NON_UTF8_INSTALLER_does_not_stop_the_run(
        rig: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The same asymmetry as a MISSING installer, for a byte instead of a file.

    `UnicodeDecodeError` is a `ValueError`, so it was caught by neither
    `installer_targets`' `except OSError` nor `_config_digest_value`'s
    `except ConfigDigestError`, and it aborted `open_run_bag`. One bad byte in
    `install.sh` therefore made every dispatch on the machine undispatchable —
    for a condition the design explicitly degrades to `unavailable`.
    """
    bad = rig.parent / "not-utf8-install.sh"
    bad.write_bytes(b'SYMLINK_TARGETS=(\n    "agents"\xff\n)\n')
    monkeypatch.setattr(ja, "INSTALL_SH_PATH", bad)

    bag = _open(rig, "runbadbyte")
    digest, fields = parse_tag_value(_tag(bag))
    assert digest is None
    assert fields["reason"] == ("installer-set-unreadable",)
    assert [label for label, _ in bag.info() if label == "Journal-Workflow"], (
        "the other five facts must still be recorded")


def test_the_reader_REFUSES_an_unparseable_bag_INSTEAD_of_calling_it_different(
        rig: Path) -> None:
    """⚠ EXIT 2, AND IT USED TO BE EXIT 1 — WHICH THE CONTRACT CALLS "DIFFER".

    `read_tag_file` raises `BagError` on a line that is neither a tag nor a
    continuation. `_read_digest` caught only `OSError`, so the exception left
    `main()` unhandled and CPython exited 1 — indistinguishable, to any caller
    reading the exit code the docstring invites it to read, from two runs that
    genuinely absorbed different configuration. That is the confidently-wrong
    shape this phase exists to remove, reproduced inside its own reader.
    """
    good = _open(rig, "runok")
    broken = rig / "not-a-real-bag"
    broken.mkdir()
    (broken / "bag-info.txt").write_text("this line is not a tag line\n")

    result = _read(good.path, broken)
    assert result.returncode == 2, (
        f"got {result.returncode}; 1 would mean DIFFERENT. "
        f"{result.stdout}{result.stderr}")
    assert "could not be read" in result.stderr


def test_the_reader_REFUSES_a_NON_UTF8_bag_info(rig: Path) -> None:
    """The same exit-code collision reached through `ValueError` rather than
    `BagError`, so fixing one class without the other would leave it live."""
    good = _open(rig, "runok2")
    broken = rig / "non-utf8-bag"
    broken.mkdir()
    (broken / "bag-info.txt").write_bytes(b"Journal-Config-Digest: sha256:\xff\n")

    result = _read(good.path, broken)
    assert result.returncode == 2, (
        f"got {result.returncode}; 1 would mean DIFFERENT. "
        f"{result.stdout}{result.stderr}")

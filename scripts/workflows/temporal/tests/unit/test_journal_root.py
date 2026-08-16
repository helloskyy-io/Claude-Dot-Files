"""The journal root's resolution contract — Phase 1 requirements 1 and 9.

WHY THIS IS THE FIRST THING TESTED. r9 makes root resolution the gate a run
passes before it does anything: a machine with a missing path, a read-only
mount, a wrong-mode directory or a root inside a checkout finds out immediately
and costs nothing. A run that starts anyway and discovers its journal unwritable
an hour in has already spent the hour, and the record of what it spent it on is
the thing that cannot be written.

EVERY REFUSAL IS ASSERTED ON ITS MESSAGE, NOT ONLY ON ITS TYPE, and that is a
requirement rather than thoroughness for its own sake. Once Phase 3 lands, a
misconfigured root stops every run INCLUDING the one an operator would use to
diagnose it, so the refusal itself has to name the resolved path and the exact
failing property. A test that only asserted `pytest.raises(JournalRootError)`
would pass against a message saying "something went wrong".

WHAT THIS FILE DOES NOT LOOK AT, stated so a green run is not read as more:

  * It does not prove any run CALLS the resolver. That is
    `test_every_parent_opens_a_run_bag.py`, and the two are complementary — a
    perfect contract nobody invokes protects nothing.
  * It does not check the deployment shapes' defaults against the machines they
    name. `/var/lib/...` is asserted as a string here; whether a systemd unit
    can write it is a property of a VM that does not exist yet.
  * It cannot observe the umask window the mode-at-creation rule closes. The
    property under test is the resulting mode; the syscall-level guarantee that
    no world-readable instant existed is not observable from Python.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from modules.journal.root import (DEPLOYMENT_SHAPES, ROOT_MODE,
                                  JournalRootError, default_root_for,
                                  journal_config, resolve_journal_root)


def _cfg(**journal) -> dict:
    return {"journal": journal}


# --- the config value, and what "unset" means --------------------------------

def test_a_configured_root_wins_over_every_default(tmp_path: Path) -> None:
    """r1: the root IS the config value. Nothing else is consulted when it is set."""
    target = tmp_path / "journal"
    got = resolve_journal_root(config=_cfg(root=str(target), deployment="user"),
                               env={"HOME": "/nowhere", "XDG_STATE_HOME": "/also-nowhere"})
    assert got == target
    assert target.is_dir()


@pytest.mark.parametrize("spelling", [None, "", "   "])
def test_the_three_spellings_of_unset_all_mean_unset(spelling) -> None:
    """Absent, null and empty are one thing to an operator editing YAML.

    Having them mean different things here would be a trap with no upside — and
    what NONE of them means is "pick something sensible without saying so",
    which is why the defaults below are documented per shape.
    """
    config = {} if spelling is None else _cfg(root=spelling)
    root, shape = journal_config(config)
    assert root is None
    assert shape == "user"


def test_an_unknown_deployment_shape_is_refused_and_lists_the_known_ones() -> None:
    """A shape nobody chose would put verbatim transcripts somewhere nobody looks."""
    with pytest.raises(JournalRootError) as exc:
        journal_config(_cfg(deployment="kubernetes"))
    assert "kubernetes" in str(exc.value)
    for known in DEPLOYMENT_SHAPES:
        assert known in str(exc.value), "the message must name what IS accepted"


def test_a_journal_section_that_is_not_a_mapping_is_refused() -> None:
    """`journal: /some/path` is the plausible YAML typo, and it must not silently win."""
    with pytest.raises(JournalRootError) as exc:
        journal_config({"journal": "/var/lib/journal"})
    assert "must be a mapping" in str(exc.value)


# --- the documented default per deployment shape ------------------------------

def test_xdg_state_home_is_honoured_when_set() -> None:
    """XDG defines this location for state persisting between restarts."""
    got = default_root_for("user", {"XDG_STATE_HOME": "/x/state", "HOME": "/home/u"})
    assert got == Path("/x/state/claude-dot-files/journal")


def test_the_user_shape_falls_back_to_XDG_S_OWN_DOCUMENTED_DEFAULT() -> None:
    """`~/.local/state` is XDG's default FOR THAT VARIABLE, not our invention.

    That is what makes it a documented default rather than the silent
    home-directory fallback r1 forbids: the document being followed is the XDG
    Base Directory Specification, and the next test shows the refusal that
    applies when even that cannot resolve.
    """
    got = default_root_for("user", {"HOME": "/home/u"})
    assert got == Path("/home/u/.local/state/claude-dot-files/journal")


def test_the_systemd_shape_uses_var_lib() -> None:
    """XDG describes XDG_STATE_HOME as "analogous to /var/lib", so the worker
    shape uses /var/lib directly rather than inventing a second convention."""
    assert default_root_for("systemd", {}) == Path("/var/lib/claude-dot-files/journal")


def test_the_container_shape_REFUSES_rather_than_guessing() -> None:
    """A guessed container root lands in the ephemeral layer and evaporates."""
    with pytest.raises(JournalRootError) as exc:
        default_root_for("container", {})
    assert "no derivable default" in str(exc.value)
    assert "journal.root:" in str(exc.value), "the message must name the remedy"


def test_no_home_and_no_XDG_is_a_REFUSAL_not_an_invented_home() -> None:
    """r1's core: the protocol must not depend on a home directory.

    The live case is an edge that is not a full Linux environment — HAOS — which
    may have no user account at all. Inventing one here is how a journal ends up
    somewhere nobody reads.
    """
    with pytest.raises(JournalRootError) as exc:
        default_root_for("user", {})
    assert "XDG_STATE_HOME" in str(exc.value) and "HOME" in str(exc.value)
    assert "journal.root:" in str(exc.value)


# --- r9: the properties the directory must have -------------------------------

def test_a_relative_root_is_refused() -> None:
    with pytest.raises(JournalRootError) as exc:
        resolve_journal_root(config=_cfg(root="var/journal"), env={})
    assert "not an absolute path" in str(exc.value)


def test_the_root_is_created_0700_including_its_intermediates(tmp_path: Path) -> None:
    """MODE AT CREATION, AND ON EVERY LEVEL WE CREATE.

    The intermediate matters and is easy to miss: `os.makedirs` applies its
    `mode` argument only to the final component, so a 0755 `claude-dot-files/`
    around a 0700 `journal/` would satisfy a check that only looked at the leaf
    while leaving the tree listable by every local account.
    """
    target = tmp_path / "outer" / "inner" / "journal"
    got = resolve_journal_root(config=_cfg(root=str(target)), env={})
    assert got == target
    for level in (target, target.parent, target.parent.parent):
        assert stat.S_IMODE(level.stat().st_mode) == ROOT_MODE, f"{level} is not 0700"


def test_a_world_readable_root_is_refused_and_the_message_names_the_mode(tmp_path: Path) -> None:
    """THE HAZARD IS READ ACCESS, and 0755 is not group- or world-WRITABLE.

    The phase doc's stated refusal is the writable one; the hazard the same
    section names is "any local account reads every run". A root that is not
    0700 was not created under this contract, so the whole mode is checked.
    """
    target = tmp_path / "journal"
    target.mkdir(mode=0o755)
    os.chmod(target, 0o755)
    with pytest.raises(JournalRootError) as exc:
        resolve_journal_root(config=_cfg(root=str(target)), env={})
    assert "0755" in str(exc.value), "the message must name the OBSERVED mode"
    assert "0700" in str(exc.value), "the message must name the REQUIRED mode"
    assert "group- or world-readable" in str(exc.value)
    assert str(target) in str(exc.value), "the message must name the resolved path"


def test_a_group_writable_root_is_refused_with_the_writable_wording(tmp_path: Path) -> None:
    """The two offences report differently, because they are different problems."""
    target = tmp_path / "journal"
    target.mkdir()
    os.chmod(target, 0o770)
    with pytest.raises(JournalRootError) as exc:
        resolve_journal_root(config=_cfg(root=str(target)), env={})
    assert "group- or world-writable" in str(exc.value)


def test_a_symlinked_root_is_refused_and_names_BOTH_paths(tmp_path: Path) -> None:
    """The target is what actually receives the transcripts.

    Following the link silently would leave the ownership and mode rules
    checking a path that is not the one being written to.
    """
    real = tmp_path / "elsewhere"
    real.mkdir(mode=ROOT_MODE)
    link = tmp_path / "journal"
    link.symlink_to(real)

    with pytest.raises(JournalRootError) as exc:
        resolve_journal_root(config=_cfg(root=str(link)), env={})
    assert "symlink" in str(exc.value)
    assert str(link) in str(exc.value) and str(real) in str(exc.value)


def test_a_root_inside_a_git_working_tree_is_refused(tmp_path: Path) -> None:
    """THE RESOLUTION RULE THAT REPLACES AN INTENT.

    The root is a config value and every build run this fleet dispatches edits
    repo config routinely, so a run can point the journal at its own worktree —
    at which point verbatim transcripts land somewhere that gets committed and
    pushed. "It does not belong in the repo" as prose has no enforcement.
    """
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    target = repo / "state" / "journal"

    with pytest.raises(JournalRootError) as exc:
        resolve_journal_root(config=_cfg(root=str(target)), env={})
    assert "git working tree" in str(exc.value)
    assert str(repo) in str(exc.value), "the message must name WHICH repo it landed in"
    assert not target.exists(), "a refused root must not have been created"


def test_a_WORKTREE_root_is_refused_too_where_dot_git_is_a_FILE(tmp_path: Path) -> None:
    """The worktree case is the one that motivates the rule, and `.git` there is
    a FILE (a gitdir pointer), not a directory. A check written as `.git`-is-a-dir
    would pass every worktree — which is where this fleet runs everything."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    (worktree / ".git").write_text("gitdir: /elsewhere/.git/worktrees/wt\n")

    with pytest.raises(JournalRootError) as exc:
        resolve_journal_root(config=_cfg(root=str(worktree / "journal")), env={})
    assert "git working tree" in str(exc.value)


def test_create_False_refuses_a_missing_root_rather_than_making_one(tmp_path: Path) -> None:
    """A diagnostic must not bring the thing it is diagnosing into existence."""
    target = tmp_path / "journal"
    with pytest.raises(JournalRootError) as exc:
        resolve_journal_root(config=_cfg(root=str(target)), env={}, create=False)
    assert "does not exist" in str(exc.value)
    assert not target.exists()


def test_a_mode_0500_root_reports_the_MODE_not_the_writability(tmp_path: Path) -> None:
    """The ordering is deliberate, and it was checked by running it.

    The obvious way to write "unwritable" is `chmod 0500` — and that root is also
    not 0700, so the mode check fires first. That is the RIGHT diagnostic (the
    remedy is `chmod 0700`, not "make it writable"), and it is pinned here so a
    later reordering that produced the vaguer message would go red rather than
    quietly degrade an operator's only recovery instruction.
    """
    if os.geteuid() == 0:
        pytest.skip("running as root: DAC permission checks are bypassed")
    target = tmp_path / "journal"
    target.mkdir(mode=ROOT_MODE)
    os.chmod(target, 0o500)
    try:
        with pytest.raises(JournalRootError) as exc:
            resolve_journal_root(config=_cfg(root=str(target)), env={})
        assert "0500" in str(exc.value) and "0700" in str(exc.value)
    finally:
        os.chmod(target, ROOT_MODE)      # so tmp_path teardown can remove it


def test_a_conforming_but_UNWRITABLE_root_is_refused(tmp_path: Path, monkeypatch) -> None:
    """The read-only-mount case: mode 0700, owned by us, and still unwritable.

    `os.access` IS MONKEYPATCHED AND THAT IS STATED RATHER THAN HIDDEN, because
    it bounds what this proves. A genuinely read-only mount cannot be produced
    inside a unit test, so what is demonstrated is that the check RUNS at this
    point in the order and that its message carries the remedy — not that Linux
    reports a read-only mount the way this assumes. The behaviour on a real
    read-only mount is integration-tier and needs a mount to test.

    It still earns its place: without this, the last check in the contract could
    be deleted and every other test here would stay green.
    """
    target = tmp_path / "journal"
    target.mkdir(mode=ROOT_MODE)

    real_access = os.access
    monkeypatch.setattr(
        os, "access",
        lambda path, mode, **kw: False if Path(path) == target else real_access(path, mode, **kw))

    with pytest.raises(JournalRootError) as exc:
        resolve_journal_root(config=_cfg(root=str(target)), env={})
    assert "not writable" in str(exc.value)
    assert "read-only mount" in str(exc.value), "the message must name the likely cause"


def test_an_existing_conforming_root_is_adopted_unchanged(tmp_path: Path) -> None:
    """POSITIVE CONTROL. Without it, a resolver that refused EVERY root would
    pass every refusal test above while making the journal unusable."""
    target = tmp_path / "journal"
    target.mkdir(mode=ROOT_MODE)
    (target / "existing-bag").mkdir(mode=ROOT_MODE)

    assert resolve_journal_root(config=_cfg(root=str(target)), env={}) == target
    assert (target / "existing-bag").is_dir(), "resolution must not disturb the journal"


def test_resolution_is_idempotent(tmp_path: Path) -> None:
    """Called on every run, forever. A resolver with a side effect that
    accumulated would be a slow leak nobody would attribute to this."""
    target = tmp_path / "journal"
    first = resolve_journal_root(config=_cfg(root=str(target)), env={})
    second = resolve_journal_root(config=_cfg(root=str(target)), env={})
    assert first == second == target
    assert list(target.iterdir()) == []


def test_JournalRootError_is_a_RuntimeError() -> None:
    """Every entrypoint carries `except RuntimeError` around its preconditions.

    This is what makes r9's fail-stop reach the operator as a printed message
    rather than as a traceback — and it is asserted rather than assumed, because
    changing the base class would silently turn eleven handled refusals into
    eleven stack traces with the suite still green.
    """
    assert issubclass(JournalRootError, RuntimeError)

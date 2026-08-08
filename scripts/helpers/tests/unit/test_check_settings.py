"""Negative controls for check_settings.py's hook-path validator.

WHY THIS EXISTS. The validator lived inline in `.github/workflows/tests.yml`
as an uncommitted Python heredoc — the one control in the repo an engineer
could not run before pushing, and whose ability to fail lived entirely in
prose in a PR body. Testing Standard § Mutation evidence requires "a guard
ships with a demonstration that it fails when the property is violated";
these eleven cases (NC-A through NC-K) are that demonstration, committed and
re-run by `run-all.sh` instead of asserted once and forgotten. Letters match
the PR body's own negative-control table (PR #56) so a reviewer can
cross-reference the two.

Each case reproduces a real behaviour the validator's rewrite fixed or had to
preserve: NC-B/C/D close false-red and false-green holes a substring match
had; NC-F/G close a partial-check hole where one bad hook among several
reported green; NC-H/I/J/K are the straightforward failure modes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from check_settings import SettingsError, load_settings, validate

REPO_ROOT = Path(__file__).resolve().parents[4]


def _hooks_dir(tmp_path: Path, *, executable: bool = True) -> Path:
    """A hooks dir holding one file, `good.sh`, executable unless told otherwise."""
    d = tmp_path / "hooks"
    d.mkdir()
    f = d / "good.sh"
    f.write_text("#!/usr/bin/env bash\necho hi\n")
    if executable:
        f.chmod(0o755)
    return d


def _cfg(*commands: str) -> dict:
    """A minimal settings.json hooks block, one hook entry per command."""
    return {"hooks": {"PreToolUse": [{"hooks": [{"command": cmd} for cmd in commands]}]}}


def test_real_settings_json_is_valid() -> None:
    """Positive control: the repo's actual config/settings.json passes today."""
    cfg = load_settings(REPO_ROOT / "config" / "settings.json")
    validate(cfg, REPO_ROOT / "config" / "hooks")  # must not raise


# --- NC-A..E: forms that MUST pass -------------------------------------------


def test_nc_a_both_canonical(tmp_path: Path) -> None:
    hooks = _hooks_dir(tmp_path)
    cfg = _cfg("$HOME/.claude/hooks/good.sh", "$HOME/.claude/hooks/good.sh")
    validate(cfg, hooks)


def test_nc_b_quoted_path_was_false_red(tmp_path: Path) -> None:
    hooks = _hooks_dir(tmp_path)
    cfg = _cfg('"$HOME/.claude/hooks/good.sh"')
    validate(cfg, hooks)


def test_nc_c_tilde_was_false_green_now_checked(tmp_path: Path) -> None:
    hooks = _hooks_dir(tmp_path)
    cfg = _cfg("~/.claude/hooks/good.sh")
    validate(cfg, hooks)


def test_nc_d_braced_home(tmp_path: Path) -> None:
    hooks = _hooks_dir(tmp_path)
    cfg = _cfg("${HOME}/.claude/hooks/good.sh")
    validate(cfg, hooks)


def test_nc_e_with_args(tmp_path: Path) -> None:
    hooks = _hooks_dir(tmp_path)
    cfg = _cfg("$HOME/.claude/hooks/good.sh --flag value")
    validate(cfg, hooks)


# --- NC-F..K: forms that MUST fail -------------------------------------------


def test_nc_f_chained_second_command_missing(tmp_path: Path) -> None:
    hooks = _hooks_dir(tmp_path)
    cfg = _cfg("$HOME/.claude/hooks/good.sh && $HOME/.claude/hooks/missing.sh")
    with pytest.raises(SettingsError, match="does not exist"):
        validate(cfg, hooks)


def test_nc_g_one_canonical_one_source_repo_path(tmp_path: Path) -> None:
    """A partial check (checked=1 of 2) must not report clean.

    Before the rewrite, `checked > 0` made this report green — one of two
    hook commands was verified and the other, a source-repo path instead of
    the canonical `$HOME/.claude/hooks/` form, went unchecked entirely.
    """
    hooks = _hooks_dir(tmp_path)
    cfg = _cfg(
        "$HOME/.claude/hooks/good.sh",
        "/home/user/Repos/claude-dot-files/config/hooks/good.sh",
    )
    with pytest.raises(SettingsError, match="references no"):
        validate(cfg, hooks)


def test_nc_h_missing_file(tmp_path: Path) -> None:
    hooks = _hooks_dir(tmp_path)
    cfg = _cfg("$HOME/.claude/hooks/missing.sh")
    with pytest.raises(SettingsError, match="does not exist"):
        validate(cfg, hooks)


def test_nc_i_not_executable(tmp_path: Path) -> None:
    hooks = _hooks_dir(tmp_path, executable=False)
    cfg = _cfg("$HOME/.claude/hooks/good.sh")
    with pytest.raises(SettingsError, match="not executable"):
        validate(cfg, hooks)


def test_nc_j_zero_hooks_verified_nothing_guard(tmp_path: Path) -> None:
    hooks = _hooks_dir(tmp_path)
    cfg: dict = {"hooks": {}}
    with pytest.raises(SettingsError, match="verified nothing"):
        validate(cfg, hooks)


def test_nc_k_malformed_json(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{not valid json")
    with pytest.raises(SettingsError, match="not valid JSON"):
        load_settings(settings_path)

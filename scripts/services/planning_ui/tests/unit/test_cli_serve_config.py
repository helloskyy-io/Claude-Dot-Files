"""`serve` takes its settings from the planning repository's `config.yaml`.

Services Standard § Centralized config.yaml and § Master kill switch: the
section is the service's own, read from the repository it serves, with
precedence flag > environment > file > the defaults the service declares —
the same defaults `--print-default-config` prints for the scaffold, so the
template and the running service cannot disagree.

An ABSENT file is the designed path (a fresh clone has the template and no
file). A file that is present and unreadable is a refusal by name, never a
silent fall-through to the defaults.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from planning_ui import cli


def _write(root: Path, section: str) -> None:
    (root / "config.yaml").write_text(section)


def test_the_printed_defaults_parse_back_to_the_declared_defaults(tmp_path: Path):
    """The template section the scaffold writes IS the service's defaults: what
    `--print-default-config` prints, read back through the same loader, is
    `DEFAULT_CONFIG`. Comments and all — the loader must not choke on them."""
    _write(tmp_path, cli.default_config_yaml())
    assert cli.load_service_config(tmp_path) == cli.DEFAULT_CONFIG
    assert cli.resolve_serve_settings(tmp_path, environ={}) == cli.DEFAULT_CONFIG


def test_no_file_means_the_defaults_and_is_not_a_fault(tmp_path: Path):
    assert cli.load_service_config(tmp_path) == {}
    assert cli.resolve_serve_settings(tmp_path, environ={}) == cli.DEFAULT_CONFIG


def test_a_file_without_this_services_section_means_the_defaults(tmp_path: Path):
    """The file is shared by every service in the repository; another
    service's section is not this one's business."""
    _write(tmp_path, "gh-monitor:\n  enabled: false\n")
    assert cli.resolve_serve_settings(tmp_path, environ={}) == cli.DEFAULT_CONFIG


def test_the_file_overrides_the_defaults(tmp_path: Path):
    """An operator's `8766` — the port collision case — is what runs."""
    _write(tmp_path, "planning-ui:\n  port: 8766\n  bind: 0.0.0.0\n")
    got = cli.resolve_serve_settings(tmp_path, environ={})
    assert got == {"enabled": True, "bind": "0.0.0.0", "port": 8766}


def test_the_environment_overrides_the_file(tmp_path: Path):
    _write(tmp_path, "planning-ui:\n  port: 8766\n")
    got = cli.resolve_serve_settings(tmp_path, environ={"PLANNING_UI_PORT": "9000"})
    assert got["port"] == 9000 and isinstance(got["port"], int)


def test_a_flag_overrides_everything(tmp_path: Path):
    _write(tmp_path, "planning-ui:\n  port: 8766\n  bind: 0.0.0.0\n")
    got = cli.resolve_serve_settings(
        tmp_path, bind="127.0.0.1", port=9001, environ={"PLANNING_UI_PORT": "9000"}
    )
    assert got["bind"] == "127.0.0.1" and got["port"] == 9001


def test_the_kill_switch_reads_from_the_file_and_the_environment(tmp_path: Path):
    _write(tmp_path, "planning-ui:\n  enabled: false\n")
    assert cli.resolve_serve_settings(tmp_path, environ={})["enabled"] is False
    assert cli.resolve_serve_settings(tmp_path, environ={"PLANNING_UI_ENABLED": "true"})["enabled"] is True
    assert cli.resolve_serve_settings(tmp_path, environ={"PLANNING_UI_ENABLED": "off"})["enabled"] is False


@pytest.mark.parametrize(
    "text, names",
    [
        ("planning-ui: [\n", "not valid YAML"),
        ("- just\n- a list\n", "must be a mapping of sections"),
        ("planning-ui: 8765\n", "`planning-ui:` must be a mapping"),
        ("planning-ui:\n  port: eighty\n", "`planning-ui.port` must be an integer"),
        ("planning-ui:\n  port: 70000\n", "`planning-ui.port` must be 1–65535"),
        ("planning-ui:\n  port: true\n", "`planning-ui.port` must be an integer"),
        ("planning-ui:\n  enabled: maybe\n", "`planning-ui.enabled` must be true or false"),
    ],
)
def test_a_present_but_unreadable_file_is_refused_by_name(tmp_path: Path, text: str, names: str):
    """Never the defaults past an operator's unreadable intent: a viewer on a
    port they did not choose is the failure this refusal exists to prevent."""
    _write(tmp_path, text)
    with pytest.raises(cli.ConfigError, match=names):
        cli.resolve_serve_settings(tmp_path, environ={})


def test_serve_with_the_kill_switch_off_exits_0_and_binds_nothing(tmp_path: Path, monkeypatch, capsys):
    """Services Standard § Master kill switch: exit 0, not 1 — a deliberately
    disabled service is a configuration state, not a failure. And nothing is
    bound: `serve()` is never reached."""
    (tmp_path / "development").mkdir()
    (tmp_path / "development" / "sprints.md").write_text("# Sprints\n")
    _write(tmp_path, "planning-ui:\n  enabled: false\n")

    def never(*_a, **_k):
        raise AssertionError("serve() must not be called when disabled")

    monkeypatch.setattr("planning_ui.serve.serve", never)
    assert cli.main(["serve", "--repo-root", str(tmp_path)]) == 0
    assert "enabled: false" in capsys.readouterr().out


def test_serve_with_an_unreadable_file_refuses_before_binding(tmp_path: Path, monkeypatch, capsys):
    (tmp_path / "development").mkdir()
    (tmp_path / "development" / "sprints.md").write_text("# Sprints\n")
    _write(tmp_path, "planning-ui:\n  port: eighty\n")

    def never(*_a, **_k):
        raise AssertionError("serve() must not be called on an unreadable config")

    monkeypatch.setattr("planning_ui.serve.serve", never)
    assert cli.main(["serve", "--repo-root", str(tmp_path)]) == 2
    assert "REFUSED" in capsys.readouterr().out


def test_serve_hands_the_resolved_settings_to_the_server(tmp_path: Path, monkeypatch):
    (tmp_path / "development").mkdir()
    (tmp_path / "development" / "sprints.md").write_text("# Sprints\n")
    _write(tmp_path, "planning-ui:\n  port: 8766\n")
    seen = {}

    def fake(bind, port, root):
        seen.update(bind=bind, port=port, root=root)
        return 0

    monkeypatch.setattr("planning_ui.serve.serve", fake)
    monkeypatch.delenv("PLANNING_UI_PORT", raising=False)
    monkeypatch.delenv("PLANNING_UI_BIND", raising=False)
    monkeypatch.delenv("PLANNING_UI_ENABLED", raising=False)
    assert cli.main(["serve", "--repo-root", str(tmp_path), "--bind", "127.0.0.2"]) == 0
    assert seen == {"bind": "127.0.0.2", "port": 8766, "root": tmp_path.resolve()}

"""Requirement 5: the vendored set is what its manifest says it is, and it
is under budget.

The manifest is the declaration a reviewer reads instead of the minified
files. These tests hold the two together: a file edited after vendoring, a
file added without an entry, or an entry whose file is gone all fail here.
The negative control is stated per test rather than in a fixture — each
mutation is a copy in `tmp_path`, never the committed set.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from planning_ui.renderers import vendor_fetch as vf

VENDOR = vf.VENDOR_DIR
MANIFEST = vf.MANIFEST

_IMPORT_RE = re.compile(r'(?:from|import)\s*"([^"]+)"')


def _check(vendor: Path, manifest: dict) -> list[str]:
    """Every discrepancy between a vendor directory and its manifest."""
    problems: list[str] = []
    listed = {entry["file"] for entry in manifest["files"]}
    # EVERY regular file under vendor/, whatever its extension — a `.js`, a
    # `.css` or a `.wasm` dropped beside the modules is third-party bytes the
    # page does not count and the budget does not see unless it is listed.
    on_disk = {p.relative_to(vendor).as_posix() for p in vendor.rglob("*") if p.is_file()} - {"manifest.json"}
    for missing in sorted(listed - on_disk):
        problems.append(f"listed but not on disk: {missing}")
    for extra in sorted(on_disk - listed):
        problems.append(f"on disk but not in the manifest: {extra}")
    total = 0
    for entry in manifest["files"]:
        path = vendor / entry["file"]
        if not path.is_file():
            continue
        data = path.read_bytes()
        total += len(data)
        if len(data) != entry["bytes"]:
            problems.append(f"{entry['file']}: {len(data)} bytes on disk, manifest says {entry['bytes']}")
        if vf.sri(data) != entry["committed_integrity"]:
            problems.append(f"{entry['file']}: committed integrity does not match the file")
        for spec in _IMPORT_RE.findall(data.decode()):
            if not spec.startswith("."):
                problems.append(f"{entry['file']} imports {spec!r} — not a relative path; the browser would reach for the network")
            elif not (path.parent / spec).resolve().is_file():
                problems.append(f"{entry['file']} imports {spec!r}, which is not a vendored file")
    if total != manifest["total_bytes"]:
        problems.append(f"total on disk {total} != manifest total {manifest['total_bytes']}")
    if manifest["total_bytes"] > manifest["budget_bytes"]:
        problems.append(f"over budget: {manifest['total_bytes']} > {manifest['budget_bytes']}")
    return problems


@pytest.fixture()
def manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def test_the_committed_set_matches_its_manifest_and_is_under_budget(manifest):
    assert manifest["files"], "positive control: the manifest lists files"
    assert manifest["budget_bytes"] == vf.BYTE_BUDGET == 262_144
    assert _check(VENDOR, manifest) == []


def test_every_entry_records_package_version_source_and_both_hashes(manifest):
    for entry in manifest["files"]:
        assert entry["package"] and entry["version"], entry
        assert entry["source"].startswith("https://esm.sh/"), entry
        assert entry["fetched_integrity"].startswith("sha384-"), entry
        assert entry["committed_integrity"].startswith("sha384-"), entry
        assert entry["file"].startswith(f"{entry['package']}@{entry['version']}/"), entry


def test_the_top_level_set_is_the_one_the_viewer_imports(manifest):
    """The view code imports vendored files by path; every such import must
    be a file the manifest lists, and the manifest's top-level set must be
    what the tool fetched from."""
    assert manifest["top_level"] == list(vf.TOP_LEVEL)
    listed = {entry["file"] for entry in manifest["files"]}
    viewer = VENDOR.parent / "viewer"
    imports = 0
    for module in viewer.glob("*.mjs"):
        for spec in _IMPORT_RE.findall(module.read_text()):
            if "/vendor/" not in spec:
                continue
            imports += 1
            assert spec.split("/vendor/", 1)[1] in listed, f"{module.name} imports {spec}, which is not vendored"
    assert imports >= 3, "positive control: the viewer imports react, react-dom/client and d3-force"


# ---- negative controls: a scratch copy, mutated three ways -----------------

def _scratch(tmp_path: Path) -> tuple[Path, dict]:
    copy = tmp_path / "vendor"
    shutil.copytree(VENDOR, copy)
    return copy, json.loads((copy / "manifest.json").read_text())


def test_control_an_edited_file_is_caught(tmp_path):
    copy, manifest = _scratch(tmp_path)
    target = copy / manifest["files"][0]["file"]
    target.write_bytes(target.read_bytes() + b"\n// edited after vendoring\n")
    problems = _check(copy, manifest)
    assert any("bytes on disk" in p for p in problems) and any("integrity" in p for p in problems)


def test_control_a_file_added_without_an_entry_is_caught_whatever_its_extension(tmp_path):
    copy, manifest = _scratch(tmp_path)
    (copy / "sneaky@1.0.0").mkdir()
    (copy / "sneaky@1.0.0" / "sneaky.mjs").write_text("export default 1;\n")
    (copy / "sneaky@1.0.0" / "sneaky.css").write_text(".x{}\n")
    (copy / "sneaky@1.0.0" / "sneaky.wasm").write_bytes(b"\0asm")
    assert _check(copy, manifest) == [
        "on disk but not in the manifest: sneaky@1.0.0/sneaky.css",
        "on disk but not in the manifest: sneaky@1.0.0/sneaky.mjs",
        "on disk but not in the manifest: sneaky@1.0.0/sneaky.wasm",
    ]


def test_control_an_absolute_import_left_in_a_module_is_caught(tmp_path):
    copy, manifest = _scratch(tmp_path)
    entry = next(e for e in manifest["files"] if e["package"] == "d3-force")
    target = copy / entry["file"]
    text = target.read_text().replace('"../d3-timer@3.0.1/d3-timer.mjs"', '"/d3-timer@^3.0.1?target=es2022"', 1)
    assert text != target.read_text(), "positive control: the specifier was there to replace"
    target.write_text(text)
    entry["bytes"] = len(text.encode())
    entry["committed_integrity"] = vf.sri(text.encode())
    manifest["total_bytes"] = sum(e["bytes"] for e in manifest["files"])
    problems = _check(copy, manifest)
    assert problems == [f"{entry['file']} imports '/d3-timer@^3.0.1?target=es2022' — not a relative path; the browser would reach for the network"]


# ---- the fetch tool's pure parts --------------------------------------------

def test_esm_paths_parse_to_package_version_and_local_layout():
    p = vf.parse_esm_path("/react-dom@19.0.0/es2022/client.mjs")
    assert (p.name, p.version, p.rest) == ("react-dom", "19.0.0", "es2022/client.mjs")
    assert p.local == "react-dom@19.0.0/client.mjs" and not p.is_stub
    stub = vf.parse_esm_path("/d3-timer@^3.0.1?target=es2022")
    assert (stub.name, stub.version, stub.rest) == ("d3-timer", "^3.0.1", "") and stub.is_stub
    scoped = vf.parse_esm_path("/@dagrejs/dagre@1.1.4/es2022/dagre.mjs")
    assert scoped.name == "@dagrejs/dagre" and scoped.local == "@dagrejs/dagre@1.1.4/dagre.mjs"
    with pytest.raises(ValueError):
        vf.parse_esm_path("not-a-path")


def test_specifiers_are_rewritten_relative_to_the_importing_file_and_nothing_else_is_touched():
    resolve = {"/react@19.0.0/es2022/react.mjs": "react@19.0.0/react.mjs", "/scheduler@^0.25.0?target=es2022": "scheduler@0.25.0/scheduler.mjs"}
    text = 'import a from"/react@19.0.0/es2022/react.mjs";import"/scheduler@^0.25.0?target=es2022";import b from"./react-dom.mjs";var s="/react@19.0.0/es2022/react.mjs";'
    out = vf.rewrite_specifiers(text, resolve, "react-dom@19.0.0/client.mjs")
    assert 'import a from"../react@19.0.0/react.mjs"' in out
    assert 'import"../scheduler@0.25.0/scheduler.mjs"' in out
    assert 'import b from"./react-dom.mjs"' in out, "a relative specifier is left alone"
    assert 'var s="/react@19.0.0/es2022/react.mjs"' in out, "a string that is not an import is left alone"


def test_a_specifier_that_was_never_fetched_is_an_error_not_a_passthrough():
    with pytest.raises(KeyError):
        vf.rewrite_specifiers('import x from"/never@1.0.0/es2022/never.mjs";', {}, "a@1/a.mjs")

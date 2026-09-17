"""Vendor the viewer's ES modules — the one network-touching tool in this package.

**Run by hand, never by ``generate``, ``--check`` or ``serve``.** The viewer
loads only files committed here (phase doc requirement 1); this is how those
files get here and how a version bump happens: *"a fetch, a hash and a commit"*.

    python3 -m planning_ui.renderers.vendor_fetch

Fetches each module in :data:`TOP_LEVEL` from esm.sh at the pinned version,
follows every import it makes — esm.sh's ES builds import their transitive
packages by absolute URL, and a top-level figure that ignores that closure
understates the committed set (the phase doc's table did, by 39 KiB) — and
writes the closure under ``vendor/<package>@<version>/``, with every import
rewritten to a relative path so the browser loads nothing from the network.

``vendor/manifest.json`` records, per file, the package, the version, the URL
it was fetched from, the SRI hash of the bytes esm.sh served (re-fetchable),
the SRI hash of the bytes committed (the served bytes after the one rewrite
below) and the committed size. The total is what requirement 5 budgets. Both
hashes are stated because a reviewer cannot read a minified module: one lets
them confirm it is what the vendor published, the other that it has not been
touched since.

**Only two kinds of specifier are rewritten.** An esm.sh absolute specifier
(``/d3-timer@^3.0.1?target=es2022`` — a version-range STUB that re-exports the
resolved module — or ``/react@19.0.0/es2022/react.mjs``, the module itself)
becomes the relative path of the resolved file. A relative specifier is
written as-is: esm.sh keeps a package's sub-modules in one directory and so
does this layout. Nothing else in a module is touched.
"""
from __future__ import annotations

import base64
import hashlib
import json
import posixpath
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ESM_SH = "https://esm.sh"

#: The modules the viewer imports, at the versions the phase doc measured.
#: `react-dom/client` brings `react-dom` and `scheduler`; `d3-force` brings
#: `d3-dispatch`, `d3-quadtree` and `d3-timer`. d3-zoom and d3-selection are
#: deliberately NOT here: their closure (d3-transition alone is 29 files) put
#: the set 11,365 bytes over the budget, and pan/zoom is ~80 lines of view
#: code — see the phase doc's byte-budget section for the measured table.
TOP_LEVEL = ("react@19.0.0", "react-dom@19.0.0/client", "d3-force@3.0.0")

VENDOR_DIR = Path(__file__).resolve().parent / "vendor"
MANIFEST = VENDOR_DIR / "manifest.json"

#: Requirement 5's budget, in bytes: 256 KiB.
BYTE_BUDGET = 262_144

_SPECIFIER_RE = re.compile(r'((?:from|import)\s*")([^"]+)(")')
_ESM_PATH_RE = re.compile(r"^/(?P<name>@?[^@/]+(?:/[^@/]+)?)@(?P<version>[^/?]+)(?:/(?P<rest>[^?]*))?(?:\?.*)?$")
_STUB_EXPORT_RE = re.compile(r'^export\s+\*\s+from\s+"([^"]+)";?$', re.MULTILINE)


@dataclass(frozen=True)
class EsmPath:
    """One esm.sh URL path, split into what the manifest records."""

    name: str
    version: str
    rest: str  # path under the package, "" for a bare stub

    @property
    def is_stub(self) -> bool:
        return not self.rest.endswith(".mjs")

    @property
    def local(self) -> str:
        """Where the file lands under ``vendor/`` — the package directory
        keyed on the RESOLVED version, and the path after esm.sh's target
        directory (``es2022/``)."""
        rest = self.rest
        if rest.startswith("es2022/"):
            rest = rest[len("es2022/"):]
        return f"{self.name}@{self.version}/{rest}"


def parse_esm_path(path: str) -> EsmPath:
    m = _ESM_PATH_RE.match(path)
    if not m:
        raise ValueError(f"not an esm.sh module path: {path!r}")
    return EsmPath(m.group("name"), m.group("version"), m.group("rest") or "")


def sri(data: bytes) -> str:
    return "sha384-" + base64.b64encode(hashlib.sha384(data).digest()).decode()


def rewrite_specifiers(text: str, resolve: dict[str, str], own_local: str) -> str:
    """Rewrite every esm.sh absolute specifier in ``text`` to a relative path.

    ``resolve`` maps an absolute esm.sh specifier to the local path of the
    module it denotes (a stub already resolved through to its target).
    ``own_local`` is the local path of the module being rewritten, so the
    result is relative to its directory. A specifier not in ``resolve`` is a
    fetch that never happened, and that is an error rather than a passthrough
    — the browser would otherwise reach for the network.
    """
    own_dir = posixpath.dirname(own_local)

    def sub(m: re.Match[str]) -> str:
        spec = m.group(2)
        if not spec.startswith("/"):
            return m.group(0)
        if spec not in resolve:
            raise KeyError(f"{own_local} imports {spec!r}, which was not fetched")
        rel = posixpath.relpath(resolve[spec], own_dir or ".")
        if not rel.startswith("."):
            rel = "./" + rel
        return f"{m.group(1)}{rel}{m.group(3)}"

    return _SPECIFIER_RE.sub(sub, text)


def _fetch(path: str) -> bytes:
    with urllib.request.urlopen(ESM_SH + path, timeout=60) as response:  # noqa: S310 — pinned host
        return response.read()


def fetch_closure(top_level: tuple[str, ...] = TOP_LEVEL) -> tuple[dict[str, bytes], dict[str, str]]:
    """Every module the top-level set reaches, keyed by esm.sh path, plus the
    specifier → local-path map the rewrite needs."""
    fetched: dict[str, bytes] = {}
    resolve: dict[str, str] = {}

    def visit(path: str) -> str:
        """Fetch ``path`` and return the LOCAL path of the module it denotes."""
        bare = path.split("?", 1)[0]
        if path in resolve:
            return resolve[path]
        data = fetched.get(bare)
        if data is None:
            data = _fetch(path)
            fetched[bare] = data
        parsed = parse_esm_path(bare)
        if parsed.is_stub:
            text = data.decode()
            targets = _STUB_EXPORT_RE.findall(text)
            if len(targets) != 1:
                raise ValueError(f"stub {path} has {len(targets)} `export * from` lines; expected 1")
            # A stub's side-effect imports order its dependencies; the target
            # module imports them itself, so following the export is enough.
            local = visit(targets[0])
            resolve[path] = local
            return local
        resolve[path] = parsed.local
        for spec in (m.group(2) for m in _SPECIFIER_RE.finditer(data.decode())):
            if spec.startswith("/"):
                visit(spec)
            elif spec.startswith("."):
                visit(posixpath.normpath(posixpath.join(posixpath.dirname(bare), spec)))
            else:
                raise ValueError(f"{bare} imports a bare specifier {spec!r}; not vendorable")
        return parsed.local

    for top in top_level:
        visit("/" + top)
    modules = {p: d for p, d in fetched.items() if parse_esm_path(p).rest.endswith(".mjs")}
    return modules, resolve


def main() -> int:
    modules, resolve = fetch_closure()
    entries = []
    written: set[Path] = set()
    for path, data in sorted(modules.items()):
        parsed = parse_esm_path(path)
        committed = rewrite_specifiers(data.decode(), resolve, parsed.local).encode()
        dest = VENDOR_DIR / parsed.local
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(committed)
        written.add(dest)
        entries.append({
            "file": parsed.local,
            "package": parsed.name,
            "version": parsed.version,
            "source": ESM_SH + path,
            "fetched_integrity": sri(data),
            "committed_integrity": sri(committed),
            "bytes": len(committed),
        })
    for stale in VENDOR_DIR.rglob("*.mjs"):
        if stale not in written:
            stale.unlink()
            print(f"removed {stale.relative_to(VENDOR_DIR)} — no longer in the closure")
    total = sum(e["bytes"] for e in entries)
    manifest = {
        "top_level": list(TOP_LEVEL),
        "budget_bytes": BYTE_BUDGET,
        "total_bytes": total,
        "rewrite": "esm.sh absolute specifiers rewritten to relative paths; nothing else changed",
        "files": entries,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{len(entries)} files, {total:,} bytes committed against a budget of {BYTE_BUDGET:,}")
    return 0 if total <= BYTE_BUDGET else 1


if __name__ == "__main__":
    sys.exit(main())

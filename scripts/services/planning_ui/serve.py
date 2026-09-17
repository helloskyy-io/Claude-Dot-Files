"""``planning-ui.sh serve`` — the process a developer starts to look at
the two diagram pages.

**What it is, and what it is not.** A stdlib HTTP server on the loopback,
started by a developer and stopped by ^C. It routes the viewer's committed
files out of ``renderers/`` and answers ``/api/views.json`` with a **fresh
derivation per request**, so a refresh of the page re-reads the corpus as it
stands. That is the one behaviour that separates it from a static file
server, and it is the operator's ruling under test in the phase doc's
runtime verification. `repo_layout.md` §1.1 rule 3 admits exactly this shape
and excludes a lifecycle: no Application, no Service, no state outliving the
process, nobody paged when it is down.

**Why a server at all.** React 19 ships as ES modules and a browser refuses
to load a module from a ``file://`` URL (MDN: *"you'll run into CORS errors
due to JavaScript module security requirements"*). Nothing is compiled and
nothing is installed — the files served are the files in the repository.

**A derivation that raises surfaces in the page.** The API answers 500 with
the traceback in the body and the page renders it in full, because a
terminal nobody is watching is not where a corpus defect should land.

**MIME types are stated here, not guessed.** ``http.server``'s guesser reads
``/etc/mime.types``, which differs per host; a module served as
``text/plain`` is refused by the loader with a MIME error. The four types
the viewer needs are pinned.
"""
from __future__ import annotations

import json
import time
import traceback
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

RENDERERS = Path(__file__).resolve().parent / "renderers"
INDEX_HTML = RENDERERS / "index.html"

#: The URL prefix the viewer's committed files are served under. The page's
#: imports are written against it.
STATIC_PREFIX = "/renderers/"
API_VIEWS = "/api/views.json"
API_STORES = "/api/stores.json"

MIME = {
    ".html": "text/html; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}


def views_payload(root: Path | None = None) -> tuple[int, dict[str, Any]]:
    """Derive afresh and shape the API response; never raises.

    Imported lazily so that starting the server does not pay for the
    extractor's imports before the first request — and so a defect in the
    extractor's import surfaces as a 500 in the page rather than as a server
    that would not start.
    """
    started = time.perf_counter()
    try:
        from planning_ui.cli import derive
        from planning_ui.views import assemble_views

        result = derive(root)
        views = assemble_views(result)
    except Exception as exc:  # noqa: BLE001 — every failure goes to the page
        return HTTPStatus.INTERNAL_SERVER_ERROR, {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
            "derived_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        }
    return HTTPStatus.OK, {
        "ok": True,
        "derived_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        "derive_ms": round((time.perf_counter() - started) * 1000),
        "counts": result.counts,
        "halted": result.halted,
        "repo": REPO_ROOT.name,
        "views": views,
    }


def stores_payload(root: Path | None = None) -> tuple[int, dict[str, Any]]:
    """The four stores, derived fresh — answered only when the page asks.

    A SEPARATE route from the views, so opening the viewer on any other page
    does not pay for a derivation of the stores it will not draw. The
    derivation is the same one; what differs is when it is asked for.
    """
    started = time.perf_counter()
    try:
        from planning_ui.cli import derive
        from planning_ui.views.stores import assemble_stores

        stores = assemble_stores(derive(root))
    except Exception as exc:  # noqa: BLE001 — every failure goes to the page
        return HTTPStatus.INTERNAL_SERVER_ERROR, {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
            "derived_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        }
    return HTTPStatus.OK, {
        "ok": True,
        "derived_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        "derive_ms": round((time.perf_counter() - started) * 1000),
        "repo": REPO_ROOT.name,
        "stores": stores,
    }


def resolve_static(url_path: str) -> Path | None:
    """The committed file a ``/renderers/...`` URL names, or ``None``.

    Resolved against ``renderers/`` and refused if the result escapes it — a
    ``..`` in a URL must not read the checkout. ``None`` for anything that is
    not a regular file inside the directory.
    """
    if not url_path.startswith(STATIC_PREFIX):
        return None
    relative = url_path[len(STATIC_PREFIX):]
    candidate = (RENDERERS / relative).resolve()
    try:
        candidate.relative_to(RENDERERS)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


class ViewerHandler(BaseHTTPRequestHandler):
    server_version = "planning_ui/serve"

    def do_GET(self) -> None:  # noqa: N802 — http.server's name
        path = urlsplit(self.path).path
        if path == "/":
            self._send_file(INDEX_HTML)
            return
        if path in (API_VIEWS, API_STORES):
            handler = views_payload if path == API_VIEWS else stores_payload
            status, payload = handler(REPO_ROOT)
            self._send_json(status, payload)
            return
        static = resolve_static(path)
        if static is not None:
            self._send_file(static)
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": f"no route for {path}"})

    def _send_file(self, file: Path) -> None:
        body = file.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", MIME.get(file.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        # Nothing is cached: a refresh must re-fetch the view code as well as
        # the derivation, or an edited module keeps its old behaviour.
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = (json.dumps(payload, default=str) + "\n").encode()
        self.send_response(status)
        self.send_header("Content-Type", MIME[".json"])
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def make_server(bind: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((bind, port), ViewerHandler)


#: The one planning repository this process serves, set once by `serve()`.
#: One viewer per planning repo: the port is that repo's, the derivation is
#: that repo's, and nothing here reaches beside it.
REPO_ROOT: Path = Path(".")


def serve(bind: str, port: int, root: Path) -> int:
    global REPO_ROOT  # noqa: PLW0603 — set once, before the first request
    REPO_ROOT = root
    with make_server(bind, port) as httpd:
        host, bound_port = httpd.server_address[:2]
        print(f"planning_ui: serving {root.name} at http://{host}:{bound_port}/ — ^C stops it")
        print("planning_ui: every refresh re-derives from this checkout; nothing is cached or written")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nplanning_ui: stopped")
    return 0

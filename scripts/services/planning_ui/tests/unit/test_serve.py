"""The serve verb's pure parts: routing a URL to a committed file and
shaping the API response. The end-to-end request path, against the live
corpus, is `tests/integration/test_serve_live.py`."""
from __future__ import annotations

from http import HTTPStatus

from planning_ui import serve


def test_a_static_url_resolves_to_a_file_inside_renderers_only():
    assert serve.resolve_static("/renderers/index.html") == serve.RENDERERS / "index.html"
    assert serve.resolve_static("/renderers/viewer/app.mjs") == serve.RENDERERS / "viewer" / "app.mjs"
    # A directory is not a file to serve; a path that is not there is None.
    assert serve.resolve_static("/renderers/viewer/") is None
    assert serve.resolve_static("/renderers/viewer/nope.mjs") is None
    # Not under the prefix at all.
    assert serve.resolve_static("/index.html") is None


def test_a_traversal_out_of_renderers_is_refused():
    """`..` in a URL must not read the checkout: cli.py sits one level up and
    is a real file, so a resolver that walked would return it."""
    assert (serve.RENDERERS.parent / "cli.py").is_file(), "positive control: the target exists"
    assert serve.resolve_static("/renderers/../cli.py") is None
    assert serve.resolve_static("/renderers/viewer/../../cli.py") is None


def test_the_module_types_are_pinned_not_guessed():
    """A module served as text/plain is refused by the loader; the four
    types the viewer needs must not depend on the host's /etc/mime.types."""
    assert serve.MIME[".mjs"].startswith("text/javascript")
    assert serve.MIME[".js"].startswith("text/javascript")
    assert serve.MIME[".json"].startswith("application/json")
    assert serve.MIME[".css"].startswith("text/css")
    assert serve.MIME[".html"].startswith("text/html")


def test_a_derivation_that_raises_becomes_a_500_with_the_traceback(monkeypatch):
    """Requirement: a raise surfaces in the page, not only in a terminal.
    The payload is what the page renders, so it must carry the traceback."""
    import planning_ui.cli as cli

    def boom(*_a, **_k):
        raise RuntimeError("the corpus did something")

    monkeypatch.setattr(cli, "derive", boom)
    status, payload = serve.views_payload()
    assert status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert payload["ok"] is False
    assert payload["error"] == "RuntimeError: the corpus did something"
    assert "RuntimeError: the corpus did something" in payload["traceback"]
    assert "boom" in payload["traceback"], "the traceback names where it raised"

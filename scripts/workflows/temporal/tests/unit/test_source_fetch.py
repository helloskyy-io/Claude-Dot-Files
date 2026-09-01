"""The fetch policy — the one place this package can be pointed at a machine.

WHY THIS FILE IS THE MOST ADVERSARIAL IN THE PACKAGE. The URL is
model-influenceable and may itself have come out of a previously-fetched
document, and the response is DURABLY STORED and RE-SERVABLE OFFLINE. That is
strictly worse than an ordinary server-side request forgery: the payload outlives
the request and is read back later by a checker that trusts the store. Every
assertion below is a case that, unclosed, makes the content store a way to reach
this network.

EVERY TEST RUNS OFFLINE, and that is a property of the code rather than of the
test harness. `fetch_source` takes its opener and its resolver as parameters
precisely so the rules can be exercised against a name with a hostile answer
without a socket — a policy that could only be tested against a live host is a
policy nobody tests.

WHAT THIS FILE DOES NOT LOOK AT, said out loud: it never touches the content
store, so nothing here says a fetched byte was stored correctly, and it never
checks a quote. It also does not close DNS rebinding — the module names that as
a residual, and a test asserting the addresses are checked does not make the
name resolve the same way twice.
"""

from __future__ import annotations

import io

import pytest

from modules.journal.source_fetch import (MAX_SOURCE_BYTES, USER_AGENT,
                                          FetchPolicy, FetchRefused,
                                          check_url, fetch_source,
                                          refused_address_reason,
                                          resolved_addresses)

PUBLIC = "93.184.216.34"


class FakeHeaders(dict):
    """Just enough of `email.message.Message` for the fetcher's three reads."""

    def get(self, key, default=None):  # noqa: D102
        for name, value in self.items():
            if name.lower() == key.lower():
                return value
        return default

    def get_content_type(self):  # noqa: D102
        return self.get("Content-Type", "text/plain").split(";")[0]


class FakeResponse:
    def __init__(self, body: bytes, headers: dict | None = None):
        self._stream = io.BytesIO(body)
        self.headers = FakeHeaders(headers or {})

    def read(self, size=-1):
        return self._stream.read(size)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeOpener:
    """Records what was asked for, and answers from a scripted map."""

    def __init__(self, responses: dict):
        self.responses = responses
        self.requests: list = []
        self.timeouts: list = []

    def open(self, request, timeout=None):
        self.requests.append(request)
        self.timeouts.append(timeout)
        answer = self.responses[request.full_url]
        if isinstance(answer, Exception):
            raise answer
        return answer


def resolver_for(mapping: dict):
    """A `getaddrinfo` stand-in: host -> list of addresses it resolves to."""
    def resolve(host, port, family=0, socktype=0):
        if host not in mapping:
            import socket
            raise socket.gaierror(-2, "Name or service not known")
        return [(2, 1, 6, "", (address, port)) for address in mapping[host]]
    return resolve


ONLY_PUBLIC = resolver_for({"example.org": [PUBLIC], "other.example": [PUBLIC]})


# --- the address rules ----------------------------------------------------------

@pytest.mark.parametrize("address", [
    "127.0.0.1", "::1",                 # loopback
    "169.254.169.254", "fe80::1",       # link-local — the cloud metadata range
    "10.0.0.5", "192.168.1.1", "172.16.0.1", "fd00::1",   # private
    "0.0.0.0", "::",                    # unspecified
    "224.0.0.1",                        # multicast
    "240.0.0.1",                        # reserved
])
def test_an_address_inside_this_network_is_refused(address: str) -> None:
    assert refused_address_reason(address) is not None


@pytest.mark.parametrize("address", [PUBLIC, "2606:2800:220:1:248:1893:25c8:1946"])
def test_a_public_address_is_permitted(address: str) -> None:
    """THE NEGATIVE HALF. A rule that refused everything would pass every test above."""
    assert refused_address_reason(address) is None


def test_EVERY_resolved_address_is_checked_not_just_the_first() -> None:
    """A name with one public and one loopback record must not be reachable by luck.

    Ordering in a DNS answer is not a security property, and a check that read
    `[0]` would pass or fail depending on which record a resolver happened to
    return first — which is a policy that works until it does not.
    """
    resolve = resolver_for({"mixed.example": [PUBLIC, "127.0.0.1"]})
    with pytest.raises(FetchRefused) as caught:
        check_url("https://mixed.example/a", FetchPolicy(), resolve=resolve)
    assert "loopback" in str(caught.value)


def test_a_name_that_resolves_to_nothing_is_refused() -> None:
    with pytest.raises(FetchRefused):
        resolved_addresses("nowhere.example", 443, resolve=resolver_for({}))


# --- the scheme allowlist -------------------------------------------------------

@pytest.mark.parametrize("url", [
    "http://example.org/a", "file:///etc/passwd", "ftp://example.org/a",
    "data:text/plain,hello", "gopher://example.org/a", "https:///nohost",
])
def test_a_scheme_or_shape_outside_the_allowlist_is_refused(url: str) -> None:
    with pytest.raises(FetchRefused):
        check_url(url, FetchPolicy(), resolve=ONLY_PUBLIC)


# --- the fetch itself -----------------------------------------------------------

def test_a_permitted_fetch_returns_the_bytes_AS_RECEIVED() -> None:
    """THE NEGATIVE CONTROL FOR THE WHOLE FILE: the happy path must still work.

    Every other test here asserts a refusal, and a `fetch_source` that raised
    unconditionally would satisfy all of them.
    """
    body = b"<html>the source said this</html>"
    opener = FakeOpener({"https://example.org/a": FakeResponse(
        body, {"Content-Type": "text/html; charset=utf-8"})})
    fetched = fetch_source("https://example.org/a", opener=opener,
                           resolve=ONLY_PUBLIC)
    assert fetched.data == body
    assert fetched.final_url == "https://example.org/a"
    assert fetched.media_type == "text/html"
    assert fetched.hops == ("https://example.org/a",)


def test_the_request_asks_for_no_content_coding_and_names_itself() -> None:
    opener = FakeOpener({"https://example.org/a": FakeResponse(b"x")})
    fetch_source("https://example.org/a", opener=opener, resolve=ONLY_PUBLIC)
    headers = opener.requests[0].headers
    assert headers["Accept-encoding"] == "identity"
    assert headers["User-agent"] == USER_AGENT


def test_the_timeout_reaches_the_opener() -> None:
    """A hung server must not be able to hold a run open indefinitely."""
    opener = FakeOpener({"https://example.org/a": FakeResponse(b"x")})
    fetch_source("https://example.org/a", opener=opener, resolve=ONLY_PUBLIC,
                 policy=FetchPolicy(timeout_seconds=3.5))
    assert opener.timeouts == [3.5]


def test_an_encoded_response_is_REFUSED_rather_than_decoded() -> None:
    """Refusing removes the decompression case; a decoded cap would only bound it.

    It also keeps "the digest is over the bytes the server sent" literally true,
    which is the sentence the whole store's guarantee rests on.
    """
    opener = FakeOpener({"https://example.org/a": FakeResponse(
        b"\x1f\x8b garbage", {"Content-Encoding": "gzip"})})
    with pytest.raises(FetchRefused) as caught:
        fetch_source("https://example.org/a", opener=opener, resolve=ONLY_PUBLIC)
    assert "gzip" in str(caught.value)


def test_an_identity_content_encoding_is_permitted() -> None:
    """The refusal is of a CODING, not of the header. `identity` is no coding."""
    opener = FakeOpener({"https://example.org/a": FakeResponse(
        b"plain", {"Content-Encoding": "identity"})})
    assert fetch_source("https://example.org/a", opener=opener,
                        resolve=ONLY_PUBLIC).data == b"plain"


# --- the size cap ---------------------------------------------------------------

def test_the_cap_is_enforced_on_the_READ_not_on_the_declared_length() -> None:
    """`Content-Length` is the server's claim about its own body.

    A fetcher that trusted it would store however many bytes actually arrived,
    which is the whole point of a cap that a hostile server can set to zero.
    """
    opener = FakeOpener({"https://example.org/a": FakeResponse(
        b"x" * 5000, {"Content-Length": "10"})})
    with pytest.raises(FetchRefused) as caught:
        fetch_source("https://example.org/a", opener=opener, resolve=ONLY_PUBLIC,
                     policy=FetchPolicy(max_bytes=100))
    assert "exceeds" in str(caught.value)


def test_an_over_declared_length_is_refused_before_the_body_is_read() -> None:
    """The cheap early exit, which is all the declared length is ever used for."""
    opener = FakeOpener({"https://example.org/a": FakeResponse(
        b"x" * 10, {"Content-Length": str(MAX_SOURCE_BYTES + 1)})})
    with pytest.raises(FetchRefused) as caught:
        fetch_source("https://example.org/a", opener=opener, resolve=ONLY_PUBLIC)
    assert "declares" in str(caught.value)


def test_a_body_exactly_at_the_cap_is_STORED_not_refused() -> None:
    """An off-by-one here silently truncates the corpus a checker later reads."""
    opener = FakeOpener({"https://example.org/a": FakeResponse(b"x" * 100)})
    fetched = fetch_source("https://example.org/a", opener=opener,
                           resolve=ONLY_PUBLIC, policy=FetchPolicy(max_bytes=100))
    assert len(fetched.data) == 100


# --- redirects: every hop re-enters every check ---------------------------------

def _redirect(location: str, code: int = 302):
    import urllib.error
    return urllib.error.HTTPError(
        "https://example.org/a", code, "Found",
        FakeHeaders({"Location": location}), None)


def test_a_redirect_to_a_LOOPBACK_host_is_refused() -> None:
    """THE STANDARD BYPASS. A permitted URL redirecting to the metadata range.

    Automatic redirect following is switched off precisely so this hop comes
    back here to be checked; a fetcher that let the library follow would store
    the response with the intermediate URL never having passed a check.
    """
    resolve = resolver_for({"example.org": [PUBLIC], "evil.example": ["127.0.0.1"]})
    opener = FakeOpener({
        "https://example.org/a": _redirect("https://evil.example/steal"),
        "https://evil.example/steal": FakeResponse(b"secrets"),
    })
    with pytest.raises(FetchRefused) as caught:
        fetch_source("https://example.org/a", opener=opener, resolve=resolve)
    assert "loopback" in str(caught.value)


def test_a_redirect_to_a_LINK_LOCAL_address_is_refused() -> None:
    resolve = resolver_for({"example.org": [PUBLIC],
                            "metadata.example": ["169.254.169.254"]})
    opener = FakeOpener({
        "https://example.org/a": _redirect("https://metadata.example/latest/meta-data/"),
    })
    with pytest.raises(FetchRefused) as caught:
        fetch_source("https://example.org/a", opener=opener, resolve=resolve)
    assert "link-local" in str(caught.value)


def test_a_redirect_to_a_NON_HTTPS_scheme_is_refused() -> None:
    opener = FakeOpener({"https://example.org/a": _redirect("http://example.org/a")})
    with pytest.raises(FetchRefused) as caught:
        fetch_source("https://example.org/a", opener=opener, resolve=ONLY_PUBLIC)
    assert "scheme" in str(caught.value)


def test_a_relative_redirect_is_resolved_against_the_hop_that_sent_it() -> None:
    """A `Location: /b` is a real redirect shape and must not be treated as a URL."""
    opener = FakeOpener({
        "https://example.org/a": _redirect("/b"),
        "https://example.org/b": FakeResponse(b"arrived"),
    })
    fetched = fetch_source("https://example.org/a", opener=opener,
                           resolve=ONLY_PUBLIC)
    assert fetched.data == b"arrived"
    assert fetched.final_url == "https://example.org/b"
    assert fetched.hops == ("https://example.org/a", "https://example.org/b")
    assert fetched.url == "https://example.org/a", (
        "the URL asked for is kept alongside the one that answered — a citation "
        "records where it landed, and an operator needs to see the chain")


def test_a_permitted_redirect_to_another_public_host_is_followed() -> None:
    opener = FakeOpener({
        "https://example.org/a": _redirect("https://other.example/b", code=308),
        "https://other.example/b": FakeResponse(b"moved permanently"),
    })
    fetched = fetch_source("https://example.org/a", opener=opener,
                           resolve=ONLY_PUBLIC)
    assert fetched.data == b"moved permanently"


def test_a_redirect_LOOP_ends_rather_than_spinning() -> None:
    opener = FakeOpener({"https://example.org/a": _redirect("https://example.org/a")})
    with pytest.raises(FetchRefused) as caught:
        fetch_source("https://example.org/a", opener=opener, resolve=ONLY_PUBLIC,
                     policy=FetchPolicy(max_redirects=2))
    assert "redirects" in str(caught.value)


def test_a_non_redirect_http_error_is_reported_not_followed() -> None:
    import urllib.error
    opener = FakeOpener({"https://example.org/a": urllib.error.HTTPError(
        "https://example.org/a", 404, "Not Found", FakeHeaders({}), None)})
    with pytest.raises(FetchRefused) as caught:
        fetch_source("https://example.org/a", opener=opener, resolve=ONLY_PUBLIC)
    assert "404" in str(caught.value)


# --- the parser's own refusals, and the redirect handler itself ------------------

@pytest.mark.parametrize("url", [
    "https://[::1",
    "https://host:99999/",
    "https://host:-1/",
])
def test_an_UNPARSEABLE_url_is_a_REFUSAL_not_a_ValueError(url) -> None:
    """⚠ `urlsplit` AND `.port` RAISE `ValueError`, PAST EVERY CALLER.

    `check_url`'s contract is "prove one URL may be fetched, refuse otherwise",
    and `FetchRefused` is what a capture activity catches. A malformed URL —
    which is exactly the kind a model-influenceable value produces — crashed the
    activity instead of being recorded as a policy refusal. A boundary that
    validates input owes its own refusal for the inputs the PARSER rejects too,
    not only for the ones its rules reject.
    """
    with pytest.raises(FetchRefused):
        check_url(url, FetchPolicy(), resolve=resolver_for({"host": [PUBLIC]}))


@pytest.mark.parametrize("address", [
    "64:ff9b::a9fe:a9fe",     # 169.254.169.254, the cloud metadata address
    "64:ff9b::7f00:1",        # 127.0.0.1
    "64:ff9b:1::a9fe:a9fe",   # the local-use translation prefix, RFC 8215
])
def test_a_NAT64_TRANSLATED_address_is_refused(address) -> None:
    """RFC 6052 EMBEDS AN IPv4 ADDRESS IN A v6 PREFIX, AND `is_reserved` CATCHES IT.

    `64:ff9b::a9fe:a9fe` is `169.254.169.254` behind a NAT64 gateway, and neither
    `is_private`, `is_loopback` nor `is_link_local` is true of it — which is why
    a review raised it as an uncovered category and why a correction pass wrote
    a hand-written prefix table before checking. `is_reserved` is ALREADY true
    across `64::/16`, so the table refused nothing and its test passed with the
    table deleted. The table was reverted; this test stays, PINNED, so the next
    reader finds the property asserted rather than re-deriving the same table.

    ⚠ THIS IS A PIN, NOT A CLOSURE. A network-specific translation prefix — RFC
    6052 permits any /32, /40, /48, /56, /64 or /96 an operator chooses — is not
    reserved and is not enumerable from here. That is a residual, beside DNS
    rebinding, and this test does not claim otherwise.
    """
    assert refused_address_reason(address) is not None


def test_a_PUBLIC_v6_address_is_still_permitted() -> None:
    """DISCRIMINATION CONTROL for the row above. A refusal table that refused
    every v6 address would pass the test above and close the fetcher entirely.

    (The first draft of this control used `64:ff9a::1`, which is itself reserved
    — a control that could not have discriminated. Named because it is the same
    mistake as the table it was written to check.)
    """
    assert refused_address_reason("2606:2800:220:1:248:1893:25c8:1946") is None
    assert refused_address_reason("2001:4860:4860::8888") is None


def test_the_redirect_HANDLER_ITSELF_stops_urllib_following() -> None:
    """⚠ EVERY OTHER REDIRECT TEST HANDS `fetch_source` A PRE-BUILT `HTTPError`.

    Those prove `fetch_source` re-validates a hop it is GIVEN. None of them
    constructs the real `OpenerDirector`, so the thing that turns urllib's own
    following OFF — `_NoRedirects` — was never exercised: a CPython change to
    `HTTPRedirectHandler`'s method set, which is the exact risk that class's
    docstring names, would silently re-enable automatic following and every SSRF
    redirect test in this file would still be green.

    ⚠ AND THE FIRST VERSION OF THIS TEST WAS ITSELF VACUOUS, WHICH IS WHY THE
    STUB RETURNS RATHER THAN RAISES. It had the stub handler RAISE `HTTPError`,
    which propagates straight out of `OpenerDirector.open` and never reaches the
    error chain at all — so `redirect_request` was not on the path and deleting
    the override changed nothing. The mutation caught it: predicted one failure,
    observed zero. A 3xx only reaches `http_error_302` when a handler RETURNS a
    response that `HTTPErrorProcessor` sees, so that is what this builds.
    """
    import email.message
    import urllib.error
    import urllib.request
    import urllib.response

    from modules.journal.source_fetch import _NoRedirects

    START = "https://start.example/a"
    INNER = "https://elsewhere.example/inner"
    visited: list[str] = []

    class Body(io.BytesIO):
        """`HTTPErrorProcessor.http_response` reads `response.msg`, and
        `addinfourl` delegates unknown attributes to the file it wraps."""
        msg = "Found"

    def real_headers(**fields) -> email.message.Message:
        """⚠ `email.message.Message`, NOT THIS FILE'S `FakeHeaders`, AND THE
        DIFFERENCE IS WHAT MADE THE SECOND DRAFT OF THIS TEST VACUOUS TOO.

        `http_error_302` asks `"location" in headers` in lower case. `Message`
        is case-insensitive; a plain `dict` is not — so a `{"Location": ...}`
        stand-in made even the STOCK `HTTPRedirectHandler` decline to follow,
        and the mutation came back green a second time against a fixture that
        could not have discriminated. Verified by running both handlers against
        this fixture: stock follows to the inner URL, `_NoRedirects` raises 302.
        """
        message = email.message.Message()
        for key, value in fields.items():
            message[key] = value
        return message

    class StubHTTPSHandler(urllib.request.HTTPSHandler):
        def https_open(self, req):
            visited.append(req.full_url)
            if req.full_url == START:
                return urllib.response.addinfourl(
                    Body(b""), real_headers(Location=INNER), req.full_url, 302)
            return urllib.response.addinfourl(
                Body(b"the inner body"), real_headers(), req.full_url, 200)

    opener = urllib.request.build_opener(_NoRedirects, StubHTTPSHandler)
    with pytest.raises(urllib.error.HTTPError) as caught:
        opener.open(urllib.request.Request(START))

    assert caught.value.code == 302
    assert visited == [START], (
        "urllib followed the redirect ITSELF — the hop never came back to "
        f"`fetch_source` to re-enter `check_url`. Visited: {visited}")

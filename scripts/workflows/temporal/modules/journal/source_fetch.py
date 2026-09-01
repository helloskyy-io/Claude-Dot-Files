"""Getting a source's bytes over the network, under a policy stated in one place.

REQUIREMENT 7(c)'s FETCH POLICY. The phase doc offered a cheap arm — tee an
existing tool's byte stream and inherit its policy — and a check of this tree
closed it: `grep -rlE "urllib|requests\\.|httpx|urlopen" --include=*.py scripts/`
returns nothing, because every citation this fleet reads is fetched by the model
through its own tooling inside a `claude -p` child. There is no stream to tee, so
this module is the policy and it is written out rather than inherited.

WHY A POLICY AT ALL, STATED AS THE THREAT AND NOT AS HYGIENE. The URL is
model-influenceable and may itself have come out of a previously-fetched
document. Without the rules below this is a server-side request forgery
primitive whose responses are DURABLY STORED and RE-SERVABLE OFFLINE — which is
strictly worse than the usual shape, because the attacker's payload outlives the
request and gets read back by a checker that trusts the store.

THE RULES, EACH WITH THE CASE IT CLOSES:

  * **`https` only.** `http` is unauthenticated in transit, and `file:`, `ftp:`
    and `data:` reach things that are not a remote source at all. A scheme
    allowlist rather than a denylist: the schemes `urllib` supports grow.
  * **Every redirect hop is re-validated.** A permitted URL that redirects to
    `http://169.254.169.254/` is the standard bypass, so automatic redirect
    following is switched OFF and each hop re-enters the same checks. A redirect
    to a non-`https` scheme, or to a refused address, ends the fetch.
  * **Private, loopback, link-local and unspecified addresses are refused**, for
    every address the host resolves to rather than for the first. A name with one
    public and one loopback record must not be reachable by luck of ordering.
  * **A timeout**, so a hung server cannot hold a run open indefinitely.
  * **A size cap**, enforced while reading rather than from `Content-Length`,
    because that header is a claim by the server. The declared length is checked
    too, as a cheap early refusal, but it is never what stops the read.
  * **Bytes are stored AS RECEIVED**, and a response carrying a content encoding
    is REFUSED rather than decoded. The phase doc allows either that or a decoded
    size cap; refusing is the smaller mechanism, it keeps "the hash is over what
    the server sent" literally true, and it removes the decompression-bomb case
    instead of bounding it. `Accept-Encoding: identity` asks for this, and the
    refusal is what happens when a server ignores the ask.

WHAT THIS DOES NOT CLOSE, SAID PLAINLY SO IT IS NOT OVER-READ. The addresses are
resolved and checked, and then `urllib` resolves the name again to connect. A
name that changes its answer between those two moments — DNS rebinding — is not
caught here. Closing it means connecting to a validated address directly and
carrying the original host through TLS verification, which is a custom
connection layer rather than a rule. It is named as a residual rather than
implied away, and the store's other protection is that a rebound response still
has to survive `verify` being run by a human who knows what was cited.
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

from .bag import BagError

__all__ = ["ALLOWED_SCHEMES", "DEFAULT_TIMEOUT_SECONDS", "MAX_SOURCE_BYTES",
           "MAX_REDIRECTS", "USER_AGENT", "FetchRefused", "FetchPolicy",
           "FetchedSource", "refused_address_reason", "check_url",
           "resolved_addresses", "fetch_source"]

ALLOWED_SCHEMES = ("https",)

DEFAULT_TIMEOUT_SECONDS = 20.0

# One object's ceiling. Generous for a document and far below anything that
# would matter against the journal's size budget; a source larger than this is
# a refusal naming the number rather than a silent truncation, because half a
# page hashed as though it were the page is a citation that verifies against
# bytes nobody read.
MAX_SOURCE_BYTES = 8 * 1024 * 1024

MAX_REDIRECTS = 5

# Identifies the fetcher to the operator of the site being read. A request that
# does not say who it is invites being treated as abuse, and this one is made on
# behalf of a record that claims to be checkable.
USER_AGENT = "skyynet-journal-content-store/1 (+persistent-memory-protocol)"


class FetchRefused(BagError):
    """A source was not fetched, and the message says which rule refused it.

    A refusal is the normal outcome for a URL that should not be reached, so it
    carries the rule's name: an operator reading it needs to know whether the
    policy worked or the source is simply unreachable.
    """


@dataclass(frozen=True)
class FetchPolicy:
    """The numbers the rules above are enforced with. One object, passed down.

    A dataclass rather than module constants read directly, so a test can tighten
    a bound without monkeypatching the module — and so the values a fetch ran
    under can be recorded beside what it fetched.
    """

    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_bytes: int = MAX_SOURCE_BYTES
    max_redirects: int = MAX_REDIRECTS
    allowed_schemes: tuple[str, ...] = ALLOWED_SCHEMES


@dataclass(frozen=True)
class FetchedSource:
    """The bytes, and the trail that produced them."""

    url: str                      # the URL asked for
    final_url: str                # the URL that answered, after any redirects
    data: bytes
    media_type: str | None
    hops: tuple[str, ...]         # every URL visited, in order, including the first


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    """Turns `urllib`'s automatic redirect following OFF.

    THE POINT IS THE HOP, NOT THE COUNT. `urllib` follows redirects itself and
    would deliver the final response with the intermediate URLs never having
    passed a check — so a permitted URL redirecting to a link-local address would
    be fetched and stored. Returning `None` from every redirect method makes
    `urllib` raise `HTTPError` on a 3xx instead, which hands the hop back to
    `fetch_source` to re-validate before it is followed.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


def refused_address_reason(address: str) -> str | None:
    """Why this IP may not be fetched from, or `None` if it may.

    Every category is refused by the `ipaddress` module's own classification
    rather than by a hand-written range table: the ranges are the standard's and
    a table here would be a second, staler copy of them. `is_global` is not used
    as the single test because it answers a slightly different question for IPv6
    and the categories below are what the threat model actually names.
    """
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return f"{address!r} is not an IP address"
    for flag, why in (("is_loopback", "a loopback address"),
                      ("is_link_local", "a link-local address (the cloud metadata range)"),
                      ("is_private", "a private address"),
                      ("is_reserved", "a reserved address"),
                      ("is_multicast", "a multicast address"),
                      ("is_unspecified", "the unspecified address")):
        if getattr(ip, flag):
            return (f"{address} is {why}. The content store fetches sources the "
                    f"model named, so a URL resolving inside this network would "
                    f"make the fetcher a way to reach it.")
    return None


def resolved_addresses(host: str, port: int,
                       resolve=socket.getaddrinfo) -> list[str]:
    """Every address `host` resolves to, as strings. Injectable for testing.

    `resolve` IS A PARAMETER BECAUSE THE ALTERNATIVE IS AN UNTESTED RULE. The
    address checks are the security half of this module and the only way to
    exercise them against a name with a hostile answer, offline and
    deterministically, is to supply the answer. A default argument keeps every
    real caller honest without a fixture.
    """
    try:
        infos = resolve(host, port, 0, socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise FetchRefused(f"cannot resolve {host!r}: {exc}") from exc
    addresses = []
    for info in infos:
        address = info[4][0]
        if address not in addresses:
            addresses.append(address)
    if not addresses:
        raise FetchRefused(f"{host!r} resolved to no addresses")
    return addresses


def check_url(url: str, policy: FetchPolicy, resolve=socket.getaddrinfo) -> str:
    """Prove one URL may be fetched. Returns its host. Refuses otherwise.

    CALLED ON THE ORIGINAL URL AND ON EVERY REDIRECT TARGET, which is the whole
    reason it is a function rather than a block at the top of `fetch_source`. A
    check that ran once would be exactly the bypass this policy exists to close.
    """
    parts = urlsplit(url)
    if parts.scheme not in policy.allowed_schemes:
        raise FetchRefused(
            f"refusing {url!r}: scheme {parts.scheme!r} is not permitted "
            f"(allowed: {', '.join(policy.allowed_schemes)}). The allowlist is "
            f"positive rather than a denylist because the set of schemes the "
            f"URL library supports grows without this module being edited.")
    if not parts.hostname:
        raise FetchRefused(f"refusing {url!r}: it names no host")

    port = parts.port or 443
    for address in resolved_addresses(parts.hostname, port, resolve=resolve):
        reason = refused_address_reason(address)
        if reason:
            raise FetchRefused(f"refusing {url!r}: {reason}")
    return parts.hostname


def _read_capped(response, max_bytes: int, url: str) -> bytes:
    """Read the body, refusing at `max_bytes` rather than truncating to it.

    THE CAP IS ENFORCED ON THE READ, and the declared length is only a cheap
    early exit. `Content-Length` is the server's claim about its own body; a
    fetcher that trusted it would store however many bytes actually arrived.
    """
    declared = response.headers.get("Content-Length")
    if declared and declared.isdigit() and int(declared) > max_bytes:
        raise FetchRefused(
            f"refusing {url!r}: it declares {int(declared)} bytes, over the "
            f"{max_bytes}-byte cap for one stored source.")

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise FetchRefused(
                f"refusing {url!r}: its body exceeds the {max_bytes}-byte cap "
                f"for one stored source. The read stops here rather than "
                f"storing a truncation — half a page hashed as though it were "
                f"the page is a citation that verifies against bytes nobody read.")
        chunks.append(chunk)
    return b"".join(chunks)


def fetch_source(url: str, *, policy: FetchPolicy | None = None,
                 opener=None, resolve=socket.getaddrinfo) -> FetchedSource:
    """Fetch one source under the policy. Every hop re-checked; bytes as received.

    `opener` AND `resolve` ARE INJECTABLE FOR THE SAME REASON. The rules this
    function enforces are the ones that matter, and a test that had to reach a
    real host to exercise them would be a test that does not run offline — which
    is the property this whole phase is about.
    """
    policy = policy or FetchPolicy()
    opener = opener or urllib.request.build_opener(_NoRedirects)

    hops: list[str] = []
    current = url
    for _ in range(policy.max_redirects + 1):
        check_url(current, policy, resolve=resolve)
        hops.append(current)

        request = urllib.request.Request(current, headers={
            "User-Agent": USER_AGENT,
            # Asks for no content coding. A server that ignores this is refused
            # below rather than decoded, which is what keeps "the digest is over
            # the bytes the server sent" literally true.
            "Accept-Encoding": "identity",
        })
        try:
            response = opener.open(request, timeout=policy.timeout_seconds)
        except urllib.error.HTTPError as exc:
            location = exc.headers.get("Location") if exc.headers else None
            if exc.code in (301, 302, 303, 307, 308) and location:
                current = urljoin(current, location)
                continue
            raise FetchRefused(
                f"fetching {current!r} failed: HTTP {exc.code} {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise FetchRefused(f"fetching {current!r} failed: {exc.reason}") from exc

        with response:
            encoding = (response.headers.get("Content-Encoding") or "").strip().lower()
            if encoding and encoding != "identity":
                raise FetchRefused(
                    f"refusing {current!r}: the response is {encoding}-encoded "
                    f"and this fetcher stores bytes as received. Decoding here "
                    f"would mean the stored digest was over something the "
                    f"server never sent, and would reopen the decompression "
                    f"case that not decoding closes outright.")
            data = _read_capped(response, policy.max_bytes, current)
            media_type = (response.headers.get_content_type()
                          if hasattr(response.headers, "get_content_type") else None)

        return FetchedSource(url=url, final_url=current, data=data,
                             media_type=media_type, hops=tuple(hops))

    raise FetchRefused(
        f"refusing {url!r}: more than {policy.max_redirects} redirects. A chain "
        f"this long is either a loop or an attempt to tire out the checks each "
        f"hop re-runs.")

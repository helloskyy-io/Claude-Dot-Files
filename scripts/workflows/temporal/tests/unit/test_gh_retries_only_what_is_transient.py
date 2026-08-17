"""`gh` rides out a blip, and refuses to ride out an answer that will not change.

WHY THIS EXISTS. On 2026-08-17 GitHub ran a Partial System Outage. One
`gh repo view --json nameWithOwner` in preflight took a single
`HTTP 503: No server is currently available to service your request`, and the
dispatch died before doing any work. `gh` ran the command once and raised on any
non-zero exit; the only retry in the fleet was one caller's, written after a
flaky read nearly discarded a completed review.

THE RISK IS OVER-RETRYING, NOT UNDER-RETRYING, WHICH IS WHY MOST OF THIS FILE
TESTS THE NEGATIVE. A guard that retries a 503 is worth nothing on its own — the
one that retries EVERYTHING also retries a 503. So every transient case below has
a terminal twin, and the two are asserted on the same observable (`calls`, the
number of times `gh` was actually executed) so neither can pass by accident.

EVERY ERROR STRING HERE WAS MEASURED, NOT INVENTED. `_LIVE_503` is the exact
stderr this repo's own `gh` produced during that outage; `_REST_404`,
`_GRAPHQL_404` and `_BAD_FLAG` were captured from real invocations in the
worktree that wrote this file. A classifier tuned against imagined error prose
is a classifier tuned against nothing.

WHAT THIS FILE DOES NOT COVER, stated because a guard that reads broader than it
is does more harm than a narrow one:

  * **Whether `gh` itself retried underneath us.** Every `gh` here is a fake.
    These tests pin OUR policy, not the transport's.
  * **Wall-clock.** `time.sleep` is replaced everywhere, so the pauses are
    asserted as VALUES and never waited on. A retry test that actually sleeps
    taxes every future run of the suite for evidence it does not produce.
  * **Concurrency.** Two dispatches retrying the same throttled endpoint make
    the throttle worse. Nothing here observes that, and nothing in the fleet
    coordinates it.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from modules.assistant import assistant_activities as act  # noqa: E402

# Captured from live invocations, 2026-08-17. See this module's docstring.
_LIVE_503 = ("HTTP 503: No server is currently available to service your request. "
             "Sorry about that. Please try resubmitting your request and contact us "
             "if the problem persists. (https://api.github.com/graphql)")
_REST_404 = "gh: Not Found (HTTP 404)"
_GRAPHQL_404 = ("GraphQL: Could not resolve to a PullRequest with the number of "
                "99999. (repository.pullRequest)")
_BAD_FLAG = "unknown flag: --not-a-flag"

_READ = ["repo", "view", "--json", "nameWithOwner"]
_ATTEMPTS = len(act._GH_RETRY_BACKOFF_SECONDS) + 1


class _FakeGh:
    """A scripted `gh`, recording every invocation it was actually asked for.

    `calls` IS THE OBSERVABLE THE WHOLE FILE TURNS ON. Asserting on the return
    value cannot tell a retry from a first success, and asserting on elapsed time
    cannot run without sleeping. The number of times the process was launched is
    the only thing that separates "retried" from "did not".
    """

    def __init__(self, replies: list[tuple[int, str]]) -> None:
        self.replies = replies
        self.calls: list[list[str]] = []

    def __call__(self, argv, **_kwargs):
        self.calls.append(argv)
        # The last reply repeats, so a test asserting exhaustion does not have to
        # know in advance how many attempts the policy will spend.
        code, stderr = self.replies[min(len(self.calls) - 1, len(self.replies) - 1)]
        return subprocess.CompletedProcess(
            argv, code, stdout="" if code else '{"ok":true}', stderr=stderr)


@pytest.fixture
def slept(monkeypatch) -> list[float]:
    """Pauses recorded rather than taken. See the docstring on wall-clock."""
    taken: list[float] = []
    monkeypatch.setattr(act.time, "sleep", taken.append)
    return taken


def _install(monkeypatch, replies: list[tuple[int, str]]) -> _FakeGh:
    fake = _FakeGh(replies)
    monkeypatch.setattr(act.subprocess, "run", fake)
    return fake


# ── the transient direction ────────────────────────────────────────────────

def test_a_503_on_a_read_is_retried_and_the_run_survives_it(
    monkeypatch, tmp_path, slept,
) -> None:
    """THE ORIGINATING FAILURE, END TO END.

    One 503 then a good reply is exactly what the outage produced, and it is
    what killed the dispatch. The assertion is that the CALLER never sees it.
    """
    fake = _install(monkeypatch, [(1, _LIVE_503), (0, "")])

    assert act.gh(_READ, tmp_path) == '{"ok":true}'
    assert len(fake.calls) == 2, (
        f"expected one retry after the 503, got {len(fake.calls)} attempt(s)")
    assert slept == [act._GH_RETRY_BACKOFF_SECONDS[0]], (
        f"backed off {slept} — the policy's first pause is "
        f"{act._GH_RETRY_BACKOFF_SECONDS[0]}s")


def test_a_persistent_503_stops_at_the_bound_and_raises_the_real_error(
    monkeypatch, tmp_path, slept,
) -> None:
    """BOUNDED IS HALF THE DESIGN. An outage must not read as latency.

    And the exception carries `gh`'s own words, not a classification of them:
    the last attempt is outside the retry loop precisely so the operator gets
    the real message rather than one this module paraphrased.
    """
    fake = _install(monkeypatch, [(1, _LIVE_503)])

    with pytest.raises(RuntimeError) as exc:
        act.gh(_READ, tmp_path)

    assert len(fake.calls) == _ATTEMPTS, (
        f"spent {len(fake.calls)} attempts against a bound of {_ATTEMPTS}")
    assert slept == list(act._GH_RETRY_BACKOFF_SECONDS)
    assert "No server is currently available" in str(exc.value), (
        "the raise paraphrased gh instead of quoting it")


@pytest.mark.parametrize(
    ("stderr", "why"),
    [
        pytest.param("HTTP 502: Bad gateway", "502", id="502"),
        pytest.param("HTTP 504: Gateway Timeout", "504", id="504"),
        pytest.param("HTTP 429: Too Many Requests", "429", id="429"),
        pytest.param(
            "HTTP 403: You have exceeded a secondary rate limit. Please wait a "
            "few minutes before you try again.", "403 naming a throttle",
            id="403-secondary-rate-limit"),
        pytest.param(
            "HTTP 403: You have triggered an abuse detection mechanism.",
            "403 naming abuse detection", id="403-abuse"),
    ],
)
def test_the_retryable_set_is_exactly_what_a_later_call_may_satisfy(
    monkeypatch, tmp_path, slept, stderr: str, why: str,
) -> None:
    fake = _install(monkeypatch, [(1, stderr), (0, "")])
    act.gh(_READ, tmp_path)
    assert len(fake.calls) == 2, f"{why} was not retried"


# ── the terminal direction: the half that makes the guard worth having ─────

@pytest.mark.parametrize(
    ("stderr", "why"),
    [
        pytest.param(_REST_404, "a 404 is the same answer every time", id="rest-404"),
        pytest.param(_GRAPHQL_404, "GraphQL's 404 carries no status token",
                     id="graphql-404"),
        pytest.param(_BAD_FLAG, "a malformed argument cannot fix itself",
                     id="bad-flag"),
        pytest.param("HTTP 401: Bad credentials", "auth is deterministic",
                     id="401"),
        pytest.param("HTTP 403: Resource not accessible by integration",
                     "a 403 that is a permission failure, not a throttle",
                     id="403-permission"),
        pytest.param("", "an empty stderr names no condition", id="no-stderr"),
    ],
)
def test_a_deterministic_failure_is_never_retried(
    monkeypatch, tmp_path, slept, stderr: str, why: str,
) -> None:
    """RETRYING THESE IS WORSE THAN NOT RETRYING AT ALL.

    It converts a fast truthful failure into a slow one, and the operator's
    stated concern is runs that will not stop. One attempt, then the truth.
    """
    fake = _install(monkeypatch, [(1, stderr)])

    with pytest.raises(RuntimeError):
        act.gh(_READ, tmp_path)

    assert len(fake.calls) == 1, (
        f"{why} — but it was attempted {len(fake.calls)} times")
    assert slept == [], f"backed off {slept} for a terminal failure"


def test_a_terminal_status_beside_a_retryable_one_stays_terminal(
    monkeypatch, tmp_path, slept,
) -> None:
    """EVERY STATUS MUST BE RETRYABLE, NOT MERELY ONE OF THEM.

    `gh` quotes server text, and server text is not ours. A reply that carries a
    404 and — for any reason — the characters `HTTP 503` must not be promoted by
    the one the classifier liked. The asymmetry is deliberate: being wrong in
    this direction is a run that will not stop.
    """
    fake = _install(monkeypatch, [(1, f"{_REST_404} — upstream said HTTP 503")])

    with pytest.raises(RuntimeError):
        act.gh(_READ, tmp_path)

    assert len(fake.calls) == 1, (
        "a 503 mentioned anywhere in the message promoted a 404 to retryable")


def test_a_403_is_read_by_its_TEXT_because_the_status_alone_cannot_decide(
) -> None:
    """The one status that is genuinely both, pinned on the classifier directly.

    Asserted as a pair in one test on purpose: the claim is a DISCRIMINATION, and
    two separate tests each showing one side would both still pass if the
    classifier stopped reading the text and started answering a constant.
    """
    throttled = act._gh_transient_reason(
        "HTTP 403: You have exceeded a secondary rate limit.")
    forbidden = act._gh_transient_reason(
        "HTTP 403: Resource not accessible by integration")

    assert throttled is not None and "throttled" in throttled
    assert forbidden is None


# ── the idempotence gate ───────────────────────────────────────────────────

@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["pr", "comment", "100", "--body-file", "/tmp/x"], id="comment"),
        pytest.param(["pr", "create", "--title", "t", "--body", "b"], id="create"),
        pytest.param(["pr", "merge", "100", "--squash"], id="merge"),
        pytest.param(["issue", "close", "41"], id="close"),
        pytest.param(["api", "repos/o/n/issues"], id="api-undecidable"),
    ],
)
def test_a_write_is_not_retried_even_when_the_failure_IS_transient(
    monkeypatch, tmp_path, slept, args: list[str],
) -> None:
    """A 502 ON A MUTATION MAY MEAN THE MUTATION LANDED AND THE REPLY WAS LOST.

    Nothing in the reply separates that from a mutation that never ran, so the
    retry that rescues a read double-posts a write. Not hypothetical here: issue
    #41 records duplicate comments on an issue an operator had to rule on.

    `api` is in this list as an UNDECIDABLE, not as a write. Its method is a flag
    rather than a verb, so the positional rule cannot rule on it and the default
    is no. Whoever adds the first `gh api` caller decides it deliberately.
    """
    fake = _install(monkeypatch, [(1, _LIVE_503)])

    with pytest.raises(RuntimeError):
        act.gh(args, tmp_path)

    assert len(fake.calls) == 1, (
        f"`gh {' '.join(args)}` was retried {len(fake.calls)} times on a 503 — a "
        f"transient failure on a write is not safe to repeat")


def test_the_read_verbs_the_fleet_actually_calls_all_pass_the_gate() -> None:
    """A gate that rejects everything also rejects every write.

    So this pins the POSITIVE side against the invocations really in the tree —
    otherwise `_READ_ONLY_GH_VERBS = frozenset()` passes every test above it and
    silently restores the original one-attempt behaviour for the whole fleet.
    """
    live = [
        ["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        ["pr", "view", "100", "--json", "headRefName", "-q", ".headRefName"],
        ["pr", "view", "100", "--json", "comments"],
        ["issue", "list", "--state", "open", "--limit", "50", "--json", "number,title"],
    ]
    assert live, "the fixture is empty — this test would pass vacuously"
    for args in live:
        assert act._gh_is_read_only(args), f"`gh {' '.join(args)}` lost its retry"


# ── visibility ─────────────────────────────────────────────────────────────

def test_a_retry_says_what_it_retried_and_why_it_thought_it_could(
    monkeypatch, tmp_path, slept, capsys,
) -> None:
    """A SILENT RETRY MEANS NOBODY EVER LEARNS HOW OFTEN THIS HAPPENS.

    The next person asking "is it GitHub or us?" has whatever these lines said
    and nothing else, so each of the four facts is asserted separately: which
    invocation, which attempt, the classification that licensed the retry, and
    which attempt finally answered.
    """
    _install(monkeypatch, [(1, _LIVE_503), (0, "")])
    act.gh(_READ, tmp_path)
    out = capsys.readouterr().out

    assert "repo view --json nameWithOwner" in out, "the invocation is not named"
    assert f"attempt 1/{_ATTEMPTS}" in out, "the attempt number is not named"
    assert "TRANSIENT" in out and "HTTP 503" in out, (
        "the retry does not say what made it think this was transient")
    assert f"succeeded on attempt 2/{_ATTEMPTS}" in out, (
        "nothing records which attempt actually answered")


def test_a_refusal_to_retry_is_ALSO_logged(
    monkeypatch, tmp_path, slept, capsys,
) -> None:
    """"IT DID NOT RETRY" IS THE HALF THAT CANNOT BE INFERRED FROM SILENCE.

    A log that only speaks when it retries makes a correctly-refused 404 and a
    retry path that is broken and never fires look identical.
    """
    _install(monkeypatch, [(1, _REST_404)])
    with pytest.raises(RuntimeError):
        act.gh(_READ, tmp_path)

    assert "TERMINAL" in capsys.readouterr().out, (
        "a refused retry left no trace, so a broken classifier would be invisible")


def test_a_multi_line_body_is_not_dumped_into_the_console(
    monkeypatch, tmp_path, slept, capsys,
) -> None:
    """The notice is a console line, and several call sites pass prose.

    A retry that prints a whole PR body teaches the operator to skip the retries,
    which costs exactly the visibility the notice exists to buy.
    """
    body = "line one\n" + ("x" * 4000)
    _install(monkeypatch, [(1, _LIVE_503), (0, "")])
    act.gh(["pr", "view", "100", "--json", body], tmp_path)

    for line in capsys.readouterr().out.splitlines():
        assert len(line) < 400, f"a console line ran to {len(line)} characters"


# ── gh_json's position, and the composition with the caller above it ───────

def test_gh_json_adds_ZERO_attempts_when_the_body_does_not_parse(
    monkeypatch, tmp_path, slept,
) -> None:
    """A ZERO-EXIT REPLY THAT WILL NOT PARSE IS NOT A TRANSIENT FAILURE.

    The transport succeeded and the server named no condition a later identical
    call would satisfy. `gh_json` normalises the decode failure to `RuntimeError`
    so callers guard one type — and that normalisation is exactly what a retry
    must not be built on, because by then the cause has been erased. Retrying
    `RuntimeError` at this level would re-run every 404 the layer below
    deliberately refused.
    """
    calls: list[list[str]] = []

    def reply(argv, **_kwargs):
        # Exit 0 with a body that will not parse — the shape `gh_json`'s
        # docstring says once crashed a parent build loop at zero attempts.
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout="<html>502</html>", stderr="")

    monkeypatch.setattr(act.subprocess, "run", reply)

    with pytest.raises(RuntimeError, match="did not return JSON"):
        act.gh_json(_READ, tmp_path)

    assert len(calls) == 1, (
        f"the unparseable body was fetched {len(calls)} times — a decode "
        f"failure is deterministic and must cost exactly one attempt")
    assert slept == []


def test_the_retry_under_the_review_threads_retry_stays_bounded(
    monkeypatch, tmp_path, slept,
) -> None:
    """TWO RETRIES NOW COMPOSE ON ONE PATH, AND THE PRODUCT IS THE THING TO PIN.

    `_read_thread_for_invariant` retried `RuntimeError` so a flaky read could not
    discard a completed review. It still does, and `gh_attempt` now retries
    underneath it, so the attempts MULTIPLY rather than add. That is acceptable
    on this path — the alternative is throwing away a ~40-minute review — but it
    is acceptable because it is bounded, and a bound nobody asserts is a bound
    that grows the next time either constant is edited.
    """
    from modules.assistant.review_pr import review_pr_workflow as wf

    monkeypatch.setattr(wf.time, "sleep", lambda _s: None)
    fake = _install(monkeypatch, [(1, _LIVE_503)])

    with pytest.raises(RuntimeError):
        wf._read_thread_for_invariant("100", tmp_path)

    expected = _ATTEMPTS * (len(wf._THREAD_READ_BACKOFF_SECONDS) + 1)
    assert len(fake.calls) == expected, (
        f"the composed bound moved: {len(fake.calls)} attempts against the "
        f"{expected} the two policies multiply to. If a constant changed "
        f"deliberately, change this number with it and say what the new "
        f"worst-case wall-clock is.")

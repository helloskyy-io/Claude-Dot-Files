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

# DERIVED, NEVER SPELLED — the seconds are pinned as literals above and in
# `test_the_retry_BUDGET_is_pinned_as_LITERALS_and_never_derived`; the MINUTES
# are a consequence and were previously restated as prose in four places, so
# moving the ceiling left three of them quietly wrong. `_read_thread_for_invariant`
# is imported lazily inside the tests that use it, so its bound is read here by
# the same lazy import rather than at module scope.
def _outer_attempts() -> int:
    from modules.assistant.review_pr import review_pr_workflow as wf
    return len(wf._THREAD_READ_BACKOFF_SECONDS) + 1


_OUTER_ATTEMPTS = _outer_attempts()
_HANG_CEILING_MIN = _OUTER_ATTEMPTS * act._SUBPROCESS_TIMEOUT_SECONDS / 60
_IF_RETRIED_MIN = (_ATTEMPTS * _OUTER_ATTEMPTS * act._SUBPROCESS_TIMEOUT_SECONDS
                   + sum(act._GH_RETRY_BACKOFF_SECONDS) * _OUTER_ATTEMPTS) / 60


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


# ── the budget itself ──────────────────────────────────────────────────────

def test_the_retry_BUDGET_is_pinned_as_LITERALS_and_never_derived() -> None:
    """EVERY OTHER TEST HERE DERIVES ITS EXPECTATION FROM THE CONSTANT, SO THE
    CONSTANT ITSELF IS UNPINNED WITHOUT THIS.

    Measured, not reasoned about: widening `_GH_RETRY_BACKOFF_SECONDS` from two
    pauses to five and running this module fired ZERO tests. `_ATTEMPTS` is
    computed from the constant and the sleep assertions compare against the
    constant, so both sides moved together — the classic shared-fixture control,
    where the test and the code under test read the same value.

    That matters because the bound IS the design. "Ride out a blip" and
    "disguise an outage as latency" differ only in this tuple, and the operator's
    stated concern is runs that will not stop. So the numbers are restated here
    as literals: changing the policy now costs a deliberate edit to a test whose
    docstring says what the numbers were chosen to buy.

      2.0s  the 503s measured during the 2026-08-17 outage cleared in seconds
      6.0s  one more, shorter than the 8.0 its sibling uses, because this sits
            UNDERNEATH `_THREAD_READ_BACKOFF_SECONDS` and the product is what an
            operator waits through
      3     attempts total: one retry is a coin flip, four starts hiding an outage
    """
    assert act._GH_RETRY_BACKOFF_SECONDS == (2.0, 6.0), (
        "the retry budget moved. That is allowed — but say in the PR what the "
        "new worst-case wall-clock is, here and in the composition test below.")
    assert sum(act._GH_RETRY_BACKOFF_SECONDS) == 8.0
    assert _ATTEMPTS == 3


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


@pytest.mark.parametrize(
    "stderr",
    [
        pytest.param("gh: Not Found (HTTP 404) — rate limit exceeded for this "
                     "org, per the docs", id="404-quoting-a-rate-limit"),
        pytest.param("HTTP 401: Bad credentials. Too Many Requests were made "
                     "with this token.", id="401-quoting-too-many-requests"),
        pytest.param("HTTP 422: Validation failed — abuse detection mechanism "
                     "rules are documented here", id="422-quoting-abuse-detection"),
    ],
)
def test_rate_limit_PROSE_promotes_ONLY_a_403_and_never_another_status(
    stderr: str,
) -> None:
    """THE PROSE RESCUE IS THE ONE PLACE THIS CLASSIFIER READS SERVER ENGLISH,
    AND ITS SCOPE IS THE ONLY THING KEEPING THAT SAFE.

    403 is genuinely both "you may not do this" and "you are throttled", so the
    status alone cannot separate them and `_RATE_LIMIT_PHRASES` breaks the tie.
    Nothing else needs that tie broken — and `gh` quotes server-supplied text,
    so any status at all can arrive carrying these words without being about
    them.

    MEASURED, NOT REASONED ABOUT: widening the `code == 403` clause to bare
    `rate_limited` left this module and the whole tree GREEN before this test
    existed, while making `gh: Not Found (HTTP 404) — ... rate limit ...`
    retryable. `_RATE_LIMIT_PHRASES`' own comment already claimed this could not
    happen; nothing checked the claim.
    """
    assert act._gh_transient_reason(stderr) is None, (
        f"a non-403 status was promoted to retryable by prose alone: {stderr!r}")


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


def test_the_TWO_refusals_do_not_say_the_same_thing(
    monkeypatch, tmp_path, slept, capsys,
) -> None:
    """A REFUSED WRITE AND A DETERMINISTIC FAILURE ARE DIFFERENT ANSWERS TO THE
    OPERATOR'S ONE QUESTION, and one label for both answers it wrongly half the
    time.

    "Is it GitHub or us?" — a 404 says us, a 503 on a `gh pr comment` says
    GitHub and the run stopped anyway because repeating it might post twice.
    Both used to print `TERMINAL (not retried)`.

    ASSERTED AS A PAIR ON PURPOSE. Two separate tests each checking one line
    would both still pass if the two branches were re-merged into one string, so
    long as that string contained both words. The claim is that the lines
    DIFFER.
    """
    _install(monkeypatch, [(1, _REST_404)])
    with pytest.raises(RuntimeError):
        act.gh(_READ, tmp_path)
    deterministic = capsys.readouterr().out

    _install(monkeypatch, [(1, _LIVE_503)])
    with pytest.raises(RuntimeError):
        act.gh(["pr", "comment", "100", "--body", "x"], tmp_path)
    refused_write = capsys.readouterr().out

    assert deterministic != refused_write, (
        "a deterministic 404 and a transient 503 refused for being a write "
        "printed the same line — the log cannot tell an operator which it was")
    assert "TERMINAL" in deterministic and "TRANSIENT" not in deterministic
    assert "TRANSIENT" in refused_write and "HTTP 503" in refused_write, (
        "the refused write does not say that GitHub, not the request, failed")
    assert "NOT A READ" in refused_write, (
        "the refused write does not say WHY it was refused despite being "
        "classified transient")


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


# ── gh_attempt's own contract: the thing `gh` is NOT ──────────────────────

@pytest.mark.parametrize(
    ("replies", "expected_calls", "why"),
    [
        pytest.param([(1, _REST_404)], 1, "a terminal failure", id="terminal"),
        pytest.param([(1, _LIVE_503)], _ATTEMPTS, "an exhausted transient one",
                     id="transient-exhausted"),
    ],
)
def test_gh_attempt_RETURNS_a_failure_rather_than_raising_it(
    monkeypatch, tmp_path, slept, replies, expected_calls: int, why: str,
) -> None:
    """THE ONE PROPERTY THAT SEPARATES `gh_attempt` FROM `gh`, AND IT WAS
    ASSERTED NOWHERE.

    Every other test in this file reaches the retry through `act.gh`, which
    raises — so all of them stay green if the raise is pushed down into
    `gh_attempt`. Measured: doing exactly that fired ZERO tests across the whole
    tree, while breaking both callers that exist BECAUSE of the tolerance.
    `plan_activities.existing_work` degrades to a "COULD NOT BE READ" note and
    `build_activities.ci_verdict` classifies by parsing, since `gh pr checks`
    exits non-zero on a merely-red PR. A raise here turns each into a crash.

    The returned reply must also be the REAL one — `gh`'s own exit code and
    stderr, not a classified summary — because both callers read those fields.
    """
    fake = _install(monkeypatch, replies)

    r = act.gh_attempt(_READ, tmp_path)

    assert isinstance(r, subprocess.CompletedProcess)
    assert r.returncode != 0, "the caller cannot see that anything failed"
    assert r.stderr == replies[0][1], "the reply was paraphrased, not returned"
    assert len(fake.calls) == expected_calls, (
        f"{why} spent {len(fake.calls)} attempts, expected {expected_calls}")


def test_gh_attempt_runs_in_the_PROCESS_cwd_when_given_no_tree(
    monkeypatch, slept,
) -> None:
    """`None` MEANS "WHEREVER THIS PROCESS IS", NOT THE STRING "None".

    `ci_verdict` addresses its PR with an explicit `--repo` and has always run
    in the process cwd; routing it through here must not silently move it into
    a tree. Without the `is not None` guard, `cwd=str(None)` is the literal
    directory `None`, and `subprocess` fails with a `FileNotFoundError` that
    names a path nobody wrote.
    """
    seen: dict = {}

    def reply(argv, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(argv, 0, stdout="[]", stderr="")

    monkeypatch.setattr(act.subprocess, "run", reply)
    act.gh_attempt(["pr", "checks", "1"], None)

    assert seen["cwd"] is None, f"cwd was {seen['cwd']!r}, not None"


@pytest.mark.parametrize(
    ("code", "stdout", "why"),
    [
        pytest.param(1, "", "the read failed outright", id="non-zero-exit"),
        pytest.param(0, "<html>502 Bad Gateway</html>",
                     "the read succeeded and the body does not parse",
                     id="zero-exit-unparseable"),
        # THE THIRD SHAPE, AND THE ONE A DECODE GUARD ALONE LETS THROUGH.
        # `{"message": …}` parses without complaint; `len()` then succeeds and
        # `for i in issues` iterates its KEYS, so `i["number"]` raises
        # `TypeError` on a string index — a dead planning dispatch, four lines
        # below a comment promising that both ways of not getting a list reach
        # the same note. There were three ways.
        pytest.param(0, '{"message": "Not Found"}',
                     "the read succeeded and the body parsed to the wrong SHAPE",
                     id="zero-exit-json-object-not-a-list"),
        pytest.param(0, '"just a string"',
                     "the read succeeded and the body parsed to a scalar",
                     id="zero-exit-json-scalar"),
    ],
)
def test_the_tolerant_caller_DEGRADES_rather_than_killing_its_dispatch(
    monkeypatch, tmp_path, slept, code: int, stdout: str, why: str,
) -> None:
    """BOTH WAYS OF NOT GETTING AN ISSUE LIST MUST REACH THE SAME NOTE.

    `plan_activities.existing_work` is the caller `gh_attempt` was widened for:
    it wants the retries without the raise, so that losing the open-issue list
    downgrades a planning prompt instead of ending a dispatch. `gh_attempt`
    returns UNJUDGED, and a zero exit is not a promise that the body parsed —
    so the second case here reached a bare `json.loads` and killed the run,
    which is the shape `gh_json`'s docstring records as having crashed a parent
    build loop once already.

    The note itself is the assertion because it is what the model reads: a
    planning run that believes the repo has no tracked work will file a second
    home for something already tracked.
    """
    from modules.assistant.plan import plan_activities as plan

    def reply(argv, **_kwargs):
        return subprocess.CompletedProcess(argv, code, stdout=stdout, stderr="")

    monkeypatch.setattr(act.subprocess, "run", reply)
    (tmp_path / "docs" / "development").mkdir(parents=True)
    research = tmp_path / "research"
    (research / "raw").mkdir(parents=True)

    out = plan.existing_work(tmp_path, research)

    assert "COULD NOT BE READ" in out, (
        f"{why}, and the prompt did not say so — the planning run reads this as "
        f"a repo with no tracked work")
    assert "**Open issues** —" not in out, "it claimed to have read an issue list"


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
        act.gh_json(_READ, tmp_path, expect=act.GH_JSON_SHAPES)

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

    # 9 AS A LITERAL, and the derivation beside it. The derived form alone moves
    # with whichever constant was just edited, which is exactly how the sibling
    # test above measured a five-pause budget as green.
    assert len(fake.calls) == 9, (
        f"the composed bound moved: {len(fake.calls)} attempts against 9. If a "
        f"constant changed deliberately, change this number with it and say what "
        f"the new worst-case wall-clock is. TWO FIGURES, BECAUSE THEY BOUND "
        f"DIFFERENT THINGS AND THIS ASSERTION USED TO STATE ONLY THE FIRST: "
        f"added LATENCY is 3×(2.0+6.0) + 2.0+8.0 = 34s, which is what an "
        f"operator waits through when GitHub answers quickly with 503s. "
        f"WALL-CLOCK when GitHub does not answer AT ALL is "
        f"{_OUTER_ATTEMPTS}×{act._SUBPROCESS_TIMEOUT_SECONDS:.0f}s = "
        f"{_HANG_CEILING_MIN:.0f}min — {_OUTER_ATTEMPTS} and not 9, because a "
        f"timeout is TERMINAL, so `gh_attempt` spends ONE attempt per hang and "
        f"only the outer loop multiplies. Retrying a timeout instead would make "
        f"it {_IF_RETRIED_MIN:.0f}min, which is the whole argument for "
        f"classifying it terminal. "
        f"`test_a_hang_costs_ONE_attempt_here_and_THREE_on_the_composed_path` "
        f"asserts both counts rather than leaving them as prose.")
    assert len(fake.calls) == _ATTEMPTS * (len(wf._THREAD_READ_BACKOFF_SECONDS) + 1)


def test_a_decode_failure_IS_retried_by_the_one_caller_that_retries_the_TYPE(
    monkeypatch, tmp_path, slept,
) -> None:
    """`gh_json`'s "ZERO ATTEMPTS" IS TRUE AT ITS OWN LAYER AND FALSE ONE UP.

    `_read_thread_for_invariant` catches bare `RuntimeError`, and `gh_json`
    deliberately normalises a decode failure to that same type so callers guard
    one thing. Both decisions are defensible; together they mean a decode
    failure IS retried three times on this one path, which contradicts the
    plainest reading of `gh_json`'s docstring.

    PINNED RATHER THAN FIXED, and the reasoning is the caller's own: its
    alternative is discarding a ~40-minute review, and three re-reads of a
    truncated body is a cheap way to find out whether it was truncated. What is
    NOT acceptable is that the behaviour was unstated and unmeasured — a reader
    trusting the docstring would have predicted 1.

    THREE, NOT NINE. The retry underneath never fires: `gh` exited 0, so
    `gh_attempt` returns on its first attempt every time and only the OUTER loop
    spends attempts. That is the multiplication NOT happening, and it is the
    observable difference between this path and the 503 path above.
    """
    from modules.assistant.review_pr import review_pr_workflow as wf

    monkeypatch.setattr(wf.time, "sleep", lambda _s: None)
    calls: list[list[str]] = []

    def reply(argv, **_kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout="<html>502</html>",
                                           stderr="")

    monkeypatch.setattr(act.subprocess, "run", reply)

    with pytest.raises(RuntimeError, match="did not return JSON"):
        wf._read_thread_for_invariant("100", tmp_path)

    assert len(calls) == 3, (
        f"a decode failure cost {len(calls)} attempts on this path, not 3. If "
        f"that is deliberate, say so in `gh_json`'s docstring, which is where "
        f"the claim a reader checks actually lives.")
    assert len(calls) == len(wf._THREAD_READ_BACKOFF_SECONDS) + 1, (
        "the outer loop's bound moved")


# ── THE CEILING: the failure the retry could not see ───────────────────────
#
# Everything above this line runs AFTER `gh` comes back. A `gh` that never comes
# back was the one GitHub-trouble mode the policy left unbounded, at the very
# function this PR made the single launch point for every retried `gh` in the
# fleet. `time.sleep` is faked here as everywhere else in this file, and so is
# the timeout — no test below waits for anything.

class _HangingGh:
    """A `gh` that never answers, spelled the way `subprocess.run` spells it.

    RAISES `TimeoutExpired` RATHER THAN RETURNING A FAKE TIMEOUT, because the
    property under test is that `run_bounded` converts the exception into a
    reply — a fake that already returned a `TimedOutProcess` would be asserting
    the test's own construction.
    """

    def __init__(self, hangs: int = 99) -> None:
        self.hangs = hangs
        self.calls: list[list[str]] = []

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        if len(self.calls) <= self.hangs:
            raise subprocess.TimeoutExpired(argv, kwargs.get("timeout", 0))
        return subprocess.CompletedProcess(argv, 0, stdout='{"ok":true}', stderr="")


def test_every_gh_launch_carries_a_wall_clock_ceiling(monkeypatch, tmp_path) -> None:
    """THE BOUND THE RETRY DID NOT HAVE.

    `_GH_RETRY_BACKOFF_SECONDS`' comment says "Bounded, and stated so it stays
    bounded", and that was true of added LATENCY and false of wall-clock: with
    no `timeout=`, a hung `gh` parked the dispatch with no ceiling and no log
    line, because the retry only ever runs after a call RETURNS.

    ASSERTED ON THE KWARG `subprocess.run` ACTUALLY RECEIVED, not on the source
    text. A grep for `timeout` passes on a comment.
    """
    seen: list[dict] = []

    def record(argv, **kwargs):
        seen.append(kwargs)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(act.subprocess, "run", record)
    act.gh_attempt(_READ, tmp_path)

    assert seen and "timeout" in seen[0], (
        "`gh` was launched with no `timeout=` — a call that never returns is "
        "never retried and never bounded")
    assert seen[0]["timeout"] == act._SUBPROCESS_TIMEOUT_SECONDS


def test_a_hang_is_TERMINAL_and_costs_exactly_one_attempt(
    monkeypatch, tmp_path, slept, capsys,
) -> None:
    """A TIMEOUT IS NOT A TRANSIENT CLASS, AND THE BOUND IS THE REASON.

    A 503 is GitHub naming a condition a later call may satisfy. A hang names
    nothing at all, and retrying it multiplies the one number that is already
    the largest in this policy: three attempts at 120s composes under
    `_THREAD_READ_BACKOFF_SECONDS` to roughly eighteen minutes, which is worse
    than the failure it would be treating.

    THE NEGATIVE HALF MATTERS MORE THAN THE POSITIVE. A guard that bounds the
    call and then retries the bound has replaced an unbounded hang with a
    long one.
    """
    hanging = _HangingGh()
    monkeypatch.setattr(act.subprocess, "run", hanging)

    r = act.gh_attempt(_READ, tmp_path)

    assert len(hanging.calls) == 1, (
        f"a hung `gh` was launched {len(hanging.calls)} times — a timeout is "
        f"classified TERMINAL precisely so it costs one attempt")
    assert slept == [], "a hang paid the backoff it is not supposed to pay"
    assert isinstance(r, act.TimedOutProcess) and r.returncode != 0
    assert "TIMED OUT" in capsys.readouterr().out, (
        "the hang was silent — a retry policy that stops without saying why "
        "is indistinguishable from one that is broken")


def test_a_hung_WRITE_is_likewise_not_repeated(
    monkeypatch, tmp_path, slept,
) -> None:
    """THE WRITE CASE IS THE ONE THAT COSTS SOMETHING TO GET WRONG.

    A `gh pr comment` that hangs may have POSTED. Nothing in a timeout says
    whether the server applied it, which is the same reasoning `_gh_is_read_only`
    already applies to a 502 on a mutation — and the timeout branch must reach
    the same answer without going through that gate at all, since it returns
    before the read check runs.
    """
    hanging = _HangingGh()
    monkeypatch.setattr(act.subprocess, "run", hanging)

    act.gh_attempt(["pr", "comment", "101", "--body", "x"], tmp_path)

    assert len(hanging.calls) == 1, (
        f"a hung write was launched {len(hanging.calls)} times — a repeat may "
        f"double-post, and a hang gives no evidence either way")
    assert slept == []


def test_gh_RAISES_on_a_hang_and_the_message_names_the_budget(
    monkeypatch, tmp_path, slept,
) -> None:
    """`gh()`'s contract does not change: non-zero is a `RuntimeError`.

    The timeout arrives as an ordinary non-zero reply precisely so this stays
    true — no caller in the fleet grew a second exception family for it.
    """
    monkeypatch.setattr(act.subprocess, "run", _HangingGh())

    with pytest.raises(RuntimeError, match="did not answer within 120s"):
        act.gh(_READ, tmp_path)


def test_gh_attempt_STILL_RETURNS_rather_than_raising_when_gh_hangs(
    monkeypatch, tmp_path, slept,
) -> None:
    """THE TOLERANT CONTRACT SURVIVES THE NEW FAILURE MODE.

    `existing_work` and `ci_verdict` exist on the promise that `gh_attempt`
    returns a failure rather than raising it. `TimeoutExpired` escaping through
    `run_bounded` would have broken both — and it would have broken them in the
    one condition they were added to survive.
    """
    monkeypatch.setattr(act.subprocess, "run", _HangingGh())

    r = act.gh_attempt(_READ, tmp_path)   # must not raise

    assert r.returncode != 0 and "did not answer" in r.stderr


def test_a_hang_costs_ONE_attempt_here_and_THREE_on_the_composed_path(
    monkeypatch, tmp_path, slept,
) -> None:
    """THE WALL-CLOCK CEILING, PINNED THE WAY THE LATENCY BOUND ALREADY WAS.

    3 AND NOT 9, and the difference IS the terminal classification. `gh_attempt`
    spends one attempt on a hang, so only `_read_thread_for_invariant`'s loop
    multiplies: 3×120s ≈ 6min. Were a timeout treated as another transient
    class, the same path would be 9×120s + 34s ≈ 18min. A reader who has to
    derive that from two files at once will not, so it is asserted here.
    """
    from modules.assistant.review_pr import review_pr_workflow as wf

    monkeypatch.setattr(wf.time, "sleep", lambda _s: None)
    hanging = _HangingGh()
    monkeypatch.setattr(act.subprocess, "run", hanging)

    with pytest.raises(RuntimeError):
        wf._read_thread_for_invariant("100", tmp_path)

    assert len(hanging.calls) == _OUTER_ATTEMPTS, (
        f"a hang cost {len(hanging.calls)} launches on the composed path "
        f"against {_OUTER_ATTEMPTS}. {_ATTEMPTS * _OUTER_ATTEMPTS} means the "
        f"timeout became a retryable class and the ceiling is now "
        f"~{_IF_RETRIED_MIN:.0f} minutes rather than ~{_HANG_CEILING_MIN:.0f}.")
    assert len(hanging.calls) == len(wf._THREAD_READ_BACKOFF_SECONDS) + 1


def test_the_THREE_refusals_do_not_say_the_same_thing(
    monkeypatch, tmp_path, slept, capsys,
) -> None:
    """"IS IT GITHUB OR US?" NOW HAS THREE ANSWERS, AND THEY ARE DIFFERENT.

    A 404 says us. A 503 on a write says GitHub, and we stopped anyway because
    a repeat may double-apply. A hang says GitHub told us NOTHING, and we
    stopped because repeating an unbounded call is how a bounded policy stops
    being one. One label for three facts answers the question wrongly two thirds
    of the time — and the first two of these were one label until a prior pass
    split them, which is why the third is asserted rather than assumed.
    """
    _install(monkeypatch, [(1, _REST_404)])
    act.gh_attempt(_READ, tmp_path)
    terminal = capsys.readouterr().out

    _install(monkeypatch, [(1, _LIVE_503)])
    act.gh_attempt(["pr", "comment", "1", "--body", "x"], tmp_path)
    write = capsys.readouterr().out

    monkeypatch.setattr(act.subprocess, "run", _HangingGh())
    act.gh_attempt(_READ, tmp_path)
    hang = capsys.readouterr().out

    assert "TERMINAL" in terminal and "NOT A READ" not in terminal
    assert "NOT A READ" in write and "TIMED OUT" not in write
    assert "TIMED OUT" in hang, "a hang was reported as one of the other two"
    assert len({terminal, write, hang}) == 3, (
        "two of the three refusals print the same line")


def test_a_hung_git_FETCH_is_fatal_the_way_a_failed_one_is(
    monkeypatch, tmp_path,
) -> None:
    """THE SAME CLASS, ONE LAYER OUT AND BEFORE ANY `gh` RUNS.

    `worktree_add`'s fetch is the first network call a dispatch makes, and its
    own docstring argues at length that a failed fetch must be FATAL because a
    stale local ref would otherwise let the run plan on a base that has moved.
    A hung fetch had neither outcome: it simply never returned. Routing it
    through `run_bounded` makes a timeout arrive as the non-zero reply that
    docstring already reasoned about, so the fatal branch fires unchanged.
    """
    monkeypatch.setattr(act.subprocess, "run", _HangingGh())

    with pytest.raises(RuntimeError, match="git fetch origin"):
        act.worktree_add(tmp_path, "wt", "origin/main")

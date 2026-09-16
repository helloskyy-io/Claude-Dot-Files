"""Capture is evidence about the paper, and it must never cost the paper.

THE BINDING CONSTRAINT, ruled by the operator via SN-PM2: a source that 404s,
times out or trips the fetch policy is a RECORDED capture-failure on that
citation — never a failed research run. A dead run because a footnote link
rotted is the wrong failure. Every test below exists to hold that, or to stop
the sweep reporting success for work it did not do.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.assistant.research.capture_cited_sources import (
    SIDECAR_NAME, CaptureReport, capture_cited_sources, read_sidecar)

ROW = {"claim_id": "c1", "quote": "the exact characters", "url": "https://e.invalid/a"}


def _pool(tmp_path: Path, rows=None, raw: str | None = None) -> Path:
    p = tmp_path / "pool"
    (p / "raw").mkdir(parents=True)
    (p / "raw" / "topic.md").write_text("# Topic\n", encoding="utf-8")
    if raw is not None:
        (p / SIDECAR_NAME).write_text(raw, encoding="utf-8")
    elif rows is not None:
        (p / SIDECAR_NAME).write_text(json.dumps(rows), encoding="utf-8")
    return p


def test_a_PAIRED_CITATION_IS_CAPTURED(tmp_path: Path) -> None:
    """The positive control. Without it every assertion below is satisfied by a
    sweep that captures nothing at all."""
    seen = []
    r = capture_cited_sources(pool_dir=_pool(tmp_path, [ROW]), bag=object(),
                              stage="research",
                              capture_fn=lambda **kw: seen.append(kw))
    assert r.captured == 1 and not r.failed
    assert seen[0]["url"] == ROW["url"] and seen[0]["quote"] == ROW["quote"]


@pytest.mark.parametrize("boom", [
    ConnectionError("connection refused"),
    TimeoutError("read timed out"),
    ValueError("refused: redirects to a private address"),
    RuntimeError("some bug nobody predicted"),
])
def test_A_FETCH_FAILURE_IS_RECORDED_AND_NEVER_RAISED(tmp_path: Path, boom) -> None:
    """⚠ THE CONSTRAINT. Parametrized over four unrelated exception types because
    the rule is about the RUN, not about a list of anticipated errors — a bug in
    the fetcher or the store is still not a reason to lose a completed paper.
    """
    def _explode(**kw):
        raise boom

    r = capture_cited_sources(pool_dir=_pool(tmp_path, [ROW]), bag=object(),
                              stage="research", capture_fn=_explode)
    assert r.captured == 0
    assert len(r.failed) == 1
    url, reason = r.failed[0]
    assert url == ROW["url"]
    assert type(boom).__name__ in reason and str(boom) in reason, (
        f"the reason must tell a rotted link from a policy refusal: {reason}")


def test_ONE_BAD_CITATION_DOES_NOT_STOP_THE_REST(tmp_path: Path) -> None:
    """A sweep that aborts on the first failure captures nothing for a paper whose
    very first link rotted, which is the common case rather than the rare one."""
    rows = [dict(ROW, claim_id="c1", url="https://e.invalid/dead"),
            dict(ROW, claim_id="c2", url="https://e.invalid/live"),
            dict(ROW, claim_id="c3", url="https://e.invalid/also-live")]

    def _one_dead(**kw):
        if kw["url"].endswith("dead"):
            raise ConnectionError("gone")

    r = capture_cited_sources(pool_dir=_pool(tmp_path, rows), bag=object(),
                              stage="research", capture_fn=_one_dead)
    assert r.captured == 2 and len(r.failed) == 1


def test_A_ROW_MISSING_ITS_QUOTE_IS_SKIPPED_NOT_FAILED(tmp_path: Path) -> None:
    """The store REFUSES a citation with no quoted span, so an unpaired URL is not
    capturable. It is counted as SKIPPED rather than FAILED because nothing was
    attempted — calling it a failed fetch would misdescribe what happened, and the
    remedy is the run's artifact rather than the source.
    """
    rows = [dict(ROW), {"claim_id": "c2", "url": "https://e.invalid/b"},
            {"quote": "q", "url": "https://e.invalid/c"}]
    r = capture_cited_sources(pool_dir=_pool(tmp_path, rows), bag=object(),
                              stage="research", capture_fn=lambda **kw: None)
    assert r.captured == 1 and r.skipped == 2 and not r.failed


def test_NO_SIDECAR_IS_REPORTED_NOT_TREATED_AS_CLEAN(tmp_path: Path) -> None:
    """⚠ VACUITY CONTROL. A run that paired nothing captured nothing, and a sweep
    that says so is telling the truth — one that returns quietly reads as "all
    sources captured" for a paper with no capture at all.
    """
    r = capture_cited_sources(pool_dir=_pool(tmp_path), bag=object(),
                              stage="research", capture_fn=lambda **kw: None)
    assert r.captured == 0 and r.sidecar is None
    assert "NOT RUN" in r.as_note() and "did not pair" in r.as_note()


def test_A_MALFORMED_SIDECAR_IS_A_FINDING_NOT_AN_EXCEPTION(tmp_path: Path) -> None:
    """Unparseable JSON is a bad artifact the run produced, not a reason to lose
    the paper it also produced. The mutation is the artifact itself."""
    r = capture_cited_sources(pool_dir=_pool(tmp_path, raw="{not json"), bag=object(),
                              stage="research", capture_fn=lambda **kw: None)
    assert r.parse_error and "NOT RUN" in r.as_note()

    rows, err = read_sidecar(_pool(tmp_path / "two", raw='{"a": 1}'))
    assert rows == [] and "array" in err


def test_THE_NOTE_NAMES_THE_FAILURES_A_READER_MUST_ACT_ON(tmp_path: Path) -> None:
    """A count with no URLs is a number an operator cannot act on."""
    r = CaptureReport(captured=1, sidecar=Path("x"),
                      failed=[("https://e.invalid/z", "ConnectionError: gone")])
    note = r.as_note()
    assert "1 captured" in note and "1 failed" in note
    assert "https://e.invalid/z" in note and "ConnectionError" in note


# --- the sidecar's well-formedness, the coverage figure, and the gap -------------
#
# Added when skyynet-master-planning#36 showed the store empty on a cited paper
# with nothing red. The tests above hold "capture never fails the run"; these hold
# the other half — "an empty store for a cited paper is never silent" — and the
# seam between them: a per-citation failure is a row, not a gap.

from modules.assistant.research.capture_cited_sources import (  # noqa: E402
    GAP_WRITE_PATH, cited_sources, papers_changed, record_capture_gap, validate_rows)

SHA = "0c87594975195608dc91b3f702e250a7b240c151"


class _Emitter:
    """Records `record_gap` calls; the real one is exercised in the integration tier."""
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def record_gap(self, **kw) -> None:
        self.calls.append(kw)


def test_validate_rows_KEEPS_a_row_whose_optional_field_is_wrong_and_SAYS_so() -> None:
    """A 7-char sha is a bookkeeping defect, not a reason to lose the bytes: the
    fetch needs the URL, and dropping a real source over a short sha would be the
    capture path manufacturing its own gap. The problem is still reported."""
    rows = [dict(ROW, sha="0c87594"), dict(ROW, claim_id="c2", paper="synthesis.md"),
            dict(ROW, claim_id="c3", sha=SHA, paper="raw/t.md")]
    ok, problems = validate_rows(rows)
    assert [r["claim_id"] for r in ok] == ["c1", "c2", "c3"]
    assert len(problems) == 2
    assert "40-hex" in problems[0] and "raw/" in problems[1]


def test_validate_rows_DROPS_a_row_missing_a_required_field_or_carrying_a_non_url() -> None:
    rows = [ROW, {"claim_id": "c2", "url": "https://e.invalid/b"},
            dict(ROW, claim_id="c3", url="ftp://e.invalid/c"),
            dict(ROW, claim_id="c4", url="https://e.invalid/with space")]
    ok, problems = validate_rows(rows)
    assert [r["claim_id"] for r in ok] == ["c1"]
    assert len(problems) == 3
    assert "missing ['quote']" in problems[0]
    assert "not an http(s) URL" in problems[1] and "not an http(s) URL" in problems[2]


def test_a_MALFORMED_optional_field_is_captured_and_NAMED_in_the_note(tmp_path: Path) -> None:
    rows = [dict(ROW, sha="short")]
    r = capture_cited_sources(pool_dir=_pool(tmp_path, rows), bag=object(),
                              stage="research", capture_fn=lambda **kw: None)
    assert r.captured == 1 and r.skipped == 0
    assert len(r.malformed) == 1 and "MALFORMED row 0" in r.as_note()


def test_cited_sources_COUNTS_DISTINCT_URLS_not_markers(tmp_path: Path) -> None:
    """A source quoted twice is one source — which is also how the store sees it —
    and a trailing sentence stop is punctuation, not part of the URL."""
    p = tmp_path / "a.md"
    p.write_text("See https://e.invalid/x and again https://e.invalid/x. Also "
                 "[B2] (https://e.invalid/y) and `https://e.invalid/z`.\n"
                 "A relative link (../guide/x.md) is not a source.\n", encoding="utf-8")
    assert cited_sources([p]) == 3
    assert cited_sources([tmp_path / "missing.md"]) == 0


def test_the_GUARD_PREDICATE_fires_only_for_a_cited_paper_with_an_EMPTY_store() -> None:
    """The four corners, and the one that is easy to get wrong: `cited is None`
    means the paper set could not be read, and unknown coverage is INCOMPLETE
    coverage — a bag must not read as complete on a check that did not run."""
    assert CaptureReport(cited=4, captured=0).store_is_empty_for_a_cited_paper
    assert CaptureReport(cited=None, captured=0).store_is_empty_for_a_cited_paper
    assert not CaptureReport(cited=4, captured=1).store_is_empty_for_a_cited_paper
    assert not CaptureReport(cited=0, captured=0).store_is_empty_for_a_cited_paper
    # A per-citation failure with the rest stored is NOT the predicate — that is
    # the invariant the tests above hold, seen from this side.
    assert not CaptureReport(cited=4, captured=3,
                             failed=[("u", "gone")]).store_is_empty_for_a_cited_paper


def test_record_capture_gap_EMITS_the_typed_class_and_MARKS_nothing_otherwise(tmp_path: Path) -> None:
    from modules.journal.events import GapClass
    em = _Emitter()
    pool = tmp_path / "pool"
    fired = CaptureReport(cited=3, captured=0)
    assert record_capture_gap(fired, emitter=em, pool_dir=pool) is True
    assert len(em.calls) == 1
    call = em.calls[0]
    assert call["gap_class"] is GapClass.SOURCES_UNCAPTURED
    assert call["write_path"] == GAP_WRITE_PATH
    assert call["destination"].store == "content_store"
    assert call["destination"].address == str(pool)
    assert call["lost_bytes"] == 0          # UNKNOWN, not zero — nothing was fetched
    assert "0/3" in call["detail"]

    quiet = _Emitter()
    assert record_capture_gap(CaptureReport(cited=3, captured=3), emitter=quiet, pool_dir=pool) is False
    assert record_capture_gap(CaptureReport(cited=0, captured=0), emitter=quiet, pool_dir=pool) is False
    assert quiet.calls == []


def test_the_note_is_LOUD_when_the_store_is_empty_for_a_cited_paper() -> None:
    """The `NOT RUN` line was true and unread. The loud form leads with the
    consequence — the bag is INCOMPLETE — and names the gap class, so an operator
    scanning notes cannot take it for a benign no-op."""
    silent_before = CaptureReport(cited=28, captured=0).as_note()
    assert silent_before.startswith("⚠ CONTENT STORE EMPTY FOR A CITED PAPER")
    assert "INCOMPLETE" in silent_before and "sources_uncaptured" in silent_before
    assert "coverage 0/28" in silent_before
    # And NOT loud when there was nothing to capture, or when something was.
    assert "⚠" not in CaptureReport(cited=0).as_note()
    assert "⚠" not in CaptureReport(cited=2, captured=1, captured_urls={"u"},
                                    sidecar=Path("x")).as_note()
    assert "coverage UNKNOWN" in CaptureReport(cited=None).as_note()


def test_the_paper_set_is_THE_DIFF_not_the_pool_and_unreadable_is_None(tmp_path: Path) -> None:
    """A mature pool holds papers that predate the sidecar; counting their URLs
    would trip the guard on every run for history no run can fix. Only the papers
    on the branch count — and a git that cannot answer returns None, never []."""
    import subprocess
    wt = tmp_path / "wt"
    (wt / "pool" / "raw").mkdir(parents=True)
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin"}

    def git(*a):
        subprocess.run(["git", *a], cwd=wt, check=True, capture_output=True, env=env)

    git("init", "-q", "-b", "main")
    (wt / "pool" / "raw" / "legacy.md").write_text("https://e.invalid/old\n")
    git("add", "-A"); git("commit", "-q", "-m", "base")
    git("checkout", "-q", "-b", "run")
    (wt / "pool" / "raw" / "new.md").write_text("https://e.invalid/new\n")
    (wt / "pool" / "synthesis.md").write_text("https://e.invalid/synth\n")
    git("add", "-A"); git("commit", "-q", "-m", "run")

    papers = papers_changed(wt / "pool", wt, "main")
    assert papers == [wt / "pool" / "raw" / "new.md"]
    assert cited_sources(papers) == 1

    assert papers_changed(wt / "pool", wt, "no-such-ref") is None
    assert papers_changed(tmp_path / "elsewhere", wt, "main") is None

    # Through the sweep: a pool nobody diffed reports UNKNOWN, not zero.
    r = capture_cited_sources(pool_dir=wt / "pool", bag=object(), stage="research",
                              capture_fn=lambda **kw: None)
    assert r.cited is None and r.store_is_empty_for_a_cited_paper
    r = capture_cited_sources(pool_dir=wt / "pool", bag=object(), stage="research",
                              capture_fn=lambda **kw: None, worktree=wt, base="main")
    assert r.cited == 1 and r.papers == ["pool/raw/new.md"]

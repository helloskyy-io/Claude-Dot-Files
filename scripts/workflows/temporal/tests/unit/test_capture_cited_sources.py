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

"""Capture and resolve — the store's two I/O boundaries, and what they refuse.

REQUIREMENT 8's ARGUMENT IS THAT A SOURCE READ THROUGH A NON-CAPTURING PATH IS A
CITATION NOBODY CAN RE-CHECK, AND IT FAILS SILENTLY. There is no error, no
missing file and nothing to notice until somebody tries to verify a claim and
finds no bytes behind it. This file asserts the two boundaries do what they say
and, in `test_a_citation_with_no_captured_bytes_FAILS_CLOSED`, that the silence
is broken by `verify` rather than by hope.

r7(c)'s RULING IS VISIBLE HERE AS TWO ENTRY FUNCTIONS WITH DIFFERENT DEFAULTS.
The harvest path defaults to the weaker guarantee because that is what it is; the
bytes-in-hand path defaults to the stronger one because a caller that had the
bytes as the source was read is the routed arm this phase did not take. Neither
default is a claim about the fleet — the row records which was used.

WHAT THIS FILE DOES NOT LOOK AT: it never exercises the fetch policy against a
hostile URL (`test_source_fetch.py` owns that), and it does not re-derive the
store's hashing (`test_content_store.py`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.journal.bag import open_bag
from modules.journal.citations import (CAPTURE_HARVEST, CAPTURE_READ_TIME,
                                       CITATIONS_FILE, CitationError,
                                       read_citations)
from modules.journal.content_activities import (capture_code_citation,
                                                capture_fetched_source,
                                                capture_source,
                                                resolve_citation)
from modules.journal.content_store import load_object, object_path
from modules.journal.verify import MISSING, VERIFIED, verify_bag, verify_citation

PAGE = b"<p>a source the run read</p>"
SHA = "0123456789abcdef0123456789abcdef01234567"


@pytest.fixture
def bag(root: Path):
    return open_bag(root, "run-activities")


def test_capturing_bytes_in_hand_stores_them_and_records_the_row(bag) -> None:
    citation = capture_fetched_source(
        bag=bag, stage="draft", claim_id="c1", quote="a source the run read",
        source_ref="https://example.org/a", data=PAGE)
    assert citation.capture == CAPTURE_READ_TIME
    assert load_object(bag.path, citation.page_content_hash) == PAGE
    assert read_citations(bag.path) == [citation]
    assert verify_citation(bag.path, citation).outcome == VERIFIED


def test_a_stage_capturing_a_SECOND_source_appends_to_its_own_file(bag) -> None:
    """`Bag.writer_dir` allocates a NAME NOBODY ELSE GETS, which is right for a
    writer claiming a workspace and wrong for a stage citing twice — its second
    source must land beside the first, not in `draft-2`."""
    for index in range(3):
        capture_fetched_source(bag=bag, stage="draft", claim_id=f"c{index}",
                               quote="a source", source_ref="https://example.org/a",
                               data=f"source {index}".encode())
    assert [p.name for p in sorted(bag.payload_dir.iterdir())
            if p.is_dir() and p.name != "content-store"] == ["draft"]
    assert (bag.payload_dir / "draft" / CITATIONS_FILE).read_text().count("\n") == 3


@pytest.mark.parametrize("stage", ["../escape", "/absolute", "..", "a/b/c"])
def test_a_HOSTILE_STAGE_NAME_cannot_escape_the_payload(bag, stage: str) -> None:
    """⚠ THIS ESCAPED, AND `test_journal_containment` IS WHAT SAID SO.

    The first version of `_writer_directory` composed the caller's stage onto
    the payload path directly — the fifth instance of this package's own
    containment class, written by the pass that had just read the module
    documenting the other four. The remedy was the two rules `Bag.writer_dir`
    already keeps, reached by name rather than re-implemented.
    """
    citation = capture_fetched_source(
        bag=bag, stage=stage, claim_id="c1", quote="a source",
        source_ref="https://example.org/a", data=PAGE)
    written = [p for p in bag.path.rglob(CITATIONS_FILE)]
    assert len(written) == 1
    assert bag.payload_dir in written[0].parents, (
        f"{written[0]} landed outside the payload directory")
    assert citation.stage == stage, (
        "the ROW keeps the stage the caller named — sanitising is a path rule, "
        "and rewriting the record would lose what the run actually called it")


def test_a_harvested_row_carries_the_WEAKER_guarantee(bag) -> None:
    """The provenance is data, so nothing downstream has to assume which arm ran."""
    class Fake:
        pass

    import modules.journal.content_activities as mod
    captured = {}

    def fake_fetch(url, *, policy=None):
        captured["url"] = url
        return type("F", (), {"final_url": url, "data": PAGE,
                              "media_type": "text/html"})()

    original = mod.fetch_source
    mod.fetch_source = fake_fetch
    try:
        citation = capture_source(bag=bag, stage="harvest", claim_id="c1",
                                  quote="a source the run read",
                                  url="https://example.org/a")
    finally:
        mod.fetch_source = original

    assert captured["url"] == "https://example.org/a"
    assert citation.capture == CAPTURE_HARVEST
    assert verify_citation(bag.path, citation).outcome == VERIFIED


def test_the_capture_path_does_NOT_check_the_span(bag) -> None:
    """A wrong quotation is a FINDING about the record, not a capture failure.

    Refusing here would move the finding out of `verify` — where an operator
    reads it as one of four outcomes — and into the run, where it becomes an
    error the run has to handle mid-flight.
    """
    citation = capture_fetched_source(
        bag=bag, stage="draft", claim_id="c1", quote="never on that page",
        source_ref="https://example.org/a", data=PAGE)
    assert citation.page_content_hash is not None
    assert verify_citation(bag.path, citation).outcome == "span-missing"


def test_a_code_citation_STORES_NOTHING(bag) -> None:
    """Requirement 6. Git is already content-addressed; a copy can drift."""
    citation = capture_code_citation(bag=bag, stage="draft", claim_id="c1",
                                     quote="def f():", commit_sha=SHA, path="f.py")
    assert citation.source_ref == f"git:{SHA}:f.py"
    assert citation.page_content_hash is None
    assert not (bag.payload_dir / "content-store").exists()


def test_an_abbreviated_sha_is_refused_at_the_boundary(bag) -> None:
    with pytest.raises(CitationError):
        capture_code_citation(bag=bag, stage="draft", claim_id="c1", quote="q",
                              commit_sha=SHA[:8])


def test_an_unknown_capture_kind_is_refused(bag) -> None:
    """It records WHICH guarantee the row carries, so it has no default here."""
    with pytest.raises(CitationError):
        capture_fetched_source(bag=bag, stage="draft", claim_id="c1", quote="q",
                               source_ref="https://example.org/a", data=PAGE,
                               capture="probably")


def test_resolve_is_the_STORE_read_and_adds_nothing(bag) -> None:
    citation = capture_fetched_source(
        bag=bag, stage="draft", claim_id="c1", quote="a source",
        source_ref="https://example.org/a", data=PAGE)
    assert resolve_citation(bag=bag, citation=citation) == PAGE

    object_path(bag.path, citation.page_content_hash).write_bytes(b"changed")
    with pytest.raises(Exception) as caught:
        resolve_citation(bag=bag, citation=citation)
    assert "TAMPERED" in str(caught.value), (
        "resolve must be `load_object` and not a softer read — a second resolver "
        "is exactly what r7(d) exists to prevent")


def test_resolve_REFUSES_to_guess_which_checkout_a_sha_belongs_to(bag) -> None:
    citation = capture_code_citation(bag=bag, stage="draft", claim_id="c1",
                                     quote="q", commit_sha=SHA)
    with pytest.raises(CitationError) as caught:
        resolve_citation(bag=bag, citation=citation)
    assert "git" in str(caught.value)


def test_a_citation_with_no_captured_bytes_FAILS_CLOSED(bag) -> None:
    """REQUIREMENT 8's ACTUAL ENFORCEMENT, and the docstrings say so plainly.

    An activity boundary does not make the call happen — nothing forces a
    workflow to capture before it cites. What breaks the silence is `verify`
    reporting `missing` with a non-zero exit for a citation naming a digest
    nothing was stored under, so a read path that skipped capture surfaces as a
    finding rather than as an empty result.
    """
    citation = capture_fetched_source(
        bag=bag, stage="draft", claim_id="c1", quote="a source",
        source_ref="https://example.org/a", data=PAGE)
    object_path(bag.path, citation.page_content_hash).unlink()

    report = verify_bag(bag.path)
    assert not report.ok
    assert report.counts()[MISSING] == 1

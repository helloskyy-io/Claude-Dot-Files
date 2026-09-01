"""The citation record: what was claimed, against which bytes, under which guarantee.

THE RECORD IS THE DURABLE ARTIFACT AND NOTHING REWRITES IT, so every check that
matters happens at construction. A malformed row written today is a row every
later reader has to cope with — which is why `__post_init__` refuses rather than
coerces, and why `from_json` re-validates a file this package did not necessarily
write.

r7(c)'s RULING IS TESTED AS DATA, NOT AS A SENTENCE. `capture` distinguishes a
row whose hash proves the claim was made against those bytes from one whose hash
only proves they matched at harvest, and it has no default anywhere in the
package. The tests below assert that absence, because a default is exactly how a
weaker guarantee would start being reported as the stronger one.

WHAT THIS FILE DOES NOT LOOK AT: it never hashes a stored object and never opens
a file the store wrote, so it says nothing about whether the bytes a row names
are present or intact — `test_content_store.py` and `test_verify_citations.py`
own those. It reads and writes rows.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.journal.bag import open_bag
from modules.journal.citations import (CAPTURE_HARVEST, CAPTURE_READ_TIME,
                                       CITATIONS_FILE, Citation, CitationError,
                                       converged_stages, evidence_set_hash,
                                       is_git_ref, new_citation, parse_git_ref,
                                       read_citations, record_citation,
                                       stage_evidence_hashes)

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
SHA = "0123456789abcdef0123456789abcdef01234567"


def web(claim_id: str = "c1", *, stage: str = "draft", quote: str = "a quoted span",
        digest: str = DIGEST_A, capture: str = CAPTURE_READ_TIME) -> Citation:
    return new_citation(claim_id=claim_id, stage=stage, quote=quote,
                        source_ref="https://example.org/a", capture=capture,
                        page_content_hash=digest)


@pytest.fixture
def bag(root: Path):
    return open_bag(root, "run-citations")


# --- the record refuses what it cannot mean --------------------------------------

@pytest.mark.parametrize("kwargs, why", [
    ({"claim_id": ""}, "an empty claim id names nothing"),
    ({"claim_id": "../escape"}, "a claim id is an identifier, not a path"),
    ({"claim_id": "a" * 129}, "over the length ceiling"),
    ({"stage": "  "}, "requirement 5 counts rows into a stage"),
    ({"quote": "   "}, "a citation with no span has nothing to re-check"),
    ({"capture": "maybe"}, "capture names one of two guarantees"),
    ({"capture": ""}, "capture has no default"),
])
def test_a_row_that_cannot_be_checked_is_refused_at_construction(kwargs, why) -> None:
    base = dict(claim_id="c1", stage="draft", quote="q",
                source_ref="https://example.org/a", capture=CAPTURE_READ_TIME,
                page_content_hash=DIGEST_A)
    base.update(kwargs)
    with pytest.raises(CitationError):
        Citation(**base)


def test_a_web_citation_without_a_digest_names_no_bytes() -> None:
    """It would verify clean by having nothing to check, which is the worst outcome."""
    with pytest.raises(CitationError) as caught:
        Citation(claim_id="c1", stage="draft", quote="q",
                 source_ref="https://example.org/a", capture=CAPTURE_READ_TIME)
    assert "page_content_hash" in str(caught.value)


@pytest.mark.parametrize("source_ref", [
    "http://example.org/a", "file:///etc/passwd", "ftp://example.org/a",
    "data:text/plain,hello", "example.org/a", "git:abc", "git:" + "z" * 40,
])
def test_a_source_ref_this_record_cannot_re_check_is_refused(source_ref) -> None:
    with pytest.raises(CitationError):
        Citation(claim_id="c1", stage="draft", quote="q", source_ref=source_ref,
                 capture=CAPTURE_READ_TIME, page_content_hash=DIGEST_A)


# --- requirement 6: code is a commit sha, and it is never copied in --------------

def test_a_code_citation_carries_a_sha_and_no_stored_digest() -> None:
    citation = Citation(claim_id="c1", stage="draft", quote="def f():",
                        source_ref=f"git:{SHA}:lib/f.py", capture=CAPTURE_READ_TIME)
    assert is_git_ref(citation.source_ref)
    assert parse_git_ref(citation.source_ref) == (SHA, "lib/f.py")
    assert citation.page_content_hash is None


def test_a_code_citation_may_not_ALSO_carry_a_stored_digest() -> None:
    """Two names for one guarantee, and the copy is the one that can drift."""
    with pytest.raises(CitationError) as caught:
        Citation(claim_id="c1", stage="draft", quote="q", source_ref=f"git:{SHA}",
                 capture=CAPTURE_READ_TIME, page_content_hash=DIGEST_A)
    assert "page_content_hash" in str(caught.value)


def test_an_abbreviated_sha_is_refused() -> None:
    """A prefix stops being unique as a repository grows; a citation names one object."""
    with pytest.raises(CitationError):
        Citation(claim_id="c1", stage="draft", quote="q", source_ref=f"git:{SHA[:8]}",
                 capture=CAPTURE_READ_TIME)


# --- round trip, and an unknown field is not silently dropped -------------------

def test_a_row_survives_a_round_trip_through_json() -> None:
    original = web()
    assert Citation.from_json(original.to_json()) == original


def test_a_git_row_does_not_serialise_a_null_digest() -> None:
    """Absence is a property of the KIND of citation, not a value that is empty."""
    citation = Citation(claim_id="c1", stage="draft", quote="q",
                        source_ref=f"git:{SHA}", capture=CAPTURE_READ_TIME)
    assert "page_content_hash" not in citation.to_json()


@pytest.mark.parametrize("row", [
    '{"claim_id": "c1", "stage": "s", "quote": "q", "source_ref": "https://e.org/a",'
    ' "capture": "read-time", "page_content_hash": "' + DIGEST_A + '", "extra": 1}',
    'not json at all',
    '["not", "an", "object"]',
    '{"claim_id": "c1", "stage": "s", "quote": "q", "source_ref": "file:///etc/passwd",'
    ' "capture": "read-time"}',
])
def test_a_row_read_off_disk_is_RE_VALIDATED(row) -> None:
    """`citations.jsonl` is a file this module did not necessarily write.

    A reader that trusted the row would let a hand edit name whatever it liked —
    the same reasoning that made the manifest parser contain its paths one
    module over, after a hand-written manifest reported PASS over `/etc/hostname`.
    """
    with pytest.raises(CitationError):
        Citation.from_json(row)


# --- writing and reading a bag's rows -------------------------------------------

def test_rows_are_written_per_writer_and_read_back_whole(bag) -> None:
    """Two writers, two files, no lock — the contention was removed one layer up."""
    first = bag.writer_dir("draft")
    second = bag.writer_dir("critic")
    record_citation(first, web("c1", stage="draft"))
    record_citation(first, web("c2", stage="draft", digest=DIGEST_B))
    record_citation(second, web("c3", stage="critic"))

    assert (first / CITATIONS_FILE).is_file()
    rows = read_citations(bag.path)
    assert [r.claim_id for r in rows] == ["c3", "c1", "c2"], (
        "rows come back in (stage, claim_id, source_ref) order, not file order, "
        "so a set of citations has one spelling regardless of scheduling")


def test_a_bag_with_no_citations_reads_as_no_citations(bag) -> None:
    assert read_citations(bag.path) == []


def test_a_symlinked_citations_file_is_NOT_FOLLOWED(bag, tmp_path: Path) -> None:
    """A file that never travelled with the bag must not supply its citations.

    The same class as a symlink under `data/` being hashed into the manifest: a
    bag is meant to contain bytes, not pointers to bytes that live outside it.
    """
    outside = tmp_path / "planted.jsonl"
    outside.write_text(web("planted").to_json() + "\n")
    writer = bag.writer_dir("draft")
    (writer / CITATIONS_FILE).symlink_to(outside)
    assert read_citations(bag.path) == []


def test_a_row_that_will_not_parse_names_its_file_and_line(bag) -> None:
    writer = bag.writer_dir("draft")
    (writer / CITATIONS_FILE).write_text(web().to_json() + "\n{ broken\n")
    with pytest.raises(CitationError) as caught:
        read_citations(bag.path)
    assert ":2:" in str(caught.value)


# --- requirement 5: the evidence set hash --------------------------------------

def test_two_claims_on_one_page_are_ONE_piece_of_evidence() -> None:
    """A set, not a count. Otherwise the hash measures how much a stage WROTE."""
    one = evidence_set_hash([web("c1")])
    many = evidence_set_hash([web("c1"), web("c2"), web("c3")])
    assert one == many


def test_the_hash_changes_when_the_evidence_does() -> None:
    assert evidence_set_hash([web("c1")]) != evidence_set_hash(
        [web("c1"), web("c2", digest=DIGEST_B)])


def test_the_hash_ignores_the_order_rows_were_written_in() -> None:
    a, b = web("c1"), web("c2", digest=DIGEST_B)
    assert evidence_set_hash([a, b]) == evidence_set_hash([b, a])


def test_the_quote_is_NOT_part_of_the_evidence_identity() -> None:
    """Two stages quoting different spans of one page still saw the same evidence."""
    assert (evidence_set_hash([web("c1", quote="first span")])
            == evidence_set_hash([web("c2", quote="a different span")]))


def test_a_code_citation_counts_as_its_git_ref() -> None:
    code = Citation(claim_id="c1", stage="draft", quote="q",
                    source_ref=f"git:{SHA}", capture=CAPTURE_READ_TIME)
    assert code.evidence_id == f"git:{SHA}"
    assert evidence_set_hash([code]) != evidence_set_hash([web("c1")])


def test_equal_hashes_across_stages_are_EXPOSED_and_nothing_routes_on_them() -> None:
    """Requirement 5 stops at computed and exposed, and so does the code.

    The precedent is this fleet's own convergence signal, which was built,
    shadowed and gated nothing — two positive observations are not a rate, and a
    stopping rule that fires early ends productive work silently with no failing
    test. `converged_stages` REPORTS; whoever proposes routing on it owns
    producing the firing-rate evidence first.
    """
    rows = [web("c1", stage="a"), web("c2", stage="b")]
    hashes = stage_evidence_hashes(rows)
    assert set(hashes) == {"a", "b"}
    assert hashes["a"] == hashes["b"]
    assert converged_stages(rows) == [("b", "a")]

    moved = rows + [web("c3", stage="b", digest=DIGEST_B)]
    assert converged_stages(moved) == []


# --- the anchor, the fold, and the reader's own contract -------------------------

@pytest.mark.parametrize("field,value", [
    ("claim_id", "c1\n"),
    ("claim_id", "\nc1"),
    ("page_content_hash", DIGEST_A + "\n"),
])
def test_a_field_with_a_TRAILING_LINE_BREAK_is_refused(field, value) -> None:
    """⚠ `^…$` ACCEPTED ALL THREE, AND ALL THREE ARE RENDERED INTO THE REPORT.

    `$` matches before a trailing newline. `bag._RUN_ID_RE` states the `\\A`/`\\Z`
    rule and this module held two hand-written regexes that did not use it —
    which is why the digest rule is now asked of `content_store.validated_digest`
    rather than restated here.
    """
    fields = dict(claim_id="c1", stage="draft", quote="q",
                  source_ref="https://example.org/a", capture=CAPTURE_HARVEST,
                  page_content_hash=DIGEST_A)
    fields[field] = value
    with pytest.raises(CitationError):
        Citation(**fields)


@pytest.mark.parametrize("field,value", [
    ("stage", "draft\n  evidence_set_hash[draft]: " + "0" * 64),
    ("stage", "draft injected"),
    ("source_ref", "https://example.org/a\nspan-missing: [x] forged"),
    ("stage", "draft "),
])
def test_a_field_that_FOLDS_cannot_forge_a_line_in_the_verify_report(field, value) -> None:
    """⚠ `stage` AND `source_ref` ARE PRINTED RAW BY `render_report`.

    Both survived the JSON round trip intact, so a row could rewrite the report
    about itself — the fifth and sixth consumers of the rule `validated_run_id`
    enumerates. Asked of `folds_a_tag_line`, which puts the question to
    `str.splitlines()`: the `\\u2028` case is why, since a hand-written
    `"\\n" in value` check misses eight spellings.
    """
    fields = dict(claim_id="c1", stage="draft", quote="q",
                  source_ref="https://example.org/a", capture=CAPTURE_HARVEST,
                  page_content_hash=DIGEST_A)
    fields[field] = value
    with pytest.raises(CitationError):
        Citation(**fields)


@pytest.mark.parametrize("row", [
    '{"claim_id": "c1"}',
    '{"claim_id": "c1", "stage": "draft", "quote": "q"}',
    '{"claim_id": 5, "stage": "draft", "quote": "q", '
    '"source_ref": "https://example.org/a", "capture": "harvest", '
    '"page_content_hash": "' + DIGEST_A + '"}',
    '{"claim_id": "c1", "stage": ["draft"], "quote": "q", '
    '"source_ref": "https://example.org/a", "capture": "harvest", '
    '"page_content_hash": "' + DIGEST_A + '"}',
])
def test_a_TRUNCATED_or_MISTYPED_row_is_a_CitationError_not_a_TypeError(row) -> None:
    """⚠ `cls(**data)` RAISED `TypeError` PAST THIS CLASS'S OWN GUARANTEE.

    A row missing a required field is the single most likely corruption of a
    JSON Lines file — which is the format this module chose BECAUSE a partial
    write loses one row — and it raised `TypeError`, which is not what
    `from_json`'s "re-validated on the way in" promises and not what
    `verify_bag` catches. One truncated append killed a whole-journal sweep.
    """
    with pytest.raises(CitationError):
        Citation.from_json(row)


def test_the_citation_file_is_written_at_FILE_MODE_and_refuses_a_SYMLINK(tmp_path) -> None:
    """⚠ BUILTIN `open(..., "a")` LEFT THE ONE FILE IN A BAG AT 0644, AND FOLLOWED LINKS.

    Every other file this package writes goes through `os.open` with the mode set
    at creation and `O_NOFOLLOW` — `_write_tag_file` states both rules, and
    `content_store.store_bytes` restates them. `record_citation` did neither, so
    the quotes and claim text were world-readable on a multi-user host, and a
    planted `citations.jsonl` symlink diverted appended rows out of the bag. The
    read side already refused to FOLLOW such a link; only the write side was open.
    """
    from modules.journal.bag import DIR_MODE, FILE_MODE

    root = tmp_path / "journal"
    root.mkdir(mode=DIR_MODE)
    bag = open_bag(root, "modes")
    writer = bag.writer_dir("draft")
    citation = new_citation(claim_id="c1", stage="draft", quote="q",
                            source_ref="https://example.org/a",
                            capture=CAPTURE_HARVEST, page_content_hash=DIGEST_A)
    target = record_citation(writer, citation)
    assert target.stat().st_mode & 0o777 == FILE_MODE

    outside = tmp_path / "outside.jsonl"
    outside.write_text("")
    diverted = bag.writer_dir("critic")
    (diverted / CITATIONS_FILE).symlink_to(outside)
    with pytest.raises(OSError):
        record_citation(diverted, citation)
    assert outside.read_text() == "", "an appended row escaped the bag through a symlink"

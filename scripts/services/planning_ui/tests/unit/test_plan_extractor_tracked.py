"""Unit tests for the tracked-store reader and its §7 contract check.

The discriminator this suite pins: a **per-item** deviation is a finding, and a
**store-wide** deviation HALTS. §7 exists because ``candidates.md`` changed shape
three times in three days and this repo discovered each change as a failed
dispatch — a shorter table that reads as a complete one is the failure being
prevented, so the halt is the behaviour under test, not an edge case.
"""

from __future__ import annotations

import pytest

from planning_ui.plan_extractor.model import Collector
from planning_ui.plan_extractor.tracked import (
    CONTRACT_VERSION,
    CORE_FIELDS,
    STORES,
    ContractMismatch,
    TrackedItem,
    _check_contract,
    _parse_frontmatter,
    _report_item_deviations,
)

WELL_FORMED = """---
id: S-a1b2c3d4
title: A one-line consequence
status: open
count: 1
filed: 2026-08-25
filed_by: review-pr
target: standards/testing/testing_standard.md
anchor: § Tier 3
ratification: pending
---

The body.
"""


def _item(store: str, **fields) -> TrackedItem:
    return TrackedItem(
        store=store,
        path=f"tracked/{store}/{fields.get('id', 'X-00000000')}.md",
        fields=fields,
        field_lines={key: index + 2 for index, key in enumerate(fields)},
    )


def test_frontmatter_parse_records_the_line_each_key_was_read_from():
    """Provenance at node granularity is requirement 1; a YAML load discards it."""
    fields, lines, body, error, _dupes = _parse_frontmatter(WELL_FORMED)
    assert error == ""
    assert fields["id"] == "S-a1b2c3d4"
    assert fields["anchor"] == "§ Tier 3"
    assert lines["id"] == 2
    assert lines["ratification"] == 10
    assert body.strip() == "The body."


def test_a_missing_closing_delimiter_is_an_error_not_a_partial_read():
    """The frontmatter-era successor to the column shift.

    Returning what was parsed so far would produce a confident, complete-looking,
    wrong item — which is the precise defect §3.1's migration note describes.
    """
    _fields, _lines, _body, error, _dupes = _parse_frontmatter("---\nid: S-a1b2c3d4\n")
    assert "closing" in error


def test_a_file_with_no_frontmatter_at_all_is_an_error():
    _fields, _lines, _body, error, _dupes = _parse_frontmatter("# Just a heading\n")
    assert "opening" in error


def test_one_item_missing_a_core_field_is_a_finding_not_a_halt():
    collector = Collector()
    items = [
        _item("issues", id="I-aaaaaaaa", title="t", status="open", count="1",
              filed="2026-08-01", filed_by="review-pr", repo="example-app"),
        _item("issues", id="I-bbbbbbbb", title="t", status="open", count="1",
              filed="2026-08-02", repo="example-app"),
    ]
    _check_contract("issues", items)  # does not raise
    _report_item_deviations("issues", "I", items, collector)
    codes = [f.code for f in collector.findings]
    assert codes == ["TRACKED_CORE_FIELD_MISSING"]
    assert "filed_by" in collector.findings[0].summary
    assert collector.findings[0].provenance.file.endswith("I-bbbbbbbb.md")


def test_a_core_field_absent_from_EVERY_item_halts_the_run():
    """The store's shape has moved. A shorter table is the forbidden output."""
    items = [
        _item("issues", id=f"I-{n}", title="t", status="open", count="1",
              filed="2026-08-01", repo="example-app")
        for n in ("aaaaaaaa", "bbbbbbbb")
    ]
    with pytest.raises(ContractMismatch) as excinfo:
        _check_contract("issues", items)
    assert "filed_by" in str(excinfo.value)
    assert CONTRACT_VERSION in str(excinfo.value)


def test_an_unexpected_field_on_every_item_halts_the_run():
    """The direction the `state:` duplicate arrived from, in 2026-08.

    A field every item carries that the contract does not name means the shared
    core moved underneath this reader — exactly what §7's pre-dispatch check is
    for.
    """
    items = [
        _item("operations", id=f"O-{n}", title="t", status="queued", count="1",
              filed="2026-08-01", filed_by="operator", ownership="PM3",
              blocked_on="x", ready="not-ready", state="queued")
        for n in ("aaaaaaaa", "bbbbbbbb")
    ]
    with pytest.raises(ContractMismatch) as excinfo:
        _check_contract("operations", items)
    assert "'state'" in str(excinfo.value)


def test_an_unexpected_field_on_only_SOME_items_does_not_halt():
    """The discriminator, stated from the other side.

    One item carrying an extra field is a corpus untidiness, not a contract
    change — halting on it would make the reader unusable.
    """
    items = [
        _item("operations", id="O-aaaaaaaa", title="t", status="queued", count="1",
              filed="2026-08-01", filed_by="operator", ownership="PM3",
              blocked_on="x", ready="not-ready", state="queued"),
        _item("operations", id="O-bbbbbbbb", title="t", status="queued", count="1",
              filed="2026-08-01", filed_by="operator", ownership="PM3",
              blocked_on="x", ready="not-ready"),
    ]
    _check_contract("operations", items)


def test_an_empty_store_never_halts():
    """A store with no items carries no evidence that the contract moved."""
    _check_contract("standards", [])


def test_id_prefix_and_filename_are_checked_against_the_store():
    collector = Collector()
    wrong = TrackedItem(
        store="candidates",
        path="tracked/candidates/C-dddddddd.md",
        fields={"id": "I-dddddddd", "title": "t", "status": "open", "count": "1",
                "filed": "2026-08-01", "filed_by": "review-pr",
                "component": "x", "size": "", "decision": ""},
        field_lines={"id": 2},
    )
    _report_item_deviations("candidates", "C", [wrong], collector)
    codes = [f.code for f in collector.findings]
    # The prefix mismatch AND the filename mismatch are separate findings: they
    # have different remedies (re-file vs rename).
    assert codes.count("TRACKED_ID_MALFORMED") == 2
    # `size:` and `decision:` are present-but-empty, which is MEANINGFUL for a
    # candidate — blank `decision` means untriaged — so they are §4 fields
    # present, not core fields missing.
    assert "TRACKED_CORE_FIELD_MISSING" not in codes


def test_the_four_stores_and_their_prefixes_are_pinned():
    """§1 + §2. A fifth store, or a changed prefix, is a contract change."""
    assert set(STORES) == {"issues", "operations", "candidates", "standards"}
    assert [STORES[s][0] for s in ("issues", "operations", "candidates", "standards")] == [
        "I", "O", "C", "S",
    ]
    assert CORE_FIELDS == ("id", "title", "status", "count", "filed", "filed_by")


def test_a_repeated_frontmatter_key_is_reported_rather_than_discarded():
    """§3.1's column shift, one layer down.

    Two ``status:`` lines are two readings of one field that disagree. Keeping
    the first and dropping the second without a word is the confident,
    complete-looking, wrong result the standard's own migration note names — and
    frontmatter removing the SHIFT does not remove the DUPLICATE.
    """
    fields, _lines, _body, error, duplicates = _parse_frontmatter(
        "---\nid: S-a1b2c3d4\nstatus: open\nstatus: resolved\n---\nbody\n"
    )
    assert error == ""
    assert fields["status"] == "open", "the first value wins"
    assert duplicates == [("status", 4)], "and the second is carried out, not dropped"


def test_a_file_with_no_repeated_key_carries_no_duplicate():
    """The negative half: the report must not grow a row for a well-formed item."""
    _fields, _lines, _body, error, duplicates = _parse_frontmatter(WELL_FORMED)
    assert error == ""
    assert duplicates == []

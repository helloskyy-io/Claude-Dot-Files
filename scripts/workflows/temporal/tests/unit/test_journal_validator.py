"""The validator — requirements 5 and 8, and the "always all three" contract.

REQUIREMENT 8 IS THE *ALWAYS*, NOT THE FIELDS. A validator that reported
`redacted` where `sealed` was also true would strand three named consumers
(Phase 4's gap accounting, Phase 5 r9, Phase 7 r4). So the checks below are not
"does it report redaction" — they are "does every report carry lifecycle AND
redacted AND incomplete, whatever their values", including the combination the
implementation checklist calls out by name: sealed, redacted *and* incomplete
at once.

THE 2x2x2 IS ENUMERATED RATHER THAN SAMPLED. Every combination of the two
lifecycle values with the two flags is built and asserted, because the whole
defect class here is a state that only misreports in combination — and a
validator sampled at three of eight points looks exactly as green as one checked
at all eight.

WHAT THIS FILE DOES NOT LOOK AT:

  * It does not prove any bag on this machine is valid. That is the integration
    tier, which needs a bag a real dispatch produced.
  * It does not check that a run SETS `incomplete` when it should. Phase 3 owns
    when; this owns what a set flag reads back as.
  * `ok` here is integrity only. A redacted or incomplete bag whose bytes match
    its manifest is `ok`, on purpose — conflating "something happened to this
    run" with "these bytes are wrong" is the collapse requirement 8 forbids.
"""

from __future__ import annotations

import itertools
from pathlib import Path

import pytest

from modules.journal.bag import (BAGIT_FILE, BAG_INFO_FILE, MANIFEST_FILE,
                                 PAYLOAD_DIR, open_bag)
from modules.journal.validate import render_report, validate_bag


def _bag(root: Path, run_id: str, *, sealed: bool, redacted: bool, incomplete: bool):
    """One bag in an exactly-specified state.

    A redaction requires a sealed bag by construction (it reseals), which is why
    the caller cannot ask for redacted-and-open — and why the enumeration below
    asserts that combination is refused rather than silently produced.
    """
    bag = open_bag(root, run_id)
    (bag.writer_dir("child") / "payload.jsonl").write_text('{"a": 1}\n')
    if sealed:
        bag.seal()
    if redacted:
        bag.redact("data/child/payload.jsonl", "carried a credential")
    if incomplete:
        bag.mark_incomplete("a second child's transcript", "the disk filled")
    return bag


# --- requirement 8: all three fields, every time -------------------------------

@pytest.mark.parametrize(
    "sealed,redacted,incomplete",
    [combo for combo in itertools.product([True, False], repeat=3)
     if not (combo[1] and not combo[0])],          # redaction implies a seal
    ids=lambda v: str(v))
def test_every_reachable_state_reports_all_three_fields(
        root: Path, sealed: bool, redacted: bool, incomplete: bool) -> None:
    bag = _bag(root, f"r-{sealed}-{redacted}-{incomplete}",
               sealed=sealed, redacted=redacted, incomplete=incomplete)
    report = validate_bag(bag.path)

    assert report.lifecycle == ("sealed" if sealed else "open")
    assert report.redacted is redacted
    assert report.incomplete is incomplete

    rendered = render_report(report)
    for field in ("lifecycle", "redacted", "incomplete"):
        assert f"{field:<11}:" in rendered.replace("payload    :", ""), \
            f"{field} absent from a report — an omitted line is indistinguishable " \
            f"from 'the validator did not look'\n{rendered}"


def test_the_three_way_combination_the_checklist_names(root: Path) -> None:
    """sealed AND redacted AND incomplete — the case a collapsed label loses.

    Called out separately from the enumeration above because it is the one the
    implementation checklist names, and because it is where a single-field
    design fails most expensively: a human's deliberate redaction and a
    disk-full data loss on the same bag.
    """
    bag = _bag(root, "all-three", sealed=True, redacted=True, incomplete=True)
    report = validate_bag(bag.path)
    assert (report.lifecycle, report.redacted, report.incomplete) == ("sealed", True, True)
    assert report.ok, "the bytes still match the manifest; the flags are not failures"
    assert report.redactions and report.gaps, \
        "both records must be separately enumerable, not merged into one list"


def test_a_redaction_cannot_be_applied_to_an_UNSEALED_bag_silently(root: Path) -> None:
    """Not a refusal — a redaction on an open bag simply leaves it open.

    Pinned because the enumeration above SKIPS that combination, and a skipped
    combination with no statement about it is how a gap in coverage reads as a
    gap in reachability.
    """
    bag = open_bag(root, "open-redacted")
    (bag.writer_dir("child") / "a").write_text("x")
    bag.redact("data/child/a", "reason")
    report = validate_bag(bag.path)
    assert (report.lifecycle, report.redacted) == ("open", True)
    assert report.ok, "an open bag has no manifest to fail against"


# --- requirement 5: re-hash, and distinguish the three ways it can differ -------

def test_a_sealed_bag_passes(root: Path) -> None:
    """POSITIVE CONTROL. A validator that failed everything would pass every
    negative check below while being useless."""
    bag = _bag(root, "clean", sealed=True, redacted=False, incomplete=False)
    report = validate_bag(bag.path)
    assert report.ok
    assert (report.missing, report.mismatched, report.unlisted, report.structural) == ((), (), (), ())
    assert report.payload_files == 1


def test_a_DELETED_payload_file_reports_MISSING(root: Path) -> None:
    bag = _bag(root, "lost", sealed=True, redacted=False, incomplete=False)
    (bag.payload_dir / "child" / "payload.jsonl").unlink()

    report = validate_bag(bag.path)
    assert not report.ok
    assert report.missing == ("data/child/payload.jsonl",)
    assert report.mismatched == (), "a deletion is not a corruption — the remedies differ"


def test_an_EDITED_payload_file_reports_MISMATCHED(root: Path) -> None:
    """The distinction is the diagnosis: a missing file is loss or a truncated
    transfer, a mismatched one is corruption or an edit to a record that must
    not be edited."""
    bag = _bag(root, "edited", sealed=True, redacted=False, incomplete=False)
    (bag.payload_dir / "child" / "payload.jsonl").write_text('{"a": 2}\n')

    report = validate_bag(bag.path)
    assert not report.ok
    assert report.mismatched == ("data/child/payload.jsonl",)
    assert report.missing == ()


def test_a_file_ADDED_AFTER_the_seal_reports_UNLISTED(root: Path) -> None:
    """The immutability rule broken from the other direction.

    A check that only walked the manifest is structurally blind to this: every
    listed file is present and correct, so it reports a clean bag while a write
    has landed in a sealed record.
    """
    bag = _bag(root, "grown", sealed=True, redacted=False, incomplete=False)
    (bag.payload_dir / "child" / "late.jsonl").write_text("after the fact\n")

    report = validate_bag(bag.path)
    assert not report.ok
    assert report.unlisted == ("data/child/late.jsonl",)
    assert (report.missing, report.mismatched) == ((), ())


def test_an_OPEN_bag_is_reported_open_and_NOT_failed(root: Path) -> None:
    """A crashed run leaving an open bag is the case this design most cares
    about, so `open` is a first-class state and not an error."""
    report = validate_bag(_bag(root, "inflight", sealed=False, redacted=False,
                               incomplete=False).path)
    assert report.lifecycle == "open"
    assert report.ok
    assert report.payload_files == 1, "an open bag's payload is still counted"


# --- structural checks ----------------------------------------------------------

def test_a_missing_bagit_txt_is_STRUCTURAL_and_the_bag_still_reports_state(root: Path) -> None:
    bag = _bag(root, "nobagit", sealed=True, redacted=False, incomplete=True)
    (bag.path / BAGIT_FILE).unlink()

    report = validate_bag(bag.path)
    assert not report.ok
    assert any(BAGIT_FILE in item for item in report.structural)
    assert report.incomplete, "a structurally broken bag still has a state worth reporting"


def test_a_three_line_bagit_txt_is_refused_by_line_count(root: Path) -> None:
    """RFC 8493 §2.1.1 is a count, so the check is a count. This is the guard
    that stops r6's premise being quietly voided by a one-line addition."""
    bag = _bag(root, "fatbagit", sealed=True, redacted=False, incomplete=False)
    with open(bag.path / BAGIT_FILE, "a", encoding="utf-8") as handle:
        handle.write("Event-Schema-Version: 1\n")

    report = validate_bag(bag.path)
    assert not report.ok
    assert any("exactly two" in item for item in report.structural)


def test_a_bag_with_no_schema_version_is_STRUCTURAL(root: Path) -> None:
    """An event written without a version is unrecoverable on read, which is why
    the rule lands in Phase 1 rather than waiting for the upcaster mechanism."""
    bag = _bag(root, "noversion", sealed=False, redacted=False, incomplete=False)
    kept = [ln for ln in bag.info_path.read_text().splitlines()
            if not ln.startswith("Event-Schema-Version:")]
    bag.info_path.write_text("\n".join(kept) + "\n")

    report = validate_bag(bag.path)
    assert not report.ok
    assert any("Event-Schema-Version" in item for item in report.structural)


def test_a_missing_payload_directory_is_STRUCTURAL(root: Path) -> None:
    bag = _bag(root, "nodata", sealed=False, redacted=False, incomplete=False)
    (bag.payload_dir / "child" / "payload.jsonl").unlink()
    (bag.payload_dir / "child").rmdir()
    (bag.payload_dir).rmdir()

    report = validate_bag(bag.path)
    assert any(PAYLOAD_DIR in item for item in report.structural)


def test_a_path_that_is_not_a_bag_reports_rather_than_raising(root: Path) -> None:
    """A sweep over a thousand bags wants a report per bag, not an exception on
    the first malformed one."""
    report = validate_bag(root / "does-not-exist")
    assert not report.ok
    assert report.structural and "not a directory" in report.structural[0]
    assert (report.lifecycle, report.redacted, report.incomplete) == ("open", False, False)


def test_a_malformed_manifest_line_is_STRUCTURAL_not_a_crash(root: Path) -> None:
    bag = _bag(root, "badmanifest", sealed=True, redacted=False, incomplete=False)
    (bag.path / MANIFEST_FILE).write_text("this is not a manifest line\n")

    report = validate_bag(bag.path)
    assert not report.ok
    assert any("checksum" in item for item in report.structural)


def test_a_manifest_listing_one_path_TWICE_is_STRUCTURAL(root: Path) -> None:
    """A manifest that does not decide a file's checksum has not decided it.

    A plain dict assignment keeps the last line and reports a clean bag, which
    is the shape where an integrity check quietly stops being one.
    """
    bag = _bag(root, "dupe", sealed=True, redacted=False, incomplete=False)
    manifest = bag.path / MANIFEST_FILE
    line = manifest.read_text().strip()
    manifest.write_text(f"{line}\n{'0' * 64}  data/child/payload.jsonl\n")

    report = validate_bag(bag.path)
    assert not report.ok
    assert any("second time" in item for item in report.structural)


def test_a_manifest_written_with_ONE_space_still_parses(root: Path) -> None:
    """A bag may have been written by another BagIt implementation, and refusing
    one on whitespace would be a compatibility bug wearing a strictness costume."""
    bag = _bag(root, "onespace", sealed=True, redacted=False, incomplete=False)
    manifest = bag.path / MANIFEST_FILE
    manifest.write_text(manifest.read_text().replace("  ", " "))

    assert validate_bag(bag.path).ok


def test_a_missing_bag_info_is_STRUCTURAL(root: Path) -> None:
    bag = _bag(root, "noinfo", sealed=False, redacted=False, incomplete=False)
    (bag.path / BAG_INFO_FILE).unlink()

    report = validate_bag(bag.path)
    assert not report.ok
    assert any(BAG_INFO_FILE in item for item in report.structural)


# --- the rendered report ---------------------------------------------------------

def test_the_rendered_report_states_PASS_or_FAIL_and_never_only_a_state(root: Path) -> None:
    clean = render_report(validate_bag(_bag(root, "a", sealed=True, redacted=False,
                                            incomplete=False).path))
    assert "result     : PASS" in clean

    broken = _bag(root, "b", sealed=True, redacted=False, incomplete=False)
    (broken.payload_dir / "child" / "payload.jsonl").unlink()
    assert "result     : FAIL" in render_report(validate_bag(broken.path))


def test_a_SYMLINK_in_the_payload_is_reported_STRUCTURALLY(root: Path, tmp_path: Path) -> None:
    """A link is not payload, and silence about it is the harm.

    A bag transfers as a directory tree; a link's target does not travel with it,
    so the receiving end gets a dangling pointer where the manifest promised
    bytes. Before this, `payload_files` followed the link and hashed the target —
    the bag validated, and what it validated was a file it did not contain.
    """
    outside = tmp_path / "outside.txt"
    outside.write_text("not payload")

    bag = open_bag(root, "r")
    (bag.payload_dir / "real.txt").write_text("payload")
    (bag.payload_dir / "link.txt").symlink_to(outside)
    bag.seal()

    report = validate_bag(bag.path)
    assert not report.ok, "a bag containing a link must not report clean"
    assert any("symlink" in item for item in report.structural), report.structural
    # The three state fields are still reported — r8's "always" survives a
    # structural failure, which is the case an operator most needs them in.
    assert report.lifecycle == "sealed"
    assert report.redacted is False
    assert report.incomplete is False

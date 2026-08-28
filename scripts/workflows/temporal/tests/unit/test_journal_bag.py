"""The bag's layout and the four writes that change it — requirements 2, 3, 4, 6.

THE FILE LAYOUT IS THE EXPENSIVE THING TO GET WRONG, which is why this phase
builds it before anything writes into it. Once three phases are emitting into a
tree, changing how that tree is organised means rewriting records that were
supposed to be permanent — and by then the folders are the only thing that can
regenerate everything else.

RFC 8493 CONFORMANCE IS ASSERTED LITERALLY, not paraphrased. `bagit.txt` having
exactly two lines is the requirement that decided where the schema version goes
(bag-info.txt, r6), so a test that checked "bagit.txt mentions a version" would
let the whole reason BagIt was chosen be forfeited without going red.

WHAT THIS FILE DOES NOT LOOK AT:

  * It does not validate. `test_journal_validator.py` owns the read side, and
    keeping them apart is what stops a bag written wrongly and read wrongly from
    agreeing with itself.
  * It does not check WHEN `mark_incomplete` is called. That is Phase 3's rule
    (*a gap may exist; a silent gap may not*); this phase supplies only the
    place the fact is recorded.
  * It says nothing about payload CONTENT. Nothing emits until Phase 3.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from modules.journal import bag as bagmod
from modules.journal.bag import (BAGIT_FILE, BAG_INFO_FILE, DIR_MODE,
                                 FILE_MODE, JOURNAL_SCHEMA_VERSION,
                                 MANIFEST_FILE, PAYLOAD_DIR, BagError,
                                 open_bag, read_tag_file)


def _info(bag) -> dict[str, list[str]]:
    """bag-info as label -> every value, since most labels are repeatable."""
    out: dict[str, list[str]] = {}
    for label, value in read_tag_file(bag.info_path):
        out.setdefault(label, []).append(value)
    return out


# --- r2 / r4: the layout ------------------------------------------------------

def test_a_new_bag_has_the_four_things_RFC_8493_asks_for(root: Path) -> None:
    bag = open_bag(root, "abc123")
    assert bag.path == root / "abc123", "r2: keyed by run_id, and by nothing else"
    assert (bag.path / BAGIT_FILE).is_file()
    assert (bag.path / BAG_INFO_FILE).is_file()
    assert (bag.path / PAYLOAD_DIR).is_dir()
    assert not (bag.path / MANIFEST_FILE).exists(), "an unsealed bag has no manifest"


def test_bagit_txt_is_EXACTLY_two_lines(root: Path) -> None:
    """r6's premise. Anything else there makes the bag non-conforming and
    forfeits the entire reason BagIt was chosen, which is why the schema version
    lives in bag-info.txt instead."""
    lines = (open_bag(root, "r").path / BAGIT_FILE).read_text().splitlines()
    assert lines == [f"BagIt-Version: {bagmod.BAGIT_VERSION}",
                     f"Tag-File-Character-Encoding: {bagmod.TAG_FILE_ENCODING}"]


def test_the_schema_version_is_in_bag_info_and_NOT_in_bagit(root: Path) -> None:
    """r6, both halves. The negative half is the one that matters: a version
    added to bagit.txt would be a two-word edit that silently breaks conformance."""
    bag = open_bag(root, "r")
    assert _info(bag)[bagmod.LABEL_SCHEMA_VERSION] == [str(JOURNAL_SCHEMA_VERSION)]
    assert "Schema" not in (bag.path / BAGIT_FILE).read_text()


def test_caller_metadata_reaches_bag_info(root: Path) -> None:
    """The originating repo is a first-class field, not a Phase 3 afterthought.

    The run log this supersedes is keyed per repo CHECKOUT while the journal is
    one root per EDGE, and a field absent from version-1 records is absent
    forever.
    """
    bag = open_bag(root, "r", info={"Journal-Origin-Remote": "git@example:org/repo.git"})
    assert _info(bag)["Journal-Origin-Remote"] == ["git@example:org/repo.git"]
    assert _info(bag)["External-Identifier"] == ["r"]


def test_modes_are_0700_on_directories_and_0600_on_tag_files(root: Path) -> None:
    """The root holds verbatim transcripts, and two deployment shapes are multi-user."""
    bag = open_bag(root, "r")
    writer = bag.writer_dir("child")
    for directory in (bag.path, bag.payload_dir, writer):
        assert stat.S_IMODE(directory.stat().st_mode) == DIR_MODE, directory
    for tag in (bag.path / BAGIT_FILE, bag.info_path):
        assert stat.S_IMODE(tag.stat().st_mode) == FILE_MODE, tag


@pytest.mark.parametrize("bad", ["", ".", "..", "a/b", "../escape"])
def test_a_run_id_that_is_not_a_folder_name_is_refused(root: Path, bad: str) -> None:
    """`run_id` is the bag's only address; a separator would put it elsewhere."""
    with pytest.raises(BagError):
        open_bag(root, bad)


# --- r3: one subfolder per writer ---------------------------------------------

def test_two_writers_asking_for_the_SAME_NAME_get_different_directories(root: Path) -> None:
    """r3's whole point: no two writers ever share a file.

    Same-name is the case that matters. Different names are trivially disjoint;
    it is two critics both calling themselves `research-critic` that would
    otherwise be handed one directory and interleave into one file.
    """
    bag = open_bag(root, "r")
    first, second, third = (bag.writer_dir("research-critic") for _ in range(3))
    assert len({first, second, third}) == 3
    assert first.parent == second.parent == bag.payload_dir


def test_a_writer_name_is_slugified_rather_than_trusted(root: Path) -> None:
    """A child's label is free text and becomes a path segment."""
    bag = open_bag(root, "r")
    allocated = bag.writer_dir("../weird name/../")
    assert allocated.parent == bag.payload_dir
    assert allocated.name not in ("", ".", "..")


# --- sealing -------------------------------------------------------------------

def test_sealing_manifests_every_payload_file_and_nothing_else(root: Path) -> None:
    bag = open_bag(root, "r")
    writer = bag.writer_dir("child")
    (writer / "a.jsonl").write_text("one")
    (writer / "nested").mkdir()
    (writer / "nested" / "b.md").write_text("two")

    bag.seal()

    listed = sorted(line.split("  ", 1)[1]
                    for line in bag.manifest_path.read_text().splitlines())
    assert listed == ["data/child/a.jsonl", "data/child/nested/b.md"]
    assert BAG_INFO_FILE not in bag.manifest_path.read_text(), \
        "a tag file is not payload — manifesting it would make every append invalidate the bag"


def test_lifecycle_is_open_until_sealed_and_sealed_after(root: Path) -> None:
    """`open` is a first-class state, not an error: a crashed run leaves one."""
    bag = open_bag(root, "r")
    assert bag.lifecycle == "open"
    bag.seal()
    assert bag.lifecycle == "sealed"


def test_the_oxum_and_dates_are_SET_not_APPENDED_across_reseals(root: Path) -> None:
    """FOUND BY RUNNING A REDACTION, NOT BY READING THE RFC.

    The first seal looked perfectly correct. `Payload-Oxum` and `Bagging-Date`
    are RFC 8493 reserved elements describing the bag AS IT STANDS, and both a
    redaction and a gap reseal — so appending left a bag carrying three of each
    with no rule saying which was current.
    """
    bag = open_bag(root, "r")
    (bag.writer_dir("child") / "a").write_text("x")
    bag.seal()
    bag.redact("data/child/a", "held a token")
    bag.mark_incomplete("a later write", "disk full")

    info = _info(bag)
    assert len(info["Payload-Oxum"]) == 1, info["Payload-Oxum"]
    assert len(info["Bagging-Date"]) == 1
    assert len(info[bagmod.LABEL_SEALED_AT]) == 1
    assert info["Bagging-Date"][0] == info[bagmod.LABEL_SEALED_AT][0][:10], \
        "RFC 8493 specifies Bagging-Date as YYYY-MM-DD; the ordering timestamp is separate"


# --- idempotency (Temporal Standard §7.1) --------------------------------------

def test_reopening_an_OPEN_bag_adopts_it_without_rewriting_its_tags(root: Path) -> None:
    """§7.1: an activity is idempotent, because a retry is a NEW ATTEMPT.

    Rewriting bag-info.txt on the second call would drop a tombstone or a gap
    record — exactly the silent loss this component exists to prevent.
    """
    first = open_bag(root, "r")
    first.mark_incomplete("something", "a reason")

    second = open_bag(root, "r")
    assert second.path == first.path
    assert second.incomplete, "the retry erased a gap record"


def test_reopening_a_SEALED_bag_is_REFUSED(root: Path) -> None:
    """A sealed manifest is a statement about a finished run.

    Appending under the same run_id would make it false with nothing recording
    that it had been.
    """
    bag = open_bag(root, "r")
    bag.seal()
    with pytest.raises(BagError) as exc:
        open_bag(root, "r")
    assert "SEALED" in str(exc.value)
    assert "Mint a new run_id" in str(exc.value), "the message must name the remedy"


# --- redaction: the ONE stated exception to immutability ------------------------

def test_a_redaction_replaces_the_file_leaves_a_tombstone_and_reseals(root: Path) -> None:
    """All three, because any one alone leaves the bag dishonest.

    Replace without reseal => the bag reports a checksum mismatch, which is what
    corruption looks like. Reseal without tombstone => the record no longer says
    that anything was removed, which is a silent edit.
    """
    bag = open_bag(root, "r")
    (bag.writer_dir("child") / "transcript.jsonl").write_text("Bearer sk-live-XXXX")
    bag.seal()
    before = bag.manifest_path.read_text()

    bag.redact("data/child/transcript.jsonl", "carried a bearer credential")

    body = (bag.payload_dir / "child" / "transcript.jsonl").read_text()
    assert "sk-live-XXXX" not in body
    assert "[REDACTED]" in body
    assert bag.redacted
    assert bag.manifest_path.read_text() != before, "the manifest must be regenerated"
    assert any("carried a bearer credential" in v
               for v in _info(bag)[bagmod.LABEL_REDACTION])


def test_a_redaction_of_a_TAG_file_is_refused(root: Path) -> None:
    """A tag file is the record OF the redaction and cannot also be its subject."""
    bag = open_bag(root, "r")
    with pytest.raises(BagError) as exc:
        bag.redact(BAG_INFO_FILE, "nice try")
    assert "only payload files" in str(exc.value)


def test_a_redaction_of_a_MISSING_file_is_refused_distinctly(root: Path) -> None:
    """A typo and a bag that already lost the file need different answers."""
    bag = open_bag(root, "r")
    with pytest.raises(BagError) as exc:
        bag.redact("data/child/nope", "reason")
    assert "no such payload file" in str(exc.value)


def test_a_redaction_reason_carrying_a_NEWLINE_is_refused(root: Path) -> None:
    """Free text becomes a tag value, and a folded value reads as a new label.

    A reason containing "\\nJournal-Incomplete: true" would otherwise set a flag
    nobody asked for — turning an operator's redaction into a false report of
    data loss.
    """
    bag = open_bag(root, "r")
    (bag.writer_dir("child") / "a").write_text("x")
    with pytest.raises(BagError) as exc:
        bag.redact("data/child/a", "reason\nJournal-Incomplete: true")
    # THE MESSAGE NO LONGER SAYS "newline", AND THAT IS THE CHANGE RATHER THAN A
    # REGRESSION. Phase 9 r6 redefined the guard against `read_tag_file`'s own
    # parser instead of a list of newline characters: `str.splitlines()` breaks
    # on EIGHT more than `\n` and `\r`, and every one of them passed the check
    # that shipped and forged a second entry. The property asserted here is the
    # round trip; the full derived battery is `test_journal_tag_lines.py`.
    assert "round trip" in str(exc.value)
    assert not bag.incomplete, "the forged flag must not have landed"


# --- incompleteness -------------------------------------------------------------

def test_the_flag_is_set_once_and_every_gap_is_recorded(root: Path) -> None:
    """The flag answers "is this bag missing something"; the records answer "what"."""
    bag = open_bag(root, "r")
    bag.mark_incomplete("the draft transcript", "disk full")
    bag.mark_incomplete("the refine transcript", "disk still full")

    info = _info(bag)
    assert info[bagmod.LABEL_INCOMPLETE] == ["true"], "the flag must not accumulate"
    assert len(info[bagmod.LABEL_GAP]) == 2
    assert bag.incomplete


def test_incomplete_and_open_are_DIFFERENT_things(root: Path) -> None:
    """`open` means nobody has sealed this yet, which is normal.
    `incomplete` means a write was attempted and did not land, which never is."""
    bag = open_bag(root, "r")
    assert bag.lifecycle == "open" and not bag.incomplete
    bag.mark_incomplete("a write", "a reason")
    assert bag.lifecycle == "open" and bag.incomplete


def test_redacted_and_incomplete_are_INDEPENDENT(root: Path) -> None:
    """The headline failure mode: collapsing them makes a bag that lost data to
    a full disk indistinguishable from one a human deliberately redacted. The
    first is a defect to investigate; the second is the system working."""
    bag = open_bag(root, "r")
    (bag.writer_dir("child") / "a").write_text("x")
    bag.seal()
    bag.redact("data/child/a", "held a token")
    assert bag.redacted and not bag.incomplete
    bag.mark_incomplete("a write", "a reason")
    assert bag.redacted and bag.incomplete


# --- tag-file parsing ------------------------------------------------------------

def test_continuation_lines_are_folded_rather_than_rejected(root: Path) -> None:
    """RFC 8493 permits them, so a bag written by another implementation has them.

    Writing one is refused (above); reading one is required.
    """
    bag = open_bag(root, "r")
    with open(bag.info_path, "a", encoding="utf-8") as handle:
        handle.write("External-Description: a long value\n    continued here\n")
    assert _info(bag)["External-Description"] == ["a long value continued here"]


def test_a_line_that_is_neither_a_label_nor_a_continuation_raises(root: Path) -> None:
    """Fail loud. A tag file that silently dropped an unparseable line would
    lose a tombstone and report the bag as clean."""
    bag = open_bag(root, "r")
    with open(bag.info_path, "a", encoding="utf-8") as handle:
        handle.write("this is not a tag line\n")
    with pytest.raises(BagError):
        read_tag_file(bag.info_path)


def test_BagError_is_a_RuntimeError() -> None:
    """Same contract as JournalRootError: eleven entrypoints print these."""
    assert issubclass(BagError, RuntimeError)


def test_open_bag_refuses_a_path_that_exists_and_is_not_a_directory(root: Path) -> None:
    collision = root / "r"
    collision.write_text("not a bag")
    with pytest.raises(BagError) as exc:
        open_bag(root, "r")
    assert "not a directory" in str(exc.value)
    os.remove(collision)


# --- containment: the redaction path is the module's one sanctioned mutation ------
#
# THESE EXIST BECAUSE THEY DID NOT, AND TWO ESCAPES SHIPPED. `writer_dir`'s free
# text was slugified and adversarially tested from the start; `redact`'s
# `payload_relpath` has to preserve internal `/` (it addresses a nested payload
# file), so slugification was not available and a first-segment check stood in
# for containment. Both holes below were demonstrated against a real bag before
# they were fixed, which is why each test names the observed damage rather than
# the rule.


def test_a_redaction_path_that_walks_OUT_of_the_bag_is_refused(root: Path) -> None:
    """`data/../../x` passed the first-segment check and overwrote a file.

    Observed: the marker was written over a file sitting in the journal root
    beside the bag — another run's record, in a real journal.
    """
    bag = open_bag(root, "r")
    (bag.payload_dir / "kept.txt").write_text("payload")
    bag.seal()

    victim = root / "ANOTHER-RUNS-FILE.txt"
    victim.write_text("precious")

    with pytest.raises(BagError) as exc:
        bag.redact("data/../../ANOTHER-RUNS-FILE.txt", "should never land")
    assert "outside this bag" in str(exc.value)
    assert victim.read_text() == "precious", "the file outside the bag was written to"


def test_a_redaction_target_that_is_a_SYMLINK_is_refused(root: Path) -> None:
    """`is_file()` follows links, so the write landed on the link's target.

    Observed: a symlink under `data/` was hashed into the manifest as payload,
    and redacting it truncated the file it pointed at — outside the bag.
    """
    bag = open_bag(root, "r")
    outside = root.parent / "outside.txt"
    outside.write_text("untouched")
    (bag.payload_dir / "link.txt").symlink_to(outside)

    with pytest.raises(BagError) as exc:
        bag.redact("data/link.txt", "should never land")
    assert "symlink" in str(exc.value)
    assert outside.read_text() == "untouched", "the symlink's target was written to"


def test_a_symlink_under_data_is_not_treated_as_payload(root: Path) -> None:
    """A bag holds bytes, not pointers to bytes that do not travel with it."""
    bag = open_bag(root, "r")
    outside = root.parent / "elsewhere.txt"
    outside.write_text("not payload")
    (bag.payload_dir / "real.txt").write_text("payload")
    (bag.payload_dir / "link.txt").symlink_to(outside)

    listed = [p.as_posix() for p in bagmod.payload_files(bag.path)]
    assert listed == ["data/real.txt"], listed
    assert [p.as_posix() for p in bagmod.payload_symlinks(bag.path)] == ["data/link.txt"]

    bag.seal()
    assert "link.txt" not in bag.manifest_path.read_text()


# --- caller metadata at creation is untrusted, exactly as it is on append ----------


def test_a_NEWLINE_in_bag_info_metadata_is_refused_at_CREATION_too(root: Path) -> None:
    """The forging check belonged to the tag format, not to one of two writers.

    Observed: `open_bag(info={"Journal-Worktree": "wt\\nJournal-Incomplete: true"})`
    wrote a second line that the validator read as a lifecycle flag, so a bag
    claimed a gap nobody recorded. `_append_tag_line` had refused this from the
    start; the creation path did not.
    """
    with pytest.raises(BagError) as exc:
        open_bag(root, "r", info={"Journal-Worktree": "wt\nJournal-Incomplete: true"})
    # THE MESSAGE NO LONGER SAYS "newline", AND THAT IS THE CHANGE RATHER THAN A
    # REGRESSION. Phase 9 r6 redefined the guard against `read_tag_file`'s own
    # parser instead of a list of newline characters: `str.splitlines()` breaks
    # on EIGHT more than `\n` and `\r`, and every one of them passed the check
    # that shipped and forged a second entry. The property asserted here is the
    # round trip; the full derived battery is `test_journal_tag_lines.py`.
    assert "round trip" in str(exc.value)


@pytest.mark.parametrize("label", ["Event-Schema-Version", "External-Identifier",
                                   "Journal-Redaction", "Journal-Incomplete",
                                   "Journal-Gap", "Payload-Oxum"])
def test_a_caller_cannot_set_a_label_this_module_OWNS(root: Path, label: str) -> None:
    """Two different harms, one rule.

    Overwriting `Event-Schema-Version` makes every upcaster read the bag wrongly,
    forever. Setting `Journal-Incomplete` at creation declares a lifecycle fact
    that has not happened — and `incomplete` existing to be distinguishable from
    `redacted` is the whole of r8.
    """
    with pytest.raises(BagError) as exc:
        open_bag(root, f"r-{label}", info={label: "anything"})
    assert label in str(exc.value)


def test_ordinary_caller_metadata_is_still_recorded(root: Path) -> None:
    """The guard above must not have closed the door it exists to keep usable."""
    bag = open_bag(root, "r", info={"Journal-Workflow": "build",
                                    "Journal-Origin-Remote": "git@example:x.git"})
    info = _info(bag)
    assert info["Journal-Workflow"] == ["build"]
    assert info["Journal-Origin-Remote"] == ["git@example:x.git"]


def test_open_bag_ADOPTS_rather_than_crashing_when_the_directory_appears_first(root: Path) -> None:
    """The `mkdir` race the module handles correctly everywhere else.

    A directory created between the `exists()` fast path and the `mkdir` is what
    a duplicate activity delivery produces. The loser must adopt; it used to
    raise an unhandled `FileExistsError`, which is the opposite of the
    idempotency `open_bag`'s docstring promises.
    """
    first = open_bag(root, "raced")
    (first.payload_dir / "a.txt").write_text("written by the winner")

    second = open_bag(root, "raced")
    assert second.path == first.path
    assert (second.payload_dir / "a.txt").read_text() == "written by the winner"

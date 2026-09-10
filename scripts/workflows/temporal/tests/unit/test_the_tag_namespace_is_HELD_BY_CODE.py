"""The `Journal-` tag namespace's extension rule — PMP Phase 3 requirement 13.

FOUR QUESTIONS, ONE REQUIREMENT, AND THE FOURTH IS WHAT MAKES THE OTHER THREE
ENFORCEABLE RATHER THAN ADVISORY. This file asserts (a), (b) and (d) as code; (c)
is deliberately an open ruling and there is nothing to assert about a decision
nobody has made — the assertion for it would manufacture the answer the
requirement declines to give.

WHY THIS IS A SEPARATE FILE FROM `test_journal_tag_lines.py`. That one owns the
LINE — folding, forging, round-tripping. This owns the NAMESPACE — who may add a
label and what a reader does with one it does not know. They are different
questions and they failed independently: the line's rule leaked twice through
different writers, and the namespace has never had a rule at all because it was
closed by construction until WD Phase 5 r1 took a tag from outside.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.journal.bag import (BAG_INFO_FILE, DESCRIPTIVE_JOURNAL_LABELS,
                                 JOURNAL_LABEL_PREFIX, LABEL_GAP,
                                 LABEL_INCOMPLETE, LABEL_REDACTION,
                                 LABEL_SCHEMA_VERSION, LABEL_SEALED_AT,
                                 RESERVED_JOURNAL_LABELS, BagError,
                                 known_journal_label, open_bag, read_tag_file,
                                 unrecognised_journal_labels)
from modules.journal.validate import validate_bag


@pytest.fixture()
def bag(tmp_path: Path):
    root = tmp_path / "journal"
    root.mkdir(mode=0o700)
    return open_bag(root, "run-1")


# --- (a) who may add one: the two trust classes -----------------------------

@pytest.mark.parametrize("label", sorted(RESERVED_JOURNAL_LABELS))
def test_a_LIFECYCLE_label_is_REFUSED_from_outside(bag, label: str) -> None:
    """The integrity space. Every one of these is a FACT about what happened.

    Phase 4, Phase 6 and Phase 7 branch on them, and they are written by the
    journal package alone from `seal`, `redact` and `mark_incomplete`. An outside
    contributor asserting one could declare a run complete, or declare a gap that
    never happened — and in an append-only store that is unfalsifiable after the
    fact.
    """
    with pytest.raises(BagError, match="reserved lifecycle label"):
        bag.add_tag(label, "true")


def test_a_DESCRIPTIVE_label_is_ACCEPTED_from_outside(bag) -> None:
    """The other trust class. A flat rule over the prefix would block this.

    WD Phase 5 r1 is the trigger: a sixth `Journal-` tag beside the five that
    exist, and the first field this bag has ever taken from outside. Refusing it
    would make the namespace closed rather than governed.
    """
    bag.add_tag("Journal-Region", "eu-west")
    assert ("Journal-Region", "eu-west") in read_tag_file(bag.info_path)


def test_add_tag_APPENDS_so_a_repeatable_label_stays_repeatable(bag) -> None:
    """`_set_tag_line` is for the RFC-reserved elements that describe the bag as
    it stands and must be replaced on a reseal. A contributed tag is a statement
    made once, and replacing it would silently keep one of three."""
    bag.add_tag("Journal-Note", "first")
    bag.add_tag("Journal-Note", "second")
    values = [v for label, v in read_tag_file(bag.info_path)
              if label == "Journal-Note"]
    assert values == ["first", "second"]


def test_add_tag_still_REFUSES_a_folded_value_and_a_forged_label(bag) -> None:
    """(d)'s point: the writer inherits the line rules rather than restating them.

    A component composing a `bag-info.txt` line itself bypasses BOTH the reserved
    check above and these — which is how the value-forging class comes back
    through a second author.
    """
    with pytest.raises(BagError, match="does not survive a round trip"):
        bag.add_tag("Journal-Note", "x\nJournal-Incomplete: true")
    with pytest.raises(BagError, match="does not survive a round trip"):
        bag.add_tag("x\nJournal-Incomplete: true", "y")


def test_the_reserved_set_is_exactly_the_five_the_package_writes() -> None:
    """A reserved set with a hole in it is not a reserved set.

    `Event-Schema-Version` is in it despite carrying no `Journal-` prefix because
    it is the same KIND of thing — a fact about the record rather than about the
    run — and a reader who has to remember one exception will eventually not.
    """
    assert RESERVED_JOURNAL_LABELS == {
        LABEL_SCHEMA_VERSION, LABEL_REDACTION, LABEL_INCOMPLETE, LABEL_GAP,
        LABEL_SEALED_AT}


def test_the_five_descriptive_labels_a_real_bag_carries_are_all_KNOWN(
        tmp_path: Path) -> None:
    """The census that keeps `DESCRIPTIVE_JOURNAL_LABELS` from going stale.

    ⚠ A NON-ZERO COUNT IS ASSERTED, because this walk could scope itself wrongly
    and report a clean sweep over nothing. That is the vacuity every
    tree-scanning guard in this package is written against.
    """
    root = tmp_path / "journal"
    root.mkdir(mode=0o700)
    written = open_bag(root, "r", info={
        "Journal-Workflow": "build", "Journal-Origin-Repo": "/repo",
        "Journal-Origin-Remote": "git@x:y.git", "Journal-Origin-Commit": "abc",
        "Journal-Worktree": "wt-1"})
    journal_labels = [label for label, _ in read_tag_file(written.info_path)
                      if label.startswith(JOURNAL_LABEL_PREFIX)]
    assert len(journal_labels) >= 5, (
        f"the walk found {len(journal_labels)} `Journal-` labels on a real bag; "
        f"a census over nothing proves nothing")
    assert all(known_journal_label(label) for label in journal_labels), (
        f"a label this fleet writes is not in either declared class: "
        f"{[l for l in journal_labels if not known_journal_label(l)]}")


# --- (b) what a reader does with one it does not recognise ------------------

def test_an_UNRECOGNISED_tag_VALIDATES_rather_than_failing(bag) -> None:
    """RFC 8493 permits arbitrary `bag-info.txt` labels, so a bag carrying a
    newer fleet's tag is a VALID bag. Failing it would make the namespace's
    stated extensibility false the first time anyone used it."""
    bag.add_tag("Journal-From-The-Future", "v2")
    bag.seal()
    assert validate_bag(bag.path).ok


def test_an_UNRECOGNISED_tag_is_REPORTED_rather_than_silently_dropped(bag) -> None:
    """The other half, and the one this phase's own § Dependencies argues for.

    A rule written only as prose has never once prevented the thing it forbids —
    so the reader half is a function with a test rather than a sentence saying
    readers *should* surface unknown labels.
    """
    bag.add_tag("Journal-From-The-Future", "v2")
    report = validate_bag(bag.path)
    assert report.unrecognised_tags == ("Journal-From-The-Future",)


def test_the_report_RENDERS_the_unrecognised_tag(bag) -> None:
    """Reported into a tuple nobody prints is the observable-with-no-reader
    failure this fleet has already committed three times."""
    from modules.journal.validate import render_report
    bag.add_tag("Journal-From-The-Future", "v2")
    assert "Journal-From-The-Future" in render_report(validate_bag(bag.path))


def test_a_KNOWN_tag_is_NOT_reported_as_unrecognised(bag) -> None:
    """The discriminator. Without it the assertion above passes for a function
    that reports every tag, which would bury the one that matters."""
    assert unrecognised_journal_labels(read_tag_file(bag.info_path)) == ()


def test_an_RFC_reserved_element_is_NOT_reported(bag) -> None:
    """`Payload-Oxum` and `Bagging-Date` are the STANDARD's namespace.

    Reporting them would be this fleet reporting that RFC 8493 exists, on every
    sealed bag — noise that teaches a reader to stop reading the line.
    """
    bag.seal()
    assert validate_bag(bag.path).unrecognised_tags == ()


def test_a_REPEATED_unrecognised_tag_is_reported_ONCE(bag) -> None:
    bag.add_tag("Journal-Note", "a")
    bag.add_tag("Journal-Note", "b")
    assert unrecognised_journal_labels(read_tag_file(bag.info_path)) == \
        ("Journal-Note",)


# --- (d) the mechanism is the writer, not just the owner --------------------

def test_the_reserved_refusal_lives_in_bag_py_and_not_in_a_caller() -> None:
    """(d): THE RULE NAMES THE WRITER. A caller-side check is one a second author
    does not inherit, which is exactly how this package's line rule leaked twice.

    Asserted on the module source rather than by behaviour, because the property
    is about WHERE the control lives — a behavioural test passes equally well
    when every caller happens to check.
    """
    source = (Path(__file__).resolve().parents[2] / "modules" / "journal" /
              "bag.py").read_text(encoding="utf-8")
    assert "RESERVED_JOURNAL_LABELS" in source
    assert "def add_tag" in source


def test_the_bag_info_file_name_is_the_one_this_test_reads(bag) -> None:
    """A trivial pin, and it is here because this file's every assertion goes
    through `bag.info_path`: if that stopped being `bag-info.txt` the namespace
    tests would still pass against whatever it became."""
    assert bag.info_path.name == BAG_INFO_FILE


# --- (c) is deliberately open -----------------------------------------------

def test_no_bag_level_version_field_was_invented(bag) -> None:
    """⚠ THE ASSERTION IS THAT THE QUESTION STAYS OPEN.

    Requirement 13(c) asks whether bag metadata carries a version distinct from
    the per-event one, and rules NOTHING — the fleet declares one version field
    today and Phase 1 describes it two ways ("the event schema version" and "the
    bag-level version"). A tag addition changes bag metadata and changes no
    event, so *"bump it"* and *"do not"* are both wrong answers to a question
    with an ambiguous subject.

    Nobody has verified that a bump is needed, so this phase manufactures no
    decision — and this test is what goes red if a later change quietly makes
    one, which is the only way an open ruling can be held open in code.
    """
    version_labels = [label for label, _ in read_tag_file(bag.info_path)
                      if "version" in label.lower()]
    assert version_labels == [LABEL_SCHEMA_VERSION], (
        f"a second version field appeared: {version_labels}. Requirement 13(c) "
        f"is an OPEN ruling; adding one here settles it without the evidence "
        f"the requirement says is missing.")


def test_adding_a_tag_does_NOT_change_the_declared_version(bag) -> None:
    before = dict(read_tag_file(bag.info_path))[LABEL_SCHEMA_VERSION]
    bag.add_tag("Journal-Region", "eu-west")
    assert dict(read_tag_file(bag.info_path))[LABEL_SCHEMA_VERSION] == before


def test_the_descriptive_class_is_not_a_PERMITTED_SET(bag) -> None:
    """A label outside it is contributable and merely UNRECOGNISED to a reader.

    Treating the declared descriptive set as an allow-list would close the
    namespace again — the state requirement 13 exists to move off.
    """
    assert "Journal-Region" not in DESCRIPTIVE_JOURNAL_LABELS
    bag.add_tag("Journal-Region", "eu-west")     # accepted anyway
    assert "Journal-Region" in unrecognised_journal_labels(
        read_tag_file(bag.info_path))


# --- the file the per-writer isolation does not cover ------------------------

def test_a_gap_appended_WHILE_the_parent_SEALS_survives(tmp_path: Path) -> None:
    """⚠ THE RACE PHASE 1 COULD NOT REACH AND PHASE 3 CREATES.

    Phase 1 gives each writer its own payload subfolder so no two writers share a
    file — but **every writer shares `bag-info.txt`**, and `_set_tag_line` is a
    read-modify-write that truncates. Nothing called `seal()` outside tests, so
    the race was unreachable until emitters existed; the day they do, a gap
    record appended while the parent seals is **lost along with the `incomplete`
    flag**, and the bag then validates clean. That is precisely the *"a bag that
    lost data reads as complete"* outcome Phase 1's four-state design exists to
    prevent, arriving through the one file its per-writer isolation does not
    cover.

    ⚠ THE FIXTURE IS ASYMMETRIC UNDER THE DEFECT, WHICH IS WHAT MAKES IT SEE IT.
    A test that sealed and then marked would pass with or without the lock,
    because the two writes would not overlap. This runs them from separate
    PROCESSES with real contention — an advisory `flock` is a cross-process
    control and a threading test would exercise the GIL rather than the lock.
    """
    import subprocess
    import sys
    import textwrap

    root = tmp_path / "journal"
    root.mkdir(mode=0o700)
    open_bag(root, "race")

    component = Path(__file__).resolve().parents[2]
    driver = textwrap.dedent(f"""
        import sys
        sys.path.insert(0, {str(component)!r})
        # `Bag(path, run_id)` DIRECTLY, never `open_bag`: that function refuses
        # to re-open a SEALED bag, which is correct and is not what this drives.
        # The subject here is two live writers of one `bag-info.txt`, which is
        # the state a parent and its emitting children are in.
        from modules.journal.bag import Bag
        which, root = sys.argv[1], {str(root)!r}
        import pathlib
        bag = Bag(path=pathlib.Path(root) / "race", run_id="race")
        for _ in range(40):
            if which == "seal":
                bag.seal()
            else:
                bag.mark_incomplete("the transcript", "disk full")
    """)
    script = tmp_path / "driver.py"
    script.write_text(driver, encoding="utf-8")

    workers = [subprocess.Popen([sys.executable, str(script), which],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
               for which in ("seal", "gap", "gap")]
    for worker in workers:
        out, err = worker.communicate(timeout=120)
        assert worker.returncode == 0, err.decode()

    from modules.journal.bag import Bag
    reopened = Bag(path=root / "race", run_id="race")
    gaps = [v for label, v in read_tag_file(reopened.info_path)
            if label == LABEL_GAP]
    assert len(gaps) == 80, (
        f"{len(gaps)} of 80 gap records survived concurrent seals — a gap "
        f"record lost to a read-modify-write is a bag that lost data and reads "
        f"as complete")
    assert reopened.incomplete, "the `incomplete` flag was truncated away"

"""Phase 9 r3 and r4 — one run resolves to one bag, and a child says which it is.

THIS IS THE BEHAVIOURAL HALF. `test_the_run_id_ARRIVES_from_outside.py` is a
source sweep: it proves the SHAPE is written across eleven entrypoints and says
nothing about what the values do. This drives the boundary itself, with a real
journal root on disk, because the two requirements here fail in ways a grep
cannot see:

  * r3's failure is SILENT. Two bags for one run reads as two runs forever
    after — nothing errors, nothing is lost, and the record is simply wrong. It
    is the only requirement in the phase whose failure leaves no trace, which is
    why it is demonstrated rather than noted.
  * r4's failure is a CHILD SILENTLY BECOMING ITS OWN RUN. A parent and its
    three children filing four bags for one piece of work destroys the join that
    makes the journal answer *what happened*, and every individual bag looks
    perfectly healthy.

⚠ WHAT r3 DELIVERS AND WHAT IT DOES NOT, because the phase splits them and the
split is load-bearing. **Idempotent on SEQUENTIAL retry** is what this file
demonstrates: attempt two arrives after attempt one either finished or died, and
adopting the existing bag is correct. **Mutual exclusion between two SIMULTANEOUS
openers is a different property**, it is Phase 9 r7, and it is deliberately NOT
delivered — creating a bag is three syscalls rather than one, so a caller losing
the `mkdir` race can adopt a bag whose `bag-info.txt` has not been written yet.
Sequential retry is the case an at-least-once orchestrator actually produces and
is the case this phase can close on its own. Nothing here should be read as
evidence for the simultaneous property.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[5]
TEMPORAL = REPO_ROOT / "scripts" / "workflows" / "temporal"
sys.path.insert(0, str(TEMPORAL))
sys.path.insert(0, str(TEMPORAL / "scripts"))

from dispatch_identity import (RunIdentity, add_identity_arguments,  # noqa: E402
                               resolve_identity)
from modules.journal.bag import (BAG_INFO_FILE, BagError,  # noqa: E402
                                 PAYLOAD_DIR, open_bag, read_tag_file)
from modules.journal.journal_activities import open_run_bag  # noqa: E402


@pytest.fixture()
def root(tmp_path: pathlib.Path) -> pathlib.Path:
    journal = tmp_path / "journal"
    journal.mkdir(mode=0o700)
    return journal


def _parse(argv: list[str]) -> argparse.Namespace:
    """Drive the REAL declaration, so the flags under test are the shipped ones."""
    parser = argparse.ArgumentParser()
    add_identity_arguments(parser)
    return parser.parse_args(argv)


# --- r4: the discriminator is an INPUT, and it has four answers ---------------------

def test_a_run_id_with_no_writer_means_THIS_INVOCATION_IS_THE_RUN() -> None:
    identity = resolve_identity(["--run-id", "abc123"], announce=False)
    assert identity == RunIdentity(run_id="abc123", writer=None, minted=False)
    assert identity.is_the_run


def test_a_run_id_WITH_a_writer_means_this_invocation_is_PART_of_a_run() -> None:
    identity = resolve_identity(["--run-id", "abc123", "--writer", "research_refine"],
                                announce=False)
    assert identity.run_id == "abc123"
    assert identity.writer == "research_refine"
    assert not identity.is_the_run


def test_NEITHER_argument_means_this_invocation_is_the_run_and_is_UNNAMED() -> None:
    """The no-orchestrator case: the boundary mints, and the run IS the run."""
    identity = resolve_identity([], announce=False)
    assert identity.minted and identity.is_the_run
    assert identity.run_id


def test_a_WRITER_with_no_run_to_join_is_REFUSED_rather_than_guessed() -> None:
    """r4's whole point, and the case with two plausible wrong answers.

    Opening its own bag silently makes a child into a run; writing nowhere
    silently loses the record. Both look like success. Neither may be reachable
    by omission, so the only correct behaviour is to refuse and say why.
    """
    with pytest.raises(BagError) as exc:
        resolve_identity(["--writer", "research_refine"], announce=False)
    message = str(exc.value)
    assert "--run-id" in message, "the message must name the missing input"
    assert "remedy" in message, "and it must say what to do about it"


def test_an_EMPTY_writer_name_is_refused(capsys: pytest.CaptureFixture) -> None:
    """`--writer ""` slugifies to the literal folder name `writer`.

    That is `writer_dir`'s correct behaviour for a name it is given, and it is
    the wrong ANSWER for a caller who supplied nothing meaningful — the record
    lands in a directory named after the concept rather than the child. Refused
    at the boundary, where the caller's mistake is visible.
    """
    with pytest.raises(BagError):
        resolve_identity(["--run-id", "abc", "--writer", "   "], announce=False)


def test_the_discriminator_is_NOT_read_from_the_environment(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """The one inference this requirement forbids by name.

    An env var reads like a passed value and behaves nothing like one: it is
    inherited by every descendant process. A parent that exported its own run id
    would hand it to a grandchild that should have had its own, and a person who
    exported it once in a shell would hand it to every unrelated run in that
    terminal. Three shapes are set here, including the two most plausible
    spellings, and none of them may change the answer.
    """
    for name in ("RUN_ID", "JOURNAL_RUN_ID", "WRITER"):
        monkeypatch.setenv(name, "from-the-environment")
    identity = resolve_identity([], announce=False)
    assert identity.run_id != "from-the-environment", (
        "the run id was taken from the environment — a child started by a "
        "person, by a parent, and by a person reproducing what a parent did are "
        "indistinguishable that way")
    assert identity.writer is None


def test_the_flags_a_parser_DECLARES_are_the_ones_resolve_READS() -> None:
    """Two readers of one declaration must not drift.

    `resolve_identity` builds a throwaway parser from `add_identity_arguments`
    rather than restating the flags, which is what keeps this true — but the
    claim is worth a test, because the failure is a flag an entrypoint accepts
    and the boundary silently ignores.
    """
    declared = _parse(["--run-id", "x", "--writer", "w"])
    resolved = resolve_identity(["--run-id", "x", "--writer", "w"], announce=False)
    assert (declared.run_id, declared.writer) == (resolved.run_id, resolved.writer)


def test_resolve_IGNORES_every_other_argument_an_entrypoint_declares() -> None:
    """The boundary reads two flags out of a full command line and nothing else.

    Realistic argv from three different entrypoints, including a positional and
    a value that itself looks like a flag value.
    """
    identity = resolve_identity(
        ["a description of the task", "--repo", "/opt/x", "--pr", "42",
         "--run-id", "build-2026-08-24", "--verbose", "--dry-run"],
        announce=False)
    assert identity.run_id == "build-2026-08-24"
    assert identity.writer is None


# --- r6 at the boundary: an unusable name is refused before anything exists --------

@pytest.mark.parametrize("bad", ["a/b", "..", "", "run\nJournal-Incomplete: true",
                                 "run id", "run:id", "a" * 129])
def test_a_supplied_name_is_VALIDATED_at_the_boundary(bad: str) -> None:
    """Cheapest possible refusal: before preflight, before a worktree exists.

    `open_bag` validates too and that is not redundant — it guards every other
    caller of the journal package, and a boundary check is not a substitute for
    one at the thing being guarded.
    """
    with pytest.raises(BagError):
        resolve_identity(["--run-id", bad], announce=False)


def test_a_MINTED_name_satisfies_the_permitted_set_it_will_be_validated_against(
) -> None:
    """The authority and the allowlist must agree, or every unnamed run fails.

    This is the pairing that would break silently if either side moved: minting
    is in the journal's activity layer, the set is in `bag.py`, and nothing else
    puts them in the same room.
    """
    for _ in range(20):
        identity = resolve_identity([], announce=False)
        assert resolve_identity(["--run-id", identity.run_id],
                                announce=False).run_id == identity.run_id


def test_a_MINTED_name_is_ANNOUNCED_so_the_run_can_be_retried_into_its_bag(
        capsys: pytest.CaptureFixture) -> None:
    """A name nobody was told is a bag nobody can retry into.

    This is the operable half of "where a caller gets the name when there is no
    orchestrator": the process that invents the name is the only thing that
    knows it, and r3's whole value depends on a second attempt being able to
    supply the same one.
    """
    identity = resolve_identity([])
    err = capsys.readouterr().err
    assert identity.run_id in err, "the minted name must be printed"
    assert "--run-id" in err, "and the line must name the flag that supplies it back"


def test_a_SUPPLIED_name_is_not_announced(capsys: pytest.CaptureFixture) -> None:
    """The caller already knows it. Echoing it is noise on every child dispatch."""
    resolve_identity(["--run-id", "abc123"])
    assert capsys.readouterr().err == ""


# --- r3: opening a bag twice under one run id yields ONE bag ----------------------

def test_a_SEQUENTIAL_RETRY_under_one_run_id_yields_ONE_BAG(
        root: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """THE REQUIREMENT (r3), demonstrated at the ACTIVITY the entrypoints call.

    DRIVEN THROUGH `open_run_bag`, NOT `open_bag`, and the difference is the
    point. `test_journal_bag.py` already demonstrates that `open_bag` adopts;
    this is the shape a RETRY actually takes — the whole activity re-invoked,
    root resolution and metadata probes included — which is what an at-least-once
    orchestrator produces and what a replayed second pass would produce.

    THE ASSERTION IS ON THE ROOT, not on the returned object. Two bags for one
    run is a fact about the directory tree, and comparing the two return values
    would pass even if a second directory had appeared beside the first.
    """
    monkeypatch.setattr("modules.journal.journal_activities.resolve_journal_root",
                        lambda **_: root)

    first = open_run_bag(run_id="retried-run", writer=None, repo_root=TEMPORAL,
                         workflow_key="build", worktree_name="wt-1")
    first.mark_incomplete("a partial write", "the first attempt died here")
    before = (first.path / BAG_INFO_FILE).read_text()

    second = open_run_bag(run_id="retried-run", writer=None, repo_root=TEMPORAL,
                          workflow_key="build", worktree_name="wt-1")

    assert second.path == first.path
    assert [p.name for p in root.iterdir()] == ["retried-run"], (
        f"one run produced more than one bag: {sorted(p.name for p in root.iterdir())}. "
        f"This is the failure that is SILENT — two bags read as two runs forever.")
    assert (second.path / BAG_INFO_FILE).read_text() == before, (
        "the retry rewrote bag-info.txt. A rewrite drops tombstones and gap "
        "records, which is the exact silent loss the component exists to prevent")
    assert second.incomplete, "the retry erased a gap record from the first attempt"


def test_a_retry_carrying_DIFFERENT_metadata_still_adopts_rather_than_rewriting(
        root: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The realistic retry, which is not a byte-identical replay.

    A second attempt cuts a new worktree, so it arrives with a different
    `Journal-Worktree`. Adoption must keep the FIRST attempt's record: the bag
    describes the run, and letting the last attempt overwrite it would make a
    retried run indistinguishable from one that never retried.
    """
    monkeypatch.setattr("modules.journal.journal_activities.resolve_journal_root",
                        lambda **_: root)

    open_run_bag(run_id="r", writer=None, repo_root=TEMPORAL,
                 workflow_key="build", worktree_name="build-111")
    second = open_run_bag(run_id="r", writer=None, repo_root=TEMPORAL,
                          workflow_key="build", worktree_name="build-222")

    entries = dict(read_tag_file(second.path / BAG_INFO_FILE))
    assert entries["Journal-Worktree"] == "build-111"
    assert entries["External-Identifier"] == "r"


# --- r4 wired end to end: one run, one bag, one subfolder per writer --------------

def test_a_PARENT_AND_ITS_CHILDREN_produce_ONE_bag_with_ONE_SUBFOLDER_EACH(
        root: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """THE SHAPE THE JOURNAL EXISTS TO PRODUCE, driven the way the fleet runs.

    A parent opens the bag first (Phase 1 r11 makes that its first step), then
    three children join it by name. The alternative this rules out is four bags
    for one piece of work — which is the failure Phase 9 § *A standalone child*
    names, and which every individual bag would look healthy under.
    """
    monkeypatch.setattr("modules.journal.journal_activities.resolve_journal_root",
                        lambda **_: root)

    parent = open_run_bag(run_id="one-run", writer=None, repo_root=TEMPORAL,
                          workflow_key="build", worktree_name="build-1")
    for child in ("build_draft", "build_refine", "review_pr"):
        joined = open_run_bag(run_id="one-run", writer=child, repo_root=TEMPORAL,
                              workflow_key=child, worktree_name="build-1")
        assert joined.path == parent.path, f"{child} filed its own bag"

    assert [p.name for p in root.iterdir()] == ["one-run"], (
        f"one run produced {len(list(root.iterdir()))} bags: "
        f"{sorted(p.name for p in root.iterdir())}")
    assert sorted(p.name for p in (parent.path / PAYLOAD_DIR).iterdir()) == [
        "build_draft", "build_refine", "review_pr"], (
        "one subfolder per writer, named for the writer — a shared directory is "
        "the contention `writer_dir` exists to remove")


def test_a_STANDALONE_CHILD_produces_exactly_one_bag_and_NO_ORPHAN(
        root: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The invocation mode the bag was never designed for, and the second wrong answer.

    A child a person starts with no `--run-id` IS the run. Under "only parents
    open bags" it would leave no record at all, and the component's central claim
    — if any store gets it, the journal gets it — would be false for a whole
    invocation mode.
    """
    monkeypatch.setattr("modules.journal.journal_activities.resolve_journal_root",
                        lambda **_: root)

    identity = resolve_identity([], announce=False)
    assert identity.is_the_run, "a child with no run id IS the run"

    bag = open_run_bag(run_id=identity.run_id, writer=identity.writer,
                       repo_root=TEMPORAL, workflow_key="research_refine",
                       worktree_name=None)

    assert [p.name for p in root.iterdir()] == [identity.run_id]
    assert list((bag.path / PAYLOAD_DIR).iterdir()) == [], (
        "an invocation that IS the run takes no writer subfolder — its records "
        "are the run's, not one member's")
    assert dict(read_tag_file(bag.path / BAG_INFO_FILE))["Journal-Workflow"] == \
        "research_refine"


def test_two_MEMBERS_asking_for_one_writer_name_do_not_share_a_directory(
        root: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A retried member, or two identically-named children, must never collide.

    `writer_dir` allocates by `os.mkdir` winning or losing rather than by
    check-then-create, so the second caller takes the next ordinal. The cost is
    a subfolder per attempt, which is VISIBLE in the bag — the alternative is two
    writers sharing a file, which is not.
    """
    monkeypatch.setattr("modules.journal.journal_activities.resolve_journal_root",
                        lambda **_: root)

    open_run_bag(run_id="r", writer=None, repo_root=TEMPORAL,
                 workflow_key="build", worktree_name="wt")
    for _ in range(2):
        bag = open_run_bag(run_id="r", writer="critic", repo_root=TEMPORAL,
                           workflow_key="critic", worktree_name="wt")

    assert sorted(p.name for p in (bag.path / PAYLOAD_DIR).iterdir()) == [
        "critic", "critic-2"]


def test_a_MEMBER_of_a_run_whose_bag_does_not_exist_yet_CREATES_it(
        root: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The shape Workflow Decomposition Phase 3 makes reachable, recorded as such.

    A person can dispatch two children under one `--run-id` with no parent
    having opened the bag. The first to arrive creates it and the second adopts,
    which is correct SEQUENTIALLY — and is exactly the case that races when they
    are simultaneous. That race is Phase 9 r7 and is not closed here; this test
    pins the sequential behaviour so the r7 work has a baseline to change
    against, and asserts nothing about concurrency.
    """
    monkeypatch.setattr("modules.journal.journal_activities.resolve_journal_root",
                        lambda **_: root)

    first = open_run_bag(run_id="parentless", writer="child_a", repo_root=TEMPORAL,
                         workflow_key="child_a", worktree_name="wt")
    second = open_run_bag(run_id="parentless", writer="child_b", repo_root=TEMPORAL,
                          workflow_key="child_b", worktree_name="wt")

    assert first.path == second.path
    assert [p.name for p in root.iterdir()] == ["parentless"]
    assert sorted(p.name for p in (first.path / PAYLOAD_DIR).iterdir()) == [
        "child_a", "child_b"]
    # The bag records the FIRST arrival's workflow, not the last — adoption does
    # not rewrite. Worth pinning: a reader of this bag must not conclude the run
    # was `child_b` simply because it arrived second.
    assert dict(read_tag_file(first.path / BAG_INFO_FILE))["Journal-Workflow"] == \
        "child_a"


# --- the control on r3: prove the two-bag failure is REACHABLE --------------------

def test_two_DIFFERENT_run_ids_DO_produce_two_bags(root: pathlib.Path) -> None:
    """The control on the control: show the fixture can produce the failure.

    Every assertion above is "exactly one directory under the root". A fixture
    that could only ever produce one directory would satisfy all of them while
    demonstrating nothing — so this shows the root does grow when the ids differ,
    which is what makes the one-directory assertions load-bearing.
    """
    open_bag(root, "run-one")
    open_bag(root, "run-two")
    assert sorted(p.name for p in root.iterdir()) == ["run-one", "run-two"]

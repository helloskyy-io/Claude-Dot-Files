"""RECURRENCE — the ranking, and the ruling it refuses to make.

§3.1 says what to do once you know a finding is one already filed. It does not
say how you know, and these tests pin the shape of the answer: **this module
ranks and the filer rules.**

THE ASYMMETRY IS THE DESIGN AND IT IS ASSERTED, not merely commented. A
duplicate costs one triage ruling. A wrong merge buries a real finding under
somebody else's, where nothing will ever surface it again. So every ambiguity
here resolves toward FILE, and the block says so in words.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.assistant.tracked import recurrence as own
from modules.assistant.tracked import tracked_items as ti


def _item(store: Path, cid: str, title: str, body: str = "", **extras: str) -> Path:
    store.mkdir(parents=True, exist_ok=True)
    fields = {"id": cid, "title": title, "status": "open", "count": "1",
              "filed": "2026-08-26", "filed_by": "test", **extras}
    path = store / f"{cid}.md"
    path.write_text("---\n" + "".join(f"{k}: {v}\n" for k, v in fields.items())
                    + "---\n\n" + (body or "body") + "\n")
    return path


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    for s in ti.STORES.values():
        (tmp_path / s.name).mkdir(parents=True)
    return tmp_path


# ---------------------------------------------------------------- the ranking

def test_a_RARE_shared_term_outranks_many_common_ones(root: Path) -> None:
    """THE SCORER'S WHOLE CLAIM, and the reason it is IDF rather than overlap.

    Two items sharing "the workflow does not" share nothing. Two sharing
    "heartbeat" probably share a subject. The decoy here deliberately shares
    MORE words than the real match — if plain overlap were used it would win.
    """
    store = root / "candidates"
    _item(store, "C-aaaaaaaa", "Heartbeat interval is unbounded on the worker")
    for n in range(6):
        _item(store, f"C-bbbbbbb{n}", "The workflow does not check the result "
                                      "before the workflow returns the result")

    hits = own.similar(root, ti.STORES["candidates"],
                       "The workflow does not bound the heartbeat interval")
    assert hits[0].id == "C-aaaaaaaa", (
        f"a rare shared term must outrank a pile of common ones; got "
        f"{[(h.id, round(h.score, 2)) for h in hits]}")


def test_an_EXACT_key_match_outranks_every_text_match(root: Path) -> None:
    """`standards` is the one store with a field that IDENTIFIES rather than
    narrows (§4.1: a named target and an actionable anchor). Two proposals
    against one anchor are two proposals to change one place."""
    store = root / "standards"
    _item(store, "S-aaaaaaaa", "Something else entirely about nothing",
          target="docs/standards/workflows/workflow-scripts.md", anchor="§ Composition")
    _item(store, "S-bbbbbbbb", "Heartbeat interval bound composition workflow",
          target="docs/standards/other.md", anchor="§ Elsewhere")

    hits = own.similar(root, ti.STORES["standards"],
                       "Heartbeat interval bound composition workflow",
                       key={"target": "docs/standards/workflows/workflow-scripts.md",
                            "anchor": "§ Composition"})
    assert hits[0].id == "S-aaaaaaaa" and hits[0].basis == "key", (
        "the exact-anchor item must lead even though the other one's WORDING "
        "is a perfect match — that is the difference between a key and a rank")


def test_a_PARTIAL_key_is_not_a_key(root: Path) -> None:
    """Same standard, different section, is a different amendment.

    `_IDENTIFYING` requires ALL its fields together. Matching on `target` alone
    would collapse every amendment to one file into one item — and a standard
    is exactly the kind of document that accumulates many.
    """
    store = root / "standards"
    _item(store, "S-aaaaaaaa", "One thing",
          target="docs/standards/workflows/workflow-scripts.md", anchor="§ Composition")
    hits = own.similar(root, ti.STORES["standards"], "One thing",
                       key={"target": "docs/standards/workflows/workflow-scripts.md",
                            "anchor": "§ Routing contracts"})
    assert all(h.basis == "text" for h in hits), (
        "a shared target with a different anchor is not the same item")


def test_no_store_but_standards_has_an_identifying_key(root: Path) -> None:
    """MEASURED, NOT ASSUMED, and the measurement is why this is asserted.

    On 2026-08-26: `component` was present on 43 of 121 candidates, and `repo`
    on 3 of 3 issues with all three the same repo. Neither identifies anything.
    Giving them a key would manufacture confidence the data does not support —
    and the failure mode of a wrong key is a wrong MERGE, which is the one
    outcome this module is built to avoid.
    """
    assert set(own._IDENTIFYING) == {"standards"}
    assert own._IDENTIFYING["standards"] == ("target", "anchor")


def test_an_EMPTY_store_returns_nothing_rather_than_raising(root: Path) -> None:
    """The first item filed into a store has nothing to recur against."""
    assert own.similar(root, ti.STORES["candidates"], "anything at all") == []


def test_a_MISSING_store_directory_returns_nothing(tmp_path: Path) -> None:
    """A convenience must not become a second precondition on the tree."""
    assert own.similar(tmp_path, ti.STORES["candidates"], "anything") == []


def test_an_UNPARSEABLE_item_is_SKIPPED_here_and_not_raised_on(root: Path) -> None:
    """`candidate_rows` ALREADY refuses the whole store, loudly and by name.

    Raising here too would be a second gate with the same message, and it would
    make a reading aid able to block filing. Skipping costs that one item its
    chance to be recommended, and nothing else.
    """
    store = root / "candidates"
    _item(store, "C-aaaaaaaa", "Heartbeat interval unbounded")
    (store / "C-bbbbbbbb.md").write_text("no frontmatter here\n")

    hits = own.similar(root, ti.STORES["candidates"], "heartbeat interval")
    assert [h.id for h in hits] == ["C-aaaaaaaa"]


def test_nothing_shared_means_nothing_returned(root: Path) -> None:
    """A score of zero is not a weak match, it is the absence of one.

    Returning the whole store ranked would make the block advice-shaped noise:
    a filer told to read five unrelated items learns to skip the step.
    """
    store = root / "candidates"
    _item(store, "C-aaaaaaaa", "Heartbeat interval unbounded on the worker")
    assert own.similar(root, ti.STORES["candidates"],
                       "Sprint hours are restated rather than derived") == []


# ------------------------------------------------------------------ the block

def test_the_block_NEVER_declares_a_duplicate(root: Path) -> None:
    """THE RULING THIS MODULE REFUSES TO MAKE.

    A model handed a confident-looking verdict rarely overturns it, so a block
    that said "this is a duplicate" would BE the decision. It names a reading
    list and what the answer changes, and stops.
    """
    store = root / "candidates"
    _item(store, "C-aaaaaaaa", "Heartbeat interval unbounded on the worker")
    block = own.recurrence_block(root, ti.STORES["candidates"],
                                 "heartbeat interval unbounded")
    lowered = block.lower()
    assert "reading list, not a verdict" in lowered
    assert "decide from the body" in lowered
    for verdict in ("this is a duplicate", "already filed as", "merge it into"):
        assert verdict not in lowered, f"the block issued a verdict: {verdict!r}"


def test_the_block_RESOLVES_AMBIGUITY_TOWARD_FILING(root: Path) -> None:
    """The asymmetry, in the words the filer actually reads.

    A duplicate costs one triage ruling. A wrong merge buries a finding where
    nothing will surface it again. The instruction has to say which way to fall.
    """
    store = root / "candidates"
    _item(store, "C-aaaaaaaa", "Heartbeat interval unbounded on the worker")
    block = own.recurrence_block(root, ti.STORES["candidates"],
                                 "heartbeat interval unbounded")
    assert "cannot tell, FILE" in block
    assert "buries a finding" in block


def test_an_EMPTY_store_produces_a_block_that_says_so(root: Path) -> None:
    """Silence would read as "the check did not run", which is the one thing a
    filer must not conclude."""
    block = own.recurrence_block(root, ti.STORES["candidates"], "anything")
    assert "holds nothing resembling this" in block
    assert "File it as a new item" in block


def test_the_block_FLAGS_the_exact_anchor_match_in_line(root: Path) -> None:
    """A `key` hit and a `text` hit are different strengths of evidence, so the
    rendered line has to distinguish them — a reader given one list treats
    every row as equally likely."""
    store = root / "standards"
    _item(store, "S-aaaaaaaa", "One thing",
          target="docs/standards/a.md", anchor="§ One")
    block = own.recurrence_block(
        root, ti.STORES["standards"], "One thing",
        key={"target": "docs/standards/a.md", "anchor": "§ One"})
    assert "same `target` and `anchor`" in block
    assert "this is a RECURRENCE" in block


def test_the_block_is_bounded_so_it_cannot_swamp_a_prompt(root: Path) -> None:
    """A prompt is re-sent every turn (see `test_prompt_budgets`), so a block
    that grew with the store would make filing more expensive the longer the
    store lived — precisely backwards."""
    store = root / "candidates"
    for n in range(40):
        _item(store, f"C-cccccc{n:02d}", "Heartbeat interval unbounded worker")
    hits = own.similar(root, ti.STORES["candidates"], "heartbeat interval worker")
    assert len(hits) == 5, "the default limit must bound the result"
    assert len(own.recurrence_block(
        root, ti.STORES["candidates"], "heartbeat interval worker")) < 1500

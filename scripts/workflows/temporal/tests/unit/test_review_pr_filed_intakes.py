"""The reviewer's filed intakes reach the harvest BY REFERENCE — issue #185, carrier 1.

THE CHAIN THIS HOLDS, ONE LINK PER SECTION: `disposition.md` tells the child to
print `FILED-INTAKE: <url>` per `gh issue create` AND to list the same URLs under
its block's `filed_intakes:`; `review_pr_helper.filed_intakes` reads the lines,
`filed_intakes_in_block` reads THIS pass's block and nothing else, and
`merge_intakes` unions them; `run_review` carries the union on
`ReviewResult.issue_urls`; and every URL the helper accepts is one the harvest's
`parse_ref` addresses — which matters because the harvest runs in the parent's
`finally` and RAISES on a reference it cannot address. The last link,
`run_review_pr.py` splicing the field into `refs=`, is held by
`test_every_parent_HARVESTS_its_github_surfaces.py`; the end-to-end read against
a real issue is `tests/integration/test_a_real_harvest.py`.

WHY TWO SURFACES: measured on 27 archived review logs (2026-09-13), the child's
top-level text in the current regime is one 27-character block — the printed
line does not reach the parent — while every intake it filed reached its posted
block. The block is the copy that lands; the line is kept as a second source.

⚠ WHAT THIS DOES NOT COVER: that a live child actually writes either. That is
a prompt's instruction to a model, and the only evidence is a run's log.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from modules.assistant.review_pr import review_pr_helper as helper
from modules.assistant.review_pr.review_pr_helper import ReviewInput
from modules.journal import harvest
from review_run_fakes import _FakeWorkflow, _record

PROMPT = (Path(__file__).resolve().parents[2] / "modules" / "assistant" / "review_pr"
          / "prompts" / "disposition.md")

ONE = "https://github.com/helloskyy-io/Claude-Dot-Files/issues/163"
TWO = "https://github.com/helloskyy-io/skyynet-master-planning/issues/9"


# --- the parser --------------------------------------------------------------

def test_no_line_means_no_intakes_and_no_error() -> None:
    assert helper.filed_intakes("VERDICT: MERGE\n") == helper.FiledIntakes((), ())
    assert helper.filed_intakes("") == helper.FiledIntakes((), ())


def test_one_line_yields_one_url() -> None:
    got = helper.filed_intakes(f"posted.\nFILED-INTAKE: {ONE}\nVERDICT: HOLD - redispatch\n")
    assert got.urls == (ONE,) and got.malformed == ()


def test_many_lines_yield_many_urls_in_the_order_printed() -> None:
    got = helper.filed_intakes(f"FILED-INTAKE: {TWO}\nprose\nFILED-INTAKE: {ONE}\n")
    assert got.urls == (TWO, ONE)


def test_the_same_url_printed_twice_is_ONE_intake() -> None:
    """A child that echoes its own line filed one issue; two refs would be
    deduped by the harvest anyway, but the banner count must not say two."""
    got = helper.filed_intakes(f"FILED-INTAKE: {ONE}\nFILED-INTAKE: {ONE}\n")
    assert got.urls == (ONE,)


@pytest.mark.parametrize("payload", [
    "https://github.com/o/r/pull/12",            # a PR is not an intake
    "163",                                       # a bare number has no repo
    "#163",
    "https://github.com/o/r/issues/",            # no number
    "https://github.com/o/r/issues/12abc",
    "https://github.com/o/r/extra/issues/12",    # three path segments
    "http://github.com/o/r/issues/12",           # wrong scheme
    "https://gitlab.com/o/r/issues/12",          # wrong host
    "https://github.com/o/r/issues/12)",         # a markdown link's tail
    "not-a-url",
])
def test_a_malformed_payload_is_REPORTED_not_harvested_and_does_not_raise(payload: str) -> None:
    got = helper.filed_intakes(f"FILED-INTAKE: {payload}\nVERDICT: MERGE\n")
    assert got.urls == ()
    assert got.malformed == (payload,)


def test_a_malformed_line_does_not_hide_a_well_formed_one() -> None:
    got = helper.filed_intakes(f"FILED-INTAKE: nope\nFILED-INTAKE: {ONE}\n")
    assert got == helper.FiledIntakes(urls=(ONE,), malformed=("nope",))


@pytest.mark.parametrize("text", [
    f"the prior pass printed FILED-INTAKE: {ONE} and I did not",   # mid-line
    f"> FILED-INTAKE: {ONE}",                                       # quoted
    f"FILED-INTAKE {ONE}",                                          # no colon
    f"FILED-INTAKE: {ONE} trailing words",                          # not alone
    f"filed-intake: {ONE}",                                         # case
])
def test_only_a_line_of_its_own_counts(text: str) -> None:
    """Anchored for `_VERDICT`'s reason: a child quoting a prior pass's comment
    must not re-file that pass's intake into this run's bag."""
    assert helper.filed_intakes(text) == helper.FiledIntakes((), ())


def test_surrounding_blanks_on_the_line_are_tolerated() -> None:
    got = helper.filed_intakes(f"FILED-INTAKE:   {ONE}  \n")
    assert got.urls == (ONE,)


# --- the agreement with the harvest -----------------------------------------

@pytest.mark.parametrize("url", [
    ONE, TWO,
    "https://github.com/a-b/c.d/issues/1",
])
def test_every_url_the_parser_ACCEPTS_the_harvest_can_ADDRESS(url: str) -> None:
    """The helper's grammar is at least as strict as `parse_ref`'s issue arm.

    The direction matters. `parse_ref` raises `HarvestError` on what it cannot
    address, and the harvest is called in the parent's `finally` — so a URL the
    helper passed through and the harvest refused would fail a review whose
    verdict is already posted. The reverse (harvest accepts, helper refuses)
    costs one un-harvested body and a banner note, which is the safe side.
    """
    got = helper.filed_intakes(f"FILED-INTAKE: {url}\n")
    assert got.urls == (url,)
    ref = harvest.parse_ref(url, default_repo=None)
    assert ref.kind == "issue" and ref.url == url


def test_what_the_parser_REFUSES_includes_what_the_harvest_would_refuse() -> None:
    """The control for the test above: a payload the harvest raises on is
    filtered here, so the raise cannot reach the `finally`."""
    payload = "not-a-url"
    with pytest.raises(harvest.HarvestError):
        harvest.parse_ref(payload, default_repo=None)
    assert helper.filed_intakes(f"FILED-INTAKE: {payload}\n").urls == ()


# --- the prompt says the shape the parser reads -----------------------------

def test_the_prompt_instructs_the_EXACT_line_the_parser_reads() -> None:
    """One shape, two surfaces. The prompt's literal, with its placeholder
    replaced by a URL, must be a line the parser accepts — a prompt that
    said `FILED INTAKE:` or `Filed-Intake:` would instruct a line nothing
    reads, and no run would ever notice."""
    text = PROMPT.read_text(encoding="utf-8")
    assert "`FILED-INTAKE: <url>`" in text, "the instruction is gone from disposition.md"
    assert helper.filed_intakes(f"FILED-INTAKE: {ONE}\n").urls == (ONE,)
    # The verdict stays the LAST line — the completion gate reads the final
    # text — so the prompt must place the intake lines before it.
    assert "after any `FILED-INTAKE:` lines" in text


# --- the block surface -------------------------------------------------------

def _block(*items: str, key: str = "filed_intakes:", tail: str = "") -> str:
    """A `pr_review:` block in the schema's shape, with `filed_intakes:` LAST as
    the prompt shows it, followed by whatever `tail` a test wants after it."""
    lines = "".join(f"    - {i}\n" for i in items)
    return (f"pr_review:\n  pr: 67\n  findings:\n    - id: a-stable-slug\n"
            f"      disposition: fixed\n  redispatched: false\n  {key}\n{lines}{tail}")


def test_a_block_with_no_key_means_no_intakes_and_no_error() -> None:
    assert helper.filed_intakes_in_block(_FakeWorkflow.DEFAULT_BLOCK) == helper.FiledIntakes((), ())
    assert helper.filed_intakes_in_block("") == helper.FiledIntakes((), ())


def test_an_inline_EMPTY_list_is_none() -> None:
    assert helper.filed_intakes_in_block(_block(key="filed_intakes: []")).urls == ()
    assert helper.filed_intakes_in_block(_block(key="filed_intakes: [] # none")) == \
        helper.FiledIntakes((), ())


def test_one_item_yields_one_url_and_the_schemas_trailing_comment_is_tolerated() -> None:
    got = helper.filed_intakes_in_block(
        _block(f"{ONE}   # the URL verbatim", key="filed_intakes:   # every intake"))
    assert got == helper.FiledIntakes((ONE,), ())


def test_many_items_yield_many_urls_in_order_and_a_quoted_one_is_unquoted() -> None:
    got = helper.filed_intakes_in_block(_block(TWO, f'"{ONE}"', TWO))
    assert got.urls == (TWO, ONE)


def test_the_section_ENDS_at_the_next_top_level_key() -> None:
    """The prompt places the key last, but a child that put it earlier must not
    have the keys after it read as items."""
    got = helper.filed_intakes_in_block(_block(ONE, tail="  homeless_items: 0\n"))
    assert got == helper.FiledIntakes((ONE,), ())


@pytest.mark.parametrize("item", ["nope", "https://github.com/o/r/pull/12", "#163"])
def test_a_malformed_item_is_REPORTED_not_harvested_and_does_not_raise(item: str) -> None:
    got = helper.filed_intakes_in_block(_block(item, ONE))
    assert got == helper.FiledIntakes((ONE,), (item,))


def test_an_inline_FLOW_list_is_a_shape_the_schema_does_not_show_and_is_REPORTED() -> None:
    got = helper.filed_intakes_in_block(_block(key=f"filed_intakes: [{ONE}]"))
    assert got.urls == () and got.malformed == (f"[{ONE}]",)


def test_the_key_is_read_at_the_TOP_LEVEL_indent_only() -> None:
    """`findings_section`'s hazard, on this key: `dispatch_context: |` is free
    text inside the same block, and a runway quoting this schema there would
    otherwise hand the harvest a list this run did not file."""
    block = (f"pr_review:\n  pr: 67\n  next_steps:\n    - item: x\n"
             f"      dispatch_context: |\n        filed_intakes:\n          - {ONE}\n")
    assert helper.filed_intakes_in_block(block) == helper.FiledIntakes((), ())


def test_merge_is_first_seen_across_surfaces_and_deduped() -> None:
    printed = helper.filed_intakes(f"FILED-INTAKE: {ONE}\nFILED-INTAKE: bad\n")
    in_block = helper.filed_intakes_in_block(_block(TWO, ONE, "worse"))
    assert helper.merge_intakes(printed, in_block) == \
        helper.FiledIntakes((ONE, TWO), ("bad", "worse"))


def test_the_notes_name_the_count_from_EACH_surface() -> None:
    """The per-surface count is the evidence the two-surface design rests on:
    a run whose printed count is 0 and block count is N says the line does not
    reach the parent, without anyone opening a log."""
    printed = helper.filed_intakes("VERDICT: MERGE\n")
    in_block = helper.filed_intakes_in_block(_block(ONE, TWO))
    notes = helper.intake_notes(printed, in_block)
    assert notes == [f"Filed 2 intake(s), handed to the harvest (0 on the printed "
                     f"FILED-INTAKE line, 2 in the posted block's filed_intakes): {ONE}, {TWO}"]


def test_the_prompt_shows_the_EXACT_block_shape_the_parser_reads() -> None:
    """The schema's own two lines, with the placeholder replaced, must parse —
    the same one-shape-two-surfaces check the printed line has above."""
    text = PROMPT.read_text(encoding="utf-8")
    schema = re.search(r"^  filed_intakes:[^\n]*\n    - <url>[^\n]*$", text, re.MULTILINE)
    assert schema, "the `filed_intakes:` key or its `- <url>` item is gone from the block schema"
    block = f"pr_review:\n  pr: 67\n{schema.group(0).replace('<url>', ONE)}\n"
    assert helper.filed_intakes_in_block(block).urls == (ONE,)
    assert "list the same\nURLs under your block's `filed_intakes:`" in text, (
        "FILING AUTHORITY no longer tells the child the block carries the same set")


# --- the result carries them ------------------------------------------------

def test_a_result_built_without_intakes_carries_an_EMPTY_list_not_None() -> None:
    """`*(result.issue_urls …)` in the entrypoint splices a sequence; None
    there is a TypeError in the `finally`."""
    result = helper.ReviewResult(pr_number="1", verdict=helper.Verdict.MERGE, this_pass=1)
    assert result.issue_urls == []


def test_run_review_carries_the_intakes_the_child_printed(monkeypatch, tmp_path) -> None:
    """The real `run_review`, with the child faked at its boundaries, reads the
    lines off the same assistant text the prose shadow reads."""
    fake = _FakeWorkflow(_record(run_id="@ISSUED@"),
                         f"FILED-INTAKE: {ONE}\nFILED-INTAKE: {TWO}\nVERDICT: MERGE\n")
    wf = fake.install(monkeypatch, tmp_path)
    result = wf.run_review(ReviewInput(pr_number="67"), tmp_path, worktree_name="review-pr-1")
    assert result.issue_urls == [ONE, TWO]
    assert any("Filed 2 intake(s)" in n and ONE in n and TWO in n for n in result.notes), result.notes


def test_run_review_with_no_intakes_carries_none_and_says_nothing(monkeypatch, tmp_path) -> None:
    fake = _FakeWorkflow(_record(run_id="@ISSUED@"), "VERDICT: MERGE\n")
    wf = fake.install(monkeypatch, tmp_path)
    result = wf.run_review(ReviewInput(pr_number="67"), tmp_path, worktree_name="review-pr-1")
    assert result.issue_urls == []
    assert not any("intake" in n.lower() for n in result.notes), result.notes


def test_a_run_that_RAISES_after_the_child_filed_still_fails_LOUD(monkeypatch, tmp_path) -> None:
    """THE FAILURE PATH, WITH INTAKES PRESENT — the one the entrypoint cannot harvest.

    The parse sits between the child's exit and the channel comparison, so a
    review whose typed channel is missing raises AFTER the lines were read. Two
    things are pinned here. The parse must not mask that raise — a `FILED-INTAKE:`
    line on the surface changes nothing about which error reaches the operator.
    And the intakes are LOCALS that die with the exception: `run_review` hands
    back no result, so `run_review_pr.py`'s `finally` sees `result is None` and
    harvests the PR alone. That is the limit the code names in three places
    (`review_pr_workflow.run_review`, `run_review_pr.main`, `harvest.py`), the
    same one a PR URL has in every producing parent — and this test is where a
    change that closes it would go red first, because it asserts the raise
    carries no intake. Closing it needs a durable carrier written BEFORE the
    comparison; `append_parent_route`'s event is frozen byte for byte, so that
    carrier is a new event beside it, not a field on it.
    """
    fake = _FakeWorkflow(None, f"FILED-INTAKE: {ONE}\nVERDICT: MERGE\n")
    wf = fake.install(monkeypatch, tmp_path)
    with pytest.raises(RuntimeError, match="record_absent") as caught:
        wf.run_review(ReviewInput(pr_number="67"), tmp_path, worktree_name="review-pr-1")
    assert ONE not in str(caught.value), (
        "the raise now carries the filed intake — the limit this test pins has "
        "moved, so update `run_review_pr.py`'s `finally` comment and this docstring")


def test_run_review_reads_the_intakes_from_the_BLOCK_when_the_child_printed_NO_line(
        monkeypatch, tmp_path) -> None:
    """The live shape: the child's text carries nothing, its posted block
    carries the list. `issue_urls` is populated from the block alone."""
    fake = _FakeWorkflow(_record(run_id="@ISSUED@"), "VERDICT: MERGE\n",
                         block=_block(ONE, TWO), block_carries_nonce=True)
    wf = fake.install(monkeypatch, tmp_path)
    result = wf.run_review(ReviewInput(pr_number="67"), tmp_path, worktree_name="review-pr-1")
    assert result.issue_urls == [ONE, TWO]
    assert any("(0 on the printed FILED-INTAKE line, 2 in the posted block" in n
               for n in result.notes), result.notes


def test_run_review_UNIONS_the_two_surfaces(monkeypatch, tmp_path) -> None:
    fake = _FakeWorkflow(_record(run_id="@ISSUED@"), f"FILED-INTAKE: {ONE}\nVERDICT: MERGE\n",
                         block=_block(ONE, TWO), block_carries_nonce=True)
    wf = fake.install(monkeypatch, tmp_path)
    result = wf.run_review(ReviewInput(pr_number="67"), tmp_path, worktree_name="review-pr-1")
    assert result.issue_urls == [ONE, TWO]


def test_ANOTHER_block_s_filed_intakes_are_NOT_this_run_s(monkeypatch, tmp_path) -> None:
    """Nonce selection, applied to this key: pass 1's block (before ours) lists
    TWO, a third party's block posted AFTER ours lists ONE, and this pass — the
    one carrying the nonce — filed nothing and says `[]`. A reader that took the
    first, the last, or every block would harvest somebody else's intake into
    this run's bag."""
    fake = _FakeWorkflow(_record(run_id="@ISSUED@"), "VERDICT: MERGE\n",
                         block=_block(key="filed_intakes: []"), block_carries_nonce=True,
                         prior_blocks=1, after_blocks=(_block(ONE),))
    wf = fake.install(monkeypatch, tmp_path)
    # Pass 1's block sits BEFORE this pass's in the window; the fake's thread
    # reads resolve `_window` at call time, so wrapping it here is enough.
    own = fake._window
    fake._window = lambda: [_block(TWO)] + own()
    result = wf.run_review(ReviewInput(pr_number="67"), tmp_path, worktree_name="review-pr-2")
    assert result.issue_urls == []
    assert not any("intake" in n.lower() for n in result.notes), result.notes


def test_run_review_NAMES_a_malformed_line_and_still_returns(monkeypatch, tmp_path) -> None:
    """The verdict is posted and the issue exists; a typo in the report costs
    one bag record, which the banner names so it can be found."""
    fake = _FakeWorkflow(_record(run_id="@ISSUED@"),
                         f"FILED-INTAKE: {ONE}\nFILED-INTAKE: oops\nVERDICT: MERGE\n")
    wf = fake.install(monkeypatch, tmp_path)
    result = wf.run_review(ReviewInput(pr_number="67"), tmp_path, worktree_name="review-pr-1")
    assert result.issue_urls == [ONE]
    assert any("NOT harvested" in n and "'oops'" in n for n in result.notes), result.notes

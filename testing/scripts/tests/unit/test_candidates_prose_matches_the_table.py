"""§ Where things stand declares numbers about the table above it. Derive them.

`candidates.md` is a table with a summary section under it, and that section is
the ONLY thing that says how large the untriaged queue is. `triage-candidates`
builds its working set from the table, but a human deciding whether a triage pass
is even owed reads the sentence — so a sentence that disagrees with the table
sends the next pass at the wrong queue, and nothing anywhere says it disagreed.

**THIS PARAGRAPH HAS BEEN WRITTEN BY HAND THREE TIMES AND WAS WRONG TWICE.** The
file records both occasions itself, in the blockquote at § Where things stand: it
once read *"Nothing is untriaged… All 45 rows… 25 `ship`, 8 `requires review`"*
while nine rows were blank and the split was 27/6, and the paragraph below it
claimed seven `requires review` rows were filed as `D-001`–`D-006` when five are.
The cost was not cosmetic — five proposals re-homed out of the GitHub issue queue
were sitting invisibly in a queue the summary declared empty.

**THE THIRD OCCASION WAS A MERGE, WHICH IS WHY THIS CHECK EXISTS AND NOT A THIRD
CORRECTION.** PR #85 and `origin/main` both rewrote this sentence, git raised the
conflict on exactly that paragraph, and a human resolved it by hand. Its sibling
`test_candidate_ids_are_unique.py` names the same seam from the other side —
*"the natural resolution of that conflict keeps both rows"* — and that is the
optimistic half. The pessimistic half is that **a conflict resolution is a
deletion channel with no red lines**: a row dropped while reconciling prose
appears in no diff anyone reads, and the declared total is the only artifact that
would have contradicted it. Restating the number is what makes it a channel;
deriving it is what closes it.

WHAT THIS KEYS ON IS THE CLASS, NOT THE INSTANCE. Not "C-073, C-074 and C-075
must survive" — the ids that happened to collide on one afternoon — but *every*
declared total, blank count, id range, gap list and per-decision split in the
section, checked against what the table actually holds. A number added to the
section later is covered the moment somebody writes it in the shape the section
already uses; a row deleted by any means at all moves a derived count.

BLOCKQUOTES ARE EXCLUDED, AND THAT EXCLUSION IS ITSELF TESTED. The section quotes
its own historical WRONG figures as evidence — "25 `ship`, 8 `requires review`",
"nine rows were blank" — so a check that swept the whole section would read the
record of the defect as a statement of the defect. `test_the_historical_wrong_
figures_are_NOT_read_as_declarations` is the control: a scope error here fails
loudly rather than quoting the neighbouring paragraph.

THE FIFTH CHECK OF ITS SHAPE IN THIS REPO — a population read off disk against a
declaration kept by hand. `test_candidate_ids_are_unique.py` names the other
four. It is the first written after the surface drifted THREE times.
"""

from __future__ import annotations

import collections
import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]
_CANDIDATES = _REPO / "docs" / "standards" / "architecture" / "research" / \
    "candidates.md"

# A row:
#   `| C-069 | <finding> | <component> | <source> | <decision> | `status` | <note> |`
# Anchored at line start, exactly as the sibling check is, so a `C-NNN` merely
# CITED inside another row's prose is not read as an allocation.
#
# THE `component` CELL WAS INSERTED AFTER `Candidate` AND SHIFTED `decision` BY
# ONE. This regex read the fourth cell as the decision; without the extra group
# it would now read the SOURCE as one. Every source string normalises to a
# non-blank value, so the counts below would have read the whole table as ruled
# and the untriaged assertions would have compared thirty-one against zero —
# loud rather than silent, which is the only reason this was cheap to catch.
_ROW = re.compile(
    r"^\|\s*(C-\d{3})\s*\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|", re.M)

_SECTION = "## Where things stand"

_ONES = ("zero one two three four five six seven eight nine ten eleven twelve "
         "thirteen fourteen fifteen sixteen seventeen eighteen nineteen").split()
_TENS = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
         "eighty", "ninety")


def _spell(n: int) -> str:
    """`27` -> `twenty-seven`. The section writes small counts as words."""
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    return _TENS[tens] + (f"-{_ONES[ones]}" if ones else "")


def _text() -> str:
    return _CANDIDATES.read_text()


def _rows() -> list[tuple[str, str]]:
    """`(id, decision)` for every row, decision normalised out of its markup."""
    return [(cid, dec.strip().strip("`").strip())
            for cid, _cand, _comp, _src, dec in _ROW.findall(_text())]


def _declarations() -> str:
    """§ Where things stand with its blockquotes removed.

    The quoted lines hold this section's own history of being wrong, in the same
    grammar as its live claims. Reading them as declarations is the exact
    failure — a check quoting its neighbour's evidence — that passes green while
    asserting about the wrong region of the file.
    """
    body = _text().split(_SECTION, 1)[-1]
    body = body.split("\n## ", 1)[0]
    return "\n".join(ln for ln in body.splitlines() if not ln.lstrip().startswith(">"))


_UNTRIAGED = re.compile(
    r"\*\*([A-Za-z]+(?:-[a-z]+)?) rows are untriaged,[^*]*?:\s*"
    r"(C-\d{3}) through (C-\d{3})\.\*\*")
_SKIPS = re.compile(r"the numbering skips ((?:C-\d{3}(?:,\s*|\s+and\s+)?)+)")
_PREDATE = re.compile(
    r"The (\d+) rows that predate them carry a decision[^\n]*?"
    r"\*\*(\d+) `ship`\*\*, \*\*(\d+) `requires review`\*\*, \*\*(\d+) `reject`\*\*")
_REVIEW_QUEUE = re.compile(
    r"\*\*The `requires review` rows are the live queue, and there are "
    r"([a-z]+): ((?:C-\d{3}(?:,\s*)?)+)\.\*\*")
_REJECTED = re.compile(r"\*\*(\d+) rejected, and the reasoning is the point\.\*\*")

_ID = re.compile(r"C-\d{3}")


# --- vacuity floor -------------------------------------------------------

def test_the_candidates_file_is_where_it_is_declared_to_be() -> None:
    """If it moves, every assertion below passes against nothing."""
    assert _CANDIDATES.is_file(), (
        f"{_CANDIDATES} does not exist. Every derivation below would read an "
        f"empty string and agree with a declaration that says nothing."
    )


def test_there_are_enough_rows_for_this_check_to_mean_anything() -> None:
    """A derivation over zero rows agrees with any declaration at all."""
    assert len(_rows()) > 30


def test_the_section_this_check_reads_still_exists() -> None:
    """Renaming the heading must fail here, not silently empty the check."""
    assert _SECTION in _text(), (
        f"`{_SECTION}` is gone. Every pattern below is anchored inside it, so "
        f"its absence turns this whole module green against nothing. If the "
        f"section was renamed, rename `_SECTION` with it."
    )


# --- each declaration is FOUND, before it is compared ---------------------
#
# A pattern that stops matching is the failure this file exists to prevent,
# wearing a different hat: an unmatched declaration is an underived number,
# and `re.search(...) is None` is indistinguishable from `numbers agree` in
# any assertion that guards on the match first.

def test_every_declaration_this_check_verifies_is_actually_FOUND() -> None:
    found = {
        "untriaged total / id range": _UNTRIAGED.search(_declarations()),
        "skipped ids": _SKIPS.search(_declarations()),
        "predating rows and their decision split": _PREDATE.search(_declarations()),
        "requires-review queue": _REVIEW_QUEUE.search(_declarations()),
        "rejected count": _REJECTED.search(_declarations()),
    }
    missing = sorted(k for k, m in found.items() if m is None)
    assert not missing, (
        f"these declarations are no longer matched by this check: {missing}. "
        f"A pattern that stops matching does not fail — it stops checking, and "
        f"the number it guarded goes back to being a restatement. Either the "
        f"sentence was reworded (update the pattern here, in the same commit) "
        f"or the claim was deleted (delete its pattern here, deliberately)."
    )


def test_the_historical_wrong_figures_are_NOT_read_as_declarations() -> None:
    """The control on this check's SCOPE, not on its subject.

    § Where things stand quotes its own past errors — `25 \\`ship\\``, `8
    \\`requires review\\`` — inside blockquotes, in the same grammar as its live
    claims. If `_declarations()` ever stops stripping those, this check reads
    the record of the defect as the defect and goes red for the wrong reason,
    or worse, matches the historical figure FIRST and passes against it.
    """
    body = _text().split(_SECTION, 1)[-1].split("\n## ", 1)[0]
    assert "25 `ship`" in body, (
        "the historical-figures blockquote is gone from the section, so this "
        "control now proves nothing. Re-point it at whatever quoted history "
        "remains, or delete it deliberately."
    )
    assert "25 `ship`" not in _declarations(), (
        "`_declarations()` is no longer stripping blockquotes: the section's "
        "own record of having been wrong is being read as a live claim."
    )


# --- the derivations -----------------------------------------------------

def test_the_UNTRIAGED_COUNT_is_the_number_of_blank_decision_cells() -> None:
    blank = [cid for cid, dec in _rows() if not dec]
    m = _UNTRIAGED.search(_declarations())
    assert m and m.group(1).lower() == _spell(len(blank)), (
        f"§ Where things stand declares '{m.group(1) if m else None} rows are "
        f"untriaged'; the table holds {len(blank)} rows with a blank "
        f"`decision` ({_spell(len(blank))}). Blank is the truth of an untriaged "
        f"row — but blank is only honest while this paragraph says how many "
        f"there are, which is that paragraph's own sentence. Fix the sentence, "
        f"and check whether a row went missing rather than assuming it did not."
    )


def test_the_declared_ID_RANGE_spans_exactly_the_untriaged_rows() -> None:
    blank = sorted(cid for cid, dec in _rows() if not dec)
    m = _UNTRIAGED.search(_declarations())
    assert m, "the untriaged declaration is unmatched — see the FOUND test"
    assert (m.group(2), m.group(3)) == (blank[0], blank[-1]), (
        f"§ Where things stand declares the untriaged working set runs "
        f"{m.group(2)} through {m.group(3)}; the blank rows actually run "
        f"{blank[0]} through {blank[-1]}. `triage-candidates` takes its working "
        f"set from the table, so a wrong range in prose points a human at a "
        f"different queue from the one the run will process."
    )


def test_the_declared_SKIPPED_IDS_are_exactly_the_gaps_in_that_range() -> None:
    """The gap list is the one declaration a DELETED row moves on its own.

    A dropped row leaves a hole. If the hole is not declared, the count test
    above catches it — and if somebody fixes the count without asking why, this
    catches the hole itself and names it.
    """
    blank = sorted(int(cid[2:]) for cid, dec in _rows() if not dec)
    present = {int(cid[2:]) for cid, _ in _rows()}
    gaps = {f"C-{n:03d}" for n in range(blank[0], blank[-1] + 1)
            if n not in present}
    m = _SKIPS.search(_declarations())
    assert m, "the skipped-ids declaration is unmatched — see the FOUND test"
    declared = set(_ID.findall(m.group(1)))
    assert declared == gaps, (
        f"§ Where things stand declares the numbering skips {sorted(declared)}; "
        f"the table's actual gaps between {blank[0]} and {blank[-1]} are "
        f"{sorted(gaps)}. An UNDECLARED gap is the shape a deleted row leaves "
        f"behind — check whether a row vanished before editing this sentence. "
        f"A conflict resolution deletes rows with no diff to show for it."
    )


def test_the_DECIDED_ROW_COUNT_and_its_SPLIT_are_derived_from_the_column() -> None:
    counts = collections.Counter(dec for _cid, dec in _rows() if dec)
    m = _PREDATE.search(_declarations())
    assert m, "the predating-rows declaration is unmatched — see the FOUND test"
    declared = (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
    derived = (sum(counts.values()), counts["ship"], counts["requires review"],
               counts["reject"])
    assert declared == derived, (
        f"§ Where things stand declares (total, ship, requires review, reject) "
        f"= {declared}; the `decision` column holds {derived}. This exact "
        f"sentence has been wrong once before — it read '25 `ship`, 8 "
        f"`requires review`' when the split was 27/6, and the file quotes "
        f"itself saying so two paragraphs down."
    )


def test_the_REJECTED_COUNT_agrees_with_itself_in_both_places() -> None:
    """One number, declared twice, by two different sentences.

    Restating it in a second paragraph doubles the ways it goes stale, and the
    second paragraph is the one nobody re-reads when the split changes.
    """
    rejected = sum(1 for _cid, dec in _rows() if dec == "reject")
    m = _REJECTED.search(_declarations())
    assert m, "the rejected-count declaration is unmatched — see the FOUND test"
    assert int(m.group(1)) == rejected, (
        f"the '§ Where things stand' rejected paragraph declares "
        f"{m.group(1)}; the column holds {rejected}. The decision-split "
        f"sentence above it declares this same number separately — if only one "
        f"of the two moved, they are now contradicting each other in one "
        f"section."
    )


def test_the_REQUIRES_REVIEW_QUEUE_is_listed_by_id_and_the_ids_are_the_column() -> None:
    """The live operator queue, declared as both a count AND an id list.

    This is the queue `direction.md` files against, so a wrong id here sends a
    ruling to a row that never asked for one.
    """
    derived = [cid for cid, dec in _rows() if dec == "requires review"]
    m = _REVIEW_QUEUE.search(_declarations())
    assert m, "the requires-review declaration is unmatched — see the FOUND test"
    assert m.group(1).lower() == _spell(len(derived)), (
        f"the requires-review queue is declared as '{m.group(1)}' rows; the "
        f"column holds {len(derived)} ({_spell(len(derived))})."
    )
    assert _ID.findall(m.group(2)) == derived, (
        f"the requires-review queue is declared as {_ID.findall(m.group(2))}; "
        f"the column holds {derived}. These rows are what `direction.md` files "
        f"against — a wrong id here routes an operator ruling to a row that "
        f"never asked for one."
    )

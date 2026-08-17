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

# The SAME row, UNNORMALISED — the rendering check below needs the cell as it
# was typed, and `_ROW` deliberately stops one cell short of `status`.
_RAW_ROW = re.compile(
    r"^\|\s*(C-\d{3})\s*\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|", re.M)

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


# --- where a table IS, derived once and asked by both rendering checks -------
#
# THE TWO CHECKS BELOW ASK DIFFERENT QUESTIONS OF THE SAME BOUNDARY, and they
# used to compute it separately — one inline, one not at all. That is the drift
# seam this file's own subject is about, one level down: a second definition of
# "inside a table" is a second thing that can be right on Tuesday.


def _ends_the_table(line: str) -> bool:
    """Whether `line` closes a GFM table block. NOT "has no pipe".

    A PLAIN PARAGRAPH LINE DOES NOT CLOSE THE TABLE, and a first version of the
    contiguity check below broke the block on any non-`|` line and reported
    C-051 as an orphan. GitHub's own `/markdown` API disagreed and the API was
    right. Only a blank line or a genuine block-level opener closes it.

    WHAT SUCH A LINE ACTUALLY DOES WAS STATED WRONG HERE FOR ONE REVISION, and
    the correction is the whole reason the cell-count check below was blind.
    This comment used to say the paragraph is *"lazily absorbed into the
    preceding row's last cell"*. It is not. MEASURED through `POST /markdown`
    on lines 157-164 of this file, back when a 1,981-character paragraph sat
    between C-050 and C-051: the block rendered **seven** `<tr>`s, not six, and
    the paragraph was its own row with all 1,981 characters in the **ID**
    column and six empty cells beside it — while C-050's Note was cut to 6,677
    characters, losing exactly the evidence the paragraph carried. Joining it
    back took the block to six `<tr>`s and C-050's Note to 8,633.

    So the absorption story was consoling and false: a stray line inside a
    table is not swallowed by its neighbour, it is a VISIBLE detached row that
    steals its neighbour's evidence. Both rows still render, which is what made
    the wrong explanation survive — the sibling check only ever asked whether
    C-050 and C-051 rendered, and they did.
    """
    s = line.strip()
    return (not s
            or s.startswith(("#", ">", "```", "~~~", "- ", "* ", "+ "))
            or set(s) <= {"-", "*", "_", " "} and len(s) >= 3)


def _is_delimiter(line: str) -> bool:
    """The `|---|---|` row, which is what makes a run of lines a TABLE."""
    return (set(line.replace("|", "").replace(" ", "")) <= {"-", ":"}
            and bool(line.replace("|", "").strip()))


def _table_blocks(lines: list[str]) -> list[list[int]]:
    """Every table in the file, as the line indices GFM renders it from.

    A block is returned HEADER-FIRST — `block[0]` is the header row, `block[1]`
    its delimiter, and the rest its body — because the header is what every
    per-table question is asked against. A run of lines with no delimiter is
    not a table and is not returned; a delimiter with no line above it inside
    the same run has no header, so GFM builds no table and neither does this.

    THE FILE HOLDS TABLES OF TWO DIFFERENT WIDTHS and that is why blocks are
    kept separate rather than merged into one set of "table lines": § Two flags
    and the `component` table are three columns, the eleven candidate tables
    are seven. A single expected cell count applied across the file would
    report every row of the narrow tables as malformed.
    """
    blocks: list[list[int]] = []
    run: list[int] = []
    for index, line in enumerate([*lines, ""]):
        if not _ends_the_table(line):
            run.append(index)
            continue
        delimiter = next((j for j in run if _is_delimiter(lines[j])), None)
        if delimiter is not None and delimiter > run[0]:
            blocks.append([j for j in run if j >= delimiter - 1])
        run = []
    return blocks


def _cells(line: str) -> int:
    """Cells a GFM renderer sees. `\\|` is an escape and never splits."""
    return len(re.split(r"(?<!\\)\|", line))


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


def test_EVERY_ROW_THIS_CHECK_COUNTS_ACTUALLY_RENDERS_AS_A_TABLE_ROW() -> None:
    """Matching `^|…|` is not the same as BEING a row, and the gap is a real one.

    MEASURED, ON THIS FILE, BY THE PASS THAT ADDED THIS TEST. A run appended a
    new candidate to the END of the file — which is BELOW `## Where things
    stand` and its prose — instead of continuing the table. GitHub-flavoured
    markdown needs body rows contiguous with their header and delimiter, so the
    line rendered as a stray paragraph of pipe-delimited text and the table
    still visibly ended at the previous id. Confirmed through GitHub's own
    `/markdown` API: the id did not appear inside a `<td>`.

    EVERY OTHER CHECK IN THIS MODULE AGREED WITH IT. `_ROW` scans the whole file
    text with no notion of where the table is, so the orphan counted as a row;
    the run had also updated the prose to match, so the declared total and the
    derived total agreed and the suite went green. A guard built to stop the
    file's claims drifting from its contents was blind to a row that textually
    exists and visually does not — which is the class this file's own subject
    belongs to: it checked the pattern that stands in for the property instead
    of the property.

    So the check is on CONTIGUITY, not on the id or the position: every counted
    row must be reachable from the delimiter row by an unbroken run of `|` lines.
    A row appended after any future heading fails here rather than rendering
    invisibly, whatever that heading turns out to be.
    """
    lines = _text().split("\n")
    in_table = {i for block in _table_blocks(lines) for i in block}

    orphans = [lines[i].split("|")[1].strip()
               for i, line in enumerate(lines)
               if _ROW.match(line) and i not in in_table]
    assert not orphans, (
        f"these rows are counted by every check in this module but do NOT render "
        f"as table rows: {orphans}. A `|`-line separated from the table by a "
        f"blank line, a heading or a paragraph is a paragraph. Move it back into "
        f"the table — appending to the end of the file puts it below "
        f"`{_SECTION}`, which is how this was found."
    )


def test_EVERY_ROW_SPLITS_INTO_THE_HEADER_S_CELL_COUNT() -> None:
    """A row with a surplus `|` renders TRUNCATED, and everything stays green.

    THE SIBLING ABOVE ASKS WHETHER A ROW RENDERS AT ALL; THIS ASKS WHETHER IT
    RENDERS WHOLE, and the two are different failures with the same green.
    GitHub-flavoured markdown splits a table row on `|` BEFORE it parses inline
    content, so a pipe inside an inline code span — a regex alternation, a
    shell pipeline in the evidence — is a cell break. GFM then DROPS every cell
    past the header's count, and the last surviving cell is cut at the offending
    pipe. Nothing errors and nothing warns.

    MEASURED ON THIS FILE, RENDERED THROUGH GITHUB'S OWN `/markdown` API rather
    than reasoned about: three rows were truncated at once. C-101 lost 2158 of
    its 2769 characters at `` `git show … | grep -c …` ``; C-093 lost 2818 of
    3561 at `` `grep -rn 'hour|hrs'` ``; C-062 lost its adjudication at a
    `(MiB|GiB|MB|GB|KiB)` character class. What is lost is always the RIGHT-HAND
    side of the row — which in this table is the `Note`, i.e. the evidence a
    human triaging the candidate is supposed to weigh. The row keeps its id, its
    `decision` and its `status`, so every derived count in this module was
    correct over all three and every one of them was green.

    THE ESCAPE IS `\\|`, AND IT WORKS INSIDE A CODE SPAN — the escape is
    processed at cell-splitting time and the backslash does not survive into the
    rendered code. This file already relied on that at C-056 and C-064 before
    anyone stated it.

    WHY THIS BELONGS HERE. This module's own subject is a file whose claims
    drift from its contents, and its sibling above already records the class:
    *"it checked the pattern that stands in for the property instead of the
    property."* The source text is a stand-in for the rendering. The module even
    keeps a second regex, `_RAW_ROW`, precisely because the rendering check
    needs the cell as typed — and then never counted the cells.

    ITS POPULATION IS WHAT GFM TREATS AS A ROW, NOT WHAT `_ROW` MATCHES, and
    that distinction is this check's own second defect rather than a nicety.
    The first version iterated lines matching `^\\| (C-\\d{3}) \\|` — a PROXY for
    "a row", and the same substitution the sibling above was written to record.
    A line GFM renders as a row while carrying no `C-NNN` is invisible to it,
    and one was sitting in this file when the check shipped: C-050's Note had
    its 1,981-character tail split onto its own line, which rendered as a
    detached row with the whole paragraph in the ID column and cut C-050's Note
    by 1,956 characters. Cell-count blind, contiguity blind, every derived
    count green — because the stray carried no id, so nothing counted it and
    nothing missed it. The population is now every line inside a table block.

    EACH BLOCK IS CHECKED AGAINST ITS OWN HEADER. This file holds tables of two
    widths — § Two flags and the `component` table are three columns, the
    eleven candidate tables are seven — so a single expected count taken from
    the candidate header would report every narrow row as malformed. That is
    the shape a widened population fails in, and it is why `_table_blocks`
    returns blocks rather than one flat set of line numbers.

    WHAT THIS DOES NOT LOOK AT. It is a CELL-COUNT check, not a rendering
    check: it cannot see an unbalanced backtick, or a cell whose content is
    malformed in any way that does not change how many cells there are. It
    cannot see a table whose header is WRONG — a header with the right number
    of columns and the wrong names passes, and so does a body row whose cells
    are correctly counted and shifted one column left. It says nothing about
    tables in any other file. And it inherits `_ends_the_table`'s notion of
    where a table stops, so a block-level opener this repo has not used yet
    (an HTML block, a footnote definition) would end a table here while GFM
    kept it open, silently shrinking the population rather than failing.
    """
    lines = _text().split("\n")

    wrong: list[str] = []
    strays: list[str] = []
    for block in _table_blocks(lines):
        expected = _cells(lines[block[0]])
        for i in block:
            line = lines[i]
            if not line.lstrip().startswith("|"):
                strays.append(f"line {i + 1}: {line.strip()[:60]!r}")
            elif _cells(line) != expected:
                label = line.split("|")[1].strip()[:40] or f"line {i + 1}"
                wrong.append(f"{label} ({_cells(line)} fields, expected {expected})")

    assert not strays, (
        f"these lines sit INSIDE a table block but are not rows — they open "
        f"with no `|`, so GFM renders each as a detached row carrying its whole "
        f"text in the FIRST column and blanks in the rest, while the row above "
        f"loses the text as its own Note: {strays}. This is what a `Note` cell "
        f"split across two lines looks like. Join it back onto the end of the "
        f"row it belongs to, escaping any interior pipe as `\\|`, and change no "
        f"word of the content."
    )
    assert not wrong, (
        "these rows do not split into their table header's field count, so "
        "GitHub drops their surplus cells and truncates the last one that "
        "survives — the Note, which is the evidence: "
        + "; ".join(wrong)
        + ". Escape the pipe as `\\|`. It is honoured inside an inline code "
          "span, so a regex alternation or a shell pipeline in the evidence "
          "stays readable. Do NOT resolve this by deleting the evidence."
    )


def test_the_TABLE_BLOCK_SCAN_reads_the_tables_that_are_actually_there() -> None:
    """The widened population's own vacuity floor.

    `_table_blocks` returning `[]` — a changed delimiter spelling, a heading
    convention this scan does not recognise — makes the two checks above pass
    over nothing, and a guard reading no lines is indistinguishable from a
    guard finding no defects. The sibling module states this rule for the
    file-sweep; a population derived by parsing needs it more, not less.

    THE WIDTHS ARE ASSERTED, NOT JUST THE COUNT. Two widths is the property
    that makes per-block headers necessary; collapsing to one would make a
    single global expected count look correct again.
    """
    lines = _text().split("\n")
    blocks = _table_blocks(lines)
    assert len(blocks) > 5, (
        f"the table scan found {len(blocks)} tables in {_CANDIDATES.name}. The "
        f"cell-count and contiguity checks are both derived from this, so a "
        f"scan that finds nothing turns both green against nothing."
    )
    counted = sum(len(b) for b in blocks)
    assert counted > 60, (
        f"the table scan reached only {counted} lines across {len(blocks)} "
        f"tables — the blocks are being truncated, and every line it did not "
        f"reach is a line neither check above is looking at."
    )
    widths = {_cells(lines[b[0]]) for b in blocks}
    assert len(widths) > 1, (
        f"every table in {_CANDIDATES.name} is now {widths} fields wide. The "
        f"per-block header lookup exists because they are not — if the narrow "
        f"tables were removed or widened, say so deliberately; until then this "
        f"is the scan mis-reading a header."
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


# --- the flag cells, against the vocabulary the file declares for them -------
#
# THE SAME SHAPE AS EVERY CHECK ABOVE, ONE COLUMN OVER: a declaration kept by
# hand, and a population read off disk. § Two flags renders each flag's admitted
# values in backticks; every data row is supposed to render the cell the same
# way, and 79 of 81 did. The two that did not were appended by an automated pass
# on this very branch, minutes apart, and nothing was watching — which is the
# whole argument for a gate rather than a third correction.
#
# WHY IT IS NOT `_check_shape`'S JOB. The runtime parser normalises backticks
# away on purpose: it reads whatever file a pipeline was handed, possibly a
# branch mid-collision, and must not abort a `plan-project` run over a cosmetic
# cell. A merge-gate on the default branch is where a rendering convention
# belongs, and it is the difference between "the value is admissible" (runtime)
# and "the file speaks one language" (here).
#
# DERIVED FROM § Two flags, NOT HARD-CODED. If the file admits a new value, the
# row declaring it moves this check with it — the same reason every count above
# is derived rather than restated.

_FLAG_DECL = "## Two flags, orthogonal — do not collapse them"
_BACKTICKED = re.compile(r"`([^`]+)`")

# `normalise_cell`'s blank set, which is the runtime's own definition of "this
# row has not been ruled / has no status yet". Kept identical on purpose: a
# rendering the parser calls blank must not be reported as a foreign spelling.
_BLANK_SPELLINGS = ("", "—", "-")


def _declared_values(flag: str) -> list[str]:
    """The backticked values § Two flags admits for `decision` or `status`."""
    body = _text().split(_FLAG_DECL, 1)[-1].split("\n## ", 1)[0]
    for line in body.splitlines():
        if line.startswith(f"| **`{flag}`**"):
            values = line.strip().strip("|").split("|")[1]
            return [v for v in _BACKTICKED.findall(values) if v != flag]
    return []


def test_the_FLAG_VOCABULARY_is_declared_where_this_check_reads_it() -> None:
    """POSITIVE CONTROL on the derivation, against its own vacuity.

    An empty admitted-set makes every cell foreign, which fails loudly — but a
    PARTIAL one is the dangerous shape: it would report correct rows as
    offenders and send somebody to edit the table instead of the declaration.
    Naming what the section is expected to admit is what tells the two apart.
    """
    assert _declared_values("decision") == ["ship", "requires review", "reject"], (
        f"§ Two flags declares decision as {_declared_values('decision')}. This "
        f"check reads its vocabulary from that row; if the row moved or was "
        f"reworded, the assertion below is comparing against the wrong set.")
    assert _declared_values("status") == ["open", "closed"], (
        f"§ Two flags declares status as {_declared_values('status')}.")


def test_EVERY_ROW_RENDERS_ITS_FLAGS_THE_WAY_THE_FILE_DECLARES_THEM() -> None:
    """One file, one spelling — because an automated writer appends here.

    `decision_log_and_reflection.md` instructs every producing run to append a
    row, so this table's growth is machine-written and unreviewed cell-by-cell.
    A second spelling costs a human scanning for `` `open` `` two rows and costs
    any future grep-shaped reader the same, and the file is the queue `/standup`
    reads. Deriving the admitted renderings from § Two flags means the fix for a
    genuinely new value is to declare it, not to widen this test.
    """
    admitted = {
        "decision": {f"`{v}`" for v in _declared_values("decision")},
        "status": {f"`{v}`" for v in _declared_values("status")},
    }
    offenders: list[str] = []
    for cid, _cand, _comp, _src, dec, st in _RAW_ROW.findall(_text()):
        for flag, cell in (("decision", dec), ("status", st)):
            value = cell.strip()
            if value in _BLANK_SPELLINGS or value in admitted[flag]:
                continue
            offenders.append(f"{cid} {flag}={cell!r}")
    assert not offenders, (
        f"these cells do not render the way § Two flags declares the value: "
        f"{offenders}. Every other row wraps the value in backticks; the two "
        f"that did not were written by an automated pass and nothing caught "
        f"them. Match the declaration, or change the declaration.")

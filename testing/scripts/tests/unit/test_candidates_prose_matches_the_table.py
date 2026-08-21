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

WHAT THIS KEYS ON IS THE CLASS, NOT THE INSTANCE. Not "C-4pr7kq11, C-xh8nvwqn and C-iceozlh1
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

import pytest

from gfm_table_scan import (
    blank_fenced,
    cells,
    off_width_rows,
    stranded_rows,
    stray_lines,
    table_blocks,
)

_REPO = Path(__file__).resolve().parents[4]
_CANDIDATES = _REPO / "docs" / "standards" / "architecture" / "research" / \
    "candidates.md"


def _scan() -> list[str]:
    """`candidates.md`'s lines with fenced code blanked.

    THIS FILE WENT UNFENCED FOR ONE REVISION WHILE ITS SIBLING DID NOT, and
    nothing said so. Both gates read `candidates.md` — it is tracked `.md`, so
    it is in the tree-wide population too — which meant a fenced example of a
    malformed row would have been a defect to one gate and correct to the
    other. That is plausible content for THIS file specifically, since it is
    the file the whole defect class was found in and its Notes quote table
    rows. Measured today: zero fenced blocks in `candidates.md`, so this
    changes no current verdict. It removes an asymmetry that was undisclosed
    rather than decided.
    """
    return blank_fenced(_text().split("\n"))

# A row:
#   `| C-skkjo6jn | <finding> | <component> | <source> | <decision> | `status` | <note> |`
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
    r"^\|\s*(C-[0-9a-z]+)\s*\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|", re.M)

# The SAME row, UNNORMALISED — the rendering check below needs the cell as it
# was typed, and `_ROW` deliberately stops one cell short of `status`.
_RAW_ROW = re.compile(
    r"^\|\s*(C-[0-9a-z]+)\s*\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|", re.M)

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


# NO ID RANGE, AND NO SKIP LIST. Both were declarations here until 2026-08-21
# and both were properties of SEQUENTIAL allocation: a range selects a
# contiguous block, and a "skip" is a gap in a sequence. Ids are now eight
# random base36 characters, so neither is observable and neither is asserted.
# They were deleted with the scheme rather than ported, because a check that
# still passes while meaning nothing is worse than no check at all.
_UNTRIAGED = re.compile(
    r"\*\*([A-Za-z]+(?:-[a-z]+)?) rows are untriaged, and they are the next"
    r"[^*]*?working set\.\*\*")
_PREDATE = re.compile(
    r"The (\d+) rows that predate them carry a decision[^\n]*?"
    r"\*\*(\d+) `ship`\*\*, \*\*(\d+) `requires review`\*\*, \*\*(\d+) `reject`\*\*")
_REVIEW_QUEUE = re.compile(
    r"\*\*The `requires review` rows are the live queue, and there are "
    r"([a-z]+): ((?:C-[0-9a-z]+(?:,\s*)?)+)\.\*\*")
_REJECTED = re.compile(r"\*\*(\d+) rejected, and the reasoning is the point\.\*\*")

_ID = re.compile(r"C-[0-9a-z]{8}")


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
    lines = _scan()
    in_table = {i for block in table_blocks(lines) for i in block}

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
    than reasoned about: three rows were truncated at once. C-npx1uwgj lost 2158 of
    its 2769 characters at `` `git show … | grep -c …` ``; C-2asq6d9x lost 2818 of
    3561 at `` `grep -rn 'hour|hrs'` ``; C-8rhxo6st lost its adjudication at a
    `(MiB|GiB|MB|GB|KiB)` character class. What is lost is always the RIGHT-HAND
    side of the row — which in this table is the `Note`, i.e. the evidence a
    human triaging the candidate is supposed to weigh. The row keeps its id, its
    `decision` and its `status`, so every derived count in this module was
    correct over all three and every one of them was green.

    THE ESCAPE IS `\\|`, AND IT WORKS INSIDE A CODE SPAN — the escape is
    processed at cell-splitting time and the backslash does not survive into the
    rendered code. This file already relied on that at C-rrm2t4sj and C-jeyows79 before
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
    and one was sitting in this file when the check shipped: C-523klr8n's Note had
    its 1,981-character tail split onto its own line, which rendered as a
    detached row with the whole paragraph in the ID column and cut C-523klr8n's Note
    by 1,956 characters. Cell-count blind, contiguity blind, every derived
    count green — because the stray carried no id, so nothing counted it and
    nothing missed it. The population is now every line inside a table block.

    EACH BLOCK IS CHECKED AGAINST ITS OWN HEADER. This file holds tables of two
    widths — § Two flags and the `component` table are three columns, the
    eleven candidate tables are seven — so a single expected count taken from
    the candidate header would report every narrow row as malformed. That is
    the shape a widened population fails in, and it is why `table_blocks`
    returns blocks rather than one flat set of line numbers.

    WHAT THIS DOES NOT LOOK AT. It is a CELL-COUNT check, not a rendering
    check: it cannot see an unbalanced backtick, or a cell whose content is
    malformed in any way that does not change how many cells there are. It
    cannot see a table whose header is WRONG — a header with the right number
    of columns and the wrong names passes, and so does a body row whose cells
    are correctly counted and shifted one column left. It says nothing about
    tables in any other file: that is
    `test_EVERY_TABLE_ROW_IN_EVERY_TRACKED_MARKDOWN_FILE_RENDERS_WHOLE` in
    `test_markdown_tables_render_whole.py`, which asks the same derivation of
    every tracked `.md`. Both call `off_width_rows`, so there is one definition
    of the property and two populations, rather than two loops that were
    identical on the day they were typed.

    AND IT INHERITS `ends_the_table`'s NOTION OF WHERE A TABLE STOPS. This
    paragraph SAID THE WRONG THING for one revision, in the same docstring that
    corrects `ends_the_table`'s own wrong story two functions above — it
    claimed such an opener "would end a table here while GFM kept it open,
    silently shrinking the population". Measured through `POST /markdown`, it
    is the other way round: `<div>html</div>` inside a table ENDS it for
    GitHub, and this scan — which tests no `<` — keeps the block open and reads
    the rows after it as members. They are not members: GitHub renders them as
    literal text. So the failure is the scan OVER-extending and missing rows
    that stopped rendering, not under-reaching. The residual is disclosed here
    and held red-able by
    `test_an_HTML_BLOCK_opener_is_the_residual_this_scan_does_NOT_see`, because
    `<span>` does NOT end a table and a blanket `<` test would invent failures
    GitHub does not have.
    """
    lines = _scan()
    wrong = [
        f"{lines[i].split('|')[1].strip()[:40] or f'line {i + 1}'} "
        f"({actual} fields, expected {expected})"
        for i, actual, expected in off_width_rows(lines)
    ]

    assert not wrong, (
        "these rows do not split into their table header's field count, so "
        "GitHub drops their surplus cells and truncates the last one that "
        "survives — the Note, which is the evidence: "
        + "; ".join(wrong)
        + ". Escape the pipe as `\\|`. It is honoured inside an inline code "
          "span, so a regex alternation or a shell pipeline in the evidence "
          "stays readable. Do NOT resolve this by deleting the evidence."
    )


def test_EVERY_LINE_INSIDE_A_TABLE_BLOCK_IS_ACTUALLY_A_ROW() -> None:
    """A non-`|` line inside a table renders as a DETACHED row, not as prose.

    THIS IS A SHAPE CHECK, NOT A CELL COUNT, and it rode inside the cell-count
    check for one revision — one function, two properties, two unrelated
    failure messages, so a red run named "cell count" in the report and "stray
    line" in the body. It belongs beside the contiguity check above, which asks
    the SAME boundary question from the other side: that one asks whether every
    row is inside a block, this one asks whether everything inside a block is a
    row. Together they are what "the population is what GFM treats as a row"
    actually means.

    The instance that produced it: C-523klr8n's `Note` had a 1,981-character tail
    split onto its own line. Rendered through `POST /markdown` it came back as
    its own `<tr>` with the whole paragraph in the ID column and six empty
    cells beside it, while C-523klr8n's own Note was cut by 1,956 characters —
    invisible to the cell count (it carried no id for `_ROW` to match) and
    invisible to contiguity (contiguity only asks about lines that DO match).
    """
    lines = _scan()
    strays = [f"line {i + 1}: {lines[i].strip()[:60]!r}" for i in stray_lines(lines)]
    assert not strays, (
        f"these lines sit INSIDE a table block but are not rows — they open "
        f"with no `|`, so GFM renders each as a detached row carrying its whole "
        f"text in the FIRST column and blanks in the rest, while the row above "
        f"loses the text as its own Note: {strays}. This is what a `Note` cell "
        f"split across two lines looks like. Join it back onto the end of the "
        f"row it belongs to, escaping any interior pipe as `\\|`, and change no "
        f"word of the content."
    )


def test_EVERY_PIPE_OPENING_LINE_SITS_INSIDE_A_TABLE_BLOCK() -> None:
    """The other half of the same boundary, and the half that was still open.

    WHY THIS EXISTS WHEN THE CONTIGUITY CHECK ALREADY RUNS. That one's
    population is `_ROW` — `^\\| (C-\\d{3}) \\|` — so it can only speak for the
    candidate tables. This file also holds two THREE-COLUMN tables (§ Two flags
    and the `component` table) whose rows carry no id, and they are the ones
    that state who may write `decision`, `status` and `component`. MEASURED:
    inserting a `- ` list line into § Two flags left the ENTIRE suite green,
    while `POST /markdown` broke the table there and swallowed the row after it
    into the `<li>`. Both existing checks were structurally unable to see it —
    `table_blocks` ends the block at the `- `, so the stranded row is outside
    every block and the two checks above only ever look INSIDE one.

    So the question this asks is the complement: not "is everything in a block
    a row" but "is every row in a block". A `|`-opening line that no block
    claims is a line GFM has stopped rendering as a row.

    IT IS A FLOOR, NOT A PARSE. It cannot tell you WHY the line fell out — the
    block-level opener above it, a deleted delimiter, a stray blank — only that
    it did, which is enough to make somebody look. Measured at 0 violations on
    the file as it stands.

    THIS IS THE STRICT BAR, AND IT IS THE ONE THING THE TREE-WIDE GATE DOES NOT
    COPY. `stranded_rows` asserts that EVERY `|`-opening line is a row, which is
    right here — `candidates.md` is a curated table file with no prose reason to
    type a pipe at the start of a line — and wrong for the tree, where three
    files carry a deliberate one-line row-shape illustration under a heading.
    `test_NO_TABLE_ROW_ANYWHERE_IN_THE_TREE_IS_SEVERED_FROM_ITS_BLOCK` in
    `test_markdown_tables_render_whole.py` asks `severed_rows` instead, which is
    the same shape at a bar that survives prose. Two bars, one derivation, and
    each states why it is the one it is.
    """
    lines = _scan()
    stranded = [f"line {i + 1}: {lines[i].strip()[:60]!r}" for i in stranded_rows(lines)]
    assert not stranded, (
        f"these lines open with `|` but sit OUTSIDE every table block, so GFM "
        f"renders them as literal text rather than as rows and every cell they "
        f"carry is lost: {stranded}. Something above them ended the table — a "
        f"list marker, a heading, a blockquote, an HTML block, or a delimiter "
        f"row that stopped being one. Find that line and move it out of the "
        f"table; do not delete the rows."
    )


def test_the_TABLE_BLOCK_SCAN_reads_the_tables_that_are_actually_there() -> None:
    """The widened population's own vacuity floor.

    `table_blocks` returning `[]` — a changed delimiter spelling, a heading
    convention this scan does not recognise — makes the two checks above pass
    over nothing, and a guard reading no lines is indistinguishable from a
    guard finding no defects. The sibling module states this rule for the
    file-sweep; a population derived by parsing needs it more, not less.

    THE WIDTHS ARE ASSERTED, NOT JUST THE COUNT. Two widths is the property
    that makes per-block headers necessary; collapsing to one would make a
    single global expected count look correct again.
    """
    lines = _scan()
    blocks = table_blocks(lines)
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
    widths = {cells(lines[b[0]]) for b in blocks}
    assert len(widths) > 1, (
        f"every table in {_CANDIDATES.name} is now {widths} fields wide. The "
        f"per-block header lookup exists because they are not — if the narrow "
        f"tables were removed or widened, say so deliberately; until then this "
        f"is the scan mis-reading a header."
    )


# --- the gate discriminates ----------------------------------------------
#
# SECTION HEADERS HERE MATCH `test_markdown_tables_render_whole.py`'s VERBATIM,
# and that is not decoration. The two modules are structurally parallel — same
# derivations, two populations, two bars — and their docstrings cross-reference
# each other by name throughout. For one revision this module folded its
# discrimination tests and its residual tests into a single undifferentiated
# section, so a reader comparing the two had to redo the categorisation by eye
# every time instead of reading it off the outline.
#
# EVERY CHECK ABOVE IS DERIVED FROM `table_blocks`, AND UNTIL HERE ITS ONLY
# CORPUS WAS `candidates.md` AS IT STANDS TODAY. That makes "still parses the
# file correctly" the whole of its regression cover, which says nothing about a
# shape the file does not currently contain — and the tree-wide gate now takes
# these helpers to every markdown table the repo treats as authoritative, where
# those shapes are the point. The fixtures below are synthetic on purpose: each
# one's expected answer was MEASURED through GitHub's `POST /markdown` first,
# so what is asserted here is the renderer's behaviour rather than this
# module's reading of the spec.


@pytest.mark.parametrize(("shape", "body", "expect_rows_after"), [
    ("a plain paragraph line",   "a stray paragraph",            True),
    ("an unordered list marker", "- a stray list line",          False),
    ("an ordered list at 1",     "1. a stray ordered line",      False),
    ("an ordered list at 2",     "2. a stray ordered line",      False),
    ("a heading",                "## a stray heading",           False),
    ("a blockquote",             "> a stray quote",              False),
])
def test_the_SCAN_BREAKS_A_TABLE_WHERE_GITHUB_BREAKS_IT(
    shape: str, body: str, expect_rows_after: bool,
) -> None:
    """Each answer below came back from `POST /markdown`, not from the spec.

    `expect_rows_after` is whether GitHub still rendered `| 3 | 4 |` as a
    `<tr>` after the interposed line. For the plain paragraph it did — twice,
    which is the measurement that made `ends_the_table` stop breaking on
    every non-`|` line. For the five block-level openers it did not: the row
    came back inside the `<ol>`/`<ul>`/raw text instead.

    THE ORDERED-LIST PAIR IS WHY THIS IS PARAMETRIZED RATHER THAN ONE CASE.
    CommonMark only lets an ordered list interrupt a PARAGRAPH when it starts
    at 1, so a spec reading predicts `2.` keeps the table open. Measured, it
    does not — `<ol start="2">` swallowed the row exactly as `1.` did. The
    pattern is `^\\d+[.)] ` because of this line, not despite it.
    """
    lines = f"| A | B |\n|---|---|\n| 1 | 2 |\n{body}\n| 3 | 4 |\n".split("\n")
    blocks = table_blocks(lines)
    assert len(blocks) == 1, f"{shape}: expected one table, got {len(blocks)}"
    reached = 4 in blocks[0]
    assert reached is expect_rows_after, (
        f"{shape}: GitHub {'still renders' if expect_rows_after else 'does NOT render'} "
        f"the row after it as a `<tr>`, and this scan {'does not' if expect_rows_after else 'does'} "
        f"agree. `ends_the_table` and the renderer have to draw the same "
        f"boundary — a scan that ends the table early reports live rows as "
        f"stranded, and one that ends it late reads literal text as rows."
    )


@pytest.mark.parametrize(("shape", "text"), [
    ("a two-column header",  "| A | B |"),
    ("one escaping pipe",    "| a \\| b | c |"),
    ("a doubled backslash",  "| a \\\\| b | c |"),
])
def test_CELLS_counts_what_the_renderer_SPLITS_ON(shape: str, text: str) -> None:
    """A DOUBLED backslash was raised as a miscount and MEASURED not to be one.

    A reviewer read `(?<!\\\\)\\|` as mishandling `\\\\|`: by CommonMark's inline
    rules a doubled backslash is an escaped backslash, so the pipe after it is
    unescaped and ought to split, truncating the row exactly the way this whole
    module exists to catch. Rendered through `POST /markdown` against a
    two-column header, `| a \\\\| b | c |` came back as exactly TWO cells reading
    `a | b` and `c` — GitHub's ROW SPLITTER runs before inline escaping and
    treats ANY backslash-preceded pipe as escaped, doubled or not. The
    one-character lookbehind is what the renderer does.

    All three shapes below are two rendered columns, so all three must count
    the same. Kept as a fixture rather than a note in a review comment, because
    the next reader will have the same correct-sounding instinct and a note
    does not go red.
    """
    assert cells(text) == cells("| A | B |"), f"{shape}: {text!r}"


def test_A_RUN_WITH_NO_DELIMITER_IS_NOT_A_TABLE() -> None:
    """The floor under `table_blocks`' own definition of a table.

    Pipes alone do not make a table — GFM needs the `|---|` row, and a run of
    pipe-looking prose without one renders as a paragraph. If this stopped
    holding, every `|`-bearing paragraph in the file would become a block and
    the cell-count check would start reporting prose as malformed rows.

    The second case is the reason `delimiter > run[0]` is in the code: a
    delimiter with nothing above it inside the same run has no header, so GFM
    builds no table and neither does this.
    """
    assert table_blocks("| a | b |\n| c | d |\n".split("\n")) == []
    assert table_blocks("|---|---|\n| c | d |\n".split("\n")) == []


# --- each declaration is FOUND, before it is compared ---------------------
#
# A pattern that stops matching is the failure this file exists to prevent,
# wearing a different hat: an unmatched declaration is an underived number,
# and `re.search(...) is None` is indistinguishable from `numbers agree` in
# any assertion that guards on the match first.

def test_every_declaration_this_check_verifies_is_actually_FOUND() -> None:
    found = {
        "untriaged total": _UNTRIAGED.search(_declarations()),
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


# --- the residuals, held red-able ----------------------------------------
#
# Same header, same meaning, same position as in
# `test_markdown_tables_render_whole.py`. A residual is a LIMIT held as a
# claim that can go red, so it is not a discrimination test and does not
# belong among them.


def test_an_HTML_BLOCK_opener_is_the_residual_this_scan_does_NOT_see() -> None:
    """The stated limit, held as a claim that can go red.

    MEASURED, BOTH DIRECTIONS: `<div>html</div>` interposed in a table ends it
    for GitHub and the row after comes back as literal text; `<span>x</span>`
    interposed in a table does NOT end it and the row after comes back as a
    `<tr>`. Which one a `<` line is depends on CommonMark's fixed list of ~62
    HTML *block* tag names, so `s.startswith("<")` is not the fix — it would
    end a table at a `<span>` GitHub keeps open and report every row below it
    as stranded, which is a false failure on a live file.

    So the gap is declared rather than closed: `candidates.md` has zero lines
    opening with `<`, and whether a repo-wide gate should carry the block-tag
    list is C-oe0gc9x6's to rule. This test exists so the declaration cannot go
    quietly stale — the same contract as the vocabulary gate's mid-word
    residual, and for the same reason.

    IF THIS GOES RED, NOTHING IS BROKEN: somebody taught `ends_the_table` the
    block-tag list. Delete this test and the limits-list paragraph it holds, in
    the same commit.
    """
    lines = "| A | B |\n|---|---|\n| 1 | 2 |\n<div>x</div>\n| 3 | 4 |\n".split("\n")
    assert 4 in table_blocks(lines)[0], (
        "`ends_the_table` now breaks a table at an HTML-block opener. That is "
        "an improvement, not a failure — but the cell-count check's limits list "
        "still declares it a residual, and `<span>` must keep NOT breaking one. "
        "Update the list and delete this test together."
    )

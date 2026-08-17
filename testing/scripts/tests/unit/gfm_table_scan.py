"""Where a GFM table IS — the scanner both markdown gates ask.

THIS IS A HELPER MODULE, NOT A TEST MODULE, AND THAT IS THE WHOLE POINT. These
four functions were private to `test_candidates_prose_matches_the_table.py`
until a repo-wide gate needed the same boundary. Reaching into a `test_*.py`
for them — statically or by `importlib`— is the exact coupling
`test_test_tree_hygiene.py` forbids: underscore names that say "private to this
file" while being a contract between two files with no declared owner, breaking
at COLLECTION, which `mutate.sh` reads as a caught mutation (issue #72). A
correction pass wrote that coupling by path-loading the sibling, and the
hygiene gate did not see it because its scan reads `ast.Import` nodes and a
path load emits none. The names live here so both callers have a declared owner.

Named for what it scans rather than for either caller, and repo-unique per the
Testing Standard's binding rule on helper module names.

EVERY BOUNDARY BELOW IS MEASURED THROUGH GITHUB'S OWN `POST /markdown`, not
reasoned from CommonMark — the two disagree in both directions here, and the
docstrings record which way each time.
"""

from __future__ import annotations

import re

# --- where a table IS, derived once and asked by both rendering checks -------
#
# THE TWO CHECKS BELOW ASK DIFFERENT QUESTIONS OF THE SAME BOUNDARY, and they
# used to compute it separately — one inline, one not at all. That is the drift
# seam this file's own subject is about, one level down: a second definition of
# "inside a table" is a second thing that can be right on Tuesday.


def ends_the_table(line: str) -> bool:
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

    ORDERED-LIST MARKERS ARE IN THE SET AND `<` IS DELIBERATELY NOT, and both
    halves of that are MEASURED through `POST /markdown` rather than reasoned
    from the spec:

      * `1. text` and `2. text` inside a table both END it — the row after
        each came back inside an `<ol>`/`<ol start="2">` as literal `| 3 | 4 |`
        text, not as a `<tr>`. So ANY ordered-list marker interrupts, not only
        one starting at 1, which is what the paragraph-interruption rule alone
        would have predicted. That is why the pattern is `^\\d+[.)] ` and not
        `^1[.)] `.
      * `<div>html</div>` inside a table ENDS it; `<span>x</span>` inside a
        table DOES NOT — it came back as a `<tr>`. Whether a `<` line closes a
        table depends on CommonMark's fixed list of ~62 HTML *block* tag names,
        and a blanket `s.startswith("<")` would therefore invent a boundary
        GitHub does not draw and report the rows after a `<span>` as stranded.
        That residual is named in the cell-count check's limits list and held
        by `test_an_HTML_BLOCK_opener_is_the_residual_this_scan_does_NOT_see`;
        it is disclosed rather than implemented because `candidates.md` has
        ZERO lines opening with `<` today and the repo-wide question is C-103's
        to rule, not this pass's to guess at.
    """
    s = line.strip()
    return (not s
            or s.startswith(("#", ">", "```", "~~~", "- ", "* ", "+ "))
            or bool(re.match(r"^\d+[.)] ", s))
            or set(s) <= {"-", "*", "_", " "} and len(s) >= 3)


def is_delimiter(line: str) -> bool:
    """The `|---|---|` row, which is what makes a run of lines a TABLE."""
    return (set(line.replace("|", "").replace(" ", "")) <= {"-", ":"}
            and bool(line.replace("|", "").strip()))


def table_blocks(lines: list[str]) -> list[list[int]]:
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
        if not ends_the_table(line):
            run.append(index)
            continue
        delimiter = next((j for j in run if is_delimiter(lines[j])), None)
        if delimiter is not None and delimiter > run[0]:
            blocks.append([j for j in run if j >= delimiter - 1])
        run = []
    return blocks


def cells(line: str) -> int:
    """Cells a GFM renderer sees. `\\|` is an escape and never splits."""
    return len(re.split(r"(?<!\\)\|", line))

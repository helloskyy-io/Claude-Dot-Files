"""Where a GFM table IS, and what is wrong with it — the scanner both gates ask.

THIS IS A HELPER MODULE, NOT A TEST MODULE, AND THAT IS THE WHOLE POINT. These
functions were private to `test_candidates_prose_matches_the_table.py` until a
repo-wide gate needed the same boundary. Reaching into a `test_*.py`
for them — statically or by `importlib`— is the exact coupling
`test_test_tree_hygiene.py` forbids: underscore names that say "private to this
file" while being a contract between two files with no declared owner, breaking
at COLLECTION, which `mutate.sh` reads as a caught mutation (issue #72). A
correction pass wrote that coupling by path-loading the sibling, and the
hygiene gate did not see it because its scan reads `ast.Import` nodes and a
path load emits none. The names live here so both callers have a declared owner.

Named for what it scans rather than for either caller, and repo-unique per the
Testing Standard's binding rule on helper module names.

THE EXTRACTION STOPPED ONE LAYER SHORT FOR ONE REVISION, AND FOUR REVIEW
FINDINGS WERE THAT ONE OMISSION WEARING FOUR HATS. The first version of this
module exported only the four PRIMITIVES below (`ends_the_table`,
`is_delimiter`, `table_blocks`, `cells`) and left the CHECKS built on top of
them — walk the blocks, compare each row against its own header, collect the
offenders — to be re-typed in each caller. Because each caller owned its own
copy, each also independently decided whether to blank fenced code first (the
tree-wide gate did, the file-local one did not, and nothing disclosed the
difference), which primitives to import (the file-local one imported two it
never called), and which vacuity floors to assert (the tree-wide one had no
table-count floor at all, so a scanner that stopped matching tables would have
gone silently green). One incomplete extraction, four symptoms, four separate
findings from three independent reviewers. The DERIVATIONS live here now; each
caller supplies only its own population and its own failure message.

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
    """The `|---|---|` row, which is what makes a run of lines a TABLE.

    EVERY CELL NEEDS AT LEAST ONE HYPHEN, AND CHECKING THE LINE AS A CHARACTER
    SET INSTEAD WAS A SOUNDNESS HOLE IN THE ONE FUNCTION EVERY GATE DERIVES
    FROM. The first version asked whether the whole line, pipes and spaces
    removed, drew only from `{-, :}`. That accepts `|:::|:::|` and `|-|::|`,
    which GFM does not: the extension requires each cell to match `:?-+:?`.
    The consequence ran the WRONG WAY round from the defect this module exists
    to catch — the scanner would fabricate a table block where GitHub renders
    a plain paragraph, and every check derived from `table_blocks` would then
    report off-width rows and stray lines against content that is not a table
    at all. A false RED in a gate whose whole value is that it can be trusted
    when green.

    MEASURED through `POST /markdown`, counting `<tr>` (the opening `<table>`
    carries attributes, so counting `<table>` literally reports zero even on a
    real table — that mis-count sent one earlier probe on this PR chasing a
    finding that did not exist):

      | delimiter row       | renders |
      |---------------------|---------|
      | `\\|---\\|---\\|`      | TABLE   |
      | `\\|:---\\|---:\\|:---:\\|` | TABLE |
      | `\\|-\\|-\\|`          | TABLE   |
      | `---\\|---` (no outer pipes) | TABLE |
      | `\\|:::\\|:::\\|`      | not a table |
      | `\\|-\\|::\\|`         | not a table |
      | `\\| --- \\| \\| --- \\|` (empty cell) | not a table |
      | `\\|- - -\\|---\\|` (spaced dashes) | not a table |

    The outer pipes are OPTIONAL in GFM, which is why the empty leading and
    trailing parts are dropped before the cells are checked rather than being
    required to exist.
    """
    parts = line.split("|")
    if parts and not parts[0].strip():
        parts = parts[1:]
    if parts and not parts[-1].strip():
        parts = parts[:-1]
    return bool(parts) and all(re.fullmatch(r":?-+:?", p.strip()) for p in parts)


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


# --- fenced code, which is not markdown and must not be scanned as it --------
#
# THE FENCE RULES BELOW ARE COMMONMARK'S, NOT A LOOSER APPROXIMATION OF THEM,
# and both tightenings were added after review because the loose version could
# only fail SILENTLY — it blanks live content rather than reporting it:
#
#   * AT MOST THREE SPACES of indent. Four or more is an indented code block,
#     so a ```-looking line inside one is literal text, not a fence opener.
#     `\s*` would have opened a phantom fence there and blanked everything
#     after it until a later false close.
#   * A CLOSING fence carries NO info string — only the marker and trailing
#     whitespace. An opener may carry one (```python). Without that asymmetry a
#     line like ``` example inside a real fence reads as a close, and the TRUE
#     close then re-opens a phantom fence that blanks real markdown behind it.
#
# THE INFO-STRING RULE IS PER-MARKER, which a review pass caught: CommonMark
# forbids a backtick in the info string of a BACKTICK fence only, because that
# is what would make the opener ambiguous with inline code. A `~~~` fence may
# carry one. A single `[^`]*` for both would leave a tilde fence with a
# backtick in its info string UNRECOGNISED and therefore UNBLANKED — content
# inside it scanned as live markdown, which is a false positive by
# construction. Zero tracked files open a `~~~` fence today; the rule is
# written correctly anyway because getting it wrong is invisible until it is
# not.
_FENCE_OPEN = re.compile(r"^ {0,3}(?:(`{3,})([^`]*)|(~{3,})(.*))$")
_FENCE_CLOSE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")


def blank_fenced(lines: list[str]) -> list[str]:
    """Fenced-code lines replaced by blanks, with line INDICES preserved.

    Blanked rather than removed so a reported line number still points at the
    line a human will open. A blank also terminates a table block, which is
    what GFM does at a fence anyway.

    The closing fence must be at least as long as the opener and of the same
    character, which is CommonMark's rule and is what lets a ```` ```` ````
    block contain a ``` line.

    BOTH CALLERS USE THIS NOW, AND FOR ONE REVISION ONLY ONE DID. The tree-wide
    gate blanked fences and the file-local one did not, so the two gates over
    the same file (`candidates.md` is in both populations) would have disagreed
    about a fenced example — and nothing said so. That asymmetry was
    undisclosed rather than decided, which is the failure mode this whole
    module is about one level down.

    WHAT THIS DOES NOT LOOK AT: fence indentation is measured from the start of
    the physical line, not from the enclosing container's content column. A
    fence nested inside a list item can legitimately sit at four or more
    absolute spaces and still be a fence rather than an indented code block;
    this reads it as the latter and leaves it unblanked. Held by
    `test_a_CONTAINER_INDENTED_FENCE_is_the_residual_this_scan_does_NOT_see`.
    Container tracking is a block parser, which is a different program from
    this one.
    """
    out: list[str] = []
    fence: str | None = None
    for line in lines:
        if fence is None:
            opener = _FENCE_OPEN.match(line)
            if opener:
                fence = opener.group(1) or opener.group(3)
                out.append("")
                continue
            out.append(line)
            continue
        closer = _FENCE_CLOSE.match(line)
        if closer and closer.group(1)[0] == fence[0] and len(closer.group(1)) >= len(fence):
            fence = None
        out.append("")
    return out


# --- the three questions asked of a block, derived ONCE ----------------------
#
# EACH RETURNS LINE INDICES AND NOTHING ELSE. Formatting a `path:line` label,
# quoting the offending text, and choosing the failure message all belong to
# the caller — that is the whole difference between two gates sharing a
# derivation and two gates sharing an opinion.


def off_width_rows(lines: list[str]) -> list[tuple[int, int, int]]:
    """`(index, actual, expected)` per row that misses its own header's count.

    This is the original defect: GFM splits a row on `|` before it parses
    inline content, so a pipe inside an inline code span is a cell break. Every
    cell past the header's count is DROPPED and the last survivor is CUT at the
    offending pipe — silently, keeping the left-hand cells, so anything derived
    from an id or a status stays green while the evidence on the right is gone.

    Rows that do not open with `|` are skipped here because they are a
    different defect with a different remedy — `stray_lines` owns that shape.
    """
    wrong: list[tuple[int, int, int]] = []
    for block in table_blocks(lines):
        expected = cells(lines[block[0]])
        for i in block:
            if not lines[i].lstrip().startswith("|"):
                continue
            if cells(lines[i]) != expected:
                wrong.append((i, cells(lines[i]), expected))
    return wrong


def stray_lines(lines: list[str]) -> list[int]:
    """Non-row lines sitting INSIDE a table block, which render DETACHED.

    A non-`|` line inside a table does not become prose and is not absorbed by
    its neighbour — it renders as its own `<tr>` with the whole paragraph in
    the first column, while the row above it is CUT. Measured on C-050 through
    `POST /markdown`: a 1,981-character tail on its own line came back as a
    seventh `<tr>`, and C-050's own Note lost 1,956 characters.
    """
    return [
        i
        for block in table_blocks(lines)
        for i in block
        if lines[i].strip() and not lines[i].lstrip().startswith("|")
    ]


def stranded_rows(lines: list[str]) -> list[int]:
    """`|`-opening lines that NO block claims — the complement of the two above.

    `off_width_rows` and `stray_lines` both only ever look INSIDE a block, so
    neither can see a row that has fallen OUT of one. MEASURED: inserting a
    `- ` list line into `candidates.md` § Two flags left the entire suite green
    while `POST /markdown` swallowed the row after it into the `<li>`, losing
    every cell. `table_blocks` ends the block at the `- `, so the row below is
    outside every block and both checks above are structurally unable to reach
    it.

    IT IS A FLOOR, NOT A PARSE. It cannot say WHY a line fell out — a
    block-level opener above it, a deleted delimiter, a stray blank — only that
    it did, which is enough to make somebody look.

    THIS IS THE STRICT BAR AND IT IS NOT THE RIGHT ONE EVERYWHERE. In a curated
    table file every `|`-opening line ought to be a row. In ordinary prose a
    lone `|`-line is usually a deliberate ROW-SHAPE ILLUSTRATION under a
    heading and nothing is wrong with it. `severed_rows` below is the bar for
    that population; this one is for callers that can assert the stricter
    property.
    """
    claimed = {i for block in table_blocks(lines) for i in block}
    return [
        i for i, line in enumerate(lines)
        if line.lstrip().startswith("|") and i not in claimed
    ]


def severed_rows(lines: list[str]) -> list[int]:
    """Stranded rows that were TORN OFF A TABLE, not written standalone.

    THE DISCRIMINATING PROPERTY IS ADJACENCY ACROSS A BLANK-FREE RUN. A row
    severed from its table is still in the same paragraph-level run of non-blank
    lines as the table it belonged to — the severing line (a list marker, a
    heading, a blockquote) interrupts the block without ending the run. A
    row-shape illustration is not: it sits in its own run, separated from
    everything else by blank lines.

    MEASURED ON THE TREE, and this is why the port of `stranded_rows` is not a
    copy-paste. Three `|`-opening lines sit outside every block today —
    `research_refresh/prompts/altitude_product.md:56`,
    `research_write/prompts/altitude_product.md:56` and
    `review_pr/prompts/disposition.md:262` — and NONE is a defect. All three are
    single isolated row-shape illustrations with no delimiter anywhere in their
    run, so GFM never rendered them as rows and nothing is lost. Applying the
    strict bar tree-wide would fail the gate on three correct files, and a gate
    that cries wolf on correct content is one people turn off.

    WHAT THIS DOES NOT LOOK AT: a row separated from its table by a BLANK line.
    That row is structurally identical to a deliberate illustration — same
    shape, same isolation, and GFM treats both the same way — so no scanner can
    tell them apart, and guessing would reintroduce exactly the false positives
    this bar exists to avoid. Held by
    `test_a_BLANK_SEPARATED_ROW_is_the_residual_this_gate_does_NOT_see`.
    """
    claimed = {i for block in table_blocks(lines) for i in block}
    stranded = set(stranded_rows(lines))
    if not stranded:
        return []

    severed: list[int] = []
    start: int | None = None
    for i in range(len(lines) + 1):
        if i < len(lines) and lines[i].strip():
            if start is None:
                start = i
            continue
        if start is not None:
            run = range(start, i)
            if any(j in claimed for j in run):
                severed.extend(j for j in run if j in stranded)
            start = None
    return sorted(severed)

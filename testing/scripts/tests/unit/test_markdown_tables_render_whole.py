"""Every markdown table in the repo renders WHOLE, not just in one file.

WHY THIS IS TREE-WIDE AND ITS SIBLING IS NOT. The cell-count check in
`test_candidates_prose_matches_the_table.py` was built for `candidates.md`
because that is where the defect was first measured. The DEFECT is not
file-shaped. GitHub-flavoured markdown splits a table row on `|` before it
parses inline content, so a pipe inside an inline code span — a regex
alternation, a shell pipeline, a `true|false` enumeration — is a cell break.
GFM then DROPS every cell past the header's count and CUTS the last survivor at
the offending pipe. Nothing errors, nothing warns, and the row keeps its
left-hand cells, so anything derived from an id or a status stays green while
the evidence on the right-hand side is gone.

MEASURED ACROSS ONE PULL REQUEST: SIX INSTANCES, IN THREE FILES, FOUND ONLY BY
LOOKING. PR #96 repaired four inside the one file it was already editing —
C-101 lost 2158 of 2769 characters, C-093 lost 2818 of 3561, C-062 lost its
adjudication, and C-050 lost 1956 to a stray line — and then a repo-wide sweep
found two more that nothing was gating: `memory-management-framework/
roadmap.md:269` returned 203 of 452 rendered characters and
`phase4_fleet_migration.md:69` returned 248 of 400. Four passes of review
closed instances one at a time; the sixth was still live when the fifth was
declared fixed. That is the evidence for gating the CLASS rather than the file.

WHAT THIS GATE DOES NOT LOOK AT, stated because a limits list that is only
prose is a claim nobody checks — each item below is held by a test in this
module so it fails loudly if it ever stops being true:

  * A MALFORMED HEADER. This counts cells, so a header with the right number
    of columns and the wrong names passes, and so does a body row whose cells
    are correctly counted and shifted one column left. Held by
    `test_a_SHIFTED_ROW_is_the_residual_this_gate_does_NOT_see`.
  * AN HTML BLOCK OPENER inside a table. `_ends_the_table` tests no `<`, and
    that is deliberate — measured through `POST /markdown`, `<div>` ends a
    table for GitHub and `<span>` does not, so a blanket test would invent
    failures. Tree-wide this scan would OVER-extend a block past a `<div>` and
    read rows GitHub renders as literal text as though they were members.
    Measured today: ZERO tracked `.md` files have a `<`-opening line inside a
    table block, so the residual is real and unexercised. Held by
    `test_an_HTML_BLOCK_opener_is_the_residual_TREE_WIDE_TOO`.
  * ANYTHING THAT IS NOT A CELL COUNT — an unbalanced backtick, a broken
    link, a cell whose content is malformed without changing how many cells
    there are.
  * FILES GIT DOES NOT TRACK, and files that are not `.md`.

VENDORED MIRRORS ARE IN THE POPULATION ON PURPOSE, AND THAT HAS A COST WORTH
NAMING. `docs/standards/{documentation,research,testing,temporal}/` are
verbatim copies that MUST NOT be edited here. If this gate ever goes red on one
of them the fix is UPSTREAM followed by a re-vendor, NOT a local edit — do not
resolve it by touching the mirror, and do not resolve it by carving the mirror
out of this scan. Measured today: 11 vendored files, 10 of them carrying
tables, all clean.

FENCED CODE BLOCKS ARE EXCLUDED BECAUSE GFM DOES NOT RENDER THEM AS TABLES AT
ALL, which makes any finding inside one a false positive by construction. That
is measured, not reasoned: a three-cell row against a two-column header inside
a ``` fence came back from `POST /markdown` as a `<pre><code>` block with ZERO
`<table>` elements. Two such tables exist in the tree today —
`config/skills/documentation-structure.md:692` and
`memory-management-framework/roadmap.md:222` — and both happen to be internally
consistent, so this exclusion is not what makes the gate green. It is what
stops a documentation example from failing it later.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]

# The GFM scanner is IMPORTED rather than reimplemented. Two definitions of
# "inside a table" is precisely the drift seam this module's subject is about,
# and the sibling's copy is the one with the measured HTML-block and
# ordered-list boundaries written into it. Loaded by path rather than by module
# name so it resolves identically under pytest and under a bare interpreter.
_SIBLING = Path(__file__).with_name("test_candidates_prose_matches_the_table.py")


def _load_sibling():
    spec = importlib.util.spec_from_file_location("_candidates_table_gate", _SIBLING)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_candidates_table_gate"] = module
    spec.loader.exec_module(module)
    return module


_GFM = _load_sibling()

_FENCE = re.compile(r"^\s*(```+|~~~+)")


def _tracked_markdown() -> list[Path]:
    """Every `.md` file git tracks, which is the population this gate claims."""
    out = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=_REPO, capture_output=True, text=True, check=True,
    ).stdout.split()
    return [_REPO / name for name in out]


def _blank_fenced(lines: list[str]) -> list[str]:
    """Fenced-code lines replaced by blanks, with line INDICES preserved.

    Blanked rather than removed so a reported line number still points at the
    line a human will open. A blank also terminates a table block, which is
    what GFM does at a fence anyway.

    The closing fence must be at least as long as the opener and of the same
    character, which is CommonMark's rule and is what lets a ```` ```` ```` ````
    block contain a ``` line.
    """
    out: list[str] = []
    fence: str | None = None
    for line in lines:
        match = _FENCE.match(line)
        if fence is None:
            if match:
                fence = match.group(1)
                out.append("")
                continue
            out.append(line)
            continue
        closing = match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence)
        if closing:
            fence = None
        out.append("")
    return out


def _display(path: Path) -> str:
    """Repo-relative where possible, absolute otherwise.

    A `tmp_path` fixture is not under `_REPO`, and `relative_to` RAISES rather
    than falling back. Without this the fixture-driven tests below could not
    call `_off_width_rows` itself and would have to reimplement its loop — which
    would leave the real predicate untested by the very tests written to prove
    it discriminates.
    """
    try:
        return str(path.relative_to(_REPO))
    except ValueError:
        return str(path)


def _off_width_rows(path: Path) -> list[str]:
    """Rows in `path` that do not split into their own table header's count."""
    lines = _blank_fenced(path.read_text(encoding="utf-8", errors="replace").split("\n"))
    wrong: list[str] = []
    for block in _GFM._table_blocks(lines):
        expected = _GFM._cells(lines[block[0]])
        for i in block:
            line = lines[i]
            if not line.lstrip().startswith("|"):
                continue  # a stray line inside a block is the sibling's shape
            if _GFM._cells(line) != expected:
                wrong.append(
                    f"{_display(path)}:{i + 1} "
                    f"({_GFM._cells(line)} fields, expected {expected})"
                )
    return wrong


# --- vacuity floor -------------------------------------------------------

def test_the_SHARED_TABLE_SCANNER_is_the_one_this_gate_reads() -> None:
    """If the sibling is renamed, this gate must fail rather than vanish."""
    assert _SIBLING.exists(), (
        f"{_SIBLING.name} is where the GFM table scanner lives and this gate "
        "imports it by path. If it moved, repoint this import — do NOT write a "
        "second copy of `_table_blocks`, which is the drift this gate exists to "
        "catch in prose."
    )
    for name in ("_table_blocks", "_cells", "_ends_the_table", "_is_delimiter"):
        assert hasattr(_GFM, name), f"the shared scanner no longer exports {name}"


def test_there_are_enough_markdown_files_for_this_gate_to_mean_anything() -> None:
    """A population that silently collapsed to nothing passes everything."""
    files = _tracked_markdown()
    assert len(files) > 100, (
        f"only {len(files)} tracked `.md` files found — this gate claims to "
        "cover the tree and was measured over 228. A collapse this large means "
        "`git ls-files` ran somewhere unexpected, not that the docs were deleted."
    )
    assert all(p.exists() for p in files)


# --- the class gate ------------------------------------------------------

def test_EVERY_TABLE_ROW_IN_EVERY_TRACKED_MARKDOWN_FILE_RENDERS_WHOLE() -> None:
    """The class the sibling check gates in one file, gated everywhere.

    THIS IS THE CHECK THAT MAKES THE NEXT INSTANCE FAIL INSTEAD OF BEING FOUND.
    Six instances were closed one at a time across four review passes of a
    single PR, in three different files; enumerating them did not converge and
    the sixth was live when the fifth was declared fixed.
    """
    wrong: list[str] = []
    for path in _tracked_markdown():
        wrong.extend(_off_width_rows(path))

    assert not wrong, (
        "these table rows do not split into their own header's field count, so "
        "GitHub drops the surplus cells and truncates the last one that "
        "survives — which is the right-hand side of the row, where the evidence "
        "is: " + "; ".join(wrong) + ". Escape the pipe as `\\|`. It is honoured "
        "inside an inline code span, so a regex alternation or a shell pipeline "
        "stays readable. Do NOT resolve this by deleting the evidence, and if "
        "the file is a vendored mirror under `docs/standards/`, fix it upstream "
        "and re-vendor rather than editing the copy."
    )


# --- the gate discriminates ----------------------------------------------

def test_AN_UNESCAPED_PIPE_IS_ACTUALLY_CAUGHT(tmp_path: Path) -> None:
    """A green sweep proves nothing unless the predicate can go red.

    Both rows below are the shape measured live: a pipe inside an inline code
    span. The escaped one must pass and the bare one must fail, because a gate
    that flags both would be un-satisfiable and one that flags neither is
    decoration.
    """
    good = tmp_path / "good.md"
    good.write_text("| a | b |\n|---|---|\n| `x \\| y` | z |\n", encoding="utf-8")

    bad = tmp_path / "bad.md"
    bad.write_text("| a | b |\n|---|---|\n| `x | y` | z |\n", encoding="utf-8")

    # `_off_width_rows` ITSELF is called here, not a copy of its loop. An
    # earlier draft of this test reimplemented the loop, which meant gutting the
    # real predicate left this test green — the exact shape it exists to catch.
    assert _off_width_rows(good) == [], "an escaped pipe must not be reported"
    assert len(_off_width_rows(bad)) == 1, (
        "an unescaped pipe inside a code span must be reported"
    )


def test_A_TABLE_INSIDE_A_FENCED_CODE_BLOCK_IS_NOT_GATED(tmp_path: Path) -> None:
    """GFM renders no table inside a fence, so a finding there is a false one.

    MEASURED through `POST /markdown`: the exact content below came back as a
    `<pre><code>` block with ZERO `<table>` elements. Without this exclusion the
    gate would fail on a documentation example that renders perfectly.
    """
    doc = tmp_path / "fenced.md"
    doc.write_text(
        "Example:\n\n```\n| a | b |\n|---|---|\n| x | y | z |\n```\n\nDone.\n",
        encoding="utf-8",
    )
    lines = _blank_fenced(doc.read_text(encoding="utf-8").split("\n"))
    assert _GFM._table_blocks(lines) == [], (
        "a table inside a fenced code block was picked up as a live table; GFM "
        "renders it as literal text, so every row it reports is a false failure"
    )


def test_a_LONGER_FENCE_CAN_CONTAIN_A_SHORTER_ONE(tmp_path: Path) -> None:
    """CommonMark's fence rule, held so `_blank_fenced` cannot silently regress.

    A ```` ```` ```` opener is closed only by a fence at least as long, so the
    inner ``` line does NOT reopen live content. Getting this wrong would let
    the tail of a nested example escape the exclusion above.
    """
    doc = tmp_path / "nested.md"
    doc.write_text(
        "````\n```\n| a | b |\n|---|---|\n| x | y | z |\n```\n````\n",
        encoding="utf-8",
    )
    lines = _blank_fenced(doc.read_text(encoding="utf-8").split("\n"))
    assert lines == [""] * 7 + [""], f"nested fence not fully blanked: {lines}"


# --- the residuals, held red-able ----------------------------------------

def test_a_SHIFTED_ROW_is_the_residual_this_gate_does_NOT_see(tmp_path: Path) -> None:
    """A cell count is not a rendering check, and this is where that bites.

    IF THIS TEST EVER GOES RED NOTHING IS BROKEN — it means the gate grew
    stronger than its limits list claims. Delete this test and the matching
    bullet in the module docstring together, so the two cannot disagree.
    """
    doc = tmp_path / "shifted.md"
    doc.write_text("| a | b | c |\n|---|---|---|\n|  | a-value | b-value |\n", encoding="utf-8")
    lines = _blank_fenced(doc.read_text(encoding="utf-8").split("\n"))
    wrong = [
        i for block in _GFM._table_blocks(lines)
        for i in block
        if lines[i].lstrip().startswith("|")
        and _GFM._cells(lines[i]) != _GFM._cells(lines[block[0]])
    ]
    assert wrong == [], (
        "a row whose cells are correctly COUNTED and shifted one column left is "
        "now caught; the docstring says it is not"
    )


def test_an_HTML_BLOCK_opener_is_the_residual_TREE_WIDE_TOO() -> None:
    """`<div>` ends a table for GitHub and this scan keeps it open.

    The consequence tree-wide is OVER-extension: rows after a `<div>` are read
    as members of the block while GitHub renders them as literal text. It is
    disclosed rather than implemented because `<span>` does NOT end a table, so
    a blanket `<` test would invent failures GitHub does not have.

    The second assertion is what keeps this honest — the residual is currently
    UNEXERCISED, and if a `<`-opening line ever lands inside a table block the
    count below moves and this test says so.
    """
    doc = ["| a | b |", "|---|---|", "| x | y |", "<div>html</div>", "| p | q |"]
    blocks = _GFM._table_blocks(doc)
    assert blocks and len(blocks[0]) == 5, (
        "the scan now stops at an HTML block opener; if that is deliberate, "
        "delete this test and the matching docstring bullet together"
    )

    live = [
        f"{p.relative_to(_REPO)}:{i + 1}"
        for p in _tracked_markdown()
        for lines in [_blank_fenced(p.read_text(encoding="utf-8", errors="replace").split("\n"))]
        for block in _GFM._table_blocks(lines)
        for i in block
        if lines[i].lstrip().startswith("<")
    ]
    assert live == [], (
        "a `<`-opening line now sits inside a table block, which is exactly the "
        "case this gate over-extends past — the rows after it may not be "
        "rendering at all: " + "; ".join(live)
    )

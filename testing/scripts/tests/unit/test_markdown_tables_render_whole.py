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
  * AN HTML BLOCK OPENER inside a table. `ends_the_table` tests no `<`, and
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
NAMING — BUT ONLY SIX FILES CARRY IT, NOT THE WHOLE DIRECTORY. An earlier
revision of this paragraph said `docs/standards/{documentation,research,
testing,temporal}/` were all verbatim copies, which is WRONG and would have
misdirected a contributor: `scripts/helpers/vendor-standards.sh` copies exactly
six files — `documentation_standard.md`, `research_standard.md`,
`testing_standard.md`, `temporal_standard.md`, `stateful_patterns.md`,
`worker_deployment_standard.md`. The four `README.md` applicability notes and
`temporal/claude-dot-files-addendum.md` in those same directories are LOCAL and
editable here, and each says so of itself.

So: if this gate goes red on one of the six, the fix is UPSTREAM followed by a
re-vendor, and neither editing the mirror nor carving it out of this scan is
the answer. If it goes red on a README or the addendum, fix it in place like
any other file. The six are read off `vendor-standards.sh` rather than restated
here, held by `test_the_VENDORED_SET_is_read_off_the_script_that_defines_it`,
because a hard-coded list is exactly the hand-kept declaration this repo's
gates exist to catch.

WHAT THIS GATE DOES NOT COVER THAT ITS SIBLING DOES — nothing. The stray-line
shape (a paragraph tail split onto its own line inside a table, which renders
as a DETACHED row and steals its neighbour's evidence — C-050 lost 1,956
characters that way) is gated here tree-wide too, by
`test_EVERY_LINE_INSIDE_EVERY_TABLE_BLOCK_IS_ACTUALLY_A_ROW`. It was left out
of the first revision of this module on the reasoning that it was "the
sibling's shape", which was wrong: the sibling's copy reads `candidates.md`
alone, so tree-wide the shape was ungated by both.

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

import re
import subprocess
from pathlib import Path

from gfm_table_scan import cells, table_blocks

_REPO = Path(__file__).resolve().parents[4]

# THE FENCE RULE IS COMMONMARK'S, NOT A LOOSER APPROXIMATION OF IT, and both
# tightenings below were added after review because the loose version could
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
_FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})([^`]*)$")
_FENCE_CLOSE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")


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
    block contain a ``` line. See `_FENCE_OPEN` / `_FENCE_CLOSE` above for the
    two further rules — indent depth and info strings — and for why a loose
    version of either fails silently rather than loudly.
    """
    out: list[str] = []
    fence: str | None = None
    for line in lines:
        if fence is None:
            opener = _FENCE_OPEN.match(line)
            if opener:
                fence = opener.group(1)
                out.append("")
                continue
            out.append(line)
            continue
        closer = _FENCE_CLOSE.match(line)
        if closer and closer.group(1)[0] == fence[0] and len(closer.group(1)) >= len(fence):
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
    for block in table_blocks(lines):
        expected = cells(lines[block[0]])
        for i in block:
            line = lines[i]
            if not line.lstrip().startswith("|"):
                continue  # the stray-line check below owns this shape
            if cells(line) != expected:
                wrong.append(
                    f"{_display(path)}:{i + 1} "
                    f"({cells(line)} fields, expected {expected})"
                )
    return wrong


# --- vacuity floor -------------------------------------------------------

def test_the_SHARED_TABLE_SCANNER_IS_NOT_A_TEST_MODULE() -> None:
    """The scanner has a DECLARED OWNER, and that is not a style preference.

    A first draft of this gate reached the four scanning functions by
    `importlib`-loading its sibling `test_candidates_prose_matches_the_table.py`
    by path. That is the coupling `test_test_tree_hygiene.py` forbids — private
    names as a contract between two files with no owner, breaking at COLLECTION,
    which `mutate.sh` reads as a caught mutation (issue #72) — and the hygiene
    gate did NOT catch it, because its scan reads `ast.Import` nodes and a path
    load emits none. Both were fixed together: the names moved to
    `gfm_table_scan.py`, and the hygiene gate now sees dynamic loads too.

    So this test asserts the SHAPE of the dependency, not merely that it
    resolves — if the scanner ever moves back inside a `test_*.py`, this fails
    here rather than being rediscovered by a review pass.
    """
    import gfm_table_scan

    owner = Path(gfm_table_scan.__file__)
    assert not owner.name.startswith("test_"), (
        f"the GFM scanner now lives in {owner.name}, which pytest COLLECTS. "
        "Move it back to a non-`test_`-prefixed helper module — a test module "
        "is not an importable surface."
    )
    for name in ("table_blocks", "cells", "ends_the_table", "is_delimiter"):
        assert hasattr(gfm_table_scan, name), (
            f"the shared scanner no longer exports {name}; repoint the import "
            "rather than writing a second copy, which is the drift this gate "
            "exists to catch in prose"
        )


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


def test_EVERY_LINE_INSIDE_EVERY_TABLE_BLOCK_IS_ACTUALLY_A_ROW() -> None:
    """The OTHER half of the class, which the first revision of this file missed.

    A non-`|` line inside a table does not become prose and is not absorbed by
    its neighbour — it renders as its own DETACHED `<tr>` with the whole
    paragraph in the first column, while the row above it is CUT. Measured on
    C-050 through `POST /markdown`: a 1,981-character tail on its own line came
    back as a seventh `<tr>`, and C-050's own Note lost 1,956 characters.

    THE SIBLING GATES THIS FOR ONE FILE ONLY. `test_EVERY_LINE_INSIDE_A_TABLE_
    BLOCK_IS_ACTUALLY_A_ROW` in `test_candidates_prose_matches_the_table.py`
    reads `candidates.md` and nothing else, so leaving this out "because it is
    the sibling's shape" left it ungated everywhere else — the same
    file-shaped reasoning this module exists to correct. Measured across all
    tracked `.md` today: zero.
    """
    stray: list[str] = []
    for path in _tracked_markdown():
        lines = _blank_fenced(path.read_text(encoding="utf-8", errors="replace").split("\n"))
        for block in table_blocks(lines):
            for i in block:
                if lines[i].strip() and not lines[i].lstrip().startswith("|"):
                    stray.append(f"{_display(path)}:{i + 1}")

    assert not stray, (
        "these lines sit INSIDE a table block without being rows, so GitHub "
        "renders each as a detached row that takes its neighbour's evidence "
        "with it: " + "; ".join(stray) + ". Join the line back onto the cell it "
        "belongs to, or put a blank line before it so the table ends first. Do "
        "NOT resolve this by deleting the text."
    )


def test_the_VENDORED_SET_is_read_off_the_script_that_defines_it() -> None:
    """This module's docstring names six mirrors; the script is the authority.

    The docstring tells a contributor whose fix goes upstream and whose is
    local, and a review pass caught an earlier revision claiming the whole of
    `docs/standards/{documentation,research,testing,temporal}/` was vendored —
    11 files rather than the 6 that actually are. A wrong answer there stalls a
    legitimate local fix against a source that has no counterpart for it.
    """
    script = _REPO / "scripts" / "helpers" / "vendor-standards.sh"
    assert script.is_file(), f"{script} is where the vendored set is declared"

    declared = re.findall(r'^\s*"[^"]+:([^"]+)"', script.read_text(encoding="utf-8"), re.M)
    names = sorted(Path(d).name for d in declared)
    assert names == sorted([
        "documentation_standard.md", "research_standard.md",
        "stateful_patterns.md", "temporal_standard.md",
        "testing_standard.md", "worker_deployment_standard.md",
    ]), (
        f"the vendored set changed to {names}. Update this module's docstring "
        "paragraph on which files route upstream — a contributor reads it to "
        "decide where a fix goes."
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
    assert table_blocks(lines) == [], (
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
    # `_off_width_rows` ITSELF, for the same reason the discrimination test
    # above calls it: a residual test that reimplements the predicate stops
    # describing the predicate the moment either one moves.
    assert _off_width_rows(doc) == [], (
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

    COMPANION: `test_an_HTML_BLOCK_opener_is_the_residual_this_scan_does_NOT_see`
    in `test_candidates_prose_matches_the_table.py` holds the same residual for
    that file. Both are claims about `ends_the_table`, which they now share, so
    teaching it CommonMark's block-tag list retires BOTH tests and BOTH
    docstring bullets — delete them in one commit or the surviving one starts
    describing a residual that no longer exists.
    """
    doc = ["| a | b |", "|---|---|", "| x | y |", "<div>html</div>", "| p | q |"]
    blocks = table_blocks(doc)
    assert blocks and len(blocks[0]) == 5, (
        "the scan now stops at an HTML block opener; if that is deliberate, "
        "delete this test and the matching docstring bullet together"
    )

    live = [
        f"{p.relative_to(_REPO)}:{i + 1}"
        for p in _tracked_markdown()
        for lines in [_blank_fenced(p.read_text(encoding="utf-8", errors="replace").split("\n"))]
        for block in table_blocks(lines)
        for i in block
        if lines[i].lstrip().startswith("<")
    ]
    assert live == [], (
        "a `<`-opening line now sits inside a table block, which is exactly the "
        "case this gate over-extends past — the rows after it may not be "
        "rendering at all: " + "; ".join(live)
    )

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
C-npx1uwgj lost 2158 of 2769 characters, C-2asq6d9x lost 2818 of 3561, C-8rhxo6st lost its
adjudication, and C-523klr8n lost 1956 to a stray line — and then a repo-wide sweep
found two more that nothing was gating: `memory-management-framework/
roadmap.md:269` returned 203 of 452 rendered characters and
`phase4_fleet_migration.md:69` returned 248 of 400. Four passes of review
closed instances one at a time; the sixth was still live when the fifth was
declared fixed. That is the evidence for gating the CLASS rather than the file.

THE THREE SHAPES ARE THREE CHECKS BECAUSE THEY ARE THREE REMEDIES. A row that
does not split into its header's count is fixed by escaping a pipe; a non-row
line inside a block is fixed by joining it back onto the cell it fell off; a
row severed from its block is fixed by moving whatever interrupted the table.
All three are derived in `gfm_table_scan.py` and asked here of every tracked
`.md`.

WHAT THIS GATE DOES NOT LOOK AT, stated because a limits list that is only
prose is a claim nobody checks — each item below is held by a test in this
module so it fails loudly if it ever stops being true:

  * A MALFORMED HEADER. This counts cells, so a header with the right number
    of columns and the wrong names passes, and so does a body row whose cells
    are correctly counted and shifted one column left. Held by
    `test_a_SHIFTED_ROW_is_the_residual_this_gate_does_NOT_see`.
  * A ROW SEPARATED FROM ITS TABLE BY A BLANK LINE. The severed-row check
    below keys on adjacency across a blank-free run, because that is the only
    property that tells a torn-off row apart from a deliberate one-line
    ROW-SHAPE ILLUSTRATION — and three correct files in this tree contain the
    latter. Put a blank line between a table and a row that belonged to it and
    nothing here can still tell which it was. Held by
    `test_a_BLANK_SEPARATED_ROW_is_the_residual_this_gate_does_NOT_see`.
  * AN HTML BLOCK OPENER inside a table. `ends_the_table` tests no `<`, and
    that is deliberate — measured through `POST /markdown`, `<div>` ends a
    table for GitHub and `<span>` does not, so a blanket test would invent
    failures. Tree-wide this scan would OVER-extend a block past a `<div>` and
    read rows GitHub renders as literal text as though they were members.
    Measured today: ZERO tracked `.md` files have a `<`-opening line inside a
    table block, so the residual is real and unexercised. Held by
    `test_an_HTML_BLOCK_opener_is_the_residual_TREE_WIDE_TOO`.
  * A FENCE INDENTED TO ITS CONTAINER rather than to the page. `blank_fenced`
    measures the ≤3-space rule from the start of the physical line, so a fence
    nested inside a list item at four or more absolute spaces is read as an
    indented code block and left unblanked. Held by
    `test_a_CONTAINER_INDENTED_FENCE_is_the_residual_this_gate_does_NOT_see`.
  * ANYTHING THAT IS NOT A CELL COUNT OR A BLOCK BOUNDARY — an unbalanced
    backtick, a broken link, a cell whose content is malformed without
    changing how many cells there are.
  * FILES GIT DOES NOT TRACK, and files that are not `.md`.

VENDORED MIRRORS ARE IN THE POPULATION ON PURPOSE, AND THAT HAS A COST WORTH
NAMING — BUT ONLY SEVEN FILES CARRY IT, NOT THE WHOLE DIRECTORY. An earlier
revision of this paragraph said `docs/standards/{documentation,research,
testing,temporal}/` were all verbatim copies, which is WRONG and would have
misdirected a contributor: `scripts/helpers/vendor-standards.sh` copies exactly
seven files — `documentation_standard.md`, `tracked_items_standard.md`,
`research_standard.md`, `testing_standard.md`, `temporal_standard.md`,
`stateful_patterns.md`, `worker_deployment_standard.md`. The four `README.md` applicability notes and
`temporal/claude-dot-files-addendum.md` in those same directories are LOCAL and
editable here, and each says so of itself.

So: if this gate goes red on one of the six, the fix is UPSTREAM followed by a
re-vendor, and neither editing the mirror nor carving it out of this scan is
the answer. If it goes red on a README or the addendum, fix it in place like
any other file. The six are read off `vendor-standards.sh` rather than restated
here, held by `test_the_VENDORED_SET_is_read_off_the_script_that_defines_it`,
because a hard-coded list is exactly the hand-kept declaration this repo's
gates exist to catch.

WHAT THIS GATE DOES NOT COVER THAT ITS SIBLING DOES — one thing, deliberately,
and this paragraph SAID "nothing" FOR ONE REVISION WHILE THAT WAS FALSE. The
sibling asserts `test_EVERY_PIPE_OPENING_LINE_SITS_INSIDE_A_TABLE_BLOCK`: in
`candidates.md`, a curated table file, EVERY `|`-opening line must be a row.
That bar is correct there and wrong here — three tracked files carry a
deliberate one-line row-shape illustration under a heading, which is not a
defect and which the strict bar would fail. This module asserts the weaker,
tree-safe half of the same property via `severed_rows`. The gap is one bar, not
one shape, and the shape itself IS gated here.

The false "nothing" claim is worth recording rather than quietly deleting,
because the paragraph diagnosed its own error one shape over while making it:
the stray-line check was left out of the first revision of this module on the
reasoning that it was "the sibling's shape", which was wrong for the same
reason — the sibling reads `candidates.md` alone, so tree-wide the shape was
ungated by both. That reasoning was then repeated verbatim for the stranded
shape, one revision later, by the paragraph correcting it.

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

from vendored_standards import EXPECTED, VENDOR_SCRIPT, vendored_paths

from gfm_table_scan import (
    blank_fenced,
    off_width_rows,
    severed_rows,
    stray_lines,
    table_blocks,
)

_REPO = Path(__file__).resolve().parents[4]


def _tracked_markdown() -> list[Path]:
    """Every `.md` file git tracks, which is the population this gate claims."""
    out = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=_REPO, capture_output=True, text=True, check=True,
    ).stdout.split()
    return [_REPO / name for name in out]


def _display(path: Path) -> str:
    """Repo-relative where possible, absolute otherwise.

    A `tmp_path` fixture is not under `_REPO`, and `relative_to` RAISES rather
    than falling back. Without this the fixture-driven tests below could not
    call the real predicates and would have to reimplement their loops — which
    would leave the real predicate untested by the very tests written to prove
    it discriminates.
    """
    try:
        return str(path.relative_to(_REPO))
    except ValueError:
        return str(path)


def _scan(path: Path) -> list[str]:
    """The file's lines, fenced code blanked, ready for any shared check.

    ONE READ AND ONE BLANKING PER FILE, asked by three checks. Each check used
    to re-read and re-blank, which is not merely wasteful: it is three places
    that can disagree about what "the file" means.
    """
    return blank_fenced(path.read_text(encoding="utf-8", errors="replace").split("\n"))


def _off_width(path: Path) -> list[str]:
    """Rows in `path` that do not split into their own table header's count."""
    return [
        f"{_display(path)}:{i + 1} ({actual} fields, expected {expected})"
        for i, actual, expected in off_width_rows(_scan(path))
    ]


# --- vacuity floors ------------------------------------------------------

def test_there_are_enough_markdown_files_for_this_gate_to_mean_anything() -> None:
    """A population that silently collapsed to nothing passes everything."""
    files = _tracked_markdown()
    assert len(files) > 100, (
        f"only {len(files)} tracked `.md` files found — this gate claims to "
        "cover the tree and was measured over 228. A collapse this large means "
        "`git ls-files` ran somewhere unexpected, not that the docs were deleted."
    )
    assert all(p.exists() for p in files)


def test_the_TREE_WIDE_SCAN_finds_the_tables_that_are_actually_there() -> None:
    """A file count is not a table count, and only the second one floors this gate.

    THE FILE FLOOR ABOVE WAS THE ONLY ONE FOR ONE REVISION, AND IT CANNOT SEE
    THE FAILURE THAT MATTERS. Every check in this module is derived from
    `table_blocks`. If that ever stopped matching real tables — a change to
    `is_delimiter` or `ends_the_table`, over-broad fence blanking, an encoding
    regression — all 228 files would still be found and every check would go
    permanently, silently green having examined ZERO tables. That is precisely
    the "nothing errors, nothing warns" shape this whole module exists to
    catch, reproduced inside its own harness.

    The sibling has had this floor since its own scan was widened and states
    the rationale in the same words; the tree-wide module simply did not copy
    it. Measured today: 449 blocks over 3,476 lines in 228 files.
    """
    blocks = lines = 0
    for path in _tracked_markdown():
        found = table_blocks(_scan(path))
        blocks += len(found)
        lines += sum(len(b) for b in found)

    assert blocks > 200, (
        f"the tree-wide scan found {blocks} tables across every tracked `.md`, "
        "and 449 were measured. All three checks below are derived from this "
        "scan, so a collapse here turns all three green against nothing."
    )
    assert lines > 1500, (
        f"the scan reached only {lines} lines across {blocks} tables — the "
        "blocks are being truncated, and every line it did not reach is a line "
        "none of the three checks below is looking at."
    )


# --- the dependency's SHAPE, which is not a vacuity floor ----------------
#
# THIS SAT UNDER THE VACUITY HEADER FOR ONE REVISION. A vacuity floor asserts
# the population is non-empty; this asserts the scanner lives somewhere pytest
# does not collect and still exports what both gates import. Different
# question, different failure, its own section.

def test_the_SHARED_TABLE_SCANNER_IS_NOT_A_TEST_MODULE() -> None:
    """The scanner has a DECLARED OWNER, and that is not a style preference.

    A first draft of this gate reached the scanning functions by
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
    for name in (
        "table_blocks", "cells", "ends_the_table", "is_delimiter",
        "blank_fenced", "off_width_rows", "stray_lines", "stranded_rows",
        "severed_rows",
    ):
        assert hasattr(gfm_table_scan, name), (
            f"the shared scanner no longer exports {name}; repoint the import "
            "rather than writing a second copy, which is the drift this gate "
            "exists to catch in prose"
        )


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
        wrong.extend(_off_width(path))

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
    """The second half of the class, which the first revision of this file missed.

    A non-`|` line inside a table does not become prose and is not absorbed by
    its neighbour — it renders as its own DETACHED `<tr>` with the whole
    paragraph in the first column, while the row above it is CUT. Measured on
    C-523klr8n through `POST /markdown`: a 1,981-character tail on its own line came
    back as a seventh `<tr>`, and C-523klr8n's own Note lost 1,956 characters.

    THE SIBLING GATES THIS FOR ONE FILE ONLY, so leaving it out "because it is
    the sibling's shape" left it ungated everywhere else — the same
    file-shaped reasoning this module exists to correct. Measured across all
    tracked `.md` today: zero.
    """
    stray: list[str] = []
    for path in _tracked_markdown():
        stray.extend(f"{_display(path)}:{i + 1}" for i in stray_lines(_scan(path)))

    assert not stray, (
        "these lines sit INSIDE a table block without being rows, so GitHub "
        "renders each as a detached row that takes its neighbour's evidence "
        "with it: " + "; ".join(stray) + ". Join the line back onto the cell it "
        "belongs to, or put a blank line before it so the table ends first. Do "
        "NOT resolve this by deleting the text."
    )


def test_NO_TABLE_ROW_ANYWHERE_IN_THE_TREE_IS_SEVERED_FROM_ITS_BLOCK() -> None:
    """The third half, and the one the two checks above are structurally blind to.

    BOTH CHECKS ABOVE ONLY EVER LOOK INSIDE A BLOCK. A row that has fallen OUT
    of one is invisible to both by construction, and the consequence is total
    rather than partial: GFM renders every cell of a severed row as literal
    text, so the whole row is lost rather than truncated.

    MEASURED ON THIS TREE, not argued. Inserting `- a stray list line` into the
    class table in `docs/standards/finding-routing.md` left BOTH markdown gate
    modules fully green — 39 tests, no failures — while `POST /markdown`
    returned the `PROPOSAL`, `RULING` and `OPERATING STATE` rows swallowed into
    an `<li>` as literal text. One list marker, three rows of a binding
    standard's own routing table gone, nothing red. The same measurement one
    pass earlier on `candidates.md` § Two flags — the three-column table that
    declares who may write `decision`, `status` and `component` — produced
    `2093 passed, 0 failed`.

    WHY THIS USES THE WEAKER BAR. The sibling asserts that every `|`-opening
    line in `candidates.md` sits inside a block, which is right for a curated
    table file and wrong for a tree containing prose: three files carry a
    deliberate one-line row-shape illustration under a heading, and the strict
    bar fails all three. `severed_rows` keys on adjacency across a blank-free
    run instead, which is the property that actually separates a torn-off row
    from a written-standalone one. See its docstring for the residual that
    costs.
    """
    severed: list[str] = []
    for path in _tracked_markdown():
        severed.extend(f"{_display(path)}:{i + 1}" for i in severed_rows(_scan(path)))

    assert not severed, (
        "these lines open with `|` and sit OUTSIDE every table block while "
        "still touching one, so something interrupted the table and GitHub now "
        "renders them as literal text — every cell they carry is lost, not "
        "merely truncated: " + "; ".join(severed) + ". Find the line above them "
        "that ended the table — a list marker, a heading, a blockquote, an HTML "
        "block, or a delimiter row that stopped being one — and move it out of "
        "the table. Do NOT resolve this by deleting the rows."
    )


def test_the_VENDORED_SET_is_read_off_the_script_that_defines_it() -> None:
    """This module's docstring names six mirrors; the script is the authority.

    The docstring tells a contributor whose fix goes upstream and whose is
    local, and a review pass caught an earlier revision claiming the whole of
    `docs/standards/{documentation,research,testing,temporal}/` was vendored —
    11 files rather than the 6 that actually are. A wrong answer there stalls a
    legitimate local fix against a source that has no counterpart for it.

    The derivation itself moved to `vendored_standards.py` once a third gate
    needed it. This assertion stays here rather than moving with it, because
    what a wrong set COSTS differs per gate and the message should say so.
    """
    assert VENDOR_SCRIPT.is_file(), (
        f"{VENDOR_SCRIPT} is where the vendored set is declared")

    names = sorted(p.name for p in vendored_paths())
    assert names == sorted(EXPECTED), (
        f"the vendored set changed to {names}. Update "
        "`vendored_standards.EXPECTED` and this module's docstring paragraph "
        "on which files route upstream — a contributor reads it to decide "
        "where a fix goes."
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

    # The REAL predicate is called here, not a copy of its loop. An earlier
    # draft of this test reimplemented the loop, which meant gutting the real
    # function left this test green — the exact shape it exists to catch.
    assert _off_width(good) == [], "an escaped pipe must not be reported"
    assert len(_off_width(bad)) == 1, (
        "an unescaped pipe inside a code span must be reported"
    )


def test_A_STRAY_LINE_INSIDE_A_TABLE_IS_ACTUALLY_CAUGHT(tmp_path: Path) -> None:
    """The one shape whose predicate could be DELETED with the suite still green.

    FOUND BY MUTATING THIS PASS'S OWN WORK, WHICH IS THE ONLY WAY IT COULD HAVE
    BEEN FOUND. `stray_lines` is asked by both gate modules, and both only ever
    assert that it returns NOTHING — which it does today, because the tree has
    zero instances. Replacing its whole body with `return []` left all 46 tests
    across both modules PASSING. The other six predicates in `gfm_table_scan.py`
    were each caught by at least one test when gutted; this one was decoration,
    and it was decoration guarding the exact defect that cost C-523klr8n 1,956
    characters of evidence.

    A guard proven only against content that does not contain the defect is not
    proven at all. The fixture is the measured C-523klr8n shape: a `Note` tail split
    onto its own line inside the table.
    """
    doc = tmp_path / "stray.md"
    doc.write_text(
        "| a | b |\n|---|---|\n| 1 | 2 |\nthe tail of a cell, split onto its own line\n| 3 | 4 |\n",
        encoding="utf-8",
    )
    assert [i + 1 for i in stray_lines(_scan(doc))] == [4], (
        "a non-row line inside a table block must be reported — GFM renders it "
        "as a detached row and CUTS the row above it"
    )

    clean = tmp_path / "clean.md"
    clean.write_text("| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n", encoding="utf-8")
    assert stray_lines(_scan(clean)) == [], (
        "a well-formed table must not be reported; a check that flags both is "
        "un-satisfiable and one that flags neither is decoration"
    )


def test_A_SEVERED_ROW_IS_CAUGHT_AND_AN_ILLUSTRATION_IS_NOT(tmp_path: Path) -> None:
    """The discrimination the tree-wide bar exists to make, both directions.

    THIS IS THE TEST THAT WOULD HAVE FAILED BEFORE THIS CHECK EXISTED, and the
    second half is why the check is not a copy of the sibling's. The severed
    fixture is the exact shape measured on `finding-routing.md`; the
    illustration fixture is the exact shape of the three tracked files that
    carry one. A bar that catches the first and spares the second is the only
    one that can run tree-wide.
    """
    severed = tmp_path / "severed.md"
    severed.write_text(
        "| a | b |\n|---|---|\n| 1 | 2 |\n- a stray list line\n| 3 | 4 |\n",
        encoding="utf-8",
    )
    illustration = tmp_path / "illustration.md"
    illustration.write_text(
        "### Row shape\n\n| ID | Recommendation | `status` |\n\nUse that shape.\n",
        encoding="utf-8",
    )

    assert [i + 1 for i in severed_rows(_scan(severed))] == [5], (
        "a row torn off its table by a list marker must be reported — every "
        "cell it carries renders as literal text"
    )
    assert severed_rows(_scan(illustration)) == [], (
        "a standalone row-shape illustration under a heading is not a defect; "
        "reporting it would fail three correct files in this tree"
    )


def test_A_DELIMITER_ROW_WITHOUT_A_HYPHEN_IS_NOT_A_TABLE(tmp_path: Path) -> None:
    """`is_delimiter`'s soundness, in the direction that produces FALSE REDS.

    Every other check here fails when the tree is wrong. This one fails when
    the SCANNER is wrong, and the failure runs the other way: a delimiter
    predicate that is too permissive fabricates a table block where GitHub
    renders a plain paragraph, and then every derived check reports off-width
    rows and stray lines against content that is not a table at all.

    Both shapes below were MEASURED through `POST /markdown` and returned zero
    `<tr>` elements; the valid one returned two. See `is_delimiter`'s docstring
    for the full measured table.
    """
    for name, delimiter in (("colons", "|:::|:::|"), ("one_bad_cell", "|-|::|")):
        doc = tmp_path / f"{name}.md"
        doc.write_text(f"| a | b |\n{delimiter}\n| 1 | 2 | 3 |\n", encoding="utf-8")
        assert table_blocks(_scan(doc)) == [], (
            f"`{delimiter}` was accepted as a delimiter row, so this scan built "
            "a table GitHub does not render. The three-cell row below it would "
            "be reported as off-width against a header that is not a header — "
            "a false RED in a gate whose value is being trustworthy when green."
        )

    doc = tmp_path / "valid.md"
    doc.write_text("| a | b |\n|:---|---:|\n| 1 | 2 |\n", encoding="utf-8")
    assert len(table_blocks(_scan(doc))) == 1, (
        "an alignment-marked delimiter row is valid GFM and must still parse"
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
    assert table_blocks(_scan(doc)) == [], (
        "a table inside a fenced code block was picked up as a live table; GFM "
        "renders it as literal text, so every row it reports is a false failure"
    )


def test_a_LONGER_FENCE_CAN_CONTAIN_A_SHORTER_ONE(tmp_path: Path) -> None:
    """CommonMark's fence rule, held so `blank_fenced` cannot silently regress.

    A ```` ```` ```` opener is closed only by a fence at least as long, so the
    inner ``` line does NOT reopen live content. Getting this wrong would let
    the tail of a nested example escape the exclusion above.
    """
    doc = tmp_path / "nested.md"
    doc.write_text(
        "````\n```\n| a | b |\n|---|---|\n| x | y | z |\n```\n````\n",
        encoding="utf-8",
    )
    assert _scan(doc) == [""] * 8, f"nested fence not fully blanked: {_scan(doc)}"


def test_a_TILDE_FENCE_MAY_CARRY_A_BACKTICK_IN_ITS_INFO_STRING(tmp_path: Path) -> None:
    """CommonMark's info-string rule is per-marker, and reading it as universal
    leaves live content UNBLANKED.

    A backtick is forbidden in the info string of a BACKTICK fence only, because
    that is what would make the opener ambiguous with inline code. A single
    ``[^`]*`` for both markers fails to recognise the opener below, leaves the
    fenced table scanned as live markdown, and reports a documentation example
    as a defect. Zero tracked files open a `~~~` fence today; the rule is
    written correctly anyway because getting it wrong is invisible until it is
    not.
    """
    doc = tmp_path / "tilde.md"
    doc.write_text(
        "~~~ text with a ` backtick\n| a | b |\n|---|---|\n| x | y | z |\n~~~\n",
        encoding="utf-8",
    )
    assert table_blocks(_scan(doc)) == [], (
        "a `~~~` fence whose info string contains a backtick was not "
        "recognised, so its contents were scanned as live markdown"
    )


# --- the residuals, held red-able ----------------------------------------

def test_a_SHIFTED_ROW_is_the_residual_this_gate_does_NOT_see(tmp_path: Path) -> None:
    """A cell count is not a rendering check, and this is where that bites.

    IF THIS TEST EVER GOES RED NOTHING IS BROKEN — it means the gate grew
    stronger than its limits list claims. Delete this test and the matching
    bullet in the module docstring together, so the two cannot disagree.
    """
    doc = tmp_path / "shifted.md"
    doc.write_text("| a | b | c |\n|---|---|---|\n|  | a-value | b-value |\n", encoding="utf-8")
    # The REAL predicate, for the same reason the discrimination tests call it:
    # a residual test that reimplements the predicate stops describing the
    # predicate the moment either one moves.
    assert _off_width(doc) == [], (
        "a row whose cells are correctly COUNTED and shifted one column left is "
        "now caught; the docstring says it is not"
    )


def test_a_BLANK_SEPARATED_ROW_is_the_residual_this_gate_does_NOT_see(tmp_path: Path) -> None:
    """A blank line makes a torn-off row indistinguishable from a written one.

    This is the price of running tree-wide. `severed_rows` keys on adjacency
    across a blank-free run because that is the only property separating a row
    torn off a table from a deliberate row-shape illustration — and once a
    blank line sits between the table and the row, the two shapes are
    IDENTICAL. No scanner can tell them apart, and guessing would fail three
    correct files in this tree.

    IF THIS TEST EVER GOES RED NOTHING IS BROKEN — it means the gate found a
    property this one does not have. Delete this test and the matching bullet
    in the module docstring together, so the two cannot disagree.
    """
    doc = tmp_path / "blank-separated.md"
    doc.write_text("| a | b |\n|---|---|\n| 1 | 2 |\n\n| 3 | 4 |\n", encoding="utf-8")
    assert severed_rows(_scan(doc)) == [], (
        "a row separated from its table by a blank line is now reported; the "
        "docstring says this gate cannot tell it from an illustration"
    )


def test_a_CONTAINER_INDENTED_FENCE_is_the_residual_this_gate_does_NOT_see(
    tmp_path: Path,
) -> None:
    """Fence indent is measured from the page, not from the enclosing container.

    CommonMark's ≤3-space rule is relative to the container's content column,
    so a fence nested inside a list item can sit at four or more ABSOLUTE
    spaces and still be a fence. `blank_fenced` reads that as an indented code
    block and leaves it unblanked, so a table inside it is scanned as live
    markdown. Container tracking is a block parser, which is a different
    program from this one.

    IF THIS TEST EVER GOES RED NOTHING IS BROKEN — it means `blank_fenced`
    learned about containers. Delete this test and the matching bullet in the
    module docstring together, so the two cannot disagree.
    """
    doc = tmp_path / "container-fence.md"
    doc.write_text(
        "- an item\n\n    ```\n    | a | b |\n    |---|---|\n    | x | y | z |\n    ```\n",
        encoding="utf-8",
    )
    assert table_blocks(_scan(doc)) != [], (
        "a container-indented fence is now blanked; the docstring says this "
        "gate reads it as an indented code block and scans it as live markdown"
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
        f"{_display(p)}:{i + 1}"
        for p in _tracked_markdown()
        for lines in [_scan(p)]
        for block in table_blocks(lines)
        for i in block
        if lines[i].lstrip().startswith("<")
    ]
    assert live == [], (
        "a `<`-opening line now sits inside a table block, which is exactly the "
        "case this gate over-extends past — the rows after it may not be "
        "rendering at all: " + "; ".join(live)
    )

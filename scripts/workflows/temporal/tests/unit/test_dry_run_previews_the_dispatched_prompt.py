"""A `--dry-run` must preview the prompt the live run dispatches, not a copy of it.

THE CLASS, AND WHY IT IS CHECKED STRUCTURALLY RATHER THAN PER RUNNER. A runner's
`--dry-run` branch and its workflow's `run_*` function both have to fill the same
prompt placeholders. Whenever the runner assembles its own dict, the two drift —
silently, because a preview that is wrong looks exactly like a preview that is
right, and the artifact an operator checked is not the artifact a model received.

**This family has shipped that bug.** `plan_sprint_workflow.correction_note`'s
docstring records a dry run rendering only half of `CORRECTION_NOTE` and
previewing text no model would ever see. It was fixed by patching the runner's
copy, which closed the instance and left the shape — and the shape is what
reproduces. Two of three runners still carried a hand-built dict afterwards, and
a third was written with one.

So the check keys on the SHAPE: no runner may pass a dict literal to `render`.
A new runner that copies the pattern fails here on the day it is written, rather
than on the day somebody adds a placeholder to one side of the pair.

WHAT THIS DOES NOT PROVE. It cannot show the two dicts hold equal VALUES — the
live path needs a worktree, a repo and a model. It proves there is only one dict,
which is the property that makes equality unnecessary.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

_RUNNERS = sorted((Path(__file__).resolve().parents[2] / "scripts").glob("run_*.py"))


def test_the_sweep_finds_the_runners() -> None:
    """VACUITY FLOOR. An assertion over an empty set is indistinguishable from
    full coverage, and this suite has already been bitten by exactly that."""
    assert len(_RUNNERS) >= 8, f"the runner sweep found only {[p.name for p in _RUNNERS]}"


def _render_calls(tree: ast.AST) -> list[ast.Call]:
    """Every `render(...)` call, however the module spells the qualifier."""
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and (getattr(n.func, "attr", None) == "render"
                 or getattr(n.func, "id", None) == "render")]


@pytest.mark.parametrize("runner", _RUNNERS, ids=lambda p: p.name)
def test_a_runner_never_hand_ASSEMBLES_the_prompt_values(runner: Path) -> None:
    """The values a runner renders must come from a CALL, never a literal.

    A call is the workflow's own assembly — `wf.prompt_values(...)` in all three
    runners that render today. A `{...}` here is a second copy of a dict that
    already exists, and the copy is what drifts.
    """
    for call in _render_calls(ast.parse(runner.read_text())):
        if len(call.args) < 2:
            continue
        values = call.args[1]
        assert not isinstance(values, ast.Dict), (
            f"{runner.name} line {values.lineno} builds its own prompt values "
            f"dict. Call the workflow's `prompt_values(...)` instead — a dry run "
            f"that assembles its own copy previews a prompt that is not the one "
            f"dispatched, which this family has already shipped once.")


@pytest.mark.parametrize("runner", _RUNNERS, ids=lambda p: p.name)
def test_a_runner_that_renders_calls_a_workflow_level_ASSEMBLER(runner: Path) -> None:
    """And the call it makes must be the workflow's, not a local helper.

    A module-local `_values()` in the runner satisfies the check above while
    being the same second copy one indirection down — the shape this whole file
    exists to keep out. Asserted by qualifier: the callee must be an attribute of
    something imported, which is how every runner names its workflow module.
    """
    for call in _render_calls(ast.parse(runner.read_text())):
        if len(call.args) < 2:
            continue
        values = call.args[1]
        if not isinstance(values, ast.Call):
            continue
        assert isinstance(values.func, ast.Attribute), (
            f"{runner.name} line {values.lineno} fills the prompt from a "
            f"module-local call. The assembler must live with the workflow that "
            f"dispatches the prompt, so both paths reach the same one.")


def _byte_labelled_prints(tree: ast.AST) -> list[ast.FormattedValue]:
    """Every `{...}` interpolation in an f-string whose own text says "bytes"."""
    out: list[ast.FormattedValue] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.JoinedStr):
            continue
        literal = "".join(v.value for v in node.values if isinstance(v, ast.Constant))
        if "bytes" not in literal:
            continue
        out.extend(v for v in node.values if isinstance(v, ast.FormattedValue))
    return out


@pytest.mark.parametrize("runner", _RUNNERS, ids=lambda p: p.name)
def test_a_figure_a_runner_LABELS_bytes_is_measured_in_bytes(runner: Path) -> None:
    """CLASS: A DRY RUN MAY NOT PRINT A CHARACTER COUNT UNDER A `bytes` LABEL.

    THE SAME SEAM AS THE REST OF THIS MODULE, one column over. Everything above
    asserts the previewed prompt is the dispatched one; this asserts the FIGURE
    printed beside it is the one the gate measures. A preview whose text is right
    and whose number is wrong is the same failure — an operator checked an
    artifact and concluded something false about it.

    THE TWO UNITS ARE NOT INTERCHANGEABLE AND THE GAP IS NOT SMALL. The budget
    gate, `testing/scripts/tests/unit/test_prompt_budgets.py`, measures
    `path.stat().st_size` — bytes on disk. `len(str)` counts CODE POINTS. The
    house style is dense in em-dashes and arrows, each three bytes and one code
    point, so on this fleet's prompts the two differ by hundreds. An operator
    comparing a dry run against a budget on a prompt near its ceiling reads
    headroom that does not exist, and the budget raise that follows is priced
    against the wrong number.

    FOUR RUNNERS SHIPPED THE CHARACTER COUNT while a fifth had already been fixed
    with a comment explaining why — which is precisely the state a per-instance
    fix leaves behind, and precisely what this parametrized sweep replaces.

    WHAT THIS DOES NOT LOOK AT:

      * It does not check the figure is the PROMPT's. A runner printing
        `len(other.encode())` under a bytes label passes; the unit is the
        property, not the subject.
      * It does not reach a figure built outside an f-string, or one assigned to
        a variable first (`size = len(rendered)` then `f"{size} bytes"`). The
        label and the expression have to be in the same literal for this to see
        them, which is how all ten runners spell it today.
      * It says nothing about any other unit. `{n} turns`, `{n} rows` and the
        rest are unconstrained.
    """
    for interp in _byte_labelled_prints(ast.parse(runner.read_text())):
        expr = ast.unparse(interp.value)
        assert ".encode()" in expr or "st_size" in expr, (
            f"{runner.name} line {interp.lineno} prints `{expr}` under a `bytes` "
            f"label. `len(str)` counts code points, and the budget gate measures "
            f"`path.stat().st_size` — on this fleet's em-dash-dense prompts the "
            f"two differ by hundreds, so an operator reads headroom that is not "
            f"there. Use `len(rendered.encode())`.")


# A DRY RUN THAT COUNTS SOMETHING MUST SAY WHICH TREE IT COUNTED.
#
# `prompt_values`' own docstring rules the prompt half: *"THE DRY RUN AND THE
# REAL RUN MUST RENDER THE SAME PROMPT"*, and the tests above hold it by proving
# one values dict serves both callers. The COUNTS half was never held, and the
# identical dict rendered against two different trees passes every one of them.
#
# The two trees are real and they diverge exactly where it costs most. A dry run
# cuts no worktree, so it reads the invocation checkout; a `--pr` run cuts its
# worktree from `origin/<the PR's branch>`. On a correction pass the work being
# corrected is on the branch and need NOT be in the checkout at all, so the
# preview reports `0` phase docs and `roadmap.md ABSENT` for a plan that is fully
# written — the same wrong conclusion PR #130 measured, relocated out of a loud
# refusal and into a confident-looking preview.
#
# THIS ASSERTS THE NAMING, NOT THE SAMENESS, AND THAT IS THE RULING RATHER THAN A
# WEAKER VERSION OF IT. Issue #134 offered two remedies; the operator ruled the
# smaller one on 2026-08-24 on measured evidence — `--dry-run` appears ZERO times
# in the operator's shell history, is documented in no guide, skill or command,
# and all 32 uses in the run logs are dispatches verifying these runners while
# building them. Asserting the trees are the SAME would fail by construction here,
# because the ruling deliberately leaves them different and labelled. When real
# operator use appears, the stronger remedy earns itself and this assertion is
# what gets tightened.
_COUNTED_IN = "Counted in :"


def _counts_a_tree(source: str) -> bool:
    """Is there a `len(...)` here that measures something other than bytes?

    BALANCED PARENS, NOT A REGEX, AND THAT IS NOT STYLE. It was a regex whose
    argument class was `[^()]*` for one revision, and that class cannot
    cross a nested call — so it silently stopped seeing
    `len(own.phase_docs(component))`, the very figure that made
    `run_plan_draft.py` a case in the first place. The regex was written to
    ADD the two research runners and it dropped a member while doing it, which
    is the same class-closure failure this module's subject is about: a key that
    cannot express something it is meant to cover.

    A dry run's byte figures — `len(rendered.encode())`, `len(context.encode())`
    — measure a string this process just built, not a tree, and owe no
    attribution. Everything else does.

    `.splitlines()` joins `.encode()` under that same sentence rather than as a
    second special case: both measure an operator-supplied string this process
    holds in memory, and neither can misattribute a tree because neither reads
    one. The instance is `run_plan_revision.py`'s live banner, which truncates a
    `--task-file` body to its first line and says so — a count that is not in the
    dry run at all. Giving that runner a `Counted in :` line to satisfy the
    detector would have it name a tree it never counts, which is the misstatement
    this guard exists to prevent, produced by the guard.
    """
    i = source.find("len(")
    while i != -1:
        depth, j = 0, i + 3
        while j < len(source):
            if source[j] == "(":
                depth += 1
            elif source[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        arg = source[i:j]
        if ".encode()" not in arg and ".splitlines()" not in arg:
            return True
        i = source.find("len(", j)
    return False


def _dry_run_counts_something(source: str) -> bool:
    """Does this runner's dry run print a figure read off a tree?

    KEYED ON THE SHAPE OF A COUNT, NOT ON NAMES. The first version of this
    listed the interpolations it had seen — `len(own.`, `sizing.`, `counts[`,
    `phase_docs` — and skipped `run_research.py` and `run_research_minor.py`,
    which print `len(due)` off a local pool directory and accept `--pr` like
    every runner here. Issue #134 flagged those two as *"may be the same shape —
    not verified here"*, and a detector keyed on names cannot verify it: the key
    could not express a member it was meant to cover.

    A runner that previews only static facts — turns, grants, the byte size of a
    prompt it just rendered — has no tree to misattribute and owes no line.
    `_counts_a_tree` above carries the byte exclusion and the reason for it.
    """
    if "DRY RUN" not in source:
        return False
    return _counts_a_tree(source) or "sizing." in source or "counts[" in source


@pytest.mark.parametrize("runner", _RUNNERS, ids=lambda p: p.name)
def test_a_dry_run_that_COUNTS_names_the_TREE_it_counted_in(runner: Path) -> None:
    source = runner.read_text()
    if not _dry_run_counts_something(source):
        pytest.skip("this runner's dry run prints no tree-derived figure")
    assert _COUNTED_IN in source, (
        f"{runner.name}'s dry run prints a figure read off a tree and never says "
        f"WHICH tree. On a `--pr` pass that figure describes the invocation "
        f"checkout while the run reads `origin/<branch>`, so a fully-written plan "
        f"previews as `0`. Print the line `run_plan_refine.py` ships, immediately "
        f"after the banner and BEFORE the first figure — a qualifier that arrives "
        f"after the numbers is read after the conclusion.")


def test_the_TREE_NAMING_SWEEP_can_see_a_runner_that_counts() -> None:
    """Vacuity floor. If `_dry_run_counts_something` stopped matching, every case
    above would skip and the module would report green over an unheld property —
    which is the same shape as the defect it guards."""
    counting = [r.name for r in _RUNNERS if _dry_run_counts_something(r.read_text())]
    assert len(counting) >= 3, (
        f"the tree-naming sweep found only {counting} — either the runners stopped "
        f"counting in their dry runs, or the detector stopped recognising a count "
        f"and every case is skipping silently.")


def test_the_byte_label_sweep_can_actually_SEE_a_figure() -> None:
    """VACUITY FLOOR for the check above, and it is the likelier failure.

    The reader keys on the word `bytes` appearing in an f-string's own literal
    text. Reword the line to `size in bytes:` on a separate print, or hand the
    figure through a variable, and every assertion above passes over an empty
    set — indistinguishable from a green run. This asserts the reader still
    finds the figures it was written against.
    """
    found = {r.name: len(_byte_labelled_prints(ast.parse(r.read_text())))
             for r in _RUNNERS}
    total = sum(found.values())
    assert total >= 5, (
        f"the byte-label reader found {total} interpolations across {len(_RUNNERS)} "
        f"runners, and there were five when it was written: {found}. Either the "
        f"dry-run lines were reworded or the reader broke — fix the reader, do "
        f"not delete this test.")

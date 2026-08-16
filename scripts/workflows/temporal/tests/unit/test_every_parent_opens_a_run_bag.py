"""Requirement 11 — a run that does not open a bag goes RED, not journal-less.

WHY A SWEEP AND NOT A PLACEMENT. Putting bag-open in the activities layer
delivers tidiness, not a guarantee: nothing in an orchestrator forces a workflow
to invoke a particular activity first, and a workflow that omits the call simply
omits it. As a library each entrypoint is asked to remember to call, the
protocol is OPTIONAL — and optional is how three controls in this fleet have
already failed. An observable shipped with no reader. A rule governing three
event types stated inside one function's docstring. A completion gate one runner
had and another did not. Each was correct as written, each was skippable, and
each was skipped.

Requirement 9's refuse-to-start cannot supply it either, and the reason is worth
stating because it reads like it should: **r9 fires only once bag-open has
ALREADY been invoked.** An entrypoint that never calls it never reaches r9. Two
guards, two failures, neither substituting for the other.

THE SHAPE IS `test_every_entrypoint_actually_calls_preflight`, which this repo
already ships one directory over and which was written for the same class of
defect — six of seven entrypoints having dropped a precondition. That test's
discovery predicate is reused deliberately rather than re-derived: two sweeps
disagreeing about what an entrypoint IS would leave a file each thought the
other covered.

WHY THE SWEPT UNIT IS THE ENTRYPOINT AND NOT THE WORKFLOW MODULE. This tree has
two defensible readings of "parent" and they do not agree: `test_isolation_
invariants.py` classifies six workflow modules as parents by `act.worktree_add(`,
while ELEVEN entrypoints are 1:1 with a run. Six of those eleven call
`worktree_add` themselves and hand the workflow module an already-cut worktree,
so a bag opened inside the workflow module would fire AFTER a worktree existed
on disk in more than half the fleet — and r9 says the run *does not start*. The
entrypoint is where `preflight` already lives, for exactly this reason. At port
time the entrypoint becomes a client that starts the workflow on a task queue,
and the call moves to the workflow's first activity invocation; this predicate
moves with it.

⚠ WHAT THIS DOES NOT COVER, stated here AND in the failure message because an
enumerating test is only as good as its discovery predicate:

  * A run initiated from outside `scripts/workflows/temporal/scripts/run_*.py`
    is invisible to this sweep. That is the swept scope and it is named in the
    failure text so a reader hitting it learns the boundary rather than assuming
    there is none.
  * It says nothing about whether any individual write is EMITTED. An entrypoint
    that opens a bag and then writes to a store through a path nobody wrapped
    still produces a gap; Phase 4's rebuild test is the guard for that class.
  * It does not reach model-issued writes at all. When the child itself runs
    `gh pr comment` there is no fleet call site to wrap, and that half is
    Phase 3's post-exit harvest.
  * A source grep proves the CALL IS WRITTEN, not that it EXECUTES. A call
    placed inside an unreachable branch would pass. `test_the_call_precedes_the
    _first_side_effect` below closes the most likely version of that by ORDER;
    proving execution needs the integration tier.
  * `--dry-run` IS A DELIBERATE EXEMPTION, and it is the concrete instance of the
    point above rather than a hypothetical one: eight entrypoints return from
    their dry-run branch before reaching bag-open, so on that path the call is
    present and does not run. That is intended — a dry run states "nothing
    invoked, nothing posted", and creating a directory would falsify it and
    litter the journal with empty bags from previews. No run happens on that
    path, so no run lacks a bag. Stated here because every other boundary of
    this guard is stated, and an unstated exemption is the one a later reader
    mistakes for an oversight.
  * The ORDERING check covers eight of eleven; the three it cannot reach are
    named in `_ORDERING_UNCOVERED` below, with why.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
ENTRYPOINTS_DIR = REPO_ROOT / "scripts" / "workflows" / "temporal" / "scripts"

# The call every entrypoint must make, and the module alias it is made through.
BAG_OPEN = "open_run_bag"

# Side-effecting calls an entrypoint can make directly. `worktree_add` cuts a
# directory on disk; a function imported from a `*_workflow` module and called by
# NAME is the handoff to a workflow that will. Bag-open must precede whichever an
# entrypoint reaches first, because r9 means *the run does not start*, not *the
# run stops early*.
_SIDE_EFFECT_ATTRS = ("worktree_add",)

# ⚠ THE ORDERING CHECK'S REAL COVERAGE IS 8 OF 11, AND STATING THE NUMBER IS THE
# POINT. The first version of this file listed `worktree_add` alone, which made
# the assertion bite on only the five entrypoints that cut their own worktree —
# the other six had no detectable side effect, so `opens and effects` was False
# and the check silently passed without examining anything. That is a guard whose
# comment claimed more than its code did.
#
# Adding the by-name workflow handoff takes it to eight. The remaining three —
# `run_research.py`, `run_research_minor.py`, `run_review_pr.py` — reach their
# workflow through an ALIASED MODULE (`rr.`, `rm.`, `wf.`), and those same
# aliases also carry pure prompt-assembly functions that legitimately run before
# the bag is opened, so treating any call on them as a side effect would produce
# false failures. Those three are covered by the presence sweep and by review,
# not by this ordering check. Named here rather than left as a silent zero.
_ORDERING_UNCOVERED = ("run_research.py", "run_research_minor.py", "run_review_pr.py")


def _side_effect_lines(tree: ast.AST) -> list[int]:
    """Line numbers of calls that create something, in one entrypoint.

    Two shapes, because this fleet has two. An attribute call to a name in
    `_SIDE_EFFECT_ATTRS` (`act.worktree_add(...)`), and a direct call to a
    function imported by name out of a `*_workflow` module (`run_build(...)`),
    which is the handoff to a workflow that cuts its own worktree.
    """
    workflow_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and \
                node.module.startswith("modules.assistant"):
            for alias in node.names:
                if node.module.endswith("_workflow") or alias.name.endswith("_workflow"):
                    workflow_names.add(alias.asname or alias.name)

    lines = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if getattr(func, "attr", None) in _SIDE_EFFECT_ATTRS:
            lines.append(node.lineno)
        elif isinstance(func, ast.Name) and func.id in workflow_names:
            lines.append(node.lineno)
    return lines


def _entrypoints(directory: Path) -> list[Path]:
    """Every kickoff entrypoint, discovered rather than listed.

    Discovered for the same reason the preflight sweep is: a new entrypoint is
    covered the day it lands. A hand-maintained list is a net whose coverage
    depends on somebody remembering to add a line, which is not a net — measured
    in this repo when the isolation list covered 3 of 10 children.
    """
    return sorted(p for p in directory.glob("run_*.py") if "__pycache__" not in p.parts)


def _modules_imported_by(paths: list[Path]) -> set[str]:
    """Every module name actually IMPORTED by the given files, by AST.

    Both import shapes, and the dotted tail of each: `import a.b.c` contributes
    `a`, `a.b` and `c`; `from a.b import c as d` contributes `a`, `a.b` and `c`.
    The bare tail is what callers compare a module's `stem` against.
    """
    names: set[str] = set()
    for path in paths:
        for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.update(alias.name.split("."))
                    names.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names.update(node.module.split("."))
                    names.add(node.module)
                for alias in node.names:
                    names.add(alias.name)
    return names


def _missing_bag_open(directory: Path) -> list[str]:
    """Entrypoints under `directory` that never call `open_run_bag`.

    READ BY AST, NOT BY SUBSTRING, and the sibling sweep in `test_preflight.py`
    is why: its first version was a substring check, and a mutation that put the
    forbidden block back stayed GREEN because a COMMENT mentioning the helper
    satisfied the grep. A guard reading a region that includes its own
    documentation reports on the documentation — silently. This file's comments
    name `open_run_bag` repeatedly, so a substring check here would be that bug
    reintroduced knowingly.
    """
    missing = []
    for path in _entrypoints(directory):
        tree = ast.parse(path.read_text(), filename=str(path))
        calls = any(
            isinstance(node, ast.Call)
            and (getattr(node.func, "id", None) == BAG_OPEN
                 or getattr(node.func, "attr", None) == BAG_OPEN)
            for node in ast.walk(tree))
        if not calls:
            missing.append(path.name)
    return missing


# --- the sweep -------------------------------------------------------------------

def test_every_entrypoint_actually_opens_a_run_bag() -> None:
    """THE REQUIREMENT. A parent added without the call goes red on the merge path."""
    discovered = _entrypoints(ENTRYPOINTS_DIR)
    assert discovered, f"no entrypoints discovered under {ENTRYPOINTS_DIR} — the sweep is inert"

    missing = _missing_bag_open(ENTRYPOINTS_DIR)
    assert not missing, (
        f"these entrypoints start a run with no journal bag: {missing}. Every run "
        f"opens one as its first step (Persistent Memory Protocol Phase 1 r11) — "
        f"call `journal.open_run_bag(run_id=journal.mint_run_id(), "
        f"repo_root=repo_root, workflow_key=...)` inside the try block that "
        f"prints RuntimeError, before the first side effect.\n"
        f"SCOPE OF THIS SWEEP: {ENTRYPOINTS_DIR.relative_to(REPO_ROOT)}/run_*.py "
        f"and nothing else. A run initiated from anywhere else is INVISIBLE here.")


def test_the_sweep_is_not_vacuous() -> None:
    """A sweep that examined nothing would satisfy every assertion above.

    The count is asserted as non-trivial rather than pinned to eleven: pinning
    it would make adding an entrypoint fail this file for the wrong reason,
    while a bare `assert discovered` cannot tell one file from the whole fleet.
    """
    discovered = _entrypoints(ENTRYPOINTS_DIR)
    assert len(discovered) >= 10, (
        f"only {len(discovered)} entrypoints discovered under {ENTRYPOINTS_DIR}; "
        f"this fleet has eleven. The predicate has drifted from the tree.")


# --- the negative control ---------------------------------------------------------

def test_the_sweep_FAILS_on_a_deliberately_non_conforming_parent(tmp_path: Path) -> None:
    """DEMONSTRATED, NOT ASSERTED. A guard that cannot go red manufactures confidence.

    THE FIXTURE IS SELF-CONTAINED AND NOT THIS REPO'S TREE. A control sharing a
    fixture with the code under mutation over-fires, and the failure reads like
    a stronger guard rather than a defect in the control. Three files here, two
    conforming and one not, so the assertion has to DISCRIMINATE rather than
    merely go red — a sweep that flagged everything would pass a control that
    only checked "something failed".
    """
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "run_good.py").write_text(
        "from modules.journal import journal_activities as journal\n"
        "def main():\n"
        "    journal.open_run_bag(run_id='x', repo_root='.', workflow_key='good')\n")
    (scripts / "run_also_good.py").write_text(
        "from modules.journal.journal_activities import open_run_bag\n"
        "def main():\n"
        "    open_run_bag(run_id='x', repo_root='.', workflow_key='also-good')\n")
    (scripts / "run_forgot.py").write_text(
        "def main():\n"
        "    worktree = worktree_add('.', 'wt', 'HEAD')\n"
        "    return run_something(worktree)\n")

    assert len(_entrypoints(scripts)) == 3, "the fixture itself must be discovered"
    assert _missing_bag_open(scripts) == ["run_forgot.py"], (
        "the sweep must name exactly the non-conforming file — flagging all "
        "three would pass a red/green control while being useless")


def test_a_MENTION_of_the_call_does_not_satisfy_the_sweep(tmp_path: Path) -> None:
    """THE SUBSTRING BUG, ruled out by construction rather than by intent.

    The sibling sweep shipped exactly this defect: prose explaining the rule
    satisfied the check for the rule. Both files below name `open_run_bag` in
    text and neither calls it, so a grep-based sweep would report zero offenders
    where the truth is two.
    """
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "run_comment.py").write_text(
        "# see journal.open_run_bag for why every run opens a bag\n"
        "def main():\n"
        "    return 0\n")
    (scripts / "run_docstring.py").write_text(
        '"""This entrypoint is covered by open_run_bag elsewhere."""\n'
        "def main():\n"
        "    return 0\n")

    assert sorted(_missing_bag_open(scripts)) == ["run_comment.py", "run_docstring.py"]


# --- ordering: the call must come before the first side effect ---------------------

def test_the_call_precedes_the_first_side_effect_in_every_entrypoint() -> None:
    """r9 means *the run does not start*, and that is an ORDERING claim.

    A bag opened after `worktree_add` still refuses an unresolvable root — but by
    then a worktree exists on disk, which is the stranded-worktree failure the
    preflight module was built to end. Checked by line number rather than by
    control flow, which is the honest limit: it catches a call written below the
    side effect, not one hidden behind a branch that never runs.
    """
    offenders = []
    unchecked = []
    for path in _entrypoints(ENTRYPOINTS_DIR):
        tree = ast.parse(path.read_text(), filename=str(path))
        opens = [n.lineno for n in ast.walk(tree)
                 if isinstance(n, ast.Call)
                 and (getattr(n.func, "id", None) == BAG_OPEN
                      or getattr(n.func, "attr", None) == BAG_OPEN)]
        effects = _side_effect_lines(tree)
        if not (opens and effects):
            unchecked.append(path.name)
            continue
        if min(opens) > min(effects):
            offenders.append(f"{path.name} (bag at line {min(opens)}, "
                             f"side effect at line {min(effects)})")

    assert not offenders, (
        f"these entrypoints create something before opening the run's bag: "
        f"{offenders}. r9's refusal must land before the first side effect, or "
        f"a run with an unresolvable journal root still strands a worktree.")

    # THE UNCHECKED SET IS PINNED, so this check cannot quietly stop covering an
    # entrypoint. If a file drops out of the ordering check — because its handoff
    # changed shape — that is a coverage regression and it fails HERE rather than
    # passing vacuously, which is what the first version of this test did for six
    # of eleven files.
    assert sorted(unchecked) == sorted(_ORDERING_UNCOVERED), (
        f"the ordering check now examines a different set than it claims. "
        f"Unchecked now: {sorted(unchecked)}; declared: {sorted(_ORDERING_UNCOVERED)}. "
        f"An entrypoint that silently left this check is a coverage regression — "
        f"either restore a detectable side effect, or amend _ORDERING_UNCOVERED "
        f"with the reason it cannot be checked.")


def test_the_ordering_check_FAILS_on_a_reversed_entrypoint(tmp_path: Path) -> None:
    """The ordering guard, demonstrated the same way as the sweep.

    Two files, identical but for the order of two lines. If the check were
    keyed on presence rather than position, both would pass — which is the
    version of this test that would have shipped without a control.

    IT DRIVES `_side_effect_lines` ITSELF rather than a local reimplementation of
    it. The first version of this control inlined its own copy of the predicate,
    which meant it proved a copy discriminated and said nothing about the guard —
    and when the real predicate was widened, the copy silently kept testing the
    old one.
    """
    def offenders_in(source: str) -> bool:
        tree = ast.parse(source)
        opens = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and (getattr(n.func, "id", None) == BAG_OPEN
                      or getattr(n.func, "attr", None) == BAG_OPEN)]
        effects = _side_effect_lines(tree)
        return bool(opens and effects and min(opens) > min(effects))

    correct = ("def main():\n"
               "    journal.open_run_bag(run_id='x')\n"
               "    act.worktree_add('.', 'wt', 'HEAD')\n")
    reversed_ = ("def main():\n"
                 "    act.worktree_add('.', 'wt', 'HEAD')\n"
                 "    journal.open_run_bag(run_id='x')\n")

    # The by-name workflow handoff, which the widened predicate added and the
    # narrow one could not see at all.
    handoff_reversed = ("from modules.assistant.b.b_workflow import run_b\n"
                        "def main():\n"
                        "    run_b('.')\n"
                        "    journal.open_run_bag(run_id='x')\n")
    handoff_correct = ("from modules.assistant.b.b_workflow import run_b\n"
                       "def main():\n"
                       "    journal.open_run_bag(run_id='x')\n"
                       "    run_b('.')\n")

    assert not offenders_in(correct), "the conforming order must not be flagged"
    assert offenders_in(reversed_), "the reversed order must be flagged"
    assert not offenders_in(handoff_correct), "a conforming by-name handoff must pass"
    assert offenders_in(handoff_reversed), (
        "a workflow handoff called BY NAME before bag-open must be flagged — this "
        "is the case the narrow `worktree_add`-only predicate could not see, and "
        "it is six of the eleven entrypoints")


# --- the other reading of "parent", so neither is silently dropped ------------------

def test_every_worktree_creating_workflow_module_is_reachable_from_an_entrypoint() -> None:
    """THE OTHER DEFINITION OF PARENT, checked in the one direction that is checkable.

    `test_isolation_invariants.py` classifies a workflow module as a parent when
    it calls `act.worktree_add`. Those modules do not open bags — their
    entrypoints do — so this asserts the property that makes that safe: every
    such module is invoked by an entrypoint, and every entrypoint opens a bag.
    A worktree-creating module NO entrypoint reaches could run with no bag and be
    invisible to the sweep above.

    READ BY AST, FOR THE REASON `_missing_bag_open` STATES ABOVE. This test's
    first version asked `p.stem not in entrypoint_text` — a substring check over
    the concatenated entrypoint sources — which is precisely the defect that
    paragraph condemns, reintroduced on a different variable. A module merely
    NAMED in a comment or a docstring anywhere across eleven heavily-commented
    files would have been reported as reachable without being imported at all.

    WHAT IT CANNOT SEE: a module invoked dynamically, or by something outside
    `scripts/`. Reachability by import-and-name is a lower bound on the call
    graph, not the call graph.
    """
    assistant = REPO_ROOT / "scripts" / "workflows" / "temporal" / "modules" / "assistant"
    parents = [p for p in sorted(assistant.rglob("*_workflow.py"))
               if "__pycache__" not in p.parts and "act.worktree_add(" in p.read_text()]
    assert parents, "no worktree-creating workflow modules found — the predicate drifted"

    imported = _modules_imported_by(_entrypoints(ENTRYPOINTS_DIR))
    unreachable = [p.stem for p in parents if p.stem not in imported]

    assert not unreachable, (
        f"these workflow modules create a worktree but no entrypoint imports "
        f"them: {unreachable}. Whatever starts them starts a run with no journal "
        f"bag, and the entrypoint sweep cannot see it.")


def test_the_reachability_check_FAILS_on_a_module_only_MENTIONED(tmp_path: Path) -> None:
    """The reachability guard's own negative control, which it shipped without.

    Two fixture entrypoints: one that genuinely imports `alpha_workflow`, one
    that only names `beta_workflow` in a comment and a docstring. A substring
    check reports both reachable; the AST check must report exactly `beta`.
    """
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "run_alpha.py").write_text(
        "from modules.assistant.alpha import alpha_workflow as wf\n"
        "def main():\n"
        "    return wf.run_alpha()\n")
    (scripts / "run_beta.py").write_text(
        '"""Started by beta_workflow elsewhere."""\n'
        "# beta_workflow is documented here and imported nowhere\n"
        "def main():\n"
        "    return 0\n")

    imported = _modules_imported_by(_entrypoints(scripts))
    assert "alpha_workflow" in imported, "a real import must be seen"
    assert "beta_workflow" not in imported, (
        "a module named only in prose must NOT count as reachable — that is the "
        "substring bug this check was rewritten to rule out")


@pytest.mark.parametrize("module", ["root", "bag", "validate", "journal_activities"])
def test_the_journal_package_imports_no_workflow_module(module: str) -> None:
    """The journal must be loadable by a measurement helper or a CPI sweep.

    Dependency-free on the workflow tree, like `convergence.py` and
    `run_log.py`. Phase 6's reader is the consumer this protects: a validator
    that dragged in `modules.assistant` would drag in its `temporalio` import
    with it.
    """
    source = (REPO_ROOT / "scripts" / "workflows" / "temporal" / "modules" /
              "journal" / f"{module}.py").read_text()
    assert "modules.assistant" not in source
    assert "from ..assistant" not in source

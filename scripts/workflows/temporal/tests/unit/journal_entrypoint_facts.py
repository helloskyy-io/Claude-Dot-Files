"""What the entrypoint population IS — discovered once, for every test that asks.

WHY THIS MODULE EXISTS. Two guards need the same facts about the eleven
`run_*.py` kickoff entrypoints: `test_every_parent_opens_a_run_bag` asserts each
one opens a bag before its first side effect, and
`test_journal_prose_figures_are_DERIVED` checks that the counts this package's
prose quotes are true of the tree. The second reaching into the first would be a
test module importing a test module — which `test_test_tree_hygiene` refuses,
because that coupling has no declared owner and resolves only under pytest's
default import mode. The Testing Standard's answer is a component-prefixed
helper module, which is this, and `review_run_fakes.py` is the exemplar.

AND THE SHARING IS THE POINT, NOT A SIDE EFFECT OF THE RULE. A second copy of
"which files are the parents" is the exact defect the guards above exist to
catch, one layer up: two enumerations agree until one is edited. One discovery,
two readers.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
ENTRYPOINTS_DIR = REPO_ROOT / "scripts" / "workflows" / "temporal" / "scripts"

# The call every entrypoint must make, and the module alias it is made through.
BAG_OPEN = "open_run_bag"

# Side-effecting calls an entrypoint can make directly. `worktree_add` cuts a
# directory on disk; a function imported from a `*_workflow` module and called by
# NAME is the handoff to a workflow that will. Bag-open must precede whichever an
# entrypoint reaches first, because r9 means *the run does not start*, not *the
# run stops early*.
SIDE_EFFECT_ATTRS = ("worktree_add",)

# ⚠ THE ORDERING CHECK'S REAL COVERAGE IS 8 OF 11, AND STATING THE NUMBER IS THE
# POINT. The first version of that check listed `worktree_add` alone, which made
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
ORDERING_UNCOVERED = ("run_research.py", "run_research_minor.py", "run_review_pr.py")


def side_effect_lines(tree: ast.AST) -> list[int]:
    """Line numbers of calls that create something, in one entrypoint.

    Two shapes, because this fleet has two. An attribute call to a name in
    `SIDE_EFFECT_ATTRS` (`act.worktree_add(...)`), and a direct call to a
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
        if getattr(func, "attr", None) in SIDE_EFFECT_ATTRS:
            lines.append(node.lineno)
        elif isinstance(func, ast.Name) and func.id in workflow_names:
            lines.append(node.lineno)
    return lines


def entrypoints(directory: Path) -> list[Path]:
    """Every kickoff entrypoint, discovered rather than listed.

    Discovered for the same reason the preflight sweep is: a new entrypoint is
    covered the day it lands. A hand-maintained list is a net whose coverage
    depends on somebody remembering to add a line, which is not a net — measured
    in this repo when the isolation list covered 3 of 10 children.
    """
    return sorted(p for p in directory.glob("run_*.py") if "__pycache__" not in p.parts)

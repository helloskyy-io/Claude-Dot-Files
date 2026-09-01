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
import re
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

# ⚠ THE ORDERING CHECK'S REAL COVERAGE IS 9 OF 11, AND STATING THE NUMBER IS THE
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
# `run_research_minor.py` was the third until 2026-08-28, when the research
# tiers merged and it was deleted. Two remain, and the count this feeds is
# derived from this tuple rather than restated.
ORDERING_UNCOVERED = ("run_research.py", "run_review_pr.py")


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


# --- Phase 9 r5: the population covers every shape that can START a run ----------
#
# THE PREDICATE ABOVE IS ONE GLOB OVER ONE DIRECTORY, AND THAT WAS ENOUGH FOR
# EXACTLY AS LONG AS `run_*.py` WAS THE ONLY SHAPE. Workflow Decomposition Phase 3
# adds nine runners; the Temporal port turns an entrypoint into a client. A sweep
# that silently covers a new shape and one that silently misses it are equally
# useless, and the difference between them is invisible until something goes
# wrong — so what a shape IS gets declared, and an unclassified file fails.
#
# Each row states WHY the file cannot start a run. An entry here is a claim
# somebody made and can be checked; a file nobody classified is a claim nobody
# made, which is the state this exists to end.
NON_STARTING_FILES = {
    "preflight.py":
        "a helper, not an entrypoint. It computes paths and validates arguments "
        "and touches the filesystem only to LOOK — nothing it does can begin a "
        "run, which is the property that lets bag-open be ordered after it.",
    "dispatch_identity.py":
        "the client-side identity boundary the entrypoints call. It parses two "
        "flags and mints a name; it starts nothing and opens no bag.",
    "dispatch_context.py":
        "the frozen run context the entrypoints construct at their boundary. "
        "Like `dispatch_identity.py` beside it, it derives values and resolves "
        "the journal root; it starts nothing, cuts nothing and opens no bag — "
        "the entrypoint that built it does all three.",
    "validate_bag.py":
        "an operator tool that READS a finished bag and prints a report. It is "
        "the one file here that addresses the journal without being a run, and "
        "opening a bag to validate one would be the tool recording itself.",
}

# A shim is `<workflow>.sh` beside its runner: thin by design, it resolves the
# interpreter and passes every argument through untouched. It cannot start a run
# on its own — it can only start the `run_*.py` it execs, which the sweep already
# covers. `shim_target` is what makes that claim checkable rather than assumed: a
# shim pointed at something outside the swept population is a run-starting shape
# the sweep cannot see, which is the exact failure r5 names.
_SHIM_EXEC_RE = re.compile(
    r'exec\s+python3\s+"\$\{SCRIPT_DIR\}/([\w.]+)"\s+"\$@"', re.M)


def shim_target(path: Path) -> str | None:
    """The `run_*.py` a shim hands control to, or None when it execs nothing.

    None is the answer that matters: a `.sh` in this directory that does not
    match the one thin-shim shape is doing something the shim contract does not
    describe, and the sweep must fail on it rather than assume it is harmless.
    """
    match = _SHIM_EXEC_RE.search(path.read_text(encoding="utf-8"))
    return match.group(1) if match else None


def unclassified(directory: Path) -> list[str]:
    """Files in `directory` that are neither swept, nor a shim, nor declared.

    THE RETURN IS THE FAILURE. Anything here is a shape nobody has said is safe
    and nobody is checking — the two silent halves of r5 in one list.
    """
    swept = {p.name for p in entrypoints(directory)}
    loose = []
    for path in sorted(directory.iterdir()):
        if path.is_dir() or path.name in swept or path.name in NON_STARTING_FILES:
            continue
        if path.suffix == ".sh" and shim_target(path) in swept:
            continue
        loose.append(path.name)
    return loose

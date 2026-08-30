"""A parent's loop-back re-enters its CORRECTOR, never its author.

THE SHAPE, AND IT IS THE SAME IN ALL THREE FAMILIES:

    draft  ->  refine  ->  [sprint]  ->  gate  ->  review-pr
                  ^                                    |
                  +--------------- loop-back ----------+

The author runs ONCE. Every correction pass re-enters the child whose job is to
fix what a judge found. `build` loops `_refine_then_dispose`, `research` loops
`_verify_then_dispose`, and since 2026-08-29 `plan` loops
`_refine_size_and_dispose`.

WHY THIS IS A TEST AND NOT A CONVENTION. `plan` re-dispatched `plan-draft` at the
top of every loop-back for its whole life, and nothing anywhere said that was
different from its siblings. What it bought was measured on MDC PR #173: a run
dispatched to fill a five-phase gap in a seven-phase roadmap returned TEN phase
docs, three of which appear nowhere in the roadmap it was planning. One approved
phase became three across two loop-backs — each split generating findings about
its own sizing and placement, which justified the next loop-back. Five passes,
$97, never converged.

**An author invoked with authoring authority authors.** That is not a prompting
defect and it was not fixed by prompting: the run carried `correction_pass=True`
and grew the plan anyway. `MAX_LOOPS` caps the SPEND; only this shape caps the
SCOPE.

WHAT THIS DOES NOT CLAIM. It does not say a draft child may never see a `--pr`.
`plan_draft.sh --pr N` is a legitimate operator dispatch and stays one. The
constraint is on the PARENT'S LOOP: the automated correction cycle may not
re-enter the writer, because nothing inside that cycle is in a position to notice
that it has started re-designing.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from modules.assistant.build.build import build_workflow
from modules.assistant.plan.plan import plan_workflow
from modules.assistant.research.research import research_workflow

# parent module -> the callee name its loop must NOT contain.
_FAMILIES = [
    (build_workflow, "run_draft"),
    (research_workflow, "run_research_draft"),
    (plan_workflow, "run_plan_draft"),
]


def _loop_callees(tree: ast.Module) -> set[str]:
    """Every function called inside a `while` whose test mentions a loop bound.

    KEYED ON THE LOOP RATHER THAN ON THE FUNCTION, because the author call is a
    legitimate statement everywhere else in these modules — `plan_workflow` still
    calls `run_plan_draft` once, before the loop, and must keep doing so. Only
    its position is the defect.
    """
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        # RECOGNISED ON TWO SHAPES, because the three families do not write the
        # bound the same way: build and plan call `should_loop_back(...)`, while
        # research spells the same condition out as
        # `verdict is Verdict.HOLD_REDISPATCH and loops < MAX_LOOPS`. Keyed on
        # either, so a family is never silently outside the population.
        test_src = ast.dump(node.test)
        if not ("should_loop_back" in test_src or "HOLD_REDISPATCH" in test_src):
            continue
        # THE BODY, NOT THE WHOLE NODE. `ast.walk(node)` includes the loop's own
        # TEST, so `should_loop_back` itself came back as a callee — harmless for
        # the real assertion and wrong enough to make the literal controls
        # unreadable, which is how it was caught.
        for stmt in node.body:
            for inner in ast.walk(stmt):
                if isinstance(inner, ast.Call):
                    fn = inner.func
                    name = getattr(fn, "attr", None) or getattr(fn, "id", None)
                    if name:
                        found.add(name)
    return found


@pytest.mark.parametrize("module,author_callee",
                         _FAMILIES, ids=lambda x: getattr(x, "__name__", x).split(".")[-1])
def test_the_loop_back_does_not_call_the_author(module, author_callee: str) -> None:
    """The one line that would have caught the runaway before it cost $97."""
    tree = ast.parse(Path(inspect.getfile(module)).read_text(encoding="utf-8"))
    callees = _loop_callees(tree)
    assert callees, (
        f"{module.__name__} has no loop-bound `while` this walk can see, "
        f"so this assertion is vacuous. If the loop moved, move this recogniser."
    )
    assert author_callee not in callees, (
        f"{module.__name__}'s loop-back calls `{author_callee}` — its AUTHOR. Every "
        f"correction pass then re-runs the child whose job is to create, with full "
        f"authoring authority and a reviewer's runway it is free to read as a brief. "
        f"Measured cost of exactly this on MDC PR #173: seven planned phases became "
        f"ten, three of them in no roadmap, across five passes and $97. Loop the "
        f"CORRECTOR instead — the unit that ends at `review-pr` — and let the author "
        f"run once."
    )


@pytest.mark.parametrize("source,expected", [
    # The corrected shape: the loop calls the disposing unit and nothing else.
    ("while helper.should_loop_back(v, n):\n"
     "    v = _refine_then_dispose(a, b)\n", {"_refine_then_dispose"}),
    # The shape this guard exists to catch.
    ("while routing.should_loop_back(v, n):\n"
     "    plan_write.run_plan_draft(x=1)\n"
     "    v = _refine_size_and_dispose(a)\n", {"run_plan_draft", "_refine_size_and_dispose"}),
    # A `while` that is not a loop-back must not be collected at all.
    ("while time.monotonic() < deadline:\n"
     "    run_plan_draft()\n", set()),
])
def test_the_loop_recogniser_answers_correctly_on_a_literal(
        source: str, expected: set[str]) -> None:
    """The predicate above, driven on snippets rather than only on the tree.

    A walk over three real modules passes trivially if `_loop_callees` stops
    recognising `while` loops — the guard would report "no author in the loop" for
    a parent that called nothing but. The third case is the one that matters: the
    recogniser keys on `should_loop_back`, so an unrelated `while` must contribute
    nothing.
    """
    assert _loop_callees(ast.parse(source)) == expected

"""Controls for `assembled_prompt`, which is a PREDICATE two guards now trust.

WHY IT NEEDS ITS OWN MODULE RATHER THAN ITS CONSUMERS' COVERAGE. Both consumers
use it the same way — expand, then assert on the result — so between them they
exercise exactly one path: a placeholder that names a real fragment. The three
things that would make it dangerous are invisible from there. A no-op `expand`
was demonstrated to turn both consumers red, which proves it is LOAD-BEARING and
says nothing about whether it is CORRECT at the edges.

Each test below is one claim, on a self-contained fixture.
"""
from __future__ import annotations

import pytest

from assembled_prompt import SHARED, expand


def test_a_POOL_placeholder_is_replaced_by_its_fragment() -> None:
    stem = "stage_order_is_mandatory"
    body = (SHARED / f"{stem}.md").read_text()
    out = expand("before\n${STAGE_ORDER_IS_MANDATORY}\nafter")
    assert body.strip() in out and "${STAGE_ORDER_IS_MANDATORY}" not in out
    assert out.startswith("before") and out.rstrip().endswith("after")


def test_a_RUNTIME_placeholder_is_left_alone() -> None:
    """The half that makes this NOT a reimplementation of `render()`.

    `${PR_NUMBER}` has no fragment behind it — it is a value the workflow
    supplies at dispatch. Substituting it would be wrong, and DROPPING it would
    be worse: a guard asserting on assembled text must still be able to see that
    a prompt asks for a PR number at all.
    """
    assert expand("see ${PR_NUMBER} and ${RESEARCH_DIR}") == "see ${PR_NUMBER} and ${RESEARCH_DIR}"


def test_a_fragment_carrying_a_fragment_resolves_to_a_FIXED_POINT() -> None:
    """`stages_1_to_4_from_plan` carries pool placeholders of its own.

    Named rather than synthesised, because a synthetic nesting would prove the
    loop runs and not that the tree actually contains the case. If this fragment
    ever stops nesting, the assertion says so instead of passing vacuously.
    """
    raw = (SHARED / "stages_1_to_4_from_plan.md").read_text()
    assert "${STAGE_ORDER_IS_MANDATORY}" in raw, (
        "the tree no longer has a nested pool fragment, so this test proves "
        "nothing about the fixed-point loop — find the new nesting case or delete it"
    )
    out = expand(raw)
    assert "${STAGE_ORDER_IS_MANDATORY}" not in out
    assert (SHARED / "stage_order_is_mandatory.md").read_text().strip() in out


def test_a_SELF_REFERENTIAL_fragment_RAISES_rather_than_spinning() -> None:
    """The bound is the difference between a loud failure and a hung suite.

    Driven through a real pool file because `expand` resolves by looking one up:
    a purely synthetic string cannot reach the loop at all. The file is removed
    in a finally so a failure here cannot leave the pool dirty for every other
    module in the run.
    """
    loop = SHARED / "zz_selfref_control.md"
    loop.write_text("carries ${ZZ_SELFREF_CONTROL} inside itself\n")
    try:
        with pytest.raises(ValueError, match="did not converge"):
            expand("${ZZ_SELFREF_CONTROL}")
    finally:
        loop.unlink()

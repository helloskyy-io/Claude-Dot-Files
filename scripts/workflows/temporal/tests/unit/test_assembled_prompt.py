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

from assembled_prompt import SHARED, assembled, expand

ASSISTANT = SHARED.parent


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


def test_a_SELF_REFERENTIAL_fragment_RAISES_rather_than_spinning(tmp_path) -> None:
    """The bound is the difference between a loud failure and a hung suite.

    Driven through a real file because `expand` resolves by looking one up: a
    purely synthetic string cannot reach the loop at all. THE FILE GOES IN
    `tmp_path`, NOT IN THE POOL, and the distinction is not tidiness — an
    earlier version of this test wrote `zz_selfref_control.md` into
    `modules/assistant/prompts/`, a directory whose contents are SENT TO THE
    MODEL, and relied on a `finally` that a SIGKILL, an OOM or a `-x` interrupt
    does not run. It also made two unrelated modules order-dependent:
    `test_prompt_completeness` fails any pool file with no supplier and
    `test_promoted_fragments_render_for_every_consumer` asserts the floor is
    set-equal to the pool, so a concurrent collection saw a fragment that was
    never promoted. `pool=` costs one argument and removes all of it.
    """
    (tmp_path / "zz_selfref_control.md").write_text(
        "carries ${ZZ_SELFREF_CONTROL} inside itself\n")
    with pytest.raises(ValueError, match="did not converge"):
        expand("${ZZ_SELFREF_CONTROL}", pool=tmp_path)


def test_a_CHILD_S_OWN_FILE_WINS_over_a_pool_fragment_of_the_same_stem() -> None:
    """The case pool-only resolution got WRONG, driven on the real collision.

    `plan_revision` supplies `${RULES}` from its own directory — the PLANNING
    ruleset — while the pool's `rules.md` is the BUILD ruleset, and the two say
    opposite things about whether a run may touch code. Named rather than
    synthesised: a synthetic collision would prove the lookup order runs and not
    that the tree contains a child this order is load-bearing for. If the
    collision is ever reconciled, this goes red and says so instead of quietly
    proving nothing.
    """
    child = (ASSISTANT / "plan" / "plan_revision" / "prompts")
    assert (child / "rules.md").is_file() and (SHARED / "rules.md").is_file(), (
        "the pool/child `rules` collision this test is about is gone — find the "
        "new collision or delete this test rather than leaving it vacuous"
    )
    planning = "This is a PLANNING build — do not modify code, scripts, or configuration files"
    assert planning in (child / "rules.md").read_text()
    assert planning not in (SHARED / "rules.md").read_text()

    out = assembled(child / "new_branch.md")
    assert planning in out, (
        "the planning ruleset did not reach the assembled planning prompt — "
        "resolution fell through to the pool, which is the defect this order fixes"
    )

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

from modules.assistant import assistant_activities as act

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


# `test_a_CHILD_S_OWN_FILE_WINS_over_a_pool_fragment_of_the_same_stem` WAS HERE,
# AND IT IS DELETED RATHER THAN REWRITTEN SYNTHETICALLY — on its own instruction:
# *"if the collision is ever reconciled, this goes red and says so instead of
# quietly proving nothing."* It drove the resolver on the ONE real collision in
# the tree: `plan_revision` supplied its own `rules.md` — the PLANNING ruleset —
# shadowing the pool's BUILD ruleset, and the two said opposite things about
# whether a run may touch code.
#
# `plan_revision` was removed on 2026-09-05 (`plan` already revises a component's
# docs and refuses to rename, renumber or delete a phase doc), and no child
# supplies a prompt whose stem collides with a pool fragment any more — measured,
# zero. The resolver's child-wins precedence is still implemented and still
# correct; it is simply load-bearing for nothing today.
#
# Re-add a driven test the moment a child shadows a pool stem again. A synthetic
# fixture was deliberately rejected here once already, and the reason still
# holds: it would prove the lookup order RUNS, not that the tree contains a child
# the order matters for.

def test_the_RESOLVER_AGREES_WITH_THE_render_IT_MODELS(tmp_path) -> None:
    """`expand` is a MODEL of `render`, and nothing was holding the two together.

    `assembled_prompt` exists so a file-scoped guard asserts on what the model
    RECEIVES rather than on what one prompt file contains, which means every
    guard built on it inherits `expand`'s claim to reproduce `render`. That
    claim was stated in a docstring and checked by nothing: the two functions
    hand-roll the same bounded fixed-point substitution in two files, and an
    edit to `render` alone would leave three guards asserting against a string
    no dispatch produces — silently, and in the green direction.

    THE GRAMMAR IS THE HALF THAT HAS ALREADY BROKEN ONCE. `render`'s own comment
    records it: an earlier `[A-Z_]+` missed `${STAGES_1_TO_4}`, and a prompt
    shipped with its entire stage body replaced by a literal placeholder while
    the check raised nothing. `expand` carries a second copy of that pattern, so
    the fixture below uses a digit-bearing name on purpose.

    WHAT THIS DOES NOT PIN, because the two are deliberately different there:
    `render` RAISES on a placeholder nothing supplies and `expand` leaves it
    standing (a runtime value a guard must still be able to see), and `render`
    has an `opaque` second pass for operator content that `expand` has no notion
    of. Those are contracts, not drift; this pins only the surface they share.
    """
    # A fragment carrying a fragment, reached through a digit-bearing name.
    (tmp_path / "zz_outer_1.md").write_text("top ${ZZ_INNER_2} tail")
    (tmp_path / "zz_inner_2.md").write_text("deep")
    template = "A ${ZZ_OUTER_1} B"

    through_expand = expand(template, pool=tmp_path)
    through_render = act.render(template, {
        "ZZ_OUTER_1": (tmp_path / "zz_outer_1.md").read_text(),
        "ZZ_INNER_2": (tmp_path / "zz_inner_2.md").read_text(),
    })

    assert through_expand == "A top deep tail B", (
        "the model no longer resolves a nested, digit-bearing placeholder"
    )
    assert through_expand == through_render, (
        "`expand` and the `render` it models disagree on the same input, so "
        "every guard built on `assembled()` is asserting against a string no "
        f"dispatch produces:\n  expand: {through_expand!r}\n  render: {through_render!r}"
    )

    # AND THEY FAIL THE SAME WAY. The bound is what turns a self-referential
    # fragment into a loud error instead of a hung suite, and it is written as a
    # literal in both files.
    (tmp_path / "zz_selfref.md").write_text("carries ${ZZ_SELFREF} inside itself")
    with pytest.raises(ValueError, match="did not converge"):
        expand("${ZZ_SELFREF}", pool=tmp_path)
    with pytest.raises(ValueError, match="did not converge"):
        act.render("${ZZ_SELFREF}", {"ZZ_SELFREF": "carries ${ZZ_SELFREF} inside itself"})

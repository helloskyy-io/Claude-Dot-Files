"""A task file's ${...} tokens reach the model LITERALLY.

WHY THIS EXISTS. Two dispatches died the same afternoon, both on briefs that
were *describing* the placeholder mechanism — one explaining the digit-blind
regex, one documenting the prompt-completeness guard. Prose about this system
routinely contains a literal token, and there was no way to escape one.

Scanned with the prompt fragments, an operator's token either gets SUBSTITUTED
into the task statement — silently changing what was asked — or trips the
leftover guard and kills the run before it starts. Both are wrong for content
the system did not author.
"""

from __future__ import annotations

import pytest

from modules.assistant.assistant_activities import render


def test_an_operator_token_is_passed_through_literally() -> None:
    """The exact failure: a brief that quotes a placeholder name."""
    out = render(
        "Task: ${DESCRIPTION}\nRules: ${RULES}",
        {"DESCRIPTION": "fix the guard that silently missed ${STAGES_1_TO_4}",
         "RULES": "be careful"},
        opaque=frozenset({"DESCRIPTION"}),
    )
    assert "${STAGES_1_TO_4}" in out, "the operator's token was rewritten or eaten"
    assert "fix the guard that silently missed ${STAGES_1_TO_4}" in out


def test_an_operator_token_does_not_trip_the_guard() -> None:
    """It must not RAISE either — that is how the two dispatches actually died."""
    render("Task: ${DESCRIPTION}", {"DESCRIPTION": "see ${SOME_VAR}"},
           opaque=frozenset({"DESCRIPTION"}))


def test_an_operator_token_is_never_substituted_from_values() -> None:
    """Even when a key of that name EXISTS, operator text is not rewritten.

    The dangerous case: the brief says ${RULES} while RULES is a real key. A
    re-scan would splice the whole rules fragment into the task statement.
    """
    out = render(
        "Task: ${DESCRIPTION}\nRules: ${RULES}",
        {"DESCRIPTION": "the ${RULES} block is too long", "RULES": "RULE ONE"},
        opaque=frozenset({"DESCRIPTION"}),
    )
    assert "the ${RULES} block is too long" in out
    assert out.count("RULE ONE") == 1, "operator text absorbed a fragment"


def test_fragments_still_resolve_to_a_fixed_point() -> None:
    """The opaque split must not break the reason the loop exists."""
    out = render("${A}", {"A": "sees ${B}", "B": "resolved"}, opaque=frozenset())
    assert out == "sees resolved"


def test_a_genuinely_missing_placeholder_still_raises() -> None:
    """POSITIVE CONTROL. A guard that stopped firing would pass every test above."""
    with pytest.raises(ValueError, match="unsubstituted"):
        render("${NOBODY_SUPPLIES_THIS}", {}, opaque=frozenset())


def test_an_opaque_key_that_is_never_supplied_still_raises() -> None:
    """Declaring a key opaque must not become a way to silence the guard."""
    with pytest.raises(ValueError, match="unsubstituted"):
        render("${DESCRIPTION} ${MISSING}", {"DESCRIPTION": "x"},
               opaque=frozenset({"DESCRIPTION"}))

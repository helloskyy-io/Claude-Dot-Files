"""V1/V2 parity: every turn cap is DERIVED from V1, never re-declared.

Exists because of a specific production failure: the V2 port RE-DECLARED V1's
constants instead of deriving from them, a draft ran at MAX_TURNS=120 against
V1's 250, and a full budget was spent producing nothing recoverable. V1's logs
already held the answer — the same task class had completed in 130 turns, so the
cap was set below a known-good measurement that existed at authoring time.

These tests convert silent divergence into a red test. A deliberate difference
is allowed but must be DECLARED here with a reason, never left implied.

The sibling files carry the rest of what the original single parity module
asserted: `test_isolation_invariants.py` (worktree isolation and observed
outcomes), `test_prompt_completeness.py` (every ${VAR} has a supplier) and
`test_delegated_contract.py` (the five variables run-claude.sh demands).
"""

from __future__ import annotations

import inspect

import pytest

from modules.assistant import assistant_activities as act
from modules.assistant.build.build_draft import build_draft_workflow as draft
from modules.assistant.build.build_refine import build_refine_workflow as refine
from modules.assistant.review_pr import review_pr_activities as rpa

# (module, V1 script it must agree with, the value V1 declares today)
TURN_CAP_OWNERS = [
    pytest.param(draft, "build-draft.sh", 250, id="build-draft"),
    pytest.param(refine, "build-refine.sh", 250, id="build-refine"),
    pytest.param(rpa, "review-pr.sh", 120, id="review-pr"),
]


def _hardcodes_a_turn_cap(source: str) -> bool:
    """True when the source states a turn cap as a literal instead of deriving it.

    Matches the two literal prefixes any realistic cap starts with (1xx, 2xx).
    Kept as a named predicate so the positive control below can prove it fires.
    """
    return "max_turns=1" in source or "max_turns=2" in source


# --- 1. Every V2 workflow DERIVES its turn cap; none hardcodes one ------------

@pytest.mark.parametrize(("module", "script", "expected"), TURN_CAP_OWNERS)
def test_turn_cap_is_derived_from_v1(module, script: str, expected: int) -> None:
    derived = int(act.v1_constant(script, "MAX_TURNS"))
    assert derived == expected, (
        f"{script} now declares MAX_TURNS={derived}, this suite expected {expected}. "
        "If V1 changed deliberately, update the expectation here WITH a reason; "
        "a cap set below a known-good measurement burns a full budget for nothing."
    )


@pytest.mark.parametrize(("module", "script", "expected"), TURN_CAP_OWNERS)
def test_no_workflow_hardcodes_a_turn_cap(module, script: str, expected: int) -> None:
    source = inspect.getsource(module)
    assert not _hardcodes_a_turn_cap(source), (
        f"{module.__name__} states a turn cap as a literal instead of calling "
        f"v1_constant({script!r}, 'MAX_TURNS'). Re-declaration is what let V2 run "
        "at 120 against V1's 250 — deriving makes divergence impossible rather "
        "than merely detectable."
    )


def test_hardcoded_cap_predicate_positive_control() -> None:
    """Positive control for the structural check above.

    Testing Standard § Structural tests need a positive control: without this,
    a rename or a changed call shape turns the grep into a permanent pass and
    nothing signals that it stopped looking.
    """
    assert _hardcodes_a_turn_cap("act.run_claude(prompt, max_turns=250)") is True
    assert _hardcodes_a_turn_cap("act.run_claude(prompt, max_turns=120)") is True
    assert _hardcodes_a_turn_cap("max_turns=act.v1_constant('build-draft.sh', 'MAX_TURNS')") is False


# --- 2. Derivation FAILS LOUD rather than guessing ----------------------------

@pytest.mark.parametrize(
    ("script", "constant", "why"),
    [
        pytest.param("nonexistent.sh", "MAX_TURNS", "missing script", id="missing-script"),
        pytest.param("build-draft.sh", "NO_SUCH_CONST", "missing constant", id="missing-constant"),
    ],
)
def test_derivation_raises_rather_than_guessing(script: str, constant: str, why: str) -> None:
    """A silent default here is the whole failure mode: a guessed cap looks like
    a working run right up until the budget is gone.
    """
    with pytest.raises((FileNotFoundError, ValueError)):
        act.v1_constant(script, constant)

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

Section 3 is the other half of this module's job and is not about turn caps at
all: it is the EXECUTABILITY sweep, the class-level guard against a name that is
used but never imported. It lives here because it arrived here — it was added to
the single parity module and has to survive the split into siblings.
"""

from __future__ import annotations

import inspect
import shutil
import subprocess
from pathlib import Path

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

# `_module` / `_expected` below: TURN_CAP_OWNERS is deliberately ONE table — it is
# the single source of truth for the module <-> script <-> V1-value mapping, and
# splitting it per-test would duplicate exactly the thing that must not diverge.
# The underscore marks the field this particular test does not read, so someone
# editing a row can see at a glance which test will and will not notice.

@pytest.mark.parametrize(("_module", "script", "expected"), TURN_CAP_OWNERS)
def test_turn_cap_is_derived_from_v1(_module, script: str, expected: int) -> None:
    derived = int(act.v1_constant(script, "MAX_TURNS"))
    assert derived == expected, (
        f"{script} now declares MAX_TURNS={derived}, this suite expected {expected}. "
        "If V1 changed deliberately, update the expectation here WITH a reason; "
        "a cap set below a known-good measurement burns a full budget for nothing."
    )


@pytest.mark.parametrize(("module", "script", "_expected"), TURN_CAP_OWNERS)
def test_no_workflow_hardcodes_a_turn_cap(module, script: str, _expected: int) -> None:
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
    ("script", "constant", "expected_error"),
    [
        # The two branches are disjoint and deterministic, so each case names the
        # ONE exception it must raise. A tuple of both would still pass if a
        # future edit swapped which branch raises which — an over-broad
        # pytest.raises is a named anti-pattern in the Testing Standard.
        pytest.param("nonexistent.sh", "MAX_TURNS", FileNotFoundError, id="missing-script"),
        pytest.param("build-draft.sh", "NO_SUCH_CONST", ValueError, id="missing-constant"),
    ],
)
def test_derivation_raises_rather_than_guessing(
    script: str, constant: str, expected_error: type[Exception]
) -> None:
    """A silent default here is the whole failure mode: a guessed cap looks like
    a working run right up until the budget is gone.
    """
    with pytest.raises(expected_error):
        act.v1_constant(script, constant)


# --- 3. EXECUTABILITY — a name that is used but never imported ----------------
#
# Tests IMPORT modules; they do not CALL into every branch. A NameError in an
# unexercised path stays invisible until a real run reaches it — which is how
# `_shared.worktree_add` crashed the LAST leg of a 40-minute pipeline, after the
# draft and refine legs had both completed real work and after the engineer who
# found it had correctly declined to fix it out of scope.
#
# ruff's F821 sweep closes the class without executing anything: it resolves
# every name in every module, including the branches no test reaches.

COMPONENT_ROOT = Path(__file__).resolve().parents[2]

# Everything this component ships that Python has to be able to resolve.
SWEEP_TARGETS = [COMPONENT_ROOT / name for name in ("modules", "scripts", "tests")]


# Wall-clock backstop. The sweep takes well under a second on this tree, so any
# value here is generous — the point is that an unbounded `subprocess.run` in
# test infrastructure that gates autonomous dispatch does not FAIL a stage when
# it goes wrong, it WEDGES one, and a wedged stage burns its whole turn budget
# with nothing to show. Same reason the root conftest bounds memory: a runaway
# must fail AS A TEST.
_RUFF_TIMEOUT_S = 60


def _ruff_f821(*targets: Path) -> subprocess.CompletedProcess[str]:
    """ruff's undefined-name check over `targets`, returncode 0 iff clean."""
    return subprocess.run(
        ["ruff", "check", "--select", "F821", "--no-cache", "-q", *(str(t) for t in targets)],
        capture_output=True,
        text=True,
        check=False,
        timeout=_RUFF_TIMEOUT_S,
    )


def test_ruff_is_installed_so_the_sweep_is_not_inert() -> None:
    """Absent ruff FAILS rather than skips.

    A skip here would report a green suite for a guard that never ran, which is
    the exact shape of the problem the sweep exists to remove. An inert guard is
    worse than no guard: it occupies the slot where a real one would go.
    """
    assert shutil.which("ruff"), (
        "ruff is not on PATH — the F821 executability sweep below cannot run. "
        "Install ruff (`pip install ruff`); do not skip this test."
    )


def test_no_undefined_names_in_the_component() -> None:
    result = _ruff_f821(*SWEEP_TARGETS)
    assert result.returncode == 0, (
        "ruff F821 found a name used but never bound — this is a live NameError "
        "waiting on the first run that reaches that branch, not a lint nit:\n"
        f"{result.stdout.strip()}"
    )


def test_the_sweep_detects_an_undefined_name(tmp_path: Path) -> None:
    """Positive control for the sweep above.

    Testing Standard § Structural tests need a positive control. Without it a
    changed flag, a renamed rule or a target list that stopped resolving turns
    the sweep into a permanent pass and nothing signals that it stopped looking.
    The probe reproduces the original defect verbatim: `_shared` used, never
    imported.
    """
    probe = tmp_path / "probe.py"
    probe.write_text("def crash():\n    return _shared.worktree_add()\n")

    result = _ruff_f821(probe)

    assert result.returncode != 0, "the F821 sweep did not fire on a known undefined name"
    assert "F821" in result.stdout, f"expected an F821 diagnostic, got: {result.stdout!r}"

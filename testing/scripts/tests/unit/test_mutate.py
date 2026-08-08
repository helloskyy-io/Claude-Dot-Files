"""The mutation harness is the apparatus that decides whether every other guard
in this repo is trustworthy, and until now nothing exercised it.

WHY THIS EXISTS. `mutate.sh` has shipped a WRONG VERDICT three times, and every
one was invisible to careful reading and to CI:

  1. It judged each leg by grepping the tail line for the substring "failed".
     A mutation that breaks collection prints "1 error" and exits 2 — the guard
     fired, hard — but that text has no "failed" in it, so the harness reported
     THE GUARD DID NOT FIRE over a guard that worked.
  2. A replacement attempt lost `report_leg`'s diagnostic into a command
     substitution; caught only because someone re-ran the repro by hand.
  3. An 18-line multi-line-OLD guard shipped having been executed by nobody.

Its failure mode is silent by construction and both directions are expensive: a
false "THE GUARD DID NOT FIRE" gets a working guard deleted, and a false
"MUTATION DEMONSTRATED" certifies a guard that asserts nothing. "You would
notice" is exactly wrong for a tool whose way of breaking is to confidently
report the wrong answer.

SHAPE. Each test builds a self-contained sandbox — one trivial source module and
one pytest file that asserts something about it — and drives the real script
end to end. Nothing is mocked: the thing under test is the harness's VERDICT,
and a verdict cannot be unit-tested away from the pytest run that produces it.
This mirrors `scripts/workflows/temporal/tests/unit/test_runner_discovery.py`,
which sandboxes `python.sh` the same way.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
MUTATE = REPO_ROOT / "testing" / "scripts" / "mutate.sh"

# Exit codes are the harness's contract with its callers, so they are asserted
# by name rather than by magic number at each site.
DEMONSTRATED = 0
FAILED_OR_HARNESS_ERROR = 1
REFUSED = 2


def test_the_harness_under_test_actually_exists() -> None:
    """Guards the whole module: a moved script would make every test below
    pass vacuously by failing for the wrong reason."""
    assert MUTATE.is_file(), f"{MUTATE} is missing — the rest of this file proves nothing"
    assert os.access(MUTATE, os.X_OK), f"{MUTATE} is not executable"


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    """A minimal world: `subject.py` holds a value, `test_subject.py` asserts it.

    Deliberately tiny. The harness runs pytest three times per invocation, so
    every second of suite time here is multiplied by three.
    """
    (tmp_path / "subject.py").write_text("THRESHOLD = 10\nLABEL = 'alpha'\n")
    (tmp_path / "test_subject.py").write_text(
        "import subject\n\n\ndef test_threshold():\n    assert subject.THRESHOLD == 10\n"
    )
    return tmp_path


def run_mutate(sandbox: Path, old: str, new: str, target: str = "test_subject.py"):
    """Drive the real script. `cwd` is the sandbox so the relative TARGET
    resolves there and `import subject` works without touching sys.path."""
    return subprocess.run(
        [str(MUTATE), "subject.py", old, new, target],
        cwd=str(sandbox), capture_output=True, text=True, timeout=180,
    )


# --------------------------------------------------------------------------
# Refusals. A mutation the harness cannot reason about must be REFUSED, never
# guessed at — a guessed mutation produces a confident verdict about nothing.
# --------------------------------------------------------------------------

def test_a_string_absent_from_the_file_is_refused(sandbox: Path) -> None:
    """The single most important refusal: a mutation that changes nothing
    proves nothing, and would otherwise report THE GUARD DID NOT FIRE over a
    guard that was never given anything to catch."""
    r = run_mutate(sandbox, "THRESHOLD = 999", "THRESHOLD = 1")
    assert r.returncode == REFUSED, f"expected refusal, got {r.returncode}\n{r.stdout}{r.stderr}"
    assert "MUTATION DEMONSTRATED" not in r.stdout


def test_a_string_occurring_twice_is_refused(sandbox: Path) -> None:
    """`.replace(old, new, 1)` hits the FIRST occurrence. If that is not the
    one the author meant, the harness reports a guard failure that did not
    happen — so ambiguity is refused rather than resolved by position."""
    (sandbox / "subject.py").write_text("X = 1\nY = 1\n")
    r = run_mutate(sandbox, "= 1", "= 2")
    assert r.returncode == REFUSED, f"ambiguous OLD was not refused\n{r.stdout}{r.stderr}"


def test_two_occurrences_on_ONE_line_are_refused(sandbox: Path) -> None:
    """The regression that shipped: the ambiguity guard counted matching LINES
    via `grep -c`, while `.replace` counts OCCURRENCES. A string appearing
    twice on a single line passed the guard and mutated the wrong one."""
    (sandbox / "subject.py").write_text("PAIR = ('a', 'a')\n")
    r = run_mutate(sandbox, "'a'", "'b'")
    assert r.returncode == REFUSED, (
        "a string occurring twice on ONE line was accepted — the ambiguity guard "
        f"is counting lines, not occurrences\n{r.stdout}{r.stderr}"
    )


def test_a_multi_line_string_is_refused(sandbox: Path) -> None:
    """The guard added by commit 2594a8c, which until this suite had been
    exercised by nobody at all."""
    r = run_mutate(sandbox, "THRESHOLD = 10\nLABEL", "THRESHOLD = 11\nLABEL")
    assert r.returncode == REFUSED, f"multi-line OLD was not refused\n{r.stdout}{r.stderr}"


# --------------------------------------------------------------------------
# Verdicts.
# --------------------------------------------------------------------------

def test_a_mutation_the_suite_catches_reports_DEMONSTRATED(sandbox: Path) -> None:
    r = run_mutate(sandbox, "THRESHOLD = 10", "THRESHOLD = 11")
    assert r.returncode == DEMONSTRATED, f"{r.stdout}{r.stderr}"
    assert "MUTATION DEMONSTRATED" in r.stdout


def test_a_mutation_nothing_asserts_reports_that_the_guard_did_not_fire(sandbox: Path) -> None:
    """`LABEL` is asserted by no test, so mutating it must produce the
    guard-did-not-fire verdict rather than a pass."""
    r = run_mutate(sandbox, "LABEL = 'alpha'", "LABEL = 'omega'")
    assert r.returncode == FAILED_OR_HARNESS_ERROR
    assert "THE GUARD DID NOT FIRE" in r.stderr


def test_the_did_not_fire_message_names_the_wrong_mutation_possibility(sandbox: Path) -> None:
    """STILL-GREEN is AMBIGUOUS and the message must say so.

    Raised by the MDC side against their own harness: a mutation anchor removed
    the wrong frozenset member, the suite stayed green, and the run read that as
    "no guard exists" when the truth was "the mutation missed". Refusing an
    absent string closes half the class; the other half is a mutation that IS
    present, DOES apply, and changes nothing that matters. The harness cannot
    detect that — so it must not report the ambiguous case as if it were
    certain.
    """
    r = run_mutate(sandbox, "LABEL = 'alpha'", "LABEL = 'omega'")
    combined = r.stdout + r.stderr
    assert "did not change" in combined.lower() or "mutation missed" in combined.lower(), (
        "the guard-did-not-fire message states only 'nothing asserts this property' "
        "and 'the assertion cannot distinguish' — it never offers the third "
        f"possibility, that the mutation itself was wrong.\n{combined}"
    )


def test_a_mutation_that_breaks_COLLECTION_still_counts_as_the_guard_firing(sandbox: Path) -> None:
    """The original shipped defect, pinned.

    A mutation producing a syntax error makes pytest exit 2 and print "1 error",
    which contains no "failed". The harness must judge by EXIT CODE.
    """
    r = run_mutate(sandbox, "THRESHOLD = 10", "THRESHOLD = (10")
    assert r.returncode == DEMONSTRATED, (
        "a collection error was not counted as the guard firing — the harness is "
        f"back to grepping for the substring 'failed'\n{r.stdout}{r.stderr}"
    )


def test_a_target_that_collects_nothing_is_a_HARNESS_ERROR_not_a_verdict(sandbox: Path) -> None:
    """pytest exit 5 means TARGET was wrong, not that anything was tested.
    Reading it as RED would certify a guard that never ran."""
    (sandbox / "empty_test.py").write_text("# no tests here\n")
    r = run_mutate(sandbox, "THRESHOLD = 10", "THRESHOLD = 11", target="empty_test.py")
    assert r.returncode == FAILED_OR_HARNESS_ERROR
    assert "HARNESS ERROR" in r.stderr
    assert "MUTATION DEMONSTRATED" not in r.stdout


def test_an_already_red_target_is_refused_before_mutating(sandbox: Path) -> None:
    """A mutation against a failing suite tells you nothing about the mutation."""
    (sandbox / "test_subject.py").write_text(
        "import subject\n\n\ndef test_threshold():\n    assert subject.THRESHOLD == 99\n"
    )
    r = run_mutate(sandbox, "THRESHOLD = 10", "THRESHOLD = 11")
    assert r.returncode == FAILED_OR_HARNESS_ERROR
    assert "ALREADY RED" in r.stderr


# --------------------------------------------------------------------------
# Cleanup. A harness that leaves a mutated tree behind is worse than no
# harness: the next run tests code nobody meant to ship.
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("old", "new", "case"),
    [
        ("THRESHOLD = 10", "THRESHOLD = 11", "success"),
        ("LABEL = 'alpha'", "LABEL = 'omega'", "guard-did-not-fire"),
        ("THRESHOLD = 10", "THRESHOLD = (10", "collection-error"),
    ],
)
def test_the_file_is_restored_on_every_exit_path(sandbox: Path, old: str, new: str, case: str) -> None:
    before = (sandbox / "subject.py").read_text()
    run_mutate(sandbox, old, new)
    assert (sandbox / "subject.py").read_text() == before, (
        f"the tree was left mutated after the {case} path — the EXIT trap did not restore it"
    )

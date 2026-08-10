"""The mutation harness is the apparatus that decides whether every other guard
in this repo is trustworthy, and until now nothing exercised it.

WHY THIS EXISTS. `mutate.sh` has shipped a WRONG VERDICT four times, and every
one was invisible to careful reading and to CI:

  1. It judged each leg by grepping the tail line for the substring "failed".
     A mutation that breaks collection prints "1 error" and exits 2 — the guard
     fired, hard — but that text has no "failed" in it, so the harness reported
     THE GUARD DID NOT FIRE over a guard that worked.
  2. A replacement attempt lost `report_leg`'s diagnostic into a command
     substitution; caught only because someone re-ran the repro by hand.
  3. An 18-line multi-line-OLD guard shipped having been executed by nobody.
  4. Fixing (1) by trusting exit 2 unconditionally went too far the other way
     (issue #72): a mutation that makes the PYTHON MODULE UNDER TEST unparseable
     also exits 2 with "1 error", but there NOTHING ran — pytest never imported
     it. The harness printed MUTATION DEMONSTRATED over a guard that was never
     exercised. It had already shipped a false certification once, caught only
     by an engineer questioning the numbers (Skyy-Command PR #254).

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


def test_a_mutation_that_makes_the_module_under_test_unparseable_is_a_harness_error(
    sandbox: Path,
) -> None:
    """Issue #72 — the defect this fix closes.

    This exact scenario was ONCE pinned here as "still counts as the guard
    firing": mutating `subject.py` into a syntax error makes `test_subject.py`
    unable to import it, so pytest exits 2 with "1 error" and ZERO tests
    collected — identical to the crontab/YAML collection error below, but here
    nothing ran at all. Reading it as RED certifies a guard that was never
    exercised — the exact laundering that already shipped once, in
    Skyy-Command PR #254, where shell `::` splitting truncated a mutation
    string into a Python SyntaxError and the harness printed MUTATION
    DEMONSTRATED over a test that never ran.
    """
    r = run_mutate(sandbox, "THRESHOLD = 10", "THRESHOLD = (10")
    assert r.returncode == FAILED_OR_HARNESS_ERROR, (
        "a SyntaxError in the module under test was not caught as a harness "
        f"error — it is back to certifying a guard that never ran\n{r.stdout}{r.stderr}"
    )
    assert "HARNESS ERROR" in r.stderr
    assert "MUTATION DEMONSTRATED" not in r.stdout


def test_a_mutation_that_breaks_an_import_in_the_module_under_test_is_a_harness_error(
    sandbox: Path,
) -> None:
    """A second way exit 2 means "nothing ran", not caught by a syntax-only
    discriminator.

    Mutating a working import into one that does not exist is syntactically
    valid Python — `ast.parse` sees nothing wrong with it — but pytest still
    cannot import the module, so it exits 2 with "1 error" and zero tests
    collected: the identical shape to the SyntaxError case above. A
    discriminator that only checks syntax closes exit 2's SyntaxError half and
    leaves its ImportError half open — the same defect one step over.
    """
    (sandbox / "subject.py").write_text("import os\nTHRESHOLD = 10\n")
    r = run_mutate(sandbox, "import os", "import os_nonexistent_xyz_mutation_probe")
    assert r.returncode == FAILED_OR_HARNESS_ERROR, (
        "an import broken by the mutation was not caught as a harness error — it "
        f"is back to certifying a guard that never ran\n{r.stdout}{r.stderr}"
    )
    assert "HARNESS ERROR" in r.stderr
    assert "MUTATION DEMONSTRATED" not in r.stdout


def test_a_mutation_that_breaks_collection_via_a_DATA_file_still_counts_as_the_guard_firing(
    tmp_path: Path,
) -> None:
    """The case the exit-2-is-RED rule exists to defend, preserved through the
    fix for issue #72.

    A mutated DATA file (a crontab entry, a workflow YAML) can make a guard's
    OWN module-level parsing raise at collection time. pytest reports that
    identically to the broken-Python-source case above — same exit code, same
    "no tests collected" tail — but here $FILE itself (crontab.txt) is not
    Python and never became unparseable; the guard's own logic is what
    rejected the mutation. The fix's discriminator must still read this as the
    guard firing, not a harness error, or the crontab/YAML regression this
    file's history records (case 1 above) reopens.
    """
    (tmp_path / "crontab.txt").write_text("0 5 * * * /usr/bin/backup.sh\n")
    (tmp_path / "test_crontab_guard.py").write_text(
        "from pathlib import Path\n\n"
        "CRONTAB = Path(__file__).parent / 'crontab.txt'\n\n"
        "def _parse(text):\n"
        "    entries = []\n"
        "    for line in text.splitlines():\n"
        "        fields = line.split()\n"
        "        if len(fields) < 6:\n"
        "            raise ValueError(f'malformed crontab line: {line!r}')\n"
        "        entries.append(fields)\n"
        "    return entries\n\n"
        "# Parsed at COLLECTION time (module level), mirroring a guard whose own\n"
        "# parsing is what 'fires' on bad data.\n"
        "ENTRIES = _parse(CRONTAB.read_text())\n\n"
        "def test_backup_entry_present():\n"
        "    assert any('/usr/bin/backup.sh' in ' '.join(e) for e in ENTRIES)\n"
    )
    r = subprocess.run(
        [
            str(MUTATE), "crontab.txt",
            "0 5 * * * /usr/bin/backup.sh", "0 5 * * *",
            "test_crontab_guard.py",
        ],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=180,
    )
    assert r.returncode == DEMONSTRATED, (
        "a collection error caused by a malformed DATA file (not Python source) "
        f"was not counted as the guard firing\n{r.stdout}{r.stderr}"
    )


def test_a_package_relative_module_whose_guard_fires_is_not_blamed_on_the_mutation(
    tmp_path: Path,
) -> None:
    """The exit-2 discriminator must be DIFFERENTIAL, not absolute.

    The first fix for issue #72 asked "can this file be imported?" when the
    question it had to answer was "did the mutation change whether it can be?".
    Those are the same answer for any module that does not import standalone —
    and a module holding a relative import (`from .constants import BASE`) is
    exactly that shape: importing it by bare path raises "attempted relative
    import with no known parent package" with no mutation in play at all. 22
    modules in this repo are that shape, one of them a live mutate target with
    its own unit suite.

    So this is the Python analogue of the crontab case below: the guard fires
    HARD at collection, pytest exits 2, and the harness must read it as the
    guard firing. Reporting it as a harness error tells the engineer to fix a
    mutation that broke nothing — and per this file's header, a false negative
    is the direction that gets a WORKING GUARD DELETED.
    """
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "constants.py").write_text("BASE = 1\n")
    (tmp_path / "pkg" / "mod.py").write_text("from .constants import BASE\n\nLIMIT = BASE * 10\n")
    # The guard is at MODULE level, so it fires during collection — the whole
    # point. A guard inside a test function would exit 1 and prove nothing here.
    (tmp_path / "test_mod.py").write_text(
        "from pkg.mod import LIMIT\n\n"
        "if LIMIT != 10:\n"
        "    raise AssertionError(f'guard: LIMIT is {LIMIT}')\n\n\n"
        "def test_limit():\n"
        "    assert LIMIT == 10\n"
    )
    r = subprocess.run(
        [str(MUTATE), "pkg/mod.py", "BASE * 10", "BASE * 11", "test_mod.py"],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=180,
    )
    assert r.returncode == DEMONSTRATED, (
        "a guard that fired at collection on a package-relative module was read as "
        "a harness error — the discriminator is measuring whether the file imports "
        f"standalone, not whether the mutation changed that\n{r.stdout}{r.stderr}"
    )
    assert "MUTATION DEMONSTRATED" in r.stdout
    # The verdict alone is symmetric under the defect this test exists for: the
    # abstain fallback also yields DEMONSTRATED, so a probe that could not
    # import the package at all would pass on the line above while proving
    # nothing about prepend mode. The right answer here is that the probe
    # imported the module and found the mutation harmless.
    assert "does not import standalone" not in r.stderr, (
        "the probe ABSTAINED on a module it should be able to import — it is not "
        f"resolving the package root the way pytest's prepend mode does\n{r.stdout}{r.stderr}"
    )


def test_an_exit_2_the_discriminator_cannot_speak_to_falls_back_to_RED_and_says_so(
    tmp_path: Path,
) -> None:
    """When the baseline itself does not import, the probe must ABSTAIN.

    A module importable only with pytest's own conftest and sys.path setup in
    place gives the probe no usable baseline: "it does not import" is true
    before and after the mutation, so nothing can be attributed to the
    mutation. The harness must then fall back to exit-2-is-RED — the pre-#72
    behaviour, which is at worst as good as what shipped before — and it must
    SAY the discriminator abstained. A silent fallback hands back the old
    verdict wearing the new verdict's confidence, which is the more expensive
    of the two errors.
    """
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "helper.py").write_text("VALUE = 1\n")
    (tmp_path / "conftest.py").write_text(
        "import sys, pathlib\n"
        "sys.path.insert(0, str(pathlib.Path(__file__).parent / 'lib'))\n"
    )
    (tmp_path / "subject.py").write_text("import helper\nTHRESHOLD = 10\n")
    (tmp_path / "test_subject.py").write_text(
        "import subject\n\n\ndef test_t():\n    assert subject.THRESHOLD == 10\n"
    )
    r = subprocess.run(
        [str(MUTATE), "subject.py", "import helper", "import helper_gone", "test_subject.py"],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=180,
    )
    assert r.returncode == DEMONSTRATED, (
        "an exit 2 the discriminator cannot speak to did not fall back to RED — the "
        f"abstain path is stricter than the behaviour it replaced\n{r.stdout}{r.stderr}"
    )
    assert "does not import standalone" in r.stderr, (
        "the harness fell back to the pre-#72 verdict SILENTLY — the reader is given "
        f"no way to know the discriminator never spoke\n{r.stdout}{r.stderr}"
    )


def test_a_stale_bytecode_cache_cannot_answer_the_import_probe(sandbox: Path) -> None:
    """Issue #72 re-entering through its own fix.

    The probe was the one Python invocation in the script without its own
    `PYTHONPYCACHEPREFIX`, so it could be served bytecode compiled from
    DIFFERENT source than the one pytest just choked on: it reports "imports
    fine", the leg is classified RED, and the harness prints MUTATION
    DEMONSTRATED over a guard that never ran.

    The cache here is seeded in UNCHECKED_HASH mode rather than by racing the
    whole-second mtime window this file's header describes. Same defect, same
    read of the same shared cache — but deterministic, and a timing-dependent
    regression test for a timing bug is a flaky test, which is worse than none.
    """
    (sandbox / "subject.py").write_text("import os\nTHRESHOLD = 10\n")
    subprocess.run(
        [
            "python3", "-c",
            "import py_compile; py_compile.compile('subject.py', "
            "invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)",
        ],
        cwd=str(sandbox), check=True, capture_output=True, timeout=60,
    )
    assert list(sandbox.glob("__pycache__/subject.*.pyc")), "the cache seed did not take"

    r = run_mutate(sandbox, "import os", "import oq")
    assert "MUTATION DEMONSTRATED" not in r.stdout, (
        "a cached .pyc answered the import probe for a file pytest cannot import, and "
        f"the harness certified a guard that never ran — issue #72\n{r.stdout}{r.stderr}"
    )
    assert r.returncode == FAILED_OR_HARNESS_ERROR
    assert "HARNESS ERROR" in r.stderr


def test_the_import_probe_leaves_no_bytecode_in_the_working_tree(sandbox: Path) -> None:
    """The EXIT trap's contract is restore-on-any-path, and it does not clean
    `__pycache__`.

    An un-prefixed probe compiles the MUTATED source and writes the result next
    to `$FILE`. The trap restores the source and removes `$CACHE_ROOT`; that
    `.pyc` survives both, so the harness leaves bytecode from code nobody meant
    to ship in the tree — the exact harm the trap's own comment names.

    Scoped to `__pycache__` deliberately. `.pytest_cache` is also left behind,
    by every leg, on `main` as much as here — it holds no mutated source, so
    the trap's stated harm does not reach it. That is a separate observation
    about pytest's own cache, not this probe's.
    """
    (sandbox / "subject.py").write_text("import os\nTHRESHOLD = 10\n")
    r = run_mutate(sandbox, "import os", "import oz_nope")
    assert "HARNESS ERROR" in r.stderr, "the probe did not run, so this proves nothing"
    strays = list(sandbox.rglob("__pycache__"))
    assert not strays, (
        "the harness left bytecode compiled from the MUTATED source in the working "
        f"tree: {[str(p) for p in strays]}\n{r.stdout}{r.stderr}"
    )


def test_a_pytest_internal_error_is_a_HARNESS_ERROR_not_a_leg_result(sandbox: Path) -> None:
    """Exit 3 is `INTERNAL_ERROR` — pytest itself failed, never a test result.

    It cannot be read as a leg verdict: pytest's exit code carries no signal
    distinguishing an internal error raised before any test ran from one raised
    after, so the harness picks the fail-closed direction and aborts.

    This test exists because the reclassification and its dedicated message
    branch shipped having been executed by nobody — cause 3 in this file's own
    header, verbatim. The build pass recorded exit 3 as having no realistic
    repro; a `conftest.py` whose collection hook raises produces it in two
    lines, well inside the sandbox pattern every test here already uses.
    """
    (sandbox / "conftest.py").write_text(
        "def pytest_collection_modifyitems(items):\n"
        "    raise RuntimeError('a plugin hook blew up')\n"
    )
    r = run_mutate(sandbox, "THRESHOLD = 10", "THRESHOLD = 11")
    assert r.returncode == FAILED_OR_HARNESS_ERROR, f"{r.stdout}{r.stderr}"
    assert "HARNESS ERROR" in r.stderr
    assert "internal error" in r.stderr, (
        "exit 3 aborted without naming pytest's own failure as the cause, so the "
        f"reader is sent to check the mutation instead\n{r.stdout}{r.stderr}"
    )
    assert "MUTATION DEMONSTRATED" not in r.stdout


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

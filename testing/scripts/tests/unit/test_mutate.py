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
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
MUTATE = REPO_ROOT / "testing" / "scripts" / "mutate.sh"

# Exit codes are the harness's contract with its callers, so they are asserted
# by name rather than by magic number at each site.
#
# `NOT_DEMONSTRATED` and `HARNESS_ERROR` used to be one constant, named
# `FAILED_OR_HARNESS_ERROR` because both outcomes exited 1 and the code alone
# could not tell them apart. That name was the defect confessing itself: it is
# the harness reproducing, in its own contract with its callers, exactly the
# "one code, two opposite meanings" conflation it exists to refuse in pytest's.
# Every harness-error test below then had to grep stderr for "HARNESS ERROR" to
# say what it meant — reading a verdict out of text, which is how this script's
# first wrong verdict shipped (case 1 in the module docstring above).
DEMONSTRATED = 0
NOT_DEMONSTRATED = 1  # the suite RAN and the answer is no
REFUSED = 2  # refused before running anything; no verdict claimed
HARNESS_ERROR = 3  # the suite NEVER RAN, so there is no verdict

# The harness runs pytest three times per invocation, plus up to two import
# probes, all as real subprocesses. The bound is a hang backstop, not a
# performance target — a wedged leg must fail the suite rather than stall it.
# Named once here rather than repeated at each call site, matching
# `test_runner_discovery.py`'s `_RUNNER_TIMEOUT_S`.
_MUTATE_TIMEOUT_S = 180


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
        cwd=str(sandbox), capture_output=True, text=True, timeout=_MUTATE_TIMEOUT_S,
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
    exercised by nobody at all — and which THIS TEST did not exercise either
    for three further passes.

    Asserting only `returncode == REFUSED` made this test unable to fail. Delete
    the multi-line guard entirely and the run is still refused, by the AMBIGUITY
    guard one check further down: `grep -F` treats the embedded newline as
    separating alternate patterns (the mechanism the multi-line guard's own
    comment documents), so `grep -oF` counts BOTH fragments, the occurrence
    count is 2, and the ambiguity guard exits 2 — the same code, from a
    different check, for a different reason. Measured: 2.

    That is cause 3 in this module's header — "a guard shipped having been
    executed by nobody" — reproducing inside the test written to close it. So
    the refusal REASON is what must be asserted; the code alone is satisfied by
    a guard this test is not about.
    """
    r = run_mutate(sandbox, "THRESHOLD = 10\nLABEL", "THRESHOLD = 11\nLABEL")
    assert r.returncode == REFUSED, f"multi-line OLD was not refused\n{r.stdout}{r.stderr}"
    assert "must be single-line" in r.stderr, (
        "the run was refused, but by the AMBIGUITY guard rather than the multi-line "
        "guard this test names — so the multi-line guard is still exercised by "
        f"nobody and this assertion is the only thing that can tell\n{r.stdout}{r.stderr}"
    )


def test_an_empty_string_to_mutate_is_refused(sandbox: Path) -> None:
    """An empty OLD passes BOTH checks that look like they would catch it, and
    then certifies a guard against a mutation nobody asked for.

    `grep -qF -- ""` matches any file, so the presence check passes. `grep -oF
    -- ""` emits one empty match per LINE, so a single-line subject counts 1 and
    the ambiguity guard passes too. What reaches the applier is
    `.replace("", NEW, 1)`, which inserts NEW at offset 0 — measured end to end
    before the fix: `mutate.sh subject.py "" "ZZZ" test_subject.py` printed
    ✓ MUTATION DEMONSTRATED and exited 0, having broken the file's syntax at a
    location the caller never named.

    The realistic trigger is an unset variable in a caller's wrapper. `set -u`
    protects this script's own variables; it does not protect the caller's argv,
    and an empty positional argument is indistinguishable from a deliberate one.
    """
    (sandbox / "subject.py").write_text("THRESHOLD = 10\n")  # one line: count is 1
    r = run_mutate(sandbox, "", "ZZZ")
    assert r.returncode == REFUSED, (
        "an empty OLD was accepted — it prepends NEW at offset 0, so the mutation "
        f"measured is not the one requested\n{r.stdout}{r.stderr}"
    )
    assert "MUTATION DEMONSTRATED" not in r.stdout


def test_mutating_this_script_with_itself_is_refused(tmp_path: Path) -> None:
    """bash reads a script lazily by byte offset, so a running `mutate.sh`
    cannot be its own subject.

    The applier rewrites `$FILE` in place (truncate + rewrite, same inode). A
    length-changing self-mutation shifts every byte the running shell has not
    yet read, and it goes on to execute fragments from the old offsets — an
    unbounded confident-wrong-answer in the one tool that must not have one.

    This is not housekeeping. `mutate.sh` now has its own unit suite, and the
    Testing Standard's mutation-evidence rule makes it a natural target for
    itself; the refusal is what keeps the obvious next command from being the
    dangerous one.
    """
    local_copy = tmp_path / "m.sh"
    local_copy.write_bytes(MUTATE.read_bytes())
    local_copy.chmod(0o755)
    (tmp_path / "test_t.py").write_text("def test_t():\n    assert 1\n")
    r = subprocess.run(
        [str(local_copy), "m.sh", "set -euo pipefail", "set -uo pipefail", "test_t.py"],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=_MUTATE_TIMEOUT_S,
    )
    assert r.returncode == REFUSED, (
        "the harness accepted ITSELF as the mutation subject — bash re-reads the "
        f"running script by byte offset\n{r.stdout}{r.stderr}"
    )
    assert "this script itself" in r.stderr


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
    assert r.returncode == NOT_DEMONSTRATED
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
    assert r.returncode == HARNESS_ERROR, (
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
    assert r.returncode == HARNESS_ERROR, (
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
        cwd=str(tmp_path), capture_output=True, text=True, timeout=_MUTATE_TIMEOUT_S,
    )
    assert r.returncode == DEMONSTRATED, (
        "a collection error caused by a malformed DATA file (not Python source) "
        f"was not counted as the guard firing\n{r.stdout}{r.stderr}"
    )
    # The verdict alone is symmetric under the defect this test defends against:
    # the `abstain` fallback ALSO yields DEMONSTRATED, so if the `*.py` check
    # that selects `not-python` were removed, this test would still pass while
    # proving nothing about the branch it names. Its two sibling tests already
    # pin their branch this way.
    assert "does not import standalone" not in r.stderr, (
        "the discriminator ABSTAINED on a data subject instead of taking the "
        "not-python branch — the verdict is right by accident, via the pre-#72 "
        f"fallback rather than via the rule this test defends\n{r.stdout}{r.stderr}"
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
        cwd=str(tmp_path), capture_output=True, text=True, timeout=_MUTATE_TIMEOUT_S,
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


def test_a_package_init_file_is_imported_as_the_package_not_as_a_submodule(
    tmp_path: Path,
) -> None:
    """`pkg/__init__.py` is a legal mutate target and the probe must name it the
    way pytest does.

    pytest's `compute_module_name` drops a trailing `__init__`, so `pkg` is what
    gets imported. Keeping it makes the probe import `pkg.__init__`, which
    executes the package body TWICE in one interpreter — once implicitly as
    `pkg`, once as the submodule. A package carrying a register-once guard at
    import time then raises in the probe and nowhere else, and the probe
    abstains on precisely the targets most likely to hold such a guard: the
    prepend fix silently stops applying to them.

    The double-execution detector hangs off `sys`, not a module global, because
    the two executions produce two distinct module objects — a flag on either
    one cannot see the other.
    """
    (tmp_path / "holder").mkdir()
    (tmp_path / "holder" / "__init__.py").write_text(
        "import sys\n\n"
        'if getattr(sys, "_holder_executed", False):\n'
        '    raise RuntimeError("package body executed twice in one interpreter")\n'
        "sys._holder_executed = True\n\n"
        "LIMIT = 10\n"
    )
    # Module-level guard, so it fires at collection and the leg exits 2 — the
    # path the discriminator is consulted on.
    (tmp_path / "test_holder.py").write_text(
        "from holder import LIMIT\n\n"
        "if LIMIT != 10:\n"
        "    raise AssertionError(f'guard: LIMIT is {LIMIT}')\n\n\n"
        "def test_limit():\n"
        "    assert LIMIT == 10\n"
    )
    r = subprocess.run(
        [str(MUTATE), "holder/__init__.py", "LIMIT = 10", "LIMIT = 11", "test_holder.py"],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=_MUTATE_TIMEOUT_S,
    )
    assert r.returncode == DEMONSTRATED, f"{r.stdout}{r.stderr}"
    assert "does not import standalone" not in r.stderr, (
        "the probe ABSTAINED on a package it can import — it is importing "
        f"`holder.__init__` rather than `holder`\n{r.stdout}{r.stderr}"
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
        cwd=str(tmp_path), capture_output=True, text=True, timeout=_MUTATE_TIMEOUT_S,
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
    assert r.returncode == HARNESS_ERROR
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
    assert r.returncode == HARNESS_ERROR, f"{r.stdout}{r.stderr}"
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
    assert r.returncode == HARNESS_ERROR
    assert "HARNESS ERROR" in r.stderr
    assert "MUTATION DEMONSTRATED" not in r.stdout


def test_the_exit_code_alone_separates_a_verdict_from_a_non_measurement(sandbox: Path) -> None:
    """The harness's OWN exit code must not repeat the conflation it exists to
    refuse in pytest's.

    Both outcomes below used to exit 1, so a caller reading `$?` could not tell
    "the suite ran and your guard asserts nothing" — actionable, and the
    direction that gets a working guard DELETED — from "the suite never ran, so
    I have no opinion about your guard". The only way to separate them was to
    grep stderr for "HARNESS ERROR", and reading a verdict out of text is how
    this script's first wrong verdict shipped.

    Asserted from ONE sandbox and driven only by the mutation string, so the
    two paths differ in nothing but which outcome they reach. Deliberately
    makes no reference to stderr: the point is that the code alone suffices.
    """
    (sandbox / "subject.py").write_text("import os\nTHRESHOLD = 10\nLABEL = 'alpha'\n")

    # The suite ran; nothing asserts LABEL. A real measurement, answer "no".
    did_not_fire = run_mutate(sandbox, "LABEL = 'alpha'", "LABEL = 'omega'")
    # The mutation broke the import, so pytest never collected a test at all.
    never_ran = run_mutate(sandbox, "import os", "import os_nonexistent_xyz_probe")

    assert did_not_fire.returncode == NOT_DEMONSTRATED, (
        f"{did_not_fire.stdout}{did_not_fire.stderr}"
    )
    assert never_ran.returncode == HARNESS_ERROR, f"{never_ran.stdout}{never_ran.stderr}"
    assert did_not_fire.returncode != never_ran.returncode, (
        "a verdict about the guard and a refusal to give one share an exit code, so "
        "a caller reading $? cannot tell them apart — the harness is reproducing, in "
        "its own contract, the one-code-two-meanings defect it exists to close"
    )


def test_an_already_red_target_is_refused_before_mutating(sandbox: Path) -> None:
    """A mutation against a failing suite tells you nothing about the mutation."""
    (sandbox / "test_subject.py").write_text(
        "import subject\n\n\ndef test_threshold():\n    assert subject.THRESHOLD == 99\n"
    )
    r = run_mutate(sandbox, "THRESHOLD = 10", "THRESHOLD = 11")
    assert r.returncode == NOT_DEMONSTRATED
    assert "ALREADY RED" in r.stderr


# --------------------------------------------------------------------------
# Termination paths that reach no verdict.
#
# The exit-code contract is only worth as much as the paths it covers. Four
# passes classified the exits this script WRITES and none asked about the exits
# bash takes on its behalf: under `set -euo pipefail` every bare command is a
# termination path nobody wrote, and each used to exit with its own status —
# in practice 1, the code reserved for "the suite ran and the answer is no".
#
# These cases drive the MECHANISM from structurally different directions rather
# than enumerating the commands, because enumerating them is what failed: one
# review named five members, a second found seven plus the trap body itself.
# --------------------------------------------------------------------------

def test_a_crash_before_any_verdict_is_a_HARNESS_ERROR_not_a_leg_result(
    tmp_path: Path,
) -> None:
    """The mutation applier itself dies, after leg 1 has already passed.

    A DATA subject holding one non-UTF-8 byte is a supported input class — a
    data subject is the case the exit-2-is-RED rule exists to defend — and
    `p.read_text()` in the applier raises `UnicodeDecodeError` on it. Measured
    before the fix: leg 1 passed, the applier printed a bare traceback, leg 2
    never ran, and the harness exited 1. None of exit 1's three enumerated
    causes was true, and the "THE GUARD DID NOT FIRE" reading of that code is
    the one this file's header says gets a working guard deleted.

    Note what found this: running the tool on an input class the suite did not
    cover, not reading the diff. Every other case here drives a `.py` subject or
    a well-formed data subject — the suite tested what the harness DECIDES,
    thoroughly, and never what happens when it cannot get far enough to decide.
    """
    (tmp_path / "data.yaml").write_bytes(b"name: caf\xe9\nTHRESHOLD: 10\n")
    (tmp_path / "test_data.py").write_text(
        'def test_threshold():\n'
        '    assert b"THRESHOLD: 10" in open("data.yaml", "rb").read()\n'
    )
    r = subprocess.run(
        [str(MUTATE), "data.yaml", "THRESHOLD: 10", "THRESHOLD: 11", "test_data.py"],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=_MUTATE_TIMEOUT_S,
    )
    assert r.returncode == HARNESS_ERROR, (
        "the harness aborted without measuring anything and returned a code that "
        f"means it did measure\n{r.stdout}{r.stderr}"
    )
    assert "HARNESS ERROR" in r.stderr
    assert "MUTATION DEMONSTRATED" not in r.stdout


def test_a_failed_restore_outranks_any_reading_of_the_mutated_leg(sandbox: Path) -> None:
    """leg 2 GREEN + leg 3 RED must report the RESTORE failure, not the guard.

    The final case analysis used to test `MUTATED_VERDICT == GREEN` before it
    tested `AFTER_VERDICT`, so this exact combination printed "THE GUARD DID NOT
    FIRE" and the "THE TREE DID NOT RESTORE CLEANLY" branch was unreachable in
    the one combination that needed it. That is the expensive direction twice
    over: the message sends an engineer to delete a test, and it does so while
    leg 3 — the proof that the tree came back — has failed, which means no
    reading of leg 2 is trustworthy at all.

    Leg 3 is made red by a counter in `conftest.py` rather than by anything the
    mutation does, which is the point: the failure is in the CONTROL leg, and
    the harness must notice that before it interprets the measurement leg.
    """
    (sandbox / "conftest.py").write_text(
        "import pathlib\n\n"
        "_C = pathlib.Path(__file__).parent / 'runs.txt'\n\n\n"
        "def pytest_sessionstart(session):\n"
        "    n = int(_C.read_text()) if _C.exists() else 0\n"
        "    _C.write_text(str(n + 1))\n"
    )
    (sandbox / "test_subject.py").write_text(
        "import pathlib\n\n"
        "import subject\n\n\n"
        "def test_threshold():\n"
        "    runs = int((pathlib.Path(__file__).parent / 'runs.txt').read_text())\n"
        "    assert runs != 3, 'deliberately red on the restored leg'\n"
        "    assert subject.THRESHOLD == 10\n"
    )
    # LABEL is asserted by nothing, so leg 2 stays GREEN.
    r = run_mutate(sandbox, "LABEL = 'alpha'", "LABEL = 'omega'")
    assert "THE TREE DID NOT RESTORE CLEANLY" in r.stderr, (
        "leg 3 was red and the harness reported something else — the restore "
        f"failure is being masked by a reading of leg 2\n{r.stdout}{r.stderr}"
    )
    assert "THE GUARD DID NOT FIRE" not in r.stderr, (
        "a run whose control leg failed was reported as a missing guard, which is "
        f"the verdict that gets a working test deleted\n{r.stdout}{r.stderr}"
    )
    assert "MUTATION DEMONSTRATED" not in r.stdout


def test_a_restore_that_cannot_be_performed_is_loud_and_never_a_verdict(
    sandbox: Path,
) -> None:
    """The EXIT trap's own failure used to be discarded, twice over.

    The trap ran under the inherited `set -e`, so a failing `cp` aborted it at
    that command — skipping the rest of the cleanup AND its own classification,
    leaving the MUTATED tree on disk, printing nothing, and handing back `cp`'s
    status: 1. That is the defect this trap exists to close, wearing the fix.
    Measured directly in bash before writing the guard.

    `conftest.py` makes `subject.py` unwritable at the end of leg 2, so both the
    leg-3 restore and the trap's retry fail. The harness must say so — a
    mutated working tree is the harm its own contract calls worse than no
    harness at all — and must not emit a verdict code over it.
    """
    (sandbox / "conftest.py").write_text(
        "import pathlib\n\n"
        "_C = pathlib.Path(__file__).parent / 'runs.txt'\n\n\n"
        "def pytest_sessionfinish(session, exitstatus):\n"
        "    n = (int(_C.read_text()) if _C.exists() else 0) + 1\n"
        "    _C.write_text(str(n))\n"
        "    if n == 2:\n"
        "        (pathlib.Path(__file__).parent / 'subject.py').chmod(0o444)\n"
    )
    try:
        r = run_mutate(sandbox, "THRESHOLD = 10", "THRESHOLD = 11")
        assert r.returncode == HARNESS_ERROR, (
            "a failed restore produced a verdict code — leg 3 proves the tree came "
            f"back, and that proof did not happen\n{r.stdout}{r.stderr}"
        )
        assert "could not restore" in r.stderr, (
            f"the restore failed SILENTLY, which is the worst form of it\n{r.stdout}{r.stderr}"
        )
        assert "STILL MUTATED" in r.stderr, (
            "the operator was not told the working tree is still mutated, so the "
            f"next run tests code nobody meant to ship\n{r.stdout}{r.stderr}"
        )
        assert "MUTATION DEMONSTRATED" not in r.stdout
    finally:
        # Leave the sandbox writable so tmp_path teardown can clean it up.
        (sandbox / "subject.py").chmod(0o644)


def test_an_inherited_PYTEST_ADDOPTS_cannot_reopen_issue_72(sandbox: Path) -> None:
    """Issue #72's false certification, re-entering through an environment
    variable that the exit-code table did not account for.

    The table's load-bearing premise was "pytest interrupts to 2 on a collection
    error unless --continue-on-collection-errors, WHICH THIS HARNESS NEVER
    PASSES" — a statement about this script's argv, not about what pytest
    receives. `PYTEST_ADDOPTS` supplies it from the environment. MEASURED with
    that variable set: the SyntaxError mutation made pytest exit 1 instead of 2,
    the differential discriminator was never consulted, and the harness printed
    ✓ MUTATION DEMONSTRATED and exited 0 over a test that never ran.

    The remaining channel is a target repo's own `addopts` in pytest.ini /
    pyproject.toml, which no environment variable can clear; it is stated in the
    exit-code table and its precheck is placed as proposal C-73bf2gvm.
    """
    env = dict(os.environ, PYTEST_ADDOPTS="--continue-on-collection-errors")
    r = subprocess.run(
        [str(MUTATE), "subject.py", "THRESHOLD = 10", "THRESHOLD = (10", "test_subject.py"],
        cwd=str(sandbox), capture_output=True, text=True,
        timeout=_MUTATE_TIMEOUT_S, env=env,
    )
    assert r.returncode == HARNESS_ERROR, (
        "an environment variable changed pytest's exit code out from under the "
        "classifier and the harness certified a guard that never ran — issue #72 "
        f"through a channel the fix did not cover\n{r.stdout}{r.stderr}"
    )
    assert "MUTATION DEMONSTRATED" not in r.stdout


# --------------------------------------------------------------------------
# CLASS CHECKS — these key on the mechanism, not on the instances.
#
# Every previous pass on this script closed the defect it was shown and the
# next pass found a structurally adjacent one: exit 2's SyntaxError half, then
# its ImportError half; the probe's absolute-vs-differential shape, then the
# probe's own shared cache; the emitted 1-vs-3 conflation, then the emitted
# codes that never reach the classifier. Enumerating instances demonstrably
# does not converge here.
#
# So these three read the SOURCE and assert the invariants that make the next
# member safe without anyone finding it: that no exit can bypass the record,
# that the trap cannot die before it classifies, and that nothing runs in front
# of the trap. Each fails on a class member that does not exist yet.
# --------------------------------------------------------------------------

def _function_body_lines(lines: list[str], header: str) -> set[int]:
    """0-indexed line numbers spanned by a top-level `name() {` … `}` block.

    Closing brace matched at column 0, which is what makes this reliable without
    parsing bash: every nested brace in this file is indented.
    """
    start = next(i for i, line in enumerate(lines) if line.startswith(header))
    end = next(i for i in range(start + 1, len(lines)) if lines[i] == "}")
    return set(range(start, end + 1))



def _strip_comment(line: str) -> str:
    """Drop a trailing comment WITHOUT destroying `$#` or `${x#y}`.

    `line.split("#")[0]` was the previous spelling and it truncated any line
    containing a parameter expansion. `mutate.sh:147` is the arg-count guard —
    `[[ $# -eq 4 ]] || { …; verdict 2; }` — and it collapsed to `[[ $`, so the
    whole line, INCLUDING ITS VERDICT SITE, was invisible to every check built
    on this. A comment opens at start-of-line or after whitespace; a `#`
    preceded by `$` or a word character is part of an expansion.
    """
    import re as _re
    return _re.sub(r"(?:(?<=\s)|^)#.*$", "", line)


# A command may start at line start, after a separator, after `{`, or after a
# compound keyword. `then`/`else`/`do` were missing, so `if …; then exit 1; fi`
# — the single most natural way to write a guard — sailed past the funnel check.
_EXIT_IN_COMMAND_POSITION = re.compile(
    r"(?:^|[;&|{]|\bthen\b|\belse\b|\bdo\b)\s*exit\b"
)


def _bypasses_the_verdict_funnel(line: str) -> bool:
    return bool(_EXIT_IN_COMMAND_POSITION.search(_strip_comment(line)))


def test_the_funnel_detector_sees_both_shapes_it_was_blind_to() -> None:
    """POSITIVE CONTROL, and it exists because this check has been found blind TWICE.

    Once for anchoring at column 0, once for comment-stripping and `then`. A
    guard that has failed twice at seeing its own class does not get a third
    chance on trust — these probes fail the moment either blind spot returns.
    """
    must_flag = [
        "    exit 1",                                    # plain, indented
        "    foo || exit 1",                             # after a separator
        "    { exit 1; }",                               # after a brace
        "    if [[ -z $x ]]; then exit 1; fi",           # after `then` — BLIND SPOT 2
        "    while :; do exit 1; done",                  # after `do`
        "    [[ $# -eq 4 ]] || { helper; exit 2; }",     # holds `$#` — BLIND SPOT 1
    ]
    for probe in must_flag:
        assert _bypasses_the_verdict_funnel(probe), f"detector is blind to: {probe!r}"

    must_not_flag = [
        "    # exit 1 in a comment",
        "    verdict 2",
        "    echo 'exit'",
        "    [[ $# -eq 4 ]] || { helper; verdict 2; }",  # the real line 147
    ]
    for probe in must_not_flag:
        assert not _bypasses_the_verdict_funnel(probe), f"false positive on: {probe!r}"


def test_every_exit_is_a_declared_verdict() -> None:
    """No `exit` may bypass the `verdict` funnel.

    `on_exit` decides "did this path reach a verdict?" by comparing the actual
    exit status against the code `verdict` recorded. An `exit` written anywhere
    else leaves the record stale, and the trap then reports HARNESS ERROR over a
    real verdict — a false negative injected into the one tool whose expensive
    error is exactly that.

    This is the check that keeps the fix from decaying into the five hand-placed
    `if`-guards it replaced: it fails on the NEXT `exit` someone adds, wherever
    they add it, rather than waiting for a review pass to notice.
    """
    lines = MUTATE.read_text().splitlines()
    allowed = _function_body_lines(lines, "verdict() {") | _function_body_lines(lines, "on_exit() {")
    offenders = [
        (n + 1, line.strip())
        for n, line in enumerate(lines)
        # Strip comments, then match `exit` only where a command may start.
        # `^\s*` and not `^`: every exit worth catching is INDENTED inside a
        # function or an `if`, and an unanchored-to-column-0 pattern missed all
        # of them. Caught by mutating `verdict 3` back to `exit 3` in report_leg
        # and watching this test stay green — the check that guards the class
        # was itself in the class.
        if n not in allowed and _bypasses_the_verdict_funnel(line)
    ]
    assert not offenders, (
        "an `exit` bypasses the `verdict` funnel, so on_exit's record no longer "
        "describes reality and a genuine verdict will be reported as a harness "
        f"error: {offenders}"
    )


def test_no_function_called_in_a_subshell_reaches_verdict() -> None:
    """`verdict`'s FOURTH invariant, which was the only one nothing checked.

    Its doc block names four invariants and had three class checks. The fourth
    — *never call `verdict` from a subshell* — had none, and the block names the
    concrete site at risk: `classify_leg`, invoked inside `$(…)` by `report_leg`.

    WHY IT MATTERS: `verdict` records the exit code that `on_exit` later compares
    against `$?`. A `verdict` inside `$(…)` writes that record in a CHILD shell,
    where it evaporates — so the parent's record stays stale and the trap reports
    HARNESS ERROR over a real verdict. That is the exact false negative this
    whole funnel exists to prevent, arriving through the one door nothing
    watched.

    DERIVED, NOT ENUMERATED: the subshell-invoked set is read from the script, so
    a function that starts being called in `$(…)` is covered without editing this
    test. Naming `classify_leg` in a literal list would guard today's instance
    and miss tomorrow's.
    """
    lines = MUTATE.read_text().splitlines()
    source = "\n".join(_strip_comment(line) for line in lines)

    ours = set(re.findall(r"(?m)^([a-z_][a-z0-9_]*)\(\) \{", source))
    direct = {n for n in re.findall(r"\$\(\s*([a-z_][a-z0-9_]*)", source) if n in ours}

    # TRANSITIVE, not depth-1. The invariant is "no function REACHABLE inside a
    # command substitution", and a depth-1 check passes the moment the risky
    # call moves one frame down — `report_leg` calls `classify_leg` in `$(…)`,
    # and a `verdict` added to anything `classify_leg` calls is just as lost.
    # Closing over the call graph costs four lines and removes the whole class.
    called_in_subshell = set(direct)
    frontier = set(direct)
    while frontier:
        name = frontier.pop()
        body = _function_body_lines(lines, f"{name}() {{")
        for n in body:
            for callee in re.findall(r"(?:^|[;&|{]|\bthen\b|\belse\b|\bdo\b)\s*([a-z_][a-z0-9_]*)",
                                     _strip_comment(lines[n])):
                if callee in ours and callee not in called_in_subshell:
                    called_in_subshell.add(callee)
                    frontier.add(callee)
    assert direct, (
        "no function was found invoked in `$(…)` — the derivation stopped "
        "working and this check is now vacuous"
    )

    offenders = {}
    for name in sorted(called_in_subshell):
        body = _function_body_lines(lines, f"{name}() {{")
        hits = [n + 1 for n in sorted(body)
                if re.search(r"(?:^|[;&|{]|\bthen\b|\belse\b|\bdo\b)\s*verdict\b",
                             _strip_comment(lines[n]))]
        if hits:
            offenders[name] = hits

    assert not offenders, (
        "these functions are invoked inside `$(…)` and call `verdict`, so the "
        "exit-code record would be written in a subshell and lost, and on_exit "
        f"would report HARNESS ERROR over a real verdict: {offenders}"
    )


def test_the_exit_trap_cannot_abort_before_it_classifies() -> None:
    """`on_exit` must capture `$?`/`$BASH_COMMAND` first and disable errexit second.

    Both invariants are load-bearing and both were established by measurement,
    not by reading the manual:

      - `$?` and `$BASH_COMMAND` are destroyed by the trap's own first command,
        so the capture must precede everything, including any `echo` or `[[`.
      - the trap inherits `set -e`, so an unguarded failing command inside it
        aborts the trap — skipping the rest of cleanup and its own
        classification, and exiting with that command's status. That is how a
        failed restore silently became exit 1 with a mutated tree on disk.

    Asserted on the source rather than by execution because the failure is
    invisible at runtime until the exact command that fails is the one nobody
    guarded — which is the shape that has already shipped here twice.
    """
    lines = MUTATE.read_text().splitlines()
    body = sorted(_function_body_lines(lines, "on_exit() {"))
    # Trailing comments stripped: both statements below carry one explaining
    # why they must be where they are, and the invariant is about the command.
    statements = [
        re.sub(r"\s+#.*$", "", lines[i]).strip() for i in body[1:]
        if lines[i].strip() and not lines[i].strip().startswith("#")
    ]
    assert statements, "on_exit has no body"
    assert statements[0].startswith("local status=$?"), (
        "on_exit does not capture $? on its first statement, so the exit status it "
        f"classifies is its own, not the script's: {statements[0]!r}"
    )
    assert "$BASH_COMMAND" in statements[0], (
        "on_exit does not capture $BASH_COMMAND with $?, so the HARNESS ERROR "
        f"cannot name the command that failed: {statements[0]!r}"
    )
    assert statements[1] == "set +e", (
        "on_exit does not disable errexit as its second statement, so a failing "
        "command inside the trap aborts it before it classifies anything — the "
        f"exact defect it exists to close: {statements[1]!r}"
    )


def test_the_exit_trap_is_installed_before_anything_that_can_fail() -> None:
    """Nothing may run in front of the classifier.

    The previous trap was installed after `mktemp -d`, `mktemp` and the backup
    `cp`, because its body dereferenced the variables those commands set. Those
    three are exactly the commands that fail when `/tmp` fills, and a classifier
    installed behind them ships with a hole in front of it — a blind spot in the
    shape of the fix.

    `trap on_exit EXIT` must therefore precede the first command in the file
    that can fail. Everything it touches is pre-declared empty so `set -u`
    cannot trip inside a handler that runs on every path.
    """
    lines = MUTATE.read_text().splitlines()
    trap_at = next(i for i, l in enumerate(lines) if l.strip() == "trap on_exit EXIT")
    first_fallible = next(
        i for i, l in enumerate(lines)
        if re.match(r"^[A-Z_]+=\"\$\((mktemp|grep|python3)", l.strip()) or l.strip().startswith("cp ")
    )
    assert trap_at < first_fallible, (
        f"the EXIT trap is installed at line {trap_at + 1}, after a command that can "
        f"fail at line {first_fallible + 1} — every abort in between is unclassified"
    )


# --------------------------------------------------------------------------
# Cleanup. A harness that leaves a mutated tree behind is worse than no
# harness: the next run tests code nobody meant to ship.
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("old", "new", "case", "expected"),
    [
        ("THRESHOLD = 10", "THRESHOLD = 11", "success", DEMONSTRATED),
        ("LABEL = 'alpha'", "LABEL = 'omega'", "guard-did-not-fire", NOT_DEMONSTRATED),
        ("THRESHOLD = 10", "THRESHOLD = (10", "collection-error", HARNESS_ERROR),
        ("THRESHOLD = 999", "THRESHOLD = 1", "refused-before-mutating", REFUSED),
    ],
)
def test_the_file_is_restored_on_every_exit_path(
    sandbox: Path, old: str, new: str, case: str, expected: int
) -> None:
    """The expected exit code is asserted alongside the content, because the
    content check alone cannot fail for the right reason.

    An unchanged file is trivially "restored", so any run that refused BEFORE
    mutating satisfies the content assertion without exercising the trap at all.
    Pinning the code is what makes each row prove that the path it names is the
    path that actually ran — and the fourth row exists to state that the
    refusal case is restored-by-never-mutating, deliberately, rather than
    leaving it as an unlabelled way for the other three to pass vacuously.
    """
    before = (sandbox / "subject.py").read_text()
    r = run_mutate(sandbox, old, new)
    assert r.returncode == expected, (
        f"the {case} row did not take the path it names, so its restore check "
        f"proves nothing\n{r.stdout}{r.stderr}"
    )
    assert (sandbox / "subject.py").read_text() == before, (
        f"the tree was left mutated after the {case} path — the EXIT trap did not restore it"
    )


def test_show_failures_prints_the_names_and_changes_nothing_else(tmp_path):
    """A predicted count is only evidence when the partition is checkable.

    SIX independent reflections asked for this flag (tracked as C-45bhs5cm), and each
    of those passes built its own pytest runner to get what it prints — because
    "48 red" and "48 red, but a different 48" are the same number and different
    results. The names were always in LEG_OUTPUT; nothing printed them.

    The flag is PRINT-ONLY. This asserts both halves: the names appear, and the
    verdict and exit code are byte-for-byte what the same mutation produces
    without it. A flag that changed the experiment would be worse than no flag.
    """
    src = tmp_path / "m.py"
    src.write_text("VALUE = 1\n")
    test = tmp_path / "test_m.py"
    test.write_text(
        "import sys; sys.path.insert(0, r'%s')\n"
        "import m\n"
        "def test_value_is_one():\n"
        "    assert m.VALUE == 1\n" % tmp_path
    )

    plain = subprocess.run(
        ["bash", str(MUTATE), str(src), "VALUE = 1", "VALUE = 2", str(test)],
        capture_output=True, text=True)
    shown = subprocess.run(
        ["bash", str(MUTATE), "--show-failures", str(src), "VALUE = 1", "VALUE = 2", str(test)],
        capture_output=True, text=True)

    assert plain.returncode == shown.returncode, (
        f"--show-failures changed the exit code ({plain.returncode} -> "
        f"{shown.returncode}). It must be print-only."
    )
    assert "test_value_is_one" not in plain.stdout, (
        "the plain run already printed the failing test name, so this flag would "
        "be asserting something that already happens and could never fail"
    )
    assert "test_value_is_one" in shown.stdout, (
        "--show-failures did not print the failing test's name, which is the "
        "entire point of the flag"
    )


def test_an_unknown_flag_is_rejected_rather_than_read_as_a_filename(tmp_path):
    """`--typo file old new target` must not silently mutate a file named `--typo`.

    Flag parsing sits ahead of the positional contract, so a misspelling that
    fell through would shift every positional by one and the harness would report
    on the wrong file.
    """
    r = subprocess.run(
        ["bash", str(MUTATE), "--show-failure", "a", "b", "c", "d"],
        capture_output=True, text=True)
    assert r.returncode == 2, f"expected the usage verdict (2), got {r.returncode}"
    assert "unknown flag" in r.stderr.lower()

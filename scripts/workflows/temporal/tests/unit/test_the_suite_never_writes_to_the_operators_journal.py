"""Running the tests must not put anything in the operator's real journal root.

HOW THIS WAS FOUND, because it is the reason the check is shaped the way it is:
not by a failing assertion — every assertion passed throughout — but by looking
at `~/.local/state/claude-dot-files/journal/` after a suite run and finding
**twenty-four bags accumulated in one day**, one per `pytest` invocation. PR #99
wired bag-open into all eleven entrypoints, the unit modules that drive an
entrypoint's `main()` run it to test its preconditions, and nothing stood
between the two. Three consequences, none of which could go red:

  * **Durable state written outside `tmp_path`**, which the Testing Standard's
    fixture-placement rule forbids for exactly this reason — it survives the run.
  * **The integration tier was grading the unit suite's litter.**
    `test_a_real_bag_validates.py` reads whatever is under the real root and
    validates it *as a bag a real dispatch produced*. Most of what it found was
    made by the suite running two directories away.
  * **Phase 5's budget is measured over the whole root**, so running the tests
    would spend an operator's retention budget.

WHY THIS IS A SEPARATE FILE FROM THE FIXTURE THAT FIXES IT. The fixture
(`tests/conftest.py`) redirects `CONFIG_PATH`, which stops the modules that
drive an entrypoint — a population `test_the_population_this_sweeps_MATCHES_THE_
TREE` pins, so it is not restated here. It cannot stop a test that reaches past
`open_run_bag` and calls
`bag.open_bag(resolve_journal_root(), …)` itself, and it stops nothing at all if
somebody deletes it. So the fixture is the remedy and this is the CHECK, and the
check is keyed on the observable property — *did the real root change* — rather
than on the mechanism, because the mechanism is what varied all four times this
package leaked something.

⚠ WHAT IT DOES NOT COVER. It runs the modules that drive an entrypoint `main()`,
discovered by AST rather than listed, because those are the ones that can reach
bag-open. A test that writes to the real root without going through an entrypoint
and without being in that population is invisible here — the population is named
in the failure message so a reader hitting it learns the boundary.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
COMPONENT = REPO_ROOT / "scripts" / "workflows" / "temporal"
UNIT_DIR = COMPONENT / "tests" / "unit"

sys.path.insert(0, str(COMPONENT))

from modules.journal import journal_activities        # noqa: E402
from modules.journal.root import JournalRootError, resolve_journal_root  # noqa: E402


def _entrypoint_driving_modules() -> list[Path]:
    """Test modules that call `main(...)` on a module object.

    Discovered, not listed, for the reason every sweep in this tree is: a hand
    list covers what somebody remembered, and the module added next week is
    exactly the one that matters.

    KEYED ON THE CALL, NOT ON THE IMPORT SPELLING — and that correction is the
    reason this docstring is longer than the function. The first version
    required a MODULE-LEVEL `import run_<something>` and a call on that exact
    name. Three of the five modules that drive an entrypoint reach it another
    way: `test_plan_verify` imports `run_plan_verify` inside the test function,
    and `test_an_entrypoint_REFUSES_an_escaping_operator_path` and
    `test_triage_candidates_split` both go through `importlib.import_module`,
    which binds no name an AST import-scan can see. So the sweep ran two of
    five, its vacuity floor was green on the two, and the docstring above said
    the population was "discovered by AST rather than listed" — true of the
    mechanism and false about the result.

    That is the same defect as `test_a_census_guard_proves_its_own_predicate`'s
    original `_ROOTS` recogniser, one file over: a guard keyed on the SPELLING
    an author happened to choose rather than on the BEHAVIOUR being audited.
    Calling `.main(...)` on a module IS the behaviour, and a test cannot drive
    an entrypoint without doing it.

    ⚠ IT MATCHES ANY `<expr>.main(...)`, so a module calling `main` on
    something that is not an entrypoint joins the sweep. That costs one extra
    module in a subprocess run and buys no false green — the failure direction
    is toward sweeping too much, which for a litter check is the safe one.
    """
    found = []
    for path in sorted(UNIT_DIR.glob("test_*.py")):
        if path.name == Path(__file__).name:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:                       # pragma: no cover - collection catches it
            continue
        if _drives_an_entrypoint(tree):
            found.append(path)
    return found


def _drives_an_entrypoint(tree: ast.Module) -> bool:
    """Does this module call `main(...)` on a module object?

    EXTRACTED SO IT CAN BE CONTROLLED, which is the half that was missing. This
    predicate was rewritten today and its only evidence was that it produced the
    right answer against today's tree — which is exactly the evidence the
    version it replaced had, and that version was wrong by three modules. The
    Testing Standard's rule that a structural test must prove it fails when the
    property is absent applies to a predicate the moment it is rewritten, and
    this module's line in `test_a_census_guard_proves_its_own_predicate.
    _WITHOUT_A_CONTROL_YET` was a carve-out for code that PREDATED that rule.
    That premise lapsed when the predicate was rewritten, so the line is gone
    and `test_the_discovery_predicate_discriminates` below is what replaced it.
    """
    return any(isinstance(node, ast.Call)
               and isinstance(node.func, ast.Attribute)
               and node.func.attr == "main"
               for node in ast.walk(tree))


def _real_root() -> Path | None:
    """The root the OPERATOR'S config resolves to, read-only, or None if unusable.

    Deliberately reads the real `config.yaml` — the session fixture in
    `conftest.py` redirects `CONFIG_PATH`, and this check has to look past that
    redirect at the thing it is protecting.
    """
    real_config = Path(journal_activities._FLEET_ROOT) / "config.yaml"
    try:
        return resolve_journal_root(
            config=journal_activities.load_journal_config(real_config), create=False)
    except JournalRootError:
        return None


def _entries(root: Path | None) -> set[str]:
    if root is None or not root.is_dir():
        return set()
    return {p.name for p in root.iterdir()}


def test_the_redirect_fixture_is_actually_IN_FORCE() -> None:
    """The cheap half: catch the fixture being deleted, without spawning anything.

    `CONFIG_PATH` is what `open_run_bag` reads, so if it still points at the
    repo's own `config.yaml` while tests are running, every entrypoint a test
    drives writes to wherever the operator's journal actually is.
    """
    assert journal_activities.CONFIG_PATH != journal_activities._FLEET_ROOT / "config.yaml", (
        "the journal-root redirect in tests/conftest.py is not in force — a test "
        "that drives an entrypoint will create a bag in the operator's real "
        "journal root. That fixture is autouse and session-scoped; if it was "
        "removed, restore it rather than deleting this test.")


def test_the_population_this_sweeps_MATCHES_THE_TREE() -> None:
    """PINNED, NOT FLOORED, because the floor is what hid the narrowing.

    This used to be `assert modules` — non-empty. It was green while the
    recogniser found two of the five modules that drive an entrypoint `main()`,
    which is exactly what a floor cannot see: a sweep can lose most of its
    population and still be non-empty. The header said the population was
    "discovered by AST rather than listed" and the code found less than half of
    it, silently — the prose was the accurate half and nothing compared them.

    THE NUMBER LIVES HERE AND IN NO PROSE. Every sentence that used to carry it
    — this file's header, and the two comments in `tests/conftest.py` that
    explain why the redirect fixture exists — now names the population instead
    of counting it. "two of five" above is history and stays true whatever the
    count becomes.

    Failing here is not a defect — it is the census reporting that the
    population moved. Confirm the new module cannot litter the operator's
    journal root, then update this number.
    """
    modules = _entrypoint_driving_modules()
    assert len(modules) == 5, (
        f"{len(modules)} test module(s) under {UNIT_DIR} drive an entrypoint "
        f"`main()`; it was 5 when this was pinned. Found: "
        f"{[m.name for m in modules]}.\n"
        f"If a module was ADDED, it now runs inside the subprocess sweep below "
        f"and this number goes up. If the count DROPPED, the discovery "
        f"predicate has drifted from how these tests are written and the sweep "
        f"is quietly checking less than it claims — which is how it came to run "
        f"two of five.\n"
        f"THE COPY THAT GOES STALE INVISIBLY IS IN ANOTHER FILE: "
        f"`tests/conftest.py` explains the autouse redirect in terms of this "
        f"same population. Nothing derives it there and no gate reads it, so it "
        f"is the one to update in the same edit. This file's own header states "
        f"the population only as history — 'it ran two of five' — which stays "
        f"true whatever the number becomes.")


# --- positive controls -------------------------------------------------------
# Testing Standard § *Structural tests need a positive control*. Three real
# spellings and two negatives, as literal snippets the tree does not contain, so
# a predicate that started answering unconditionally fails HERE rather than
# passing forever against a population that happens to still be five.

_MODULE_LEVEL_IMPORT = """
import run_plan_draft
def test_it(tmp_path):
    assert run_plan_draft.main(["--dry-run"]) == 0
"""

_FUNCTION_LOCAL_IMPORT = """
def test_it(tmp_path):
    import run_plan_verify
    assert run_plan_verify.main([]) == 0
"""

_IMPORTLIB = """
import importlib
def test_it(tmp_path):
    kickoff = importlib.import_module("run_triage_candidates")
    assert kickoff.main(["--dry-run"]) == 0
"""

_IMPORTS_BUT_NEVER_DRIVES = """
import run_plan_draft
def test_it():
    assert run_plan_draft.SOME_CONSTANT == 3
"""

_A_BARE_LOCAL_MAIN = """
def main():
    return 0
def test_it():
    assert main() == 0
"""


def test_the_discovery_predicate_discriminates() -> None:
    """THE CONTROL. Three ways a test reaches an entrypoint, and two near-misses.

    The three positives are the three spellings that exist in this tree, and the
    first version of this predicate saw only the first of them. The negatives
    are the two shapes a reader would reasonably worry the widened match admits:
    a module that imports an entrypoint without driving it, and a bare local
    `main()` that is a `Name` call rather than an attribute access.
    """
    for label, snippet in (("module-level import", _MODULE_LEVEL_IMPORT),
                           ("function-local import", _FUNCTION_LOCAL_IMPORT),
                           ("importlib.import_module", _IMPORTLIB)):
        assert _drives_an_entrypoint(ast.parse(snippet)) is True, (
            f"a test driving an entrypoint by {label} was not seen — that is "
            f"the exact miss this predicate was rewritten to fix, and the "
            f"module would silently drop out of the swept population")

    assert _drives_an_entrypoint(ast.parse(_IMPORTS_BUT_NEVER_DRIVES)) is False, (
        "importing an entrypoint without calling `main` was read as driving "
        "it; the predicate has stopped looking at the call")
    assert _drives_an_entrypoint(ast.parse(_A_BARE_LOCAL_MAIN)) is False, (
        "a bare local `main()` was read as an entrypoint drive — it is a "
        "`Name` call, not an attribute access on a module, and admitting it "
        "would sweep modules that cannot reach bag-open at all")


@pytest.mark.skipif(os.environ.get("CDF_SKIP_SUBPROCESS_TESTS") == "1",
                    reason="explicitly disabled")
def test_running_the_entrypoint_tests_ADDS_NOTHING_to_the_operators_journal(
        tmp_path: Path) -> None:
    """THE REQUIREMENT, measured the only way it can be: run them and look.

    A subprocess rather than an in-process re-run, because the thing under test
    is what a fresh `pytest` does — the redirect is applied by a session fixture,
    and a session fixture already active in THIS process would mask exactly the
    regression this exists to catch.
    """
    root = _real_root()
    if root is None:
        pytest.skip("the configured journal root does not resolve here — nothing "
                    "for a test to pollute, and nothing to assert about")

    modules = _entrypoint_driving_modules()
    before = _entries(root)

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         *[str(m) for m in modules]],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
        env={**os.environ, "CDF_SKIP_SUBPROCESS_TESTS": "1"})

    after = _entries(root)
    created = sorted(after - before)

    # WHAT THIS OBSERVES IS A WINDOW, NOT AN AUTHOR, and the message says so.
    # The instrument is a set-difference over a directory the operator's own
    # dispatches also write to, so a background dispatch that opens a bag during
    # these ~3 seconds lands in `created` and is indistinguishable from litter.
    # The check is right and its old wording was not: it said the tests "created"
    # them, which is an attribution the measurement cannot support and which
    # sends a reader to fix a redirect fixture that is working. Narrowing by
    # mtime would not help — a concurrent bag is inside the window too.
    assert not created, (
        f"{len(created)} bag(s) APPEARED in the OPERATOR'S journal root {root} "
        f"while the entrypoint tests ran: {created[:5]}.\n"
        f"FIRST, RULE OUT A CONCURRENT DISPATCH. This is a window, not an "
        f"author — anything writing to that root during the run lands here. If "
        f"one of your own dispatches was live, re-run before investigating.\n"
        f"If it was the tests: a test must not leave durable state outside "
        f"tmp_path — and the integration tier reads this directory and "
        f"validates what it finds as though a real dispatch produced it, so "
        f"litter here is graded as evidence.\n"
        f"POPULATION SWEPT: {[m.name for m in modules]} — a module outside it "
        f"that writes here is invisible to this check.\n"
        f"Fix by redirecting the root (see the autouse fixture in "
        f"tests/conftest.py), never by deleting the bags.")

    assert result.returncode == 0, (
        f"the swept modules did not pass in a subprocess, so the assertion above "
        f"proved nothing — they may have failed before reaching bag-open.\n"
        f"{result.stdout[-2000:]}")

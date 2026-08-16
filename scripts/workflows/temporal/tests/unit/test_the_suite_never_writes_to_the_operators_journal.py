"""Running the tests must not put anything in the operator's real journal root.

HOW THIS WAS FOUND, because it is the reason the check is shaped the way it is:
not by a failing assertion — every assertion passed throughout — but by looking
at `~/.local/state/claude-dot-files/journal/` after a suite run and finding
**twenty-four bags accumulated in one day**, one per `pytest` invocation. PR #99
wired bag-open into all eleven entrypoints, five unit modules drive an
entrypoint's `main()` to test its preconditions, and nothing stood between the
two. Three consequences, none of which could go red:

  * **Durable state written outside `tmp_path`**, which the Testing Standard's
    fixture-placement rule forbids for exactly this reason — it survives the run.
  * **The integration tier was grading the unit suite's litter.**
    `test_a_real_bag_validates.py` reads whatever is under the real root and
    validates it *as a bag a real dispatch produced*. Most of what it found was
    made by the suite running two directories away.
  * **Phase 5's budget is measured over the whole root**, so running the tests
    would spend an operator's retention budget.

WHY THIS IS A SEPARATE FILE FROM THE FIXTURE THAT FIXES IT. The fixture
(`tests/conftest.py`) redirects `CONFIG_PATH`, which stops the five modules that
exist today. It cannot stop a test that reaches past `open_run_bag` and calls
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
    """Test modules that call `main(...)` on something imported from `scripts/`.

    Discovered, not listed, for the reason every sweep in this tree is: a hand
    list covers what somebody remembered, and the module added next week is
    exactly the one that matters.
    """
    found = []
    for path in sorted(UNIT_DIR.glob("test_*.py")):
        if path.name == Path(__file__).name:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:                       # pragma: no cover - collection catches it
            continue
        imported = {alias.asname or alias.name
                    for node in ast.walk(tree) if isinstance(node, ast.Import)
                    for alias in node.names if alias.name.startswith("run_")}
        drives = any(
            isinstance(node, ast.Call)
            and getattr(node.func, "attr", None) == "main"
            and getattr(node.func.value, "id", None) in imported
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name))
        if drives:
            found.append(path)
    return found


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


def test_the_population_this_sweeps_is_NOT_EMPTY() -> None:
    """A sweep over nothing passes every assertion below it."""
    modules = _entrypoint_driving_modules()
    assert modules, (
        f"no test module under {UNIT_DIR} was found driving an entrypoint "
        f"`main()`. Either the discovery predicate has drifted from how these "
        f"tests are written, or the tests that exercise entrypoint preconditions "
        f"are gone — both need looking at, and neither is 'nothing to check'.")


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

    assert not created, (
        f"running the entrypoint tests created {len(created)} bag(s) in the "
        f"OPERATOR'S journal root {root}: {created[:5]}.\n"
        f"A test must not leave durable state outside tmp_path — and the "
        f"integration tier reads this directory and validates what it finds as "
        f"though a real dispatch produced it, so litter here is graded as "
        f"evidence.\n"
        f"POPULATION SWEPT: {[m.name for m in modules]} — a module outside it "
        f"that writes here is invisible to this check.\n"
        f"Fix by redirecting the root (see the autouse fixture in "
        f"tests/conftest.py), never by deleting the bags.")

    assert result.returncode == 0, (
        f"the swept modules did not pass in a subprocess, so the assertion above "
        f"proved nothing — they may have failed before reaching bag-open.\n"
        f"{result.stdout[-2000:]}")

"""Component-scoped pytest configuration for the temporal workflow tree.

Puts the component root — the directory holding `modules/` — on `sys.path` so
tests import `modules.assistant.…` exactly as the runtime does.

This replaces the per-file `sys.path.insert(0, parents[1])` preamble the two
original test files each carried. One conftest instead of N copies means a test
file added later inherits the import path rather than having to remember the
incantation, and the path is identical for every test in the component rather
than depending on how deep the file happens to sit.
"""

from __future__ import annotations

import sys
from pathlib import Path

COMPONENT_ROOT = Path(__file__).resolve().parents[1]

if str(COMPONENT_ROOT) not in sys.path:
    sys.path.insert(0, str(COMPONENT_ROOT))

# `scripts/` holds the launch-concern modules — `preflight` and the run_* CLIs.
# An entrypoint gets this directory for free when Python runs it directly; a
# test importing the same module does not, and the preconditions in there are
# exactly the code that must be tested rather than trusted.
SCRIPTS_ROOT = COMPONENT_ROOT / "scripts"

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

# `tests/unit/` holds `review_run_fakes.py`, the shared harness both review_pr
# test modules import BY NAME. pytest's DEFAULT `prepend` import mode already
# puts this directory on the path as a side effect of collecting the tests in
# it — which is precisely why the coupling it replaced looked like it worked.
# `pytest.ini` pins `testpaths` and NOT `importmode`, so relying on that side
# effect makes the import mode load-bearing: `--import-mode=importlib` removes
# it and every consumer fails with an ImportError AT COLLECTION, which is the
# one failure `mutate.sh` reads as a caught mutation (issue #72). Declaring the
# path here makes the import a property of this component rather than of how
# pytest happened to be invoked.
UNIT_TESTS = Path(__file__).resolve().parent / "unit"

if str(UNIT_TESTS) not in sys.path:
    sys.path.insert(0, str(UNIT_TESTS))


# --- the journal root must never be the OPERATOR'S during a test run ---------------

# FOUND BY RUNNING THE SUITE AND THEN LOOKING AT THE OPERATOR'S HOME, which is the
# only way it could have been found: every assertion passed the whole time.
# PR #99 made all seventeen entrypoints open a journal bag, and the unit modules that
# drive an entrypoint's `main()` test its preconditions by running it — so each
# `pytest` run
# created REAL bags under `~/.local/state/claude-dot-files/journal/`. Twenty-four
# had accumulated in one day. Three separate consequences, none of them visible
# as a red test:
#
#   * durable state written outside `tmp_path`, which the Testing Standard's
#     fixture-placement rule forbids precisely because it survives the run;
#   * the integration tier reads that root and validates what it finds AS THOUGH
#     A REAL DISPATCH PRODUCED IT — so it was grading the unit suite's litter;
#   * Phase 5's budget is measured over the whole root, so a test suite run
#     would consume an operator's retention budget.
#
# REDIRECTED BY CONFIG AND NOT BY ENVIRONMENT, deliberately. Setting
# `XDG_STATE_HOME` would work only while `config.yaml`'s `journal.root:` is
# empty — the configured value wins over every default by design — so an operator
# who sets a root would silently lose the protection. Pointing `CONFIG_PATH` at a
# generated config is true regardless of what the real one says.
#
# AUTOUSE AND SESSION-WIDE BECAUSE THE DEFECT WAS OPT-OUT. A fixture each test
# had to remember is the same shape as the optional control this component's own
# requirement 11 exists to argue against: the modules that reach an entrypoint are
# a population `test_the_suite_never_writes_to_the_operators_journal.py` pins, and
# the NEXT one to be written is what this is for. The count is deliberately not
# restated here — this comment is where the previous one went stale unseen, because
# nothing in this file derives it and the journal prose gate excludes the shape.

import pytest  # noqa: E402


@pytest.fixture(autouse=True, scope="session")
def _journal_root_is_never_the_operators(tmp_path_factory):
    """Point every bag this suite opens at a temporary root, for the whole session.

    ⚠ AUTOUSE AND SESSION-SCOPED, WHICH MAKES *WHEN* YOU RESOLVE THE ROOT PART OF
    THE TEST'S MEANING. A test body runs INSIDE this fixture, so resolving the
    journal root there yields the sandbox above — never the operator's root. An
    integration test that means to read the REAL journal must resolve it at
    MODULE scope, which runs at collection time and therefore before any fixture.

    THE FAILURE IS A SKIP, WHICH IS WHY IT NEEDS SAYING HERE. The sandbox root
    does not exist until a bag is opened in it, so an in-body resolution raises
    `JournalRootError`; a tier that turns that into `pytest.skip` then reports an
    environment-sounding reason — "no journal on this machine" — on a machine
    holding a journal full of bags. A skip that is really a scoping bug and a
    skip that is really a fresh clone are indistinguishable in a summary table,
    and `run-all.sh` prints the same word for both.

    MEASURED TWICE. `tests/integration/test_a_real_bag_validates.py` resolves at
    module scope and carried no comment saying why, so the constraint survived as
    one file's habit. `tests/integration/test_citations_verify_offline.py` then
    shipped a tier that passed vacuously via skip on a machine holding bags, and
    was corrected the same way. Both depend on this fixture's scope; stating it
    at the fixture reaches the next such file, which neither of them can.
    """
    from modules.journal import journal_activities

    sandbox = tmp_path_factory.mktemp("journal-sandbox")
    config = sandbox / "config.yaml"
    config.write_text(f'journal:\n  root: "{sandbox / "journal"}"\n  deployment: user\n',
                      encoding="utf-8")

    real = journal_activities.CONFIG_PATH
    journal_activities.CONFIG_PATH = config
    try:
        yield sandbox / "journal"
    finally:
        journal_activities.CONFIG_PATH = real

# `tests/` on the path so a unit test can `from planning_corpus import ...`.
# The corpus moved to the sibling planning repo on 2026-08-31 and seventeen tests
# assert against the live one; they share ONE resolver rather than each deriving
# a path, because seventeen copies of "where is the corpus" is seventeen chances
# to be wrong about it.
import sys as _sys
from pathlib import Path as _Path
_TESTS = str(_Path(__file__).resolve().parent)
if _TESTS not in _sys.path:
    _sys.path.insert(0, _TESTS)

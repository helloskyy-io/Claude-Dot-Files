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
# PR #99 made all eleven entrypoints open a journal bag, and five unit modules
# drive an entrypoint's `main()` to test its preconditions — so each `pytest` run
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
# requirement 11 exists to argue against: five modules reach an entrypoint today
# and the sixth is what this is for.

import pytest  # noqa: E402


@pytest.fixture(autouse=True, scope="session")
def _journal_root_is_never_the_operators(tmp_path_factory):
    """Point every bag this suite opens at a temporary root, for the whole session."""
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

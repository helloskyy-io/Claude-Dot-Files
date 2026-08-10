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

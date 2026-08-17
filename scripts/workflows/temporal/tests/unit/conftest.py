"""Fixtures shared by the unit tier.

WHY HERE AND NOT IN `tests/conftest.py`. The component-level conftest one
directory up owns the IMPORT PATH — a property of the whole component, which is
why the Testing Standard names that location for it. A journal-root fixture is
not that: it is scaffolding three unit modules happen to need, and hoisting it
to the component root would put it in front of the integration tier, which
deliberately reads the REAL root rather than a temporary one.

WHY IT EXISTS AT ALL. The same four lines were pasted into `test_journal_bag`,
`test_journal_validator` and `test_journal_concurrent_writers`, and a fourth
copy in `test_journal_validator` had already drifted to a bare `0o700` literal
in a file that imports `DIR_MODE` for the other three. That is the shape this
package keeps finding in itself — the same rule written down N times, correct
until one copy is edited — so it gets one home rather than a fifth copy.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

# `modules.journal` is importable because `tests/conftest.py` put the component
# root on `sys.path`; this import is what makes the mode a shared constant
# rather than a literal each caller retypes.
from modules.journal.bag import DIR_MODE  # noqa: E402

assert sys.path, "component conftest must have run first"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A journal root for one test, created at the mode the contract requires.

    `DIR_MODE` RATHER THAN `0o700`, because requirement 9's mode is a property
    the code owns. A test that retypes the octal passes just as well when the
    contract changes, which makes it evidence of nothing.
    """
    journal = tmp_path / "journal"
    journal.mkdir(mode=DIR_MODE)
    return journal

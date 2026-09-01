"""Fixtures for the integration tier.

ONE `journal` FIXTURE, BECAUSE THE FOURTH COPY IS THE ONE THAT DRIFTS. This is
`tests/unit/conftest.py`'s argument at the tier below it, and that file records
what it cost there: the same four lines were pasted into three test modules and a
fourth copy had already drifted to a bare `0o700` literal, so a mode change would
have reached three files and silently missed one.

`tests/unit/conftest.py` is not reachable from here — pytest resolves conftest by
directory, and `tests/integration/` is a sibling — which is why this file exists
rather than the import that would obviously be cheaper.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.journal.bag import DIR_MODE


@pytest.fixture
def journal_root(tmp_path: Path) -> Path:
    """A journal root at the package's own directory mode, never a bare literal.

    `DIR_MODE` rather than `0o700` written out: the mode is the package's to
    state, and a test that hard-codes it stops testing the package's choice the
    moment the package changes it.
    """
    root = tmp_path / "journal"
    root.mkdir(mode=DIR_MODE)
    return root

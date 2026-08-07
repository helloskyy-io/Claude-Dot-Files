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

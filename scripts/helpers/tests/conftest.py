"""Component-scoped pytest configuration for scripts/helpers.

Puts `scripts/helpers/` on `sys.path` so tests import `check_settings`
exactly as `check-settings.sh` runs it — as a sibling script, not a package.
Mirrors `scripts/workflows/temporal/tests/conftest.py`'s pattern.
"""

from __future__ import annotations

import sys
from pathlib import Path

COMPONENT_ROOT = Path(__file__).resolve().parents[1]

if str(COMPONENT_ROOT) not in sys.path:
    sys.path.insert(0, str(COMPONENT_ROOT))

"""``python -m planning_ui`` — generate the views, or check they are current.

The entry point is a module rather than a console script because this package
is never installed: it is read out of the checkout it describes.
"""
from __future__ import annotations

import sys

from planning_ui.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

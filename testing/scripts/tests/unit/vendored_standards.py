"""Which files under `docs/standards/` are VENDORED MIRRORs, read off the script.

Three merge gates need this answer and each one had grown its own copy of the
parse:

  * `test_relative_links_resolve.py` EXEMPTS them — their links point into
    MDC-Master-Planning and do not resolve here.
  * `test_markdown_tables_render_whole.py` routes a failure on one of them
    UPSTREAM instead of prescribing a local edit.

IT IS THREE FILES, NOT A DIRECTORY, and that distinction is the whole reason
this module exists rather than a set literal. `standards/temporal/` also holds
LOCAL, editable files — the `README.md` applicability note and
`claude-dot-files-addendum.md` — and every gate that modelled the vendored set
as a directory name got those wrong. The documentation, research and testing
standards are OWNED by this planning repo and are not mirrors at all. `test_markdown_tables_render_whole.py` recorded making and
correcting that error in its own docstring; `test_relative_links_resolve.py` was
still making it, silently exempting all five from link checking, until this
module was extracted.

WHY DERIVED AND NOT LISTED: `scripts/helpers/vendor-standards.sh` is where the
set is actually declared and where `--check` reads it from, so a hand-kept copy
here would be exactly the stale declaration these gates exist to catch. Each
consuming module keeps its own vacuity assertion against `vendored_paths()`,
because what a wrong answer COSTS differs per gate and the message should say so.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]

import sys as _s  # noqa: E402
_s.path.insert(0, str(_REPO / "scripts" / "workflows" / "temporal" / "tests"))
from planning_corpus import PLANNING_ROOT  # noqa: E402

VENDOR_SCRIPT = _REPO / "scripts" / "helpers" / "vendor-standards.sh"

# `FILES=( "<owner>:<upstream-path>:<local-path>" ... )`. ONLY THE `MDC:` ENTRIES
# ARE MIRRORS HERE. An `SN:` entry is a standard this planning repo OWNS and
# mirrors OUT; its links must resolve in this tree and every gate that exempts
# a mirror must NOT exempt it. This parser read the owner prefix as part of the
# upstream path for ten days after the prefix appeared, so four owned standards
# were exempt from link checking and 22 dead links sat under a green suite
# (measured by MDC-PM3, 2026-09-14). The LOCAL half is what every consumer
# matches on.
_ENTRY = re.compile(r'^\s*"MDC:[^":]+:([^"]+)"', re.M)

# What the script declares today. Consumers assert against this so a parse that
# silently stops matching cannot quietly empty the set — see each gate's own
# vacuity test for what that would cost there.
EXPECTED = (
    "stateful_patterns.md",
    "temporal_standard.md",
    "worker_deployment_standard.md",
)


@lru_cache(maxsize=1)
def vendored_paths() -> frozenset[Path]:
    """The vendored mirrors, as RESOLVED absolute paths.

    Resolved so callers can compare against paths they built any way they like
    — `git ls-files` output joined onto the repo root, or a walk — without each
    one having to remember to normalise. Cached because
    `test_relative_links_resolve.py` consults this per link across the whole
    tree, and lazy (rather than a module-level constant) so an unreadable
    script fails inside the test that asks rather than at import, which would
    take the whole module's collection down with it.
    """
    text = VENDOR_SCRIPT.read_text(encoding="utf-8")
    return frozenset(
        (PLANNING_ROOT / "standards" / local).resolve()
        for local in _ENTRY.findall(text)
    )

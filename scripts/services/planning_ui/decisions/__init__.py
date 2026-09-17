"""The Decisions That Sit — every repo-resident store whose entries accumulate
unruled, as one page.

Five sources: the four ``tracked/`` stores, plus ``sprints.md § Sprint:
Unplaced``. All five are read from the checkout; **none is fetched**, and none
is written.

This package is the CONSUMER half of a seam whose producer is
``services/plan_extractor/``. That package owns the reader — §3 frontmatter
parsing, the §7 contract check, the ``sprints.md`` parser, the provenance stamp
and the derived orphan set. This one owns the **judgement**: *owes a ruling*
means something different in each of the five stores, and deriving it requires
§0's three-properties test, §4's per-store terminal states, §4.2's prune clock,
and reporting the contradictions they produce.

**This page rules on nothing.** It sets no ``decision:``, ``size:``,
``component:``, ``ready:`` or ``ratification:``; it schedules and retires
nothing; it edits ``sprints.md`` never. Reading is the entire relationship.

**And it cannot write.** ``tracked/operations/`` is reserved to humans by §1.2,
and §1.2 records that moving ``tracked/`` to the repo root took the store out of
every path-prefix write guard silently — so the protection is prose. The
guarantee here is structural instead: no module in this package holds a
file-opening call, and ``tests/unit/test_decisions_read_only.py`` proves it by
scanning the syntax tree, with a negative control showing the scan goes red when
a write is introduced. Requirement 6 is explicit that stated intent does not
satisfy it.

Entry points::

    from planning_ui.decisions import derive, render_markdown

    page = derive("/path/to/a/planning/repo")
    page.tables      # the five per-store tables
    page.crossings   # the four cross-store readings
    render_markdown(page)
"""

from .derive import PAGE_SCHEMA_VERSION, assemble, derive
from .model import DecisionsPage, Table
from .render import render_markdown

__all__ = [
    "DecisionsPage",
    "PAGE_SCHEMA_VERSION",
    "Table",
    "assemble",
    "derive",
    "render_markdown",
]

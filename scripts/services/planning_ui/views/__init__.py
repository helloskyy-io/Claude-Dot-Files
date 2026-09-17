"""The viewer's derived inputs — what the two diagram pages read.

Two views, one derivation. Both are computed from the :class:`ExtractionResult`
the graph, the report and the decisions page already share, never from a
second walk of the corpus, and both are emitted into ``development/derived/`` by
the same ``generate`` pass and gated by the same ``--check``
(`phase3_generated_diagrams.md` § What is committed).

**The graph is the artifact; the drawing is a reading of it.** Nothing here
computes a layout or a position — that happens in the browser, at the depth
the reader chose. What IS derived here is what a browser should not have to
re-derive from 620 edges on every load:

- :mod:`.neighbourhood` — the component-level dependency graph, every phase
  edge rolled up to the component that owns the phase, with its state kept.
- :mod:`.sprint_board` — per sprint, its items and the directed edges among
  them, derived from what each item schedules.

**Colour is derived, never authored.** Every state carried here is copied off
the edge or the accounting row the extractor derived; this package holds no
opinion about whether a dependency is satisfied.
"""
from __future__ import annotations

from typing import Any

from planning_ui.plan_extractor import ExtractionResult

# `neighbourhood()` — the depth query — is deliberately NOT re-exported: a
# package attribute named like a submodule shadows it, so
# `import planning_ui.views.neighbourhood as nb` would bind the function. Import
# the query from the submodule.
from .neighbourhood import component_index, state_counts
from .sprint_board import sprint_boards

#: Contract version of ``view-inputs.json``. Distinct from the graph's schema
#: version: the two files are consumed by different readers.
VIEW_SCHEMA_VERSION = "1"


def assemble_views(result: ExtractionResult) -> dict[str, Any]:
    """The ``view-inputs.json`` shape, from the one derivation."""
    return {
        "schema_version": VIEW_SCHEMA_VERSION,
        "provenance": dict(result.graph["provenance"]),
        "state_counts": state_counts(result.graph),
        "neighbourhood": component_index(result.graph),
        "sprints": sprint_boards(result),
    }


__all__ = [
    "VIEW_SCHEMA_VERSION",
    "assemble_views",
    "component_index",
    "sprint_boards",
    "state_counts",
]

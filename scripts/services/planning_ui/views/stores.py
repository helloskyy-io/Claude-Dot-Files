"""The four tracked stores as a viewer input.

**A SECOND artifact, deliberately.** ``view-inputs.json`` is derived from the
whole corpus, so every planning commit in every lane rewrites it; the store
rows change on a different rhythm — a triage ruling, an intake drain — and are
read by one page. Putting them in the same file would make every lane's diff
carry four hundred rows that lane did not touch, and would make the graph
pages wait on data they never draw.

**Nothing is re-derived here.** The tables come from the same
:func:`planning_ui.decisions.assemble` call the committed markdown page renders
from, so the page and the artifact are two renderings of one reading. Parsing
the markdown back into rows would be a second implementation that drifts.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from planning_ui.decisions import assemble
from planning_ui.plan_extractor import ExtractionResult

#: Contract version of ``view-stores.json``. Its own, because it is consumed
#: by one page and versions independently of the graph views.
STORES_SCHEMA_VERSION = "1"


def assemble_stores(result: ExtractionResult, as_of: date | None = None) -> dict[str, Any]:
    """The ``view-stores.json`` shape.

    ``as_of`` is the reference date the "how long it has sat" columns count
    back to, and it is threaded from the caller rather than defaulted here:
    two artifacts written in one pass that each took their own "today" would
    disagree at midnight, and ``--check`` reads the date back off the
    committed page to compare like with like.
    """
    page = assemble(result, as_of)
    return {
        "schema_version": STORES_SCHEMA_VERSION,
        "provenance": dict(result.graph["provenance"]),
        **page.to_dict(),
    }

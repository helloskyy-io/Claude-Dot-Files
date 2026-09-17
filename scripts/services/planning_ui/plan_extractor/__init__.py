"""The plan extractor — reads the planning corpus, derives a graph, reports
every place the corpus disagrees with itself.

A pure function of a checkout: no service, no database, no network call.
:func:`extract` returns the ``plan-graph.json`` shape and every finding; writing
is ``cli.py``'s alone, which commits what this returns at ``development/derived/``
and carries the ``--check`` that fails when it drifts (`repo_layout.md` §1.1).

Entry points::

    from planning_ui.plan_extractor import extract, render_markdown

    result = extract("/path/to/a/planning/repo")
    result.graph          # the plan-graph.json shape
    render_markdown(result)  # the consistency report

Nothing in this package imports Django, which is what makes requirement 1
("emitted from a plain checkout") testable rather than asserted.
"""

from .extractor import ExtractionResult, GRAPH_SCHEMA_VERSION, SECTION_ORDER, extract
from .report import render_markdown
from .tracked import CONTRACT_VERSION, ContractMismatch

__all__ = [
    "CONTRACT_VERSION",
    "ContractMismatch",
    "ExtractionResult",
    "GRAPH_SCHEMA_VERSION",
    "SECTION_ORDER",
    "extract",
    "render_markdown",
]

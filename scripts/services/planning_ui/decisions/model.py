"""Data model for The Decisions That Sit.

One shape for every table on the page — the five per-store tables and the four
cross-store readings — because a reader who learns one table has learned all
nine, and a renderer written once cannot render two of them differently.

**Nothing in this package writes.** The proof is structural and asserted by
``tests/unit/test_decisions_read_only.py`` rather than stated here: requirement
6 is explicit that intent does not satisfy it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from planning_ui.plan_extractor.model import Finding, Provenance

# ---------------------------------------------------------------------------
# Finding codes owned by this page
# ---------------------------------------------------------------------------
#
# UPPER_SNAKE_CASE, continuing the plan extractor's vocabulary. Codes this page
# does NOT own are consumed from the extractor rather than re-emitted — the
# orphan disagreements table 5 checks against are `ORPHAN_NOT_DECLARED` and
# `DECLARED_NOT_ORPHAN`, derived once, in the module that owns the derivation.
# Two derivations of one question is how two answers to it get onto one page.

#: An item holds a §4 terminal state while still owing a ruling. The
#: `adopted`-with-blank-`size` case is the named instance; the class is wider.
#:
#: **Ruled by the operator 2026-09-02: reported, never smoothed.** `decision:`
#: is set from code by `triage-candidates`, so a contradictory item is evidence
#: of a tooling defect or of hand-editing predating the standards now governing
#: these files. The fix belongs at the SOURCE — the item's own file, manually
#: reset so it gets a fresh evaluation. A display-layer rule mapping the
#: contradiction onto "owing triage" would hide the very defect this page
#: exists to expose, and would let pre-standards residue render tidily forever.
DECISION_CONTRADICTION = "DECISION_CONTRADICTION"

#: §0's third property, measured: an item that has survived three consecutive
#: triage passes without a ruling is itself a finding, "reported at the next
#: standup — not carried silently a fourth time". It requires history across
#: passes, which no item file records.
EXIT_TEST_FAILED = "EXIT_TEST_FAILED"

#: §0's second property, measured: a store whose triage gate is not open has no
#: cadence in fact, whatever §4 states. A store missing any of the three §0
#: properties is out of conformance.
STORE_CADENCE_ABSENT = "STORE_CADENCE_ABSENT"

#: A § Sprint: Unplaced entry whose staleness cannot be derived, because the
#: entry links no document the derivation can check it against. Reported rather
#: than rendered as a confident "still true" — which is the whole point of the
#: column.
UNPLACED_STALENESS_UNDERIVABLE = "UNPLACED_STALENESS_UNDERIVABLE"

#: History was unavailable (no `.git`, no `git` binary), so every column derived
#: from it is absent. Reported once and loudly: a page silently missing its age
#: columns reads as a page whose items have all just been filed.
HISTORY_UNAVAILABLE = "HISTORY_UNAVAILABLE"

#: The section this page's own findings are grouped under.
SECTION_DECISIONS = "what the page could not rule on cleanly"


@dataclass(frozen=True)
class Column:
    """One table column.

    ``derived`` marks the columns requirement 2 binds — the ones the source
    document cannot carry. It is rendered on the page, so a reader can see which
    half of each row is arithmetic and which half is transcription. Without the
    mark the requirement is satisfiable by assertion, which is how a re-render
    of files a reader could already open ends up claiming to be a derivation.
    """

    key: str
    label: str
    derived: bool = False


@dataclass(frozen=True)
class Row:
    cells: dict[str, str]
    source: Provenance

    def to_dict(self) -> dict[str, Any]:
        return {"cells": self.cells, "file": self.source.file, "line": self.source.line}


@dataclass
class Table:
    """One table, carrying its own definition of what *owes a ruling* means.

    ``owes_definition`` is rendered ON the page, per requirement 1 — the phrase
    means something different in each of the five stores, and a table that does
    not say which meaning it used is asking the reader to guess.

    ``scanned`` and ``suppressed`` are rendered beside the row count for the
    same reason the extractor reports what it could not parse: a short table and
    an empty store are otherwise indistinguishable, and only one of them is good
    news.
    """

    key: str
    title: str
    source: str
    owes_definition: str
    columns: list[Column]
    rows: list[Row] = field(default_factory=list)
    scanned: int = 0
    suppressed: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "source": self.source,
            "owes_definition": self.owes_definition,
            "columns": [
                {"key": c.key, "label": c.label, "derived": c.derived} for c in self.columns
            ],
            "rows": [row.to_dict() for row in self.rows],
            "scanned": self.scanned,
            "suppressed": self.suppressed,
            "notes": self.notes,
        }


@dataclass
class DecisionsPage:
    """The whole page: five store tables, four cross-store readings, findings."""

    provenance: dict[str, Any]
    tables: list[Table]
    crossings: list[Table]
    findings: list[Finding]
    halted: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance": self.provenance,
            "tables": [t.to_dict() for t in self.tables],
            "crossings": [t.to_dict() for t in self.crossings],
            "findings": [f.to_dict() for f in self.findings],
            "halted": self.halted,
        }

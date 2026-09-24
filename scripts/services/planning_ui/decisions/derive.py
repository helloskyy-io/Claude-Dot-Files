"""Assemble The Decisions That Sit — five tables, four cross-store readings.

A pure function of a checkout and one date. **No network call**, no database.
The page is committed at ``development/derived/`` by ``cli.py`` and staleness-
gated by ``--check`` — `repo_layout.md` §1.1's committed-and-gated pairing.

:func:`assemble` takes an :class:`~planning_ui.plan_extractor.ExtractionResult`, so
the CLI derives the corpus ONCE and renders all four artifacts from it;
:func:`derive` is the one-call convenience that extracts and assembles.

**The §7 contract check runs before this page is assembled**, because
:func:`plan_extractor.extract` runs it while reading the stores. A store whose
shape no longer matches the expected §3 core halts the run and this function
renders the mismatch instead of the tables — never a shorter table that reads as
a complete one.

Nothing here imports Django, which is what makes "generated from a plain
checkout" testable rather than asserted.
"""

from __future__ import annotations

from datetime import date, timezone, datetime
from pathlib import Path

from planning_ui.plan_extractor import ExtractionResult, extract
from planning_ui.plan_extractor.model import Collector, Finding, Provenance
from planning_ui.plan_extractor.sprints import SPRINTS_REL
from planning_ui.plan_extractor.tracked import CONTRACT_VERSION, STORES

from . import crossings, tables
from .history import read_history
from .model import HISTORY_UNAVAILABLE, SECTION_DECISIONS, DecisionsPage

#: Contract version of the emitted page shape. Distinct from the Tracked Items
#: §7 contract, which versions the STORES this page reads.
PAGE_SCHEMA_VERSION = "1"


def derive(corpus_root: str | Path, as_of: date | None = None) -> DecisionsPage:
    """Read the checkout and assemble the page — extract, then :func:`assemble`."""
    return assemble(extract(corpus_root), as_of)


def assemble(result: ExtractionResult, as_of: date | None = None) -> DecisionsPage:
    """Assemble the page from a derivation already made.

    ``as_of`` is the reference date the "how long it has sat" columns count back
    to. It defaults to today in UTC and is **injectable**, which is what lets the
    determinism test pin it: two runs on an unchanged checkout produce
    byte-identical output, and the only value in the artifact that is not a pure
    function of the checkout is this one date, stated on the page — which is
    also what lets ``--check`` read it back off the committed page and compare
    like with like.
    """
    root = result.root
    reference = as_of or datetime.now(tz=timezone.utc).date()

    findings: list[Finding] = [
        f for f in result.findings if f.section == "tracked-store findings"
    ]

    provenance = dict(result.graph["provenance"])
    provenance["page_schema_version"] = PAGE_SCHEMA_VERSION
    provenance["as_of"] = reference.isoformat()

    if result.halted:
        # The tables are absent rather than short. §7 exists because an
        # unversioned contract between two repos was discovered as a failed
        # dispatch, three times in three days.
        return DecisionsPage(
            provenance=provenance,
            tables=[],
            crossings=[],
            findings=findings,
            halted=result.halted,
        )

    history = read_history(root, tuple(sorted(STORES)), SPRINTS_REL)
    # An item being ADDED by the commit this hook is regenerating for has no
    # commit touching it yet. Seeded from its own `filed:` so the page does not
    # arrive stale and need a second, empty commit to settle. See
    # `History.seed_uncommitted`.
    history.seed_uncommitted(result.stores.all_items())
    if not history.available:
        findings.append(
            Finding(
                code=HISTORY_UNAVAILABLE,
                section=SECTION_DECISIONS,
                summary=(
                    "the checkout carries no readable git history, so every "
                    "how-long-it-has-sat and triage-pass column is absent"
                ),
                # The checkout root, named repo-relatively: an absolute path
                # here would make the page differ by checkout location, which
                # is the one thing a committed artifact must not do.
                provenance=Provenance("."),
                expected="a git checkout of the planning corpus",
                detail=(
                    "Reported rather than rendered as zero. A page silently missing its "
                    "age columns reads as a page whose items have all just been filed, "
                    "which is the opposite of what an absent history means."
                ),
            )
        )
    elif not history.blame_available:
        # The asymmetric half. The log succeeding and the blame failing leaves
        # table 5's age column entirely dashed while every other table's is
        # populated — which reads as "nobody has touched § Sprint: Unplaced
        # recently", the exact opposite of "we could not find out".
        findings.append(
            Finding(
                code=HISTORY_UNAVAILABLE,
                section=SECTION_DECISIONS,
                summary=(
                    f"`git blame` on `{SPRINTS_REL}` could not be read, so table 5's "
                    "how-long-it-has-sat column is absent while every other table's is not"
                ),
                provenance=Provenance(SPRINTS_REL),
                expected=f"`{SPRINTS_REL}` committed in the checkout",
                detail=(
                    "The per-ENTRY age in table 5 comes from blame, not from the file's "
                    "own history — a file-level date would make every entry as old as the "
                    "most recent edit anywhere in the document, erasing the signal the "
                    "section was built to expose."
                ),
            )
        )

    # One collector, for the anchor resolution table 3 performs. Its findings are
    # the plan extractor's own vocabulary (an unreadable target file), so they
    # join the tracked-store findings rather than becoming a new code.
    collector = Collector()

    page_tables = [
        tables.build_candidates(root, result.stores, history, reference, findings),
        tables.build_issues(result.stores, result.sprint_doc, history, reference, findings),
        tables.build_standards(
            root, result.stores, history, reference, collector, findings
        ),
        tables.build_operations(result.stores, history, reference, findings),
        tables.build_unplaced(
            result.sprint_doc,
            result.components,
            result.derived_orphans,
            result.declared_orphans,
            history,
            reference,
            findings,
        ),
    ]

    close_out_name, _line = tables.next_close_out(result.sprint_doc)
    page_crossings = [
        crossings.triage_queue(result.stores, history, reference),
        crossings.prune_clock(result.stores, history, reference),
        crossings.exit_test(result.stores, history, findings),
        crossings.store_conformance(
            result.stores, history, bool(close_out_name), findings
        ),
    ]

    findings.extend(collector.findings)

    return DecisionsPage(
        provenance=provenance,
        tables=page_tables,
        crossings=page_crossings,
        # ONE ordering, so the rendered page and the JSON carry the same worklist
        # in the same order. Sorting on the finding's own fields keeps it stable
        # across runs regardless of the order the tables happened to append in.
        findings=sorted(
            findings, key=lambda f: (f.provenance.file, f.provenance.line, f.code, f.summary)
        ),
        halted="",
    )


__all__ = ["PAGE_SCHEMA_VERSION", "CONTRACT_VERSION", "DecisionsPage", "assemble", "derive"]

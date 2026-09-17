"""Phase documents are read for ONE thing: a dependency marker they must not carry.

Rule 9 names one carrier — the roadmap. *"A phase doc does not restate its
dependencies; where it needs to discuss one it cites the roadmap entry."* A
``**Depends on:**`` line inside a phase document is therefore a finding for the
document's owner, naming the roadmap entry that should carry the declaration
instead.

**The line is reported and NEVER read as an edge.** The tempting fix is to
parse it too, so a dependency recorded only here is not lost. That makes the
phase document a second authoring surface — the drift rather than the fix —
and it is the reasoning already recorded on ``tracked/candidates/C-of5igont``.
Whatever the line says, the roadmap is the input.

Three findings can leave one line, and they are separate rows because they are
separate decisions: the one-carrier violation (move it), a qualified
standalone token (``Nothing hard`` — rule 9 makes a qualifier a finding, not a
declaration), and a phase cited by number in a link's text (``Phase 0`` — rule
4). Bundling them hands an owner three decisions in one row. **The by-number
predicate is :data:`~.dependencies.BY_NUMBER_RE`, and the roadmap walker runs
it over every declaration it parses** — it used to be defined here alone, so
the guard fired on the surface rule 9 exempts and never on the one it binds.

**What this reader does NOT look at**, stated so the next reader does not assume
coverage it lacks: a marker that is not line-initial — ``- **Dependencies:**
sub-item 2 complete`` is a SUB-ITEM's field inside a phase's own decomposition,
not a restatement of the phase's dependencies, and reporting it as a
one-carrier violation would be a false finding class that trains readers to
ignore the section. Both spellings ARE read, because the roadmap reader reads
both and two walkers disagreeing about what a marker is was the defect the
shared predicate was extracted to close.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import corpus_io
from .dependencies import BY_NUMBER_RE
from .model import (
    DEPENDENCY_CITES_BY_NUMBER,
    DEPENDENCY_IN_PHASE_DOC,
    DEPENDENCY_QUALIFIED_NONE,
    SECTION_DEPENDS_GRAPH,
    Collector,
    Provenance,
)
from .roadmaps import Component, PhaseRef, declaration_blocks
from .sprints import LINK_RE

#: The standalone token, in the ratified spelling and the one it replaced.
#: ``nothing`` is admitted alongside ``NONE`` because every live qualified
#: instance writes it. A line that starts with the token and is NOT the bare
#: token (``_BARE_TOKEN_RE``, ``NONE_RE``'s shape in both spellings) is
#: qualified. Checking against ``NONE_RE`` alone reported a bare ``nothing`` —
#: the pre-2026-09-07 spelling, unqualified — as *"silent about whatever the
#: qualifier excludes"* when there was no qualifier at all.
_TOKEN_RE = re.compile(r"^(?:NONE|nothing)\b", re.IGNORECASE)
_BARE_TOKEN_RE = re.compile(r"^(?:NONE|nothing)\s*(?:[.;,)\]]|$)", re.IGNORECASE)


def report_phase_doc_markers(
    root: Path,
    phase_paths: set[str],
    components: list[Component],
    collector: Collector,
) -> int:
    """Report every line-initial dependency marker in every phase document.

    Returns the number of documents reported, so the extractor can carry the
    count beside the rows. One ``DEPENDENCY_IN_PHASE_DOC`` row per document
    naming every offending line; one ``DEPENDENCY_QUALIFIED_NONE`` and one
    ``DEPENDENCY_CITES_BY_NUMBER`` row per line that has the defect.
    """
    entry_by_path: dict[str, tuple[Component, PhaseRef]] = {}
    for component in components:
        for ref in component.owned:
            if ref.path:
                entry_by_path[ref.path] = (component, ref)
    by_directory = {c.path: c for c in components}

    reported = 0
    for path in sorted(phase_paths):
        lines = corpus_io.read_lines(root, path, collector)
        if lines is None:
            continue  # reported as FILE_UNREADABLE by the read
        blocks, _unterminated = declaration_blocks(lines)
        offending = [b for b in blocks if not lines[b.index][: b.match.start()].strip()]
        if not offending:
            continue
        reported += 1

        owner = entry_by_path.get(path)
        if owner is not None:
            component, ref = owner
            carrier = f"`{component.roadmap}:{ref.line}` — the entry for `{ref.name}`"
        else:
            directory = path.rsplit("/", 1)[0]
            component = by_directory.get(directory)
            carrier = (
                f"`{component.roadmap}` — no phase entry there owns this document yet"
                if component is not None
                else "no roadmap in this directory — the document has no owner to carry it"
            )

        collector.add_finding(
            DEPENDENCY_IN_PHASE_DOC,
            SECTION_DEPENDS_GRAPH,
            f"phase document carries {len(offending)} dependency marker(s) on line(s) "
            + ", ".join(f"L{b.index + 1}" for b in offending)
            + "; rule 9 names one carrier, and it is the roadmap",
            Provenance(path, offending[0].index + 1),
            expected=f"the declaration on the roadmap entry instead: {carrier}",
            detail=(
                "Reported, never read as an edge: parsing it would make the phase document "
                "a second authoring surface, which is the drift rather than the fix. Where "
                "the roadmap entry carries no `**Depends on:**` line at all, the dependency "
                "exists today only where nothing reads it."
            ),
        )

        for block in offending:
            line = lines[block.index]
            rest = line[block.match.end() :].strip().strip("*`").strip()
            if _TOKEN_RE.match(rest) and not _BARE_TOKEN_RE.match(rest):
                collector.add_finding(
                    DEPENDENCY_QUALIFIED_NONE,
                    SECTION_DEPENDS_GRAPH,
                    f"standalone token is QUALIFIED — `{rest[:60]}` — so the line is "
                    "silent about whatever the qualifier excludes",
                    Provenance(path, block.index + 1),
                    expected="`**Depends on:** NONE` — the token, then the end of the clause",
                    detail=(
                        "Rule 9: a qualified form is a scoped declaration wearing the "
                        "standalone one's clothes, and reading it as standalone silently "
                        "deletes a real dependency. Separate from the one-carrier row on "
                        "the same line — it is a separate decision."
                    ),
                )
            by_number = [
                match.group("text")
                for i in block.lines
                for match in LINK_RE.finditer(lines[i])
                if BY_NUMBER_RE.match(match.group("text"))
            ]
            if by_number:
                collector.add_finding(
                    DEPENDENCY_CITES_BY_NUMBER,
                    SECTION_DEPENDS_GRAPH,
                    f"{len(by_number)} link(s) cite a phase by NUMBER — "
                    + ", ".join(f"`{text.strip()}`" for text in by_number),
                    Provenance(path, block.index + 1),
                    expected="the phase cited by NAME (Documentation Standard rule 4)",
                    detail=(
                        "A number survives a rename and tells a reader nothing about which "
                        "phase it was. Separate from the one-carrier row on the same line "
                        "— fixing the citation and moving the line are two edits."
                    ),
                )
    return reported

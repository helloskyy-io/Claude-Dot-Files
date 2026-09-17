"""Parser for ``development/sprints.md``.

The irregularity IS the specification. This file is mid-conversion by its own §1
note, so a parser written against the ideal §6 shape fails on the corpus as it
stands. Every item that misses the shape is a FINDING with its file and its line
— never a parse failure that shrinks the graph.

**The denominator is unsettled and is itself a finding.** Three defensible
counts of "sprint work item" exist and the file states none of them, so this
parser states which it counts (:data:`WORK_ITEM_DEFINITION`) and reports all
three. Stating the method is the tool's own output; inventing a corrected figure
would be authoring, which is forbidden here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .model import (
    PATH_ESCAPES_ROOT,
    SECTION_UNPARSED,
    UNPARSED_LINE,
    Collector,
    Provenance,
)
from . import corpus_io
from .fences import fenced_mask
from .safe_paths import PathEscape, is_external, resolve_within_root, split_anchor

SPRINTS_REL = "development/sprints.md"

#: ``## Sprint: <name>`` is the ratified shape. ``## Sprint — <name> (<hours>)``
#: is the interim shape the §1 migration note says some sections still carry;
#: both are accepted so an unconverted sprint is a finding about ITS items, not
#: a section that vanishes.
SPRINT_HEADING_RE = re.compile(r"^##\s+Sprint\s*(?::|—|-)\s*(?P<name>.+?)\s*$")

CHECKBOX_RE = re.compile(r"^(?P<indent>\s*)- \[(?P<mark>[ xX])\]\s*(?P<body>.*)$")
LAYER_RE = re.compile(r"(?<![A-Za-z0-9])L(\d+)(?![0-9])")
LINK_RE = re.compile(r"\[(?P<text>[^\]]*)\]\((?P<target>[^)\s]+)\)")
BOLD_RE = re.compile(r"\*\*(?P<text>.+?)\*\*")
#: ``~42h``, ``~30–40h``, ``~10-15h``, ``~42 hrs``.
HOURS_RE = re.compile(r"~\s*(?P<low>\d+)(?:\s*[–-]\s*(?P<high>\d+))?\s*(?:h\b|hrs?\b)")

MARKERS = {
    "🔵": "NOT SCHEDULED",
    "🟠": "PLANNED",
    "🟡": "IN PROGRESS",
    "✅": "COMPLETE",
}

UNPLACED_HEADING = "Unplaced"
CLOSE_OUT_MARKER = "Sprint close-out"

#: The definition this tool counts, stated rather than inherited.
WORK_ITEM_DEFINITION = (
    "a checkbox line inside a `## Sprint:` section, outside § Sprint: Unplaced, "
    "outside every fenced code block, and not the recurring `Sprint close-out` gate"
)


@dataclass
class SprintItem:
    sprint: str
    line: int
    checked: bool
    raw: str
    title: str
    layer: int | None
    links: list[tuple[str, str]]  # (text, raw target)
    link_paths: list[str]  # resolved repo-relative paths
    hours_low: int | None
    hours_high: int | None
    needs_planning: bool
    cross_cutting: bool
    is_close_out: bool
    in_unplaced: bool
    #: For a § Sprint: Unplaced entry, the `### …` subsection it sits under.
    #: The section distinguishes a whole unscheduled COMPONENT from an
    #: unscheduled phase inside a component that IS scheduled — the recorded
    #: measurement compares against the former only, and conflating them
    #: manufactures four false disagreements.
    unplaced_section: str = ""
    #: True when this item fails the §6 item shape. **This flag is what the
    #: founding measurement counts**, and it exists because the measurement used
    #: to be re-derived by scanning the report for the `UNPARSED_LINE` code —
    #: which eight sites in this module emit, only these four being §6 shape
    #: misses. A sprint losing its status marker then inflated a row whose
    #: stated method is "count items failing §6", flipping it to disagree with a
    #: recorded figure it in fact reproduces. A measurement must own its
    #: predicate; a shared finding code is not one.
    misses_shape: bool = False


@dataclass
class Sprint:
    name: str
    line: int
    marker: str | None
    marker_line: int
    items: list[SprintItem] = field(default_factory=list)

    @property
    def is_unplaced(self) -> bool:
        return UNPLACED_HEADING.lower() in self.name.lower()


@dataclass
class SprintsDocument:
    sprints: list[Sprint]
    #: Every checkbox line seen, including fenced-template and Unplaced lines.
    total_checkbox_lines: int
    #: Checkbox lines outside § Sprint: Unplaced.
    outside_unplaced: int
    #: The stated work-item denominator (:data:`WORK_ITEM_DEFINITION`).
    work_items: int
    #: Repo-relative paths any item links to.
    linked_paths: set[str]
    #: Entries of the § Sprint: Unplaced hand-maintained orphan list.
    unplaced_entries: list[SprintItem]
    #: The subset naming a whole unscheduled component.
    unplaced_whole_components: list[SprintItem]
    #: The "Deliberately NOT listed" exclusions, as (component path, line).
    stated_exclusions: list[tuple[str, int]]


#: The § Sprint: Unplaced subsection that names whole unscheduled components.
WHOLE_COMPONENTS_SUBSECTION = "whole components"


def _parse_item(
    root: Path,
    sprint: Sprint,
    lineno: int,
    match: re.Match[str],
    collector: Collector,
    unplaced_section: str = "",
) -> SprintItem:
    body = match.group("body")
    checked = match.group("mark").lower() == "x"

    bold = BOLD_RE.search(body)
    title = bold.group("text").strip() if bold else body.strip()

    layer_match = LAYER_RE.search(body)
    layer = int(layer_match.group(1)) if layer_match else None

    links = [(m.group("text"), m.group("target")) for m in LINK_RE.finditer(body)]
    link_paths: list[str] = []
    for _text, target in links:
        if is_external(target):
            continue
        path_part, _anchor = split_anchor(target)
        if not path_part:
            continue
        try:
            link_paths.append(resolve_within_root(root, SPRINTS_REL, path_part))
        except PathEscape as exc:
            collector.add_finding(
                PATH_ESCAPES_ROOT,
                SECTION_UNPARSED,
                f"sprint item link escapes the checkout root: {exc.raw}",
                Provenance(SPRINTS_REL, lineno),
                expected="a link target that resolves inside the checkout",
                detail="Reported and never opened.",
            )

    hours = HOURS_RE.search(body)
    hours_low = int(hours.group("low")) if hours else None
    hours_high = int(hours.group("high")) if hours and hours.group("high") else None

    needs_planning = "NEEDS PLANNING" in body
    cross_cutting = "cross-cutting" in body.lower()
    is_close_out = CLOSE_OUT_MARKER.lower() in body.lower()

    item = SprintItem(
        sprint=sprint.name,
        line=lineno,
        checked=checked,
        raw=body,
        title=title,
        layer=layer,
        links=links,
        link_paths=link_paths,
        hours_low=hours_low,
        hours_high=hours_high,
        needs_planning=needs_planning,
        cross_cutting=cross_cutting,
        is_close_out=is_close_out,
        in_unplaced=sprint.is_unplaced,
        unplaced_section=unplaced_section,
    )

    _report_shape_misses(item, collector)
    return item


def _report_shape_misses(item: SprintItem, collector: Collector) -> None:
    """Every §6 shape miss is a named finding — none shrinks the graph.

    The close-out gate is deliberately exempt from the ``L<n>`` and link
    requirements: §6 describes a work item, and the close-out is a recurring
    check with its own ``([checks](…))`` link shape. Exempting it here is a
    STATED exclusion, which is the difference between a taxonomy and a
    suppression list.
    """
    where = Provenance(SPRINTS_REL, item.line)
    if item.is_close_out or item.in_unplaced:
        return

    before = len(collector.findings)

    if item.layer is None:
        if item.cross_cutting:
            collector.add_finding(
                UNPARSED_LINE,
                SECTION_UNPARSED,
                f"sprint item carries `cross-cutting` in place of the required layer: {item.title}",
                where,
                expected="`· L<n> ·` per sprints.md §6 (`L<n>` is required)",
            )
        else:
            collector.add_finding(
                UNPARSED_LINE,
                SECTION_UNPARSED,
                f"sprint item has no `L<n>` layer: {item.title}",
                where,
                expected="`· L<n> ·` per sprints.md §6 (`L<n>` is required)",
            )

    if not item.checked and item.needs_planning and not item.links:
        collector.add_finding(
            UNPARSED_LINE,
            SECTION_UNPARSED,
            f"open sprint item carries `NEEDS PLANNING` and links to nothing: {item.title}",
            where,
            expected=(
                "`([roadmap](…) · [phase](…))`, or `(NEEDS PLANNING)` in place of "
                "the link with a roadmap link still present"
            ),
        )
    elif not item.checked and not item.links and not item.needs_planning:
        collector.add_finding(
            UNPARSED_LINE,
            SECTION_UNPARSED,
            f"open sprint item links to no document and carries no `NEEDS PLANNING`: {item.title}",
            where,
            expected="a link to the document that describes the work, per sprints.md §6",
        )

    # One ITEM, one miss — an item can fail twice (a `cross-cutting` in place of
    # its layer AND no link) and the recorded measurement counts items.
    item.misses_shape = len(collector.findings) > before


def _parse_exclusions(lines: list[str], start: int, fenced: list[bool]) -> list[tuple[str, int]]:
    """The § Sprint: Unplaced "Deliberately NOT listed" stated exclusions.

    They are load-bearing: a derivation that flags a retired component, or a
    coordination document that has no phases of its own, as an orphan is
    wrong, and the report must say so rather than report a false one.

    ``start`` is the index of the ``## Sprint: Unplaced`` heading, and the scan
    begins on the line AFTER it. **It used to begin ON it**, so the very first
    iteration matched the ``## `` break and this function returned an empty list
    for every corpus that has the section — the exclusions were never read at
    all. It went unnoticed because both live exclusions are suppressed by a
    second mechanism anyway (one is retired, the other is sprint-linked), so the
    orphan set was right for the wrong reason and the test asserting it passed
    on a dead code path.
    """
    out: list[tuple[str, int]] = []
    in_section = False
    for offset, line in enumerate(lines[start + 1 :], start=start + 1):
        # The same mask `parse_sprints` walks the document with. An exclusion
        # SUPPRESSES an orphan finding, so a fenced example of the subsection —
        # the shape sprints.md uses to show what one looks like — would hide a
        # component from the report on the strength of an illustration.
        if fenced[offset]:
            continue
        if line.startswith("### "):
            in_section = "deliberately not listed" in line.lower()
            continue
        if line.startswith("## "):
            break
        if not in_section:
            continue
        for match in re.finditer(r"`([a-z0-9_./-]+/)`", line):
            out.append((match.group(1).rstrip("/"), offset + 1))
    return out


def parse_sprints(root: Path, collector: Collector) -> SprintsDocument:
    """Parse ``development/sprints.md`` into sprints, items and counts."""
    path = root / SPRINTS_REL
    if not path.is_file():
        collector.add_finding(
            UNPARSED_LINE,
            SECTION_UNPARSED,
            "development/sprints.md is absent from the checkout",
            Provenance(SPRINTS_REL),
            expected="the sprint execution plan",
        )
        return SprintsDocument([], 0, 0, 0, set(), [], [], [])

    lines = corpus_io.read_lines(root, SPRINTS_REL, collector)
    if lines is None:
        # Reported as FILE_UNREADABLE. An empty document is returned rather than
        # a crash: the rest of the report is still worth producing, and the one
        # thing that must not happen — a silently smaller graph — is exactly
        # what the finding prevents.
        return SprintsDocument([], 0, 0, 0, set(), [], [], [])
    # The §6 template block is a fenced example of a well-formed item. Parsing
    # it as a real item would add a phantom sprint item to the graph — the exact
    # class of silent wrongness this phase exists to catch, so the mask is
    # load-bearing rather than cosmetic. It is `fences.fenced_mask` and not a
    # local walk because a local walk is how this file spent five commits being
    # the one length-blind reader nobody counted.
    fenced = fenced_mask(lines)

    sprints: list[Sprint] = []
    current: Sprint | None = None
    total = 0
    outside_unplaced = 0
    work_items = 0
    linked_paths: set[str] = set()
    unplaced_entries: list[SprintItem] = []
    whole_components: list[SprintItem] = []
    exclusions: list[tuple[str, int]] = []
    subsection = ""

    for index, line in enumerate(lines):
        lineno = index + 1
        if fenced[index]:
            if CHECKBOX_RE.match(line):
                total += 1
                if current is None or not current.is_unplaced:
                    outside_unplaced += 1
            continue

        heading = SPRINT_HEADING_RE.match(line)
        if heading:
            current = Sprint(
                name=heading.group("name").strip(),
                line=lineno,
                marker=None,
                marker_line=0,
            )
            sprints.append(current)
            subsection = ""
            if current.is_unplaced:
                exclusions = _parse_exclusions(lines, index, fenced)
            continue

        if line.startswith("### "):
            subsection = line[4:].strip()

        # The status marker belongs to the sprint's HEADER BLOCK — the lines
        # between the heading and its first item. Scanning the whole section
        # would let any later line that happens to open with a marker glyph (a
        # legend, a retrospective note, a quoted marker in prose) be read as the
        # sprint's status. Measured on `main`: every one of the 21 markers sits
        # 1-2 lines below its heading, so the bound costs nothing and closes a
        # misattribution that would be silent.
        if current is not None and current.marker is None and not current.items:
            for glyph, label in MARKERS.items():
                if line.strip().startswith(glyph):
                    current.marker = label
                    current.marker_line = lineno
                    break

        checkbox = CHECKBOX_RE.match(line)
        if not checkbox:
            continue

        total += 1
        if current is None:
            # A checkbox outside every sprint section. Not droppable: report it.
            collector.add_finding(
                UNPARSED_LINE,
                SECTION_UNPARSED,
                "checkbox line sits outside every `## Sprint:` section",
                Provenance(SPRINTS_REL, lineno),
                expected="a checkbox inside a `## Sprint: <name>` section",
            )
            outside_unplaced += 1
            continue

        item = _parse_item(
            root, current, lineno, checkbox, collector, unplaced_section=subsection
        )
        current.items.append(item)
        linked_paths.update(item.link_paths)

        if current.is_unplaced:
            unplaced_entries.append(item)
            if WHOLE_COMPONENTS_SUBSECTION in subsection.lower():
                whole_components.append(item)
        else:
            outside_unplaced += 1
            if not item.is_close_out:
                work_items += 1

    if current is not None and current.marker is None:
        collector.add_finding(
            UNPARSED_LINE,
            SECTION_UNPARSED,
            f"sprint `{current.name}` carries no status marker",
            Provenance(SPRINTS_REL, current.line),
            expected="a 🔵 / 🟠 / 🟡 / ✅ marker on the line below the heading",
        )

    for sprint in sprints:
        if sprint.marker is None and sprint is not current:
            collector.add_finding(
                UNPARSED_LINE,
                SECTION_UNPARSED,
                f"sprint `{sprint.name}` carries no status marker",
                Provenance(SPRINTS_REL, sprint.line),
                expected="a 🔵 / 🟠 / 🟡 / ✅ marker on the line below the heading",
            )

    return SprintsDocument(
        sprints=sprints,
        total_checkbox_lines=total,
        outside_unplaced=outside_unplaced,
        work_items=work_items,
        linked_paths=linked_paths,
        unplaced_entries=unplaced_entries,
        unplaced_whole_components=whole_components,
        stated_exclusions=exclusions,
    )

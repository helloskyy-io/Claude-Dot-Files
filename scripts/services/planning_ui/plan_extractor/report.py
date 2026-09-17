"""Render the consistency report — the phase's actual deliverable.

The report is also the worklist that The Dependency Contract and The Decisions
That Sit execute against, so every row carries the file and the line it was read
from. A report that says "13 orphans" without saying where each was read is a
number, not a worklist.
"""

from __future__ import annotations

from .dependencies import ACCOUNTING_METHOD, WORKLISTS
from .extractor import SECTION_ORDER, ExtractionResult
from .contract import load as load_contract
from .measurements import host_absolute_method
from .model import SECTION_HOST_ABSOLUTE
from .sprints import WORK_ITEM_DEFINITION

#: What the page says about where it came from. It used to say *"Derived per
#: request from the read-only mount. Nothing is stored."* — a Django view that
#: no longer exists. The page is now a committed artifact, and the sentence
#: says so; a page that describes a mechanism it does not have is the copy
#: disagreeing with the carrier.
PROVENANCE_STATEMENT = (
    "**Generated from this checkout by `python3 -m planning_ui` and committed at "
    "`development/derived/`. `python3 -m planning_ui --check` fails when it drifts from "
    "the corpus; the pull-request workflow runs that check.**"
)


def render_markdown(result: ExtractionResult) -> str:
    """The consistency report as markdown."""
    prov = result.graph["provenance"]
    out: list[str] = []
    out.append("# Consistency report")
    out.append("")
    out.append(f"- **Commit read:** `{prov['commit']}`")
    if prov["commit_date"]:
        out.append(f"- **Commit date:** {prov['commit_date']}")
    out.append(f"- **Input digest:** `{prov['input_digest']}` over {prov['input_count']} files")
    out.append(f"- **Tracked Items contract:** `{prov['tracked_contract_version']}`")
    # Rendered because the graph shape moved to "2" in this phase and a reader
    # comparing two reports otherwise cannot tell which shape produced each.
    out.append(f"- **Graph schema:** `{prov['schema_version']}`")
    out.append("")
    out.append(PROVENANCE_STATEMENT)
    out.append("")

    if result.halted:
        out.append("## RUN HALTED")
        out.append("")
        out.append(f"> {result.halted}")
        out.append("")
        out.append(
            "The tracked-store tables below are absent because the store's shape no "
            "longer matches the expected §3 core. A shorter table that reads as a "
            "complete one is the failure Tracked Items §7 exists to stop."
        )
        out.append("")

    out.append("## Counts, and the definition each uses")
    out.append("")
    out.append("| Count | Value |")
    out.append("|---|---|")
    for label, key in (
        ("Components (a directory with a `roadmap.md`)", "components"),
        ("Phase documents", "phases"),
        ("Sprints", "sprints"),
        ("Checkbox lines in `sprints.md`", "checkbox_lines"),
        ("…outside § Sprint: Unplaced", "outside_unplaced"),
        ("…work items, as defined below", "work_items"),
        ("Tracked items across the four stores", "tracked_items"),
        ("`**Depends on:**` declarations read", "dependency_declarations"),
        ("…of those, bound to a phase entry rather than its component", "declarations_attributed_to_a_phase"),
        ("Dependency edges emitted", "depends_on_edges"),
        ("…satisfied — the target phase is `✅ COMPLETE`, or the standard or artifact resolves", "edges_satisfied"),
        ("…unsatisfied — the target phase carries any other marker", "edges_unsatisfied"),
        ("…BROKEN — the target does not resolve", "edges_broken"),
        ("…underivable — the target has no satisfaction rule 9 defines", "edges_underivable"),
        ("Phases OWNED by a roadmap's entries", "phases_owned"),
        ("…of those, living inline in the roadmap with no document", "phases_inline"),
        ("Phase links a roadmap merely REFERENCES", "phases_referenced"),
        ("Standards depended on", "standards_depended_on"),
        ("Other artifacts depended on — a paper, the sprint file, a guide page", "artifacts_depended_on"),
        ("Phase documents carrying a `**Depends on:**` marker", "phase_docs_carrying_a_dependency_marker"),
        ("Roadmaps whose every declaration resolves", "roadmaps_resolving"),
        ("Roadmaps on the stated exception list", "roadmaps_excepted"),
        ("Roadmaps declaring a dependency in prose only", "roadmaps_prose_only"),
        ("Roadmaps declaring no dependency at all", "roadmaps_declaring_nothing"),
        ("Sprint-item hour figures with a roadmap figure to compare", "hour_pairs_compared"),
        ("Sprint-item hour figures whose phase roadmap carries none", "hour_pairs_without_roadmap_figure"),
        ("Findings", "findings"),
    ):
        out.append(f"| {label} | {result.counts.get(key, 0)} |")
    out.append("")
    out.append(f"**Work item is counted as:** {WORK_ITEM_DEFINITION}")
    out.append("")
    out.append(
        "*The denominator is unsettled in the corpus and that is itself a finding. "
        "This tool states which definition it counts rather than inheriting one, and "
        "authors no corrected figure.*"
    )
    out.append("")

    grouped = result.findings_by_section()
    for section in SECTION_ORDER:
        findings = grouped.get(section, [])
        out.append(f"## {section} — {len(findings)}")
        out.append("")
        if section == SECTION_HOST_ABSOLUTE:
            # A population, so the method is stated beside the count.
            out.append(f"**Method:** {host_absolute_method(load_contract(result.root))}")
            out.append("")
        if not findings:
            out.append("*None.*")
            out.append("")
            continue
        out.append("| Where | Code | Finding | Expected |")
        out.append("|---|---|---|---|")
        for finding in findings:
            where = str(finding.provenance)
            out.append(
                f"| `{where}` | `{finding.code}` | {_cell(finding.summary)} "
                f"| {_cell(finding.expected)} |"
            )
        out.append("")

    out.append("## Every roadmap, accounted for")
    out.append("")
    out.append(
        "*Requirement: nothing falls through silently. Every roadmap below either "
        "resolves, sits on the exception list, or is named on exactly one of the two "
        "worklists — and **no dependency is authored for any of them.***"
    )
    out.append("")
    out.append(f"**Method:** {ACCOUNTING_METHOD}")
    out.append("")
    out.append("| Roadmap | Disposition | Why | Declarations |")
    out.append("|---|---|---|---|")
    for row in result.dependency_accounting:
        lines = (
            ", ".join(f"L{line}" for line in row.declaration_lines)
            if row.declaration_lines
            else "—"
        )
        marker = "**" if row.disposition in WORKLISTS else ""
        out.append(
            f"| `{_cell(row.component)}` | {marker}{_cell(row.disposition)}{marker} "
            f"| {_cell(row.reason)} | {lines} |"
        )
    out.append("")
    out.append(
        f"*{result.counts.get('roadmaps_resolving', 0)} resolve · "
        f"{result.counts.get('roadmaps_excepted', 0)} excepted · "
        f"{result.counts.get('roadmaps_prose_only', 0)} declare in prose only · "
        f"{result.counts.get('roadmaps_declaring_nothing', 0)} declare nothing.*"
    )
    out.append("")

    out.append("## Five structural measurements")
    out.append("")
    # A baseline column only when some row carries one: a corpus that states
    # its own figures gets the comparison; one that does not gets no empty
    # column implying a comparison was made.
    with_baseline = any(row.recorded for row in result.rows)
    if with_baseline:
        out.append("| Measured | Method | Derived | Recorded |")
        out.append("|---|---|---|---|")
    else:
        out.append("| Measured | Method | Derived |")
        out.append("|---|---|---|")
    for row in result.rows:
        line = f"| {_cell(row.name)} | {_cell(row.method)} | **{_cell(row.derived)}** |"
        if with_baseline:
            line += f" {_cell(row.recorded)} |"
        out.append(line)
    out.append("")
    for row in result.rows:
        if row.agrees or not row.note:
            continue
        out.append(f"- **{row.name}** — {row.note}")
    out.append("")
    out.append(
        "*Each figure is a method plus what it yields on this checkout, never a "
        "target. Where a corpus records its own figure, it is compared and never edited.*"
    )
    out.append("")
    return "\n".join(out)


def _cell(text: str) -> str:
    """Escape a value for a markdown table cell."""
    return text.replace("|", "\\|").replace("\n", " ")

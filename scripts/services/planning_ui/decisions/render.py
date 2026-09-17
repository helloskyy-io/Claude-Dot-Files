"""Render the page as markdown — five tables and four cross-store readings.

One renderer for every table, because every table is one shape. Markdown is
the page's only surface: it is committed at ``development/derived/`` and read on
GitHub or in an editor, and a **worklist** a reader can paste into a PR body or
a standup note is worth more than one that only exists behind a login.
"""

from __future__ import annotations

from .model import DecisionsPage, Table

#: What the page says about where it came from. It used to say *"Derived per
#: request from the checkout … nothing committed"* — a view that no longer
#: exists. The half that is still true stays: the page rules on nothing and
#: writes no store.
PROVENANCE_STATEMENT = (
    "**Generated from this checkout by `python3 -m planning_ui` and committed at "
    "`development/derived/`; `--check` fails when it drifts from the corpus. No "
    "network call. This page reports what owes a ruling; it rules on nothing "
    "and writes no store.**"
)


def render_markdown(page: DecisionsPage) -> str:
    out: list[str] = []
    out.append("# The Decisions That Sit")
    out.append("")
    out.append(f"- **Commit read:** `{page.provenance.get('commit', 'unknown')}`")
    if page.provenance.get("commit_date"):
        out.append(f"- **Commit date:** {page.provenance['commit_date']}")
    out.append(
        f"- **Input digest:** `{page.provenance.get('input_digest', '')}` over "
        f"{page.provenance.get('input_count', 0)} files"
    )
    out.append(f"- **Tracked Items contract:** `{page.provenance.get('tracked_contract_version')}`")
    out.append(f"- **Ages counted back to:** {page.provenance.get('as_of')}")
    out.append("")
    out.append(PROVENANCE_STATEMENT)
    out.append("")

    if page.halted:
        out.append("## RUN HALTED")
        out.append("")
        out.append(f"> {page.halted}")
        out.append("")
        out.append(
            "Every table is absent because a store's shape no longer matches the "
            "expected §3 core. A shorter table that reads as a complete one is the "
            "failure Tracked Items §7 exists to stop."
        )
        out.append("")

    for table in page.tables:
        out.extend(_render_table(table))

    if page.crossings:
        out.append("## The cross-store readings — why this is one page and not five views")
        out.append("")
        out.append(
            "Each table above is worth having. These are what none of them can "
            "produce alone."
        )
        out.append("")
    for table in page.crossings:
        out.extend(_render_table(table))

    out.append(f"## Findings — {len(page.findings)}")
    out.append("")
    if not page.findings:
        out.append("*None.*")
        out.append("")
    else:
        out.append("| Where | Code | Finding | Expected |")
        out.append("|---|---|---|---|")
        for finding in page.findings:
            out.append(
                f"| `{finding.provenance}` | `{finding.code}` | {_cell(finding.summary)} "
                f"| {_cell(finding.expected)} |"
            )
        out.append("")
    return "\n".join(out)


def _render_table(table: Table) -> list[str]:
    out: list[str] = []
    out.append(f"## {table.title}")
    out.append("")
    out.append(f"**Source:** `{table.source}`")
    out.append("")
    out.append(f"**What *owes a ruling* means here.** {table.owes_definition}")
    out.append("")
    out.append(
        f"*{len(table.rows)} row(s) · {table.scanned} item(s) read · "
        f"{table.suppressed} owing nothing and therefore not listed.*"
    )
    out.append("")
    header = " | ".join(
        f"{c.label} ᴰ" if c.derived else c.label for c in table.columns
    )
    out.append(f"| {header} |")
    out.append("|" + "---|" * len(table.columns))
    for row in table.rows:
        cells = [_cell(row.cells.get(column.key, "")) for column in table.columns]
        out.append("| " + " | ".join(cells) + " |")
    if not table.rows:
        out.append("| " + " | ".join("—" for _ in table.columns) + " |")
    out.append("")
    out.append("*ᴰ marks a column derived from the checkout — one its source document cannot carry.*")
    out.append("")
    for note in table.notes:
        out.append(f"> {note}")
        out.append("")
    return out


def _cell(text: str) -> str:
    """Escape a value for a markdown table cell."""
    return text.replace("|", "\\|").replace("\n", " ")

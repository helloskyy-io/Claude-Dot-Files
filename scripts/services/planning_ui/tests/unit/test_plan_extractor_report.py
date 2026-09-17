"""Unit tests for report rendering and the roadmap shapes — pure over strings."""

from __future__ import annotations

import re

from planning_ui.plan_extractor import SECTION_ORDER
from pathlib import Path

from planning_ui.plan_extractor.extractor import ExtractionResult
from planning_ui.plan_extractor.model import (
    SECTION_UNPARSED,
    Finding,
    Measurement,
    Provenance,
)
from planning_ui.plan_extractor.report import _cell, render_markdown
from planning_ui.plan_extractor.roadmaps import LEGACY_RETIRED_RE, STATUS_RE, is_phase_link


def _result(findings=(), rows=(), halted="") -> ExtractionResult:
    return ExtractionResult(
        root=Path("/nowhere"),
        graph={
            "provenance": {
                "commit": "abc123",
                "commit_date": "2026-08-29T00:00:00+00:00",
                "input_digest": "sha256:deadbeef",
                "input_count": 3,
                "tracked_contract_version": "v1",
                "schema_version": "2",
            }
        },
        findings=list(findings),
        rows=list(rows),
        halted=halted,
        counts={"components": 2, "findings": len(findings)},
    )


def test_the_report_stamps_the_commit_and_the_input_digest():
    """Requirement 5: every emitted artifact records what it was derived from."""
    text = render_markdown(_result())
    assert "abc123" in text
    assert "sha256:deadbeef" in text
    assert "over 3 files" in text


def test_sections_are_emitted_in_order_with_unparsed_first():
    text = render_markdown(_result())
    positions = [text.index(f"## {section}") for section in SECTION_ORDER]
    assert positions == sorted(positions)


def test_an_empty_section_says_None_rather_than_being_omitted():
    """An omitted section reads as "nothing was checked"."""
    text = render_markdown(_result())
    for section in SECTION_ORDER:
        assert f"## {section} — 0" in text
    assert text.count("*None.*") == len(SECTION_ORDER)


def test_a_halted_run_says_so_instead_of_rendering_a_shorter_table():
    text = render_markdown(_result(halted="tracked/issues/ does not match contract v1: …"))
    assert "## RUN HALTED" in text
    assert "does not match contract v1" in text
    assert "shorter table" in text


def test_a_finding_renders_its_file_line_code_and_expected_shape():
    finding = Finding(
        code="UNPARSED_LINE",
        section=SECTION_UNPARSED,
        summary="sprint item has no `L<n>` layer: a thing",
        provenance=Provenance("development/sprints.md", 42),
        expected="`· L<n> ·` per sprints.md §6",
    )
    text = render_markdown(_result(findings=[finding]))
    assert "development/sprints.md:42" in text
    assert "UNPARSED_LINE" in text
    assert "per sprints.md §6" in text


def test_a_pipe_in_a_finding_cannot_break_the_markdown_table():
    """The corpus is full of table syntax; an unescaped `|` silently shifts
    every column to its right — which is the column-shift defect this phase's
    spine is written against, reproduced in the tool's own output."""
    assert _cell("a | b") == "a \\| b"
    assert _cell("two\nlines") == "two lines"
    finding = Finding(
        code="X",
        section=SECTION_UNPARSED,
        summary="a | b | c",
        provenance=Provenance("f.md", 1),
    )
    row = [
        line for line in render_markdown(_result(findings=[finding])).splitlines()
        if "a \\| b" in line
    ]
    assert len(row) == 1
    assert row[0].count("|") - row[0].count("\\|") == 5  # 4 cells => 5 delimiters


def test_a_measurement_row_shows_the_method_beside_the_figure():
    row = Measurement(
        name="A thing",
        method="counted like so",
        derived="7 of 39",
        recorded="11 of 39",
        agrees=False,
        note="the definition is contested",
    )
    text = render_markdown(_result(rows=[row]))
    assert "counted like so" in text
    assert "**7 of 39**" in text
    assert "11 of 39" in text
    assert "the definition is contested" in text
    # No third figure is authored anywhere.
    assert not re.search(r"should be ~?\d", text)


# --- roadmap shapes -------------------------------------------------------


def test_status_line_extraction():
    assert STATUS_RE.match("**Status:** Phase 0 ✅ Complete").group("text") == "Phase 0 ✅ Complete"
    assert STATUS_RE.match("Some prose **Status:** here") is None


def test_the_legacy_retired_marker_is_read_from_the_status_line_not_the_name():
    """Retirement is a `**Lifecycle:**` line now; this pattern only recognises
    the form that predates it, so a corpus mid-conversion keeps its
    suppression while the divergence is reported.

    Reading it from the STATUS LINE rather than the path is what keeps
    `probe/old/` — which carries no status line at all — its own finding.
    """
    assert LEGACY_RETIRED_RE.search("⚫ **RETIRED 2026-08-21.** Built, demoed, no sale.")
    assert LEGACY_RETIRED_RE.search("Planning surface. No phases scheduled.") is None


def test_phase_link_recognition_covers_the_non_conforming_genesis_names():
    assert is_phase_link("development/common/planning_ui/phase1_plan_extractor.md")
    assert is_phase_link("development/common/genesis/genesis-1a_k3s-0.md")
    assert not is_phase_link("development/common/planning_ui/roadmap.md")
    assert not is_phase_link("standards/api/api_standard.md")


def test_the_report_describes_the_mechanism_it_actually_has():
    """Phase 6 requirement 5: no sentence about a mechanism that no longer exists.

    The page used to say *"Derived per request from the read-only mount"* — a
    Django view deleted when the code moved. Corrected at source, in the
    renderer, never in the output.
    """
    text = render_markdown(_result())
    assert "per request" not in text
    assert "read-only mount" not in text
    assert "python3 -m planning_ui --check" in text


def test_the_host_absolute_section_states_its_method_beside_its_count():
    """The method is built from the corpus's OWN declarations. A root with no
    `corpus.toml` states that it declares no canonical host path — the report
    says so rather than describing some other repository's method."""
    from planning_ui.plan_extractor.model import SECTION_HOST_ABSOLUTE

    text = render_markdown(_result())
    heading = text.index(f"## {SECTION_HOST_ABSOLUTE} — 0")
    method_at = text.index("**Method:** every markdown link under the checkout")
    assert method_at > heading
    assert "declares no canonical host path" in text

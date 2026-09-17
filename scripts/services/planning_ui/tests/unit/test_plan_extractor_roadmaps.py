"""The roadmap header's two independent axes.

**Status is DERIVED from checkboxes; lifecycle is DECLARED by the operator.**
Conflating them is what produced a fifth status marker that the standard says
does not exist: an abandoned experiment kept whatever marker its boxes gave it
and someone reached for `⚫ RETIRED` to say nobody was working it. These hold
the two apart.
"""
from __future__ import annotations

from pathlib import Path

from planning_ui.plan_extractor import roadmaps
from planning_ui.plan_extractor.model import Collector

LIFECYCLE_ROADMAP = """# Widget

**Status:** 🟠 PLANNED

**Lifecycle:** retired 2026-09-16 — maintained in SkyyNet as planning-ui

## Only Phase 🟠 PLANNED — **~5h**

**Implementation:** [`phase1_only.md`](phase1_only.md)
"""


def _read(tmp_path: Path, text: str):
    root = tmp_path / "corpus"
    (root / "development" / "common" / "w").mkdir(parents=True)
    (root / "development" / "common" / "w" / "roadmap.md").write_text(text)
    (root / "development" / "common" / "w" / "phase1_only.md").write_text("# P\n")
    collector = Collector()
    component = roadmaps.parse_roadmap(
        root, "development/common/w/roadmap.md", collector
    )
    return component, collector


def _legacy(collector: Collector) -> list:
    return [f for f in collector.findings if f.code == roadmaps.COMPONENT_LEGACY_LIFECYCLE]


def test_the_lifecycle_line_retires_a_component_and_the_marker_stays_derived(tmp_path):
    """Two axes at once: the marker still says PLANNED because that is what the
    checkboxes say, and the component is retired because the operator declared
    it. Neither reads the other."""
    component, collector = _read(tmp_path, LIFECYCLE_ROADMAP)
    assert component.retired is True
    assert "PLANNED" in component.status_text
    assert _legacy(collector) == []


def test_a_roadmap_with_no_lifecycle_line_is_active(tmp_path):
    component, _ = _read(tmp_path, LIFECYCLE_ROADMAP.replace(
        "**Lifecycle:** retired 2026-09-16 — maintained in SkyyNet as planning-ui\n\n", ""))
    assert component.retired is False


def test_lifecycle_active_is_not_retired(tmp_path):
    component, _ = _read(tmp_path, LIFECYCLE_ROADMAP.replace(
        "retired 2026-09-16 — maintained in SkyyNet as planning-ui", "active"))
    assert component.retired is False


def test_the_old_marker_keeps_its_suppression_and_is_reported(tmp_path):
    """Both halves matter, and neither alone is right.

    Stripping the suppression would flood the report with findings the
    roadmap states why it does not want. Leaving it silent is a reader
    admitting a fifth status marker the standard denies. So: honoured, and
    named, until the corpus converts.
    """
    component, collector = _read(tmp_path, LIFECYCLE_ROADMAP.replace(
        "**Lifecycle:** retired 2026-09-16 — maintained in SkyyNet as planning-ui\n\n", ""
    ).replace("**Status:** 🟠 PLANNED", "**Status:** ⚫ RETIRED 2026-08-21 — no sale"))
    assert component.retired is True, "suppression survives the transition"
    named = _legacy(collector)
    assert len(named) == 1
    assert "Lifecycle:" in named[0].expected


def test_the_lifecycle_line_wins_over_a_legacy_marker(tmp_path):
    """A roadmap carrying both is converting; the declared line is the answer
    and there is nothing left to report."""
    component, collector = _read(tmp_path, LIFECYCLE_ROADMAP.replace(
        "**Status:** 🟠 PLANNED", "**Status:** ⚫ RETIRED 2026-08-21 — no sale"))
    assert component.retired is True
    assert _legacy(collector) == []

"""Own phases, referenced phases and edge states — the seventh phase's contract.

Three things this file pins, each against a self-contained miniature corpus:

* **Attribution.** A phase is OWNED by the roadmap whose phase ENTRY names it,
  in every shape the corpus uses, and a link anywhere else is a REFERENCE. The
  coordination-document exception still fires off the referenced set.
* **Edge states.** Satisfaction derives from what the target IS — a phase from
  its owning entry's rule-8 marker, a standard from resolving — and a BROKEN
  edge is a different thing from an UNSATISFIED one, under its own code.
* **The anchor forms.** ``roadmap.md#anchor`` and a bare ``#anchor`` resolve to
  the PHASE the anchor names, never to its component, and an inline phase is a
  node carrying its own marker.

Every corpus here is built in ``tmp_path`` rather than taken from the shared
fixture tree: a control that shares a fixture with the code under mutation
over-fires, and the shared tree's counts are pinned by other files.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from planning_ui.plan_extractor import dependencies, extract, render_markdown
from planning_ui.plan_extractor.model import (
    EDGE_BROKEN,
    EDGE_SATISFIED,
    EDGE_STATES,
    EDGE_UNDERIVABLE,
    EDGE_UNSATISFIED,
    Collector,
)
from planning_ui.plan_extractor import roadmaps

SPRINTS = """# Implementation Plan

## Sprint: One
🟡 IN PROGRESS

- [x] **common/alpha · One** · L1 · ([roadmap](./common/alpha/roadmap.md)) — done · **~2h**
"""


def build(tmp_path: Path, roadmap_texts: dict[str, str], phases: tuple[str, ...] = ()) -> Path:
    """A miniature corpus. ``roadmap_texts`` maps ``<domain>/<name>`` to roadmap text."""
    root = tmp_path / "corpus"
    (root / "development").mkdir(parents=True)
    (root / "development" / "sprints.md").write_text(SPRINTS, encoding="utf-8")
    for slug, text in roadmap_texts.items():
        directory = root / "development" / slug
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "roadmap.md").write_text(text, encoding="utf-8")
    for rel in phases:
        target = root / "development" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# A phase\n\n## Requirements for completion\n\n- [ ] a thing\n")
    return root


def roadmap(title: str, body: str, status: str = "🟡 IN PROGRESS") -> str:
    return f"# {title}\n\n**Status:** {status}\n\n{body}\n"


def codes(result, code: str) -> list:
    return [f for f in result.findings if f.code == code]


def component(result, path: str) -> roadmaps.Component:
    return next(c for c in result.components if c.path == f"development/{path}")


def node(result, node_id: str) -> dict:
    return next(n for n in result.graph["nodes"] if n["id"] == node_id)


def depends(result) -> list[dict]:
    return [e for e in result.graph["edges"] if e["kind"] == "depends_on"]


def edges_of_kind(result, kind: str, source: str) -> set[str]:
    return {e["target"] for e in result.graph["edges"] if e["kind"] == kind and e["source"] == source}


BETA = roadmap("Beta", "### Beta One ✅ COMPLETE\n\n**Implementation:** [phase1_beta.md](phase1_beta.md)\n")
GAMMA = roadmap("Gamma", "### Gamma One 🟠 PLANNED\n\n**Implementation:** [phase1_gamma.md](phase1_gamma.md)\n")


# ---------------------------------------------------------------------------
# Requirement 1 — owned versus referenced
# ---------------------------------------------------------------------------


def test_a_foreign_phase_linked_in_prose_is_referenced_and_never_owned(tmp_path: Path):
    """The defect, measured: 27 of 38 live roadmaps attributed phases they merely link."""
    alpha = roadmap(
        "Alpha",
        "### Alpha One 🟠 PLANNED\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "Builds on [Beta One](../beta/phase1_beta.md), which is done.\n",
    )
    result = extract(
        build(
            tmp_path,
            {"common/alpha": alpha, "common/beta": BETA},
            phases=("common/alpha/phase1_alpha.md", "common/beta/phase1_beta.md"),
        )
    )
    a = component(result, "common/alpha")
    assert [r.path for r in a.owned] == ["development/common/alpha/phase1_alpha.md"]
    assert [r.path for r in a.referenced] == ["development/common/beta/phase1_beta.md"]

    attrs = node(result, "component:development/common/alpha")["attrs"]
    assert attrs["owned_phases"] == ["phase:development/common/alpha/phase1_alpha.md"]
    assert attrs["referenced_phases"] == ["phase:development/common/beta/phase1_beta.md"]
    assert edges_of_kind(result, "plans", a.node_id) == {"phase:development/common/alpha/phase1_alpha.md"}
    assert edges_of_kind(result, "references", a.node_id) == {"phase:development/common/beta/phase1_beta.md"}


def test_a_coordination_document_is_still_recognised_off_the_referenced_set(tmp_path: Path):
    """The exception is DEFINED by foreign links; the split must not remove them."""
    coord = roadmap(
        "Coord", "Sequences [Beta One](../beta/phase1_beta.md) then [Gamma One](../gamma/phase1_gamma.md).\n"
    )
    result = extract(
        build(
            tmp_path,
            {"common/coord": coord, "common/beta": BETA, "common/gamma": GAMMA},
            phases=("common/beta/phase1_beta.md", "common/gamma/phase1_gamma.md"),
        )
    )
    c = component(result, "common/coord")
    assert c.owned == []
    assert len(c.referenced) == 2
    (row,) = [r for r in result.dependency_accounting if r.component == c.path]
    assert row.disposition == dependencies.EXCEPTION_COORDINATION


def test_a_roadmap_with_unclaimed_documents_on_disk_is_not_a_coordination_document(tmp_path: Path):
    """The hiding direction: excepting it would bury the ownership finding."""
    coord = roadmap(
        "Coord",
        "Sequences [Beta One](../beta/phase1_beta.md) then [Gamma One](../gamma/phase1_gamma.md).\n",
    )
    result = extract(
        build(
            tmp_path,
            {"common/coord": coord, "common/beta": BETA, "common/gamma": GAMMA},
            phases=(
                "common/coord/phase1_coord.md",
                "common/beta/phase1_beta.md",
                "common/gamma/phase1_gamma.md",
            ),
        )
    )
    (row,) = [r for r in result.dependency_accounting if r.component == "development/common/coord"]
    assert row.disposition != dependencies.EXCEPTION_COORDINATION
    (finding,) = codes(result, "PHASE_OWNERSHIP_DISAGREES_WITH_DISK")
    assert "phase1_coord.md" in finding.summary


# ---------------------------------------------------------------------------
# Requirement 2 — both entry shapes
# ---------------------------------------------------------------------------


def test_the_legacy_checkbox_list_owns_with_status_from_the_mark(tmp_path: Path):
    """Rule 8's conversion clause: tooling MUST accept this form until the corpus converts."""
    alpha = roadmap(
        "Alpha",
        "## Phases\n\n"
        "- [x] **Done** ([phase1_alpha.md](./phase1_alpha.md)) — landed\n"
        "- [ ] **Open** ([phase2_alpha.md](./phase2_alpha.md)) — pending\n"
        "- [~] **Gone** ([phase3_alpha.md](./phase3_alpha.md)) — superseded\n",
    )
    result = extract(
        build(
            tmp_path,
            {"common/alpha": alpha},
            phases=tuple(f"common/alpha/phase{n}_alpha.md" for n in (1, 2, 3)),
        )
    )
    a = component(result, "common/alpha")
    assert [(r.path.rsplit("/", 1)[-1], r.shape, r.status, r.name) for r in a.owned] == [
        ("phase1_alpha.md", roadmaps.SHAPE_CHECKBOX, "COMPLETE", "Done"),
        ("phase2_alpha.md", roadmaps.SHAPE_CHECKBOX, "UNCHECKED", "Open"),
        ("phase3_alpha.md", roadmaps.SHAPE_CHECKBOX, "DEPRECATED", "Gone"),
    ]
    assert a.referenced == []
    assert codes(result, "PHASE_OWNERSHIP_DISAGREES_WITH_DISK") == []


def test_a_heading_whose_text_is_the_phase_link_is_a_reference_not_an_entry(tmp_path: Path):
    """The shape the operator ruled OUT of the corpus (intake #262; converted at
    `670294b`). The reader that owned it is deleted; the link is a reference, so
    the phase is unowned and the disagreement with disk is reported."""
    alpha = roadmap("Alpha", "## [First](phase1_alpha.md) — **~10h**\n\nProse.\n")
    result = extract(build(tmp_path, {"common/alpha": alpha}, phases=("common/alpha/phase1_alpha.md",)))
    a = component(result, "common/alpha")
    assert a.owned == []
    assert [(r.path.rsplit("/", 1)[-1], r.line) for r in a.referenced] == [("phase1_alpha.md", 5)]
    assert not hasattr(roadmaps, "SHAPE_HEADING_LINK")
    assert codes(result, "PHASE_OWNERSHIP_DISAGREES_WITH_DISK") != []


def test_a_criterion_bullet_inside_a_rule_8_section_is_not_a_second_entry(tmp_path: Path):
    """`common/planning_ui`'s live shape: a `- [ ]` criterion linking another own phase.

    Reading it as a legacy entry would claim `phase2` with `UNCHECKED` while
    its real entry says `✅ COMPLETE` — two statuses for one phase.
    """
    alpha = roadmap(
        "Alpha",
        "### One 🟠 PLANNED\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "- [ ] Consumes what [Two](phase2_alpha.md) delivers\n\n"
        "### Two ✅ COMPLETE\n\n**Implementation:** [phase2_alpha.md](phase2_alpha.md)\n",
    )
    result = extract(
        build(
            tmp_path,
            {"common/alpha": alpha},
            phases=("common/alpha/phase1_alpha.md", "common/alpha/phase2_alpha.md"),
        )
    )
    a = component(result, "common/alpha")
    assert [(r.path.rsplit("/", 1)[-1], r.status) for r in a.owned] == [
        ("phase1_alpha.md", "PLANNED"),
        ("phase2_alpha.md", "COMPLETE"),
    ]
    assert node(result, "phase:development/common/alpha/phase2_alpha.md")["attrs"]["status"] == "COMPLETE"


def test_an_implementation_line_naming_a_foreign_document_references_it(tmp_path: Path):
    """`common/genesis` L140's shape. The directory owns the phase, not the entry."""
    alpha = roadmap(
        "Alpha", "### Borrowed\n\n**Implementation:** [Beta One](../beta/phase1_beta.md)\n"
    )
    result = extract(
        build(tmp_path, {"common/alpha": alpha, "common/beta": BETA}, phases=("common/beta/phase1_beta.md",))
    )
    a = component(result, "common/alpha")
    assert a.owned == []
    assert [r.path for r in a.referenced] == ["development/common/beta/phase1_beta.md"]


# ---------------------------------------------------------------------------
# Requirement 3 — residual mismatches are findings, never absorbed
# ---------------------------------------------------------------------------


def test_ownership_versus_disk_reports_both_directions_in_one_row(tmp_path: Path):
    alpha = roadmap(
        "Alpha",
        "### One ✅ COMPLETE\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "### Ghost 🟠 PLANNED\n\n**Implementation:** [phase9_ghost.md](phase9_ghost.md)\n",
    )
    result = extract(
        build(
            tmp_path,
            {"common/alpha": alpha},
            phases=("common/alpha/phase1_alpha.md", "common/alpha/phase2_unclaimed.md"),
        )
    )
    (finding,) = codes(result, "PHASE_OWNERSHIP_DISAGREES_WITH_DISK")
    assert "phase9_ghost.md" in finding.summary and "no conforming phase document" in finding.summary
    assert "phase2_unclaimed.md" in finding.summary and "no entry claims" in finding.summary
    assert finding.provenance.file == "development/common/alpha/roadmap.md"
    assert finding.provenance.line == 11, "anchored on the entry whose document is missing"
    assert "RETIRED" not in finding.detail


def test_a_retired_component_s_unclaimed_documents_are_reported_and_say_so(tmp_path: Path):
    """`workload/probe`: suppression by status is how a live gap hides behind a label."""
    result = extract(
        build(
            tmp_path,
            {"workload/gone": roadmap("Gone", "Torn down.", status="⚫ RETIRED 2026-01-01")},
            phases=("workload/gone/phase1_old.md",),
        )
    )
    (finding,) = codes(result, "PHASE_OWNERSHIP_DISAGREES_WITH_DISK")
    assert "phase1_old.md" in finding.summary
    assert finding.detail.startswith("This component's status line reads RETIRED")


def test_a_misnamed_document_claimed_by_an_entry_is_a_finding_not_a_match(tmp_path: Path):
    """`common/genesis`: discovery reports the name; ownership must not silently adopt it."""
    root = build(
        tmp_path,
        {"common/alpha": roadmap("Alpha", "### G\n\n**Implementation:** [g](genesis-1a_k3s.md)\n")},
    )
    (root / "development" / "common" / "alpha" / "genesis-1a_k3s.md").write_text(
        "# G\n\n## Requirements for completion\n"
    )
    result = extract(root)
    assert [r.path.rsplit("/", 1)[-1] for r in component(result, "common/alpha").owned] == [
        "genesis-1a_k3s.md"
    ], "the entry's claim is recorded"
    (finding,) = codes(result, "PHASE_OWNERSHIP_DISAGREES_WITH_DISK")
    assert "genesis-1a_k3s.md" in finding.summary


# ---------------------------------------------------------------------------
# Hours move with ownership
# ---------------------------------------------------------------------------


def test_hours_bind_to_the_single_owned_entry_and_a_foreign_only_section_is_unattributed(
    tmp_path: Path,
):
    """`common/resilience` L22's live shape: a `~30–50 hrs` figure beside a link to
    ANOTHER component's phase used to become that phase's roadmap figure."""
    alpha = roadmap(
        "Alpha",
        "### One 🟠 PLANNED\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "**Estimate: ~8h** — and it cites [Beta One](../beta/phase1_beta.md) in passing.\n\n"
        "### Elsewhere\n\n- Waits on [Beta One](../beta/phase1_beta.md) (~30–50 hrs)\n",
    )
    result = extract(
        build(
            tmp_path,
            {"common/alpha": alpha, "common/beta": BETA},
            phases=("common/alpha/phase1_alpha.md", "common/beta/phase1_beta.md"),
        )
    )
    a = component(result, "common/alpha")
    assert [(r.path.rsplit("/", 1)[-1], r.hours_low) for r in a.owned] == [("phase1_alpha.md", 8)]
    (finding,) = codes(result, "HOURS_UNATTRIBUTED")
    assert "L13 ~30-50h" in finding.detail
    b = component(result, "common/beta")
    assert all(r.hours_low is None for r in b.owned), "beta's figure is beta's to write"


# ---------------------------------------------------------------------------
# Requirements 4 and 5 — edge states, derived from what the target IS
# ---------------------------------------------------------------------------


def _alpha_depending_on_beta(beta_heading: str) -> dict[str, str]:
    return {
        "common/alpha": roadmap(
            "Alpha",
            "### One 🟠 PLANNED\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
            "**Depends on:** [`common/beta` · Beta One](../beta/phase1_beta.md)\n",
        ),
        "common/beta": roadmap(
            "Beta", f"### {beta_heading}\n\n**Implementation:** [phase1_beta.md](phase1_beta.md)\n"
        ),
    }


@pytest.mark.parametrize(
    ("heading", "state"),
    [
        ("Beta One ✅ COMPLETE", EDGE_SATISFIED),
        ("Beta One 🟡 IN PROGRESS", EDGE_UNSATISFIED),
        ("Beta One 🟠 PLANNED", EDGE_UNSATISFIED),
        ("Beta One 🔵 NOT SCHEDULED", EDGE_UNSATISFIED),
        ("Beta One", EDGE_UNDERIVABLE),
        ("Beta One ✅", EDGE_UNDERIVABLE),
    ],
)
def test_a_phase_target_derives_from_its_rule_8_marker(tmp_path: Path, heading: str, state: str):
    """Each of the four states, plus the two no-marker cases: no marker at all,
    and a bare `✅` that is not one of the four and must not be read as one."""
    result = extract(
        build(
            tmp_path,
            _alpha_depending_on_beta(heading),
            phases=("common/alpha/phase1_alpha.md", "common/beta/phase1_beta.md"),
        )
    )
    (edge,) = depends(result)
    assert edge["state"] == state
    underivable = codes(result, "DEPENDENCY_TARGET_UNDERIVABLE")
    if state == EDGE_UNDERIVABLE:
        (finding,) = underivable
        assert "no rule-8 status marker" in finding.summary
    else:
        assert underivable == []
    assert codes(result, "DEPENDENCY_EDGE_BROKEN") == []


def test_a_broken_edge_is_not_an_unsatisfied_one(tmp_path: Path):
    """Requirement 4, both halves in one corpus: a target that is not there and a
    target that is there and unfinished, side by side, with different states and
    only ONE of them a finding."""
    alpha = roadmap(
        "Alpha",
        "### One 🟠 PLANNED\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "**Depends on:** [`common/beta` · Beta One](../beta/phase1_beta.md) · "
        "[`common/beta` · Ghost](../beta/phase9_ghost.md)\n",
    )
    result = extract(
        build(
            tmp_path,
            {"common/alpha": alpha, "common/beta": GAMMA.replace("gamma", "beta").replace("Gamma", "Beta")},
            phases=("common/alpha/phase1_alpha.md", "common/beta/phase1_beta.md"),
        )
    )
    states = {e["target"].rsplit("/", 1)[-1]: e["state"] for e in depends(result)}
    assert states == {"phase1_beta.md": EDGE_UNSATISFIED, "phase9_ghost.md": EDGE_BROKEN}
    (broken,) = codes(result, "DEPENDENCY_EDGE_BROKEN")
    assert "phase9_ghost.md" in broken.summary
    assert broken.provenance.line == 9
    # An unsatisfied edge is work not yet done — it is NOT a finding.
    assert not any("phase1_beta" in f.summary for f in result.findings if f.section.startswith("dependency"))
    # And the generic no-such-node sweep does not report the same defect twice.
    assert [f for f in codes(result, "EDGE_RESOLVES_TO_NO_NODE") if "depends_on" in f.detail] == []


def test_the_four_states_are_distinct_and_the_report_renders_each_on_its_own_row(tmp_path: Path):
    """The vocabulary is four distinct values and the rendered report carries
    four distinct count rows. That a broken and an unsatisfied edge are COUNTED
    apart is :func:`test_a_broken_edge_is_not_an_unsatisfied_one`'s claim; this
    corpus carries no dependency edge and checks the vocabulary and the page."""
    assert len(EDGE_STATES) == 4
    assert {EDGE_SATISFIED, EDGE_UNSATISFIED, EDGE_BROKEN, EDGE_UNDERIVABLE} == EDGE_STATES
    result = extract(build(tmp_path, {"common/alpha": roadmap("Alpha", "Nothing.")}))
    page = render_markdown(result)
    for label in ("…satisfied", "…unsatisfied", "…BROKEN", "…underivable"):
        assert page.count(f"| {label}") == 1, label


def test_a_standard_is_satisfied_by_resolving_and_carries_its_vendoring_banner(tmp_path: Path):
    alpha = roadmap(
        "Alpha",
        "### One 🟠 PLANNED\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "**Depends on:** [Testing Standard](../../../standards/testing/testing_standard.md) · "
        "[Local Standard §2](../../../standards/local/local.md)\n",
    )
    root = build(tmp_path, {"common/alpha": alpha}, phases=("common/alpha/phase1_alpha.md",))
    (root / "standards" / "testing").mkdir(parents=True)
    (root / "standards" / "testing" / "testing_standard.md").write_text(
        "<!-- VENDORED — DO NOT EDIT LOCALLY -->\n> *Vendored from upstream.*\n\n# Testing Standard\n"
    )
    (root / "standards" / "local").mkdir(parents=True)
    (root / "standards" / "local" / "local.md").write_text("# Local\n\n## §2 The rule\n")
    result = extract(root)

    assert {e["state"] for e in depends(result)} == {EDGE_SATISFIED}
    vendored = {n["attrs"]["path"]: n["attrs"]["vendored"] for n in result.graph["nodes"] if n["kind"] == "standard"}
    assert vendored == {"standards/testing/testing_standard.md": True, "standards/local/local.md": False}
    assert codes(result, "DEPENDENCY_EDGE_BROKEN") == []


def test_a_missing_standard_and_a_rotted_standard_anchor_are_broken_edges(tmp_path: Path):
    alpha = roadmap(
        "Alpha",
        "### One 🟠 PLANNED\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "**Depends on:** [Gone](../../../standards/gone/gone.md) · "
        "[Local §9](../../../standards/local/local.md#§9)\n",
    )
    root = build(tmp_path, {"common/alpha": alpha}, phases=("common/alpha/phase1_alpha.md",))
    (root / "standards" / "local").mkdir(parents=True)
    (root / "standards" / "local" / "local.md").write_text("# Local\n\n## §2 The rule\n")
    result = extract(root)

    assert [e["state"] for e in depends(result)] == [EDGE_BROKEN, EDGE_BROKEN]
    reasons = sorted(f.summary for f in codes(result, "DEPENDENCY_EDGE_BROKEN"))
    assert any("no standards document exists" in r for r in reasons)
    assert any("no longer resolves" in r for r in reasons)


def test_a_component_target_is_underivable_and_reported(tmp_path: Path):
    """A dependency points at a PHASE; a component's status line is prose."""
    alpha = roadmap(
        "Alpha",
        "### One 🟠 PLANNED\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "**Depends on:** [`common/beta`](../beta/roadmap.md)\n",
    )
    result = extract(
        build(
            tmp_path,
            {"common/alpha": alpha, "common/beta": BETA},
            phases=("common/alpha/phase1_alpha.md", "common/beta/phase1_beta.md"),
        )
    )
    (edge,) = depends(result)
    assert edge["target"] == "component:development/common/beta"
    assert edge["state"] == EDGE_UNDERIVABLE
    (finding,) = codes(result, "DEPENDENCY_TARGET_UNDERIVABLE")
    assert "whole component" in finding.summary
    assert "roadmap.md#<anchor>" in finding.expected


def test_an_artifact_target_that_resolves_is_a_satisfied_edge(tmp_path: Path):
    """Rule 9: *"a standard or other non-phase artifact: whether it resolves."*
    `service/home-auto`'s live shape — a research paper and `sprints.md` on
    the line. These used to be reported UNDERIVABLE with no edge, which was the
    phase doc narrowing the rule; a phase doc never overrides a binding rule."""
    alpha = roadmap(
        "Alpha",
        "### One 🟠 PLANNED\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "**Depends on:** [the sprint file](../../sprints.md) · "
        "[the paper](./research/paper.md) · [a guide page](../../../docs/guide/page.md)\n",
    )
    root = build(tmp_path, {"common/alpha": alpha}, phases=("common/alpha/phase1_alpha.md",))
    (root / "development" / "common" / "alpha" / "research").mkdir()
    (root / "development" / "common" / "alpha" / "research" / "paper.md").write_text("# Paper\n")
    (root / "docs" / "guide").mkdir(parents=True)
    (root / "docs" / "guide" / "page.md").write_text("# Page\n")
    result = extract(root)

    edges = depends(result)
    assert sorted(e["target"] for e in edges) == [
        "artifact:development/common/alpha/research/paper.md",
        "artifact:development/sprints.md",
        "artifact:docs/guide/page.md",
    ]
    assert {e["state"] for e in edges} == {EDGE_SATISFIED}
    artifacts = [n for n in result.graph["nodes"] if n["kind"] == "artifact"]
    assert len(artifacts) == 3
    assert all("vendored" not in n["attrs"] for n in artifacts), "a banner is a standard's attribute"
    assert codes(result, "DEPENDENCY_TARGET_UNDERIVABLE") == []
    assert codes(result, "DEPENDENCY_EDGE_BROKEN") == []
    assert result.counts["artifacts_depended_on"] == 3


def test_a_missing_artifact_and_a_rotted_artifact_anchor_are_broken_edges(tmp_path: Path):
    alpha = roadmap(
        "Alpha",
        "### One 🟠 PLANNED\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "**Depends on:** [a paper that is not there](./research/gone.md) · "
        "[the paper §gone](./research/paper.md#gone)\n",
    )
    root = build(tmp_path, {"common/alpha": alpha}, phases=("common/alpha/phase1_alpha.md",))
    (root / "development" / "common" / "alpha" / "research").mkdir()
    (root / "development" / "common" / "alpha" / "research" / "paper.md").write_text(
        "# Paper\n\n## The Rule\n"
    )
    result = extract(root)

    assert [e["state"] for e in depends(result)] == [EDGE_BROKEN, EDGE_BROKEN]
    reasons = sorted(f.summary for f in codes(result, "DEPENDENCY_EDGE_BROKEN"))
    assert len(reasons) == 2
    assert any("no such file exists at `development/common/alpha/research/gone.md`" in r for r in reasons)
    assert any("anchor `gone` no longer resolves" in r for r in reasons)
    assert codes(result, "DEPENDENCY_TARGET_UNDERIVABLE") == []


# ---------------------------------------------------------------------------
# Requirement 7 — the anchor forms, and the inline phase node
# ---------------------------------------------------------------------------

INLINE_BETA = roadmap(
    "Beta",
    '### The Substrate <a id="the-substrate"></a> ✅ COMPLETE\n\n- [x] laid\n\n'
    '### The Tower <a id="the-tower"></a> 🟠 PLANNED\n\n**Depends on:** [The Substrate](#the-substrate)\n',
)


def test_a_roadmap_anchor_target_resolves_to_the_inline_phase_and_not_the_component(tmp_path: Path):
    """The headline case: beta's status line reads 🟡 IN PROGRESS and its inline
    phase reads ✅ COMPLETE. The edge must land on the phase and derive satisfied."""
    alpha = roadmap(
        "Alpha",
        "### One 🟠 PLANNED\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "**Depends on:** [`common/beta` · The Substrate](../beta/roadmap.md#the-substrate)\n",
    )
    result = extract(
        build(tmp_path, {"common/alpha": alpha, "common/beta": INLINE_BETA}, phases=("common/alpha/phase1_alpha.md",))
    )
    (edge,) = [e for e in depends(result) if e["source"].startswith("phase:development/common/alpha")]
    assert edge["target"] == "phase:development/common/beta/roadmap.md#the-substrate"
    assert edge["state"] == EDGE_SATISFIED
    inline = node(result, "phase:development/common/beta/roadmap.md#the-substrate")
    assert inline["kind"] == "phase"
    assert inline["attrs"] == {
        "component": "development/common/beta",
        "status": "COMPLETE",
        "owner": "development/common/beta",
        "entry_line": 5,
        "entry_shape": roadmaps.SHAPE_INLINE,
        "inline": True,
        "anchor": "the-substrate",
    }
    assert node(result, "component:development/common/beta")["attrs"]["status"] == "🟡 IN PROGRESS"
    assert codes(result, "PHASE_ANCHOR_MISSING") == []


def test_a_bare_anchor_resolves_against_the_roadmap_it_was_read_from(tmp_path: Path):
    """Rule 9's same-file form. It used to fall through a bare `continue`."""
    result = extract(build(tmp_path, {"common/beta": INLINE_BETA}))
    (edge,) = depends(result)
    assert edge["source"] == "phase:development/common/beta/roadmap.md#the-tower", (
        "the declaration beneath an inline heading belongs to THAT phase"
    )
    assert edge["target"] == "phase:development/common/beta/roadmap.md#the-substrate"
    assert edge["state"] == EDGE_SATISFIED
    assert codes(result, "DEPENDENCY_EDGE_BROKEN") == []


def test_an_anchor_on_an_entry_with_a_document_resolves_to_the_document_node(tmp_path: Path):
    """`common/planning_ui`'s shape: the anchor sits on the line BEFORE the heading, and
    the entry has a phase doc — so the anchor names the doc's node."""
    beta = roadmap(
        "Beta",
        '<a id="beta-one"></a>\n### Beta One ✅ COMPLETE\n\n**Implementation:** [phase1_beta.md](phase1_beta.md)\n',
    )
    alpha = roadmap(
        "Alpha",
        "### One 🟠 PLANNED\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "**Depends on:** [`common/beta` · Beta One](../beta/roadmap.md#beta-one)\n",
    )
    result = extract(
        build(
            tmp_path,
            {"common/alpha": alpha, "common/beta": beta},
            phases=("common/alpha/phase1_alpha.md", "common/beta/phase1_beta.md"),
        )
    )
    (edge,) = depends(result)
    assert edge["target"] == "phase:development/common/beta/phase1_beta.md"
    assert edge["state"] == EDGE_SATISFIED
    assert component(result, "common/beta").anchors == {"beta-one": "phase:development/common/beta/phase1_beta.md"}


def test_an_anchor_naming_no_entry_is_a_broken_edge_with_the_anchor_named(tmp_path: Path):
    alpha = roadmap(
        "Alpha",
        "### One 🟠 PLANNED\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "**Depends on:** [`common/beta` · Nowhere](../beta/roadmap.md#nowhere)\n",
    )
    result = extract(
        build(tmp_path, {"common/alpha": alpha, "common/beta": INLINE_BETA}, phases=("common/alpha/phase1_alpha.md",))
    )
    (edge,) = [e for e in depends(result) if e["source"].startswith("phase:development/common/alpha")]
    assert edge["target"] == "phase:development/common/beta/roadmap.md#nowhere"
    assert edge["state"] == EDGE_BROKEN
    (finding,) = codes(result, "DEPENDENCY_EDGE_BROKEN")
    assert "anchor `#nowhere` names no phase entry" in finding.summary


def test_an_inline_heading_with_no_explicit_anchor_is_a_finding_and_still_a_node(tmp_path: Path):
    """A generated slug dies on rewording; the node exists under an id no link can name."""
    beta = roadmap("Beta", "### The Substrate ✅ COMPLETE\n\n- [x] laid\n")
    result = extract(build(tmp_path, {"common/beta": beta}))
    (finding,) = codes(result, "PHASE_ANCHOR_MISSING")
    assert finding.provenance == ("development/common/beta/roadmap.md", 5) or (
        finding.provenance.file == "development/common/beta/roadmap.md" and finding.provenance.line == 5
    )
    assert "The Substrate" in finding.summary
    inline = node(result, "phase:development/common/beta/roadmap.md@L5")
    assert inline["attrs"]["status"] == "COMPLETE"
    assert inline["attrs"]["anchor"] == ""


# ---------------------------------------------------------------------------
# Requirement 6 — a marker in a phase document is reported, never read
# ---------------------------------------------------------------------------


def test_a_dependency_marker_in_a_phase_document_is_three_separate_findings(tmp_path: Path):
    """One line, three decisions: move it, unqualify it, cite by name."""
    alpha = roadmap(
        "Alpha",
        "### Alpha One 🟠 PLANNED\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "**Depends on:** NONE\n",
    )
    root = build(tmp_path, {"common/alpha": alpha}, phases=("common/alpha/phase1_alpha.md",))
    (root / "development" / "common" / "alpha" / "phase1_alpha.md").write_text(
        "# Alpha One\n\n"
        "**Depends on:** Nothing hard — but see [Phase 0](phase0_alpha.md).\n\n"
        "## Sub-items\n\n"
        "- **Dependencies:** sub-item 2 complete — a sub-item's field, not the phase's\n\n"
        "The convention looks like this:\n\n"
        "```\n**Depends on:** [an illustration](nowhere.md)\n```\n"
    )
    result = extract(root)

    (carrier,) = codes(result, "DEPENDENCY_IN_PHASE_DOC")
    assert carrier.provenance.file == "development/common/alpha/phase1_alpha.md"
    assert carrier.provenance.line == 3
    assert "L3" in carrier.summary and "L7" not in carrier.summary and "L12" not in carrier.summary
    assert "development/common/alpha/roadmap.md:7" in carrier.expected, "names the entry that should carry it"

    (qualified,) = codes(result, "DEPENDENCY_QUALIFIED_NONE")
    assert qualified.provenance.line == 3 and "Nothing hard" in qualified.summary
    (by_number,) = codes(result, "DEPENDENCY_CITES_BY_NUMBER")
    assert by_number.provenance.line == 3 and "`Phase 0`" in by_number.summary

    # Never read as an edge: the roadmap's own NONE is the only declaration.
    assert depends(result) == []
    assert result.counts["phase_docs_carrying_a_dependency_marker"] == 1


def test_an_unqualified_none_in_a_phase_document_is_only_the_one_carrier_finding(tmp_path: Path):
    alpha = roadmap("Alpha", "### Alpha One 🟠 PLANNED\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n")
    root = build(tmp_path, {"common/alpha": alpha}, phases=("common/alpha/phase1_alpha.md",))
    (root / "development" / "common" / "alpha" / "phase1_alpha.md").write_text(
        "# Alpha One\n\n**Depends on:** NONE\n"
    )
    result = extract(root)
    assert len(codes(result, "DEPENDENCY_IN_PHASE_DOC")) == 1
    assert codes(result, "DEPENDENCY_QUALIFIED_NONE") == []
    assert codes(result, "DEPENDENCY_CITES_BY_NUMBER") == []


def test_a_phase_document_nobody_owns_names_the_roadmap_that_should(tmp_path: Path):
    alpha = roadmap("Alpha", "Nothing claims the document below.")
    root = build(tmp_path, {"common/alpha": alpha}, phases=("common/alpha/phase1_alpha.md",))
    (root / "development" / "common" / "alpha" / "phase1_alpha.md").write_text(
        "# Alpha One\n\n**Dependencies:** [Beta](../beta/phase1_beta.md)\n"
    )
    result = extract(root)
    (carrier,) = codes(result, "DEPENDENCY_IN_PHASE_DOC")
    assert "no phase entry there owns this document yet" in carrier.expected
    assert "development/common/alpha/roadmap.md" in carrier.expected


# ---------------------------------------------------------------------------
# The Implementation line is read once
# ---------------------------------------------------------------------------


def test_the_dependency_contract_binds_sources_through_the_roadmap_reader(tmp_path: Path):
    """``_attribute_sources`` consumes ``PhaseRef.section``; it re-reads nothing."""
    root = build(
        tmp_path,
        {"common/alpha": roadmap("Alpha", "### One\n\n**Implementation:** [a](phase1_alpha.md)\n\n**Depends on:** NONE\n")},
        phases=("common/alpha/phase1_alpha.md",),
    )
    collector = Collector()
    c = roadmaps.parse_roadmap(root, "development/common/alpha/roadmap.md", collector)
    assert c is not None and [r.section for r in c.owned] == [2]
    declarations = dependencies.parse_declarations(root, c, collector)
    assert [d.source_id for d in declarations] == ["phase:development/common/alpha/phase1_alpha.md"]
    c.owned.clear()
    declarations = dependencies.parse_declarations(root, c, collector)
    assert [d.source_id for d in declarations] == ["component:development/common/alpha"], (
        "with no owned entry the binding falls to the component — proving the "
        "contract reads the roadmap reader's result and not the line itself"
    )


# ---------------------------------------------------------------------------
# The tail of `_collect_phases` — dedupe, demotion and naming. Added by the
# refine pass: this region had no test constructing an input for it, and two
# silent drops and one mislabelled name were living there.
# ---------------------------------------------------------------------------


def test_a_second_entry_claiming_the_same_document_is_a_finding_and_not_a_silent_drop(
    tmp_path: Path,
):
    """It used to be appended to `references` and then filtered out as already
    owned — gone with no trace. The first claim keeps the status."""
    alpha = roadmap(
        "Alpha",
        "### One ✅ COMPLETE\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "### One again 🟠 PLANNED\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n",
    )
    result = extract(build(tmp_path, {"common/alpha": alpha}, phases=("common/alpha/phase1_alpha.md",)))
    a = component(result, "common/alpha")
    assert [(r.line, r.status) for r in a.owned] == [(7, "COMPLETE")], "first claim wins"
    assert a.referenced == [], "a document the roadmap owns is not also a reference"
    (finding,) = codes(result, "PHASE_CLAIMED_TWICE")
    assert finding.provenance == ("development/common/alpha/roadmap.md", 11) or (
        finding.provenance.file == "development/common/alpha/roadmap.md" and finding.provenance.line == 11
    )
    assert "L7" in finding.summary and "L11" in finding.summary
    assert node(result, "phase:development/common/alpha/phase1_alpha.md")["attrs"]["status"] == "COMPLETE"


def test_two_roadmaps_claiming_one_document_is_a_finding_naming_both(tmp_path: Path):
    """`Component.owns` is a directory prefix, so a parent roadmap can name a
    document under a nested component. Path order used to pick the node's
    status silently."""
    parent = roadmap(
        "Parent",
        "### Nested one 🟠 PLANNED\n\n**Implementation:** [old/phase1_nested.md](old/phase1_nested.md)\n",
    )
    nested = roadmap(
        "Nested", "### One ✅ COMPLETE\n\n**Implementation:** [phase1_nested.md](phase1_nested.md)\n"
    )
    result = extract(
        build(
            tmp_path,
            {"workload/beta": parent, "workload/beta/old": nested},
            phases=("workload/beta/old/phase1_nested.md",),
        )
    )
    (finding,) = codes(result, "PHASE_CLAIMED_TWICE")
    # Roadmaps parse in sorted path order and `…/beta/old/roadmap.md` sorts
    # before `…/beta/roadmap.md`, so the nested entry is the one the node
    # reads and the parent's is the row. Which wins is string order, not a
    # ruling — which is exactly why the row names both.
    assert finding.provenance.file == "development/workload/beta/roadmap.md"
    assert finding.provenance.line == 7
    assert "development/workload/beta/old/roadmap.md:7" in finding.summary
    assert node(result, "phase:development/workload/beta/old/phase1_nested.md")["attrs"] == {
        "component": "development/workload/beta/old",
        "status": "COMPLETE",
        "owner": "development/workload/beta/old",
        "entry_line": 7,
        "entry_shape": roadmaps.SHAPE_IMPLEMENTATION,
    }


def test_a_heading_link_in_a_section_that_also_has_an_implementation_line_is_a_reference(
    tmp_path: Path,
):
    """The `**Implementation:**` line is the entry; the heading's link is a
    reference. It used to be read by neither branch — dropped with no node,
    edge or finding."""
    alpha = roadmap(
        "Alpha",
        "## [Two](phase2_alpha.md) 🟠 PLANNED\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n",
    )
    result = extract(
        build(
            tmp_path,
            {"common/alpha": alpha},
            phases=("common/alpha/phase1_alpha.md", "common/alpha/phase2_alpha.md"),
        )
    )
    a = component(result, "common/alpha")
    assert [r.path.rsplit("/", 1)[-1] for r in a.owned] == ["phase1_alpha.md"]
    assert [(r.path.rsplit("/", 1)[-1], r.line) for r in a.referenced] == [("phase2_alpha.md", 5)]
    assert edges_of_kind(result, "references", "component:development/common/alpha") == {
        "phase:development/common/alpha/phase2_alpha.md"
    }


def test_an_entry_s_name_is_the_heading_text_before_its_marker(tmp_path: Path):
    """40 of 117 live entries carried `🟠 PLANNED` inside their name, and an
    inline node's label is that name."""
    beta = roadmap(
        "Beta",
        '<a id="beta-one"></a>\n### Beta One — the substrate ✅ COMPLETE\n\n'
        "**Implementation:** [phase1_beta.md](phase1_beta.md)\n\n"
        '### The Tower <a id="the-tower"></a> 🟠 PLANNED\n\n- [ ] build it\n',
    )
    root = build(tmp_path, {"common/beta": beta}, phases=("common/beta/phase1_beta.md",))
    (root / "development" / "common" / "beta" / "phase1_beta.md").write_text(
        "# Beta One\n\n**Depends on:** NONE\n"
    )
    result = extract(root)
    assert [r.name for r in component(result, "common/beta").owned] == [
        "Beta One — the substrate",
        "The Tower",
    ]
    assert node(result, "phase:development/common/beta/roadmap.md#the-tower")["label"] == "The Tower"
    (carrier,) = codes(result, "DEPENDENCY_IN_PHASE_DOC")
    assert "the entry for `Beta One — the substrate`" in carrier.expected


def test_deprecated_is_a_prefix_and_a_heading_that_merely_mentions_it_is_live(tmp_path: Path):
    """Rule 5: a canceled phase carries a `DEPRECATED` PREFIX."""
    alpha = roadmap(
        "Alpha",
        "### DEPRECATED — the old way\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "### Retire the DEPRECATED resolver 🟠 PLANNED\n\n**Implementation:** [phase2_alpha.md](phase2_alpha.md)\n",
    )
    result = extract(
        build(
            tmp_path,
            {"common/alpha": alpha},
            phases=("common/alpha/phase1_alpha.md", "common/alpha/phase2_alpha.md"),
        )
    )
    assert [r.status for r in component(result, "common/alpha").owned] == ["DEPRECATED", "PLANNED"]


def test_a_bare_nothing_in_a_phase_document_is_unqualified(tmp_path: Path):
    """The pre-2026-09-07 spelling, unqualified. The qualified-token check used
    to compare against `NONE_RE`, which knows one spelling, and reported a
    qualifier that was not there."""
    alpha = roadmap("Alpha", "### Alpha One 🟠 PLANNED\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n")
    root = build(tmp_path, {"common/alpha": alpha}, phases=("common/alpha/phase1_alpha.md",))
    (root / "development" / "common" / "alpha" / "phase1_alpha.md").write_text(
        "# Alpha One\n\n**Depends on:** nothing.\n"
    )
    result = extract(root)
    assert len(codes(result, "DEPENDENCY_IN_PHASE_DOC")) == 1
    assert codes(result, "DEPENDENCY_QUALIFIED_NONE") == []


def test_an_external_target_on_a_declaration_is_reported_and_not_dropped(tmp_path: Path):
    """Rule 9: a dependency on another ecosystem's artifact stays. `_links_in`
    used to `continue` past an `https://` target with no finding — the same
    shape as the bare-anchor drop."""
    alpha = roadmap(
        "Alpha",
        "### One 🟠 PLANNED\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "**Depends on:** [the upstream release](https://example.invalid/release)\n",
    )
    result = extract(build(tmp_path, {"common/alpha": alpha}, phases=("common/alpha/phase1_alpha.md",)))
    assert depends(result) == [], "no node to point at, so no edge"
    (finding,) = codes(result, "DEPENDENCY_TARGET_UNDERIVABLE")
    assert "https://example.invalid/release" in finding.summary
    assert "outside this checkout" in finding.summary
    assert finding.provenance.line == 9


def test_an_indented_checkbox_is_a_sub_item_and_never_a_legacy_entry(tmp_path: Path):
    """`service/github-automation:142` live: a sub-item citing `phase2…#d1` was
    read as phase 2's entry, and the real entry two lines down was deduplicated
    away — so the phase's status came from a sub-item's `[ ]`."""
    alpha = roadmap(
        "Alpha",
        "- [x] **One** ([phase1_alpha.md](phase1_alpha.md)) — done\n"
        "  - [ ] **[Two's D1](phase2_alpha.md#d1)** — a sub-item that opens with the link\n"
        "- [x] **Two** ([phase2_alpha.md](phase2_alpha.md)) — also done\n",
    )
    result = extract(
        build(
            tmp_path,
            {"common/alpha": alpha},
            phases=("common/alpha/phase1_alpha.md", "common/alpha/phase2_alpha.md"),
        )
    )
    a = component(result, "common/alpha")
    assert [(r.path.rsplit("/", 1)[-1], r.line, r.status) for r in a.owned] == [
        ("phase1_alpha.md", 5, "COMPLETE"),
        ("phase2_alpha.md", 7, "COMPLETE"),
    ]
    assert codes(result, "PHASE_CLAIMED_TWICE") == []


def test_a_prose_citation_of_a_later_phase_does_not_steal_its_entry(tmp_path: Path):
    """`common/temporal:30` live: the Harbor entry's prose cites phase 7, and it
    sat above phase 7's own entry — so first-link-wins credited Harbor with
    phase 7 and the one-carrier finding named the wrong entry."""
    alpha = roadmap(
        "Alpha",
        "- [ ] **Harbor** (~10h) — pushes images; currency is [seven](phase7_alpha.md)'s job\n"
        "- [x] **[Seven](phase7_alpha.md)** — the gate\n",
    )
    result = extract(build(tmp_path, {"common/alpha": alpha}, phases=("common/alpha/phase7_alpha.md",)))
    (ref,) = component(result, "common/alpha").owned
    assert (ref.line, ref.name, ref.status) == (6, "Seven", "COMPLETE")
    assert codes(result, "PHASE_CLAIMED_TWICE") == [], "a losing weak claim is a citation, not a finding"

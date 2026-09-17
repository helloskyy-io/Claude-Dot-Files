"""The Dependency Contract — the parser, the dispositions and the two worklists.

Each corpus here is built in ``tmp_path`` rather than added to the shared
fixture tree, for the same reason the fixture tree exists at all: the shapes
under test are adversarial, and a corpus that has to carry a cycle, a broken
dependency link and a deliberately mismatched prose line in order to be a test
subject stops being a readable example of anything else.

**Every behavioural claim here was probed against the LIVE corpus first and the
assertion written from what the parser actually did.** That order caught the
headline defect on this PR: attributing a declaration to *the section's own
phase link, when there is exactly one* invents an attribution for a section that
has no phase document of its own, and the invented self-edge was then reported
as a real cycle in the plan. It is asserted directly, below.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from planning_ui.plan_extractor import dependencies, extract

SPRINTS = """# Implementation Plan

## Sprint: Everything
🟡 IN PROGRESS

- [x] **common/alpha · One** · L1 · ([roadmap](./common/alpha/roadmap.md)) — done · **~2h**
"""


def build(tmp_path: Path, roadmaps: dict[str, str], phases: tuple[str, ...] = ()) -> Path:
    """A miniature corpus. ``roadmaps`` maps ``<domain>/<name>`` to roadmap text."""
    root = tmp_path / "corpus"
    (root / "development").mkdir(parents=True)
    (root / "development" / "sprints.md").write_text(SPRINTS, encoding="utf-8")
    for slug, text in roadmaps.items():
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


def disposition_of(result, component: str) -> str:
    (row,) = [r for r in result.dependency_accounting if r.component == component]
    return row.disposition


def depends_edges(result) -> list[tuple[str, str, int]]:
    return [
        (e["source"], e["target"], e["line"])
        for e in result.graph["edges"]
        if e["kind"] == "depends_on"
    ]


# ---------------------------------------------------------------------------
# The ruled format
# ---------------------------------------------------------------------------


def _two_component_corpus(tmp_path: Path, alpha_body: str) -> Path:
    return build(
        tmp_path,
        {
            "common/alpha": roadmap("Alpha", alpha_body),
            "common/beta": roadmap(
                "Beta",
                "### Beta One\n\n**Implementation:** [phase1_beta.md](phase1_beta.md)\n",
            ),
        },
        phases=("common/alpha/phase1_alpha.md", "common/beta/phase1_beta.md"),
    )


ALPHA_CONFORMING = (
    "### Alpha One\n\n"
    "**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
    "**Depends on:** [`common/beta` · Beta One](../beta/phase1_beta.md) — satisfied already.\n"
)


def test_the_ruled_format_parses_into_an_edge_from_the_phase_entry(tmp_path: Path):
    """The exemplar shape, end to end: marker, link, prose, phase attribution."""
    result = extract(_two_component_corpus(tmp_path, ALPHA_CONFORMING))

    assert depends_edges(result) == [
        (
            "phase:development/common/alpha/phase1_alpha.md",
            "phase:development/common/beta/phase1_beta.md",
            9,
        )
    ]
    assert disposition_of(result, "development/common/alpha") == dependencies.RESOLVES


def test_prose_after_the_links_is_ignored_and_never_becomes_an_edge(tmp_path: Path):
    """*The parser reads only the links. Prose stays and stays valuable.*"""
    body = ALPHA_CONFORMING.replace(
        "— satisfied already.",
        "— satisfied, landed in the same PR. Coordinates with Sprint 2-1d; "
        "see §4 and the UDM BGP work.",
    )
    result = extract(_two_component_corpus(tmp_path, body))
    assert len(depends_edges(result)) == 1
    assert disposition_of(result, "development/common/alpha") == dependencies.RESOLVES


def test_a_mid_paragraph_marker_is_READ_and_reported_as_non_conforming(tmp_path: Path):
    """``common/clusters``'s live shape, reduced — and the reason the
    first draft of this parser was wrong.

    Four roadmaps write a marker mid-paragraph and one of them carries a link
    that RESOLVES. A line-anchored parser drops the declaration and then puts
    its owner on the *go author a dependency* worklist for a dependency they
    already wrote. The deviation is a finding; it is never a reason to stop
    reading.
    """
    body = (
        "### Alpha One\n\n"
        "**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "Corrects the base mis-scoping. **Depends on:** "
        "[`common/beta` · Beta One](../beta/phase1_beta.md) landing first.\n"
    )
    result = extract(_two_component_corpus(tmp_path, body))

    assert len(depends_edges(result)) == 1, "a recorded dependency, read"
    assert disposition_of(result, "development/common/alpha") == dependencies.RESOLVES
    (finding,) = codes(result, "DEPENDENCY_MARKER_NON_CONFORMING")
    assert "mid-paragraph" in finding.detail
    assert finding.expected == "`**Depends on:**` at the start of its line"


def test_the_second_spelling_is_READ_and_reported_as_non_conforming(tmp_path: Path):
    """``**Dependencies:**`` — 10 roadmaps, `common/backend` under every entry.

    The phase doc's corpus survey missed this shape, which is why it counted 28
    roadmaps as declaring nothing. Refusing the spelling sends ten owners the
    authoring remedy when the work they owe is converting.
    """
    body = (
        "### Alpha One\n\n"
        "**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "**Dependencies:** [`common/beta` · Beta One](../beta/phase1_beta.md)\n"
    )
    result = extract(_two_component_corpus(tmp_path, body))

    assert len(depends_edges(result)) == 1
    assert disposition_of(result, "development/common/alpha") == dependencies.RESOLVES
    (finding,) = codes(result, "DEPENDENCY_MARKER_NON_CONFORMING")
    assert "**Dependencies:**" in finding.detail


def test_a_marker_inside_a_code_span_is_prose_about_the_marker(tmp_path: Path):
    """``common/planning_ui``'s own roadmap contains this exact sentence.

    Without the exclusion a document that DESCRIBES the convention is read as
    USING it — and this component's roadmap would declare a dependency on the
    Backstage documentation page it cites.
    """
    body = (
        "### Alpha One\n\n"
        "**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "The convention is a `**Depends on:**` line under each phase entry, "
        "linking [`common/beta` · Beta One](../beta/phase1_beta.md).\n"
    )
    result = extract(_two_component_corpus(tmp_path, body))
    assert depends_edges(result) == []
    assert codes(result, "DEPENDENCY_MARKER_NON_CONFORMING") == []
    assert disposition_of(result, "development/common/alpha") == dependencies.WORKLIST_UNDECLARED


def test_a_marker_inside_a_fenced_block_is_an_example_not_a_declaration(tmp_path: Path):
    """A roadmap that SHOWS the format must not be read as declaring it."""
    body = (
        "### Alpha One\n\n"
        "**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "```markdown\n"
        "**Depends on:** [`common/beta` · Beta One](../beta/phase1_beta.md)\n"
        "```\n"
    )
    result = extract(_two_component_corpus(tmp_path, body))
    assert depends_edges(result) == []
    assert disposition_of(result, "development/common/alpha") == dependencies.WORKLIST_UNDECLARED


def test_a_conforming_declaration_raises_no_conformance_finding(tmp_path: Path):
    """The negative half — the conformance check must not fire on the exemplar."""
    result = extract(_two_component_corpus(tmp_path, ALPHA_CONFORMING))
    assert codes(result, "DEPENDENCY_MARKER_NON_CONFORMING") == []


def test_a_list_beneath_an_empty_marker_line_is_read(tmp_path: Path):
    """``common/networking`` and ``common/imager`` both write it this way."""
    body = (
        "### Alpha One\n\n"
        "**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "**Depends on:**\n"
        "- [`common/beta` · Beta One](../beta/phase1_beta.md)\n"
        "- Sprint 1-1 — already complete\n"
    )
    result = extract(_two_component_corpus(tmp_path, body))
    assert len(depends_edges(result)) == 1
    assert disposition_of(result, "development/common/alpha") == dependencies.RESOLVES


def test_a_list_beneath_a_marker_line_that_already_carries_text_is_not_swallowed(
    tmp_path: Path,
):
    """The stated blind spot, asserted rather than left to be discovered.

    Only a list beneath an EMPTY marker line is read as a continuation. A list
    following a marker line that already carries prose is not, because grabbing
    it would author edges nobody declared — and a false edge feeds a diagram
    presented as the platform's dependency graph.
    """
    body = (
        "### Alpha One\n\n"
        "**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "**Depends on:** NONE yet. Out of scope below:\n"
        "- [`common/beta` · Beta One](../beta/phase1_beta.md)\n"
    )
    result = extract(_two_component_corpus(tmp_path, body))
    assert depends_edges(result) == []


# ---------------------------------------------------------------------------
# Requirement 3 — a link that resolves to no node is a finding, not a drop
# ---------------------------------------------------------------------------


def test_a_dependency_link_to_a_phase_that_does_not_exist_is_reported(tmp_path: Path):
    """Adversarial, and the reason the worklists are trustworthy at all.

    A dropped edge makes a broken link read as a satisfied dependency. The edge
    is emitted so it can be reported, and the roadmap still lands on a worklist
    rather than reading as resolved.
    """
    body = (
        "### Alpha One\n\n"
        "**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "**Depends on:** [`common/beta` · Ghost](../beta/phase9_ghost.md)\n"
    )
    result = extract(_two_component_corpus(tmp_path, body))

    # Under the dependency contract's OWN code — a broken edge is a defect in
    # the corpus, distinct from an unsatisfied one, and it is reported once
    # here rather than a second time by the generic no-such-node sweep.
    (finding,) = codes(result, "DEPENDENCY_EDGE_BROKEN")
    assert "phase9_ghost.md" in finding.summary
    assert finding.provenance.file == "development/common/alpha/roadmap.md"
    assert finding.provenance.line == 9
    assert [
        f for f in codes(result, "EDGE_RESOLVES_TO_NO_NODE") if "Edge kind: depends_on" in f.detail
    ] == [], "one defect, one row"
    (edge,) = [e for e in result.graph["edges"] if e["kind"] == "depends_on"]
    assert edge["state"] == "broken", "the edge is emitted, in the broken state, so it can be reported"
    assert disposition_of(result, "development/common/alpha") == dependencies.WORKLIST_PROSE_ONLY


def test_a_dependency_edge_leaving_a_phase_that_does_not_exist_is_reported(tmp_path: Path):
    """The SOURCE end, which a target-only check cannot see.

    A declaration's source is derived from its section's `**Implementation:**`
    link, and that link can point at a phase document nobody wrote. The edge
    then leaves a node the graph does not have — and every consumer that walks
    outward from real nodes silently never meets it.

    **This test exists because a mutation found its absence.** Reverting the
    both-ends check to target-only left the whole suite green.
    """
    body = (
        "### Alpha One\n\n"
        "**Implementation:** [phase9_ghost.md](phase9_ghost.md)\n\n"
        "**Depends on:** [`common/beta` · Beta One](../beta/phase1_beta.md)\n"
    )
    result = extract(_two_component_corpus(tmp_path, body))

    (source_finding,) = [
        f
        for f in codes(result, "EDGE_RESOLVES_TO_NO_NODE")
        if "Edge kind: depends_on" in f.detail
    ]
    assert "source" in source_finding.summary
    assert "phase9_ghost.md" in source_finding.summary
    # The edge itself is still emitted — reporting it is only possible because
    # it was not dropped.
    assert depends_edges(result) == [
        (
            "phase:development/common/alpha/phase9_ghost.md",
            "phase:development/common/beta/phase1_beta.md",
            9,
        )
    ]


def test_a_link_to_a_standard_is_a_dependency_satisfied_by_resolving(tmp_path: Path):
    """``common/imager``'s live shape: a Vault Standard link on a
    ``Depends on:`` block.

    **This test used to assert the opposite** — that a standard is a reference
    and never an edge. Documentation Standard rule 9, ratified 2026-09-06, makes
    a standard a legal target: *"satisfied by resolving, plus its vendoring
    banner where it carries one."* The edge is emitted onto a `standard` node,
    derives `satisfied`, and the roadmap resolves.
    """
    root = _two_component_corpus(
        tmp_path,
        "### Alpha One\n\n"
        "**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "**Depends on:**\n"
        "- Vault operational per [Vault Standard §6](../../../standards/secrets/vault.md)\n",
    )
    (root / "standards" / "secrets").mkdir(parents=True)
    (root / "standards" / "secrets" / "vault.md").write_text("# Vault Standard\n\n§6\n")

    result = extract(root)
    assert depends_edges(result) == [
        ("phase:development/common/alpha/phase1_alpha.md", "standard:standards/secrets/vault.md", 10)
    ]
    (edge,) = [e for e in result.graph["edges"] if e["kind"] == "depends_on"]
    assert edge["state"] == "satisfied"
    (node,) = [n for n in result.graph["nodes"] if n["kind"] == "standard"]
    assert node["attrs"]["vendored"] is False
    assert codes(result, "DEPENDENCY_EDGE_BROKEN") == []
    assert disposition_of(result, "development/common/alpha") == dependencies.RESOLVES


# ---------------------------------------------------------------------------
# The exception list — and both directions of it
# ---------------------------------------------------------------------------


def test_a_retired_component_is_excepted_from_its_own_status_line(tmp_path: Path):
    """``workload/probe``'s shape. On the strength of the line, not the name."""
    root = build(
        tmp_path,
        {
            "workload/gone": roadmap(
                "Gone",
                "Nothing is deployed.",
                status="⚫ **RETIRED 2026-08-21.** Torn down.",
            )
        },
    )
    result = extract(root)
    assert disposition_of(result, "development/workload/gone") == dependencies.EXCEPTION_RETIRED
    assert codes(result, "DEPENDENCY_UNDECLARED") == []


def test_a_coordination_document_is_excepted_and_one_with_phase_docs_is_not(tmp_path: Path):
    """**Both directions are the check**, exactly as the phase doc puts it.

    A wrong exception hides a gap permanently; a wrong worklist entry merely
    annoys an owner. ``coord`` owns no phase document and sequences two other
    components — the ``common/vm_orch`` shape. ``gpu`` links the same
    two AND owns two phases of its own — the ``common/gpu_operations`` shape,
    which is emphatically not an exception.
    """
    sequencing = (
        "Sequences [Alpha One](../alpha/phase1_alpha.md) then "
        "[Beta One](../beta/phase1_beta.md).\n"
    )
    root = build(
        tmp_path,
        {
            "common/alpha": roadmap("Alpha", "[one](phase1_alpha.md)"),
            "common/beta": roadmap("Beta", "[one](phase1_beta.md)"),
            "common/coord": roadmap("Coord", sequencing),
            "common/gpu": roadmap(
                "Gpu",
                sequencing + "\nIts own: [a](phase1_gpu.md) and [b](phase2_gpu.md)\n",
            ),
        },
        phases=(
            "common/alpha/phase1_alpha.md",
            "common/beta/phase1_beta.md",
            "common/gpu/phase1_gpu.md",
            "common/gpu/phase2_gpu.md",
        ),
    )
    result = extract(root)
    assert (
        disposition_of(result, "development/common/coord")
        == dependencies.EXCEPTION_COORDINATION
    )
    assert (
        disposition_of(result, "development/common/gpu") == dependencies.WORKLIST_UNDECLARED
    ), "a component with phase docs of its own has nodes, so it owes a declaration"


@pytest.mark.parametrize(
    ("name", "body"),
    [
        # `service/logging`'s shape: a roadmap, no phase documents, no links out.
        ("lonely", "A roadmap that names no phase and links nothing."),
        # `common/resilience` / `service/monitoring`: no phase documents of its
        # own, and ONE other component's phase linked. One is not "sequences".
        ("single", "Waits on [Alpha One](../alpha/phase1_alpha.md) before it starts."),
    ],
)
def test_no_phase_docs_alone_does_not_earn_the_coordination_exception(
    tmp_path: Path, name: str, body: str
):
    """The half of the exception rule with no live example to fail on.

    The phase doc's implementation step abbreviates the class to
    *"roadmap-with-no-phase-docs"*. Taken literally that excepts every unbuilt
    component in the corpus — six of them today — and an exception hides a gap
    PERMANENTLY while a worklist entry merely annoys an owner. The full
    definition is *indexes work owned elsewhere*: no phases of its own AND phase
    links into two or more other components.
    """
    root = build(
        tmp_path,
        {
            "common/alpha": roadmap("Alpha", "**Implementation:** [a](phase1_alpha.md)"),
            f"common/{name}": roadmap(name.title(), body),
        },
        phases=("common/alpha/phase1_alpha.md",),
    )
    result = extract(root)
    assert (
        disposition_of(result, f"development/common/{name}")
        == dependencies.WORKLIST_UNDECLARED
    )


def test_an_unqualified_NONE_is_the_standalone_exception(tmp_path: Path):
    root = build(
        tmp_path,
        {"common/alpha": roadmap("Alpha", "**Depends on:** NONE; fully startable today.")},
    )
    result = extract(root)
    assert (
        disposition_of(result, "development/common/alpha") == dependencies.EXCEPTION_STANDALONE
    )


@pytest.mark.parametrize(
    "line",
    [
        "**Depends on:** nothing inside this component. Blocked by two operator calls.",
        "**Depends on:** nothing internal. Runs concurrently with the Register.",
    ],
)
def test_a_qualified_NONE_is_not_a_standalone_declaration(tmp_path: Path, line: str):
    """Both live wordings, and both say something narrower than *nothing*.

    They are silent about external dependencies, so they are not the positive
    record the standalone class asks for. Erring toward the worklist is the
    direction the phase doc rules for.
    """
    root = build(tmp_path, {"common/alpha": roadmap("Alpha", line)})
    result = extract(root)
    assert (
        disposition_of(result, "development/common/alpha") == dependencies.WORKLIST_PROSE_ONLY
    )


# ---------------------------------------------------------------------------
# The two worklists
# ---------------------------------------------------------------------------


def test_declaring_nothing_and_declaring_in_prose_are_different_findings(tmp_path: Path):
    """Different remedies — authoring versus converting — so different codes."""
    root = build(
        tmp_path,
        {
            "common/alpha": roadmap("Alpha", "**Depends on:** Phase 1 complete. Ceph CSI."),
            "common/beta": roadmap("Beta", "No dependency line anywhere in this document."),
        },
    )
    result = extract(root)

    (prose,) = codes(result, "DEPENDENCY_PROSE_ONLY")
    assert prose.provenance.file == "development/common/alpha/roadmap.md"
    assert "CONVERTING" in prose.detail

    (undeclared,) = codes(result, "DEPENDENCY_UNDECLARED")
    assert undeclared.provenance.file == "development/common/beta/roadmap.md"
    assert "owner" in undeclared.detail


def test_one_conforming_line_does_not_clear_a_roadmap_that_also_carries_prose(
    tmp_path: Path,
):
    """The rollup decision, asserted because a reasonable engineer would differ.

    Both live exemplars carry one conforming line and several prose ones.
    Reporting the roadmap as resolved on the strength of the conforming one
    would hide the rest behind it — and the conforming line still parses into a
    real edge, which is what validates the format.
    """
    body = ALPHA_CONFORMING + "\n### Alpha Two\n\n**Depends on:** Sprint 7 landing first.\n"
    result = extract(_two_component_corpus(tmp_path, body))

    assert disposition_of(result, "development/common/alpha") == dependencies.WORKLIST_PROSE_ONLY
    assert len(depends_edges(result)) == 1, "the conforming line still yields its edge"
    (row,) = [
        r for r in result.dependency_accounting if r.component == "development/common/alpha"
    ]
    assert row.resolving_lines == (9,)
    assert row.unresolved_lines == (13,)


def test_a_dependencies_md_beside_the_roadmap_is_named_as_a_cheap_close(tmp_path: Path):
    """*Naming the file its owner can read the answer out of costs nothing.*"""
    root = build(tmp_path, {"common/alpha": roadmap("Alpha", "No line here.")})
    (root / "development" / "common" / "alpha" / "dependencies.md").write_text("# Matrix\n")
    result = extract(root)
    (finding,) = codes(result, "DEPENDENCY_UNDECLARED")
    assert "cheap close" in finding.detail
    assert "alpha/dependencies.md" in finding.detail


def test_every_roadmap_lands_in_exactly_one_disposition(tmp_path: Path):
    """Requirement 2's spine: nothing falls through silently.

    The check is over the ACCOUNTING rather than over the findings, because a
    roadmap that resolves or is excepted emits no finding — and *no finding* is
    exactly what an omission looks like.
    """
    root = build(
        tmp_path,
        {
            "common/alpha": roadmap("Alpha", ALPHA_CONFORMING),
            "common/beta": roadmap("Beta", "**Implementation:** [b](phase1_beta.md)"),
            "common/coord": roadmap(
                "Coord",
                "Sequences [a](../alpha/phase1_alpha.md) and [b](../beta/phase1_beta.md).",
            ),
            "common/gamma": roadmap("Gamma", "**Depends on:** nothing."),
            "workload/gone": roadmap("Gone", "x", status="⚫ RETIRED"),
            "service/delta": roadmap("Delta", "**Depends on:** Phase 1 complete."),
        },
        phases=("common/alpha/phase1_alpha.md", "common/beta/phase1_beta.md"),
    )
    result = extract(root)

    components = {c.path for c in result.components}
    accounted = [row.component for row in result.dependency_accounting]
    assert sorted(accounted) == sorted(components), "every roadmap has a row"
    assert len(accounted) == len(set(accounted)), "and exactly one"

    valid = (
        {dependencies.RESOLVES} | dependencies.EXCEPTIONS | dependencies.WORKLISTS
    )
    assert {row.disposition for row in result.dependency_accounting} <= valid

    worklisted = {
        row.component
        for row in result.dependency_accounting
        if row.disposition in dependencies.WORKLISTS
    }
    from_findings = {
        f.provenance.file.removesuffix("/roadmap.md")
        for f in result.findings
        if f.code in {"DEPENDENCY_UNDECLARED", "DEPENDENCY_PROSE_ONLY"}
    }
    assert worklisted == from_findings, "the table and the worklists cannot disagree"


# ---------------------------------------------------------------------------
# Prose/link mismatch
# ---------------------------------------------------------------------------


def test_prose_naming_a_component_the_links_omit_is_flagged(tmp_path: Path):
    """Requirement 5, verified against a deliberately mismatched line."""
    body = ALPHA_CONFORMING.replace(
        "— satisfied already.",
        "— and on service/gamma's exporter work landing first.",
    )
    root = build(
        tmp_path,
        {
            "common/alpha": roadmap("Alpha", body),
            "common/beta": roadmap("Beta", "**Implementation:** [b](phase1_beta.md)"),
            "service/gamma": roadmap("Gamma", "**Depends on:** nothing."),
        },
        phases=("common/alpha/phase1_alpha.md", "common/beta/phase1_beta.md"),
    )
    result = extract(root)
    (finding,) = codes(result, "DEPENDENCY_PROSE_LINK_MISMATCH")
    assert "service/gamma" in finding.summary
    assert finding.provenance.line == 9
    assert "common/beta" in finding.detail, "the linked side is named too"


def test_a_component_named_in_prose_AND_linked_is_not_a_mismatch(tmp_path: Path):
    """The negative half. The link text carries the slug by convention, so a
    check that read the link text would fire on every conforming line."""
    result = extract(_two_component_corpus(tmp_path, ALPHA_CONFORMING))
    assert codes(result, "DEPENDENCY_PROSE_LINK_MISMATCH") == []


def test_prose_naming_a_component_is_not_satisfied_by_a_link_to_a_document_inside_it(
    tmp_path: Path,
):
    """An `artifact:` link resolves (rule 9), so the line is LINE_RESOLVES and
    this check runs on it — but a research paper under `service/gamma/` is a
    link to the paper, not to `service/gamma`'s plan. Credited to the component
    by directory prefix alone, prose naming the component would read as linked
    while no phase of it is, and the mismatch would never be reported."""
    body = (
        "### Alpha One\n\n"
        "**Implementation:** [a](phase1_alpha.md)\n\n"
        "**Depends on:** service/gamma's exporter work, described in "
        "[gamma's notes](../../service/gamma/research/notes.md)\n"
    )
    root = build(
        tmp_path,
        {
            "common/alpha": roadmap("Alpha", body),
            "service/gamma": roadmap("Gamma", "**Depends on:** nothing."),
        },
        phases=("common/alpha/phase1_alpha.md",),
    )
    paper = root / "development" / "service" / "gamma" / "research" / "notes.md"
    paper.parent.mkdir(parents=True)
    paper.write_text("# Notes\n")
    result = extract(root)

    # The artifact edge itself is satisfied — the paper resolves.
    assert [e["state"] for e in result.graph["edges"] if e["kind"] == "depends_on"] == ["satisfied"]
    (finding,) = codes(result, "DEPENDENCY_PROSE_LINK_MISMATCH")
    assert "`service/gamma`" in finding.summary, finding.summary
    assert "Linked components on this line: none" in finding.detail, finding.detail


def test_the_mismatch_check_stays_off_a_line_that_resolves_nothing(tmp_path: Path):
    """Scoped deliberately: on a prose-only line every name would fire, and the
    owner would get the same roadmap on two worklists saying one thing."""
    root = build(
        tmp_path,
        {
            "common/alpha": roadmap("Alpha", "**Depends on:** service/gamma's exporter."),
            "service/gamma": roadmap("Gamma", "**Depends on:** nothing."),
        },
    )
    result = extract(root)
    assert codes(result, "DEPENDENCY_PROSE_LINK_MISMATCH") == []
    assert codes(result, "DEPENDENCY_PROSE_ONLY")


# ---------------------------------------------------------------------------
# Cycles
# ---------------------------------------------------------------------------


def _cycle_corpus(tmp_path: Path) -> Path:
    return build(
        tmp_path,
        {
            "common/alpha": roadmap(
                "Alpha",
                "### Alpha One\n\n**Implementation:** [a](phase1_alpha.md)\n\n"
                "**Depends on:** [`common/beta` · Beta One](../beta/phase1_beta.md)\n",
            ),
            "common/beta": roadmap(
                "Beta",
                "### Beta One\n\n**Implementation:** [b](phase1_beta.md)\n\n"
                "**Depends on:** [`common/alpha` · Alpha One](../alpha/phase1_alpha.md)\n",
            ),
        },
        phases=("common/alpha/phase1_alpha.md", "common/beta/phase1_beta.md"),
    )


def test_a_cycle_is_reported_once_naming_the_two_entries_that_close_it(tmp_path: Path):
    result = extract(_cycle_corpus(tmp_path))
    (finding,) = codes(result, "DEPENDENCY_CYCLE")
    assert "phase1_alpha.md" in finding.summary and "phase1_beta.md" in finding.summary
    assert "→" in finding.detail
    assert "never resolved" in finding.detail
    assert finding.provenance.line > 0


def test_prose_naming_a_PARENT_component_is_not_satisfied_by_a_link_into_its_CHILD(
    tmp_path: Path,
):
    """`workload/probe` and `workload/probe/old` are both live components.

    Deriving the linked component by positional split — the second and third
    path segments — credits a link into the nested component to its parent, so
    prose naming the parent reads as already satisfied and the mismatch is never
    reported. The component set is already in hand; longest-prefix against it is
    the only derivation that can tell the two apart.
    """
    body = (
        "### Alpha One\n\n"
        "**Implementation:** [a](phase1_alpha.md)\n\n"
        "**Depends on:** [`workload/beta/old` · Old Beta](../../workload/beta/old/phase1_old.md)"
        " — and on workload/beta itself, which is NOT linked\n"
    )
    root = build(
        tmp_path,
        {
            "common/alpha": roadmap("Alpha", body),
            "workload/beta": roadmap("Beta", "### Beta One\n"),
            "workload/beta/old": roadmap("Old Beta", "### Old Beta One\n"),
        },
        phases=("workload/beta/old/phase1_old.md", "common/alpha/phase1_alpha.md"),
    )
    result = extract(root)

    (finding,) = codes(result, "DEPENDENCY_PROSE_LINK_MISMATCH")
    assert "`workload/beta`" in finding.summary, finding.summary
    # And the child it IS linked to is credited to the child, not to the parent.
    assert "`workload/beta/old`" in finding.detail, finding.detail


def test_a_roadmap_mixing_a_resolving_line_and_a_nothing_line_does_not_claim_both_resolve(
    tmp_path: Path,
):
    """`resolving_lines` exists to keep two ideas apart; the reason must too.

    An owner-authored `NONE` is neither unresolved nor a resolving LINK.
    Saying *"all 2 declarations resolve"* of a roadmap carrying one of each
    claims a link that does not exist — the "reads healthier than it is" failure
    this phase names repeatedly, in the tool's own output.
    """
    body = (
        "### Alpha One\n\n"
        "**Implementation:** [a](phase1_alpha.md)\n\n"
        "**Depends on:** [`common/beta` · Beta One](../beta/phase1_beta.md)\n\n"
        "### Alpha Two\n\n"
        "**Depends on:** NONE.\n"
    )
    result = extract(_two_component_corpus(tmp_path, body))

    (row,) = [r for r in result.dependency_accounting if r.component == "development/common/alpha"]
    assert row.disposition == dependencies.RESOLVES
    assert len(row.declaration_lines) == 2 and len(row.resolving_lines) == 1
    assert "1 resolving to a node" in row.reason, row.reason
    assert "1 owner-declared `NONE`" in row.reason, row.reason


def test_an_unterminated_fence_is_a_finding_and_not_a_silent_drop(tmp_path: Path):
    """The one shape that could make this parser lie by omission.

    A fence that is opened and never closed hides every line below it, and a
    roadmap whose declarations are all below it lands on the *declares nothing*
    worklist — indistinguishable from one that genuinely declares nothing. The
    module's whole spine is that what it cannot read is a finding.
    """
    body = (
        "### Alpha One\n\n"
        "**Implementation:** [a](phase1_alpha.md)\n\n"
        "```\n"
        "an example block nobody closed\n\n"
        "**Depends on:** [`common/beta` · Beta One](../beta/phase1_beta.md)\n"
    )
    result = extract(_two_component_corpus(tmp_path, body))

    (finding,) = [
        f
        for f in codes(result, "UNPARSED_LINE")
        if "fence" in f.summary and "common/alpha" in f.summary
    ]
    assert finding.provenance.line > 0, "the opening fence must be located"
    assert "declaring nothing" in finding.detail
    # And the silent half is still silent — that is exactly why it needs saying.
    assert disposition_of(result, "development/common/alpha") == (
        dependencies.WORKLIST_UNDECLARED
    )


def test_a_closed_fence_reports_nothing_and_still_hides_its_contents(tmp_path: Path):
    """The negative half. A balanced fence is the normal case and must be quiet."""
    body = (
        "### Alpha One\n\n"
        "**Implementation:** [a](phase1_alpha.md)\n\n"
        "```\n"
        "**Depends on:** [`common/beta` · Beta One](../beta/phase1_beta.md)\n"
        "```\n"
    )
    result = extract(_two_component_corpus(tmp_path, body))
    assert [f for f in codes(result, "UNPARSED_LINE") if "fence" in f.summary] == []
    assert depends_edges(result) == [], "a fenced marker is prose ABOUT the convention"


def test_a_declaration_deviating_on_BOTH_axes_is_reported_on_both(tmp_path: Path):
    """`common/vm_orch:85` is live proof the two deviations co-occur.

    Reporting only the spelling tells its owner about half the rewrite they owe,
    and the half it omits is the one a reader of the ruled format would check
    for first.
    """
    body = (
        "### Alpha One\n\n"
        "**Implementation:** [a](phase1_alpha.md)\n\n"
        "Some prose leading in. **Dependencies:** "
        "[`common/beta` · Beta One](../beta/phase1_beta.md)\n"
    )
    result = extract(_two_component_corpus(tmp_path, body))
    (finding,) = codes(result, "DEPENDENCY_MARKER_NON_CONFORMING")
    assert "**Dependencies:**" in finding.detail
    assert "mid-paragraph" in finding.detail
    # Read, not dropped — the deviation is a finding, never a reason to stop.
    assert depends_edges(result), "the declaration must still yield its edge"


def test_the_cycle_detector_reports_at_least_one_cycle_in_any_tangle(tmp_path: Path):
    """The guarantee the docstring makes, and the blind spot it admits.

    Visiting each node once means the detector does not enumerate every simple
    cycle. What it DOES guarantee is the property the phase's requirement rests
    on — an empty cycle section always means acyclic — so this asserts the
    guarantee and pins the known gap, rather than asserting a completeness the
    algorithm has never delivered.

    The corpus is the complete graph over three phases: every pair is a 2-cycle
    and the triangle is a third. A complete enumeration would report five
    cycles.
    """
    body = "### {t} One\n\n**Implementation:** [x](phase1_{n}.md)\n\n**Depends on:** {deps}\n"
    names = ("alpha", "beta", "gamma")
    tree = {
        f"common/{n}": roadmap(
            n.title(),
            body.format(
                t=n.title(),
                n=n,
                deps=" · ".join(
                    f"[`common/{o}` · {o.title()} One](../{o}/phase1_{o}.md)"
                    for o in names
                    if o != n
                ),
            ),
        )
        for n in names
    }
    result = extract(
        build(tmp_path, tree, phases=tuple(f"common/{n}/phase1_{n}.md" for n in names))
    )

    found = codes(result, "DEPENDENCY_CYCLE")
    assert found, "a graph with cycles must report at least one — this is the guarantee"
    node_sets = [frozenset(f.detail.split("Cycle: ")[1].split(". Reported")[0].split(" → ")) for f in found]
    assert len(node_sets) == len(set(node_sets)), "each node set is reported once"
    # The admitted gap, pinned so a future reader does not mistake the count for
    # completeness: five simple cycles exist here and fewer are reported.
    assert len(found) < 5, (
        "the detector now enumerates more than it used to — if that is deliberate, "
        "the docstring's stated blind spots must be updated with it"
    )
    for finding in found:
        assert "→" in finding.detail and finding.provenance.line > 0


def test_the_stated_accounting_method_names_every_disposition_it_can_emit(tmp_path: Path):
    """`ACCOUNTING_METHOD` is rendered beside the table as the derivation a
    reader reproduces it from. It is prose restating a branch ladder, so it
    drifts the first time a branch moves and nothing fails.
    """
    for disposition in (
        dependencies.RESOLVES,
        *dependencies.EXCEPTIONS,
        *dependencies.WORKLISTS,
    ):
        # The method states the CLASS, not the label verbatim; the distinguishing
        # word of each is what must survive a rewording.
        keyword = disposition.split("—")[-1].strip().split()[0].upper()
        assert keyword in dependencies.ACCOUNTING_METHOD.upper(), (
            f"the rendered method does not mention `{disposition}`, so the page "
            "states a derivation the code does not perform"
        )


def test_an_acyclic_dependency_graph_reports_no_cycle(tmp_path: Path):
    """The negative half — the detector must not fire on a plain chain."""
    result = extract(_two_component_corpus(tmp_path, ALPHA_CONFORMING))
    assert codes(result, "DEPENDENCY_CYCLE") == []


# ---------------------------------------------------------------------------
# Attribution — the defect that produced a false cycle
# ---------------------------------------------------------------------------


def test_a_phase_link_in_a_criterion_bullet_does_not_attribute_the_section(tmp_path: Path):
    """The live-corpus regression, reduced to its shape.

    ``common/planning_ui``'s roadmap has a section with **no phase document of its
    own** that links another phase in a criterion bullet. Attributing on *the
    section's own phase link, when there is exactly one* made that section's
    declaration leave the phase it depends ON — a self-edge, reported as a real
    cycle in the plan. An operator would have been sent to re-sequence work that
    is correctly sequenced.
    """
    body = (
        "### Alpha One\n\n"
        "**Implementation:** [a](phase1_alpha.md)\n\n"
        "### A Later Idea\n\n"
        "**Depends on:** [`common/alpha` · Alpha One](phase1_alpha.md)\n\n"
        "- [ ] The budget from [Alpha One](phase1_alpha.md) is demonstrated to bite\n"
    )
    result = extract(_two_component_corpus(tmp_path, body))

    assert codes(result, "DEPENDENCY_CYCLE") == [], "a self-edge invented by attribution"
    assert depends_edges(result) == [
        (
            "component:development/common/alpha",
            "phase:development/common/alpha/phase1_alpha.md",
            11,
        )
    ]


def test_a_declaration_under_an_implementation_line_is_bound_to_that_phase(tmp_path: Path):
    """The negative half: attribution must not collapse to the component."""
    result = extract(_two_component_corpus(tmp_path, ALPHA_CONFORMING))
    (source, _target, _line) = depends_edges(result)[0]
    assert source == "phase:development/common/alpha/phase1_alpha.md"
    assert result.counts["declarations_attributed_to_a_phase"] == 1


# ---------------------------------------------------------------------------
# The artifact
# ---------------------------------------------------------------------------


def test_the_graph_carries_the_accounting_and_the_schema_version_moved(tmp_path: Path):
    """A consumer pinned to schema 1 is reading a graph with no dependency edges."""
    result = extract(_two_component_corpus(tmp_path, ALPHA_CONFORMING))
    assert result.graph["schema_version"] == "3"
    rows = result.graph["dependency_accounting"]
    assert {row["component"] for row in rows} == {
        "development/common/alpha",
        "development/common/beta",
    }
    assert all("disposition" in row and "reason" in row for row in rows)


# ---------------------------------------------------------------------------
# A declaration's links are not the declaring component's phases
# ---------------------------------------------------------------------------


def _declares_into_two_components(tmp_path: Path, alpha_body: str) -> Path:
    """``common/alpha`` owns no phase document; beta and gamma each own one."""
    return build(
        tmp_path,
        {
            "common/alpha": roadmap("Alpha", alpha_body),
            "common/beta": roadmap(
                "Beta", "### Beta One\n\n**Implementation:** [phase1_beta.md](phase1_beta.md)"
            ),
            "common/gamma": roadmap(
                "Gamma", "### Gamma One\n\n**Implementation:** [phase1_gamma.md](phase1_gamma.md)"
            ),
        },
        phases=("common/beta/phase1_beta.md", "common/gamma/phase1_gamma.md"),
    )


def test_declaring_two_dependencies_does_not_except_a_roadmap_off_the_worklist(
    tmp_path: Path,
):
    """The live shape, and the reason the guard exists.

    ``Component.owned`` answers *which phases does this component claim*, and
    ``Component.referenced`` *which other phase documents does it link*; a
    coordination document is derived from those two and ``on_disk``: nothing
    owned, no documents on disk, two or more OTHER components' phases referenced. A `**Depends on:**`
    line names other components' phases BY DEFINITION — so reading its links as
    phase references turns *"I depend on beta and gamma"* into *"I sequence beta
    and gamma"* and excepts the roadmap out of the report entirely.

    ``service/monitoring`` and ``common/resilience`` are each ONE resolvable
    link away from this on the live corpus, and the link the tool asks them for
    is the one that would delete them. **A wrong exception hides a gap
    permanently while a wrong worklist entry merely annoys an owner** — this is
    the hiding direction, reached by following the tool's own advice.
    """
    body = (
        "**Depends on:** [`common/beta` · Beta One](../beta/phase1_beta.md) · "
        "[`common/gamma` · Gamma One](../gamma/phase1_gamma.md)\n\n"
        "### Alpha Two\n\n"
        "**Depends on:** Sprint 7 landing first.\n"
    )
    result = extract(_declares_into_two_components(tmp_path, body))

    assert disposition_of(result, "development/common/alpha") == dependencies.WORKLIST_PROSE_ONLY
    assert len(depends_edges(result)) == 2, "both declared dependencies are still real edges"
    assert [
        e for e in result.graph["edges"] if e["kind"] == "plans" and "alpha" in e["source"]
    ] == [], "a dependency is not a phase alpha plans"


def test_a_block_form_declaration_s_list_is_not_read_as_phase_entries_either(
    tmp_path: Path,
):
    """The same guard over the OTHER half of a declaration's extent.

    The dependency walker reads the list beneath an EMPTY marker line as part of
    the declaration. Skipping only the marker line here would leave the identical
    hole open for every roadmap that writes the block form — eight do on the live
    corpus — and the fix would read as complete while covering one shape of two.
    """
    body = (
        "**Depends on:**\n"
        "- [`common/beta` · Beta One](../beta/phase1_beta.md)\n"
        "- [`common/gamma` · Gamma One](../gamma/phase1_gamma.md)\n\n"
        "### Alpha Two\n\n"
        "**Depends on:** Sprint 7 landing first.\n"
    )
    result = extract(_declares_into_two_components(tmp_path, body))

    assert disposition_of(result, "development/common/alpha") == dependencies.WORKLIST_PROSE_ONLY
    assert len(depends_edges(result)) == 2


def test_a_phase_link_inside_a_fence_is_not_a_phase_entry(tmp_path: Path):
    """The fence guard at the SAME scope in both walkers.

    ``MDC-Master-Planning#229`` records differing guard scope between these two
    walkers as a repeat defect. The dependency walker already ignored a fenced
    marker; the phase walker read fenced links as real phase entries, so a
    roadmap SHOWING the convention acquired the phases it was illustrating.
    """
    body = (
        "```markdown\n"
        "**Depends on:** [`common/beta` · Beta One](../beta/phase1_beta.md)\n"
        "[`common/gamma` · Gamma One](../gamma/phase1_gamma.md)\n"
        "```\n\n"
        "**Depends on:** Sprint 7 landing first.\n"
    )
    result = extract(_declares_into_two_components(tmp_path, body))

    assert disposition_of(result, "development/common/alpha") == dependencies.WORKLIST_PROSE_ONLY
    assert depends_edges(result) == []
    assert [
        e for e in result.graph["edges"] if e["kind"] == "plans" and "alpha" in e["source"]
    ] == [], "a fenced example is not a phase entry"


def test_a_fence_ends_a_block_form_declaration_in_both_walkers(tmp_path: Path):
    """The two walkers must agree about where a declaration ENDS, not just where
    it starts.

    The dependency walker's continuation lookahead stops at the first line that
    is not a list item, and a fence delimiter is not a list item — so a bullet
    written after a fence that opened under a bare marker is part of NO
    declaration there. The phase walker's ``in_declaration_list`` flag used to
    survive the whole fenced block, so it masked that same bullet out of the
    component's phase sets: a link read by NEITHER walker, dropped with no report.

    That is the same defect this partition was written to close, relocated one
    line-shape over — which is precisely the recurrence ``MDC-Master-Planning#229``
    records. A plain bullet is a REFERENCE rather than an entry since the
    owned/referenced split, so the link lands as a `references` edge — and the
    check is that it lands at all.
    """
    body = (
        "**Depends on:**\n"
        "```\n"
        "an illustrative block, not a continuation\n"
        "```\n"
        "- [`common/alpha` · Alpha One](phase1_alpha.md)\n"
    )
    root = build(
        tmp_path,
        {
            "common/alpha": roadmap("Alpha", body),
            "common/beta": roadmap(
                "Beta", "### Beta One\n\n**Implementation:** [phase1_beta.md](phase1_beta.md)"
            ),
        },
        phases=("common/alpha/phase1_alpha.md", "common/beta/phase1_beta.md"),
    )
    result = extract(root)

    read = [
        e["target"]
        for e in result.graph["edges"]
        if e["kind"] in ("plans", "references")
        and e["source"] == "component:development/common/alpha"
    ]
    assert any("phase1_alpha" in t for t in read), (
        "the bullet sits after the fence closed, so neither walker's declaration "
        "extent reaches it and the phase walker must read it"
    )


def test_an_hours_figure_beside_a_declaration_still_attributes_to_the_section(
    tmp_path: Path,
):
    """The deliberate asymmetry, pinned so a later pass cannot 'tidy' it silently.

    Links read only the text in front of a marker; hours read the WHOLE line. An
    ``~Nh`` figure attaches to the heading SECTION, not to a link, and a figure
    written beside a declaration is this section's own estimate — there is no
    dependency-owned phase for it to attach to instead. Restricting the hours
    scan symmetrically would drop the figure from attribution entirely, and
    nothing asserted that until now.
    """
    body = (
        "### Alpha One\n\n"
        "**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "**Depends on:** [`common/beta` · Beta One](../beta/phase1_beta.md) — ~12h once unblocked\n"
    )
    root = build(
        tmp_path,
        {
            "common/alpha": roadmap("Alpha", body),
            "common/beta": roadmap(
                "Beta", "### Beta One\n\n**Implementation:** [phase1_beta.md](phase1_beta.md)"
            ),
        },
        phases=("common/alpha/phase1_alpha.md", "common/beta/phase1_beta.md"),
    )
    result = extract(root)

    alpha = next(c for c in result.components if c.path == "development/common/alpha")
    hours = {p.path: p.hours_low for p in alpha.owned}
    assert hours == {"development/common/alpha/phase1_alpha.md": 12}, (
        "the section has exactly one owned phase entry — alpha's own — so the figure "
        "beside the declaration binds to it rather than being lost"
    )


def test_a_roadmap_declaration_citing_a_phase_by_number_is_one_row_per_line(tmp_path: Path):
    """Rule 4's by-number guard ran only on phase documents — the surface rule 9
    exempts — and never on the roadmap, the one carrier it binds. Live:
    `service/home-auto` cites `[Django Phase 7](…)` and `common/backend`
    cites two, with no row for either."""
    body = (
        "### Alpha One 🟠 PLANNED\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "**Depends on:** [Phase 3](../beta/phase3_beta.md) · [beta phase1](../beta/phase1_beta.md)\n\n"
        "### Alpha Two 🟠 PLANNED\n\n**Implementation:** [phase2_alpha.md](phase2_alpha.md)\n\n"
        "**Depends on:** [Phase 3](../beta/phase3_beta.md)\n"
    )
    root = build(
        tmp_path,
        {"common/alpha": roadmap("Alpha", body), "common/beta": roadmap("Beta", "prose")},
        phases=(
            "common/alpha/phase1_alpha.md",
            "common/alpha/phase2_alpha.md",
            "common/beta/phase1_beta.md",
            "common/beta/phase3_beta.md",
        ),
    )
    result = extract(root)

    rows = codes(result, "DEPENDENCY_CITES_BY_NUMBER")
    assert [(r.provenance.file, r.provenance.line) for r in rows] == [
        ("development/common/alpha/roadmap.md", 9),
        ("development/common/alpha/roadmap.md", 15),
    ], "one row per declaration LINE, not per link"
    assert "2 link(s) cite a phase by NUMBER — `Phase 3`, `beta phase1`" in rows[0].summary
    assert "1 link(s) cite a phase by NUMBER — `Phase 3`" in rows[1].summary
    assert rows[0].expected == "the phase cited by NAME (Documentation Standard rule 4)"
    # The edges still derive — the row is about the citation's text.
    assert len([e for e in result.graph["edges"] if e["kind"] == "depends_on"]) == 3


def test_a_roadmap_declaration_citing_a_multi_word_component_by_number_is_a_row(tmp_path: Path):
    """The predicate allowed ONE word before `Phase N`, so `[Home Assistant
    Phase 1]` — live at `common/backend:297` — passed a guard blind by
    construction to every two-word component name. A `§N.N` section suffix
    was rejected by the same `$` (live: `imager:301` cites
    `phase10 §10.3`). Both are numbers standing where rule 4 wants a name."""
    body = (
        "### Alpha One 🟠 PLANNED\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "**Depends on:** [Home Assistant Phase 1](../beta/phase1_beta.md)"
        " · [phase3 §3.2](../beta/phase3_beta.md#h)"
        " · [Home Assistant Local HAOS](../beta/phase1_beta.md)\n"
    )
    root = build(
        tmp_path,
        {"common/alpha": roadmap("Alpha", body), "common/beta": roadmap("Beta", "prose")},
        phases=(
            "common/alpha/phase1_alpha.md",
            "common/beta/phase1_beta.md",
            "common/beta/phase3_beta.md",
        ),
    )
    result = extract(root)

    (row,) = codes(result, "DEPENDENCY_CITES_BY_NUMBER")
    assert (row.provenance.file, row.provenance.line) == ("development/common/alpha/roadmap.md", 9)
    assert "2 link(s) cite a phase by NUMBER — `Home Assistant Phase 1`, `phase3 §3.2`" in row.summary
    assert "Home Assistant Local HAOS" not in row.summary, "a NAME after the component is not a number"


@pytest.mark.parametrize(
    "text",
    [
        "Phase 0",
        "phase1",
        "ansible Phase 4",
        "Home Assistant Phase 1",
        "Control Plane Migration Phase 2b",
        "Django Backend Roadmap Phase 4",
        "Resilience Phase 1 + Phase 6",
        "phase10 §10.3",
        "1Password Phase 1 §6.5",
        "VM reconciler — Phase 7",
        "roadmap.md §Phase 3",
        "`install_nvidia_container_toolkit` role from DAS Phase 12",
        " Phase 7 ",
    ],
)
def test_by_number_predicate_matches_every_shape_a_number_stands_in_for_a_name(text: str):
    """One definition, both walkers. Each row is a shape measured live in the
    corpus; a member missing here is a by-number citation with no finding."""
    assert dependencies.BY_NUMBER_RE.match(text), text


@pytest.mark.parametrize(
    "text",
    [
        "Beta Three",
        "Home Assistant Local HAOS",
        "ESO Deployment",
        "Monitoring Roadmap Phase 2 — Configuration as Code",
        "phase5_platform_substrate_server_template.md",
        "Phase",
        "phased rollout",
        "subphase 2",
        "Phase 2 (planned)",
    ],
)
def test_by_number_predicate_leaves_a_name_alone(text: str):
    """Negative control: a name, a name after a number, a filename, the word
    `phase` without a number, `phase` inside a longer word, and a trailing
    annotation (not live; the predicate's comment says where to widen) are not
    by-number citations."""
    assert not dependencies.BY_NUMBER_RE.match(text), text


def test_a_roadmap_declaration_citing_a_phase_by_name_is_not_a_by_number_row(tmp_path: Path):
    """Negative control for the guard above."""
    body = (
        "### Alpha One 🟠 PLANNED\n\n**Implementation:** [phase1_alpha.md](phase1_alpha.md)\n\n"
        "**Depends on:** [`common/beta` · Beta Three](../beta/phase3_beta.md)\n"
    )
    root = build(
        tmp_path,
        {"common/alpha": roadmap("Alpha", body), "common/beta": roadmap("Beta", "prose")},
        phases=("common/alpha/phase1_alpha.md", "common/beta/phase3_beta.md"),
    )
    result = extract(root)
    assert codes(result, "DEPENDENCY_CITES_BY_NUMBER") == []

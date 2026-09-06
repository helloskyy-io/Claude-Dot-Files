"""Rule 9's four derived facts, driven on fixtures that discriminate.

`documentation_standard.md` § Development Planning Files rule 9 says a phase entry
declares ONE thing — a forward `**Depends on:**` line — and that the reverse edge, the
component rollup, the satisfaction state and the graph are all DERIVED. This holds the
derivation, because a rule asserting "derived" with nothing deriving is a promise.

TWO BUGS THIS MODULE EXISTS BECAUSE OF, both found by running the deriver against
`workflow-decomposition`'s real four-row table before any corpus was converted:

  * `_phase_marker_for` first matched *"the phase doc's name appears anywhere in this
    entry's span"* — the loose predicate this repo had ALREADY measured and rejected in
    `phase_sizing` (*"a section that CITES a phase doc is not a phase section"*, 5 -> 7
    here and 5 -> 12 in MDC). It read PMP's opening paragraph, which mentions
    `phase1_the_run_bag.md` in prose, as that phase's owning entry and returned the wrong
    marker. Now keyed on rule 8's `**Implementation:**` anchor.
  * `gated_on` returned a component's own phase-to-phase edges as INBOUND, so every
    component appeared gated on itself.

Both were silent: each produced a plausible graph. That is why the fixtures below assert
the discriminating case rather than the happy one.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules"))
from assistant.plan import plan_activities as pa  # noqa: E402


def _component(root: Path, name: str, roadmap: str, docs: tuple[str, ...] = ()) -> Path:
    d = root / "development" / "edge" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "roadmap.md").write_text(roadmap, encoding="utf-8")
    for doc in docs:
        (d / doc).write_text("# " + doc, encoding="utf-8")
    return d


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    """Two components and a standard: one satisfied edge, one not, one cross-component."""
    (tmp_path / "standards" / "documentation").mkdir(parents=True)
    (tmp_path / "standards" / "documentation" / "s.md").write_text("# S", encoding="utf-8")

    _component(tmp_path, "upstream",
        "# Upstream\n\n"
        "### Done thing ✅ COMPLETE\n\n"
        "**Implementation:** [`phase1_done.md`](phase1_done.md)\n\n"
        "### Unfinished thing 🟠 PLANNED\n\n"
        "**Implementation:** [`phase2_open.md`](phase2_open.md)\n",
        ("phase1_done.md", "phase2_open.md"))

    _component(tmp_path, "downstream",
        "# Downstream\n\n"
        "### Needs the done one 🟠 PLANNED\n\n"
        "**Implementation:** [`phase1_a.md`](phase1_a.md)\n"
        "**Depends on:** [upstream · Done thing](../upstream/phase1_done.md) — prose survives\n\n"
        "### Needs the open one 🟠 PLANNED\n\n"
        "**Implementation:** [`phase2_b.md`](phase2_b.md)\n"
        "**Depends on:** [upstream · Unfinished](../upstream/phase2_open.md) · "
        "[The Standard](../../../standards/documentation/s.md)\n\n"
        "### Internal only 🔵 NOT SCHEDULED\n\n"
        "**Depends on:** [Needs the done one](phase1_a.md)\n",
        ("phase1_a.md", "phase2_b.md"))
    return tmp_path


def test_a_forward_edge_is_READ_and_its_prose_IGNORED(corpus: Path) -> None:
    edges = pa.dependency_edges(corpus / "development/edge/downstream/roadmap.md")
    assert len(edges) == 4, [e.text for e in edges]
    first = edges[0]
    assert first.phase == "Needs the done one"
    assert first.target.name == "phase1_done.md"
    assert "prose survives" in first.note


def test_SATISFACTION_derives_from_WHAT_THE_TARGET_IS(corpus: Path) -> None:
    """A phase reads its rule-8 marker; a standard is satisfied by resolving."""
    by = {(e.phase, e.target.name): pa.edge_state(e, corpus)
          for e in pa.dependency_edges(corpus / "development/edge/downstream/roadmap.md")}
    assert by[("Needs the done one", "phase1_done.md")] == "satisfied"
    assert by[("Needs the open one", "phase2_open.md")] == "unsatisfied"
    assert by[("Needs the open one", "s.md")] == "satisfied"


def test_A_BROKEN_TARGET_IS_NOT_AN_UNSATISFIED_ONE(corpus: Path) -> None:
    """Rule 9 separates them and says a renderer must not show them alike."""
    rm = corpus / "development/edge/downstream/roadmap.md"
    rm.write_text(rm.read_text(encoding="utf-8") +
                  "\n### Typo 🟠 PLANNED\n\n**Depends on:** [gone](../upstream/phase9_nope.md)\n",
                  encoding="utf-8")
    state = {e.phase: pa.edge_state(e, corpus) for e in pa.dependency_edges(rm)}
    assert state["Typo"] == "broken"
    assert "broken" != "unsatisfied"


def test_THE_OWNING_ENTRY_IS_FOUND_BY_ITS_IMPLEMENTATION_LINE_NOT_A_MENTION(corpus: Path) -> None:
    """The regression that made a complete phase read as unfinished.

    A roadmap's OPENING PROSE citing a phase doc must not be taken for that phase's
    entry — the exact miscount `phase_sizing` records as measured and rejected.
    """
    # THE REAL SHAPE, taken from `persistent-memory-protocol`: a NON-PHASE `###`
    # section, carrying no status marker, that cites a phase doc in prose and sits
    # ABOVE that phase's own entry. The loose predicate matches this window first,
    # finds no marker in its heading, and reports a COMPLETE phase as unfinished.
    # Prose above the first heading does not reproduce it — no window contains it.
    up = corpus / "development/edge/upstream/roadmap.md"
    body = up.read_text(encoding="utf-8")
    up.write_text(body.replace(
        "### Done thing ✅ COMPLETE",
        "### The four kinds of record\n\n"
        "Discussed here rather than owned: [Done thing](phase1_done.md) is where the\n"
        "run bag lands. This section CITES a phase doc and is not a phase entry.\n\n"
        "### Done thing ✅ COMPLETE", 1), encoding="utf-8")
    edge = pa.dependency_edges(corpus / "development/edge/downstream/roadmap.md")[0]
    assert pa.edge_state(edge, corpus) == "satisfied", (
        "the opening paragraph was read as the owning entry — the loose predicate is back"
    )


def test_THE_REVERSE_EDGE_IS_DERIVED_AND_EXCLUDES_A_COMPONENTS_OWN(corpus: Path) -> None:
    graph = pa.dependency_graph(corpus)
    inbound = pa.gated_on(corpus / "development/edge/upstream", graph)
    assert {e.roadmap.parent.name for e in inbound} == {"downstream"}

    # `downstream` declares an INTERNAL edge (phase3 -> its own phase1). That is
    # sequencing inside one plan, and reporting it as inbound shows a component
    # gated on itself — which the first version of `gated_on` did.
    assert pa.gated_on(corpus / "development/edge/downstream", graph) == []


def test_THE_COMPONENT_ROLLUP_IS_DERIVED_FROM_THE_PHASE_EDGES(corpus: Path) -> None:
    rollup = pa.component_dependencies(pa.dependency_graph(corpus))
    downstream = corpus / "development/edge/downstream"
    assert {p.name for p in rollup[downstream]} == {"upstream", "documentation"}, (
        "a component depends on X if ANY of its phases does, and its own directory "
        "is never a member of its own dependency set"
    )


def test_A_ROADMAP_WITH_NO_DEPENDS_ON_LINE_YIELDS_NO_EDGES(corpus: Path) -> None:
    """Absence is the declaration. An unconverted roadmap is silent, not malformed."""
    assert pa.dependency_edges(corpus / "development/edge/upstream/roadmap.md") == []
    assert pa.dependency_edges(corpus / "development/edge/upstream/nope.md") == []


# --- rule 9's THIRD state: a blank is a finding, not a declaration -----------------
#
# Amended 2026-09-06 after MDC-PM1 showed that absence cannot distinguish a
# declaration from DAMAGE. Four failure modes produce an identical blank — a sweep
# that skips a roadmap, an emitter that throws, a hand-authored roadmap, and a bad
# merge that deletes the line — and the last silently converts a real dependency into
# a conformant "depends on nothing". A mechanical rename pass had already mangled a
# `Depends on:` line in the MDC corpus when this was raised.


def _entry(name: str, marker: str, line: str | None) -> str:
    body = f"### {name} {marker}\n\n**Implementation:** [`p.md`](p.md)\n"
    return body + (f"{line}\n\n" if line else "\n")


@pytest.fixture
def states(tmp_path: Path) -> Path:
    rm = tmp_path / "development" / "edge" / "c" / "roadmap.md"
    rm.parent.mkdir(parents=True)
    (rm.parent / "t.md").write_text("# t", encoding="utf-8")
    rm.write_text(
        "# C\n\n"
        + _entry("Has deps", "🟠 PLANNED", "**Depends on:** [t](t.md) — with prose")
        + _entry("Standalone", "🟠 PLANNED", "**Depends on:** NONE")
        + _entry("Standalone dotted", "🟠 PLANNED", "**Depends on:** NONE.")
        + _entry("Scoped internal", "🟠 PLANNED", "**Depends on:** NONE internal.")
        + _entry("Scoped inside", "🟠 PLANNED",
                 "**Depends on:** NONE inside this component. **Blocked** by two operator calls.")
        + _entry("Truncated", "🟠 PLANNED", "**Depends on:**")
        + _entry("Silent", "🟠 PLANNED", None),
        encoding="utf-8")
    return rm


@pytest.mark.parametrize("phase,expected", [
    ("Has deps", "declared"),
    ("Standalone", "standalone"),
    ("Standalone dotted", "standalone"),
    # THE TRAP: a qualified token means "and something outside", so calling it
    # standalone silently deletes a real dependency. Both shapes are live in MDC.
    ("Scoped internal", "qualified"),
    ("Scoped inside", "qualified"),
    # A bare marker is a truncation — exactly as lossy as absence, same as the rule says.
    ("Truncated", "qualified"),
    ("Silent", "missing"),
])
def test_the_DECLARATION_STATE_discriminates(states: Path, phase: str, expected: str) -> None:
    assert pa.declaration_state(states, phase) == expected


def test_a_QUALIFIED_token_is_never_read_as_standalone(states: Path) -> None:
    """Stated separately because folding it into `standalone` is the silent deletion."""
    assert pa.declaration_state(states, "Scoped internal") != "standalone"
    assert pa.declaration_state(states, "Scoped inside") != "standalone"


def test_THE_WORKLIST_IS_WHAT_THE_CORPUS_DOES_NOT_KNOW_ABOUT_ITSELF(states: Path) -> None:
    found = {(ph, st) for _, ph, st in pa.unassessed_phases(states.parents[3])}
    assert found == {
        ("Scoped internal", "qualified"),
        ("Scoped inside", "qualified"),
        ("Truncated", "qualified"),
        ("Silent", "missing"),
    }, "a declared or standalone entry must not appear on the worklist"


def test_A_NON_PHASE_HEADING_IS_NOT_A_FINDING(tmp_path: Path) -> None:
    """A prose section claims nothing, so its silence is not a missing declaration.

    Without this the worklist reports every discussion heading in every roadmap and
    becomes unreadable — the same over-reporting `phase_sizing` measured when it tried
    a looser phase predicate.
    """
    rm = tmp_path / "development" / "edge" / "c" / "roadmap.md"
    rm.parent.mkdir(parents=True)
    rm.write_text("# C\n\n### In plain words\n\nProse, no marker.\n\n"
                  + _entry("Real", "🟠 PLANNED", "**Depends on:** NONE"), encoding="utf-8")
    assert pa.unassessed_phases(tmp_path) == []

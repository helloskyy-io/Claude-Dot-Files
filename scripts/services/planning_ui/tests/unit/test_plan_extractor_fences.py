"""The fence guard, asserted as a CLASS rather than as the walkers that failed it.

A fenced code block is an ILLUSTRATION of a planning document, not one. Every
walker in this package that reads a markdown line's SHAPE — a heading, a status,
a ``**Depends on:**`` marker, an ``**Implementation:**`` link, a checkbox, an
amendment heading — must therefore agree that a line inside a fence is not
content.

**They did not, and enumerating the ones that did not is what kept failing.**
The guard reached ``_collect_phases`` in one pass; a review then found
``parse_roadmap`` and ``dependencies._attribute_sources``; a sweep for the class
found three more, in modules nobody had opened. So the headline test here does
not name a walker at all: it asserts that swapping the BODY of every fenced
block in a corpus for inert text leaves the derived artifact byte-identical.
A seventh walker added tomorrow fails it without anyone remembering to add a
case, which is the only shape of check that converges.

The per-walker tests below stay because the class check tells you *something*
leaks and they tell you *which*, and a failure you cannot localise costs a pass.
"""

from __future__ import annotations

import ast
import json
import tempfile
from pathlib import Path

from planning_ui.plan_extractor import (
    amendments,
    dependencies,
    derivations,
    discovery,
    extract,
    measurements,
    roadmaps,
    sprints,
)
from planning_ui.plan_extractor.model import Collector, UNPARSED_LINE
from planning_ui.plan_extractor.fences import advance_fence, fenced_mask
from planning_ui.plan_extractor.roadmaps import parse_roadmap

#: A fence delimiter, built rather than written, so the class check below does
#: not report this file's own fixtures as offenders. It reads every string
#: constant in the package and this module is not exempt from its own rule.
#: Calls whose string argument is a TEST against a line, not prose about one.
TESTING_CALLS = frozenset(
    {"startswith", "endswith", "match", "search", "fullmatch", "compile", "split"}
)

BACKTICK_RUN = "`" * 3
TILDE_RUN = "~" * 3

FENCED_PHASE_HEADING = (
    "# Notes\n\nExample:\n\n"
    + BACKTICK_RUN
    + "markdown\n## Requirements for completion\n"
    + BACKTICK_RUN
    + "\n"
)
REAL_PHASE_HEADING = "# Notes\n\n## Requirements for completion\n\n- do the thing\n"

#: The live shape from ``clusters/phase3_kubevip_ha.md``, reduced: a
#: four-backtick block quoting proposed standard text, wrapping a three-backtick
#: example whose first line is a shell comment ``HEADING_RE`` matches.
NESTED_FENCE_DOC = (
    "# Notes\n\n## Standards-amendment candidates\n\n"
    + BACKTICK_RUN
    + "`markdown\n### Proposed 12.4\n\n"
    + BACKTICK_RUN
    + "bash\n# a shell comment that HEADING_RE matches\nkubectl get nodes\n"
    + BACKTICK_RUN
    + "\n"
    + BACKTICK_RUN
    + "`\n\n"
    "- Whether it should bind for all clusters - awaiting human review\n"
    "- Whether kube-vip is the binding implementation - awaiting human review\n"
)

SPRINTS = """# Implementation Plan

## Sprint: Everything
🟡 IN PROGRESS

- [x] **common/alpha · One** · L1 · ([roadmap](./common/alpha/roadmap.md)) — done · **~2h**

## Sprint: Unplaced
"""

#: Every lexical shape this package reads, in one block. Written once so a
#: reader can see what the fence is being asked to hide.
SHAPES = (
    # FIRST, and the ordering is load-bearing: `sprints._parse_exclusions`
    # BREAKS at the first `## ` line it meets, so an exclusion subsection sited
    # after one is unreachable even with the guard removed — the check would
    # pass on a broken guard, which is how this fixture failed its own mutation
    # twice before this line was written.
    "### Components deliberately NOT listed\n"
    "- `development/common/beta/`\n"
    "# Fake Label\n"
    "**Status:** ⚫ RETIRED\n"
    "## Requirements for completion\n"
    "## Standards implications (surfaced for ratification)\n"
    "# install the thing\n"
    "**Implementation:** [ghost](phase9_ghost.md)\n"
    "**Depends on:** [`common/beta` · Beta One](../beta/phase1_beta.md)\n"
    "## Ratification Queue\n"
)

#: NOT in :data:`SHAPES`, and the omission is a ruling rather than an oversight.
#: ``SprintsDocument.total_checkbox_lines`` is documented as *"every checkbox
#: line seen, INCLUDING fenced-template and Unplaced lines"* — a deliberately
#: raw denominator, stated as one of three. A fenced checkbox is therefore
#: SUPPOSED to move it, so putting one in the class check would make the check
#: forbid a method the tool publishes. It is pinned by its own test below
#: instead, so that a change to it is visible rather than silent.
FENCED_CHECKBOX = "- [ ] **common/gamma · Ghost** · L1 · ([roadmap](./x.md)) — **~9h**"

#: The same number of lines, carrying nothing. The two corpora differ ONLY in
#: what sits between the fence delimiters, so every line number is preserved and
#: the artifacts are directly comparable.
INERT = "\n".join(["nothing to see here"] * len(SHAPES.splitlines())) + "\n"


#: A tracked-store item whose anchor names a heading that exists only in a fence.
#: `derivations.anchor_resolves_in` is reachable ONLY through a `tracked/` store,
#: so without this the class check never calls it.
TRACKED_ITEM = """---
id: S-fencechk
title: an anchor pointed at a fenced heading
status: open
count: 1
filed: 2026-09-06
filed_by: test
target: `standards/quoted.md`
anchor: `#ratification-queue`
ratification:
---

A candidate whose anchor must not resolve against a fenced illustration.
"""


def _corpus(tmp_path: Path, name: str, fence_body: str) -> Path:
    """A miniature corpus whose every readable document carries one fenced block.

    **The fenced block is sited on every surface a guard protects**, not merely
    on the ones the walkers that failed happened to read. The first version of
    this fixture had no § Sprint: Unplaced section and no ``tracked/`` store, so
    reverting either the sprints or the derivations guard left this test GREEN —
    a class check whose fixture cannot reach two of the six class members is a
    per-walker check wearing a class check's docstring.
    """
    root = tmp_path / name
    development = root / "development"
    development.mkdir(parents=True)
    (development / "sprints.md").write_text(
        SPRINTS + f"\n```markdown\n{fence_body}```\n", encoding="utf-8"
    )
    tracked = root / "tracked" / "standards"
    tracked.mkdir(parents=True)
    (tracked / "S-fencechk.md").write_text(TRACKED_ITEM, encoding="utf-8")
    standards = root / "standards"
    standards.mkdir(parents=True)
    (standards / "quoted.md").write_text(
        f"# Quoted\n\n```markdown\n{fence_body}```\n", encoding="utf-8"
    )
    for slug, title in (("common/alpha", "Alpha"), ("common/beta", "Beta")):
        directory = development / slug
        directory.mkdir(parents=True, exist_ok=True)
        # The fenced block sits INSIDE the phase section, after the real
        # `**Implementation:**` line and before the section ends. That placement
        # is load-bearing: a fence in a preamble can only leak shapes that are
        # section-independent, so a walker that reads a fenced heading or a
        # fenced `**Implementation:**` link would go unnoticed. Sited here, both
        # collide with the section they would corrupt.
        (directory / "roadmap.md").write_text(
            f"# {title}\n\n"
            # A SECOND fenced block, in the preamble. `parse_roadmap` keeps the
            # FIRST status line it sees, so a fence sited only after the real
            # one cannot demonstrate the guard — the ordering rule would hide
            # the leak. Both placements are needed and neither is redundant.
            f"```markdown\n{fence_body}```\n\n"
            f"**Status:** 🟡 IN PROGRESS\n\n"
            f"### {title} One\n\n"
            f"**Implementation:** [x](phase1_{title.lower()}.md)\n\n"
            f"```markdown\n{fence_body}```\n\n"
            f"**Depends on:** [`common/beta` · Beta One](../beta/phase1_beta.md)\n",
            encoding="utf-8",
        )
        (directory / f"phase1_{title.lower()}.md").write_text(
            "# A phase\n\n"
            f"```markdown\n{fence_body}```\n\n"
            "## Requirements for completion\n\n- [ ] a thing\n",
            encoding="utf-8",
        )
    return root


def test_fenced_content_contributes_nothing_to_the_derived_artifact(tmp_path: Path):
    """THE CLASS CHECK. Not one walker — every walker, by the property.

    Two corpora identical except for what sits inside their fences: one carrying
    every lexical shape the package reads, one carrying inert prose of the same
    line count. If any walker reads through a fence, the shape leaks into the
    graph and the two artifacts differ.

    A failure here does NOT name the walker. That is the point — it fires for a
    walker that did not exist when this was written, which is the only way this
    class stops being rediscovered one pass at a time.

    **What it covers, established by mutation rather than by claim.** Reverting
    any one of the five shape guards this package applies —
    ``parse_roadmap``, ``_attribute_sources`` (both of its reads),
    ``anchor_resolves_in`` and ``_parse_exclusions`` — turns this test red. Two
    things do NOT turn it red and are covered by their own tests instead:
    ``amendments._classify_section``'s body mask (a COUNT inside a surface, not
    a shape that leaks into the graph) and the unterminated-fence report.

    Getting there took three fixture corrections, each of which is a comment
    above the thing it fixed, because each time the fixture passed against a
    guard that had been removed. A class check that cannot reach a class member
    is a per-walker check wearing a class check's docstring.
    """
    live = extract(_corpus(tmp_path, "live", SHAPES)).graph
    inert = extract(_corpus(tmp_path, "inert", INERT)).graph

    # `provenance.input_digest` is a hash of the input BYTES, which differ by
    # construction — the two corpora are the same documents with different
    # fence bodies. Comparing it would assert the corpora are identical, which
    # is the opposite of the experiment.
    live.pop("provenance")
    inert.pop("provenance")

    assert json.dumps(live, sort_keys=True) == json.dumps(inert, sort_keys=True)


def test_a_fenced_checkbox_moves_the_raw_denominator_and_not_the_work_item_count(tmp_path: Path):
    """The one shape a fence is NOT supposed to hide, pinned so it stays deliberate.

    ``total_checkbox_lines`` is published as the widest of three denominators
    and says in its own comment that it counts fenced-template lines. The narrow
    ``work_items`` count must not move, because that one IS the stated shape.

    Written as a test rather than left out of the class check silently: the next
    reader meeting a fenced checkbox in the denominator should find the ruling,
    not re-derive it.
    """
    from planning_ui.plan_extractor import sprints as sprints_module

    root = _corpus(tmp_path, "raw", SHAPES)
    path = root / "development" / "sprints.md"
    plain = sprints_module.parse_sprints(root, Collector())
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "```markdown\n", f"```markdown\n{FENCED_CHECKBOX}\n", 1
        ),
        encoding="utf-8",
    )
    fenced = sprints_module.parse_sprints(root, Collector())

    assert fenced.total_checkbox_lines == plain.total_checkbox_lines + 1
    assert fenced.work_items == plain.work_items


def test_fenced_mask_covers_the_delimiter_itself(tmp_path: Path):
    """The delimiter line is masked, not merely the interior.

    ```` ```markdown ```` is heading-shaped to nothing, but ``~~~`` is not, and a
    walker handed a mask that exposes its delimiters reads the fence's own line.
    Asserted because every caller now trusts one mask instead of its own loop.
    """
    assert fenced_mask(["a", "```py", "b", "```", "c"]) == [False, True, True, True, False]
    assert fenced_mask(["```", "unterminated"]) == [True, True]


# ---------------------------------------------------------------------------
# Per-walker localisation — which reader leaked
# ---------------------------------------------------------------------------


def test_a_fenced_status_line_does_not_retire_a_component(tmp_path: Path):
    """``roadmaps.parse_roadmap``'s status/label walk.

    A retired component is suppressed from the report ENTIRELY, so a roadmap
    that illustrates the retired marker in a fence would delete itself from the
    worklist by documenting the convention — the hiding direction, reached by
    writing documentation.
    """
    root = tmp_path / "corpus"
    (root / "development" / "common" / "alpha").mkdir(parents=True)
    (root / "development" / "sprints.md").write_text(SPRINTS, encoding="utf-8")
    rel = "development/common/alpha/roadmap.md"
    (root / rel).write_text(
        "# Alpha\n\n"
        "How a retired component is marked:\n\n"
        "```markdown\n**Status:** ⚫ RETIRED\n```\n\n"
        "**Status:** 🟡 IN PROGRESS\n",
        encoding="utf-8",
    )

    component = parse_roadmap(root, rel, Collector())

    assert component is not None
    assert component.retired is False
    assert component.status_text == "🟡 IN PROGRESS"


def test_a_fenced_shell_comment_does_not_strip_a_declaration_of_its_phase(tmp_path: Path):
    """``dependencies._attribute_sources``, with the fence-free control beside it.

    ``HEADING_RE`` matches ``# install the thing`` — an ordinary shell comment.
    A fenced bash example between an ``**Implementation:**`` line and a
    declaration used to advance the section counter that ``_collect_phases``
    does not advance, and the declaration fell from its phase to its component.

    The control is what distinguishes the fix from a coincidence: without it,
    a test asserting ``"phase"`` passes on a parser that never attributed
    anything to a phase at all.
    """
    def build(with_fence: bool) -> Path:
        root = tmp_path / ("fenced" if with_fence else "control")
        development = root / "development"
        development.mkdir(parents=True)
        (development / "sprints.md").write_text(SPRINTS, encoding="utf-8")
        fence = "```bash\n# install the thing\n```\n\n" if with_fence else ""
        (development / "common" / "alpha").mkdir(parents=True)
        (development / "common" / "alpha" / "roadmap.md").write_text(
            "# Alpha\n\n**Status:** 🟡 IN PROGRESS\n\n"
            "### Alpha One\n\n"
            "**Implementation:** [a](phase1_alpha.md)\n\n"
            f"{fence}"
            "**Depends on:** [`common/beta` · Beta One](../beta/phase1_beta.md)\n",
            encoding="utf-8",
        )
        (development / "common" / "alpha" / "phase1_alpha.md").write_text("# A\n", encoding="utf-8")
        (development / "common" / "beta").mkdir(parents=True)
        (development / "common" / "beta" / "roadmap.md").write_text(
            "# Beta\n\n**Status:** 🟡 IN PROGRESS\n", encoding="utf-8"
        )
        (development / "common" / "beta" / "phase1_beta.md").write_text("# B\n", encoding="utf-8")
        return root

    def sources(root: Path) -> list[str]:
        return [
            e["source"]
            for e in extract(root).graph["edges"]
            if e["kind"] == "depends_on"
        ]

    control = sources(build(False))
    assert control == ["phase:development/common/alpha/phase1_alpha.md"]
    assert sources(build(True)) == control


def test_a_fenced_implementation_link_does_not_attribute_a_declaration(tmp_path: Path):
    """``_attribute_sources``' OTHER read, which the section-counter guard misses.

    The walker consults the fence mask twice — once before advancing the section
    counter, once before reading an ``**Implementation:**`` link — and the two
    are separate guards protecting separate failures. This one is the worse of
    the pair: a section with no phase document of its own, illustrating an
    `**Implementation:**` line in a fence, would have the illustration's phase
    INVENTED as the declaration's source. The module's own docstring records
    that an invented attribution produced a false cycle in the plan.

    **Added because a mutation survived.** Removing this guard alone left the
    whole suite green until the class check's fixture was re-sited.
    """
    root = tmp_path / "corpus"
    development = root / "development"
    development.mkdir(parents=True)
    (development / "sprints.md").write_text(SPRINTS, encoding="utf-8")
    (development / "common" / "alpha").mkdir(parents=True)
    (development / "common" / "alpha" / "roadmap.md").write_text(
        "# Alpha\n\n**Status:** 🟡 IN PROGRESS\n\n"
        "### Prose, with no phase of its own\n\n"
        "A phase entry is written like this:\n\n"
        "```markdown\n**Implementation:** [ghost](phase9_ghost.md)\n```\n\n"
        "**Depends on:** [`common/beta` · Beta One](../beta/phase1_beta.md)\n",
        encoding="utf-8",
    )
    (development / "common" / "beta").mkdir(parents=True)
    (development / "common" / "beta" / "roadmap.md").write_text(
        "# Beta\n\n**Status:** 🟡 IN PROGRESS\n", encoding="utf-8"
    )
    (development / "common" / "beta" / "phase1_beta.md").write_text("# B\n", encoding="utf-8")

    sources = [
        e["source"] for e in extract(root).graph["edges"] if e["kind"] == "depends_on"
    ]

    assert sources == ["component:development/common/alpha"]


def test_a_fenced_heading_does_not_resolve_a_tracked_anchor():
    """``derivations.anchor_resolves_in``.

    The verdict is ``True``, so a fenced illustration SUPPRESSES the
    ``TRACKED_ANCHOR_UNRESOLVED`` finding rather than raising a false one — a
    tracked item pointing at a section that does not exist reads as sound.
    """
    fenced = "# Doc\n\n```markdown\n## Ratification Queue\n```\n"
    assert derivations.anchor_resolves_in(fenced, "#ratification-queue") is False
    assert derivations.anchor_resolves_in("# Doc\n\n## Ratification Queue\n", "#ratification-queue")
    assert derivations.anchor_resolves_in("# Doc\n", "#ratification-queue") is False


def test_a_fenced_amendment_heading_is_not_a_second_surface(tmp_path: Path):
    """``amendments.census``, both halves: the heading walk and the item count.

    The census names ``tracked_items_standard.md`` in its exclusion list for
    exactly this reason — it quotes the convention — and the exclusion was
    needed only because the walk read fences. A surface that PROPOSES verbatim
    standard text fences it, and counting those lines tells a reader the surface
    owes rulings it does not owe.
    """
    root = tmp_path / "corpus"
    (root / "standards").mkdir(parents=True)
    (root / "standards" / "quoted.md").write_text(
        "# Quoted\n\nHow to surface one:\n\n"
        "```markdown\n## Standards implications (surfaced)\n\n- [ ] a candidate\n```\n",
        encoding="utf-8",
    )
    (root / "standards" / "real.md").write_text(
        "# Real\n\n## Standards implications (surfaced)\n\n"
        "- [ ] a candidate\n\n"
        "Proposed verbatim text:\n\n"
        "```markdown\n- not an item\n- also not an item\n```\n",
        encoding="utf-8",
    )

    surfaces = {s.file: s for s in amendments.census(root, Collector())}

    assert "standards/quoted.md" not in surfaces
    assert surfaces["standards/real.md"].item_count == 1


def test_a_fenced_exclusion_subsection_does_not_hide_a_component():
    """``sprints._parse_exclusions``.

    An exclusion SUPPRESSES an orphan finding, so a fenced example of the
    subsection would hide a component from the report on the strength of an
    illustration.
    """
    lines = [
        "## Sprint: Unplaced",
        "```markdown",
        "### Components deliberately not listed",
        "- `development/common/phantom/`",
        "```",
        "### Components deliberately not listed",
        "- `development/common/real/`",
        "## Sprint 9",
    ]
    found = sprints._parse_exclusions(lines, 0, fenced_mask(lines))
    assert [name for name, _line in found] == ["development/common/real"]


def test_an_unterminated_fence_is_reported_only_when_it_swallows_a_surface(tmp_path: Path):
    """The guard's own cost, reported on the LOSS rather than on the condition.

    Skipping fenced lines means a file that never closes its fence is skipped to
    EOF. That is right — but silence then looks exactly like a file with no
    amendment surface, so the census must say what it could not read. It must
    NOT say it for the four live files that carry an unterminated fence and
    swallow nothing, or the finding is noise on day one.

    The closing-delimiter case is asserted because it was WRONG first: the mask
    marks a delimiter line ``True`` whether it opens or closes, so a file ending
    on its own closing fence read as unterminated until the check was rewritten
    to walk the delimiters.
    """
    root = tmp_path / "corpus"
    (root / "standards").mkdir(parents=True)
    (root / "standards" / "swallowed.md").write_text(
        "# Doc\n\n```markdown\n## Standards implications (surfaced)\n",
        encoding="utf-8",
    )
    (root / "standards" / "harmless.md").write_text(
        "# Doc\n\n```bash\nls -la\n", encoding="utf-8"
    )
    (root / "standards" / "closed.md").write_text(
        "# Doc\n\n```markdown\n## Standards implications (surfaced)\n```\n",
        encoding="utf-8",
    )

    collector = Collector()
    amendments.census(root, collector)
    reported = {
        f.provenance.file for f in collector.findings if f.code == "UNPARSED_LINE"
    }

    assert reported == {"standards/swallowed.md"}


def test_discovery_does_not_read_a_fenced_phase_heading():
    """The sixth member of the class, and it was the LAST because of an import.

    ``discovery.is_phase_shaped`` classifies a document by a heading it carries,
    and it read fenced ones for as long as the delimiter lived in ``roadmaps`` —
    ``roadmaps`` imports ``discovery``, so ``discovery`` could not ask without a
    cycle. This test asserted the leak, PINNED, with ``MDC-Master-Planning#229``
    carrying the structural move. The move happened: the delimiter is now
    :mod:`~.fences`, a leaf, and the reason the gap existed stopped existing.

    Latent when closed — 0 fenced phase-shape headings on the live corpus and
    the derived artifact does not move — which is exactly why it could sit open.
    """
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "probe.md"
        probe.write_text(FENCED_PHASE_HEADING, encoding="utf-8")
        fenced = discovery.is_phase_shaped(Path(tmp), "probe.md", frozenset(), Collector())

        probe.write_text(REAL_PHASE_HEADING, encoding="utf-8")
        real = discovery.is_phase_shaped(Path(tmp), "probe.md", frozenset(), Collector())

    assert fenced == ""
    assert real == "carries a `## Requirements for completion` heading"


def test_no_module_outside_fences_spells_a_fence_delimiter():
    """The CLASS check for the length rule: one answer, and nobody may re-spell it.

    A closing fence must use the opener's character and be at least as long
    (CommonMark). Read length-blind, a four-backtick block wrapping a
    three-backtick example is CLOSED by the inner delimiter and everything after
    it is read as prose. Not hypothetical: it truncated
    ``clusters/phase3_kubevip_ha.md``'s amendment section 49 lines early
    at a shell comment, and six explicitly-deferred human rulings were reported
    as **zero owed**.

    **This asserts the SEAM, not the walkers.** Five walks each spelled their own
    toggle — four around ``FENCE_RE``, one around a bare ``startswith`` — and all
    five were wrong IDENTICALLY, which is indistinguishable from agreement until
    a nested fence appears. Enumerating walkers is what kept failing, so the
    check is that no module outside ``fences`` names a delimiter at all: a sixth
    walk cannot be length-blind without first re-introducing the duplication,
    and re-introducing it fails here.

    **A delimiter SPELLED AS A TEST is the offence, not a delimiter mentioned.**
    Prose about the convention — docstrings, and the ``expected=`` text a finding
    shows an operator ("every fenced block closed by a matching ``` or ~~~") —
    is how this package explains itself, and three modules would be unable to
    state their own contract if naming the characters were the offence. So the
    check keys on USE: a fence run reaching ``startswith``/``match``/``search``/
    ``re.compile``, or standing in a comparison. That is a toggle; a sentence is
    not.
    """
    package = Path(discovery.__file__).parent
    offenders: list[str] = []
    for module in sorted(package.glob("*.py")):
        if module.name == "fences.py":
            continue
        tree = ast.parse(module.read_text(encoding="utf-8"))
        docstrings = {
            id(node.body[0].value)
            for node in ast.walk(tree)
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef))
            and node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        }
        def spells_delimiter(node: ast.AST) -> bool:
            return (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in docstrings
                and (BACKTICK_RUN in node.value or TILDE_RUN in node.value)
            )

        for node in ast.walk(tree):
            tested: list[ast.AST] = []
            if isinstance(node, ast.Call):
                name = getattr(node.func, "attr", getattr(node.func, "id", ""))
                if name in TESTING_CALLS:
                    tested = list(node.args)
            elif isinstance(node, ast.Compare):
                tested = [node.left, *node.comparators]
            for argument in tested:
                if spells_delimiter(argument):
                    offenders.append(f"{module.name}:{argument.lineno} {argument.value!r}")

    assert offenders == [], (
        "a fence delimiter is spelled outside `fences.py`; it will be "
        "length-blind the day a nested fence appears:\n" + "\n".join(offenders)
    )


def test_the_delimiter_rule_itself():
    """The rule `advance_fence` encodes, at the seam every walk goes through."""
    assert advance_fence(BACKTICK_RUN + "`markdown", None) == (BACKTICK_RUN + "`", True)
    assert advance_fence(BACKTICK_RUN + "bash", BACKTICK_RUN + "`") == (
        BACKTICK_RUN + "`",
        False,
    ), "a shorter run inside a longer block is CONTENT, not a close"
    assert advance_fence(BACKTICK_RUN + "`", BACKTICK_RUN + "`") == (None, True)
    assert advance_fence(BACKTICK_RUN + "``", BACKTICK_RUN + "`") == (
        None,
        True,
    ), "a longer run closes"
    assert advance_fence(TILDE_RUN, BACKTICK_RUN) == (
        BACKTICK_RUN,
        False,
    ), "the other character never closes"


def test_a_nested_fence_does_not_truncate_a_section_at_a_shell_comment():
    """The live shape, end to end through :func:`amendments.scan`.

    A four-backtick block quoting proposed standard text, containing an inner
    example whose first line is a ``#`` comment that ``HEADING_RE`` matches.
    Length-blind, the section ends at that comment and every item below it is
    invisible — the surface reports owing nothing.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "development").mkdir()
        (root / "development" / "notes.md").write_text(NESTED_FENCE_DOC, encoding="utf-8")
        surfaces = amendments.census(root, Collector())

    section = [s for s in surfaces if s.heading == "Standards-amendment candidates"]
    assert len(section) == 1
    assert section[0].item_count == 2, "the nested fence must not end the section early"

def test_mask_fences_treats_a_nested_inner_run_as_content():
    """The re-derived call site, directly: ``measurements._mask_fences``.

    Its ``opened_at``/``swallowed`` bookkeeping had to grow a third case when the
    delimiter became length-aware — an inner run that does NOT close the block is
    CONTENT, so it belongs in what the block swallowed rather than beside it.
    Covered end-to-end by the class check; covered HERE so a regression names the
    function instead of a corpus.
    """
    balanced = (
        "before [a](gone.md)\n"
        + BACKTICK_RUN
        + "`markdown\n[placeholder](relative/path/to/standard.md)\n"
        + BACKTICK_RUN
        + "bash\n# not a close\n"
        + BACKTICK_RUN
        + "\n"
        + BACKTICK_RUN
        + "`\nafter [b](also-gone.md)\n"
    )
    masked = measurements._mask_fences(balanced)

    assert masked.unterminated_at is None, "the 4-run closes it; the 3-run does not"
    assert masked.swallowed == ""
    assert "relative/path/to/standard.md" not in masked.text
    assert "gone.md" in masked.text and "also-gone.md" in masked.text
    assert len(masked.text.splitlines()) == len(balanced.splitlines()), "line count"

    unterminated = (
        "before\n"
        + BACKTICK_RUN
        + "`markdown\n[swallowed](nowhere.md)\n"
        + BACKTICK_RUN
        + "bash\n# not a close\n"
        + BACKTICK_RUN
        + "\ntail [also](nowhere-either.md)\n"
    )
    masked = measurements._mask_fences(unterminated)

    assert masked.unterminated_at == 2, "the 4-run opener, not the inner 3-run"
    assert "nowhere.md" in masked.swallowed
    assert "nowhere-either.md" in masked.swallowed, (
        "everything below the OUTER opener is swallowed, including what sits "
        "after the inner run a length-blind walk would have read as a close"
    )


def test_parse_declarations_does_not_read_a_declaration_out_of_a_nested_fence(tmp_path: Path):
    """The other re-derived call site, directly: ``dependencies.parse_declarations``.

    Its ``while`` loop's fence skip became ``is_delimiter or was_open``. A
    ``**Depends on:**`` line inside a nested inner run must stay invisible, and
    the real declaration after the OUTER close must still be read — a skip that
    is wrong in either direction passes a test that only checks one.
    """
    root = tmp_path / "corpus"
    component_dir = root / "development" / "common" / "alpha"
    component_dir.mkdir(parents=True)
    # The line between the inner run and its partner is THE divergent slot: it is
    # fenced under the length rule and UNFENCED without it. A fixture that puts
    # anything else there passes on a length-blind delimiter — this one did, and
    # its own negative control is what said so.
    (component_dir / "roadmap.md").write_text(
        "# Alpha\n"
        "\n"
        "## Phase 1\n"
        "\n"
        + BACKTICK_RUN
        + "`markdown\n"
        "**Depends on:** [`common/ghost` · Ghost](../ghost/phase1_ghost.md)\n"
        "\n"
        + BACKTICK_RUN
        + "bash\n"
        "**Depends on:** [`common/phantom` · Phantom](../phantom/phase1_phantom.md)\n"
        + BACKTICK_RUN
        + "\n"
        + BACKTICK_RUN
        + "`\n"
        "\n"
        "**Depends on:** [`common/beta` · Beta](../beta/phase1_beta.md)\n",
        encoding="utf-8",
    )
    component = roadmaps.Component(
        path="development/common/alpha",
        roadmap="development/common/alpha/roadmap.md",
        label="Alpha",
        status_text=None,
        status_line=0,
        retired=False,
    )
    collector = Collector()
    found = dependencies.parse_declarations(root, component, collector)

    assert [declaration.line for declaration in found] == [13], (
        "only the declaration below the OUTER close is real; the two inside the "
        "4-backtick block are illustrations, and the inner 3-run does not end it"
    )
    assert "beta" in found[0].rest
    assert "ghost" not in found[0].rest and "phantom" not in found[0].rest
    assert not [f for f in collector.findings if f.code == UNPARSED_LINE], (
        "the outer fence DOES close, so nothing was swallowed"
    )

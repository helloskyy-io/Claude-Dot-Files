"""Unit tests for the ``sprints.md`` shapes — pure functions over strings.

The corpus is mid-conversion by its own §1 note, so the irregularity IS the
specification. Each case below is a shape the file actually carries today.
"""

from __future__ import annotations

import pytest

from planning_ui.plan_extractor.model import Collector
from planning_ui.plan_extractor.sprints import (
    CHECKBOX_RE,
    HOURS_RE,
    LAYER_RE,
    MARKERS,
    SPRINT_HEADING_RE,
    parse_sprints,
)
from planning_ui.plan_extractor.fences import fenced_mask


@pytest.mark.parametrize(
    "line,name",
    [
        ("## Sprint: Developer Planning UI", "Developer Planning UI"),
        ("## Sprint: Unplaced — every entry owes a ruling", "Unplaced — every entry owes a ruling"),
        # The interim shape §1 says some sections still carry.
        ("## Sprint — Secrets Management (40h)", "Secrets Management (40h)"),
    ],
)
def test_both_sprint_heading_shapes_are_accepted(line, name):
    """An unconverted sprint must be a finding about ITS items, not a section
    that vanishes from the graph."""
    match = SPRINT_HEADING_RE.match(line)
    assert match is not None
    assert match.group("name") == name


def test_a_non_sprint_h2_is_not_a_sprint():
    assert SPRINT_HEADING_RE.match("## How things are named here") is None


def test_fenced_blocks_are_masked_so_the_template_is_not_a_phantom_item():
    """The §6 template is a fenced example of a well-formed item.

    Parsing it would add a sprint item to the graph that no sprint contains —
    silent wrongness of exactly the class this phase exists to catch.
    """
    lines = [
        "before",
        "```",
        "- [x] **Component · Phase Name** · L<n> · ([roadmap](…)) — template",
        "```",
        "- [ ] **Real · Item** · L1 · ([roadmap](./r.md))",
    ]
    mask = fenced_mask(lines)
    assert mask == [False, True, True, True, False]


def test_an_unterminated_fence_masks_the_remainder():
    """Conservative direction: a stray fence hides items rather than inventing
    them. An invented item is unfalsifiable downstream; a missing one shows up
    as a count that does not reconcile."""
    assert fenced_mask(["a", "```", "b", "c"]) == [False, True, True, True]


@pytest.mark.parametrize(
    "body,layer",
    [
        ("**x** · L1 · ([roadmap](./r.md))", 1),
        ("**x** · L11 · ([roadmap](./r.md))", 11),
        ("**x** · cross-cutting · ([roadmap](./r.md))", None),
        ("**x** · ([roadmap](./r.md))", None),
    ],
)
def test_layer_extraction(body, layer):
    match = LAYER_RE.search(body)
    assert (int(match.group(1)) if match else None) == layer


def test_layer_regex_does_not_match_a_letter_run_inside_a_word():
    """`L` inside an identifier is not a layer.

    Without the boundary guards, `SL3` or `phase12_L4x` would silently supply a
    layer to an item that carries none — turning a finding into a false pass.
    """
    assert LAYER_RE.search("SL3") is None
    assert LAYER_RE.search("Ceph-L2-thing") is not None  # `-` is a boundary
    assert LAYER_RE.search("aL2") is None


@pytest.mark.parametrize(
    "body,low,high",
    [
        ("**~42h**", 42, None),
        ("**~30–40h**", 30, 40),
        ("**~10-15h**", 10, 15),
        ("**Estimate: ~42 hrs**", 42, None),
        ("~101h total", 101, None),
        ("nothing here", None, None),
    ],
)
def test_hour_shapes_the_corpus_actually_carries(body, low, high):
    match = HOURS_RE.search(body)
    assert (int(match.group("low")) if match else None) == low
    assert (int(match.group("high")) if match and match.group("high") else None) == high


def test_hours_regex_does_not_swallow_a_bare_number():
    """`~40` with no unit is not an hour figure.

    Sprint prose carries approximate counts (`~40 non-node files`); reading one
    as hours would manufacture a disagreement against a roadmap figure.
    """
    assert HOURS_RE.search("~40 non-node files") is None
    assert HOURS_RE.search("~40 files") is None


def test_checkbox_shapes():
    assert CHECKBOX_RE.match("- [x] **A** · L1")
    assert CHECKBOX_RE.match("- [ ] **A** · L1")
    assert CHECKBOX_RE.match("  - [ ] nested")
    assert CHECKBOX_RE.match("- [X] uppercase")
    assert CHECKBOX_RE.match("- [] no space") is None
    assert CHECKBOX_RE.match("* [ ] asterisk bullet") is None


def test_the_four_status_markers_are_pinned():
    """sprints.md §5. A marker is DERIVED, never typed, so the vocabulary is a
    contract with the derivation."""
    assert MARKERS == {
        "🔵": "NOT SCHEDULED",
        "🟠": "PLANNED",
        "🟡": "IN PROGRESS",
        "✅": "COMPLETE",
    }


def test_the_header_block_marker_wins_over_a_later_glyph(tmp_path):
    """First marker wins — a DIFFERENT property from the header-block bound.

    Named for what it actually verifies. Its first draft was named for the bound
    and was structurally blind to it: the header-block marker latches before the
    later glyph is ever reached, so removing the bound did not turn this test
    red. The bound's own guard is the next test, where no header-block marker
    exists to latch.
    """
    root = tmp_path
    (root / "development").mkdir(parents=True)
    (root / "development" / "sprints.md").write_text(
        "# Sprints\n"
        "\n"
        "## Sprint: Header Block\n"
        "🟠 PLANNED\n"
        "\n"
        "- [ ] service/x · Thing · L1 · ~2h\n"
        "\n"
        "✅ this line quotes a glyph in prose and is NOT the status\n"
    )

    document = parse_sprints(root, Collector())

    assert len(document.sprints) == 1
    assert document.sprints[0].marker == "PLANNED", (
        "the glyph below the first item must not overwrite the header-block marker"
    )


def test_a_sprint_with_no_marker_before_its_first_item_carries_none(tmp_path):
    """The discriminator: the bound must not invent a marker either."""
    root = tmp_path
    (root / "development").mkdir(parents=True)
    (root / "development" / "sprints.md").write_text(
        "# Sprints\n"
        "\n"
        "## Sprint: No Marker\n"
        "\n"
        "- [ ] service/x · Thing · L1 · ~2h\n"
        "\n"
        "✅ prose after the first item\n"
    )

    document = parse_sprints(root, Collector())

    assert document.sprints[0].marker is None

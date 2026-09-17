"""The derivation must not depend on where the checkout sits on the filesystem.

Reading the same commit from a git worktree at a different filesystem location
must not change the result. A resolver that tries a host-absolute link as a
real path first yields edges that exist only on the one host whose checkout
sits at that path — and a derivation that differs by location can never run
on a runner.

**The corpus below is written by the test, not shared with any fixture.** The
control has to be self-contained: a mutation of the resolver that broke a shared
fixture would over-fire on every test that reads it, and this test's claim is
narrower than that.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from planning_ui.plan_extractor import extract

#: A SYNTHETIC canonical host path, declared by the scratch corpus below in its
#: own `corpus.toml`. Never a path that exists on the machine running this:
#: the whole point is that the answer comes from the declaration.
CANONICAL_CHECKOUT = "/srv/example/planning"

#: A roadmap that links its phase the way 1,600+ corpus links are written — by
#: the host path of the canonical checkout — beside one written relatively.
ROADMAP = f"""# Widget

**Status:** 🟡 IN PROGRESS

## Relative Phase 🟠 PLANNED — **~5h**

**Implementation:** [`phase1_relative.md`](phase1_relative.md)

## Host-Absolute Phase 🟠 PLANNED — **~5h**

**Implementation:** [`phase2_absolute.md`]({CANONICAL_CHECKOUT}/development/common/widget/phase2_absolute.md)

**Depends on:** NONE
"""

SPRINTS = """# Sprints

## Sprint: One 🟡 IN PROGRESS

- [ ] **common/widget · Relative Phase** · L0 · ([roadmap](./common/widget/roadmap.md) · [phase](./common/widget/phase1_relative.md)) — x · **~5h**
"""


def _write_corpus(root: Path) -> None:
    widget = root / "development" / "common" / "widget"
    widget.mkdir(parents=True)
    (root / "corpus.toml").write_text(f'[corpus]\ncanonical_checkout = "{CANONICAL_CHECKOUT}"\n')
    (widget / "roadmap.md").write_text(ROADMAP)
    (widget / "phase1_relative.md").write_text("# Relative\n")
    (widget / "phase2_absolute.md").write_text("# Absolute\n")
    (root / "development" / "sprints.md").write_text(SPRINTS)
    for store in ("candidates", "issues", "operations", "standards"):
        (root / "tracked" / store).mkdir(parents=True)


def _plans_edges(root: Path) -> set[tuple[str, str]]:
    result = extract(root)
    return {
        (e["source"], e["target"]) for e in result.graph["edges"] if e["kind"] == "plans"
    }


def test_the_edge_set_is_identical_from_two_filesystem_paths(tmp_path: Path):
    """Requirement 2, as the plan words it: derive at two paths, compare edges."""
    first = tmp_path / "checkout-a"
    _write_corpus(first)
    second = tmp_path / "elsewhere" / "checkout-b"
    shutil.copytree(first, second)

    assert _plans_edges(first) == _plans_edges(second)


def test_a_host_absolute_link_yields_its_edge_at_a_non_canonical_path(tmp_path: Path):
    """The discriminator — the half of requirement 2 that failed before the fix.

    Two non-canonical paths agreed BEFORE the fix too: both dropped the edge.
    What made the graph path-dependent is that the canonical checkout kept it.
    So the assertion is that the edge is present from a path that is NOT the
    canonical one — which is every path the test can run at.
    """
    root = tmp_path / "checkout"
    _write_corpus(root)

    edges = _plans_edges(root)
    assert (
        "component:development/common/widget",
        "phase:development/common/widget/phase2_absolute.md",
    ) in edges, sorted(edges)
    assert (
        "component:development/common/widget",
        "phase:development/common/widget/phase1_relative.md",
    ) in edges

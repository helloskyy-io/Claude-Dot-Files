"""The codified-block check, held to its stated method.

Every assertion here is about the METHOD — the floor, the threshold, the
diverged/duplicated split, the tail, and scope-as-data. None asserts a count
against the live corpus: requirement 2 says the population is unknown and
should fall as sites are cited, and a pinned number would hide that.
"""
from __future__ import annotations

from pathlib import Path

from planning_ui.plan_extractor import codified
from planning_ui.plan_extractor.contract import Contract
from planning_ui.plan_extractor.model import Collector

PROFILE = """# S

## §4.2 the profile block

```yaml
type: workload-trusted
vlan: 120
bridge: vmbr0
ip_assignment: dhcp
node_role: server
pod_security: restricted
```
"""


def _corpus(tmp_path: Path, doc: str) -> Path:
    root = tmp_path / "corpus"
    (root / "standards" / "platform").mkdir(parents=True)
    (root / "standards" / "platform" / "clusters.md").write_text(PROFILE)
    (root / "development" / "common" / "w").mkdir(parents=True)
    (root / "development" / "common" / "w" / "phase1_p.md").write_text(doc)
    (root / "development" / "sprints.md").write_text("# s\n")
    return root


def _codes(collector: Collector) -> list[str]:
    return [f.code for f in collector.findings if f.code.startswith("CODIFIED")]


def test_a_copy_missing_a_field_is_diverged_and_names_the_field(tmp_path):
    """The class the rule was written from: a dropped `pod_security`."""
    doc = "# P\n\n```yaml\ntype: workload-trusted\nvlan: 120\nbridge: vmbr0\n" \
          "ip_assignment: dhcp\nnode_role: server\n```\n"
    collector = Collector()
    codified.check(_corpus(tmp_path, doc), collector, Contract())
    diverged = [f for f in collector.findings if f.code == codified.CODIFIED_BLOCK_DIVERGED]
    assert len(diverged) == 1
    assert "pod_security" in diverged[0].summary, diverged[0].summary
    assert "the-profile-block" in diverged[0].summary, "the finding cites the anchor"


def test_an_exact_copy_is_duplicated_and_ranks_below_a_drift(tmp_path):
    doc = "# P\n\n```yaml\ntype: workload-trusted\nvlan: 120\nbridge: vmbr0\n" \
          "ip_assignment: dhcp\nnode_role: server\npod_security: restricted\n```\n"
    collector = Collector()
    codified.check(_corpus(tmp_path, doc), collector, Contract())
    assert _codes(collector) == [codified.CODIFIED_BLOCK_DUPLICATED]


def test_a_document_that_CITES_the_block_produces_nothing(tmp_path):
    """The negative control, and the one that makes the others mean anything.

    Without it, a check that never fires and a check that is accurate are
    indistinguishable. This document does what the rule ASKS for — names the
    block and links it, re-typing no field — and must be silent.
    """
    doc = (
        "# P\n\nThe node profile is the [§4.2 the profile block]"
        "(../../../standards/platform/clusters.md#42-the-profile-block), verbatim.\n"
        "Nothing here re-types it.\n"
    )
    collector = Collector()
    reported, tail = codified.check(_corpus(tmp_path, doc), collector, Contract())
    assert (reported, tail) == (0, 0)
    assert _codes(collector) == []


def test_a_block_under_the_field_floor_is_not_a_match(tmp_path):
    """Three names collide by coincidence; four do not. The floor is the guard."""
    doc = "# P\n\n```yaml\ntype: a\nvlan: 1\nbridge: b\n```\n"
    collector = Collector()
    codified.check(_corpus(tmp_path, doc), collector, Contract())
    assert _codes(collector) == []


def test_an_overlap_under_the_threshold_is_the_tail_and_is_never_dropped(tmp_path):
    """Requirement 4: a quietly smaller finding set is the same defect as a
    quietly smaller graph.

    The tail is only REACHABLE against a large block — four shared names out of
    ten is 40%, under the threshold; four out of six would be 67% and a match.
    A fixture that cannot reach the branch would pass while proving nothing.
    """
    root = tmp_path / "corpus"
    (root / "standards" / "platform").mkdir(parents=True)
    (root / "standards" / "platform" / "big.md").write_text(
        "# S\n\n## §9 the big block\n\n```yaml\n"
        + "".join(f"field_{n}: v\n" for n in range(10))
        + "```\n"
    )
    (root / "development" / "common" / "w").mkdir(parents=True)
    (root / "development" / "common" / "w" / "phase1_p.md").write_text(
        "# P\n\n```yaml\n" + "".join(f"field_{n}: v\n" for n in range(4)) + "```\n"
    )
    (root / "development" / "sprints.md").write_text("# s\n")

    collector = Collector()
    _, tail = codified.check(root, collector, Contract())
    assert tail == 1, "four of ten shared is under the threshold and is the tail"
    assert _codes(collector) == [codified.CODIFIED_BLOCK_UNCLASSIFIED]
    row = collector.findings[-1]
    assert row.provenance.file.endswith("phase1_p.md"), "the tail names its file"
    assert row.provenance.line > 0, "and its line — a row without one is a number"


def test_the_scope_is_data_so_only_the_population_differs(tmp_path):
    """Requirement 5, demonstrated rather than asserted: the same corpus under
    a scope that excludes the document yields nothing, and nothing else moves."""
    doc = "# P\n\n```yaml\ntype: workload-trusted\nvlan: 120\nbridge: vmbr0\n" \
          "ip_assignment: dhcp\nnode_role: server\n```\n"
    root = _corpus(tmp_path, doc)

    wide = Collector()
    codified.check(root, wide, Contract(), scope=("development/",))
    narrow = Collector()
    codified.check(root, narrow, Contract(), scope=("nothing-here/",))

    assert _codes(wide) == [codified.CODIFIED_BLOCK_DIVERGED]
    assert _codes(narrow) == []


def test_a_structural_name_cannot_carry_a_match_on_its_own():
    """The false positive the first live run produced: a Deployment matched a
    PersistentVolume pattern on `kind`/`metadata`/`spec`/`name` alone."""
    index = [
        codified.Block("s.md", 1, "a", frozenset({"kind", "metadata", "spec", "name", "capacity"})),
        codified.Block("s.md", 9, "b", frozenset({"kind", "metadata", "spec", "name", "replicas"})),
        codified.Block("s.md", 20, "c", frozenset({"kind", "metadata", "spec", "name", "ports"})),
        codified.Block("s.md", 30, "d", frozenset({"kind", "metadata", "spec", "name", "rules"})),
    ]
    structural = codified.structural_names(index)
    assert {"kind", "metadata", "spec", "name"} <= structural
    copy = codified.Block("p.md", 1, "", frozenset({"kind", "metadata", "spec", "name"}))
    assert codified.match_share(copy, index[0], structural) == 0.0


def test_the_standards_index_carries_the_anchor_a_document_would_cite():
    blocks = codified.blocks_in("s.md", PROFILE.splitlines())
    assert len(blocks) == 1
    assert blocks[0].anchor == "§4.2 the profile block"
    assert "pod_security" in blocks[0].fields

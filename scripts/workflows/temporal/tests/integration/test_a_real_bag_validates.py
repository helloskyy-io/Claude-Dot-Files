"""Every bag a REAL dispatch left on this machine still validates.

WHY THIS TIER EXISTS AND WHAT IT ADDS. Every unit test in this component builds
its own bag, which means the whole suite could be green while the ONE path that
matters — an entrypoint resolving the configured root on this machine and opening
a bag there — was broken. This tier reads what the fleet actually wrote.

IT SKIPS WHEN THERE IS NOTHING TO READ, AND THAT IS NOT THE SAME AS PASSING.
`run-all.sh` reports a skipped category distinctly from a passing one, on purpose
— "a silent skip and a pass look identical in a summary table" is this repo's own
wording. A clone, a CI runner or a fresh machine has no journal because no
dispatch has run there, and there is nothing honest to assert about that.

WHAT THIS DOES NOT PROVE, so a green run is not over-read:

  * It does not prove any PARTICULAR workflow opened a bag. It reads whatever is
    on disk; a fleet where ten of eleven entrypoints had quietly stopped opening
    bags would still pass here on the eleventh's output. The structural guarantee
    is `tests/unit/test_every_parent_opens_a_run_bag.py`, and this tier does not
    substitute for it.
  * It does not exercise a REFUSAL against a real misconfigured root. A
    read-only mount and a foreign-owned directory both need a machine set up to
    have them; the contract for those is pinned in the unit tier.
  * It cannot run in CI as things stand, because the journal is machine-local
    state that no clone can re-derive — which is exactly the property that made
    `.claude/logs/` invisible to every consumer that reads the repo.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.journal.journal_activities import load_journal_config
from modules.journal.root import JournalRootError, resolve_journal_root
from modules.journal.validate import render_report, validate_bag


def _real_bags() -> list[Path]:
    """Bags under the root THIS machine's config resolves to, or an empty list.

    `create=False` because a test must not bring the journal into existence: a
    machine with no journal has to be distinguishable from one whose journal is
    empty, and creating it here would erase that distinction permanently.
    """
    try:
        root = resolve_journal_root(config=load_journal_config(), create=False)
    except (JournalRootError, RuntimeError):
        return []
    return sorted(p for p in root.iterdir() if p.is_dir())


BAGS = _real_bags()


@pytest.mark.skipif(not BAGS, reason="no journal on this machine — no dispatch has run here")
@pytest.mark.parametrize("bag_path", BAGS, ids=lambda p: p.name)
def test_a_real_bag_is_structurally_sound(bag_path: Path) -> None:
    """Structure, separately from integrity, because they fail for different reasons.

    A structural problem means the bag was WRITTEN wrongly — a bug in this
    package. An integrity problem means it was written correctly and something
    happened to it afterwards. Asserting them together would report the second
    when the cause was the first.
    """
    report = validate_bag(bag_path)
    assert not report.structural, (
        f"a bag this fleet wrote is malformed:\n{render_report(report)}")


@pytest.mark.skipif(not BAGS, reason="no journal on this machine — no dispatch has run here")
@pytest.mark.parametrize("bag_path", BAGS, ids=lambda p: p.name)
def test_a_real_bag_passes_integrity(bag_path: Path) -> None:
    """The bytes match the manifest — or the bag is still open, which is normal.

    An open bag is a run in flight or a run that died before sealing, and this
    tier runs on a machine where either is likely. Reporting that as a failure
    would make the suite red for the case the design most cares about getting
    right.
    """
    report = validate_bag(bag_path)
    assert report.ok, (
        f"a real bag failed integrity — this is data loss or an edit to an "
        f"immutable record, not a test problem:\n{render_report(report)}")


@pytest.mark.skipif(not BAGS, reason="no journal on this machine — no dispatch has run here")
def test_every_real_bag_reports_all_three_state_fields() -> None:
    """Requirement 8, against real bags rather than constructed ones.

    Constructed bags only ever have the states the constructing test asked for.
    This asserts the report is complete for whatever states actually occurred.
    """
    for bag_path in BAGS:
        report = validate_bag(bag_path)
        assert report.lifecycle in ("open", "sealed"), report.lifecycle
        assert isinstance(report.redacted, bool)
        assert isinstance(report.incomplete, bool)
        rendered = render_report(report)
        for field in ("lifecycle", "redacted", "incomplete"):
            assert f"{field}" in rendered, f"{bag_path.name}: {field} absent from the report"

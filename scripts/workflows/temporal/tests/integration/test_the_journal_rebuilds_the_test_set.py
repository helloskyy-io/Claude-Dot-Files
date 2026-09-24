"""PMP Phase 4 requirement 4 — the completeness arm: the REAL emits are complete.

ONE TEST, TWO INPUTS, NO SKIP. The phase doc rules it exactly this way: *"the
test runs on the merge path against a committed synthetic fixture, and against
the live journal only on a host"* — and *"the skip-when-absent arm is
forbidden."* So the input is chosen by WHERE THIS RUNS, not by whether an input
happens to be present:

  * on the merge path (`GITHUB_ACTIONS=true`, the runner's own declaration)
    the input is the committed fixture under `tests/fixtures/rebuild/`. A runner
    has a checkout and no journal BY PHASE 1's RULING — the journal is
    machine-local state outside every repo — so there is nothing absent to skip
    on; what CI can prove about a machine-local store is that the mechanism
    works, and this arm proves it on the same code path the host arm runs.
  * on a host, the input is THIS MACHINE'S journal and the planning repo's live
    `tracked/`. If either cannot be found, or no snapshot has been taken, the
    test goes RED and names the remedy. It does not skip. A host whose journal
    went missing must not produce a green integration tier.

THE REAL ROOT IS RESOLVED AT MODULE SCOPE, on purpose and per
`tests/conftest.py`'s warning: the session-wide autouse fixture redirects the
journal root into a sandbox for every test BODY, so a body that resolved the
root would read an empty sandbox and never the operator's journal. Collection
time is before any fixture runs. Nothing here WRITES to that root — the replay
writes into a `tmp_path` scratch, and `rebuild()` reads bags and the snapshot
only — so `test_the_suite_never_writes_to_the_operators_journal.py`'s property
holds.

WHAT A GREEN RUN ON A HOST MEANS, WITH ITS DENOMINATOR. The report states the
number of tracked-store intents applied against the bags replayed; pytest
captures it, so it is visible under `-s`, in full in every failure message,
and on demand from `scripts/rebuild.py check`. A host on
which no run has yet filed a tracked item — measured on the build host on
2026-09-15: 168 bags, 0 `tracked_*` events — proves the mechanism over the
real journal and a completeness guarantee over ZERO run-authored writes. The
figure is in the report so nobody reads "PASS" as more than it is.

A GAP, OR AN UNRECORDED ORDER, REACHES THE SUMMARY ON A GREEN RUN. A `gapped`
store is neither green nor red by design (`RebuildReport.ok`), and a
same-second cross-run tie is reported rather than resolved — but a report that
pytest captured on pass is a report nobody read, and `python.sh` passes no
`-s`. So both are raised as `warnings.warn` here: they print in pytest's
warnings summary without `-s`, red nothing, and requirement 7's "reported, not
silently tolerated" is then true at the tier that runs, not only under a flag.

WHAT A RED RUN ON A HOST MEANS. A `MISSING from rebuild` or `MISMATCH` line is
one of two things and the report cannot tell them apart (requirement 5's
ruling, `rebuild.py`'s docstring): a fleet write that never emitted — the
defect this phase exists to catch — or an out-of-run edit made on purpose. The
operator decides which; for the second, a new snapshot makes the edited state
the baseline.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path

from modules.assistant.tracked import rebuild as rb
from common.journal.journal_activities import load_journal_config
from common.journal.root import JournalRootError, resolve_journal_root
from planning_corpus import PLANNING_ROOT
from rebuild_fixture import COMMITTED

ON_MERGE_PATH = os.environ.get("GITHUB_ACTIONS") == "true"


def _host_inputs() -> tuple[Path, Path] | str:
    """`(journal_root, stores_root)` for this machine, or the reason there is none."""
    try:
        journal = resolve_journal_root(config=load_journal_config(), create=False)
    except (JournalRootError, RuntimeError) as exc:
        return (f"this host's journal root could not be resolved: {exc}\n"
                f"  A host with no journal has run no dispatch; the completeness "
                f"arm has nothing to read and REFUSES rather than skips. Run a "
                f"dispatch, or set `journal.root:` in config.yaml.")
    stores = PLANNING_ROOT / "tracked"
    if not stores.is_dir():
        return (f"no tracked/ directory at {stores} — the planning repo is not "
                f"beside this one, so the live stores cannot be read. A host "
                f"that runs dispatches has both repos side by side.")
    return journal, stores


if ON_MERGE_PATH:
    ARM = "mechanism (merge path): committed synthetic fixture"
    INPUTS: tuple[Path, Path] | str = (COMMITTED / "journal", COMMITTED / "tracked")
else:
    ARM = "completeness (host): the live journal and the live stores"
    INPUTS = _host_inputs()


def test_the_journal_rebuilds_the_test_set(tmp_path: Path) -> None:
    assert not isinstance(INPUTS, str), f"[{ARM}]\n{INPUTS}"
    journal, stores = INPUTS
    scratch = tmp_path / "scratch"
    scratch.mkdir()

    report = rb.rebuild(journal, stores, scratch=scratch)
    rendered = rb.render_report(report)
    print(f"[{ARM}]\n{rendered}")                  # shown under -s; in full on red

    assert report.bags_seen > 0, f"[{ARM}] replay read no bags — it examined nothing"
    assert set(report.stores) == set(rb.TEST_SET)

    # The negative control on REAL data: the exclusion is reported and non-empty.
    ops = report.stores["operations"]
    assert ops.verdict == "excluded", rendered
    assert ops.live_files > 0, (
        f"[{ARM}] tracked/operations/ is empty, so the exclusion demonstrates "
        f"nothing — the negative control needs live items to be visibly NOT rebuilt")
    assert ops.rebuilt_files == 0

    # Requirement 7: the verdict is two facts. The second is printed above.
    assert f"gapped: {report.bags_gapped}/{report.bags_seen}" in rendered

    assert report.ok, (
        f"[{ARM}] the rebuild does not reproduce the test set.\n{rendered}\n"
        f"  A MISSING or MISMATCH line is a fleet write that never emitted, OR "
        f"an out-of-run edit. Rule which. For a deliberate edit, take a new "
        f"snapshot: python3 -m modules.assistant.tracked.rebuild snapshot --stores {stores}")

    # Green, and still two facts the summary must carry (module docstring).
    gapped_stores = sorted(n for n, v in report.stores.items() if v.verdict == "gapped")
    if report.has_gaps or gapped_stores:
        warnings.warn(
            f"[{ARM}] gapped: {report.bags_gapped}/{report.bags_seen} bag(s); "
            f"stores gapped: {', '.join(gapped_stores) or 'none'} — diff "
            f"reported, not ruled\n{rendered}", stacklevel=1)
    if report.ambiguous_order:
        warnings.warn(
            f"[{ARM}] {len(report.ambiguous_order)} write(s) with no recorded "
            f"cross-run order — applied last by lexical tie-break, not by the "
            f"journal\n" + "\n".join(report.ambiguous_order), stacklevel=1)

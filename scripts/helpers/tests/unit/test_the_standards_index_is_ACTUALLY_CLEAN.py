"""The index audit runs against the REAL corpus, not only against fixtures.

WHY THIS EXISTS, AND IT IS THE gap THE AUDIT ITSELF HAD. `standards_index.py` has
unit tests for every predicate it owns — headers parsed, staleness detected, the
fence spliced — and every one of them runs against a synthetic tree. **Nothing ran
it against the corpus it was written for.** So the tool was correct and the check
was not in effect: a standard could lose its header, or arrive referenced by
nothing, and the suite would stay green while the audit that would have caught it
sat unrun.

That is the same shape as the intake harvest nobody drained and the sibling
worktrees nobody swept — a designed control with no cadence. The cadence for this
one is the suite, because the corpus is read by the suite already.

WHAT IT ASSERTS IS THE TOOL'S OWN VERDICT, not a re-implementation of it. A test
that re-derived "is every standard indexed" would be a second copy of the audit
that drifts from the first.

THE VENDORED STANDARDS ARE NOT THIS REPO'S TO FIX and the audit already separates
them — a mirror's header is its owner's to write. Only the OWNED corpus binds here.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HELPERS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HELPERS))
sys.path.insert(0, str(HELPERS.parents[0] / "workflows" / "temporal" / "tests"))

import planning_corpus  # noqa: E402
import standards_index as si  # noqa: E402

pytestmark = pytest.mark.skipif(
    not planning_corpus.planning_root().is_dir(),
    reason="no planning corpus beside this checkout — see planning_corpus.py")


def test_EVERY_OWNED_STANDARD_CARRIES_ITS_HEADER_AND_IS_INDEXED() -> None:
    """The audit's own two findings, against the corpus this repo actually reads.

    `Read when` is what a session routes on and `Breaking it looks like` is what a
    reviewer holds a PR against, so a standard missing either is one nobody can act
    on. A standard the index references nowhere is unreachable to a session that
    routes through `CLAUDE.md` — which is the only route (see the CLAUDE.md
    governance rule).
    """
    root = planning_corpus.planning_root()
    items = si.standards_in(root)
    assert len(items) > 5, (
        f"the sweep found {len(items)} standards under {root} — it is reading "
        f"nothing, and would pass for that reason alone")

    owned = [s for s in items if not s.vendored]
    assert owned, "every standard read as vendored — the provenance test inverted"

    incomplete = {str(s.path.relative_to(root)): s.missing for s in owned if s.missing}
    assert not incomplete, (
        f"{len(incomplete)} owned standard(s) are missing header lines the audit "
        f"requires:\n  "
        + "\n  ".join(f"{p} — missing {', '.join(m)}" for p, m in sorted(incomplete.items()))
        + "\nRun `standards_index.py --repo-root <repo>` for the full report.")

    stray = si.unindexed(root, owned)
    assert not stray, (
        f"{len(stray)} standard(s) are referenced by no index, so a session routing "
        f"through CLAUDE.md cannot reach them:\n  "
        + "\n  ".join(str(s.path.relative_to(root)) for s in stray))


def test_THE_GENERATED_INDEX_IS_NOT_STALE() -> None:
    """A generated block that stopped matching its source is worse than a
    hand-written one: it carries the authority of being derived while saying
    something the headers no longer say.

    Silent when the corpus has no fence — a repo that has not adopted generation
    has a hand-written index, and absence is not staleness.
    """
    root = planning_corpus.planning_root()
    drift = si.stale_block(root, si.standards_in(root))
    assert not drift, (
        f"the committed index block no longer matches the headers: {drift}. "
        f"Regenerate with `standards_index.py --repo-root <repo> --write`.")

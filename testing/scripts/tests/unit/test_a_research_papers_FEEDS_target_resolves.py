"""A paper's `Feeds:` line names where its evidence goes. It must resolve.

REQUESTED BY FIVE RUNS ON ONE PR AND BY THE REVIEWER ON A SECOND. PR #122's two
producing runs, its correction pass and both review passes each independently
proposed this check; PR #123's run hit the same class from the other side. When
five actors reach for the same instrument, the instrument is the finding.

WHAT IT PROTECTS, and it is not tidiness. `Feeds:` is the field that makes a
paper's destination checkable — the Research Standard's own framing is that a
paper with no destination is not in scope. A dead `Feeds:` is worse than a
missing one: it reads as a destination, so a planner follows it, finds nothing,
and has no way to tell whether the paper was misfiled or the target moved.

MEASURED WHEN THIS SHIPPED: 35 of 36 papers carry a header `Feeds:` and **15 of
them pointed at a file that does not exist** — a 43% rot rate. Every one is a
target that MOVED rather than a typo: `docs/development/roadmap.md` (8 papers)
never existed under that name, the Fleet Reliability sprint dissolved and took
its section with it, and MMF's narrative doc became `roadmap.md`.

WHY A FROZEN BASELINE AND NOT A CLEAN FAIL. Fifteen cannot be repointed in the
change that adds the guard — each needs somebody who knows where that evidence
was actually meant to land, and guessing would replace a visibly dead pointer
with an invisibly wrong one. So the existing rot is frozen and the ratchet runs
BOTH ways, the same shape `test_prompt_blocks_are_shared_not_copied` uses:

  * a dead target NOT in the baseline  -> fail. No new rot.
  * a baseline entry that now resolves -> fail. Delete the line.

The second is what makes the list shrink instead of becoming an excuse list.

WHAT IT DOES NOT CHECK, so it is not over-read:

  * **That the target is the RIGHT one.** A `Feeds:` pointing at a real file that
    has nothing to do with the paper resolves cleanly here. This checks that a
    reader following the pointer arrives somewhere, never that arriving helps.
  * **Section and line anchors.** `roadmap.md § Phase 2` resolves on the file; if
    § Phase 2 is gone, this is silent. Anchors are the obvious next axis and are
    deliberately out of scope rather than forgotten.
  * **`candidates.md` Notes**, which carry the same class of stale pointer with a
    different owner and no watcher. Named here because the reviewer named it, and
    because a guard that covers one of two surfaces reads as covering both.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
_FEEDS = re.compile(r"^Feeds:\s*(.+)$", re.M)
_TARGET = re.compile(r"[\w./-]+\.md")

# FROZEN 2026-08-19. (paper, target) -> why it is dead.
# THIS LIST MAY SHRINK. IT MAY NEVER GROW.
ACCEPTED: dict[tuple[str, str], str] = {
    ("dual_channel_outcome_records.md", "docs/development/memory-management-framework/memory-management-framework.md"):
        "MMF's narrative doc became roadmap.md when the component was planned",
    ("non_model_observables.md", "docs/development/memory-management-framework/memory-management-framework.md"):
        "same rename",
    ("backbone_edge_generality.md", "problem-statement.md"):
        "repo-root-relative; the file is at docs/standards/architecture/",
    ("dedicated_edge_routing.md", "problem-statement.md"): "same",
    ("subscription_economics.md", "problem-statement.md"): "same",
    ("edge_identity_trust.md", "standards/architecture/problem-statement.md"):
        "missing the docs/ prefix",
    ("workflow_reuse_boundary.md", "synthesis.md"):
        "bare filename; ambiguous between the product pool and a component pool",
    ("bernstein_capability_mining.md", "docs/development/roadmap.md"):
        "no such file has ever existed; the project's plan is sprint.md plus "
        "per-component roadmaps",
    ("convergence_stopping.md", "docs/development/roadmap.md"): "same",
    ("fleet_failure_modes.md", "docs/development/roadmap.md"): "same",
    ("hermes_assessment.md", "docs/development/roadmap.md"): "same",
    ("openclaw_assessment.md", "docs/development/roadmap.md"): "same",
    ("operator_interface.md", "docs/development/roadmap.md"): "same",
    ("paperclip_assessment.md", "docs/development/roadmap.md"): "same",
    ("python_sdk_long_activities.md", "docs/development/roadmap.md"): "same",
}


def _dead() -> dict[tuple[str, str], str]:
    """Every (paper, target) whose target resolves from neither anchor."""
    out: dict[tuple[str, str], str] = {}
    papers = sorted(ROOT.glob("docs/**/research/raw/*.md"))
    assert len(papers) > 10, (
        f"only {len(papers)} papers found under {ROOT} — the glob is wrong, and a "
        f"guard that reads nothing passes silently"
    )
    for p in papers:
        head = "\n".join(p.read_text(errors="ignore").splitlines()[:20])
        m = _FEEDS.search(head)
        if not m:
            continue
        for tok in _TARGET.findall(m.group(1)):
            if (ROOT / tok).exists() or (p.parent / tok).resolve().exists():
                continue
            out[(p.name, tok)] = str(p.relative_to(ROOT))
    return out


def test_no_NEW_dead_feeds_target() -> None:
    dead = _dead()
    new = {k: v for k, v in dead.items() if k not in ACCEPTED}
    assert not new, (
        "a paper's `Feeds:` names a file that does not exist. A dead destination "
        "reads as a real one, so a planner follows it and cannot tell whether the "
        "paper was misfiled or the target moved:\n  "
        + "\n  ".join(f"{v} -> {t}" for (p, t), v in sorted(new.items()))
        + "\n\nRepoint it, or — if the destination genuinely no longer exists — say "
        "so in the paper rather than leaving a pointer to nothing."
    )


def test_a_REPOINTED_target_leaves_the_baseline() -> None:
    """The ratchet. Without it the baseline is a permanent excuse list."""
    stale = sorted(k for k in ACCEPTED if k not in _dead())
    assert not stale, (
        "these baseline entries now resolve — the pointer was repaired or the "
        "target came back. Delete their lines so the list keeps shrinking:\n  "
        + "\n  ".join(f"{p} -> {t}" for p, t in stale)
    )


def test_the_detector_can_actually_FAIL(tmp_path: Path) -> None:
    """A control whose failing path never runs is not a control."""
    assert _TARGET.findall("docs/development/x/roadmap.md § Phase 2") == [
        "docs/development/x/roadmap.md"], "the target pattern stopped matching a path"
    assert not _TARGET.findall("the Phase 2 ruling"), "the pattern matches bare prose"
    assert _FEEDS.search("Topic: a\nFeeds:  docs/x.md\nLast validated: y"), (
        "the Feeds line pattern stopped matching a header block")

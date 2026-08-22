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

SIX OF THE FIFTEEN WERE REPOINTED ON THIS PR'S CORRECTION PASS, because the
baseline's own comments already named their correct target: four `Feeds:` lines
were repo-root-relative or missing the `docs/` prefix against a file that exists
at `docs/standards/architecture/problem-statement.md`, and two named MMF's
narrative doc, which is `docs/development/memory-management-framework/roadmap.md`.
Their `§` ANCHORS were repointed in the same edit — a correct path with a dead
anchor is the invisibly-wrong pointer this guard exists to prevent, and
`problem-statement.md` had been substantially reworded in the interval.

WHY A FROZEN BASELINE AND NOT A CLEAN FAIL. The remaining NINE cannot be
repointed by a run: each needs somebody who knows where that evidence was
actually meant to land, and guessing would replace a visibly dead pointer with
an invisibly wrong one. They are deferred to `C-9yi1yv2h`. So the existing rot
is frozen and the ratchet runs BOTH ways, the same shape
`test_prompt_blocks_are_shared_not_copied` uses:

  * a dead target NOT in the baseline  -> fail. No new rot.
  * a baseline entry that now resolves -> fail. Delete the line.
  * a baseline entry whose `Feeds:` LINE was deleted -> fail, and say something
    different. The first version of this module reported that case with the
    "these now resolve" message, which is how a ratchet launders rot: a deleted
    pointer is not a repaired one, and a baseline that shrinks because evidence
    stopped declaring a destination is shrinking for the wrong reason.

The second is what makes the list shrink instead of becoming an excuse list.
The third is what stops the shrink being fakeable in one keystroke.

WHAT IT DOES NOT CHECK, so it is not over-read:

  * **That the target is the RIGHT one.** A `Feeds:` pointing at a real file that
    has nothing to do with the paper resolves cleanly here. This checks that a
    reader following the pointer arrives somewhere, never that arriving helps.
  * **Section and line anchors.** `roadmap.md § Phase 2` resolves on the file; if
    § Phase 2 is gone, this is silent.
  * **Continuation lines.** Only the FIRST line of a `Feeds:` block is read, so a
    target named on a wrapped line is invisible — `backbone_edge_generality.md`
    names a `system-overview.md` that has never existed and this guard is blind
    to it.
  * **`candidates.md` Notes**, which carry the same class of stale pointer with a
    different owner and no watcher.

    All three are the same axis — a pointer that resolved once and does not now —
    and they are PLACED rather than merely named: `C-gkuvhctk` in
    `docs/standards/architecture/research/candidates.md`, with the measurement
    behind them. Naming an axis in a docstring and placing nothing is how a
    surfaced proposal dies at merge.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
_FEEDS = re.compile(r"^Feeds:\s*(.+)$", re.M)
_TARGET = re.compile(r"[\w./-]+\.md")

# FROZEN 2026-08-19, six entries repointed and removed 2026-08-22.
# THIS LIST MAY SHRINK. IT MAY NEVER GROW.
ACCEPTED: dict[tuple[str, str], str] = {
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


def _declared() -> list[tuple[Path, set[str] | None]]:
    """Every paper, paired with the targets its header `Feeds:` line names.

    `None` means the paper carries NO `Feeds:` line, which is a different answer
    from an empty set and from the paper being absent altogether. Keeping the
    three apart is the whole of `_ratchet` below; collapsing them is what let a
    deleted pointer report as a repaired one.
    """
    papers = sorted(ROOT.glob("docs/**/research/raw/*.md"))
    assert len(papers) > 10, (
        f"only {len(papers)} papers found under {ROOT} — the glob is wrong, and a "
        f"guard that reads nothing passes silently"
    )
    out: list[tuple[Path, set[str] | None]] = []
    for p in papers:
        head = "\n".join(p.read_text(errors="ignore").splitlines()[:20])
        m = _FEEDS.search(head)
        out.append((p, set(_TARGET.findall(m.group(1))) if m else None))
    return out


def _dead() -> dict[tuple[str, str], str]:
    """Every (paper, target) whose target resolves from neither anchor."""
    out: dict[tuple[str, str], str] = {}
    for p, targets in _declared():
        for tok in sorted(targets or ()):
            if (ROOT / tok).exists() or (p.parent / tok).resolve().exists():
                continue
            out[(p.name, tok)] = str(p.relative_to(ROOT))
    return out


def _ratchet(
    accepted: dict[tuple[str, str], str],
    dead: dict[tuple[str, str], str],
    declared: dict[str, set[str] | None],
) -> tuple[list[str], list[str]]:
    """Baseline entries that stopped being dead, split by WHY.

    Returns `(repaired, gone)`. A repaired entry is one the ratchet wants: the
    paper still declares a destination and following it now arrives somewhere.
    A gone entry is one where the paper stopped declaring anything — the rot was
    deleted rather than fixed, and the baseline would shrink on a lie.

    PURE, over already-read inputs, so `test_the_ratchet_DISCRIMINATES` can drive
    every arm on data this tree does not contain. A classifier only ever exercised
    against today's answer is a classifier that has never been tested.
    """
    repaired: list[str] = []
    gone: list[str] = []
    for paper, target in sorted(accepted):
        if (paper, target) in dead:
            continue
        if paper not in declared:
            gone.append(f"{paper} -> {target}: the paper itself is gone")
        elif declared[paper] is None:
            gone.append(f"{paper} -> {target}: the paper's `Feeds:` line is gone")
        elif target in (declared[paper] or set()):
            repaired.append(f"{paper} -> {target}: the target exists again")
        else:
            repaired.append(f"{paper} -> {target}: repointed away from it")
    return repaired, gone


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


def _current_ratchet() -> tuple[list[str], list[str]]:
    return _ratchet(ACCEPTED, _dead(), {p.name: t for p, t in _declared()})


def test_a_REPOINTED_target_leaves_the_baseline() -> None:
    """The ratchet. Without it the baseline is a permanent excuse list."""
    repaired, _ = _current_ratchet()
    assert not repaired, (
        "these baseline entries no longer point at nothing — the target came back "
        "or the paper was repointed. Delete their lines so the list keeps "
        "shrinking:\n  " + "\n  ".join(repaired)
    )


def test_a_DELETED_pointer_is_NOT_a_repaired_one() -> None:
    """The half that makes the shrink mean something.

    Deleting a paper's `Feeds:` line removes its entry from `_dead()` exactly as
    a real repair does. Reported with the repair message — which is what this
    module did when it shipped — the ratchet congratulates a run for destroying
    the evidence it was supposed to fix, and the baseline gets shorter while the
    tree gets worse.
    """
    _, gone = _current_ratchet()
    assert not gone, (
        "a baseline entry stopped being dead because its `Feeds:` line stopped "
        "existing, NOT because it was repaired. A deleted pointer is not a "
        "repaired pointer, and this is the one way the baseline can shrink "
        "dishonestly:\n  " + "\n  ".join(gone)
        + "\n\nRestore the line and repoint it. If the paper genuinely has no "
        "destination any more, that is a Research Standard question about what "
        "such a paper's state IS — see `C-9yi1yv2h` — not a line to delete."
    )


def test_the_detector_can_actually_FAIL(tmp_path: Path) -> None:
    """A control whose failing path never runs is not a control."""
    assert _TARGET.findall("docs/development/x/roadmap.md § Phase 2") == [
        "docs/development/x/roadmap.md"], "the target pattern stopped matching a path"
    assert not _TARGET.findall("the Phase 2 ruling"), "the pattern matches bare prose"
    assert _FEEDS.search("Topic: a\nFeeds:  docs/x.md\nLast validated: y"), (
        "the Feeds line pattern stopped matching a header block")


@pytest.mark.parametrize(
    "declared, expect_repaired, expect_gone",
    [
        # The target came back and the paper still names it.
        ({"a.md": {"gone.md"}}, 1, 0),
        # The paper was repointed at something else. That is a repair.
        ({"a.md": {"docs/real.md"}}, 1, 0),
        # The `Feeds:` line was deleted. That is NOT a repair.
        ({"a.md": None}, 0, 1),
        # The paper was deleted. Also not a repair.
        ({}, 0, 1),
    ],
)
def test_the_ratchet_DISCRIMINATES(
    declared: dict[str, set[str] | None], expect_repaired: int, expect_gone: int
) -> None:
    """Every arm driven, on a baseline this tree does not contain.

    Written because the two outcomes are indistinguishable from `_dead()` alone —
    both simply drop out of it — so a classifier that answered "repaired"
    unconditionally would have looked correct against the real tree on the day it
    shipped and stayed silent forever after.
    """
    accepted = {("a.md", "gone.md"): "frozen for this control"}
    repaired, gone = _ratchet(accepted, {}, declared)
    assert (len(repaired), len(gone)) == (expect_repaired, expect_gone), (
        f"classified {repaired=} {gone=} for {declared=}"
    )

    # AND THE STILL-DEAD ARM STAYS SILENT, whatever the paper declares: an entry
    # that is still in `_dead()` has not moved and is not the ratchet's business.
    assert _ratchet(accepted, dict(accepted), declared) == ([], [])

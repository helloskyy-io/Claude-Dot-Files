"""A workflow and its `_minor` sibling may differ in DEPTH, never by accident.

THE BLIND SPOT THIS COVERS, named in the standard that created its sibling.
`workflow-scripts.md` § *A prompt block with two consumers is promoted* ends by
saying what its test cannot see: *"Matching is verbatim, so a copy that has
already drifted by one word is invisible — and a drifted copy is the more
dangerous kind, because it reads as intent rather than as an accident."*
`test_prompt_blocks_are_shared_not_copied` hashes blocks, so one edited word
takes a pair out of its view entirely. This is the complement: pairs that are
CLOSE and not equal.

WHAT IT COST, MEASURED, AND IT IS WHY THE SCOPE IS TIER SIBLINGS. PR #100
promoted 35 duplicated blocks and shipped green. A review pass then found that
`build_refine` and `build_refine_minor` had drifted by one sentence in two
places, IN OPPOSITE DIRECTIONS: the major tier alone was told `RULING-REQUIRED`
extends to a brief's CONSTRAINT and not only to a definition-of-done's MEANS;
the minor tier alone was told the measured evidence that rejections get left
standing. Opposite directions is the tell — a deliberate tiering runs one way.
So the two tiers were disposing findings under different rules, on a surface
where both workflows' own comments say the tiers differ **in how many review
lenses they run, never in what a pass IS**. Both were reconciled by union and
promoted; the pairs below are what remained.

IT SURFACES, IT DOES NOT RULE, and that distinction is load-bearing. The same
standards paragraph assigns the near-duplicate judgement to *"the
fork-vs-parameterize ruling, not to a test"* — so this test decides nothing
about the seven pairs it froze. It asserts only that the SET has not grown, and
its failure message offers both exits: promote it, or record it here as
deliberate with a note saying why. A test that offered only the first would be
making the ruling, which is the thing the standard reserves.

WHY TIER SIBLINGS AND NOT THE WHOLE CORPUS. Across all children there are 19
near-duplicate pairs, most of them cross-family (`build_refine` +
`plan_revision` and similar). Whether two children in different families should
say the same thing is a real question nobody has answered. Whether a workflow
and its own `_minor` sibling should is already answered, in both workflows'
comments and in this repo's own test messages — so this is the subset where a
drift is an accident by definition rather than by argument.

WHAT THIS DOES NOT LOOK AT, so the guard is not over-read:

  * **Blocks under 120 bytes**, matching its sibling's floor. A one-line drift
    in a short block is invisible to both guards.
  * **Similarity below 0.80.** Two paragraphs saying opposite things in similar
    words score low, and this will never see them. It catches copies that
    drifted, never divergence that was written from scratch.
  * **Which side is right.** When a pair is genuinely accidental the remedy is
    usually a union, but that is a reading of the two texts, not a computation.
  * **Anything outside the child prompt tree.** Drift between a prompt and the
    standard it quotes is a different problem with no guard at all.
"""
from __future__ import annotations

import difflib
import re
from pathlib import Path

ASSISTANT = Path(__file__).resolve().parents[2] / "modules" / "assistant"
SHARED = ASSISTANT / "prompts"

# Both floors match `test_prompt_blocks_are_shared_not_copied` so the two guards
# partition the same population rather than overlapping in a way nobody can
# reason about: it owns ratio == 1.0, this owns 0.80 < ratio < 1.0.
MIN_BLOCK = 120
NEAR = 0.80

# A workflow and the `_minor` tier of the same job.
TIER_PAIRS = [
    ("build_draft", "build_draft_minor"),
    ("build_refine", "build_refine_minor"),
    ("research_write", "research_write_minor"),
]

# How much of a block's opening identifies it here. Long enough to be unique
# within one child, short enough that editing the body does not silently rename
# an entry and read as a brand-new pair.
KEY_LEN = 60

# FROZEN 2026-08-17. "<tier pair>" -> {opening of the major tier's block: note}.
# THIS LIST MAY SHRINK. IT MAY NEVER GROW WITHOUT A NOTE SAYING THE DIFFERENCE
# IS DELIBERATE — that sentence is the whole difference between a baseline and
# an excuse list, and it is the reader's only evidence that a pair was looked at.
#
# None of these has been ruled on. They are frozen as OBSERVED, which is the
# honest state: the fork-vs-parameterize ruling has not been made for any of
# them, and a test may not make it. The two pairs that WERE ruled on — by the
# review pass that found them — are absent because they were reconciled and
# promoted, which is what a shrink looks like here.
ACCEPTED_DRIFT: dict[str, dict[str, str]] = {
    "build_draft+build_draft_minor": {
        "**IF THE TASK IS TO CHARACTERIZE EXISTING BEHAVIOUR, ESTABLI":
            "0.86 — the characterization rule. Unruled.",
    },
    "build_refine+build_refine_minor": {
        "#### code-reviewer agent — correctness and code quality\nAnal":
            "0.91 — the code-reviewer lens brief. Plausibly deliberate: this is "
            "the one axis the two tiers are documented to differ on.",
        "- Read the PR diff, its body, its commits, AND ITS COMMENTS:":
            "0.90 — the major tier alone carries the `gh pr view` truncation "
            "warning. Reads accidental, same shape as the two that were fixed. "
            "Unruled: reconciling it changes what a tier is told.",
        "## Stage 5: SUBMIT\n- Stage any uncommitted changes remaining":
            "0.86 — the submit stage. Unruled.",
        "- **When a verification FAILS, doubt your own invocation bef":
            "0.81 — the failed-reproduction rule. Unruled.",
        "- **If the PR ships or MODIFIES a tool that certifies other ":
            "0.81 — the mutate-the-harness rule. Unruled.",
    },
    "research_write+research_write_minor": {
        "RULES:\n- This is an EVIDENCE workflow: never fabricate, neve":
            "0.94 — the evidence rules. Unruled.",
    },
}


def _blocks(child: str) -> list[str]:
    """Every substantive block in one child's prompts, in no particular order."""
    out = []
    for p in ASSISTANT.rglob("prompts/*.md"):
        if p.parent == SHARED or p.parent.parent.name != child:
            continue
        for raw in re.split(r"\n\s*\n", p.read_text()):
            b = raw.strip()
            if len(b) >= MIN_BLOCK:
                out.append(b)
    return out


def _drifted(major: str, minor: str) -> dict[str, float]:
    """Openings of the MAJOR tier's blocks that a minor-tier block nearly matches.

    `quick_ratio()` is an UPPER BOUND on `ratio()`, so skipping on it can never
    discard a real hit — it is the only prefilter that is safe here. The obvious
    alternative, skipping on a length difference, is not: two blocks differing
    30% in length can still score 0.82.
    """
    found: dict[str, float] = {}
    minor_blocks = _blocks(minor)
    for x in _blocks(major):
        best = 0.0
        for y in minor_blocks:
            m = difflib.SequenceMatcher(None, x, y)
            if m.quick_ratio() <= NEAR:
                continue
            r = m.ratio()
            if NEAR < r < 1.0:
                best = max(best, r)
        if best:
            found[x[:KEY_LEN]] = best
    return found


def test_no_NEW_drift_appears_between_a_workflow_and_its_minor_tier() -> None:
    new: list[str] = []
    for major, minor in TIER_PAIRS:
        frozen = ACCEPTED_DRIFT[f"{major}+{minor}"]
        for opening, ratio in sorted(_drifted(major, minor).items()):
            if opening not in frozen:
                new.append(f"{major} vs {minor}  ({ratio:.2f})  {opening!r}")
    assert not new, (
        "a block is NEARLY identical between a workflow and its _minor tier and "
        "is not in the frozen list. The two tiers are documented to differ in "
        "review depth and in nothing else, so a one-sentence difference is "
        "almost always an edit that landed in one of them:\n  "
        + "\n  ".join(new)
        + "\n\nTWO WAYS TO CLOSE THIS, and the second is a real option, not a "
          "fallback:\n"
          "  1. The difference is an accident — reconcile the two (usually by "
          "union, since both texts were meant to apply), then PROMOTE the block "
          "to modules/assistant/prompts/, because it is now verbatim-shared and "
          "test_no_NEW_block_is_copied_between_children will say so.\n"
          "  2. The difference is DELIBERATE — add the opening to "
          "ACCEPTED_DRIFT with a note saying what the tiers are meant to say "
          "differently. This test does not rule on that; it only requires that "
          "somebody did."
    )


def test_a_RECONCILED_drift_is_removed_from_the_frozen_list() -> None:
    """The ratchet. Without it the list is an excuse list, exactly as next door."""
    stale: list[str] = []
    for major, minor in TIER_PAIRS:
        key = f"{major}+{minor}"
        live = _drifted(major, minor)
        stale += [f"{key}  {o!r}" for o in sorted(ACCEPTED_DRIFT[key]) if o not in live]
    assert not stale, (
        "these frozen entries no longer describe a near-duplicate — the pair was "
        "reconciled, promoted, deleted, or its opening was edited. Remove the "
        "line so the list keeps shrinking:\n  " + "\n  ".join(stale)
    )


def test_the_frozen_list_COVERS_the_pairs_it_claims_to() -> None:
    """Vacuity guard: a typo'd child name would make both tests assert nothing.

    `_blocks()` filters by directory name and returns an empty list for a name
    that matches nothing, so a misspelled tier would report zero drift forever
    and both assertions above would pass for the wrong reason.
    """
    assert set(ACCEPTED_DRIFT) == {f"{a}+{b}" for a, b in TIER_PAIRS}
    for major, minor in TIER_PAIRS:
        for child in (major, minor):
            assert len(_blocks(child)) > 5, (
                f"{child} yielded {len(_blocks(child))} blocks over {MIN_BLOCK} "
                f"bytes — the child name is wrong or its prompts moved, and this "
                f"module is comparing nothing against nothing."
            )

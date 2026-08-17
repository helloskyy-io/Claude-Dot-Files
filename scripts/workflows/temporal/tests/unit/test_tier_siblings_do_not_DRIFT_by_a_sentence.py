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
about the pairs it froze. It asserts only that the SET has not grown, and
its failure message offers both exits: promote it, or record it here as
deliberate with a note saying why. A test that offered only the first would be
making the ruling, which is the thing the standard reserves.

TWO DETECTORS, BECAUSE A RATIO IS BLIND TO THE SHAPE THIS FLEET ACTUALLY
PRODUCES. Every drift observed here has been ONE-SIDED ADDITIVE: one tier's
block is the other's with text INSERTED, nothing replaced and nothing deleted.
A similarity ratio has INVERTED sensitivity to that class — the more text was
appended, the lower the score — so a ratio floor is least likely to fire on the
largest accidental divergences. Measured on the review pass that found this:
seven one-sided-additive pairs existed, and THREE were invisible below the 0.80
floor, at 0.786, 0.771 and 0.479. All three were the same accidental-append
class, in the same pair that motivated this module. So `_appended` runs beside
`_drifted` and needs no threshold at all: "all opcodes are equal or insert" is
exact. Lowering NEAR was measured and rejected — 0.65 still misses the 0.479
pair, and 0.50 grows the frozen list with false positives in the other two tier
pairs.

WHY TIER SIBLINGS AND NOT THE WHOLE CORPUS. Near-duplicate pairs exist across
the whole child corpus, most of them cross-family (`build_refine` +
`plan_revision` and similar). Whether two children in different families should
say the same thing is a real question nobody has answered. Whether a workflow
and its own `_minor` sibling should is already answered, in both workflows'
comments and in this repo's own test messages — so this is the subset where a
drift is an accident by definition rather than by argument.

THAT SENTENCE USED TO CARRY A COUNT AND THE COUNT IS NOW DERIVED INSTEAD, which
is not tidying. It read "there are 19 near-duplicate pairs" and 19 was wrong
when written — the corpus held 22, and 19 was the undercount produced by a
25%-length prefilter that `_drifted` rejects below as unsafe. The reconciliation
in the same PR then moved the true figure TO 19, so the wrong number became
accidentally right while nothing about how it was obtained improved. A bare
count in prose is a race with the tree; `test_promotion_guard_prose_FIGURES_are_
derived` now binds this one to the detector that produces it.

WHAT THIS DOES NOT LOOK AT, so the guard is not over-read:

  * **Blocks under 120 bytes**, matching its sibling's floor. A one-line drift
    in a short block is invisible to both guards.
  * **A drift that BOTH replaces and inserts text AND scores under 0.80.** This
    is the real residual, and it is narrower than what this list used to claim.
    It said the sub-floor region held "paragraphs saying opposite things in
    similar words" and "divergence written from scratch" — measurably not what
    was down there. `_appended` now takes the whole one-sided region at any
    ratio, so what remains uncovered is two-sided divergence that also scores
    low. Divergence written from scratch is still invisible, correctly: it is
    not a copy that drifted.
  * **A block present in ONE tier and absent from the other.** Both detectors
    compare pairs, so text existing in only one sibling has no counterpart to
    match and cannot register — this is the LARGEST uncovered class, not a
    corner. Most of it is the documented lens-count axis (the major tier's
    Stage-2a/2b machinery), but not all: `MUTATE AN ASSERTION'S SCOPE`,
    `COMPARE THE CHECK SET` and `PRINT WHAT THE MUTATION ACTUALLY PRODUCED` are
    general guidance only one tier is given. Whether they SHOULD be is the
    fork-vs-parameterize ruling, unmade, and no guard can make it.
  * **Which side is right.** When a pair is genuinely accidental the remedy is
    usually a union, but that is a reading of the two texts, not a computation.
  * **Anything outside the child prompt tree.** Drift between a prompt and the
    standard it quotes is a different problem with no guard at all — and so is
    drift between a child's block and a SHARED fragment, since `_blocks()` skips
    the pool.
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
            "0.91 — the code-reviewer lens brief, one-sided additive. Unruled, "
            "and the ONE pair deliberately left when the other six were "
            "reconciled: review depth is the single axis the two tiers are "
            "documented to differ on, so this is the one place a difference is "
            "plausibly intended. Note the measured delta is 'Give it the diff "
            "and the original task.' — a dispatch-contents sentence, not a "
            "lens-count one, so the 'plausibly deliberate' reading is weaker "
            "than it looks and the ruling is still owed.",
        "## Stage 5: SUBMIT\n- Stage any uncommitted changes remaining":
            "0.86 — the submit stage. Two-sided, so not the append class. "
            "Unruled.",
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


def _one_sided(small: str, big: str) -> bool:
    """True when `big` is `small` with text INSERTED — nothing replaced or deleted.

    Split out as a pure function so the control below can drive it with
    synthetic input. The live tree holds one member of this class, so the real
    corpus can only ever exercise the passing path.
    """
    return all(tag in ("equal", "insert")
               for tag, *_ in difflib.SequenceMatcher(None, small, big).get_opcodes())


def _appended(major: str, minor: str) -> dict[str, float]:
    """Openings of MAJOR blocks that are one tier's text plus an APPEND.

    The second detector, and it needs no threshold: a ratio answers "how alike",
    which is the wrong question for a class defined by "identical, plus more".
    Runs beside `_drifted` rather than replacing it — the ratio still owns
    two-sided edits, where no subset relation holds in either direction.
    """
    found: dict[str, float] = {}
    minor_blocks = _blocks(minor)
    for x in _blocks(major):
        best = 0.0
        for y in minor_blocks:
            if x == y:
                continue          # identical is the verbatim guard's population
            if _one_sided(x, y) or _one_sided(y, x):
                best = max(best, difflib.SequenceMatcher(None, x, y).ratio())
        if best:
            found[x[:KEY_LEN]] = best
    return found


def _drift(major: str, minor: str) -> dict[str, float]:
    """Every near-duplicate this module can see, from BOTH detectors.

    Both tests key on this, so a pair caught only by `_appended` — which is
    every pair below the ratio floor — is frozen and ratcheted on exactly the
    same terms as one the ratio found.
    """
    seen = dict(_drifted(major, minor))
    for opening, ratio in _appended(major, minor).items():
        seen[opening] = max(seen.get(opening, 0.0), ratio)
    return seen


def test_the_APPEND_detector_fires_on_a_one_sided_drift() -> None:
    """Live control for `_one_sided`, from the class the ratio floor could not see.

    Three synthetic cases, because red-on-mutation is not enough on its own:
    the detector must CATCH the append class, must NOT catch a two-sided edit
    (or it becomes a second ratio with no threshold and floods the frozen list),
    and must report the empty comparison honestly.
    """
    base = "A rule with a reason attached, long enough to be a real block of prose."
    appended = base + " **Measured:** and here is the evidence sentence that landed in one tier."
    assert _one_sided(base, appended), "the append class is not caught"
    assert not _one_sided(appended, base), "the subset relation is not directional"

    replaced = base.replace("reason", "justification")
    assert not _one_sided(base, replaced), (
        "a REPLACED word must not read as an append — this detector's whole "
        "claim is that it needs no threshold, which holds only if it is exact"
    )
    assert not _one_sided(replaced, base), "the replacement must fail both ways"

    assert _one_sided("", base), "insertion into nothing is still insertion"
    assert not _one_sided(base, ""), "deletion to nothing must not read as insertion"


def test_the_two_detectors_TOGETHER_cover_the_pairs_the_frozen_list_names() -> None:
    """Vacuity floor for the union, and the reason `_drift` exists at all.

    If `_appended` silently returned `{}` — a typo'd child name, an opcode API
    change — the union would collapse to the ratio detector and every sub-floor
    pair would go unwatched while both assertions below stayed green. So assert
    the append detector reaches a non-zero population on the pair it was built
    for, and that everything frozen is visible to the union.
    """
    assert _appended("build_refine", "build_refine_minor"), (
        "the append detector finds NOTHING in the pair it was written for — it "
        "is asserting nothing at all"
    )
    for major, minor in TIER_PAIRS:
        live = _drift(major, minor)
        for opening in ACCEPTED_DRIFT[f"{major}+{minor}"]:
            assert opening in live, (
                f"{major}+{minor} freezes {opening!r}, which NEITHER detector "
                f"can see — the entry is unfalsifiable"
            )


def test_no_NEW_drift_appears_between_a_workflow_and_its_minor_tier() -> None:
    new: list[str] = []
    for major, minor in TIER_PAIRS:
        frozen = ACCEPTED_DRIFT[f"{major}+{minor}"]
        for opening, ratio in sorted(_drift(major, minor).items()):
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
        live = _drift(major, minor)
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

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

AND A THIRD, BECAUSE BOTH OF THOSE READ A BLOCK AS AN ATOM. `_orphan_lines`
looks INSIDE the pairs the two above surface, and it exists because the block
granularity hid a live defect for two review passes. The `## Stage 5: SUBMIT`
pair sat frozen here noted *"Two-sided, so not the append class. Unruled."* —
a classification true about the MECHANISM and misleading about the CONTENT. Its
two-sidedness was ENTIRELY tier-identity tokens (the rework-vs-scoped-correction
line and the `build-refine:` commit prefix), and hiding behind that noise was a
pure one-sided omission: the minor tier was never told to RE-CHECK `origin/main`
before pushing, an instruction whose own text carries the evidence *"two
candidate-id collisions in one day, one of which would have merged silently"*.
The ratio detector saw a pair and said nothing about its contents; the append
detector was routed away by the tier-identity replacements; the frozen note
recorded the pair as looked-at. **A baseline entry is the one place a defect can
be simultaneously recorded and invisible**, so the remedy keys on the class —
a whole LINE with no counterpart on the other side — rather than on the bullet
that happened to be missing.

WHY A LINE AND NOT A SENTENCE. These prompts are bullet lists, so a line IS the
unit an author adds or forgets; splitting further would fire on every reworded
clause. `LINE_PAIRED` is the floor below which a line is judged to have no
counterpart at all, and it is chosen from a measured GAP rather than tuned:
every line in every surfaced pair scores at or above 0.826 against its best
counterpart, and the reconciled defect scores 0.253 when reintroduced. Anything
between those separates them identically, so the constant sits in the middle of
an empty band rather than on a side somebody had to pick.

THE FIRST VERSION OF THAT PARAGRAPH WAS WRONG, and how it was wrong is worth
keeping. It cited a gap between 0.366 and 0.692 — which was one line pair
measured twice, in two directions, because `difflib`'s autojunk heuristic builds
its ignore-set from the second argument alone and every line here is long enough
to trigger it. The floor was calibrated on an artifact, and the pair it made
look like an orphan was frozen below as a deliberate tier difference. Two review
lenses caught it independently. `_pair_score` is the fix and
`test_the_LINE_score_does_not_depend_on_ARGUMENT_ORDER` is what stops it
returning; the episode is recorded because a guard that mis-measured its own
population once will be read by someone deciding whether to trust its numbers.

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
count in prose is a race with the tree, so this one is no longer stated here —
`test_promotion_guard_prose_figures_are_DERIVED` fails any figure in these
guards that is neither bound to a deriver nor declared historical.

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
  * **A block present in ONE tier and absent from the other.** Both block
    detectors compare pairs, so text existing in only one sibling has no
    counterpart to match and cannot register — this is the LARGEST uncovered
    class, not a corner. Most of it is the documented lens-count axis (the major
    tier's Stage-2a/2b machinery), but not all: `MUTATE AN ASSERTION'S SCOPE`,
    `COMPARE THE CHECK SET` and `PRINT WHAT THE MUTATION ACTUALLY PRODUCED` are
    general guidance only one tier is given. Whether they SHOULD be is the
    fork-vs-parameterize ruling, unmade, and no guard can make it. **It is
    placed as `C-108` rather than left as a remark**, because a class named only
    in a docstring is re-derived from scratch by whoever next edits a tier.
    Note the distinction from `_orphan_lines` below, which is deliberately NOT
    this class: an orphan LINE lives inside a block that HAS a counterpart, and
    that is why a guard can reach it at all.
  * **A SUBSEQUENCE that is not an append.** `_one_sided` is exact for what it
    says — every opcode is `equal` or `insert` — and that is slightly broader
    than "one tier's block plus a tail": a block quoting another verbatim inside
    a wrapper also satisfies it. For prose the two coincide almost always, and
    the failure direction is a false POSITIVE (a pair surfaced for a human), not
    a miss.
  * **A SECOND block sharing a 60-byte opening.** `KEY_LEN` is the entry key, so
    two blocks in one child that start identically collapse to one entry, and
    such pairs exist in this corpus today. `_scan` takes the MAX rather than the
    last write, so a drifting block can no longer be MASKED by a namesake — but
    the frozen list still shows one line where two blocks are in play.
  * **A LINE under `MIN_LINE` bytes**, and a line orphaned inside a pair that
    NEITHER block detector surfaced. `_orphan_lines` inherits its population
    from `_drift`, so it can only look inside pairs something else already
    matched — it widens the granularity, never the reach.
  * **WHICH BLOCK IS THE COUNTERPART.** `_partner` takes the highest-ratio
    block, which is a heuristic and not a fact. If a tier moved a bullet into a
    DIFFERENT block, the line reads as orphaned in one and unmatched in the
    other; the failure direction is a false positive handed to a human, which is
    this module's stance everywhere.
  * **Which side is right.** When a pair is genuinely accidental the remedy is
    usually a union, but that is a reading of the two texts, not a computation.
  * **Anything outside the child prompt tree.** Drift between a prompt and the
    standard it quotes is a different problem with no guard at all — and so is
    drift between a child's block and a SHARED fragment, since `_blocks()` skips
    the pool.
  * **DELETION FROM THE POOL, which is the risk PROMOTION CREATES and the one
    this module can never cover.** Measured, not feared: after
    `submit_and_push.md` was promoted, deleting the `RE-CHECK origin/main`
    bullet from the fragment outright left the whole suite green. Every detector
    here fires on DIVERGENCE between two tiers, and removing shared text takes
    it from both at once, so nothing diverges. Promotion trades a drift risk for
    a single-point-of-deletion risk; it is the right trade and it is not free.
    Recorded as an expansion of `C-106`, which owns the pool-fidelity question.
"""
from __future__ import annotations

import difflib
import re
from collections.abc import Sequence
from functools import lru_cache
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
# ALL BUT ONE are frozen as OBSERVED, which is the honest state: the
# fork-vs-parameterize ruling has not been made for them, and a test may not
# make it. The submit-stage entry IS ruled, and its note says so and says by
# whom. Pairs that were ruled and RECONCILED are absent rather than annotated —
# they were promoted, which is what a shrink looks like here.
#
# EVERY NOTE MUST DESCRIBE THE BLOCK IT KEYS, and this sentence is here because
# the submit-stage note once did not. It enumerated a difference that lives at
# `refine.md:3` — a standalone line under MIN_BLOCK, in no block at all — while
# omitting the one difference actually inside the block it was attached to. A
# note is the reader's only evidence that a pair was looked at, so a note
# pointing outside its own block is worse than no note.
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
            "0.992 — the submit stage, and the one entry here that is RULED "
            "rather than observed. The residual delta INSIDE THIS BLOCK is a "
            "single token: the `build-refine:` / `build-refine-minor:` commit "
            "prefix each tier tells the model to use. That is tier identity by "
            "definition and cannot be shared. Everything else the two tiers "
            "once said here — the self-description bullet, the push-time "
            "checks, the PR-URL contract — is now the `submit_and_push` "
            "fragment both consumers render. Its previous note read 'Two-"
            "sided, so not the append class. Unruled.', which was true about "
            "the MECHANISM and hid a pure one-sided content omission for two "
            "review passes: the minor tier was never told to re-check "
            "`origin/main` before pushing, and the identity tokens are what "
            "made the pair read as two-sided so the append detector never "
            "looked. A LATER NOTE THEN CLAIMED the residual was the "
            "rework-vs-scoped-correction line, which is at `refine.md:3`, "
            "below MIN_BLOCK, and in no block at all — a note describing a "
            "difference outside the block it keys. Both are fixed; "
            "`_orphan_lines` keys on the class.",
    },
    "research_write+research_write_minor": {
        "RULES:\n- This is an EVIDENCE workflow: never fabricate, neve":
            "0.94 — the evidence rules. Unruled.",
    },
}


# One granularity down from MIN_BLOCK, and the same value: a line long enough to
# carry an instruction is long enough to be worth a guard.
MIN_LINE = 120

# Below this, a line has no counterpart on the other side. Chosen from a measured
# gap and not tuned — see the docstring's WHY A LINE AND NOT A SENTENCE.
LINE_PAIRED = 0.60

# FROZEN 2026-08-17, same ratchet and same rules as ACCEPTED_DRIFT above: it may
# shrink, and it may not grow without a note saying the difference is deliberate.
# Keyed by `(side, opening of the orphaned line)`.
#
# EMPTY, AND IT DID NOT START THAT WAY. The first version of this detector froze
# one entry here as a deliberate tier difference. It was not one: it was the same
# instruction reworded for its tier, scoring 0.826 once `_pair_score` stopped
# letting `difflib`'s autojunk heuristic decide the answer. An empty baseline is
# the honest state — every line in every surfaced pair has a counterpart — but it
# is ALSO indistinguishable from a detector that reaches nothing, which is why
# `test_the_LINE_detector_IS_LOOKING_AT_SOMETHING` asserts the population rather
# than the verdict.
ACCEPTED_ORPHAN_LINES: dict[str, dict[tuple[str, str], str]] = {
    "build_draft+build_draft_minor": {},
    "build_refine+build_refine_minor": {},
    "research_write+research_write_minor": {},
}


@lru_cache(maxsize=None)
def _blocks(child: str) -> tuple[str, ...]:
    """Every substantive block in one child's prompts, SORTED.

    CACHED, and returning a TUPLE so the cached value cannot be mutated by one
    caller under another. The tree does not change within a run, and this was
    being re-walked for every detector on every pair.

    Sorted because `rglob` order is filesystem-dependent and `_scan` keys its
    result on a 60-byte opening: where two blocks in one child share an opening,
    iteration order would otherwise decide which entry a reader sees, and the
    same tree could report differently on two machines.
    """
    out = []
    for p in ASSISTANT.rglob("prompts/*.md"):
        if p.parent == SHARED or p.parent.parent.name != child:
            continue
        for raw in re.split(r"\n\s*\n", p.read_text()):
            b = raw.strip()
            if len(b) >= MIN_BLOCK:
                out.append(b)
    return tuple(sorted(out))


def _scan(major_blocks: Sequence[str], minor_blocks: Sequence[str],
          score) -> dict[str, float]:
    """Best score per MAJOR block, keyed by its opening.

    Takes BLOCK LISTS rather than child names so a control can drive it with
    synthetic input — against the live tree only the passing path ever runs.
    Both detectors share this body: they differ ONLY in `score`, and having two
    copies of the bookkeeping would reproduce, inside the guard, the very defect
    the guard exists to police.

    `max` ON COLLISION, NOT OVERWRITE. Blocks sharing a 60-byte opening within
    one child already exist in this corpus — measured, not hypothetical — so a
    plain assignment let a drifting block be masked by a non-drifting namesake
    scanned after it. The key stays the opening rather than a hash because the
    frozen list is meant to be READ.
    """
    found: dict[str, float] = {}
    for x in major_blocks:
        best = 0.0
        for y in minor_blocks:
            best = max(best, score(x, y))
        if best:
            key = x[:KEY_LEN]
            found[key] = max(found.get(key, 0.0), best)
    return found


def _ratio_score(x: str, y: str) -> float:
    """How alike, when they are near-but-not-equal.

    `quick_ratio()` is an UPPER BOUND on `ratio()`, so skipping on it can never
    discard a real hit — it is the only prefilter that is safe here. The obvious
    alternative, skipping on a length difference, is not: two blocks differing
    30% in length can still score 0.82.
    """
    m = difflib.SequenceMatcher(None, x, y)
    if m.quick_ratio() <= NEAR:
        return 0.0
    r = m.ratio()
    return r if NEAR < r < 1.0 else 0.0


def _one_sided(small: str, big: str) -> bool:
    """True when `big` is `small` with text INSERTED — nothing replaced or deleted.

    Split out as a pure function so the control below can drive it with
    synthetic input. The live tree holds one member of this class, so the real
    corpus can only ever exercise the passing path.
    """
    return all(tag in ("equal", "insert")
               for tag, *_ in difflib.SequenceMatcher(None, small, big).get_opcodes())


def _append_score(x: str, y: str) -> float:
    """Non-zero when one block is the other plus an append, at ANY ratio.

    The second detector, and it needs no threshold: a ratio answers "how alike",
    which is the wrong question for a class defined by "identical, plus more".
    Runs beside `_ratio_score` rather than replacing it — the ratio still owns
    two-sided edits, where no subset relation holds in either direction.

    The length comparison is a free prefilter, not an optimisation of taste: an
    insertion cannot SHRINK a string, so `_one_sided(x, y)` is impossible when
    `y` is shorter and the `get_opcodes()` call in that direction is wasted.
    """
    if x == y:
        return 0.0                # identical is the verbatim guard's population
    ordered = (x, y) if len(y) >= len(x) else (y, x)
    if not _one_sided(*ordered):
        return 0.0
    return difflib.SequenceMatcher(None, x, y).ratio()


@lru_cache(maxsize=None)
def _drifted(major: str, minor: str) -> dict[str, float]:
    """Openings of the MAJOR tier's blocks that a minor-tier block nearly matches."""
    return _scan(_blocks(major), _blocks(minor), _ratio_score)


@lru_cache(maxsize=None)
def _appended(major: str, minor: str) -> dict[str, float]:
    """Openings of MAJOR blocks that are one tier's text plus an APPEND."""
    return _scan(_blocks(major), _blocks(minor), _append_score)


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


def _lines(block: str) -> list[str]:
    """The substantive lines of a block, stripped."""
    return [ln.strip() for ln in block.split("\n") if len(ln.strip()) >= MIN_LINE]


# The line pair that was frozen here as a deliberate orphan and was nothing of
# the kind. QUOTED FROM THE TREE AS IT STOOD, and deliberately a copy rather
# than a live read: it is a regression fixture for a scorer defect, so it must
# keep demonstrating that defect even after the prompts it came from are edited.
# The asymmetry needs the specific length difference (327 vs 252) — a synthetic
# pair of similar lengths scores identically both ways and proves nothing, which
# is how the first attempt at this control passed while asserting nothing.
_AUTOJUNK_REGRESSION_PAIR = (
    "- **Before your final commit, confirm each artifact is at its contract "
    "path and nowhere else** — `${RESEARCH_DIR}/topics.md`, "
    "`${RESEARCH_DIR}/raw/*.md`, `${RESEARCH_DIR}/synthesis.md`. `ls` them. A "
    "consumer reads the synthesis by path; one written elsewhere is invisible "
    "to everything downstream while the run reports success.",
    "- **Before your final commit, confirm the paper is at its contract path "
    "and nowhere else** — `${RESEARCH_DIR}/raw/<topic>.md`. `ls` it. A consumer "
    "reads by path; one written elsewhere is invisible to everything "
    "downstream while the run reports success.",
)


def _pair_score(a: str, b: str) -> float:
    """How alike two LINES are — symmetric, and with `autojunk` off.

    BOTH OF THOSE ARE CORRECTIONS OF A MEASURED DEFECT, not preferences.
    `difflib` builds its popular-element set from the SECOND argument only, and
    that heuristic engages once that argument reaches 200 elements. Every
    substantive line in this corpus is longer than that, so nearly every
    character became "junk" and was excluded from matching — and because the set
    comes from one side, the score DEPENDED ON ARGUMENT ORDER.

    Measured on the one line pair this detector originally froze: 0.366 read one
    way and 0.701 read the other, against 0.826 and 0.822 with the heuristic
    off. It is the same instruction reworded for its tier, it plainly has a
    counterpart, and the default scoring called it an orphan from one side only.
    The frozen baseline recorded that artifact as a DELIBERATE tier difference,
    which is this module's own worst failure shape — a defect simultaneously
    recorded and invisible — and the floor below was then calibrated on the gap
    between two readings of a single pair rather than on a real population.

    `autojunk` exists to keep `ratio()` fast on long machine-generated input.
    These are hand-written prose lines and there are a few hundred of them, so
    the speed it buys is worth less than the correctness it costs.
    """
    return max(difflib.SequenceMatcher(None, a, b, autojunk=False).ratio(),
               difflib.SequenceMatcher(None, b, a, autojunk=False).ratio())


def _partner(x: str, candidates: Sequence[str]) -> str:
    """The block most like `x`, which is a HEURISTIC and named as one.

    Returns `""` for an empty candidate list, which the caller MUST treat as
    "no comparison possible": scoring every line of `x` against nothing would
    report the entire block as orphaned.
    """
    best, chosen = -1.0, ""
    for y in candidates:
        r = _pair_score(x, y)
        if r > best:
            best, chosen = r, y
    return chosen


def _lines_without_counterpart(x: str, y: str) -> dict[str, float]:
    """Lines of `x` that nothing in `y` resembles, keyed by opening.

    A pure function over two blocks so the controls can drive it synthetically.
    ONE DIRECTION ONLY — the caller runs it both ways, because an instruction
    present only in the MINOR tier is exactly as much a divergence as one
    present only in the major, and a detector that looked only downhill would
    have a blind side no note records.

    `min` ON COLLISION, WHICH IS `_scan`'S `max` AND NOT ITS OPPOSITE. Both keep
    the most suspicious member of a collided key; the two detectors just measure
    suspicion in opposite directions. For a near-duplicate the alarming value is
    HIGH (more alike than it should be), for an orphan it is LOW (nothing like
    it on the other side). Harmonising these two to the same builtin for
    consistency would silently reintroduce the masking each exists to prevent.
    """
    out: dict[str, float] = {}
    other = _lines(y)
    for a in _lines(x):
        best = max((_pair_score(a, b) for b in other), default=0.0)
        if best < LINE_PAIRED:
            key = a[:KEY_LEN]
            out[key] = min(out.get(key, 1.0), best)
    return out


def _orphan_core(major_blocks: Sequence[str], minor_blocks: Sequence[str],
                 surfaced: set[str]) -> dict[tuple[str, str], float]:
    """Orphaned lines inside blocks the caller has already surfaced.

    TAKES BLOCK LISTS, NOT CHILD NAMES, for the reason `_scan` does: against the
    live tree only the passing path ever runs, so every piece of bookkeeping in
    here — the both-directions loop, the collision rule, the side label — would
    otherwise be exercised by nothing a control can reach.

    DRIVEN FROM BLOCKS RATHER THAN FROM OPENINGS, which is not a refactor. The
    first version walked the surfaced KEYS and recovered a block with
    `next(b for b in mb if b.startswith(opening))` — so where two blocks in one
    child share a 60-byte opening, it inspected whichever sorted first and the
    other was invisible. `_scan`'s own comment records that those collisions are
    live in this corpus, and it takes the `max` across them for exactly this
    reason. Filtering blocks BY key inspects every namesake and deletes the
    recovery step rather than fixing it.

    KEYED ON `(side, opening)`. Keying on the opening alone let a frozen
    minor-only entry silently forgive a later major-only orphan that happened to
    start with the same 60 bytes — one baseline line standing for two facts,
    only one of which anybody looked at.
    """
    found: dict[tuple[str, str], float] = {}
    for x in major_blocks:
        if x[:KEY_LEN] not in surfaced:
            continue
        y = _partner(x, minor_blocks)
        if not y:
            continue
        for side, (p, q) in (("major-only", (x, y)), ("minor-only", (y, x))):
            for key, score in _lines_without_counterpart(p, q).items():
                k = (side, key)
                found[k] = min(found.get(k, 1.0), score)
    return found


def _orphan_lines(major: str, minor: str) -> dict[tuple[str, str], float]:
    """`_orphan_core` against the live tree, over the pairs `_drift` surfaced.

    The population is `_drift`'s, deliberately: this detector widens the
    GRANULARITY of what is inspected, never the reach. A block with no
    counterpart at all is a different class, placed as `C-108` rather than
    guarded here, because there is nothing to compare it against.
    """
    return _orphan_core(_blocks(major), _blocks(minor),
                        set(_drift(major, minor)))


def test_the_LINE_detector_SEES_WHAT_THE_BLOCK_DETECTORS_CANNOT() -> None:
    """The control for the class this module was extended for.

    THE FIXTURE IS THE REAL DEFECT'S SHAPE, not a convenient one. The live
    `## Stage 5: SUBMIT` pair carried a whole missing bullet for two review
    passes while every assertion here stayed green, and the mechanism was
    precise: two TIER-IDENTITY replacements made the pair read as two-sided, so
    `_append_score` — whose entire claim is that it needs no threshold — was
    routed away, and `_ratio_score` reported only that a pair existed. So the
    fixture must reproduce all three properties at once, and each is asserted
    rather than described.
    """
    # The shared bulk is sized so the pair lands ABOVE `NEAR`, because that is
    # where the real one sat: a block big enough that one missing bullet barely
    # moves the ratio is exactly the block whose missing bullet nobody sees.
    shared = "\n".join(
        f"- Bullet {n} of real operational guidance, stated at the length these "
        f"prompts actually run to, so the comparison is honest rather than "
        f"convenient and the ratio means what it means in the live corpus."
        for n in ("one", "two", "three", "four")
    )
    identity = "- This is the {} tier, which is the difference that is intended."
    orphan = ("- **RE-CHECK the upstream branch NOW, immediately before "
              "pushing** — a finding true when written can be false two hours "
              "later, and an id allocated from a stale read merges silently.")
    major = "\n".join([shared, identity.format("MAJOR"), orphan])
    minor = "\n".join([shared, identity.format("MINOR")])

    ratio = difflib.SequenceMatcher(None, major, minor).ratio()
    assert ratio > NEAR, (
        f"the fixture scores {ratio:.3f}, at or below the {NEAR} floor — the "
        f"defect it stands for hid ABOVE the floor, inside an ACCEPTED pair, "
        f"and a sub-floor fixture would be testing a different story"
    )

    assert _scan([major], [minor], _ratio_score), (
        "the fixture does not even register as a near-duplicate PAIR — it is "
        "not the shape that hid the defect"
    )
    assert _scan([major], [minor], _append_score) == {}, (
        "the fixture is one-sided, so the APPEND detector would have caught it "
        "on its own and the fixture proves nothing about the line detector"
    )
    orphans = _lines_without_counterpart(major, minor)
    assert orphans, (
        "the LINE detector cannot see a whole bullet present in one tier and "
        "absent from the other, inside a block pair both block detectors "
        "already match — which is the entire reason it exists"
    )
    assert any(k.startswith("- **RE-CHECK") for k in orphans), (
        f"the wrong line was reported as orphaned: {sorted(orphans)}"
    )


def test_the_COMPOSED_line_detector_reports_BOTH_directions_and_all_namesakes()\
        -> None:
    """Control for `_orphan_core`'s bookkeeping, which the live tree cannot reach.

    The live baseline is EMPTY, so every assertion keyed on the tree exercises
    the passing path only — and the three things this function does beyond
    `_lines_without_counterpart` are precisely the things a regression would
    delete silently: it runs both directions, it labels which side, and it
    inspects EVERY block sharing a surfaced 60-byte opening rather than the
    first. Each gets an assertion here.
    """
    common = ("The very same sixty byte opening shared by two different blocks, "
              "which is a real shape in this corpus and the reason `_scan` takes "
              "a max across namesakes rather than the last one it happened to see.")
    first_orphan = ("- Alpha bullet: guidance carried by one tier and nothing "
                    "whatever resembling it anywhere on the other side, which "
                    "is what makes it an orphan rather than a reword of it.")
    second_orphan = ("- Beta clause: entirely separate wording, sharing no "
                     "phrasing with any other line in this fixture, placed in "
                     "the SECOND block that shares the opening above.")
    minor_orphan = ("- Gamma note: text held by the counterpart block alone, "
                    "unlike everything else here, so it is orphaned in the "
                    "opposite direction from the two above.")
    first = common + "\n" + first_orphan
    second = common + " A second block, same opening.\n" + second_orphan
    partner = common + "\n" + minor_orphan

    found = _orphan_core([first, second], [partner], {common[:KEY_LEN]})
    sides = {side for side, _ in found}
    assert sides == {"major-only", "minor-only"}, (
        f"the composed detector reported only {sides or 'nothing'} — it must "
        f"run BOTH directions, or an instruction the minor tier alone carries "
        f"is invisible"
    )
    assert ("major-only", first_orphan[:KEY_LEN]) in found, (
        "the orphan in the FIRST namesake block was not reported"
    )
    assert ("major-only", second_orphan[:KEY_LEN]) in found, (
        "the orphan in the SECOND namesake block was not reported — the "
        "detector is inspecting one block per surfaced opening, which is the "
        "masking `_scan` takes a max to avoid"
    )
    assert ("minor-only", minor_orphan[:KEY_LEN]) in found, (
        "the counterpart block's own orphan was not reported"
    )
    assert _orphan_core([first, second], [], {common[:KEY_LEN]}) == {}, (
        "with no candidate blocks there is no comparison to make, and every "
        "line must NOT be reported as orphaned against nothing"
    )
    assert _orphan_core([first], [partner], set()) == {}, (
        "a block the BLOCK detectors never surfaced must not be inspected — "
        "this detector widens granularity, never reach"
    )


def test_the_LINE_detector_does_NOT_fire_on_a_tier_appropriate_REWORD() -> None:
    """The other half, and without it `LINE_PAIRED` could be set to 1.0.

    A detector that reported every non-identical line would be a second copy of
    the ratio detector with the threshold removed, and its frozen list would
    grow until nobody read it. A line REWORDED for its tier still has a
    counterpart; only a line with nothing on the other side is an orphan.

    THE FIXTURE IS THE REAL PAIR THIS DETECTOR ORIGINALLY GOT WRONG, and it is
    the same one `_AUTOJUNK_REGRESSION_PAIR` holds rather than a second copy of
    it. An earlier version froze this pair as a deliberate orphan; it is nothing
    of the kind. Its length is asserted below because that is what made it a
    defect: a fixture UNDER `difflib`'s 200-element autojunk threshold sits in a
    different scoring regime from every line in the live corpus, so a short
    fixture would have certified a floor that the real population disproves.
    """
    major, minor = _AUTOJUNK_REGRESSION_PAIR
    assert min(len(major), len(minor)) > 200, (
        "the fixture is below difflib's autojunk threshold, so it exercises a "
        "scoring regime no line in the live corpus is in — which is exactly "
        "how the floor was mis-calibrated the first time"
    )
    assert _lines_without_counterpart(major, minor) == {}, (
        "a tier-appropriate rewording of the SAME instruction is being reported "
        "as an orphan — the floor is too high and the frozen list will grow "
        "until it is an excuse list"
    )
    assert _lines_without_counterpart(minor, major) == {}, "and in both directions"


def test_the_LINE_score_does_not_depend_on_ARGUMENT_ORDER() -> None:
    """The defect `_pair_score` was written to fix, pinned so it cannot return.

    `difflib`'s autojunk heuristic derives its popular-element set from the
    SECOND argument only, so with it enabled the score of a long pair differs by
    which way round it is read. That is how a line with a perfectly good
    counterpart was frozen here as a deliberate orphan. This asserts the defect
    is real (so the control is not vacuous) and that `_pair_score` is immune.
    """
    a, b = _AUTOJUNK_REGRESSION_PAIR
    assert min(len(a), len(b)) > 200, "below the threshold the defect cannot occur"

    naive_ab = difflib.SequenceMatcher(None, a, b).ratio()
    naive_ba = difflib.SequenceMatcher(None, b, a).ratio()
    assert abs(naive_ab - naive_ba) > 0.05, (
        f"the default scoring is symmetric on this fixture ({naive_ab:.3f} vs "
        f"{naive_ba:.3f}) — the fixture no longer demonstrates the defect and "
        f"_pair_score's docstring is asserting something untested"
    )
    assert _pair_score(a, b) == _pair_score(b, a), (
        "_pair_score is not symmetric — the score of a line pair still depends "
        "on which tier the caller happened to pass first"
    )
    assert _pair_score(a, b) > LINE_PAIRED, (
        "the same instruction reworded for its tier scores below the floor — "
        "this is the false-orphan that got frozen as deliberate"
    )


def test_the_LINE_detector_IS_LOOKING_AT_SOMETHING() -> None:
    """Vacuity floor, and the reason it asserts the POPULATION not the verdict.

    `ACCEPTED_ORPHAN_LINES` is empty, which is the honest end state — and it
    means every live assertion in the two tests below passes over empty output.
    A `MIN_LINE` bump, a `_partner` regression or a `difflib` change could make
    this detector reach nothing at all and the suite would stay green, because
    "no orphans found" and "nothing was inspected" produce identical results.
    An earlier draft was protected only by the single baseline entry going
    stale — that is, by the one thing the ratchet next door exists to remove.
    """
    total = 0
    for major, minor in TIER_PAIRS:
        surfaced = set(_drift(major, minor))
        assert surfaced, (
            f"{major}+{minor}: the BLOCK detectors surfaced no pair, so the "
            f"line detector inherits an empty population and asserts nothing"
        )
        inspected = [x for x in _blocks(major) if x[:KEY_LEN] in surfaced]
        assert inspected, (
            f"{major}+{minor}: no block matches a surfaced opening — the key "
            f"and the block list have come apart"
        )
        lines = sum(len(_lines(b)) for b in inspected)
        assert lines >= 1, (
            f"{major}+{minor}: the surfaced blocks yield NO line over "
            f"{MIN_LINE} bytes, so this pair contributes nothing to the "
            f"comparison and an empty result means only that it looked at "
            f"nothing"
        )
        total += lines
    # PER-PAIR THE FLOOR CAN ONLY BE 1, because most tier pairs really do surface
    # a single-line block today — so a per-pair floor cannot tell a healthy
    # corpus from a collapsed one. The CORPUS total can: a regression that
    # quietly cut the population by most of itself would still clear every
    # per-pair check above.
    assert total >= 5, (
        f"the line detector inspects {total} lines across the whole corpus, "
        f"below the floor it was built against. Something upstream — MIN_LINE, "
        f"_partner, the block split — has collapsed its population, and an "
        f"empty orphan list now means 'looked at almost nothing' rather than "
        f"'found nothing'"
    )


def test_no_NEW_orphan_line_appears_inside_a_matched_block_pair() -> None:
    new: list[str] = []
    for major, minor in TIER_PAIRS:
        frozen = ACCEPTED_ORPHAN_LINES[f"{major}+{minor}"]
        for (side, key), score in sorted(_orphan_lines(major, minor).items()):
            if (side, key) not in frozen:
                new.append(f"{major} vs {minor}  [{side}]  ({score:.2f})  {key!r}")
    assert not new, (
        "a whole LINE exists on one side of a block pair the two tiers "
        "otherwise share, and has no counterpart on the other. This is the "
        "shape that hid a missing push-time instruction behind a frozen entry "
        "recorded as looked-at for two review passes — the block was accepted "
        "while a bullet inside it was missing:\n  "
        + "\n  ".join(new)
        + "\n\nTWO WAYS TO CLOSE THIS, and the second is a real option:\n"
          "  1. The omission is an accident — copy the line into the sibling "
          "VERBATIM. Check afterwards whether the block became identical; if "
          "it did, test_no_NEW_block_is_copied_between_children will tell you "
          "to promote it.\n"
          "  2. The difference is DELIBERATE — add the opening to "
          "ACCEPTED_ORPHAN_LINES with a note saying which tier is meant to "
          "carry it and why. This test does not rule on that; it requires that "
          "somebody did."
    )


def test_a_RECONCILED_orphan_line_is_removed_from_the_frozen_list() -> None:
    """The ratchet, matching the one `ACCEPTED_DRIFT` runs."""
    stale: list[str] = []
    for major, minor in TIER_PAIRS:
        key = f"{major}+{minor}"
        stale += _stale(ACCEPTED_ORPHAN_LINES[key], _orphan_lines(major, minor), key)
    assert not stale, (
        "these frozen entries no longer describe an orphaned line — it was "
        "reconciled, deleted, or reworded. Remove the line so the list keeps "
        "shrinking:\n  " + "\n  ".join(stale)
    )


def test_TIER_PAIRS_NAMES_EVERY_MINOR_SIBLING_THAT_HAS_PROMPTS() -> None:
    """The population itself is declared by hand, so something must check it.

    Every other vacuity guard here protects the frozen lists against the pair
    list. Nothing protected the PAIR LIST against the tree: a `_minor` child
    added tomorrow with its own `prompts/` would be watched by nothing, and
    every assertion in this module would stay green because it was never asked
    about it. That is the same shape as a frozen note whose classification no
    longer matches its content — recorded as complete, and silently not.

    `_minor` children with no `prompts/` directory are correctly absent: they
    are workflow modules that reuse another child's prompts, so there is no
    second copy of anything to drift.
    """
    minors = {p.parent.parent.name for p in ASSISTANT.rglob("prompts/*.md")
              if p.parent != SHARED and p.parent.parent.name.endswith("_minor")}
    named = {minor for _, minor in TIER_PAIRS}
    assert minors == named, (
        f"the tree has minor-tier prompt children this module does not watch, "
        f"or names ones that no longer exist. Unwatched: {sorted(minors - named)}; "
        f"named but absent: {sorted(named - minors)}. Add the pair to TIER_PAIRS "
        f"and give it an entry in BOTH frozen dicts."
    )
    for major, minor in TIER_PAIRS:
        assert minor == f"{major}_minor", (
            f"TIER_PAIRS names {major!r}/{minor!r}, which are not a tier pair "
            f"by name — the two frozen lists would be keyed on a relationship "
            f"that does not exist"
        )


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


def test_the_APPEND_detector_SEES_WHAT_THE_RATIO_CANNOT() -> None:
    """The claim this module was rewritten for, exercised rather than narrated.

    THE LIVE CORPUS CANNOT SHOW THIS AND THAT IS THE POINT. Every sub-floor pair
    that motivated `_appended` was reconciled and promoted in the same change, so
    the only survivor scores 0.91 — which `_ratio_score` finds on its own. A
    regression that broke `_appended`'s sub-floor reach specifically would leave
    every live assertion green. So the two detectors are driven through `_scan`
    against a synthetic pair sitting BELOW `NEAR`, and the ratio detector is
    required to miss it.
    """
    base = ("A rule with a reason attached, stated at the length a real block of "
            "guidance in this corpus actually runs to, so the comparison is fair.")
    appended = base + (" **Measured:** " + "and here is a long evidence sentence "
                       "that landed in exactly one tier and nowhere else. " * 3)
    ratio = difflib.SequenceMatcher(None, base, appended).ratio()
    assert ratio < NEAR, (
        f"the fixture scores {ratio:.3f}, at or above the {NEAR} floor — it no "
        f"longer represents the sub-floor class and proves nothing"
    )
    assert _scan([base], [appended], _ratio_score) == {}, (
        "the RATIO detector claims to find a pair below its own floor"
    )
    assert _scan([base], [appended], _append_score), (
        "the APPEND detector cannot see a one-sided drift below the ratio floor "
        "— which is the entire reason it exists"
    )


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


def test_a_FROZEN_NOTES_RATIO_still_matches_what_the_detectors_MEASURE() -> None:
    """A note may not state a score the tree no longer supports.

    THE RATCHET NEXT DOOR KEYS ON PRESENCE, NOT ON VALUE, and that is the hole
    this closes. `test_no_NEW_drift…` asks only whether an opening is in the
    frozen dict, so a pair may drift from near-identical to barely-alike, keep
    its opening, and stay green under a note quoting the score it used to have.
    That is this module's own thesis — a baseline entry recorded as looked-at
    while its content moved underneath — applied to the baseline itself.

    Compared at the PRECISION THE NOTE STATES, so a note is free to say 0.86 or
    0.992 and is held to exactly what it claimed. `test_promotion_guard_prose_
    figures_are_DERIVED` cannot reach these: its predicate deliberately skips
    the tail of a decimal, so every ratio in this file is invisible to it.
    """
    wrong: list[str] = []
    for major, minor in TIER_PAIRS:
        live = _drift(major, minor)
        for opening, note in ACCEPTED_DRIFT[f"{major}+{minor}"].items():
            m = re.match(r"(\d\.(\d+))", note)
            assert m, (
                f"{major}+{minor}: the note for {opening!r} does not open with "
                f"its measured ratio, which every other note here does and "
                f"which is the only thing making the figure checkable"
            )
            if opening not in live:
                # The pair was reconciled — the DESIGNED outcome, and the
                # ratchet next door owns it with a message that says what to do.
                # Indexing here instead would raise a bare KeyError alongside
                # that message, on this module's most common failure path.
                continue
            claimed, places = m.group(1), len(m.group(2))
            actual = f"{round(live[opening], places):.{places}f}"
            if claimed != actual:
                wrong.append(f"{major}+{minor}  {opening!r}: note says "
                             f"{claimed}, detectors say {actual}")
    assert not wrong, (
        "a frozen note quotes a ratio the tree no longer produces. The pair "
        "moved while the note stood still — re-measure and correct the figure, "
        "and check whether what moved also changed what the note CLAIMS:\n  "
        + "\n  ".join(wrong)
    )


def _stale(frozen, live, label: str) -> list[str]:
    """Frozen entries the detectors no longer produce.

    A pure function shared by BOTH ratchets, for the reason `_scan` is shared by
    both block detectors: two copies of a ratchet drift apart, and against the
    live tree only the passing path of either ever runs. Driven synthetically by
    `test_the_RATCHET_fires_when_a_frozen_entry_goes_stale`, so the failing path
    is one somebody has seen work.
    """
    return [f"{label}  {entry!r}" for entry in sorted(frozen) if entry not in live]


def test_the_RATCHET_fires_when_a_frozen_entry_goes_stale() -> None:
    """Control for `_stale`. Both live callers can only ever pass."""
    assert _stale({"a": "note"}, {"a": 0.9}, "pair") == [], (
        "an entry the detectors still produce must stay green"
    )
    gone = _stale({"a": "note", "b": "note"}, {"a": 0.9}, "pair")
    assert gone == ["pair  'b'"], f"the ratchet missed a stale entry: {gone}"
    assert _stale({}, {"a": 0.9}, "pair") == [], (
        "a live pair that is NOT frozen is the other test's business, not this "
        "one's — reporting it here would make both fire on one fact"
    )


def test_a_RECONCILED_drift_is_removed_from_the_frozen_list() -> None:
    """The ratchet. Without it the list is an excuse list, exactly as next door."""
    stale: list[str] = []
    for major, minor in TIER_PAIRS:
        key = f"{major}+{minor}"
        stale += _stale(ACCEPTED_DRIFT[key], _drift(major, minor), key)
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
    assert set(ACCEPTED_ORPHAN_LINES) == {f"{a}+{b}" for a, b in TIER_PAIRS}, (
        "the line-orphan baseline is keyed on a different set of pairs than the "
        "block baseline — a pair missing from it would KeyError rather than "
        "assert, and one present in it alone would be silently unreachable"
    )
    for major, minor in TIER_PAIRS:
        for child in (major, minor):
            assert len(_blocks(child)) > 5, (
                f"{child} yielded {len(_blocks(child))} blocks over {MIN_BLOCK} "
                f"bytes — the child name is wrong or its prompts moved, and this "
                f"module is comparing nothing against nothing."
            )

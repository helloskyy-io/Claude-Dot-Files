"""A prompt block copied into two children must be SHARED, not duplicated.

THE RULE THIS ENFORCES ALREADY EXISTS. §10.1: *promoted iff >1 consumer —
consumer count decides, never taste.* It was written for code and never applied
to prose, so the prompt corpus accumulated 61 duplicated blocks carrying 25,270
bytes of copy. Nothing was watching, because a copy and an original are the same
file type.

WHAT IT COST, MEASURED. `stages_1_to_4.md` and its `_from_plan` sibling forked:
the normal one accumulated eleven testing rules and the plan variant received
none of them. Every PMP phase builds from a plan, so the whole component ran
without the rule that tells a run how much rigour a change warrants. Nobody chose
that — the copy simply stopped being updated, and no reader could tell.

WHY A FROZEN BASELINE AND NOT A CLEAN FAIL. 61 blocks cannot be promoted in one
change, and a test that is red on arrival gets skipped rather than fixed. So the
existing duplication is frozen below and the ratchet runs BOTH ways:

  * a block duplicated but NOT in the baseline  -> fail. No new copying.
  * a baseline entry NO LONGER duplicated       -> fail. Delete the line.

The second is what makes the list shrink instead of becoming a permanent excuse
list. Fixing a duplication forces its row out, and the row cannot come back.

AND IT SHRANK TO NOTHING: 48 -> 13 in one change, and 13 -> 0 in the next. The
first pass took the three largest consumer-sets. The second ruled on what was
left and promoted all of it, so `ACCEPTED` below is empty and the guard is now a
clean assertion that no prompt block is copied between children at all.

AN EMPTY BASELINE IS STRICTLY STRONGER AND ALSO QUIETER, and the second half
cost this module its last live exercise. `test_a_baselined_block_does_not_
SPREAD_to_another_child` and `test_a_FIXED_duplication_is_removed_from_the_
baseline` both iterate `ACCEPTED` and are VACUOUS while it is empty, and
`test_no_NEW_block_is_copied_between_children` passes on an empty result — so
while the baseline had rows, `_duplicated()` had to keep FINDING them or the
stale check fired, and emptying it removed the only thing standing between a
silently-broken detector and a permanently green module.

MEASURED, NOT REASONED: replacing `_duplicated()`'s body with `return {}` gave
**1646 passed, 0 failed**. A changed rglob pattern, a raised `MIN_BLOCK` or a
different block split does the same thing without anyone editing a test.

SO EVERY PREDICATE HERE IS DRIVEN SYNTHETICALLY AS WELL AS OVER THE TREE:
`_blocks` by `test_the_DUPLICATION_DETECTOR_fires_on_a_block_TWO_CHILDREN_share`,
`_spread` by `test_the_SPREAD_check_fires_when_a_block_gains_a_consumer`,
`_stale` by `test_the_STALE_check_fires_when_a_baseline_row_is_FIXED`, and the
walk itself by `test_the_walk_actually_READS_the_prompt_corpus`, which is the
floor that catches the detector going blind rather than going wrong.

WHY THE REMAINDER WAS PROMOTED RATHER THAN LEFT AS A JUDGEMENT NOBODY MADE. The
note here used to say the cross-family sets were "deliberately still here", on
the reasoning that promoting them would couple runs with no reason to be
coupled. The standard this guard enforces says the opposite in as many words —
*"The shared pool sits above ALL families, so a fragment may be shared by a
build child and a research child — family boundaries do not enter into it"* —
and the standard is the thing under version control that a later reader checks
against. The ruling was made by category of guidance rather than by pair,
because a blind trial found per-pair ruling was not reproducible here; the
procedure, the trial and the rulings are in `fork_vs_parameterize.py` and
`FAMILY_RULINGS` below.

HOW TO FIX ONE, rather than adding to the baseline: move the block to
`modules/assistant/prompts/<name>.md`, put a placeholder where it used to be in
each child, and pass `"NAME": act.shared_prompt("<name>")` in each workflow's
values dict. `prompts/mutation_discipline.md` is the worked example.

WHAT THIS DOES NOT LOOK AT, so the guard is not over-read:

  * **NEAR-duplicates are invisible to it.** Blocks are matched verbatim, so a
    copy that has already drifted by a single word does not register — and a
    drifted copy is the more dangerous kind, because it reads as intent.
    `test_tier_siblings_do_not_DRIFT_by_a_sentence` is the complement and owns
    that half. This list used to name three same-named prompts "at 85.8%, 76.1%
    and 62.1%"; two of those three figures were falsified by the promotions in
    the very PR that wrote them, which is why the similarities are no longer
    restated here.
  * It cannot say whether a block SHOULD be shared. A child doing a genuinely
    different job may legitimately repeat a sentence. This reports duplication;
    a human rules on it.
  * It sees only the child prompt tree. Duplication between a prompt and a
    docstring, or a prompt and a standard, is out of scope.
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

import fork_vs_parameterize as fvp

ASSISTANT = Path(__file__).resolve().parents[2] / "modules" / "assistant"
SHARED = ASSISTANT / "prompts"

# Below this, a repeated line is boilerplate rather than duplicated substance.
# Chosen from the measurement: 120 captures 25,270 bytes across 61 blocks, while
# dropping to 60 adds only noise-sized fragments.
MIN_BLOCK = 120

# FROZEN 2026-08-16, EMPTIED 2026-08-19. hash -> how many children carry it, and
# its opening words. THIS LIST MAY SHRINK. IT MAY NEVER GROW. It is empty because
# every row was disposed rather than because nothing was ever forgiven — the
# rulings are `FAMILY_RULINGS` below, and the shape of an entry is preserved here
# because `_spread` still parses it and its control still drives it.
#
# THE LEADING `Nx` IS AN ASSERTION, NOT A NOTE — see
# `test_a_baselined_block_does_not_SPREAD_to_another_child`. It was decoration
# until PR #100's correction pass mutated the guard and found that copying an
# ALREADY-BASELINED block into a THIRD child produced 1282 passed and zero
# failures: the baseline froze WHICH blocks are duplicated and never HOW WIDELY,
# so a duplication could keep spreading through the exact blocks the list had
# already forgiven. The same pass had just regenerated these counts (one moved
# 5x -> 4x), which is what made leaving them unchecked the worse option — a
# freshly-rewritten number reads as live data.

ACCEPTED: dict[str, str] = {}


# --- the rulings that emptied it ---------------------------------------------
#
# ONE RULING PER FAMILY OF GUIDANCE, NOT ONE PER PAIR, and that granularity is a
# MEASURED outcome rather than a convenience. The blind trial recorded in
# `docs/development/workflow-decomposition/fork_vs_parameterize_blind_trial.md`
# put two shell-less raters on seven drifted pairs, sealed their calls in a
# commit before any history was read, and scored them against a co-evolution
# audit. Inter-rater kappa came out at 0.000 — at or below the field's 0.271
# benchmark — so ruling moved from per-pair to per-family, which is exactly the
# outcome the phase's requirement 3 was written to permit rather than to avoid.
#
# EVERY VALUE IS CHECKED, not decorative: `test_every_FAMILY_RULING_is_well_
# formed` runs each through `fork_vs_parameterize.ruling_defects`, which demands
# a verdict, a named deciding signal, a category from the `_minor` tier contract,
# and NO similarity magnitude anywhere in the reasoning.
FAMILY_RULINGS: dict[str, tuple[tuple[str, ...], str]] = {
    "stage-ordering": (
        ("stage_order_is_mandatory", "stage_order_skipped_marker"),
        "PROMOTE S2 stage-ordering — every consumer is a staged run whose stages "
        "must not be reordered or silently skipped. The two sites are alike on "
        "the only dimension the text addresses, so a divergence here would mean "
        "one child had quietly stopped being told stages are ordered. How MANY "
        "stages a child has is tier-scoped and is not what these blocks say.",
    ),
    "operational-safety": (
        ("gitignore_collision_check", "research_stage_1_verify_and_discover",
         "worktree_is_compared_to_a_snapshot"),
        "PROMOTE S2 operational-safety — what a run may do to the tree, and the "
        "checks that catch it having done the wrong thing. A cheaper or "
        "differently-jobbed run is not a run permitted to be less careful, so "
        "SC3 does not reach these even where the two children's jobs differ: "
        "the referent is the WORKTREE, which both hold identically.",
    ),
    "evidence-discipline": (
        ("verify_the_tasks_asserted_facts", "verification_is_by_fetch"),
        "PROMOTE S2 evidence-discipline — how a claim is established before it "
        "is written down. Scope changes what a run examines; it never changes "
        "what counts as having examined it. Left duplicated, these are the exact "
        "shape that forked before: general discipline landing in one consumer "
        "and not its sibling, with a reader unable to tell.",
    ),
    "finding-disposition": (
        ("resolve_apply_the_remedy_you_wrote", "resolve_rejecting_is_legitimate",
         "resolve_your_own_dispositions_too"),
        "PROMOTE S2 finding-disposition — the rules for what may be done with a "
        "finding once it exists. This category was already treated as invariant "
        "when the resolve_* fragments were promoted, and these three were the "
        "remainder, frozen with two consumers each so a third tier could not "
        "take them without tripping the spread check. Reconciled into "
        "build_refine_minor in the same change, per C-110's own reading.",
    ),
    "orchestration-mechanics": (
        ("orchestrator_executes_agents_read",),
        "PROMOTE S2 orchestration-mechanics — who executes and who reads. True "
        "of a run dispatching one agent and of a run dispatching five, so it "
        "renders in both refine tiers; the ROSTER is a different category and is "
        "ruled separately below.",
    ),
    "review-depth": (
        ("tell_each_agent_what_it_can_run", "agents_have_no_shell"),
        "PROMOTE S3 review-depth — promoted because both consumers dispatch the "
        "same multi-agent roster, and TIER-SCOPED because the text enumerates "
        "that roster. The pair is one instruction split across two blocks (the "
        "first ends 'in these two parts:'), so they are ruled together and move "
        "together. build_refine_minor dispatches one agent and is deliberately "
        "NOT a consumer — recorded in test_promoted_fragments_render_for_every_"
        "consumer, which asks for exactly this ruling to be made there.",
    ),
}


def _owner(p: Path) -> str:
    """The child workflow a prompt belongs to."""
    return p.parent.parent.name


def _corpus() -> list[tuple[str, str]]:
    """Every child prompt file as `(owning child, text)`. The pool is not one."""
    return [(_owner(p), p.read_text())
            for p in ASSISTANT.rglob("prompts/*.md") if p.parent != SHARED]


def _blocks(corpus: Sequence[tuple[str, str]]) -> dict[str, tuple[str, set[str]]]:
    """Verbatim blocks appearing in more than one owner, keyed by content hash.

    Split from the walk so a control can drive it on a synthetic corpus. It is
    the module's whole predicate, and while the baseline had rows the tree
    exercised it for free; with `ACCEPTED` empty a blinded detector is
    indistinguishable from a clean tree, which is measured in the docstring.
    """
    seen: dict[str, set[str]] = defaultdict(set)
    text: dict[str, str] = {}
    for owner, body in corpus:
        for raw in re.split(r"\n\s*\n", body):
            b = raw.strip()
            if len(b) < MIN_BLOCK:
                continue
            h = hashlib.sha1(b.encode()).hexdigest()[:12]
            seen[h].add(owner)
            text[h] = b
    return {h: (text[h], o) for h, o in seen.items() if len(o) > 1}


def _duplicated() -> dict[str, tuple[str, set[str]]]:
    """Verbatim blocks appearing in more than one child, keyed by content hash."""
    return _blocks(_corpus())


def test_the_DUPLICATION_DETECTOR_fires_on_a_block_TWO_CHILDREN_share() -> None:
    """Live control for `_blocks`, one arm per way it can answer wrongly.

    Without this the module is green whether the detector works or not — see
    the measurement in the docstring. Fixtures are self-contained strings: a
    control that mutates the real corpus proves the corpus.
    """
    block = "R" * MIN_BLOCK
    shared = [("build_draft", block), ("build_refine", block)]
    assert list(_blocks(shared)) and next(iter(_blocks(shared).values()))[1] == {
        "build_draft", "build_refine"}, "a block in two children must be reported"

    assert _blocks([("build_draft", block), ("build_draft", block)]) == {}, (
        "two copies inside ONE child are not cross-child duplication — that axis "
        "is C-115's, and reporting it here would make this guard fire on a file "
        "pair no promotion can fix"
    )
    assert _blocks([("build_draft", "S" * (MIN_BLOCK - 1)),
                    ("build_refine", "S" * (MIN_BLOCK - 1))]) == {}, (
        "below MIN_BLOCK a repeated line is boilerplate, not duplicated substance"
    )
    assert _blocks([("build_draft", block), ("build_refine", block[:-1] + "X")]) == {}, (
        "matching is VERBATIM — a near-copy is test_tier_siblings_do_not_DRIFT_"
        "by_a_sentence's half, and blurring the two hides which guard is which"
    )
    para = f"{block}\n\n{'Q' * MIN_BLOCK}"
    assert len(_blocks([("build_draft", para), ("build_refine", para)])) == 2, (
        "a file is split into blocks at blank lines, so two shared paragraphs "
        "are two findings and not one"
    )


def test_the_walk_actually_READS_the_prompt_corpus() -> None:
    """Vacuity floor on the WALK, which the control above cannot reach.

    `_blocks` can be perfect while `_corpus` returns nothing — a moved prompt
    directory, a changed glob, a rename of `prompts/`. The failure is silent and
    it looks exactly like success. Floors are deliberately far below the live
    figures so an ordinary promotion does not trip them; they catch a collapse.
    """
    corpus = _corpus()
    children = {owner for owner, _ in corpus}
    assert len(children) >= 5, (
        f"the walk found prompt files for only {sorted(children)} — the child "
        f"prompt tree moved or the glob stopped matching, and every assertion in "
        f"this module is now about nothing"
    )
    blocks = sum(1 for _, body in corpus
                 for raw in re.split(r"\n\s*\n", body) if len(raw.strip()) >= MIN_BLOCK)
    assert blocks >= 100, (
        f"only {blocks} blocks reach MIN_BLOCK across the whole child corpus; the "
        f"split or the threshold has stopped seeing prose that is plainly there"
    )


def test_no_NEW_block_is_copied_between_children() -> None:
    dup = _duplicated()
    new = {h: v for h, v in dup.items() if h not in ACCEPTED}
    assert not new, (
        "A prompt block is copied into more than one child and is not in the "
        "frozen baseline. Promote it to modules/assistant/prompts/ and reference "
        "it with a placeholder — do NOT add it to ACCEPTED:\n  "
        + "\n  ".join(
            f'{h} · {sorted(o)} · {" ".join(t.split())[:90]}'
            for h, (t, o) in sorted(new.items())
        )
    )


def _spread(accepted: dict[str, str],
            dup: dict[str, tuple[str, set[str]]]) -> list[tuple[str, int, list[str], str]]:
    """Baselined blocks now carried by MORE children than the note freezes.

    Split out from the test so the control below can drive it with a synthetic
    baseline. The real tree can only ever exercise the passing case, and a
    ratchet whose failing path has never run is a ratchet nobody has seen work.
    """
    out = []
    for h, note in accepted.items():
        if h not in dup:
            continue                      # stale — the last test owns that case
        m = re.match(r"(\d+)x", note)
        assert m, f"{h}'s baseline note must start with its consumer count, e.g. '2x': {note!r}"
        frozen, owners = int(m.group(1)), dup[h][1]
        if len(owners) > frozen:
            out.append((h, frozen, sorted(owners), note))
    return out


def test_the_SPREAD_check_fires_when_a_block_gains_a_consumer() -> None:
    """Live control for the ratchet below, from the mutation that found the hole.

    PR #100's correction pass copied an already-baselined block into a THIRD
    child and got `1282 passed` with zero failures: the baseline froze WHICH
    blocks were duplicated and never HOW WIDELY. That mutation is reproduced
    here against `_spread` directly rather than narrated in a comment, so the
    failing path is exercised on every run instead of once, by hand, in a
    session nobody can re-open.
    """
    frozen = {"deadbeef1234": "2x  a block two children were forgiven for"}
    within = {"deadbeef1234": ("text", {"build_draft", "build_draft_minor"})}
    assert _spread(frozen, within) == [], "the check fires at the frozen width"
    widened = {"deadbeef1234": ("text", {"build_draft", "build_draft_minor", "plan_revision"})}
    assert _spread(frozen, widened), "the check is blind to a THIRD consumer"
    narrowed = {"deadbeef1234": ("text", {"build_draft"})}
    assert _spread(frozen, narrowed) == [], (
        "shrinkage must stay green — the list may only shrink, and "
        "test_a_FIXED_duplication_is_removed_from_the_baseline owns that half"
    )


def test_a_baselined_block_does_not_SPREAD_to_another_child() -> None:
    """The other axis of the ratchet: a forgiven block may not gain consumers.

    `test_no_NEW_block_is_copied_between_children` keys on the block, so once a
    hash is in ACCEPTED it is forgiven no matter how many children carry it.
    Widening was therefore free, and free is what the `Nx` prefix looked like it
    was preventing while checking nothing.
    """
    spread = _spread(ACCEPTED, _duplicated())
    assert not spread, (
        "These blocks were already duplicated when the baseline froze and have "
        "since been copied into MORE children. The baseline forgives the "
        "duplication that existed, never its growth — promote the block to "
        "modules/assistant/prompts/ rather than widening its entry:\n  "
        + "\n  ".join(
            f"{h}  frozen at {n}x, now {len(o)}x {o}" for h, n, o, _ in sorted(spread)
        )
    )


def _stale(accepted: dict[str, str], dup: dict[str, tuple[str, set[str]]]) -> list[str]:
    """Baselined blocks that are no longer duplicated at all.

    Split from the test for the same reason `_spread` is: with `ACCEPTED` empty
    the live caller can only ever return `[]`, so without the control below this
    half of the ratchet has a failing path nobody has ever seen run.
    """
    return sorted(h for h in accepted if h not in dup)


def test_the_STALE_check_fires_when_a_baseline_row_is_FIXED() -> None:
    """Live control for the ratchet's shrink half, on a synthetic baseline."""
    still = {"deadbeef1234": ("text", {"build_draft", "build_refine"})}
    assert _stale({"deadbeef1234": "2x still copied"}, still) == [], (
        "a row whose block is still duplicated stays green")
    assert _stale({"deadbeef1234": "2x promoted since"}, {}) == ["deadbeef1234"], (
        "a row whose block is no longer duplicated MUST be reported — this is "
        "the half that makes the list shrink instead of becoming an excuse list")
    assert _stale({}, still) == [], "an empty baseline has nothing to go stale"


def test_a_FIXED_duplication_is_removed_from_the_baseline() -> None:
    """The ratchet. Without this, the baseline is a permanent excuse list."""
    stale = _stale(ACCEPTED, _duplicated())
    assert not stale, (
        "These baseline entries are no longer duplicated — the block was promoted "
        "or deleted. Remove their lines from ACCEPTED so the list keeps "
        "shrinking:\n  " + "\n  ".join(f"{h}  {ACCEPTED[h]}" for h in stale)
    )


# --- the rulings, checked -----------------------------------------------------


def test_every_FAMILY_RULING_is_well_formed() -> None:
    """A ruling states a verdict, the SIGNAL that produced it, and its category.

    The phase this landed under does not ask merely that each baseline row be
    disposed — it asks that a disposition say *which signal decided it and why*,
    because an undisposed row and a row disposed by a shrug look identical six
    weeks later. `ruling_defects` is the shape check; the control below proves
    it can fail.
    """
    bad = {k: fvp.ruling_defects(r) for k, (_, r) in FAMILY_RULINGS.items()}
    bad = {k: v for k, v in bad.items() if v}
    assert not bad, "malformed family rulings:\n  " + "\n  ".join(
        f"{k}: {'; '.join(v)}" for k, v in sorted(bad.items())
    )

    # AND IT MUST NAME ITS OWN KEY, which `ruling_defects` cannot check because
    # it sees one string and not the dict it is filed under. Without this, a
    # ruling keyed `review-depth` whose text cites `stage-ordering` passes every
    # shape check while defeating the property the key exists for — that a later
    # reconciliation is a LOOKUP. The key is the index; the citation is the
    # answer; a mismatch means the index points at the wrong answer.
    contract = set(fvp.TIER_INVARIANT) | set(fvp.TIER_SCOPED)
    unknown = sorted(set(FAMILY_RULINGS) - contract)
    assert not unknown, (
        f"these rulings are filed under a category the tier contract does not "
        f"define, so nothing can look them up: {unknown}"
    )
    mismatched = sorted(k for k, (_, r) in FAMILY_RULINGS.items() if k not in r)
    assert not mismatched, (
        f"these rulings do not cite the category they are filed under: "
        f"{mismatched}. A reconciliation looks up the category and reads the "
        f"ruling; if they disagree it reads the wrong one."
    )


def test_the_RULING_CHECK_fires_on_each_way_a_ruling_can_be_empty() -> None:
    """Live control for the check above, one arm per defect it claims to catch.

    THE CORPUS CAN ONLY EVER EXERCISE THE PASSING BRANCH — every ruling in the
    tree is well-formed by construction, so without this the validator's failing
    path would never run. Each arm is a SELF-CONTAINED string rather than a
    mutation of a real ruling: a control sharing a fixture with the thing it
    mutates over-fires, and what it then proves is the fixture.
    """
    assert fvp.ruling_defects(
        "PROMOTE S2 stage-ordering — because the sites are alike."
    ) == [], "a well-formed ruling must pass"

    def one(text: str) -> str:
        d = fvp.ruling_defects(text)
        assert len(d) == 1, f"expected exactly one defect, got {d}"
        return d[0]

    assert "must OPEN" in one("S2 stage-ordering — no verdict at the front.")
    assert "no deciding signal" in one("PROMOTE stage-ordering — no signal named.")
    assert "no category" in one("PROMOTE S2 — no category from the contract.")
    assert "magnitude" in one(
        "PROMOTE S2 stage-ordering — the two sit at 85.8% similarity."
    )
    assert "magnitude" in one(
        "PROMOTE S2 stage-ordering — a ratio of 0.786 between the copies."
    )
    assert "magnitude" in one(
        "PROMOTE S2 stage-ordering — the copies are 86 percent alike."
    )

    # AND THE BAN IS ON A SUBSTITUTE FOR REASONING, NOT ON ARITHMETIC. A ruling
    # citing the blind trial's kappa is citing the measurement that RETIRED
    # per-pair ruling; an earlier version of the check rejected it, which left an
    # author choosing between deleting the strongest evidence and spelling it as
    # a word. Both arms below must stay green.
    assert fvp.ruling_defects(
        "UNRULED S1 tier-identity — per-pair ruling measured kappa 0.000 against "
        "the field's 0.271 benchmark, so no signal here decides it."
    ) == [], "a ruling citing the trial's own kappa must not read as a magnitude"
    assert fvp.ruling_defects(
        "PROMOTE S2 stage-ordering — 3 dispatch paths render it and none omits it."
    ) == [], "a plain count is not a similarity magnitude"


def test_every_RULED_fragment_still_EXISTS_in_the_pool() -> None:
    """A ruling naming a fragment nobody ships is a ruling about nothing.

    This is the ratchet's other end. `test_a_FIXED_duplication_is_removed_from_
    the_baseline` stops a disposed row from lingering; this stops a DISPOSITION
    from outliving the thing it disposed of. A fragment deleted or renamed
    without its ruling being revisited leaves prose asserting a decision about
    text that is gone, which is the state the whole module exists to prevent.
    """
    named = [stem for stems, _ in FAMILY_RULINGS.values() for stem in stems]
    assert len(named) == len(set(named)), (
        "a fragment is ruled twice; one finding is one entry, and two rulings on "
        f"one fragment is two answers: {sorted(n for n in named if named.count(n) > 1)}"
    )
    missing = sorted(s for s in named if not (SHARED / f"{s}.md").is_file())
    assert not missing, (
        "these fragments carry a family ruling and no longer exist in the pool. "
        "Either restore them or revisit the ruling — a decision about deleted "
        f"text is worse than no decision: {missing}"
    )

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

AND IT SHRANK: 48 -> 13 in one change. The three largest consumer-sets were the
whole of it — a child and its `_minor` sibling twice over, plus the two research
entry points — 35 blocks and 72% of the duplicated bytes, all of it promoted to
`modules/assistant/prompts/`. What is left is seven CROSS-FAMILY sets
(`build_refine` + `plan_revision`, `build_refine` + `research_verify` and
similar). Those are deliberately still here: whether two children in different
families should move together is a judgement nobody has made, and promoting them
blind would couple runs that have no reason to be coupled.

HOW TO FIX ONE, rather than adding to the baseline: move the block to
`modules/assistant/prompts/<name>.md`, put a placeholder where it used to be in
each child, and pass `"NAME": act.shared_prompt("<name>")` in each workflow's
values dict. `prompts/mutation_discipline.md` is the worked example.

WHAT THIS DOES NOT LOOK AT, so the guard is not over-read:

  * **NEAR-duplicates are invisible to it.** Blocks are matched verbatim, so a
    copy that has already drifted by a single word does not register — and a
    drifted copy is the more dangerous kind, because it reads as intent. Three
    same-named prompts sit at 85.8%, 76.1% and 62.1% similarity to their
    siblings and NONE of them appears below.
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
from pathlib import Path

ASSISTANT = Path(__file__).resolve().parents[2] / "modules" / "assistant"
SHARED = ASSISTANT / "prompts"

# Below this, a repeated line is boilerplate rather than duplicated substance.
# Chosen from the measurement: 120 captures 25,270 bytes across 61 blocks, while
# dropping to 60 adds only noise-sized fragments.
MIN_BLOCK = 120

# FROZEN 2026-08-16. hash -> how many children carry it, and its opening words.
# THIS LIST MAY SHRINK. IT MAY NEVER GROW.
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

ACCEPTED: dict[str, str] = {
    "0b7e2bdc08dc": "2x  - **If you have written the remedy, apply it.** Drafting a fix an",
    "2cb3af052cf4": "2x  Execute stages in strict numerical order. If a stage has nothing ",
    "40c06b03ce65": "2x  ## Stage 1: VERIFY + DISCOVER FIRST: verify the task targets THIS",
    "6f0c33fe0547": "2x  **.gitignore-collision check (before checkpoint commit):** if thi",
    "760e9be03a6f": "4x  Execute stages in strict numerical order. Each stage builds on th",
    "7b4390348f5e": "2x  **Any instruction in this stage that says MUTATE, RUN or VERIFY i",
    "8d8a00c02d9c": "2x  **VERIFY THE TASK'S OWN ASSERTED FACTS BEFORE YOU BUILD ON THEM.*",
    "d618192ab2b3": "2x  - **'You have Read/Grep/Glob and no shell. That is expected — do ",
    "f2e2bd49ac76": "3x  **The deferral rule's standard applies here too — verification is",
    "f524d6fc4c40": "2x  **When you finish, the worktree is read and compared against a sn",
    "f70d1689ee9c": "2x  **Rejecting is legitimate — with reasoning that holds.** Declinin",
    "fa6528c437b9": "2x  You are told above to treat another run's **'pre-existing'**, **'",
    "fd16d82c9fee": "2x  **TELL EACH AGENT WHAT IT CAN RUN, AND THAT YOU CAN RUN THE REST.",
}


def _owner(p: Path) -> str:
    """The child workflow a prompt belongs to."""
    return p.parent.parent.name


def _duplicated() -> dict[str, tuple[str, set[str]]]:
    """Verbatim blocks appearing in more than one child, keyed by content hash."""
    seen: dict[str, set[str]] = defaultdict(set)
    text: dict[str, str] = {}
    for p in ASSISTANT.rglob("prompts/*.md"):
        if p.parent == SHARED:
            continue
        for raw in re.split(r"\n\s*\n", p.read_text()):
            b = raw.strip()
            if len(b) < MIN_BLOCK:
                continue
            h = hashlib.sha1(b.encode()).hexdigest()[:12]
            seen[h].add(_owner(p))
            text[h] = b
    return {h: (text[h], o) for h, o in seen.items() if len(o) > 1}


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


def test_a_FIXED_duplication_is_removed_from_the_baseline() -> None:
    """The ratchet. Without this, the baseline is a permanent excuse list."""
    dup = _duplicated()
    stale = sorted(h for h in ACCEPTED if h not in dup)
    assert not stale, (
        "These baseline entries are no longer duplicated — the block was promoted "
        "or deleted. Remove their lines from ACCEPTED so the list keeps "
        "shrinking:\n  " + "\n  ".join(f"{h}  {ACCEPTED[h]}" for h in stale)
    )

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
ACCEPTED: dict[str, str] = {
    "9059503abb24": "2x  - Discover the project's test hierarchy: look for `docs/standards/",
    "760e9be03a6f": "5x  Execute stages in strict numerical order. Each stage builds on the",
    "6f0c33fe0547": "3x  **.gitignore-collision check (before checkpoint commit):** if this",
    "f2e2bd49ac76": "3x  **The deferral rule's standard applies here too — verification is ",
    "f7b064f1785b": "2x  **Coverage check (do this FIRST):** Before writing or running test",
    "9cb7fb3c9346": "2x  ## Stage 8: SUBMIT - Stage any uncommitted changes remaining from ",
    "5854146ac948": "2x  **A word about your own bias, because it is not the one you were b",
    "0b7e2bdc08dc": "2x  - **If you have written the remedy, apply it.** Drafting a fix and",
    "8d8a00c02d9c": "2x  **VERIFY THE TASK'S OWN ASSERTED FACTS BEFORE YOU BUILD ON THEM.**",
    "c68280bc1061": "2x  1. **State it in `synthesis.md`** under a clearly-marked heading: ",
    "d618192ab2b3": "2x  - **'You have Read/Grep/Glob and no shell. That is expected — do n",
    "2b87ce89ba32": "2x  **Then check the DELIVERED CI gate — you are the only actor who ca",
    "c425e7a6ebe1": "2x  **CAN THIS TEST FAIL? (do this before declaring green — a green su",
    "0a75885e1520": "2x  **Understand why rather than obeying it.** Six versions of this ru",
    "60954fc026d4": "2x  **If yes, exactly THREE dispositions exist and the rest are UNREAC",
    "6551baf7e6f6": "2x  **You are running at COMPONENT altitude.** The pool you are buildi",
    "40c06b03ce65": "2x  ## Stage 1: VERIFY + DISCOVER FIRST: verify the task targets THIS ",
    "c182ae279adf": "2x  **This check is the reason this workflow is a separate run.** A si",
    "22f7c5d1d4bd": "2x  **The question you are answering is: how do we build this thing we",
    "19873bccbfef": "2x  ## Stage 4: VERIFY Run scoped regression to verify everything pass",
    "fd16d82c9fee": "2x  **TELL EACH AGENT WHAT IT CAN RUN, AND THAT YOU CAN RUN THE REST.*",
    "4b91ce821075": "2x  (No research-integrity check here: a build consumes the PLAN — whi",
    "b65b7e5bf5fe": "2x  ## Stage 1: FIDELITY — did this deliver what was actually asked? Y",
    "ad3a5794e542": "2x  ## Stage 3: RESOLVE — disposition AND fix You hold the disposition",
    "8389af3b48c9": "2x  ## Stage 3: IMPLEMENT Before writing code, discover the applicable",
    "3621076d701f": "2x  **Use it. Do not repeat it.** A topic already covered upstream doe",
    "5e3a3b1c2da7": "2x  **BEFORE choosing any disposition below, ask: IS THIS ABOUT THE WO",
    "b3e865fbe6f0": "2x  You may turn up a finding that bears on what the project believes ",
    "c4ffc10854dd": "2x  ## Stage 2: VALIDATE Evaluate whether the plan is actionable: - Ar",
    "70fe28a9e837": "2x  After refactoring or replacing code, actively search for and delet",
    "28635655880a": "2x  ## Stage 1: LOAD PLAN Read the plan document at the path above. Ex",
    "fa6528c437b9": "2x  You are told above to treat another run's **'pre-existing'**, **'o",
    "2ef1c828a180": "2x  Checkpoint commit: once implementation and cleanup are complete, s",
    "acaffea0db4c": "2x  This protects the work if later stages fail or the turn budget is ",
    "7b4390348f5e": "2x  **Any instruction in this stage that says MUTATE, RUN or VERIFY is",
    "4ddfea2405d3": "2x  **An escalation is rare.** If you produce more than one or two, th",
    "eaba38816677": "2x  Fix by default. You are the cheap place to fix a finding: the code",
    "2cb3af052cf4": "2x  Execute stages in strict numerical order. If a stage has nothing t",
    "21f20fc77f52": "2x  The product-level research pool is supplied to you below as read-o",
    "f70d1689ee9c": "2x  **Rejecting is legitimate — with reasoning that holds.** Declining",
    "00cf502093a2": "2x  If the project has no master runner or component test suite, fall ",
    "637fe105b298": "2x  Your action candidates live in `synthesis.md`, as §4 requires. Tha",
    "b42e417bcc8f": "2x  Then produce a consolidated summary: original task vs what was del",
    "8b979301517a": "2x  Produce a brief summary noting: - What was built and why - Any dev",
    "ac2f8f92a6d4": "2x  **You may not write to the product pool.** Not a paper, not a row,",
    "f524d6fc4c40": "2x  **When you finish, the worktree is read and compared against a sna",
    "e8c488d80967": "2x  The Standard's own test: **would this finding INVALIDATE a phase, ",
    "32e2aab93970": "2x  If the plan is not actionable, stop and clearly report what's miss",
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


def test_a_FIXED_duplication_is_removed_from_the_baseline() -> None:
    """The ratchet. Without this, the baseline is a permanent excuse list."""
    dup = _duplicated()
    stale = sorted(h for h in ACCEPTED if h not in dup)
    assert not stale, (
        "These baseline entries are no longer duplicated — the block was promoted "
        "or deleted. Remove their lines from ACCEPTED so the list keeps "
        "shrinking:\n  " + "\n  ".join(f"{h}  {ACCEPTED[h]}" for h in stale)
    )

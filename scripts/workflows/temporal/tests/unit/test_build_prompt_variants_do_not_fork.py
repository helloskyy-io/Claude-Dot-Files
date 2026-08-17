"""A build prompt variant must not silently lose the discipline its sibling carries.

THE MEASURED FAILURE, PR #99. `build_draft` ships two stage prompts: the normal
one and a `_from_plan` variant used whenever a run is launched with `--phase`.
They forked. The normal one accumulated eleven testing rules; the plan variant
received none of them and kept a stale copy of a twelfth.

**Every PMP phase builds from a plan**, so that variant is the one the whole
component runs on — and it ran with no instruction to SIZE the change. The rule
it was missing is the one that says do LESS:

    One file, no contract change: mutate only if the change IS a guard.
    A new module, contract or schema: mutate.
    A safety control, a gate or an authorization boundary: all of it.

So the fork did not merely drop rigour. It dropped the *calibration*, and the run
mutated six times with nothing telling it whether six was right.

WHY A TEST AND NOT A NOTE IN A PROMPT. A prompt line is administrative — someone
must remember to apply it to the next variant. There are five stage prompts and
adding a sixth is a normal thing to do. A test cannot be forgotten by whoever
adds it.

WHAT THIS DOES NOT LOOK AT, so the guard is not over-read:

  * **`build_refine`'s discipline is NOT the same text** — measured at 7% overlap
    with the draft fragment. It is a correction pass and says different things.
    This test does not claim the two families should share a fragment.
  * **`build_refine_minor` carries no tiering rule and this test does not fail
    it.** That is an unmeasured case, flagged rather than fixed blind; adding it
    here would assert a conclusion nobody has evidence for.
  * It checks that the discipline is REACHABLE, never that a model applied it.
"""
from __future__ import annotations

from pathlib import Path

BUILD = Path(__file__).resolve().parents[2] / "modules" / "assistant" / "build"
SHARED = Path(__file__).resolve().parents[2] / "modules" / "assistant" / "prompts"

# The placeholder every draft-family stage prompt resolves the discipline through.
PLACEHOLDER = "${MUTATION_DISCIPLINE}"

# The rule whose absence was the measured defect. Named explicitly rather than
# checking "the fragment is referenced", so that gutting the fragment fails too.
TIERING = "SIZE THE CHANGE, THEN SET THE BAR"
GUARD_SCOPE = "ASK WHAT EACH GUARD DOES NOT LOOK AT"

# THE `_from_plan` VARIANT IS NOW ONE FILE, in the shared pool. It used to be
# two byte-identical copies in the two draft children, held together by a
# `test_the_two_from_plan_prompts_are_IDENTICAL` that lived here and said it
# would go when the fork-vs-parameterize ruling collapsed them. That ruling is
# §10.1's promotion rule applied to prose, it landed, and the test went with it:
# a single file cannot differ from itself, so keeping the assertion would have
# been a check that can no longer fail.
#
# What remains here is the half that a single file does NOT make impossible —
# the variant losing the discipline its sibling carries.
DRAFT_STAGE_PROMPTS = [
    BUILD / "build_draft" / "prompts" / "stages_1_to_4.md",
    SHARED / "stages_1_to_4_from_plan.md",
]


def test_the_shared_fragment_actually_carries_the_rules() -> None:
    """Referencing an empty fragment would satisfy every other check here."""
    frag = (SHARED / "mutation_discipline.md").read_text()
    for rule in (TIERING, GUARD_SCOPE):
        assert rule in frag, (
            f"prompts/mutation_discipline.md no longer contains {rule!r}. Every "
            f"draft stage prompt resolves its discipline through this file, so "
            f"removing a rule here removes it from all of them at once."
        )


def test_every_draft_stage_prompt_REACHES_the_discipline() -> None:
    """The fork is caught here: a variant that carries neither is the defect."""
    missing = []
    for p in DRAFT_STAGE_PROMPTS:
        t = p.read_text()
        if PLACEHOLDER not in t and TIERING not in t:
            missing.append(p.relative_to(BUILD.parent))
    assert not missing, (
        "A build stage prompt neither references the shared discipline nor "
        "inlines it, so a run using it is never told how much rigour the change "
        "warrants — the PR #99 defect exactly:\n  "
        + "\n  ".join(str(m) for m in missing)
    )


def test_no_draft_child_KEEPS_a_private_copy_of_the_plan_variant() -> None:
    """The collapse must stay collapsed — a re-copied file is the fork returning.

    Deleting the identical-copies assertion above removed the only thing that
    was watching this pair. `test_prompt_blocks_are_shared_not_copied` would
    catch a re-copy at BLOCK granularity, but only for blocks over its 120-byte
    floor and only once someone regenerates its frozen baseline; this names the
    file, which is the form the defect actually took.
    """
    strays = [
        p
        for child in ("build_draft", "build_draft_minor")
        for p in (BUILD / child / "prompts").glob("*from_plan*.md")
    ]
    assert not strays, (
        "a draft child carries its own copy of a plan-driven prompt again. Both "
        "children load these from modules/assistant/prompts/ via shared_prompt(); "
        "a local copy is the PR #99 fork re-forming:\n  "
        + "\n  ".join(str(p.relative_to(BUILD.parent)) for p in strays)
    )

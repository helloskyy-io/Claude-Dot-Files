"""English number-words, shared by the prose-figure sweeps.

WHY THIS IS A MODULE AND NOT A CONSTANT IN EACH SWEEP. Two guards sweep prose
for un-derived figures — `test_journal_prose_figures_are_DERIVED` over the
journal package, `test_promotion_guard_prose_figures_are_DERIVED` over the
prompt-promotion guards. Each began with its own copy of this mapping and the
copies had ALREADY diverged when the second one landed: one stopped at `twelve`,
the other ran to `fourteen`. Nothing was watching, because a copy and an
original are the same file type.

That is verbatim the failure both of those guards exist to catch, one level down
in their own supporting data — and it is the same failure
`test_prompt_blocks_are_shared_not_copied` polices in the prompt corpus. A
figure written as "thirteen entrypoints" would have been INVISIBLE to the sweep
with the shorter vocabulary: not unregistered, not reported, simply never
recognised as a figure. A false negative in a guard whose whole job is to stop
an un-derived figure from shipping.

WHY A HELPER MODULE RATHER THAN AN IMPORT BETWEEN THE TWO SWEEPS.
`test_test_tree_hygiene` forbids a test module importing another: the names are
`_`-private, the coupling has no declared owner, and it resolves only under
pytest's default `prepend` import mode. `journal_entrypoint_facts.py` is the
established precedent for exactly this, and this file follows it.

EXTENDING THIS WIDENS BOTH SWEEPS AT ONCE, which is the point. Adding a word
makes every consumer able to see figures written with it; that is a widening of
coverage and never a narrowing, so it needs no coordination.
"""

from __future__ import annotations

NUMBER_WORDS: dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16,
}

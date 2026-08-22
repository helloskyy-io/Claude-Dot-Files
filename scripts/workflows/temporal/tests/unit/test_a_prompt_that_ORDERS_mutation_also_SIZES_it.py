"""A tier told to mutate must also be told how much, in the same assembled prompt.

THE DEFECT THIS CLOSES, MEASURED 2026-08-20. `mutation_discipline.md` carries the
fleet's sizing rule — *"SIZE THE CHANGE, THEN SET THE BAR — the maximum applied to
everything is not rigour but the absence of judgement, and it is paid in wall-clock
on every run"* — and only `build_draft` and `build_draft_minor` load it. The two
REFINE tiers load `fidelity_mutate_what_you_added.md` instead, which ordered mutation
and carried no ceiling. So a refine pass received a binding floor from the Testing
Standard (§ *When it binds*: any new test file, any test written to close a finding)
and had to find a ceiling somewhere else. PR #124 ran ELEVEN passes, nearly all
refine.

**EXACTLY ONE TIER WAS UNCEILINGED, AND THE FIRST DRAFT OF THIS DOCSTRING SAID TWO.**
A mutation corrected it: reverting the fragment fails `build_refine_minor` ALONE,
because `build_refine`'s own `prompts/stages_2_to_4.md` carries a **drifted copy** of
the sizing block while its `_minor` sibling's does not. That is C-110's finding —
guidance that is not about review depth living in one tier and not the other — and
C-111's child-versus-pool duplication axis, met from a third direction. The sizing
rule therefore exists in THREE places, two of them copies, and the tier that most
needed it had none. Stating "both tiers" would have been a false claim in the prose
of a guard, which is the class this PR's parent was closing.

THE MEASUREMENT THAT FOUND IT, and the one that killed the first hypothesis. Across
`.claude/logs`, build runs whose own output performed mutation went 44% (2026-08-06)
-> 94% (2026-08-16) -> 100% (2026-08-20). The obvious suspect was a model change,
and the logs refute it: `claude-opus-5` was already serving on 2026-08-06 at the 44%
figure, so the model was CONSTANT across the whole climb. The actual cause is commit
`7ab933b` on 2026-08-16, which promoted mutation discipline from one prompt to a
shared fragment and wired it into three more consumers — workflow-decomposition
Phase 2 doing precisely what it was chartered to do. The rise was the promotion
working; the cost was that only half of it reached the refine tiers.

WHY THE CHECK IS ON THE ASSEMBLED PROMPT AND NOT ON THE FILES. Reading the fragments
would ask *"does some file pair an order with a gate"*, which every arrangement of
these files satisfies — `mutation_discipline.md` pairs them today and the defect
existed anyway, because the tier that needed the gate never loaded that file. The
model reads ONE assembled string per dispatch; that string is the only place the
pairing is real. So this drives the real entry points, the same way
`test_promoted_fragments_render_for_every_consumer` does and for the same stated
reason: the prompt file is not the prompt.

WHAT THIS DOES NOT LOOK AT:
  * It does not judge whether a tier's gate is the RIGHT gate — only that the
    assembled prompt states one. A gate saying "always mutate everything" would
    pass here and is a content ruling, not a structural one.
  * It says nothing about whether a model OBEYED the gate. Only that it was told.
  * It does not reach a fragment no entry point renders. A gate written into a
    branch neither arm takes is invisible here, as it is everywhere else.
  * `rules.md` mentions mutation only to warn about restoring files afterwards,
    and `fidelity_evidence_discipline.md` orders a NEGATIVE CONTROL on a tool the
    run is about to trust — the floor, correctly unconditional. Neither is an
    order to do discrimination analysis, so neither needs a ceiling; the ORDERS
    tuple below is what separates them, and it is a list of imperatives rather
    than of the word "mutation".
"""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.assistant import assistant_activities as act
from modules.assistant.build.build_draft import build_draft_workflow as draft
from modules.assistant.build.build_draft_minor import build_draft_minor_workflow as draft_minor
from modules.assistant.build.build_refine import build_refine_workflow as refine
from modules.assistant.build.build_refine_minor import build_refine_minor_workflow as refine_minor

# AN ORDER TO RUN DISCRIMINATION ANALYSIS, not the word "mutation". A fragment
# that merely mentions mutating — a warning about restoring files, a note that a
# past run's loop reverted live edits — is not ordering the expensive practice
# and owes no ceiling. These are the imperatives that do order it.
# `SIZE THE CHANGE, THEN SET THE BAR` IS DELIBERATELY NOT HERE, and a mutation is
# why. It was, and the guard then could not fail on it: the string is the header
# of a block that both orders mutation and sizes it, so a prompt carrying only
# that string satisfied ORDERS and GATES at once and self-cleared. An order and
# its ceiling have to be separately observable or the pairing is unfalsifiable.
ORDERS = (
    "AND MUTATE WHAT *YOU* ADDED",
    "Verified negative control",
)

# THE CEILING, IN ANY OF THE SPELLINGS A TIER MAY CARRY IT. The draft tiers carry
# the tier table itself; the refine tiers carry the split that defers to it. Both
# are gates, and pinning one spelling would fail the other tier for being correct
# a different way.
GATES = (
    "SIZE THE CHANGE, THEN SET THE BAR",
    "NEGATIVE CONTROL is the floor",
    "MUTATION_DISCIPLINE`'s tier table",
)


class _CapturedPrompt:
    """Stands in for `run_claude` and keeps the string the model would have read."""

    def __init__(self) -> None:
        self.prompt: str | None = None

    def __call__(self, prompt, **_kwargs):
        self.prompt = prompt
        # A PR URL, because the draft tiers PARSE this reply to hand off to
        # refine and raise without one. Same shape and same reason as
        # `test_promoted_fragments_render_for_every_consumer`'s stub.
        return "done\nhttps://github.com/o/r/pull/7\n"


def _drive(monkeypatch, call) -> str:
    captured = _CapturedPrompt()
    monkeypatch.setattr(act, "run_claude", captured)
    call()
    assert captured.prompt is not None, "the workflow never reached run_claude"
    return captured.prompt


def _draft(monkeypatch, tmp_path: Path, entry) -> str:
    return _drive(monkeypatch, lambda: entry(
        description="do the thing", repo_root=tmp_path, worktree=tmp_path,
        plan_path="docs/development/widget/phase1.md", context="CTX",
    ))


def _refine(monkeypatch, tmp_path: Path, entry) -> str:
    monkeypatch.setattr(act, "pr_branch", lambda *a, **k: "build/x")
    return _drive(monkeypatch, lambda: entry(
        description="the original task", pr_number="7",
        repo_root=tmp_path, worktree=tmp_path,
    ))


TIERS = [
    ("build_draft", _draft, draft.run_draft),
    ("build_draft_minor", _draft, draft_minor.run_draft_minor),
    ("build_refine", _refine, refine.run_refine),
    ("build_refine_minor", _refine, refine_minor.run_refine_minor),
]


@pytest.mark.parametrize(("name", "build", "entry"), TIERS)
def test_a_tier_ORDERED_to_mutate_is_also_GIVEN_A_CEILING(
    monkeypatch, tmp_path: Path, name: str, build, entry
) -> None:
    prompt = build(monkeypatch, tmp_path, entry)
    ordered = [o for o in ORDERS if o in prompt]
    if not ordered:
        pytest.skip(f"{name} orders no mutation; nothing to size")
    assert any(g in prompt for g in GATES), (
        f"{name}'s assembled prompt ORDERS mutation ({ordered}) and states no "
        f"ceiling. A tier given the Testing Standard's binding floor and no upper "
        f"bound applies the maximum to everything, which the fleet's own sizing "
        f"rule calls 'the absence of judgement, paid in wall-clock on every run'. "
        f"Either load a fragment carrying the tier table, or state the "
        f"floor/elaboration split in the fragment that gives the order."
    )


def test_EVERY_TIER_IS_ORDERED_TO_MUTATE_not_merely_one_of_them(
    monkeypatch, tmp_path: Path
) -> None:
    """THE VACUITY FLOOR, PER TIER — because "at least one" was a hole.

    The check above SKIPS a tier matching no string in `ORDERS`, and `ORDERS` is
    hand-pasted wording that lives in the fragment files. A reworded fragment
    therefore turns the assertion into a SKIP rather than a failure.

    THE TWO DRAFT TIERS HELD THE OLD FLOOR GREEN. They match on `Verified
    negative control`, which comes from `mutation_discipline.md` — a fragment
    the REFINE tiers do not load. So the refine tiers, the only ones ever
    unceilinged and the entire reason this module exists, could go dark with
    nothing red, while the floor reported success on the strength of tiers that
    were never the problem.

    Found by `review-pr` against this module's own commit, using the discipline
    the commit is about: reword the fragment and watch what fails. Nothing did.
    """
    unordered = [name for name, build, entry in TIERS
                 if not any(o in build(monkeypatch, tmp_path, entry) for o in ORDERS)]
    assert not unordered, (
        f"these tiers match no string in ORDERS, so the ceiling check SKIPS them "
        f"rather than failing: {unordered}. ORDERS is a hand-pasted copy of "
        f"wording that lives in the fragments, so a reworded fragment silently "
        f"removes a tier from this module's population. Update ORDERS to the new "
        f"wording — do not delete the tier."
    )

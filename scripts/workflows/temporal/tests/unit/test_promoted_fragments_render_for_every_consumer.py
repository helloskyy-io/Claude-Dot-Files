"""A promoted prompt fragment must RENDER for every consumer, not merely have one.

WHY THIS IS NOT test_prompt_completeness. That module answers "does something
supply `${NAME}`?" by reading the consumer's source for the literal string
`"NAME"`. It is a text match, and it cannot see WHICH ARM supplies it. When this
module landed, nine fragments had just been promoted in one change (a historical
count, not a claim about `_PROMOTED` below, which has grown since) and two of
their suppliers sat inside an
`if`/`else` — `ALTITUDE_COMPONENT` is set only on the component arm, mirroring
`CANDIDATE_CEILING` on the product arm. A supplier written into the wrong branch
satisfies the static check completely and ships a literal `${ALTITUDE_COMPONENT}`
to the model, or trips `render()`'s leftover guard mid-dispatch, at real spend.

So this module DRIVES THE REAL ENTRY POINTS and reads the prompt they built —
the same shape `test_research_minor` uses, and for the same stated reason: the
prompt file is not the prompt.

WHAT THIS DOES NOT LOOK AT:

  * It does not judge whether a fragment SHOULD be shared. That is the promotion
    rule's question and `test_prompt_blocks_are_shared_not_copied` reports on it.
  * It renders one fixture per arm, not every combination of every flag. A
    branch neither arm reaches is invisible here, as it is everywhere else.
  * It asserts the fragment's text ARRIVED, never that a model obeyed it.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

import fork_vs_parameterize as fvp

from modules.assistant import assistant_activities as act
from modules.assistant.build.build_draft import build_draft_workflow as draft
from modules.assistant.build.build_draft_minor import build_draft_minor_workflow as draft_minor
from modules.assistant.build.build_refine import build_refine_workflow as refine
from modules.assistant.build.build_refine_minor import build_refine_minor_workflow as refine_minor
from modules.assistant.plan.plan_feature import plan_feature_workflow as pfeat
from modules.assistant.plan.plan_verify import plan_verify_workflow as pverify
from modules.assistant.research import research_activities as ract
from modules.assistant.research.research_refresh import research_refresh_workflow as refresh
from modules.assistant.research.research_write import research_write_workflow as write

_SHARED = Path(__file__).resolve().parents[2] / "modules" / "assistant" / "prompts"

# THE POOL IS THE PROMOTED SET, DERIVED RATHER THAN LISTED.
#
# This was a hand-maintained enumeration of a derivable set, and it fell behind
# the pool it guards: `altitude_product`, `decision_log_and_reflection`,
# `headless_execution_guard`, `mutation_discipline` and `rules` were all promoted
# before anyone re-counted, so each sat outside `_FRAGMENT_FLOOR` below and was
# unguarded against silent deletion for as long as the literal list went
# unrevisited. Pasting the missing names in would have left the NEXT promotion
# uncovered the day it landed — the same defect, one commit later. Deriving from
# the pool directory makes coverage SET-EQUAL to it by construction.
#
# The obligation does not depend on WHEN a fragment was promoted: what this
# module verifies is that a shared fragment renders for every consumer that
# loads it, which is true of every fragment in the pool. THAT SENTENCE IS A
# CHECK RATHER THAN A CLAIM — `test_every_POOL_fragment_is_render_checked_by_some_consumer`
# below holds it, because deriving this set covered the pool for the DELETION
# floor and was read as covering it for the RENDER assertions, which keyed off
# hand-maintained subsets and did not.
#
# THERE IS NO EXCLUSION SET, AND EMPTY IS THE INTENDED STEADY STATE. Every
# fragment in the pool yields a usable needle and carries a floor — measured, in
# `test_the_needles_are_real` and `test_no_PROMOTED_fragment_QUIETLY_LOSES_A_LINE`
# respectively. If one ever genuinely cannot be render-checked per consumer,
# exclude it HERE as a named constant with a one-line reason per entry, NEVER by
# narrowing the glob: an undocumented omission is precisely what produced this
# defect, and a reason in-line is what makes the next one reviewable.
#
# Needles are read from the FILE rather than pasted here: a copy would drift, and
# a drifted needle turns every assertion below into a permanent pass.
_PROMOTED = sorted(p.stem for p in _SHARED.glob("*.md"))


def _stems_loaded_by(module) -> set[str]:
    """Every pool fragment a consumer LOADS, read from that consumer's own source.

    PARSED, NOT GREPPED, and the difference is live in this tree:
    `research_write_workflow` mentions `shared_prompt("altitude_component")`
    inside a COMMENT explaining the altitude split. A regex reads that as a
    load; the AST does not see it at all, so the derivation stays about what
    the module DOES rather than about what it talks about.

    A non-literal argument is a hole rather than a stem. Skipping it silently
    would SHRINK the expected set — the failure mode where a guard gets
    quieter exactly when the code gets harder to read — so it fails here.
    """
    path = Path(module.__file__)
    return _shared_prompt_stems(ast.parse(path.read_text(encoding="utf-8")), path.name)


def _shared_prompt_stems(tree: ast.Module, where: str) -> set[str]:
    """The PREDICATE half, over an already-parsed tree so a control can drive it.

    Split out for `test_the_supplier_reader_DISCRIMINATES` below, which is the
    positive control `test_a_census_guard_proves_its_own_predicate` requires of
    every module that walks the tree: a walk that still finds call sites while
    its predicate has quietly started answering unconditionally is a permanent
    green, and a green guard replaces a review rather than prompting one.

    THE READ STAYS INLINED IN THE CALLER ABOVE, on purpose. That census
    recognises its population by `ast.parse(<expr>.read_text(...))` in argument
    position and names the bound-first shape as its largest hole; binding the
    source here to tidy the split would walk this module out of the population
    it belongs to, which is the guard-edited-to-fit-the-matcher failure that
    file explicitly refuses.
    """
    stems: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        called = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
        if called != "shared_prompt":
            continue
        arg = node.args[0] if node.args else None
        assert isinstance(arg, ast.Constant) and isinstance(arg.value, str), (
            f"{where} line {node.lineno} calls shared_prompt() "
            f"with a non-literal name, so this derivation cannot tell which "
            f"fragment it loads and the consumer's expected set would silently "
            f"shrink. Pass the stem as a literal, or exclude the consumer here "
            f"with the reason."
        )
        stems.add(arg.value)
    return stems


# THE ARM-CONDITIONAL PAIR, which is the one thing a flat source read gets wrong.
#
# A research workflow loads `altitude_component` on one arm and `altitude_product`
# on the other, so its source names both while any single run renders exactly one.
# Demanding both would make the altitude split itself a failure. Each arm below
# therefore expects its consumer's loads MINUS its sibling arm's fragment, and
# asserts that sibling is ABSENT — which is the discriminating half, and the
# reason a supplier written into the wrong branch cannot pass here.
_ALTITUDES = {"component": "altitude_component", "product": "altitude_product"}

# Matches `render()`'s own placeholder shape, DIGITS INCLUDED — an earlier
# `[A-Z_]+` in the renderer silently missed `${STAGES_1_TO_4}` and shipped a
# prompt with its whole stage body replaced by a literal token.
_PLACEHOLDER = re.compile(r"\$\{[A-Z_][A-Z_0-9]*\}")


def _needle(stem: str) -> str:
    """The longest line of a fragment — distinctive enough to locate it in a prompt.

    Skips an HTML comment header — commentary about the fragment rather than its
    substance — and SPLITS each line on its placeholders rather than discarding
    any line that contains one.

    THE DISCARD WAS THE BUG AND IT WENT ONE WAY. This read `"${" not in ln`,
    which the docstring described as skipping "placeholder-only lines" — but a
    line of PROSE carrying an inline `${RESEARCH_DIR}` is not placeholder-only,
    and dropping it took a fragment's only substantive line out of the running.
    The needle then fell back to a 29-character heading, which is under the floor
    `test_the_needles_are_real` sets and would otherwise have been a needle short
    enough to match text that is not the fragment. Splitting keeps the surviving
    prose, and a segment either side of a placeholder is exactly what survives
    rendering — which is the property a needle needs.

    NOTE THE TWO DIFFERENT SUBJECTS, because getting them the same way round is
    what makes the second condition dead code. An opening `<!--` may be indented,
    so it is tested against the STRIPPED line; a header's CONTINUATION lines are
    identified BY their indentation, so they must be tested against the RAW one.
    Testing both against `lstrip()` — as the first version of this did — makes
    the continuation arm unreachable, since `lstrip()` has already eaten the very
    whitespace that arm looks for. Harmless while no prompt carries a header —
    none does, and that is now GATED rather than observed:
    `test_no_prompt_ships_EDITOR_COMMENTARY_to_the_model` fails on any HTML
    comment in any prompt file, so this arm cannot silently start mattering. It
    is kept because the gate is the thing that could be deleted, and a needle
    drawn from commentary would make every membership check below vacuous.
    """
    segments = [
        seg.strip()
        for ln in (_SHARED / f"{stem}.md").read_text().splitlines()
        if ln.strip()
        and not ln.lstrip().startswith(("<!--", "-->"))
        and not ln.startswith("     ")
        for seg in _PLACEHOLDER.split(ln)
        if seg.strip()
    ]
    assert segments, f"{stem}.md yielded no usable needle — the fragment is empty or all placeholders"
    return max(segments, key=len)


class _CapturedPrompt:
    """Stands in for `run_claude` and keeps the prompt it was handed."""

    def __init__(self) -> None:
        self.prompt: str | None = None

    def __call__(self, prompt, **_kwargs):
        self.prompt = prompt
        return "done\nhttps://github.com/o/r/pull/7\n"


def _drive(monkeypatch, activities, call) -> str:
    captured = _CapturedPrompt()
    monkeypatch.setattr(activities, "run_claude", captured)
    call()
    assert captured.prompt is not None, "the workflow never reached run_claude"
    return captured.prompt


# --- build: the plan-driven draft, shared across both tiers -------------------


def _draft_prompt(monkeypatch, tmp_path: Path, entry) -> str:
    return _drive(monkeypatch, act, lambda: entry(
        description="do the thing", repo_root=tmp_path, worktree=tmp_path,
        plan_path="docs/development/widget/phase1.md", context="CTX",
    ))


def _draft_prompts_EVERY_PATH(monkeypatch, tmp_path: Path, entry) -> dict[str, str]:
    """Every prompt a draft tier can dispatch, keyed by the path that builds it.

    A DRAFT TIER HAS THREE, NOT ONE, and the check above used to drive only the
    plan-driven one. Its rationale — "a supplier that is built but never reaches
    the prompt" — is about a fragment reaching NO prompt, but its implementation
    read "does not reach THIS prompt", which are different claims the moment a
    workflow has more than one template. A block living in the non-plan stages
    body is legitimately absent from the plan-driven body: the plan path renders
    `prompts/stages_1_to_4_from_plan.md` instead.

    Driving all three makes the assertion match the rationale and is strictly
    stronger than what it replaced, because the two non-plan wrappers were never
    rendered here at all.
    """
    monkeypatch.setattr(act, "pr_branch", lambda *a, **k: "build/x")
    common = dict(description="do the thing", repo_root=tmp_path, worktree=tmp_path)
    return {
        "plan": _drive(monkeypatch, act, lambda: entry(
            plan_path="docs/development/widget/phase1.md", context="CTX", **common)),
        "new_branch": _drive(monkeypatch, act, lambda: entry(context="CTX", **common)),
        "update_pr": _drive(monkeypatch, act, lambda: entry(
            pr_number="7", context="CTX", **common)),
    }


@pytest.mark.parametrize(
    ("name", "entry", "module"),
    [("build_draft", draft.run_draft, draft),
     ("build_draft_minor", draft_minor.run_draft_minor, draft_minor)],
)
def test_a_draft_tier_renders_EVERY_fragment_it_loads_on_SOME_path(
    monkeypatch, tmp_path, name: str, entry, module
) -> None:
    """The expected set is the consumer's own loads, not a list kept beside it.

    This named two stems while the draft tiers load more than that through
    `shared_prompt()`, so the rest were supplied and never checked — the same
    hand-maintained-subset defect `_PROMOTED` above was just corrected for,
    one level down. Deriving from the consumer means a fragment is covered
    the moment that consumer starts loading it.
    """
    prompts = _draft_prompts_EVERY_PATH(monkeypatch, tmp_path, entry)
    assert len(prompts) == 3, "a draft tier's dispatch paths are not all covered"
    missing = sorted(
        s for s in _stems_loaded_by(module)
        if not any(_needle(s) in p for p in prompts.values())
    )
    assert not missing, (
        f"{name} loads {missing} through shared_prompt() and renders without "
        f"them on ANY of its dispatch paths ({sorted(prompts)}). A supplier that "
        f"is built but never reaches a prompt leaves that tier running on "
        f"instructions the fragment's edits never touch."
    )


# --- the two guards the SOME-path check above cannot be -----------------------
#
# `..._on_SOME_path` asks whether a fragment reaches ANY of a tier's three
# dispatch bodies, which is the right question for "is this supplier ever used"
# and the wrong one for both defects that arrived through this seam: two
# evidence-discipline fragments were loaded unconditionally by both draft
# modules and referenced by neither the plan wrapper nor the plan body, and the
# minor tier's new-branch wrapper was missing two blocks its PR-path sibling
# had. One rendering path satisfied `any()` in every case, so the suite was
# green over both.
#
# The split is by the tier contract, not by a list: LOADED-ON-A-PATH must RENDER
# ON THAT PATH for every fragment, and a fragment ruled TIER-INVARIANT must
# additionally reach EVERY path. Which is which comes from
# `fork_vs_parameterize.FAMILY_RULINGS`, so a fragment is covered the moment it
# is ruled rather than when someone remembers to add it here.


class _RecordingPool:
    """Wraps `act.shared_prompt` and records what ONE dispatch actually loaded.

    WHY DYNAMIC WHERE `_stems_loaded_by` IS STATIC. The AST reader returns every
    stem a module CAN load on any path; both draft modules load fragments inside
    an `if plan_path:` arm, and source cannot say which arm ran. "Did this
    dispatch use what it built" is a per-dispatch question, so it is answered by
    watching the dispatch.
    """

    def __init__(self, real) -> None:
        self._real = real
        self.stems: list[str] = []

    def __call__(self, stem: str) -> str:
        self.stems.append(stem)
        return self._real(stem)


def _draft_paths_with_loads(monkeypatch, tmp_path: Path, entry) -> dict[str, tuple[str, set[str]]]:
    """Each dispatch path as `(rendered prompt, pool stems that path loaded)`."""
    monkeypatch.setattr(act, "pr_branch", lambda *a, **k: "build/x")
    common = dict(description="do the thing", repo_root=tmp_path, worktree=tmp_path)
    calls = {
        "plan": lambda: entry(plan_path="docs/development/widget/phase1.md",
                              context="CTX", **common),
        "new_branch": lambda: entry(context="CTX", **common),
        "update_pr": lambda: entry(pr_number="7", context="CTX", **common),
    }
    real = act.shared_prompt
    out: dict[str, tuple[str, set[str]]] = {}
    for path, call in calls.items():
        pool = _RecordingPool(real)
        monkeypatch.setattr(act, "shared_prompt", pool)
        try:
            out[path] = (_drive(monkeypatch, act, call), set(pool.stems))
        finally:
            # Restored explicitly rather than with `monkeypatch.undo()`, which
            # would also revert `pr_branch` and break the next path.
            monkeypatch.setattr(act, "shared_prompt", real)
    return out


_DRAFT_TIERS = [("build_draft", draft.run_draft),
                ("build_draft_minor", draft_minor.run_draft_minor)]


@pytest.mark.parametrize(("name", "entry"), _DRAFT_TIERS)
def test_every_pool_fragment_a_dispatch_LOADS_also_RENDERS(
    monkeypatch, tmp_path, name: str, entry
) -> None:
    """A fragment built for a path and not referenced by it is text nobody reads.

    This is the finding that produced the whole guard: `build_from_plan.md` and
    `stages_1_to_4_from_plan.md` referenced neither evidence-discipline fragment
    while both draft modules loaded both unconditionally, so every plan-driven
    build in this repo — which is how every phase here gets built — ran without
    the rule that tells a run to verify the task's own asserted facts. Nothing
    failed, because the two fragments did render on the two non-plan paths.

    NO CATEGORY IS CONSULTED HERE. Loading a fragment and discarding it is waste
    whatever the fragment says, and keeping this half classification-free means
    it still fires on the pool's unruled majority.
    """
    paths = _draft_paths_with_loads(monkeypatch, tmp_path, entry)
    assert len(paths) == 3, "a draft tier's dispatch paths are not all covered"
    # VACUITY FLOOR: a recorder that captured nothing would make the assertion
    # below trivially true on every path, and a green suite would then mean
    # `shared_prompt` had stopped being the seam rather than that nothing is
    # discarded.
    empty = sorted(p for p, (_, stems) in paths.items() if not stems)
    assert not empty, (
        f"{name} loaded NO pool fragment on {empty} — either the tier stopped "
        f"using shared_prompt() or this fixture stopped observing it, and in "
        f"both cases the check below is asserting nothing"
    )
    discarded = sorted(
        f"{path}: {stem}"
        for path, (prompt, stems) in paths.items()
        for stem in stems
        if _needle(stem) not in prompt
    )
    assert not discarded, (
        f"{name} loads these fragments on a path whose template never "
        f"references them, so the text is built and thrown away:\n  "
        + "\n  ".join(discarded)
        + "\nEither reference the placeholder from that path's body, or move the "
          "supplier into the arm that has a consumer."
    )


# A TIER-INVARIANT FRAGMENT THAT DOES NOT YET REACH EVERY PATH, with the reason.
# THIS LIST MAY SHRINK AND MAY NEVER GROW SILENTLY — the staleness half of the
# test below deletes-by-failing any entry that has stopped being a gap, so it
# cannot rot into permission the way an unexamined exemption does.
#
# It exists because the alternative was worse in a way this repo has measured: a
# guard that is red on arrival gets skipped rather than fixed, and each of these
# is a real content decision outside the change that added the guard. Every one
# is a live finding, written where the next reader of the guard sees it rather
# than in a merged PR body nobody re-reads.
_INVARIANT_PATH_GAPS = {
    ("build_draft_minor", "gitignore_collision_check"):
        "the two wrappers carry no gitignore-collision check at all, so a light "
        "tier run that creates a file matched by an unanchored ignore pattern "
        "ships a PR the file is invisible in. Genuinely absent rather than "
        "reworded — the closest thing either wrapper has is a self-description "
        "step about docs/file_structure.txt.",
    ("build_draft_minor", "stage_order_is_mandatory"):
        "both wrappers open with their own condensed EXECUTION ORDER IS "
        "MANDATORY paragraph instead of the fragment, so the instruction is "
        "present and the fragment is not. That is a child holding a drifted "
        "near-copy of a pool fragment, which is C-111's axis and reachable by "
        "no guard here at any granularity; reconciling it is a content ruling, "
        "not a wiring fix.",
    ("build_draft_minor", "characterize_by_execution"):
        "promoted out of the PR-path wrapper and given to the new-branch "
        "wrapper in the same change; the plan-driven body has never carried it, "
        "and adding it there would change the prompt build_draft renders from "
        "the same shared body. A cross-tier edit, correctly not made by the "
        "pass that promoted the fragment.",
}


@pytest.mark.parametrize(("name", "entry"), _DRAFT_TIERS)
def test_a_TIER_INVARIANT_fragment_reaches_EVERY_dispatch_path(
    monkeypatch, tmp_path, name: str, entry
) -> None:
    """What the contract classes invariant, every path of that tier must receive.

    TIER_INVARIANT's own words are the assertion: a category where "a difference
    between the tiers would mean the two are running different rules". A
    difference between two PATHS of ONE tier is the same defect with a smaller
    blast radius and no reviewer looking at it, which is how the evidence-
    discipline pair reached only two of three draft bodies while a ruling in
    this tree declared it invariant.

    WHAT THIS DOES NOT LOOK AT: a fragment no ruling names is skipped entirely,
    and most of the pool is unruled. It also cannot see an invariant instruction
    a path carries as its OWN prose instead of as the fragment — `_needle` looks
    for the fragment's longest line, so a reworded copy reads as absent and a
    verbatim copy reads as present. Two of the exemptions below are exactly that.
    """
    paths = _draft_paths_with_loads(monkeypatch, tmp_path, entry)
    loaded_somewhere = set().union(*(stems for _, stems in paths.values()))
    invariant = sorted(
        s for s in loaded_somewhere if fvp.category_of(s) in fvp.TIER_INVARIANT
    )
    assert invariant, (
        f"{name} loaded no fragment carrying a TIER_INVARIANT ruling, so this "
        f"test asserted nothing. Either the rulings moved or the fixture did."
    )
    missing = {
        s: sorted(p for p, (prompt, _) in paths.items() if _needle(s) not in prompt)
        for s in invariant
    }
    missing = {s: where for s, where in missing.items() if where}

    unexplained = sorted(s for s in missing if (name, s) not in _INVARIANT_PATH_GAPS)
    assert not unexplained, (
        f"{name} does not render these TIER-INVARIANT fragments on every "
        f"dispatch path: "
        + "; ".join(f"{s} missing from {missing[s]}" for s in unexplained)
        + ". The contract says a difference here means the two tiers — or, "
          "here, two paths of one tier — are running different rules. Reference "
          "the placeholder from the body that lacks it, or, if the difference "
          "is deliberate, rule the fragment TIER_SCOPED in FAMILY_RULINGS with "
          "the signal that decided it."
    )

    # THE RATCHET. An exemption that has stopped being true must go, or the list
    # becomes a record of what was once wrong rather than of what still is.
    stale = sorted(s for (tier, s) in _INVARIANT_PATH_GAPS if tier == name and s not in missing)
    assert not stale, (
        f"these {name} entries in _INVARIANT_PATH_GAPS name fragments that now "
        f"reach every dispatch path — delete the rows: {stale}"
    )


def test_the_INVARIANT_GAP_LIST_names_only_fragments_the_CONTRACT_calls_invariant() -> None:
    """An exemption for a tier-scoped fragment would forgive a rule nobody made.

    Cheap and worth stating: the list above suppresses failures, so an entry for
    a fragment the contract never classed invariant is a row that can never
    expire — the ratchet in the test above only fires on a gap that CLOSED, and
    a fragment outside the invariant set never enters the check at all.
    """
    wrong = sorted(
        f"{tier}/{stem}" for (tier, stem) in _INVARIANT_PATH_GAPS
        if fvp.category_of(stem) not in fvp.TIER_INVARIANT
    )
    assert not wrong, (
        f"_INVARIANT_PATH_GAPS exempts fragments that carry no TIER_INVARIANT "
        f"ruling, so the exemption forgives nothing and will never expire: {wrong}"
    )


def test_the_two_draft_TIERS_RENDER_IDENTICALLY(monkeypatch, tmp_path) -> None:
    """What the deleted file-identity assertion used to guarantee, but stronger.

    `test_build_prompt_variants_do_not_fork` once held two byte-identical
    `_from_plan` FILES together. Promotion collapsed them, so that assertion
    could no longer fail and was removed — but the property it protected is
    about what the two tiers SEND, and a single file does not guarantee that on
    its own. Either workflow can still diverge in the values dict it builds
    around the shared text.

    So the check moved up a level: same inputs, same rendered prompt, byte for
    byte. This catches a class the file check never could — a supplier added to
    one tier and not the other.
    """
    a = _draft_prompt(monkeypatch, tmp_path, draft.run_draft)
    b = _draft_prompt(monkeypatch, tmp_path, draft_minor.run_draft_minor)
    assert a == b, (
        "build_draft and build_draft_minor render DIFFERENT prompts from the same "
        "plan-driven inputs, so the two tiers no longer share one plan-build "
        f"instruction set ({len(a):,} vs {len(b):,} bytes)."
    )


# --- build: the fragments BOTH refine tiers share -----------------------------
#
# This banner used to state a count and the count was left behind twice by the
# commits that grew the list — "six" over eight entries, then over eleven. The
# list's own length is the figure, so the banner no longer restates it and
# `test_promotion_guard_prose_figures_are_DERIVED` enforces that it cannot
# start again.

# THE UNION, DELIBERATELY, NOT THE INTERSECTION. Every fragment EITHER refine
# tier loads is demanded of BOTH, which is the contract the failure message
# below states: the tiers differ in how many lenses they run, never in what a
# refine pass IS. An intersection would let a fragment drop out of one tier
# and quietly narrow the check to whatever survived in both — the same silent
# shrink this module keeps finding. If a genuinely tier-scoped fragment is
# ever promoted, that is the ruling to make explicitly, here, with a reason.
# THE RULING THE COMMENT ABOVE ASKS FOR, MADE. These two are ONE instruction
# split across two blocks — the first ends "Put this in the dispatch, in these
# two parts:" and the second is those parts — and what they carry is the MAJOR
# tier's agent roster, named agent by agent. Under the `_minor` tier contract in
# `fork_vs_parameterize.py` a roster is `review-depth`, which is the one axis
# both refine workflows' own comments already agree is tier-scoped. They are
# still POOL fragments, because `build_refine` and `plan_revision` both dispatch
# that same roster and the pool sits above families; they are simply not
# demanded of a tier that dispatches one agent.
#
# THE EXCLUSION IS BY STEM AND IT IS NARROW ON PURPOSE. Anything else either tier
# loads is still demanded of both, so this cannot become the intersection the
# comment above warns against — adding a stem here is a visible edit carrying a
# reason, which is what distinguishes a ruling from a quiet shrink.
_TIER_SCOPED_FRAGMENTS = {
    "tell_each_agent_what_it_can_run":
        "review-depth: enumerates the major tier's five-agent roster",
    "agents_have_no_shell":
        "review-depth: the second half of that same roster instruction",
}

_REFINE_FRAGMENTS = sorted(
    (_stems_loaded_by(refine) | _stems_loaded_by(refine_minor)) - set(_TIER_SCOPED_FRAGMENTS)
)


@pytest.mark.parametrize(
    ("name", "entry"),
    [("build_refine", refine.run_refine),
     ("build_refine_minor", refine_minor.run_refine_minor)],
)
def test_a_refine_pass_renders_EVERY_shared_disposition_fragment(
    monkeypatch, tmp_path, name: str, entry
) -> None:
    monkeypatch.setattr(act, "pr_branch", lambda *a, **k: "build/x")
    prompt = _drive(monkeypatch, act, lambda: entry(
        description="the original task", pr_number="7",
        repo_root=tmp_path, worktree=tmp_path,
    ))
    missing = [s for s in _REFINE_FRAGMENTS if _needle(s) not in prompt]
    assert not missing, (
        f"{name} renders without {missing}. The two refine tiers differ in how "
        f"many review lenses they run, never in what a refine pass IS — a tier "
        f"missing one of these is running a different disposition contract."
    )


# --- research: the altitude arms, which is where the branch risk lives ---------


# The parametrize below passes an ENTRY POINT; the deriver needs the module that
# entry point lives in. Mapped by name rather than reached through `entry` so the
# association is visible where it is declared.
_RESEARCH_MODULE = {"research_write": write, "research_refresh": refresh}


def _component_pool(tmp_path: Path) -> Path:
    pool = tmp_path / "docs" / "development" / "widget" / "research"
    pool.mkdir(parents=True)
    return pool


def _product_pool(tmp_path: Path) -> Path:
    pool = tmp_path / "docs" / "standards" / "architecture" / "research"
    (pool / "raw").mkdir(parents=True)
    return pool


def _research_prompt(monkeypatch, tmp_path: Path, entry, pool: Path) -> str:
    kwargs = {"research_dir": pool, "repo_root": tmp_path, "worktree": tmp_path}
    if entry is refresh.run_refresh:
        kwargs["due"] = [pool / "raw" / "a-paper.md"]
    return _drive(monkeypatch, ract, lambda: entry(**kwargs))


@pytest.mark.parametrize(
    ("name", "entry"),
    [("research_write", write.run_write), ("research_refresh", refresh.run_refresh)],
)
def test_a_COMPONENT_run_renders_the_shared_lane_rules(
    monkeypatch, tmp_path, name: str, entry
) -> None:
    """The branch-placement check this module exists for.

    `ALTITUDE_COMPONENT` is supplied on the `else` arm only. Written into the
    wrong arm it still satisfies the static supplier check, and the failure
    surfaces as literal `${ALTITUDE_COMPONENT}` reaching the model, or as
    `render()` raising at dispatch — never in a suite.
    """
    prompt = _research_prompt(monkeypatch, tmp_path, entry, _component_pool(tmp_path))
    expected = _stems_loaded_by(_RESEARCH_MODULE[name]) - {_ALTITUDES["product"]}
    missing = sorted(s for s in expected if _needle(s) not in prompt)
    assert not missing, (
        f"{name} at COMPONENT altitude renders without {missing}. The lane rules "
        f"that bound what the run may write are supplied and did not arrive."
    )
    assert "${" not in prompt, (
        f"{name} shipped a literal placeholder — render()'s leftover guard should "
        f"have raised before this."
    )


@pytest.mark.parametrize(
    ("name", "entry"),
    [("research_write", write.run_write), ("research_refresh", refresh.run_refresh)],
)
def test_a_PRODUCT_run_renders_NO_component_lane_rules(
    monkeypatch, tmp_path, name: str, entry
) -> None:
    """The discriminating half — without it, an UNCONDITIONAL supplier passes.

    Supplying the component fragment on both arms would satisfy every assertion
    above and inject a component pool's write boundary into a product run, which
    is the exact confusion the altitude split exists to prevent. The two
    altitudes must render DIFFERENT text, and this is the side that says so.
    """
    prompt = _research_prompt(monkeypatch, tmp_path, entry, _product_pool(tmp_path))
    assert _needle(_ALTITUDES["component"]) not in prompt, (
        f"{name} at PRODUCT altitude renders the COMPONENT lane rules. The "
        f"supplier has become unconditional."
    )
    expected = _stems_loaded_by(_RESEARCH_MODULE[name]) - {_ALTITUDES["component"]}
    missing = sorted(s for s in expected if _needle(s) not in prompt)
    assert not missing, (
        f"{name} at PRODUCT altitude renders without {missing}. Without the "
        f"positive half this test only says what is ABSENT, so an arm that "
        f"renders nothing at all passes it."
    )


# --- the guard that makes all of the above meaningful -------------------------


def test_an_UNSUPPLIED_fragment_placeholder_stops_the_dispatch(monkeypatch, tmp_path) -> None:
    """Negative control, derived from the claim the promotion rule makes.

    The rule permits a shared fragment to carry its own placeholders and says
    every consumer must supply them, because one that does not "renders a live
    ${...} and render() raises at dispatch rather than in the suite". This
    proves that raise is real on a PROMOTED path — otherwise the assertions
    above are checking that text arrives while the actual failure mode (text
    arriving with a hole in it) goes unobserved.

    The mutation is on the FRAGMENT, not on a workflow's values dict: it
    reproduces a fragment gaining a placeholder that its consumers were never
    updated for, which is the way this fails in practice.
    """
    real = act.shared_prompt

    def sabotaged(name: str) -> str:
        if name == "stages_1_to_4_from_plan":
            return real(name) + "\n${NOBODY_SUPPLIES_THIS}\n"
        return real(name)

    monkeypatch.setattr(act, "shared_prompt", sabotaged)
    with pytest.raises(ValueError, match="unsubstituted prompt placeholders"):
        _draft_prompt(monkeypatch, tmp_path, draft.run_draft)


# FROZEN 2026-08-17: substantive lines (40+ chars) per promoted fragment.
#
# WHY A FLOOR EXISTS AT ALL, measured rather than imagined. PROMOTION TRADES A
# DRIFT RISK FOR A DELETION RISK. While text is duplicated across two children a
# one-sided edit is a divergence some detector can see; once it is shared,
# removing it takes it from every consumer at once and NOTHING diverges. Proved
# on the fragment this change created: deleting the `RE-CHECK origin/main`
# bullet from `submit_and_push.md` outright left the entire suite green. The
# membership checks above could not see it because `_needle` returns the LONGEST
# line, so deleting any other line simply promotes a new needle.
#
# THIS IS THE LOCAL HALF, AND IT NOW SPANS THE WHOLE POOL — `_PROMOTED` is
# derived from it, so no fragment sits outside the floor. The general question
# remains open: a standing CONTENT gate, which is C-108 (placed as C-106 and
# renumbered when this branch's merge found the id taken). A floor is not that
# gate — it catches deletion and says nothing about a line being rewritten into
# something else, which is the half no guard here reaches.
_FRAGMENT_FLOOR = {
    "filing_a_candidate_row": 4,
    "build_from_plan": 9,
    # 44, lowered from 46 on 2026-08-19, and the reason is recorded because this
    # floor exists precisely so a shrink cannot pass unexplained. Two blocks left
    # this fragment and NOT the prompt: `stage_order_is_mandatory` and
    # `gitignore_collision_check` were byte-exact copies of pool fragments living
    # INSIDE a pool fragment — an axis no duplication guard reaches, since
    # `_duplicated()` skips the pool by construction — and are now placeholders
    # both draft tiers supply. The assembled prompt is unchanged but for the
    # promotion seam.
    "stages_1_to_4_from_plan": 44,
    "fidelity_premise": 2,
    "fidelity_read_and_compare": 6,
    "fidelity_needs_a_separate_run": 1,
    "fidelity_evidence_discipline": 4,
    "fidelity_mutate_what_you_added": 1,
    "resolve_disposition_authority": 2,
    "resolve_rejections_must_be_executed": 1,
    "resolve_closed_disposition_list": 4,
    "resolve_disposition_definitions": 5,
    "resolve_fix_by_default_and_summary": 3,
    "verify_and_ci_gate": 6,
    "altitude_component": 16,
    "submit_and_push": 5,
    # MEASURED 2026-08-17 by `_substantive_lines`, when `_PROMOTED` stopped being
    # a literal list and these came under the floor for the first time. Each was
    # promoted before this module last counted, so each was unguarded until now.
    "altitude_product": 34,
    "decision_log_and_reflection": 43,
    "headless_execution_guard": 6,
    "mutation_discipline": 12,
    "rules": 22,
    # MEASURED 2026-08-19, when the frozen duplication baseline was ruled on and
    # emptied. Each was a block duplicated between two children until this change.
    "agents_have_no_shell": 8,
    "gitignore_collision_check": 1,
    "orchestrator_executes_agents_read": 3,
    "research_stage_1_verify_and_discover": 1,
    "resolve_apply_the_remedy_you_wrote": 4,
    "resolve_rejecting_is_legitimate": 1,
    "resolve_your_own_dispositions_too": 1,
    "stage_order_is_mandatory": 1,
    "stage_order_skipped_marker": 1,
    "tell_each_agent_what_it_can_run": 5,
    "verification_is_by_fetch": 1,
    "verify_the_tasks_asserted_facts": 1,
    "worktree_is_compared_to_a_snapshot": 1,
    # MEASURED 2026-08-20. Both are single-paragraph blocks promoted out of
    # `build_draft_minor/update_pr.md` once `new_branch.md` became a second
    # consumer, so a one-line floor is the whole fragment — a shrink here is
    # a deletion, not a trim.
    "characterize_by_execution": 1,
    "can_it_fail_light_tier": 1,
}


def _substantive_lines(stem: str) -> int:
    body = (_SHARED / f"{stem}.md").read_text(encoding="utf-8")
    return len([ln for ln in body.split("\n") if len(ln.strip()) >= 40])


def test_no_PROMOTED_fragment_QUIETLY_LOSES_A_LINE() -> None:
    """Shared text can be deleted from every consumer at once, in one edit."""
    assert set(_FRAGMENT_FLOOR) == set(_PROMOTED), (
        f"the floor and the promoted set disagree; a fragment with no floor is "
        f"unguarded and a floor with no fragment asserts nothing. Only in the "
        f"floor: {sorted(set(_FRAGMENT_FLOOR) - set(_PROMOTED))}; only promoted:"
        f" {sorted(set(_PROMOTED) - set(_FRAGMENT_FLOOR))}"
    )
    shrunk = [f"{s}: {_substantive_lines(s)} lines, floor {n}"
              for s, n in sorted(_FRAGMENT_FLOOR.items())
              if _substantive_lines(s) < n]
    assert not shrunk, (
        "a shared fragment lost a substantive line, which removes it from EVERY "
        "consumer at once with no divergence for any drift detector to see:\n  "
        + "\n  ".join(shrunk)
        + "\n\nIf the deletion is intended, lower the floor in the same commit — "
          "that is the whole point of the number, and it makes the removal a "
          "decision somebody wrote down rather than a line that stopped existing."
    )


def test_the_supplier_reader_DISCRIMINATES() -> None:
    """Positive control for `_shared_prompt_stems`, on literal snippets.

    The walk above is exercised by every test in this module; the PREDICATE is
    not, and a predicate that started answering unconditionally would leave all
    of them green while checking nothing. Driven on source the tree does not
    contain, so it tests the question rather than today's answer.
    """
    loads = 'values = {"RULES": act.shared_prompt("rules")}'
    assert _shared_prompt_stems(ast.parse(loads), "<snippet>") == {"rules"}

    # A MENTION IS NOT A LOAD, and this is the arm that made the AST worth the
    # cost: `research_write_workflow` names a fragment inside a comment, and a
    # regex over the source reads that as a consumer loading it.
    mentioned = '# act.shared_prompt("rules")\nx = "act.shared_prompt(rules)"\n'
    assert _shared_prompt_stems(ast.parse(mentioned), "<snippet>") == set()

    # A DIFFERENT CALL IS NOT A LOAD.
    other = 'values = {"RULES": act.local_prompt("rules")}'
    assert _shared_prompt_stems(ast.parse(other), "<snippet>") == set()

    # A NON-LITERAL NAME FAILS RATHER THAN SHRINKING THE EXPECTED SET, which is
    # the direction that matters: a silently smaller expectation is a guard
    # getting quieter exactly where the code got harder to read.
    with pytest.raises(AssertionError, match="non-literal"):
        _shared_prompt_stems(ast.parse('v = act.shared_prompt(stem)'), "<snippet>")


# Fragments the module deliberately does not render-check, each with the reason.
# EMPTY, AND EMPTY IS THE INTENDED STEADY STATE — the same shape and the same
# rule as the pool derivation above: an entry here is a decision somebody wrote
# down, never a way to make the check below go quiet.
_NOT_RENDER_CHECKED: dict[str, str] = {}

# Every consumer this module DRIVES — meaning a test below RENDERS it and looks
# for each fragment in the result, not merely that a static scan can see the
# `shared_prompt()` call.
#
# `pfeat`/`pverify` joined 2026-08-19 with the first fragment promoted for the
# PLANNING family, and joined WITHOUT a fixture: the entry said "a static AST
# scan needs no fixture, only the module." That is true of the check below and
# false of the name — `_DRIVEN`'s whole meaning is that a rendered prompt was
# inspected, and the two planning modules were the only members of which that
# was not true, so `worktree_is_compared_to_a_snapshot` was reported as
# render-checked by nothing that rendered it. Clearing a guard's red by widening
# its population is the move this module's own header records twice; the
# fixture is `_planning_prompt` below and it cost nine lines.
_DRIVEN = (draft, draft_minor, refine, refine_minor, write, refresh,
           pfeat, pverify)


def _planning_prompt(tmp_path: Path, module, filename: str) -> str:
    """A planning child's prompt, rendered through its OWN `prompt_values`.

    Not a drive of the entrypoint: `prompt_values` is the seam both the live
    path and `--dry-run` render from (see its docstring), so rendering it here
    is the same string the dispatch builds, without a Temporal harness.
    """
    component = tmp_path / "docs" / "development" / "comp"
    component.mkdir(parents=True)
    (component / "roadmap.md").write_text("# roadmap\n")
    candidates = tmp_path / "docs" / "standards" / "architecture" / "research" / "candidates.md"
    candidates.parent.mkdir(parents=True)
    candidates.write_text("| id | finding |\n")
    values = module.prompt_values(component.relative_to(tmp_path),
                                  candidates.relative_to(tmp_path),
                                  tmp_path, None, "")
    return act.render(act.load_prompt(module.PROMPTS / filename), values,
                      opaque=frozenset({"TASK_CONTEXT"}))


@pytest.mark.parametrize(
    ("name", "module", "filename"),
    [("plan_feature", pfeat, "plan_feature.md"),
     ("plan_verify", pverify, "plan_verify.md")],
)
def test_a_planning_run_renders_EVERY_fragment_it_loads(
    tmp_path, name: str, module, filename: str
) -> None:
    """The fixture `_DRIVEN` was widened instead of gaining.

    Derived from the consumer's own loads for the same reason the draft-tier
    check is: a named subset stops covering the moment the consumer starts
    loading something new, and nothing says so.
    """
    prompt = _planning_prompt(tmp_path, module, filename)
    missing = sorted(s for s in _stems_loaded_by(module) if _needle(s) not in prompt)
    assert not missing, (
        f"{name} loads {missing} through shared_prompt() and renders without "
        f"them. A supplier built but never reaching the prompt leaves that run "
        f"on instructions the fragment's edits never touch."
    )


def test_every_POOL_fragment_is_render_checked_by_some_consumer() -> None:
    """The header comment above claims the whole pool is covered. This is that claim.

    WITHOUT IT THE CLAIM IS PROSE. Deriving `_PROMOTED` from the pool put every
    fragment under the deletion FLOOR, and it was read — by the pass that wrote
    it and by the lens that reviewed it — as putting every fragment under the
    RENDER checks too. It did not: those keyed off hand-maintained subsets, and
    the fragments the floor had just started guarding were rendered by nothing
    any assertion looked at. A promotion whose supplier never reaches a prompt
    is the exact failure this module exists for, so it is checked rather than
    asserted in a comment.

    THE DIRECTION OF FAILURE IS DELIBERATE. A fragment promoted for a consumer
    this module does not drive goes RED here, and that is the report wanted:
    the pool has consumers outside these — the planning family among them — and
    a fragment reaching only those is genuinely unverified by this module. The
    remedy is a fixture for that consumer, or an entry above with the reason.
    """
    checked: set[str] = set()
    for module in _DRIVEN:
        checked |= _stems_loaded_by(module)
    unchecked = sorted(set(_PROMOTED) - checked - set(_NOT_RENDER_CHECKED))
    assert not unchecked, (
        f"promoted and rendered by no consumer this module drives: {unchecked}. "
        f"The floor guards them against deletion and nothing guards them "
        f"against never arriving — add a fixture for the consumer that loads "
        f"them, or name them in _NOT_RENDER_CHECKED with the reason."
    )
    stale = sorted(set(_NOT_RENDER_CHECKED) - set(_PROMOTED))
    assert not stale, (
        f"excluded from render-checking but not in the pool: {stale}. An "
        f"exclusion that names nothing excuses nothing and hides the next one."
    )


def test_the_needles_are_real() -> None:
    """Vacuity guard: every assertion here is `needle in prompt`.

    A `_needle` that silently returned "" would make every membership check
    above pass against any string at all, and the PRODUCT-altitude check would
    then be the only one that failed — pointing at the wrong thing entirely.
    """
    assert _PROMOTED, (
        f"the pool glob matched nothing under {_SHARED} — every membership "
        f"assertion in this module would be vacuous. This replaces a literal "
        f"count, which was the same hand-maintained-figure defect that deriving "
        f"`_PROMOTED` exists to remove."
    )
    for stem in _PROMOTED:
        assert (_SHARED / f"{stem}.md").is_file(), f"prompts/{stem}.md is missing"
        n = _needle(stem)
        assert len(n) > 40, f"{stem}.md yielded a {len(n)}-char needle: {n!r}"

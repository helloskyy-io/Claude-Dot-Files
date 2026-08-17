"""A promoted prompt fragment must RENDER for every consumer, not merely have one.

WHY THIS IS NOT test_prompt_completeness. That module answers "does something
supply `${NAME}`?" by reading the consumer's source for the literal string
`"NAME"`. It is a text match, and it cannot see WHICH ARM supplies it. Nine
fragments were promoted in one change and two of their suppliers sit inside an
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

from pathlib import Path

import pytest

from modules.assistant import assistant_activities as act
from modules.assistant.build.build_draft import build_draft_workflow as draft
from modules.assistant.build.build_draft_minor import build_draft_minor_workflow as draft_minor
from modules.assistant.build.build_refine import build_refine_workflow as refine
from modules.assistant.build.build_refine_minor import build_refine_minor_workflow as refine_minor
from modules.assistant.research import research_activities as ract
from modules.assistant.research.research_refresh import research_refresh_workflow as refresh
from modules.assistant.research.research_write import research_write_workflow as write

_SHARED = Path(__file__).resolve().parents[2] / "modules" / "assistant" / "prompts"

# A distinctive sentence from each fragment promoted by this change, keyed by
# stem. Read from the FILE rather than pasted here: a copy would drift, and a
# drifted needle turns every assertion below into a permanent pass.
_PROMOTED = [
    "build_from_plan",
    "stages_1_to_4_from_plan",
    "fidelity_premise",
    "fidelity_needs_a_separate_run",
    "resolve_disposition_authority",
    "resolve_closed_disposition_list",
    "resolve_fix_by_default",
    "verify_and_ci_gate",
    "altitude_component",
]


def _needle(stem: str) -> str:
    """The longest line of a fragment — distinctive enough to locate it in a prompt.

    Skips the `<!-- SHARED -->` editor header, which is commentary about the
    fragment rather than its substance, and skips placeholder-only lines, which
    are gone by the time the prompt is rendered.
    """
    lines = [
        ln.strip()
        for ln in (_SHARED / f"{stem}.md").read_text().splitlines()
        if ln.strip() and not ln.lstrip().startswith(("<!--", "-->", "     "))
        and "${" not in ln
    ]
    assert lines, f"{stem}.md yielded no usable needle — the fragment is empty or all placeholders"
    return max(lines, key=len)


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


@pytest.mark.parametrize(
    ("name", "entry"),
    [("build_draft", draft.run_draft), ("build_draft_minor", draft_minor.run_draft_minor)],
)
def test_a_plan_driven_draft_renders_both_shared_prompts(
    monkeypatch, tmp_path, name: str, entry
) -> None:
    prompt = _draft_prompt(monkeypatch, tmp_path, entry)
    for stem in ("build_from_plan", "stages_1_to_4_from_plan"):
        assert _needle(stem) in prompt, (
            f"{name}'s plan-driven prompt does not contain prompts/{stem}.md. Both "
            f"draft tiers load it through shared_prompt(); if one stopped, that "
            f"tier is running on a prompt the other tier's edits never reach."
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


# --- build: the refine pair's six fragments -----------------------------------

_REFINE_FRAGMENTS = [
    "fidelity_premise", "fidelity_needs_a_separate_run",
    "resolve_disposition_authority", "resolve_closed_disposition_list",
    "resolve_fix_by_default", "verify_and_ci_gate",
]


@pytest.mark.parametrize(
    ("name", "entry"),
    [("build_refine", refine.run_refine),
     ("build_refine_minor", refine_minor.run_refine_minor)],
)
def test_a_refine_pass_renders_all_six_shared_fragments(
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
    assert _needle("altitude_component") in prompt, (
        f"{name} at COMPONENT altitude renders without prompts/altitude_component.md, "
        f"so the run is not told the lane rules that bound what it may write."
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
    assert _needle("altitude_component") not in prompt, (
        f"{name} at PRODUCT altitude renders the COMPONENT lane rules. The "
        f"supplier has become unconditional."
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


def test_the_needles_are_real(monkeypatch) -> None:
    """Vacuity guard: every assertion here is `needle in prompt`.

    A `_needle` that silently returned "" would make every membership check
    above pass against any string at all, and the PRODUCT-altitude check would
    then be the only one that failed — pointing at the wrong thing entirely.
    """
    assert len(_PROMOTED) == 9, "the promoted set changed; update this module"
    for stem in _PROMOTED:
        assert (_SHARED / f"{stem}.md").is_file(), f"prompts/{stem}.md is missing"
        n = _needle(stem)
        assert len(n) > 40, f"{stem}.md yielded a {len(n)}-char needle: {n!r}"

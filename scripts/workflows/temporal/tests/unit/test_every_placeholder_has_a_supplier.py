"""Every `${PLACEHOLDER}` a prompt consumes is supplied by whoever renders it.

WHY THIS EXISTS, AND IT COST A WHOLE PLANNING RUN. `act.render` raises on a
placeholder it cannot fill — correctly, since an unsubstituted `${NAME}` reaches
the model as an instruction about a variable. But it raises at DISPATCH TIME,
which for `review-pr` is after `plan-draft`, `plan-refine` and `plan-sprint` have
all completed and opened a PR. MDC PR #204: three children succeeded, the plan
landed, and the run exited 1 at the review stage with
`unsubstituted prompt placeholders: ['${SIMILAR_CANDIDATES}']`. **The expensive
authoring work all landed; the one stage that would judge it never ran.**

WHAT MADE IT INVISIBLE: the full suite passed between the two edits that caused
it. A placeholder was added to a prompt in one change and its supplier added to
the renderer in another, and NOTHING RENDERED THE TWO TOGETHER. Every existing
test either drives a workflow with its own stubs or reads a prompt as text.

THE TRANSITIVE CASE IS THE ONE THAT BIT. `render` loops to convergence, so a
shared fragment inserted as a VALUE can carry its own placeholders — and those
must be supplied by whoever renders the fragment's HOST, not by the fragment.
`filing_a_candidate_row.md` consumes `${SIMILAR_CANDIDATES}`; its hosts are
`plan-draft` and `plan-refine`, and they are the modules that must supply it.

WHAT THIS DOES NOT DO: it does not check that a value is CORRECT, only that one
exists. A wrong path still ships; an absent key cannot.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_ASSISTANT = Path(__file__).resolve().parents[2] / "modules" / "assistant"

_PLACEHOLDER = re.compile(r"\$\{([A-Z_]+)\}")
# `"KEY":` inside a values dict, and `shared_prompt("stem")` / `load_prompt(... "x.md")`
_SUPPLIED = re.compile(r'"([A-Z_]+)"\s*:')
_FRAGMENT = re.compile(r'shared_prompt\("([a-z_]+)"\)')
_OWN_PROMPT = re.compile(r'PROMPTS\s*/\s*"([a-z0-9_]+\.md)"')


def _renderers() -> list[Path]:
    """Modules that build a values dict AND name at least one prompt."""
    out = []
    for p in sorted(_ASSISTANT.rglob("*_workflow.py")):
        src = p.read_text(encoding="utf-8")
        if _OWN_PROMPT.search(src) and _SUPPLIED.search(src):
            out.append(p)
    return out


def _placeholders_of(path: Path) -> set[str]:
    return set(_PLACEHOLDER.findall(path.read_text(encoding="utf-8"))) if path.is_file() else set()


@pytest.mark.parametrize("module", _renderers(), ids=lambda p: p.stem)
def test_every_placeholder_the_module_renders_has_a_value(module: Path) -> None:
    src = module.read_text(encoding="utf-8")
    supplied = set(_SUPPLIED.findall(src))

    need: set[str] = set()
    prompts_dir = module.parent / "prompts"
    for name in set(_OWN_PROMPT.findall(src)):
        need |= _placeholders_of(prompts_dir / name)
    for stem in set(_FRAGMENT.findall(src)):
        need |= _placeholders_of(_ASSISTANT / "prompts" / f"{stem}.md")

    missing = sorted(need - supplied)
    assert not missing, (
        f"{module.name} renders prompt(s) consuming {missing} and supplies no value for "
        f"them. `act.render` raises at DISPATCH time, which for a late child is after "
        f"every earlier child has already run and spent its money — MDC PR #204 lost its "
        f"whole review stage to exactly this, with the plan already written and pushed. "
        f"Either add the key to this module's values dict, or remove the placeholder from "
        f"the prompt.\n"
        f"  consumed: {sorted(need)}\n"
        f"  supplied: {sorted(supplied)}"
    )


def test_the_walk_found_the_renderers_it_audits() -> None:
    """Vacuity floor: an empty population makes every assertion above trivially true."""
    mods = _renderers()
    assert len(mods) >= 6, (
        f"the walk found {len(mods)} renderer(s); the tree carries at least six "
        f"(plan-draft, plan-refine, plan-sprint, triage-candidates, research-draft, "
        f"research-refine). If the shape moved, move this recogniser."
    )


@pytest.mark.parametrize("src,prompt_text,expected_missing", [
    # supplies what it consumes
    ('values = {"PR_NUMBER": x}\nact.render(act.load_prompt(PROMPTS / "a.md"), values)',
     "hello ${PR_NUMBER}", []),
    # consumes one it does not supply — the #204 shape
    ('values = {"PR_NUMBER": x}\nact.render(act.load_prompt(PROMPTS / "a.md"), values)',
     "hello ${PR_NUMBER} and ${SIMILAR_CANDIDATES}", ["SIMILAR_CANDIDATES"]),
    # a prompt with no placeholders can never fail
    ('values = {"PR_NUMBER": x}\nact.render(act.load_prompt(PROMPTS / "a.md"), values)',
     "no placeholders here", []),
])
def test_the_recogniser_answers_correctly_on_a_literal(
        tmp_path: Path, src: str, prompt_text: str, expected_missing: list[str]) -> None:
    """The predicate above, driven on snippets rather than only on the tree.

    Without this the walk passes trivially the moment either regex stops matching
    — and a guard that reports "no missing placeholders" for a tree full of them
    is worse than no guard.
    """
    (tmp_path / "a.md").write_text(prompt_text, encoding="utf-8")
    supplied = set(_SUPPLIED.findall(src))
    need: set[str] = set()
    for name in set(_OWN_PROMPT.findall(src)):
        need |= _placeholders_of(tmp_path / name)
    assert sorted(need - supplied) == expected_missing

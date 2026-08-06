"""PROMPT COMPLETENESS — every ${VAR} in a shipped prompt has a supplier.

Three prompt bodies once shipped MISSING behind 46 passing assertions, and a run
then completed cleanly on two-thirds of its instructions. Exit 0 is not evidence
a prompt arrived intact; only a check against the source is.

MIGRATION-SCOPED: the reference is the bash original, so this retires with it.

The cases are enumerated at COLLECTION time — one test per (prompt, placeholder)
pair rather than one test for all of them. A single failure then names the exact
prompt and the exact variable, and the remaining pairs still run instead of
being masked by the first one to fail.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_ASSISTANT = Path(__file__).resolve().parents[2] / "modules" / "assistant"
_PLACEHOLDER = re.compile(r"\$\{([A-Z_][A-Z_0-9]*)\}")


def _prompts() -> list[Path]:
    return sorted(_ASSISTANT.rglob("prompts/*.md"))


def _rel(prompt: Path) -> str:
    return str(prompt).split("modules/assistant/")[-1]


def _placeholders(prompt: Path) -> list[str]:
    return sorted(set(_PLACEHOLDER.findall(prompt.read_text())))


def _has_a_supplier(prompt: Path, name: str) -> bool:
    """A supplier is either the workflow beside it or a promoted shared prompt.

    Kept as a named predicate so the positive control below can prove it fires.
    """
    workflow_dir = prompt.parent.parent
    source = (
        "".join(f.read_text() for f in workflow_dir.glob("*.py"))
        if workflow_dir.exists()
        else ""
    )
    shared = {p.stem.upper() for p in (_ASSISTANT / "prompts").glob("*.md")}
    sibling = {p.stem.upper() for p in prompt.parent.glob("*.md")}
    return (f'"{name}"' in source) or (name in shared) or (name in sibling)


def _supplier_cases() -> list:
    return [
        pytest.param(prompt, name, id=f"{_rel(prompt)}-{name}")
        for prompt in _prompts()
        for name in _placeholders(prompt)
    ]


def _stage_body_cases() -> list:
    return [
        pytest.param(prompt, name, id=f"{_rel(prompt)}-{name}")
        for prompt in _prompts()
        for name in _placeholders(prompt)
        if name.startswith("STAGES_")
    ]


def test_prompts_were_actually_discovered() -> None:
    """Loud failure on an empty sweep.

    Testing Standard § Tier Enforcement: a runner that finds no files and exits
    zero is indistinguishable from a passing run. This whole module is
    data-driven off an rglob — if the tree moves, every parametrised test below
    silently collects zero cases and reports green while checking nothing.
    """
    prompts = _prompts()
    assert prompts, (
        f"no prompts found under {_ASSISTANT}/**/prompts/*.md — the prompt tree "
        "moved and this suite is now asserting nothing"
    )
    assert _supplier_cases(), (
        "prompts were found but none contain a ${PLACEHOLDER} — either the "
        "placeholder syntax changed or the prompts lost their substitutions"
    )


@pytest.mark.parametrize(("prompt", "name"), _supplier_cases())
def test_every_placeholder_has_a_supplier(prompt: Path, name: str) -> None:
    assert _has_a_supplier(prompt, name), (
        f"{_rel(prompt)} references ${{{name}}} but nothing supplies it: not the "
        f"workflow at {prompt.parent.parent.name}/*.py, not a promoted shared "
        f"prompt, not a sibling .md. An unsupplied placeholder either reaches the "
        f"model as literal text or trips render()'s leftover guard at dispatch time."
    )


@pytest.mark.parametrize(("prompt", "name"), _stage_body_cases())
def test_referenced_stage_body_exists_beside_the_wrapper(prompt: Path, name: str) -> None:
    """A wrapper prompt that references a stage body must find that body present.

    The workflow may select a VARIANT (stages_1_to_4_from_plan.md), so the
    requirement is a file whose stem STARTS WITH the placeholder name, not an
    exact match.
    """
    candidates = sorted(f.name for f in prompt.parent.glob("*.md"))
    assert any(f.stem.startswith(name.lower()) for f in prompt.parent.glob("*.md")), (
        f"{_rel(prompt)} references ${{{name}}} but no {name.lower()}*.md body "
        f"sits beside it. Present in that directory: {candidates}. This is the "
        f"exact shape of the failure where three prompt bodies shipped missing "
        f"and the run completed on two-thirds of its instructions."
    )


def test_supplier_predicate_positive_control(tmp_path: Path) -> None:
    """Positive control for the structural check above.

    A predicate that reads source text can stop matching (a rename, a moved
    file, a changed quoting style) and become a permanent pass. This proves it
    still distinguishes supplied from unsupplied.
    """
    workflow_dir = tmp_path / "some_workflow"
    prompts_dir = workflow_dir / "prompts"
    prompts_dir.mkdir(parents=True)
    (workflow_dir / "some_workflow.py").write_text('values = {"PR_NUMBER": pr}\n')
    target = prompts_dir / "body.md"
    target.write_text("PR is ${PR_NUMBER} and ${NOBODY_SUPPLIES_THIS}\n")

    assert _placeholders(target) == ["NOBODY_SUPPLIES_THIS", "PR_NUMBER"]
    assert _has_a_supplier(target, "PR_NUMBER") is True
    assert _has_a_supplier(target, "NOBODY_SUPPLIES_THIS") is False

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

from modules.assistant import assistant_activities as _act
from modules.assistant.review_pr import review_pr_helper as _review_helper

_ASSISTANT = Path(__file__).resolve().parents[2] / "modules" / "assistant"
_PLACEHOLDER = re.compile(r"\$\{([A-Z_][A-Z_0-9]*)\}")


def _prompts() -> list[Path]:
    return sorted(_ASSISTANT.rglob("prompts/*.md"))


def _rel(prompt: Path) -> str:
    return str(prompt).split("modules/assistant/")[-1]


def _placeholders(prompt: Path) -> list[str]:
    return sorted(set(_PLACEHOLDER.findall(prompt.read_text())))


def _consumers_of_shared(stem: str) -> list[Path]:
    """Every workflow that loads the shared fragment `stem`.

    A shared fragment has NO workflow beside it, so "the directory it sits in"
    cannot answer who supplies its placeholders. Its consumers are whoever calls
    `shared_prompt("<stem>")`, and there is more than one by definition —
    otherwise it would not have been promoted (§10.1).
    """
    needle = f'shared_prompt("{stem}")'
    return [f for f in _ASSISTANT.rglob("*.py") if needle in f.read_text()]


def _has_a_supplier(prompt: Path, name: str) -> bool:
    """A supplier is either the workflow beside it or a promoted shared prompt.

    Kept as a named predicate so the positive control below can prove it fires.

    A SHARED FRAGMENT IS THE STRICTER CASE, and it arrived with
    `altitude_product.md` (issue #91) — the first promoted prompt to carry any
    placeholder at all. EVERY workflow that loads it must supply them, not just
    one somewhere in the tree: a fragment supplied by one consumer and not
    another renders with a live `${...}` in the second, and `render()` raises at
    dispatch time rather than here.
    """
    if prompt.parent == _ASSISTANT / "prompts":
        consumers = _consumers_of_shared(prompt.stem)
        return bool(consumers) and all(
            f'"{name}"' in f.read_text() for f in consumers
        )
    workflow_dir = prompt.parent.parent
    source = (
        "".join(f.read_text() for f in workflow_dir.glob("*.py"))
        if workflow_dir.exists()
        else ""
    )
    shared = {p.stem.upper() for p in (_ASSISTANT / "prompts").glob("*.md")}
    sibling = {p.stem.upper() for p in prompt.parent.glob("*.md")}
    return (f'"{name}"' in source) or (name in shared) or (name in sibling)


def _stage_body_present(prompt: Path, name: str) -> bool:
    """True when a body file for `${name}` sits beside the wrapper that references it.

    The workflow may select a VARIANT (`stages_1_to_4_from_plan.md`), so the
    requirement is a file whose stem STARTS WITH the placeholder name, not an
    exact match.

    Kept as a named predicate so the positive control below can prove it fires.
    """
    return any(f.stem.startswith(name.lower()) for f in prompt.parent.glob("*.md"))


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
    """A wrapper prompt that references a stage body must find that body present."""
    candidates = [f.name for f in sorted(prompt.parent.glob("*.md"))]
    assert _stage_body_present(prompt, name), (
        f"{_rel(prompt)} references ${{{name}}} but no {name.lower()}*.md body "
        f"sits beside it. Present in that directory: {candidates}. This is the "
        f"exact shape of the failure where three prompt bodies shipped missing "
        f"and the run completed on two-thirds of its instructions."
    )


def test_stage_body_predicate_positive_control(tmp_path: Path) -> None:
    """Positive control for the structural check above.

    Testing Standard § Structural tests need a positive control. This predicate
    only ever runs against real, already-conforming prompt directories, so
    nothing else here would notice if it stopped discriminating — a changed
    variant-naming convention or a moved prompts directory would turn it into a
    permanent pass, which is the same hollow-green the module exists to prevent.

    The probe reproduces the original defect: a wrapper that references a stage
    body with no such body beside it.
    """
    prompts_dir = tmp_path / "some_workflow" / "prompts"
    prompts_dir.mkdir(parents=True)
    wrapper = prompts_dir / "wrapper.md"
    wrapper.write_text("do the work\n${STAGES_1_TO_4}\n")

    # The body is MISSING — the predicate must say so.
    assert _stage_body_present(wrapper, "STAGES_1_TO_4") is False

    # A VARIANT stem satisfies it; an exact match is not required.
    (prompts_dir / "stages_1_to_4_from_plan.md").write_text("the stage body\n")
    assert _stage_body_present(wrapper, "STAGES_1_TO_4") is True

    # An unrelated body does not satisfy it — the predicate must not be matching
    # "any .md beside the wrapper", which is how a startswith check silently
    # degrades into a directory-is-non-empty check.
    assert _stage_body_present(wrapper, "STAGES_5_TO_7") is False


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


# --- The leftover guard, in BOTH renderers -----------------------------------
#
# The supplier checks above are static: they read prompts off disk. This section
# covers the dispatch-time backstop — the guard that refuses to hand a prompt to
# the model while a `${NAME}` is still literal in it.
#
# There are two renderers, and the guard is written out twice. It was wrong in
# both: `[A-Z_]+` does not match a digit, so `${STAGES_1_TO_4}` slipped past and
# a prompt shipped with its entire stage body replaced by the placeholder's own
# name — a run that reported success on roughly 8kB of missing instructions.
# `assistant_activities.render` was corrected; the review-pr copy was not, and
# stayed latent only because review-pr's own placeholders happen to be
# digit-free. Both are exercised below with the SAME digit-bearing name, since
# the failure was never that one of them was wrong — it was that they differed.

_DIGIT_BEARING = "${STAGES_1_TO_4}"


def test_shared_render_catches_a_digit_bearing_placeholder() -> None:
    with pytest.raises(ValueError, match="unsubstituted prompt placeholders"):
        _act.render(f"do the work\n{_DIGIT_BEARING}\n", {"PR_NUMBER": "31"})


def test_review_pr_render_catches_a_digit_bearing_placeholder() -> None:
    with pytest.raises(ValueError, match="unsubstituted prompt placeholders"):
        _review_helper.render_prompt(
            f"review PR ${{PR_NUMBER}}\n{_DIGIT_BEARING}\n",
            pr_number="31",
            pr_branch="build/x",
            this_pass=1,
            prior_pass=0,
            headless_guard="guard",
            run_id="deadbeef",
        )


@pytest.mark.parametrize(
    ("render_name", "render_call"),
    [
        pytest.param("assistant_activities.render",
                     lambda t: _act.render(t, {"PR_NUMBER": "31"}), id="shared"),
        pytest.param("review_pr_helper.render_prompt",
                     lambda t: _review_helper.render_prompt(
                         t, pr_number="31", pr_branch="build/x",
                         this_pass=1, prior_pass=0, headless_guard="guard",
                         run_id="deadbeef"),
                     id="review-pr"),
    ],
)
def test_a_fully_substituted_prompt_is_not_rejected(render_name: str, render_call) -> None:
    """Negative control for the two guards above.

    A guard that raised on everything would pass both digit tests while making
    every dispatch impossible. This proves each still lets a clean prompt
    through — and that the digit-aware pattern did not start matching the
    literal `$` and `{` that these prompts are full of.
    """
    clean = 'review PR ${PR_NUMBER} — the JSON is {"a": 1} and the shell is ${\n'
    out = render_call(clean)
    assert "31" in out, f"{render_name} did not substitute a supplied placeholder"


def test_the_review_pr_dry_run_renders_the_real_prompt(monkeypatch, tmp_path) -> None:
    """THE ZERO-SPEND PRE-FLIGHT MUST ACTUALLY RUN, and a signature change broke it.

    `--dry-run` is the only way to check review-pr's plumbing without a live
    dispatch, which matters most while the phase's remaining work IS live
    dispatches at real budget. Adding a required `run_id` to `render_prompt`
    updated the workflow and both test call sites and not `_dry_run`'s — and
    because the divergence is a TypeError rather than a wrong result, the CLI's
    error handler did not catch it either: the operator got a traceback.

    `run_review`'s own docstring already records this exact dry-run/real-path
    drift happening once before. A placeholder-supplier check over the prompt
    body cannot see it; only executing the path can, which is why this test
    calls `_dry_run` rather than asserting on its source.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    import run_review_pr as kickoff
    from modules.assistant.review_pr.review_pr_helper import ReviewInput

    monkeypatch.setattr(kickoff.act, "fetch_pr", lambda *a, **k: {
        "headRefName": "build/x", "state": "OPEN", "title": "t"})
    monkeypatch.setattr(kickoff.act, "count_prior_passes", lambda *a, **k: 0)

    assert kickoff._dry_run(ReviewInput(pr_number="31"), tmp_path) == 0

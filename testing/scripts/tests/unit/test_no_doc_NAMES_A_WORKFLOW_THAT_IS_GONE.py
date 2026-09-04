"""Every workflow script an operator-facing doc names must actually exist.

THE FAILURE THIS IS WRITTEN FROM. `config/commands/get-started.md` is what
`config/rules/personal-tooling.md` tells every session to read first, and on
2026-09-04 it still advertised the hyphenated bash fleet. A PM in another repo
followed it exactly, dispatched `build-phase.sh`, and spent a 196-turn run
against a stage whose agent roster named two agents that had been consolidated
away three weeks earlier. Nothing was broken in the sense of throwing — the doc
was simply describing a fleet that was being retired, and it was the only map
anyone had.

WHY THE PREDICATE IS "RESOLVES", NOT "IS NOT V1". Three bash workflows —
`plan-new.sh`, `review-runs.sh`, `review-sprint.sh` — have no Python successor
and are still the right thing to dispatch, so a ban on the old tree would fail
on correct docs. And the inverse ban is equally wrong: `build.sh` and
`research.sh` exist in BOTH trees. The property that actually distinguishes a
good doc from the one that misrouted a run is whether the name resolves to a
file, so that is what this checks. It keeps working through the next deletion
without being re-aimed, which the previous doc sweep did not.

SCOPE. Operator-facing surfaces only — `config/` and `docs/`. Prompts under
`scripts/workflows/temporal/` are swept by
`test_no_prompt_ROUTES_the_model_into_the_FROZEN_fleet.py`, which asks a
different question (does this referent resolve ONLY in the frozen tree) against
a different population. Two sweeps, two properties, deliberately not merged:
that one may forgive a name this one must reject, once the frozen tree is empty.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
BASH_DIR = REPO_ROOT / "scripts" / "workflows"
SHIM_DIR = BASH_DIR / "temporal" / "scripts"

# A workflow name, not any shell script: hooks, test runners and helpers live
# elsewhere and are named the same way, so the check is anchored to the two
# directories that hold dispatchable workflows rather than to the `.sh` suffix.
_NAME = re.compile(r"\b([a-z][a-z0-9]*(?:[-_][a-z0-9]+)*\.sh)\b")

SURFACES = sorted(
    p for d in ("config", "docs")
    for p in (REPO_ROOT / d).rglob("*.md")
    # Relative to the repo root — see the sibling agent sweep for why an absolute
    # substring test blanks the population inside a worktree.
    if ".claude/worktrees/" not in p.relative_to(REPO_ROOT).as_posix()
)


def _resolves(name: str) -> bool:
    return (BASH_DIR / name).is_file() or (SHIM_DIR / name).is_file()


# A RETIRED SCRIPT WHOSE SUCCESSOR IS NOT A SAME-STEM FILE, and the reason this
# map exists rather than the twin rule alone. `build-phase.sh` did not become
# `build_phase.sh` — it became a FLAG, `build.sh --phase`. The twin rule cannot
# see that, and `build-phase.sh` is the exact script that misrouted the run this
# module was written from: the first draft of this sweep passed on it.
#
# Keep this SMALL. Every same-stem rename is caught by the twin rule with no
# entry here; a name earns a row only when its successor changed shape.
RETIRED_WITHOUT_A_TWIN = {
    "build-phase.sh": "build.sh --phase",
}


def _known_workflow_names() -> set[str]:
    """Every name either tree currently offers — the vocabulary a doc may use."""
    return {p.name for p in BASH_DIR.glob("*.sh")} | {p.name for p in SHIM_DIR.glob("*.sh")}


def _successor_of(name: str, known: set[str]) -> str | None:
    """What a reader should use instead, or None if the name is not retired."""
    if name in RETIRED_WITHOUT_A_TWIN:
        return RETIRED_WITHOUT_A_TWIN[name]
    twin = name[:-3].replace("-", "_") + ".sh"
    return twin if twin != name and twin in known else None


def _paragraphs(text: str) -> list[str]:
    return [b for b in text.split("\n\n") if b.strip()]


def _dangling(text: str) -> list[str]:
    """Names that LOOK like a workflow this repo ships, but resolve to nothing.

    Keyed on the retired-name shape rather than on every `.sh` token: a doc may
    legitimately mention `run-all.sh`, `block-dangerous.sh` or some third-party
    script, and none of those is this sweep's business. A token counts only if a
    same-stem workflow exists in either tree under the OTHER separator — which
    is exactly what a rename leaves behind, and exactly what stranded the run.
    """
    known = _known_workflow_names()
    out = []
    for block in _paragraphs(text):
        for m in sorted(set(_NAME.findall(block))):
            if _resolves(m):
                continue
            successor = _successor_of(m, known)
            if successor is None:
                continue
            # A RETIREMENT NOTE IS THE OPPOSITE OF A MISROUTE, and this repo now
            # ships several. `personal-tooling.md` has to write the words
            # "build-phase.sh no longer exists" to say so, and the first version
            # of this guard failed on the very rule announcing the deletion.
            # Naming the successor in the same paragraph is the discriminator:
            # a reader of that paragraph is told where to go, which is exactly
            # what the misrouting doc failed to do.
            if successor in block:
                continue
            label = "now" if m in RETIRED_WITHOUT_A_TWIN else "renamed"
            out.append(f"{m} ({label}: {successor})")
    return sorted(set(out))


def test_the_two_trees_are_where_this_module_looks() -> None:
    """Vacuity floor. An empty population is an absent test, not a passing one."""
    assert SURFACES, "no markdown found under config/ or docs/"
    assert _known_workflow_names(), (
        f"neither {BASH_DIR} nor {SHIM_DIR} offers a workflow — if the fleet moved, "
        f"re-aim this module rather than letting it forgive everything."
    )


@pytest.mark.parametrize("path", SURFACES, ids=lambda p: p.name)
def test_no_doc_names_a_workflow_that_does_not_exist(path: Path) -> None:
    bad = _dangling(path.read_text(encoding="utf-8"))
    assert not bad, (
        f"{path.relative_to(REPO_ROOT)} names {bad} — the file does not exist, but a "
        f"same-stem workflow does under the other separator. An operator following "
        f"this doc gets 'no such file'. The Python fleet uses UNDERSCORES and lives "
        f"in {SHIM_DIR.relative_to(REPO_ROOT)}; `build-phase.sh` specifically became "
        f"`build.sh --phase`."
    )


@pytest.mark.parametrize(
    "text,expected",
    [
        ("dispatch build-minor.sh --pr 1", ["build-minor.sh (renamed: build_minor.sh)"]),
        ("dispatch plan-revision.sh now", ["plan-revision.sh (renamed: plan_revision.sh)"]),
        # THE ONE THAT GOT PAST THE FIRST DRAFT — no same-stem twin exists.
        ("dispatch build-phase.sh plan.md", ["build-phase.sh (now: build.sh --phase)"]),
        # SURVIVORS — no Python successor, so naming them is correct.
        ("run plan-new.sh for greenfield", []),
        ("run review-sprint.sh at sprint end", []),
        # SHARED NAMES — resolve in the shim tree; a ban on `.sh` would fail here.
        ("dispatch build.sh and research.sh", []),
        # NOT WORKFLOWS — hooks and runners are named alike and are out of scope.
        ("testing/run-all.sh and block-dangerous.sh", []),
        # A RETIREMENT NOTE names the dead script AND its successor — allowed.
        ("`build-phase.sh` no longer exists; use `build.sh --phase <plan>`.", []),
        ("plan-revision.sh was renamed to plan_revision.sh.", []),
        # ...but only when the successor is actually there to be read.
        ("plan-revision.sh was renamed.\n\nplan_revision.sh is elsewhere.",
         ["plan-revision.sh (renamed: plan_revision.sh)"]),
    ],
)
def test_the_RESOLUTION_PREDICATE_discriminates(text: str, expected: list[str]) -> None:
    """Positive AND negative controls.

    Without the negative arms this would be indistinguishable from a ban on
    naming any script, which would fail on the survivors and on the two names
    that legitimately exist in both trees.
    """
    assert _dangling(text) == expected

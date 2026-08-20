"""No shipped prompt may name a workflow that exists only in the frozen fleet.

`config/rules/personal-tooling.md` is unambiguous: `scripts/workflows/*.sh` is
FROZEN REFERENCE kept only as a backup while the Python fleet is built, the
operator deletes it when it stops being needed, and the Python fleet may not
depend on it. A prompt that names one of those scripts hands the model — or the
operator reading the model's output — a command that routes into the frozen tree
today and names NOTHING after the deletion.

THIS IS A CLASS AND IT HAS BEEN CLOSED ONE SPELLING AT A TIME, THREE TIMES:

  * `plan_revision/prompts/stages_1_to_5.md` carried a STOP recommending
    `plan-revision.sh`, `build-minor.sh` or `build.sh`. Repaired, with the
    reasoning recorded in `test_plan_revision_v1_parity.SUPERSEDED_V1_LINES`.
  * `modules/assistant/prompts/build_from_plan.md` — the wrapper BOTH draft
    tiers render on the plan path — opened *"You are executing the BUILD-PHASE
    workflow"* and asked for a `build-phase:` PR title. There is no `build_phase`
    module anywhere under `temporal/`; `build-phase.sh` is frozen-only. Repaired
    by parameterising tier identity per tier.
  * `review_pr/prompts/disposition.md` named `build-minor.sh` and
    `plan-revision.sh` in its sizing table and in the `dispatch_tool` enum every
    review emits — so the workflow that HOLDS other PRs for this exact defect was
    asking its own reviewer to emit the referent it enforces against.

Each was found by a human sweep, each fix closed its instances, and the next
sweep found the next spelling. Enumerating instances does not converge; keying
the check on the CLASS does.

THE PREDICATE IS RESOLUTION, NOT A STRING MATCH, and that distinction is
load-bearing in BOTH directions. The Python fleet's own shims are spelled with
UNDERSCORES — `scripts/build_minor.sh`, `scripts/plan_revision.sh` — while the
frozen fleet uses hyphens, and some names (`build.sh`, `research.sh`) exist in
BOTH trees. So a ban on any `.sh` referent would reject four correct prompts, and
a ban on hyphens alone would miss a frozen-only name that happens to have none. A
referent is a violation exactly when it resolves under the frozen directory and
does NOT resolve under the Python shim directory.

WHAT THIS DOES NOT LOOK AT: prompt text that lives in a PYTHON string rather
than a `.md` file — `build_refine`'s `CORRECTION_NOTE` is the live example.
Widening the population to `.py` would also sweep in module docstrings, and two
of those legitimately name their V1 script to record what the module is a port
OF (`plan_revision_workflow`, `research_refresh_workflow`). Telling a
model-facing string from an engineer-facing docstring needs data flow, so the
boundary is drawn at the file type and stated here rather than left implicit. The
failure direction is that a frozen referent added to an inline prompt string
escapes, not that a correct file is blocked.

Also not looked at: a prompt naming a script that exists in NEITHER tree
(a typo, or a script in a target repo like `testing/run-all.sh`) is out of scope —
this is about the frozen fleet specifically, and a general "every named script
exists" check would have to know which repo each prompt runs against. It also
cannot see a referent assembled at runtime from a placeholder, which is the
correct outcome: `${TIER_PREFIX}` is supplied per tier and each supplied value is
`WORKFLOW_KEY`-derived, so it cannot name a script at all.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

TEMPORAL = Path(__file__).resolve().parents[2]
REPO_ROOT = TEMPORAL.parents[2]

#: The frozen bash fleet. `personal-tooling.md`: reference only, deleted when unused.
FROZEN_DIR = REPO_ROOT / "scripts" / "workflows"
#: The Python fleet's own operator-facing shims.
SHIM_DIR = TEMPORAL / "scripts"

PROMPT_ROOT = TEMPORAL / "modules" / "assistant"

_SCRIPT = re.compile(r"\b([a-z][a-z0-9_-]*\.sh)\b")


def _frozen_only() -> set[str]:
    frozen = {p.name for p in FROZEN_DIR.glob("*.sh")}
    shims = {p.name for p in SHIM_DIR.glob("*.sh")}
    return frozen - shims


FROZEN_ONLY = _frozen_only()
PROMPTS = sorted(PROMPT_ROOT.rglob("*.md"))


def test_both_trees_are_where_this_module_looks() -> None:
    """Vacuity floor, and the retirement notice for this whole module.

    If `FROZEN_ONLY` is empty the check below passes over everything, which is
    ambiguous between two very different worlds: the frozen fleet was DELETED —
    in which case this module has done its job and should be deleted with it —
    and the glob stopped matching. Failing here says which, rather than going
    quietly green.
    """
    assert PROMPTS, f"no prompt files found under {PROMPT_ROOT}"
    assert (FROZEN_DIR / "build.sh").is_file(), (
        f"{FROZEN_DIR} no longer holds the frozen fleet. If the operator has "
        f"deleted it, delete this module too — a check with no population is not "
        f"a passing test, it is an absent one."
    )
    assert FROZEN_ONLY, (
        "every frozen script now has a same-named Python shim, so this check "
        "forgives everything. Confirm that is really true before deleting it."
    )


@pytest.mark.parametrize("path", PROMPTS, ids=lambda p: p.name)
def test_no_prompt_names_a_FROZEN_ONLY_script(path: Path) -> None:
    """A referent resolving only under the frozen tree is the violation."""
    named = sorted({m for m in _SCRIPT.findall(path.read_text()) if m in FROZEN_ONLY})
    assert not named, (
        f"{path.relative_to(TEMPORAL)} names {named}, which resolve ONLY under "
        f"{FROZEN_DIR.relative_to(REPO_ROOT)} — the FROZEN fleet. "
        f"`config/rules/personal-tooling.md` forbids the Python fleet depending "
        f"on it and records that the operator deletes it, so this prompt hands "
        f"the model a command that names nothing after that deletion. The Python "
        f"shims are the same names with UNDERSCORES, in "
        f"{SHIM_DIR.relative_to(REPO_ROOT)}."
    )


def test_the_RESOLUTION_PREDICATE_discriminates() -> None:
    """Positive control: it must fire on a frozen-only name and NOT on a shared one.

    A ban on any `.sh` referent would look identical to this check on a clean
    tree and would be wrong on four live prompts — `build.sh` and `research.sh`
    exist in BOTH trees and are correct referents. Asserting the negative arm is
    what distinguishes the two.
    """
    fires = sorted({m for m in _SCRIPT.findall(
        "Re-dispatch with build-minor.sh --pr 1 or plan-revision.sh."
    ) if m in FROZEN_ONLY})
    assert fires == ["build-minor.sh", "plan-revision.sh"], (
        f"the predicate no longer reports frozen-only referents (saw {fires}); "
        f"FROZEN_ONLY is {sorted(FROZEN_ONLY)}"
    )
    quiet = sorted({m for m in _SCRIPT.findall(
        "Re-dispatch with build.sh --pr 1, research.sh, or testing/run-all.sh."
    ) if m in FROZEN_ONLY})
    assert quiet == [], (
        f"the predicate now reports {quiet}, which resolve under the PYTHON shim "
        f"directory too — it has degenerated into a ban on naming any script and "
        f"would fail on correct prompts"
    )

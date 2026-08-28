"""A roadmap that has not converted yet must still be countable.

WHY THIS IS BINDING RATHER THAN NICE. `documentation_standard.md` rule 8 rules
the roadmap phase entry into a heading carrying a status marker with an
`**Implementation:**` line beneath it — and in the same breath obliges every
reader of phase entries to keep accepting the shape it replaces:

    "Tooling that reads phase entries MUST accept the checkbox-list form
     until the corpus finishes converting."

That is not politeness. Rule 4's migration clause converts a roadmap when
someone is already working in it, never in a sweep, so the corpus carries both
shapes for months. **12 of MDC's 39 roadmaps carried the checkbox list when the
rule was written.**

WHAT A ZERO ACTUALLY COSTS, WHICH IS THE PART THAT IS NOT OBVIOUS. Reading no
phases is not inert. `sizing_block` renders *"lists no phases"* and, in doing so,
withholds the `(~Nh total · ~Nh to-do)` template it otherwise hands the run. The
run then has nothing authoritative to copy, falls back to the neighbouring
sections of the file it is editing, and writes whatever shape those carry.

**That is how `~128h sized ·` — a form neither repo's standard permits — reached
MDC PR #171.** Not a tool ignoring a convention: a tool with nothing to say. So
this module and the sprint-header shape are one defect, and this is its root.

THE ANCHORS ARE EXACT, WHICH IS THE WHOLE DIFFERENCE FROM THE REJECTED
HEURISTIC. A checkbox, a bold name, and a phase-doc reference in the entry's own
span. The heuristic that was measured and thrown away — *"a heading whose section
links a `phaseN_*.md`"* — INFERRED a phase from a citation and found 12 in
`dev_ui` where there are 5. These three anchors are the notation itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules"))

from assistant.plan import plan_activities as A  # noqa: E402


def _roadmap(tmp_path: Path, body: str) -> Path:
    comp = tmp_path / "component"
    comp.mkdir(parents=True, exist_ok=True)
    (comp / "roadmap.md").write_text(body)
    return comp


CHECKBOX = """# Cluster Provision — Roadmap

## Phases

- [x] **Bootstrap the control plane** ([phase1_bootstrap.md](./phase1_bootstrap.md)) — brings up
  the first node and proves the API answers. **Est: ~14 hrs**
- [ ] **Join the worker pool** ([phase2_workers.md](./phase2_workers.md)) — **Est: ~9 hrs**
- [ ] **Storage class** ([phase3_storage.md](./phase3_storage.md)) — **Est: ~22 hrs**
"""

RULE_8 = """# Cluster Provision — Roadmap

### Bootstrap the control plane ✅ COMPLETE

**Implementation:** [`phase1_bootstrap.md`](phase1_bootstrap.md)

**Est: ~14 hrs**

### Join the worker pool 🟠 PLANNED

**Implementation:** [`phase2_workers.md`](phase2_workers.md)

**Est: ~9 hrs**
"""


def test_the_checkbox_form_is_counted_at_all(tmp_path: Path) -> None:
    """THE REGRESSION. Measured at 0 phases / 0 h before the key existed."""
    sizing = A.phase_sizing(_roadmap(tmp_path, CHECKBOX))
    assert len(sizing.rows) == 3, (
        f"read {len(sizing.rows)} phases from a checkbox-form roadmap carrying "
        f"three. A zero here is what withholds the sprint-header template and "
        f"lets a run copy a neighbour's wrong shape instead."
    )
    assert sizing.total == 45.0, sizing.rows


def test_a_CHECKED_entry_is_complete_so_TO_DO_excludes_it(tmp_path: Path) -> None:
    """Rule 5 names `[x]` the checkbox equivalent of `✅ COMPLETE`.

    The two paths must therefore agree on what `todo` means, or the same plan
    totals differently either side of its conversion — which would make
    converting a roadmap look like work appearing or vanishing.
    """
    sizing = A.phase_sizing(_roadmap(tmp_path, CHECKBOX))
    assert sizing.todo == 31.0, (
        f"to-do is {sizing.todo}, expected 31 — 45 total less the 14 h phase "
        f"marked `[x]`. Rule 5 maps `[x]` to `✅ COMPLETE`, and `todo` tests for "
        f"that marker, so the checkbox path must synthesise it."
    )


def test_converting_a_roadmap_DOES_NOT_MOVE_ITS_NUMBERS(tmp_path: Path) -> None:
    """The point of accepting both shapes: conversion is a reformat, not a re-size.

    If the two readers disagree, every opportunistic conversion silently moves a
    sprint header — and the operator cannot tell a real re-plan from a notation
    change. This is the property that makes the dual window safe to run for
    months rather than a temporary tolerance.
    """
    before = A.phase_sizing(_roadmap(tmp_path / "a", CHECKBOX))
    after = A.phase_sizing(_roadmap(tmp_path / "b", RULE_8))
    common = {h.replace(" ✅ COMPLETE", "").replace(" 🟠 PLANNED", ""): v
              for h, v in after.rows}
    for head, hours in before.rows:
        name = head.replace(" ✅ COMPLETE", "")
        if name in common:
            assert common[name] == hours, (
                f"'{name}' sizes {hours} h in the checkbox form and "
                f"{common[name]} h after conversion. Converting a roadmap must "
                f"not change what it costs."
            )


def test_an_ORDINARY_bolded_checklist_item_is_not_a_phase(tmp_path: Path) -> None:
    """THE NEGATIVE CONTROL, and the reason the doc reference is required.

    Every roadmap is full of bolded checkboxes — acceptance criteria, task lists,
    close-out gates. Two anchors would sweep all of them in. The phase-doc
    reference is the third, and without this test a future simplification that
    drops it would still pass every other check here.
    """
    body = """# Roadmap

## Acceptance criteria

- [x] **The API answers** — verified against a cold checkout. **Est: ~3 hrs**
- [ ] **Logs are structured** — **Est: ~2 hrs**
"""
    sizing = A.phase_sizing(_roadmap(tmp_path, body))
    assert sizing.rows == (), (
        f"read {len(sizing.rows)} phases from a plain checklist: {sizing.rows}. "
        f"A bolded checkbox with no phase-doc reference is a criterion, not a "
        f"phase, and counting one inflates a sprint header."
    )


def test_the_RULE_8_FORM_WINS_when_a_file_carries_both(tmp_path: Path) -> None:
    """Alternatives, not additive — or a converting roadmap counts twice.

    A file mid-conversion holds both notations for the same phase. Reading both
    and summing would double its hours, and a doubled total is the silent wrong
    count this whole function exists to prevent. Undercounting is the deliberate
    trade: `sizing_floor` counts phase-doc FILES ON DISK, so a short read fails
    loudly there.
    """
    sizing = A.phase_sizing(_roadmap(tmp_path, RULE_8 + "\n" + CHECKBOX))
    assert sizing.total == 23.0, (
        f"total is {sizing.total}, expected the rule-8 form's 23 h alone. A file "
        f"carrying both notations must not sum them — 68 h here would be the two "
        f"shapes double-counted, and nothing downstream could tell."
    )


@pytest.mark.parametrize("component,expected", [
    ("memory-management-framework", 124.0),
    ("persistent-memory-protocol", 187.0),
    ("temporal-integration", 193.0),
    ("workflow-decomposition", 73.0),
])
def test_this_repos_own_roadmaps_are_UNCHANGED(component: str, expected: float) -> None:
    """A positive control on the live corpus, not on a fixture.

    Adding a second key to a counter is exactly the change that quietly moves a
    number somewhere else. These four are the figures the sprint file carries,
    and they were measured before the key was added.
    """
    repo = Path(__file__).resolve().parents[5]
    sizing = A.phase_sizing(repo / "docs" / "development" / component)
    assert sizing.total == expected, (
        f"{component} totals {sizing.total} h, was {expected} h before the "
        f"checkbox key existed. The key must be inert on a rule-8 roadmap."
    )

"""`phase_sizing` — the TOTAL and the TO-DO the sprint header is built from.

WHY THIS FILE EXISTS. `PhaseSizing`, `total`, `todo`, `_COMPLETE_MARK` and
`sizing_block` shipped on 2026-08-25 in `4042357` with NO unit test — the only
test that commit touched was a prompt-budget count. These two figures are what
the operator reads to decide what a component costs and how much of it is left,
and nothing pinned either of them.

THE CLASS THIS SUITE GUARDS, stated so the next change is not made blind: the
WRITER of estimates (`plan-refine`), the FLOOR that checks them
(`plan_refine_activities.sizing_floor`) and the SUMMER that derives these two
figures are three separate surfaces over one convention. On 2026-08-19 an
exception was carved into the writer's prompt — a COMPLETE phase "gets none" —
which neither of the other two knew about. The floor counts phase-doc FILES ON
DISK, so a run obeying its brief failed at the last guard; and `todo` subtracts
complete phases, so it needs them PRESENT to differ from `total` at all. The
resolution was to delete the exception: every phase is sized on every run.
These tests pin the half of that contract that lives in code.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.assistant.plan import plan_activities as own


def _roadmap(tree: Path, body: str) -> Path:
    component = tree / "component"
    component.mkdir(parents=True, exist_ok=True)
    (component / "roadmap.md").write_text(body)
    return component


def test_a_component_with_NO_roadmap_sizes_to_zero_rather_than_raising(
        tmp_path: Path) -> None:
    """The all-quiet case, pinned because the caller renders it into a prompt."""
    sizing = own.phase_sizing(tmp_path / "nothing")
    assert sizing == own.PhaseSizing((), 0.0, 0.0, ())


def test_the_TOTAL_sums_every_phase_INCLUDING_the_complete_one(
        tmp_path: Path) -> None:
    """TOTAL IS THE WHOLE COST OF THE COMPONENT, not the cost of what remains.

    THE DISCRIMINATOR FOR THE DELETED EXCEPTION. Under the 2026-08-19 rule the
    complete phase carried no estimate and this total came out 30 — describing
    less than the component cost, with nothing saying so. If a future change
    re-introduces "a complete phase gets none", this is the test that fails.
    """
    c = _roadmap(tmp_path, (
        "# Comp\n\n"
        "## Phase 1 — the groundwork ✅ COMPLETE\n\n**~12 hrs.** Basis: shipped.\n\n"
        "## Phase 2 — the mechanism\n\n**~18 hrs.** Basis: one new package.\n\n"
        "## Phase 3 — the gate\n\n**~12 hrs.** Basis: two arms.\n"
    ))
    sizing = own.phase_sizing(c)
    assert sizing.total == 42.0
    assert sizing.todo == 30.0
    assert sizing.unsized == ()


def test_the_TODO_subtracts_COMPLETE_phases_and_ONLY_those(tmp_path: Path) -> None:
    """Two complete, two not. `todo` is the pair that is left and nothing else."""
    c = _roadmap(tmp_path, (
        "# Comp\n\n"
        "## Phase 1 — a ✅ COMPLETE\n\n**~5 hrs.**\n\n"
        "## Phase 2 — b\n\n**~7 hrs.**\n\n"
        "## Phase 3 — c ✅ COMPLETE\n\n**~11 hrs.**\n\n"
        "## Phase 4 — d\n\n**~13 hrs.**\n"
    ))
    sizing = own.phase_sizing(c)
    assert sizing.total == 36.0
    assert sizing.todo == 20.0


def test_TODO_EQUALS_TOTAL_when_the_roadmap_marks_nothing_complete(
        tmp_path: Path) -> None:
    """The starting state of every component, and it must not be read as a bug."""
    c = _roadmap(tmp_path, (
        "# Comp\n\n"
        "## Phase 1 — a\n\n**~9 hrs.**\n\n"
        "## Phase 2 — b\n\n**~9 hrs.**\n"
    ))
    sizing = own.phase_sizing(c)
    assert sizing.total == sizing.todo == 18.0


def test_TODO_NEVER_EXCEEDS_TOTAL_whatever_the_roadmap_says(tmp_path: Path) -> None:
    """A standing invariant rather than a case: what is LEFT cannot exceed the WHOLE.

    Keyed on the relationship and not on either figure, so it survives a change
    to how completion is detected or to how estimates are matched.
    """
    c = _roadmap(tmp_path, (
        "# Comp\n\n"
        "## Phase 1 — a ✅ COMPLETE\n\n**~4 hrs.**\n\n"
        "## Phase 2 — b\n\n**~6 hrs.**\n\n"
        "## Phase 3 — c\n\nno figure here at all\n"
    ))
    sizing = own.phase_sizing(c)
    assert 0.0 <= sizing.todo <= sizing.total


def test_a_phase_with_NO_estimate_lands_in_unsized_and_is_NEVER_read_as_zero(
        tmp_path: Path) -> None:
    """A MISSING ESTIMATE IS A DEFECT, AND A QUIETLY SHORT TOTAL IS THE FAILURE.

    The unsized phase must be NAMED. Treating it as zero produces a total that
    is wrong with nothing saying it is wrong, which is worse than no total.
    """
    c = _roadmap(tmp_path, (
        "# Comp\n\n"
        "## Phase 1 — sized\n\n**~10 hrs.**\n\n"
        "## Phase 2 — nobody sized this one\n\nprose, but no figure\n"
    ))
    sizing = own.phase_sizing(c)
    assert sizing.total == 10.0
    assert len(sizing.unsized) == 1
    assert "nobody sized this one" in sizing.unsized[0]
    assert len(sizing.rows) == 2, "the unsized phase is still a ROW, not dropped"


def test_completion_is_keyed_on_the_EMOJI_and_not_on_the_WORD(
        tmp_path: Path) -> None:
    """A PHASE NAMED FOR COMPLETENESS MUST NOT SUBTRACT ITSELF.

    The reason `_COMPLETE_MARK` is `✅` and not `complete`, stated in the
    constant's own comment: a heading like "Nothing a run relies on is
    invisible" is one word away from matching a word test, and a phase that
    silently removes itself from the remaining work is the under-report this
    whole derivation exists to prevent.
    """
    c = _roadmap(tmp_path, (
        "# Comp\n\n"
        "## Phase 1 — the completeness sweep is complete in scope\n\n**~20 hrs.**\n"
    ))
    sizing = own.phase_sizing(c)
    assert sizing.todo == 20.0, "a WORD match here would have zeroed the to-do"


def test_an_UNMARKED_complete_phase_OVER_reports_what_is_left(
        tmp_path: Path) -> None:
    """THE CHOSEN FAILURE DIRECTION, PINNED SO A REFACTOR CANNOT QUIETLY FLIP IT.

    A roadmap that one day marks completion some other way reads as OUTSTANDING
    here, so `todo` comes out too HIGH. Over-reporting remaining work costs a
    second look; under-reporting quietly shortens a plan. This test asserts the
    safe direction rather than assuming it.
    """
    c = _roadmap(tmp_path, (
        "# Comp\n\n"
        "## Phase 1 — shipped, but marked with a tick nobody parses [DONE]\n\n"
        "**~15 hrs.**\n"
    ))
    sizing = own.phase_sizing(c)
    assert sizing.todo == sizing.total == 15.0


def test_an_estimate_BELOW_the_heading_is_found_the_same_as_one_beside_it(
        tmp_path: Path) -> None:
    """`plan-refine` writes the figure as its own paragraph, not in the heading."""
    c = _roadmap(tmp_path, (
        "# Comp\n\n"
        "## Phase 1 — a thing\n\n"
        "*a subtitle line*\n\n"
        "**~25 hrs.** Basis: measured against the neighbour.\n"
    ))
    sizing = own.phase_sizing(c)
    assert sizing.total == 25.0
    assert sizing.unsized == ()


def test_one_phases_estimate_is_NEVER_attributed_to_the_PREVIOUS_phase(
        tmp_path: Path) -> None:
    """THE WINDOW MUST NOT REACH THE NEXT HEADING.

    The below-heading search reads a six-line window. If that window could span
    into the following phase, an unsized phase would silently borrow its
    neighbour's figure and the `unsized` list — the only signal that a phase was
    missed — would come back empty.
    """
    c = _roadmap(tmp_path, (
        "# Comp\n\n"
        "## Phase 1 — nobody sized this\n\n"
        "## Phase 2 — sized\n\n**~30 hrs.**\n"
    ))
    sizing = own.phase_sizing(c)
    assert sizing.total == 30.0
    assert len(sizing.unsized) == 1
    assert "nobody sized this" in sizing.unsized[0]


def test_a_roadmap_MIXING_both_estimate_spellings_sizes_every_phase(
        tmp_path: Path) -> None:
    """ONE PHASE INLINE, ONE BELOW ITS HEADING, AND BOTH MUST BE FOUND.

    The below-heading search used to run only when EVERY phase lacked an inline
    figure, so a roadmap that mixed the two spellings reported all its
    below-heading phases as unsized. Loud rather than silent, but wrong on a
    correct document — and `unsized` is the list a reader is told to treat as
    defects.
    """
    c = _roadmap(tmp_path, (
        "# Comp\n\n"
        "## Phase 1 — inline (8h)\n\nprose about the phase\n\n"
        "## Phase 2 — below\n\n**~12 hrs.** Basis: stated.\n"
    ))
    sizing = own.phase_sizing(c)
    assert sizing.total == 20.0
    assert sizing.unsized == ()


@pytest.mark.parametrize("heading", [
    "## Phase 1 — a thing",
    "### Phase 2 — a thing",
    "#### Phase 3 — a thing",
])
def test_phase_headings_are_read_at_every_depth_the_roadmaps_use(
        tmp_path: Path, heading: str) -> None:
    """Roadmaps in this tree nest phases at more than one level."""
    c = _roadmap(tmp_path, f"# Comp\n\n{heading}\n\n**~8 hrs.**\n")
    assert own.phase_sizing(c).total == 8.0


def test_a_heading_that_is_not_a_phase_is_not_sized(tmp_path: Path) -> None:
    """Roadmaps carry prose sections whose figures are not phase estimates."""
    c = _roadmap(tmp_path, (
        "# Comp\n\n"
        "## Open inputs\n\n**~99 hrs** of unrelated prose about time\n\n"
        "## Phase 1 — the real one\n\n**~8 hrs.**\n"
    ))
    sizing = own.phase_sizing(c)
    assert sizing.total == 8.0
    assert len(sizing.rows) == 1


def test_the_sizing_block_STATES_both_figures_and_names_what_is_unsized(
        tmp_path: Path) -> None:
    """The block is what a model reads INSTEAD of adding the numbers itself.

    Both figures must appear, and an unsized phase must be named in it — a block
    that showed a total while silently omitting a phase is the shape the
    `unsized` list exists to make impossible.
    """
    c = _roadmap(tmp_path, (
        "# Comp\n\n"
        "## Phase 1 — done ✅ COMPLETE\n\n**~10 hrs.**\n\n"
        "## Phase 2 — left\n\n**~6 hrs.**\n\n"
        "## Phase 3 — missed\n\nno figure\n"
    ))
    block = own.sizing_block(own.phase_sizing(c), Path("docs/development/comp"))
    assert "16 h" in block, "the TOTAL"
    assert "6 h" in block, "the TO-DO"
    assert "missed" in block, "the unsized phase must be named, not merely counted"
    assert "do not recount" in block


def test_the_sizing_block_says_so_when_there_are_NO_phases(tmp_path: Path) -> None:
    """An empty roadmap must not render a table of nothing with a 0 h total."""
    c = _roadmap(tmp_path, "# Comp\n\nprose only, no phases yet\n")
    block = own.sizing_block(own.phase_sizing(c), Path("docs/development/comp"))
    assert "no phases" in block
    assert "TOTAL" not in block


def test_a_phase_declaring_NOT_SIZED_is_unsized_even_though_it_quotes_a_figure(tmp_path):
    """A removal notice necessarily names the figure it removed.

    MEASURED ON PR #145. `plan-refine` split a phase, deleted the inherited
    estimate as no longer meaningful, and wrote *"**NOT SIZED. The 2026-08-19
    figure of ~24 hours was written against a phase that no longer exists and has
    been removed rather than left to mislead**"*. `HOUR_ESTIMATE`'s first
    alternative needs only a tilde, so it read that quoted figure as the phase's
    estimate — **the phase declaring itself unsized parsed as sized at 24 h**,
    and the total it fed was wrong in the direction nobody checks.

    The honest act — deleting a stale figure and saying why — is exactly what
    tripped it. That is the shape this guards.
    """
    comp = tmp_path / "c"; comp.mkdir()
    (comp / "roadmap.md").write_text(
        "# R\n\n"
        "### Nothing a run relies on is invisible 🟠 PLANNED\n\n"
        "**NOT SIZED. The 2026-08-19 figure of ~24 hours was written against a phase "
        "that no longer exists and has been removed rather than left to mislead** — "
        "both halves need reading cold.\n\n"
        "### Dual-mode children 🟠 PLANNED\n\n"
        "**Est: ~30 hours**\n"
    )
    sizing = own.phase_sizing(comp)
    assert sizing.total == 30.0, (
        f"total is {sizing.total}, expected 30 — the NOT SIZED phase must "
        f"contribute nothing. A phantom 24 h here inflates every figure derived "
        f"from this roadmap, including the sprint header."
    )
    assert "Nothing a run relies on is invisible 🟠 PLANNED" in " ".join(sizing.unsized), (
        f"the NOT SIZED phase must appear in `unsized`: {sizing.unsized}. That "
        f"list is the only signal an operator gets that a phase still needs a figure."
    )


def test_plan_sprint_IS_HANDED_the_estimates_plan_refine_writes() -> None:
    """The check that holds `run_plan_refine.py`'s closing message.

    That epilogue asserted the opposite for two `plan-refine` passes on PR #145
    — *"`plan-sprint` does NOT read them today ... nothing in it reads a roadmap
    or an hour figure"* — and an operator acting on it would build a handoff that
    already exists. The claim was true of the MODEL (plan-sprint's prompt does
    forbid opening a phase doc) and generalised to the WORKFLOW, whose parent
    computes the figures before the model is called.

    `C-zwzepum0`'s rule: a sentence asserting how another file behaves either
    names the check that holds it, or is not written. This is that check.
    """
    root = Path(__file__).resolve().parents[2] / "modules" / "assistant" / "plan"
    wf = (root / "plan_sprint" / "plan_sprint_workflow.py").read_text()
    assert "act.phase_sizing(" in wf, (
        "plan_sprint_workflow no longer calls `phase_sizing`. If the handoff was "
        "deliberately removed, correct `run_plan_refine.py`'s closing message in "
        "the same commit — it tells the operator this wiring exists."
    )
    assert '"SIZING_BLOCK"' in wf, (
        "plan_sprint_workflow no longer injects SIZING_BLOCK, so the computed "
        "total never reaches the model even though it is calculated."
    )
    prompt = (root / "plan_sprint" / "prompts" / "plan_sprint.md").read_text()
    assert "${SIZING_BLOCK}" in prompt, (
        "the prompt dropped its ${SIZING_BLOCK} placeholder, so the parent "
        "computes the figures and renders them nowhere."
    )


def test_REWORDING_a_checked_bullet_is_not_a_flip(tmp_path) -> None:
    """Editing a checked item's text must not read as erasing and re-ticking it.

    MEASURED ON PR #145. `plan-sprint` appended `· **~34h**` to two already-checked
    sprint bullets and the guard reported *"flipped 4 completion checkbox(es)"* —
    two ERASED, two TICKED, the same two items. `- [x]` before, `- [x]` after.

    A guard that cannot tell a reworded item from a fabricated completion spends
    its credibility on the wrong alarm, and the real prohibition — do not claim
    work nobody did — is the one that stops being believed.
    """
    before = tmp_path / "before.md"
    after = tmp_path / "after.md"
    before.write_text(
        "- [x] **Decompose the build families** · ([roadmap](r.md)) — the shape written down\n"
        "- [ ] **Dual-mode children** · ([roadmap](r.md)) — nine children run alone\n")
    after.write_text(
        "- [x] **Decompose the build families** · ([roadmap](r.md)) · **~34h** — the shape written down\n"
        "- [ ] **Dual-mode children** · ([roadmap](r.md)) · **~30h** — nine children run alone\n")
    assert own.checked_boxes(before) == own.checked_boxes(after), (
        "rewording a checked bullet registered as a checkbox flip. Only the "
        "bullet's text changed; its state did not."
    )


def test_an_ACTUAL_flip_is_still_caught(tmp_path) -> None:
    """The control. Keying on identity must not blind the guard to a real tick."""
    before = tmp_path / "b.md"; after = tmp_path / "a.md"
    before.write_text("- [ ] **Dual-mode children** — nine children run alone\n")
    after.write_text("- [x] **Dual-mode children** — nine children run alone\n")
    moved = own.checked_boxes(after) - own.checked_boxes(before)
    assert list(moved.elements()) == ["Dual-mode children"], (
        f"a genuine tick was not detected: {moved}. Identity keying must narrow "
        f"WHAT is compared, never WHETHER a flip is seen."
    )


def test_a_component_SPLIT_ACROSS_SECTIONS_reports_all_of_them(tmp_path) -> None:
    """One section reported as the whole component is a wrong count with authority.

    MEASURED ON PR #150. `persistent-memory-protocol` occupies TWO sprint
    sections — `— Part 1` and `— Part 2`, an established shape in that file —
    and the counter's `next(...)` returned the first. The run was told, under a
    block reading *"authoritative — do not recount"*, that the component had ONE
    section carrying six bullets. It never learned the second existed, and the
    second is where the gated phases live.

    A WRONG COUNT IS WORSE THAN A ZERO because it announces authority: a zero
    says "I found nothing" and a run checks, while this says "I counted" and a
    run believes it. That is the same failure `phase_sizing` was fixed for.
    """
    sprint = tmp_path / "sprint.md"
    sprint.write_text(
        "## Sprint: Alpha\n\n- [ ] **Alpha · one**\n\n"
        "## Sprint: Widget Thing — Part 1\n\n- [x] **Widget Thing · a**\n- [ ] **Widget Thing · b**\n\n"
        "## Sprint: Widget Thing — Part 2\n\n- [ ] **Widget Thing · c**\n")
    out = own.sprint_state(sprint, Path("widget-thing"))
    assert "SPLIT ACROSS 2 SECTIONS" in out, f"reported only one section: {out}"
    assert "Part 1" in out and "Part 2" in out, "both sections must be named"
    assert "2 bullet(s)" in out and "1 bullet(s)" in out, (
        "each section's own bullet count must be reported — a total across both "
        "would hide which section a phase belongs to"
    )
    assert "operator's split, not yours" in out, (
        "the run must be told NOT to move a phase between sections; doing so "
        "re-sequences the plan, which is the operator's decision"
    )


def test_a_component_in_ONE_section_still_reads_as_one(tmp_path) -> None:
    """The control: widening the match must not turn every component into a split."""
    sprint = tmp_path / "sprint.md"
    sprint.write_text("## Sprint: Alpha\n\n- [ ] **Alpha · one**\n\n"
                      "## Sprint: Widget Thing\n\n- [ ] **Widget Thing · a**\n")
    out = own.sprint_state(sprint, Path("widget-thing"))
    assert "SPLIT ACROSS" not in out, f"a single-section component read as split: {out}"
    assert "HAS a section" in out and "1 phase bullet(s)" in out

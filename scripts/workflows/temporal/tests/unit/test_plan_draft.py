"""`plan-draft`'s four own prohibitions, and the readers that observe them.

WHAT IS AND IS NOT COVERED HERE, because two other modules already cover half of
this workflow and duplicating them would be worse than a gap. The registries are
held elsewhere and generically: `test_authorization_is_observed.py` proves every
`You MAY NOT` row names a mechanism that EXISTS, and
`test_disappearance_is_observed.py` proves every before/after snapshot names what
watches it for absence. Both DISCOVER this workflow by AST rather than being told
about it. Neither proves any guard FIRES, which is what this module is for.

THE FOUR ARE NOT EQUALLY OBVIOUS, and the two easy ones are the traps:

  * **The phase-doc grammar** and **the reused number** look like one check and
    are two. A renumber is an ADD and a DELETE together, so a guard that only
    judged what appeared would report `phase3_x.md` as fine while `phase2_x.md`
    had ceased to exist. Deletion is checked FIRST for that reason, and
    `test_a_RENUMBER_is_caught_as_a_deletion_not_as_a_new_name` is the fixture
    where the two answers differ.
  * **The hour detector** is the one that can fail in the expensive direction. A
    guard keyed on the word `hours` fires on ordinary prose about time, and this
    repo's planning docs carry exactly three such phrases and ZERO estimates — so
    a word-keyed pattern would fail three correct runs on the first component
    that quoted one. Those three lines are the negative fixture below, taken
    verbatim from the tree.
  * **The write boundary** is the one whose fixture must not be symmetric. A
    component path granted back out of a wholesale `docs/development/` denial
    reads correct against its own component and says nothing about a SIBLING, so
    every boundary case here uses two components rather than one.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from modules.assistant.plan import plan_activities as act  # noqa: E402
from modules.assistant.plan.plan_draft import plan_draft_activities as own  # noqa: E402
from modules.assistant.plan.plan_draft import plan_draft_workflow as wf  # noqa: E402


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    (tmp_path / "docs" / "development" / "alpha" / "research" / "raw").mkdir(parents=True)
    (tmp_path / "docs" / "development" / "beta").mkdir(parents=True)
    return tmp_path


def _component(tree: Path, name: str = "alpha") -> Path:
    return tree / "docs" / "development" / name


def _write(component: Path, name: str, body: str = "# x\n") -> Path:
    f = component / name
    f.write_text(body)
    return f


# --- vacuity floor ---------------------------------------------------------

def test_a_conformant_plan_passes_EVERY_guard(tree: Path) -> None:
    """THE FLOOR. If this does not pass, every assertion below is vacuous — a
    guard that rejects correct work is indistinguishable from one that works."""
    c = _component(tree)
    before, before_plan = own.phase_docs(c), own.plan_docs(c)
    _write(c, "roadmap.md", "# Alpha\n\n- [ ] a criterion\n")
    _write(c, "phase1_the_first_thing.md", "# Phase 1\n\n- [ ] a step\n")
    _write(c, "phase2b_a_sub_letter.md", "# Phase 2b\n")
    after, after_plan = own.phase_docs(c), own.plan_docs(c)

    assert own.malformed_phase_docs(before_plan, after_plan) == [], (
        "`roadmap.md` is the one legitimate non-phase name and must not be "
        "flagged by the guard that judges every other new plan file")
    assert own.reused_phase_numbers(before, after) == []
    assert own.hour_estimates(c, tree) == []
    assert act.ids_deleted(before, after) == []
    assert own.plan_boxes(c) == Counter(), "no box is ticked in a fresh plan"
    assert len(after) == 2, "the phase-doc reader found nothing to judge"
    assert len(after_plan) == 3, "the plan reader must also see the roadmap"


# --- the phase number is IDENTITY ------------------------------------------

@pytest.mark.parametrize("name", [
    "phase_the_thing.md",            # dropped the number — failure mode (b)
    "Phase3_the_thing.md",           # capitalised
    "phase3-the-thing.md",           # no underscore separator
    "phase3_the_thing(old).md",      # parenthetical disambiguation
    "phase3.md",                     # no descriptor
    "phaseA_the_thing.md",           # letter where the number goes
    "the_run_bag.md",                # DROPPED THE PREFIX ENTIRELY — see below
    "README.md",                     # a third kind of file; there are only two
])
def test_a_NEW_phase_doc_outside_the_grammar_is_caught(tree: Path, name: str) -> None:
    """The Documentation Standard's own recommended CI lint, at authoring time.

    Every one of these is a form the standard names as a real failure mode: it
    lists dropping the number, retroactive sub-letters and parenthetical
    disambiguation by name, having watched engineers reach for all three.

    `the_run_bag.md` IS THE CASE THAT WAS MISSING, AND IT IS THE PLAINEST ONE.
    Every other entry here begins with `phase`, so a guard sourced from a
    `^phase` sweep catches them all by construction and this parametrize list
    read as thorough while being blind to a name that drops the convention
    outright — which is the standard's first-named failure mode and what a model
    writes when it forgets the convention rather than mistyping it. Closing it is
    what moved this guard onto `plan_docs` (the write grant's own set) from
    `phase_docs`.

    A `_v2` SUFFIX IS DELIBERATELY ABSENT FROM THIS LIST, AND THE SPEC IS WHY.
    The standard's prose forbids "version suffixes" while its own binding regex —
    `^phase[0-9]+[a-z]?_[a-z0-9_-]+\\.md$`, quoted verbatim under *Filename
    pattern (binding)* — admits digits anywhere in the descriptor, so
    `phase3_the_thing_v2.md` conforms. This test asserted the prose and went red
    against the regex. **The versioned artifact wins over a reading of the prose
    around it**, so the case is dropped rather than the grammar tightened: a guard
    stricter than the binding pattern would fail a filename the standard permits,
    and this workflow may not rename its way out of one.
    """
    c = _component(tree)
    before = own.plan_docs(c)
    _write(c, name)
    assert own.malformed_phase_docs(before, own.plan_docs(c)) == [name]


def test_the_ROADMAP_is_the_one_new_name_that_is_not_a_phase_doc(tree: Path) -> None:
    """The guard judges every NEW plan file, so the exemption must be explicit.

    Widening the sweep to the write grant made `roadmap.md` a candidate for its
    own naming guard — it is a new top-level markdown file that is not a
    conformant phase name. Excluding it by name is the whole of the difference
    between "this run writes two kinds of file" and "this run cannot write its
    own deliverable".
    """
    c = _component(tree)
    before = own.plan_docs(c)
    _write(c, "roadmap.md")
    assert own.malformed_phase_docs(before, own.plan_docs(c)) == []


def test_a_PRE_EXISTING_malformed_name_is_left_alone(tree: Path) -> None:
    """The guard judges what this run ADDED, and only that.

    A legacy non-conformant name is somebody else's, and renaming it is
    explicitly out of scope — the number is identity, and "fixing" one costs a
    cross-reference sweep to buy nothing. A guard that failed the run over a file
    it is FORBIDDEN to touch would make the component unplannable: there would be
    no action available that both satisfies the guard and respects the boundary.
    """
    c = _component(tree)
    _write(c, "phase_legacy.md")
    _write(c, "an_old_note.md")
    before = own.plan_docs(c)
    _write(c, "phase1_new_work.md")
    assert own.malformed_phase_docs(before, own.plan_docs(c)) == []


def test_a_new_phase_reusing_a_LIVE_number_is_caught(tree: Path) -> None:
    c = _component(tree)
    _write(c, "phase2_incumbent.md")
    before = own.phase_docs(c)
    _write(c, "phase2_a_second_one.md")
    assert own.reused_phase_numbers(before, own.phase_docs(c)) == [
        ("phase2_a_second_one.md", 2)]


def test_a_GAP_is_not_a_free_number(tree: Path) -> None:
    """Rule 5, and it is the half that gets read backwards.

    Gaps are CORRECT — they reflect cancelled or relocated phases — and they are
    not available. External references in commit messages, code comments and the
    sprint plan may still point at a retired number, so reusing it makes every
    one of them silently ambiguous. A run reading a gap as an invitation is the
    likelier mistake, because the sequence looks untidy and tidying it is the
    obvious move.
    """
    c = _component(tree)
    _write(c, "phase1_a.md")
    _write(c, "phase3_c.md")          # phase 2 was retired
    before = own.phase_docs(c)
    _write(c, "phase4_legitimate.md")
    assert own.reused_phase_numbers(before, own.phase_docs(c)) == [], (
        "max+1 must be accepted; the guard is about reuse, not about density")

    _write(c, "phase2_filling_the_gap.md")
    assert own.reused_phase_numbers(before, own.phase_docs(c)) == [], (
        "a gap number is not in the BEFORE set, so this reader cannot see it — "
        "which is a real limit of the mechanism and is why the prompt states the "
        "rule and the roadmap's tombstone entries carry the archaeology")


def test_a_sub_letter_shares_its_phase_NUMBER(tree: Path) -> None:
    """Rule 6: `2a` and `2b` are two atomic chunks of ONE phase planned together.

    They share an identity, so they share a number, and a caller asking which
    numbers are taken wants 2 for both. Reading the sub-letter as part of the
    number would make `phase2b` a distinct phase 2b and let a later `phase2_x`
    slip past the reuse guard.
    """
    assert own.phase_number("phase2a_poc.md") == 2
    assert own.phase_number("phase2b_rollout.md") == 2
    assert own.phase_number("phase12_the_twelfth.md") == 12
    assert own.phase_number("phase_unnumbered.md") is None


def test_a_RENUMBER_is_caught_as_a_deletion_not_as_a_new_name(tree: Path) -> None:
    """THE FIXTURE WHERE THE THREE GUARDS DISAGREE, which is why it exists.

    Renumbering `phase2_x.md` to `phase3_x.md` produces a name that is perfectly
    VALID and a number that is NOT reused, so both name guards pass it. The only
    observation that sees it is that `phase2_x.md` was there before this run and
    is not there after — which is why the workflow checks deletion FIRST and why
    a rename, a renumber and a delete are one mechanism rather than three.

    A single-value mutation could not reach this: the input's SHAPE has to change
    — a file leaves and another arrives — and a fixture that only ever adds is
    symmetric under the defect.
    """
    c = _component(tree)
    _write(c, "phase2_the_thing.md")
    before = own.phase_docs(c)

    before_plan = own.plan_docs(c)
    (c / "phase2_the_thing.md").rename(c / "phase3_the_thing.md")
    after = own.phase_docs(c)

    assert own.malformed_phase_docs(before_plan, own.plan_docs(c)) == [], (
        "the new name is valid")
    assert own.reused_phase_numbers(before, after) == [], "3 was never taken"
    assert act.ids_deleted(before, after) == ["phase2_the_thing.md"], (
        "the deletion comparator is the ONLY one that sees a renumber; if this "
        "stops firing, renaming to express rollout order becomes invisible")


def test_an_EDIT_to_an_existing_phase_doc_is_not_a_deletion(tree: Path) -> None:
    """The content hash changes and the key does not — a rewrite is not a rename."""
    c = _component(tree)
    f = _write(c, "phase1_a.md", "# before\n")
    before = own.phase_docs(c)
    f.write_text("# after, materially different\n")
    after = own.phase_docs(c)
    assert act.ids_deleted(before, after) == []
    assert before["phase1_a.md"] != after["phase1_a.md"], (
        "hashing by content is what lets a caller tell a rewritten doc from an "
        "untouched one; if these matched, the reader is keying on the name alone")


def test_research_papers_named_like_phases_are_NOT_phase_docs(tree: Path) -> None:
    """The reader is top-level-only, and `research/` is deliberately outside it."""
    c = _component(tree)
    (c / "research" / "raw" / "phase_transitions_in_queues.md").write_text("# paper\n")
    assert own.phase_docs(c) == {}


# --- hours: the guard that must NOT over-fire ------------------------------

# Verbatim from this repo's planning docs, found with
#   grep -rniE '(hrs|hours)' docs/development/memory-management-framework/ \
#                            docs/development/persistent-memory-protocol/
# which returns exactly these three lines and nothing else. There are ZERO hour
# estimates in the tree, so every real occurrence of the word is prose — and a
# word-keyed guard would fail three correct runs on the first component quoting
# one of them.
_PROSE_ABOUT_TIME = [
    "ment's figures true for a few hours and then wrong again",
    'nt"*; that was true for a few hours on 2026-08-10 and w',
    "has a shelf life measured in hours, and the reading-in",
    # THE THREE THE SHIPPED PATTERN FAILED ON, and the reason this list is no
    # longer only lines lifted from the tree. The pattern's own comment cited the
    # first of these as the false positive `[^.\n]` prevents — and a `\.?` added
    # after the whole label group to catch `Est.` handed the property straight
    # back, because it also consumed a genuine sentence-ending full stop. All
    # three matched the shipped guard; none is an estimate. The marker word here
    # ENDS a sentence and the figure belongs to the next one, which is the shape
    # no line copied out of the tree happened to have.
    "Based on the estimate. It took 3 hours to migrate by hand.",
    "That is the whole effort. Then 5 hours later the poller fired.",
    "We settled the sizing. We waited 2 hours for the first run.",
]


@pytest.mark.parametrize("line", _PROSE_ABOUT_TIME)
def test_ordinary_prose_about_time_is_NOT_an_estimate(tree: Path, line: str) -> None:
    """THE NEGATIVE CONTROL THAT DECIDED THE PATTERN'S SHAPE.

    These are real lines from real phase docs. A guard that fired on them would
    be worse than no guard: it fails a run that did nothing wrong, and the
    operator's only remedy is to reword correct prose.
    """
    c = _component(tree)
    _write(c, "phase1_a.md", f"# Phase 1\n\n{line}\n")
    assert own.hour_estimates(c, tree) == []


@pytest.mark.parametrize("text,label", [
    ("### Phase 1 — the thing (~30 hrs)", "the Documentation Standard's own example"),
    ("Sizing: ~8h", "tilde plus bare h"),
    ("Delivers the bag (12 hours)", "bare parenthetical"),
    ("Estimated at 40 hours across two engineers", "explicit label"),
    ("Effort: roughly 6 hrs", "labelled with an intervening word"),
    ("Est. 2.5 hours", "fractional"),
])
def test_an_hour_ESTIMATE_is_caught(tree: Path, text: str, label: str) -> None:
    c = _component(tree)
    _write(c, "roadmap.md", f"# Alpha\n\n{text}\n")
    found = own.hour_estimates(c, tree)
    assert len(found) == 1, f"{label}: expected one finding, got {found}"
    assert found[0].startswith("docs/development/alpha/roadmap.md:3:"), (
        f"the citation must name the file and the line — the operator's next "
        f"question is always WHERE. Got {found[0]!r}")


def test_the_hour_guard_reads_phase_docs_AND_the_roadmap(tree: Path) -> None:
    """Scope, asserted with a COUNT rather than a boolean.

    A guard scoped to `roadmap.md` alone would be blind to the likelier mistake:
    a phase doc is where an implementation checklist lives and is where somebody
    writes a number beside a step.
    """
    c = _component(tree)
    _write(c, "roadmap.md", "# Alpha\n\n(~4 hrs)\n")
    _write(c, "phase1_a.md", "# Phase 1\n\nEstimate: 9 hours\n")
    assert len(own.hour_estimates(c, tree)) == 2


def test_the_hour_guard_does_NOT_read_the_research_pool(tree: Path) -> None:
    """A synthesis reporting a MEASURED wall-clock is evidence, not an estimate."""
    c = _component(tree)
    (c / "research" / "synthesis.md").write_text("The sweep took ~3 hours.\n")
    assert own.hour_estimates(c, tree) == []


def test_the_hour_and_checkbox_GUARDS_COVER_THE_WHOLE_WRITE_GRANT(tree: Path) -> None:
    """A guard narrower than the grant leaves a file the run may write unread.

    The grant is every markdown file directly in the component, and both content
    guards were scoped to `roadmap.md`-or-`phase*` instead. So a top-level
    `notes.md` — permitted by the grant, therefore exempt from
    `boundary_crossings` by construction — could carry an hour estimate and a
    pre-ticked criterion past every check in the workflow. Nothing else in the
    module would have noticed: the boundary tests assert the grant is WIDE and
    the content tests assert the guards FIRE, and neither compares the two sets.
    """
    c = _component(tree)
    _write(c, "notes.md", "# Notes\n\nSizing: ~8h\n\n- [x] already done\n")
    assert own.hour_estimates(c, tree) == [
        "docs/development/alpha/notes.md:3: Sizing: ~8h"]
    assert own.plan_boxes(c) == Counter({"already done": 1})


def test_plan_boxes_reads_the_ROADMAP_and_the_phase_docs_together(tree: Path) -> None:
    """One Counter over the whole plan, because the prohibition is about the plan.

    Counted by TEXT so that re-ordering sections is invisible, and a Counter
    rather than a set so that ticking the second of two identically worded
    criteria is still seen.
    """
    c = _component(tree)
    _write(c, "roadmap.md", "# Alpha\n\n- [x] a criterion\n- [ ] an unchecked one\n")
    _write(c, "phase1_a.md", "# Phase 1\n\n- [x] a criterion\n* [X] a step\n")
    assert own.plan_boxes(c) == Counter({"a criterion": 2, "a step": 1})
    assert own.plan_boxes(_component(tree, "beta")) == Counter(), (
        "a component with no plan yet must count zero rather than raise")


# --- the write boundary: two components, never one -------------------------

def _state(paths: dict[str, str]) -> dict[str, str]:
    """A `worktree_state`-shaped map: relative path -> content sentinel."""
    return dict(paths)


def test_the_boundary_grants_the_component_and_denies_its_SIBLING(tree: Path) -> None:
    """THE ASYMMETRIC FIXTURE. One component proves nothing about the other.

    A grant tested only against its own component reads correct whether or not
    the denial reaches a sibling — the input is symmetric under the defect. Both
    are exercised here in one comparison, so the grant and the denial are
    separable in the result.
    """
    permitted = wf.permitted_paths(Path("docs/development/alpha"), Path("tracked/candidates"))
    before = _state({
        "docs/development/alpha/roadmap.md": "a",
        "docs/development/beta/roadmap.md": "a",
        "docs/development/sprint.md": "a",
        "docs/development/alpha/research/synthesis.md": "a",
        "docs/standards/architecture/problem-statement.md": "a",
    })
    after = {k: "CHANGED" for k in before}
    crossed = act.boundary_crossings(before, after, wf.FORBIDDEN_PATHS, permitted)
    assert crossed == [
        "docs/development/alpha/research/synthesis.md",
        "docs/development/beta/roadmap.md",
        "docs/development/sprint.md",
        "docs/standards/architecture/problem-statement.md",
    ], (
        "expected the sibling component, the sprint plan, the run's own research "
        "pool and the thesis to be crossings, and only the component's top-level "
        "markdown plus an item in the candidates pool to be granted"
    )


def test_the_grant_reaches_NO_subdirectory_of_the_component(tree: Path) -> None:
    """`research/` is the subdirectory that matters, and it is not the only one.

    The grant is expressed as a SHAPE — files directly in the component — rather
    than as a second deny rule naming `research/`, so a component that later
    grows `notes/` or `diagrams/` is covered with no rule to remember. Asserted
    over a directory that does not exist today, which is the whole claim.
    """
    permitted = wf.permitted_paths(Path("docs/development/alpha"), Path("tracked/candidates"))
    before = _state({
        "docs/development/alpha/phase1_a.md": "a",
        "docs/development/alpha/research/raw/p.md": "a",
        "docs/development/alpha/some_future_dir/x.md": "a",
    })
    after = {k: "CHANGED" for k in before}
    assert act.boundary_crossings(before, after, wf.FORBIDDEN_PATHS, permitted) == [
        "docs/development/alpha/research/raw/p.md",
        "docs/development/alpha/some_future_dir/x.md",
    ]


def test_a_component_whose_name_PREFIXES_another_is_not_granted_it(tree: Path) -> None:
    """`alpha` must not grant `alpha-two`, which a prefix match would.

    The grant is anchored at `^` and the component segment is followed by `/`, so
    the match cannot run past the directory name. Worth an assertion rather than
    an argument: `docs/development/` holds sixteen sibling slugs and several
    share prefixes.
    """
    permitted = wf.permitted_paths(Path("docs/development/alpha"), Path("tracked/candidates"))
    before = _state({"docs/development/alpha-two/roadmap.md": "a"})
    after = {k: "CHANGED" for k in before}
    assert act.boundary_crossings(
        before, after, wf.FORBIDDEN_PATHS, permitted) == [
        "docs/development/alpha-two/roadmap.md"]


def test_the_component_name_is_ESCAPED_before_it_becomes_a_pattern(tree: Path) -> None:
    """A directory name is DATA, and interpolating it raw makes it a pattern.

    The standalone dispatch takes an operator-supplied directory and nothing
    slugs it — only the `plan-project` path runs it through `component_slug`. So
    a real name carrying a regex metacharacter, `v2.1-migration` being the
    likeliest, becomes a grant whose `.` matches any character and therefore
    reaches `v2x1-migration/` as well. The boundary silently widening to a
    SIBLING is the one failure the whole module exists to prevent, and every
    other boundary test here uses `alpha`, which has no metacharacter to escape.
    """
    permitted = wf.permitted_paths(Path("docs/development/v2.1-migration"), Path("tracked/candidates"))
    before = _state({"docs/development/v2x1-migration/roadmap.md": "a"})
    after = {k: "CHANGED" for k in before}
    assert act.boundary_crossings(before, after, wf.FORBIDDEN_PATHS, permitted) == [
        "docs/development/v2x1-migration/roadmap.md"], (
        "the grant matched a sibling whose name differs by one character — the "
        "component segment reached the regex unescaped")

    own_file = {"docs/development/v2.1-migration/roadmap.md": "a"}
    assert act.boundary_crossings(
        own_file, {k: "CHANGED" for k in own_file},
        wf.FORBIDDEN_PATHS, permitted) == [], "and its own component is still granted"


def test_every_granted_path_is_also_watched_for_DELETION(tree: Path) -> None:
    """A WRITE GRANT IS NOT A DELETE GRANT, exercised rather than declared.

    `test_disappearance_is_observed.py` asserts STRUCTURALLY that the same grant
    tuple reaches both calls. This asserts the consequence: the exempted files
    are precisely the ones `boundary_crossings` cannot see disappear, so
    something else has to.

    A DELETED FILE IS THE `ABSENT` SENTINEL, NOT A MISSING KEY, and the two mean
    OPPOSITE things — an absent key is `BASELINE`, i.e. *git never reported this
    path*, which is how a run may legitimately CREATE a permitted file without
    being failed for it. This fixture used `{}` and observed nothing; the guard
    was right and the fixture's model of `worktree_state` was wrong.
    """
    permitted = wf.permitted_paths(Path("docs/development/alpha"), Path("tracked/candidates"))
    before = _state({
        "docs/development/alpha/roadmap.md": "a",
    })
    after = {k: act.ABSENT for k in before}
    assert act.boundary_crossings(before, after, wf.FORBIDDEN_PATHS, permitted) == [], (
        "the exemption is unconditional, so the boundary check is BLIND here — "
        "that blindness is the reason the check below must exist")
    assert act.grants_that_vanished(before, after, permitted) == [
        "docs/development/alpha/roadmap.md",
    ]


# --- what the model is handed ----------------------------------------------

def test_planning_state_distinguishes_FIRST_PLAN_from_EXTEND(tree: Path) -> None:
    """Two genuinely different jobs, and an unlabelled listing conflates them."""
    c = _component(tree)
    first = own.planning_state(c, tree)
    assert "FIRST time" in first and "phase1_" in first
    assert "EXTENDED" not in first

    _write(c, "roadmap.md")
    _write(c, "phase1_a.md")
    _write(c, "phase4_d.md")
    extend = own.planning_state(c, tree)
    assert "EXTENDED" in extend
    assert "next free phase number is 5" in extend, (
        "max+1, counted in code — a model asked to count them will eventually "
        "miscount, and the cost is a colliding identity")
    assert "gaps (1, 4)" in extend and "a gap "  in extend, (
        "a gap must be reported WITH its rule; reporting the sequence alone "
        "invites tidying it")


def test_research_inventory_reports_an_EMPTY_pool_with_its_zero(tree: Path) -> None:
    """An unread pool is otherwise invisible, and a missing one reads as fine.

    A component whose research never ran is a component whose plan is about to be
    written from priors — the single most useful thing this block can say before
    the run starts.
    """
    c = _component(tree)
    empty = own.research_inventory(c, tree)
    assert "0 paper(s)" in empty and "NO `synthesis.md`" in empty
    assert "priors" in empty

    (c / "research" / "synthesis.md").write_text("# s\n")
    (c / "research" / "raw" / "p.md").write_text("# p\n")
    full = own.research_inventory(c, tree)
    assert "1 paper(s)" in full and "`synthesis.md` present" in full
    assert "`p.md`" in full, "the paper list is the coverage check"

    missing = own.research_inventory(_component(tree, "beta"), tree)
    assert "DOES NOT EXIST" in missing


# --- the CLI contract ------------------------------------------------------

def test_the_shim_invokes_its_OWN_runner() -> None:
    """`test_shim_usage_names_itself` holds the usage block; this holds the exec.

    Three shims once carried usage lines copied from the file they were cloned
    from. The `exec` line is the other half of the same class and nothing checked
    it — a shim that runs a DIFFERENT workflow has a different model key and a
    different turn budget.
    """
    shim = Path(__file__).resolve().parents[2] / "scripts" / "plan_draft.sh"
    text = shim.read_text()
    assert "run_plan_draft.py" in text
    assert re.search(r"^#\s+\./plan_draft\.sh", text, re.M), (
        "the usage block must invoke this shim by its own name")


def test_the_runner_REFUSES_a_component_outside_the_repo(tmp_path: Path, capsys) -> None:
    """Two independent operator inputs, and `../` between them escapes the tree.

    `--repo` and the component path are parsed separately, so nothing else stops
    `../../elsewhere` from planning a directory the run is not reviewing — and a
    plan written outside the worktree is invisible to the PR.

    THE REPO IS A REAL GIT REPO, AND THAT IS THE ASSERTION RATHER THAN SETUP.
    This test shipped against a bare `mkdir`, so `preflight` refused it with *not
    inside a git repository* and the run returned 1 without the escape check ever
    executing: the exit code was right, the reason was a different guard, and
    deleting the `is_relative_to` check outright would not have failed it. The
    message is asserted for the same reason — an exit code alone cannot tell two
    refusals apart, which is exactly how this passed vacuously.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    import run_plan_draft as runner

    repo = tmp_path / "repo"
    (repo / "docs" / "development").mkdir(parents=True)
    (repo / "development").mkdir(parents=True, exist_ok=True)
    (repo / "development" / "sprints.md").write_text("# Sprints\n")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (tmp_path / "outside").mkdir()

    assert runner.main(["../outside", "--repo", str(repo)]) == 1
    assert "resolves outside the repo" in capsys.readouterr().err, (
        "the run was refused by some OTHER guard — this test is not exercising "
        "the escape check it names")


# --- the guard SEQUENCE, driven end to end ---------------------------------

def _harness(monkeypatch: pytest.MonkeyPatch, tree: Path, writes):
    """Wire `run_plan_draft` to a fake model that mutates the tree; return the call.

    THE ONLY TEST HERE THAT GOES THROUGH THE ORCHESTRATOR, and the gap it closes
    is a real one: every other assertion in this module drives a comparator in
    isolation, so all of them stayed green while the workflow raised the WRONG
    guard's message for its own primary case. A renumbered phase doc is both a
    vanished grant and a lost identity, and with the generic check first the
    identity message — the only place the rule is explained — was unreachable.

    The fake offends the way a real run does, by writing to the worktree, rather
    than by patching a guard's inputs.

    `worktree_state` IS STUBBED BUT NOT SILENCED, and the difference decides
    whether the ordering assertion means anything. The fixture tree is not a git
    repository, so the real reader cannot run — but a stub returning `{}` makes
    `grants_that_vanished` empty on every input, which is precisely the guard the
    ordering test claims to be ordered AGAINST. This one mimics git instead: a
    path once reported stays reported, and a file that is gone reads as
    `act.ABSENT`. Written flat first, and it passed while asserting nothing.
    """
    cands = tree / "tracked" / "candidates"
    cands.mkdir(parents=True, exist_ok=True)
    (cands / "C-d1uhacwn.md").write_text(
        "---\nid: C-d1uhacwn\ntitle: a candidate\nstatus: open\ncount: 1\n"
        "filed: 2026-08-26\nfiled_by: test\ncomponent: \nsize: feature\n"
        "decision: \n---\n\nn\n")

    comp, seen = _component(tree), set()

    def snapshot(*_a: object, **_k: object) -> dict[str, str]:
        seen.update(p.name for p in comp.iterdir()
                    if p.is_file() and p.suffix == ".md")
        return {f"docs/development/alpha/{n}":
                ("digest" if (comp / n).is_file() else act.ABSENT) for n in seen}

    monkeypatch.setattr(act, "worktree_state", snapshot)
    monkeypatch.setattr(act, "evidence_block", lambda *a, **k: "<evidence>")
    monkeypatch.setattr(act, "run_claude",
                        lambda prompt, **kw: (writes(), "https://github.com/o/r/pull/9")[1])

    return lambda: wf.run_plan_draft(repo_root=tree, worktree=tree,
                                       component=_component(tree),
                                       candidates_path=cands)


def _drive(monkeypatch: pytest.MonkeyPatch, tree: Path, writes) -> str:
    """`_harness`, asserting the run FAILS, and returning the operator's message.

    Split from `_harness` so a test can also assert a run SUCCEEDS. That
    direction is not symmetry for its own sake: a guard that fires when it should
    not is as much a defect as one that stays silent, and only a passing run can
    show it. See `test_a_PRE_EXISTING_violation_of_a_PROHIBITION_does_not_fail_a
    _clean_run`, which was red before `hour_hits` made the hour guard a delta.
    """
    with pytest.raises(RuntimeError) as exc:
        _harness(monkeypatch, tree, writes)()
    return str(exc.value)


def test_a_RENUMBER_raises_the_IDENTITY_message_not_the_generic_one(
        tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The specific diagnostic must be the one an operator actually sees."""
    c = _component(tree)
    _write(c, "roadmap.md")
    _write(c, "phase2_the_thing.md")

    message = _drive(monkeypatch, tree,
                     lambda: (c / "phase2_the_thing.md").rename(c / "phase3_the_thing.md"))
    assert "NAMES the phase for life" in message, (
        f"the renumber raised a different guard's message: {message}")
    assert "cease to exist" not in message


def test_an_UNNUMBERED_plan_doc_fails_the_run(
        tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`the_run_bag.md` reaches the naming guard through the orchestrator too."""
    c = _component(tree)
    _write(c, "roadmap.md")
    _write(c, "phase1_a.md")

    message = _drive(monkeypatch, tree, lambda: _write(c, "the_run_bag.md"))
    assert "the_run_bag.md" in message and "exactly two kinds" in message


# --- CLASS CHECKS: what the guards do NOT look at --------------------------
#
# Three passes on this workflow have each found a SCOPE defect and no other kind:
# a regex crossing a sentence, a grant crossing a directory, a sweep missing a
# filename class, an ordering hiding a message, a comparator that never compared
# new against new, a guard reading state where the prohibition is about a delta.
# Enumerating those instances does not converge — the two tests below key on the
# CLASS instead, so the NEXT member fails here rather than being found by a
# fourth pass.

def test_a_PRE_EXISTING_violation_of_a_PROHIBITION_does_not_fail_a_clean_run(
        tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CLASS: a prohibition guard judges what THIS RUN DID, never what the tree IS.

    Every prohibition here is about the run's own conduct, so a component that
    ALREADY violates one must not fail a run that violated nothing. Seeded with
    one pre-existing instance of all four — a ticked box, an hour estimate, a
    non-conformant filename, and a phase number in use — and a run whose only act
    is to add one legal phase doc.

    THIS WAS RED, and on exactly one of the four: `hour_estimates` scanned
    post-run STATE, so an estimate somebody else wrote failed the run with a
    message asserting *"plan-draft wrote 1 hour estimate(s)"*. Reproduced
    against `docs/development/reviews/`, which carries `~7h` and `~12.8 hours`
    today, and against `plan-revision` — the unsplit planner that DOES size work,
    so any component it planned is one this workflow could never extend.

    A FIFTH GUARD ADDED LATER AND KEYED ON STATE FAILS HERE, which is the point.
    Add its pre-existing instance to the seed above when you add the guard.
    """
    c = _component(tree)
    _write(c, "roadmap.md", "# alpha\n\n- [x] a box ticked before this run existed\n")
    _write(c, "phase1_a.md", "An earlier planner sized this at ~30 hrs.\n")
    _write(c, "phase7_b.md", "# seven\n")
    _write(c, "the_run_bag.md", "a name that predates the naming rule\n")

    url = _harness(monkeypatch, tree, lambda: _write(c, "phase8_new.md", "# eight\n"))()
    assert url == "https://github.com/o/r/pull/9"


_LOOKALIKES = ["phase_notes.txt", "phase9_x.md.bak", "phase3.markdown", "phase2.md.txt"]


@pytest.mark.parametrize("name", _LOOKALIKES)
def test_a_non_markdown_LOOKALIKE_is_a_phase_doc_to_NEITHER_reader(
        tree: Path, name: str) -> None:
    """CLASS: the two filename classifiers agree on what counts as a plan file.

    `plan_docs` requires `.md` because it must equal the write grant.
    `phase_docs` is deliberately WIDER on the stem — `^phase` case-insensitively,
    so a legacy `Phase3.md` is still a phase doc whose deletion is an offence —
    and it was wider on the SUFFIX too, which was not deliberate. Two consequences
    reproduced: `planning_state` reported a `.txt` to the model under the label
    *"Counted in code, authoritative — do not recount"*, and the
    `if not after_phase` deliverable guard was satisfied by one.

    A third classifier added later that disagrees with these two fails here.
    """
    c = _component(tree)
    _write(c, name, "not a plan document\n")
    assert name not in own.phase_docs(c), "phase_docs read a non-markdown file"
    assert name not in own.plan_docs(c), "plan_docs read a non-markdown file"
    assert own.phase_identity(name) is None and own.phase_number(name) is None


def test_a_LOOKALIKE_does_not_satisfy_the_DELIVERABLE_guard(
        tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The consequence, through the orchestrator: zero phase docs must fail."""
    c = _component(tree)
    _write(c, "phase_notes.txt", "scratch notes\n")

    message = _drive(monkeypatch, tree, lambda: _write(c, "roadmap.md"))
    assert "produced no phase doc" in message, (
        f"a stray non-markdown file satisfied the deliverable guard: {message}")


def test_two_NEW_phase_docs_may_not_claim_the_SAME_number(tree: Path) -> None:
    """CLASS: a before/after comparator must also compare new against NEW.

    `taken` was built once from `before` and never grew, so two files written in
    the SAME dispatch collided with nothing. Both shipped, both called Phase 5 —
    straight past the one guard that makes a number an identity.
    """
    assert own.reused_phase_numbers({}, {"phase5_a.md": "h", "phase5_b.md": "h"}) == [
        ("phase5_b.md", 5)]


def test_SUB_LETTERS_planned_in_ONE_pass_stay_legal(tree: Path) -> None:
    """The carve-out the fix above must not eat. Rule 6, quoted in `phase_identity`."""
    assert own.reused_phase_numbers(
        {}, {"phase5a_poc.md": "h", "phase5b_rollout.md": "h"}) == []


def test_a_RETROACTIVE_sub_letter_is_still_an_offence(tree: Path) -> None:
    """Rule 6's own failure mode (c): `phase5b_` arriving after `phase5a_` shipped."""
    assert own.reused_phase_numbers(
        {"phase5a_poc.md": "h"},
        {"phase5a_poc.md": "h", "phase5b_late.md": "h"}) == [("phase5b_late.md", 5)]


def test_a_BARE_number_and_a_LETTERED_one_in_one_run_collide(tree: Path) -> None:
    """A phase cannot be both chunked and not. `phase5_` + `phase5a_` is ambiguous."""
    assert own.reused_phase_numbers(
        {}, {"phase5_a.md": "h", "phase5a_b.md": "h"}) == [("phase5a_b.md", 5)]


# --- the phase precount is over IDENTITIES, not filenames ---------------------

def test_a_phase_named_only_in_the_ROADMAP_is_taken(tmp_path) -> None:
    """The defect the first-ever plan-draft run hit, reproduced.

    `workflow-decomposition` had three phases in `roadmap.md` and ZERO phase
    docs, so a filename-only count reported none taken and `planning_state` said
    *"a new phase starts at 1"* — under a header reading **Counted in code,
    authoritative — do not recount.** Numbering from 1 would have collided with
    three live identities and orphaned every reference to them.
    """
    c = tmp_path / "comp"
    c.mkdir()
    (c / "roadmap.md").write_text(
        "### Phase 1 — done\n### Phase 2 — live\n### Phase 3 — ahead\n"
    )
    assert own.taken_phase_numbers(c) == {1, 2, 3}
    assert "next free phase number is 4" in own.planning_state(c, tmp_path)


def test_a_RETIRED_phase_number_is_still_taken(tmp_path) -> None:
    """The second defect, found by the fix for the first one.

    The same roadmap said *"What used to be Phase 4 … moved to Assistant Workflow
    Design"* — a number RETIRED, never reusable, because commit messages and
    sprint bullets still point at it. The run numbered its new phases 4, 5, 6 and
    took it. Prose is where a retirement is recorded, so prose is where the count
    has to look.
    """
    c = tmp_path / "comp"
    c.mkdir()
    (c / "roadmap.md").write_text(
        "### Phase 1 — done\n\nWhat used to be Phase 4 moved to another component.\n"
    )
    assert own.taken_phase_numbers(c) == {1, 4}
    state = own.planning_state(c, tmp_path)
    assert "next free phase number is 5" in state
    assert "a gap is not a free number" in state.lower()


def test_the_first_time_path_is_UNCHANGED(tmp_path) -> None:
    """No roadmap and no docs still means start at 1 — the fix must not widen."""
    c = tmp_path / "comp"
    c.mkdir()
    assert own.taken_phase_numbers(c) == set()
    assert "Numbering starts at `phase1_`" in own.planning_state(c, tmp_path)


def test_every_pr_accepting_plan_runner_bases_its_worktree_ON_THE_PR() -> None:
    """A `--pr` pass must open its worktree on the PR's branch, not on `main`.

    ALL FOUR HAD THE SAME LINE. `worktree_add(..., "HEAD")` is correct for a
    fresh run and wrong for a correction pass, and nothing distinguished them —
    so `--pr` changed where the run PUSHED and never where it STARTED.

    Measured on plan-draft's first correction pass: the counted-in-code block
    reported "0 phase doc(s)", true of the worktree it was handed and false of
    the four documents it was told to correct. The run detected the mismatch,
    fetched the branch and checked it out itself, and said so in its reflection.
    A run rescuing itself from its own harness is not a control.

    Asserted over a DISCOVERED set rather than a list, so a fifth runner that
    gains `--pr` is covered on the day it does.
    """
    scripts = Path(__file__).resolve().parents[2] / "scripts"
    offenders = []
    for p in sorted(scripts.glob("run_*.py")):
        src = p.read_text()
        if '"--pr"' not in src:
            continue                      # a runner with no --pr cannot have the bug
        if 'worktree_add(repo_root, worktree_name, "HEAD")' in src:
            offenders.append(p.name)
    assert not offenders, (
        "these runners accept --pr and still base the worktree on HEAD, so a "
        "correction pass starts from the default branch with none of the PR's "
        "work in it:\n  " + "\n  ".join(offenders)
        + "\n\nDerive the ref instead:\n"
        '    ref = f"origin/{act.branch_of(a.pr_number, repo_root)}" if a.pr_number else "HEAD"'
    )

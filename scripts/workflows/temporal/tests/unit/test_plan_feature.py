"""`plan-feature`'s four own prohibitions, and the readers that observe them.

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
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from modules.assistant.plan import plan_activities as act  # noqa: E402
from modules.assistant.plan.plan_feature import plan_feature_activities as own  # noqa: E402
from modules.assistant.plan.plan_feature import plan_feature_workflow as wf  # noqa: E402


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
    before = own.phase_docs(c)
    _write(c, "roadmap.md", "# Alpha\n\n- [ ] a criterion\n")
    _write(c, "phase1_the_first_thing.md", "# Phase 1\n\n- [ ] a step\n")
    _write(c, "phase2b_a_sub_letter.md", "# Phase 2b\n")
    after = own.phase_docs(c)

    assert own.malformed_phase_docs(before, after) == []
    assert own.reused_phase_numbers(before, after) == []
    assert own.hour_estimates(c, tree) == []
    assert act.ids_deleted(before, after) == []
    assert len(after) == 2, "the phase-doc reader found nothing to judge"


# --- the phase number is IDENTITY ------------------------------------------

@pytest.mark.parametrize("name", [
    "phase_the_thing.md",            # dropped the number — failure mode (b)
    "Phase3_the_thing.md",           # capitalised
    "phase3-the-thing.md",           # no underscore separator
    "phase3_the_thing(old).md",      # parenthetical disambiguation
    "phase3.md",                     # no descriptor
    "phaseA_the_thing.md",           # letter where the number goes
])
def test_a_NEW_phase_doc_outside_the_grammar_is_caught(tree: Path, name: str) -> None:
    """The Documentation Standard's own recommended CI lint, at authoring time.

    Every one of these is a form the standard names as a real failure mode: it
    lists dropping the number, retroactive sub-letters and parenthetical
    disambiguation by name, having watched engineers reach for all three.

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
    before = own.phase_docs(c)
    _write(c, name)
    assert own.malformed_phase_docs(before, own.phase_docs(c)) == [name]


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
    before = own.phase_docs(c)
    _write(c, "phase1_new_work.md")
    assert own.malformed_phase_docs(before, own.phase_docs(c)) == []


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

    (c / "phase2_the_thing.md").rename(c / "phase3_the_thing.md")
    after = own.phase_docs(c)

    assert own.malformed_phase_docs(before, after) == [], "the new name is valid"
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
    permitted = wf.permitted_paths(Path("docs/development/alpha"))
    before = _state({
        "docs/development/alpha/roadmap.md": "a",
        "docs/development/beta/roadmap.md": "a",
        "docs/development/sprint.md": "a",
        "docs/development/alpha/research/synthesis.md": "a",
        "docs/standards/architecture/research/candidates.md": "a",
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
        "markdown plus candidates.md to be granted"
    )


def test_the_grant_reaches_NO_subdirectory_of_the_component(tree: Path) -> None:
    """`research/` is the subdirectory that matters, and it is not the only one.

    The grant is expressed as a SHAPE — files directly in the component — rather
    than as a second deny rule naming `research/`, so a component that later
    grows `notes/` or `diagrams/` is covered with no rule to remember. Asserted
    over a directory that does not exist today, which is the whole claim.
    """
    permitted = wf.permitted_paths(Path("docs/development/alpha"))
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
    permitted = wf.permitted_paths(Path("docs/development/alpha"))
    before = _state({"docs/development/alpha-two/roadmap.md": "a"})
    after = {k: "CHANGED" for k in before}
    assert act.boundary_crossings(
        before, after, wf.FORBIDDEN_PATHS, permitted) == [
        "docs/development/alpha-two/roadmap.md"]


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
    permitted = wf.permitted_paths(Path("docs/development/alpha"))
    before = _state({
        "docs/development/alpha/roadmap.md": "a",
        "docs/standards/architecture/research/candidates.md": "a",
    })
    after = {k: act.ABSENT for k in before}
    assert act.boundary_crossings(before, after, wf.FORBIDDEN_PATHS, permitted) == [], (
        "the exemption is unconditional, so the boundary check is BLIND here — "
        "that blindness is the reason the check below must exist")
    assert act.grants_that_vanished(before, after, permitted) == [
        "docs/development/alpha/roadmap.md",
        "docs/standards/architecture/research/candidates.md",
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
    shim = Path(__file__).resolve().parents[2] / "scripts" / "plan_feature.sh"
    text = shim.read_text()
    assert "run_plan_feature.py" in text
    assert re.search(r"^#\s+\./plan_feature\.sh", text, re.M), (
        "the usage block must invoke this shim by its own name")


def test_the_runner_REFUSES_a_component_outside_the_repo(tmp_path: Path) -> None:
    """Two independent operator inputs, and `../` between them escapes the tree.

    `--repo` and the component path are parsed separately, so nothing else stops
    `../../elsewhere` from planning a directory the run is not reviewing — and a
    plan written outside the worktree is invisible to the PR.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    import run_plan_feature as runner

    (tmp_path / "repo" / "docs" / "development").mkdir(parents=True)
    (tmp_path / "outside").mkdir()
    assert runner.main(["../outside", "--repo", str(tmp_path / "repo")]) == 1

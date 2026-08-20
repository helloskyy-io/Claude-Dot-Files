"""`plan-verify`'s own guards, and the two properties that are unique to a JUDGE.

WHAT IS AND IS NOT COVERED HERE. The registries are held elsewhere and
generically: `test_authorization_is_observed.py` proves every `You MAY NOT` row
names a mechanism that EXISTS, and `test_disappearance_is_observed.py` proves
every before/after snapshot names what watches it for absence. Both DISCOVER this
workflow by AST rather than being told about it. Neither proves any guard FIRES,
which is what this module is for.

TWO OF THESE PROPERTIES DO NOT EXIST ANYWHERE ELSE IN THE FAMILY, and they are
the ones worth attacking:

  * **The deliverable guard is keyed on STATE, and every prohibition guard in
    this family is keyed on a DELTA.** That asymmetry is deliberate and it is
    exactly the kind of thing a later pass "fixes" into a delta for consistency.
    A `--pr` correction pass legitimately writes no new hours — last pass's
    estimates are already in the roadmap — so a delta-shaped deliverable guard
    fails precisely the pass most likely to be the last one anybody reads.
    `test_a_CORRECTION_PASS_that_writes_no_new_hours_is_not_UNSIZED` is that
    fixture, and a fixture that only ever ADDS is symmetric under the defect.

  * **The re-planning guard watches the INSIDE of the one file the grant
    opens.** `boundary_crossings` exempts `roadmap.md` unconditionally — it must,
    since writing it is the job — so it is blind by construction to a judge that
    drops a phase it disagreed with. That is `plan-sprint`'s measured
    disappearance defect one altitude down, and the fixture has to move a link
    rather than change a character.

AND THE BOUNDARY FIXTURE IS NOT THE WRITE HALF'S. `plan-feature`'s grant is a
SHAPE — every markdown file directly in the component — so its boundary tests use
two components, because one component says nothing about a sibling. This
workflow's grant is ONE NAMED FILE inside a component it may otherwise not touch,
so the discriminating fixture is a phase doc in its OWN component: a test that
only ever denies a sibling reads correct whether or not the grant leaks to the
file next to the roadmap, which is the whole difference between a reader and a
second author.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from modules.assistant.plan import plan_activities as act  # noqa: E402
from modules.assistant.plan.plan_verify import plan_verify_activities as own  # noqa: E402
from modules.assistant.plan.plan_verify import plan_verify_workflow as wf  # noqa: E402

_SIZED_ROADMAP = (
    "# Alpha\n\n"
    "## Phase 1 — the first thing (~8 hrs)\n"
    "See [`phase1_the_first_thing.md`](phase1_the_first_thing.md).\n\n"
    "- [ ] a criterion\n\n"
    "## Phase 2 — the gated one (~12 hrs)\n"
    "See [`phase2_the_gated_one.md`](phase2_the_gated_one.md).\n"
)


# The repo's own candidates path, passed EXPLICITLY because the grant is now
# derived from the argument rather than hard-coded. Named once so the boundary
# tests below read as being about the COMPONENT half, which is what they test.
_CANDS = Path("docs/standards/architecture/research/candidates.md")


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


def _planned(tree: Path, roadmap: str = _SIZED_ROADMAP) -> Path:
    """A component as `plan-feature` leaves it, plus whatever roadmap is passed."""
    c = _component(tree)
    _write(c, "phase1_the_first_thing.md", "# Phase 1\n\n- [ ] a step\n")
    _write(c, "phase2_the_gated_one.md", "# Phase 2\n")
    _write(c, own.ROADMAP, roadmap)
    return c


# --- vacuity floor ---------------------------------------------------------

def test_a_SIZED_plan_satisfies_EVERY_reader(tree: Path) -> None:
    """THE FLOOR. If this does not pass, every assertion below is vacuous — a
    guard that rejects correct work is indistinguishable from one that works."""
    c = _planned(tree)

    assert sum(own.roadmap_hours(c).values()) == 2
    assert len(own.phase_docs_of(c)) == 2
    assert sum(own.roadmap_phase_links(c).values()) >= 2, (
        "the link reader found nothing to compare, so the re-planning guard "
        "would pass vacuously on this fixture")
    assert act.checked_boxes(c / own.ROADMAP) == Counter(), "no box is ticked"


# --- the DELIVERABLE: sizing, scoped to the roadmap ------------------------

@pytest.mark.parametrize("text,matched", [
    ("## Phase 1 — the thing (~30 hrs)", "~30 hrs"),
    # The LABEL alternative wins here, not the tilde one — `sizing` starts
    # earlier in the line, so the span carries the label with it. That is
    # invisible to a count-only assertion and it decides the Counter's key.
    ("Sizing: ~8h", "Sizing: ~8h"),
    ("Delivers the bag (12 hours)", "(12 hours)"),
    ("Estimated at 40 hours across two engineers", "Estimated at 40 hours"),
    ("Est. 2.5 hours", "Est. 2.5 hours"),
])
def test_an_hour_estimate_in_the_ROADMAP_counts(
        tree: Path, text: str, matched: str) -> None:
    """The shape this workflow must PRODUCE is the shape `plan-feature` forbids.

    ONE PATTERN, TWO OPPOSITE CONSUMERS. `act.HOUR_ESTIMATE` is shared between
    them for exactly that reason: two copies would let the write half forbid a
    spelling the read half does not produce, or the read half satisfy itself with
    one the write half would have rejected — and neither shows in a diff.

    THE MATCHED SPAN IS ASSERTED, NOT JUST THE COUNT. `roadmap_hours` keys its
    Counter on that span, so what it captures decides whether two differently
    worded estimates of the same size count as one or two — and the tilde
    alternative wins over the parenthetical one on `(~30 hrs)`, which is exactly
    the kind of thing a count-only assertion cannot see.
    """
    c = _component(tree)
    _write(c, own.ROADMAP, f"# Alpha\n\n{text}\n")
    assert own.roadmap_hours(c) == Counter({matched: 1})


def test_a_citation_names_the_FILE_and_the_LINE(tree: Path) -> None:
    """The operator's next question about an estimate is always WHERE."""
    c = _component(tree)
    _write(c, own.ROADMAP, "# Alpha\n\nintro\n\n## Phase 1 (~8 hrs)\n")
    assert own.hour_citations(c, tree) == [
        "docs/development/alpha/roadmap.md:5: ~8 hrs"]


@pytest.mark.parametrize("line", [
    "ment's figures true for a few hours and then wrong again",
    "has a shelf life measured in hours, and the reading-in",
    "Based on the estimate. It took 3 hours to migrate by hand.",
])
def test_ordinary_prose_about_time_does_NOT_count_as_an_estimate(
        tree: Path, line: str) -> None:
    """The shared pattern's discriminator, exercised from the CONSUMING side too.

    `test_plan_feature.py` owns the argument for the pattern's shape — a
    word-keyed guard fires on three real lines in this tree. It matters here for
    the OPPOSITE reason: a roadmap that merely says "hours" somewhere must not
    satisfy this workflow's deliverable guard, or a run could report a sized plan
    over a component nobody estimated.
    """
    c = _component(tree)
    _write(c, own.ROADMAP, f"# Alpha\n\n{line}\n")
    assert own.roadmap_hours(c) == Counter()


def test_the_sizing_reader_does_NOT_look_at_a_phase_doc(tree: Path) -> None:
    """SCOPE, and it is the design decision rather than an implementation detail.

    Hours live in `roadmap.md` and nowhere else, so an estimate written into a
    phase doc must NOT satisfy the deliverable — otherwise the one-figure-one-home
    rule is prose and the run passes with the number in the wrong file. The
    prohibition half is the write grant, exercised in the boundary section below;
    this is the half that stops the guard accepting a misplaced figure.
    """
    c = _component(tree)
    _write(c, own.ROADMAP, "# Alpha\n\nno numbers here\n")
    _write(c, "phase1_a.md", "# Phase 1\n\nSizing: ~8h\n")
    assert own.roadmap_hours(c) == Counter()
    assert own.hour_citations(c, tree) == []


def test_the_sizing_reader_does_NOT_look_at_the_research_pool(tree: Path) -> None:
    """A synthesis reporting a MEASURED wall-clock is evidence, not an estimate."""
    c = _component(tree)
    _write(c, own.ROADMAP, "# Alpha\n\n(~4 hrs)\n")
    (c / "research" / "synthesis.md").write_text("The sweep took ~3 hours.\n")
    assert sum(own.roadmap_hours(c).values()) == 1


def test_TWO_phases_sized_IDENTICALLY_count_as_two(tree: Path) -> None:
    """A Counter and not a set, because the floor is a COUNT against the phases.

    Two phases legitimately estimated `~8 hrs` are two estimates. Keyed by text
    into a set they would collapse to one, and a two-phase component sized
    correctly would fail as unsized — a guard failing correct work, which is the
    direction that gets a guard deleted rather than fixed.
    """
    c = _component(tree)
    _write(c, own.ROADMAP, "# Alpha\n\n## P1 (~8 hrs)\n\n## P2 (~8 hrs)\n")
    assert sum(own.roadmap_hours(c).values()) == 2


@pytest.mark.parametrize("name,is_a_reference", [
    ("phase1_the_first_thing.md", True),
    ("phase2a_a_sub_phase.md", True),
    ("phase12_a-b.md", True),
    # THE LEGACY SPELLINGS. `act._LOOKS_LIKE_A_PHASE` accepts these and its own
    # comment says why — *"a legacy PHASE3.MD is a phase doc whoever spelled
    # it"*. The pointer reader required an underscore and therefore did not, so a
    # judge could drop a legacy-named phase's roadmap ENTRY and neither guard saw
    # it: the file was still on disk, and the link was invisible to the link
    # counter. One reader claiming coverage its pair does not reciprocate.
    ("phase3.md", True),
    ("PHASE3.MD", True),
    # AND THE DIGIT IS WHAT KEEPS IT OFF PROSE. Widening far enough to admit
    # these would make the re-planning guard fire on a reworded sentence, which
    # is a guard failing correct work — the direction that gets guards deleted.
    ("phases.md", False),
    ("phase.md", False),
    ("phase_notes.md", False),
])
def test_the_POINTER_reader_matches_every_name_the_FILE_reader_would(
        tree: Path, name: str, is_a_reference: bool) -> None:
    """THE PAIR HAS TO AGREE, because neither guard covers the gap alone.

    `phase_docs_of` watches the FILE and `roadmap_phase_links` watches the
    POINTER. A name one recognises and the other does not is a phase whose
    roadmap entry can be deleted with the file left in place — invisible to the
    disappearance guard (nothing vanished) and to the link guard (it never
    counted the link). Asserted per name rather than as a rule, so the two
    readers' disagreement is what fails rather than someone noticing it.
    """
    c = _component(tree)
    _write(c, own.ROADMAP, f"# Alpha\n\nSee [`{name}`]({name}).\n")
    assert bool(own.roadmap_phase_links(c)) is is_a_reference
    if is_a_reference:
        _write(c, name)
        assert name in own.phase_docs_of(c), (
            "the FILE reader must accept every name the POINTER reader does, or "
            "the pair disagrees in the other direction")


def test_ordinary_roadmap_PROSE_is_not_read_as_a_phase_reference(tree: Path) -> None:
    """NEGATIVE CONTROL for the widening above, on real sentences.

    The re-planning guard compares link counts either side of the run, so a
    reader that matched prose would fire on a judge REWORDING a paragraph — which
    is a legitimate act on the one file it may write.
    """
    c = _component(tree)
    _write(c, own.ROADMAP,
           "# Alpha\n\nSee Phase 3 of the memory doc. Phase 12 delivers the bag.\n"
           "The phase.md convention is dead and phases.md is the index.\n")
    assert own.roadmap_phase_links(c) == Counter()


def test_a_MISSING_roadmap_is_an_empty_counter_and_not_an_error(tree: Path) -> None:
    """The caller turns absence into a message about the plan, not a traceback."""
    assert own.roadmap_hours(_component(tree, "beta")) == Counter()
    assert own.hour_citations(_component(tree, "beta"), tree) == []


# --- RE-PLANNING: the prohibition inside the granted file ------------------

def test_the_link_reader_sees_every_phase_the_roadmap_REFERENCES(tree: Path) -> None:
    c = _planned(tree)
    links = own.roadmap_phase_links(c)
    assert set(links) == {"phase1_the_first_thing.md", "phase2_the_gated_one.md"}
    assert sum(links.values()) == 4, (
        "each phase is referenced twice in the fixture — once in the link text "
        "and once in the target — and the reader counts references rather than "
        "distinct names, so a phase whose SECOND mention is deleted is still seen")


def test_a_DROPPED_phase_reference_is_the_offence_the_boundary_cannot_see(
        tree: Path) -> None:
    """THE FIXTURE WHERE THE TWO MECHANISMS DISAGREE, which is why it exists.

    `roadmap.md` is a permitted path, and `boundary_crossings` exempts a
    permitted path UNCONDITIONALLY — so a judge that deleted a phase it
    disagreed with produces no crossing at all. That is `plan-sprint`'s measured
    disappearance defect one altitude down: the file an override exists FOR is
    the file whose contents nothing watches.

    The input's SHAPE changes here — a reference leaves — rather than a value,
    because a single-character mutation of the roadmap is caught by nothing and
    proves nothing.
    """
    c = _planned(tree)
    before = own.roadmap_phase_links(c)
    permitted = wf.permitted_paths(Path("docs/development/alpha"), _CANDS)

    (c / own.ROADMAP).write_text(
        "# Alpha\n\n## Phase 1 — the first thing (~8 hrs)\n"
        "See [`phase1_the_first_thing.md`](phase1_the_first_thing.md).\n")
    after = own.roadmap_phase_links(c)

    assert sorted((before - after).elements()) == [
        "phase2_the_gated_one.md", "phase2_the_gated_one.md"], (
        "the link reader is the ONLY mechanism that sees a phase dropped from "
        "the plan; if this stops firing, a judge can re-plan the component "
        "through the one file it may write")
    assert act.boundary_crossings(
        {"docs/development/alpha/roadmap.md": "a"},
        {"docs/development/alpha/roadmap.md": "b"},
        wf.FORBIDDEN_PATHS, permitted) == [], (
        "the boundary check is BLIND here by construction — that blindness is "
        "the entire reason the link reader has to exist")


def test_an_ADDED_phase_reference_is_also_an_offence(tree: Path) -> None:
    """Both directions. Adding a phase is writing a plan rather than judging one."""
    c = _planned(tree)
    before = own.roadmap_phase_links(c)
    (c / own.ROADMAP).write_text(
        _SIZED_ROADMAP + "\n## Phase 3 — one I thought of (~4 hrs)\n"
        "See [`phase3_one_i_thought_of.md`](phase3_one_i_thought_of.md).\n")
    assert sorted(set((own.roadmap_phase_links(c) - before).elements())) == [
        "phase3_one_i_thought_of.md"]


def test_writing_only_the_HOURS_moves_no_link(tree: Path) -> None:
    """DISCRIMINATOR. Sizing is the job, so it must not read as re-planning.

    Without this the guard could return every reference it saw and every
    assertion above would still pass — while failing every correct run.
    """
    c = _planned(tree, roadmap=_SIZED_ROADMAP.replace(" (~8 hrs)", "").replace(" (~12 hrs)", ""))
    before = own.roadmap_phase_links(c)
    (c / own.ROADMAP).write_text(_SIZED_ROADMAP)
    after = own.roadmap_phase_links(c)
    assert before == after
    assert sum(own.roadmap_hours(c).values()) == 2, "and the hours DID land"


def test_a_legacy_phase_name_is_still_a_reference(tree: Path) -> None:
    """The reader asks *what does the roadmap point at*, not *is that name legal*.

    `plan_feature_activities._PHASE_FILE` judges a name a run WROTE. A
    non-conformant legacy doc a roadmap already links is still a phase this
    workflow must not drop, so the two classifiers deliberately differ and the
    looser one belongs here.
    """
    c = _component(tree)
    _write(c, own.ROADMAP, "# Alpha\n\nSee [x](PHASE3_The-Thing.md) (~2 hrs)\n")
    assert set(own.roadmap_phase_links(c)) == {"phase3_the-thing.md"}, (
        "matched case-insensitively and folded to one key, so a reference that "
        "merely changed case does not read as one phase dropped and another added")


# --- what the model is handed ----------------------------------------------

def test_the_inventory_REFUSES_a_component_with_no_plan(tree: Path) -> None:
    """There is nothing to verify, and the honest instruction is to stop.

    The dangerous alternative is silence: a judge handed an empty directory and
    told to size it will write the plan, which is the one thing this workflow
    holds no grant for and the one failure a fresh-context reviewer must not
    commit.
    """
    block = own.plan_inventory(_component(tree, "beta"), tree)
    assert "no `roadmap.md`" in block and "NO PLAN HERE TO VERIFY" in block
    assert "Do not write one" in block


def test_the_inventory_NAMES_every_phase_doc_rather_than_counting_them(
        tree: Path) -> None:
    """A judge told "read the plan" reads the roadmap and stops.

    The decomposition being judged lives in the phase docs, so they are listed by
    name — an enumeration leaves no exit that a count does.
    """
    c = _planned(tree)
    block = own.plan_inventory(c, tree)
    assert "2 phase doc(s)" in block
    assert "`docs/development/alpha/phase1_the_first_thing.md`" in block
    assert "`docs/development/alpha/phase2_the_gated_one.md`" in block
    assert "GATED phase" in block, (
        "a roadmap entry with no phase doc must be named as a phase that still "
        "gets an estimate; without it the floor reads as the whole requirement")


def test_the_inventory_does_NOT_report_a_CROSS_COMPONENT_link_as_a_phase(
        tree: Path) -> None:
    """FOUND BY RUNNING THE TOOL, not by reading it, and it is a real corpus shape.

    `docs/development/memory-management-framework/roadmap.md` links THREE of
    `persistent-memory-protocol`'s phase docs, so a reference count over that
    real file reads 9 against 6 docs on disk. The reader is deliberately broad —
    the guard wants to see a sibling cross-reference deleted too — but handing a
    model *"9 phase docs referenced"* under a label reading **authoritative, do
    not recount** is a false statement in the one block whose whole job is to
    stop a run inventing a state, and the obvious inference from it is that
    three phase docs are missing.

    Asserted through the DIVERGENCE rather than through a count, so a fixture
    where the two numbers happen to agree cannot pass this vacuously.
    """
    c = _planned(tree, roadmap=_SIZED_ROADMAP
                 + "\nSee [PMP Phase 1](../beta/phase1_the_run_bag.md) for the "
                   "event this consumes.\n")
    block = own.plan_inventory(c, tree)
    assert "2 phase doc(s) of its own" in block
    assert "3 distinct phase-doc reference(s)" in block
    assert "MORE than it has docs" in block and "SIBLING" in block
    assert "phase1_the_run_bag.md" not in block, (
        "a sibling component's phase must not be listed as one to read and size")


def test_the_inventory_says_nothing_about_siblings_when_the_counts_AGREE(
        tree: Path) -> None:
    """DISCRIMINATOR. The caveat must be conditional, or it is noise on every run.

    Without this the sentence could be unconditional and every assertion above
    would still pass — while telling a run with no cross-references at all to go
    looking for siblings that are not there.
    """
    block = own.plan_inventory(_planned(tree), tree)
    assert "MORE than it has docs" not in block and "SIBLING" not in block


def test_the_inventory_reports_a_MISSING_synthesis_as_a_finding(tree: Path) -> None:
    """Question 4 has no rolled-up answer, and that is worth saying rather than skipping."""
    c = _planned(tree)
    assert "NO `synthesis.md`" in own.plan_inventory(c, tree)

    (c / "research" / "synthesis.md").write_text("# s\n")
    assert "synthesis.md` — read it" in own.plan_inventory(c, tree)


# --- the write boundary: ONE file, inside a component it may not otherwise touch

def _state(paths: dict[str, str]) -> dict[str, str]:
    """A `worktree_state`-shaped map: relative path -> content sentinel."""
    return dict(paths)


def test_the_grant_reaches_the_ROADMAP_and_NOT_the_phase_doc_beside_it(
        tree: Path) -> None:
    """The grant reaches every TOP-LEVEL doc, and stops at the subdirectory.

    WIDENED 2026-08-19, and the old assertion is worth recording because it was
    right for the design it guarded and wrong for this one. It read *"expected
    everything in the component except its roadmap to be a crossing — a phase
    doc most of all, since a judge that may edit one can quietly become its
    author"*. The bundled prohibition it enforced has since been split: this run
    may CORRECT a determined defect in a phase doc and may not RE-PLAN, and the
    re-plan half moved to the observers that always did that work —
    `roadmap_phase_links`, `phase_docs_of`, and `plan_boxes` keyed on box TEXT.

    What still discriminates is the SUBDIRECTORY: `research/` is this run's
    evidence and must stay read-only, and a grant shaped `[^/]+\.md$` reaches no
    subdirectory by construction. That is what this fixture now proves.
    """
    permitted = wf.permitted_paths(Path("docs/development/alpha"), _CANDS)
    before = _state({
        "docs/development/alpha/roadmap.md": "a",
        "docs/development/alpha/phase1_a.md": "a",
        "docs/development/alpha/notes.md": "a",
        "docs/development/alpha/research/synthesis.md": "a",
        "docs/development/beta/roadmap.md": "a",
        "docs/development/sprint.md": "a",
        "docs/standards/architecture/research/candidates.md": "a",
        "docs/standards/architecture/problem-statement.md": "a",
    })
    after = {k: "CHANGED" for k in before}
    assert act.boundary_crossings(before, after, wf.FORBIDDEN_PATHS, permitted) == [
        "docs/development/alpha/research/synthesis.md",
        "docs/development/beta/roadmap.md",
        "docs/development/sprint.md",
        "docs/standards/architecture/problem-statement.md",
    ], (
        "expected every TOP-LEVEL doc in this component to be inside the grant "
        "and `research/` to be outside it — the evidence a run plans against "
        "must not be editable by the run that judges the plan"
    )


def test_a_SIBLING_component_s_roadmap_is_not_granted(tree: Path) -> None:
    """The grant names one component; `roadmap.md` exists in sixteen directories."""
    permitted = wf.permitted_paths(Path("docs/development/alpha"), _CANDS)
    before = _state({"docs/development/beta/roadmap.md": "a"})
    assert act.boundary_crossings(
        before, {k: "CHANGED" for k in before},
        wf.FORBIDDEN_PATHS, permitted) == ["docs/development/beta/roadmap.md"]


def test_a_component_whose_name_PREFIXES_another_is_not_granted_it(tree: Path) -> None:
    """`alpha` must not grant `alpha-two`, which a prefix match would."""
    permitted = wf.permitted_paths(Path("docs/development/alpha"), _CANDS)
    before = _state({"docs/development/alpha-two/roadmap.md": "a"})
    assert act.boundary_crossings(
        before, {k: "CHANGED" for k in before},
        wf.FORBIDDEN_PATHS, permitted) == ["docs/development/alpha-two/roadmap.md"]


def test_the_component_name_is_ESCAPED_before_it_becomes_a_pattern(tree: Path) -> None:
    """A directory name is DATA, and interpolating it raw makes it a pattern.

    The standalone dispatch takes an operator-supplied directory and nothing
    slugs it. A real name carrying a metacharacter — `v2.1-migration` being the
    likeliest — becomes a grant whose `.` matches any character and therefore
    reaches `v2x1-migration/roadmap.md` too. Every other boundary test here uses
    `alpha`, which has no metacharacter to escape.
    """
    permitted = wf.permitted_paths(Path("docs/development/v2.1-migration"), _CANDS)
    before = _state({"docs/development/v2x1-migration/roadmap.md": "a"})
    assert act.boundary_crossings(
        before, {k: "CHANGED" for k in before},
        wf.FORBIDDEN_PATHS, permitted) == [
        "docs/development/v2x1-migration/roadmap.md"], (
        "the grant matched a sibling whose name differs by one character — the "
        "component segment reached the regex unescaped")

    own_file = {"docs/development/v2.1-migration/roadmap.md": "a"}
    assert act.boundary_crossings(
        own_file, {k: "CHANGED" for k in own_file},
        wf.FORBIDDEN_PATHS, permitted) == [], "and its own roadmap is still granted"


def test_the_CANDIDATES_grant_follows_the_operator_s_path(tree: Path) -> None:
    """THE OTHER HALF OF THE BOUNDARY IS ALSO AN ARGUMENT, and it used to be a literal.

    `--candidates` is a documented flag on every runner in this family, and it
    is how a DIFFERENT repository is targeted: `--repo` points at a tree whose
    pool need not sit at this repo's path. With the grant hard-coded, that flag
    guaranteed failure — the prompt was handed `CANDIDATES_PATH` and told to
    append a proposal there, `^docs/standards/` denied the whole tree, and
    `boundary_crossings` read the model obeying its instructions as a crossing.
    A correct run failed at the LAST guard, after all the work.

    ESCAPED, for the reason the component segment is: the path is operator input
    and nothing slugs it.
    """
    elsewhere = Path("docs/standards/architecture/research/pool-v2.md")
    permitted = wf.permitted_paths(Path("docs/development/alpha"), elsewhere)
    moved = {elsewhere.as_posix(): "a"}
    assert act.boundary_crossings(
        moved, {k: "CHANGED" for k in moved},
        wf.FORBIDDEN_PATHS, permitted) == [], (
        "the operator's candidates file was denied, so the run would fail for "
        "doing exactly what its prompt told it to do")

    default = {_CANDS.as_posix(): "a"}
    assert act.boundary_crossings(
        default, {k: "CHANGED" for k in default},
        wf.FORBIDDEN_PATHS, permitted) == [_CANDS.as_posix()], (
        "and the grant did NOT follow the argument — it still reaches the "
        "default path, which means it is a literal wearing a parameter")


def test_every_granted_path_is_also_watched_for_DELETION(tree: Path) -> None:
    """A WRITE GRANT IS NOT A DELETE GRANT, exercised rather than declared.

    A DELETED FILE IS THE `ABSENT` SENTINEL, NOT A MISSING KEY, and the two mean
    OPPOSITE things — an absent key is `BASELINE`, i.e. *git never reported this
    path*, which is how a run may legitimately CREATE a permitted file.
    """
    permitted = wf.permitted_paths(Path("docs/development/alpha"), _CANDS)
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


# --- the CLI contract ------------------------------------------------------

def test_the_shim_invokes_its_OWN_runner() -> None:
    """`test_shim_usage_names_itself` holds the usage block; this holds the exec."""
    shim = Path(__file__).resolve().parents[2] / "scripts" / "plan_verify.sh"
    text = shim.read_text()
    assert "run_plan_verify.py" in text
    assert re.search(r"^#\s+\./plan_verify\.sh", text, re.M), (
        "the usage block must invoke this shim by its own name")


def _runner():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    import run_plan_verify
    return run_plan_verify


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "docs" / "development" / "alpha").mkdir(parents=True)
    (repo / "docs" / "standards" / "architecture" / "research").mkdir(parents=True)
    (repo / "docs" / "standards" / "architecture" / "research"
     / "candidates.md").write_text("| ID |\n")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    return repo


def test_the_runner_REFUSES_a_component_outside_the_repo(
        tmp_path: Path, capsys) -> None:
    """Two independent operator inputs, and `../` between them escapes the tree.

    THE REPO IS A REAL GIT REPO, AND THAT IS THE ASSERTION RATHER THAN SETUP. The
    sibling test shipped against a bare `mkdir`, so `preflight` refused it for a
    DIFFERENT reason and deleting the escape check outright would not have failed
    it. The message is asserted because an exit code alone cannot tell two
    refusals apart.
    """
    repo = _repo(tmp_path)
    (tmp_path / "outside").mkdir()
    assert _runner().main(["../outside", "--repo", str(repo)]) == 1
    assert "resolves outside the repo" in capsys.readouterr().err, (
        "the run was refused by some OTHER guard — this test is not exercising "
        "the escape check it names")


def test_the_runner_REFUSES_a_component_with_NO_roadmap(
        tmp_path: Path, capsys) -> None:
    """The precondition is checked BEFORE a worktree is cut, per issue #49's class.

    Without it the run reaches the UNSIZED post-condition, whose message says
    "you sized nothing" — and the obvious remedy a reader draws from that is to
    write the plan, which is the one thing this workflow may not do. A dead run
    must also leave no orphaned worktree behind it, and preflight is the altitude
    where that is true.
    """
    repo = _repo(tmp_path)
    assert _runner().main(["docs/development/alpha", "--repo", str(repo)]) == 1
    err = capsys.readouterr().err
    assert "no roadmap.md" in err and "plan_feature.sh" in err, (
        f"the refusal must name the missing file AND the workflow that writes "
        f"it; got {err!r}")


# --- the guard SEQUENCE, driven end to end ---------------------------------

def _harness(monkeypatch: pytest.MonkeyPatch, tree: Path, writes):
    """Wire `run_plan_verify` to a fake model that mutates the tree; return the call.

    THE ONLY TESTS HERE THAT GO THROUGH THE ORCHESTRATOR. Every other assertion
    drives a reader in isolation, so all of them stay green while the workflow
    raises the WRONG guard's message — which is a defect the write half actually
    shipped, and the reason its own harness exists.

    The fake offends the way a real run does, by writing to the worktree, rather
    than by patching a guard's inputs.

    `worktree_state` IS STUBBED BUT NOT SILENCED. The fixture tree is not a git
    repository, so the real reader cannot run — but a stub returning `{}` makes
    `grants_that_vanished` empty on every input, which is precisely the guard the
    ordering assertions claim to be ordered against. This one mimics git: a path
    once reported stays reported, and a file that is gone reads as `act.ABSENT`.

    AND IT HASHES CONTENT RATHER THAN RETURNING A CONSTANT, which it did not
    until a test asked it to. With a fixed `"digest"` every surviving file
    compared EQUAL either side, so `boundary_crossings` — the last and broadest
    guard, the one that stands behind every path-scoped row in the
    authorization table — could not fire end to end no matter what the fake
    model wrote. Every ordering assertion that claims a guard runs *instead of*
    the boundary check was therefore true for the wrong reason. A stub is a
    claim about the real reader, and the claim has to hold for the property
    under test.
    """
    cands = tree / "docs" / "standards" / "architecture" / "research" / "candidates.md"
    cands.parent.mkdir(parents=True, exist_ok=True)
    cands.write_text(
        "| ID | Candidate | `component` | Source | `decision` | `status` | Note |\n"
        "|---|---|---|---|---|---|---|\n"
        "| C-001 | a candidate |  | PR #1 |  | `open` | n |\n")

    comp, seen = _component(tree), set()

    def snapshot(*_a: object, **_k: object) -> dict[str, str]:
        # RECURSIVE since 2026-08-19, and the widened grant is why. When this run
        # could write only `roadmap.md`, every top-level sibling of it was a
        # crossing and a non-recursive walk could prove the boundary fires. Now
        # every top-level `.md` is INSIDE the grant, so the only crossing left
        # inside this component is `research/` — invisible to a walk that stops
        # at the directory. A stub that cannot see the one remaining offence
        # makes every assertion about that boundary vacuous.
        seen.update(str(p.relative_to(comp)) for p in comp.rglob("*.md")
                    if p.is_file())
        return {f"docs/development/alpha/{n}":
                (hashlib.sha256((comp / n).read_bytes()).hexdigest()
                 if (comp / n).is_file() else act.ABSENT) for n in seen}

    monkeypatch.setattr(act, "worktree_state", snapshot)
    monkeypatch.setattr(act, "evidence_block", lambda *a, **k: "<evidence>")
    monkeypatch.setattr(act, "run_claude",
                        lambda prompt, **kw: (writes(), "https://github.com/o/r/pull/9")[1])

    return lambda: wf.run_plan_verify(repo_root=tree, worktree=tree,
                                      component=_component(tree),
                                      candidates_path=cands)


def _drive(monkeypatch: pytest.MonkeyPatch, tree: Path, writes) -> str:
    """`_harness`, asserting the run FAILS, and returning the operator's message."""
    with pytest.raises(RuntimeError) as exc:
        _harness(monkeypatch, tree, writes)()
    return str(exc.value)


def test_a_SIZED_run_returns_the_PR_URL(
        tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """THE FLOOR FOR THE ORCHESTRATOR. A guard that fires on correct work is a defect."""
    c = _planned(tree, roadmap=_SIZED_ROADMAP.replace(" (~8 hrs)", "").replace(" (~12 hrs)", ""))
    url = _harness(monkeypatch, tree,
                   lambda: (c / own.ROADMAP).write_text(_SIZED_ROADMAP))()
    assert url == "https://github.com/o/r/pull/9"


def test_a_run_that_SIZES_NOTHING_fails_as_UNSIZED(
        tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sizing is the deliverable; a judge that only reported would ship it silently."""
    c = _planned(tree, roadmap=_SIZED_ROADMAP.replace(" (~8 hrs)", "").replace(" (~12 hrs)", ""))
    message = _drive(monkeypatch, tree, lambda: (c / own.ROADMAP).write_text(
        (c / own.ROADMAP).read_text() + "\nRead it and it looks fine.\n"))
    assert "UNSIZED" in message
    assert "0 hour estimate(s) against a floor of 2, from 2 phase doc(s)" in message


def test_a_PARTIALLY_sized_plan_fails_too(
        tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The floor is a COUNT of estimates against a COUNT of phases, not a boolean.

    One estimate on a two-phase component is the likelier miss than none at all —
    a run that sizes the phase it understood and skips the gated one — and a
    boolean "are there any hours" guard would pass it. The message shows what IS
    there so the operator can see which phase was skipped.
    """
    c = _planned(tree, roadmap=_SIZED_ROADMAP.replace(" (~12 hrs)", ""))
    message = _drive(monkeypatch, tree, lambda: None)
    assert "1 hour estimate(s) against a floor of 2, from 2 phase doc(s)" in message
    assert "roadmap.md:3: ~8 hrs" in message, (
        "the message must cite what WAS written; 'somewhere in the roadmap' "
        "sends the operator to grep for it")


@pytest.mark.parametrize("docs", [0, 1, 2, 5])
def test_the_sizing_floor_is_NEVER_ZERO_however_many_phase_docs_exist(
        tree: Path, docs: int) -> None:
    """CLASS: A THRESHOLD DERIVED FROM A COUNT THAT CAN BE ZERO IS A GUARD ITS
    OWN INPUT CAN SWITCH OFF.

    KEYED ON THE CLASS AND NOT ON THE INSTANCE, which is the whole point of
    parameterising over the doc count rather than asserting the all-gated case
    alone. The shipped guard read `sum(hours) < len(phase_docs)` inline. Every
    word of the argument above it was true — narrower is safe, a floor cannot
    fail a correct run — and all of it stopped applying at zero, where `sum < 0`
    is unsatisfiable and the guard is not narrow but ABSENT. A run could write no
    estimates at all, raise nothing, and print `SIZED` at the operator.

    ZERO IS NOT A HYPOTHETICAL SHAPE HERE, it is the one the design decision was
    made FOR: hours live in `roadmap.md` rather than in phase docs precisely
    because a GATED phase has a roadmap entry and no doc, and a component whose
    phases are all gated therefore has no docs at all.

    A later change that tightens the floor toward the true phase count SHOULD
    keep this green — it asserts a lower bound, not an exact figure. A change
    that makes it fail has re-derived the floor from something that can vanish.
    """
    c = _component(tree)
    for n in range(docs):
        _write(c, f"phase{n + 1}_a_thing.md")
    _write(c, own.ROADMAP, "# Alpha\n\n## Phase 1 — gated on the fleet\n")
    assert own.sizing_floor(c, own.phase_docs_of(c)) >= 1
    assert own.sizing_floor(c, own.phase_docs_of(c)) >= docs


def test_a_component_with_NO_phase_docs_at_all_still_fails_as_UNSIZED(
        tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """THE SHIPPED DEFECT, DRIVEN END TO END. Discriminator for the fix above.

    Reverting `sizing_floor` to `len(docs)` makes this the ONE test that fails —
    the run returns the PR URL, the operator is told `SIZED`, and nothing was
    sized. Every other test in this module stays green through that revert,
    because every other fixture writes phase-doc files.
    """
    c = _component(tree)
    _write(c, own.ROADMAP,
           "# Alpha\n\n## Phase 1 — gated on the fleet\nNo doc yet; the gate is named.\n")
    assert own.phase_docs_of(c) == {}, "the fixture's point is that there are none"

    message = _drive(monkeypatch, tree, lambda: (c / own.ROADMAP).write_text(
        (c / own.ROADMAP).read_text() + "\nRead it cold and it looks fine.\n"))
    assert "UNSIZED" in message
    assert "floor of 1" in message and "ALL GATED" in message, (
        f"the message must say WHY the floor is one on a component with no "
        f"phase docs, or it reads as an off-by-one; got {message!r}")


def test_ONE_estimate_clears_the_floor_on_an_all_gated_component(
        tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """THE RESIDUAL, PINNED RATHER THAN ASSUMED — and it is deliberately GREEN.

    The floor closes the TOTAL collapse (a run that sized nothing) and not the
    PARTIAL one: a six-phase all-gated component still passes on one estimate,
    because the true phase count is not derivable — a gated phase has no doc for
    the roadmap to link, and roadmap headings have no binding grammar.

    NOT AN `xfail`, which would read as *known bug, someone will fix it*. This is
    a checked limit with a stated reason. If a later change makes this test FAIL,
    the floor got tighter and the right response is to REWRITE this test to the
    new bound — not to restore the old behaviour to keep it green.
    """
    c = _component(tree)
    _write(c, own.ROADMAP, "# Alpha\n\n## Phase 1 — gated\n## Phase 2 — also gated\n")
    url = _harness(monkeypatch, tree, lambda: (c / own.ROADMAP).write_text(
        "# Alpha\n\n## Phase 1 — gated (~8 hrs)\n## Phase 2 — also gated\n"))()
    assert url == "https://github.com/o/r/pull/9"


def test_a_CORRECTION_PASS_that_writes_no_new_hours_is_not_UNSIZED(
        tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CLASS: THE DELIVERABLE IS KEYED ON STATE, and every prohibition on a DELTA.

    This asymmetry is the single most likely thing for a later pass to "fix" for
    consistency, and doing so breaks exactly the pass most likely to be the last
    one anybody reads. A `--pr` redispatch meets a roadmap that already carries
    last pass's estimates; its job is to close a reviewer's runway, and it may
    legitimately change no hour figure at all. Under a delta-shaped guard
    (`after - before >= phases`) that correct run fails.

    The fixture is a run that writes something OTHER than hours, so the delta is
    zero while the state is complete — the two readings differ, which is the only
    way this assertion can discriminate.
    """
    c = _planned(tree)                       # already sized, as pass 1 left it
    url = _harness(monkeypatch, tree, lambda: (c / own.ROADMAP).write_text(
        _SIZED_ROADMAP + "\n> Reviewer runway closed: the Phase 2 gate is named.\n"))()
    assert url == "https://github.com/o/r/pull/9"


def test_DROPPING_a_phase_raises_the_RE_PLANNING_message_NOT_the_unsized_one(
        tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ORDERING, and this fixture FOUND the defect rather than confirming its absence.

    Dropping a phase's roadmap entry takes its estimate with it, so the
    commonest re-planning offence ALSO trips the sizing floor — which counts
    phase DOCS, and the doc is still on disk. Written with the sizing guard
    first, this run failed with *"UNSIZED: 1 hour estimate against 2 phase
    docs"*: a true failure naming the wrong cause, whose suggested remedy — add
    an estimate — leaves the dropped phase dropped.

    That is the write half's shipped defect exactly, one workflow over: its
    phase-identity message was unreachable behind a generic grant check, so the
    operator got "a file you may write ceased to exist" for the one failure the
    workflow was built to name. Asserting the ABSENCE of the other message is
    what makes this an ordering test rather than a message test.
    """
    c = _planned(tree)
    message = _drive(monkeypatch, tree, lambda: (c / own.ROADMAP).write_text(
        "# Alpha\n\n## Phase 1 (~8 hrs)\nSee [x](phase1_the_first_thing.md).\n"))
    assert "DROPPED phase2_the_gated_one.md" in message
    assert "you do not rewrite it" in message
    assert "still on disk with nothing pointing at it" in message
    assert "UNSIZED" not in message, (
        "the sizing guard fired first and told the operator to add a number to a "
        "phase this run had just deleted from the plan")


def test_a_TICKED_checkbox_fails_the_run(
        tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """*Built is not proven*, and sizing a phase is the clearest case of not building it."""
    c = _planned(tree)
    message = _drive(monkeypatch, tree, lambda: (c / own.ROADMAP).write_text(
        _SIZED_ROADMAP.replace("- [ ] a criterion", "- [x] a criterion")))
    assert "TICKED 'a criterion'" in message and "Built is not proven" in message


def test_an_ERASED_checkbox_fails_the_run_TOO(
        tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The worse half, and `Counter` subtraction one way round reports nothing.

    A plan that reports work nobody built is bad; a plan that has forgotten work
    somebody DID is worse, because nothing downstream ever asks for it again.
    """
    c = _planned(tree, roadmap=_SIZED_ROADMAP.replace("- [ ] a criterion",
                                                      "- [x] a criterion"))
    message = _drive(monkeypatch, tree, lambda: (c / own.ROADMAP).write_text(
        _SIZED_ROADMAP))
    assert "ERASED 'a criterion'" in message


def test_a_PRE_EXISTING_violation_does_not_fail_a_clean_run(
        tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CLASS: a prohibition guard judges what THIS RUN DID, never what the tree IS.

    Seeded with a pre-existing instance of the two prohibitions that could
    plausibly be keyed on state — a ticked box the previous pass left, and a
    phase reference that was already there — against a run whose only act is to
    add the hours it was dispatched to add.

    A GUARD ADDED LATER AND KEYED ON STATE FAILS HERE, which is the point. Add
    its pre-existing instance to the seed above when you add the guard. The
    DELIVERABLE guard is deliberately not in that set and is keyed on state on
    purpose — see the correction-pass fixture above.
    """
    unsized = _SIZED_ROADMAP.replace(" (~8 hrs)", "").replace(" (~12 hrs)", "")
    c = _planned(tree, roadmap=unsized.replace("- [ ] a criterion",
                                               "- [x] a box ticked before this run"))
    url = _harness(monkeypatch, tree, lambda: (c / own.ROADMAP).write_text(
        _SIZED_ROADMAP.replace("- [ ] a criterion",
                               "- [x] a box ticked before this run")))()
    assert url == "https://github.com/o/r/pull/9"


def test_a_DELETED_roadmap_raises_the_GRANT_message_not_the_UNSIZED_one(
        tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ORDERING, and it is a real reachability question rather than a preference.

    A deleted roadmap satisfies BOTH guards: `grants_that_vanished` sees a
    permitted file gone, and `roadmap_hours` reads an empty Counter and reports
    zero estimates. With the sizing guard first, the operator is told "you sized
    nothing" about a file that no longer exists — and the obvious remedy that
    message suggests is to write the plan back, which is not the same plan and is
    work this workflow may not do.
    """
    c = _planned(tree)
    message = _drive(monkeypatch, tree, lambda: (c / own.ROADMAP).unlink())
    assert "cease to exist" in message, (
        f"the deletion raised a different guard's message: {message}")
    assert "UNSIZED" not in message


def test_DELETING_a_PHASE_DOC_raises_its_OWN_message_not_the_unsized_one(
        tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """THE SCOPE QUESTION, ASKED OF THE GUARDS RATHER THAN OF THEIR VALUES.

    Every guard above was mutated and every mutation was caught — and this case
    still got through all of them, because the question a negative control asks
    is *does this guard discriminate*, never *what is this guard not looking
    at*. A phase doc deleted with the roadmap's reference to it LEFT STANDING
    moves neither of the two guards that run before sizing:

      * `grants_that_vanished` watches the two files this run may WRITE, and a
        phase doc is not one of them;
      * `roadmap_phase_links` reads a roadmap that did not change, so the link
        Counter is identical either side.

    It reaches `boundary_crossings` — correctly, but LAST. So a run that also
    left a phase unsized was told "you sized nothing" about a run that had
    erased a document, which is the identical misdirection this file already
    reorders the sizing guard to avoid, arriving by a second route.

    THE FIXTURE UNDER-SIZES ON PURPOSE. Deleting the doc drops the phase count
    from 2 to 1 while the roadmap still carries two estimates, so a naive
    reading passes sizing outright; the roadmap here is stripped to one estimate
    so BOTH guards have something to say and only one of them may.
    """
    c = _planned(tree, roadmap=_SIZED_ROADMAP.replace(" (~12 hrs)", ""))
    message = _drive(monkeypatch, tree,
                     lambda: (c / "phase2_the_gated_one.md").unlink())
    assert "phase2_the_gated_one.md" in message and "cease to exist" in message, (
        f"a deleted phase doc raised a different guard's message: {message}")
    assert "UNSIZED" not in message, (
        "the sizing guard ran first and blamed the estimates for a run that "
        "erased a document — the remedy it suggests leaves the doc deleted")


def test_an_EDIT_OUTSIDE_THE_GRANT_is_left_to_the_BOUNDARY_check(
        tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """THE DISCRIMINATOR for the guard above, and it is a scope assertion.

    Without this, the deletion guard could have been written as a content
    compare — and it would pass the test above while stealing the message from
    `boundary_crossings`, which is the guard that says the right thing about an
    EDIT. Only DISAPPEARANCE needs its own message, because only disappearance
    is what the generic message gets wrong.

    THE FIXTURE MOVED 2026-08-19 and the reason matters. It used to EDIT a phase
    doc, which was a crossing when this run could write only `roadmap.md`. It no
    longer is: the grant reaches every top-level doc so a determined correction
    can be applied where the defect is. `research/synthesis.md` is the file that
    still separates the two guards — outside the grant by the SUBDIRECTORY, and
    the evidence this run judges a plan against, so a run editing it has made
    the evidence agree with the verdict it is about to write.
    """
    c = _planned(tree)
    evidence = c / "research" / "synthesis.md"
    evidence.write_text("# evidence\n")
    message = _drive(monkeypatch, tree,
                     lambda: evidence.write_text("# rewritten evidence\n"))
    assert "outside its authorization" in message, (
        f"an edited research file should reach the boundary check: {message}")
    assert "cease to exist" not in message


def test_TWO_estimates_beside_ONE_phase_satisfy_the_floor(
        tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """THE RESIDUAL, PINNED RATHER THAN ASSUMED — this run PASSES, and should not.

    The deliverable guard compares a TOTAL count of estimates against a TOTAL
    count of phase docs. Nothing in code knows which phase an estimate sits
    beside, so two figures written against Phase 1 cover a Phase 2 with none and
    the run reports SIZED over a plan that is half unsized.

    IT IS ASSERTED HERE, GREEN, AS A KNOWN LIMIT rather than left for the next
    reader to discover. A per-phase association was attempted and is blocked by
    the corpus in two independent ways, both of which would FAIL CORRECT RUNS:
    chunking by phase heading needs a heading grammar the Documentation Standard
    does not fix — and its own worked example puts the estimate IN the heading,
    above the link — while requiring an estimate on each phase-REFERENCE line
    fails outright, because `roadmap_phase_links` matches CROSS-COMPONENT
    references by design and those are not this component's phases to size.

    So the floor stays a floor, the prompt names the limit to the model in the
    imperative, and this test is what stops the limit being silently widened or
    silently forgotten. **If a later change makes this test FAIL, that is the
    guard getting stronger and this test should be rewritten, not restored.**
    """
    c = _planned(tree, roadmap=_SIZED_ROADMAP.replace(" (~12 hrs)", ""))
    url = _harness(monkeypatch, tree, lambda: (c / own.ROADMAP).write_text(
        (c / own.ROADMAP).read_text().replace(
            "## Phase 1 — the first thing (~8 hrs)",
            "## Phase 1 — the first thing (~8 hrs)\n\nRevised up from Est. 5 hours.")))()
    assert url == "https://github.com/o/r/pull/9", (
        "the fixture no longer reaches the deliverable guard at all, so it has "
        "stopped documenting anything — re-check what it writes")
    assert sum(own.roadmap_hours(c).values()) == 2 and len(own.phase_docs_of(c)) == 2
    assert not re.search(r"hrs|hours",
                         (c / own.ROADMAP).read_text().split("## Phase 2")[1]), (
        "PHASE 2 CARRIES NO ESTIMATE — that is the whole point of this fixture, "
        "and a passing run over it is the residual being demonstrated")


def test_the_PREFLIGHT_asks_the_PR_BRANCH_for_the_plan_not_just_this_checkout() -> None:
    """A `--pr` pass reads the PR's tree, so the precondition must ask that tree.

    MEASURED ON PR #130. `plan-feature` had written a roadmap and six phase docs
    minutes earlier; this preflight asked the local checkout, found none, and
    refused the run — declaring missing the exact plan it had been pointed at.

    THIRD INSTANCE OF ONE CLASS THIS WEEK, which is why the guard is on the
    lookup rather than on the message. PR #115 fixed four runners that opened a
    worktree on HEAD instead of the PR's branch; plan-verify's dry run still
    counts from the repo because no worktree exists yet, which is correct and
    documented. This one was neither correct nor documented: it BLOCKED the run.

    Absence on both sides is still a refusal — the precondition is real and a
    plan that exists nowhere cannot be verified. What changed is which trees
    count as "nowhere".
    """
    src = (Path(__file__).resolve().parents[2] / "scripts" / "run_plan_verify.py").read_text()
    guard = src[src.index("plan_exists = "):src.index("return 1", src.index("plan_exists = "))]
    assert "a.pr_number" in guard, (
        "the roadmap precondition no longer consults the PR number, so a --pr "
        "pass is judged against a checkout that need not contain the plan")
    assert "pr_branch" in guard and "cat-file" in guard, (
        "the precondition does not ask the PR's BRANCH for the file. Asking only "
        "the local tree refuses runs whose plan exists exactly where the run "
        "would have read it")
    assert "not here and not on PR" in guard, (
        "the refusal message no longer says BOTH trees were checked. A caller "
        "told only 'has no roadmap.md' will go looking in the wrong one")

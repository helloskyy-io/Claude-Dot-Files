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


# A REFERENCE THAT REACHES ALL THE PRINTED FIGURES AT ONCE — the grammar a
# blanket zero claim has to use, and the boundary the dry-run caveat's zeros
# must be narrowed inside of. Used by the mixed-tree test far below, and named
# here rather than inline because what counts as "sweeping" is the judgement
# that assertion turns on: a wording this misses is a wording that assertion
# stops holding, so the list is the thing to extend when the caveat is reworded.
_SWEEPS_THE_COUNTS = re.compile(
    r"\b(?:every|all|each)\b|\b(?:counts?|figures?|numbers?)\s+below\b")


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
    r"""The grant reaches every TOP-LEVEL doc, and stops at the subdirectory.

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
        "| ID | Candidate | `component` | Source | `decision` | `size` | `status` | Note |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| C-d1uhacwn | a candidate |  | PR #1 |  | feature | `open` | n |\n")

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
    # ANCHOR ON THE ASSIGNMENT, NOT ON THE PHRASE. Slicing from the first
    # occurrence of "plan_exists = " caught a mention inside the comment that
    # explains the lookup, so the guard read a paragraph of prose and failed.
    start = src.index("plan_exists = (component")
    guard = src[start:src.index("return 1", start)]
    assert "a.pr_number" in guard, (
        "the roadmap precondition no longer consults the PR number, so a --pr "
        "pass is judged against a checkout that need not contain the plan")
    assert "pr_branch" in guard and "origin/{branch}" in guard, (
        "the precondition does not ask the PR's BRANCH for the file. Asking only "
        "the local tree refuses runs whose plan exists exactly where the run "
        "would have read it")
    # THE QUERY MUST NOT SWALLOW ITS OWN FAILURE. An unreadable ref and an absent
    # file are different facts, and collapsing them into `plan_exists = False`
    # delivers "I cannot see it" as "it is not there" — the same wrong-confidence
    # shape this whole guard exists to stop, one layer down.
    assert "except" not in guard, (
        "the branch lookup catches its own failure, so a ref this run could not "
        "read is reported to the caller as a plan that does not exist")
    assert "not here and not on PR" in guard, (
        "the refusal message no longer says BOTH trees were checked. A caller "
        "told only 'has no roadmap.md' will go looking in the wrong one")


# --- the `--pr` precondition, DRIVEN rather than read ----------------------
#
# THE TEST ABOVE READS THIS GUARD AS TEXT AND NEVER RUNS IT, which is issue
# #103's class exactly: a structural guard that can stay green over an
# accumulating defect because nothing exercises its predicate. Every substring
# it asserts survives a boolean inversion, a wrong relative path, and a lookup
# pointed at the wrong ref. It is KEPT — it holds the `except`-absence property,
# which no behavioural test can express — and these four run the thing.
#
# THE FAKE ANSWERS THE QUERY; IT DOES NOT REPLACE THE GUARD. `pr_branch` and
# `git_output` are the two boundary calls, so stubbing exactly those leaves the
# whole precondition — the local check, the `--pr` condition, the path it builds,
# the ref it asks, the refusal, the handler — running for real. Recording their
# ARGUMENTS is half the point: "handed the wrong relative path" and "pointed at
# the wrong ref" are two of the three defects the source-grep cannot see.
#
# WHAT THESE FOUR NEVER INSPECT, stated so the next reader does not credit them
# with it. (1) The PROCESS layer: both boundary calls are stubbed, so nothing
# here proves `gh pr view` and `git ls-tree` are spelled correctly for the real
# binaries, nor that a real `ls-tree` prints what `bool(...strip())` assumes —
# that contract lives in `plan_activities` and its own tests. (2) The NON-`--pr`
# refusal, which `test_the_runner_REFUSES_a_component_with_NO_roadmap` holds.
# (3) The order of `open_run_bag` against `worktree_add` — these only assert
# that NEITHER is reached on a refusal, which is issue #49's property;
# `test_the_call_precedes_the_first_side_effect_in_every_entrypoint` holds the
# order between them. (4) The NON-`--pr` refusal's side-effect freedom: the
# sibling test asserts its exit code and message and does not watch for an
# orphaned bag, so that half of #49 is still held by placement alone.

def _pr_lookup(monkeypatch: pytest.MonkeyPatch, branch: str, tree_answer: str,
               calls: list, raise_on: str | None = None):
    """Answer the two boundary calls the `--pr` precondition makes, and log them.

    `raise_on` names the call that fails — `"pr_branch"` for an unresolvable
    `--pr`, `"fetch"` for a ref this run cannot read, `"no_gh"` for a host with
    no `gh` on PATH.

    TWO EXCEPTION TYPES, NOT ONE, and the second is why `"no_gh"` exists.
    `RuntimeError` is the ordinary failure: `pr_branch` raises it through `gh()`,
    `git_output` on any non-zero exit. But both bottom out in `subprocess`, which
    raises `FileNotFoundError` when the BINARY is missing — `run_bounded` does not
    catch it, so it escapes by a second route entirely. The runner's `except`
    names both types for exactly that reason. Until `"no_gh"` every fake here
    raised `RuntimeError` alone, so narrowing that `except` back to
    `except RuntimeError:` — which silently reopens the traceback leak this
    precondition was written to close — left the whole file green.
    """
    def pr_branch(pr_number: str, repo_root: Path) -> str:
        calls.append(("pr_branch", pr_number))
        if raise_on == "no_gh":
            # THE REAL SHAPE, not a `RuntimeError` wearing a different message.
            # `subprocess.run(["gh", ...])` on a host without `gh` raises this,
            # and the point of the case is the TYPE reaching the handler.
            raise FileNotFoundError(2, "No such file or directory", "gh")
        if raise_on == "pr_branch":
            # NO TRAILING PERIOD, DELIBERATELY. `gh()` raises
            # `f"... failed in {repo_root}: {r.stderr.strip()}"`, and git/gh
            # stderr does not reliably end in punctuation — a fake that supplies
            # one hides the run-on the handler is responsible for separating.
            raise RuntimeError(f"gh pr view {pr_number} --json headRefName -q "
                               f".headRefName failed in {repo_root}: no pull "
                               f"requests found")
        return branch

    def git_output(worktree: Path, argv: list[str], cannot_hint: str) -> str:
        calls.append(tuple(argv))
        if raise_on == "fetch" and argv[1] == "fetch":
            raise RuntimeError(
                f"could not read the worktree state in {worktree} via "
                f"`{' '.join(argv)}`: couldn't find remote ref. {cannot_hint}")
        return tree_answer if argv[1] == "ls-tree" else ""

    monkeypatch.setattr(act, "pr_branch", pr_branch)
    monkeypatch.setattr(act, "git_output", git_output)


def _record_side_effects(monkeypatch: pytest.MonkeyPatch, runner, calls: list,
                         url: str = "https://github.com/o/r/pull/132"):
    """Log the run's first three side effects instead of performing them.

    ISSUE #49'S CLASS, ASSERTED RATHER THAN ASSUMED. A precondition that refuses
    AFTER the run bag is opened or the worktree is cut leaves both orphaned, and
    "it is refused before anything is created" is the reason this check lives in
    preflight at all. The refusing tests below assert these names are ABSENT from
    `calls`; the accepting one asserts they were reached.

    It also makes every case here hermetic. Without it a run that wrongly gets
    past the guard reaches real `git` and, one step further, a real model
    dispatch — which a unit test must never be one defect away from.
    """
    monkeypatch.setattr(runner.journal, "open_run_bag",
                        lambda **k: calls.append("open_run_bag"))
    monkeypatch.setattr(act, "worktree_add",
                        lambda repo_root, *a, **k: (calls.append("worktree_add"),
                                                    repo_root)[1])
    monkeypatch.setattr(wf, "run_plan_verify",
                        lambda **k: (calls.append("run_plan_verify"), url)[1])


def test_a_PR_pass_is_NOT_refused_when_the_plan_is_only_on_the_PRs_BRANCH(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """The case PR #130 measured: no roadmap here, a roadmap on the PR. Run it.

    THE ASSERTION IS EXIT 0, not the absence of one message. A refusal and a
    later failure both exit 1, so an exit code alone cannot tell "the
    precondition let it through" from "it let it through and something after it
    died" — and the local tree genuinely has no roadmap, so plenty could.
    Everything past the precondition is stubbed for that reason: reaching the
    banner is the proof.

    AND THE ARGUMENTS ARE ASSERTED, because that is where this differs from the
    source-grep. `origin/<branch>` and the roadmap's path RELATIVE TO THE REPO
    are the two values the guard computes, and a lookup that asks the wrong ref
    or the wrong path still contains every substring that test greps for.
    """
    repo, runner, calls = _repo(tmp_path), _runner(), []
    _pr_lookup(monkeypatch, "plan-feature-1787204416",
               f"docs/development/alpha/{own.ROADMAP}\n", calls)
    _record_side_effects(monkeypatch, runner, calls)

    rc = runner.main(["docs/development/alpha", "--repo", str(repo), "--pr", "132"])
    err = capsys.readouterr().err
    assert rc == 0, (
        f"a plan that exists on the PR's branch was refused anyway — this is the "
        f"defect measured on PR #130, one layer down; stderr was {err!r}")
    assert not (repo / "docs" / "development" / "alpha" / own.ROADMAP).is_file(), (
        "the fixture stopped discriminating: the roadmap is present LOCALLY, so "
        "this run would pass with the PR-branch lookup deleted entirely")
    ls_tree = ("git", "ls-tree", "-r", "--name-only",
               "origin/plan-feature-1787204416", "--",
               f"docs/development/alpha/{own.ROADMAP}")
    assert "run_plan_verify" in calls, (
        f"the run never reached the dispatch, so the `not in calls` assertions "
        f"in the refusing cases below are vacuous — the recorder never fires; "
        f"the calls were {calls!r}")
    assert ls_tree in calls, (
        f"the lookup asked for something other than the roadmap's repo-relative "
        f"path on origin/<the PR's branch>; it asked {calls!r}")
    # AND THE FETCH CAME FIRST. The ref has to be local before anything can read
    # it, and this precondition runs BEFORE the worktree helper that would
    # otherwise have done the fetching — so an `ls-tree` that overtakes the fetch
    # reads a ref that need not exist yet, and on a repo where an earlier run
    # left one behind it reads a STALE one, which is the worse half.
    fetch = ("git", "fetch", "-q", "origin", "plan-feature-1787204416")
    assert fetch in calls and calls.index(fetch) < calls.index(ls_tree), (
        f"the PR's ref was queried without being fetched first, or after; the "
        f"calls in order were {calls!r}")


def test_a_PR_pass_IS_refused_when_the_plan_is_on_NEITHER_tree(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """Absence on both sides is still a refusal — the precondition is real.

    A boolean inversion of the guard passes the source-grep and fails here: it
    would let a run through with no plan on either tree, which is the state the
    precondition exists to stop.
    """
    repo, runner, calls = _repo(tmp_path), _runner(), []
    _pr_lookup(monkeypatch, "some-branch", "", calls)
    _record_side_effects(monkeypatch, runner, calls)

    rc = runner.main(["docs/development/alpha", "--repo", str(repo), "--pr", "132"])
    err = capsys.readouterr().err
    assert rc == 1, "a component with no plan on either tree was accepted"
    assert "open_run_bag" not in calls and "worktree_add" not in calls, (
        f"the refusal came AFTER the run had created something, so a dead run "
        f"leaves it orphaned — issue #49's class; the calls were {calls!r}")
    assert "not here and not on PR #132's branch" in err, (
        f"the refusal does not say BOTH trees were checked, so a caller reading "
        f"it goes looking in the wrong one; got {err!r}")
    assert "plan_feature.sh" in err, (
        f"the refusal must still name the workflow that writes the plan; got {err!r}")


def test_a_PR_pass_IS_refused_when_the_plan_is_HERE_but_NOT_on_the_PRs_BRANCH(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """The local tree does not VOTE on a `--pr` pass — it only shapes the message.

    THE ONE CASE THE OTHER FOUR CANNOT REACH, and it went unwritten because the
    precondition began life as an `or` over two trees. A roadmap in the operator's
    checkout satisfied the check and the branch was never consulted; the run then
    cut its worktree from `origin/<the PR's branch>` — which is the ONLY tree it
    ever reads — and dispatched a model against a component with no plan in it.
    That is issue #49's shape reached the long way round: a wasted dispatch and a
    stranded worktree, produced by the guard that exists to prevent both.

    MEASURED AS A SURVIVING MUTATION, not reasoned about. With the short-circuit
    in place, changing the condition to consult the branch unconditionally left
    all 65 tests green, which is the definition of an unpinned behaviour: the two
    readings of this precondition were indistinguishable to the suite.

    AND THE WORDING IS ASSERTED, not just the exit code. "Write the plan" and
    "push the plan you already wrote" are different remedies, and an operator
    handed the both-trees sentence for this state goes looking for a file that is
    sitting in front of them.
    """
    repo, runner, calls = _repo(tmp_path), _runner(), []
    (repo / "docs" / "development" / "alpha" / own.ROADMAP).write_text(
        "# Alpha\n\n## Phase 1 — a thing (~4 hrs)\n")
    _pr_lookup(monkeypatch, "some-branch", "", calls)
    _record_side_effects(monkeypatch, runner, calls)

    rc = runner.main(["docs/development/alpha", "--repo", str(repo), "--pr", "132"])
    err = capsys.readouterr().err
    assert rc == 1, (
        f"a plan present ONLY in this checkout was accepted for a --pr pass, so "
        f"the run proceeds against a branch that does not carry it; stderr was "
        f"{err!r}")
    assert ("git", "ls-tree", "-r", "--name-only", "origin/some-branch", "--",
            f"docs/development/alpha/{own.ROADMAP}") in calls, (
        f"the PR's branch was never asked — the local file answered on its "
        f"behalf, which is the short-circuit this test exists to pin; the calls "
        f"were {calls!r}")
    assert "it IS in this checkout, but not on PR #132's branch" in err, (
        f"the refusal does not distinguish 'you have not written the plan' from "
        f"'you have not pushed it', and those have different remedies; got {err!r}")
    assert "not here and not on PR" not in err, (
        f"a plan that IS here was reported as absent from both trees, which is "
        f"false and sends the operator to write a file they already have; got "
        f"{err!r}")
    # AND THE REMEDY IS THE HALF THE DOCSTRING ABOVE CLAIMED AND NOTHING HELD.
    # For one commit the diagnostic branched and the ACTIONABLE sentence did not:
    # "it IS in this checkout" was printed over a fixed "Run plan_feature.sh
    # against this component first — writing the plan is its job", telling an
    # operator whose only problem is an unpushed commit to re-run the workflow
    # that had already succeeded. The two assertions above could not see it —
    # both read the diagnostic clause, which was correct the whole time. A remedy
    # is the only part of a refusal anyone ACTS on, so this asserts the wrong one
    # is absent as well as the right one being present.
    assert "plan_feature.sh" not in err, (
        f"the refusal diagnosed 'the plan is here but unpushed' and then told "
        f"the operator to run the workflow that WRITES the plan — the remedy "
        f"contradicts the diagnosis one sentence earlier, and the remedy is the "
        f"part they will act on; got {err!r}")
    assert "push" in err, (
        f"the refusal names no way out of the state it just diagnosed: the plan "
        f"is written and this run cannot see it, so pushing it to the branch is "
        f"the only remedy and the message has to say so; got {err!r}")
    assert "open_run_bag" not in calls and "worktree_add" not in calls, (
        f"the refusal came AFTER the run had created something — issue #49's "
        f"class; the calls were {calls!r}")


@pytest.mark.parametrize("raise_on, unreadable", [
    ("pr_branch", "the --pr number resolves to no branch"),
    ("fetch", "the PR's ref cannot be fetched"),
    # THE THIRD CASE IS A DIFFERENT EXCEPTION TYPE, not a third message. The two
    # above both raise `RuntimeError`, so between them they pin the handler's
    # BEHAVIOUR while pinning only half of what it CATCHES — and dropping
    # `FileNotFoundError` from the `except` tuple left the whole file green,
    # reopening the traceback leak by the one route `run_bounded` does not cover.
    ("no_gh", "there is no gh binary on this host"),
])
def test_a_PR_LOOKUP_that_FAILS_stops_the_run_and_says_so_rather_than_guessing(
        raise_on: str, unreadable: str, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """"I cannot see it" must not be delivered as "it is not there" — nor as a traceback.

    TWO PROPERTIES, AND THE SECOND IS THE ONE WITH TEETH.

    First: the failure reaches the operator in this file's `✗ <one line>` shape
    with exit 1, like its two sibling handlers. Both boundary calls raise, and
    they are made BETWEEN main's two try statements, so before this they escaped
    as a Python traceback — measured by execution, not inferred.

    Second, and this is what the source-grep structurally cannot hold: the
    refusal wording must be ABSENT. `plan_exists = False` in a handler is the
    swallow this whole guard exists to prevent, and a handler placed outside the
    grepped span can reintroduce it with every asserted substring still in place.
    An unknown reported as a confident "there is no plan" fails here and only
    here.

    The hint is asserted on BOTH raise sites because it reached only one: it was
    `git_output`'s `cannot_hint` argument, so an operator who mistyped `--pr` —
    the likeliest caller of all — never saw it.
    """
    repo, runner, calls = _repo(tmp_path), _runner(), []
    _pr_lookup(monkeypatch, "some-branch", "", calls, raise_on=raise_on)
    _record_side_effects(monkeypatch, runner, calls)

    rc = runner.main(["docs/development/alpha", "--repo", str(repo), "--pr", "132"])
    out, err = capsys.readouterr()
    assert rc == 1, f"{unreadable} and the run continued anyway"
    assert err.startswith("\n✗ "), (
        f"a failed lookup does not answer in this file's one-line refusal shape; "
        f"got {err!r}")
    assert "\u2014 this run cannot tell whether PR #132 carries a plan" in err, (
        f"{unreadable}, and the operator is not told what that leaves unknown; "
        f"got {err!r}")
    assert "not here and not on PR" not in err, (
        f"an UNREADABLE lookup was reported as an ABSENT plan — 'I cannot see "
        f"it' delivered as 'it is not there', which is the exact defect this "
        f"precondition was rewritten to remove; got {err!r}")
    assert "https://github.com" not in out, (
        "the run proceeded past a lookup it could not complete")
    assert "open_run_bag" not in calls and "worktree_add" not in calls, (
        f"a lookup this run could not complete still created something — the "
        f"handler continued instead of stopping, which is the swallow in a "
        f"different costume; the calls were {calls!r}")


# --- the `--pr` DRY RUN, which counts a different tree than the run reads -----
#
# `--dry-run` HAD NO TEST IN THIS FILE AT ALL until these two, which is how the
# defect below reached `main` under five behavioural tests and a source-grep: all
# six watch the precondition, and none of them watches what the runner PRINTS
# once the precondition has let it through.
#
# THE DEFECT THESE PIN, MEASURED BY EXECUTION rather than read out of the source.
# Driving `--pr N --dry-run` with the roadmap on the branch and absent here exits
# 0 and prints `Phase docs : 0`, `Sized now : 0 estimate(s)` and `floor is 0` for
# a plan that is fully written — because every count is taken off the LOCAL
# component path while the run cuts its worktree from `origin/<the PR's branch>`
# and reads nothing else. On `origin/main` that state was unreachable: the
# precondition unconditionally required a local `roadmap.md`, so the local tree
# was guaranteed non-empty. Making the branch authoritative removed that
# guarantee and relocated PR #130's wrong conclusion out of a loud refusal and
# into a confident-looking preview.
#
# WHAT THEY DO NOT HOLD. The counts themselves are still LOCAL — these assert the
# output SAYS SO, not that the numbers describe the dispatched tree. Reading them
# from the branch (`git ls-tree` / `git show`) is the larger fix and belongs to
# all four `--pr`-accepting runners at once; it is issue #134's, not this file's.
# So a run whose preview is honest about being the wrong tree passes here, and
# that is the whole claim.

def test_a_DRY_RUN_on_a_PR_pass_SAYS_the_counts_came_from_a_TREE_WITHOUT_the_plan(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """The zeros are real, so the preview must say which tree produced them.

    THE ASSERTION IS ON STDOUT, not on the counts. `Phase docs : 0` is the
    CORRECT reading of this checkout — the roadmap genuinely is not here — and
    the defect is that nothing said so, leaving an operator to read a local
    reading as a preview of the dispatch. Both halves are asserted together: the
    zeros prove the fixture is in the divergent state, and the note proves the
    output no longer presents them as the dispatch's own.

    AND THE BRANCH IS REUSED, NOT RE-FETCHED. `pr_branch` is asserted to have
    been called exactly ONCE across the whole run. A note that re-derived the
    branch with a second `gh pr view` would print identical text while
    reinstating the duplicate round-trip this file removed one commit earlier —
    and nothing would guarantee the two answers agreed.
    """
    repo, runner, calls = _repo(tmp_path), _runner(), []
    _pr_lookup(monkeypatch, "plan-feature-1787204416",
               f"docs/development/alpha/{own.ROADMAP}\n", calls)
    _record_side_effects(monkeypatch, runner, calls)

    rc = runner.main(["docs/development/alpha", "--repo", str(repo),
                      "--pr", "132", "--dry-run"])
    out, err = capsys.readouterr()
    assert rc == 0, (
        f"the dry run did not complete, so nothing below is exercising its "
        f"output; stderr was {err!r}")
    assert not (repo / "docs" / "development" / "alpha" / own.ROADMAP).is_file(), (
        "the fixture stopped discriminating: with the roadmap present LOCALLY "
        "the two trees agree and there is nothing for this test to catch")
    assert "Sized now  : 0 estimate(s)" in out and "floor is 0" in out, (
        f"the counts are no longer the local zeros this test is about — either "
        f"the fixture changed or the dry run now reads the branch, in which case "
        f"issue #134's larger fix has landed and this test should assert THAT "
        f"instead of the caveat; got {out!r}")
    assert "Counted in : this checkout" in out, (
        f"the preview does not name the tree its counts came from, so a local "
        f"reading is presented as a preview of the dispatched run; got {out!r}")
    assert "does NOT carry docs/development/alpha/roadmap.md" in out, (
        f"the preview does not say this checkout lacks the plan, so the zeros "
        f"above read as a plan that was never written; got {out!r}")
    assert "origin/plan-feature-1787204416" in out, (
        f"the preview does not name the tree the run will actually read, which "
        f"is the one place the operator can go to check; got {out!r}")
    # AND ABOVE THE ZEROS, NOT UNDER THEM — asserted in the shape this file uses
    # for the fetch/ls-tree ordering, because `in out` cannot see a placement.
    # The runner's own comment calls this placement load-bearing (an operator
    # scanning top-down must meet the reason before the numbers), and the caveat
    # says "the counts BELOW", so a caveat printed underneath them contradicts
    # its own wording while passing every substring assertion above.
    assert out.index("Counted in") < out.index("NOT HERE") < out.index("Phase docs"), (
        f"the provenance and the caveat are not above the counts they qualify — "
        f"the operator meets the zeros before the reason, and the caveat's own "
        f"\"counts below\" is false where it now sits; got {out!r}")
    assert calls.count(("pr_branch", "132")) == 1, (
        f"the PR's branch was resolved more than once — the preview re-derived "
        f"what the precondition had already put in `branch`, which is two "
        f"round-trips for one fact with nothing forcing them to agree; the calls "
        f"were {calls!r}")
    assert not {"open_run_bag", "worktree_add", "run_plan_verify"} & set(calls), (
        f"a --dry-run created something or dispatched — `nothing invoked, "
        f"nothing posted` is the banner's promise; the calls were {calls!r}")


def test_a_DRY_RUN_still_names_its_tree_and_DROPS_the_caveat_when_the_plan_IS_here(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """The caveat is CONDITIONAL, and an unconditional one would be a lie.

    THE OTHER HALF OF THE PAIR, and the reason it exists: a note printed on every
    `--pr` dry run passes its sibling above while telling an operator whose
    checkout DOES carry the plan that it does not. That is the same wrong-
    confidence failure pointed the other way, and the sibling cannot see it —
    it only ever asserts the note is PRESENT.

    Provenance is unconditional and the caveat is not: naming the tree is true of
    every dry run, while "the plan is elsewhere" is true only when it is.
    """
    repo, runner, calls = _repo(tmp_path), _runner(), []
    (repo / "docs" / "development" / "alpha" / own.ROADMAP).write_text(
        "# Alpha\n\n## Phase 1 — a thing (~4 hrs)\n")
    _pr_lookup(monkeypatch, "plan-feature-1787204416",
               f"docs/development/alpha/{own.ROADMAP}\n", calls)
    _record_side_effects(monkeypatch, runner, calls)

    rc = runner.main(["docs/development/alpha", "--repo", str(repo),
                      "--pr", "132", "--dry-run"])
    out, err = capsys.readouterr()
    assert rc == 0, f"the dry run did not complete; stderr was {err!r}"
    # ONE ESTIMATE, NOT FOUR — and the `hours` in `roadmap_hours` is what misled
    # the first draft of this line. It returns a Counter keyed on the matched
    # estimate TEXT, so its values are OCCURRENCE COUNTS and the runner's
    # `sum(...values())` is the NUMBER of estimates, which is what its own
    # `estimate(s)` label says. `~4 hrs` is that one estimate's size and is never
    # summed. Written as 4, corrected by running it.
    assert "Sized now  : 1 estimate(s)" in out, (
        f"the fixture is not in the agreeing state this test needs — the local "
        f"roadmap was not read, so an unconditional caveat would pass here for "
        f"the wrong reason; got {out!r}")
    assert "Counted in : this checkout" in out, (
        f"the tree is named only in the divergent case, so a dry run whose two "
        f"trees agree still does not say where its numbers came from; got {out!r}")
    assert "NOT HERE" not in out and "does NOT carry" not in out, (
        f"the caveat fired for a checkout that DOES carry the plan, telling the "
        f"operator their own file is missing; got {out!r}")


def test_a_DRY_RUN_with_NO_pr_still_NAMES_the_tree_it_counted(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """Provenance is unconditional, and until this test nothing held that.

    THE TWO TESTS ABOVE BOTH PASS `--pr`, so neither can tell "names the tree
    always" from "names the tree only on a `--pr` pass". Gating the `Counted in`
    line on `a.pr_number` was run as a mutation and SURVIVED the whole unit
    suite — 0 red — which is what this test exists to close. Their docstrings
    already claim unconditionality ("true of every dry run"); this is the
    assertion that makes the claim checkable rather than merely stated.

    AND IT IS THE HONESTY FLOOR, not a nicety. The caveat keys on the roadmap
    being ABSENT here, so a checkout holding a STALE roadmap at the same path
    gets no caveat and still counts a tree the run will not read. On that pass
    this line is the only thing that tells the operator where the numbers came
    from — and on a non-`--pr` run it is the only provenance printed at all.

    `pr_branch` IS ASSERTED NEVER TO HAVE RUN. Without `--pr` there is no PR to
    resolve, and a provenance line that reached for a branch anyway would put a
    network round-trip behind a purely local preview.
    """
    repo, runner, calls = _repo(tmp_path), _runner(), []
    (repo / "docs" / "development" / "alpha" / own.ROADMAP).write_text(
        "# Alpha\n\n## Phase 1 — a thing (~4 hrs)\n")
    _pr_lookup(monkeypatch, "plan-feature-1787204416",
               f"docs/development/alpha/{own.ROADMAP}\n", calls)
    _record_side_effects(monkeypatch, runner, calls)

    rc = runner.main(["docs/development/alpha", "--repo", str(repo), "--dry-run"])
    out, err = capsys.readouterr()
    assert rc == 0, f"the dry run did not complete; stderr was {err!r}"
    assert "Sized now  : 1 estimate(s)" in out, (
        f"the local roadmap was not read, so this run is not previewing the "
        f"component this test set up; got {out!r}")
    assert "Counted in : this checkout" in out, (
        f"a dry run WITHOUT --pr does not name the tree its counts came from, "
        f"so provenance is conditional on a flag that has nothing to do with "
        f"where the counting happened; got {out!r}")
    assert "NOT HERE" not in out, (
        f"the branch caveat fired on a run that named no PR and resolved no "
        f"branch; got {out!r}")
    assert not [c for c in calls if c and c[0] == "pr_branch"], (
        f"a run given no --pr resolved a PR branch anyway; the calls were "
        f"{calls!r}")
    assert not {"open_run_bag", "worktree_add", "run_plan_verify"} & set(calls), (
        f"a --dry-run created something or dispatched — `nothing invoked, "
        f"nothing posted` is the banner's promise; the calls were {calls!r}")


def test_a_DRY_RUN_caveat_may_NOT_claim_a_count_is_ZERO_when_that_COUNT_IS_NOT(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """The MIXED tree, which the three tests above structurally cannot reach.

    THEIR FIXTURE COMPONENT HOLDS A ROADMAP AND NOTHING ELSE, so "the roadmap is
    absent here" and "the plan is absent here" are the same state in all three
    and no assertion can tell them apart. They are different states, and the
    difference is reachable through this runner's own target workflow: a
    component laid out by hand with phase docs, whose `roadmap.md` `plan-feature`
    writes later, verified from a checkout predating that PR. Only `phase_docs_of`
    ignores the roadmap, so in that state it prints a NON-ZERO count while
    `roadmap_phase_links`, `roadmap_hours` and `sizing_floor` are all correctly 0.

    MEASURED AT 4337371 BY EXECUTION, first against the real binary and then
    reproduced here: the caveat called this checkout "a tree WITHOUT the plan"
    and said "the counts below ... will be 0", one line above `Phase docs : 4 of
    its own`. An operator who meets a warning and then immediately meets a number
    the warning said would not exist reads the warning as inapplicable — so the
    LOCAL phase-doc count gets taken for the branch's, which is the exact
    wrong-confidence failure the caveat was added to prevent. A caveat that
    over-claims is worse than none: it is what makes the local number look
    vouched for.

    THE ASSERTIONS ARE ON THE PROPERTY, NOT ON A REPLACEMENT WORDING, which
    matters because a gate satisfiable by pasting a required string into the
    artifact is worse than no gate. The number is parsed out of the runner's own
    output and the caveat's claims are checked AGAINST it.

    THIS SENTENCE WAS FALSE WHEN IT WAS FIRST WRITTEN, and saying so is the
    point of leaving it here. As shipped at 142421a it claimed a rewording into
    a blanket zero claim "fails here however it is phrased"; review pass 5
    falsified that by mutation — it restored the over-claim in substance and
    this file ran 71 passed, 0 red. The scan neutralises the interpolated path
    now, and matches the word `zero` as well as the digit, so the claim below is
    the narrowed one the code actually delivers. A guard's docstring is read as
    a warrant by whoever edits the thing it guards, so an over-claiming one is
    the same defect as an over-claiming diagnostic, one layer up.

    WHAT IT HOLDS. Between the last SWEEPING reference before a zero-claim and
    the claim itself, the word `roadmap` must appear — so a wording that reaches
    all the printed figures at once and then calls them 0 must narrow that reach
    to the roadmap first, which is the grammar the shipped caveat uses. It holds
    for the digit and for the word `zero`, with the interpolated file path
    blanked so the filename cannot stand in for the narrowing; and a caveat that
    stops naming its zeros altogether fails rather than emptying the loop and
    passing in silence.

    A PROXIMITY CHECK WAS TRIED FIRST AND WAS NOT ENOUGH, which is worth keeping
    because the difference is the whole subject. Asking whether `roadmap` occurs
    within N characters of the zero tests CO-OCCURRENCE, and co-occurrence comes
    apart from scope on the wording a careless edit actually writes: "with the
    roadmap absent, every count below comes out 0" names the roadmap, sweeps the
    phase-doc count in anyway, and clears a proximity check comfortably. Three
    such wordings were constructed and run — two by review, one here — and all
    three passed the proximity form and red the bounded one.

    WHAT IT DOES NOT HOLD, stated so its silence is not over-read.

    It does not read English, and it is not a proof. It holds a NECESSARY
    condition on the wording — narrow before you claim — and a determined
    rewording that satisfies the letter while still misleading (naming the
    roadmap inside the swept span for an unrelated reason) would pass. Review is
    the backstop for that; this assertion is the floor, and calling it more than
    a floor is the same over-claim it exists to catch.

    `_SWEEPS_THE_COUNTS` is a list, and a sweeping wording it does not match is a
    wording this stops holding. That is the maintenance cost and it is the reason
    the pattern is a named module constant rather than an inline literal.

    It does not check the counts are RIGHT — they are still this checkout's,
    which is issue #134's fix for all four `--pr`-accepting runners at once. It
    holds only that nothing printed beneath the caveat contradicts the caveat.

    It reds CLOSED on two shapes rather than passing them: a caveat that scopes
    its zeros by naming the roadmap FILE PATH and never the bare word loses its
    only narrowing token to the blanking, and a caveat that spells its zeros a
    third way (`nil`, `none`) trips the empty-claims guard. Both are deliberate.
    Failing closed on a wording nobody has written beats passing open on the one
    that shipped, and each failure message names which of the two it is.
    """
    repo, runner, calls = _repo(tmp_path), _runner(), []
    component = repo / "docs" / "development" / "alpha"
    # NAMES THAT MATCH `act._LOOKS_LIKE_A_PHASE` (`^phase.*\.md$`), which is read
    # from the module rather than guessed — a fixture whose files do not match it
    # prints `0 of its own` and this test then passes for the WRONG reason,
    # reporting a defect as fixed when nothing has been exercised. The count
    # assertion below is what turns that silent pass into a loud failure.
    (component / "phase1_first.md").write_text("# Phase 1\n")
    (component / "phase2_second.md").write_text("# Phase 2\n")
    _pr_lookup(monkeypatch, "plan-feature-1787204416",
               f"docs/development/alpha/{own.ROADMAP}\n", calls)
    _record_side_effects(monkeypatch, runner, calls)

    rc = runner.main(["docs/development/alpha", "--repo", str(repo),
                      "--pr", "132", "--dry-run"])
    out, err = capsys.readouterr()
    assert rc == 0, (
        f"the dry run did not complete, so nothing below is exercising its "
        f"output; stderr was {err!r}")
    assert not (component / own.ROADMAP).is_file(), (
        "the fixture stopped discriminating: with the roadmap present LOCALLY "
        "the caveat does not fire and there is nothing here to contradict")

    caveat = next((ln for ln in out.splitlines() if "NOT HERE" in ln), None)
    assert caveat is not None, (
        f"the caveat did not fire on a --pr dry run whose roadmap is absent "
        f"here, so this test is asserting nothing about its claims; got {out!r}")
    counted = re.search(r"Phase docs : (\d+) of its own", out)
    assert counted, (
        f"the phase-doc count is no longer printed in a shape this test can "
        f"read, so the caveat's claim cannot be checked against it; got {out!r}")
    phase_docs_here = int(counted.group(1))
    # THE FIXTURE'S OWN DISCRIMINATOR. Two phase-doc-shaped files were written
    # above; a `0` here means they did not match `_LOOKS_LIKE_A_PHASE` and the
    # component is in the all-absent state the three tests above already cover —
    # which is NOT this test's state and must not be mistaken for a pass.
    assert phase_docs_here == 2, (
        f"the fixture is not in the MIXED state: {phase_docs_here} phase docs "
        f"were counted where 2 were written, so either the files stopped "
        f"matching act._LOOKS_LIKE_A_PHASE or the count stopped being local. "
        f"Nothing below discriminates in that state; got {out!r}")

    # THE PROPERTY, CHECKED AGAINST THE NUMBER RATHER THAN AGAINST A WORDING:
    # every zero the caveat asserts must be SCOPED to the figures that actually
    # read the roadmap. A blanket zero claim is false the moment `phase_docs_of`
    # returns anything, and that is the state this fixture is in.
    #
    # THE INTERPOLATED PATH IS BLANKED BEFORE SCANNING, and that one line is the
    # whole reason this assertion discriminates. The caveat unconditionally opens
    # by naming the file it is about, so `{rel}/roadmap.md` puts the word
    # `roadmap` at a fixed low index of EVERY caveat this runner can print —
    # inside the lookback of every zero in a line of realistic length. Scanning
    # the raw string, the window was satisfied by the FILENAME and never by the
    # claim's scope, so the loop could not fail: review pass 5 restored the
    # blanket over-claim in substance and all 71 tests in this file stayed green.
    # Blanking the path leaves only prose the WORDING chose to write.
    #
    # `zero` IS SCANNED ALONGSIDE `0` because `\b0\b` alone is a second, quieter
    # vacuity of the same kind: a blanket claim spelled "are all zero" matches
    # nothing at all, the loop body never runs, and a loop that never runs is an
    # assertion that cannot fail.
    #
    # AND THE SPAN IS BOUNDED BY THE SWEEP, NOT BY A CHARACTER COUNT. A fixed
    # lookback asks "does the word `roadmap` appear NEAR this zero", which is
    # co-occurrence and not scope — and the two come apart on the wording a
    # careless edit actually produces: `with the roadmap absent, every count
    # below comes out 0` names the roadmap, sweeps the phase-doc count in
    # anyway, and passes a proximity check comfortably. So the span starts at
    # the LAST sweeping reference before the zero (`every`/`all`/`each`, or
    # `the counts/figures below`) and the restriction must sit INSIDE it: what
    # the quantifier reaches has to be narrowed to the roadmap before the zero
    # is claimed, which is the grammar the shipped caveat actually uses
    # ("every figure below THAT IS READ FROM THE ROADMAP ... is 0"). With no
    # sweep at all the span is the whole caveat, so an unquantified blanket
    # claim is caught by the same line.
    scanned = caveat.replace(f"{component.relative_to(repo)}/{own.ROADMAP}",
                             "<the file this caveat is about>")
    claims = list(re.finditer(r"\b0\b|\bzeros?\b", scanned))
    assert claims, (
        f"the caveat makes no zero-claim this assertion can read, so the loop "
        f"below is vacuous and nothing about its scope is being held. Either "
        f"the caveat stopped naming the zeros it attributes to the absent "
        f"roadmap, or it spells them a third way this scan does not match; got "
        f"{caveat!r}")
    low = scanned.lower()
    for zero in claims:
        sweep = max((m.end() for m in _SWEEPS_THE_COUNTS.finditer(low[:zero.start()])),
                    default=0)
        assert "roadmap" in low[sweep:zero.end()], (
            f"the caveat claims a figure is 0 without narrowing the claim to "
            f"the roadmap-derived ones first, while {phase_docs_here} phase "
            f"docs are counted one line below it — the operator meets a warning "
            f"and then a number it said would not exist, and reads the warning "
            f"as not applying. What is unrestricted is {low[sweep:zero.end()]!r}; "
            f"got {caveat!r}")
    # AND IT MUST NOT DESCRIBE THIS CHECKOUT BY WHAT IS STILL IN IT. What is
    # absent here is the roadmap; the plan's phase docs are on disk, computed
    # below rather than assumed, so "a tree WITHOUT the plan" is false of it.
    on_disk = sorted(p.name for p in component.iterdir() if p.is_file())
    assert "without the plan" not in caveat.lower(), (
        f"the caveat calls this checkout a tree WITHOUT the plan while {on_disk} "
        f"are sitting in it — what is absent is the roadmap, and naming the "
        f"wrong thing absent is what the count below then contradicts; got "
        f"{caveat!r}")
    # THE THREE THAT GENUINELY ARE 0 STILL ARE, so the narrowed claim is checked
    # for being TRUE and not merely for being cautious — a caveat that claims
    # nothing would pass every assertion above.
    assert "· 0 phase-doc reference(s)" in out and "Sized now  : 0 estimate(s)" in out \
        and "floor is 0" in out, (
        f"the roadmap-derived figures are no longer the zeros the caveat "
        f"attributes to the absent roadmap — either the fixture changed or the "
        f"dry run now reads the branch, in which case issue #134's larger fix "
        f"has landed and this test should assert THAT instead; got {out!r}")
    assert out.index("Counted in") < out.index("NOT HERE") < out.index("Phase docs"), (
        f"the caveat is not above the counts it qualifies, so its own "
        f"\"below\" is false where it sits; got {out!r}")
    assert not {"open_run_bag", "worktree_add", "run_plan_verify"} & set(calls), (
        f"a --dry-run created something or dispatched — `nothing invoked, "
        f"nothing posted` is the banner's promise; the calls were {calls!r}")

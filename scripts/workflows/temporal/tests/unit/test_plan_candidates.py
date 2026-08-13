"""plan-candidates creates structure and never plans work, and both halves fire.

THE BOUNDARY THIS MODULE EXISTS FOR. `plan-feature` owns roadmap and phase
CONTENT — the epics, the milestones, the hours per phase. `plan-candidates` owns
the component's CHARTER: what the domain is, what it is not, where it came from.
A run that plans phases has built the wrong child, and the two failure modes are
structurally different from anything either sibling can commit:

  * it EDITS A ROADMAP THAT ALREADY EXISTS, which no path rule can see —
    `worktree_state` reports a created roadmap and an edited one identically,
    since both are absent from the before-snapshot and present in the after one;
  * it PLANS PHASES INSIDE THE ROADMAP IT WAS ALLOWED TO CREATE, which no
    snapshot can see at all, because that file is the workflow's own output.

So both are observed by reading DISK on either side of the run, and this module
proves each observation fires and — the half that matters more — that it does not
fire on the correct behaviour it sits one line away from.

THE REGISTRY HALF IS ELSEWHERE. `test_authorization_is_observed.py` proves every
`You MAY NOT` row names a mechanism and that the mechanism exists;
`test_disappearance_is_observed.py` proves every snapshot names what watches it
for absence. This module proves they fire. The split is the same one the triage
suite already draws, for the same reason: a registry entry that resolves is not
evidence that the guard it names does anything.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from modules.assistant.plan import plan_activities as act
from modules.assistant.plan.plan_candidates import plan_candidates_activities as own
from modules.assistant.plan.plan_candidates import plan_candidates_workflow as scaffold

PR_URL = "https://github.com/o/r/pull/43"

_HEADER = (
    "| ID | Candidate | Source | `decision` | `status` | Note |\n"
    "|---|---|---|---|---|---|\n"
)

def _charter_template() -> str:
    """The charter template AS THE PROMPT SHIPS IT, read out of the prompt file.

    DERIVED, NEVER RESTATED, and this used to be a hand-copied constant that had
    already drifted — the copy was missing the `## Dependencies` section and the
    `Serves:` line. That matters more here than anywhere else in this module: the
    one test certifying *a compliant run cannot fail its own guard* was checking
    an approximation of what the model is actually handed, so a later prompt edit
    that tripped `_PHASE_PLANNED` or `_HOURS_ESTIMATED` would have left the suite
    green while every correct run raised. Same discipline as
    `observer_registry.workflows_declaring`, which derives the prompt filename
    for exactly this reason.
    """
    text = (scaffold.PROMPTS / "plan_candidates.md").read_text()
    blocks = re.findall(r"^```markdown\n(.*?)^```", text, re.S | re.M)
    assert len(blocks) == 1, (
        f"expected exactly one ```markdown block in plan_candidates.md (the "
        f"charter template); found {len(blocks)}. If the prompt legitimately "
        f"grew a second, name which one this test wants — a silent [0] here is "
        f"how this check starts reading the wrong block.")
    return blocks[0]


_CHARTER = _charter_template()


def _table(rows: list[tuple[str, ...]], note: str = "n") -> str:
    """A candidates file holding exactly `rows` as (id, decision[, status]) tuples."""
    body = "".join(
        f"| {row[0]} | a candidate | PR #1 | {row[1]} | {row[2] if len(row) > 2 else '`open`'} | {note} |\n"
        for row in rows)
    return "# Action candidates\n\n" + _HEADER + body


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """A repo-shaped tmp dir that is BOTH repo_root and worktree.

    The workflow computes `candidates_path.relative_to(repo_root)` and then
    re-roots it under the worktree; passing the same path for both keeps that
    arithmetic honest without building two trees.
    """
    (tmp_path / "docs" / "development").mkdir(parents=True)
    (tmp_path / "r" / "raw").mkdir(parents=True)
    return tmp_path


def _component(tree: Path, slug: str, *, roadmap: str | None = None,
               research: bool = False, papers: bool = False,
               defining_doc: bool = False) -> Path:
    """`research` makes the FOLDER; `papers` puts something in it.

    The two are separate parameters because conflating them is the defect this
    fixture used to encode: `research=True` created an empty directory and the
    inventory called it evidence. Twelve components in this repo hold a
    `research/` folder and three hold a paper.
    """
    d = tree / "docs" / "development" / slug
    d.mkdir(parents=True, exist_ok=True)
    if roadmap is not None:
        (d / "roadmap.md").write_text(roadmap)
    if defining_doc:
        (d / f"{slug}.md").write_text(f"# {slug}\n\n**Status:** COMPLETE\n")
    if research or papers:
        (d / "research" / "raw").mkdir(parents=True, exist_ok=True)
    if papers:
        (d / "research" / "raw" / "topic.md").write_text("# a paper\n")
    return d


@pytest.fixture
def stub_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """Silence the helpers that shell out; leave every guard under test live.

    `existing_work` runs `gh`, which would put a network dependency in a unit
    test. `worktree_state` runs `git` and the fixture tree is not a repository,
    so it is stubbed to the CLEAN answer — an unchanged tree on both sides — and
    the tests that care about the path boundary override it via `_crossing`. A
    fixture returning a violation would make every other test here fail for the
    wrong reason.

    `component_roadmaps`, `component_dirs` and `phase_planning_in` are NOT
    stubbed: they read the tmp tree, which is exactly what they do in production,
    and stubbing them would leave this module asserting about its own fakes.
    """
    monkeypatch.setattr(scaffold.act, "existing_work", lambda *a, **k: "<work>")
    monkeypatch.setattr(act, "worktree_state", lambda *a, **k: {})


def _crossing(monkeypatch: pytest.MonkeyPatch, path: str) -> None:
    """Make the NEXT snapshot pair look like this run edited `path`.

    Drives the guard through `worktree_state`'s real return SHAPE — a path mapped
    to a content digest — rather than stubbing the comparison, so the
    forbidden/permitted declarations under test are the ones that actually run.
    """
    snapshots = iter([{}, {path: "digest"}])
    monkeypatch.setattr(act, "worktree_state", lambda *a, **k: next(snapshots))


def _vanished(monkeypatch: pytest.MonkeyPatch, path: str) -> None:
    """Make the NEXT snapshot pair look like this run DELETED `path`."""
    snapshots = iter([{}, {path: act.ABSENT}])
    monkeypatch.setattr(act, "worktree_state", lambda *a, **k: next(snapshots))


def _fake_run(monkeypatch: pytest.MonkeyPatch, mutate=None,
              output: str = f"done\n{PR_URL}\n"):
    """Stand in for the model: optionally mutate the tree, then answer.

    Mutating the real tmp tree is how a live run offends — it writes files in the
    worktree — so the fake offends the same way rather than by patching a guard's
    inputs. A guard driven by hand-built dicts proves the comparator works and
    says nothing about whether the workflow calls it.
    """
    def run(prompt: str, **kw: object) -> str:
        if mutate is not None:
            mutate()
        return output
    monkeypatch.setattr(scaffold.act, "run_claude", run)


def _run(tree: Path) -> str:
    return scaffold.run_plan_candidates(
        repo_root=tree, worktree=tree,
        candidates_path=tree / "c.md", research_dir=tree / "r")


# --- `component_roadmaps`: the reader every roadmap guard is built on ---------

def test_it_finds_a_charter_per_component_keyed_by_relative_path(tree: Path) -> None:
    _component(tree, "alpha", roadmap="# A\n")
    _component(tree, "beta", roadmap="# B\n")
    assert set(own.component_roadmaps(tree)) == {
        "docs/development/alpha/roadmap.md", "docs/development/beta/roadmap.md"}


def test_a_component_with_NO_charter_is_simply_absent(tree: Path) -> None:
    """The shell state, and it must not read as an error or as a charter.

    Sixteen of this repo's seventeen components are in exactly this state, so a
    reader that raised or invented an entry would be wrong about almost the whole
    tree.
    """
    _component(tree, "fleet-reliability", research=True)
    assert own.component_roadmaps(tree) == {}


def test_the_digest_moves_with_the_CONTENT_and_not_with_the_path(tree: Path) -> None:
    """DISCRIMINATOR. Without this the map could return a constant per path and
    every "was it edited?" assertion below would still pass — while the guard
    reported clean on every edit there is."""
    _component(tree, "alpha", roadmap="# A\n")
    first = own.component_roadmaps(tree)
    (tree / "docs" / "development" / "alpha" / "roadmap.md").write_text("# A changed\n")
    assert own.component_roadmaps(tree) != first


def test_a_missing_component_root_reads_as_EMPTY_rather_than_raising(tmp_path: Path) -> None:
    """A repo with no component layer is the repo this workflow is most useful in."""
    assert own.component_roadmaps(tmp_path) == {}


def test_reviews_is_not_a_component(tree: Path) -> None:
    """`docs/development/reviews/` holds review artifacts, not a domain of work.

    `plan_activities.existing_work` already excludes it, and a second definition
    of "what counts as a component" that disagreed would be the drift
    `normalise_cell` exists to record.
    """
    _component(tree, "reviews", roadmap="# not a component\n")
    assert own.component_roadmaps(tree) == {}
    assert own.component_dirs(tree) == set()


# --- create versus edit: the boundary a path rule cannot see ------------------

def test_an_EDITED_charter_is_reported(tree: Path) -> None:
    before = {"docs/development/alpha/roadmap.md": "aaa"}
    after = {"docs/development/alpha/roadmap.md": "bbb"}
    assert own.roadmaps_edited(before, after) == ["docs/development/alpha/roadmap.md"]


def test_a_CREATED_charter_is_not_an_edit(tree: Path) -> None:
    """DISCRIMINATOR, and creating is the whole job.

    Without this pair `roadmaps_edited` could return every key it saw and every
    assertion above would still pass — while failing every correct run.
    """
    after = {"docs/development/alpha/roadmap.md": "aaa"}
    assert own.roadmaps_edited({}, after) == []
    assert own.roadmaps_created({}, after) == ["docs/development/alpha/roadmap.md"]


def test_a_DELETED_charter_is_invisible_to_the_edit_comparison(tree: Path) -> None:
    """WHY THE DELETION CHECK RUNS FIRST IN THE WORKFLOW, asserted rather than claimed.

    `roadmaps_edited` judges only keys present on both sides, so a razed charter
    is in neither intersection and this comparison reports nothing whatever about
    it. That is not a defect here — it is the reason `act.ids_deleted` is called
    ahead of it, and the reason this assertion is written down.
    """
    before = {"docs/development/alpha/roadmap.md": "aaa"}
    assert own.roadmaps_edited(before, {}) == []
    assert act.ids_deleted(before, {}) == ["docs/development/alpha/roadmap.md"]


# --- phase planning inside the workflow's OWN output --------------------------

@pytest.mark.parametrize("line", [
    "See `phase1_measure.md` for detail",
    "### Phase 2 — the fan-out",
    "- phase-3: migrate the fleet",
    "Estimated at 40 hours",
    "Roughly 20h of work",
    "| Phase 1 | 12 hrs |",
], ids=["phase-file", "phase-heading", "phase-hyphen", "hours-word",
        "hours-short", "table-row"])
def test_a_planned_phase_or_an_estimate_in_a_CREATED_charter_is_reported(
        tree: Path, line: str) -> None:
    _component(tree, "alpha", roadmap=f"# Alpha\n\n{line}\n")
    found = own.phase_planning_in(tree, ["docs/development/alpha/roadmap.md"])
    assert list(found) == ["docs/development/alpha/roadmap.md"], (
        f"{line!r} planned a phase or estimated hours and was not reported")


@pytest.mark.parametrize("line", [
    "**Status: CHARTERED — phases are not planned yet. `plan-feature` writes them.**",
    "Phases and hour estimates are `plan-feature`'s, not this document's.",
    "This component depends on the memory-management-framework charter.",
    "Derived from `C-001`, `C-014`.",
], ids=["status-line", "boundary-sentence", "dependency", "provenance"])
def test_the_charter_may_SAY_that_phases_are_somebody_else_s(
        tree: Path, line: str) -> None:
    """DISCRIMINATOR, and it is the reason the pattern matches a SHAPE.

    The prompt REQUIRES the charter to state what it is not, so a check keyed on
    the word `phase` would forbid the sentence that makes the boundary legible —
    and the obvious response to a guard that fails every correct run is to delete
    it. A planned phase carries a NUMBER and an estimate carries a figure with a
    unit; the disclaimer carries neither.

    `C-001` is in this list deliberately: it is a digit adjacent to a letter, and
    a sloppier hours pattern would read it as one.
    """
    _component(tree, "alpha", roadmap=f"# Alpha\n\n{line}\n")
    assert own.phase_planning_in(tree, ["docs/development/alpha/roadmap.md"]) == {}


def test_the_full_charter_template_the_prompt_hands_the_model_passes(tree: Path) -> None:
    """THE END-TO-END DISCRIMINATOR: a run that follows its instructions exactly
    must not fail its own post-condition. A guard that rejects the template in
    the prompt beside it is worse than no guard — it fails only correct runs."""
    _component(tree, "alpha", roadmap=_CHARTER)
    assert own.phase_planning_in(tree, ["docs/development/alpha/roadmap.md"]) == {}


@pytest.mark.parametrize("line", [
    "Derived from `C-011` — ship three cheap guards (~9 h).",
    'Derived from `C-013` — close the "evaluate Paperclip after Phase 4" gate.',
], ids=["hours-in-a-quoted-title", "phase-in-a-quoted-title"])
def test_a_candidate_TITLE_carrying_a_phase_or_an_hour_still_trips_the_guard(
        tree: Path, line: str) -> None:
    """THE GUARD CANNOT TELL A QUOTE FROM A PLAN, and this pins that it cannot.

    Both strings are real: `C-011`'s title ends `(~9 h)` and `C-013`'s contains
    `Phase 4`, and both rows are ruled `ship` today, so both are in the live
    working set. The charter template REQUIRES a *Where it came from* line saying
    what those candidates asked for — so a run that quotes either title fails
    AFTER the model has spent its budget and opened the PR, and the exception
    takes the whole `plan-project` dispatch down with it.

    THE FIX IS IN THE PROMPT, NOT HERE, and this test is why it can stay there:
    loosening the pattern to admit a quoted phase number would also admit a
    planned one, which is the boundary the entire child is defined by. So the
    guard stays strict, the prompt tells the run to paraphrase and cite the
    candidate by id, and this asserts the trap is still where the prompt says.
    """
    _component(tree, "alpha", roadmap=f"# Alpha\n\n{line}\n")
    assert own.phase_planning_in(tree, ["docs/development/alpha/roadmap.md"]), (
        f"{line!r} no longer trips the guard. If that was deliberate, the "
        f"paraphrase instruction in prompts/plan_candidates.md is now telling "
        f"the model to avoid something harmless — delete one or the other, but "
        f"do not leave the prompt warning about a trap that is gone.")


@pytest.mark.parametrize("line", [
    "Derived from `C-011` — three cheap guards, sized as a small piece of work.",
    "Derived from `C-013` — close the gate deferring the Paperclip evaluation.",
    "Depends on the memory-management-framework's typed exit record.",
], ids=["paraphrased-hours", "paraphrased-phase", "paraphrased-dependency"])
def test_the_PARAPHRASE_the_prompt_asks_for_passes(tree: Path, line: str) -> None:
    """DISCRIMINATOR on the pair above: the instruction must be followable.

    A trap with no way around it is a guard that fails every correct run. These
    are the exact rewrites the prompt gives as examples, so if one of them ever
    trips the pattern the instruction has become impossible to obey.
    """
    _component(tree, "alpha", roadmap=f"# Alpha\n\n{line}\n")
    assert own.phase_planning_in(tree, ["docs/development/alpha/roadmap.md"]) == {}


def test_an_EXISTING_roadmap_full_of_phases_is_not_this_check_s_business(tree: Path) -> None:
    """Scoped to CREATED roadmaps, and the scope is load-bearing.

    `memory-management-framework/roadmap.md` legitimately lists six numbered
    phases. A check over every roadmap in the tree would fail every run in this
    repo over a file nobody in the dispatch touched — and its edit is caught by
    `roadmaps_edited` instead, which is the correct guard for it.
    """
    _component(tree, "mmf", roadmap="# MMF\n\n### Phase 4 — 40 hours\n")
    assert own.phase_planning_in(tree, []) == {}


# --- the empty shell ----------------------------------------------------------

def test_a_component_directory_created_with_NO_charter_is_reported(tree: Path) -> None:
    """The state `docs/development/fleet-reliability/` is actually in on `main`."""
    assert own.shells_without_a_charter(set(), {"alpha"}, {}) == ["alpha"]


def test_a_component_directory_created_WITH_a_charter_is_not(tree: Path) -> None:
    """DISCRIMINATOR: creating a chartered component is the entire job."""
    assert own.shells_without_a_charter(
        set(), {"alpha"}, {"docs/development/alpha/roadmap.md": "d"}) == []


def test_a_PRE_EXISTING_charterless_component_is_not_charged_to_this_run(tree: Path) -> None:
    """DISCRIMINATOR, and without it this guard fails every run in this repo.

    Sixteen of seventeen components here have no `roadmap.md`. Judged against the
    tree rather than against what the run ADDED, the check would fire on all of
    them, on every dispatch, over work nobody in it did — which is the shape of
    guard that gets deleted rather than fixed.
    """
    assert own.shells_without_a_charter({"fleet-reliability"},
                                        {"fleet-reliability"}, {}) == []


# --- the working set, counted in code -----------------------------------------

def test_only_the_SHIP_rows_are_the_working_set() -> None:
    text = own.shipped_working_set(
        {"C-001": "ship", "C-002": "reject", "C-003": "", "C-004": "requires review",
         "C-005": "ship"})
    assert "**2 ruled `ship`**" in text
    assert "C-001, C-005" in text
    for invisible in ("C-002", "C-003", "C-004"):
        assert invisible not in text, (
            f"{invisible} reached the working set. A rejected row is settled, an "
            f"untriaged one is not yours to read as an intention, and a "
            f"`requires review` row is the operator's open question.")


def test_an_EMPTY_ship_set_is_a_state_and_says_so() -> None:
    """A model told `0 ship` with no further instruction reasonably concludes
    there is work to find, and the nearest work is the rows it may not touch."""
    text = own.shipped_working_set({"C-001": "reject", "C-002": ""})
    assert "**none ruled `ship`**" in text
    assert "NOTHING TO SCAFFOLD" in text


def test_the_inventory_names_a_SHELL_as_the_cheap_repair(tree: Path) -> None:
    """The one existing directory this workflow may write into, and it must be
    told which — adding a charter a component never had is CREATING one."""
    _component(tree, "fleet-reliability", papers=True)
    _component(tree, "mmf", roadmap="# M\n")
    text = own.component_inventory(tree)
    assert "RESEARCH BUT NOTHING DEFINING IT" in text
    assert "fleet-reliability" in text and "HAS A CHARTER" in text
    assert "Chartered: 1 · already defined by their own `<slug>.md`: 0 · " \
           "holding research with nothing above it: 1." in text


def test_an_EMPTY_research_folder_is_not_evidence_and_not_a_shell(tree: Path) -> None:
    """DISCRIMINATOR, and it is the one that decides how much this run creates.

    Nine of this repo's twelve `research/` directories hold nothing but a
    `.gitkeep`. Keyed on the folder EXISTING, the inventory told the model those
    components "have evidence and nothing saying what the component IS" — while
    the prompt calls repairing a shell the cheapest correct outcome available.
    A compliant run would have chartered up to eleven pre-existing components and
    the parent would have commissioned a research cycle into each, with every
    guard reporting clean because each creation is legitimate by construction.
    """
    _component(tree, "empty-pool", research=True)
    text = own.component_inventory(tree)
    assert "an empty directory" in text
    assert "RESEARCH BUT NOTHING DEFINING IT" not in text, (
        "an empty `research/` folder read as evidence")
    assert "holding research with nothing above it: 0." in text


def test_a_component_DEFINED_BY_ITS_OWN_SLUG_DOC_is_marked_do_not_charter(
        tree: Path) -> None:
    """DISCRIMINATOR against inventing a second home for a defined component.

    `sprint.md`'s convention is that a component fitting in one phase IS
    `<slug>/<slug>.md`, and eleven of this repo's sixteen components are in
    exactly that state — several marked COMPLETE. The inventory was blind to that
    file, so it reported them to the model as components with nothing saying what
    they are, which is the strongest available invitation to charter one.
    """
    _component(tree, "planning-and-agents", defining_doc=True, research=True)
    text = own.component_inventory(tree)
    assert "ALREADY DEFINED" in text and "Do not charter it" in text
    assert "already defined by their own `<slug>.md`: 1" in text


# --- the guards, fired through the real entrypoint ----------------------------
#
# PREDICTED BEFORE RUNNING: of the seven mutations below, all seven must raise
# and the two clean runs must return the PR URL. The mutations are derived from
# the workflow's own claims about itself — one per `You MAY NOT` row that carries
# a mechanism — rather than from whatever is easiest to break.

def test_a_clean_run_that_charters_a_NEW_component_returns_the_url(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    (tree / "c.md").write_text(_table([("C-001", "`ship`")]))
    _fake_run(monkeypatch, lambda: _component(tree, "alpha", roadmap=_CHARTER))
    assert _run(tree) == PR_URL


def test_a_clean_run_that_charters_NOTHING_returns_the_url(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """The designed common case: every ruled row extends something that exists.

    Without this, every assertion in this section would still pass over a
    workflow that REQUIRED a component to be created — which is the failure the
    prompt's "most rows will be one of the first two" section exists to prevent.
    """
    (tree / "c.md").write_text(_table([("C-001", "`ship`")]))
    _component(tree, "alpha", roadmap=_CHARTER)
    _fake_run(monkeypatch, None)
    assert _run(tree) == PR_URL


def test_editing_an_EXISTING_charter_fails_the_run(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    (tree / "c.md").write_text(_table([("C-001", "`ship`")]))
    _component(tree, "alpha", roadmap=_CHARTER)
    _fake_run(monkeypatch,
              lambda: _component(tree, "alpha", roadmap=_CHARTER + "\nrewritten\n"))
    with pytest.raises(RuntimeError, match="roadmap.* that already existed"):
        _run(tree)


def test_deleting_a_charter_fails_the_run(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    (tree / "c.md").write_text(_table([("C-001", "`ship`")]))
    _component(tree, "alpha", roadmap=_CHARTER)

    def raze() -> None:
        (tree / "docs" / "development" / "alpha" / "roadmap.md").unlink()

    _fake_run(monkeypatch, raze)
    with pytest.raises(RuntimeError, match="deleted 1 component charter"):
        _run(tree)


def test_planning_phases_in_a_created_charter_fails_the_run(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """THE BOUNDARY AGAINST `plan-feature`, fired end to end."""
    (tree / "c.md").write_text(_table([("C-001", "`ship`")]))
    _fake_run(monkeypatch, lambda: _component(
        tree, "alpha", roadmap=_CHARTER + "\n### Phase 1 — 20h\n"))
    with pytest.raises(RuntimeError, match="planned phases or estimated hours"):
        _run(tree)


def test_creating_a_component_directory_with_no_charter_fails_the_run(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    (tree / "c.md").write_text(_table([("C-001", "`ship`")]))
    _fake_run(monkeypatch, lambda: _component(tree, "alpha", research=True))
    with pytest.raises(RuntimeError, match="no `roadmap.md` in them"):
        _run(tree)


def test_setting_a_DECISION_fails_the_run(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    (tree / "c.md").write_text(_table([("C-001", "")]))
    _fake_run(monkeypatch,
              lambda: (tree / "c.md").write_text(_table([("C-001", "`ship`")])))
    with pytest.raises(RuntimeError, match="`decision` column"):
        _run(tree)


def test_setting_a_STATUS_fails_the_run(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    (tree / "c.md").write_text(_table([("C-001", "`ship`", "`open`")]))
    _fake_run(monkeypatch, lambda: (tree / "c.md").write_text(
        _table([("C-001", "`ship`", "`closed`")])))
    with pytest.raises(RuntimeError, match="`status` column"):
        _run(tree)


def test_placing_a_BLANK_proposal_row_is_permitted(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """DISCRIMINATOR against the decision guard, and a shared instruction depends on it.

    `decision_log_and_reflection.md` tells every producing run to place a proposal
    it surfaced into `candidates.md` with `decision` blank. A guard that diffed
    the id sets outright would make that instruction unfollowable: the run would
    place a proposal exactly as told and then fail its own post-condition.
    """
    (tree / "c.md").write_text(_table([("C-001", "`ship`")]))
    _fake_run(monkeypatch, lambda: (tree / "c.md").write_text(
        _table([("C-001", "`ship`"), ("C-002", "")])))
    assert _run(tree) == PR_URL


def test_a_run_that_produced_no_PR_URL_fails_rather_than_returning_nothing(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """The children after this research and plan INTO what it created."""
    (tree / "c.md").write_text(_table([("C-001", "`ship`")]))
    _fake_run(monkeypatch, None, output="all done, nothing to report\n")
    with pytest.raises(RuntimeError, match="produced no PR URL"):
        _run(tree)


@pytest.mark.parametrize("path", [
    "docs/development/sprint.md",
    "docs/development/mmf/phase1_first.md",
    "docs/development/planning-and-agents/planning-and-agents.md",
    "docs/development/cpi-decisions.md",
    "docs/development/fleet-reliability/research/synthesis.md",
    "docs/standards/architecture/research/direction.md",
    "docs/standards/architecture/problem-statement.md",
], ids=["sprint", "phase-doc", "component-doc", "cpi-log", "research-pool",
        "direction", "thesis"])
def test_reaching_outside_the_path_boundary_fails_the_run(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch,
        path: str) -> None:
    (tree / "c.md").write_text(_table([("C-001", "`ship`")]))
    _fake_run(monkeypatch, None)
    _crossing(monkeypatch, path)
    with pytest.raises(RuntimeError, match="outside its authorization"):
        _run(tree)


@pytest.mark.parametrize("path", [
    "docs/development/alpha/roadmap.md",
    "docs/standards/architecture/research/candidates.md",
], ids=["the-charter-it-creates", "the-proposal-row-it-places"])
def test_the_two_paths_it_MAY_write_are_not_crossings(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch,
        path: str) -> None:
    """DISCRIMINATOR, and every other guard in this module has one but this did not.

    The forbidden list above is `^docs/development/` and `^docs/standards/` — both
    whole directories — so without this pair the boundary could be maximally
    strict and every assertion above would still pass, while the workflow failed
    on its own output. That is not hypothetical for this workflow: writing a
    charter under `docs/development/` IS the job.
    """
    (tree / "c.md").write_text(_table([("C-001", "`ship`")]))
    _fake_run(monkeypatch, None)
    _crossing(monkeypatch, path)
    assert _run(tree) == PR_URL


def test_deleting_the_candidates_file_fails_before_anything_tries_to_parse_it(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """A WRITE GRANT IS NOT A DELETE GRANT, and the ORDER is the point.

    Checked ahead of every reader, so removing the file raises about the grant
    rather than surfacing as a `FileNotFoundError` from the decision reader — a
    true failure naming the wrong cause, which is the shape that gets a guard
    "fixed" by making the reader tolerant.
    """
    (tree / "c.md").write_text(_table([("C-001", "`ship`")]))
    rel = "docs/standards/architecture/research/candidates.md"
    _fake_run(monkeypatch, None)
    _vanished(monkeypatch, rel)
    with pytest.raises(RuntimeError, match="cease to exist"):
        _run(tree)

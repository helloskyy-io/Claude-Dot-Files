"""The triage split: two workflows, one writer each, and the seam enforced.

`plan-sprint` did two jobs in one run — its own docstring said so — and nothing
could be sequenced between them. `triage-candidates` is the triage half, split
out so feature planning can occupy the gap.

WHAT THIS MODULE GUARDS, and why prose could not:

  1. **`decision` moved and did not widen.** Nine documents now say
     `triage-candidates` owns that column. A document is not a mechanism: the
     narrowed `plan-sprint` still reads `candidates.md`, still holds write access
     to it in its worktree, and a model that has just decided a candidate is too
     small for a sprint section is one plausible step from writing that into the
     cell beside it. `plan_sprint` therefore snapshots the column and fails the
     run if a ruling changed — and THAT is what is exercised here.

  2. **The post-condition MOVED rather than being copied.** "Every row reaches a
     disposition" is triage's contract. Left behind as well, `plan-sprint` would
     fail runs over a column it is forbidden to write — an unsatisfiable
     workflow, and the failure would name the wrong cause.

  3. **The shared fragments are USED, not duplicated.** Distinct job, distinct
     workflow, shared fragments is the repo's answer to near-duplication;
     `build_draft` and `build_draft_minor` are the precedent.

THE FIXTURES ARE SELF-CONTAINED, NEVER THE REPO'S OWN `candidates.md`. A control
that shares a fixture with the code under mutation over-fires, and reading the
live file would make these assertions depend on how many rows happen to be
untriaged this week.
"""

from __future__ import annotations

import inspect
import subprocess
from pathlib import Path

import pytest

from modules.assistant.plan import plan_activities as act
from modules.assistant.plan.plan_sprint import plan_sprint_workflow as sprint
from modules.assistant.plan.triage_candidates import triage_candidates_activities as triage_act
from modules.assistant.plan.triage_candidates import triage_candidates_workflow as triage

PR_URL = "https://github.com/o/r/pull/43"

_HEADER = (
    "| ID | Candidate | `component` | Source | `decision` | `size` | `status` | Note |\n"
    "|---|---|---|---|---|---|---|---|\n"
)


def _table(rows: list[tuple[str, ...]], note: str = "n", component: str = "") -> list[dict]:
    """The candidates holding exactly `rows` as (id, decision[, status[, size]]) tuples.

    KEPT AS A ROW BUILDER ACROSS THE 2026-08-26 FLIP. The store is one file per
    item, so there is no table any more — but all fifty call sites here state
    their fixture as *these candidates, with these cells*, and that is still
    exactly what they mean. `_render` writes; this names.

    `status` defaults to `` `open` `` because that is what every item carries
    while its work is outstanding; the tests that care about the status guard
    pass the third element explicitly.

    `component` defaults to BLANK, and deliberately. Every assertion in this
    module is about the fields and the guards built on them; a component name
    would be inert fixture noise except in the two tests that assert on the
    `component` guard, which pass one explicitly. The items that exercise
    SCAFFOLDING live in `test_plan_candidates.py`, where that is the subject.
    """
    # `size` DEFAULTS TO BLANK, which is what an unsized item looks like and what
    # every item carried when the field arrived. Tests that assert on the size
    # guard pass a fourth element; everything else is unaffected by a field it
    # never reads.
    return [{"id": r[0], "decision": r[1],
             "status": r[2] if len(r) > 2 else "`open`",
             "size": r[3] if len(r) > 3 else "",
             "component": component, "note": note}
            for r in rows]


def _render(store: Path, items: list[dict]) -> Path:
    """Write `items` into a candidates STORE, replacing whatever it held.

    REPLACES, because this stands in for `Path.write_text` on the old single
    file. A directory ACCUMULATES where a file overwrote, so a test that stages
    a store twice would otherwise read both at once.
    """
    store.mkdir(parents=True, exist_ok=True)
    for stale in store.glob("*.md"):
        stale.unlink()
    for it in items:
        (store / f"{it['id']}.md").write_text(
            f"---\nid: {it['id']}\ntitle: a candidate\nstatus: {it['status']}\n"
            f"count: 1\nfiled: 2026-08-26\nfiled_by: test\n"
            f"component: {it['component']}\nsize: {it['size']}\n"
            f"decision: {it['decision']}\n---\n\n{it['note']}\n")
    return store


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """A repo-shaped tmp dir that is BOTH repo_root and worktree.

    The workflows compute `candidates_path.relative_to(repo_root)` and then
    re-root it under the worktree; passing the same path for both keeps that
    arithmetic honest without building two trees.
    """
    (tmp_path / "development").mkdir(parents=True, exist_ok=True)
    # the successor layout too — runner defaults name `development/sprints.md`,
    # which is what MDC and skyynet-master-planning both use.
    (tmp_path / "development").mkdir(parents=True, exist_ok=True)
    (tmp_path / "development" / "sprints.md").write_text("# Sprints\n")
    # and the product research pool at the successor's depth, which is what
    # `--research` now defaults to.
    (tmp_path / "standards" / "architecture" / "research").mkdir(parents=True, exist_ok=True)
    (tmp_path / "r" / "raw").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def stub_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """Silence the helpers that shell out or walk the real tree.

    `existing_work` runs `gh` and iterates `development/`; the reader
    reads a file; `worktree_state` runs `git` and the fixture tree is not a
    repository. None of them is what any assertion here is about, and
    `existing_work` making a live subprocess call would put a network dependency
    in a unit test.

    `worktree_state` is stubbed to the CLEAN answer — an unchanged tree on both
    sides — so the tests that care about the path boundary are the ones that
    override it via `_crossing`. A fixture returning a violation would make every
    other test in the module fail for the wrong reason.

    THE REAL GIT PATH IS NOT LEFT UNTESTED BY THIS. `worktree_state` is exercised
    against an actual repository further down, because the defect it was rewritten
    to close — a renamed-away sprint file reading as untouched — lived in exactly
    the parsing this stub skips.
    """
    monkeypatch.setattr(sprint.act, "existing_work", lambda *a, **k: "<work>")
    monkeypatch.setattr(triage.act, "existing_work", lambda *a, **k: "<work>")
    monkeypatch.setattr(act, "worktree_state", lambda *a, **k: {})


def _crossing(monkeypatch: pytest.MonkeyPatch, path: str) -> None:
    """Make the NEXT snapshot pair look like this run edited `path`.

    Drives the guard through `worktree_state`'s real return SHAPE — a path
    mapped to a content digest — rather than stubbing the comparison, so the
    forbidden/permitted declarations under test are the ones that actually run.
    """
    snapshots = iter([{}, {path: "digest"}])
    monkeypatch.setattr(act, "worktree_state", lambda *a, **k: next(snapshots))


def _vanished(monkeypatch: pytest.MonkeyPatch, path: str) -> None:
    """Make the NEXT snapshot pair look like this run DELETED `path`.

    Sibling of `_crossing`, and the distinction between them is the whole of the
    class this module grew to cover: `_crossing` produces a digest, which is a
    file whose CONTENT moved, while this produces `act.ABSENT`, which is a file
    that is no longer there. `boundary_crossings` sees the first and exempts the
    second whenever the path is permitted.
    """
    snapshots = iter([{}, {path: act.ABSENT}])
    monkeypatch.setattr(act, "worktree_state", lambda *a, **k: next(snapshots))


def _fake_run(module, monkeypatch: pytest.MonkeyPatch, *, writes=None,
              path: Path | None = None, output: str = f"done\n{PR_URL}\n"):
    """Stand in for the model: optionally rewrite the candidates store, then answer.

    Rewriting the store is how a real run offends — it edits items in the
    worktree — so the fake offends the same way rather than by patching the
    guard's inputs. `writes` is the item list the run leaves behind, and it
    REPLACES the store, which is what a rewrite does.
    """
    def run(prompt: str, **kw: object) -> str:
        if writes is not None and path is not None:
            _render(path, writes)
        return output
    monkeypatch.setattr(module.act, "run_claude", run)


# --- `candidate_decisions`: the reader the guard is built on ------------------

def test_it_reads_a_ruling_per_row(tree: Path) -> None:
    f = tree / "tracked" / "candidates"
    _render(f, _table([("C-d1uhacwn", "`ship`"), ("C-p5qvm3e7", "reject"), ("C-q65w30xm", "")]))
    assert act.candidate_decisions(f) == {
        "C-d1uhacwn": "ship", "C-p5qvm3e7": "reject", "C-q65w30xm": ""}


@pytest.mark.parametrize("spelling", ["", " ", "—", "-", "  —  "])
def test_every_spelling_of_UNRULED_reads_as_the_same_thing(tree: Path, spelling: str) -> None:
    """`—` and `` and `-` are one state, and the guard must not see three.

    Were they distinct, a run that tidied an em-dash to an empty cell would be
    reported as having overturned a ruling — a false accusation that fails a
    completed run.
    """
    f = tree / "tracked" / "candidates"
    _render(f, _table([("C-d1uhacwn", spelling)]))
    assert act.candidate_decisions(f) == {"C-d1uhacwn": ""}


def test_MARKUP_is_not_MEANING(tree: Path) -> None:
    """DISCRIMINATOR. The comparison is on the ruling, never on how it is typeset.

    A run that reformats `` `ship` `` to `ship` has changed nothing and must not
    fail; a run that changes `ship` to `reject` has changed everything and must.
    Without this pair the normalisation could be dropped entirely and every other
    assertion here would still pass.
    """
    f = tree / "tracked" / "candidates"
    _render(f, _table([("C-d1uhacwn", "`ship`")]))
    typeset = act.candidate_decisions(f)
    _render(f, _table([("C-d1uhacwn", "ship")]))
    assert act.candidate_decisions(f) == typeset
    _render(f, _table([("C-d1uhacwn", "reject")]))
    assert act.candidate_decisions(f) != typeset


def test_a_missing_file_says_so_rather_than_reading_as_empty(tree: Path) -> None:
    """An empty dict from a missing file would make the guard pass vacuously."""
    with pytest.raises(FileNotFoundError, match="candidates store not found"):
        act.candidate_decisions(tree / "nope.md")


# --- the transferred authority, enforced --------------------------------------
#
# PREDICTED BEFORE RUNNING: of the six mutation shapes below, FOUR must raise
# (a ruling rewritten, a blank filled in, a row deleted, a row appended already
# ruled) and TWO must not (markup reformatted, a proposal appended unruled).
# Observed: 4 and 2. The two exemptions are the discriminating half — a guard
# that simply diffed the two id-to-decision maps would go red on all six, and
# would have been indistinguishable from a correct one against the four.

_ORIGINAL = [("C-d1uhacwn", "`ship`"), ("C-p5qvm3e7", "`reject`"), ("C-q65w30xm", "")]

_OFFENCES = [
    pytest.param([("C-d1uhacwn", "`reject`"), ("C-p5qvm3e7", "`reject`"), ("C-q65w30xm", "")],
                 id="a-ruling-was-rewritten"),
    pytest.param([("C-d1uhacwn", "`ship`"), ("C-p5qvm3e7", "`reject`"), ("C-q65w30xm", "`ship`")],
                 id="a-blank-was-filled-in"),
    pytest.param([("C-d1uhacwn", "`ship`"), ("C-p5qvm3e7", "`reject`")],
                 id="a-row-was-deleted"),
    pytest.param([("C-d1uhacwn", "`ship`"), ("C-p5qvm3e7", "`reject`"), ("C-q65w30xm", ""),
                  ("C-c5y9uqhk", "`ship`")],
                 id="a-new-row-arrived-already-ruled"),
]

_PERMITTED = [
    pytest.param([("C-d1uhacwn", "ship"), ("C-p5qvm3e7", "reject"), ("C-q65w30xm", "—")],
                 id="markup-only-reformat"),
    pytest.param([("C-d1uhacwn", "`ship`"), ("C-p5qvm3e7", "`reject`"), ("C-q65w30xm", ""),
                  ("C-c5y9uqhk", "")],
                 id="a-proposal-was-placed-unruled"),
]


def _run_sprint(tree: Path) -> str:
    """Drive the rebuilt `plan-sprint`: ONE component, ONE granted file.

    THE SIGNATURE LOST `candidates_path` AND `research_dir` ON 2026-08-19, and the
    tests below changed meaning with it. This workflow used to hold a write grant
    on `candidates.md` so it could place ruled `ship` rows, and every assertion
    here that it must not move `decision`, `status` or somebody else's `component`
    was guarding the edges of that grant.

    The grant is gone with the job. So the property is no longer *"it may write
    that file but not those columns"* — it is *"it cannot reach that file at
    all"*, which `boundary_crossings` enforces against the one permitted path.
    Strictly stronger, and enforced by a mechanism that needs no column readers.
    """
    comp = tree / "development" / "alpha"
    comp.mkdir(parents=True, exist_ok=True)
    if not (comp / "roadmap.md").is_file():
        (comp / "roadmap.md").write_text("### Phase 1 — a thing\n\n**Est: ~4 hours**\n")
    return sprint.run_plan_sprint(
        repo_root=tree, worktree=tree, sprint_path=tree / "sprint.md",
        component=comp, verbose=False,
    )


@pytest.mark.parametrize("mutated", _OFFENCES)
def test_plan_sprint_FAILS_when_it_touched_the_decision_column(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch,
        mutated: list) -> None:
    """THE AUTHORITY TRANSFER, AS A MECHANISM — now enforced one level lower.

    Nine documents say `decision` is `triage-candidates`'s. This asserted it of a
    RUN rather than of a paragraph, by comparing the column either side and
    failing on a move.

    THE MECHANISM CHANGED ON 2026-08-19 AND IS STRICTLY STRONGER. `plan-sprint`
    held a write grant on `candidates.md` so it could place ruled `ship` rows;
    that job left, so the grant left, and the file is now simply outside its
    boundary. It cannot move the `decision` column because it cannot write the
    file — which needs no column reader and cannot be defeated by a mutation the
    reader does not model.

    The fixture moves with it, twice over. `candidates.md` now sits under
    `standards/` because that is the prefix `FORBIDDEN_PATHS` names — a file
    at the tree root matched no rule at all — and the offence is staged through
    `_crossing`, this module's own idiom, because the shared fixture stubs
    `worktree_state` to a CONSTANT and a constant cannot express an edit.

    `mutated` is now unused and deliberately kept: each case names a distinct way
    the column could move, and the parametrisation is what says all four are
    denied by one rule rather than four.
    """
    _fake_run(sprint, monkeypatch)
    _crossing(monkeypatch, "standards/architecture/research/candidates.md")

    with pytest.raises(RuntimeError, match="outside its authorization"):
        _run_sprint(tree)


@pytest.mark.parametrize("mutated", _PERMITTED)
def test_plan_sprint_does_NOT_fail_on_a_change_it_was_entitled_to_make(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch,
        mutated: list) -> None:
    """NEGATIVE CONTROL, and it found a real defect in the guard.

    The first cut compared the two id-to-decision maps outright. That made the
    SHARED placement instruction unfollowable: `decision_log_and_reflection.md`
    tells every producing run to append a proposal it surfaced with `decision`
    blank, so this workflow would have placed one exactly as instructed and then
    failed its own post-condition — a run that cannot obey two of its own rules
    at once. Blank is the absence of a ruling; placing one rules nothing.
    """
    f = tree / "tracked" / "candidates"
    _render(f, _table(_ORIGINAL))
    _fake_run(sprint, monkeypatch, writes=_table(mutated), path=f)

    assert _run_sprint(tree) == PR_URL


def test_plan_sprint_is_UNBOTHERED_by_rows_it_merely_left_untriaged(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """THE POST-CONDITION MOVED, IT WAS NOT COPIED.

    `plan-sprint` used to raise when any row was left untriaged. Kept here after
    the split, that check would fail every run against a file triage had not
    caught up with — over a column this workflow is forbidden to write. The
    failure would be real, unfixable from inside this workflow, and would name
    the wrong cause.
    """
    f = tree / "tracked" / "candidates"
    _render(f, _table([("C-d1uhacwn", "`ship`"), ("C-p5qvm3e7", ""), ("C-q65w30xm", "")]))
    _fake_run(sprint, monkeypatch)

    assert _run_sprint(tree) == PR_URL


def test_plan_sprint_still_fails_when_it_produced_no_PR(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """The decision guard must not have displaced the completion contract.

    Ordering matters: the URL is extracted first, so an early-stopped run is
    reported as an early-stopped run rather than as a clean one that happened to
    change no rulings.
    """
    _render(tree / "tracked" / "candidates", _table(_ORIGINAL))
    _fake_run(sprint, monkeypatch, output="I stopped early\n")

    with pytest.raises(RuntimeError, match="produced no PR URL"):
        _run_sprint(tree)


# --- triage keeps the contract it took ----------------------------------------

def _run_triage(tree: Path) -> str:
    return triage.run_triage_candidates(
        repo_root=tree, worktree=tree, candidates_path=tree / "tracked" / "candidates",
        research_dir=tree / "r", verbose=False,
    )


def test_triage_FAILS_when_it_left_a_row_unruled(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """A partial triage that reports as complete is the failure worth catching.

    The PR reads as ruled and is not, and the untriaged rows stay invisible until
    the next research cycle re-proposes them.
    """
    f = tree / "tracked" / "candidates"
    _render(f, _table([("C-d1uhacwn", ""), ("C-p5qvm3e7", ""), ("C-q65w30xm", "")]))
    _fake_run(triage, monkeypatch, writes=_table(
        [("C-d1uhacwn", "`ship`"), ("C-p5qvm3e7", ""), ("C-q65w30xm", "")]), path=f)

    with pytest.raises(RuntimeError, match="left 2 of 3 candidates untriaged"):
        _run_triage(tree)


def test_triage_passes_when_every_row_reached_a_disposition(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Negative control: the contract above must not fail a complete pass."""
    f = tree / "tracked" / "candidates"
    _render(f, _table([("C-d1uhacwn", ""), ("C-p5qvm3e7", "")]))
    _fake_run(triage, monkeypatch, writes=_table(
        [("C-d1uhacwn", "`ship`"), ("C-p5qvm3e7", "`requires review`")]), path=f)

    assert _run_triage(tree) == PR_URL


def test_triage_names_the_rows_it_failed_on(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """An operator cannot act on a count. The ids have to be in the message."""
    f = tree / "tracked" / "candidates"
    _render(f, _table([("C-d1uhacwn", ""), ("C-yi2wk5fn", "")]))
    _fake_run(triage, monkeypatch, writes=_table(
        [("C-d1uhacwn", "`ship`"), ("C-yi2wk5fn", "")]), path=f)

    with pytest.raises(RuntimeError, match="C-yi2wk5fn"):
        _run_triage(tree)


# --- the working-set notes discriminate ---------------------------------------

def test_an_empty_working_set_is_told_it_is_REVISING_not_idle() -> None:
    """Zero untriaged is a state, not a no-op, and silence reads as "stop".

    A `--pr` re-dispatch finds every row ruled. Told only `0 untriaged`, a model
    reasonably concludes there is nothing to do and ends the run — on a pass whose
    whole job is to close a reviewer's runway.
    """
    empty = triage._working_set(
        {"total": 5, "untriaged": 0, "triaged": 5, "untriaged_ids": []})
    assert "REVISE" in empty and "no fresh working set" in empty.lower()

    full = triage._working_set(
        {"total": 5, "untriaged": 2, "triaged": 3, "untriaged_ids": ["C-d1uhacwn", "C-p5qvm3e7"]})
    assert "C-d1uhacwn" in full and "C-p5qvm3e7" in full
    assert "REVISE" not in full


def test_plan_sprint_is_told_the_untriaged_rows_are_NOT_ITS_JOB() -> None:
    """A model reading blank cells in a column it is reading will fill them.

    Standalone, this workflow meets files triage has not run against. The note has
    to name the rows AND refuse them; naming them alone reads as a work list.
    """
    note = sprint._untriaged_note(
        {"total": 3, "untriaged": 1, "triaged": 2, "untriaged_ids": ["C-hjwrspgl"]})
    assert "C-hjwrspgl" in note
    assert "NOT YOURS" in note
    assert "triage-candidates" in note

    none_left = sprint._untriaged_note(
        {"total": 3, "untriaged": 0, "triaged": 3, "untriaged_ids": []})
    assert "NOT YOURS" not in none_left


# --- shared fragments, not copies ---------------------------------------------

_SHARED = Path(triage.__file__).resolve().parents[2] / "prompts"


@pytest.mark.parametrize("workflow", [sprint, triage], ids=["plan_sprint", "triage"])
@pytest.mark.parametrize("fragment", ["decision_log_and_reflection", "headless_execution_guard"])
def test_both_workflows_INTERPOLATE_the_shared_fragment(workflow, fragment: str) -> None:
    """Distinct job, distinct workflow, SHARED fragments.

    `build_draft` and `build_draft_minor` are separate workflows for jobs closer
    together than these two, and they share these same fragments — that is the
    repo's settled answer to near-duplication. A split that copied the
    peer-review discipline into a second prompt would have two texts drifting
    apart with nothing comparing them.
    """
    source = Path(workflow.__file__).read_text()
    assert f'act.shared_prompt("{fragment}")' in source, (
        f"{workflow.__name__} no longer interpolates the shared {fragment} "
        f"fragment. If it grew its own copy, the two will drift and nothing here "
        f"or anywhere else compares them."
    )


@pytest.mark.parametrize("fragment", ["decision_log_and_reflection", "headless_execution_guard"])
def test_the_shared_fragment_is_not_ALSO_pasted_into_the_prompt(fragment: str) -> None:
    """The interpolation is worthless if a copy sits beside it.

    Verified against the fragment's own opening line rather than its title: a
    heading can legitimately be referenced in prose, while its body cannot
    legitimately appear twice.
    """
    body = (_SHARED / f"{fragment}.md").read_text()
    signature = next(line for line in body.splitlines() if len(line.strip()) > 40)
    for prompt in (Path(triage.PROMPTS) / "triage_candidates.md",
                   Path(sprint.PROMPTS) / "plan_sprint.md"):
        assert signature not in prompt.read_text(), (
            f"{prompt.name} contains a line copied verbatim from {fragment}.md. "
            f"It is interpolated at render time; a second copy is drift waiting to "
            f"happen."
        )


def test_the_signature_probe_would_actually_find_a_copy() -> None:
    """Positive control on the check above.

    `signature` is derived from a file that could change shape — if it ever
    resolved to something trivially absent, the assertion would pass over a
    wholesale copy-paste. This proves it matches the text it was taken from.
    """
    body = (_SHARED / "headless_execution_guard.md").read_text()
    signature = next(line for line in body.splitlines() if len(line.strip()) > 40)
    assert signature in body, "the probe cannot find its own source line"
    assert len(signature.strip()) > 40


# --- the two workflows are genuinely separate ---------------------------------

def test_plan_sprint_no_longer_carries_triage_instructions() -> None:
    """The job left, so its instructions must have left with it.

    A prompt that still explains how to rule a candidate, in a workflow forbidden
    to write `decision`, is an instruction the run cannot follow and a reviewer
    cannot check. It is also how the split silently un-does itself.
    """
    text = (Path(sprint.PROMPTS) / "plan_sprint.md").read_text()
    for gone in ("D-NNN", "release valve", "requires review`, not `ship"):
        assert gone not in text, (
            f"plan_sprint.md still contains triage instruction {gone!r}. Triage "
            f"moved to triage-candidates; this prompt tells a run to do something "
            f"its own post-condition fails it for."
        )
    # THE POSITIVE HALF CHANGED SHAPE ON 2026-08-19 AND IS STILL A POSITIVE HALF.
    # It used to require the prompt to SAY the `decision` column belongs to
    # triage — a sentence explaining a boundary this workflow sat next to,
    # because it still held a write grant on the file that column lives in.
    #
    # It does not any more. The grant went with the placing job, so the prompt no
    # longer explains a column it cannot reach; it names the prohibition once in
    # the authorization table and lets the path boundary do the work. Asserting
    # the old sentence would now require re-adding an explanation of a file this
    # run never opens.
    assert "`decision` is `triage-candidates`'s alone" in text, (
        "plan_sprint.md no longer names ruling a candidate as forbidden. The "
        "path boundary stops it, but the authorization table is what a reader "
        "and `test_authorization_is_observed` both key on."
    )


def test_triage_is_given_no_sprint_authority() -> None:
    """The sprint override did NOT transfer, and it must not.

    `sprint.md` is the operator's sequencing surface and exactly one workflow
    holds an override to write it. A split that handed the same authority to both
    halves would have doubled the number of autonomous writers to that file while
    reading as a refactor.

    ASSERTED AGAINST THE SIGNATURE, NOT THE FILE'S TEXT. This was a substring
    search over the whole module source, and it went red on a COMMENT that used
    the words `sprint_path` to explain why there is no such parameter — a check
    reading a region far wider than the property it names. `inspect.signature` is
    the property itself: whatever the prose says, this is what the function takes.
    """
    params = inspect.signature(triage.run_triage_candidates).parameters
    assert not [p for p in params if "sprint" in p], (
        f"run_triage_candidates takes {sorted(params)} — a sprint parameter is how "
        f"the authority creeps back. It has no business knowing where sprint.md is."
    )
    text = (Path(triage.PROMPTS) / "triage_candidates.md").read_text()
    assert "Touch `sprint.md` at all" in text and "you do not.**" in text


# --- the guards the split had left on prose alone -----------------------------

def test_triage_FAILS_when_it_edited_the_sprint_plan(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """THE MIRROR OF plan-sprint's DECISION GUARD, and it was missing.

    Taking no `sprint_path` parameter constrains the SIGNATURE. The run holds the
    whole worktree either way, and its own prompt hands it the trigger — "if a
    candidate you ship looks like it needs a sprint section, say so" — one step
    from writing the section instead of saying so. The argument that built the
    decision guard ("prose is not a mechanism") reaches this boundary unchanged.
    """
    f = tree / "tracked" / "candidates"
    _render(f, _table([("C-d1uhacwn", "")]))
    _fake_run(triage, monkeypatch, writes=_table([("C-d1uhacwn", "`ship`")]), path=f)
    _crossing(monkeypatch, "development/sprint.md")

    with pytest.raises(RuntimeError, match="outside its authorization"):
        _run_triage(tree)


@pytest.mark.parametrize("workflow,runner", [(triage, _run_triage)], ids=["triage"])
# PLAN_SPRINT DROPPED FROM THIS PARAMETRISATION 2026-08-19, and not because the
# rule stopped applying to it. The rule is now enforced one level lower: the
# rebuild took its `candidates.md` write grant away with the placing job, so the
# file is outside its boundary and no column comparator runs for it at all.
# `test_plan_sprint_FAILS_when_it_touched_the_decision_column` asserts that
# stronger property against the path. Keeping it here would test a guard the
# workflow no longer has and read as coverage.
def test_NEITHER_workflow_may_move_the_status_column(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch,
        workflow, runner) -> None:
    """`decision` MOVED between the two; `status` moved nowhere, because it was
    never either one's.

    The store gives `status` to "a later process" — `plan-draft`, or the build
    that completes the item — and its terminal values are Tracked Items §4's
    `adopted` / `rejected` since the 2026-08-26 flip, not the table's `closed` — and both prompts list it under MAY NOT. Ruling a
    candidate is not doing it, and placing one is not finishing it. Without this,
    the split enforced one of the two columns it names and trusted prose for the
    other.
    """
    f = tree / "tracked" / "candidates"
    _render(f, _table([("C-d1uhacwn", "`ship`", "`open`")]))
    _fake_run(workflow, monkeypatch,
              writes=_table([("C-d1uhacwn", "`ship`", "`adopted`")]), path=f)

    with pytest.raises(RuntimeError, match="changed the `status` column"):
        runner(tree)


@pytest.mark.parametrize("workflow,runner", [(triage, _run_triage)], ids=["triage"])
# PLAN_SPRINT DROPPED FROM THIS PARAMETRISATION 2026-08-19, and not because the
# rule stopped applying to it. The rule is now enforced one level lower: the
# rebuild took its `candidates.md` write grant away with the placing job, so the
# file is outside its boundary and no column comparator runs for it at all.
# `test_plan_sprint_FAILS_when_it_touched_the_decision_column` asserts that
# stronger property against the path. Keeping it here would test a guard the
# workflow no longer has and read as coverage.
def test_NEITHER_workflow_may_name_the_component_on_somebody_elses_row(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch,
        workflow, runner) -> None:
    """`component` is the FILER's, and it is the one column whose guess gets BUILT.

    `decision` and `status` each got a comparator and a MAY NOT row when the
    column split happened; `component` arrived with neither, and it is the higher
    stake of the three: `plan-candidates` runs in the parent immediately after
    these two and turns whatever the cell says into a committed
    `development/<name>/` on the same branch. A guessed name is not a bad
    cell, it is a directory and two research dispatches.
    """
    f = tree / "tracked" / "candidates"
    _render(f, _table([("C-d1uhacwn", "`ship`", "`open`")]))
    _fake_run(workflow, monkeypatch, writes=_table(
        [("C-d1uhacwn", "`ship`", "`open`")], component="guessed-from-a-summary"), path=f)

    with pytest.raises(RuntimeError, match="`component` column"):
        runner(tree)


def test_a_component_named_on_a_row_the_run_APPENDED_is_permitted(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """NEGATIVE CONTROL, and without it the guard forbids what another rule REQUIRES.

    `decision_log_and_reflection.md` instructs every producing run to file a
    proposal it surfaced AND to name that proposal's component. Judging new rows
    would make the two instructions mutually unfollowable. Only a row that
    already existed can have had its component set by somebody who did not file it.

    `plan_sprint` ONLY, exactly as the sibling `status` control is — and for the
    same reason rather than a copied shape. A row appended with a blank
    `decision` fails triage's own completion post-condition before any column
    guard is reached, so parametrizing this over triage would assert about that
    post-condition instead of about this guard.
    """
    f = tree / "tracked" / "candidates"
    _render(f, _table([("C-d1uhacwn", "`ship`", "`open`")]))
    body = (_table([("C-d1uhacwn", "`ship`", "`open`")])
            + _table([("C-p5qvm3e7", "", "`open`")], component="filed-by-this-run"))
    _fake_run(sprint, monkeypatch, writes=body, path=f)

    assert _run_sprint(tree) == PR_URL


def test_a_row_APPENDED_with_a_status_is_not_a_status_the_run_moved(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """NEGATIVE CONTROL, and it is the same exemption the decision guard needed.

    `decision_log_and_reflection.md` tells every producing run to place a proposal
    it surfaced with `status: open`. Judging new rows would make that shared
    instruction unfollowable — the run would obey one of its own rules and fail
    another. Only a row that already existed can have had its status MOVED.
    """
    f = tree / "tracked" / "candidates"
    _render(f, _table([("C-d1uhacwn", "`ship`", "`open`")]))
    _fake_run(sprint, monkeypatch, writes=_table(
        [("C-d1uhacwn", "`ship`", "`open`"), ("C-p5qvm3e7", "", "`open`")]), path=f)

    assert _run_sprint(tree) == PR_URL


def test_the_two_readers_agree_on_what_BLANK_means(tree: Path) -> None:
    """REGRESSION. Two hand-written normalisations drifted, and the drift was silent.

    `candidate_counts` stripped `.strip().strip("`")` and `candidate_decisions`
    `.strip().strip("`").strip()`. A cell typed `` ` — ` `` — padding INSIDE the
    backticks — came out `" — "` under the first and `""` under the second, so the
    row read RULED to the counter and BLANK to the guard. `triage-candidates`'s
    completion post-condition is built on the counter, so that row would drop out
    of the working set unruled while the post-condition reported a complete pass.

    Both now go through one `normalise_cell`, and this walks the spellings that
    told them apart.

    ASSERTED ON THE VALUE, NOT ON AGREEMENT — and a mutation is what forced that.
    The first cut checked only that the two readers AGREE, which sharing one
    helper makes structurally true: restoring the old two-strip normalisation
    changed both identically and the test stayed green. An assertion that cannot
    fail is not a regression test. Each reader is now held to the ANSWER, so the
    old normalisation fails both.
    """
    f = tree / "tracked" / "candidates"
    for spelling in ("` — `", "`  `", "` `", "—", "`—`", " - ", "``", "`  —  `"):
        _render(f, _table([("C-d1uhacwn", spelling)]))
        assert act.candidate_counts(f)["untriaged_ids"] == ["C-d1uhacwn"], (
            f"candidate_counts read {spelling!r} as RULED. `triage-candidates`'s "
            f"working set and its completion post-condition are both built on this "
            f"count, so the row would never be offered for triage and the run would "
            f"still report a complete pass."
        )
        assert act.candidate_decisions(f)["C-d1uhacwn"] == "", (
            f"candidate_decisions read {spelling!r} as a ruling. plan-sprint's guard "
            f"compares this before and after, so a run that merely tidied the cell "
            f"would be failed for overturning a ruling that was never there."
        )


def _id_keyed_readers() -> set[str]:
    """Every `candidate_*` reader in the family that returns a row-keyed map.

    DISCOVERED FROM THE ANNOTATIONS, NOT LISTED, and that is the whole point of
    it being a function. The roster below is hand-written — it has to be, since
    each entry names the alias its registry entry uses — and a hand-written
    roster goes stale in exactly the way this test already caught once: it
    asserted over two readers while three existed, so `before_component`'s entry
    read as covered and the column it covers was never compared. Comparing the
    roster against a DERIVED set means the fourth reader fails here the moment it
    is written, rather than the next time somebody re-reads this test.

    `dict[str, str]` is the shape that makes a reader id-keyed; `candidate_counts`
    returns `dict[str, int]` and is a tally rather than a map, so it is correctly
    absent. Annotations are strings because both modules carry
    `from __future__ import annotations`, which is why this compares text.
    """
    found = set()
    for module, alias in ((act, "act"),):
        for name, fn in vars(module).items():
            if not name.startswith("candidate_") or not callable(fn):
                continue
            if getattr(fn, "__annotations__", {}).get("return") == "dict[str, str]":
                found.add(f"{alias}.{name}")
    return found


_ID_KEYED_READERS = _id_keyed_readers()


def test_the_reader_sweep_finds_readers_at_all() -> None:
    """POSITIVE CONTROL: an empty derived set makes the roster check vacuous.

    `set(roster) == set()` fails loudly, but a sweep that found only SOME would
    not — and a sweep that found none would turn the comparison below into a
    claim nobody can read. This is the floor that makes the comparison mean
    something.
    """
    assert len(_ID_KEYED_READERS) >= 3, (
        f"the id-keyed reader sweep found {sorted(_ID_KEYED_READERS)}. It matches "
        f"`candidate_*` functions annotated `-> dict[str, str]`; if that "
        f"annotation or naming changed, the roster below is being compared "
        f"against nothing.")


@pytest.mark.parametrize("rows", [
    pytest.param([("C-d1uhacwn", "`ship`"), ("C-p5qvm3e7", ""), ("C-q65w30xm", "—")], id="mixed"),
    pytest.param([("C-d1uhacwn", "`ship`", ""), ("C-p5qvm3e7", "", "`open`")], id="blank-status"),
    pytest.param([], id="no-rows"),
], ids=None)
def test_the_two_candidate_READERS_ALWAYS_KEY_THE_SAME_ROWS(tree: Path, rows: list) -> None:
    """THE INVARIANT `plan-sprint`'S DISAPPEARANCE REGISTRY RESTS ON, made executable.

    `DISAPPEARANCE_OBSERVERS["before_status"]` is the one entry in either
    workflow that does not name a guard applied to its OWN snapshot: it claims
    coverage by `before`'s guard, on the grounds that `act.candidate_statuses`
    and `act.candidate_decisions` are both built from `act.candidate_rows` and so
    can never disagree about which ids exist. That claim is TRUE today and was
    ASSERTED rather than checked — which is precisely the shape
    `observer_registry` exists to distrust, since resolving the symbols an entry
    names proves the functions exist and says nothing about the reasoning
    between them.

    So the reasoning is what this holds. Separate the two readers' key sets and
    a deleted row becomes invisible to `plan-sprint` again — the whole channel,
    silently, with the registry still reading as covered.
    """
    f = tree / "tracked" / "candidates"
    _render(f, _table(rows))
    keyed = {
        "act.candidate_statuses": act.candidate_statuses(f).keys(),
        "act.candidate_decisions": act.candidate_decisions(f).keys(),
        # `size` joined on 2026-08-19 as triage's SECOND ruling. It keys the
        # same rows for the same reason the others do — all four are built
        # from `candidate_rows`, so a row absent from one is absent from all.
        "act.candidate_sizes": act.candidate_sizes(f).keys(),
        # THE THIRD READER, ADDED WHEN `component` GOT ITS GUARD AND NOT BEFORE.
        # Both workflows' `before_component` registry entries discharge their
        # deletion obligation by naming exactly this coupling — and this test
        # asserted over two readers while three exist, so the entry read as
        # covered and the column it covers was never in the assertion.
        "act.candidate_components": act.candidate_components(f).keys(),
    }
    assert set(keyed) == _ID_KEYED_READERS, (
        f"the roster above is {sorted(keyed)} and the id-keyed readers in the "
        f"family are {sorted(_ID_KEYED_READERS)}. A reader missing from the "
        f"roster is one whose key set nothing compares, which is how the "
        f"`before_component` entry read as covered while the column it covers "
        f"was never in the assertion.")
    disagreeing = [name for name, ks in keyed.items()
                   if ks != keyed["act.candidate_statuses"]]
    assert not disagreeing, (
        f"{disagreeing} no longer key the same rows as the others, so the "
        f"row-deletion coverage both workflows' DISAPPEARANCE_OBSERVERS entries "
        f"claim comes from a sibling column's guard has a hole in it")


def test_the_dry_run_renders_the_SAME_correction_note_a_live_run_does() -> None:
    """`--dry-run` previewed text no model would ever receive.

    It rendered `_untriaged_note(counts)` alone while the live run prefixed the
    counted line, so the one flag whose entire purpose is "count and render, no
    model, no spend" could not show a regression in the counted line. Both call
    `correction_note` now, and this is what holds them together.
    """
    counts = {"total": 9, "untriaged": 2, "triaged": 7, "untriaged_ids": ["C-1", "C-2"]}
    live = sprint.correction_note(counts, correction_pass=False)
    assert "Counted in code" in live and "NOT YOURS" in live
    assert sprint._untriaged_note(counts) in live, (
        "the counted line and the untriaged note must both be in the one slot — "
        "rendering half of it is the bug this test exists for"
    )
    correction = sprint.correction_note(counts, correction_pass=True)
    assert "CORRECTION PASS" in correction
    assert all(str(counts[k]) in correction for k in ("total", "triaged", "untriaged")), (
        "the correction branch dropped the authoritative counts. Stage 4 requires "
        "the report to state how many candidates still carry a blank `decision`, "
        "so without them that figure is model-derived on the pass most likely to "
        "be the last one anybody reads — the invented-count class "
        "`candidate_counts` exists to prevent"
    )


# --- the rest of the authorization table, observed rather than asserted -------
#
# `test_authorization_is_observed.py` proves every `You MAY NOT` row NAMES a
# mechanism and that the mechanism exists. These prove the mechanisms FIRE. The
# split had a real guard for two rows and prose for the rest, and the prompt told
# the model all of them were enforced.

@pytest.mark.parametrize("path", [
    "development/temporal-integration/phase-1.md",   # "any phase doc"
    "standards/architecture/problem-statement.md",   # named explicitly
    "standards/workflow-scripts.md",                 # "anything else under"
])
def test_triage_FAILS_when_it_reached_outside_its_authorization(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch,
        path: str) -> None:
    """Three MAY NOT rows that had no mechanism at all until now.

    Each was a prohibition the prompt asserted was enforced, sitting one row
    below the two that genuinely were. A phase doc rewritten by a triage pass is
    planning done by a workflow whose whole contract is that it decides and does
    not plan.
    """
    f = tree / "tracked" / "candidates"
    _render(f, _table([("C-d1uhacwn", "")]))
    _fake_run(triage, monkeypatch, writes=_table([("C-d1uhacwn", "`ship`")]), path=f)
    _crossing(monkeypatch, path)

    with pytest.raises(RuntimeError, match="outside its authorization"):
        _run_triage(tree)


# THE FIXTURE'S OWN PATHS, WHICH ARE NOT THIS REPO'S. `_run_triage` passes
# `candidates_path=tree / "tracked" / "candidates"` and `research_dir=tree / "r"`, and the grants
# now DERIVE from those arguments rather than naming this repo's pool as a
# literal. Spelling the repo's default here passed only because the grant ignored
# what the run was pointed at — so this parametrize is now exercising the
# non-default pool that `--candidates` and `--research` exist to reach.
@pytest.mark.parametrize("path", ["tracked/candidates/C-d1uhacwn.md"])
def test_triage_is_NOT_failed_for_writing_the_two_files_it_exists_to_write(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch,
        path: str) -> None:
    """NEGATIVE CONTROL, and the one this guard would most easily get wrong.

    Both files live UNDER `standards/`, which the same table forbids
    wholesale. A boundary without the exception fails every correct run — and it
    would fail it after the PR was already open, which is the worst moment to
    discover a guard is wrong.
    """
    f = tree / "tracked" / "candidates"
    _render(f, _table([("C-d1uhacwn", "")]))
    _fake_run(triage, monkeypatch, writes=_table([("C-d1uhacwn", "`ship`")]), path=f)
    _crossing(monkeypatch, path)

    assert _run_triage(tree) == PR_URL


def test_triage_FAILS_when_a_candidate_row_simply_VANISHED(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """DELETING an untriaged row passed the completion post-condition.

    That post-condition counts blank `decision` cells, so a deleted row drops the
    count exactly as ruling it would: the run reports a complete triage over a
    candidate that no longer exists. Both status guards are blind to it by
    construction — they judge the ids present on BOTH sides. The file's whole
    promise is that a rejected candidate stays visibly rejected instead of being
    re-proposed by the next research cycle.
    """
    f = tree / "tracked" / "candidates"
    _render(f, _table([("C-d1uhacwn", ""), ("C-p5qvm3e7", "")]))
    _fake_run(triage, monkeypatch, writes=_table([("C-d1uhacwn", "`ship`")]), path=f)

    with pytest.raises(RuntimeError, match="deleted 1 candidate row"):
        _run_triage(tree)


def test_plan_sprint_FAILS_when_it_ticked_a_completion_checkbox(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """A checkbox means SHIPPED AND VALIDATED, and this workflow validates nothing.

    It places work that will be built later. A plan reporting work nobody has
    built is worse than one merely out of date, because the operator reads that
    file to know what is done.
    """
    sp = tree / "sprint.md"
    sp.write_text("## Sprint: X\n\n- [ ] build the thing\n- [ ] test the thing\n")
    f = tree / "tracked" / "candidates"
    _render(f, _table([("C-d1uhacwn", "`ship`")]))

    def run(prompt: str, **kw: object) -> str:
        sp.write_text("## Sprint: X\n\n- [x] build the thing\n- [ ] test the thing\n")
        return f"done\n{PR_URL}\n"
    monkeypatch.setattr(sprint.act, "run_claude", run)

    with pytest.raises(RuntimeError, match="flipped 1 completion checkbox"):
        _run_sprint(tree)


def test_plan_sprint_may_ADD_an_unchecked_milestone_and_REORDER_the_file(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """NEGATIVE CONTROL covering both things this workflow is FOR.

    Adding a milestone and re-ordering sections to reflect dependency are both in
    its MAY column. Counting boxes by TEXT rather than by line is what lets a
    re-order through — a positional comparison would fire on a box that merely
    moved, which is the shape that makes a guard get deleted rather than fixed.
    """
    sp = tree / "sprint.md"
    sp.write_text("## Sprint: A\n\n- [x] done already\n\n## Sprint: B\n\n- [ ] b1\n")
    f = tree / "tracked" / "candidates"
    _render(f, _table([("C-d1uhacwn", "`ship`")]))

    def run(prompt: str, **kw: object) -> str:
        sp.write_text("## Sprint: B\n\n- [ ] b1\n- [ ] b2 is new\n\n"
                      "## Sprint: A\n\n- [x] done already\n")
        return f"done\n{PR_URL}\n"
    monkeypatch.setattr(sprint.act, "run_claude", run)

    assert _run_sprint(tree) == PR_URL


def test_plan_sprint_FAILS_when_it_appended_to_the_operators_inbox(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """`direction.md` is `triage-candidates`'s to append to and this one's never.

    Deliberately NOT in `permitted_paths`, and that absence IS the mechanism —
    which is why it is asserted here rather than left to be inferred from a list
    it does not appear on.
    """
    f = tree / "tracked" / "candidates"
    _render(f, _table([("C-d1uhacwn", "`ship`")]))
    _fake_run(sprint, monkeypatch)
    _crossing(monkeypatch, "standards/architecture/research/direction.md")

    with pytest.raises(RuntimeError, match="outside its authorization"):
        _run_sprint(tree)


# --- DISAPPEARANCE: the class every comparator above is blind to --------------
#
# Each guard above judges what is present on BOTH sides of the snapshot, so a
# row, a checkbox or a whole file that is simply GONE is invisible to all of
# them. Four channels were demonstrated returning a PR URL and a green run
# before these existed; `test_disappearance_is_observed.py` holds the class, and
# these prove each mechanism actually fires.

@pytest.mark.parametrize("workflow,runner,path", [
    # AN ITEM INSIDE THE STORE, not the store itself. The grant now covers a
    # DIRECTORY, so the deletion a run can actually commit is of one item file —
    # and that is the one this guard has to catch, because deleting an item is
    # how a ruled candidate silently stops existing.
    (triage, _run_triage, "tracked/candidates/C-d1uhacwn.md"),
    (sprint, _run_sprint, "sprint.md"),
    # `(sprint, "c.md")` REMOVED 2026-08-19: plan-sprint no longer holds a
    # candidates grant, so there is no permitted file for it to delete there —
    # the case it tested cannot arise, and a parametrisation that cannot arise
    # reads as coverage while asserting nothing.
], ids=["triage-candidates-file", "sprint-plan"])
def test_NEITHER_workflow_may_delete_a_file_it_is_merely_PERMITTED_to_write(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch,
        workflow, runner, path: str) -> None:
    """A WRITE GRANT IS NOT A DELETE GRANT — every grant in the family, not one.

    `boundary_crossings` exempts a permitted path unconditionally, so before
    this the exemption list was precisely the list of files whose removal
    nothing could see. `plan-sprint` holds the family's only override to write
    `sprint.md`, and deleting it returned a PR URL and a green run.
    """
    _render(tree / "tracked" / "candidates", _table([("C-d1uhacwn", "`ship`")]))
    _fake_run(workflow, monkeypatch)
    _vanished(monkeypatch, path)

    with pytest.raises(RuntimeError, match="cease to exist"):
        runner(tree)


def test_plan_sprint_FAILS_when_it_ERASED_a_completion_checkbox(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """The other half of "flip a checkbox", and only one half was observed.

    `Counter` subtraction keeps positive counts, so `after - before` reports a
    tick ADDED and says nothing about one erased — by unticking it, by rewording
    the milestone, or by dropping the section that held it. A plan reporting work
    nobody built is bad; a plan that has forgotten work somebody DID is worse,
    because nothing downstream will ask for it again.
    """
    sp = tree / "sprint.md"
    sp.write_text("## Sprint: X\n\n- [x] shipped the thing\n- [ ] next thing\n")
    _render(tree / "tracked" / "candidates", _table([("C-d1uhacwn", "`ship`")]))

    def run(prompt: str, **kw: object) -> str:
        sp.write_text("## Sprint: X\n\n- [ ] next thing\n")
        return f"done\n{PR_URL}\n"
    monkeypatch.setattr(sprint.act, "run_claude", run)

    with pytest.raises(RuntimeError, match="ERASED: shipped the thing"):
        _run_sprint(tree)


# --- the observer itself, against a REAL repository ---------------------------

@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A git repo with an `origin/main` to diff against, and a sprint plan in it.

    STUBBED EVERYWHERE ELSE IN THIS MODULE, AND THAT IS THE POINT OF THIS FIXTURE.
    The defect these tests exist for lived in the git parsing itself, so a suite
    that only ever monkeypatched the observer reported green over it.
    """
    import subprocess

    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=str(tmp_path), check=True,
                       capture_output=True)

    (tmp_path / "development").mkdir(parents=True, exist_ok=True)
    # the successor layout too — runner defaults name `development/sprints.md`,
    # which is what MDC and skyynet-master-planning both use.
    (tmp_path / "development").mkdir(parents=True, exist_ok=True)
    (tmp_path / "development" / "sprints.md").write_text("# Sprints\n")
    (tmp_path / "development" / "sprint.md").write_text("## Sprint: X\n")
    git("init", "-q", "-b", "main")
    git("-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base")
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    return tmp_path


def test_renaming_the_sprint_file_AWAY_is_seen_as_editing_it(repo: Path) -> None:
    """THE BYPASS THE PREVIOUS GUARD HAD, reproduced before it was closed.

    It split a `git status --porcelain` rename line on `" -> "` and kept the
    DESTINATION, so `git mv sprint.md notes.md` yielded `notes.md`, matched no
    sprint pattern, and the run reported success over an edit to the operator's
    sequencing surface. `--no-renames` reports the two halves separately, so
    there is no arrow to parse and the source half is no longer discarded.
    """
    import subprocess

    before = act.worktree_state(repo)
    subprocess.run(["git", "mv", "development/sprint.md",
                    "development/notes.md"], cwd=str(repo), check=True,
                   capture_output=True)
    crossed = act.boundary_crossings(before, act.worktree_state(repo),
                                     triage.FORBIDDEN_PATHS,
                                     triage.permitted_paths(Path("standards/architecture/research/candidates.md"), Path("standards/architecture/research")))
    assert "development/sprint.md" in crossed, (
        f"a renamed-away sprint plan read as untouched; observed {crossed}")


def test_an_uncommitted_edit_counts_and_so_does_a_committed_one(repo: Path) -> None:
    """Both halves of the tree are read — status AND the diff against the base.

    A run that commits its offence is not less offensive than one that leaves it
    dirty, and `plan-sprint` commits before it reports.
    """
    import subprocess

    before = act.worktree_state(repo)
    (repo / "development" / "sprint.md").write_text("## Sprint: X\n\nedited\n")
    assert act.boundary_crossings(before, act.worktree_state(repo),
                                  triage.FORBIDDEN_PATHS,
                                     triage.permitted_paths(Path("standards/architecture/research/candidates.md"), Path("standards/architecture/research")))

    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-aqm", "edit"], cwd=str(repo), check=True,
                   capture_output=True)
    assert act.boundary_crossings(before, act.worktree_state(repo),
                                  triage.FORBIDDEN_PATHS,
                                     triage.permitted_paths(Path("standards/architecture/research/candidates.md"), Path("standards/architecture/research"))), (
        "committing the edit made it invisible — the diff half of the observer "
        "is not reading the base ref")


def test_a_file_a_PREVIOUS_child_changed_is_not_charged_to_this_run(repo: Path) -> None:
    """WHY THE SNAPSHOT IS TAKEN AROUND THE RUN AND NOT AGAINST `origin/main`.

    `plan-sprint` runs LAST on a branch `triage-candidates` has already written
    `direction.md` on. A diff against the base would report triage's legitimate
    row as plan-sprint's forbidden edit, failing a correct run — and the obvious
    "fix" for that is to weaken the guard.
    """
    import subprocess

    d = repo / "standards" / "architecture" / "research"
    d.mkdir(parents=True)
    (d / "direction.md").write_text("| `D-001` | r | w | `C-d1uhacwn` | `open` |\n")
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "add", "-A"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "triage did this"], cwd=str(repo), check=True,
                   capture_output=True)

    before = act.worktree_state(repo)          # plan-sprint starts here
    rel = "development/sprint.md"
    assert act.boundary_crossings(before, act.worktree_state(repo),
                                  sprint.FORBIDDEN_PATHS,
                                  sprint.permitted_paths(rel)) == [], (
        "an edit made before this run started was charged to it")


@pytest.mark.parametrize("how", ["deleted", "renamed-out-of-the-tree",
                                 "renamed-within-the-tree"])
def test_a_DELETED_sprint_plan_is_seen_by_the_real_observer(repo: Path, how: str) -> None:
    """AGAINST REAL GIT, because the stub cannot prove the sentinel is produced.

    Everything above drives `grants_that_vanished` through a hand-made snapshot.
    That proves the comparison, not the READING — and the reading is where this
    family's bypasses have all lived. `ABSENT` only means "deleted" if
    `worktree_state` actually emits it for a file git reports as changed and
    that is not on disk, and a rename produces exactly that on the SOURCE half
    only because `--no-renames` splits the pair.

    Three spellings, because they defeat different things. Deleting the file is
    the plain case. `git mv` OUT of `development/` also slips past
    `boundary_crossings` entirely — the destination matches no forbidden pattern
    and the source half is exempted as permitted — so nothing at all fired for
    it, and the assertion below pins that. `git mv` WITHIN the directory is the
    one case the path boundary did catch, via the destination; it is here
    because the guard order changed, and the run must still fail on the SOURCE
    file vanishing rather than depending on where the destination happened to
    land.
    """
    import subprocess

    rel = "development/sprint.md"
    destination = {"renamed-out-of-the-tree": "notes.md",
                   "renamed-within-the-tree": "development/notes.md"}
    before = act.worktree_state(repo)
    if how == "deleted":
        (repo / rel).unlink()
    else:
        subprocess.run(["git", "mv", rel, destination[how]], cwd=str(repo),
                       check=True, capture_output=True)

    after = act.worktree_state(repo)
    assert act.grants_that_vanished(before, after,
                                    sprint.permitted_paths(rel)) == [rel], (
        f"a {how} sprint plan read as present; observed {after.get(rel)!r}")
    if how != "renamed-within-the-tree":
        assert act.boundary_crossings(before, after, sprint.FORBIDDEN_PATHS,
                                      sprint.permitted_paths(rel)) == [], (
            "the path boundary caught this on its own, so the control proves "
            "nothing about the check written for it")


def test_a_sprint_plan_merely_EDITED_is_not_read_as_vanished(repo: Path) -> None:
    """DISCRIMINATOR against real git: editing is what the override is FOR.

    Without this the new check could report every granted path it saw and every
    assertion above would still pass — while failing every correct run, which is
    the shape that gets a guard deleted rather than fixed.
    """
    rel = "development/sprint.md"
    before = act.worktree_state(repo)
    (repo / rel).write_text("## Sprint: X\n\n- [ ] a new milestone\n")

    assert act.grants_that_vanished(before, act.worktree_state(repo),
                                    sprint.permitted_paths(rel)) == []


def test_the_observer_RAISES_when_git_cannot_answer(tmp_path: Path) -> None:
    """A guard that cannot observe must not be read as having observed nothing.

    An empty return is indistinguishable from a clean run, so a git failure would
    manufacture evidence of compliance — which is worse than no guard, because
    the run then reports success with a boundary nobody checked.
    """
    with pytest.raises(RuntimeError, match="could not read the worktree state"):
        act.worktree_state(tmp_path)


# --- the repo-vs-worktree census ---------------------------------------------
#
# THE CLASS: a run reads and writes inside its WORKTREE, and every path it hands
# a model must be anchored there. `repo_root` arrives because that is where the
# paths are configured, and a call that keeps it reads the MAIN CHECKOUT — a
# real tree, present, populated, and not the one the run is working in. Nothing
# raises; the enumeration is simply of somebody else's files.
#
# Both workflows shipped exactly that, one line apart from their correct
# neighbours: `existing_work(repo_root, research_dir)` sitting beside
# `direction_ceiling(worktree / rel_research)`. `plan-sprint`'s instance was the
# expensive one — it runs THIRD, after the parent has written a new component's
# `synthesis.md` into the worktree, and its Stage 1 is told to read every
# synthesis the enumeration lists.
#
# So the check is not "call `existing_work` correctly". It is: every use of
# `repo_root` inside a `run_*` entrypoint is declared here with a reason, and a
# new one fails until somebody writes down why the repo is the right tree.

_REPO_ROOT_USES = {
    # callee -> why the REPO, not the worktree, is correct here
    "relative_to": "makes a configured path relative; the repo IS the anchor "
                   "being removed, and the result is re-rooted at the worktree",
    "run_claude": "the launcher needs both — the repo for git/gh identity and "
                  "the worktree for the model's cwd — and takes them separately",
}


def _run_entrypoints():
    """Every `run_*` function in a discovered workflow, with its module path."""
    import ast

    from observer_registry import workflows_declaring

    out = []
    for mod, _prompt, name in workflows_declaring("DISAPPEARANCE_OBSERVERS"):
        path = Path(mod.__file__)
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and node.name.startswith("run_"):
                out.append((name, path, node))
    return out


def test_the_repo_root_census_finds_the_entrypoints_it_is_meant_to() -> None:
    """POSITIVE CONTROL. A census over zero functions declares everything clean."""
    found = {name for name, _p, _n in _run_entrypoints()}
    assert found == {"triage-candidates", "plan-sprint", "plan-draft",
                     "plan-refine"}, (
        f"the census found run_* entrypoints in {sorted(found)}; if a workflow "
        f"dropped out, its repo-rooted reads stopped being checked")


def test_every_use_of_repo_root_in_a_run_ENTRYPOINT_is_declared() -> None:
    """A repo-rooted read inside a worktree-scoped run, caught by class.

    Undeclared does not mean wrong — it means nobody has said why the repo is
    the right tree for it. Writing the reason into `_REPO_ROOT_USES` is the
    whole remedy, and it is the moment the question gets asked at all.
    """
    import ast

    undeclared: list[str] = []
    for name, path, fn in _run_entrypoints():
        if "repo_root" not in {a.arg for a in fn.args.args + fn.args.kwonlyargs}:
            continue
        for call in (c for c in ast.walk(fn) if isinstance(c, ast.Call)):
            passes_repo_root = any(
                isinstance(a, ast.Name) and a.id == "repo_root"
                for a in call.args
            ) or any(
                isinstance(k.value, ast.Name) and k.value.id == "repo_root"
                for k in call.keywords
            )
            if not passes_repo_root:
                continue
            callee = (call.func.attr if isinstance(call.func, ast.Attribute)
                      else getattr(call.func, "id", "<expr>"))
            if callee not in _REPO_ROOT_USES:
                undeclared.append(f"{name}: {path.name}:{call.lineno} "
                                  f"{callee}(… repo_root …)")

    assert not undeclared, (
        "these calls hand `repo_root` to something inside a worktree-scoped "
        "run, and no reason is recorded:\n  " + "\n  ".join(undeclared) +
        "\n\nA run reads and writes inside its WORKTREE. A read anchored at the "
        "repo returns the main checkout — real, populated, and not the tree the "
        "run is working in — so nothing raises and the model is handed somebody "
        "else's files. If the repo genuinely is the right tree here, add the "
        "callee to `_REPO_ROOT_USES` with the reason; that entry IS the "
        "decision. Otherwise pass `worktree`, or `worktree / rel_<thing>`."
    )


# --- the entrypoints' zero-spend path, EXECUTED ------------------------------
#
# THE CLASS: each kickoff script rebuilds the prompt's values dict inline for
# `--dry-run`, separately from the workflow that builds it for a live run. Two
# constructions of one dict drift, and the drift is invisible to every static
# check: a key added to the workflow and not the script renders a preview no
# model would receive, and a signature change raises a TypeError the CLI's
# `except (RuntimeError, FileNotFoundError, ValueError)` does not catch — the
# operator gets a traceback out of the one command that exists to cost nothing.
#
# BOTH HALVES OF THIS PR'S FAMILY HAVE ALREADY PAID FOR IT. `correction_note`
# exists as a function because `--dry-run` rendered half that slot; `review-pr`
# shipped a broken dry-run for a whole phase behind green static checks, and
# `test_the_review_pr_dry_run_renders_the_real_prompt` is the precedent these
# two are modelled on. Executing the path is the only thing that sees it.

def _fixture_repo(tmp_path: Path) -> Path:
    """The minimum tree both entrypoints check for before rendering anything.

    A REAL `git init`, so that `preflight` runs rather than being stubbed out.
    These two tests used to `monkeypatch.setattr(kickoff, "preflight", ...)`,
    which worked while each runner imported the function into its own namespace
    and broke the moment the resolution moved inside `RepoPathParser`. Stubbing
    it was never the point — the point is a tree the entrypoints can render
    against — and one `git init` buys the real path, which is the one that now
    also resolves every declared operator path.
    """
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    research = tmp_path / "standards" / "architecture" / "research"
    research.mkdir(parents=True)
    # `plan-sprint` takes a COMPONENT since 2026-08-19 and reads its roadmap for
    # the phase estimates, so the fixture repo needs one for its dry run to
    # render. `triage-candidates` ignores it.
    comp = tmp_path / "development" / "alpha"
    comp.mkdir(parents=True, exist_ok=True)
    (comp / "roadmap.md").write_text("### Phase 1 — a thing\n\n**Est: ~4 hours**\n")
    # THE STORE IS ROOT-RELATIVE, not under the research tree — that is what
    # makes one implementation work in every repo that adopts the contract
    # (Tracked Items §1), and it is where the runners now default.
    _render(tmp_path / "tracked" / "candidates",
            _table([("C-d1uhacwn", "`ship`"), ("C-p5qvm3e7", "")]))
    (tmp_path / "development").mkdir(parents=True, exist_ok=True)
    # the successor layout too — runner defaults name `development/sprints.md`,
    # which is what MDC and skyynet-master-planning both use.
    (tmp_path / "development").mkdir(parents=True, exist_ok=True)
    (tmp_path / "development" / "sprints.md").write_text("# Sprints\n")
    (tmp_path / "development" / "sprint.md").write_text("# Sprint\n")
    # `--research` defaults to the successor's depth since the consolidation.
    (tmp_path / "standards" / "architecture" / "research").mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.mark.parametrize("module_name", ["run_triage_candidates", "run_plan_sprint"])
def test_the_dry_run_of_each_entrypoint_RUNS_and_renders(
        module_name: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Executed, not read. A values dict that has drifted raises here and only here.

    `act.render` fails loud on any unsubstituted `${NAME}`, so a key the
    workflow supplies and the script does not is a `ValueError` the moment this
    runs — and a key the script supplies with the wrong arity is a `TypeError`
    before that. Neither is visible in the source of either file.

    `existing_work` is stubbed at its boundary for the reason the module's other
    stubs are: it shells out to `gh`, and a unit test that reached the network
    would fail for a reason having nothing to do with the property here.
    """
    import importlib
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    kickoff = importlib.import_module(module_name)

    repo = _fixture_repo(tmp_path)
    monkeypatch.setattr(kickoff.act, "existing_work", lambda *a, **k: "<work>")

    argv = ["--repo", str(repo), "--dry-run"]
    if module_name == "run_plan_sprint":
        # `plan-sprint` gained a required positional on 2026-08-19: it acts on
        # ONE planned component now, where it used to walk the candidate table.
        argv.insert(0, "development/alpha")
    assert kickoff.main(argv) == 0


@pytest.mark.parametrize("module_name", ["run_triage_candidates", "run_plan_sprint"])
def test_the_dry_run_would_FAIL_on_a_values_dict_that_had_drifted(
        module_name: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
        capsys: pytest.CaptureFixture[str]) -> None:
    """POSITIVE CONTROL on the test above, which otherwise proves only that it ran.

    A prompt gains a placeholder the script's inline dict does not supply — the
    exact drift shape — and the run must come back NON-ZERO naming it, rather
    than printing a preview with a literal `${…}` in it. Without this,
    `main() == 0` above would keep passing if `render`'s leftover guard were
    ever loosened, and would be attesting only that the function returned.

    The exit code is asserted alongside the message because a dry run is a
    scripted command: a caller reads `$?`, not stderr.
    """
    import importlib
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    kickoff = importlib.import_module(module_name)

    repo = _fixture_repo(tmp_path)
    monkeypatch.setattr(kickoff.act, "existing_work", lambda *a, **k: "<work>")
    monkeypatch.setattr(kickoff.act, "load_prompt",
                        lambda p: "${A_SLOT_THE_SCRIPT_DOES_NOT_SUPPLY}")

    argv = ["--repo", str(repo), "--dry-run"]
    if module_name == "run_plan_sprint":
        argv.insert(0, "development/alpha")   # required positional since 2026-08-19
    assert kickoff.main(argv) == 1, (
        "a prompt slot the script does not supply rendered anyway — the dry "
        "run reported success over a preview no model would ever receive")
    assert "A_SLOT_THE_SCRIPT_DOES_NOT_SUPPLY" in capsys.readouterr().err, (
        "the run failed without naming the missing slot, so the operator "
        "cannot tell a drifted values dict from any other error")

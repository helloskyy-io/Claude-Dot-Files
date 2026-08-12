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
from pathlib import Path

import pytest

from modules.assistant.plan import plan_activities as act
from modules.assistant.plan.plan_sprint import plan_sprint_activities as sprint_act
from modules.assistant.plan.plan_sprint import plan_sprint_workflow as sprint
from modules.assistant.plan.triage_candidates import triage_candidates_activities as triage_act
from modules.assistant.plan.triage_candidates import triage_candidates_workflow as triage

PR_URL = "https://github.com/o/r/pull/43"

_HEADER = (
    "| ID | Candidate | Source | `decision` | `status` | Note |\n"
    "|---|---|---|---|---|---|\n"
)


def _table(rows: list[tuple[str, ...]], note: str = "n") -> str:
    """A candidates file holding exactly `rows` as (id, decision[, status]) tuples.

    `status` defaults to `` `open` `` because that is what every row in the real
    file carries while its work is outstanding; the tests that care about the
    status guard pass the third element explicitly.
    """
    body = "".join(
        f"| {row[0]} | a candidate | PR #1 | {row[1]} | {row[2] if len(row) > 2 else '`open`'} | {note} |\n"
        for row in rows)
    return "# Action candidates\n\n" + _HEADER + body


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """A repo-shaped tmp dir that is BOTH repo_root and worktree.

    The workflows compute `candidates_path.relative_to(repo_root)` and then
    re-root it under the worktree; passing the same path for both keeps that
    arithmetic honest without building two trees.
    """
    (tmp_path / "docs" / "development").mkdir(parents=True)
    (tmp_path / "r" / "raw").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def stub_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """Silence the helpers that shell out or walk the real tree.

    `existing_work` runs `gh` and iterates `docs/development/`; `direction_ceiling`
    reads a file; `sprint_files_touched` runs `git` and the fixture tree is not a
    repository. None of them is what any assertion here is about, and
    `existing_work` making a live subprocess call would put a network dependency
    in a unit test.

    `sprint_files_touched` is stubbed to the CLEAN answer, so the tests that care
    about that guard are the ones that override it — a fixture that returned a
    violation would make every other test in the module fail for the wrong reason.
    """
    monkeypatch.setattr(sprint.act, "existing_work", lambda *a, **k: "<work>")
    monkeypatch.setattr(triage.act, "existing_work", lambda *a, **k: "<work>")
    monkeypatch.setattr(triage.own, "direction_ceiling", lambda *a, **k: "<ceiling>")
    monkeypatch.setattr(triage.own, "sprint_files_touched", lambda *a, **k: [])


def _fake_run(module, monkeypatch: pytest.MonkeyPatch, *, writes: str | None = None,
              path: Path | None = None, output: str = f"done\n{PR_URL}\n"):
    """Stand in for the model: optionally rewrite the candidates file, then answer.

    Rewriting the file is how a real run offends — it edits `candidates.md` in
    the worktree — so the fake offends the same way rather than by patching the
    guard's inputs.
    """
    def run(prompt: str, **kw: object) -> str:
        if writes is not None and path is not None:
            path.write_text(writes)
        return output
    monkeypatch.setattr(module.act, "run_claude", run)


# --- `candidate_decisions`: the reader the guard is built on ------------------

def test_it_reads_a_ruling_per_row(tree: Path) -> None:
    f = tree / "c.md"
    f.write_text(_table([("C-001", "`ship`"), ("C-002", "reject"), ("C-003", "")]))
    assert sprint_act.candidate_decisions(f) == {
        "C-001": "ship", "C-002": "reject", "C-003": ""}


@pytest.mark.parametrize("spelling", ["", " ", "—", "-", "  —  "])
def test_every_spelling_of_UNRULED_reads_as_the_same_thing(tree: Path, spelling: str) -> None:
    """`—` and `` and `-` are one state, and the guard must not see three.

    Were they distinct, a run that tidied an em-dash to an empty cell would be
    reported as having overturned a ruling — a false accusation that fails a
    completed run.
    """
    f = tree / "c.md"
    f.write_text(_table([("C-001", spelling)]))
    assert sprint_act.candidate_decisions(f) == {"C-001": ""}


def test_MARKUP_is_not_MEANING(tree: Path) -> None:
    """DISCRIMINATOR. The comparison is on the ruling, never on how it is typeset.

    A run that reformats `` `ship` `` to `ship` has changed nothing and must not
    fail; a run that changes `ship` to `reject` has changed everything and must.
    Without this pair the normalisation could be dropped entirely and every other
    assertion here would still pass.
    """
    f = tree / "c.md"
    f.write_text(_table([("C-001", "`ship`")]))
    typeset = sprint_act.candidate_decisions(f)
    f.write_text(_table([("C-001", "ship")]))
    assert sprint_act.candidate_decisions(f) == typeset
    f.write_text(_table([("C-001", "reject")]))
    assert sprint_act.candidate_decisions(f) != typeset


def test_a_missing_file_says_so_rather_than_reading_as_empty(tree: Path) -> None:
    """An empty dict from a missing file would make the guard pass vacuously."""
    with pytest.raises(FileNotFoundError, match="candidates file not found"):
        sprint_act.candidate_decisions(tree / "nope.md")


# --- the transferred authority, enforced --------------------------------------
#
# PREDICTED BEFORE RUNNING: of the six mutation shapes below, FOUR must raise
# (a ruling rewritten, a blank filled in, a row deleted, a row appended already
# ruled) and TWO must not (markup reformatted, a proposal appended unruled).
# Observed: 4 and 2. The two exemptions are the discriminating half — a guard
# that simply diffed the two id-to-decision maps would go red on all six, and
# would have been indistinguishable from a correct one against the four.

_ORIGINAL = [("C-001", "`ship`"), ("C-002", "`reject`"), ("C-003", "")]

_OFFENCES = [
    pytest.param([("C-001", "`reject`"), ("C-002", "`reject`"), ("C-003", "")],
                 id="a-ruling-was-rewritten"),
    pytest.param([("C-001", "`ship`"), ("C-002", "`reject`"), ("C-003", "`ship`")],
                 id="a-blank-was-filled-in"),
    pytest.param([("C-001", "`ship`"), ("C-002", "`reject`")],
                 id="a-row-was-deleted"),
    pytest.param([("C-001", "`ship`"), ("C-002", "`reject`"), ("C-003", ""),
                  ("C-004", "`ship`")],
                 id="a-new-row-arrived-already-ruled"),
]

_PERMITTED = [
    pytest.param([("C-001", "ship"), ("C-002", "reject"), ("C-003", "—")],
                 id="markup-only-reformat"),
    pytest.param([("C-001", "`ship`"), ("C-002", "`reject`"), ("C-003", ""),
                  ("C-004", "")],
                 id="a-proposal-was-placed-unruled"),
]


def _run_sprint(tree: Path) -> str:
    return sprint.run_plan_sprint(
        repo_root=tree, worktree=tree, sprint_path=tree / "sprint.md",
        candidates_path=tree / "c.md", research_dir=tree / "r", verbose=False,
    )


@pytest.mark.parametrize("mutated", _OFFENCES)
def test_plan_sprint_FAILS_when_it_touched_the_decision_column(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch,
        mutated: list) -> None:
    """THE AUTHORITY TRANSFER, AS A MECHANISM.

    Nine documents now say `decision` is `triage-candidates`'s. This is the only
    thing that makes that true of a run rather than of a paragraph.
    """
    f = tree / "c.md"
    f.write_text(_table(_ORIGINAL))
    _fake_run(sprint, monkeypatch, writes=_table(mutated), path=f)

    with pytest.raises(RuntimeError, match="changed the `decision` column"):
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
    f = tree / "c.md"
    f.write_text(_table(_ORIGINAL))
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
    f = tree / "c.md"
    f.write_text(_table([("C-001", "`ship`"), ("C-002", ""), ("C-003", "")]))
    _fake_run(sprint, monkeypatch)

    assert _run_sprint(tree) == PR_URL


def test_plan_sprint_still_fails_when_it_produced_no_PR(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """The decision guard must not have displaced the completion contract.

    Ordering matters: the URL is extracted first, so an early-stopped run is
    reported as an early-stopped run rather than as a clean one that happened to
    change no rulings.
    """
    (tree / "c.md").write_text(_table(_ORIGINAL))
    _fake_run(sprint, monkeypatch, output="I stopped early\n")

    with pytest.raises(RuntimeError, match="produced no PR URL"):
        _run_sprint(tree)


# --- triage keeps the contract it took ----------------------------------------

def _run_triage(tree: Path) -> str:
    return triage.run_triage_candidates(
        repo_root=tree, worktree=tree, candidates_path=tree / "c.md",
        research_dir=tree / "r", verbose=False,
    )


def test_triage_FAILS_when_it_left_a_row_unruled(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """A partial triage that reports as complete is the failure worth catching.

    The PR reads as ruled and is not, and the untriaged rows stay invisible until
    the next research cycle re-proposes them.
    """
    f = tree / "c.md"
    f.write_text(_table([("C-001", ""), ("C-002", ""), ("C-003", "")]))
    _fake_run(triage, monkeypatch, writes=_table(
        [("C-001", "`ship`"), ("C-002", ""), ("C-003", "")]), path=f)

    with pytest.raises(RuntimeError, match="left 2 of 3 candidates untriaged"):
        _run_triage(tree)


def test_triage_passes_when_every_row_reached_a_disposition(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Negative control: the contract above must not fail a complete pass."""
    f = tree / "c.md"
    f.write_text(_table([("C-001", ""), ("C-002", "")]))
    _fake_run(triage, monkeypatch, writes=_table(
        [("C-001", "`ship`"), ("C-002", "`requires review`")]), path=f)

    assert _run_triage(tree) == PR_URL


def test_triage_names_the_rows_it_failed_on(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """An operator cannot act on a count. The ids have to be in the message."""
    f = tree / "c.md"
    f.write_text(_table([("C-001", ""), ("C-007", "")]))
    _fake_run(triage, monkeypatch, writes=_table(
        [("C-001", "`ship`"), ("C-007", "")]), path=f)

    with pytest.raises(RuntimeError, match="C-007"):
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
        {"total": 5, "untriaged": 2, "triaged": 3, "untriaged_ids": ["C-001", "C-002"]})
    assert "C-001" in full and "C-002" in full
    assert "REVISE" not in full


def test_plan_sprint_is_told_the_untriaged_rows_are_NOT_ITS_JOB() -> None:
    """A model reading blank cells in a column it is reading will fill them.

    Standalone, this workflow meets files triage has not run against. The note has
    to name the rows AND refuse them; naming them alone reads as a work list.
    """
    note = sprint._untriaged_note(
        {"total": 3, "untriaged": 1, "triaged": 2, "untriaged_ids": ["C-009"]})
    assert "C-009" in note
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
    assert "decision` column belongs to `triage-candidates" in text


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
    f = tree / "c.md"
    f.write_text(_table([("C-001", "")]))
    _fake_run(triage, monkeypatch, writes=_table([("C-001", "`ship`")]), path=f)
    monkeypatch.setattr(triage.own, "sprint_files_touched",
                        lambda *a, **k: ["docs/development/sprint.md"])

    with pytest.raises(RuntimeError, match="edited the sprint plan"):
        _run_triage(tree)


@pytest.mark.parametrize("workflow,runner", [(sprint, _run_sprint), (triage, _run_triage)],
                         ids=["plan_sprint", "triage"])
def test_NEITHER_workflow_may_move_the_status_column(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch,
        workflow, runner) -> None:
    """`decision` MOVED between the two; `status` moved nowhere, because it was
    never either one's.

    `candidates.md` gives it to "a later process" — `plan-feature`, or the build
    that completes the item — and both prompts list it under MAY NOT. Ruling a
    candidate is not doing it, and placing one is not finishing it. Without this,
    the split enforced one of the two columns it names and trusted prose for the
    other.
    """
    f = tree / "c.md"
    f.write_text(_table([("C-001", "`ship`", "`open`")]))
    _fake_run(workflow, monkeypatch,
              writes=_table([("C-001", "`ship`", "`closed`")]), path=f)

    with pytest.raises(RuntimeError, match="changed the `status` column"):
        runner(tree)


def test_a_row_APPENDED_with_a_status_is_not_a_status_the_run_moved(
        tree: Path, stub_context: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """NEGATIVE CONTROL, and it is the same exemption the decision guard needed.

    `decision_log_and_reflection.md` tells every producing run to place a proposal
    it surfaced with `status: open`. Judging new rows would make that shared
    instruction unfollowable — the run would obey one of its own rules and fail
    another. Only a row that already existed can have had its status MOVED.
    """
    f = tree / "c.md"
    f.write_text(_table([("C-001", "`ship`", "`open`")]))
    _fake_run(sprint, monkeypatch, writes=_table(
        [("C-001", "`ship`", "`open`"), ("C-002", "", "`open`")]), path=f)

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
    f = tree / "c.md"
    for spelling in ("` — `", "`  `", "` `", "—", "`—`", " - ", "``", "`  —  `"):
        f.write_text(_table([("C-001", spelling)]))
        assert act.candidate_counts(f)["untriaged_ids"] == ["C-001"], (
            f"candidate_counts read {spelling!r} as RULED. `triage-candidates`'s "
            f"working set and its completion post-condition are both built on this "
            f"count, so the row would never be offered for triage and the run would "
            f"still report a complete pass."
        )
        assert sprint_act.candidate_decisions(f)["C-001"] == "", (
            f"candidate_decisions read {spelling!r} as a ruling. plan-sprint's guard "
            f"compares this before and after, so a run that merely tidied the cell "
            f"would be failed for overturning a ruling that was never there."
        )


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
    assert "CORRECTION PASS" in correction and "Counted in code" not in correction

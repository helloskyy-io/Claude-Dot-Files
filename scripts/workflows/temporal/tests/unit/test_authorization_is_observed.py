"""Every `You MAY NOT` row names the code that observes it, or says why nothing can.

THE CLASS, NOT THE ROW THAT HAPPENED TO BE FOUND. The triage split built a real
mechanism for two prohibitions — the `decision` column and the sprint file — and
left the rest of both authorization tables on prose. One of those, `status` on a
`direction.md` row, was the OPERATOR'S OWN RULING, and the prompt asserted it was
enforced: *"Both of those are enforced, not requested … the `status` column is
compared against what it held before you started"*, sitting directly under a table
listing two distinct `status` columns. A review pass found that row. The rows
either side of it — phase docs, the standards tree, a ticked checkbox, a deleted
candidate row — were in exactly the same state and nothing would have found them.

WHY A PROMPT'S FALSE ENFORCEMENT CLAIM IS WORSE THAN SILENCE. A prohibition a
model is told is checked buys compliance on the strength of the claim. When the
claim is false the compliance is unearned, and the failure is invisible: the run
is green, the PR looks ruled, and in `direction.md`'s case `/standup` then rotates
the row out and deletes the receipt.

WHAT THIS TEST KEYS ON. Not the rows that were found — the CORRESPONDENCE between
the rendered table and a map each workflow declares. Reword a row and the key
stops matching; add a row and it has no entry at all. Either way the suite goes
red until somebody answers *"what observes this?"* — and `JUDGEMENT`, with a
reason, is a legitimate answer. It is the difference between "nothing checks
this" being a decision and being an oversight.

THE BEHAVIOURAL HALF LIVES IN `test_triage_candidates_split.py`, beside the
guards themselves: this module proves every prohibition is CLAIMED by a
mechanism and that the mechanism EXISTS; that one proves it fires.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import NamedTuple

import pytest

from observer_registry import names_code, unresolved, workflows_declaring

from assembled_prompt import assembled
from modules.assistant.plan import plan_activities as act
# Still imported BY NAME below: the three boundary tests at the bottom assert
# about these two workflows' specific grant tuples, which is a claim about them
# rather than about the class, and naming them is the honest way to say so.
from modules.assistant.plan.plan_sprint import plan_sprint_workflow as sprint
from modules.assistant.plan.triage_candidates import triage_candidates_workflow as triage

# DISCOVERED, NOT LISTED. This was a hardcoded `[triage, sprint]`, which put the
# universe of checked workflows back on somebody remembering to widen it — the
# same failure this module exists to close, one altitude up. A third workflow
# growing a `You MAY NOT` table now inherits every assertion below without
# anyone touching this file; `plan_activities.py`'s docstring already names the
# next one coming.
WORKFLOWS = [pytest.param(mod, prompt, id=name)
             for mod, prompt, name in workflows_declaring("MAY_NOT_OBSERVERS")]


def may_not_rows(prompt_text: str) -> list[str]:
    """The right-hand column of the `You MAY | You MAY NOT` table, verbatim.

    Reads the RENDERED prohibition rather than a restatement of it, because a
    restatement is the thing that drifts. The table is found by its header, so a
    table moved elsewhere in the prompt is still read and a table DELETED yields
    an empty list — which `test_the_parser_finds_a_table_at_all` turns into a
    failure instead of a silent pass.
    """
    rows: list[str] = []
    inside = False
    for line in prompt_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            inside = False
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) == 2 and cells[0] == "You MAY" and cells[1] == "You MAY NOT":
            inside = True
            continue
        if not inside:
            continue
        if set("".join(cells)) <= set("-: "):        # the header separator
            continue
        if len(cells) >= 2 and cells[1]:
            rows.append(cells[1])
    return rows


def _prompt(mod, name: str) -> str:
    """THE ASSEMBLED PROMPT, NOT THE FILE — the model never reads the file.

    This was `read_text()`, and it went wrong the moment a block it sweeps for
    was PROMOTED to a shared fragment. `plan_draft.md` and `plan_verify.md`
    still promise a completeness list; the opening anchor now arrives through
    `${WORKTREE_IS_COMPARED_TO_A_SNAPSHOT}` instead of sitting in the file. A
    file-level read sees the promise, misses the list, and drops both prompts
    out of the population — so the sweep reports that their promise "is no
    longer read by anything", which is a true sentence about the guard and a
    false one about the prompt.

    Found by merging this branch with the promotion that caused it, which is
    the only place the two halves meet: each side is green alone.
    """
    return assembled(mod.PROMPTS / name)


# --- the correspondence itself ----------------------------------------------

def test_the_workflow_sweep_finds_the_tables_it_is_meant_to() -> None:
    """POSITIVE CONTROL on the DISCOVERY, not on any one workflow's table.

    Every parametrised assertion below runs once per discovered workflow, so a
    sweep that found nothing would collect zero tests and report green — the
    exact shape of a check that stopped checking. This names today's two, so
    losing one is a failure rather than a smaller run. A THIRD workflow arriving
    is expected to fail here once, deliberately: the fix is to add its id, which
    is the moment somebody confirms its table is now covered.
    """
    found = {p.id for p in WORKFLOWS}
    assert found == {"triage-candidates", "plan-sprint", "plan-draft",
                     "plan-verify"}, (
        f"the MAY_NOT_OBSERVERS sweep found {sorted(found)}. If a workflow "
        f"vanished, this module is silently no longer checking its "
        f"authorization table; if one appeared, add its id here to confirm it "
        f"is genuinely covered rather than merely collected.")


@pytest.mark.parametrize("mod,prompt_name", WORKFLOWS)
def test_the_parser_finds_a_table_at_all(mod, prompt_name: str) -> None:
    """POSITIVE CONTROL on the parser, against its own vacuity.

    Every assertion below compares two sets. A parser that matched nothing would
    make one of them empty, and an empty-vs-empty comparison passes over a table
    whose every row is unobserved — which reads identically to full coverage.
    """
    rows = may_not_rows(_prompt(mod, prompt_name))
    assert len(rows) >= 5, (
        f"{prompt_name}: parsed {len(rows)} MAY NOT rows. The table is found by "
        f"its `| You MAY | You MAY NOT |` header; if that header changed, this "
        f"whole module is checking nothing.")


def test_the_parser_would_see_a_newly_added_row() -> None:
    """POSITIVE CONTROL on the property this test exists to enforce.

    The failure mode being prevented is a new prohibition arriving with no
    observer. That only fails the suite if the parser SEES the new row, so the
    parser is shown a synthetic table carrying one.
    """
    table = ("| You MAY | You MAY NOT |\n"
             "|---|---|\n"
             "| Do the job | Set `status` |\n"
             "| | Delete the whole file |\n")
    assert may_not_rows(table) == ["Set `status`", "Delete the whole file"]


@pytest.mark.parametrize("mod,prompt_name", WORKFLOWS)
def test_every_prohibition_in_the_prompt_has_an_entry(mod, prompt_name: str) -> None:
    rows = may_not_rows(_prompt(mod, prompt_name))
    missing = [r for r in rows if r not in mod.MAY_NOT_OBSERVERS]
    assert not missing, (
        f"{prompt_name} forbids something nothing is registered against:\n  "
        + "\n  ".join(repr(r) for r in missing)
        + f"\n\nAdd each to {mod.__name__}.MAY_NOT_OBSERVERS naming the code that "
          f"observes it — or `JUDGEMENT` with the reason no artifact can. A "
          f"prohibition the prompt states and nothing checks is the defect this "
          f"test exists for, and the prompt tells the model both are enforced.")


@pytest.mark.parametrize("mod,prompt_name", WORKFLOWS)
def test_no_entry_describes_a_prohibition_that_is_gone(mod, prompt_name: str) -> None:
    """A stale entry is not harmless — it is a mechanism guarding nothing.

    Kept as a separate assertion from the one above so a failure says which
    direction the drift went. A row removed from the table while its guard stays
    wired is dead code that reads as coverage.
    """
    rows = set(may_not_rows(_prompt(mod, prompt_name)))
    orphaned = [k for k in mod.MAY_NOT_OBSERVERS if k not in rows]
    assert not orphaned, (
        f"{mod.__name__}.MAY_NOT_OBSERVERS registers rows {prompt_name} no longer "
        f"has:\n  " + "\n  ".join(repr(k) for k in orphaned)
        + "\n\nEither the row was reworded — in which case re-answer 'what "
          "observes this?' for the new wording rather than renaming the key — or "
          "it was dropped, in which case remove the mechanism too.")


@pytest.mark.parametrize("mod,prompt_name", WORKFLOWS)
def test_no_row_is_listed_twice(mod, prompt_name: str) -> None:
    """Two identical rows would collapse to one key and hide one prohibition."""
    rows = may_not_rows(_prompt(mod, prompt_name))
    dupes = {r for r in rows if rows.count(r) > 1}
    assert not dupes, f"{prompt_name} repeats {dupes}; one key would cover both"


# --- the mechanisms named must EXIST ----------------------------------------

@pytest.mark.parametrize("mod,prompt_name", WORKFLOWS)
def test_every_named_mechanism_resolves(mod, prompt_name: str) -> None:
    """An entry naming a function that does not exist is worse than a blank one.

    This is the attestation failure the registry is otherwise wide open to:
    writing `act.some_guard` next to a row costs one line and looks exactly like
    coverage. Every `act.` / `own.` reference is resolved against the module the
    workflow actually imports, and every module-level symbol against the
    workflow module itself — through `observer_registry`, which is shared with
    the disappearance registry so the two resolvers cannot drift apart.
    """
    missing = [f"{row!r} -> {sym}"
               for row, mechanism in mod.MAY_NOT_OBSERVERS.items()
               if not mechanism.startswith("JUDGEMENT")
               for sym in unresolved(mod, mechanism)]
    assert not missing, (
        f"{mod.__name__} names mechanisms that do not exist:\n  "
        + "\n  ".join(missing))


@pytest.mark.parametrize("mod,prompt_name", WORKFLOWS)
def test_every_mechanism_is_named_or_the_judgement_is_reasoned(mod, prompt_name: str) -> None:
    """`JUDGEMENT` must say WHY, and a non-judgement entry must name something.

    Without this, `JUDGEMENT` becomes the cheapest exit from every row and the
    registry converges on a table of waivers.
    """
    thin: list[str] = []
    for row, mechanism in mod.MAY_NOT_OBSERVERS.items():
        if mechanism.startswith("JUDGEMENT"):
            if len(mechanism) < 80 or "—" not in mechanism:
                thin.append(f"{row!r}: JUDGEMENT with no reason")
        elif not names_code(mechanism):
            thin.append(f"{row!r}: names no code")
    assert not thin, (
        f"{mod.__name__} entries that assert coverage without carrying it:\n  "
        + "\n  ".join(thin))


# --- the path declarations must actually cover what the rows say ------------

def test_triage_forbids_the_files_it_may_not_write_and_permits_the_two_it_must() -> None:
    """The declaration is checked against concrete paths, not read as prose.

    `docs/standards/` is forbidden wholesale and the two files this workflow
    EXISTS to write live inside it, so a missing exception would fail every
    correct run — and an over-broad exception would silently re-open the tree.
    """
    forbidden = ("docs/development/sprint.md",
                 "docs/development/temporal-integration/phase-1.md",
                 "docs/standards/architecture/problem-statement.md",
                 "docs/standards/workflow-scripts.md",
                 # `direction.md` DELETED 2026-08-26 — the second queue for the
                 # `requires review` disposition. It is forbidden now like any
                 # other standards path, with no carve-out, because there is
                 # nothing there to write.
                 "docs/standards/architecture/research/direction.md")
    # AN ITEM IN THE POOL, not the pool directory: `tracked/` is forbidden as a
    # tree and the grant carves back the item files a run actually writes.
    permitted = ("tracked/candidates/C-d1uhacwn.md",)
    for path in forbidden:
        assert act.boundary_crossings({}, {path: "h"}, triage.FORBIDDEN_PATHS,
                                      triage.permitted_paths(Path("tracked/candidates"), Path("docs/standards/architecture/research"))) == [path], (
            f"triage-candidates may edit {path} undetected")
    for path in permitted:
        assert act.boundary_crossings({}, {path: "h"}, triage.FORBIDDEN_PATHS,
                                      triage.permitted_paths(Path("tracked/candidates"), Path("docs/standards/architecture/research"))) == [], (
            f"triage-candidates cannot do its job: {path} is blocked")


def test_plan_sprint_permits_ONLY_its_override() -> None:
    """Its override opens ONE file, which sits among the phase docs it must not touch.

    IT WAS TWO FILES UNTIL 2026-08-19. `candidates.md` was permitted so this run
    could place ruled `ship` rows and append a surfaced proposal, with its columns
    guarded separately — permitting the path without permitting a ruling. The
    placing job left in the rebuild, and the grant left with it: a permission kept
    after its purpose is one nothing needs and everything inherits.

    The proposal instruction it was partly held for is `plan-draft`'s and
    `plan-verify`'s to satisfy — both still hold that grant, and both run before
    this one on the same branch.

    `direction.md` was and remains absent: appending to it is
    `triage-candidates`'s alone.
    """
    rel_sprint = "docs/development/sprint.md"
    allowed = sprint.permitted_paths(rel_sprint)
    assert act.boundary_crossings({}, {rel_sprint: "h"}, sprint.FORBIDDEN_PATHS,
                                  allowed) == [], "plan-sprint blocked from its own override"
    assert act.boundary_crossings(
        {}, {"tracked/candidates/C-d1uhacwn.md": "h"},
        sprint.FORBIDDEN_PATHS, allowed) == [
        "tracked/candidates/C-d1uhacwn.md"], (
        "plan-sprint can still reach the candidates pool — the grant outlived its job")
    for path in ("docs/standards/architecture/research/direction.md",
                 "docs/development/temporal-integration/phase-1.md",
                 "docs/standards/finding-routing.md"):
        assert act.boundary_crossings({}, {path: "h"}, sprint.FORBIDDEN_PATHS,
                                      allowed) == [path], (
            f"plan-sprint may edit {path} undetected")


def test_a_sprint_file_kept_somewhere_else_is_still_the_permitted_one() -> None:
    """`--sprint` moves the plan, so the exception is computed rather than fixed.

    A hard-coded `docs/development/sprint.md` would fail every correct run in a
    repo that keeps its plan elsewhere — and the failure would arrive after the
    PR was already open.
    """
    rel = "planning/current-sprint.md"
    assert act.boundary_crossings({}, {rel: "h"}, sprint.FORBIDDEN_PATHS,
                                  sprint.permitted_paths(rel)) == []


# --- what a guard SAYS when it fires ----------------------------------------
#
# THE SECOND HALF OF "the prohibition is observed": the guard has to hand back
# the value that moved, not merely the row it moved on. Four of the five
# value-comparator guards in this family rendered `id 'before'->'after'`; two did
# not, and the sibling comment on one of them said out loud that it was rendered
# *"`before->after` the way plan-sprint's twin does"* — written by the pass that
# left its own twin, one call above it, naming ids alone. That is the shape this
# correction cycle keeps meeting: a fix applied to one branch of a symmetric
# pair. Enumerating the branches does not converge; asking the question of every
# guard the AST can find does.

_COMPARATOR = "this_run_had_no_right_to"


class _ValueGuard(NamedTuple):
    """One `offender = <comparator>(before, after)` / `if offender: raise` pair.

    NAMED RATHER THAN A BARE TUPLE because the shape grew: `comparator` was added
    on 2026-08-20 for the check below it, and a positional 5-tuple would have
    re-pointed every unpacking site by one — the same failure `CandidateRow`'s
    docstring records, in the file that asserts about it.
    """

    comparator: str
    offender: str
    before: str
    after: str
    raised: str


def _snapshot_readers(tree: ast.Module) -> dict[str, str]:
    """`before_size` -> `candidate_sizes`: which reader produced each snapshot.

    The COLUMN a guard is about is not recoverable from the guard itself — the
    offender variable is named for the offence (`ruled`, `flipped`, `named`) and
    the snapshot variable is named by hand. The reader is the only place the
    column is stated by something that had to be right for the code to work at
    all, so the check below keys on it rather than on any of the three names.
    """
    readers: dict[str, str] = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Call)):
            fn = node.value.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if name:
                readers[node.targets[0].id] = name
    return readers


def _value_guards(mod) -> list[_ValueGuard]:
    """Every value guard in a workflow MODULE — see `_value_guards_in`."""
    return _value_guards_in(Path(mod.__file__).read_text(encoding="utf-8"))


def _value_guards_in(src: str) -> list[_ValueGuard]:
    """Every `offender = <comparator>(before, after)` / `if offender: raise` pair.

    DISCOVERED FROM THE SOURCE, not listed, for the same reason `WORKFLOWS` is:
    a guard added later must inherit the assertion without anybody editing this
    file. The comparator is matched by NAME SUFFIX rather than by an import list
    — `act.statuses_this_run_had_no_right_to`, `own.` anything, and a module-
    private `_rulings_this_run_had_no_right_to` are all the same shape and the
    matcher admits all three. It ADMITS rather than FINDS the third: nothing in
    the tree calls a module-private comparator today, so no guard of that shape
    is in any sweep's result — see `test_no_DOCSTRING_calls_an_UNCALLED_
    comparator_a_LIVE_RULE` for the one that is defined and never called.

    DELETION COMPARATORS ARE DELIBERATELY OUT OF SCOPE. `ids_deleted` and
    `grants_that_vanished` answer *what is GONE*, and there is no after-value to
    render — naming the id alone is the whole of what can be said, so requiring
    an arrow there would demand a lie.
    """
    tree = ast.parse(src)

    pending: dict[str, tuple[str, str, str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        for call in ast.walk(node.value):
            if not isinstance(call, ast.Call):
                continue
            fn = call.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if name.endswith(_COMPARATOR) and len(call.args) == 2:
                pending[ast.unparse(node.targets[0])] = (
                    name, *(ast.unparse(a) for a in call.args))

    guards: list[_ValueGuard] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        offender = ast.unparse(node.test)
        if offender not in pending:
            continue
        comparator, before, after = pending[offender]
        for raised in ast.walk(node):
            if isinstance(raised, ast.Raise):
                guards.append(_ValueGuard(comparator, offender, before, after,
                                          ast.get_source_segment(src, raised) or ""))
    return guards


def test_the_value_guard_sweep_finds_guards_at_all() -> None:
    """POSITIVE CONTROL on the discovery, against its own vacuity.

    The assertion below iterates whatever this finds. An AST walk that matched
    nothing — a renamed comparator, a guard moved inside a helper — would iterate
    an empty list and report green over a family with no diagnostics at all,
    which reads identically to every diagnostic being right.
    """
    found = [g for mod, _, _ in workflows_declaring("MAY_NOT_OBSERVERS")
             for g in _value_guards(mod)]
    assert len(found) >= 4, (
        f"the value-guard sweep found {len(found)} guard(s). The comparators are "
        f"matched by the `{_COMPARATOR}` name suffix; if one was renamed, this "
        f"check is no longer reading the guards it is named for.")


def test_the_GUARDED_COLUMN_LIST_matches_the_comparator_family() -> None:
    """`plan_activities._GUARDED_COLUMNS` must be exactly the guarded columns.

    THE CLASS IS A HAND-KEPT ENUMERATION OF A COLLECTION THAT GREW, and it has
    now produced a finding in three consecutive passes on one branch. When `size`
    became the fourth guarded column, four prose enumerations of the other three
    stayed as they were: `_raise_on_duplicate_ids`' operator message and its
    docstring, `CandidateRow`'s docstring, and `scaffold_candidate_components`'
    skip-condition count. Each was individually correct when written, each went
    stale silently, and each was found by a human reading two files side by side.

    `_GUARDED_COLUMNS` is the single place the list now lives, and this is what
    makes adding a column fail HERE — one assertion, with the fix in one place —
    instead of leaving four sentences that read as coverage. It is the same
    remedy `_CONSTRAINED_CELLS` applied to the cell count in the same module.

    MATCHED BY PREFIX, because the reader and the comparator carry the PLURAL
    (`candidate_statuses`, `statuses_this_run_had_no_right_to`) and English
    plurals are not a function anything here should be computing. A column whose
    plural is not its singular plus a suffix fails this loudly rather than
    passing quietly, which is the correct direction: the message says what to do.
    """
    stems = sorted(n[:-len(_COMPARATOR) - 1] for n in dir(act)
                   if n.endswith(_COMPARATOR) and not n.startswith("_"))
    paired = [s for s in stems if hasattr(act, f"candidate_{s}")]
    unmatched_stems = [s for s in paired
                       if sum(s.startswith(c) for c in act._GUARDED_COLUMNS) != 1]
    unmatched_cols = [c for c in act._GUARDED_COLUMNS
                      if sum(s.startswith(c) for s in paired) != 1]
    assert not unmatched_stems and not unmatched_cols, (
        f"`_GUARDED_COLUMNS` is {list(act._GUARDED_COLUMNS)} and the reader/"
        f"comparator pairs in `plan_activities` are {paired}. Unmatched "
        f"pairs: {unmatched_stems}; unmatched columns: {unmatched_cols}. Every "
        f"column with both a `candidate_<plural>` reader and a "
        f"`<plural>_{_COMPARATOR}` comparator is a guarded column and must be "
        f"named in `_GUARDED_COLUMNS`, because the operator-facing messages "
        f"interpolate that tuple rather than restating the list — a column "
        f"missing from it is a column those messages silently omit.")


def _borrowed_comparators(src: str) -> list[str]:
    """Every guard in this source calling a comparator that is not its column's.

    TAKES SOURCE TEXT RATHER THAN A MODULE so it can be exercised on a snippet
    this tree does not contain — see `test_the_column_rule_SEPARATES_a_borrowed_
    comparator_from_an_own_one`. A predicate reachable only through
    `workflows_declaring` is one whose only evidence is that today's four
    workflows pass it, which is the vacuity `test_a_census_guard_proves_its_own_
    predicate` exists to refuse.
    """
    readers = _snapshot_readers(ast.parse(src))
    offences: list[str] = []
    for guard in _value_guards_in(src):
        snapshots = {readers.get(guard.before), readers.get(guard.after)}
        if len(snapshots) != 1 or None in snapshots:
            offences.append(
                f"{guard.offender} compares {guard.before} to {guard.after}, "
                f"which this sweep cannot trace to one reader "
                f"(saw {sorted(str(r) for r in snapshots)})")
            continue
        reader = snapshots.pop()
        expected = f"{reader.rsplit('_', 1)[-1]}_{_COMPARATOR}"
        if guard.comparator.lstrip("_") != expected:
            offences.append(
                f"{guard.offender} snapshots with `{reader}` and compares with "
                f"`{guard.comparator}`, not `{expected}`")
    return offences


def test_EVERY_value_guard_CALLS_ITS_OWN_COLUMNS_COMPARATOR() -> None:
    """A guard must call the comparator named after the reader it snapshots.

    KEYED ON THE CLASS, NOT ON THE COLUMN THAT WAS WRONG. `decision` rode
    `statuses_this_run_had_no_right_to` in both planning workflows from the day
    the guard was written until 2026-08-20 — the call resolved, the guard fired
    correctly, the raise message named `decision`, and every existing check here
    was green, because none of them ever asked which comparator was on the other
    end. Fixing the two call sites and stopping there would leave the next column
    to be discovered the same way, by a reviewer reading two lines side by side.

    THE CONSEQUENCE IS NOT COSMETIC, and the family's own design is what makes
    it real. `components_this_run_had_no_right_to`'s docstring states that the
    bodies are duplicated rather than shared *"because the two columns are
    prohibited for DIFFERENT reasons and each docstring is the place that reason
    is recorded"* — so a column with no comparator of its own has nowhere to
    record why it is prohibited, and any later specialisation of the comparator
    it borrows silently retargets its guard in every workflow at once.

    THE READER IS THE ORACLE. `before_direction = own.direction_statuses(...)` is
    a guard over `direction.md`'s **`status`** column whose snapshot variable
    names the FILE, so a check keyed on the variable name would have called that
    correct guard an offence. Keyed on the reader, it passes: `direction_
    statuses` -> `statuses` -> `statuses_this_run_had_no_right_to`.
    """
    offenders = [f"{name}: {offence}"
                 for mod, _, name in workflows_declaring("MAY_NOT_OBSERVERS")
                 for offence in _borrowed_comparators(
                     Path(mod.__file__).read_text(encoding="utf-8"))]
    assert not offenders, (
        f"these guards borrow another column's comparator: {offenders}. Each "
        f"column in this family gets its OWN `<column>s_{_COMPARATOR}`, whose "
        f"docstring is the one place its prohibition is explained; a guard "
        f"riding a sibling's comparator has nowhere to record why its column is "
        f"prohibited, and specialising that sibling later retargets this guard "
        f"in every workflow that calls it. Add the comparator beside its three "
        f"siblings in `plan_activities.py` and point the call site at it.")


# --- the column rule, exercised on source this tree does not contain ---------
#
# Three snippets rather than two, and the third is the one that matters: it is
# the shape a naive rule gets WRONG. Keying on the snapshot VARIABLE name looks
# equivalent and would call `triage-candidates`' correct `direction.md` guard an
# offence, because that variable is named for the FILE and the column it guards
# is `status`. A control that only separated the obvious pair would have shipped
# that rule.

_OWN_COMPARATOR = """
def run():
    before_size = act.candidate_sizes(p)
    after_size = act.candidate_sizes(p)
    sized = act.sizes_this_run_had_no_right_to(before_size, after_size)
    if sized:
        raise RuntimeError("no")
"""

_BORROWED_COMPARATOR = """
def run():
    before_size = act.candidate_sizes(p)
    after_size = act.candidate_sizes(p)
    sized = act.statuses_this_run_had_no_right_to(before_size, after_size)
    if sized:
        raise RuntimeError("no")
"""

_READER_NAMED_FOR_THE_FILE = """
def run():
    before_direction = own.direction_statuses(p)
    after_direction = own.direction_statuses(p)
    ruled = act.statuses_this_run_had_no_right_to(before_direction, after_direction)
    if ruled:
        raise RuntimeError("no")
"""


@pytest.mark.parametrize("label,snippet,offends", [
    ("a column calling its own comparator", _OWN_COMPARATOR, False),
    ("a column riding a sibling's comparator", _BORROWED_COMPARATOR, True),
    ("a reader named for the file, not the column", _READER_NAMED_FOR_THE_FILE,
     False),
], ids=["own", "borrowed", "reader-named-for-file"])
def test_the_column_rule_SEPARATES_a_borrowed_comparator_from_an_own_one(
        label: str, snippet: str, offends: bool) -> None:
    """Both answers, on source written for this test alone.

    `_borrowed_comparators` is otherwise reachable only through the four
    workflows `workflows_declaring` finds, all of which pass — so an AST shape
    change that made `_snapshot_readers` return `{}` would silently answer "no
    offences" for every one of them and the rule above would be permanently
    green over exactly the defect it was written for.
    """
    assert bool(_borrowed_comparators(snippet)) is offends, (
        f"{label}: the predicate reported {_borrowed_comparators(snippet)}")


def test_EVERY_value_guard_NAMES_THE_VALUE_THAT_MOVED() -> None:
    """A guard that names only the row hands the operator half the answer.

    KEYED ON THE COMPARATOR, NOT ON THE FIVE GUARDS THAT EXIST TODAY. Each of
    these fires on a column whose wrong value is the thing to undo — an invented
    `component` becomes a committed directory, an invented `direction.md` status
    is a ruling only the operator may make and one `/standup` then rotates the
    receipt away for. "Row C-htg3mh0t changed" sends them back to `git diff` to learn
    what it changed to; `C-htg3mh0t ''->'fleet-reliability'` tells them whether they
    are looking at an invention or a correction, which is the ruling they have to
    make.
    """
    offenders: list[str] = []
    for mod, _, name in workflows_declaring("MAY_NOT_OBSERVERS"):
        for guard in _value_guards(mod):
            if ("->" in guard.raised and guard.before in guard.raised
                    and guard.after in guard.raised):
                continue
            offenders.append(f"{name}:{guard.offender} "
                             f"(comparing {guard.before} to {guard.after})")
    assert not offenders, (
        f"these guards raise without rendering the value that moved: {offenders}. "
        f"Every other guard built on a `{_COMPARATOR}` comparator renders "
        f"`id 'before'->'after'`; one that names ids alone tells the operator "
        f"WHICH row was written and not WHAT was written into it, which is the "
        f"half they need to tell an invention from a correction.")


# --- the prompt's ENFORCEMENT LIST must name every column its table forbids ---
#
# THE SECOND STATEMENT OF THE SAME BOUNDARY, AND THE ONE NOTHING READ. Each of
# these prompts tells the model what is watched TWICE: once as a `You MAY NOT`
# row, and once as a prose list beneath it that promises to be exhaustive. Every
# assertion above this line reads the ROW. When `size` became the fourth guarded
# column, all three rows were widened and all three lists were left saying
# *"All three candidate columns"* / omitting `size` entirely — green, because the
# half the model actually reads to learn what is watched was read by no test at
# all.
#
# WHY THE OMISSION IS A DEFECT AND NOT UNTIDINESS. Each list closes with an
# explicit completeness guarantee — *"One row in that column is NOT mechanically
# checked, and you are told which"* — and names the sole exception. A column
# missing from the list makes that sentence false in the direction that costs
# most: the model learns its `size` prohibition is on the honour system, writes
# the cell, and the guard fails the whole run at its final check. The durable
# harm is worse than the run — a disclosure list that under-claims teaches the
# model to distrust the list, which is the mechanism this repo uses to keep a
# prompt honest about its own coverage.
#
# THE POPULATION IS DECIDED BY THE PROMPT'S OWN TEXT, not by a name list. A
# prompt is in scope because it MAKES the promise, so `plan_sprint.md` — whose
# enforcement claim is one compressed sentence covering its rows by PATH, with no
# per-row completeness guarantee — is out by construction rather than by
# exception. An excluded-by-list workflow is the failure `workflows_declaring`
# was built to close; an excluded-by-predicate one re-enters the moment it starts
# making the promise.

# WHAT THIS GUARD DOES NOT LOOK AT, stated because the rule below is narrower
# than its heading sounds and a scoped control read as a general one is how the
# next member gets missed:
#
#   * **A prohibition that is not a COLUMN.** The key is backticked tokens
#     intersected with `_GUARDED_COLUMNS`, so `plan_draft.md`'s "Estimate
#     hours, or size the work in any unit of time" sits outside it by
#     construction. A REVIEW PASS FOUND EXACTLY THAT MEMBER, one row over from
#     the `size` omission this rule was written for.
#   * **AND WIDENING THE KEY WAS TRIED AND MEASURED VACUOUS**, which is why the
#     scope is recorded here instead of removed. The obvious generalisation --
#     require some content word of each non-`JUDGEMENT` row to appear in the
#     block -- answers OK for all 30 non-judgement rows across the three
#     prompts INCLUDING the omitted hours row, which matches on the incidental
#     words "size" and "work". A key that cannot separate the one known defect
#     from 29 correct rows is a wrong verdict wearing a rule's clothes, and
#     shipping it would have been worse than the gap it papered over. The hours
#     row was closed by fixing the PROMPT, and no key is claimed for that half.
#   * **WHERE the prompt accounts for a row.** The search is the enforcement
#     block alone, deliberately: a column name appearing elsewhere in the prompt
#     proves nothing about the list that promises to enumerate them, which is
#     what `test_the_enforcement_block_is_NOT_EMPTY` exists to keep honest.
#
# What IS closed here beyond the original column rule: the two hand-maintained
# FIGURES this section carried -- the numeral quantifying the column
# enumeration, and the count of rows the closing sentence calls unchecked. Both
# are derivable, both were being remembered, and both now have a rule.

_ENFORCEMENT_OPENS = ("the worktree is read and compared against a snapshot "
                      "taken before you started")

# THE CLOSING PROMISE -- AND THE NUMERAL IS A CAPTURE, NOT PART OF THE ANCHOR.
# This was matched literally as "One row in that column is NOT mechanically
# checked", which welded the extractor to a hand-maintained figure: a prompt
# that CORRECTLY grew to "Two rows" would stop matching, drop out of the
# population, and surface as the sweep below reporting that its promise "is no
# longer read by anything" -- a true sentence pointing at the wrong cause.
# Capturing the numeral lets the rule that actually owns it say so instead.
_ENFORCEMENT_CLOSES = re.compile(
    r"(\w+) rows? in that column (?:is|are) NOT mechanically checked")

_NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                 "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}

_A_NUMERAL = re.compile(
    r"\b(\d+|" + "|".join(_NUMBER_WORDS) + r")\b", re.IGNORECASE)

# A backticked token that could be a column name. Deliberately refuses anything
# with a dot or a slash — `direction.md`, `research/`, `phaseN_<name>.md` are
# files and paths, and a column rule has nothing to say about them.
_BACKTICKED = re.compile(r"`([a-z_]+)`")


def _enforcement_block(prompt_text: str) -> str | None:
    """The prose between "compared against a snapshot" and the completeness promise.

    `None` when the prompt makes no such promise, which is how the population
    below is decided. Both anchors are required: a prompt that opened a list and
    never closed it would otherwise yield everything after the anchor and pass
    on text that is not the list at all.
    """
    start = prompt_text.find(_ENFORCEMENT_OPENS)
    close = _ENFORCEMENT_CLOSES.search(prompt_text)
    if start < 0 or close is None or close.start() <= start:
        return None
    return prompt_text[start:close.start()]


def _columns_forbidden(mod, prompt_text: str) -> dict[str, str]:
    """`size` -> the MAY NOT row that forbids it, for every guarded column.

    KEYED ON THE ROW'S OWN BACKTICKS, intersected with `_GUARDED_COLUMNS`. The
    alternative — deriving columns from the comparators the registry names —
    reads one instance short: `triage-candidates` guards `size` through
    `own.sized_without_shipping`, which is a PAIRING check over one row and not a
    `<column>s_this_run_had_no_right_to` comparator at all. A rule keyed on
    comparators would have called that prompt's omission compliant.

    `JUDGEMENT` rows are skipped because they are the rows the closing sentence
    exists to name as unchecked; requiring the list to claim them would invert
    the property.
    """
    forbidden: dict[str, str] = {}
    for row in may_not_rows(prompt_text):
        if mod.MAY_NOT_OBSERVERS.get(row, "").startswith("JUDGEMENT"):
            continue
        for token in _BACKTICKED.findall(row):
            if token in act._GUARDED_COLUMNS:
                forbidden.setdefault(token, row)
    return forbidden


def _columns_undisclosed(block: str, columns) -> list[str]:
    """Every column the table forbids that the enforcement list never names."""
    return sorted(c for c in columns if f"`{c}`" not in block)


DISCLOSING = [pytest.param(mod, prompt, id=name)
              for mod, prompt, name in workflows_declaring("MAY_NOT_OBSERVERS")
              if _enforcement_block(_prompt(mod, prompt)) is not None]


def test_the_enforcement_BLOCK_sweep_finds_the_prompts_that_PROMISE_one() -> None:
    """POSITIVE CONTROL on the population, not on any one prompt.

    The rule below is parametrised over prompts that carry an enforcement list,
    so a pair of anchors that stopped matching would collect zero tests and
    report green — the shape of a check that stopped checking. `plan-sprint` is
    expected to be ABSENT and that absence is the reasoned one described above;
    if it ever grows an enumerated list with a completeness guarantee, it belongs
    here and this assertion is where somebody notices.
    """
    found = {p.id for p in DISCLOSING}
    assert found == {"plan-draft", "plan-verify", "triage-candidates"}, (
        f"the enforcement-block sweep found {sorted(found)}. If one vanished, "
        f"its prompt's promise is no longer read by anything; if one appeared, "
        f"add its id here to confirm its list is genuinely covered rather than "
        f"merely collected.")


@pytest.mark.parametrize("mod,prompt_name", DISCLOSING)
def test_the_enforcement_block_is_NOT_EMPTY(mod, prompt_name: str) -> None:
    """POSITIVE CONTROL on the extractor, against its own vacuity.

    The rule is a substring search over this block. A block that came back as a
    few characters would answer "undisclosed" for every column and a block that
    came back as the WHOLE PROMPT would answer "disclosed" for every column —
    the second is the silent direction, and it is the one this catches.
    """
    block = _enforcement_block(_prompt(mod, prompt_name))
    assert 500 < len(block) < 6000, (
        f"{prompt_name}: the enforcement block extracted to {len(block)} bytes. "
        f"Too short and the rule below sees no list; too long and it is matching "
        f"the rest of the prompt, where a column name appearing proves nothing.")


@pytest.mark.parametrize("mod,prompt_name", DISCLOSING)
def test_the_enforcement_LIST_NAMES_EVERY_COLUMN_the_TABLE_forbids(
        mod, prompt_name: str) -> None:
    """A prompt that promises an exhaustive list must have one.

    KEYED ON THE TABLE, NOT ON THE COLUMN THAT WAS MISSING. `size` was added to
    all three MAY NOT rows and to none of the three lists, and the same will be
    true of the next column: widening a row is what the registry test above makes
    you do, and nothing made anybody widen the sentence beneath it.
    """
    text = _prompt(mod, prompt_name)
    forbidden = _columns_forbidden(mod, text)
    undisclosed = _columns_undisclosed(_enforcement_block(text), forbidden)
    assert not undisclosed, (
        f"{prompt_name} forbids {undisclosed} in its `You MAY NOT` table and "
        f"never names them in the enforcement list beneath it. The rows are: "
        + "; ".join(repr(forbidden[c]) for c in undisclosed)
        + ". That list closes by promising exactly one row is NOT mechanically "
          "checked and naming which; a guarded column missing from it makes the "
          "promise false and tells the model the column is on the honour system.")


_LIST_NAMING_FOUR = """
When you finish, the worktree is read and compared against a snapshot taken before you started:
- **All four candidate columns** — `decision`, `size`, `status`, `component` —
  are compared cell by cell.
One row in that column is NOT mechanically checked, and you are told which.
"""

_LIST_NAMING_THREE = """
When you finish, the worktree is read and compared against a snapshot taken before you started:
- **All three candidate columns** — `decision`, `status`, `component` — are
  compared cell by cell.
One row in that column is NOT mechanically checked, and you are told which.
"""

_NO_PROMISE_AT_ALL = """
Every path outside `${SPRINT_PATH}` is compared by content.
"""


@pytest.mark.parametrize("label,prompt_body,columns,expected", [
    ("a list naming every guarded column", _LIST_NAMING_FOUR,
     {"decision", "size", "status", "component"}, []),
    ("a list one column short", _LIST_NAMING_THREE,
     {"decision", "size", "status", "component"}, ["size"]),
], ids=["complete", "one-short"])
def test_the_disclosure_rule_SEPARATES_a_complete_list_from_a_short_one(
        label: str, prompt_body: str, columns, expected: list[str]) -> None:
    """Both answers, on prompt text this tree does not contain.

    `_columns_undisclosed` is otherwise reachable only through three live prompts
    that now pass, so a change to the anchors or the backtick spelling would
    answer "nothing undisclosed" for all three and the rule would be permanently
    green over exactly the defect it was written for.
    """
    block = _enforcement_block(prompt_body)
    assert block is not None, f"{label}: the anchors stopped matching"
    assert _columns_undisclosed(block, columns) == expected


def test_a_prompt_making_NO_completeness_promise_is_OUT_OF_POPULATION() -> None:
    """The exclusion is by the prompt's own text, and it has to be demonstrated.

    `plan_sprint.md` covers its rows by PATH in one sentence and guarantees
    nothing about per-row completeness, so a column-keyed rule would report its
    `decision` row as undisclosed — a false positive of the heuristic rather than
    a defect. Asserting the mechanism here, on a snippet, rather than trusting
    that today's `plan_sprint.md` happens to lack the anchors.
    """
    assert _enforcement_block(_NO_PROMISE_AT_ALL) is None


# --- the two FIGURES the enforcement section was remembering -----------------
#
# THE CLASS IS "A PROSE NUMBER ABOUT A POPULATION THE CODE ALREADY DERIVES", and
# this repo has paid for it four times on PR #101 alone. It is gated in four
# corpora already -- `tests/unit/` by
# `test_a_prose_COUNT_of_a_collection_is_DERIVED.py`, the journal package, the
# phase docs, and `candidates.md`. PROMPTS UNDER `modules/` WERE A FIFTH CORPUS
# WITH NO GATE, and the enforcement section carried two members of the class:
#
#   * the numeral quantifying the column enumeration -- "All four candidate
#     columns -- `decision`, `size`, `status`, `component`". True when written.
#     Nothing derives it, and the rules above force the NAME of a fifth column
#     into the block while saying nothing about the count, so the next widening
#     yields "All four candidate columns -- <five names>" in the one artifact
#     whose whole job is telling a model what is watched.
#   * the count in the closing sentence -- "One row in that column is NOT
#     mechanically checked". The registry knows exactly how many rows are
#     `JUDGEMENT`; the sentence remembers it.
#
# BOTH RULES ARE KEYED ON THE POPULATION THE EXTRACTOR ALREADY DEFINES, not on a
# regex over prompt prose. A loose "numeral near a backticked list" sweep was
# measured over all 49 prompts first: it fired on `stages_2_to_4.md`'s "A miss
# has four causes" against an unrelated `set()` one clause away. Scoped to the
# enforcement block, the population is exactly the three disclosing prompts and
# there is nothing to argue about.


def _column_bullets(block: str) -> list[str]:
    """Every bullet in the block that names a guarded column.

    FOUND BY CONTENT, NOT BY WORDING, so the rule cannot be dodged by rewriting
    the sentence it judges. ONE BULLET PER COLUMN IS A LEGITIMATE SHAPE and the
    threshold is deliberately one rather than two: `triage_candidates.md` gives
    `status`, `component` and `size` a bullet each so every column can carry its
    own reason, while the two `plan_*` prompts enumerate all four in one. A rule
    demanding a single enumerating bullet would have called the better-written
    prompt non-compliant -- it did, on the first run of this rule, which is why
    the threshold is stated here rather than assumed.

    DELIBERATELY OVER-INCLUSIVE IN ONE HARMLESS DIRECTION: a bullet that merely
    MENTIONS a guarded column in its body is matched too -- `triage-candidates`'s
    deletion bullet is here because it says "the two `status` comparisons". The
    rule only ever reads the LEAD, so an extra bullet costs nothing and the
    alternative -- deciding which mentions "really" enumerate -- is judgement
    this can do without.
    """
    found = []
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        if any(t in act._GUARDED_COLUMNS for t in _BACKTICKED.findall(stripped)):
            found.append(stripped)
    return found


def _bullet_lead(bullet: str) -> str:
    """The bolded lead phrase — the part that QUANTIFIES what follows.

    Scoped to the lead rather than the whole bullet because the body legitimately
    contains prose that may carry a number; it is the quantifier in front of the
    enumeration that duplicates a derivable count.
    """
    match = re.match(r"-\s*\*\*(.+?)\*\*", bullet)
    return match.group(1) if match else ""


def _stated_unchecked(prompt_text: str) -> int | None:
    """How many rows the closing sentence CLAIMS are not mechanically checked."""
    close = _ENFORCEMENT_CLOSES.search(prompt_text)
    if close is None:
        return None
    return _NUMBER_WORDS.get(close.group(1).lower())


def _judgement_rows(observers: dict[str, str]) -> list[str]:
    """The rows the registry itself says nothing can observe."""
    return sorted(row for row, obs in observers.items()
                  if obs.startswith("JUDGEMENT"))


@pytest.mark.parametrize("mod,prompt_name", DISCLOSING)
def test_the_COLUMN_BULLET_does_not_RESTATE_a_count_it_could_DERIVE(
        mod, prompt_name: str) -> None:
    """The enumeration is right there; quantifying it is a second copy.

    The rules above already force every guarded column's NAME into this bullet.
    A reader — human or model — can count them. A numeral in front of them is a
    figure nothing recomputes, in the artifact that tells a model what is
    watched, and it goes stale on exactly the change the other rules compel.
    """
    restated = [(_bullet_lead(b), _A_NUMERAL.search(_bullet_lead(b)).group(0))
                for b in _column_bullets(_enforcement_block(
                    _prompt(mod, prompt_name)))
                if _A_NUMERAL.search(_bullet_lead(b))]
    assert not restated, (
        f"{prompt_name} leads a column bullet with a count of the very list it "
        f"enumerates: "
        + "; ".join(f"{lead!r} states {num!r}" for lead, num in restated)
        + ". Nothing derives that number. Widening the guarded columns forces "
          "the new NAME into this bullet and leaves the count untouched, so the "
          "next column makes the sentence false in the one artifact whose job "
          "is telling a model what is watched. Say `Every candidate column` and "
          "let the enumeration carry the count.")


@pytest.mark.parametrize("mod,prompt_name", DISCLOSING)
def test_the_CLOSING_PROMISE_counts_the_rows_the_REGISTRY_calls_unchecked(
        mod, prompt_name: str) -> None:
    """"One row is NOT mechanically checked" is a claim the registry can settle.

    THE SILENT DIRECTION IS A SECOND `JUDGEMENT` ROW. Registering one leaves this
    sentence matching, the population intact and every other rule green, while
    the prompt now under-states what is on the honour system — the exact
    direction the enforcement list exists to prevent, arriving through the
    sentence that promises it cannot.
    """
    stated = _stated_unchecked(_prompt(mod, prompt_name))
    judged = _judgement_rows(mod.MAY_NOT_OBSERVERS)
    assert stated is not None, (
        f"{prompt_name}: the closing promise names a quantity this rule cannot "
        f"read. Spell it as a word up to ten, or teach `_NUMBER_WORDS` the "
        f"spelling — an unreadable count is an unchecked one.")
    assert stated == len(judged), (
        f"{prompt_name} promises {stated} row(s) in that column are NOT "
        f"mechanically checked, and its MAY_NOT_OBSERVERS registry marks "
        f"{len(judged)} as JUDGEMENT: {judged}. A prompt claiming FEWER "
        f"unchecked rows than there are tells the model the difference is "
        f"watched when nothing watches it.")


_LEAD_WITH_A_COUNT = "- **All four candidate columns** — `decision`, `size` — x."
_LEAD_WITHOUT_ONE = "- **Every candidate column** — `decision`, `size` — x."


@pytest.mark.parametrize("label,bullet,restates", [
    ("a lead that quantifies the enumeration", _LEAD_WITH_A_COUNT, True),
    ("a lead that lets the list carry it", _LEAD_WITHOUT_ONE, False),
], ids=["restates", "derives"])
def test_the_COUNT_rule_SEPARATES_a_restated_figure_from_a_derived_one(
        label: str, bullet: str, restates: bool) -> None:
    """Both answers, on bullets the live prompts no longer contain.

    Once the three prompts are corrected, this rule is reachable only through
    text that passes — so a change to `_bullet_lead` or `_A_NUMERAL` would answer
    "nothing restated" everywhere and go permanently green over the defect it
    was written for. The failing case has to live somewhere, and here it is.
    """
    assert bool(_A_NUMERAL.search(_bullet_lead(bullet))) is restates
    assert _column_bullets(bullet) == [bullet], (
        f"{label}: the bullet finder no longer recognises its own fixture")


_PROMISES_ONE = "One row in that column is NOT mechanically checked, and you are told which."
_PROMISES_TWO = "Two rows in that column are NOT mechanically checked, and you are told which."
_PROMISES_NOTHING = "Every path outside the grant is compared by content."

_ONE_JUDGEMENT = {"a": "act.ids_deleted over both snapshots",
                  "b": "JUDGEMENT — sequencing leaves no artifact"}
_TWO_JUDGEMENTS = {"a": "JUDGEMENT — design leaves no artifact",
                   "b": "JUDGEMENT — sequencing leaves no artifact"}


@pytest.mark.parametrize("label,sentence,observers,agrees", [
    ("one promised, one registered", _PROMISES_ONE, _ONE_JUDGEMENT, True),
    ("one promised, two registered", _PROMISES_ONE, _TWO_JUDGEMENTS, False),
    ("two promised, two registered", _PROMISES_TWO, _TWO_JUDGEMENTS, True),
    ("two promised, one registered", _PROMISES_TWO, _ONE_JUDGEMENT, False),
], ids=["1-1", "1-2", "2-2", "2-1"])
def test_the_PROMISE_rule_SEPARATES_a_true_count_from_a_stale_one(
        label: str, sentence: str, observers: dict[str, str],
        agrees: bool) -> None:
    """All four corners, including the PLURAL the live prompts never exercise.

    Every live prompt says "One row … is", so the singular is the only spelling
    the anchor is proved against by the parametrisation above. A regex that had
    silently lost its `rows?`/`are` alternation would still pass there and would
    drop any prompt that grew a second judgement row straight out of the
    population — failing open on precisely the change this rule watches for.
    """
    assert (_stated_unchecked(sentence) == len(_judgement_rows(observers))) is agrees


def test_the_PROMISE_rule_reads_NOTHING_from_a_prompt_that_makes_no_promise() -> None:
    """`None`, not a crash and not a zero.

    A sentence-free prompt must be UNREADABLE rather than read as "zero rows
    unchecked" — zero is a claim, and one that would agree with any registry
    holding no `JUDGEMENT` rows at all.
    """
    assert _stated_unchecked(_PROMISES_NOTHING) is None


def test_the_COLUMN_BULLET_finder_HAS_a_population() -> None:
    """POSITIVE CONTROL on the finder, against the rule above passing vacuously.

    `test_the_COLUMN_BULLET_does_not_RESTATE_a_count_it_could_DERIVE` asserts an
    EMPTY list, so a finder that matched nothing at all would satisfy it for
    every prompt forever — the exact shape of a check that stopped checking, and
    the one this repo has issue #103 open about. Pinned per prompt rather than as
    a total, because a total hides one prompt falling to zero while another
    grows. The figures are what the shapes described in `_column_bullets`
    produce: one enumerating bullet for each `plan_*` prompt, and for
    `triage-candidates` a bullet each for `status`, `component` and `size` plus
    its deletion bullet, which names `status` in its body. FOUR, NOT THREE --
    this control was written asserting three and the finder corrected it, which
    is the control doing its job before the rule ever shipped.
    """
    found = {name: len(_column_bullets(_enforcement_block(_prompt(mod, prompt))))
             for mod, prompt, name in workflows_declaring("MAY_NOT_OBSERVERS")
             if _enforcement_block(_prompt(mod, prompt)) is not None}
    assert found == {"plan-draft": 1, "plan-verify": 1, "triage-candidates": 4}, (
        f"the column-bullet finder sees {found}. A count that fell to 0 means "
        f"the rule above is judging nothing for that prompt and would stay green "
        f"through any count it grew back; a count that ROSE means the list "
        f"gained a bullet naming a guarded column, which is legitimate — confirm "
        f"its lead carries no restated figure and update this number.")

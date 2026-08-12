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

import re
from pathlib import Path

import pytest

from modules.assistant.plan import plan_activities as act
from modules.assistant.plan.plan_sprint import plan_sprint_workflow as sprint
from modules.assistant.plan.triage_candidates import triage_candidates_workflow as triage

WORKFLOWS = [
    pytest.param(triage, "triage_candidates.md", id="triage-candidates"),
    pytest.param(sprint, "plan_sprint.md", id="plan-sprint"),
]

_NS_REF = re.compile(r"\b(act|own)\.([a-z_][a-z_0-9]*)\b")
_OWN_SYMBOL = re.compile(r"\b(FORBIDDEN_PATHS|PERMITTED_PATHS|permitted_paths|"
                         r"_rulings_this_run_had_no_right_to)\b")


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
    return (mod.PROMPTS / name).read_text()


# --- the correspondence itself ----------------------------------------------

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
    workflow module itself.
    """
    unresolved: list[str] = []
    for row, mechanism in mod.MAY_NOT_OBSERVERS.items():
        if mechanism.startswith("JUDGEMENT"):
            continue
        for ns, attr in _NS_REF.findall(mechanism):
            target = getattr(mod, ns, None)
            if target is None or not hasattr(target, attr):
                unresolved.append(f"{row!r} -> {ns}.{attr}")
        for symbol in set(_OWN_SYMBOL.findall(mechanism)):
            if not hasattr(mod, symbol):
                unresolved.append(f"{row!r} -> {symbol}")
    assert not unresolved, (
        f"{mod.__name__} names mechanisms that do not exist:\n  "
        + "\n  ".join(unresolved))


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
        elif not (_NS_REF.search(mechanism) or _OWN_SYMBOL.search(mechanism)):
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
                 "docs/standards/workflow-scripts.md")
    permitted = ("docs/standards/architecture/research/candidates.md",
                 "docs/standards/architecture/research/direction.md")
    for path in forbidden:
        assert act.boundary_crossings({}, {path: "h"}, triage.FORBIDDEN_PATHS,
                                      triage.PERMITTED_PATHS) == [path], (
            f"triage-candidates may edit {path} undetected")
    for path in permitted:
        assert act.boundary_crossings({}, {path: "h"}, triage.FORBIDDEN_PATHS,
                                      triage.PERMITTED_PATHS) == [], (
            f"triage-candidates cannot do its job: {path} is blocked")


def test_plan_sprint_permits_only_its_override_and_the_proposal_file() -> None:
    """Its override opens ONE file, which sits among the phase docs it must not touch.

    `direction.md` is deliberately absent from the permitted set — appending to
    it is `triage-candidates`'s — and `candidates.md` is present only because the
    SHARED instruction in `decision_log_and_reflection.md` requires every
    producing run to place a surfaced proposal there. Its columns are guarded
    separately, so permitting the path does not permit a ruling.
    """
    rel_sprint = "docs/development/sprint.md"
    allowed = sprint.permitted_paths(rel_sprint)
    for path in (rel_sprint, "docs/standards/architecture/research/candidates.md"):
        assert act.boundary_crossings({}, {path: "h"}, sprint.FORBIDDEN_PATHS,
                                      allowed) == [], f"plan-sprint blocked from {path}"
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

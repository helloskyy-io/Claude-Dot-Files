"""Shared I/O for the planning family — promoted per §10.1 rule 3.

Sits at module level because more than one workflow uses it: `plan_sprint`,
`triage_candidates` and `plan_revision` today, `plan_tech_stack` when it lands.
The promotion rule was anticipatory when this file was written and is now
satisfied outright.

THE SPLIT SETTLED WHAT BELONGS HERE, AND RULE 3 DECIDED IT — NOT TASTE. This
docstring used to record `candidate_counts`, `direction_ceiling` and
`existing_work` as a stated rule-3 deviation: here on the family's shared surface
with only `plan_sprint` calling them. Splitting triage out gave two of them a
genuine second caller and left the other single-consumer, so each moved to where
its consumer count puts it:

  * `candidate_counts` — `triage_candidates` (its working set) and `plan_sprint`
    (the ruled set it places from). Two consumers, so it stays.
  * `existing_work` — `triage_candidates` (does this candidate already have a
    home?) and `plan_sprint` (§4b coherence: a finding with no home in the sprint
    plan, in a component, or in an open issue). Two consumers, so it stays.
  * `candidate_statuses` — both workflows, each to prove it did not touch the one
    column neither of them owns. Two consumers, so it stays.
  * `candidate_decisions` — one consumer. MOVED to `plan_sprint_activities`.
  * `direction_ceiling` — one consumer. MOVED to `triage_candidates_activities`.
  * `new_sprint_sections`, `component_dir` — one consumer each (`plan_project`,
    and nothing else in the tree). MOVED to `plan_project_activities`. They were
    missing from the audit above when it was first written, which made this
    docstring's own rule-3 claim incomplete on the very file that states the
    rule. Counted rather than eyeballed the second time.

`candidate_decisions` and `direction_ceiling` were briefly argued to belong here
anyway, as "the same concern as their neighbours".
[`workflow-scripts.md` § Location](../../../../../../docs/standards/workflow-scripts.md)
restates §10.1 rule 3 as BINDING and forecloses exactly that argument — *"consumer
count decides, never taste"* — and rule 6 gives a workflow folder its place to
grow a helper it has earned. The row-level primitives they need are exported
below, so the parsing still has one definition.

WHAT ELSE IS SHARED, AND WHY IT IS *HERE* RATHER THAN IN EITHER FOLDER. Both
workflows must show they stayed inside their authorization, and both do it the
same way: snapshot the worktree before the model runs, snapshot it after, and
name any forbidden path whose content moved. `git_output`, `worktree_state` and
`boundary_crossings` are that mechanism, with two consumers each. `ids_deleted`
likewise — a row vanishing from `candidates.md` is an offence under BOTH
workflows, and it used to be caught under only one.

DISAPPEARANCE IS ITS OWN CLASS, AND EVERY COMPARATOR HERE WAS BLIND TO IT.
`statuses_this_run_had_no_right_to` judges `before.keys() & after.keys()`;
`Counter` subtraction discards removals; `boundary_crossings` exempts a permitted
path unconditionally. Each reports ADDITION and MUTATION and says nothing about a
row, a checkbox or a whole file that is simply GONE — so four separate channels
returned a green run and a PR URL over a deleted operator ruling, a deleted
sprint plan, a sprint plan renamed out of the tree, and an erased completion tick.
`ids_deleted` and `grants_that_vanished` are the two answers, one per altitude:
rows and files. `test_disappearance_is_observed.py` holds the class by requiring
every before/after snapshot in the family to name what watches it for absence.

NOT IDEMPOTENT (§7.1): these push commits and open PRs. Under Temporal a retry
is a NEW ATTEMPT, not a replay.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import NamedTuple

from .. import assistant_activities as shared

load_prompt = shared.load_prompt
shared_prompt = shared.shared_prompt
render = shared.render
run_claude = shared.run_claude
worktree_add = shared.worktree_add
pr_branch = shared.pr_branch
extract_pr_url = shared.extract_pr_url
observe_outcome = shared.observe_outcome
max_turns = shared.max_turns

# A candidate row:
#   | C-001 | title | component | source | `decision` | `status` | note |
#
# CELLS ARE MATCHED AS `[^|\n]*`, NOT `.*?`, AND THAT IS LOAD-BEARING. Note text
# in this file carries UNESCAPED PIPES, so anything that splits a whole row on
# `|` reads a different number of cells per row. Every cell this regex captures
# stops at the next pipe, and the Note it never reaches is the only place a stray
# pipe has ever appeared.
#
# THE PROPERTY IS STATED WITHOUT A TALLY, DELIBERATELY. This comment carried
# "four rows of 76 do" and was falsified by the very commit that added the
# `component` column, because that commit also appended a row — a restated figure
# drifting one commit after it was measured is the class C-050's own Note names.
# The load-bearing claim is that NO row's first five cells contain a pipe; a tally
# of the Note's pipes is decoration and any new row can falsify it.
_ROW = re.compile(
    r"^\|\s*(C-\d{3})\s*\|([^|\n]*)\|([^|\n]*)\|[^|\n]*\|([^|\n]*)\|([^|\n]*)\|", re.M)

# The seven-column header, as every candidate table in the file renders it.
# Kept for the MESSAGE it can give — "your table is the old shape" is a better
# sentence than "row C-082's decision is unreadable" when the whole table moved.
# It is NOT the guard; see `_check_shape`.
_HEADER = "| ID | Candidate | `component` | Source | `decision` | `status` | Note |"

# Anything that PRESENTS as a candidate row, whatever its id happens to look
# like. `_ROW` insists on `C-\d{3}`; this insists only on the shape a reader
# would call a row, so the two can be compared and a row that fell out of the
# parse can be named instead of vanishing.
_ROW_LINE = re.compile(r"^\|\s*(C-\S+?)\s*\|", re.M)

# THE CLOSED VOCABULARIES, AND THEY ARE THE FILE'S OWN. `candidates.md` § The
# three dispositions: *"Every candidate ends at exactly one of these. There is no
# fourth"* — `ship` / `requires review` / `reject`, plus blank for not-yet-triaged.
# § Two flags gives `status` its two values.
_DECISIONS = ("", "ship", "requires review", "reject")
_STATUSES = ("", "open", "closed")

_BLANK = ("", "—", "-")


class CandidateRow(NamedTuple):
    """One parsed row, NAMED — because the tuple grew and callers index it.

    It was a bare `(id, decision, status)` triple until `component` was added
    between `Candidate` and `Source`. Widening a positional tuple silently
    re-points every unpacking site by one, and three of the sites here are
    AUTHORIZATION GUARDS — `candidate_decisions`, `candidate_statuses` and
    `candidate_components` each prove a run did not write a column it does not
    own. A guard that compares the wrong field still returns a clean dict and
    still reports a clean run, so the failure would be invisible in exactly the
    place invisibility costs most. Named access makes the same mistake a crash
    instead.
    """

    id: str
    title: str
    component: str
    decision: str
    status: str


def normalise_cell(cell: str) -> str:
    """One definition of what a `decision` / `status` cell MEANS, markup removed.

    ONE definition, because two of them drifted. `candidate_counts` normalised
    with `.strip().strip("`")` and `candidate_decisions` — written later, for the
    guard — with `.strip().strip("`").strip()`. The extra strip matters: a cell
    typed `` ` — ` `` (padding INSIDE the backticks) came out as `" — "` under the
    first and `""` under the second, so the row read as RULED to the counter and
    BLANK to the guard. `triage_candidates`'s completion post-condition is built
    on the counter, so such a row would drop out of the working set unruled while
    the post-condition reported a complete pass — the exact failure that
    post-condition exists to catch, defeated by a normalisation written twice.

    Measured on the live file at the time of the fix: 69 rows, 24 untriaged, the
    two readers agreeing on every row. The defect was latent, not firing — which
    is why it is worth removing rather than watching.
    """
    value = cell.strip().strip("`").strip()
    return "" if value in _BLANK else value


def candidate_rows(candidates_path: Path, *, missing_hint: str) -> list[CandidateRow]:
    """Every row in the file, normalised. One parse, one place.

    `missing_hint` lets each caller say what the absent file costs IT, without a
    second copy of the regex travelling with the sentence.

    `title` and `component` are normalised the same way as the two flags. For
    `component` that matters: a filer typing `` ` — ` `` means "I did not name
    one", and a scaffolder that read it literally would try to create a
    directory out of an em dash.

    THE SHAPE IS CHECKED BEFORE ANY ROW IS RETURNED, and it raises rather than
    returning what it can. See `_check_shape`: every way this file's real shape
    can depart from the assumed one lands in the same place — a row that reads
    as TRIAGED without anybody having ruled it, or a row that is simply not
    there. An empty-ish result here is not a safe degradation; it is a
    clean-looking answer over a working set that has quietly lost rows.
    """
    if not candidates_path.exists():
        raise FileNotFoundError(f"candidates file not found: {candidates_path}. {missing_hint}")
    text = candidates_path.read_text()
    rows = [CandidateRow(cid, normalise_cell(title), normalise_cell(comp),
                         normalise_cell(dec), normalise_cell(st))
            for cid, title, comp, dec, st in _ROW.findall(text)]
    _check_shape(candidates_path, text, rows, missing_hint)
    return rows


def _check_shape(path: Path, text: str, rows: list[CandidateRow],
                 missing_hint: str) -> None:
    """Raise unless the file's real shape is the one `_ROW` assumes.

    KEYED ON THE CLASS, NOT ON A SPELLING OF IT, and that distinction is the
    whole reason this is a function rather than the one-line header test it
    replaces. Every way the shape has departed or can depart produces the SAME
    failure — a row that leaves the untriaged working set without anybody ruling
    it, while `triage-candidates` reports a complete pass — so the check asks
    about the failure rather than about the departures.

    THE HEADER TEST CAUGHT ONE OF THEM, AND ONLY BY LUCK. It asked whether a
    seven-column header appeared ANYWHERE in the file; this file holds many
    candidate tables, so the correct ones satisfied it while another was
    malformed. Measured on the real file: one table reverted to the old shape and
    the guard stayed silent while the untriaged count fell from 33 to 25.

    So the check no longer asks about the table's shape at all. It asks the
    questions whose answers a departure necessarily corrupts, one per helper
    below, and each helper's docstring is the only place its case is described:

      * `_raise_on_unparsed_rows`  — is the population the readers see the
        population the file holds?
      * `_raise_on_duplicate_ids`  — the same question one altitude down, and it
        needs its own helper because a SET answers neither on its own.
      * `_raise_on_foreign_cell`   — does every parsed row's `decision` and
        `status` fall in the closed vocabulary `candidates.md` defines?

    ONE CASE PER HELPER, RATHER THAN ONE LIST IN ONE DOCSTRING, and that is the
    fix for a defect this docstring itself carried: it opened *"Three ways the
    shape has departed"* over FOUR bulleted cases, because the fourth was added
    without the tally being re-counted. That is the same class as every hand-kept
    figure this repo has already gated — a count of mutable state, restated where
    nothing derives it — arriving inside the function whose whole argument is
    *count things, do not eyeball them*. A list that lives in one docstring per
    case cannot go out of step with itself, and the next case added here inherits
    that by construction rather than by anybody remembering.
    """
    _raise_on_unparsed_rows(path, text, rows, missing_hint)
    _raise_on_duplicate_ids(path, rows, missing_hint)
    _raise_on_foreign_cell(path, text, rows, missing_hint)


def _raise_on_unparsed_rows(path: Path, text: str, rows: list[CandidateRow],
                            missing_hint: str) -> None:
    """Every line that PRESENTS as a candidate row must actually have parsed.

    An id that is not `C-` plus exactly three digits is the reachable way to fail
    this: `_ROW` does not match it at all, so the row is absent from every reader
    and every guard here is green over it.
    """
    unparsed = sorted(set(_ROW_LINE.findall(text)) - {row.id for row in rows})
    if unparsed:
        raise ValueError(
            f"{path} holds {len(unparsed)} line(s) that present as candidate rows "
            f"but that the row parser does not match: {', '.join(unparsed)}. An "
            f"id must be `C-` plus exactly three digits. A row the parser cannot "
            f"see is absent from the untriaged working set, from every "
            f"authorization snapshot, and from the deletion check — every guard "
            f"reads green over it. {missing_hint}")


def _raise_on_duplicate_ids(path: Path, rows: list[CandidateRow],
                            missing_hint: str) -> None:
    """No id may name two rows — the door that has actually opened.

    Every reader here is a dict keyed by id, so the second row's `decision`,
    `status` and `component` silently overwrite the first's and one of the two
    candidates stops existing for every consumer.
    `test_candidate_ids_are_unique` records it three times by 2026-08-11 and
    twice more on 2026-08-13, always the same way — two branches each allocate
    the next free id against the same base and both merge. That test is a merge
    gate on ONE file on the default branch; this runs at the moment a pipeline
    reads whatever file it was handed, which is the branch mid-collision, and the
    two comparators that would notice a lost row (`ids_deleted`,
    `components_this_run_had_no_right_to`) are keyed by the same colliding id and
    see nothing.

    IT CANNOT BE FOLDED INTO THE CHECK ABOVE, and that is why it is its own
    helper rather than two lines there: that one compares SETS, and a duplicated
    id collapses into a set — so it reads clean over exactly the row this exists
    to catch.
    """
    repeated = sorted(cid for cid, n in Counter(row.id for row in rows).items() if n > 1)
    if repeated:
        raise ValueError(
            f"{path} allocates {len(repeated)} id(s) to more than one row: "
            f"{', '.join(repeated)}. Every reader here is a dict keyed by id, so "
            f"the later row's `decision`, `status` and `component` overwrite the "
            f"earlier one's and one of the two candidates stops existing for the "
            f"untriaged working set, for both authorization snapshots and for the "
            f"deletion check — all of which are keyed by the same colliding id and "
            f"see nothing. This happens when two branches each allocate the next "
            f"free id against the same base and both merge; take the next free id "
            f"by re-reading the file at HEAD. {missing_hint}")


def _raise_on_foreign_cell(path: Path, text: str, rows: list[CandidateRow],
                           missing_hint: str) -> None:
    """`decision` and `status` must hold values `candidates.md` admits.

    THIS IS THE ARM THAT COVERS SHAPES NOBODY HAS THOUGHT OF YET, which is why it
    does not name any of them. A column shift moves foreign text into the two
    flag cells — `open` into `decision` for a table left in the old six-column
    shape, a Source string for a row carrying a pipe in one of its first five
    cells (markdown's own escape for a literal pipe is `\\|`, and `[^|\\n]*`
    treats that pipe as a cell boundary, so a CORRECTLY escaped title shifts the
    row). Neither shape is enumerated in the condition: the condition asks
    whether the cell reads as something the file admits, so any future departure
    that moves text sideways fails here rather than being discovered by a later
    pass.

    It is not exhaustive and does not claim to be — a shift lands silently only
    if the displaced text happens to read as one of the seven admitted strings.
    The message names both known shapes because a reader who has just been told
    "row C-082's decision is unreadable" needs to know where to look.
    """
    for row in rows:
        if row.decision in _DECISIONS and row.status in _STATUSES:
            continue
        shape = ("" if _HEADER in text else
                 f"\nNo table in this file carries the expected header:\n  {_HEADER}\n"
                 f"so the whole table is probably still in the old six-column shape.")
        raise ValueError(
            f"{path} row {row.id} parses to decision={row.decision!r} "
            f"status={row.status!r}, and `candidates.md` admits no such value — "
            f"`decision` is one of {_DECISIONS} and `status` one of {_STATUSES}. "
            f"A cell holding anything else means the columns have SHIFTED: the "
            f"row then reads as triaged, drops out of the untriaged working set, "
            f"and `triage-candidates` reports a complete pass over a candidate "
            f"nobody ruled. Either a table is in the old six-column shape, or "
            f"this row carries a pipe in one of its first five cells — only the "
            f"Note may contain one.{shape} {missing_hint}")


def candidate_components(candidates_path: Path) -> dict[str, str]:
    """Every row's `component`, normalised, keyed by id — the column NO workflow owns.

    THE THIRD COLUMN, AND THE ONLY ONE WHOSE WRITER IS NOT A PROCESS.
    `candidates.md` gives `decision` to `triage-candidates` and `status` to a
    later process; it gives `component` to *whoever FILES the candidate, at the
    moment they file it*, on the stated grounds that anything downstream would be
    guessing at it from a one-line summary.

    It needs a guard for a reason the other two do not have: a guessed value here
    does not stay a bad cell. `plan-candidates` turns it into
    `docs/development/<slug>/research/` in the very next step of the same parent,
    on the same branch, in the same PR — so a run that invents a component name
    ships a committed directory and two research dispatches for it.

    AND IT IS NO LONGER ALONE IN THAT, WHICH IS WORTH SAYING RATHER THAN LETTING
    A READER INFER THE OPPOSITE. `_seed` writes `title` verbatim into the new
    component's synthesis and the parent tells the research child that file is its
    brief — so an edited SUMMARY changes what a research cycle is commissioned to
    investigate. A fourth snapshot was considered and NOT taken: a wrong title
    produces a wrong brief, which `research-verify` reads and can hold on, whereas
    a wrong `component` produces a directory nothing downstream inspects. Different
    exposure, so the guard goes where the exposure is unobserved.

    An APPENDED row is exempt by construction, because the comparator judges only
    ids present on both sides: a run filing a proposal is *required* to name its
    component, and that is the one write of this column any workflow may make.
    """
    return {row.id: row.component for row in candidate_rows(candidates_path, missing_hint=(
        "Without it there is no `component` column to hold anything to."))}


def components_this_run_had_no_right_to(before: dict[str, str],
                                        after: dict[str, str]) -> list[str]:
    """Ids whose `component` changed on a row that already existed. No workflow may.

    The same shape as `statuses_this_run_had_no_right_to` and for the same
    reason — only pre-existing rows are judged, so a row this run APPENDED is
    outside it. Written out rather than routed through a shared helper because
    the two columns are prohibited for DIFFERENT reasons and each docstring is
    the place that reason is recorded; sharing the body would leave one of them
    with nowhere to say it.
    """
    return sorted(cid for cid in before.keys() & after.keys()
                  if before[cid] != after[cid])


def candidate_counts(candidates_path: Path) -> dict[str, int]:
    """Count rows by triage state — computed in code, never asked of a model.

    Arithmetic is not delegated: a model once marked four of eight papers past
    window when one was, every flag internally consistent against a date it had
    invented. The same rule applies to any count a prompt or a report asserts.
    """
    rows = candidate_rows(candidates_path, missing_hint=(
        "`triage-candidates` rules the rows in it and `plan-sprint` places what "
        "they ruled; without the file neither has anything to work from."))
    untriaged = [row.id for row in rows if not row.decision]
    return {
        "total": len(rows),
        "untriaged": len(untriaged),
        "triaged": len(rows) - len(untriaged),
        "untriaged_ids": untriaged,
    }


def candidate_statuses(candidates_path: Path) -> dict[str, str]:
    """Every row's `status`, normalised, keyed by id — the column NEITHER owns.

    `decision` moved from `plan-sprint` to `triage-candidates`; `status` moved
    nowhere, because it was never either workflow's. `candidates.md` gives it to
    "a later process" — `plan-feature`, or the build that completes the item —
    and both prompts list it under MAY NOT.

    It is here rather than in one workflow's folder because BOTH snapshot it, for
    the same reason and against the same file. The argument that built the
    `decision` guard reaches this column unchanged: `status` is the cell
    immediately beside the one each run is legitimately reading, and *"we have
    decided to do this"* is one plausible step from *"this is handled"*.
    """
    return {row.id: row.status for row in candidate_rows(candidates_path, missing_hint=(
        "Without it there is no `status` column to hold anything to."))}


def statuses_this_run_had_no_right_to(before: dict[str, str],
                                      after: dict[str, str]) -> list[str]:
    """Ids whose `status` changed on a row that already existed. Neither run may.

    ONLY pre-existing rows are judged. A row this run APPENDED is a proposal
    placed under the shared instruction in `decision_log_and_reflection.md`,
    which tells it to write `status: open` — so a new row's `status` is
    prescribed by another rule and is not this guard's business. Row deletion is
    already an offence under the `decision` guard, so it is not re-reported here.
    """
    return sorted(cid for cid in before.keys() & after.keys()
                  if before[cid] != after[cid])


def ids_deleted(before: dict[str, str], after: dict[str, str]) -> list[str]:
    """Ids that were in the file before this run and are not in it after.

    ONE DEFINITION, because the claim that it had one was false. The comment on
    `statuses_this_run_had_no_right_to` said *"row deletion is already an offence
    under the `decision` guard, so it is not re-reported here"* — true of
    `plan-sprint`, which does compare the id sets, and FALSE of
    `triage-candidates`, which had no such comparison at all. Its completion
    post-condition counts rows whose `decision` is blank, so DELETING an
    untriaged row drops the count exactly as ruling it would: the run reports a
    complete triage over a candidate that no longer exists. The file's whole
    promise is that a rejected candidate stays visibly rejected instead of being
    re-proposed, and a silently dropped row breaks it in the one direction nobody
    would look for.

    Both status guards are blind to this by construction — they judge
    `before.keys() & after.keys()`, and a deleted id is in neither intersection.
    """
    return sorted(before.keys() - after.keys())


def git_output(worktree: Path, argv: list[str], cannot_hint: str) -> str:
    """Run a read-only git query in the worktree, or RAISE saying what is now unknown.

    Every boundary observer in this family needs the same thing — git's answer,
    or a loud failure — and each one that hand-rolled it wrote its own message
    about what the silence would cost. Sharing the mechanism keeps the failure
    behaviour identical while each caller still supplies its own `cannot_hint`,
    which is the part that differs.

    RAISES rather than returning empty, and the distinction is the whole point: a
    guard that cannot observe must not be read as having observed nothing. An
    empty return is indistinguishable from a clean run, so a git failure would
    manufacture evidence of compliance.
    """
    out = subprocess.run(argv, cwd=str(worktree), capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(
            f"could not read the worktree state in {worktree} via "
            f"`{' '.join(argv)}`: {out.stderr.strip()}. {cannot_hint}"
        )
    return out.stdout


def worktree_state(worktree: Path, base_ref: str = "origin/main") -> dict[str, str]:
    """Every path this worktree has touched, mapped to a digest of its content.

    SNAPSHOT-AROUND-THE-RUN, NOT DIFF-AGAINST-MAIN, and that is a correctness
    requirement rather than a preference. `plan-sprint` runs LAST on a branch
    `triage-candidates` has already written to, so a diff against `origin/main`
    attributes triage's legitimate `direction.md` edit to plan-sprint, which is
    forbidden from touching it. Comparing two snapshots taken either side of one
    model run names what THAT run did and nothing else.

    Content is digested rather than merely listed because the earlier path-list
    form could not tell "triage edited this file" from "triage edited it and
    plan-sprint edited it again": both appear once in a name-only diff.

    `--no-renames -z` is deliberate on both commands, and it retired a real
    bypass. The previous guard split a porcelain rename line on `" -> "` and kept
    the DESTINATION, so renaming `sprint.md` AWAY (`git mv sprint.md notes.md`)
    produced `notes.md`, matched nothing, and the run reported success over an
    edit to the operator's sequencing surface. Reproduced before fixing.
    `--no-renames` reports the two halves as a separate delete and add, so there
    is no arrow to parse; `-z` turns off git's C-style quoting, so there are no
    backslash escapes to unescape either. Two parsing bug classes deleted rather
    than handled.
    """
    hint = ("This run cannot show which files it left alone, and an unobservable "
            "boundary is not a kept one.")
    touched: set[str] = set()
    for argv in (["git", "diff", "--name-only", "--no-renames", "-z", f"{base_ref}...HEAD"],
                 ["git", "status", "--porcelain", "--no-renames", "-z"]):
        is_status = argv[1] == "status"
        for entry in git_output(worktree, argv, hint).split("\0"):
            # porcelain prefixes a two-column state and a space; `git diff
            # --name-only` does not. Both are NUL-terminated, so the split
            # leaves a trailing empty field.
            path = entry[3:] if is_status else entry
            if path:
                touched.add(path)

    state: dict[str, str] = {}
    for rel in touched:
        f = worktree / rel
        state[rel] = (hashlib.sha256(f.read_bytes()).hexdigest()
                      if f.is_file() else ABSENT)
    return state


# TWO DISTINCT KINDS OF "no digest", and collapsing them re-opened the exact
# bypass this observer was rewritten to close.
#
#   ABSENT   — git reported the path as changed and it is not on disk: DELETED.
#   BASELINE — git did not report it at all: untouched, whatever the base holds.
#
# A rename-away produces ABSENT in the after-snapshot and NOTHING in the before
# one, because a clean tree reports no changed paths. With a single sentinel as
# the `.get` default those compare equal and `git mv sprint.md notes.md` reads as
# untouched — the same defeat the old `" -> "` parsing had, arriving by a
# different route. Caught by the regression test written for the original bypass,
# which is why that test exercises real git rather than a stub.
ABSENT = "<absent>"
BASELINE = "<unchanged>"


def grants_that_vanished(before: dict[str, str], after: dict[str, str],
                         permitted: tuple[str, ...]) -> list[str]:
    """Permitted paths this run made cease to exist. A WRITE GRANT IS NOT A DELETE GRANT.

    THE HOLE THIS CLOSES, and it was the widest one in the family. `permitted`
    wins over `forbidden` in `boundary_crossings` unconditionally, so the one
    file each workflow's override exists FOR is the one file whose disappearance
    nothing observed. Demonstrated end-to-end before it was fixed: `plan-sprint`
    deleting `docs/development/sprint.md` returned a PR URL and a green run, and
    so did `git mv docs/development/sprint.md notes.md` — the operator's
    cross-domain sequencing surface, which `standards-governance.md` protects
    with a human-in-the-loop rule, gone with every guard reporting clean.

    DERIVED FROM `permitted`, NEVER FROM A LIST OF FILES, and that is what makes
    this a class check rather than two patches. Each workflow already declares
    the paths its override opens; a grant added later is covered the moment it is
    declared, with nobody having to remember this function exists.

    ABSENT ON THE AFTER SIDE ONLY. A path git does not report at all is
    `BASELINE`, so a permitted file that never existed and still does not is not
    a deletion — `triage-candidates` legitimately CREATES `direction.md`, and a
    run that creates it must not be failed for having created it. Requiring the
    before side to differ also exempts a file some EARLIER child on the branch
    deleted: that is already `ABSENT` on both sides, and this run did not do it.
    """
    allow = [re.compile(p) for p in permitted]
    return [rel for rel in sorted(before.keys() | after.keys())
            if after.get(rel, BASELINE) == ABSENT
            and before.get(rel, BASELINE) != ABSENT
            and any(p.search(rel) for p in allow)]


def boundary_crossings(before: dict[str, str], after: dict[str, str],
                       forbidden: tuple[str, ...],
                       permitted: tuple[str, ...] = ()) -> list[str]:
    """Forbidden paths whose content moved between the two snapshots.

    `permitted` wins over `forbidden`, and it is not an optional refinement:
    every real declaration in this family needs it. `triage-candidates` may not
    edit anything under `docs/standards/` — except `candidates.md` and
    `direction.md`, which live there and which it EXISTS to write.
    `plan-sprint` may not edit a phase doc under `docs/development/` — except the
    sprint file, which lives there and which it alone is authorised to edit.
    Without the exception list a correct run fails on its own output.
    """
    allow = [re.compile(p) for p in permitted]
    deny = [re.compile(p) for p in forbidden]
    return [rel for rel in sorted(before.keys() | after.keys())
            if before.get(rel, BASELINE) != after.get(rel, BASELINE)
            and not any(p.search(rel) for p in allow)
            and any(p.search(rel) for p in deny)]


def existing_work(tree: Path, research_dir: Path) -> str:
    """Enumerate what a candidate might ALREADY have a home in.

    `tree` IS THE TREE THE RUN CAN SEE, NOT THE REPO. Both callers pass their
    WORKTREE, and the parameter is named for that rather than `repo_root`
    because it was `repo_root` and both callers duly passed one — which
    enumerated the main checkout while the run read and wrote somewhere else.
    The cost is not symmetric: `plan-sprint` runs THIRD, after the parent has
    written a brand-new `docs/development/<slug>/research/synthesis.md` into the
    worktree, and its Stage 1 is told to read *"EVERY component synthesis listed
    in the enumeration below"*. An enumeration anchored at the repo cannot list
    the one paper the pipeline exists to hand it, and the run reports having
    read every synthesis there was.

    A dry-run renders this against the repo itself, and that is still correct —
    the parameter asks for whichever tree the caller's model will read, and for
    a dry run there is no other.

    Deliberately NOT included: `cpi-decisions.md`. It is the tooling-improvement
    loop and the home for deferrals carrying watch-criteria — a different concern
    from product trajectory. Feeding it to a triage pass invites the run to
    re-decide things outside its remit.

    Computed in code and handed over, rather than asked of the model: a triage
    that ships a candidate already tracked as an open issue creates two homes for
    one item, which is the duplication the candidates file exists to prevent.
    """
    import subprocess

    lines: list[str] = []

    comps = sorted(d for d in (tree / "docs" / "development").iterdir()
                   if d.is_dir() and d.name != "reviews")
    lines.append("**Existing components** (a candidate may belong inside one rather than needing its own sprint section):")
    for c in comps:
        syn = c / "research" / "synthesis.md"
        mark = " — **HAS COMPONENT RESEARCH**: `" + str(syn.relative_to(tree)) + "`" if syn.exists() else ""
        lines.append(f"  - `docs/development/{c.name}/`{mark}")

    withres = [c for c in comps if (c / "research" / "synthesis.md").exists()]
    if withres:
        lines.append(
            f"\n**{len(withres)} component(s) carry their own research synthesis, listed above and counted in code.** "
            f"Each one is evidence about a sprint section that ALREADY EXISTS, and it is almost always NEWER than the "
            f"section it backs — research is commissioned after a sprint item is written, so the section states what "
            f"was believed BEFORE the evidence arrived. **Read every one of them in Stage 1** and reconcile its "
            f"sprint section against it in Stage 4. A synthesis nobody reads back into the plan is a paper we paid "
            f"for and did not use."
        )

    papers = sorted(p.name for p in (research_dir / "raw").glob("*.md"))
    lines.append(f"\n**Research pool** — {len(papers)} papers. A significant finding with no home in the "
                 f"sprint plan is a Stage 4 coherence finding:")
    lines += [f"  - `{n}`" for n in papers]

    r = subprocess.run(["gh", "issue", "list", "--state", "open", "--limit", "50",
                        "--json", "number,title"], cwd=str(tree),
                       capture_output=True, text=True)
    if r.returncode == 0:
        import json
        issues = json.loads(r.stdout)
        lines.append(f"\n**Open issues** — {len(issues)}. **A candidate matching one of these is ALREADY tracked**; "
                     f"say so and do not create a second home for it:")
        lines += [f"  - #{i['number']} {i['title']}" for i in issues]
    else:
        lines.append("\n**Open issues: COULD NOT BE READ.** Do not assume there are none — "
                     "say in your report that this check did not run.")

    return "\n".join(lines)


PROBLEM_STATEMENT = Path("docs/standards/architecture/problem-statement.md")
PRODUCT_POOL = Path("docs/standards/architecture/research")
COMPONENT_ROOT = Path("docs/development")


def evidence_block(repo_root: Path) -> str:
    """POINT a planning run at the thesis and the pools, PRIMARY first.

    THE GAP THIS CLOSES. `plan_revision` consumes research only when the
    dispatch brief happens to hand it over — its prompt's research checks are
    both conditional ("if your inputs include research artifacts"). So a plan
    designed against evidence the fleet already paid for depended on whoever
    wrote the brief remembering to name it. `plan_sprint` reads the problem
    statement; `plan_revision` had no pointer to anything.

    That is the same failure that cost a full research cycle on 2026-08-12, one
    layer up: a brief named four files, the run read exactly those four, and the
    paper that already answered the question sat unopened in the pool.

    ORDERED, NOT DUMPED. `plan_revision` is the GENERIC planning child — unlike
    its siblings it is told no file structure and infers its target from a
    free-text description. A flat list of every pool makes the run guess which
    one is its own, so the block teaches the convention instead: a feature's own
    pool is the PRIMARY evidence, and the project pool is there for how it all
    fits together. Product-first ordering had the emphasis exactly backwards.

    A POINTER, never the content. Counts are computed because an unread pool is
    otherwise invisible, and empty pools are listed WITH their zero — a pool with
    no papers says the topic was scoped and never investigated, which a planner
    needs to know before assuming coverage.
    """
    def _pool(pool: Path) -> tuple[Path, int, str]:
        papers = sorted((pool / "raw").glob("*.md"))
        syn = "synthesis.md" if (pool / "synthesis.md").is_file() else "NO synthesis"
        return pool.relative_to(repo_root), len(papers), syn

    features = [_pool(d) for d in sorted((repo_root / COMPONENT_ROOT).glob("*/research")) if d.is_dir()]
    product = _pool(repo_root / PRODUCT_POOL) if (repo_root / PRODUCT_POOL).is_dir() else None
    has_thesis = (repo_root / PROBLEM_STATEMENT).is_file()
    if not (features or product or has_thesis):
        return ""

    lines = ["--- evidence available to this plan (READ-ONLY, you never write to any of it) ---", ""]
    lines += [
        "**THE CONVENTION, because this workflow is told no file structure and must not guess it:**",
        "every feature under `docs/development/<feature>/` may hold its own `research/` pool —",
        "`raw/` for the papers and `synthesis.md` rolled up. **The pool belonging to the feature you",
        "are planning is your PRIMARY evidence**, and a synthesis is written to be consumed by",
        "exactly this step.",
        "",
    ]
    if features:
        lines.append("**FEATURE POOLS — start here. Counted in code:**")
        lines.append("")
        lines += [f"  {rel}  ({n} papers, {syn})" for rel, n, syn in features]
        lines += [
            "",
            "**A plan that re-derives what its own pool already settled has spent a research cycle",
            "twice, and may reach a different answer the second time.** Cite the paper you relied on.",
            "**Say plainly when the relevant pool is EMPTY rather than assuming the topic was",
            "covered** — a zero above means the topic was scoped and never investigated.",
            "",
        ]
    if product:
        rel, n, syn = product
        lines += [
            "**PROJECT POOL — secondary, for how it all fits together:**",
            "",
            f"  {rel}  ({n} papers, {syn})",
            "",
            "Reach for it when your feature has to cohere with the whole — a cross-cutting decision,",
            "a shared substrate, or a comparable system. **The pool whose name least resembles your",
            "task is the one most likely to hold an already-solved mechanism**; that miss is",
            "documented and it cost a full day.",
            "",
        ]
    if has_thesis:
        lines += [
            f"  {PROBLEM_STATEMENT}   <- the thesis this plan must serve.",
            "",
            "**Read it for WHY this component exists.** A plan that does not serve the thesis is a",
            "well-formed plan for something nobody needed. **READ-ONLY — never edited, and never",
            "proposed for edit from inside a plan.**",
        ]
    return "\n".join([*lines, "--- end evidence available to this plan ---"])


def submit_prompt(pr_number: str | None, label: str) -> str:
    if pr_number:
        return (f"- Stage and commit your changes with message `{label}`\n"
                f"- Push to the PR branch and report PR #{pr_number}'s URL as your FINAL line")
    return (f"- Stage and commit your changes with message `{label}`\n"
            f"- Push the branch and open a PR; report its URL as your FINAL line")

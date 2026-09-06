"""Shared I/O for the planning family — promoted per §10.1 rule 3.

Sits at module level because more than one workflow uses it: `plan_sprint`,
`triage_candidates`, `plan_draft` and `plan_revision` today, `plan_tech_stack`
when it lands. The promotion rule was anticipatory when this file was written and
is now satisfied outright.

THE SPLIT SETTLED WHAT BELONGS HERE, AND RULE 3 DECIDED IT — NOT TASTE. This
docstring used to record `candidate_counts` and
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
  * `candidate_decisions` — one consumer at the split, so it MOVED to
    `plan_sprint_activities`. **It came back when `plan_draft` landed**, which
    holds the same `candidates.md` write grant for the same reason — the shared
    `decision_log_and_reflection` instruction requires every producing run to
    APPEND a proposal there — and therefore owes the same proof that it did not
    write the transferred column. Two consumers, so rule 3 moves it back. The
    round trip is the rule WORKING rather than churn: the helper sat where its
    consumer count put it on both days.
  * `checked_boxes` — one consumer at the split, and its home argued at length
    that a second could never exist: *"every checkbox-bearing file in this tree is
    a sprint plan or a phase doc, and [triage-candidates'] path boundary forbids
    both outright."* True of the workflow it reasoned about, and one workflow too
    general. `plan_draft` WRITES phase docs, so it reaches the surface the
    argument called unreachable. Two consumers, so it is here — and the lesson is
    narrower than "the argument was wrong": **a claim that no second consumer CAN
    exist is a claim about every workflow not yet written.**
  * `new_sprint_sections`, `component_dir` — one consumer each (`plan_project`,
    and nothing else in the tree). MOVED to `plan_project_activities`. They were
    missing from the audit above when it was first written, which made this
    docstring's own rule-3 claim incomplete on the very file that states the
    rule. Counted rather than eyeballed the second time.

`candidate_decisions` was briefly argued to belong elsewhere
anyway, as "the same concern as their neighbours".
[`workflow-scripts.md` § Location](/opt/skyy-net/skyynet-master-planning/standards/workflows/workflow-scripts.md)
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
from collections import Counter
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urldefrag

from .. import assistant_activities as shared
from ..tracked import tracked_items

load_prompt = shared.load_prompt
shared_prompt = shared.shared_prompt
helper_script = shared.helper_script
render = shared.render
run_claude = shared.run_claude
worktree_add = shared.worktree_add
pr_branch = shared.pr_branch
# RE-EXPORTED because the runners in this family alias THIS module as `act`.
# `test_runner_module_attributes_EXIST` is what says so — it caught the
# omission the moment `base_ref` landed in the shared module only, which is
# the same class as the `act.branch_of` NameError that guard was written for.
base_ref = shared.base_ref
default_branch = shared.default_branch
extract_pr_url = shared.extract_pr_url
observe_outcome = shared.observe_outcome
max_turns = shared.max_turns
anchor_task_source = shared.anchor_task_source

# A candidate row, in the eight-column shape `_HEADER` declares:
#   | C-d1uhacwn | title | component | source | `decision` | `size` | `status` | note |
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
# drifting one commit after it was measured is the class C-523klr8n's own Note names.
# The load-bearing claim is that NO cell before the Note contains a pipe; a tally
# of the Note's pipes is decoration and any new row can falsify it.
#
# AND THE CELL COUNT IS NOT WRITTEN HERE EITHER, for the same reason one line up.
# This sentence read "first five cells" through two column additions: it was true
# of the six-column table it was written against, went stale the moment
# `component` landed, and was still stale when `size` did — so the figure has
# been wrong for longer than it was right, in the comment that argues against
# restating figures. `_CONSTRAINED_CELLS` below derives it from `_HEADER`.
_ROW = re.compile(
    r"^\|\s*(C-[0-9a-z]{8})\s*\|([^|\n]*)\|([^|\n]*)\|[^|\n]*\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|",
    re.M)

# The eight-column header, as every candidate table in the file renders it.
# Kept for the MESSAGE it can give — "your table is the old shape" is a better
# sentence than "row C-dhot2cyq's decision is unreadable" when the whole table moved.
# It is NOT the guard; see `_check_shape`.
_HEADER = ("| ID | Candidate | `component` | Source | `decision` | `size` | "
           "`status` | Note |")

# How many cells `_ROW` constrains — every column but the Note. DERIVED from the
# header rather than restated, because the restated version was wrong twice (see
# the `_ROW` comment). Eight columns are bracketed by nine pipes, and the Note is
# the one cell that may hold a pipe of its own, so: pipes, less the two that
# bracket the Note.
_CONSTRAINED_CELLS = _HEADER.count("|") - 2

# Anything that PRESENTS as a candidate row, whatever its id happens to look
# like. `_ROW` insists on `C-[0-9a-z]{8}`; this insists only on the shape a reader
# would call a row, so the two can be compared and a row that fell out of the
# parse can be named instead of vanishing.
# §2's identity shape, checked by the reader — see `candidate_rows`.
_ID_SHAPE = re.compile(r"[A-Z]-[0-9a-z]{8}")

#: The four markers `sprint.md`'s legend defines, used one level down on a
#: phase heading with the same meanings. No fifth state.
_PHASE_MARKER = re.compile(r"(?:✅ COMPLETE|🟡 IN PROGRESS|🟠 PLANNED|🔵 NOT SCHEDULED)\s*$")
#: The labelled line beneath a heading that names the phase doc. Present
#: exactly when a doc exists — MDC measured 4 occurrences against 4 phases in
#: `dev_ui`, and it is in use across ten of their roadmaps with no false hit.
_IMPLEMENTATION = re.compile(r"^\*\*Implementation:\*\*", re.M)

#: THE PRE-RULE-8 CHECKBOX LIST, which `documentation_standard.md` rule 8 binds
#: every reader to accept: *"Tooling that reads phase entries MUST accept the
#: checkbox-list form until the corpus finishes converting."* Rule 4's migration
#: clause makes conversion opportunistic — a roadmap converts when someone is
#: already working in it — so **12 of MDC's 39 roadmaps carry this shape** and
#: will for months.
#:
#: **Two exact anchors, the same standard the heading key is held to:** a
#: checkbox, and a bold name. The phase-doc link is required separately over the
#: entry's own span, which is what keeps an ordinary bolded checklist item out.
#: This is NOT the heuristic that was measured and rejected — *"a heading whose
#: section links a `phaseN_*.md`"* inferred a phase from a citation; these
#: anchors are the notation itself.
_CHECKBOX_PHASE = re.compile(r"^\s*[-*]\s*\[([ x~X])\]\s*\*\*(.+?)\*\*")

#: A phase doc named anywhere in a checkbox entry's span. Required in addition to
#: the box and the bold name — three anchors, no inference.
_PHASE_DOC_REF = re.compile(r"\bphase\d+[\w.-]*\.md\b", re.I)

# THE CLOSED VOCABULARIES. `decision` is the store's own: *"Every candidate ends
# at exactly one of these. There is no fourth"* — `ship` / `requires review` /
# `reject`, plus blank for not-yet-triaged.
#
# `status` IS THE STANDARD'S, NOT THIS MODULE'S, and it changed at the flip.
# The table carried `open` / `closed`; [Tracked Items Standard §4]
# (/opt/skyy-net/skyynet-master-planning/standards/documentation/tracked_items_standard.md) gives
# the candidates store the terminal states **`adopted` · `rejected`**. Those are
# not renamings of `closed` — they say WHICH WAY it closed, which `closed` never
# did, and §4.2 prunes them on different clocks (14 days against six months)
# precisely because a rejection must stay visible so it is not re-proposed.
#
# THE MIGRATION WROTE THE STANDARD'S VALUES AND THIS TUPLE STILL HELD THE
# TABLE'S, so the first real read of the store raised on its first item. Caught
# by `_raise_on_foreign_cell` doing exactly its job — the vocabulary check is
# what noticed that two definitions of `status` had come apart.
_DECISIONS = ("", "ship", "requires review", "reject")
_STATUSES = ("", "open", "adopted", "rejected")
# `size` is `triage-candidates`'s SECOND ruling and it is asked ONLY of a `ship`.
# Blank is the honest value everywhere else: a rejected candidate has no size, and
# a shipped row filed before this column existed is UNSIZED rather than wrongly
# sized — `plan-candidates` skips those and says so, which makes the backfill
# self-healing instead of a migration.
_SIZES = ("", "feature", "phase", "checkboxes")

# THE COLUMNS A RUN CAN BE HELD TO, WRITTEN ONCE. Each of these has a reader
# (`candidate_<column>s`) and a comparator (`<column>s_this_run_had_no_right_to`)
# below, and every message here that has to enumerate them interpolates this
# rather than restating it.
#
# IT EXISTS BECAUSE THE HAND-KEPT COPIES DRIFTED THE MOMENT `size` LANDED, three
# of them at once — `_raise_on_duplicate_ids`' operator message and its
# docstring, and `CandidateRow`'s. All three named `decision`, `status` and
# `component`, all three were true of the seven-column table, and none of them
# went red when a fourth guarded column arrived. That is the same class as the
# cell count two comments up, and it has the same answer: state it in one place
# that something else derives from, rather than in four places a reviewer has to
# find. `test_the_GUARDED_COLUMN_LIST_matches_the_comparator_family` is what
# holds it — the next column with a reader and a comparator fails until it is
# named here, and naming it here moves every message at once.
_GUARDED_COLUMNS = ("decision", "size", "status", "component")

_BLANK = ("", "—", "-")


class CandidateRow(NamedTuple):
    """One parsed row, NAMED — because the tuple grew and callers index it.

    It was a bare `(id, decision, status)` triple until `component` was added
    between `Candidate` and `Source`. Widening a positional tuple silently
    re-points every unpacking site by one, and the sites reading `_GUARDED_
    COLUMNS` are AUTHORIZATION GUARDS — each `candidate_<column>s` reader proves
    a run did not write a column it does not own. A guard that compares the wrong
    field still returns a clean dict and still reports a clean run, so the
    failure would be invisible in exactly the place invisibility costs most.
    Named access makes the same mistake a crash instead.

    NO COUNT OF THOSE SITES IS WRITTEN HERE. This sentence said "three of the
    sites" from the day it was written until `size` made it four, and the claim
    it is making is the PROPERTY — a guard reading the wrong field is silent —
    which needs no denominator.
    """

    id: str
    title: str
    component: str
    decision: str
    size: str
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
    """Every item in the candidates STORE, normalised. One parse, one place.

    `candidates_path` is `tracked/candidates/` — a DIRECTORY, one file per item.
    It was a markdown table until 2026-08-26; see the module note on the flip.

    `missing_hint` lets each caller say what the absent store costs IT, without a
    second copy of the reader travelling with the sentence.

    THE SHAPE IS CHECKED BEFORE ANY ROW IS RETURNED, and it raises rather than
    returning what it can. See `_check_shape`: every way the store's real shape
    can depart from the assumed one lands in the same place — an item that reads
    as TRIAGED without anybody having ruled it, or an item that is simply not
    there. An empty-ish result here is not a safe degradation; it is a
    clean-looking answer over a working set that has quietly lost items.
    """
    if not candidates_path.is_dir():
        raise FileNotFoundError(
            f"candidates store not found: {candidates_path}. It is a DIRECTORY, "
            f"one file per item, per Tracked Items Standard §1. {missing_hint}")

    rows: list[CandidateRow] = []
    unreadable: list[tuple[str, str]] = []
    _filed_of: dict[str, str] = {}
    for path in sorted(candidates_path.glob("*.md")):
        try:
            fields, _ = tracked_items.parse(path)
            # THE ID IS CHECKED HERE, NOT ONLY IN THE STORE'S OWN SUITE, and the
            # reason is what the flip would otherwise have dropped. Under the
            # table, an id that was not `C-` plus eight base36 characters did not
            # match the row regex AT ALL, so the row was absent from every reader
            # and `_raise_on_unparsed_rows` caught it. A store has no regex to
            # miss: a file with `id: nonsense` parses perfectly and joins the
            # working set. Without this the flip would have RETIRED a live guard
            # by accident rather than by argument.
            #
            # THE FILENAME MUST AGREE TOO (§2: the filename IS the id). A file
            # copied and edited without its `id` changed reads as its neighbour
            # to every dict keyed by id.
            cid = fields.get("id", "")
            if not _ID_SHAPE.fullmatch(cid):
                raise ValueError(
                    f"id {cid!r} is not a prefix plus eight lowercase base36 "
                    f"characters (Tracked Items Standard §2)")
            if cid != path.stem:
                raise ValueError(
                    f"id {cid!r} disagrees with its filename {path.stem!r}; the "
                    f"filename IS the id (§2)")
            rows.append(CandidateRow(
                fields["id"],
                normalise_cell(fields.get("title", "")),
                normalise_cell(fields.get("component", "")),
                normalise_cell(fields.get("decision", "")),
                normalise_cell(fields.get("size", "")),
                normalise_cell(fields.get("status", "")),
            ))
            _filed_of[cid] = fields.get("filed", "")
        except (ValueError, KeyError) as exc:
            unreadable.append((path.name, str(exc)))

    _check_shape(candidates_path, unreadable, rows, missing_hint)

    # ORDER IS FILED-DATE THEN ID, AND IT IS A DECISION RATHER THAN A DEFAULT.
    # The table carried filing order for free: a row's position in the file WAS
    # the order it was filed in. A store has no positions, and `glob` yields
    # filesystem order, so an unsorted read would hand every consumer a
    # different sequence on a different machine — and two of them render lists a
    # human reads.
    #
    # FILED-THEN-ID rather than id alone, because `filed` is the only field that
    # carries what position used to: the date the candidate was surfaced. Id is
    # the tiebreak and is arbitrary BY DESIGN (§2 mints at random), which is
    # exactly what a tiebreak wants — stable, and carrying no accidental meaning.
    #
    # WHAT THIS CANNOT RECOVER, stated rather than glossed: the 119 items
    # migrated on 2026-08-26 all carry that date, so within them the original
    # table order is GONE and the id tiebreak decides. Nothing downstream ranks
    # on it — triage sorts by `count` (§3.1) — but a reader comparing today's
    # order to the old file will not find them the same, and that is why it is
    # written here instead of being discovered.
    rows.sort(key=lambda r: (_filed_of.get(r.id, ""), r.id))
    return rows


def _check_shape(path: Path, unreadable: list[tuple[str, str]],
                 rows: list[CandidateRow], missing_hint: str) -> None:
    """Raise unless the store's real shape is the one the reader assumes.

    KEYED ON THE CLASS, NOT ON A SPELLING OF IT. Every way the shape has departed
    or can depart produces the SAME failure — an item that leaves the untriaged
    working set without anybody ruling it, while `triage-candidates` reports a
    complete pass — so the check asks about the failure rather than about the
    departures.

    THE THREE QUESTIONS SURVIVED THE FLIP FROM A TABLE TO A STORE, because they
    were never about markdown. A file that will not parse is exactly what an
    unparsed ROW was; two files claiming one id is what two rows claiming one id
    was; a cell outside the closed vocabulary is unchanged. What went away is the
    column-shift family — a store has no columns to shift — and nothing replaced
    it, which is a genuine reduction rather than a gap:

      * `_raise_on_unparsed_rows`  — is the population the readers see the
        population the store holds?
      * `_raise_on_duplicate_ids`  — the same question one altitude down, and it
        needs its own helper because a SET answers neither on its own.
      * `_raise_on_foreign_cell`   — does every item's `decision`, `size` and
        `status` fall in the closed vocabulary the store admits?

    ONE CASE PER HELPER, RATHER THAN ONE LIST IN ONE DOCSTRING, and that is the
    fix for a defect this docstring itself carried: it opened *"Three ways the
    shape has departed"* over FOUR bulleted cases, because the fourth was added
    without the tally being re-counted. A list that lives in one docstring per
    case cannot go out of step with itself.
    """
    _raise_on_unparsed_rows(path, unreadable, missing_hint)
    _raise_on_duplicate_ids(path, rows, missing_hint)
    _raise_on_foreign_cell(path, rows, missing_hint)


def _raise_on_unparsed_rows(path: Path, unreadable: list[tuple[str, str]],
                            missing_hint: str) -> None:
    """Every `*.md` in the store must actually have parsed into an item.

    A FILE THE READER CANNOT PARSE IS A CANDIDATE THAT DOES NOT EXIST for every
    consumer downstream — absent from the untriaged working set, from every
    authorization snapshot, and from the deletion check — and every guard reads
    green over it. Skipping it would be the silent shrink this whole check
    family exists to prevent, so an unreadable file stops the run and names
    itself. Reachable ways to land here: no frontmatter block, a frontmatter
    line that is not `key: value`, or a missing `id`.
    """
    if unreadable:
        listed = "; ".join(f"{name} ({why})" for name, why in unreadable)
        raise ValueError(
            f"{path} holds {len(unreadable)} file(s) the item parser cannot "
            f"read: {listed}. An item opens with a frontmatter block carrying "
            f"`id`, per Tracked Items Standard §3. A file the parser cannot see "
            f"is absent from the untriaged working set, from every authorization "
            f"snapshot, and from the deletion check — every guard reads green "
            f"over it. {missing_hint}")


def _raise_on_duplicate_ids(path: Path, rows: list[CandidateRow],
                            missing_hint: str) -> None:
    """No id may name two items — the door that has actually opened.

    Every reader here is a dict keyed by id, so the second item's fields
    silently overwrite the first's — every column in `_GUARDED_COLUMNS`, which is
    where the list is kept rather than restated here — and one of the two
    candidates stops existing for every consumer.

    THE FILENAME IS THE ID (§2), so the filesystem now refuses the commonest way
    to land here, and that is precisely why this check is worth keeping rather
    than retiring: what it catches now is an item whose FRONTMATTER `id`
    disagrees with a neighbour's — a file copied and edited without its id being
    changed. A guard whose failure mode has become rare is not a guard whose
    value has become zero; it is the one catching the case nobody is watching for.
    """
    seen: dict[str, int] = {}
    for row in rows:
        seen[row.id] = seen.get(row.id, 0) + 1
    dupes = sorted(i for i, n in seen.items() if n > 1)
    if dupes:
        raise ValueError(
            f"{path} holds {len(dupes)} id(s) naming more than one item: "
            f"{', '.join(dupes)}. Every reader here is keyed by id, so one "
            f"item's {', '.join(f'`{c}`' for c in _GUARDED_COLUMNS)} silently "
            f"overwrites the other's and one candidate stops existing. Ids are "
            f"RANDOM and the filename IS the id, so a duplicate means a "
            f"frontmatter `id` was COPIED rather than allocated. {missing_hint}")


def _raise_on_foreign_cell(path: Path, rows: list[CandidateRow],
                           missing_hint: str) -> None:
    """`decision`, `size` and `status` must hold values the store admits.

    THIS IS THE ARM THAT COVERS SHAPES NOBODY HAS THOUGHT OF YET, which is why it
    does not name any of them. It asks whether the value reads as something the
    store admits, so a future departure fails here rather than being discovered
    by a later pass.

    ALL THREE RULED FIELDS, NOT TWO. `size` was added and left out of this
    condition once already, so the one field a stalled migration displaced text
    INTO was the one field that accepted anything. Widening the condition is what
    makes `_SIZES` load-bearing rather than documentation.

    WHAT THE FLIP REMOVED. Under the table, the reachable cause was a COLUMN
    SHIFT — a seven-column table putting `status` into `size`, or a pipe inside a
    cell moving every field sideways. A store has no columns and no cell
    boundaries, so that entire family is gone. What remains is a hand-edited
    value: a `decision` of `shipped`, a `status` of `done`. The check is
    unchanged because it never asked about markdown.
    """
    for row in rows:
        if (row.decision in _DECISIONS and row.size in _SIZES
                and row.status in _STATUSES):
            continue
        raise ValueError(
            f"{path} item {row.id} carries decision={row.decision!r} "
            f"size={row.size!r} status={row.status!r}, and the store admits no "
            f"such value — `decision` is one of {_DECISIONS}, `size` one of "
            f"{_SIZES} and `status` one of {_STATUSES}. An item holding anything "
            f"else reads as triaged, drops out of the untriaged working set, and "
            f"`triage-candidates` reports a complete pass over a candidate "
            f"nobody ruled. {missing_hint}")


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
    produces a wrong brief, which `research-refine` reads and can hold on, whereas
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
    "a later process" — `plan-draft`, or the build that completes the item —
    and both prompts list it under MAY NOT.

    It is here rather than in one workflow's folder because BOTH snapshot it, for
    the same reason and against the same file. The argument that built the
    `decision` guard reaches this column unchanged: `status` is the cell
    immediately beside the one each run is legitimately reading, and *"we have
    decided to do this"* is one plausible step from *"this is handled"*.
    """
    return {row.id: row.status for row in candidate_rows(candidates_path, missing_hint=(
        "Without it there is no `status` column to hold anything to."))}


def candidate_decisions(candidates_path: Path) -> dict[str, str]:
    """Every row's `decision`, normalised, keyed by id — `triage-candidates`' column.

    PROMOTED HERE WHEN IT EARNED A SECOND CONSUMER, which is the whole of the
    test. It lived in `plan_sprint_activities` while `plan_sprint` was the only
    workflow proving it had not written the transferred column; `plan_draft`
    holds the same `candidates.md` write grant, for the same reason — the shared
    `decision_log_and_reflection` instruction requires every producing run to
    APPEND a proposal there — and therefore owes the same proof. Two consumers,
    so rule 3 moves it, and rule 3 is *"consumer count decides, never taste"*.

    THE AUTHORITY TRANSFER, ENFORCED RATHER THAN ASSERTED. `decision` was
    `plan-sprint`'s until triage became its own workflow; it is now
    `triage-candidates`'s alone. Prose in nine documents says so, and prose is not
    a mechanism: both consumers READ this file, both have write access to it in
    their worktree, and a model that has just planned a candidate's whole
    component is one plausible step from recording that in the column beside it.

    So each snapshots this before its run and compares after. Same discipline as
    `candidate_counts`: OBSERVE what the run wrote, never ask it what it wrote.

    Normalised via `normalise_cell`, so a row reformatted from `` `ship` `` to
    `ship` does not read as a ruling changed. The comparison must fire on MEANING
    rather than markup, and on the SAME meaning the counter sees: two
    hand-written normalisations had already drifted apart once.
    """
    return {row.id: row.decision for row in candidate_rows(
        candidates_path,
        missing_hint="Without it there is no `decision` column to hold anything to.")}


def candidate_sizes(candidates_path: Path) -> dict[str, str]:
    """Every row's `size`, normalised, keyed by id — `triage-candidates`' SECOND column.

    THE SECOND RULING TRIAGE MAKES, and it is asked only of a `ship`. `decision`
    answers *is this worth promoting from a candidate to committed work*; this
    answers *how big is it* — a `feature`, a `phase` inside an existing one, or
    `checkboxes` added to a phase that already exists.

    WHY IT NEEDS A COLUMN RATHER THAN AN INFERENCE. `plan-candidates` used to
    derive size from a proxy: if the named component's directory did not exist,
    the candidate must be a new component. That is true of a feature and wrong of
    the other two — a phase-sized candidate whose component happens to be new
    scaffolds a whole component, and a checkbox-sized one has no expressible form
    at all. A proxy that is right for one of three cases reads as a decision and
    is an accident.

    Guarded exactly like `decision`: snapshotted either side of every run whose
    prompt puts this column in its `You MAY NOT` table, and compared. That is
    `plan-draft` and `plan-refine`, and it is NOT the same set as "every run
    holding a write grant on this file" — `triage-candidates` holds one and is
    the run that RULES this column, so it is guarded on `status` and `component`
    and deliberately not on `size`. Same reason as `decision`, too: a run that
    has just planned a component is one plausible step from recording a size
    beside it.
    """
    return {row.id: row.size for row in candidate_rows(
        candidates_path,
        missing_hint="Without it there is no `size` column to hold anything to.")}


def decisions_this_run_had_no_right_to(before: dict[str, str],
                                       after: dict[str, str]) -> list[str]:
    """Ids whose `decision` changed on a row that already existed. Only triage may.

    IT RODE THE `status` COMPARATOR UNTIL 2026-08-20, in both planning workflows,
    and the family's own design is the reason that was wrong rather than merely
    untidy. `components_this_run_had_no_right_to` states it: the bodies are
    written out instead of shared *"because the two columns are prohibited for
    DIFFERENT reasons and each docstring is the place that reason is recorded"*.
    `decision` had no such place — its reason lived in the workflows' raise
    messages and nowhere in this module — and any specialisation of the status
    comparator would silently have retargeted the `decision` guard in two
    workflows at once. Two docstrings here already treat it as a first-class
    member (`candidate_sizes` says *"Guarded exactly like `decision`"*;
    `statuses_this_run_had_no_right_to` says row deletion *"is already an offence
    under the `decision` guard"*) and both pointed at a guard with no comparator.

    ONLY pre-existing rows are judged, for the reason `statuses_this_run_had_no_
    right_to` states: a row this run APPENDED is a proposal placed under the
    shared instruction in `decision_log_and_reflection.md`, which prescribes a
    BLANK `decision` — so a new row's `decision` is prescribed by that rule
    rather than by this guard. Row deletion is `act.ids_deleted`, which both
    callers check AHEAD of every comparator precisely because a row that is
    simply gone is in neither key set here.

    `plan_sprint._rulings_this_run_had_no_right_to` reads like a wider version of
    this rule — its body also refuses a NEW row arriving already ruled — and it
    is UNCALLED. Nothing in the tree invokes it: it is residue of the 2026-08-19
    rebuild, which dropped that workflow's `candidates.md` grant along with the
    job that needed it and left the comparator behind. The boundary it once held
    is discharged by that workflow's `FORBIDDEN_PATHS ^docs/standards/`, which
    needs no column reader at all. Said here rather than left out because the two
    names read as one family, and a reader meeting that one has no way to tell it
    fires nothing. Whether to delete it or wire it is an authorization ruling and
    not this module's to make.
    """
    return sorted(cid for cid in before.keys() & after.keys()
                  if before[cid] != after[cid])


def sizes_this_run_had_no_right_to(before: dict[str, str],
                                   after: dict[str, str]) -> list[str]:
    """Ids whose `size` changed on a row that already existed. Only triage may.

    ONLY pre-existing rows are judged, for the reason `statuses_this_run_had_no_
    right_to` states: a row this run APPENDED is a proposal placed under the
    shared instruction, and its own cells are prescribed by that rule rather than
    by this guard. A filer appending a row leaves `size` BLANK — sizing is a
    ruling and the filer is not the one making it.
    """
    return sorted(cid for cid in before.keys() & after.keys()
                  if before[cid] != after[cid])


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


# A completed checkbox in any of the markdown dialects this tree writes.
_CHECKED = re.compile(r"^\s*[-*]\s*\[[xX]\]\s*(.+?)\s*$", re.M)

#: A checked item's IDENTITY, so a box is tracked by WHICH item it is rather than
#: by the whole line. A sprint bullet leads with its bolded name; that name is
#: what makes it the same item across an edit.
#:
#: WITHOUT THIS, EDITING A CHECKED BULLET READS AS TWO FLIPS. `plan-sprint`
#: appended `· **~34h**` to two already-checked bullets on PR #145 and the guard
#: reported *"flipped 4 completion checkbox(es)"* — the same two items, counted
#: once as ERASED under their old text and once as TICKED under their new text.
#: Neither box moved: `- [x]` before, `- [x]` after.
#:
#: The guard's own comment had ruled this acceptable — *"a reworded box was never
#: legitimate, so symmetry adds no new false positive"* — which was true when
#: `plan-sprint` wrote no per-bullet figures. It writes them now. **Whether it
#: SHOULD is a live house-style question for the operator; conflating it with
#: fabricating a completion is a separate defect and this is that fix.**
_ITEM_ID = re.compile(r"\*\*(.+?)\*\*")


def checked_boxes(path: Path) -> Counter:
    """The completed checkboxes in a planning file, counted by their text.

    A CHECKBOX MEANS *SHIPPED AND VALIDATED*, and no workflow that reads this has
    validated anything — `plan-sprint` places work decided elsewhere, and
    `plan-draft` writes the plan for work nobody has started. The Documentation
    Standard's § *Completion checkboxes* rule is the authority and it is exact:
    a dispatch may flip a box **for work it completed in that PR**, and *built is
    not proven*. Neither of these workflows completes any.

    PROMOTED HERE WHEN A SECOND CONSUMER ARRIVED, and this module's previous home
    for it argued at length that one never could: *"every checkbox-bearing file in
    this tree is a sprint plan or a phase doc, and [triage-candidates'] path
    boundary forbids both outright."* That was true of the workflow it was
    reasoning about and it generalised one workflow too far. `plan-draft` WRITES
    phase docs — checkbox-bearing by construction, since a roadmap phase entry is
    3-5 completion criteria — so the surface the argument called unreachable is
    the new consumer's primary output. The lesson is narrower than "the argument
    was wrong": a claim that no second consumer *can* exist is a claim about
    every workflow not yet written.

    THE PARAMETER IS `path`, NOT `sprint_path`, and the rename is the promotion.
    `plan-draft` hands it a `roadmap.md` and each phase doc in turn; a parameter
    named for one caller's file is how a shared helper acquires a phantom scope.

    COUNTED BY TEXT rather than diffed by line number, because a caller may
    legitimately re-order sections: a positional comparison would fire on a box
    that simply moved. Adding an UNCHECKED item is legitimate and invisible here;
    adding a checked one is not, and shows up as a new entry. A Counter rather
    than a set so that ticking the second of two identically worded items is
    still seen.

    A missing file is an empty Counter, and that reading is deliberate and must
    not change: it is what lets a tree with no plan yet run at all. THIS IS
    THEREFORE NOT AN EXISTENCE CHECK, and reading it as one is how the sprint plan
    came to be deletable — an empty Counter after a deleted file compares
    identically to an empty Counter after an untouched empty one.
    `grants_that_vanished` is the existence check, and it runs ahead of this one
    for exactly that reason.

    The COMPARISON is symmetric even though this reader is not: a caller takes the
    difference in both directions, because "flip a checkbox" is a prohibition on
    erasing a tick as much as on adding one.
    """
    if not path.exists():
        return Counter()
    # KEYED ON IDENTITY, NOT ON THE WHOLE LINE — see `_ITEM_ID`. An item with no
    # bolded name falls back to its full text, which is the pre-existing
    # behaviour and is right for a phase doc's completion criteria: those are
    # sentences, and the sentence IS the identity.
    def _identity(text: str) -> str:
        m = _ITEM_ID.search(text)
        return m.group(1) if m else text

    return Counter(_identity(t) for t in _CHECKED.findall(path.read_text()))


# What a phase doc might be NAMED, which is deliberately wider than what one may
# be named. This answers *which files are phase docs*, never *which files may
# this run write* — the grammar that judges a NEW name lives in
# `plan_draft_activities._PHASE_FILE`, beside the only workflow that writes one.
#
# THE SUFFIX IS PART OF THE QUESTION. `^phase` alone admits `phase_notes.txt` and
# `phase9_x.md.bak`, and two consumers then read those as phase docs: a
# deliverable guard that a single stray `.txt` satisfies, and a counted block
# handed to a model labelled *"authoritative — do not recount"*. Both reproduced
# by execution before this was tightened.
#
# CASE-INSENSITIVE ON BOTH HALVES: a legacy `PHASE3.MD` is a phase doc whoever
# spelled it, and its disappearance is an offence just the same.
# `\A…\Z` AND NOT `^…$`: `$` also matches immediately BEFORE a trailing
# newline, which a POSIX filename may end with, so the anchor that refuses
# `phase9_x.md.bak` above would have admitted `phase9_x.md\n`. Swept from
# `modules/journal/`, where the same spelling let a digest carrying a newline
# through the gate that derives an on-disk path.
_LOOKS_LIKE_A_PHASE = re.compile(r"\Aphase.*\.md\Z", re.I)


def phase_docs(component: Path) -> dict[str, str]:
    """Every phase-doc-shaped file directly in the component dir, name -> content hash.

    PROMOTED HERE WHEN `plan-refine` LANDED, per §10.1 rule 3 — *consumer count
    decides, never taste*. `plan-draft` asks it *did a phase doc VANISH?*, which
    is what a rename or a renumber looks like from outside; `plan-refine` asks it
    *what am I reading, and how many phases must I size?*. Two consumers, so the
    definition sits here and `plan_draft_activities` reaches it by alias. A
    second hand-written `phase*.md` sweep is precisely the drift `normalise_cell`
    exists to record — and the two questions are far enough apart that the copies
    would have looked reasonable side by side.

    KEYED BY FILENAME, HASHED BY CONTENT, and both halves are load-bearing. The
    key is what `ids_deleted` compares, so a rename shows up as a disappearance.
    The value lets a caller tell a doc that was rewritten from one left alone
    without holding two copies of the tree.

    A MISSING COMPONENT DIRECTORY IS AN EMPTY MAP, NOT AN ERROR — a component may
    hold nothing but `research/`, which is what `plan-candidates` leaves behind.

    Files only, and only at the top level: `research/raw/phase_something.md` is a
    research paper that happens to be named like a phase.
    """
    if not component.is_dir():
        return {}
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(component.iterdir())
            if p.is_file() and _LOOKS_LIKE_A_PHASE.match(p.name)}


# An hour ESTIMATE, in the three spellings a plan can carry one. The
# Documentation Standard's own worked example is `### 1-2. DAS Phase 1 +
# Version-of-Record Phase A (~30 hrs)`, which the first two alternatives catch.
#
# ONE PATTERN, TWO OPPOSITE CONSUMERS, WHICH IS EXACTLY WHY IT IS SHARED.
# `plan-draft` uses it as a PROHIBITION — an author sizing their own
# decomposition is defending it — and `plan-refine` uses it as the DELIVERABLE it
# must produce. Two copies of this regex would let the write half forbid a shape
# the read half does not produce, or the read half satisfy itself with a shape
# the write half would have rejected, and neither divergence shows in a diff.
#
# ALTERNATIVES (b) AND (c) REQUIRE AN ESTIMATE MARKER. ALTERNATIVE (a) DOES NOT
# — the tilde is its only discriminator, and that is weaker than it reads. A
# tilde-figure inside ordinary prose matches: `**NOT SIZED. The 2026-08-19 figure
# of ~24 hours ... has been removed**` parsed as an estimate of 24 h, so a phase
# declaring itself unsized read as sized. `_NOT_SIZED` below is the fix; widening
# (a) is not, because the Documentation Standard's own worked example puts a bare
# `(~30 hrs)` in a heading with no label anywhere near it.
#
# (This comment previously asserted that every alternative required a marker.
# It was describing (b) and (c) and had never been checked against (a).)
#
# THE PERIOD IS ALLOWED AFTER THE ABBREVIATION `est` AND NOWHERE ELSE, and the
# narrowness is the fix rather than a nicety. `[^.\n]` is what keeps the label
# and the figure inside ONE SENTENCE, so *"the estimate. It took 3 hours"* is
# prose. A blanket `\.?` after the whole label group — which this pattern shipped
# with — handed that property straight back, because the optional period consumed
# a genuine sentence-ending full stop. Reproduced by execution against the
# shipped pattern.
#
# The residual limit is stated rather than hidden: an estimate whose label sits
# more than 24 non-period characters from its figure is not caught, and neither
# is one written in a fourth spelling.
HOUR_ESTIMATE = re.compile(
    r"""
      ~\s*(?P<a>\d+(?:\.\d+)?)\s*(?:h|hrs?|hours?)\b        # ~30 hrs, ~8h
    | \(\s*(?P<b>\d+(?:\.\d+)?)\s*(?:h|hrs?|hours?)\s*\)   # (30 hrs)
    | (?: \best\.?[:\s]                                      # Est. 2.5 hours, Est: 8h
        | \b(?:estimate[sd]?|sizing|effort)\b\s*:?  )         # Estimate: 8 hours
      [^.\n]{0,24}?(?P<c>\d+(?:\.\d+)?)\s*(?:h|hrs?|hours?)\b
    """,
    re.I | re.X,
)
# THE NUMBER IS CAPTURED, and it was not until 2026-08-19. This pattern existed
# only to DETECT that `plan-draft` had written an hour — a thing it is
# forbidden to do — so no caller needed the value and `Est: 8 hours` (with a
# colon) silently failed to match. Summing makes both matter: an estimate the
# pattern misses does not raise, it lowers the total, and a total that is quietly
# short is worse than one that is absent because nothing says it is wrong.


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
    out = shared.run_bounded(argv, cwd=worktree)
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
    deleting `/opt/skyy-net/skyynet-master-planning/development/sprints.md` returned a PR URL and a green run, and
    so did `git mv /opt/skyy-net/skyynet-master-planning/development/sprints.md notes.md` — the operator's
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
    lines: list[str] = []

    # Components sit one level below their edge bucket; `common/reviews/` is a
    # records directory, not a component.
    def _is_component(d: Path) -> bool:
        """The two shapes the corpus uses: roadmap+phases, or a single one-pager.

        Filtering on SHAPE rather than on depth is what keeps the edge BUCKETS
        (`development/edge-assistant/`) out of the list without hardcoding their
        names — a new edge is handled on the day it is created.
        """
        return d.is_dir() and ((d / "roadmap.md").is_file()
                               or (d / f"{d.name}.md").is_file())

    comps = sorted({d for depth in ("*", "*/*")
                    for d in (tree / COMPONENT_ROOT).glob(depth)
                    if _is_component(d)})
    lines.append("**Existing components** (a candidate may belong inside one rather than needing its own sprint section):")
    for c in comps:
        syn = c / "research" / "synthesis.md"
        mark = " — **HAS COMPONENT RESEARCH**: `" + str(syn.relative_to(tree)) + "`" if syn.exists() else ""
        lines.append(f"  - `{c.relative_to(tree)}/`{mark}")

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

    # `gh_attempt`, NOT `subprocess.run`: this block degrades to a COULD-NOT-BE-READ
    # note rather than raising, so it wants the retry without the raise — and a
    # planning run that silently loses its open-issue list to one 503 plans
    # against a repo it believes has no tracked work.
    r = shared.gh_attempt(["issue", "list", "--state", "open", "--limit", "50",
                           "--json", "number,title"], tree)
    # THE DECODE IS GUARDED, because `gh_attempt` returns UNJUDGED and a zero
    # exit is not a promise that the body parsed. That is the shape `gh_json`'s
    # docstring records as having crashed a parent build loop at zero attempts,
    # and an unguarded `json.loads` here would kill a planning dispatch on a
    # truncated reply — the same run this block's else-branch exists to keep
    # alive when the read fails outright.
    #
    # AND THE SHAPE IS GUARDED TOO, WHICH IS A SEPARATE FACT. A guard that
    # catches only `JSONDecodeError` says "it parsed" and lets the caller assume
    # "it is a list". `{"message": "Not Found"}` parses; `len()` then succeeds,
    # `for i in issues` iterates its KEYS, and `i["number"]` raises `TypeError` —
    # the planning dispatch dies on the third way of not getting an issue list,
    # four lines below the comment promising all of them reach the same note.
    # `ci_verdict` and `wait_for_ci` in `assistant_activities` already spell this
    # `isinstance(..., list)`; this block was the one sibling that did not.
    issues = None
    if r.returncode == 0:
        import json
        try:
            issues = json.loads(r.stdout)
        except json.JSONDecodeError:
            issues = None
        if not isinstance(issues, list):
            issues = None
    if issues is not None:
        lines.append(f"\n**Open issues** — {len(issues)}. **A candidate matching one of these is ALREADY tracked**; "
                     f"say so and do not create a second home for it:")
        lines += [f"  - #{i['number']} {i['title']}" for i in issues]
    else:
        lines.append("\n**Open issues: COULD NOT BE READ.** Do not assume there are none — "
                     "say in your report that this check did not run.")

    return "\n".join(lines)


PROBLEM_STATEMENT = Path("standards/architecture/problem-statement.md")
PRODUCT_POOL = Path("research")
# No `docs/` level: the planning corpus lives in `skyynet-master-planning`, whose
# layout mirrors MDC's — `standards/` and `development/` sit at the repo root.
# `PROBLEM_STATEMENT` and `PRODUCT_POOL` above were migrated with the corpus and
# this constant was not, which left the plan family half-pointed at a tree that
# no longer exists while the two neighbouring constants resolved correctly.
COMPONENT_ROOT = Path("development")


def evidence_block(tree: Path) -> str:
    """POINT a planning run at the thesis and the pools, PRIMARY first.

    `tree` IS THE TREE THE RUN CAN SEE, NOT NECESSARILY THE REPO, and the
    parameter is named for that the way `existing_work`'s is — for the same
    reason and after the same near-miss. It was `tree`, and a second caller
    duly passed one: `plan-draft` runs inside `plan-project` immediately after
    a component was scaffolded and researched IN THE WORKTREE, so a repo-anchored
    enumeration would list every pool except the one the run is planning from,
    and report having seen them all. Caught by the repo-root census rather than
    by review, which is the argument for the census.

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
        return pool.relative_to(tree), len(papers), syn

    # TWO DEPTHS, UNIONED — same reason as `research_activities`: components are
    # bucketed by edge (`development/edge-assistant/<c>/`), so a single-level glob
    # finds the BUCKETS and reports every feature pool as absent. A plan run that
    # cannot see the research is the failure this evidence block exists to prevent.
    features = [_pool(d) for d in sorted(
        {p for depth in ("*/research", "*/*/research")
         for p in (tree / COMPONENT_ROOT).glob(depth) if p.is_dir()})]
    product = _pool(tree / PRODUCT_POOL) if (tree / PRODUCT_POOL).is_dir() else None
    has_thesis = (tree / PROBLEM_STATEMENT).is_file()
    if not (features or product or has_thesis):
        return ""

    lines = ["--- evidence available to this plan (READ-ONLY, you never write to any of it) ---", ""]
    lines += [
        "**THE CONVENTION, because this workflow is told no file structure and must not guess it:**",
        "every feature under `development/<edge>/<feature>/` may hold its own `research/` pool —",
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
        # THE BODY UPDATE IS THE THIRD INSTRUCTION, AND IT WAS MISSING. This
        # path emitted commit-and-push only, so every child dispatched with
        # `--pr` — every loop-back, every correction — left the PR body exactly
        # as pass 1 wrote it while the branch accumulated commits. MEASURED on
        # PR #145: 34 commits under a pass-1 body, and FOUR of the eight findings
        # review-pr held on were the body contradicting the diff, the tree, or
        # itself. `plan_revision/prompts/update_pr.md` has carried this line all
        # along; the shared helper its siblings use did not.
        return (f"- Stage and commit your changes with message `{label}`\n"
                f"- Push to the PR branch and report PR #{pr_number}'s URL as your FINAL line\n"
                f"- **Update the PR body so it describes the branch as it now stands** — it was\n"
                f"  written for an earlier pass and the branch has moved. A reviewer and the\n"
                f"  merged record both read it. Keep it a scannable index of the diff")
    return (f"- Stage and commit your changes with message `{label}`\n"
            f"- Push the branch and open a PR; report its URL as your FINAL line")

def plan_docs(component: Path) -> dict[str, str]:
    """EVERY top-level markdown file in the component — the write grant's own scope.

    THE SCOPE OF THE GUARDS MUST BE THE SCOPE OF THE GRANT, and this reader is
    what makes those two the same set. The grant is `<component>/[^/]+\\.md$` —
    any markdown file sitting directly in the component — while `phase_docs`
    above answers a narrower question (*which files are phase docs*) by matching
    `^phase`. Three guards were built on the narrow reader and inherited its
    scope, which left the grant wider than anything that inspected it:

      * a NEW `the_run_bag.md` — a phase doc with the number dropped, which is
        the FIRST failure mode the standard names and the likeliest one — does
        not start with `phase`, so it was invisible to `malformed_phase_docs`
        while the row it violates claims that function observes it;
      * an hour estimate or a pre-ticked checkbox written into any top-level file
        other than `roadmap.md` or a `phase*` one was scanned by nothing.

    Both are closed by asking the grant's question instead of the phase reader's.
    `roadmap.md` is the one legitimate non-phase name and the callers below say
    so explicitly rather than this reader excluding it — the deletion and
    checkbox guards want it in, and only the naming guard wants it out.

    A MISSING COMPONENT DIRECTORY IS AN EMPTY MAP, for the same reason
    `phase_docs` gives: `plan-candidates` creates the folder and the seed and
    nothing else, so a first-time plan legitimately starts from nothing.
    """
    if not component.is_dir():
        return {}
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(component.iterdir())
            if p.is_file() and p.suffix == ".md"}

def plan_boxes(component: Path) -> Counter:
    """Every completion checkbox in the component's PLAN, as one Counter.

    THE ROADMAP AND EVERY OTHER TOP-LEVEL DOC TOGETHER, because the prohibition
    is about the plan and not about a file. `checked_boxes` reads one path;
    this workflow's output is one roadmap plus N phase docs, and a guard scoped
    to `roadmap.md` alone would be blind to a phase doc shipping with its steps
    pre-ticked — which is the likelier mistake, since a phase doc is where the
    implementation checklist lives.

    SCOPED BY `plan_docs`, i.e. by the write grant, so it cannot be narrower than
    what the run may write. It sat in the workflow module keyed on a hand-written
    `name == "roadmap.md" or name.lower().startswith("phase")`, which was a
    second spelling of `_LOOKS_LIKE_A_PHASE` in a second file with nothing
    forcing the two to move together — and it carried the same scope gap
    `plan_docs` exists to close.

    `research/` is deliberately outside the sweep, for the same reason it is
    outside the write grant: a synthesis' own checkboxes are not this plan's.
    """
    boxes: Counter = Counter()
    for name in plan_docs(component):
        boxes += checked_boxes(component / name)
    return boxes




# WHAT MARKS A PHASE COMPLETE IN A ROADMAP HEADING. Measured across every
# roadmap in the tree on 2026-08-25: the vocabulary is exactly two tokens, `⬜`
# and `✅ COMPLETE`, ten and three occurrences. Keyed on the EMOJI rather than
# the word, because a phase legitimately named for completeness — "Nothing a run
# relies on is invisible" is one heading away from it — would match a word test
# and silently subtract itself from the remaining work.
#
# THE FAILURE DIRECTION IS CHOSEN. A roadmap that one day marks completion some
# other way makes this read that phase as OUTSTANDING, so the to-do figure comes
# out too HIGH. Over-reporting remaining work is the safe error: it costs a
# second look, where under-reporting quietly shortens a plan.
_COMPLETE_MARK = "✅"

#: A phase saying it is DELIBERATELY unsized. Checked BEFORE `HOUR_ESTIMATE`,
#: because a removal notice necessarily quotes the figure it removed and
#: `HOUR_ESTIMATE`'s first alternative cannot tell a quoted figure from a live
#: one. Without this the honest act — deleting a stale estimate and saying why —
#: leaves the phase reading as sized at the number it just retired.
_NOT_SIZED = re.compile(r"\*\*\s*NOT SIZED\b", re.I)


class PhaseSizing(NamedTuple):
    """One component's phases, each with the estimate `plan-refine` wrote.

    `total` is every estimate summed. `todo` is that less every phase the
    roadmap marks COMPLETE — the figure the sprint header shows beside it,
    and the one that answers *how much of this is left*. Both are derived
    here because a figure restated where nothing derives it goes stale.
    """

    rows: tuple[tuple[str, float | None], ...]   # (phase heading, hours or None)
    total: float
    todo: float                                  # total, less what is COMPLETE
    unsized: tuple[str, ...]


def phase_sizing(component: Path) -> PhaseSizing:
    """Read the roadmap's phase headings and the estimate beside each. Sum in CODE.

    THE SUM IS ARITHMETIC AND A MODEL IS THE WRONG TOOL FOR IT. `plan-refine`
    writes one estimate per phase and deliberately writes no total, because "a
    total is derived from the parts and a derived figure restated where nothing
    derives it" goes stale. This is the thing that derives it. A model asked to
    add four numbers out of a document can misread one and nothing catches it —
    the repo's own rule is that a count is a claim, enumerated rather than
    asserted, and this enumerates.

    WHAT THE MODEL STILL DECIDES, so the split is not read as "code does sizing":
    whether the component has a home in the sprint, where a new section belongs
    in the order, and what its bullets say. The NUMBER is a fact handed over;
    everything done WITH it is judgement.

    AN UNSIZED PHASE IS REPORTED, NEVER TREATED AS ZERO, AND HAS NO BENIGN CASE.
    `plan-refine` sizes EVERY phase on every run, a COMPLETE one included, so a
    phase without an estimate is always a defect the total must not swallow — a
    quietly short total is worse than an absent one, because nothing says it is
    wrong. The prompt is told to say which.

    SIZING A COMPLETE PHASE DOES NOT INFLATE WHAT IS LEFT, which is the whole
    reason the exception that used to live here was removed: `total` counts it and
    `todo` subtracts it, so the two figures need it present to differ at all. An
    exception carved into the WRITER cannot be seen by `sizing_floor`, which
    counts phase-doc FILES ON DISK — that disagreement failed a real run on
    2026-08-25, and the fix was to delete the exception rather than teach three
    surfaces about it.
    """
    roadmap = component / "roadmap.md"
    if not roadmap.is_file():
        return PhaseSizing((), 0.0, 0.0, ())

    text = roadmap.read_text().splitlines()
    heading_at = [n for n, line in enumerate(text) if re.match(r"^#{2,4}\s", line)]

    rows: list[tuple[str, float | None]] = []
    for n in heading_at:
        line = text[n]
        nxt = next((k for k in heading_at if k > n), len(text))
        # A PHASE HEADING CARRIES A STATUS MARKER; ITS SECTION MAY NAME A DOC.
        # Either signal identifies one, and both are EXACT rather than heuristic.
        #
        # THIS USED TO REQUIRE A LITERAL `Phase <digit>` IN THE HEADING, and
        # `documentation_standard.md` rule 4 binds the opposite — *"a phase is
        # CITED BY NAME, never by number"* — naming roadmap headings as a surface
        # that CONVERTS. A roadmap written to the standard was invisible to the
        # counter that reads it. Reported three times on one MDC PR; measured
        # here at the moment of conversion, when all four roadmaps went to 0
        # phases / 0 h at once.
        #
        # AND THE FAILURE IS NOT LOUD, which is why the signals had to be exact:
        # `sizing_block` renders an authoritative *"counted in code, do not
        # recount — lists no phases"* over a fully sized component, and the one
        # run that survived it did so by overriding the block and saying so.
        #
        # A LOOSER PREDICATE WAS TRIED FIRST AND REJECTED ON MEASUREMENT. Reading
        # "any `phaseN_*.md` named in the heading's section" miscounted both
        # corpora — ours 5 -> 7, MDC's 5 -> 12, picking up *"Page 1"* and
        # *"Research posture"* — because a section that CITES a phase doc is not
        # a phase section. Three window widths were measured; none separated
        # them. **A parser that finds seven phases where there are five is worse
        # than one that finds none**, because a wrong count is summed into a
        # sprint header while a zero announces itself.
        marker = _PHASE_MARKER.search(line)
        impl = _IMPLEMENTATION.search("\n".join(text[n:nxt]))
        if not (marker or impl or re.search(r"\bPhase\s+\d+", line, re.I)):
            continue

        # ONE WINDOW PER PHASE, STARTING AT THE HEADING ITSELF, so an estimate
        # written INTO the heading and one written as the paragraph below it are
        # the same search rather than two passes. The previous shape ran the
        # below-heading pass only when EVERY phase lacked an inline figure, so a
        # roadmap mixing the two spellings reported every below-heading phase as
        # unsized. That failed loudly rather than quietly, but it failed on a
        # correct document.
        #
        # SIX LINES, measured rather than guessed: `plan-refine` writes
        # `**Est: ~15 hours** *(sized cold …)*` as its own paragraph after the
        # heading and a blank line and the phase's italic subtitle, which lands
        # it four lines down. A window of 4 found nothing on the first real
        # roadmap it met. Six covers that with one line of slack.
        #
        # AND IT IS BOUNDED BY THE NEXT HEADING, because six lines alone is NOT
        # enough to keep it out of the following phase. The comment here used to
        # assert that it "cannot reach the NEXT heading"; that was false for a
        # phase whose body is short or empty — two adjacent headings put the
        # SECOND phase's estimate inside the FIRST phase's window, which is a
        # double fault: the figure is counted twice in the total, and the phase
        # that was actually missed drops out of `unsized`, which is the only
        # signal anyone gets that it was missed. A GATED phase — a roadmap entry
        # with no doc and often no body — is exactly that shape.
        nxt = next((k for k in heading_at if k > n), len(text))
        # THE WHOLE SECTION, BOUNDED BY THE NEXT HEADING — not a fixed line
        # count. It was six lines, chosen when an estimate sat four lines under
        # the heading. Adding the `**Implementation:**` line on 2026-08-28 moved
        # every estimate down two and pushed seven of them out of the window:
        # `temporal-integration` read 34 h against 193, and
        # `workflow-decomposition` read ZERO with all five phases unsized.
        #
        # A LINE COUNT WAS ALWAYS A PROXY FOR *"inside this phase's own text"*,
        # and `nxt` expresses that exactly, so the proxy is gone rather than
        # retuned — a wider fixed window would break again on the next line
        # anyone adds. The prompt already forbids a second hour figure in a
        # sizing note, which is what keeps one section to one estimate.
        section = "\n".join(text[n:nxt])
        # DECLARED ABSENCE WINS OVER AN INFERRED FIGURE — see `_NOT_SIZED`.
        m = None if _NOT_SIZED.search(section) else HOUR_ESTIMATE.search(section)
        hours = float(next(g for g in m.groups() if g)) if m else None
        rows.append((line.lstrip("# ").strip(), hours))

    # THE PRE-RULE-8 CHECKBOX FORM. `documentation_standard.md` rule 8 binds
    # every phase-entry reader to accept it until the corpus finishes converting,
    # and rule 4 converts a roadmap only when someone is already working in it.
    #
    # A ZERO HERE IS NOT INERT: `sizing_block` renders "lists no phases" and so
    # withholds the `(~Nh total · ~Nh to-do)` template it otherwise hands the run,
    # which then copies its target file's neighbours instead. The sprint header's
    # shape therefore depends on this counter finding phases.
    #
    # ALTERNATIVES, NOT ADDITIVE — a mid-conversion file holds both notations for
    # one phase, and summing them doubles its hours. Undercounting is the chosen
    # trade because `sizing_floor` counts phase-doc FILES ON DISK and fails loudly
    # on a short read, where a doubled total is silent.
    if not rows:
        starts = [n for n, line in enumerate(text) if _CHECKBOX_PHASE.match(line)]
        for i, n in enumerate(starts):
            nxt = min([k for k in starts[i + 1:] + heading_at if k > n],
                      default=len(text))
            span = "\n".join(text[n:nxt])
            if not _PHASE_DOC_REF.search(span):
                continue            # a bolded checklist item, not a phase entry
            box, name = _CHECKBOX_PHASE.match(text[n]).groups()
            # THE MARKER IS SYNTHESISED SO BOTH PATHS PRODUCE ONE ROW SHAPE.
            # A rule-8 row's head literally contains `✅ COMPLETE` because it is
            # part of the heading, and `todo` below tests exactly that. Rule 5
            # names `[x]` the checkbox equivalent of `✅ COMPLETE`, so this is
            # the standard's own mapping applied, not a convenience.
            head = f"{name} {_COMPLETE_MARK} COMPLETE" if box.lower() == "x" else name
            m = HOUR_ESTIMATE.search(span)
            rows.append((head, float(next(g for g in m.groups() if g)) if m else None))

    total = sum(h for _, h in rows if h is not None)
    unsized = tuple(head for head, h in rows if h is None)
    todo = sum(h for head, h in rows
               if h is not None and _COMPLETE_MARK not in head)
    return PhaseSizing(tuple(rows), total, todo, unsized)


def sizing_block(sizing: "PhaseSizing", component_rel: Path) -> str:
    """The phases, their estimates and the TOTAL, rendered as a stated fact.

    THE SAME SHAPE AS `planning_state` AND `candidate_counts`, and for the same
    reason: a figure the prompt asks a model to derive is a figure that can be
    derived wrongly with nothing to catch it. This one is arithmetic, which makes
    it the clearest case in the family.

    THE UNSIZED LIST IS NOT DECORATION, AND IT HAS NO BENIGN MEMBER. Every phase
    carries an estimate, a COMPLETE one included and sized for the work it
    contained, so a phase missing one is always a defect; presenting a total
    without saying which phases it does NOT cover is how a quietly short number
    gets recorded as the cost of the work.
    """
    if not sizing.rows:
        return (f"**Counted in code, authoritative — do not recount:** "
                f"`{component_rel.as_posix()}/roadmap.md` lists **no phases**. "
                f"There is nothing to total; say so and change no estimate.")
    lines = "\n".join(
        f"| {head} | {'—' if hours is None else f'{hours:g} h'} |"
        for head, hours in sizing.rows)
    unsized = (
        "\n\n**Unsized:** " + ", ".join(f"*{u}*" for u in sizing.unsized)
        + " — every phase should carry one, a COMPLETE phase included and sized "
          "for the work it contained, so each of these is a defect and the total "
          "does not cover it. Say so rather than presenting the total as whole."
        if sizing.unsized else
        "\n\n**Every phase carries an estimate.**")
    return (f"**Counted in code, authoritative — do not recount, re-derive or "
            f"adjust:**\n\n| Phase | Estimate |\n|---|---|\n{lines}\n"
            f"| **TOTAL** | **{sizing.total:g} h** |\n"
            f"| **TO-DO** | **{sizing.todo:g} h** |{unsized}\n\n"
            f"**The sprint header carries BOTH**, in the shape the neighbouring "
            f"sections use: `(~{sizing.total:g}h total · ~{sizing.todo:g}h to-do)`. "
            f"TO-DO is the total less every phase the roadmap marks complete — "
            f"derived here so nothing subtracts it by hand.")


def sprint_state(sprint: Path, component_rel: Path) -> str:
    """Whether this component already has a section, counted rather than guessed.

    The two cases are different jobs — refresh an entry the operator positioned,
    or add one and inherit a position — and a model reading an unlabelled sprint
    file will conflate them. `plan_draft.planning_state` states the same kind of
    fact for the same kind of reason.
    """
    if not sprint.is_file():
        return f"**Counted in code:** `{sprint.name}` does not exist."
    text = sprint.read_text()
    slug = component_rel.name
    words = [w for w in re.split(r"[-_]", slug) if w]
    heads = re.findall(r"^## Sprint: (.+)$", text, re.M)
    # ALL MATCHING SECTIONS, NOT THE FIRST. A component is legitimately split
    # across sections — `— Part 1` / `— Part 2` is an established shape in this
    # file — and `next(...)` reported the first one as though it were the whole
    # component, under a block that says "authoritative — do not recount".
    # Measured on PR #150: `persistent-memory-protocol` has TWO sections; the run
    # was told it had one, carrying 6 bullets, and never learned the second held
    # the gated phases. A wrong count is worse than a zero because it announces
    # authority, which is the same failure `phase_sizing` was fixed for.
    hits = [h for h in heads if all(w.lower() in h.lower() for w in words)]
    hit = hits[0] if hits else None
    if hit is None:
        return (f"**Counted in code, authoritative — do not recount:** the sprint "
                f"plan has **{len(heads)} sections** and **none of them is "
                f"`{slug}`**. This component needs one ADDED, and its position is "
                f"inherited from what it depends on — not argued from scratch.")
    def _bullets(head: str) -> int:
        body = text.split(f"## Sprint: {head}", 1)[1].split("\n## Sprint:", 1)[0]
        return len(re.findall(r"^- \[[ x]\]", body, re.M))

    if len(hits) > 1:
        rows = "; ".join(f"`{h}` ({_bullets(h)} bullet(s), "
                         f"{heads.index(h) + 1} of {len(heads)})" for h in hits)
        return (f"**Counted in code, authoritative — do not recount:** this "
                f"component is SPLIT ACROSS {len(hits)} SECTIONS — {rows}. "
                f"**Update every one of them in place**, and put each phase in "
                f"the section the operator already placed it in. **Which phase "
                f"belongs to which part is the operator's split, not yours** — "
                f"moving one between sections re-sequences the plan, which is a "
                f"decision this workflow does not make.")

    return (f"**Counted in code, authoritative — do not recount:** this component "
            f"HAS a section — `## Sprint: {hit}` — carrying **{_bullets(hit)} phase "
            f"bullet(s)**. It is **{heads.index(hit) + 1} of {len(heads)}** in the "
            f"file. **Update it in place**: its position is the operator's and "
            f"nothing upstream of you changed it.")


# --- rule 9: the dependency graph, derived -----------------------------------------
#
# `documentation_standard.md` § Development Planning Files rule 9 states one optional
# `**Depends on:**` line per phase entry and rules that FOUR facts are derived rather
# than written: the reverse edge, the component-level rollup `plan_sprint` orders on,
# whether an edge is satisfied, and the graph itself. This is what derives them, and it
# exists so that "derived" is a property of the corpus rather than a promise in prose.
#
# WHY IN CODE AND NOT IN A PROMPT. The rule's whole argument is that a computed value
# written down a second time is correct on the day it is written and silently wrong
# afterwards. A model asked to reconstruct the reverse edges of a corpus can miss one and
# nothing catches it. This enumerates, the same reason `phase_sizing` sums in code.

#: Rule 9's marker, anchored at the start of a line inside a phase entry's span.
_DEPENDS_ON = re.compile(r"^\*\*Depends on:\*\*\s*(.*)$", re.M)
#: A markdown link. Rule 9: the parser reads only the links and ignores the words, so
#: prose around them survives without breaking either reader.
_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
#: Rule 9's standalone token, UNQUALIFIED — the word, then the end of the clause.
#: A qualified form is a SCOPED declaration wearing the standalone one's clothes:
#: `nothing internal` and `nothing inside this component` each mean *and something
#: outside it*, so reading either as standalone silently deletes a real dependency.
#: Both are live in the MDC corpus, which is what this anchor exists to refuse.
_STANDALONE = re.compile(r"^NONE\s*(?:[.;,)\]]|$)")


class DependencyEdge(NamedTuple):
    """One forward edge, as declared. Everything else about it is computed."""
    roadmap: Path            #: the declaring roadmap, absolute
    phase: str               #: the declaring phase entry's name, marker stripped
    text: str                #: the link text, as written
    target: Path             #: resolved absolute path of the depended-on artifact
    note: str                #: the rest of the line — prose the parser ignores


def _entry_windows(text: list[str]) -> list[tuple[int, int, str]]:
    """(start, end, heading-text) per `##`-`####` heading. Same spans `phase_sizing` uses.

    Shared shape rather than a second walk: two parsers disagreeing about where an
    entry ENDS would attribute a `Depends on:` line to the wrong phase, and the
    disagreement would be invisible in both outputs.
    """
    at = [n for n, line in enumerate(text) if re.match(r"^#{2,4}\s", line)]
    return [(n, next((k for k in at if k > n), len(text)),
             re.sub(r"^#{2,4}\s+", "", text[n])) for n in at]


def dependency_edges(roadmap: Path) -> list[DependencyEdge]:
    """Every forward edge this roadmap declares, resolved against its own directory.

    A LINK THAT DOES NOT RESOLVE IS STILL AN EDGE. Rule 9 distinguishes a broken
    target from an unsatisfied one and says a renderer must not show them alike, so
    resolution is `edge_state`'s job and never a filter here — dropping it would make
    a typo indistinguishable from a dependency nobody declared.
    """
    if not roadmap.is_file():
        return []
    text = roadmap.read_text(encoding="utf-8").splitlines()
    out: list[DependencyEdge] = []
    for start, end, heading in _entry_windows(text):
        phase = _PHASE_MARKER.sub("", heading).strip()
        for line in text[start:end]:
            m = _DEPENDS_ON.match(line)
            if not m:
                continue
            body = m.group(1)
            for label, href in _MD_LINK.findall(body):
                if href.startswith(("http://", "https://", "#")):
                    continue          # an external or intra-page link is not an edge
                out.append(DependencyEdge(
                    roadmap=roadmap, phase=phase, text=label,
                    # `urldefrag`, never a split — `test_pr_url_address` holds the
                    # rule that a path segment is not derived by string surgery, and a
                    # link may legitimately carry `#section` after the file.
                    target=(roadmap.parent / urldefrag(href).url).resolve(),
                    note=_MD_LINK.sub("", body).strip(" ·—-"),
                ))
    return out


def declaration_state(roadmap: Path, phase: str) -> str:
    """`declared` · `standalone` · `qualified` · `missing`, for ONE phase entry.

    RULE 9 HAS THREE LEGAL STATES AND A BLANK IS NOT ONE OF THEM. Absence cannot
    distinguish a declaration from damage: a sweep that skips a roadmap, an emitter that
    throws, a hand-authored roadmap and a bad merge that deletes the line all produce the
    same artifact. A mechanical rename pass has already mangled a `Depends on:` line in
    the MDC corpus; one that deleted it instead would, under an absence rule, have
    silently converted a real dependency into a conformant *"depends on nothing"*.

    `qualified` is reported separately from `standalone` rather than folded into it —
    *"nothing internal"* is a scoped claim, and calling it standalone is precisely the
    silent deletion this distinguishes.
    """
    if not roadmap.is_file():
        return "missing"
    text = roadmap.read_text(encoding="utf-8").splitlines()
    for start, end, heading in _entry_windows(text):
        if _PHASE_MARKER.sub("", heading).strip() != phase:
            continue
        for line in text[start:end]:
            m = _DEPENDS_ON.match(line)
            if not m:
                continue
            body = m.group(1).strip()
            if _MD_LINK.search(body):
                return "declared"
            if _STANDALONE.match(body):
                return "standalone"
            return "qualified"          # includes a bare marker: a truncation, not a claim
        return "missing"
    return "missing"


def unassessed_phases(repo_root: Path) -> list[tuple[Path, str, str]]:
    """Every phase entry whose dependency declaration is absent or qualified.

    This is the finding rule 9's third state exists to produce, and the worklist a
    conversion sweep is measured against — *the corpus telling you what it does not know
    about itself*.
    """
    out = []
    for rm in sorted((repo_root / "development").rglob("roadmap.md")):
        text = rm.read_text(encoding="utf-8").splitlines()
        for _, _, heading in _entry_windows(text):
            if not _PHASE_MARKER.search(heading):
                continue                # not a rule-8 phase entry; nothing is claimed
            phase = _PHASE_MARKER.sub("", heading).strip()
            state = declaration_state(rm, phase)
            if state in ("missing", "qualified"):
                out.append((rm, phase, state))
    return out


def dependency_graph(repo_root: Path) -> list[DependencyEdge]:
    """Every forward edge in the corpus. Rule 9: this is the whole input."""
    return [e for rm in sorted((repo_root / "development").rglob("roadmap.md"))
            for e in dependency_edges(rm)]


def edge_state(edge: DependencyEdge, repo_root: Path) -> str:
    """`satisfied` · `unsatisfied` · `broken`, derived from what the TARGET IS.

    Rule 9, corrected 2026-09-06 after the phase-6 row of `workflow-decomposition`'s
    table failed to derive: a PHASE resolves to its rule-8 status marker, while a
    STANDARD or other non-phase artifact has none and is satisfied by resolving —
    plus its vendoring banner, which is what makes *"vendored and ratified, amendments
    go upstream"* a computed fact.

    **`broken` is not a flavour of `unsatisfied`.** A target that does not exist is a
    typo or a deletion; a target that exists and is unfinished is the graph working.
    """
    if not edge.target.exists():
        return "broken"
    if re.match(r"phase\d", edge.target.name):
        marker = _phase_marker_for(edge.target)
        if marker is None:
            return "unsatisfied"      # a doc no roadmap entry claims
        return "satisfied" if "COMPLETE" in marker else "unsatisfied"
    return "satisfied"                # a standard or other artifact: it resolves


def _phase_marker_for(phase_doc: Path) -> str | None:
    """The rule-8 marker on the entry that OWNS this phase doc.

    The marker lives on the roadmap entry, never in the phase doc, so satisfaction is
    read where rule 8 put it rather than from a second place the doc might restate it.
    """
    roadmap = phase_doc.parent / "roadmap.md"
    if not roadmap.is_file():
        return None
    text = roadmap.read_text(encoding="utf-8").splitlines()
    for start, end, heading in _entry_windows(text):
        # THE `**Implementation:**` LINE, NEVER "the name appears in this span" —
        # rule 8's exact anchor, and the looser predicate is one this repo has
        # already measured and rejected: *"a section that CITES a phase doc is not a
        # phase section"*, which miscounted 5 -> 7 here and 5 -> 12 in MDC. It was
        # written the loose way first and read PMP's OPENING PARAGRAPH — which
        # mentions `phase1_the_run_bag.md` in prose — as the owning entry, returning
        # its marker instead of the real one twelve headings down.
        owning = [l for l in text[start:end] if _IMPLEMENTATION.match(l)
                  and phase_doc.name in l]
        if owning:
            m = _PHASE_MARKER.search(heading)
            return m.group(0).strip() if m else None
    return None


def gated_on(component: Path, graph: list[DependencyEdge]) -> list[DependencyEdge]:
    """The REVERSE edges — what depends on this component. Derived, never declared.

    Rule 9 forbids declaring these: one fact in two files disagrees eventually, and
    `memory-management-framework` carried a reverse list whose every derivable member
    was already declared forward by the component itself.
    """
    here = component.resolve()
    # A COMPONENT'S OWN PHASE-TO-PHASE EDGES ARE NOT REVERSE DEPENDENCIES. Rule 9's
    # reverse edge answers *what OTHER work is gated on this*; an internal edge is
    # sequencing inside one plan and rendering it as inbound would show every
    # component gated on itself.
    return [e for e in graph
            if (here in e.target.parents or e.target.parent == here)
            and e.roadmap.parent.resolve() != here]


def component_dependencies(graph: list[DependencyEdge]) -> dict[Path, set[Path]]:
    """Component -> the components it depends on. What `plan_sprint` orders on.

    Rule 9: a component depends on X if ANY of its phases does. Declared at the phase
    and rolled up here, because the rollup is computable from the finer grain and the
    finer grain is not computable from the rollup.
    """
    out: dict[Path, set[Path]] = {}
    for e in graph:
        out.setdefault(e.roadmap.parent, set()).add(e.target.parent)
    return {k: {t for t in v if t != k} for k, v in out.items()}

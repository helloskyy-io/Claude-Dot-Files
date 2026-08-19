"""plan-sprint — keep the sprint plan current against the ruled candidates.

Folder holds only this file (§10.1 rule 6); the family's shared capability is
promoted to `plan_activities`.

WHAT THIS IS FOR. Candidates get ruled `ship` and then have to land somewhere.
This workflow places what is placeable in the sprint plan, reconciles sections
the research has since corrected, and reports what the three planning documents
say about each other. It is the sprint plan's maintainer.

IT NO LONGER TRIAGES, AND THAT IS THE POINT OF THE SPLIT. This workflow used to
do two jobs in one run — its own docstring said *"triage research candidates and
keep the sprint plan current"* — and nothing could be sequenced between them.
`triage_candidates` now owns the ruling, runs ahead of this, and **`decision` is
its output alone.** The post-condition that every row reach a disposition went
with it: a workflow that no longer writes the column must not raise about it.

That split also fixed an ordering defect for free. The sprint plan used to be
updated BEFORE anything estimated the work, so its hour totals landed ahead of
the estimates they depend on. `plan_project` now runs this LAST.

WHAT IT DELIBERATELY DOES NOT DO. It does not rule a candidate, it does not file
a `direction.md` row, and it does not write a phase doc. It reads
`problem-statement.md` and never writes it — that document is the thesis
everything else derives from, and the judgement in it is not delegable.

IT IS AUTHORISED TO EDIT THE SPRINT FILE, which is otherwise forbidden. The
governing rule's override covers exactly this case and rests on the PR being
human-reviewed before merge. **That authorization did not transfer to
`triage_candidates` and must not** — one workflow writes `sprint.md`, and it is
this one. The scope limits live in the prompt, where the model reading them can
be bound by them.
"""

from __future__ import annotations

import re

from ... import routing

from pathlib import Path

from .. import plan_activities as act

_HERE = Path(__file__).resolve().parent
PROMPTS = _HERE / "prompts"

MODEL_KEY = "plan-sprint"

# An ESTIMATE, stated as one — this workflow has never been measured. The basis
# and the revise-from-measurement note live with the value in config.yaml.
WORKFLOW_KEY = "plan-sprint"   # NOT MODEL_KEY -- see run_claude's docstring
MAX_TURNS = act.max_turns(WORKFLOW_KEY)

COMPLETION_PATTERN = routing.PR_URL_COMPLETION_ERE

# --- THE PATH BOUNDARY, DECLARED WHERE THE PROMPT'S TABLE CAN BE READ AGAINST IT
#
# Every path-scoped `You MAY NOT` row in `prompts/plan_sprint.md`, as a pattern.
# This workflow's authorization is UNUSUAL — it holds the one override permitting
# a dispatch to write `sprint.md` — which is exactly why the edges of it are
# observed rather than trusted: the file the override opens sits inside the same
# directory as the phase docs it must not touch.
FORBIDDEN_PATHS = (
    r"^docs/development/",      # "Write or edit any phase doc"
    r"^docs/standards/",        # "Append to or edit `direction.md`" and the rest
)


def permitted_paths(sprint_rel: str) -> tuple[str, ...]:
    """The ONE file this workflow legitimately writes, from its own argument.

    Computed from the sprint path rather than hard-coded because the path is a
    parameter — `--sprint` moves it, and a boundary that assumed
    `docs/development/sprint.md` would fail a correct run in any repo that keeps
    its plan elsewhere.

    IT WAS TWO GRANTS UNTIL 2026-08-19. The second was `candidates.md`, held so
    this workflow could place ruled `ship` rows — the job that left when the
    chain was rebuilt around a planned COMPONENT. A grant kept after its job
    moved is a permission nothing needs and everything inherits, so it went with
    the job. Appending a surfaced proposal is `plan-feature`'s and
    `plan-verify`'s; ruling one is `triage-candidates`'s; neither is this run's.
    """
    return (rf"^{re.escape(sprint_rel)}$",)


# --- EVERY `You MAY NOT` ROW, AND WHAT OBSERVES IT ---------------------------
#
# See `triage_candidates_workflow.MAY_NOT_OBSERVERS` for why this map exists
# and why it is keyed by the row's exact text — CITED rather than restated.
# `test_authorization_is_observed.py` compares these keys against the rendered
# table over a DISCOVERED set of workflows, and `JUDGEMENT` is a legitimate
# answer that must say why the property has no artifact.
MAY_NOT_OBSERVERS: dict[str, str] = {
    "**RE-SIZE anything** — the estimates are `plan-verify`'s and the total is computed for you":
        "FORBIDDEN_PATHS `^docs/development/` less permitted_paths, whose only "
        "grant is the sprint file — so every roadmap, where the estimates live, "
        "is a forbidden path. The total this run is handed comes from "
        "act.phase_sizing, computed BEFORE the model is called, so the number in "
        "the prompt is not one the run can have moved",
    "**Touch another component's section** — not its bullets, not its total, not its position":
        "JUDGEMENT. The sprint file is ONE granted path and every section lives "
        "inside it, so no path comparator can separate this component's section "
        "from its neighbour's. What DOES observe it is the diff a human reads: "
        "the report's change table names the section touched, and a run that "
        "edited another one is visible there. Stated as judgement rather than "
        "left implied — a per-section comparator is real work and would be the "
        "honest fix if this is ever breached",
    "**MOVE a section that already exists** — anyone's, including this component's":
        "JUDGEMENT — re-ordering happens INSIDE the one granted file, so no "
        "path comparator can see it and a text compare of the whole file cannot "
        "tell a legitimate insertion from a rearrangement around it. The prompt "
        "carries the rule as `insert, never rearrange`, and the report must "
        "state where a new section went and what decided the position",
    "**Rule a candidate** — `decision` is `triage-candidates`'s alone":
        "FORBIDDEN_PATHS `^docs/standards/`, which this workflow no longer "
        "exempts. The candidates grant was dropped in the 2026-08-19 rebuild "
        "along with the job that needed it, so the file is simply outside the "
        "boundary — a stronger rule than the column comparators it replaces, and "
        "one that needs no reader",
    "**Tick a completion checkbox** — nothing here has been built":
        "act.checked_boxes over the sprint file — the only file this run may "
        "write — counted either side and compared in BOTH directions",
    "Write or edit a roadmap, a phase doc, a standard, or `candidates.md`":
        "FORBIDDEN_PATHS `^docs/development/` and `^docs/standards/` less "
        "permitted_paths, via act.worktree_state / act.boundary_crossings",
    "**Delete a section, a bullet or a milestone**":
        "act.grants_that_vanished over permitted_paths for the FILE, and "
        "act.checked_boxes compared in the erasure direction for a BULLET that "
        "carried a checkbox. A prose milestone with no box is JUDGEMENT — the "
        "change table is where a reader sees it",
}

# --- EVERY BEFORE/AFTER SNAPSHOT, AND WHAT WATCHES IT FOR ABSENCE ------------
#
# See `triage_candidates_workflow.DISAPPEARANCE_OBSERVERS` for why this map is
# keyed by the snapshot rather than by the prohibition.
DISAPPEARANCE_OBSERVERS: dict[str, str] = {
    # THREE ENTRIES LEFT ON 2026-08-19 — `before`, `before_status` and
    # `before_component`, the candidate-column snapshots. They watched a file this
    # workflow no longer writes: the `candidates.md` grant went with the job of
    # placing ruled rows, so there is no column to protect and nothing to snapshot.
    # The rows are not "no longer checked" — they are outside the boundary now,
    # which `boundary_crossings` enforces through `before_tree` below.
    "before_boxes":
        "act.checked_boxes compared in both directions — `after - before` is a "
        "tick added, `before - after` a tick erased, and Counter subtraction "
        "reports only the first",
    "before_tree":
        "act.grants_that_vanished over permitted_paths for the sprint plan — the "
        "only grant left — and act.boundary_crossings for every other path, where "
        "a deletion already reads as a content change via the ABSENT sentinel",
}


def prompt_values(rel_sprint: str, rel_component: Path, tree: Path,
                  correction_pass: bool, pr_number: str | None,
                  context: str = "") -> dict[str, str]:
    """Every placeholder the prompt takes, assembled ONCE for both callers.

    THE DRY RUN AND THE REAL RUN MUST RENDER THE SAME PROMPT. This module's
    `correction_note` docstring records what happens otherwise: the runner built
    its own copy of this dict, rendered only half of `CORRECTION_NOTE`, and
    previewed text no model would ever receive. That was fixed by patching the
    copy, which left the copy — and the shape that produced the bug — in place.
    One assembly is what removes it.

    `tree` IS THE TREE THE COUNTS ARE TAKEN FROM: the worktree on the live path,
    the repo on the dry-run path, where no worktree exists yet.
    """
    sizing = act.phase_sizing(tree / rel_component)
    return {
        "SPRINT_PATH": rel_sprint,
        "COMPONENT_PATH": rel_component.as_posix(),
        # COMPUTED, NOT ASKED FOR. The sum is arithmetic and a model is the wrong
        # tool for it — `plan-verify` writes one estimate per phase and no total,
        # deliberately, so the thing that derives the total has to be code or the
        # figure is an assertion. Both the parts and the sum are handed over.
        "SIZING_BLOCK": act.sizing_block(sizing, rel_component),
        "SPRINT_STATE": act.sprint_state(tree / rel_sprint, rel_component),
        "TASK_CONTEXT": (
            "## OPERATOR CONTEXT FOR THIS RUN\n\n"
            "**This is authoritative and overrides your own reading where they "
            "disagree.** Verify any FACT it asserts about the tree before "
            "building on it.\n\n" + context
            if context.strip() else ""
        ),
        "CORRECTION_NOTE": (
            "This is a CORRECTION PASS. A prior disposition returned HOLD with a "
            "scoped runway; close it." if correction_pass else ""
        ),
        "SUBMIT_PROMPT": act.submit_prompt(
            pr_number, f"plan-sprint: {rel_component.name}"),
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
        "HEADLESS_EXECUTION_GUARD": act.shared_prompt("headless_execution_guard"),
    }


def run_plan_sprint(*, repo_root: Path, worktree: Path, sprint_path: Path,
                    component: Path, pr_number: str | None = None,
                    correction_pass: bool = False, context: str = "",
                    verbose: bool = False) -> str:
    """Give ONE planned component a current home in the sprint. Returns the PR URL.

    REBUILT 2026-08-19, and the previous prompt is kept beside this one as
    `plan_sprint_OLD.md` until `triage-candidates` takes over the half that left.
    The old workflow was entirely candidate-driven: it walked `candidates.md`,
    applied a five-condition bar to every `ship` row, and decided sprint section
    versus milestone versus not-in-this-file. It had no component input at all.

    That is the wrong half. By the time this runs, `triage-candidates` has ruled
    the candidate, `plan-candidates` has scaffolded it, `plan-feature` has written
    its roadmap and phase docs and `plan-verify` has sized every phase — so
    "does this warrant a sprint section" was answered upstream by the chain
    BUILDING the thing, and re-deciding it here overturns a ruling with less
    context than the run that made it.

    What was actually missing is the job this now does: take the component that
    was just planned, and make its sprint entry current — the phase bullets and
    the hour total. Nothing produced that total before, and no sprint section in
    this repo has ever carried one.
    """
    # Paths arrive rooted at the REPO because that is where they are configured,
    # but the run reads and writes inside the WORKTREE. Count what the model will
    # actually see, and later re-read what it actually wrote.
    rel_component = component.relative_to(repo_root)
    rel_sprint = str(sprint_path.relative_to(repo_root))
    wt_sprint = worktree / rel_sprint

    # Counted in code so the report cannot assert a total it invented.

    # WHAT THIS RUN MUST NOT MOVE, snapshotted before it can move it. `decision`
    # is `triage-candidates`'s; `status` is a later process's; a ticked checkbox
    # claims validation this workflow has performed none of; and the paths
    # outside its authorization are not its to reach at all.
    #
    # Snapshotted AROUND THE MODEL, never diffed against `origin/main`: this
    # workflow runs LAST on a branch `triage-candidates` has already written to,
    # so a diff against the base would report triage's legitimate `direction.md`
    # row as this run's forbidden edit.
    before_boxes = act.checked_boxes(wt_sprint)
    before_tree = act.worktree_state(worktree)

    values = prompt_values(rel_sprint, rel_component, worktree,
                           correction_pass, pr_number, context)

    output = act.run_claude(
        act.render(act.load_prompt(PROMPTS / "plan_sprint.md"), values,
                   opaque=frozenset({"TASK_CONTEXT"})),
        model_key=MODEL_KEY, workflow_key=WORKFLOW_KEY,
        completion_pattern=COMPLETION_PATTERN,
        repo_root=repo_root, worktree=worktree,
        max_turns=MAX_TURNS, verbose=verbose,
    )

    url = act.extract_pr_url(output)
    if not url:
        raise RuntimeError(
            "plan-sprint produced no PR URL. Its sprint edits are UNREVIEWED — the "
            "sprint plan must not be trusted as current."
        )

    # A WRITE GRANT IS NOT A DELETE GRANT, and this workflow holds the family's
    # only override — so it is the one place where an unbounded reading of that
    # grant costs the operator their sequencing surface. Checked FIRST because
    # every reader below assumes the file it parses is still there: a deleted
    # `candidates.md` would otherwise surface as a FileNotFoundError, a true
    # failure naming the wrong cause.
    #
    # A NARROW EXISTENCE RULE OVER THE DECLARED GRANTS, NOT A GENERAL "permitted
    # paths may not disappear" WIDENING OF `boundary_crossings`: absence is a
    # legitimate state for a permitted path elsewhere in this family —
    # `triage-candidates` CREATES `direction.md` — so a general rule would have
    # to carve that back out immediately. `grants_that_vanished` derives from
    # each workflow's own `permitted` tuple, so a grant added later is covered
    # the moment it is declared.
    after_tree = act.worktree_state(worktree)
    vanished = act.grants_that_vanished(before_tree, after_tree,
                                        permitted_paths(rel_sprint))
    if vanished:
        raise RuntimeError(
            f"plan-sprint made {len(vanished)} file(s) it may WRITE cease to "
            f"exist: {', '.join(vanished)}. Maintaining {rel_sprint} is this "
            f"workflow's whole job, and its override covers EDITING that file, "
            f"not removing it. The sprint plan is the operator's cross-domain "
            f"sequencing surface; a plan that has ceased to exist is "
            f"unrecoverable from their side without reading the diff, and this "
            f"run would otherwise have reported success — see {url}"
        )

    # OBSERVE, DO NOT ASSERT. The prompt forbids writing `decision`; this reads
    # the file to check it did not. An authority transfer stated only in prose is
    # a convention a model can reason past — this is the mechanism.
    # The SAME argument, one column over. `status` is neither workflow's, and the
    # guard above would have watched a run close a candidate it merely placed.
    # Read ONCE: the previous form called the reader three times — once for the
    # comparison and once per offending id inside the message — re-parsing the
    # file for a value that cannot have changed between calls.
    # THE SAME ARGUMENT, ONE COLUMN FURTHER LEFT, and this one is not merely a
    # bad cell. `component` belongs to whoever FILED the row; `plan-candidates`
    # reads it in the NEXT parent run and turns a name into a committed
    # `docs/development/<name>/`. Placing an item in the sprint plan is not the
    # same as deciding which component owns it. The prohibition this run is given
    # is the MAY NOT row at plan_sprint.md:32 and nothing else — this comment
    # attributed "you never decide where a shipped candidate goes" to "the prompt",
    # and that sentence appears only in triage_candidates.md, about the workflow
    # that does NOT place. A maintainer auditing this surface would have believed
    # a prose backstop existed here. It does not; the row is the whole of it.
    # A proposal this run files may
    # still name its own component, which the pre-existing-rows-only comparison
    # permits without a second rule.
    # A CHECKBOX MEANS SHIPPED AND VALIDATED. This workflow places work that will
    # be built later; it has validated nothing, and the Documentation Standard's
    # rule is that built is not proven, let alone planned. Counted by text, so a
    # section legitimately re-ordered does not read as a box ticked.
    #
    # BOTH DIRECTIONS, because the prohibition is "flip a checkbox" and only one
    # direction was observed. `Counter` subtraction keeps positive counts, so a
    # `[x]` line ERASED — by deleting a completed milestone, or by dropping the
    # section holding it — came out as an empty difference and passed. That is
    # the same disappearance-blindness the row guards had, one altitude down,
    # and it destroys the record of work rather than fabricating one. Editing a
    # completed milestone's TEXT already failed here as an added tick, so a
    # reworded box was never legitimate and symmetry adds no new false positive.
    after_boxes = act.checked_boxes(wt_sprint)
    ticked = sorted((after_boxes - before_boxes).elements())
    erased = sorted((before_boxes - after_boxes).elements())
    if ticked or erased:
        moved = ([f"TICKED: {t}" for t in ticked]
                 + [f"ERASED: {e}" for e in erased])
        raise RuntimeError(
            f"plan-sprint flipped {len(moved)} completion checkbox(es) in "
            f"{rel_sprint}: " + "; ".join(moved)
            + f". A checkbox means SHIPPED AND VALIDATED, and this run placed "
              f"work rather than doing it. A plan that reports work nobody has "
              f"built is worse than one that is merely out of date; a plan that "
              f"has forgotten work somebody DID is worse still, because nothing "
              f"downstream will ever ask for it again — see {url}"
        )

    # THE REST OF THE DECLARED BOUNDARY. The override this workflow holds opens
    # exactly one file, and it sits in the same directory as the phase docs the
    # same table forbids — so the edge is observed rather than trusted.
    crossed = act.boundary_crossings(before_tree, after_tree,
                                     FORBIDDEN_PATHS, permitted_paths(rel_sprint))
    if crossed:
        raise RuntimeError(
            f"plan-sprint edited {len(crossed)} file(s) outside its authorization: "
            f"{', '.join(crossed)}. Its override covers {rel_sprint} and nothing "
            f"else — not a phase doc, not a standard, and not `direction.md`, "
            f"which is `triage-candidates`'s to append to and the operator's to "
            f"rule on — see {url}"
        )
    return url


def correction_note(counts: dict, correction_pass: bool) -> str:
    """The whole `${CORRECTION_NOTE}` slot, built ONE way for every caller.

    Public and whole because `--dry-run` renders this prompt too, and it was
    rendering a DIFFERENT one: it passed `_untriaged_note(counts)` alone while
    the real run prefixed the counted line. A dry run whose whole purpose is
    "count and render, no model, no spend" was previewing text no model would
    ever receive, so a regression in the counted line could not be seen without
    spending a live dispatch. `triage_candidates` never had this bug because
    `_working_set` already bundled both halves — this makes the two match.
    """
    counted = (f"\n**Counted in code, authoritative — do not recount:** "
               f"{counts['total']} candidates, {counts['triaged']} ruled, "
               f"{counts['untriaged']} still untriaged.\n\n")
    if correction_pass:
        # THE COUNTS BELONG ON BOTH BRANCHES, and the correction pass needs them
        # MORE than the first pass does. Stage 4 requires the report to state how
        # many candidates still carry a blank `decision`; dropping the counted
        # line left that figure model-derived on exactly the pass most likely to
        # be the last one anybody reads — the invented-count class
        # `candidate_counts` exists to prevent. The `_untriaged_note` PROHIBITION
        # is not repeated here: it is already static in the prompt's "`decision`
        # IS NOT YOURS" section, so what a correction pass was missing is the
        # COUNT, not the rule.
        return (counted + "This is a CORRECTION PASS. A prior review returned HOLD "
                "with a scoped runway; close it.")
    return counted + _untriaged_note(counts)


def _rulings_this_run_had_no_right_to(before: dict[str, str],
                                      after: dict[str, str]) -> list[str]:
    """Ids whose `decision` this run must not have touched, and did.

    Three ways to offend and ONE way not to, and the exemption is why this is a
    named function rather than a set comparison:

      * a ruling CHANGED  — re-litigating a triage pass's output
      * a row DISAPPEARED — the file's own rule is that nobody deletes a row
      * a NEW row arrives already RULED — triage, by another route

      * a NEW row arrives with a BLANK decision — **legitimate, and the naive
        comparison forbade it.** `decision_log_and_reflection.md` instructs
        EVERY producing run to place a proposal it surfaced into `candidates.md`
        with `decision` blank, and this workflow is a producing run. Diffing the
        two id sets outright made the shared placement instruction unfollowable:
        the run would place a proposal exactly as told and then fail its own
        post-condition. Blank is the absence of a ruling, so placing one is not
        ruling anything.
    """
    # Deletion is `act.ids_deleted` rather than a branch here, because the claim
    # that it had one definition was false: the comment on
    # `statuses_this_run_had_no_right_to` said row deletion was "already an
    # offence under the `decision` guard", which was true of this workflow and
    # false of `triage-candidates`, whose count-based post-condition it defeated.
    offences: list[str] = act.ids_deleted(before, after)
    for cid in after.keys():
        was, now = before.get(cid), after[cid]
        if cid not in before:
            if now:                          # appended ALREADY ruled
                offences.append(cid)
        elif was != now:
            offences.append(cid)             # ruling rewritten
    return offences


def _untriaged_note(counts: dict) -> str:
    """What an untriaged row means to THIS workflow: nothing it may act on.

    Standalone, this workflow can meet a file `triage_candidates` has not been
    run against. The honest instruction is not "triage them" — that authority
    moved — and not silence either, because a model that sees blank cells in a
    column it is reading will fill them.
    """
    if not counts["untriaged"]:
        return ("Every row carries a decision. The `ship` rows are the set you "
                "place from.")
    return (
        f"**{counts['untriaged']} rows are UNTRIAGED and they are NOT YOURS: "
        f"{', '.join(counts['untriaged_ids'])}.** A blank `decision` means nothing "
        f"has ruled on that candidate yet, and ruling is `triage-candidates`'s job, "
        f"not this workflow's. **Do not set `decision` on any row, for any reason.** "
        f"Work only from the rows already marked `ship`; note the untriaged count in "
        f"your report so the operator can see triage has not caught up, and move on."
    )

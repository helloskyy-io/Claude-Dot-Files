"""Shared I/O for the planning family — promoted per §10.1 rule 3.

Sits at module level because more than one workflow uses it: `plan_sprint`,
`triage_candidates`, `plan_candidates` and `plan_revision` today, `plan_tech_stack`
when it lands.
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
    **CAME BACK when `plan_candidates` landed**, see below.
  * `direction_ceiling` — one consumer. MOVED to `triage_candidates_activities`.
  * `new_sprint_sections`, `component_dir` — one consumer each (`plan_project`,
    and nothing else in the tree). MOVED to `plan_project_activities`. They were
    missing from the audit above when it was first written, which made this
    docstring's own rule-3 claim incomplete on the very file that states the
    rule. Counted rather than eyeballed the second time. **Both are GONE now**:
    `plan_project`'s research step no longer keys off a sprint diff, so its only
    consumer stopped existing and `scaffolded_components` replaced them.

RULE 3 MOVES IN BOTH DIRECTIONS, AND `plan_candidates` DEMONSTRATED IT. That
workflow may not set `decision` either, so `candidate_decisions` and the
comparator built on it acquired a genuine second consumer and came back here as
`candidate_decisions` / `rulings_this_run_had_no_right_to`. The rule is a
consumer count, not a one-way ratchet: a helper that earned its way into a
workflow folder earns its way back out the moment a second workflow needs it.
Duplicating either would be the drift `normalise_cell` below exists to record —
two hand-written readings of one cell, disagreeing about whether a row is ruled.

`candidate_decisions` and `direction_ceiling` were briefly argued to belong here
anyway, as "the same concern as their neighbours".
[`workflow-scripts.md` § Location](../../../../../docs/standards/workflow-scripts.md)
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
from pathlib import Path

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

# A candidate row: | C-001 | title | source | `decision` | `status` | note |
_ROW = re.compile(r"^\|\s*(C-\d{3})\s*\|.*?\|.*?\|\s*(.*?)\s*\|\s*(.*?)\s*\|", re.M)

_BLANK = ("", "—", "-")


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


def candidate_rows(candidates_path: Path, *, missing_hint: str) -> list[tuple[str, str, str]]:
    """Every `(id, decision, status)` in the file, normalised. One parse, one place.

    `missing_hint` lets each caller say what the absent file costs IT, without a
    second copy of the regex travelling with the sentence.
    """
    if not candidates_path.exists():
        raise FileNotFoundError(f"candidates file not found: {candidates_path}. {missing_hint}")
    return [(cid, normalise_cell(dec), normalise_cell(st))
            for cid, dec, st in _ROW.findall(candidates_path.read_text())]


def candidate_counts(candidates_path: Path) -> dict[str, int]:
    """Count rows by triage state — computed in code, never asked of a model.

    Arithmetic is not delegated: a model once marked four of eight papers past
    window when one was, every flag internally consistent against a date it had
    invented. The same rule applies to any count a prompt or a report asserts.
    """
    rows = candidate_rows(candidates_path, missing_hint=(
        "`triage-candidates` rules the rows in it and `plan-sprint` places what "
        "they ruled; without the file neither has anything to work from."))
    untriaged = [cid for cid, dec, _st in rows if not dec]
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
    return {cid: st for cid, _dec, st in candidate_rows(candidates_path, missing_hint=(
        "Without it there is no `status` column to hold anything to."))}


def candidate_decisions(candidates_path: Path) -> dict[str, str]:
    """Every row's `decision`, normalised, keyed by id — the triaged column.

    THIS IS THE AUTHORITY TRANSFER, ENFORCED RATHER THAN ASSERTED. `decision` was
    `plan-sprint`'s output until triage became its own workflow; it is now
    `triage-candidates`'s alone. Prose in nine documents says so, and prose is
    not a mechanism: every other planning workflow still READS this file and
    still has write access to it in its worktree, and a model that has just
    decided a candidate needs no component is one plausible step from recording
    that conclusion in the column next to it.

    So each of them snapshots this before its run and compares after. Same
    discipline as `candidate_counts`: OBSERVE what the run wrote, never ask it
    what it wrote.

    Normalised via `normalise_cell` — backticks and the several spellings of
    empty all collapse — so a row reformatted from `` `ship` `` to `ship` does
    not read as a ruling changed. The comparison must fire on MEANING, not on
    markup, and it must fire on the SAME meaning the counter sees: two
    hand-written normalisations had already drifted apart once.
    """
    return {cid: dec for cid, dec, _st in candidate_rows(
        candidates_path,
        missing_hint="Without it there is no `decision` column to hold anything to.")}


def rulings_this_run_had_no_right_to(before: dict[str, str],
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
        with `decision` blank, and every workflow guarded by this is a producing
        run. Diffing the two id sets outright made the shared placement
        instruction unfollowable: the run would place a proposal exactly as told
        and then fail its own post-condition. Blank is the absence of a ruling,
        so placing one is not ruling anything.
    """
    # Deletion is `ids_deleted` rather than a branch here, because the claim
    # that it had one definition was false: the comment on
    # `statuses_this_run_had_no_right_to` said row deletion was "already an
    # offence under the `decision` guard", which was true of `plan-sprint` and
    # false of `triage-candidates`, whose count-based post-condition it defeated.
    offences: list[str] = ids_deleted(before, after)
    for cid in after.keys():
        was, now = before.get(cid), after[cid]
        if cid not in before:
            if now:                          # appended ALREADY ruled
                offences.append(cid)
        elif was != now:
            offences.append(cid)             # ruling rewritten
    return offences


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

    comps = sorted(d for d in (tree / COMPONENT_ROOT).iterdir()
                   if d.is_dir() and d.name not in NOT_A_COMPONENT)
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

# THE ONE DEFINITION OF THE COMPONENT LAYER, and it is a `str` rather than a
# `Path` because three of its four consumers build a repo-RELATIVE KEY out of it
# (`f"{COMPONENT_ROOT}/{slug}/roadmap.md"`) and only one joins it onto a tree.
# `Path / str` works; `f"{Path(...)}"` also works but silently makes the key
# format platform-dependent, which is a subtlety a snapshot key cannot afford.
#
# It sits here because §10.1 rule 3 is a consumer count: `existing_work` below,
# `plan_candidates_activities` and `plan_project_activities` all read this layer.
# `plan_candidates` briefly declared its own copy as a `str` beside this one as a
# `Path`, and `plan_project` imported the CHILD's — so narrowing the root in one
# workflow folder would have silently broken the parent's research sweep, which
# is the drift `normalise_cell` exists to record, one directory up.
COMPONENT_ROOT = "docs/development"

# `reviews/` holds review artifacts, not a domain of work. Shared for the same
# reason as the root: two definitions of "what counts as a component" feeding one
# prompt is the same drift, and both readers below render into the same prompt.
NOT_A_COMPONENT = frozenset({"reviews"})


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

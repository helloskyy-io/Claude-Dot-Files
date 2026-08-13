"""plan-candidates' own I/O — one consumer each, so §10.1 rule 3 puts them here.

Every function below reads or judges the COMPONENT LAYER — the directories under
`docs/development/` and the `roadmap.md` at the top of each one. Nothing else in
the family touches that layer: `triage_candidates` rules rows, `plan_sprint`
maintains one file, and `plan_project` reads a diff. One consumer, so they live
with their consumer, and
[`workflow-scripts.md` § Location](../../../../../../docs/standards/workflow-scripts.md)
restates §10.1 rule 3 as BINDING and mechanical — *"consumer count decides, never
taste"*. Rule 6 gives a workflow folder its place to grow the helpers it earns.

WHY THE ROADMAP MAP IS A DIGEST AND NOT A PATH LIST, which is the one design
decision here worth stating. `plan_activities.worktree_state` reports only paths
git says CHANGED, so a `roadmap.md` that was created and a `roadmap.md` that was
edited look identical through it — both are absent from the before-snapshot and
present in the after one. This workflow's whole boundary is the difference
between those two cases: creating a roadmap is its job and editing one is
forbidden. So the map is read from DISK on both sides, over every component
whether git mentions it or not, and the comparison is by content digest.

NOT IDEMPOTENT (§7.1) is not in play here — this module only reads.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

# The component layer, and the one file at the top of each component that this
# workflow creates. `reviews/` is not a component — it is where review artifacts
# land — and `plan_activities.existing_work` already excludes it for the same
# reason.
COMPONENT_ROOT = "docs/development"
_NOT_A_COMPONENT = {"reviews"}

# A phase the model planned into a roadmap it was only meant to charter. Matches
# the SHAPE of the claim rather than any wording: a phase reference always
# carries its number (`phase1_`, `Phase 2`, `phase-3`), and an estimate always
# carries a figure attached to a unit. Prose ABOUT the boundary — "phases are
# `plan-feature`'s", "hour estimates are not mine to make" — carries neither a
# digit nor a unit and passes, which is the distinction that has to hold for the
# charter to be able to say what it is not.
_PHASE_PLANNED = re.compile(r"phase[\s_-]*\d", re.I)
_HOURS_ESTIMATED = re.compile(r"\d+\s*(?:h\b|hrs?\b|hours?\b)", re.I)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def component_roadmaps(tree: Path) -> dict[str, str]:
    """Every `docs/development/*/roadmap.md` on disk, mapped to a content digest.

    READ FROM DISK, NOT FROM GIT, and that is what makes the create-versus-edit
    boundary observable at all. `worktree_state` lists changed paths, so a
    created roadmap and an edited one are the same shape through it: absent
    before, present after. Walking the tree puts the pre-existing roadmap in the
    BEFORE map with its digest, so an edit shows as a changed value on a key that
    was already there and a creation shows as a new key.

    Keyed by REPO-RELATIVE PATH so both snapshots key the same way regardless of
    which worktree they were taken in, and so a failure message names something
    the operator can open.

    A MISSING `docs/development/` IS AN EMPTY MAP, not an error: a repo with no
    component layer yet is exactly the repo this workflow is most useful in, and
    a run that creates the first component must not fail for having created it.
    """
    root = tree / COMPONENT_ROOT
    if not root.is_dir():
        return {}
    found: dict[str, str] = {}
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name in _NOT_A_COMPONENT:
            continue
        roadmap = d / "roadmap.md"
        if roadmap.is_file():
            found[f"{COMPONENT_ROOT}/{d.name}/roadmap.md"] = _digest(roadmap)
    return found


def roadmaps_edited(before: dict[str, str], after: dict[str, str]) -> list[str]:
    """Roadmaps that existed before this run and whose content moved. Forbidden.

    THE BOUNDARY AGAINST `plan-feature`, AS A COMPARISON. This workflow creates a
    component's charter and never revises one: the phases, the epics and the hour
    estimates that go into an existing roadmap are `plan-feature`'s output, and a
    run that edits a roadmap has either written those or rewritten somebody's
    scope decision. Both are somebody else's call.

    ONLY KEYS PRESENT ON BOTH SIDES, which is the same contract
    `statuses_this_run_had_no_right_to` has and for the same reason: a NEW key is
    a created roadmap, which is the whole point of the run, and a key that went
    MISSING is a deletion — reported by `plan_activities.ids_deleted` over the
    same pair, because this comparison is blind to it by construction.
    """
    return sorted(rel for rel in before.keys() & after.keys()
                  if before[rel] != after[rel])


def roadmaps_created(before: dict[str, str], after: dict[str, str]) -> list[str]:
    """Roadmaps this run brought into existence — its legitimate output."""
    return sorted(after.keys() - before.keys())


def phase_planning_in(tree: Path, created: list[str]) -> dict[str, list[str]]:
    """Created roadmaps that planned phases or estimated hours. Also forbidden.

    THE OTHER HALF OF THE SAME BOUNDARY, and the half a path rule cannot reach.
    Forbidding the phase-doc PATH stops a run writing `phase1_x.md`; it does
    nothing about a run that writes the phase breakdown into the roadmap it was
    allowed to create. That file is this workflow's own output, so no path or
    snapshot comparison can see inside it — the only observable is its content.

    Returns the offending lines rather than a boolean, because the failure has to
    be actionable: "this roadmap plans phases" sends a reader looking, and
    "line 14: `### Phase 2 — 20h`" is the finding.

    MATCHES THE CLAIM SHAPE, NOT A VOCABULARY. A charter is REQUIRED to say what
    it is not — "phases are not planned here; `plan-feature` writes them" — so a
    check keyed on the word `phase` would forbid the sentence that makes the
    boundary legible. A planned phase carries a NUMBER (`phase1_`, `Phase 2`) and
    an estimate carries a figure with a unit (`20h`, `40 hours`); the disclaimer
    carries neither.
    """
    offences: dict[str, list[str]] = {}
    for rel in created:
        lines = [f"line {n}: {line.strip()}"
                 for n, line in enumerate((tree / rel).read_text().splitlines(), 1)
                 if _PHASE_PLANNED.search(line) or _HOURS_ESTIMATED.search(line)]
        if lines:
            offences[rel] = lines
    return offences


def component_dirs(tree: Path) -> set[str]:
    """Every component directory under `docs/development/`, by name.

    Paired with `component_roadmaps` to catch the EMPTY SHELL: a directory this
    run created with no charter in it. That is not a hypothetical — the pipeline
    has already produced one. `docs/development/fleet-reliability/` holds five
    verified research papers and a synthesis, and no planning document of any
    kind, because the parent's research step created the folder with a `mkdir`
    and nothing ahead of it wrote what the component IS.
    """
    root = tree / COMPONENT_ROOT
    if not root.is_dir():
        return set()
    return {d.name for d in root.iterdir()
            if d.is_dir() and d.name not in _NOT_A_COMPONENT}


def shells_without_a_charter(before_dirs: set[str], after_dirs: set[str],
                             after_roadmaps: dict[str, str]) -> list[str]:
    """Component directories this run created that hold no `roadmap.md`.

    THE DOCUMENTATION STANDARD'S RULE 1, MADE OBSERVABLE: *"A file exists only
    when it carries binding content. An empty cell is a reserved name, never a
    stub doc."* A directory is the same thing one level up — a reserved name that
    reads as a component and holds nothing anyone can act on.

    Judged against directories this run ADDED, never against the tree as it
    stands. Sixteen of this repo's seventeen components have no `roadmap.md`
    today, so a tree-wide sweep would fail every run over work nobody in this
    dispatch did — which is the shape of guard that gets deleted rather than
    fixed.
    """
    return sorted(name for name in after_dirs - before_dirs
                  if f"{COMPONENT_ROOT}/{name}/roadmap.md" not in after_roadmaps)


def component_inventory(tree: Path) -> str:
    """What already exists, so the run does not stand up a second home for it.

    Computed in code and handed over rather than asked of the model, for the
    reason `existing_work` states: a run that scaffolds a component for work an
    existing one already covers creates the duplication the candidates file was
    built to prevent — and unlike a duplicate row, a duplicate component folder
    is a durable structure that later research and planning both write into.

    THE THREE STATES ARE NAMED SEPARATELY because they mean different things to
    this workflow and collapsing them is how the wrong one gets picked. A
    component with a charter is a target `plan-feature` can already plan into. A
    component with research but no charter is the shell described in
    `component_dirs` — the ONE case where this workflow legitimately writes into
    an existing directory, since adding the missing charter is not editing a
    roadmap that does not exist. A bare directory is neither.
    """
    root = tree / COMPONENT_ROOT
    if not root.is_dir():
        return (f"**`{COMPONENT_ROOT}/` does not exist.** Every component you "
                f"scaffold is the first one.")

    lines = [f"**Existing components under `{COMPONENT_ROOT}/`, counted in code "
             f"— a candidate whose work falls inside one of these needs NO "
             f"scaffolding:**", ""]
    charted = shells = 0
    for name in sorted(component_dirs(tree)):
        d = root / name
        has_roadmap = (d / "roadmap.md").is_file()
        has_research = (d / "research").is_dir()
        if has_roadmap:
            charted += 1
            mark = "**HAS A CHARTER** — `plan-feature` can plan into it as it stands"
        elif has_research:
            shells += 1
            mark = ("**RESEARCH BUT NO CHARTER** — a shell. It has evidence and "
                    "nothing saying what the component IS")
        else:
            mark = "no roadmap, no research pool"
        lines.append(f"  - `{COMPONENT_ROOT}/{name}/` — {mark}")

    lines += ["", f"**{charted} of these carry a charter; {shells} hold research "
                  f"with no charter above it.** A shell is the one existing "
                  f"directory you may write into: adding the `roadmap.md` it "
                  f"never had is CREATING a charter, not editing one, and it is "
                  f"the cheapest correction available to this run."]
    return "\n".join(lines)


def shipped_working_set(decisions: dict[str, str]) -> str:
    """The `ship` rows, counted in code, and what an empty set MEANS.

    Counted rather than asked, for the reason `candidate_counts` states: a model
    once marked four of eight papers past window when one was, every flag
    internally consistent against a date it had invented.

    THE WORKING SET IS EVERY `ship` ROW, NOT THE RECENT ONES, and that is
    deliberate rather than lazy. There is no column recording that a candidate
    has been scaffolded — `status` belongs to a later process and this workflow
    may not write it — so "recently triaged" is not a fact available to anybody
    here. Re-examining the whole shipped set each run is what makes the workflow
    IDEMPOTENT instead: a candidate whose component already exists needs no
    scaffolding, the run says so, and nothing is written. The check is cheap
    because the answer is a directory listing.
    """
    ship = sorted(cid for cid, dec in decisions.items() if dec == "ship")
    if not ship:
        return ("**Counted in code, authoritative — do not recount:** "
                f"{len(decisions)} candidates, **none ruled `ship`**.\n\n"
                "**THERE IS NOTHING TO SCAFFOLD, and that is a state rather than "
                "a fault.** Either triage has not run, or it ruled everything "
                "`reject` / `requires review`. Say which, in one line, change "
                "nothing, and open the PR. Do NOT go looking for work in the "
                "rows that were not ruled `ship` — an untriaged row is not yours "
                "to read as an intention, and a `requires review` row is a "
                "question the operator has not answered.")
    return (f"**Counted in code, authoritative — do not recount:** "
            f"{len(decisions)} candidates, **{len(ship)} ruled `ship`**.\n\n"
            f"Those {len(ship)} rows are your ENTIRE working set: "
            f"{', '.join(ship)}. **Every other row is invisible to you** — a "
            f"`reject` is settled, a `requires review` is the operator's open "
            f"question, and a blank `decision` means triage has not happened. "
            f"None of the three is an instruction to build somewhere for it.")

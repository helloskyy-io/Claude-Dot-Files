"""plan-project's own I/O — one consumer each, so §10.1 rule 3 puts them here.

Every function here serves the PARENT's decisions: which components are new,
where their research pool belongs, and — since `plan-candidates` — creating that
pool for a candidate triage has agreed to. Nothing else in the family calls any
of them, and [`workflow-scripts.md` § Location](../../../../../../docs/standards/workflow-scripts.md)
restates §10.1 rule 3 as BINDING and mechanical — *"consumer count decides,
never taste"*. Rule 6 gives a one-file workflow folder its place to grow the
helper it has earned.

THEY SAT ON THE FAMILY'S SHARED SURFACE UNTIL THE SPLIT AUDIT WAS FINISHED
PROPERLY. `plan_activities`'s docstring listed five functions it had checked
against rule 3 and moved two of them out; these two were single-consumer the
whole time and were simply not in the list, so a file whose stated invariant is
*"shared by definition"* held two functions that were not. Counted this time
rather than eyeballed.

`scaffold_candidate_components` LANDED HERE FOR THE SAME REASON AND NOT BECAUSE
IT IS CONVENIENT. Its only consumer is `plan_project`, and it is the second
consumer of `component_dir` — which is already in this file, so rule 3 moves
nothing. That it needed no migration is a consequence of the rule, not a reason
to skip checking it.

NOT IDEMPOTENT (§7.1) applies to `scaffold_candidate_components` alone; the
other two only read. It is CONVERGENT rather than idempotent: it creates nothing
where a directory already exists, so a replay against an unchanged tree is a
no-op and a replay after `plan-feature` has filled a component in leaves it
alone. Under Temporal a retry is a NEW ATTEMPT, and this one is safe to repeat.
"""

from __future__ import annotations

import re
from pathlib import Path

from .. import plan_activities as act

# Strips the leading marker so a section name is just its name.
_SECTION_NAME = re.compile(r"^## Sprint:\s*")


def new_sprint_sections(worktree: Path, sprint_rel: str, *, base_ref: str) -> list[str]:
    """Sprint sections THIS DISPATCH added — read from the diff, in code.

    A NON-MODEL OBSERVABLE. The parent must know which components are new so it
    can research and plan only those, and asking the triage child to report them
    would make the parent trust an account rather than read the artifact. `git`
    already knows, and a diff is not something a model can be wrong about.

    `base_ref` IS REQUIRED AND HAS NO DEFAULT, deliberately. It defaulted to
    `origin/main`, which answers a different question — *what has this BRANCH
    accumulated* rather than *what has THIS RUN added* — and the two diverge on
    exactly the path the entrypoints document: a `--pr` redispatch cuts its
    worktree from a branch that already carries a `## Sprint:` heading an
    earlier pass added and researched, so the section reads as new again and
    buys a second full research cycle for it. `plan_activities.py`'s snapshot
    comparators state the same rule for the same reason — *snapshot around the
    run, never diff against the base* — and a caller cannot inherit the wrong
    base by saying nothing.

    Matched on the added-heading form specifically: a section merely EDITED
    shows as a changed body with no added `## Sprint:` line, and researching an
    existing component because its prose moved would spend a full cycle on
    nothing.
    """
    out = act.git_output(
        worktree, ["git", "diff", f"{base_ref}...HEAD", "--", sprint_rel],
        "The parent cannot tell which components are new, and guessing would "
        "research the wrong ones.",
    )
    return [
        _SECTION_NAME.sub("", line[1:]).split("—")[0].strip()
        for line in out.splitlines()
        if line.startswith("+## Sprint:")
    ]


def component_dir(tree: Path, section_name: str) -> Path:
    """`Fleet Reliability` -> `docs/development/fleet-reliability`.

    The convention the whole tree already follows, applied in code rather than
    asked of a model — a component whose folder name does not match its sprint
    section is invisible to every reconciliation that walks one against the other.

    `tree`, not `repo_root`: the only caller passes its WORKTREE, because the
    research pool this returns is written on the branch. The parameter was named
    `repo_root` and the call was correct anyway, which is the combination that
    survives review and breaks on the second caller.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", section_name.lower()).strip("-")
    if not slug:
        raise ValueError(f"sprint section {section_name!r} yields no folder name")
    return tree / "docs" / "development" / slug


def scaffold_candidate_components(worktree: Path, candidates_path: Path) -> list[str]:
    """Create the folder and seed the synthesis for every shipped candidate that has neither.

    THIS IS AN ACTIVITY, NOT A CHILD, AND THE DISTINCTION IS THE WHOLE DESIGN.
    There is no prompt, no entry script and no model call. The job is to move
    what triage already decided to where the next step reads from — the operator's
    words are *"it just needs to move the info over to the correct place so the
    next step can happen"*. Nothing in that needs judgement, so nothing in it
    should cost a dispatch: this runs for free, deterministically, and is
    unit-testable without a model.

    An earlier attempt built it as a model child — 1,605 lines and a 173-line
    prompt for this — and every hold the review raised was a consequence of it
    being a dispatch at all. It was closed rather than repaired.

    FOUR CONDITIONS, AND EACH SKIP IS A DECISION SOMEBODY ELSE ALREADY MADE:

      * `decision` is not `ship` — triage has not agreed to do it, or has refused.
      * `status` is not `open` — it is already handled.
      * `component` is blank — nobody has said where it goes. **That is an
        unanswered question, not an error**, and answering it is not this code's
        job: the filer knows and this does not. A blank scaffolds nothing and
        fails nothing.
      * The directory already exists — the candidate EXTENDS something already
        planned, so there is nothing to scaffold. Seeding a synthesis into a
        live component's pool would put a one-line proposal on top of real
        research.

    WHAT IT DOES NOT DO: no `roadmap.md`, no phase docs. `sprint.md` says every
    component gets both, and `plan-feature` writes them. This creates a folder
    and a seeded synthesis and stops.

    NOT IDEMPOTENT in the §7.1 sense of "safe to replay against a changed tree",
    but it is CONVERGENT against an unchanged one: the directory-exists check
    makes a second run over the same file a no-op. A retry that lands after
    `plan-feature` has filled the component in will correctly leave it alone.

    Returns the slugs it created, in file order — the research step's input.
    """
    created: list[str] = []
    rows = act.candidate_rows(candidates_path, missing_hint=(
        "Without it there is nothing to scaffold from, and the research step "
        "that reads what this creates has no input."))

    for row in rows:
        if row.decision != "ship" or row.status != "open" or not row.component:
            continue
        target = component_dir(worktree, row.component)
        if target.exists():
            continue
        (target / "research").mkdir(parents=True)
        (target / "research" / "synthesis.md").write_text(
            _seed(row, target.name))
        created.append(target.name)

    return created


def _seed(row: act.CandidateRow, slug: str) -> str:
    """The first document in a new component's pool — provenance, then the summary.

    Deliberately thin. It is a HANDOFF, not a research paper: it says where this
    came from and what was proposed, so the research child that runs next has a
    brief instead of an empty directory. `research_write` rewrites this file with
    real findings; anything more elaborate here would be written to be discarded.

    The `C-NNN` id is the load-bearing part. It is the only link back from the
    component to the row that authorised it, and without it a reader finding this
    folder cannot tell scaffolding from abandoned work.
    """
    return (
        f"# {slug} — synthesis\n"
        f"\n"
        f"**This component arrived from project-wide planning as a candidate for "
        f"inclusion — [`{row.id}`]"
        f"(../../../standards/architecture/research/candidates.md).** It was ruled "
        f"`ship` by `triage-candidates` and scaffolded by `plan-candidates`, which "
        f"creates the folder and this file and nothing else. **No research has been "
        f"done yet**, and the `roadmap.md` and phase docs that `plan-feature` writes "
        f"do not exist.\n"
        f"\n"
        f"## The candidate as filed\n"
        f"\n"
        f"{row.title}\n"
        f"\n"
        f"> That summary is a PROPOSAL, not a finding — it is what was written when "
        f"the candidate was filed, carried across verbatim. The next research pass "
        f"replaces this file.\n"
    )

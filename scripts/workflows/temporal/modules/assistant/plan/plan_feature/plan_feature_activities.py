"""plan-feature's own I/O — one consumer each, so §10.1 rule 3 puts them here.

[`workflow-scripts.md` § Location](../../../../../../../docs/standards/workflow-scripts.md)
restates §10.1 rule 3 as BINDING and mechanical — *"consumer count decides, never
taste"* — and rule 6 gives a workflow folder its place to grow the helpers it has
earned. Everything below has exactly one consumer: `plan_feature_workflow`.

WHAT THIS MODULE IS FOR. `plan-feature` writes a component's `roadmap.md` and its
numbered phase docs. Three of its four prohibitions are properties of FILENAMES
and one is a property of PROSE, and none of them is visible to the path- and
column-comparators the planning family already shares:

  * `plan_activities.boundary_crossings` answers *did this run write outside its
    component?* — it cannot tell `phase2_x.md` from `the_thing.md` inside it.
  * `plan_activities.ids_deleted` answers *did a phase doc VANISH?* when handed
    the maps below, which is what a rename or a renumber looks like from outside.
    That one is reused rather than re-implemented, deliberately.
  * Nothing anywhere answers *is this a valid phase filename*, *does this new
    phase reuse a retired number*, or *did the run size the work in hours*.

THE PHASE NUMBER IS IDENTITY, AND THAT IS WHY TWO OF THESE EXIST.
[Documentation Standard § Phase Numbering and Roadmap Ordering](../../../../../../../docs/standards/documentation/documentation_standard.md)
is binding and states three separable layers: the phase NUMBER is immutable
identity, the roadmap POSITION is the logical order, and the sprint position is
execution order. A run that renumbers to express order has confused the first
layer with the second, and the cost is measured — this repo came within one
dispatch of renaming sixteen phase files across forty-three references to buy a
reordering freedom it already had. The standard names the filename grammar and
calls a CI lint over it *"the recommended guardrail"*; `malformed_phase_docs` is
that lint, applied at the moment of writing rather than after the fact.

HOURS ARE DETECTED BY SHAPE, NEVER BY THE WORD. Sizing belongs to `plan-verify`
— an author sizing their own decomposition is defending it — so a written hour
figure is a boundary crossing here. But *"true for a few hours"* and *"a shelf
life measured in hours"* are ordinary prose, and this repo's planning docs
contain exactly three such phrases and ZERO estimates. A pattern keyed on the
word `hours` would fail three runs that did nothing wrong on the first component
that quoted one of those lines. `_HOURS` therefore requires an estimate SHAPE —
a tilde, a bare parenthetical, or an explicit sizing label — which none of the
three prose instances has.

NOT IDEMPOTENT (§7.1) is not in play here — this module only reads.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

# The binding filename grammar, verbatim from the Documentation Standard's
# "Filename pattern (binding)" block: `phase{N}_{descriptor}.md` canonical, with
# `phase{N}{a-z}_{descriptor}.md` as rule 6's narrow sub-letter carve-out.
# Anchored at both ends because the whole point is that no OTHER form is valid.
_PHASE_FILE = re.compile(r"^phase(\d+)([a-z]?)_[a-z0-9_-]+\.md$")

# What a phase doc might be NAMED, which is deliberately wider than what one may
# be named. `phase_notes.md`, `Phase3.md` and `phase03b(old)_x.md` all have to
# reach `malformed_phase_docs` to be reported, so the sweep matches loosely and
# the grammar above judges. A glob of `phase*.md` alone would miss `Phase3.md`.
_LOOKS_LIKE_A_PHASE = re.compile(r"^phase", re.I)

# An hour ESTIMATE, in the three spellings a plan can carry one. The Documentation
# Standard's own worked example is `### 1-2. DAS Phase 1 + Version-of-Record
# Phase A (~30 hrs)`, which the first two alternatives both catch.
#
# EVERY ALTERNATIVE REQUIRES A DIGIT ADJACENT TO THE UNIT *AND* AN ESTIMATE
# MARKER. That second requirement is the whole discriminator: without it the
# pattern reads "measured in hours" as a finding.
#
# THE `\.?` AFTER THE LABEL IS A FIX, NOT DECORATION. `[^.\n]` keeps the label
# and the figure inside one sentence — without it, *"the estimate. It took 3
# hours"* reads as a finding — and it also meant the pattern could not cross the
# period in the abbreviation `Est.`, so `Est. 2.5 hours` went undetected. Allowing
# exactly one period immediately after the label, and none after, keeps the
# sentence bound and closes the abbreviation. Found by the control below
# predicting a catch that did not happen.
_HOURS = re.compile(
    r"""
      ~\s*\d+(?:\.\d+)?\s*(?:h|hrs?|hours?)\b            # ~30 hrs, ~8h
    | \(\s*\d+(?:\.\d+)?\s*(?:h|hrs?|hours?)\s*\)        # (30 hrs)
    | \b(?:est|estimate[sd]?|sizing|effort)\b\.?
      [^.\n]{0,24}?\d+(?:\.\d+)?\s*(?:h|hrs?|hours?)\b   # Estimate: 8 hours, Est. 2.5 hours
    """,
    re.I | re.X,
)


def phase_docs(component: Path) -> dict[str, str]:
    """Every phase-doc-shaped file directly in the component dir, name -> content hash.

    KEYED BY FILENAME, HASHED BY CONTENT, and both halves are load-bearing.
    The key is what `plan_activities.ids_deleted` compares, so a rename shows up
    as a disappearance — which is exactly what a renumber IS, seen from outside.
    The value is what lets a caller tell a phase doc that was rewritten from one
    that was merely left alone, without holding two copies of the tree.

    A MISSING COMPONENT DIRECTORY IS AN EMPTY MAP, NOT AN ERROR. The before-read
    happens on a component that may hold nothing but `research/`, which is the
    normal case: `plan-candidates` creates the folder and the seed and nothing
    else. Empty on both sides is the same answer as unchanged.

    Files only, and only at the top level: `research/raw/phase_something.md` is a
    research paper that happens to be named like a phase, and this workflow
    neither writes nor judges anything under `research/`.
    """
    if not component.is_dir():
        return {}
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(component.iterdir())
            if p.is_file() and _LOOKS_LIKE_A_PHASE.match(p.name)}


def phase_number(name: str) -> int | None:
    """`phase12b_x.md` -> 12. None when the name is not a conformant phase doc.

    The sub-letter is deliberately discarded: rule 6 makes `2a` and `2b` two
    atomic chunks of ONE phase planned together, so they share an identity and a
    number, and a caller asking "which numbers are taken" wants 2 for both.
    """
    m = _PHASE_FILE.match(name)
    return int(m.group(1)) if m else None


def malformed_phase_docs(before: dict[str, str], after: dict[str, str]) -> list[str]:
    """New phase-doc-shaped files whose names break the binding grammar.

    JUDGES ONLY WHAT THIS RUN ADDED. A pre-existing non-conformant name is
    somebody else's legacy and renaming it is explicitly out of scope — the
    number is identity, and "fixing" one costs a cross-reference sweep to buy
    nothing. A guard that failed the run over a file it is forbidden to touch
    would make a conformant component unplannable.
    """
    return sorted(name for name in after
                  if name not in before and not _PHASE_FILE.match(name))


def reused_phase_numbers(before: dict[str, str],
                         after: dict[str, str]) -> list[tuple[str, int]]:
    """New phase docs whose number was already taken. Returns `(filename, number)`.

    RULE 1 AND RULE 5 TOGETHER, AND RULE 5 IS THE ONE THAT BITES. A new phase
    takes `max(existing) + 1`; gaps are correct and are NOT free numbers, because
    *"external references in code comments, commit messages, and sprint docs may
    still point at them, and reusing the number creates silent ambiguity."*

    So the taken set is every number visible in `before`, gaps included by
    construction — a number absent from `before` cannot be a gap this run can
    see. What this cannot catch is a number retired before the component was
    committed; that is archaeology, and the roadmap's own tombstone entries are
    where a run reads it.

    A malformed new name yields no number and is reported by
    `malformed_phase_docs` instead; reporting it twice would make one mistake
    look like two.
    """
    taken = {n for n in (phase_number(name) for name in before) if n is not None}
    out: list[tuple[str, int]] = []
    for name in sorted(after):
        if name in before:
            continue
        num = phase_number(name)
        if num is not None and num in taken:
            out.append((name, num))
    return out


def hour_estimates(component: Path, tree: Path) -> list[str]:
    """`relpath:line: matched text` for every hour estimate in the component's plan.

    SIZING IS `plan-verify`'S, AND THAT IS A DESIGN DECISION RATHER THAN A
    DIVISION OF LABOUR. An author sizing their own decomposition is defending it;
    a fresh reader sizing it is a second opinion. It is the same `author != judge`
    rule the research and build families split on, applied to a number.

    SCOPED TO THE FILES THIS WORKFLOW WRITES — `roadmap.md` and the phase docs at
    the component's top level. Naming the scope matters: `research/` is outside
    it, and a synthesis legitimately reporting a measured wall-clock in hours is
    evidence, not an estimate, and is not this guard's business.

    Returns citations rather than a boolean because the operator's next question
    is always *where*, and a guard that answers "somewhere in the plan" sends
    them to grep for it.
    """
    if not component.is_dir():
        return []
    targets = [p for p in sorted(component.iterdir())
               if p.is_file() and (p.name == "roadmap.md" or _LOOKS_LIKE_A_PHASE.match(p.name))]
    found: list[str] = []
    for path in targets:
        rel = path.relative_to(tree)
        for lineno, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            for m in _HOURS.finditer(line):
                found.append(f"{rel}:{lineno}: {m.group(0).strip()}")
    return found


def planning_state(component: Path, tree: Path) -> str:
    """What this component already has, counted in code and handed over.

    COUNTED HERE SO THE PROMPT CANNOT ASSERT A STATE IT INVENTED, the discipline
    `candidate_counts` states for the triage working set. The two states this
    distinguishes are genuinely different jobs and a model reading an unlabelled
    directory listing will conflate them: a component with no roadmap is being
    planned for the first time, and one with a roadmap is being EXTENDED — where
    the existing phase numbers are taken, the existing files are not to be
    touched, and the new phase is `max + 1`.
    """
    rel = component.relative_to(tree)
    docs = phase_docs(component)
    roadmap = component / "roadmap.md"
    taken = sorted(n for n in (phase_number(name) for name in docs) if n is not None)

    if not roadmap.is_file() and not docs:
        return (
            f"**Counted in code, authoritative — do not recount:** `{rel}/` has "
            f"**no `roadmap.md` and no phase docs**.\n\n"
            f"**This component is being planned for the FIRST time.** Its whole plan "
            f"is yours to write: one `roadmap.md`, and one `phaseN_<name>.md` per "
            f"phase. **Numbering starts at `phase1_`.**"
        )

    listed = ", ".join(f"`{name}`" for name in sorted(docs)) or "none"
    ceiling = (f"**The next free phase number is {max(taken) + 1}.**"
               if taken else
               "**No conformant phase number is in use; a new phase starts at 1.**")
    gaps = ("" if len(taken) < 2 or taken == list(range(taken[0], taken[-1] + 1)) else
            f" The sequence has gaps ({', '.join(str(n) for n in taken)}) and **a gap "
            f"is not a free number** — a retired phase's number is never reused, "
            f"because references to it survive elsewhere.")

    return (
        f"**Counted in code, authoritative — do not recount:** `{rel}/` already has "
        f"{'a `roadmap.md`' if roadmap.is_file() else '**no `roadmap.md`**'} and "
        f"**{len(docs)} phase doc(s)**: {listed}.\n\n"
        f"**This component is being EXTENDED, not planned from scratch.** {ceiling}{gaps} "
        f"Every existing phase doc stays exactly as it is — same filename, same "
        f"number. If a phase's position in the rollout changes, **you move its line "
        f"in `roadmap.md` and the file does not move.**"
    )


def research_inventory(component: Path, tree: Path) -> str:
    """This component's own pool — the PRIMARY evidence, named and counted.

    `plan_activities.evidence_block` already points a planning run at every pool
    in the tree and teaches the convention. It cannot say which one is THIS run's,
    because it is handed a repo and not a component. This block does, and the
    distinction decided a real failure one layer up: a brief named four files, the
    run read exactly those four, and the paper that answered the question sat
    unopened in the pool.

    AN EMPTY POOL IS REPORTED WITH ITS ZERO, never omitted — the same rule
    `evidence_block` states. A component whose research never ran is a component
    whose plan is about to be written from priors, and that is the single most
    useful thing this block can tell the run before it starts.
    """
    pool = component / "research"
    if not pool.is_dir():
        return (f"**`{component.relative_to(tree)}/research/` DOES NOT EXIST.** This "
                f"component has no evidence pool at all. Say so plainly in your report "
                f"and name, per phase, what the plan is resting on instead.")

    papers = sorted(p.name for p in (pool / "raw").glob("*.md")) if (pool / "raw").is_dir() else []
    syn = pool / "synthesis.md"
    rel = pool.relative_to(tree)

    lines = [f"**Your PRIMARY evidence is `{rel}/`, counted in code: "
             f"{len(papers)} paper(s), "
             f"{'`synthesis.md` present' if syn.is_file() else '**NO `synthesis.md`**'}.**",
             ""]
    if syn.is_file():
        lines += [
            f"**Read `{rel}/synthesis.md` and plan from it.** A synthesis is written to "
            f"be consumed by exactly this step. The paper list below is for COVERAGE "
            f"checking — noticing a title the synthesis never mentions is a finding for "
            f"your report. Open a paper only when a phase cannot be written without it, "
            f"and say which and why.",
            "",
        ]
    else:
        lines += [
            "**There is no synthesis, so there is no rolled-up evidence.** Say so in "
            "your report and name what each phase rests on instead. Do not silently "
            "plan from priors and present the result as evidence-backed.",
            "",
        ]
    lines += [f"  - `{n}`" for n in papers] or ["  *(the pool holds no papers)*"]
    return "\n".join(lines)

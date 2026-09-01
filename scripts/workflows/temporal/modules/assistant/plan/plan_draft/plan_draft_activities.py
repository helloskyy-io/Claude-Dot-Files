"""plan-draft's own I/O — one consumer each, so §10.1 rule 3 puts them here.

[`workflow-scripts.md` § Location](/opt/skyy-net/skyynet-master-planning/standards/workflow-scripts.md)
restates §10.1 rule 3 as BINDING and mechanical — *"consumer count decides, never
taste"* — and rule 6 gives a workflow folder its place to grow the helpers it has
earned. Everything DEFINED below has exactly one consumer: `plan_draft_workflow`.

TWO SYMBOLS ARE NOW ALIASES RATHER THAN DEFINITIONS, and the rule is what moved
them. `phase_docs` and the hour pattern acquired a second consumer the day
`plan-refine` landed — the fresh-context reader asks *what am I reading, and how
many phases must I size?* of the first, and produces as its DELIVERABLE the
shape the second exists to forbid here. Rule 3 puts a two-consumer helper on the
shared surface, so their definitions are in `plan_activities` and this module
reaches them by name. The round trip is the rule working: `checked_boxes` and
`candidate_decisions` made the same journey when this workflow itself landed.

WHAT THIS MODULE IS FOR. `plan-draft` writes a component's `roadmap.md` and its
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
[Documentation Standard § Phase Numbering and Roadmap Ordering](/opt/skyy-net/skyynet-master-planning/standards/documentation/documentation_standard.md)
is binding and states three separable layers: the phase NUMBER is immutable
identity, the roadmap POSITION is the logical order, and the sprint position is
execution order. A run that renumbers to express order has confused the first
layer with the second, and the cost is measured — this repo came within one
dispatch of renaming sixteen phase files across forty-three references to buy a
reordering freedom it already had. The standard names the filename grammar and
calls a CI lint over it *"the recommended guardrail"*; `malformed_phase_docs` is
that lint, applied at the moment of writing rather than after the fact.

HOURS ARE DETECTED BY SHAPE, NEVER BY THE WORD. Sizing belongs to `plan-refine`
— an author sizing their own decomposition is defending it — so a written hour
figure is a boundary crossing here. But *"true for a few hours"* and *"a shelf
life measured in hours"* are ordinary prose, and this repo's planning docs
contain exactly three such phrases and ZERO estimates. A pattern keyed on the
word `hours` would fail three runs that did nothing wrong on the first component
that quoted one of those lines. `act.HOUR_ESTIMATE` therefore requires an estimate
SHAPE — a tilde, a bare parenthetical, or an explicit sizing label — which none of
the three prose instances has. **The pattern is shared with `plan-refine`, which
uses it as the deliverable it must produce**, so the shape this workflow forbids
and the shape that workflow writes cannot drift apart.

NOT IDEMPOTENT (§7.1) is not in play here — this module only reads.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from pathlib import Path

from .. import plan_activities as act
# PROMOTED 2026-08-19: `plan_refine` gained a phase-doc write grant and needs the
# same two, so §10.1 moved them to the family layer. Re-exported here rather
# than rewritten at ~20 call sites and in the observer strings that name them.
from ..plan_activities import plan_boxes, plan_docs  # noqa: F401

# The binding filename grammar, verbatim from the Documentation Standard's
# "Filename pattern (binding)" block: `phase{N}_{descriptor}.md` canonical, with
# `phase{N}{a-z}_{descriptor}.md` as rule 6's narrow sub-letter carve-out.
# Anchored at both ends because the whole point is that no OTHER form is valid.
# `\A…\Z` for the reason `_LOOKS_LIKE_A_PHASE` carries: `$` matches before a
# trailing newline, and this pattern is what decides whether a NAME is a
# conformant phase doc.
_PHASE_FILE = re.compile(r"\Aphase(\d+)([a-z]?)_[a-z0-9_-]+\.md\Z")

# PROMOTED TO THE SHARED SURFACE WHEN `plan-refine` BECAME A SECOND CONSUMER, per
# §10.1 rule 3 — *consumer count decides, never taste*. Reached through `own.` so
# this module's callers, its registry entries and its tests keep one spelling; the
# DEFINITION lives once, in `plan_activities`, which is what stops a `phase*.md`
# sweep and an hour pattern from acquiring second copies that drift.
#
# The asymmetry with `plan_docs` below survives the move and is still the point:
# `plan_docs` must equal the case-sensitive WRITE GRANT `[^/]+\.md$`, while
# `phase_docs` answers the wider *what is a phase doc*.
phase_docs = act.phase_docs
_HOURS = act.HOUR_ESTIMATE

# The other half of the output, and the only top-level name that is not a phase
# doc. Named rather than spelled inline because three readers below test for it.
ROADMAP = "roadmap.md"


# `Phase 4`, `**Phase 4**`, `### Phase 4 — name`. Case-insensitive because a
# roadmap heading and a sprint bullet do not agree on it.
_PHASE_IN_PROSE = re.compile(r"\bPhase\s+(\d+)\b", re.I)


def phase_number(name: str) -> int | None:
    """`phase12b_x.md` -> 12. None when the name is not a conformant phase doc.

    The sub-letter is deliberately discarded: rule 6 makes `2a` and `2b` two
    atomic chunks of ONE phase planned together, so they share an identity and a
    number, and a caller asking "which numbers are taken" wants 2 for both.
    """
    m = _PHASE_FILE.match(name)
    return int(m.group(1)) if m else None


def taken_phase_numbers(component: Path) -> set[int]:
    """Every phase number that is a LIVE IDENTITY here, not just a filename.

    A PHASE EXISTS BEFORE ITS DOCUMENT DOES, and reading only `phaseN_*.md` misses
    that. Measured on the first `plan-draft` run ever executed: the
    `workflow-decomposition` component had three phases named in `roadmap.md` and
    ZERO phase docs, so this returned empty and `planning_state` told the run
    *"No conformant phase number is in use; a new phase starts at 1."* Under a
    block headed **Counted in code, authoritative — do not recount.**

    The run disbelieved it, checked the roadmap, and numbered from 4 — and said so
    in its report. That is the run being better than its instructions, which is not
    a control. Numbering from 1 would have collided with three live identities and
    orphaned every reference in `roadmap.md`, `sprint.md` and the research pool.

    A number is retired-but-taken forever, so the union is the answer and a gap in
    it is never a free number.
    """
    numbers = {n for n in (phase_number(name) for name in phase_docs(component))
               if n is not None}
    roadmap = component / "roadmap.md"
    if roadmap.is_file():
        numbers |= {int(m.group(1))
                    for m in _PHASE_IN_PROSE.finditer(roadmap.read_text())}
    return numbers


def malformed_phase_docs(before: dict[str, str], after: dict[str, str]) -> list[str]:
    """New top-level plan files that are neither `roadmap.md` nor a valid phase doc.

    TAKES `plan_docs` MAPS, NOT `phase_docs` MAPS, and that is the whole of the
    fix rather than a refinement. Built on the phase reader it could only ever
    judge names that already began with `phase`, so it caught `Phase3.md` and
    `phase3-x.md` — the tidy near-misses — and was blind to `the_run_bag.md`,
    which is the standard's own first-named failure mode and the one a model
    reaches for when it forgets the convention entirely. The prompt states this
    run writes exactly TWO kinds of file; this is what makes that observed.

    JUDGES ONLY WHAT THIS RUN ADDED. A pre-existing non-conformant name is
    somebody else's legacy and renaming it is explicitly out of scope — the
    number is identity, and "fixing" one costs a cross-reference sweep to buy
    nothing. A guard that failed the run over a file it is forbidden to touch
    would make a conformant component unplannable.
    """
    return sorted(name for name in after
                  if name not in before
                  and name != ROADMAP
                  and not _PHASE_FILE.match(name))


def phase_identity(name: str) -> tuple[int, str] | None:
    """`phase12b_x.md` -> `(12, "b")`, `phase12_x.md` -> `(12, "")`. None if malformed.

    THE FULL IDENTITY, where `phase_number` gives only its first half. Both
    exist because the two comparisons below need different halves: a NEW phase
    against a PRE-EXISTING one collides on the bare number (rule 6 forbids
    injecting a sub-letter retroactively, so `phase5b_` arriving after
    `phase5a_` is an offence), while two files this run wrote TOGETHER collide
    only on the whole identity, since `phase5a_` + `phase5b_` planned in one
    pass is exactly the carve-out rule 6 permits.
    """
    m = _PHASE_FILE.match(name)
    return (int(m.group(1)), m.group(2)) if m else None


def reused_phase_numbers(before: dict[str, str],
                         after: dict[str, str]) -> list[tuple[str, int]]:
    """New phase docs whose identity was already taken. Returns `(filename, number)`.

    RULE 1 AND RULE 5 TOGETHER, AND RULE 5 IS THE ONE THAT BITES. A new phase
    takes `max(existing) + 1`; gaps are correct and are NOT free numbers, because
    *"external references in code comments, commit messages, and sprint docs may
    still point at them, and reusing the number creates silent ambiguity."*

    So the taken set is every number visible in `before`, gaps included by
    construction — a number absent from `before` cannot be a gap this run can
    see. What this cannot catch is a number retired before the component was
    committed; that is archaeology, and the roadmap's own tombstone entries are
    where a run reads it.

    TWO NEW FILES ARE ALSO CHECKED AGAINST EACH OTHER, and that half was missing:
    `taken` was built once from `before` and never grew, so `phase5_a.md` and
    `phase5_b.md` written in the SAME dispatch collided with nothing and both
    shipped — two documents permanently both called Phase 5, past the one guard
    that exists to make a number an identity. Reproduced by execution before this
    was closed. The comparison among new files is by full identity rather than by
    bare number, because `phase5a_poc.md` + `phase5b_rollout.md` in one pass is
    rule 6's carve-out and must stay legal; a bare number mixed with a lettered
    one is not, since the phase cannot be both chunked and not.

    A malformed new name yields no identity and is reported by
    `malformed_phase_docs` instead; reporting it twice would make one mistake
    look like two.
    """
    taken = {n for n in (phase_number(name) for name in before) if n is not None}
    written: dict[int, set[str]] = {}
    out: list[tuple[str, int]] = []
    for name in sorted(after):
        if name in before:
            continue
        ident = phase_identity(name)
        if ident is None:
            continue
        num, letter = ident
        letters = written.setdefault(num, set())
        # A bare number and a lettered one are the same phase claiming two
        # shapes, so `letters and ("" in letters or letter == "")` is a
        # collision exactly as an exact repeat is.
        if (num in taken
                or letter in letters
                or (letters and ("" in letters or letter == ""))):
            out.append((name, num))
        letters.add(letter)
    return out


def hour_hits(component: Path) -> Counter:
    """`(filename, matched text)` -> count, over the same set `hour_estimates` scans.

    THE SNAPSHOT HALF, so the prohibition can be judged as a DELTA like every
    other one in this workflow. `hour_estimates` answers *what estimates are in
    this plan*; the guard's question is *what estimates did THIS RUN write*, and
    those are different whenever the component already carried one. They already
    do: `/opt/skyy-net/skyynet-master-planning/development/common/reviews` holds `~7h` and `~12.8 hours` today, and
    `plan-revision` — the unsplit planner this workflow is the write half of a
    replacement for — sizes work, so any component it planned carries estimates
    a `plan-draft` extending it never wrote.

    Scanning post-run STATE made those a permanent failure with a message
    asserting *"plan-draft wrote N hour estimate(s)"*, which was false, and
    left the component unplannable until a human edited text this workflow is
    not otherwise in the business of touching.

    KEYED ON (FILE, TEXT) AND NOT ON THE CITATION, because a citation carries a
    line number and inserting a phase above an untouched estimate would move it
    — reporting a line shift as a new estimate. The same reason `plan_boxes`
    counts box TEXT rather than box position.
    """
    hits: Counter = Counter()
    for name in plan_docs(component):
        text = (component / name).read_text(errors="replace")
        for line in text.splitlines():
            for m in _HOURS.finditer(line):
                hits[(name, m.group(0).strip())] += 1
    return hits


def hour_estimates(component: Path, tree: Path,
                   only: Counter | None = None) -> list[str]:
    """`relpath:line: matched text` for every hour estimate in the component's plan.

    `only` RESTRICTS THE CITATIONS to a set of `(filename, matched text)` pairs —
    the delta `hour_hits` produces — so the operator is shown the estimates this
    run is answerable for and not the ones it inherited. `None` means every hit,
    which is what a standalone audit of a component wants.

    SIZING IS `plan-refine`'S, AND THAT IS A DESIGN DECISION RATHER THAN A
    DIVISION OF LABOUR. An author sizing their own decomposition is defending it;
    a fresh reader sizing it is a second opinion. It is the same `author != judge`
    rule the research and build families split on, applied to a number.

    SCOPED BY `plan_docs`, i.e. by the write grant — every markdown file sitting
    directly in the component. Naming the scope matters twice over: `research/`
    is outside it, because a synthesis legitimately reporting a measured
    wall-clock in hours is evidence rather than an estimate and is not this
    guard's business; and NOTHING inside it is outside, because a scope narrower
    than the grant leaves the run a file it may write and nothing reads.

    Returns citations rather than a boolean because the operator's next question
    is always *where*, and a guard that answers "somewhere in the plan" sends
    them to grep for it.
    """
    found: list[str] = []
    for name in plan_docs(component):
        path = component / name
        rel = path.relative_to(tree)
        for lineno, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            for m in _HOURS.finditer(line):
                text = m.group(0).strip()
                if only is not None and (name, text) not in only:
                    continue
                found.append(f"{rel}:{lineno}: {text}")
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
    taken = sorted(taken_phase_numbers(component))

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

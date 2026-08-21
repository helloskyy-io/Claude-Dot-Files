"""plan-verify's own I/O — one consumer each, so §10.1 rule 3 puts them here.

[`workflow-scripts.md` § Location](../../../../../../../docs/standards/workflow-scripts.md)
restates §10.1 rule 3 as BINDING and mechanical — *"consumer count decides, never
taste"* — and rule 6 gives a workflow folder its place to grow the helpers it has
earned. Everything below has exactly one consumer: `plan_verify_workflow`.

WHAT THIS MODULE IS FOR, AND WHY IT IS NOT `plan_feature_activities` REVERSED.
`plan-feature` is forbidden to size, and its readers are shaped for a
PROHIBITION: component-wide, keyed by file, judged as a delta, and answering
*what did this run write that it should not have*. `plan-verify` produces the
same shape as its DELIVERABLE, and a deliverable is judged on STATE — the
roadmap either carries an estimate per phase when the run finishes or it does
not. A `--pr` correction pass that leaves last pass's estimates untouched writes
no new hours and is entirely correct, so a delta-shaped deliverable guard would
fail exactly the pass most likely to be the last one anybody reads.

  * `roadmap_hours` answers *is this plan sized*, scoped to the ONE file this
    workflow may write, on post-run state.
  * `roadmap_phase_links` answers *is this still the same decomposition* — the
    only mechanism that can see a judge quietly re-planning the component
    through the one file it holds a grant on.
  * `plan_inventory` is the counted state block, so the prompt cannot assert a
    plan shape it invented.

The hour PATTERN itself is `plan_activities.HOUR_ESTIMATE` and is deliberately
shared with `plan-feature`. Two copies would let the write half forbid a shape
the read half does not produce, or the read half satisfy itself with a shape the
write half would have rejected — and neither divergence shows up in a diff.

NOT IDEMPOTENT (§7.1) is not in play here — this module only reads.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .. import plan_activities as act

# The one file this workflow writes. Named rather than spelled inline because
# four readers below and the workflow's own grant all test for it.
ROADMAP = "roadmap.md"

# The phase-doc reader lives on the shared surface — two consumers, per §10.1
# rule 3. Aliased here so this module reads in one alphabet, and named
# `phase_docs_of` rather than `phase_docs` so the registry entry beside it cannot
# be misread as `plan-feature`'s: that workflow GUARDS phase docs, this one only
# counts them.
phase_docs_of = act.phase_docs

# A phase doc REFERENCED from the roadmap — a link target, a bare filename in a
# table cell, or an inline code span. Deliberately looser than
# `plan_feature_activities._PHASE_FILE`, which judges whether a name a run WROTE
# is legal: this one asks which phases the roadmap currently points at, and a
# non-conformant legacy name it points at is still a phase it points at.
#
# IT MATCHES A CROSS-COMPONENT LINK TOO, AND THAT IS DELIBERATE RATHER THAN
# TOLERATED. `docs/development/memory-management-framework/roadmap.md` links
# three of `persistent-memory-protocol`'s phase docs — measured, not supposed, by
# running this reader against the live file — so the reference set is genuinely
# wider than the component's own phases. For the GUARD that is the property
# wanted: a judge deleting a sibling cross-reference has removed a pointer
# somebody put there on purpose, and `boundary_crossings` cannot see it either.
# What it must not do is masquerade as a phase COUNT — `plan_inventory` says
# "reference(s)" and lists the component's own docs separately for that reason.
# THE DESCRIPTOR IS OPTIONAL, AND MAKING IT REQUIRED WAS A HOLE. This read
# `phase\d+[a-z]?_[a-z0-9_-]+\.md` — underscore-plus-descriptor mandatory — while
# its PAIRED reader `act._LOOKS_LIKE_A_PHASE` deliberately accepts a legacy
# `PHASE3.MD` and says so in its own comment. The pair is the whole mechanism:
# `phase_docs_of` sees the FILE and this sees the POINTER, and a link the roadmap
# drops while leaving the file on disk is visible to neither if only one of them
# recognises the name. So a judge could delete a legacy-named phase's roadmap
# entry — the exact re-planning offence this reader exists for — and return a
# green run. One reader claiming coverage the other does not reciprocate is the
# same class as a docstring claiming a behaviour the code does not have.
#
# THE DIGIT STAYS REQUIRED, and it is what keeps this off ordinary prose:
# `phases.md`, `phase.md` and `phase_notes.md` do not match, and neither does
# *"see Phase 3 of the memory doc"* — measured against both, not assumed.
_PHASE_REF = re.compile(r"\bphase\d+[a-z]?[a-z0-9_-]*\.md\b", re.I)


def roadmap_hours(component: Path) -> Counter:
    """Every hour estimate in the component's `roadmap.md`, counted by matched text.

    SCOPED TO ONE FILE ON PURPOSE, and the scope IS the design decision this
    workflow makes. A figure restated in two places with nothing deriving it is
    the class this repo keeps paying for — `candidates.md` C-523klr8n names it, and
    `test_measurement_figures_are_cited.py` is the gate built after four
    consecutive passes each corrected a figure at its source and left a copy
    standing. So the estimates live in the roadmap and NOWHERE else, and the
    enforcement of *nowhere else* is not a second scanner: it is the write grant,
    which reaches `roadmap.md` and no other file in the component.

    THE ROADMAP AND NOT THE PHASE DOCS, and the deciding argument is coverage
    rather than taste. `plan-feature`'s own prompt is explicit that **a phase
    gated on something outside the component gets a roadmap entry and NO phase
    doc yet** — so a phase-doc-only sizing structurally cannot size a gated
    phase, which is exactly the phase whose cost an operator most needs before
    deciding whether to unblock it. The roadmap is also the file a PM opens
    first and the only one where every phase is visible together, which is what
    a total is taken over.

    COUNTED BY TEXT, not by line, so inserting a paragraph above an estimate does
    not read as a new estimate — the same reason `checked_boxes` counts box text.
    A Counter rather than a set so two phases legitimately estimated `~8 hrs`
    count as two.

    A MISSING ROADMAP IS AN EMPTY COUNTER, NOT AN ERROR. The caller's deliverable
    guard is what turns that into a failure, with a message about the plan rather
    than a `FileNotFoundError` about a path.
    """
    roadmap = component / ROADMAP
    if not roadmap.is_file():
        return Counter()
    return Counter(m.group(0).strip()
                   for m in act.HOUR_ESTIMATE.finditer(roadmap.read_text(errors="replace")))


def hour_citations(component: Path, tree: Path) -> list[str]:
    """`relpath:line: matched text` for every estimate in the roadmap.

    Returned rather than a count because the operator's next question about a
    sizing they disagree with is always *where*, and a guard that answers
    "somewhere in the roadmap" sends them to grep for it. Used by the deliverable
    guard's message, which has to show what WAS written to make "and this many
    phases were not" legible.
    """
    roadmap = component / ROADMAP
    if not roadmap.is_file():
        return []
    rel = roadmap.relative_to(tree)
    return [f"{rel}:{n}: {m.group(0).strip()}"
            for n, line in enumerate(roadmap.read_text(errors="replace").splitlines(), 1)
            for m in act.HOUR_ESTIMATE.finditer(line)]


def roadmap_phase_links(component: Path) -> Counter:
    """Every phase doc the roadmap references, counted by filename.

    THE MECHANISM THE REGISTRY DEMANDED AND NOTHING ELSE SUPPLIED. This workflow
    holds a write grant on `roadmap.md` and a prohibition on RE-PLANNING the
    component — merging two phases, dropping one, inventing another. Every other
    prohibition here is a path the boundary check already sees; this one happens
    entirely inside the single file the grant opens, so `boundary_crossings` is
    blind to it by construction and a judge rewriting the decomposition it was
    sent to judge would return a PR URL and a green run.

    Writing the `MAY_NOT_OBSERVERS` row is what surfaced that: the honest answer
    to *what observes this?* was "nothing", and the row is not allowed to say so
    without a reason. This is the mechanism instead.

    WHAT IT CANNOT SEE, STATED SO THE ROW IS NOT READ AS COVERING MORE THAN IT
    DOES. A Counter has no order, so RE-ORDERING the roadmap's phase entries is
    invisible here — deliberately at the margin, since re-ordering within the
    roadmap is a legitimate act for `plan-feature` and the prohibition this
    workflow carries is about *deciding when the component gets built*, whose
    artifact is `sprint.md` and IS observed. And a roadmap that links no phase
    doc at all yields an empty Counter on both sides, which passes vacuously;
    `plan_inventory` puts the link count in front of the model for that reason,
    and `sizing_floor` is what stops that same emptiness disabling the
    deliverable guard. **That sentence used to say the deliverable guard "fails a
    component with no phases", and it was FALSE** — the guard compared against
    `len(phase_docs)`, so on a component with none the comparison was `sum < 0`
    and the guard could not fire at all. A docstring asserting what a DIFFERENT
    object does is the one claim nothing in this tree checks; this one was one
    read from being believed. Corrected here, and the behaviour it names is now
    real rather than the claim being deleted.
    """
    roadmap = component / ROADMAP
    if not roadmap.is_file():
        return Counter()
    return Counter(m.group(0).lower()
                   for m in _PHASE_REF.finditer(roadmap.read_text(errors="replace")))


def sizing_floor(component: Path, docs: dict[str, str]) -> int:
    """The MINIMUM number of hour estimates a correct run leaves in the roadmap.

    A SEPARATE FUNCTION BECAUSE THE FLOOR IS THE GUARD, and the guard was a
    NO-OP for the exact shape the design decision was made for. It read
    `sum(hours) < len(phase_docs)` inline, and `phase_docs` counts FILES ON DISK.
    A component whose phases are ALL GATED has a roadmap entry per phase and no
    doc for any of them — which is the whole reason the estimates live in
    `roadmap.md` and not in phase docs — so the count was 0, the comparison was
    `sum < 0`, and a run could write ZERO estimates, raise nothing, and print
    `SIZED` at the operator. The one output this workflow exists to produce was
    unenforced precisely where it matters most.

    THE CLASS, STATED SO THE NEXT FLOOR IS NOT WRITTEN THE SAME WAY: a threshold
    derived from a count that can legitimately be zero is a guard its own input
    can switch off. Narrowing a floor is safe — it cannot fail a correct run —
    right up to the point it reaches zero, at which it stops being narrow and
    starts being absent. The distinction is invisible in the arithmetic.

    THE FLOOR IS ONE WHEN THERE IS A PLAN AND NO DOCS, and one is chosen rather
    than the true phase count because the true count is not derivable:

      * `roadmap_phase_links` cannot supply it — a GATED phase has no doc, so
        there is no `phaseN_*.md` for the roadmap to link, and it counts
        CROSS-COMPONENT links besides.
      * Counting roadmap HEADINGS needs a heading grammar the Documentation
        Standard does not fix, and would fail correct runs written to a spelling
        it did not anticipate.

    So this closes the TOTAL collapse (a run that sized nothing) and not the
    PARTIAL one (an all-gated component with six phases still passes on one
    estimate). That residual is real, is narrower than what it replaces, and is
    pinned by a test rather than assumed. The sufficient check remains the
    reviewer reading the report, which the guard's message says outright.

    NO ROADMAP MEANS NO FLOOR, and that is not a loophole: `plan_inventory` tells
    a run that finds no roadmap to size nothing and stop, `run_plan_verify`
    refuses to launch without one, and a floor here would fail that correct run
    at the last guard for obeying its instructions.
    """
    if not (component / ROADMAP).is_file():
        return 0
    return max(len(docs), 1)


def plan_inventory(component: Path, tree: Path) -> str:
    """What this run is reading, counted in code and handed over.

    COUNTED HERE SO THE PROMPT CANNOT ASSERT A STATE IT INVENTED — the discipline
    `candidate_counts` states for the triage working set and `planning_state` for
    the write half. The number that matters most is the PHASE COUNT, because it
    is simultaneously this run's workload, the floor its deliverable guard
    enforces, and the thing a run skimming a roadmap will undercount.

    THE COLD-READ INSTRUCTION IS PART OF THE BLOCK RATHER THAN STATIC PROMPT
    TEXT, because it has to name the actual files. A judge told "read the plan"
    reads the roadmap and stops; a judge handed the phase-doc list by name has no
    such exit, and the phase docs are where the decomposition it is judging
    actually lives.
    """
    rel = component.relative_to(tree)
    docs = sorted(phase_docs_of(component))
    roadmap = component / ROADMAP
    syn = component / "research" / "synthesis.md"

    if not roadmap.is_file():
        return (
            f"**Counted in code, authoritative — do not recount:** `{rel}/` has "
            f"**no `roadmap.md`**, and {len(docs)} phase doc(s).\n\n"
            f"**THERE IS NO PLAN HERE TO VERIFY.** Do not write one — that is "
            f"`plan-feature`'s and you hold no grant over a phase doc. Say so "
            f"plainly in your report, size nothing, and stop."
        )

    refs = len(roadmap_phase_links(component))
    listed = "\n".join(f"  - `{rel}/{n}`" for n in docs) or "  *(none)*"
    # THE TWO NUMBERS ARE NOT THE SAME NUMBER, and saying so is the whole reason
    # this sentence is shaped this way. A roadmap legitimately links a SIBLING
    # component's phase docs — the memory-management-framework roadmap links
    # three of persistent-memory-protocol's — so the reference count runs ahead
    # of the phase count on a perfectly correct plan. Handing a model "9 phase
    # docs referenced" over a directory holding 6, under a label reading
    # *authoritative, do not recount*, is a false statement in the one block
    # whose whole job is to stop the run inventing a state.
    return (
        f"**Counted in code, authoritative — do not recount:** `{rel}/` has a "
        f"`roadmap.md` and **{len(docs)} phase doc(s) of its own**. Its roadmap "
        f"carries **{refs} distinct phase-doc reference(s)**"
        + (", which is MORE than it has docs — a roadmap may link a SIBLING "
           "component's phases, and those are cross-references rather than "
           "phases of this component. **Size the docs listed below, not the "
           "references.**" if refs > len(docs) else ".")
        + f"\n\n**READ EVERY ONE OF THESE, COLD.** You did not write them.\n\n"
        f"  - `{rel}/{ROADMAP}`\n{listed}\n\n"
        + (f"Its evidence pool rolls up to `{syn.relative_to(tree)}` — read it to "
           f"answer question 4, and only for that.\n"
           if syn.is_file() else
           "**Its evidence pool has NO `synthesis.md`.** Question 4 — *does the "
           "cited evidence support the phase* — then has no rolled-up answer, and "
           "that is itself a finding to report rather than a reason to skip it.\n")
        + f"\n**A roadmap entry with no phase doc is a GATED phase, not a missing "
        f"one, and it still gets an estimate.** It is the phase whose cost the "
        f"operator most needs before deciding whether to unblock it."
    )

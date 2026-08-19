# Blind inter-rater trial — fork-vs-parameterize

**Sealed 2026-08-19, before any commit history was consulted.** This file exists because
[Phase 2](phase2_family_alignment.md) requirement 3 forbids trusting the ruling procedure until it
has been validated, and *"an unvalidated procedure applied to 13 rows produces 13 confident
guesses."* The requirement is explicitly allowed to fail. **It did fail**, and §4 records how.

The procedure under test is
[`fork_vs_parameterize.py`](../../../scripts/workflows/temporal/tests/unit/fork_vs_parameterize.py) —
four signals in order, four short-circuits applied first, and absence-of-signal yielding *unruled*
rather than *deliberate*. The benchmark is [R3]'s **κ = 0.271** as reported in
[`fork_vs_parameterize_drift_signal.md`](research/raw/fork_vs_parameterize_drift_signal.md) §3.1,
which the paper names as *the ceiling* on any rule built from the same signals.

---

## 1. Method

**Sample.** The five same-named prompt-file groups that have drifted, expanded to the seven file
PAIRS they contain (`new_branch.md` and `update_pr.md` each have three copies). The research paper's
§7.1 asks for *"each of the five drifted groups"*; a group of three copies is not one comparison,
so the unit here is the pair. Two byte-identical groups the paper measured at its own commit —
`from_plan.md` and `stages_1_to_4_from_plan.md` — are absent from this sample because they have
since been promoted, which is short-circuit SC1 arriving by mechanism rather than by ruling.

| Pair | Left | Right |
|---|---|---|
| P1 | `research_refresh/prompts/altitude_component_tail.md` | `research_write/prompts/altitude_component_tail.md` |
| P2 | `build_draft/prompts/new_branch.md` | `build_draft_minor/prompts/new_branch.md` |
| P3 | `build_draft/prompts/new_branch.md` | `plan_revision/prompts/new_branch.md` |
| P4 | `build_refine/prompts/refine.md` | `build_refine_minor/prompts/refine.md` |
| P5 | `build_refine/prompts/stages_2_to_4.md` | `build_refine_minor/prompts/stages_2_to_4.md` |
| P6 | `build_draft/prompts/update_pr.md` | `build_draft_minor/prompts/update_pr.md` |
| P7 | `build_draft/prompts/update_pr.md` | `plan_revision/prompts/update_pr.md` |

**Raters.** Two agents holding `Read`, `Grep` and `Glob` and **no shell** — so `git log` was not
merely forbidden, it was unreachable. Rater A was dispatched as `code-reviewer`, rater B as
`quality-control`. Using two different agent definitions rather than the same one twice is
deliberate: identical raters measure prompt determinism, and the trial is about whether the
PROCEDURE reproduces across judges who bring different priors, which is what [R3]'s three human
judges were.

**Blinding.** Both raters received a byte-identical instruction naming the four signals, the four
short-circuits, the asymmetry of signal 4, the *absence yields UNRULED* rule, and the prohibition on
similarity magnitude. Both were told not to read `scripts/workflows/temporal/tests/` or
`docs/development/workflow-decomposition/`, which hold prior rulings.

**Sealing.** Their verbatim outputs are §2 and §3 below, written and committed before the operator
of this run ran any history command against a prompt file.

---

## 2. Rater A — verbatim, sealed

```
P1  VERDICT: DELIBERATE   DECIDED BY: SC3
    WHY: research_refresh and research_write are stated to be different jobs — refresh revalidates an
    existing pool via a mechanical date-gate and a diff-agent, write creates and sizes a new pool via a
    rubric (research_refresh_workflow.py docstring). The tail content each carries (revalidate-don't-grow
    vs. sizing-band guidance) is exactly what each child's own job requires, not a stale copy of the other.

P2  VERDICT: DELIBERATE   DECIDED BY: S4
    WHY: build_draft_minor_workflow.py's own docstring states the rationale: "Its prompts are
    self-contained — unlike the major tier they pull in neither RULES nor the headless guard, which is why
    they are larger." That explains exactly the shape of the difference between the two new_branch.md files
    (templated/placeholder-driven vs. fully inlined stages).

P3  VERDICT: DELIBERATE   DECIDED BY: SC3
    WHY: build_draft and plan_revision are different families doing different jobs (code change vs.
    planning-doc revision), each prompt says so of itself ("SIGNIFICANT rework" vs. "PLANNING doc build
    workflow — not a code change workflow"), and plan_revision_workflow.py documents a deliberate, separate
    RULES file ("different text — reaching for the shared one would silently hand a planning run the
    code-change ruleset").

P4  VERDICT: DELIBERATE   DECIDED BY: S3
    WHY: The only differences are a tier-describing sentence ("SIGNIFICANT rework" vs. "MINOR tier: a scoped
    correction, reviewed by one lens") and the commit-message prefix ("build-refine:" vs
    "build-refine-minor:") — parameterization of named entities, not missing blocks, consistent with this
    family's established major/minor pattern.

P5  VERDICT: DELIBERATE   DECIDED BY: S4
    WHY: The minor copy states its own rationale in-line for dispatching one review agent instead of two
    ("This is the minor tier... the structural, standards and holistic lenses that build-refine runs are
    sized for multi-file architectural work and would spend most of this run's budget confirming there is
    nothing to say") and even names the routing signal for when that assumption breaks.

P6  VERDICT: DELIBERATE   DECIDED BY: S4
    WHY: Same self-contained-vs-templated split as P2, governed by the same stated docstring rationale in
    build_draft_minor_workflow.py — the minor tier's prompts intentionally inline everything the major tier
    pulls in via shared placeholders.

P7  VERDICT: DELIBERATE   DECIDED BY: SC3
    WHY: Same cross-family divergence as P3 — build_draft's update_pr.md carries a code-change
    self-description/file_structure.txt bullet appropriate to its job, while plan_revision's carries a
    planning-review summary format (architect/planner/security-auditor/standards-architect/quality-control)
    appropriate to its own reviewer set; each fits its own referent.

CONFIDENCE NOTE: P5 was the hardest to be fully certain of — the minor copy also drops several
fidelity-guidance paragraphs (mutation-testing sub-techniques) that the major copy has, and without the
explicit "this is the minor tier" framing sitting right next to it, that specific omission alone could have
read as NEGLECTED rather than a deliberately lighter fidelity bar.
```

---

## 3. Rater B — verbatim, sealed

```
P1  VERDICT: DELIBERATE   DECIDED BY: S4
    WHY: research_refresh/prompts/altitude_component_tail.md states its own rationale in-text — "You are
    refreshing, not sizing... you do not grow the pool with new topics" — directly explaining why it omits
    research_write's sizing-band content. That stated rationale is sufficient on its own to call this
    deliberate.

P2  VERDICT: NEGLECTED    DECIDED BY: S1
    WHY: build_draft_minor/prompts/new_branch.md opens "You are executing the BUILD workflow" (not
    BUILD-DRAFT-MINOR), names artifacts its own child does not have (build-minor.sh, build.sh — bash-fleet
    script names, while this child is build_draft_minor_workflow.py in the Python/temporal system), and uses
    commit prefix "build:" instead of a prefix matching its own WORKFLOW_KEY = "build-draft-minor".
    build_draft/new_branch.md, by contrast, correctly self-identifies as BUILD-DRAFT and uses "build-draft:".
    The workflow's own docstring explains why the structure is self-contained (no shared RULES/guard), but
    not why the content still names artifacts this child does not possess — that residue reads as
    unreconciled leftover text rather than intentional wording.

P3  VERDICT: DELIBERATE   DECIDED BY: SC3
    WHY: plan_revision's workflow module states its job is planning-doc revision (roadmaps, requirements,
    ADRs, epics) — genuinely different work from build_draft's code-change job. Each copy correctly fits its
    own referent: plan_revision/new_branch.md says "PLANNING doc build workflow — not a code change
    workflow," 6 stages, commit prefix "docs:"; build_draft/new_branch.md says 8 stages and "build-draft:".
    Both are internally consistent with their own child.

P4  VERDICT: DELIBERATE   DECIDED BY: S3
    WHY: The only differences between build_refine/refine.md and build_refine_minor/refine.md are the
    tier-description sentence (line 3) and the commit prefix ("build-refine:" vs "build-refine-minor:"), and
    both correctly match each file's own module identity (WORKFLOW_KEYs "build-refine" and
    "build-refine-minor" respectively, per each workflow module). This is drift confined to named
    parameters, not missing blocks.

P5  VERDICT: DELIBERATE   DECIDED BY: S4
    WHY: build_refine_minor/stages_2_to_4.md states explicitly, in its own text, why it dispatches only one
    review agent instead of the two-plus-cross-read arrangement in build_refine's copy: "This is the minor
    tier... the structural, standards and holistic lenses that build-refine runs are sized for multi-file
    architectural work and would spend most of this run's budget confirming there is nothing to say." That
    is a rationale stated in the artifact itself.

P6  VERDICT: NEGLECTED    DECIDED BY: S1
    WHY: Same defect class as P2, in the update-PR wrapper: build_draft_minor/prompts/update_pr.md opens
    "You are executing the BUILD workflow on PR #..." (not BUILD-DRAFT-MINOR), references
    build-minor.sh/build.sh, and commits as "build:" rather than a prefix tied to its own WORKFLOW_KEY =
    "build-draft-minor", while build_draft/update_pr.md correctly self-identifies as BUILD-DRAFT and uses
    "build-draft:". The content does not fit its own child's identity.

P7  VERDICT: DELIBERATE   DECIDED BY: SC3
    WHY: Same as P3: plan_revision/update_pr.md is doing a genuinely different job (planning-doc revision, 6
    stages, "docs:" commit prefix, reviewer set of
    architect/planner/security-auditor/standards-architect/quality-control) from build_draft/update_pr.md
    (code-change workflow, 8 stages, "build-draft:" prefix). Each fits its own referent.

CONFIDENCE NOTE: P2 and P6 were the hardest — the workflow docstring gives a real architectural reason for
the minor tier's prompts being self-contained (structural difference), which could be mistaken for covering
the specific stale bash-script references and mismatched commit prefix too; I treated those two as a
separate, unexplained residue rather than folding them into the docstring's rationale.
```

---

## 4. Scoring — TO BE COMPLETED AFTER THE REVEAL

Sections 5 onward are written after the commit history is revealed. Everything above this line was
committed first; the commit that contains §1–§3 and nothing below is the seal.

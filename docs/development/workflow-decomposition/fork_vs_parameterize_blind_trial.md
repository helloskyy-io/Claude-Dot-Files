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

## 4. The reveal — ground truth, by a mechanical audit

The seal is commit `beb103f`, whose message is *"SEAL blind-trial classifications before any history
is consulted"* and whose diff is §1–§3 and nothing else. No `git log` was run against a prompt file
before it.

**Ground truth is a CO-EVOLUTION AUDIT, and the criterion was fixed before it was run** so the
reveal could not become a search for the answer already wanted. For each pair, `git log --follow`
both sides and partition the commits into those touching BOTH copies and those touching only one:

- **DELIBERATE** — no *substantive* commit is one-sided. Renames, directory moves and the original
  ports do not count: they change where a file is, not what it says.
- **NEGLECTED** — substantive prompt-content commits landed on one side and not the other, and the
  counterpart file existed at the time.

**This repo has an advantage the literature does not, and §7.2 of the paper says so: the history
exists even though the ruling method may not consult it.** Kapser & Godfrey could not run this
check. It is the difference between measuring AGREEMENT and measuring ACCURACY.

| Pair | both | left-only | right-only | Ground truth |
|---|---|---|---|---|
| P1 | 1 | 0 | 0 | **DELIBERATE** — both files were CREATED by one commit, `168dc8a`, which split a shared head into the pool and left each child its own tail. The difference is the split, by construction. |
| P2 | 1 | 3 | 3 | **DELIBERATE** — every one-sided commit is a rename, a directory move or the original port. The only substantive commit, `41a0589`, changed the SAME line in both copies. |
| P3 | 0 | 4 | 1 | **DELIBERATE** — cross-family. Each side evolves inside its own family and neither has ever been a copy the other was maintained against. |
| P4 | 5 | 1 | 1 | **DELIBERATE** — five shared commits; the left-only one (`38cb5a4`) was later reconciled by the promotion in `168dc8a`, and what remains is the tier description and the commit prefix. |
| **P5** | 10 | **11** | 0 | **NEGLECTED** — eleven substantive prompt-improvement commits landed in `build_refine` and in `build_refine_minor` never. Named, because a count alone would be a claim: `4c07f24`, `f41afc7`, `92d661a`, `cf1776e`, `5c03389`, `bd16b09`, `f912b41`, `38cb5a4`, `e1c270d`, `14334f1`, `2d24414`. |
| P6 | 0 | 3 | 6 | **DELIBERATE, and the PAIR IS MIS-FORMED** — the right side's three substantive commits (`44706eb`, `8be3600`, `41a0589`) each touched `build_draft/prompts/stages_1_to_4.md` in the same commit. The major tier's counterpart to the minor tier's self-contained wrapper is the wrapper PLUS the stages body, so same-filename selected a comparison that is not the real one. |
| P7 | 0 | 3 | 1 | **DELIBERATE** — cross-family, as P3. |

**The eleven of P5 is the same shape and the same number as the failure this whole component was
opened for** — *"the normal one accumulated eleven testing rules and the plan variant received none
of them"*. That is a coincidence in the number and not in the mechanism.

---

## 5. Scoring

### 5.1 Agreement between the raters — kappa = 0.000

Raters agreed on five of seven (P1, P3, P4, P5, P7) and disagreed on P2 and P6.

```
observed agreement   Po = 5/7                    = 0.714
rater A marginals    DELIBERATE 7, NEGLECTED 0
rater B marginals    DELIBERATE 5, NEGLECTED 2
chance agreement     Pe = (7*5 + 0*2) / 7^2      = 0.714
Cohen's kappa        (Po - Pe) / (1 - Pe) = 0.000 / 0.286 = 0.000
```

**kappa = 0.000, against the field's benchmark of 0.271.** Requirement 3's rule — *"if agreement is
at or below the field's kappa = 0.271 benchmark, ruling moves from per-pair to per-family"* — is
triggered.

### 5.2 Accuracy against ground truth, which points the OTHER WAY

| | P1 | P2 | P3 | P4 | P5 | P6 | P7 | correct |
|---|---|---|---|---|---|---|---|---|
| ground truth | D | D | D | D | **N** | D | D | — |
| rater A | D | D | D | D | D | D | D | **6 / 7** |
| rater B | D | **N** | D | D | D | **N** | D | **4 / 7** |

**REPORTING kappa ALONE WOULD HAVE BEEN MISLEADING AND THE DIRECTION MATTERS.** kappa is degenerate
here: rater A used one category for all seven, so chance agreement equals observed agreement and
kappa is zero no matter how many it got right. A run that reported only "kappa = 0.000, procedure
retired" would have thrown away the fact that one rater was right six times out of seven.

### 5.3 And rater A's accuracy is worth nothing, which is the actual finding

Rater A returned **DELIBERATE on every pair** and never once returned NEGLECTED or UNRULED. Both
raters were told, in identical words, that the field's default-to-intentional convention is NOT
imported here and that a genuinely absent signal yields *unruled*. One of them applied the forbidden
default anyway.

It scored 6/7 **because the population is 6/7 deliberate** — a constant classifier scores exactly
that on this sample without reading anything. And it was wrong on **P5**, the one pair where the
default is wrong, which is the one pair that is the defect class this entire component exists to
catch. **A procedure whose accuracy comes from a default has zero value on the only case that
matters**, and the paper's §6.3 predicted precisely this: *the field's conservative default is safe
for them and unsafe for us*.

### 5.4 Two structural findings the trial produced that were not the question

- **Signal 4 fires early and then generalizes past its own scope.** Both raters ruled P5
  DELIBERATE on S4, citing the minor tier's in-text explanation of why it runs one review lens.
  That rationale is TRUE and explains ONE difference. Eleven other differences in the same pair have
  nothing to do with lens count. A stated rationale short-circuits the procedure, and neither rater
  asked whether it covered everything it was being used to excuse.
- **A file pair is not a ruling unit.** P6's two files are not counterparts at all — the major
  tier's counterpart is a wrapper plus a separate stages body — and the same-name heuristic that
  chose the sample could not see that. Rater A worked it out from the workflow module's docstring;
  rater B did not.

---

## 6. The ruling

**Per-pair ruling is not reproducible on this corpus, and the granularity moves to per-family.**
Recorded here rather than argued later:

1. **kappa = 0.000 is at or below 0.271**, which is the trigger requirement 3 named in advance.
2. **The disagreements were not about confidence, they were about which failure was in view.** On
   P2 and P6 one rater ruled on the pair's structure and the other on stale referents inside it.
   Both readings were defensible and they are not two estimates of one quantity.
3. **The one accurate rater was accurate by a forbidden default**, so its accuracy does not transfer
   to a population with a different deliberate/neglected mix — and the mix is exactly what nobody
   knows in advance.

**What per-family means in practice.** A ruling is made once for a CATEGORY OF GUIDANCE — using the
`_minor` tier contract in
[`fork_vs_parameterize.py`](../../../scripts/workflows/temporal/tests/unit/fork_vs_parameterize.py)
— and then applied to every pair carrying that category. The rulings that emptied the frozen
duplication baseline are `FAMILY_RULINGS` in that same module, beside the contract each one is
required to cite, one per category and not one per pair. The baseline they emptied is `ACCEPTED` in
[`test_prompt_blocks_are_shared_not_copied.py`](../../../scripts/workflows/temporal/tests/unit/test_prompt_blocks_are_shared_not_copied.py),
which is where the rulings were written and no longer where they live. **Requirement 2 is satisfied at that granularity, which is
what requirement 3 was written to permit.**

**A per-pair verdict is now advisory and is written down as such.** The procedure is not retired —
it is what a reviewer applies when a guard surfaces a pair, and §5.4's two findings make it better
than it was. It is no longer treated as reproducible enough that two reviewers would reach the same
answer.

### 6.1 What this trial does NOT establish

- **Seven pairs is a small sample and kappa is unstable on it.** One flipped call moves kappa
  substantially. The finding that survives that instability is §5.3 — a rater that never uses two
  of three categories — which is a property of the rater, not of the sample size.
- **Two raters were LLM agents, not humans.** They were given no shell so history was unreachable,
  which is a stronger blind than the literature's, and they hold different system prompts, which is
  the diversity the trial needed. They are not the three human judges of [R3] and this does not
  claim they are.
- **Ground truth is itself a judgement, made mechanical.** The co-evolution criterion is stated
  above and applied identically to all seven, but "substantive" versus "a rename" is a reading. It
  is a better-founded reading than the raters had, because it can see what happened.
- **It says nothing about pairs outside the sample.** The four block-level pairs frozen in
  `test_tier_siblings_do_not_DRIFT_by_a_sentence` were not rated.

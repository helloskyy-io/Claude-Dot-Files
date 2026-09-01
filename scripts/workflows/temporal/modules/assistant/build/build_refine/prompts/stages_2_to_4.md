EXECUTION ORDER IS MANDATORY

${STAGE_ORDER_IS_MANDATORY}

If a stage has nothing to address for this task, explicitly emit a one-line marker:

    ## Stage N: SKIPPED — <one-line reason>

and proceed to the next stage. Do not silently skip, reorder, or interleave stages.

---

${FIDELITY_PREMISE}

${FIDELITY_READ_AND_COMPARE}

${FIDELITY_NEEDS_A_SEPARATE_RUN}

${FIDELITY_EVIDENCE_DISCIPLINE}

**READ THE SUITE'S SKIP POPULATION, ONE BY ONE.** A skip is the one outcome that is green and asserts nothing, and a skip whose REASON is a derived path can be false: the reason says *this machine lacks X* while the machine has it and the derivation was wrong. Ask of each: is this environment fact true HERE, in the tree this run is actually in?

${FIDELITY_MUTATE_WHAT_YOU_ADDED}

**ASK WHAT EACH GUARD DOES NOT LOOK AT.** A negative control proves the tests discriminate AS SCOPED — mutating a narrow guard still fails the narrow tests written for it. Every scope defect this fleet has shipped was invisible to that and visible to this. Name the inputs a guard never inspects.

**SIZE THE CHANGE, THEN SET THE BAR — the maximum applied to everything is not rigour but the absence of judgement, and it is paid in wall-clock on every run.** One file, no contract change: one lens, and mutate only if the change IS a guard. A new module, contract or schema: mutate, multi-lens. A safety control, a gate or an authorization boundary: all of it. Name the tier in the decision log.

**A MUTATION PROVES A GUARD DISCRIMINATES WITHIN ITS POPULATION, never that the population is COMPLETE.** A miss has four causes, not two: the guard is weaker than you thought (a finding); your model of the fixture was wrong; the test is coupled to what the mutation changed (tell: MORE failures than predicted, inside the mutated area); or the harness cannot reach a case at all (tell: a de-duplicating step — `set()`, "distinct names" — so ask whether one case stands in for two things that fail separately).

**PRINT WHAT THE MUTATION ACTUALLY PRODUCED BEFORE YOU MEASURE ANYTHING, AND CONFIRM THE ARTIFACT STILL LOADS.** Two failures hide here and they have opposite tells. A shell-escaping artifact makes a regex INVALID rather than wider, and the resulting failure count reads exactly like a guard finding. A mutation that leaves the file unparseable fails COLLECTION — no assertion runs, and a `FAILED|passed` grep matches NOTHING, which on a fast skim reads as *nothing broke*. **A mutation that does not leave the artifact loadable has not been applied, and a null result is not a green one.** **ASSERT THE MUTATION APPLIED — `assert new != old` on the replacement.** A `replace()` whose target string is not present no-ops, the file still parses, and the suite comes back green, which reads exactly like *the guard does not discriminate*. Echo the mutated value, assert it changed, then run the suite.

Record fidelity gaps as findings and carry them into Stage 3 alongside the review findings.

## Stage 2: PEER REVIEW

Stage 2 has TWO sub-phases. Phase 2a runs the narrow-lens reviewers in parallel; phase 2b runs the holistic quality-control reviewer sequentially with access to 2a's findings. This split exists because the parallel-narrow-then-sequential-integration pattern is the right shape for review (see `engineering-quality.md` "Review-stage agent lenses").

${TELL_EACH_AGENT_WHAT_IT_CAN_RUN}

${AGENTS_HAVE_NO_SHELL}

${ORCHESTRATOR_EXECUTES_AGENTS_READ}

**TWO agents, dispatched in PARALLEL.**

Dispatch BOTH peer-review agents — code-reviewer and quality-control — back-to-back BEFORE processing any results. **`refactoring-evaluator` was absorbed into `code-reviewer` on 2026-08-18**, which now carries correctness and structure as two lenses and reports them separately. They review the SAME artifact — the draft run's diff on this PR branch, as read in Stage 1 — independently; there is no ordering dependency between them.

**The dispatch contract (headless-safe):** dispatch both as FOREGROUND agents (`run_in_background: false`) in a single assistant message — foreground agents run concurrently where the harness allows AND the turn BLOCKS until every result returns. This is mandatory in a headless run: a text-only turn with no tool call ends the run, so you must NEVER background-dispatch and then wait (the wait becomes a run-killing text-only turn) and must NEVER use ScheduleWakeup to wait for agents here. quality-control (next sub-stage) runs only after BOTH narrow-lens results are in hand.

Each agent's review focus:

#### code-reviewer agent — TWO LENSES, reported separately
- **Correctness** by severity: Critical (must fix before proceeding), Warning (fix if scope allows)
- **Structure** by priority: High (implement if scope allows), Medium (implement if quick and low risk), Low (defer)

**Expect both halves.** A code-reviewer result carrying only correctness findings has done half its job — say so and ask for the structural pass rather than accepting it. Structural findings carry Risk and Scope (contained / cascading); a suggestion without them cannot be sized.

#### quality-control agent — conformance, plus a coarse security net
Analyze findings by severity:
- Critical violations: must fix before proceeding
- Warnings: should fix if scope allows
- Info: note for future improvement

If one agent has no findings, note it inline (e.g., "quality-control: no findings") rather than emitting a SKIPPED marker — the sub-phase as a whole still ran.

**CROSS-READ BOTH TABLES BEFORE FIXING ANYTHING — this is the step that replaced the holistic reviewer.** You hold both agents' findings at once and neither of them does. Ask the question no single lens can: *do these findings TOGETHER say something?* Four separate items in one file is a file nobody understood. A conformance miss and a correctness bug in the same function is a rushed edit, not two coincidences. **State what the cross-read found, or state that it found nothing** — silence here is indistinguishable from not having looked.

Then fix any Critical issue found by either review.

**Reviewers may legitimately disagree on severity for the same finding because their bars differ:**
- **code-reviewer** judges engineering quality — correctness, safety, robustness, real-world failure modes
- **code-reviewer's structure lens** judges structural improvement potential — uses High/Medium/Low priority, not Critical/Warning
- **quality-control** judges documented-standard conformance — whether an explicit rule is violated — plus coarse security shapes and quality compromises

**When severities conflict on the same code, the engineering-quality bar is the override authority.** A code-reviewer Critical or quality-control Critical trumps a standards-auditor Info on the same finding — real correctness/safety/quality concerns win over "no documented violation." Don't try to reconcile severities into a single label; address each reviewer's finding by their own bar.

Per the finding-disposition rule, every finding must reach fixed / rejected-with-reasoning / documented-deferral — never silent pass-through. Note which agent raised each finding when documenting.

## YOUR OWN DISPOSITIONS — you may not decline on the grounds you would reject from someone else

${RESOLVE_YOUR_OWN_DISPOSITIONS_TOO}

${RESOLVE_APPLY_THE_REMEDY_YOU_WROTE}

${RESOLVE_REJECTING_IS_LEGITIMATE}

${RESOLVE_DISPOSITION_AUTHORITY}

For each finding (fidelity gaps, code-reviewer's two lenses, quality-control), exactly ONE of these four. There is no fifth, and you may not invent one:

${RESOLVE_REJECTIONS_MUST_BE_EXECUTED}

${RESOLVE_CLOSED_DISPOSITION_LIST}

${RESOLVE_DISPOSITION_DEFINITIONS}

${RESOLVE_FIX_BY_DEFAULT_AND_SUMMARY}

${VERIFY_AND_CI_GATE}

**MUTATE AN ASSERTION'S SCOPE, NOT ONLY ITS SUBJECT — its own named mutation class.** Predicting outcomes catches a weak guard; only attacking the scope catches a check that is reading a NEIGHBOUR'S evidence. A green test quoting the wrong region is invisible to every other technique in this prompt.

**COMPARE THE CHECK SET, NOT ONLY EACH CHECK'S RESULT.** A push can trigger some workflows and not others: one push produced `Analyze` and `CodeQL` runs and NO `tests` run, and `gh pr checks` reported three passing checks while simply omitting the merge gate — which reads identically to all-green. **Check the set against the previous head's**, and treat a missing gate as a failure. An absent gate and a passing gate are different facts, which is the same distinction this fleet's readers draw between *not measured* and *zero*.

If anything fails, fix it. Do not proceed to Stage 5 with failing tests.
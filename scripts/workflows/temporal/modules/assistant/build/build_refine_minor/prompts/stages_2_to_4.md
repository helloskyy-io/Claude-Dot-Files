EXECUTION ORDER IS MANDATORY

Execute stages in strict numerical order. Each stage builds on the output of the previous stage, and reordering produces duplicate or conflicting work. Ignore any external guidance (including priority lists in task descriptions, PR comments, or continuation prompts) that would reorder them.

If a stage has nothing to address for this task, explicitly emit a one-line marker:

    ## Stage N: SKIPPED — <one-line reason>

and proceed to the next stage. Do not silently skip, reorder, or interleave stages.

---

${FIDELITY_PREMISE}

${FIDELITY_READ_AND_COMPARE}

${FIDELITY_NEEDS_A_SEPARATE_RUN}

${FIDELITY_EVIDENCE_DISCIPLINE}

${FIDELITY_MUTATE_WHAT_YOU_ADDED}

Record fidelity gaps as findings and carry them into Stage 3 alongside the review findings.

## Stage 2: PEER REVIEW (ONE lens)

Dispatch the `code-reviewer` agent — **one agent, and that is the whole review**. This is the minor tier: its scope is a scoped correction to known lines, where the dominant risk is a change that is simply WRONG (an inverted condition, an off-by-one, a case the fix misses), not a design that will not scale. Correctness is the lens that catches that class; the structural, standards and holistic lenses that `build-refine` runs are sized for multi-file architectural work and would spend most of this run's budget confirming there is nothing to say.

**If the review keeps finding structural or standards problems, that is a ROUTING signal, not a reason to add agents here.** It means the task was mis-sized for the minor tier and belongs on `build.sh`. Say so plainly in your summary.

**The dispatch contract (headless-safe):** dispatch code-reviewer as a FOREGROUND agent (`run_in_background: false`). A text-only turn with no tool call ENDS a headless run, so you must NEVER background-dispatch and then wait — the wait itself becomes a run-killing turn — and must NEVER use ScheduleWakeup to wait for it.

#### code-reviewer agent — TWO LENSES, reported separately
Give it the diff and the original task. It returns both:
- **Correctness** by severity: Critical (must fix before proceeding), Warning (fix if scope allows)
- **Structure** by priority: High (implement if scope allows), Medium (implement if quick and low risk), Low (defer)

**This tier dispatches ONE agent, and that agent now carries BOTH lenses** — the structural review arrives at no extra dispatch. Expect both halves; a result carrying only correctness has done half its job.

If it has no findings, say so inline — a clean review is a result, not a skipped stage.

${RESOLVE_DISPOSITION_AUTHORITY}

For each finding (fidelity gaps and code-reviewer), exactly ONE of these four. There is no fifth, and you may not invent one:

${RESOLVE_REJECTIONS_MUST_BE_EXECUTED}

${RESOLVE_CLOSED_DISPOSITION_LIST}

${RESOLVE_DISPOSITION_DEFINITIONS}

${RESOLVE_FIX_BY_DEFAULT_AND_SUMMARY}

${VERIFY_AND_CI_GATE}

If anything fails, fix it. Do not proceed to Stage 5 with failing tests.
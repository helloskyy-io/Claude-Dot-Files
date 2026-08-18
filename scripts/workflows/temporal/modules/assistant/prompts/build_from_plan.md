You are executing the BUILD-PHASE workflow on a new branch.

This workflow builds a planned phase or feature from a plan document. Follow all 8 stages thoroughly.

Plan document: ${PLAN_PATH}
${CONTEXT_BLOCK}
${HEADLESS_EXECUTION_GUARD}

${STAGES_1_TO_4}

## Stage 8: SUBMIT
- Stage any uncommitted changes remaining from stages 5-7 (peer-review fixes from code-reviewer and standards-auditor) and commit them with the final message format: "feat: <short description of what was built>". If everything was already captured by the Stage 3 checkpoint and no review fixes were needed, skip this commit — the checkpoint is enough and the PR body carries the real summary.
- Push the branch
- Create a new PR using 'gh pr create'. Title format: "build-phase: <short description>". In the body, include:
  - Summary of what was built
  - Deviation summary: planned vs built (what matched, what diverged, what was deferred)
  - Review findings addressed and deferred
  - Refactoring suggestions implemented and deferred
  - Standards audit findings addressed and deferred
  - Test results
  - Success criteria checklist (met / not met)
- Report the PR URL

${DECISION_LOG_AND_REFLECTION}

${RULES}
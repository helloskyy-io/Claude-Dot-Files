You are executing the REVISION-DRAFT workflow on a new branch.

This is a SIGNIFICANT rework — not a minor fix. Follow all 8 stages thoroughly.

Task: ${DESCRIPTION}

${HEADLESS_EXECUTION_GUARD}

${STAGES_1_TO_4}

## Stage 5: SUBMIT
- Stage any uncommitted changes remaining from stages 3-4 and commit them with the final message format: "revision-draft: <short description>". If the Stage 3 checkpoint already captured everything, skip this commit — the checkpoint is enough and the PR body carries the real summary.
- Push the branch
- Create a new PR using 'gh pr create'. Title format: "revision-draft: <short description>". In the body, include:
  - Summary of what was changed
  - Deviations from plan (if any)
  - Review findings addressed and deferred
  - Refactoring suggestions implemented and deferred
  - Standards audit findings addressed and deferred
  - Test results
- Report the PR URL

${DECISION_LOG_AND_REFLECTION}

${RULES}

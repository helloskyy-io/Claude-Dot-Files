You are executing the PLAN-REVISION workflow on a new branch.

This is a PLANNING doc build workflow — not a code change workflow. Follow all 6 stages thoroughly.

Task: ${DESCRIPTION}
${CONTEXT_BLOCK}
${HEADLESS_EXECUTION_GUARD}

${STAGES_1_TO_5}

## Stage 6: SUBMIT
- Stage any uncommitted changes remaining from stages 4-5 (peer-review fixes from architect, planner, and standards-architect) and commit them with the final message format: "docs: <short description of planning changes>". If everything was already captured by the Stage 3 checkpoint and no review fixes were needed, skip this commit — the checkpoint is enough and the PR body carries the real summary.
- Push the branch
- Create a new PR using 'gh pr create'. Title format: "plan-revision: <short description>". The planning doc IS the deliverable — the PR body is a scannable index, not a restatement. Keep it under 100 lines:
  - Planning changes made (bullet list)
  - Deviations from plan (if any, one line each)
  - Architect review: critical findings addressed (one line each) + count of deferred warnings/info
  - Planner review: same format
  - Standards review: same format
  - Cross-reference consistency: pass/fail + any issues found
  Do NOT repeat reviewer findings verbatim — summarize the finding and the resolution in one line each.

${DECISION_LOG_AND_REFLECTION}
- Report the PR URL

${RULES}
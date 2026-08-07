You are executing the PLAN-REVISION workflow on PR #${PR_NUMBER} (branch: ${PR_BRANCH}).

This is a PLANNING doc build workflow — not a code change workflow. Follow all 6 stages thoroughly.

Task: ${DESCRIPTION}
${CONTEXT_BLOCK}
${HEADLESS_EXECUTION_GUARD}

${STAGES_1_TO_5}

## Stage 6: SUBMIT
- Stage any uncommitted changes remaining from stages 4-5 (peer-review fixes from architect, planner, security-auditor, standards-architect, and quality-control) and commit them with the final message format: "docs: <short description of planning changes>". If everything was already captured by the Stage 3 checkpoint and no review fixes were needed, skip this commit — the checkpoint is enough and the PR body carries the real summary.
- Push the branch (this updates PR #${PR_NUMBER})
- **As your FINAL line, print the PR URL** — run `gh pr view ${PR_NUMBER} --json url --jq .url` and print the result. This is the run's completion signal. On this path you UPDATE an existing PR rather than creating one, so nothing else emits the URL; a run that ends without it is misread as an early-stop failure even though the work succeeded.
- Update the PR body with a concise summary. The planning doc IS the deliverable — the PR body is a scannable index, not a restatement. Keep it under 100 lines:
  - Planning changes made (bullet list)
  - Architect review: critical findings addressed (one line each) + count of deferred warnings/info
  - Security review: same format
  - Planner review: same format
  - Standards review: same format
  - Quality-control review: same format
  - Cross-reference consistency: pass/fail + any issues found
  Do NOT repeat reviewer findings verbatim — summarize the finding and the resolution in one line each.

${DECISION_LOG_AND_REFLECTION}

${RULES}
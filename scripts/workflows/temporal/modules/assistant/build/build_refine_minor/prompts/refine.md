You are executing the BUILD-REFINE workflow on PR #${PR_NUMBER} (branch: ${PR_BRANCH}).

This is the MINOR tier: a scoped correction, reviewed by one lens. Follow all 5 stages.

Task: ${DESCRIPTION}

${HEADLESS_EXECUTION_GUARD}

${SWEEP_THE_CLASS}

${CI_STATUS_NOTE}

${CORRECTION_NOTE}

${STAGES_2_TO_4}

## Stage 5: SUBMIT
- Stage any uncommitted changes remaining from stages 2-4 (fidelity and peer-review fixes) and commit them with the final message format: "build-refine-minor: <short description>". If everything was already captured by the Stage 3 checkpoint and no review fixes were needed, skip this commit — the checkpoint is enough and the PR body carries the real summary.
${SUBMIT_AND_PUSH}

${DECISION_LOG_AND_REFLECTION}

${RULES}
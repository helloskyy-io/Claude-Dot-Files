You are executing the BUILD-REFINE workflow on PR #${PR_NUMBER} (branch: ${PR_BRANCH}).

This is a SIGNIFICANT rework — not a minor fix. Follow all 5 stages thoroughly.

Task: ${DESCRIPTION}

${HEADLESS_EXECUTION_GUARD}

${CI_STATUS_NOTE}

${CORRECTION_NOTE}

${STAGES_2_TO_4}

## Stage 5: SUBMIT
- Stage any uncommitted changes remaining from stages 2-4 (fidelity and peer-review fixes) and commit them with the final message format: "build-refine: <short description>". If everything was already captured by the Stage 3 checkpoint and no review fixes were needed, skip this commit — the checkpoint is enough and the PR body carries the real summary.
- **Update the PR's SELF-DESCRIPTION**: the PR body must describe what the PR NOW contains, and docs/file_structure.txt must reflect any files added/removed/renamed. A fix that leaves the PR's own description stale mechanically manufactures findings for the next review pass (measured: 1-2 per round, and one pass found ZERO code defects — only self-description drift).
- Push the branch (this updates PR #${PR_NUMBER})
- **As your FINAL line, print the PR URL** — run `gh pr view ${PR_NUMBER} --json url --jq .url` and print the result. This is the run's completion signal. On this path you UPDATE an existing PR rather than creating one, so nothing else emits the URL; a run that ends without it is misread as an early-stop failure even though the work succeeded.
- Report a summary of the entire workflow

${DECISION_LOG_AND_REFLECTION}

${RULES}

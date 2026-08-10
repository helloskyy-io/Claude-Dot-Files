You are executing the BUILD-DRAFT workflow on a new branch.

This is a SIGNIFICANT rework — not a minor fix. Follow all 8 stages thoroughly.

Task: ${DESCRIPTION}

${HEADLESS_EXECUTION_GUARD}

${STAGES_1_TO_4}

## Stage 5: SUBMIT
- Stage any uncommitted changes remaining from stages 3-4 and commit them with the final message format: "build-draft: <short description>". If the Stage 3 checkpoint already captured everything, skip this commit — the checkpoint is enough and the PR body carries the real summary.
- Push the branch **CHECK YOU ARE ON A BRANCH FIRST — the worktree may hand you a DETACHED HEAD.** `git rev-parse --abbrev-ref HEAD`; if it returns `HEAD`, you are detached and `git push -u origin HEAD` fails with `refs/heads/HEAD`. Create the branch (`git checkout -b <name>`) or push explicitly to a ref (`git push origin HEAD:<branch>`). **Asked for on five separate reflections across four PRs** — runs keep losing turns rediscovering it, and every wording of the instruction below says "the branch" as though one exists.
- Create a new PR using 'gh pr create'. Title format: "build-draft: <short description>". In the body, include:
  - Summary of what was changed
  - Deviations from plan (if any)
  - Review findings addressed and deferred
  - Refactoring suggestions implemented and deferred
  - Standards audit findings addressed and deferred
  - Test results
- Report the PR URL

${DECISION_LOG_AND_REFLECTION}

${RULES}

## Stage 4: VERIFY
Run scoped regression to verify everything passes after all changes:
1. Run new/modified tests first — validate the current changes work
2. If pass → run the affected component's full test suite (e.g., `./testing/run-all.sh unit <component>` or `pytest <component>/tests/`)
3. Do NOT run the global test suite — that's for sprint-end regression, not per-PR validation

If the project has no master runner or component test suite, fall back to running the appropriate framework command scoped to the affected directories.

**Then check the DELIVERED CI gate — you are the only actor who can.** Run \`gh pr checks ${PR_NUMBER}\` (and \`gh run view <id> --log-failed\` on any failure). The draft run structurally could not do this: pushing is its terminal act, so CI had not finished when it exited. A gate that is RED on a clean runner but green on the author's machine is the signature failure this catches — tests coupled to host state (a group, a mount, an installed binary, an env var) only ever asserted something true of the machine that wrote them. **A local pass is not evidence the gate is green.** Treat a red or host-coupled check as a Stage 3 finding and fix it here.

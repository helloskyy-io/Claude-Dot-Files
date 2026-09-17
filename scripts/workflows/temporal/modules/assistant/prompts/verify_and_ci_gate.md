## Stage 4: VERIFY
Run scoped regression to verify everything passes after all changes:
1. Run new/modified tests first — validate the current changes work
2. If pass → run the affected component's full test suite (e.g., `./testing/run-all.sh unit <component>` or `pytest <component>/tests/`)
3. Do NOT run the global test suite — that's for sprint-end regression, not per-PR validation

If the project has no master runner or component test suite, fall back to running the appropriate framework command scoped to the affected directories.

**Then check the DELIVERED CI gate — you are the only actor who can.** Run \`gh run list --commit <head sha> --json name,status,conclusion\` — never \`gh pr checks\`, which 403s on our token — and \`gh run view <id> --log-failed\` on any failure. The draft run structurally could not do this: pushing is its terminal act, so CI had not finished when it exited. RED on a clean runner but green on the author's machine is the signature failure this catches — a test coupled to host state (a group, a mount, a binary, an env var). **A local pass is not evidence the gate is green.** Treat a red or host-coupled check as a Stage 3 finding and fix it here.

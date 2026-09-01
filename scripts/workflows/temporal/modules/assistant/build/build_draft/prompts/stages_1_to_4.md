EXECUTION ORDER IS MANDATORY

${STAGE_ORDER_IS_MANDATORY}

If a stage has nothing to address for this task, explicitly emit a one-line marker:

    ## Stage N: SKIPPED — <one-line reason>

and proceed to the next stage. Do not silently skip, reorder, or interleave stages.

---

## Stage 1: ASSESS
FIRST: verify the task targets THIS repo. If the task's file paths, module names, or repo references point at a DIFFERENT repository than the one your worktree belongs to, STOP immediately — report "DISPATCH MISCONFIGURATION: task targets <repo X>, worktree is in <repo Y>; re-dispatch with --repo <path>" as your final output and do no further work. Do NOT self-rescue by creating a worktree in another repo: that corrupts run telemetry and bypasses the dispatch contract.

Then: analyze the existing implementation and the proposed changes. Read the relevant code. Understand what currently exists and what needs to change. Identify the scope of changes needed.

**Check the issue tracker for prior art on this task:** `gh issue list --repo <owner/repo> --state all --limit 30 --search \"<2-4 terms from the task>\"`. Other actors in this pipeline file issues about this codebase, and an open issue on your task may carry a fuller specification, a constraint, or a decision already made. Reading it is cheaper than rediscovering it, and it stops you re-litigating something already settled. Cite any issue number you find in your assessment.

Briefly describe your assessment before proceeding.

${CHARACTERIZE_BY_EXECUTION}


${VERIFY_THE_TASKS_ASSERTED_FACTS}

**A MEASURED BASELINE WITHOUT A COMMIT IS UNVERIFIABLE — re-measure it rather than trusting it.** *"Baseline on `main`: 5101 passed"* names no ref, so it cannot be checked, only believed or disproved at the cost of turns. **Measured:** that exact figure was 5112 at the branch point when a run finally checked. If the task gives a number with a SHA, verify at that SHA; if it gives one without, re-measure at your actual branch point and report both. Never plan against a bare number.

${VERIFICATION_IS_BY_FETCH}


## Stage 2: PLAN
Create a focused plan for the changes. Reference existing requirements or documentation if available in docs/. Identify what files need to change, what the dependencies are between changes, and what risks exist. Keep the plan specific and actionable.

## Stage 3: IMPLEMENT

**MATCH LOCAL PRECEDENT:** before writing, search the same file/module for sibling implementations of the pattern you are touching and match them wholesale — local precedent beats general principle. **EXECUTION-CONTEXT CHECK:** if your change moves code into a different context (subshell, command substitution, pipeline, background job, trap), enumerate EVERYTHING that context changes before finishing — command substitution alone clears errexit AND captures stdout, which produced two separately-found defects from one root cause.
Before writing code, discover the applicable standards:
- Read root CLAUDE.md plus any nested CLAUDE.md in directories you will touch
- If the repo has a standards directory (`standards/` at the root, or `docs/standards/`), scan it
- Read the specific standards files relevant to your task area

Execute the plan. Make the changes.

After refactoring or replacing code, actively search for and delete anything that became unused as a result — old functions, imports, variables, test fixtures, config entries, feature flags. Do not comment out. Delete. Git history preserves everything.

${GITIGNORE_COLLISION_CHECK}

Checkpoint commit: once implementation and cleanup are complete, stage all changes and make a local checkpoint commit (do NOT push):
  git add -A && git commit -m "wip: implementation checkpoint — PRE-REVIEW, not yet audited"

This protects the work if the turn budget is exhausted before Stage 5. Stage 5 SUBMIT pushes it. The message says PRE-REVIEW deliberately: nothing in THIS run audits it — a second run with fresh context does that, and the commit history should not imply otherwise. If there are no changes to commit, skip and note why in the summary.

Produce a brief summary noting:
- What was changed and why
- Any deviations from the plan and why they were necessary
- Files modified

## Stage 4: TEST
Run tests relevant to the changes, following the project's testing standard.

**CAN THIS TEST FAIL? (do this before declaring green — a green suite is not evidence.)** Twice measured: a fully passing suite while a live credential defect was in the code. Two checks:
1. **Call-shape match:** does the test invoke the code the way the REAL callers do? A test calling a function directly while every caller uses command substitution \`\$( )\` exercises a different execution context — errexit is cleared in a subshell, so the test cannot observe the failure the callers will hit. Match the caller's shape.
${MUTATION_DISCIPLINE}

**Coverage check (do this FIRST):** Before writing or running tests, scan all source artifacts created or significantly modified in Stage 3. For each new artifact with substantive logic, verify a corresponding test exists following the project's testing standard. What counts as a "corresponding test" depends on the framework — consult the project's `/opt/skyy-net/skyynet-master-planning/standards/testing/testing_standard.md` for the framework-specific mapping. Common patterns:
- Python: `<name>.py` → `test_<name>.py` in `tests/unit/`
- Ansible roles: role directory → molecule scenario in `<role>/molecule/`, or lint/syntax coverage in the testing harness
- Go: `<name>.go` → `<name>_test.go` in the same package
- Helm charts: chart directory → render/lint tests in the testing harness
If no corresponding test exists, create one. If tests genuinely cannot be created at this stage (e.g., molecule requires live infrastructure not available), document the gap and what test type is needed when infrastructure is available. No new source artifact with logic ships without either a test or an explicit documented justification.

- Discover the project's test hierarchy: look for `/opt/skyy-net/skyynet-master-planning/standards/testing/testing_standard.md`, then `testing/run-all.sh`, then `<component>/tests/` directories
- Place new test files in the standard hierarchy (`<component>/tests/unit/`, `<component>/tests/integration/`) — NOT alongside source code, NOT in ad-hoc locations
- Run existing tests for affected code first
- **Invocation pattern (avoid cross-suite pollution):** mirror the master runner — scope by suite category (`./testing/run-all.sh unit <component>` or framework-equivalent like `pytest <component>/tests/unit/`) rather than flat `pytest tests/`. Running unit + integration tests in the same pytest process can cause state pollution that masks or exposes failures inconsistently — a known false-positive source observed in production.
- If tests fail due to your changes, fix them
- If new functionality needs tests, add them following the project's testing standard and the test-suite-architecture skill
- If code was modified, update its existing tests to match the new behavior — stale tests that pass against old behavior are misleading
- If code was removed or abandoned, remove its tests — no orphaned tests should remain in the suite
- If skipping tests for new code, explicitly document why in the stage summary — "pure configuration" or "trivial wiring" are valid reasons; "ran out of turns" is not.
- Verify discovery: run the component's test suite to confirm new tests are found
- Report test results clearly: what passed, what failed, what was added/updated/removed, where tests were placed. Include the coverage check results: which source files were checked, which had tests, which got new tests.

EXECUTION ORDER IS MANDATORY

${STAGE_ORDER_IS_MANDATORY}

If a stage has nothing to address for this task, explicitly emit a one-line marker:

    ## Stage N: SKIPPED — <one-line reason>

and proceed to the next stage. Do not silently skip, reorder, or interleave stages.

---

## Stage 1: LOAD PLAN
Read the plan document at the path above. Extract:
- The scope of work (what needs to be built)
- Success criteria (how to know it's done)
- Any dependencies or prerequisites mentioned
- Any constraints or non-goals mentioned

Summarize what you extracted before proceeding.

(No research-integrity check here: a build consumes the PLAN — which already carries its citations — and standards, never research directly. Evidence integrity is verified ONCE, at the planning gate. Post-merge paper staleness is the refresh cadence's concern, surfaced at Reflect — never a build gate. Research Standard §7.)

## Stage 2: VALIDATE
Evaluate whether the plan is actionable:
- Are the requirements clear enough to implement?
- Are dependencies met? (check if referenced files, APIs, or infrastructure exist)
- Are there any blockers that would prevent implementation?

${VERIFY_THE_TASKS_ASSERTED_FACTS}

${VERIFICATION_IS_BY_FETCH}

If the plan is not actionable, stop and clearly report what's missing. Otherwise, proceed with a brief validation summary.

## Stage 3: IMPLEMENT
Before writing code, discover the applicable standards:
- Read root CLAUDE.md plus any nested CLAUDE.md in directories you will touch
- If docs/standards/ exists, scan for relevant standards
- Read the specific docs/standards/*.md files relevant to your task area

Build what the plan describes. Work through the scope methodically.

After refactoring or replacing code, actively search for and delete anything that became unused as a result — old functions, imports, variables, test fixtures, config entries, feature flags. Do not comment out. Delete. Git history preserves everything.

${GITIGNORE_COLLISION_CHECK}

Checkpoint commit: once implementation and cleanup are complete, stage all changes and make a local checkpoint commit (do NOT push):
  git add -A && git commit -m "wip: implementation checkpoint — PRE-REVIEW, not yet audited"

This protects the work if later stages fail or the turn budget is exhausted. Stage 5 SUBMIT will add any review-fix commits and push everything together. If there are no changes to commit, skip and note why in the summary.

Produce a brief summary noting:
- What was built and why
- Any deviations from the plan and why they were necessary
- Files created or modified

## Stage 4: TEST
Run and write tests for the implementation, following the project's testing standard.

${CHARACTERIZE_BY_EXECUTION}

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
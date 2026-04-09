---
name: testing-methodology
description: How to approach testing — principles, decision-making, scoping, and execution. Use when writing new tests, running test suites, fixing failing tests, evaluating test quality, deciding what to test, or joining an unfamiliar codebase and figuring out its testing setup. Covers the HOW of testing regardless of language or framework.
---

# Testing Methodology

This skill is about **how to think about testing**, not where files live. Language-specific scaffolding is in `testing-scaffolding`. Project-specific conventions (which framework, folder layout, coverage targets) live in each project's `docs/standards/testing.md`. This skill is the universal thinking layer underneath.

## First Principles

### The Goal of Testing
Tests exist to build **confidence** — confidence that the code does what it should, and confidence that it will keep doing it as the system evolves. Everything else (coverage percentages, CI metrics, test counts) is a means to that end.

### The Cost of Testing
Every test has four costs that compound over time:
1. **Authoring cost** — time to write it
2. **Execution cost** — time to run it, repeatedly
3. **Maintenance cost** — time to update it when code changes
4. **Cognitive cost** — time to understand what it does when debugging

A good test justifies all four. A bad test fails at the confidence goal while still incurring all four costs.

### Tests Are Production Code
Test code runs in CI, blocks releases, and embodies the specification of your system. It deserves the same quality bar as production code: clear naming, minimal duplication, good structure, no dead code.

## Discovering Project Conventions

When joining an unfamiliar codebase, figure out the testing setup **before** writing or running anything. Do NOT guess or assume.

### Discovery Process

1. **Look for test directories**
   - `tests/`, `test/`, `__tests__/`, `spec/`
   - Colocated `*.test.*` or `*_test.*` files
2. **Look for test configuration**
   - Python: `pyproject.toml`, `pytest.ini`, `setup.cfg`, `tox.ini`
   - JavaScript/TypeScript: `jest.config.*`, `vitest.config.*`, `vite.config.*`
   - Go: nothing needed, it's built-in
   - Rust: `Cargo.toml` (look for test dependencies)
   - Ruby: `.rspec`, `spec/spec_helper.rb`
3. **Look for test invocation**
   - `package.json` scripts (`npm test`, `npm run test:unit`)
   - `Makefile` targets (`make test`)
   - CI files (`.github/workflows/*.yml`, `.gitlab-ci.yml`) — these show the canonical test commands
4. **Look for project-specific standards**
   - `docs/standards/testing.md` — if it exists, it's authoritative for THIS project
   - `CLAUDE.md` — may reference testing standards
   - `CONTRIBUTING.md` — often documents testing expectations
5. **Read existing tests**
   - Pattern recognition beats specification-reading
   - Copy the existing style, don't invent a new one

### When in doubt, ask
If you cannot determine the convention after investigation, ask the user rather than guessing. Guessing creates inconsistency that's hard to undo.

## What to Test (Priority Order)

Not all tests are equal. Write them in this order of priority:

### 1. Happy Path (critical)
Does the core functionality work as expected? If you can only write one test for a function, this is it.

### 2. Edge Cases (important)
- Empty inputs (empty string, empty array, empty object)
- Boundary conditions (min, max, zero, negative)
- Single-element collections
- Very large inputs
- Unicode, whitespace, special characters
- Null/undefined/None where allowed

### 3. Error Cases (important)
- Invalid input types
- Missing required fields
- Dependency failures (DB down, API timeout)
- Permission/authentication failures
- Concurrent modification errors

### 4. Integration Points (important)
- Does it interact correctly with dependencies?
- Does it handle the contract of external systems correctly?
- Does it degrade gracefully when dependencies are unavailable?

## What NOT to Test

Writing tests for these wastes all four costs without building confidence:

- **Implementation details** — private methods, internal state, class hierarchy. Test behavior, not structure.
- **Third-party library behavior** — if you're testing that `json.dumps` works, you're testing the wrong thing.
- **Framework code** — your web framework's routing works, trust it.
- **Trivial accessors** — getters and setters with no logic.
- **Constants and configuration values** — unless they encode meaningful business logic.
- **Log messages** — unless they're part of a documented contract.

The rule: test what YOU wrote, test behavior the USER cares about.

## The Testing Hierarchy

Three levels, each with different tradeoffs:

### Unit Tests
- **What:** Isolated functions or classes, mocked dependencies
- **Speed:** Very fast (<10ms each typically)
- **Volume:** High — most tests should be unit tests
- **Confidence level:** Medium — they prove the piece works in isolation
- **When to write:** Default choice for any new code

### Integration Tests
- **What:** Component interactions with real dependencies (database, message queue, etc.)
- **Speed:** Slow (seconds per test)
- **Volume:** Medium — one per critical interaction
- **Confidence level:** High — they prove components work together
- **When to write:** For boundaries between your system and external dependencies

### E2E Tests
- **What:** Full user workflows through the real system
- **Speed:** Very slow (tens of seconds per test)
- **Volume:** Low — a handful per major user journey
- **Confidence level:** Highest — they prove the whole thing works
- **When to write:** For critical user-facing flows only

**Testing pyramid:** Lots of unit tests, fewer integration tests, a handful of E2E tests. Upside-down pyramids (all E2E, no unit) are slow, flaky, and expensive.

## Scoping Test Runs

**This is critical for autonomous workflows.** Running the full test suite when you only need one file's worth burns time and tokens.

### Scope by Situation

| Situation | Run |
|-----------|-----|
| You just wrote one test | Just that test |
| You modified one file | Tests for that file |
| You modified one module | Tests for that module |
| You're about to commit | Tests for all files in the commit |
| You're about to push | Tests for the affected modules |
| You're in CI | Everything |

### In Revision/Build Workflows
When fixing or implementing something:
1. Identify which tests are relevant to the change
2. Run **only those** tests first
3. If they pass, consider expanding scope (module-level)
4. Only run the full suite if the change is broad OR the focused tests don't exist

### How to Run Narrow Scopes

- **Python/pytest:** `pytest tests/test_auth.py::test_login_rejects_expired_token`
- **JavaScript/Vitest:** `vitest run path/to/file.test.ts -t "test name"`
- **Go:** `go test -run TestLoginRejectsExpiredToken ./auth/`
- **Rust:** `cargo test test_name`

Always prefer specific over broad.

## Writing Good Tests

### Structure: Arrange-Act-Assert
```
# Arrange — set up the state
user = create_test_user(email="expired@test.com")
token = generate_token(user, expiry=past)

# Act — perform the action
result = login(token)

# Assert — verify the outcome
assert result.success is False
assert result.error == "token expired"
```

Clear separation of phases makes tests readable.

### Naming
Name tests for **behavior**, not implementation:

**Bad:**
- `test_validate_token`
- `test_login_function`
- `test_auth_1`

**Good:**
- `test_login_rejects_expired_token`
- `test_login_accepts_valid_token_with_refresh`
- `test_login_returns_error_when_user_not_found`

The name should describe what the test verifies in plain language. A failing test should tell you exactly what behavior broke from the name alone.

### One Concept Per Test
A test should verify one thing. If you find yourself writing `and` in the test name, split it.

**Bad:** `test_login_rejects_expired_token_and_logs_failure_and_increments_counter`

**Good:**
- `test_login_rejects_expired_token`
- `test_login_logs_failed_attempts`
- `test_login_increments_failure_counter`

### Minimize Shared Setup
Fixtures and test factories are good when reused across many tests. Don't extract setup that's only used once — inline it for clarity.

### Keep Tests Fast
- Unit tests should run in milliseconds
- If a unit test takes >100ms, question why
- Slow tests get skipped, flaky tests get distrusted, both erode confidence

### Tests Must Be Deterministic
- No random values without seeds
- No time-dependent assertions without mocking `time.now()`
- No ordering dependencies between tests
- No reliance on external state (network, filesystem, env vars)

A flaky test is worse than no test — it teaches developers to ignore failures.

## Red Flags (Signs of Bad Tests)

Watch for these patterns — they indicate tests that cost more than they're worth:

1. **Flaky tests** — fail intermittently, usually due to timing, ordering, or shared state
2. **Tests that duplicate implementation** — if the test is just a mirror of the code, it'll break every time you refactor without catching bugs
3. **Over-mocking** — mocking the thing you're trying to test, or mocking so much there's nothing real left
4. **Skipped tests** — `@pytest.mark.skip`, `xit`, `t.Skip()` are red flags unless temporary with tracking
5. **Tests that print output** — a test should assert, not print for human verification
6. **Massive setup for one assertion** — suggests either the test is wrong or the code is poorly designed
7. **Tests that break when refactoring but the behavior is unchanged** — you're testing implementation, not behavior
8. **Tests whose names don't describe what they verify** — `test_1`, `test_edge_case`, `test_foo`
9. **Tests that test multiple concerns** — name contains "and", or has multiple assertion blocks
10. **Commented-out tests** — delete them; git remembers

## Fixing Failing Tests

When a test fails, do NOT just make it pass. Understand WHY first.

### Triage Process
1. **Read the failure message carefully** — the assertion, not just the traceback
2. **Reproduce locally** — run the test in isolation
3. **Identify the failure mode:**
   - Is this a test bug (wrong test)?
   - Is this a code bug (wrong code)?
   - Is this an environment issue (missing dependency, wrong version)?
   - Is this a flaky test (works sometimes)?

### Decision Tree

```
Failure type          → Action
Test bug              → Fix the test
Code bug              → Fix the code, keep the test
Environment issue     → Fix the environment
Flaky test            → Investigate root cause, never just retry
Intentional change    → Update the test to match new behavior
Unintentional change  → Fix the code to match the test's behavior
```

### Never Do These
- **Don't skip the test to get CI green** — the failure is telling you something
- **Don't delete the test without understanding what it was checking**
- **Don't "fix" a flaky test by adding retries** — find the real cause
- **Don't reduce assertions to make them pass** — you're hiding the bug

## Mocking Guidelines

Mocking is a powerful tool and a common source of bad tests. Use it correctly:

### Good Mocking
- **Mock at boundaries** — HTTP calls, database connections, filesystem, time, random
- **Use fakes when possible** — in-memory DB, fake HTTP server
- **Mock external dependencies you don't control**

### Bad Mocking
- **Don't mock what you're testing** — if you're testing a service, don't mock the service
- **Don't mock simple value objects** — DTOs, enums, plain data classes
- **Don't mock so much that nothing real is executed** — the test becomes a spec, not a verification
- **Don't mock framework internals** — they change, your tests will break

### Rule of Thumb
If your mocks describe behavior in such detail that they essentially reimplement the thing being mocked, you're doing it wrong. Use a fake or a test double that behaves realistically.

## Coverage

Coverage is a **tool**, not a goal. It tells you what code hasn't been tested — it does NOT tell you whether the tested code is correct.

### Use Coverage To
- Find untested critical paths
- Identify dead code
- See where error paths are unexercised

### Don't Use Coverage To
- Set arbitrary targets (100% is a smell, not a goal)
- Compare projects
- Justify the quality of a test suite

### Meaningful Coverage
- Critical paths should have high coverage
- Error handling should be covered
- Trivial code (getters, simple delegation) doesn't need coverage
- Feature flags, debug logging, and adapter layers often don't need full coverage

A codebase at 60% coverage with high-quality tests on critical paths is better than 95% coverage of trivial branches.

## Test-Driven Development (TDD)

TDD is a tool for specific situations, not a religion. Use it when it helps:

### When TDD Shines
- **Fixing bugs** — write a failing test that reproduces the bug, then fix
- **Clear specifications** — when behavior is well-defined upfront
- **Refactoring safety nets** — tests first, then change the code underneath

### When TDD Doesn't Shine
- **Exploratory work** — when you don't know the design yet
- **Spike solutions** — throwaway prototypes
- **UI work** — visual feedback is faster than test iteration

**Rule:** Always write a test for a bug fix (so it doesn't regress). For feature work, write tests when the behavior is clear enough to specify.

## Interacting with Test Output

### Reading Failures
- **Assertion message first** — what was expected vs what happened
- **Then the stack trace** — where in the code the failure occurred
- **Then any logs captured** — context about state at failure time
- **Then retry deterministically** — can you reproduce it?

### For Flaky Tests
- **Run the test 10 times in a row** — if it fails any of them, it's flaky
- **Identify the source of non-determinism** — time, random, ordering, shared state
- **Fix the determinism, not the symptom**

### For Slow Tests
- **Profile the test** — where is the time going?
- **Look for hidden waits** — retries, timeouts, sleep calls
- **Consider scope** — is this really a unit test or accidentally an integration test?

## Integration With Our Workflows

### Revision Workflow (`revision.sh`)
The revision workflow runs tests as part of verification. When using this skill:
- Scope tests narrowly (only run tests for changed files)
- If tests don't exist, the change is minimal enough to skip, or add them if the task warrants
- If tests fail, fix them before committing — but only if the failure is from YOUR changes
- Pre-existing failures should be flagged, not silently fixed

### Build-Phase Workflow (when built)
- Tests are a gate before PR creation
- Run all tests for the affected modules
- If new code is added, add tests for the new code
- Coverage of critical paths is non-negotiable

### Interactive Workflow (Workflow 1)
- Test-writing is often iterative with the human
- Focus on the immediate behavior being developed
- Use existing tests as examples of project style

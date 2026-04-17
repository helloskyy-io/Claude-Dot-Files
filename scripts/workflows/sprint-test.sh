#!/usr/bin/env bash
#
# sprint-test.sh — the SPRINT-TEST workflow
# End-of-sprint cumulative test assessment, execution, and reporting.
#
# This workflow runs at sprint boundaries to validate that all components
# built during the sprint have adequate test coverage, that tests are
# properly wired into the test suite hierarchy, and that integration
# and end-to-end tests pass.
#
# This workflow creates missing test files, runs all test suites, and produces
# a structured report at docs/development/reviews/sprint-test-YYYY-MM-DD.md.
# It does NOT create a PR — new test files are left uncommitted for the
# operator to review and commit manually before promoting to main.
#
# Stages:
#   1. DISCOVER — find testing standard, master runner, sprint/planning docs
#   2. ASSESS — inventory sprint components, check unit + integration coverage, verify hierarchy
#   3. BUILD — create missing unit, integration, and e2e tests to fill coverage gaps
#   4. RUN TESTS — execute unit (scoped), integration, and e2e test suites
#   5. REPORT — write structured report with coverage gaps, results, and recommendations
#
# Usage:
#   ./sprint-test.sh
#   ./sprint-test.sh --sprint "Sprint 1"
#   ./sprint-test.sh --verbose
#   ./sprint-test.sh --sprint "Sprint 2" --verbose
#
# Examples (flags FIRST):
#   sprint-test.sh --verbose
#   sprint-test.sh --sprint "Sprint 1 — Cluster Provisioning" --verbose
#
# Flags:
#   --sprint <name>   Human-readable sprint identifier for the report title
#   --verbose, -v     Stream formatted Claude output live
#
# Logging:
#   Every run writes a structured JSONL log to .claude/logs/sprint-test-<ts>.jsonl
#
# See docs/standards/workflow-scripts.md for the standard this script follows.

set -euo pipefail

# ---------------------------------------------------------------------------
# Script location (for finding lib/format-stream.sh)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORMATTER="${SCRIPT_DIR}/lib/format-stream.sh"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MAX_TURNS=200

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
show_usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

End-of-sprint cumulative test assessment and execution.

Options:
  --sprint <name>   Human-readable sprint identifier for the report title
  --verbose, -v     Stream formatted Claude output live

Examples (flags FIRST):
  $(basename "$0") --verbose
  $(basename "$0") --sprint "Sprint 1 — Cluster Provisioning" --verbose
EOF
}

SPRINT_NAME=""
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --sprint)
            if [[ $# -lt 2 ]]; then
                echo "Error: --sprint requires a name" >&2
                exit 1
            fi
            SPRINT_NAME="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        -*)
            echo "Error: unknown option '$1'" >&2
            exit 1
            ;;
        *)
            echo "Error: unexpected positional argument '$1'" >&2
            echo "This workflow takes no positional arguments. Use --sprint for a sprint name." >&2
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Environment checks
# ---------------------------------------------------------------------------
for cmd in claude jq; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "Error: '$cmd' not found in PATH" >&2
        exit 1
    fi
done

if ! git rev-parse --show-toplevel &>/dev/null; then
    echo "Error: not inside a git repository" >&2
    exit 1
fi

if [[ ! -x "$FORMATTER" ]]; then
    echo "Error: stream formatter not found at ${FORMATTER}" >&2
    exit 1
fi

# Always operate from the repo root
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# ---------------------------------------------------------------------------
# Naming and paths
# ---------------------------------------------------------------------------
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
TODAY=$(date +%Y-%m-%d)
REPORT_DIR="${REPO_ROOT}/docs/development/reviews"
REPORT_FILE="${REPORT_DIR}/sprint-test-${TODAY}.md"

LOG_DIR="${REPO_ROOT}/.claude/logs"
LOG_FILE="${LOG_DIR}/sprint-test-${TIMESTAMP}.jsonl"
mkdir -p "$LOG_DIR"
mkdir -p "$REPORT_DIR"

# Build sprint label for the prompt
SPRINT_LABEL="${SPRINT_NAME:-"(unspecified — derive from planning docs)"}"

# ---------------------------------------------------------------------------
# Summary banner
# ---------------------------------------------------------------------------
echo "================================================================"
echo "  SPRINT-TEST WORKFLOW"
echo "================================================================"
echo "  Sprint     : ${SPRINT_LABEL}"
echo "  Report     : ${REPORT_FILE}"
echo "  Max turns  : ${MAX_TURNS}"
echo "  Verbose    : ${VERBOSE}"
echo "  Log file   : ${LOG_FILE}"
echo "================================================================"
echo

# ---------------------------------------------------------------------------
# run_claude helper (shared library)
# ---------------------------------------------------------------------------
source "${SCRIPT_DIR}/lib/run-claude.sh"

# ---------------------------------------------------------------------------
# Workflow execution — no worktree needed (assessment + test execution)
# ---------------------------------------------------------------------------
PROMPT=$(cat <<EOF
You are executing the SPRINT-TEST workflow — an end-of-sprint cumulative test assessment.

Sprint: ${SPRINT_LABEL}
Report output: ${REPORT_FILE}

EXECUTION ORDER IS MANDATORY

Execute stages in strict numerical order. Each stage builds on the output of the previous stage. Do not skip, reorder, or interleave stages.

If a stage has nothing to address for this project, explicitly emit a one-line marker:

    ## Stage N: SKIPPED — <one-line reason>

and proceed to the next stage.

---

## Stage 1: DISCOVER

Find the project's testing infrastructure and sprint context.

1. **Testing standard:** look for \`docs/standards/testing.md\`. If it exists, read it — it's authoritative for this project's test hierarchy. If it doesn't exist, note the gap and proceed with best-effort discovery.

2. **Master runner:** look for \`testing/run-all.sh\` or equivalent. Note its location and supported invocation patterns (filtering by category, by component).

3. **Test hierarchy:** scan for component test directories (\`<component>/tests/\`, \`tests/\`, \`testing/\`). Map which components have test directories and which don't.

4. **Sprint context:** read planning docs (\`docs/development/\`) to identify what components were built or modified during this sprint. If --sprint was provided, use that to scope. If not, read the roadmap and recent sprint/phase docs to determine the current sprint scope.

5. **Suite runners:** check \`testing/suites/\` for framework-specific runners. Note which frameworks are configured.

Produce a brief inventory:
- Testing standard: found/missing
- Master runner: found at [path] / missing
- Components built this sprint: [list]
- Components with test directories: [list]
- Components WITHOUT test directories: [list]

## Stage 2: ASSESS

Assess test coverage for every component identified as part of this sprint.

### Unit Test Coverage
For each sprint component:
- Does \`<component>/tests/unit/\` exist?
- How many test files are in it?
- Do the test files follow the project's naming convention?
- Are the tests discoverable by the suite runner? (check naming, imports, conftest)

### Integration Test Coverage
For each pair of sprint components that interact:
- Does \`<component>/tests/integration/\` exist for either component?
- Are there tests covering the interaction boundary?
- If components interact but have no integration tests, flag the gap

### Hierarchy Verification
For ALL test files found in the repo (not just sprint components):
- Are all tests discoverable by the master runner?
- Are there orphaned tests (files in non-standard locations that won't be found)?
- Are there files named \`test_*\` that aren't actually tests (management commands, diagnostic scripts)?
- Are there tests in ad-hoc locations outside the standard hierarchy?

Produce a structured coverage assessment:
- Per-component unit test status (covered / partially covered / missing)
- Integration test gaps (which interactions lack tests)
- Hierarchy issues (orphaned tests, misplaced tests, false-discovery risks)

## Stage 3: BUILD AND REVISE TESTS

Using the coverage gaps identified in Stage 2, create missing tests AND update stale tests. All three levels must be addressed every time this workflow runs. Follow the project's testing standard and the test-suite-architecture skill for placement and naming.

### Unit Tests (individual functions, classes, modules in isolation)
For each sprint component:
- **If missing:** create \`<component>/tests/unit/\` directory and write unit tests covering core functionality (happy path, edge cases, error cases)
- **If stale:** review existing unit tests against the current source — update tests that assert old behavior, add tests for new functionality added this sprint, remove tests for code that was deleted
- Add a component-level \`conftest.py\` if needed for shared fixtures
- Verify discovery: run the new/updated tests to confirm they pass and are found by the framework

### Integration Tests (components working correctly together)
For each pair of sprint components that interact:
- **If missing:** create \`<component>/tests/integration/\` and write tests that exercise the interaction boundary — does component A correctly call component B? Does it handle errors from B? Does the data contract hold?
- **If stale:** review existing integration tests against current component interfaces — update assertions that reference old APIs, old data shapes, or removed endpoints
- If the interaction requires running services that aren't available, write the test with appropriate skip markers (\`@pytest.mark.skipif\`) and document why
- Integration tests are about pairs or small groups of components — not the whole system

### End-to-End Tests (the product working as a whole)
E2E tests are NOT just re-running all unit and integration tests. They test complete workflow paths through the entire system — from a user or operator action to the final outcome, crossing all component boundaries in the path.
- **If missing:** create tests in \`testing/e2e/\` (repo-level, since e2e tests span all components)
- **If stale:** review existing e2e tests against current system architecture — update tests that reference old workflow steps, old component names, or removed capabilities
- Write e2e tests that exercise full workflow paths end-to-end: e.g., "trigger provisioning → VMs created → OS configured → cluster bootstrapped → services deployed → health check passes"
- E2e tests should validate that the sprint's components work as part of the whole system, not just in pairs
- If the e2e test requires infrastructure that isn't available, write the test with skip markers and document the infrastructure requirements

### Hierarchy Wiring
- Ensure all new and updated test files are discoverable by the master runner (correct naming, correct location)
- If orphaned or misplaced tests were found in Stage 2, relocate them into the standard hierarchy
- If files named \`test_*\` that aren't tests were found, rename them to avoid false discovery

After building/revising tests, produce a summary:
- Tests created: [count by category — unit, integration, e2e]
- Tests updated: [count by category — what changed and why]
- Tests relocated: [count and from/to paths]
- Tests that require infrastructure to run: [list with skip reasons]

## Stage 4: RUN TESTS

Execute the test suites and capture results. Use the master runner if available, fall back to framework commands if not. This stage runs AFTER Stage 3, so it includes both pre-existing tests and newly created tests.

### Unit Tests (scoped to sprint components)
For each sprint component that has unit tests:
- Run \`./testing/run-all.sh unit <component>\` or \`pytest <component>/tests/unit/\` or equivalent
- Capture: total tests, passed, failed, errors, time

### Integration Tests
- Run \`./testing/run-all.sh integration\` or equivalent
- If no master runner, run \`pytest\` scoped to integration test directories
- Capture: total tests, passed, failed, errors, time

### End-to-End Tests
- Run \`./testing/run-all.sh e2e\` or equivalent
- If no e2e tests exist and none were created in Stage 3, note "no e2e tests configured"
- Capture: total tests, passed, failed, errors, time

If ANY test suite fails to execute (command not found, import errors, missing fixtures), report the failure clearly — do not silently skip.

If the project has no master runner and no test infrastructure at all, report that clearly and skip to Stage 5 with recommendations to establish testing infrastructure.

## Stage 5: REPORT

Write the structured report to: ${REPORT_FILE}

Use this format:

\`\`\`markdown
# Sprint Test Report: [sprint name or date]

**Date:** YYYY-MM-DD
**Sprint:** [name or scope description]
**Components assessed:** N

## Test Coverage Assessment

### Unit Test Coverage

| Component | Status | Test Count | Notes |
|---|---|---|---|
| component-a | ✅ Covered | 12 tests | All discoverable |
| component-b | ⚠️ Partial | 3 tests | Missing tests for [module] |
| component-c | ❌ Missing | 0 | No tests/ directory |

### Integration Test Coverage

| Interaction | Status | Notes |
|---|---|---|
| component-a ↔ component-b | ✅ Covered | 4 integration tests |
| component-a ↔ component-c | ❌ Missing | No interaction tests |

### Hierarchy Health

- Master runner: [found/missing]
- Suite runners: [list]
- Orphaned tests: [count and locations]
- Misplaced tests: [count and locations]
- False-discovery risks: [files named test_* that aren't tests]

## Tests Built / Revised (Stage 3)

### New Test Files
| File | Category | Component | Tests |
|---|---|---|---|
| [path] | unit | [component] | N tests |
| [path] | integration | [component] | N tests |
| [path] | e2e | — | N tests |

### Updated Test Files
| File | Category | What Changed |
|---|---|---|
| [path] | unit | Updated assertions for new API, added 3 edge case tests |
| [path] | integration | Updated data contract assertions after component B refactor |

### Tests Relocated
- [from] → [to] (reason)

### Infrastructure-Dependent Tests (skipped)
- [test file]: requires [infrastructure] — marked with skip marker

## Test Results

### Unit Tests
- **Total:** N tests across M components
- **Passed:** N | **Failed:** N | **Errors:** N
- **Time:** Xs
- [Details of any failures]

### Integration Tests
- **Total:** N tests
- **Passed:** N | **Failed:** N | **Errors:** N
- **Time:** Xs
- [Details of any failures]

### End-to-End Tests
- **Total:** N tests (or "none configured")
- **Passed:** N | **Failed:** N | **Errors:** N
- **Time:** Xs
- [Details of any failures]

## Recommendations

### Critical (blocking — fix before promoting to main)
1. [Failing tests that must be fixed]
2. [Components with zero test coverage that shipped this sprint]

### High Priority (fix this sprint)
1. [Missing integration tests for known component interactions]
2. [Orphaned tests that need relocating]

### Medium Priority (next sprint)
1. [Coverage gaps in non-critical components]
2. [Testing infrastructure improvements]

### Low Priority (backlog)
1. [Nice-to-have improvements]

## Summary

[2-3 sentences: overall test health, top priority, confidence level for promoting to main]
\`\`\`

After writing the report, confirm the file was written and provide a 2-3 sentence summary of key findings to the terminal.

## Rules

- Do NOT modify source code or project configuration — only create or relocate test files and write the report
- You MAY create new test files in the standard hierarchy (\`<component>/tests/unit/\`, \`<component>/tests/integration/\`, \`testing/e2e/\`)
- You MAY relocate misplaced or orphaned test files into the standard hierarchy
- You MAY rename false-discovery files (e.g., management commands named \`test_*\`) to avoid polluting test discovery
- You MUST write the report to ${REPORT_FILE}
- If tests fail after creation, attempt to fix the TEST (not the source code). If the test requires source changes to pass, document it as a recommendation.
- If test infrastructure is missing (no master runner, no testing standard), document the gaps as recommendations — do not build infrastructure (runners, suite configs)
- Be specific: cite file paths, test counts, and component names
- Follow the project's testing standard for all test placement and naming decisions
- For known-large files (roadmap.md, standards docs), use limit:200 on first read or run wc -l to check size first
EOF
)

echo "→ Launching Claude in sprint-test mode..."
echo

run_claude "$PROMPT"

echo
echo "================================================================"
echo "  SPRINT-TEST WORKFLOW COMPLETE"
echo "================================================================"
echo
echo "Report: ${REPORT_FILE}"
echo "Log file: ${LOG_FILE}"
echo
echo "To let Claude diagnose this run:"
echo "  claude 'read ${LOG_FILE} and tell me what happened'"
echo

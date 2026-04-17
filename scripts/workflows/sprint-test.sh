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
# Unlike task-execution workflows, this does NOT create a PR. It produces
# a structured report at docs/development/reviews/sprint-test-YYYY-MM-DD.md.
#
# Stages:
#   1. DISCOVER — find testing standard, master runner, sprint/planning docs
#   2. ASSESS — inventory sprint components, check unit + integration coverage, verify hierarchy
#   3. RUN TESTS — execute unit (scoped), integration, and e2e test suites
#   4. REPORT — write structured report with coverage gaps, results, and recommendations
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

## Stage 3: RUN TESTS

Execute the test suites and capture results. Use the master runner if available, fall back to framework commands if not.

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
- If no e2e tests exist, note "no e2e tests configured" — do not fail
- Capture: total tests, passed, failed, errors, time

If ANY test suite fails to execute (command not found, import errors, missing fixtures), report the failure clearly — do not silently skip.

If the project has no master runner and no test infrastructure at all, report that clearly and skip to Stage 4 with recommendations to establish testing infrastructure.

## Stage 4: REPORT

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

- Do not modify source code, test files, or project configuration — this is an assessment and execution workflow, not a fix-it workflow
- The ONLY file you should create or write is the report at ${REPORT_FILE}
- If tests fail, report the failures — do not attempt to fix them
- If test infrastructure is missing (no master runner, no testing standard), document the gaps as recommendations — do not build them
- Be specific: cite file paths, test counts, and component names
- If the project has no tests at all, the report should clearly state that and recommend establishing testing infrastructure as a critical priority
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

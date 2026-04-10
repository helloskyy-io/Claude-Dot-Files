#!/usr/bin/env bash
#
# revision-major.sh — the REVISION-MAJOR workflow
# Significant rework of existing code — when PR comments aren't enough.
#
# This is the heavy revision workflow. It runs multiple stages through a
# single Claude session, invoking custom agents for review, testing, and
# refactoring evaluation before creating a PR.
#
# Stages:
#   1. ASSESS — analyze proposed fixes against existing implementation
#   2. PLAN — create a fix plan that meets original requirements
#   3. IMPLEMENT — engineer the changes, producing a deviation summary
#   4. TEST — run tests at all levels, report results
#   5. REVIEW — code review via code-reviewer agent, report findings
#   6. REFACTOR — refactoring evaluation via refactoring-evaluator agent
#   7. RESOLVE — engineer decides which review/refactor suggestions to apply
#   8. VERIFY — final test pass and summary
#   9. SUBMIT — commit, push, create/update PR with comprehensive summary
#
# Usage:
#   ./revision-major.sh "description of changes needed"
#   ./revision-major.sh "description of changes needed" --pr <pr-number>
#   ./revision-major.sh "description" --verbose
#
# Examples:
#   ./revision-major.sh "the auth flow needs to use sessions instead of JWT"
#   ./revision-major.sh "refactor the data access layer to use repository pattern"
#   ./revision-major.sh "address all code review findings from PR #5" --pr 5
#   ./revision-major.sh "restructure the API routes" --verbose
#
# Flags:
#   --pr <number>   Update an existing PR instead of creating a new one
#   --verbose, -v   Stream formatted Claude output live
#
# Logging:
#   Every run writes a structured JSONL log to .claude/logs/revision-major-<ts>.jsonl
#
# See docs/guide/dual_workflow_model.md for the full
# architectural context behind this workflow.
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
MAX_TURNS=75

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
if [[ $# -lt 1 ]]; then
    cat <<EOF
Usage: $(basename "$0") "description of changes needed" [options]

Options:
  --pr <number>   Update an existing PR instead of creating a new one
  --verbose, -v   Stream formatted Claude output live

Examples:
  $(basename "$0") "the auth flow needs to use sessions instead of JWT"
  $(basename "$0") "address all findings from PR #5" --pr 5
  $(basename "$0") "restructure the API routes" --verbose

This workflow is for SIGNIFICANT rework — not minor fixes.
For minor corrections, use revision.sh instead.
EOF
    exit 1
fi

DESCRIPTION="$1"
shift

PR_NUMBER=""
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --pr)
            if [[ $# -lt 2 ]]; then
                echo "Error: --pr requires a PR number" >&2
                exit 1
            fi
            PR_NUMBER="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Error: unknown option '$1'" >&2
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Environment checks
# ---------------------------------------------------------------------------
for cmd in claude gh jq; do
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
WORKTREE_NAME="revision-major-${TIMESTAMP}"

LOG_DIR="${REPO_ROOT}/.claude/logs"
LOG_FILE="${LOG_DIR}/revision-major-${TIMESTAMP}.jsonl"
mkdir -p "$LOG_DIR"

# ---------------------------------------------------------------------------
# Summary banner
# ---------------------------------------------------------------------------
echo "================================================================"
echo "  REVISION-MAJOR WORKFLOW"
echo "================================================================"
echo "  Description : ${DESCRIPTION}"
if [[ -n "$PR_NUMBER" ]]; then
    echo "  Target      : PR #${PR_NUMBER} (updating existing)"
else
    echo "  Target      : new branch and PR"
fi
echo "  Worktree    : ${WORKTREE_NAME}"
echo "  Max turns   : ${MAX_TURNS}"
echo "  Verbose     : ${VERBOSE}"
echo "  Log file    : ${LOG_FILE}"
echo "================================================================"
echo

# ---------------------------------------------------------------------------
# run_claude helper (from workflow-scripts standard)
# ---------------------------------------------------------------------------
run_claude() {
    local prompt="$1"
    shift
    local extra_args=("$@")

    local claude_cmd=(
        claude -p "$prompt"
        --output-format stream-json
        --verbose
        --max-turns "$MAX_TURNS"
        --dangerously-skip-permissions
        "${extra_args[@]}"
    )

    if $VERBOSE; then
        "${claude_cmd[@]}" \
            | tee "$LOG_FILE" \
            | "$FORMATTER"
    else
        "${claude_cmd[@]}" > "$LOG_FILE"

        jq -r 'select(.type == "result") |
            "Turns: \(.num_turns // "?") · Cost: $\(.total_cost_usd // 0) · Duration: \((.duration_ms // 0) / 1000)s\n\n\(.result // "Complete.")"' \
            "$LOG_FILE"
    fi
}

# ---------------------------------------------------------------------------
# Workflow execution
# ---------------------------------------------------------------------------
if [[ -n "$PR_NUMBER" ]]; then
    # ---- Existing PR path -------------------------------------------------
    echo "→ Fetching PR #${PR_NUMBER} metadata..."
    PR_BRANCH=$(gh pr view "$PR_NUMBER" --json headRefName --jq '.headRefName')
    if [[ -z "$PR_BRANCH" ]]; then
        echo "Error: could not determine branch for PR #${PR_NUMBER}" >&2
        exit 1
    fi
    echo "  Branch: ${PR_BRANCH}"

    WORKTREE_PATH=".claude/worktrees/${WORKTREE_NAME}"
    mkdir -p .claude/worktrees

    echo "→ Fetching latest PR branch state..."
    git fetch origin "$PR_BRANCH"

    echo "→ Creating worktree at ${WORKTREE_PATH}..."
    git worktree add -f "$WORKTREE_PATH" "origin/${PR_BRANCH}"

    PROMPT=$(cat <<EOF
You are executing the REVISION-MAJOR workflow on PR #${PR_NUMBER} (branch: ${PR_BRANCH}).

This is a SIGNIFICANT rework — not a minor fix. Follow all 9 stages thoroughly.

Task: ${DESCRIPTION}

## Stage 1: ASSESS
Analyze the existing implementation and the proposed changes. Read the relevant code. Understand what currently exists and what needs to change. Identify the scope of changes needed. Briefly describe your assessment before proceeding.

## Stage 2: PLAN
Create a focused plan for the changes. Reference existing requirements or documentation if available in docs/. Identify what files need to change, what the dependencies are between changes, and what risks exist. Keep the plan specific and actionable.

## Stage 3: IMPLEMENT
Execute the plan. Make the changes. Produce a brief summary noting:
- What was changed and why
- Any deviations from the plan and why they were necessary
- Files modified

## Stage 4: TEST
Run tests relevant to the changes.
- Run existing tests for affected code first
- If tests fail due to your changes, fix them
- If new functionality needs tests, add them
- Report test results clearly: what passed, what failed, what was added

## Stage 5: REVIEW
Use the code-reviewer agent to review your changes. Analyze the findings:
- Critical issues: must fix before proceeding
- Warnings: should fix if scope allows
- Info: note for future improvement

Fix any Critical issues found. Document which Warning and Info items you chose to address and which you deferred.

## Stage 6: REFACTOR
Use the refactoring-evaluator agent to evaluate the changed code for structural improvements. Analyze the findings:
- High priority: implement if scope allows
- Medium priority: implement if quick and low risk
- Low priority: defer to future work

Document which suggestions you implemented and which you deferred.

## Stage 7: RESOLVE
Review all changes made across stages 3-6. Produce a consolidated summary:
- Original task vs what was actually done
- Review findings addressed vs deferred
- Refactoring suggestions implemented vs deferred
- Any remaining concerns

## Stage 8: VERIFY
Run the full relevant test suite one final time to verify everything passes after all changes. If anything fails, fix it. Do not proceed to Stage 9 with failing tests.

## Stage 9: SUBMIT
- Stage and commit all changes with a clear message. Use format: "revision-major: <short description>"
- Push the branch (this updates PR #${PR_NUMBER})
- Report a summary of the entire workflow

Rules:
- Follow each stage in order — do not skip stages
- Be thorough — this is a major revision, not a quick fix
- Fix Critical review findings before submitting
- Tests must pass before committing
- Document deviations from the plan
- If you cannot complete a stage, stop and clearly report why
EOF
)

    echo
    echo "→ Launching Claude in revision-major mode (updating PR #${PR_NUMBER})..."
    echo

    (
        cd "$WORKTREE_PATH"
        run_claude "$PROMPT"
    )

else
    # ---- New revision path ------------------------------------------------
    PROMPT=$(cat <<EOF
You are executing the REVISION-MAJOR workflow on a new branch.

This is a SIGNIFICANT rework — not a minor fix. Follow all 9 stages thoroughly.

Task: ${DESCRIPTION}

## Stage 1: ASSESS
Analyze the existing implementation and the proposed changes. Read the relevant code. Understand what currently exists and what needs to change. Identify the scope of changes needed. Briefly describe your assessment before proceeding.

## Stage 2: PLAN
Create a focused plan for the changes. Reference existing requirements or documentation if available in docs/. Identify what files need to change, what the dependencies are between changes, and what risks exist. Keep the plan specific and actionable.

## Stage 3: IMPLEMENT
Execute the plan. Make the changes. Produce a brief summary noting:
- What was changed and why
- Any deviations from the plan and why they were necessary
- Files modified

## Stage 4: TEST
Run tests relevant to the changes.
- Run existing tests for affected code first
- If tests fail due to your changes, fix them
- If new functionality needs tests, add them
- Report test results clearly: what passed, what failed, what was added

## Stage 5: REVIEW
Use the code-reviewer agent to review your changes. Analyze the findings:
- Critical issues: must fix before proceeding
- Warnings: should fix if scope allows
- Info: note for future improvement

Fix any Critical issues found. Document which Warning and Info items you chose to address and which you deferred.

## Stage 6: REFACTOR
Use the refactoring-evaluator agent to evaluate the changed code for structural improvements. Analyze the findings:
- High priority: implement if scope allows
- Medium priority: implement if quick and low risk
- Low priority: defer to future work

Document which suggestions you implemented and which you deferred.

## Stage 7: RESOLVE
Review all changes made across stages 3-6. Produce a consolidated summary:
- Original task vs what was actually done
- Review findings addressed vs deferred
- Refactoring suggestions implemented vs deferred
- Any remaining concerns

## Stage 8: VERIFY
Run the full relevant test suite one final time to verify everything passes after all changes. If anything fails, fix it. Do not proceed to Stage 9 with failing tests.

## Stage 9: SUBMIT
- Stage and commit all changes with a clear message. Use format: "revision-major: <short description>"
- Push the branch
- Create a new PR using 'gh pr create'. Title format: "revision-major: <short description>". In the body, include:
  - Summary of what was changed
  - Deviations from plan (if any)
  - Review findings addressed and deferred
  - Refactoring suggestions implemented and deferred
  - Test results
- Report the PR URL

Rules:
- Follow each stage in order — do not skip stages
- Be thorough — this is a major revision, not a quick fix
- Fix Critical review findings before submitting
- Tests must pass before committing
- Document deviations from the plan
- If you cannot complete a stage, stop and clearly report why
EOF
)

    echo "→ Launching Claude in revision-major mode (new branch)..."
    echo

    run_claude "$PROMPT" -w "$WORKTREE_NAME"
fi

echo
echo "================================================================"
echo "  REVISION-MAJOR WORKFLOW COMPLETE"
echo "================================================================"
echo
echo "Worktree: .claude/worktrees/${WORKTREE_NAME}"
echo "Log file: ${LOG_FILE}"
echo
echo "To let Claude diagnose this run:"
echo "  claude 'read ${LOG_FILE} and tell me what happened'"
echo
echo "To clean up when done:"
echo "  /cleanup-merged-worktrees    (after PR is merged or closed)"
echo

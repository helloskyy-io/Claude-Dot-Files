#!/usr/bin/env bash
#
# build-phase.sh — the BUILD-PHASE workflow
# Architect and build a planned phase or feature from a plan document.
#
# This is the primary autonomous workflow for implementing a planned phase or
# feature. Unlike revision workflows that take a free-text description, this
# workflow takes a PATH to a plan document (phase doc, feature doc, or roadmap
# section) as its primary input. Claude reads the plan, extracts scope and
# success criteria, validates dependencies, then implements, tests, reviews,
# and submits a PR with a deviation summary comparing built vs planned.
#
# Stages:
#   1. LOAD PLAN — read the plan doc, extract scope and success criteria
#   2. VALIDATE — is the plan actionable? are dependencies met?
#   3. IMPLEMENT — build what the plan says
#   4. TEST — run/write tests
#   5. REVIEW — code review via code-reviewer agent
#   6. REFACTOR — refactoring evaluation via refactoring-evaluator agent
#   7. RESOLVE — decide which suggestions to apply
#   8. VERIFY — final tests + check success criteria from the plan
#   9. SUBMIT — commit, push, PR with deviation summary comparing built vs planned
#
# Usage:
#   ./build-phase.sh path/to/plan.md
#   ./build-phase.sh path/to/plan.md "additional context here"
#   ./build-phase.sh path/to/plan.md "additional context here" --verbose
#   ./build-phase.sh path/to/plan.md --pr <pr-number>
#
# Examples:
#   ./build-phase.sh docs/development/phase-4-autonomous.md
#   ./build-phase.sh docs/development/features/webhook-handler.md
#   ./build-phase.sh docs/development/features/webhook-handler.md "focus on error handling paths"
#   ./build-phase.sh docs/development/roadmap.md --verbose
#   ./build-phase.sh docs/development/phase-3.md "skip the optional metrics work" --pr 12
#
# Flags:
#   --pr <number>   Update an existing PR instead of creating a new one
#   --verbose, -v   Stream formatted Claude output live
#
# Logging:
#   Every run writes a structured JSONL log to .claude/logs/build-phase-<ts>.jsonl
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
MAX_TURNS=150

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
if [[ $# -lt 1 ]]; then
    cat <<EOF
Usage: $(basename "$0") path/to/plan.md ["context"] [options]

Arguments:
  path/to/plan.md   Path to the plan document (required)
  "context"         Additional context injected into the prompt (optional)

Options:
  --pr <number>   Update an existing PR instead of creating a new one
  --verbose, -v   Stream formatted Claude output live

Examples:
  $(basename "$0") docs/development/phase-4-autonomous.md
  $(basename "$0") docs/development/features/webhook-handler.md "focus on error handling paths"
  $(basename "$0") docs/development/phase-3.md --pr 12
  $(basename "$0") docs/development/roadmap.md "skip the optional metrics work" --verbose

This workflow reads a plan document and builds what it describes.
For corrections to existing code, use revision.sh or revision-major.sh instead.
EOF
    exit 1
fi

PLAN_PATH="$1"
shift

# Optional context argument: second positional arg if it doesn't start with -
CONTEXT=""
if [[ $# -gt 0 && ! "$1" =~ ^- ]]; then
    CONTEXT="$1"
    shift
fi

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
# Input validation
# ---------------------------------------------------------------------------
if [[ ! -f "$PLAN_PATH" ]]; then
    echo "Error: plan document not found: ${PLAN_PATH}" >&2
    exit 1
fi

if [[ ! -r "$PLAN_PATH" ]]; then
    echo "Error: plan document not readable: ${PLAN_PATH}" >&2
    exit 1
fi

# Resolve to absolute path before we cd to repo root
PLAN_PATH="$(cd "$(dirname "$PLAN_PATH")" && pwd)/$(basename "$PLAN_PATH")"

SAFE_PATH_RE='^[a-zA-Z0-9/_. -]+$'
if [[ ! "$PLAN_PATH" =~ $SAFE_PATH_RE ]]; then
    echo "Error: plan path contains unsupported characters: ${PLAN_PATH}" >&2
    exit 1
fi

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
WORKTREE_NAME="build-phase-${TIMESTAMP}"

LOG_DIR="${REPO_ROOT}/.claude/logs"
LOG_FILE="${LOG_DIR}/build-phase-${TIMESTAMP}.jsonl"
mkdir -p "$LOG_DIR"

# ---------------------------------------------------------------------------
# Summary banner
# ---------------------------------------------------------------------------
echo "================================================================"
echo "  BUILD-PHASE WORKFLOW"
echo "================================================================"
echo "  Plan file   : ${PLAN_PATH}"
if [[ -n "$CONTEXT" ]]; then
    echo "  Context     : ${CONTEXT}"
fi
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
# run_claude helper (shared library)
# ---------------------------------------------------------------------------
source "${SCRIPT_DIR}/lib/run-claude.sh"

# ---------------------------------------------------------------------------
# Context block (injected into prompt only when context is provided)
# ---------------------------------------------------------------------------
CONTEXT_BLOCK=""
if [[ -n "$CONTEXT" ]]; then
    CONTEXT_BLOCK="
--- additional context ---
${CONTEXT}
--- end additional context ---
"
fi

# ---------------------------------------------------------------------------
# Shared prompt stages (Stages 1-8 + Rules are identical for both paths)
# ---------------------------------------------------------------------------
STAGES_1_TO_8=$(cat <<'STAGES_EOF'
## Stage 1: LOAD PLAN
Read the plan document at the path above. Extract:
- The scope of work (what needs to be built)
- Success criteria (how to know it's done)
- Any dependencies or prerequisites mentioned
- Any constraints or non-goals mentioned

Summarize what you extracted before proceeding.

## Stage 2: VALIDATE
Evaluate whether the plan is actionable:
- Are the requirements clear enough to implement?
- Are dependencies met? (check if referenced files, APIs, or infrastructure exist)
- Are there any blockers that would prevent implementation?

If the plan is not actionable, stop and clearly report what's missing. Otherwise, proceed with a brief validation summary.

## Stage 3: IMPLEMENT
Build what the plan describes. Work through the scope methodically. Produce a brief summary noting:
- What was built and why
- Any deviations from the plan and why they were necessary
- Files created or modified

## Stage 4: TEST
Run and write tests for the implementation.
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
- Plan scope vs what was actually built
- Review findings addressed vs deferred
- Refactoring suggestions implemented vs deferred
- Any remaining concerns

## Stage 8: VERIFY
Run the full relevant test suite one final time to verify everything passes after all changes. Also verify against the success criteria extracted in Stage 1. If anything fails, fix it. Do not proceed to Stage 9 with failing tests or unmet success criteria.
STAGES_EOF
)

RULES=$(cat <<'RULES_EOF'
Rules:
- Follow each stage in order — do not skip stages
- Be thorough — this is a full build, not a quick fix
- Do not re-read files whose content you already know and haven't modified since you last read them
- Fix Critical review findings before submitting
- Tests must pass before committing
- Document deviations from the plan
- If you cannot complete a stage, stop and clearly report why
- Stay within the scope defined by the plan — do not add features not in the plan
RULES_EOF
)

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

    PROMPT="You are executing the BUILD-PHASE workflow on PR #${PR_NUMBER} (branch: ${PR_BRANCH}).

This workflow builds a planned phase or feature from a plan document. Follow all 9 stages thoroughly.

Plan document: ${PLAN_PATH}
${CONTEXT_BLOCK}
${STAGES_1_TO_8}

## Stage 9: SUBMIT
- Stage and commit all changes with a clear message. Use format: \"feat: <short description of what was built>\"
- Push the branch (this updates PR #${PR_NUMBER})
- Report a summary of the entire workflow including a deviation summary comparing what was planned vs what was built

${RULES}"

    echo
    echo "→ Launching Claude in build-phase mode (updating PR #${PR_NUMBER})..."
    echo

    (
        cd "$WORKTREE_PATH"
        run_claude "$PROMPT"
    )

else
    # ---- New branch path --------------------------------------------------
    PROMPT="You are executing the BUILD-PHASE workflow on a new branch.

This workflow builds a planned phase or feature from a plan document. Follow all 9 stages thoroughly.

Plan document: ${PLAN_PATH}
${CONTEXT_BLOCK}
${STAGES_1_TO_8}

## Stage 9: SUBMIT
- Stage and commit all changes with a clear message. Use format: \"feat: <short description of what was built>\"
- Push the branch
- Create a new PR using 'gh pr create'. Title format: \"build-phase: <short description>\". In the body, include:
  - Summary of what was built
  - Deviation summary: planned vs built (what matched, what diverged, what was deferred)
  - Review findings addressed and deferred
  - Refactoring suggestions implemented and deferred
  - Test results
  - Success criteria checklist (met / not met)
- Report the PR URL

${RULES}"

    echo "→ Launching Claude in build-phase mode (new branch)..."
    echo

    run_claude "$PROMPT" -w "$WORKTREE_NAME"
fi

echo
echo "================================================================"
echo "  BUILD-PHASE WORKFLOW COMPLETE"
echo "================================================================"
echo
echo "Worktree: .claude/worktrees/${WORKTREE_NAME}"
echo "Log file: ${LOG_FILE}"
echo
echo "To read the log in human-readable form:"
echo "  cat ${LOG_FILE} | ${FORMATTER}"
echo
echo "To let Claude diagnose this run:"
echo "  claude 'read ${LOG_FILE} and tell me what happened'"
echo
echo "To clean up when done:"
echo "  /cleanup-merged-worktrees    (after PR is merged or closed)"
echo

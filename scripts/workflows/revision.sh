#!/usr/bin/env bash
#
# revision.sh — the REVISION workflow
# Minor corrections and fixes to existing code.
#
# This is the lightest autonomous workflow in the dual-flow model. It:
#   1. Assesses what needs to change
#   2. Implements minimal, focused changes
#   3. Runs tests and fixes any failures
#   4. Commits, pushes, and either creates or updates a PR
#
# Usage:
#   ./revision.sh "description of what to revise"
#   ./revision.sh "description of what to revise" --pr <pr-number>
#
# Examples:
#   ./revision.sh "fix the null check in login()"
#   ./revision.sh "add error handling to the webhook handler"
#   ./revision.sh "correct the typo in the README header" --pr 42
#
# The first form creates a new branch and PR.
# The second form updates an existing PR by checking out its branch.
#
# See docs/official_documentation/dual_workflow_model.md for the full
# architectural context behind this workflow.

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MAX_TURNS=30

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
if [[ $# -lt 1 ]]; then
    cat <<EOF
Usage: $(basename "$0") "description of what to revise" [--pr <number>]

Examples:
  $(basename "$0") "fix the null check in login()"
  $(basename "$0") "add error handling" --pr 42

The first form creates a new branch and PR.
The second form updates an existing PR.
EOF
    exit 1
fi

DESCRIPTION="$1"
shift

PR_NUMBER=""
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
        *)
            echo "Error: unknown option '$1'" >&2
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Environment checks
# ---------------------------------------------------------------------------
if ! command -v claude &>/dev/null; then
    echo "Error: 'claude' CLI not found in PATH" >&2
    exit 1
fi

if ! command -v gh &>/dev/null; then
    echo "Error: 'gh' CLI not found in PATH" >&2
    exit 1
fi

if ! git rev-parse --show-toplevel &>/dev/null; then
    echo "Error: not inside a git repository" >&2
    exit 1
fi

# Always operate from the repo root so worktree paths are consistent
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# ---------------------------------------------------------------------------
# Worktree naming
# ---------------------------------------------------------------------------
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
WORKTREE_NAME="revision-${TIMESTAMP}"

# ---------------------------------------------------------------------------
# Summary banner
# ---------------------------------------------------------------------------
echo "================================================================"
echo "  REVISION WORKFLOW"
echo "================================================================"
echo "  Description : ${DESCRIPTION}"
if [[ -n "$PR_NUMBER" ]]; then
    echo "  Target      : PR #${PR_NUMBER} (updating existing)"
else
    echo "  Target      : new branch and PR"
fi
echo "  Worktree    : ${WORKTREE_NAME}"
echo "  Max turns   : ${MAX_TURNS}"
echo "================================================================"
echo

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
You are executing the REVISION workflow on PR #${PR_NUMBER} (branch: ${PR_BRANCH}).

Task: ${DESCRIPTION}

Follow these stages exactly:

1. ASSESS: Read the relevant files in the current directory to understand what needs to change. Focus only on the scope of the task. Do not explore unrelated code.

2. IMPLEMENT: Apply the fix. Make minimal, focused changes. Do not refactor or improve code outside the scope of the task.

3. TEST: Run any existing tests for the affected code. If tests fail because of your changes, fix them. If the task requires new tests, add them. Only run tests relevant to the changes — do not run the full test suite unless necessary.

4. COMMIT: Stage the changes and commit with a clear, focused message. Use format: "revision: <short description>"

5. PUSH: Push the branch. This will update PR #${PR_NUMBER} automatically.

Rules:
- Keep changes minimal and focused on the task
- Do not add features not requested
- Do not refactor unrelated code
- Always verify tests pass before committing
- If tests cannot be made to pass, stop and clearly report the failure
- At the end, report a one-paragraph summary of what was changed
EOF
)

    echo
    echo "→ Launching Claude in revision mode (updating PR #${PR_NUMBER})..."
    echo

    (
        cd "$WORKTREE_PATH"
        claude -p "$PROMPT" \
            --max-turns "$MAX_TURNS" \
            --dangerously-skip-permissions
    )

else
    # ---- New revision path ------------------------------------------------
    PROMPT=$(cat <<EOF
You are executing the REVISION workflow on a new branch.

Task: ${DESCRIPTION}

Follow these stages exactly:

1. ASSESS: Read the relevant files in the current directory to understand what needs to change. Focus only on the scope of the task. Do not explore unrelated code.

2. IMPLEMENT: Apply the fix. Make minimal, focused changes. Do not refactor or improve code outside the scope of the task.

3. TEST: Run any existing tests for the affected code. If tests fail because of your changes, fix them. If the task requires new tests, add them. Only run tests relevant to the changes — do not run the full test suite unless necessary.

4. COMMIT: Stage the changes and commit with a clear, focused message. Use format: "revision: <short description>"

5. PUSH: Push the branch to origin.

6. PR: Create a new PR using 'gh pr create'. Use title format: "revision: <short description>". In the body, describe what was changed and why. Report the PR URL at the end.

Rules:
- Keep changes minimal and focused on the task
- Do not add features not requested
- Do not refactor unrelated code
- Always verify tests pass before committing
- If tests cannot be made to pass, stop and clearly report the failure
- At the end, report the PR URL and a one-paragraph summary
EOF
)

    echo "→ Launching Claude in revision mode (new branch)..."
    echo

    claude -p "$PROMPT" \
        --max-turns "$MAX_TURNS" \
        --dangerously-skip-permissions \
        -w "$WORKTREE_NAME"
fi

echo
echo "================================================================"
echo "  REVISION WORKFLOW COMPLETE"
echo "================================================================"
echo
echo "Worktree: .claude/worktrees/${WORKTREE_NAME}"
echo
echo "To clean up when done:"
echo "  /cleanup-merged-worktrees    (after PR is merged or closed)"
echo

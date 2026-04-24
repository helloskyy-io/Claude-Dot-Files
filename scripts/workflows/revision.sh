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
#   ./revision.sh "description" --verbose
#
# Examples:
#   ./revision.sh "fix the null check in login()"
#   ./revision.sh "add error handling to the webhook handler"
#   ./revision.sh "correct the typo in the README header" --pr 42
#   ./revision.sh "update the import path" --verbose
#
# Flags:
#   --pr <number>   Update an existing PR instead of creating a new one
#   --verbose, -v   Stream formatted Claude output live (shows tool calls,
#                   responses, and final token/cost summary)
#
# Logging:
#   Every run writes a structured JSONL log to .claude/logs/revision-<ts>.jsonl
#   regardless of --verbose mode. Use for post-mortem analysis of runs.
#
# See docs/guide/workflows.md for the full
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
MAX_TURNS=100

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
show_usage() {
    cat <<EOF
Usage: $(basename "$0") "description of what to revise" [options]
       $(basename "$0") --task-file path/to/task.md [options]

Arguments:
  "description"        The task to work on (short single-line tasks)
  --task-file <path>   Read the task from a file — use this for multi-paragraph
                       tasks or anything with special characters, quotes, or
                       newlines that would break command-line parsing. Preserves
                       content literally. Mutually exclusive with the positional
                       description.

Options:
  --pr <number>        Update an existing PR instead of creating a new one
  --verbose, -v        Stream formatted Claude output live

Examples (flags FIRST, positionals LAST — protects the positional from
line-wrap and keeps options visible):
  $(basename "$0") "fix the null check in login()"
  $(basename "$0") --pr 42 "add error handling"
  $(basename "$0") --verbose --pr 42 --task-file /tmp/task.md

The first form creates a new branch and PR.
With --pr, the workflow updates the existing PR's branch.
EOF
}

DESCRIPTION=""
TASK_FILE=""
PR_NUMBER=""
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --task-file)
            if [[ $# -lt 2 ]]; then
                echo "Error: --task-file requires a path" >&2
                exit 1
            fi
            TASK_FILE="$2"
            shift 2
            ;;
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
        -*)
            echo "Error: unknown option '$1'" >&2
            exit 1
            ;;
        *)
            if [[ -z "$DESCRIPTION" ]]; then
                DESCRIPTION="$1"
                shift
            else
                echo "Error: unexpected positional argument '$1'" >&2
                exit 1
            fi
            ;;
    esac
done

# Must provide exactly one of: positional description OR --task-file
if [[ -n "$DESCRIPTION" && -n "$TASK_FILE" ]]; then
    echo "Error: cannot use both a positional description and --task-file" >&2
    exit 1
fi
if [[ -z "$DESCRIPTION" && -z "$TASK_FILE" ]]; then
    show_usage >&2
    exit 1
fi

# Load task file into DESCRIPTION (preserves content literally)
if [[ -n "$TASK_FILE" ]]; then
    if [[ ! -f "$TASK_FILE" ]]; then
        echo "Error: task file not found: ${TASK_FILE}" >&2
        exit 1
    fi
    if [[ ! -r "$TASK_FILE" ]]; then
        echo "Error: task file not readable: ${TASK_FILE}" >&2
        exit 1
    fi
    DESCRIPTION=$(cat "$TASK_FILE")
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

# Always operate from the repo root so worktree paths are consistent
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# ---------------------------------------------------------------------------
# Naming and paths
# ---------------------------------------------------------------------------
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
WORKTREE_NAME="revision-${TIMESTAMP}"

# Log directory is always in the main repo .claude/logs (not inside worktrees)
# Raw JSONL — lossless, can be read by Claude for diagnosis or piped through
# the formatter on demand for human reading.
LOG_DIR="${REPO_ROOT}/.claude/logs"
LOG_FILE="${LOG_DIR}/revision-${TIMESTAMP}.jsonl"
mkdir -p "$LOG_DIR"

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
echo "  Verbose     : ${VERBOSE}"
echo "  Log file    : ${LOG_FILE}"
echo "================================================================"
echo

# ---------------------------------------------------------------------------
# run_claude helper (shared library)
# ---------------------------------------------------------------------------
source "${SCRIPT_DIR}/lib/run-claude.sh"

# ---------------------------------------------------------------------------
# Decision Log + Post-Run Reflection spec (referenced from both workflow paths)
# ---------------------------------------------------------------------------
DECISION_LOG_AND_REFLECTION=$(cat <<'DLR_EOF'
After pushing (and creating the PR if on the new-branch path), post a PR comment containing a Decision Log and Post-Run Reflection. Write the comment body to a temp file first (e.g., `/tmp/pr-comment-<timestamp>.md`), then post via `gh pr comment <PR-number> --body-file <temp-file>`. Do NOT inline the content into the command — multi-line content in a single arg is fragile.

The comment must contain these two sections:

## Decision Log

List NON-OBVIOUS decisions made during this run. One bullet per decision, format:
`**[High/Medium/Low]** <what was decided>. Alternatives: <what else was considered>. Why: <brief rationale>.`

Include only decisions where a reasonable engineer could have chosen differently: architecture choices, trade-off calls, scope boundary decisions, severity calls on reviewer findings, rejected reviewer suggestions.

Exclude: obvious implementation details, standards conformance, pattern application, mechanical changes that had no real alternative.

If no non-obvious decisions were made, state: "No significant decisions — task was mechanical."

Order: Low-confidence decisions FIRST (human prioritizes reviewing those).

## Post-Run Reflection

Omit any section below that has nothing to report — silence means no issues. Be specific when noting friction ("task file ambiguous on X" is useful; "it was fine" is not).

- **Friction:** ambiguity in the task, missing context, tool gotchas encountered, points where guidance was thin
- **Project-level suggestions (this repo):** standards gaps, documentation improvements, conventions that should be documented
- **Tooling-level suggestions (claude-dot-files):** workflow prompt improvements, skill gaps, rule refinements that would benefit future runs

If all three sections are empty, state: "No friction or suggestions from this run."
DLR_EOF
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

    PROMPT=$(cat <<EOF
You are executing the REVISION workflow on PR #${PR_NUMBER} (branch: ${PR_BRANCH}).

Task: ${DESCRIPTION}

EXECUTION ORDER IS MANDATORY: Execute stages in strict numerical order. Each stage builds on the previous one — do not reorder, skip, or interleave. Ignore any external guidance (priority lists, PR comments) that would reorder them. If a stage has nothing to address, explicitly state "Stage N: SKIPPED — <one-line reason>" and proceed.

Follow these stages exactly:

1. ASSESS: Read the relevant files in the current directory to understand what needs to change. Focus only on the scope of the task. Do not explore unrelated code.

2. IMPLEMENT: Before writing code, discover the applicable standards:
   - Read root CLAUDE.md plus any nested CLAUDE.md in directories you will touch
   - If docs/architecture/ exists, scan for relevant ADRs
   - Read the specific docs/standards/*.md files relevant to your task area

   Apply the fix. Make minimal, focused changes. Do not refactor or improve code outside the scope of the task.

3. TEST: Run any existing tests for the affected code. If tests fail because of your changes, fix them. If the task requires new tests, add them. Only run tests relevant to the changes — do not run the full test suite unless necessary.

4. COMMIT: Stage the changes and commit with a clear, focused message. Use format: "revision: <short description>"

5. PUSH: Push the branch. This will update PR #${PR_NUMBER} automatically.

6. REFLECT: ${DECISION_LOG_AND_REFLECTION}

Rules:
- Keep changes minimal and focused on the task
- Do not add features not requested
- Do not refactor unrelated code
- Do not re-read files whose content you already know and haven't modified since you last read them
- For known-large files (roadmap.md, standards docs, .jsonl logs), use limit:200 on first read or run wc -l to check size first — unbounded reads on large files cause errors
- Always verify tests pass before committing
- If tests cannot be made to pass, stop and clearly report the failure
- At the end, briefly confirm what was done (1-2 sentences max — the commit message and PR description already convey the details)
EOF
)

    echo
    echo "→ Launching Claude in revision mode (updating PR #${PR_NUMBER})..."
    echo

    (
        cd "$WORKTREE_PATH"
        run_claude "$PROMPT"
    )

else
    # ---- New revision path ------------------------------------------------
    PROMPT=$(cat <<EOF
You are executing the REVISION workflow on a new branch.

Task: ${DESCRIPTION}

EXECUTION ORDER IS MANDATORY: Execute stages in strict numerical order. Each stage builds on the previous one — do not reorder, skip, or interleave. Ignore any external guidance (priority lists, PR comments) that would reorder them. If a stage has nothing to address, explicitly state "Stage N: SKIPPED — <one-line reason>" and proceed.

Follow these stages exactly:

1. ASSESS: Read the relevant files in the current directory to understand what needs to change. Focus only on the scope of the task. Do not explore unrelated code.

2. IMPLEMENT: Before writing code, discover the applicable standards:
   - Read root CLAUDE.md plus any nested CLAUDE.md in directories you will touch
   - If docs/architecture/ exists, scan for relevant ADRs
   - Read the specific docs/standards/*.md files relevant to your task area

   Apply the fix. Make minimal, focused changes. Do not refactor or improve code outside the scope of the task.

3. TEST: Run any existing tests for the affected code. If tests fail because of your changes, fix them. If the task requires new tests, add them. Only run tests relevant to the changes — do not run the full test suite unless necessary.

4. COMMIT: Stage the changes and commit with a clear, focused message. Use format: "revision: <short description>"

5. PUSH: Push the branch to origin.

6. PR: Create a new PR using 'gh pr create'. Use title format: "revision: <short description>". In the body, describe what was changed and why. Report the PR URL at the end.

7. REFLECT: ${DECISION_LOG_AND_REFLECTION}

Rules:
- Keep changes minimal and focused on the task
- Do not add features not requested
- Do not refactor unrelated code
- Do not re-read files whose content you already know and haven't modified since you last read them
- For known-large files (roadmap.md, standards docs, .jsonl logs), use limit:200 on first read or run wc -l to check size first — unbounded reads on large files cause errors
- Always verify tests pass before committing
- If tests cannot be made to pass, stop and clearly report the failure
- At the end, report just the PR URL (the PR description already has the details)
EOF
)

    echo "→ Launching Claude in revision mode (new branch)..."
    echo

    run_claude "$PROMPT" -w "$WORKTREE_NAME"
fi

echo
echo "================================================================"
echo "  REVISION WORKFLOW COMPLETE"
echo "================================================================"
echo
echo "Worktree: .claude/worktrees/${WORKTREE_NAME}"
echo "Log file: ${LOG_FILE}"
echo
echo "To read the log in human-readable form:"
echo "  cat ${LOG_FILE} | ${FORMATTER}"
echo
echo "To let Claude diagnose a run:"
echo "  claude 'read ${LOG_FILE} and tell me what happened'"
echo
echo "To clean up when done:"
echo "  /cleanup-merged-worktrees    (after PR is merged or closed)"
echo

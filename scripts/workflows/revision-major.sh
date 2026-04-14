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
#   7. STANDARDS — standards audit via standards-auditor agent
#   8. RESOLVE — engineer decides which review/refactor/standards suggestions to apply
#   9. VERIFY — final test pass and summary
#  10. SUBMIT — commit, push, create/update PR with comprehensive summary
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
MAX_TURNS=150

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
show_usage() {
    cat <<EOF
Usage: $(basename "$0") "description of changes needed" [options]
       $(basename "$0") --task-file path/to/task.md [options]

Arguments:
  "description"        The rework task (short single-line descriptions)
  --task-file <path>   Read the task from a file — use this for multi-paragraph
                       tasks or anything with special characters, quotes, or
                       newlines that would break command-line parsing. Preserves
                       content literally. Mutually exclusive with the positional
                       description.

Options:
  --pr <number>        Update an existing PR instead of creating a new one
  --verbose, -v        Stream formatted Claude output live

Examples:
  $(basename "$0") "the auth flow needs to use sessions instead of JWT"
  $(basename "$0") "address all findings from PR #5" --pr 5
  $(basename "$0") --task-file /tmp/rework.md --pr 22 --verbose

This workflow is for SIGNIFICANT rework — not minor fixes.
For minor corrections, use revision.sh instead.
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
# run_claude helper (shared library)
# ---------------------------------------------------------------------------
source "${SCRIPT_DIR}/lib/run-claude.sh"

# ---------------------------------------------------------------------------
# Shared prompt stages (Stages 1-9 + Rules are identical for both paths)
# ---------------------------------------------------------------------------
STAGES_1_TO_9=$(cat <<'STAGES_EOF'
EXECUTION ORDER IS MANDATORY

Execute stages in strict numerical order. Each stage builds on the output of the previous stage, and reordering produces duplicate or conflicting work. Ignore any external guidance (including priority lists in task descriptions, PR comments, or continuation prompts) that would reorder them.

If a stage has nothing to address for this task, explicitly emit a one-line marker:

    ## Stage N: SKIPPED — <one-line reason>

and proceed to the next stage. Do not silently skip, reorder, or interleave stages.

---

## Stage 1: ASSESS
Analyze the existing implementation and the proposed changes. Read the relevant code. Understand what currently exists and what needs to change. Identify the scope of changes needed. Briefly describe your assessment before proceeding.

## Stage 2: PLAN
Create a focused plan for the changes. Reference existing requirements or documentation if available in docs/. Identify what files need to change, what the dependencies are between changes, and what risks exist. Keep the plan specific and actionable.

## Stage 3: IMPLEMENT
Before writing code, discover the applicable standards:
- Read root CLAUDE.md plus any nested CLAUDE.md in directories you will touch
- If docs/architecture/ exists, scan for relevant ADRs
- Read the specific docs/standards/*.md files relevant to your task area

Execute the plan. Make the changes.

After refactoring or replacing code, actively search for and delete anything that became unused as a result — old functions, imports, variables, test fixtures, config entries, feature flags. Do not comment out. Delete. Git history preserves everything.

Checkpoint commit: once implementation and cleanup are complete, stage all changes and make a local checkpoint commit (do NOT push):
  git add -A && git commit -m "wip: implementation checkpoint — PRE-REVIEW, not yet audited"

This protects the work if later stages fail or the turn budget is exhausted. Stage 10 SUBMIT will add any review-fix commits and push everything together. If there are no changes to commit, skip and note why in the summary.

Produce a brief summary noting:
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

## Stage 7: STANDARDS
Use the standards-auditor agent to audit your changes against project standards. Analyze the findings:
- Critical violations: must fix before proceeding
- Warnings: should fix if scope allows
- Info: note for future improvement

Fix any Critical violations found. Document which Warning and Info items you chose to address and which you deferred.

## Stage 8: RESOLVE
Review all changes made across stages 3-7. Produce a consolidated summary:
- Original task vs what was actually done
- Review findings addressed vs deferred
- Refactoring suggestions implemented vs deferred
- Standards audit findings addressed vs deferred
- Any remaining concerns

## Stage 9: VERIFY
Run the full relevant test suite one final time to verify everything passes after all changes. If anything fails, fix it. Do not proceed to Stage 10 with failing tests.
STAGES_EOF
)

RULES=$(cat <<'RULES_EOF'
Rules:
- Follow each stage in order — do not skip stages
- Be thorough — this is a major revision, not a quick fix
- Do not re-read files whose content you already know and haven't modified since you last read them
- For known-large files (roadmap.md, standards docs, .jsonl logs), use limit:200 on first read or run wc -l to check size first — unbounded reads on large files cause errors
- Fix Critical review findings before submitting
- Tests must pass before committing
- Document deviations from the plan
- If you cannot complete a stage, stop and clearly report why
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

    PROMPT="You are executing the REVISION-MAJOR workflow on PR #${PR_NUMBER} (branch: ${PR_BRANCH}).

This is a SIGNIFICANT rework — not a minor fix. Follow all 10 stages thoroughly.

Task: ${DESCRIPTION}

${STAGES_1_TO_9}

## Stage 10: SUBMIT
- Stage any uncommitted changes remaining from stages 5-9 (review fixes, refactors, standards fixes) and commit them with the final message format: \"revision-major: <short description>\". If everything was already captured by the Stage 3 checkpoint and no review fixes were needed, skip this commit — the checkpoint is enough and the PR body carries the real summary.
- Push the branch (this updates PR #${PR_NUMBER})
- Report a summary of the entire workflow

${RULES}"

    echo
    echo "→ Launching Claude in revision-major mode (updating PR #${PR_NUMBER})..."
    echo

    (
        cd "$WORKTREE_PATH"
        run_claude "$PROMPT"
    )

else
    # ---- New revision path ------------------------------------------------
    PROMPT="You are executing the REVISION-MAJOR workflow on a new branch.

This is a SIGNIFICANT rework — not a minor fix. Follow all 10 stages thoroughly.

Task: ${DESCRIPTION}

${STAGES_1_TO_9}

## Stage 10: SUBMIT
- Stage any uncommitted changes remaining from stages 5-9 (review fixes, refactors, standards fixes) and commit them with the final message format: \"revision-major: <short description>\". If everything was already captured by the Stage 3 checkpoint and no review fixes were needed, skip this commit — the checkpoint is enough and the PR body carries the real summary.
- Push the branch
- Create a new PR using 'gh pr create'. Title format: \"revision-major: <short description>\". In the body, include:
  - Summary of what was changed
  - Deviations from plan (if any)
  - Review findings addressed and deferred
  - Refactoring suggestions implemented and deferred
  - Standards audit findings addressed and deferred
  - Test results
- Report the PR URL

${RULES}"

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

#!/usr/bin/env bash
#
# review-runs.sh — the REVIEW-RUNS workflow
# Analyzes recent workflow logs and produces a structured improvement report.
#
# This is the continuous process improvement (CPI) workflow. It:
#   1. Scans .claude/logs/ for recent JSONL logs
#   2. Invokes Claude with the workflow-analysis methodology to analyze them
#   3. Produces a report at docs/development/reviews/review-YYYY-MM-DD.md
#
# Usage:
#   ./review-runs.sh
#   ./review-runs.sh --days 14
#   ./review-runs.sh --last 5
#   ./review-runs.sh --verbose
#
# Examples:
#   ./review-runs.sh                     # analyze logs from the last 7 days
#   ./review-runs.sh --days 30           # analyze logs from the last 30 days
#   ./review-runs.sh --last 10           # analyze the 10 most recent logs
#   ./review-runs.sh --days 7 --verbose  # with live streaming
#
# Flags:
#   --days <N>      Analyze logs from the last N days (default: 7)
#   --last <N>      Analyze the N most recent log files (mutually exclusive with --days)
#   --verbose, -v   Stream formatted Claude output live
#
# Logging:
#   Every run writes a structured JSONL log to .claude/logs/review-runs-<ts>.jsonl
#
# See docs/development/roadmap.md Phase 5a for the design context.
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
MAX_TURNS=30

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
DAYS=""
LAST=""
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --days)
            if [[ -n "$LAST" ]]; then
                echo "Error: --days and --last are mutually exclusive" >&2
                exit 1
            fi
            if [[ $# -lt 2 ]]; then
                echo "Error: --days requires a number" >&2
                exit 1
            fi
            DAYS="$2"
            if ! [[ "$DAYS" =~ ^[0-9]+$ ]] || [[ "$DAYS" -eq 0 ]]; then
                echo "Error: --days requires a positive integer" >&2
                exit 1
            fi
            shift 2
            ;;
        --last)
            if [[ -n "$DAYS" ]]; then
                echo "Error: --days and --last are mutually exclusive" >&2
                exit 1
            fi
            if [[ $# -lt 2 ]]; then
                echo "Error: --last requires a number" >&2
                exit 1
            fi
            LAST="$2"
            if ! [[ "$LAST" =~ ^[0-9]+$ ]] || [[ "$LAST" -eq 0 ]]; then
                echo "Error: --last requires a positive integer" >&2
                exit 1
            fi
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            cat <<EOF
Usage: $(basename "$0") [options]

Analyzes recent workflow logs and produces a structured improvement report.

Options:
  --days <N>      Analyze logs from the last N days (default: 7)
  --last <N>      Analyze the N most recent log files
  --verbose, -v   Stream formatted Claude output live
  --help, -h      Show this help message

Examples:
  $(basename "$0")                     # last 7 days of logs
  $(basename "$0") --days 30           # last 30 days
  $(basename "$0") --last 10           # 10 most recent logs
  $(basename "$0") --days 7 --verbose  # with live streaming
EOF
            exit 0
            ;;
        *)
            echo "Error: unknown option '$1'" >&2
            exit 1
            ;;
    esac
done

# Default to 7 days if neither --days nor --last specified
if [[ -z "$DAYS" && -z "$LAST" ]]; then
    DAYS=7
fi

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

# Find the main repo root (not the worktree) for log access.
# Logs always live in the main repo's .claude/logs/ per workflow-scripts standard.
# --git-common-dir returns ".git" (relative) in the main repo, absolute path in worktrees.
GIT_COMMON_DIR="$(git rev-parse --git-common-dir)"
if [[ "$GIT_COMMON_DIR" == ".git" ]]; then
    MAIN_REPO_ROOT="$REPO_ROOT"
else
    MAIN_REPO_ROOT="$(dirname "$GIT_COMMON_DIR")"
fi

# ---------------------------------------------------------------------------
# Scan for log files
# ---------------------------------------------------------------------------
SCAN_LOG_DIR="${MAIN_REPO_ROOT}/.claude/logs"

if [[ ! -d "$SCAN_LOG_DIR" ]]; then
    echo "Error: log directory not found at ${SCAN_LOG_DIR}" >&2
    echo "No workflow runs have been logged yet." >&2
    exit 1
fi

# Build the list of log files to analyze
# NOTE: -printf is GNU find only; not portable to BSD/macOS
LOG_FILES=()

if [[ -n "$LAST" ]]; then
    # Most recent N log files by modification time
    while IFS= read -r file; do
        LOG_FILES+=("$file")
    done < <(find "$SCAN_LOG_DIR" -maxdepth 1 -name '*.jsonl' -type f -printf '%T@ %p\n' \
        | sort -rn | head -n "$LAST" | awk '{print $2}')
else
    # Log files modified within the last N days
    while IFS= read -r file; do
        LOG_FILES+=("$file")
    done < <(find "$SCAN_LOG_DIR" -maxdepth 1 -name '*.jsonl' -type f -mtime "-${DAYS}" -printf '%T@ %p\n' \
        | sort -rn | awk '{print $2}')
fi

if [[ ${#LOG_FILES[@]} -eq 0 ]]; then
    if [[ -n "$LAST" ]]; then
        echo "No log files found in ${SCAN_LOG_DIR}."
    else
        echo "No log files found in the last ${DAYS} days in ${SCAN_LOG_DIR}."
    fi
    echo "Run some workflows first to generate logs."
    exit 0
fi

# ---------------------------------------------------------------------------
# Naming and paths
# ---------------------------------------------------------------------------
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
TODAY=$(date +%Y-%m-%d)
REPORT_DIR="${REPO_ROOT}/docs/development/reviews"
REPORT_FILE="${REPORT_DIR}/review-${TODAY}.md"

# Log for THIS run (the review workflow itself) — always in main repo
LOG_DIR="${MAIN_REPO_ROOT}/.claude/logs"
LOG_FILE="${LOG_DIR}/review-runs-${TIMESTAMP}.jsonl"
mkdir -p "$LOG_DIR"
mkdir -p "$REPORT_DIR"

# Build file lists for display and prompt (single loop, literal newlines)
FILE_LIST=""
PROMPT_FILE_LIST=""
for f in "${LOG_FILES[@]}"; do
    FILE_LIST="${FILE_LIST}  - ${f}
"
    PROMPT_FILE_LIST="${PROMPT_FILE_LIST}- ${f}
"
done

# ---------------------------------------------------------------------------
# Summary banner
# ---------------------------------------------------------------------------
echo "================================================================"
echo "  REVIEW-RUNS WORKFLOW"
echo "================================================================"
if [[ -n "$LAST" ]]; then
    echo "  Filter      : last ${LAST} log files"
else
    echo "  Filter      : last ${DAYS} days"
fi
echo "  Logs found  : ${#LOG_FILES[@]}"
echo "  Report      : ${REPORT_FILE}"
echo "  Max turns   : ${MAX_TURNS}"
echo "  Verbose     : ${VERBOSE}"
echo "  Log file    : ${LOG_FILE}"
echo "================================================================"
echo
echo "Log files to analyze:"
printf "%s" "$FILE_LIST"
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
# Workflow execution — no worktree needed (read-only analysis)
# ---------------------------------------------------------------------------
PROMPT=$(cat <<EOF
You are executing the REVIEW-RUNS workflow.

Your task is to analyze recent workflow logs and produce a structured improvement report.

## Log Files to Analyze

${PROMPT_FILE_LIST}

## Instructions

1. GATHER: Read each of the log files listed above. For very large logs, focus on the result events, tool call patterns, and any error events. Use the Grep tool to extract key events efficiently rather than reading entire files if they are large.

2. ANALYZE: Use the workflow-analysis skill methodology to analyze the logs. Look for:
   - Inefficiencies (unnecessary tool calls, redundant reads, scope creep)
   - Repeated failures (same errors across runs)
   - Manual corrections (user overrides, feedback patterns)
   - Missed opportunities (parallelization, better tool usage)
   - Successes worth preserving (approaches that worked well)

3. SCORE: Rate each finding using the confidence scoring system:
   - High: pattern in 3+ runs, clear cause-effect
   - Medium: pattern in 2 runs, or strong single observation
   - Low: single observation, possible coincidence

4. REPORT: Write the report to: ${REPORT_FILE}

   Use the structured format from the workflow-analyst agent:
   - Runs Analyzed (count, date range, workflow types)
   - High-Confidence Findings (with evidence, recommendation, impact)
   - Medium-Confidence Findings (with evidence, recommendation, needs)
   - Low-Confidence Findings (with watch-for notes)
   - Patterns Resolved Since Last Review (if prior reviews exist in docs/development/reviews/)
   - Metrics (average turns, token usage, failure types, trends)
   - Summary (2-3 sentences: health, top priority, trend)

5. CONFIRM: After writing the report, confirm the file was written and provide a 2-3 sentence summary of the key findings.

## Rules

- Read-only analysis of logs — do not modify any workflow scripts, agents, or skills
- The ONLY file you should write is the report at ${REPORT_FILE}
- Cite specific log evidence for every finding
- If the logs look clean, say so — don't invent problems
- Always disclose sample size and confidence level
- If prior reviews exist in docs/development/reviews/, check them for resolved patterns
- Focus on patterns, not one-off anomalies (unless severe)
EOF
)

echo "→ Launching Claude in review-runs mode..."
echo

run_claude "$PROMPT"

echo
echo "================================================================"
echo "  REVIEW-RUNS WORKFLOW COMPLETE"
echo "================================================================"
echo
echo "Report: ${REPORT_FILE}"
echo "Log file: ${LOG_FILE}"
echo
echo "To read the log in human-readable form:"
echo "  cat ${LOG_FILE} | ${FORMATTER}"
echo
echo "To let Claude diagnose this run:"
echo "  claude 'read ${LOG_FILE} and tell me what happened'"
echo

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

# Resolve the claude-dot-files repo root by walking up from the script's location.
# Reports are written here regardless of which repo's logs are being analyzed,
# so they accumulate in a single searchable location instead of scattering
# across every analyzed repo. Works on any machine regardless of install path.
CLAUDE_DOT_FILES_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MAX_TURNS=100

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

Run this from INSIDE the repo whose logs you want to analyze. Logs are stored
per-repo at <repo>/.claude/logs/ — each repo accumulates its own workflow
history. The report is written to <repo>/docs/development/reviews/.

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
    cat >&2 <<EOF
Error: no log directory found at ${SCAN_LOG_DIR}

Logs are stored per-repo at <repo>/.claude/logs/ — each repo accumulates its
own workflow history. This repo has no autonomous workflow runs logged.

If your production workflow runs happened in a different repo, cd into that
repo and run this script from there:

  cd /path/to/target-repo && $(basename "$0") --last 20

To see which repos have logs on this machine:
  for d in ~/Repos/*/ /opt/*/*/; do
    [ -d "\${d}.claude/logs" ] && echo "\$(basename \$d): \$(ls -1 \${d}.claude/logs/*.jsonl 2>/dev/null | wc -l) logs"
  done
EOF
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

# Source context: which repo and machine does this analysis come from?
# Used in the report filename AND in the report's metadata header so that
# a reader can always tell which repo's workflow history produced each review.
SOURCE_REPO_NAME="$(basename "$MAIN_REPO_ROOT")"
SOURCE_MACHINE="$(hostname -s)"

# Reports always go to claude-dot-files/docs/development/reviews/ — single
# searchable location across all analyzed repos and machines. Filename
# includes the source repo so reports never collide.
REPORT_DIR="${CLAUDE_DOT_FILES_ROOT}/docs/development/reviews"
REPORT_FILE="${REPORT_DIR}/review-${SOURCE_REPO_NAME}-${TODAY}.md"

# Log for THIS run (the review workflow itself) stays with the analyzed repo's
# logs — it's part of that repo's workflow history, consistent with how every
# other workflow logs to its target repo.
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
echo "  Source repo : ${SOURCE_REPO_NAME} (${MAIN_REPO_ROOT})"
echo "  Machine     : ${SOURCE_MACHINE}"
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
# run_claude helper (shared library)
# ---------------------------------------------------------------------------
source "${SCRIPT_DIR}/lib/run-claude.sh"

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

   Start the report with a metadata header immediately after the title, so a
   reader can always tell which repo and machine this analysis came from:

   \`\`\`
   # Workflow Review — ${SOURCE_REPO_NAME} — ${TODAY}

   **Source repo:** \`${MAIN_REPO_ROOT}\`
   **Source machine:** \`${SOURCE_MACHINE}\`
   **Analysis date:** ${TODAY}
   **Logs analyzed:** (count and date range, filled in below)
   \`\`\`

   Then use the structured format from the workflow-analyst agent:
   - Runs Analyzed (count, date range, workflow types)
   - High-Confidence Findings (with evidence, recommendation, impact)
   - Medium-Confidence Findings (with evidence, recommendation, needs)
   - Low-Confidence Findings (with watch-for notes)
   - Patterns Resolved Since Last Review (look for prior reviews matching \`review-${SOURCE_REPO_NAME}-*.md\` in the same directory — compare only against reviews of THIS repo)
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
- For known-large files (roadmap.md, standards docs, .jsonl logs), use limit:200 on first read or run wc -l to check size first — unbounded reads on large files cause errors
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

# run-claude.sh — shared run_claude helper for workflow scripts
#
# Source this file from any workflow script to get the standard run_claude
# function. This avoids duplicating the verbose/quiet invocation logic across
# every workflow.
#
# Required environment variables (must be set before sourcing):
#   LOG_FILE    — path to the JSONL log file for this run
#   MAX_TURNS   — maximum conversation turns for claude
#   VERBOSE     — "true" or "false" for live streaming
#   FORMATTER   — path to the format-stream.sh formatter script
#
# Usage in a workflow script:
#   source "${SCRIPT_DIR}/lib/run-claude.sh"
#   run_claude "$PROMPT" -w "$WORKTREE_NAME"

# Guard: verify required variables are set
: "${LOG_FILE:?run-claude.sh: LOG_FILE must be set before sourcing}"
: "${MAX_TURNS:?run-claude.sh: MAX_TURNS must be set before sourcing}"
: "${VERBOSE:?run-claude.sh: VERBOSE must be set before sourcing}"
: "${FORMATTER:?run-claude.sh: FORMATTER must be set before sourcing}"

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

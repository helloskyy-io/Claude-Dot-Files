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
#   MODEL_KEY   — this workflow's key in config.yaml's `models:` map
#
# Optional environment variables:
#   MODEL_OVERRIDE     — bypass the config.yaml map for this dispatch (A/B runs):
#                        MODEL_OVERRIDE=sonnet ./children/build-draft.sh "task"
#   COMPLETION_PATTERN — an ERE the final result MUST contain for the run to
#                        count as complete. Missing → run_claude fails LOUD and
#                        returns nonzero (exit 0 must mean done). PR-producing
#                        workflows set this to a PR-URL pattern. Unset = no check.
#
# Usage in a workflow script:
#   MODEL_KEY="build-draft"
#   source "${SCRIPT_DIR}/activities/run-claude.sh"
#   run_claude "$PROMPT" -w "$WORKTREE_NAME"

# Guard: verify required variables are set
: "${LOG_FILE:?run-claude.sh: LOG_FILE must be set before sourcing}"
: "${MAX_TURNS:?run-claude.sh: MAX_TURNS must be set before sourcing}"
: "${VERBOSE:?run-claude.sh: VERBOSE must be set before sourcing}"
: "${FORMATTER:?run-claude.sh: FORMATTER must be set before sourcing}"
: "${MODEL_KEY:?run-claude.sh: MODEL_KEY must be set before sourcing (key into config.yaml models: map)}"

# ---------------------------------------------------------------------------
# Model resolution
# Every dispatch runs with an EXPLICIT --model. Headless runs otherwise
# inherit ambient defaults (the dispatching PM session's model — the
# mixed-results incident), and model identity must be an explicit input,
# never derived (Temporal Standard §7.5 principle). Resolution order:
#   1. MODEL_OVERRIDE env var (per-dispatch A/B override)
#   2. config.yaml `models: <MODEL_KEY>` (single authority)
#   3. FAIL LOUD — never dispatch on an inherited default
# ---------------------------------------------------------------------------
if ! command -v yq &>/dev/null; then
    echo "Error: 'yq' is required for model resolution (config.yaml models map) but not found in PATH" >&2
    exit 1
fi

_CDF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
_MODELS_CONFIG="${_CDF_ROOT}/config.yaml"

if [[ -n "${MODEL_OVERRIDE:-}" ]]; then
    WORKFLOW_MODEL="$MODEL_OVERRIDE"
    echo "→ Model: ${WORKFLOW_MODEL} (MODEL_OVERRIDE — bypassing config.yaml)"
else
    if [[ ! -f "$_MODELS_CONFIG" ]]; then
        echo "Error: config.yaml not found at ${_MODELS_CONFIG} — cannot resolve model for '${MODEL_KEY}'" >&2
        exit 1
    fi
    WORKFLOW_MODEL="$(yq -r ".models.\"${MODEL_KEY}\" // \"\"" "$_MODELS_CONFIG")"
    if [[ -z "$WORKFLOW_MODEL" || "$WORKFLOW_MODEL" == "null" ]]; then
        echo "Error: no model configured for '${MODEL_KEY}' in ${_MODELS_CONFIG} (models: section)." >&2
        echo "Refusing to dispatch on an inherited default — add the key or set MODEL_OVERRIDE." >&2
        exit 1
    fi
    echo "→ Model: ${WORKFLOW_MODEL} (config.yaml models.${MODEL_KEY})"
fi

# ---------------------------------------------------------------------------
# Pre-run rate limit check
# Sends a minimal probe request to detect rate limiting before the real run.
# On non-zero exit, checks stderr for rate-limit signals. Non-rate-limit
# errors are passed through to let the real run surface them.
# ---------------------------------------------------------------------------
check_rate_limit() {
    local max_attempts=3
    local wait_seconds=30
    local attempt=1

    while (( attempt <= max_attempts )); do
        local probe_stderr
        probe_stderr=$(claude -p "ping" --max-turns 1 --output-format text 2>&1 >/dev/null) && return 0

        if echo "$probe_stderr" | grep -qi "rate.limit\|throttl\|429\|overloaded"; then
            echo "⚠ Rate limit detected (attempt ${attempt}/${max_attempts}). Waiting ${wait_seconds}s..." >&2
            sleep "$wait_seconds"
            wait_seconds=$((wait_seconds * 2))
            (( attempt++ ))
        else
            # Non-rate-limit error — don't block, let the real run surface it
            return 0
        fi
    done

    echo "Error: still rate-limited after ${max_attempts} attempts. Aborting." >&2
    return 1
}

# ---------------------------------------------------------------------------
# Cycle cost rollup
# Sums total cost + turns across all workflow runs in the current calendar
# month from the JSONL logs. Used by workflow completion banners to show
# monthly burn alongside the per-run cost. Silent if no logs exist.
# Usage: print_cycle_totals "$LOG_DIR"
# ---------------------------------------------------------------------------
print_cycle_totals() {
    local log_dir="${1:-.claude/logs}"
    [[ -d "$log_dir" ]] || return 0

    local current_month
    current_month=$(date +%Y-%m)

    local results
    results=$(find "$log_dir" -maxdepth 1 -name '*.jsonl' -type f -newermt "${current_month}-01" -print0 2>/dev/null | \
              xargs -0 -I {} jq -r 'select(.type == "result") | "\(.total_cost_usd // 0)\t\(.num_turns // 0)"' {} 2>/dev/null)

    [[ -n "$results" ]] || return 0

    local total_cost total_turns run_count
    total_cost=$(echo "$results" | awk '{s+=$1} END {printf "%.2f", s}')
    total_turns=$(echo "$results" | awk '{s+=$2} END {print s}')
    run_count=$(echo "$results" | wc -l)

    printf "Cycle totals (%s, %d runs): \$%s · %d turns\n" "$current_month" "$run_count" "$total_cost" "$total_turns"
}

run_claude() {
    local prompt="$1"
    shift
    local extra_args=("$@")

    check_rate_limit || return 1

    local claude_cmd=(
        claude -p "$prompt"
        --model "$WORKFLOW_MODEL"
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

    # -----------------------------------------------------------------------
    # Turn-cap termination — make a silent death LOUD. Deliberately visibility
    # only: no commit, no push, no state file, no resume. Measured rate is
    # 0.9% (4/443 runs, 3 of them from April), every occurrence so far with a
    # human watching, so recovery machinery would add failure modes
    # (unverified commits pushed onto a healthy-looking PR, salvage loops) to
    # serve a sub-1% event that a message already resolves — hand recovery
    # took ~10 minutes once the operator knew where to look. Reopen only if
    # the rate climbs under unattended/pooled operation, and even then the
    # fix is louder signalling, not resume.
    # -----------------------------------------------------------------------
    if grep -q '"subtype":"error_max_turns"' "$LOG_FILE" 2>/dev/null; then
        local wt="" i
        for (( i = 0; i < ${#extra_args[@]}; i++ )); do
            if [[ "${extra_args[i]}" == "-w" ]]; then
                wt="$(git rev-parse --show-toplevel 2>/dev/null)/.claude/worktrees/${extra_args[i+1]}"
                break
            fi
        done
        [[ -n "$wt" ]] || wt="$PWD"
        {
            echo
            echo "================================================================"
            echo "  ⚠ RUN TERMINATED AT TURN CAP (${MAX_TURNS} turns)"
            echo "================================================================"
            echo "  Work is uncommitted at: ${wt}"
            echo "  NOTHING was committed or pushed."
            echo
            echo "  Most often this means the task was mis-sized for this workflow —"
            echo "  a heavier one (build.sh / build-phase.sh) may"
            echo "  fit better, or the task may need splitting."
            echo
            echo "  Inspect:  cd ${wt} && git status"
            echo "================================================================"
        } >&2
        return 1
    fi

    # -----------------------------------------------------------------------
    # Completion contract — exit 0 must mean the workflow actually finished.
    # A headless (`claude -p`) run ends on ANY text-only turn, including a
    # premature "waiting on dispatched agents…" message: the harness reports
    # exit 0 with nothing produced. When a workflow declares COMPLETION_PATTERN,
    # verify the final result contains it; a miss means early-stop → fail LOUD.
    # -----------------------------------------------------------------------
    if [[ -n "${COMPLETION_PATTERN:-}" ]]; then
        local final_result
        final_result=$(jq -r 'select(.type == "result") | .result // ""' "$LOG_FILE" 2>/dev/null)
        if ! grep -qE "$COMPLETION_PATTERN" <<<"$final_result"; then
            {
                echo
                echo "================================================================"
                echo "  ⚠ RUN ENDED WITHOUT COMPLETING — headless early-stop suspected"
                echo "================================================================"
                echo "  Expected completion signal not found in the final result:"
                echo "    pattern: ${COMPLETION_PATTERN}"
                echo
                echo "  Most common cause: the main loop ended a turn with a text-only"
                echo "  message (e.g. 'waiting on dispatched agents') while work was"
                echo "  still outstanding. In headless mode a text-only turn TERMINATES"
                echo "  the run before later stages execute."
                echo "  Inspect: ${LOG_FILE}"
                echo "================================================================"
            } >&2
            return 1
        fi
    fi
}

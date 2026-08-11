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
#   EXIT_RECORD_SCHEMA — a JSON Schema, inline, declaring the Kind 2 typed exit
#                        record the child emits at exit (docs/standards/exit-protocol.md).
#                        Set → the CLI is invoked with --json-schema and the
#                        result event carries `structured_output`. Unset → this
#                        activity behaves exactly as it did before, byte for
#                        byte, which is what keeps the FROZEN V1 bash fleet
#                        (exit-protocol.md §7) out of the migration.
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
    )

    # The typed exit record rides in the CLI's own result envelope, so no write
    # crosses the worktree boundary — the isolation boundary the fleet's safety
    # argument rests on. Appended only when a caller declares a schema; V1
    # callers declare none and their command line is unchanged.
    if [[ -n "${EXIT_RECORD_SCHEMA:-}" ]]; then
        claude_cmd+=(--json-schema "$EXIT_RECORD_SCHEMA")
    fi

    claude_cmd+=("${extra_args[@]}")

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
    # Safety observability — permission_denials[], surfaced on EVERY run.
    #
    # ROUTES NOTHING, DELIBERATELY. This prints and returns nothing; the only
    # actor that BRANCHES on a denial is rule R1 in the V2 router
    # (docs/standards/exit-protocol.md §4), and it routes to the human arm and
    # never to automatic redispatch. Adding a second decider here would put an
    # unbounded retry loop against the fleet's only in-run control in the one
    # file both fleets share.
    #
    # WHY IT IS HERE AND NOT IN THE PYTHON PARENT. Every child of both fleets
    # runs through this function, so one read covers 21 declared workflows
    # rather than the one that reads the typed record. It matters most for the
    # fleet that has no router at all: every V1 child runs under
    # --dangerously-skip-permissions, block-dangerous.sh is by its own header
    # the primary safety layer for headless mode, a tripped hook does NOT fail
    # the run, and build.sh:277 will loop back on `HOLD - redispatch` — so
    # before this line, a V1 child could trip the only control there is and be
    # auto-redispatched with the array as its sole, unread trace.
    #
    # WHY IT CANNOT BE INFERRED FROM ANYTHING ELSE. Measured (Phase 1 E1(f), CLI
    # 2.1.224): the forced-denial run exited 0 with `is_error: false` and
    # `subtype: "success"`. Every signal the fleet reads said clean.
    #
    # `tool_input` IS NOT PRINTED. It carries literal command lines and absolute
    # worktree paths; the Python side drops it at read time so there is no copy
    # to leak, and this must not reintroduce one into a terminal scrollback or a
    # CI log. Count, tool name and tool_use_id only — the id is what locates the
    # denied call in $LOG_FILE, which is the question an operator asks next.
    # THE `fromjson? // empty` PREFILTER IS LOAD-BEARING, and the first version
    # of this block did not have it. The § Completion contract below argues the
    # same point over the same file and its argument applies here verbatim: the
    # stream demonstrably carries non-JSON lines (`assistant_activities.
    # _log_events` documents that it "must SKIP a malformed line", with a test),
    # `jq` STOPS at the first parse error, and the `result` event is the LAST
    # event in the stream — so one junk line anywhere before it suppresses this
    # banner entirely, on exactly the runs where the fleet's only in-run control
    # fired. Three readers of one file disagreeing about whether it may contain
    # junk is how a gate deletes itself.
    #
    # `|| true` IS THE SECOND HALF AND IS NOT DEFENSIVE HABIT. `local denials`
    # is declared on its own line, so the assignment below is a simple command
    # whose exit status IS the pipeline's; every V1 caller runs `set -euo pipefail` and
    # calls `run_claude` unguarded, so without it a parse error would kill a V1
    # workflow immediately after a successful model run, with `2>/dev/null`
    # hiding the reason and BEFORE the turn-cap banner that exists to make a
    # silent death loud. It is a new abort point that `review-runs.sh` — which
    # declares no COMPLETION_PATTERN and so reaches no other jq — never had.
    # It sits in the assignment, outside the block
    # `test_the_denial_surface_ROUTES_NOTHING` scans, because it is about this
    # read surviving, not about the surface deciding anything.
    #
    # AND `|| true` IS ALSO WHAT COVERS A MALFORMED `permission_denials`. `// []`
    # substitutes for null and false ONLY, so a value that arrived as a string
    # or an object reaches `.[]` and is a jq runtime error. A `select(type ==
    # "array")` guard was written here and then removed: with `|| true` present
    # its outcome is byte-identical (empty output, non-fatal), so it was a guard
    # whose removal no test could notice — and an untestable guard beside a
    # test that passes either way is worse than the shorter expression plus one
    # test that actually discriminates.
    local denials denial_count
    denials=$(jq -R 'fromjson? // empty' "$LOG_FILE" 2>/dev/null \
        | jq -r 'select(.type == "result") | .permission_denials // [] | .[]
            | "    · \(.tool_name // "?")  (tool_use_id: \(.tool_use_id // "?"))"' \
            2>/dev/null || true)
    if [[ -n "$denials" ]]; then
        denial_count=$(printf '%s\n' "$denials" | wc -l)
        {
            echo
            echo "================================================================"
            echo "  ⚠ ${denial_count} PERMISSION DENIAL(S) RECORDED — the in-run safety control fired"
            echo "================================================================"
            echo "$denials"
            echo
            echo "  The run's exit status says NOTHING about this: a denial does not"
            echo "  fail the run. This is observability, not a verdict — nothing here"
            echo "  changes what the workflow does next."
            echo "  Inspect: ${LOG_FILE}"
            echo "================================================================"
        } >&2
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
        if [[ -n "${EXIT_RECORD_SCHEMA:-}" ]]; then
            # DECLARING A SCHEMA REPLACES `.result` WITH THE SERIALISED
            # STRUCTURED OUTPUT. Measured on CLI 2.1.224, 2026-08-09, on a run
            # that emitted prose AND called the tool: `.result` was
            # {"outcome":"merge",...} and the model's terminal VERDICT line was
            # not in it. Reading `.result` here would have made this gate fail
            # on every conforming run — silently deleting the fleet's only
            # write-time gate in the same change that added the typed record.
            #
            # The prose survives in the stream's assistant text blocks, so the
            # gate reads those instead.
            #
            # THE `last` IS THE WHOLE GATE, not tidiness. This check exists to
            # catch a run that ENDED EARLY, and `.result` gave it that for free
            # by being the final message. Grepping every assistant block would
            # change the predicate from "the run finished with a verdict" to
            # "the run ever mentioned a verdict" — a model that prints its
            # verdict at turn 20 and then stops on "let me confirm the comment
            # posted" would pass a gate built to fail exactly that. Taking the
            # last text block reproduces `.result`'s finality on the surface the
            # schema left the prose in.
            #
            # `parent_tool_use_id == null` excludes Task sub-agent turns: a
            # nested agent's terminal line is not this run's completion signal.
            #
            # THE `fromjson? // empty` PREFILTER IS LOAD-BEARING, not defensive
            # habit. `jq -s` must parse the WHOLE file before it emits anything,
            # so a single non-JSON line aborts it and `final_result` comes back
            # empty — and this gate then reports "RUN ENDED WITHOUT COMPLETING"
            # for a run that completed perfectly. The stream demonstrably carries
            # such lines: `assistant_activities._log_events` documents that it
            # "must SKIP a malformed line" and a test asserts the Python reader
            # survives a fixture containing raw stderr noise. Two readers of one
            # file disagreeing about whether it may contain junk is how a gate
            # deletes itself. The non-slurp `.result` branch below degrades
            # gracefully by construction (values parsed before the bad line are
            # still emitted), which is why only this branch needs it.
            final_result=$(jq -R 'fromjson? // empty' "$LOG_FILE" 2>/dev/null | jq -rs '[ .[]
                | select(.type == "assistant" and .parent_tool_use_id == null)
                | .message.content[]? | select(.type == "text") | .text ]
                | last // ""')
        else
            final_result=$(jq -r 'select(.type == "result") | .result // ""' "$LOG_FILE" 2>/dev/null)
        fi
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

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
#   EXIT_RECORD_SCHEMA — a JSON Schema, inline, declaring the typed exit
#                        record the child emits at exit (/opt/skyy-net/skyynet-master-planning/standards/exit-protocol.md).
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

# ---------------------------------------------------------------------------
# What the worktree ACTUALLY holds — read from git, printed as facts.
#
# THE BANNER BELOW USED TO ASSERT THIS WITHOUT LOOKING. It printed "Work is
# uncommitted at: <wt>" and "NOTHING was committed or pushed." on every turn-cap
# termination, and it was FALSE the first time it mattered: PR #56's redispatch
# hit the 100-turn cap while printing the PR URL — the last step — with every
# deliverable already pushed and CI green (issue #65). A wrong claim about state
# is worse than no claim: it sends an operator to salvage an empty tree, and can
# get work that is already merge-ready re-dispatched, paying a second full
# budget and opening a conflicting branch. Silence sends them to look; a
# confident sentence sends them somewhere.
#
# WHAT THIS DOES NOT LOOK AT, stated because not asking it is what produced the
# defect. This reads the LOCAL tree only. It does not ask the forge whether a PR
# exists, whether CI passed, or whether the branch merged — so "pushed" here
# means exactly "the branch's upstream ref contains every local commit", which
# is why that arm says CHECK THE PR rather than claiming the work landed. It
# also says nothing about whether the pushed work is CORRECT.
#
# CANNOT-DETERMINE IS A STATE, NOT THE CLEAN CASE. A worktree already removed, a
# tree that is not a repository, a detached HEAD, and a branch with no upstream
# each have no local answer. Each gets its own line saying so. Collapsing any of
# them into "nothing was pushed" would rebuild the defect with better plumbing.
#
# NO `local x=$(...)` ANYWHERE BELOW. That form's exit status is `local`'s, not
# the command's, so a failing git would read as success. Declared first, then
# assigned — which also keeps every status explicit for the `set -euo pipefail`
# callers: every V1 child runs under errexit and calls `run_claude` unguarded,
# so an unguarded non-zero here would kill the workflow inside the banner that
# exists to explain why it died.
#
# AND NO PIPE INTO A COUNTER, WHICH IS THE SAME MISTAKE ONE LAYER DOWN. THERE
# ARE TWO CALLERS WITH DIFFERENT SHELL OPTIONS, and this function must be right
# under both. The five V1 children all run `set -euo pipefail`; the V2 Python
# fleet sources this file with NO options at all
# (`assistant_activities.py`: `bash -c 'source "$runner"; run_claude "$1"'`), and
# this script sets none itself. In `x=$(git ... | wc -l)` the substitution's exit
# status is `wc`'s, and `wc -l` on empty stdin SUCCEEDS printing `0` — so without
# pipefail a failed `git` reads as "zero commits ahead" and the function prints
# `✓ fully pushed`. That is issue #65's defect rebuilt inside issue #65's fix,
# reachable only on the fleet the migration is moving toward. Every counter below
# is therefore a single command or a here-string, never a pipe: the exit status
# that reaches the `||` is the one that knows whether the check ran.
_wds_undetermined() {
    echo "  ? $1"
    echo "    Committed and pushed state cannot be determined from here — check the PR."
}

worktree_delivery_state() {
    local wt="$1"

    if [[ ! -d "$wt" ]]; then
        _wds_undetermined "The worktree is NOT on disk: ${wt}"
        return 0
    fi
    local toplevel
    if ! toplevel=$(git -C "$wt" rev-parse --show-toplevel 2>/dev/null); then
        _wds_undetermined "${wt} is not a readable git worktree."
        return 0
    fi
    # AND IT MUST BE *THIS* WORKTREE'S ROOT. The fleet's worktrees live at
    # <repo>/.claude/worktrees/<name>, INSIDE the parent repository — so a
    # leftover directory there (a `git worktree remove` that partially failed,
    # a stale mkdir) is still a path `git -C` answers for, by walking up to the
    # PARENT. That answer is the main checkout's branch and the main checkout's
    # dirt, reported as this run's. It is the same defect this function exists
    # to remove, reached through a path the -d test above cannot see.
    local wt_real top_real
    wt_real=$(cd "$wt" && pwd -P) || wt_real=""
    top_real=$(cd "$toplevel" && pwd -P) || top_real=""
    if [[ -z "$wt_real" || "$wt_real" != "$top_real" ]]; then
        _wds_undetermined "${wt} exists but is not a worktree root — git answers there for ${toplevel}."
        return 0
    fi
    # A DISTINCT REASON, NOT THE ONE ABOVE. This arm and the `rev-parse` arm are
    # different failures — here git resolved the toplevel and then could not read
    # the index (a corrupt or locked `.git/index`, an unreadable object store) —
    # and they shared a sentence in the first draft. Two causes reported with one
    # message is a report an operator cannot act on, which is a quieter form of
    # the same defect: it names a state it did not distinguish.
    local porcelain
    if ! porcelain=$(git -C "$wt" status --porcelain 2>/dev/null); then
        _wds_undetermined "${wt} is a git worktree, but its status could not be read (index or object store unreadable)."
        return 0
    fi

    # UNCOMMITTED AND UNPUSHED ARE INDEPENDENT, and both are reported. The
    # original banner used one sentence for both, which is how a fully-pushed
    # tree got described as unsalvaged work.
    #
    # A HERE-STRING, NOT A PIPE — see the header. `x=$(... | wc -l)` would hide
    # the counter's exit status behind `wc`'s under the V2 caller's optionless
    # shell.
    local dirty=0
    [[ -z "$porcelain" ]] || dirty=$(wc -l <<<"$porcelain")
    if [[ "$dirty" -gt 0 ]]; then
        echo "  ✗ ${dirty} path(s) carry UNCOMMITTED changes at: ${wt}"
    else
        echo "  ✓ Working tree is clean — nothing uncommitted at: ${wt}"
    fi

    local branch upstream unpushed
    branch=$(git -C "$wt" rev-parse --abbrev-ref HEAD 2>/dev/null) || branch=""
    upstream=$(git -C "$wt" rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null) || upstream=""

    if [[ -z "$branch" || "$branch" == "HEAD" ]]; then
        echo "  ? HEAD is detached — there is no branch, so whether the work was pushed"
        echo "    has no local answer. Check the PR."
        return 0
    fi
    if [[ -z "$upstream" ]]; then
        echo "  ? Branch '${branch}' has no upstream ref — whether it was pushed cannot be"
        echo "    determined from here. Check the PR, or: git -C ${wt} log --oneline"
        return 0
    fi
    # The remote-tracking ref, NOT the remote. Read locally and deliberately: a
    # fetch inside a failure banner is a network call on a path whose whole job
    # is to print. A push made by this run updates the tracking ref, which is
    # the case this arm has to get right.
    #
    # `rev-list --count`, NOT `log | wc -l`. It is ONE command, so the exit
    # status the `||` sees is git's own — the count is unavailable exactly when
    # git could not produce it, under every caller's shell options rather than
    # only under `pipefail`. The `wc` form claimed `✓ fully pushed` from a failed
    # git on the V2 fleet; see the header.
    unpushed=$(git -C "$wt" rev-list --count "${upstream}..HEAD" 2>/dev/null) || unpushed=""
    if [[ -z "$unpushed" ]]; then
        echo "  ? Could not compare '${branch}' against '${upstream}' — pushed state unknown."
    elif [[ "$unpushed" -gt 0 ]]; then
        echo "  ✗ ${unpushed} commit(s) on '${branch}' are NOT pushed to '${upstream}'."
    else
        echo "  ✓ '${branch}' is fully pushed to '${upstream}' — the cap may have fired AFTER"
        echo "    the work landed. CHECK THE PR BEFORE REDISPATCHING: re-running work that is"
        echo "    already merge-ready costs a second budget and can open a conflicting branch."
    fi
}

# THE COMPLETION-FAILURE DIAGNOSIS, AS ITS OWN FUNCTION SO A TEST CAN DRIVE IT.
# Same reason `_wds_undetermined` is separate: a banner welded inside
# `run_claude` is reachable only by running a whole dispatch, so the branch
# that reports the WRONG CAUSE is exactly the one nothing ever executes.
# Reads $1 = LOG_FILE, $2 = COMPLETION_PATTERN. Writes the banner to stderr.
_completion_failure_banner() {
    local LOG_FILE="$1" COMPLETION_PATTERN="$2"
        # ASK THE LOG WHY BEFORE GUESSING WHY. The result row carries
        # `is_error` and a plain-English reason — "You've hit your session
        # limit · resets 3:20am", "API Error: The response stopped
        # arriving" — and this gate used to print a confident early-stop
        # diagnosis over the top of it. The two causes have OPPOSITE
        # remedies: a transport or quota failure is re-dispatched unchanged,
        # an early stop means the prompt lets a text-only turn end the run.
        # Sending the operator to rewrite a prompt when the answer was
        # "wait and re-run" is the wrong-confidence class this fleet keeps
        # finding, and here it was the diagnostic itself.
        #
        # MEASURED across `.claude/logs`: 4 runs, 3 workflows, 2 distinct
        # real causes, and all 4 were reported as a suspected early stop.
        local err_reason
        err_reason=$(jq -R 'fromjson? // empty' "$LOG_FILE" 2>/dev/null \
            | jq -rs '[ .[] | select(.type == "result" and .is_error == true)
                | .result // "" ] | last // ""')
        {
            echo
            echo "================================================================"
            if [[ -n "$err_reason" ]]; then
                echo "  ⚠ RUN ENDED WITHOUT COMPLETING — the run reported an ERROR"
                echo "================================================================"
                echo "  The run did not stop early; it FAILED, and said why:"
                echo
                echo "    ${err_reason}"
                echo
                echo "  Re-dispatch once the stated condition clears. This is NOT a"
                echo "  prompt defect and the prompt does not need changing."
            else
                echo "  ⚠ RUN ENDED WITHOUT COMPLETING — headless early-stop suspected"
                echo "================================================================"
                echo "  The run reported NO error and still emitted no verdict,"
                echo "  which is what an early stop looks like."
                echo
                echo "  Most common cause: the main loop ended a turn with a text-only"
                echo "  message (e.g. 'waiting on dispatched agents') while work was"
                echo "  still outstanding. In headless mode a text-only turn TERMINATES"
                echo "  the run before later stages execute."
            fi
            echo "  Expected completion signal: ${COMPLETION_PATTERN}"
            echo "  Inspect: ${LOG_FILE}"
            echo "================================================================"
        } >&2
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
    # (/opt/skyy-net/skyynet-master-planning/standards/exit-protocol.md §4), and it routes to the human arm and
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
            worktree_delivery_state "$wt"
            echo
            echo "  If work is genuinely incomplete above, the task was probably mis-sized"
            echo "  for this workflow — a heavier one (build.sh / build-phase.sh) may fit"
            echo "  better, or the task may need splitting."
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
            _completion_failure_banner "$LOG_FILE" "$COMPLETION_PATTERN"
            return 1
        fi
    fi
}

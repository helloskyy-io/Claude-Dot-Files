#!/usr/bin/env bash
# gh-monitor.sh — GitHub monitor for @claude PR comment automation
#
# Polls configured GitHub repos for PR comments mentioning @claude,
# routes them to the appropriate workflow script, and tracks state
# via emoji reactions.
#
# Usage:
#   ./gh-monitor.sh              # normal polling run
#   ./gh-monitor.sh --dry-run    # detect comments but don't run workflows
#
# Designed to run as a systemd oneshot service triggered by gh-monitor.timer.
# Uses bash + gh CLI only — zero Claude/AI tokens burned on polling.
#
# See docs/standards/services.md for the conventions this script follows.

set -euo pipefail

# ---------------------------------------------------------------------------
# Script location and repo root
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# ---------------------------------------------------------------------------
# Environment checks (must run before config loading, which requires yq)
# ---------------------------------------------------------------------------
for cmd in gh jq yq; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "Error: '$cmd' not found in PATH" >&2
        exit 1
    fi
done

# ---------------------------------------------------------------------------
# Load config from config.yaml (all vars have defaults below)
# ---------------------------------------------------------------------------
CONFIG_FILE="${REPO_ROOT}/config.yaml"

# Helper: read a value from config.yaml, returns empty string if key is missing/null
# Usage: cfg <section> <key>
cfg() {
    local section="$1" key="$2"
    local val
    val=$(yq -r ".${section}.${key}" "$CONFIG_FILE" 2>/dev/null || echo "")
    # yq prints "null" for missing keys
    if [[ "$val" == "null" ]]; then
        echo ""
    else
        echo "$val"
    fi
}

if [[ -f "$CONFIG_FILE" ]]; then
    GH_MONITOR_REPO_FOLDERS="${GH_MONITOR_REPO_FOLDERS:-$(cfg gh-monitor repo-folders)}"
    GH_MONITOR_MAX_CONCURRENT="${GH_MONITOR_MAX_CONCURRENT:-$(cfg gh-monitor max-concurrent)}"
    GH_MONITOR_ENABLE_REVISION="${GH_MONITOR_ENABLE_REVISION:-$(cfg gh-monitor enable-revision)}"
    GH_MONITOR_ENABLE_REVISION_MAJOR="${GH_MONITOR_ENABLE_REVISION_MAJOR:-$(cfg gh-monitor enable-revision-major)}"
    GH_MONITOR_ENABLE_PLAN_REVISION="${GH_MONITOR_ENABLE_PLAN_REVISION:-$(cfg gh-monitor enable-plan-revision)}"
    GH_MONITOR_ENABLE_BUILD_PHASE="${GH_MONITOR_ENABLE_BUILD_PHASE:-$(cfg gh-monitor enable-build-phase)}"
    GH_MONITOR_ENABLE_HELP="${GH_MONITOR_ENABLE_HELP:-$(cfg gh-monitor enable-help)}"
    GH_MONITOR_DRY_RUN="${GH_MONITOR_DRY_RUN:-$(cfg gh-monitor dry-run)}"
    GH_MONITOR_BACKLOG_DAYS="${GH_MONITOR_BACKLOG_DAYS:-$(cfg gh-monitor backlog-days)}"
    GH_MONITOR_WORKFLOW_DIR="${GH_MONITOR_WORKFLOW_DIR:-$(cfg gh-monitor workflow-dir)}"
fi

# ---------------------------------------------------------------------------
# Defaults (applied if not set by config or environment)
# ---------------------------------------------------------------------------
: "${GH_MONITOR_REPO_FOLDERS:=""}"
: "${GH_MONITOR_MAX_CONCURRENT:=1}"
: "${GH_MONITOR_ENABLE_REVISION:=true}"
: "${GH_MONITOR_ENABLE_REVISION_MAJOR:=true}"
: "${GH_MONITOR_ENABLE_PLAN_REVISION:=true}"
: "${GH_MONITOR_ENABLE_BUILD_PHASE:=true}"
: "${GH_MONITOR_ENABLE_HELP:=true}"
: "${GH_MONITOR_DRY_RUN:=false}"
: "${GH_MONITOR_BACKLOG_DAYS:=7}"
: "${GH_MONITOR_WORKFLOW_DIR:="${REPO_ROOT}/scripts/workflows"}"

# ---------------------------------------------------------------------------
# Discover GitHub repos from configured folders
# ---------------------------------------------------------------------------
# Associative array: GitHub org/repo → local path
declare -A REPO_PATH_MAP

discover_repos() {
    local repos=()
    for folder in $GH_MONITOR_REPO_FOLDERS; do
        # Expand ~ to home dir
        folder="${folder/#\~/$HOME}"
        if [[ ! -d "$folder" ]]; then
            echo "  Note: repo folder ${folder} does not exist on this machine — skipping"
            continue
        fi
        for dir in "$folder"/*/; do
            if [[ -d "${dir}.git" ]]; then
                # Extract GitHub org/repo from the git remote
                local remote
                remote=$(git -C "$dir" remote get-url origin 2>/dev/null || echo "")
                if [[ -n "$remote" ]]; then
                    # Handle both SSH and HTTPS remotes
                    local gh_repo
                    gh_repo=$(echo "$remote" | sed -E 's#.*github\.com[:/]##; s#\.git$##')
                    if [[ -n "$gh_repo" && "$gh_repo" == */* ]]; then
                        repos+=("$gh_repo")
                        # Store the mapping so we can cd to the right repo later
                        REPO_PATH_MAP["$gh_repo"]="${dir%/}"
                    fi
                fi
            fi
        done
    done
    echo "${repos[*]}"
}

GH_MONITOR_REPOS=$(discover_repos)

# Helper: get local path for a GitHub repo
get_repo_path() {
    local repo="$1"
    echo "${REPO_PATH_MAP[$repo]:-}"
}

# CLI flag override
for arg in "$@"; do
    case "$arg" in
        --dry-run) GH_MONITOR_DRY_RUN=true ;;
        *) echo "Error: unknown option '$arg'" >&2; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# State directory and lock file
# ---------------------------------------------------------------------------
STATE_DIR="${REPO_ROOT}/.claude/state"
LOCK_FILE="${STATE_DIR}/gh-monitor.lock"
mkdir -p "$STATE_DIR"

# Verify gh authentication
if ! gh auth status &>/dev/null; then
    echo "Error: gh CLI is not authenticated. Run 'gh auth login' first." >&2
    exit 1
fi

# Verify repos were discovered
if [[ -z "$GH_MONITOR_REPOS" ]]; then
    if [[ -z "$GH_MONITOR_REPO_FOLDERS" ]]; then
        echo "Error: No repo-folders configured in ${CONFIG_FILE} under gh-monitor.repo-folders" >&2
    else
        echo "Error: No GitHub repos found in configured folders: ${GH_MONITOR_REPO_FOLDERS}" >&2
    fi
    exit 1
fi

# Verify workflow directory exists
if [[ ! -d "$GH_MONITOR_WORKFLOW_DIR" ]]; then
    echo "Error: workflow directory not found at ${GH_MONITOR_WORKFLOW_DIR}" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Concurrency guard (lock file with PID for stale detection)
# Note: while the lock is held, manual gh-monitor.sh runs will also be blocked.
# ---------------------------------------------------------------------------
if [[ -f "$LOCK_FILE" ]]; then
    LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
    if [[ -n "$LOCK_PID" ]] && kill -0 "$LOCK_PID" 2>/dev/null; then
        echo "Another instance is running (PID ${LOCK_PID}). Skipping."
        exit 0
    fi
    echo "Stale lock file found (PID ${LOCK_PID} not running). Removing."
    rm -f "$LOCK_FILE"
fi
trap 'rm -f "$LOCK_FILE"' EXIT
echo $$ > "$LOCK_FILE"

# ---------------------------------------------------------------------------
# Rate limit check
# ---------------------------------------------------------------------------
check_rate_limit() {
    local remaining
    remaining=$(gh api rate_limit --jq '.resources.core.remaining' 2>/dev/null || echo "0")
    if [[ "$remaining" -lt 50 ]]; then
        echo "Warning: GitHub API rate limit low (${remaining} remaining). Backing off."
        return 1
    fi
    return 0
}

if ! check_rate_limit; then
    exit 0
fi

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
echo "================================================================"
echo "  GH-MONITOR"
echo "================================================================"
echo "  Repos     : ${GH_MONITOR_REPOS}"
echo "  Dry run   : ${GH_MONITOR_DRY_RUN}"
echo "  Backlog   : ${GH_MONITOR_BACKLOG_DAYS} days"
echo "  Workflows : ${GH_MONITOR_WORKFLOW_DIR}"
echo "  Timestamp : $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================================"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Calculate the cutoff date for backlog processing (UTC to match GitHub's timestamps)
BACKLOG_CUTOFF=$(date -u -d "${GH_MONITOR_BACKLOG_DAYS} days ago" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
    || date -u -v-${GH_MONITOR_BACKLOG_DAYS}d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
    || echo "")
if [[ -z "$BACKLOG_CUTOFF" ]]; then
    echo "Warning: could not compute backlog cutoff date. All comments will be eligible."
fi

# Check if a comment already has one of our state reactions
# State reactions: eyes (processing), hooray (success), -1 (failed), confused (clarification)
comment_has_reaction() {
    local repo="$1"
    local comment_id="$2"
    local our_reactions
    our_reactions=$(gh api "repos/${repo}/issues/comments/${comment_id}/reactions" \
        --jq '[.[] | select(.content == "eyes" or .content == "hooray" or .content == "-1" or .content == "confused")] | length' \
        2>/dev/null || echo "error")

    # If the API call failed, treat as "has reaction" to avoid duplicate processing
    if [[ "$our_reactions" == "error" ]]; then
        echo "    Warning: could not check reactions for comment ${comment_id}, skipping to be safe."
        return 0
    fi

    [[ "$our_reactions" -gt 0 ]]
}

# React to a comment with a specific emoji
react_to_comment() {
    local repo="$1"
    local comment_id="$2"
    local reaction="$3"

    if [[ "$GH_MONITOR_DRY_RUN" == "true" ]]; then
        echo "  [DRY RUN] Would react with ${reaction} on comment ${comment_id}"
        return 0
    fi

    gh api "repos/${repo}/issues/comments/${comment_id}/reactions" \
        -f content="$reaction" \
        --silent 2>/dev/null || true
}

# Post a comment on a PR
post_pr_comment() {
    local repo="$1"
    local pr_number="$2"
    local body="🤖 **[gh-monitor]** $3"

    if [[ "$GH_MONITOR_DRY_RUN" == "true" ]]; then
        echo "  [DRY RUN] Would post comment on PR #${pr_number}"
        return 0
    fi

    gh api "repos/${repo}/issues/${pr_number}/comments" \
        -f body="$body" \
        --silent 2>/dev/null || true
}

# Parse the @claude command from a comment body
# Returns: route and description separated by a tab
parse_command() {
    local body="$1"

    # Strip code blocks (``` ... ```) to avoid matching @claude inside them
    local cleaned
    cleaned=$(echo "$body" | sed '/^```/,/^```/d')

    # Match @claude at start of line or start of comment
    local match
    match=$(echo "$cleaned" | grep -m1 -iE '^\s*@claude\b' || echo "")

    if [[ -z "$match" ]]; then
        echo ""
        return
    fi

    # Extract the part after @claude
    local after_mention
    after_mention=$(echo "$match" | sed -E 's/^\s*@claude\s*//i')

    # Determine route
    if echo "$after_mention" | grep -qiE '^help\s*$'; then
        echo "help"
        return
    fi

    if echo "$after_mention" | grep -qiE '^revision-major:\s*'; then
        local desc
        desc=$(echo "$after_mention" | sed -E 's/^revision-major:\s*//i')
        printf "revision-major\t%s" "$desc"
        return
    fi

    if echo "$after_mention" | grep -qiE '^revision:\s*'; then
        local desc
        desc=$(echo "$after_mention" | sed -E 's/^revision:\s*//i')
        printf "revision\t%s" "$desc"
        return
    fi

    if echo "$after_mention" | grep -qiE '^plan-revision:\s*'; then
        local desc
        desc=$(echo "$after_mention" | sed -E 's/^plan-revision:\s*//i')
        printf "plan-revision\t%s" "$desc"
        return
    fi

    if echo "$after_mention" | grep -qiE '^build-phase:\s*'; then
        local desc
        desc=$(echo "$after_mention" | sed -E 's/^build-phase:\s*//i')
        printf "build-phase\t%s" "$desc"
        return
    fi

    # Unrecognized route
    printf "unknown\t%s" "$after_mention"
}

# Generate help text
generate_help_text() {
    cat <<'HELPEOF'
## Available Commands

| Command | Description |
|---------|------------|
| `@claude revision: <description>` | Minor code fix |
| `@claude revision-major: <description>` | Significant code rework (with code review + refactoring agents) |
| `@claude plan-revision: <description>` | Revise planning docs (with architect + planner agents) |
| `@claude build-phase: <description>` | Implement from a plan doc (requires plan path in description) |
| `@claude help` | Show this help message |

### Examples

```
@claude revision: fix the typo in the README header
@claude revision-major: restructure the authentication module to use JWT
@claude plan-revision: add detailed phase doc for the Harbor integration
@claude help
```

### Notes
- Every command requires an explicit route prefix
- Commands are processed by a local poller — responses may take a few minutes
- Only one workflow runs at a time per machine
HELPEOF
}

# Count currently running workflow processes (scoped to our workflow scripts)
count_running_workflows() {
    local count
    count=$(pgrep -f "${GH_MONITOR_WORKFLOW_DIR}/(revision|revision-major|plan-revision|build-phase)\.sh" 2>/dev/null | wc -l || echo "0")
    echo "$count"
}

# Run a workflow route (shared logic for revision and revision-major)
# Args: route_name enable_flag script_name repo pr_number comment_id description
run_workflow_route() {
    local route_name="$1"
    local enable_flag="$2"
    local script_name="$3"
    local repo="$4"
    local pr_number="$5"
    local comment_id="$6"
    local description="$7"

    if [[ "$enable_flag" != "true" ]]; then
        echo "    ${route_name} route is disabled. Skipping."
        ((SKIPPED++)) || true
        return 0
    fi

    if [[ -z "$description" || ${#description} -lt 10 ]]; then
        react_to_comment "$repo" "$comment_id" "confused"
        local clarify_body="I need a more specific description for this ${route_name}. Please provide details."
        clarify_body+=$'\n\n'"Example: \`@claude ${route_name}: <describe what you want changed>\`"
        clarify_body+=$'\n\n'"Type \`@claude help\` for available commands."
        post_pr_comment "$repo" "$pr_number" "$clarify_body"
        echo "    Insufficient context — posted clarification request."
        ((PROCESSED++)) || true
        return 0
    fi

    # Check concurrency
    local running
    running=$(count_running_workflows)
    if [[ "$running" -ge "$GH_MONITOR_MAX_CONCURRENT" ]]; then
        echo "    Max concurrent workflows reached (${running}/${GH_MONITOR_MAX_CONCURRENT}). Skipping."
        ((SKIPPED++)) || true
        return 0
    fi

    react_to_comment "$repo" "$comment_id" "eyes"

    if [[ "$GH_MONITOR_DRY_RUN" == "true" ]]; then
        echo "    [DRY RUN] Would run: ${script_name} \"${description}\" --pr ${pr_number}"
        react_to_comment "$repo" "$comment_id" "hooray"
        ((PROCESSED++)) || true
        return 0
    fi

    # Run the workflow from the TARGET repo's directory (not claude-dot-files)
    local target_path
    target_path=$(get_repo_path "$repo")
    if [[ -z "$target_path" ]]; then
        echo "    Error: could not find local path for ${repo}"
        react_to_comment "$repo" "$comment_id" "-1"
        post_pr_comment "$repo" "$pr_number" "Failed: could not find local clone of ${repo} on this machine."
        ((ERRORS++)) || true
        return 0
    fi
    echo "    Target repo: ${target_path}"
    echo "    Launching ${script_name}..."
    local workflow_exit=0
    (
        cd "$target_path"
        "${GH_MONITOR_WORKFLOW_DIR}/${script_name}" "$description" --pr "$pr_number"
    ) || workflow_exit=$?

    if [[ "$workflow_exit" -eq 0 ]]; then
        react_to_comment "$repo" "$comment_id" "hooray"
        post_pr_comment "$repo" "$pr_number" "✅ Completed ${route_name} workflow. Changes pushed to this PR."
        echo "    ${route_name} completed successfully."
    else
        react_to_comment "$repo" "$comment_id" "-1"
        local error_body="${route_name} workflow failed (exit code: ${workflow_exit}). Check the logs for details."
        error_body+=$'\n\n'"Triggered by: \`@claude ${route_name}: ${description}\`"
        post_pr_comment "$repo" "$pr_number" "$error_body"
        echo "    ${route_name} FAILED (exit ${workflow_exit})."
        ((ERRORS++)) || true
    fi
    ((PROCESSED++)) || true
}

# ---------------------------------------------------------------------------
# Main processing loop
# ---------------------------------------------------------------------------
PROCESSED=0
SKIPPED=0
ERRORS=0

for REPO in $GH_MONITOR_REPOS; do
    echo ""
    echo "--- Checking ${REPO} ---"

    # Get open PRs with comments
    PR_NUMBERS=$(gh api "repos/${REPO}/pulls?state=open&per_page=100" \
        --jq '.[].number' 2>/dev/null || echo "")

    if [[ -z "$PR_NUMBERS" ]]; then
        echo "  No open PRs found."
        continue
    fi

    for PR_NUMBER in $PR_NUMBERS; do
        # Get comments on this PR
        COMMENTS_JSON=$(gh api "repos/${REPO}/issues/${PR_NUMBER}/comments?per_page=100" \
            --jq '[.[] | {id: .id, body: .body, created_at: .created_at, user: .user.login}]' \
            2>/dev/null || echo "[]")

        # Filter for @claude mentions
        COMMENT_IDS=$(echo "$COMMENTS_JSON" | jq -r '.[] | select(.body | test("(?i)^\\s*@claude\\b"; "m")) | .id' 2>/dev/null || echo "")

        if [[ -z "$COMMENT_IDS" ]]; then
            continue
        fi

        for COMMENT_ID in $COMMENT_IDS; do
            # Extract all comment fields in a single jq pass (use --argjson for safe interpolation)
            COMMENT_DETAILS=$(echo "$COMMENTS_JSON" | jq -r --argjson cid "$COMMENT_ID" \
                '.[] | select(.id == $cid) | "\(.created_at)\t\(.user)"')
            COMMENT_DATE=$(echo "$COMMENT_DETAILS" | cut -f1)
            COMMENT_USER=$(echo "$COMMENT_DETAILS" | cut -f2)
            COMMENT_BODY=$(echo "$COMMENTS_JSON" | jq -r --argjson cid "$COMMENT_ID" '.[] | select(.id == $cid) | .body')

            # Skip if too old (backlog limit)
            if [[ -n "$BACKLOG_CUTOFF" ]]; then
                if [[ "$COMMENT_DATE" < "$BACKLOG_CUTOFF" ]]; then
                    echo "  PR #${PR_NUMBER} comment ${COMMENT_ID}: skipped (older than ${GH_MONITOR_BACKLOG_DAYS} days)"
                    ((SKIPPED++)) || true
                    continue
                fi
            fi

            # Check for existing reactions (dedup)
            if comment_has_reaction "$REPO" "$COMMENT_ID"; then
                continue
            fi

            echo "  PR #${PR_NUMBER} comment ${COMMENT_ID} by ${COMMENT_USER}: processing..."

            # Parse the command
            PARSED=$(parse_command "$COMMENT_BODY")
            ROUTE=$(echo "$PARSED" | cut -f1)
            DESCRIPTION=$(echo "$PARSED" | cut -sf2-)

            if [[ -z "$ROUTE" ]]; then
                # No @claude mention found at line start (might be inside code block)
                continue
            fi

            echo "    Route: ${ROUTE}"
            if [[ -n "$DESCRIPTION" ]]; then
                echo "    Description: ${DESCRIPTION}"
            fi

            case "$ROUTE" in
                help)
                    if [[ "$GH_MONITOR_ENABLE_HELP" != "true" ]]; then
                        echo "    Help route is disabled. Skipping."
                        ((SKIPPED++)) || true
                        continue
                    fi

                    react_to_comment "$REPO" "$COMMENT_ID" "eyes"
                    HELP_TEXT=$(generate_help_text)
                    post_pr_comment "$REPO" "$PR_NUMBER" "$HELP_TEXT"
                    react_to_comment "$REPO" "$COMMENT_ID" "hooray"
                    echo "    Posted help text."
                    ((PROCESSED++)) || true
                    ;;

                revision)
                    run_workflow_route "revision" "$GH_MONITOR_ENABLE_REVISION" "revision.sh" \
                        "$REPO" "$PR_NUMBER" "$COMMENT_ID" "$DESCRIPTION"
                    ;;

                revision-major)
                    run_workflow_route "revision-major" "$GH_MONITOR_ENABLE_REVISION_MAJOR" "revision-major.sh" \
                        "$REPO" "$PR_NUMBER" "$COMMENT_ID" "$DESCRIPTION"
                    ;;

                plan-revision)
                    run_workflow_route "plan-revision" "${GH_MONITOR_ENABLE_PLAN_REVISION:-true}" "plan-revision.sh" \
                        "$REPO" "$PR_NUMBER" "$COMMENT_ID" "$DESCRIPTION"
                    ;;

                build-phase)
                    run_workflow_route "build-phase" "${GH_MONITOR_ENABLE_BUILD_PHASE:-true}" "build-phase.sh" \
                        "$REPO" "$PR_NUMBER" "$COMMENT_ID" "$DESCRIPTION"
                    ;;

                unknown)
                    react_to_comment "$REPO" "$COMMENT_ID" "confused"
                    UNKNOWN_BODY="I didn't recognize that command. Every command requires an explicit route prefix."
                    UNKNOWN_BODY+=$'\n\n'"Type \`@claude help\` to see available commands and syntax."
                    post_pr_comment "$REPO" "$PR_NUMBER" "$UNKNOWN_BODY"
                    echo "    Unknown route — posted clarification."
                    ((PROCESSED++)) || true
                    ;;
            esac
        done
    done
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "================================================================"
echo "  GH-MONITOR COMPLETE"
echo "================================================================"
echo "  Processed : ${PROCESSED}"
echo "  Skipped   : ${SKIPPED}"
echo "  Errors    : ${ERRORS}"
echo "  Timestamp : $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================================"

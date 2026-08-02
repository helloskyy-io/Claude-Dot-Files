#!/usr/bin/env bash
#
# require-environment.sh — ACTIVITY: establish the execution environment
#
# ACTIVITY LAYER (Temporal Standard §3.3b, "generic executors"): workflow-
# agnostic, single technical responsibility, idempotent — it inspects and
# resolves, it never mutates anything but the current directory.
#
# THE DUPLICATION IT REPLACES: ten workflows opened with the same ~36 lines —
# tool presence, --repo validation, git-repo confirmation, formatter check,
# cd-to-root. Two children carried it byte-identical; the other eight had
# drifted into three variants. Drift in a preamble is the expensive kind,
# because it is the code nobody reads while reviewing a prompt change.
#
# Usage (after arg parsing, before any naming/paths):
#   source "${SCRIPT_DIR}/activities/require-environment.sh"   # or ../activities/
#   require_environment "$REPO_TARGET" "$FORMATTER"
#
# Sets REPO_ROOT and leaves the shell cd'd there. Exits non-zero and loud on any
# failure — these are all preconditions, and a workflow that proceeds without
# them fails later in a way that looks like a model problem.
#
# Args:
#   $1  repo_target  — the --repo value, or "" to use the invocation directory
#   $2  formatter    — path to the stream formatter this workflow will use
#   $3+ extra_cmds   — optional additional required commands (default: claude gh jq)

require_environment() {
    local repo_target="${1:-}"
    local formatter="${2:-}"
    shift 2 2>/dev/null || true
    local cmds=(claude gh jq "$@")

    local cmd
    for cmd in "${cmds[@]}"; do
        if ! command -v "$cmd" &>/dev/null; then
            echo "Error: '$cmd' not found in PATH" >&2
            exit 1
        fi
    done

    # Explicit target repo (--repo) — validate and switch BEFORE resolving the
    # root. The target identity is explicit, never derived from the invocation
    # directory (Temporal Standard §7.5 principle): cwd DRIFTS as a side effect
    # of other workflow runs, observed independently by two sessions. Without
    # --repo, the invocation directory's repo is the target.
    if [[ -n "$repo_target" ]]; then
        if [[ ! -d "$repo_target" ]]; then
            echo "Error: --repo path not found: ${repo_target}" >&2
            exit 1
        fi
        if ! git -C "$repo_target" rev-parse --show-toplevel &>/dev/null; then
            echo "Error: --repo path is not a git repository: ${repo_target}" >&2
            exit 1
        fi
        cd "$repo_target"
    fi

    if ! git rev-parse --show-toplevel &>/dev/null; then
        echo "Error: not inside a git repository" >&2
        exit 1
    fi

    if [[ -n "$formatter" && ! -x "$formatter" ]]; then
        echo "Error: stream formatter not found at ${formatter}" >&2
        exit 1
    fi

    # Always operate from the repo root so worktree paths are consistent
    REPO_ROOT="$(git rev-parse --show-toplevel)"
    cd "$REPO_ROOT"
}

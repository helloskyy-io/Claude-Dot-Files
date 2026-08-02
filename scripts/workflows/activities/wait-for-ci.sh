#!/usr/bin/env bash
#
# wait-for-ci.sh — ACTIVITY: block until a PR's head commit has settled checks
#
# ACTIVITY LAYER (Temporal Standard §3.3b, "generic executors"): workflow-
# agnostic, single technical responsibility, idempotent — polling can be
# repeated freely and re-running it never changes the world. Sourced by any
# parent that sequences two children across a push.
#
# WHY A PARENT NEEDS THIS AT ALL: the child that pushes cannot see its own CI.
# Pushing is its terminal act, so the gate has not finished when it exits. The
# gap between two children is therefore a real verification window — a run has
# already caught a gate RED on a clean runner while green locally (tests coupled
# to host state). Nothing made that window exist; it was luck of the runner.
#
# WHY IT LIVES IN THE PARENT AND NOT IN A CHILD: the parent is pure bash with no
# turn budget, so polling costs wall-clock only. The same loop inside a model run
# would burn the reliability budget the child split exists to protect.
#
# Usage:   source activities/wait-for-ci.sh
#          wait_for_ci <pr-number>
# Sets:    CI_UNSETTLED=true when settlement could not be confirmed.
# Returns: always 0 — a slow CI gate must never kill a run (see the timeout).

CI_TIMEOUT=${CI_TIMEOUT:-600}   # 10 min — long enough for typical gates, short enough not to strand a run
CI_GRACE=${CI_GRACE:-45}        # checks take a beat to register; "zero checks" before this races the runner
CI_POLL=${CI_POLL:-15}

wait_for_ci() {
    local pr="$1"
    CI_UNSETTLED=false

    local head_sha
    head_sha=$(gh pr view "$pr" --json headRefOid --jq '.headRefOid' 2>/dev/null || echo "")
    if [[ -z "$head_sha" ]]; then
        echo "⚠ Could not resolve PR #${pr} head SHA — skipping the CI wait." >&2
        CI_UNSETTLED=true
        return 0
    fi

    # Guard GitHub's replication lag between the push and the next child's fresh
    # worktree fetch: if the SHA is not yet fetchable, that child would check out
    # a stale branch and review the wrong code. Prevents a silent class.
    if ! git fetch -q origin "$head_sha" 2>/dev/null && ! git cat-file -e "${head_sha}^{commit}" 2>/dev/null; then
        echo "→ Head SHA ${head_sha:0:8} not yet fetchable — waiting ${CI_GRACE}s for replication…"
        sleep "$CI_GRACE"
    fi

    echo "→ Waiting for CI on ${head_sha:0:8} (timeout ${CI_TIMEOUT}s)…"
    local elapsed=0 check_states
    while true; do
        # `gh pr checks` exits nonzero when checks FAIL and when none exist, so
        # branch on the states themselves rather than on the exit code.
        check_states=$(gh pr checks "$pr" --json state --jq '.[].state' 2>/dev/null || echo "")

        if [[ -z "$check_states" ]]; then
            if (( elapsed >= CI_GRACE )); then
                echo "  No checks configured for this PR — proceeding."
                return 0
            fi
        elif ! grep -qE '^(QUEUED|IN_PROGRESS|PENDING|WAITING|REQUESTED)$' <<<"$check_states"; then
            echo "  CI settled ($(wc -l <<<"$check_states" | tr -d ' ') checks) — proceeding."
            return 0
        fi

        if (( elapsed >= CI_TIMEOUT )); then
            # Proceed, do NOT fail. The next child can still do its work without
            # CI; killing the run because Actions is slow trades a large loss for
            # a small one. But it must be LOUD, so the child states the gate is
            # unknown rather than reporting a clean-looking review.
            echo "⚠ CI did not settle within ${CI_TIMEOUT}s — proceeding with gate state UNKNOWN." >&2
            CI_UNSETTLED=true
            return 0
        fi

        sleep "$CI_POLL"
        elapsed=$((elapsed + CI_POLL))
    done
}


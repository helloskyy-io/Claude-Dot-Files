#!/usr/bin/env bash
# Tier 1 master runner — Testing Standard § Tier 1: Master Runner.
#
# The single entry point for "run everything". Discovers component test
# directories by walking the source tree, dispatches to the Tier 2 framework
# runners in category order (unit -> integration -> e2e), logs each suite's
# output under testing/logs/, prints a summary table, and returns non-zero if
# any suite failed.
#
# Usage:
#   ./testing/run-all.sh                    # everything
#   ./testing/run-all.sh unit               # all unit tests, every component
#   ./testing/run-all.sh unit temporal      # one component's unit tests
#   ./testing/run-all.sh integration
#   ./testing/run-all.sh e2e
#
# Only the pytest suite runner exists, because pytest is the only test framework
# this repo has adopted. Testing Standard § Tier 2: "Only create suite runners
# for frameworks actually in use. Don't scaffold runners for frameworks you
# haven't adopted." A bash/bats runner gets added with the first .bats file, not
# before it.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUITES_DIR="$REPO_ROOT/testing/suites"
LOG_DIR="$REPO_ROOT/testing/logs"

ALL_CATEGORIES=(unit integration e2e)
FRAMEWORKS=(python)

CATEGORY="${1:-}"
COMPONENT="${2:-}"

if [[ -n "$CATEGORY" ]]; then
    valid=false
    for c in "${ALL_CATEGORIES[@]}"; do [[ "$c" == "$CATEGORY" ]] && valid=true; done
    if [[ "$valid" != true ]]; then
        echo "unknown category '$CATEGORY' — expected one of: ${ALL_CATEGORIES[*]}" >&2
        echo "usage: run-all.sh [unit|integration|e2e] [component]" >&2
        exit 2
    fi
    CATEGORIES=("$CATEGORY")
else
    CATEGORIES=("${ALL_CATEGORIES[@]}")
fi

mkdir -p "$LOG_DIR"

# Parallel arrays: bash 4 has no struct, and three aligned arrays read better
# here than encoding fields into one delimited string.
RESULT_LABEL=()
RESULT_STATUS=()
RESULT_LOG=()

ANY_FAILED=0
ANY_RAN=0

for category in "${CATEGORIES[@]}"; do
    for framework in "${FRAMEWORKS[@]}"; do
        runner="$SUITES_DIR/$framework.sh"
        label="$framework/$category"
        log_file="$LOG_DIR/${framework}-${category}${COMPONENT:+-$COMPONENT}.log"

        if [[ ! -x "$runner" ]]; then
            echo "FATAL: suite runner $runner is missing or not executable." >&2
            exit 1
        fi

        echo "==> $label${COMPONENT:+ (component: $COMPONENT)}"

        # Scoped suppression, single statement: the runner's exit code IS the
        # result we are collecting, so it must not abort the loop before the
        # remaining categories run or the summary prints.
        #
        # `|| rc=$?` and NOT `|| true` followed by ${PIPESTATUS[0]}. The obvious
        # form is silently wrong: `|| true` runs a simple command, which resets
        # PIPESTATUS to (0), so every failing suite reads back as exit 0. This
        # runner shipped that bug for exactly one test run and reported
        # "RESULT: PASSED" over a red pytest suite. `set -o pipefail` is what
        # makes this form correct — tee exits 0, so the pipeline's status is the
        # runner's own.
        rc=0
        "$runner" "$category" "$COMPONENT" 2>&1 | tee "$log_file" || rc=$?

        case "$rc" in
            0)
                RESULT_LABEL+=("$label"); RESULT_STATUS+=("PASS"); RESULT_LOG+=("$log_file")
                ANY_RAN=1
                ;;
            3)
                # Category genuinely absent from the tree. Reported, not hidden —
                # a silent skip and a pass look identical in a summary table.
                RESULT_LABEL+=("$label"); RESULT_STATUS+=("SKIP (no tests/$category)"); RESULT_LOG+=("$log_file")
                ;;
            *)
                RESULT_LABEL+=("$label"); RESULT_STATUS+=("FAIL (exit $rc)"); RESULT_LOG+=("$log_file")
                ANY_RAN=1
                ANY_FAILED=1
                ;;
        esac
        echo
    done
done

echo "======================================================================"
echo " Test summary${COMPONENT:+  —  component: $COMPONENT}"
echo "======================================================================"
printf ' %-22s %-26s %s\n' "SUITE" "RESULT" "LOG"
for i in "${!RESULT_LABEL[@]}"; do
    printf ' %-22s %-26s %s\n' \
        "${RESULT_LABEL[$i]}" "${RESULT_STATUS[$i]}" "${RESULT_LOG[$i]#"$REPO_ROOT"/}"
done
echo "======================================================================"

if [[ "$ANY_RAN" -eq 0 ]]; then
    # Every suite skipped. Exiting zero here would report a full green run for a
    # repo in which nothing executed — the precise failure Testing Standard
    # § Tier Enforcement calls out.
    echo "FATAL: no test suite actually ran. Nothing was verified." >&2
    exit 1
fi

if [[ "$ANY_FAILED" -ne 0 ]]; then
    echo "RESULT: FAILED"
    exit 1
fi

echo "RESULT: PASSED"

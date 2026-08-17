#!/usr/bin/env bash
# Tier 2 suite runner — pytest. Testing Standard § Tier 2: Framework Suite Runners.
#
# Discovers every `<unit>/tests/<category>/` directory holding pytest files and
# runs them in ONE pytest process scoped to that category. Category scoping is
# the point: running unit and integration tests in the same process is a known
# state-pollution source that the master runner masks and a flat invocation
# exposes.
#
# Usage:  python.sh <category> [component]
#
# Exit codes are a contract the master runner branches on:
#   0  the suite ran and passed
#   1  the suite ran and failed, OR it was asked to run tests that do not exist,
#      OR a test file was found sitting outside a category directory
#   3  nothing to run — no `tests/<category>/` directory anywhere in the tree
#
# The 1-vs-3 split matters. Exit 3 means the category is simply not present in
# this repo yet (`e2e` is the remaining one; `integration` arrived with the
# journal package, so it exits 0 or 1 now rather than 3). Exit 1 on an
# empty-but-present directory is deliberate: Testing
# Standard § Tier Enforcement — "a runner that finds no files ... and exits zero
# is indistinguishable from a passing run. Assert a non-zero expected count."

set -euo pipefail

CATEGORY="${1:-}"
COMPONENT="${2:-}"

if [[ -z "$CATEGORY" ]]; then
    echo "usage: python.sh <unit|integration|e2e> [component]" >&2
    exit 2
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "FATAL: $PYTHON_BIN not found — cannot run the python suite." >&2
    exit 1
fi
if ! "$PYTHON_BIN" -m pytest --version >/dev/null 2>&1; then
    # Loud, not skipped. A missing framework that exits zero reports a green
    # suite for tests that never ran.
    echo "FATAL: pytest is not installed for $PYTHON_BIN — install it before running the suite." >&2
    exit 1
fi

# Discovery runs from a RELATIVE root on purpose. This repo's own worktrees live
# under `.claude/worktrees/`, so an absolute-path find would see `/.claude/` in
# every single path and the exclusion below would match everything, discovering
# nothing while exiting cleanly.
cd "$REPO_ROOT"

# Paths that are never part of this repo's own test tree. Held in ONE array
# because two finds consume it: an exclusion added to the suite scan and
# forgotten in the orphan scan below would leave the two disagreeing about what
# the tree contains, which is precisely the failure this file is guarding.
#
# `.git/` and `.claude/` are anchored at the repo root because that is the only
# place they legitimately exist. Everything else is anchored with `*/` so it
# prunes at ANY depth: a virtualenv nested inside a component ships thousands of
# third-party `test_*.py` files, and an unpruned one would trip the orphan guard
# below and fail the whole run on vendored code nobody here wrote.
PRUNE=(
    -not -path "./.git/*"
    -not -path "./.claude/*"
    -not -path "*/archive/*"
    -not -path "*/__pycache__/*"
    -not -path "*/node_modules/*"
    -not -path "*/site-packages/*"
    -not -path "*/.venv/*"
    -not -path "*/venv/*"
)

# `find` must fail LOUD, and it cannot do that from a process substitution:
# `mapfile -t X < <(find ...)` discards the subshell's exit status entirely, so
# an unreadable directory would yield a PARTIAL walk that both scans below then
# treat as the whole tree. That is not a cosmetic loss. A truncated orphan scan
# under-reports orphans, and a truncated suite scan lands on the exit-3 path,
# which the master runner renders as SKIP — "nothing to run" printed over tests
# that exist. Assign first, check the status, and refuse to report a count
# derived from a walk that did not finish.
#
# The result lands in the global SCAN_OUTPUT rather than on stdout on purpose:
# `$(scan_or_die ...)` would run the function in a subshell, where `exit 1`
# terminates only that subshell and the script sails on — the identical trap
# this function exists to close.
SCAN_OUTPUT=""
scan_or_die() {
    local what="$1"
    shift
    if ! SCAN_OUTPUT="$(find "$@" | sed 's|^\./||' | sort)"; then
        echo "FATAL: the $what could not walk the tree — find exited non-zero." >&2
        echo "       Refusing to report a result derived from a partial walk." >&2
        exit 1
    fi
}

# `mapfile <<< ""` yields a one-element array holding an empty string, which
# would read as "one orphan found". Guard the empty case explicitly.
read_scan_into() {
    local -n _dest="$1"
    _dest=()
    if [[ -n "$SCAN_OUTPUT" ]]; then
        mapfile -t _dest <<< "$SCAN_OUTPUT"
    fi
}

# ORPHAN GUARD — Testing Standard § Discovery completeness (ratified 2026-07-24):
# a test that exists outside `run-all.sh` discovery is a DEFECT, not a gap; and
# § Purpose names an orphaned test file as a standards violation outright.
#
# Suite discovery below matches `*/tests/<category>` only, so a `test_*.py` one
# directory too high — `tests/test_foo.py` rather than `tests/unit/test_foo.py` —
# is invisible to it. Nothing else notices either: the file count printed below
# silently excludes the file and the run exits zero, which reads as "those tests
# passed". Not hypothetical — `tests/test_build_helper.py` and
# `tests/test_v1_parity.py` were both live in this state on `main`.
#
# Two deliberate properties:
#   - CATEGORY-INDEPENDENT. A file in `tests/unit/` is not an orphan during the
#     `integration` pass, so the scan asks only "is it inside ANY category
#     directory", never "is it inside THIS category".
#   - Runs BEFORE the exit-3 early return, so a tree whose only test files are
#     orphaned FAILS instead of reporting "nothing to run".
scan_or_die "orphan scan" . -type f -name 'test_*.py' \
    -not -path "*/tests/unit/*" \
    -not -path "*/tests/integration/*" \
    -not -path "*/tests/e2e/*" \
    "${PRUNE[@]}"
read_scan_into ORPHAN_TESTS

if [[ ${#ORPHAN_TESTS[@]} -gt 0 ]]; then
    echo "FATAL: ${#ORPHAN_TESTS[@]} test file(s) sit outside tests/{unit,integration,e2e}/" >&2
    echo "       and will never be executed by any runner:" >&2
    for orphan in "${ORPHAN_TESTS[@]}"; do echo "         - $orphan" >&2; done
    echo "       Move each into a category directory. A test that exists but never" >&2
    echo "       runs is worse than a missing one — it reports protection the suite" >&2
    echo "       does not have, and the summary table stays green over its absence." >&2
    exit 1
fi

scan_or_die "suite scan" . -type d -path "*/tests/$CATEGORY" "${PRUNE[@]}"
read_scan_into SUITE_DIRS

if [[ ${#SUITE_DIRS[@]} -eq 0 ]]; then
    echo "python/$CATEGORY: no tests/$CATEGORY directories in the tree — nothing to run"
    exit 3
fi

# Component filter: the unit that OWNS the tests directory, i.e. the parent of
# `tests`. `scripts/workflows/temporal/tests/unit` -> `temporal`.
if [[ -n "$COMPONENT" ]]; then
    FILTERED=()
    for dir in "${SUITE_DIRS[@]}"; do
        unit_dir="$(dirname "$(dirname "$dir")")"
        if [[ "$(basename "$unit_dir")" == "$COMPONENT" ]]; then
            FILTERED+=("$dir")
        fi
    done
    if [[ ${#FILTERED[@]} -eq 0 ]]; then
        # Asked for a specific component and it has nothing here. That is a
        # failure, not a skip: the caller named something that does not exist.
        echo "FATAL: no tests/$CATEGORY directory for component '$COMPONENT'." >&2
        echo "       discovered: ${SUITE_DIRS[*]}" >&2
        exit 1
    fi
    SUITE_DIRS=("${FILTERED[@]}")
fi

TEST_FILE_COUNT=0
for dir in "${SUITE_DIRS[@]}"; do
    count=$(find "$dir" -name 'test_*.py' -type f -not -path '*/__pycache__/*' | wc -l)
    TEST_FILE_COUNT=$((TEST_FILE_COUNT + count))
done

if [[ "$TEST_FILE_COUNT" -eq 0 ]]; then
    echo "FATAL: ${#SUITE_DIRS[@]} tests/$CATEGORY director(y|ies) exist but contain no test_*.py files." >&2
    echo "       An empty tier that exits zero reports a protection that does not exist." >&2
    exit 1
fi

echo "python/$CATEGORY: ${TEST_FILE_COUNT} test file(s) across ${#SUITE_DIRS[@]} director(y|ies)"
for dir in "${SUITE_DIRS[@]}"; do echo "  - $dir"; done

# `|| rc=$?` rather than `set +e`: the suppression is scoped to this single
# statement and the exit code is propagated below. Disabling errexit for the
# rest of the file would detach the runner's pass/fail detection from the
# assertions it runs, which Testing Standard § No flag may make a suite unable
# to report failure forbids outright.
rc=0
"$PYTHON_BIN" -m pytest "${SUITE_DIRS[@]}" --tb=short "${@:3}" || rc=$?

# pytest exit 5 == "no tests collected". Files were present, so collection
# silently dropped them (an import error swallowed by a conftest, a renamed
# discovery pattern). That is a failure, never a pass.
if [[ $rc -eq 5 ]]; then
    echo "FATAL: pytest collected 0 tests from $TEST_FILE_COUNT file(s) — collection is broken." >&2
    exit 1
fi

# NORMALIZE. Never let a raw pytest exit code reach the caller, because pytest's
# own code 3 ("internal error") collides with this script's sentinel 3 ("no such
# category in the tree") and the master runner reads 3 as a SKIP — so a pytest
# crash would be reported as "nothing to run" and the overall run would pass.
# pytest 1/2/3/4 are all failures (tests failed / interrupted / internal error /
# usage error); collapse every one of them to 1 so the sentinel stays unambiguous.
if [[ $rc -ne 0 ]]; then
    echo "python/$CATEGORY: pytest exited $rc" >&2
    exit 1
fi

exit 0

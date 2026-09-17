#!/usr/bin/env bash
# js.sh — the JavaScript suite: `node --test` over every `tests/js/*.test.mjs`.
#
# Contract with run-all.sh: exit 0 PASS · exit 3 SKIP (no tests for this
# category) · anything else FAIL.
#
# REFUSES LOUDLY UNDER NODE < 18, and that is a FAIL, not a SKIP. `node --test`
# and the `node:test` assert module arrived in 18. A runtime too old to run the
# tests is not "no tests for this category" — the tests exist and did not run —
# and reporting it as a skip is the green-run-that-ran-nothing this suite tier
# exists to prevent. A dev host with an old `node` on PATH sets NODE_BIN once,
# the way python.sh's PYTHON_BIN works; CI installs a current Node before the
# suite. The refusal names the override so nobody has to read this to find it.
#
# Only `unit` has JavaScript tests today. Other categories exit 3 by name.

set -euo pipefail

CATEGORY="${1:-}"
COMPONENT="${2:-}"

if [[ -z "$CATEGORY" ]]; then
    echo "usage: js.sh <unit|integration|e2e> [component]" >&2
    exit 2
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NODE_BIN="${NODE_BIN:-node}"
MIN_MAJOR=18

if [[ "$CATEGORY" != "unit" ]]; then
    echo "js/$CATEGORY: no JavaScript tests in this category"
    exit 3
fi

# Every tests/js directory, or the one component's.
mapfile -t TEST_DIRS < <(
    find "$REPO_ROOT/scripts" -type d -path "*/tests/js" -not -path "*/node_modules/*" \
        ${COMPONENT:+-path "*/$COMPONENT/*"} 2>/dev/null | sort
)
if [[ ${#TEST_DIRS[@]} -eq 0 ]]; then
    echo "js/unit: no tests/js directory found${COMPONENT:+ for component $COMPONENT}"
    exit 3
fi

if ! command -v "$NODE_BIN" >/dev/null 2>&1; then
    echo "REFUSED: no Node runtime — '$NODE_BIN' not found. The JavaScript tests exist" >&2
    echo "         (${#TEST_DIRS[@]} tests/js director$([[ ${#TEST_DIRS[@]} -eq 1 ]] && echo y || echo ies)) and did not run." >&2
    echo "         Set NODE_BIN=/path/to/node (>= $MIN_MAJOR), or install one on PATH." >&2
    exit 1
fi

MAJOR="$("$NODE_BIN" --version | sed -E 's/^v([0-9]+).*/\1/')"
if [[ -z "$MAJOR" || "$MAJOR" -lt "$MIN_MAJOR" ]]; then
    echo "REFUSED: $NODE_BIN is $("$NODE_BIN" --version) and this suite needs Node >= $MIN_MAJOR" >&2
    echo "         (node --test and node:test arrived in 18). The tests exist and did not run." >&2
    echo "         Set NODE_BIN=/path/to/node (>= $MIN_MAJOR), or put one first on PATH." >&2
    exit 1
fi

FILES=()
for d in "${TEST_DIRS[@]}"; do
    while IFS= read -r f; do FILES+=("$f"); done < <(find "$d" -maxdepth 1 -name '*.test.mjs' | sort)
done
if [[ ${#FILES[@]} -eq 0 ]]; then
    echo "js/unit: tests/js directories exist but hold no *.test.mjs files — that is a defect, not a skip" >&2
    exit 1
fi

echo "js/unit: $NODE_BIN $("$NODE_BIN" --version) · ${#FILES[@]} file(s)"
exec "$NODE_BIN" --test "${FILES[@]}"

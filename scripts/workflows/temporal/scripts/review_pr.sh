#!/usr/bin/env bash
# review-pr — kickoff shim for the Python workflow.
#
# Thin by design: resolves the interpreter and passes every argument through
# untouched, so the CLI contract is defined in exactly one place
# (run_review_pr.py) rather than duplicated in bash.
#
# Usage:
#   ./review-pr.sh --pr <N>
#   ./review-pr.sh --pr <N> --type research --verbose
#   ./review-pr.sh --pr <N> --dry-run        # render only: no model, no spend
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_review_pr.py" "$@"

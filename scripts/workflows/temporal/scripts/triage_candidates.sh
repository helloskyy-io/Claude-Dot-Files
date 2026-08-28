#!/usr/bin/env bash
# triage-candidates — kickoff shim for the Python workflow.
#
# Thin by design: it resolves the interpreter and hands every argument through
# untouched. Argument parsing lives in run_triage_candidates.py so there is
# exactly one place that defines the CLI contract.
#
# Usage:
#   ./triage_candidates.sh --verbose
#   ./triage_candidates.sh --candidates tracked/candidates
#   ./triage_candidates.sh --pr 42 --verbose
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_triage_candidates.py" "$@"

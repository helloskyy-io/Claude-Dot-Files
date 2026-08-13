#!/usr/bin/env bash
# plan-candidates — kickoff shim for the Python workflow.
#
# Thin by design: it resolves the interpreter and hands every argument through
# untouched. Argument parsing lives in run_plan_candidates.py so there is
# exactly one place that defines the CLI contract.
#
# Usage:
#   ./plan_candidates.sh --verbose
#   ./plan_candidates.sh --candidates docs/standards/architecture/research/candidates.md
#   ./plan_candidates.sh --pr 42 --verbose
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_plan_candidates.py" "$@"

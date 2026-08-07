#!/usr/bin/env bash
# plan-master — kickoff shim for the Python workflow.
#
# Thin by design: it resolves the interpreter and hands every argument through
# untouched. Argument parsing lives in run_plan_master.py so there is exactly
# one place that defines the CLI contract.
#
# Usage:
#   ./plan_master.sh
#   ./plan_master.sh --pr 43 --verbose
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_plan_master.py" "$@"

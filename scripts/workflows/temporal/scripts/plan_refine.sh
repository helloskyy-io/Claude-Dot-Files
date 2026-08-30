#!/usr/bin/env bash
# plan-refine — kickoff shim for the Python workflow.
#
# Thin by design: it resolves the interpreter and hands every argument through
# untouched. Argument parsing lives in run_plan_refine.py so there is exactly
# one place that defines the CLI contract.
#
# Usage:
#   ./plan_refine.sh docs/development/memory-management-framework
#   ./plan_refine.sh docs/development/persistent-memory-protocol --dry-run
#   ./plan_refine.sh docs/development/mcp-servers --pr 42 --verbose
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_plan_refine.py" "$@"

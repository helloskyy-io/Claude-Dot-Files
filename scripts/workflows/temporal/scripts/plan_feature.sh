#!/usr/bin/env bash
# plan-feature — kickoff shim for the Python workflow.
#
# Thin by design: it resolves the interpreter and hands every argument through
# untouched. Argument parsing lives in run_plan_feature.py so there is exactly
# one place that defines the CLI contract.
#
# Usage:
#   ./plan_feature.sh docs/development/fleet-reliability
#   ./plan_feature.sh docs/development/managed-configuration --dry-run
#   ./plan_feature.sh docs/development/mcp-servers --pr 42 --verbose
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_plan_feature.py" "$@"

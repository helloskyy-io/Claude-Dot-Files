#!/usr/bin/env bash
# plan — kickoff shim for the planning PARENT.
#
# Thin by design: it resolves the interpreter and hands every argument through
# untouched. Argument parsing lives in run_plan.py so there is exactly one
# place that defines the CLI contract.
#
# Usage:
#   ./plan.sh docs/development/workflow-decomposition
#   ./plan.sh docs/development/workflow-decomposition --pr 145 --verbose
#   ./plan.sh docs/development/mcp-servers --task-file /tmp/claude-<name>.md
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_plan.py" "$@"

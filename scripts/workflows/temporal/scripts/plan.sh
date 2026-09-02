#!/usr/bin/env bash
# plan — kickoff shim for the planning PARENT.
#
# Thin by design: it resolves the interpreter and hands every argument through
# untouched. Argument parsing lives in run_plan.py so there is exactly one
# place that defines the CLI contract.
#
# Usage:
#   ./plan.sh development/edge-assistant/workflow-decomposition --repo /opt/skyy-net/skyynet-master-planning
#   ./plan.sh development/edge-assistant/workflow-decomposition --repo /opt/skyy-net/skyynet-master-planning --pr 145 --verbose
#   ./plan.sh development/edge-assistant/mcp-servers --repo /opt/skyy-net/skyynet-master-planning --task-file /tmp/claude-<name>.md
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_plan.py" "$@"

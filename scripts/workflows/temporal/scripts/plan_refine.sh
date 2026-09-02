#!/usr/bin/env bash
# plan-refine — kickoff shim for the Python workflow.
#
# Thin by design: it resolves the interpreter and hands every argument through
# untouched. Argument parsing lives in run_plan_refine.py so there is exactly
# one place that defines the CLI contract.
#
# Usage:
#   ./plan_refine.sh development/edge-assistant/memory-management-framework --repo /opt/skyy-net/skyynet-master-planning
#   ./plan_refine.sh development/edge-assistant/persistent-memory-protocol --repo /opt/skyy-net/skyynet-master-planning --dry-run
#   ./plan_refine.sh development/edge-assistant/temporal-integration --repo /opt/skyy-net/skyynet-master-planning --pr 42 --verbose
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_plan_refine.py" "$@"

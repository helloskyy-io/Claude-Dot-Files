#!/usr/bin/env bash
# plan-draft — kickoff shim for the Python workflow.
#
# Thin by design: it resolves the interpreter and hands every argument through
# untouched. Argument parsing lives in run_plan_draft.py so there is exactly
# one place that defines the CLI contract.
#
# Usage:
#   ./plan_draft.sh development/edge-assistant/local-ai-offloading --repo /opt/skyy-net/skyynet-master-planning
#   ./plan_draft.sh development/edge-assistant/cross-device-sync --repo /opt/skyy-net/skyynet-master-planning --dry-run
#   ./plan_draft.sh development/edge-assistant/mcp-servers --repo /opt/skyy-net/skyynet-master-planning --pr 42 --verbose
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_plan_draft.py" "$@"

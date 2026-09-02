#!/usr/bin/env bash
# plan-sprint — kickoff shim for the Python workflow.
#
# Thin by design: it resolves the interpreter and hands every argument through
# untouched. Argument parsing lives in run_plan_sprint.py so there is exactly one
# place that defines the CLI contract.
#
# Usage:
#   ./plan_sprint.sh development/<component> --verbose
#   ./plan_sprint.sh development/<component> --sprint development/sprints.md
#   ./plan_sprint.sh development/<component> --pr 42 --verbose
#   ./plan_sprint.sh development/<component> --repo /opt/skyy-net/skyynet-master-planning --dry-run
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_plan_sprint.py" "$@"

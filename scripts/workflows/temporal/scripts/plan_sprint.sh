#!/usr/bin/env bash
# plan-sprint — kickoff shim for the Python workflow.
#
# Thin by design: it resolves the interpreter and hands every argument through
# untouched. Argument parsing lives in run_plan_sprint.py so there is exactly one
# place that defines the CLI contract.
#
# Usage:
#   ./build.sh "description of what to revise"
#   ./build.sh --task-file /tmp/claude-task.md --verbose
#   ./build.sh "description" --pr 42
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_plan_sprint.py" "$@"

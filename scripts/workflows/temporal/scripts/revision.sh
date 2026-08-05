#!/usr/bin/env bash
# revision — kickoff shim for the Python workflow.
#
# Thin by design: it resolves the interpreter and hands every argument through
# untouched. Argument parsing lives in run_revision.py so there is exactly one
# place that defines the CLI contract.
#
# Usage:
#   ./revision.sh "description of what to revise"
#   ./revision.sh --task-file /tmp/claude-task.md --verbose
#   ./revision.sh "description" --pr 42
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_revision.py" "$@"

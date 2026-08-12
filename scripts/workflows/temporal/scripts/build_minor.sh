#!/usr/bin/env bash
# build-minor — kickoff shim for the Python workflow.
#
# Thin by design: it resolves the interpreter and hands every argument through
# untouched. Argument parsing lives in run_build_minor.py so there is exactly one
# place that defines the CLI contract.
#
# Usage:
#   ./build_minor.sh "description of the scoped change"
#   ./build_minor.sh --task-file /tmp/claude-task.md --verbose
#   ./build_minor.sh --pr 42 --task-file /tmp/claude-runway.md
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_build_minor.py" "$@"

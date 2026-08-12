#!/usr/bin/env bash
# research — kickoff shim for the Python workflow.
#
# Thin by design: it resolves the interpreter and hands every argument through
# untouched. Argument parsing lives in run_research.py so there is exactly one
# place that defines the CLI contract.
#
# Usage:
#   ./research.sh docs/standards/architecture/research
#   ./research.sh docs/development/<component>/research --task-file /tmp/claude-task.md --verbose
#   ./research.sh docs/standards/architecture/research --refresh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_research.py" "$@"

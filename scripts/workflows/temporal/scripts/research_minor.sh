#!/usr/bin/env bash
# research-minor — kickoff shim for the Python workflow.
#
# Thin by design: it resolves the interpreter and hands every argument through
# untouched. Argument parsing lives in run_research_minor.py so there is exactly
# one place that defines the CLI contract.
#
# ONE topic, ONE paper, plus the synthesis a planner reads — no topic list and
# no fan-out. For a topic the full research pool is overkill for. Reach for the
# full research.sh when the subject needs several papers on separate subjects.
#
# Usage:
#   ./research_minor.sh docs/development/<component>/research
#   ./research_minor.sh docs/development/<component>/research --task-file /tmp/claude-task.md --verbose
#   ./research_minor.sh docs/development/<component>/research --pr 42
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_research_minor.py" "$@"

#!/usr/bin/env bash
# plan-revision — kickoff shim for the Python workflow.
#
# Thin by design: it resolves the interpreter and hands every argument through
# untouched. Argument parsing lives in run_plan_revision.py so there is exactly
# one place that defines the CLI contract.
#
# Usage:
#   ./plan_revision.sh "update roadmap to reflect Phase 4 completion"
#   ./plan_revision.sh "description" "additional context"
#   ./plan_revision.sh --pr 18 --task-file /tmp/claude-context.md "description"
#   ./plan_revision.sh --verbose "realign roadmap milestones"
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_plan_revision.py" "$@"

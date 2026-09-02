#!/usr/bin/env bash
# build-draft-minor — kickoff shim for the Python workflow.
#
# Thin by design: it resolves the interpreter and hands every argument through
# untouched. Argument parsing lives in run_build_draft_minor.py so there is exactly one
# place that defines the CLI contract.
#
# THIS CHILD RUNS STANDALONE AND UNDER ITS PARENT, EQUALLY WELL. The parent
# imports the core function and calls it directly; this shim exists so a person
# can exercise the same child without paying for the whole chain. Standalone is
# an interface, not a recovery hatch — `workflow-scripts.md` § File Conventions.
#
# Usage:
#   ./build_draft_minor.sh "description of the scoped change"
#   ./build_draft_minor.sh --task-file /tmp/claude-<name>.md --verbose
#   ./build_draft_minor.sh --dry-run "description"   # no model, no spend
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_build_draft_minor.py" "$@"

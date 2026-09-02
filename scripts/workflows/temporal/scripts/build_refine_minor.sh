#!/usr/bin/env bash
# build-refine-minor — kickoff shim for the Python workflow.
#
# Thin by design: it resolves the interpreter and hands every argument through
# untouched. Argument parsing lives in run_build_refine_minor.py so there is exactly one
# place that defines the CLI contract.
#
# THIS CHILD RUNS STANDALONE AND UNDER ITS PARENT, EQUALLY WELL. The parent
# imports the core function and calls it directly; this shim exists so a person
# can exercise the same child without paying for the whole chain. Standalone is
# an interface, not a recovery hatch — `workflow-scripts.md` § File Conventions.
#
# Usage:
#   ./build_refine_minor.sh --pr 42 "the ORIGINAL task"
#   ./build_refine_minor.sh --pr 42 --task-file /tmp/claude-<name>.md --correction-pass
#   ./build_refine_minor.sh --pr 42 --dry-run   # no model, no spend
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_build_refine_minor.py" "$@"

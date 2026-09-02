#!/usr/bin/env bash
# build-draft — kickoff shim for the Python workflow.
#
# Thin by design: it resolves the interpreter and hands every argument through
# untouched. Argument parsing lives in run_build_draft.py so there is exactly one
# place that defines the CLI contract.
#
# THIS CHILD RUNS STANDALONE AND UNDER ITS PARENT, EQUALLY WELL. The parent
# imports the core function and calls it directly; this shim exists so a person
# can exercise the same child without paying for the whole chain. Standalone is
# an interface, not a recovery hatch — `workflow-scripts.md` § File Conventions.
#
# Usage:
#   ./build_draft.sh "description of the change"
#   ./build_draft.sh --task-file /tmp/claude-<name>.md --verbose
#   ./build_draft.sh --phase /path/to/phase.md --repo /path/to/repo
#   ./build_draft.sh --dry-run "description"   # no model, no worktree, no spend
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_build_draft.py" "$@"

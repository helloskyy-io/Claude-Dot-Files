#!/usr/bin/env bash
# research-draft — kickoff shim for the Python workflow.
#
# Thin by design: it resolves the interpreter and hands every argument through
# untouched. Argument parsing lives in run_research_draft.py so there is exactly one
# place that defines the CLI contract.
#
# THIS CHILD RUNS STANDALONE AND UNDER ITS PARENT, EQUALLY WELL. The parent
# imports the core function and calls it directly; this shim exists so a person
# can exercise the same child without paying for the whole chain. Standalone is
# an interface, not a recovery hatch — `workflow-scripts.md` § File Conventions.
#
# Usage:
#   ./research_draft.sh development/<component>/research
#   ./research_draft.sh development/<component>/research --task-file /tmp/claude-<name>.md -v
#   ./research_draft.sh development/<component>/research --dry-run   # no model, no spend
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_research_draft.py" "$@"

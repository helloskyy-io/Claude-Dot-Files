#!/usr/bin/env bash
# research — kickoff shim for the Python workflow.
#
# Thin by design: it resolves the interpreter and hands every argument through
# untouched. Argument parsing lives in run_research.py so there is exactly one
# place that defines the CLI contract.
#
# THE POOL IS RESOLVED AGAINST THE REPO ROOT, so it is written repo-relative
# here. An absolute path into another checkout needs `--repo <that repo>` too, or
# `resolve_operator_paths` refuses it as escaping the tree it was pointed at.
#
# Usage:
#   ./research.sh development/<component>/research
#   ./research.sh development/<component>/research --task-file /tmp/claude-<name>.md --verbose
#   ./research.sh development/<component>/research --repo /opt/skyy-net/skyynet-master-planning
#   ./research.sh development/<component>/research --dry-run
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_research.py" "$@"

#!/usr/bin/env bash
# research-refine — kickoff shim for the Python workflow.
#
# Thin by design: it resolves the interpreter and hands every argument through
# untouched. Argument parsing lives in run_research_refine.py so there is exactly one
# place that defines the CLI contract.
#
# THIS CHILD RUNS STANDALONE AND UNDER ITS PARENT, EQUALLY WELL. The parent
# imports the core function and calls it directly; this shim exists so a person
# can exercise the same child without paying for the whole chain. Standalone is
# an interface, not a recovery hatch — `workflow-scripts.md` § File Conventions.
#
# THE POOL IS RESOLVED AGAINST THE REPO ROOT, so it is written repo-relative
# here. This repo has no `development/` tree — the pools live in the planning
# repo, so every line below needs `--repo` unless you are standing in one. An
# absolute path into another checkout needs `--repo <that repo>` too, or
# `resolve_operator_paths` refuses it as escaping the tree it was pointed at.
#
# Usage:
#   ./research_refine.sh development/<component>/research --pr 42
#   ./research_refine.sh development/<component>/research --pr 42 --correction-pass
#   ./research_refine.sh development/<component>/research --pr 42 --dry-run
#   ./research_refine.sh development/<component>/research --pr 42 --repo /opt/skyy-net/skyynet-master-planning
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_research_refine.py" "$@"

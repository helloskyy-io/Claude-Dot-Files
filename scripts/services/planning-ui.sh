#!/usr/bin/env bash
# planning-ui.sh — the planning-corpus viewer: derive a planning repository's
# views, check the committed ones are current, or serve the diagram pages.
#
# Usage (from the planning repository, or with --repo-root <path>):
#   planning-ui.sh                          # generate development/derived/
#   planning-ui.sh --check                  # exit 1 if the committed views drifted
#   planning-ui.sh serve                    # serve the pages; bind/port from config.yaml
#   planning-ui.sh --print-default-config   # the config.yaml section the scaffold writes
#
# THIS IS THE ONE ENTRY POINT, AND IT LOCATES THE PACKAGE ITSELF. The Python
# under planning_ui/ is never installed — it is read out of this checkout,
# which sits at a different path on every machine — so a caller that ran
# `python3 -m planning_ui` would first have to know where the tooling is. The
# git hook, the scaffolded CI step and an operator all run this file instead,
# and this file resolves its own location (through a symlink, hence readlink
# -f) so none of them carry a PYTHONPATH. Standard library only: nothing to
# install on the host that runs it.
#
# See /opt/skyy-net/skyynet-master-planning/standards/services/services.md for the conventions this script follows.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"

if ! command -v python3 &>/dev/null; then
    echo "Error: 'python3' not found in PATH" >&2
    exit 1
fi

PYTHONPATH="${SCRIPT_DIR}${PYTHONPATH:+:$PYTHONPATH}" exec python3 -m planning_ui "$@"

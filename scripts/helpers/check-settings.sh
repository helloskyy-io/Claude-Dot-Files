#!/usr/bin/env bash
#
# check-settings.sh — validate config/settings.json before it reaches the
# merge path.
#
# WHY THIS EXISTS: config/settings.json configures the permission model and
# the hooks. install.sh only symlinks it — nothing anywhere parses it as a
# check — so a malformed file, or a hook path that no longer resolves, can
# mean the hooks never load at all: the only control operating during an
# autonomous run, silently gone. See check_settings.py's own docstring for
# the full CATCHES / DOES NOT CATCH breakdown and why the hook-path check
# tokenises rather than substring-matches.
#
# This is the local-runnable half of the guard the `suite` job runs — the
# CI step calls this same script, so a red run here is a red run there.
#
# Run as a ship gate before committing config/settings.json or config/hooks/
# changes:
#   scripts/helpers/check-settings.sh
# Exit 0 = clean; exit 1 = validation failed.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

python3 "${SCRIPT_DIR}/check_settings.py" "${REPO_ROOT}/config/settings.json" "${REPO_ROOT}/config/hooks"

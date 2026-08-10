#!/usr/bin/env bash
#
# config-value.sh — read one value out of config.yaml's <map>: block.
#
# Usage:  config-value.sh <map> <key>
#   e.g.  MAX_TURNS="$("${SCRIPT_DIR}/../common/config-value.sh" max_turns build-draft)"
#
# INVOKED, NOT SOURCED. Sourcing would need the caller to have already set up
# its environment; this is called at the top of a workflow script, before that
# has happened. Command substitution keeps it usable from any line.
#
# WHY THIS EXISTS: operational config used to be declared inside the workflow
# executables themselves, which meant the only way for another fleet to share a
# value was to parse the executable. The Python tree did that — a regex over
# `children/*.sh` at runtime — so deleting the bash fleet would have stopped
# the Python fleet from starting. Config belongs in the config file; both
# fleets read it; neither reads the other.
#
# FAILS LOUD, ALWAYS. A missing key is an error, never a default. A workflow
# silently running at someone else's turn budget is worse than one that does
# not start, because the cap is only observable once the run has already
# burned it.

set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "config-value.sh: usage: config-value.sh <map> <key> (got $# args)" >&2
    exit 2
fi

_MAP="$1"
_KEY="$2"
_CDF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
_CONFIG="${_CDF_ROOT}/config.yaml"

if ! command -v yq &>/dev/null; then
    echo "config-value.sh: 'yq' is required to read ${_CONFIG} but is not in PATH" >&2
    exit 1
fi

if [[ ! -f "${_CONFIG}" ]]; then
    echo "config-value.sh: config.yaml not found at ${_CONFIG}" >&2
    exit 1
fi

# `// ""` turns a missing key into an empty string rather than the literal
# "null" yq would otherwise print — which would sail through as a value.
_VALUE="$(yq -r ".${_MAP}.\"${_KEY}\" // \"\"" "${_CONFIG}")"

if [[ -z "${_VALUE}" ]]; then
    echo "config-value.sh: no '${_KEY}' in the '${_MAP}:' map of ${_CONFIG}." >&2
    echo "  Add it there — do not hardcode a value at the call site." >&2
    exit 1
fi

printf '%s\n' "${_VALUE}"

#!/usr/bin/env bash
#
# lint-prompts.sh — catch prompt-construction landmines that `bash -n` cannot see.
#
# THE CLASS: an UNESCAPED backtick inside a double-quoted PROMPT="..." string
# triggers command substitution at *runtime*. bash tries to execute the
# backtick's contents as a command during the assignment — the script dies
# (exit 127 for a non-command like `run_in_background: false`; silent prompt
# corruption or a stdin-hang for a real command like `wc -l`). `bash -n` passes
# it because it is syntactically valid; it only fails when the line executes,
# which no syntax check reaches.
#
# THE FIX ENFORCED HERE: inside a double-quoted string, every literal backtick
# must be escaped (\`). Backticks inside SINGLE-quoted heredocs (<<'EOF') are
# already literal and safe — this lint strips those bodies before checking.
#
# Run as a ship gate before committing workflow prompt changes:
#   scripts/helpers/lint-prompts.sh
# Exit 0 = clean; exit 1 = landmines found (with file:line locations).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WF_DIR="${SCRIPT_DIR}/../workflows"

fail=0
for f in "$WF_DIR"/*.sh "$WF_DIR"/lib/*.sh; do
    [[ -e "$f" ]] || continue

    # awk: emit only lines OUTSIDE single-quoted heredocs, with escaped
    # backticks (\`) removed. Any backtick surviving in the emitted text is an
    # unescaped backtick in a command-substitutable region → a landmine.
    hits=$(awk '
        {
            line = $0
            if (inh) { if (line == delim) inh = 0; next }
            if (match(line, /<<'"'"'[A-Za-z_0-9]+'"'"'/)) {
                m = substr(line, RSTART, RLENGTH)
                gsub(/<<'"'"'/, "", m); gsub(/'"'"'/, "", m)
                inh = 1; delim = m; next
            }
            if (line ~ /^[[:space:]]*#/) next   # bash comment / markdown header line — backticks here are not evaluated
            stripped = line
            gsub(/\\`/, "", stripped)      # drop escaped backticks — those are safe
            if (stripped ~ /`/) print NR": "line
        }
    ' "$f" || true)

    if [[ -n "$hits" ]]; then
        echo "✗ ${f#"$WF_DIR"/} — unescaped backtick(s) in a command-substitutable region:"
        echo "$hits" | sed 's/^/      /'
        fail=1
    fi
done

if [[ $fail -eq 0 ]]; then
    echo "✓ prompt lint clean — no unescaped backticks outside single-quoted heredocs"
fi
exit $fail

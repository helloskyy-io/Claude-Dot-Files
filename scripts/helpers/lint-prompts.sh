#!/usr/bin/env bash
#
# lint-prompts.sh — catch prompt-construction landmines that `bash -n` cannot see.
#
# THE CLASS: "prompt strings are code." A workflow's PROMPT is a double-quoted
# bash assignment (or an unquoted heredoc), so anything bash treats specially —
# backticks, $( ), stray double quotes — is EVALUATED at runtime. Two fleet
# outages in one day came from this class:
#
#   1. Unescaped BACKTICK: `run_in_background: false` ran as a command -> 127.
#      `bash -n` passes (syntactically valid).
#   2. Unescaped DOUBLE QUOTES around a phrase containing whitespace:
#      "deferred until a second adopter exists" closed PROMPT mid-string; the
#      remaining prose parsed as commands -> `until: command not found` -> 127.
#      `bash -n` ALSO passes, because the stray quotes BALANCE (even count) —
#      the file is valid bash that simply means something else.
#
# WHY THIS IS AN EXECUTION CHECK, NOT A PATTERN CHECK: case 2 proves a
# per-vector pattern list is unsound — the gate built for backticks certified a
# file that could not launch. Parsing is not enough either (`bash -n` on the
# block passes: it IS valid syntax). The only check that catches every vector,
# including ones we have not met yet, is to actually CONSTRUCT each prompt in a
# sandbox and see whether bash does anything other than assign a string.
#
# SANDBOX: each block runs under `env -i` with a PATH containing ONLY `cat`
# (needed by heredoc-form prompts). Any other command — whether from a stray
# backtick, a $( ), or prose parsed after a broken quote — is not found, exits
# non-zero, and is reported. Nothing from the real system can execute.
#
# Run as a ship gate before committing workflow prompt changes:
#   scripts/helpers/lint-prompts.sh
# Exit 0 = clean; exit 1 = landmines found.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WF_DIR="${SCRIPT_DIR}/../workflows"
fail=0

# --- sandbox: only `cat` is reachable -----------------------------------------
SANDBOX="$(mktemp -d)"
trap 'rm -rf "$SANDBOX"' EXIT
ln -sf "$(command -v cat)" "$SANDBOX/cat"
BASH_BIN="$(command -v bash)"

# --- Pass 1 (static): unescaped backticks, for precise line numbers -----------
# Fast, and pinpoints the offending line. Pass 2 is the real net.
for f in "$WF_DIR"/*.sh "$WF_DIR"/lib/*.sh; do
    [[ -e "$f" ]] || continue
    hits=$(awk '
        {
            line = $0
            if (inh) { if (line == delim) inh = 0; next }
            if (match(line, /<<'"'"'[A-Za-z_0-9]+'"'"'/)) {
                m = substr(line, RSTART, RLENGTH)
                gsub(/<<'"'"'/, "", m); gsub(/'"'"'/, "", m)
                inh = 1; delim = m; next
            }
            if (line ~ /^[[:space:]]*#/) next
            stripped = line
            gsub(/\\`/, "", stripped)
            if (stripped ~ /`/) print NR": "line
        }
    ' "$f")
    if [[ -n "$hits" ]]; then
        echo "✗ ${f#"$WF_DIR"/} — unescaped backtick(s):"
        echo "$hits" | sed 's/^/      /'
        fail=1
    fi
done

# --- Pass 2 (execution): construct every prompt block in the sandbox ----------
for f in "$WF_DIR"/*.sh; do
    [[ -e "$f" ]] || continue
    while IFS= read -r s; do
        [[ -n "$s" ]] || continue
        startline=$(sed -n "${s}p" "$f")
        if [[ "$startline" == *'=$(cat <<'* ]]; then
            # heredoc form: PROMPT=$(cat <<EOF ... EOF )  — ends at a lone ')'
            e=$(awk -v s="$s" 'NR>s && /^\)/ {print NR; exit}' "$f")
            [[ -n "$e" ]] || continue
            block=$(sed -n "${s},${e}p" "$f")
        else
            # inline form: PROMPT="…" — ends before the next real shell statement.
            # Terminators are deliberately NARROW (`echo` / `run_claude` / a lone
            # `)`): a loose pattern like `^[[:space:]]*\(` matches PROSE such as
            # "(1) STATE THE CONTEXT…" and silently truncates the block, which
            # then fails to construct for the wrong reason.
            e=$(awk -v s="$s" 'NR>s && (/^[[:space:]]*(echo|run_claude)/ || /^\)/) {print NR; exit}' "$f")
            [[ -n "$e" ]] || e=$(( $(wc -l < "$f") + 1 ))
            block=$(sed -n "${s},$((e-1))p" "$f")
        fi

        # Invoke bash by ABSOLUTE path — the sandbox PATH deliberately contains
        # only `cat`, so `bash` itself would not resolve through it.
        if ! err=$(env -i PATH="$SANDBOX" "$BASH_BIN" -c "set -e
$block" 2>&1); then
            echo "✗ $(basename "$f") — prompt block starting at line ${s} does NOT construct:"
            echo "$err" | sed 's/^/      /'
            echo "      (error line numbers are relative to the block; block starts at file line ${s})"
            fail=1
        fi
    done < <(grep -nE '^[[:space:]]*[A-Za-z_]*PROMPT=("|\$\(cat <<)' "$f" | cut -d: -f1)
done

if [[ $fail -eq 0 ]]; then
    echo "✓ prompt lint clean — every prompt block constructs as a plain string"
fi
exit $fail

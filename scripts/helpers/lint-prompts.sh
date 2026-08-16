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

# --- what this run actually CHECKED -------------------------------------------
# THE SUMMARY AT THE BOTTOM IS BUILT FROM THESE. It used to be a literal —
# "every prompt block constructs, every MODEL_KEY resolves" — printed whenever
# nothing had failed, while Pass 3 was guarded on `yq` being installed. On a
# machine without yq the pass did not run and the line still claimed it had
# (issue #57). The class Pass 3 catches is a RENAME: revision.sh ->
# revision-minor.sh moved the script and its config.yaml key apart, leaving the
# workflow silently unlaunchable. A rename is exactly what an operator runs this
# gate before committing, so the false claim landed on its own use case.
#
# The remedy is structural rather than a reworded string: each pass RECORDS what
# it examined, and the report is derived from that record. A pass that does not
# run cannot write a count, so it cannot be claimed.
#
# COUNTS, NOT BOOLEANS, and that is the second half of the fix. Both scan
# populations come from a glob, and a glob that matches nothing yields a loop
# that examines zero files and falls through to a clean report — the same defect
# one layer down. The counts are printed so the claim is checkable by eye, and
# asserted non-zero below so a vacuous scan is a failure rather than a tick.
p1_files=0        # Pass 1: files scanned for unescaped backticks
p2_files=0        # Pass 2: files containing at least one prompt block
p2_blocks=0       # Pass 2: prompt blocks constructed in the sandbox
p3_keys=0         # Pass 3: MODEL_KEYs resolved against config.yaml
p3_seen=0         # Pass 3: MODEL_KEY declarations found — its OWN population
p3_skip=""        # Pass 3: non-empty means it DID NOT RUN, and says why

# STRICT turns an un-run pass into a failure. CI sets it: on a runner the
# absence of yq is a broken image, not a local convenience, and the ruling
# belongs here beside the pass rather than re-derived by every caller.
#
# OFF IS AN ENUMERATED SET, NOT "anything but 0". The first version tested
# `!= "0"`, so `LINT_PROMPTS_STRICT=false` turned strict ON — and `false` is the
# natural spelling here, because the sibling this script sits beside spells its
# boolean that way (`run-claude.sh`: `VERBOSE` is "true"/"false", executed as a
# literal). A flag whose off-switch turns it on is the same class as the rest of
# this file: a control reporting a state nobody established. Both spellings are
# accepted, and anything else is ON — an unrecognised value must not silently
# disable a gate.
STRICT=1
case "${LINT_PROMPTS_STRICT:-0}" in
    0|false|no|"") STRICT=0 ;;
esac

# --- sandbox: only `cat` is reachable -----------------------------------------
SANDBOX="$(mktemp -d)"
trap 'rm -rf "$SANDBOX"' EXIT
ln -sf "$(command -v cat)" "$SANDBOX/cat"
BASH_BIN="$(command -v bash)"

# --- Pass 1 (static): unescaped backticks, for precise line numbers -----------
# Fast, and pinpoints the offending line. Pass 2 is the real net.
for f in "$WF_DIR"/*.sh "$WF_DIR"/children/*.sh "$WF_DIR"/activities/*.sh "$WF_DIR"/common/*.sh; do
    [[ -e "$f" ]] || continue
    # `p1_files=$(( ... + 1 ))` and NOT `(( p1_files++ ))`: post-increment from
    # zero EVALUATES to zero, so the arithmetic command exits 1. Harmless under
    # this script's `set -uo pipefail`, and a live abort the day anyone adds
    # `-e`. Same form used for every counter below.
    p1_files=$(( p1_files + 1 ))
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

# --- Which assignments are prompt blocks? -------------------------------------
# NOT "variables named *PROMPT". That detector shipped first and immediately
# missed a live exit-127 bug in a fragment named CI_STATUS_NOTE: prompts are
# ASSEMBLED from fragments (CI_STATUS_NOTE, RULES, STAGES_*, guards), and every
# fragment is prompt text with the same escaping exposure as the PROMPT itself.
# Naming is not the signal.
#
# The signal is MULTI-LINE double-quoted: a prompt fragment opens a double quote
# that does not close on the same line. That rule admits every fragment
# regardless of name and excludes the ordinary one-line assignments that would
# otherwise flood the sandbox with false positives — `PR_NUMBER="$2"`,
# `SCRIPT_DIR="$(cd "$(dirname …)" && pwd)"` (real command substitution, closes
# on its line, not a prompt).
#
# Detection: count unescaped double quotes on the start line. ODD = the string
# continues to later lines = prompt fragment. EVEN = closed here = skip.
# This stays sound against the balanced-stray-quote bug (case 2 in the header):
# there the strays are on LATER lines, so the start line still counts odd.
find_prompt_blocks() {
    awk '
        /^[[:space:]]*[A-Za-z_][A-Za-z_0-9]*=\$\(cat <</ { print NR; next }
        /^[[:space:]]*[A-Za-z_][A-Za-z_0-9]*="/ {
            line = $0
            gsub(/\\"/, "", line)          # escaped quotes are not delimiters
            n = gsub(/"/, "", line)
            if (n % 2 == 1) print NR
        }
    ' "$1"
}

# --- Pass 2 (execution): construct every prompt block in the sandbox ----------
for f in "$WF_DIR"/*.sh "$WF_DIR"/children/*.sh; do
    [[ -e "$f" ]] || continue
    f_blocks=0
    while IFS= read -r s; do
        [[ -n "$s" ]] || continue
        startline=$(sed -n "${s}p" "$f")
        if [[ "$startline" == *'=$(cat <<'* ]]; then
            # heredoc form: PROMPT=$(cat <<EOF ... EOF )  — ends at a lone ')'
            e=$(awk -v s="$s" 'NR>s && /^\)/ {print NR; exit}' "$f")
            # A DROP IS NAMED AND COUNTED, NEVER SILENT. This `continue` used to
            # be bare: a block whose closing `)` the scan could not find left the
            # population without leaving a trace, so the summary's block count
            # quietly went down by one and nothing said a block had gone
            # unchecked. That is this script's own subject — a report that does
            # not mention what it failed to look at — and the case it hides is
            # the worst one, an unterminated heredoc.
            if [[ -z "$e" ]]; then
                echo "✗ ${f#"$WF_DIR"/}:${s} — prompt block starts here and its closing ')' was never found; NOT constructed"
                fail=1
                continue
            fi
            block=$(sed -n "${s},${e}p" "$f")
        else
            # inline form: VAR="…" — extract EXACTLY the assignment statement, by
            # finding the line where the opening quote closes: walk forward
            # counting unescaped double quotes, and stop when the running total
            # goes even. This replaced a terminator-scan ("read until the next
            # `echo`/`run_claude`/`fi`"), which was guesswork: it swallowed the
            # `done` of a loop whose body accumulated a multi-line string, and
            # reported a syntax error that was the extractor's, not the file's.
            #
            # Sound against BOTH stray-quote parities, which is why the counting
            # is safe here: an ODD number of strays unbalances the file and
            # `bash -n` catches it; an EVEN number leaves the running total's
            # parity intact, so the block stays whole and the sandbox catches it.
            e=$(awk -v s="$s" '
                NR >= s {
                    line = $0
                    gsub(/\\"/, "", line)
                    n += gsub(/"/, "", line)
                    if (n % 2 == 0) { print NR; exit }
                }
            ' "$f")
            [[ -n "$e" ]] || e=$(wc -l < "$f")
            block=$(sed -n "${s},${e}p" "$f")
        fi

        # Counted HERE and not at the top of the loop: the claim the summary
        # makes is "N prompt blocks CONSTRUCT", so the counter has to sit where
        # a block is actually handed to the sandbox. A block the extractor gave
        # up on above `continue`s past this line and is not claimed.
        f_blocks=$(( f_blocks + 1 ))

        # Invoke bash by ABSOLUTE path — the sandbox PATH deliberately contains
        # only `cat`, so `bash` itself would not resolve through it.
        if ! err=$(env -i PATH="$SANDBOX" "$BASH_BIN" -c "set -e
$block" 2>&1); then
            echo "✗ $(basename "$f") — prompt block starting at line ${s} does NOT construct:"
            echo "$err" | sed 's/^/      /'
            echo "      (error line numbers are relative to the block; block starts at file line ${s})"
            fail=1
        fi
    done < <(find_prompt_blocks "$f")
    # The `while` reads from a process substitution, so its body runs in THIS
    # shell and `f_blocks` survives the loop. A pipe would have put it in a
    # subshell and every count would read zero — silently, and in the direction
    # that makes the vacuous-scan assertion below fire on a healthy tree.
    if [[ $f_blocks -gt 0 ]]; then
        p2_files=$(( p2_files + 1 ))
        p2_blocks=$(( p2_blocks + f_blocks ))
    fi
done

# --- Pass 3: every MODEL_KEY resolves in config.yaml --------------------------
# A MODEL_KEY with no config.yaml entry makes run-claude.sh abort at dispatch —
# correct behaviour (never run on an inherited default), but the failure lands on
# the operator at launch time rather than here. This class is created by RENAMES:
# revision.sh -> revision-minor.sh moved the script and the config key while its
# MODEL_KEY kept the old name, leaving the workflow unlaunchable and silent about
# it until someone tried to dispatch. Cheap to check, so check it.
#
# THE GUARD IS RECORDED, NOT JUST TAKEN. Both conditions below are reasons the
# pass DID NOT RUN, and each writes its own reason into `p3_skip` — the summary
# then prints that reason instead of a claim. Collapsing them into one message
# would tell an operator to install yq on a machine where yq is fine and the
# config file is the thing that moved.
CONFIG="${SCRIPT_DIR}/../../config.yaml"
if ! command -v yq &>/dev/null; then
    p3_skip="yq is not installed"
elif [[ ! -f "$CONFIG" ]]; then
    p3_skip="no config.yaml at ${CONFIG}"
else
    for f in "$WF_DIR"/*.sh "$WF_DIR"/children/*.sh; do
        [[ -e "$f" ]] || continue
        mk=$(grep -m1 '^MODEL_KEY=' "$f" | sed 's/MODEL_KEY="//;s/"//')
        [[ -n "$mk" ]] || continue
        p3_seen=$(( p3_seen + 1 ))
        if [[ -z "$(yq -r ".models.\"${mk}\" // \"\"" "$CONFIG")" ]]; then
            echo "✗ ${f#"$WF_DIR"/} — MODEL_KEY '${mk}' has no entry in config.yaml models: — this workflow CANNOT dispatch"
            fail=1
        else
            p3_keys=$(( p3_keys + 1 ))
        fi
    done
    # A file with no `MODEL_KEY=` line is skipped by the loop, which is correct
    # — not every workflow script declares one — but if NONE did, the pass
    # examined nothing and must not be reported as having run.
    #
    # KEYED ON PASS 3's OWN POPULATION (`p3_seen`), NOT ON THE GLOBAL `$fail`.
    # The first version read `$fail`, which passes 1 and 2 also write — so a
    # pass-1 failure suppressed pass 3's "examined nothing" diagnostic on a run
    # where pass 3 had genuinely examined nothing. That is this file's own
    # subject inverted: a state established and then not reported because an
    # unrelated check happened to have failed.
    [[ $p3_seen -gt 0 ]] || p3_skip="no MODEL_KEY declarations found under ${WF_DIR}"
fi

# --- Summary: claim exactly what ran ------------------------------------------
# A scan that examined nothing is not a clean scan. Both populations above come
# from a glob, so a moved directory, a wrong SCRIPT_DIR or a bad checkout yields
# an empty loop and, before this, a green tick. Asserted rather than merely
# printed, because the tick is what an operator reads.
if [[ $p1_files -eq 0 || $p2_blocks -eq 0 ]]; then
    echo "✗ this lint examined nothing — pass 1 saw ${p1_files} file(s), pass 2 constructed ${p2_blocks} block(s)"
    echo "      WF_DIR=${WF_DIR}"
    echo "      A clean result over an empty scan is the defect this gate exists to prevent, so it is a failure."
    exit 1
fi

# STRICT: an un-run pass is a failure, not a footnote. Evaluated after the
# vacuous-scan check so a broken checkout reports as a broken checkout.
if [[ -n "$p3_skip" && "$STRICT" != "0" ]]; then
    echo "✗ pass 3 (MODEL_KEY resolution) DID NOT RUN — ${p3_skip}"
    echo "      LINT_PROMPTS_STRICT=${STRICT}: a pass that cannot run is a failure, not a skip."
    fail=1
fi

if [[ $fail -eq 0 ]]; then
    echo "✓ prompt lint clean"
    echo "    pass 1 · unescaped backticks   — ${p1_files} file(s) scanned"
    echo "    pass 2 · sandbox construction  — ${p2_blocks} prompt block(s) in ${p2_files} file(s) construct"
    if [[ -z "$p3_skip" ]]; then
        echo "    pass 3 · MODEL_KEY resolution  — ${p3_keys} MODEL_KEY(s) resolve in config.yaml"
    else
        echo "    pass 3 · MODEL_KEY resolution  — DID NOT RUN: ${p3_skip}"
        echo
        echo "  ⚠ Nothing above says a workflow can dispatch. Pass 3 is the only check that a"
        echo "    script's MODEL_KEY still has a config.yaml entry, and the class it catches is a"
        echo "    RENAME — moving a script and its models: key apart leaves the workflow silently"
        echo "    unlaunchable until someone tries to run it."
        echo "    Install yq, or re-run with LINT_PROMPTS_STRICT=1 to make this a hard failure."
    fi
fi
exit $fail

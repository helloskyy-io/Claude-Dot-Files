#!/usr/bin/env bash
# Mutation harness — prove a guard can FAIL, mechanically.
#
# The Testing Standard's efficacy rule requires a guard to be demonstrably able
# to fail. That question is usually asked in prose and answered by assertion.
# This makes it executable: falsify -> show red -> restore -> show green.
#
# Usage:
#   testing/scripts/mutate.sh <file> <old-string> <new-string> <pytest-target>
#
# Example — prove the loop bound is actually enforced:
#   testing/scripts/mutate.sh \
#     scripts/workflows/temporal/modules/assistant/routing.py \
#     'MAX_LOOPS = 1' 'MAX_LOOPS = 3' \
#     scripts/workflows/temporal/tests/unit/test_plan_project_loop.py
#
# WHY THIS EXISTS AS A TOOL AND NOT PER-RUN CODE. Four independent runs on a
# sibling repo each hand-rolled this identical loop. It is a tool.
#
# THE NON-OBVIOUS PART — READ BEFORE CHANGING ANYTHING BELOW.
#
# CPython validates a cached .pyc on WHOLE-SECOND mtime plus source byte size.
# A length-preserving mutation applied within the same second of the original
# leaves both unchanged, so Python loads the STALE bytecode and the harness
# reports green having tested nothing at all.
#
# `PYTHONDONTWRITEBYTECODE=1` DOES NOT FIX THIS. It suppresses WRITING a cache,
# not READING one that already exists. That is the trap: the obvious guard
# looks like it addresses the problem and does not.
#
# We are not hypothetically exposed. On 2026-08-07 this repo mutated
# `MAX_LOOPS = 1` to `MAX_LOOPS = 3` — same byte length, same file, Python —
# and it only reported correctly because minutes happened to elapse between the
# edit and the run. Sub-second, it would have passed while testing nothing.
#
# So every leg below gets its own PYTHONPYCACHEPREFIX. A cache directory that
# did not exist a moment ago cannot serve a stale entry.
set -euo pipefail

[[ $# -eq 4 ]] || { sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
FILE="$1"; OLD="$2"; NEW="$3"; TARGET="$4"

[[ -f "$FILE" ]] || { echo "✗ no such file: $FILE" >&2; exit 2; }
grep -qF -- "$OLD" "$FILE" || {
    echo "✗ the string to mutate is NOT PRESENT in $FILE:" >&2
    echo "    $OLD" >&2
    echo "  A mutation that changes nothing proves nothing — that is the failure" >&2
    echo "  this check exists to catch. Fix the string, do not proceed." >&2
    exit 2
}

# AMBIGUITY IS A HARD ERROR, because the mutation below replaces only the FIRST
# occurrence. If the string appears more than once, "the first one" is whichever
# the file happens to list earliest — routinely a mention inside a comment
# header rather than the live code beneath it. Mutating a comment changes no
# behaviour, every leg stays green, and the harness reports "✗ THE GUARD DID NOT
# FIRE" over a guard that is in fact working. That is a FALSE NEGATIVE from a
# tool whose entire job is telling you whether to trust a test, and it is not
# hypothetical: on 2026-08-08 a review run hit exactly this against
# `config/hooks/block-dangerous.sh`, where `git reset --hard` appears both in
# the THREAT MODEL comment block and in the pattern array.
#
# The caller disambiguates — usually by including the surrounding syntax, e.g.
# passing "'git reset --hard'" WITH the shell quotes so it matches the array
# entry and not the prose.
# Occurrences, not matching LINES: `grep -c` counts lines, so a string
# appearing twice on one line would report 1 and sail through this guard while
# `.replace(old, new, 1)` below mutates only the first of the two — the same
# false-negative shape this guard exists to close, one level down.
OCCURRENCES="$(grep -oF -- "$OLD" "$FILE" | wc -l || true)"
if [[ "$OCCURRENCES" -gt 1 ]]; then
    echo "✗ AMBIGUOUS: the string to mutate appears $OCCURRENCES times in $FILE:" >&2
    echo "    $OLD" >&2
    grep -nF -- "$OLD" "$FILE" | sed 's/^/      /' >&2
    echo "  Only the FIRST occurrence would be replaced, and if that one sits in a" >&2
    echo "  comment the mutation changes no behaviour — every leg stays green and" >&2
    echo "  this harness reports a guard failure that did not happen." >&2
    echo "  Narrow the string until it matches exactly one occurrence (including" >&2
    echo "  the surrounding quotes or indentation is usually enough)." >&2
    exit 2
fi

CACHE_ROOT="$(mktemp -d)"
BACKUP="$(mktemp)"
cp "$FILE" "$BACKUP"
# Restore on ANY exit path. A harness that leaves a mutated tree behind is
# worse than no harness — the next run tests code nobody meant to ship.
trap 'cp "$BACKUP" "$FILE"; rm -f "$BACKUP"; rm -rf "$CACHE_ROOT"' EXIT

# Judged by pytest's EXIT CODE, not by grepping the tail line for the substring
# "failed". A mutation that breaks collection (a syntax error, an unparseable
# array entry) prints "1 error" and exits 2 — the guard fired, hard — but that
# text does not contain "failed", so the old substring check reported "THE
# GUARD DID NOT FIRE" over a guard that worked. Measured on 2026-08-08 against
# this exact file's own coverage guard: a mutated crontab entry with a trailing
# comment errored at collection, and the substring check called it a miss.
#
# Sets LEG_STATUS (pytest's raw exit code) and LEG_TAIL (the human-readable
# summary line, kept because it is still the useful part of the output) as
# globals rather than returning through command substitution — command
# substitution can only capture stdout, and the exit code is the whole point.
#
# Assigned inside an `if`, not as a bare `var="$(cmd)"`: under `set -e` a bare
# assignment whose command substitution fails aborts the script before $? can
# be read at all. Any command tested by an `if` is exempt from that.
run_leg() {  # $1 = leg name, used to make the cache prefix unique
    local name="$1" output
    if output="$(PYTHONPYCACHEPREFIX="${CACHE_ROOT}/${name}" python3 -m pytest "$TARGET" -q 2>&1)"; then
        LEG_STATUS=0
    else
        LEG_STATUS=$?
    fi
    LEG_TAIL="$(tail -n1 <<<"$output")"
}

# Classifies a pytest exit code per pytest's documented meaning:
#   0            -> GREEN  (all tests passed)
#   1, 2, 3      -> RED    (tests failed / run interrupted / internal error —
#                           a collection error is 2 and MUST count as the
#                           guard firing)
#   4, 5, other  -> HARNESS_ERROR, not a leg result. In particular 5 ("no
#                   tests collected") must never read as "the guard fired" —
#                   it means TARGET was wrong, not that anything was tested.
classify_leg() {
    case "$1" in
        0) echo GREEN ;;
        1|2|3) echo RED ;;
        *) echo HARNESS_ERROR ;;
    esac
}

# Prints the leg's tail line plus its exit code, and aborts the whole run on
# HARNESS_ERROR — a leg result is meaningless if pytest itself never ran the
# suite. Sets LEG_VERDICT to GREEN or RED for the caller — NOT returned
# through command substitution: the tail line below is printed for the human
# reading the terminal, and wrapping this call in "$(...)" to capture a return
# value would swallow that print into the captured string instead.
report_leg() {  # $1 = leg label for the abort message
    echo "   $LEG_TAIL  [exit $LEG_STATUS]"
    LEG_VERDICT="$(classify_leg "$LEG_STATUS")"
    if [[ "$LEG_VERDICT" == HARNESS_ERROR ]]; then
        echo "✗ HARNESS ERROR on $1: pytest exited $LEG_STATUS, which is not a leg" >&2
        echo "  result. Exit 5 means no tests were collected — TARGET is probably" >&2
        echo "  wrong. Exit 4 is a pytest usage error. Fix the invocation, not the" >&2
        echo "  mutation." >&2
        exit 1
    fi
}

echo "── leg 1: BASELINE — the guard must be green before it is meaningful"
run_leg baseline
report_leg "leg 1 (baseline)"
BEFORE_VERDICT="$LEG_VERDICT"
if [[ "$BEFORE_VERDICT" == RED ]]; then
    echo "✗ the target is ALREADY RED. Fix that first — a mutation against a" >&2
    echo "  failing suite tells you nothing about the mutation." >&2
    exit 1
fi

echo "── leg 2: MUTATED — the guard must now fail"
python3 - "$FILE" "$OLD" "$NEW" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); p.write_text(p.read_text().replace(sys.argv[2], sys.argv[3], 1))
PY
run_leg mutated
MUTATED_STATUS="$LEG_STATUS"
report_leg "leg 2 (mutated)"
MUTATED_VERDICT="$LEG_VERDICT"

echo "── leg 3: RESTORED — and green again, proving the harness cleaned up"
cp "$BACKUP" "$FILE"
run_leg restored
report_leg "leg 3 (restored)"
AFTER_VERDICT="$LEG_VERDICT"

echo
if [[ "$MUTATED_VERDICT" == RED && "$AFTER_VERDICT" == GREEN ]]; then
    echo "✓ MUTATION DEMONSTRATED — the guard fails when the property is violated (leg 2 exit $MUTATED_STATUS)"
    exit 0
fi
if [[ "$MUTATED_VERDICT" == GREEN ]]; then
    echo "✗ THE GUARD DID NOT FIRE. The mutation broke the property and every test" >&2
    echo "  still passed. Either nothing asserts this property, or the assertion" >&2
    echo "  cannot distinguish the mutated value from the original." >&2
    exit 1
fi
echo "✗ THE TREE DID NOT RESTORE CLEANLY — red after restore. Investigate before" >&2
echo "  trusting any result from this harness." >&2
exit 1

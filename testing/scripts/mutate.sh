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
OCCURRENCES="$(grep -cF -- "$OLD" "$FILE" || true)"
if [[ "$OCCURRENCES" -gt 1 ]]; then
    echo "✗ AMBIGUOUS: the string to mutate appears on $OCCURRENCES lines of $FILE:" >&2
    echo "    $OLD" >&2
    grep -nF -- "$OLD" "$FILE" | sed 's/^/      /' >&2
    echo "  Only the FIRST occurrence would be replaced, and if that one sits in a" >&2
    echo "  comment the mutation changes no behaviour — every leg stays green and" >&2
    echo "  this harness reports a guard failure that did not happen." >&2
    echo "  Narrow the string until it matches exactly one line (including the" >&2
    echo "  surrounding quotes or indentation is usually enough)." >&2
    exit 2
fi

CACHE_ROOT="$(mktemp -d)"
BACKUP="$(mktemp)"
cp "$FILE" "$BACKUP"
# Restore on ANY exit path. A harness that leaves a mutated tree behind is
# worse than no harness — the next run tests code nobody meant to ship.
trap 'cp "$BACKUP" "$FILE"; rm -f "$BACKUP"; rm -rf "$CACHE_ROOT"' EXIT

run_leg() {  # $1 = leg name, used to make the cache prefix unique
    PYTHONPYCACHEPREFIX="${CACHE_ROOT}/$1" python3 -m pytest "$TARGET" -q 2>&1 | tail -1
}

echo "── leg 1: BASELINE — the guard must be green before it is meaningful"
BEFORE="$(run_leg baseline || true)"
echo "   $BEFORE"
grep -q "failed" <<<"$BEFORE" && {
    echo "✗ the target is ALREADY RED. Fix that first — a mutation against a" >&2
    echo "  failing suite tells you nothing about the mutation." >&2
    exit 1
}

echo "── leg 2: MUTATED — the guard must now fail"
python3 - "$FILE" "$OLD" "$NEW" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); p.write_text(p.read_text().replace(sys.argv[2], sys.argv[3], 1))
PY
MUTATED="$(run_leg mutated || true)"
echo "   $MUTATED"

echo "── leg 3: RESTORED — and green again, proving the harness cleaned up"
cp "$BACKUP" "$FILE"
AFTER="$(run_leg restored || true)"
echo "   $AFTER"

echo
if grep -q "failed" <<<"$MUTATED" && ! grep -q "failed" <<<"$AFTER"; then
    echo "✓ MUTATION DEMONSTRATED — the guard fails when the property is violated"
    exit 0
fi
if ! grep -q "failed" <<<"$MUTATED"; then
    echo "✗ THE GUARD DID NOT FIRE. The mutation broke the property and every test" >&2
    echo "  still passed. Either nothing asserts this property, or the assertion" >&2
    echo "  cannot distinguish the mutated value from the original." >&2
    exit 1
fi
echo "✗ THE TREE DID NOT RESTORE CLEANLY — red after restore. Investigate before" >&2
echo "  trusting any result from this harness." >&2
exit 1

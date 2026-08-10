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
# did not exist a moment ago cannot serve a stale entry. EVERY Python
# invocation this script makes against the tree is a leg for that purpose,
# including the import probe — it ran without a prefix once, and a stale entry
# answered it "imports fine" for a file pytest could not import at all.
set -euo pipefail

[[ $# -eq 4 ]] || { sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
FILE="$1"; OLD="$2"; NEW="$3"; TARGET="$4"

[[ -f "$FILE" ]] || { echo "✗ no such file: $FILE" >&2; exit 2; }

# OLD must be single-line. Both the presence check and the occurrence count
# below are `grep -F`, which treats an embedded newline in its PATTERN
# argument as separating independent alternate patterns (like -f patternfile)
# rather than as a literal line break — so a multi-line OLD would be tested as
# "does any of these fragments appear anywhere in the file", not "does this
# exact block appear". That can both false-flag AMBIGUOUS (fragments recur
# elsewhere) and false-pass a real multi-line ambiguity the per-fragment count
# cannot see — the same false-negative shape the occurrence-count fix below
# exists to close, one level further down. Reject up front rather than mis-
# count silently; no caller needs a multi-line OLD today.
[[ "$OLD" != *$'\n'* ]] || {
    echo "✗ OLD must be single-line: grep -F treats an embedded newline as" >&2
    echo "  separating alternate patterns, not as a literal line break, so" >&2
    echo "  presence and ambiguity checks below cannot be trusted against it." >&2
    exit 2
}

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
# array entry) prints "1 error" and *can* mean the guard fired, hard — but
# that text does not contain "failed", so the old substring check reported
# "THE GUARD DID NOT FIRE" over a guard that worked. Measured on 2026-08-08
# against this exact file's own coverage guard: a mutated crontab entry with a
# trailing comment errored at collection, and the substring check called it a
# miss. (Exit 2 is not always a fired guard, though — see classify_leg below
# for the case where it means the opposite.)
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
    LEG_NAME="$name"
    if output="$(PYTHONPYCACHEPREFIX="${CACHE_ROOT}/${name}" python3 -m pytest "$TARGET" -q 2>&1)"; then
        LEG_STATUS=0
    else
        LEG_STATUS=$?
    fi
    LEG_TAIL="$(tail -n1 <<<"$output")"
}

# The measurement behind the exit-2 discriminator (see classify_leg below):
# can $FILE be IMPORTED right now? A SyntaxError makes that impossible on its
# own, and so does anything else a mutation could turn $FILE into that isn't
# valid, importable Python: a broken import (`import os` mutated to
# `import os_typo`), a NameError, any exception $FILE raises at module level.
# Checking syntax alone (an earlier version of this function used `ast.parse`)
# caught the SyntaxError shape but not the others — an import that mutates
# cleanly into a reference to a nonexistent module is syntactically valid and
# still means nothing ran. Any of these is SUFFICIENT on its own to cause
# "Interrupted: N error during collection", so nothing else needs to have run
# for pytest to report exit 2, and nothing else can be inferred to have run.
#
# Cheaper than comparing collected-test counts between legs, and more precise:
# tried empirically against a module-level crontab-parsing guard (the shape
# the exit-2-is-RED comment above defends) and its collection error ALSO
# collects zero tests — "no tests collected, 1 error" — identical to the
# broken-.py signature. Collected count cannot tell the two cases apart;
# whether $FILE itself still imports can, because it names the actual cause
# instead of inferring it from a symptom both cases share.
#
# THIS FUNCTION ANSWERS AN ABSOLUTE QUESTION AND THE DISCRIMINATOR NEEDS A
# DIFFERENTIAL ONE. "This file does not import" and "the mutation broke this
# file" are the same answer here, and they are not the same fact — so the
# caller takes a PRISTINE baseline before leg 2 mutates anything and only
# blames the mutation when the answer CHANGED. Shipping the absolute form
# reported a genuinely-firing guard as a broken mutation; see
# EXIT_2_DISCRIMINATOR below for the baseline and for what happens when the
# probe cannot speak at all.
#
# IMPORTS THE WAY PYTEST DOES, not by bare path. pytest's default `prepend`
# import mode resolves the package root FIRST: it walks up while __init__.py
# exists, puts that root on sys.path, and imports the DOTTED name. Importing
# the bare path with spec_from_file_location skips all of that, so any module
# holding a relative import (`from .constants import BASE`) raises "attempted
# relative import with no known parent package" with no mutation in play at
# all. 22 modules in this repo are that shape — one of them a live mutate
# target with its own unit suite — so a bare-path probe measures the probe,
# not the mutation.
#
# GETS ITS OWN PYTHONPYCACHEPREFIX, PER INVOCATION, exactly as run_leg does.
# The top-of-file doctrine applies to this Python invocation unchanged, and
# with two calls against one path it applies WITHIN this function: a shared
# cache directory lets the pristine call's bytecode answer the post-mutation
# call, reporting "imports fine" for a file pytest cannot import — issue #72
# re-entering through its own fix. A fresh prefix under $CACHE_ROOT also keeps
# bytecode compiled from the MUTATED source out of the working tree, which the
# EXIT trap does not clean and which the trap's own contract forbids leaving.
#
# Imports via importlib rather than running `python3 "$FILE"` directly, so a
# `if __name__ == "__main__":` block in $FILE does not execute here — this
# probe must mirror what a real import does (module body only), not what
# running the file as a script would do, or it could raise on code a genuine
# pytest import would never touch.
#
# Guarded like every other command here: under `set -e`, a bare failing
# command aborts the script before its exit status can be inspected, so every
# call below is the condition of an `if`, not a bare invocation.
file_imports_cleanly() {  # $1 = cache label, must be unique per invocation
    PYTHONPYCACHEPREFIX="${CACHE_ROOT}/probe-$1" python3 -c "
import importlib, pathlib, sys
p = pathlib.Path(sys.argv[1]).resolve()
root, parts = p.parent, [p.stem]
while (root / '__init__.py').exists():   # pytest's prepend mode: find the package root
    parts.insert(0, root.name)
    root = root.parent
sys.path.insert(0, str(root))
importlib.import_module('.'.join(parts))
" "$FILE" >/dev/null 2>&1
}

# EVERY exit code this harness classifies, and for each the only question that
# matters: can it mean BOTH "the suite ran" and "the suite never ran"? Fixing
# one ambiguous code and leaving a second is the same defect one step over, so
# the table is exhaustive and each row answers the question explicitly.
#
#   0    -> GREEN. AMBIGUOUS, and deliberately left alone. pytest exits 0 both
#           when tests ran and passed AND when every test was SKIPPED, which
#           runs nothing (verified: one skipped test, exit 0). But the two
#           resolve to the same safe place — a GREEN leg 2 prints "THE GUARD
#           DID NOT FIRE" and refuses to certify — so this ambiguity cannot
#           produce a false certification, only a conservative non-verdict.
#           Nothing to close; the direction is already fail-closed.
#   1    -> RED. UNAMBIGUOUS on this question: exit 1 requires collection to
#           have fully succeeded (pytest interrupts to 2 on a collection error
#           unless --continue-on-collection-errors, which this harness never
#           passes), so tests were collected and executed.
#           KNOWN BOUNDARY, stated rather than papered over: exit 1 proves the
#           SUITE ran, not that the guard's ASSERTION was evaluated. A test
#           that imports $FILE inside its own body fails on the mutation's
#           ImportError before reaching the assertion, and pytest's exit code
#           carries no signal for that. It is a different channel, not a
#           different exit code, and no classification of exit codes can reach
#           it — reading pass/fail per test would be required.
#   2    -> AMBIGUOUS, and this is the one that needed closing.
#           "Interrupted: N error during collection" fires for two opposite
#           reasons pytest does not distinguish in its exit code:
#             - mutating a DATA subject (a workflow YAML, a crontab entry) so
#               the guard's OWN parsing rejects it — the guard firing, hard.
#             - mutating the PYTHON MODULE UNDER TEST so it can no longer be
#               imported (invalid syntax, a broken import, a module-level
#               exception), so pytest can never import it and NO test runs.
#           Resolved DIFFERENTIALLY, not absolutely: HARNESS_ERROR only when
#           $FILE imported cleanly BEFORE the mutation and does not now. When
#           the probe cannot establish that baseline it abstains to RED — the
#           pre-#72 behaviour — and says so, rather than asserting a cause.
#   3    -> HARNESS_ERROR. AMBIGUOUS in principle — pytest's "internal error
#           happened while executing tests" can strike before or after tests
#           ran — and its exit code carries nothing that tells the two apart.
#           So the harness picks a direction, and for a tool whose expensive
#           error is false certification the fail-closed one is right: a
#           pytest/plugin failure is never a leg result. Treat it like 4/5.
#   4    -> HARNESS_ERROR. UNAMBIGUOUS: a pytest usage error, nothing ran.
#   5    -> HARNESS_ERROR. UNAMBIGUOUS: "no tests collected" means TARGET was
#           wrong, not that anything was tested — reading it as "the guard
#           fired" is the exact laundering this tool exists to stop.
#   other-> HARNESS_ERROR. Signals (128+N) and anything pytest does not
#           document land here; unknown is not a leg result either.
classify_leg() {
    case "$1" in
        0) echo GREEN ;;
        1) echo RED ;;
        2)
            if [[ "$EXIT_2_DISCRIMINATOR" == live ]] && ! file_imports_cleanly "$LEG_NAME"; then
                echo HARNESS_ERROR
            else
                echo RED
            fi
            ;;
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
        case "$LEG_STATUS" in
            2)
                echo "✗ HARNESS ERROR on $1: pytest exited 2 (collection error)." >&2
                echo "  $FILE imported cleanly BEFORE the mutation and cannot be" >&2
                echo "  imported now, so the mutation broke the target (syntax, an" >&2
                echo "  import, or a module-level exception) and no test in $TARGET" >&2
                echo "  ran. Check the mutation string, not the guard." >&2
                ;;
            3)
                echo "✗ HARNESS ERROR on $1: pytest exited 3 (internal error) — pytest" >&2
                echo "  itself failed, not a test. That does not mean the guard ran;" >&2
                echo "  investigate pytest's own failure, not the mutation." >&2
                ;;
            *)
                echo "✗ HARNESS ERROR on $1: pytest exited $LEG_STATUS, which is not a" >&2
                echo "  leg result. Exit 5 means no tests were collected — TARGET is" >&2
                echo "  probably wrong. Exit 4 is a pytest usage error. Fix the" >&2
                echo "  invocation, not the mutation." >&2
                ;;
        esac
        exit 1
    fi
    # The discriminator was NEEDED here and could not speak. Saying so is the
    # point: falling back to RED silently would hand back the pre-#72 verdict
    # with the confidence of the post-#72 one.
    if [[ "$LEG_STATUS" -eq 2 && "$EXIT_2_DISCRIMINATOR" == abstain ]]; then
        echo "   note: $FILE does not import standalone even UNMUTATED, so the" >&2
        echo "   exit-2 discriminator cannot tell whether the mutation broke the" >&2
        echo "   target or the guard's own parsing rejected it. Read as RED (the" >&2
        echo "   pre-#72 behaviour) and confirm by hand that a test in $TARGET" >&2
        echo "   actually ran before trusting this verdict." >&2
    fi
}

# THE PRISTINE BASELINE — taken HERE, before leg 2 mutates anything, because
# after that there is nothing pristine left to measure. This is what makes the
# exit-2 discriminator differential instead of absolute:
#
#   live       $FILE is Python AND imports cleanly unmutated. "It does not
#              import now" is therefore attributable to the mutation, and an
#              exit 2 on the mutated leg is a HARNESS_ERROR.
#   abstain    $FILE is Python and does NOT import unmutated. The probe cannot
#              distinguish anything; exit 2 falls back to RED with the note in
#              report_leg. NOT an error — 22 modules in this repo import only
#              with pytest's own conftest and sys.path setup in place, and
#              refusing to run against them would be worse than the pre-#72
#              behaviour, not better.
#   not-python $FILE is a crontab, a YAML, any data subject. It cannot become
#              unimportable Python, so an exit 2 belongs to the guard's own
#              parsing and reads as the guard firing — the case the exit-2-is-
#              RED rule above exists to defend, preserved exactly.
#
# Costs one extra execution of $FILE's module body per run, in its own process
# and its own bytecode cache. pytest imports it three times anyway, once per
# leg; this is the price of the question being differential at all.
LEG_NAME=""
EXIT_2_DISCRIMINATOR=not-python
if [[ "$FILE" == *.py ]]; then
    if file_imports_cleanly pristine; then
        EXIT_2_DISCRIMINATOR=live
    else
        EXIT_2_DISCRIMINATOR=abstain
    fi
fi

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
    echo "✗ THE GUARD DID NOT FIRE — and this result is AMBIGUOUS. Three causes," >&2
    echo "  and you must tell them apart before acting:" >&2
    echo "    1. nothing asserts this property (a missing guard — the usual case)" >&2
    echo "    2. the assertion cannot distinguish the mutated value from the original" >&2
    echo "    3. THE MUTATION ITSELF DID NOT CHANGE BEHAVIOUR — it applied to the" >&2
    echo "       file but altered nothing the code actually depends on. The guard" >&2
    echo "       is fine and the mutation missed." >&2
    echo "  Refusing an absent OLD rules out the crudest form of 3, not all of it." >&2
    echo "  Confirm the mutated line is on a path the target exercises before you" >&2
    echo "  conclude a guard is missing: deleting a working guard on a wrong" >&2
    echo "  mutation is the expensive direction of this error." >&2
    exit 1
fi
echo "✗ THE TREE DID NOT RESTORE CLEANLY — red after restore. Investigate before" >&2
echo "  trusting any result from this harness." >&2
exit 1

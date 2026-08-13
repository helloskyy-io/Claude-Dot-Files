#!/usr/bin/env bash
# Mutation harness — prove a guard can FAIL, mechanically.
#
# The Testing Standard's efficacy rule requires a guard to be demonstrably able
# to fail. That question is usually asked in prose and answered by assertion.
# This makes it executable: falsify -> show red -> restore -> show green.
#
# Usage:
#   testing/scripts/mutate.sh [--show-failures] <file> <old-string> <new-string> <pytest-target>
#
#   --show-failures  after each leg, list the FAILED test node ids.
#                    A predicted count is only evidence when the partition is
#                    checkable: 48 red that are the predicted 48 and 48 red that
#                    are some other 48 are the same number and different results.
#
# Example — prove the loop bound is actually enforced:
#   testing/scripts/mutate.sh \
#     scripts/workflows/temporal/modules/assistant/routing.py \
#     'MAX_LOOPS = 3' 'MAX_LOOPS = 9' \
#     scripts/workflows/temporal/tests/unit/test_plan_project_loop.py
#
# EXIT CODES — the contract with whoever calls this. No code means both "the
# suite ran" and "the suite never ran"; that separation is the whole point of
# the tool, so it holds for what this script emits and not only for what it
# reads out of pytest. Reasoning in the table above classify_leg.
#   0  MUTATION DEMONSTRATED — the guard fails when the property is violated.
#   1  The suite ran and the answer is no: already red / the guard did not
#      fire / the tree did not restore.
#   2  REFUSED before running anything — an input this harness will not reason
#      about. No verdict claimed.
#   3  HARNESS ERROR — the suite never ran, so there is no verdict to give.
#   128+N  killed by signal N. Not a verdict either, and unambiguous.
#
# AND THAT CONTRACT IS ENFORCED, NOT MERELY DOCUMENTED — this is the part the
# first four attempts at it got wrong. Stating the four codes above classifies
# the exits this script WRITES; it says nothing about the exits bash takes on
# its behalf. Under `set -euo pipefail` every bare command is a termination
# path nobody wrote, and each one used to exit with its own failing status —
# in practice 1, i.e. "the suite ran and the answer is no", from a script that
# had measured nothing. Reproduced live: a data subject holding one non-UTF-8
# byte crashed the mutation applier after leg 1 and exited 1 with a bare
# traceback and no HARNESS ERROR.
#
# So the classification does not live in a list of guarded commands — that list
# was enumerated twice and was wrong both times (five members, then seven, plus
# the trap body itself). It lives in `on_exit` below, which every termination
# passes through: any exit this script did not DELIBERATELY choose via
# `verdict` is by construction a path that reached no verdict, and becomes a 3.
# The exits you did not write are exits.
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
# `MAX_LOOPS = 3` to `MAX_LOOPS = 9` — same byte length, same file, Python —
# and it only reported correctly because minutes happened to elapse between the
# edit and the run. Sub-second, it would have passed while testing nothing.
#
# So every leg below gets its own PYTHONPYCACHEPREFIX. A cache directory that
# did not exist a moment ago cannot serve a stale entry. EVERY Python
# invocation this script makes against the tree is a leg for that purpose,
# including the import probe — it ran without a prefix once, and a stale entry
# answered it "imports fine" for a file pytest could not import at all.
set -euo pipefail

# THE ONLY WAY THIS SCRIPT DELIBERATELY TERMINATES. `verdict` records the code
# it is about to emit; `on_exit` below treats any exit that does NOT match the
# record as a path that reached no verdict. Every `exit` in this file is either
# inside `verdict` or inside `on_exit` — `test_every_exit_is_a_declared_verdict`
# is the gate on that, because the moment one is added elsewhere the record
# stops describing reality and the trap starts calling a real verdict a harness
# error.
#
# NEVER CALL FROM A SUBSHELL. The record is a shell variable, so a `verdict`
# reached inside `$(...)` would set it in the child and leave the parent's
# empty — the trap would then report HARNESS ERROR over a correct run, which is
# a false negative injected into the one tool whose expensive error is exactly
# that. This matters concretely: `classify_leg` IS invoked in a command
# substitution (see report_leg), so it must never grow a `verdict` call.
VERDICT_CODE=""
verdict() {  # $1 = the code this harness has DECIDED to emit
    VERDICT_CODE="$1"
    exit "$1"
}

# Runs on EVERY termination: deliberate verdict, `set -e` abort, or signal.
# Restores the tree and classifies the exit.
#
# EVERY COMMAND IN HERE IS GUARDED, and that is not stylistic. A trap running
# under the inherited `set -e` aborts at its first failing command — skipping
# the rest of the cleanup AND its own classification, and handing back that
# command's status. Measured: an unguarded failing `cp` inside this trap makes
# the script exit 1 with the mutated tree still on disk and nothing printed,
# which is the exact defect this trap exists to close, wearing the fix. So
# `set +e` first, then check each command by hand.
on_exit() {
    local status=$? failed_cmd="$BASH_COMMAND"   # MUST be the first line: any
    set +e                                       # command below destroys both.
    local restore_failed=""

    if [[ -n "$BACKUP_READY" ]]; then
        # Guarded on BACKUP_READY, not on -f "$BACKUP": the backup file exists
        # from `mktemp` onward but does not hold $FILE's contents until the cp
        # below it succeeds, and restoring $FILE from an empty or half-written
        # backup would destroy the very thing this trap exists to protect.
        if ! cp "$BACKUP" "$FILE"; then
            restore_failed=1
            echo "✗ HARNESS ERROR: could not restore $FILE from $BACKUP." >&2
            echo "  THE WORKING TREE IS STILL MUTATED. Restore it by hand before" >&2
            echo "  running anything else — the next run tests code nobody meant" >&2
            echo "  to ship, which is the harm this trap exists to prevent." >&2
        fi
    fi
    [[ -z "$BACKUP" ]] || rm -f "$BACKUP" || echo "  note: could not remove $BACKUP" >&2
    [[ -z "$CACHE_ROOT" ]] || rm -rf "$CACHE_ROOT" || echo "  note: could not remove $CACHE_ROOT" >&2

    # A failed restore outranks any verdict. Leg 3 proves "green again, so the
    # tree restored"; if the restore did not happen, that proof is void no
    # matter how the legs read.
    if [[ -n "$restore_failed" ]]; then
        exit 3
    fi
    if [[ "$status" != "$VERDICT_CODE" ]]; then
        echo "✗ HARNESS ERROR: the harness aborted without reaching a verdict." >&2
        echo "  Failing command: $failed_cmd" >&2
        echo "  Raw exit status: $status. No leg result is implied by this — the" >&2
        echo "  suite did not run to a conclusion, so the guard is UNJUDGED." >&2
        # Signals (128+N) are left alone: they are already outside the verdict
        # codes, and rewriting one to 3 would erase "the operator hit Ctrl-C".
        if [[ "$status" -lt 128 ]]; then
            exit 3
        fi
    fi
}
# Installed BEFORE the first command that can fail, so the classification has
# no blind spot in front of it. Everything it touches is pre-declared empty so
# `set -u` cannot trip inside a trap that runs on every path.
BACKUP=""; CACHE_ROOT=""; BACKUP_READY=""
trap on_exit EXIT

# Parsed BEFORE the positional contract so `$#` still means "the four
# required arguments". The flag is print-only: it changes no exit code, no
# leg classification and no mutation, so a run with it and a run without it
# are the same experiment.
SHOW_FAILURES=""
while [[ "${1:-}" == --* ]]; do
    case "$1" in
        --show-failures) SHOW_FAILURES=1; shift ;;
        *) echo "✗ unknown flag: $1" >&2; verdict 2 ;;
    esac
done

[[ $# -eq 4 ]] || { sed -n '2,19p' "$0" | sed 's/^# \{0,1\}//' >&2; verdict 2; }
FILE="$1"; OLD="$2"; NEW="$3"; TARGET="$4"

[[ -f "$FILE" ]] || { echo "✗ no such file: $FILE" >&2; verdict 2; }

# Mutating this script while bash is executing it is not a supported input, and
# the failure is silent and unbounded. bash reads a script LAZILY, by byte
# offset; the applier below rewrites $FILE in place (truncate + rewrite, same
# inode), so a length-changing self-mutation shifts every byte the running
# shell has not yet read and it goes on to execute fragments of the new file
# from the old offsets. Refused rather than reasoned about — and this is not
# hypothetical housekeeping: this script now has its own unit suite, and the
# Testing Standard's mutation-evidence rule makes `mutate.sh` a natural target
# for `mutate.sh`.
[[ ! "$FILE" -ef "$0" ]] || {
    echo "✗ REFUSED: $FILE is this script itself." >&2
    echo "  bash reads a script lazily by byte offset, so mutating it mid-run" >&2
    echo "  shifts the offsets underneath the running shell and it executes" >&2
    echo "  fragments of the mutated file. Copy it elsewhere and mutate that." >&2
    verdict 2
}

# An EMPTY OLD is refused, and it has to be refused HERE rather than left to
# the checks below, both of which pass it: `grep -qF -- ""` matches any file,
# and `grep -oF -- ""` emits one empty match per LINE, so a single-line subject
# counts 1 and sails through the ambiguity guard. What then reaches the applier
# is `.replace("", NEW, 1)`, which inserts NEW at offset 0 — a mutation at a
# location the caller never named. Measured: an empty OLD against a one-line
# subject prints ✓ MUTATION DEMONSTRATED, certifying a guard against a mutation
# nobody asked for. The realistic trigger is an unset variable in a caller's
# wrapper; `set -u` protects this script's variables, not the caller's argv.
[[ -n "$OLD" ]] || {
    echo "✗ REFUSED: the string to mutate is EMPTY." >&2
    echo "  An empty OLD inserts NEW at the start of the file, so the mutation" >&2
    echo "  measured is not the one you asked for. This is usually an unset" >&2
    echo "  variable in the calling command line." >&2
    verdict 2
}

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
    verdict 2
}

grep -qF -- "$OLD" "$FILE" || {
    echo "✗ the string to mutate is NOT PRESENT in $FILE:" >&2
    echo "    $OLD" >&2
    echo "  A mutation that changes nothing proves nothing — that is the failure" >&2
    echo "  this check exists to catch. Fix the string, do not proceed." >&2
    verdict 2
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
    verdict 2
fi

# pytest's ABSENCE must not enter the leg classifier. `python3 -m pytest` exits
# 1 when pytest is not importable (wrong interpreter, venv not active, a plugin
# broken at import) — and classify_leg reads 1 as RED, so leg 1 would abort
# with "the target is ALREADY RED", exit 1, sending the operator to debug a
# suite that never ran and handing a programmatic caller a measurement that
# does not exist. Verified: rc 1 on an interpreter with no pytest.
if ! python3 -c 'import pytest' >/dev/null 2>&1; then
    echo "✗ HARNESS ERROR: pytest is not importable by $(command -v python3)." >&2
    echo "  Nothing has been measured and no leg has run — this is the harness's" >&2
    echo "  own environment failing, not a verdict about your guard. Activate the" >&2
    echo "  right interpreter or install pytest, then re-run." >&2
    verdict 3
fi

# CACHE_ROOT and BACKUP are still bare, and deliberately so: on_exit now
# classifies any abort here as a 3, which is what they need. Guarding them
# individually would add nothing the trap does not already do.
CACHE_ROOT="$(mktemp -d)"
BACKUP="$(mktemp)"
cp "$FILE" "$BACKUP"
# Only NOW is the backup a faithful copy, and only now may the trap restore
# from it. See on_exit: restoring from a backup whose `cp` failed would destroy
# $FILE rather than protect it.
BACKUP_READY=1

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
#
# PYTEST_ADDOPTS IS CLEARED, and that is a correctness fix rather than hygiene.
# The exit-code table below rests on "pytest interrupts to 2 on a collection
# error unless --continue-on-collection-errors", and the old parenthetical
# justified that with "which this harness never passes" — which is a statement
# about this script's argv and not about what pytest receives. PYTEST_ADDOPTS
# supplies it from the environment. MEASURED: with
# PYTEST_ADDOPTS=--continue-on-collection-errors set, the issue-#72 scenario
# (mutating the module under test into a SyntaxError) makes pytest exit 1
# instead of 2, so the differential discriminator is never consulted at all and
# the harness prints ✓ MUTATION DEMONSTRATED over a test that never ran. That
# is #72's false certification re-entering through an environment variable.
#
# The whole output is kept, not just its tail. When this harness aborts saying
# "the mutation broke the target — check the mutation string", the reader was
# previously shown a one-line summary and had to reproduce the run by hand to
# learn which of the three causes it was; this file's own history records a
# wrong verdict caught only by someone doing exactly that.
run_leg() {  # $1 = leg name, used to make the cache prefix unique
    local name="$1" output
    LEG_NAME="$name"
    if output="$(PYTHONPYCACHEPREFIX="${CACHE_ROOT}/${name}" PYTEST_ADDOPTS= \
                 python3 -m pytest "$TARGET" -q 2>&1)"; then
        LEG_STATUS=0
    else
        LEG_STATUS=$?
    fi
    LEG_OUTPUT="$output"
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
#
# The Python body is a QUOTED heredoc (<<'PY'), matching the mutation applier
# below, so bash performs no expansion inside it. The earlier form embedded the
# same code in a double-quoted string, where a future `$` — an f-string, a
# `${...}` literal — would have been silently substituted by the shell rather
# than reaching Python. Silent is the operative word in a file whose whole
# premise is that this class of bug ships without anyone noticing.
file_imports_cleanly() {  # $1 = cache label, must be unique per invocation
    PYTHONPYCACHEPREFIX="${CACHE_ROOT}/probe-$1" python3 - "$FILE" >/dev/null 2>&1 <<'PY'
import importlib, pathlib, sys

p = pathlib.Path(sys.argv[1]).resolve()
root, parts = p.parent, [p.stem]
# pytest's prepend mode: walk up to the package root.
#
# pytest's resolve_package_path ALSO breaks on a directory name that is not a
# legal identifier; this deliberately does not, and the difference is measured
# rather than assumed. importlib.import_module accepts a non-identifier
# component (`import_module('data-pkg.mod')` imports fine — only the `import`
# STATEMENT requires an identifier), so adding that break changes no outcome
# here. It is not free either: it lowers the root past a package boundary, so a
# module holding a relative import that resolves today would stop resolving and
# the probe would abstain where it currently answers. A guard that cannot be
# shown to fix anything and can be shown to cost something does not ship.
while (root / '__init__.py').is_file():
    parts.insert(0, root.name)
    root = root.parent
# pytest's compute_module_name drops a trailing `__init__`: the module name for
# pkg/__init__.py is `pkg`, not `pkg.__init__`. Importing the latter executes
# the package body TWICE in one process — once implicitly as `pkg`, once as the
# submodule — so a module carrying a register-once guard at import time raises
# here where a real pytest import would not, and the probe would abstain on the
# very targets most likely to have such a guard. Guarded on len > 1 so a bare
# `__init__.py` with no package above it cannot reduce to an empty name.
if len(parts) > 1 and parts[-1] == '__init__':
    parts.pop()
sys.path.insert(0, str(root))
importlib.import_module('.'.join(parts))
PY
}

# EVERY exit code this harness classifies, and for each the only question that
# matters: can it mean BOTH "the suite ran" and "the suite never ran"? Fixing
# one ambiguous code and leaving a second is the same defect one step over, so
# the table is exhaustive and each row answers the question explicitly.
#
#   0    -> GREEN. AMBIGUOUS, and closed on ONE leg out of three. pytest exits
#           0 both when tests ran and passed AND when every test was SKIPPED,
#           which runs nothing (verified: one skipped test, exit 0).
#           On LEG 2 the ambiguity is harmless: both readings land on "THE
#           GUARD DID NOT FIRE", a refusal to certify, so it cannot launder a
#           certification.
#           On LEGS 1 AND 3 it is NOT harmless and is NOT closed. Leg 1 exists
#           to establish "the guard is green before it is meaningful" and leg 3
#           to prove "green again, so the tree restored"; an all-skipped leg
#           establishes neither and is accepted as GREEN anyway. MEASURED, not
#           reasoned: a subject whose tests skip while it is pristine and run
#           once mutated yields leg 1 = nothing ran, leg 2 = RED, leg 3 =
#           nothing ran — and this harness prints "✓ MUTATION DEMONSTRATED"
#           over two legs that executed no test at all.
#           Not closed here because closing it requires counting EXECUTED
#           tests, and no pytest exit code carries that. It is a different
#           channel, not a wider `case` arm — the same boundary exit 1 hits
#           below. Stated rather than claimed closed; the mechanism is a
#           proposal, C-060 in
#           docs/standards/architecture/research/candidates.md.
#   1    -> RED. UNAMBIGUOUS on this question: exit 1 requires collection to
#           have fully succeeded (pytest interrupts to 2 on a collection error
#           unless --continue-on-collection-errors, which run_leg clears
#           PYTEST_ADDOPTS to keep out of the environment), so tests were
#           collected and executed.
#           RESIDUAL, and it is NOT closed: a target repo's own `addopts` in
#           pytest.ini / pyproject.toml supplies the same flag and cannot be
#           cleared by an environment variable. Clearing PYTEST_ADDOPTS closes
#           the channel that was measured re-opening issue #72; the ini channel
#           is stated here rather than claimed closed, and the precheck that
#           would close it is a proposal, C-061 in candidates.md.
#           KNOWN BOUNDARY, stated rather than papered over: exit 1 proves the
#           SUITE ran, not that the guard's ASSERTION was evaluated. A test
#           that imports $FILE inside its own body fails on the mutation's
#           ImportError before reaching the assertion, and pytest's exit code
#           carries no signal for that. No classification of EXIT CODES can
#           reach it — but that is a statement about exit codes, not about the
#           harness: the import probe below is a second channel and is exactly
#           the shape that could, by asking on a RED leg whether $FILE still
#           imports. It is not consulted on exit 1 today because a note there
#           would fire on every legitimately-failing test that also imports a
#           broken module, and no one has measured how often that is. The door
#           is open, not closed.
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
#
# THE SAME QUESTION, ASKED OF THE CODES THIS HARNESS ITSELF EMITS. The table
# above covers every code pytest hands IN. Asking it only of the input side is
# the same defect one step over — so the output side answers it too, and the
# answer is what fixed it: exit 1 used to mean BOTH "the suite ran and the
# answer is no" AND "the suite never ran", the exact conflation this tool
# exists to refuse.
#
#   0 -> the suite ran, the guard fired, the tree restored. DEMONSTRATED.
#        TWO BOUNDARIES, stated because the row above them is the one this
#        whole file is about and a false claim here is the worst kind:
#          - the all-skipped ambiguity on legs 1 and 3 (see the exit-0 row in
#            the pytest table above). Mechanism to close it: C-060.
#          - the ABSTAIN path. When $FILE is Python that does not import even
#            unmutated, the discriminator cannot speak and leg 2's exit 2 falls
#            back to RED — which can be the guard firing OR the mutation having
#            broken the import with nothing run. So a 0 emitted on an abstained
#            run carries issue #72's residual risk. stderr says so on every such
#            run ("does not import standalone"), and 22 modules in this repo are
#            that shape. Whether that case deserves its OWN emitted code is a
#            live question and is NOT settled here — see the note below.
#   1 -> the suite RAN and the answer is no. Three causes, one meaning: the
#        target was ALREADY RED, THE GUARD DID NOT FIRE, or the tree did not
#        restore. All are measurements this harness stands behind.
#   2 -> REFUSED before anything ran. Input this harness will not reason about
#        (bad argument count, missing file, multi-line or absent or ambiguous
#        OLD, an empty OLD, or $FILE being this script itself). No verdict is
#        claimed, so nothing can be laundered.
#   3 -> HARNESS ERROR: the suite NEVER RAN, so there is no answer. Chosen to
#        echo pytest's own exit 3 ("the tool failed, not a test"). Also every
#        termination this script did not deliberately choose — see on_exit.
#   128+N -> killed by signal N. Left as-is rather than rewritten to 3: it is
#        already outside the verdict codes, and flattening it would erase the
#        fact that an operator hit Ctrl-C.
#
# THE ONE ROW THAT IS ARGUED RATHER THAN SETTLED. The case for splitting 1 from
# 3 (below) applies with some force to splitting an abstained 0 from a clean 0,
# and this file should not pretend otherwise. The reason it was NOT done here:
# the 1-vs-3 split separates codes that point in OPPOSITE directions — "go fix
# your guard" versus "the guard is unjudged" — whereas a clean 0 and an
# abstained 0 point the SAME way ("the guard fired, keep it") and differ in
# CONFIDENCE, not in the action they license. That is a weaker case, not no
# case: an abstained 0 can still be a false certification, which is the other
# expensive direction. Left as an explicit open ruling rather than decided
# quietly, because deciding it quietly is how the 1-vs-3 conflation survived
# four passes.
#
# Why this was worth splitting off 1 rather than documenting as overloaded, as
# run-all.sh's exit 1 legitimately is: there BOTH readings mean "not green", so
# conflating them cannot mislead. Here they point opposite ways. "THE GUARD DID
# NOT FIRE" is an actionable verdict about the guard — it sends an engineer to
# delete or rewrite a test — while HARNESS ERROR means the harness could not
# measure and the guard is unjudged. Acting on the first when the truth is the
# second is precisely the direction this file's header calls expensive: it gets
# a working guard deleted. A caller could only tell them apart by grepping
# stderr for "HARNESS ERROR", which is how wrong verdict #1 shipped.
classify_leg() {  # $1 = pytest's exit code, $2 = leg name (the probe's cache label)
    case "$1" in
        0) echo GREEN ;;
        1) echo RED ;;
        2)
            if [[ "$EXIT_2_DISCRIMINATOR" == live ]] && ! file_imports_cleanly "$2"; then
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
    # The names were always in LEG_OUTPUT; six reflections asked for them and
    # each pass built its own runner to get what these four lines print.
    if [[ -n "$SHOW_FAILURES" ]]; then
        grep -E '^(FAILED|ERROR) ' <<<"$LEG_OUTPUT" | sed 's/^/     /' || true
    fi
    # LEG_NAME passed explicitly rather than read as a global inside
    # classify_leg: the probe's cache prefix is derived from it, and a stale
    # name would point two probes at one cache directory — the shared-cache
    # defect this file spends forty lines defeating everywhere else. Making it
    # an argument means the pairing of status and leg cannot silently drift if
    # a future edit puts anything between run_leg and report_leg.
    LEG_VERDICT="$(classify_leg "$LEG_STATUS" "$LEG_NAME")"
    if [[ "$LEG_VERDICT" == HARNESS_ERROR ]]; then
        case "$LEG_STATUS" in
            2)
                echo "✗ HARNESS ERROR on $1: pytest exited 2 (collection error)." >&2
                echo "  $FILE imported cleanly BEFORE the mutation and cannot be" >&2
                echo "  imported now, so the mutation broke the target (syntax, an" >&2
                echo "  import, or a module-level exception) and no test in $TARGET" >&2
                echo "  ran. Usually that means the mutation string is wrong." >&2
                echo "  ONE CASE WHERE IT DOES NOT: if $FILE validates ITSELF at" >&2
                echo "  module level (an assert, a schema build, a _validate()" >&2
                echo "  call), then that guard firing is what stopped the import" >&2
                echo "  and your mutation was correct. The harness cannot tell the" >&2
                echo "  two apart — it can only say that nothing in $TARGET ran, so" >&2
                echo "  the guard is UNJUDGED either way. Read $FILE before" >&2
                echo "  rewriting the mutation." >&2
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
        # The evidence, not just the conclusion. Every branch above tells the
        # reader to go investigate something; withholding pytest's own output
        # means they must reproduce the run by hand to do it, and this file's
        # history records a wrong verdict that was caught ONLY because someone
        # did. For a tool whose failure mode is a confident wrong answer,
        # discarding the one artifact that could falsify the answer is backwards.
        echo "  ── pytest output from $1 ──" >&2
        sed 's/^/  /' >&2 <<<"$LEG_OUTPUT"
        # Exit 3, NOT 1 — see the emitted-exit-code table above. Exit 1 is
        # reserved for measurements this harness stands behind; nothing was
        # measured here, so it must not share a code with a verdict.
        verdict 3
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
# Costs one extra execution of $FILE's module body per run, plus one more for
# every leg that exits 2 and consults the probe — so between one and four in
# total, each in its own process and its own bytecode cache. pytest imports it
# three times anyway, once per leg; this is the price of the question being
# differential at all. Worth knowing if $FILE has import side effects.
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
    verdict 1
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
# A FAILED RESTORE IS TESTED FIRST, and the order is the whole point. When it
# was tested last, the combination "leg 2 green, leg 3 red" fell into the
# guard-did-not-fire branch below and printed THE GUARD DID NOT FIRE — the
# verdict this file's header calls the expensive direction, because it sends an
# engineer to delete a test — over a tree whose state is not trustworthy enough
# to support any verdict at all. The THE TREE DID NOT RESTORE branch was
# unreachable in exactly the combination that needed it. Leg 3 is the proof
# that the tree came back; if that proof failed, no reading of leg 2 survives
# it, so it must be checked before leg 2 is interpreted at all.
if [[ "$AFTER_VERDICT" != GREEN ]]; then
    echo "✗ THE TREE DID NOT RESTORE CLEANLY — red after restore. Investigate before" >&2
    echo "  trusting any result from this harness. Leg 2 read $MUTATED_VERDICT, but that" >&2
    echo "  reading is not trustworthy while leg 3 is red: the suite is either" >&2
    echo "  non-deterministic or leg 2 left state behind that the file restore" >&2
    echo "  does not undo." >&2
    verdict 1
fi
if [[ "$MUTATED_VERDICT" == RED ]]; then
    echo "✓ MUTATION DEMONSTRATED — the guard fails when the property is violated (leg 2 exit $MUTATED_STATUS)"
    verdict 0
fi
if [[ "$MUTATED_VERDICT" == GREEN ]]; then
    echo "✗ THE GUARD DID NOT FIRE — and this result is AMBIGUOUS. FOUR causes," >&2
    echo "  and you must tell them apart before acting:" >&2
    echo "    1. nothing asserts this property (a missing guard — the usual case)" >&2
    echo "    2. the assertion cannot distinguish the mutated value from the original" >&2
    echo "    3. THE MUTATION ITSELF DID NOT CHANGE BEHAVIOUR — it applied to the" >&2
    echo "       file but altered nothing the code actually depends on. The guard" >&2
    echo "       is fine and the mutation missed." >&2
    echo "    4. THE MUTATED CODE IS REDUNDANT — the mutation DID change the file" >&2
    echo "       and nothing noticed because something else already enforces the" >&2
    echo "       property. Then the right response is DELETING THE REDUNDANT CODE," >&2
    echo "       not adding a test for it. Distinct from 3: there the mutation was" >&2
    echo "       ineffective; here it was effective and the code was dead weight." >&2
    echo "       Reported from a sibling repo, where a jq type guard's removal was" >&2
    echo "       byte-identical in outcome to the \`|| true\` beside it." >&2
    echo "  Refusing an absent OLD rules out the crudest form of 3, not all of it." >&2
    echo "  Cause 4 is the one that pulls TOWARD adding a vacuous test to make the" >&2
    echo "  tally look complete. Check whether anything else already enforces the" >&2
    echo "  property before you write one." >&2
    echo "  Confirm the mutated line is on a path the target exercises before you" >&2
    echo "  conclude a guard is missing: deleting a working guard on a wrong" >&2
    echo "  mutation is the expensive direction of this error." >&2
    verdict 1
fi
# Unreachable by construction: leg 3 is GREEN (checked above) and leg 2 is
# neither RED nor GREEN, but classify_leg returns only those two — a
# HARNESS_ERROR would have aborted in report_leg. Kept as a fail-closed
# backstop rather than deleted, because "unreachable" is a claim about today's
# classify_leg and this file's history is a record of such claims aging badly.
echo "✗ HARNESS ERROR: leg 2 produced the verdict '$MUTATED_VERDICT', which is" >&2
echo "  neither RED nor GREEN. classify_leg has grown a case this branch does" >&2
echo "  not know about; no verdict is claimed." >&2
verdict 3

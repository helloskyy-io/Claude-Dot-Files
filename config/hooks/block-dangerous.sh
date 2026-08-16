#!/usr/bin/env bash
# PreToolUse hook: blocks destructive bash commands
# Receives JSON on stdin from Claude Code, returns deny decision if dangerous
#
# This is the PRIMARY safety layer for autonomous (headless) mode, where
# --dangerously-skip-permissions bypasses the allow/deny lists in settings.json.
# Hooks still fire regardless, so this hook must catch everything that should
# NEVER run regardless of permission mode.
#
# ---------------------------------------------------------------------------
# THREAT MODEL (scope of what this hook addresses)
# ---------------------------------------------------------------------------
#
# EVERY COMMAND NAMED IN THIS BLOCK IS EXECUTABLE, AND SO IS EVERY CLAIM MADE
# ABOUT A PATTERN BELOW. The `PASSES THROUGH:` / `BLOCKED ANYWAY:` markers in
# this block, and the `MUST BLOCK:` / `MUST ALLOW:` markers on each pattern,
# are parsed by `testing/config-hooks/tests/unit/test_block_dangerous.py` and
# asserted against this hook as it actually behaves. A claim that stops being
# true fails the suite.
#
# That is deliberate and it is the fix for a measured defect class, not
# decoration. Three separate defects (issues #59, #60, #62, all folded into
# #61) were the same shape: a pattern that did not match what it named, four
# patterns that matched more than they named, and this block describing two
# caught cases as gaps while staying silent on three real ones. Prose cannot
# detect its own drift and neither can a regex; the markers make the
# relationship between a pattern and what it CLAIMS to cover checkable.
#
# WHAT THE MARKERS DO NOT GUARANTEE — read this before trusting them. They
# check the pattern against what its AUTHOR WROTE DOWN. They cannot check it
# against what the author should have written down, so a boundary nobody
# thought to probe is a boundary nobody checks. That is not hypothetical: the
# first version of the `curl … | (sh|bash|zsh)` right boundary below was
# `([[:space:]]|$)`, every claim beside it was true, the whole suite was green,
# and `curl … | bash;true` sailed through. The things that make the mechanism
# more than self-consistency are therefore mechanical rather than authorial,
# and all of them are in the suite:
#   - EVERY pattern must carry a `MUST ALLOW:` as well as a `MUST BLOCK:`,
#     because all four defects found by review were in the ALLOW/boundary
#     direction and an optional claim is not a check;
#   - every dangerous command in the corpus is re-run with a shell separator
#     (`;true`, `&`, `&& echo ok`, `|cat`) APPENDED and must STILL be denied,
#     which probes the boundary at the END of the match;
#   - every dangerous command is re-run with its INTERNAL separators respelled
#     — tabs, doubled spaces, the space after a redirect operator removed, and
#     a word split across a backslash-newline continuation — and must STILL be
#     denied, which probes the separators INSIDE the match.
#
# THE SECOND AND THIRD ARE ONE CLASS SEEN AT TWO POSITIONS, and reading them as
# one thing is the point. A pattern that says "a space goes here" has ENUMERATED
# one spelling of a separator, and everything not enumerated passes. The
# end-of-match half was fixed first; the sweep built for it appends to the end
# of the command, so it structurally could not see the same defect sitting
# between a keyword and its operand — and nearly the whole corpus was passing
# with a tab in place of a space while that sweep was green. The remedy for the
# mid-match half is the canonicalization step further down rather than a
# boundary edit per pattern; see the comment there for why. THE MEASURED
# FIGURES ARE STATED ONCE, beside `_RESPELLINGS` in the suite, and are not
# repeated here — this file had four copies of them and three stale prose
# totals besides, which is the drift this whole block is about.
#
# WHAT THIS HOOK CATCHES (in-scope) — FIVE CLASSES, and the test for each is
# *is it unrecoverable*:
#   1. Disk and filesystem destruction — mkfs, wipefs, fdisk/parted on a device
#   2. Raw block-device writes — dd, or a redirect, onto /dev/sd|nvme|hd|…
#   3. Recursive delete of a SYSTEM path — /, ~, /etc, /usr, /home/<user>,
#      and bare /tmp. NOT of scratch or a project directory.
#   4. Bare `git push --force`. `--force-with-lease` is deliberately permitted:
#      the safety rule names it as the sanctioned form for an instructed rebase.
#   5. The authentication boundary — /etc/{passwd,shadow,sudoers} and any
#      authorized_keys.
#   - Any event it cannot understand. See "FAILING CLOSED" below.
#
# THIS LIST WAS FIFTY-NINE PATTERNS UNTIL 2026-08-15, and `settings.json` held
# forty-nine permission-deny rules beside it. What went, and why, is recorded
# above the array. The short version: everything recoverable. `git reset --hard`
# and `git clean` come back from the reflog; `sudo` is too broad and everything
# catastrophic under it is caught by classes 1 and 2; the SQL and kubectl
# patterns guarded systems this fleet does not have; `shutdown`/`reboot` cost a
# read-only `findmnt` a denial for the word appearing in an `echo`.
#
# WHAT THIS HOOK DOES NOT CATCH (out-of-scope, known gaps):
#   - **Obfuscated commands** — the dangerous payload is hidden in a base64
#     blob, hex-encoded shell, or other indirection. Not detected.
#     PASSES THROUGH: bash -c "$(echo cm0gLXJmIC8= | base64 -d)"
#   - **Variable indirection** — the dangerous content was placed in the
#     variable in an earlier turn, so the hook sees the reference and not the
#     resolved content.
#     PASSES THROUGH: eval "$evil_var"
#   - **Aliasing** — the alias was DEFINED IN AN EARLIER TURN, so this turn's
#     command is nothing but its name. Defining and invoking it in one string
#     is caught; see "CAUGHT, THOUGH IT READS LIKE A GAP" below.
#     PASSES THROUGH: safe
#   - **Here-strings or unusual quoting** — quoting that splits a keyword
#     defeats the patterns. Note what this no longer says: the patterns used to
#     assume ONE SPACE between a keyword and its operand, and that assumption
#     was a defect rather than a gap — it is fixed by the canonicalization step
#     below, so a TAB or a doubled space no longer defeats them. Quoting inside
#     the KEYWORD ITSELF still does. A LEADING BACKSLASH DOES NOT; see below.
#     PASSES THROUGH: r''m -rf /
#   - **Subshell smuggling** — dangerous content inside `$(...)`, `<(...)`, or
#     backticks that the regex doesn't unpack.
#     PASSES THROUGH: bash -c "$(cat /tmp/payload.sh)"
#   - **Under-matches in the patterns themselves** — ACCEPTED, not overlooked
#     (issue #60). The `/etc/` patterns cover shell redirects only, so a copy
#     onto a system file passes. `authorized_keys` is covered for `~/` and
#     `/root/` only — BOTH now carry the append AND the truncating operator,
#     which is a correction and not a widening: `/root/` had only `>>`, so the
#     more destructive of the two writes passed while this sentence said the
#     path was covered. An expanded absolute home path still passes, and that
#     half is the accepted gap. Only `purge`
#     and `remove --purge` are covered, so a plain remove passes. Widening
#     these was considered and declined: each trades a slice of false-positive
#     risk on the SOLE live control of an autonomous run, and the risk profile
#     below argues for naming them rather than widening. Revisit under "WHEN
#     TO REVISIT".
#     THE HOME-PATH GAP CLOSED ON 2026-08-15, incidentally rather than by
#     design: the five-pattern rewrite spells the authentication boundary as
#     `[^ ]*\.ssh/authorized_keys`, which reaches any path ending that way
#     instead of only `~/` and `/root/`. Recorded because the accepted gap it
#     replaces was argued for at length above, and a reader comparing the two
#     should see that the argument was overtaken rather than overruled.
#     PASSES THROUGH: cp /tmp/evil /etc/passwd
#     PASSES THROUGH: apt remove nginx
#     BLOCKED ANYWAY: echo ssh-ed25519 AAAA >> /home/puma/.ssh/authorized_keys
#
# CAUGHT, THOUGH IT READS LIKE A GAP:
#   Both of these were listed as gaps until issue #60. They are not, and a
#   later narrowing made on the belief that they already pass would be a
#   silent regression — which is why they are pinned rather than merely noted.
#   - An alias DEFINED AND INVOKED in the same command string USED to be caught
#     — the body is in the string the hook inspects, and the broad `rm -rf `
#     pattern matched it there. It is a gap as of 2026-08-15: pattern 3
#     terminates the target with a space, a shell separator or end-of-string,
#     and inside an alias the target is followed by a quote. Accepted rather
#     than chased: defining and invoking a destructive alias in one string is
#     deliberate evasion, and this hook's threat model is accident.
#     PASSES THROUGH: alias safe='rm -rf /' && safe
#   - A leading backslash: the left guard on these patterns is `[^a-z]`, which
#     a backslash satisfies, so `\rm` matches exactly as `rm` does.
#     BLOCKED ANYWAY: \rm -rf /
#
# KNOWN OVER-MATCH, ACCEPTED (issue #62):
#   - The patterns match anywhere in the command string, so WRITING ABOUT a
#     dangerous command is blocked as though running it. There is no clean
#     regex fix: telling mention from use needs a shell parser, which is a
#     larger change with its own failure modes on the only live control. This
#     over-blocks, which is the safe direction, and it is recorded here so it
#     is a ruling rather than a surprise. The over-matches that blocked
#     ORDINARY work were narrowed instead — `git push --force-with-lease`,
#     `curl … | shasum`, `./confirm -f` (issue #62), and then, found by review
#     of the fix for those, `git checkout -- ./src/app.py`,
#     `git checkout -- .gitignore` and `DELETE FROM … WHERE 100 < retries`.
#     See those patterns' MUST ALLOW claims. That a review of four over-match
#     fixes found three more is the argument for the mandatory-`MUST ALLOW`
#     rule stated above, not a count worth chasing to zero.
#     BLOCKED ANYWAY: echo "never run rm -rf / on this box" >> NOTES.md
#
# OVER-MATCH NARROWED, RULED BY THE OPERATOR (2026-08-13) — SQL keywords in prose:
#   - The acceptance above rested on "there is no clean regex fix". That is true
#     for SHELL patterns and false for the five SQL ones, and the difference is
#     the anchor. Every other pattern in the array is anchored to a command
#     position; `DROP TABLE`, `DROP DATABASE`, `DROP SCHEMA`, `TRUNCATE ` and
#     `DELETE FROM … WHERE 1` were the ONLY unanchored members. Under `grep -Ei`
#     — case-insensitive, and correctly so, since `RM -RF` must match — a bare
#     SQL keyword is an ENGLISH-WORD matcher.
#   - MEASURED: five read-only commands were blocked inside twenty minutes for
#     containing these words in prose, in a `grep` pattern, in a test fixture,
#     and in the command that was editing this file.
#   - THIS IS NOT A NARROWING OF INTENT, and the test suite is the evidence:
#     every SQL deny case in it is already written as `psql -c "…"`. The tests
#     always documented a client context; the patterns never enforced it.
#     Anchoring makes the pattern match what its own tests assert.
#   - The fleet also runs no SQL. Searching scripts/ and config/ for a client or
#     a keyword returns one file, whose only hit is the word "TRUNCATED" in a
#     docstring. These five have never had a real invocation to catch here.
#   - The rule the ruling rests on: a control that blocks ordinary work gets
#     routed around, and a routed-around control is worse than none because the
#     safety story still claims it is there. That is issue #62's own opening
#     argument, applied to the one case #62 left unruled.
#   RESOLVED 2026-08-15 BY DELETION. The five SQL patterns are gone. The
#   paragraph above argued they had never had a real invocation to catch, and
#   the narrowing to five patterns took the conclusion the argument was already
#   making: a pattern guarding a database this fleet does not have is cost with
#   no coverage, and it was one of the shapes over-matching on prose.
#     PASSES THROUGH: psql -c "DROP TABLE users"
#     PASSES THROUGH: sqlite3 app.db "DROP TABLE t"
#
# OVER-MATCH NARROWED, MEASURED (2026-08-10) — a scratch delete under /tmp:
#   The `rm` patterns match a recursive delete of ANY target, which made
#   `rm -rf /tmp/<scratch>` a denial. That is the ordinary business of a
#   dispatch, not a destructive act, and it was measured HALTING TWO COMPLETED
#   RUNS overnight — a mutation sandbox being reset, and `review-pr` cleaning
#   up the trial merge it had just used to reach `VERDICT: MERGE`. Both runs
#   lost their result. A fail-closed control that denies valid events is its
#   own outage, and this is the sole control operating unattended, so this
#   over-match is narrowed rather than accepted — the same call already made
#   for `git push --force-with-lease` and `curl … | shasum` under issue #62.
#   THE MECHANISM CHANGED ON 2026-08-15 AND THE PROBLEM DID NOT. It was a
#   193-line SCRATCH-DELETE ELISION that rewrote $CMD to drop scratch deletes
#   before matching — an exception engine built beside an over-broad rule. The
#   rule is now narrow instead: pattern 3 NAMES the system paths it refuses,
#   so a scratch delete never matches in the first place and there is nothing
#   to except. The elision was verified inert before removal — nine cases
#   spanning every shape it handled, zero verdict changes.
#
#   A RELATIVE TARGET IS NO LONGER COVERED, and that is a deliberate loss. The
#   elision tracked `cd` into scratch so it could reason about `rm -rf build`;
#   nothing does now, so a recursive delete of a relative path passes wherever
#   it is run. It is accepted because such a delete is recoverable — a project
#   directory comes back from its remote — and this hook's remit is narrowed to
#   what is not.
#     PASSES THROUGH: rm -rf /tmp/pr75-merge
#     PASSES THROUGH: cd /tmp && rm -rf m6 && mkdir m6 && cd m6
#     PASSES THROUGH: cd /home/puma && rm -rf Repos
#     BLOCKED ANYWAY: rm -rf /tmp
#     BLOCKED ANYWAY: rm -rf /tmp/build /
#     BLOCKED ANYWAY: rm -rf /tmp/evil && rm -rf /tmp/evil /
#
# FAILING CLOSED (issue #61, `hook-scripts.md § The headless safety
# invariant` point 2):
#   An event this hook cannot understand is DENIED, not allowed. Malformed
#   JSON, a payload that is not an object, an absent or non-string
#   `tool_name`, a Bash payload whose `command` is absent or not a string, and
#   `jq` missing from PATH all deny. So does a pattern that cannot be
#   EVALUATED — the invariant covers both halves, and the matching loop reads
#   grep's status as three outcomes rather than two for that reason. The
#   distinction that matters, and the one
#   whose collapse makes a fail-open defect look correct in review: a hook
#   that legitimately DOES NOT APPLY to an event exits 0, while a hook that
#   COULD NOT TELL WHAT THE EVENT IS denies. A well-formed event naming some
#   other tool is the first case and is the overwhelmingly common one.
#
# THREAT-MODEL CONTEXT:
#   The operator is an interactive senior engineer using Claude for
#   coding tasks. Autonomous LLM dispatches have not demonstrated
#   intent or capability to construct deliberate bypasses of the
#   patterns below — the failure mode this hook protects against is
#   accidental destructive commands (the model writes `rm -rf` because
#   it thinks it should clean up, not because it's adversarial).
#   The acceptable risk profile reflects this: catch the common
#   accidents reliably; do not attempt to defend against an adversarial
#   LLM constructing intentional bypasses (that would require sandboxing
#   the entire workflow, which is a different threat model).
#
# WHEN TO REVISIT:
#   - Operator starts dispatching with untrusted task content (e.g.
#     workflows triggered by external PR comments from arbitrary users)
#   - Evidence of an LLM constructing obfuscated commands in logs
#   - A second person uses these workflows on their own machine and
#     would expect stronger guarantees than "trust the regex"
#   - Any of the three accepted under-matches above is hit in practice — that
#     converts a considered trade into observed exposure
#
# Full threat-model documentation is deferred with watch-criteria in
# `docs/development/cpi-decisions.md`. The hook's tests live at
# `testing/config-hooks/tests/unit/test_block_dangerous.py` (issue #52).
# ---------------------------------------------------------------------------

INPUT=$(cat)

# `jq` is how this hook reads its input AND how it emits a decision. Without it
# the event cannot be parsed, so the answer is deny — the alternative is the
# fail-open hole issue #61 was filed about, reachable by nothing more exotic
# than a truncated PATH.
#
# This is the one deny path that cannot use `jq -n`, because `jq` is precisely
# what is missing. `hook-scripts.md § Critical Rules` forbids raw string
# INTERPOLATION for JSON output, and its stated reason is escaping: an
# interpolated variable can break the payload. The literal below interpolates
# nothing — it is a constant, and the suite parses it as JSON so a typo in it
# fails the tests rather than shipping an unparseable denial.
if ! command -v jq >/dev/null 2>&1; then
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Blocked by safety hook: jq is not available, so this event could not be parsed"}}'
  exit 0
fi

# THE OUTPUT CONTRACT IS `hookSpecificOutput`, NOT A TOP-LEVEL `decision`.
# This hook emitted `{"decision":"deny"}` from the day it was written and
# therefore never blocked anything: Claude Code reads
# `hookSpecificOutput.permissionDecision` for PreToolUse, and the top-level
# `decision` field is not valid for tool events. The shape below is the
# documented one (code.claude.com/docs/en/hooks).
#
# WHERE THE BUG CAME FROM, so it is not reintroduced: the `Stop` event — also
# configured in this repo's settings.json — DOES take a top-level `decision`.
# One event's contract was copied to another, and every test asserted the copy.
#
# exit 0 is correct and deliberate: with exit 0 Claude Code reads the JSON and
# lets it decide. Exit 2 would block unconditionally, ignoring the JSON, which
# would make the allow path unexpressible.
deny() {
  jq -n --arg reason "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
  exit 0
}

# Which tool is this? Anything other than a JSON object carrying a non-empty
# string `tool_name` is an event we cannot identify, and an unidentified event
# is denied.
#
# `jq`'s exit status is CAPTURED rather than discarded — that discard was the
# defect. `error(...)` exits 5, a parse failure exits 2 or 5, and an empty or
# whitespace-only stdin makes `jq` produce NO OUTPUT while still exiting 0,
# which is why the emptiness of $TOOL is checked alongside the status. The
# assignment sits inside `if !` so the status is readable and so a future
# `set -e` could not turn this branch into an abort.
if ! TOOL=$(printf '%s' "$INPUT" | jq -r '
      if type != "object" then
        error("event is not a JSON object")
      elif (.tool_name | type) != "string" or .tool_name == "" then
        error("tool_name is absent, empty, or not a string")
      else
        .tool_name
      end' 2>/dev/null) || [ -z "$TOOL" ]; then
  deny "Blocked by safety hook: could not determine which tool this event invokes"
fi

# A well-formed event for a tool this hook does not police. It legitimately
# DOES NOT APPLY — exit 0. This is the common case and denying here would halt
# ordinary work; it is the line that keeps "fail closed" from meaning "fail".
if [ "$TOOL" != "Bash" ]; then
  exit 0
fi

# A Bash event whose command cannot be read as a string is one whose rule
# cannot be evaluated, so it denies. The non-string case is not pedantry: `jq
# -r` renders an array or object across several lines, and a command smuggled
# through as `["rm","-rf","/"]` would be matched against fragments no pattern
# covers.
if ! CMD=$(printf '%s' "$INPUT" | jq -r '
      if (.tool_input | type) != "object" then
        error("tool_input is absent or not an object")
      elif (.tool_input.command | type) != "string" then
        error("command is absent or not a string")
      else
        .tool_input.command
      end' 2>/dev/null); then
  deny "Blocked by safety hook: this Bash event carries no readable command string"
fi

# An empty command string is fully understood and matches nothing — allow. The
# rule WAS evaluated here, which is what separates this from the denials above.
if [ -z "$CMD" ]; then
  exit 0
fi

# ---------------------------------------------------------------------------
# WHITESPACE CANONICALIZATION — the class fix for a separator defect measured
# across nearly the whole of the suite's dangerous corpus. (Figures beside
# `_RESPELLINGS` in the suite; stated once, on purpose.)
# ---------------------------------------------------------------------------
#
# Every pattern below spells a token separator as a literal space (` `, ` +`).
# That is an ENUMERATION of one spelling of "the shell separated these two
# words", and the shell admits several: a TAB, a run of spaces, a CR before the
# newline. `systemctl<TAB>stop nginx`, `TRUNCATE<TAB>TABLE users` and
# `wipefs<TAB>-a /dev/sda` were all ALLOWED by this hook. It is the SAME defect
# as the right-boundary enumeration described beside the `curl … | (sh|bash)`
# entry — one position to the left. That one sits after the match; this one
# sits between a keyword and its operand, which is why the suite's end-of-
# command separator sweep could not see it.
#
# WHY HERE AND NOT IN THE PATTERNS, decided by execution rather than taste.
# Appending the ratified `([^[:alnum:]_-]|$)` boundary to the eight
# keyword+operand patterns turns `cat doas.conf`, `man wipefs` and
# `echo needs sudo` into denials — the first two are MUST ALLOW claims this
# hook already states. Canonicalizing the INPUT fixes every pattern at once,
# changes no boundary, and so cannot introduce a boundary false positive. The
# patterns are written against a single-space canonical form; nothing was ever
# putting the input INTO that form.
#
# PER LINE, deliberately — with ONE exception, and the exception is the third
# member of this class rather than a special case. Collapsing newlines in
# general would let the `.*` patterns span two unrelated commands: `git push
# origin main` on one line and a `-f` mentioned on the next would match
# `git push.*-f`. `grep` is line-oriented and so is this hook; that stays true.
#
# But a BACKSLASH-NEWLINE is not a line break at all — the shell DELETES it
# before parsing, so `rm -r\` + newline + `f /tmp/build` IS `rm -rf /tmp/build`
# and there is exactly one command there, not two. Measured: it was ALLOWED,
# for the same reason a tab was — the patterns model one spelling of "these two
# tokens are joined" and the shell has three (a space run, a tab, and a
# continuation that is no character at all). Deleting it here is not joining
# lines; it is reading the line the shell will read.
#
# ALL FOUR REMAINING WHITESPACE FORMS ARE CONVERTED UNCONDITIONALLY, not just a
# CR in the CRLF position. A bare CR with no LF then reads as a separator
# rather than as a line break, which merges two would-be lines — the
# over-blocking direction, on input no shell treats as two commands anyway.
#
# NO SUBPROCESS. A `sed` or `tr` here would add a second binary whose absence
# empties `$CMD` and allows everything — reintroducing the exact fail-open
# shape issue #61 was filed about, in the fix for its sibling. Bash's own
# substitution cannot fail that way.
CMD="${CMD//\\$'\n'/}"
CMD="${CMD//$'\t'/ }"
CMD="${CMD//$'\r'/ }"
CMD="${CMD//$'\v'/ }"
CMD="${CMD//$'\f'/ }"

# RUNS OF SPACES COLLAPSE BY HALVING, NOT BY `${CMD//+( )/ }`. The extglob form
# reads better and was this hook's ENTIRE cost: measured on 2026-08-14 at 1.80s
# for a 1 KB command and 14.20s for 2 KB, growing ~8x per doubling. This hook
# runs on EVERY Bash tool call of every run, so one 11 KB markdown heredoc held
# a live build for 8m44s at 99.9% CPU before it was killed. A quantified pattern
# in a bash global substitution re-scans from every position; a fixed two-space
# pattern does not. Each pass at least halves the longest run, so this is
# log2(longest run) passes of a linear substitution.
#
# STILL NO SUBPROCESS, for the reason the block above states: a `sed` or `tr`
# whose absence empties `$CMD` allows everything, which is the fail-open shape
# issue #61 was filed about.
while [[ $CMD == *"  "* ]]; do
  CMD="${CMD//  / }"
done
# UNSET DEFENSIVELY — nothing in this file turns extglob ON any more, and this
# line stays because bash INHERITS shopt settings through `BASHOPTS`, so "we
# never set it" is not the same as "it is off". Leaving it on is a live footgun
# rather than a tidiness point: a literal `+(` inside a later `[[ =~ ]]` parses
# as the extglob operator instead of a regex quantifier, bash raises `syntax
# error near '+('`, execution CONTINUES, and the script reaches `exit 0` — the
# fail-open hole issue #61 was filed about. That happened once while this file
# was being written (see the elision block below).
shopt -u extglob

# THE SCRATCH-DELETE ELISION WAS REMOVED HERE ON 2026-08-15, and what it did
# matters more than that it is gone. It rewrote $CMD to drop `rm -rf
# /tmp/<name>` segments before matching, because the pattern set then held a
# broad `rm -rf ` rule that could not tell a run's own scratch directory from
# anything else — an over-match measured killing COMPLETED autonomous runs
# twice in one night.
#
# It is gone because the rule it excepted is gone. Pattern 3 now names the
# system paths it refuses instead of refusing every recursive delete, so it is
# MORE permissive than the carve-out ever was and there is nothing left to
# carve out. Verified rather than assumed: with the block disabled, none of
# nine cases spanning every shape it handled changed verdict.
#
# THE GENERAL LESSON, and it is the third instance found on one day: when a
# rule over-fires, NARROW THE RULE. Do not build an exception engine beside
# it. This block was 193 lines and an O(separators x length) walk that cost
# 87 seconds on a large command; the deny list in settings.json was the same
# mistake one layer up.

# Regex patterns (matched with grep -Ei)
#
# EVERY ENTRY CARRIES AT LEAST ONE `MUST BLOCK:` CLAIM AND AT LEAST ONE
# `MUST ALLOW:` CLAIM. Both are mandatory and the suite refuses a pattern
# missing either. `MUST ALLOW` used to be optional, and that asymmetry is why
# four boundary defects survived the first pass of this mechanism: the enforced
# half caught patterns that stopped matching what they named, while every one
# of the four was a pattern matching more — or less — than its boundary
# implied. The suite asserts each claim against THAT pattern with the same
# engine and flags the loop below uses, and additionally runs every MUST ALLOW
# through the whole hook — so a pattern cannot be narrowed into uselessness,
# widened into a false positive, or added without stating both halves.
REGEX_PATTERNS=(
  # ---------------------------------------------------------------------------
  # FIVE PATTERNS, AND THE TEST FOR EACH IS *IS IT UNRECOVERABLE*.
  #
  # This array held 59 patterns until 2026-08-15, and `settings.json` held 49
  # permission-deny rules beside it. The deny list was added as a compensating
  # control while this hook was unreliable, against the operator's advice, and
  # was never retired when the hook was fixed — so two mechanisms enforced
  # overlapping rules with different semantics and no record of which one fired.
  # A reviewer's own `/tmp` cleanup was refused by the deny rule while this hook
  # allowed it. The deny list is now empty; this is the only control.
  #
  # WHAT WAS DROPPED AND WHY: recoverability. `git reset --hard` and `git clean`
  # are recoverable from the reflog; `sudo` is too broad and everything
  # catastrophic under it is caught by classes 1 and 2; the database patterns
  # guard a database this fleet does not have; `systemctl`/`iptables`/`ufw`
  # guard infrastructure these machines do not reach; `shutdown`/`reboot` cost a
  # read-only `findmnt` a denial for the word appearing in an `echo`, and a
  # reboot is recoverable; `chmod 777`, `pip uninstall`, `crontab -r` and the
  # rest are nuisance-level.
  #
  # MEASURED, and it is the argument for narrowing rather than a bonus: EIGHT
  # denials were recorded on 2026-08-15 and NONE was a destructive command about
  # to run. Seven were dangerous text appearing as DATA — inside a test fixture,
  # a commit message, an analysis script. The `rm` narrowing below removes that
  # whole class, because every one of them targeted scratch or a project
  # directory rather than a system path.
  # ---------------------------------------------------------------------------

  # 1 · Disk and filesystem destruction. No undo exists.
  #
  # EACH VERB CARRIES ITS OWN OPERAND REQUIREMENT, and collapsing them into a
  # bare alternation over the four names was wrong: it denied `fdisk -l`,
  # `parted --version` and a `grep` for the word — all read-only. The operand is
  # what separates inspecting a disk from destroying one, and the sub-patterns
  # below are the originals, which carried MUST ALLOW claims proving exactly
  # those cases.
  # MUST BLOCK: mkfs.ext4 /dev/sda1
  # MUST BLOCK: wipefs -a /dev/sdb
  # MUST BLOCK: fdisk /dev/sda
  # MUST ALLOW: fdisk -l
  # MUST ALLOW: parted --version
  # MUST ALLOW: grep -rn mkfs docs/
  '(^|[^a-z])(mkfs[.]|wipefs |fdisk +/dev/|parted +/dev/)'

  # 2 · Raw block-device write. Same class, reached by a different verb.
  # MUST BLOCK: dd if=/dev/zero of=/dev/sda bs=1M
  # MUST ALLOW: dd if=/dev/zero of=/tmp/testfile bs=1M count=1
  '(dd .*of=|>[|]? *)/dev/(sd|nvme|hd|disk|vd)'

  # 3 · Recursive delete of a SYSTEM path — never of scratch or a project dir.
  # The narrowing is the point: an unqualified `rm -rf` guard fires on the text
  # far more often than on the act, and `/home/<user>` is bounded to the home
  # itself so ordinary work under it stays writable.
  # EVERY OPERAND IS INSPECTED, not only the first. `rm -rf /tmp/build /` reads
  # as a scratch delete until the second operand, and a pattern anchored to the
  # first argument passes it. `( +[^ ]+)*` walks the earlier operands so the
  # dangerous one is found wherever it sits.
  #
  # BARE `/tmp` AND `/var/tmp` ARE BLOCKED while `/tmp/<name>` is allowed: the
  # scratch carve-out exists for THIS run's directory, and `/tmp` itself is
  # every other run's sandbox.
  # MUST BLOCK: rm -rf /
  # MUST BLOCK: rm -rf /etc
  # MUST BLOCK: rm -rf /home/puma
  # MUST BLOCK: rm -rf /tmp
  # MUST BLOCK: rm -rf /tmp/build /
  # MUST ALLOW: rm -rf build
  # MUST ALLOW: rm -rf /tmp/scratch-probe
  # MUST ALLOW: rm -rf /home/puma/Repos/claude-dot-files/.claude/worktrees/build-123
  # THE TERMINATOR INCLUDES SHELL SEPARATORS, NOT JUST SPACE AND END-OF-STRING.
  # `rm -rf /tmp;true` ends the target with `;`, and a terminator of `( |$)`
  # reads it as part of the path and matches nothing — the trailing-separator
  # evasion the suite sweeps every dangerous command for.
  '(^|[^a-z])rm +-[A-Za-z]*[rRf][A-Za-z]*( +[^ ;&|]+)* +(/|~|/tmp|/var/tmp|/(bin|boot|etc|lib|opt|root|sbin|usr|var)(/[^ ;&|]*)?|/home(/[^/ ;&|]+)?)([ ;&|]|$)'

  # 4 · Bare force-push. `--force-with-lease` is DELIBERATELY not matched: the
  # safety rule names it as the sanctioned mechanism for an instructed rebase,
  # and the lease is what makes it refuse when someone else has pushed.
  # MUST BLOCK: git push --force origin main
  # MUST ALLOW: git push --force-with-lease origin main
  'git push.*--force([^-]|$)'

  # 5 · Authentication boundary. Cheap, and reachable by an agent running under
  # --dangerously-skip-permissions.
  # MUST BLOCK: echo x > /etc/shadow
  # MUST BLOCK: echo hacker >> ~/.ssh/authorized_keys
  # MUST ALLOW: cat /etc/passwd
  '>[|]? *(/etc/(passwd|shadow|sudoers)|[^ ]*\.ssh/authorized_keys)'
)

# Fixed-string patterns (matched with grep -Fi, no regex interpretation)
FIXED_PATTERNS=(
  # MUST BLOCK: :(){ :|:& };:
  # MUST ALLOW: greet(){ echo hi; }
  ':(){ :|:& };:'
)

# `printf '%s\n'` rather than `echo`, matching the input path above. `echo`
# treats a lone argument consisting only of `-neE` characters as its own
# options and prints nothing; no real command has that shape, but the parsing
# side of this file already avoids `echo` for exactly that reason and a safety
# control should not read one way at the top and another at the bottom.
#
# `grep`'s status is read as THREE outcomes, not two. `0` is a match and `1` is
# a clean no-match; anything else — `2` for an invalid pattern, `127` for a
# `grep` that is not on PATH — means the rule COULD NOT BE EVALUATED, and the
# invariant makes that a denial just as an unparseable event is. Testing the
# pipeline with a bare `if` collapses `1` and `2` into "falsy", which is the
# same fail-open shape as the discarded `jq` status one layer up: a corrupted
# array entry or a truncated PATH would have silently disabled every pattern
# after it while the hook kept reporting allow. Found by execution, not review.
for pattern in "${REGEX_PATTERNS[@]}"; do
  printf '%s\n' "$CMD" | grep -qEi "$pattern"
  MATCH_STATUS=$?
  if [ "$MATCH_STATUS" -eq 0 ]; then
    deny "Blocked by safety hook: matched destructive pattern ${pattern}"
  elif [ "$MATCH_STATUS" -ne 1 ]; then
    deny "Blocked by safety hook: could not evaluate pattern ${pattern} (grep exited ${MATCH_STATUS})"
  fi
done

for pattern in "${FIXED_PATTERNS[@]}"; do
  printf '%s\n' "$CMD" | grep -qFi "$pattern"
  MATCH_STATUS=$?
  if [ "$MATCH_STATUS" -eq 0 ]; then
    deny "Blocked by safety hook: matched destructive pattern ${pattern}"
  elif [ "$MATCH_STATUS" -ne 1 ]; then
    deny "Blocked by safety hook: could not evaluate fixed pattern ${pattern} (grep exited ${MATCH_STATUS})"
  fi
done

exit 0

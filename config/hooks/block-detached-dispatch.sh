#!/usr/bin/env bash
# PreToolUse hook: blocks `nohup`, which detaches a dispatch from the harness.
#
# ---------------------------------------------------------------------------
# WHY THIS IS A SEPARATE HOOK FROM `block-dangerous.sh`
# ---------------------------------------------------------------------------
#
# Its neighbour states its own admission test in one line: *"FIVE PATTERNS, AND
# THE TEST FOR EACH IS *IS IT UNRECOVERABLE*."* That array was cut from 59
# patterns to 5 on 2026-08-15 after a measurement — EIGHT denials recorded in a
# day, NONE a destructive command about to run, SEVEN of them dangerous text
# appearing as DATA.
#
# `nohup` fails that test twice. A detached process is entirely RECOVERABLE:
# find it, kill it, run it again. And it is exactly the data-shaped false
# positive that drove the narrowing — this repo's own memory file says "NEVER
# nohup", `config/rules/personal-tooling.md` discusses it, and this very file
# is full of the word. A substring match would deny `grep -rn nohup`.
#
# Adding it next door would have reopened a rule that is five days old and was
# measured into existence. So it lives here, with its own threat model.
#
# ---------------------------------------------------------------------------
# WHAT THIS PREVENTS
# ---------------------------------------------------------------------------
#
# `nohup <dispatch> &` detaches the process from Claude Code. The consequence is
# not danger, it is BLINDNESS: the harness stops tracking it, so nothing
# notifies anyone when the run finishes, its output is not captured, and a
# failure is indistinguishable from still-running. The operator's tray shows
# nothing. What follows is invariably a hand-rolled polling loop that burns
# turns re-discovering what the harness would have reported for free.
#
# The Bash tool's `run_in_background: true` does all of it: tracks the process,
# re-invokes on completion, captures output to a file.
#
# ---------------------------------------------------------------------------
# THIS HOOK FAILS OPEN, AND ITS NEIGHBOUR FAILS CLOSED
# ---------------------------------------------------------------------------
#
# A deliberate divergence, and the direction follows the CONSEQUENCE rather than
# the convention. `block-dangerous.sh` denies on an event it cannot parse because
# the thing it guards is unrecoverable, so a missed deny is a disaster and a
# wrong deny is an inconvenience. Here it is the other way round: a missed deny
# costs one detached process the operator can kill, while a wrong deny halts
# ordinary work to prevent nothing. So anything this hook cannot read with
# certainty — no `jq`, an unparseable event, a non-Bash tool, a command that is
# not a string — exits 0 and lets the work through.
#
# ---------------------------------------------------------------------------
# COMMAND POSITION, NOT SUBSTRING
# ---------------------------------------------------------------------------
#
# The key is "runs nohup"; the class a substring match expresses is "contains
# the letters nohup", and those differ on every mention of the rule itself. So
# the pattern anchors to command position: line start, or immediately after a
# separator (`;` `&` `|` `(` or a backtick), allowing whitespace. `&&` and `||`
# are covered because their final character is in that set.
#
# MUST BLOCK: nohup ./build.sh &
# MUST BLOCK: cd /repo && nohup scripts/workflows/temporal/scripts/build.sh --pr 1 &
# MUST BLOCK: echo start; nohup python run_build.py
# MUST BLOCK: (nohup long-thing &)
# MUST BLOCK: nohup
# MUST ALLOW: grep -rn nohup config/rules/
# MUST ALLOW: echo "never use nohup, use run_in_background"
# MUST ALLOW: git commit -m "block nohup in a hook"
# MUST ALLOW: ./nohuppy --run
# MUST ALLOW: ls -la
#
# Tests: `testing/config-hooks/tests/unit/test_block_detached_dispatch.py`,
# which parses the claims above and asserts each against this hook as it runs.
# ---------------------------------------------------------------------------

INPUT=$(cat)

# No `jq` means no readable event. Fails OPEN, per the section above.
command -v jq >/dev/null 2>&1 || exit 0

TOOL=$(printf '%s' "$INPUT" | jq -r 'if type == "object" and (.tool_name | type) == "string"
                                     then .tool_name else "" end' 2>/dev/null) || exit 0
[ "$TOOL" = "Bash" ] || exit 0

CMD=$(printf '%s' "$INPUT" | jq -r 'if (.tool_input | type) == "object"
                                       and (.tool_input.command | type) == "string"
                                    then .tool_input.command else "" end' 2>/dev/null) || exit 0
[ -n "$CMD" ] || exit 0

# `grep -E` reads line by line, so `^` anchors every line of a multi-line
# command, which is where a second command most often sits.
if printf '%s' "$CMD" | grep -qE '(^|[;&|(`])[[:space:]]*nohup([[:space:]]|$)'; then
  jq -n --arg reason \
"nohup is blocked in this workspace. Use the Bash tool's \`run_in_background: true\` instead.

nohup detaches the process from Claude Code: nothing tracks it, nothing notifies you when it finishes, its output is not captured, and a crash looks identical to still-running. The operator's tray shows nothing, and what follows is a hand-rolled polling loop that burns turns re-discovering what the harness reports for free.

\`run_in_background: true\` tracks the process, re-invokes on completion, and writes output to a file you can read while it runs. That is the option you want.

If you genuinely need a detached process, say so and ask the operator." \
    '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
  exit 0
fi

exit 0

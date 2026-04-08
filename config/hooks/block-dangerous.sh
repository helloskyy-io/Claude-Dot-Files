#!/usr/bin/env bash
# PreToolUse hook: blocks destructive bash commands
# Receives JSON on stdin from Claude Code, returns deny decision if dangerous

INPUT=$(cat)

TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty')
if [ "$TOOL" != "Bash" ]; then
  exit 0
fi

CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
if [ -z "$CMD" ]; then
  exit 0
fi

# Regex patterns (matched with grep -Ei)
REGEX_PATTERNS=(
  'rm +-r?f?r? '
  'rm +-fr '
  'git push.*--force'
  'git push.*-f( |$)'
  'git reset --hard'
  'git clean -f'
  'git checkout -- \.'
  'DROP TABLE'
  'DROP DATABASE'
  'TRUNCATE '
  'mkfs[.]'
  'dd if=.* of=/dev/'
  '> /dev/sd'
  'chmod -R 777'
)

# Fixed-string patterns (matched with grep -Fi, no regex interpretation)
FIXED_PATTERNS=(
  ':(){ :|:& };:'
)

for pattern in "${REGEX_PATTERNS[@]}"; do
  if echo "$CMD" | grep -qEi "$pattern"; then
    jq -n --arg reason "Blocked by safety hook: matched destructive pattern" \
      '{"decision": "deny", "reason": $reason}'
    exit 0
  fi
done

for pattern in "${FIXED_PATTERNS[@]}"; do
  if echo "$CMD" | grep -qFi "$pattern"; then
    jq -n --arg reason "Blocked by safety hook: matched destructive pattern" \
      '{"decision": "deny", "reason": $reason}'
    exit 0
  fi
done

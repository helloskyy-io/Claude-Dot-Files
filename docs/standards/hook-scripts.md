# Hook Script Standards

Conventions for writing hook scripts in `config/hooks/`.

## Purpose

Hook scripts are invoked by Claude Code at specific lifecycle events (PreToolUse, PostToolUse, Stop, etc.) as defined in `settings.json`. They provide deterministic guardrails and automation that Claude cannot ignore or work around.

## File Conventions

### Location
All hook scripts live in `config/hooks/` and are symlinked to `~/.claude/hooks/` via `install.sh`.

### Naming
Use kebab-case descriptive names that indicate the hook's purpose:
- `block-dangerous.sh` (what it does)
- `notify-done.sh` (what it does)
- `format-on-commit.sh` (what it does)

Avoid generic names like `hook1.sh` or `pre-tool.sh`.

### Executable
All hook scripts must be executable (`chmod +x`). The `install.sh` script preserves executable bits through symlinks.

### Shebang
Always use `#!/usr/bin/env bash` for portability, not `/bin/bash` or `/bin/sh`.

## Input Handling

**Hook scripts receive JSON on stdin, NOT via environment variables.**

Always read input with:
```bash
INPUT=$(cat)
```

Then parse with `jq`:
```bash
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty')
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
```

Use `// empty` in jq expressions to handle missing fields gracefully.

## Output Handling

### Allow (default)
Exit with code 0 and no output. Claude Code treats this as approval.
```bash
exit 0
```

### Deny
Output a JSON object with `decision: "deny"` and a `reason`. Use `jq -n` to build valid JSON — never string interpolation.

```bash
jq -n --arg reason "Blocked by safety hook: matched destructive pattern" \
  '{"decision": "deny", "reason": $reason}'
exit 0
```

**Never do this** (unsafe string interpolation):
```bash
echo "{\"decision\": \"deny\", \"reason\": \"$REASON\"}"  # BAD
```

## Tool Filtering

If your hook should only act on specific tools, check early and exit silently for others:

```bash
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty')
if [ "$TOOL" != "Bash" ]; then
  exit 0
fi
```

## Safety Script Patterns

For PreToolUse safety hooks (like `block-dangerous.sh`):

### Pattern Arrays
Split patterns into regex and fixed-string arrays. Regex patterns use `grep -Ei`, fixed patterns use `grep -Fi`.

```bash
# Regex patterns (matched with grep -Ei)
REGEX_PATTERNS=(
  'rm +-r?f?r? '
  'git push.*--force'
)

# Fixed-string patterns (matched with grep -Fi, no regex interpretation)
FIXED_PATTERNS=(
  ':(){ :|:& };:'
)
```

Fixed patterns are essential for strings with regex metacharacters (like fork bombs) that would fail regex parsing.

### Loop Matching
```bash
for pattern in "${REGEX_PATTERNS[@]}"; do
  if echo "$CMD" | grep -qEi "$pattern"; then
    jq -n --arg reason "Blocked by safety hook: matched destructive pattern" \
      '{"decision": "deny", "reason": $reason}'
    exit 0
  fi
done
```

## Documentation

Every hook script must include a header comment explaining:
1. What the hook does
2. When it fires (event type)
3. Any critical context the reader needs

Example:
```bash
#!/usr/bin/env bash
# PreToolUse hook: blocks destructive bash commands
# Receives JSON on stdin from Claude Code, returns deny decision if dangerous
#
# This is the PRIMARY safety layer for autonomous (headless) mode, where
# --dangerously-skip-permissions bypasses the allow/deny lists in settings.json.
# Hooks still fire regardless, so this hook must catch everything that should
# NEVER run regardless of permission mode.
```

## Settings.json Integration

Wire the hook in `config/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$HOME/.claude/hooks/block-dangerous.sh"
          }
        ]
      }
    ]
  }
}
```

Always reference via `$HOME/.claude/hooks/` (symlinked path), never the source repo path.

## Testing

Test hooks manually by piping JSON to them:

```bash
# Test a block scenario
echo '{"tool_name": "Bash", "tool_input": {"command": "sudo apt update"}}' | \
  ~/.claude/hooks/block-dangerous.sh

# Test an allow scenario (should produce no output)
echo '{"tool_name": "Bash", "tool_input": {"command": "ls -la"}}' | \
  ~/.claude/hooks/block-dangerous.sh
```

Verify both directions:
1. Dangerous patterns produce deny JSON
2. Safe commands produce no output

## Critical Rules

- **Hook scripts MUST NOT be interactive** — no prompts, no user input
- **Hook scripts MUST be fast** — they run on every matching tool call
- **Hook scripts MUST fail safe** — if something goes wrong, prefer allowing the action over blocking
- **Hook scripts MUST NOT have side effects beyond their stated purpose** — no logging to random files, no modifying state
- **Hook scripts MUST use `jq` for JSON output** — never raw string interpolation

## Related Documentation

- `docs/guide/workflows.md` — Why hooks are the safety layer for autonomous mode

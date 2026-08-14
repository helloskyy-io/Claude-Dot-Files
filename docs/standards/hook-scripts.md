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

Then parse with `jq`, **capturing jq's exit status rather than discarding it**:
```bash
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
```

**Do NOT use `// empty` to extract a field you are going to make a decision on.**
It collapses three different situations into one empty string: the field was
absent, the field was present and null, and **the input did not parse at all**.
The third is the dangerous one — a hook that cannot parse its event must deny
(§ The headless safety invariant point 2), and `// empty` makes that
indistinguishable from a field that was legitimately missing.

Two details in the form above are load-bearing:

- **The assignment sits inside `if !`** so the status is readable, and so that
  a later `set -e` cannot turn the branch into an abort.
- **Emptiness is checked alongside the status** because empty or
  whitespace-only stdin makes `jq` produce no output while still exiting `0`.

`// empty` remains fine for a field that is genuinely optional and whose
absence has a well-defined meaning — a description string used only in a log
line. The test is whether an unparseable event and an absent field should lead
to the same behaviour. For anything feeding a decision, they must not.

`config/hooks/block-dangerous.sh` is the worked reference for this whole
section.

## Output Handling

### Allow (default)
Exit with code 0 and no output. Claude Code treats this as approval.
```bash
exit 0
```

### Deny

**THE SHAPE IS PER-EVENT, AND GETTING IT WRONG IS SILENT.** A hook that emits the wrong shape
still runs, still matches, still exits 0 — and its decision is discarded. Nothing reports an
error, so the hook appears healthy while blocking nothing.

**For `PreToolUse`**, emit a nested `hookSpecificOutput`
([contract](https://code.claude.com/docs/en/hooks)). **A top-level `decision` field is NOT valid
for tool events:**

```bash
deny() {
  jq -n --arg reason "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
  exit 0
}
```

**For `Stop`**, a top-level `decision` IS the contract. **Name the event when you write a deny
helper, and verify the shape against the linked contract rather than against another hook in this
repo.** *(Corrected 2026-08-13 — this document previously specified the `Stop` shape for a
`PreToolUse` hook.)*

**Define it once as a helper.** Every example in this document calls it, and a
hook with several deny paths should not restate the payload shape at each one.

**The decision travels in stdout, never in the exit code** — hence the `exit 0`
inside the helper. A non-zero exit reads to Claude Code as a *broken hook*
rather than as a denial, so a well-meaning `exit 1` on a deny path silently
converts blocking into erroring.

**Never do this** (unsafe string interpolation):
```bash
echo "{\"hookSpecificOutput\": {\"permissionDecision\": \"deny\"}}"  # BAD
```

## Tool Filtering

If your hook should only act on specific tools, check early and exit silently for others.

**EXTRACT-OR-DENY FIRST, FILTER SECOND. The order is the whole point.**

```bash
# 1. Extract or deny — see § Input Handling for the full form.
if ! TOOL=$(printf '%s' "$INPUT" | jq -r '…' 2>/dev/null) || [ -z "$TOOL" ]; then
  deny "Blocked by safety hook: could not determine which tool this event invokes"
fi

# 2. Only now is it safe to filter. A well-formed event for a tool this hook
#    does not police legitimately DOES NOT APPLY — exit 0.
if [ "$TOOL" != "Bash" ]; then
  exit 0
fi
```

Filtering on a value extracted with `// empty` is precisely how an unparseable
event comes to read as *"not my tool"* and is allowed. `TOOL` is `""`, `""` is
not `"Bash"`, the hook exits 0, and nothing anywhere reports a problem. That is
the shape of the defect issue #61 was filed about, and it looks correct in
review because the filter itself is correct — the bug is that it ran on a value
that never should have reached it.

This is the same distinction § Critical Rules draws between *"not my tool"* and
*"I could not tell"*, expressed as an ordering constraint: you cannot decide the
first until you have ruled out the second.

## The headless safety invariant (BINDING)

**A `PreToolUse` hook is the only safety control operating *during* an autonomous run.**

Workflow dispatches pass `--dangerously-skip-permissions`, which bypasses the allow/deny lists in `settings.json` entirely. Of the three layers usually cited — worktree isolation, the hook, PR review — isolation only bounds blast radius and PR review happens after the fact. **The hook is the only one that can stop a command before it runs.**

Three consequences bind anyone touching hooks:

1. **`block-dangerous.sh` is load-bearing, not defence-in-depth.** Weakening a pattern, adding a broad exemption, or making it fail open removes the sole live control from every autonomous run on the machine.
2. **A hook must fail CLOSED.** If it cannot parse its input or evaluate a rule, it denies. A hook that errors into "allow" is worse than no hook, because the safety story still claims it is there.
3. **Any change to which setting sources load MUST prove the hook survives first.** Hook configuration lives in the user-level `settings.json`. Narrowing setting sources — e.g. `--setting-sources project,local` on a dispatch — drops user settings and takes the hook with them. A two-line change becomes a two-line safety regression. See `workflow-scripts.md § The safety-layer invariant`.

*Breaking it looks like:* a hook that exits 0 on an internal error; a dispatch narrowing setting sources without demonstrating a headless run still triggers the hook; a "temporary" pattern relaxation with no expiry.

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

**Read `grep`'s status as THREE outcomes, not two.**

```bash
for pattern in "${REGEX_PATTERNS[@]}"; do
  printf '%s\n' "$CMD" | grep -qEi "$pattern"
  MATCH_STATUS=$?
  if [ "$MATCH_STATUS" -eq 0 ]; then
    deny "Blocked by safety hook: matched destructive pattern ${pattern}"
  elif [ "$MATCH_STATUS" -ne 1 ]; then
    deny "Blocked by safety hook: could not evaluate pattern ${pattern} (grep exited ${MATCH_STATUS})"
  fi
done
```

`0` is a match and `1` is a clean no-match. **Anything else means the rule could
not be EVALUATED** — `2` for a pattern that will not compile, `127` for a `grep`
that is not on `PATH` — and the fail-closed invariant covers that half too.

Testing the pipeline with a bare `if echo … | grep -q …; then` collapses `1` and
`2` into a single falsy branch. A corrupted array entry then silently disables
**every pattern after it** while the hook goes on reporting allow, which is the
same fail-open shape as discarding `jq`'s status one layer up.

`printf '%s\n'` rather than `echo`, for the same reason the input path avoids
it: `echo` treats a lone argument made only of `-neE` characters as its own
options and prints nothing.

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

# Test the FAIL-CLOSED direction (should produce deny JSON)
printf 'not json at all' | ~/.claude/hooks/block-dangerous.sh
echo '{"tool_input": {"command": "ls"}}' | ~/.claude/hooks/block-dangerous.sh
```

Verify **three** directions, not two:
1. Dangerous patterns produce deny JSON
2. Safe commands produce no output
3. **Input the hook cannot understand produces deny JSON** — malformed JSON, a
   payload that is not an object, an absent or non-string `tool_name`

The third is the one that gets skipped, and it is the direction the fail-open
defects have actually been found in. A hook can pass 1 and 2 perfectly while
allowing every event it fails to parse.

**Build test payloads with an encoder, never with string interpolation.** A
`printf` that splices a command containing a tab, a quote or a backslash into a
JSON string produces *invalid* JSON, so every probe denies — and a reader then
takes a uniform deny as proof the hook works, when it proves only that the
harness is broken. Use `jq -nc --arg c "$CMD" '{tool_name:"Bash",tool_input:{command:$c}}'`.

**And pair every such check with two control probes** — one command that MUST
deny and one that MUST allow — read *before* the result under test. On a
control whose failure mode is denying, "everything denied" is otherwise
indistinguishable from success.

Automated coverage belongs in `testing/config-hooks/` — see that directory's
`README.md` for the placement divergence and `test_block_dangerous.py` for the
worked pattern-claim mechanism.

## Critical Rules

- **Hook scripts MUST NOT be interactive** — no prompts, no user input
- **Hook scripts MUST be fast** — they run on every matching tool call
- **Hook scripts MUST fail CLOSED** — if a hook cannot parse its input or evaluate a rule, it **denies**. *(Corrected 2026-08-09. This line previously read "MUST fail safe — prefer allowing the action over blocking", which directly contradicted § The headless safety invariant point 2 in the same document. Both were binding, so an engineer fixing a fail-open defect had to pick. **Point 2 wins**, and the line above it says why: `block-dangerous.sh` is load-bearing rather than defence-in-depth, so failing open removes the sole live control from every autonomous run. "Fail safe" was generic hook advice written before this hook carried that weight.)*
- **Distinguish "not my tool" from "I could not tell"** — a hook that legitimately does not apply to an event exits 0; a hook that could not determine what the event **is** denies. Collapsing the two is how a fail-open defect looks correct in review
- **Hook scripts MUST NOT have side effects beyond their stated purpose** — no logging to random files, no modifying state
- **Hook scripts MUST use `jq` for JSON output** — never raw string interpolation. **The sole exception is a deny path taken *because `jq` is unavailable*:** emit a constant literal that interpolates nothing, and cover it with a test that parses it. *(Added 2026-08-10, closing issue #76.) `jq` missing from `PATH` is one of the conditions that must deny, and it is the one condition under which the payload cannot be built with `jq -n` — `jq` is precisely what is absent. A hook obeying this rule and the fail-closed rule above had no way to satisfy both, and that is the same contradiction shape ruled on at `1082185`: an actor trying to obey both stalls, and a reviewer reading only this line has grounds to reject **correct** code. The rule's own stated reason is escaping — an interpolated variable can break the payload — and a constant has nothing to interpolate, so the exception is a scoping of this rule rather than a hole in it. `config/hooks/block-dangerous.sh` is the worked reference; `test_denies_when_jq_is_unavailable` parses its literal, so a typo fails the suite instead of shipping an unparseable denial.*

## Related Documentation

- `docs/guide/workflows.md` — Why hooks are the safety layer for autonomous mode

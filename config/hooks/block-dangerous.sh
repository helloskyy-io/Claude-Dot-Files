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
# WHAT THIS HOOK CATCHES (in-scope):
#   - Literal destructive commands matching the regex patterns below
#     (rm -rf, git push --force, git reset --hard, dd, mkfs, sudo,
#     fork bombs, DROP TABLE, package purges, systemd disable, SSH
#     tampering, RCE patterns, etc.)
#
# WHAT THIS HOOK DOES NOT CATCH (out-of-scope, known gaps):
#   - **Obfuscated commands** — e.g. `bash -c "$(echo cm0gLXJmIC8= | base64 -d)"`
#     bypasses regex by hiding the dangerous payload in a base64 blob,
#     hex-encoded shell, or other indirection. Not detected.
#   - **Variable indirection** — e.g. `eval "$evil_var"` where the
#     dangerous content was placed in the variable in an earlier turn.
#     The hook sees `eval "$evil_var"`, not the resolved content.
#   - **Aliasing** — e.g. `alias safe='rm -rf /' && safe`. The hook
#     sees `safe`, not `rm -rf /`.
#   - **Here-strings or unusual quoting** — e.g. `r''m -rf /` or
#     `\\rm -rf /`. The regex patterns assume reasonable spacing.
#   - **Subshell smuggling** — e.g. dangerous content inside `$(...)`,
#     `<(...)`, or backticks that the regex doesn't unpack.
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
#
# Full threat-model documentation is tracked in `docs/development/loose_ends.md`
# as a deferred item.
# ---------------------------------------------------------------------------

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
  # Privilege escalation
  '(^|[^a-z])sudo '
  '(^|[^a-z])su +-'
  '(^|[^a-z])doas '

  # File deletion
  'rm +-r?f?r? '
  'rm +-fr '

  # Git destructive operations
  'git push.*--force'
  'git push.*-f( |$)'
  'git reset --hard'
  'git clean -f'
  'git checkout -- \.'

  # Database destructive operations
  'DROP TABLE'
  'DROP DATABASE'
  'DROP SCHEMA'
  'TRUNCATE '
  'DELETE FROM .* WHERE 1'

  # Disk and filesystem
  'mkfs[.]'
  'dd if=.* of=/dev/'
  'fdisk +/dev/'
  'parted +/dev/'
  'wipefs '

  # Direct device writes
  '> /dev/sd'
  '> /dev/nvme'
  '> /dev/hd'

  # System directory writes
  '> /etc/'
  '>> /etc/passwd'
  '>> /etc/shadow'
  '>> /etc/sudoers'
  '> /boot/'
  '> /sys/'
  '> /proc/sys'

  # System control
  '(^|[^a-z])shutdown '
  '(^|[^a-z])reboot( |$)'
  '(^|[^a-z])halt( |$)'
  '(^|[^a-z])poweroff( |$)'
  'systemctl +(stop|disable|mask) '
  'init +0'
  'init +6'

  # Permission disasters
  'chmod -R 777'
  'chmod +777'
  'chown -R .*:(root|nobody) /'

  # Remote code execution patterns
  'curl .*\| *(sh|bash|zsh)'
  'wget .*\| *(sh|bash|zsh)'
  'curl .*-o .*\.sh.*&&.*sh '

  # SSH authorized_keys tampering
  '>> ~/\.ssh/authorized_keys'
  '> ~/\.ssh/authorized_keys'
  '>> /root/\.ssh/authorized_keys'

  # Package manager destructive
  'apt(-get)? +(purge|remove --purge)'
  'dpkg +--purge'
  'pip +uninstall +-y'
  'npm +uninstall +-g'

  # Crontab manipulation
  'crontab +-r'
  '> /etc/crontab'

  # Network/firewall disasters
  'iptables +-F'
  'ufw +--force +reset'
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

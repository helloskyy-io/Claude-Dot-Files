#!/usr/bin/env bash
# PreToolUse hook: blocks destructive bash commands
# Receives JSON on stdin from Claude Code, returns deny decision if dangerous
#
# This is the PRIMARY safety layer for autonomous (headless) mode, where
# --dangerously-skip-permissions bypasses the allow/deny lists in settings.json.
# Hooks still fire regardless, so this hook must catch everything that should
# NEVER run regardless of permission mode.

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

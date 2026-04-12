#!/usr/bin/env bash
# Stop hook: sends a desktop notification when Claude finishes
# Receives JSON on stdin from Claude Code
# Silently skips on headless/VM environments where D-Bus is unavailable

INPUT=$(cat)

STOP_REASON=$(echo "$INPUT" | jq -r '.stop_reason // "finished"')

# Only attempt notification if notify-send exists AND D-Bus session is available
if command -v notify-send &>/dev/null && [ -n "${DBUS_SESSION_BUS_ADDRESS:-}" ]; then
  notify-send "Claude Code" "Task ${STOP_REASON}" --icon=terminal 2>/dev/null
fi

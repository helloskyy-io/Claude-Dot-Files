#!/usr/bin/env bash
# Stop hook: sends a desktop notification when Claude finishes
# Receives JSON on stdin from Claude Code
# Silently skips on headless/VM environments where D-Bus is unavailable
# MUST exit 0 — non-zero exit causes Claude Code to report hook errors

INPUT=$(cat)

STOP_REASON=$(echo "$INPUT" | jq -r '.stop_reason // "finished"' 2>/dev/null || echo "finished")

# Only attempt notification if notify-send exists AND D-Bus session is available
if command -v notify-send &>/dev/null && [ -n "${DBUS_SESSION_BUS_ADDRESS:-}" ]; then
  notify-send "Claude Code" "Task ${STOP_REASON}" --icon=terminal 2>/dev/null || true
fi

exit 0

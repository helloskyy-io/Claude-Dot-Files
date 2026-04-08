#!/usr/bin/env bash
# Stop hook: sends a desktop notification when Claude finishes
# Receives JSON on stdin from Claude Code

INPUT=$(cat)

STOP_REASON=$(echo "$INPUT" | jq -r '.stop_reason // "finished"')

if command -v notify-send &>/dev/null; then
  notify-send "Claude Code" "Task ${STOP_REASON}" --icon=terminal
fi

#!/usr/bin/env bash
# Probe fixture, NOT a fleet hook. Answers one question — did this hook RUN —
# in a way that does not depend on what the model said or which command it
# chose: it writes a marker file named by its first argument, then denies.
# A marker on disk is the observation; the deny keeps the trial's tool call
# from running so the two halves of the fixture cannot disagree.
set -euo pipefail
name="${1:?marker name}"
dir="${PROBE_MARKER_DIR:-/probe}"
mkdir -p "$dir"
date -u +%FT%TZ > "$dir/$name"
printf '%s\n' "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"probe marker hook ${name} fired\"}}"
exit 0

#!/usr/bin/env bash
#
# format-stream.sh — Format Claude Code stream-json output for human display
#
# Reads JSONL from stdin (output of `claude -p --output-format stream-json`)
# and writes formatted, human-readable output to stdout. Used by workflow
# scripts to provide --verbose mode visibility during development and
# burn-testing.
#
# Usage:
#   claude -p "prompt" --output-format stream-json | format-stream.sh
#
# Color support:
#   Colors are enabled if stdout is a TTY. When piped to a file, output is
#   plain text so logs remain searchable and readable.

set -uo pipefail

# ---------------------------------------------------------------------------
# Color setup (TTY only)
# ---------------------------------------------------------------------------
if [ -t 1 ]; then
    C_RESET=$'\033[0m'
    C_DIM=$'\033[2m'
    C_BOLD=$'\033[1m'
    C_BLUE=$'\033[34m'
    C_CYAN=$'\033[36m'
    C_GREEN=$'\033[32m'
    C_YELLOW=$'\033[33m'
    C_MAGENTA=$'\033[35m'
    C_RED=$'\033[31m'
else
    C_RESET=""
    C_DIM=""
    C_BOLD=""
    C_BLUE=""
    C_CYAN=""
    C_GREEN=""
    C_YELLOW=""
    C_MAGENTA=""
    C_RED=""
fi

# ---------------------------------------------------------------------------
# Line-by-line formatter
# ---------------------------------------------------------------------------
# Reads JSONL from stdin, extracts interesting events, formats them.
# Unknown events are silently skipped to keep output clean.

while IFS= read -r line; do
    # Skip empty lines
    [ -z "$line" ] && continue

    # Skip invalid JSON (claude may emit non-JSON stderr mixed in)
    if ! echo "$line" | jq -e . >/dev/null 2>&1; then
        echo "${C_DIM}${line}${C_RESET}"
        continue
    fi

    # Extract the event type
    TYPE=$(echo "$line" | jq -r '.type // empty')

    case "$TYPE" in
        system)
            SUBTYPE=$(echo "$line" | jq -r '.subtype // empty')
            if [ "$SUBTYPE" = "init" ]; then
                MODEL=$(echo "$line" | jq -r '.model // "unknown"')
                SESSION=$(echo "$line" | jq -r '.session_id // empty')
                echo "${C_DIM}[session] started · model=${MODEL}${SESSION:+ · id=${SESSION:0:8}}${C_RESET}"
            fi
            ;;

        assistant)
            # Iterate content blocks
            echo "$line" | jq -c '.message.content[]? // empty' 2>/dev/null | while IFS= read -r block; do
                BTYPE=$(echo "$block" | jq -r '.type // empty')
                case "$BTYPE" in
                    text)
                        TEXT=$(echo "$block" | jq -r '.text // empty')
                        if [ -n "$TEXT" ]; then
                            echo
                            echo "${C_CYAN}${C_BOLD}[claude]${C_RESET} ${TEXT}"
                        fi
                        ;;
                    tool_use)
                        NAME=$(echo "$block" | jq -r '.name // empty')
                        # Extract a short summary of the tool input.
                        # For Bash, take the first line only (heredocs get long)
                        # and truncate to 200 chars. Multi-line commands get a
                        # "(multiline)" marker so you know the rest was cut.
                        SUMMARY=$(echo "$block" | jq -r '
                            .input as $i |
                            def truncate(n): if length > n then .[0:n] + "..." else . end;
                            if .name == "Bash" then
                                ($i.command // "") as $cmd |
                                ($cmd | split("\n")[0]) as $first |
                                if ($cmd | contains("\n"))
                                then ($first | truncate(200)) + " (multiline)"
                                else ($first | truncate(200))
                                end
                            elif .name == "Read" then ($i.file_path // "")
                            elif .name == "Edit" then ($i.file_path // "")
                            elif .name == "Write" then ($i.file_path // "")
                            elif .name == "Glob" then ($i.pattern // "")
                            elif .name == "Grep" then ($i.pattern // "")
                            elif .name == "Agent" then ($i.subagent_type // "general") + ": " + (($i.prompt // "") | truncate(150))
                            else ($i | tostring | truncate(200))
                            end
                        ')
                            echo "${C_BLUE}  → ${NAME}${C_RESET}${C_DIM}: ${SUMMARY}${C_RESET}"
                        ;;
                    thinking)
                        # Show thinking is happening but don't dump the content
                        echo "${C_DIM}  · thinking...${C_RESET}"
                        ;;
                esac
            done
            ;;

        user)
            # User messages are tool results coming back
            TOOL_RESULT=$(echo "$line" | jq -r '.message.content[]? | select(.type == "tool_result") | .content[0].text // empty' 2>/dev/null | head -c 200)
            if [ -n "$TOOL_RESULT" ]; then
                # Show truncated result to confirm tool completed
                echo "${C_DIM}  ← result (${#TOOL_RESULT} chars)${C_RESET}"
            fi
            ;;

        result)
            SUBTYPE=$(echo "$line" | jq -r '.subtype // empty')
            TURNS=$(echo "$line" | jq -r '.num_turns // "?"')
            COST_RAW=$(echo "$line" | jq -r '.total_cost_usd // 0')
            COST=$(awk "BEGIN { printf \"%.4f\", $COST_RAW }")
            DURATION_MS=$(echo "$line" | jq -r '.duration_ms // 0')
            DURATION_S=$(awk "BEGIN { printf \"%.1f\", $DURATION_MS / 1000 }")

            echo
            if [ "$SUBTYPE" = "success" ]; then
                echo "${C_GREEN}${C_BOLD}[done]${C_RESET} turns=${TURNS} · cost=\$${COST} · duration=${DURATION_S}s"
            else
                echo "${C_RED}${C_BOLD}[failed]${C_RESET} turns=${TURNS} · cost=\$${COST} · duration=${DURATION_S}s"
            fi

            # Also print the final text result if present
            RESULT_TEXT=$(echo "$line" | jq -r '.result // empty')
            if [ -n "$RESULT_TEXT" ]; then
                echo
                echo "${C_BOLD}Final output:${C_RESET}"
                echo "$RESULT_TEXT"
            fi
            ;;

        error)
            MSG=$(echo "$line" | jq -r '.message // .error // "unknown error"')
            echo "${C_RED}${C_BOLD}[error]${C_RESET} ${MSG}"
            ;;
    esac
done

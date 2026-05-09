# Terminal Commands & Prompts

When generating shell commands for the user to copy-paste:

- NEVER use heredoc syntax (`$(cat <<'EOF'...)`, `<<'CONTEXT'`, etc.). Heredocs break on copy-paste every time.
- ALWAYS use a single double-quoted string on one line for prompts.
- ALWAYS use absolute paths to scripts (the user may be in a different repo).
- For long or multi-paragraph task/context inputs, write the payload to `/tmp/claude-<name>.md` first, then pass `--task-file /tmp/claude-<name>.md`. This bypasses command-line parsing entirely — quotes, newlines, backticks, and special characters all pass through literally.
- **ALL commands given to the user must be a SINGLE LINE.** No exceptions. No multi-line code blocks, no embedded newlines, no `sudo bash -c '...'` blocks spanning lines. If a command can't fit on one line, write it to `/tmp/claude-<descriptive-name>.sh` and give the user `sudo bash /tmp/claude-<descriptive-name>.sh` as the single-line invocation. This applies to EVERYTHING: workflow dispatches, operational commands, diagnostic commands, git sequences. Terminal whitespace handling corrupts multi-line pastes every time. Chain 2-3 simple related commands with `&&` on one line when script-to-tmp is overkill.

For workflow dispatch invocation shape, ordering rules, and the `--task-file` pattern, see `~/Repos/claude-dot-files/docs/guide/workflows.md`.

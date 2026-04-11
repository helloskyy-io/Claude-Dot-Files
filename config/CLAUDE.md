# Global Instructions

These rules apply to all projects and sessions.

## Communication

- Don't add docstrings, comments, or type annotations to code you didn't change.
- Ask before making changes beyond what was requested.

## Code Style

- Prefer readability over cleverness.
- Use early returns over deeply nested conditionals.
- Don't over-engineer. Solve the current problem, not hypothetical future ones.
- Three similar lines of code is better than a premature abstraction.

## Safety

- Never commit files containing secrets (.env, credentials, tokens, API keys).
- Never hardcode secrets — use environment variables.
- Never force push without explicit approval.
- Never run destructive commands (rm -rf, DROP TABLE, git reset --hard) without confirmation.

## Git

- Use conventional commit format: `type: short description` (e.g., `fix: resolve null check in auth middleware`).
- Don't push unless asked.
- Don't amend commits unless asked — create new commits instead.

## Terminal Commands & Prompts

- When generating shell commands for the user to copy-paste, NEVER use heredoc syntax (`$(cat <<'EOF'...)`, `<<'CONTEXT'`, etc.). Heredocs break on copy-paste every time.
- ALWAYS use a single double-quoted string on one line for workflow script prompts.
- ALWAYS use absolute paths to scripts (the user may be in a different repo).

## Dependencies & Tools

- Check if a tool/package is already in the project before adding a new one.
- Prefer standard library solutions over adding dependencies for trivial tasks.
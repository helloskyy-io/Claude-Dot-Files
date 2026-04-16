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
- Flags FIRST, positionals LAST in workflow invocations: `script.sh --verbose --pr 22 --task-file /tmp/task.md`. Protects the positional payload from being stepped on by line-wrap and keeps options visible at the start.
- For long or multi-paragraph task/context inputs to workflow scripts, use `--task-file <path>` instead of inlining. Write the payload to `/tmp/claude-<name>.md` first, then reference it with `--task-file /tmp/claude-<name>.md`. This bypasses command-line parsing entirely — quotes, newlines, backticks, and special characters all pass through literally.
- For multi-step command sequences: write the sequence to `/tmp/claude-<descriptive-name>.sh` and give the user a SINGLE-LINE invocation `bash /tmp/claude-<descriptive-name>.sh`. NEVER give the user a multi-line code block to copy-paste — terminal whitespace handling corrupts multi-line pastes. Chain 2-3 simple related commands with `&&` on one line when script-to-tmp is overkill.

### Workflow invocation template

When dispatching a workflow (revision.sh, revision-major.sh, build-phase.sh, plan-new.sh, plan-revision.sh), produce **one single-line command** in this exact shape:

```
cd <absolute-path-to-target-repo> && <absolute-path-to-workflow-script> [flags] --task-file /tmp/claude-<name>.md
```

Order: `cd` → `&&` → script absolute path → flags (`--verbose`, `--pr <N>`) → `--task-file` LAST so the file path stays visible/editable. The `cd` matters because workflows operate against the current working directory. Default to including `--verbose` unless the user says otherwise (he wants live streaming). Don't wrap the invocation in a bash launcher script — the single-line command IS the deliverable. Write the long task payload to `/tmp/claude-<name>.md` separately with the Write tool first, then present only the invocation line.

## Personal Tooling

Autonomous workflow scripts live at `~/Repos/claude-dot-files/scripts/workflows/`:
- `revision.sh` — small code fixes
- `revision-major.sh` — significant rework with code-reviewer + refactoring-evaluator + standards-auditor review
- `build-phase.sh` — implement from a plan document
- `plan-new.sh` — define a new project from scratch (architect + planner + security-auditor review)
- `plan-revision.sh` — revise existing planning docs (architect + planner review)
- `review-runs.sh` — CPI analysis of workflow JSONL logs

Each runs in an isolated git worktree and produces a PR. All support `--pr <N>` (update existing PR), `--verbose` (live stream), and `--task-file <path>` (read long payload from file). Always use absolute paths when suggesting invocations. Run `/get-started` at session start for full workflow context, role definitions, and workflow-selection guidance.

## Dependencies & Tools

- Check if a tool/package is already in the project before adding a new one.
- Prefer standard library solutions over adding dependencies for trivial tasks.
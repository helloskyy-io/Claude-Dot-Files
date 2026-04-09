# Slash Command Standards

Conventions for writing custom slash commands in `config/commands/`.

## Purpose

Slash commands are reusable prompt templates that you invoke with `/command-name`. They're saved prompts that you'd otherwise type out every time. The file content IS the prompt — no special syntax, no API — just the text you want Claude to receive.

## File Conventions

### Location
All slash commands live in `config/commands/` and are symlinked to `~/.claude/commands/` via `install.sh`.

### Naming
Use kebab-case. The filename becomes the command name:
- `review.md` → `/review`
- `update-file-structure.md` → `/update-file-structure`
- `cleanup-merged-worktrees.md` → `/cleanup-merged-worktrees`

Choose names that are:
- **Short** — you'll type them dozens of times
- **Descriptive** — clear what they do
- **Verb-oriented** when possible — `/review`, `/update`, `/cleanup`

### No Frontmatter
Unlike agents and skills, slash commands do NOT use YAML frontmatter. The entire file content is the prompt that gets injected.

## Prompt Conventions

### Write Like You'd Type
The content is literally what Claude sees when you invoke the command. Write it the same way you'd type a prompt to Claude in chat.

Example from `commands/review.md`:
```markdown
Use the code-reviewer agent to review code and report findings with structured severity levels (Critical, Warning, Info).

Scope: $ARGUMENTS

If no specific files or scope is provided, review the most recent changes (staged or unstaged) in the current repo.
```

### Parameters via `$ARGUMENTS`
Anything typed after the command name becomes `$ARGUMENTS`. Use this for the variable part of the prompt.

```markdown
Apply this thinking to: $ARGUMENTS
```

Invocation:
```
/best-practices database connection pooling
```

Claude sees:
```
... Apply this thinking to: database connection pooling
```

### Handle Missing Arguments Gracefully
If the command makes sense without arguments, include a fallback:

```markdown
Scope: $ARGUMENTS

If no specific scope is provided, review the most recent changes.
```

If arguments are required, say so:

```markdown
Task: $ARGUMENTS

The task must include a specific description of what to revise.
```

### Invoke Agents by Name
Commands can instruct Claude to use custom agents:

```markdown
Use the code-reviewer agent to review the staged changes in this repo.
Focus on: $ARGUMENTS
```

Or chain multiple agents:

```markdown
Use the architect agent to analyze the current codebase, then use the
planner agent to create an implementation plan for: $ARGUMENTS
```

### Structured Multi-Step Instructions
For complex commands, use numbered steps:

```markdown
Process:

1. Run `git worktree list` to get all active worktrees
2. For each worktree (skip the main working directory):
   - Identify the branch name
   - Check if the PR is merged or closed
3. Clean up merged worktrees
```

## Focus Rules

### One Purpose Per Command
Each command should do one thing well. If your command does three unrelated things, make it three commands.

### Commands vs Agents vs Skills
| Use | When |
|-----|------|
| Command | You want to trigger something explicitly with a shortcut |
| Agent | You want a specialist with restricted tools running in isolation |
| Skill | You want methodology to load automatically based on context |

Don't use a command when a skill would be better. Commands are for explicit triggering.

### Cheap to Invoke
Commands inject prompt text into your current conversation — they're cheap, no new context window, no separate process. This is different from agents (which spawn new sessions) and skills (which load context-aware).

## Safety Conventions

### Show Proposals Before Destructive Actions
If your command modifies files or git state, tell Claude to present the proposed changes first:

```markdown
Present all proposed CLAUDE.md files for review before creating them.
```

### Dry Run Support
For commands with side effects, consider supporting a "dry run" mode via arguments:

```markdown
If $ARGUMENTS contains "dry run", show what you would change but do not modify anything.
```

### Don't Bypass Permissions
Commands run in whatever context invoked them. Don't try to circumvent the user's permission settings from within a command.

## Documentation Within the Command

Include a brief comment at the top if the command's purpose isn't obvious from the prompt itself. But keep it short — commands are meant to be easy to read at a glance.

```markdown
Scan the /docs/standards/ directory for all standard definition files. Then
review each CLAUDE.md file in the project (root and subdirectories) and
update their references to standards.

For each CLAUDE.md:
...
```

## README Integration

When you add a new command, update the **Operation** section of the README to list it. Users should be able to discover available commands from the README without browsing the config directory.

## Examples of Good Commands

### Simple pass-through
```markdown
Apply industry best practices to: $ARGUMENTS
```

### Agent invocation
```markdown
Use the code-reviewer agent to review: $ARGUMENTS
```

### Multi-step workflow
```markdown
Follow these stages:

1. Scan the codebase
2. Identify issues
3. Report findings with severity levels
4. Do not modify files
```

## Critical Rules

- **Commands MUST be plain markdown with no frontmatter**
- **Commands MUST use `$ARGUMENTS` for variable input**
- **Commands MUST be focused on a single purpose**
- **Commands SHOULD be listed in the README Operation section**
- **Commands SHOULD support safe/dry-run modes for destructive operations**

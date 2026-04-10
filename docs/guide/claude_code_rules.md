# Claude Code Rules

## What Are Rules?

Rules are modular instruction files that Claude loads at the start of every conversation. They are functionally identical to `CLAUDE.md` — same effect, same priority — but split into individual `.md` files by topic.

Rules are just `CLAUDE.md` broken into pieces. No special behavior, no priority difference, no conditional logic.

## When to Use Rules vs CLAUDE.md

| Use CLAUDE.md | Use Rules |
|---------------|-----------|
| Instructions are short and manageable | CLAUDE.md has grown long and unwieldy |
| Everything fits in one place | You want to enable/disable specific topics by adding/removing a file |
| Solo developer | Team members need to share individual rules without merging into a monolith |

**Rule of thumb:** If your `CLAUDE.md` is under ~50 lines, there's no reason to split it. When you start scrolling to find things, that's when rules earn their keep.

## Where Rules Live

There are two levels:

### Global Rules (apply to all projects)

```
~/.claude/rules/*.md
```

In this repo, managed at `config/rules/` and symlinked to `~/.claude/rules/`. These load in every project, on every machine.

### Project Rules (apply to one repo)

```
your-project/.claude/rules/*.md
```

These live in a specific project's git repo. They only load when working in that directory. Not managed by this repo.

## Loading Hierarchy

When you're in a project, Claude loads all of these together:

1. `~/.claude/CLAUDE.md` — global instructions
2. `~/.claude/rules/*.md` — global rules
3. `repo-root/CLAUDE.md` — project instructions
4. `repo-root/.claude/rules/*.md` — project rules

Global sets the baseline, project adds specifics. All four layers combine — nothing overrides, they stack.

## File Format

Rules are plain markdown files. No frontmatter required — just write the instructions.

```markdown
# Git Conventions

- Use conventional commit format: `type: short description`
- Don't push unless asked
- Don't amend commits unless asked — create new commits instead
- Never force push without explicit approval
```

File naming convention: use descriptive kebab-case names like `git-conventions.md`, `security.md`, `code-style.md`.

## Examples of When to Split

If your `CLAUDE.md` grows to cover many topics:

```
rules/
├── code-style.md        ← readability, early returns, no over-engineering
├── git-conventions.md   ← commit format, push rules, force push policy
├── security.md          ← no secrets, no hardcoded keys, env vars only
├── dependencies.md      ← check before adding, prefer stdlib
└── testing.md           ← test patterns, coverage expectations
```

Each file is self-contained and can be added, removed, or shared independently.

## Current State

Our global `CLAUDE.md` is ~30 lines and covers everything cleanly. The `config/rules/` directory is synced and ready but intentionally empty. No need to split until the instructions outgrow a single file.

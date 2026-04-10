# Claude Code Headless Mode

## What Is Headless Mode?

Headless mode is Claude Code running without you in the conversation. No interactive terminal, no approval prompts, no back-and-forth. You give it a task, it does the work, and returns the result.

```
Interactive:  You type → Claude responds → you approve → Claude continues → repeat
Headless:     You run a command → Claude works autonomously → result comes back when done
```

## Basic Usage

```bash
claude -p "your task here"
```

The `-p` flag means run the prompt non-interactively and print the output. The flag goes before the prompt.

## Key Flags

| Flag | What It Does |
|------|-------------|
| `-p "prompt"` | Run non-interactively |
| `--max-turns 50` | Safety limit — stop after N tool calls |
| `--output-format stream-json` | Structured output for scripting |
| `--allowedTools` | Restrict which tools Claude can use for this run |
| `-w NAME` / `--worktree NAME` | Run in an isolated git worktree |
| `--headless` | Headless mode (no TTY required, for CI/scripts) |

## How Permissions Work in Headless Mode

In interactive mode, unlisted tools get an approval popup. In headless mode, there's no one to ask — so unlisted tools are denied.

```
Interactive:  allow list → auto-approve
              everything else → ask you

Headless:     allow list → auto-approve
              everything else → denied (no one to ask)
```

Your `settings.json` allow list, deny list, and hooks (like `block-dangerous.sh`) all still apply. The only difference is there's no human to prompt for edge cases.

This is why a well-configured `settings.json` matters more for headless — anything not explicitly allowed is off-limits.

## Slash Commands in Headless Mode

Slash commands work in headless mode:

```bash
claude -p "/update-file-structure"
claude -p "/review src/auth/"
claude -p "/best-practices database connection pooling"
```

## Outcomes

Every headless run has one of two outcomes:

1. **Success** — Task completed, changes made (or PR created). Desktop notification fires via `notify-done.sh`.
2. **Failure** — Claude hit an error, ran out of turns, or couldn't resolve an issue. Read the output, adjust the prompt, try again.

## Using Plans as Work Orders

Claude's built-in plan mode saves ephemeral plans to `~/.claude/plans/` (per-session, not version controlled). But for Workflow 2 (Autonomous), your real plans live in your project's `/docs/development/` directory — persistent, version-controlled, and thoroughly thought through.

These plan documents ARE the prompt. You point headless Claude at them:

```bash
claude -p "Read docs/development/phase-2-api-endpoints.md and implement everything marked as [ ]. Run tests, fix issues, create a PR when complete." --max-turns 100 -w api-endpoints
```

Claude reads your plan, sees the checkboxes, works through them, and delivers a PR.

### Plan Document Structure

Organize plans as a roadmap with detailed phase docs:

```
docs/development/
├── roadmap.md                    ← high-level phases overview
├── phase-1-data-models.md        ← detailed steps, checkboxes
├── phase-2-api-endpoints.md      ← depends on phase 1
├── phase-3-auth.md               ← depends on phase 2
└── phase-4-frontend.md           ← depends on phase 3
```

Work through them in order, one headless run per phase:

```bash
# Phase 1 complete and merged. Start phase 2:
claude -p "Read docs/development/phase-2-api-endpoints.md and implement all unchecked items. Write tests. Create a PR." --max-turns 100 -w api-endpoints

# Phase 2 complete and merged. Start phase 3:
claude -p "Read docs/development/phase-3-auth.md and implement all unchecked items. Write tests. Create a PR." --max-turns 100 -w auth
```

### Why This Works

Your detailed phase docs with checkboxes aren't just documentation — they're machine-readable work orders. Claude reads them the same way a developer would:

- `[ ]` = work to do
- `[x]` = already done, skip
- Step descriptions = implementation instructions
- Dependencies listed = order of operations

The more specific your phase doc, the better the autonomous output. A vague plan gets vague results. A plan with file paths, acceptance criteria, and test expectations gets precise results.

### Invoking Agents from Plans

You can instruct Claude to use your custom agents as part of the autonomous run:

```bash
claude -p "Read docs/development/phase-3-auth.md. Use the planner agent to validate the plan, then implement all unchecked items. When complete, use the code-reviewer agent to review your work and fix any issues found. Run all tests. Create a PR." --max-turns 100 -w auth
```

This chains: plan validation → implementation → self-review → fixes → tests → PR. All autonomous.

## Worktree Isolation

The `-w` / `--worktree` flag creates an isolated git worktree so Claude works on a separate branch without touching your working directory.

```bash
claude -p "implement feature X" -w feature-x
```

This:
1. Creates a worktree at `.claude/worktrees/feature-x/`
2. Creates a new branch (Claude Code auto-prefixes with `worktree-` — so `-w feature-x` creates branch `worktree-feature-x`)
3. Claude works entirely in that isolated copy
4. Your main working directory is untouched
5. Auto-cleans if no changes were made

Use worktrees for any headless run that modifies files. This prevents conflicts with your own in-progress work.

### Worktree Naming Best Practices

Each worktree needs a unique name. If you try to reuse an existing worktree name, Claude Code will fail or branch from stale state.

**Purpose-based names** (readable, good for manual runs):
```bash
claude -p "..." -w add-auth
claude -p "..." -w fix-login-bug
```

**Timestamp-based names** (always unique, good for automation):
```bash
claude -p "..." -w "task-$(date +%Y%m%d-%H%M%S)"
```

**Always branch from fresh main.** Before kicking off an autonomous run, update your main:
```bash
git checkout main
git pull
claude -p "..." -w feature-name
```

### Worktree Cleanup

Worktrees accumulate over time. Clean them up after PRs are merged.

**Manual cleanup:**
```bash
# See what exists
git worktree list
git branch -a

# Remove one worktree
git worktree remove .claude/worktrees/feature-name
git branch -D worktree-feature-name
git push origin --delete worktree-feature-name
```

**Automated cleanup:**

Use the `/cleanup-merged-worktrees` slash command to scan all worktrees, find those whose PRs have been merged or closed, and remove them automatically. It uses `gh pr list` to check PR status and only cleans up worktrees with resolved PRs — open PRs are left alone.

```
/cleanup-merged-worktrees
```

Safe defaults: won't touch the main working directory, won't delete branches with open PRs, asks for confirmation if cleaning up more than 5 worktrees at once.

## Safety

### `--max-turns` Is Your Safety Net

Always set `--max-turns` for headless runs. Without it, a confused Claude could loop indefinitely.

**What is a "turn"?** A turn is one cycle of the Claude agent loop — each time Claude makes a tool call, returns a response, or processes tool results and decides what to do next. Think of it as one "round" of the agent acting on its task.

**Concrete example:** A simple feature that reads 5 files, writes 3 files, runs tests twice, commits, pushes, and creates a PR is roughly 14 turns.

| Task Size | Suggested Limit |
|-----------|----------------|
| Simple (edit + commit) | 10-20 |
| Medium (small feature with tests) | 30-50 |
| Large (full feature implementation) | 50-100 |
| Extra large (full phase implementation) | 100-150 |

Start conservative and increase as you build trust with the output quality. If Claude regularly hits the limit and fails, bump it up. If it never comes close, leave it low.

### Hooks Still Protect You

Your `block-dangerous.sh` PreToolUse hook fires in headless mode. Destructive commands are denied even when you're not watching. The `notify-done.sh` Stop hook fires a desktop notification when the run completes.

### Start Small

Before running a full phase implementation headless:
1. Run a few read-only headless tasks first (`/review`, `/update-file-structure`)
2. Try a small write task in a worktree
3. Review the output carefully
4. Build up to larger autonomous runs as you trust the results

## Quick Reference

```bash
# Read-only tasks (safe, no worktree needed)
claude -p "/review src/auth/"
claude -p "describe the architecture of this project"

# Small changes (use worktree for safety)
claude -p "add input validation to the login endpoint" -w login-validation --max-turns 30

# Full feature (worktree + agents + safety limit)
claude -p "Read docs/development/phase-2-api.md, implement all unchecked items, write tests, create a PR" -w api-phase2 --max-turns 100

# With agent chain
claude -p "Use the planner to validate the plan in docs/development/phase-3.md, implement it, use the code-reviewer to review, fix issues, run tests, create PR" -w phase3 --max-turns 100
```

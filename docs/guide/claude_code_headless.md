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

A headless run looks like it has two outcomes. It has **three**, and the third is the dangerous one:

1. **Success** — task completed, changes made (or PR created). Desktop notification fires via `notify-done.sh`.
2. **Failure** — an error, a turn-cap termination, or an unresolvable issue. Read the output, adjust, retry. Loud and obvious.
3. **Exit 0 having produced nothing** — the run *reports success* and there is no work. This is the one that costs you.

### Why the third outcome exists

**A `claude -p` run ends on any turn that produces text without a tool call.** That rule is invisible interactively, where a text-only turn is just Claude talking to you and the conversation continues. Headless, it is a termination condition.

So a run that dispatches background agents and then says *"waiting for the review agents to return…"* has just ended itself. The turn had text and no tool call. Every stage after that point never executes, the harness reports exit 0, and nothing distinguishes it from a real success except that the PR does not exist.

Observed for real: a research workflow exited 0, in normal time, having produced no paper — because the main loop backgrounded its agents and narrated the wait.

### The two defences

**1. Dispatch agents in the foreground.** Never background-and-wait in a headless run. Foreground agents run concurrently where the harness allows *and* block the turn until results return, so the turn ends on a tool result rather than on prose. Never use a scheduled wake-up to wait for agents either — same failure, longer.

**2. Declare a completion contract.** Give the run an expected pattern its final output must contain, and verify it after the run:

```bash
COMPLETION_PATTERN='https://github\.com/[^ )]+/pull/[0-9]+'
```

Then check the final result against it. A miss means the run stopped early — **fail loud and return non-zero.** The principle: *exit 0 must mean done.* Without this, "the workflow ran fine" and "the workflow did nothing" are the same signal.

The contract pays a second dividend. Once a run provably reports completion plus a stable identifier on its last line, another script can *chain* to it — the exit code plus that line is a complete interface between two independent runs. That is the whole mechanism behind the parent/child workflow pattern; see [workflows.md](workflows.md#why-the-parent-is-pure-bash).

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
├── sprint.md                    ← high-level phases overview
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

The figures below were early estimates and ran low once agent dispatch and review stages entered the picture — each dispatched agent, each verification pass, and each round of applying findings costs turns the naive count misses. Production caps in this repo:

| Workflow class | Cap | Example |
|---|---|---|
| Light single-pass fix | 100 | `build-minor.sh` |
| Reviewed child of a parent | 100–250 | `build-refine-minor.sh` (100) · `build-refine.sh` (250) |
| Disposition (decide-only, no code written) | 120 | `children/review-pr.sh` |
| Phase implementation, planning build | 300 | `build-phase.sh`, `plan-revision.sh` |
| Greenfield planning, whole-repo review | 500–600 | `plan-new.sh`, `review-sprint.sh` |

**A cap is a RUNAWAY GUARD, not a budget.** An unused turn costs nothing — spend is driven by turns actually consumed, so raising a ceiling from 200 to 250 costs zero on every run that never reaches it, and only changes when the guard fires.

This corrects an earlier framing that called caps "reliability controls." That conflated two separate things. A cap **cannot buy reliability** — it can only truncate. Reliability comes from scope discipline: the workflow-fit checks, the routing decision, the size of the task you hand a child. All a low ceiling does to a mis-scoped run is kill it partway and strand the work.

The routing signal survives, but it now reads off **consumption, not termination**: a child that routinely *uses* most of its budget was probably mis-sized and wants the next workflow up. Watch the number it spends, not whether it hit the wall.

**Make a cap kill loud.** Turn-cap termination happens at roughly 0.9% of runs, but when it does, work sits uncommitted in a worktree and nothing says so. Detect it (`"subtype":"error_max_turns"` in the JSONL) and print the worktree path — recovery is minutes once you know where to look, and indefinite when you don't.

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

# Workflows Guide

## Quick Reference — All Scripts

### Helper Scripts (no AI, pure bash)

| Script | Purpose | Location |
|---|---|---|
| `init-project.sh` | Initialize a new project (git, GitHub, scaffolding) | `scripts/helpers/` |

### Workflow Scripts (AI-powered, autonomous)

| Script | Purpose | Agents Used | Max Turns |
|---|---|---|---|
| `revision.sh` | Minor code fixes | None | 30 |
| `revision-major.sh` | Significant code rework | code-reviewer, refactoring-evaluator | 75 |
| `build-phase.sh` | Implement from a plan doc | code-reviewer, refactoring-evaluator | 150 |
| `plan-new.sh` | Define new project from scratch | architect, planner | 225 |
| `plan-revision.sh` | Revise existing planning docs | architect, planner | 75 |
| `review-runs.sh` | CPI log analysis | workflow-analyst | 30 |

### Services (background, systemd)

| Script | Purpose | Location |
|---|---|---|
| `gh-monitor.sh` | Poll GitHub for @claude PR comments | `scripts/services/` |

## Starting a New Project

```bash
# Option 1: Full automation (init-project handles scaffolding, plan-new handles AI planning)
~/Repos/claude-dot-files/scripts/helpers/init-project.sh "my-project" --org helloskyy-io
~/Repos/claude-dot-files/scripts/workflows/plan-new.sh "my-project" "description of the project" --verbose

# Option 2: plan-new.sh auto-detects and calls init-project if needed (future)
```

## Naming Conventions

Workflow families are grouped by prefix:
- **`revision-*`** — fix existing code (minor or major)
- **`build-*`** — implement from plans
- **`plan-*`** — create or revise planning docs
- **`review-*`** — analyze and report

---

## The Dual Workflow Model

## Core Insight

Claude Code already orchestrates agents internally. When you run a regular `claude` command, Claude spawns Explore agents for research, uses the Task tool for delegation, manages context across tool calls, and coordinates its own multi-agent flows behind the scenes.

**Building elaborate custom orchestration on top of this duplicates work Claude already does.** It creates diminishing returns, burns tokens, and adds complexity without proportional value.

Custom orchestration is only valuable when you need something Claude's internal handling can't provide:

- **Named specialists at specific stages** — "use MY planner, MY architect, MY security-auditor" in a specific order with fresh context per stage
- **Walk-away workflows** — autonomous runs that complete while you do other things
- **Explicit context reset between phases** — each stage gets a fresh context window
- **Parallel execution of independent work** — multiple features built simultaneously in isolated worktrees

Everything else, Claude handles natively. This principle drives our entire development model.

## The Two Workflows

We use Claude Code through exactly two workflows. Every task falls into one of them.

### Workflow 1: Interactive Development

**When:** Daily work, small changes, learning, exploration, anything where you want to stay in the loop.

**How:** Start a continuous chat session.

```bash
claude
```

**Characteristics:**
- Direct feedback on each step
- Approval-based (popup on unlisted commands)
- Educational — you see how Claude thinks and works
- Best for: bug fixes, small features, refactoring, exploration, debugging, learning

**Permission model:**
- Conservative allow list in `settings.json`
- Popup approval on anything not allowed
- Deny list for destructive operations

**Use slash commands to accelerate common tasks:**
- `/review` — code review on recent changes
- `/best-practices <topic>` — industry-standard approach primer
- `/update-file-structure` — refresh file_structure.txt
- `/cleanup-merged-worktrees` — clean up old autonomous run artifacts

**This is the default mode.** Probably 90% of development work happens here.

### Workflow 2: Autonomous Development

**When:** Large, well-scoped features or phases where you want to walk away and come back to a PR ready for review. Two specific high-value scenarios:

1. **Initial planning of complex features** — getting multiple expert perspectives upfront (architect, planner, security auditor) saves significant time later
2. **Initial implementation of a planned phase** — executing a pre-thought-out plan while you do other work

**How:** Headless mode with `claude -p` in an isolated worktree, escalating to GitHub PR comments for refinement.

**Permission model:**
- `--dangerously-skip-permissions` flag
- Safety comes from the `block-dangerous.sh` hook (hardened against ~40 destructive patterns)
- Blast radius limited by worktree isolation
- PR review gates merge to main

## Workflow 2 — The Four Stages

Workflow 2 is not a single step. It's a staged flow with clear escalation paths.

### Stage A: Initial Autonomous Run

The primary autonomous path. You kick off a single command and get a PR ready for review.

```bash
./scripts/workflows/build-phase.sh "add user authentication with JWT"
```

Or for a smaller change:

```bash
./scripts/workflows/revision.sh "fix the null check in login()"
```

Workflow scripts handle the worktree creation, claude invocation, logging, and PR creation internally — you just provide the task description.

What happens:
1. Planning pipeline runs (planner → architect → security-auditor → consolidation)
2. Implementation pipeline runs (implement → test → commit → push)
3. PR created via `gh pr create`
4. Stop hook fires desktop notification
5. You come back to a PR ready for review

**Scope:** Entire feature or phase, initial build

### Stage B: PR Review

Standard human review of the PR in GitHub's browser UI.

```
You review the PR
  ↓
Decision:
  ├── Perfect → merge
  ├── Minor issues → leave PR comments (go to Stage C)
  └── Major issues → full re-run needed (go to Stage D)
```

**Scope:** Human judgment on autonomous output

### Stage C: Minor Fix Path (PR Comments)

For small corrections, use GitHub's PR comment system. This is the most elegant iteration mechanism.

```
You leave PR comments: "fix the error handling in login()", "add test for null case"
  ↓
GitHub Actions detects @claude mention
  ↓
Claude reads comments, makes fixes
  ↓
Claude pushes to the same branch
  ↓
PR auto-updates
  ↓
You review again (back to Stage B)
```

**Why this is smart:**
- **GitHub IS the orchestration layer** — no bash state management needed
- **Comments are naturally iterative** — each comment is a correction
- **State persists in the PR** — no `/tmp/workflow/` files
- **Matches existing review workflow** — same as human code review
- **Async-friendly** — works for distributed teams
- **No custom code needed** — GitHub Actions handles the plumbing

**Scope:** Small to medium corrections that fit naturally in review comments

### Stage D: Major Fix Path (Full Re-run)

When corrections are too extensive for PR comments — architectural changes, substantial refactoring, large scope changes — escalate to a full autonomous re-run.

```bash
claude -p "/fix-pr 42 with major changes: the auth flow needs to use sessions instead of JWT" \
  --max-turns 100 \
  --dangerously-skip-permissions \
  -w fix-pr-42
```

What happens:
1. Claude checks out the existing PR branch in a new worktree
2. Applies the requested changes
3. Pushes updates to the same branch
4. PR updates with new commits
5. You review again (back to Stage B)

**Scope:** Substantial rework that would overwhelm PR comments

## Why This Model Works

### 1. It Matches Existing Workflow Patterns

PR review is already how you iterate on code. Extending that natural flow to include Claude means there's nothing new to learn — Claude just becomes another collaborator who responds to PR comments.

### 2. It Uses GitHub as the Orchestration Layer

For iteration, we don't need to build complex bash state management. GitHub PRs remember state, track comments, maintain branch history. Using GitHub as the orchestration layer means **less custom code to maintain**.

### 3. It Scales by Task Complexity

| Task Size | Workflow | Stage |
|-----------|----------|-------|
| One-line fix | Interactive | N/A |
| Bug investigation | Interactive | N/A |
| Small feature | Interactive | N/A |
| Medium feature | Either | Stage A, maybe C |
| Large phase | Autonomous | Stage A → C or D as needed |
| Entire subsystem | Autonomous | Multiple Stage A runs |

The model doesn't force you to pick one mode — it lets the task size drive the choice.

### 4. It Respects Claude's Internal Orchestration

We're not fighting what Claude already does. Custom agents and workflows only appear at specific high-value entry points (initial planning, initial build). Everything in between is Claude's native handling.

### 5. It's Portable

None of this locks us into bash scripts, Paperclip, or a specific SDK. Workflow 2 is mostly GitHub-native with a thin layer of commands on top. If Claude Code's Agent Teams goes GA, we can swap out the bash layer without changing the overall model.

## The Escalation Ladder

Think of the workflows as a ladder. You climb only as high as the task requires.

```
                                    ┌──────────────────────┐
                                    │  Stage D             │
                                    │  Full re-run         │
                                    │  (major changes)     │
                                    └──────────────────────┘
                                              ▲
                                              │ escalate
                                              │
                                    ┌──────────────────────┐
                                    │  Stage C             │
                                    │  PR comments         │
                                    │  (minor fixes)       │
                                    └──────────────────────┘
                                              ▲
                                              │ iterate
                                              │
                                    ┌──────────────────────┐
                                    │  Stage B             │
                                    │  PR review           │
                                    └──────────────────────┘
                                              ▲
                                              │ output
                                              │
                                    ┌──────────────────────┐
                                    │  Stage A             │
                                    │  Initial autonomous  │
                                    │  run                 │
                                    └──────────────────────┘
                                              ▲
                                              │
┌──────────────────────┐                      │
│  Workflow 1          │──────── for ────────►│
│  Interactive         │        everything    │
│  (default for 90%    │        else          │
│  of work)            │                      │
└──────────────────────┘
```

## What We Build

Given this model, the scope of what we actually build is narrower than it might appear.

### Essential Components

**For Workflow 1 (already built):**
- Custom agents (architect, planner, code-reviewer, test-writer, security-auditor)
- Slash commands (review, best-practices, update-file-structure, etc.)
- Safety hooks (block-dangerous.sh, notify-done.sh)

**For Stage A (Initial Autonomous Run):**
- Workflow scripts in `scripts/workflows/`:
  - `revision.sh` — minor corrections (built)
  - `revision-major.sh` — significant rework (planned)
  - `build-phase.sh` — architect & build a phase (planned)
  - `plan-new.sh` — research & planning (built)

**For Stage C (PR Comments):**
- GitHub Actions workflow file (`.github/workflows/claude-pr-handler.yml`)
- Claude GitHub App installed on repos (`claude /install-github-app`)
- Guidelines for how to write PR comments that Claude can act on

**For Stage D (Major Fix):**
- `/fix-pr <PR#>` command that checks out existing PR branch and applies corrections
- Essentially a variant of Stage A with different inputs

### What We Do NOT Build

These were considered and rejected based on research and the dual-flow principle:

- ❌ **Complex iterative refinement loops** — Use PR comments instead (Stage C)
- ❌ **Multi-stage review cycles** — Single pass with human review gate
- ❌ **Parallel multi-feature orchestration** — Wait for Agent Teams GA
- ❌ **Wrapper scripts for every combination** — Only build what's needed
- ❌ **Custom state management** — Let GitHub PRs hold state

## When to Use What

Quick decision guide:

**"I just want to fix this bug"** → Workflow 1 (Interactive)
**"I'm learning a new codebase"** → Workflow 1 (Interactive)
**"Small refactor"** → Workflow 1 (Interactive)
**"I want a second opinion on my design"** → Workflow 1 + `/review` or manually invoke code-reviewer agent
**"I have a well-planned feature, build it"** → Workflow 2, Stage A
**"I'm starting a major new subsystem"** → Workflow 2, Stage A with detailed plan
**"The PR is 90% right, just fix a few things"** → Workflow 2, Stage C (PR comments)
**"The PR needs major rework"** → Workflow 2, Stage D (full re-run)
**"I'm not sure where to start"** → Workflow 1, ask Claude to help you plan

## Principles

Rules we follow across both workflows:

1. **Let Claude do Claude things** — Don't reimplement what the internal orchestration already handles well
2. **Custom orchestration only at high-value entry points** — Planning and initial build, not iteration
3. **GitHub as state** — Use PR/commit history as orchestration state whenever possible
4. **Scope every investigation narrowly** — Unscoped exploration kills token budgets
5. **Verify everything** — PR review is non-negotiable
6. **Stay portable** — Don't lock into any orchestration platform that we can't easily leave
7. **Kill instead of recover** — If autonomous runs fail, restart cleanly instead of trying to rescue them

## Graduation Triggers

This model is right for now. It may not be right forever. Consider graduating when:

- You're running many concurrent autonomous workflows (3+ per day) → Consider Agent Teams when GA
- You need multi-project governance → Consider Anthropic Managed Agents or Paperclip
- You have a team using these workflows → Consider Managed Agents for consistency
- Bash scripts hit real limitations → Consider Claude Agent SDK for production-grade error handling

Until then, the dual workflow model is the right fit.

# Claude Code Orchestration

## What Is Orchestration?

Orchestration is how you stitch together multiple Claude agents, tool calls, and decision points into a coordinated workflow. It's the difference between "run Claude once" and "run a multi-stage pipeline where different agents do different parts of the work."

For Workflow 2 (Autonomous), orchestration is essential — you can't do "plan → implement → test → review → PR" in a single prompt reliably. You need a structure that sequences the stages and manages state between them.

## The Seven Options

There are multiple ways to build orchestrated workflows, ranging from trivial to production-grade. Pick the lightest option that meets your needs.

### 1. Single Detailed Prompt

The simplest approach — write one massive prompt that tells Claude exactly what to do at each stage.

```bash
claude -p "Use the planner to create a plan. Then use the architect to review.
Then implement the plan. Then run tests. Then create a PR." \
  --max-turns 100 --dangerously-skip-permissions -w feature-x
```

**Pros:** No scripting, native, cheapest to set up
**Cons:** Fragile — Claude may skip stages, lose track, or hallucinate progress
**Good for:** Quick tasks, learning, simple workflows where stage ordering is obvious

### 2. Bash Script Chaining

A shell script runs multiple `claude -p` calls, one per stage, with explicit state passing via files.

```bash
#!/bin/bash
# plan-feature.sh

FEATURE=$1
mkdir -p /tmp/workflow

claude -p "Use the planner agent. Task: $FEATURE. Save plan to /tmp/workflow/plan.md" \
  --max-turns 30 --dangerously-skip-permissions

claude -p "Use the architect agent. Read /tmp/workflow/plan.md. Improve it. Save to /tmp/workflow/plan-v2.md" \
  --max-turns 30 --dangerously-skip-permissions

claude -p "Use the security-auditor. Read /tmp/workflow/plan-v2.md. Identify concerns. Save to /tmp/workflow/security.md" \
  --max-turns 30 --dangerously-skip-permissions
```

**Pros:** Explicit control, debuggable, each stage visible, portable forward
**Cons:** You write and maintain bash, no visual feedback, stateful bookkeeping
**Good for:** Production workflows you want deterministic. **← current choice**

### 3. Claude Code Agent Teams

Native Claude Code feature (experimental, GA coming) where one session spawns 3-5 workers in isolated git worktrees.

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

**Pros:** Native, parallel execution, Claude manages coordination
**Cons:** Experimental, less explicit control, harder to reason about failures
**Good for:** Parallel work (multiple independent features), waiting for GA

### 4. Ralph Wiggum Loop (Stop Hook Pattern)

Stop hook intercepts Claude's exit, checks for a completion token, re-injects the prompt if not done.

**Pros:** Simple iteration pattern, works with existing agents
**Cons:** Has known bugs as of 2026 (permission issues, file reading in non-interactive mode), fragile
**Good for:** Simple "iterate until done" with clear exit criteria — but probably skip in favor of explicit loops

### 5. Claude Agent SDK

TypeScript/Python programming framework for building custom agent loops with full control.

```typescript
import { Agent } from '@anthropic-ai/agent-sdk'

const agent = new Agent({
  model: 'claude-opus-4-6',
  tools: [...],
  systemPrompt: '...'
})
```

**Pros:** Full programmatic control, type-safe, testable, production-grade error handling and state management
**Cons:** You're writing code — build system, tests, deployment, team maintenance
**Good for:** Production systems, teams with engineering resources, workflows that outgrow bash

### 6. Anthropic Managed Agents

Fully managed cloud service from Anthropic. Define agents via natural language or YAML, Anthropic handles execution sandbox, credentials, file I/O, code execution, web browsing.

**Pricing:** Token usage + $0.08/session-hour active runtime
**Status:** Public beta as of April 2026

**Pros:** Zero infrastructure, first-party from Anthropic, 10x faster to production vs custom
**Cons:** Vendor dependence, cost model different from Max subscription, less portable
**Good for:** Production deployments where you want managed infrastructure, governance, and compliance

### 7. Third-Party Platforms

Paperclip, Ruflo, oh-my-claudecode, etc. Visual workflow designers and orchestration platforms built on top of Claude Code.

**Pros:** Visual tooling, multi-project management, community-built features
**Cons:** Ecosystem lock-in, config may not be portable back to raw Claude Code, learning curve
**Good for:** Teams that need visual workflow design or governance features

## The Coordinator/Worker Pattern

The dominant community pattern for Claude Code orchestration is **coordinator/worker**:

```
┌─────────────────────────────────────┐
│  Coordinator                        │
│  (bash script, Python, or Claude)   │
│                                     │
│  • Decides what work to dispatch    │
│  • Manages task queue               │
│  • Handles state between workers    │
│  • Enforces WIP limit (3-5 max)     │
│  • Applies kill criteria            │
└─────────────────────────────────────┘
         │
         ├──► Worker 1: claude -p "..." -w task-1
         ├──► Worker 2: claude -p "..." -w task-2
         └──► Worker 3: claude -p "..." -w task-3
              (each in isolated worktree)
```

**Key properties:**
- Each worker is a fresh `claude -p` call with its own context and tools
- Workers operate in isolated git worktrees — no file conflicts
- Coordinator holds state; workers are stateless
- Explicit kill criteria — if a worker is stuck 3+ iterations, restart instead of recover
- WIP limit: maximum 3-5 concurrent workers (more than that causes diminishing returns and token burn)

## Critical Lessons From Production Use

These are the top 5 lessons from engineers running Claude Code orchestration in production as of April 2026. Internalize these before building workflows.

### 1. Context Management Is the Hardest Problem

Claude Code's agent loop eats context fast. Autocompact cycles trigger when context approaches limits and burn 100-200K tokens per cycle. In a naive loop, autocompact can fire 3+ times per turn.

**Mitigations:**
- Keep per-worker scope narrow — one focused task, not "investigate the whole repo"
- Use subagents for exploration (they have their own context window)
- Pass state between workers via small files, not massive prompts
- Monitor token usage; abort if compaction reduces by less than 30%

### 2. Over-Specified CLAUDE.md Backfires

Counter-intuitive but real: a 500-line CLAUDE.md is WORSE than a 50-line CLAUDE.md. Claude ignores critical rules buried in noise.

**Mitigations:**
- Keep CLAUDE.md ruthlessly short (under ~50 lines ideal)
- Move detailed methodology to skills (load on-demand, not always)
- Put project-specific rules in project-level CLAUDE.md, not global
- Regularly prune — if a rule hasn't been invoked in months, remove it

### 3. Infinite Exploration Kills Token Budgets

Unscoped "investigate the codebase" requests read hundreds of files and burn through context. This is one of the fastest ways to exhaust tokens on nothing.

**Mitigations:**
- Scope every investigation narrowly — `/review src/auth/` not `/review`
- Give agents explicit file lists or directory boundaries
- Use Explore subagent for scoped investigation, not open-ended exploration
- Set hard time limits on investigation phases

### 4. Trust-Then-Verify Is Essential

Claude generates plausible but incomplete implementations. Code that looks correct can have subtle bugs, missing edge cases, or hallucinated imports. You cannot ship agent output unverified.

**Mitigations:**
- Always run tests in your workflows
- Use the code-reviewer agent as a gate before PR creation
- Have security-auditor review any auth/data handling changes
- Manual review of PRs is non-negotiable

### 5. Multi-Agent Workflows Aren't for 95% of Tasks

For most tasks, a single `claude -p` call is faster, cheaper, and just as good as orchestrating multiple agents. Multi-agent is only worth it for genuinely complex problems.

**When to use multi-agent:**
- Task has clearly distinct phases (plan → implement → review)
- Different phases need different expertise (architecture vs security)
- Parallel work is possible (3 independent features)
- Complexity exceeds what one agent can hold in context

**When NOT to use multi-agent:**
- Simple bug fix
- One-file change
- Quick refactor
- Anything you could describe in one paragraph

Set a WIP limit of 3-5 agents maximum. More than that causes token burn and coordination overhead.

## Starting Principles for Our Workflows

Based on the lessons above, our workflows follow these rules:

1. **Start simple** — 2-3 stages maximum for the first version of any workflow
2. **Composition is allowed; unbounded iteration is not** — *(revised)*. This principle read "sequential, not nested," and the distinction it was reaching for was the wrong one. A parent script that runs two independent child runs in sequence IS nesting, and it is the most valuable structure in this repo. What has to stay banned is the **loop with no bounded exit**: a stage that re-enters itself until it decides it is happy. One-way composition with a fixed number of children is deterministic and cheap to reason about; a review-fix-review cycle is neither
3. **Explicit exit criteria** — "exit when tests pass," not "repeat 3 times"
4. **State via git, not files** — *(revised)*. The original said `/tmp/workflow/*.md`. In practice the handoff between stages is the **PR, its diff, and its comments**, plus the original task passed to both children. Git is already durable, already reviewable, already the thing the next actor would have to read anyway — and a temp file is state that a session boundary deletes
5. **Scope narrowly** — every stage has a specific, bounded task
6. **Verify everything** — include a review/test stage before anything irreversible
7. **Kill instead of recover** — if a stage fails, restart cleanly instead of fixing mid-flight. Corollary learned the hard way: **make the kill loud**, and make `exit 0` provably mean *done* (see the completion contract in [claude_code_headless.md](claude_code_headless.md#outcomes)). A silent success is worse than a failure
8. **WIP limit** — maximum 3-5 concurrent workers
9. **Separate the actor that produces from the actor that judges** — *(added from production)*. The single highest-value structural change made to this fleet. A run that authors work and then rules on the review findings about it defends the work; splitting those across two runs with no shared context is the only thing that fixed it. See [workflows.md](workflows.md#the-build-split--why-authoring-and-judging-are-separate-runs)

## Where This Repo Landed

Of the seven options above, this repo runs **option 2 — bash script chaining** — and has stayed there deliberately as the workflows grew from single-stage scripts to a parent orchestrating two independent children.

The reason it holds up is worth stating, because it is not "bash is good enough." **Composition never needed a framework.** A parent workflow needs exactly two things from a child: a reliable exit code, and one stable identifier on its last line. Once children declare a completion contract (see [claude_code_headless.md](claude_code_headless.md#outcomes)), bash has everything required to sequence them, branch on failure, and wait on external state between them. `build.sh` polls for CI to settle between its two children in ~40 lines of shell — the kind of thing a framework is usually adopted *for*.

## When to Graduate Beyond Bash

Bash is not right forever. What it does NOT give you, and what would actually justify graduating:

| Limitation | What you need |
|---|---|
| **Durability** — a crash, reboot, or killed terminal loses an in-flight run entirely | Durable execution (Temporal or equivalent) |
| **Resumability** — a failed 3rd stage means re-running stages 1 and 2 | Durable execution |
| **Observability across runs** — "which of the 40 dispatches this week stalled, and where" | Durable execution, or a real orchestrator |
| Error handling becomes genuinely painful | Claude Agent SDK (Python/TypeScript) |
| Structured data processing between stages | Claude Agent SDK |
| Team-scale governance | Anthropic Managed Agents |

**The current position, decided deliberately:** move to Temporal-style durable execution when durability is the binding constraint — **not** to gain composition, which already works. Framing the migration as "we need an orchestrator to compose workflows" would have bought a large dependency for a problem 40 lines of bash had already solved, and would have obscured the actual gap. See `docs/development/skyy-net-seed-handoff.md`.

Until durability binds, stay in bash.

## Quick Reference

**For a simple workflow:** single detailed `claude -p` prompt
**For a real pipeline:** bash script with 2-3 stages
**For parallel work:** multiple `claude -p` calls with unique worktree names
**For work that must be reviewed before you see it:** a parent script over two independent children — one authors, one judges
**When durability binds:** durable execution (Temporal), not because composition needs it
**Never:** unbounded iteration loops, unscoped exploration, workflows without verification stages, or a run whose `exit 0` does not prove it finished

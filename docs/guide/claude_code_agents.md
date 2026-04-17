# Claude Code Agents

## Our Custom Agents — Quick Reference

| Agent | Role | Tools | Model | Preloaded Skills | Trigger |
|-------|------|-------|-------|-----------------|---------|
| architect | System design & trade-off analysis | Read-only | Opus | architecture-decisions, documentation-structure | On-demand |
| planner | Detailed implementation plans | Read-only | Opus | planning-methodology, documentation-structure | On-demand |
| code-reviewer | Code review with structured findings | Read-only | Sonnet | testing-methodology | On-demand |
| refactoring-evaluator | Structural improvement evaluation | Read-only | Sonnet | refactoring-methodology | On-demand |
| test-writer | Generate & run tests, place in standard hierarchy | Full access | Sonnet | testing-methodology, testing-scaffolding, test-suite-architecture | On-demand |
| security-auditor | Vulnerability detection & audit | Read-only | Sonnet | testing-methodology | On-demand |
| standards-auditor | Standards conformance verification (code against standards) | Read-only | Sonnet | standards-enforcement, documentation-structure | On-demand |
| standards-architect | Audits the standards documents themselves — duplication, gaps, drift | Read-only | Sonnet | standards-enforcement, documentation-structure | On-demand |
| workflow-analyst | Workflow log analysis & improvement | Read-only | Sonnet | workflow-analysis | On-demand |

All custom agents are **on-demand only** — Claude's built-in agents handle routine tasks automatically. Invoke these by name when you need depth (e.g., "use the security-auditor to audit src/auth/").

---

## What Are Agents?

Agents are specialist Claude sessions that run independently with restricted tools and a focused system prompt. Think of them as handing a colleague a task sheet and getting a report back. They work in isolation — separate context, separate tools, separate instructions — and return their results to the main conversation.

## Agent Definition Files

Agents live in `~/.claude/agents/` (global) or `.claude/agents/` (project-level). Each agent is a single `.md` file with YAML frontmatter:

```yaml
---
name: code-reviewer
description: Reviews code for bugs, performance issues, and style violations
tools: ["Read", "Grep", "Glob"]
model: sonnet
---

You are a senior code reviewer. Analyze code for:
- Bugs and logic errors
- Performance issues
- Style violations against project standards
- Security concerns

Report findings as a structured list with severity (critical/warning/info).
Do not modify any files. Read-only analysis only.
```

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Identifier used when spawning the agent |
| `description` | Yes | Tells Claude when to use this agent. Include "Use PROACTIVELY" to enable automatic triggering |
| `tools` | Yes | Array of tools the agent can access. This is the primary guardrail |
| `model` | No | Which Claude model to use: `opus`, `sonnet`, or `haiku`. Defaults to parent model if omitted |

### The Prompt Body

Everything below the frontmatter `---` is the agent's system prompt. This defines its personality, focus area, output format, and constraints. Write it like you're briefing a new team member.

## Built-in vs Custom Agents

Claude Code has two categories of agents:

- **Built-in agents** — Ship with Claude Code (e.g., `Explore`, `Plan`, `architect`, `planner`). These are available as `subagent_type` options when Claude spawns subagents internally.
- **Custom agents** — Your `.md` files in `agents/`. Claude reads their frontmatter and uses their definitions to inform how it spawns subagents. The custom agent's `description`, `tools`, `model`, and prompt body shape the subagent's behavior.

In practice, you don't need to think about this distinction. Just ask Claude to use an agent by name and it handles the rest. The key point: your custom agent files are **definitions that guide Claude**, not standalone executables.

## How Agents Get Triggered

There are three ways an agent gets called:

### 1. Automatic (Proactive)

If the agent's `description` includes language like "Use PROACTIVELY when...", Claude will spawn it on its own when it judges the task fits. Example:

```yaml
description: Expert planning specialist. Use PROACTIVELY when users request feature implementation or complex refactoring.
```

With this, saying "let's plan a new auth system" may automatically spin up the agent without you asking for it.

### 2. You Ask For It

Explicitly tell Claude to use a specific agent:

> "Use the architect agent to evaluate this design"
> "Have the code-reviewer look at the changes in src/auth/"

### 3. Claude Decides

Mid-task, Claude may decide that delegating to a specialist agent would produce better results than handling it inline. This is Claude's judgment call based on the agent descriptions available.

## What Happens When an Agent Runs

```
Main conversation (you + Claude)
  |
  |-- spawns agent
  |     - Gets its own fresh context (no memory of your conversation)
  |     - Gets ONLY the tools listed in its definition
  |     - Gets the system prompt from the .md file
  |     - Claude briefs it with a task-specific prompt
  |     - Works independently (reads files, searches code, etc.)
  |     - Returns a single result back to main conversation
  |
  |-- Claude continues with the agent's findings
```

The agent does NOT see your conversation history. Claude must include all relevant context in the spawn prompt. This is why clear, specific agent descriptions matter — they help Claude write better briefs.

## Guardrails: The `tools` Field

The `tools` array is the primary safety mechanism. It physically restricts what an agent can do — not just instructions, but hard enforcement.

### Common Tool Sets

**Read-only (safest):**
```yaml
tools: ["Read", "Grep", "Glob"]
```
Can explore code but cannot modify anything. Good for reviewers, architects, planners.

**Read + write:**
```yaml
tools: ["Read", "Grep", "Glob", "Edit", "Write"]
```
Can modify files but cannot run commands. Good for generators and formatters.

**Full access:**
```yaml
tools: ["Read", "Grep", "Glob", "Edit", "Write", "Bash"]
```
Can do everything including running shell commands. Use sparingly — only for agents that need to run tests, install packages, etc.

### Available Tools

| Tool | What It Does |
|------|-------------|
| `Read` | Read file contents |
| `Grep` | Search file contents with regex |
| `Glob` | Find files by name patterns |
| `Edit` | Modify existing files |
| `Write` | Create or overwrite files |
| `Bash` | Run shell commands |
| `WebFetch` | Fetch a URL |
| `WebSearch` | Search the web |

Note: Agents inherit the same permission rules from `settings.json`. If your settings deny `Bash(rm -rf *)`, agents with Bash access are also blocked.

## The `model` Field

Controls which Claude model the agent uses:

| Model | Strengths | Best For |
|-------|-----------|----------|
| `opus` | Most capable, deepest reasoning | Architecture decisions, complex planning, nuanced review |
| `sonnet` | Fast, capable, cost-effective | Code review, test generation, documentation |
| `haiku` | Fastest, lightest | Simple classification, quick lookups, formatting |

If omitted, the agent uses the same model as the parent conversation.

## What Agents Cannot Do

- **Cannot spawn other agents** — no nesting. For multi-step workflows, chain agents from the main conversation or use slash commands to orchestrate.
- **Cannot see your conversation history** — each spawn starts fresh. Claude must brief the agent with all relevant context.
- **Cannot access tools not in their `tools` list** — hard restriction, not just a suggestion.
- **Cannot persist anything between runs** — every spawn is a clean slate. No memory, no state.
- **Cannot talk to other agents** — agents report back to the main conversation only.

## Agents vs Slash Commands vs Skills

| Feature | Agents | Slash Commands | Skills |
|---------|--------|---------------|--------|
| What they are | Specialist Claude sessions | Prompt templates | Reusable capability definitions |
| Where they live | `agents/*.md` | `commands/*.md` | `skills/*.md` |
| How they run | Separate context, restricted tools | Injected into current conversation | Invoked in current conversation |
| Isolation | Full (own context, own tools) | None (same conversation) | None (same conversation) |
| Best for | Focused tasks, parallel work, safety via tool restriction | Repeatable prompts, team playbooks | Complex multi-step procedures |

## Two-Tier Agent Strategy

Claude Code ships with built-in agents (Explore, Plan, architect, planner, etc.) that handle common tasks automatically. Custom agents in your `agents/` directory are a second tier — heavier, more detailed, and more expensive in tokens.

The strategy: **let built-in agents handle routine work, keep custom agents on standby for when you need depth.**

### Tier 1: Built-In Agents (default, automatic)
- Lean prompts, low token cost
- Claude picks these automatically for everyday tasks
- Good enough for most interactive work

### Tier 2: Custom Agents (on-demand, explicit)
- Detailed process, structured output, specific criteria
- Only fire when you explicitly ask ("use the architect agent") or when an autonomous pipeline invokes them
- Worth the token cost when you need thorough, structured results

### How to Control Triggering

The `description` field controls whether Claude auto-triggers an agent:

**Proactive (auto-triggers):**
```yaml
description: Use PROACTIVELY when users request feature implementation...
```
Claude spawns this agent on its own when it thinks the task fits. Use sparingly — this fires on every matching task and burns tokens.

**On-demand (manual only):**
```yaml
description: Expert planning specialist. Only use when explicitly requested or as part of an autonomous workflow pipeline.
```
Claude only uses this when you ask for it by name, or when a pipeline/command invokes it. Keeps expensive agents off the hot path.

**Rule of thumb:** Start every custom agent as on-demand. Only add "Use PROACTIVELY" if you find yourself manually requesting it on nearly every task.

## Design Patterns

### Read-Only Reviewer
Safest pattern. Agent can only observe, never modify. Use for code review, architecture analysis, security audits.

```yaml
tools: ["Read", "Grep", "Glob"]
model: sonnet
```

### Scoped Writer
Can modify files but not run commands. Good for generating tests, documentation, or boilerplate where you want the output but don't want arbitrary command execution.

```yaml
tools: ["Read", "Grep", "Glob", "Edit", "Write"]
model: sonnet
```

### Full Executor
Can do anything. Reserve for agents that genuinely need to run tests or interact with external systems. Always pair with clear constraints in the prompt body.

```yaml
tools: ["Read", "Grep", "Glob", "Edit", "Write", "Bash"]
model: opus
```

## Tips

- **Start read-only.** You can always grant more tools later. It's harder to clean up after an agent that modified things unexpectedly.
- **Be specific in descriptions.** Vague descriptions lead to agents being triggered at wrong times or getting poor briefs from Claude.
- **Use `sonnet` for most agents.** Reserve `opus` for tasks that genuinely need deep reasoning. This saves tokens and speeds up responses.
- **Test agents on real tasks** before relying on them. The prompt body often needs tuning based on actual output quality.
- **Keep prompts focused.** An agent that tries to do everything will do nothing well. One job per agent.

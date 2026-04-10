# Agent Standards

Conventions for writing custom agent definitions in `config/agents/`.

## Purpose

Agents are specialist Claude sessions that run independently with restricted tools and a focused system prompt. They're our way of defining custom specialists that complement Claude's built-in agents. The two-tier strategy: built-in agents handle routine work automatically, custom agents are on-demand specialists for when depth is needed.

## File Conventions

### Location
All custom agents live in `config/agents/` and are symlinked to `~/.claude/agents/` via `install.sh`.

### Naming
Use kebab-case that describes the role:
- `code-reviewer.md` — reviews code
- `security-auditor.md` — audits security
- `test-writer.md` — writes tests
- `architect.md` — designs systems

Avoid generic names like `helper.md` or `assistant.md`.

## Frontmatter Schema

Every agent file begins with YAML frontmatter defining its properties:

```yaml
---
name: code-reviewer
description: Reviews code for bugs, performance issues, security concerns, and style violations. Use when the user asks for a code review, second opinion, or wants changes evaluated before committing.
tools: ["Read", "Grep", "Glob"]
model: sonnet
---
```

### Required Fields

| Field | Purpose |
|-------|---------|
| `name` | Identifier used when spawning the agent |
| `description` | Tells Claude when to use this agent — CRITICAL for triggering behavior |
| `tools` | Array of tools the agent can access — the primary guardrail |

### Optional Fields

| Field | Purpose |
|-------|---------|
| `model` | Which Claude model: `opus`, `sonnet`, or `haiku`. Defaults to parent model |
| `skills` | List of skill names to preload into the agent's context at startup |

### The `skills:` Field

**Critical for lean agents.** Subagents do NOT automatically load skills from `~/.claude/skills/`. Skills are only preloaded if explicitly listed in the agent's `skills:` field.

Without `skills:`, the agent would need to discover skills via filesystem scanning (Read/Glob), which wastes turns and isn't guaranteed. With `skills:`, the skill content is injected directly into the agent's context at startup.

```yaml
skills:
  - planning-methodology
  - documentation-structure
```

References skills by `name:` (the `name` field in the skill's frontmatter), not by filename.

**Rule:** Every agent that references a methodology skill in its prompt body MUST list that skill in its `skills:` frontmatter. Otherwise the reference is a broken pointer — the agent says "follow the planning-methodology skill" but can't actually read it.

## Description Field

The `description` is the most important field — it controls when Claude activates the agent.

### On-Demand Only (our default)
For specialists that should only fire when explicitly requested:
```yaml
description: Software architecture specialist for system design, scalability, and technical decision-making. Only use when explicitly requested or as part of an autonomous workflow pipeline.
```

### Proactive Triggering (use sparingly)
If the agent should auto-activate in matching contexts, include "PROACTIVELY":
```yaml
description: Code reviewer. Use PROACTIVELY after any significant code changes.
```

**Our rule:** Start every custom agent as on-demand only. Proactive triggering burns tokens because the agent spawns on every matching task. Only add proactive if you find yourself manually requesting it on nearly every task.

## Tools Field

The `tools` array is the primary safety mechanism. It physically restricts what an agent can do.

### Common Tool Sets

**Read-only (safest, default choice):**
```yaml
tools: ["Read", "Grep", "Glob"]
```
Good for: reviewers, architects, planners, auditors, analyzers.

**Read + write (scoped):**
```yaml
tools: ["Read", "Grep", "Glob", "Edit", "Write"]
```
Good for: generators, formatters, documentation writers.

**Full access:**
```yaml
tools: ["Read", "Grep", "Glob", "Edit", "Write", "Bash"]
```
Good for: agents that need to run tests, install packages, execute commands. Use sparingly.

### Rules
- Start with the most restrictive set that works
- A read-only reviewer is safer than a full-access reviewer — even if you trust the prompt
- Tool restrictions are hard limits, not suggestions — they can't be bypassed from within the prompt
- Document why you chose the tool set in the agent's prompt body when not obvious

## Model Field

Choose the model based on the work's complexity:

| Model | Use When |
|-------|----------|
| `opus` | Deep reasoning, complex architecture decisions, nuanced review, planning |
| `sonnet` | Structured tasks, code review, test generation, most specialist work |
| `haiku` | Simple classification, quick lookups, formatting, trivial tasks |

**Default to `sonnet`** for most custom agents. It's the right balance of capability and cost. Reserve `opus` for agents where the extra reasoning genuinely matters.

## Prompt Body Conventions

Everything below the frontmatter `---` is the agent's system prompt.

### Structure
Good agent prompts have:
1. **Role statement** — who the agent is
2. **Process/methodology** — how they approach work
3. **Criteria or checklist** — what to look for
4. **Output format** — how to report results
5. **Rules/constraints** — what NOT to do

### Role Statement
Start with a clear role declaration:
```markdown
You are a senior code reviewer. Your job is to analyze code and report findings — never modify files.
```

### Output Format
Define the expected output format explicitly. This makes agent output consistent and parseable.

```markdown
## Output Format

```
## Review: [file or feature name]

### Critical
- **[file:line]** — description of the issue and why it matters

### Warning
- **[file:line]** — description of the issue and suggested fix

### Info
- **[file:line]** — observation and suggestion

### Summary
[1-2 sentence overall assessment]
```
```

### Rules Section
Include explicit rules at the end:
```markdown
## Rules

- Be specific: cite file paths and line numbers
- Explain why something is a problem, not just that it is
- If the code looks good, say so — don't invent issues
- Do not modify any files — read-only analysis only
```

## Keep Agents Lean

**Don't put methodology in agent prompts — put it in skills.**

An agent is a role. A skill is a methodology. They should stack:
- Lean agent (~20-30 lines) defines the role
- Rich skill (however long needed) defines the methodology
- Claude loads the skill when the agent is doing matching work

### Bad (200+ lines, methodology embedded):
```yaml
---
name: planner
---
You are a planner.

## Detailed Planning Process
[50 lines]

## Worked Example
[80 lines]

## Red Flags
[20 lines]
```

### Good (20 lines, methodology in skill):
```yaml
---
name: planner
---
You are an expert planner. Analyze requirements, break down features into
phased implementation steps, identify dependencies and risks, and produce
actionable plans.

Report plans in structured markdown with phases, steps, file paths,
dependencies, risks, and success criteria.
```

The methodology lives in `skills/planning-methodology.md` and loads automatically when planning work is happening.

## Agent Directory Documentation

When you add a new agent, update the quick reference table in `docs/guide/claude_code_agents.md`:

```markdown
| Agent | Role | Tools | Model | Trigger |
|-------|------|-------|-------|---------|
| code-reviewer | Code review with structured findings | Read-only | Sonnet | On-demand |
```

## Critical Rules

- **Start read-only.** You can always grant more tools later.
- **Keep prompts focused on role, not methodology.** Methodology goes in skills.
- **Be specific in descriptions.** Vague descriptions cause wrong triggering.
- **Default to `sonnet` model** unless opus reasoning is genuinely needed.
- **On-demand by default.** Only add "PROACTIVELY" if you really want auto-triggering.
- **Update the quick reference table** when adding new agents.
- **Agents CANNOT spawn other agents** — no nesting. Chain from main conversation.
- **Agents CANNOT see conversation history** — each spawn starts fresh.

## Related Documentation

- `docs/guide/claude_code_agents.md` — Full agent architecture guide
- `docs/standards/skills.md` — Skill standards (for where methodology lives)

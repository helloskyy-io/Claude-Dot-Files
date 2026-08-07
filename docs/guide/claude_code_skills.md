# Claude Code Skills

## Our Skills

**The current roster lives in [`operations.md § Skills`](operations.md#skills)** — 17 methodology documents with what each covers. Not duplicated here; this document explains what skills *are* and how to write one.

Skills are **context-aware and load on demand** — Claude reads the descriptions and loads only what matches the work in front of it. No manual invocation needed, though several are also exposed as slash commands (`/decide` → `decision-methodology`, `/troubleshoot` → `troubleshooting-methodology`) for when you want to force the lens.

---

## What Are Skills?

Skills are context-aware instruction sets that Claude loads on-demand when the work matches the skill's description. Think of them as **procedure manuals that only open when relevant** — they don't burn tokens sitting in every conversation, but they're there when Claude needs them.

## Where Skills Fit

| Layer | When It Loads | Best For |
|-------|--------------|----------|
| Rules / CLAUDE.md | Always, every conversation | Universal standards (code style, safety, git conventions) |
| Skills | On-demand, when context matches | Detailed methodology for specific types of work |
| Commands | When you type `/command-name` | Repeatable prompts you trigger explicitly |
| Agents | When spawned (by you or Claude) | Focused specialist tasks in isolation |

**The key insight:** Rules define what Claude should *always* know. Skills define what Claude should know *when relevant*. This keeps your context window lean for quick tasks but rich for complex ones.

## Skills + Agents: The Architecture

Skills and agents are complementary — they separate *who* from *how*:

- **Agents** define the *role* — who it is, what tools it has, output format (lean, ~20-30 lines)
- **Skills** define the *methodology* — how to do the work, standards, process details (rich, as long as needed)

```
Agent (lean):     "You are a planner. Create implementation plans."
                       ↓
                  Claude is now doing planning work
                       ↓
Skill activates:  "Here's the detailed planning methodology..."
Skill activates:  "Here's how to do requirements gathering..."
Skill activates:  "Here's how to estimate risk..."
```

The agent doesn't need to reference skills explicitly. Claude matches them based on what it's doing. This means:

- Agents stay cheap to spawn (small prompt, low tokens)
- Methodology lives in one place (skills), not duplicated across agents
- Multiple agents can benefit from the same skill
- You can update a methodology without touching any agent definitions

## Skill Definition Files

Skills live in `~/.claude/skills/` (global) or `.claude/skills/` (project-level). Each skill is a single `.md` file.

In this repo, managed at `config/skills/` and symlinked to `~/.claude/skills/`.

### Format

```yaml
---
name: planning-methodology
description: Detailed methodology for planning features and breaking down work. Use when creating implementation plans, designing features, or scoping work.
---

## Requirements Gathering

Before planning any implementation:

1. Identify the problem being solved (not the solution)
2. List functional requirements (what it must do)
3. List non-functional requirements (performance, security, scalability)
4. Identify constraints (timeline, tech stack, dependencies)
5. Define success criteria (how do we know it's done?)

## Task Breakdown

...
```

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Identifier for the skill |
| `description` | Yes | Tells Claude when to activate this skill. Be specific about the context — this is what triggers loading |

### The Description Field

The `description` is the most important part. It determines when Claude loads the skill. Be specific about the type of work that should trigger it:

**Good — specific context:**
```yaml
description: Methodology for planning features and breaking down implementation work. Use when creating implementation plans, designing features, or scoping work.
```

**Good — specific trigger:**
```yaml
description: PR creation standards and checklist. Use when creating pull requests or preparing code for review.
```

**Bad — too vague:**
```yaml
description: General coding guidelines.
```
This would match almost everything and defeat the purpose of on-demand loading.

### The Prompt Body

Everything below the frontmatter is the skill content. This is where you put the detailed methodology, standards, checklists, and processes. There's no length limit — skills can be as detailed as needed since they only load when relevant.

Write skills like you're documenting your process for a senior developer joining your team. Include:

- Step-by-step processes
- Decision criteria
- Examples of good and bad approaches
- Checklists
- Standards and conventions

## How Skills Get Triggered

Three ways:

### 1. Automatic (context matching)

Claude reads the `description` of all available skills and loads ones that match the current work. If you're doing planning, planning skills activate. If you're writing tests, testing skills activate.

This is the primary mechanism — you don't need to do anything.

### 2. You invoke it

You can call a skill directly like a slash command:

```
/skill-name
```

### 3. Referenced by other instructions

An agent prompt or command can mention a methodology, and if a skill matches that context, Claude loads it.

## Building a Skills Library

### Approach: Write from Experience

Don't try to write all your skills upfront. The best skills come from real work:

1. Work on real tasks with Claude
2. Notice when you're correcting Claude or wishing it did something differently
3. Capture *that* as a skill
4. Refine over time as you use it

### Candidate Topics

The list below was written before any skill existed. Most of the Planning & Design and Implementation entries are now built — see [`operations.md § Skills`](operations.md#skills) for what actually exists. What remains unbuilt is instructive: the **Operations** group (incident response, monitoring, performance review) is still open, because none of it has been explained twice yet. That is the signal to watch, not the list.

Common areas where detailed methodology adds value:

**Planning & Design:**
- Feature planning methodology
- Requirements gathering process
- Architecture decision-making (standards-doc format, trade-off analysis)
- Task breakdown and estimation

**Implementation:**
- Testing philosophy (what to test, TDD approach, coverage expectations)
- Code review standards (severity levels, what to look for)
- Refactoring methodology
- API design standards

**Delivery:**
- PR creation standards and checklist
- Git workflow (branching strategy, commit conventions)
- Deployment procedures
- Documentation standards

**Operations:**
- Security review process
- Performance review methodology
- Incident response procedures
- Monitoring and alerting standards

### Organization

Name files by topic using kebab-case:

```
skills/
├── planning-methodology.md
├── architecture-standards.md
├── testing-philosophy.md
├── pr-standards.md
├── code-review-standards.md
├── security-review-process.md
└── api-design-standards.md
```

## Skills vs Everything Else — Decision Guide

**"Claude should always know this"** → Put it in `CLAUDE.md` or `rules/`
- Code style preferences
- Safety rules (no secrets, no force push)
- Git commit format

**"Claude should know this when doing X type of work"** → Make it a skill
- How to plan features
- How to review code
- How to write tests
- How to create PRs

**"I want to trigger this explicitly"** → Make it a command
- `/review` — run the code reviewer
- `/best-practices` — prime Claude's mindset

**"This needs to run in isolation with restricted tools"** → Make it an agent
- Code reviewer (read-only)
- Security auditor (read-only)
- Test writer (needs write + bash)

## Current State

17 skills, built incrementally as methodology got defined through real usage — which was the plan, and it held. The pattern that produced them: a methodology becomes a skill once it has been explained twice. The first time is a conversation; the second time is evidence that it is reusable and that re-deriving it is waste.

Two later additions show the shape maturing. `decision-methodology` and `troubleshooting-methodology` were both extracted from repeated live sessions where the *approach* mattered more than the answer — reframe the question before answering it; bisect and form hypotheses rather than guess-and-check. Both were paired with a slash command so the lens can be forced rather than waited for.

## Example: Trimming an Agent with Skills

Before (everything in the agent — 200+ lines):

```yaml
---
name: planner
description: Expert planning specialist.
tools: ["Read", "Grep", "Glob"]
model: opus
---

You are an expert planner.

## Planning Process
[50 lines of methodology]

## Worked Example: Stripe Subscriptions
[80 lines of example]

## Sizing and Phasing
[30 lines of guidance]

## Red Flags
[20 lines of anti-patterns]
```

After (agent is lean, skills hold the depth):

```yaml
---
name: planner
description: Expert planning specialist. Only use when explicitly requested.
tools: ["Read", "Grep", "Glob"]
model: opus
---

You are an expert planner. Analyze requirements, break down features
into phased implementation steps, identify dependencies and risks,
and produce actionable plans.

Report plans in structured markdown with phases, steps, file paths,
dependencies, risks, and success criteria.
```

```yaml
# skills/planning-methodology.md
---
name: planning-methodology
description: Detailed methodology for planning features. Use when creating implementation plans.
---

## Planning Process
[50 lines of methodology]

## Worked Example: Stripe Subscriptions
[80 lines of example]

## Sizing and Phasing
[30 lines of guidance]

## Red Flags
[20 lines of anti-patterns]
```

Same depth, but now:
- The agent is cheap to spawn every time
- The methodology loads only when planning is happening
- Other agents doing planning work also benefit from the same skill
- You can update the methodology in one place

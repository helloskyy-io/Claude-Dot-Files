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

**Default to `sonnet`.** Reserve `opus` for agents where the extra reasoning genuinely matters.

**Bigger is not automatically better, and the tier is an evidence question.** Tier by what the job actually needs: an agent that fetches citations and compares them to claims is doing mechanical verification, and a cheaper tier does it as well for a fraction of the cost — while the agent that *authors* the synthesis is not. A whole tier was removed from this fleet on economics alone after it accounted for roughly 57% of a week's spend with no matching quality delta.

**Never omit `model`.** An unpinned agent inherits whatever the dispatching session happened to be running, which makes a behaviour change impossible to attribute afterwards. Model identity is an explicit input, never derived — the same rule workflows enforce at dispatch.

### The tier canon lives in `config.yaml`, and agents must conform (BINDING)

Agents pin their model in **their own frontmatter**, because an agent file is static markdown and cannot read `config.yaml`. Workflows resolve theirs at dispatch **from** `config.yaml`. Two mechanisms, and they can drift.

The one-glance record of every agent's approved tier is therefore a comment block in `config.yaml`'s `models:` section, and **agent frontmatter MUST match it**. Checked at CPI time. Where they disagree, `config.yaml` is the statement of intent and the agent file is the bug.

*Breaking it looks like:* an agent with no `model:`; a tier changed in frontmatter without updating the canon; a canon entry for an agent that no longer exists.

### Opus-Approved Roles

**The test:** Does this agent produce *deliberative artifacts* — designs, plans, or decisions that downstream work depends on — or does it perform *structured inspection* (review, audit, test generation, formatting)? Deliberative artifacts justify `opus`; structured inspection stays on `sonnet`.

**Currently approved for `opus`** (both pass the test):

- **`architect`** — system design, scalability analysis, technology selection, architectural trade-offs
- **`planner`** — feature decomposition, phased implementation plans, risk and dependency analysis

The list above is a snapshot, not a closed allowlist. A future role that passes the deliberative-artifacts test (e.g., a threat-modeler or a migration-strategist) can adopt `opus` without requiring an amendment to this document — update the snapshot when the role lands.

## Web Access Is a Capability Decision (BINDING)

Most agents are `Read` / `Grep` / `Glob` only. **Add `WebSearch` / `WebFetch` when the agent's ground truth lives OUTSIDE the repo — and only then.**

Verifying a design against current industry practice, checking a CVE, gathering sources: all ground truth that no amount of reading the repo will produce. For those, web access is not an enhancement, it is the job.

**There is a real reason to withhold it, and it is not cost.** Giving web access to a conformance checker is actively wrong: its ground truth is `docs/standards/`, and letting it consult the internet invites it to grade your code against someone else's conventions. The agent will not tell you it did this — the findings will simply be subtly about a different codebase.

**The test:** if the agent's job is *"does this match what WE decided"*, it must not have web access. If the job is *"is what we decided still true"*, it must.

*Breaking it looks like:* a standards or conformance agent with `WebFetch`; a research or verification agent without it.

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

## Dispatching Agents (BINDING)

### Parallel narrow lenses, then sequential integration

Multiple `Agent` calls in a **single** assistant message run concurrently; splitting them across messages forces sequential execution and multiplies wall time on the review stage.

So a review stage dispatches its **narrow-lens** agents in one message, then dispatches the **integration lens** afterwards, in its own message, with the narrow findings in hand. The ordering is not stylistic: an integrator's value is meta-pattern detection across the others' findings — *"these together suggest the work was rushed"* — which it cannot do without seeing them first.

*Breaking it looks like:* narrow-lens agents dispatched one per message; an integration agent dispatched alongside the agents it is meant to integrate.

### Foreground dispatch is MANDATORY in headless runs

**A `claude -p` run terminates on any turn that produces text without a tool call.** Invisible interactively, fatal here.

So a run that background-dispatches agents and then says *"waiting for results…"* **has just ended itself** — the turn had text and no tool call. Every later stage never executes, the harness reports exit 0, and nothing distinguishes it from success except that the work does not exist.

Dispatch agents in the **foreground**. Foreground agents still run concurrently where the harness allows, *and* the turn blocks until results return, so it ends on a tool result rather than on prose. Never background-and-wait, and never use a scheduled wake-up to wait for agents — same failure, longer.

*Breaking it looks like:* `run_in_background: true` in a headless workflow prompt; any "waiting for the agents" narration between dispatch and results.

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

**This standard does not carry the roster, and neither does any other document except one.** The authoritative inventory — every agent with its lens, tier and web access — lives in `docs/guide/operations.md § Agents`. A standard states rules; a roster is completion-state, and a second copy drifts silently (see `documentation/documentation_standard.md`).

When you add or retire an agent, update **three** places, and all three are required:

1. `docs/guide/operations.md` — the roster.
2. The tier canon comment in `config.yaml`'s `models:` section — so the agent-side and workflow-side model mechanisms stay reconcilable.
3. `docs/file_structure.txt` — if the file set changed.

*Breaking it looks like:* a new agent that appears in no roster; a roster entry whose tier disagrees with the agent's frontmatter; an agent table re-listed in a second document.

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

- `docs/guide/operations.md § Agents` — **the roster** (lens, tier, web access per agent)
- `docs/guide/claude_code_agents.md` — platform background: what agents are, frontmatter, tool guardrails, dispatch patterns
- `docs/standards/skills.md` — Skill standards (for where methodology lives)

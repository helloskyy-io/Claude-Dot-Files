# Skill Standards

Conventions for writing skill definitions in `config/skills/`.

## Purpose

Skills are context-aware instruction sets that Claude loads on-demand when the work matches the skill's description. They hold the detailed methodology, standards, and processes that agents and commands reference without having to include inline. Think of them as procedure manuals that only open when relevant.

## The Core Principle

**Skills separate role from methodology.**

- **Agents** define the role — who it is, what tools, output format
- **Skills** define the methodology — how to do the work, standards, process
- Claude loads the skill when the agent is doing matching work

This keeps agent prompts lean (cheap to spawn) while making rich methodology available exactly when needed.

## File Conventions

### Location
All skills live in `config/skills/` and are symlinked to `~/.claude/skills/` via `install.sh`.

### Naming
Use kebab-case that describes the methodology's domain:
- `planning-methodology.md` — how to plan features
- `testing-methodology.md` — how to approach testing
- `architecture-standards.md` — architectural principles
- `pr-standards.md` — PR creation standards
- `security-review-process.md` — security audit methodology

Avoid:
- Generic names (`general.md`, `guidelines.md`)
- Overly specific names (`planning-for-auth-features.md`)

## Frontmatter Schema

```yaml
---
name: planning-methodology
description: Detailed methodology for planning features and breaking down implementation work. Use when creating implementation plans, designing features, or scoping work.
---
```

### Required Fields

| Field | Purpose |
|-------|---------|
| `name` | Identifier for the skill |
| `description` | Tells Claude when to activate the skill — CRITICAL for triggering |

### No Tools Field
Unlike agents, skills don't define tools. They load into whatever session is currently running and inherit its tool access.

### No Model Field
Skills run in the current conversation — they don't spawn new sessions, so there's no model to choose.

## Description Field (Most Important)

The `description` controls when Claude loads the skill. Be **specific** about the context.

### Good — Specific Context
```yaml
description: Methodology for planning features and breaking down implementation work. Use when creating implementation plans, designing features, or scoping work.
```

Claude will load this when doing planning work — not during bug fixes, not during code review, not during deployment.

### Good — Specific Trigger
```yaml
description: PR creation standards and checklist. Use when creating pull requests or preparing code for review.
```

### Bad — Too Vague
```yaml
description: General coding guidelines.
```

This would match almost everything and defeat the purpose of on-demand loading.

### Bad — Too Narrow
```yaml
description: How to plan JWT-based authentication features for Node.js apps.
```

This is so specific it will almost never match. Be domain-specific, not feature-specific.

## Prompt Body Conventions

Everything below the frontmatter is the skill content. There's no length limit — skills can be as detailed as needed since they only load when relevant.

### Write Like Onboarding Documentation
Write skills like you're documenting your process for a senior developer joining your team. Be clear, concrete, and specific.

### Include
- Step-by-step processes
- Decision criteria
- Examples of good and bad approaches
- Checklists
- Standards and conventions
- The "why" behind the "what"

### Structure
A well-structured skill typically has:

1. **Principles** — the WHY
2. **Process** — the WHAT and HOW
3. **Criteria** — how to judge quality
4. **Examples** — good and bad
5. **Red flags** — what to watch out for
6. **Checklist** — quick reference

### Example Structure
```markdown
---
name: testing-methodology
description: How to approach writing and running tests. Use when writing tests, running test suites, or evaluating test coverage.
---

## Testing Principles

Testing is not about coverage percentage. It's about building confidence that
the code does what it should and will keep doing it as the system evolves.

## Process for Writing Tests

1. Understand the behavior being tested (not the implementation)
2. Identify the project's test framework and conventions
3. Write tests that would fail if the behavior broke
4. ...

## What to Test

### Priority Order
1. **Happy path** — does the core functionality work?
2. **Edge cases** — empty inputs, null values, boundary conditions
3. **Error cases** — invalid inputs, missing dependencies
4. **Integration points** — does it interact correctly with dependencies?

### What NOT to Test
- Implementation details
- Third-party library behavior
- Trivial getters/setters

## Red Flags
- Tests that duplicate implementation
- Over-mocking
- Tests that are skipped "temporarily"
- ...
```

## Skills vs Project Standards

Skills live globally in this dotfiles repo. Per-project standards live in each project's own repo.

**Global skill** — the methodology, principles, and patterns (same across projects):
```markdown
# skills/testing-methodology.md
How to approach testing. Identify the project's test framework. Follow its
conventions. Test behavior, not implementation...
```

**Project standards** — the specific setup (varies per project):
```markdown
# <project>/docs/standards/testing.md
This project uses pytest. Tests live in /tests/unit/, /tests/integration/,
/tests/e2e/. Minimum coverage is 80%. Use factory fixtures for test data...
```

The global skill says HOW to think. The project standards say WHAT this project does specifically.

## Building Skills From Experience

**Don't write all your skills upfront.** Start with an empty `skills/` directory and build skills as you discover gaps:

1. Work on real tasks with Claude
2. Notice when you're correcting Claude or wishing it did something differently
3. Capture that correction as a skill
4. Refine over time

The best skills come from real workflow experience, not speculation about what might be useful.

## Common Skill Topics

Areas where detailed methodology usually earns its keep:

**Planning & Design:**
- `planning-methodology.md`
- `architecture-standards.md`
- `requirements-gathering.md`

**Implementation:**
- `testing-methodology.md`
- `code-review-standards.md`
- `refactoring-methodology.md`

**Delivery:**
- `pr-standards.md`
- `git-workflow.md`
- `deployment-procedures.md`

**Review:**
- `security-review-process.md`
- `performance-review.md`

## Keep Skills Focused

### One Topic Per Skill
A skill that covers "planning and architecture and testing" is too broad. Split it:
- `planning-methodology.md`
- `architecture-standards.md`
- `testing-methodology.md`

This way Claude loads only what's relevant, not a giant monolith.

### Don't Put Rules in Skills
Rules go in `CLAUDE.md` or `rules/` — those are always loaded. Skills are for detailed methodology that loads on-demand.

**Rule** (always applies):
> Never commit secrets

**Skill content** (loads when reviewing code):
> When reviewing for security, check for hardcoded credentials, API keys in source,
> environment variables that leak into logs, and...

## Critical Rules

- **Description is everything** — it determines when the skill loads
- **Keep skills focused on one topic**
- **Write skills from experience, not speculation**
- **Separate role (agents) from methodology (skills)**
- **Global skills describe HOW to think; project standards describe WHAT to do**
- **Don't put always-applicable rules in skills** — those go in CLAUDE.md/rules

## Related Documentation

- `docs/guide/claude_code_skills.md` — Full skills architecture guide
- `docs/standards/agents.md` — Agent standards (for where roles live)

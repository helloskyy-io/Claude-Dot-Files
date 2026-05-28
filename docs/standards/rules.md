# Rule Standards

Conventions for writing rule files in `config/rules/`.

## Purpose

Rules are modular instruction files that Claude loads at the start of every conversation. They are functionally identical to `CLAUDE.md` — same effect, same priority — but split into individual `.md` files by topic so they can be added, removed, or shared independently.

## When to Use Rules

Write a rule instead of a skill when the instruction is **always applicable** — it governs all work in every conversation, not just specific contexts.

| Write a Rule | Write a Skill |
|--------------|---------------|
| Applies to every conversation | Applies only when the work matches |
| "Never commit secrets" | "When reviewing for security, check for…" |
| Short, declarative constraint | Multi-step methodology or process |
| Needs to load automatically | Load on-demand based on context |

If it would go in `CLAUDE.md`, it's rule material. If it would go in onboarding documentation for a specific methodology, it's skill material.

### Rules vs. `CLAUDE.md`

`config/rules/*.md` is the PRIMARY vehicle for global instructions in this repo. `config/CLAUDE.md` is a stub redirect that points to `/rules` and is locked from edits. The split happened because `CLAUDE.md` outgrew a single file — every topical rule now lives in its own `rules/` file.

**The pattern:** each rule file owns one topic (`git.md`, `safety.md`, `code-style.md`, `engineering-quality.md`, etc.). Rules stack with no override semantics — they all load and combine. Adding a new rule means creating a new file in `config/rules/` with a kebab-case name describing its topic.

**Do not put rule content in `CLAUDE.md`.** The stub redirect there enforces the convention. If you find yourself wanting to add to `CLAUDE.md`, create a new rule file instead.

## File Conventions

### Location
All rules live in `config/rules/` and are symlinked to `~/.claude/rules/` via `install.sh`. These load in every project, on every machine where this repo is installed.

### Loading Behavior
Claude loads `~/.claude/rules/*.md` into every conversation, stacked with `CLAUDE.md`. There is no triggering logic — rules are always on. This is the opposite of skills, which only load when their description matches the work.

### Naming
Use descriptive kebab-case names that identify the topic:
- `git-conventions.md`
- `security.md`
- `code-style.md`
- `dependencies.md`

Avoid generic names (`rules.md`, `general.md`) — the directory is already named `rules/`, so the filename should name the topic.

### No Frontmatter
Rules are plain markdown. No YAML frontmatter required — the entire file content is the instruction set.

## Writing Rule Content

Rules come in two shapes:

**Constraint rules** — short, declarative, one-line-per-bullet. Use for hard constraints with no nuance:

```markdown
# Git

- Use conventional commit format: `type: short description`
- Never force push without explicit approval
- Don't amend commits unless asked — create new commits instead
- Don't push unless asked
```

**Methodology rules** — longer-form rules that codify structural discipline (mandatory checkpoints, decision frameworks, recognition signatures). Use when the rule requires sections and concrete examples to be followable. `engineering-quality.md` and `proactive-doc-management.md` are examples.

The discriminator: if the rule states a hard constraint, keep it short. If the rule defines a process or discipline that needs structure to be effective, expand as needed but stay focused. Don't write prose paragraphs for their own sake. Methodology rules are still rules — they fire always, so concision still matters; just not at the extreme of one-line-per-bullet.

## Critical Rules

- **Rules are always loaded** — use them for universal constraints, not context-specific methodology
- **One topic per file** — the filename identifies the topic
- **Short and declarative** — rules are constraints, not tutorials
- **No frontmatter** — plain markdown
- **Don't duplicate `CLAUDE.md`** — when a rule is moved from `CLAUDE.md` into a rule file, remove it from `CLAUDE.md`

## Related Documentation

- `docs/guide/claude_code_rules.md` — Full rules architecture and loading hierarchy
- `docs/standards/skills.md` — Skill standards (for on-demand methodology)

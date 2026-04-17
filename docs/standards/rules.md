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

Our current `config/CLAUDE.md` is short and fits cleanly in one file. The `config/rules/` directory is **synced and ready but intentionally empty** — don't create rule files speculatively. It exists as the split target for when `CLAUDE.md` outgrows a single file, not as scaffolding to populate now.

**Heuristic:** If `config/CLAUDE.md` passes ~50 lines and you find yourself scrolling to locate instructions by topic, that's when splitting earns its keep. When splitting, move each coherent topic into its own rule file (`git-conventions.md`, `security.md`, etc.) and remove the content from `CLAUDE.md`. Don't duplicate — rules and `CLAUDE.md` stack, they don't override.

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

Keep rules short and declarative. Each rule is one line, ideally starting with a verb (Never, Always, Prefer, Use) or an imperative phrasing.

```markdown
# Git Conventions

- Use conventional commit format: `type: short description`
- Never force push without explicit approval
- Don't amend commits unless asked — create new commits instead
- Don't push unless asked
```

Don't write prose paragraphs in rule files. If a rule needs explanation, trim the explanation to the minimum needed and move the rest into a skill.

## Critical Rules

- **Rules are always loaded** — use them for universal constraints, not context-specific methodology
- **One topic per file** — the filename identifies the topic
- **Short and declarative** — rules are constraints, not tutorials
- **No frontmatter** — plain markdown
- **Don't duplicate `CLAUDE.md`** — when a rule is moved from `CLAUDE.md` into a rule file, remove it from `CLAUDE.md`

## Related Documentation

- `docs/guide/claude_code_rules.md` — Full rules architecture and loading hierarchy
- `docs/standards/skills.md` — Skill standards (for on-demand methodology)

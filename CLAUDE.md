# Claude Dotfiles

Personal Claude Code configuration repo. Syncs selected items from `~/.claude/` across machines (Ubuntu workstation, travel laptop, remote VMs) using targeted symlinks.

## Repo Structure

```
claude-dotfiles/
├── CLAUDE.md                    ← you are here
├── config.yaml                  ← centralized service/workflow configuration
├── config/                      ← source of truth for synced Claude Code config
│   ├── settings.json            ← global settings, permissions, hooks config
│   ├── CLAUDE.md                ← global instructions for all projects
│   ├── agents/                  ← subagent definitions (.md files)
│   ├── commands/                ← custom slash commands (.md files)
│   ├── hooks/                   ← hook scripts referenced by settings.json
│   ├── rules/                   ← global rules (.md files)
│   └── skills/                  ← reusable skill definitions (.md files)
├── install.sh                   ← creates individual symlinks into ~/.claude/
├── docs/
│   ├── architecture/             ← THE WHY: ADRs, system design
│   ├── development/              ← THE WHAT: roadmap, phases, features
│   ├── guide/                    ← OPERATING MANUAL: user-facing docs
│   ├── standards/                ← THE HOW: conventions and patterns
│   └── file_structure.txt        ← annotated map of the repo
└── README.md
```

**Documentation layout follows the four-bucket convention** (see `config/skills/documentation-structure.md`). Each bucket answers one question: architecture (WHY), development (WHAT), standards (HOW), guide (USER-FACING).

## Symlink Strategy

`install.sh` creates individual symlinks for only the items we manage. The rest of `~/.claude/` (credentials, sessions, history, cache, projects, etc.) is left untouched as machine-local state.

**Symlinked (7 targets):**
- `~/.claude/settings.json` → `config/settings.json`
- `~/.claude/CLAUDE.md` → `config/CLAUDE.md`
- `~/.claude/agents/` → `config/agents/`
- `~/.claude/commands/` → `config/commands/`
- `~/.claude/hooks/` → `config/hooks/`
- `~/.claude/rules/` → `config/rules/`
- `~/.claude/skills/` → `config/skills/`

**NOT synced (machine-local):** `.credentials.json`, `projects/`, `history.jsonl`, `sessions/`, `cache/`, `backups/`, `downloads/`, `file-history/`, `ide/`, `plans/`, `plugins/`, `session-env/`, `shell-snapshots/`, `telemetry/`

## Key Context

- **Owner**: Puma. Claude Max subscriber ($100/mo). Migrating from ChatGPT + Cursor to Claude + Claude Code.
- **Sync method**: Targeted symlinks via bash `install.sh` (not GNU Stow — selective linking within `~/.claude/` is cleaner than stow's tree-mirroring approach)
- **What syncs**: settings.json, CLAUDE.md, agents/, commands/, hooks/, rules/, skills/
- **What does NOT sync**: Everything else in `~/.claude/` — credentials, sessions, projects (path-keyed), cache, history, etc.
- **Hardware**: A6000 (48GB), RTX 4080 (16GB), several 8GB GPUs — Ollama instances managed by SkyyCommand

## Development

See `docs/development/roadmap.md` for the full phased migration plan. Phases 0-3 complete, current focus is Phase 4 (Autonomous Execution).

## Reference Documentation

For detailed documentation on Claude Code concepts:
- Agent architecture and two-tier strategy: `docs/guide/claude_code_agents.md`
- Headless mode, worktrees, and autonomous runs: `docs/guide/claude_code_headless.md`
- Orchestration options and patterns: `docs/guide/claude_code_orchestration.md`
- Rules and when to use them: `docs/guide/claude_code_rules.md`
- Skills and context-aware methodology: `docs/guide/claude_code_skills.md`
- Workflows guide (all scripts, dual model, usage): `docs/guide/workflows.md`

## Standards

For contributing to this repo, follow the standards:
- For agent standards, refer to `docs/standards/agents.md`
- For hook script standards, refer to `docs/standards/hook-scripts.md`
- For rule standards, refer to `docs/standards/rules.md`
- For skill standards, refer to `docs/standards/skills.md`
- For service standards, refer to `docs/standards/services.md`
- For slash command standards, refer to `docs/standards/slash-commands.md`
- For workflow script standards, refer to `docs/standards/workflow-scripts.md`

## Rules

- Do not create files outside the repo structure defined above without asking first.
- When creating hook scripts, follow `docs/standards/hook-scripts.md` (stdin JSON + jq, never env vars).
- MCP secrets must use `${env:VAR_NAME}` references, never hardcoded values.
- Keep `config/` as the single source of truth — never edit `~/.claude/` directly for synced items.
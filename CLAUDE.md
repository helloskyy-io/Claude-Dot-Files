# Claude Dotfiles

Personal Claude Code configuration repo. Syncs selected items from `~/.claude/` across machines (Ubuntu workstation, travel laptop, remote VMs) using targeted symlinks.

## Repo Structure

```
claude-dotfiles/
├── CLAUDE.md                    ← you are here
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
│   ├── file_structure.txt       ← detailed file structure reference
│   └── development/
│       └── roadmap.md           ← phased migration plan
└── README.md
```

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

See `docs/development/roadmap.md` for the full phased migration plan. Current focus is Phase 1 (cross-device sync).

## Rules

- Do not create files outside the repo structure defined above without asking first.
- When creating hook scripts, they must read JSON from stdin (not env vars). Use `INPUT=$(cat)` then parse with `jq`.
- MCP secrets must use `${env:VAR_NAME}` references, never hardcoded values.
- Keep `config/` as the single source of truth — never edit `~/.claude/` directly for synced items.
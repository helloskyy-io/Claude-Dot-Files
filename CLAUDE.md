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
│   ├── architecture/             ← THE WHY: architecture standards, system design
│   ├── development/              ← THE WHAT: roadmap, phases, features
│   ├── guide/                    ← OPERATING MANUAL: user-facing docs
│   ├── standards/                ← THE HOW: conventions and patterns
│   └── file_structure.txt        ← annotated map of the repo
├── tracked/                      ← the four tracked-item stores (issues/operations/candidates/standards)
├── testing/                      ← Tier 1 + 2 of the Testing Standard: run-all.sh, suites/
├── conftest.py                   ← repo-root pytest memory guardrail (RLIMIT_AS)
├── pytest.ini                    ← pins rootdir so that guardrail is invocation-agnostic
└── README.md
```

This is an orientation sketch, not the exhaustive map — `docs/file_structure.txt` is that, and it is authoritative. (`scripts/` is a top-level directory this sketch has never listed.)

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

See `docs/development/sprint.md` for the full phased migration plan. Phases 0-3 complete, current focus is Phase 4 (Autonomous Execution).

## Reference Documentation

For detailed documentation on Claude Code concepts:
- Agent architecture and two-tier strategy: `docs/guide/claude_code_agents.md`
- Headless mode, worktrees, and autonomous runs: `docs/guide/claude_code_headless.md`
- Orchestration options and patterns: `docs/guide/claude_code_orchestration.md`
- Rules and when to use them: `docs/guide/claude_code_rules.md`
- Skills and context-aware methodology: `docs/guide/claude_code_skills.md`
- Workflows guide (all scripts, dual model, usage): `docs/guide/workflows.md`
- CPI cycle (review-runs + decisions log + cadence): `docs/guide/cpi-cycle.md`

## Standards

For contributing to this repo, follow the standards:
- For agent standards, refer to `docs/standards/agents.md`
- For hook script standards, refer to `docs/standards/hook-scripts.md`
- For rule standards, refer to `docs/standards/rules.md`
- For skill standards, refer to `docs/standards/skills.md`
- For service standards, refer to `docs/standards/services.md`
- For slash command standards, refer to `docs/standards/slash-commands.md`
- For workflow script standards, refer to `docs/standards/workflow-scripts.md`
- For research standards, refer to `docs/standards/research/` — **vendored (MIRROR)**. Research is EVIDENCE, never binding; pools live at TWO altitudes — `docs/standards/architecture/research/` for findings that could change WHAT we build, and `docs/development/<phase>/research/` for the ~98% that decide HOW to build something already committed to.
- **For where a FINDING goes — a bug, a proposal, a ruling, operating state — refer to `docs/standards/finding-routing.md`.** It owns that question end to end and is the single place to look; the documents below are cited by it where they bind. Its `INTERFACE` sections are a promotion candidate for MDC-Master-Planning; its `BINDING` section is ours.
- For documentation standards, refer to `docs/standards/documentation/` — **vendored (MIRROR)** from MDC-Master-Planning. Start with its `README.md`. Binding here: standards state the rule never completion-state; cite a codified block rather than re-listing it; cross-reference instead of repeating; and **a CLAUDE.md references standards, it never contains standards content**.
- For testing standards, refer to `docs/standards/testing/` — **vendored (MIRROR)**. Three tiers: master runner (`testing/run-all.sh`), framework suite runners (`testing/suites/`), and per-unit `tests/` directories categorized `unit/` / `integration/` / `e2e/`. **pytest**, not script-style tests. Start with its `README.md`, which states which half of the vendored standard binds here and, in § The gate, what the merge-path gate covers. That gate is `.github/workflows/tests.yml` (issue #30, closed). Tests for `config/hooks/` are the one documented placement divergence — see `testing/config-hooks/README.md`.
- For Temporal standards, refer to `docs/standards/temporal/` — **vendored (MIRROR)** from MDC-Master-Planning. Start with its `README.md`, which states what binds today (§3 three-layer architecture, §3.4 composition, §7 idempotency) versus what applies only once workers exist. Local additions go in `claude-dot-files-addendum.md`.

**Vendored standards are verbatim copies and MUST NOT be edited here** — amendments go upstream, then re-vendor with `scripts/helpers/vendor-standards.sh`. `--check` fails on local drift.

## Rules

- Do not create files outside the repo structure defined above without asking first.
- When creating hook scripts, follow `docs/standards/hook-scripts.md` (stdin JSON + jq, never env vars).
- MCP secrets must use `${env:VAR_NAME}` references, never hardcoded values.
- Keep `config/` as the single source of truth — never edit `~/.claude/` directly for synced items.
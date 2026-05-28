# System Overview

High-level architecture of the claude-dot-files repo — how the layers fit together, what decisions shape the system, and where the seams are.

## What this repo does

Personal Claude Code configuration that syncs across multiple machines (workstation, laptop, remote VMs) via targeted symlinks. Provides:

- Always-loaded global instructions (rules + CLAUDE.md stub)
- Description-matched skills (on-demand methodology)
- Named subagents (specialist Claude sessions)
- Slash commands (interactive prompt-template injection)
- Hook scripts (safety + notification gates)
- Autonomous workflow scripts (`scripts/workflows/`)
- A polling GitHub monitor service (`scripts/services/gh-monitor.sh`)

## Layered architecture

```
Always-loaded layer (session start)
├── CLAUDE.md           — stub redirect to /rules
├── rules/*.md          — topical behavioral rules
└── settings.json       — permissions + hook config

On-demand layer (description-matched / explicit)
├── skills/*.md         — methodology, loaded when context matches
├── agents/*.md         — named specialists, invoked via Task tool
└── commands/*.md       — slash commands, invoked via /<name>

Hook layer (event-driven)
├── PreToolUse → block-dangerous.sh   — safety gate before Bash
└── Stop → notify-done.sh             — desktop notification on completion

Workflow layer (autonomous via claude -p)
├── scripts/workflows/lib/            — shared helpers (run-claude.sh, format-stream.sh)
└── scripts/workflows/*.sh            — task-execution + analysis workflows

Service layer (background)
└── scripts/services/gh-monitor.sh    — systemd timer polls GitHub for @claude PR comments
```

Each layer has clean separation: rules are constraints, skills are methodology, agents are specialists, commands are templates, hooks are gates, workflows are autonomous orchestrators, services are background processes. No layer reaches into another layer's responsibilities.

## Key architectural decisions

Recorded here because each shaped the system meaningfully. Binding decisions with full trade-off analysis live in `docs/standards/` per the standards-governance rule; this section captures the architectural shape at a glance.

### Sync strategy: targeted symlinks (not GNU Stow)

`install.sh` creates 7 individual symlinks from `config/*` into `~/.claude/`. Chosen over GNU Stow (which mirrors entire directory trees) because:

- Surgical control over what syncs vs what stays machine-local (`credentials/`, `projects/`, `sessions/`, `cache/`, telemetry — all machine-local by nature)
- Idempotent reinstall with conflict backup to `~/.claude/backups/pre-install-<ts>/`
- `--non-interactive` flag for Ansible automation on workstations/laptops
- VM deployment uses interactive mode (auth requires browser OAuth)

### Dual permission model

Interactive sessions: conservative allow/deny lists in `settings.json` with permission prompts for unlisted commands.

Autonomous workflows: `--dangerously-skip-permissions` flag (no prompts, faster execution). Safety provided by `block-dangerous.sh` PreToolUse hook which fires regardless of the skip-permissions flag. Verified empirically that hooks fire under autonomous mode.

Two layers of defense, calibrated per workflow shape.

### Hook architecture

Hooks defined in `settings.json` reference scripts in `config/hooks/`. Three hook types available, current usage:

- **PreToolUse** with matcher `Bash` → `block-dangerous.sh` (regex-based deny list for destructive commands)
- **Stop** → `notify-done.sh` (desktop notification via `notify-send`, gracefully skips on headless machines)

Hook scripts receive event JSON on stdin (NOT environment variables). Parse with `jq`. Output structured responses via JSON-on-stdout.

PostToolUse auto-format hooks intentionally NOT used — formatting on every Write/Edit eats context window. Project-level formatting (prettier, black) runs at commit time instead.

### Orchestration: bash-over-Python

Bash scripts wrap `claude -p` invocations with structured stages, safety guards, visibility, and JSONL logging. Chosen over Python/Agent SDK because:

- Portable forward (can migrate to SDK later without losing logic)
- Debuggable with standard shell tools
- Zero learning curve beyond what's already known
- Native to the operator's environment

Graduation triggers documented in `docs/development/roadmap.md` — move to Agent SDK only if real limitations surface (error handling, structured data, team scale).

### Dual workflow model

Two ways the operator works with Claude Code:

- **Interactive** — daily small changes, in-the-loop approval, fast iteration
- **Autonomous** — large planned features via `scripts/workflows/*.sh`, walk-away execution, PR delivery for review

Each workflow script implements specific stages with numbered structure. See `docs/guide/workflows.md` for the full workflow inventory and `MAX_TURNS` per script.

### Worktree-per-task isolation

All workflow scripts that modify code use git worktrees in `.claude/worktrees/<workflow>-<timestamp>/`. The main working directory is never touched by autonomous runs. Two patterns:

- **New branch:** Claude Code creates the worktree via `-w <name>` flag with auto-prefixed `worktree-` branch name
- **Update existing PR:** Manually create worktree checked out to the PR's branch, then invoke claude inside it

The main branch is sacred — autonomous changes only reach `main` through PR review and merge.

### JSONL log contract

Every workflow run writes a raw JSONL log to `.claude/logs/<workflow>-<timestamp>.jsonl`. Format invariant:

- **Lossless** — no information dropped vs the stream-json events
- **Self-diagnosable** — Claude can read the log directly to post-mortem a failed run
- **Queryable** — `jq` extracts metrics (cost, turns, duration, errors)
- **Formattable on demand** — `scripts/workflows/lib/format-stream.sh` converts JSONL → human-readable text

Logs always live in the MAIN repo's `.claude/logs/`, not inside worktrees, so all logs aggregate in one place for analysis.

### CPI loop (continuous process improvement)

Real workflow runs produce JSONL logs. `scripts/workflows/review-runs.sh` analyzes recent logs and produces structured reports in `docs/development/reviews/`. The interactive architecture session reviews findings and ships/defers/rejects each one. Deferrals get appended to `docs/development/cpi-decisions.md` with explicit watch-criteria. Append-only — entries don't get deleted, just amended when previously-deferred items eventually ship.

This is the mechanism by which the system improves itself over time without requiring all-knowing upfront design.

### gh-monitor: local polling (not webhook)

`scripts/services/gh-monitor.sh` runs as a systemd user timer polling GitHub every 5 minutes for `@claude` PR comments. Local polling chosen over GitHub Actions / webhooks because:

- GitHub Actions runners require Claude API billing (not Max subscription)
- Webhooks would require exposing an endpoint (Tailscale-hardened workstation, undesirable surface)
- 5-minute polling latency is acceptable for the workflow ergonomics
- Reaction-based deduplication (👀 / hooray / -1 / confused emojis) makes multi-machine concurrency safe

### Standards-not-ADRs convention

Architectural decisions are captured as standards documents in `docs/standards/<topic>.md`, not as numbered ADR files. Codified in `config/rules/standards-governance.md`. The architecture-decisions skill's methodology (trade-off analysis, alternatives, consequences) still applies — but the artifact is a standards doc. Standards are easier for AI to read and reference than scattered numbered ADRs.

`docs/architecture/` (this directory) holds high-level overviews and supporting docs (system-overview, threat-model, component-diagram) — not per-decision artifacts.

## Where the seams are

Clean seams:
- Config (`config/`) vs imperative scripts (`scripts/`)
- Always-loaded (rules + CLAUDE.md) vs on-demand (skills + agents + commands)
- Interactive permission model vs autonomous permission model
- Per-task worktree isolation vs shared main branch
- Workflow scripts vs background services

Seams worth being aware of:
- The `--dangerously-skip-permissions` + hook trust model: the hook is the load-bearing safety floor for autonomous mode; regex-based pattern matching has known limits worth understanding (see `docs/development/loose_ends.md` for threat model TODO)
- Workflow prompt duplication across scripts: shared stages exist as bash variables in some scripts but not all; `DECISION_LOG_AND_REFLECTION` is copy-pasted across 6 scripts (extraction is a known refactor item)
- `gh-monitor` single-instance assumption: no heartbeat / health-check — silent failures only surface when the operator notices missed PR replies

## Related documentation

- `docs/guide/workflows.md` — operating manual for the workflows
- `docs/guide/cpi-cycle.md` — how the CPI loop runs
- `docs/standards/workflow-scripts.md` — binding rules for workflow script structure
- `docs/standards/hook-scripts.md` — binding rules for hook scripts
- `docs/standards/services.md` — binding rules for long-running services
- `docs/development/roadmap.md` — what we've built and what's next
- `docs/development/cpi-decisions.md` — append-only log of CPI decisions
- `docs/development/loose_ends.md` — deferred architectural items with re-evaluation triggers

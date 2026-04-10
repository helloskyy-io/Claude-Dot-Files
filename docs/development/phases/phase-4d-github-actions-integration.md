# Phase 4d: PR Comment Automation — Local GitHub Monitor

## Status
Not started (redesigned 2026-04-10)

## Overview
A local systemd service that polls GitHub for `@claude` PR comments and launches the appropriate workflow script. Uses the Max subscription locally — zero API costs, zero security exposure.

## Goal
PR comments become an iteration mechanism: comment `@claude fix X` → poller detects it → runs `revision.sh --pr N` locally → PR updates. All using existing workflows, existing auth, existing infrastructure.

## Architecture

```
┌────────────────────────────────────────┐
│  systemd timer (every 5 min)           │
│  Unit: gh-monitor.timer                │
└────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│  scripts/services/gh-monitor.sh        │
│  (bash + gh CLI — no AI for polling)   │
│                                        │
│  1. Source config from gh-monitor.     │
│     config.env                         │
│  2. For each repo in config:           │
│     a. List open PRs with comments     │
│     b. Filter for @claude mentions     │
│     c. Skip comments already reacted   │
│  3. For each unprocessed comment:      │
│     a. React 👀 (processing)           │
│     b. Parse route and description     │
│     c. Launch correct workflow          │
│     d. React ✅ or ❌ based on result  │
│     e. Post error comment if failed    │
└────────────────────────────────────────┘
         │ routes to (explicit prefix required):
         ▼
┌────────────────────────────────────────┐
│  @claude revision: fix X               │
│  → revision.sh "fix X" --pr N          │
│                                        │
│  @claude revision-major: restructure Y │
│  → revision-major.sh "restructure Y"   │
│    --pr N                              │
│                                        │
│  @claude help                          │
│  → gh pr comment (post help text)      │
│                                        │
│  @claude <unrecognized route>          │
│  → gh pr comment (ask for valid cmd)   │
└────────────────────────────────────────┘
```

## Why NOT GitHub Actions
1. **Billing mismatch** — Actions runners require Claude API tokens (per-token billing), not the $100/mo Max subscription
2. **Security exposure** — Workstation is Tailscale-hardened with no open ports. GitHub webhooks would require external exposure. Polling reaches OUT to GitHub; nothing reaches IN.
3. **Unnecessary complexity** — Spinning up VMs to install Claude Code per comment is heavyweight

## Requirements

### Functional
- Systemd timer runs `gh-monitor.sh` on a configurable interval (default: 5 min)
- Poller checks all configured repos for open PRs with `@claude` comments
- Reaction-based deduplication prevents processing the same comment twice
- Routes comments to the correct workflow based on explicit prefix (no default route):
  - `@claude revision: <description>` → `revision.sh "<description>" --pr N`
  - `@claude revision-major: <description>` → `revision-major.sh "<description>" --pr N`
  - `@claude help` → post a help comment listing available commands and syntax
  - `@claude <anything without a recognized route>` → post a clarifying comment asking for a valid command prefix
- Every command requires an explicit route — no implicit defaults, no guessing
- React with emoji to track state: 👀 (processing), ✅ (done), ❌ (failed), 💬 (clarification needed)
- Post error comment on PR if a workflow fails
- JSONL logs captured per workflow standard (from the workflow scripts themselves)

### Non-functional
- Polling uses zero Claude tokens (bash + `gh` CLI only)
- Must handle machine being off (backlog processing on restart, skip comments older than 7 days)
- Must not process same comment twice even if multiple machines are polling (reaction-based dedup)
- Must not block if a workflow is already running (concurrency guard with lock file)
- Must handle `gh` API rate limits gracefully (check remaining quota, back off if low)

### Constraints
- `gh` CLI must be installed and authenticated
- Workflow scripts must exist in the repo
- Systemd user service support required (standard on Linux Mint/Ubuntu)
- Runs as user, not root (principle of least privilege)
- Workstation must be on for polling to work (acceptable tradeoff for zero cost)

## File Layout

```
scripts/
└── services/
    ├── gh-monitor.sh              # the polling script
    ├── gh-monitor.service         # systemd oneshot unit
    ├── gh-monitor.timer           # systemd timer (5 min default)
    ├── gh-monitor.config.env      # configuration (gitignored if contains secrets)
    └── gh-monitor.config.env.example  # documented config template (committed)
```

Follows the service standards in `docs/standards/services.md`.

## Configuration

Config file: `scripts/services/gh-monitor.config.env`

```bash
# Repos to monitor (space-separated owner/repo)
GH_MONITOR_REPOS="helloskyy-io/Claude-Dot-Files"

# Max simultaneous workflows (concurrency guard)
GH_MONITOR_MAX_CONCURRENT=1

# Route enablement
GH_MONITOR_ENABLE_REVISION=true
GH_MONITOR_ENABLE_REVISION_MAJOR=true
GH_MONITOR_ENABLE_HELP=true

# Dry run mode (detect comments, log what would happen, but don't run workflows)
GH_MONITOR_DRY_RUN=false

# Backlog limit (skip comments older than N days)
GH_MONITOR_BACKLOG_DAYS=7

# Path to workflow scripts
GH_MONITOR_WORKFLOW_DIR="${HOME}/Repos/claude-dot-files/scripts/workflows"
```

All variables have sensible defaults in the script. Config file overrides.

## Deployment

### Via install.sh (opt-in)

```bash
./install.sh --with-services
```

This:
1. Creates `~/.config/systemd/user/` if needed
2. Symlinks `.service` and `.timer` files
3. Runs `systemctl --user daemon-reload`
4. Enables and starts the timer
5. Copies `.config.env.example` to `.config.env` if no config exists

### Manual

```bash
# Symlink units
ln -sf ~/Repos/claude-dot-files/scripts/services/gh-monitor.service ~/.config/systemd/user/
ln -sf ~/Repos/claude-dot-files/scripts/services/gh-monitor.timer ~/.config/systemd/user/

# Reload and start
systemctl --user daemon-reload
systemctl --user enable gh-monitor.timer
systemctl --user start gh-monitor.timer

# Copy config
cp scripts/services/gh-monitor.config.env.example scripts/services/gh-monitor.config.env
# Edit config as needed
```

## Tasks

### Core Service
- [ ] **Create `scripts/services/gh-monitor.sh`** — Main polling script. Sources config, iterates repos, finds unprocessed `@claude` comments, routes to workflows, manages reactions and error comments.
- [ ] **Create `scripts/services/gh-monitor.config.env.example`** — Documented config template with all variables and defaults.
- [ ] **Reaction-based deduplication** — Check for existing 👀/✅/❌/💬 reactions before processing. First reactor wins (multi-machine safe).
- [ ] **Comment routing logic** — Parse `@claude help`, `@claude revision-major: <desc>`, and default `@claude <desc>`. Handle edge cases (code blocks, nested mentions).
- [ ] **Insufficient context handling** — When description is too vague (e.g., `@claude fix it` with no specifics), post a clarifying comment and react with 💬 instead of guessing.
- [ ] **Concurrency guard** — Lock file at `.claude/state/gh-monitor.lock`. Skip if locked. Release on exit via trap.
- [ ] **Error handling** — Single-comment failures don't crash the poller. Post error comment with reason. React ❌. Continue to next comment.

### Systemd Integration
- [ ] **Create `gh-monitor.service`** — Type=oneshot, runs as user, network dependency
- [ ] **Create `gh-monitor.timer`** — 5-minute interval, Persistent=true for backlog on boot
- [ ] **Update `install.sh`** — Add `--with-services` flag for opt-in service deployment (idempotent)
- [ ] **Document management commands** — enable, disable, status, logs

### Help Command
- [ ] **`@claude help` response** — Posts a PR comment with a formatted table of available commands, syntax, and examples

### Testing
- [ ] **Dry run mode** — `GH_MONITOR_DRY_RUN=true` logs what would happen without invoking workflows
- [ ] **Manual test** — Post `@claude help` on a test PR, verify response
- [ ] **Revision test** — Post `@claude fix X` on a test PR, verify workflow runs and PR updates
- [ ] **Error test** — Post something that should fail, verify ❌ reaction and error comment

## Scalability Notes (v1 acknowledged, not solved)

- **Multi-machine:** Reaction-based dedup handles this for v1. First machine to react 👀 wins.
- **Multi-repo:** Config file accepts a list. Repos processed sequentially.
- **Backlog:** `Persistent=true` + backlog day limit (default 7 days) handles this.
- **Rate limits:** `gh` CLI handles auth token rate limits. Monitor with `gh api rate_limit` if needed.
- **Concurrency:** Lock file prevents overlapping runs. Max concurrent workflows configurable.

## Dependencies
- `gh` CLI installed and authenticated ✅
- Workflow scripts (revision.sh, revision-major.sh) ✅
- Systemd user services ✅ (standard on Linux Mint/Ubuntu)
- Service standards (`docs/standards/services.md`) ✅

## Success Criteria
- [ ] Timer fires every 5 minutes (verify with `systemctl --user status gh-monitor.timer`)
- [ ] `@claude fix X` on a PR triggers revision.sh and pushes a fix
- [ ] `@claude revision-major: Y` triggers revision-major.sh
- [ ] `@claude help` posts a helpful comment
- [ ] Same comment never processed twice (reaction dedup verified)
- [ ] Failed runs react ❌ and post error comment
- [ ] Vague requests get clarifying comment + 💬 reaction
- [ ] Zero Claude tokens burned on polling
- [ ] Survives machine reboot (Persistent=true)
- [ ] Dry run mode works for testing

## Risks & Mitigations
- **Risk:** Machine is off when comment is posted
  - **Mitigation:** Poller catches up on next boot (Persistent=true). Comments don't expire. Skip > 7 days.
- **Risk:** Multiple machines both react to same comment
  - **Mitigation:** First to react 👀 wins. Others see the reaction and skip. Inherently safe.
- **Risk:** `gh` auth expires
  - **Mitigation:** Check `gh auth status` at startup. Exit with clear error if not authed.
- **Risk:** Comment parsing edge cases (code blocks, nested mentions)
  - **Mitigation:** Match `@claude` only at start of comment or after newline. Ignore content inside backtick blocks.
- **Risk:** Workflow takes too long and overlaps with next timer cycle
  - **Mitigation:** Lock file prevents concurrent runs. Next cycle skips if locked.

## Standards
- Follow `docs/standards/services.md` for service conventions
- Workflow invocations follow `docs/standards/workflow-scripts.md`
- Follow `docs/standards/hook-scripts.md` for any hook-related integration
- Bash conventions: `set -euo pipefail`, env checks, clear errors

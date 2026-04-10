# Service Standards

Conventions for building long-running services and daemons in `scripts/services/`.

## Purpose

Services are background processes that run on a timer or continuously, performing automated tasks without user interaction. They differ from workflow scripts (which run once per invocation) and hooks (which run per Claude tool call).

Examples: GitHub comment pollers, log rotation, scheduled CPI analysis, health checks.

## File Conventions

### Location
```
scripts/
├── services/
│   ├── gh-monitor.sh              # the service script
│   ├── gh-monitor.service          # systemd unit file
│   ├── gh-monitor.timer            # systemd timer file
│   └── gh-monitor.config.env       # config file (not committed if contains secrets)
└── workflows/                      # workflow scripts (different concern)
```

### Naming
Name services for the **category**, not the specific first use case.

**Good:** `gh-monitor` (can handle PR comments, issues, reviews, CI failures)
**Bad:** `pr-watcher` (too specific — what about issue watching?)

**Rule:** If you can imagine a second handler for this service, the name should already accommodate it.

File naming:
- Service script: `<name>.sh`
- Systemd service: `<name>.service`
- Systemd timer: `<name>.timer`
- Config: `<name>.config.env` (or `.yaml` for complex config)

### Executable
Service scripts must be executable (`chmod +x`). Systemd unit files should NOT be executable.

## Configuration

### Config File Pattern
Services with configurable behavior use an environment file sourced at startup.

**Location:** `scripts/services/<name>.config.env`

**Format:**
```bash
# gh-monitor configuration
# -----------------------------------------------

# Repos to monitor (space-separated)
GH_MONITOR_REPOS="helloskyy-io/Claude-Dot-Files"

# Polling interval is controlled by the systemd timer, not here

# Concurrency: max simultaneous workflows
GH_MONITOR_MAX_CONCURRENT=1

# Route enablement
GH_MONITOR_ENABLE_REVISION=true
GH_MONITOR_ENABLE_REVISION_MAJOR=true
GH_MONITOR_ENABLE_HELP=true

# Workflow max turns (override defaults)
GH_MONITOR_REVISION_MAX_TURNS=30
GH_MONITOR_REVISION_MAJOR_MAX_TURNS=75

# Dry run mode (check for comments but don't run workflows)
GH_MONITOR_DRY_RUN=false
```

### Config Rules
- **Prefix all variables** with the service name in SCREAMING_SNAKE_CASE to avoid collisions
- **Document every variable** with a comment explaining what it does
- **Provide sensible defaults** in the script itself — the config file overrides, not defines
- **Never commit secrets** — if the config contains tokens or keys, add it to `.gitignore` and document the required variables
- **Ship a `.config.env.example`** with all variables documented but secrets blanked

### Loading Config
```bash
# Source config file if it exists (all vars have defaults in the script)
CONFIG_FILE="${SCRIPT_DIR}/<name>.config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

# Defaults (applied if not set by config)
: "${GH_MONITOR_REPOS:=""}"
: "${GH_MONITOR_MAX_CONCURRENT:=1}"
: "${GH_MONITOR_DRY_RUN:=false}"
```

The `: "${VAR:=default}"` pattern sets the default only if the variable is unset or empty.

## Systemd Integration

### Service Unit File
```ini
# gh-monitor.service
[Unit]
Description=GitHub monitor for @claude PR comment automation
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/home/%u/Repos/claude-dot-files/scripts/services/gh-monitor.sh
Environment=HOME=/home/%u

[Install]
WantedBy=default.target
```

### Timer Unit File
```ini
# gh-monitor.timer
[Unit]
Description=Run GitHub monitor every 5 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
Persistent=true

[Install]
WantedBy=timers.target
```

### Key Design Choices
- **Type=oneshot** — the script runs, does its work, and exits. The timer triggers it again.
- **Persistent=true** — if the machine was off when a timer would have fired, it runs immediately on boot.
- **User service** — runs as the user, not root. Lives in `~/.config/systemd/user/`.
- **%u** — expands to the current username for portability.

### Deployment
Services are deployed by `install.sh` with an opt-in flag:

```bash
# In install.sh:
if [[ "$INSTALL_SERVICES" == "true" ]]; then
    mkdir -p "$HOME/.config/systemd/user"
    ln -sf "$REPO_DIR/scripts/services/gh-monitor.service" "$HOME/.config/systemd/user/"
    ln -sf "$REPO_DIR/scripts/services/gh-monitor.timer" "$HOME/.config/systemd/user/"
    systemctl --user daemon-reload
    systemctl --user enable gh-monitor.timer
    systemctl --user start gh-monitor.timer
fi
```

**Opt-in because:** Not every machine needs services running. Workstation? Yes. Laptop? Maybe. VM? Probably not.

### Management Commands
```bash
# Enable and start
systemctl --user enable gh-monitor.timer
systemctl --user start gh-monitor.timer

# Check status
systemctl --user status gh-monitor.timer
systemctl --user status gh-monitor.service

# View logs
journalctl --user -u gh-monitor.service -f

# Stop
systemctl --user stop gh-monitor.timer

# Disable (won't start on boot)
systemctl --user disable gh-monitor.timer
```

## Script Conventions

### Bash Standards
Same as workflow scripts:
- `#!/usr/bin/env bash`
- `set -euo pipefail`
- Environment checks at startup (verify `gh`, `jq`, etc.)
- Clear error messages on failure

### State Tracking
Services that process items need to track what's been processed.

**For the GitHub monitor:** Use emoji reactions on comments as state markers:
- 👀 (eyes) — processing started
- ✅ (check) — completed successfully
- ❌ (cross) — failed

This is idempotent — checking "does this comment already have a 👀 reaction?" is a simple API call.

**For other services:** Use a state file in `.claude/state/<service-name>/` if API-based state tracking isn't available.

### Concurrency Control
If a service might overlap with itself or with manual workflow runs:
- Use a lock file (e.g., `.claude/state/gh-monitor.lock`)
- Check for running workflows before launching new ones
- Release the lock on exit (use `trap` for cleanup)

```bash
LOCK_FILE="${STATE_DIR}/gh-monitor.lock"
if [[ -f "$LOCK_FILE" ]]; then
    echo "Another instance is running. Skipping."
    exit 0
fi
trap 'rm -f "$LOCK_FILE"' EXIT
touch "$LOCK_FILE"
```

### Logging
Services log to systemd journal by default (stdout/stderr captured by systemd). For additional structured logging, write to `.claude/logs/` following the workflow logging convention.

### Error Handling
- **Don't crash the service on single-item failures.** If processing one comment fails, log it, react with ❌, and continue to the next.
- **Do crash on infrastructure failures.** If `gh` isn't authed or the network is down, exit with error.
- **Post error comments on PRs** when a workflow fails, so the commenter knows what happened.

### Insufficient Context Handling
When a comment or request doesn't provide enough context for Claude to act:
- **Don't guess.** A wrong implementation costs hours to undo.
- **Post a clarifying comment** asking for specifics.
- React with a 💬 (speech bubble) to indicate "question asked."
- The next polling cycle can check if the user replied.

## Scaling Considerations

### Multi-Machine
If the same service runs on multiple machines, they'll both try to process the same comments. Solutions:
- **Leader election** — only one machine processes (complex)
- **Reaction-based dedup** — first machine to react with 👀 wins, others skip (simple, recommended)

### Multi-Repo
Accept a list of repos in the config file. Process each repo in sequence per polling cycle.

### Backlog Processing
When the machine comes back online after being off:
- `Persistent=true` in the timer ensures it runs immediately
- Process oldest-first to maintain order
- Set a reasonable backlog limit (e.g., skip comments older than 7 days)

## Critical Rules

- **Name for the category, not the instance** — extensible naming from day one
- **Config files for anything an operator might change** — don't hardcode
- **Opt-in deployment** — not every machine needs services
- **State tracking is mandatory** — never process the same item twice
- **Don't crash on single-item failures** — log and continue
- **Don't guess when context is insufficient** — ask for clarification
- **User services, not root** — principle of least privilege
- **Secrets never committed** — use `.config.env.example` pattern

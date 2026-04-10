# Service Standards

Conventions for building long-running services and daemons in `scripts/services/`.

## Purpose

Services are background processes that run on a timer or continuously, performing automated tasks without user interaction. They differ from workflow scripts (which run once per invocation) and hooks (which run per Claude tool call).

Examples: GitHub comment pollers, log rotation, scheduled CPI analysis, health checks.

## File Conventions

### Location
```
config.yaml                            # centralized config (committed, no secrets)
scripts/
├── services/
│   ├── gh-monitor.sh              # the service script
│   ├── gh-monitor.service          # systemd unit file
│   └── gh-monitor.timer            # systemd timer file
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
- Config: section in `config.yaml` at repo root

### Executable
Service scripts must be executable (`chmod +x`). Systemd unit files should NOT be executable.

## Configuration

### Centralized config.yaml
All service configuration lives in `config.yaml` at the repo root. Each service gets its own top-level YAML section with kebab-case keys.

**Location:** `config.yaml` (committed — no secrets)

**Format:**
```yaml
# gh-monitor — GitHub monitor for @claude PR comment automation
gh-monitor:
  repos: "helloskyy-io/Claude-Dot-Files"
  max-concurrent: 1
  enable-revision: true
  enable-revision-major: true
  enable-help: true
  dry-run: false
  backlog-days: 7
```

### Config Rules
- **One section per service** — use the service name as the top-level YAML key
- **Use kebab-case keys** — YAML convention, not SCREAMING_SNAKE_CASE
- **Document every field** with a YAML comment explaining what it does
- **Provide sensible defaults** in the script itself — config.yaml overrides, not defines
- **Never put secrets in config.yaml** — it is committed to the repo
- **Environment variables override config.yaml** — allows machine-specific overrides without editing the file

### Loading Config
Services read from `config.yaml` using `yq` (requires [mikefarah/yq](https://github.com/mikefarah/yq)):

```bash
CONFIG_FILE="${REPO_ROOT}/config.yaml"

# Helper: read a value from config.yaml, returns empty string if key is missing/null
# Usage: cfg <section> <key>
cfg() {
    local section="$1" key="$2"
    local val
    val=$(yq -r ".${section}.${key}" "$CONFIG_FILE" 2>/dev/null || echo "")
    # yq prints "null" for missing keys
    if [[ "$val" == "null" ]]; then echo ""; else echo "$val"; fi
}

if [[ -f "$CONFIG_FILE" ]]; then
    MY_VAR="${MY_VAR:-$(cfg my-service some-key)}"
fi

# Defaults (applied if not set by config or environment)
: "${MY_VAR:=default-value}"
```

**Precedence:** environment variable > config.yaml > script default.

### Prerequisites
Services that read `config.yaml` must check for `yq` at startup alongside `gh` and `jq`:
```bash
for cmd in gh jq yq; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "Error: '$cmd' not found in PATH" >&2
        exit 1
    fi
done
```

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
- 🎉 (hooray) — completed successfully
- 👎 (-1) — failed
- 💬 (confused) — clarification requested

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
- **Secrets never committed** — config.yaml is committed (no secrets); use env vars for sensitive values

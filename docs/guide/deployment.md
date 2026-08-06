# Deployment

How to install and sync this configuration across machines. **Operation is covered separately** — see [`operations.md`](operations.md) once everything is installed.

## The model: targeted symlinks, nothing clever

`install.sh` creates individual symlinks from `config/` into `~/.claude/`. It does not manage the whole directory, and that is deliberate: `~/.claude/` also holds credentials, session history, project state and caches, none of which should be in git and none of which is portable between machines.

So the split is between **what we author** (symlinked, versioned, identical everywhere) and **what the machine accumulates** (left alone). A machine with no config repo still works; a machine with one gets the same agents, skills, rules and hooks as every other.

**There is no server component, no daemon, and nothing to provision.** The only long-running piece is an optional systemd timer (see [Services](#services-optional)), and it is off by default.

## What Gets Synced

| Item | Description |
|---|---|
| `settings.json` | Global settings, permissions, hooks config |
| `CLAUDE.md` | Global instructions for all projects |
| `agents/` | Subagent definitions |
| `commands/` | Custom slash commands |
| `hooks/` | Hook scripts referenced by settings.json |
| `rules/` | Global rules |
| `skills/` | Reusable skill definitions |

Everything else in `~/.claude/` (credentials, sessions, projects, cache, history, etc.) is machine-local and never synced.

## Prerequisites

| Tool | Needed for | Notes |
|---|---|---|
| `claude` | everything | `npm install -g @anthropic-ai/claude-code` |
| `jq` | hooks, log parsing | hooks read JSON on stdin |
| `yq` (v4) | model resolution, service config | workflows refuse to dispatch without it |
| `gh` | autonomous workflows | only needed if you run Workflow 2 |
| `git` | everything | |

`install.sh` checks for what it needs and fails loud rather than half-installing.


There are three ways to deploy depending on the machine type.

## Local (manual)

For first-time setup on any machine where you're working interactively.

```bash
# Clone and install
git clone https://github.com/helloskyy-io/Claude-Dot-Files.git ~/Repos/claude-dot-files
cd ~/Repos/claude-dot-files
./install.sh

# Global gitignore (prevents .claude/ worktrees from conflicting with parent repos)
echo ".claude/" >> ~/.gitignore_global && git config --global core.excludesFile ~/.gitignore_global

# Authenticate Claude Code (requires browser)
claude login

# Authenticate GitHub CLI (required for Workflow 2 autonomous PR creation)
gh auth login
```

The script will:
- Check that Claude Code and jq are installed (prompts you to install if missing)
- Check for Claude Code authentication (prompts you to run `claude login` if needed)
- Back up any existing config files in `~/.claude/`
- Create symlinks from `config/` into `~/.claude/`
- Verify all symlinks

**Note:** `gh` CLI is installed by the workstation bootstrap automation. For `gh auth login`, select: GitHub.com → SSH → your existing key → login with web browser.

## VMs (manual)

VMs typically don't have Claude Code or jq pre-installed. Install prerequisites first, then run the interactive installer.

```bash
# Define path
CLAUDE_PATH=/opt/skyy-net/claude-dot-files

# Install prerequisites (yq v4 is required by gh-monitor and workflow model resolution)
npm install -g @anthropic-ai/claude-code
sudo apt install -y jq
sudo wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 && sudo chmod +x /usr/local/bin/yq

# Clone and install
git clone https://github.com/helloskyy-io/Claude-Dot-Files.git $CLAUDE_PATH
cd $CLAUDE_PATH
./install.sh

# Global gitignore
echo ".claude/" >> ~/.gitignore_global && git config --global core.excludesFile ~/.gitignore_global

# Fix permissions for shared repos (root-owned, puma accesses via group)
sudo chmod -R g+rwX /opt/skyy-net/
sudo find /opt/skyy-net/ -type d -exec chmod g+s {} \;
for repo in /opt/skyy-net/*/; do
  if [ -d "$repo/.git" ]; then
    cd "$repo" && sudo git config core.sharedRepository group
  fi
done

# Authenticate Claude Code (requires browser)
claude login

# Authenticate GitHub CLI (if running autonomous workflows with PR creation)
gh auth login
```

**VM-specific notes:**
- Git repos under `/opt/skyy-net/` may be root-owned with group access. Set `core.sharedRepository group` so new git objects are group-writable. Without this, Claude's commits will fail on permission errors.
- Install `gh` CLI if you want to run autonomous workflows that create PRs from the VM.

## Managed workstations (Ansible)

For desktops and laptops managed by the [workstation-bootstrap](https://github.com/helloskyy-io) Ansible playbook.

The Ansible playbook handles:
1. Installing Claude Code and jq
2. Cloning this repo
3. Running `install.sh --non-interactive`

The `--non-interactive` flag skips all prompts and fails fast if prerequisites are missing. Authentication (`claude login`) is done manually after the playbook runs.

```bash
# What Ansible runs:
./install.sh --non-interactive
```

## Re-running the installer

The install script is idempotent — safe to run repeatedly. Existing correct symlinks are skipped, and any conflicting files are backed up before being replaced. Ansible runs it on every playbook execution.

## Updating

After pulling new changes, symlinks automatically point to the updated files. No need to re-run the installer.

```bash
cd ~/Repos/claude-dot-files
git pull  # symlinks pick up changes immediately
```

## Services (optional)

`gh-monitor` is a systemd **user** timer that polls GitHub for `@claude` PR comments. It is opt-in (`install.sh --with-services`) and currently **disabled** in `config.yaml` — the `@claude` comment path is not in use; PR disposition runs through `review-pr.sh` instead.

Two things about user timers that bite:

- **`loginctl enable-linger "$USER"` is non-negotiable.** Without it, user timers die when you log out and silently never run again. `install.sh --with-services` sets it idempotently.
- **A disabled service exits 0.** Config-disabled is a normal state, not a failure — a red unit trains you to ignore the alert. See `docs/standards/services.md`.

## Troubleshooting

**A workflow refuses to dispatch: "no model configured for `<key>`."** Working as designed — it will not run on an inherited default. Add the key to `config.yaml` under `models:`, or the script's `MODEL_KEY` does not match its config entry. `scripts/helpers/lint-prompts.sh` catches the mismatch before you hit it.

**Symlinks look right but changes do not take effect.** A running session holds the config it started with. Restart it.

**`.claude/` worktrees showing up as changes in an unrelated repo.** The global gitignore step was skipped — see the Local instructions above.

**Permission errors committing under `/opt/skyy-net/`.** Group-shared repos need `core.sharedRepository group`; see the VM notes above.

## What deployment does NOT cover yet

The fleet runs today as bash scripts invoked from a terminal on the machine that holds the repo. **There is nothing to deploy beyond the symlinks.**

A durable-execution topology — a Temporal server on a backed-up VM, worker processes on each machine holding repos, and the secrets handling that implies — is planned and **not built**. It is deliberately absent from this guide rather than sketched, because a deployment guide describing a deployment nobody can perform is worse than one that stops at the truth. See `docs/development/sprint.md § Phase: Temporal Integration` for the direction and `docs/development/skyy-net-seed-handoff.md` for the topology decision record.

## Related

- [`operations.md`](operations.md) — running the harness day to day
- [`workflows.md`](workflows.md) — workflow architecture
- [`../standards/services.md`](../standards/services.md) — conventions for anything long-running
- [`../development/sprint.md`](../development/sprint.md) — what is planned

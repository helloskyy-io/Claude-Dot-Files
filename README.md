# Claude Dot Files

Personal Claude Code configuration repo. Syncs selected items from `~/.claude/` across machines (workstations, laptops, and VMs) using targeted symlinks.

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

## Deployment

There are three ways to deploy depending on the machine type.

### 1. Local (manual)

For first-time setup on any machine where you're working interactively.

```bash
# Clone and install
git clone https://github.com/helloskyy-io/Claude-Dot-Files.git ~/Repos/claude-dot-files
cd ~/Repos/claude-dot-files
./install.sh

# Authenticate (requires browser)
claude login
```

The script will:
- Check that Claude Code and jq are installed (prompts you to install if missing)
- Check for Claude Code authentication (prompts you to run `claude login` if needed)
- Back up any existing config files in `~/.claude/`
- Create symlinks from `config/` into `~/.claude/`
- Verify all symlinks

### 2. VMs (manual)

VMs typically don't have Claude Code or jq pre-installed. Install prerequisites first, then run the interactive installer.

```bash
# Define path
CLAUDE_PATH=/opt/skyy-net/claude-dot-files

# Install prerequisites
npm install -g @anthropic-ai/claude-code
sudo apt install -y jq

# Clone and install
git clone https://github.com/helloskyy-io/Claude-Dot-Files.git $CLAUDE_PATH
cd $CLAUDE_PATH
./install.sh

# Authenticate (requires browser)
claude login
```

### 3. Managed workstations (Ansible)

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

## Re-running

The install script is idempotent — safe to run repeatedly. Existing correct symlinks are skipped, and any conflicting files are backed up before being replaced. Ansible runs it on every playbook execution.

## Updating

After pulling new changes, symlinks automatically point to the updated files. No need to re-run the installer.

```bash
cd ~/Repos/claude-dot-files
git pull  # symlinks pick up changes immediately
```

## Project Structure

```
claude-dot-files/
├── CLAUDE.md              ← project instructions (for working on this repo)
├── config/                ← source of truth for synced config
│   ├── settings.json
│   ├── CLAUDE.md
│   ├── agents/
│   ├── commands/
│   ├── hooks/
│   ├── rules/
│   └── skills/
├── install.sh             ← symlink installer (interactive + non-interactive)
├── docs/
│   └── development/
│       └── roadmap.md     ← phased migration plan
└── README.md
```

## License

[MIT](LICENSE)



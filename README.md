# Claude Dot Files

Personal Claude Code configuration repo. Syncs selected items from `~/.claude/` across machines (workstations, laptops, and VMs) using targeted symlinks.

## Operation

This repo is configured for two distinct workflows:

### Workflow 1: Interactive (minor changes, approve on the fly)

Your default day-to-day mode. You work with Claude in real-time, approving changes as they happen.

```bash
claude                         # start a session in the current directory
```

Use custom slash commands for common tasks:
- `/review` — run the code-reviewer agent on recent changes
- `/best-practices <topic>` — prime Claude with industry-standard approach
- `/create-claude` — generate CLAUDE.md files for a new project
- `/update-claude` — sync CLAUDE.md references to your standards
- `/update-file-structure` — update docs/file_structure.txt
- `/cleanup-merged-worktrees` — remove worktrees whose PRs have been merged or closed

### Workflow 2: Autonomous (plan → execute → PR)

Claude works independently on a planned task, creates a PR, and notifies you when done. Uses structured workflow scripts in `scripts/workflows/` or direct `claude -p` invocation.

```bash
# Minor revision — the lightweight autonomous workflow
./scripts/workflows/revision.sh "fix the null check in login()"
./scripts/workflows/revision.sh "add error handling" --pr 42

# Direct headless invocation (for ad-hoc tasks)
claude -p "implement feature X, write tests, create a PR" \
  --max-turns 50 \
  --dangerously-skip-permissions \
  -w feature-x
```

See `docs/official_documentation/dual_workflow_model.md` for the full architecture of how the two workflows fit together, including the escalation paths (PR review → PR comments → full re-run).

Safety mechanisms apply to both modes:
- **Permissions** — `settings.json` allow/deny lists for bash commands
- **PreToolUse hook** — `block-dangerous.sh` denies destructive patterns
- **Stop hook** — `notify-done.sh` fires a desktop notification when done

For detailed documentation on agents, rules, skills, and headless mode, see `docs/official_documentation/`.

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

# Authenticate Claude Code (requires browser)
claude login
```

VMs typically don't need `gh` CLI since autonomous runs with PR creation generally happen from workstations, not VMs. Skip `gh` setup unless you have a specific use case for it.

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

See [`docs/file_structure.txt`](docs/file_structure.txt) for the full annotated file tree.

## License

[MIT](LICENSE)

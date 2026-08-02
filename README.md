# Claude Dot Files

A self-improving Claude Code development environment. Custom agents, autonomous workflows, and a continuous process improvement loop — synced across all your machines.

**What makes this different from a basic dotfiles repo:**
- **Parent/child workflows** — the flagship pattern. A workflow that both writes code and rules on the review findings about it will defend its own work; no amount of prompt engineering fixes that. So the run that authors is no longer the run that judges: a parent script orchestrates two independent headless runs, and the second inherits nothing but git and the original task. See [Parent/Child Workflows](#parentchild-workflows-the-flagship-pattern)
- **14 custom agents** — architect, planner, code-reviewer, refactoring-evaluator, standards-auditor, standards-architect, security-auditor, quality-control, test-writer, doc-manager, workflow-analyst, plus the research family (research-analyst, research-critic, research-currency) — model-tiered per role, web-enabled where ground truth lives outside the repo
- **17 methodology skills** — planning, architecture decisions, decision-making (five-whys reframing), troubleshooting (hypothesis-driven debugging), testing (methodology, scaffolding, suite architecture), refactoring, standards (authoring, enforcement), documentation (structure, management), quality control, project definition and organization, workflow analysis and dispatch — load on-demand based on context
- **10 autonomous workflows** (plus 2 child steps) — bash scripts that run Claude headless in isolated git worktrees, review work through agent panels, and deliver PRs ready for human review — including a research family (create + refresh) producing source-verified evidence pools and a decide-only PR disposition engine that mechanizes the returned-PR review ritual
- **Verification over narrative** — every reviewing actor is bound to check claims against the artifact rather than the account of it. A PR body, a run's summary, a prior pass's prescription and an agent's finding are all *claims about* the code; none of them are the code
- **Git-native memory** — no state files, no bookmarks: *open* IS the to-do bit. Three surfaces carry it — PR threads (change-outcomes), Issues (no-change outcomes), and a standup tracker (continuity) — and `/standup` reads all three into a morning brief. See [the memory model](docs/guide/operations.md#the-memory-model)
- **Continuous process improvement** — `review-runs.sh` analyzes Claude's own workflow logs across repos; every finding lands in an append-only decisions log (`docs/development/cpi-decisions.md`) as ship/defer/reject with explicit watch-criteria. The system gets measurably smarter with use.
- **Cross-device sync** — targeted symlinks deploy everything to workstations, laptops, and VMs via a single `install.sh`

## Operation

> **The full operating manual is [`docs/guide/operations.md`](docs/guide/operations.md)** — the memory model, the daily loop, and a one-entry-per-item reference for every workflow, agent, command, skill, and rule. This section is the orientation; that document is what you actually work from.

This repo is configured for two distinct workflows:

### Workflow 1: Interactive (minor changes, approve on the fly)

Your default day-to-day mode. You work with Claude in real-time, approving changes as they happen.

```bash
claude                         # start a session in the current directory
/get-started                   # session primer: sets working roles, explains dual workflow model, establishes operating pattern
```

The two you'll use every day:
- `/get-started` — session primer: sets working roles, the dual-workflow model, and the operating pattern
- `/standup [--since <window>]` — read-only: reads the standup tracker (persistent operating state), then sweeps git memory surfaces (open PRs + their `pr_review:` verdicts, open issues, recent merges) into an attention brief

Eight more cover review, decisions, debugging, and doc maintenance — see [operations.md § Slash commands](docs/guide/operations.md#slash-commands).

### New Project Setup

Initialize a new project with standard scaffolding, then define it with AI planning:

```bash
# Initialize (pure bash, no AI, zero tokens)
~/Repos/claude-dot-files/scripts/helpers/init-project.sh "my-project" --org helloskyy-io

# Define the project (AI-powered, 14-stage planning workflow)
~/Repos/claude-dot-files/scripts/workflows/plan-new.sh "my-project" "description of the project" --verbose
```

### Workflow 2: Autonomous (plan → execute → PR)

Claude works independently on a planned task, creates a PR, and notifies you when done. Structured workflow scripts handle worktree isolation, agent invocation, logging, and PR creation.

```bash
# Minor revision — single pass, no review agents (5 stages: assess → implement → test → commit → PR)
./scripts/workflows/revision-minor.sh "fix the null check in login()"
./scripts/workflows/revision-minor.sh "add error handling" --pr 42

# Revision — PARENT: a DRAFT run writes the change, then a FRESH-context REFINE run judges it
./scripts/workflows/revision.sh "restructure the auth flow to use sessions"
./scripts/workflows/revision.sh "address all review findings" --pr 5

# PR disposition — decide-only: forces every surfaced item to a terminal ruling, ends in MERGE | HOLD
./scripts/workflows/pr-review.sh --pr 42

# Planning revision (7 stages: assess → plan → revise → architect review → planner review → resolve → PR)
./scripts/workflows/plan-revision.sh "add detailed phase doc for the auth feature"

# Build from a plan doc (9 stages: load plan → validate → implement → test → review → refactor → resolve → verify → PR)
./scripts/workflows/build-phase.sh docs/development/phases/phase-1.md "follow all standards" --verbose

# End-of-sprint review (6 stages: discover → parallel specialists → QC → build missing tests → synthesize → PR)
./scripts/workflows/sprint-review.sh --sprint "Sprint 1" --verbose

# CPI loop: analyze recent workflow logs, produce an improvement report
./scripts/workflows/review-runs.sh --days 21
```

Every run saves a JSONL log to `.claude/logs/` for self-diagnosis and continuous improvement analysis.

## Parent/Child Workflows (the flagship pattern)

**The problem: the author of a change defends it.** A single workflow that writes code and then rules on the review findings about it will dismiss findings rather than fix them — not from carelessness, but because the party weighing the finding is the party that chose the thing being questioned.

This was not fixable at the prompt level, and the attempt is documented: engineer self-review, four in-context review agents under an explicit fixed/rejected/deferred taxonomy, and manual verification. Defects survived all of it, then fell to a fresh-context pass costing a few dollars. Commitment bias needs a **process boundary**, not better wording.

So `revision.sh` is a **parent**: pure bash orchestration over two independent headless runs. It calls no model itself.

```
revision.sh  (parent — no model, no turn budget of its own)
  │
  ├─ 1. children/revision-draft.sh    200 turns   writes the change, opens an UNREVIEWED PR
  │        ↓  handoff = git + the original task
  ├─ 2. children/revision-refine.sh   200 turns   FRESH context: fidelity → review → resolve → verify
  │        ↓  handoff = git + the original task
  └─ 3. pr-review.sh                  120 turns   decide-only: MERGE, or HOLD + a runway
           ↳ HOLD(redispatch) → ONE loop-back, then stop. HOLD(needs-assistance) → stop now.
```

**Draft holds no review authority at all** — its review stages were deleted, not downgraded, and its checkpoint commit says so: `wip: implementation checkpoint — PRE-REVIEW, not yet audited`. A drafter that kept a *weakened* self-review would reproduce the same bias on a smaller budget.

**Refine opens on fidelity, not code review.** Its first instruction is *"You did NOT write this code. A different run did, in a context you do not share, and it is gone."* It must enumerate what the task asked for that is **present**, what is **missing**, and what was delivered that was **not asked for** — scope creep counts. A single context structurally cannot ask itself that question: it judges the result against the plan it already talked itself into.

**What crosses the boundary — nothing but git and the task.** Refine's inputs are the PR, its diff, its comments (the draft's self-reflection is posted as a comment), and **the original task, which the parent passes to both children**. That last part is load-bearing: without the task, refine can only ask *"is this code good?"* and never *"did this deliver what was asked?"* — and the second question is the one that catches missing scope.

**Failure semantics are explicit.** Draft fails → refine never runs. Refine fails → the parent says loudly that the PR exists and is **unreviewed**, and prints the command to re-run just the review half. A draft PR looks completely healthy on GitHub whether or not anything reviewed it.

### Why the parent is pure bash

Because that's where the work that *shouldn't* be probabilistic goes. The parent decides sequencing, enforces the handoff, and waits for CI to settle between the children — a real verification window, since pushing is the draft's terminal act and CI hasn't finished when it exits. Polling there costs wall-clock only; the same loop inside a model run would burn the reliability budget the split exists to protect.

The handoff mechanism turned out to be something already built for another reason. Each child declares a **completion contract** — an expected pattern its final output must contain, so that `exit 0` provably means *finished* rather than *stopped talking*. That contract, added to catch headless early-stop, doubles as the parent's interface: the parent reads a child's exit code plus the PR URL on its final line, and needs nothing else.

Deterministic control flow outside, non-deterministic work inside independent activities — the shape a durable-execution engine wants. **Composition already works in bash; Temporal would add durability, not composition.**

### What it catches in practice

Measured across the first cycles on real PRs, refine has caught things the authoring context structurally could not:

- **A security defect inside the seam being migrated** — a truncate-before-scrub ordering where slicing text before redaction leaves a secret fragment the scrub pattern no longer matches. Fixed at the seam rather than per-caller, which deleted a third open-coded copy of the same rule.
- **An overstated claim in the draft's own reflection** — the draft's evidence table was accurate but its generalization wasn't. Refine re-ran the experiment rather than accepting the conclusion, then corrected the record in the PR body and the tracking issue.
- **A test tier with no merge-path enforcement** — every CI workflow in the repo was path-filtered and none matched the tier, so 4127 tests had never gated a merge. Refine surfaced it and explicitly *refused to build the gate*, on the grounds that path filters and blocking posture affect every future PR and are the operator's call to scope.

Downstream of both children, `pr-review.sh` runs as a **decide-only** disposition engine — it never merges, fixes, or dispatches. It forces every surfaced item to a terminal ruling and verifies each pointer by fetching it, on the principle that **bias relocates rather than vanishes**: a run that didn't author the code still authored its own disposition table, and has an interest in that table looking complete.

Full architecture, sizing guidance, and escalation paths: [`docs/guide/workflows.md`](docs/guide/workflows.md). Decision history: [`docs/development/cpi-decisions.md`](docs/development/cpi-decisions.md).

## Services and safety

The `gh-monitor` systemd service (`scripts/services/`) watches open PRs for `@claude revision:` / `@claude revision-minor:` comments and dispatches the matching workflow automatically — PR feedback becomes rework without leaving GitHub. Currently disabled (`gh-monitor.enabled: false` in `config.yaml`) — the `@claude` comment path is not in use; PR disposition runs through `pr-review.sh` instead.

Safety mechanisms apply to both modes:
- **Permissions** — `settings.json` allow/deny lists for bash commands
- **PreToolUse hook** — `block-dangerous.sh` denies destructive patterns
- **Stop hook** — `notify-done.sh` fires a desktop notification when done

For detailed documentation on agents, rules, skills, and headless mode, see `docs/guide/`.

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

### 2. VMs (manual)

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

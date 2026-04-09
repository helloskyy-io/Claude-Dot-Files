# Claude Code Dotfiles — Migration & Setup Plan

## About This Repo

This is my personal Claude Code configuration repo. It syncs my `~/.claude/` config across: Ubuntu desktop workstation, travel laptop, and multiple remote VMs accessed via VS Code SSH remote extension. I work in a small team environment with some small and some large codebases. Team members will also be on Claude Max subscriptions, but likely not sharing my VMs

## My Setup

- **Subscription**: Claude Max (individual, $100/mo) — covers Claude Code usage
- **Auth**: `claude login` once per machine. CRITICAL: if `ANTHROPIC_API_KEY` is set as an env var anywhere, Claude Code will use API billing instead of Max. Check all machines.
- **Node.js**: Must be installed on each remote VM for Claude Code to run
- **Previous tooling**: Migrating from ChatGPT (browser) + Cursor (IDE) to Claude (browser) + Claude Code (terminal in VS Code)
- **Local AI hardware**: A6000 (48GB VRAM), RTX 4080 (16GB VRAM), several 8GB GPUs — for future local LLM offloading via Ollama

## Repo Structure

```
claude-dotfiles/
├── CLAUDE.md                    ← project instructions (read by Claude Code at session start)
├── config/                      ← source of truth for synced Claude Code config
│   ├── settings.json            ← global settings, permissions, hooks config
│   ├── CLAUDE.md                ← global instructions for all projects
│   ├── agents/                  ← subagent definitions
│   ├── commands/                ← custom slash commands (team playbooks)
│   ├── hooks/                   ← hook scripts referenced by settings.json
│   ├── rules/                   ← global rules
│   └── skills/                  ← reusable skill definitions
├── install.sh                   ← creates individual symlinks into ~/.claude/
├── docs/
│   ├── file_structure.txt       ← detailed file/symlink reference
│   └── development/
│       └── roadmap.md           ← this file
└── README.md                    ← repo documentation
```

## Sync Strategy Decisions

- **Sync method**: Targeted symlinks via bash `install.sh`, deployed manually, or by Ansible/automation. Each synced item gets its own symlink into `~/.claude/`. We chose targeted symlinks over GNU Stow (which mirrors entire directory trees). For automation, clone the repo and run `install.sh --non-interactive` on each machine, with Claude Code and jq installed as prerequisites.
- **What syncs** (7 symlinks): `settings.json`, `CLAUDE.md`, `agents/`, `commands/`, `hooks/`, `rules/`, `skills/`
- **What does NOT sync**: Everything else in `~/.claude/` — credentials, `projects/` (path-keyed), sessions, history, cache, telemetry, IDE state, etc. These are machine-local by nature.
- **Team config**: Project-level `.mcp.json` files are committed to each project repo with shared server definitions. Secrets are referenced via `${env:VAR_NAME}`. Each dev adds their own tokens in local scope (`~/.claude.json`).

## Per-Project Repo Structure (for reference, not in this repo)

Each codebase repo should have:
```
project-root/
├── CLAUDE.md                    ← project-specific rules, stack, run commands
├── .claude/
│   └── commands/                ← project-specific slash commands
├── .mcp.json                    ← shared MCP server config (committed)
└── docs/
    └── internal/standards/      ← existing docs, referenced via pointer rules
```

---

# Migration Plan — Phased Approach

Status key: `[ ]` not started · `[~]` in progress · `[x]` complete

## Two Workflows

This roadmap is organized around two distinct workflows that drive how we use Claude Code:

1. **Interactive** — Small, focused changes. You're in the loop, approving each step. Quick iterations, direct feedback. This is the default mode for day-to-day development.

2. **Autonomous** — Large, planned features. Claude works independently through a plan: implements, tests, refactors, then delivers a PR for review. You define the goal and review the output.

Everything in this roadmap serves one or both of these workflows.

---

## Phase 0: Explore ~/.claude ✅ COMPLETE

Mapped the directory structure. All folders exist but are empty (fresh install). Key discovery: `projects/` is path-keyed and should not be synced.

## Phase 1: Cross-Device Sync ✅ COMPLETE

Goal: Get this repo deploying to all machines so everything built in later phases automatically propagates.

- [x] **Finalize repo structure** — `config/` directory with synced items (settings.json, CLAUDE.md, agents/, commands/, hooks/, rules/, skills/)
- [x] **Write install.sh** — Idempotent script: checks prerequisites (Claude Code, auth, jq), backs up existing targets, creates individual symlinks from `config/*` into `~/.claude/`, verifies all links. Supports `--non-interactive` / `-n` flag for automation (skips interactive prompts, fails fast on missing prerequisites, skips auth check entirely).
- [x] **Create starter settings.json** — Minimal global settings to start with (can be expanded in later phases)
- [x] **Create global CLAUDE.md** — The `~/.claude/CLAUDE.md` that applies to ALL projects (coding style preferences, global rules, team conventions)
- [x] **Test on laptop** — install.sh runs clean, all 7 symlinks verified
- [x] **Deploy to workstation** — Clone repo, run install.sh, verify
- [x] **Ansible integration (workstations/laptops)** — install.sh runs via Ansible playbook with `--non-interactive` flag on desktops and laptops. Ansible handles cloning the repo and installing prerequisites (Claude Code, jq) before running the script.
- [x] **Deploy to VMs** — Tested on skyy-net VM at `/opt/skyy-net/claude-dot-files`, all 7 symlinks verified

### Phase 1 — Notes

**Workstations & laptops**: Ansible runs `install.sh --non-interactive` on every playbook run. This is safe because the script is idempotent (existing correct symlinks are skipped), and the script may do more than manage symlinks in the future.

**VMs**: Deployed manually with the standard interactive install.sh. Auth (`claude login`) must be done on each new machine — it requires a browser OAuth flow.

---

## Phase 2: Safety & Guardrails ✅ COMPLETE

**Serves: Both workflows** — Interactive mode needs guardrails so you can approve quickly with confidence. Autonomous mode needs them even more since Claude is working unsupervised.

Dependencies: Phase 1 (so hooks sync across machines automatically)

- [x] **PreToolUse hook: block dangerous commands** — `hooks/block-dangerous.sh` reads JSON from stdin, extracts the bash command, denies if it matches destructive patterns (rm -rf, force push, git reset --hard, DROP TABLE, dd, fork bombs, etc.). Wired in settings.json with matcher `"Bash"`.
- [x] **Stop hook: desktop notification** — `hooks/notify-done.sh` fires `notify-send` on Linux when Claude finishes. Gracefully skips on headless machines. Wired in settings.json Stop event.
- [x] **Review permissions in settings.json** — Permissions provide the first layer (approval popup for unlisted commands), hooks provide the second layer (pattern-based deny for dangerous commands that might match broad allow rules). Two-layer safety net confirmed working.
- [x] **Test each hook** — Permission layer prompts on dangerous commands (first safety layer works). notify-send fires desktop notification (top-right on Cinnamon/Mint). Both verified.

### Phase 2 — Hook Architecture

Hooks are defined in settings.json and reference scripts in `hooks/`:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "$HOME/.claude/hooks/block-dangerous.sh" }]
      }
    ],
    "Stop": [
      {
        "hooks": [{ "type": "command", "command": "$HOME/.claude/hooks/notify-done.sh" }]
      }
    ]
  }
}
```

Hook scripts receive JSON on stdin (NOT env vars). Read with: `INPUT=$(cat)` then parse with `jq`.

Three handler types available:
- **command**: shell scripts (most common, start here)
- **prompt**: sends a prompt to Claude for semantic evaluation
- **agent**: spawns a subagent with tool access for deep verification

### Phase 2 — Decision: Auto-Format Hook

Formatting on every Write/Edit eats context window. **Recommendation**: skip PostToolUse auto-format for now. Instead, rely on project-level formatting (prettier, black, etc.) that runs as part of the test/commit step in autonomous workflows. Revisit if formatting drift becomes a real problem.

---

## Phase 3: Planning & Agents ✅ COMPLETE

**Serves: Primarily Workflow 2 (Autonomous)** — These are the building blocks Claude uses to plan, review, and execute work independently. Also useful in interactive mode for getting a second opinion.

Dependencies: Phase 1 (for sync)

- [x] **architect agent** — `agents/architect.md`: read-only (Read, Grep, Glob), Opus model. Designs system architecture, evaluates trade-offs. On-demand only (built-in agents handle routine work).
- [x] **planner agent** — `agents/planner.md`: read-only (Read, Grep, Glob), Opus model. Creates detailed implementation plans with phased steps. On-demand only.
- [x] **code-reviewer agent** — `agents/code-reviewer.md`: read-only (Read, Grep, Glob), Sonnet model. Reviews code for bugs, performance, security, style. Reports findings with structured severity levels (Critical/Warning/Info). Tested on this repo.
- [x] **test-writer agent** — `agents/test-writer.md`: full access (Read, Grep, Glob, Edit, Write, Bash), Sonnet model. Generates tests matching project conventions and runs them to verify. Critical for autonomous workflow loops.
- [x] **security-auditor agent** — `agents/security-auditor.md`: read-only (Read, Grep, Glob), Sonnet model. OWASP-focused vulnerability detection with exploitation scenarios. Reports clean areas to prove coverage.
- [x] **Two-tier agent strategy** — Built-in agents handle routine tasks automatically. Custom agents are on-demand only for when depth is needed. Documented in `docs/official_documentation/claude_code_agents.md`.
- [x] **`/review` slash command** — `commands/review.md`: invokes code-reviewer agent on specified scope or recent changes.
- [x] **`/best-practices` slash command** — `commands/best-practices.md`: mindset primer for industry-standard approaches before tackling a problem.
- [ ] **Port Cursor workflows to slash commands** — Anything from old cursor_rules or repeated prompts becomes `commands/command-name.md`. Use `$ARGUMENTS` for parameterization.

### Phase 3 — Subagent Format

```yaml
---
name: code-reviewer
description: Reviews code for bugs, performance issues, and style violations
tools: ["Read", "Grep", "Glob"]
model: sonnet
---

You are a senior code reviewer. Analyze code for:
- Bugs and logic errors
- Performance issues
- Style violations against project standards
- Security concerns

Report findings as a structured list with severity (critical/warning/info).
Do not modify any files. Read-only analysis only.
```

Key constraints: Subagents cannot spawn other subagents. For multi-step workflows, chain subagents from the main conversation or use slash commands to orchestrate.

---

## Phase 4: Autonomous Execution

**Serves: Workflow 2 (Autonomous)** — This is the core of the "plan → execute → PR" pipeline.

Dependencies: Phase 2 (safety hooks), Phase 3 (planning agents)

### Orchestration Strategy

Seven ways to build agentic workflows, from simple to complex:

1. **Detailed single `claude -p` prompt** — cheapest, most fragile
2. **Bash scripts chaining multiple `claude -p` calls** — explicit, debuggable, portable ← **current choice**
3. **Claude Code Agent Teams** — native parallel coordination (experimental, GA coming soon)
4. **Ralph Wiggum style Stop hook loops** — simple iteration pattern, has known bugs as of 2026
5. **Claude Agent SDK (TypeScript/Python)** — production-grade, heavy
6. **Anthropic Managed Agents** — hosted orchestration service, public beta as of April 2026 (token usage + $0.08/session-hour)
7. **Third-party platforms (Paperclip, Ruflo, oh-my-claudecode)** — ecosystem choice, governance features

**Current direction:** Start with **bash script orchestration**. It's portable forward (can port to SDK later without losing logic), debuggable, and zero learning curve beyond what we already know.

**Don't over-invest.** Agent Teams is going GA and Anthropic Managed Agents is in public beta. Building elaborate bash orchestration that will be obsoleted by native solutions is wasted effort. Build only what you need *now*.

**Graduation triggers** — move beyond bash only if you hit real limitations:
- Error handling gets painful → consider Agent SDK
- Multi-project state management needed → consider Managed Agents or Paperclip
- Native parallel coordination needed → wait for Agent Teams GA
- Complex structured data processing → Agent SDK

**Critical warnings from research:**
- **Token burn is serious.** Autocompact at ~187K tokens costs 100-200K per cycle. Iterative refinement loops can trigger this 3+ times per turn.
- **Loop drift is real.** Agents re-run work redundantly — 40-60% of read tokens wasted in naive loops.
- **Sequential beats nested.** Running agents sequentially in a chain is more reliable than nested iteration loops.
- **Explicit exit criteria beat loop counts.** "Exit when tests pass" is better than "repeat 3 times."
- **Precision in the initial prompt beats iteration.** A well-specified prompt gets better results than a vague prompt iterated 10 times.

**Top 5 lessons from production use (April 2026):**
1. **Context management is the hardest problem** — implement summarization when approaching limits
2. **Over-specified CLAUDE.md backfires** — keep ruthlessly short or Claude ignores rules buried in noise
3. **Infinite exploration kills token budgets** — scope investigations narrowly, use subagents for exploration
4. **Trust-then-verify is essential** — Claude generates plausible but incomplete implementations
5. **Multi-agent workflows aren't for 95% of tasks** — set WIP limit at 3-5 agents max

### Phase 4a: Foundation Validation ✅ COMPLETE

Verify the primitives work end-to-end before building any orchestration.

- [x] **Test headless mode** — Tested `claude -p "/update-file-structure"` successfully. Slash commands work in headless mode.
- [x] **Install and auth `gh` CLI** — Installed via GitHub's apt repo, authed via SSH on both workstation and laptop (Yoga). Protocol: SSH. Account: Pumapumapumas.
- [x] **Test worktree mode** — Tested `-w test-worktree` flag. Claude Code auto-prefixes branch with `worktree-` (so `-w test-worktree` creates branch `worktree-test-worktree`). Worktree lives at `.claude/worktrees/<name>/`. Main working directory untouched during autonomous run.
- [x] **Test PR creation flow** — Full pipeline validated in one command: headless run → worktree created → edit → commit → push → `gh pr create`. PR #1 created successfully. Entire flow autonomous with `--dangerously-skip-permissions`.
- [x] **Establish dual permission model** — Interactive mode uses allow/deny lists (conservative, popup on new). Autonomous mode uses `--dangerously-skip-permissions` (permissive within isolated worktree). Safety comes from `block-dangerous.sh` hook which still fires regardless of permission flags. Hook hardened with expanded patterns (sudo, system control, RCE, SSH tampering, package purges, etc.). Verified empirically that hooks fire under `--dangerously-skip-permissions`.
- [x] **Build cleanup automation** — `/cleanup-merged-worktrees` command scans worktrees, checks PR status via `gh`, removes merged/closed ones. Tested and working.

### Phase 4b: Stage A — Initial Autonomous Run

Build the primary autonomous path: kick off `/plan-and-build`, get a PR back.

Aligned with the [Dual Workflow Model](../official_documentation/dual_workflow_model.md) — this is Stage A of Workflow 2.

- [x] **Document orchestration patterns** — `docs/official_documentation/claude_code_orchestration.md` covers the 7 approaches, coordinator/worker pattern, and the 5 production lessons.
- [x] **Document the dual workflow model** — `docs/official_documentation/dual_workflow_model.md` captures the architectural decision for how we use Claude Code.
- [ ] **Build `/plan-and-build` command or bash script** — Chains planner → architect → security-auditor → implement → test → PR. Single-pass, no iteration. May split into `/plan-feature` and `/implement-feature` for granular control.
- [ ] **Test on a real small feature** — Something low-risk in this repo or a test repo.
- [ ] **Measure token usage and output quality** — Track tokens per agent, evaluate output, document findings.
- [ ] **Identify gaps** — What did Claude miss? What did you have to correct? These become skills.

### Phase 4c: Stage C — PR Comments (GitHub Actions)

Build the minor fix escalation path: leave PR comments → Claude makes fixes → PR updates.

Aligned with the [Dual Workflow Model](../official_documentation/dual_workflow_model.md) — this is Stage C of Workflow 2.

- [ ] **Install Claude GitHub App** — `claude /install-github-app` to connect Claude to this repo and any others we want.
- [ ] **Create GitHub Actions workflow** — `.github/workflows/claude-pr-handler.yml` that triggers on `@claude` mentions in PR comments.
- [ ] **Document PR comment patterns** — How to write comments Claude can act on. Add to dual_workflow_model.md or a new doc.
- [ ] **Test the flow** — Create a test PR, leave a `@claude` comment, verify Claude pushes a fix to the same branch.

### Phase 4d: Stage D — Major Fix Path (Full Re-run)

Build the major fix escalation: when PR comments aren't enough, trigger a full re-run against the existing PR branch.

Aligned with the [Dual Workflow Model](../official_documentation/dual_workflow_model.md) — this is Stage D of Workflow 2.

- [ ] **Build `/fix-pr <PR#>` command** — Checks out the existing PR branch in a worktree, applies requested corrections, pushes updates back to the same branch.
- [ ] **Test on a real PR** — Create a PR, request major changes, verify the full re-run updates the PR correctly.

### Phase 4e: Foundational Skills (as we learn)

Build skills from experience, not upfront. Only after running real workflows.

- [ ] **Build 1-2 foundational skills** — Based on gaps identified in 4b. Start small. Don't build a library upfront.
- [ ] **Graduation evaluation** — Have we hit real bash limitations? Does Agent SDK or Managed Agents or Paperclip make sense? If not, stay where we are.

### Scheduled & Remote Triggers (deferred)

For tasks that should run on a schedule. Not a blocker for the autonomous pipeline.

- [ ] **Explore remote triggers** — `claude schedule` or the `/schedule` skill for cron-based autonomous runs.

---

## Phase 5: MCP Servers

**Serves: Both workflows** — Extends Claude's reach to external tools and APIs.

Dependencies: Phase 1 (for config sync)

- [ ] **Evaluate GitHub MCP need** — `gh` CLI already handles PR creation, simple operations, and saves context tokens. Only add GitHub MCP if we need complex operations (reading PR comments programmatically, triaging issues with structured data, cross-repo queries). Rule: `gh` CLI for high-frequency simple ops, MCP for complex structured queries.
- [ ] **Create .mcp.json template** — A starter project-level MCP config for team repos. Committed to git. Secrets via `${env:VAR_NAME}`.
- [ ] **Add 1–2 stack-specific servers** — Choose based on daily workflow. Candidates:
  - Playwright (browser testing)
  - Sentry (error monitoring)
  - PostgreSQL/Supabase (database access)
  - Linear/Jira (issue tracking)
  - Don't add everything at once — each server has a context cost.
- [ ] **Document team MCP setup** — Instructions for team members: how to add tokens locally, how to verify servers (`claude mcp list`)

### Phase 5 — MCP Scopes

- **User scope** (`~/.claude.json`): personal API keys, tokens. NOT synced by this repo (contains secrets).
- **Project scope** (`.mcp.json` in repo root): shared server definitions, committed to git. No secrets — use `${env:VAR_NAME}`.
- **Local scope** (default): only on current machine. Good for experimental servers.

Transport types: stdio (local process, most common), HTTP (remote/cloud services, recommended for new servers), SSE (deprecated — use HTTP).

### Phase 5 — MCP via Docker

MCP servers can run as Docker containers, which provides isolation and reproducibility. Useful for servers that have complex dependencies or need specific runtime environments. If using Docker Desktop, the MCP server runs inside a container and communicates via stdio or HTTP.

---

## Phase 6: Local AI Offloading (Future)

**Serves: Both workflows** — Preserves Claude subscription for complex thinking by offloading mechanical tasks to local GPU hardware.

Dependencies: Phase 5 (MCP knowledge — Ollama connects via MCP server)

NOTE: Ollama installation and GPU provisioning are handled by SkyyCommand, not this repo. This phase only covers the Claude Code integration side — MCP server config and delegation rules.

- [ ] **Add Ollama MCP server to Claude Code** — Use mcp-local-llm or similar MCP server pointing at SkyyCommand-managed Ollama instances. Claude becomes orchestrator, local models handle volume.
- [ ] **Add delegation rules to global CLAUDE.md** — "For summarization, classification, and initial drafts, use mcp__local-llm__* tools. For architecture decisions and complex logic, handle directly."
- [ ] **Test with A6000 instance** — Verify MCP connection to 32B model (Qwen 2.5 Coder) on A6000
- [ ] **Add RTX 4080 and smaller GPU endpoints** — 7B–14B models for fast linting, commit messages; 3B–7B for classification

### Phase 6 — Architecture

```
You (human) → Claude Code (orchestrator/thinker)
                  ├── MCP → Ollama on A6000 (32B model: drafts, summaries, boilerplate)
                  ├── MCP → Ollama on RTX 4080 (7B-14B: fast lint, commit msgs)
                  └── MCP → Ollama on 8GB GPUs (3B-7B: classify, simple processing)
                  (Ollama instances provisioned by SkyyCommand)
```

Claude reviews everything the local models produce. Local handles volume; Claude handles quality.

---

# Tools to Evaluate

These are worth investigating but not committed to the roadmap yet:

- **Paperclip** — UI overlay for Claude Code. Offers visual workflow design, agent management, parallel project tracking, and PR review. May overlap with native headless mode + triggers. Evaluate after Phase 4 to see what gaps remain.
- **Claude Agent SDK** — TypeScript/Python framework that powers Claude Code under the hood. Enables building custom agents for non-coding workflows. Worth exploring if we need automation beyond what Claude Code provides natively (e.g., custom CI pipelines, Slack bots, monitoring agents).

---

# Reference

## Key Commands

```bash
# Interactive mode
claude                        # Start Claude Code in current directory
claude --continue             # Resume previous session
claude --resume               # Same as --continue
/clear                        # Clear context between unrelated tasks

# Headless / Autonomous mode
claude -p "prompt"            # Run non-interactively, print result
claude -p "prompt" --headless # Headless mode (no TTY required)
claude -p "prompt" -w NAME    # Run in isolated worktree
claude -p "prompt" --max-turns 50  # Limit iterations for safety
claude -p "prompt" --output-format stream-json  # Structured output

# Management
/commands                     # List available slash commands
/agents                       # List/create subagents
claude mcp list               # Show connected MCP servers
claude mcp add <name>         # Add an MCP server
claude /install-github-app    # Connect Claude to GitHub repos
```

## File Hierarchy (what Claude Code reads)

1. `~/.claude/CLAUDE.md` — global rules (always read)
2. `~/.claude/settings.json` — global settings, hooks, permissions
3. `repo-root/CLAUDE.md` — project rules (read when in that repo)
4. `repo-root/.claude/` — project-level commands, settings
5. Subtree `CLAUDE.md` files — per-directory overrides within a repo

## Important Gotchas

- If `ANTHROPIC_API_KEY` env var is set, Claude Code uses API billing instead of Max subscription
- `~/.claude/projects/` is keyed by absolute path — do NOT sync across machines
- Hook scripts receive JSON on stdin, NOT via environment variables
- Subagents cannot spawn other subagents
- MCP servers have a context cost — don't add everything at once
- PostToolUse formatting hooks eat context if run on every edit — prefer formatting at commit time
- Conversation history and memory are machine-local — reinstalling Claude Code may wipe them
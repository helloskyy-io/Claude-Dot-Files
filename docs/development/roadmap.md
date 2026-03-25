# Claude Code Dotfiles — Migration & Setup Plan

## About This Repo

This is my personal Claude Code configuration repo. It syncs my `~/.claude/` config across: Ubuntu desktop workstation, travel laptop, and multiple remote VMs accessed via VS Code SSH remote extension. I work in a small team environment with some large codebases. Team members will also be on Claude Max subscriptions.

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

- **Sync method**: Targeted symlinks via bash `install.sh`, deployed by Ansible. Each synced item gets its own symlink into `~/.claude/`. We chose targeted symlinks over GNU Stow (which mirrors entire directory trees — awkward when `~/.claude/` has ~15 machine-local items we must not touch). Ansible clones the repo and runs `install.sh --non-interactive` on each machine, with Claude Code and jq installed as prerequisites in earlier playbook steps.
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

## Phase 2: Hooks — Safety and Consistency

Goal: Deterministic guardrails that Claude Code cannot ignore. Unlike CLAUDE.md instructions (suggestions), hooks are guaranteed to execute.

Dependencies: Phase 1 (so hooks sync across machines automatically)

- [ ] **PreToolUse: block dangerous commands** — Hook script that reads JSON from stdin, extracts the bash command, denies if it matches destructive patterns (rm -rf, force push, etc.). Returns `permissionDecision: "deny"` with reason.
- [ ] **PostToolUse: auto-format on edit** — Runs team formatter (prettier, black, etc.) after Write/Edit tool calls. NOTE: formatting on every edit eats context window. Consider formatting on Stop (commit time) instead.
- [ ] **Stop: desktop notification** — `notify-send` on Linux so you know when Claude finishes a long task.
- [ ] **Configure in settings.json** — Wire all hooks into the hooks config with proper matchers (e.g., PreToolUse matcher: "Bash", PostToolUse matcher: "Write|Edit")
- [ ] **Test each hook** — Verify blocking works, formatting triggers, notifications fire

### Phase 2 — Hook Architecture

Hooks are defined in settings.json and reference scripts in hooks/:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "$HOME/.claude/hooks/block-dangerous.sh" }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{ "type": "command", "command": "$HOME/.claude/hooks/auto-format.sh" }]
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

## Phase 3: MCP Servers — Extend the Reach

Goal: Connect Claude Code to external tools, databases, and APIs.

Dependencies: Phase 1 (for user-level config sync), Phase 2 helpful but not required

- [ ] **Add GitHub MCP** — `claude mcp add github --scope user`. Highest-value single MCP server: PR workflows, issue management, repo operations.
- [ ] **Create .mcp.json template** — A starter project-level MCP config that team members can use. Committed to project repos. Secrets via `${env:VAR_NAME}`.
- [ ] **Add 1–2 stack-specific servers** — Choose based on daily workflow: Playwright (browser testing), Sentry (error monitoring), PostgreSQL/Supabase (database), Figma (design). Don't add everything at once — each server has a context cost.
- [ ] **Document team MCP setup** — Write instructions for team members: how to add their tokens locally, how to verify servers are connected (`claude mcp list`)

### Phase 3 — MCP Scopes

- **User scope** (`~/.claude.json`): personal API keys, tokens. Syncs via dotfiles but consider encryption.
- **Project scope** (`.mcp.json` in repo root): shared server definitions, committed to git. No secrets here.
- **Local scope** (default): only on current machine. Good for experimental servers.

Three transport types: stdio (local process, most common), HTTP (remote cloud services, recommended), SSE (deprecated, use HTTP).

## Phase 4: Subagents and Slash Commands

Goal: Reusable specialists and team playbooks.

Dependencies: Phase 1 (for sync), understanding of tool restrictions

- [ ] **Create code-reviewer subagent** — `agents/code-reviewer.md`: read-only tools (Read, Grep, Glob), reviews code without modifying anything
- [ ] **Create test-writer subagent** — `agents/test-writer.md`: full tool access, focused on generating tests for existing code
- [ ] **Create docs-generator subagent** — `agents/docs-generator.md`: Read + Write tools, generates documentation
- [ ] **Port Cursor workflows to slash commands** — Anything from cursor_rules or repeated prompts becomes `commands/command-name.md`. Use `$ARGUMENTS` for parameterization.
- [ ] **Create /new-endpoint command** — Team playbook for creating API endpoints following standards
- [ ] **Test delegation flow** — Practice: "use the code-reviewer subagent to review X" → subagent works in isolation → results return

### Phase 4 — Subagent Format

```yaml
---
name: code-reviewer
description: Reviews code for bugs, performance issues, and style violations
tools: Read, Grep, Glob
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

Subagents cannot spawn other subagents. For nested workflows, chain subagents from the main conversation.

## Phase 5: Ralph Wiggum Loop

Goal: Autonomous iterative development — Claude works on a task until verified complete.

Dependencies: Phase 2 (hooks — Ralph IS a Stop hook) + Phase 4 (slash commands)

- [ ] **Install the official ralph-wiggum plugin** — Available in Anthropic's plugin marketplace
- [ ] **Run a small test task** — `/ralph-loop "migrate tests from X to Y" --max-iterations 10 --completion-promise "DONE"`
- [ ] **Write verification-first prompts** — TDD approach: define tests first, loop runs tests → implements → reruns until green
- [ ] **Watch first 2–3 iterations** — Build intuition for how the loop works before going AFK
- [ ] **Customize your own version** — Fork the Stop hook behavior, add logging, integrate with notification hooks

### Phase 5 — How Ralph Works Under the Hood

1. You invoke: `/ralph-loop "task description" --max-iterations 20 --completion-promise "DONE"`
2. Claude works on the task
3. Claude tries to exit (Stop event fires)
4. Stop hook intercepts, checks if completion promise was output
5. If no promise found AND iterations < max: re-injects the original prompt
6. Claude sees its own previous file changes and git history, continues iterating
7. Loop ends when: promise is output, max iterations reached, or you cancel

Key philosophy: "Deterministically bad means failures are predictable and informative. Success depends on writing good prompts, not just having a good model."

Always set --max-iterations as primary safety mechanism. The --completion-promise uses exact string matching.

## Phase 6: Agent Teams (Experimental)

Goal: Multiple Claude Code sessions working in parallel with direct communication.

Dependencies: Phase 4 (subagents) + comfort with single-agent workflow

- [ ] **Enable Agent Teams** — `{ "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" } }` in settings
- [ ] **Try on a parallelizable task** — 3+ independent features, multi-module refactor, parallel test coverage
- [ ] **Learn coordination model** — Team lead assigns, teammates work independently, can message each other directly. Use Shift+Down to cycle between teammates.

### Phase 6 — When to Use What

- **Subagents**: workers that report back to you. Good for focused, isolated tasks. Low overhead.
- **Agent Teams**: workers that talk to each other. Good for tasks requiring coordination. 3–5x faster wall-clock time but proportionally more tokens.
- **Rule of thumb**: If workers don't need to communicate → subagents. If they need to share findings and coordinate → Agent Teams.

## Phase 7: Local AI Offloading (Future)

Goal: Use local GPU hardware to handle mechanical tasks, preserving Claude subscription for complex thinking.

Dependencies: Phase 3 (MCP knowledge — Ollama connects via MCP server)

NOTE: Ollama installation and GPU provisioning are handled by SkyyCommand, not this repo. This phase only covers the Claude Code integration side — MCP server config and delegation rules.

- [ ] **Add Ollama MCP server to Claude Code** — Use mcp-local-llm or OllamaClaude MCP server pointing at SkyyCommand-managed Ollama instances. Claude becomes orchestrator, local models handle volume.
- [ ] **Add delegation rules to global CLAUDE.md** — "For summarization, classification, and initial drafts, use mcp__local-llm__* tools. For architecture decisions and complex logic, handle directly."
- [ ] **Test with A6000 instance** — Verify MCP connection to 32B model (Qwen 2.5 Coder) on A6000
- [ ] **Add RTX 4080 and smaller GPU endpoints** — 7B–14B models for fast linting, commit messages; 3B–7B for classification

### Phase 7 — Architecture

```
You (human) → Claude Code (orchestrator/thinker)
                  ├── MCP → Ollama on A6000 (32B model: drafts, summaries, boilerplate)
                  ├── MCP → Ollama on RTX 4080 (7B-14B: fast lint, commit msgs)
                  └── MCP → Ollama on 8GB GPUs (3B-7B: classify, simple processing)
                  (Ollama instances provisioned by SkyyCommand)
```

Claude reviews everything the local models produce. Local handles volume; Claude handles quality.

---

# Reference

## Key Commands

```bash
claude                    # Start Claude Code in current directory
claude --continue         # Resume previous session
claude --resume           # Same as --continue
/clear                    # Clear context between unrelated tasks
/commands                 # List available slash commands
/agents                   # List/create subagents
claude mcp list           # Show connected MCP servers
claude mcp add <name>     # Add an MCP server
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
- PostToolUse formatting hooks eat context if run on every edit — prefer formatting on Stop/commit
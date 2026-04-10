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
- [x] **Two-tier agent strategy** — Built-in agents handle routine tasks automatically. Custom agents are on-demand only for when depth is needed. Documented in `docs/guide/claude_code_agents.md`.
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

### Phase 4b: Standards Documentation ✅ COMPLETE

Before building more workflows, capture the conventions we've been following so future additions stay consistent and team members can contribute.

- [x] **Agent standards** — `docs/standards/agents.md`: frontmatter schema, tool restrictions, on-demand vs proactive, two-tier strategy, role vs methodology separation.
- [x] **Hook script standards** — `docs/standards/hook-scripts.md`: JSON stdin patterns, jq output (no string interpolation), regex vs fixed-string pattern arrays, testing patterns, integration with settings.json.
- [x] **Skill standards** — `docs/standards/skills.md`: description field criticality, layering with project standards (global HOW, project WHAT), build-from-experience principle, one-topic-per-skill rule.
- [x] **Slash command standards** — `docs/standards/slash-commands.md`: plain markdown (no frontmatter), `$ARGUMENTS` patterns, agent invocation, safety conventions, commands vs agents vs skills decision guide.
- [x] **Reference standards from CLAUDE.md** — Root `CLAUDE.md` Standards section points to all four. Global `config/CLAUDE.md` intentionally does NOT reference (it syncs to all projects and those paths wouldn't exist elsewhere).

### Phase 4c: Core Workflows (The Four Autonomous Workflows)

Aligned with the [Dual Workflow Model](../guide/dual_workflow_model.md) — these are the four concrete workflows that collectively implement Stage A (Initial Autonomous Run). They vary by scope: from trivial revisions to full project definition.

#### revision workflow — Minor Corrections ✅ COMPLETE

Lightweight workflow for small, bounded fixes to existing code. Daily utility. Implemented as `scripts/workflows/revision.sh`.

- [x] **Build `scripts/workflows/revision.sh`** — Structured 5-stage single-session workflow (assess → implement → test → commit → push → PR). Supports new branch mode and update-existing-PR mode via `--pr` flag.
- [x] **Environment checks and safety** — Validates claude/gh/git availability, runs from repo root, timestamped worktree names, 30 max turns, `--dangerously-skip-permissions` for autonomous execution.
- [x] **Real-world validation** — Used the revision workflow itself to generate the initial testing skill (meta-validation). PR created, reviewed, merged, content evaluated. The workflow works.
- [x] **Visibility infrastructure** — `--verbose` flag streams formatted output live, raw JSONL log saved to `.claude/logs/` for self-diagnosis.
- [x] **Document in README** — Operation section shows usage examples.

#### revision-major workflow — Significant Rework ✅ COMPLETE

Heavy workflow for substantial corrections: when the AI went off the rails, requirements were incomplete, stack choice was poor, or architectural changes are needed. Implemented as `scripts/workflows/revision-major.sh`.

- [x] **Build `scripts/workflows/revision-major.sh`** — 9-stage workflow: assess → plan → implement → test → code review (via code-reviewer agent) → refactoring evaluation (via refactoring-evaluator agent) → resolve (decide what to apply) → verify (final test pass) → submit PR. 75 max turns. Supports new branch and existing PR update via `--pr` flag.
- [x] **Build refactoring-methodology skill** — `config/skills/refactoring-methodology.md`: when to refactor vs leave alone, evaluating suggestions (accept/reject/defer), safe refactoring patterns, the three-line rule, measuring impact.
- [x] **Build refactoring-evaluator agent** — `config/agents/refactoring-evaluator.md`: read-only Sonnet agent for structural improvement evaluation. Distinct from code-reviewer (correctness vs structure).
- [x] **Trim planner agent** — 212 → 45 lines (79% reduction). Methodology extracted to skills. Agent is now a lean role definition.
- [x] **Trim architect agent** — 212 → 50 lines (76% reduction). Same pattern — lean role, skills carry the depth.
- [x] **Add `skills:` preloading to all agents** — Critical fix: subagents don't auto-load skills. Added `skills:` frontmatter to all 6 agents so methodology is injected at startup. Verified via Anthropic docs. Evaluated edge cases — current skill assignments are correct, no additions needed.
- [x] **Test on a real task** — Ran revision-major on "build Phase 5 agent and skill." Results: all 9 stages followed correctly, 44 turns, $1.68 (API-equivalent), 7m 19s. Produced workflow-analyst agent and workflow-analysis skill. PR #5 created with comprehensive review/refactor documentation.
- [x] **Self-evaluation via logs** — Claude analyzed the run's JSONL log. Found ~35% redundant reads (same files re-read 4x across stages). Applied fix: added "do not re-read files already known" rule to both revision.sh and revision-major.sh. Estimated savings: ~$0.40/run, ~9 turns.
- [x] **New agent and skill from the test** — `workflow-analyst` agent (read-only, Sonnet, preloads workflow-analysis skill) and `workflow-analysis` skill (pattern categories, confidence scoring, report format) created by the autonomous workflow itself. Validates that the workflow can produce production-quality agents and skills.

#### build-phase workflow — Architect & Build ✅ COMPLETE

Main autonomous path. Takes a plan document path as input and implements what it describes. 9-stage workflow with deviation tracking and success criteria verification. Implemented as `scripts/workflows/build-phase.sh`.

- [x] **Build `scripts/workflows/build-phase.sh`** — 9-stage workflow: load plan → validate → implement → test → code review (code-reviewer agent) → refactoring evaluation (refactoring-evaluator agent) → resolve → verify (tests + success criteria) → submit PR with deviation summary. 150 max turns. Built by revision-major.sh (PR #7).
- [x] **Plan-driven input** — Takes a plan document path, not free-text. Extracts scope and success criteria from the plan, verifies against them at the end. Path validation with sanitization regex for heredoc injection prevention.
- [x] **Shared prompt extraction** — Stages 1-8 and Rules extracted into shell variables, eliminating ~80 lines of duplication between new-branch and existing-PR paths.
- [x] **Shared lib integration** — Updated to source `lib/run-claude.sh` (PR #9), matching the pattern of all other workflow scripts.
- [ ] **Add optional context argument** — Second positional arg after plan path for injecting additional instructions (e.g., "follow all standards in /docs/standards/"). In progress (PR pending).
- [x] **Single-pass architecture** — Starting with single-session. Will refactor to multi-stage if context bloats on large builds.
- [ ] **Test on a real phase** — First real test running now (Phase 4d GitHub Actions plan). Evaluate output quality and token usage.

#### Shared Workflow Infrastructure ✅ COMPLETE

- [x] **Extract `run_claude` to shared lib** — `scripts/workflows/lib/run-claude.sh` sourced by all 4 workflow scripts. Expects LOG_FILE, MAX_TURNS, VERBOSE, FORMATTER as environment variables with guards. Eliminates ~75 lines of duplication (PR #8).
- [x] **Stream formatter** — `scripts/workflows/lib/format-stream.sh` for live verbose output. Color-coded, handles tool calls, agent spawns, thinking indicators, cost/turn summary.

#### define-project workflow — Research & Planning (TODO)

Heaviest workflow. For new projects or major features — produces the foundation documents that prevent drift and disappointment later. Will be implemented as `scripts/workflows/define-project.sh`.

- [ ] **Build `scripts/workflows/define-project.sh`** — Structured workflow: requirements gathering → initial roadmap → tech stack selection → phased approach breakdown → epic definition per phase → dependency identification → security audit → detailed roadmap revision → PR with summary.
- [x] **Supporting skills already built** — Planning methodology, architecture decisions, project definition, and documentation structure skills all exist. No new skills needed.
- [ ] **Test on a real project** — Define a real small project from scratch, evaluate output quality.

### Phase 4d: PR Comment Automation (Local GitHub Monitor) — REDESIGNED

The Stage C escalation path. A local systemd timer (`gh-monitor`) polls GitHub for `@claude` PR comments and launches workflows locally using Max subscription. Zero API costs, zero security exposure.

**Redesign rationale (2026-04-10):** Original GitHub Actions approach (PR #10, closed) was abandoned because: (1) Actions runners require Claude API billing, not Max subscription; (2) security exposure on a Tailscale-hardened workstation is unacceptable; (3) local polling achieves the same UX at zero additional cost.

Plan document: `docs/development/phases/phase-4d-github-actions-integration.md`
Service standard: `docs/standards/services.md`

- [ ] **Build `scripts/services/gh-monitor.sh`** — Bash poller using `gh` CLI. No Claude invocation for polling (zero tokens). Routes `@claude` comments to revision.sh, revision-major.sh, or help response. Posts clarifying comment when context is insufficient.
- [ ] **Configuration** — `gh-monitor.config.env` with documented variables: repos to monitor, concurrency limits, route enablement, dry run mode, backlog limits.
- [ ] **Reaction-based deduplication** — 👀 (processing), ✅ (done), ❌ (failed), 💬 (clarification needed). First reactor wins (multi-machine safe).
- [ ] **Systemd integration** — `gh-monitor.service` (oneshot) + `gh-monitor.timer` (5 min, Persistent=true). Survives reboots, catches up on backlog.
- [ ] **Update install.sh** — Add `--with-services` flag for opt-in service deployment.
- [ ] **Test the flow** — Dry run first, then real test: post `@claude fix X` on a PR, verify poller picks it up and pushes a fix.

### Phase 4e: Skills Library (ongoing, built from experience)

Build skills incrementally based on what workflows need. Not a one-time phase — this is continuous.

**Testing skills:**
- [x] **Testing methodology skill** — `config/skills/testing-methodology.md`: how to think about testing (principles, scoping, discovery, red flags, fixing failures). Activates during daily test work.
- [x] **Testing scaffolding skill** — `config/skills/testing-scaffolding.md`: how to set up test infrastructure in new projects. Narrow trigger, activates rarely.

**Documentation skills:**
- [x] **Documentation structure skill** — `config/skills/documentation-structure.md`: foundation skill defining four-bucket layout (architecture/development/standards/guide), document templates (ADR, phase, standards, guide), file naming conventions, cross-references, file_structure.txt maintenance. Other skills reference this for document placement and format.
- [x] **Rename `official_documentation/` → `guide/`** — Following the four-bucket convention. All references updated across 9 files.
- [x] **Establish `docs/architecture/`** — Empty directory with README explaining purpose and when to write ADRs.

**Planning skills:**
- [x] **Planning methodology skill** — `config/skills/planning-methodology.md`: how to plan features, break down work, identify dependencies and risks. Most frequently activated planning skill. Covers when to plan vs when to just start, the 7-stage planning process, task templates, dependency mapping, risk identification, success criteria, and phase-level work organization.
- [x] **Architecture decisions skill** — `config/skills/architecture-decisions.md`: when to write an ADR, reversibility spectrum (two-way/medium/one-way doors), trade-off analysis methodology, research process, and red flags. Moderate activation (when making design choices within existing projects).
- [x] **Project definition skill** — `config/skills/project-definition.md`: 11-stage process for defining a new project from scratch — requirements gathering, stakeholders & success criteria, tech stack selection, high-level architecture, phase breakdown, epic identification, dependency mapping, initial security review, roadmap, documentation layout, CLAUDE.md setup. Scales from very small (<2 weeks) to large (1+ years) projects. Rare activation (only for greenfield projects via `define-project.sh`).

**Refactoring skills:**
- [x] **Refactoring methodology skill** — `config/skills/refactoring-methodology.md`: when to refactor vs leave alone, evaluating suggestions (accept/reject/defer), safe refactoring patterns, dangerous patterns, measuring impact. Pairs with refactoring-evaluator agent.

**Other skills (build as gaps emerge):**
- [ ] **Code review methodology skill** — Beyond the existing code-reviewer agent, detailed review criteria and severity definitions.
- [ ] **Additional skills as gaps emerge** — Driven by real workflow failures and corrections.

**Agent review:**
- [x] **Trimmed planner agent** — 212 → 45 lines. Methodology extracted to planning-methodology skill. Agent is lean role definition referencing the skill.
- [x] **Trimmed architect agent** — 212 → 50 lines. Same pattern. References architecture-decisions skill.
- [x] **Built refactoring-evaluator agent** — New read-only Sonnet agent for structural evaluation. Distinct from code-reviewer (correctness vs structure).

### Phase 4f: Graduation Evaluation (deferred)

Only relevant once workflows 4c are all built and tested in production use, and we've run the continuous improvement loop for several cycles.

- [ ] **Evaluate bash limits** — Have we hit real limitations (error handling, state, structured data, team scale)?
- [ ] **Evaluate Agent SDK** — If bash is hitting limits, consider Python/TypeScript SDK.
- [ ] **Evaluate Anthropic Managed Agents** — Public beta option for hosted orchestration.
- [ ] **Evaluate Paperclip** — Criteria: does it reuse existing agent assets? Can workflows be done with raw `claude -p`? Is config portable?

### Scheduled & Remote Triggers (deferred)

For tasks that should run on a schedule. Not a blocker for the autonomous pipeline.

- [ ] **Explore remote triggers** — `claude schedule` or the `/schedule` skill for cron-based autonomous runs.

---

## Phase 5: Continuous Process Improvement

**The game-changer phase.** This phase elevates the dotfiles repo from "static configuration" to a **self-improving development environment**. By analyzing logs from real workflow runs, we identify patterns, inefficiencies, and improvements — then feed those back into the system. The result is a true continuous-improvement feedback loop where the development environment gets smarter over time based on actual usage.

This phase deserves its own top-level designation because:
- It's a **meta-workflow** that operates on other workflows
- It transforms the entire system from "manually maintained" to "self-calibrating with human oversight"
- It compounds over time — every cycle makes future cycles more valuable
- It has its own architecture, prerequisites, and graduation path
- It's the foundation for everything that comes after (including SkyyCommand AI integration)

### Phase 5a: Review Workflow (manual mode)

Build the core workflow that analyzes recent logs and produces actionable recommendations.

**Prerequisites (updated 2026-04-10):**
- ~~Phase 4c complete (at least `revision.sh` + `build-phase.sh` built)~~ → ✅ All 4 core workflows built: revision.sh, revision-major.sh, build-phase.sh, review-runs.sh.
- ~20+ workflow runs logged in `.claude/logs/` for meaningful PATTERN analysis. **Note:** We have ~8-10 logs from today's session alone. Growing rapidly as we use workflows to build workflows.
- ~~Phase 4e: some foundational skills exist~~ → ✅ 8 skills exist

**Early wins (ahead of schedule):**
- [x] **`workflow-analyst` agent built** — Created by revision-major's first real test run (PR #5). Read-only Sonnet agent with structured report format, confidence scoring, and metrics. Preloads workflow-analysis skill.
- [x] **`workflow-analysis` skill built** — Created alongside the agent. Covers pattern categories (inefficiencies, repeated failures, manual corrections, missed opportunities, successes), confidence scoring methodology, analysis process, red flags, and output format.
- [x] **Manual self-evaluation proven** — First real test: Claude analyzed revision-major's JSONL log and identified ~35% redundant reads ($0.40/run savings). Fix applied to both workflows. The CPI loop works even without `review-runs.sh` formalized.
- [x] **First empirical data point** — revision-major run: 44 turns, $1.68, 7m19s, 64 tool calls, all 9 stages followed. Baseline established for future comparison.

**Why this matters:**
- **Real data, not speculation** — improvements come from actual usage patterns
- **Self-calibrating** — adapts as work patterns change
- **Catches drift** — notices when workflows gradually degrade
- **Surfaces hidden wins** — "Claude keeps making this manual correction, bake it into the prompt"
- **Compounds over time** — each cycle makes the next one better

**Design:**

```
Daily workflows run → logs accumulate in .claude/logs/
  ↓
Review workflow runs (manual or via workflow-analyst agent)
  ↓
Claude reads recent logs, looks for patterns
  ↓
Produces report with findings and recommendations
  ↓
You review and decide what to apply
  ↓
Next runs use improved versions
```

**Remaining tasks:**

- [x] **Build `scripts/workflows/review-runs.sh`** — Built by revision-major.sh (PR #6). Scans `.claude/logs/` for JSONL logs, configurable via `--days N` or `--last N` (mutually exclusive, validated). Produces structured report at `docs/development/reviews/review-YYYY-MM-DD.md`. Smart MAIN_REPO_ROOT resolution for worktree compatibility. No worktree isolation (read-only analysis). 30 max turns.
- [ ] **Run first formal cross-run analysis** — Once we have ~20 runs, invoke `review-runs.sh` and evaluate if cross-run pattern analysis adds value beyond single-run analysis.
- [ ] **Capture findings into workflow improvements** — First formal cycle: apply highest-confidence recommendations, observe quality improvement on next runs.

### Phase 5b: Automated PR Generation

Take the manual review workflow and have it create PRs with proposed changes.

**Tasks:**

- [ ] **Extend review-runs.sh to optionally create a PR** — Instead of just a markdown report, the workflow can open a PR with proposed changes to workflow scripts, agents, prompts, or skills. Always requires human review.
- [ ] **Design the PR template** — Each PR includes: which logs were analyzed, what patterns were found, confidence scores, before/after diffs, and recommended testing approach.
- [ ] **Test the PR creation flow** — Run it on real findings, verify the PR is reviewable and the changes are sensible.

### Phase 5c: Scheduled Operation

Move from manual triggering to scheduled operation.

**Tasks:**

- [ ] **Schedule weekly review runs** — Use `claude schedule` to run the review workflow every Monday morning. Reports arrive automatically.
- [ ] **Schedule automated PR generation** — After scheduled reports prove useful, escalate to scheduled PRs with proposed changes.
- [ ] **Tune the analysis window** — Find the right balance between recency (responsive to recent work) and sample size (statistical relevance). Likely 7-14 days.
- [ ] **Add notification on completion** — Hook into the existing Stop hook pattern so you know when the weekly report is ready.

### Phase 5d: Pattern Library and Skills

The continuous improvement loop generates insights that should be captured systematically. As patterns emerge consistently across multiple cycles, they should become permanent parts of the system.

**Tasks:**

- [x] **Build a "workflow analysis" skill** — `config/skills/workflow-analysis.md`: pattern categories, confidence scoring, analysis process, red flags. Built ahead of schedule by the revision-major test run (PR #5).
- [ ] **Build a "continuous improvement methodology" skill** — Capture the patterns we learn about what makes workflows good vs bad. This becomes the institutional knowledge of "what we learned about Claude Code workflows." Distinct from workflow-analysis (which is about log reading) — this is about the meta-process of improving the system.
- [ ] **Track resolved patterns** — Maintain a log of patterns identified and resolved so we don't re-litigate them. Location: `docs/development/reviews/resolved-patterns.md`.
- [ ] **Pattern → skill pipeline** — When the same recommendation appears across multiple review cycles, automatically suggest promoting it to a permanent skill.

### Phase 5e: Advanced Self-Improvement (future, careful)

This is where we approach true self-improvement, but with significant guardrails. Only build this once we have months of stable operation and high-confidence patterns.

**Tasks:**

- [ ] **Build automated skill capture** — When a pattern is identified consistently across multiple review cycles with high confidence, auto-add it to skills (still gated by human PR approval).
- [ ] **Cross-workflow analysis** — Compare patterns across different workflow types. Are there common improvements that apply to all?
- [ ] **Effectiveness tracking** — Measure if the recommended changes actually improved subsequent runs. Did the change reduce token usage? Decrease turn count? Improve output quality?
- [ ] **Regression detection** — Notice when changes made changes things WORSE. Alert on degradations.

### Critical Rules (Apply to All of Phase 5)

These rules are non-negotiable for the entire continuous improvement system:

1. **Never auto-apply changes** — All modifications require human review and approval via PR
2. **Human is always the decision-maker** — The AI suggests, the human decides
3. **Explicit audit trail** — Every change should be traceable back to the patterns that motivated it
4. **Reversible** — All changes must be reversible. No one-way doors.
5. **Confidence scoring** — Recommendations must include how confident the analysis is, so you can prioritize what to act on
6. **Sample size matters** — Don't act on patterns from single runs. Require multiple observations before recommending changes
7. **Cost awareness** — The continuous improvement loop should not cost more in tokens than it saves in workflow improvements

### Why This Is Game-Changing

Traditional development:
```
Write workflow → ship → hope it works → manually iterate when issues surface → ship again
```

What Phase 5 unlocks:
```
Write workflow → run it → AI analyzes runs → surfaces specific improvements → 
human reviews → better workflow → loop
```

The killer feature isn't that Claude can analyze logs. It's that the analysis is **precise enough to act on without a human having to read the logs first**. That's the breakthrough. Insights that would take a human 10-15 minutes per log to find, Claude produces in 42 seconds for pennies. Scale that across hundreds of runs over months, and the system improves continuously while you focus on actual work.

This phase is the foundation for treating Claude Code not as a tool you use, but as a development environment that **adapts to how you work**.

---

## Phase 6: MCP Servers

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

### Phase 6 — MCP Scopes

- **User scope** (`~/.claude.json`): personal API keys, tokens. NOT synced by this repo (contains secrets).
- **Project scope** (`.mcp.json` in repo root): shared server definitions, committed to git. No secrets — use `${env:VAR_NAME}`.
- **Local scope** (default): only on current machine. Good for experimental servers.

Transport types: stdio (local process, most common), HTTP (remote/cloud services, recommended for new servers), SSE (deprecated — use HTTP).

### Phase 6 — MCP via Docker

MCP servers can run as Docker containers, which provides isolation and reproducibility. Useful for servers that have complex dependencies or need specific runtime environments. If using Docker Desktop, the MCP server runs inside a container and communicates via stdio or HTTP.

---

## Phase 7: Local AI Offloading (Future)

**Serves: Both workflows** — Preserves Claude subscription for complex thinking by offloading mechanical tasks to local GPU hardware.

Dependencies: Phase 6 (MCP knowledge — Ollama connects via MCP server)

NOTE: Ollama installation and GPU provisioning are handled by SkyyCommand, not this repo. This phase only covers the Claude Code integration side — MCP server config and delegation rules.

- [ ] **Add Ollama MCP server to Claude Code** — Use mcp-local-llm or similar MCP server pointing at SkyyCommand-managed Ollama instances. Claude becomes orchestrator, local models handle volume.
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
# Roadmap

**What this file is:** the phase list. Each phase carries its milestones as checkboxes and links to a detailed planning doc in [`phases/`](phases/). Nothing else lives here — repo structure, setup and command reference are in [`../../README.md`](../../README.md), [`../guide/deployment.md`](../guide/deployment.md) and [`../guide/operations.md`](../guide/operations.md).

## How to use it

1. **Pick a milestone** from a phase below.
2. **Open its phase doc.** That is where the planning, the task-level checkboxes and the completion criteria live. A phase with no doc yet is not ready to work — writing the doc *is* the planning step.
3. **Work the phase doc** until its boxes are checked and the result is tested.
4. **Then check the box here.** A roadmap checkbox means *shipped and validated*, not *attempted*.

**Phases are named, never numbered**, and headings read `## Phase: <name>`. Numbering made reordering expensive and encoded a sequence that stopped being true. Order reflects rough dependency; **phases are not worked to completion in order**, and moving between them to unblock something is normal.

**Phase docs are written when a phase is picked up, not in advance.** A detailed plan for work that has not started yet is a guess that ages badly — the same reason skills are written after a methodology has been explained twice.

**Status markers:** ✅ COMPLETE · 🟡 IN PROGRESS · 📋 QUEUED, NEEDS PLANNING · 🔵 NOT SCHEDULED · ⚠️ needs restating

---

## Phase: Explore ~/.claude ✅ COMPLETE

Mapped the directory structure. All folders exist but are empty (fresh install). Key discovery: `projects/` is path-keyed and should not be synced.

## Phase: Cross-Device Sync ✅ COMPLETE

Goal: Get this repo deploying to all machines so everything built in later phases automatically propagates.

- [x] **Finalize repo structure** — `config/` directory with synced items (settings.json, CLAUDE.md, agents/, commands/, hooks/, rules/, skills/)
- [x] **Write install.sh** — Idempotent script: checks prerequisites (Claude Code, auth, jq), backs up existing targets, creates individual symlinks from `config/*` into `~/.claude/`, verifies all links. Supports `--non-interactive` / `-n` flag for automation (skips interactive prompts, fails fast on missing prerequisites, skips auth check entirely).
- [x] **Create starter settings.json** — Minimal global settings to start with (can be expanded in later phases)
- [x] **Create global CLAUDE.md** — The `~/.claude/CLAUDE.md` that applies to ALL projects (coding style preferences, global rules, team conventions)
- [x] **Test on laptop** — install.sh runs clean, all 7 symlinks verified
- [x] **Deploy to workstation** — Clone repo, run install.sh, verify
- [x] **Ansible integration (workstations/laptops)** — install.sh runs via Ansible playbook with `--non-interactive` flag on desktops and laptops. Ansible handles cloning the repo and installing prerequisites (Claude Code, jq) before running the script.
- [x] **Deploy to VMs** — Tested on skyy-net VM at `/opt/skyy-net/claude-dot-files`, all 7 symlinks verified

### Cross-Device Sync — Notes

**Workstations & laptops**: Ansible runs `install.sh --non-interactive` on every playbook run. This is safe because the script is idempotent (existing correct symlinks are skipped), and the script may do more than manage symlinks in the future.

**VMs**: Deployed manually with the standard interactive install.sh. Auth (`claude login`) must be done on each new machine — it requires a browser OAuth flow.

---

## Phase: Safety & Guardrails ✅ COMPLETE

**Serves: Both workflows** — Interactive mode needs guardrails so you can approve quickly with confidence. Autonomous mode needs them even more since Claude is working unsupervised.

Dependencies: Phase 1 (so hooks sync across machines automatically)

- [x] **PreToolUse hook: block dangerous commands** — `hooks/block-dangerous.sh` reads JSON from stdin, extracts the bash command, denies if it matches destructive patterns (rm -rf, force push, git reset --hard, DROP TABLE, dd, fork bombs, etc.). Wired in settings.json with matcher `"Bash"`.
- [x] **Stop hook: desktop notification** — `hooks/notify-done.sh` fires `notify-send` on Linux when Claude finishes. Gracefully skips on headless machines. Wired in settings.json Stop event.
- [x] **Review permissions in settings.json** — Permissions provide the first layer (approval popup for unlisted commands), hooks provide the second layer (pattern-based deny for dangerous commands that might match broad allow rules). Two-layer safety net confirmed working.
- [x] **Test each hook** — Permission layer prompts on dangerous commands (first safety layer works). notify-send fires desktop notification (top-right on Cinnamon/Mint). Both verified.

### Safety & Guardrails — Notes

Hook architecture (settings.json wiring, stdin JSON contract, three handler types) and the decision to skip PostToolUse auto-format are documented in `docs/architecture/system-overview.md`. Standards for writing hook scripts live in `docs/standards/hook-scripts.md`.

---

## Phase: Planning & Agents ✅ COMPLETE

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

### Planning & Agents — Subagent Format

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

## Phase: Autonomous Execution

> **Not to be confused with `Phase: Autonomous Operation`, further down.** This phase is about *building the workflows* — the scripts, agents and skills that let Claude do a unit of work unattended. That one is about *running the fleet* unattended: nobody pressing the button, nothing depending on which workstation happens to be awake. This is largely complete; that one is gated on Temporal Integration.


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

### Foundation Validation ✅ COMPLETE

Verify the primitives work end-to-end before building any orchestration.

- [x] **Test headless mode** — Tested `claude -p "/update-file-structure"` successfully. Slash commands work in headless mode.
- [x] **Install and auth `gh` CLI** — Installed via GitHub's apt repo, authed via SSH on both workstation and laptop (Yoga). Protocol: SSH. Account: Pumapumapumas.
- [x] **Test worktree mode** — Tested `-w test-worktree` flag. Claude Code auto-prefixes branch with `worktree-` (so `-w test-worktree` creates branch `worktree-test-worktree`). Worktree lives at `.claude/worktrees/<name>/`. Main working directory untouched during autonomous run.
- [x] **Test PR creation flow** — Full pipeline validated in one command: headless run → worktree created → edit → commit → push → `gh pr create`. PR #1 created successfully. Entire flow autonomous with `--dangerously-skip-permissions`.
- [x] **Establish dual permission model** — Interactive mode uses allow/deny lists (conservative, popup on new). Autonomous mode uses `--dangerously-skip-permissions` (permissive within isolated worktree). Safety comes from `block-dangerous.sh` hook which still fires regardless of permission flags. Hook hardened with expanded patterns (sudo, system control, RCE, SSH tampering, package purges, etc.). Verified empirically that hooks fire under `--dangerously-skip-permissions`.
- [x] **Build cleanup automation** — `/cleanup-merged-worktrees` command scans worktrees, checks PR status via `gh`, removes merged/closed ones. Tested and working.

### Standards Documentation ✅ COMPLETE

Before building more workflows, capture the conventions we've been following so future additions stay consistent and team members can contribute.

- [x] **Agent standards** — `docs/standards/agents.md`: frontmatter schema, tool restrictions, on-demand vs proactive, two-tier strategy, role vs methodology separation.
- [x] **Hook script standards** — `docs/standards/hook-scripts.md`: JSON stdin patterns, jq output (no string interpolation), regex vs fixed-string pattern arrays, testing patterns, integration with settings.json.
- [x] **Skill standards** — `docs/standards/skills.md`: description field criticality, layering with project standards (global HOW, project WHAT), build-from-experience principle, one-topic-per-skill rule.
- [x] **Slash command standards** — `docs/standards/slash-commands.md`: plain markdown (no frontmatter), `$ARGUMENTS` patterns, agent invocation, safety conventions, commands vs agents vs skills decision guide.
- [x] **Reference standards from CLAUDE.md** — Root `CLAUDE.md` Standards section points to all four. Global `config/CLAUDE.md` intentionally does NOT reference (it syncs to all projects and those paths wouldn't exist elsewhere).

### Core Workflows

Aligned with the [Dual Workflow Model](../guide/workflows.md) — these are the four concrete workflows that collectively implement Stage A (Initial Autonomous Run). They vary by scope: from trivial revisions to full project definition.

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
- [x] **Standards enforcement stage added (2026-04-14)** — New Stage 7 (STANDARDS) inserted between refactor and resolve, using the new `standards-auditor` agent. Workflow is now 10 stages. Driven by production feedback: autonomous engineers were drifting from project standards when prompts didn't explicitly require reading them. Inline CLAUDE.md / standards / architecture discovery reminder also added to the IMPLEMENT stage. (PR #21)
- [x] **Shared stages extraction (2026-04-14)** — Stages 1-9 and the Rules block factored into `STAGES_1_TO_9` and `RULES` shell variables, matching the pattern already used by build-phase.sh. Eliminates ~106 lines of duplication between the new-branch and existing-PR paths. Flagged as deferred by the standards-auditor during PR #21 and applied manually as a follow-up.

#### build-phase workflow — Architect & Build ✅ COMPLETE

Main autonomous path. Takes a plan document path as input and implements what it describes. 9-stage workflow with deviation tracking and success criteria verification. Implemented as `scripts/workflows/build-phase.sh`.

- [x] **Build `scripts/workflows/build-phase.sh`** — 9-stage workflow: load plan → validate → implement → test → code review (code-reviewer agent) → refactoring evaluation (refactoring-evaluator agent) → resolve → verify (tests + success criteria) → submit PR with deviation summary. 150 max turns. Built by revision-major.sh (PR #7).
- [x] **Plan-driven input** — Takes a plan document path, not free-text. Extracts scope and success criteria from the plan, verifies against them at the end. Path validation with sanitization regex for heredoc injection prevention.
- [x] **Shared prompt extraction** — Stages 1-8 and Rules extracted into shell variables, eliminating ~80 lines of duplication between new-branch and existing-PR paths.
- [x] **Shared lib integration** — Updated to source `lib/run-claude.sh` (PR #9), matching the pattern of all other workflow scripts.
- [x] **Add optional context argument** — Second positional arg after plan path for injecting additional instructions. Backwards compatible. Delimiter-wrapped to prevent prompt confusion. (PR #11, merged).
- [x] **Single-pass architecture** — Starting with single-session. Will refactor to multi-stage if context bloats on large builds.
- [x] **Test on a real phase** — Tested on Phase 4d gh-monitor plan. build-phase.sh produced 585 lines across 6 files (gh-monitor.sh, systemd units, config, install.sh update, .gitignore). PR #12 created with full deviation summary and success criteria checklist. Workflow followed all 9 stages correctly.
- [x] **Standards enforcement stage added (2026-04-14)** — New Stage 7 (STANDARDS) inserted between refactor and resolve, using the new `standards-auditor` agent. Workflow is now 10 stages. Same addition as revision-major.sh, applied in the same revision-major run. Inline CLAUDE.md / standards / architecture discovery reminder also added to the IMPLEMENT stage. (PR #21)

#### Helper Scripts ✅ COMPLETE

- [x] **Build `scripts/helpers/init-project.sh`** — Pure bash utility (zero AI tokens) for initializing new projects. Creates: git repo (main branch), GitHub remote (SSH, private default), .gitignore (multi-language defaults), four-bucket docs scaffolding, minimal CLAUDE.md and README.md, .claude/ directory. Fully idempotent. Supports `--org`, `--public`, `--skip-remote` flags.

#### Shared Workflow Infrastructure ✅ COMPLETE

- [x] **Extract `run_claude` to shared lib** — `scripts/workflows/lib/run-claude.sh` sourced by all 4 workflow scripts. Expects LOG_FILE, MAX_TURNS, VERBOSE, FORMATTER as environment variables with guards. Eliminates ~75 lines of duplication (PR #8).
- [x] **Stream formatter** — `scripts/workflows/lib/format-stream.sh` for live verbose output. Color-coded, handles tool calls, agent spawns, thinking indicators, cost/turn summary.

#### plan-new workflow (formerly define-project) — Greenfield Project Definition ✅ COMPLETE

Heaviest workflow. For new projects or major features — produces the foundation documents that prevent drift and disappointment later. Implemented as `scripts/workflows/plan-new.sh`.

- [x] **Build `scripts/workflows/plan-new.sh`** — 14-stage workflow: requirements → stakeholders → tech stack → architecture → phases → epics → dependencies → security → roadmap → documentation → architect review → planner review → resolve → submit. 225 max turns. Built by revision-major.sh (PR #15).
- [x] **Supporting skills already built** — Planning methodology, architecture decisions, project definition, and documentation structure skills all exist.
- [x] **Review stages added** — Architect and planner agents review the planning output before submission (Stages 11-13). Added via gh-monitor `@claude revision-major:` comment on PR #15. First successful gh-monitor live test.
- [x] **Rename to `plan-new.sh`** — Align with the naming convention: `plan-*` prefix for planning workflows.
- [x] **Test on a real project** — Tested on 1Password Vault Manager (helloskyy-io/1password-integration). v1 graded B+. Gaps addressed: no-redundancy rule, secrets management framework, security-auditor review stage added (now 15 stages). v2 re-run with init-project scaffolding in progress.

#### plan-revision workflow — Revise Existing Planning Docs ✅ COMPLETE

The most-used daily planning workflow. For revising roadmaps, adding phase docs, updating requirements, creating ADRs, restructuring epics — anything that modifies planning documentation within an existing project. Uses planning agents (architect + planner), NOT code agents. Implemented as `scripts/workflows/plan-revision.sh`.

- [x] **Build `scripts/workflows/plan-revision.sh`** — 7-stage workflow: assess → plan → revise → architect review → planner review → resolve → submit. Uses architect and planner agents for review (NOT code-reviewer or refactoring-evaluator). Sources shared lib/run-claude.sh. 75 max turns. Built by revision-major.sh (PR #18).
- [x] **Supporting agents already built** — architect (preloads architecture-decisions, documentation-structure) and planner (preloads planning-methodology, documentation-structure) exist and have the right skills.
- [x] **Supporting skills already built** — planning-methodology, architecture-decisions, documentation-structure all exist.
- [x] **Test on a real planning task** — Used to create Phase 5b detailed phase doc (`docs/development/phases/automated-pr-generation.md`). PR #19 created with full task breakdown, dependencies, success criteria, risks. Architect and planner review stages validated — output quality significantly higher than unreviewed planning.

### PR Comment Automation (Local GitHub Monitor) ✅ COMPLETE

The Stage C escalation path. A local systemd timer (`gh-monitor`) polls GitHub for `@claude` PR comments and launches workflows locally using Max subscription. Zero API costs, zero security exposure.

**Redesign rationale (2026-04-10):** Original GitHub Actions approach (PR #10, closed) was abandoned because: (1) Actions runners require Claude API billing, not Max subscription; (2) security exposure on a Tailscale-hardened workstation is unacceptable; (3) local polling achieves the same UX at zero additional cost.

Plan document: `docs/development/phases/github-actions-integration.md`
Service standard: `docs/standards/services.md`

- [x] **Build `scripts/services/gh-monitor.sh`** — 467-line bash poller using `gh` CLI. Routes `@claude revision:`, `@claude revision-major:`, `@claude help`, and unknown commands. Posts clarifying comment when context is insufficient (<10 chars). Concurrency guard with PID-based stale lock detection. Rate limit checking. Dry run mode. Code block stripping for @claude detection. Built by build-phase.sh (PR #12).
- [x] **Configuration** — Centralized `config.yaml` at repo root with `gh-monitor:` section. Read via `yq` with reusable `cfg()` helper. Precedence: env var > config.yaml > script default. (PR #13, migrated from per-service .config.env)
- [x] **Reaction-based deduplication** — 👀 (eyes/processing), hooray (done), -1 (failed), confused (clarification). First reactor wins (multi-machine safe via API check).
- [x] **Systemd integration** — `gh-monitor.service` (oneshot) + `gh-monitor.timer` (5 min, Persistent=true, OnBootSec=2min). Survives reboots, catches up on backlog.
- [x] **Update install.sh** — `--with-services` flag for opt-in deployment. Symlinks units, reloads systemd, enables timer. Idempotent. Architecture-aware yq installation (amd64/arm64/arm).
- [x] **Deploy and enable** — Ran `install.sh --with-services` on workstation. yq installed (architecture-aware amd64), systemd units symlinked, timer enabled and started. Verified active with `systemctl --user status gh-monitor.timer`. Polling every 5 minutes.
- [x] **Live test** — Posted `@claude revision-major:` comment on PR #15. gh-monitor detected it within one polling cycle, parsed the route correctly, fetched the PR branch, created a worktree, and launched `revision-major.sh --pr 15`. Full autonomous loop confirmed. Success comment posting also verified (PR #16 added the feature). Note: comments post as the user's GitHub account (gh CLI auth), not a bot — prefixed with 🤖 **[gh-monitor]** to distinguish from human comments.

### Skills Library (ongoing, built from experience)

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
- [x] **Project definition skill** — `config/skills/project-definition.md`: 11-stage process for defining a new project from scratch — requirements gathering, stakeholders & success criteria, tech stack selection, high-level architecture, phase breakdown, epic identification, dependency mapping, initial security review, roadmap, documentation layout, CLAUDE.md setup. Scales from very small (<2 weeks) to large (1+ years) projects. Rare activation (only for greenfield projects via `plan-new.sh`).

**Refactoring skills:**
- [x] **Refactoring methodology skill** — `config/skills/refactoring-methodology.md`: when to refactor vs leave alone, evaluating suggestions (accept/reject/defer), safe refactoring patterns, dangerous patterns, measuring impact. Pairs with refactoring-evaluator agent.

**Standards skills:**
- [x] **Standards enforcement skill (2026-04-14)** — `config/skills/standards-enforcement.md`: methodology for verifying conformance against the CLAUDE.md chain, `docs/standards/`, `docs/architecture/`, and existing exemplar files. Covers a layered discovery process (read standards first, grep for exemplars, cite sources), confidence scoring (High / Medium / Low), and red flags. Pairs with the standards-auditor agent. Added in response to production feedback about autonomous workflows drifting from project standards when prompts didn't explicitly require reading them.

**Future skills (CPI-driven, build only when gaps are identified):**

One gap was identified from production feedback on 2026-04-14 and addressed by the standards-enforcement skill above. Code-reviewer agent continues to perform well without a dedicated methodology skill (CPI finding #5 confirms). Future skills will be driven by CPI analysis and production feedback — when the data or lived experience shows a recurring gap, that becomes a skill. This is Phase 5 territory, not Phase 4.

**Agent review:**
- [x] **Trimmed planner agent** — 212 → 45 lines. Methodology extracted to planning-methodology skill. Agent is lean role definition referencing the skill.
- [x] **Trimmed architect agent** — 212 → 50 lines. Same pattern. References architecture-decisions skill.
- [x] **Built refactoring-evaluator agent** — New read-only Sonnet agent for structural evaluation. Distinct from code-reviewer (correctness vs structure).
- [x] **Built standards-auditor agent (2026-04-14)** — `config/agents/standards-auditor.md`: read-only Sonnet agent for project-standards conformance review. Distinct from code-reviewer (correctness) and refactoring-evaluator (structure) — asks "does this follow the project's established conventions?" Preloads standards-enforcement + documentation-structure skills. Integrated as Stage 7 in both revision-major.sh and build-phase.sh.


---

## Phase: Continuous Process Improvement

**The game-changer phase.** This phase elevates the dotfiles repo from "static configuration" to a **self-improving development environment**. By analyzing logs from real workflow runs, we identify patterns, inefficiencies, and improvements — then feed those back into the system. The result is a true continuous-improvement feedback loop where the development environment gets smarter over time based on actual usage.

This phase deserves its own top-level designation because:
- It's a **meta-workflow** that operates on other workflows
- It transforms the entire system from "manually maintained" to "self-calibrating with human oversight"
- It compounds over time — every cycle makes future cycles more valuable
- It has its own architecture, prerequisites, and graduation path
- It's the foundation for everything that comes after (including SkyyCommand AI integration)

### Review Workflow (manual mode)

Build the core workflow that analyzes recent logs and produces actionable recommendations.

**Prerequisites (updated 2026-04-10):**
- ~~Phase 4c complete (at least `revision.sh` + `build-phase.sh` built)~~ → ✅ All 4 core workflows built: revision.sh, revision-major.sh, build-phase.sh, review-runs.sh.
- ~~20+ workflow runs logged~~ → 12 logs analyzed in first formal CPI report. Patterns already emerging clearly at this sample size.
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
- [x] **Run first formal cross-run analysis** — Analyzed 12 logs across 4 workflow types. Produced 14-finding report at `docs/development/reviews/review-2026-04-10.md`. 5 high-confidence findings, 5 medium, 4 low. 100% success rate, zero user corrections across all runs.
- [x] **Capture findings into workflow improvements** — First CPI cycle complete (PR #14). Applied 3 high-confidence findings: (1) file-too-large read guidance added to all workflow prompts, (2) rate limit check with exponential backoff added to shared lib/run-claude.sh protecting all workflows, (3) test fixture path guidance added to workflow-scripts standard. **Phase 5a: Cycle 1 complete.**
- [x] **Cross-repo review infrastructure + CPI cycles 2-3 (2026-04-24)** — review-runs.sh report output migrated to claude-dot-files/docs/development/reviews/ with source-repo metadata in filename and header (eliminates per-repo report scatter). Two production reviews generated: mdc-master-planning (20 plan-revision runs) and skyy-command (20 revision-major + build-phase runs). Shipped across both cycles: H1 parallel review-agent dispatch (plan-revision, then extended to revision-major + build-phase — ~2× review phase speedup), H2 generalized large-file reading rule, extended H3 parameter-naming rules (Grep + Read + Glob + TodoWrite), M1 bulk-rename workflow-fit check in plan-revision Stage 1, NEW file-reading discipline rule (no unbounded re-reads), NEW re-Read-before-Edit rule (formatter/linter races), NEW parallel gather-phase rule. plan-revision collapsed from 8→6 stages, revision-major + build-phase from 10→8 stages. **Phase 5a: Cycles 2 and 3 complete.** Expected impact awaiting next review cycle (~2026-04-30).
- [x] **Build a "workflow analysis" skill** — `config/skills/workflow-analysis.md`: pattern categories, confidence scoring, analysis process, red flags. Built ahead of schedule by the revision-major test run (PR #5).

### Automated PR Generation from CPI findings — ⚠️ NEEDS RESTATING, may be dead

Extending `review-runs.sh` to open a PR with proposed workflow changes rather than emitting a report. **Written before `standards-governance.md` existed, and it likely conflicts with it** — CPI findings are ruled ship/defer/reject by a human in the interactive session **by design**, and an auto-opened PR of workflow changes routes around that. Same problem as Advanced Self-Improvement's "automated skill capture" below.

Not automatically dead: a PR is a *proposal*, not a merge, so a version where the workflow drafts and a human still rules may survive. But it needs restating in those terms before it is scheduled, and the restating is the work.

- [ ] **Extend review-runs.sh to optionally create a PR** — Instead of just a markdown report, the workflow can open a PR with proposed changes to workflow scripts, agents, prompts, or skills. Always requires human review.
- [ ] **Design the PR template** — Each PR includes: which logs were analyzed, what patterns were found, confidence scores, before/after diffs, and recommended testing approach.
- [ ] **Test the PR creation flow** — Run it on real findings, verify the PR is reviewable and the changes are sensible.

### Scheduled Operation

> **The future of this is `Phase: Autonomous Operation → Temporal Crons`.** `review-runs.sh` itself stays here — it exists and it is CPI. Only the *trigger* moves, off `claude schedule` / systemd timers onto a durable schedule that survives the machine being off.

Move from manual triggering to scheduled operation.

**Tasks:**

- [ ] **Schedule weekly review runs** — Use `claude schedule` to run the review workflow every Monday morning. Reports arrive automatically.
- [ ] **Schedule automated PR generation** — After scheduled reports prove useful, escalate to scheduled PRs with proposed changes.
- [ ] **Tune the analysis window** — Find the right balance between recency (responsive to recent work) and sample size (statistical relevance). Likely 7-14 days.
- [ ] **Add notification on completion** — Hook into the existing Stop hook pattern so you know when the weekly report is ready.

### Pattern Library and Skills

The continuous improvement loop generates insights that should be captured systematically. As patterns emerge consistently across multiple cycles, they should become permanent parts of the system.

**Tasks:**

- [ ] **Build a "continuous improvement methodology" skill** — Capture the patterns we learn about what makes workflows good vs bad. This becomes the institutional knowledge of "what we learned about Claude Code workflows." Distinct from workflow-analysis (which is about log reading) — this is about the meta-process of improving the system.
- [ ] **Track resolved patterns** — Maintain a log of patterns identified and resolved so we don't re-litigate them. Location: `docs/development/reviews/resolved-patterns.md`.
- [ ] **Pattern → skill pipeline** — When the same recommendation appears across multiple review cycles, automatically suggest promoting it to a permanent skill.

### Graduation Evaluation — ✅ ANSWERED 2026-07-30, items below are historical

**This question is settled and the items below are kept as record, not as work.** The evaluation happened; the answer is **durable execution (Temporal-shaped), adopted for durability and resumability — NOT to gain composition, which already works in bash.** A parent needs only a child's exit code plus one stable identifier on its final line, which the completion contract already provides; `revision.sh` polls CI between children in ~40 lines of shell, the kind of thing a framework is usually adopted *for*.

Agent SDK, Managed Agents and Paperclip were considered and are not the gap — none of them supplies durability. See `docs/development/skyy-net-seed-handoff.md` for the decision record and `docs/guide/claude_code_orchestration.md § When to Graduate Beyond Bash` for the criteria as they now read.

**Do not re-litigate these boxes:**

Evaluate whether bash-based workflows are sufficient or if heavier tooling is warranted. Only relevant after several CPI cycles with production data.

- [ ] **Evaluate bash limits** — Have we hit real limitations (error handling, state, structured data, team scale)?
- [ ] **Evaluate Agent SDK** — If bash is hitting limits, consider Python/TypeScript SDK.
- [ ] **Evaluate Anthropic Managed Agents** — Public beta option for hosted orchestration.
- [ ] **Evaluate Paperclip** — Criteria: does it reuse existing agent assets? Can workflows be done with raw `claude -p`? Is config portable?

### Advanced Self-Improvement — ⚠️ PARTLY FORBIDDEN as written, needs restating before any of it is scheduled

**"Automated skill capture" and any auto-add-to-standards item directly conflicts with `config/rules/standards-governance.md`**, which is binding: standards and skills are a curated product with human-in-the-loop control, and autonomous workflows may SURFACE candidates but must never auto-create or auto-modify them. That rule postdates these boxes and wins.

The measurement items (effectiveness tracking, regression detection, cross-workflow analysis) are still valid and are genuinely interesting — but they need rewriting as *surface-for-review*, not *auto-apply*.

**Partly delivered already:** `docs/development/cpi-decisions.md` is the resolved-pattern log Phase 5d asked for, append-only with watch-criteria, and the pattern→skill promotion happens through the interactive session by design rather than automatically.

**Items below are historical and must be restated before scheduling:**

This is where we approach true self-improvement, but with significant guardrails. Only build this once we have months of stable operation and high-confidence patterns.

**Tasks:**

- [ ] **Build automated skill capture** — When a pattern is identified consistently across multiple review cycles with high confidence, auto-add it to skills (still gated by human PR approval).
- [ ] **Cross-workflow analysis** — Compare patterns across different workflow types. Are there common improvements that apply to all?
- [ ] **Effectiveness tracking** — Measure if the recommended changes actually improved subsequent runs. Did the change reduce token usage? Decrease turn count? Improve output quality?
- [ ] **Regression detection** — Notice when changes made changes things WORSE. Alert on degradations.

### Critical Rules (apply to all CPI work)

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

## Phase: Workflow Decomposition — 📋 QUEUED, NEEDS PLANNING

**Phase doc:** not yet written — writing it is the planning step.

Turning every heavy workflow into a parent over children, so each boundary is a retry/resume point and children become recombinable rather than copied. **Half-built already**: `revision.sh` and `revision-minor.sh` shipped as three-child parents before any of it was written down.

- [ ] **Rule fork-vs-parameterize** — gates everything else here. Refines are ~82% shared (parameterize); drafts are ~9% shared and are a *behaviour* decision, not a deduplication. Rule before a third copy family exists
- [ ] **Decompose `build-phase.sh`** — `review-pr` drops in free; the open question is whether draft/refine fit, given `build` carries a plan-conformance obligation revision does not
- [ ] **`lint-docs.sh`** — gate the stale-doc class: a script no doc names, or a doc stating a turn count its script disagrees with
- [x] **Split `revision.sh` into draft → refine → review-pr** — shipped, two burn-test cycles
- [x] **Split `revision-minor.sh` on the same shape** — shipped, one-lens middle child
- [x] **Extract the activities layer** — `run-claude`, `wait-for-ci`, `require-environment`
- [x] **Write it down** — `docs/standards/workflow-scripts.md § Composition`

Evidence and confidence levels: [`phases/burn-test-intake-2026-08-02.md`](phases/burn-test-intake-2026-08-02.md)

## Phase: Memory Management Framework — 📋 QUEUED, NEEDS PLANNING

**Phase doc:** not yet written. Kind 2 below **needs real research first** — the problem is well understood, the answer is not.

Two distinct kinds of memory, currently conflated and only half-built. Both exist because a context window ends and the work does not; they differ in who reads them.

**Kind 1 — durable memory in git, read by humans and AI.** Built and in use, undocumented as a framework: PR threads carry change-outcomes, Issues carry no-change outcomes, the standup tracker carries continuity. *Open* IS the to-do bit.

**Kind 2 — machine handoff in a file, read by CODE.** Not built. A parent must decide *in code, with no AI in the loop*, which child to invoke next.

- [ ] **Read the result envelope; gate on `is_error`** — the last line of every `stream-json` log already carries `is_error`, `subtype`, `terminal_reason`, and **the parent gates on none of them**. A child can fail and the parent greps on regardless. Replaces a 307-line log scrape
- [ ] **Research the payload contract** — GitHub Actions *deprecated* stdout output-passing for a caller-declared file path; Argo and Tekton converge on the same shape; Tekton's 4096-byte cap is the lesson that this channel carries **references, not payloads**
- [ ] **Design it** — closed-vocabulary verdict plus the payload the bare token cannot carry. Absent or malformed must fail safe to the human branch, because **our producer is an LLM that can emit a plausible-looking but wrong result** — an assumption no surveyed CI system has to defend against
- [ ] **Document Kind 1 as a framework** — it exists as prose in `operations.md` and behaviour spread across prompts
- [ ] **Convergence-based stopping** — *"did this pass find anything not in the previous pass's result?"* is answerable against two typed payloads, not two prose logs. Depends on the above

Evidence, prior art and the plateau correction: [`phases/burn-test-intake-2026-08-02.md`](phases/burn-test-intake-2026-08-02.md)

## Phase: Managed Configuration — 📋 QUEUED, NEEDS A DECISION FIRST

**Phase doc:** not yet written. **The boundary decision comes first** — the mechanism follows from it, and picking a mechanism first is backwards.

Monolithic agent files are not a problem; they are dumb and simple and that is a feature. The problem is *where they live and who can change them*. Everything a workflow depends on is symlinked into `~/.claude/`, so an interactive session editing any of it silently changes what every autonomous dispatch on that machine does — with no divergence detection between machines. `run-claude.sh` already refuses to dispatch on an inherited *model*; by that same rule all of this is ambient and underived.

- [ ] **Decide where the managed/user boundary falls** — agents, skills, rules and hooks are all workflow-critical; `commands/` is the clearest user tier, except `/standup` which is operational
- [ ] **⚠️ Resolve the safety blocker first** — `hooks.PreToolUse → block-dangerous.sh` lives in **user-level** `settings.json`, and headless runs pass `--dangerously-skip-permissions`, making it the only live control. `--setting-sources project,local` would strip it from every autonomous run. The hook must change scope, or be supplied another way, before the flag is touched
- [ ] **Test `--agents` at our prompt sizes** — it takes inline JSON and our definitions are large
- [ ] **Choose the mechanism** — injection at dispatch, scope separation, or something else

## Phase: Temporal Integration — 📋 QUEUED, NEEDS PLANNING

The port to durable execution. **Gated on the two phases above** — not by preference, by dependency: Temporal is being adopted for durability, resumability and cross-run observability, **NOT to gain composition**, which already works in bash. A parent needs a child's exit code plus one stable identifier on its final line, and the completion contract already supplies both. Porting before the decomposition and the handoff contract are settled would mean porting a shape we are still changing.

**Direction is settled; nothing is planned.** Decision record: [`skyy-net-seed-handoff.md`](skyy-net-seed-handoff.md). Binding standard the port conforms to: `standards/development/temporal/` in `mdc-master-planning` — the three-tier model (generic activities → composable child workflows → parent workflows), `ActivityResult`, `ACTIVITY_MAP`.

**What is already true and should not be re-derived:**

- **Our layers already map.** `children/` are child workflows, not activities (an activity must be idempotent per §7.1, and a child that pushes commits is not). `activities/` are the generic executors. Parents are parent workflows. That alignment was done deliberately so the port is a re-host rather than a redesign.
- **No helper/compiler tier is needed** for our shape — the standard exempts direct-dispatch orchestrations (parents naming the callable inline) from the step-dict execution-plan pattern. That exemption stops applying when git/gh operations move out of the model's turn and something has to compile their inputs.
- **Topology, from the seed handoff:** server (Temporal + Postgres) on a backed-up VM so event history is a backed-up asset; workers as **bare systemd processes, never containerized**, on every machine that holds repos. Claude Code must run on the machine holding the repo — that repo-locality constraint drives the whole worker placement.

**Open, and the thing to settle before any build:**

- [ ] **The invocation must be indistinguishable from an operator running the command in a terminal.** This is a design constraint, not a permission question, and it is the one that decides whether the port is viable on a subscription model at all. It is being tested separately.
- [ ] **A `claude_cli` activity domain** — heartbeating for 10–60 minute runs, transcript-to-file for payload limits. This is the genuinely new work; most of the rest is a port.
- [ ] **Plan the migration order** — which workflow moves first, and what runs in parallel during the cutover.
- [ ] **Decide what happens to the bash fleet after** — retired, or kept as the edge fallback.

### Implementation Language — ✅ DECIDED 2026-08-03: Python

**Bash is not an option, and that is not a preference.** Temporal has no bash SDK. A worker is a long-running process that implements the task-queue protocol and, for workflow code, guarantees deterministic replay. Bash cannot do either. The SDKs are Go, Java, Python, TypeScript, .NET, PHP and Ruby — pick one or do not port.

**But the bash does not die.** Skyy-Command's activities already shell out via `subprocess` in several domains, and every activity we would write ultimately invokes `claude -p` anyway. A bash script survives as *an executable an activity calls*. The question is only whether that indirection earns its keep once the caller is already a real program.

**Why Python, recorded once so it is not re-argued.** The inputs were never open questions:

- The framework being ported **is Python** — `lib/temporal/` in Skyy-Command, 123 non-test modules.
- The **Worker Deployment Standard is written in Python** — `python:3.11-slim` base image, `CMD ["python", "<worker>_worker.py"]`. Conforming to a binding standard while choosing a different language means diverging from it on day one.
- The seed handoff already specifies the worker as a Python venv with `temporalio` + the `claude` CLI.

Choosing anything else is not "evaluating options," it is proposing to diverge from a standard we have already agreed to conform to. **The narrow thing that does deserve checking** is whether any Python-SDK constraint bites our specific shape — 10–60 minute activities need heartbeating, and large transcripts hit payload limits. Both are already flagged as known work in the seed handoff, which is evidence the constraint is understood rather than unexplored.

**Convert → test → orchestrate. The port does not need a big bang, and the standard's own architecture is what allows this.**

Generic executors under `activities/` are **plain functions** — verified in Skyy-Command: no `@activity.defn`, no `temporalio` import, just `subprocess` and a returned `ActivityResult`. Decoration happens one layer up, in the semantic wrappers. So the port splits into stages that are each independently valuable:

| Stage | What exists at the end | Temporal needed? |
|---|---|---|
| **A — Convert** | The fleet as plain Python functions plus a CLI entrypoint. Same invocation UX as today, now unit-testable, and the prompts-are-code escaping class disappears with real string literals | **No** |
| **B — Wrap** | Semantic wrappers add `@activity.defn`; the plain functions from A are untouched | Yes, but nothing orchestrates yet |
| **C — Orchestrate** | Workflows and parents compose the wrappers; schedules replace timers | Yes |

**Stage A is a valid resting place.** If Temporal slips, we still have a tested Python fleet that runs exactly like the bash one and has shed an entire class of outage. That is the property that makes this safe to start before everything else is settled.

**DECIDED: Python. Do not re-open this.** The framework being ported is Python, the Worker Deployment Standard is written in Python, and the seed handoff already specifies a Python venv worker. Choosing otherwise would mean diverging from a binding standard on day one for no stated benefit. Recorded here so the decision is not made a second time.

**The agreed migration path, end to end:**

1. **Convert the existing fleet to Python, in place.** Everything in `activities/`, `common/`, `children/` and the top-level parents becomes Python with a CLI entrypoint. Same invocation UX, same behaviour, no Temporal. This is Stage A, and it stands on its own.
2. **Stand up Temporal.**
3. **Refactor into the Temporal file layout** — the `{name}_workflow.py` / `{name}_helper.py` / `{name}_activities.py` trio beside each other in a module purpose folder, generic executors under `activities/`, per Temporal Standard §3 and §10. `activities/` and `common/` map straight across. **`children/` dissolves** — there is no such directory in the Temporal model, because a child workflow is not a kind of file in a place, it is a workflow another workflow starts; every workflow lands in `modules/` regardless of who calls it. The directory exists today only because bash has no call graph to read.
4. **Bring the Temporal standards over** — `temporal_standard.md`, `worker_deployment_standard.md` and `stateful_patterns.md` from `mdc-master-planning`, adopted here rather than re-derived, with a claude-dot-files addendum only for what is genuinely ours (long-activity discipline for 10–60 minute `claude -p` runs, machine-axis queue naming, topology profiles).

- [ ] **Confirm the two known SDK constraints** — heartbeating for long activities, payload limits for transcripts.
- [ ] **Decide what happens to the bash fleet after Stage A** — retired, or kept as an edge fallback needing no runtime.

---

### Counter-argument, recorded

**Counter-argument, stated fairly:** bash has zero runtime dependencies, the current fleet works, and every activity ultimately shells out to `claude -p` regardless. A rewrite buys nothing on its own — **it only pays off as part of this port**, and Stage A above is what makes it pay off early rather than at the end.

---

## Phase: Autonomous Operation — 🔵 NOT SCHEDULED

> **Gated on Temporal Integration, deliberately placed after it.** Distinct from `Phase: Autonomous Execution` above, which is about building the workflows themselves. This phase is about running the fleet with nobody pressing the button.

The tier above parents. Where a parent composes children into one task-complete unit of work, this composes **parents** into a loop that keeps going: what ran, what it concluded, and what should run next — decided from memory, in code, with no human in the loop and no AI choosing the route.

**The shape, as far as it is understood:**

- **A driver that runs many parent workflows in sequence**, choosing each next dispatch from persisted state rather than from a script written in advance. This is the payoff of the Memory Management Framework — the typed result a parent leaves behind is what the next decision reads.
- **Exit criteria that are real and observable** — a `HOLD` on a PR needing human judgement, a convergence signal, a budget ceiling. **None of this is designed.** The one thing already known: it must be able to stop and hand back, and "stop" has to be a state something can *observe*, not a turn count.
- **Cron-driven entry** for the time-shaped work (below).

**Not designed. Not planned. Do not build toward it yet** — the loop is only safe once memory is typed and durable execution can resume a failed leg. Recorded now so the earlier phases are built with it in view.

### Temporal Crons — 📋 STUB

Scheduled dispatch owned by the durable-execution layer rather than by the edge machine. Depends entirely on **Temporal Integration** landing first.

**This is where `review-runs.sh` gets its scheduling.** The workflow itself already exists and belongs to Continuous Process Improvement — nothing about it moves here. What moves here is only the *trigger*.

- [ ] **Move scheduled dispatch off `claude schedule` / systemd timers onto Temporal schedules** — the current design puts the trigger on whichever workstation happens to be awake. A Temporal schedule survives the machine being off, is visible in one place, and its history is queryable.
- [ ] **Decide what is actually cron-shaped** — CPI sweeps and research revalidation are the obvious candidates because they are time-driven. PR disposition is event-driven and should stay event-driven; do not put it on a timer because the timer exists.
- [ ] **Define failure behaviour for a missed window** — catch-up run, skip, or alert. Different answers for a CPI sweep (skip is fine) and a research revalidation (skipping silently lets a paper rot).

---

## Phase: MCP Servers — 🔵 NOT SCHEDULED

Untouched since April and nothing depends on it. Still plausible, still unstarted — recorded honestly rather than left looking active. Revisit when a concrete need appears rather than on a calendar.



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

### MCP Scopes

- **User scope** (`~/.claude.json`): personal API keys, tokens. NOT synced by this repo (contains secrets).
- **Project scope** (`.mcp.json` in repo root): shared server definitions, committed to git. No secrets — use `${env:VAR_NAME}`.
- **Local scope** (default): only on current machine. Good for experimental servers.

Transport types: stdio (local process, most common), HTTP (remote/cloud services, recommended for new servers), SSE (deprecated — use HTTP).

### MCP via Docker

MCP servers can run as Docker containers, which provides isolation and reproducibility. Useful for servers that have complex dependencies or need specific runtime environments. If using Docker Desktop, the MCP server runs inside a container and communicates via stdio or HTTP.

---

## Phase: Local AI Offloading — 🔵 NOT SCHEDULED

Untouched since April. The hardware exists and the idea holds, but model management went a different direction in the meantime (per-workflow explicit `--model` resolved from `config.yaml`), so the integration points below predate the current design and would need re-reading before any of it is built.



**Serves: Both workflows** — Preserves Claude Max rate limits by offloading mechanical tasks (file summarization, classification, boilerplate) to local GPU hardware. Estimated savings: ~10-15% of Opus turns per workflow with zero quality loss on offloaded tasks.

**Priority elevated (2026-04-12):** Real-world usage showed 2 concurrent engineers + PM session can exhaust rate limits in half a metered period. Local offloading is now a near-term priority, not a future nice-to-have.

Dependencies: Phase 6 (MCP knowledge — Ollama connects via MCP server). NOTE: Ollama installation and GPU provisioning are handled by SkyyCommand, not this repo.

### Model Testing and Selection

Test candidate models on real project files before committing to the MCP integration. Quality and speed must be validated empirically.

**Hardware allocation:**

```
RTX 4080 (16GB VRAM):
├── Qwen 2.5 Coder 7B (Q4_K_M)  — ~5GB  — candidate for summarization
├── Timpi Node                    — ~1.6GB — passive income (colocated)
└── Free                          — ~9GB

A6000 (48GB VRAM):
├── Qwen 2.5 Coder 14B (Q4_K_M) — ~10GB — candidate for summarization (higher quality?)
└── Free                          — ~38GB
```

- [ ] **Deploy Qwen 2.5 Coder 7B on RTX 4080** — via Ollama on SkyyCommand-managed instance
- [ ] **Deploy Qwen 2.5 Coder 14B on A6000** — via Ollama on SkyyCommand-managed instance
- [ ] **Benchmark summarization quality** — Feed the same 10 project files through both models. Compare summaries for accuracy, completeness, and missed details. Use real files from skyy-command and mdc-master-planning.
- [ ] **Benchmark speed** — Measure tokens/sec on each GPU for each model. Target: responses under 5 seconds for typical file summaries.
- [ ] **Decide: 7B or 14B for summarization** — If 7B quality is comparable to 14B, use 7B (faster, less VRAM). If 7B misses important details, use 14B.
- [ ] **Validate Timpi coexistence** — Confirm Timpi node (1.6GB) runs alongside the chosen model without VRAM contention.

### Local-Model MCP Integration

Connect the winning model to Claude Code via MCP server.

- [ ] **Add Ollama MCP server to Claude Code** — Use mcp-local-llm or similar MCP server pointing at SkyyCommand-managed Ollama instances.
- [ ] **Add delegation rules to global CLAUDE.md** — "For file summarization and classification, use mcp__local-llm__* tools. For architecture decisions, code review, and complex logic, handle directly."
- [ ] **Test end-to-end** — Run a workflow where Opus delegates file reading to the local model. Verify summaries are accurate and workflow quality is maintained.
- [ ] **Measure savings** — Compare Opus turn count and rate limit utilization with and without local offloading.

### Local-Model Workflow Integration

Embed local model usage into the workflow scripts.

- [ ] **Create a summarization skill** — Methodology for when to offload to local model vs read directly. Rules: summarize when exploring/filtering, read directly when editing or reviewing specific lines.
- [ ] **Update workflow prompts** — Add guidance to use local model tools for file scanning and summarization phases.
- [ ] **CPI analysis** — After several workflow runs with offloading, analyze logs for quality impact and savings.

### What Gets Offloaded (and What Doesn't)

| Task | Offload? | Why |
|---|---|---|
| File reading for context | **Yes** — summarize for Opus | Simple comprehension |
| Filtering files by relevance | **Yes** — local model scans, tells Opus which to read | Classification task |
| Writing/editing code | **No** | Quality matters |
| Code review | **No** | Nuance matters (already Sonnet) |
| Architecture decisions | **No** | Deep reasoning needed |
| Boilerplate generation | **Maybe** — test quality first | Simple patterns |

Realistic estimate: **10-15% of Opus turns offloaded** with zero quality loss. The savings compound — every workflow run benefits.

---

# Tools to Evaluate

These are worth investigating but not committed to the roadmap yet:

- **Paperclip** — UI overlay for Claude Code. Offers visual workflow design, agent management, parallel project tracking, and PR review. May overlap with native headless mode + triggers. Evaluate after Phase 4 to see what gaps remain.
- **Claude Agent SDK** — TypeScript/Python framework that powers Claude Code under the hood. Enables building custom agents for non-coding workflows. Worth exploring if we need automation beyond what Claude Code provides natively (e.g., custom CI pipelines, Slack bots, monitoring agents).

---

# Future Ideas (Not Yet Committed)

Potential future capabilities identified during development. These are ideas worth exploring but not prioritized into phases yet. When one becomes actionable, create a phase doc and add it to the roadmap.

### A. Cross-Project Intelligence
Aggregate CPI analysis across multiple repos. Patterns from one project could inform another. "Across your 5 repos, the testing stage consistently takes the most turns — here's why." Requires centralized log collection or report aggregation.

### B. Workflow Composition / Chaining
Chain workflows in sequence: `plan-revision.sh → build-phase.sh → review-runs.sh`. A workflow orchestrator that runs a pipeline of workflows end-to-end. Bash-native version of what Agent Teams or Paperclip offers.

### C. Project Templates
Pre-configured `plan-new.sh` contexts for common project types. "FastAPI microservice," "React dashboard," "CLI tool," "Ansible role." Each template provides stack preferences, common patterns, and boilerplate decisions already made. Eliminates repetitive context in plan-new prompts.

### D. Team Scaling
Adapt the system for multi-developer use:
- Shared `config.yaml` with per-user overrides
- Team-wide CPI reports aggregated across members
- Role-based workflow access (juniors: revision only, seniors: plan-new)
- Shared skills capturing team methodology
- Onboarding workflow that sets up new developers

### E. Metrics Dashboard
Visualize JSONL log data: cost trends, workflow efficiency, failure types, agent utilization. Could be a static HTML page generated weekly by a CPI workflow. Makes trends visible without reading raw reports.

### F. Rollback Automation
A `/rollback-cpi` command that reverts the last CPI PR and marks that pattern as "tried and failed." Prevents repeated application of changes that don't work. Important as CPI automation increases.

### G. SkyyCommand AI Decision Engine
Claude + agent infrastructure as the decision engine for SkyyCommand VM placement. Agents evaluate GPU requirements, server capacity, network topology. The same lean-agent + rich-skill pattern transfers directly to infrastructure management. See memory note `project_skyycommand_ai.md`.

### H. Prompt Pattern Library
As workflows run across real projects, effective prompts emerge. Capturing these as **prompt patterns** (similar to design patterns but for AI interaction) creates a reusable asset. "This phrasing produces better build-phase output" becomes institutional knowledge.

### I. plan-new.sh Greenfield Improvements
Currently `plan-new.sh` requires a pre-existing git repo. For a true greenfield workflow, it should handle `git init`, initial commit, and remote setup automatically. Discovered during the 1Password vault manager test (2026-04-11).

---

# Reference

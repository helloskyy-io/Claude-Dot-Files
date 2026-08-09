# Sprint Plan

**What is being built:** a Claude Code environment that improves itself. Custom agents and methodology skills, autonomous workflows that run headless and deliver reviewed PRs, a memory model built on git rather than state files, and a continuous-improvement loop that reads the system's own run logs and feeds findings back as tracked decisions. It syncs to every machine from one repo.

**The arc.** The completed phases built the foundation — sync, safety, agents, and the autonomous workflows themselves. The current work is **decomposition**: breaking monolithic workflows into composable parents and children, so that each boundary is a review boundary and a retry point. That leads to a **typed handoff** between runs, which is what lets a parent route on a child's result in code rather than by parsing prose — and that, in turn, is the prerequisite for porting onto **durable execution**, where a failed leg resumes instead of restarting.

The through-line: *the run that authors work should not be the run that judges it, and a system should be able to tell you what it decided in a form that code can act on.*

---

**What this file is:** the sprint list. Each sprint carries its milestones as checkboxes and links to a component folder beside this file. Nothing else lives here — repo structure, setup and command reference are in [`../../README.md`](../../README.md), [`../guide/deployment.md`](../guide/deployment.md) and [`../guide/operations.md`](../guide/operations.md).

## How to use it

1. **Pick a milestone** from a sprint below.
2. **Open its phase doc.** That is where the planning, the task-level checkboxes and the completion criteria live. A sprint with no doc yet is not ready to work — writing the doc *is* the planning step.
3. **Work the phase doc** until its boxes are checked and the result is tested.
4. **Then check the box here.** A checkbox here means *shipped and validated*, not *attempted*.

**Sprints are named, never numbered**, and headings read `## Sprint: <name>`. Numbering made reordering expensive and encoded a sequence that stopped being true. Order reflects rough dependency; **sprints are not worked to completion in order**, and moving between them to unblock something is normal.

**A sprint plan is never a history lesson.** It states what is built or is going to be built — nothing else. Why a decision was made, what an approach cost, what got abandoned and on what reasoning: all of that belongs in the phase doc. An abandoned item is struck there with its explanation; it does not appear here at all. Retrospective notes here turn it into a dumping ground and bury the one thing it exists to show.

**A component is a folder, not a file.** `<name>/<name>.md` is its phase doc — named for the component rather than `README.md`, so a tab, a grep hit or a search result identifies itself without its directory. `<name>/research/` holds the evidence its planning cites: `raw/` for the pool, `synthesis.md` for what it means.

Research sits *inside* the component it belongs to, so the plan and the evidence for it are never more than one directory apart and there is no central corpus to hunt through. Research is **non-binding** — a phase doc may cite a pool, never treat one as a decision already made.

**A component that outgrows one phase gets its own `roadmap.md` plus numbered `phaseN_<name>.md` files**, in the same folder. One phase needs no roadmap; do not create one to be tidy. This matches `MDC-Master-Planning`'s `development/service/<component>/` shape, so a workflow can find the same artifacts by name in either repo.

**Phase docs are written when a sprint is picked up, not in advance.** A detailed plan for work that has not started yet is a guess that ages badly — the same reason skills are written after a methodology has been explained twice.

**Status markers:** ✅ COMPLETE · 🟡 IN PROGRESS · 📋 QUEUED, NEEDS PLANNING · 🔵 NOT SCHEDULED · ⚠️ needs restating

---

## Sprint: Explore ~/.claude ✅ COMPLETE

**Phase doc:** [`explore-claude-directory/explore-claude-directory.md`](explore-claude-directory/explore-claude-directory.md)

Mapped what Claude Code stores in `~/.claude/` and classified every path as portable or machine-local, before deciding what to sync.

The directory mixes two very different things: what you *author* — agents, skills, rules, hooks — sitting alongside what Claude Code writes for *itself*, including credentials, session history and per-project state. Getting that split wrong in either direction meant leaking secrets into git or hand-copying config forever. This phase produced the classification every later phase is built on.

- [x] **Every path under `~/.claude/` classified portable or machine-local**

---

## Sprint: Cross-Device Sync ✅ COMPLETE

**Phase doc:** [`cross-device-sync/cross-device-sync.md`](cross-device-sync/cross-device-sync.md)

Get the repo deploying to every machine, so everything built later propagates automatically rather than being hand-copied.

One idempotent installer creates seven targeted symlinks from `config/` into `~/.claude/`, touching nothing machine-local. It runs the same way by hand on a VM or unattended via Ansible on a workstation. The criterion that matters is not that the links exist — it is that an agent written on the laptop is live on the VM after a `git pull`, with no further step.

- [x] **`install.sh`** — idempotent installer, verified on laptop, workstation and VM
- [x] **Ansible integration** — `--non-interactive` for unattended runs
- [x] **Seven targeted symlinks** — `settings.json`, `CLAUDE.md`, `agents/`, `commands/`, `hooks/`, `rules/`, `skills/`

---

## Sprint: Safety & Guardrails ✅ COMPLETE

**Phase doc:** [`safety-and-guardrails/safety-and-guardrails.md`](safety-and-guardrails/safety-and-guardrails.md)

Make it safe to say yes quickly in interactive mode, and safe to walk away in autonomous mode — two different problems needing two different layers.

Permissions prompt on anything unlisted, so approving in a live session is fast and informed. A `PreToolUse` hook denies known-destructive commands regardless of what the allow list says, catching the case where a broad allow rule accidentally matches something that should never run. The second layer is what makes unattended work possible at all — autonomous dispatches bypass permissions entirely, leaving the hook as the only control still operating.

- [x] **`PreToolUse` → `block-dangerous.sh`** — pattern-denies destructive commands
- [x] **`Stop` → `notify-done.sh`** — desktop notification on completion, skips on headless
- [x] **Two-layer model** — permissions for unlisted commands, hook for known-dangerous ones

---

## Sprint: Planning & Agents ✅ COMPLETE

**Phase doc:** [`planning-and-agents/planning-and-agents.md`](planning-and-agents/planning-and-agents.md)

Build the specialists a workflow can dispatch — the actors that plan, review and verify without a human in the loop.

Each agent answers **one question no other agent answers** — narrow lenses rather than one thorough generalist, so a panel dispatched at the same tree returns four distinct results instead of the same finding four times. Everything is read-only unless writing is the job, which is what makes dispatching a whole panel at one worktree safe. None of them fires unless asked; depth is something you reach for, not something that interrupts you.

- [x] **Five specialist agents** — `architect`, `planner`, `code-reviewer`, `test-writer`, `security-auditor`
- [x] **Two-tier strategy** — built-ins for routine work, custom agents on-demand only
- [x] **`/review` and `/best-practices`** slash commands

---

## Sprint: Autonomous Execution ✅ COMPLETE

**Phase doc:** [`autonomous-execution/autonomous-execution.md`](autonomous-execution/autonomous-execution.md)

Build the plan → execute → PR pipeline — scripts that run Claude headless in an isolated worktree, review their own output, and deliver a pull request with nobody watching.

A dispatch gets its own git worktree, so a bad run damages nothing outside it, and every run ends at a **pull request** rather than a push — which is what makes running with permissions bypassed acceptable. Each one leaves a JSONL log of everything it did, and those logs are what the improvement loop later reads. Five workflows cover the range from a one-line correction to defining a project from scratch.

- [x] **Foundation validated** — headless mode, worktree isolation, `gh` auth, and the full dispatch → worktree → commit → PR pipeline in one command
- [x] **Five workflows** — `build`, `build-minor`, `build-phase`, `plan-new`, `plan-revision`
- [x] **`init-project.sh`** — pure bash project scaffolding, zero AI tokens
- [x] **Shared library** — `run_claude`, stream formatter, and common prompt blocks sourced by every workflow
- [x] **Four standards written** — agents, hooks, skills, slash commands, all referenced from `CLAUDE.md`
- [x] **`gh-monitor`** — systemd-timed poller routing `@claude` PR comments to workflows
- [x] **Skills library** — testing, documentation, planning, refactoring and standards methodology, each built when a gap appeared

---

## Sprint: Continuous Process Improvement 🟡 IN PROGRESS

**Phase doc:** [`continuous-process-improvement/continuous-process-improvement.md`](continuous-process-improvement/continuous-process-improvement.md)

Make the system improve its own tooling from evidence it generates itself.

**No human gathers the data.** Every dispatch leaves a JSONL log of what it actually did, and every workflow ends by posting a reflection on its own work — friction hit, decisions that could have gone another way, tooling suggestions. Those are two machine-produced records of the same run, and they carry different things: a log shows a file was read seventeen times, the reflection says the guidance was ambiguous. Findings from both reach an explicit ship / defer / reject, ruled by a human — the system observes itself and proposes, it does not modify itself.

- [x] **`review-runs.sh`** — analyses a window of run logs across repos and produces an improvement report
- [x] **`workflow-analyst` agent** and the `workflow-analysis` skill
- [x] **Cross-repo reporting** — centralised with source-repo metadata, so patterns spanning repos are visible
- [x] **Append-only decisions log** — ship / defer / reject, deferrals carrying an explicit watch-criterion
- [x] **Post-Run Reflection** — every workflow posts a decision log and tooling suggestions to its PR
- [x] **`review-pr` mines reflections** — the run's own words are its primary evidence surface
- [ ] **Sweep the reflection channel systematically** — tooling suggestions are written by every run and read opportunistically; nothing sweeps them the way `review-runs.sh` sweeps logs
- [ ] **Measure the judge's marginal yield** — classify 30 PRs' disposition items as already-stated-by-the-run or new, over logs and threads that already exist

---

## Sprint: Workflow Decomposition — 🟡 IN PROGRESS

**Phase doc:** not yet written — writing it is the planning step.

Turning every heavy workflow into a parent over children, so each boundary is a retry/resume point and children become recombinable rather than copied. **Half-built already**: `build.sh` and `build-minor.sh` shipped as three-child parents before any of it was written down.

- [ ] **Rule fork-vs-parameterize** — gates everything else here. Refines are ~82% shared (parameterize); drafts are ~9% shared and are a *behaviour* decision, not a deduplication. Rule before a third copy family exists
- [x] **Absorb `build-phase.sh` into `build` as `--phase`** — one family, one set of children
- [ ] **`lint-docs.sh`** — gate the stale-doc class: a script no doc names, or a doc stating a turn count its script disagrees with
- [x] **Split `build.sh` into draft → refine → review-pr** — shipped, two burn-test cycles
- [x] **Split `build-minor.sh` on the same shape** — shipped, one-lens middle child
- [x] **Extract the activities layer** — `run-claude`, `wait-for-ci`, `require-environment`
- [x] **Write it down** — `docs/standards/workflow-scripts.md § Composition`

Evidence and confidence levels: [`burn-test-intake-2026-08-02.md`](burn-test-intake-2026-08-02.md)

## Sprint: Memory Management Framework — 🟡 IN PROGRESS

**Planning:** [`memory-management-framework/roadmap.md`](memory-management-framework/roadmap.md) — roadmap + 5 phase docs.
**Phases 1 and 2 complete.** Phase 1 measured 2026-08-08 (13 rulings; 3 no-ops cancelled downstream work); Phase 2 delivered `docs/guide/memory-model.md`. **Nothing is built yet** — Phases 3-5 are the build.

Two distinct kinds of memory, currently conflated and only half-built. Both exist because a context window ends and the work does not; they differ in who reads them.

**Kind 1 — durable memory in git, read by humans and AI.** Built and in use; **documented as a framework by Phase 2**. **Five** surfaces, measured: PR threads carry change-outcomes, Issues carry no-change outcomes, the standup tracker carries continuity, `direction.md` carries rulings only the operator can make, and `candidates.md` carries research candidates and their dispositions — the last of these being what makes `direction.md`'s 90-day rotation safe, since a ruled row may only be deleted once its reasoning is recorded in the candidate that never deletes. The record's own to-do bit is what marks work as current.

**Kind 2 — machine handoff in a file, read by CODE.** Not built. A parent must decide *in code, with no AI in the loop*, which child to invoke next.

- [x] **Phase 1 · Measure the channel** — six experiments against the pinned CLI and the archived logs. 13 rulings; 3 no-ops cancelled downstream work. Merged 2026-08-08
- [x] **Phase 2 · Document Kind 1 as a framework** — delivered as [`docs/guide/memory-model.md`](../guide/memory-model.md). Five surfaces measured, not three. Merged 2026-08-09
- [ ] **Phase 3 · The typed exit record** — envelope, split abstention (*could-not-check* vs *needs-a-ruling*), fail-safe contract, proven on one parent/child pair. Transport measured: `structured_output`
- [ ] **Phase 4 · Migrate the fleet** — every V2 child emits it, no parent parses prose. Bash is frozen and out of scope by decision
- [ ] **Phase 5 · Convergence-based stopping** — computed over the **open** finding set, stopping when it is *empty* rather than unchanged

Evidence, prior art and the plateau correction: [`burn-test-intake-2026-08-02.md`](burn-test-intake-2026-08-02.md)

## Sprint: Managed Configuration — 📋 QUEUED, NEEDS A DECISION FIRST

**Phase doc:** not yet written. **The boundary decision comes first** — the mechanism follows from it, and picking a mechanism first is backwards.

Monolithic agent files are not a problem; they are dumb and simple and that is a feature. The problem is *where they live and who can change them*. Everything a workflow depends on is symlinked into `~/.claude/`, so an interactive session editing any of it silently changes what every autonomous dispatch on that machine does — with no divergence detection between machines. `run-claude.sh` already refuses to dispatch on an inherited *model*; by that same rule all of this is ambient and underived.

- [ ] **Decide where the managed/user boundary falls** — agents, skills, rules and hooks are all workflow-critical; `commands/` is the clearest user tier, except `/standup` which is operational
- [ ] **⚠️ Resolve the safety blocker first** — `hooks.PreToolUse → block-dangerous.sh` lives in **user-level** `settings.json`, and headless runs pass `--dangerously-skip-permissions`, making it the only live control. `--setting-sources project,local` would strip it from every autonomous run. The hook must change scope, or be supplied another way, before the flag is touched
- [ ] **Test `--agents` at our prompt sizes** — it takes inline JSON and our definitions are large
- [ ] **Choose the mechanism** — injection at dispatch, scope separation, or something else

## Sprint: Fleet Reliability — 📋 QUEUED, NEEDS PLANNING

**Phase doc:** not yet written — writing it is the planning step.

The fleet fails in ways nothing watches for. A credential expires overnight, a run reports a success it did not achieve, a dispatch is never claimed at all — and the operator finds out by noticing that nothing happened.

This is the layer that notices, and the one channel that reaches a human when work is blocked rather than a dashboard nobody opens. **It lands before workers**: a restart-recovery contract retrofitted onto running workers is a rewrite, and the guards apply to the fleet that runs today regardless of what it is ported onto.

- [ ] **Three cheap guards** — credential expiry, false completion, and a safety-hook wiring test
- [ ] **A restart-recovery contract** — durable dispatch id and per-subsystem recovery, designed once and covering all three guards
- [ ] **The three-legged liveness predicate** — stalled, looping and stranded, each detected separately
- [ ] **A blocked-work notifier** — and an inbox the operator reads, in place of a dashboard
- [ ] **Per-credential quota headroom** — derived from observed cap-errors, with no provider telemetry

## Sprint: Temporal Integration — 🟡 IN PROGRESS

**Phase doc:** [`temporal-integration/temporal-integration.md`](temporal-integration/temporal-integration.md)

The port to durable execution, in three stages: convert the fleet to Python, wrap it as activities, then orchestrate. **Gated on Workflow Decomposition and the Memory Management Framework** — Temporal buys durability and resumability, not composition, and porting before the shape settles means porting a shape we are still changing.

- [x] **Stage A — the Python tree** — `scripts/workflows/temporal/`, parent/child modules with a CLI entrypoint, no Temporal runtime
- [x] **V1 parity suite** — the Python fleet checked against the bash one it replaces
- [ ] **A `claude_cli` activity domain** — heartbeating for 10–60 minute runs, transcript-to-file for payload limits. The genuinely new work; the rest is a port
- [ ] **Port `review-runs`** — the CPI log sweep, the one of the four with a live role and a run history
- [ ] **Rule on `plan-new` and `review-sprint`** — 1,228 lines between them and **neither has ever executed**; decide whether they die with the bash fleet or earn a port
- [ ] **Stand up the Temporal server** — Postgres-backed, on the VM that gets backed up
- [ ] **Stage B — semantic wrappers** — `@activity.defn` over the plain functions from Stage A
- [ ] **Stage C — orchestrate** — workflows compose the wrappers; schedules replace timers

---

## Sprint: Autonomous Operation — 🔵 NOT SCHEDULED

**Phase doc:** [`autonomous-operation/autonomous-operation.md`](autonomous-operation/autonomous-operation.md) — shape notes, deliberately not a plan

The tier above parents: a driver that composes **parents** into a loop that keeps going, choosing each next dispatch from persisted state rather than a script written in advance. **Gated on Temporal Integration.** Distinct from *Autonomous Execution* above, which built the workflows themselves.

- [ ] **A driver that dispatches from persisted state** — the payoff of the Memory Management Framework
- [ ] **Observable exit criteria** — a `HOLD`, a convergence signal, a budget ceiling. Not a turn count
- [ ] **Scheduled dispatch on Temporal schedules** — off `claude schedule` and systemd timers, so a schedule survives the machine being off
- [ ] **Catch-up behaviour per schedule** — decided by the window-scoped vs state-converging split in the phase doc

---

## Sprint: MCP Servers — 🔵 NOT SCHEDULED

**Phase doc:** [`mcp-servers/mcp-servers.md`](mcp-servers/mcp-servers.md) — April notes, not a plan

Extend Claude's reach to external tools and APIs. Untouched since April and nothing depends on it — revisit when a concrete need appears rather than on a calendar.

- [ ] **A `.mcp.json` template** — project-level config committed to git, secrets via `${env:VAR_NAME}`
- [ ] **One or two stack-specific servers** — chosen against daily workflow, added one at a time
- [ ] **Setup documentation** — adding tokens locally, verifying with `claude mcp list`

---

## Sprint: Local AI Offloading — 🔵 NOT SCHEDULED

**Phase doc:** [`local-ai-offloading/local-ai-offloading.md`](local-ai-offloading/local-ai-offloading.md) — April notes, not a plan

Offload mechanical work — file summarization, classification, boilerplate — to local GPU hardware, to preserve Claude Max rate limits. Untouched since April; model management has changed shape since, so the April integration points need re-reading before any of this is built.

- [ ] **A summarization model deployed and benchmarked** — 7B on the RTX 4080 against 14B on the A6000, on real project files, for accuracy and speed
- [ ] **The winning model reachable from Claude Code** — mechanism unsettled; the April plan assumed MCP
- [ ] **A summarization skill** — when to offload versus read directly
- [ ] **Measured savings** — Opus turn count and rate-limit utilization, with and without

---

# Tools to Evaluate

Not committed to the plan. **Two categories, not one list:** a comparator either competes with the **backbone** — the orchestration layer — or with **Claude Code**, the runtime inside our edge. Judged on backbone axes an edge runtime fails trivially and teaches nothing, which is why the split exists.

### Backbone comparators

- **Paperclip** — **ASSESSED 2026-08-04, architecture rejected, capabilities mined.** Bespoke Postgres durability rather than Temporal, which conflicts with settled direction. See [`paperclip_assessment.md`](../standards/architecture/research/raw/paperclip_assessment.md). No further evaluation gate.

### Edge runtimes

- **OpenClaw** — **ASSESSED 2026-08-06, architecture rejected, mined heavily.** See [`openclaw_assessment.md`](../standards/architecture/research/raw/openclaw_assessment.md).
- **Hermes Agent** — **ASSESSED 2026-08-06, architecture rejected as a backbone, mined.** See [`hermes_assessment.md`](../standards/architecture/research/raw/hermes_assessment.md).

### Frameworks and libraries

- **Claude Agent SDK** — the framework Claude Code is built on. Worth exploring if automation is ever needed beyond what Claude Code provides natively. Unassessed.

---

**Ideas not committed to anything** live in [`candidates.md`](../standards/architecture/research/candidates.md), not here. A plan file that carries an idea list stops being a plan.

# Roadmap

**What is being built:** a Claude Code environment that improves itself. Custom agents and methodology skills, autonomous workflows that run headless and deliver reviewed PRs, a memory model built on git rather than state files, and a continuous-improvement loop that reads the system's own run logs and feeds findings back as tracked decisions. It syncs to every machine from one repo.

**The arc.** The completed phases built the foundation — sync, safety, agents, and the autonomous workflows themselves. The current work is **decomposition**: breaking monolithic workflows into composable parents and children, so that each boundary is a review boundary and a retry point. That leads to a **typed handoff** between runs, which is what lets a parent route on a child's result in code rather than by parsing prose — and that, in turn, is the prerequisite for porting onto **durable execution**, where a failed leg resumes instead of restarting.

The through-line: *the run that authors work should not be the run that judges it, and a system should be able to tell you what it decided in a form that code can act on.*

---

**What this file is:** the phase list. Each phase carries its milestones as checkboxes and links to a detailed planning doc in [`phases/`](phases/). Nothing else lives here — repo structure, setup and command reference are in [`../../README.md`](../../README.md), [`../guide/deployment.md`](../guide/deployment.md) and [`../guide/operations.md`](../guide/operations.md).

## How to use it

1. **Pick a milestone** from a phase below.
2. **Open its phase doc.** That is where the planning, the task-level checkboxes and the completion criteria live. A phase with no doc yet is not ready to work — writing the doc *is* the planning step.
3. **Work the phase doc** until its boxes are checked and the result is tested.
4. **Then check the box here.** A roadmap checkbox means *shipped and validated*, not *attempted*.

**Phases are named, never numbered**, and headings read `## Phase: <name>`. Numbering made reordering expensive and encoded a sequence that stopped being true. Order reflects rough dependency; **phases are not worked to completion in order**, and moving between them to unblock something is normal.

**A roadmap is never a history lesson.** It states what is built or is going to be built — nothing else. Why a decision was made, what an approach cost, what got abandoned and on what reasoning: all of that belongs in the phase doc. An abandoned item is struck there with its explanation; it does not appear here at all. Retrospective notes in a roadmap turn it into a dumping ground and bury the one thing it exists to show.

**A phase is a folder, not a file.** `phases/<name>/<name>.md` is the phase doc — named for the phase rather than `README.md`, so a tab, a grep hit or a search result identifies itself without its directory. `phases/<name>/research/` holds the evidence that phase's planning cites: `raw/` for the pool, `synthesis.md` for what it means. Research sits *inside* the phase it belongs to, so the plan and the evidence for it are never more than one directory apart and there is no central corpus to hunt through. Research is **non-binding** — a phase doc may cite a pool, never treat one as a decision already made.

**Phase docs are written when a phase is picked up, not in advance.** A detailed plan for work that has not started yet is a guess that ages badly — the same reason skills are written after a methodology has been explained twice.

**Status markers:** ✅ COMPLETE · 🟡 IN PROGRESS · 📋 QUEUED, NEEDS PLANNING · 🔵 NOT SCHEDULED · ⚠️ needs restating

---

## Phase: Explore ~/.claude ✅ COMPLETE

**Phase doc:** [`phases/explore-claude-directory/explore-claude-directory.md`](phases/explore-claude-directory/explore-claude-directory.md)

Mapped what Claude Code stores in `~/.claude/` and classified every path as portable or machine-local, before deciding what to sync.

The directory mixes two very different things: what you *author* — agents, skills, rules, hooks — sitting alongside what Claude Code writes for *itself*, including credentials, session history and per-project state. Getting that split wrong in either direction meant leaking secrets into git or hand-copying config forever. This phase produced the classification every later phase is built on.

- [x] **Every path under `~/.claude/` classified portable or machine-local**

---

## Phase: Cross-Device Sync ✅ COMPLETE

**Phase doc:** [`phases/cross-device-sync/cross-device-sync.md`](phases/cross-device-sync/cross-device-sync.md)

Get the repo deploying to every machine, so everything built later propagates automatically rather than being hand-copied.

One idempotent installer creates seven targeted symlinks from `config/` into `~/.claude/`, touching nothing machine-local. It runs the same way by hand on a VM or unattended via Ansible on a workstation. The criterion that matters is not that the links exist — it is that an agent written on the laptop is live on the VM after a `git pull`, with no further step.

- [x] **`install.sh`** — idempotent installer, verified on laptop, workstation and VM
- [x] **Ansible integration** — `--non-interactive` for unattended runs
- [x] **Seven targeted symlinks** — `settings.json`, `CLAUDE.md`, `agents/`, `commands/`, `hooks/`, `rules/`, `skills/`

---

## Phase: Safety & Guardrails ✅ COMPLETE

**Phase doc:** [`phases/safety-and-guardrails/safety-and-guardrails.md`](phases/safety-and-guardrails/safety-and-guardrails.md)

Make it safe to say yes quickly in interactive mode, and safe to walk away in autonomous mode — two different problems needing two different layers.

Permissions prompt on anything unlisted, so approving in a live session is fast and informed. A `PreToolUse` hook denies known-destructive commands regardless of what the allow list says, catching the case where a broad allow rule accidentally matches something that should never run. The second layer is what makes unattended work possible at all — autonomous dispatches bypass permissions entirely, leaving the hook as the only control still operating.

- [x] **`PreToolUse` → `block-dangerous.sh`** — pattern-denies destructive commands
- [x] **`Stop` → `notify-done.sh`** — desktop notification on completion, skips on headless
- [x] **Two-layer model** — permissions for unlisted commands, hook for known-dangerous ones

---

## Phase: Planning & Agents ✅ COMPLETE

**Phase doc:** [`phases/planning-and-agents/planning-and-agents.md`](phases/planning-and-agents/planning-and-agents.md)

Build the specialists a workflow can dispatch — the actors that plan, review and verify without a human in the loop.

Each agent answers **one question no other agent answers** — narrow lenses rather than one thorough generalist, so a panel dispatched at the same tree returns four distinct results instead of the same finding four times. Everything is read-only unless writing is the job, which is what makes dispatching a whole panel at one worktree safe. None of them fires unless asked; depth is something you reach for, not something that interrupts you.

- [x] **Five specialist agents** — `architect`, `planner`, `code-reviewer`, `test-writer`, `security-auditor`
- [x] **Two-tier strategy** — built-ins for routine work, custom agents on-demand only
- [x] **`/review` and `/best-practices`** slash commands

---

## Phase: Autonomous Execution ✅ COMPLETE

**Phase doc:** [`phases/autonomous-execution/autonomous-execution.md`](phases/autonomous-execution/autonomous-execution.md)

Build the plan → execute → PR pipeline — scripts that run Claude headless in an isolated worktree, review their own output, and deliver a pull request with nobody watching.

A dispatch gets its own git worktree, so a bad run damages nothing outside it, and every run ends at a **pull request** rather than a push — which is what makes running with permissions bypassed acceptable. Each one leaves a JSONL log of everything it did, and those logs are what the improvement loop later reads. Five workflows cover the range from a one-line correction to defining a project from scratch.

- [x] **Foundation validated** — headless mode, worktree isolation, `gh` auth, and the full dispatch → worktree → commit → PR pipeline in one command
- [x] **Five workflows** — `revision`, `revision-major`, `build-phase`, `plan-new`, `plan-revision`
- [x] **`init-project.sh`** — pure bash project scaffolding, zero AI tokens
- [x] **Shared library** — `run_claude`, stream formatter, and common prompt blocks sourced by every workflow
- [x] **Four standards written** — agents, hooks, skills, slash commands, all referenced from `CLAUDE.md`
- [x] **`gh-monitor`** — systemd-timed poller routing `@claude` PR comments to workflows
- [x] **Skills library** — testing, documentation, planning, refactoring and standards methodology, each built when a gap appeared

---

## Phase: Continuous Process Improvement 🟡 IN PROGRESS

**Phase doc:** [`phases/continuous-process-improvement/continuous-process-improvement.md`](phases/continuous-process-improvement/continuous-process-improvement.md)

Make the system improve its own tooling from evidence it generates itself.

**No human gathers the data.** Every dispatch leaves a JSONL log of what it actually did, and every workflow ends by posting a reflection on its own work — friction hit, decisions that could have gone another way, tooling suggestions. Those are two machine-produced records of the same run, and they carry different things: a log shows a file was read seventeen times, the reflection says the guidance was ambiguous. Findings from both reach an explicit ship / defer / reject, ruled by a human — the system observes itself and proposes, it does not modify itself.

- [x] **`review-runs.sh`** — analyses a window of run logs across repos and produces an improvement report
- [x] **`workflow-analyst` agent** and the `workflow-analysis` skill
- [x] **Cross-repo reporting** — centralised with source-repo metadata, so patterns spanning repos are visible
- [x] **Append-only decisions log** — ship / defer / reject, deferrals carrying an explicit watch-criterion
- [x] **Post-Run Reflection** — every workflow posts a decision log and tooling suggestions to its PR
- [x] **`review-pr` mines reflections** — the run's own words are its primary evidence surface
- [ ] **Sweep the reflection channel systematically** — tooling suggestions are written by every run and read opportunistically; nothing sweeps them the way `review-runs.sh` sweeps logs

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

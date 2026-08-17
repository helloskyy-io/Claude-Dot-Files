# Sprint Plan

**What is being built:** a Claude Code environment that improves itself. Custom agents and methodology skills, autonomous workflows that run headless and deliver reviewed PRs, a memory model built on git rather than state files, and a continuous-improvement loop that reads the system's own run logs and feeds findings back as tracked decisions. It syncs to every machine from one repo.

**The arc.** The completed phases built the foundation — sync, safety, agents, and the autonomous workflows themselves. The current work rests on a **typed handoff** between runs — the record that lets a parent route on a child's result in code rather than by parsing prose. On top of it sits **decomposition**: breaking monolithic workflows into composable parents and children, so that each boundary is a review boundary and a retry point. A boundary is only sound once the handoff across it is typed, which is why the handoff comes first even though decomposition is what revealed the need for it. Both are prerequisites for porting onto **durable execution**, where a failed leg resumes instead of restarting.

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

**Every component gets a `roadmap.md` plus numbered `phaseN_<name>.md` files**, in the same folder — including one that only ever has a single phase.

**A phase number is IDENTITY, not order** — it names the phase for life, the way a ticket number does. Order lives in two mutable places instead: the roadmap's ordering within the component, and the sprint file's ordering across components. A phase ships first or last without its filename changing. *(Numbers only impede reordering if they are read AS the order — see Documentation Standard § Sprint Structure for the sprint side, where an ordinal DOES encode a changing judgement and is therefore forbidden.)* This matches `MDC-Master-Planning`'s `development/service/<component>/` shape, so a workflow can find the same artifacts by name in either repo. *(One-phase exception removed 2026-08-13.)*

**A component with no plan yet is UNPLANNED, not non-conformant.** The structure above applies when a component is planned; a folder holding only `research/` is waiting its turn in the plan family, not violating anything.

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

## Sprint: Continuous Process Improvement — ✅ COMPLETE

**Phase doc:** [`continuous-process-improvement/continuous-process-improvement.md`](continuous-process-improvement/continuous-process-improvement.md)

Make the system improve its own tooling from evidence it generates itself.

**No human gathers the data.** Every dispatch leaves a JSONL log of what it actually did, and every workflow ends by posting a reflection on its own work — friction hit, decisions that could have gone another way, tooling suggestions. Those are two machine-produced records of the same run, and they carry different things: a log shows a file was read seventeen times, the reflection says the guidance was ambiguous. Findings from both reach an explicit ship / defer / reject, ruled by a human — the system observes itself and proposes, it does not modify itself.

- [x] **`review-runs.sh`** — analyses a window of run logs across repos and produces an improvement report
- [x] **`workflow-analyst` agent** and the `workflow-analysis` skill
- [x] **Cross-repo reporting** — centralised with source-repo metadata, so patterns spanning repos are visible
- [x] **Append-only decisions log** — ship / defer / reject, deferrals carrying an explicit watch-criterion
- [x] **Post-Run Reflection** — every workflow posts a decision log and tooling suggestions to its PR
- [x] **`review-pr` mines reflections** — the run's own words are its primary evidence surface
- [x] **CLOSED BY TRANSFER — absorbed by [PMP Phase 6](persistent-memory-protocol/phase6_cpi_reads_the_journal.md).** Reflections are pull-request comments, and PMP's emit rule puts *every comment* into the journal. Phase 6 then moves the evidence sweep onto that journal. **Building a comment-scraper here would be replaced by it**, so the requirement is real and the mechanism belongs there.
- [x] **Measure the judge's marginal yield** — `scripts/helpers/measure/judge_marginal_yield.py` classifies every disposition finding as ECHOED by the producing run's own reflection or NEW to the judge, and prints its denominator and its own limit. **Roughly half are NEW, and the lexical matching biases that UPWARD — so it is an upper bound.** The separate pass earns its cost. Answered 2026-08-16; figures are the tool's, deliberately not restated here.

---

## Sprint: Memory Management Framework — ✅ COMPLETE

**Planning:** [`memory-management-framework/roadmap.md`](memory-management-framework/roadmap.md) — roadmap + 6 phase docs, kept as the record of what was built.

**Retired into the [Persistent Memory Protocol](persistent-memory-protocol/roadmap.md)**, which now covers all of memory. The typed exit record is PMP's.

Two distinct kinds of memory, both built. Both exist because a context window ends and the work does not; they differ in who reads them.

**Kind 1 — durable memory in git, read by humans and AI.** Built and in use; **documented as a framework by Phase 2**. **Five** surfaces, measured: PR threads carry change-outcomes, Issues carry no-change outcomes, the standup tracker carries continuity, `direction.md` carries rulings only the operator can make, and `candidates.md` carries research candidates and their dispositions — the last of these being what makes `direction.md`'s 90-day rotation safe, since a ruled row may only be deleted once its reasoning is recorded in the candidate that never deletes. The record's own to-do bit is what marks work as current.

**Kind 2 — machine handoff in a file, read by CODE.** The typed exit record: a parent decides *in code, with no AI in the loop*, which child to invoke next. Now PMP's.

- [x] **Phase 1 · Measure the channel** — six experiments against the pinned CLI and the archived logs. 13 rulings; 3 no-ops cancelled downstream work. Merged 2026-08-08
- [x] **Phase 2 · Document Kind 1 as a framework** — delivered as [`docs/guide/memory-model.md`](../guide/memory-model.md). Five surfaces measured, not three. Merged 2026-08-09
- [x] **Phase 3 · The typed exit record** — envelope, split abstention (*could-not-check* vs *needs-a-ruling*), fail-safe contract, proven on one parent/child pair. Transport measured: `structured_output`
- [x] **Phase 4 · Migrate the fleet** — every V2 child emits it, no parent parses prose. Bash is frozen and out of scope by decision
- [x] **Phase 5 · Convergence-based stopping** — computed over the **open** finding set, stopping when it is *empty* rather than unchanged — built, not gating
- [x] **Phase 6 · Read what it writes** — three readers for the run log's parent-written observables

Evidence, prior art and the plateau correction: [`cpi-decisions.md`](cpi-decisions.md) (2026-08-17), which salvaged them from the deleted burn-test intake

## Sprint: Workflow Decomposition — 🟡 IN PROGRESS

**Planning:** [`workflow-decomposition/roadmap.md`](workflow-decomposition/roadmap.md) — four phases. Written after Phase 1 shipped; that phase's boxes are a record, the rest are planning.

Taking apart the long-running workflows that already existed, so each boundary is a retry/resume point and children become recombinable rather than copied. **Building the ones that do not exist yet is [Assistant Workflow Design](#sprint-assistant-workflow-design--🔵-not-scheduled-needs-research-then-planning).**

- [x] **Phase 1 · Decompose the build families and codify the shape** — draft/refine/review-pr, the activities layer, and the composition contract written down
- [ ] **Phase 2 · Family alignment** — children in a family do not diverge except where they need to. Mechanism and standard shipped; the fleet backlog and the drifted-copy ruling remain
- [ ] **Phase 3 · The invocation contract** — a workflow derives what it needs from how it was called: dual-mode children, scope from the target, centrally managed config

## Sprint: Persistent Memory Protocol — Part 1 — 🟡 IN PROGRESS

**Planning:** [`persistent-memory-protocol/roadmap.md`](persistent-memory-protocol/roadmap.md) — roadmap plus eight phase docs. Part 2 below is phases 5–8.

All of memory in this fleet — the framework and the protocol. Every run writes a folder; the folder is the truth, and every other store is rebuilt from it. Phases 1–4 have no external gate and depend only on each other.

- [ ] **Phase 1 · The journal root and the run bag** — one configurable root per machine, one folder per run keyed by `run_id`, a valid BagIt bag with a manifest a validator re-checksums
- [ ] **Phase 2 · The content store** — every cited artifact stored by checksum, and a `verify` that resolves every citation with the network disabled
- [ ] **Phase 3 · The emit rule** — every write path emits the authored content verbatim with the destination as a field; a failed journal write is never silent
- [ ] **Phase 4 · Rebuildability is a test** — replay reproduces `candidates.md` and `direction.md`; deleting one emit makes the test fail

## Sprint: Temporal Integration — 🟡 IN PROGRESS

**Phase doc:** [`temporal-integration/temporal-integration.md`](temporal-integration/temporal-integration.md)

The port to durable execution, in three stages: convert the fleet to Python, wrap it as activities, then orchestrate. **Gated on Workflow Decomposition and the Memory Management Framework** — Temporal buys durability and resumability, not composition, and porting before the shape settles means porting a shape we are still changing.

- [x] **Stage A — the Python tree** — `scripts/workflows/temporal/`, parent/child modules with a CLI entrypoint, no Temporal runtime
- [x] **V1 parity suite** — the Python fleet checked against the bash one it replaces
- [ ] **A `claude_cli` activity domain** — heartbeating for 10–60 minute runs, transcript-to-file for payload limits. The genuinely new work; the rest is a port
- [ ] **Port `review-runs`** — the CPI log sweep, the one of the four with a live role and a run history
- [ ] **Rule on `plan-new` and `review-sprint`** — 1,228 lines between them and **neither has ever executed**; decide whether they die with the bash fleet or earn a port
- [ ] **Stand up the Temporal server** — Postgres-backed, on the VM that gets backed up
- [ ] **A restart-recovery contract** — a durable dispatch id and per-subsystem recovery, designed once. Retrofitting one onto running workers is a rewrite, so it lands with them rather than after
- [ ] **Rule the retry boundary before wrapping anything** — Temporal retries an ACTIVITY, and `gh()` gained its own bounded retry for transient outages (PR #101). Nesting them multiplies: 3 activity attempts × 3 call attempts is 9, which turns a brief outage into a long stall. Decide which layer owns it, and carry the transient-vs-terminal classification into `non_retryable_error_types` rather than re-deriving it — Temporal's default retries almost everything, including a `404`. **`preflight` is outside this and stays outside**: it runs before any workflow exists, so no retry policy can reach it
- [ ] **Stage B — semantic wrappers** — `@activity.defn` over the plain functions from Stage A
- [ ] **Stage C — orchestrate** — workflows compose the wrappers; schedules replace timers

---

## Sprint: Persistent Memory Protocol — Part 2 — 📋 QUEUED, GATED

**Planning:** [`persistent-memory-protocol/roadmap.md`](persistent-memory-protocol/roadmap.md) — same component, same eight phase docs. Part 1 above is phases 1–4.

The four phases that wait on something that does not exist yet.

- [ ] **Phase 5 · Snapshots, then retention** — the 1 GB budget governs the whole journal with nothing exempt. *Gate: the Temporal server, for the recurring half only*
- [ ] **Phase 6 · CPI reads the journal** — moves the continuous-improvement evidence sweep off comment-scraping. *Gate: **Port `review-runs`**, a Temporal Integration milestone — **not** the server*
- [ ] **Phase 7 · Cross-machine aggregation** — write locally first, ship bags to a bucket per edge. *Gate: a second machine that actually produces runs — unrelated to Temporal*
- [ ] **Phase 8 · The poller** — reads a to-do bit and starts work with no human trigger. *Gate: Temporal schedules, and a retention rule so it is not walking an unbounded tree*

**Phase 6 can be pulled forward** — it needs the `review-runs` port, not the server.

## Sprint: Assistant Workflow Design — 🔵 NOT SCHEDULED, NEEDS RESEARCH THEN PLANNING

**Planning:** not yet written. Research first — this component's whole failure mode is building children nobody sized.

**Named for `modules/assistant/`, which is where every one of these lives.** Decomposition takes apart what already existed; this designs, builds and trains what does not. **A long-running component: it gains phases as the fleet gains capabilities, and those phases land in much later sprints while staying this feature.**

- [ ] **The roster** — what every parent and child IS and what it DOES, as one readable catalog. The set is currently knowable only by reading the tree
- [ ] **"No god workflows" as an actual rule** — what a single workflow may not do, stated so it can be checked
- [ ] **Marketing children** — viability, target audience, opportunities. A loop that revises the *problem statement* rather than building against it: who has this problem, how common is it, can the solution be sold
- [ ] **Research-children training** — getting a research cycle to produce what was actually wanted, at accuracy. **The prerequisite to [Self Improvement](#sprint-self-improvement--🔵-not-scheduled-needs-research-then-planning), not part of it**
- [ ] **Chain `plan-verify` into `plan-project`** — it exists as a child and appears in all three planning scenarios, and nothing calls it

## Sprint: Self Improvement — 🔵 NOT SCHEDULED, NEEDS RESEARCH THEN PLANNING

**Planning:** not yet written. Research comes first — this is a measurement problem before it is a training problem.

Making a child better at its job, measured rather than asserted. Today a child's performance is scattered across pull-request comments and log files nothing reads, so there is no baseline to improve against and no way to tell an improvement from a good day.

**Training the children is NOT here** — that is [Assistant Workflow Design](#sprint-assistant-workflow-design--🔵-not-scheduled-needs-research-then-planning), and it is the prerequisite. This component is the system improving itself, which presupposes children that already work.

**Gated on the journal.** [PMP](persistent-memory-protocol/roadmap.md) Part 1 gives runs a durable record; [Phase 6](persistent-memory-protocol/phase6_cpi_reads_the_journal.md) is what reads it back. Until a child's behaviour is measurable across runs, training is guesswork with a confident voice.

**It sits in front of [Autonomous Operation](#sprint-autonomous-operation--🔵-not-scheduled)** because a loop that dispatches its own work amplifies whatever the children already do — well or badly. Improving them first is cheaper than supervising them later.

- [ ] **Measure a child's performance** — what a good run looks like, derived from the journal rather than declared
- [ ] **Decide what generalises** — whether the method transfers to other children or only fit the first one

## Sprint: Autonomous Operation — 🔵 NOT SCHEDULED

**Phase doc:** [`autonomous-operation/autonomous-operation.md`](autonomous-operation/autonomous-operation.md) — shape notes, deliberately not a plan

The tier above parents: a driver that composes **parents** into a loop that keeps going, choosing each next dispatch from persisted state rather than a script written in advance. **Gated on Temporal Integration.** Distinct from *Autonomous Execution* above, which built the workflows themselves.

- [ ] **A driver that dispatches from persisted state** — the payoff of the Memory Management Framework
- [ ] **Observable exit criteria** — a `HOLD`, a convergence signal, a budget ceiling. Not a turn count. **Includes the three-legged liveness predicate** — stalled, looping and stranded detected separately, since a driver that keeps going needs to know which of the three it is in
- [ ] **A blocked-work notifier** — the one channel that reaches a human when work is blocked, and an inbox the operator reads rather than a dashboard nobody opens
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

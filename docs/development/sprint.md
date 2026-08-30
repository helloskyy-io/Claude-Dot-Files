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

**Status markers, and each is DERIVED rather than typed** — the state follows from the items below it, so a marker that disagrees with its own checkboxes is a defect:

| Marker | Means | Placed by | Derived as |
|---|---|---|---|
| 🔵 NOT SCHEDULED | no plan exists | scaffolding | no phase-linked item |
| 🟠 PLANNED | planned, not started | `plan-sprint` | phase-linked items, none checked |
| 🟡 IN PROGRESS | under way | the first checked box | some checked, not all |
| ✅ COMPLETE | delivered | sprint close-out | every item checked |

---

## Sprint: Explore ~/.claude

✅ COMPLETE

Mapped what Claude Code stores in `~/.claude/` and classified every path as portable or machine-local, before deciding what to sync.

The directory mixes two very different things: what you *author* — agents, skills, rules, hooks — sitting alongside what Claude Code writes for *itself*, including credentials, session history and per-project state. Getting that split wrong in either direction meant leaking secrets into git or hand-copying config forever. This phase produced the classification every later phase is built on.

- [x] **Explore ~/.claude · Every path under `~/.claude/` classified portable or machine-local** · ([doc](explore-claude-directory/explore-claude-directory.md))

---

## Sprint: Cross-Device Sync

✅ COMPLETE

Get the repo deploying to every machine, so everything built later propagates automatically rather than being hand-copied.

One idempotent installer creates seven targeted symlinks from `config/` into `~/.claude/`, touching nothing machine-local. It runs the same way by hand on a VM or unattended via Ansible on a workstation. The criterion that matters is not that the links exist — it is that an agent written on the laptop is live on the VM after a `git pull`, with no further step.

- [x] **Cross-Device Sync · `install.sh`** · ([doc](cross-device-sync/cross-device-sync.md)) — idempotent installer, verified on laptop, workstation and VM
- [x] **Cross-Device Sync · Ansible integration** · ([doc](cross-device-sync/cross-device-sync.md)) — `--non-interactive` for unattended runs
- [x] **Cross-Device Sync · Seven targeted symlinks** · ([doc](cross-device-sync/cross-device-sync.md)) — `settings.json`, `CLAUDE.md`, `agents/`, `commands/`, `hooks/`, `rules/`, `skills/`

---

## Sprint: Safety & Guardrails

✅ COMPLETE

Make it safe to say yes quickly in interactive mode, and safe to walk away in autonomous mode — two different problems needing two different layers.

Permissions prompt on anything unlisted, so approving in a live session is fast and informed. A `PreToolUse` hook denies known-destructive commands regardless of what the allow list says, catching the case where a broad allow rule accidentally matches something that should never run. The second layer is what makes unattended work possible at all — autonomous dispatches bypass permissions entirely, leaving the hook as the only control still operating.

- [x] **Safety & Guardrails · `PreToolUse` → `block-dangerous.sh`** · ([doc](safety-and-guardrails/safety-and-guardrails.md)) — pattern-denies destructive commands
- [x] **Safety & Guardrails · `Stop` → `notify-done.sh`** · ([doc](safety-and-guardrails/safety-and-guardrails.md)) — desktop notification on completion, skips on headless
- [x] **Safety & Guardrails · Two-layer model** · ([doc](safety-and-guardrails/safety-and-guardrails.md)) — permissions for unlisted commands, hook for known-dangerous ones

---

## Sprint: Planning & Agents

✅ COMPLETE

Build the specialists a workflow can dispatch — the actors that plan, review and verify without a human in the loop.

Each agent answers **one question no other agent answers** — narrow lenses rather than one thorough generalist, so a panel dispatched at the same tree returns four distinct results instead of the same finding four times. Everything is read-only unless writing is the job, which is what makes dispatching a whole panel at one worktree safe. None of them fires unless asked; depth is something you reach for, not something that interrupts you.

- [x] **Planning & Agents · Five specialist agents** · ([doc](planning-and-agents/planning-and-agents.md)) — `architect`, `planner`, `code-reviewer`, `test-writer`, `security-auditor`
- [x] **Planning & Agents · Two-tier strategy** · ([doc](planning-and-agents/planning-and-agents.md)) — built-ins for routine work, custom agents on-demand only
- [x] **Planning & Agents · `/review` and `/best-practices` slash commands** · ([doc](planning-and-agents/planning-and-agents.md))

---

## Sprint: Autonomous Execution

✅ COMPLETE

Build the plan → execute → PR pipeline — scripts that run Claude headless in an isolated worktree, review their own output, and deliver a pull request with nobody watching.

A dispatch gets its own git worktree, so a bad run damages nothing outside it, and every run ends at a **pull request** rather than a push — which is what makes running with permissions bypassed acceptable. Each one leaves a JSONL log of everything it did, and those logs are what the improvement loop later reads. Five workflows cover the range from a one-line correction to defining a project from scratch.

- [x] **Autonomous Execution · Foundation validated** · ([doc](autonomous-execution/autonomous-execution.md)) — headless mode, worktree isolation, `gh` auth, and the full dispatch → worktree → commit → PR pipeline in one command
- [x] **Autonomous Execution · Five workflows** · ([doc](autonomous-execution/autonomous-execution.md)) — `build`, `build-minor`, `build-phase`, `plan-new`, `plan-revision`
- [x] **Autonomous Execution · `init-project.sh`** · ([doc](autonomous-execution/autonomous-execution.md)) — pure bash project scaffolding, zero AI tokens
- [x] **Autonomous Execution · Shared library** · ([doc](autonomous-execution/autonomous-execution.md)) — `run_claude`, stream formatter, and common prompt blocks sourced by every workflow
- [x] **Autonomous Execution · Four standards written** · ([doc](autonomous-execution/autonomous-execution.md)) — agents, hooks, skills, slash commands, all referenced from `CLAUDE.md`
- [x] **Autonomous Execution · `gh-monitor`** · ([doc](autonomous-execution/autonomous-execution.md)) — systemd-timed poller routing `@claude` PR comments to workflows
- [x] **Autonomous Execution · Skills library** · ([doc](autonomous-execution/autonomous-execution.md)) — testing, documentation, planning, refactoring and standards methodology, each built when a gap appeared

---

## Sprint: Continuous Process Improvement

✅ COMPLETE

Make the system improve its own tooling from evidence it generates itself.

**No human gathers the data.** Every dispatch leaves a JSONL log of what it actually did, and every workflow ends by posting a reflection on its own work — friction hit, decisions that could have gone another way, tooling suggestions. Those are two machine-produced records of the same run, and they carry different things: a log shows a file was read seventeen times, the reflection says the guidance was ambiguous. Findings from both reach an explicit ship / defer / reject, ruled by a human — the system observes itself and proposes, it does not modify itself.

- [x] **Continuous Process Improvement · `review-runs.sh`** · ([doc](continuous-process-improvement/continuous-process-improvement.md)) — analyses a window of run logs across repos and produces an improvement report
- [x] **Continuous Process Improvement · `workflow-analyst` agent and the `workflow-analysis` skill** · ([doc](continuous-process-improvement/continuous-process-improvement.md))
- [x] **Continuous Process Improvement · Cross-repo reporting** · ([doc](continuous-process-improvement/continuous-process-improvement.md)) — centralised with source-repo metadata, so patterns spanning repos are visible
- [x] **Continuous Process Improvement · Append-only decisions log** · ([doc](continuous-process-improvement/continuous-process-improvement.md)) — ship / defer / reject, deferrals carrying an explicit watch-criterion
- [x] **Continuous Process Improvement · Post-Run Reflection** · ([doc](continuous-process-improvement/continuous-process-improvement.md)) — every workflow posts a decision log and tooling suggestions to its PR
- [x] **Continuous Process Improvement · `review-pr` mines reflections** · ([doc](continuous-process-improvement/continuous-process-improvement.md)) — the run's own words are its primary evidence surface
- [x] **Continuous Process Improvement · Measure the judge's marginal yield** · ([doc](continuous-process-improvement/continuous-process-improvement.md)) — `scripts/helpers/measure/judge_marginal_yield.py`; the tool prints its own figures

---

## Sprint: Memory Management Framework

✅ COMPLETE · (~124h total · ~0h to-do)

**Future memory work is covered by the [Persistent Memory Protocol](persistent-memory-protocol/roadmap.md)**, which carries the obligations this component handed forward. The typed exit record is PMP's.

Two distinct kinds of memory, both built. Both exist because a context window ends and the work does not; they differ in who reads them.

**Kind 1 — durable memory in git, read by humans and AI.** Built and in use; **documented as a framework by Phase 2**. **One API surface and four file surfaces:** PR threads carry change-outcomes, and the four [`tracked/`](../../tracked/) stores carry defects, continuity, proposals and standards amendments — one file per item, the `status:` field as the to-do bit. *(Phase 2 shipped against five surfaces including two markdown tables; the substrate was rebound on 2026-08-26 and the properties did not move.)* The record's own to-do bit is what marks work as current.

**Kind 2 — machine handoff in a file, read by CODE.** The typed exit record: a parent decides *in code, with no AI in the loop*, which child to invoke next. Now PMP's.

- [x] **Memory Management Framework · Measure the channel** · ([roadmap](memory-management-framework/roadmap.md) · [phase](memory-management-framework/phase1_measure_the_channel.md)) — six experiments against the pinned CLI and the archived logs. 13 rulings; 3 no-ops cancelled downstream work. Merged 2026-08-08
- [x] **Memory Management Framework · Document Kind 1 as a framework** · ([roadmap](memory-management-framework/roadmap.md) · [phase](memory-management-framework/phase2_kind1_framework.md)) — delivered as [`docs/guide/memory-model.md`](../guide/memory-model.md). Five surfaces measured, not three. Merged 2026-08-09
- [x] **Memory Management Framework · The typed exit record** · ([roadmap](memory-management-framework/roadmap.md) · [phase](memory-management-framework/phase3_typed_exit_record.md)) — envelope, split abstention (*could-not-check* vs *needs-a-ruling*), fail-safe contract, proven on one parent/child pair. Transport measured: `structured_output`
- [x] **Memory Management Framework · Migrate the fleet** · ([roadmap](memory-management-framework/roadmap.md) · [phase](memory-management-framework/phase4_fleet_migration.md)) — every V2 child emits it, no parent parses prose. Bash is frozen and out of scope by decision
- [x] **Memory Management Framework · Convergence-based stopping** · ([roadmap](memory-management-framework/roadmap.md) · [phase](memory-management-framework/phase5_convergence_stopping.md)) — computed over the **open** finding set, stopping when it is *empty* rather than unchanged — built, not gating
- [x] **Memory Management Framework · Read what it writes** · ([roadmap](memory-management-framework/roadmap.md) · [phase](memory-management-framework/phase6_read_what_it_writes.md)) — three readers for the run log's parent-written observables
- [x] **Sprint close-out** · ([checks](close_out/sprint_end_recurring.md)) — recurring checks run for this sprint and every finding dispositioned (fixed / rejected-with-reasoning / placed); no open issue belongs to this sprint's work

Evidence, prior art and the plateau correction: [`cpi-decisions.md`](cpi-decisions.md) (2026-08-17), which salvaged them from the deleted burn-test intake

## Sprint: Workflow Decomposition

🟡 IN PROGRESS · (~182h total · ~118h to-do)

Taking apart the long-running workflows that already existed, so each boundary is a retry/resume point and children become recombinable rather than copied. **Building the ones that do not exist yet is [Assistant Workflow Design](#sprint-assistant-workflow-design).**

- [x] **Workflow Decomposition · Decompose the build families and codify the shape** · ([roadmap](workflow-decomposition/roadmap.md)) — draft/refine/review-pr, the activities layer, and the composition contract written down
- [x] **Workflow Decomposition · Family alignment** · ([roadmap](workflow-decomposition/roadmap.md) · [phase](workflow-decomposition/phase2_family_alignment.md)) — children in a family do not diverge except where they need to. Mechanism, standard, fleet backlog and the drifted-copy ruling all shipped; the ruling procedure scored κ = 0.000 in its own blind trial, which *Dual-mode children* inherits as an open question
- [ ] **Workflow Decomposition · Nothing a run relies on is invisible** · ([roadmap](workflow-decomposition/roadmap.md) · [phase](workflow-decomposition/phase4_nothing_invisible.md)) — a run's derived values on ONE frozen object, constructed once at the dispatch boundary and passed down, stated on the live path before the first side effect, and a wrong derivation demonstrated visible
- [ ] **Workflow Decomposition · Dual-mode children** · ([roadmap](workflow-decomposition/roadmap.md) · [phase](workflow-decomposition/phase3_dual_mode_children.md)) — the six children that cannot be started by a person get a runner of their own, each proven running alone
- [ ] **Workflow Decomposition · What configuration a run absorbed** · ([roadmap](workflow-decomposition/roadmap.md) · [phase](workflow-decomposition/phase5_configuration_a_run_absorbed.md)) — a sixth `Journal-` tag digesting the config a run ran under, and the reader that answers whether two runs used the same configuration
- [ ] **Workflow Decomposition · Every producer names its consumer** · ([roadmap](workflow-decomposition/roadmap.md) · [phase](workflow-decomposition/phase6_every_producer_names_its_consumer.md)) — what counts as a producer defined with its exclusions named, and the producer-with-no-consumer gate extended beyond one directory with its population read off disk
- [ ] **Workflow Decomposition · Managed configuration, and whose tier wins** · ([roadmap](workflow-decomposition/roadmap.md)) — gated on *What configuration a run absorbed* for both its digest evidence and its Managed-tier measurement, plus an operator ruling on precedence direction and an unresearched buy-versus-build question. No phase doc by design
- [ ] **Sprint close-out** · ([checks](close_out/sprint_end_recurring.md)) — recurring checks run for this sprint and every finding dispositioned (fixed / rejected-with-reasoning / placed); no open issue belongs to this sprint's work

## Sprint: Persistent Memory Protocol — Part 1

🟡 IN PROGRESS · (~183h total · ~147h to-do)

All of memory in this fleet — the framework and the protocol. Every run writes a folder; the folder is the truth, and every other store is rebuilt from it. The phases in this part have no external gate and depend only on each other. **One run, one identity** builds second, straight after the run bag, and ahead of the content store. Across both parts the component is ~297h total, ~261h to-do.

- [x] **Persistent Memory Protocol · The journal root and the run bag** · ([roadmap](persistent-memory-protocol/roadmap.md) · [phase](persistent-memory-protocol/phase1_the_run_bag.md)) — one configurable root per machine, one folder per run keyed by `run_id`, a valid BagIt bag with a manifest a validator re-checksums
- [ ] **Persistent Memory Protocol · One run, one identity** · ([roadmap](persistent-memory-protocol/roadmap.md) · [phase](persistent-memory-protocol/phase9_one_run_one_identity.md)) — one authority names a run, the name is handed TO the journal rather than made by it, and every shape an invocation can take resolves to one bag under one name
- [ ] **Persistent Memory Protocol · The content store** · ([roadmap](persistent-memory-protocol/roadmap.md) · [phase](persistent-memory-protocol/phase2_content_store.md)) — every cited artifact stored by checksum, and a `verify` that resolves every citation with the network disabled
- [ ] **Persistent Memory Protocol · The emit rule** · ([roadmap](persistent-memory-protocol/roadmap.md) · [phase](persistent-memory-protocol/phase3_the_emit_rule.md)) — every write path emits the authored content verbatim with the destination as a field; a failed journal write is never silent
- [ ] **Persistent Memory Protocol · The model-issued harvest** · ([roadmap](persistent-memory-protocol/roadmap.md) · [phase](persistent-memory-protocol/phase10_the_model_issued_harvest.md)) — what a run wrote to its GitHub surfaces after it exits, fetched by run id and emitted verbatim, with a standing check that goes red when the harvest is disabled
- [ ] **Persistent Memory Protocol · Rebuildability is a test** · ([roadmap](persistent-memory-protocol/roadmap.md) · [phase](persistent-memory-protocol/phase4_rebuild_is_a_test.md)) — replay reproduces the `tracked/` stores; deleting one emit makes the test fail
- [ ] **Sprint close-out** · ([checks](close_out/sprint_end_recurring.md)) — recurring checks run for this sprint and every finding dispositioned (fixed / rejected-with-reasoning / placed); no open issue belongs to this sprint's work

## Sprint: Temporal Integration

🟠 PLANNED · (~193h total · ~193h to-do)

The port to durable execution. Phases are listed in BUILD order, which is not their numeric order — `review-runs` was split out late and lands between the retry boundary and the `claude_cli` domain.

- [ ] **Temporal Integration · The starter control plane** · ([roadmap](temporal-integration/roadmap.md) · [phase](temporal-integration/phase1_the_starter_control_plane.md))
- [ ] **Temporal Integration · Durable dispatch identity, and the recovery contract** · ([roadmap](temporal-integration/roadmap.md) · [phase](temporal-integration/phase2_durable_dispatch_identity.md))
- [ ] **Temporal Integration · The retry boundary, and a `gh` failure that carries its own verdict** · ([roadmap](temporal-integration/roadmap.md) · [phase](temporal-integration/phase3_the_retry_boundary.md))
- [ ] **Temporal Integration · `review-runs`, written in the Python tree** · ([roadmap](temporal-integration/roadmap.md) · [phase](temporal-integration/phase9_review_runs_in_the_python_tree.md))
- [ ] **Temporal Integration · The `claude_cli` activity domain** · ([roadmap](temporal-integration/roadmap.md) · [phase](temporal-integration/phase4_the_claude_cli_activity.md))
- [ ] **Temporal Integration · The first dispatch, end to end** · ([roadmap](temporal-integration/roadmap.md) · [phase](temporal-integration/phase5_the_first_dispatch.md))
- [ ] **Temporal Integration · The rest of the fleet, and the two that never ran** · ([roadmap](temporal-integration/roadmap.md) · [phase](temporal-integration/phase6_the_rest_of_the_fleet.md))
- [ ] **Temporal Integration · The three-node cluster** · ([roadmap](temporal-integration/roadmap.md)) — gated; inherited from MDC when its procedure exists. No phase doc by design
- [ ] **Temporal Integration · The pivot, and the starter is destroyed** · ([roadmap](temporal-integration/roadmap.md)) — gated; the upstream procedure does not exist yet. No phase doc by design
- [ ] **Sprint close-out** · ([checks](close_out/sprint_end_recurring.md)) — recurring checks run for this sprint and every finding dispositioned (fixed / rejected-with-reasoning / placed); no open issue belongs to this sprint's work

## Sprint: Persistent Memory Protocol — Part 2

🟠 PLANNED · (~114h total · ~114h to-do)

The four phases that wait on something that does not exist yet.

- [ ] **Persistent Memory Protocol · Snapshots, then retention** · ([roadmap](persistent-memory-protocol/roadmap.md) · [phase](persistent-memory-protocol/phase5_snapshots_then_retention.md)) — the 1 GB budget governs the whole journal with nothing exempt. *Gate: the Temporal server, for the recurring half only*
- [ ] **Persistent Memory Protocol · CPI reads the journal** · ([roadmap](persistent-memory-protocol/roadmap.md) · [phase](persistent-memory-protocol/phase6_cpi_reads_the_journal.md)) — moves the continuous-improvement evidence sweep off comment-scraping. *Gate: **Port `review-runs`**, a Temporal Integration milestone — **not** the server*
- [ ] **Persistent Memory Protocol · Cross-machine aggregation** · ([roadmap](persistent-memory-protocol/roadmap.md) · [phase](persistent-memory-protocol/phase7_s3_aggregation.md)) — write locally first, ship bags to a bucket per edge. *Gate: a second machine that actually produces runs — unrelated to Temporal*
- [ ] **Persistent Memory Protocol · The poller** · ([roadmap](persistent-memory-protocol/roadmap.md) · [phase](persistent-memory-protocol/phase8_the_poller.md)) — reads a to-do bit and starts work with no human trigger. *Gate: Temporal schedules, and a retention rule so it is not walking an unbounded tree*
- [ ] **Sprint close-out** · ([checks](close_out/sprint_end_recurring.md)) — recurring checks run for this sprint and every finding dispositioned (fixed / rejected-with-reasoning / placed); no open issue belongs to this sprint's work

**Phase 6 can be pulled forward** — it needs the `review-runs` port, not the server.

## Sprint: Assistant Workflow Design

🔵 NOT SCHEDULED

**Named for `modules/assistant/`, which is where every one of these lives.** Decomposition takes apart what already existed; this designs, builds and trains what does not. **A long-running component: it gains phases as the fleet gains capabilities, and those phases land in much later sprints while staying this feature.**

- [ ] **The roster** — what every parent and child IS and what it DOES, as one readable catalog. The set is currently knowable only by reading the tree
- [ ] **The conditions under which a god-like workflow becomes possible** — long chains with no human behind each parent are the eventual goal, not a prohibition. They are blocked today by child performance, not by design: HiL is load-bearing because the children need it. Name what has to be true — accuracy, measured — before review stops being the thing holding a chain together. Gated on [Self Improvement](#sprint-self-improvement)
- [ ] **Marketing children** — viability, target audience, opportunities. A loop that revises the *problem statement* rather than building against it: who has this problem, how common is it, can the solution be sold
- [ ] **Research-children training** — getting a research cycle to produce what was actually wanted, at accuracy. **The prerequisite to [Self Improvement](#sprint-self-improvement), not part of it**
- [ ] **Chain `plan-verify` into `plan-project`** — it exists as a child and appears in all three planning scenarios, and nothing calls it
- [ ] **Sprint close-out** · ([checks](close_out/sprint_end_recurring.md)) — recurring checks run for this sprint and every finding dispositioned (fixed / rejected-with-reasoning / placed); no open issue belongs to this sprint's work

## Sprint: Self Improvement

🔵 NOT SCHEDULED

Making a child better at its job, measured rather than asserted. Today a child's performance is scattered across pull-request comments and log files nothing reads, so there is no baseline to improve against and no way to tell an improvement from a good day.

**Training the children is NOT here** — that is [Assistant Workflow Design](#sprint-assistant-workflow-design), and it is the prerequisite. This component is the system improving itself, which presupposes children that already work.

**Gated on the journal.** [PMP](persistent-memory-protocol/roadmap.md) Part 1 gives runs a durable record; [Phase 6](persistent-memory-protocol/phase6_cpi_reads_the_journal.md) is what reads it back. Until a child's behaviour is measurable across runs, training is guesswork with a confident voice.

**It sits in front of [Autonomous Operation](#sprint-autonomous-operation)** because a loop that dispatches its own work amplifies whatever the children already do — well or badly. Improving them first is cheaper than supervising them later.

- [ ] **Measure a child's performance** — what a good run looks like, derived from the journal rather than declared
- [ ] **Decide what generalises** — whether the method transfers to other children or only fit the first one
- [ ] **Sprint close-out** · ([checks](close_out/sprint_end_recurring.md)) — recurring checks run for this sprint and every finding dispositioned (fixed / rejected-with-reasoning / placed); no open issue belongs to this sprint's work

## Sprint: Autonomous Operation

🔵 NOT SCHEDULED

The tier above parents: a driver that composes **parents** into a loop that keeps going, choosing each next dispatch from persisted state rather than a script written in advance. **Gated on Temporal Integration.** Distinct from *Autonomous Execution* above, which built the workflows themselves.

- [ ] **Autonomous Operation · A driver that dispatches from persisted state** · ([doc](autonomous-operation/autonomous-operation.md)) — the payoff of the Memory Management Framework
- [ ] **Autonomous Operation · Observable exit criteria** · ([doc](autonomous-operation/autonomous-operation.md)) — a `HOLD`, a convergence signal, a budget ceiling. Not a turn count. **Includes the three-legged liveness predicate** — stalled, looping and stranded detected separately, since a driver that keeps going needs to know which of the three it is in
- [ ] **Autonomous Operation · A blocked-work notifier** · ([doc](autonomous-operation/autonomous-operation.md)) — the one channel that reaches a human when work is blocked, and an inbox the operator reads rather than a dashboard nobody opens
- [ ] **Autonomous Operation · Scheduled dispatch on Temporal schedules** · ([doc](autonomous-operation/autonomous-operation.md)) — off `claude schedule` and systemd timers, so a schedule survives the machine being off
- [ ] **Autonomous Operation · Catch-up behaviour per schedule** · ([doc](autonomous-operation/autonomous-operation.md)) — decided by the window-scoped vs state-converging split in the phase doc
- [ ] **Sprint close-out** · ([checks](close_out/sprint_end_recurring.md)) — recurring checks run for this sprint and every finding dispositioned (fixed / rejected-with-reasoning / placed); no open issue belongs to this sprint's work

---

## Sprint: MCP Servers

🔵 NOT SCHEDULED

Extend Claude's reach to external tools and APIs. Untouched since April and nothing depends on it — revisit when a concrete need appears rather than on a calendar.

- [ ] **MCP Servers · A `.mcp.json` template** · ([doc](mcp-servers/mcp-servers.md)) — project-level config committed to git, secrets via `${env:VAR_NAME}`
- [ ] **MCP Servers · One or two stack-specific servers** · ([doc](mcp-servers/mcp-servers.md)) — chosen against daily workflow, added one at a time
- [ ] **MCP Servers · Setup documentation** · ([doc](mcp-servers/mcp-servers.md)) — adding tokens locally, verifying with `claude mcp list`
- [ ] **Sprint close-out** · ([checks](close_out/sprint_end_recurring.md)) — recurring checks run for this sprint and every finding dispositioned (fixed / rejected-with-reasoning / placed); no open issue belongs to this sprint's work

---

## Sprint: Local AI Offloading

🔵 NOT SCHEDULED

Offload mechanical work — file summarization, classification, boilerplate — to local GPU hardware, to preserve Claude Max rate limits. Untouched since April; model management has changed shape since, so the April integration points need re-reading before any of this is built.

- [ ] **Local AI Offloading · A summarization model deployed and benchmarked** · ([doc](local-ai-offloading/local-ai-offloading.md)) — 7B on the RTX 4080 against 14B on the A6000, on real project files, for accuracy and speed
- [ ] **Local AI Offloading · The winning model reachable from Claude Code** · ([doc](local-ai-offloading/local-ai-offloading.md)) — mechanism unsettled; the April plan assumed MCP
- [ ] **Local AI Offloading · A summarization skill** · ([doc](local-ai-offloading/local-ai-offloading.md)) — when to offload versus read directly
- [ ] **Local AI Offloading · Measured savings** · ([doc](local-ai-offloading/local-ai-offloading.md)) — Opus turn count and rate-limit utilization, with and without
- [ ] **Sprint close-out** · ([checks](close_out/sprint_end_recurring.md)) — recurring checks run for this sprint and every finding dispositioned (fixed / rejected-with-reasoning / placed); no open issue belongs to this sprint's work

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

**Ideas not committed to anything** live in [`candidates.md`](../../tracked/candidates/), not here. A plan file that carries an idea list stops being a plan.

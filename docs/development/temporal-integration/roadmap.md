# Temporal Integration — Roadmap

**Status: 🟡 IN PROGRESS.** Stage A — the Python tree and its parity suite — is built and recorded in [`sprint.md`](../sprint.md). Nothing is orchestrated, and Temporal itself is not stood up. **Phases are listed in logical rollout order. Phase numbers are creation-order identifiers and do not reflect rollout sequence; execution order across components lives in [`sprint.md`](../sprint.md).**

**This is the component's FIRST plan**, written 2026-08-19. It had a decision record and a research pool and no roadmap. At creation the numbering was made to match the rollout order — 1 → 8 — because nothing outside this file cited a phase number yet. **From here the numbers are IDENTITY, not order:** a number names a phase for life, so a later re-sequencing moves an entry and never its number.

**The decision record is [`temporal-integration.md`](temporal-integration.md) and it is not superseded by this file.** It holds *why* Temporal, *why* Python was forced, and the Convert → Wrap → Orchestrate staging. This roadmap holds *what gets built and in what order*. Where the two describe the same work, the decision record is the reasoning and this file is the plan.

---

## In plain words

The workflow fleet is a set of long-running programs that call `claude -p`, write to git, and open pull requests. Today each one is a process someone starts. If the machine reboots four hours in, the run is gone and nothing knows how far it got.

Temporal is a durable execution engine: it records every step a workflow takes, so a crash resumes instead of restarting. Adopting it means three things, in this order. **A server has to exist** — that is a machine, a database, and a control plane. **The work has to be made safe to retry** — because an engine that retries a step will happily run it twice, and this fleet's steps push commits and open PRs. **Then the fleet moves onto it**, one family at a time.

The second of those is where most of the design is. The rest is a port.

---

## What this component owns

- **The Temporal control plane** — the server, its database, its namespace, and the machine it runs on
- **The activity contract** — what a dispatch's identity is, what a failure means, and which layer owns a retry
- **The `claude_cli` activity domain** — the genuinely new work: heartbeating a 10–60 minute run, and keeping a transcript out of event history
- **Workers** — one per machine that holds a repo, as bare systemd processes
- **The port itself** — every workflow that earns one, and the ruling on the ones that do not. **Including a workflow that exists only in the fleet being replaced and therefore has to be AUTHORED rather than converted** — [Phase 9](phase9_review_runs_in_the_python_tree.md) is the first, and the boundary against [Workflow Decomposition](../workflow-decomposition/roadmap.md) still holds: that component reshapes what exists, this one does not design workflows nobody has asked for

**It does not own:** the shape of the workflows being ported — that is [Workflow Decomposition](../workflow-decomposition/roadmap.md), and this component is gated on it. Nor what a run records ([PMP](../persistent-memory-protocol/roadmap.md)), nor the driver that composes parents into an unattended loop ([Autonomous Operation](../autonomous-operation/autonomous-operation.md), which is gated on this component), nor designing workflows that do not exist yet.

**And it explicitly does not own the wider Skyy-Net product.** Per [D6 of the seed handoff](../skyy-net-seed-handoff.md), the k3s + ArgoCD + Temporal + Postgres + UI stack is a separate product and this repo is a **consumer** of it. What this component owns is the part that runs *here*: a control plane sized for this fleet, and the workers on the machines that hold these repos.

---

## Phases

### [Phase 1 — The starter control plane](phase1_the_starter_control_plane.md) ⬜

*Every other phase assumes a control plane that exists, so this one goes first.*

**Est: ~16 hours** *(sized cold by `plan-verify`, 2026-08-20; every figure below is hours of focused development, not elapsed time, and states what it rests on so it can be argued with)* — the standup itself is a mirror of a setup that already exists, and that half is cheap. The other five artifacts are not: a server-side topology record the vendored standard does not cover, three build-time one-way-door rulings, the §A3 queue-naming ruling plus its no-fallback rule written into the addendum, a standup script that has to be re-runnable rather than a transcript of what was typed, and a cold-start reboot verification. Requirement 7's poll-prevention measurement also needs a throwaway worker process written purely to probe with, which the phase does not name. The doc's own *"a day's work"* covers the standup and not the five artifacts around it.

One node, one Temporal control plane, reachable from this workstation. **This phase stands up a known thing; it does not decide what to stand up.** **What to stand up is [D13 of the seed handoff](../skyy-net-seed-handoff.md)** — the operator's 2026-08-19 deployment brief, recorded where the other settled decisions live, and authoritative for this phase's scope. It is a mirror of a setup that has been stood up before, which is why it is a day's work rather than a project. What is genuinely this repo's to write down is the server-side topology (the vendored standard covers *workers*, not the server), the network path a worker takes to the frontend, and the machine-axis task-queue naming that [§A3 of the addendum](../../standards/temporal/claude-dot-files-addendum.md) has carried as OPEN. It also spends this component's three build-time one-way doors, which cannot be reopened once a workflow has run.

- [ ] **A Temporal control plane runs on one node and answers from this workstation** — demonstrated by a health check run from here, not from the node
- [ ] **Which Temporal services run where is written down** — frontend, history, matching, worker-service, Postgres, Web UI, namespace — and **how a worker reaches the frontend** is named rather than assumed
- [ ] **The three build-time one-way doors are decided and recorded BEFORE the first workflow runs** — history-shard count, namespace name, and a retention period ≥ 30 days
- [ ] **§A3 is closed** — machine-axis task-queue naming decided and written into the addendum, including the no-fallback-queue rule
- [ ] **The node was stood up by a script that can stand up the next one** — even a rough one; the automation is the artifact

### [Phase 2 — Durable dispatch identity, and the recovery contract](phase2_durable_dispatch_identity.md) ⬜

*An identity minted inside the thing that retries becomes a new identity on every attempt.*

**Est: ~22 hours** *(sized cold by `plan-verify`, 2026-08-20)* — most of it is enumeration rather than mechanism. The `run_id` seam, the atomic name reservation and the half-supplied `ValueError` already ship, so requirement 1 is a boundary change and not a rewrite. What is expensive: an identity function that has to be defined for every family in a twenty-workflow tree, a request fingerprint Temporal declines to supply and that therefore has no upstream shape to copy, and a six-column recovery table filled for *every* subsystem this fleet has. One cost the phase does not name: `uuid.uuid7` does not exist on the Python this repo runs — verified, `hasattr(uuid, "uuid7")` is `False` on 3.13.12 and it lands in 3.14 — so the UUIDv7 attempt id is a dependency decision or a hand-roll, not a stdlib call.

A retry is only safe if the work it repeats is the *same* work. Today a dispatch's identity is a composite: a caller may supply a `run_id`, and where one does not, the activity invents a random one and a wall-clock stamp names the log file. Under a retry policy that is an unbounded fan of identities and log files. This phase makes the identity an **input** — computed by the caller from the work, stable across every attempt — and writes the per-subsystem recovery table once, so each later guard supplies a value to an existing schema rather than designing its own.

**It must land before anything is wrapped.** Retrofitting an identity onto running workers is a rewrite.

- [ ] **No code path invents a dispatch identity inside an activity** — the logical id is computed by the caller from the work and passed in
- [ ] **The six identity components exist as record fields** — logical id, attempt id, uniqueness scope, request fingerprint, retention horizon, and the two conflict rulings
- [ ] **The per-subsystem recovery table is filled for every subsystem this fleet has**, including the rows whose values another component supplies
- [ ] **Re-dispatching the same logical id is demonstrated to reuse one identity**, and a duplicate launch while one is live fails loudly rather than starting a second run against the same worktree
- [ ] **Nothing Temporal replaces is built** — no claim/lease/TTL, no boot reconciler, no retry bookkeeping

### [Phase 3 — The retry boundary, and a `gh` failure that carries its own verdict](phase3_the_retry_boundary.md) ⬜

*Temporal retries an activity; `gh()` retries a call. Nested, a brief outage becomes a long stall.*

**Est: ~16 hours** *(sized cold by `plan-verify`, 2026-08-20)* — the hardest thinking is already done in the phase doc, and the population is small and bounded: two files call `gh` or `gh_json` today and three sites catch `RuntimeError`. The cost sits in the parts that are not the hierarchy — an audit-holding test that fails when a *new* re-wrap appears, preserving the named test that pins `gh_json`'s decode-retry behaviour rather than silently changing it, minting a `GITHUB_*` code vocabulary with no list anywhere to derive it from, and demonstrating three retry compositions rather than asserting them. Confirmed this genuinely needs no server: `temporalio.testing.WorkflowEnvironment` imports on the installed SDK.

`gh()` gained a bounded three-attempt retry for transient outages. Temporal's default retry policy is effectively unlimited. Composed naïvely that is nine attempts, and Temporal will happily retry a `404` forever. Deciding which layer owns the retry turns out to need a prerequisite the sprint item never named: `gh()` raises one bare `RuntimeError` for every failure class, and Temporal matches non-retryable errors by **exact string on the type name** — so today's code cannot express the transient-vs-terminal split at all. This phase supplies the typed raise, then rules the boundary per call class rather than picking one winner.

- [ ] **`gh()` raises a typed error** carrying the transient/terminal split *and* the read-only guard — never a bare `RuntimeError`
- [ ] **Nothing between that raise and the activity boundary re-wraps it** — `gh_json` and every caller audited, with a test that fails if a re-wrap reappears
- [ ] **The boundary is ruled per call class, not once** — read-only and idempotent goes one way, mutating and file/git-before-`gh` goes the other, and both are written down with the reasoning
- [ ] **`preflight` is demonstrably outside** — it runs before any workflow exists, so no retry policy reaches it
- [ ] **The three cases are demonstrated**: a transient failure on a read retries at one layer only, a terminal failure does not retry at all, and a mutating call is bounded

### [Phase 9 — `review-runs`, written in the Python tree](phase9_review_runs_in_the_python_tree.md) ⬜

*A deliverable with a consumer already waiting, gated behind a server it does not need.*

**Est: ~20 hours** *(sized 2026-08-20 alongside the split that created this phase, and **NOT judged by an independent pass** — see the caveat at the end of this section)* — the incumbent is 375 lines of bash and nothing in the Python tree answers to its name, so this is a write rather than a port. The scaffolding is pattern-work against a shape the fleet already has — module, activities, prompt, entrypoint shim, `run_*.py`, unit tests — anchored on the nearest comparable, `triage_candidates`, the other workflow authored directly in Python with no bash ancestor: **806 lines in its module plus 1,609 outside it**, measured in the phase doc's § *Runtime Verification*. What is not pattern-work: this workflow has **no parity oracle**, because parity here compares a conversion and there is no conversion, and its output is prose findings rather than a diffable artifact; and requirements 3, 4 and 5 are design work rather than transcription — a named read interface with one implementation and a second consumer already specified, a cross-repository output ruling, and a containment boundary for untrusted transcript content.

**A first pass at this figure was ~14 hours and it was wrong for a checkable reason:** it anchored on the comparable's module directory alone, which is 806 of that workflow's 2,415 lines. Recorded rather than silently replaced, because the failure mode — measuring the part of a comparable that is easy to `wc -l` — will recur.

**It is listed here, between [Phase 3](phase3_the_retry_boundary.md) and [Phase 4](phase4_the_claude_cli_activity.md), because that is its place in rollout order — and it is numbered 9 because 9 was the next free identifier.** This is the first entry that exercises the rule stated at the top of this file: **a number names a phase for life and says nothing about when it is built.**

**Why it is a phase and not a requirement inside [Phase 6](phase6_the_rest_of_the_fleet.md).** [PMP Phase 6](../persistent-memory-protocol/phase6_cpi_reads_the_journal.md) waits on the *Python port of `review-runs`* and states in both its own documents that the Temporal server is **not** a gate on it — and PMP split that phase out of its own Phase 8 for exactly this reason, so its only consumer would not sit behind a server nobody has stood up. Carrying the write inside Phase 6 put it straight back there, because Phase 6 waits on [Phase 5](phase5_the_first_dispatch.md), which waits on [Phase 1](phase1_the_starter_control_plane.md), which *is* the server. **Splitting the write out is what makes the "Not waiting on" cell below true rather than aspirational.** The alternative considered was splitting Phase 6's requirement 2 into two requirements in place; that leaves both inside a phase whose gate they would still inherit, which is the defect rather than its remedy. **Orchestrating `review-runs` under Temporal stays in [Phase 6](phase6_the_rest_of_the_fleet.md), with every other workflow's orchestration.**

- [ ] **`review-runs` exists in the Python tree** — written, not moved; there is no counterpart to port
- [ ] **It produces a CPI report from the incumbent's inputs**, demonstrated on a real window rather than asserted
- [ ] **Its evidence source sits behind a named read interface** — enumerate, read one, report gaps — so [PMP Phase 6](../persistent-memory-protocol/phase6_cpi_reads_the_journal.md) adds a second implementation rather than rewriting the sweep
- [ ] **Where the report goes is ruled, not inherited** — it crosses a repository boundary today and nothing has examined that
- [ ] **The transcripts it reads are treated as untrusted input**, and what the sweep may read and write is declared rather than inherited
- [ ] **Nothing here needs a server, a worker or a schedule** — demonstrated by running it from a shell
- [ ] **`review-runs.sh` keeps working** until [Phase 6](phase6_the_rest_of_the_fleet.md) orchestrates the replacement

### [Phase 4 — The `claude_cli` activity domain](phase4_the_claude_cli_activity.md) ⬜

*The one part of this port that is not a port.*

**Est: ~28 hours** *(sized cold by `plan-verify`, 2026-08-20; unchanged by the corrections of 2026-08-20, which is the point — the figure was set assuming them)* — **the largest phase before the first end-to-end dispatch, and until this pass the phase doc argued the opposite.** The payload half is genuinely closed: the limits are first-party numbers and transcript-to-file is a small change against a run bag that already exists. The heartbeat half is not. The paper this phase rests on calls its own recommended shape *"this paper's composition of documented parts, not a documented pattern… a design hypothesis until §9's tests pass"*, and the cadence cannot be chosen without measuring the CLI's longest natural silence across a batch of real runs — **now requirement 7, which is where that work was already priced.** Add the async-subprocess shape itself, cancellation delivery into a blocked child, orphan behaviour on a hard worker kill, and the slot-count ruling that is **now requirement 8** — the SDK default admits a hundred concurrent CLI runs on the operator's own workstation.

Every upstream Temporal activity runs for seconds to minutes and returns a structured result. Ours runs for 10–60 minutes and returns prose. Nothing in the vendored standards reaches that shape, which is why [§A1 of the addendum](../../standards/temporal/claude-dot-files-addendum.md) has carried it as OPEN since the addendum was written. This phase closes it by building one: a `claude -p` invocation that heartbeats, keeps its transcript out of event history, and has a stated answer for what a retry of a non-deterministic producer even means.

**One requirement here cannot be checked yet and is left open deliberately** — see the phase doc.

- [ ] **The activity heartbeats at a stated cadence**, and what counts as progress is defined rather than assumed
- [ ] **The transcript is a file and the result carries a reference** — event history carries references, never payloads
- [ ] **Retry semantics for a non-deterministic producer are ruled** and folded into [Phase 2](phase2_durable_dispatch_identity.md)'s contract
- [ ] **§A1 is closed in the addendum** — all three of its open bullets
- [ ] **A long run is demonstrated completing under a real worker**, and a worker restart mid-run behaves the way the ruling says it should
- [ ] **The CLI's maximum inter-line interval is measured across ≥20 real runs** — the number *and* its spread — **before** the cadence is chosen
- [ ] **The worker's activity slot count comes from the host's concurrency budget**, not the SDK default of 100, and the executor is at least as wide

### [Phase 5 — The first dispatch, end to end](phase5_the_first_dispatch.md) ⬜

*One family, all the way through, before anything else moves.*

**Est: ~26 hours** *(sized cold by `plan-verify`, 2026-08-20)* — thin in ambition, not in work. The family is one, but its wrappers are written against a shared activity layer of some 1,800 lines that the family reaches transitively, and requirement 2 rules *every* activity in that transitive set on whole-body idempotency with the reasoning recorded per activity. Around that: a systemd worker on the repo-holding machine, a parent rewritten as a workflow holding no process code and calling no model, an explicit-task-queue test for a failure mode whose symptom is silence rather than an error, and one dispatch carried end to end to a pull request plus a mid-run worker restart.

This is the strangler fig: one worker, one family's activities, one parent as a workflow, one pull request produced end to end under Temporal. It is deliberately thin, and it is the phase that proves the whole model — because the thing that breaks a port is never the second family. It also carries the audit that [Phase 3](phase3_the_retry_boundary.md)'s ruling defers: Temporal retries the *whole activity body*, not the failed call, so every wrapper has to be ruled idempotent-or-not against the actual population.

- [ ] **One worker runs as a bare systemd process** on the machine holding the repo, polling exactly one machine-axis queue
- [ ] **Every activity that family needs is wrapped**, and each is ruled against [Phase 3](phase3_the_retry_boundary.md)'s two options — the whole population, not a sample
- [ ] **Every dispatch names its target task queue explicitly** — inheriting the parent's queue is forbidden and fails silently when it happens
- [ ] **The completion contract still holds** — the run's final line still carries the stable identifier a parent reads
- [ ] **One dispatch produces one PR end to end**, and survives a worker restart mid-run
- [ ] **[Phase 2](phase2_durable_dispatch_identity.md)'s *parent sequencing* recovery row is read here** — a parent that dies between children resumes knowing the earlier ones succeeded

### [Phase 6 — The rest of the fleet, and the two that never ran](phase6_the_rest_of_the_fleet.md) ⬜

*The port stops being a demonstration and becomes the way work happens.*

**Est: ~31 hours** *(a fresh judgement of what remains after the 2026-08-20 split — **not** a subtraction, and **not judged by an independent pass**; see the caveat at the end of this section)* — still the largest phase in the component, and the figure is a floor rather than a midpoint. **The arithmetic that would read as tidier is not available:** the ~45-hour cold sizing was a whole-phase figure with no line item attributing hours to the `review-runs` write, so `45 − 20` would be subtracting a number that was never isolated from one that never contained it. It ports what [Phase 5](phase5_the_first_dispatch.md) left — three remaining purpose families plus `journal` — across a tree of roughly seventeen thousand non-test lines and sixty-four prompt files; decides the worker set by the domain-boundary test and stands up every declared domain including the empty shells; replaces timers with schedules and rules catch-up per schedule rather than globally; and applies the promotion rule across every shared fragment. **The sizing report named `review-runs` as the seam this phase would split at, and it has been split there** — the remaining figure is that report's own, minus the piece that left.

With one family proven, the rest follow the same shape. Two workflows do not get the benefit of the doubt: `plan-new` and `review-sprint` have never executed, and this phase rules whether they earn a port or die with the bash fleet. Schedules replace timers here, which is what unblocks two phases in other components.

- [ ] **Every workflow that earns a port is orchestrated by Temporal**, and the bash fleet has no remaining consumers
- [ ] **`review-runs` runs under Temporal** — [Phase 9](phase9_review_runs_in_the_python_tree.md) writes it; this phase orchestrates it, like every other workflow
- [ ] **`plan-new` and `review-sprint` are ruled** — ported, or retired with a written reason
- [ ] **Schedules replace timers** — consumers are [PMP Phase 8](../persistent-memory-protocol/phase8_the_poller.md) and [Autonomous Operation](../autonomous-operation/autonomous-operation.md)
- [ ] **The worker inventory is accurate** — every worker, its queue, and its registered activities, per the vendored standard's same-PR obligation

### Phase 7 — The three-node cluster

*Gated on work another project owns. No phase doc, deliberately.*

**Est: ~20 hours** *(sized cold by `plan-verify`, 2026-08-20 — what it will cost when the gate opens, not what it costs to wait)* — everything but wireguard arrives from MDC's bootstrap, so the novel work is the mesh across three nodes and the failure modes it introduces between them, and the rest is the standup script [Phase 1](phase1_the_starter_control_plane.md) leaves behind applied twice more. **Gated on** MDC's cluster work plus the wireguard design; the figure assumes both are in hand and would be wrong if the bootstrap itself has to be authored here.

The starter is one node and is meant to be. **That the permanent clustered control plane is a later sprint inherited from MDC is [D14 of the seed handoff](../skyy-net-seed-handoff.md)**, which also records why it is not planned now — including that the upstream migration and decommission procedures are still stubs. What this file adds is the one piece D14 says has no upstream to copy: **wireguard between the three nodes** is this project's own, and it is the only novel work here. **No phase doc exists for this and none should be written yet** — planning it in detail now is a guess that ages badly against a cluster somebody else is still building.

**Gate:** the MDC-owned cluster work, plus the wireguard design.

- [ ] **Three k3s nodes, with wireguard between them**
- [ ] **The wireguard layer is designed here** — it is the part MDC does not supply
- [ ] **A phase doc is written when the gate opens**, not before

### Phase 8 — The pivot, and the starter is destroyed

*Gated on [Phase 7](#phase-7--the-three-node-cluster). No phase doc, deliberately.*

**Est: ~14 hours** *(sized cold by `plan-verify`, 2026-08-20 — what it will cost when the gate opens)* — the second control plane is stood up by a script that exists by then, so the cost is the part that is not mechanical: reissuing every secret placed on the starter rather than copying it, repointing every worker onto the new frontend, and proving nothing still depends on the node before it is destroyed. **Gated on** [Phase 7](#phase-7--the-three-node-cluster) and on a secrets-management story that does not exist today; the reissue half is the piece that figure is least confident about, because nothing has yet said what issues those secrets.

A new permanent control plane is stood up on the good cluster and the starter node is **destroyed — not migrated. That ruling and its reason are [D13 of the seed handoff](../skyy-net-seed-handoff.md)**, which also records MDC's own form of the rule (*"Bootstrap-era secrets die with `k3s-0` — never migrated"*); this entry cites it rather than restating it. What is worth adding here is that the shape has a name: Cluster API calls it a pivot, and the bootstrap chain it runs on is MDC's.

**Gate:** [Phase 7](#phase-7--the-three-node-cluster), and a secrets-management story that does not exist today.

**This phase is where the deferred hardening lands, and saying so is what makes the deferral a placement rather than a disappearance.** [Phase 1](phase1_the_starter_control_plane.md) does not harden the starter and is right not to. Nothing between there and here carries the question, so without the checkbox below the standup script written for a disposable node becomes the standup script for a permanent one and nobody is asked to re-decide.

- [ ] **A permanent control plane runs on the three-node cluster**
- [ ] **Its security posture is decided BEFORE any worker points at it** — worker→frontend transport auth, the authorizer decision, and who may reach the frontend at all. **This is where [Phase 1](phase1_the_starter_control_plane.md)'s accepted risks stop being accepted**: the permissive default authorizer and namespace-as-only-boundary were accepted because the node is destroyed, and this plane is not. The [seed handoff](../skyy-net-seed-handoff.md) § *Security surface* is the input and D13 does not supersede it
- [ ] **Every secret placed on the starter is treated as compromised** and reissued rather than copied
- [ ] **The starter node is destroyed**, and nothing depends on it any more

---

**Two figures in this section were set by the pass that created the split they price, and neither has been judged by anything but its author** — [Phase 9](phase9_review_runs_in_the_python_tree.md)'s ~20 hours and [Phase 6](phase6_the_rest_of_the_fleet.md)'s revised ~31. Every other figure here was sized cold by `plan-verify`, which is a different actor reading the plan it did not write. **Both should go to the next sizing pass**, and until they have, they are the two numbers in this file least entitled to be planned against.

---

## The order, and what each part waits on

**[Phase 1](phase1_the_starter_control_plane.md) is first because every other milestone assumes a control plane that exists.** That is a sequencing instruction from the operator, not a derivation from the research — the research pool does not cover deployment at all, and that is a decision recorded elsewhere rather than a gap in the evidence.

**[Phase 2](phase2_durable_dispatch_identity.md), [Phase 3](phase3_the_retry_boundary.md) and [Phase 9](phase9_review_runs_in_the_python_tree.md) do not actually need the server**, and this is worth knowing before anything is scheduled. All three are changes to Python that already exists or Python that lands beside it, all three are testable with no Temporal runtime. If [Phase 1](phase1_the_starter_control_plane.md) stalls on a machine, these are what proceed. Phases 2 and 3 are independent of each other and could swap; **[Phase 9](phase9_review_runs_in_the_python_tree.md) is independent of both** and is the one with a consumer in another component already waiting on it.

**One requirement inside a GATED phase is itself ungated, and it is the longest-lead measurement in the component.** [Phase 4](phase4_the_claude_cli_activity.md) requirement 7 — measure the CLI's maximum inter-line interval across at least twenty real runs — needs the installed CLI and nothing else. Phase 4 as a whole waits on [Phase 1](phase1_the_starter_control_plane.md) because heartbeating cannot be *demonstrated* without a server; **the measurement is not the demonstration**, and it is hours of elapsed wall-clock rather than hours of work. **It can be collected alongside Phases 2, 3 and 9, and only the cadence ruling waits.** This is the same shape [Phase 9](phase9_review_runs_in_the_python_tree.md) exists to fix, one level down: a phase-level gate asserted over a requirement that does not need it.

**The difference between them is what they are prerequisites for.** Phases 2 and 3 are hard prerequisites for wrapping anything, so they gate the port. Phase 9 gates nothing inside this component — it gates [PMP Phase 6](../persistent-memory-protocol/phase6_cpi_reads_the_journal.md), and [Phase 6](phase6_the_rest_of_the_fleet.md) only needs it to exist before orchestrating it. **That asymmetry is the whole argument for it being a phase**: a deliverable whose only consumer is outside this component has no business inheriting this component's internal gates.

**[Phase 4](phase4_the_claude_cli_activity.md) needs [Phase 1](phase1_the_starter_control_plane.md)** — heartbeating cannot be demonstrated without a server to heartbeat to.

**[Phase 5](phase5_the_first_dispatch.md) needs [Phases 1, 2, 3 and 4](phase1_the_starter_control_plane.md)** — named rather than counted, because [Phase 9](phase9_review_runs_in_the_python_tree.md) precedes it in this listing and **is not one of its gates.** It is the first phase where a wrong answer in any of the four shows up.

**[Phase 6](phase6_the_rest_of_the_fleet.md) needs [Phase 5](phase5_the_first_dispatch.md)**, plus [Phase 9](phase9_review_runs_in_the_python_tree.md) for its requirement 2 alone — there has to be a `review-runs` before there is one to orchestrate.

**[Phase 7](#phase-7--the-three-node-cluster) and [Phase 8](#phase-8--the-pivot-and-the-starter-is-destroyed) sit last in rollout order and are gated outside this component.** A single-node control plane running a handful of workers is a legitimate resting state and is what this repo actually needs for a long time.

---

## Dependencies on other components

| This component | Depends on | Which way |
|---|---|---|
| The port itself ([Phase 5](phase5_the_first_dispatch.md), [Phase 6](phase6_the_rest_of_the_fleet.md)) | [Workflow Decomposition](../workflow-decomposition/roadmap.md) | **gates us** — porting a shape still being changed means porting it twice |
| The port itself | [Memory Management Framework](../memory-management-framework/roadmap.md) | **satisfied** — that component is complete, and the typed exit record moved to PMP |
| [Phase 2](phase2_durable_dispatch_identity.md) | [PMP Phase 1](../persistent-memory-protocol/phase1_the_run_bag.md) — the run bag keyed by `run_id` | **satisfied**; the bag is the store the identity record extends |
| [Phase 7](#phase-7--the-three-node-cluster), [Phase 8](#phase-8--the-pivot-and-the-starter-is-destroyed) | MDC's cluster and bootstrap work | **gates us** — and is why neither has a phase doc |

**Components gated on THIS one, listed so their planners can see where they sit:**

| Waiting component | Waiting on | Not waiting on |
|---|---|---|
| [PMP Phase 5](../persistent-memory-protocol/phase5_snapshots_then_retention.md) — snapshots and retention | [Phase 1](phase1_the_starter_control_plane.md), for the recurring half only | the port |
| [PMP Phase 6](../persistent-memory-protocol/phase6_cpi_reads_the_journal.md) — CPI reads the journal | [Phase 9](phase9_review_runs_in_the_python_tree.md) — `review-runs` written in Python, and nothing else | **the server**, and **[Phase 6](phase6_the_rest_of_the_fleet.md)** — [Phase 9](phase9_review_runs_in_the_python_tree.md) is ungated, so this one can be pulled forward |
| [PMP Phase 8](../persistent-memory-protocol/phase8_the_poller.md) — the poller | Temporal schedules, in [Phase 6](phase6_the_rest_of_the_fleet.md) | — |
| [Autonomous Operation](../autonomous-operation/autonomous-operation.md) | this component as a whole | — |

---

## Research

[`research/`](research/) holds six papers and [`synthesis.md`](research/synthesis.md) rolls them up. **Read the synthesis, not the pool** — and read its *Housekeeping* section first, because it says something a planner needs: **only two of the six papers feed this component.**

| Paper | Backs | Status |
|---|---|---|
| [`raw/activity_retry_boundary.md`](research/raw/activity_retry_boundary.md) | [Phase 3](phase3_the_retry_boundary.md) | `Last validated 2026-08-19`, Critic `PASS-WITH-FIXES` |
| [`raw/durable_dispatch_identity.md`](research/raw/durable_dispatch_identity.md) | [Phase 2](phase2_durable_dispatch_identity.md), and one row of [Phase 4](phase4_the_claude_cli_activity.md) | `Last validated 2026-08-07`, Critic `PASS-WITH-FIXES` |

The other four — `liveness_signal_measurement`, `blocked_work_notification`, `credential_expiry_detection`, `false_completion_detection` — are physically in this pool and feed **other** components' milestones. They are not evidence for anything below, and no phase here plans against them. Their re-homing is an operator ruling; the half with a ratified `ship` decision behind it is tracked at [issue #125](https://github.com/helloskyy-io/Claude-Dot-Files/issues/125).

**[Phase 1](phase1_the_starter_control_plane.md) and [Phase 9](phase9_review_runs_in_the_python_tree.md) rest on no paper in this pool**, and each says so in its own doc. Phase 9 rests on [`cpi-cycle.md`](../../guide/cpi-cycle.md) — the operating manual for the cycle it serves — plus [`workflow-scripts.md`](../../standards/workflow-scripts.md) and one forward constraint from [PMP Phase 6](../persistent-memory-protocol/phase6_cpi_reads_the_journal.md). Phase 1's evidence is listed next. Its evidence is the operator's deployment brief, the vendored [Worker Deployment Standard](../../standards/temporal/worker_deployment_standard.md), the [seed handoff](../skyy-net-seed-handoff.md), and first-party Temporal documentation read at plan time.

**The product-level pool** at [`../../standards/architecture/research/`](../../standards/architecture/research/) supplies four findings this plan cites rather than re-derives: that shard capacity is a build-time one-way door, that self-hosted Temporal ships an authorizer that allows every request, that an unresolvable assignee must park rather than fall back to a default queue, and that no first-party Claude ↔ Temporal runtime integration exists — so the hand-rolled `claude_cli` activity is not a temporary state to wait out.

---

## What is deliberately not built

- **Anything beyond a single node in [Phase 1](phase1_the_starter_control_plane.md).** No alternatives compared, no lighter-weight option proposed, no evaluation of k3s against anything. **The scope is [D13 of the seed handoff](../skyy-net-seed-handoff.md) and this file does not restate it** — read it there, along with [D14](../skyy-net-seed-handoff.md) for why the permanent cluster is a later sprint and [D15](../skyy-net-seed-handoff.md) for why no workload tier is expected. **If a build run finds itself weighing a deployment choice, it has left the phase's scope.**
- **mTLS and Tailscale ACLs — NOT in [Phase 1](phase1_the_starter_control_plane.md).** Hardening a node scheduled for demolition buys nothing that survives [Phase 8](#phase-8--the-pivot-and-the-starter-is-destroyed)'s pivot. **[D13](../skyy-net-seed-handoff.md) is the ruling and it supersedes D11's mTLS clause in the handoff itself**, which is where the supersession is recorded — this file cites it rather than carrying a second copy of the reasoning. **The deferral has a destination and it is [Phase 8](#phase-8--the-pivot-and-the-starter-is-destroyed)**, which stands up the plane that is *not* disposable; deferring without one is how an accepted risk on a temporary node becomes the permanent posture by default.
- **The security standard itself — UNSCHEDULED here, and that is not the same as ruled out.** D13 rules only that a node scheduled for destruction is not hardened; it says nothing about the standard the [seed handoff](../skyy-net-seed-handoff.md) § *Standards to author* still lists, and D10 (*"security head-on from day one"*) is not superseded. **Do not read the bullet above as covering it.** Its content — including the `claude_cli` input constraints the handoff names as the mitigation for queue injection — has no home in this component's phases, and standards are human-in-the-loop, so this file names the gap rather than filling it.
- **§A4 of the addendum — whether a prompt is an INPUT or a RESOURCE — is NOT ruled by this plan, and no phase here closes it.** [Phase 4](phase4_the_claude_cli_activity.md) closes [§A1](../../standards/temporal/claude-dot-files-addendum.md) and [Phase 1](phase1_the_starter_control_plane.md) closes §A3; §A4 stays open. **It becomes concrete at [Phase 5](phase5_the_first_dispatch.md)**, where a parent first becomes a workflow and a replay first has to load a prompt from somewhere. The ruling is tracked as candidate **C-obarkm4s** in [`candidates.md`](../../standards/architecture/research/candidates.md), `component: temporal-integration`, untriaged — **naming it here is the placement, not the decision.** **One criterion belongs on that ruling and is easy to miss:** [Phase 4](phase4_the_claude_cli_activity.md) requirement 2 makes keeping payloads out of event history a *security* control, not only a size one — and workflow and activity **inputs** are recorded in event history exactly as results are. So *"prompt as input"* puts prompt text into the central Postgres for the ≥ 30-day retention [Phase 1](phase1_the_starter_control_plane.md) requirement 4 mandates. **It has to clear that rule or be ruled out on it**, and replay-correctness alone is not the whole question.
- **The provisioner.** [Phase 1](phase1_the_starter_control_plane.md) scripts its own standup so the next node is not twenty manual rebuilds. That is *"do not do it by hand"*, not *"build deployment automation"* — which is candidate C-2xgap6o1's subject and a sprint of its own.
- **Temporal Cloud, and serverless workers.** Both ruled out and written down in [`stack_reference.md`](../../standards/architecture/stack_reference.md) — Cloud since 2026-07-12, and AWS Lambda because a 15-minute activity ceiling cannot host a 10–60 minute `claude -p` run. A prior research cycle already spent effort pricing Cloud against a decision made three weeks earlier. **Do not reopen either.**
- **Claim/lease/TTL, a boot reconciler, retry bookkeeping, or a hand-rolled liveness probe.** Temporal replaces that layer outright. Building any of it now is building the thing the port deletes.
- **A second, git-native tier-1 dispatch record on `refs/dispatch/*`.** This component's own pool proposes one — [`raw/durable_dispatch_identity.md`](research/raw/durable_dispatch_identity.md) §3.6 splits dispatch state into two tiers, §5.3's migration table carries the tier-1 row at a *zero* **port-time rewrite** cost (which is not a build cost), and §6 item 6 prices the build at *1–2 days*: *"Tier 1 store: `refs/dispatch/*` with CAS creation"*. **It is superseded by the PMP run bag, which already IS the store such a record lives in and is deliberately ONE tier** ([PMP Phase 1](../persistent-memory-protocol/phase1_the_run_bag.md) § *One location, a folder per run, many formats*), so retention, transfer and replay operate on a single unit rather than on two that can disagree about what a run was. The plan already builds on the bag rather than beside it: [Phase 2](phase2_durable_dispatch_identity.md) § *Dependencies* records that *"The run bag is already keyed by `run_id`, and the identity record extends a store that exists rather than creating one"*, and [Phase 4](phase4_the_claude_cli_activity.md) says the same for the transcript — *"Reuse the run bag rather than inventing a second store …"*. **The paper claims two advantages for its tier 1 over a store like the bag, and saying which one survives is what makes this a supersession rather than a dismissal.** **(1) `git update-ref` gives compare-and-swap on ref creation — and this one does not survive**, because the bag's create is already atomic. What is genuinely missing is the signal that tells a *retry*, which must adopt the open bag, from a *duplicate launch*, which [Phase 2](phase2_durable_dispatch_identity.md) requirement 4 says must fail loudly. That is Phase 2's own work rather than a property of either store, and it carries a checklist item there — this file records the ruling and does not keep a second copy of its reasoning. **(2) The paper's tier 1 is *"the only fleet state that crosses a machine boundary"* — and this one does survive**: the bag is one root per edge that ships to object storage local-first and asynchronously ([PMP roadmap](../persistent-memory-protocol/roadmap.md) commitment 8) — it transfers across machines, it does not arbitrate between them. **Nothing hand-rolls a cross-machine lock in the gap**, which [Phase 2](phase2_durable_dispatch_identity.md) requirement 5 forbids anyway: the uniqueness scope is `(machine-id, repo)` today, there is one edge, and it becomes `(Namespace, Task Queue)` at the port. **A reader arriving from the paper should treat its tier-1 recommendation as ruled on here** — the paper stays as written, because a pool is evidence and this file is where the plan disagrees with it.
- **Containerized workers.** They spawn `claude` against a real repo, a real toolchain and a real credential; containerizing buys worse fidelity at higher complexity. MDC containerizes *its* workers because its activities call APIs rather than local development environments — a different constraint with a different answer.
- **The three cheap guards** — credential expiry, false completion, safety-hook wiring. Two papers in this pool are their evidence and their milestone was deleted when Fleet Reliability dissolved. [Phase 2](phase2_durable_dispatch_identity.md) gives them **rows in the recovery table** so that whoever builds them supplies a value rather than designing a schema; it does not build them. The ruling on where they live is [issue #125](https://github.com/helloskyy-io/Claude-Dot-Files/issues/125).

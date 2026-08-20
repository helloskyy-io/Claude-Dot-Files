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
- **The port itself** — every workflow that earns one, and the ruling on the ones that do not

**It does not own:** the shape of the workflows being ported — that is [Workflow Decomposition](../workflow-decomposition/roadmap.md), and this component is gated on it. Nor what a run records ([PMP](../persistent-memory-protocol/roadmap.md)), nor the driver that composes parents into an unattended loop ([Autonomous Operation](../autonomous-operation/autonomous-operation.md), which is gated on this component), nor designing workflows that do not exist yet.

**And it explicitly does not own the wider Skyy-Net product.** Per [D6 of the seed handoff](../skyy-net-seed-handoff.md), the k3s + ArgoCD + Temporal + Postgres + UI stack is a separate product and this repo is a **consumer** of it. What this component owns is the part that runs *here*: a control plane sized for this fleet, and the workers on the machines that hold these repos.

---

## Phases

### [Phase 1 — The starter control plane](phase1_the_starter_control_plane.md) ⬜

*Every other phase assumes a control plane that exists, so this one goes first.*

One node, one Temporal control plane, reachable from this workstation. **This phase stands up a known thing; it does not decide what to stand up.** The setup is the one MDC runs today, mirrored — same gear, same images, same shape — which is why it is a day's work rather than a project. What is genuinely this repo's to write down is the server-side topology (the vendored standard covers *workers*, not the server), the network path a worker takes to the frontend, and the machine-axis task-queue naming that [§A3 of the addendum](../../standards/temporal/claude-dot-files-addendum.md) has carried as OPEN. It also spends this component's three build-time one-way doors, which cannot be reopened once a workflow has run.

- [ ] **A Temporal control plane runs on one node and answers from this workstation** — demonstrated by a health check run from here, not from the node
- [ ] **Which Temporal services run where is written down** — frontend, history, matching, worker-service, Postgres, Web UI, namespace — and **how a worker reaches the frontend** is named rather than assumed
- [ ] **The three build-time one-way doors are decided and recorded BEFORE the first workflow runs** — history-shard count, namespace name, and a retention period ≥ 30 days
- [ ] **§A3 is closed** — machine-axis task-queue naming decided and written into the addendum, including the no-fallback-queue rule
- [ ] **The node was stood up by a script that can stand up the next one** — even a rough one; the automation is the artifact

### [Phase 2 — Durable dispatch identity, and the recovery contract](phase2_durable_dispatch_identity.md) ⬜

*An identity minted inside the thing that retries becomes a new identity on every attempt.*

A retry is only safe if the work it repeats is the *same* work. Today a dispatch's identity is a composite: a caller may supply a `run_id`, and where one does not, the activity invents a random one and a wall-clock stamp names the log file. Under a retry policy that is an unbounded fan of identities and log files. This phase makes the identity an **input** — computed by the caller from the work, stable across every attempt — and writes the per-subsystem recovery table once, so each later guard supplies a value to an existing schema rather than designing its own.

**It must land before anything is wrapped.** Retrofitting an identity onto running workers is a rewrite.

- [ ] **No code path invents a dispatch identity inside an activity** — the logical id is computed by the caller from the work and passed in
- [ ] **The six identity components exist as record fields** — logical id, attempt id, uniqueness scope, request fingerprint, retention horizon, and the two conflict rulings
- [ ] **The per-subsystem recovery table is filled for every subsystem this fleet has**, including the rows whose values another component supplies
- [ ] **Re-dispatching the same logical id is demonstrated to reuse one identity**, and a duplicate launch while one is live fails loudly rather than starting a second run against the same worktree
- [ ] **Nothing Temporal replaces is built** — no claim/lease/TTL, no boot reconciler, no retry bookkeeping

### [Phase 3 — The retry boundary, and a `gh` failure that carries its own verdict](phase3_the_retry_boundary.md) ⬜

*Temporal retries an activity; `gh()` retries a call. Nested, a brief outage becomes a long stall.*

`gh()` gained a bounded three-attempt retry for transient outages. Temporal's default retry policy is effectively unlimited. Composed naïvely that is nine attempts, and Temporal will happily retry a `404` forever. Deciding which layer owns the retry turns out to need a prerequisite the sprint item never named: `gh()` raises one bare `RuntimeError` for every failure class, and Temporal matches non-retryable errors by **exact string on the type name** — so today's code cannot express the transient-vs-terminal split at all. This phase supplies the typed raise, then rules the boundary per call class rather than picking one winner.

- [ ] **`gh()` raises a typed error** carrying the transient/terminal split *and* the read-only guard — never a bare `RuntimeError`
- [ ] **Nothing between that raise and the activity boundary re-wraps it** — `gh_json` and every caller audited, with a test that fails if a re-wrap reappears
- [ ] **The boundary is ruled per call class, not once** — read-only and idempotent goes one way, mutating and file/git-before-`gh` goes the other, and both are written down with the reasoning
- [ ] **`preflight` is demonstrably outside** — it runs before any workflow exists, so no retry policy reaches it
- [ ] **The three cases are demonstrated**: a transient failure on a read retries at one layer only, a terminal failure does not retry at all, and a mutating call is bounded

### [Phase 4 — The `claude_cli` activity domain](phase4_the_claude_cli_activity.md) ⬜

*The one part of this port that is not a port.*

Every upstream Temporal activity runs for seconds to minutes and returns a structured result. Ours runs for 10–60 minutes and returns prose. Nothing in the vendored standards reaches that shape, which is why [§A1 of the addendum](../../standards/temporal/claude-dot-files-addendum.md) has carried it as OPEN since the addendum was written. This phase closes it by building one: a `claude -p` invocation that heartbeats, keeps its transcript out of event history, and has a stated answer for what a retry of a non-deterministic producer even means.

**One requirement here cannot be checked yet and is left open deliberately** — see the phase doc.

- [ ] **The activity heartbeats at a stated cadence**, and what counts as progress is defined rather than assumed
- [ ] **The transcript is a file and the result carries a reference** — event history carries references, never payloads
- [ ] **Retry semantics for a non-deterministic producer are ruled** and folded into [Phase 2](phase2_durable_dispatch_identity.md)'s contract
- [ ] **§A1 is closed in the addendum** — all three of its open bullets
- [ ] **A long run is demonstrated completing under a real worker**, and a worker restart mid-run behaves the way the ruling says it should

### [Phase 5 — The first dispatch, end to end](phase5_the_first_dispatch.md) ⬜

*One family, all the way through, before anything else moves.*

This is the strangler fig: one worker, one family's activities, one parent as a workflow, one pull request produced end to end under Temporal. It is deliberately thin, and it is the phase that proves the whole model — because the thing that breaks a port is never the second family. It also carries the audit that [Phase 3](phase3_the_retry_boundary.md)'s ruling defers: Temporal retries the *whole activity body*, not the failed call, so every wrapper has to be ruled idempotent-or-not against the actual population.

- [ ] **One worker runs as a bare systemd process** on the machine holding the repo, polling exactly one machine-axis queue
- [ ] **Every activity that family needs is wrapped**, and each is ruled against [Phase 3](phase3_the_retry_boundary.md)'s two options — the whole population, not a sample
- [ ] **Every dispatch names its target task queue explicitly** — inheriting the parent's queue is forbidden and fails silently when it happens
- [ ] **The completion contract still holds** — the run's final line still carries the stable identifier a parent reads
- [ ] **One dispatch produces one PR end to end**, and survives a worker restart mid-run

### [Phase 6 — The rest of the fleet, and the two that never ran](phase6_the_rest_of_the_fleet.md) ⬜

*The port stops being a demonstration and becomes the way work happens.*

With one family proven, the rest follow the same shape. Two workflows do not get the benefit of the doubt: `plan-new` and `review-sprint` have never executed, and this phase rules whether they earn a port or die with the bash fleet. Schedules replace timers here, which is what unblocks two phases in other components.

- [ ] **Every workflow that earns a port is orchestrated by Temporal**, and the bash fleet has no remaining consumers
- [ ] **`review-runs` is ported** — its consumer is [PMP Phase 6](../persistent-memory-protocol/phase6_cpi_reads_the_journal.md), which moves the CPI evidence sweep off comment-scraping
- [ ] **`plan-new` and `review-sprint` are ruled** — ported, or retired with a written reason
- [ ] **Schedules replace timers** — consumers are [PMP Phase 8](../persistent-memory-protocol/phase8_the_poller.md) and [Autonomous Operation](../autonomous-operation/autonomous-operation.md)
- [ ] **The worker inventory is accurate** — every worker, its queue, and its registered activities, per the vendored standard's same-PR obligation

### Phase 7 — The three-node cluster

*Gated on work another project owns. No phase doc, deliberately.*

The starter is one node and is meant to be. The real cluster is three k3s nodes with **wireguard between them**. Everything except wireguard comes from MDC; the wireguard layer is this project's own addition and is the only novel piece. **No phase doc exists for this and none should be written yet** — planning it in detail now is a guess that ages badly against a cluster somebody else is still building.

**Gate:** the MDC-owned cluster work, plus the wireguard design.

- [ ] **Three k3s nodes, with wireguard between them**
- [ ] **The wireguard layer is designed here** — it is the part MDC does not supply
- [ ] **A phase doc is written when the gate opens**, not before

### Phase 8 — The pivot, and the starter is destroyed

*Gated on [Phase 7](#phase-7--the-three-node-cluster). No phase doc, deliberately.*

A new permanent control plane is stood up on the good cluster and the starter node is **destroyed — not migrated.** Its secrets were placed before secrets management existed, so they are treated as compromised by construction. This is a known pattern; Cluster API calls it a pivot, and the bootstrap chain it runs on is MDC's.

**Gate:** [Phase 7](#phase-7--the-three-node-cluster), and a secrets-management story that does not exist today.

- [ ] **A permanent control plane runs on the three-node cluster**
- [ ] **Every secret placed on the starter is treated as compromised** and reissued rather than copied
- [ ] **The starter node is destroyed**, and nothing depends on it any more

---

## The order, and what each part waits on

**[Phase 1](phase1_the_starter_control_plane.md) is first because every other milestone assumes a control plane that exists.** That is a sequencing instruction from the operator, not a derivation from the research — the research pool does not cover deployment at all, and that is a decision recorded elsewhere rather than a gap in the evidence.

**[Phase 2](phase2_durable_dispatch_identity.md) and [Phase 3](phase3_the_retry_boundary.md) do not actually need the server**, and this is worth knowing before anything is scheduled. Both are changes to Python that already exists, both are testable with no Temporal runtime, and both are hard prerequisites for wrapping anything. If [Phase 1](phase1_the_starter_control_plane.md) stalls on a machine, these are what proceed. They are independent of each other and could swap.

**[Phase 4](phase4_the_claude_cli_activity.md) needs [Phase 1](phase1_the_starter_control_plane.md)** — heartbeating cannot be demonstrated without a server to heartbeat to.

**[Phase 5](phase5_the_first_dispatch.md) needs all four before it**, and it is the first phase where a wrong answer in any of them shows up.

**[Phase 6](phase6_the_rest_of_the_fleet.md) needs [Phase 5](phase5_the_first_dispatch.md)** and nothing else inside this component.

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
| [PMP Phase 6](../persistent-memory-protocol/phase6_cpi_reads_the_journal.md) — CPI reads the journal | the `review-runs` port in [Phase 6](phase6_the_rest_of_the_fleet.md) | **the server** — this one can be pulled forward |
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

**[Phase 1](phase1_the_starter_control_plane.md) rests on no paper in this pool**, and says so in its own doc. Its evidence is the operator's deployment brief, the vendored [Worker Deployment Standard](../../standards/temporal/worker_deployment_standard.md), the [seed handoff](../skyy-net-seed-handoff.md), and first-party Temporal documentation read at plan time.

**The product-level pool** at [`../../standards/architecture/research/`](../../standards/architecture/research/) supplies four findings this plan cites rather than re-derives: that shard capacity is a build-time one-way door, that self-hosted Temporal ships an authorizer that allows every request, that an unresolvable assignee must park rather than fall back to a default queue, and that no first-party Claude ↔ Temporal runtime integration exists — so the hand-rolled `claude_cli` activity is not a temporary state to wait out.

---

## What is deliberately not built

- **Anything beyond a single node in [Phase 1](phase1_the_starter_control_plane.md).** No alternatives compared, no lighter-weight option proposed, no evaluation of k3s against anything. The starter is a mirror of a setup that already exists and has been stood up before; that is the entire reason it is cheap. **If a build run finds itself weighing a deployment choice, it has left the phase's scope.**
- **mTLS, Tailscale ACLs, and the security standard — NOT in [Phase 1](phase1_the_starter_control_plane.md).** The starter is internal-IP, key-based, no frills, and is destroyed in [Phase 8](#phase-8--the-pivot-and-the-starter-is-destroyed) precisely because its secrets predate secrets management. **This diverges from D11 of the [seed handoff](../skyy-net-seed-handoff.md)**, which puts "one PR produced end-to-end under mTLS" in its milestone 1; the operator's later deployment brief supersedes it, and the divergence is named here rather than left for a reader to trip over.
- **The provisioner.** [Phase 1](phase1_the_starter_control_plane.md) scripts its own standup so the next node is not twenty manual rebuilds. That is *"do not do it by hand"*, not *"build deployment automation"* — which is candidate C-076's subject and a sprint of its own.
- **Temporal Cloud, and serverless workers.** Both ruled out and written down in [`stack_reference.md`](../../standards/architecture/stack_reference.md) — Cloud since 2026-07-12, and AWS Lambda because a 15-minute activity ceiling cannot host a 10–60 minute `claude -p` run. A prior research cycle already spent effort pricing Cloud against a decision made three weeks earlier. **Do not reopen either.**
- **Claim/lease/TTL, a boot reconciler, retry bookkeeping, or a hand-rolled liveness probe.** Temporal replaces that layer outright. Building any of it now is building the thing the port deletes.
- **Containerized workers.** They spawn `claude` against a real repo, a real toolchain and a real credential; containerizing buys worse fidelity at higher complexity. MDC containerizes *its* workers because its activities call APIs rather than local development environments — a different constraint with a different answer.
- **The three cheap guards** — credential expiry, false completion, safety-hook wiring. Two papers in this pool are their evidence and their milestone was deleted when Fleet Reliability dissolved. [Phase 2](phase2_durable_dispatch_identity.md) gives them **rows in the recovery table** so that whoever builds them supplies a value rather than designing a schema; it does not build them. The ruling on where they live is [issue #125](https://github.com/helloskyy-io/Claude-Dot-Files/issues/125).

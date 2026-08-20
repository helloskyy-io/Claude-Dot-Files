# Phase 1 — The starter control plane

**Status: ⬜ NOT STARTED.** First in [rollout order](roadmap.md); every other phase in this component assumes a control plane that exists.

**This phase stands up a KNOWN thing. It does not decide what to stand up.** The setup is the one MDC runs today, mirrored — same gear, same images, same shape. It has been stood up before, which is the entire reason it is a day's work rather than a project. **Do not compare alternatives, do not evaluate k3s against anything, and do not propose a lighter-weight option because one node seems like a lot of machinery for one fleet.** If the build finds itself weighing a deployment choice, it has left this phase's scope.

What *is* this phase's work is the other half: writing down the parts that are specific to this repo. The vendored [Worker Deployment Standard](../../standards/temporal/worker_deployment_standard.md) is 618 lines about **workers**. The server side — which service runs where, how a worker reaches it, what the namespace is called and how long it keeps history — is undocumented for this repo, and three of those settings can never be changed once a workflow has run.

---

## Requirements for completion

1. **A Temporal control plane runs on one node and answers from this workstation.** Demonstrated by a health check issued *from here*, not from the node — the thing under test is reachability across the network path, not that the process started.
2. **The server-side topology is written down.** Which Temporal services run where — frontend, history, matching, worker-service — plus Postgres, the Web UI, and the namespace. The vendored standard does not cover this and nothing else in the repo does either.
3. **The worker→frontend network path is NAMED, not assumed.** Whatever provides it today is this project's first answer to edge-to-brain connectivity, and it should be written down as such rather than discovered later by a worker that cannot poll.
4. **The three build-time one-way doors are decided and recorded BEFORE the first workflow runs** — history-shard count, namespace name, and a retention period of at least 30 days. Requirement 6 explains why the third is not a detail.
5. **[§A3](../../standards/temporal/claude-dot-files-addendum.md) is closed** — machine-axis task-queue naming decided and written into the addendum, together with the no-fallback rule in requirement 7.
6. **The node was stood up by a script that can stand up the next one.** Even a rough one. Twenty manual rebuilds teach twenty times and leave nothing behind; the automation is the artifact.
7. **Whether a worker can be prevented from polling a queue it should not serve is MEASURED** against the standing node. **This requirement stays unchecked until it is measured** — see § *What this phase does not settle*.

**Requirement 7 is deliberately open.** It is not deferred work and it does not have a tracker: it is an *input* this phase consumes, and the measurement is cheap only while a disposable node exists. See the closing section.

---

## Dependencies

**Inside this component:** none. This is the first phase and it is ungated.

**Outside this component:** none that block it. The component as a whole is gated on [Workflow Decomposition](../workflow-decomposition/roadmap.md), but that gate is about *porting a shape still being changed* — it does not reach a control plane, which ports nothing. [Memory Management Framework](../memory-management-framework/roadmap.md), the other stated gate, is complete.

**What this phase unblocks:** [Phase 4](phase4_the_claude_cli_activity.md) and [Phase 5](phase5_the_first_dispatch.md) directly, and [PMP Phase 5](../persistent-memory-protocol/phase5_snapshots_then_retention.md)'s recurring half.

---

## What this phase rests on — and it is not this component's research pool

**Stated plainly because it is the most useful line in this document.** [`research/synthesis.md`](research/synthesis.md) rolls up six papers and **none of them covers deployment.** That is not a gap in the evidence; it is a decision recorded elsewhere. **Do not go looking for deployment evidence in the pool, do not report its absence as a finding, and do not plan a research cycle for it.**

What this phase rests on instead:

| Source | What it supplies |
|---|---|
| The operator's deployment brief (2026-08-19) | The three-step intent: starter node → real cluster → pivot. Authoritative for this phase's scope |
| [`worker_deployment_standard.md`](../../standards/temporal/worker_deployment_standard.md) | The deployment model, binding: k3s, immutable images, multi-stage layering, task-queue naming (§2), worker entry points (§7), fail-fast dispatch (§8). **Vendored MIRROR — do not edit it here** |
| [`skyy-net-seed-handoff.md`](../skyy-net-seed-handoff.md) | D3 (two-piece topology), D5 (k3s single-node stack from the existing bootstrap), D7 (seed VM on the PBS-backed MDC), D8 (the server-placement rule) |
| [`stack_reference.md`](../../standards/architecture/stack_reference.md) | *"Temporal, SELF-HOSTED. Temporal Cloud is not on the table. Decided 2026-07-12."* And the shard-capacity consequence: a build-time one-way door we own |
| [`../../standards/architecture/research/synthesis.md`](../../standards/architecture/research/synthesis.md) | Four findings cited, not re-derived — see the two subsections below |
| First-party Temporal documentation | Read at plan time; the exact facts and their sources are in § *Runtime Verification* |

### Two findings from the product pool that this phase must act on

**Self-hosted Temporal ships an authorizer that allows every API request, and the namespace is the only credential boundary offered.** Authorisation is code we write; there is no free multi-tenancy in the substrate. For a starter node behind an internal IP with key-based access this is an **accepted risk, and the point is to write it down** rather than discover it at Phase 8's pivot. The [seed handoff](../skyy-net-seed-handoff.md) says the same thing from the other direction: OSS Temporal has no real RBAC, and for a single operator that is adequate *if stated*.

**An unresolvable assignee must PARK with a typed event — never fall back to a default queue.** This is a negative design constraint on queue topology and it costs nothing: it removes work rather than adding it. It belongs in the §A3 ruling because a fallback queue is exactly the shape a machine-axis naming scheme invites — "the machine is offline, send it to the general queue" — and the whole point of pinning work to an edge is that no other machine holds the credential or the working tree.

---

## Implementation steps

The commands themselves are an implementation task; this list is what has to happen and in what order.

- [ ] **Re-run § *Runtime Verification* below and refresh it.** It was written on 2026-08-19 against a machine with no Temporal server on it, and its whole purpose is to be replaced by observations of the thing this phase builds.
- [ ] **Identify the source images and charts from MDC and pin them.** Mirroring means the same versions, not the latest — see implementation task.
- [ ] **Decide the namespace name, and write down why.** [Per the vendored standard §2.3](../../standards/temporal/worker_deployment_standard.md), the Temporal namespace and the k8s namespace are two orthogonal identities and **neither may be derived from the other.** The names will resemble each other; that resemblance is the trap, not a derivation rule.
- [ ] **Decide the history-shard count.** First-party: *"You set Shard capacity, and often overall Temporal Service throughput, at build time and can't adjust it later."* This is one of exactly three settings on this node that a later phase cannot fix.
- [ ] **Decide the retention period, and do NOT accept the default.** The CLI default is **3 days**. The recovery contract [Phase 2](phase2_durable_dispatch_identity.md) writes requires a horizon **at least as long as the Claude Code transcript's 30-day default**, or the event history expires before the artifact it references. A 3-day namespace silently breaks a contract written one phase later.
- [ ] **Write the standup script.** Rough is fine. It is what makes [Phase 7](roadmap.md)'s three nodes and [Phase 8](roadmap.md)'s permanent control plane something other than three more manual rebuilds.
- [ ] **Stand the node up by running that script**, not by hand. If a step cannot be scripted yet, the script says so in a comment and the step is listed beside it — an honest gap in the automation is recoverable; an undocumented manual step is not.
- [ ] **Verify from this workstation, not from the node.** Health check plus a namespace list, both issued across the network path a worker will use.
- [ ] **Record which service runs where, with its port**, in this doc's § *Runtime Verification*. This is requirement 2 and it is an artifact requirement — the observation goes in the doc, not in a scratch file.
- [ ] **Name the worker→frontend path.** Write down what carries it, what has to be true for it to work, and what breaks it. This is the first answer this project has given to edge-to-brain connectivity and it should be legible as such.
- [ ] **Measure requirement 7** — attempt to poll a task queue the worker should not serve, and record what happens. See § *What this phase does not settle*.
- [ ] **Decide the machine-axis queue naming and write it into [§A3](../../standards/temporal/claude-dot-files-addendum.md).** Read [§2 of the vendored standard](../../standards/temporal/worker_deployment_standard.md) first: its convention is `<domain>-<env>`, ours needs a machine axis on top of it because Claude Code must run on the machine holding the repo. The [seed handoff](../skyy-net-seed-handoff.md) proposes `dispatch-<machine>-<env>`; that is a proposal, not a ruling, and this step is the ruling.
- [ ] **Include the no-fallback rule in the same §A3 edit.** An unresolvable assignee parks with a typed event.
- [ ] **Record the accepted risks** — the permissive default authorizer, the namespace as the only boundary, and the fact that every secret on this node is treated as compromised by construction at [Phase 8](roadmap.md).
- [ ] **Verify the whole thing again from a cold start** — reboot the node, confirm the control plane comes back without a human, and record it.

---

## §Runtime Verification

**Date:** 2026-08-19 · **Host:** `puma-workstation-mint` · **Runtime verified:** the *absence* of a Temporal control plane, the local SDK and container tooling, and the first-party documentation this phase's one-way-door decisions rest on.

**Read this section for what it is.** This phase builds the runtime it is supposed to verify, so on the day of planning there is nothing running to observe. What can be verified today is the starting state and the documented behaviour of the thing being stood up — and one of those observations is a live obstacle nobody had noticed. **The build re-runs this block against the standing node and replaces it.**

### The starting state on this workstation

```
$ hostname
puma-workstation-mint

$ which k3s kubectl helm temporal docker
/usr/bin/docker

$ docker --version
Docker version 29.7.2, build a7dcaa6

$ python3 --version
Python 3.13.12

$ python3 -m pip show temporalio | head -3
Name: temporalio
Version: 1.27.2
Summary: Temporal.io Python SDK
```

### Port 7233 on this workstation is ALREADY IN USE, and not by Temporal

```
$ ss -tlnp | grep -E '7233|7234|7235|8080'
LISTEN 0 511 127.0.0.1:8080  0.0.0.0:* users:(("code",pid=3528184,fd=62))
LISTEN 0 511 127.0.0.1:7233  0.0.0.0:* users:(("code",pid=3528184,fd=67))
```

**Both ports are held by a running VS Code process, not by a Temporal service.** A naive `exec 3<>/dev/tcp/127.0.0.1/7233` reachability probe returns *open* on this machine and means nothing — it is the editor answering. Two consequences for the build:

- **Any local port-forward to the frontend must not assume 7233 is free here**, and any "is the server up?" check that keys on a port being open will return a false positive on this workstation.
- **The Web UI's conventional 8080 collides too.** Same process, same reason.

This is exactly the class of thing the Live-Runtime Verification rule exists to catch: a plan that assumed the default ports were available would have been wrong on the very machine the health check in requirement 1 is issued from.

### First-party documentation read at plan time

| Fact | Source, fetched 2026-08-19 |
|---|---|
| **Frontend Service** — *"a stateless gateway service that exposes a strongly typed Proto API"*; handles rate limiting, authorization, validation and routing of inbound requests including worker polls. Default gRPC port **7233** | [docs.temporal.io/temporal-service/temporal-server](https://docs.temporal.io/temporal-service/temporal-server) |
| **History Service** — *"responsible for persisting Workflow Execution state to the Event History"*. Default gRPC port **7234** | same |
| **Matching Service** — *"responsible for hosting user-facing Task Queues for Task dispatching"*. Default gRPC port **7235** | same |
| **Worker Service** — *"runs background processing for the replication queue, system Workflows"*. Port not stated in that page | same |
| **Shard capacity** — *"You set Shard capacity, and often overall Temporal Service throughput, at build time and can't adjust it later."* | [docs.temporal.io/self-hosted-guide/production-checklist](https://docs.temporal.io/self-hosted-guide/production-checklist) |
| **Retention Period** — *"the duration for which the Temporal Service stores data associated with closed Workflow Executions on a Namespace in the Persistence store."* Defaults to **3 days** if unset on `temporal operator namespace create`; **minimum 1 day** | [docs.temporal.io/temporal-service/temporal-server](https://docs.temporal.io/temporal-service/temporal-server) |

**The retention row is the one that bites.** The default is 3 days; [Phase 2](phase2_durable_dispatch_identity.md)'s contract needs at least 30. Nothing warns you — a 3-day namespace works perfectly until the day someone tries to resume against history that expired.

**Re-verify before the build dispatch fires.** Temporal's documentation and its default ports both move between releases, and the four service descriptions above are the shape this phase is required to record for *our* deployment, not a substitute for recording it.

---

## Notes, decisions and gotchas

- **The vendored standard says k3s and immutable images; the [seed handoff](../skyy-net-seed-handoff.md) says workers are bare systemd processes and never containerized. Both are true and they are not in conflict.** The k3s/immutable-image model governs the **control plane** — Temporal server, Postgres, the UI — which is what this phase stands up. Workers are the other half of the topology, they run on machines that hold repos, and they arrive in [Phase 5](phase5_the_first_dispatch.md). A build run that reads §4 of the deployment standard and concludes our workers must be containerized has crossed the two halves. **MDC containerizes its workers because its activities call APIs; ours spawn `claude` against a real repo, a real toolchain and a real credential.**
- **The Temporal namespace and the k8s namespace are different identities and neither is derived from the other.** [§2.3 of the vendored standard](../../standards/temporal/worker_deployment_standard.md) is binding on this and calls the resemblance between the two names *the trap, not a derivation rule*.
- **Do not create the worker task queue as an afterthought.** Queue names are expensive to change once workers deploy against them, which is why [§A3](../../standards/temporal/claude-dot-files-addendum.md) is a requirement of this phase rather than of [Phase 5](phase5_the_first_dispatch.md), where the first worker actually appears.
- **This node is disposable by design and that changes what "good enough" means.** Internal IP, key-based access, no frills. [Phase 8](roadmap.md) destroys it rather than migrating it, because its secrets were placed before secrets management existed and are treated as compromised by construction. **Do not harden it.** Effort spent on mTLS or an ACL story here is effort spent on a machine scheduled for demolition — and it diverges from the operator's brief, which is authoritative on this phase's scope.
- **That divergence is worth naming explicitly**, because a reader will find the other side of it: D11 of the [seed handoff](../skyy-net-seed-handoff.md) describes a milestone 1 that ships *"one PR produced end-to-end under mTLS"*. The operator's later deployment brief supersedes it — the starter is no-frills and disposable. The handoff has not been amended, so a build run reading it in isolation will over-scope this phase.
- **The health check goes across the network, from this workstation.** A check run on the node proves the process started; it does not prove the thing this phase exists to deliver, which is a control plane the fleet can reach.

---

## What this phase does not settle

**Whether a worker can be prevented from polling a task queue it should not serve.** This has **no first-party documentation** — the product pool established that by enumerating the security, namespaces, multi-tenant-patterns, production-deployment and self-hosted-guide pages. The candidate answer, that a custom Authorizer gates polling, is marked in that pool as a *derived hypothesis*, not a fact.

**It matters here and nowhere cheaper.** The pinned-edge design — work runs on the machine holding the credential, because that is the only machine that can run it — assumes an answer this gap does not supply. And the §A3 queue naming this phase writes is the surface where the assumption becomes concrete. Measuring it against a standing single node that is scheduled for demolition is as cheap as it will ever be; measuring it after workers have deployed against those queue names is not.

**Requirement 7 therefore stays unchecked until the measurement exists**, and nothing in [§A3](../../standards/temporal/claude-dot-files-addendum.md) may be designed on the assumed answer. Built is not proven, and a requirement whose evidence cannot exist yet is not checked.

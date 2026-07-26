# Skyy-Net Seed — Architecture Session Handoff

**Written:** 2026-07-24, at the close of the architecture session that produced these decisions.
**Purpose:** full context transfer to future sessions (any machine, any repo name). This document is the canonical record of the durable-execution / Skyy-Net-seed direction — read it top-to-bottom before resuming this work. It supersedes session memory.
**Status of this work:** CONCEPT SETTLED, NOTHING BUILT. Operator's binding build order: standards in markdown → planning docs → dispatched builds scrutinized via PR. Do not skip ahead.

---

## The arc (how we got here)

1. The claude-dot-files CPI system matured (2026-07-24 cycle: 92 runs, 4 repos, no new failure classes — fine-tuning territory; see `cpi-decisions.md` same-date entry).
2. Operator proposed durable execution (Temporal) as the next foundation, motivated by both operations (observability, resume, HiL) and a grad Agentic AI research project (the repo is real tooling first; may be featured in the paper).
3. Scrutiny (via `/decide`) reframed "adopt Temporal?" → "what durable-state foundation replaces bash orchestration, and what's the cheapest reversible step that proves it?"
4. Exploration of Skyy-Command's existing Temporal implementation found a mature, battle-tested framework worth porting wholesale rather than rebuilding.
5. Topology analysis (repo-locality constraint + security concerns) produced the two-piece model.
6. Final reframe by operator: this is not a claude-dot-files component — it is a **separate product**, the earliest seed of **Skyy-Net** (future federated controller / central AI brain across SkyyCommands globally, plus edge use cases: Home Assistant, industrial controls, robotics).

## Settled decisions (each with its WHY — do not re-litigate without new evidence)

| # | Decision | Why |
|---|---|---|
| D1 | **Port Skyy-Command's Temporal framework; do not build fresh** | `lib/temporal/`: 298 activities / 41 workflows / 26 domains / 26 helpers, uniform naming, battle-tested. The standards trio in mdc-master-planning (`standards/development/temporal/`: temporal_standard.md 661 lines, worker_deployment_standard.md 587, stateful_patterns.md 350) is the crown jewel. Months of design already paid for. |
| D2 | **The three-layer LEGO architecture ports 100% intact** | Workflow (orchestration) → helper (pure compiler) → semantic wrappers (Layer 3a, real `@activity.defn` giving unique UI names per call-site) → generic executors (Layer 3b). Plus: ActivityResult (ok/changed/skipped/failed), ACTIVITY_MAP, error-code vocabularies with retry-semantics-by-code, anti-drift registration tuples, `delegate()` adapter. Operator explicitly wants 100% of this standard maintained. NOTE: the "unique UI names" superpower lives in `*_activities.py` (semantic wrappers), NOT `*_helper.py` (pure compilers) — keep the precise language when porting. |
| D3 | **Two-piece topology: central server + bare-metal workers** | Claude Code MUST run on the machine holding the repo (tools operate on local FS; tests must run in the app's real environment — remote mounts and SSH-driven both dead ends). Temporal workers poll the server outbound via gRPC — so workers co-locate with repos, server lives anywhere. Hub-and-spoke with no inbound trust edge to spokes. |
| D4 | **Workers are bare systemd processes, NEVER containerized** | Worker spawns `claude` needing real repo, real toolchain, real creds. Containerizing buys worse fidelity at higher complexity. Worker footprint: Python venv + temporalio + claude CLI + one systemd unit. (MDC containerizes ITS workers because its activities call APIs, not local dev environments — different constraint, different answer.) |
| D5 | **Server = k3s single-node stack, stood up by the existing Skyy-Command bootstrap** | Temporal does NOT require k8s (that's Argo). k3s chosen because: charts exist (temporal-server, temporal-postgresql, temporal-worker-lib), bootstrap exists, and the observed "dead-ass reliable" quality of SkyyCommand is the ArgoCD GitOps reconciliation loop — the pattern, not the binary. Compose would fork operational idioms for ~1GB RAM savings. Endgame (HA multi-DC Skyy-Net) is k8s-shaped; starting on k3s makes graduation add-nodes, not re-platform. |
| D6 | **This is a SEPARATE PRODUCT (Skyy-Net seed), not a claude-dot-files component** | Stack: k3s + ArgoCD + Temporal + Postgres + UI, Django dormant (rides along as future control-plane UI, excluded from initial sync). claude-dot-files remains the Claude Code config layer and becomes a CONSUMER; its bash workflow scripts eventually retire into Skyy-Net workflows. Planning home: `skyynet-master-planning` repo (exists on the VM). |
| D7 | **Deployment: seed VM on the MDC (PBS-backed); edge worker on a dev VM for testing; workstations deferred** | VM survives workstation reboots, PBS makes event history a backed-up asset, always-on for long-lived signal workflows. Edge test VM must hold a real repo clone — repo-locality IS the thing under test. Laptop/offline case stays covered later by per-machine standalone profile (`temporal server start-dev` is a single binary). |
| D8 | **Server-placement rule (binding, goes in topology standard)** | A machine hosts a Temporal server only if (a) primary dev seat / dedicated tooling VM AND (b) not itself a system under development. Everyone else is worker-only. Dev tooling must not share a failure domain with the thing under development (dev k3s clusters get demolished on purpose — reconciler work rebuilds them). This is also why "embed into SkyyCommand's own k3s/services" was REJECTED. |
| D9 | **The seed is production-discipline from day one** | Corollary of D8 turned inward: by becoming "early Skyy-Net," the seed will someday be a system under development itself. Guard: all changes flow through desired-state/ArgoCD (no hand-hacking); future Skyy-Net FEATURE development happens on a separate dev instance, never on the cluster orchestrating dev tooling. |
| D10 | **Security head-on from day one** (operator directive) | See security surface below. Becomes a first-class standards deliverable. |
| D11 | **Milestone 1 stays THIN despite the product reframe** | Strangler fig: seed VM up via bootstrap → ArgoCD+Temporal+Postgres+UI synced → ONE dispatch workflow → ONE edge worker on ONE dev VM → one PR produced end-to-end under mTLS. Django dormant. Bash scripts stay live in parallel (reversible). Everything after = adding LEGO to a running platform. |
| D12 | **Max-plan compatibility** | Activities shell out to `claude -p` with existing CLI OAuth — identical mechanism to today's bash workflows, stays on subscription. Plan rate-windows/weekly caps still apply; central server enables global rate coordination via per-queue worker concurrency caps (impossible with N independent bash scripts). VERIFY current Anthropic policy on programmatic subscription use in the research pass (policies shift; do not assert from memory). |

## What's genuinely NEW work (the ~20% not covered by the port)

- `activities/claude_cli/` domain: run `claude -p` headless with **heartbeating** (runs are 10–60 min; MDC activities are seconds-to-minutes — their standard never needed long-activity discipline) and **transcript-to-file** (payload limits ~2MB/event; history carries references, never transcripts — this is also a security control).
- `modules/dispatch/` (revision pipeline as parent workflow with semantic wrappers) and `modules/monitor/` (gh-monitor becomes a long-lived signal-receiving workflow — kills the polling loop; a pause becomes `wait_condition`, zero cost for days).
- One `dispatch-worker` per edge machine; task queues on a MACHINE axis (`dispatch-<machine>-<env>`) vs MDC's domain axis — naming convention needed in the topology standard.
- mTLS on worker↔server gRPC (likely NEW chart/config work — SkyyCommand's in-cluster workers may never have needed external mTLS).

## Security surface (day-one standards content)

- **mTLS** on the gRPC link; client certs double as "who may start workflows."
- **Tailscale ACLs:** only tagged edge VMs reach server:7233; Web UI restricted to operator devices. Existing ACL-as-code discipline, one more stanza.
- **Queue-injection threat (the real hub risk):** server compromise ≈ ability to enqueue work that spokes voluntarily execute; with `claude_cli` registered, that approximates code execution on spokes. Mitigations: the worker's registered-activity list IS its capability contract (worker-inventory discipline doing security duty); input constraints on `claude_cli` defined in its standard; network posture above.
- **Payload discipline as security control:** transcripts, secrets, repo content never in event history (it persists in central Postgres). Secrets load edge-side per MDC §8.3 pattern (.env/1Password, never workflow inputs).
- **Known accepted risks (write them down):** OSS Temporal has no real RBAC (authz = mTLS claim-mapping + network posture — adequate for single operator, must be documented); the edge VM's Claude credential is the operator's Max OAuth (whoever owns the VM codes as the operator — mitigation is VM hygiene, stated not silent).

## Standards to author (the next concrete work, all HiL through architecture session)

1. Ported + genericized Temporal trio (strip MDC worker inventories / per-system error vocabularies; keep every binding pattern).
2. Long-activity addendum (heartbeats, transcript artifacts, Max-plan rate policy via queue concurrency).
3. Topology/profiles standard (D3/D4/D5/D7/D8/D9 + machine-axis queue naming + standalone-vs-fleet per-machine profiles).
4. Security standard (surface above + accepted risks).
5. Product-boundary doc (what lives in Skyy-Net vs claude-dot-files; consumer relationship; bash-scripts retirement path).

## Open items / pending

- **Research pass (item 3 from 2026-07-24 session, NOT yet run):** what's new at Anthropic (Agent SDK, Claude Code capabilities); current Temporal mTLS/deployment best practice. **Max-plan policy item LARGELY RESOLVED 2026-07-26** via PM3's citation-grounded research paper (`CSC6905/research_project/research/raw/anthropic_tos_and_enterprise.md`): per code.claude.com legal-and-compliance (2026-02-19), consumer-tier OAuth is for purchasers' own ordinary Claude Code use; prohibited pattern is third parties routing through your credentials for THEIR users. Operator's-own-worker → operator's-own-CLI → operator's-own-use = permitted by construction. Final verify against the live page at Temporal-port build time.
- **`temporal-developer` skill adoption (investigated 2026-07-25, decision: adopt at milestone-1 build time).** Temporal's official Claude Code plugin (`temporalio/claude-temporal-plugin`, Public Preview; canonical content `temporalio/skill-temporal-developer`) — developer-assistance knowledge pack (per-SDK determinism/versioning/gotchas references), NOT runtime integration. We are beyond it architecturally (it knows nothing of our LEGO standards) but it patches the stale-SDK-training-data gap for dispatch engineers writing `temporalio` Python during the port. Two guards on adoption: (1) precedence line in the ported standards — skill is advisory, `docs/standards/temporal/*.md` binding and wins on conflict; (2) review skill content at install + after major updates (third-party auto-updating content in agent sessions, per day-one-security posture). Roadmap note: Temporal plans an eval pipeline + future operations/CLI skills; the skill's "AI patterns" reference may interest the paper.
- Repo naming/creation for the product (operator's call); planning docs land in `skyynet-master-planning`.
- `--base-branch` flag still deferred in cpi-decisions.md (watch-criteria unfired; S5 plumbing makes it a 10-min add).
- CPI watch item: abnormal terminations ~6% (see 2026-07-24 cpi-decisions entry).

## Source-material pointers (verified 2026-07-24)

- Framework: `Skyy-Command/lib/temporal/` (modules/, activities/, common/types/activity_result.py, common/activity_delegation.py, common/task_queue.py). Workers: `Skyy-Command/docker/images/workers/<domain>/<domain>_worker.py`.
- Charts: `Skyy-Command/deployments/common/temporal-server|temporal-postgresql|temporal-worker-lib`.
- Standards: `mdc-master-planning/standards/development/temporal/{temporal_standard,worker_deployment_standard,stateful_patterns}.md`.
- Exemplar of the wrapper pattern: `modules/service/onepassword/onepassword_activities.py`; registration-tuple pattern at the bottom of any `*_activities.py`.
- Session memory (path-keyed, dies on repo rename — this doc supersedes it): `project_temporal_durable_execution.md` in the claude-dot-files auto-memory dir.

## How to resume in a fresh session

Open the session in whichever repo the work targets, then: "Read docs/development/skyy-net-seed-handoff.md in claude-dot-files (or its successor location) end-to-end, then confirm the decision table before proposing anything." Guard against re-deriving settled decisions; new evidence is the only license to reopen one.

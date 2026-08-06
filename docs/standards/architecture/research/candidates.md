# Action candidates — the running list

**This file is the durable home for research action candidates. `synthesis.md` is rewritten every cycle; this is not.**

## Why it exists

A candidate surfaced in `synthesis.md` disappeared on the next research cycle, so its disposition — and the reasoning behind a rejection — went with it. Two consequences, both observed: candidates already ruled on were re-proposed in later cycles, and seven of them were parked on the standup tracker because no other surface would hold them, which the tracker's own rules forbid.

## The rule

> **Research creates and appends. Planning dispositions.**

- **Research** adds new candidates with a **stable ID**, never reused, and never renumbers an existing one.
- **Planning** sets `Status` and, for anything not shipped, the reasoning or the condition.
- **Nobody deletes a row.** A rejected candidate stays visible so it is not re-proposed — that is the whole point.

`Status` is one of: **SHIPPED** · **REJECTED** (with reasoning) · **DEFERRED** (with a condition that would bring it back) · **OPEN**.

## Provenance note — read before trusting cycle-4 rows

Cycle-3 rows come from `synthesis.md` on `main` and are settled. **Cycle-4 rows come from PR #33, which is `HOLD - redispatch` and unmerged.** Its held item concerns a currency-tier marker that C-024's costing rests on, so cycle-4 entries are **provisional** and this file gets revised if that assessment finds the evidence thin.

---

## Cycle 3 — 2026-08-04

| ID | Candidate | Source | Status |
|---|---|---|---|
| C-001 | Heartbeat clause on `python_sdk_long_activities.md` — heartbeats free at the SDK layer, billable on Cloud | `temporal.md` | **REJECTED (amended)** — billing is moot on self-hosted. The *ceiling* survives for a different reason: every heartbeat is a persistence write on our own cluster |
| C-002 | Schedule the self-host-vs-Cloud decision | `temporal.md` | **REJECTED** — decided 2026-07-12, self-hosted. Recorded in `system-overview.md` § Deployment target |
| C-003 | Decide shard capacity before the first self-hosted workflow runs | `temporal.md` | **OPEN** — build-time one-way door, and now *more* relevant since we self-host |
| C-004 | Override the default retry policy on every activity wrapping a paid API — Temporal defaults to unlimited attempts | `temporal.md` | **OPEN** |
| C-005 | Amend the Serverless Workers reading — Lambda caps an activity at 15 min | `dedicated_edge_routing.md` | **REJECTED** — k3s pods, not serverless |
| C-006 | Record that no first-party Claude ↔ Temporal runtime integration exists | `temporal.md` | **OPEN** |
| C-007 | Correct differentiator #1 in `problem-statement.md` | `bernstein_capability_mining.md` §0.1 | **SHIPPED** `b9710d5` |
| C-008 | Replace differentiator #2 with the credential version | `dedicated_edge_routing.md` §7 | **SHIPPED** `b9710d5` |
| C-009 | Add the trust-domain claim — stronger than any scheduling-model difference | `bernstein_capability_mining.md` §0.2 | **SHIPPED** `b9710d5`, promoted to differentiator #1 |
| C-010 | Resolve the queue-axis conflict before Temporal Integration is planned | `dedicated_edge_routing.md` §4.1 | **OPEN** — gates that sprint; addendum §A3 |
| C-011 | Ship three cheap guards: credential expiry, false completion, safety-hook wiring test (~9 h) | `fleet_failure_modes.md` §7 | **OPEN** |
| C-012 | Do NOT build an operator dashboard; build the blocked-work notifier | `operator_interface.md` §0, §6 | **OPEN** — the negative *is* the finding |
| C-013 | Close the "evaluate Paperclip after Phase 4" gate and rewrite the item | `paperclip_assessment.md` §7 | **SHIPPED** `b9710d5` |
| C-014 | Adopt the eight cost-S, dependency-free interface/doctrine items | `bernstein_capability_mining.md` §5 | **OPEN** — case-by-case, not a bundle |
| C-015 | Fix the missed-window assumption in the sprint plan — backwards, verified against the code | `fleet_failure_modes.md` §5.2 | **SHIPPED** `b9710d5` |
| C-016 | Design the stalled predicate as a three-way conjunction before workers are written | `paperclip_assessment.md` §4.4 | **OPEN** — claims the failure mode is live here today; **unverified** |
| C-017 | Decide dedupe granularity as a ruling, not a build | `paperclip_assessment.md` §4.3, §6 | **OPEN** — explicitly not a pair to build both of |
| C-018 | Drop any uniqueness framing on subscription-auth-at-the-edge | `paperclip_assessment.md` §4.6 | **SHIPPED** `b9710d5` |
| C-019 | Reconsider giving up cross-machine failover for *all* work | `dedicated_edge_routing.md` §5, §7 | **OPEN** — superseded by C-037's third option |

## Cycle 4 — 2026-08-06 · PROVISIONAL (PR #33 unmerged)

| ID | Candidate | Source | Status |
|---|---|---|---|
| C-020 | Restate differentiator #1 on the credential, not the topology — state both halves together | cycle-4 pool | **OPEN** |
| C-021 | Cost differentiator #1 with the self-hosted-CI-runner warning; rule on the laptop trust boundary | cycle-4 pool | **OPEN** |
| C-022 | Settle whether a Temporal worker can be prevented from polling a queue it should not serve — **before** the pinned-edge design | cycle-4 pool | **OPEN** — bears directly on C-010 |
| C-023 | Record that self-hosted Temporal ships `noopAuthorizer` by default; the namespace is the only credential boundary offered | cycle-4 pool | **OPEN** — security-relevant to the two-server split |
| C-024 | Split the sprint plan's *Tools to Evaluate* into backbone comparators and edge runtimes | cycle-4 pool | **OPEN** — the row whose evidence the held item concerns |
| C-025 | Give "nearest neighbour" an axis: bernstein by architecture, OpenClaw by thesis | cycle-4 pool | **OPEN** |
| C-026 | Add OpenClaw as ASSESSED-and-closed, not as an evaluation gate | cycle-4 pool | **OPEN** |
| C-027 | Add Hermes under a new edge-runtimes heading | cycle-4 pool | **OPEN** — an addition, not a rewrite |
| C-028 | Plan the three pre-worker recovery items as ONE design session | cycle-4 pool | **OPEN** |
| C-029 | Adopt the three-legged liveness taxonomy: stalled / looping / stranded | cycle-4 pool | **OPEN** — supersedes C-016's two-way framing |
| C-030 | Unblock quota-headroom — derivable from observed cap-errors, no provider telemetry needed | cycle-4 pool | **OPEN** |
| C-031 | No fallback queue: an unresolvable assignee PARKs with a typed event, never silently falls back | cycle-4 pool | **OPEN** — a negative design decision |
| C-032 | Amend `workflow-scripts.md` § Composition — it justifies two mechanisms with an argument supporting only the first | cycle-4 pool | **OPEN** |
| C-033 | Withdraw or downgrade `case_against.md`'s D7 — contradicted by its own primary source | cycle-4 pool | **OPEN** |
| C-034 | Switch `review-pr` to a cross-family judge — self-preference bias is causally linked to self-recognition | cycle-4 pool | **OPEN** |
| C-035 | Run E1b first — classify 30 PRs' disposition items to read out the judge's marginal yield | cycle-4 pool | **OPEN** — cheap, and it sizes C-034 |
| C-036 | Correct differentiator #1 (generality) in `problem-statement.md` | carried from C-007 | **SHIPPED** `b9710d5` |
| C-037 | Reconsider cross-machine failover — **a third option exists**: pin the credential, not the work | carried from C-019, amended | **OPEN** |

---

## Dispositions so far

**6 shipped**, all in `b9710d5`, all corrections to `problem-statement.md` and the sprint plan driven by cycle-3 evidence.

**3 rejected**, all for the same reason: they assumed **Temporal Cloud**. That decision was settled 2026-07-12 and was not written down anywhere a tool could read, so a research cycle costed out a vendor product ruled out three weeks earlier. Now recorded in `system-overview.md` § Deployment target — which is what stops C-002 and C-005 being proposed a third time.

**29 open**, of which four are rulings that gate other work: **C-010** (queue axis, gates Temporal Integration), **C-017** (dedupe granularity), **C-037** (failover), and **C-022**, which arrived in cycle 4 and bears directly on C-010.

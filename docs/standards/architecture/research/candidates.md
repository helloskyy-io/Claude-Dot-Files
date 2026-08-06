# Action candidates — the running list

**This file is the durable home for research action candidates. `synthesis.md` is rewritten every cycle; this is not.**

## Why it exists

A candidate surfaced in `synthesis.md` disappeared on the next research cycle, so its disposition — and the reasoning behind a rejection — went with it. Two consequences, both observed: candidates already ruled on were re-proposed in later cycles, and seven of them were parked on the standup tracker because no other surface would hold them, which the tracker's own rules forbid.

## The rule

> **Research creates and appends. Planning dispositions.**

- **Research** adds new candidates with a **stable ID**, never reused, and never renumbers an existing one.
- **Planning** sets `decision`; a later process sets `status`. Both carry reasoning in the Note.
- **A carried-forward candidate REUSES its original ID.** When a later cycle restates a live candidate, it is the same candidate — do not mint a new ID. (Cycle 4 restated C-007 and this file briefly carried it twice before the duplicate was removed.)
- **Nobody deletes a row.** A rejected candidate stays visible so it is not re-proposed — that is the whole point.

## Two flags, orthogonal — do not collapse them

| Flag | Values | Who sets it |
|---|---|---|
| **`decision`** | `ship` · `reject` · **blank = not yet triaged** | **`plan-sprint`, and only `plan-sprint`.** This is its triage output |
| **`status`** | `open` · `closed` | **A later process.** `plan-feature` when the item lands in a phase doc; the build that completes it |

**`ship` means "we have decided to do this." It does NOT mean done.** A shipped candidate stays `open` until something actually implements it — and neither `plan-sprint` nor `plan-tech-stack` does detailed phase design, so neither can close one on its own.

**A blank decision is not the same as `open`.** Blank means nobody has triaged it; `open` means the work is outstanding. Collapsing the two is what turns this file into a to-do list nobody agreed to — the failure that put seven untriaged candidates on the standup tracker.

**Where a decision lands depends on its size.** A candidate large enough to need its own sprint section gets one, added by `plan-sprint` — that is the extent of `plan-sprint`'s implementation. Smaller ones belong inside an *existing* phase doc, placed by `plan-feature`, and `plan-sprint` does nothing with them beyond setting `decision`.

**Every workflow that touches this file states its own portion in its prompt:** *the decision was made — implement your portion only.*

## Provenance note — read before trusting cycle-4 rows

Cycle-3 rows come from `synthesis.md` on `main` and are settled. **Cycle-4 rows come from PR #33, which is `HOLD - redispatch` and unmerged.** Its held item concerns a currency-tier marker that C-024's costing rests on, so cycle-4 entries are **provisional** and this file gets revised if that assessment finds the evidence thin.

---

## Cycle 3 — 2026-08-04

| ID | Candidate | Source | `decision` | `status` | Note |
|---|---|---|---|---|---|
| C-001 | Heartbeat clause on `python_sdk_long_activities.md` — heartbeats free at the SDK layer, billable on Cloud | `temporal.md` | `reject` | `closed` | billing is moot on self-hosted. The *ceiling* survives for a different reason: every heartbeat is a persistence write on our own cluster |
| C-002 | Schedule the self-host-vs-Cloud decision | `temporal.md` | `reject` | `closed` | decided 2026-07-12, self-hosted. Recorded in `system-overview.md` § Deployment target |
| C-003 | Decide shard capacity before the first self-hosted workflow runs | `temporal.md` | — | `open` | build-time one-way door, and now *more* relevant since we self-host |
| C-004 | Override the default retry policy on every activity wrapping a paid API — Temporal defaults to unlimited attempts | `temporal.md` | — | `open` |  |
| C-005 | Amend the Serverless Workers reading — Lambda caps an activity at 15 min | `dedicated_edge_routing.md` | `reject` | `closed` | k3s pods, not serverless |
| C-006 | Record that no first-party Claude ↔ Temporal runtime integration exists | `temporal.md` | — | `open` |  |
| C-007 | Correct differentiator #1 in `problem-statement.md` | `bernstein_capability_mining.md` §0.1 | `ship` | `closed` | `b9710d5` |
| C-008 | Replace differentiator #2 with the credential version | `dedicated_edge_routing.md` §7 | `ship` | `closed` | `b9710d5` |
| C-009 | Add the trust-domain claim — stronger than any scheduling-model difference | `bernstein_capability_mining.md` §0.2 | `ship` | `closed` | `b9710d5`, promoted to differentiator #1 |
| C-010 | Resolve the queue-axis conflict before Temporal Integration is planned | `dedicated_edge_routing.md` §4.1 | — | `open` | gates that sprint; addendum §A3 |
| C-011 | Ship three cheap guards: credential expiry, false completion, safety-hook wiring test (~9 h) | `fleet_failure_modes.md` §7 | — | `open` |  |
| C-012 | Do NOT build an operator dashboard; build the blocked-work notifier | `operator_interface.md` §0, §6 | — | `open` | the negative *is* the finding |
| C-013 | Close the "evaluate Paperclip after Phase 4" gate and rewrite the item | `paperclip_assessment.md` §7 | `ship` | `closed` | `b9710d5` |
| C-014 | Adopt the eight cost-S, dependency-free interface/doctrine items | `bernstein_capability_mining.md` §5 | — | `open` | case-by-case, not a bundle |
| C-015 | Fix the missed-window assumption in the sprint plan — backwards, verified against the code | `fleet_failure_modes.md` §5.2 | `ship` | `closed` | `b9710d5` |
| C-016 | Design the stalled predicate as a three-way conjunction before workers are written | `paperclip_assessment.md` §4.4 | — | `open` | claims the failure mode is live here today; **unverified** |
| C-017 | Decide dedupe granularity as a ruling, not a build | `paperclip_assessment.md` §4.3, §6 | — | `open` | explicitly not a pair to build both of |
| C-018 | Drop any uniqueness framing on subscription-auth-at-the-edge | `paperclip_assessment.md` §4.6 | `ship` | `closed` | `b9710d5` |
| C-019 | Reconsider giving up cross-machine failover for *all* work | `dedicated_edge_routing.md` §5, §7 | — | `open` | amended by C-037 — read both |

## Cycle 4 — 2026-08-06 · PROVISIONAL (PR #33 unmerged)

| ID | Candidate | Source | `decision` | `status` | Note |
|---|---|---|---|---|---|
| C-020 | Restate differentiator #1 on the credential, not the topology — state both halves together | cycle-4 pool | — | `open` |  |
| C-021 | Cost differentiator #1 with the self-hosted-CI-runner warning; rule on the laptop trust boundary | cycle-4 pool | — | `open` |  |
| C-022 | Settle whether a Temporal worker can be prevented from polling a queue it should not serve — **before** the pinned-edge design | cycle-4 pool | — | `open` | bears directly on C-010 |
| C-023 | Record that self-hosted Temporal ships `noopAuthorizer` by default; the namespace is the only credential boundary offered | cycle-4 pool | — | `open` | security-relevant to the two-server split |
| C-024 | Split the sprint plan's *Tools to Evaluate* into backbone comparators and edge runtimes | cycle-4 pool | — | `open` | the row whose evidence the held item concerns |
| C-025 | Give "nearest neighbour" an axis: bernstein by architecture, OpenClaw by thesis | cycle-4 pool | — | `open` |  |
| C-026 | Add OpenClaw as ASSESSED-and-closed, not as an evaluation gate | cycle-4 pool | — | `open` |  |
| C-027 | Add Hermes under a new edge-runtimes heading | cycle-4 pool | — | `open` | an addition, not a rewrite |
| C-028 | Plan the three pre-worker recovery items as ONE design session | cycle-4 pool | — | `open` |  |
| C-029 | Adopt the three-legged liveness taxonomy: stalled / looping / stranded | cycle-4 pool | — | `open` | supersedes C-016's two-way framing |
| C-030 | Unblock quota-headroom — derivable from observed cap-errors, no provider telemetry needed | cycle-4 pool | — | `open` |  |
| C-031 | No fallback queue: an unresolvable assignee PARKs with a typed event, never silently falls back | cycle-4 pool | — | `open` | a negative design decision |
| C-032 | Amend `workflow-scripts.md` § Composition — it justifies two mechanisms with an argument supporting only the first | cycle-4 pool | — | `open` |  |
| C-033 | Withdraw or downgrade `case_against.md`'s D7 — contradicted by its own primary source | cycle-4 pool | — | `open` |  |
| C-034 | Switch `review-pr` to a cross-family judge — self-preference bias is causally linked to self-recognition | cycle-4 pool | — | `open` |  |
| C-035 | Run E1b first — classify 30 PRs' disposition items to read out the judge's marginal yield | cycle-4 pool | — | `open` | cheap, and it sizes C-034 |
| C-037 | Cross-machine failover — **a third option**: pin the credential, not the work | amends C-019 | — | `open` |  |

## Evicted from the sprint plan — 2026-08-06

Nine ideas that lived in the sprint plan under *Future Ideas (Not Yet Committed)*, some since April. **None was ever committed to and none had been triaged** — a candidates list wearing a plan's clothes, which is exactly the shape this file exists to hold. Moved verbatim in substance; the plan file is not the place to park an idea.

| ID | Candidate | Source | `decision` | `status` | Note |
|---|---|---|---|---|---|
| C-038 | Cross-project intelligence — aggregate CPI analysis across repos so a pattern in one informs another | sprint plan, Future Idea A | — | `open` | needs centralized log collection or report aggregation |
| C-039 | Workflow composition / chaining — an orchestrator running a pipeline of workflows end to end | sprint plan, Future Idea B | — | `open` | **largely overtaken** — parent/child composition ships today; re-read before triage |
| C-040 | Project templates for `plan-new` — stack preferences and boilerplate decisions pre-made per project type | sprint plan, Future Idea C | — | `open` |  |
| C-041 | Team scaling — per-user config overrides, aggregated CPI, role-based workflow access, onboarding | sprint plan, Future Idea D | — | `open` | bears on the SkyyNet multi-participant question |
| C-042 | Metrics dashboard over the JSONL logs — cost trends, efficiency, failure types, agent utilization | sprint plan, Future Idea E | — | `open` | **tension**: cycle-4 evidence argues a blocked-work notifier over a dashboard |
| C-043 | `/rollback-cpi` — revert the last CPI PR and mark that pattern tried-and-failed | sprint plan, Future Idea F | — | `open` | grows in value as CPI automation increases |
| C-044 | SkyyCommand AI decision engine — the lean-agent + rich-skill pattern applied to VM placement | sprint plan, Future Idea G | — | `open` | out of this repo's scope; belongs to SkyyCommand |
| C-045 | Prompt pattern library — capture phrasings that measurably produce better output | sprint plan, Future Idea H | — | `open` |  |
| C-046 | `plan-new` greenfield — handle `git init`, initial commit and remote setup rather than requiring a repo | sprint plan, Future Idea I | — | `open` | found during the 1Password vault manager test, 2026-04-11 |

---

## Where things stand

**6 decided `ship` and `closed`**, all in `b9710d5`, all corrections to `problem-statement.md` and the sprint plan driven by cycle-3 evidence.

**3 rejected**, all for the same reason: they assumed **Temporal Cloud**. That decision was settled 2026-07-12 and was not written down anywhere a tool could read, so a research cycle costed out a vendor product ruled out three weeks earlier. Now recorded in `system-overview.md` § Deployment target — which is what stops C-002 and C-005 being proposed a third time.

**27 UNTRIAGED** — blank decision, nobody has ruled. That is `plan-sprint`'s first job. Four of them gate other work: **C-010** (queue axis, gates Temporal Integration), **C-017** (dedupe granularity), **C-037** (failover), and **C-022**, which arrived in cycle 4 and bears directly on C-010.

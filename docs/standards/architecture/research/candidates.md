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

## Provenance note

Cycle-3 rows come from `synthesis.md` on `main` and are settled. **Cycle-4 rows are also settled: PR #33 merged at `9182aea`**, and the currency-tier marker its held item concerned is resolved — `synthesis.md` records the dispatch-computed table marking all 21 carried-forward papers CURRENT. The provisional caveat this note previously carried no longer applies, and cycle-4 rows were triaged on the same footing as cycle-3.

---

## Cycle 3 — 2026-08-04

| ID | Candidate | Source | `decision` | `status` | Note |
|---|---|---|---|---|---|
| C-001 | Heartbeat clause on `python_sdk_long_activities.md` — heartbeats free at the SDK layer, billable on Cloud | `temporal.md` | `reject` | `closed` | billing is moot on self-hosted. The *ceiling* survives for a different reason: every heartbeat is a persistence write on our own cluster |
| C-002 | Schedule the self-host-vs-Cloud decision | `temporal.md` | `reject` | `closed` | decided 2026-07-12, self-hosted. Recorded in `system-overview.md` § Deployment target |
| C-003 | Decide shard capacity before the first self-hosted workflow runs | `temporal.md` | `ship` | `open` | a one-way door fixed at cluster creation. The number is **SkyyCommand's** to pick — `stack_reference.md` says this repo consumes the orchestration decision — so our action is to state the requirement before the cluster is built, not to choose it. For placement |
| C-004 | Override the default retry policy on every activity wrapping a paid API — Temporal defaults to unlimited attempts | `temporal.md` | `ship` | `open` | unlimited attempts against a per-person subscription is a rate-limit hazard, and the `claude_cli` domain is the one that wraps it. A build rule, not a sprint — for placement in Temporal Integration |
| C-005 | Amend the Serverless Workers reading — Lambda caps an activity at 15 min | `dedicated_edge_routing.md` | `reject` | `closed` | k3s pods, not serverless |
| C-006 | Record that no first-party Claude ↔ Temporal runtime integration exists | `temporal.md` | `ship` | `open` | no `anthropic/` or `claude/` in `temporalio/contrib` while OpenAI, Google ADK, LangGraph and Strands each have one. The hand-rolled `claude_cli` activity is **permanent, not a state to wait out**, and Temporal Integration should be scoped on that basis. Its secondary half — Temporal's Knowledge Base MCP Server, usable today — belongs to Sprint: MCP Servers. For placement |
| C-007 | Correct differentiator #1 in `problem-statement.md` | `bernstein_capability_mining.md` §0.1 | `ship` | `closed` | `b9710d5` |
| C-008 | Replace differentiator #2 with the credential version | `dedicated_edge_routing.md` §7 | `ship` | `closed` | `b9710d5` |
| C-009 | Add the trust-domain claim — stronger than any scheduling-model difference | `bernstein_capability_mining.md` §0.2 | `ship` | `closed` | `b9710d5`, promoted to differentiator #1 |
| C-010 | Resolve the queue-axis conflict before Temporal Integration is planned | `dedicated_edge_routing.md` §4.1 | `ship` | `open` | gates that sprint; addendum §A3. Milestone in the new **Sprint: Edge Trust & Queue Topology**, which is placed ahead of Temporal Integration precisely because this and C-022 gate it |
| C-011 | Ship three cheap guards: credential expiry, false completion, safety-hook wiring test (~9 h) | `fleet_failure_modes.md` §7 | `ship` | `open` | three independent guards at ~9 operator-hours. Cycle 4 reinforced the first: credential/session expiry at an unattended edge is unsolved and undocumented in **every** surveyed prior art, so nothing can be copied. Milestone in the new **Sprint: Fleet Liveness & Recovery** |
| C-012 | Do NOT build an operator dashboard; build the blocked-work notifier | `operator_interface.md` §0, §6 | `ship` | `open` | the negative *is* the finding — and the positive half is where the blocked-work inbox, homeless across cycles, finally gets a surface. Milestone in **Sprint: Fleet Liveness & Recovery** |
| C-013 | Close the "evaluate Paperclip after Phase 4" gate and rewrite the item | `paperclip_assessment.md` §7 | `ship` | `closed` | `b9710d5` |
| C-014 | Adopt the eight cost-S, dependency-free interface/doctrine items | `bernstein_capability_mining.md` §5 | `ship` | `open` | worth doing, and **the case-by-case ruling happens at placement, not here** — §5 already maps each to a different existing home, so none needs a sprint section: row 2 typed refusal → Workflow Decomposition · row 4 short-lived worker doctrine → Temporal Integration · row 6 no checker closes its own finding → CPI · row 8 filtered credential env at the spawn boundary → Managed Configuration · rows 9 and 11 intent capsule and loop/stall thresholds → Autonomous Operation · row 10 checkpoint contents → Temporal Integration · row 12 edge admission criterion → a `problem-statement.md` amendment, the operator's. **Row 11 converges with C-029** — plan them together or the taxonomy gets built twice. For placement |
| C-015 | Fix the missed-window assumption in the sprint plan — backwards, verified against the code | `fleet_failure_modes.md` §5.2 | `ship` | `closed` | `b9710d5` |
| C-016 | Design the stalled predicate as a three-way conjunction before workers are written | `paperclip_assessment.md` §4.4 | `reject` | `open` | **superseded by C-029**, not dropped. Its stalled-only framing is one leg of a three-legged taxonomy; ruling on both rows separately is exactly the "two partial contracts" outcome the synthesis's de-confliction warns against. The design work survives inside C-029 and C-028 — and this row's unverified claim (that the failure mode is live here today) does not need settling to build the predicate |
| C-017 | Decide dedupe granularity as a ruling, not a build | `paperclip_assessment.md` §4.3, §6 | `ship` | `open` | explicitly not a pair to build both of. **Now upstream of a live research gap** — what happens to a Task already handed to a worker that then sleeps is what sets the granularity, and nobody has researched it. Milestone in **Sprint: Fleet Liveness & Recovery** |
| C-018 | Drop any uniqueness framing on subscription-auth-at-the-edge | `paperclip_assessment.md` §4.6 | `ship` | `closed` | `b9710d5` |
| C-019 | Reconsider giving up cross-machine failover for *all* work | `dedicated_edge_routing.md` §5, §7 | `reject` | `open` | **superseded by C-037**, which is the same open ruling with the third option and the evidence that closes it. Two rows on one question produce two answers. Ruled under C-037 |

## Cycle 4 — 2026-08-06 · PROVISIONAL (PR #33 unmerged)

| ID | Candidate | Source | `decision` | `status` | Note |
|---|---|---|---|---|---|
| C-020 | Restate differentiator #1 on the credential, not the topology — state both halves together | cycle-4 pool | `ship` | `open` | **already landed at `f2b80a6`** — `problem-statement.md` § *Where we actually differ* now concedes the topology as SPIFFE Federation renamed and claims the unmintable credential, both halves in one place. Ruled `ship` because the decision was `plan-sprint`'s to make; `status` is a later process's to set |
| C-021 | Cost differentiator #1 with the self-hosted-CI-runner warning; rule on the laptop trust boundary | cycle-4 pool | `ship` | `open` | the price of the trust model, and nothing had costed it: both major CI vendors publish guidance against this exact configuration, and the mitigation — ephemeral isolated execution — is what a laptop is worst at. **The ruling half is a milestone in Sprint: Edge Trust & Queue Topology**; the `problem-statement.md` wording is the operator's, not `plan-sprint`'s |
| C-022 | Settle whether a Temporal worker can be prevented from polling a queue it should not serve — **before** the pinned-edge design | cycle-4 pool | `ship` | `open` | bears directly on C-010. The pinned-edge design assumes an answer **no first-party documentation supplies**, and "a custom Authorizer gates polling" is a derived hypothesis. Cheap now, expensive after workers exist. Milestone in **Sprint: Edge Trust & Queue Topology** |
| C-023 | Record that self-hosted Temporal ships `noopAuthorizer` by default; the namespace is the only credential boundary offered | cycle-4 pool | `ship` | `open` | there is no free multi-tenancy in the substrate — authorisation is code someone writes, and that someone is SkyyCommand, which owns the two-server split. Recording surface is `stack_reference.md` § Orchestration, which `plan-sprint` may not edit. For `plan-tech-stack` |
| C-024 | Split the sprint plan's *Tools to Evaluate* into backbone comparators and edge runtimes | cycle-4 pool | `ship` | `open` | **applied to `sprint.md` this run.** Found independently by two analysts, cost 0, and it is why an unassessed comparator looked low-priority for three cycles |
| C-025 | Give "nearest neighbour" an axis: bernstein by architecture, OpenClaw by thesis | cycle-4 pool | `ship` | `open` | **already landed at `f2b80a6`** — the axis table is in `problem-statement.md` § *The nearest neighbor* |
| C-026 | Add OpenClaw as ASSESSED-and-closed, not as an evaluation gate | cycle-4 pool | `ship` | `open` | **applied to `sprint.md` this run**, under the new edge-runtimes heading and using the entry text drafted in `openclaw_assessment.md` §7. Its absence from the comparator set was itself the finding; no evaluation gate is opened |
| C-027 | Add Hermes under a new edge-runtimes heading | cycle-4 pool | `ship` | `open` | an addition, not a rewrite. **Applied to `sprint.md` this run** — Hermes Agent (`NousResearch/hermes-agent`) had no entry to correct |
| C-028 | Plan the three pre-worker recovery items as ONE design session | cycle-4 pool | `ship` | `open` | both source papers independently say *before workers are written*, and workers arrive in Temporal Integration Stage B — so this is upstream of a sprint already queued. **It is the shape of the new Sprint: Fleet Liveness & Recovery**, not one milestone in it |
| C-029 | Adopt the three-legged liveness taxonomy: stalled / looping / stranded | cycle-4 pool | `ship` | `open` | supersedes C-016's two-way framing. Three papers each supply one leg and none states the set — the clearest case in the pool of the corpus producing something no single source contains. Milestone in **Sprint: Fleet Liveness & Recovery** |
| C-030 | Unblock quota-headroom — derivable from observed cap-errors, no provider telemetry needed | cycle-4 pool | `ship` | `open` | it corrects the gap's own stated blocker, which held it out of sequencing for two cycles. **Adopt the telemetry, NOT the rotation** — rotation presumes more than one subscription and we hold one. Milestone in **Sprint: Fleet Liveness & Recovery** |
| C-031 | No fallback queue: an unresolvable assignee PARKs with a typed event, never silently falls back | cycle-4 pool | `ship` | `open` | a negative design decision, and cost 0 — it removes work rather than adding it. A silent fallback would move work off the edge holding the credential, which the trust model forbids. Milestone in **Sprint: Edge Trust & Queue Topology** |
| C-032 | Amend `workflow-scripts.md` § Composition — it justifies two mechanisms with an argument supporting only the first | cycle-4 pool | `ship` | `open` | the fleet's core seam is stated with measured backing that exists for fresh-context and does not exist for no-authoring-authority. The design may still be right; the *justification* over-claims, and a standard that over-claims gets cited as settled. A standards amendment — `surface ≠ ratify`, human-ratified path, and `plan-sprint` may not edit `docs/standards/` |
| C-033 | Withdraw or downgrade `case_against.md`'s D7 — contradicted by its own primary source | cycle-4 pool | `ship` | `open` | **the most urgent of the surfaced items.** D7 argues against `decide ≠ act` — the seam the entire fleet is built on — and its own cited source excludes the transfer. A planning run reading the pool can act on it today. The correction is a `research/raw/` edit and belongs to a research run, not here |
| C-034 | Switch `review-pr` to a cross-family judge — self-preference bias is causally linked to self-recognition | cycle-4 pool | — | `open` | **NOT RULED — needs the operator.** "Close to a one-line change" holds only if *cross-family* means another Anthropic model. If it means another vendor, the judge moves off the subscription onto metered billing with a second credential at the edge — which trades against the affordability thesis and differentiator #1, and Sprint: Local AI Offloading already rules code review out of local offload on quality grounds. The answer flips the cost by orders of magnitude, so it is not `plan-sprint`'s to assume. C-035 is shipped independently and does not wait on this |
| C-035 | Run E1b first — classify 30 PRs' disposition items to read out the judge's marginal yield | cycle-4 pool | `ship` | `open` | cheap, and it sizes C-034. No new dispatches — it reads existing JSONL logs and PR threads — and if the marginal yield is near zero it falsifies the review stage more cheaply than any experiment that runs one. **Added as a milestone to Sprint: Continuous Process Improvement**: it is the first empirical test of whether that stage earns its keep |
| C-037 | Cross-machine failover — **a third option**: pin the credential, not the work | amends C-019 | `ship` | `open` | supersedes C-019. The third option is proxying the *model call* rather than moving the work — and OpenClaw documenting that this **does not work for `claude-cli` runtimes** is what lets the ruling close in favour of today's pinned design instead of staying open. Milestone in **Sprint: Edge Trust & Queue Topology** |

---

## Where things stand

**Triaged 2026-08-06 by `plan-sprint`. 36 rows: 30 `ship`, 5 `reject`, 1 unruled.**

**6 decided `ship` and `closed`**, all in `b9710d5`, all corrections to `problem-statement.md` and the sprint plan driven by cycle-3 evidence.

**5 rejected.** Three assumed **Temporal Cloud** — settled 2026-07-12, not written down anywhere a tool could read, so a research cycle costed out a vendor product ruled out three weeks earlier. Now recorded in `system-overview.md` § Deployment target, which is what stops C-002 and C-005 being proposed a third time. The other two, **C-016** and **C-019**, are rejected as **superseded** rather than unwanted: each is the earlier half of a question a cycle-4 row states better (C-029 and C-037), and the work survives there. Read the superseding row before concluding either idea was dropped.

**1 unruled — C-034**, and deliberately. Its blocking question is in its Note: *cross-family* means one thing if the judge is another Anthropic model and a different thing entirely if it is another vendor, and only the second trades against the affordability thesis.

**24 newly shipped.** Two were already implemented when triaged (**C-020**, **C-025** at `f2b80a6`) and three were implemented by this run as sprint-file edits (**C-024**, **C-026**, **C-027**). Eleven became milestones in two new sprint sections — **Edge Trust & Queue Topology** (C-010, C-021, C-022, C-031, C-037) and **Fleet Liveness & Recovery** (C-011, C-012, C-017, C-028, C-029, C-030) — and one expanded an existing sprint (**C-035** into Continuous Process Improvement). The remainder are **for placement**: too small for a section, awaiting a phase doc — C-003, C-004, C-006, C-014, C-023, C-032, C-033.

**`ship` is not `done`.** Every shipped row stays `open` until something implements it; `plan-sprint` does no phase design and closes nothing.

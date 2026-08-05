# Synthesis — product-level research

**Cycle:** 2026-08-05 · **Pool:** 21 papers · **Tier:** Large / architecture-layer · **This cycle: a REFRESH — 1 paper revalidated, 0 added**

Read this instead of the pool. It says what the evidence means for the product's direction and ends in reviewable candidates. Nothing here is binding — research is evidence, and a finding becomes a rule only by being codified into a standard through human review.

**This is a revalidation cycle, not a research cycle.** The refresh gate found exactly one paper past its window — `raw/temporal.md`, the pool's oldest and the substrate every Temporal-related roadmap item depends on. The 2026-08-04 cycle flagged it and explicitly declined to act on it (`topics.md` § *Retirements*: "that is a refresh decision, not this cycle's"). It has now been revalidated, and the result is larger than a re-dating: **the paper's topic was re-scoped, its central thesis was corrected, and it produced one finding that contradicts a sibling paper validated two days earlier.**

The prior cycle's substance — the trajectory question, the five new papers, the plannable list — is unchanged and is carried forward below. **What a standup should read is § *Synthesis diff* at the end.**

---

## Inputs

**Refreshed this cycle.**

| Paper | Last validated | Revalidate | Critic verdict |
|---|---|---|---|
| `raw/temporal.md` | **2026-08-05** | **high — 6 weeks** (top of §5's high band, with an on-announcement override trigger list) | **PASS-WITH-FIXES** — two independent critic passes. Pass 1: 4 blocking (all MISCITED, **zero fabricated**) — a release count that was a truncated-fetch artifact asserted under an "enumerated, not counted by a retrieval layer" heading; two false negatives on Cloud pricing and the billable-Action definition that were repo-path absences written up as documentation absences; and a restructure claim built on a path the paper itself constructed. Pass 2 verified all four repairs at source and caught the pricing repair **converting one defect into a new miscitation** (an invented marketing-page plan-count discrepancy) plus a **stale dependent** left by the recommendation reversal. Round 3 fixed both. All 11 counts independently re-derived; 38 sources, S1–S38 contiguous |

**Carried forward, unchanged. The pool now has NO past-window paper for the first time since 2026-07-04.**

| Paper | Last validated | Revalidate | Critic verdict |
|---|---|---|---|
| `raw/bernstein_capability_mining.md` | 2026-08-04 | high — 2 weeks | PASS-WITH-FIXES |
| `raw/paperclip_assessment.md` | 2026-08-04 | high — 4 weeks | PASS-WITH-FIXES |
| `raw/operator_interface.md` | 2026-08-04 | high — 4 weeks | PASS-WITH-FIXES |
| `raw/dedicated_edge_routing.md` | 2026-08-04 | high — 6 weeks | PASS-WITH-FIXES |
| `raw/fleet_failure_modes.md` | 2026-08-04 | high — 4 weeks | PASS-WITH-FIXES |
| `raw/backbone_edge_generality.md` | 2026-08-03 | high — 6 weeks | PASS-WITH-FIXES |
| `raw/case_against.md` | 2026-08-03 | high — 4 weeks | PASS-WITH-FIXES |
| `raw/code_routed_control_flow.md` | 2026-08-03 | high — 6 weeks | PASS |
| `raw/combination_prior_art.md` | 2026-08-03 | high — 4 weeks | PASS-WITH-FIXES |
| `raw/convergence_stopping.md` | 2026-08-03 | high — 6 weeks | PASS |
| `raw/subscription_economics.md` | 2026-08-03 | high — 2 weeks | PASS |
| `raw/workflow_reuse_boundary.md` | 2026-08-03 | high — 6 weeks | PASS-WITH-FIXES |
| `raw/python_sdk_long_activities.md` | 2026-08-03 | high — 4 weeks | PASS-WITH-FIXES |
| `raw/durable_execution.md` | 2026-07-27 | low — 6 months | PASS |
| `raw/claude_code_integration_surface.md` | 2026-07-25 | high — 4 weeks | PASS |
| `raw/hierarchical_agents.md` | 2026-07-25 | medium — 3 months | PASS |
| `raw/hook_sourcing_supplement.md` | 2026-07-25 | high — 4 weeks | PASS |
| `raw/anthropic_tos_and_enterprise.md` | 2026-07-24 | high — 4 weeks | PASS |
| `raw/production_cases.md` | 2026-07-23 | medium — 3 months | PASS |
| `raw/reflection_literature.md` | 2026-07-23 | medium — 3 months | PASS |

⚠️ **Two papers come due within days** — `subscription_economics.md` and `bernstein_capability_mining.md` both carry `high — 2 weeks` against a 2026-08-03/04 validation, so both fall due around **2026-08-17**. `claude_code_integration_surface.md`, `hook_sourcing_supplement.md` and `anthropic_tos_and_enterprise.md` follow around 2026-08-22.

**No papers were retired.** One topic was **re-scoped** — see below.

---

## What the refresh changed

### 1. The Temporal paper was a pre-standard artifact, and that was the real finding

`raw/temporal.md` was 39 lines: an ASCII table of "agentic failure mode → Temporal primitive", two paragraphs of uncited assertion, and a header. **No citations. No honest-boundary section. No content arc.** Under Research Standard §3 that is three separate entries on the *"breaking it looks like"* list, and it had been consumed as the substrate paper for a live phase since 2026-07-04.

It is now 799 lines against the §3 contract with 38 sources. **The refresh gate found this only because the paper aged out** — nothing in the pipeline checks a paper against the contract on the way in. That is a gap in the tooling, not in the standard.

Two unsourced claims were **removed** and the removal recorded so it is auditable rather than silent: a named-companies adoption assertion (*Sourcegraph's Cody, Databricks' agent operations, Fireflies, Vercel's AI SDK backends*) and a quantified figure (*"reinventing 60% of it in Redis + Postgres + wrappers"*). Neither was locatable.

### 2. The paper's central thesis was backwards

The old paper's closing argument was that the LangGraph/CrewAI layer *"skips almost every one of the failure modes above. Prototype-grade orchestration, not production-grade."*

**Temporal ships `temporalio/contrib/langgraph`**, which runs LangGraph nodes as Temporal activities to give them durable execution, retries and timeouts. The `contrib` directory also carries `openai_agents`, `google_adk_agents` and `strands`. **The relationship is composition, not substitution** — the framing that made LangGraph a rejected alternative was wrong, and it was load-bearing for how the two layers were being positioned.

### 3. The topic was re-scoped — the old question was dead

*"Does Temporal supply what a durable workflow layer needs, and at what cost in complexity?"* failed on both halves. The **supply** half is decided — Temporal is chosen and the port is underway, so continuing to ask it is decide-then-justify, which §0 explicitly distinguishes from research's job. The **evidence** half was taken by siblings between 2026-07-27 and 2026-08-04: heartbeat and payload limits went to `python_sdk_long_activities.md` (which names `temporal.md` in its own citations as the paper whose gap it closes), routing and placement to `dedicated_edge_routing.md`, concepts to `durable_execution.md`.

**Not a retirement** — §6 retires a topic whose *subject* died, and Temporal is the substrate of a live phase. The sweep found a real, unowned question underneath: **nobody in the pool owned the cost and commitment of the vendor.** No paper stated the licence (**MIT**). No paper priced Cloud. No paper carried the upgrade obligation or the shard-capacity one-way door. The paper now owns that.

### 4. Vendor facts that were never in the pool

- **Licence: MIT.** The single most important vendor fact, and it was nowhere in 21 papers.
- **Shard capacity is fixed at build time and cannot be adjusted later.** A self-hosted stand-up done casually encodes a throughput ceiling nobody chose. This is a one-way door taken *before the first workflow runs*.
- **The default retry policy is unlimited max attempts.** Every activity wrapping a paid API must override it — cheap to enforce, expensive to discover in production.
- **Workflow-execution limits:** 51,200 events / 50 MB history; 2,000 pending per class; 30 pending Nexus.
- **Updates** are the primitive for an approval gate that needs acknowledgement — the old paper's table had Signals but not Updates.
- **Child workflows do not carry over continue-as-new**, which collides with continue-as-new being the required history-bounding mechanism. Guidance caps children at ~1,000 per parent.
- **Workflow Pause** (server v1.30.0+) and **Workflow Streams** are new primitives, neither previously in the pool.
- **No first-party Anthropic/Claude runtime integration exists.** Established as a negative *by enumeration* — `temporalio/contrib` has 11 entries and contains no `anthropic/` and no `claude/`. Temporal's Anthropic surface is a *tooling* relationship (a Claude Code plugin, two Skills, a Knowledge Base MCP Server), not a runtime one.

### 5. Self-host-vs-Cloud is no longer research-blocked — and the refresh proved it twice

The refresh's first pass reported "no first-party definition of a billable Action" and called it the single blocker on the decision. **That was false**, and the critic closed it: `docs/glossary.md` (raw) defines an Action as the fundamental pricing unit, and `/cloud/actions` enumerates **eleven** billable categories — Workflow, Activity, Timer, Signal, Query, Update, Schedule, Nexus, Export, Fairness, Capacity.

**The decision is now a sizing question against a documented model, not a missing definition.** The residual unknown is a measurement, not a gap. Two things fell out of the correction:

- **The Essentials plan is "greater of $100/mo or 5% of Usage Spend"** — a *floor on a usage-scaled fee*, not an entry price. For a small-usage single-operator fleet 5% sits below $100, so the floor binds and $100 is the real number — but a plan table that reads "starting at $100" hides that.
- **Activity heartbeat recording is a billable Action.** See below — this is the cycle's sharpest cross-paper finding.

---

## The correction that traces to a dependent paper

**`python_sdk_long_activities.md` (validated 2026-08-03, PASS-WITH-FIXES) recommends heartbeating per `stream-json` line on a 10–60 minute activity, on the stated reasoning that the SDK's throttle "makes per-line heartbeats free."**

That reasoning is **correct about SDK and network cost and does not transfer to Temporal Cloud billing** — a heartbeat that reaches the server is a billable Action. This repo's hour-long `claude_cli` activity is exactly the shape where it bites.

Per §4 the correction traces to **all** its dependents, so stating the bound matters as much as stating the hazard: the same throttle that makes heartbeats free locally also **caps what they can cost** — the effective interval is `min(0.8 × heartbeat_timeout, max_heartbeat_throttle_interval)` with a 60 s default, so a 60-minute activity emits **at most ~60 heartbeat Actions**. **Per-line heartbeating does not mean per-line billing.** The sibling's recommendation survives; its *justification* needs one clause added, and a planner costing Cloud needs the ceiling or they will over-price it.

Dependents identified: `python_sdk_long_activities.md` §1.4 / §7.3 (the recommendation and its rationale); any Cloud cost model built for `Phase: Temporal Integration`; and action candidate 5 below.

**A second cross-paper note, smaller:** Serverless Workers on **AWS Lambda cap an activity at 15 minutes**, so Lambda cannot host this repo's 10–60 minute `claude_cli` activity — **only Cloud Run is shape-compatible.** `dedicated_edge_routing.md` treats Serverless Workers as a single option; it is two, and one of them is ruled out by shape.

**A third, purely mechanical:** `python_sdk_long_activities.md` §8's negative finding (no first-party sample or documented pattern for a long/subprocess-wrapping activity) has a search method that did not include `docs/design-patterns/`, which contains `long-running-activity.mdx`, `resumable-activity.mdx` and `polling.mdx`. **None is subprocess-specific, so the gap is not closed** — but the claim of absence should be re-stated against that directory at the sibling's next touch. Likewise, server-side Worker Deployment APIs went GA at v1.31.0 while the newer `CreateWorkerDeployment*` APIs remain pre-release; `dedicated_edge_routing.md` line 51 characterises the *CLI command's* experimental note, which is a different object — no contradiction, but worth a look at its next touch.

---

## Carried forward from the 2026-08-04 cycle — unchanged

The prior cycle asked *is the trajectory right, and what are we missing for the end goal?* and answered: **the trajectory is right, and the expensive-looking work is mostly already solved by decisions already made.** Nothing in this refresh disturbs that. In brief, and unchanged:

1. **Differentiator #1 has moved.** The nearest neighbour generalised its execution boundary to five modalities with one typed result contract, two verified by something other than tests, while its *positioning* stayed code-framed. Honest restatement: *"comparable systems are sold for code; the nearest one generalised its boundary without generalising its product."*
2. **Differentiator #2 holds for the wrong stated reason.** "Role-pull assumes fungible workers distinguished by a label" is refuted — labels are how Kubernetes, Slurm and Temporal itself address physical hardware. **The differentiator that survives every counter-case is the credential.** The stronger unstated claim is the trust domain: bernstein's fleet is *"not multi-tenant in the security sense"* and lists cross-org federation as out of scope.
3. **The operator interface: the field is unanimous, and the answer is still mostly "don't build it."** Ten of ten comparable systems ship one, no counter-example located — but it is ~70% met here already, and the genuine gap is *liveness*, which the Temporal port supplies free.
4. **The free lessons.** Already immune: LLM-in-the-coordination-loop, persistent-session sleep, file-lock deadlock, headless early-stop, turn-cap exhaustion. Most exposed, none deleted by the port: credential expiry at an unattended edge (~2h), false completion (~4h), the safety hook silently not firing (~3h).
5. **Paperclip: MINE AND DISCARD.** Architecture rejected on four grounds; seven capabilities taken; the roadmap item's own text is wrong and should be replaced.

The full plannable list — the pre-worker decisions (~1 week of planning, no build), the cheap guards (~9 operator-hours for the top three), the eight cost-S doctrine items, and the sequenced operator surface — stands as written in the 2026-08-04 synthesis and is not restated here. **Three items in it are amended by this refresh** and are called out in the candidates below.

---

## Action candidates

Reviewable items, sized for a standup. Nothing is ratified. Per §7 this run surfaces candidates and writes nothing outside `research/` — routing is the reviewer's and the operator's.

**New or changed this cycle** (1–6). **Carried forward unchanged** (7–19).

| # | Candidate | Type | Rests on |
|---|---|---|---|
| 1 | **Add a clause to `python_sdk_long_activities.md`'s heartbeat recommendation: heartbeats are free at the SDK/transport layer and BILLABLE on Temporal Cloud.** The recommendation survives; its justification does not. State the ceiling with it — `min(0.8 × heartbeat_timeout, 60 s)` bounds a 60-minute activity at ~60 heartbeat Actions — or a planner will over-price Cloud | change direction | `temporal.md` §3.2 item 1; `python_sdk_long_activities.md` §1.4, §7.3 |
| 2 | **Self-host-vs-Cloud is no longer research-blocked — schedule the decision.** It is a sizing question against a documented billing model (11 enumerated Action categories, "greater of $100/mo or 5% of usage"). The residual unknown is a measurement: run one representative agent workflow against the $1,000 trial credit and read the billed Action count, instrumenting the heartbeat contribution separately | adopt | `temporal.md` §3.2, §8 T3 |
| 3 | **Decide shard capacity deliberately before the first self-hosted workflow runs.** It is fixed at build time and not adjustable later — a casual stand-up encodes a throughput ceiling nobody chose. **Belongs on the pre-worker decision list beside the queue-axis and Worker-Deployment-topology items**, which are the same class of one-way door | adopt | `temporal.md` §3.1, §8 T2 |
| 4 | **Override the default retry policy on every activity wrapping a paid API.** Temporal's default is **unlimited max attempts**. Against a metered LLM API that is a cost hazard; against a subscription it is a rate-limit hazard. Cheap to enforce as a lint or a base class, expensive to discover in production | adopt | `temporal.md` §2.2, §5 |
| 5 | **Amend the Serverless Workers reading in `dedicated_edge_routing.md`: Lambda caps an activity at 15 minutes and cannot host the 10–60 minute `claude_cli` activity. Only Cloud Run is shape-compatible.** The paper treats Serverless Workers as one option; it is two, and one is ruled out by shape | change direction | `temporal.md` §6.2 |
| 6 | **Note that no first-party Claude ↔ Temporal RUNTIME integration exists** — established by enumerating `temporalio/contrib` (11 entries, no `anthropic/`, no `claude/`) while OpenAI, Google ADK, LangGraph and Strands all have one. The Anthropic surface is developer tooling. **The hand-rolled integration is not a temporary state to wait out**, and `Phase: Temporal Integration` should be scoped on that basis | adopt | `temporal.md` §6.3 |
| 7 | **Correct differentiator #1 in `problem-statement.md`** — the nearest neighbour has already generalised its execution boundary | change direction | `bernstein_capability_mining.md` §0.1 |
| 8 | **Replace differentiator #2's wording with the credential version.** Replacement wording is drafted | change direction | `dedicated_edge_routing.md` §7 |
| 9 | **Add the trust-domain claim to `problem-statement.md`** — stronger and more durable than any scheduling-model difference | adopt | `bernstein_capability_mining.md` §0.2 |
| 10 | **Resolve the queue-axis conflict with the vendored Worker Deployment Standard before `Phase: Temporal Integration` is planned.** Standards-amendment candidate — the vendored file must not be edited here | new concept | `dedicated_edge_routing.md` §4.1 |
| 11 | **Ship the three cheap guards: credential expiry, false completion, safety-hook wiring test. ~9 operator-hours** | adopt | `fleet_failure_modes.md` §7 |
| 12 | **Do NOT build an operator dashboard.** Build the blocked-work notifier (1–2 days) and give the inbox a roadmap home (0.5 days) | no change *(the negative is the finding)* | `operator_interface.md` §0, §6 |
| 13 | **Close the "evaluate Paperclip after Phase 4" gate now and rewrite the item's text** | adopt | `paperclip_assessment.md` §7 |
| 14 | **Adopt the eight cost-S, dependency-free interface/doctrine items** | adopt | `bernstein_capability_mining.md` §5 |
| 15 | **Fix the missed-window assumption in `roadmap.md` — it is backwards, verified against the code** | change direction | `fleet_failure_modes.md` §5.2 |
| 16 | **Design the stalled predicate as a three-way conjunction before workers are written** | adopt | `paperclip_assessment.md` §4.4 |
| 17 | **Decide the dedupe granularity as a ruling, not a build** | adopt | `paperclip_assessment.md` §4.3, §6 |
| 18 | **Drop any uniqueness framing on subscription-auth-at-the-edge** | change direction | `paperclip_assessment.md` §4.6 |
| 19 | **Reconsider giving up cross-machine failover for *all* work** — Temporal's own pattern is two-tier | new concept | `dedicated_edge_routing.md` §5, §7 |

**Retired candidate.** The prior cycle's candidate 14 — *"Refresh `raw/temporal.md`, the pool's only past-window paper, carried from two prior cycles"* — **is done. This cycle is its execution.**

---

## Homeless findings

Named here rather than parked elsewhere, per §7 — a homeless finding means the surface is missing.

- **This repo has no surface that holds "an upstream standards amendment we owe."** Carried from three prior cycles. The Research Standard is **vendored MIRROR** from `MDC-Master-Planning`, so amendments cannot be made here. **This cycle adds a fourth owed amendment** (below), and the two methodology findings it corroborates were already owed. **The missing surface is the finding.**

- **A count read through a summarizing fetch layer is unreliable — now corroborated a THIRD time, in a new failure shape.** Prior cycles measured seven fetches producing seven different totals with `truncated: false` present and wrong every time. This cycle adds a cleaner instance: the GitHub releases API returned **the same 7 objects for `?per_page=15` and `?per_page=100`**, while pages 2 and 3 of the same endpoint yielded 12 more — and in one fetch the layer's own self-reported element count disagreed with the rows it returned. **A page total is not a population.** Three independent corroborations across two analysts, two codebases and now an API is past the threshold where this is an observation.

- **A repaired span is a new claim — and this cycle MEASURED the conversion a second time, in the round that was supposed to be the safe one.** The round-2 repair that correctly added a fourth Temporal Cloud plan **also invented a marketing-vs-documentation discrepancy to justify itself**, and then used that invention to tell readers to distrust a source. It survived the analyst's own verification and was caught only by a second, independent critic. The rule is already in §3; what is missing is the **structural** answer — this defect class exists *only because review is happening*, and the round that closes findings gets the least scrutiny. **Two independent critic passes is what caught it.** That is the finding: a single critic round is not sufficient for a substantially-rewritten paper.

- **A NEW owed amendment: §3's paper contract is not checked on the way IN, only on the way out via the refresh gate.** `temporal.md` sat in the pool for a month as the substrate paper for a live phase while violating three separate "breaking it looks like" clauses — no citations, no honest boundary, no content arc. It was caught because it **aged out**, not because anything checked it. A pre-standard paper that never ages past its window is never checked at all. Same missing upstream surface.

- **A defined shape for production feedback.** Carried from three prior cycles and still homeless.

- **The sizing rubric's bands are calibrated for components whose destination is a plan.** This component's destination is a thesis plus a roadmap plus a live competitive field — 21 topics against a Large band of 8–10. Same vendored-standard problem.

---

## Gaps this cycle did not cover

A refresh cycle covers one paper; the standing gap list is unchanged except where noted.

- **Decide-only disposition — does a judging stage with no authoring authority actually reduce defects?** **Displaced for a third consecutive cycle**, though this one is a refresh and had no topic slot to give it. The prior cycle's warning stands and hardens: *a topic displaced twice is at risk of being displaced permanently — the next cycle should either run it or retire it explicitly.* **It is now three.**
- **New, from this refresh, and unowned: what a billable Action actually costs for THIS workload.** The definition is closed; the measurement is not. Blocking nothing today, but it is the input to candidate 2 and it is a minutes-long test, not a research topic.
- **Multi-edge identity, trust and credential distribution.** Established as **not mineable** — the nearest neighbour is explicitly single-trust-domain. Needs its own pass with no reference implementation.
- **The quota-headroom view.** Genuinely novel, falls out of the affordability thesis, and **not sequenceable yet** — blocked on one minutes-long test and one unread document.
- **Whether an agentic `claude -p` run decomposes into resumable per-turn legs** — still uncovered; decides the port's shape.
- **Temporal patching/versioning cost** and the **OpenAI Agents GA-vs-Preview contradiction** across three first-party surfaces — both left open by this refresh, both stated with their search methods in `temporal.md` §9.
- **Provider-shaped edges**, **duplicated prompt prose**, **inter-process handoff wire format** (phase-level, redirected), **reflection-channel mining**, and **bash → Python Stage A** — all unchanged in status.
- **Certification and conformity regimes for a physical edge** — still unanswerable without paid standards access.

# Topics — product-level research

**Last assessed:** 2026-08-06 (cycle 4 — 4 topics added, 0 retired)

## Sizing

**Tier: Large / architecture-layer.** The destination is the stack itself, not a phase of it: `docs/development/roadmap.md` (the authoritative destination list), `docs/standards/architecture/problem-statement.md` (what the system is for), and `system-overview.md` (what exists). A finding here can invalidate the premise of a phase rather than its sequencing, which is [Research Standard §1](../../research/research_standard.md)'s holistic altitude at its purest.

**The frame set on 2026-08-04 and corrected on 2026-08-05 stands, and this cycle does not re-open it.** Three things are settled and are inputs, not questions:

- **Novelty is closed.** The problem statement states the four elements as *the known recipe* and the intent as *"to execute it better than anyone else, and to acquire the lessons rather than re-learn them."* **Mining is the stated strategy**, so a finding that a competitor does something better is a win. This inverts what makes a comparator topic worth running: the question is never *are we threatened*, it is *what is takeable*.
- **The altitude.** This repo is **Jarvis, the assistant edge**, under SkyyCommand under SkyyNet. Every topic is judged against the federated destination.
- **The deployment target.** `system-overview.md` § *Deployment target* records it: **Temporal is SELF-HOSTED; Temporal Cloud is not on the table** (decided 2026-07-12) — two servers never combined, HA on k3s, systemd workers. Cycle 3 did not have this written down and priced Cloud against a deployment ruled out three weeks earlier. Cloud pricing, billable Actions and serverless worker patterns are **out of scope for every topic on this list.**

**Topic count: 25 — fifteen above the rubric's 8–10 band, and the second consecutive overrun.**

The previous assessment recorded the overshoot as *"a finding about the rubric"* and surfaced it as a homeless finding needing an upstream amendment. **That reading is incomplete, and this cycle corrects it.** §2 already anticipates a list running past the band and prescribes a remedy before band-widening is even considered: *"A component whose topic list runs well past 8–10 usually has **more than one destination** — a plan, plus a thesis, plus a competitive read are three consumers, not one — and the correct response is to check whether it is one component before widening the band. Split it per §6 and each part sizes normally."*

That sentence describes this pool exactly, using this pool's own three destinations as its example. The pool has never been checked against it. On inspection the 25 topics fall into three destination groups:

| Group | Consumer | Topics |
|---|---|---|
| **The thesis** | `problem-statement.md` | 9 |
| **The plan** | `roadmap.md` + phase docs | 12 |
| **The competitive read** | `problem-statement.md` § *The nearest neighbor* + `roadmap.md` § *Tools to Evaluate* | 4 |

Each group sizes at or near a normal band. **The overrun is a splitting signal, not a calibration failure**, and the standard does not need amending to accommodate it — it needs applying. *(This is this cycle's own inference from §2's text against the pool, not a finding from an analyst. The split itself is a structural change to `research/` and is surfaced as an action candidate for the operator, not executed here.)*

**This cycle covers 4 of the 25.** §2 caps a cycle at ~5. The 21 existing papers hold and are not rewritten — the currency table computed at dispatch marks **all 21 current, with none past its window**, and revalidation is `research-refresh`'s job.

**Consumer:** the synthesis feeds a master-planning pass that will revise `roadmap.md`. A finding must carry what the capability is, why it matters for the federated destination, what evidence supports it, and roughly what it costs to build. A finding a planner cannot sequence cannot be planned.

## Topics

Dates and intervals below are the **computed currency table supplied at dispatch**, which is authoritative over any prior synthesis.

| Topic | Feeds | Paper | Last validated | Revalidate |
|---|---|---|---|---|
| **OpenClaw — durability, generality, dispatch model, credential locality, and what is mineable** | `roadmap.md` § *Tools to Evaluate* — the comparator set; `problem-statement.md` § *The nearest neighbor* — whether that designation still holds | `raw/openclaw_assessment.md` | *(new this cycle)* | — |
| **Hermes — the same axes, independently assessed** | `roadmap.md` § *Tools to Evaluate*; `problem-statement.md` § *The nearest neighbor* | `raw/hermes_assessment.md` | *(new this cycle)* | — |
| **Multi-edge identity, trust and credential distribution across trust boundaries** | `problem-statement.md` § *Where we actually differ* **#1 — the strongest claim we make and the least evidenced**; § *The edges*; `Phase: Temporal Integration` — worker identity and credential locality | `raw/edge_identity_trust.md` | *(new this cycle)* | — |
| **Decide-only disposition — does a judging stage with no authoring authority actually reduce defects?** | `problem-statement.md` element 2; validates `docs/standards/workflow-scripts.md § Composition` (line 417) — the author ≠ judge seam | `raw/decide_only_disposition.md` | *(new this cycle)* | — |
| Mining the nearest neighbor — what `bernstein` ships that we do not | `roadmap.md` — new items across phases; `problem-statement.md` § *The nearest neighbor* | `raw/bernstein_capability_mining.md` | 2026-08-04 | high — 2 weeks |
| Paperclip — durability machinery, operator surface, Claude Code integration | `roadmap.md` § *Tools to Evaluate* → the closed "evaluate after Phase 4" item; `Phase: Temporal Integration` | `raw/paperclip_assessment.md` | 2026-08-04 | high — 4 weeks |
| The operator interface — is a control surface a requirement, and what must it show | `roadmap.md` — **no phase holds this today**; the named gap | `raw/operator_interface.md` | 2026-08-04 | high — 4 weeks |
| Dedicated non-fungible edges vs. central-queue claim-and-contend | `problem-statement.md` § *Where we actually differ* #2; `Phase: Temporal Integration` — worker placement and queue naming | `raw/dedicated_edge_routing.md` | 2026-08-04 | high — 6 weeks |
| What the field learned the hard way running long-lived agent fleets | `roadmap.md` sequencing overall; `Phase: Autonomous Operation` — exit criteria and failure behaviour | `raw/fleet_failure_modes.md` | 2026-08-04 | high — 4 weeks |
| Temporal as a vendor commitment | `Phase: Temporal Integration` — the upgrade cadence the fleet must keep and the workflow-side primitive surface. Explicitly NOT activity mechanics nor worker placement | `raw/temporal.md` | 2026-08-05 | high — 6 weeks |
| Durable execution | `problem-statement.md` element 1; `Phase: Temporal Integration` — whether durability is the binding constraint | `raw/durable_execution.md` | 2026-07-27 | low — 6 months |
| Claude Code integration surface | `Phase: Temporal Integration` → the `claude_cli` activity domain | `raw/claude_code_integration_surface.md` | 2026-07-25 | high — 4 weeks |
| Anthropic ToS and enterprise auth | `problem-statement.md` § *The edges* — whether subscription auth at the edge is **permitted** | `raw/anthropic_tos_and_enterprise.md` | 2026-07-24 | high — 4 weeks |
| Hook sourcing | `Phase: Managed Configuration` — setting-source loading and the ⚠️ safety blocker | `raw/hook_sourcing_supplement.md` | 2026-07-25 | high — 4 weeks |
| Hierarchical agents | `problem-statement.md` element 2; `Phase: Workflow Decomposition` — parent/child composition | `raw/hierarchical_agents.md` | 2026-07-25 | medium — 3 months |
| Reflection literature | `problem-statement.md` element 2; `Phase: Continuous Process Improvement` | `raw/reflection_literature.md` | 2026-07-23 | medium — 3 months |
| Production cases | `roadmap.md` overall — what other teams hit | `raw/production_cases.md` | 2026-07-23 | medium — 3 months |
| Convergence and the plateau | `Phase: Autonomous Operation` — observable exit criteria; the loop-back bound in `revision.sh` | `raw/convergence_stopping.md` | 2026-08-03 | high — 6 weeks |
| Parameterize vs fork | `Phase: Workflow Decomposition`'s gating ruling | `raw/workflow_reuse_boundary.md` | 2026-08-03 | high — 6 weeks |
| Long activities, Python SDK | `Phase: Temporal Integration` → the `claude_cli` activity domain | `raw/python_sdk_long_activities.md` | 2026-08-03 | high — 4 weeks |
| Prior art on the combination | **Re-pointed** (below) — `problem-statement.md` § *The nearest neighbor* and the mining strategy | `raw/combination_prior_art.md` | 2026-08-03 | high — 4 weeks |
| Code-routed control flow | `problem-statement.md` element 3 and 4; `system-overview.md` § *What is not built* | `raw/code_routed_control_flow.md` | 2026-08-03 | high — 6 weeks |
| Subscription economics as enabler | `problem-statement.md` § *Affordability is the enabler* | `raw/subscription_economics.md` | 2026-08-03 | high — 2 weeks |
| The case against | **Re-pointed** (below) — `problem-statement.md` overall, as the standing adversarial brief | `raw/case_against.md` | 2026-08-03 | high — 4 weeks |
| Backbone / edge generality | `problem-statement.md` § *Where we actually differ* #1 and § *The edges* | `raw/backbone_edge_generality.md` | 2026-08-03 | high — 6 weeks |

### Two papers whose destination moved, and why their headers were not edited

`combination_prior_art.md` and `case_against.md` both carry `Feeds:` lines naming sections of `problem-statement.md` that **no longer exist** — the novelty section and the gap claim. Both papers are the reason those sections were rewritten; the problem statement now names them explicitly as the two that forced it.

The destinations are re-pointed **here, in this table, and the paper headers are left alone.** A paper's header records the question it was commissioned to answer and the state it was verified in; rewriting it to match a document the paper itself changed would erase the trace of *why* the document changed. Recorded explicitly because a reader checking header-against-destination will otherwise read this as drift.

*(`temporal.md` is the opposite case and was handled the opposite way — its **question** was replaced by the 2026-08-05 refresh, not just its destination, so its header was edited to record the new commission. The two cases should not be read as inconsistent.)*

### Why these four

Cycle 3 asked *is the trajectory right, and what are we missing for the end goal?* and answered: the trajectory is right. This cycle takes the two things that answer left open — **an incomplete competitive read** and **the least-evidenced claim in the thesis** — and adds the one topic the pool's own memory says must now be run or explicitly retired.

- **OpenClaw and Hermes.** The comparative read covers exactly two products, and the problem statement's *nearest neighbor* designation is an assertion about a field only two members of which have been inspected. Mining is the stated strategy, and an unassessed comparator is unmined ore. Both are assessed on the axes the existing comparators were, under the **two-tests rule**: *(a) is its architecture right for us* and *(b) does it have features, interfaces or lessons worth taking* are **independent questions, and (b) is frequently yes when (a) is no.** Paperclip is the precedent — architecture rejected, seven capabilities taken.
- **Multi-edge identity, trust and credential distribution.** This is now **differentiator #1** and the strongest claim the problem statement makes. `bernstein_capability_mining.md` established first-party that it is **not mineable** from the nearest neighbour — that fleet is *"multi-project, not multi-tenant in the security sense… assumed to be run by the same operator, on a network the operator trusts,"* with cross-org federation explicitly out of scope. So the claim currently rests on a competitor's **absence** rather than on positive evidence about how the thing is actually done. A differentiator evidenced only by what the neighbour does not do is the shape that breaks first.
- **Decide-only disposition.** Displaced three consecutive cycles. The prior assessment's own warning — *"a topic displaced twice is at risk of being displaced permanently; the next cycle should either run it or retire it explicitly"* — is the oldest unactioned item on the list, and this cycle has the slot. It is run rather than retired because the subject is alive: it is the seam `workflow-scripts.md § Composition` is built on, and `case_against.md` surfaced a live sourced contradiction that the pool has never adjudicated.

### Deliberately NOT re-opened

- **The novelty question.** Closed by cycle 2, accepted by the problem statement.
- **Temporal Cloud pricing, billable Actions, serverless worker patterns.** Ruled out by `system-overview.md` § *Deployment target*. Cycle 3 spent effort here against a decision made 2026-07-12; that is not repeated.
- **The two stubs in `problem-statement.md`** — the SkyyNet/SkyyCommand frame and the building-and-industrial-automation edge. Both are marked deliberately incomplete and await their own exercise. This cycle fills gaps *around* them and does not fact-check them as claims.
- **Inter-process handoff contracts — the wire format.** Redirected to `docs/development/phases/memory-management-framework/research/` by an earlier cycle; that redirect stands.

## Retirements

**None.** No subject died this cycle, and no paper in the pool is excluded from the synthesis.

## Gaps named, not covered this cycle

| Gap | Feeds | Why not here |
|---|---|---|
| **The quota-headroom view — per-edge rate-limit capacity as the scarce resource** | `roadmap.md` (no home); `problem-statement.md` § *Affordability is the enabler* | Surfaced by cycle 3 via `operator_interface.md` §4.2. Genuinely novel and falls out of the affordability thesis: every surveyed competitor's cost surface is shaped by *metered* billing, and under a flat subscription dollars are not scarce — **per-edge rate-limit headroom is**. **Not deferred on priority — not sequenceable yet**, because it is blocked on one unanswered question (does the Claude Code result envelope expose remaining quota at all? a minutes-long test) and one unread document. A recommendation with an unresolved input should not be given a rank it cannot support. Unchanged in status. |
| **What a billable Temporal Cloud Action costs for THIS workload** | — | **RETIRED AS A GAP this cycle.** It was recorded by cycle 3 as a pending measurement. `system-overview.md` § *Deployment target* rules Cloud off the table entirely, so the measurement has no consumer. Recorded here so a later cycle does not resurrect it from the cycle-3 synthesis, which predates that section being written down. |
| **Provider-shaped edges — Codex, Claude Code and others exposing different capabilities** | `problem-statement.md` § *Jarvis* (stub) | Deferred because its destination is a stub. The problem statement states the intent — *"the backbone should not care which; the edge should"* — and marks the section deliberately incomplete. Researching against a sketch produces a paper the sketch's own exercise will invalidate. **Note:** if the OpenClaw paper finds a provider-abstraction layer, that is partial coverage arriving sideways and should be read as such rather than as closing this gap. |
| **Whether an agentic `claude -p` run decomposes into resumable per-turn legs** | `Phase: Temporal Integration` — the single-activity vs child-workflow fork | Per-cycle cap. Surfaced by `python_sdk_long_activities.md` §8 and still uncovered across three cycles. Decides the port's shape, not whether the trajectory holds — second tier. **This is now the highest-priority uncovered topic for cycle 5.** |
| **Duplicated prompt *prose* — does the clone-fault evidence transfer?** | `Phase: Workflow Decomposition` | Per-cycle cap, unchanged in priority. No located literature; needs a scoping pass before it earns a dispatch. |
| **Temporal patching/versioning cost**, and the **OpenAI Agents GA-vs-Preview contradiction** across three first-party surfaces | `Phase: Temporal Integration` | Left open by the 2026-08-05 refresh, both stated with their search methods in `temporal.md` §9. Refresh-owned, not a new topic. |
| **Inter-process handoff contracts — the wire format** | `Phase: Memory Management Framework` (kind 2) | **Redirected, not deferred** — phase-level. Still the highest-value open research on that queue and still blocked on the phase doc being unwritten. |
| **Reflection-channel mining** | `Phase: Continuous Process Improvement` — the one open milestone | Phase-level. The milestone is committed; the question is how to build the sweeper. |
| **Bash → Python Stage A conversion** | `Phase: Temporal Integration` | Phase-level, and the direction is decided. Research does not settle execution. |
| **Certification and conformity regimes for a physical edge** | `problem-statement.md` § *Building & industrial automation* | **Not answerable with the access available** — every authoritative source was paywalled, 403'd or truncated (iso.org, ISO OBP, TÜV SÜD, EUR-Lex CELEX 32023R1230 cut off before the Annexes). Plausibly the largest unpriced cost item in the architecture. Needs paid standards access, not another dispatch. Feeds a section marked stub, which lowers its urgency without lowering its size. |

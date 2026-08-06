# Topics — product-level research

**Last assessed:** 2026-08-06 (cycle 4 — the first run of the decomposed `research` pipeline)

## Sizing

**Tier: Large / architecture-layer.** The destination is the stack itself, not a phase of it: `docs/development/roadmap.md` (the authoritative destination list), `docs/standards/architecture/problem-statement.md` (what the system is for), and `system-overview.md` (what exists and what is settled). A finding here can invalidate the premise of a phase rather than its sequencing, which is [Research Standard §1](../../research/research_standard.md)'s holistic altitude at its purest.

**The frame is settled and this cycle does not re-open it.** `problem-statement.md` was rewritten 2026-08-04 and corrected 2026-08-05, driven by this pool's own findings. Three consequences bind every topic below:

- **Novelty is a closed question.** The four-element combination is the known recipe, the field is converging on all four, and the stated intent is *"to execute it better than anyone else, and to acquire the lessons rather than re-learn them."* **Mining is the strategy**, so a finding that a competitor does something better is a WIN, not a threat.
- **The altitude.** This repo is **Jarvis, the assistant edge**, under SkyyCommand, under SkyyNet. Trajectory is judged against the federated destination, not against a coding tool.
- **Comparators are shipping products, not papers.** `bernstein` and Paperclip were assessed as products in cycle 3; the two added this cycle are assessed the same way.

**Deployment is settled and out of scope.** `system-overview.md` § *Deployment target* records it: **Temporal is SELF-HOSTED, Temporal Cloud is not on the table** — two servers never combined, HA on k3s, systemd workers, decided 2026-07-12 and owned by SkyyCommand. Cycle 3 did not know this and spent effort pricing Cloud. Cloud pricing, billable Actions and serverless-worker patterns are excluded from this cycle by construction, not by priority.

**Topic count: 25 — fifteen above the rubric's 8–10 Large band, and the overshoot is now a scoping finding rather than an observation.** §2 says an assessment materially above the band is *"a scoping signal, not a band failure"*, that such a component *"usually has more than one destination — a plan, plus a thesis, plus a competitive read are three consumers, not one"*, and that the correct response is **to check whether it is one component and split it per §6** — widening the band only after a genuinely single-destination component overruns more than once.

**That check has now been deferred by three consecutive cycles and the answer is visible in the table below: this is not one component.** The 25 topics sort cleanly into exactly the three consumers §2 names —

| Sub-pool | Destination | Topics |
|---|---|---|
| **Thesis** — is the position true | `problem-statement.md` | 9 |
| **Competitive read** — what the field ships and what to mine | `problem-statement.md` § *The nearest neighbor* + `roadmap.md` § *Tools to Evaluate* | 5 |
| **Plan** — what to build and in what order | `roadmap.md` and its phases | 11 |

Each part sizes at or near its band. Prior cycles recorded the overshoot as *a finding about the rubric*; that reading is withdrawn — the rubric prescribes a response this pool has not applied. **Surfaced in `synthesis.md` as a candidate.** The split is a scoping ruling with a file-moving consequence, so a research run names it and does not execute it.

**This cycle covers 4 of the 25.** §2 caps a cycle at ~5 and sequences most-decision-blocking first. The 21 existing papers hold and are not rewritten — the currency table computed at dispatch marks **all 21 current, none past window**, and revalidation is `research-refresh.sh`'s job.

**Consumer:** the synthesis feeds a master-planning pass that will revise `roadmap.md`. Each finding must carry what the capability is, why it matters for the federated destination, what evidence supports it, and roughly what it costs. A finding a planner cannot sequence cannot be planned.

## Topics

| Topic | Feeds | Paper | Last validated | Revalidate |
|---|---|---|---|---|
| **OpenClaw — architecture, and what is worth taking regardless** | `roadmap.md` § *Tools to Evaluate* (no item exists yet — the gap is part of the finding); `problem-statement.md` § *Where we actually differ* #4 and § *The edges* | `raw/openclaw_assessment.md` | 2026-08-06 | high — 4 weeks |
| **Hermes — architecture, and what is worth taking regardless** | `roadmap.md` § *Tools to Evaluate*; `problem-statement.md` § *The edges* — the provider-shaped-edge sketch | `raw/hermes_assessment.md` | 2026-08-06 | high — 4 weeks |
| **Multi-edge identity, trust and credential distribution** | `problem-statement.md` § *Where we actually differ* **#1 — the strongest claim we make and the least-evidenced**; `Phase: Temporal Integration` — worker placement, queue naming, what a worker may hold | `raw/multi_edge_identity_trust.md` | 2026-08-06 | high — 6 weeks |
| **Decide-only disposition — does a judging stage with no authoring authority reduce defects?** | `problem-statement.md` element 2 (*"one that authors, one that judges with no stake in the work"*); validates `docs/standards/workflow-scripts.md § Composition` and the `review-pr` decide-only design | `raw/decide_only_disposition.md` | 2026-08-06 | medium — 3 months |
| Mining the nearest neighbor — `bernstein` | `roadmap.md` — new items across phases; `problem-statement.md` § *The nearest neighbor* | `raw/bernstein_capability_mining.md` | 2026-08-04 | high — 2 weeks |
| Paperclip — durability machinery, operator surface, Claude Code integration | `roadmap.md` § *Tools to Evaluate*; `Phase: Temporal Integration` | `raw/paperclip_assessment.md` | 2026-08-04 | high — 4 weeks |
| The operator interface — is a control surface a requirement, and what must it show | `roadmap.md` — no phase holds this today; the named gap | `raw/operator_interface.md` | 2026-08-04 | high — 4 weeks |
| Dedicated non-fungible edges vs. central-queue claim-and-contend | `problem-statement.md` § *Where we actually differ* #2; `Phase: Temporal Integration` | `raw/dedicated_edge_routing.md` | 2026-08-04 | high — 6 weeks |
| What the field learned the hard way running long-lived agent fleets | `roadmap.md` sequencing; `Phase: Autonomous Operation` — exit criteria and failure behaviour | `raw/fleet_failure_modes.md` | 2026-08-04 | high — 4 weeks |
| Temporal as a vendor commitment | `Phase: Temporal Integration` — upgrade cadence, one-way doors, workflow-side primitive surface | `raw/temporal.md` | 2026-08-05 | high — 6 weeks |
| Durable execution | `problem-statement.md` element 1; `Phase: Temporal Integration` | `raw/durable_execution.md` | 2026-07-27 | low — 6 months |
| Claude Code integration surface | `Phase: Temporal Integration` → the `claude_cli` activity domain | `raw/claude_code_integration_surface.md` | 2026-07-25 | high — 4 weeks |
| Anthropic ToS and enterprise auth | `problem-statement.md` § *The edges* — whether subscription auth at the edge is permitted | `raw/anthropic_tos_and_enterprise.md` | 2026-07-24 | high — 4 weeks |
| Hook sourcing | `Phase: Managed Configuration` — setting-source loading and the ⚠️ safety blocker | `raw/hook_sourcing_supplement.md` | 2026-07-25 | high — 4 weeks |
| Hierarchical agents | `problem-statement.md` element 2; `Phase: Workflow Decomposition` | `raw/hierarchical_agents.md` | 2026-07-25 | medium — 3 months |
| Reflection literature | `problem-statement.md` element 2; `Phase: Continuous Process Improvement` | `raw/reflection_literature.md` | 2026-07-23 | medium — 3 months |
| Production cases | `roadmap.md` overall — what other teams hit | `raw/production_cases.md` | 2026-07-23 | medium — 3 months |
| Convergence and the plateau | `Phase: Autonomous Operation` — observable exit criteria; the loop-back bound in `revision.sh` | `raw/convergence_stopping.md` | 2026-08-03 | high — 6 weeks |
| Parameterize vs fork | `Phase: Workflow Decomposition`'s gating ruling | `raw/workflow_reuse_boundary.md` | 2026-08-03 | high — 6 weeks |
| Long activities, Python SDK | `Phase: Temporal Integration` → the `claude_cli` activity domain | `raw/python_sdk_long_activities.md` | 2026-08-03 | high — 4 weeks |
| Prior art on the combination | Re-pointed (below) — `problem-statement.md` § *The nearest neighbor* and the mining strategy | `raw/combination_prior_art.md` | 2026-08-03 | high — 4 weeks |
| Code-routed control flow | `problem-statement.md` elements 3 and 4; `system-overview.md` § *What is not built* | `raw/code_routed_control_flow.md` | 2026-08-03 | high — 6 weeks |
| Subscription economics as enabler | `problem-statement.md` § *Affordability is the enabler* | `raw/subscription_economics.md` | 2026-08-03 | high — 2 weeks |
| The case against | Re-pointed (below) — `problem-statement.md` overall, as the standing adversarial brief | `raw/case_against.md` | 2026-08-03 | high — 4 weeks |
| Backbone / edge generality | `problem-statement.md` § *Where we actually differ* #1 and #4, § *The edges* | `raw/backbone_edge_generality.md` | 2026-08-03 | high — 6 weeks |

### Two papers whose destination moved, and why their headers are still not edited

`combination_prior_art.md` and `case_against.md` carry `Feeds:` lines naming sections of `problem-statement.md` that no longer exist — the novelty section and the gap claim. **Both papers are the reason those sections were rewritten**, and the problem statement now names them explicitly as the two that forced it.

The destinations are re-pointed **here, in this table; the paper headers are left alone.** A header records the question a paper was commissioned to answer and the state it was verified in. Rewriting it to match a document the paper itself changed would erase the trace of *why* the document changed. Restated rather than cited, because §2 requires this file to state the current judgement whole.

Contrast `temporal.md`, whose `Topic:` and `Feeds:` headers **were** edited on 2026-08-05: there the question itself was replaced, so the header records the new commission. Destination-moved ≠ question-replaced; the two cases are deliberately handled differently.

### Why these four

Cycle 3 asked *is the trajectory right, and what are we missing?* and answered that it is. This cycle asks the two questions that answer left standing, plus the one the standard says must not be deferred again.

- **OpenClaw and Hermes.** Two products in this exact category, **never assessed** — the pool's competitive read covers `bernstein` and Paperclip only, and both new names surface in the pool already as *adapters other people's platforms integrate* (`hermes_local`, `hermes_gateway`, `openclaw_gateway` in Paperclip's adapter registry; OpenClaw in the February 2026 OAuth-enforcement coverage in `anthropic_tos_and_enterprise.md`). Being adapted by a competitor is evidence of a shipped interface worth reading. Assessed on the axes the existing comparators were — durability approach, domain generality, dispatch/worker model, credential locality, deployment shape — and under the **two-tests rule**: *(a) is its architecture right for us* and *(b) does it have features, interfaces or lessons worth taking* are independent questions, and (b) is frequently yes when (a) is no. Paperclip is the precedent: architecture rejected, seven capabilities taken.
- **Multi-edge identity, trust and credential distribution.** **This is now differentiator #1 — the strongest claim in `problem-statement.md` — and it is the least-evidenced.** `bernstein_capability_mining.md` established first-party that it is **not mineable** from the nearest neighbour: that fleet is *"multi-project, not multi-tenant in the security sense… assumed to be run by the same operator, on a network the operator trusts,"* with cross-org federation explicitly out of scope. So the claim currently rests on **a competitor's absence** rather than on positive evidence about how the thing is actually done. A differentiator supported only by nobody-else-does-it is a hope with a citation.
- **Decide-only disposition.** Displaced three consecutive cycles. `topics.md` has carried the warning *"a topic displaced twice is at risk of being displaced permanently; the next cycle should either run it or retire it explicitly"* since 2026-08-04, and the 2026-08-05 refresh escalated it to *"it is now three."* It is the sharpest testable claim inside `problem-statement.md` element 2, it validates a design already shipped in `review-pr`, and `case_against.md` surfaced a live sourced contradiction (Cognition's position vs. `convergence_stopping.md`). **Run, not retired.** Running it is a slot the standard's own escalation had already earned; retiring it would delete the only check on element 2.

### Deliberately NOT re-opened

- **The novelty question.** Closed by cycle 2, accepted by the problem statement, and re-litigating it spends a topic to re-derive a conclusion already acted on.
- **Temporal Cloud economics of every kind** — pricing, billable Actions, serverless worker patterns. Ruled out by a settled deployment decision, now recorded in `system-overview.md`. The prior cycle's candidates 1, 2 and 5 are the artefacts of not knowing that; the synthesis re-states them under the settled frame rather than repeating them.
- **The two stubs in `problem-statement.md`** — the SkyyNet/SkyyCommand frame and the building-and-industrial-automation edge. Both marked deliberately incomplete and awaiting their own exercise.
- **Inter-process handoff contracts — the wire format.** Redirected to `docs/development/phases/memory-management-framework/research/`; that redirect stands.

## Retirements

**None.** No subject died this cycle. No paper in the pool is excluded from the synthesis, and no paper carries `Revalidate: retired`.

## Gaps named, not covered this cycle

| Gap | Feeds | Why not here |
|---|---|---|
| **The pool is three components, not one — split it** | `topics.md` itself; §6 | **Named as a finding, not deferred on priority.** §2 prescribes the split and the check has been deferred three cycles running; the table above shows it resolves cleanly into thesis / competitive-read / plan. A research run must not execute it — it is a scoping ruling that moves files and re-points every `Feeds:` line. **Surfaced in `synthesis.md` for the reviewer.** |
| **What a billable Temporal Cloud Action costs for THIS workload** | — | **Withdrawn, not deferred.** Cycle 3 raised it without knowing Cloud was ruled out on 2026-07-12. `system-overview.md` § *Deployment target* now records the decision. There is no measurement to run and no decision it feeds. Recorded so a later cycle does not resurrect it a third time. |
| **The quota-headroom view — per-edge rate-limit capacity as the scarce resource** | `roadmap.md` (no home); `problem-statement.md` § *Affordability is the enabler* | Unchanged from cycle 3: genuinely novel, falls out of the affordability thesis, and **not sequenceable yet** — blocked on one unanswered question (does the Claude Code result envelope expose remaining quota at all? a minutes-long test) and one unread document. A recommendation with an unresolved input should not be given a rank it cannot support. **This is now the oldest un-actioned item on this list and inherits the displacement warning the decide-only topic just discharged.** |
| **Provider-shaped edges — Codex, Claude Code and others exposing different capabilities** | `problem-statement.md` § *Jarvis* (stub) | Destination is a stub. Researching against a sketch produces a paper the sketch's own exercise invalidates. **Partially served this cycle as a side-effect** — the Hermes and OpenClaw papers touch what a non-Claude edge exposes, without pretending to answer the topic. |
| **Whether an agentic `claude -p` run decomposes into resumable per-turn legs** | `Phase: Temporal Integration` — the single-activity vs child-workflow fork | Per-cycle cap. Surfaced by `python_sdk_long_activities.md` §8, still uncovered. Decides the port's shape, not whether the trajectory holds — second tier. |
| **Duplicated prompt *prose* — does the clone-fault evidence transfer?** | `Phase: Workflow Decomposition` | Per-cycle cap. No located literature; needs a scoping pass before it earns a dispatch. |
| **Inter-process handoff contracts — the wire format** | `Phase: Memory Management Framework` (kind 2) | **Redirected, not deferred** — phase-level. Still the highest-value open research on the queue, still blocked on the phase doc being unwritten. |
| **Reflection-channel mining** | `Phase: Continuous Process Improvement` — the one open milestone | Phase-level. The milestone is committed; the question is how to build the sweeper. |
| **Bash → Python Stage A conversion** | `Phase: Temporal Integration` | Phase-level, and the direction is decided. Research does not settle execution. |
| **Certification and conformity regimes for a physical edge** | `problem-statement.md` § *Building & industrial automation* (stub) | **Not answerable with the access available** — iso.org, ISO OBP, TÜV SÜD and EUR-Lex CELEX 32023R1230 were all paywalled, 403'd or truncated before the Annexes. Plausibly the largest unpriced cost item in the architecture. Needs paid standards access, not another dispatch. |

# Topics — product-level research

**Last assessed:** 2026-08-04 · **Refresh touch:** 2026-08-05 (`research-refresh.sh` — one paper revalidated, one topic re-scoped; the sizing assessment below is NOT re-run by a refresh)

## Sizing

**Tier: Large / architecture-layer.** The destination is the stack itself, not a phase of it: `docs/development/roadmap.md` (the authoritative destination list), `docs/standards/architecture/problem-statement.md` (what the system is for), and `system-overview.md` (what exists). A finding here can invalidate the premise of a phase rather than its sequencing, which is [Research Standard §1](../../research/research_standard.md)'s holistic altitude at its purest.

**The destination changed shape on 2026-08-04, and it changes what a finding IS.** `problem-statement.md` was rewritten, driven by this pool's own prior findings. Three changes bind this assessment:

- **The novelty question is closed.** The document no longer claims the four-way combination is novel; it states the four elements as *the known recipe* and states the intent as *"to execute it better than anyone else, and to acquire the lessons rather than re-learn them."* **Mining is now the stated strategy.** A finding that a competitor does something better is therefore a win, not a threat — which inverts what makes a topic worth running.
- **The altitude corrected.** This repo is not a product; it is **Jarvis, the assistant edge**, under SkyyCommand under SkyyNet. Every topic is assessed against the federated destination, not against a coding tool.
- **`bernstein` is a shipping product, not a paper.** The prior cycle assessed it from documentation alone and scored it as a peer. It is now named in the problem statement as the nearest neighbor and as reference material, ahead of this repo on every axis except three.

**Topic count: 21 — eleven above the rubric's 8–10 band.** §2 requires the list to grow when the component grows and states the thresholds are a starting calibration. The overshoot is a finding about the rubric, not a licence: **the bands are sized for components whose destination is a plan; this component's destination is a thesis plus a roadmap plus a live competitive field**, which carries more falsifiable claims per unit of build than a plan does. Surfaced in `synthesis.md`; the Research Standard is vendored MIRROR and cannot be amended here.

**This cycle covers 5 of the 21.** §2 caps a cycle at ~5 and sequences most-decision-blocking first. The sixteen existing papers hold and are not rewritten — the currency table computed at dispatch marks fifteen of them current, and revalidation is `research-refresh.sh`'s job, not this cycle's.

**Consumer:** the synthesis feeds a master-planning pass that will revise `roadmap.md`. That determines the shape of a useful finding — each one must carry what the capability is, why it matters for the federated destination, what evidence supports it, and roughly what it costs to build. A finding a planner cannot sequence cannot be planned.

## Topics

| Topic | Feeds | Paper | Last validated | Revalidate |
|---|---|---|---|---|
| **Mining the nearest neighbor — what `bernstein` ships that we do not** | `roadmap.md` — new items across phases; `problem-statement.md` § *The nearest neighbor* | `raw/bernstein_capability_mining.md` | 2026-08-04 | high — 2 weeks |
| **Paperclip — durability machinery, operator surface, Claude Code integration** | `roadmap.md` § *Tools to Evaluate* → the open "evaluate after Phase 4" item; `Phase: Temporal Integration` | `raw/paperclip_assessment.md` | 2026-08-04 | high — 4 weeks |
| **The operator interface — is a control surface a requirement, and what must it show** | `roadmap.md` — **no phase holds this today**; the named gap | `raw/operator_interface.md` | 2026-08-04 | high — 4 weeks |
| **Dedicated non-fungible edges vs. central-queue claim-and-contend** | `problem-statement.md` § *Where we actually differ* #2; `Phase: Temporal Integration` — worker placement and queue naming | `raw/dedicated_edge_routing.md` | 2026-08-04 | high — 6 weeks |
| **What the field learned the hard way running long-lived agent fleets** | `roadmap.md` sequencing overall; `Phase: Autonomous Operation` — exit criteria and failure behaviour | `raw/fleet_failure_modes.md` | 2026-08-04 | high — 4 weeks |
| Durable execution | `problem-statement.md` element 1; `Phase: Temporal Integration` — whether durability is the binding constraint | `raw/durable_execution.md` | 2026-07-27 | low — 6 months |
| **Temporal as a vendor commitment** — **RE-SCOPED 2026-08-05** (below) | `Phase: Temporal Integration` — the self-hosted-vs-Cloud decision, the upgrade cadence the fleet must keep, and the workflow-side primitive surface. Explicitly NOT activity mechanics (`python_sdk_long_activities.md`) nor worker placement (`dedicated_edge_routing.md`) | `raw/temporal.md` | **2026-08-05** | high — 6 weeks |
| Claude Code integration surface | `Phase: Temporal Integration` → the `claude_cli` activity domain | `raw/claude_code_integration_surface.md` | 2026-07-25 | high — 4 weeks |
| Anthropic ToS and enterprise auth | `problem-statement.md` § *The edges* — whether subscription auth at the edge is **permitted** | `raw/anthropic_tos_and_enterprise.md` | 2026-07-24 | high — 4 weeks |
| Hook sourcing | `Phase: Managed Configuration` — setting-source loading and the ⚠️ safety blocker | `raw/hook_sourcing_supplement.md` | 2026-07-25 | high — 4 weeks |
| Hierarchical agents | `problem-statement.md` element 2; `Phase: Workflow Decomposition` — parent/child composition | `raw/hierarchical_agents.md` | 2026-07-25 | medium — 3 months |
| Reflection literature | `problem-statement.md` element 2; `Phase: Continuous Process Improvement` | `raw/reflection_literature.md` | 2026-07-23 | medium — 3 months |
| Production cases | `roadmap.md` overall — what other teams hit | `raw/production_cases.md` | 2026-07-23 | medium — 3 months |
| Convergence and the plateau | `Phase: Autonomous Operation` — observable exit criteria; the loop-back bound in `revision.sh` | `raw/convergence_stopping.md` | 2026-08-03 | high — 6 weeks |
| Parameterize vs fork | `Phase: Workflow Decomposition`'s gating ruling | `raw/workflow_reuse_boundary.md` | 2026-08-03 | high — 6 weeks |
| Long activities, Python SDK | `Phase: Temporal Integration` → the `claude_cli` activity domain | `raw/python_sdk_long_activities.md` | 2026-08-03 | high — 4 weeks |
| Prior art on the combination | **Re-pointed** (below) — now `problem-statement.md` § *The nearest neighbor* and the mining strategy | `raw/combination_prior_art.md` | 2026-08-03 | high — 4 weeks |
| Code-routed control flow | `problem-statement.md` element 3 and 4; `system-overview.md` § *What is not built* | `raw/code_routed_control_flow.md` | 2026-08-03 | high — 6 weeks |
| Subscription economics as enabler | `problem-statement.md` § *Affordability is the enabler* | `raw/subscription_economics.md` | 2026-08-03 | high — 2 weeks |
| The case against | **Re-pointed** (below) — now `problem-statement.md` overall, as the standing adversarial brief | `raw/case_against.md` | 2026-08-03 | high — 4 weeks |
| Backbone / edge generality | `problem-statement.md` § *Where we actually differ* #1 and § *The edges* | `raw/backbone_edge_generality.md` | 2026-08-03 | high — 6 weeks |

### Two papers whose destination moved, and why their headers were not edited

`combination_prior_art.md` and `case_against.md` both carry `Feeds:` lines naming sections of `problem-statement.md` that **no longer exist** — the novelty section and the gap claim. Both papers are the reason those sections were rewritten; the problem statement now names them explicitly as the two that forced it.

The destinations are re-pointed **here, in this table, and the paper headers are left alone.** A paper's header records the question it was commissioned to answer and the state it was verified in; rewriting it to match a document the paper itself changed would erase the trace of *why* the document changed. The re-pointing belongs in the topic list, which is the artifact that tracks destinations. Recorded explicitly because a reader checking header-against-destination will otherwise read this as drift.

### Why these five

The previous cycle asked *is the combination novel and sound?* and answered no, correctly. That question is closed. This cycle asks the question the rewrite makes possible: **is the trajectory right, and what are we missing for the end goal?** The five follow from taking that question seriously against a roadmap whose destination is a federated fabric.

- **Mining the nearest neighbor.** The problem statement names `bernstein` as reference material and the prior cycle left **40 of its 52 doc directories unread** — that was already the standing highest-priority test item. A shipping product with a Kubernetes operator, mTLS, tunneled remote workers, checkpoint/resume and typed refusal, at 3,397 commits in 4.5 months, is the cheapest available source of production lessons in the entire field. Mining is the stated strategy and this is the richest seam.
- **Paperclip.** `roadmap.md` § *Tools to Evaluate* carries an open item to evaluate it, and it has been assessed twice in this session on thin evidence and got it wrong both times — it *does* carry durability machinery and it *does* integrate with Claude Code. Its org-chart metaphor is wrong for us; that is a verdict on architecture and says nothing about features. At 75,600 stars it is the largest player in the category and the roadmap item is live.
- **The operator interface.** This repo has **no operator surface at all** beyond a CLI and a text standup, and no phase in the roadmap holds one. For a fabric running many edges across MDCs, whether that is a genuine requirement — and what it must show — is a question about the destination that a human cannot settle by taste. It is the clearest named gap and it is currently homeless.
- **Dedicated non-fungible edges.** This is differentiator #2, marked *designed, not yet built*, and the industry model is the opposite. What a human cannot judge without evidence is **what building it actually requires** on the chosen substrate, and what the claim-and-contend model buys that a dedicated model gives up. If the cost is larger than assumed, that changes `Phase: Temporal Integration`'s scope, not just its ordering.
- **What the field learned the hard way.** Named in the dispatch as the highest-value output available, and the pool has nothing like it: `production_cases.md` surveys *who adopted durable execution*, not *what killed the runs*. Failure modes, dead ends and designs that did not survive production are free lessons, and the roadmap currently sequences on assumed rather than observed failure behaviour.

### Deliberately NOT re-opened

- **The novelty question.** Closed by the previous cycle, accepted by the problem statement, and re-litigating it would spend a topic to re-derive a conclusion already acted on.
- **The two stubs in `problem-statement.md`** — the SkyyNet/SkyyCommand frame and the building-and-industrial-automation edge. Both are marked deliberately incomplete and await their own exercise. This cycle fills gaps *around* them and does not fact-check them as claims.
- **Inter-process handoff contracts — the wire format.** Redirected to `docs/development/phases/memory-management-framework/research/` by an earlier cycle; that redirect stands.

## Retirements

**None.** No subject died. The 2026-08-04 reframe added destinations and re-pointed two papers (above); neither is a retirement, and no paper in the pool is excluded from the synthesis.

### `raw/temporal.md` — RE-SCOPED, not retired (2026-08-05 refresh)

The 2026-08-04 cycle left this paper past-window and deferred it to `research-refresh.sh`. That refresh has now run, and it found the paper's **question** dead even though its **subject** is not.

The old topic — *"Does Temporal supply what a durable workflow layer needs, and at what cost in complexity?"* — failed on both halves. The **supply** half is a decided question: the roadmap has chosen Temporal and the port is underway, so continuing to ask it audits a taken direction, which [Research Standard §0](../../research/research_standard.md) distinguishes from research's job. The **evidence** half was taken by siblings between 2026-07-27 and 2026-08-04 — heartbeat and payload limits to `python_sdk_long_activities.md` (which names `temporal.md` in its own citations as the paper whose gap it closes), routing and placement to `dedicated_edge_routing.md`, concepts to `durable_execution.md`. By 2026-08-04 the paper had been hollowed out by its own pool.

**§6 retires a topic whose subject died.** Temporal did not die — it is the substrate of a live phase. What the refresh found underneath was a real, unowned question: **nobody in the pool owned the cost and commitment of the vendor.** No paper stated the licence (MIT). No paper priced Cloud. No paper carried the upgrade obligation or the shard-capacity one-way door. Retiring the topic would have deleted the only home for that.

The paper's `Topic:` and `Feeds:` headers were **edited** here — unlike `combination_prior_art.md` and `case_against.md` above, whose destinations moved while their questions stood. This is the opposite case: the question itself was replaced, so the header records the new commission rather than preserving a trace of an old one. The distinction is deliberate and the two cases should not be read as inconsistent.

**One consequence for this list.** The paper was a **pre-standard artifact** — 39 lines, no citations, no honest-boundary section, no content arc — and sat in the pool for a month as the substrate paper for a live phase in that state. It was caught because it aged out, not because anything checked it against §3. Surfaced as a homeless finding in `synthesis.md`.

## Gaps named, not covered this cycle

| Gap | Feeds | Why not here |
|---|---|---|
| **Decide-only disposition — does a judging stage with no authoring authority actually reduce defects?** | `problem-statement.md` element 2; validates `workflow-scripts.md § Composition` | Per-cycle cap — and **displaced for the second consecutive cycle**, which is itself worth recording. It was named first-in-line last cycle; the problem-statement rewrite then made capability acquisition for the federated destination the binding question, and validating a shipped decision lost to it again. It remains the sharpest testable claim inside element 2 and `case_against.md` surfaced a live sourced contradiction (Cognition vs. `convergence_stopping.md`) that only an experiment resolves. **A topic displaced twice is at risk of being displaced permanently; the next cycle should either run it or retire it explicitly.** *(2026-08-05 refresh: still not run. A refresh cycle has no topic slot to give it, so this is not a third displacement on the merits — but it is a third cycle in which it did not happen, and the warning above is now the oldest unactioned item on this list.)* |
| **What a billable Temporal Cloud Action actually costs for THIS workload** | `Phase: Temporal Integration` — the self-host-vs-Cloud decision | **New, from the 2026-08-05 refresh.** The *definition* gap is closed — `/cloud/actions` enumerates eleven billable categories and `glossary.md` defines the unit — so this is no longer research-blocked. What remains is a **measurement, not a topic**: run one representative agent workflow against the $1,000 trial credit and read the billed Action count, instrumenting the heartbeat contribution separately (heartbeat recording is billable). Recorded here so it is not mistaken for an open research question. |
| **Multi-edge identity, trust and credential distribution** | `problem-statement.md` § *The edges*; `Phase: Temporal Integration` | **New this cycle, and now evidenced as NOT mineable.** The mining paper established first-party that bernstein's fleet mode is *"multi-project, not multi-tenant in the security sense… assumed to be run by the same operator, on a network the operator trusts"*, and that its federation v1 limitations explicitly list *"Cross-tenant federation across organisations."* Its mTLS is intra-trust-domain plumbing, not an answer to *how an edge proves it is the edge it claims to be* across MDCs and operators. **The nearest neighbour does not solve the problem we have**, which upgrades this from "deferred on scope" to "needs its own pass with no reference implementation to mine." |
| **The quota-headroom view — per-edge rate-limit capacity as the scarce resource** | `roadmap.md` (no home); `problem-statement.md` § *Affordability is the enabler* | **Surfaced by this cycle** via `raw/operator_interface.md` §4.2. Genuinely novel and falls out of the affordability thesis: every surveyed competitor's cost surface is shaped by *metered* billing, and under a flat subscription dollars are not scarce — **per-edge rate-limit headroom is**, and each edge has its own subscription. Nobody surveyed exposes that view. **Not deferred on priority — not sequenceable yet**, because it is blocked on one unanswered question (does the Claude Code result envelope expose remaining quota at all? a minutes-long test) and one unread document. A recommendation with an unresolved input should not be given a rank it cannot support. |
| **Provider-shaped edges — Codex, Claude Code and others exposing different capabilities** | `problem-statement.md` § *Jarvis* (stub) | Deferred because its destination is a stub. The problem statement states the intent — *"the backbone should not care which; the edge should"* — and marks the section deliberately incomplete. Researching against a sketch produces a paper the sketch's own exercise will invalidate. |
| **Whether an agentic `claude -p` run decomposes into resumable per-turn legs** | `Phase: Temporal Integration` — the single-activity vs child-workflow fork | Per-cycle cap. Surfaced by `python_sdk_long_activities.md` §8 and still uncovered. Decides the port's shape, not whether the trajectory holds — second tier. |
| **Duplicated prompt *prose* — does the clone-fault evidence transfer?** | `Phase: Workflow Decomposition` | Per-cycle cap, unchanged in priority. No located literature; needs a scoping pass before it earns a dispatch. |
| **Inter-process handoff contracts — the wire format** | `Phase: Memory Management Framework` (kind 2) | **Redirected, not deferred** — phase-level. Still the highest-value open research on the queue and still blocked on the phase doc being unwritten. |
| **Reflection-channel mining** | `Phase: Continuous Process Improvement` — the one open milestone | Phase-level. The milestone is committed; the question is how to build the sweeper. |
| **Bash → Python Stage A conversion** | `Phase: Temporal Integration` | Phase-level, and the direction is decided. Research does not settle execution. |
| **Certification and conformity regimes for a physical edge** | `problem-statement.md` § *Building & industrial automation* | **Not answerable with the access available** — every authoritative source was paywalled, 403'd or truncated (iso.org, ISO OBP, TÜV SÜD, EUR-Lex CELEX 32023R1230 cut off before the Annexes). Plausibly the largest unpriced cost item in the architecture. Needs paid standards access, not another dispatch. Note this now feeds a section marked stub, which lowers its urgency without lowering its size. |

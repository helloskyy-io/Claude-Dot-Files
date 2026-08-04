# Topics — product-level research

**Last assessed:** 2026-08-03

## Sizing

**Tier: Large / architecture-layer.** The destination is no longer only `docs/development/roadmap.md`. Since the previous assessment, `docs/standards/architecture/problem-statement.md` was written, and it states a **thesis**: four elements combined, plus affordability as the enabler, plus a claim that the backbone generalises across edges. A finding at this altitude can now invalidate the *premise* of a phase rather than its sequencing, which is the stack layer in §1 at its purest.

**Correction to the previous assessment.** That assessment excluded `docs/standards/architecture/system-overview.md` as substantively stale and treated it as absent. **That judgement is now out of date — the file has been rewritten and is accurate.** It is a live destination this cycle, and the synthesis's § *A stale destination* is superseded. Recorded here because the exclusion is the kind of thing a later cycle inherits without re-checking.

**Topic count: 16 — six above the rubric's 8–10 band, and the gap is a finding about the rubric, not a licence.** Eleven topics were assessed against a roadmap. The problem statement adds a destination of a different kind: a four-part novelty claim, an economic enabler claim, and a generality claim, each of which is falsifiable and none of which any existing paper addresses. §2 requires the list to grow when the component grows and states the thresholds are a starting calibration; a list unchanged across the arrival of the document that states what the product is *for* is exactly §2's named breakage. **The honest observation is that the rubric bands are sized for components whose destination is a plan; a component whose destination is a thesis carries more falsifiable claims per unit of build.** Surfaced in `synthesis.md`, not acted on here — the Research Standard is vendored MIRROR and cannot be amended in this repo.

**This cycle covers 5 of the 16.** §2 caps a cycle at ~5 and sequences most-decision-blocking first. The eleven existing papers still hold and are not rewritten (see *Retirements*); this cycle adds only what the new frame exposed.

## Topics

| Topic | Feeds | Paper | Last validated | Revalidate |
|---|---|---|---|---|
| Durable execution | `problem-statement.md` element 1; `Phase: Temporal Integration` — whether durability is the binding constraint | `raw/durable_execution.md` | 2026-07-27 | low — 6 months |
| Temporal | `Phase: Temporal Integration` — SDK constraints, worker model, heartbeat and payload limits | `raw/temporal.md` | 2026-07-04 | high — 4 weeks **(PAST WINDOW)** |
| Claude Code integration surface | `Phase: Temporal Integration` → the `claude_cli` activity domain — what an activity can invoke, and how | `raw/claude_code_integration_surface.md` | 2026-07-25 | high — 4 weeks |
| Anthropic ToS and enterprise auth | `problem-statement.md` § *What is being built* (edge tier) — whether subscription auth at the edge is **permitted** | `raw/anthropic_tos_and_enterprise.md` | 2026-07-24 | high — 4 weeks |
| Hook sourcing | `Phase: Managed Configuration` — setting-source loading, and the hook that survives it (the ⚠️ safety blocker) | `raw/hook_sourcing_supplement.md` | 2026-07-25 | high — 4 weeks |
| Hierarchical agents | `problem-statement.md` element 2; `Phase: Workflow Decomposition` — parent/child composition | `raw/hierarchical_agents.md` | 2026-07-25 | medium — 3 months |
| Reflection literature | `problem-statement.md` element 2; `Phase: Continuous Process Improvement` — the reflection channel and the plateau question | `raw/reflection_literature.md` | 2026-07-23 | medium — 3 months |
| Production cases | The roadmap overall — what other teams hit, and where this approach diverges | `raw/production_cases.md` | 2026-07-23 | medium — 3 months |
| Convergence and the plateau | `Phase: Autonomous Operation` — "exit criteria that are real and observable"; the one-loop-back bound live in `revision.sh` | `raw/convergence_stopping.md` | 2026-08-03 | high — 6 weeks |
| Parameterize vs fork | `problem-statement.md` § *the shared workflow library*; `Phase: Workflow Decomposition`'s gating ruling | `raw/workflow_reuse_boundary.md` | 2026-08-03 | high — 6 weeks |
| Long activities, Python SDK | `Phase: Temporal Integration` → the `claude_cli` activity domain | `raw/python_sdk_long_activities.md` | 2026-08-03 | high — 4 weeks |
| **Prior art on the combination** | `problem-statement.md` § *What we are combining, and why it is novel* — the novelty claim itself | `raw/combination_prior_art.md` | *(this cycle)* | *(this cycle)* |
| **Code-routed control flow** | `problem-statement.md` elements 3 **and** 4; `system-overview.md` § *What is not built* | `raw/code_routed_control_flow.md` | *(this cycle)* | *(this cycle)* |
| **Subscription economics as enabler** | `problem-statement.md` § *Affordability is not a footnote — it is the enabler* | `raw/subscription_economics.md` | *(this cycle)* | *(this cycle)* |
| **The case against the thesis** | `problem-statement.md` overall — the adversarial brief the pool does not have | `raw/case_against.md` | *(this cycle)* | *(this cycle)* |
| **Backbone / edge generality** | `problem-statement.md` § *Where this repo sits* + § *Nothing may assume the coding edge* | `raw/backbone_edge_generality.md` | *(this cycle)* | *(this cycle)* |

### Why these five, and not the others

The previous cycle asked *what does this fleet need next?* This one asks *does the architecture close the gap it claims to, and does the evidence support the combination as novel and sound?* The selection follows from mapping the existing pool onto the thesis and taking what is uncovered.

- **Prior art on the combination.** The novelty claim is the contribution, and nothing in the pool tests it. `production_cases.md` surveys who adopted durable execution and what they hit — a different question. **A finding that someone has already built this is worth more than a finding that nobody has**, and the topic is written to reward the positive result rather than the comfortable one.
- **Code-routed control flow.** Elements 3 and 4 share one premise: **routing decisions are made by code over typed state, with no model in the loop.** Every hierarchical system in `hierarchical_agents.md` puts an *LLM planner* at the top — AgentOrchestra, HALO, AiScientist, CORPGEN all route by model. The thesis rejects exactly that variant, and the pool has zero evidence on it. This is the weakest-evidenced leg and plausibly the actual novel core.
- **Subscription economics.** Affordability is stated as *the enabler* of the other three, and it is the only load-bearing claim in the problem statement with no paper of any kind. `anthropic_tos_and_enterprise.md` answers whether edge-subscription auth is **permitted**; it does not answer whether flat-rate billing actually makes wasteful long-running experimentation accessible, nor what erodes that (usage caps are a second metering surface; falling token prices attack the premise from the other side).
- **The case against the thesis.** §3 requires each paper to carry its own honest boundary, and they do. What the pool has never had is a paper whose *whole job* is the counter-position. A pool that only supports its own direction is advocacy — the standard says so about individual papers, and it is truer of a pool assembled by the party that benefits from the answer.
- **Backbone / edge generality.** "Nothing may assume the coding edge" is a live constraint on every design decision made here today, and it rests on an untested economies-of-scope claim — that each new edge costs less to stand up than the last. If that does not hold, iteration one is paying abstraction costs for edges that will not arrive in the shape assumed. That is a direction change, not a sequencing note, which is what puts it at this altitude.

### Deliberately NOT re-opened

**Inter-process handoff contracts — the wire format.** The previous cycle redirected this to `docs/development/phases/memory-management-framework/research/` on the strength of this folder's own README worked example, and **that redirect stands.** *Typed file vs parsed log* informs a committed phase. The new topic above is a different question at a different altitude: not *what shape should the handoff take*, but *does code-routed control flow hold up as a design element at all*. The first informs the Memory Management phase; the second invalidates the premise of `Phase: Autonomous Operation` if it fails. Stated explicitly because a reader who knows the prior redirect will otherwise read the new topic as ignoring it.

## Retirements

**None this cycle.** No subject died, and the new frame retired nothing — it added destinations rather than removing them. Three papers whose `Feeds:` lines named only a roadmap phase now also serve a problem-statement element; that is a widening of destination, recorded in the table above, not a retirement.

`raw/temporal.md` is past its revalidation window and consumers treat it as unverified until `research-refresh.sh` runs (§5). The prior synthesis's candidate #8 proposed rewriting rather than diffing it at that refresh. **That is a refresh decision, not a retirement, and this cycle does not act on it.**

## Gaps named, not covered this cycle

| Gap | Feeds | Why not here |
|---|---|---|
| **Decide-only disposition — does a judging stage with no authoring authority actually reduce defects?** | `problem-statement.md` element 2 ("one that judges with no stake in the work"); validates `workflow-scripts.md § Composition` | Per-cycle cap, and it was displaced rather than dropped. The new frame **raises** its priority: it is no longer only validation of a shipped decision, it is the sharpest testable claim inside element 2 — "the layering is what makes the improvement real rather than an agent agreeing with itself." First in line next cycle. |
| **Does an agentic `claude -p` run decompose into resumable per-turn legs?** | `Phase: Temporal Integration` — the fork between single-activity and child-workflow shapes | Per-cycle cap. Surfaced by the previous cycle via `python_sdk_long_activities.md` §8 and still uncovered. Note the new frame does **not** promote it: it decides the port's shape, not whether the thesis holds. Product-level, second tier. |
| **Duplicated prompt *prose* — does the clone-fault evidence transfer?** | `Phase: Workflow Decomposition`; the ruling `raw/workflow_reuse_boundary.md` feeds | Per-cycle cap, and unchanged in priority by the new frame. A topic with no located literature needs a scoping pass before it earns a dispatch. |
| **Inter-process handoff contracts — the wire format** | `Phase: Memory Management Framework` (kind 2) | **Redirected, not deferred.** Phase-level; see *Deliberately NOT re-opened* above. Still the highest-value open research on the queue, and still blocked on the phase doc being unwritten. |
| **Reflection-channel mining** | `Phase: Continuous Process Improvement` — the open "sweep the reflection channel systematically" milestone | Phase-level. The milestone is committed; the question is how to build the sweeper. |
| **Bash → Python Stage A conversion** | `Phase: Temporal Integration` | Phase-level, and the direction is decided. Research does not settle execution. |

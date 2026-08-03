# Topics — product-level research

**Last assessed:** 2026-07-27

## Sizing

**Tier: Large / architecture-layer.** The destination docs are `docs/standards/architecture/system-overview.md` and `docs/development/roadmap.md` — a whole-system description and a multi-phase plan, not a single component. Findings at this altitude can invalidate a phase rather than inform one, which is the definition of the stack layer in §2.

**Topic count: 8.** Within the 8–10 the tier calls for. The roadmap names six live phases plus two unscheduled; eight topics covers each phase that carries an open technical question, with two topics on Temporal because the port is the largest single commitment on the plan.

## Topics

> **Prior-run artifact.** This pool was produced by the CSCI-6905.604 research project (2026-07-04 → 07-27) using this
> methodology by hand — the workflow was modelled on it. Placed here as a completed prior cycle so the next dispatch
> exercises the **re-assessment** path rather than a cold start. `synthesis.md` is that project's direction document and
> is deliberately **not** reshaped to the §4 contract; Stage 5 should rewrite it.

| Topic | Feeds | Paper | Last validated | Revalidate |
|---|---|---|
| Durable execution | `Phase: Temporal Integration` — whether durability is the binding constraint, and what an engine must supply | `raw/durable_execution.md` | 2026-07-27 | low — 6 months |
| Temporal | `Phase: Temporal Integration` — SDK constraints, worker model, heartbeat and payload limits | `raw/temporal.md` | 2026-07-04 | high — 4 weeks **(DUE)** |
| Claude Code integration surface | `Phase: Temporal Integration` → the `claude_cli` activity domain — what an activity can invoke, and how | `raw/claude_code_integration_surface.md` | 2026-07-25 | high — 4 weeks |
| Anthropic ToS and enterprise auth | `Phase: Managed Configuration` + edge-worker topology — whether subscription-tier auth at the edge is viable | `raw/anthropic_tos_and_enterprise.md` | 2026-07-24 | high — 4 weeks |
| Hook sourcing | `Phase: Managed Configuration` — setting-source loading, and the hook that survives it | `raw/hook_sourcing_supplement.md` | 2026-07-25 | high — 4 weeks |
| Hierarchical agents | `Phase: Workflow Decomposition` + `Phase: Autonomous Operation` — parent/child composition, and the tier above parents | `raw/hierarchical_agents.md` | 2026-07-25 | medium — 3 months |
| Reflection literature | `Phase: Continuous Process Improvement` — the reflection channel and the plateau question | `raw/reflection_literature.md` | 2026-07-23 | medium — 3 months |
| Production cases | The roadmap overall — what other teams hit, and where this approach diverges | `raw/production_cases.md` | 2026-07-23 | medium — 3 months |

## Gaps named, not covered this cycle

| Gap | Feeds | Why deferred |
|---|---|---|
| Inter-process handoff contracts | `Phase: Memory Management Framework` | Per-cycle cap. Highest-value remaining gap — the phase currently reasons from one informal survey |
| Convergence-based stopping conditions | `Phase: Memory Management Framework` / `Autonomous Operation` | Depends on the handoff contract landing first |

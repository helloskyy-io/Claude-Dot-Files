# Topic list — product-level research

**What this file is.** The output of `research.sh` Stage 2 (SIZE), persisted. Stage 2 assesses complexity against [Research Standard §2](../../research/research_standard.md), produces a topic list, and Stage 3 dispatches on it — but the list itself has never been written down anywhere. Only the resulting papers survive, so on the next run the *reasoning* is gone: which tier was assessed, why this many topics, whether a short list means "small tier, done" or "large tier, cycle 1 of 3."

This file is that memory. **Re-assessed on every touch, not appended** — §2 requires complexity to be re-evaluated each run, so a later run rewrites this with its own assessment rather than adding to it.

---

## Assessment — 2026-08-03

**Complexity tier: Large / architecture-layer.** This pool backs the product's direction rather than any single phase — it is the altitude where a finding can invalidate a phase rather than inform one. §2's shape for that tier is 8–10 topics.

**Topic count: 8.** Within tier. No further topics needed for the questions currently on the roadmap.

**Cycle note:** §2 caps a cycle at ~5 topics. These 8 were produced outside this workflow, by the CSCI-6905.604 research project, so they arrived without that constraint. A future run adding topics must respect the per-cycle cap and split.

## Topics

Each line: `<topic> — Feeds: <the decision or doc it validates>`. A topic with no destination does not make the list.

| Topic | Feeds | Paper |
|---|---|---|
| **Durable execution** | `Phase: Temporal Integration` — whether durability is the binding constraint, and what the engine must supply | `raw/durable_execution.md` |
| **Temporal specifics** | `Phase: Temporal Integration` — SDK constraints, worker model, the heartbeat and payload questions | `raw/temporal.md` |
| **Claude Code integration surface** | `Phase: Temporal Integration` → the `claude_cli` activity domain; what an activity can actually invoke and how | `raw/claude_code_integration_surface.md` |
| **Anthropic ToS and enterprise auth** | `Phase: Managed Configuration` + the edge-worker topology — whether subscription-tier auth at the edge is viable, which decides the whole deployment shape | `raw/anthropic_tos_and_enterprise.md` |
| **Hook sourcing** | `Phase: Managed Configuration` — the setting-source question, and the safety blocker on `--setting-sources` | `raw/hook_sourcing_supplement.md` |
| **Hierarchical agents** | `Phase: Workflow Decomposition` + `Phase: Autonomous Operation` — parent/child composition, and the loop tier above parents | `raw/hierarchical_agents.md` |
| **Reflection literature** | `Phase: Continuous Process Improvement` — the reflection channel, and the plateau question the one-loop-back bound rests on | `raw/reflection_literature.md` |
| **Production cases** | The roadmap as a whole — what other teams hit, and where our approach diverges | `raw/production_cases.md` |

## Gaps this assessment names

Topics a later cycle should consider, each with a destination — recorded here so the next SIZE run inherits them rather than re-deriving:

- **Inter-process handoff contracts** — `Phase: Memory Management Framework`. The prior art was surveyed once informally and explicitly flagged *suggestive only*. Highest-value gap on the list.
- **Convergence-based stopping conditions** — `Phase: Memory Management Framework` / `Autonomous Operation`. Depends on the above.

## Provenance

The eight papers were produced by the CSCI-6905.604 research project between 2026-07-04 and 2026-07-27, outside this workflow. They are placed here as an existing pool so the next run exercises the **re-assessment** path — grow, retire, keep valid papers — rather than a cold start. That is the path every subsequent run takes.

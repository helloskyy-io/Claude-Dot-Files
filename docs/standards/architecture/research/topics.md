# Topics — product-level research

**Last assessed:** 2026-08-03

## Sizing

**Tier: Large / architecture-layer.** The destination is `docs/development/roadmap.md` — eleven named phases, four of them queued with open technical questions and one in progress. Findings at this altitude can invalidate a phase rather than inform one, which is the definition of the stack layer in §1.

*`docs/standards/architecture/system-overview.md` is NOT a destination this cycle.* It is substantively stale — it still describes orchestration as "bash-over-Python" monoliths and contains no mention of parent/child workflows, the activities layer, the disposition engine, or the Python decision. Sizing against it would have measured a system that no longer exists. Treated as absent.

**Topic count: 11 — one above the rubric's 8–10 band, deliberately.** Three architectural layers landed since the 2026-07-27 assessment — parent/child decomposition, the extracted activities layer, and the decide-only disposition engine — plus an implementation-language decision and a roadmap restructured into named phases. None of the eight existing papers speaks to any of them. §2 requires the topic list to grow when the component grows and states the thresholds are a starting calibration; growing by three and saying so is the honest reading, and a list unchanged across a change this size is what §2's "breaking it looks like" names.

**This cycle covers 3 of the 11.** §2 caps a cycle at ~5 and sequences most-decision-blocking first. The eight existing papers still hold (see retirements below), so this cycle adds only the new topics.

## Topics

| Topic | Feeds | Paper | Last validated | Revalidate |
|---|---|---|---|---|
| Durable execution | `Phase: Temporal Integration` — whether durability is the binding constraint, and what an engine must supply | `raw/durable_execution.md` | 2026-07-27 | low — 6 months |
| Temporal | `Phase: Temporal Integration` — SDK constraints, worker model, heartbeat and payload limits | `raw/temporal.md` | 2026-07-04 | high — 4 weeks **(DUE)** |
| Claude Code integration surface | `Phase: Temporal Integration` → the `claude_cli` activity domain — what an activity can invoke, and how | `raw/claude_code_integration_surface.md` | 2026-07-25 | high — 4 weeks **(DUE)** |
| Anthropic ToS and enterprise auth | `Phase: Managed Configuration` + edge-worker topology — whether subscription-tier auth at the edge is viable | `raw/anthropic_tos_and_enterprise.md` | 2026-07-24 | high — 4 weeks **(DUE)** |
| Hook sourcing | `Phase: Managed Configuration` — setting-source loading, and the hook that survives it (the ⚠️ safety blocker) | `raw/hook_sourcing_supplement.md` | 2026-07-25 | high — 4 weeks **(DUE)** |
| Hierarchical agents | `Phase: Workflow Decomposition` + `Phase: Autonomous Operation` — parent/child composition, and the tier above parents | `raw/hierarchical_agents.md` | 2026-07-25 | medium — 3 months |
| Reflection literature | `Phase: Continuous Process Improvement` — the reflection channel and the plateau question | `raw/reflection_literature.md` | 2026-07-23 | medium — 3 months |
| Production cases | The roadmap overall — what other teams hit, and where this approach diverges | `raw/production_cases.md` | 2026-07-23 | medium — 3 months |
| **Convergence and the plateau** | `Phase: Autonomous Operation` — "exit criteria that are real and observable"; and the one-loop-back bound already live in `revision.sh` | `raw/convergence_stopping.md` | 2026-08-03 | *(this cycle)* |
| **Parameterize vs fork** | Synthesis candidate #4, "the shared workflow library is the first-class artifact" + `Phase: Workflow Decomposition`'s gating ruling | `raw/workflow_reuse_boundary.md` | 2026-08-03 | *(this cycle)* |
| **Long activities, Python SDK** | `Phase: Temporal Integration` → the `claude_cli` activity domain; the roadmap's unchecked "Confirm the two known SDK constraints" | `raw/python_sdk_long_activities.md` | 2026-08-03 | *(this cycle)* |

### Why these three, and not the others

- **Convergence and the plateau.** The one-loop-back bound in `revision.sh` is *live today* and was set from an extrapolation the operator has already shown to be wrong (`phases/burn-test-intake-2026-08-02.md`, "the plateau correction": three passes, no plateau, and a cap at 1 would have left two live credential exits in `main`). A shipped design resting on evidence known to be bad is the most decision-blocking thing on the list.
- **Parameterize vs fork.** The burn-test intake calls this "the highest-leverage ruling in the queue," and it gates `build-phase` decomposition. Scoped here to the *premise* — does a parameterized shared library hold up, or do teams fork anyway — because that is what tests candidate #4. The concrete `build-phase` ruling is phase-level and is not asked here.
- **Long activities, Python SDK.** `temporal.md` marks heartbeat and payload limits UNVERIFIED against our shape, and the roadmap calls the `claude_cli` domain "the genuinely new work." A negative finding changes the port's shape, not merely its build order, which is what puts it at this altitude rather than inside the phase.

## Retirements

**None this cycle.** Every one of the eight existing papers still names a live destination: `Managed Configuration` now carries an explicit ⚠️ safety blocker that `hook_sourcing_supplement.md` is the direct evidence for; `Continuous Process Improvement` still has the reflection-sweep milestone open that `reflection_literature.md` feeds; and the three Temporal-facing papers feed a phase whose direction was *reaffirmed* since the last assessment, not abandoned. Four papers are past their revalidation window and are marked **(DUE)** above — that is `research-refresh.sh`'s work, not a retirement, and consumers treat them as unverified until it runs (§5).

## Gaps named, not covered this cycle

| Gap | Feeds | Why not here |
|---|---|---|
| **Inter-process handoff contracts** | `Phase: Memory Management Framework` (kind 2) | **Redirected, not deferred — the prior assessment placed it at the wrong altitude.** This folder's own `README.md` uses this exact question as its worked example of a *phase-level* question: "*should a parent hand off through a typed file or a parsed log* informs the Memory Management phase and belongs there." It informs a committed phase, it does not invalidate one. It belongs in `docs/development/phases/memory-management-framework/research/`, which does not exist yet because the phase doc is unwritten. Still the highest-value open research on the queue — the burn-test intake's Item 4 says so and flags its prior art as an unverified lead. It is not covered here because it must not be. |
| **Decide-only disposition — does a judging stage with no authoring authority actually reduce defects?** | `Phase: Workflow Decomposition`; validates `workflow-scripts.md § Composition`'s central claim | Per-cycle cap. `review-pr` already shipped as the last child of every PR-producing parent, so this is validation of a taken decision rather than a decision block — genuinely product-level (it is the README's own example of one), and first in line for the next cycle. |
| **Does an agentic `claude -p` run decompose into resumable per-turn legs?** | `Phase: Temporal Integration` → the choice between the single-activity and child-workflow shapes | **Surfaced by this cycle**, by `raw/python_sdk_long_activities.md` §8, which names it as the decisive fork and states plainly that it is *not* a Temporal question and therefore outside that paper's scope. No paper in the pool covers it. Product-level: it decides the port's shape. First-tier candidate for the next cycle alongside decide-only disposition. |
| **Duplicated prompt *prose* — does the clone-fault evidence transfer?** | `Phase: Workflow Decomposition`; the same ruling `raw/workflow_reuse_boundary.md` feeds | **Surfaced by this cycle.** Every quantified source in that paper concerns code or configuration. Much of what our near-copy workflows actually duplicate is prompt text, and the paper states it found no literature on that at all. If the evidence does not transfer, the fork-vs-parameterize ruling loses its empirical base. Deferred on the per-cycle cap, and because a topic with no located literature needs a scoping pass before it earns a dispatch. |
| **Reflection-channel mining** | `Phase: Continuous Process Improvement` — the open "sweep the reflection channel systematically" milestone | Phase-level, not product-level. The milestone is committed; the question is how to build the sweeper. Belongs in that phase's `research/`. |
| **Bash → Python Stage A conversion** | `Phase: Temporal Integration` — the staged convert → wrap → orchestrate path | Phase-level, and the direction is decided ("DECIDED: Python. Do not re-open this."). What remains is execution, which research does not settle. The one part that *is* product-level — whether the Python SDK can carry our activity shape — is covered as a topic above. |

---
id: C-k3nd8vwp
title: The producer definition Phase 4 adopted would reject Phase 5's digest — the one pairing both phase docs hold up as the exemplar of doing it right — and no phase rules the shape it falls into
status: open
count: 1
filed: 2026-08-27
filed_by: plan-verify
component: workflow-decomposition
size:
decision:
---

**PROPOSAL — rule a fifth shape into [Phase 4](../../docs/development/workflow-decomposition/phase4_nothing_invisible.md)'s producer definition before its gate is built: a surface read ON DEMAND, with no cadence and no exit.** Nothing behaves wrongly today; both phases are unbuilt.

**The definition Phase 4 adopted on 2026-08-27 is strictly stronger than the one its shapes were ruled against, and the phase says so itself.** Borrowing [Tracked Items Standard §0](../../docs/standards/documentation/tracked_items_standard.md), it now reads: *"a producer is a surface something else is meant to read; it is conformant when its reader is named, **the reader is invoked on a named cadence**, and the surface empties or terminates."* The phase is explicit that the cadence is the new part — *"that is this phase's definition with the cadence added, and the cadence is the part the measure-tool version was missing."*

**Apply it to [Phase 5](../../docs/development/workflow-decomposition/phase5_configuration_a_run_absorbed.md)'s deliverable and it fails.** The sixth `Journal-` tag is the producer; the two-bag comparison reader is the consumer. The reader is **named** ✅. It is invoked on a **named cadence** ❌ — nothing schedules it, and Phase 5's implementation steps do not scope one; a human runs it when two runs are suspected to disagree. The surface **empties or terminates** ❌ for the population — bags accumulate and are never edited after sealing.

**That is the pairing BOTH docs cite as the exemplar.** Phase 4: *"[Phase 5] is the strongest case for the produced half existing. It adds one producer and one consumer in the same phase, deliberately."* Phase 5: *"This phase is the strongest argument for [Phase 4], and it also dodges it — it ships its consumer in the same phase as its producer."* Both sentences were written against the **pre-strengthening** definition, which asked only whether a reader was named. Neither was re-checked when the definition gained the cadence clause on 2026-08-27.

**The consequence, and it is a real fork rather than a wording problem.** Whichever phase lands second discovers this, and the two escapes are not equivalent:

- **If Phase 4 lands first**, Phase 5 ships a producer its own component's brand-new gate red-flags, and the pressure is to bolt a cadence onto the reader that nobody asked for — inventing a schedule to satisfy a check is the shape that gets a gate routed around.
- **If Phase 5 lands first**, the definition is written with the exemplar already in the tree, and the honest answer is likely a carve-out — which is fine, but a carve-out written to excuse an existing surface is the weakest way to arrive at one.

**Phase 4 lists three shapes to rule on plus a fourth added on 2026-08-27** — a tool that answers a question (in), a record a run writes for a later run (probably in), a declaration module (out by name), and a surface whose only legitimate consumer is a human (`tracked/operations/`, out by name). **A surface read on demand by a named machine reader is none of those four.** It is not the human case: the reader is code, and a check *can* observe that it exists and resolves. It is the second shape with the cadence question left open, and the second shape is where Phase 4 says *"the real value is."*

**Proposed action.** In the step that writes the definition, add a fifth honest test beside the intake one already there: *the definition must give a defensible answer for a surface whose named reader is invoked on demand rather than on a schedule.* Rule it explicitly one way — either the cadence clause is required only of surfaces that ACCUMULATE (a store), leaving on-demand readers conformant, or an on-demand reader is non-conformant and Phase 5 must scope who runs the comparison and when. **Both are defensible; what is not defensible is discovering it while building the second of the two phases.**

**Why the §0 borrowing does not settle it by itself.** §0's three properties govern **stores** — surfaces that accumulate items awaiting a decision — and its exit clause is about items reaching a terminal state. Phase 4 generalises them to **producers**, which is a wider class that includes surfaces nothing accumulates in. The generalisation is a good one and this candidate does not reopen it; the gap is that the wider class contains a member the narrower one never had to cover.

**Not a duplicate of [[C-v4k9pz2h]].** That proposes splitting Phase 4 into its derived and produced halves, and this finding lands inside the produced half whichever way that is ruled. If the split is adopted, this belongs to the produced half's phase.

**Source:** `plan-verify` cold read of `docs/development/workflow-decomposition`, 2026-08-27, following Phase 4 § *The stores supplied the definition this phase was missing* into [Tracked Items Standard §0](../../docs/standards/documentation/tracked_items_standard.md) and back out to Phase 5 § *Requirements for completion*.

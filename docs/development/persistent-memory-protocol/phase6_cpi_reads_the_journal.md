# Phase 6 — CPI reads the journal

**Component:** [Persistent Memory Protocol](roadmap.md) · **Status:** not started · **Gate:** Phase 4, and *Port `review-runs`* ([`sprint.md`](../sprint.md) § *Sprint: Temporal Integration*)

## What this phase does

Every phase before this one *writes* the record. This one is the first thing that reads it.

The continuous-improvement sweep is the tool that looks across many past runs and asks what keeps going wrong. Today it does that by walking a pile of log files scattered per repository checkout, plus whatever a person points it at. After this phase it reads the journal instead: one place, everything a run wrote and everything it did, joined by run id.

**This is the consumer for everything Phases 1–4 produce, and that is the whole reason it exists as its own phase.**

**Terms used here.** The **journal** is the whole record: one folder per run, never edited after the run ends. A **bag** is one run's folder (the name comes from BagIt, the file-layout standard it follows — a folder on disk, never a Docker container). **CPI** is continuous process improvement — the cycle that reads past runs for recurring problems and turns them into tracked decisions; its **evidence sweep** is the read half of that. A **gap event** is [Phase 3](phase3_the_emit_rule.md)'s record of a write that failed. An **edge** is one machine running this fleet.

The synthesis states the discipline this phase enforces plainly: **pair every producer with its consumer.** A producer with no consumer is how 262 MB accumulated unread — and this fleet has the measured local record of what happens otherwise: three separate phases each added a parent-written observable to the same run log and **no committed tool read any of the three**; two of those three shipped with no reader at all, and only one of the two even placed a candidate for one.

---

## Why this phase sits ahead of Phase 5 in the roadmap, and why it was split at review

**At draft this was one phase with the poller, gated on the Temporal server.** That would have put this component's *only consumer* behind a server nobody has stood up, for four phases of producers — the failure above, committed by the plan that cites it as its own cautionary precedent, with a longer fuse and a larger store.

Only the **poller** needs a scheduler. **Reading the journal needs a journal.** So the two split: this phase, and [Phase 8](phase8_the_poller.md).

**It still has a gate, and it is a real one.** The CPI evidence sweep exists today only as `scripts/workflows/review-runs.sh`, which is in the **frozen bash fleet** and may not be modified. Its Python port is a milestone of the [Temporal Integration](../temporal-integration/temporal-integration.md) component, tracked as a checkbox in [`sprint.md`](../sprint.md) § *Sprint: Temporal Integration*. This phase builds on the port; it does not perform it, and it does not touch the bash script.

---

## Requirements for completion

1. **CPI's evidence sweep sources the journal**, not a per-repo JSONL walk.
2. **The two agree on one overlapping window.** The journal-sourced sweep and the incumbent sweep produce the same findings over the same period, and any disagreement is explained rather than averaged away.
3. **Every producer shipped by Phases 1–4 has a named, committed consumer** — enumerated in this doc as a table, not asserted in prose.
4. **The cross-run sweep's wall-clock is measured against journal size**, and reported as the first real test of [Phase 1](phase1_the_run_bag.md)'s no-database decision.
5. **Cross-machine CPI is not built here.** CPI stays on one machine until a second one produces runs.
6. **Any gap in the journal appears in the sweep's own output.** § *A report over an incomplete record says so* below.
7. **The sweep reaches its evidence through one storage interface**, with the local filesystem as the first implementation, and no filesystem semantics leak into the sweep itself. § *Why the reader has to be portable before anything needs it to be* below. This requirement exists because [Phase 7](phase7_s3_aggregation.md) requirement 3 depends on it and Phase 6 is built four positions earlier. **The interface's shape is also a boundary the [Temporal Integration](../temporal-integration/temporal-integration.md) component owns** — the sweep becomes a ported workflow and this is its I/O boundary — so what this phase states is what it needs, not the mechanism ([roadmap § *Constraints that run BOTH ways*](roadmap.md#constraints-that-run-both-ways-with-the-temporal-port)).

---

## Dependencies

- **[Phase 4](phase4_rebuild_is_a_test.md)** — hard. Reading a journal whose completeness is unproven means reporting findings from a record that may be missing the runs that mattered.
- ***Port `review-runs`*** — hard, and it is outside this component. It is a milestone of the [Temporal Integration](../temporal-integration/temporal-integration.md) component, tracked as a checkbox in [`sprint.md`](../sprint.md) § *Sprint: Temporal Integration* — **that is where to check whether the gate has opened**, not the component doc, which contains neither string. **This is the only gate; the Temporal server is not one.** A sweep is a batch read, not a schedule.
- **Not** [Phase 5](phase5_snapshots_then_retention.md). Retention makes the journal bounded; it does not make it readable. If the sweep is uncomfortable at this phase's journal size, requirement 4's measurement is the evidence that pulls Phase 5 forward — which is a finding, not a reason to wait.

---

## What this phase decides

### CPI reads one store instead of searching for evidence

CPI today assembles its evidence from a per-repo pile of `.claude/logs/*.jsonl` plus whatever a human points it at. Under the journal, everything a run authored *and* everything it did are joined by `run_id` in one place — which is what turns the accumulated log from a liability into the asset the synthesis argues it is. **The fix for a store nobody reads is the reader, not a smaller store.**

**Requirement 2 is the honest part.** A new reader over a new store that produces *different* findings from the incumbent is not obviously better — it might be seeing more, or it might be seeing a subset it can parse. Running both over one window and explaining every difference is what distinguishes those two cases, and it is cheap exactly once, before the incumbent is retired.

### The producer/consumer table

**Requirement 3 is the discipline this component keeps invoking, made checkable.** Prose that says *"every producer has a consumer"* is the same unfalsifiable universal [Phase 3](phase3_the_emit_rule.md)'s requirement 1 needed converting; a table is checkable by a reviewer, and a blank cell is the finding.

| Producer (phase, artifact) | Consumer | Committed at |
|---|---|---|
| *(enumerated at build time)* | | |

**A producer with no consumer at the end of this phase is not deferred work — it is either a consumer that must be built here, or a producer that should not have shipped.** Naming which is part of the requirement.

### This is the no-database decision's first real test

[Phase 1](phase1_the_run_bag.md) records *no database* as a decision with a revisit trigger: **a real query that the tree cannot serve.** `state_passing` §4.3.3's format table has exactly one empty row — *queries over accumulated history* — and this phase's sweep is one.

**So requirement 4 is not telemetry, it is the trigger's evidence.** If a cross-run sweep over a directory tree is comfortable at this journal's size, the decision holds and the measurement says by how much. If it is not, the trigger has fired on a number rather than on a feeling, which is what Phase 1 asked for — and per that section, adopting a database is then install-and-import, with nothing in this component needing to change.

### Why the reader has to be portable before anything needs it to be — requirement 7

[Phase 7](phase7_s3_aggregation.md) requirement 3 says the sweep reads shared object storage **with no change to the reader written here** — the input location changes, the reader does not. That is what makes the cross-machine step cheap, and it is the reason this phase must not be built as throwaway.

**But a constraint stated in a later phase does not build itself in an earlier one.** The natural implementation of a sweep over a local folder tree walks directories, calls `stat`, and assumes a rename is atomic. **None of that survives object storage**, so Phase 7 would become a rewrite of this reader rather than a change of its input — and by then this phase has been closed for however long the second machine took to arrive.

**So the constraint lands here, as a requirement, at the phase that can actually satisfy it.** The interface is small: enumerate bags, read a file from a bag, read the gap events. The local implementation is a thin wrapper over the filesystem and costs almost nothing now; retrofitting it after three consumers read the tree directly is a cross-cutting refactor.

*(This is one of several forward constraints a gated phase turned out to place on an ungated one. Each was invisible while the gated phase was a roadmap row, and the [roadmap](roadmap.md#what-a-gated-phase-requires-of-a-phase-being-built-today) now tracks them as a table so the next one cannot go missing the same way.)*

### A report over an incomplete record says so — requirement 6

**A sweep that reads a record with holes in it and reports as though the record were whole is worse than no sweep**, because its silence reads as evidence. "Nothing recurring in the last thirty runs" is a very different statement depending on whether the record actually holds thirty runs.

Two sources of incompleteness reach this phase, and both already have their own machinery:

- **Gap events.** [Phase 3](phase3_the_emit_rule.md) rules that a failed journal write appends a typed gap event and marks the bag `incomplete`. [Phase 4](phase4_rebuild_is_a_test.md) requirement 7 reports gapped bags against bags replayed **and against bags rotated out behind the snapshot, deduped on `run_id`**. **This phase carries that number into its own output with the same denominator**, so a reader of a CPI report learns it from the report — and so the ratio cannot drift above 1 as retention shrinks the denominator under a numerator the snapshot preserves.
- **Stores the journal could not rebuild.** [Phase 4](phase4_rebuild_is_a_test.md) § *Stores not covered* names each and says why. Those exclusions are inherited here, and they belong in the same place.

**The place is the sweep's own output, not this document.** Someone reading a CPI report should not have to find a phase doc in a component they may never have heard of in order to learn what the record does not contain. That is the same reasoning [Phase 4](phase4_rebuild_is_a_test.md) requirement 6 applies to the two markdown tables, applied one layer up.

### What this phase deliberately does not build

- **The poller.** [Phase 8](phase8_the_poller.md).
- **Cross-machine CPI.** [Phase 7](phase7_s3_aggregation.md), and only once a second machine produces runs. The sequencing is the synthesis's and it is a sequencing decision rather than a compromise: **the same reader, different input** is what makes the cross-edge step cheap later, and it is the reason this phase must not be built as throwaway.
- **Any modification to `scripts/workflows/review-runs.sh`.** Frozen.

---

## Implementation checklist

- [ ] Confirm the Python `review-runs` port has landed; if not, stop — this phase is gated, and the bash script is not an option
- [ ] Put the sweep's evidence access behind one storage interface — enumerate bags, read a file from a bag, read the gap events — with the local filesystem as the first implementation, and assert no filesystem semantics leak past it
- [ ] Point the sweep's evidence source at the journal, joined by `run_id`
- [ ] Run both sweeps over one overlapping window and record every disagreement with its explanation
- [ ] Build the producer/consumer table above from Phases 1–4's shipped artifacts, and resolve every blank cell
- [ ] Measure sweep wall-clock against journal size, with the denominator, in § *Measurement*
- [ ] Tests per the [Testing Standard](../../standards/testing/README.md) — `unit/` for the journal-sourced evidence assembly, `integration/` for a real sweep over a real journal
- [ ] Carry [Phase 4](phase4_rebuild_is_a_test.md)'s gapped-bag count and its § *Stores not covered* exclusions into the sweep's own output, so a report over an incomplete record says so
- [ ] Confirm the incumbent's retirement is a separate decision with its own evidence, not a side effect of this phase

---

## Measurement

*(Populated when the phase runs. Figures come from commands run in the tree and are pasted with the command.)*

Three figures with denominators: **findings agreed against findings total** across the overlapping window (requirement 2); **sweep wall-clock against journal size** (requirement 4), which is the figure Phase 1's no-database revisit trigger reads; and **runs the sweep could read against runs in the window** (requirement 6), which is what makes a null finding interpretable.

---

## Notes and open items

- **This phase does not retire the incumbent sweep.** Requirement 2 produces the evidence that would justify retiring it; acting on that evidence is a separate change, so a disagreement discovered here cannot be resolved by deleting the thing that disagreed.
- **If Phase 4's completeness arm has known exclusions** (stores it could not rebuild), this phase's findings inherit them. Requirement 6 is where that lands, and it puts them in the sweep's own output rather than in this doc.

# Phase 6 — CPI reads the journal

**Component:** [Persistent Memory Protocol](roadmap.md) · **Status:** not started · **Gate:** Phase 4, and *Port `review-runs`* in [Temporal Integration](../temporal-integration/temporal-integration.md)

Moves CPI's evidence sweep onto the journal, so it reads one store instead of walking a per-repo pile of JSONL.

**This is the consumer for everything Phases 1–4 produce, and that is the whole reason it exists as its own phase.** The synthesis states the discipline plainly: **pair every producer with its consumer.** A producer with no consumer is how 262 MB accumulated unread — and this fleet has the measured local record of what happens otherwise. [MMF Phase 6](../memory-management-framework/phase6_read_what_it_writes.md) exists because three separate phases each added a parent-written observable to the same run log and **no committed tool read any of the three**; two of those three shipped with no reader at all, and only one of the two even placed a candidate for one.

---

## Why this phase sits ahead of Phase 5 in the roadmap, and why it was split at review

**At draft this was one phase with the poller, gated on the Temporal server.** That would have put this component's *only consumer* behind a server nobody has stood up, for four phases of producers — the failure above, committed by the plan that cites it as its own cautionary precedent, with a longer fuse and a larger store.

Only the **poller** needs a scheduler. **Reading the journal needs a journal.** So the two split: this phase, and [Phase 8](roadmap.md#phase-8--the-poller-gated-temporal-schedules).

**It still has a gate, and it is a real one.** The CPI evidence sweep exists today only as `scripts/workflows/review-runs.sh`, which is in the **frozen bash fleet** and may not be modified. Its Python port is an open item in [Temporal Integration](../temporal-integration/temporal-integration.md) (*Port `review-runs`*). This phase builds on the port; it does not perform it, and it does not touch the bash script.

---

## Requirements for completion

1. **CPI's evidence sweep sources the journal**, not a per-repo JSONL walk.
2. **The two agree on one overlapping window.** The journal-sourced sweep and the incumbent sweep produce the same findings over the same period, and any disagreement is explained rather than averaged away.
3. **Every producer shipped by Phases 1–4 has a named, committed consumer** — enumerated in this doc as a table, not asserted in prose.
4. **The cross-run sweep's wall-clock is measured against journal size**, and reported as the first real test of [Phase 1](phase1_the_run_bag.md)'s no-database decision.
5. **Cross-edge CPI is not built here.** CPI stays on Edge1 until a second edge produces runs.

---

## Dependencies

- **[Phase 4](phase4_rebuild_is_a_test.md)** — hard. Reading a journal whose completeness is unproven means reporting findings from a record that may be missing the runs that mattered.
- **[Temporal Integration](../temporal-integration/temporal-integration.md) → *Port `review-runs`*** — hard, and it is outside this component. **This is the only gate; the Temporal server is not one.** A sweep is a batch read, not a schedule.
- **Not** [Phase 5](roadmap.md#phase-5--snapshots-then-retention-gated-temporal-server). Retention makes the journal bounded; it does not make it readable. If the sweep is uncomfortable at this phase's journal size, requirement 4's measurement is the evidence that pulls Phase 5 forward — which is a finding, not a reason to wait.

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

### What this phase deliberately does not build

- **The poller.** [Phase 8](roadmap.md#phase-8--the-poller-gated-temporal-schedules).
- **Cross-edge CPI.** [Phase 7](roadmap.md#phase-7--s3-aggregation-local-write-first-gated-a-second-edge-and-a-classification-ruling), and only once a second edge produces runs. The sequencing is the synthesis's and it is a sequencing decision rather than a compromise: **the same reader, different input** is what makes the cross-edge step cheap later, and it is the reason this phase must not be built as throwaway.
- **Any modification to `scripts/workflows/review-runs.sh`.** Frozen.

---

## Implementation checklist

- [ ] Confirm the Python `review-runs` port has landed; if not, stop — this phase is gated, and the bash script is not an option
- [ ] Point the sweep's evidence source at the journal, joined by `run_id`
- [ ] Run both sweeps over one overlapping window and record every disagreement with its explanation
- [ ] Build the producer/consumer table above from Phases 1–4's shipped artifacts, and resolve every blank cell
- [ ] Measure sweep wall-clock against journal size, with the denominator, in § *Measurement*
- [ ] Tests per the [Testing Standard](../../standards/testing/README.md) — `unit/` for the journal-sourced evidence assembly, `integration/` for a real sweep over a real journal
- [ ] Confirm the incumbent's retirement is a separate decision with its own evidence, not a side effect of this phase

---

## Measurement

*(Populated when the phase runs. Figures come from commands run in the tree and are pasted with the command.)*

Two figures with denominators: **findings agreed / findings total** across the overlapping window (requirement 2), and **sweep wall-clock against journal size** (requirement 4). The second is the one Phase 1's no-database revisit trigger reads.

---

## Notes and open items

- **This phase does not retire the incumbent sweep.** Requirement 2 produces the evidence that would justify retiring it; acting on that evidence is a separate change, so a disagreement discovered here cannot be resolved by deleting the thing that disagreed.
- **If Phase 4's completeness arm has known exclusions** (stores it could not rebuild), this phase's findings inherit them. Say so in the sweep's own output rather than in this doc — a reader of a CPI report should not have to come here to learn what the record does not contain.

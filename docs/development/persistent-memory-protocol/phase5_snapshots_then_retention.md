# Phase 5 — Snapshots, then retention

**Component:** [Persistent Memory Protocol](roadmap.md) · **Status:** not started · **Gate:** the Temporal server, for the recurring half only

## What this phase does

The journal grows and nothing deletes any of it. This phase adds the deleting — and, before that, the thing that makes deleting safe.

The order matters more than either half. By the time this phase runs, the folders on disk are the only place some information exists: [Phase 4](phase4_rebuild_is_a_test.md) made the markdown tables and other stores into things the journal regenerates, so **deleting old folders is a decision about what the fleet can no longer reconstruct**, not a decision about disk space. Deleting first and thinking later is how a rebuild stops working, silently, weeks after the change.

So this phase builds a **snapshot** first — a record of what every store held at one moment, written into the journal — and only then a **retention pass** that deletes old run folders, oldest first, and refuses to delete past the most recent snapshot. Everything before the snapshot is redundant with it; everything after it is needed.

It also splits the record in two, because the two halves are nothing alike. The text runs actually wrote is about 40 KB per run and roughly 7 MB for the fleet's entire history; it is never deleted. The transcript — every tool call and result — is 99.2% of the bytes and stops being useful within weeks; it is deleted on a schedule.

**Terms used here.** A **journal** is the whole record: one folder tree per machine, one folder per run, never edited after the run ends. A **bag** is one run's folder (the name comes from BagIt, the file-layout standard it follows — it is a folder on disk, never a Docker container). A **manifest** is the file inside a bag listing every payload file with its checksum. To **emit** is to write one entry into the journal. To **rebuild** a store is to read the journal back and regenerate what that store holds. A **snapshot** records what every store held at one moment, so a rebuild can start there rather than at the beginning of history.

## Why this phase waits, and what that does not mean

**The gate is the Temporal server**, and it reaches **exactly one of this phase's seven requirements — requirement 1's recurrence.** A retention pass on a cadence is a scheduled workflow plus a configuration value; there is no scheduler today, so nothing runs it on a cadence. That is a fact about the calendar.

**Every other requirement here is a policy and a command, and each is labelled `(ungated)` above so a dispatch can act on the trigger rather than stall on the phase.** That matters because two other docs name pulling this phase forward as an evidence-driven action ([Phase 4](phase4_rebuild_is_a_test.md) § Notes and [Phase 6](phase6_cpi_reads_the_journal.md) § Dependencies) — and a trigger that fires against a phase whose scope nobody has divided is a trigger nobody can act on. **The window this closes is real:** after Phase 4, removing a payload file is a merge-gate change, so a fleet with no retention mechanism accumulates a permanently unbounded store until an out-of-component gate opens.

**It is not a reason the snapshot mechanism waits.** [Phase 4](phase4_rebuild_is_a_test.md) requirement 2 already builds a one-off snapshot, because its rebuild test has no baseline without one — `candidates.md` carries rows that predate the journal by months, so replaying only what Phase 3 emitted forward reproduces a store that starts empty and never matches. **This phase adds the recurring snapshot and the deletion; it does not invent the snapshot.**

*(That distinction was got wrong once and the error is worth naming, because it is easy to repeat. "Rotation must not ship without a snapshot to stop at" constrains rotation. It says nothing about snapshots needing rotation — and reading it symmetrically parked the snapshot mechanism behind rotation's scheduler, which made Phase 4 unclosable.)*

---

## Requirements for completion

1. **(GATED — this is the only requirement here that needs the server.) A recurring snapshot records every store's state into the journal**, addressable as the point a rebuild starts from. It records the same store set [Phase 4](phase4_rebuild_is_a_test.md) tests against, and a store Phase 4 could not rebuild is not silently snapshotted as though it could be.
2. **(ungated) A retention dry-run refuses to delete past the most recent snapshot**, demonstrated against a real journal — and the refusal is a non-zero exit with a named reason, not a warning.
3. **(ungated) The authored record and the transcript carry separate stated retention rules**, and the transcript is removable from inside a run folder without destroying the record.
4. **(ungated) A rebuild from the most recent snapshot forward still passes [Phase 4](phase4_rebuild_is_a_test.md)'s test after a retention pass has run** — demonstrated by running that test on both sides of a real deletion.
5. **The storage budget and the snapshot cadence are recorded as ruled numbers.** This requirement stays **unchecked** until the operator rules them; see [roadmap § *Open inputs*](roadmap.md#open-inputs--questions-this-plan-carries-forward-without-answering), item 1.
6. **(ungated) A retention pass emits its own journal events** — what it deleted, when, and under which snapshot — and leaves each affected bag validating in the `pruned` state rather than reporting missing files.
7. **(ungated) A bag that is both incomplete and pruned stays distinguishable as both.** § *Retention meets a gapped bag* below.

---

## Dependencies

- **[Phase 4](phase4_rebuild_is_a_test.md)** — hard, and in both directions of reasoning. Phase 4 supplies the one-off snapshot mechanism this phase makes recurring, and it supplies the test that requirement 4 runs. **Without Phase 4 there is no way to know whether a deletion broke anything**, which is precisely the state this phase must not be built in.
- **[Phase 1](phase1_the_run_bag.md)** — supplies the `pruned` lifecycle state and the rule that pruning regenerates a manifest and leaves a tombstone. This phase inherits that rule; it does not invent one under time pressure.
- ***Stand up the Temporal server*** — for requirement 1's recurrence only. It is a milestone of the [Temporal Integration](../temporal-integration/temporal-integration.md) component, tracked as a checkbox in [`sprint.md`](../sprint.md) § *Sprint: Temporal Integration*.
- **Not [Phase 6](phase6_cpi_reads_the_journal.md).** Retention makes the journal bounded; it does not make it readable. If Phase 6's sweep is uncomfortable at its journal size, that measurement is evidence for pulling this phase forward — which is a finding, not a reason Phase 6 waits.

---

## What this phase decides

### The snapshot is what makes deletion a bounded loss rather than an open one

A snapshot is a full materialization: every store in the test set, written into the journal as it stands at that moment, as one addressable event. After it exists, every journal event *before* it is redundant — a rebuild that starts at the snapshot and replays forward reaches the same result as one that starts at the beginning.

**That redundancy is the entire licence to delete anything**, and it is why the two halves cannot be separated into different phases. Rotation without a snapshot to stop at is not an incomplete feature; it is a data-loss bug wearing a feature's clothes, because after [Phase 4](phase4_rebuild_is_a_test.md) the journal is the only thing that can regenerate a store.

**What a snapshot does not cover.** It records what stores held, not the reasoning inside the deleted run folders. A run's transcript is not reconstructible from a snapshot of `candidates.md`, and it never will be. That is the accepted cost of requirement 3's split, stated here rather than discovered later: **deleting the transcript loses the ability to diagnose an old run, and keeps the ability to answer what happened and why.**

### The two halves of the record get different rules, and the split is measured

| | One `research_minor` cycle | Rule |
|---|---|---|
| **Authored output** — pull-request body, comments, decisions, triage, candidate rows | 39,772 bytes | **Never deleted.** At that rate the entire 175-run history is roughly 7 MB. There is no volume argument for deleting it, and it is the half that answers *what happened and why*. |
| **CLI transcript** — every tool call and result | 4,823,628 bytes | **Deleted on a schedule.** It is 99.2% of the bytes and its value decays — it is what you read to diagnose a run, and that need is concentrated in the weeks after it ran. |

*(Both figures are the synthesis's, measured 2026-08-12, and are the baseline this phase's own measurement is taken against. § Measurement.)*

**The transcript is deleted from inside a run folder, and the folder survives.** That is the seam [Phase 1](phase1_the_run_bag.md)'s per-run layout exists to give: no record is destroyed, only its most expensive part. A folder that has had its transcript removed regenerates its manifest and reports as `pruned` — valid, with a tombstone naming what was removed and when — rather than reporting missing files, which would be indistinguishable from data loss.

**Whole-folder deletion is the other operation and it is bounded differently.** Oldest first, never past the most recent snapshot, and only for folders whose authored content is already covered by that snapshot. The two operations are not variants of each other and requirement 3 keeps them separate.

**Two further bounds, because the snapshot barrier alone is weaker than it reads.** Writing one snapshot makes *everything before it* eligible in a single step, and the only other limit is a storage budget nobody has ruled yet (requirement 5). So: **a minimum age floor applies independently of the snapshot barrier**, and **a retention pass is fleet-code only** — never a model-issued write, using [Phase 3](phase3_the_emit_rule.md) requirement 9's own distinction between the two.

**And the record of a deletion must outlive the thing it deleted.** Requirement 6's retention events, [Phase 3](phase3_the_emit_rule.md)'s gap events and [Phase 1](phase1_the_run_bag.md)'s redaction events all live in bags that a later oldest-first pass would remove — which would delete the explanation of a deletion, and the historical fact that the record ever had holes. **These three event classes are exempt from whole-folder deletion, or they are folded into the snapshot.** Either is acceptable; losing them is not.

### Retention meets a gapped bag — requirement 7

[Phase 3](phase3_the_emit_rule.md) rules that a failed journal write is never silent: where nothing can be withheld, the failure appends a typed **gap event** and the bag is marked `incomplete`. That state has to survive this phase, and the naive implementation destroys it.

The problem is that pruning and gapping both leave a bag with fewer payload files than its manifest once listed, and both regenerate the manifest. **Collapsing them makes a bag that lost data to a disk-full error indistinguishable from one that was deliberately trimmed** — and the first is a defect to investigate while the second is the system working. Since the whole point of a gap event is that a reader can tell the record is incomplete, losing that distinction at the retention boundary silently un-does [Phase 3](phase3_the_emit_rule.md)'s guarantee.

**So `incomplete` and `pruned` are independent facts about a bag, not two values of one field.** A bag can be neither, either, or both, and the validator reports both. A retention pass never clears `incomplete`, and requirement 6's tombstone records only what *this pass* removed.

### Deleting is itself a write, so it emits

[Phase 3](phase3_the_emit_rule.md)'s rule has no exception for the fleet's own maintenance. A retention pass changes what the record contains, which is the single most consequential kind of change anything makes to it — so it emits: what was deleted, when, under which snapshot, and by which pass.

**This is not bookkeeping.** Without it, the answer to *"why can I not find run X"* is indistinguishable from *"run X never happened"*, and those are very different facts. The emitted event is what makes a deleted run's absence explicable rather than merely true.

### What is not built here

- **Any cross-machine retention.** A bucket has its own lifecycle rules and its own cost model. [Phase 7](phase7_s3_aggregation.md) owns that, and it must not inherit this phase's numbers by default — the local budget is bounded by one disk and the remote one is not.
- **Deleting the content store — and this gap is now PLACED rather than named.** [Phase 2](phase2_content_store.md)'s cached bytes are referenced by checksum from potentially many bags, so deleting them needs a reachability pass. **Whether the gap exists at all is decided by [Phase 2](phase2_content_store.md) requirement 7(a)**: under the per-run shape, deleting a bag deletes its bytes and there is nothing to reclaim; under the root-level-shared shape, nothing reclaims anything and the store grows without bound. So the obligation is written into the decision that creates it — Phase 2 r7(a) now states that choosing root-level shared creates a reclamation obligation — and requirement 6's checklist below carries the conditional pass. *(It was prose in this section's Notes until review, which is a deferral with no placement and the shape `engineering-quality.md` forbids.)*
- **A retention rule for a store that Phase 4 could not rebuild.** Requirement 1 forbids snapshotting such a store as though it were covered. If any exist, they are listed in [Phase 4](phase4_rebuild_is_a_test.md) § *Stores not covered* and this phase's snapshot names them as out of coverage rather than including them silently.

---

## Implementation checklist

- [ ] Build the recurring snapshot on top of [Phase 4](phase4_rebuild_is_a_test.md)'s one-off mechanism, addressable as a replay starting point, over the same store set Phase 4 tests
- [ ] Specify the retention rule: whole folders oldest-first, never past the most recent snapshot, with a minimum age floor, restricted to the fleet-code path, and the refusal as a non-zero exit with a named reason
- [ ] Exempt retention, gap and redaction events from whole-folder deletion, or fold them into the snapshot — and demonstrate that the explanation of a deletion survives the deletion
- [ ] Specify the transcript rule separately: removable from inside a folder, manifest regenerated, tombstone written, folder still valid
- [ ] Keep `incomplete` and `pruned` independent, and confirm a bag carrying both reports both
- [ ] Emit a journal event per retention pass naming what was deleted, when, and under which snapshot
- [ ] **If [Phase 2](phase2_content_store.md) r7(a) ruled root-level shared:** build the reachability pass that reclaims content-store objects no retained bag references. If it ruled per-run, record that this is a no-op and why
- [ ] Demonstrate a dry-run refusing to cross the last snapshot, against a real journal, and record the command
- [ ] Run [Phase 4](phase4_rebuild_is_a_test.md)'s rebuild test on both sides of a real deletion and record both results
- [ ] Record the storage budget and snapshot cadence **once the operator has ruled them**, and leave requirement 5 unchecked until then with prose saying why
- [ ] Tests per the [Testing Standard](../../standards/testing/README.md): `unit/` for the refusal condition, the two retention rules and the `incomplete`/`pruned` independence; `integration/` for a real snapshot-then-delete-then-rebuild cycle
- [ ] Record measured journal size before and after one retention pass, with its denominator, in § *Measurement*

---

## Measurement

*(Populated when the phase runs. Every figure is produced by a command run against the tree and pasted with the command that produced it.)*

The figures this phase owns, each with a denominator:

- **Journal size before and after one retention pass**, with the number of folders affected — the only figure that says whether the retention rule is doing anything.
- **Rebuild wall-clock from the most recent snapshot versus from the beginning**, over the same store set. This is what the snapshot is *for*, and if the two are close the cadence is too tight.
- **Authored bytes retained versus transcript bytes deleted**, against the synthesis's 39,772 / 4,823,628 baseline for one `research_minor` cycle. A materially different ratio at fleet scale means the split rule is not cutting where the measurement said it would.

---

## Notes and open items

- **Requirement 5's two numbers are the only thing in this phase that no amount of work produces.** They are preferences and they trade against each other: a longer snapshot cadence needs more disk to stay rebuildable, and a tighter storage budget forces a tighter cadence. This phase can be built and demonstrated with placeholder values; it cannot be *closed* with them, which is why requirement 5 exists as its own line rather than as a configuration detail.
- **The content-store gap named above is the most likely thing to be forgotten.** It is out of scope here deliberately — a reachability pass over content-addressed objects is its own piece of work — but it means "the journal is bounded" will be *false* until something owns it, and anyone reading a bounded-journal claim after this phase should know that.

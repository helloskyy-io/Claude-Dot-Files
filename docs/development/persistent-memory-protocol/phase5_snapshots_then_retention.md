# Phase 5 — Snapshots, then retention

**Component:** [Persistent Memory Protocol](roadmap.md) · **Status:** not started · **Gate:** the Temporal server, for the recurring half only

## What this phase does

The journal grows and nothing deletes any of it. This phase adds the deleting — and, before that, the thing that makes deleting safe.

The order matters more than either half. By the time this phase runs, the folders on disk are the only place some information exists: [Phase 4](phase4_rebuild_is_a_test.md) made the markdown tables and other stores into things the journal regenerates, so **deleting old folders is a decision about what the fleet can no longer reconstruct**, not a decision about disk space. Deleting first and thinking later is how a rebuild stops working, silently, weeks after the change.

So this phase builds a **snapshot** first — a record of what every store held at one moment, written into the journal — and only then a **retention pass** that deletes old run folders, oldest first, and refuses to delete past the most recent snapshot. Everything before the snapshot is redundant with it; everything after it is needed.

**There is one number and it is a size.** The journal has a storage budget — 1 GB by default, a configuration value — and it governs the whole journal with nothing exempt. When the journal is over budget, whole run folders go, oldest first, until it is back under.

**Terms used here.** A **journal** is the whole record: one folder tree per machine, one folder per run, never edited after the run ends. A **bag** is one run's folder (the name comes from BagIt, the file-layout standard it follows — it is a folder on disk, never a Docker container). A **manifest** is the file inside a bag listing every payload file with its checksum. To **emit** is to write one entry into the journal. To **rebuild** a store is to read the journal back and regenerate what that store holds. A **snapshot** records what every store held at one moment, so a rebuild can start there rather than at the beginning of history. The **budget** is the journal's one size limit.

## Why this phase waits, and what that does not mean

**The gate is the Temporal server**, and it reaches **exactly one of this phase's requirements — requirement 1's recurrence.** Running the retention pass on a cadence is a scheduled workflow; there is no scheduler today, so nothing runs it unattended. That is a fact about the calendar.

**Every other requirement here is a policy and a command, and each is labelled `(ungated)` below so a dispatch can act on the trigger rather than stall on the phase.** That matters because two other docs name pulling this phase forward as an evidence-driven action ([Phase 4](phase4_rebuild_is_a_test.md) § Notes and [Phase 6](phase6_cpi_reads_the_journal.md) § Dependencies) — and a trigger that fires against a phase whose scope nobody has divided is a trigger nobody can act on. **The window this closes is real:** after Phase 4, removing a payload file is a merge-gate change, so a fleet with no retention mechanism accumulates a permanently unbounded store until an out-of-component gate opens.

**It is not a reason the snapshot mechanism waits.** [Phase 4](phase4_rebuild_is_a_test.md) requirement 2 already builds a one-off snapshot, because its rebuild test has no baseline without one — `candidates.md` carries rows that predate the journal by months, so replaying only what Phase 3 emitted forward reproduces a store that starts empty and never matches. **This phase adds the recurring pass and the deletion; it does not invent the snapshot.**

*(One-way constraint, stated because reading it symmetrically once parked the snapshot mechanism behind rotation's scheduler and made Phase 4 unclosable: "rotation must not ship without a snapshot to stop at" constrains **rotation**. It says nothing about snapshots needing rotation.)*

---

## Requirements for completion

1. **(GATED — the only requirement here that needs the server.) A recurring retention pass runs on a cadence**, brings the journal under budget, and **writes a snapshot when it needs a newer barrier to delete against.** A snapshot records the same store set [Phase 4](phase4_rebuild_is_a_test.md) tests against, and a store Phase 4 could not rebuild is not silently snapshotted as though it could be.
2. **(ungated) The budget is one configuration value with a documented default of 1 GB**, and it governs **the whole journal**. **No half is exempt, no floor is reserved, and there is no second number.** § *One budget, and nothing is exempt from it* below.
3. **(ungated) Deletion is whole run folders, oldest first, until the journal is under budget** — **never a partial run.** § *A partial run record is worthless* below.
4. **(ungated) A retention dry-run refuses to delete past the most recent snapshot**, demonstrated against a real journal — and the refusal is a non-zero exit with a named reason, not a warning.
5. **(ungated) A rebuild from the most recent snapshot forward still passes [Phase 4](phase4_rebuild_is_a_test.md)'s test after a retention pass has run** — demonstrated by running that test on both sides of a real deletion.
6. **(ungated) A retention pass emits its own journal events** — what it deleted, when, and under which snapshot — and those events are **folded into the snapshot** so that the explanation of a deletion survives the next one. § *The record of a deletion has to outlive what it deleted*.
7. **(ungated) A bag that is both incomplete and redacted stays distinguishable as both.** § *Retention meets a gapped bag* below.

---

## Dependencies

- **[Phase 4](phase4_rebuild_is_a_test.md)** — hard, and in both directions of reasoning. Phase 4 supplies the one-off snapshot mechanism this phase makes recurring, and it supplies the test that requirement 5 runs. **Without Phase 4 there is no way to know whether a deletion broke anything**, which is precisely the state this phase must not be built in.
- **[Phase 1](phase1_the_run_bag.md)** — supplies the bag lifecycle states and the rule that a manifest is regenerated with a tombstone when a payload file is replaced. This phase inherits that rule; it does not invent one under time pressure.
- ***Stand up the Temporal server*** — for requirement 1's recurrence only. It is a milestone of the [Temporal Integration](../temporal-integration/temporal-integration.md) component, tracked as a checkbox in [`sprint.md`](../sprint.md) § *Sprint: Temporal Integration*.
- **Not [Phase 6](phase6_cpi_reads_the_journal.md).** Retention makes the journal bounded; it does not make it readable. If Phase 6's sweep is uncomfortable at its journal size, that measurement is evidence for pulling this phase forward — which is a finding, not a reason Phase 6 waits.

---

## What this phase decides

### The snapshot is what makes deletion a bounded loss rather than an open one

A snapshot is a full materialization: every store in the test set, written into the journal as it stands at that moment, as one addressable event. After it exists, every journal event *before* it is redundant — a rebuild that starts at the snapshot and replays forward reaches the same result as one that starts at the beginning.

**That redundancy is the entire licence to delete anything**, and it is why the snapshot and the deletion cannot be separated into different phases. Rotation without a snapshot to stop at is not an incomplete feature; it is a data-loss bug wearing a feature's clothes, because after [Phase 4](phase4_rebuild_is_a_test.md) the journal is the only thing that can regenerate a store.

**Stated the way that decides the rest of this phase: a deletion behind a snapshot costs the ability to *replay from before that point*. It does not cost the state.** The stores still hold what they held; a rebuild still reaches the same result; what is gone is the intermediate history and the reasoning inside the deleted run folders.

**What a snapshot does not cover.** It records what stores held, not what the deleted runs said about how they got there. A run's transcript is not reconstructible from a snapshot of `candidates.md`, and it never will be. That is the accepted cost of any retention at all, stated here rather than discovered later: **rotating a run out loses the ability to diagnose that run, and keeps the ability to answer what the fleet currently knows.**

### One budget, and nothing is exempt from it — requirement 2

**The journal has one size limit: 1 GB by default, and it is a configuration value an operator changes without editing code.** Not a constant, not a figure compiled in, and not a pair of numbers that trade against each other.

**It governs the whole journal. There is no half kept forever and no reserved floor.**

> **This is a ruling and this section is where it is recorded, with its reasoning.** It replaces a rule that rotated the CLI transcript on a schedule and kept the authored text permanently. That rule is gone for two independent reasons, and either would be sufficient.
>
> **First: there is no requirement to keep any record forever, and the permanent half was a carve-out nobody asked for.** It rested on treating the authored record as irreplaceable. It is not — [Phase 4](phase4_rebuild_is_a_test.md) makes the stores rebuildable and the snapshot above makes the state survive the deletion of the folders behind it.
>
> **Second, and this is the reasoning that matters: a partial run record is worthless.** See below. The old rule produced precisely the partial record the new one forbids.
>
> **It is recorded in the plan rather than in a pull-request body because it has been ruled once before and was not written down** — which is a live instance of exactly the failure this component exists to prevent.

**The budget is not tight.** Measured on one `research_minor` cycle: authored output 39,772 bytes and CLI transcript 4,823,628 bytes, so a complete run is **4,863,400 bytes**. At that size, **1 GB holds about 205 complete runs**, and the fleet's *entire* 125-day, 175-run history to date would be about **851 MB** — under the default budget with room to spare.

```
python3 -c "a=39772; t=4823628; r=a+t; print(r, round(10**9/r,1), round(175*r/1e6,1))"
4863400 205.6 851.1
```

*(Both input figures are the synthesis's, measured 2026-08-12; the run count and date span are `state_passing` §4.4's timestamped lower bound, not a stable fact. The arithmetic above is this phase's, and it is re-derivable from the command beside it.)*

**⚠ What the budget does NOT bound, named so nobody reads it as a guarantee it is not:**

- **It is not an age limit.** A secret that reached a transcript rotates out when the journal fills, which is a delay of unknown length rather than a control. [Phase 3](phase3_the_emit_rule.md)'s capture-time filter and [Phase 1](phase1_the_run_bag.md)'s redaction event are the controls; this is not one.
- **It does not bound the content store** unless [Phase 2](phase2_content_store.md) requirement 7(a) ruled per-run. Under the root-level-shared shape, deleting bags reclaims nothing — see § *What is not built here*.
- **It does not bound object storage.** A bucket has its own lifecycle rules and its own cost model, and [Phase 7](phase7_s3_aggregation.md) must not inherit this number by default.
- **It does not protect a recent run from a burst.** With one number and no age floor, a pathological burst of runs can rotate out a folder from the same day. That is accepted rather than overlooked: the snapshot means the *state* survives, and adding an age floor would reintroduce the second number this ruling exists to remove.

### A partial run record is worthless — requirement 3

**Deletion is all-or-nothing per run, and the reasoning is not disk.**

A run whose transcript was rotated away but whose authored output remained would be a run you can *half*-read. Someone looking for what happened finds a folder, finds prose in it, and reads it as the record — when the half that says what the run actually did is gone. **Half-readable reads as coverage**, and coverage you do not have is worse than an absence you can see.

**So a run folder is the unit.** It is present, entire, or it is gone, entire, with a retention event saying so. There is no state in [Phase 1](phase1_the_run_bag.md)'s lifecycle table for a partially deleted bag, and that is deliberate: nothing is allowed to produce one.

**The trade is obvious once the budget is stated.** At 1 GB the journal holds roughly two hundred complete runs. Rotating the oldest whole ones out buys a bounded store and keeps every surviving record readable end to end.

### The cadence is derived from the budget, not ruled separately

**A snapshot's only purpose is to be the barrier a deletion stops at.** So it is written exactly when a deletion needs a newer one:

1. The retention pass runs and measures the journal against the budget.
2. If it is under budget, nothing happens.
3. If it is over, it removes whole run folders oldest-first — **stopping at the most recent snapshot.**
4. **If it is still over budget at that barrier, it writes a new snapshot and continues.**

**That is the whole of the cadence and there is no second number to rule.** A busy period produces snapshots more often because it produces deletions more often; a quiet one produces none, because none is needed. A cadence set independently of the budget would either write snapshots nobody deletes against or leave a deletion blocked at a stale barrier, and both are the failure the two-number version invited.

**What still needs a number is how often the *pass* runs**, and that is a scheduling parameter rather than a retention policy — it decides how far over budget the journal may drift between checks, not what is kept. Requirement 1 owns it and it is the half the Temporal gate reaches.

### The record of a deletion has to outlive what it deleted — requirement 6

Requirement 6's retention events, [Phase 3](phase3_the_emit_rule.md)'s gap events and [Phase 1](phase1_the_run_bag.md)'s redaction events all live in bags that a later oldest-first pass would remove — which would delete the explanation of a deletion, and the historical fact that the record ever had holes.

**They are folded into the snapshot.** Exempting them was the other available answer and it is not available any more: **nothing is exempt from the budget**, and an exemption list is a floor by another name. Folding them into the snapshot is strictly better anyway — the snapshot is the thing a rebuild starts from, so a deletion's explanation ends up in the one artifact every later read already consults.

**This is not bookkeeping.** Without it, the answer to *"why can I not find run X"* is indistinguishable from *"run X never happened"*, and those are very different facts. And [Phase 3](phase3_the_emit_rule.md)'s rule has no exception for the fleet's own maintenance: a retention pass changes what the record contains, which is the single most consequential kind of change anything makes to it, so it emits.

### Retention meets a gapped bag — requirement 7

[Phase 3](phase3_the_emit_rule.md) rules that a failed journal write is never silent: where nothing can be withheld, the failure appends a typed **gap event** and the bag is marked `incomplete`. That state has to survive this phase.

**Under whole-folder deletion the collision is smaller than it was, and the residue is worth naming.** A retention pass no longer trims a payload, so it no longer leaves a bag that looks short. What remains is the case where a bag is **`incomplete`** — it lost data to a disk-full error — and separately **`redacted`**, because a human replaced a payload file. Both leave a bag whose payload differs from what was first written, and collapsing them makes a defect indistinguishable from the system working.

**So `incomplete` and `redacted` are independent facts about a bag, not two values of one field.** A bag can be neither, either, or both, and the validator reports both. **A retention pass never clears `incomplete`** — and when it deletes such a bag, the gap events folded into the snapshot are what keep the historical fact that the record had a hole there.

### What is not built here

- **Any cross-machine retention.** A bucket has its own lifecycle rules and its own cost model. [Phase 7](phase7_s3_aggregation.md) owns that, and it must not inherit this phase's number by default — the local budget is bounded by one disk and a bucket is not.
- **Deleting the content store — and this gap is PLACED rather than named.** [Phase 2](phase2_content_store.md)'s cached bytes are referenced by checksum from potentially many bags, so deleting them needs a reachability pass. **Whether the gap exists at all is decided by [Phase 2](phase2_content_store.md) requirement 7(a)**: under the per-run shape, deleting a bag deletes its bytes and there is nothing to reclaim; under the root-level-shared shape, nothing reclaims anything and the store grows without bound *outside* the budget above. Phase 2 r7(a) states that choosing root-level shared creates the reclamation obligation, and this phase's checklist carries the conditional pass.
- **A retention rule for a store that Phase 4 could not rebuild.** Requirement 1 forbids snapshotting such a store as though it were covered. If any exist, they are listed in [Phase 4](phase4_rebuild_is_a_test.md) § *Stores not covered* and this phase's snapshot names them as out of coverage rather than including them silently.

---

## Implementation checklist

- [ ] Make the budget a configuration value with a documented default of 1 GB, and confirm by inspection that no code path carries a second retention number
- [ ] Build the recurring retention pass on top of [Phase 4](phase4_rebuild_is_a_test.md)'s one-off snapshot mechanism: measure against budget, delete whole folders oldest-first, stop at the last snapshot, write a new snapshot and continue if still over
- [ ] Specify and enforce that deletion is whole run folders only — **no code path removes a file from inside a bag for retention reasons** — with the refusal to cross a snapshot as a non-zero exit with a named reason
- [ ] Fold retention, gap and redaction events into the snapshot, and demonstrate that the explanation of a deletion survives a later deletion
- [ ] Keep `incomplete` and `redacted` independent, and confirm a bag carrying both reports both
- [ ] Emit a journal event per retention pass naming what was deleted, when, and under which snapshot
- [ ] **If [Phase 2](phase2_content_store.md) r7(a) ruled root-level shared:** build the reachability pass that reclaims content-store objects no retained bag references. If it ruled per-run, record that this is a no-op and why
- [ ] Demonstrate a dry-run refusing to cross the last snapshot, against a real journal, and record the command
- [ ] Run [Phase 4](phase4_rebuild_is_a_test.md)'s rebuild test on both sides of a real deletion and record both results
- [ ] Tests per the [Testing Standard](../../standards/testing/README.md): `unit/` for the refusal condition, the whole-folder rule, the snapshot-when-blocked step and the `incomplete`/`redacted` independence; `integration/` for a real over-budget → snapshot → delete → rebuild cycle
- [ ] Record measured journal size before and after one retention pass, with its denominator, in § *Measurement*

---

## Measurement

*(Populated when the phase runs. Every figure is produced by a command run against the tree and pasted with the command that produced it.)*

The figures this phase owns, each with a denominator:

- **Journal size before and after one retention pass**, with the number of folders removed — the only figure that says whether the retention rule is doing anything.
- **Rebuild wall-clock from the most recent snapshot versus from the beginning**, over the same store set. This is what the snapshot is *for*, and if the two are close the snapshots are being written more often than they need to be.
- **Measured bytes per complete run, against the 4,863,400-byte figure this doc derives**, with the run count as the denominator. That figure is what turns the budget into a number of runs, and if the real ratio differs materially the budget's practical depth differs with it.

---

## Notes and open items

- **The budget is the only knob and it is deliberately blunt.** It is a size, not an age and not a per-class policy, and the whole argument for that is § *A partial run record is worthless*. If a future need genuinely requires a second dimension, the thing to check first is whether it is really asking for an *age* limit — and if it is, it is asking for a control the budget was never claiming to be.
- **The content-store gap named above is the most likely thing to be forgotten.** It is out of scope here deliberately — a reachability pass over content-addressed objects is its own piece of work — but it means "the journal is bounded" is *narrower than it sounds* until [Phase 2](phase2_content_store.md) r7(a) is ruled, and anyone reading a bounded-journal claim after this phase should know which of the two shapes it was ruled into.

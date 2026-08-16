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

1. **(GATED — the only requirement here that needs the server.) A recurring retention pass runs on a cadence** and brings the journal under budget by the algorithm in § *The pass, stated as steps* below. A snapshot records the same store set [Phase 4](phase4_rebuild_is_a_test.md) tests against, and a store Phase 4 could not rebuild is not silently snapshotted as though it could be.
2. **(ungated) The budget is one configuration value with a documented default of 1 GB**, and it is measured over **everything under the journal root** — bags, the content store and the snapshot. **No half is exempt, no floor is reserved, and there is no second number.** § *What the budget is measured over* below.
3. **(ungated) Deletion is whole run folders, oldest first, until the journal is under budget** — **never a partial run, and never a bag that is not `sealed`.** § *A partial run record is worthless* and § *The pass, stated as steps*.
4. **(ungated) The pass has a stated terminal state and never loops.** It writes **at most one snapshot per pass**, and when it cannot reach budget with what it is permitted to delete it **stops, emits a typed `over-budget-unreclaimable` event naming what it could not reclaim, and exits non-zero.** § *The pass, stated as steps*.
5. **(ungated) A retention dry-run refuses to delete past the most recent snapshot**, demonstrated against a real journal — and the refusal is a non-zero exit with a named reason, not a warning.
6. **(ungated) The retention pass is a fleet-code path only.** It is not exposed to a child and is not invocable from a model-issued write, using [Phase 3](phase3_the_emit_rule.md) requirement 9's own distinction between the two. § *Who may invoke a deletion* below.
7. **(ungated) A rebuild from the most recent snapshot forward still passes [Phase 4](phase4_rebuild_is_a_test.md)'s test after a retention pass has run** — demonstrated by running that test on both sides of a real deletion.
8. **(ungated) A retention pass emits its own journal events** — what it deleted, when, and under which snapshot — and those events are **carried into the snapshot preserving their event class**, so that after the carrying bag is gone a redaction is still enumerable separately from a gap and from a retention deletion. § *The record of a deletion has to outlive what it deleted*.
9. **(ungated) A bag that is both incomplete and redacted stays distinguishable as both.** § *Retention meets a gapped bag* below.

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
- **It does not make every byte under the root *reclaimable*.** The budget is measured over the whole root (requirement 2), but whole-folder deletion only reclaims bags — so if [Phase 2](phase2_content_store.md) r7(a) rules root-level shared without its reachability pass, the pass measures bytes it cannot free and terminates at step 5 rather than reaching budget. That is the honest behaviour and it is why the reachability pass is a prerequisite.
- **It does not bound object storage.** A bucket has its own lifecycle rules and its own cost model, and [Phase 7](phase7_s3_aggregation.md) must not inherit this number by default.
- **It does not protect a recent run from a burst.** With one number and no age floor, a pathological burst of runs can rotate out a folder from the same day. That is accepted rather than overlooked: the snapshot means the *state* survives, and adding an age floor would reintroduce the second number this ruling exists to remove.

### A partial run record is worthless — requirement 3

**Deletion is all-or-nothing per run, and the reasoning is not disk.**

A run whose transcript was rotated away but whose authored output remained would be a run you can *half*-read. Someone looking for what happened finds a folder, finds prose in it, and reads it as the record — when the half that says what the run actually did is gone. **Half-readable reads as coverage**, and coverage you do not have is worse than an absence you can see.

**So a run folder is the unit.** It is present, entire, or it is gone, entire, with a retention event saying so. There is no state in [Phase 1](phase1_the_run_bag.md)'s lifecycle table for a partially deleted bag, and that is deliberate: nothing is allowed to produce one.

**The trade is obvious once the budget is stated.** At 1 GB the journal holds roughly two hundred complete runs. Rotating the oldest whole ones out buys a bounded store and keeps every surviving record readable end to end.

### What the budget is measured over — requirement 2

**Everything under the journal root: the bags, [Phase 2](phase2_content_store.md)'s content store, and the snapshot.** That is what *nothing is exempt* means, and stating it any other way would make the commitment false of its own text.

**It is stated this way rather than the convenient way, because the convenient way hides the case that breaks the pass.** Measuring over bags alone would make the budget easy to satisfy and would leave the content store — which sits under the same root and which whole-folder deletion cannot reclaim — growing outside any bound. **Measuring over the root means the pass can genuinely fail to reach budget**, and requirement 4 is the terminal state that failure needs.

**One consequence lands on [Phase 2](phase2_content_store.md) r7(a) and it is now a prerequisite rather than a note:** if that requirement rules the content store **root-level shared**, deleting bags reclaims none of its bytes, so **the reachability pass is a prerequisite of this phase**, not a conditional checklist item. If it rules per-run, deleting a bag deletes its bytes and there is nothing to reclaim.

### The pass, stated as steps — requirements 1, 3 and 4

**A snapshot's only purpose is to be the barrier a deletion stops at**, so it is written when a deletion needs a newer one rather than on a cadence of its own. The pass:

1. **Measure** the journal root against the budget. Under budget → stop, nothing happens.
2. **If no snapshot exists, write one.** Every rule below is expressed relative to *the most recent snapshot*, and a journal with none is the normal state before [Phase 4](phase4_rebuild_is_a_test.md)'s baseline snapshot has been taken.
3. **Delete whole `sealed` run folders, oldest first, stopping at the most recent snapshot.** **A bag that is not `sealed` is never deleted, regardless of age** — an `open` bag belongs to a run that may still be writing into it, and the pass runs concurrently with live runs by construction once it is scheduled.
4. **If still over budget at that barrier, write ONE new snapshot and continue — at most one snapshot per pass.** Advancing the barrier makes older sealed folders eligible that the previous barrier protected. **A pass that advances the barrier escalates on the same durable surface [Phase 3](phase3_the_emit_rule.md) case (d) uses**, because evicting runs the previous pass protected is a fact an operator should learn from something other than an absence.
5. **Terminal state.** If the journal is still over budget when nothing further may be deleted — no `sealed` bag remains outside the current barrier, or the residue is the content store or the snapshot itself — the pass **stops, emits a typed `over-budget-unreclaimable` event naming what it could not reclaim, and exits non-zero.** It does not write a second snapshot and it does not loop.

**That is the whole of the cadence, and there is no second number to rule.** A busy period produces snapshots more often because it produces deletions more often; a quiet one produces none. A cadence set independently of the budget would either write snapshots nobody deletes against or leave a deletion blocked at a stale barrier.

**⚠ Step 5 is the requirement most likely to be dropped as an edge case, and it is the one that keeps this phase from being a data-loss bug.** Without it the loop in steps 3–4 has no exit: each iteration writes a barrier at *now*, which reopens every folder the previous barrier protected, and a journal whose unreclaimable residue exceeds the budget gets deleted down to nothing while the pass keeps going. **The failure is silent and it is total.**

**What still needs a number is how often the *pass* runs**, and that is a scheduling parameter rather than a retention policy — it decides how far over budget the journal may drift between checks, not what is kept. Requirement 1 owns it and it is the half the Temporal gate reaches.

### Who may invoke a deletion — requirement 6

**The retention pass is fleet code, and it is not reachable from a child.** [Phase 3](phase3_the_emit_rule.md) requirement 9 already splits every write in this fleet into *fleet-code* and *model-issued*; deletion is fleet-code only, and the pass is not exposed on any surface a model-issued write can reach.

**This matters more under whole-folder deletion than it did under a transcript trim**, because one invocation is now strictly more destructive than the operation this bound was originally written against. It does **not** defend against a genuinely compromised run — [Phase 1](phase1_the_run_bag.md) § *The manifest is BagIt* already concedes that the record is writable by the very processes it is a record of, and that concession stands. What it buys is the difference between *a model tidied up* and *a model cannot reach the delete path at all*.

### The record of a deletion has to outlive what it deleted — requirement 6

Requirement 6's retention events, [Phase 3](phase3_the_emit_rule.md)'s gap events and [Phase 1](phase1_the_run_bag.md)'s redaction events all live in bags that a later oldest-first pass would remove — which would delete the explanation of a deletion, and the historical fact that the record ever had holes.

**They are carried into the snapshot.** Exempting them was the other available answer and it is not available any more: **nothing is exempt from the budget**, and an exemption list is a floor by another name. Carrying them into the snapshot is strictly better anyway — the snapshot is the thing a rebuild starts from, so a deletion's explanation ends up in the one artifact every later read already consults.

**Three properties the carry must have, because a naive carry destroys what it is meant to preserve:**

- **The event class survives.** [Phase 1](phase1_the_run_bag.md) spends two sections establishing that a redaction must never be indistinguishable from a gap or from housekeeping. A carry that flattens the three into one section satisfies requirement 8's headline and destroys that distinction at exactly the moment the original evidence is gone. **Carried events keep their class, and a redaction stays enumerable on its own.**
- **The originating `run_id` survives**, so a gap can be counted once. [Phase 4](phase4_rebuild_is_a_test.md) r7 reports gapped bags against bags replayed and [Phase 6](phase6_cpi_reads_the_journal.md) r6 carries that number outward; without the id, a gap is counted from the snapshot *and* from its bag while the bag survives, and afterwards the numerator persists while the denominator shrinks. **Counting is dedupe-on-`run_id`, and the denominator is bags replayed plus bags rotated out behind the snapshot.**
- **The carry compacts rather than accumulates.** Snapshot N carries snapshot N−1's set, and **only the most recent snapshot is retained** — writing a new one carries the previous one's events forward in compacted form (class, count and `run_id`s rather than verbatim payloads) and then removes it. Without that, the snapshot is a permanently-growing artifact inside a budget that claims nothing is exempt, which reintroduces the permanent half this ruling removed.

**This is not bookkeeping.** Without it, the answer to *"why can I not find run X"* is indistinguishable from *"run X never happened"*, and those are very different facts. And [Phase 3](phase3_the_emit_rule.md)'s rule has no exception for the fleet's own maintenance: a retention pass changes what the record contains, which is the single most consequential kind of change anything makes to it, so it emits.

### Retention meets a gapped bag — requirement 7

[Phase 3](phase3_the_emit_rule.md) rules that a failed journal write is never silent: where nothing can be withheld, the failure appends a typed **gap event** and the bag is marked `incomplete`. That state has to survive this phase.

**Under whole-folder deletion the collision is smaller than it was, and the residue is worth naming.** A retention pass no longer trims a payload, so it no longer leaves a bag that looks short. What remains is the case where a bag is **`incomplete`** — it lost data to a disk-full error — and separately **`redacted`**, because a human replaced a payload file. Both leave a bag whose payload differs from what was first written, and collapsing them makes a defect indistinguishable from the system working.

**So `incomplete` and `redacted` are independent flags on a bag, not values of its lifecycle field** ([Phase 1](phase1_the_run_bag.md) r8, which is the single writer for the validator's output contract). A bag can carry neither, either, or both, and the validator always reports all three fields. **A retention pass never clears `incomplete`** — and when it deletes such a bag, the gap events folded into the snapshot are what keep the historical fact that the record had a hole there.

### What is not built here

- **Any cross-machine retention.** A bucket has its own lifecycle rules and its own cost model. [Phase 7](phase7_s3_aggregation.md) owns that, and it must not inherit this phase's number by default — the local budget is bounded by one disk and a bucket is not.
- **A reclamation pass for a root-level-shared content store is built HERE if [Phase 2](phase2_content_store.md) r7(a) ruled that shape, and it is a prerequisite rather than a conditional extra** (§ *What the budget is measured over*). It is listed under *not built here* only in the sense that this phase does not re-litigate r7(a)'s ruling.
- **A retention rule for a store that Phase 4 could not rebuild.** Requirement 1 forbids snapshotting such a store as though it were covered. If any exist, they are listed in [Phase 4](phase4_rebuild_is_a_test.md) § *Stores not covered* and this phase's snapshot names them as out of coverage rather than including them silently.

---

## Implementation checklist

- [ ] Make the budget a configuration value with a documented default of 1 GB, and confirm by inspection that no code path carries a second retention number
- [ ] Build the recurring retention pass on top of [Phase 4](phase4_rebuild_is_a_test.md)'s one-off snapshot mechanism, exactly as § *The pass, stated as steps* states it — including step 2's write-a-snapshot-if-none-exists and step 5's terminal state
- [ ] Specify and enforce that deletion is whole run folders only — **no code path removes a file from inside a bag for retention reasons** — with the refusal to cross a snapshot as a non-zero exit with a named reason
- [ ] Carry retention, gap and redaction events into the snapshot **preserving event class and originating `run_id`**, compact rather than accumulate, retain only the most recent snapshot, and demonstrate that a redaction is still enumerable separately after the bag that carried it is gone
- [ ] Implement the terminal state (requirement 4): at most one snapshot per pass, and an `over-budget-unreclaimable` event plus a non-zero exit when budget cannot be reached
- [ ] Never delete a bag that is not `sealed`, and demonstrate a retention pass running concurrently with a live run that leaves the live bag intact
- [ ] Confirm by inspection that the retention path is fleet-code only and is not reachable from any model-issued write (requirement 6)
- [ ] Keep `incomplete` and `redacted` independent, and confirm a bag carrying both reports both
- [ ] Emit a journal event per retention pass naming what was deleted, when, and under which snapshot
- [ ] **If [Phase 2](phase2_content_store.md) r7(a) ruled root-level shared:** build the reachability pass that reclaims content-store objects no retained bag references. If it ruled per-run, record that this is a no-op and why
- [ ] Demonstrate a dry-run refusing to cross the last snapshot, against a real journal, and record the command
- [ ] Run [Phase 4](phase4_rebuild_is_a_test.md)'s rebuild test on both sides of a real deletion and record both results
- [ ] Tests per the [Testing Standard](../../standards/testing/README.md): `unit/` for the refusal condition, the whole-folder rule, the no-snapshot cold start, the unreclaimable terminal state, the `sealed`-only rule and the `incomplete`/`redacted` independence; `integration/` for a real over-budget → snapshot → delete → rebuild cycle, and one exercising the pass concurrently with a live run
- [ ] **Bring `install.sh` and the operator-facing footprint documentation up to date with the journal root.** As of [Phase 1](phase1_the_run_bag.md) (PR #99) every non-dry-run dispatch creates `~/.local/state/claude-dot-files/journal/<run_id>/` on demand, so **nothing is broken today** — but `install.sh` neither creates nor removes it, and an operator's mental model of *"what this repo puts on my machine"* is the symlink list in [`CLAUDE.md`](../../../CLAUDE.md), which this path sits outside of. It becomes operationally interesting **here**, at retention: this is the phase that decides what deletes the directory, what a budget change means for an operator who has never seen the path, and whether uninstalling should leave a journal behind (it should — it is the record, not the tool). Until then it is 16 KiB per run; from [Phase 3](phase3_the_emit_rule.md) it is ~4.9 MB per run against a 1 GB budget. *(Placed here rather than filed as an issue because its trigger is this phase, not a date: it has no done-state until retention exists. Surfaced by `review-pr` on PR #99; the live-at-merge half — naming the path in [`docs/guide/operations.md`](../../guide/operations.md) so it is not undocumented state — was done in that PR.)*
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
- **The content-store reclamation pass is the most likely thing to be forgotten, which is why requirement 2 makes it a prerequisite rather than a note.** Under the root-level-shared shape it is a real piece of work — a reachability pass over content-addressed objects — and without it this phase measures bytes it cannot free and terminates at step 5 every time. Anyone reading a bounded-journal claim after this phase should check which shape [Phase 2](phase2_content_store.md) r7(a) was ruled into.

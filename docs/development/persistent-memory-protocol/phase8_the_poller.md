# Phase 8 — The poller

**Component:** [Persistent Memory Protocol](roadmap.md) · **Status:** not started · **Gate:** Temporal schedules

## What this phase does

Every other phase in this component is about *recording* what happened. This one is about *acting* on it without a human pressing anything.

Today, work that is ready to be picked up sits in a table marked `status: open` and waits for a person to notice. The information is already there and already machine-readable; what is missing is something that looks at it on a timer and starts the run. This phase builds that: a scheduled workflow that reads a store, finds work marked as needing attention, and starts a child.

**Nothing new is invented on the memory side.** No new surface, no new marker, no new "queue" table. `candidates.md`'s `status: open` column already is the marker, and the [memory model](../../guide/memory-model.md) §1 already makes such a marker a required property of every durable record in this fleet. Creating another one would mean two things to keep in sync, and the fleet has already measured what happens then.

**Terms used here.** A **journal** is the whole record: one folder per run, never edited after the run ends. A **store** is any place other than the journal that a run writes to — a markdown table, a pull-request comment, an issue. A **to-do bit** is a machine-readable flag on a record saying whether it still needs something; in this fleet's file surfaces it is a `status:` column. A **cue** is a to-do bit that has fired — a specific record that needs a specific run. An **edge** is one machine running this fleet.

## Why this phase waits, and why it is last

**The gate is Temporal schedules** — the same server as [Phase 5](phase5_snapshots_then_retention.md). A poller is a scheduled workflow by definition: something has to run it on a cadence with no process sitting resident, and that is what a schedule is.

**A second, softer gate is a journal with a retention rule.** A poller that starts children reads state repeatedly and forever, and doing that against an unbounded and growing tree is how a cheap read becomes an expensive one without anyone noticing. [Phase 5](phase5_snapshots_then_retention.md) is what bounds it.

**It is last because it is the only phase that makes the fleet act rather than remember**, and acting on a record whose completeness is unproven is worse than not acting. [Phase 4](phase4_rebuild_is_a_test.md) is what makes the record's completeness a test rather than a claim; a poller built before it would be dispatching work off a record nobody had checked.

*(This phase was split out of [Phase 6](phase6_cpi_reads_the_journal.md) at review. At draft they were one phase, gated on the Temporal server — which would have put this component's **only consumer** behind a server nobody has stood up, for four phases of producers. Only the poller needs a scheduler; reading needs a journal. The split is what stops this plan reproducing the failure it cites [MMF Phase 6](../memory-management-framework/phase6_read_what_it_writes.md) for.)*

---

## Requirements for completion

1. **A scheduled workflow reads a store's to-do bit and starts a child with no human trigger**, demonstrated end-to-end on one real cue.
2. **The cue is read from an existing surface. No new cue surface is created**, and if the build finds it needs one, that is a finding about the existing surface rather than a licence to add another.
3. **A cue that fires twice starts one child, not two.** § *Firing once* below.
4. **The poller reads the store, not the journal**, and this doc says why. § *Why the poller reads the store*.
5. **A cue that a run failed to complete is still a cue**, and does not silently vanish or silently repeat forever. § *When the child fails*.

---

## Dependencies

- **[Temporal Integration](../temporal-integration/temporal-integration.md) → *Stand up the Temporal server*** — hard. Temporal schedules are the mechanism.
- **[Phase 5](phase5_snapshots_then_retention.md)** — soft but real. See above.
- **[Phase 4](phase4_rebuild_is_a_test.md)** — hard in the sense that matters: this phase starts work on the strength of what a record says, and Phase 4 is what makes the record trustworthy enough for that.
- **[`memory-model.md`](../../guide/memory-model.md)** — supplies the to-do bit as a stated property and the per-surface consumer map requirement 2 checks against. It is [MMF Phase 2](../memory-management-framework/phase2_kind1_framework.md)'s deliverable and is complete.

---

## What this phase decides

### Why the poller reads the store, not the journal — requirement 4

This looks backwards for a component whose whole thesis is *"every question starts in the journal"*, so the reason has to be stated rather than assumed.

**The journal holds history. The store holds current state.** A poller's question is *"what needs doing right now?"* — which is a question about the present. Answering it from the journal means replaying the record forward to reconstruct current state on every tick, which is both slower and a second implementation of something [Phase 4](phase4_rebuild_is_a_test.md) already built once.

**And the store is safe to read for this purpose precisely because of Phase 4.** After it, the store is a thing the journal regenerates — so reading the store is reading a derived view that something else keeps honest, not reading an unaudited second source of truth. **Before Phase 4 that would not be true**, and it is the second reason this phase sits after it.

*(The one thing this does mean: a cue whose emit was lost is invisible to the poller, exactly as it is invisible to the store. That is not a new failure mode introduced here — it is [Phase 3](phase3_the_emit_rule.md)'s gap rule doing what it says, and a gapped bag is reported as gapped.)*

### Firing once — requirement 3

A scheduled workflow runs on a cadence and a cue stays open until something closes it, so **the default behaviour of the obvious implementation is to start a child on every tick until the work is done.** That is not a subtle bug; it is what the naive version does on its second tick.

The fleet already has the rule this needs: the [Temporal Standard](../../standards/temporal/temporal_standard.md) §7 requires every activity to be idempotent, because activities execute at least once. **Applied here it means the identity of a dispatch is derived from the cue rather than from the tick** — the same cue produces the same dispatch identity, and starting it twice is a no-op rather than a second run.

**This is the same discipline [Phase 3](phase3_the_emit_rule.md) requirement 7 applies to events**, one level up: an event carries a deterministic identity so a retried activity cannot double-append, and a dispatch carries one so a repeated tick cannot double-start. Stating the connection is worth more than restating the mechanism — if the two are implemented with different notions of identity, a reader of either will be surprised by the other.

### When the child fails — requirement 5

A cue that starts a child which then fails is the case that decides whether this phase is useful or merely dangerous, and there are exactly two bad answers.

- **Retry forever.** The cue never closes, so the poller restarts it every tick. A cue that fails for a permanent reason — a malformed row, a missing dependency — becomes an infinite dispatch loop that costs real money and produces nothing.
- **Close it silently.** The work vanishes. The record says the cue was handled and nothing happened, which is worse than never having polled at all because it is invisible.

**The answer is neither, and it follows from this component's own rule that a failure is never silent** ([Phase 3](phase3_the_emit_rule.md)): a failed dispatch emits, the cue stays open, and **repeated failure against one cue is itself a condition someone is told about** rather than a loop nobody watches. What the escalation surface is — a bounded attempt count, a flag on the row, an entry on the standup tracker — is a build-time choice; that there is one is a requirement.

### What this phase does not build

- **A general work queue.** Requirement 2 is deliberately narrow: read an existing to-do bit. The moment this phase starts designing a queue with priorities, dependencies and a scheduler of its own, it has stopped being a poller and started being a second orchestrator beside Temporal.
- **Cross-machine polling.** One machine polls its own stores. Whether a machine may start work on the strength of another machine's record is the ingress ruling, and it belongs to [Phase 7](phase7_s3_aggregation.md).
- **Any change to who may set a to-do bit.** `direction.md`'s `status` is the operator's alone and stays that way; this phase reads bits, it does not write them.

---

## Implementation checklist

- [ ] Enumerate which existing surfaces carry a to-do bit a poller could read, from [`memory-model.md`](../../guide/memory-model.md) §2, and pick the one this phase demonstrates against
- [ ] Build the scheduled workflow: read the store, find open cues, start a child
- [ ] Derive dispatch identity from the cue, and demonstrate that a repeated tick against one open cue starts nothing new
- [ ] Build the failure path: emit, leave the cue open, escalate on repeated failure — and name the escalation surface
- [ ] Demonstrate end-to-end on one real cue, from `status: open` to a child that ran, and record the commands
- [ ] Confirm no new cue surface was created, and record any pressure to create one as a finding about the existing surface
- [ ] Tests per the [Testing Standard](../../standards/testing/README.md): `unit/` for cue selection, dispatch identity and the failure path; `integration/` for one real scheduled dispatch
- [ ] Record ticks-to-dispatch and duplicate-start count, with denominators, in § *Measurement*

---

## Measurement

*(Populated when the phase runs. Figures come from commands run against the tree and are pasted with the command.)*

Two figures with denominators:

- **Duplicate starts against total ticks over open cues.** Requirement 3's whole content. It should be zero, and a zero with a small denominator is not evidence — the denominator is the number that makes this measurement mean anything.
- **Time from a cue opening to a child starting**, against the schedule interval. If they are not close, something other than the schedule is the delay and it is worth knowing what.

---

## Notes and open items

- **This phase is the first time the fleet acts without a human in the loop on the memory path**, and that is worth saying plainly rather than burying in a requirement. Everything before it records; this one dispatches. The safeguards that matter are requirement 3 (not twice) and requirement 5 (not silently, and not forever), and if either is weakened during the build, that is a change to what this phase is — not a scope trim.
- **Requirement 2 is likely to come under pressure.** The temptation when a surface turns out to be awkward to poll is to add a purpose-built one, and the reason not to is the same reason this fleet keeps no state files: a second thing to keep in sync is a second thing to be wrong. If the existing surface genuinely cannot express a cue, that is a real finding — about the surface, and it goes back to whoever owns it.

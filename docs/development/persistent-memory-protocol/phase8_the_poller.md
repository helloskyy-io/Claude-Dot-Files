# Phase 8 — The poller

**Component:** [Persistent Memory Protocol](roadmap.md) · **Status:** not started · **Gate:** Temporal schedules

## What this phase does

Every other phase in this component is about *recording* what happened. This one is about *acting* on it without a human pressing anything.

Today, work that is ready to be picked up sits in a table marked `status: open` and waits for a person to notice. The information is already there and already machine-readable; what is missing is something that looks at it on a timer and starts the run. This phase builds that: a scheduled workflow that reads a store, finds work marked as needing attention, and starts a child.

**Nothing new is invented on the memory side.** No new surface, no new marker, no new "queue" table. `candidates.md`'s `status: open` column already is the marker, and a to-do bit is a required property of every [working record](../../guide/memory-model.md) in this fleet. Creating another one would mean two things to keep in sync, and the fleet has already measured what happens then.

**Terms used here.** A **journal** is the whole record: one folder per run, never edited after the run ends. A **store** is any place other than the journal that a run writes to — a markdown table, a pull-request comment, an issue. A **to-do bit** is a machine-readable flag on a record saying whether it still needs something; in this fleet's file surfaces it is a `status:` column. A **cue** is a to-do bit that has fired — a specific record that needs a specific run. An **edge** is one machine running this fleet.

## Why this phase waits, and why it is last

**The gate is Temporal schedules** — the same server as [Phase 5](phase5_snapshots_then_retention.md). A poller is a scheduled workflow by definition: something has to run it on a cadence with no process sitting resident, and that is what a schedule is.

**A second, softer gate is a journal with a retention rule.** A poller that starts children reads state repeatedly and forever, and doing that against an unbounded and growing tree is how a cheap read becomes an expensive one without anyone noticing. [Phase 5](phase5_snapshots_then_retention.md)'s storage budget is what bounds it.

**It is last because it is the only phase that makes the fleet act rather than remember**, and acting on a record whose completeness is unproven is worse than not acting. [Phase 4](phase4_rebuild_is_a_test.md) is what makes the record's completeness a test rather than a claim; a poller built before it would be dispatching work off a record nobody had checked.

*(This phase and [Phase 6](phase6_cpi_reads_the_journal.md) are deliberately separate, and the reason is worth one clause so nobody merges them again: bundled, they would put this component's **only consumer** behind a server nobody has stood up, for four phases of producers. Only the poller needs a scheduler; reading needs a journal.)*

---

## Requirements for completion

1. **A scheduled workflow reads a store's to-do bit and starts a child with no human trigger**, demonstrated end-to-end on one real cue.
2. **The cue is read from an existing surface. No new cue surface is created**, and if the build finds it needs one, that is a finding about the existing surface rather than a licence to add another.
3. **A cue that fires twice starts one child, not two**, and the fact that it already fired lives somewhere durable. § *Firing once* below.
4. **The poller reads the store, not the journal**, and this doc says why. § *Why the poller reads the store*.
5. **A cue that a run failed to complete is still a cue**, and does not silently vanish or silently repeat forever. § *When the child fails*. **If the escalation surface is a store, that write goes through [Phase 3](phase3_the_emit_rule.md)'s emit path like any other.**
6. **The cue→dispatch mapping is a fixed code-side table, and row content is data.** § *What a cue may start* below. This is the requirement that bounds what an unattended dispatcher can be made to do.
7. **The poller acts only on cues of local origin.** § *What a cue may start*. Today every cue is local and this holds trivially — **and the filter is built anyway rather than skipped**, because the day [Phase 7](phase7_s3_aggregation.md) lands is the day it stops holding trivially, and nothing would prompt a re-review then.

---

## Dependencies

- ***Stand up the Temporal server*** — hard; Temporal schedules are the mechanism. It is a milestone of the [Temporal Integration](../temporal-integration/temporal-integration.md) component, tracked as a checkbox in [`sprint.md`](../sprint.md) § *Sprint: Temporal Integration*.
- **[Phase 3](phase3_the_emit_rule.md)** — hard, and it was missing from this list until review. Requirement 5's failure path *emits*, and requirement 7's provenance class is the field requirement 7 here reads. Neither exists without it.
- **[Phase 5](phase5_snapshots_then_retention.md)** — soft but real. See above.
- **[Phase 4](phase4_rebuild_is_a_test.md)** — hard in the sense that matters: this phase starts work on the strength of what a record says, and Phase 4 is what makes the record trustworthy enough for that.
- **[`memory-model.md`](../../guide/memory-model.md)** — supplies the to-do bit as a stated property of the working record, and the per-surface consumer map requirement 2 checks against. Complete, so it does not block.

---

## What this phase decides

### Why the poller reads the store, not the journal — requirement 4

This looks backwards for a component whose whole thesis is *"every question starts in the journal"*, so the reason has to be stated rather than assumed.

**The journal holds history. The store holds current state.** A poller's question is *"what needs doing right now?"* — which is a question about the present. Answering it from the journal means replaying the record forward to reconstruct current state on every tick, which is both slower and a second implementation of something [Phase 4](phase4_rebuild_is_a_test.md) already built once.

**And Phase 4 is what makes the store safe to read for this purpose — up to a point that has to be stated.** After it, the store is a derived view that something else keeps honest rather than an unaudited second source of truth, and that is the second reason this phase sits after it. **But a derived view is exactly as trustworthy as what it derives from** — [Phase 4](phase4_rebuild_is_a_test.md) requirement 9 says so in as many words — so after [Phase 7](phase7_s3_aggregation.md) the journal behind this store may include folders that arrived from another machine. **Read the reassurance the wrong way round and it inverts:** *the store is safe because Phase 4 made it a rebuild* is true of accuracy and says nothing about origin. That is what requirement 7 above is for.

*(The one thing this does mean: a cue whose emit was lost is invisible to the poller, exactly as it is invisible to the store. That is not a new failure mode introduced here — it is [Phase 3](phase3_the_emit_rule.md)'s gap rule doing what it says, and a gapped bag is reported as gapped.)*

### What a cue may start — requirements 6 and 7

**This is the first thing in the fleet that starts work with no human in the loop, and it starts it from a row in a markdown table.** That sentence is the whole reason this section exists. Everything before this phase records; this one dispatches, under the same bypassed-permissions posture every other run uses.

**So two things are bounded here, in code, and neither is a build-time preference.**

**(a) The workflow is chosen by the surface, never by the row.** The mapping from cue to dispatch is a fixed table in code: *this surface's open rows start this workflow*. Row content is passed as **data** — never as workflow selection, never as an unquoted fragment of a prompt. **A poller that decides what to run by reading what a row says is a remote-code-execution path wearing a scheduler's clothes**, and it would be one the moment [Phase 7](phase7_s3_aggregation.md) makes a row's ultimate origin a machine other than this one.

**(b) The poller acts only on cues of local origin.** Trace the chain the plan already contains: a party with write access to a shared bucket lands a record → [Phase 4](phase4_rebuild_is_a_test.md)'s replay applies it → a row appears in `candidates.md` → this phase reads that row and starts a run. **Every link exists in the design; none of them is hypothetical**, and the only one that does not exist *today* is the shared bucket. And the [heartbeat pollution paper](https://arxiv.org/pdf/2603.23064) measured exactly the entry point — pollution reaching durable memory at rates up to 91%, **with prompt injection not required.**

**The field that makes (b) checkable is not this phase's to build.** [Phase 3](phase3_the_emit_rule.md) requirement 7 puts a provenance class on every event, and [Phase 4](phase4_rebuild_is_a_test.md) requirement 9 requires it to survive the rebuild — because a rebuilt row with no origin column is a row nobody can filter. **Without that chain, requirement 7 here is unimplementable**, which is why Phase 3 and Phase 4 are hard dependencies and why this is stated rather than left to the build.

**⚠ And requirement 7 is built even while it holds trivially, for a reason the rollout order makes concrete.** This phase is listed *ahead* of Phase 7 and is gated only on Temporal schedules, so it may well ship while every cue is local and every origin check is a no-op. **Shipping it without the filter means silently acquiring a remote-triggered dispatch path the day Phase 7 lands, with nothing prompting a re-review.** So the filter is written, tested against a synthetic non-local origin, and recorded as a no-op against the live corpus — which is a different and much cheaper thing than adding it later.

### Firing once — requirement 3

A scheduled workflow runs on a cadence and a cue stays open until something closes it, so **the default behaviour of the obvious implementation is to start a child on every tick until the work is done.** That is not a subtle bug; it is what the naive version does on its second tick.

The fleet already has the rule this needs: the [Temporal Standard](../../standards/temporal/temporal_standard.md) §7.1 requires every activity to be idempotent, because activities execute at least once. **Applied here it means the identity of a dispatch is derived from the cue rather than from the tick** — the same cue produces the same dispatch identity, and starting it twice is a no-op rather than a second run.

**This is the same discipline [Phase 3](phase3_the_emit_rule.md) requirement 7 applies to events**, one level up: an event carries a deterministic identity so a retried activity cannot double-append, and a dispatch carries one so a repeated tick cannot double-start. Stating the connection is worth more than restating the mechanism — if the two are implemented with different notions of identity, a reader of either will be surprised by the other.

**⚠ And the "already fired" fact needs a durable home, which is why requirement 3 names one.** The obvious mechanism is a Temporal workflow id — and this component's own § *What is deliberately not built* rules Temporal's store *"an execution log with a time limit, not a durable record."* **So a workflow id alone makes requirement 3 true only inside Temporal's retention window**, and a cue still open after it re-fires. The marker goes somewhere that outlives both Temporal retention and [Phase 5](phase5_snapshots_then_retention.md)'s journal retention: a journal event, or a field on the row the poller already reads.

**Identity derivation needs one more decision, and both of the obvious answers are wrong in opposite directions.** A content hash re-fires on a benign edit to the row; a bare row id suppresses genuinely new work if an id is ever reused. Naming which fields the identity is derived from — and why an edit to the others does not re-fire — is part of this requirement rather than a build detail.

### When the child fails — requirement 5

A cue that starts a child which then fails is the case that decides whether this phase is useful or merely dangerous, and there are exactly two bad answers.

- **Retry forever.** The cue never closes, so the poller restarts it every tick. A cue that fails for a permanent reason — a malformed row, a missing dependency — becomes an infinite dispatch loop that costs real money and produces nothing.
- **Close it silently.** The work vanishes. The record says the cue was handled and nothing happened, which is worse than never having polled at all because it is invisible.

**The answer is neither, and it follows from this component's own rule that a failure is never silent** ([Phase 3](phase3_the_emit_rule.md)): a failed dispatch emits, the cue stays open, and **repeated failure against one cue is itself a condition someone is told about** rather than a loop nobody watches. What the escalation surface is — a bounded attempt count, a flag on the row, an entry on the standup tracker — is a build-time choice; that there is one is a requirement.

### What this phase does not build

- **A general work queue.** Requirement 2 is deliberately narrow: read an existing to-do bit. The moment this phase starts designing a queue with priorities, dependencies and a scheduler of its own, it has stopped being a poller and started being a second orchestrator beside Temporal.
- **Cross-machine polling.** One machine polls its own stores. Whether a machine may start work on the strength of another machine's record is a question for whoever builds a shared bucket, and [Phase 7](phase7_s3_aggregation.md) § *Where a shared bucket would change things* is where it is written down.
- **Any change to who may set a to-do bit.** `direction.md`'s `status` is the operator's alone and stays that way; this phase reads bits, it does not write them. **That read-only posture is about to-do bits specifically and not about every write this phase makes** — requirement 5's failure record is a write, and it emits like any other.

---

## Implementation checklist

- [ ] Enumerate which existing surfaces carry a to-do bit a poller could read, from [`memory-model.md`](../../guide/memory-model.md) §2, and pick the one this phase demonstrates against
- [ ] Build the scheduled workflow: read the store, find open cues, start a child
- [ ] Build the cue→dispatch table in code: workflow chosen by surface, row content passed as data only
- [ ] Filter cues by origin, reading the provenance the rebuild carried forward ([Phase 4](phase4_rebuild_is_a_test.md) r9) — **build and test it against a synthetic non-local origin even when the live corpus makes it a no-op**, and record that it was a no-op rather than skipping it
- [ ] Derive dispatch identity from named fields of the cue, put the already-fired marker somewhere that outlives Temporal retention, and demonstrate that a repeated tick against one open cue starts nothing new
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

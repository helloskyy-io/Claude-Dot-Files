# Phase 3 — The emit rule: every write to any store also emits to the journal

**Component:** [Persistent Memory Protocol](roadmap.md) · **Status:** not started · **Gate:** Phase 1

This is the core rule of the component, and it is the operator's. A run writes wherever it needs to, in whatever format that surface wants. **If any store gets it, the journal gets it, verbatim.**

**The design test, in the operator's words, and every proposal to leave something out is checked against this sentence:**

> *"If I have a question it always starts in the journal. I rarely have to go to another source, because I know if I do it is just duplicated info from the journal anyway."*

---

## Requirements for completion

1. **Every write path to every store emits a journal event** carrying the authored content **verbatim**, with the destination store as a field.
2. **The journal is identical regardless of destination.** git, SQLite, a GitHub object, an MQTT topic on an edge with no repo — the destination is a field, not a format.
3. **The event envelope is modality-neutral** and extends [MMF Phase 3](../memory-management-framework/phase3_typed_exit_record.md)'s typed exit record rather than inventing a second contract.
4. **Every emitted item records which input item produced it**, so a fan-out round can be traced output-to-input.
5. **Every event carries a stable `edge_id` that never rotates.** The API key authenticates and *maps to* it; the key is never the identifier.
6. **Every event carries a schema version** and no written event is ever mutated.
7. **The write-path inventory is complete and enumerated in this doc** — a list of every surface the fleet writes to, each with its emit, so a reviewer can check coverage against something rather than take it on trust.

**Requirement 7 is the honest half of requirement 1.** "Every write path" is unverifiable as stated; a named list is verifiable, and [Phase 4](phase4_rebuild_is_a_test.md) is what keeps the list true after this phase closes.

---

## Dependencies

- **[Phase 1](phase1_the_run_bag.md)** — the bag is where events land. Hard dependency.
- **[MMF Phase 3](../memory-management-framework/phase3_typed_exit_record.md)** — supplies the typed exit record this envelope extends. **Complete**, so it does not block.
- **[Phase 2](phase2_content_store.md)** — not a dependency. Events reference artifacts by hash where a content store exists and by SHA/URL where it does not; the emit rule does not wait on the store.

---

## What this phase decides

### Completeness is absolute — prose in, code out

**Everything a run authors goes in:** the PR body, every reflection and decision-log comment, the review verdict, the triage, the direction, the approval, the re-run count, the PR number and repo, issues, candidate rows. Anything on any surface.

**The one exclusion is the code diff, and it is excluded for a stated reason rather than to save space: git is already a better store for it.** The journal carries the commit SHA and you go get the diff. That is [Phase 2](phase2_content_store.md)'s by-reference rule applied to the record itself.

**The line is one question: does a better durable store already exist for this artifact type?** For code it does. For the prose a run writes into GitHub it emphatically does not — comments are editable, deletable, unversioned, hosted by a service, **and they are where the reasoning lives.**

**The volume objection is measured, and it does not survive.** The instinct is to fear the byte count. For one full `research_minor` cycle, **all authored text — PR body plus every comment — was 39,772 bytes.** At that rate the authored record for the entire 175-run history is roughly **7 MB**. **The completeness rule costs almost nothing.** The volume in this system lives entirely in the CLI transcript, which is also in the journal and is governed separately by [Phase 5](roadmap.md#phase-5--snapshots-then-retention-gated-temporal-server)'s split retention.

### The destination is a field, not a format

**The journal is identical whether the run wrote into git, a GitHub object, a SQLite file, or an MQTT topic on an edge with no repo.**

That property is not stylistic. It is what makes the record portable across edges, and it is what [Phase 7](roadmap.md#phase-7--s3-aggregation-local-write-first-gated-a-second-edge-and-a-classification-ruling) depends on: a second edge of any type sources the same data from the protocol rather than from a repo. **Git stays for the edge we are building now**, because that edge's memory *is* versioned with code, reviewed in PRs, and travels with a clone — but git is that edge's binding, not the protocol's. Each edge reads and writes whatever surface it needs; **the truth is always the centralized output.** A surface is a local convenience; the journal is the record.

**Why not repo-per-edge.** [`state_passing`](research/raw/state_passing_between_workflow_children.md) established that identity compatibility is not integration — repos without a sync path are isolated memories that *look* joined, which is worse than obviously separate ones. And an edge like Home Assistant has no codebase to version. **It has runs.**

### Stores stay plural; the record is what gets consolidated

Two different things get merged in discussion, and separating them is what makes the rest tractable:

- **The journal** — append-only, immutable, never edited, joined by run id. One location.
- **The working stores** — `candidates.md`, `direction.md`, phase docs, GitHub objects. Mutable, curated, each with its own lifecycle.

**This phase consolidates the record and touches no store's lifecycle.** `state_passing` §4.2 found all six surveyed systems run multiple channels deliberately, each with a selection rule attached — Temporal ships `memo` and then documents that it *"shouldn't store data that's critical to the execution of a Workflow."* **Consolidation is not what mature systems do.**

And our own two file surfaces have opposite requirements: `candidates.md` never deletes a row by design; `direction.md` rotates a ruled row at 90 days. **No single retention or merge policy can serve both**, so collapsing them destroys one of them.

### One typed return per step, modality-neutral

`bernstein`'s typed activity boundary is *"the one contract a non-coding modality — research, browser/computer-use, data, ops — participates through as a replayable step"*, and *"every activity returns an artifact plus the hashes needed to replay it."* Every modality returns an `ActivityResult` carrying `kind`, `artifact`, `artifact_hash`, `evidence_set_hash`, `terminal_state`, `reason_code`.

**We take the shape close to as-is, and the reason it transfers is checkable rather than assumed.** The lesson worth keeping separately: *take a mechanism with its reason, then check the reason still holds here.* bernstein's reason is modality-neutrality across a shared scheduler. That is exactly our situation — our children are the same shape (research / build / review / plan) — which is why it transfers nearly whole.

**And we already have a subset of it.** MMF Phase 3's typed exit record is the shipped starting point. **This is the extension of something shipped, not a new invention**, and requirement 3 forbids a second parallel contract precisely because two envelopes is how the field sets drift.

### Lineage on every emitted item — and this reverses a wrong call

**Provenance:** n8n's `pairedItem`, which records which output item came from which input item, by index.

**A decision was made in session and then reversed against the evidence, and the reversal is load-bearing.** The PM argued n8n's model did not transfer because our children run in sequence. **That is false.** Nothing prevents a parent launching children in parallel, and we already do: the 2026-08-12 verify round dispatched two critics **21 seconds apart**. Fan-out is real today, so *"which output came from which input"* is a question about our own runs that we currently cannot answer.

**Do not re-derive the sequential-children argument.** It has been checked against a real dispatch and it lost.

### An API key is a credential, not an identifier

The upstream Django/Temporal pair has to know every edge and how to work with it, and **the API key already associated with an edge is the natural carrier** — it is how the edge authenticates today, so the identity exists and merely needs mirroring outward.

**⚠ But a key is a CREDENTIAL, and credentials rotate.** A journal keyed by API key **orphans an edge's entire history the day the key is rotated**. The key authenticates; **it maps to a stable edge id that never rotates**. One line of design now, an unrecoverable data-modelling mess later — which is why requirement 5 lands in this phase rather than in Phase 7 where the second edge appears.

**Security consequence, stated because it constrains the implementation:** the `edge_id` is an identifier and appears in every event; the key is a secret and appears in none. An event carrying a key — or a value derived from a key in a way that survives rotation — is a defect, not a convenience.

### Schema evolution — decided on day one because it is brutal to retrofit

A journal written under v1 must still replay under v3, forever. Every event-sourced system meets this. **The settled answer: version every event, never mutate a written one, upcast on read.**

The version field's home is Phase 1's `bagit.txt`; requirement 6 is this phase honouring it on every event. **The detailed mechanism is open** (roadmap § *Open inputs*, item 4) and this phase does not close it — but an unversioned v1 event is unrecoverable, so the rule ships now and the mechanism follows.

**Provenance.** This is **event sourcing**, and it is Temporal's own model applied one level up: event history is the truth, workflow state is a projection rebuilt by replay. `bernstein`'s journal is the same shape.

---

## The write-path inventory

*(Requirement 7. Populated when the phase runs — enumerated from the tree, not from memory, with the command that enumerated it.)*

Every row is a surface the fleet writes to, and every row needs an emit. **A surface with no emit is the finding**, and it is what [Phase 4](phase4_rebuild_is_a_test.md) turns into a failing test rather than a note.

| Surface | Written by | Emit | Rebuildable? |
|---|---|---|---|
| *(enumerated at build time)* | | | |

The five Kind 1 surfaces documented in [`memory-model.md`](../../guide/memory-model.md) §2 are the known floor, not the expected total — the inventory is derived by searching the tree for write paths, and any surface found that `memory-model.md` does not list is itself a finding worth reporting back to that doc.

---

## Implementation checklist

- [ ] Enumerate every write path in the tree and populate the inventory above with the command used
- [ ] Specify the event envelope as an extension of MMF Phase 3's record — every added field with its named consumer
- [ ] Add `edge_id`, `schema_version`, `destination`, and the lineage reference to the envelope
- [ ] Specify how `edge_id` is derived from the authenticating key **without the key surviving into any event**
- [ ] Wire the emit into every inventoried write path
- [ ] Demonstrate a full `research_minor` cycle whose authored output appears in the journal verbatim
- [ ] Demonstrate a parallel fan-out round whose outputs each trace back to their input
- [ ] Tests per the [Testing Standard](../../standards/testing/README.md): `unit/` for envelope construction and edge-id mapping, `integration/` for one real dispatch's emits
- [ ] Record the measured authored-byte total against the 39,772-byte baseline, with its denominator, in § *Measurement*

---

## Measurement

*(Populated when the phase runs.)*

The number that matters is **authored bytes emitted per run against authored bytes written to stores** — they should be equal, and any gap is an unemitted write path. The 39,772-byte figure from one `research_minor` cycle (synthesis §2, measured 2026-08-12) is the baseline; a materially smaller figure means the emit is incomplete, and a materially larger one means something is being emitted twice.

---

## Notes and open items

- **Completeness cannot be proven by this phase.** Requirement 7's inventory is a snapshot, and a snapshot goes stale the first time a write path is added. **[Phase 4](phase4_rebuild_is_a_test.md) is what makes it stay true**, and this phase is not done in any meaningful sense until Phase 4 runs. They are separate phases because they have separate verifiable outcomes — not because the gap between them is safe.
- **This phase writes no reader.** Under the pair-every-producer-with-its-consumer discipline that is a debt, and [Phase 6](roadmap.md#phase-6--the-poller-and-cpi-on-edge1-gated-phase-5) is where it is paid. It is called out here rather than left implicit because [MMF Phase 6](../memory-management-framework/phase6_read_what_it_writes.md) measured what happens when it is not: three phases shipped an emitter and none shipped a reader.

# Phase 3 — The emit rule: every write to any store also emits to the journal

**Component:** [Persistent Memory Protocol](roadmap.md) · **Status:** not started · **Gate:** Phase 1

This is the core rule of the component, and it is the operator's. A run writes wherever it needs to, in whatever format that surface wants. **If any store gets it, the journal gets it, verbatim.**

**The design test, in the operator's words, and every proposal to leave something out is checked against this sentence:**

> *"If I have a question it always starts in the journal. I rarely have to go to another source, because I know if I do it is just duplicated info from the journal anyway."*

---

## Requirements for completion

1. **Every write path in the inventory emits a journal event** carrying the authored content **verbatim**, with the destination store as a field. **The bar is: the inventory is complete, and every inventoried path emits.** *(Stated this precisely at review, because "every write path to every store" carries two readings an order of magnitude apart — the envelope proven on one path, versus every path in the fleet — and the sibling component has already paid for that ambiguity once, at a measured factor of ten.)*
2. **The journal is identical regardless of destination.** git, SQLite, a GitHub object, an MQTT topic on an edge with no repo — the destination is a field, not a format.
3. **The event envelope is modality-neutral** and extends [MMF Phase 3](../memory-management-framework/phase3_typed_exit_record.md)'s typed exit record rather than inventing a second contract.
4. **Every emitted item records which input item produced it**, so a fan-out round can be traced output-to-input.
5. **Every event carries a stable `edge_id` that never rotates**, persisted at the edge and independent of any credential. **This is closable on its own** and carries the constraint that no event ever contains a key or a value derived from one.
6. **The event admission contract is specified** — identity, authority, epoch and provenance. § *What makes an event admissible* below; it is one decision with four fields, not four decisions.
7. **Every event carries a schema version** and no written event is ever mutated, with the redaction event class ([Phase 1](phase1_the_run_bag.md)) as the single stated exception.
8. **The write-path inventory is complete and enumerated in this doc**, split into **fleet-code writes** and **model-issued writes**, each with its named emit mechanism.
9. **The capture path filters secrets before a payload is sealed.** § *Capture-time filtering* below.

**Requirement 8 is the honest half of requirement 1.** "Every write path" is unverifiable as stated; a named list is verifiable, and [Phase 4](phase4_rebuild_is_a_test.md) is what keeps the list true after this phase closes.

**Deferred on a named trigger, per the sibling component's precedent:** requirement 1 closes when the inventory's paths emit. **A write path added after this phase is that change's responsibility, not a re-opening of this one** — which is exactly what requirement 8 plus Phase 4's failing test are for.

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

### What makes an event admissible — one decision, four fields, none retrofittable

**Requirement 6 exists because "append verbatim" says nothing about who may append, or whether an append happened once.** Four questions, and the plan's own argument for deciding schema versioning on day one applies unchanged to each: an event written without these fields is unrecoverable.

**(a) Identity, against an at-least-once execution model.** The [Temporal Standard](../../standards/temporal/temporal_standard.md) §7.1 requires every activity to be idempotent, because activities execute **at least once** — a retried activity re-runs its side effects. An append-only journal fed by retried activities accumulates **duplicate events**, and [Phase 4](phase4_rebuild_is_a_test.md)'s replay then rebuilds a store with duplicated rows — or worse, passes under a normalisation that hides them. **Every event carries a deterministic identity** (`run_id` + write-path + logical sequence, or a content hash), and **replay is defined as dedupe-on-identity.**

**(b) Authority — who says which `edge_id` an event carries.** Requirement 5 makes the id stable; it does not say who asserts it. Events are naturally built at the edge, so the default implementation is a **self-reported field** — and then any holder of any valid credential can author events attributed to a different edge. In an append-only store that is unfalsifiable after the fact, and under Phase 4 the stores are **projections**, so spoofed attribution replays straight into `candidates.md` and `direction.md`. **The rule: `edge_id` is assigned by the authenticating authority and bound at ingest. An edge-supplied `edge_id` in an event envelope is rejected, not trusted.**

**(c) A credential epoch, so compromise has a boundary.** *"An id that never rotates"* is right, and it leaves no way to say *"events from edge E between T1 and T2 were authored under a credential that leaked."* Revoking a leaked key then revokes nothing about the record: the injected events replay faithfully. **Every event carries a non-secret `key_id` / credential epoch** — an opaque server-assigned identifier or monotonic counter, **explicitly not derived from the key**, per the ruling below — **and a replay may be scoped to exclude an epoch.**

**(d) Provenance — what kind of thing this content is by origin.** Fleet-authored prose, operator-authored input, and **bytes fetched from the internet** all enter the journal (the last via tool results in the transcript and wholesale via [Phase 2](phase2_content_store.md)'s content store). Without a trust-class field every downstream reader sees one undifferentiated stream. **This is the field [Phase 7](roadmap.md#phase-7--s3-aggregation-local-write-first-gated-a-second-edge-and-a-classification-ruling)'s ingress ruling has to range over** — omitting it here forecloses that ruling before it is made.

### Capture-time filtering — requirement 9

The journal is immutable and the authored record never prunes, so **capture is the only point in the lifecycle where a secret can be cheaply kept out.** After [Phase 4](phase4_rebuild_is_a_test.md) wires the rebuild test to a gate, removing a payload file is a gate change; after Phase 7 it is a bucket-wide purge.

The transcript carries the literal input of every Bash call, and this repo already treats that as sensitive: `scripts/workflows/temporal/modules/assistant/review_pr/exit_record.py` drops tool input *"at READ TIME, so there is no copy to leak"*, with a test holding the claim. **That control guards a display surface. The journal is a durable one, so the filter runs before the payload is sealed** — and it **emits a placeholder event**, so the record stays complete about the *fact* of a redaction rather than silently shorter. [Phase 1](phase1_the_run_bag.md)'s redaction event class is the after-the-fact complement, for what gets through.

### An API key is a credential, not an identifier

The upstream Django/Temporal pair has to know every edge and how to work with it, and **the API key already associated with an edge is the natural carrier** — it is how the edge authenticates today, so the identity exists and merely needs mirroring outward.

**⚠ But a key is a CREDENTIAL, and credentials rotate.** A journal keyed by API key **orphans an edge's entire history the day the key is rotated**. The key authenticates; **it maps to a stable edge id that never rotates**. One line of design now, an unrecoverable data-modelling mess later — which is why requirement 5 lands in this phase rather than in Phase 7 where the second edge appears.

**Security consequence, stated because it constrains the implementation:** the `edge_id` is an identifier and appears in every event; the key is a secret and appears in none. An event carrying a key — or a value derived from a key in a way that survives rotation — is a defect, not a convenience. *(That clause also rules out `hash(api_key)` as an edge id, which is both the rotation bug and a security one: a stored hash of a live credential is an offline confirmation oracle.)*

**⚠ Requirement 5 was split from the mapping at review, because the two have different evidence bars.** A **stable, persisted `edge_id` independent of any credential** is buildable in this repo today and closes on its own. The **key→id mapping** lives in the upstream Django/Temporal pair — a system outside this repo, with no edge API key in this fleet's configuration to point at — so it can only be closed by assertion here. It is deferred on the named trigger *"the upstream pair authenticates an edge."* The no-key-in-events constraint rides on the buildable half, deliberately.

### Schema evolution — decided on day one because it is brutal to retrofit

A journal written under v1 must still replay under v3, forever. Every event-sourced system meets this. **The settled answer: version every event, never mutate a written one, upcast on read.**

The version field's home is Phase 1's `bagit.txt`; requirement 6 is this phase honouring it on every event. **The detailed mechanism is open** (roadmap § *Open inputs*, item 4) and this phase does not close it — but an unversioned v1 event is unrecoverable, so the rule ships now and the mechanism follows.

**Provenance.** This is **event sourcing**, and it is Temporal's own model applied one level up: event history is the truth, workflow state is a projection rebuilt by replay. `bernstein`'s journal is the same shape.

---

## The write-path inventory

*(Requirement 8. Populated when the phase runs — enumerated from the tree, not from memory, with the command that enumerated it.)*

Every row is a surface the fleet writes to, and every row needs an emit. **A surface with no emit is the finding**, and it is what [Phase 4](phase4_rebuild_is_a_test.md) turns into a failing test rather than a note.

**⚠ THE INVENTORY HAS TWO HALVES, AND A TREE SEARCH FINDS ONLY ONE OF THEM.** This is the gap most likely to close this phase with its headline requirement unmet:

- **Fleet-code writes** — a call site in `scripts/` that writes to a store. Enumerable by grep; wrap it and it emits.
- **MODEL-ISSUED writes** — the child itself runs `gh pr comment --body-file …`, instructed by a prompt. **A tree search finds a prompt sentence, not a call site.** And these are the writes this component exists for: the PR body, the decision log, the reflection comment are the first artifacts the synthesis names and the ones the operator's design test is about.

**A build that enumerates only the first half populates the table, wires every row, closes requirement 1, and never emits a single PR comment — and nothing goes red**, because [Phase 4](phase4_rebuild_is_a_test.md) can only test the stores whose emits exist. So the inventory is split by construction, and the second half needs a *mechanism* rather than a wrap. The cheapest one that works today is a **post-exit harvest**: after the child exits, fleet code fetches the run's PR body and comments via `gh`, keyed by `run_id`, and emits them verbatim. It has a stated failure mode — **a comment posted after the harvest window is not captured** — and naming that is part of the requirement.

| Surface | Written by (fleet-code / model-issued) | Emit mechanism | Rebuildable? |
|---|---|---|---|
| *(enumerated at build time)* | | | |

The five Kind 1 surfaces documented in [`memory-model.md`](../../guide/memory-model.md) §2 are the known floor, not the expected total, and any surface found that `memory-model.md` does not list is itself a finding worth reporting back to that doc.

**⚠ And a third category exists that neither half covers: writes made by no run at all.** The operator sets `direction.md`'s `status`; `/standup` deletes rotated rows; `candidates.md` rows have been hand-corrected. **No tree search finds a human**, and under Phase 4 those edits are writes that must also emit or replay reverts them — which would revert exactly the operator rulings that are the highest-value content in either file. **For the file binding the natural emit is the git commit itself**, which is consistent with synthesis §10 (each surface's own binding is a local convenience; the journal is the record). Specifying that is part of requirement 8; if it is not specified, [Phase 4](phase4_rebuild_is_a_test.md) scopes its rebuild targets to run-authored content and records the exclusion, rather than shipping a test that is green and wrong.

---

## Implementation checklist

- [ ] Enumerate every write path and populate the inventory above with the command used — **split fleet-code from model-issued, and name the mechanism for the second**
- [ ] Specify the third category (out-of-run writes) or hand its exclusion to Phase 4 explicitly
- [ ] Specify the event envelope as an extension of MMF Phase 3's record — every added field with its named consumer
- [ ] Add `edge_id`, `schema_version`, `destination`, the lineage reference, **the event identity, the credential epoch and the provenance class** to the envelope — one change, per requirement 6
- [ ] State that `edge_id` is bound at ingest by the authenticating authority and that an edge-supplied one is rejected, **with no key or key-derived value surviving into any event**
- [ ] Define replay's dedupe-on-identity rule so a retried activity cannot double-append
- [ ] Build capture-time filtering, emitting a placeholder event where it fires
- [ ] Wire the emit into every inventoried write path
- [ ] Demonstrate a full `research_minor` cycle whose authored output — **including the PR body and every comment** — appears in the journal verbatim
- [ ] Demonstrate a parallel fan-out round whose outputs each trace back to their input, in real bags (this is [Phase 1](phase1_the_run_bag.md) requirement 3's live evidence, which Phase 1 cannot produce)
- [ ] Demonstrate that a deliberately retried emit appends once
- [ ] Tests per the [Testing Standard](../../standards/testing/README.md): `unit/` for envelope construction and edge-id mapping, `integration/` for one real dispatch's emits
- [ ] Record the measured authored-byte total against the 39,772-byte baseline, with its denominator, in § *Measurement*

---

## Measurement

*(Populated when the phase runs.)*

The number that matters is **authored bytes emitted per run against authored bytes written to stores** — they should be equal, and any gap is an unemitted write path. The 39,772-byte figure from one `research_minor` cycle (synthesis §2, measured 2026-08-12) is the baseline; a materially smaller figure means the emit is incomplete, and a materially larger one means something is being emitted twice.

---

## Notes and open items

- **Completeness cannot be proven by this phase.** Requirement 7's inventory is a snapshot, and a snapshot goes stale the first time a write path is added. **[Phase 4](phase4_rebuild_is_a_test.md) is what makes it stay true**, and this phase is not done in any meaningful sense until Phase 4 runs. They are separate phases because they have separate verifiable outcomes — not because the gap between them is safe.
- **This phase writes no reader.** Under the pair-every-producer-with-its-consumer discipline that is a debt, and [Phase 6](phase6_cpi_reads_the_journal.md) is where it is paid. It is called out here rather than left implicit because [MMF Phase 6](../memory-management-framework/phase6_read_what_it_writes.md) measured what happens when it is not: three phases shipped an emitter and none shipped a reader.

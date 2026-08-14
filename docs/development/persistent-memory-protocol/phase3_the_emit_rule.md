# Phase 3 — The emit rule: every write to any store also emits to the journal

**Component:** [Persistent Memory Protocol](roadmap.md) · **Status:** not started · **Gate:** Phase 1

## What this phase does

This is the phase that actually starts writing the record, and the rule it enforces is one sentence: **whenever a run writes anything to any store, it also writes a copy into the journal.** The pull-request body, every comment, the review verdict, the triage, the approval, issues, table rows — all of it, word for word.

The one exception is a code change, and it is excluded for a stated reason rather than to save room: git already stores code better than anything this component could build, so the journal records which commit it was and you go get it from there.

**And this phase answers what happens when that write fails** — when the disk is full, the mount went read-only, or the path is gone. That question decides whether the next phase's guarantee means anything, so it is answered here rather than discovered during an incident.

**Terms used here.** The **journal** is the whole record: one folder tree per machine, one folder per run, never edited after the run ends. A **bag** is one run's folder (the name comes from BagIt, the file-layout standard it follows — a folder on disk, never a Docker container). To **emit** is to write one entry into the journal. An **event** is one such entry; events are appended and never changed. A **store** is any place other than the journal that a run writes to. To **rebuild** a store is to read the journal back and regenerate what it holds. An **edge** is one machine running this fleet.

**The design test, in the operator's words, and every proposal to leave something out is checked against this sentence:**

> *"If I have a question it always starts in the journal. I rarely have to go to another source, because I know if I do it is just duplicated info from the journal anyway."*

---

## Requirements for completion

1. **Every write path in the inventory emits a journal event** carrying the authored content **verbatim**, with the destination store as a field. **The bar is: the inventory is complete, and every inventoried path emits.** *(Stated this precisely at review, because "every write path to every store" carries two readings an order of magnitude apart — the envelope proven on one path, versus every path in the fleet — and the sibling component has already paid for that ambiguity once, at a measured factor of ten.)*
2. **The journal is identical regardless of destination.** git, SQLite, a GitHub object, a message topic on a machine with no repo — the destination is a field, not a format.
3. **The event contract reuses the [typed exit record](../memory-management-framework/phase3_typed_exit_record.md)'s vocabulary, with one declaration per shared concept, and is a separate contract from it.** Not an extension of it. § *One vocabulary, two contracts* below states why the extension the draft promised is not possible.
4. **A failed journal write is never silent.** § *When the journal cannot be written* below — **four** cases, each with a stated behaviour, and none of them is "continue and hope". A paired write is **one unit with two events** (intent, then completion), and replay applies only an intent that has a completion.
5. **Every emitted item records which input item produced it**, so a fan-out round can be traced output-to-input.
6. **Every event carries a stable `edge_id` that never rotates**, persisted at the machine and independent of any credential. **This is closable on its own** and carries the constraint that no event ever contains a key or a value derived from one.
7. **The event admission contract is specified** — identity, authority, epoch and provenance. § *What makes an event admissible* below; it is one decision with four fields, not four decisions.
8. **Every event carries a schema version** and no written event is ever changed, with the redaction event class ([Phase 1](phase1_the_run_bag.md)) as the single stated exception.
9. **The write-path inventory is complete and enumerated in this doc**, split into **fleet-code writes** and **model-issued writes**, each with its named emit mechanism.
10. **The capture path filters secrets at append time** — before any byte reaches the journal root, not merely before the bag is sealed. § *Capture-time filtering* below.

**Requirement 9 is the honest half of requirement 1.** "Every write path" is unverifiable as stated; a named list is verifiable, and [Phase 4](phase4_rebuild_is_a_test.md) is what keeps the list true after this phase closes.

**Deferred on a named trigger, per the sibling component's precedent:** requirement 1 closes when the inventory's paths emit. **A write path added after this phase is that change's responsibility, not a re-opening of this one** — which is exactly what requirement 9 plus Phase 4's failing test are for.

---

## Dependencies

- **[Phase 1](phase1_the_run_bag.md)** — the bag is where events land. Hard dependency.
- **[MMF Phase 3](../memory-management-framework/phase3_typed_exit_record.md)** — supplies two things, and they are different. (i) The **vocabulary** this phase's events reuse (requirement 3). (ii) The **channel** requirement 4 reports an unwritable journal on, which is the one place a journal failure can be announced without needing the journal. **Complete**, so neither blocks.
- **[Phase 2](phase2_content_store.md)** — not a dependency. Events reference artifacts by hash where a content store exists and by SHA/URL where it does not; the emit rule does not wait on the store.

---

## What this phase decides

### Completeness is absolute — prose in, code out

**Everything a run authors goes in:** the PR body, every reflection and decision-log comment, the review verdict, the triage, the direction, the approval, the re-run count, the PR number and repo, issues, candidate rows. Anything on any surface.

**The one exclusion is the code diff, and it is excluded for a stated reason rather than to save space: git is already a better store for it.** The journal carries the commit SHA and you go get the diff. That is [Phase 2](phase2_content_store.md)'s by-reference rule applied to the record itself.

**The line is one question: does a better durable store already exist for this artifact type?** For code it does. For the prose a run writes into GitHub it emphatically does not — comments are editable, deletable, unversioned, hosted by a service, **and they are where the reasoning lives.**

**The volume objection is measured, and it does not survive.** The instinct is to fear the byte count. For one full `research_minor` cycle, **all authored text — PR body plus every comment — was 39,772 bytes.** At that rate the authored record for the entire 175-run history is roughly **7 MB**. **The completeness rule costs almost nothing.** The volume in this system lives entirely in the CLI transcript, which is also in the journal and is governed separately by [Phase 5](phase5_snapshots_then_retention.md)'s split retention.

### The destination is a field, not a format

**The journal is identical whether the run wrote into git, a GitHub object, a SQLite file, or an MQTT topic on an edge with no repo.**

That property is not stylistic. It is what makes the record portable across edges, and it is what [Phase 7](phase7_s3_aggregation.md) depends on: a second edge of any type sources the same data from the protocol rather than from a repo. **Git stays for the edge we are building now**, because that edge's memory *is* versioned with code, reviewed in PRs, and travels with a clone — but git is that edge's binding, not the protocol's. Each edge reads and writes whatever surface it needs; **the truth is always the centralized output.** A surface is a local convenience; the journal is the record.

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

**And we already have a subset of it.** MMF Phase 3's typed exit record is the shipped starting point — for the *vocabulary*, not for the envelope. The next section is why that distinction is load-bearing rather than pedantic.

### One vocabulary, two contracts — requirement 3, corrected

**The draft of this doc said the journal envelope "extends MMF Phase 3's typed exit record rather than inventing a second contract." That is not possible, and the standard it names is what forbids it.**

[`exit-protocol.md`](../../standards/exit-protocol.md) §2 states two rules about that record:

- *"No field is added on behalf of a consumer that does not exist."*
- §2.5: the envelope's fixed part is bounded at **4096 bytes**, *"the one corroborated cap figure in this evidence base (Tekton)."*

**Both rules reject what this phase needs, and not marginally.** Requirement 7 adds event identity, credential epoch and provenance class; requirements 5, 6 and 1 add lineage, `edge_id` and destination. **No parent branches on any of the six**, so the first rule rejects every one of them. And a journal event carries authored content verbatim — one `research_minor` cycle's authored output measured **39,772 bytes** (synthesis §2) against a 4096-byte bound, roughly tenfold over on size alone.

**So the two are separate contracts that share one vocabulary**, and requirement 3 is the discipline that keeps that from becoming drift:

| | Typed exit record | Journal event |
|---|---|---|
| Read by | the parent, in code, within seconds | a later run, a person, a rebuild — indefinitely |
| Lifetime | one invocation | forever |
| Admission rule | a consumer must already exist | completeness: if a store got it, this gets it |
| Size posture | bounded at 4096 bytes | carries content verbatim |

**What "one vocabulary" binds:** every concept both contracts name — an outcome, a terminal state, a reason code — is **declared once, in one module, and spelled the same way in both.** Two spellings of one concept is the drift requirement 3 exists to prevent, and it is a real risk precisely because the contracts are separate.

**The MMF-side change this implies is proposed, not written.** `exit-protocol.md` §2's no-speculative-fields rule and §2.5's size bound are correct **for a routing channel** and should say so; as written they read as governing any typed record this fleet emits, which is how a durable record came to be promised as an extension of a 4 KB routing envelope. That file is human-in-the-loop under [`standards-governance.md`](../../../config/rules/standards-governance.md), so the change is carried in this plan's [roadmap § *Questioning the Memory Management Framework*](roadmap.md#questioning-the-memory-management-framework) and in its pull-request body. **Nothing in this phase waits on it** — the correction above is a change to what *this* component builds.

### When the journal cannot be written — requirement 4

**The question this section answers:** the disk is full, the mount went read-only, the path is gone, the file handle failed. Does the run stop, or does it continue with a hole in the record?

**Neither, as stated — and the reason the question needs a real answer rather than a default is [Phase 4](phase4_rebuild_is_a_test.md).** That phase requires the journal to be able to rebuild the stores. **A journal with holes nothing knows about cannot rebuild anything**, and it cannot even report that it failed to: a rebuild that silently produces a store missing three rows looks exactly like a rebuild that worked. So a rule saying "every write also emits" is worth nothing if a failed emit is invisible.

**The rule: a gap may exist; a silent gap may not.**

**And one decision has to be made before the cases make sense, because getting it wrong makes the record confidently wrong rather than merely short.** *Does an emitted event record an INTENT to write, or the FACT of a write?*

**It records an intent, and therefore a second event records the fact.** The reasoning is in § *Why one event per write is not enough* below; every case here assumes it.

That splits into four cases by what is available to withhold, and they are ordered because the first one prevents most of the others.

**(a) The root cannot be resolved, at the start of the run → the run does not start.**

[Phase 1](phase1_the_run_bag.md) requirement 9 owns this: the root is resolved once, before any work happens, and a missing path, a read-only mount or a wrong-mode directory fails there. It is the cheapest possible failure — nothing has been spent — and it converts most of the interesting disk-level failures into a refusal at second zero rather than a hole at minute ninety.

**(b) A write that has a paired store write → the intent event goes FIRST, and a failed intent means the store write does not happen.**

This is the ordering that makes requirement 1's invariant self-enforcing. The rule is *if any store gets it, the journal gets it*. Order the intent before the store write and a journal failure means **neither** happened — the invariant holds, because both sides are absent. Order it after and a journal failure means the store has something the record does not, which is exactly the state the component exists to prevent.

The run then stops at that boundary with a named terminal state rather than continuing. **It does not retry indefinitely and it does not carry on to the next step**, because every subsequent step's record would be conditioned on a write nobody can see.

*(This is a write-ahead log, which is what an append-only record that other stores are regenerated from is. Naming it is worth a sentence: the ordering constraint is not an invention of this plan, and anyone implementing it has decades of prior art to read.)*

**(c) A write with no pairable store write → a typed gap event, and the bag is marked `incomplete`.**

Some of what goes into the journal has no corresponding store write to withhold: the CLI transcript, the execution facts, and the post-exit harvest of model-issued writes. Write-ahead ordering has nothing to offer here — the content already exists and the only question is whether it lands.

So the failure is **recorded rather than prevented**. A gap event names what was lost, when, why, and how much — and it is a **closed typed field set** (write-path id, byte count, error class, timestamp), never free text derived from the content or from an exception message, so it costs a few hundred bytes and cannot become a side channel for the very bytes it is reporting the loss of. The bag is marked **`incomplete`** ([Phase 1](phase1_the_run_bag.md) § *Bag lifecycle*). Everything downstream then treats that bag as a known-gap input rather than a clean one: [Phase 4](phase4_rebuild_is_a_test.md) reports gapped bags with a count and its denominator rather than diffing them as complete, [Phase 6](phase6_cpi_reads_the_journal.md) says so in its own report, and [Phase 7](phase7_s3_aggregation.md) ships the marking with the bag.

**⚠ The transcript is the one member of this case that is not merely a completeness problem.** It is the fleet's only record of what commands ran, this fleet runs with permissions bypassed, and a run can itself create the disk-full condition that drops it. Losing it while the run proceeds to completion is evidence loss wearing a routine defect's clothes. **So a failed transcript write is treated as case (b) — the run stops** — rather than as an ordinary gap. The other two members of this case (execution facts, post-exit harvest) are gaps and the run continues.

**(d) The bootstrap case — the journal is unwritable, so the gap event cannot go in the journal either.**

This is the case that makes (c) circular if it is not answered. If the write failed because the root is gone or the gap event itself cannot be written, the record of that failure cannot be written to the root. **It is not startup-only** — case (a) catches the startup instance, and this one covers any point at which the journal stops being writable mid-run.

**It surfaces on two channels that are not the journal, and the second one is why the first is not enough.** The typed exit record ([MMF Phase 3](../memory-management-framework/phase3_typed_exit_record.md)) plus a non-zero exit status carry it out of the process — **and both are read within seconds and then gone**, so a failure reported only there is invisible to every consumer this component builds. **The durable half is the parent's own [Kind 1](../../guide/memory-model.md) write**: a pull-request comment or a standup-tracker line, which is durable, addressable, and outside the journal root by construction.

**And this case is uncountable from the journal, by construction.** [Phase 6](phase6_cpi_reads_the_journal.md) requirement 6 counts gaps by reading gap events, and a run in case (d) produced no gap event, no bag and nothing to count. That is not a defect in Phase 6's measurement; it is a stated limit of it, and Phase 6 says so rather than reporting a gap count that silently excludes the worst failures.

### Why one event per write is not enough

**Write-ahead ordering protects exactly one of the three ways a paired write can break, and the other two produce a journal that is confidently wrong.** Naming them is what makes the intent/completion split obviously necessary rather than ceremony:

| What breaks | What one event per write does | Why it matters |
|---|---|---|
| The journal write fails | Handled — case (b). Neither side is written. | This is the case the ordering was chosen for |
| **The store write fails after a successful emit** | The journal claims content the store never got. [Phase 4](phase4_rebuild_is_a_test.md) replays it and **materialises unpublished content into the store** — turning a failed write into a delayed successful one that no run and no human approved. | The rebuild is supposed to restore what happened, not complete what did not |
| **The activity is retried** | The [Temporal Standard](../../standards/temporal/temporal_standard.md) §7.1 requires idempotency because activities run **at least once**, so a retry re-runs *both* side effects. Requirement 7's dedupe-on-identity covers the journal side only, so the store gets a duplicate comment while the journal correctly records one. | Same red diff as the row above, in the opposite direction |

**And a third thing one event cannot carry: the store's own address.** A GitHub comment has no id or URL until after it is created, and requirement 8 forbids changing a written event. An intent-only record therefore can never name the object it is about.

**So a paired write is one unit with two events**, sharing requirement 7's identity: an **intent** before the store write, and a **completion** after it carrying the store-assigned address — or a typed **store-write-failure** event in its place. The store write derives its own idempotency key from that same identity, so a retry is a no-op on both sides rather than on one.

**Replay applies only an intent that has a completion.** That single rule is what makes the second and third rows above visible rather than silently wrong, and it is why [Phase 4](phase4_rebuild_is_a_test.md) § *Normalisation* can keep saying *"the finding is the missing emit"* — because with completions in the record, a diff genuinely is one.

**The model-issued half of requirement 9's inventory is case (c) by construction, and the docs must not imply otherwise.** When the child itself runs `gh pr comment`, the content exists before the fleet ever sees it — there is nothing to withhold, so write-ahead ordering is structurally unavailable and the post-exit harvest emits a **completion with no prior intent**, which is a legitimate typed shape rather than a hole. **This matters because that half is the half the operator's design test is about** — the pull-request body, the decision log, the reflection comment. They are protected by *"a gap event names what was lost"*, not by *"neither side is written"*, and that is a materially weaker guarantee stated here rather than discovered later.

**What is deliberately not built here:** any attempt to buffer, queue or retry into a second location. A fallback store is a second record with its own failure modes, and a record whose location depends on which failure occurred is worse than one that reliably refuses. **Failing loudly at a known boundary beats succeeding into somewhere nobody looks.**

### Lineage on every emitted item — and this reverses a wrong call

**Provenance:** n8n's `pairedItem`, which records which output item came from which input item, by index.

**A decision was made in session and then reversed against the evidence, and the reversal is load-bearing.** The PM argued n8n's model did not transfer because our children run in sequence. **That is false.** Nothing prevents a parent launching children in parallel, and we already do: the 2026-08-12 verify round dispatched two critics **21 seconds apart**. Fan-out is real today, so *"which output came from which input"* is a question about our own runs that we currently cannot answer.

**Do not re-derive the sequential-children argument.** It has been checked against a real dispatch and it lost.

### What makes an event admissible — one decision, four fields, none retrofittable

**Requirement 7 exists because "append verbatim" says nothing about who may append, or whether an append happened once.** Four questions, and the plan's own argument for deciding schema versioning on day one applies unchanged to each: an event written without these fields is unrecoverable.

**(a) Identity, against an at-least-once execution model.** The [Temporal Standard](../../standards/temporal/temporal_standard.md) §7.1 requires every activity to be idempotent, because activities execute **at least once** — a retried activity re-runs its side effects. An append-only journal fed by retried activities accumulates **duplicate events**, and [Phase 4](phase4_rebuild_is_a_test.md)'s replay then rebuilds a store with duplicated rows — or worse, passes under a normalisation that hides them. **Every event carries a deterministic identity** (`run_id` + write-path + logical sequence, or a content hash), and **replay is defined as dedupe-on-identity.**

**(b) Authority — who says which `edge_id` an event carries.** Requirement 6 makes the id stable; it does not say who asserts it. Events are naturally built at the edge, so the default implementation is a **self-reported field** — and then any holder of any valid credential can author events attributed to a different edge. In an append-only store that is unfalsifiable after the fact, and after Phase 4 the stores are rebuilt from the journal, so a spoofed attribution replays straight into `candidates.md` and `direction.md`. **The rule, stated in two halves because only one of them is buildable today.** The target: an `edge_id` is assigned by an authenticating authority and bound at ingest, and a self-supplied one is rejected rather than trusted. **But there is no ingest tier in this design and there is not going to be one soon** — [Phase 7](phase7_s3_aggregation.md) syncs sealed bags directly to object storage, and a receiver cannot rebind a field inside a sealed bag without invalidating its manifest. **So until an authenticating ingest exists, `edge_id` is SELF-REPORTED and is not an attribution control**, and this doc says so rather than stating a guarantee nothing enforces. The control that does exist in this topology is [Phase 7](phase7_s3_aggregation.md)'s: **a per-machine storage credential scoped to that machine's own prefix, with origin derived from the prefix an object was found under and a prefix/`edge_id` disagreement reported as a finding.** The field stays on the event because the ingress ruling needs something to range over and because a later ingest tier can begin binding it without a schema change.

**(c) A credential epoch, so compromise has a boundary.** *"An id that never rotates"* is right, and it leaves no way to say *"events from edge E between T1 and T2 were authored under a credential that leaked."* Revoking a leaked key then revokes nothing about the record: the injected events replay faithfully. **Every event carries a non-secret `key_id` / credential epoch** — an opaque server-assigned identifier or monotonic counter, **explicitly not derived from the key**, per the ruling below — **and a replay may be scoped to exclude an epoch.**

**(d) Provenance — what kind of thing this content is by origin.** Fleet-authored prose, operator-authored input, and **bytes fetched from the internet** all enter the journal (the last via tool results in the transcript and wholesale via [Phase 2](phase2_content_store.md)'s content store). Without a trust-class field every downstream reader sees one undifferentiated stream. **This is the field [Phase 7](phase7_s3_aggregation.md)'s ingress ruling has to range over** — omitting it here forecloses that ruling before it is made.

### Capture-time filtering — requirement 10

The journal is immutable and the authored record never prunes, so **capture is the only point in the lifecycle where a secret can be cheaply kept out.** After [Phase 4](phase4_rebuild_is_a_test.md) wires the rebuild test to a gate, removing a payload file is a gate change; after Phase 7 it is a bucket-wide purge.

The transcript carries the literal input of every Bash call, and this repo already treats that as sensitive: `scripts/workflows/temporal/modules/assistant/review_pr/exit_record.py` drops tool input *"at READ TIME, so there is no copy to leak"*, with a test holding the claim. **That control guards a display surface. The journal is a durable one, so the filter runs at APPEND time — before any byte reaches the journal root, not merely before the bag is sealed.** The distinction is load-bearing under write-ahead ordering: the journal now receives every payload *first*, so "before sealed" would leave unfiltered bytes sitting in appended event files for the life of the run, and filtering them at seal time would change written events, which requirement 8 forbids. **The filter cannot run retroactively** — redaction is the only after-the-fact path. And it **emits a placeholder event**, so the record stays complete about the *fact* of a redaction rather than silently shorter. [Phase 1](phase1_the_run_bag.md)'s redaction event class is the after-the-fact complement, for what gets through.

### An API key is a credential, not an identifier

The upstream Django/Temporal pair has to know every edge and how to work with it, and **the API key already associated with an edge is the natural carrier** — it is how the edge authenticates today, so the identity exists and merely needs mirroring outward.

**⚠ But a key is a CREDENTIAL, and credentials rotate.** A journal keyed by API key **orphans an edge's entire history the day the key is rotated**. The key authenticates; **it maps to a stable edge id that never rotates**. One line of design now, an unrecoverable data-modelling mess later — which is why requirement 6 lands in this phase rather than in Phase 7 where the second edge appears.

**This is already a binding rule rather than this component's preference.** [Temporal Standard](../../standards/temporal/temporal_standard.md) §7.5 *Identities are explicit, never derived* states it generally — *wherever a resource is located or targeted by an identity, the identity is an explicit input, not a derivation* — and the `edge_id` is one instance of it.

**Security consequence, stated because it constrains the implementation:** the `edge_id` is an identifier and appears in every event; the key is a secret and appears in none. An event carrying a key — or a value derived from a key in a way that survives rotation — is a defect, not a convenience. *(That clause also rules out `hash(api_key)` as an edge id, which is both the rotation bug and a security one: a stored hash of a live credential is an offline confirmation oracle.)*

**⚠ Requirement 6 was split from the mapping at review, because the two have different evidence bars.** A **stable, persisted `edge_id` independent of any credential** is buildable in this repo today and closes on its own. The **key→id mapping** lives in the upstream Django/Temporal pair — a system outside this repo, with no edge API key in this fleet's configuration to point at — so it can only be closed by assertion here. It is deferred on the named trigger *"the upstream pair authenticates an edge."* The no-key-in-events constraint rides on the buildable half, deliberately.

### Schema evolution — decided on day one because it is brutal to retrofit

A journal written under v1 must still replay under v3, forever. Every event-sourced system meets this. **The settled answer: version every event, never mutate a written one, upcast on read.**

The version field's home is Phase 1's `bag-info.txt` — **not `bagit.txt`**, which RFC 8493 requires to be exactly two lines ([Phase 1](phase1_the_run_bag.md) requirement 6 carries the correction and its reason). Requirement 8 is this phase honouring the version on every event. **The detailed mechanism is open** ([roadmap § *Open inputs*](roadmap.md#open-inputs--questions-this-plan-carries-forward-without-answering), item 6) and this phase does not close it — but an unversioned v1 event is unrecoverable, so the rule ships now and the mechanism follows.

**Provenance.** This is **event sourcing**, and it is Temporal's own model applied one level up: event history is the truth, and workflow state is regenerated from it by replay. `bernstein`'s journal is the same shape.

---

## The write-path inventory

*(Requirement 9. Populated when the phase runs — enumerated from the tree, not from memory, with the command that enumerated it.)*

Every row is a surface the fleet writes to, and every row needs an emit. **A surface with no emit is the finding**, and it is what [Phase 4](phase4_rebuild_is_a_test.md) turns into a failing test rather than a note.

**⚠ THE INVENTORY HAS TWO HALVES, AND A TREE SEARCH FINDS ONLY ONE OF THEM.** This is the gap most likely to close this phase with its headline requirement unmet:

- **Fleet-code writes** — a call site in `scripts/` that writes to a store. Enumerable by grep; wrap it and it emits.
- **MODEL-ISSUED writes** — the child itself runs `gh pr comment --body-file …`, instructed by a prompt. **A tree search finds a prompt sentence, not a call site.** And these are the writes this component exists for: the PR body, the decision log, the reflection comment are the first artifacts the synthesis names and the ones the operator's design test is about.

**A build that enumerates only the first half populates the table, wires every row, closes requirement 1, and never emits a single PR comment — and nothing goes red**, because [Phase 4](phase4_rebuild_is_a_test.md) can only test the stores whose emits exist. So the inventory is split by construction, and the second half needs a *mechanism* rather than a wrap. The cheapest one that works today is a **post-exit harvest**: after the child exits, fleet code fetches the run's PR body and comments via `gh`, keyed by `run_id`, and emits them verbatim. It has a stated failure mode — **a comment posted after the harvest window is not captured** — and naming that is part of the requirement.

| Surface | Written by (fleet-code / model-issued) | Emit mechanism | Rebuildable? |
|---|---|---|---|
| *(enumerated at build time)* | | | |

The five Kind 1 surfaces documented in [`memory-model.md`](../../guide/memory-model.md) §2 are the known floor, not the expected total, and any surface found that `memory-model.md` does not list is itself a finding worth reporting back to that doc.

**⚠ And a third category exists that neither half covers: writes made by no run at all.** The operator sets `direction.md`'s `status`; `/standup` deletes rotated rows; `candidates.md` rows have been hand-corrected. **No tree search finds a human**, and under Phase 4 those edits are writes that must also emit or replay reverts them — which would revert exactly the operator rulings that are the highest-value content in either file. **For the file binding the natural emit is the git commit itself**, which is consistent with synthesis §10 (each surface's own binding is a local convenience; the journal is the record). Specifying that is part of requirement 9; if it is not specified, [Phase 4](phase4_rebuild_is_a_test.md) scopes its rebuild targets to run-authored content and records the exclusion, rather than shipping a test that is green and wrong.

---

## Implementation checklist

- [ ] Enumerate every write path and populate the inventory above with the command used — **split fleet-code from model-issued, and name the mechanism for the second**
- [ ] Specify the third category (out-of-run writes) or hand its exclusion to Phase 4 explicitly
- [ ] Specify the journal event contract as its own contract, and enumerate every concept it shares with MMF Phase 3's record — each declared once, in one module, spelled the same in both
- [ ] **Build the write-ahead ordering**: the emit precedes its paired store write, and a failed emit means the store write does not happen
- [ ] **Build the gap event** for writes with no pairable store write — bounded and typed, naming what was lost, when, why and how much — and mark the bag `incomplete`
- [ ] **Report an unwritable journal on the typed exit record and a non-zero exit status**, so the bootstrap case is not silent
- [ ] **Specify the paired write as one unit with two events** — intent then completion (or a typed store-write-failure event) sharing requirement 7's identity, with the store write deriving its idempotency key from that same identity
- [ ] Demonstrate all **four** write-failure cases against a real journal: an unresolvable root refusing to start; a failed intent leaving neither side written; a failed unpairable write producing a gap event on an `incomplete` bag; and an unwritable journal reported on the exit record **and** on a durable Kind 1 surface
- [ ] Demonstrate the **store-write** failure and the **retried-activity** cases: an intent with no completion is not applied by replay, and a retry appends once on both sides
- [ ] Add `edge_id`, `schema_version`, `destination`, the lineage reference, **the event identity, the credential epoch and the provenance class** to the event contract — one change, per requirement 7
- [ ] State that `edge_id` is bound at ingest by the authenticating authority and that an edge-supplied one is rejected, **with no key or key-derived value surviving into any event**
- [ ] Define replay's dedupe-on-identity rule so a retried activity cannot double-append
- [ ] Build capture-time filtering, emitting a placeholder event where it fires
- [ ] Wire the emit into every inventoried write path
- [ ] Demonstrate a full `research_minor` cycle whose authored output — **including the PR body and every comment** — appears in the journal verbatim
- [ ] Demonstrate a parallel fan-out round whose outputs each trace back to their input, in real bags (this is [Phase 1](phase1_the_run_bag.md) requirement 3's live evidence, which Phase 1 cannot produce)
- [ ] Demonstrate that a deliberately retried emit appends once
- [ ] Tests per the [Testing Standard](../../standards/testing/README.md): `unit/` for event construction, edge-id mapping, each of the four write-failure cases, and the intent-without-completion rule; `integration/` for one real dispatch's emits
- [ ] Record the measured authored-byte total against the 39,772-byte baseline, with its denominator, in § *Measurement*

---

## Measurement

*(Populated when the phase runs.)*

The number that matters is **authored bytes emitted per run against authored bytes written to stores** — they should be equal, and any gap is an unemitted write path. The 39,772-byte figure from one `research_minor` cycle (synthesis §2, measured 2026-08-12) is the baseline; a materially smaller figure means the emit is incomplete, and a materially larger one means something is being emitted twice.

---

## Notes and open items

- **Completeness cannot be proven by this phase.** Requirement 9's inventory is a snapshot, and a snapshot goes stale the first time a write path is added. **[Phase 4](phase4_rebuild_is_a_test.md) is what makes it stay true**, and this phase is not done in any meaningful sense until Phase 4 runs. They are separate phases because they have separate verifiable outcomes — not because the gap between them is safe.
- **This phase writes no reader.** Under the pair-every-producer-with-its-consumer discipline that is a debt, and [Phase 6](phase6_cpi_reads_the_journal.md) is where it is paid. It is called out here rather than left implicit because [MMF Phase 6](../memory-management-framework/phase6_read_what_it_writes.md) measured what happens when it is not: three phases shipped an emitter and none shipped a reader.

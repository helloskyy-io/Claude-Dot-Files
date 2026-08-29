# The emit rule: every write to any store also emits to the journal — Persistent Memory Protocol

**Component:** [Persistent Memory Protocol](roadmap.md) · **Status:** not started · **Gate:** Phase 1, Phase 9 — **partially, and the scope is stated once in § *Dependencies* below**

> **This phase was SPLIT on 2026-08-28 and the half that left is [Phase 10](phase10_the_model_issued_harvest.md).** This doc still owns the emit rule for **fleet-code writes** — a call site in `scripts/` that writes to a store — and it still owns the *inventory* of both halves (requirement 9). What moved is the **mechanism** for model-issued writes: the post-exit harvest, its window, its standing check and its demonstration are [Phase 10](phase10_the_model_issued_harvest.md) r1–r7. **Nothing left this component and nothing entered it**; see § *Dependencies* below and [`roadmap.md`](roadmap.md) § *The order*. Stated here so a reader landing mid-document is not briefed into building the moved half twice.

**Why [Phase 9](phase9_one_run_one_identity.md) is a gate and not a sibling:** it rules **who owns the run id**, and this phase is the one that threads that value down to the children that emit — an emitter cannot be wired to a name whose authority has not been settled. The direction is stated from the other side too, in [Phase 9](phase9_one_run_one_identity.md) § *Dependencies* (*"this phase is a dependency OF Phase 3"*), and in `mint_run_id`'s own docstring (*"Threading this value down to the children is Phase 3's job"*).

**⚠ And the gate is scoped to the half of Phase 9 that can close, which is not a technicality.** Phase 9's own r2 *"stays UNCHECKED until its shape is agreed with the Temporal port"*, and [roadmap § *Open inputs*](roadmap.md) item 4 says that question *"is not answerable from here"*. **An unscoped `Gate: Phase 9` would therefore put this phase — and [Phase 4](phase4_rebuild_is_a_test.md) and [Phase 6](phase6_cpi_reads_the_journal.md) behind it — permanently behind another component's naming decision**, which would make the roadmap's *"commitments 1 through 5 … the component's whole thesis, standing on its own"* false. **WHICH of Phase 9's requirements this phase needs is stated once, in § *Dependencies* below, and is deliberately not restated here.** [Phase 9](phase9_one_run_one_identity.md) § *Dependencies* is the writer of that scope; this callout gives the CONSEQUENCE of getting the scope wrong and nothing more. **An earlier draft enumerated the requirement set here as well, and the two statements drifted** — this one still named *"r2's MECHANISM"* after the Dependencies bullet had been corrected to *"r1 and r4 … NOT r2"*, so a builder who met this callout first blocked on the one requirement that cannot close on this component's timeline. That is the whole reason the set is cited rather than repeated.

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
3. **The event contract reuses the typed exit record's vocabulary, with one declaration per shared concept, and is a separate contract from it.** Not an extension of it. § *One vocabulary, two contracts* below states why an extension is not possible.
4. **A failed journal write is never silent.** § *When the journal cannot be written* below — **four** cases, each with a stated behaviour, and none of them is "continue and hope". A paired write is **one unit with two events** (intent, then completion), and replay applies only an intent that has a completion. **Case (d)'s durable failure report is the single stated exception to requirement 1's invariant and to case (b)'s ordering**, because the emit that would precede it is the thing that failed.
5. **Every emitted item records which input item produced it**, so a fan-out round can be traced output-to-input.
6. **Every event carries a stable `edge_id` that never rotates**, persisted at the machine and independent of any credential. **This is closable on its own** and carries the constraint that no event ever contains a key or a value derived from one. **The identity's final shape is agreed jointly with the [Temporal Integration](../temporal-integration/temporal-integration.md) component**, which has its own reasons to name a machine — § *An identity is a joint design, not a requirement imposed on the port* below.
7. **The event admission contract is specified** — identity, authority, epoch and provenance. § *What makes an event admissible* below; it is one decision with four fields, not four decisions.
8. **Every event carries a schema version** and no written event is ever changed, with the redaction event class ([Phase 1](phase1_the_run_bag.md)) as the single stated exception.
9. **The write-path inventory is complete and enumerated in this doc**, split into **fleet-code writes** and **model-issued writes**, each with its named emit mechanism.
10. **The capture path filters secrets at append time** — before any byte reaches the journal root, not merely before the bag is sealed. § *Capture-time filtering* below.
11. **The unwritable-journal signal ships with a committed reader in the same change.** Case (d) below puts a new signal on the typed exit record's channel and on a durable working-record surface. **A signal nobody reads is not a report** — and this fleet has the measured instance: three phases each appended a parent-written observable to the same run log and no committed tool read any of the three. § *When the journal cannot be written* names the reader alongside the signal.
12. **The emit is an ACTIVITY, not a library call each workflow remembers to make** — the same reason [Phase 1](phase1_the_run_bag.md) requirement 11 gives, applied to the write path. **Same split: layer placement, invocation and fail-stop are buildable today; orchestrator-driven retry and recorded execution are port-time.** § *Why the emit is an activity* below.

13. **The bag's tag namespace has a stated extension rule** — **four questions, one requirement**, and the fourth is the one that makes the other three enforceable rather than advisory.
    - **(a) Who may add a `Journal-` tag**, answered separately for the namespace's **two trust classes**, because a flat rule over the prefix either blocks a legitimate descriptive tag or opens the integrity space. The **lifecycle** labels — `Journal-Incomplete`, `Journal-Gap`, `Journal-Redaction`, `Journal-Sealed-At` — are the flags [Phase 4](phase4_rebuild_is_a_test.md), [Phase 6](phase6_cpi_reads_the_journal.md) and [Phase 7](phase7_s3_aggregation.md) branch on, and they are facts about what happened to a run rather than something its opener declares. The **descriptive** ones — the workflow key, the origin repo, its remote, its commit, the worktree — say what the run was. WD Phase 5's sixth tag is descriptive.
    - **(b) What a reader does with a tag it does not recognise.** RFC 8493 permits arbitrary `bag-info.txt` labels and gives readers no guidance for unknown ones, so this is genuinely ours to answer rather than a citation.
    - **(c) Whether bag metadata carries a version of its own, distinct from the per-event version.** **Stated as the open ruling it is** — the fleet declares one version field today, and [Phase 1](phase1_the_run_bag.md) r6 and Phase 1's § *Schema versioning* describe that same field two different ways (*"the event schema version"* and *"the bag-level version"*). A tag addition changes bag metadata and changes no event, so *"bump it"* and *"do not"* are both wrong answers to a question with an ambiguous subject. **This requirement deliberately does not rule which** — nobody has verified that a bump is needed, and settling it here would manufacture a decision no run has made.
    - **(d) BY WHAT MECHANISM an outside component contributes a tag.** The controls that actually hold this namespace are code, not prose: a reserved-label refusal and a folded-value refusal that run on the bag-open path and nowhere else. A component that composes a `bag-info.txt` line itself — or reaches a lower-level tag writer directly — bypasses every one of them, which is how the value-forging class comes back through a second author — [Phase 1](phase1_the_run_bag.md) § *And the rule stayed prose, so it leaked twice more* is that exact history, and its conclusion was that the rule had to become a function and a sweep rather than a sentence. **So the rule names the writer, not just the owner**, and the reserved set is the namespace's stated edge rather than an implementation detail.

    **Trigger: [WD Phase 5](../workflow-decomposition/phase5_configuration_a_run_absorbed.md) r1** — a sixth `Journal-` tag beside the five that exist, and the first field this bag has ever taken from outside. [Phase 1](phase1_the_run_bag.md) r6 gave the schema version a home in `bag-info.txt` and requirement 8 above governs versioning for *events*; **neither says what happens when a different component writes into the bag's tag space**, and today nothing has to — every `Journal-` label is a literal inside the journal package and callers supply values, never labels. **The namespace is closed by construction, and this requirement is the ruling on whether it opens.**

**Requirement 9 is the honest half of requirement 1.** "Every write path" is unverifiable as stated; a named list is verifiable, and [Phase 4](phase4_rebuild_is_a_test.md) is what keeps the list true after this phase closes.

**Deferred on a named trigger, per the sibling component's precedent:** requirement 1 closes when the inventory's paths emit. **A write path added after this phase is that change's responsibility, not a re-opening of this one** — which is exactly what requirement 9 plus Phase 4's failing test are for.

---

## Dependencies

- **[Phase 1](phase1_the_run_bag.md)** — the bag is where events land. Hard dependency.
- **[Phase 9](phase9_one_run_one_identity.md)** — hard dependency on **r1 and r4**, and stated from both sides. It rules who names a run; this phase threads that value down to the emitting children, so what it needs is *what the value is* (r1) and *who owns it* (r4). **Not a dependency on Phase 9 reaching complete, and NOT on r2** — Phase 9 § *Dependencies* is the writer of that scope and states it in the same terms; r2 closes against the Temporal port and r7 waits on a carrier that does not exist, so a gate written against either would stall this phase indefinitely. **This bullet previously also claimed r2's mechanism and said it was "stated from both sides" while Phase 9 said the opposite** — a run briefed from here would have blocked on a requirement Phase 9 had already ruled out of the gate. Its requirements are not restated here.
- **The typed exit record** — built, in daily use, and this component's own ([roadmap § *Absorbed work*](roadmap.md#absorbed-work--the-typed-exit-record-and-the-three-boxes-that-came-with-it)). It supplies two things, and they are different. (i) The **vocabulary** this phase's events reuse (requirement 3). (ii) The **channel** requirement 4 reports an unwritable journal on, which is the one place a journal failure can be announced without needing the journal. Its own contract is stated in [`exit-protocol.md`](../../standards/exit-protocol.md), which remains that contract's single writer.
- **[Phase 2](phase2_content_store.md)** — not a dependency. Events reference artifacts by hash where a content store exists and by SHA/URL where it does not; the emit rule does not wait on the store.
- **[Phase 10](phase10_the_model_issued_harvest.md)** — **not a dependency; a dependent, and it is the half this phase was split into on 2026-08-28.** What moved is the emit *mechanism* for **model-issued** writes — the writes a child performs itself on a prompt instruction, which have no call site to wrap. That is the post-exit harvest, its window and its standing check, now [Phase 10](phase10_the_model_issued_harvest.md) r1–r7. **What stayed is requirement 9's two-half inventory**, whose model-issued rows are that phase's input, plus the event contract, the destination field, the four write-failure cases and the capture-time filter, which [Phase 10](phase10_the_model_issued_harvest.md) consumes and does not restate. **This phase can close with [Phase 10](phase10_the_model_issued_harvest.md) unbuilt**, and the residual is named in § *The write-path inventory* rather than left to be discovered.
- **⚠ [Phase 5](phase5_snapshots_then_retention.md) requirements 2–9 are a PRECONDITION of this phase, not a parallel track.** This phase is the one that makes the journal grow: from Phase 1's 523-byte floor per run to roughly 4.9 MB, on a root every run now hard-depends on. With no retention in place, a full disk stops **every** run including the one an operator would use to diagnose it — [Phase 1](phase1_the_run_bag.md) § *Why this is an activity and not a library* names that cost, and r2–r9 are labelled `(ungated)` precisely so they can land first. Recorded here as a dependency rather than left in Phase 1's prose, because **a rule written only as prose has not once prevented a write path being added without it** — which is this component's own argument for requirement 11, applied to its own sequencing.

---

## What this phase decides

### Completeness is absolute — prose in, code out

**Everything a run authors goes in:** the PR body, every reflection and decision-log comment, the review verdict, the triage, the direction, the approval, the re-run count, the PR number and repo, issues, candidate rows. Anything on any surface.

**The one exclusion is the code diff, and it is excluded for a stated reason rather than to save space: git is already a better store for it.** The journal carries the commit SHA and you go get the diff. That is [Phase 2](phase2_content_store.md)'s by-reference rule applied to the record itself.

**The line is one question: does a better durable store already exist for this artifact type?** For code it does. For the prose a run writes into GitHub it emphatically does not — comments are editable, deletable, unversioned, hosted by a service, **and they are where the reasoning lives.**

**The volume objection is measured, and it does not survive.** The instinct is to fear the byte count. For one full `research_minor` cycle, **all authored text — PR body plus every comment — was 39,772 bytes.** At that rate the authored record for the entire 175-run history is roughly **7 MB**. **The completeness rule costs almost nothing.** *(Those particular bytes are [Phase 10](phase10_the_model_issued_harvest.md)'s to capture — the figure is cited here as the volume argument for the rule, not as this phase's measurement target. § *Measurement* below gives this phase its own denominator.)* The volume in this system lives entirely in the CLI transcript, which is also in the journal and is what [Phase 5](phase5_snapshots_then_retention.md)'s storage budget is actually sized against.

### The destination is a field, not a format

**The journal is identical whether the run wrote into git, a GitHub object, a SQLite file, or an MQTT topic on an edge with no repo.**

That property is not stylistic. It is what makes the record portable across edges, and it is what [Phase 7](phase7_s3_aggregation.md) depends on: a second edge of any type sources the same data from the protocol rather than from a repo. **Git stays for the edge we are building now**, because that edge's memory *is* versioned with code, reviewed in PRs, and travels with a clone — but git is that edge's binding, not the protocol's. Each edge reads and writes whatever surface it needs; **the truth is always the centralized output.** A surface is a local convenience; the journal is the record.

**Why not repo-per-edge.** [`state_passing`](research/raw/state_passing_between_workflow_children.md) established that identity compatibility is not integration — repos without a sync path are isolated memories that *look* joined, which is worse than obviously separate ones. And an edge like Home Assistant has no codebase to version. **It has runs.**

### Stores stay plural; the record is what gets consolidated

Two different things get merged in discussion, and separating them is what makes the rest tractable:

- **The journal** — append-only, immutable, never edited, joined by run id. One location.
- **The working stores** — the four [`tracked/`](../../../tracked/) stores, phase docs, GitHub objects. Mutable, curated, each with its own lifecycle.

**This phase consolidates the record and touches no store's lifecycle.** `state_passing` §4.2 found all six surveyed systems run multiple channels deliberately, each with a selection rule attached — Temporal ships `memo` and then documents that it *"shouldn't store data that's critical to the execution of a Workflow."* **Consolidation is not what mature systems do.**

And our own file surfaces have opposite requirements even after the four-store migration of 2026-08-26: [`tracked/operations/`](../../../tracked/operations/) admits no machine write at all ([Tracked Items §1.2](../../standards/documentation/tracked_items_standard.md)), while [`tracked/candidates/`](../../../tracked/candidates/) is filed, triaged and incremented entirely by dispatches — and §4.2's prune clock runs from *last activity*, so two items in one store have different lifetimes. **No single retention or admission policy can serve all four**, so collapsing them destroys the ones that differ.

### One typed return per step, modality-neutral

`bernstein`'s typed activity boundary is *"the one contract a non-coding modality — research, browser/computer-use, data, ops — participates through as a replayable step"*, and *"every activity returns an artifact plus the hashes needed to replay it."* Every modality returns an `ActivityResult` carrying `kind`, `artifact`, `artifact_hash`, `evidence_set_hash`, `terminal_state`, `reason_code`.

**We take the shape close to as-is, and the reason it transfers is checkable rather than assumed.** The lesson worth keeping separately: *take a mechanism with its reason, then check the reason still holds here.* bernstein's reason is modality-neutrality across a shared scheduler. That is exactly our situation — our children are the same shape (research / build / review / plan) — which is why it transfers nearly whole.

**And we already have a subset of it.** The typed exit record is the shipped starting point — for the *vocabulary*, not for the envelope. The next section is why that distinction is load-bearing rather than pedantic.

### One vocabulary, two contracts — requirement 3, corrected

**The obvious move is to make the journal envelope an extension of the typed exit record, so as not to invent a second contract. That is not possible, and the standard governing that record is what forbids it — recorded here because it is the reading anyone arrives at first.**

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

**The standards-side change this implies is proposed, not written.** `exit-protocol.md` §2's no-speculative-fields rule and §2.5's size bound are correct **for a routing channel** and should say so; as written they read as governing any typed record this fleet emits, which would forbid the durable one. That file is human-in-the-loop under [`standards-governance.md`](../../../config/rules/standards-governance.md), so the amendment is carried at [roadmap § *Standards-amendment candidates*](roadmap.md#standards-amendment-candidates), item 3. **Nothing in this phase waits on it** — the resolution above is a change to what *this* component builds.

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

**It surfaces on two channels that are not the journal, and the second one is why the first is not enough.** The typed exit record plus a non-zero exit status carry it out of the process — **and both are invocation state: read within seconds and then gone**, so a failure reported only there is invisible to every consumer this component builds. **The durable half is the parent's own [working-record](../../guide/memory-model.md) write**: a pull-request comment or a standup-tracker line, which is durable, addressable, and outside the journal root by construction.

**⚠ THIS WRITE IS THE ONE STATED EXCEPTION TO REQUIREMENT 1'S INVARIANT AND TO CASE (b)'s ORDERING, and it has to be stated or the two rules cancel each other.** The durable report is a **store write**. Case (b) says a store write does not happen unless its intent event landed first — and in case (d) the journal is unwritable by definition, so the intent can never land. Read literally, this component's own ordering rule suppresses the only durable signal that the component is broken. **So: the case-(d) failure report is the single store write permitted with no preceding emit, because the emit is precisely the thing that failed.** It is not a hole in the invariant; it is the invariant's boundary condition, and a build that implements case (b) as an unconditional wrapper without this exception ships the failure path silently broken.

**Requirement 11 binds both halves: each signal ships with its reader in the same change.** The exit-record field has a named parent branch that reads it; the working-record line has a named consumer that surfaces it. Adding a field to a channel and leaving the reading to somebody later is how this fleet has already lost three observables, and the one channel this component's failure path depends on is the last place to repeat it.

**And this case is uncountable from the journal, by construction.** [Phase 6](phase6_cpi_reads_the_journal.md) requirement 6 counts gaps by reading gap events, and a run in case (d) produced no gap event, no bag and nothing to count. That is not a defect in Phase 6's measurement; it is a stated limit of it, and Phase 6 says so rather than reporting a gap count that silently excludes the worst failures.

### Why one event per write is not enough

**Write-ahead ordering protects exactly one of the three ways a paired write can break, and the other two produce a journal that is confidently wrong.** Naming them is what makes the intent/completion split obviously necessary rather than ceremony:

| What breaks | What one event per write does | Why it matters |
|---|---|---|
| The journal write fails | Handled — case (b). Neither side is written. | This is the case the ordering was chosen for |
| **The store write fails after a successful emit** | The journal claims content the store never got. [Phase 4](phase4_rebuild_is_a_test.md) replays it and **materialises unpublished content into the store** — turning a failed write into a delayed successful one that no run and no human approved. | The rebuild is supposed to restore what happened, not complete what did not |
| **The activity is retried** | Temporal's execution model runs an activity **at least once**, which is why the [Temporal Standard](../../standards/temporal/temporal_standard.md) §7.1 requires every activity to be idempotent — a retry re-runs *both* side effects. Requirement 7's dedupe-on-identity covers the journal side only, so the store gets a duplicate comment while the journal correctly records one. | Same red diff as the row above, in the opposite direction |

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

**(a) Identity, against an at-least-once execution model.** Temporal executes an activity **at least once**, which is why the [Temporal Standard](../../standards/temporal/temporal_standard.md) §7.1 requires every activity to be idempotent — a retried activity re-runs its side effects. An append-only journal fed by retried activities accumulates **duplicate events**, and [Phase 4](phase4_rebuild_is_a_test.md)'s replay then rebuilds a store with duplicated rows — or worse, passes under a normalisation that hides them. **Every event carries a deterministic identity** (`run_id` + write-path + logical sequence, or a content hash), and **replay is defined as dedupe-on-identity.**

**(b) Authority — who says which `edge_id` an event carries.** Requirement 6 makes the id stable; it does not say who asserts it. Events are naturally built at the edge, so the default implementation is a **self-reported field** — and then any holder of any valid credential can author events attributed to a different edge. In an append-only store that is unfalsifiable after the fact, and after Phase 4 the stores are rebuilt from the journal, so a spoofed attribution replays straight into the [`tracked/`](../../../tracked/) stores. **The rule, stated in two halves because only one of them is buildable today.** The target: an `edge_id` is assigned by an authenticating authority and bound at ingest, and a self-supplied one is rejected rather than trusted. **But there is no ingest tier in this design and there is not going to be one soon** — [Phase 7](phase7_s3_aggregation.md) syncs sealed bags directly to object storage, and a receiver cannot rebind a field inside a sealed bag without invalidating its manifest. **So until an authenticating ingest exists, `edge_id` is SELF-REPORTED and is not an attribution control**, and this doc says so rather than stating a guarantee nothing enforces. The control that does exist in this topology is [Phase 7](phase7_s3_aggregation.md)'s: **a per-machine storage credential scoped to that machine's own prefix, with origin derived from the prefix an object was found under and a prefix/`edge_id` disagreement reported as a finding.** The field stays on the event because a reader needs something to filter on and because a later ingest tier can begin binding it without a schema change.

**(c) A credential epoch, so compromise has a boundary.** *"An id that never rotates"* is right, and it leaves no way to say *"events from edge E between T1 and T2 were authored under a credential that leaked."* Revoking a leaked key then revokes nothing about the record: the injected events replay faithfully. **Every event carries a non-secret `key_id` / credential epoch** — an opaque server-assigned identifier or monotonic counter, **explicitly not derived from the key**, per the ruling below.

**⚠ This is the one admission field with no consumer today, and it is stated the way [Phase 1](phase1_the_run_bag.md) r7's classification slot is rather than left to look like an oversight.** Its consumer is *a replay scoped to exclude an epoch*, which nothing needs until a credential is known to have leaked. **Trigger: the first credential revocation.** It lands in version-1 events anyway because a field absent from version-1 events is absent forever, and an epoch that starts being recorded on the day of a leak cannot bound the events written before it. **[Phase 6](phase6_cpi_reads_the_journal.md) r3's producer/consumer table records this as a knowingly-empty cell with its trigger, not as a blank one.**

**(d) Provenance — what kind of thing this content is by origin.** Fleet-authored prose, operator-authored input, and **bytes fetched from the internet** all enter the journal (the last via tool results in the transcript and wholesale via [Phase 2](phase2_content_store.md)'s content store). Without a trust-class field every downstream reader sees one undifferentiated stream. **[Phase 8](phase8_the_poller.md)'s poller is the consumer that makes this sharp** — it reads a row and *starts work*, so the field it filters on has to exist on the event and survive [Phase 4](phase4_rebuild_is_a_test.md)'s rebuild. **A field absent from version-1 events is absent forever**, which is why it lands here rather than at the phase that first needs it.

### Why the emit is an activity — requirement 12

**An emit is a step the orchestrator invokes, retries and records — not a helper each write path is asked to remember to call.**

**The reason is the same one [Phase 1](phase1_the_run_bag.md) requirement 11 gives and it is worth restating at the write path, because this is where the failure would actually happen.** As a library, the emit rule is advice; the fleet has already lost three observables and one cross-fleet gate to advice. Made structural, the emit's ordering guarantee — the intent event *before* its paired store write — is something the orchestrator enforces rather than something a call site gets right.

**⚠ And this is precisely where the activity boundary stops helping, so the limit is stated rather than assumed.** An activity wrapper reaches **fleet-code writes**. It does not reach **model-issued writes** at all: when the child itself runs `gh pr comment`, there is no call site to wrap, and the mechanism is the post-exit harvest below. It does not reach a write path nobody wrapped in the first place — **[Phase 4](phase4_rebuild_is_a_test.md)'s rebuild test is the guard for that class**, and the two guards are complementary rather than redundant.

**What an activity *is* here is a boundary [Temporal Integration](../temporal-integration/temporal-integration.md) also owns**, and this phase states what it needs — a recorded, retried step whose failure stops the run at a named boundary — rather than the mechanism. Requirement 7(a)'s event identity is the other half of that seam: an activity executes **at least once**, so the journal is a side effect the port has to hold for, and dedupe-on-identity is what discharges [Temporal Standard](../../standards/temporal/temporal_standard.md) §7.1's idempotency rule here.

### Capture-time filtering — requirement 10

The journal is immutable and nothing removes a file from inside a bag except a redaction, so **capture is the only point in the lifecycle where a secret can be cheaply kept out.** After [Phase 4](phase4_rebuild_is_a_test.md) wires the rebuild test to a gate, removing a payload file is a gate change; after Phase 7 it is a bucket-wide purge. **[Phase 5](phase5_snapshots_then_retention.md)'s budget is not a control here** — it is a size limit, not an age limit, so how long a leaked byte survives is unknown rather than bounded.

The transcript carries the literal input of every Bash call, and this repo already treats that as sensitive: `scripts/workflows/temporal/modules/assistant/review_pr/exit_record.py` drops tool input *"at READ TIME, so there is no copy to leak"*, with a test holding the claim. **That control guards a display surface. The journal is a durable one, so the filter runs at APPEND time — before any byte reaches the journal root, not merely before the bag is sealed.** The distinction is load-bearing under write-ahead ordering: the journal now receives every payload *first*, so "before sealed" would leave unfiltered bytes sitting in appended event files for the life of the run, and filtering them at seal time would change written events, which requirement 8 forbids. **The filter cannot run retroactively** — redaction is the only after-the-fact path. And it **emits a placeholder event**, so the record stays complete about the *fact* of a redaction rather than silently shorter. [Phase 1](phase1_the_run_bag.md)'s redaction event class is the after-the-fact complement, for what gets through.

### An API key is a credential, not an identifier

The upstream Django/Temporal pair has to know every edge and how to work with it, and **the API key already associated with an edge is the natural carrier** — it is how the edge authenticates today, so the identity exists and merely needs mirroring outward.

**⚠ But a key is a CREDENTIAL, and credentials rotate.** A journal keyed by API key **orphans an edge's entire history the day the key is rotated**. The key authenticates; **it maps to a stable edge id that never rotates**. One line of design now, an unrecoverable data-modelling mess later — which is why requirement 6 lands in this phase rather than in Phase 7 where the second edge appears.

**This is already a binding rule rather than this component's preference.** [Temporal Standard](../../standards/temporal/temporal_standard.md) §7.5 *Identities are explicit, never derived* states it generally — *wherever a resource is located or targeted by an identity, the identity is an explicit input, not a derivation* — and the `edge_id` is one instance of it.

### An identity is a joint design, not a requirement imposed on the port

**This component lands ahead of the Temporal port, so `edge_id` is not something it inherits — and it is equally not something it dictates.**

**What this component needs is three constraints, and they are all it needs:**

- the identity is **stable across credential rotation** — a journal keyed by a credential orphans a machine's entire history the day the key is rotated;
- it is **never derived from a key**, which rules out `hash(api_key)` on both the rotation ground and the security one;
- it is **present on every event**, because a field absent from version-1 events is absent forever.

**What it does not state is the shape.** Whether the identity is a UUID, a host-scoped name, an operator-assigned label or something the orchestrator already issues is not decided here, and it should not be: [Temporal Integration](../temporal-integration/temporal-integration.md) addresses workers, task queues and schedules, and has its own reasons to name a machine. **Its criteria are an input to the final shape, not a consumer of this one.** That component names no machine or edge id today, so the question is open on both sides and gets settled once rather than twice — in whichever of the two is being built when it comes up, with the other citing it.

**⚠ What these three constraints do NOT cover.** They make an identity *durable*; they say nothing about whether it is *trustworthy*. Sub-decision (b) above is explicit that `edge_id` is self-reported until an authenticating ingest exists, and no amount of stability fixes that. The two are separate properties and this section supplies only the first.

**Security consequence, stated because it constrains the implementation:** the `edge_id` is an identifier and appears in every event; the key is a secret and appears in none. An event carrying a key — or a value derived from a key in a way that survives rotation — is a defect, not a convenience. *(That clause also rules out `hash(api_key)` as an edge id, which is both the rotation bug and a security one: a stored hash of a live credential is an offline confirmation oracle.)*

**⚠ Requirement 6 was split from the mapping at review, because the two have different evidence bars.** A **stable, persisted `edge_id` independent of any credential** is buildable in this repo today and closes on its own. The **key→id mapping** lives in the upstream Django/Temporal pair — a system outside this repo, with no edge API key in this fleet's configuration to point at — so it can only be closed by assertion here. It is deferred on the named trigger *"the upstream pair authenticates an edge."* The no-key-in-events constraint rides on the buildable half, deliberately.

### Schema evolution — decided on day one because it is brutal to retrofit

A journal written under v1 must still replay under v3, forever. Every event-sourced system meets this. **The settled answer: version every event, never mutate a written one, upcast on read.**

The version field's home is Phase 1's `bag-info.txt` — **not `bagit.txt`**, which RFC 8493 requires to be exactly two lines ([Phase 1](phase1_the_run_bag.md) requirement 6 carries the correction and its reason). Requirement 8 is this phase honouring the version on every event. **The detailed mechanism is open** ([roadmap § *Open inputs*](roadmap.md#open-inputs--questions-this-plan-carries-forward-without-answering), item 2) and this phase does not close it — but an unversioned v1 event is unrecoverable, so the rule ships now and the mechanism follows.

**Provenance.** This is **event sourcing**, and it is Temporal's own model applied one level up: event history is the truth, and workflow state is regenerated from it by replay. `bernstein`'s journal is the same shape.

---

## The write-path inventory

*(Requirement 9. Populated when the phase runs — enumerated from the tree, not from memory, with the command that enumerated it.)*

Every row is a surface the fleet writes to, and every row needs an emit. **A surface with no emit is the finding**, and it is what [Phase 4](phase4_rebuild_is_a_test.md) turns into a failing test rather than a note.

**⚠ THE INVENTORY HAS TWO HALVES, AND A TREE SEARCH FINDS ONLY ONE OF THEM.** This is the gap most likely to close this phase with its headline requirement unmet:

- **Fleet-code writes** — a call site in `scripts/` that writes to a store. Enumerable by grep; wrap it and it emits.
- **MODEL-ISSUED writes** — the child itself runs `gh pr comment --body-file …`, instructed by a prompt. **A tree search finds a prompt sentence, not a call site.** And these are the writes this component exists for: the PR body, the decision log, the reflection comment are the first artifacts the synthesis names and the ones the operator's design test is about.

**A build that enumerates only the first half populates the table, wires every row, closes requirement 1, and never emits a single PR comment — and nothing goes red**, because [Phase 4](phase4_rebuild_is_a_test.md) can only test the stores whose emits exist. So the inventory is split by construction, and the second half needs a *mechanism* rather than a wrap.

**⚠ THAT MECHANISM IS NO LONGER THIS PHASE'S — it is [Phase 10](phase10_the_model_issued_harvest.md), and requirement 9 stops at the enumeration.** This phase still owns the inventory and **both** of its halves: every model-issued write is enumerated in the table below with `model-issued` in its second column, and its *Emit mechanism* cell names [Phase 10](phase10_the_model_issued_harvest.md) rather than specifying one here. The post-exit harvest itself — fetching a run's GitHub surfaces after the child exits, the window in which a late comment is missed, the standing check that keeps the harvest honest — is [Phase 10](phase10_the_model_issued_harvest.md) r1–r7, and its reasoning for harvesting rather than intercepting is stated there.

**Enumerating a write path whose emit another phase builds is the point rather than an awkwardness.** The table is what makes [Phase 10](phase10_the_model_issued_harvest.md)'s scope enumerable instead of remembered, and a model-issued row omitted here is a write path that phase never learns about. **The residual is stated rather than hidden:** until [Phase 10](phase10_the_model_issued_harvest.md) lands, this phase's headline claim — *if any store gets it, the journal gets it* — is true of files and false of prose.

| Surface | Written by (fleet-code / model-issued) | Emit mechanism | Rebuildable? |
|---|---|---|---|
| *(enumerated at build time)* | | | |

The five working-record surfaces documented in [`memory-model.md`](../../guide/memory-model.md) §2 are the known floor, not the expected total, and any surface found that `memory-model.md` does not list is itself a finding worth reporting back to that doc.

**⚠ And a third category exists that neither half covers: writes made by no run at all.** `/standup` is a writer and is an interactive session rather than a dispatch; `ready:` on an operations item and `ratification:` on a standards candidate are the operator's alone ([Tracked Items §4](../../standards/documentation/tracked_items_standard.md)); items in every store have been hand-corrected. **[`tracked/operations/`](../../../tracked/operations/) is nothing but this case** — §1.2 forbids any machine write to it. **No tree search finds a human**, and under Phase 4 those edits are writes that must also emit or replay reverts them — which would revert exactly the operator rulings that are the highest-value content in the stores. **For the file binding the natural emit is the git commit itself**, which is consistent with synthesis §10 (each surface's own binding is a local convenience; the journal is the record). Specifying that is part of requirement 9; if it is not specified, [Phase 4](phase4_rebuild_is_a_test.md) scopes its rebuild targets to run-authored content and records the exclusion, rather than shipping a test that is green and wrong.

---

## Implementation checklist

- [ ] Enumerate every write path and populate the inventory above with the command used — **split fleet-code from model-issued**, and give every model-issued row [Phase 10](phase10_the_model_issued_harvest.md) as its emit mechanism rather than specifying one here
- [ ] Specify the third category (out-of-run writes) or hand its exclusion to Phase 4 explicitly
- [ ] Specify the journal event contract as its own contract, and enumerate every concept it shares with the typed exit record — each declared once, in one module, spelled the same in both
- [ ] **Build the write-ahead ordering**: the emit precedes its paired store write, and a failed emit means the store write does not happen
- [ ] **Build the gap event** for writes with no pairable store write — bounded and typed, naming what was lost, when, why and how much — and mark the bag `incomplete`
- [ ] **Report an unwritable journal on the typed exit record and a non-zero exit status**, so the bootstrap case is not silent
- [ ] **Specify the paired write as one unit with two events** — intent then completion (or a typed store-write-failure event) sharing requirement 7's identity, with the store write deriving its idempotency key from that same identity
- [ ] Demonstrate all **four** write-failure cases against a real journal: an unresolvable root refusing to start; a failed intent leaving neither side written; a failed unpairable write producing a gap event on an `incomplete` bag; and an unwritable journal reported on the exit record **and** on a durable working-record surface
- [ ] Demonstrate the **store-write** failure and the **retried-activity** cases: an intent with no completion is not applied by replay, and a retry appends once on both sides
- [ ] Add `edge_id`, `schema_version`, `destination`, the lineage reference, **the event identity, the credential epoch and the provenance class** to the event contract — one change, per requirement 7
- [ ] State that `edge_id` is **self-reported and is not an attribution control** until an authenticating ingest exists, that origin is derived from the storage prefix ([Phase 7](phase7_s3_aggregation.md) r5), and that **no key or key-derived value survives into any event**
- [ ] Define replay's dedupe-on-identity rule so a retried activity cannot double-append
- [ ] State the tag-namespace extension rule in [Phase 1](phase1_the_run_bag.md)'s tag contract, where a contributor already looks — all four clauses of r13, with the lifecycle and descriptive classes answered separately
- [ ] **Make the reader half demonstrable rather than prose**: a bag carrying an unrecognised `Journal-` tag validates, and is *reported* as unrecognised rather than failing or being silently dropped — asserted against the validator's known-tag list, because this phase's own § *Dependencies* argues that a rule written only as prose has never once prevented the thing it forbids
- [ ] Build capture-time filtering, emitting a placeholder event where it fires
- [ ] **Build the emit as an activity** (requirement 12), and confirm the intent-before-store-write ordering is enforced by that boundary rather than by each call site
- [ ] **Name the reader for each unwritable-journal signal** — the parent branch that reads the exit-record field, and the consumer that surfaces the durable working-record line — and land both in this phase's change (requirement 11)
- [ ] **Make a `bag-info.txt` update atomic BEFORE any emitter can call `mark_incomplete` concurrently with `seal`.** [Phase 1](phase1_the_run_bag.md) gives each writer its own payload subfolder so no two writers share a file — but **every writer shares `bag-info.txt`**, and `_set_tag_line` is a read-modify-write that truncates. Nothing calls `seal()` outside tests today, so the race is unreachable until this phase wires emitters; the day it does, a gap record appended while the parent seals is **lost along with the `incomplete` flag**, and the bag then validates clean. That is precisely the *"a bag that lost data reads as complete"* outcome Phase 1's four-state design exists to prevent, arriving through the one file its per-writer isolation does not cover. Write-temp-plus-`os.replace`, or an exclusive lock inside the three tag-line composers. *(Raised by the code-reviewer on PR #99 and placed here rather than fixed there, because the trigger is this phase.)*
- [ ] **Write payload files at `0600` through the bag, not through whatever a caller reaches for.** [`config.yaml`](../../../config.yaml) already states payload files are `0600`; Phase 1 applies `FILE_MODE` only to the tag files it writes itself, because nothing writes payload yet. This phase is what makes that statement true or a lie — and it stops being harmless the moment [Phase 7](phase7_s3_aggregation.md) tars a bag and lands world-readable transcripts somewhere the `0700` root is not protecting them. Add the payload writer to the bag's own surface so an emitter has a correct thing to call.
- [ ] Wire the emit into every inventoried write path
- [ ] Demonstrate a full `research_minor` cycle whose **fleet-code** writes appear in the journal verbatim, against the inventory's fleet-code half. **The PR body and every comment are [Phase 10](phase10_the_model_issued_harvest.md)'s demonstration and not this one's** — claiming them here is precisely how the moved half gets built twice
- [ ] Demonstrate a parallel fan-out round whose outputs each trace back to their input, in real bags (this is [Phase 1](phase1_the_run_bag.md) requirement 3's live evidence, which Phase 1 cannot produce)
- [ ] Demonstrate that a deliberately retried emit appends once
- [ ] Tests per the [Testing Standard](../../standards/testing/README.md): `unit/` for event construction, edge-id mapping, each of the four write-failure cases, and the intent-without-completion rule; `integration/` for one real dispatch's emits
- [ ] Record the measured **fleet-code** authored-byte total with its denominator in § *Measurement* — **not against the 39,772-byte whole-cycle figure**, which counts the half [Phase 10](phase10_the_model_issued_harvest.md) now owns

---

## Measurement

*(Populated when the phase runs.)*

The number that matters is **authored bytes emitted per run against authored bytes written to stores** — they should be equal, and any gap is an unemitted write path.

**⚠ This phase's denominator is NOT the 39,772-byte figure, and the correction matters rather than being pedantic.** That figure (synthesis §2, measured 2026-08-12 over one `research_minor` cycle) counts *the PR body plus every comment* — which is exactly the half that moved to [Phase 10](phase10_the_model_issued_harvest.md) and which this phase's wraps structurally cannot reach. Measured against it, a perfectly correct build of this phase reports as permanently incomplete.

**This phase's denominator is the bytes written by fleet-code call sites**, taken from requirement 9's inventory and summed over the same demonstration cycle. It has to be measured rather than looked up, because no prior measurement split a cycle on that axis. A materially smaller emitted figure means the emit is incomplete; a materially larger one means something is being emitted twice. **The 39,772-byte whole-cycle figure remains the right baseline for [Phase 10](phase10_the_model_issued_harvest.md)**, and only the two together say whether the record is whole.

---

## Notes and open items

- **Completeness cannot be proven by this phase.** Requirement 9's inventory is a snapshot, and a snapshot goes stale the first time a write path is added. **[Phase 4](phase4_rebuild_is_a_test.md) is what makes it stay true**, and this phase is not done in any meaningful sense until Phase 4 runs. They are separate phases because they have separate verifiable outcomes — not because the gap between them is safe.
- **This phase writes no reader for the journal itself.** Under the pair-every-producer-with-its-consumer discipline that is a debt, and [Phase 6](phase6_cpi_reads_the_journal.md) is where it is paid. It is called out here rather than left implicit because this fleet has measured what happens when it is not: three phases each appended a parent-written observable to one log and no committed tool read any of the three. **Requirement 11 is the one exception and it is deliberate** — the unwritable-journal signal is the report of a failure, so shipping it without a reader would mean the failure path itself is the thing nobody sees.

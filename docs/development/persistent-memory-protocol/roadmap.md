# Persistent Memory Protocol — Roadmap

**Status: 📋 PLANNED, NOT STARTED.** Phases 1–4 are unblocked and have phase docs. Phase 6's only gate is inside the sibling Temporal-Integration component, so it has one too. Phases 5, 7 and 8 are gated on named external triggers and carry roadmap rows only.

*Phases are listed in logical rollout order. Phase numbers are creation-order identifiers and do not reflect rollout sequence; execution order across components lives in [`sprint.md`](../sprint.md).*

**On this component's doc shape, and one citation corrected.** [`sprint.md`](../sprint.md) is the authority: *"A component that outgrows one phase gets its own `roadmap.md` plus numbered `phaseN_<name>.md` files … One phase needs no roadmap; do not create one to be tidy."* This component outgrows one phase — see *Why eight phases* below — so it takes that shape, and it is the second here to do so after the [Memory Management Framework](../memory-management-framework/roadmap.md).

The vendored [Documentation Standard](../../standards/documentation/documentation_standard.md) § *Development Planning Files* **§0 Component vs phase** states the same rule and is marked `(binding)` — but [its applicability note excludes that entire section from binding here](../../standards/documentation/README.md) (*"assumes the master-planning layout"*). §0 is therefore applied below as a **pattern worth matching**, and cited as one; `sprint.md` carries the authority. The same treatment the MMF roadmap gives `§Runtime Verification`. *(That §0 is layout-independent while sitting inside a layout-specific exclusion is the third instance of one structural hazard — the [README](../../standards/documentation/README.md) records two earlier ones. Surfaced as [`C-078`](../../standards/architecture/research/candidates.md), not decided here.)*

---

## What this component is

**One durable record of everything the fleet has done, at one location per edge, that can rebuild every other store from itself.**

Today the fleet's memory is five curated surfaces plus a run log. The surfaces are read; the run log is 262 MB across 125 days with no retention rule and — until [MMF Phase 6](../memory-management-framework/phase6_read_what_it_writes.md) — no reader. Neither half is a *record*: the surfaces hold current state and drop the history behind it, and the log holds history nothing can reconstruct state from.

The protocol closes that. Every write to any store also emits to a **journal** — append-only, immutable, joined by run id — and the journal carries enough to regenerate what the store holds. The stores stop being sources of truth and become **projections**. The design test is the operator's, quoted from the synthesis:

> *"If I have a question it always starts in the journal. I rarely have to go to another source, because I know if I do it is just duplicated info from the journal anyway."*

**This component owns:** the journal's on-disk shape and its manifest; the emit rule and what completeness means; the content store and offline hash verification; the rebuild test that makes completeness enforceable; snapshots, rotation and the two-tier retention split; the stable edge identity the record is keyed by; and cross-edge aggregation when a second edge exists.

**It does not own:** the typed parent↔child handoff and its fail-safe contract (built — [MMF Phase 3](../memory-management-framework/phase3_typed_exit_record.md)); the Kind 1 interface and its five properties (documented — [`memory-model.md`](../../guide/memory-model.md)); where a *finding* goes ([`finding-routing.md`](../../standards/finding-routing.md)); the Temporal port ([`temporal-integration/`](../temporal-integration/temporal-integration.md)); or the fleet's deployment automation ([`C-076`](../../standards/architecture/research/candidates.md)).

**Evidence.** [`research/synthesis.md`](research/synthesis.md) is the decision record this plan is built from — 15 adopted concepts with their provenance, written by an operator+PM session on 2026-08-12. **It states in its own header that it is not a research artifact and must not be cited as evidence**, so every claim below cites what it points at: [`state_passing_between_workflow_children.md`](research/raw/state_passing_between_workflow_children.md) (Critic: PASS-WITH-FIXES, 2026-08-12) and [`bernstein_capability_mining.md`](../../standards/architecture/research/raw/bernstein_capability_mining.md). [`cross_node_memory_protocol.md`](research/raw/cross_node_memory_protocol.md) is SUPERSEDED by its own header; its two surviving findings are re-grounded elsewhere and it is cited only where the synthesis says it survives.

---

## Why this is a component and not a phase of the Memory Management Framework

[`C-074`](../../standards/architecture/research/candidates.md) is the open candidate for exactly this question, and the research that surfaced it declined to rule: [`cross_node_memory_protocol.md`](research/raw/cross_node_memory_protocol.md) §5.1 records that **no source bears on component-vs-phase**, and names the trap — *a long mechanism list reads as an argument for a dedicated component while being equally consistent with a phase*. So the argument below is deliberately **not** "there are fifteen concepts." It is a comparison of two stated ownership claims.

*(That paper is SUPERSEDED by its own header, so citing it needs a reason. It is cited here only for the fact that **the evidence does not decide this question** — a negative finding about the paper's own limits, which supersession does not disturb — and `C-074`'s Note quotes the same passage. It is not relied on for anything the plan builds. [`state_passing`](research/raw/state_passing_between_workflow_children.md) §5.1 makes the same point about its own decision in weaker form and is not superseded.)*

**The test** (§0, and `sprint.md`'s *a component is a folder*): *does this work stand up a new domain, or extend an existing one?*

**MMF states its own scope**, in [its roadmap](../memory-management-framework/roadmap.md): *"the typed record and its schema; what a parent may route on without a model in the loop; how that relates to the durable human-readable record already in git; and the fail-safe contract when the record is absent or malformed."*

All four are properties of **a handoff between two steps of one run** — a channel that is fresh per invocation, read within seconds, and discarded. This component's subject is a **store**: a root path, a bag per run, a checksum manifest, a content-addressed byte cache, snapshots, rotation, a stable edge identity, and aggregation across machines. **Not one of MMF's four clauses reaches any of those**, and no phase of MMF could acquire them without restating its scope sentence.

Two further checks, each against an artifact rather than an impression:

- **It inverts authority over MMF's own outputs.** Under §2 of the synthesis, `candidates.md` and `direction.md` become materialized views of the journal. A phase does not change what its component's other phases are the truth of.
- **The journal is not a Kind 1 record, so it cannot be that interface's next binding.** [`memory-model.md`](../../guide/memory-model.md) §1 requires all five properties, and the journal fails two of them by design: it has **no to-do bit** (property 4 — a journal event is history and never *needs* anything), and it has **no selection rule**, because §1.1's whole question — *which surface does this outcome go to* — presupposes a mutable, curated store. It is also immutable and never edited, where every Kind 1 surface is edited or closed. **The journal is the substrate the Kind 1 surfaces are rebuilt from, not another one of them.**

**The strongest counter-reading, stated so the operator sees it rather than only the case for.** [MMF Phase 2](../memory-management-framework/phase2_kind1_framework.md) delivered Kind 1 as a **substrate-free interface** — `memory-model.md` §1 says outright *"No property below is stated in terms of GitHub, git, a file or a URL … That is the claim, and it is the one a grep can check"* — and it already names *"an edge device, a robot, a datacenter node"* as needing durable memory without a PR. Read that way, the protocol is simply **Kind 1's third binding**, which would make it a phase of the component that owns the interface. That is a serious reading and it is the one to beat.

**It is rejected on the property test above, not on scope aesthetics.** A binding of an interface must satisfy the interface. The journal satisfies three of five properties and contradicts a fourth. What *is* a third Kind 1 binding is the set of stores the journal rebuilds — and those already exist. *(Two earlier supporting checks were dropped at review: **"MMF is six-of-six complete"** — MMF itself added a sixth phase to a shipped component on 2026-08-10, so that argument would forbid a move MMF made three days before this plan; and **"MMF's binding is git"** — which is contradicted by the substrate-free framing above and, cited as evidence for separation, argues the opposite. Recorded rather than silently removed, so nobody re-derives them.)*

**The one genuine overlap is synthesis §3** — one typed return per step, which the synthesis itself calls *"the extension of something shipped"* ([MMF Phase 3](../memory-management-framework/phase3_typed_exit_record.md)). That is a **dependency across components**, which a roadmap declares explicitly (§ *Dependencies* below), not a reason to fold one into the other.

**What this settles, and what it does not.** The reasoning above settles `C-074`'s substance and this plan implements it. **`C-074`'s `decision` flag is left blank**, because setting it is `plan-sprint`'s write and the ruling is the operator's ([`standards-governance.md`](../../../config/rules/standards-governance.md) § *Standards governance*). Its Note now points here. If the operator rules the other way, the remedy is mechanical: the phase docs move into `memory-management-framework/` and renumber from 7.

---

## Why eight phases

The test [`sprint.md`](../sprint.md) and §0 both apply: **a phase ends where something works end-to-end, and a phase that grows past one verifiable outcome gets split.** Applying it produced eight — seven at draft, and an eighth when review applied the same test to a phase that had grown two bars — and four of the splits are load-bearing:

1. **The container is separable from what fills it.** Phase 1 delivers a valid bag on disk and nothing else. Every later phase writes into it, so getting the shape wrong is expensive to unwind — and a bag either validates or it does not, which is a demonstrable outcome with no judgement in it.
2. **The emit rule and its enforcement are two phases, deliberately.** Phase 3 makes every write path emit; Phase 4 proves the journal can rebuild the store. Folding 4 into 3 would make it the last checkbox of a phase whose headline was already met — and [MMF Phase 6](../memory-management-framework/phase6_read_what_it_writes.md) is the measured record of what happens then: *three phases shipped an emitter and none shipped a reader*. This plan does not repeat that.
3. **Snapshots precede rotation inside one phase, and cannot be split from it.** Rotation without a snapshot to stop at is a data-loss bug, not an incomplete feature, because under §2 the journal is the only thing that can rebuild a store. They ship together or neither ships.

4. **The reader and the scheduler are two phases, because only one of them needs a server.** At draft these were one phase, gated on Temporal — which would have put this component's *only consumer* behind a server nobody has stood up, for four phases of producers. That is the failure at item 2 with a longer fuse, committed by the plan that cites it. Split at review: **Phase 6** (CPI reads the journal — needs a journal and a Python `review-runs`, no scheduler) and **Phase 8** (the poller — needs schedules).

The remaining splits follow the gates: Phase 2 is independent of everything and is the cheapest item on the page; Phase 5 needs a server; Phase 7 needs a second edge that does not exist.

**Phase docs exist for phases 1–4 and 6.** `sprint.md`: *"Phase docs are written when a sprint is picked up, not in advance. A detailed plan for work that has not started yet is a guess that ages badly."* **This plan applies an adjacent test rather than that one, and says so rather than letting the divergence pass silently:** `sprint.md` conditions doc-writing on *sprint pickup*, and this component has no sprint row yet (§ *Open inputs*, item 4) — read literally, none of these docs would exist. The line drawn instead: **a phase doc exists iff the phase has no gate outside this component**, because the ungated phases are exactly the ones a sprint row would name. Phases 5, 7 and 8 each name an external gate below; their docs are written when the gate opens. Phases 5 and 8 orchestrate Temporal and Phase 7 orchestrates S3, so each will need a `§Runtime Verification` block when written — adopted as a pattern, per the doc-shape note above.

**The checkboxes below summarise each phase doc's numbered requirements; they do not reproduce them, and the phase doc is authoritative.** Phase 1 has 5 boxes over 9 requirements, Phase 2 has 5 over 7, Phase 3 has 5 over 9, Phase 4 has 4 over 6. **A dispatch briefed from this section alone will under-size every one of them** — most consequentially Phase 3, whose write-path inventory (its own *"honest half of requirement 1"*) has no box here. Brief from the phase doc.

---

## Phases

### [Phase 1 — The journal root and the run bag](phase1_the_run_bag.md)

Stands up the container: one configurable root per edge, one folder per run keyed by `run_id`, one subfolder per concurrent child, and a **BagIt (RFC 8493)** manifest so the protocol can read a folder rather than guess at it by file extension. Delivers the payload spec — what goes in the journal and what stays out, with the reason for each exclusion — and records *no database* as a decision with its revisit trigger rather than as an omission. Nothing emits into it yet; the outcome is a bag that validates.

- [ ] The root is a **config value** with a documented default per deployment shape, and nothing in the implementation depends on a home directory existing
- [ ] A run's record is one folder keyed by `run_id` — **never by path** — with one subfolder per concurrent child, so no two writers share a file
- [ ] The folder is a valid BagIt bag: `data/` payload, `manifest-sha256.txt` over every payload file, `bagit.txt` declaring version and encoding; a validator re-hashes the payload and reports pass/fail
- [ ] `bagit.txt` carries the **event schema version**, and the versioning rule is written down: version every event, never mutate a written one, upcast on read
- [ ] The payload spec is stated as a table with a reason per row — authored output, transcript and execution facts in; code diffs out (commit SHA); Temporal history out (it expires)

### [Phase 2 — The content store and offline hash verification](phase2_content_store.md)

Stores the bytes behind every claim, addressed by hash, and ships a `verify` that resolves every citation **from the content store alone** — re-hashing to detect an altered source and confirming the quoted span still occurs. It holds with the network disabled. Three payoffs from one mechanism: it mechanises what `research-critic` does by hand, it makes a shared multi-edge store trustworthy because a record can be *proven* unaltered, and an `evidence_set_hash` equal to a prior stage's is a no-new-evidence stop condition **computed rather than judged**.

- [ ] Every cited artifact is stored by content hash under the journal root; nothing is inlined by value
- [ ] `verify` runs against a real prior run **with the network disabled** and distinguishes verified / missing / tampered by exit code
- [ ] A deliberately altered stored byte is detected, and a quoted span that no longer occurs in its source is reported as a distinct failure from a missing source
- [ ] `evidence_set_hash` is computed per stage and its equality with the prior stage's is exposed as a stop condition
- [ ] Code diffs are carried as a commit SHA and resolved from git, never copied into the store

### [Phase 3 — The emit rule: every write to any store also emits to the journal](phase3_the_emit_rule.md)

The core rule, and it is absolute: **if any store gets it, the journal gets it, verbatim.** A PR body, every reflection and decision-log comment, the review verdict, the triage, the approval, the re-run count, issues, candidate rows. The destination is a **field, not a format** — the journal is identical whether the run wrote into git, a GitHub object, or an MQTT topic on an edge with no repo, which is the property cross-edge aggregation later depends on. Every emitted item carries lineage (which input produced it) and a **stable edge id that never rotates**.

- [ ] Every write path to every store emits a journal event carrying the authored content verbatim, with the destination store as a field
- [ ] The event envelope is modality-neutral and extends [MMF Phase 3](../memory-management-framework/phase3_typed_exit_record.md)'s typed exit record rather than inventing a second contract
- [ ] Every emitted item records which input item produced it, so a fan-out round can be traced output-to-input
- [ ] Every event carries a stable `edge_id`; **the API key authenticates and maps to it and is never the key itself**
- [ ] Measured against the synthesis's 39,772-byte baseline for one `research_minor` cycle, and the observed figure reported with its denominator

### [Phase 4 — Rebuildability is a test](phase4_rebuild_is_a_test.md)

Replays the journal into a scratch directory and diffs the result against the live store. This is what makes Phase 3 enforceable: without it, completeness degrades silently the first time a write path is added and its emit is forgotten — a failure this repo has produced in several other forms. The test belongs in the merge-path gate, so a missing emit goes red rather than unnoticed.

- [ ] Replay of the journal reproduces `candidates.md` and `direction.md`, either byte-identical or under a normalisation that is stated and justified
- [ ] Deleting one emit from a write path makes the test **fail**, demonstrated
- [ ] The test runs in `.github/workflows/tests.yml` and is wired into [`testing/run-all.sh`](../../../testing/run-all.sh)
- [ ] A store the journal cannot rebuild is named as such, with the reason, rather than silently excluded from the test

### [Phase 6 — CPI reads the journal](phase6_cpi_reads_the_journal.md)

Moves CPI's evidence sweep onto the journal, so it reads one store instead of walking a per-repo pile of JSONL. **This is the consumer for everything Phases 1–4 produce, and it is listed here — ahead of Phase 5 — because it needs no scheduler and no server.** The discipline it enforces is the one the synthesis names: **pair every producer with its consumer.** A producer with no consumer is how 262 MB accumulated unread, and [MMF Phase 6](../memory-management-framework/phase6_read_what_it_writes.md) is the measured local record of three emitters shipping against zero readers.

- [ ] CPI's evidence sweep sources the journal, and produces the same findings as the incumbent sweep on one overlapping window
- [ ] **Every producer shipped by Phases 1–4 has a named, committed consumer** — enumerated, not asserted
- [ ] The wall-clock of the cross-run sweep is measured against journal size, and reported as the first real test of Phase 1's no-database decision
- [ ] Cross-edge CPI is explicitly **not** built here; CPI stays on Edge1

### Phase 5 — Snapshots, then retention *(gated: Temporal server)*

**Phase doc written when picked up.** Materializes every store's state at a point in time into the journal, and only then rotates. Rotation deletes whole run folders oldest-first and **never past the last snapshot** — that ordering is the whole phase, because under §2 the journal is the only thing that can regenerate a store, so a pruning rule is a decision about what the fleet can no longer reconstruct. The two halves of the record get different rules: the authored record (≈7 MB for the entire 175-run history) never prunes; the transcript (99.2% of the bytes, value decaying within weeks) prunes on a schedule.

**Gate:** rotation is a scheduled Temporal workflow plus a config variable — it needs [`temporal-integration`](../temporal-integration/temporal-integration.md) *Stand up the Temporal server*.

- [ ] A snapshot materializes every store's state into the journal, addressable as the replay floor
- [ ] A rotation dry-run **refuses** to cross the last snapshot, demonstrated against a real journal
- [ ] The authored record and the transcript carry separate stated retention rules, and the transcript prunes inside a run folder without destroying the record
- [ ] A replay from the last snapshot forward rebuilds a store, so Phase 4's test still passes after a rotation
- [ ] **The storage budget and the snapshot cadence are recorded as ruled numbers** — this box stays unchecked until the operator rules them (see § *Open inputs*)

### Phase 8 — The poller *(gated: Temporal schedules)*

**Phase doc written when picked up.** No new cue surface is needed — `candidates.md`'s `status: open` **is** the to-do bit, and [`memory-model.md`](../../guide/memory-model.md) §1 property 4 already makes a to-do bit a required property of a durable record. What is missing is the poller: a scheduled workflow that queries state and starts children.

**Gate:** Temporal schedules (same server as Phase 5), and a journal with retention so a poller is not reading an unbounded tree. *(Split from Phase 6 at review: only the poller needs a scheduler, and bundling the two would have gated this component's only consumer behind a server nobody has stood up — reproducing the failure the plan cites MMF Phase 6 against.)*

- [ ] A scheduled workflow reads a store's to-do bit and starts a child with no human trigger, demonstrated end-to-end on one real cue
- [ ] The cue is read from an existing surface; no new cue surface is created
- [ ] A cue that fires twice starts one child, not two

### Phase 7 — S3 aggregation, local-write-first *(gated: a second edge, and a classification ruling)*

**Phase doc written when picked up, and it will likely split.** The synthesis sizes this at *"a couple of phases or its own sprint"* — an involved integration, not a feature — so this row is a placeholder that gets split at the point its gate opens. Layout under `<machine_id>` + `<run_id>`; the local file is the source of truth at write time and ships asynchronously, so the edge works when the bucket is unreachable. Syncing a bag tree to S3 is a boring directory sync, which is the payoff of Phase 1's shape. CPI then reads the bucket instead of one local journal — **same reader, different input**, which is why Phase 6 must not be built as throwaway.

**Three gates, and the last two are separate rulings that were nearly collapsed into one:**

- **A second edge that actually produces runs.** Building cross-edge aggregation before one exists is the speculative-generality trap `state_passing` §5.2 already caught this fleet in once.
- **An EGRESS ruling — per-field classification.** *What may leave this edge?* Shipping raw records to a store every edge reads crosses a line nobody has drawn. It is smaller than it looks — the journal's contents were *deliberately* written to a durable surface and most of it is already public in a GitHub PR, so the question is per-field — but it is still a decision and it still gates a shared store.
- **An INGRESS ruling — trust in another edge's records.** *What may this edge believe?* **This is what the [heartbeat pollution paper](https://arxiv.org/pdf/2603.23064) is actually about, and collapsing it into the ruling above is how it gets skipped.** That paper measured pollution reaching durable memory at rates up to 91%, with **prompt injection not required — ordinary misinformation sufficed.** That is an *integrity* threat, not a disclosure one: a build could classify every field correctly and still ship a reader that treats another edge's records as fleet history. Under [Phase 4](phase4_rebuild_is_a_test.md) the stores are **projections of the journal**, so a polluted record replays straight into `candidates.md` and `direction.md`.

- [ ] Bags ship to `<machine_id>/<run_id>` asynchronously; the edge continues to run with the bucket unreachable
- [ ] A shipped bag validates against its own manifest after transfer, using Phase 2's mechanism — **and the content-store objects a bag references ship with it**, or the validation is knowingly partial and the doc says so
- [ ] CPI reads the bucket with **no change to the reader** written in Phase 6
- [ ] **The egress classification ruling — this box stays unchecked until the operator rules it** (§ *Open inputs*)
- [ ] **The ingress trust ruling — this box stays unchecked until the operator rules it.** It states what a reader may *act on* versus merely display, and whether records are origin-authenticated. A BagIt manifest is regenerable by any writer, so it proves integrity against **accident and transport corruption**, not against a party with write access — which is exactly the party a shared store introduces

---

## Where each adopted concept is planned

All fifteen concepts in [`research/synthesis.md`](research/synthesis.md) are phased. Nothing is deferred out of the plan.

**Read the third column as *"which numbered requirement carries it"*, not as a topic tag.** Where a cell says **(stated)**, the concept is a recorded decision in that phase's prose rather than a checkable requirement — that is honest and it is different, because a reviewer checking coverage against a requirement list will not find it.

| § | Concept | Phase |
|---|---|---|
| 1 | Stores stay plural; the RECORD is what gets consolidated | **3** (§ *Stores stay plural*, stated), 1 (payload spec, r7) |
| 2 | Every write also emits to the journal, completely; the journal rebuilds the store; rebuildability is a test | 1 (r6, versioning), 3 (r1, r7), 4 (r1, r2) |
| 3 | One typed return per step, modality-neutral | 3 (r3) |
| 4 | Artifact by reference plus a hash, never content by value | 1 (r7, diffs as SHA), 2 (r1, r6) |
| 5 | Lineage on every emitted item | 3 (r4) |
| 6 | Content store, with offline hash re-verification | 2 (r1–r4) |
| 7 | Each artifact keeps its own format — and no database, deliberately | 1 (r8, no-database) · 1 (format-per-artifact, **stated**) |
| 8 | The accumulated log is an asset; pruning is small, planned work | 5 |
| 9 | Cue surfaces already exist; what is missing is the poller — and a stable edge id | 3 (r5, edge id), **8** (poller) |
| 10 | Git is the coding edge's binding, not the protocol's | 3 (r2, destination as a field), 7 |
| 11 | S3 as the aggregation point, with a local-first write | 7 |
| 12 | Temporal's own store is telemetry, not memory | 1 (r7, contents table), 5 (split retention) |
| 13 | CPI stays on Edge1 until a second edge produces runs | **6** (step 1), 7 (steps 2–3) |
| 14 | One location, a folder per run, many formats, and a BagIt manifest | 1 (r2, r4) |
| 15 | Concurrent children write to their own subfolder | 1 (r3) |

---

## Dependencies

**On other components:**

- **[Memory Management Framework](../memory-management-framework/roadmap.md)** — Phase 3 supplies the typed exit record this component's envelope extends (synthesis §3); Phase 2 supplies [`memory-model.md`](../../guide/memory-model.md), whose five properties and to-do bit Phase 8's poller reads. Both are **complete**, so neither blocks.
- **[Temporal Integration](../temporal-integration/temporal-integration.md)** — two separate items, and conflating them is what gated this component's consumer behind a server at draft:
  - *Stand up the Temporal server* gates Phases 5 and 8. **Nothing in Phases 1–4 or 6 needs it.**
  - ***Port `review-runs`*** gates **Phase 6**. The CPI evidence sweep exists today only as `scripts/workflows/review-runs.sh` in the frozen bash fleet, which may not be modified — so Phase 6 cannot be built until the Python port lands. Surfaced by review; it was undeclared in the draft.
- **[`C-076`](../../standards/architecture/research/candidates.md)** — deployment automation is a dependency of §13's redeploy path, sized as its own sprint, and is explicitly **not** in this component.

**On rulings:** Phase 5 needs the storage budget and the snapshot cadence; Phase 7 needs both the egress and the ingress rulings. All are below.

---

## Open inputs — questions this plan carries forward without answering

The synthesis's § *What this does NOT settle* is the source. These are inputs to the build, not deferred work: each is named at the phase that consumes it, and the corresponding requirement stays unchecked with prose saying why — **built is not proven, and a requirement whose evidence cannot exist yet is not checked.**

**Operator calls — this plan does not make them:**

1. **The storage budget and the snapshot cadence** (Phase 5). The mechanism is settled: rotate whole run folders oldest-first, never past the last snapshot. The two numbers are not — *how much disk the journal may hold* and *how often state is materialized* — and **they trade against each other**: a longer cadence needs more disk to stay rebuildable, a tighter budget forces a tighter cadence. Neither is derivable from evidence; both are preferences.
2. **What an edge actually is** (Phase 1, and nearer than the rest). Home-directory placement suits the edge we have because Claude Code itself requires a user context. An edge that is not a full Linux environment — HAOS is the live example — may have **no user account**, and may need a sidecar to run at all. **This does not block the build**: Phase 1's first requirement is that the root is a config value and nothing depends on a home directory, which is the buildable half. The definition is the unbuildable half.
3. **The egress and ingress rulings** (Phase 7). Two rulings, not one — *what may leave this edge* and *what may this edge believe*. Both are named at Phase 7 with their own unchecked box. **Moved here from "no owner yet" at review**, because a security-bearing gate whose owner is unnamed is a gate the building run opens from priors, which is the failure [`C-079`](../../standards/architecture/research/candidates.md) predicts in its own words. The research that would inform them is `C-079`; the ruling is still the operator's.
4. **A `sprint.md` entry for this component.** `sprint.md` is operator-only and this plan does not write it. Without a row there the component is planned but unreachable from the file operators are told to start at, and unscheduled against everything else. Surfaced in this plan's PR body as a sprint-item candidate; it lands by operator edit. *(This is the one open input that is not a design question — it is a placement the governance rule reserves to a human.)*

**Open questions with no owner yet:**

5. **The three questions the journal must answer.** The operator's, asked in session and not yet answered. They decide the format, and nothing else does — and §2's rebuild test raises the stakes, because the journal now has to carry enough to *regenerate* a store rather than merely describe a run. Phase 1's payload spec is written against the rebuild test in the absence of the three questions; if they arrive and disagree with it, Phase 1's spec is what changes.
6. **Event schema versioning, in detail** (Phases 1, 3). The approach is settled — version, never mutate, upcast on read. The mechanism is not.
7. **Journal format at this volume, and redaction/classification for records crossing a trust boundary.** Both are genuine research questions and the strongest candidates for a full research cycle on this topic. Placed as [`C-079`](../../standards/architecture/research/candidates.md), which covers both the egress and the ingress halves of item 3.
8. **Whether the Kind-1 / Kind-2 cut should be re-drawn.** [`state_passing`](research/raw/state_passing_between_workflow_children.md) §4.3.4 established that the two kinds cover three of eight channels and that *lifecycle* discriminates where *audience* does not — and explicitly declined to rule. Nothing in Phases 1–8 depends on the answer.

---

## What is deliberately not built

- **A database.** `state_passing` §4.3.3's format table has one empty row — *queries over accumulated history* — and the reflex is to fill it with SQLite. A per-run folder tree with a checksum manifest answers the questions we actually have. **And a database would be a projection**, which §2 already makes rebuildable from the journal — so this is a future build opportunity **with no refactor cost**. Revisit on a real query, not on a feeling that a record ought to live in a database.
- **An invented manifest format.** BagIt (RFC 8493) exists, its manifest *is* checksums, its `bagit.txt` declares a version, and bags transfer as loose trees or serialized. Three of this plan's requirements come free with it.
- **Cross-edge anything, before a second edge produces runs.** Phase 7's gate, and it is the same trap `state_passing` §5.2 caught once already.
- **Reading Temporal's own history as memory.** Its identity scheme is bounded by retention and continue-as-new starts a fresh history — an execution log with a TTL, not a durable record. Where CPI needs something Temporal knows, **the fleet emits it into the journal per step, and the failure path writes a terminal event.** *(The synthesis phrases this as "at completion"; that phrasing is corrected here, because a terminated, timed-out or crashed run never reaches completion — and failed runs are CPI's primary input, so a completion-only emit loses exactly the runs the record exists for. Per-step also matches synthesis §3, which this plan adopts: one typed return per **step**, not per workflow.)*

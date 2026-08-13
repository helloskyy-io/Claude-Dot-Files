# Persistent Memory Protocol — Roadmap

**Status: 📋 PLANNED, NOT STARTED.** Phases 1–4 are unblocked and have phase docs. Phases 5–7 are gated on named external triggers and carry roadmap rows only.

*Phases are listed in logical rollout order. Phase numbers are creation-order identifiers and do not reflect rollout sequence; execution order across components lives in [`sprint.md`](../sprint.md).*

**On this component's doc shape, and one citation corrected.** [`sprint.md`](../sprint.md) is the authority: *"A component that outgrows one phase gets its own `roadmap.md` plus numbered `phaseN_<name>.md` files … One phase needs no roadmap; do not create one to be tidy."* This component outgrows one phase — see *Why seven phases* below — so it takes that shape, and it is the second here to do so after the [Memory Management Framework](../memory-management-framework/roadmap.md).

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

[`C-074`](../../standards/architecture/research/candidates.md) is the open candidate for exactly this question, and the research that surfaced it declined to rule: `cross_node_memory_protocol.md` §5.1 records that **no source bears on component-vs-phase**, and names the trap — *a long mechanism list reads as an argument for a dedicated component while being equally consistent with a phase*. So the argument below is deliberately **not** "there are fifteen concepts." It is a comparison of two stated ownership claims.

**The test** (§0, and `sprint.md`'s *a component is a folder*): *does this work stand up a new domain, or extend an existing one?*

**MMF states its own scope**, in [its roadmap](../memory-management-framework/roadmap.md): *"the typed record and its schema; what a parent may route on without a model in the loop; how that relates to the durable human-readable record already in git; and the fail-safe contract when the record is absent or malformed."*

All four are properties of **a handoff between two steps of one run** — a channel that is fresh per invocation, read within seconds, and discarded. This component's subject is a **store**: a root path, a bag per run, a checksum manifest, a content-addressed byte cache, snapshots, rotation, a stable edge identity, and aggregation across machines. **Not one of MMF's four clauses reaches any of those**, and no phase of MMF could acquire them without restating its scope sentence.

Three further checks, each against an artifact rather than an impression:

- **It inverts authority over MMF's own outputs.** Under §2 of the synthesis, `candidates.md` and `direction.md` become materialized views of the journal. A phase does not change what its component's other phases are the truth of.
- **MMF is six-of-six complete** (`sprint.md` § Memory Management Framework, all six `[x]`). Adding a seventh phase to a closed component makes its completion claim untrue, and there is no trigger-gated work left in it to attach to.
- **It fails MMF's substrate assumption.** MMF's Kind 1 binding is git and GitHub. Synthesis §10 rules that **git is the coding edge's binding, not the protocol's** — an edge like Home Assistant has no codebase to version, and the [problem statement](../../standards/architecture/problem-statement.md) makes *"nothing may assume the coding edge"* a standing consequence. A component whose scope sentence names git cannot host work whose first principle is that git is optional.

**The one genuine overlap is synthesis §3** — one typed return per step, which the synthesis itself calls *"the extension of something shipped"* ([MMF Phase 3](../memory-management-framework/phase3_typed_exit_record.md)). That is a **dependency across components**, which a roadmap declares explicitly (§ *Dependencies* below), not a reason to fold one into the other.

**What this settles, and what it does not.** The reasoning above settles `C-074`'s substance and this plan implements it. **`C-074`'s `decision` flag is left blank**, because setting it is `plan-sprint`'s write and the ruling is the operator's ([`standards-governance.md`](../../../config/rules/standards-governance.md) § *Standards governance*). Its Note now points here. If the operator rules the other way, the remedy is mechanical: the phase docs move into `memory-management-framework/` and renumber from 7.

---

## Why seven phases

The test [`sprint.md`](../sprint.md) and §0 both apply: **a phase ends where something works end-to-end, and a phase that grows past one verifiable outcome gets split.** Applying it produced seven, and three of the splits are load-bearing:

1. **The container is separable from what fills it.** Phase 1 delivers a valid bag on disk and nothing else. Every later phase writes into it, so getting the shape wrong is expensive to unwind — and a bag either validates or it does not, which is a demonstrable outcome with no judgement in it.
2. **The emit rule and its enforcement are two phases, deliberately.** Phase 3 makes every write path emit; Phase 4 proves the journal can rebuild the store. Folding 4 into 3 would make it the last checkbox of a phase whose headline was already met — and [MMF Phase 6](../memory-management-framework/phase6_read_what_it_writes.md) is the measured record of what happens then: *three phases shipped an emitter and none shipped a reader*. This plan does not repeat that.
3. **Snapshots precede rotation inside one phase, and cannot be split from it.** Rotation without a snapshot to stop at is a data-loss bug, not an incomplete feature, because under §2 the journal is the only thing that can rebuild a store. They ship together or neither ships.

The remaining splits follow the gates: Phase 2 is independent of everything and is the cheapest item on the page; Phase 6 needs a scheduler; Phase 7 needs a second edge that does not exist.

**Phase docs exist for phases 1–4 only.** `sprint.md`: *"Phase docs are written when a sprint is picked up, not in advance. A detailed plan for work that has not started yet is a guess that ages badly."* The line drawn here: **a phase doc exists iff the phase is unblocked today.** Phases 5–7 each name their gate below; their docs are written when the gate opens. Phases 5 and 6 orchestrate Temporal and Phase 7 orchestrates S3, so each will need a `§Runtime Verification` block when written — adopted as a pattern, per the doc-shape note above.

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

### Phase 5 — Snapshots, then retention *(gated: Temporal server)*

**Phase doc written when picked up.** Materializes every store's state at a point in time into the journal, and only then rotates. Rotation deletes whole run folders oldest-first and **never past the last snapshot** — that ordering is the whole phase, because under §2 the journal is the only thing that can regenerate a store, so a pruning rule is a decision about what the fleet can no longer reconstruct. The two halves of the record get different rules: the authored record (≈7 MB for the entire 175-run history) never prunes; the transcript (99.2% of the bytes, value decaying within weeks) prunes on a schedule.

**Gate:** rotation is a scheduled Temporal workflow plus a config variable — it needs [`temporal-integration`](../temporal-integration/temporal-integration.md) *Stand up the Temporal server*.

- [ ] A snapshot materializes every store's state into the journal, addressable as the replay floor
- [ ] A rotation dry-run **refuses** to cross the last snapshot, demonstrated against a real journal
- [ ] The authored record and the transcript carry separate stated retention rules, and the transcript prunes inside a run folder without destroying the record
- [ ] A replay from the last snapshot forward rebuilds a store, so Phase 4's test still passes after a rotation
- [ ] **The storage budget and the snapshot cadence are recorded as ruled numbers** — this box stays unchecked until the operator rules them (see § *Open inputs*)

### Phase 6 — The poller, and CPI on Edge1 *(gated: Phase 5)*

**Phase doc written when picked up.** No new cue surface is needed — `candidates.md`'s `status: open` **is** the to-do bit, and [`memory-model.md`](../../guide/memory-model.md) §1 property 4 already makes a to-do bit a required property of a durable record. What is missing is the poller: a scheduled workflow that queries state and starts children. This phase also moves CPI onto the journal, so it reads one store instead of searching git — which is what makes the accumulated log an asset rather than 262 MB nobody opens.

**Gate:** needs Temporal schedules (same server as Phase 5) and a journal with retention, so a poller is not reading an unbounded tree.

- [ ] A scheduled workflow reads a store's to-do bit and starts a child with no human trigger, demonstrated end-to-end on one real cue
- [ ] CPI's log sweep sources the journal rather than searching git, and the two produce the same findings on one overlapping window
- [ ] **Every producer shipped by Phases 1–5 has a named, committed consumer** — the discipline that pairs producer with consumer *in the same change*
- [ ] Cross-edge CPI is explicitly **not** built here; CPI stays on Edge1

### Phase 7 — S3 aggregation, local-write-first *(gated: a second edge, and a classification ruling)*

**Phase doc written when picked up, and it will likely split.** The synthesis sizes this at *"a couple of phases or its own sprint"* — an involved integration, not a feature — so this row is a placeholder that gets split at the point its gate opens. Layout under `<machine_id>` + `<run_id>`; the local file is the source of truth at write time and ships asynchronously, so the edge works when the bucket is unreachable. Syncing a bag tree to S3 is a boring directory sync, which is the payoff of Phase 1's shape. CPI then reads the bucket instead of one local journal — **same reader, different input**, which is why Phase 6 must not be built as throwaway.

**Two gates, and both are hard:**

- **A second edge that actually produces runs.** Building cross-edge aggregation before one exists is the speculative-generality trap `state_passing` §5.2 already caught this fleet in once.
- **A classification ruling for records crossing a trust boundary.** Shipping raw records to a store every edge reads crosses a line nobody has drawn. It is smaller than it looks — the journal's contents were *deliberately* written to a durable surface and most of it is already public in a GitHub PR, so the question is per-field — but it is still a decision and it still gates a shared store. The [heartbeat pollution paper](https://arxiv.org/pdf/2603.23064) is why a shared memory surface is an attack surface: pollution reached durable memory at rates up to 91%, and **prompt injection was not required — ordinary misinformation sufficed.**

- [ ] Bags ship to `<machine_id>/<run_id>` asynchronously; the edge continues to run with the bucket unreachable
- [ ] A shipped bag validates against its own manifest after transfer, using Phase 2's mechanism
- [ ] CPI reads the bucket with **no change to the reader** written in Phase 6
- [ ] The per-field classification ruling is recorded before the first record crosses the boundary

---

## Where each adopted concept is planned

All fifteen concepts in [`research/synthesis.md`](research/synthesis.md) are phased. Nothing is deferred out of the plan.

| § | Concept | Phase |
|---|---|---|
| 1 | Stores stay plural; the RECORD is what gets consolidated | 1 (payload spec) |
| 2 | Every write also emits to the journal, completely; the journal rebuilds the store; rebuildability is a test | 1 (versioning), 3 (a), 4 (b, c) |
| 3 | One typed return per step, modality-neutral | 3 |
| 4 | Artifact by reference plus a hash, never content by value | 1 (diffs as SHA), 2 (content store) |
| 5 | Lineage on every emitted item | 3 |
| 6 | Content store, with offline hash re-verification | 2 |
| 7 | Each artifact keeps its own format — and no database, deliberately | 1 |
| 8 | The accumulated log is an asset; pruning is small, planned work | 5 |
| 9 | Cue surfaces already exist; what is missing is the poller — and a stable edge id | 3 (edge id), 6 (poller) |
| 10 | Git is the coding edge's binding, not the protocol's | 3 (destination as a field), 7 |
| 11 | S3 as the aggregation point, with a local-first write | 7 |
| 12 | Temporal's own store is telemetry, not memory | 1 (contents table), 5 (split retention) |
| 13 | CPI stays on Edge1 until a second edge produces runs | 6 (step 1), 7 (steps 2–3) |
| 14 | One location, a folder per run, many formats, and a BagIt manifest | 1 |
| 15 | Concurrent children write to their own subfolder | 1 |

---

## Dependencies

**On other components:**

- **[Memory Management Framework](../memory-management-framework/roadmap.md)** — Phase 3 supplies the typed exit record this component's envelope extends (synthesis §3); Phase 2 supplies [`memory-model.md`](../../guide/memory-model.md), whose five properties and to-do bit Phase 6's poller reads. Both are **complete**, so neither blocks.
- **[Temporal Integration](../temporal-integration/temporal-integration.md)** — *Stand up the Temporal server* gates Phases 5 and 6. Nothing in Phases 1–4 needs it.
- **[`C-076`](../../standards/architecture/research/candidates.md)** — deployment automation is a dependency of §13's redeploy path, sized as its own sprint, and is explicitly **not** in this component.

**On rulings:** Phase 5 needs the storage budget and the snapshot cadence; Phase 7 needs the classification ruling. Both are below.

---

## Open inputs — questions this plan carries forward without answering

The synthesis's § *What this does NOT settle* is the source. These are inputs to the build, not deferred work: each is named at the phase that consumes it, and the corresponding requirement stays unchecked with prose saying why — **built is not proven, and a requirement whose evidence cannot exist yet is not checked.**

**Operator calls — this plan does not make them:**

1. **The storage budget and the snapshot cadence** (Phase 5). The mechanism is settled: rotate whole run folders oldest-first, never past the last snapshot. The two numbers are not — *how much disk the journal may hold* and *how often state is materialized* — and **they trade against each other**: a longer cadence needs more disk to stay rebuildable, a tighter budget forces a tighter cadence. Neither is derivable from evidence; both are preferences.
2. **What an edge actually is** (Phase 1, and nearer than the rest). Home-directory placement suits the edge we have because Claude Code itself requires a user context. An edge that is not a full Linux environment — HAOS is the live example — may have **no user account**, and may need a sidecar to run at all. **This does not block the build**: Phase 1's first requirement is that the root is a config value and nothing depends on a home directory, which is the buildable half. The definition is the unbuildable half.

**Open questions with no owner yet:**

3. **The three questions the journal must answer.** The operator's, asked in session and not yet answered. They decide the format, and nothing else does — and §2's rebuild test raises the stakes, because the journal now has to carry enough to *regenerate* a store rather than merely describe a run. Phase 1's payload spec is written against the rebuild test in the absence of the three questions; if they arrive and disagree with it, Phase 1's spec is what changes.
4. **Event schema versioning, in detail** (Phases 1, 3). The approach is settled — version, never mutate, upcast on read. The mechanism is not.
5. **Journal format at this volume, and redaction/classification for records crossing a trust boundary.** Both are genuine research questions and the strongest candidates for a full research cycle on this topic. The second gates Phase 7. Placed as [`C-077`](../../standards/architecture/research/candidates.md).
6. **Whether the Kind-1 / Kind-2 cut should be re-drawn.** [`state_passing`](research/raw/state_passing_between_workflow_children.md) §4.3.4 established that the two kinds cover three of eight channels and that *lifecycle* discriminates where *audience* does not — and explicitly declined to rule. Nothing in Phases 1–7 depends on the answer.

---

## What is deliberately not built

- **A database.** `state_passing` §4.3.1's format table has one empty row — *queries over accumulated history* — and the reflex is to fill it with SQLite. A per-run folder tree with a checksum manifest answers the questions we actually have. **And a database would be a projection**, which §2 already makes rebuildable from the journal — so this is a future build opportunity **with no refactor cost**. Revisit on a real query, not on a feeling that a record ought to live in a database.
- **An invented manifest format.** BagIt (RFC 8493) exists, its manifest *is* checksums, its `bagit.txt` declares a version, and bags transfer as loose trees or serialized. Three of this plan's requirements come free with it.
- **Cross-edge anything, before a second edge produces runs.** Phase 7's gate, and it is the same trap `state_passing` §5.2 caught once already.
- **Reading Temporal's own history as memory.** Its identity scheme is bounded by retention and continue-as-new starts a fresh history — an execution log with a TTL, not a durable record. Where CPI needs something Temporal knows, **the workflow emits it into the journal at completion.**

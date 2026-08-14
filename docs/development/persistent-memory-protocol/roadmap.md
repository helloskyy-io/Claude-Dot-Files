# Persistent Memory Protocol — Roadmap

**Status: 📋 PLANNED, NOT STARTED.** All eight phases have a phase doc. Four of them wait on something that does not exist yet; that is a scheduling fact recorded below, and it is not a reason any of them is planned less completely.

---

## In plain words

Right now, when a run finishes, most of what it did is gone or scattered. Some of it is in a GitHub pull request. Some is in a markdown table in this repo. Some is in a log file on one machine that nothing reads and nothing deletes. There is no single place you can go to ask *what happened, and why*.

This component builds that single place. **Every run writes a folder. The folder holds everything the run produced — what it wrote, how it got there, what it cost. The folders are never edited after the run ends, and they are never thrown away without a decision.**

The important part is the second half. Today, those markdown tables and pull requests are where the truth lives, and the log is a leftover. After this component, that flips: **the folders are the truth, and everything else can be rebuilt from them.** If a table gets corrupted, you regenerate it. If you want to know why a decision was made eight weeks ago, you read the folder instead of guessing which pull request it was in.

The test the whole design is measured against is the operator's, in his words:

> *"If I have a question it always starts in the journal. I rarely have to go to another source, because I know if I do it is just duplicated info from the journal anyway."*

Everything below is that idea, worked out far enough to build.

---

## The words this plan uses

Every term of art in this component is defined here, once. Each phase doc re-defines the terms it uses on first mention, so you can read any phase doc without this table in front of you.

| Word | What it means |
|---|---|
| **journal** | The whole record. One folder tree per machine, holding one folder per run. Nothing in it is ever edited after the run ends. |
| **bag** | One run's folder. The name comes from BagIt, the file-layout standard the folder follows. *(Never called a "container" — that word means a Docker container everywhere else in this system, and using it for a folder has already cost real confusion.)* |
| **manifest** | A file inside the bag listing every other file in it, with a checksum for each. It is how a reader knows what is in a folder and whether the bytes have changed, instead of guessing from file extensions. |
| **emit** | To write one entry into the journal. "Every write also emits" means: whenever a run writes something anywhere else, it also writes a copy into the journal. |
| **event** | One entry in the journal. Events are appended and never changed. |
| **store** | Any place other than the journal that a run writes to — a markdown table, a pull request comment, a GitHub issue. |
| **rebuild** | Read the journal back and regenerate what a store holds. If the journal can rebuild a store, nothing important is missing from the journal. *(The formal name for this is "the store is a projection of the journal." The plain sentence means the same thing and is used throughout.)* |
| **content store** | A byte cache. When a run cites a source, the source's actual bytes are saved and named by their checksum, so the claim can be re-checked later without the network. |
| **edge** | One machine running this fleet. Today there is one. The design assumes there will be more, and says where that assumption is load-bearing. |
| **snapshot** | A record of what every store held at one moment, written into the journal, so a rebuild can start from there instead of from the beginning of time. |
| **gate** | Something that has to exist before a phase can be built. A gate says *when*, never *whether*. |

---

## What this component is

**One durable record of everything the fleet has done, in one place per machine, that can rebuild every other store from itself.**

Today the fleet's memory is five curated surfaces plus a run log. The surfaces get read; the run log is 262 MB across 125 days with no rule for deleting any of it and — until [MMF Phase 6](../memory-management-framework/phase6_read_what_it_writes.md) — nothing that read it. Neither half is a record: the surfaces hold current state and drop the history behind it, and the log holds history that nothing can reconstruct state from.

This component closes that. Every write to any store also emits an event to the journal, and the journal carries enough to regenerate what the store holds.

**This component owns:** the journal's on-disk shape and its manifest; the emit rule, what completeness means, and what happens when a write fails; the content store and offline checksum verification; the rebuild test that makes completeness enforceable; snapshots, rotation and the split retention rule; the stable machine identity the record is keyed by; and combining records across machines once a second machine exists.

**It does not own:** the typed parent↔child handoff (built — [MMF Phase 3](../memory-management-framework/phase3_typed_exit_record.md)); the durable-record interface and its five properties (documented — [`memory-model.md`](../../guide/memory-model.md)); where a *finding* goes ([`finding-routing.md`](../../standards/finding-routing.md)); the Temporal port ([`temporal-integration/`](../temporal-integration/temporal-integration.md)); or the fleet's deployment automation ([`C-076`](../../standards/architecture/research/candidates.md)).

**Doc shape.** [`sprint.md`](../sprint.md) is the authority and it is unconditional as of 2026-08-13: *"Every component gets a `roadmap.md` plus numbered `phaseN_<name>.md` files, in the same folder — including one that only ever has a single phase."* This component takes that shape. *(An earlier version of this roadmap quoted the rule this replaced — "one phase needs no roadmap; do not create one to be tidy" — which was deleted from `sprint.md` the same day this plan was written. `sprint.md` also now states the rule locally rather than deferring to the vendored [Documentation Standard](../../standards/documentation/documentation_standard.md) §0, so the paragraph this roadmap used to carry about that section's applicability is no longer needed here.)*

**Evidence.** [`research/synthesis.md`](research/synthesis.md) is the decision record this plan is built from — 15 adopted concepts with their provenance, written by an operator+PM session on 2026-08-12. It states in its own header that it is not a research artifact and must not be cited as evidence, so every claim below cites what it points at: [`state_passing_between_workflow_children.md`](research/raw/state_passing_between_workflow_children.md) (Critic: PASS-WITH-FIXES, 2026-08-12) and [`bernstein_capability_mining.md`](../../standards/architecture/research/raw/bernstein_capability_mining.md). [`cross_node_memory_protocol.md`](research/raw/cross_node_memory_protocol.md) is superseded by its own header; it is cited only where the synthesis says a finding survives.

---

## Why this is a component and not a phase of the Memory Management Framework

[`C-074`](../../standards/architecture/research/candidates.md) is the open candidate for exactly this question, and the research that surfaced it declined to rule: [`cross_node_memory_protocol.md`](research/raw/cross_node_memory_protocol.md) §5.1 records that no source bears on component-vs-phase, and names the trap — a long list of mechanisms reads as an argument for a dedicated component while being equally consistent with a phase. So the argument below is deliberately not "there are fifteen concepts." It is a comparison of two stated ownership claims.

**The test** ([`sprint.md`](../sprint.md), *a component is a folder*): does this work stand up a new domain, or extend an existing one?

**MMF states its own scope**, in [its roadmap](../memory-management-framework/roadmap.md): *"the typed record and its schema; what a parent may route on without a model in the loop; how that relates to the durable human-readable record already in git; and the fail-safe contract when the record is absent or malformed."*

All four are properties of a handoff between two steps of one run — a channel that is fresh per invocation, read within seconds, then discarded. This component's subject is a *store*: a root path, a folder per run, a checksum manifest, a byte cache, snapshots, rotation, a stable machine identity, and combining records across machines. None of MMF's four clauses reaches any of those, and no phase of MMF could acquire them without restating its scope sentence.

Two further checks, each against an artifact rather than an impression:

- **It inverts authority over MMF's own outputs.** Under synthesis §2, `candidates.md` and `direction.md` become things the journal rebuilds. A phase does not change what its component's other phases are the truth of.
- **The journal is not one of the five durable-record surfaces**, so it cannot be that interface's next binding. [`memory-model.md`](../../guide/memory-model.md) §1 requires all five properties, and the journal fails two by design: it has no to-do bit (property 4 — a journal event is history and never *needs* anything), and it has no selection rule, because §1.1's whole question — *which surface does this outcome go to* — assumes a mutable, curated store. It is also never edited, where every one of those five surfaces is edited or closed. The journal is the substrate those surfaces are rebuilt from, not another one of them.

**The strongest counter-reading, stated so the operator sees it rather than only the case for.** [MMF Phase 2](../memory-management-framework/phase2_kind1_framework.md) delivered the durable-record interface as substrate-free — `memory-model.md` §1 says outright *"No property below is stated in terms of GitHub, git, a file or a URL … That is the claim, and it is the one a grep can check"* — and it already names *"an edge device, a robot, a datacenter node"* as needing durable memory without a pull request. Read that way, the protocol is simply that interface's third binding, which would make it a phase of the component that owns the interface. That is a serious reading and it is the one to beat.

**It is rejected on the property test above, not on scope aesthetics.** A binding of an interface must satisfy the interface. The journal satisfies three of five properties and contradicts a fourth. What *is* a third binding is the set of stores the journal rebuilds — and those already exist.

*(Two earlier supporting checks were dropped at review and are recorded so nobody re-derives them: "MMF is six-of-six complete" — MMF itself added a sixth phase to a shipped component on 2026-08-10, so that argument would forbid a move MMF made three days before this plan; and "MMF's binding is git" — contradicted by the substrate-free framing above, and cited as evidence for separation it argues the opposite.)*

**The one genuine overlap is synthesis §3** — one typed return per step, which the synthesis calls *"the extension of something shipped"* ([MMF Phase 3](../memory-management-framework/phase3_typed_exit_record.md)). That is a dependency across components, which a roadmap declares (§ *Dependencies*). **And the previous version of this plan got that overlap wrong in a way the next section corrects.**

---

## Questioning the Memory Management Framework

MMF is an early iteration, not a fixed point. This plan was rewritten because its first version treated MMF's model as settled input and shaped the protocol around it. That was backwards: where the two disagree, the protocol's requirement is the one grounded in what the record has to do, and the MMF-side change is proposed rather than worked around.

Four challenges. Each names what MMF says today, why it does not serve this protocol, and what change is proposed. **None of them is written by this plan** — `memory-model.md` and `exit-protocol.md` are human-in-the-loop under [`standards-governance.md`](../../../config/rules/standards-governance.md). They are stated here and carried into this plan's pull-request body, which is the surface an operator rules from.

### 1 · The journal envelope cannot extend the typed exit record, and the previous plan promised it would

**What MMF says.** [`exit-protocol.md`](../../standards/exit-protocol.md) §2: *"No field is added on behalf of a consumer that does not exist."* §2.5 bounds the envelope's fixed part at **4096 bytes**, *"the one corroborated cap figure in this evidence base (Tekton)."*

**Why it does not serve this protocol.** [Phase 3](phase3_the_emit_rule.md) needs six fields on every journal event — event identity, credential epoch, provenance class, lineage, `edge_id`, destination — and **no parent branches on any of them**, so §2's rule rejects every one. And a journal event carries authored content verbatim: one `research_minor` cycle's authored output measured **39,772 bytes** (synthesis §2), against a 4096-byte bound. The previous plan's requirement 3 said the envelope *"extends MMF Phase 3's typed exit record rather than inventing a second contract."* **That is not possible under the standard it names.** It was written to avoid appearing to invent a second contract, and it bought that appearance with a promise nothing could keep.

**The protocol-side resolution**, which Phase 3 now carries: the journal event is **a distinct contract that reuses the exit record's vocabulary** — the same enum members, spelled once, declared in one module — and is **not** the same envelope. They have different consumers, different lifetimes (one invocation versus forever), and different admission rules. Requirement 3 is now *one vocabulary, two contracts, no second spelling of any shared concept*.

**Proposed MMF change.** `exit-protocol.md` §2's no-speculative-fields rule and §2.5's size bound are correct **for a routing channel** and should say so. As written they read as governing any typed record this fleet emits, which is how a durable record ended up promised as an extension of a 4 KB routing envelope. One sentence scoping both rules to the routing channel resolves it.

### 2 · Two kinds do not cover the fleet's channels, and this component makes that worse

**What MMF says.** `memory-model.md` splits memory into Kind 1 (the durable record, read by humans and later runs) and Kind 2 (the typed exit record, read by code). MMF Phase 6 proposes a Kind 3 for the per-run log.

**Why it does not serve this protocol.** [`state_passing`](research/raw/state_passing_between_workflow_children.md) §4.3.4 enumerated eight boundary-crossing channels and found the two kinds cover **three**; five are covered by neither. It also found that the axis the kinds are named on — *audience* — does not discriminate between the two file surfaces, while **lifecycle does**, using vocabulary `memory-model.md` §3.1 already has (Transactional / Task / Continuous). This component adds a ninth channel that fits no existing kind, and MMF's answer so far has been to mint a new kind per surface.

**Proposed MMF change.** Stop numbering kinds and classify on lifecycle, which §3.1 already defines. The journal is a fourth lifecycle shape — **append-only**: its to-do bit is absent by construction rather than by omission, and its pruning rule is a decision about reconstructability rather than about housekeeping. This is the change with the widest blast radius of the four and it is the one most worth an operator's time; it is also the one this component can proceed without.

### 3 · MMF's own re-open condition for Kind 3 has fired, and the amendment has not landed yet

**What MMF says.** MMF Phase 6's proposed §2.7 amendment argues the per-run log is not a durable record because it fails property 1 — machine-local, gitignored. It carries its own condition, in its own words: *"If the run log is ever persisted beyond one machine — a synced archive, a log shipper, a Temporal payload store — that leg evaporates and this boundary moves. Re-open the ruling then rather than inheriting it."*

**Why it does not serve this protocol.** This component **is** that event. [Phase 1](phase1_the_run_bag.md) puts the transcript and the execution facts into a durable, machine-independent root, and [Phase 7](phase7_s3_aggregation.md) ships them off the machine. The Kind 3 amendment is unratified and sitting in MMF's roadmap awaiting an operator paste. **If it lands as written it will be stale on arrival.**

**Proposed MMF change.** Rule the Kind 3 amendment together with Phase 1's requirement 7, not before it. Phase 1 has to decide whether the journal absorbs the run log or sits beside it with a stated seam; the amendment's property-1 argument is downstream of that answer. Landing them out of order documents a boundary the next phase moves.

### 4 · The five properties describe surfaces that this component demotes, and readers of those surfaces are not told

**What MMF says.** `memory-model.md` §2.4 and §2.5 check `direction.md` and `candidates.md` against the five properties and find both pass — they are durable records, and they are described as where the answer lives.

**Why it does not serve this protocol.** After [Phase 4](phase4_rebuild_is_a_test.md) they are things the journal rebuilds. A hand edit that does not also emit gets reverted by the next rebuild — and the highest-value content in both files is hand-written by the operator. **Someone editing `candidates.md` after Phase 4 without knowing this will conclude the tool is broken.** Phase 4 requirement 6 already demands this be written where readers of those stores will find it, and that place is an MMF deliverable.

**Proposed MMF change.** `memory-model.md` §2 gains an authority note on both file surfaces at the Phase 4 trigger: *these are rebuilt from the journal; an edit that does not emit does not survive a rebuild.* Small, mechanical, and it prevents a data-loss-shaped surprise.

### What MMF gets right, and where this component depends on it

Not everything is a challenge, and one MMF property is load-bearing here in a way nothing else can replace. When the journal itself cannot be written, the failure cannot be recorded *in the journal* — so it surfaces on the one channel that is not the journal: the typed exit record MMF Phase 3 shipped, plus the process exit status. [Phase 3](phase3_the_emit_rule.md)'s § *When the journal cannot be written* depends on that channel existing, and it does. That is the dependency running the right way round.

---

## The protocol, whole

**Read this section as the design.** The phase list after it is a delivery order over exactly this content, and nothing here is contingent on when a part gets built.

The protocol is eight commitments. They are stated in dependency order — each one assumes the ones above it — not in build order.

**1 · One place, one folder per run, each file in whatever format suits it.**
The journal is one configurable root per machine. Inside it, one folder per run, keyed by run id and never by filesystem path. Concurrent children each write into their own subfolder, so no two writers ever touch one file. Each artifact keeps the format that suits it — the transcript stays JSONL, authored text stays markdown, execution facts are typed JSON, code is a commit SHA. A manifest per folder says what is in it and carries a checksum for each file, so a reader never has to guess from file extensions. The layout is BagIt (RFC 8493) because it already specifies exactly this and there is no reason to invent one.

**2 · Every write to any store also emits, verbatim, and the destination is a field.**
If any store gets it, the journal gets it — the pull-request body, every comment, the review verdict, the triage, the approval, issues, candidate rows. The one exclusion is the code diff, and it is excluded for a stated reason rather than to save space: git is already a better store for it, so the journal carries the SHA. The journal event is identical whether the run wrote into git, a GitHub object, or a message topic on a machine with no repo at all — that property is what makes the record portable to a second machine later.

**3 · A failed write is never silent.**
This is the commitment that keeps commitment 2 honest, and it has to be designed rather than discovered. **The rule is: a gap may exist; a silent gap may not.** Where a journal write has a paired store write, the emit goes first and a failed emit means the store write does not happen — so the invariant in commitment 2 is preserved by *both* sides being absent, which is loud and recoverable. Where there is no paired store write, a failure appends a typed gap event and marks the bag `incomplete`, and everything downstream treats an `incomplete` bag as a known-gap input rather than a clean one. [Phase 3](phase3_the_emit_rule.md) owns the rule; [Phase 1](phase1_the_run_bag.md) owns the bag state; [Phase 4](phase4_rebuild_is_a_test.md) and [Phase 6](phase6_cpi_reads_the_journal.md) honour it.

**4 · Bytes behind a claim are stored and re-checkable offline.**
When a run cites a source, the source's bytes are saved and named by their checksum. A verifier resolves every citation from that cache alone — re-checksumming to detect an altered source and confirming the quoted span still occurs — and it works with the network off. This is what makes a citation checkable without re-fetching, and it gives a computed stop condition: two stages that saw exactly the same evidence produce the same evidence checksum.

**5 · The journal can rebuild the store, and that is a test rather than a claim.**
Replay the journal into a scratch directory and diff the result against the live store. Without this, completeness decays silently the first time someone adds a write path and forgets the emit. With it, a missing emit goes red. This is also what inverts the authority: after it holds, the stores are things the journal regenerates, and a rule about deleting old journal data becomes a decision about what the fleet can no longer reconstruct.

**6 · Nothing is deleted without a snapshot to fall back to, and the two halves of the record get different rules.**
A snapshot records what every store held at one moment, into the journal. Deleting old data removes whole run folders oldest-first and never past the last snapshot — that ordering is the whole point, because after commitment 5 the journal is the only thing that can regenerate a store. And the two halves of the record are not alike: the authored text is roughly 7 MB for the entire 175-run history and never gets deleted; the transcript is 99.2% of the bytes and its value decays within weeks, so it gets deleted on a schedule.

**7 · The record is keyed by a machine identity that never rotates.**
Every event carries a stable machine id. An API key authenticates and maps to that id; it is never the id itself, and no key or key-derived value ever appears in an event. A journal keyed by credential orphans a machine's entire history the day the credential is rotated.

**8 · A second machine ships its folders to shared storage, writing locally first.**
Folders sync to object storage under machine id and run id. The local file is the truth at write time and ships asynchronously, so a machine keeps working when the bucket is unreachable. Syncing a folder tree is a boring operation, which is the payoff of commitment 1. Two rulings gate this and they are separate: what may leave a machine, and what a machine may believe about another machine's records.

**Where the design is deliberately incomplete, and it is named rather than hidden.** Three inputs are operator preferences that no amount of work would produce — the storage budget, the snapshot cadence, and the two rulings in commitment 8. They are listed in § *Open inputs* and each is carried by the phase that consumes it, with its requirement left unchecked and prose saying why.

---

## The order, and what each part waits on

Everything above is planned. This section says only *when*, and every gate below is a fact about the calendar rather than a limit on the design.

**Four phases have no gate at all** and could start today: 1 (the bag), 2 (the content store), 3 (the emit rule), 4 (the rebuild test). Together they deliver commitments 1 through 5 — which is the component's whole thesis, standing on its own.

**Four wait on something named:**

| Phase | Waits on | Why that thing and not another |
|---|---|---|
| **6** — CPI reads the journal | the Python port of `review-runs` ([Temporal Integration](../temporal-integration/temporal-integration.md)) | The evidence sweep exists today only in the frozen bash fleet, which may not be modified. **Not the Temporal server** — a sweep is a batch read, not a schedule. |
| **5** — snapshots, then retention | the Temporal server | Deleting old data on a schedule is a scheduled workflow plus a config value. The *snapshot* half needs no scheduler and Phase 4 builds a one-off snapshot for its own use. |
| **8** — the poller | Temporal schedules | Reading a to-do bit and starting a child with no human trigger is what a scheduler does. |
| **7** — cross-machine aggregation | a second machine that actually produces runs, plus two operator rulings | Building this before a second machine exists is the speculative-generality trap `state_passing` §5.2 already caught this fleet in once. |

**Why the phase numbers do not match the order.** Numbers are creation-order identifiers; the roadmap lists phases in rollout order. Phase 6 sits ahead of Phase 5 because only Phase 5 needs a server. That split was made at review, and it is worth stating why: at draft, Phase 6 and Phase 8 were one phase gated on Temporal, which would have put this component's **only consumer** behind a server nobody has stood up, for four phases of producers. [MMF Phase 6](../memory-management-framework/phase6_read_what_it_writes.md) is the measured record of what happens then — three phases shipped an emitter and none shipped a reader. Splitting them is what stops this plan repeating a failure it cites.

**On phase docs existing before a sprint picks the work up.** [`sprint.md`](../sprint.md) says *"Phase docs are written when a sprint is picked up, not in advance. A detailed plan for work that has not started yet is a guess that ages badly."* This plan diverges from that and says so rather than letting it pass silently. **A gated phase with a roadmap row and no document is a half-planned design, and the gap is not neutral** — the parts that get left out are precisely the parts that constrain the parts being built now. Phase 7's ingress ruling is the example: it constrains what field [Phase 3](phase3_the_emit_rule.md) must put on every event *today*, and it only became visible once Phase 7 was written out. The divergence is deliberate, it is scoped to this component, and the sizing risk `sprint.md` names is real — a gated phase doc will need re-reading when its gate opens.

**The checkboxes under each phase below summarise that phase doc's numbered requirements. They do not reproduce them, and the phase doc is authoritative.** A dispatch briefed from this section alone will under-size every phase — most of all Phase 3, whose write-path inventory has no checkbox here. Brief from the phase doc.

---

## Phases

### [Phase 1 — The journal root and the run bag](phase1_the_run_bag.md)

Stands up the folder structure everything else writes into. One configurable root per machine, one folder per run keyed by run id, one subfolder per concurrent child, and a BagIt (RFC 8493) manifest so a reader can read a folder rather than guess at it. Delivers the payload spec — what goes in the journal and what stays out, with a reason for each exclusion — and records *no database* as a decision with a revisit trigger rather than as an omission. Nothing emits into it yet; the outcome is a folder that validates.

- [ ] The root is a config value with a documented default per deployment shape, and nothing in the implementation depends on a home directory existing
- [ ] A run's record is one folder keyed by `run_id` — never by path — with one subfolder per concurrent child, so no two writers share a file
- [ ] The folder is a valid BagIt bag: `data/` payload, `manifest-sha256.txt` over every payload file, `bagit.txt` declaring version and encoding; a validator re-checksums the payload and reports pass/fail
- [ ] `bag-info.txt` carries the event schema version, and the versioning rule is written down: version every event, never change a written one, upgrade it on read
- [ ] The bag has four lifecycle states — open, sealed, pruned, **incomplete** — and the validator reports each distinctly
- [ ] The payload spec is stated as a table with a reason per row — authored output, transcript and execution facts in; code diffs out (commit SHA); Temporal history out (it expires)

### [Phase 2 — The content store and offline checksum verification](phase2_content_store.md)

Stores the bytes behind every claim, named by checksum, and ships a `verify` that resolves every citation from that cache alone — re-checksumming to detect an altered source and confirming the quoted span still occurs. It works with the network off. Three payoffs from one mechanism: it mechanises what `research-critic` does by hand, it makes a shared multi-machine store checkable for corruption, and an evidence checksum equal to a prior stage's is a no-new-evidence stop condition computed rather than judged.

- [ ] Every cited artifact is stored by content checksum under the journal root; nothing is copied in by value
- [ ] `verify` runs against a real prior run with the network disabled and distinguishes verified / missing / tampered by exit code
- [ ] A deliberately altered stored byte is detected, and a quoted span that no longer occurs in its source is reported as a distinct failure from a missing source
- [ ] `evidence_set_hash` is computed per stage and its equality with the prior stage's is exposed as a stop condition
- [ ] Code diffs are carried as a commit SHA and fetched from git, never copied into the store

### [Phase 3 — The emit rule: every write to any store also emits](phase3_the_emit_rule.md)

The core rule, and it is absolute: if any store gets it, the journal gets it, verbatim. The destination is a field rather than a format, which is the property cross-machine work later depends on. Every emitted item records which input produced it and carries a stable machine id. **And this phase answers what happens when the journal cannot be written** — the question that decides whether Phase 4's guarantee means anything.

- [ ] Every write path in the inventory emits a journal event carrying the authored content verbatim, with the destination store as a field
- [ ] The event contract reuses the [typed exit record](../memory-management-framework/phase3_typed_exit_record.md)'s vocabulary with one declaration per shared concept, and is explicitly a **separate contract** from it
- [ ] **A failed journal write is never silent** — write-ahead ordering where a paired store write exists, a typed gap event and an `incomplete` bag where none does, and the exit record where the journal itself is unwritable
- [ ] Every emitted item records which input item produced it, so a fan-out round can be traced output-to-input
- [ ] Every event carries a stable `edge_id`; the API key authenticates and maps to it and is never the id itself
- [ ] The write-path inventory is complete and enumerated in the phase doc, split into fleet-code writes and model-issued writes
- [ ] Measured against the synthesis's 39,772-byte baseline for one `research_minor` cycle, with the observed figure reported with its denominator

### [Phase 4 — Rebuildability is a test](phase4_rebuild_is_a_test.md)

Replays the journal into a scratch directory and diffs the result against the live store. This is what makes Phase 3 enforceable: without it, completeness decays silently the first time a write path is added and its emit is forgotten. The test belongs on the merge path, so a missing emit goes red rather than unnoticed.

- [ ] Replay of the journal reproduces `candidates.md` and `direction.md`, either byte-identical or under a normalisation that is stated and justified, from a starting snapshot forward
- [ ] Deleting one emit from a write path makes the test **fail**, demonstrated
- [ ] The test runs on the merge path against a committed synthetic fixture and against the live journal on a host, with **no skip-when-absent arm**
- [ ] A store the journal cannot rebuild is named as such, with the reason, rather than silently excluded
- [ ] **A journal containing gap events is reported as gapped, with the count and its denominator** — never diffed as though it were complete

### [Phase 6 — CPI reads the journal](phase6_cpi_reads_the_journal.md)

Moves the continuous-improvement evidence sweep onto the journal, so it reads one store instead of walking a per-repo pile of JSONL. **This is the consumer for everything Phases 1–4 produce, and it is listed ahead of Phase 5 because it needs no scheduler and no server.** The discipline it enforces is the synthesis's: pair every producer with its consumer. A producer with no consumer is how 262 MB accumulated unread.

**Gate:** the Python port of `review-runs`. Not the Temporal server.

- [ ] The evidence sweep sources the journal, and produces the same findings as the incumbent sweep over one overlapping window
- [ ] Every producer shipped by Phases 1–4 has a named, committed consumer — enumerated, not asserted
- [ ] The wall-clock of the cross-run sweep is measured against journal size, and reported as the first real test of Phase 1's no-database decision
- [ ] **Any gap in the journal appears in the sweep's own output**, so a reader of a CPI report learns what the record does not contain without coming here
- [ ] Cross-machine CPI is explicitly not built here

### [Phase 5 — Snapshots, then retention](phase5_snapshots_then_retention.md)

Records what every store held at a point in time into the journal, and only then deletes anything. Deletion removes whole run folders oldest-first and never past the last snapshot — that ordering is the whole phase, because after Phase 4 the journal is the only thing that can regenerate a store, so a deletion rule is a decision about what the fleet can no longer reconstruct. The authored record never gets deleted; the transcript does, on a schedule.

**Gate:** the Temporal server, for the recurring half only. Phase 4 builds the one-off snapshot it needs for its own baseline.

- [ ] A recurring snapshot records every store's state into the journal, addressable as the point a rebuild starts from
- [ ] A deletion dry-run **refuses** to cross the last snapshot, demonstrated against a real journal
- [ ] The authored record and the transcript carry separate stated retention rules, and the transcript is removable from inside a run folder without destroying the record
- [ ] A rebuild from the last snapshot forward still passes Phase 4's test after a deletion pass
- [ ] The storage budget and the snapshot cadence are recorded as ruled numbers — **this box stays unchecked until the operator rules them** (§ *Open inputs*)

### [Phase 8 — The poller](phase8_the_poller.md)

No new to-do surface is needed — `candidates.md`'s `status: open` already is one, and [`memory-model.md`](../../guide/memory-model.md) §1 property 4 already makes a to-do bit a required property of a durable record. What is missing is the thing that reads it: a scheduled workflow that queries state and starts children with no human trigger.

**Gate:** Temporal schedules, and a journal with a retention rule so a poller is not walking an unbounded tree.

- [ ] A scheduled workflow reads a store's to-do bit and starts a child with no human trigger, demonstrated end-to-end on one real cue
- [ ] The cue is read from an existing surface; no new cue surface is created
- [ ] A cue that fires twice starts one child, not two
- [ ] The poller reads the store rather than the journal, and the phase doc says why

### [Phase 7 — Cross-machine aggregation, writing locally first](phase7_s3_aggregation.md)

Folders sync to object storage under machine id and run id. The local file is the truth at write time and ships asynchronously, so a machine keeps working when the bucket is unreachable. CPI then reads the bucket instead of one local journal — same reader, different input, which is why Phase 6 must not be built as throwaway.

**Gates — three, and the last two are separate rulings that were nearly collapsed into one:** a second machine that actually produces runs; an **egress** ruling (*what may leave this machine?*); and an **ingress** ruling (*what may this machine believe?*). The second and third are different questions — one is about disclosure and one is about integrity — and the [heartbeat pollution paper](https://arxiv.org/pdf/2603.23064) is evidence for the third, not the second: it measured pollution reaching durable memory at rates up to 91%, **with prompt injection not required — ordinary misinformation sufficed**. Under [Phase 4](phase4_rebuild_is_a_test.md) a polluted record replays straight into `candidates.md`.

- [ ] Folders ship to `<machine_id>/<run_id>` asynchronously; the machine keeps running with the bucket unreachable
- [ ] A shipped folder validates against its own manifest after transfer, and the content-store objects it references ship with it — or the validation is knowingly partial and the doc says so
- [ ] CPI reads the bucket with no change to the reader written in Phase 6
- [ ] The egress ruling — **this box stays unchecked until the operator rules it**
- [ ] The ingress ruling — **this box stays unchecked until the operator rules it.** It states what a reader may *act on* versus merely display, and whether records are origin-authenticated

---

## Where each adopted concept is planned

All fifteen concepts in [`research/synthesis.md`](research/synthesis.md) are phased. Nothing is deferred out of the plan.

Read the third column as *"which numbered requirement carries it"*, not as a topic tag. Where a cell says **(stated)**, the concept is a recorded decision in that phase's prose rather than a checkable requirement — that is honest and it is different, because a reviewer checking coverage against a requirement list will not find it.

| § | Concept | Phase |
|---|---|---|
| 1 | Stores stay plural; the RECORD is what gets consolidated | **3** (§ *Stores stay plural*, stated), 1 (payload spec, r7) |
| 2 | Every write also emits, completely; the journal rebuilds the store; rebuildability is a test | 1 (r6, versioning), 3 (r1, r8), 4 (r1, r2) |
| 3 | One typed return per step, modality-neutral | 3 (r3) |
| 4 | Artifact by reference plus a checksum, never content by value | 1 (r7, diffs as SHA), 2 (r1, r6) |
| 5 | Lineage on every emitted item | 3 (r5) |
| 6 | Content store, with offline checksum re-verification | 2 (r1–r4) |
| 7 | Each artifact keeps its own format — and no database, deliberately | 1 (r10, no-database) · 1 (format-per-artifact, **stated**) |
| 8 | The accumulated log is an asset; deleting is small, planned work | **5** (r1–r3) |
| 9 | Cue surfaces already exist; what is missing is the poller — and a stable machine id | 3 (r6, edge id), **8** (r1–r3) |
| 10 | Git is the coding machine's binding, not the protocol's | 3 (r2, destination as a field), 7 (r1) |
| 11 | Object storage as the aggregation point, with a local-first write | **7** (r1–r3) |
| 12 | Temporal's own store is telemetry, not memory | 1 (r7, contents table), 5 (r3, split retention) |
| 13 | CPI stays on one machine until a second produces runs | **6** (r5), 7 (r3) |
| 14 | One location, a folder per run, many formats, and a manifest | 1 (r2, r4) |
| 15 | Concurrent children write to their own subfolder | 1 (r3) |

**One concept is not from the synthesis and is added by this revision:** a failed journal write is never silent, carried by [Phase 3](phase3_the_emit_rule.md) r4 and honoured by Phases 1 (r5), 4 (r7) and 6 (r6). It is here because Phase 4's guarantee is meaningless without it — a journal with silent gaps cannot rebuild anything — and the synthesis does not address it.

---

## Dependencies

**On other components:**

- **[Memory Management Framework](../memory-management-framework/roadmap.md)** — Phase 3 supplies the typed exit record whose *vocabulary* this component's events reuse, and whose channel [Phase 3](phase3_the_emit_rule.md) uses to report an unwritable journal; Phase 2 supplies [`memory-model.md`](../../guide/memory-model.md), whose to-do bit [Phase 8](phase8_the_poller.md)'s poller reads. Both are complete, so neither blocks. **Four changes to MMF are proposed** — see § *Questioning the Memory Management Framework*; none of them blocks this component.
- **[Temporal Integration](../temporal-integration/temporal-integration.md)** — two separate items, and conflating them is what gated this component's consumer behind a server at draft:
  - *Stand up the Temporal server* gates Phases 5 and 8. **Nothing in Phases 1–4 or 6 needs it.**
  - *Port `review-runs`* gates **Phase 6**. The evidence sweep exists today only as `scripts/workflows/review-runs.sh` in the frozen bash fleet, which may not be modified.
- **[`C-076`](../../standards/architecture/research/candidates.md)** — deployment automation is a dependency of synthesis §13's redeploy path, sized as its own sprint, and explicitly not in this component.

**On rulings:** Phase 5 needs the storage budget and the snapshot cadence; Phase 7 needs both the egress and the ingress rulings. All are below.

---

## Open inputs — questions this plan carries forward without answering

The synthesis's § *What this does NOT settle* is the source. These are inputs to the build, not deferred work: each is named at the phase that consumes it, and the corresponding requirement stays unchecked with prose saying why — **built is not proven, and a requirement whose evidence cannot exist yet is not checked.**

**Operator calls — this plan does not make them:**

1. **The storage budget and the snapshot cadence** ([Phase 5](phase5_snapshots_then_retention.md)). The mechanism is settled: remove whole run folders oldest-first, never past the last snapshot. The two numbers are not — how much disk the journal may hold, and how often state is recorded — and they trade against each other: a longer cadence needs more disk to stay rebuildable, a tighter budget forces a tighter cadence. Neither is derivable from evidence; both are preferences.
2. **What a machine actually is** ([Phase 1](phase1_the_run_bag.md), and nearer than the rest). Home-directory placement suits the machine we have because Claude Code itself requires a user context. A machine that is not a full Linux environment — HAOS is the live example — may have no user account, and may need a sidecar to run at all. **This does not block the build**: Phase 1's first requirement is that the root is a config value and nothing depends on a home directory. The definition is the unbuildable half.
3. **The egress and ingress rulings** ([Phase 7](phase7_s3_aggregation.md)). Two rulings, not one — *what may leave this machine* and *what may this machine believe*. Both are named at Phase 7 with their own unchecked box. The research that would inform them is [`C-079`](../../standards/architecture/research/candidates.md); the ruling is still the operator's.
4. **A `sprint.md` entry for this component.** `sprint.md` is operator-only and this plan does not write it. Without a row there the component is planned but unscheduled against everything else. Surfaced in this plan's pull-request body as a sprint-item candidate; it lands by operator edit.

**Open questions with no owner yet:**

5. **The three questions the journal must answer.** The operator's, asked in session and not yet answered. They decide the format, and nothing else does — and Phase 4's rebuild test raises the stakes, because the journal has to carry enough to *regenerate* a store rather than merely describe a run. Phase 1's payload spec is written against the rebuild test in their absence; if they arrive and disagree with it, Phase 1's spec is what changes.
6. **Event schema versioning, in detail** (Phases 1, 3). The approach is settled — version, never change a written event, upgrade it on read. The mechanism is not.
7. **Journal format at this volume, and redaction/classification for records crossing a trust boundary.** Both are genuine research questions and the strongest candidates for a full research cycle. Placed as [`C-079`](../../standards/architecture/research/candidates.md), which covers both halves of item 3.
8. **Whether MMF's memory taxonomy should be re-cut on lifecycle rather than audience.** [`state_passing`](research/raw/state_passing_between_workflow_children.md) §4.3.4 established that the two kinds cover three of eight channels and that lifecycle discriminates where audience does not, and declined to rule. **This plan does not depend on the answer, and it does now take a position** — see § *Questioning the Memory Management Framework*, challenge 2, which proposes the re-cut and says why. The ruling is the operator's.

---

## What is deliberately not built

- **A database.** `state_passing` §4.3.3's format table has one empty row — *queries over accumulated history* — and the reflex is to fill it with SQLite. A per-run folder tree with a checksum manifest answers the questions we actually have. And a database would be something the journal rebuilds, which Phase 4 already makes cheap — so this is a future build opportunity with no rework cost. Revisit on a real query, not on a feeling that a record ought to live in a database. [Phase 6](phase6_cpi_reads_the_journal.md)'s measurement is that trigger's first evidence.
- **An invented manifest format.** BagIt (RFC 8493) exists, its manifest *is* checksums, its `bagit.txt` declares a version, and bags transfer as loose trees or serialized. Three of this plan's requirements come free with it.
- **Cross-machine anything, before a second machine produces runs.** Phase 7's gate, and the same trap `state_passing` §5.2 caught once already.
- **Reading Temporal's own history as memory.** Its identity scheme is bounded by retention and continue-as-new starts a fresh history — an execution log with a time limit, not a durable record. Where CPI needs something Temporal knows, the fleet emits it into the journal per step, and the failure path writes a terminal event. *(The synthesis phrases this as "at completion"; that is corrected here, because a terminated, timed-out or crashed run never reaches completion — and failed runs are CPI's primary input, so a completion-only emit loses exactly the runs the record exists for.)*

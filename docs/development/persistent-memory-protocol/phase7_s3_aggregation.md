# Phase 7 — Cross-machine aggregation, writing locally first

**Component:** [Persistent Memory Protocol](roadmap.md) · **Status:** not started · **Gates:** a second machine that produces runs, plus two separate operator rulings

## What this phase does

Everything before this phase produces a record on one machine. This phase makes several machines' records readable together.

Each machine keeps writing to its own local folders exactly as before. In the background, those folders are copied to shared object storage, filed under which machine produced them and which run they belong to. The continuous-improvement sweep then reads the shared storage instead of one machine's disk — **the same reader, pointed at a different input**, which is why the reader built in [Phase 6](phase6_cpi_reads_the_journal.md) must not be built as throwaway.

The word "background" is doing real work. **The local file is the truth at the moment it is written**, and shipping happens afterwards. A machine whose network is down, or whose bucket credentials expired, keeps running and keeps a complete local record; it catches up later. Any design where a machine cannot work without reaching shared storage has moved the record off the machine, which is the opposite of what this component is for.

**Terms used here.** A **journal** is the whole record on one machine: one folder per run, never edited after the run ends. A **bag** is one run's folder (the name comes from BagIt, the file-layout standard it follows — a folder on disk, never a Docker container). A **manifest** is the file inside a bag listing every payload file with its checksum. The **content store** is a byte cache holding the sources a run cited, named by checksum. An **edge** is one machine running this fleet. To **rebuild** a store is to read the journal back and regenerate what that store holds.

## Why this phase waits, and what each gate is actually waiting for

Three gates. They are facts about what exists, and none of them is a reason this design is stated incompletely — two of the three **constrain what earlier phases must build today**, which is exactly why this document exists before its gates open.

| Gate | What it is waiting for | What it constrains *now* |
|---|---|---|
| **A second machine that produces runs** | Nothing else. Building cross-machine aggregation before one exists is the speculative-generality trap [`state_passing`](research/raw/state_passing_between_workflow_children.md) §5.2 already caught this fleet in once. | Nothing. This is the pure scheduling gate. |
| **The egress ruling** — *what may leave this machine?* | An operator decision. See below. | [Phase 3](phase3_the_emit_rule.md)'s payload fields: a classification that cannot be expressed per field is one nobody can enforce later. |
| **The ingress ruling** — *what may this machine believe?* | An operator decision, and a different one. See below. | [Phase 3](phase3_the_emit_rule.md) requirement 7's provenance class and credential epoch. **A field absent from version-1 events is absent forever**, so omitting them would foreclose this ruling before it is made. |

**The second and third were nearly collapsed into one gate, and collapsing them is how the third gets skipped.** They ask different questions, they have different failure modes, and satisfying one says nothing about the other.

## This phase will split, and here is where

The synthesis sizes this as *"a couple of phases or its own sprint"* — an involved integration rather than a feature. **Rather than leaving that as a warning, the seams are named here so the split is a mechanical act when the gate opens** and not a fresh planning exercise.

Three separable outcomes, in dependency order:

1. **Ship and validate.** Bags sync to the bucket and validate on arrival. Requirements 1 and 2. Verifiable on its own with nothing reading the bucket.
2. **Read.** [Phase 6](phase6_cpi_reads_the_journal.md)'s sweep points at the bucket. Requirement 3. Verifiable on its own once (1) holds.
3. **Trust.** Whatever the ingress ruling demands — origin authentication, a trust class on the reader, or an explicit decision that a shared bucket among mutually-trusting machines needs neither. Requirement 5.

**(3) may be larger than (1) and (2) put together, and it may be empty.** That depends entirely on the ingress ruling, which is why it cannot be sized here — and why it is a seam rather than a checklist item.

---

## Requirements for completion

1. **Bags ship to `<machine_id>/<run_id>` asynchronously**, and the machine keeps running with the bucket unreachable — demonstrated with the bucket actually unreachable, not asserted.
2. **A shipped bag validates against its own manifest after transfer**, using [Phase 2](phase2_content_store.md)'s mechanism — **and the content-store objects the bag references ship with it**, or the validation is knowingly partial and this doc says so and says why.
3. **The sweep reads the bucket with no change to the reader written in [Phase 6](phase6_cpi_reads_the_journal.md)** — the input location changes, the reader does not.
4. **The egress ruling is recorded, per field.** This requirement stays **unchecked** until the operator rules it.
5. **The ingress ruling is recorded.** It states what a reader may *act on* versus merely display, and whether records are origin-authenticated. This requirement stays **unchecked** until the operator rules it.
6. **A gap in a shipped bag survives the transfer as a gap.** [Phase 3](phase3_the_emit_rule.md)'s `incomplete` marking and its gap events ship with the bag and are visible to a reader of the bucket. A record that arrives looking complete when it is not is worse than one that does not arrive.

---

## Dependencies

- **[Phase 1](phase1_the_run_bag.md)** — the whole reason this phase is cheap. Syncing a directory tree to object storage is a solved, boring operation; syncing *"a database plus some files plus some GitHub state"* is not. This is the payoff of choosing a folder-per-run layout.
- **[Phase 2](phase2_content_store.md)** — supplies the manifest-validation mechanism requirement 2 runs after transfer, and the content-store objects requirement 2 has to decide about.
- **[Phase 3](phase3_the_emit_rule.md)** — supplies the stable machine id every object is filed under, and the provenance class and credential epoch the ingress ruling ranges over.
- **[Phase 6](phase6_cpi_reads_the_journal.md)** — supplies the reader requirement 3 must not have to change.
- **An operator ruling on egress, and a separate one on ingress.** Both are [roadmap § *Open inputs*](roadmap.md#open-inputs--questions-this-plan-carries-forward-without-answering), item 3. The research that would inform them is [`C-079`](../../standards/architecture/research/candidates.md).

---

## What this phase decides

### Local first is a correctness property, not a performance one

The local file is the truth at write time. Shipping is asynchronous, retried, and may lag arbitrarily.

**What that buys:** a machine works when the bucket is unreachable, with a complete local record and no degraded mode. What it costs is that the bucket is *eventually* consistent with the machines — a reader of the bucket is reading a slightly old picture, and requirement 3's sweep has to be correct under that.

**The alternative was considered and is worse.** Writing to the bucket first, or synchronously, makes every run depend on network reachability for its own record — so the record is least likely to exist exactly when something went wrong, which is when it matters most. It also puts the record somewhere the machine does not control, which contradicts the whole edge posture.

### The layout is `<machine_id>/<run_id>`, and the machine id is the one from Phase 3

Object storage is the standard answer for write-once, high-volume, append-only, rarely-read-but-must-be-readable data. The layout follows directly from [Phase 1](phase1_the_run_bag.md)'s on-disk shape with one level prepended.

**The machine id is [Phase 3](phase3_the_emit_rule.md) requirement 6's stable `edge_id`, and this is where the reason for that requirement becomes concrete.** If the key had been derived from a credential, rotating that credential would orphan a machine's entire history in the bucket — a rename of every object it ever wrote, with nothing to say the two prefixes are the same machine. One line of design in Phase 3; an unrecoverable data-modelling mess here.

### The egress ruling — what may leave this machine

**The question:** which fields of a record may be copied to storage that other machines read?

**It is smaller than it first looks, and that is itself part of the answer.** The existing classification rule excludes model-authored text, because it was written for the per-run log, which sits beside the CLI transcript where such text arrives incidentally. **The journal is different: every byte in it was deliberately written to a durable surface**, and most of it is already public in a GitHub pull request. So the question is per-field, and most fields answer themselves.

**It is still a decision and it still gates a shared store**, for one reason: the transcript. It carries the literal input of every command the fleet ran, and this fleet runs with permissions bypassed. [Phase 3](phase3_the_emit_rule.md)'s capture-time filter is the first control and [Phase 1](phase1_the_run_bag.md)'s redaction event class is the second, but a filter is a best effort and a shared bucket is permanent. **Whether the transcript leaves the machine at all is the live question**, and the honest default until it is ruled is that it does not.

**What the ruling has to produce:** a per-field classification that requirement 4 can be checked against. Not a principle — a table.

### The ingress ruling — what may this machine believe

**The question:** how does a reader treat another machine's records?

**This is an integrity question, not a disclosure one, and that is why it cannot be folded into the ruling above.** A build could classify every field correctly on the way out and still ship a reader that treats another machine's records as fleet history. The [heartbeat pollution paper](https://arxiv.org/pdf/2603.23064) is the evidence: it measured pollution reaching durable memory at rates up to **91%**, and **prompt injection was not required — ordinary misinformation sufficed.**

**Under [Phase 4](phase4_rebuild_is_a_test.md) the stores are things the journal rebuilds.** So a polluted record does not merely sit in a bucket being wrong; it **replays into `candidates.md` and `direction.md`** the next time anything rebuilds them. The blast radius of believing a bad record is the fleet's own decision surfaces.

**And the manifest does not close this.** A `manifest-sha256.txt` is regenerable by anyone who can write the bag. It proves integrity against **accident and transport corruption** — which is real and is what requirement 2 buys — and it proves **nothing** against a party with write access, which is exactly the party a shared bucket introduces. [Phase 2](phase2_content_store.md) § *What "verify" actually checks* states the same limit from the other side, deliberately, so this claim is not over-read in either document.

**What the ruling has to produce:** a statement of what a reader may *act on* versus merely display, and whether records are origin-authenticated. **A legitimate outcome is "neither, because every machine in this fleet is one operator's"** — that is a ruling, and recording it is what stops the next person re-deriving it. What is not legitimate is building the reader without asking.

**The field this ruling ranges over already has to exist.** [Phase 3](phase3_the_emit_rule.md) requirement 7's provenance class distinguishes fleet-authored prose, operator-authored input, and bytes fetched from the internet. Without it every downstream reader sees one undifferentiated stream and no ingress rule can be expressed at all — which is why that field lands in Phase 3 rather than here.

### The reader does not change, and that is a requirement rather than a hope

[Phase 6](phase6_cpi_reads_the_journal.md) builds the sweep against one local journal. Requirement 3 says pointing it at a bucket changes the input location and nothing else.

**That is a constraint on Phase 6, stated here so it lands there.** A sweep that hard-codes local filesystem semantics — walking directories, stat-ing files, assuming a rename is atomic — will not survive object storage, and rewriting it here would make this phase a rewrite of the consumer rather than a change of input. Phase 6's job is to make this requirement cheap; this requirement is how anyone knows whether it did.

---

## Implementation checklist

- [ ] Specify the bucket layout: `<machine_id>/<run_id>`, with the machine id from [Phase 3](phase3_the_emit_rule.md) requirement 6
- [ ] Build the asynchronous shipper: local write is the truth, shipping retries, backlog is bounded and observable
- [ ] Demonstrate a full run completing with the bucket unreachable, and the backlog draining afterwards — record both commands
- [ ] Rule requirement 2's content-store question: objects ship with the bag, or validation is partial and this doc says so
- [ ] Validate a shipped bag against its manifest after transfer, and demonstrate a corrupted transfer being caught
- [ ] Confirm an `incomplete` bag arrives marked `incomplete`, with its gap events intact
- [ ] Point [Phase 6](phase6_cpi_reads_the_journal.md)'s sweep at the bucket **with no change to the reader**, and record what did have to change
- [ ] Record the egress ruling as a per-field table **once the operator has ruled it**; leave requirement 4 unchecked until then with prose saying why
- [ ] Record the ingress ruling **once the operator has ruled it**, including an explicit "neither is required, and here is why" if that is the ruling; leave requirement 5 unchecked until then
- [ ] Tests per the [Testing Standard](../../standards/testing/README.md): `unit/` for layout derivation and backlog behaviour, `integration/` for a real ship-and-validate cycle against a real bucket
- [ ] Record transfer volume and wall-clock against bag count, with denominators, in § *Measurement*

---

## Measurement

*(Populated when the phase runs. Figures come from commands run against the tree and are pasted with the command.)*

Three figures with denominators:

- **Bytes shipped per run against bytes written per run.** If the egress ruling excludes the transcript, this ratio is roughly 1:125 on the synthesis's measured split (39,772 authored bytes against 4,823,628 transcript bytes for one `research_minor` cycle) — and knowing which side of that ruling the fleet is on is the difference between a trivial sync and a substantial one.
- **Backlog depth over a real outage**, with the outage duration as the denominator. This is what says whether "asynchronous" is bounded in practice.
- **Sweep wall-clock reading the bucket against reading one local journal**, over the same window. Requirement 3 is about correctness; this is about whether the result is usable.

---

## Notes and open items

- **This phase does not build cross-machine retention.** [Phase 5](phase5_snapshots_then_retention.md)'s numbers are bounded by one disk; a bucket is not, and it has its own lifecycle rules and its own cost model. Inheriting the local budget here by default would be a guess dressed as a decision.
- **Nothing in this phase authenticates a machine to the bucket beyond whatever the storage provider offers.** That is deliberate — the ingress ruling may make it a requirement, and pre-empting a ruling is how a build opens a security gate from priors.
- **The second machine is likely to be a building-automation edge**, per [`problem-statement.md`](../../standards/architecture/problem-statement.md), which has no repository to version and *"has runs"*. That is the case this component's destination-is-a-field property was designed for, and it is the one to check this phase against when the gate opens — not a second coding machine, which would exercise none of it.

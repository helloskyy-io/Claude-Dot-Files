# Phase 7 — Cross-machine aggregation, writing locally first

**Component:** [Persistent Memory Protocol](roadmap.md) · **Status:** not started · **Gate:** a second machine that produces runs

## What this phase does

Everything before this phase produces a record on one machine. This phase makes several machines' records readable together.

Each machine keeps writing to its own local folders exactly as before. In the background, those folders are copied to shared object storage, filed under which machine produced them and which run they belong to. The continuous-improvement sweep then reads the shared storage instead of one machine's disk — **the same reader, pointed at a different input**, which is why the reader built in [Phase 6](phase6_cpi_reads_the_journal.md) must not be built as throwaway.

The word "background" is doing real work. **The local file is the truth at the moment it is written**, and shipping happens afterwards. A machine whose network is down, or whose bucket credentials expired, keeps running and keeps a complete local record; it catches up later. Any design where a machine cannot work without reaching shared storage has moved the record off the machine, which is the opposite of what this component is for.

**Terms used here.** A **journal** is the whole record on one machine: one folder per run, never edited after the run ends. A **bag** is one run's folder (the name comes from BagIt, the file-layout standard it follows — a folder on disk, never a Docker container). A **manifest** is the file inside a bag listing every payload file with its checksum. The **content store** is a byte cache holding the sources a run cited, named by checksum. An **edge** is one machine running this fleet. To **rebuild** a store is to read the journal back and regenerate what that store holds.

## Why this phase waits, and what the gate is actually waiting for

**One gate: a second machine that actually produces runs.** Building cross-machine aggregation before one exists is the speculative-generality trap [`state_passing`](research/raw/state_passing_between_workflow_children.md) §5.2 warns against — it argues this fleet does not have the problem such a framework would solve, and that building one anyway is the trap. **It is a pure scheduling gate and it constrains nothing being built today.**

### The storage arrangement, which is settled and is not a gate

**Each edge has access to an S3 bucket — shared or its own — and uses it as it sees fit.** Today there is one edge and it has access to its own data. Anything further is decided by a future need rather than now.

That is the whole arrangement. **It is stated here so nobody re-derives it, and it is deliberately not a ruling with a checkbox**: an earlier version of this plan held two unchecked operator rulings — one about what may leave a machine, one about what a machine may believe — and both were blocking a phase whose only real gate is a machine that does not exist.

**Two things still land in earlier phases, and they land because of what they cost later rather than because a ruling waits on them:**

| What earlier phases carry | Why now rather than here |
|---|---|
| [Phase 1](phase1_the_run_bag.md) r7's payload spec carries a **per-field classification slot** | A classification the payload shape cannot express is one nobody can act on later, and a field absent from version-1 events is absent forever. Every row's value is *shippable* today; the slot exists so a narrower answer is expressible if one is ever wanted. |
| [Phase 3](phase3_the_emit_rule.md) r7's **provenance class** and **credential epoch** | Same reason, one layer up: a reader that cannot say where content came from cannot filter on it, and [Phase 8](phase8_the_poller.md)'s poller is the consumer that needs to. |

## This phase will split, and here is where

The synthesis sizes this as *"a couple of phases or its own sprint"* — an involved integration rather than a feature. **Rather than leaving that as a warning, the seams are named here so the split is a mechanical act when the gate opens** and not a fresh planning exercise.

Three separable outcomes, in dependency order:

1. **Ship and validate.** Bags sync to the bucket and validate on arrival. **Requirements 1, 2 and 4.** Verifiable on its own with nothing reading the bucket.
2. **Read.** [Phase 6](phase6_cpi_reads_the_journal.md)'s sweep points at the bucket. Requirement 3. Verifiable on its own once (1) holds.
3. **Attribute.** Origin derived from the prefix, and a prefix/`edge_id` disagreement reported. Requirement 5. Small on its own, and the seam that grows if a bucket ever becomes shared between machines that do not trust each other equally.

**Seam 2 does not close seam 3's question, and requirement 3 must not be read as forbidding its answer.** Requirement 3 says the *reader* does not change; **an origin filter placed ahead of the reader is not a change to the reader.** Without that sentence the seam order reads as closing the reader before the thing that constrains it.

---

## Requirements for completion

1. **Bags ship to `<machine_id>/<run_id>` asynchronously**, and the machine keeps running with the bucket unreachable — demonstrated with the bucket actually unreachable, not asserted.
2. **A shipped bag validates against its own manifest after transfer**, using [Phase 2](phase2_content_store.md)'s mechanism — **and the content-store objects the bag references ship with it**, or the validation is knowingly partial and this doc says so and says why.
3. **The sweep reads the bucket with no change to the reader written in [Phase 6](phase6_cpi_reads_the_journal.md)** — the input location changes, the reader does not.
4. **A gap in a shipped bag survives the transfer as a gap.** [Phase 3](phase3_the_emit_rule.md)'s `incomplete` marking and its gap events ship with the bag and are visible to a reader of the bucket. A record that arrives looking complete when it is not is worse than one that does not arrive.
5. **Origin is derived from the prefix an object was found under, never from a field inside the object**, and a disagreement between the two is reported as a finding rather than resolved in favour of the field. § *Origin is where an object is, not what it claims* below.
6. **The destination bucket blocks public access, encrypts at rest, is reached over TLS, and its credential is stored outside the repo and outside the journal.** § *The bucket's own posture* below. The last clause is the other half of [Phase 3](phase3_the_emit_rule.md) r6's no-key-in-events rule: a credential that never appears in an event but sits in a committed config file is the same exposure by a different route.

---

## Dependencies

- **[Phase 1](phase1_the_run_bag.md)** — the whole reason this phase is cheap. Syncing a directory tree to object storage is a solved, boring operation; syncing *"a database plus some files plus some GitHub state"* is not. This is the payoff of choosing a folder-per-run layout.
- **[Phase 2](phase2_content_store.md)** — supplies the manifest-validation mechanism requirement 2 runs after transfer, and the content-store objects requirement 2 has to decide about.
- **[Phase 3](phase3_the_emit_rule.md)** — supplies the stable machine id every object is filed under, and the provenance class and credential epoch a reader filters on.
- **[Phase 6](phase6_cpi_reads_the_journal.md)** — supplies the reader requirement 3 must not have to change.
- **A second machine.** That is the gate, and it is the whole of it.

---

## What this phase decides

### Local first is a correctness property, not a performance one

The local file is the truth at write time. Shipping is asynchronous, retried, and may lag arbitrarily.

**What that buys:** a machine works when the bucket is unreachable, with a complete local record and no degraded mode. What it costs is that the bucket is *eventually* consistent with the machines — a reader of the bucket is reading a slightly old picture, and requirement 3's sweep has to be correct under that.

**The alternative was considered and is worse.** Writing to the bucket first, or synchronously, makes every run depend on network reachability for its own record — so the record is least likely to exist exactly when something went wrong, which is when it matters most. It also puts the record somewhere the machine does not control, which contradicts the whole edge posture.

### The layout is `<machine_id>/<run_id>`, and the machine id is the one from Phase 3

Object storage is the standard answer for write-once, high-volume, append-only, rarely-read-but-must-be-readable data. The layout follows directly from [Phase 1](phase1_the_run_bag.md)'s on-disk shape with one level prepended.

**The prefix is the origin authority, and the in-event `edge_id` is not.** [Phase 3](phase3_the_emit_rule.md) requirement 7(b) states the target — an id assigned by an authenticating authority and bound at ingest — and states plainly that **no ingest tier exists to do the binding**, because bags sync here sealed. So the control this phase supplies instead: **each machine's storage credential is scoped by storage-side policy to its own `<machine_id>/` prefix**, and a reader derives origin from **the prefix an object was found under**, never from the `edge_id` inside the event. A disagreement between the two is a reportable finding, not a tie broken in favour of the field. That is the shape [`problem-statement.md`](../../standards/architecture/problem-statement.md) already argues for at the credential layer — *no label grants one edge the ability to authenticate as another subscriber*.

**The machine id is [Phase 3](phase3_the_emit_rule.md) requirement 6's stable `edge_id`, and this is where the reason for that requirement becomes concrete.** If the key had been derived from a credential, rotating that credential would orphan a machine's entire history in the bucket — a rename of every object it ever wrote, with nothing to say the two prefixes are the same machine. One line of design in Phase 3; an unrecoverable data-modelling mess here.

### Origin is where an object is, not what it claims — requirement 5

**The prefix is the origin authority, and the in-event `edge_id` is not.** [Phase 3](phase3_the_emit_rule.md) requirement 7(b) states the target — an id assigned by an authenticating authority and bound at ingest — and states plainly that **no ingest tier exists to do the binding**, because bags sync here sealed and a receiver cannot rebind a field inside a sealed bag without invalidating its manifest.

So the control this phase supplies instead is topological: **each machine's storage credential is scoped by storage-side policy to its own `<machine_id>/` prefix**, and a reader derives origin from **the prefix an object was found under**. A disagreement between the prefix and the `edge_id` inside the event is a reportable finding, not a tie broken in favour of the field. That is the shape [`problem-statement.md`](../../standards/architecture/problem-statement.md) already argues for at the credential layer — *no label grants one edge the ability to authenticate as another subscriber*.

**⚠ What this does NOT give.** It is an *attribution* control and not an *authenticity* one. A `manifest-sha256.txt` is regenerable by anyone who can write the bag: it proves integrity against **accident and transport corruption** — which is real and is what requirement 2 buys — and it proves nothing against a party with write access to the prefix itself. [Phase 2](phase2_content_store.md) § *What "verify" actually checks* states the same limit from the other side, deliberately, so the claim is not over-read in either document.

### Where a shared bucket would change things — a design note, not a gate

**The arrangement today is that each edge has access to a bucket and uses it as it sees fit, and there is one edge.** So the questions below are not open decisions blocking anything; they are what to read first if a bucket ever becomes genuinely shared between machines. Written down so nobody re-derives them under time pressure.

**Both postures would change, and the disclosure one is bigger than the surface-count framing suggests.** It is true that the *authored* half of the journal was deliberately written to a durable surface and is mostly already public in a GitHub pull request — **and that half is 0.8% of the bytes.** The other 99.2% is the CLI transcript: captured rather than authored, public nowhere, and carrying the literal input of every command the fleet ran under bypassed permissions. **So *what may leave* does not answer itself; it is essentially the transcript question and nothing else.**

**The evidence, because it is stronger than intuition suggests.** The [heartbeat pollution paper](https://arxiv.org/pdf/2603.23064) measured pollution reaching durable memory at rates up to **91%**, and **prompt injection was not required — ordinary misinformation sufficed.** Under [Phase 4](phase4_rebuild_is_a_test.md) the stores are things the journal rebuilds, so a polluted record does not merely sit in a bucket being wrong; it **replays into `candidates.md` and `direction.md`** the next time anything rebuilds them, and [Phase 8](phase8_the_poller.md) may then start a run off the result.

**So the three things a shared-bucket build would state, in order:** what a reader may *act on* versus merely display; whether records are origin-authenticated beyond prefix scoping; and whether the transcript is shipped at all. **The fields those answers range over already exist** ([Phase 1](phase1_the_run_bag.md) r7's per-field classification, [Phase 3](phase3_the_emit_rule.md) r7's provenance class), which is the whole reason they are built early.

### The bucket's own posture — named here rather than left absent

**Requirement 6 exists because the arrangement settles *who reaches the bucket*, and settles nothing about how the bucket itself is configured.** That is a different question and it does not become smaller when there is one edge: the object shipped is 4.8 MB per run of literal command input, and a single permissive bucket policy exposes every command the fleet has ever run plus whatever [Phase 3](phase3_the_emit_rule.md)'s capture filter missed.

**It is not an open ruling and it is not a gate — it is a requirement with an obvious answer that has to be written down so a build cannot skip it**, which is the difference between *deferred* and *absent* this plan is otherwise careful about.

### The reader does not change, and that is a requirement rather than a hope

[Phase 6](phase6_cpi_reads_the_journal.md) builds the sweep against one local journal. Requirement 3 says pointing it at a bucket changes the input location and nothing else.

**That is a constraint on Phase 6, stated here so it lands there.** A sweep that hard-codes local filesystem semantics — walking directories, stat-ing files, assuming a rename is atomic — will not survive object storage, and rewriting it here would make this phase a rewrite of the consumer rather than a change of input. Phase 6's job is to make this requirement cheap; this requirement is how anyone knows whether it did.

---

## Implementation checklist

- [ ] Specify the bucket layout: `<machine_id>/<run_id>`, with the machine id from [Phase 3](phase3_the_emit_rule.md) requirement 6
- [ ] Scope each machine's storage credential to its own prefix by storage-side policy, derive origin from the prefix, and report a prefix/`edge_id` disagreement as a finding
- [ ] Build the asynchronous shipper: local write is the truth, shipping retries, backlog is bounded and observable
- [ ] Demonstrate a full run completing with the bucket unreachable, and the backlog draining afterwards — record both commands
- [ ] Rule requirement 2's content-store question: objects ship with the bag, or validation is partial and this doc says so
- [ ] Validate a shipped bag against its manifest after transfer, and demonstrate a corrupted transfer being caught
- [ ] Confirm an `incomplete` bag arrives marked `incomplete`, with its gap events intact
- [ ] Point [Phase 6](phase6_cpi_reads_the_journal.md)'s sweep at the bucket **with no change to the reader**, and record what did have to change
- [ ] Ship according to [Phase 1](phase1_the_run_bag.md) r7's per-field classification as it stands when this phase runs, and record what that classification was at the time
- [ ] Confirm the bucket blocks public access, encrypts at rest and is reached over TLS, and record where its credential lives — outside the repo and outside the journal root (requirement 6)
- [ ] Tests per the [Testing Standard](../../standards/testing/README.md): `unit/` for layout derivation and backlog behaviour, `integration/` for a real ship-and-validate cycle against a real bucket
- [ ] Record transfer volume and wall-clock against bag count, with denominators, in § *Measurement*

---

## Measurement

*(Populated when the phase runs. Figures come from commands run against the tree and are pasted with the command.)*

Three figures with denominators:

- **Bytes shipped per run against bytes written per run.** The synthesis's measured split for one `research_minor` cycle is 39,772 authored bytes against 4,823,628 transcript bytes, so a build that ships everything and one that ships only the authored half differ by roughly two orders of magnitude in transfer volume. Which one this is decides whether the sync is trivial or substantial.
- **Backlog depth over a real outage**, with the outage duration as the denominator. This is what says whether "asynchronous" is bounded in practice.
- **Sweep wall-clock reading the bucket against reading one local journal**, over the same window. Requirement 3 is about correctness; this is about whether the result is usable.

---

## Notes and open items

- **This phase does not build cross-machine retention.** [Phase 5](phase5_snapshots_then_retention.md)'s numbers are bounded by one disk; a bucket is not, and it has its own lifecycle rules and its own cost model. Inheriting the local budget here by default would be a guess dressed as a decision.
- **Nothing in this phase authenticates a machine to the bucket beyond the storage provider's own credential scoping described above.** That is deliberate and it is bounded by the arrangement: one edge, its own data. What the prefix scoping buys unconditionally is that origin is a fact about where an object *is* rather than a claim inside it — which is the property a stronger scheme would build on rather than replace.
- **The second machine is likely to be a building-automation edge** — [`problem-statement.md`](../../standards/architecture/problem-statement.md) § *Building & industrial automation* names it as the natural next one because SkyyCommand already runs Home Assistant on the local network, so the domain is present and the hardware exists. It has no codebase to version; what it has is runs. That is the case this component's destination-is-a-field property was designed for, and it is the one to check this phase against when the gate opens — not a second coding machine, which would exercise none of it.

# Persistent Memory Protocol — synthesis

> **This synthesis was written by an operator+PM session on 2026-08-12, not by a research cycle.**
> It is the pool's consumption surface all the same: it is what the next research round reads to
> start from where we left off, and what planning reads to build a design against.
>
> It captures what we are adopting, where each idea came from, and why we chose it.
>
> **It is NOT a research artifact.** It did not pass the `research-critic` gate, its external
> sources were read once and not span-verified, and several were found by live search rather than
> a sourced sweep. **Confidence in anything sourced to § Live-session sources is one reading, no
> verification.** Do not cite this document as evidence; cite what it points at.
>
> **It is NOT a design.** No schema is specified here.
>
> **Status:** open. Adding to it is expected. A later full research cycle reads this, then rewrites
> this file per the Research Standard — ingesting what is below rather than starting over.

---

## Where the evidence came from

**Verified — passed the critic gate, in this repo:**

| Source | What it contributed |
|---|---|
| [`state_passing_between_workflow_children.md`](raw/state_passing_between_workflow_children.md) | Our own channel enumeration; the format axes; the by-value ceiling; the retention measurement; the Kind-1/Kind-2 mismatch |
| [`bernstein_capability_mining.md`](../../../standards/architecture/research/raw/bernstein_capability_mining.md) | The nearest comparable system's actual contracts. **The single highest-yield source in this document** |
| [`cross_node_memory_protocol.md`](raw/cross_node_memory_protocol.md) | **Superseded** — answered a question we do not have. Two findings survive, both re-grounded elsewhere |
| [`memory-model.md`](../../../guide/memory-model.md) | The existing vocabulary: durable record as an interface, five properties, the to-do bit |
| [`problem-statement.md`](../../../standards/architecture/problem-statement.md) | Names `bernstein` and `OpenClaw` as the two nearest neighbours, by different axes |

**Live-session sources — ONE READING, NOT VERIFIED:**

| Source | What it contributed |
|---|---|
| [n8n data structure](https://docs.n8n.io/build/work-with-data/understand-n8ns-data-structure) | The item envelope: `json` / `binary`, and `pairedItem` for lineage |
| [OpenClaw memory](https://mem0.ai/blog/mem0-memory-for-openclaw) | Two-store split in a shipping product — markdown for facts, `memory.sqlite` + `sqlite-vec` for retrieval — and its documented failure mode |
| [Inside the Scaffold (arXiv 2604.03515)](https://arxiv.org/pdf/2604.03515) | 13 coding-agent scaffolds at pinned commits × 12 dimensions. **States that state management and context compaction remain OPEN design questions** |
| [Mind Your HEARTBEAT! (arXiv 2603.23064)](https://arxiv.org/pdf/2603.23064) | What does not work: shared-session background execution pollutes durable memory at rates up to 91% |

---

## The concepts

### 1 · Stores stay plural. The RECORD is what gets consolidated.

**Adopted.** Two different things were being merged in early discussion, and separating them is what
makes the rest tractable:

- **The journal** — append-only, immutable, never edited, joined by run id. One location.
- **The working stores** — `candidates.md`, `direction.md`, phase docs, GitHub objects. Mutable,
  curated, each with its own lifecycle.

**Provenance.** `state_passing` §4.2 found all six surveyed systems run multiple channels
deliberately, each with a selection rule attached — Temporal ships `memo` and then documents that it
*"shouldn't store data that's critical to the execution of a Workflow."* Consolidation is not what
mature systems do.

**Why we chose it.** Our own two file surfaces have opposite requirements: `candidates.md` never
deletes a row by design; `direction.md` rotates a ruled row at 90 days. **No single retention or
merge policy can serve both**, so collapsing them destroys one of them.

### 2 · Every write to any store also emits to the journal — COMPLETELY, and the journal can rebuild the store

**Adopted — this is the core rule, and it is the operator's.** Three parts, and the third is what
keeps the first two honest.

**(a) Completeness is absolute.** A run writes wherever it needs to, in whatever format that surface
wants. **If ANY store gets it, the journal gets it** — what was written, where, and how it was
flagged. No surface is unrepresented and no write is journal-exempt.

**(b) The journal must be able to REBUILD anything any store holds**, in the same format. That
inverts the authority: the stores stop being sources of truth and become **projections** of the
journal. `candidates.md` becomes a materialized view; recovery becomes replay.

**(c) Rebuildability is a TEST, not a claim.** Replay the journal into a scratch directory and diff
the result against the live file. **This is the mechanism that makes (a) enforceable** — without it,
completeness degrades silently the first time a write path is added and the emit is forgotten, which
is a failure this repo has produced in several other forms.

**Provenance.** This is **event sourcing**, and it is Temporal's own model applied one level up:
event history is the truth, workflow state is a projection rebuilt by replay. `bernstein`'s journal
is the same shape.

**Why we chose it.** It buys *"never any question what happened"* without collapsing surfaces that
cannot share a lifecycle (§1). The stores hold state; the journal holds history and can regenerate
the state.

**⚠ The known cost, decided on day one because it is brutal to retrofit: SCHEMA EVOLUTION.** A
journal written under v1 must still replay under v3, forever. Every event-sourced system meets this.
The settled answer: **version every event, never mutate a written one, upcast on read.**

### 3 · One typed return per step, modality-neutral

**Adopted, and we take the shape close to as-is.**

`bernstein`'s typed activity boundary is *"the one contract a non-coding modality — research,
browser/computer-use, data, ops — participates through as a replayable step"*, and *"every activity
returns an artifact plus the hashes needed to replay it."* Every modality returns an `ActivityResult`
carrying `kind`, `artifact`, `artifact_hash`, `evidence_set_hash`, `terminal_state`, `reason_code`.

**Why we chose it.** Our children are the same shape — research / build / review / plan — and we
**already have a subset of this**: the Phase 3 typed exit record. This is the extension of something
shipped, not a new invention.

**The lesson worth keeping separately:** take a mechanism *with its reason*, then check the reason
still holds here. bernstein's reason is modality-neutrality across a shared scheduler. That is
exactly our situation, which is why it transfers nearly whole.

### 4 · Artifact by reference plus a hash. Never content by value.

**Adopted.**

**Provenance.** Converged from three places: `bernstein`'s artifact+hash; every ceiling in
`state_passing` §4.1 (Temporal 2 MiB/event, Temporal Cloud 40 KB/memo, Argo 1 MB, Airflow "small
amounts"); and our own `upstream_block` docstring, which records that inlining a synthesis cost 48k
characters and tripled a prompt.

**Why we chose it.** Our by-value channel is a single `execve` argument, capped by the kernel at
**131,072 bytes**. The largest fixed template is already at **58%** of it and the substituted blocks
are unbounded. Exceeding it is not degradation — it is a hard `E2BIG` naming neither the prompt nor
the block that grew.

### 5 · Lineage on every emitted item

**Adopted.**

**Provenance.** n8n's `pairedItem`, which records which output item came from which input item, by
index.

**Why we chose it — and this reversed a wrong call made in session.** The PM argued n8n's model did
not transfer because our children run in sequence. **That is false.** Nothing prevents a parent
launching children in parallel, and we already do: the 2026-08-12 verify round dispatched two
critics **21 seconds apart**. Fan-out is real today, so *"which output came from which input"* is a
question about our own runs that we currently cannot answer.

### 6 · Content store, with offline hash re-verification

**Adopted, and it is the cheapest item on this page.**

`bernstein activity verify <run>` *"resolves every citation from the content store alone"*,
*"re-hashes them to detect an altered source, and confirms the quoted span still occurs in them"*,
and *"The check touches only the content store, so it holds with the network disabled."*

**Why we chose it.** Three payoffs from one mechanism: it is the mechanical fix for our
research-critic re-fetching citations by hand; it makes a shared multi-edge store *trustworthy*,
since a record can be proven unaltered; and `evidence_set_hash` matching a prior stage's gives a
**no-new-evidence stop condition computed from a hash rather than judged by a model.**

> **⚠ `bernstein_capability_mining.md` §4.6 ranked this Tier 1, costed it S, named its roadmap home,
> and called it *"the item with the shortest path from read about it to we are using it."* It was
> never placed — not in `candidates.md`, not `direction.md`, not the roadmap, not an issue. The
> fleet then spent 2026-08-12 bounding by hand the exact cost it solves.**

### 7 · Two audiences, two formats, one journal

**Adopted.**

**Provenance.** OpenClaw ships markdown files for facts plus `memory.sqlite` with `sqlite-vec` for
retrieval. Our own format axes (`state_passing` §4.3.1) cut on reader latency, write pattern and
typing.

**Why we chose it.** Humans read markdown; code queries a database. Our format table has exactly one
empty row — *queries over accumulated history* — and that is the journal's reader.

**OpenClaw's documented failure is the warning to carry:** its memory *"lives in files that must be
explicitly loaded, which means continuity depends entirely on what gets re-read at startup"*, and
summarised context is lossy. A journal nothing loads is our 262 MB.

### 8 · The accumulated log is an ASSET. Retention is config, not architecture.

**Adopted — operator's ruling, and it corrects the PM's framing.**

175 files, 262 MB, 125 days, no pruning code. The PM presented this as a failure. **It is an
opportunity:** once lessons-learned and git-derived history also land in the journal, **CPI reads one
store instead of searching git.** Rotation is a scheduled Temporal workflow and a config variable at
server setup — not a design problem.

**What remains true from the original finding:** a store nobody reads is still the failure. The fix
is the reader, not a smaller store.

**And it does get pruned — that is planned work, not a permanent exemption.** Retention is a
scheduled Temporal workflow plus a config variable; it is small, and it is not zero. Under §2 the
journal is the authority that rebuilds the stores, so **a pruning rule is a decision about what the
fleet can no longer reconstruct** — which is why it gets planned rather than defaulted.

### 9 · Cue surfaces already exist. What is missing is the poller.

**Adopted.**

The operator's example — *a cron kicks off a candidate review* — needs no new surface.
`candidates.md`'s `status: open` **is** the to-do bit, and `memory-model.md` §1 property 4 already
makes a to-do bit a required property of a durable record. Temporal scheduled workflows are built for
exactly this: query state, start children.

**The discipline this must carry:** pair every producer with its consumer **in the same change**. A
producer with no consumer is how 262 MB accumulated unread.

**The other side of the handshake.** The upstream Django/Temporal pair has to know every edge and
how to work with it, and the **API key already associated with an edge is the natural carrier** — it
is how the edge authenticates today, so the identity exists and merely needs mirroring outward.

**⚠ But a key is a CREDENTIAL, not an IDENTIFIER, and credentials rotate.** A journal keyed by API
key orphans an edge's entire history the day the key is rotated. **The key authenticates; it maps to
a stable edge id that never rotates.** One line of design now, an unrecoverable data-modelling mess
later.

### 10 · Git is the coding edge's binding, not the protocol's

**Adopted — operator's ruling.**

Git stays for the edge we are building now, because that edge's memory *is* versioned with code,
reviewed in PRs, and travels with a clone. **The protocol stream carries the same data**, so a second
edge of any type sources it from the protocol rather than from a repo.

**Each edge reads and writes whatever surface that edge needs** — git, SQLite, a file, a broker.
**The truth is always the centralized output.** A surface is a local convenience; the journal is the
record.

**Why not repo-per-edge.** `state_passing` established that identity compatibility is not
integration — repos without a sync path are isolated memories that *look* joined, which is worse than
obviously separate ones. And an edge like Home Assistant has no codebase to version. **It has runs.**

### 11 · S3 as the aggregation point, with a local-first write

**Adopted in principle. Sized at a couple of phases or its own sprint** — an involved integration,
not a feature.

Layout under `<machine_id>` + `<run_id>`. Object storage is the standard answer for write-once,
high-volume, append-only, rarely-read-but-must-be-readable data.

**Three constraints, and the third is the real one:**

- **Write local first, ship asynchronously.** Local-first means the edge works when the bucket is
  unreachable, so the local file is the source of truth at write time.
- **Pairs with §6.** Hashing is what makes a shared store's records provably unaltered.
- **⚠ BLOCKER — classification.** Our run log already carries a PUBLISHABLE / NOT-PUBLISHABLE rule
  and deliberately excludes model-authored text. Shipping raw records to a store every edge reads
  crosses that line, and the [heartbeat pollution paper](https://arxiv.org/pdf/2603.23064) is the
  evidence for why a shared memory surface is an attack surface: **pollution reached durable memory
  at rates up to 91%, and prompt injection was not required — ordinary misinformation sufficed.**

### 12 · Temporal's own store is telemetry, not memory. Do not build on it.

**Adopted.**

Temporal generates its own database-driven history, and the question is whether CPI should read it.
**No — and the reason is in our own prior research:** Temporal's identity scheme is *"bounded by
retention"*, and continue-as-new starts a fresh history. **It is an execution log with a TTL, not a
durable memory.** Building analysis on it means building on a store that deletes itself on a
schedule configured months earlier.

The two records hold genuinely different things, and the split is clean:

| | Holds |
|---|---|
| **Temporal history** | orchestration — retries, per-activity timing, which worker ran what, signals, timers |
| **The journal** | content — what changed, where, how it was flagged, and what links to what across runs |

**The rule:** if CPI needs something Temporal knows, **the workflow emits it into the journal at
completion.** One writer, one record, at the edge.

**This also settles a boundary question: the edge store does NOT need to be reachable from the
server side**, and keeping that answer *no* is what preserves local-first.

### 13 · CPI stays on Edge1 until a second edge actually produces runs

**Adopted, and it is a sequencing decision rather than a compromise.**

Edge1 is the coding edge. It has git, it runs CPI today, and it is the only party that needs both
sides of the boundary. It makes changes and pushes to git, which redeploys the server side.

**Why not build cross-edge CPI now: there is no second edge producing runs.** This is the same
speculative-generality trap `state_passing` §5.2 already caught once, where it found the fleet had
designed away the problem it was about to build a framework for.

**The sequence, each step built only when the previous one has a real second party:**

1. **Now** — Edge1 runs CPI over its own journal. Nothing new required.
2. **When edge 2 exists** — S3 aggregation (§11), local-write-first.
3. **Then** — CPI reads the bucket instead of one local journal. **Same reader, different input** —
   which is the property that makes step 3 cheap, and the reason step 1 should not be built to be
   throwaway.

---

## What this does NOT settle

- **The three questions the journal must answer.** Operator's, and they decide the format. Nothing
  else does. *(Asked in session, not yet answered — and §2's rebuild test raises the stakes: the
  journal now has to carry enough to regenerate a store, not merely to describe a run.)*
- **The pruning rule** (§8). Under §2 it is a decision about what the fleet can no longer
  reconstruct, so it is planned work with a real trade-off rather than a config default.
- **Event schema versioning in detail** (§2). The approach is settled — version, never mutate,
  upcast on read — but not the mechanism.
- **Component or phase** — [`C-074`](../../../standards/architecture/research/candidates.md), still
  open. Nothing here depends on it; it decides where the plan gets written, not what is in it.
- **Journal format at this volume**, and redaction/classification for records crossing a trust
  boundary (§11's blocker). **Both are genuine research questions** and are the strongest candidates
  for a full cycle on this topic.
- **Whether the Kind-1 / Kind-2 cut should be re-drawn.**
  [`state_passing`](raw/state_passing_between_workflow_children.md) §4.3.4 established that the two
  kinds cover three of eight channels and that *lifecycle* discriminates where *audience* does not —
  but explicitly declined to rule.

## Out of scope for this component, captured so it is not lost

- **CI/CD and automated deployment** of the fleet — the server side, the edges, and the redeploy
  path §13 depends on. **This is delivery, not memory**, and it is sized as its own sprint. Placed
  as a candidate rather than described here, because a proposal that lives only in a synthesis dies
  when the synthesis is rewritten.

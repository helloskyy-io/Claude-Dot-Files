# Persistent Memory Protocol — Roadmap

**Status: 🟡 IN PROGRESS.** [Phase 1](phase1_the_run_bag.md) is complete — the journal root, the run bag and its validator ship today. Nine phases have a phase doc. Four of them wait on something that does not exist yet; that is a scheduling fact recorded below, and it is not a reason any of them is planned less completely.

**Phases are listed in logical rollout order. Phase numbers are creation-order identifiers and do not reflect rollout sequence; execution order across components lives in [`sprint.md`](../sprint.md).** [Phase 9](phase9_one_run_one_identity.md) is listed second for that reason — it was created last and is built early.

**This component is all of memory in this fleet — the framework and the protocol.** It owns how the fleet remembers anything: what kinds of record exist and how long each lives, the typed record a child writes at exit, the durable journal every write also lands in, and the rules that keep the two honest. There is no second memory component and nothing here defers a memory question elsewhere.

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
| **store** | Any place other than the journal that a run writes to, and that a reader consults for *current* state — a markdown table, a pull-request comment, a GitHub issue. A store is edited in place; the journal is not. |
| **rebuild** | Read the journal back and regenerate what a store holds. If the journal can rebuild a store, nothing important is missing from the journal. *(The formal name for this is "the store is a projection of the journal." The plain sentence means the same thing and is used throughout.)* |
| **completeness** | The property that if any store got something, the journal got it too, verbatim. It is not an assertion — [Phase 4](phase4_rebuild_is_a_test.md) turns it into a test that goes red when it stops being true. |
| **content store** | A byte cache. When a run cites a source, the source's actual bytes are saved and named by their checksum, so the claim can be re-checked later without the network. |
| **edge** | One machine running this fleet. Today there is one. The design assumes there will be more, and says where that assumption is load-bearing. |
| **snapshot** | A record of what every store held at one moment, written into the journal, so a rebuild can start from there instead of from the beginning of time. It is what makes deleting old folders safe. |

---

## The four kinds of record, and what ends each one's life

**This is the fleet's memory taxonomy, and this component is its single writer.** It replaces an earlier cut that named its classes by *audience* — who reads them — with numbered labels. Two things were wrong with that cut and both are checkable rather than aesthetic.

**It did not enumerate the fleet's channels.** [`state_passing`](research/raw/state_passing_between_workflow_children.md) §2.1 enumerated nine channels, eight of which cross a `claude -p` process boundary, and §4.3.4 found the audience-based classes covered **three of the eight**. Five — the prompt, the worktree path, the worktree contents, the completion-contract stdout line, and the per-run log — fell into no class at all. The response each time a new surface appeared was to mint another numbered kind.

**And audience did not predict behaviour where lifecycle did.** §4.3.4's second observation: `candidates.md` and `direction.md` are both markdown tables in one directory, both read by humans and by code, both in the same class — and one never deletes a row while the other rotates a ruled row out at 90 days. Audience says nothing about that difference. What ends a record's life does.

**So the cut is on lifecycle, and every class is named for what it is.**

| The class | What ends its life | What it holds | Where it lives here |
|---|---|---|---|
| **invocation state** | the invocation that created it ends — a child's, or the run's | everything a parent and a child pass each other in flight — the prompt, the worktree path and its contents, the completion line, and **the typed exit record**, which is the one contracted member | in the process, and on the exit-record channel |
| **the working record** | its to-do bit clears | the current state of one unit of work, edited in place, with the history behind it dropped | pull-request threads, Issues, the standup tracker, `direction.md`, `candidates.md` |
| **the journal** | the storage budget rotates its run folder out, and never past the last snapshot | history — appended, never edited, and with **no to-do bit at all**, because a past event never *needs* anything | this component |
| **measurement samples** | the population they belong to has been measured | a number that decides nothing on its own and becomes a decision only as a rate over many runs | the per-run JSONL log |

**Those four cover all eight boundary-crossing channels**: rows 1–5 of §2.1's enumeration are invocation state, row 6 is measurement samples, rows 7 and 8 are the working record. Row 9 crosses nothing — it is a parent's in-process list — and it is invocation state by lifecycle. **The journal is a new surface this component adds and appears nowhere in that enumeration.** The row numbers are §2.1's own and are re-derivable from its table.

**⚠ Two clauses keep `invocation state` from being read as a leftovers bin.** First, the discriminator is *the invocation that created it ends*, not *the child exits* — §2.1 rows 2 and 3 (the worktree path and its contents) are explicitly `child N → child N+1` and outlive any one child; they end at run teardown. Second, **a worktree's committed contents graduate out of the class at commit time**: once a commit exists, git is a store, which is exactly why commitment 2 carries the SHA rather than the diff. The class is what a run holds *while it is running*, and its members leave it by ending or by being written somewhere durable.

**And a class's substrate may move without the class dissolving.** [Phase 1](phase1_the_run_bag.md) § *The surface this replaces* **has now ruled it: the journal absorbs the per-run log.** So measurement samples get a new home and a new clearing rule while remaining what they are — a number that means nothing alone — and `run_log.py`'s three member event types keep their class across the move. The cut-over is [Phase 3](phase3_the_emit_rule.md)'s, which is where emitters live.

**Reading the old names.** Anything in this repo's history that says *Kind 1* means **the working record**; *Kind 2* means **the typed exit record**; a *Kind 3* was proposed and never ratified, and it means **measurement samples**. The numbers are not used here and are not reintroduced.

**The lifecycle axis keeps discriminating one level down, which is the point.** Within the working record, *how* the to-do bit clears and what happens to the row afterwards is a per-surface property and is stated per surface: `candidates.md` never deletes a row, `direction.md` rotates a ruled one out at 90 days. That is the difference audience never predicted, and it stays visible because the axis the classes are named on is the axis it lives on.

**What this taxonomy does NOT do.** It does not say which surface a given outcome should go to — that is a selection rule, it belongs to [`finding-routing.md`](../../standards/finding-routing.md), and it presupposes a mutable curated store, so it cannot reach the journal at all. It does not classify anything by *substrate*: a working record is a working record whether it is a GitHub thread or a markdown table, and [`memory-model.md`](../../guide/memory-model.md) §9 is where the substrate-specific half is enumerated. And it says nothing about *value* — a measurement sample is not a lesser record, it is a record whose unit of meaning is the population rather than the row.

**The origin of the interface, cited rather than deferred to.** The five properties a durable record has to satisfy were first written down in [`memory-model.md`](../../guide/memory-model.md) §1, and that document remains both their single writer and the operating manual for the working record's five surfaces. **This roadmap is the writer for the taxonomy itself**; where the two disagree, this is the one that changed and the amendment is listed in § *Standards-amendment candidates* below.

---

## What this component is

**One durable record of everything the fleet has done, in one place per machine, that can rebuild every other store from itself — plus the rules for every other kind of record the fleet keeps.**

Today the fleet's memory is five curated surfaces plus a run log. The surfaces get read; the run log is 262 MB across 125 days with no rule for deleting any of it. Neither half is a record: the surfaces hold current state and drop the history behind it, and the log holds history that nothing can reconstruct state from.

This component closes that. Every write to any store also emits an event to the journal, and the journal carries enough to regenerate what the store holds.

**Where a definition originated somewhere else, this plan states it anyway and cites the origin.** A protocol that points at four other documents for its own contracts is not a protocol. So *store*, *completeness*, *event* and *identity* are defined in § *The words this plan uses* and in the commitments below, not deferred; where that produces two statements of one thing, the single writer is named so they cannot drift:

| The thing | Origin | Single writer from here on |
|---|---|---|
| The memory taxonomy | [`memory-model.md`](../../guide/memory-model.md) §1, §3.1 | **this roadmap**, § *The four kinds of record* |
| The five properties of a durable record | [`memory-model.md`](../../guide/memory-model.md) §1 | `memory-model.md` — cited here, not restated |
| The typed exit record's envelope and its fail-safe contract | [`exit-protocol.md`](../../standards/exit-protocol.md) | `exit-protocol.md` — a routing channel, and a **separate contract** from the journal event ([Phase 3](phase3_the_emit_rule.md) r3) |
| The journal event contract | — | **[Phase 3](phase3_the_emit_rule.md)** |
| The storage budget and what deletion costs | — | **[Phase 5](phase5_snapshots_then_retention.md)**, on commitment 6 |
| Where a *finding* goes | [`finding-routing.md`](../../standards/finding-routing.md) | `finding-routing.md` — a different question from where a *record* goes |

**It does not own:** the Temporal port ([`temporal-integration/`](../temporal-integration/temporal-integration.md)), the fleet's deployment automation ([`C-076`](../../standards/architecture/research/candidates.md)), or **managed configuration and the digest of what a run absorbed** — that is [Workflow Decomposition Phase 5](../workflow-decomposition/phase5_configuration_a_run_absorbed.md)'s in full, by operator ruling on 2026-08-19.

**⚠ That last one is a boundary worth stating precisely, because it is the first time another component WRITES into this one's record.** The config digest is *stored* in the bag and *owned* by decomposition: it decides what the digest covers, computes it, and ships the reader that compares two of them. **This component owns the surface it lands on** — the tag namespace, the schema version, and what a reader does with a tag it does not recognise. **Being written into is not the same as owning**, and the seam is what distinguishes them: the question *"what configuration did this run absorb"* is decomposition's derive-not-inherit seam, not a memory question, so the paragraph above about there being no second memory component is unaffected.

**Evidence.** [`research/synthesis.md`](research/synthesis.md) is the decision record this plan is built from — 15 adopted concepts with their provenance, written by an operator+PM session on 2026-08-12. It states in its own header that it is not a research artifact and must not be cited as evidence, so every claim below cites what it points at: [`state_passing_between_workflow_children.md`](research/raw/state_passing_between_workflow_children.md) (Critic: PASS-WITH-FIXES, 2026-08-12) and [`bernstein_capability_mining.md`](../../standards/architecture/research/raw/bernstein_capability_mining.md). [`cross_node_memory_protocol.md`](research/raw/cross_node_memory_protocol.md) is superseded by its own header; it is cited only where the synthesis says a finding survives.

---

## Absorbed work — the typed exit record, and the three boxes that came with it

**The typed exit record is this component's, and it is the one part of the design that is already built and in daily use.** A child writes a small typed record at exit, on a channel the parent owns; the parent reads it in code within seconds and routes on it. It is a member of *invocation state* — one invocation's lifetime, then gone — and it is bounded, versioned and total, with an ordered fail-safe contract whose residual arm is a named recorded state rather than a silent fall-through. Its contract is stated in [`exit-protocol.md`](../../standards/exit-protocol.md), which remains that contract's single writer.

**This component depends on it in one specific, load-bearing way.** When the journal itself cannot be written, the failure cannot be recorded *in the journal* — so it surfaces on the one channel that is not the journal: this record, plus the process exit status ([Phase 3](phase3_the_emit_rule.md) § *When the journal cannot be written*, case (d)). That is the dependency running the right way round, and it is why the record is adopted rather than replaced.

**This protocol is its own component, not a phase of anything, by operator ruling on 2026-08-16** — the framework it would have been a phase of was retired into it. [`C-074`](../../standards/architecture/research/candidates.md) asks the question; its `decision` is the triager's to set and this is the evidence.

## The protocol, whole

**Read this section as the design.** The phase list after it is a delivery order over exactly this content, and nothing here is contingent on when a part gets built.

The protocol is nine commitments. They are stated in dependency order — each one assumes the ones above it — not in build order.

**1 · One place, one folder per run, each file in whatever format suits it.**
The journal is one configurable root per machine. Inside it, one folder per run, keyed by run id and never by filesystem path. Concurrent children each write into their own subfolder, so no two writers ever touch one file. Each artifact keeps the format that suits it — the transcript stays JSONL, authored text stays markdown, execution facts are typed JSON, code is a commit SHA. A manifest per folder says what is in it and carries a checksum for each file, so a reader never has to guess from file extensions. The layout is BagIt (RFC 8493) because it already specifies exactly this and there is no reason to invent one.

**2 · Every write to any store also emits, verbatim, and the destination is a field.**
If any store gets it, the journal gets it — the pull-request body, every comment, the review verdict, the triage, the approval, issues, candidate rows. The one exclusion is the code diff, and it is excluded for a stated reason rather than to save space: git is already a better store for it, so the journal carries the SHA. The journal event is identical whether the run wrote into git, a GitHub object, or a message topic on a machine with no repo at all — that property is what makes the record portable to a second machine later.

**3 · A failed write is never silent.**
This is the commitment that keeps commitment 2 honest, and it has to be designed rather than discovered. **The rule is: a gap may exist; a silent gap may not.** Where a journal write has a paired store write, the emit goes first and a failed emit means the store write does not happen — so the invariant in commitment 2 is preserved by *both* sides being absent, which is loud and recoverable. Where there is no paired store write, a failure appends a typed gap event and marks the bag `incomplete`, and everything downstream treats an `incomplete` bag as a known-gap input rather than a clean one. [Phase 3](phase3_the_emit_rule.md) owns the rule; [Phase 1](phase1_the_run_bag.md) owns the bag state; [Phase 4](phase4_rebuild_is_a_test.md) and [Phase 6](phase6_cpi_reads_the_journal.md) honour it.

**4 · Bytes behind a claim are stored and re-checkable offline.**
When a run cites a source, the source's bytes are saved and named by their checksum. A verifier resolves every citation from that cache alone — re-checksumming to detect an altered source and confirming the quoted span still occurs — and it works with the network off. This is what makes a citation checkable without re-fetching, and it gives a computed stop condition: two stages that saw exactly the same evidence produce the same evidence checksum.

**5 · The journal can rebuild the store, and that is a test rather than a claim — and a restore, not only a test.**
Replay the journal into a scratch directory and diff the result against the live store. Without this, completeness decays silently the first time someone adds a write path and forgets the emit. With it, a missing emit goes red. **The same replay, pointed at the real store instead of a scratch directory, is the restore this component is sold on** — *if a table gets corrupted, you regenerate it* — and it is built rather than left as an implied consequence, because the person who writes it later writes it against whatever containment rules happen to exist then. This is also what flips the authority: after it holds, the stores are things the journal regenerates, **so every consumer of a rebuilt store is a consumer of the journal and inherits every rule that governs reading one.** A rule about deleting old journal data then becomes a decision about what the fleet can no longer reconstruct.

**6 · One storage budget over the whole journal, and the snapshot is what makes deleting safe.**
The journal has **one size limit: 1 GB by default, and it is a configuration value an operator changes without editing code.** **It is measured over everything under the journal root — the bags, the content store and the snapshot — and nothing is exempt from it**: no half kept forever, no reserved floor. When the journal is over budget, a retention pass removes **whole `sealed` run folders, oldest first, until it is back under**, and never past the most recent snapshot.

**The snapshot is what makes that safe, and stating that is the point of the rule.** A snapshot records what every store held at one moment, into the journal — so state survives the deletion of the folders behind it. **What a deletion costs is the ability to replay from before that point, not the state itself.** If getting under budget would require crossing the last snapshot, the pass writes a new snapshot first. **That is the whole of the cadence, and it is derived from the budget rather than being a second number to rule.**

**And the pass has a terminal state, which is the half a cadence-derived rule most easily omits.** It writes **at most one snapshot per pass**, never deletes a bag that is not `sealed`, and when it cannot reach budget with what it is permitted to delete it **stops and reports rather than continuing** — because a barrier the pass keeps re-advancing is not a barrier. [Phase 5](phase5_snapshots_then_retention.md) § *The pass, stated as steps* is the authoritative statement of the algorithm.

**Deletion is all-or-nothing per run, and the reasoning is not disk.** A run whose transcript was rotated away but whose authored output remains is a run you can half-read — and **half-readable reads as coverage**, which gives false confidence in what the record holds. A partial run record is worthless. At 1 GB the journal holds a very large library of *complete* runs, and rotating the oldest whole ones out is the obvious trade.

> **This is a ruling, and it is recorded here with its reasoning rather than in a pull-request body, because it has been ruled once before and was not written down** — which is a live instance of exactly the failure this component exists to prevent. It replaces a rule that rotated the transcript on a schedule and kept the authored text forever. That rule produced precisely the partial record this one forbids, and it treated the authored record as irreplaceable — which it is not: [Phase 4](phase4_rebuild_is_a_test.md) makes the stores rebuildable and [Phase 5](phase5_snapshots_then_retention.md) makes the snapshot the point a rebuild starts from.

**7 · The record is keyed by a machine identity that never rotates, and that identity is designed jointly with the orchestrator.**
Every event carries a stable machine id. An API key authenticates and maps to that id; it is never the id itself, and no key or key-derived value ever appears in an event. A journal keyed by credential orphans a machine's entire history the day the credential is rotated.

**What this component needs is stated as a constraint, not as a specification:** an identity that is **stable across credential rotation**, **never derived from a key**, and **present on every event**. **The final shape has to satisfy the Temporal port as well** — that component addresses workers, task queues and schedules, and has its own reasons to name a machine. This component lands first, so its constraint is an *input* to that design rather than a requirement imposed on it. [`temporal-integration.md`](../temporal-integration/temporal-integration.md) names no machine or edge id today, so the question is open on both sides and gets settled once instead of twice.

**8 · A second machine ships its folders to object storage, writing locally first.**
Folders sync to object storage under machine id and run id. The local file is the truth at write time and ships asynchronously, so a machine keeps working when the bucket is unreachable. Syncing a folder tree is a boring operation, which is the payoff of commitment 1.

**The arrangement is settled and it is short: each edge has access to an S3 bucket — shared or its own — and uses it as it sees fit.** Today there is one edge and it has access to its own data. What a *shared* bucket would additionally require of a reader is decided by the need that produces one, not now — and [Phase 7](phase7_s3_aggregation.md) states the shape it would take so nobody re-derives it.

**9 · What goes in is filtered at capture, and the one exception to immutability is a redaction.**
The transcript carries the literal input of every command the fleet runs, and this fleet runs with permissions bypassed. A secret that reaches the journal is sealed into a checksum-covered file that Phase 4's test then makes expensive to remove — so the filter runs **at capture, before any byte lands**, and it emits a placeholder so the record is honest about the removal rather than silently shorter. And because a filter is best-effort, there is **one stated exception to never-changing-a-written-event**: a redaction is a new appended event that supersedes, the file is replaced by a marker, the manifest is regenerated and that regeneration is itself recorded — tagged distinctly from a **gap event**, which shares its shape — both leave a bag whose payload differs from what was first written — so a deliberate redaction is never mistaken for bytes lost to a full disk. **Nothing is ever silently edited.** [Phase 3](phase3_the_emit_rule.md) owns the filter; [Phase 1](phase1_the_run_bag.md) owns the exception.

**Where the design is deliberately incomplete, and it is named rather than hidden.** One input is not derivable from any amount of work: **what a machine actually is**, when the second one is not a full Linux environment. It is listed in § *Open inputs*, carried by [Phase 1](phase1_the_run_bag.md), and it does not block that phase — Phase 1's first requirement is that the root is a config value and nothing depends on a home directory.

---

## Why the protocol is built as activities

**Bag setup is an activity every parent invokes as its first step, so a run cannot execute without a journal.**

As a library each workflow remembers to call, the protocol is optional — and optional is precisely how three separate controls in this fleet have already failed: an observable emitted with no reader, a rule stated in a docstring that governed three event types from the wrong place, and a completion gate that one fleet's runner had and the other's did not. **A rule written in prose has not once prevented a write path from being added without its emit.**

**⚠ And the activity boundary alone does not deliver that, which is why each of the three requirements carries a test rather than a placement.** Nothing in an orchestrator forces a workflow to invoke a particular activity first — a workflow that omits the call simply omits it. So *"the journal code lives in the activities layer"* is tidiness, not a guarantee; and [Phase 1](phase1_the_run_bag.md) r9's refuse-to-start cannot supply it either, because **r9 fires only once bag-open has already been invoked.**

**What delivers it is an enumerating test, and this repo already ships the exemplar** — `test_every_entrypoint_actually_calls_preflight` discovers every entrypoint under `scripts/workflows/temporal/scripts/` and asserts each one calls `preflight(`. [Phase 1](phase1_the_run_bag.md) r11, [Phase 2](phase2_content_store.md) r8 and [Phase 3](phase3_the_emit_rule.md) r12 each take that shape for the surface they own. **A parent added without the call goes red on the merge path**; a parent that opens a bag against an unresolvable root gets a run that does not start ([Phase 1](phase1_the_run_bag.md) r9). Two guards, two failures, neither substituting for the other.

**Half of each requirement is buildable today and half is port-time, and the phase docs say which.** Layer placement, invocation as the parent's first step, fail-stop on error and the enumerating test are buildable now; **orchestrator-driven retry and recorded execution are properties of a worker that does not exist** and land with the port. Stating the split is what stops a dispatch either stalling on a missing worker or checking the box on a plain function.

**What this does NOT cover, stated so the guard is not over-read.** It makes the journal *structurally present*; it does not make any individual write *complete*. A parent that opens a bag and then writes to a store through a path nobody wrapped still produces a gap, and neither the boundary nor the sweep can see that — **[Phase 4](phase4_rebuild_is_a_test.md)'s rebuild test is the guard for that class.** It does not reach model-issued writes at all, which are [Phase 3](phase3_the_emit_rule.md)'s post-exit harvest and are structurally outside any wrapper. And **an enumerating test is only as good as its discovery predicate** — a parent living outside the swept directory is invisible to it.

**⚠ Making the journal mandatory has a cost, and it is named rather than discovered.** Once [Phase 3](phase3_the_emit_rule.md) lands, a full disk stops *every* run including the one you would use to diagnose it. Two things bound that, and both are stated: [Phase 5](phase5_snapshots_then_retention.md)'s requirements 2–6 are ungated and should land with or before Phase 3 rather than waiting for the server only its requirement 1 needs; and Phase 1 r9's refusal names the resolved path and the failing property, so recovery does not need a working journal.

**This is one of the constraints that runs both ways with the Temporal port** — see § *Dependencies*.

---

## The order, and what each part waits on

Everything above is planned. This section says only *when*, and every gate below is a fact about the calendar rather than a limit on the design.

**[Phase 1](phase1_the_run_bag.md) is built.** The journal root, the run bag, its BagIt manifest and its validator ship today, and eleven entrypoints open a bag before their first side effect.

**Four phases have no EXTERNAL gate** and could start today: 9 (run identity), 2 (the content store), 3 (the emit rule), 4 (the rebuild test). They depend only on each other and on Phase 1 — 1 → 2, and 1 → 9 → 3 → 4, as each phase doc's own header says, so *ungated* means *waiting on nothing outside this component* rather than *runnable in parallel*. Together with Phase 1 they deliver commitments 1 through 5 — which is the component's whole thesis, standing on its own.

**⚠ Ungated is not the same as unpressed, and [Phase 9](phase9_one_run_one_identity.md) is the one that shows the difference.** It waits on nothing, and two other components have already set clocks on it: [Workflow Decomposition Phase 3](../workflow-decomposition/phase3_dual_mode_children.md) adds nine entrypoints into the directory this component's bag-open sweep enumerates, and the Temporal port's Stage B wraps the functions the run id is generated inside. **Neither is a gate on this component; both are deadlines, and a deadline nobody schedules against is missed by default.**

**Four wait on something named:**

| Phase | Waits on | Why that thing and not another |
|---|---|---|
| **5** — snapshots, then retention | the Temporal server (*Stand up the Temporal server*, a milestone of the [Temporal Integration](../temporal-integration/temporal-integration.md) component, tracked as a checkbox in [`sprint.md`](../sprint.md) § *Sprint: Temporal Integration*) — **and only its recurring half** | Running the retention pass *on a cadence* is a scheduled workflow. Only requirement 1's recurrence needs that; the other eight are a policy and a command, and Phase 4 already builds the one-off snapshot. |
| **6** — CPI reads the journal | *Port `review-runs`* — same component, same tracking surface | The evidence sweep exists today only in the frozen bash fleet, which may not be modified. **Not the Temporal server** — a sweep is a batch read, not a schedule. |
| **7** — cross-machine aggregation | a second machine that actually produces runs | Building this before a second machine exists is the speculative-generality trap [`state_passing`](research/raw/state_passing_between_workflow_children.md) §5.2 warns this fleet against. **One gate, not three** — the storage arrangement is settled (commitment 8) and is not a gate. |
| **8** — the poller | Temporal schedules (same server) | Reading a to-do bit and starting a child with no human trigger is what a scheduler does. |

**⚠ EVERY ONE OF THOSE GATES IS DEEPER THAN IT READS, and the depth was added after this table was written.** Both named milestones — *Stand up the Temporal server* and *Port `review-runs`* — sit in [`sprint.md`](../sprint.md) § *Sprint: Temporal Integration* **below** a milestone that says of itself that it *"gates everything below it"*: proving a dispatched invocation is indistinguishable from an operator at a terminal. That component is in turn gated on [Workflow Decomposition](../workflow-decomposition/roadmap.md), which has four open phases. **So Phases 5, 6 and 8 are transitively behind a viability question and a whole sibling component**, and this document previously implied they were behind one checkbox each.

**What that does NOT change:** the gates are still correctly *named*, Phase 6's is still the port and not the server, and Phase 6 can still be pulled forward relative to 5 and 8. **What it changes is the planning assumption** — *"waiting on one checkbox"* and *"waiting on a component plus an unanswered question"* schedule very differently, and the second is the true one.

**Phase 7's gate is unaffected and is still a fact about the world:** a second machine that actually produces runs. Nothing in the Temporal port opens it.

### What a gated phase requires of a phase being built today

**This is the concrete payoff of writing the gated docs.** Writing them out surfaced constraints they place on earlier phases which were invisible while they were roadmap rows. They are tracked here as a table for the same reason the concept-coverage map exists — an unplaced constraint is invisible until something goes looking for it.

| Stated by | The constraint | Discharged by |
|---|---|---|
| [Phase 8](phase8_the_poller.md) r7 | every event carries a **provenance class**, so a reader that *starts work* off a row can filter it by origin | [Phase 3](phase3_the_emit_rule.md) r7(d) |
| [Phase 7](phase7_s3_aggregation.md) § *Where a shared bucket would change things* | every event carries a **credential epoch**, so a replay can exclude events authored under a credential known to have leaked | [Phase 3](phase3_the_emit_rule.md) r7(c) |
| [Phase 7](phase7_s3_aggregation.md) r2 | the content store's shape is ruled such that a shipped bag's cited bytes are resolvable at the destination | [Phase 2](phase2_content_store.md) r7(a) |
| [Phase 7](phase7_s3_aggregation.md) r3 | the sweep reads through a storage interface, so pointing it at a bucket is not a rewrite | [Phase 6](phase6_cpi_reads_the_journal.md) r7 |
| [Phase 7](phase7_s3_aggregation.md) § *The storage arrangement* | the payload spec can express a **per-field** classification, because a classification the payload shape cannot express is one nobody can act on later | [Phase 1](phase1_the_run_bag.md) r7 |
| [Phase 8](phase8_the_poller.md) r7 | the provenance class survives the rebuild, so a rebuilt row can be filtered by origin | [Phase 4](phase4_rebuild_is_a_test.md) r9 |

**A new constraint stated by any gated phase adds a row here and a requirement there.** Stating it only in the gated doc is how such a constraint goes missing.

### What a SIBLING COMPONENT requires of a phase here

**Same mechanism, other direction, and it was empty until 2026-08-19** — when this component was re-read against [Workflow Decomposition](../workflow-decomposition/roadmap.md) and [Temporal Integration](../temporal-integration/temporal-integration.md), both of which were replanned after this roadmap was written. **A constraint a sibling states about our surface is exactly as invisible as one a gated phase states about an early one**, and it has one extra failure mode: nobody here is obliged to read that component's plan.

| Stated by | The constraint | Discharged by |
|---|---|---|
| [WD Phase 5](../workflow-decomposition/phase5_configuration_a_run_absorbed.md) r1 | a **sixth `Journal-` tag** is written into `bag-info.txt` by another component — so the bag's tag namespace needs a stated extension rule: who may add a tag, what a reader does with one it does not know, and **who bumps the schema version**, since a field absent from v1 records is absent for good | **[Phase 3](phase3_the_emit_rule.md) r13** — the extension rule is its own requirement, stated there because this is the first field the bag has taken from outside this component; **r8 stays the event-versioning rule r13 has to answer to** |
| [WD Phase 5](../workflow-decomposition/phase5_configuration_a_run_absorbed.md) r3 | the config-digest reader is a **consumer of bag content**, so it belongs in the consumer enumeration this component owes | [Phase 6](phase6_cpi_reads_the_journal.md) r3, which enumerates consumers rather than asserting them |
| [WD Phase 3](../workflow-decomposition/phase3_dual_mode_children.md) | nine **new entrypoints** land in the directory the bag-open sweep enumerates, so what a standalone child does about the journal is decided by whoever lands them unless it is decided first | **[Phase 9](phase9_one_run_one_identity.md)** r4, r5 |
| [WD Phase 4](../workflow-decomposition/phase4_nothing_invisible.md) | the producer-with-no-consumer gate is extended **beyond one directory**, which brings this component's producers under it | [Phase 6](phase6_cpi_reads_the_journal.md) r3 — **and see the sequencing warning below, because the two can collide** |
| [Temporal Integration](../temporal-integration/temporal-integration.md), Stage B | the run id must be **supplied to** the work rather than generated inside it, or a retry and a replay each produce a new one | **[Phase 9](phase9_one_run_one_identity.md)** r2 |

**⚠ WD Phase 4 and [Phase 6](phase6_cpi_reads_the_journal.md) can collide on schedule, and the collision is one-directional.** Phases 1–5 here ship producers — bag tags, journal events, gap events, snapshots — whose only planned consumer is Phase 6, which is gated on the `review-runs` port. If a fleet-wide producer/consumer gate lands while that gate is still shut, this component's own producers are what turn it red. **The resolution is not to weaken either**: it is that whichever lands second states the other's producers as a named, reasoned exemption with the phase that discharges it. Recorded here so it is a scheduling input rather than a surprise.

**The phases are listed in LOGICAL ROLLOUT ORDER, and the numbers are identifiers rather than that order.** [Phase 9](phase9_one_run_one_identity.md) is listed second and was created last. A phase number names a phase for life, the way a ticket number does. **What gets built *when* across components is the sprint's decision and not this document's** — the gate table above says only what each phase waits on.

**Why Phase 6 is its own phase, split from Phase 8.** At draft the two were one phase gated on the Temporal server, which would have put this component's **only consumer** behind a server nobody has stood up, for four phases of producers. This fleet has the measured record of what happens then — three phases each appended a parent-written observable to one log and no committed tool read any of the three. Splitting them is why Phase 6 waits on the `review-runs` port rather than on the server.

**The checkboxes under each phase below are a reading aid, not a completion record.** They summarise each phase doc's numbered requirements without reproducing them, and **the phase doc is authoritative** — so a fully-checked list here never means a phase is done. A dispatch briefed from this section alone will under-size every phase; most of all Phase 3, whose write-path inventory has no checkbox here. **Brief from the phase doc, and track completion against its numbered requirements.**

---

## Phases

### [Phase 1 — The journal root and the run bag](phase1_the_run_bag.md) ✅ COMPLETE

Stands up the folder structure everything else writes into. One configurable root per machine, one folder per run keyed by run id, one subfolder per concurrent child, and a BagIt (RFC 8493) manifest so a reader can read a folder rather than guess at it. Delivers the payload spec — what goes in the journal and what stays out, with a reason for each exclusion — and records *no database* as a decision with a revisit trigger rather than as an omission. Nothing emits into it yet; the outcome is a folder that validates.

- [x] The root is a config value with a documented default per deployment shape, and nothing in the implementation depends on a home directory existing
- [x] A run's record is one folder keyed by `run_id` — never by path — with one subfolder per concurrent child, so no two writers share a file
- [x] The folder is a valid BagIt bag: `data/` payload, `manifest-sha256.txt` over every payload file, `bagit.txt` declaring version and encoding; a validator re-checksums the payload and reports pass/fail
- [x] `bag-info.txt` carries the event schema version, and the versioning rule is written down: version every event, never change a written one, upgrade it on read
- [x] The bag's state is reported as `open`/`sealed` plus two independent flags — **`redacted`** and **`incomplete`** — and the validator always reports all three fields
- [x] The payload spec is stated as a table with a reason per row — authored output, transcript and execution facts in; code diffs out (commit SHA); Temporal history out (it expires) — **and every row carries a per-field classification slot**
- [x] The root is created `0700` with payload files `0600`, resolution **refuses** a group- or world-writable root or an out-of-path symlink, and **an unresolvable root means the run does not start**
- [x] **Opening the bag is an activity a parent invokes as its first step, and a test enumerates every parent and fails when one does not** — the activity boundary alone does not make the call happen

### [Phase 9 — One run, one identity, one bag](phase9_one_run_one_identity.md)

Settles who names a run. [Phase 1](phase1_the_run_bag.md) keyed the bag by a run id and generated that id inside the journal package, which was right for the one invocation shape that then existed. Two decisions taken since end that: under the Temporal port an id generated inside retried or replayed code is a **different id on every attempt**, and [Workflow Decomposition Phase 3](../workflow-decomposition/phase3_dual_mode_children.md) gives nine children runners of their own, so an invocation that is not a parent can now begin. This phase makes the run id an input supplied by the caller, rules whether a standalone child opens its own bag or joins its parent's, and widens the enumerating sweep to every shape that can start a run.

**Gate: none.** It depends only on [Phase 1](phase1_the_run_bag.md), which is complete. It carries two *deadlines* rather than gates — before Workflow Decomposition ships nine new entrypoints, and before the Temporal port's Stage B wraps anything as an activity.

- [ ] Exactly one authority in the fleet names a run; the second, per-model-invocation `run_id` is retired or explicitly distinguished in code and in prose
- [ ] The run id is an **input** to bag-open rather than minted inside it — **unchecked until its shape is agreed with the Temporal port**, which has its own reasons to name a dispatch
- [ ] Opening a bag twice under one run id yields **one** bag, demonstrated — the shape a retry takes, and the only failure here that is silent
- [ ] A child started on its own is journaled, and the rule for which bag it writes into is stated and enforced, on an input that is **passed rather than inferred**
- [ ] The enumerating sweep covers every shape that can start a run, and every shape it excludes is named in its failure text

### [Phase 2 — The content store and offline checksum verification](phase2_content_store.md)

Stores the bytes behind every claim, named by checksum, and ships a `verify` that resolves every citation from that cache alone — re-checksumming to detect an altered source and confirming the quoted span still occurs. It works with the network off. Three payoffs from one mechanism: it mechanises what `research-critic` does by hand, it makes a shared multi-machine store checkable for corruption, and an evidence checksum equal to a prior stage's is a no-new-evidence stop condition computed rather than judged.

- [ ] Every cited artifact is stored by content checksum under the journal root; nothing is copied in by value
- [ ] `verify` runs against a real prior run with the network disabled and distinguishes verified / missing / tampered by exit code
- [ ] A deliberately altered stored byte is detected, and a quoted span that no longer occurs in its source is reported as a distinct failure from a missing source
- [ ] `evidence_set_hash` is computed per stage and its equality with the prior stage's is exposed as a stop condition
- [ ] Code diffs are carried as a commit SHA and fetched from git, never copied into the store
- [ ] **Capture and resolve are activities**, so storing a source's bytes is not something a caller can forget to do

### [Phase 3 — The emit rule: every write to any store also emits](phase3_the_emit_rule.md)

The core rule, and it is absolute: if any store gets it, the journal gets it, verbatim. The destination is a field rather than a format, which is the property cross-machine work later depends on. Every emitted item records which input produced it and carries a stable machine id. **And this phase answers what happens when the journal cannot be written** — the question that decides whether Phase 4's guarantee means anything.

- [ ] Every write path in the inventory emits a journal event carrying the authored content verbatim, with the destination store as a field
- [ ] The event contract reuses the typed exit record's vocabulary with one declaration per shared concept, and is explicitly a **separate contract** from it
- [ ] **A failed journal write is never silent** — write-ahead ordering where a paired store write exists, a typed gap event and an `incomplete` bag where none does, and the exit record where the journal itself is unwritable
- [ ] Every emitted item records which input item produced it, so a fan-out round can be traced output-to-input
- [ ] Every event carries a stable `edge_id`; the API key authenticates and maps to it and is never the id itself. **The identity's final shape is agreed jointly with the Temporal port**
- [ ] **The event admission contract is specified** — event identity (so a retried activity cannot double-append), who asserts the `edge_id`, a credential epoch, and a provenance class
- [ ] **Secrets are filtered at capture**, before any byte reaches the journal root, with a placeholder event where the filter fires
- [ ] The write-path inventory is complete and enumerated in the phase doc, split into fleet-code writes and model-issued writes
- [ ] **The unwritable-journal signal ships with a committed reader in the same change**, so the one channel this component depends on does not acquire a field nobody reads
- [ ] **The emit is an activity**, not a call a prompt asks a model to remember
- [ ] Measured against the synthesis's 39,772-byte baseline for one `research_minor` cycle, with the observed figure reported with its denominator

### [Phase 4 — Rebuildability is a test](phase4_rebuild_is_a_test.md)

Replays the journal into a scratch directory and diffs the result against the live store. This is what makes Phase 3 enforceable: without it, completeness decays silently the first time a write path is added and its emit is forgotten. The test belongs on the merge path, so a missing emit goes red rather than unnoticed.

- [ ] Replay of the journal reproduces `candidates.md` and `direction.md`, either byte-identical or under a normalisation that is stated and justified, from a starting snapshot forward
- [ ] Deleting one emit from a write path makes the test **fail**, demonstrated
- [ ] The test runs on the merge path against a committed synthetic fixture and against the live journal on a host, with **no skip-when-absent arm**
- [ ] A store the journal cannot rebuild is named as such, with the reason, rather than silently excluded
- [ ] **A journal containing gap events is reported as gapped, with the count and its denominator** — never diffed as though it were complete
- [ ] **Restoring a store from the journal is built and contained** — `destination` resolved through an allowlist, never taken from the event — because that is the capability this component is sold on
- [ ] **A rebuilt store carries the journal's provenance forward**, so every consumer of one is bound by the rules that govern reading the journal

### [Phase 5 — Snapshots, then retention](phase5_snapshots_then_retention.md)

Records what every store held at a point in time into the journal, and only then deletes anything. Deletion removes whole run folders oldest-first until the journal is under its budget, and never past the last snapshot — that ordering is the whole phase, because after Phase 4 the journal is the only thing that can regenerate a store. **One budget governs the whole journal and nothing is exempt from it**; deletion is all-or-nothing per run, because a half-readable run reads as coverage.

**Gate:** the Temporal server, for the recurring half only. Phase 4 builds the one-off snapshot it needs for its own baseline.

- [ ] A recurring retention pass runs on a cadence and brings the journal under budget by the phase doc's stated algorithm
- [ ] The budget is one configuration value, 1 GB by default, **measured over everything under the journal root** — no half exempt, no reserved floor, no second number
- [ ] Deletion is **whole `sealed` run folders, oldest first, until under budget** — never a partial run, never a live bag
- [ ] **The pass has a terminal state and never loops** — at most one snapshot per pass, and an `over-budget-unreclaimable` event with a non-zero exit when budget cannot be reached
- [ ] A deletion dry-run **refuses** to cross the last snapshot, demonstrated against a real journal
- [ ] The retention path is fleet-code only and is not reachable from a model-issued write
- [ ] A rebuild from the last snapshot forward still passes Phase 4's test after a deletion pass
- [ ] A retention pass emits its own journal events, carried into the snapshot **preserving event class and originating `run_id`**, and a bag that is both incomplete and redacted stays distinguishable as both

### [Phase 6 — CPI reads the journal](phase6_cpi_reads_the_journal.md)

Moves the continuous-improvement evidence sweep onto the journal, so it reads one store instead of walking a per-repo pile of JSONL. **This is the consumer for everything Phases 1–4 produce**, and it needs no scheduler and no server. The discipline it enforces is the synthesis's: pair every producer with its consumer. A producer with no consumer is how 262 MB accumulated unread.

**Gate:** the Python port of `review-runs`. Not the Temporal server.

- [ ] The evidence sweep sources the journal, and produces the same findings as the incumbent sweep over one overlapping window
- [ ] Every producer shipped by Phases 1–4 has a named, committed consumer — enumerated, not asserted
- [ ] The wall-clock of the cross-run sweep is measured against journal size, and reported as the first real test of Phase 1's no-database decision
- [ ] **Any gap in the journal appears in the sweep's own output** (r6), so a reader of a CPI report learns what the record does not contain without coming here
- [ ] The sweep reaches its evidence through one storage interface (r7), so pointing it at object storage later is a change of input rather than a rewrite
- [ ] Cross-machine CPI is explicitly not built here

### [Phase 7 — Cross-machine aggregation, writing locally first](phase7_s3_aggregation.md)

Folders sync to object storage under machine id and run id. The local file is the truth at write time and ships asynchronously, so a machine keeps working when the bucket is unreachable. CPI then reads the bucket instead of one local journal — same reader, different input, which is why Phase 6 must not be built as throwaway.

**Gate — one:** a second machine that actually produces runs.

- [ ] Folders ship to `<machine_id>/<run_id>` asynchronously; the machine keeps running with the bucket unreachable
- [ ] A shipped folder validates against its own manifest after transfer, and the content-store objects it references ship with it — or the validation is knowingly partial and the doc says so
- [ ] CPI reads the bucket with no change to the reader written in Phase 6
- [ ] A gap in a shipped folder survives the transfer as a gap
- [ ] Origin is derived from the prefix an object was found under, never from a field inside the object, and a disagreement between the two is reported
- [ ] The bucket blocks public access, encrypts at rest and is reached over TLS, and its credential lives outside the repo and outside the journal

### [Phase 8 — The poller](phase8_the_poller.md)

No new to-do surface is needed — `candidates.md`'s `status: open` already is one, and a to-do bit is a required property of every working record. What is missing is the thing that reads it: a scheduled workflow that queries state and starts children with no human trigger.

**Gate:** Temporal schedules, and a journal with a retention rule so a poller is not walking an unbounded tree.

- [ ] A scheduled workflow reads a store's to-do bit and starts a child with no human trigger, demonstrated end-to-end on one real cue
- [ ] The cue is read from an existing surface; no new cue surface is created
- [ ] A cue that fires twice starts one child, not two
- [ ] The poller reads the store rather than the journal, and the phase doc says why
- [ ] The workflow a cue starts is chosen by the surface in a fixed code-side table, never by the row's content
- [ ] The poller acts only on cues of local origin

---

## Where each adopted concept is planned

All fifteen concepts in [`research/synthesis.md`](research/synthesis.md) are phased. Nothing is deferred out of the plan.

Read the third column as *"which numbered requirement carries it"*, not as a topic tag. Where a cell says **(stated)**, the concept is a recorded decision in that phase's prose rather than a checkable requirement — that is honest and it is different, because a reviewer checking coverage against a requirement list will not find it.

| § | Concept | Phase |
|---|---|---|
| 1 | Stores stay plural; the RECORD is what gets consolidated | **3** (§ *Stores stay plural*, stated), 1 (payload spec, r7) |
| 2 | Every write also emits, completely; the journal rebuilds the store; rebuildability is a test | 1 (r6, versioning), 3 (r1, r9), 4 (r1, r2) |
| 3 | One typed return per step, modality-neutral | 3 (r3) |
| 4 | Artifact by reference plus a checksum, never content by value | 1 (r7, diffs as SHA), 2 (r1, r6) |
| 5 | Lineage on every emitted item | 3 (r5) |
| 6 | Content store, with offline checksum re-verification | 2 (r1–r4) |
| 7 | Each artifact keeps its own format — and no database, deliberately | 1 (r10, no-database) · 1 (format-per-artifact, **stated**) |
| 8 | The accumulated log is an asset; deleting is small, planned work | **5** (r1–r5, r8) |
| 9 | Cue surfaces already exist; what is missing is the poller — and a stable machine id | 3 (r6, edge id), **8** (r1–r3) |
| 10 | Git is the coding machine's binding, not the protocol's | 3 (r2, destination as a field), 7 (r1) |
| 11 | Object storage as the aggregation point, with a local-first write | **7** (r1–r3) |
| 12 | Temporal's own store is telemetry, not memory | 1 (r7, contents table), 5 (r2, the budget) |
| 13 | CPI stays on one machine until a second produces runs | **6** (r5), 7 (r3) |
| 14 | One location, a folder per run, many formats, and a manifest | 1 (r2, r4) |
| 15 | Concurrent children write to their own subfolder | 1 (r3) |

**Four concepts are not from the synthesis and are added by this plan:**

- **The run id is supplied by the caller, and one authority names a run** — [Phase 9](phase9_one_run_one_identity.md) r1–r5. It is here because the synthesis settled that a bag is keyed by run id (§14) and said nothing about *who mints it*, which was a complete answer for the one invocation shape that existed when it was written. Two decisions taken since — the Temporal port's retry-and-replay semantics, and [Workflow Decomposition Phase 3](../workflow-decomposition/phase3_dual_mode_children.md)'s nine standalone child runners — make the minting site load-bearing. Its evidence is not this component's pool: it is [`temporal-integration/research/synthesis.md`](../temporal-integration/research/synthesis.md) §3, which surveyed six systems that name a unit of work and found none that mints the name inside the work.

- **A failed journal write is never silent** — carried by [Phase 3](phase3_the_emit_rule.md) r4, and honoured by Phase 1 (**r8** for the `incomplete` state, **r9** for the refuse-to-start case), Phase 4 (r7), Phase 5 (r9) and Phase 6 (r6). It is here because Phase 4's guarantee is meaningless without it — a journal with silent gaps cannot rebuild anything — and the synthesis does not address it.
- **What goes in is filtered at capture, with redaction as the single stated exception to immutability** — [Phase 3](phase3_the_emit_rule.md) r10 and [Phase 1](phase1_the_run_bag.md) r6. It is here because the component is otherwise **strictly weaker than what exists today**: `.claude/logs/` is equally unfiltered but is machine-local and deletable with no consequence, and after Phase 4 the journal is neither.
- **The protocol is built as activities with an enumerating test behind them, not as a library** — [Phase 1](phase1_the_run_bag.md) r11, [Phase 2](phase2_content_store.md) r8, [Phase 3](phase3_the_emit_rule.md) r12. It is here because a protocol each workflow has to remember to call is optional, and § *Why the protocol is built as activities* names the three controls this fleet has already lost that way.

---

## Dependencies

**On other components:**

- **[Temporal Integration](../temporal-integration/temporal-integration.md)** — two separate items, and conflating them is what gated this component's consumer behind a server at draft:
  - *Stand up the Temporal server* gates Phases 5 and 8. **Nothing in Phases 1–4 or 6 needs it.**
  - *Port `review-runs`* gates **Phase 6**. The evidence sweep exists today only as `scripts/workflows/review-runs.sh` in the frozen bash fleet, which may not be modified.
- **[Workflow Decomposition](../workflow-decomposition/roadmap.md)** — **a two-way dependency that neither roadmap carried until 2026-08-19**, and the traffic runs mostly toward us:
  - **[WD Phase 5](../workflow-decomposition/phase5_configuration_a_run_absorbed.md) depends on [Phase 1](phase1_the_run_bag.md)** — it writes a sixth `Journal-` tag into the bag. **That dependency is satisfied**, and WD's own roadmap says so. What is *not* settled on our side is the extension rule for the tag namespace it writes into; see § *What a SIBLING COMPONENT requires*.
  - **[WD Phase 3](../workflow-decomposition/phase3_dual_mode_children.md) collides with [Phase 9](phase9_one_run_one_identity.md)** — nine new entrypoints in the swept directory. Neither gates the other; whichever lands first sets the contract.
  - **[WD Phase 4](../workflow-decomposition/phase4_nothing_invisible.md) extends a gate over our producers** while our consumer is gated. A scheduling input, recorded above.
- **[`C-076`](../../standards/architecture/research/candidates.md)** — deployment automation is a dependency of synthesis §13's redeploy path, sized as its own sprint, and explicitly not in this component.

### Constraints that run BOTH ways with the Temporal port

**This component now lands ahead of the port, which changes several things from *inherited* to *jointly designed*.** Each of the following is something this component needs from a boundary the port also owns. **They are stated as constraints on a shared design, not as requirements imposed on a component that has not been planned yet** — the port has its own criteria and the answer has to satisfy both.

| What this component needs | Why the port has a stake | Where it is written |
|---|---|---|
| **A machine identity** that is stable across credential rotation, never derived from a key, and present on every event | The port addresses workers, task queues and schedules, and has its own reasons to name a machine. `temporal-integration.md` names no machine or edge id today, so nothing has been decided in either direction | commitment 7; [Phase 3](phase3_the_emit_rule.md) r6 |
| **Event identity that survives an at-least-once retry**, so a retried activity cannot double-append | Idempotency under retry is the port's own rule ([Temporal Standard](../../standards/temporal/temporal_standard.md) §7.1), and the journal is a side effect it has to hold for | [Phase 3](phase3_the_emit_rule.md) r7(a) |
| **A RUN identity supplied by the caller** — stable across the whole run, reproduced by a retry and by a replay, and not generated inside the work | The port already names a dispatch (workflow id plus run id, with two orthogonal reuse policies), and the answer is either that name or a second one that has to be joined to it. **Its reliability pool has already ruled that generation moves to an activity input before Stage B**, so this is the port's own finding rather than a request from here | commitment 1; **[Phase 9](phase9_one_run_one_identity.md) r2** |
| **The activity boundary itself** — bag setup, capture and emit are activities so a run cannot execute without a journal | What is an activity versus a workflow step is the port's composition question, and this component is asking for three specific ones | § *Why the protocol is built as activities* |
| **A storage interface** the evidence sweep reads through, so pointing it at object storage is a change of input | The sweep becomes a ported workflow, and its I/O boundary is the port's activity boundary | [Phase 6](phase6_cpi_reads_the_journal.md) r7 |

**Where the two disagree, neither wins by default — and "neither wins" needs a place, or it is an abdication.** The place already exists: [the local Temporal addendum](../../standards/temporal/claude-dot-files-addendum.md) §A3 *Machine-axis queue naming* is marked OPEN, is the **local addendum** rather than vendored content, and is open on the same question from the port's side. **The identity decision lands there, with this component's three constraints written into it as inputs.** That is what turns *neither wins by default* from a posture into an artifact somebody can read.

**The run identity belongs in the same artifact as the machine identity, for the same reason** — both are a name the port and this component each have cause to mint, and settling them apart is how two names for one thing arrive. **The difference is that the port's side of the run identity is already ruled**: its reliability pool states that generation moves to an activity input before Stage B. So this row is not open on both sides; it is open on ours, and [Phase 9](phase9_one_run_one_identity.md) is where it closes.

The remaining three rows have no equivalent open artifact yet; each is settled in whichever of the two components is being built at the time, and the other cites it rather than restating it.

---

## Open inputs — questions this plan carries forward without answering

These are inputs to the build, not deferred work: each is named at the phase that consumes it, and the corresponding requirement stays unchecked with prose saying why — **built is not proven, and a requirement whose evidence cannot exist yet is not checked.**

1. **What a machine actually is** ([Phase 1](phase1_the_run_bag.md)). Home-directory placement suits the machine we have because Claude Code itself requires a user context. A machine that is not a full Linux environment — HAOS is the live example — may have no user account, and may need a sidecar to run at all. **This does not block the build**: Phase 1's first requirement is that the root is a config value and nothing depends on a home directory. The definition is the unbuildable half.
2. **Event schema versioning, in detail** (Phases 1, 3). The approach is settled — version, never change a written event, upgrade it on read. The mechanism is not.
3. **Journal format at this volume.** A genuine research question and the strongest remaining candidate for a full research cycle. Placed as [`C-079`](../../standards/architecture/research/candidates.md).
4. **Whether the port's dispatch name can BE the run id, or has to be joined to it** ([Phase 9](phase9_one_run_one_identity.md)). The three properties this component needs are stated — supplied by the caller, stable across the whole run, mapped onto whatever the orchestrator already calls a dispatch — and the third decides whether the phase is a parameter change or a migration. **It is not answerable from here**: it needs the port's own naming decision, and that component has its own criteria. Phase 9's requirement 2 stays unchecked until it exists.

**What used to be on this list and is now ruled, recorded so nobody re-opens it:** the storage budget and the snapshot cadence (commitment 6 — one configurable budget, cadence derived from it), the egress and ingress questions (commitment 8 — each edge has access to a bucket and uses it as it sees fit), and whether the memory taxonomy should be re-cut on lifecycle (§ *The four kinds of record* — it is).

---

## Standards-amendment candidates

**Surfaced, never written — the documents below are human-in-the-loop under [`standards-governance.md`](../../../config/rules/standards-governance.md).** Every entry names when it lands, which is what keeps this list from becoming a carried-work ledger. **This roadmap is the writer for these entries.**

1. **APPLIED 2026-08-16 — the entry is kept with its reasoning rather than deleted, and the counts it gave are corrected below.** [`memory-model.md`](../../guide/memory-model.md)'s memory taxonomy **is** re-cut on lifecycle, and the numbered labels are gone from it, from [`exit-protocol.md`](../../standards/exit-protocol.md) and from [`finding-routing.md`](../../standards/finding-routing.md). Both parts landed: §3.1's table is re-cut on *what ends its life* with a fourth shape, and the sweep reached **every surface where the term is still binding** — the three documents named above, the live `review-pr` disposition prompt, `docs/file_structure.txt`'s entries for live surfaces, and the comment, docstring, identifier and assertion-message sites in live Python and `activities/run-claude.sh`. **What it deliberately did not reach is every occurrence that is a *record*** — renaming one of those would make it describe something that never happened — and **that set is declared ONCE, in [`test_retired_vocabulary_is_gone_from_live_surfaces.py`](../../../testing/scripts/tests/unit/test_retired_vocabulary_is_gone_from_live_surfaces.py)'s `RECORD_SURFACES`, with the reason each entry is a record.** It is not re-enumerated here: this entry said *"stated so the claim is checkable"* and then listed the exclusions in prose, which is a second declaration of the same set and drifted from the tree within one pass. **The claim is now machine-checked rather than asserted**, and the gate fails when a live surface acquires a label or when a declared record surface stops carrying one. *(§ Reading the old names above is what keeps every excluded record readable, and it is the first entry a reader of an old label should reach.)* **The counts this entry originally gave were low and the sweep's own instrument was the reason** — it was a line-based, case-sensitive, space-only `grep`, so it could not see a label wrapped across a newline, written `KIND 1`, hyphenated, or spelled `SHARED_KIND_ONE_PATTERNS`. All four spellings survived it and were found by later passes reading the same tree a different way; the gate above reads normalised text for exactly that reason. Renaming any of those would make a record describe something that never happened, and § *Reading the old names* is what keeps all of them readable. **Two counts in this entry were low, measured at application time:** `memory-model.md` carried **16** occurrences, not *"roughly nine beyond §3.1"*; `exit-protocol.md` carried **9**, not eight; and this entry did not name `finding-routing.md`, which carried **1**. § *Reading the old names* above is unchanged and is what keeps every excluded record readable. **The original entry, verbatim:** [`memory-model.md`](../../guide/memory-model.md)'s memory taxonomy is re-cut on lifecycle, and the numbered labels go. § *The four kinds of record* above is the replacement, with the four class names and the old-name mapping. The cost is stated rather than understated: §3.1's three lifecycle shapes are discriminated by one column — *when the to-do bit clears* — and the journal has no to-do bit, so this **replaces that discriminator** and moves §3.1's *"a substrate must provide all three or the model does not fit on it"* clause. It is a re-founding of that document's central table, not a vocabulary swap. **The amendment is two parts and an operator applying only the first would leave the ruling half-satisfied**, so both are named: **(i) the structural re-cut** of §3.1's table as described above, and **(ii) a terminology sweep over the rest of the file** — the labels also appear in §1's opening line, §2's lead-in, §7's heading (*"The seam Kind 2 attaches to"*), §9's table framing and elsewhere, roughly nine occurrences beyond §3.1. `grep -n 'Kind 1\|Kind 2\|Kind 3' docs/guide/memory-model.md` enumerates them. **[`exit-protocol.md`](../../standards/exit-protocol.md) carries eight more** (§1, §2's stratum discussion, §6's table) and is the same amendment.

*The original trigger and consequence, preserved with the entry above and no longer live:* **Trigger: none — this is a ruling to take when it is worth taking. Nothing in this component is blocked on it**, because this roadmap states the taxonomy itself. **Consequence if it never lands:** the operating manual describes two numbered kinds while the fleet keeps four named ones, so the next author to add an observable reads a document with no row for the case they are in.

2. **[`memory-model.md`](../../guide/memory-model.md) §2.4 and §2.5 need an authority note once the two file surfaces become things a journal rebuilds.** Both sections check `direction.md` and `candidates.md` against §1's five properties and describe them as where the answer lives. After [Phase 4](phase4_rebuild_is_a_test.md), **a hand edit that does not also emit is reverted by the next rebuild** — and the highest-value content in both files is hand-written by the operator. **Trigger: Phase 4 landing.** **Consequence if it never lands:** someone edits `candidates.md`, watches the edit disappear, and concludes the tool is broken. [Phase 4](phase4_rebuild_is_a_test.md) r6 is that phase's own statement of this and it explicitly cannot satisfy itself — the warning has to live where readers of those files are.

3. **[`exit-protocol.md`](../../standards/exit-protocol.md) §2 and §2.5 should say they govern the ROUTING CHANNEL, not every typed record the fleet emits.** §2 states *"No field is added on behalf of a consumer that does not exist"* and §2.5 bounds the envelope's fixed part at **4096 bytes**. Both are right for a channel a parent reads in code within seconds. **Read as governing any typed record, they forbid the durable one**, and the argument rests on the two clauses that actually bite rather than on a byte comparison: **§2's no-speculative-fields rule rejects all six** of the journal event's fields, unambiguously, because no parent branches on any of them; and **§2.5's bound is on the fixed part *and explicitly exempts `findings[]` "because it carries two short fields per finding and no prose"** — which is precisely the clause that excludes a record carrying authored content verbatim. *(Resting this on "39,772 bytes exceeds 4096" would be rebuttable at ruling time, since §2.5 already exempts the growing part; the no-prose clause is the one that holds.)* [Phase 3](phase3_the_emit_rule.md) r3 resolves this on the protocol's side — *one vocabulary, two contracts* — and the standard's side is this amendment.

**This amendment also carries two stale rollout pointers in the same file**, because they now point into a retired component: §3's `artifact` marker and §1's cross-reference both name that component's phase docs as the carrier of an obligation. **Re-home both onto this component's [Phase 3](phase3_the_emit_rule.md) checklist under the standard's own existing trigger** — *the first parent other than `review-pr` that routes on a typed record* — so an obligation with a live trigger stops being carried by documents nobody opens. **Trigger: that draft's ratification** — it binds nothing today, so there is nothing to fix yet, only something to fix before it binds. **Consequence if it lands unscoped:** the next durable record is designed against a 4 KB routing bound, or the rule is quietly ignored and stops meaning anything for the channel it *is* right for.

4. **[`memory-model.md`](../../guide/memory-model.md)'s run-log surface is superseded by the journal, and the document still describes it as current.** [Phase 1](phase1_the_run_bag.md) § *The surface this replaces* ruled the open question that phase carried: **the journal is the run log's new home**, not a second surface beside it. `run_log.py`'s three member event types, its join key and its `PUBLISHABLE_FIELDS` classification are carried into the journal's vocabulary rather than discarded — but the join key **changes meaning**, from per-model-invocation to per-run, which is the substantive half of the amendment and not a rename. **The existing `.claude/logs/` archive is deliberately not migrated** (it is gitignored, it is a moving denominator, and it holds no identifier addressing a whole run — a migration would have to synthesise records, which is the one thing a journal must never do). **Trigger: [Phase 3](phase3_the_emit_rule.md) landing**, which is when the cut-over actually happens; before that both surfaces exist and only one is written to, so nothing in the document is yet wrong. **Consequence if it never lands:** the operating manual documents a surface the fleet has stopped writing to, and the next author to add an observable adds it to the dead one.

5. **`docs/standards/architecture/problem-statement.md` element 3 is weakened by evidence in the product pool, and the ruling is the operator's.** The N6 gap and its *re-cut (a)/(b)* framing are [`code_routed_control_flow.md`](../../standards/architecture/research/raw/code_routed_control_flow.md)'s, not this component's pool's — **cited explicitly here because an operator disposing of this item otherwise has no traceable source.** The claim: that pool closes N6 *from outside the agent corpus*, which retires re-cut (b) ("routing on values the model did not author") as a novelty claim and leaves re-cut (a) — cross-process, cross-run, disjoint-context — as the only reading still uncovered by the located literature. **Trigger: none; it lands when the operator disposes of it.** It touches a product-altitude document this component does not own.

6. **The vendored [Testing Standard](../../standards/testing/README.md)'s applicability table still classes the integration tier as *"not yet"*, one directory from where it now exists.** Its row reads *"Service / integration tiers | **not yet** | No service runs here. `run-all.sh` reports these as `SKIP (no tests/integration)`"* — true when vendored, false since [Phase 1](phase1_the_run_bag.md) added `scripts/workflows/temporal/tests/integration/`. **The amendment carries a second clause, and it is the one worth the operator's time:** the tier that now exists is `skipif`-gated on machine-local state, so it reports **PASS having asserted nothing** on a clean runner — the category-present-but-nothing-ran case, which `run-all.sh` cannot tell from a real pass because no pytest exit code carries an executed-test count. That is the same gap [`C-067`](../../standards/architecture/research/candidates.md) already describes for `mutate.sh`, reached through a second tool, so the standard should say what an integration test is and is not evidence for rather than merely that the tier exists. **Trigger: none — a ruling to take.** It is vendored, so it is amended upstream in MDC-Master-Planning and re-vendored, never edited here. **Consequence if it never lands:** the binding document tells the next author the tier does not exist while the tree has one, and the interim answer — [`testing/README.md`](../../../testing/README.md), amended in PR #99 — is repo-local operational doc that does not bind.

7. **[`workflow-scripts.md` § *Location*](../../standards/workflow-scripts.md) has no row for a fleet-wide, activity-only module, and this component is about to land three of them.** The standard's target layout says `{module}/  ONE PER EDGE — assistant/, home_automation/, robotics/, …` with `modules/common/` for *workflows* owned by no edge. `modules/journal/` is neither: it is not an edge, and it holds no workflow — so it opens a third, unruled meaning for a child of `modules/`. [Phase 2](phase2_content_store.md)'s content store and [Phase 3](phase3_the_emit_rule.md)'s emitters are the next two, and each will land the same way by precedent, at which point *"a `modules/` child names a domain"* stops discriminating and a reader cannot tell an edge from a capability without opening files. **Two readings are available and the operator picks one:** amend § *Location* to admit `modules/<capability>/` for a fleet-wide activity-only package, or relocate to `modules/common/journal/` and widen `common/`'s definition beyond workflows. **Trigger: Phase 2 starting**, which is when the precedent stops being a single case. **Consequence if it never lands:** the layout rule quietly becomes descriptive instead of binding, and the ruling gets made by whichever dispatch happens to land Phase 2. *(Surfaced by the standards-auditor on PR #99 and deliberately not acted on there — eleven entrypoint imports and a pinned sweep predicate ride on the current path, so moving the package on an unruled reading is the expensive half.)*

8. **[`exit-protocol.md`](../../standards/exit-protocol.md)'s ratification gate is stated in terms of a component that shipped six phases and was then retired, so the standard can never become binding by its own terms.** `:9` says what makes it binding — *"all five phases complete, the protocol proven across the fleet rather than on one pair, and an explicit operator ratification recorded here with its date"* — and § *Ratification* repeats the condition. The [Memory Management Framework](../memory-management-framework/roadmap.md) shipped **six** phases and was **retired on 2026-08-16**, so the first clause is unsatisfiable as written: there is no fifth-of-five left to complete, and no component left to complete it. **The remedy is reserved to the operator by the document itself** — *"an explicit operator ratification"* — and its § *Ratification* choreographs a whole change rather than one line: strip the DRAFT banner and every remaining `⟨PHASE N⟩` marker, §2's Status column, §2.4's phase-titled heading and its E1(g) framing, §2.1's `run_id` Publish cell and the blockquote beneath it, and §4's two history-narrating passages. **Trigger: the protocol proven across the fleet rather than on one pair** — the gate's own second clause, which is the half that is still meaningful and still unmet. **Consequence if it never lands:** the standard stays permanently unratified on a condition nobody can satisfy, so each reader decides privately whether a draft carrying six phases of evidence binds them; and its `⟨PHASE N⟩` markers, whose declared meaning is *"this answer has not been measured yet"*, go on pointing at the component that measured them. *(PR #96 fixed the dead **instruction** at `:7` — which told an engineer to go build a phase of a retired component — and deliberately left this gate alone. The instruction was addressed to nobody; the gate is addressed to the operator.)*

---

## What is deliberately not built

- **A database.** `state_passing` §4.3.3's format table has one empty row — *queries over accumulated history* — and the reflex is to fill it with SQLite. A per-run folder tree with a checksum manifest answers the questions we actually have. And a database would be something the journal rebuilds, which Phase 4 already makes cheap — so this is a future build opportunity with no rework cost. Revisit on a real query, not on a feeling that a record ought to live in a database. [Phase 6](phase6_cpi_reads_the_journal.md)'s measurement is that trigger's first evidence.
- **An invented manifest format.** BagIt (RFC 8493) exists, its manifest *is* checksums, its `bagit.txt` declares a version, and bags transfer as loose trees or serialized. Three of this plan's requirements come free with it.
- **Cross-machine anything, before a second machine produces runs.** Phase 7's gate, and the same trap `state_passing` §5.2 caught once already.
- **A SECOND dispatch record beside the bag.** The reliability pool now under [Temporal Integration](../temporal-integration/temporal-integration.md) proposes a two-tier state store — a small dispatch record git-native on `refs/dispatch/*` using `git update-ref`'s compare-and-swap, with bulk transcripts left local and referenced by `(machine-id, path)`. **The bag already IS that record**, and it is one tier rather than two by deliberate decision: commitment 1 puts every artifact of a run in one folder precisely so retention, transfer and replay operate on one unit. **What that proposal has and the bag does not is compare-and-swap on the small part**, which is a real property and the reason it is named here rather than dismissed — but it is a mechanism the bag can acquire, not a second store the fleet should carry. **The seam: this component owns the record; the port owns what it needs from the record.** *(Recorded 2026-08-19, when this component was re-read against that pool. It is a note for whoever plans the restart-recovery contract, and it is why [Phase 9](phase9_one_run_one_identity.md) exists.)*
- **Reading Temporal's own history as memory.** Its identity scheme is bounded by retention and continue-as-new starts a fresh history — an execution log with a time limit, not a durable record. Where CPI needs something Temporal knows, the fleet emits it into the journal per step, and the failure path writes a terminal event. **Per step and not at completion**, because a terminated, timed-out or crashed run never reaches completion — and failed runs are CPI's primary input, so a completion-only emit loses exactly the runs the record exists for.

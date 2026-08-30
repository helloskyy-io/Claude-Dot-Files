# Rebuildability is a test — Persistent Memory Protocol

**Component:** [Persistent Memory Protocol](roadmap.md) · **Status:** not started · **Gate:** Phase 3

## What this phase does

The previous phase makes a promise: everything a run writes anywhere also goes into the record. This phase turns that promise into something a machine checks.

The check is simple to describe. Read the record back from the start, write out what it says the tables should contain, and compare that to the tables as they actually are. If they match, nothing is missing. If they do not, something a run wrote never made it into the record — and now a test says so, in red, instead of nobody finding out for six weeks.

**Without this, the promise decays quietly.** Someone adds a new place the fleet writes to, forgets to also write it into the record, and everything keeps working — right up until somebody needs the record and it is short. This repo has produced that failure in several other forms, and a rule written in prose has never once prevented it.

**Terms used here.** The **journal** is the whole record: one folder per run, never edited after the run ends. A **bag** is one run's folder (the name comes from BagIt, the file-layout standard it follows — a folder on disk, never a Docker container). A **store** is any place other than the journal that a run writes to — here, chiefly the committed `tracked/` stores. To **replay** is to read the journal in order and apply each entry. To **rebuild** a store is to replay into an empty directory and produce what that store should hold. A **snapshot** records what a store held at one moment, so a replay can start there rather than at the beginning of history. A **gap event** is [Phase 3](phase3_the_emit_rule.md)'s record of a write that failed.

---

## Why this is its own phase and not Phase 3's last checkbox

The temptation is to fold it in: Phase 3 emits, and *"verify the emit is complete"* looks like a completion criterion of emitting.

**This fleet has the measured record of what happens then.** Three phases each added a parent-written observable to the same run log — `parent_route`, `convergence`, `run_resources` — and no committed tool read any of the three. Folded into any of those phases, the reader would have been the last checklist item of a phase whose headline was already met. **Two of the three shipped without a reader, and only one of those two placed a candidate for it.**

The general shape: **a verification folded into the phase it verifies is a gate the same run walks straight past on its way to the thing it already intended to build.** As its own phase, it is a ruling with a human in between.

There is a second reason, specific to this one. Phase 3's completeness requirement ("every write path emits") is **unfalsifiable as stated** — you cannot check a universal by inspection. Phase 4 converts it into a falsifiable claim: *replay this journal and the store comes back*. That is a different kind of assertion, verified by a different mechanism, which is exactly the split test a phase boundary applies.

---

## Requirements for completion

1. **Replay of the journal reproduces the test set — [`tracked/candidates/`](../../../tracked/candidates/) and [`tracked/operations/`](../../../tracked/operations/)** — either byte-identical, or under a normalisation that is **stated and justified in this doc** — **from a starting snapshot forward** (requirement 2). **Replay records the [Tracked Items](../../standards/documentation/tracked_items_standard.md) §7 contract version it rebuilt against**, so a change to the store's own shape is an upcast on read rather than an unattributable diff. § *Which stores are in the test set* rules the selection and states why the other two stores are out.
2. **A starting snapshot exists, in a stated shape with its own version.** A one-off record of each in-test store's contents, written into the journal at journal start. § *Why replay needs a starting point* below; it needs no scheduler and no server, so it belongs here rather than behind [Phase 5](phase5_snapshots_then_retention.md)'s gate. **The shape is two named sections and a version field**, because [Phase 5](phase5_snapshots_then_retention.md) adds structurally different content to the same artifact later and a mid-stream shape change would violate this component's own *never change a written artifact, upcast on read* rule:
   - **(a) store materialisation** — what each in-test store held at that moment. **Replay applies this section and only this section.**
   - **(b) carried-forward journal-meta events** — retention, gap and redaction events preserved from bags that have been rotated out ([Phase 5](phase5_snapshots_then_retention.md) r8). Empty at Phase 4. **Replay never applies section (b) as a store write**, because materialising a housekeeping record into `tracked/candidates/` is exactly the junk this separation exists to prevent.
3. **Deleting one emit from a write path makes the test fail**, demonstrated. A test that passes when the thing it guards is removed is not a test.
4. **The test runs on the merge path against a committed synthetic fixture, and against the live journal only on a host.** § *Where this test can actually run* below. **The skip-when-absent arm is forbidden.**
5. **A store the journal cannot rebuild is named as such in this doc, with the reason**, rather than quietly excluded from the test set — and out-of-run writes are ruled on explicitly (§ *Which stores are in the test set*).
6. **The change in authority is documented where readers of those stores will find it** — the [`tracked/`](../../../tracked/) stores are now rebuilt from the journal, and the doc that describes them says so. § *Where this has to be written, and why this phase cannot write it* below.
7. **A journal containing gap events is reported as gapped, with the count and its denominator** — never diffed as though it were complete. § *Replaying a record with known holes* below.
8. **Restoring a store from the journal is a built, contained operation** — not an implied consequence of the test. § *Restore is the thing the component is sold on, and it is not the test* below.
9. **A rebuilt store carries the journal's provenance forward, and every consumer of one is a consumer of the journal.** § *What the flip does to everyone downstream* below.

**Requirement 4's containment contract is part of it, not a build detail — and it binds every replay target, not a directory name.** Replay applies journal events to a filesystem, and events carry a `destination` field plus verbatim content. **Every path an event resolves to is validated *after* full normalisation to be inside the replay root** — absolute paths rejected, `..` rejected, symlinks resolved and re-checked, a symlinked root refused. **Replay is a pure event→tree function**: no shell, no template rendering, no execution. It runs with no network and no credentials, and a scratch root is never under `testing/logs/` (which CI uploads as a downloadable artifact).

**Stated as *the replay root* rather than *the scratch root* deliberately.** Requirement 8's restore writes into the working tree, where a `destination` of `config/hooks/` or `.github/workflows/` is a file that gets executed — so a contract scoped to the test's scratch directory would leave the one dangerous replay uncovered. **And requirement 8 adds a second control the test does not need:** a restore resolves `destination` through an explicit allowlist of store paths, taken from requirement 5's enumeration. **The path is never taken from the event.** At [Phase 7](phase7_s3_aggregation.md) the events replayed may originate from another machine, which makes a path-join bug reachable by anything that can write to the shared bucket.

**⚠ That allowlist and the repo's `tracked/` write guard are the same list, and stating it once is the point.** [Tracked Items §1.2](../../standards/documentation/tracked_items_standard.md) requires this repo to add `tracked/` to its path-prefix write guards and grant back only the machine-writable pools — `issues/`, `candidates/`, `standards/` — because moving the stores to the repo root took them out of every existing boundary silently. **A restore that could write `tracked/operations/` would be an autonomous write into the one store reserved to the operator**, arriving through a component that is nominally only regenerating state. Two lists that must agree will eventually disagree, so requirement 5's enumeration is the single statement and the guard is derived from it.

---

## Dependencies

- **[Phase 3](phase3_the_emit_rule.md)** — hard. There is nothing to replay until the emits exist.
- **[Phase 1](phase1_the_run_bag.md)** — replay operates on one run's bag, in order. The per-run folder is what makes this tractable rather than a query across a shared store.

---

## What this phase decides

### The journal becomes the authority, and the stores become things it regenerates

Under Phase 3's rule the journal must be able to rebuild anything any store holds, in the same format. **That flips which one is the truth.** Before this phase, a `tracked/` item is where the answer lives and the journal is a copy of it. After, the journal is where the answer lives and the item file is what you get when you read the journal back. Losing a store stops being a disaster and becomes a rebuild.

**Provenance.** This is event sourcing, and it is Temporal's own model applied one level up: the event history is the truth, and workflow state is regenerated from it by replay.

**The consequence that must not be lost:** once this holds, a rule about deleting old journal data ([Phase 5](phase5_snapshots_then_retention.md)) is **a decision about what the fleet can no longer reconstruct**, not a decision about disk. That reframing is why Phase 5 cannot ship deletion without snapshots, and it originates here.

**Requirement 6 exists because the flip is invisible from the store's own side.** Someone editing a `tracked/` item by hand needs to know their edit is now a write that must also emit — otherwise the next replay silently reverts it, and they will conclude the tool is broken.

### What the flip does to everyone downstream — requirement 9

**The flip is not confined to the test set, and every consumer of a rebuilt store inherits something without being told.** After this phase, reading a `tracked/` item is reading the journal through one layer of regeneration. So:

**Every rule that governs reading the journal governs reading a rebuilt store.** That is the whole requirement, and it is stated here because this is where the flip happens rather than in each of the places that inherits it.

Three consequences follow immediately, and each would otherwise have to be re-derived by whoever hits it:

- **Provenance survives the rebuild.** [Phase 3](phase3_the_emit_rule.md) requirement 7 puts a trust class on every event; a rebuild that drops it hands downstream a store where fleet-authored rows and rows that arrived from somewhere else are indistinguishable. **[Phase 8](phase8_the_poller.md) is the consumer that makes this sharp** — it reads a store's to-do bit and *starts work* — so the field it would need to bound what it acts on has to survive the regeneration that produced the row.
- **The gap reporting survives it too.** A store rebuilt from a gapped journal is a gapped store, and requirement 7's count is what says so.
- **A write to a rebuilt store is a write to the journal.** Anything that edits one of these files — including a later phase's own failure record — emits, or the next rebuild reverts it. Requirement 5 says this for a hand-editor; requirement 9 says it for every automated consumer.

**And after [Phase 7](phase7_s3_aggregation.md), the journal behind a store may include folders that arrived from another machine** — so this rule is what carries origin to consumers that never read object storage directly. Read the other way round, [Phase 8](phase8_the_poller.md)'s *"the store is safe to read precisely because of Phase 4"* is only true to the degree the journal behind it is, which is why that phase filters on origin rather than assuming it.

### Restore is the thing the component is sold on, and it is not the test — requirement 8

**The [roadmap](roadmap.md) sells this component with a sentence this phase did not build:** *"If a table gets corrupted, you regenerate it."* Everything above replays into a scratch directory and **diffs**. Nothing writes the result back.

**That gap is worse than a missing feature, because the missing feature is three lines.** Whoever needs it first will write those three lines, and they will write them against a containment contract that — before this revision — said *"inside the scratch root"*, into a working tree where a `destination` of `config/hooks/` is executable.

**So the restore is built here, with the test, and it is contained here too.** It shares the replay function with the test; what it adds is requirement 4's second control — `destination` resolved through an allowlist from requirement 5's store enumeration, never taken from the event — plus a dry-run that shows what would change before anything does.

**What it is not:** an automatic recovery. Nothing detects corruption and nothing restores on its own. A human decides a store is wrong and runs it. Making that automatic is a different capability with a different failure mode, and this phase does not build it.

### Where this has to be written, and why this phase cannot write it — requirement 6

**The place a reader of those stores learns what they are is [`memory-model.md`](../../guide/memory-model.md) §2.4**, which today checks `tracked/candidates/` against the five durable-record properties and describes them as where the answer lives. After this phase that description is incomplete in a way that costs someone their edit.

**That file is the fleet's operating manual for the working record and is human-in-the-loop** under [`standards-governance.md`](../../../config/rules/standards-governance.md) — no dispatch writes it. So requirement 6 is met by **proposing the amendment, not by making it**: one note on the file surfaces saying they are rebuilt from the journal and that an edit which does not emit does not survive a rebuild. The proposal is placed at [roadmap § *Standards-amendment candidates*](roadmap.md#standards-amendment-candidates), item 2, with this phase's landing as its trigger.

**The requirement is not satisfied by a note in this document.** A reader who is about to hand-edit a `tracked/` item is not reading a phase doc in a component they may never have heard of, and requirement 6's whole content is *where* the warning lives.

### Replaying a record with known holes — requirement 7

[Phase 3](phase3_the_emit_rule.md) rules that a failed journal write is never silent: where nothing can be withheld, the failure appends a **gap event** and the bag is marked `incomplete`. This phase is the main consumer of that marking, and getting it wrong destroys the value of both.

**The naive implementation diffs every bag the same way, and it fails in both directions.** A gapped journal replayed against a live store produces a mismatch — so the test goes red for a reason that has nothing to do with a missing emit, which is the thing it exists to catch. Told to tolerate the mismatch, it goes green over a record that is genuinely short, which is worse.

**So a gap is an input to the test, not a failure of it.** Replay reads the gap events first, reports how many bags are gapped against how many were replayed, and states what each gap covered. **A gapped bag is excluded from the diff and counted, never silently tolerated inside it.** The test's verdict is then two facts rather than one: *the emits that exist are complete*, and *this fraction of the record has holes and here is where.*

**Both numbers matter, and reporting only the first is the failure mode.** "The rebuild test passes" over a journal that is 12% gapped is a true sentence and a misleading one, which is exactly the shape § *Measurement* below asks every figure to carry a denominator for.

### Where this test can actually run — and the precedent the repo already set

**The draft of this doc put the test in `.github/workflows/tests.yml` and stopped there. That does not resolve**, and the contradiction is visible between two of this component's own docs: [Phase 1](phase1_the_run_bag.md) rules the journal machine-local state *"outside the repo"* and notes it is invisible to every consumer that reads the repo; the merge-path job is a GitHub runner with a checkout. **It has the stores — they are in git — and no journal.**

Only two resolutions exist and both are bad as stated: **skip when the journal is absent**, which emits a green check that verified nothing; or **commit a real journal fixture**, putting verbatim transcripts and whatever secrets they carry into git history permanently, in a repo whose CI publishes `testing/logs/` as a downloadable artifact.

**This repo has already fought this exact fight and recorded the answer.** `.github/workflows/tests.yml` deliberately leaves `vendor-standards.sh --check` ungated rather than skip-when-the-clone-is-absent, on the stated reasoning that a skip *"emits a green check that verified nothing, which is worse than the gap it hides"* (tracked at issue #55). **That precedent binds this requirement**, so requirement 4 splits into two arms with different evidence and neither is a skip:

| Arm | Runs where | What it proves | Fixture |
|---|---|---|---|
| **Mechanism** | merge-path CI | replay and dedupe are correct, and requirement 3's negative test goes red | a **committed synthetic** journal + synthetic stores. **No real journal bytes are ever committed** — a stated constraint of this phase, not an assumption |
| **Completeness** | host, via [`testing/run-all.sh`](../../../testing/run-all.sh) | the *real* emits are complete | the live machine-local journal |

**The completeness arm's non-CI status is stated in this doc rather than hidden**, because that is the honest shape: what CI can prove about a machine-local store is that the mechanism works, and claiming more would be the same green-check-that-verified-nothing in a different costume.

### Why replay needs a starting point — the first snapshot

**Requirement 1 has no baseline without it.** [`tracked/candidates/`](../../../tracked/candidates/) carries 133 items (2026-08-28) and every store predates the journal by months; replaying only what [Phase 3](phase3_the_emit_rule.md) emitted forward reproduces a store that starts empty and never matches. The mechanism that supplies the starting state is a **snapshot** — and at draft the only snapshot lived in [Phase 5](phase5_snapshots_then_retention.md), behind the Temporal gate, which made this phase unclosable and its likely resolution silent: weaken requirement 1 to *"reproduces the rows the journal has"*, which passes while the guarantee it stands for is false.

**The error was a one-way constraint read as two-way.** *"Rotation must not ship without a snapshot to stop at"* constrains **rotation**. It says nothing about snapshots needing rotation — and reading it symmetrically parked the snapshot mechanism behind rotation's scheduler. **The first snapshot is a one-off: it records what each store holds right now, and needs no scheduler, no server and no retention policy.** Phase 5 then adds *recurring* snapshots and rotation on top of it.

### Which stores are in the test set, and which are not — RULED

**The pair this section used to name was `candidates.md` and `direction.md`, and both files were deleted by the four-store migration on 2026-08-26.** They were chosen to span a *retention* axis — one never deleted a row, one rotated a ruled row at 90 days — and **neither property survived**: [Tracked Items §4.2](../../standards/documentation/tracked_items_standard.md) prunes every store, on a clock that runs from **last activity** and resets on a `count` increment.

**The axis itself is what stopped needing two stores, and that is the finding rather than the loss.** §4.2 gives *one* store both shapes at once: a `resolved` item is deleted after 14 days, a `rejected` one after 6 months, and an item that keeps recurring is never deleted at all because each increment restarts its clock. So *"the live store deliberately holds less than the journal"* is now exercisable with three items inside a single store, in three different terminal states — a strictly richer case than rotation, and one that no longer costs a second store to reach.

**What a two-store set must span now is the WRITER axis**, because that is the axis on which the four stores actually differ and the axis this test is weakest on:

| Store | Role in the test | Why it is the strictest available choice |
|---|---|---|
| [`tracked/candidates/`](../../../tracked/candidates/) | **Positive control** | The highest-volume machine-written store (133 items, 2026-08-28), and the only one where **three different actors write different parts of one item**: the filer writes the body and `status`, `triage-candidates` writes `decision`, and any later filer increments `count` and appends a line under `## Recurrences`. Every one of those has a run behind it, so a green rebuild here is a real green — and a replay that loses a `count` increment or a third-party `decision` is visibly wrong |
| [`tracked/operations/`](../../../tracked/operations/) | **Negative control** | **§1.2 makes it human-in-the-loop only — no workflow, dispatch or agent ever writes it.** It is the pure form of the out-of-run problem below, and including it deliberately is what turns requirement 5 from an escape hatch into a demonstrated case |

**The negative control is the part worth defending, because it looks like a store you would obviously exclude.** A test set made only of stores the fleet writes is a test set selected for passing. `tracked/operations/` cannot be rebuilt from run-authored events **by construction**, so replaying against it must produce a **reported, non-empty exclusion** with its reason — never a green diff, and never a normalisation that makes an empty rebuild compare equal to nine live items. If it ever does compare equal, the test is measuring nothing and this store is what says so.

**The retention axis is tested inside the positive control**, with three `tracked/candidates/` items chosen in three states — one `open`, one terminal-and-recent, one terminal-and-past-its-window — rather than by adding a third store.

**Two properties the migration handed this phase for free, stated so the build does not re-solve them:**

- **File-per-item collapses most of the normalisation problem.** A missing emit is now a **missing file**, not a missing row inside a file that still parses. Row ordering, column alignment and table-rendering differences — the normalisations § *Normalisation is allowed* warns are how this test stops testing anything — do not arise. What remains is YAML key order and a trailing newline, which is a set small enough to state honestly.
- **The store contract is versioned, so replay pins it.** [Tracked Items §7](../../standards/documentation/tracked_items_standard.md) declares **contract version `v1`** over §2 and §3, and any change to them increments it. Replay records the contract version it rebuilt against, so a store-shape change becomes an **upcast on read** — this component's own *version, never change a written event, upgrade it on read* rule reaching the store side — rather than a silent diff nobody can attribute.

**⚠ THE OUT-OF-RUN PROBLEM DID NOT GO AWAY; IT GOT SHARPER, AND `tracked/operations/` IS WHY.** Per [`memory-model.md`](../../guide/memory-model.md) §2, `/standup` — an interactive session, not a dispatch — is a writer; `ready:` on an operations item and `ratification:` on a standards candidate are the operator's alone; and items in every store have been hand-corrected. **[The emit rule](phase3_the_emit_rule.md)'s inventory is derived by searching the tree, which cannot find an operator session.** So without an ingest for out-of-run writes, replay reverts operator rulings — the highest-value content in the stores — or the test only ever passes under a normalisation that discards them, which makes the guarantee false while the check is green. **Under the four-store shape one whole store is nothing but that case**, which is exactly why it is in the test set rather than quietly outside it.

**Requirement 5 forces the ruling before the phase closes**, and there are exactly two acceptable answers: [the emit rule](phase3_the_emit_rule.md) specifies the out-of-run ingest (**the git commit is the natural emit for the file binding**), or requirement 1 is scoped to run-authored content and the exclusion is recorded below with its reason — **with `tracked/operations/` as the first row of that table either way**. **Silently normalising the difference away is not one of them.**

**`tracked/issues/` and `tracked/standards/` are out of the test set, and the reason is that they add no axis.** They share the shared core of §3, the prune rule of §4.2 and the file-per-item shape with `tracked/candidates/`, and they are smaller. Testing them would raise the *count* in § *Measurement*'s stores-in-set fraction without raising the *strength* of the guarantee, which is the opposite of what that fraction is for. **They are named here rather than omitted**, because a store nobody mentions reads as a store nobody thought of.

**GitHub-hosted surfaces stay the expected hard case**, and the honest position is unchanged: a PR thread's rendered state depends on GitHub's own ordering and on edits made outside any run. **What changed is that they now have a phase of their own** — [the model-issued harvest](phase10_the_model_issued_harvest.md) — whose requirement 4 builds a standing check for that half rather than leaving it to this test set. If they still cannot be rebuilt, **naming them and saying why is the deliverable** — a silent exclusion turns this test green while the guarantee is false, which is worse than having no test.

### Normalisation is allowed, and it is where this test goes wrong

Requirement 1 permits a normalisation. It is necessary — trailing whitespace, line-ending, and ordering differences are not information loss — and it is also the mechanism by which this test quietly stops testing anything. A normalisation broad enough to pass is a normalisation that would pass a store rebuilt wrong.

**So every normalisation is stated in this doc with a justification**, and adding one is a change reviewers see rather than a diff in a helper function. The rule: **a normalisation may discard formatting; it may never discard content.** If a normalisation is required to make two *different* values compare equal, the rebuild is incomplete and the finding is the missing emit.

---

## Implementation checklist

- [ ] Build the starting snapshot: record each in-test store's contents into the journal once, as the point replay starts from
- [ ] Build the replay: read one edge's journal in order, dedupe on event identity, apply each event to a scratch directory — **with requirement 4's path-containment contract, as a pure event→tree function**
- [ ] Build the diff against the live store, with the normalisation set stated in this doc
- [ ] Build the **restore** (requirement 8): the same replay, writing into the working tree, with `destination` resolved through an allowlist from requirement 5's enumeration and a dry-run that shows what would change first
- [ ] Carry provenance and gap state through the rebuild (requirement 9), and confirm a rebuilt row is distinguishable by origin
- [ ] Rule on out-of-run writes: either Phase 3 specifies the ingest, or requirement 1 is scoped and the exclusion is recorded below
- [ ] Run it against the ruled test set — `tracked/candidates/` and `tracked/operations/` — and record the result with its command
- [ ] **Negative test**: remove one emit, confirm the test goes red, restore it
- [ ] Read [Phase 3](phase3_the_emit_rule.md)'s gap events before diffing: **exclude gapped bags from the diff and count them**, and confirm a gapped journal produces a *reported gap* rather than either a red test or a silently tolerated mismatch
- [ ] Enumerate every store, mark each in-test or out-of-test, and give a reason for every exclusion in § *Stores not covered* — **`tracked/operations/` is the first row either way**, per § *Which stores are in the test set*
- [ ] Build the **committed synthetic fixture** (journal + stores) for the merge-path arm, and confirm no real journal bytes are committed
- [ ] Wire the mechanism arm into `.github/workflows/tests.yml` and the completeness arm into [`testing/run-all.sh`](../../../testing/run-all.sh) as host-only — **and confirm no arm skips when its input is absent**
- [ ] **Propose** the authority note for [`memory-model.md`](../../guide/memory-model.md) §2.4 — that the `tracked/` stores are rebuilt from the journal and an edit which does not emit does not survive a rebuild — by landing it at [roadmap § *Standards-amendment candidates*](roadmap.md#standards-amendment-candidates) item 2 with its trigger fired, since that file is human-in-the-loop and no dispatch writes it
- [ ] Record the replay wall-clock against the journal size, with its denominator, in § *Measurement*

---

## Stores not covered

*(Requirement 5. Populated when the phase runs. A store listed here is a stated gap in the guarantee, not an oversight — every row carries why it cannot be rebuilt and what would have to change.)*

| Store | Why it cannot be rebuilt | What would change that |
|---|---|---|

---

## Measurement

*(Populated when the phase runs.)*

Three figures, all with denominators:

- **Replay wall-clock against journal size**, because a rebuild test that takes longer than a CI budget will be disabled rather than fixed.
- **Stores in the test set against the total enumerated**, because that ratio *is* the strength of the guarantee, and stating it as a fraction stops "the rebuild test passes" from being read as "everything rebuilds."
- **Gapped bags against bags replayed, plus bags rotated out behind the snapshot** (requirement 7). A green test over a journal that is 12% gapped is a true sentence and a misleading one; this is the number that keeps it honest. **Counting is dedupe-on-`run_id`** — after [Phase 5](phase5_snapshots_then_retention.md) a gap can be reachable both from its own bag and from the snapshot that carried it forward, and counting it twice inflates the numerator while rotation shrinks the denominator.

---

## Notes and open items

- **This phase is where the completeness rule stops being a promise.** If it is descoped, [Phase 3](phase3_the_emit_rule.md) reverts to an unverifiable universal — and the component's central claim ("the journal can rebuild the store") becomes something nobody has checked. Descoping it is a decision about the component's thesis, not about a test.
- **Replay cost grows with journal size**, and nothing bounds journal size until [Phase 5](phase5_snapshots_then_retention.md) lands the storage budget. If the measured wall-clock is already uncomfortable at Phase 4's journal size, that is the trigger to bring Phase 5 forward — and it is a real finding, not a reason to weaken this test.

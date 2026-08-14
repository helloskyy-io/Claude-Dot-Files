# Phase 4 — Rebuildability is a test

**Component:** [Persistent Memory Protocol](roadmap.md) · **Status:** not started · **Gate:** Phase 3

## What this phase does

The previous phase makes a promise: everything a run writes anywhere also goes into the record. This phase turns that promise into something a machine checks.

The check is simple to describe. Read the record back from the start, write out what it says the tables should contain, and compare that to the tables as they actually are. If they match, nothing is missing. If they do not, something a run wrote never made it into the record — and now a test says so, in red, instead of nobody finding out for six weeks.

**Without this, the promise decays quietly.** Someone adds a new place the fleet writes to, forgets to also write it into the record, and everything keeps working — right up until somebody needs the record and it is short. This repo has produced that failure in several other forms, and a rule written in prose has never once prevented it.

**Terms used here.** The **journal** is the whole record: one folder per run, never edited after the run ends. A **bag** is one run's folder (the name comes from BagIt, the file-layout standard it follows — a folder on disk, never a Docker container). A **store** is any place other than the journal that a run writes to — here, chiefly two committed markdown tables. To **replay** is to read the journal in order and apply each entry. To **rebuild** a store is to replay into an empty directory and produce what that store should hold. A **snapshot** records what a store held at one moment, so a replay can start there rather than at the beginning of history. A **gap event** is [Phase 3](phase3_the_emit_rule.md)'s record of a write that failed.

---

## Why this is its own phase and not Phase 3's last checkbox

The temptation is to fold it in: Phase 3 emits, and *"verify the emit is complete"* looks like a completion criterion of emitting.

**[MMF Phase 6](../memory-management-framework/phase6_read_what_it_writes.md) is the measured record of what happens then.** Three phases each added a parent-written observable to the same run log — `parent_route`, `convergence`, `run_resources` — and no committed tool read any of the three. Folded into any of those phases, the reader would have been the last checklist item of a phase whose headline was already met. **Two of the three shipped without a reader, and only one of those two placed a candidate for it.**

The general shape: **a verification folded into the phase it verifies is a gate the same run walks straight past on its way to the thing it already intended to build.** As its own phase, it is a ruling with a human in between.

There is a second reason, specific to this one. Phase 3's completeness requirement ("every write path emits") is **unfalsifiable as stated** — you cannot check a universal by inspection. Phase 4 converts it into a falsifiable claim: *replay this journal and the store comes back*. That is a different kind of assertion, verified by a different mechanism, which is exactly the split test a phase boundary applies.

---

## Requirements for completion

1. **Replay of the journal reproduces `candidates.md` and `direction.md`** — either byte-identical, or under a normalisation that is **stated and justified in this doc** — **from a starting snapshot forward** (requirement 2).
2. **A starting snapshot exists.** A one-off record of each in-test store's contents, written into the journal at journal start. § *Why replay needs a starting point* below; it needs no scheduler and no server, so it belongs here rather than behind [Phase 5](phase5_snapshots_then_retention.md)'s gate.
3. **Deleting one emit from a write path makes the test fail**, demonstrated. A test that passes when the thing it guards is removed is not a test.
4. **The test runs on the merge path against a committed synthetic fixture, and against the live journal only on a host.** § *Where this test can actually run* below. **The skip-when-absent arm is forbidden.**
5. **A store the journal cannot rebuild is named as such in this doc, with the reason**, rather than quietly excluded from the test set — and out-of-run writes are ruled on explicitly (§ *Which stores are in the test set*).
6. **The change in authority is documented where readers of those stores will find it** — `candidates.md` and `direction.md` are now rebuilt from the journal, and the doc that describes them says so. § *Where this has to be written, and why this phase cannot write it* below.
7. **A journal containing gap events is reported as gapped, with the count and its denominator** — never diffed as though it were complete. § *Replaying a record with known holes* below.

**Requirement 4's containment contract is part of it, not a build detail.** Replay applies journal events to a filesystem, and events carry a `destination` field plus verbatim content. **Every path an event resolves to is validated *after* full normalisation to be inside the scratch root** — absolute paths rejected, `..` rejected, symlinks resolved and re-checked, a symlinked scratch root refused. **Replay is a pure event→tree function**: no shell, no template rendering, no execution. It runs with no network and no credentials, and the scratch root is never under `testing/logs/` (which CI uploads as a downloadable artifact). Stated here because at [Phase 7](phase7_s3_aggregation.md) the events replayed may originate from another edge, which makes a path-join bug reachable by anything that can write to the shared bucket.

---

## Dependencies

- **[Phase 3](phase3_the_emit_rule.md)** — hard. There is nothing to replay until the emits exist.
- **[Phase 1](phase1_the_run_bag.md)** — replay operates on one run's bag, in order. The per-run folder is what makes this tractable rather than a query across a shared store.

---

## What this phase decides

### The journal becomes the authority, and the stores become things it regenerates

Under Phase 3's rule the journal must be able to rebuild anything any store holds, in the same format. **That flips which one is the truth.** Before this phase, `candidates.md` is where the answer lives and the journal is a copy of it. After, the journal is where the answer lives and `candidates.md` is what you get when you read the journal back. Losing the table stops being a disaster and becomes a rebuild.

**Provenance.** This is event sourcing, and it is Temporal's own model applied one level up: the event history is the truth, and workflow state is regenerated from it by replay.

**The consequence that must not be lost:** once this holds, a rule about deleting old journal data ([Phase 5](phase5_snapshots_then_retention.md)) is **a decision about what the fleet can no longer reconstruct**, not a decision about disk. That reframing is why Phase 5 cannot ship deletion without snapshots, and it originates here.

**Requirement 5 exists because the flip is invisible from the store's own side.** Someone editing `candidates.md` by hand needs to know their edit is now a write that must also emit — otherwise the next replay silently reverts it, and they will conclude the tool is broken.

### Where this has to be written, and why this phase cannot write it — requirement 6

**The place a reader of those two tables learns what they are is [`memory-model.md`](../../guide/memory-model.md) §2.4 and §2.5**, which today checks both against the five durable-record properties and describes them as where the answer lives. After this phase that description is incomplete in a way that costs someone their edit.

**That file is [MMF Phase 2](../memory-management-framework/phase2_kind1_framework.md)'s deliverable and is human-in-the-loop** under [`standards-governance.md`](../../../config/rules/standards-governance.md) — no dispatch writes it. So requirement 6 is met by **proposing the amendment, not by making it**: one note on both file surfaces saying they are rebuilt from the journal and that an edit which does not emit does not survive a rebuild. The proposal is carried in [roadmap § *Questioning the Memory Management Framework*](roadmap.md#questioning-the-memory-management-framework), challenge 4, and in this component's pull-request body.

**The requirement is not satisfied by a note in this document.** A reader who is about to hand-edit `candidates.md` is not reading a phase doc in a component they may never have heard of, and requirement 6's whole content is *where* the warning lives.

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

**Requirement 1 has no baseline without it.** `candidates.md` carries 75 rows and `direction.md` predates the journal by months; replaying only what [Phase 3](phase3_the_emit_rule.md) emitted forward reproduces a store that starts empty and never matches. The mechanism that supplies the starting state is a **snapshot** — and at draft the only snapshot lived in [Phase 5](phase5_snapshots_then_retention.md), behind the Temporal gate, which made this phase unclosable and its likely resolution silent: weaken requirement 1 to *"reproduces the rows the journal has"*, which passes while the guarantee it stands for is false.

**The error was a one-way constraint read as two-way.** *"Rotation must not ship without a snapshot to stop at"* constrains **rotation**. It says nothing about snapshots needing rotation — and reading it symmetrically parked the snapshot mechanism behind rotation's scheduler. **The first snapshot is a one-off: it records what each store holds right now, and needs no scheduler, no server and no retention policy.** Phase 5 then adds *recurring* snapshots and rotation on top of it.

### Which stores are in the test set, and which are not

Requirement 4 forces the honest answer rather than a convenient one. The two named in requirement 1 are chosen because they are the strictest available pair:

- **`candidates.md` never deletes a row**, so a rebuild that loses anything is visibly wrong.
- **`direction.md` rotates a ruled row at 90 days**, so it exercises the case where the live store deliberately holds *less* than the journal — the rebuild target is the store's current state, not the journal's full history, and getting that wrong in either direction is a bug.

**Together they cover both retention shapes in the file binding**, which is the reason to test two rather than one.

**⚠ AND THEY ARE ALSO THE TWO STORES WHOSE MOST VALUABLE FIELDS ARE WRITTEN OUTSIDE ANY RUN.** Per [`memory-model.md`](../../guide/memory-model.md) §2, the operator alone sets `direction.md`'s `status`; `/standup` — an interactive session, not a dispatch — deletes rotated rows and corrects stale ones; `candidates.md` rows have been hand-corrected. **[Phase 3](phase3_the_emit_rule.md)'s inventory is derived by searching the tree, which cannot find an operator session.** So without an ingest for out-of-run writes, replay reverts operator rulings — the highest-value content in either file — or the test only ever passes under a normalisation that discards them, which makes the guarantee false while the check is green.

**Requirement 5 forces the ruling before the phase closes**, and there are exactly two acceptable answers: Phase 3 specifies the out-of-run ingest (**the git commit is the natural emit for the file binding**), or requirement 1 is scoped to run-authored content and the exclusion is recorded below with its reason. **Silently normalising the difference away is not one of them.**

**GitHub-hosted surfaces are the expected hard case**, and the honest position is that they may land in requirement 4 rather than requirement 1: a PR thread's rendered state depends on GitHub's own ordering and on edits made outside any run. If a surface cannot be rebuilt, **naming it and saying why is the deliverable** — a silent exclusion turns the test green while the guarantee is false, which is worse than having no test.

### Normalisation is allowed, and it is where this test goes wrong

Requirement 1 permits a normalisation. It is necessary — trailing whitespace, line-ending, and ordering differences are not information loss — and it is also the mechanism by which this test quietly stops testing anything. A normalisation broad enough to pass is a normalisation that would pass a store rebuilt wrong.

**So every normalisation is stated in this doc with a justification**, and adding one is a change reviewers see rather than a diff in a helper function. The rule: **a normalisation may discard formatting; it may never discard content.** If a normalisation is required to make two *different* values compare equal, the rebuild is incomplete and the finding is the missing emit.

---

## Implementation checklist

- [ ] Build the starting snapshot: record each in-test store's contents into the journal once, as the point replay starts from
- [ ] Build the replay: read one edge's journal in order, dedupe on event identity, apply each event to a scratch directory — **with requirement 4's path-containment contract, as a pure event→tree function**
- [ ] Build the diff against the live store, with the normalisation set stated in this doc
- [ ] Rule on out-of-run writes: either Phase 3 specifies the ingest, or requirement 1 is scoped and the exclusion is recorded below
- [ ] Run it against `candidates.md` and `direction.md` and record the result with its command
- [ ] **Negative test**: remove one emit, confirm the test goes red, restore it
- [ ] Read [Phase 3](phase3_the_emit_rule.md)'s gap events before diffing: **exclude gapped bags from the diff and count them**, and confirm a gapped journal produces a *reported gap* rather than either a red test or a silently tolerated mismatch
- [ ] Enumerate every store, mark each in-test or out-of-test, and give a reason for every exclusion in § *Stores not covered*
- [ ] Build the **committed synthetic fixture** (journal + stores) for the merge-path arm, and confirm no real journal bytes are committed
- [ ] Wire the mechanism arm into `.github/workflows/tests.yml` and the completeness arm into [`testing/run-all.sh`](../../../testing/run-all.sh) as host-only — **and confirm no arm skips when its input is absent**
- [ ] **Propose** the authority note for `memory-model.md` §2.4 and §2.5 — that both files are rebuilt from the journal and an edit which does not emit does not survive a rebuild — in the PR body, since that file is human-in-the-loop and no dispatch writes it
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
- **Gapped bags against bags replayed** (requirement 7). A green test over a journal that is 12% gapped is a true sentence and a misleading one; this is the number that keeps it honest.

---

## Notes and open items

- **This phase is where the completeness rule stops being a promise.** If it is descoped, [Phase 3](phase3_the_emit_rule.md) reverts to an unverifiable universal — and the component's central claim ("the journal can rebuild the store") becomes something nobody has checked. Descoping it is a decision about the component's thesis, not about a test.
- **Replay cost grows with journal size**, and nothing bounds journal size until [Phase 5](phase5_snapshots_then_retention.md) lands snapshots. If the measured wall-clock is already uncomfortable at Phase 4's journal size, that is the trigger to bring Phase 5 forward — and it is a real finding, not a reason to weaken this test.

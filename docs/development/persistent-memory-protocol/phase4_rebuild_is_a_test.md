# Phase 4 — Rebuildability is a test

**Component:** [Persistent Memory Protocol](roadmap.md) · **Status:** not started · **Gate:** Phase 3

Replays the journal into a scratch directory and diffs the result against the live store.

**This is the phase that makes [Phase 3](phase3_the_emit_rule.md)'s completeness rule enforceable.** Without it, completeness degrades silently the first time a write path is added and the emit is forgotten — a failure this repo has produced in several other forms, and one that a prose rule has never once prevented.

---

## Why this is its own phase and not Phase 3's last checkbox

The temptation is to fold it in: Phase 3 emits, and *"verify the emit is complete"* looks like a completion criterion of emitting.

**[MMF Phase 6](../memory-management-framework/phase6_read_what_it_writes.md) is the measured record of what happens then.** Three phases each added a parent-written observable to the same run log — `parent_route`, `convergence`, `run_resources` — and no committed tool read any of the three. Folded into any of those phases, the reader would have been the last checklist item of a phase whose headline was already met. **Two of the three shipped without a reader, and only one of those two placed a candidate for it.**

The general shape: **a verification folded into the phase it verifies is a gate the same run walks straight past on its way to the thing it already intended to build.** As its own phase, it is a ruling with a human in between.

There is a second reason, specific to this one. Phase 3's completeness requirement ("every write path emits") is **unfalsifiable as stated** — you cannot check a universal by inspection. Phase 4 converts it into a falsifiable claim: *replay this journal and the store comes back*. That is a different kind of assertion, verified by a different mechanism, which is exactly the split test a phase boundary applies.

---

## Requirements for completion

1. **Replay of the journal reproduces `candidates.md` and `direction.md`** — either byte-identical, or under a normalisation that is **stated and justified in this doc**.
2. **Deleting one emit from a write path makes the test fail**, demonstrated. A test that passes when the thing it guards is removed is not a test.
3. **The test runs in the merge-path gate** — `.github/workflows/tests.yml`, wired through [`testing/run-all.sh`](../../../testing/run-all.sh).
4. **A store the journal cannot rebuild is named as such in this doc, with the reason**, rather than quietly excluded from the test set.
5. **The authority inversion is documented where readers of those stores will find it** — `candidates.md` and `direction.md` become projections, and the doc that describes them says so.

---

## Dependencies

- **[Phase 3](phase3_the_emit_rule.md)** — hard. There is nothing to replay until the emits exist.
- **[Phase 1](phase1_the_run_bag.md)** — replay operates on one run's bag, in order. The per-run folder is what makes this tractable rather than a query across a shared store.

---

## What this phase decides

### The stores become projections, and that is the point

Under Phase 3's rule the journal must be able to **rebuild anything any store holds, in the same format**. That inverts the authority: the stores stop being sources of truth and become **projections** of the journal. `candidates.md` becomes a materialized view; recovery becomes replay.

**Provenance.** This is event sourcing, and it is Temporal's own model applied one level up: event history is the truth, workflow state is a projection rebuilt by replay.

**The consequence that must not be lost:** once this holds, a pruning rule ([Phase 5](roadmap.md#phase-5--snapshots-then-retention-gated-temporal-server)) is **a decision about what the fleet can no longer reconstruct**, not a decision about disk. That reframing is why Phase 5 cannot ship rotation without snapshots, and it originates here.

**Requirement 5 exists because the inversion is invisible from the store's own side.** Someone editing `candidates.md` by hand needs to know their edit is now a write that must also emit — otherwise the next replay silently reverts it, and they will conclude the tool is broken.

### Which stores are in the test set, and which are not

Requirement 4 forces the honest answer rather than a convenient one. The two named in requirement 1 are chosen because they are the strictest available pair:

- **`candidates.md` never deletes a row**, so a rebuild that loses anything is visibly wrong.
- **`direction.md` rotates a ruled row at 90 days**, so it exercises the case where the live store deliberately holds *less* than the journal — the rebuild target is the store's current state, not the journal's full history, and getting that wrong in either direction is a bug.

**Together they cover both retention shapes in the file binding**, which is the reason to test two rather than one.

**GitHub-hosted surfaces are the expected hard case**, and the honest position is that they may land in requirement 4 rather than requirement 1: a PR thread's rendered state depends on GitHub's own ordering and on edits made outside any run. If a surface cannot be rebuilt, **naming it and saying why is the deliverable** — a silent exclusion turns the test green while the guarantee is false, which is worse than having no test.

### Normalisation is allowed, and it is where this test goes wrong

Requirement 1 permits a normalisation. It is necessary — trailing whitespace, line-ending, and ordering differences are not information loss — and it is also the mechanism by which this test quietly stops testing anything. A normalisation broad enough to pass is a normalisation that would pass a store rebuilt wrong.

**So every normalisation is stated in this doc with a justification**, and adding one is a change reviewers see rather than a diff in a helper function. The rule: **a normalisation may discard formatting; it may never discard content.** If a normalisation is required to make two *different* values compare equal, the rebuild is incomplete and the finding is the missing emit.

---

## Implementation checklist

- [ ] Build the replay: read one edge's journal in order, apply each event to a scratch directory
- [ ] Build the diff against the live store, with the normalisation set stated in this doc
- [ ] Run it against `candidates.md` and `direction.md` and record the result with its command
- [ ] **Negative test**: remove one emit, confirm the test goes red, restore it
- [ ] Enumerate every store, mark each in-test or out-of-test, and give a reason for every exclusion in § *Stores not covered*
- [ ] Wire into [`testing/run-all.sh`](../../../testing/run-all.sh) and confirm it runs in `.github/workflows/tests.yml`
- [ ] Add the projection note to wherever `candidates.md` and `direction.md` describe their own authority, so a hand-editor is warned
- [ ] Record the replay wall-clock against the journal size, with its denominator, in § *Measurement*

---

## Stores not covered

*(Requirement 4. Populated when the phase runs. A store listed here is a stated gap in the guarantee, not an oversight — every row carries why it cannot be rebuilt and what would have to change.)*

| Store | Why it cannot be rebuilt | What would change that |
|---|---|---|

---

## Measurement

*(Populated when the phase runs.)*

Two figures, both with denominators: **replay wall-clock against journal size**, because a rebuild test that takes longer than a CI budget will be disabled rather than fixed; and **the count of stores in the test set against the total enumerated**, because that ratio *is* the strength of the guarantee and stating it as a fraction stops "the rebuild test passes" from being read as "everything rebuilds."

---

## Notes and open items

- **This phase is where the completeness rule stops being a promise.** If it is descoped, [Phase 3](phase3_the_emit_rule.md) reverts to an unverifiable universal — and the component's central claim ("the journal can rebuild the store") becomes something nobody has checked. Descoping it is a decision about the component's thesis, not about a test.
- **Replay cost grows with journal size**, and nothing bounds journal size until [Phase 5](roadmap.md#phase-5--snapshots-then-retention-gated-temporal-server) lands snapshots. If the measured wall-clock is already uncomfortable at Phase 4's journal size, that is the trigger to bring Phase 5 forward — and it is a real finding, not a reason to weaken this test.

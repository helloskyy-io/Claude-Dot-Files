# Phase 5 — Convergence-based stopping

**Component:** [Memory Management Framework](roadmap.md) · **Status: not started**

Replaces a **model-asserted** convergence flag with a **computed** one.

`review-pr` already emits `converged: true|false` (`children/review-pr.sh:355`) under a documented single-pass severity heuristic — *"the first pass whose findings are ALL preventive … IS convergence"* (`:323`) — and already mandates that a persisting finding reuse its prior `id` slug verbatim across passes (`:221`, `:357`). Nothing in either fleet routes on that flag today; it is an unconsumed, human-facing signal.

So this phase is not greenfield, and framing it as such would have cost twice: it would have built a second finding-identity scheme beside a shipped one, and it would have exempted itself from a parity audit it needs. What it actually does is narrower and stronger — **move convergence from a class-(iii) assertion the model makes about one pass to a class-(ii) delta computed across two.** *"Did this pass find anything not in the previous pass's result?"* is answerable against two typed payloads and is not answerable against two prose logs.

---

## Requirements for completion

Done when:

1. **The incumbent is dispositioned, not ignored.** A `§Capability Parity` audit records what the shipped `converged` field did, and whether this phase reuses the key, replaces it, or introduces a new one — with the consequence for any existing reader or writer of the current semantics stated either way.
2. **The delta is computed over the stable ids the child already emits** — no second identity scheme.
3. **The stopping predicate is a total function** whose residual arm is a named recorded state, consistent with [Phase 3](phase3_typed_exit_record.md)'s contract.
4. **Every documented false-convergence mode is named with the specific check that separates it from real convergence**, and each check has a test proven able to fail.
5. **The rule is validated against [Phase 1](phase1_measure_the_channel.md) E7's replay before it gates anything live**, and the existing loop-back bound stays in force until that measurement supports replacing it.

---

## Dependencies

- **[Phase 3](phase3_typed_exit_record.md) — hard, and this is the real gate.** Findings are emitted by exactly one child, `review-pr`, which Phase 3 migrates by name. That is all this phase needs to consume.
- **[Phase 4](phase4_fleet_migration.md) — soft.** Its breadth produces nothing this phase reads. It is required only for fleet-wide coverage of the resulting signal, so **this phase may run in parallel with Phase 4** rather than behind it. Scheduling it behind Phase 4 would delay the component's strongest justification by a full phase for no input it needs.
- **[Phase 1](phase1_measure_the_channel.md) E7 — hard for requirement 5.** E7 replays archived `pr_review:` blocks and reports how often the delta was empty, how often `converged: true` was asserted, how those two disagree, and whether the stable-id convention actually holds in practice. **If E7 finds the delta is never empty, the predicate never fires and this phase says so before it is built. If E7 finds stable ids do not hold in practice, step 1 becomes this phase's hard part rather than its premise.**
- **Cites but does not re-derive:** `docs/standards/architecture/research/raw/convergence_stopping.md` — P11 (convergence detection *requires* typed comparable finding records) and §5.1–5.7 (the case against a naive "stop when nothing new" rule).
- **Required by:** [Autonomous Operation](../autonomous-operation/autonomous-operation.md) — its *observable exit criteria* milestone names a convergence signal, explicitly *"not a turn count."*
- **Interacts with:** `docs/standards/workflow-scripts.md` § Bounded composition, which already states *prefer convergence over counting* and *do not legislate a pass count from a single run*. This phase implements what that standard prefers; it does not amend it.

---

## Implementation steps

### 1. Disposition the incumbent before building beside it

- [ ] Record what the shipped `converged` field means today (a single-pass severity heuristic — all findings preventive), what emits it, and what reads it. `grep` establishes the last one; the answer today appears to be nothing programmatic, and if that has changed by the time this phase runs, the change is the finding
- [ ] **Rule on the key.** Does the computed signal reuse `converged` — silently redefining an already-shipped field's meaning for any future reader — or take a new name alongside it? Either is defensible; leaving it ambiguous is how a shipped key acquires two meanings
- [ ] Record the semantic difference plainly: the incumbent asks *"are this pass's findings all preventive?"*; the replacement asks *"is anything still open?"* **E7 measured how often they disagree: they do not — 1 of 1, on the only block where both have a value, they agree.** (An earlier reading of E7 reported a disagreement; it computed the delta over the cumulative id set and was corrected.)
- [ ] Write the `§Capability Parity` table: every behaviour of the incumbent flag mapped to ported or consciously dropped, no silent drops

### 2. Establish finding identity — on the convention that already exists

> **Amended by [Phase 1](phase1_measure_the_channel.md) E7 (2026-08-08, corrected in the same day's refine pass).** The convention **holds on the added direction**: over the 7 consecutive-pass pairs in the archive, 25 ids were added and 0 of the 25 adjudicated as a restatement of an existing finding under a new slug. This step is this phase's **premise, not its hard part** — as its dependency clause anticipated.
>
> **One half of that amendment was withdrawn and this step must not rely on it.** The companion figure "**0** ids were dropped or renamed" is **not a measurement**: the `pr_review:` block is **cumulative** (`review-pr.sh:221` — each pass restates every prior id and updates its `disposition` in place), so an id cannot be dropped whatever the reviewer does. Id-disappearance carries no information here.
>
> Three structural facts this step must respect: **`pass` numbers are not dense** (PR #31 runs 1, 2, 4 — "consecutive" comes from block order, never from the integer); **an id is stable while its `title` is not** (#45 reuses an id across passes with a completely rewritten title and consequence, because pass 2 restates it as fixed); and **an id's presence is not its liveness** — `disposition` is what says whether a finding is still open, and identity plus disposition together are what step 3 computes over. Identity itself is computed from the id alone.

- [x] Start from the shipped convention: a persisting finding reuses its prior `id` slug verbatim, and only genuinely-new findings get new slugs. **The identity mechanism is not this phase's invention; verifying that it holds is this phase's work**
- [x] Confirm against E7's measurement how often the same finding recurred under the same id versus under a new one. A convention the prompt mandates and the model does not follow is not an identity mechanism, and the delta computed over it would report novelty that is only rewording
- [ ] State what the identity is computed from and what it deliberately ignores. Rewording must not break it — the same model re-describing the same defect in different words is the normal case, not the edge case
- [ ] Record what fraction of findings cannot be given stable identity and what happens to them. **They are the residual arm's population, and pretending they do not exist is how the predicate reports convergence it did not observe**

### 3. Build the delta

> **Amended by [Phase 1](phase1_measure_the_channel.md) E7 (2026-08-08) — the set-difference mechanism is SOUND, but the set it is computed over must change.** An earlier version of this amendment said the predicate never fires and directed this step onto a severity-based signal. **That was withdrawn the same day**; the paragraph below replaces it, and Phase 1's E7 ruling records both versions with the reason.
>
> Over the entire archive — 7 consecutive-pass pairs, the only 5 PRs that have ever had more than one review pass — the delta over **all** finding ids was empty **0 times**. That is a property of the reporting shape, not of the fleet: the `pr_review:` block is cumulative, so the id set cannot shrink and its delta cannot empty, at any N.
>
> **Computed over the OPEN subset — findings whose `disposition` is not `fixed` / `deferred` / `rejected` / `noted` — the same 7 pairs give an empty delta 2 times**, and the open set reaches **zero once: PR #42 pass 2, which is the only `MERGE` and the only `converged: true` in the archive.** The incumbent heuristic and this computation therefore **agree** where both have a value (1 of 1), not disagree.
>
> **Do NOT build this on a `severity` field.** `severity` appears on **0 of the 195** archived findings. `disposition` appears on all 195.
>
> **One measured distinction this step must encode:** the stopping condition is the open set being **EMPTY**, not merely **UNCHANGED**. At #58 pass 2→3 the open set was unchanged and non-empty (2 → 2, nothing added, nothing closed); a rule reading "the open set stopped changing" would have stopped there and been wrong. A rule reading "nothing is open" would not have.
>
> **Nothing else in this component is cancelled** — Phase 3's consumers and Phase 4's `subtype` routing are independent of this.

- [ ] **Compute the delta over the OPEN subset, and make the stopping condition "the open set is empty" — not "the open set is unchanged."** Both halves are measured (2 of 7 empty; one unchanged-but-non-empty pair where stopping would have been wrong). State where `disposition` comes from in the [Phase 3](phase3_typed_exit_record.md) envelope and which of its six values count as closed
- [ ] **Record that the open-set-empty predicate has exactly ONE archived positive observation** (#42 pass 2, of 14 blocks). That is enough to establish the mechanism fires; it is **not** a firing rate, and this phase must not quote it as one
- [ ] Compute the all-ids delta as well, and emit it — **as an input to step 4's windowed check and as telemetry, not as the stopping condition.** **The delta is a computed observable even though the findings are model-authored** — the records were chosen by the model, the delta was not, and the delta is what the predicate reads. This classification is the whole reason the phase is worth doing; misclassifying it would put the one genuinely reliable signal this component produces into the arm reserved for things that can be confidently wrong
- [ ] Emit the delta's output as a typed value in the record, consistent with the [Phase 3](phase3_typed_exit_record.md) envelope and its publish classification, so a parent reads it rather than recomputing it

### 4. Defend against false convergence — each mode, each check

Each of the following is a documented way a naive "nothing new" rule reports convergence that is not there. Each needs its own check and its own test.

- [ ] **A degraded pass that emits nothing.** An empty finding set from a failed, truncated or turn-capped pass is indistinguishable from an empty set from a clean pass unless the predicate requires evidence the pass actually ran and completed. Check: the run's own outcome record must show a completed pass before its emptiness counts as a signal. The fleet's measured turn-cap rate is 0.9% (4/443), so this is rare and real
- [ ] **An oscillating finding set.** Two passes alternating between two sets each look "new" to a pairwise comparison and never converge; a comparison over a longer window sees the cycle. Check: compare against a window, not only the immediately preceding pass
- [ ] **An adaptively biased reviewer.** A reviewer that has learned the shape of the previous pass's findings can stop producing them without the underlying issues being resolved. Check: the predicate must not be the only stopping authority — the bound from step 6 remains
- [x] **A reviewer that never emits an empty pass.** The inverse failure: a pass that always finds *something* means the predicate never fires and the loop runs to its bound. Check: this is E7's measurement, taken in Phase 1 precisely so it can cancel this phase rather than be discovered inside it. **ANSWERED — and the answer depends entirely on which set is read.** Every pass adds *some* new id (7 of 7), so over the cumulative id set the mode is real and the predicate would never fire. Over the **open** subset it is not the norm: the open set emptied on 1 of 14 blocks and its delta emptied on 2 of 7 pairs. **The mode is defended against by reading the open subset, which step 3 now specifies** — not by abandoning set-difference
- [ ] **A pass that closes nothing and adds nothing.** Measured at #58 pass 2→3: the open set held at 2, unchanged, with nothing added and nothing closed. An "open delta is empty" rule stops here; an "open set is empty" rule does not. Check: the predicate reads emptiness of the set, and a stalled-but-non-empty open set routes to the bound in step 6 rather than to convergence
- [ ] Each check has a test, and each test is proven able to fail by mutating the input it guards. A test that cannot fail records a protection that does not exist

### 5. Make the predicate total

- [ ] The predicate returns a named state in every case, including "could not determine" — which is the computed *could-not-check* arm [Phase 3](phase3_typed_exit_record.md) defined, reused here rather than re-invented
- [ ] The residual arm is recorded, not silently defaulted. Every surveyed orchestrator has an answer for the unmatched case and none of them is "fall through"
- [ ] Absence of a comparable prior pass routes to the residual arm, never to "converged"

### 6. Validate before gating

- [ ] Replay the predicate over archived multi-pass runs (E7's corpus) and record: how often it would have fired, how often it would have fired *early*, and how often it would never have fired
- [ ] Compare against what the fixed loop-back bound actually did on those same runs, and against what the incumbent `converged` flag asserted. The bound exists because self-correction plateaus and a run was observed reaching eight review passes with pass 8 reviewing the same tree as pass 7 — the predicate has to beat that behaviour, not merely differ from it
- [ ] Keep the existing bound in force as a ceiling. Convergence is the honest stopping condition; the bound is the runaway guard, and they are not substitutes
- [ ] **Do not legislate a new pass count from this measurement.** A measured run and a cited plateau band are both evidence, neither is a constant — if a floor must exist before the predicate is trusted, state it as temporary with its reasoning

### Close-out

- [ ] Every requirement met with its evidence in this doc, including measurement numbers with their denominators
- [ ] [Autonomous Operation](../autonomous-operation/autonomous-operation.md) is told what signal it can consume and what its residual arm means — its exit-criteria milestone depends on this and should not have to re-derive it
- [ ] Any standards implication is surfaced in the [roadmap](roadmap.md#standards-amendment-candidates), not written

---

## Notes and gotchas

- **This phase is the component's strongest justification, and it is also the one most able to produce a confident wrong answer.** A stopping rule that fires early ends work that was still productive, and it does so silently — there is no failing test, just a shorter run. Every check in step 4 exists because the failure has no natural alarm.
- **The justification is narrower than "nothing detects convergence today," and the narrower version is the true one.** A flag exists; nothing routes on it; it answers a different question. Claiming greenfield here would be the same overclaim the [roadmap](roadmap.md#key-decisions) warns against on the routing side, and a reviewer who reads `review-pr.sh` would break it.
- **Nothing in the evidence base measures the error rate of any non-model observable used as a routing channel.** That gap is stated in the research as a gap; step 6 is the closest this fleet gets to closing it locally, and its numbers should be written down as such rather than presented as validation.

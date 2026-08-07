# Phase 5 — Convergence-based stopping

**Component:** [Memory Management Framework](roadmap.md) · **Status: not started**

The capability the typed record exists for, and the component's strongest justification: *"did this pass find anything not in the previous pass's result?"* is answerable against two typed payloads and is **not** answerable against two prose logs. Unlike the routing argument, this one has no working incumbent to beat — nothing in the fleet detects convergence today, and the current bound is a fixed loop-back count.

---

## Requirements for completion

Done when:

1. **Findings carry stable identity across passes** — "the same finding" is a computed fact, not a string comparison over prose.
2. **The stopping predicate is a total function** whose residual arm is a named recorded state, consistent with [Phase 3](phase3_typed_exit_record.md)'s contract.
3. **Every documented false-convergence mode is named in this doc with the specific check that separates it from real convergence**, and each check has a test that is demonstrably able to fail.
4. **The rule is measured against archived multi-pass runs before it gates anything live**, and the measurement is recorded here.
5. **The existing loop-back bound stays in force until the measurement supports replacing it.** Replacing a measured floor with an unmeasured predicate is a regression wearing an improvement's clothes.

---

## Dependencies

- **[Phase 4](phase4_fleet_migration.md) — hard.** There is nothing to compare until children emit typed finding records across passes. This is the gating dependency and it is absolute.
- **[Phase 3](phase3_typed_exit_record.md)** — the total-function shape and the named-residual rule are inherited, not re-invented.
- **Cites but does not re-derive:** `docs/standards/architecture/research/raw/convergence_stopping.md` — P11 (convergence detection *requires* typed comparable finding records) and §5.1–5.7 (the case against a naive "stop when nothing new" rule).
- **Required by:** [Autonomous Operation](../autonomous-operation/autonomous-operation.md) — its *observable exit criteria* milestone names a convergence signal, explicitly *"not a turn count."*
- **Interacts with:** `docs/standards/workflow-scripts.md § Bounded composition`, which already states *prefer convergence over counting* and *do not legislate a pass count from a single run*. This phase implements what that standard prefers; it does not amend it.

---

## Implementation steps

### 1. Establish finding identity

- [ ] Define what makes two findings across passes "the same" — the identity must survive rewording, because the same model re-describing the same defect in different words is the normal case, not the edge case
- [ ] State what the identity is computed from and what it deliberately ignores. A hash over the finding's prose is not identity; it is a hash over the prose
- [ ] Verify identity stability against archived multi-pass runs: take passes known to have re-found the same defect, and assert the identity matches. This is the check that decides whether the whole phase is buildable
- [ ] Record what fraction of findings cannot be given stable identity and what happens to them. **They are the residual arm's population and pretending they do not exist is how the predicate reports convergence it did not observe**

### 2. Build the delta

- [ ] Compute the finding-set delta between consecutive passes. **The delta is a computed observable even though the findings are model-authored** — the records were chosen by the model, the delta was not, and the delta is what the predicate reads. Getting this classification right is what makes the signal worth having
- [ ] State the delta's output as a typed value in the record, consistent with the [Phase 3](phase3_typed_exit_record.md) envelope, so a parent reads it rather than recomputing it

### 3. Defend against false convergence — each mode, each check

Each of the following is a documented way a naive "nothing new" rule reports convergence that is not there. Each needs its own check and its own test.

- [ ] **A degraded pass that emits nothing.** An empty finding set from a failed, truncated or turn-capped pass is indistinguishable from an empty set from a clean pass unless the predicate requires evidence that the pass actually ran and completed. Check: the run's own outcome record must show a completed pass before its emptiness counts as a signal
- [ ] **An oscillating finding set.** Two passes alternating between two sets each look "new" to a pairwise comparison and never converge; a comparison over a longer window sees the cycle. Check: compare against a window, not only the immediately preceding pass
- [ ] **An adaptively biased reviewer.** A reviewer that has learned the shape of the previous pass's findings can stop producing them without the underlying issues being resolved. Check: the predicate must not be the only stopping authority — the bound from step 5 remains
- [ ] **A reviewer that never emits an empty pass.** The inverse failure: a pass that always finds *something* means the predicate never fires and the loop runs to its bound. Check: measure the empty-pass rate over archived runs before relying on the predicate at all — if it is zero, the predicate is decorative and this doc says so
- [ ] Each check above has a test, and each test is proven able to fail by mutating the input it guards. A test that cannot fail records a protection that does not exist

### 4. Make the predicate total

- [ ] The predicate returns a named state in every case, including "could not determine" — which is the computed *could-not-check* arm [Phase 3](phase3_typed_exit_record.md) defined, reused here rather than re-invented
- [ ] The residual arm is recorded, not silently defaulted. Every surveyed orchestrator has an answer for the unmatched case and none of them is "fall through"
- [ ] Absence of a comparable prior pass routes to the residual arm, never to "converged"

### 5. Measure before gating

- [ ] Replay the predicate over archived multi-pass runs and record: how often it would have fired, how often it would have fired *early*, and how often it would never have fired
- [ ] Compare against what the fixed loop-back bound actually did on those same runs. The bound exists because self-correction plateaus and a run was observed reaching eight review passes with pass 8 reviewing the same tree as pass 7 — the predicate has to beat that behaviour, not merely differ from it
- [ ] Keep the existing bound in force as a ceiling. Convergence is the honest stopping condition; the bound is the runaway guard, and they are not substitutes
- [ ] **Do not legislate a new pass count from this measurement.** A measured run and a cited plateau band are both evidence, neither is a constant — if a floor must exist before the predicate is trusted, state it as temporary with its reasoning

### Close-out

- [ ] Every requirement met with its evidence in this doc, including the measurement numbers with their denominators
- [ ] [Autonomous Operation](../autonomous-operation/autonomous-operation.md) is told what signal it can consume and what its residual arm means — its exit-criteria milestone depends on this and should not have to re-derive it
- [ ] Any standards implication is surfaced in the [roadmap](roadmap.md#standards-amendment-candidates), not written

---

## Notes and gotchas

- **This phase is why the component exists, and it is also the one most able to produce a confident wrong answer.** A stopping rule that fires early ends work that was still productive, and it does so silently — there is no failing test, just a shorter run. Every check in step 3 exists because the failure has no natural alarm.
- **The delta's classification matters more than it looks.** A finding-set delta over two model-authored finding sets is a *computed* observable, because the delta is not something the model chose. Misclassifying it as a model assertion would put the one genuinely reliable signal this component produces into the arm reserved for things that can be confidently wrong.
- **Nothing in the evidence base measures the error rate of any non-model observable used as a routing channel.** That gap is stated in the research as a gap; this phase's step 5 is the closest this fleet will get to closing it locally, and its numbers should be written down as such rather than presented as validation.

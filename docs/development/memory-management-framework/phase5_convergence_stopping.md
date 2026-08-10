# Phase 5 — Convergence-based stopping

**Component:** [Memory Management Framework](roadmap.md) · **Status: 🔨 BUILT AND MEASURED, GATING NOTHING (2026-08-09)**

> **The predicate is built, total, guarded and replayed over the whole archive. It routes nothing, and that is the phase's finding rather than an unfinished edge.** Requirement 5 makes the loop-back bound stay in force *until the measurement supports replacing it*, and the measurement supports the mechanism while falling far short of a rate: **two positive observations, on 2 of 12 assessable blocks across 41 PRs.** Two falsifies *"it never fires"*. It does not license handing a stopping decision to a signal whose only writer is the loop it would stop. What closes the phase is stated in § What would let this gate — and it is a denominator, not a design.
>
> **One of Phase 1 E7's headline numbers went stale in a single day and this phase re-took it rather than quoting it.** E7 measured *"the open set reaches zero exactly once — PR #42 pass 2, the only `MERGE` and the only `converged: true` in the archive."* Re-measured 2026-08-09: there are now **two** of each. The archive is a moving denominator and every figure below carries its date.

Replaces a **model-asserted** convergence flag with a **computed** one.

`review-pr` already emits `converged: true|false` (`children/review-pr.sh:355`) under a documented single-pass severity heuristic — *"the first pass whose findings are ALL preventive … IS convergence"* (`:323`) — and already mandates that a persisting finding reuse its prior `id` slug verbatim across passes (`:221`, `:357`). Nothing in either fleet routes on that flag today; it is an unconsumed, human-facing signal.

So this phase is not greenfield, and framing it as such would have cost twice: it would have built a second finding-identity scheme beside a shipped one, and it would have exempted itself from a parity audit it needs. What it actually does is narrower and stronger — **move convergence from a class-(iii) assertion the model makes about one pass to a class-(ii) delta computed across two.** *"Did this pass find anything not in the previous pass's result?"* is answerable against two typed payloads and is not answerable against two prose logs.

---

## Requirements for completion

**All five are met, and the fifth is met by the predicate gating NOTHING rather than by a measurement that licensed it to.** Evidence per requirement is named inline; the numbers are in § Measurement above.

Done when:

1. **The incumbent is dispositioned, not ignored.** A `§Capability Parity` audit records what the shipped `converged` field did, and whether this phase reuses the key, replaces it, or introduces a new one — with the consequence for any existing reader or writer of the current semantics stated either way.
2. **The delta is computed over the stable ids the child already emits** — no second identity scheme.
3. **The stopping predicate is a total function** whose residual arm is a named recorded state, consistent with [Phase 3](phase3_typed_exit_record.md)'s contract.
4. **Every documented false-convergence mode is named with the specific check that separates it from real convergence**, and each check has a test proven able to fail.
5. **The rule is validated against [Phase 1](phase1_measure_the_channel.md) E7's replay before it gates anything live**, and the existing loop-back bound stays in force until that measurement supports replacing it.

---

## §Measurement — the replay, with its denominators

Adopted practice, not a binding local rule — see the [roadmap's note on doc shape](roadmap.md). Required in substance because requirement 5 makes a measurement the gate on this phase's own output.

**Taken 2026-08-09, host `puma-workstation-mint`, over `helloskyy-io/Claude-Dot-Files` at 41 PRs.** Re-take it with `python3 scripts/helpers/measure/replay_convergence_predicate.py` — that tool **imports the shipped predicate** rather than pinning a copy, deliberately and unlike its sibling `replay_completion_predicate.py`, because a copy would validate a rule nobody runs.

### The corpus, and how much of it moved since E7

| | E7 (2026-08-08) | this phase (2026-08-09) |
|---|---|---|
| PRs in the repo | 38 | **41** |
| PRs carrying ≥1 `pr_review:` block | 7 | **10** |
| PRs carrying >1 | 5 | **7** (adds #67, #71) |
| blocks | 14 | **22** |
| findings | 195 | **300** |
| consecutive-pass pairs | 7 | **12** |
| `converged: true` blocks | 1 | **2** (#42 p2, #71 p3) |
| `MERGE` verdicts | 1 | **2** |
| findings carrying a `severity` field | 0 | **0** — re-checked; `disposition` is on 300 of 300 |
| `escalated` findings | 2 | **13**, and now inside multi-pass blocks |

### What the predicate would have done

| | count | denominator |
|---|---|---|
| blocks assessed | 22 | every block the predicate would have seen |
| blocks with a prior pass (assessable) | 12 | pass 1 always lands in the residual arm |
| **would have FIRED** | **2** | of 12 assessable — #42 pass 2, #71 pass 3 |
| **would have fired EARLY** (converged against a `HOLD` verdict) | **0** | of 12 |
| multi-pass PRs it would never have fired on | 5 of 7 | #31, #33, #45, #58, #67 |
| residual arm | 10 | all `no_prior_pass`; no other reason occurs in the archive |
| **disagreements with the incumbent `converged` flag** | **0** | of 12 assessable blocks, both positives included |

**The all-ids delta was empty 0 of 12 pairs, exactly as E7 measured at 7** — and it is still a property of the reporting shape rather than of the fleet. **No pass has ever dropped a prior id: 0 of 12.** That is also structural, and it is why the `prior_findings_dropped` guard is written against a mode that has never occurred rather than one being observed.

### The `escalated` ruling, which is the one number that moves

E7 counted `escalated` as **open**, said the corpus could not constrain the choice, and required this phase to rule. **The corpus that settles it now exists**, and the two readings are not equivalent:

| | `escalated` = CLOSED (**shipped**) | `escalated` = OPEN (E7's provisional reading) |
|---|---|---|
| would have fired | **2 of 12** | 1 of 12 |
| disagreements with the incumbent flag | **0** | **1** — #71 pass 3 asserts `converged: true` against 3 escalated findings |
| PRs where the predicate is structurally unable to fire | none observed | **any PR with a live escalation** |

**RULED: `escalated` is CLOSED for the stopping predicate, and the evidence is PR #67.** `standup-md-self-contradiction` and `sprint-mmf-entry-stale` are escalated at pass 1 and *still escalated, unchanged*, at pass 4. An escalated finding has been moved to another authority, so **this reviewer cannot close it on any future pass by definition** — counting it open makes the predicate structurally unable to fire on any PR that ever escalates anything, which is the never-fires failure mode E7's re-scoping to the open subset existed to escape, re-entering through a different door. It is the same rule `routing.should_loop_back` already applies one level up: *needs-assistance never loops at any count, because more passes cannot produce a human ruling.*

**What it costs, and the cost is paid in the open rather than argued away: convergence can now be reported while work is genuinely outstanding somewhere else** — #71 pass 3 is exactly that block. So `escalated_open` carries the ids on every assessment and in every run-log event, and the operator note names them. **A later gating decision reads the number rather than rediscovering the trade.** *This ruling is also the reason E7's "they agree, 1 of 1" survived contact with a bigger corpus: under the other reading it would now be 1 of 2, and E7's consequence 3 would be falsified.*

### The denominator, stated so it cannot be quoted as a rate

**Two positive observations. Not a rate, and this phase does not quote one.** 2 of 12 assessable blocks, from 7 multi-pass PRs, out of 41. One case falsifies *"it never fires"*; two do not establish how often it fires, and the 0-early-fires figure has the same denominator — **0 of 12 is consistent with a true early-fire rate of anything up to about 20%** at any conventional confidence.

**What would establish a rate**, stated concretely rather than as "more data": the interesting quantity is the *early-fire* rate, because that is the failure with no natural alarm. Bounding it below 5% with 95% confidence needs roughly **60 assessable blocks with zero early fires** — five times today's corpus. At the observed cadence (12 assessable blocks accumulated over the repo's whole history, 5 of them in the last two days as multi-pass review became routine) that is **a few months of ordinary operation**, not a special exercise. The predicate is emitted on every dispatch from today, so the corpus accrues without anyone scheduling it.

## §Capability Parity — the incumbent `converged` flag

Every behaviour of the shipped flag mapped to ported, kept, or consciously dropped. No silent drops.

**What the incumbent is:** a **model-asserted, single-pass severity heuristic** — *"the first pass whose findings are ALL preventive … IS convergence"* — emitted as `converged: true|false` inside the durable `pr_review:` block.

**Two emitters, not one, and the phase doc previously said one.** `children/review-pr.sh:355` (frozen V1 fleet) **and** `review_pr/prompts/disposition.md:265` (live V2 prompt) both instruct it. Naming only the bash one would have let a reader conclude the V2 tree had already dropped it.

| Behaviour of the incumbent | Disposition | Where |
|---|---|---|
| Emitted per block into the durable Kind 1 record | **KEPT, unchanged.** Both prompts still instruct it; no prompt text was edited by this phase | `disposition.md:265`, `review-pr.sh:355` |
| Answers *"are this pass's findings all preventive?"* | **KEPT as its own question.** The computed signal answers a different one — *"is anything still open?"* — and does not redefine it | § *Rule on the key* below |
| Zero programmatic readers | **CHANGED, and this is the phase's only change to the incumbent.** It now has exactly one: the parent reads it back to shadow the computation against it. It is read, never routed on | `review_pr_helper.CONVERGED_FLAG`; [`memory-model.md` §4.1](../../guide/memory-model.md) updated |
| Human-facing signal in the block | **KEPT.** Nothing is removed from the block and nothing is re-spelled | — |
| Absent on blocks predating the flag | **KEPT AS A THIRD VALUE.** `None` stays distinct from `false`; folding them would score every pre-flag block as a disagreement | `asserted_converged_in_block` |
| Decides nothing | **KEPT — and so does the replacement.** Neither the flag nor the computation routes anything today | `test_nothing_in_the_tree_routes_on_the_convergence_signal` |

**RULE ON THE KEY: the computed signal takes a NEW name and does not reuse `converged`.** It is `convergence.state` in the parent stratum, values `converged` / `not_converged` / `indeterminate`. **This is the `outcome`/`routed_outcome` shape [Phase 3](phase3_typed_exit_record.md) step 6 already ruled**, applied one level out: the raw assertion is never overwritten and the computed value sits beside it under its own name. Reusing `converged` would silently redefine an already-shipped field for every future reader of the archive — including the replay tools, which read 22 blocks written under the old meaning.

**And the state's SPELLING for the residual arm is deliberately not the protocol's.** `indeterminate`, not `undetermined`. Both values land in the *same run log*, joined on `run_id`, so one token meaning *"the router could not evaluate this record"* and *"the predicate could not evaluate this loop"* would put two different facts in one grep — the shared-bin measurement failure `UndeterminedReason.DENIALS_UNREADABLE` exists to prevent, one artifact over. **This was found by the one-declaration gate rather than by taste**: the first draft spelled it `undetermined` and `test_the_typed_vocabulary_is_declared_in_exactly_one_module` went red.

## §The predicate reads what `review-pr` writes — stated, because it is the hazard

**`review-pr` authors `findings[].disposition`. This predicate reads it. If the reader and the writer are the same actor, the loop optimises the metric it produces.** That is not a hypothetical framing borrowed from Goodhart; it is [Phase 1](phase1_measure_the_channel.md) E7's own lesson, one day old — *ask what the reporting shape makes impossible before reading a zero as evidence* — and this phase is the thing that reads the shape.

**What the predicate reads, and who writes each term:**

| Term | Written by | Can the writer bias it? |
|---|---|---|
| this pass's `(id, disposition)` set | the **child**, in the typed record | **yes, directly** |
| every prior pass's `(id, disposition)` set | the **child**, in a durable block, on an earlier invocation | yes, but the copy is immutable once posted |
| *the pass completed and routed* | the **parent**, from the typed exit record | no — computed from a byte sequence |
| *this pass's block matches this pass's record* | the **parent**, write-time invariant | no |

**What happens if the writer were biased, answered honestly per mode:**

| Bias | Separated by | Test |
|---|---|---|
| **Convergence by forgetting** — stop mentioning open findings | `prior_findings_dropped`: the id set must be a superset of the prior pass's | `test_dropping_a_prior_finding_makes_the_open_set_INCOMPARABLE` + its control |
| **Convergence by churn** — close, re-open, close | `oscillating_findings`: the whole history is scanned, not the last pair | `test_a_pairwise_comparison_would_have_MISSED_the_reopen` |
| **Convergence by emptiness** — a degraded pass emits nothing | `pass_not_evaluable`: the pass's typed record must have routed | `test_a_pass_that_did_not_route_is_never_evidence` + its control |
| **Convergence by drift** — a new disposition value nobody classified | unknown counts as OPEN, and the partition is gated against `CHILD_SCHEMA`'s enum | `test_the_partition_is_EXACTLY_the_schemas_disposition_vocabulary` |
| **Convergence by assertion** — the reviewer marks `fixed` what is not fixed | **NOTHING. UNMITIGATED.** | — |

**The last row is the finding and it is written as a row rather than a caveat.** No check in code separates a truthfully-`fixed` finding from a falsely-`fixed` one, because such a check *is a second review*. The render↔record invariant does not help: it proves the two copies agree, and a biased author writes both. **So the honest answer to *"what if the writer were biased"* is: for four of five modes the predicate withholds convergence; for the fifth it silently agrees.** That is the whole reason this phase gates nothing and the whole reason `routing.MAX_LOOPS` stays. Carried as candidate **C-057**.

## §What would let this gate

Written as conditions rather than as a plan, so a later run can check them instead of re-deriving them.

1. **~60 assessable blocks with 0 early fires** — the bound above. Accrues on its own; the signal is emitted on every dispatch from today.
2. **At least one archived instance of each guard firing on real data**, or an explicit statement that it has not. Today `prior_findings_dropped` and `oscillating_findings` have **zero** archived instances — they guard modes that are documented, not observed, and a guard that has never fired on real input is a guard with mutation evidence and no field evidence.
3. **A ruling on what convergence would gate.** It is **not** a merge authority — that stays with `routed_outcome`. The only thing it could replace is the *loop-back bound*, and `MAX_LOOPS = 1` is already tight enough that the predicate would rarely get to act: at most two review passes happen inside one build run, so a rule that stops a loop already capped at one loop-back buys little. **The larger prize is the cross-dispatch case** — #67 and #71 reached passes 3 and 4 through *separate operator dispatches*, which no bound governs. That is where a convergence signal would actually decide something, and it is [Autonomous Operation](../autonomous-operation/autonomous-operation.md)'s territory, not this component's.
4. **The Phase 3 run set.** Requirement 6 of [Phase 3](phase3_typed_exit_record.md) is still open, and this phase's `pass_evaluable` gate reads the same typed record that requirement is about. Gating on a predicate whose completeness check rests on an unproven channel would inherit that gap silently.

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

- [x] Record what the shipped `converged` field means today (a single-pass severity heuristic — all findings preventive), what emits it, and what reads it. **Recorded in §Capability Parity, and the checklist's own premise needed one correction: there are TWO emitters, not one** — the frozen `children/review-pr.sh:355` and the live `disposition.md:265`. `grep -rn converged` over `scripts/` and `config/` returns exactly one programmatic reader, `replay_pr_review_blocks.py`, which is a measurement tool outside the fleet. **Nothing routes on it, re-verified 2026-08-09 rather than cited**
- [x] **Rule on the key. RULED: A NEW NAME.** `convergence.state` in the parent stratum, beside an untouched `converged:` in the block — the `outcome`/`routed_outcome` shape [Phase 3](phase3_typed_exit_record.md) step 6 already ruled, applied one level out. Reusing the key would redefine it for every reader of the 22 blocks already written under the old meaning, including both replay tools. **And the residual arm's SPELLING is deliberately `indeterminate` rather than the protocol's `undetermined`** — both land in the same run log, and one token for two facts is the shared-bin measurement failure, not a naming preference. That was caught by the one-declaration gate, not by taste
- [x] Record the semantic difference plainly: the incumbent asks *"are this pass's findings all preventive?"*; the replacement asks *"is anything still open?"* **Re-measured at the larger denominator rather than quoted: they agree 12 of 12 assessable blocks, both positives included** — up from E7's 1 of 1. (An earlier reading of E7 reported a disagreement; it computed the delta over the cumulative id set and was corrected.) **The agreement is contingent on this phase's `escalated` ruling, and that is stated rather than hidden:** under E7's provisional *escalated = open* reading the same corpus gives **1 disagreement of 12**, at #71 pass 3. E7 said the corpus could not constrain that choice; at 41 PRs it can, and the choice now moves the headline number it was previously invisible to.
- [x] Write the `§Capability Parity` table: every behaviour of the incumbent flag mapped to ported or consciously dropped, no silent drops — **written above. One behaviour changed and it is named: the flag acquired its first programmatic reader** (the shadow), which moves it out of [`memory-model.md` §4.2](../../guide/memory-model.md)'s *read by nobody* list and into §4.1's consumer map. That guide edit is part of this phase's diff

### 2. Establish finding identity — on the convention that already exists

> **Amended by [Phase 1](phase1_measure_the_channel.md) E7 (2026-08-08, corrected in the same day's refine pass).** The convention **holds on the added direction**: over the 7 consecutive-pass pairs in the archive, 25 ids were added and 0 of the 25 adjudicated as a restatement of an existing finding under a new slug. This step is this phase's **premise, not its hard part** — as its dependency clause anticipated.
>
> **One half of that amendment was withdrawn and this step must not rely on it.** The companion figure "**0** ids were dropped or renamed" is **not a measurement**: the `pr_review:` block is **cumulative** (`review-pr.sh:221` — each pass restates every prior id and updates its `disposition` in place), so an id cannot be dropped whatever the reviewer does. Id-disappearance carries no information here.
>
> Three structural facts this step must respect: **`pass` numbers are not dense** (PR #31 runs 1, 2, 4 — "consecutive" comes from block order, never from the integer); **an id is stable while its `title` is not** (#45 reuses an id across passes with a completely rewritten title and consequence, because pass 2 restates it as fixed); and **an id's presence is not its liveness** — `disposition` is what says whether a finding is still open, and identity plus disposition together are what step 3 computes over. Identity itself is computed from the id alone.

- [x] Start from the shipped convention: a persisting finding reuses its prior `id` slug verbatim, and only genuinely-new findings get new slugs. **The identity mechanism is not this phase's invention; verifying that it holds is this phase's work**
- [x] Confirm against E7's measurement how often the same finding recurred under the same id versus under a new one. A convention the prompt mandates and the model does not follow is not an identity mechanism, and the delta computed over it would report novelty that is only rewording
- [x] State what the identity is computed from and what it deliberately ignores — **the `id` slug alone.** Deliberately ignored: `title` (E7 measured #45 carrying one id across a completely rewritten title), the finding body, `category`, ordering within a block, and the block's own `pass:` integer. Sequence comes from block order. Written into `convergence.py`'s module docstring, which is where a reader of the code arrives
- [x] Record what fraction of findings cannot be given stable identity and what happens to them — **and the honest answer differs by channel, which the checklist assumed away.** On the TYPED side the fraction is **0 by construction**: `id` is in `CHILD_SCHEMA`'s `required` list, so a finding without one makes the record fail validation at R3 and the pass never becomes convergence evidence. On the PROSE side (prior passes) a finding with no `- id:` line is invisible to the extractor, so it is not in the prior set at all — and if a later pass restates it *with* an id it reads as an addition, never as a closure. **Neither direction can empty the open set**, which is the property that matters. What CAN is an unrecognised `disposition`, and that counts as OPEN by rule with its own test

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

- [x] **Compute the delta over the OPEN subset, with the stopping condition "the open set is empty".** `convergence.assess` rule C4 returns `NOT_CONVERGED` on any non-empty open set and flags the unchanged sub-case as `stalled`; only C6 returns `CONVERGED`. `disposition` arrives as `findings[].disposition` in [`exit-protocol.md` §2.1](../../standards/exit-protocol.md), enum of six. **CLOSED: `fixed` · `deferred` · `rejected` · `noted` · `escalated`. OPEN: `hold`, plus any value the vocabulary does not recognise.** The `escalated` half is this phase's ruling, measured above; a completeness gate asserts the partition is *exactly* `CHILD_SCHEMA`'s enum, so a seventh value cannot ship unclassified
- [x] **Record the positive observations and refuse to quote them as a rate — and re-measure rather than restate, because the count has already changed.** It is **TWO**, not one: #42 pass 2 and #71 pass 3, of 22 blocks / 12 assessable. § Measurement states the figure with its denominator, states that 0 early fires is consistent with a true early-fire rate up to ~20%, and states what corpus would bound it — roughly 60 assessable blocks, a few months of ordinary operation
- [x] Compute the all-ids delta as well, and emit it — **as telemetry and as the window check's input, never as the stopping condition.** `ConvergenceAssessment.added_ids`, carried into the run-log event, with `test_the_all_ids_delta_is_TELEMETRY_and_never_the_stopping_condition` proving a converging pass may add ids (PR #42 pass 2 added three). **The delta is a computed observable even though the findings are model-authored** — the records were chosen by the model, the delta was not, and the delta is what the predicate reads. This classification is the whole reason the phase is worth doing; misclassifying it would put the one genuinely reliable signal this component produces into the arm reserved for things that can be confidently wrong
- [x] Emit the output as a typed value the parent reads rather than recomputes — **and it deliberately does NOT enter the [Phase 3](phase3_typed_exit_record.md) envelope, which is a ruling rather than an omission.** [`exit-protocol.md` §2](../../standards/exit-protocol.md) is explicit: *no field is added on behalf of a consumer that does not exist*, and this signal has no routing consumer by design. It is emitted as a typed `ConvergenceAssessment` and persisted as its own `{"type": "convergence"}` run-log event beside the parent stratum, joined on `run_id`. **When a parent routes on it, it enters §2.3 by §5's additive rule** — which is exactly what that rule is for, and adding it early would have put a field with no consumer in a protocol whose own §2 forbids it

### 4. Defend against false convergence — each mode, each check

Each of the following is a documented way a naive "nothing new" rule reports convergence that is not there. Each needs its own check and its own test.

- [x] **A degraded pass that emits nothing.** Check: rule **C0** — `assess` takes `pass_evaluable` as a REQUIRED keyword with no default, and the live caller supplies *the typed exit record routed to something other than `undetermined`*. No default, so a Phase 4 call site cannot acquire this hole by forgetting the argument. Tests: `test_a_pass_that_did_not_route_is_never_evidence` **plus its control on byte-identical input**, and the mutation removing C0 turns the first red
- [x] **An oscillating finding set.** Check: rule **C5** — `_ever_reopened` scans the WHOLE history for an id closed in one pass and open in a later one, and a single reopening withholds convergence for the rest of the PR. The window is the whole history rather than a fixed N because any fixed N is a number nobody measured. Tests: the mode, its control isolating the reopen from the history's length, and `test_a_pairwise_comparison_would_have_MISSED_the_reopen`, which demonstrates the same input converging when only the last two passes are handed in. **Zero archived instances (0 of 12 pairs) — this guards a documented mode, not an observed one, and § What would let this gate records that as a gap**
- [x] **An adaptively biased reviewer.** Check: the predicate is **not a stopping authority at all** — `routing.MAX_LOOPS` is unchanged and nothing branches on the signal. `test_nothing_in_the_tree_routes_on_the_convergence_signal` enforces it **on the class rather than on today's call sites**: any `if`/`while`/`elif` in `modules/` whose condition mentions `ConvergenceState` or `convergence.assess` fails, plus an assertion that `MAX_LOOPS == 1`. The mutation adding such a branch turns it red. **§ The predicate reads what `review-pr` writes** decomposes this mode into five and states plainly that four are separated by a check and the fifth — a reviewer marking `fixed` what is not fixed — is **unmitigated**, because separating it is a second review. Carried as **C-057**
- [x] **A reviewer that never emits an empty pass.** The inverse failure: a pass that always finds *something* means the predicate never fires and the loop runs to its bound. Check: this is E7's measurement, taken in Phase 1 precisely so it can cancel this phase rather than be discovered inside it. **ANSWERED — and the answer depends entirely on which set is read.** Every pass adds *some* new id (7 of 7), so over the cumulative id set the mode is real and the predicate would never fire. Over the **open** subset it is not the norm: the open set emptied on 1 of 14 blocks and its delta emptied on 2 of 7 pairs. **The mode is defended against by reading the open subset, which step 3 now specifies** — not by abandoning set-difference
- [x] **A pass that closes nothing and adds nothing.** Check: C4 reads emptiness of the SET, and `ConvergenceAssessment.stalled` names the sub-case for the operator without changing a route. Replayed: #58 index 3 is the archive's only `stalled: True` row. Tests: the stalled case, **plus a control asserting a moving-but-open pass is NOT stalled** so the flag discriminates rather than merely being true, and the mutation weakening C4 to a delta rule turns the first red
- [x] Each check has a test proven able to fail. **22 mutations run across the two suites; 22 caught, 0 surviving**, each by the test that names the property. The list is in the PR body. Two beyond the modes above guard *this phase's obligation to Phase 4* rather than the predicate: widening the `parent_route` payload, and `append_convergence` reusing the `parent_route` type string — both go red. **And two of the 22 are worth recording as METHOD rather than as results.** One initially **SURVIVED** — folding an absent `converged:` key into `false` in `asserted_converged_in_block`, which would have scored every pre-flag block as a disagreement in the live shadow — and the test that closes it exists *because the mutation found the gap*. One initially went **red for the wrong reason**: the mutation broke the expression's syntax, so the suite died at collection and proved nothing about any assertion; re-derived as a semantically valid change (dedupe the window) it was then caught by the test that reads order. **A control that goes red on a syntax error is not evidence, and a mutation run where nothing survives is a run that has not yet found its own blind spot**

### 5. Make the predicate total

- [x] The predicate returns a named state in every case. `ConvergenceState` is three members and `assess` is six ordered rules with C6 as the documented default — the `podFailurePolicy` shape `exit_record.route` already borrowed, borrowed again rather than re-designed. **The SHAPE of Phase 3's computed *could-not-check* arm is reused; its SPELLING is deliberately not**, per the parity audit
- [x] The residual arm is recorded, not silently defaulted. `IndeterminateReason` is five members, required IFF the state is `INDETERMINATE` and **enforced in `__post_init__`** — the invariant `ExitRecord` learned to enforce after documenting it and enforcing it nowhere left the reporting path one `None` from an `AttributeError`. Every assessment reaches the run log as a `{"type": "convergence"}` event, including the indeterminate ones, so the residual arm has a denominator. Five separate reasons rather than one bin, for the reason §4's R1a/R2 split records: **the arm is grouped BY the reason, so a `gh` rate limit must not be counted as a degraded review**
- [x] Absence of a comparable prior pass routes to the residual arm, never to converged — rule **C2**, `no_prior_pass`. This is the archive's single most common outcome (10 of 22 blocks) and the case most likely to read as convergence to a naive implementation, because a pass-1 review that closed everything it found has a genuinely empty open set. Test plus a control proving the emptiness is not what withholds it

### 6. Validate before gating

- [x] Replay the predicate over the archived runs and record all three numbers — § Measurement: **fired 2 of 12 assessable blocks · fired early 0 · never fired on 5 of the 7 multi-pass PRs.** The tool is kept at `scripts/helpers/measure/replay_convergence_predicate.py` and imports the shipped predicate, so a re-run measures what actually ships
- [x] Compare against the incumbent flag and against the bound — **and the two halves reached very different kinds of answer, which is the finding.** Against the flag: **0 disagreements over 12 assessable blocks**, both positives included, so E7's *treat `converged` as a label the computation should reproduce* holds at the larger denominator. Against the bound: **the comparison is not answerable from this corpus and that is a result, not a gap.** `MAX_LOOPS = 1` caps a build run at two review passes; #31, #58 and #71 carry three blocks and #67 carries four, so **at least 4 of the 7 multi-pass PRs demonstrably span more than one dispatch** and no archived pass sequence can be attributed to the bound acting. *(`attempt:` rises across every pair, but it cannot separate the two — a loop-back also lands work and increments it — so it is NOT used as evidence here.)* **The eight-pass run the bound was written for is outside this archive entirely** — it predates the block format and is recorded only in [`cpi-decisions.md`](../cpi-decisions.md) — so whether the predicate *beats* that behaviour is **unanswerable today** and is not claimed. What the corpus does show is where a convergence signal would actually decide something: the **cross-dispatch** case, which no bound governs
- [x] Keep the existing bound in force as a ceiling — **`routing.MAX_LOOPS` is byte-unchanged and the predicate routes nothing**, which is stronger than keeping the bound *alongside* a live signal. Enforced by a test on the class, not by intention
- [x] **No new pass count is legislated, and none is proposed.** No constant in this diff changes. § What would let this gate is written as *conditions a later run can check*, not as a number — and the one quantity it does state (~60 assessable blocks) is a **confidence bound on the early-fire rate**, derived from the denominator, not a pass count

### Close-out

- [x] Every requirement met with its evidence in this doc, including measurement numbers with their denominators — **all five, and § Measurement carries every figure with the date it was taken and the denominator it came from.** The one thing this phase does NOT claim is a firing rate; § Measurement says so in those words and states what corpus would produce one
- [x] [Autonomous Operation](../autonomous-operation/autonomous-operation.md) is told what it can consume — **written into that doc as a constraint rather than an offer**, with three things a consumer must not get wrong (convergence is not merge authority; `indeterminate` is a third state, not a soft negative; `converged` can carry outstanding escalations) and the reader-is-the-writer constraint stated plainly
- [x] Any standards implication is surfaced in the [roadmap](roadmap.md#standards-amendment-candidates), not written — **one, item 9: `exit-protocol.md` §2.3 gains a convergence field WHEN a parent routes on it, by §5's additive rule, and not before.** Trigger-gated on that event, which is a real trigger rather than an unrelated one. **[`workflow-scripts.md` § Bounded composition](../../standards/workflow-scripts.md) is deliberately NOT amended**: it already says *prefer convergence over counting* and *do not legislate a pass count from a single run*, and this phase implements what it prefers while changing no count. Amending it to describe a signal that gates nothing would be the *standard amended on the strength of a plan* that Phase 3's close-out warns against

---

## Notes and gotchas

- **This phase is the component's strongest justification, and it is also the one most able to produce a confident wrong answer.** A stopping rule that fires early ends work that was still productive, and it does so silently — there is no failing test, just a shorter run. Every check in step 4 exists because the failure has no natural alarm.
- **The justification is narrower than "nothing detects convergence today," and the narrower version is the true one.** A flag exists; nothing routes on it; it answers a different question. Claiming greenfield here would be the same overclaim the [roadmap](roadmap.md#key-decisions) warns against on the routing side, and a reviewer who reads `review-pr.sh` would break it.
- **Nothing in the evidence base measures the error rate of any non-model observable used as a routing channel.** That gap is stated in the research as a gap; step 6 is the closest this fleet gets to closing it locally, and its numbers should be written down as such rather than presented as validation.

- **The predicate is a HYBRID and the seam is worth knowing before Phase 4 reads this.** Its most recent term comes from the TYPED exit record; every earlier term comes from a durable `pr_review:` block, parsed as prose. That is not a hole in the typed channel — a Kind 2 record's lifetime is one parent invocation, so a prior pass's typed record does not exist to be read, and Kind 1 is the only durable copy. **The two are interchangeable only because the render↔record invariant makes this pass's block and this pass's record carry identical `(id, disposition)` pairs.** A weakening of that invariant would not fail a convergence test; it would silently make yesterday's prose term disagree with what today's typed term was compared against. `_assert_block_matches_record`'s docstring now says so at the place a refactor would read it.

- **This phase is the first consumer that needs a typed record to OUTLIVE its invocation, and it works around that rather than solving it.** Carried as candidate **C-058** — surfaced, not built, because solving it means a durable store for Kind 2 records and that is a component-sized decision, not a phase-sized one.

- **A guard with mutation evidence and no field evidence is still a guard, and the difference is recorded rather than smoothed over.** `prior_findings_dropped` and `oscillating_findings` have **zero** archived instances. Every mutation of them goes red, which proves the check works; nothing proves the mode occurs. § What would let this gate lists that as condition 2 rather than leaving a reader to infer that four green checks mean four observed defences.

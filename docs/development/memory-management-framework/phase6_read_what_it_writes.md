# Phase 6 — Read what the component writes

**Component:** [Memory Management Framework](roadmap.md) · **Status: not started**

Three phases have each added a parent-written observable to the per-run JSONL log. **No committed tool reads any of them**, no document says the run log is a surface, and the rule for adding a fourth lives in one event's docstring. This phase names the surface, gives it a growth rule and a reader, and — because the reader is the instrument the check needs — gives [Phase 5](phase5_convergence_stopping.md)'s un-owned activation an owner and a trigger.

**One phase, one end-to-end outcome:** *the component's own gate conditions can be checked by running a tool, instead of by a human remembering to.*

---

## The measured problem

**Three event types, three phases, zero readers.**

| Event `type` | Added by | Written at | Read by a committed tool |
|---|---|---|---|
| `parent_route` | [Phase 3](phase3_typed_exit_record.md) | `assistant_activities.append_parent_route` | **no** |
| `convergence` | [Phase 5](phase5_convergence_stopping.md) | `assistant_activities.append_convergence` | **no** — carried as candidate **C-059** |
| `run_resources` | `0feacc3`, corrected by `a623c25` | `assistant_activities.append_run_resources` | **no**, and nothing was carried |

Re-derive with:

```
grep -rn "_append_run_event" scripts/workflows/temporal/modules/assistant/assistant_activities.py
grep -rln "parent_route\|run_resources\|\"convergence\"" scripts/helpers/measure/
```

The second command returns nothing today. `scripts/helpers/measure/` holds three replay tools and every one of them reads either the CLI's own `result`/`assistant` events or the GitHub `pr_review:` archive.

**This is the documented failure of `loose_ends.md`, in a different substrate.** That file ran ten weeks; two of its entries described work completed the same day it was finally read, and one had a run flag six weeks earlier that its trigger had fired. [`memory-model.md` §1.2](../../guide/memory-model.md) states the rule this violates without exception: *"A record with no reader is not memory, it is exhaust — and it costs the reader of the other records their attention."* **A store that accepts anything gets read by nobody**, and a JSONL append is the cheapest possible way to accept anything.

**Phase 5 did the right thing and it is the control case.** It emitted `convergence` with no reader and **placed C-059** — a proposal, with a named trigger, on the surface `finding-routing.md` §7 assigns to proposals. `run_resources` shipped with no reader and no placement. The difference is the whole of this phase's admission rule.

---

## The ruling this phase exists to make: where telemetry lives

> **The operator's framing, which governs this section:** *"This really feels like an additional means of persistent memory. But we don't want to keep creating more and more and more for every use. We want a select well-designed few that cover the bases and also allow for future growth."*

### What exists, factually

`run_resources` is written by `append_run_resources()` into the per-run JSONL log, beside `parent_route` and `convergence`. It carries `peak_anon`, `peak_total`, `mean_total`, `pids_peak`, `high_events`, `oom_kills`, `tool_result_bytes`, `subagents_spawned`, and an explicit `measured: false` with a reason when a run could not be measured. It is written **before** the failure branch, deliberately — a run that died is the one whose numbers are most worth having.

### 1 · Which Kind is it? — RULED: **neither**, and one property decides it

[`memory-model.md`](../../guide/memory-model.md) opens with the discriminator and this ruling uses it rather than inventing one: *"Two kinds of memory exist because a context window ends and the work does not. **They differ in who reads them.**"* Kind 1's reader is a human or a later run deciding what to do next. Kind 2's reader is code, within seconds, deciding a route.

**The deciding property is this: for Kind 1 and Kind 2 alike, the unit of meaning is the RECORD. For `run_resources` it is the POPULATION.** A single `peak_anon` answers nothing — the module's own docstring says so: the open question is whether footprint is governed by the *number* of subagents or the *volume* each pulls into context, *"and across enough runs the question stops being an argument and becomes a regression."* One record has zero information content by construction.

That single property discharges the whole question and it is why this is not decided by resemblance to a neighbour:

- **Not Kind 2.** Kind 2's lifetime is one parent invocation and its purpose is to decide that invocation's route. `run_resources` is written *after* the child exits, routes nothing, and its value is realised only across runs. [`exit-protocol.md` §2](../../standards/exit-protocol.md)'s own rule — *no field is added on behalf of a consumer that does not exist* — forbids putting it in the envelope, which is the same rule Phase 5 applied to the convergence signal.
- **Not Kind 1,** and it fails three of the five properties, each for the same underlying reason. **Property 1 (durable — outlives the machine):** `.claude/logs/` is machine-local and globally gitignored; the run log does not survive the workstation. **Property 3 (outcome *and* reasoning):** it carries numbers. `unmeasured_reason` is a reason for an *absence*, not reasoning about an outcome, and no re-adjudication is possible from it. **Property 4 (a to-do bit):** see below.
- **Not a candidate for forcing into Kind 1 by adding what it lacks.** Making it durable-across-machines means committing per-run telemetry to git; making it carry reasoning means asking a machine sampler to author prose. Both are the tail wagging the dog.

### 2 · Is the run log a surface nobody has named? — RULED: **yes, and it has been one since Phase 3**

It is not created here; it is *recognised*. The evidence is that it already has every property of a surface except a name:

- **Three member event types**, added by three separate phases, each namespaced away from the CLI's own types so a future CLI cannot collide with them.
- **A reader family with its own stated discipline** — `scripts/helpers/measure/README.md` already carries a pin-versus-import rule (*"pin when the number must stay reproducible, import when the rule must be the one that ships"*) and a sample-size rule (*"every count these emit carries its denominator, and every excluded artifact is named as excluded"*). Those are surface rules, written for a surface nobody had named.
- **A join key.** Every event carries `run_id`; `convergence.py:111` already documents joining to `parent_route.routed_outcome` on it.
- **A rule for adding a fourth — stated in the wrong place.** `append_parent_route`'s docstring says its payload is frozen while Phase 4 reads it, and that *"a later phase adding its OWN observable adds its OWN event type beside this one."* That is a rule about **one** event which has become the de-facto rule for **all** of them. `append_run_resources`'s docstring cites it as *"`append_parent_route`'s OWN RULE"* — which is the surface's governing rule being quoted from a neighbour's docstring, and is precisely how a convention becomes unfindable.

**So this is the move [Phase 2](phase2_kind1_framework.md) made for Kind 1, one surface over:** the thing was built and in daily use, and writing it down was an authoring task with its own done-state. **Nothing new is created here** — which is the direct answer to the guard rail against inventing a surface because telemetry does not fit the existing two.

**Proposed name: Kind 3 — the measurement record.** Written by the parent after the unit finishes; read by an offline replay tool; the unit of meaning is the population, not the record. **The naming is the operator's to ratify**, because it amends a Phase 2 deliverable ([`memory-model.md`](../../guide/memory-model.md)), and this phase surfaces it rather than writing it.

### 3 · Does it need a to-do bit, and does anything read it? — RULED: **no bit; and the consumer is planned, not the deletion**

**No to-do bit, and its absence is a positive design property rather than a gap.** Property 4 is per-record, and a resource sample has nothing to do. What *does* have something to do is the population — it has to reach a denominator — and that obligation already has a home in this component's vocabulary: [Phase 5 § What would let this gate](phase5_convergence_stopping.md) is a set of conditions on a corpus, not a flag on a row. **A to-do bit on a Kind 3 record would be a bit nobody could ever clear**, which is the `loose_ends.md` shape wearing a schema.

**Consumer, not deletion, and here is why deletion loses.** The deletion argument is real: nothing reads `run_resources`, and an unread store is the documented failure. It loses on one thing — **the emission is already correct and the corpus already accrues.** The instrument was built for a livelock that produced *no evidence at all*; deleting it restores the state where nobody can establish what held the memory. The remedy for an unread store is a reader, and the reader is small.

**Named consumer: `scripts/helpers/measure/replay_run_resources.py`**, a sibling of the three that already exist, on the same read-only-over-`.claude/logs/` shape as `replay_completion_predicate.py`. It must produce four figures, and **each is specified with its denominator and, where a bound is meaningful, with both bounds**:

1. **The `measured: false` rate, with its reasons, as the first output.** An unmeasured run must be *countable*: *"we have no data"* and *"we have data showing nothing happened"* are different facts, and collapsing them is how a gap becomes invisible. This figure exists because the incident that produced the instrument was an evidence failure, not an outage.
2. **`peak_anon` distribution keyed by workflow**, so the per-workflow `resource_limits:` ceiling can be checked against observation instead of against the one incident that set it.
3. **The knob question**: the relationship between `subagents_spawned`, `tool_result_bytes` and `peak_anon`. This is the question `resource_telemetry.py`'s docstring names as its purpose, and it is unanswerable from any single run.
4. **The AGGREGATE, which is the figure the failure actually needs and which no per-run record yields alone:** the summed peak of runs whose wall-clock windows overlap. Every other figure describes a unit.

### 4 · What is the growth rule? — RULED: two clauses, and the second is the one with teeth

**Clause A — PLACEMENT is decided by the reader, and there are exactly three readers.** A fifth observable joins an existing kind; it does not get a new one.

| The new observable's reader | Where it goes | Mechanism |
|---|---|---|
| code, within seconds, deciding this invocation's route | **Kind 2** — the exit-record envelope | [`exit-protocol.md`](../../standards/exit-protocol.md) §2.3, added by §5's additive rule **when a routing consumer exists**, never before |
| a human, or a later run deciding what to do next | **Kind 1** — the five surfaces | [`memory-model.md` §2.1](../../guide/memory-model.md)'s selection rule, question 0 first |
| an offline replay tool computing a rate over a growing denominator | **Kind 3** — the run log | its own `{"type": …}` event, sharing **no payload** with an existing type |

This is the model's own discriminator applied consistently rather than a new axis, which is what keeps the answer to *"a select well-designed few"* at three and not at four-and-counting.

**Clause B — ADMISSION: an observable ships with its reader in the same change, or with a placed candidate carrying a named trigger.** No third option. **On current evidence the de-facto rule is *"a new event type, added by whichever phase needs it, governed by a docstring"*, and that is not adequate** — it is adequate for placement and silent on admission, and admission is the half that failed. Measured against the two events that tested it: Phase 5 emitted `convergence` and placed **C-059** with the trigger *the first question only the live corpus can answer* → conforms. `run_resources` shipped with neither → does not, and this phase is the remedy.

> **Guard rail check, stated so the ruling can be audited rather than trusted.** The instruction was: do not create a surface merely because telemetry fits neither existing one, and do not force it into an existing one merely to avoid creating one. This ruling does neither — **it names a surface that already had three members, three phases of contributors, a join key, a reader directory and a written discipline.** The counterfactual test: if `run_resources` had never been written, `parent_route` and `convergence` would still constitute the same unnamed surface with the same unread problem. The telemetry did not create the question; it made it the third instance.

---

## Requirements for completion

Done when all of the following hold:

1. **The run log is stated as a surface** — its member event types, its join key, its owner, and the rule for adding a fourth — in **one** place that is not a function docstring. The rule currently stated in `append_parent_route`'s docstring is moved, and that docstring cites the new home rather than restating it, per [Documentation Standard § Single-source codified fields](../../standards/documentation/documentation_standard.md).
2. **Every parent-written event type has a committed reader**, or a placed candidate carrying a named trigger. Zero of three today. **This requirement is met by readers, not by a table listing what a reader would say.**
3. **`run_resources` has a named consumer producing the four figures above, each with its denominator**, or the emission and its module are deleted in this phase's diff. Not both, and not neither.
4. **Every ceiling this component states says whether it binds a UNIT or an AGGREGATE.** `config.yaml`'s `resource_limits:` binds a unit today (`MemoryHigh`/`MemoryMax` on one child's scope) while naming the aggregate surface it does not yet use (`slice: claude-workflows.slice` — *"all children share it, so a future cap binds the TOTAL"*), and `max_parallel_agents: 4` binds one message within one dispatch. **Three separately-correct per-unit caps summed past a 31 GiB host on 2026-08-10**; a plan that states a ceiling without its scope has not stated a ceiling.
5. **[Phase 5](phase5_convergence_stopping.md)'s activation has an owner and a trigger** — see below. Met when the conditions are *printed by a tool with their denominators*, not when the predicate is switched on.
6. **Every figure this phase's tools emit carries its denominator, and every excluded artifact is named as excluded.** Inherited from `scripts/helpers/measure/README.md`, which already binds its siblings.

---

## §Phase 5's un-owned activation — the owner and the trigger

**The gap, stated precisely and without disturbing what Phase 5 built.** Phase 5 is BUILT, MEASURED AND REVIEWED, GATING NOTHING, and that is its finding rather than an unfinished edge. Its requirement 5 says the rule *"is validated against Phase 1 E7's replay **before it gates anything live**"*. Phase 5 closed without switching the predicate on — correctly, on its own evidence — and **no phase claims the second half of that sentence.** Phase 4 does not. So the component could complete with a predicate nobody ever enabled.

**Nothing Phase 5 built is un-built, and no box of its is un-checked.** Its five requirements were met on the evidence available; the predicate is total, guarded and replayed. What was missing was never a deliverable — it was an **owner for the check**.

**OWNER: this phase, for making the conditions checkable. The OPERATOR, for the ruling to enable.** The split is the same one the component uses everywhere: a dispatch produces the number, a human disposes of it.

**TRIGGER: this phase's reader family, because it is the instrument the condition needs.** Phase 5 § What would let this gate condition 1 waits on **scorable fires** — a `CONVERGED` assessment with at least one later pass on the same PR — of which there are **0**, over an empty denominator. That figure comes from `replay_convergence_predicate.py` over the GitHub `pr_review:` archive. **The live path emits a `convergence` event on every dispatch and nothing reads it**, so the two facts the archive structurally cannot produce — the `pass_not_evaluable` and `history_unreadable` rates, and the typed term the live predicate actually reads — have no denominator at all. That reader is **C-059**. Building it is what turns condition 1 from a number a human must remember to re-derive into a number a tool prints.

- [ ] Build the `convergence`-event reader (**C-059**), so the live corpus has a denominator beside the archive's
- [ ] Print Phase 5 § What would let this gate's conditions 1 and 2 **as tool output with their denominators**, so a later run checks them rather than re-deriving them. Condition 4 has already fired and is recorded as fired; condition 3 is a ruling and stays out of scope here
- [ ] **Record the ruling authority explicitly: enabling the predicate is the operator's call on this phase's numbers, and it is not this component's to make alone.** Phase 5 condition 3 already places the interesting case — the cross-dispatch loop, which no `MAX_LOOPS` governs — in [Autonomous Operation](../autonomous-operation/autonomous-operation.md)'s territory. **This phase must not enable the predicate and must not propose a pass count**
- [ ] `routing.MAX_LOOPS` stays byte-unchanged in this phase's diff, and `test_nothing_in_the_tree_routes_on_the_convergence_signal` stays green. **The restraint is the deliverable, not a side condition**

**Why this is a checkbox on Phase 6 and not a new phase.** [`engineering-quality.md` § *A deferral is PLACED*](../../../config/rules/engineering-quality.md)'s first placement question: does it have a done-state today? The *ruling* does not — it waits on a corpus. The *instrument* does, and the phase that owns the instrument is the phase that owns the trigger. A phase created for the ruling alone would sit unstartable, which is the trigger-gated-issue failure that rule exists to prevent.

---

## Implementation steps

### 1. Name the surface before adding to it

- [ ] State the run log's member event types, join key and owner in one place. **The natural home is a `docs/guide/` addition or a section of the draft [Exit Protocol](../../standards/exit-protocol.md)** — the protocol already owns the parent stratum (§2.3), which is where two of the three events come from. **Standards are surfaced, never written by a dispatch acting on its own initiative**; if this phase's brief authorises the protocol edit, the mechanism is a PR ([`standards-governance.md`](../../../config/rules/standards-governance.md)), and if it does not, it lands as roadmap candidate **10**
- [ ] Move the add-a-fourth rule out of `append_parent_route`'s docstring; have that docstring cite the new home. **Keep the payload freeze where it is** — that clause is about Phase 4 reading this specific event and is genuinely local
- [ ] A test asserts the declared event-type set equals the set `_append_run_event` is actually called with, so a fifth type fails here rather than waiting for a reader. **Mutate in both directions:** an undeclared new type goes red, and a declared type with no writer goes red

### 2. Build the readers

- [ ] `replay_run_resources.py`, producing the four figures in § 3 above. **Import or pin per the README's stated rule** — this reports facts about archived runs rather than validating a candidate rule, so it reads the log format and pins nothing executable
- [ ] The `convergence`-event reader (**C-059**)
- [ ] Decide, and record, whether `parent_route` needs its own reader or is adequately served by the two above joining on `run_id`. **Rule it either way; do not leave it unruled** — it is the one of the three with no candidate carrying it
- [ ] Add a row per new tool to `scripts/helpers/measure/README.md`'s table, including its **Read by** column. A tool with no named reader in that column reproduces this phase's own finding one level up

### 3. State every ceiling's scope

- [ ] Audit every numeric ceiling this component and its config state, and label each **unit** or **aggregate**: `config.yaml`'s `resource_limits.MemoryHigh`/`MemoryMax` (unit — one child scope), `resource_limits.slice` (the aggregate surface, **declared and uncapped**), `max_parallel_agents: 4` (unit — one message in one dispatch), `max_turns:` per workflow (unit — one invocation), `routing.MAX_LOOPS` (unit — one build run)
- [ ] Where a ceiling is a unit and the failure it guards against is an aggregate, **say so at the ceiling** rather than in a note elsewhere. `max_parallel_agents: 4` is the live instance: the 2026-08-10 livelock was three sessions and two dispatches, each individually within its limits
- [ ] **Do not set an aggregate cap in this phase.** The slice exists and is uncapped deliberately — `config.yaml:179` states the command and says *"once the data supports one"*, and this phase's whole point is that the data does not exist yet. Setting one here would be legislating a number from a single incident, which is the failure [`workflow-scripts.md` § Bounded composition](../../standards/workflow-scripts.md) already names

### 4. Verify by both bounds

- [ ] Every check this phase adds asserts a floor **and** a ceiling where a bound is meaningful. **The motivating failure is in this component's own tree:** the resource telemetry's first test asserted only a floor, passed, and was measuring the caller's cgroup rather than the child's — reporting three different children at an identical figure (`a623c25`). A one-sided assertion cannot see a plausible wrong number
- [ ] Every count this phase reports is produced by a command recorded beside it. **Three times in two days a figure in this repo was correct with a fabricated derivation** — a right count with a wrong reason, a `grep` that could not fail, and a diffstat computed from a previous diffstat — and each passed every check aimed at the figure

### Close-out

- [ ] Every requirement met with its evidence in this doc, including every figure with its denominator and its date
- [ ] The Kind-3 naming is surfaced for operator ratification as a [`memory-model.md`](../../guide/memory-model.md) amendment, **not written into it** — that file is a Phase 2 deliverable and the surface set it states is already the subject of an unresolved reconciliation with the binding [Architecture Standard § 4](../../standards/architecture/architectural_standard.md) (roadmap candidate 8). **Two open amendments to one file must be disposed of together or the second re-derives the first**
- [ ] Phase 5's activation conditions are printed by a tool, and the ruling is recorded as the operator's

---

## Dependencies

- **[Phase 5](phase5_convergence_stopping.md) — hard.** It emits the `convergence` events and states the conditions this phase makes checkable. Nothing here re-opens its rulings.
- **[Phase 4](phase4_fleet_migration.md) — soft, and the ordering is deliberate.** Phase 4 widens `parent_route` emission from one parent to the V2 tree. A reader built before that measures one parent and reports it as a fleet rate. **This phase should follow Phase 4 rather than run beside it** — but it is not blocked by it, and if Phase 4 slips, a reader over one parent with its denominator stated is still worth more than three unread event types.
- **Not gated on the bash-fleet ruling**, which is answered — see [Phase 4 § The scope ruling](phase4_fleet_migration.md).
- **Required by:** [Autonomous Operation](../autonomous-operation/autonomous-operation.md) — its *observable exit criteria* milestone consumes the convergence signal, and the numbers that would license enabling it come from here.

---

## Notes and gotchas

- **The thing this phase is most likely to get wrong is to write the surface down and not build the reader.** Requirement 1 is an authoring task with a clean done-state and requirement 2 is not; a run short on budget will do the easy one and report the phase substantially complete. **Requirement 3 is stated as "a consumer, or the deletion" precisely to make that outcome fail** — a documented surface with three unread members is the finding restated, not the finding fixed.
- **Naming a third Kind is a claim against a shipped Phase 2 deliverable, and it should be read as a proposal to the operator throughout.** The argument is in § 1–4 above and it rests on one property. If the operator rules the run log is a *variety of Kind 1 with a machine-local binding* rather than a third kind, **requirements 1–4 are unaffected** — the surface still needs a name, an owner, a growth rule and a reader. Only the label moves.
- **`0feacc3` and `a623c25` are worth reading together before touching the telemetry**, because the second corrects the first on exactly the axis this phase's readers will run over: the sampler was measuring the caller's session scope rather than the child's, and the test that should have caught it asserted only a floor.
- **The livelock produced no evidence, and that was the cost.** A 31 GiB host died under two dispatches and three sessions on 2026-08-10; no OOM report was ever written, because the kernel kept reclaiming ~22 GiB of page cache instead of selecting a victim. Nobody could establish what held the memory. **That is why deletion loses in § 3** — and it is also why the `measured: false` rate is the reader's *first* output rather than a footnote.

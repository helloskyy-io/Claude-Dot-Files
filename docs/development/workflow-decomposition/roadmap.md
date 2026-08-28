# Workflow Decomposition — Roadmap

**Status: 🟡 IN PROGRESS.** Phases 1 and [2](phase2_family_alignment.md) are complete, and five more are planned. **Phases are listed in logical rollout order. Phase numbers are creation-order identifiers and do not reflect rollout sequence; execution order across components lives in [`sprint.md`](../sprint.md).**

**This roadmap was written after Phase 1 shipped.** The component ran for eleven days on a burn-test triage list — since deleted, its two orphaned rulings salvaged into [`cpi-decisions.md`](../cpi-decisions.md) (2026-08-17) — with no roadmap, no phase docs and an empty research pool. Phase 1's boxes below are therefore a **record of what was built**, not requirements it was built against.

**Phases 2–5 were decomposed on 2026-08-18 from [`research/synthesis.md`](research/synthesis.md), and corrected on 2026-08-19 against two operator rulings.** What used to be a single four-box phase is now three phases — 3, 4 and 5 — because its four boxes deliver separate things on separate surfaces. Every original checkbox line is carried below, unchanged, under the phase that now owns it: a completion criterion is not reworded by the run that plans against it, so where a box's wording is wrong or its cross-reference has moved, the correction sits in prose beside it rather than in the box.

**Revised on 2026-08-28 by a design pass over the three unbuilt phases. The phase list DID change this time, in two places, and each has a reason it can state:**

- **[Phase 4](phase4_nothing_invisible.md) was SPLIT and its produced half is now [Phase 6](phase6_every_producer_names_its_consumer.md).** Its outcome could only be stated with the word *and* — *a wrong derivation is visible before it costs anything* **and** *a producer with no consumer turns the suite red* — so whichever half finished first could not be shown as finished. **Two independent passes reached this**, one of them cold, and the merge's original premise (*"neither carried enough work to be its own document"*) stopped being true when the produced half gained a ratified definition anchor and a named on-disk population. Filed as [`C-v4k9pz2h`](../../../tracked/candidates/C-v4k9pz2h.md).
- **Phase 7 — *Managed configuration, and whose tier wins* — was ADDED as a roadmap entry with no phase doc.** The managed/user configuration tier is this component's to build (operator ruling, 2026-08-19) and [Phase 5](phase5_configuration_a_run_absorbed.md) deliberately declines to build it — but the roadmap also claims *"when these phases close, decomposition is done"*, which cannot both be true. The successor now has an entry with its gate named. Filed as [`C-mq7v3z8k`](../../../tracked/candidates/C-mq7v3z8k.md).

**What changed underneath this plan in the interval:** the **four tracked stores** landed on 2026-08-26 ([`tracked/issues/`](../../../tracked/issues/), [`tracked/operations/`](../../../tracked/operations/), [`tracked/candidates/`](../../../tracked/candidates/), [`tracked/standards/`](../../../tracked/standards/), under the [Tracked Items Standard](../../standards/documentation/tracked_items_standard.md)), which gave [Phase 6](phase6_every_producer_names_its_consumer.md) a first-party definition it previously had to invent and gave deferrals a surface that outlives the phase deferring them.

**No completed checkbox was ticked, untucked or removed, and no box was reworded except one** — [Phase 4](phase4_nothing_invisible.md)'s two-clause demonstration box, which is a conjunction the split had to separate. **It is quoted in full where it was split**, so the original wording remains readable. Measurements dated August 2026 that cite surfaces since changed are left standing where they are records; where one is load-bearing and stale, it is corrected in place with the date of the re-measurement.

---

## In plain words

A workflow used to be one long script that did everything. If it failed at step nine, you started again at step one. If two workflows needed the same instruction, you copied it.

This component takes them apart. A **parent** decides what happens next; a **child** does one job. Each boundary between them is a place work can be reviewed, retried, or resumed — and children can be recombined instead of copied.

Two things follow from that, and they are the second half of the work: children in the same family must not drift apart, and a child should work the same whether a human runs it or a parent does.

A third thing follows that is easy to miss. Once a workflow can be started by a human *or* by a parent, **what it does depends on things nobody typed** — the directory it was started from, the path it was pointed at, the configuration files sitting on that machine. Those are derived values, and a wrong one does not crash: it produces a competent run of the wrong work. Making every one of them visible is the rest of this component.

---

## What this component owns

- **The parent/child split** — which workflows are parents, which are children, and where the boundary falls
- **The composition contract** — what a parent may do, what a child must return
- **Family alignment** — how children that share a job stay aligned, and where they are allowed to differ
- **The invocation contract** — how a workflow learns what to do from how it was called, and how it says so out loud
- **What a run writes for somebody else** — the rule that a produced surface names the thing that reads it, and the gate that holds it
- **The record of what a run absorbed** — the digest of the configuration a dispatch ran under, written into that run's own bag

**It does not own:** designing or building workflows that do not exist yet — that is [Assistant Workflow Design](../sprint.md), which is the other side of this component's seam: decomposition takes apart what already existed, that one creates what does not. Nor durability or resumption ([Temporal Integration](../temporal-integration/temporal-integration.md)), what a run records ([PMP](../persistent-memory-protocol/roadmap.md)), or making a child better at its job ([Self Improvement](../sprint.md)).

**And it DOES own managed configuration, both halves.** Which tier wins, what a user's own tier may override, and the record of what a dispatch actually absorbed are all this component's — operator ruling, 2026-08-19. The reason it lands here rather than beside other configuration work is the seam, not the subject matter: `run-claude` already refuses to dispatch on an *inherited* model, and agents, skills, rules and hooks are the ambient inputs still outstanding. That is decomposition's own derive-not-inherit seam, finished. [Phase 5](phase5_configuration_a_run_absorbed.md) builds the record first and says why the tier policy waits on it.

---

## Phases

**Phases are listed in logical rollout order, and at creation the numbering was made to match it** — 2 → 3 → 4 → 5. **From here the numbers are IDENTITY, not order**: a number names a phase for life, the way a ticket number does, so a later re-sequencing moves a phase's entry and never its number. Execution order across components lives in [`sprint.md`](../sprint.md).

### Decompose the build families and codify the shape ✅ COMPLETE

Take the monoliths apart, then write down what the shape is.

**THIS PHASE SHOULD CARRY AN ESTIMATE AND DOES NOT. Ruled 2026-08-28; the figure is `plan-verify`'s to write and is deliberately not written here.**

The line this replaces read: *"No estimate, and the absence is deliberate. This phase shipped; its boxes are a record of what was built rather than work to be sized."* **That reason applies word-for-word to [Phase 2](phase2_family_alignment.md)**, which also shipped and which the same pass *did* size — so the stated rule was already not the rule being followed, and a reader could take either half. **A completed phase's cost is part of what the component cost**; it is the *to-do* figure that subtracts a complete phase, and that is derived separately from the total. The counter that reads this roadmap currently reports this phase as unsized, which is accurate and is the defect.

**What this phase contained, so whoever sizes it is not sizing from five checkbox lines:** a structural refactor of the fleet's largest family while that family was running — two monoliths became the six workflow modules under `modules/assistant/build/`, `build-phase` was absorbed as a flag rather than kept as a seventh module, the activities layer was lifted out into what is now `assistant_activities.py`, and the shape was written into [`workflow-scripts.md` § Composition](../../standards/workflow-scripts.md).

Every phase below carries one figure, written by `plan-verify` reading the plan cold. Each is **hours of focused development, not elapsed time**, and each states what it rests on so it can be argued with. **No total is written here** — a total is derived from the parts, and a derived figure restated where nothing derives it goes stale in one direction only.

- [x] Split `build` into draft → refine → review-pr
- [x] Split `build-minor` on the same shape — one-lens middle child
- [x] Absorb `build-phase` into `build --phase` — one family, one set of children
- [x] Extract the activities layer — `run-claude`, `wait-for-ci`, `require-environment`
- [x] Write it down — [`workflow-scripts.md` § Composition](../../standards/workflow-scripts.md)

### Family alignment ✅ COMPLETE

**Implementation:** [`phase2_family_alignment.md`](phase2_family_alignment.md)

*Children in a family do not diverge except where they need to.*

**Est: ~15 hours** *(sized cold by `plan-verify`, 2026-08-19)* — almost none of it is code: the mechanism, the ratchet and the standard's wording all shipped. The cost is a judgement pass over the frozen baseline's rows, grouped into eight consumer-sets, each needing two prompt files read plus the git history behind them; a blind trial that must be sealed before any history is consulted and then scored; and one document that does not exist anywhere today — the `_minor` tier contract, which is C-at80groo's subject.

The mechanism shipped, the ratchet worked, and the baseline is now EMPTY — 48 rows, then 13, then none. The half a test could not decide was ruled per FAMILY rather than per pair, because the blind trial this phase required measured κ = 0.000 between two raters and the phase named that as the trigger to change granularity. The procedure, the rulings and the `_minor` tier contract are in `tests/unit/fork_vs_parameterize.py`; the trial is in [`fork_vs_parameterize_blind_trial.md`](fork_vs_parameterize_blind_trial.md).

- [x] The shared-fragment mechanism — a block with two consumers lives in `modules/assistant/prompts/` and is referenced by placeholder
- [x] The duplication ratchet — a frozen baseline that fails on new copying **and** on a fixed entry left behind, so it can only shrink
- [x] The promotion rule extended to prompts, in [`workflow-scripts.md`](../../standards/workflow-scripts.md)
- [x] **Bring the fleet up to the rule** — the measured backlog, largest groups first
- [x] **Rule fork-vs-parameterize** — the half a test cannot judge: a copy that has already drifted reads as intent, not accident
- [x] **Every row in the frozen duplication baseline is either gone or carries a written ruling** — 13 rows on 2026-08-18
- [x] **The ruling method is validated before it is trusted** — classify a sample blind, then reveal the history, and record the disagreement
- [x] **What a `_minor` tier's prompt is FOR is written down where a guard can cite it** — the contract no test can supply

### Dual-mode children 🟠 PLANNED

**Implementation:** [`phase3_dual_mode_children.md`](phase3_dual_mode_children.md)

*Every child runs standalone and under a parent, equally well.*

**Est: ~20 hours** *(sized cold by `plan-verify`, 2026-08-19 — and see the correction below, which the figure has not been re-read against)* — the adapters are the cheap half and the demonstrations are the expensive one. Nine runners written against eleven existing pairs, the five divergences ruled once rather than nine times, and a 53-line naming guard widened from eleven subjects to twenty. Then each of the nine is run alone until it behaves — and this phase's own evidence is that a child takes several fix rounds, which is why the proof outweighs the construction.

> **The measurement that figure was written against is STALE, and it is corrected here rather than left to be re-derived.** The 2026-08-19 note read *"runners run 88–172 lines, shims 13–18"*. **Re-counted on disk 2026-08-28: the eleven runners span 116–372 lines, median ~135; the eleven shims are unchanged at 13–18.** The range moved because `plan_verify` (372) and `triage_candidates` (117) landed in the interval. **The nine adapters this phase writes are modelled on the eleven that exist, so the range is what the work is scoped against** — the figure above predates the correction and is left as its author wrote it. **This phase also gained a requirement (6) after that sizing.**

Twenty workflows exist; **eleven can be started by a person and nine cannot.** The nine are all children, and each one's core function already works — what is missing is the outer half of the shape the other eleven have: a runner that owns the CLI contract, and a thin shim beside it. This phase builds those nine and proves each by running it alone. **It sits this early because it is what makes every later change cheap to iterate on:** a child that can only be exercised through its parent is a child that can only be debugged at parent prices, and these children are not good out of the box.

- [ ] **Every child runs standalone and under a parent, equally well**
- [ ] **`research_refresh_parent` has no entrypoint** — a parent nothing can invoke, found while counting for the box above
- [ ] **The five known divergences are ruled once, not nine times** — verbosity, exit codes, interactive prompts, stream discipline, working directory
- [ ] **The shim-naming guard covers all twenty**, extended in the same change that adds the nine
- [ ] **Each of the nine is demonstrated running alone**, end to end — constructing a runner is not the deliverable
- [ ] **The nine are ruled as ONE family, once, before the first is written** — [Phase 2](phase2_family_alignment.md)'s per-pair procedure measured κ = 0.000 and per-family is the granularity that replaced it; nine rulings after the fact is the failure
- [ ] **The mechanism the nine share is EXTRACTED before they are written, not detected afterwards** — no guard in this repo can see duplication in a Python runner, so there is nothing to detect it with

*The last two boxes are new on 2026-08-28 and they are the only boxes this component gained.* The first carries what [`sprint.md`](../sprint.md) already recorded that Phase 3 inherits from [Phase 2](phase2_family_alignment.md) — a ruling procedure demoted to advisory after scoring κ = 0.000 against the field's 0.271 benchmark — and which this phase's doc never named. **The second exists because this phase's own notes call nine adapters from one template *"a copying event waiting to happen"* while its implementation step points at a guard that structurally cannot fire on them:** the duplication ratchet's population is `ASSISTANT.rglob("prompts/*.md")` (verified 2026-08-28 at `tests/unit/test_prompt_blocks_are_shared_not_copied.py:137`), so a Python file under `scripts/` cannot add a row to it and cannot turn it red. **It has already happened at seven** — [`C-8tv8ewto`](../../../tracked/candidates/C-8tv8ewto.md) records seven runners carrying a byte-identical failure block, found by a review agent with the ratchet green throughout. Detection is not available here; **sharing the mechanism first is.** Filed as [`C-7q2m4xzb`](../../../tracked/candidates/C-7q2m4xzb.md); the ruling and what was rejected are in [`phase3_dual_mode_children.md`](phase3_dual_mode_children.md) § *The runner corpus has no duplication guard*.

*Two notes on the second box, kept out of its text because a planning run does not reword a completion criterion.* **“The box above”** in it means the managed-config box, which now lives at [Phase 5](phase5_configuration_a_run_absorbed.md). And its premise is **wrong as measured**: `research_refresh_parent` *is* invocable — `run_research.py --refresh` and `research.sh <dir> --refresh` both reach it (verified 2026-08-19 at `scripts/workflows/temporal/scripts/run_research.py:10,70`). The real defect is narrower: it has no entrypoint **of its own**, no `research_refresh.sh` beside the other shims. A run that decomposes the box as written will scope the wrong fix. Source: [`research/raw/invocation_contract.md`](research/raw/invocation_contract.md) §5.1.

### Nothing a run relies on is invisible 🟠 PLANNED

**Implementation:** [`phase4_nothing_invisible.md`](phase4_nothing_invisible.md)

*A wrong flag fails at parse time; a wrong derivation runs competently against the wrong thing, and a surface nobody reads never goes red at all.*

**NOT SIZED. The 2026-08-19 figure of ~24 hours was written against a phase that no longer exists and has been removed rather than left to mislead** — it covered both halves, and the produced half is now [Phase 6](phase6_every_producer_names_its_consumer.md). Both halves need reading cold by `plan-verify`; neither figure is written by the pass that split them.

A run depends on two classes of thing it never announces: what it worked out for itself, and what it wrote for somebody else. **This phase is the first of those, and [Phase 6](phase6_every_producer_names_its_consumer.md) is the second.** Derived values — the repo root, the component under plan — already anchor on real markers and already have an override, but nothing publishes how they are derived, nothing echoes them on the live path, and nothing states what breaks when one is wrong. This phase finishes that defence and proves it the way the whole component proves things: make the system say the wrong thing out loud, before it costs anything.

- [ ] **`plan-project` derives feature scope from its target** — feature scope is the project chain's tail, and a path states it rather than a flag

*A note on the box above, kept out of its text because a planning run does not reword a completion criterion — and it is the same shape as the `research_refresh_parent` note one phase over.* **Its premise is already partly true.** `run_plan_feature.py` takes `component` as a positional path and `run_plan_project.py` derives `research_dir` from a contained path, so scope IS derived from the target rather than from a flag — verified in code 2026-08-19. The paper says so at the top of [`research/raw/invocation_contract.md`](research/raw/invocation_contract.md): *"not 'build derivation'. It is 'finish and harden the derivation that shipped'"*. **A run decomposing this box from the roadmap wording alone will over-scope it.**
- [ ] **Every derived value is published with its marker, its algorithm, its override and its scope of effect** — not recoverable only by reading the call chain
- [ ] **A run echoes what it derived, and a parent can silence the echo without losing the record**
- [ ] **A wrong derivation is demonstrated to be visible** — point a run at the wrong component and watch it say so

*This phase was a merge of two that were planned separately on 2026-08-18 — a derivation audit and a producer/consumer gate — and on 2026-08-28 it was SPLIT back apart, the produced half becoming [Phase 6](phase6_every_producer_names_its_consumer.md). The merge's reason was that neither carried enough work to be its own document; that stopped being true, and the phase could not state its outcome without the word "and".*

***The one reworded box, quoted so the original is not lost.*** *The 2026-08-18 line read:* **“A wrong derivation and an unread producer are both demonstrated to be visible — point a run at the wrong component and watch it say so; add a producer with no consumer and watch the suite go red.”** *It is a conjunction of two demonstrations on two mechanisms, and separating the conjuncts IS the split. Its first clause stays here verbatim; its second is [Phase 6](phase6_every_producer_names_its_consumer.md)'s last box, also verbatim. **No requirement was weakened, added or dropped in the separation** — this is the only box in this roadmap that has been reworded by a planning run, and it is called out rather than done quietly.*

*Three boxes moved to [Phase 6](phase6_every_producer_names_its_consumer.md) unchanged: the gate extension, the producer definition, and the read-off-disk population property.*

### What configuration a run absorbed 🟠 PLANNED

**Implementation:** [`phase5_configuration_a_run_absorbed.md`](phase5_configuration_a_run_absorbed.md)

*A dispatch reads agents, skills, rules and hooks from `~/.claude/`, so an interactive edit silently changes what every later dispatch on that machine does.*

**Est: ~14 hours** *(sized cold by `plan-verify`, 2026-08-19)* — the smallest of the four as scoped, because every surface it touches already exists: the five tags it joins are written in one place in `journal_activities.py`, and the digest's input set is the installer's own symlink targets rather than a tree that has to be classified. The reader is a comparison over two bags with no network and no live filesystem read. The live-CLI measurement against `--setting-sources` and `--safe-mode` is a real cost and is included. **The managed/user tier half of the first box is NOT in this figure** — it is deliberately unbuilt until the record supplies the evidence for it, so it is unsized here rather than estimated.

The smallest thing that fixes the visible half is one digest: record what configuration a run absorbed as a sixth `Journal-` tag in that run's bag, and write the reader that compares two of them. Divergence detection then falls out as a reader over bags that already exist, instead of a drift detector nobody has justified building. **The managed/user tier itself is this component's to build** — the first box below — and it stays open deliberately, because the precedence direction is a policy choice and the digest is what supplies the evidence for it.

- [ ] **Centrally managed config, with a user tier beside it** — agents, skills, rules and hooks are read from `~/.claude/`, so an interactive edit silently changes what every dispatch on that machine does and no two machines can be shown to match. The fleet's set becomes managed; the user keeps a tier they own and can extend. *Gate: PMP Part 1 — if the run bag records the config a run used, the divergence half shrinks to a reader.* **`run-claude` already refuses an inherited model; this is the same seam applied to everything else a dispatch absorbs.**
- [ ] **A run's bag records a digest of the configuration it ran under** — a sixth `Journal-` tag beside the five that exist
- [ ] **A reader answers "did these two runs use the same configuration"** from bags alone
- [ ] **Whether the Managed tier survives `--setting-sources` and `--safe-mode` is MEASURED** — unchecked, and nothing may be designed on it until it is

*Two notes added 2026-08-28.* **The tier half of the first box now has an entry that outlives this phase** — **Phase 7** below, with [`C-mq7v3z8k`](../../../tracked/candidates/C-mq7v3z8k.md) carrying its three sub-decisions. The deferral itself is unchanged and is not reopened; what changed is that a successor named only in the prose of a phase about to be marked complete stops existing when the box is ticked. **And this phase's producer/consumer pair is [Phase 6](phase6_every_producer_names_its_consumer.md)'s named test case rather than its exemplar** — the digest's reader is named but is invoked on demand, with no cadence and no termination, which is a shape the producer definition does not yet rule on either way. Both phase docs previously held this pairing up as the model of doing it right; that was written against a weaker definition and is corrected in each. Filed as [`C-k3nd8vwp`](../../../tracked/candidates/C-k3nd8vwp.md).

*The facts this phase is scoped on were re-read on disk 2026-08-28 and are unchanged: five `Journal-` tags at `modules/journal/journal_activities.py:342-346`, and seven installer symlink targets in `install.sh`.*

### Every producer names its consumer 🟠 PLANNED

**Implementation:** [`phase6_every_producer_names_its_consumer.md`](phase6_every_producer_names_its_consumer.md)

*A surface nobody reads never goes red at all.*

**NOT SIZED — this phase was split out of [Phase 4](phase4_nothing_invisible.md) on 2026-08-28** and the ~24-hour figure that covered both halves has been removed rather than divided. `plan-verify` sizes it cold.

A surface written by one part of the system and read by no other part is not neutral: it costs the run that produces it, it looks like coverage to a reader, and nothing goes red when it stops being correct. That has happened here twice — three parent-written observables shipped with no reader at all, and the directory whose README stated the rule in prose shipped a tool unread anyway. A gate exists for exactly one directory. This phase decides what the rule actually is, rules the fleet's surfaces against it, extends the gate to the ones that qualify, and proves it by breaking it on purpose.

- [ ] **What counts as a producer is defined** — and what is deliberately excluded, by name rather than by omission
- [ ] **Extend the producer-with-no-consumer gate** beyond `scripts/helpers/measure/`
- [ ] **The population is read off disk, never off the table** — the same property that makes the existing gate work
- [ ] **A surface read on demand by a named machine reader is ruled, one way, before the gate is written** — [Phase 5](phase5_configuration_a_run_absorbed.md)'s two-bag reader is the test case, and this plan does not rule it
- [ ] **An unread producer is demonstrated to be visible** — add a producer with no consumer and watch the suite go red

*The first three boxes are carried verbatim from [Phase 4](phase4_nothing_invisible.md), which held them until 2026-08-28. The last box is the second clause of that phase's two-clause demonstration box, quoted in full there. **The fourth box is the only genuinely new criterion**, and it is unchecked with the reason stated: the ruling is an INPUT to this phase that this plan deliberately does not supply, because setting a fleet-wide conformance property from one instance is the kind of decision a build should make with the instance in front of it.*

### Managed configuration, and whose tier wins 🔵 NOT SCHEDULED

*The fleet's configuration becomes managed, and the user keeps a tier they own and can extend.*

**No phase doc, and no checkboxes yet, by design** — a detailed plan for work that cannot start is a guess that ages badly, and `🔵 NOT SCHEDULED` means exactly *no plan exists*. **Gated on three things, all named:** [Phase 5](phase5_configuration_a_run_absorbed.md)'s digest and reader existing, so the design rests on evidence rather than assumption; [Phase 5](phase5_configuration_a_run_absorbed.md)'s requirement 5 measurement of whether Claude Code's own Managed tier survives `--setting-sources` and `--safe-mode`; and an **operator ruling on which direction precedence runs**, which is a policy call no evidence settles.

**This entry exists because the roadmap could not otherwise be true.** [Phase 5](phase5_configuration_a_run_absorbed.md) deliberately builds the record and declines to build the tier — correctly, since the digest is what supplies the evidence the tier design needs. But this roadmap also states that *when these phases close, decomposition is done*, and the tier is this component's to build (operator ruling, 2026-08-19). **Both cannot be true while the tier is named only in the prose of a phase that closes.** The three sub-decisions it will have to make — the precedence direction, what the user tier may override stated as a list, and whether Claude Code's Managed tier is the mechanism at all — are written out in [`C-mq7v3z8k`](../../../tracked/candidates/C-mq7v3z8k.md), which is also where triage rules whether this stays a phase here or becomes something else.

**The trap this entry exists to hold, restated because it is easy to walk into:** the field runs precedence **both ways**. Vendor-package systems (git, npm, systemd) let the *local* tier win; org-policy systems — including Claude Code's own Managed tier — let the managed tier win **unconditionally, with no user override**. [Phase 5](phase5_configuration_a_run_absorbed.md)'s first box promises the first shape. **Reaching for Claude Code's Managed tier because the word matches would silently adopt the second and remove the very tier that box promises the user.** Source: [`research/synthesis.md`](research/synthesis.md) § *Facet 3*.

## The order, and what each part waits on

**Four of the five remaining phases are buildable today; one is gated and says so.** [Phase 3](phase3_dual_mode_children.md) was blocked until 2026-08-19 on a ruling rather than on a system, and that ruling was made. **Phase 7 is the one gate**, and all three of its conditions are named in its entry — two of them are things [Phase 5](phase5_configuration_a_run_absorbed.md) produces, and the third is an operator ruling.

**The order above is 2 → 3 → 4 → 5 → 6 → 7, and two positions in it are arguments.**

**[Phase 3](phase3_dual_mode_children.md) sits first among the unbuilt because it is the *enabler*.** A child with no standalone entrypoint can only be exercised through its parent, and every one of the changes the later phases make has to be exercised on children. **A child earns autonomous operation; it cannot earn anything it cannot be run to demonstrate.**

**[Phase 5](phase5_configuration_a_run_absorbed.md) sits deliberately BEFORE [Phase 6](phase6_every_producer_names_its_consumer.md), and this is the position most worth arguing with.** Phase 6 has to rule whether a surface read *on demand* by a named machine reader is a conformant producer, and Phase 5's digest-and-reader pair is the only instance of that shape anyone has designed. **Whichever of the two lands second discovers the question, and the two discoveries are not equally good.** If Phase 6 lands first, Phase 5 ships a producer its own component's brand-new gate red-flags, and the pressure is to bolt on a cadence nobody asked for — inventing a schedule to satisfy a check is how a gate gets routed around. **If Phase 5 lands first, the instance is in the tree as a required test case when the definition is written**, which is why Phase 6 carries that ruling as an explicit unchecked requirement rather than as an assumption. Ordering alone would not have been enough; the requirement is what makes the order safe. Source: [`C-k3nd8vwp`](../../../tracked/candidates/C-k3nd8vwp.md).

**One coupling worth knowing before either is scheduled:** [Phase 4](phase4_nothing_invisible.md) rules what a run echoes about what it derived and what a parent may silence; [Phase 3](phase3_dual_mode_children.md) creates nine new standalone callers, which are exactly the callers that want that echo loud. Neither blocks the other — but whichever lands first sets the contract, and nine adapters each inventing their own answer is the failure mode.

**A second coupling, in the other direction:** [Phase 4](phase4_nothing_invisible.md)'s echo is itself a producer, so [Phase 6](phase6_every_producer_names_its_consumer.md)'s gate is what should catch it if it is ever removed. That is a reason to build 4 before 6, and it is satisfied by the order above.

**Phase 5's stated gate is already open.** It reads *"PMP Part 1 — if the run bag records the config a run used"*; the run bag shipped with [PMP Phase 1](../persistent-memory-protocol/phase1_the_run_bag.md) and already carries five `Journal-` tags. Adding a sixth is an addition to a mechanism that exists.

The component has a real end: when these phases close — **including Phase 7, which is why it is listed rather than left in prose** — decomposition is done.

**Research:** [`research/`](research/) holds two papers, each with its own destination. [`raw/fork_vs_parameterize_drift_signal.md`](research/raw/fork_vs_parameterize_drift_signal.md) (`Last validated: 2026-08-17`, `Revalidate: high — 6 weeks`, `Critic: PASS-WITH-FIXES`) backs [Phase 2](phase2_family_alignment.md). [`raw/invocation_contract.md`](research/raw/invocation_contract.md) (`Last validated: 2026-08-18`, `Revalidate: high — 4 weeks`, `Critic: PASS-WITH-FIXES`) backs [Phase 3](phase3_dual_mode_children.md), [Phase 4](phase4_nothing_invisible.md), [Phase 5](phase5_configuration_a_run_absorbed.md) and, through Phase 4's split, [Phase 6](phase6_every_producer_names_its_consumer.md). [`synthesis.md`](research/synthesis.md) rolls both up. Neither paper is a ruling on the item it feeds — research is evidence, and a ruling is a separate act, and both of the rulings this plan carries were made by the operator rather than found in a paper.

**One evidence caveat, checked 2026-08-28 and worth stating rather than leaving for a reader to trip on.** Both component papers are inside their revalidation windows. **An upstream paper they lean on is not:** [`claude_code_integration_surface.md`](../../standards/architecture/research/raw/claude_code_integration_surface.md) was due 2026-08-22, and [`synthesis.md`](research/synthesis.md) itself flags that its P13/P12 corroboration must be treated as unverified past that date. **Nothing in this plan rests on it** — P13 is the `--bare` recommendation, which this roadmap already rules *against* adopting on independent grounds, stated below. **[Phase 6](phase6_every_producer_names_its_consumer.md) is the phase least backed by the pool**, and it says so in its own doc: its definition rests on a ratified standard borrowed from elsewhere plus two locally-measured occurrences of one shape, not on a paper.

**Dependencies on other components:**

| This component | Depends on | Which way |
|---|---|---|
| [Phase 5](phase5_configuration_a_run_absorbed.md) | [PMP Phase 1](../persistent-memory-protocol/phase1_the_run_bag.md) — the run bag it adds a tag to | satisfied; PMP Phase 1 is complete |
| [Phase 6](phase6_every_producer_names_its_consumer.md) | [Tracked Items Standard](../../standards/documentation/tracked_items_standard.md) § 0 — the property it borrows as its definition | satisfied; the standard is vendored and ratified. **Read-only: amendments go upstream** |
| Phase 7 | [Phase 5](phase5_configuration_a_run_absorbed.md), twice — its digest evidence and its requirement 5 measurement — plus an operator ruling on precedence direction | **not satisfied**; this is why Phase 7 has no doc |
| [Temporal Integration](../temporal-integration/temporal-integration.md) | this whole component | it is gated on us — porting a shape still being changed means porting it twice |

**No sibling component owns any part of this one.** Managed configuration in particular is ours in full — [Phase 5](phase5_configuration_a_run_absorbed.md) builds the record and Phase 7 is the tier itself.

---

## What is deliberately not built

> **The managed/user configuration TIER used to belong on this list and no longer does.** It is Phase 7 above — deferred with its gate named, not declined. What stays deferred is *building* it before the evidence exists; what changed on 2026-08-28 is that the deferral has an entry instead of a sentence in a phase that closes.

- **A drift detector, a provenance command, or a cross-machine agreement proof.** [Phase 5](phase5_configuration_a_run_absorbed.md) builds one digest, one tag and one reader, and stops. The field ships all three of the others; none is justified until the digest shows what actually diverges. **This is a scope decision, not an assumption about fleet size** — see that phase's § *Why one digest and not the rest*.
- **A god workflow — NOT YET, and deliberately not NEVER.** A single workflow running a long chain unattended is the eventual goal; it is blocked by child performance rather than by design, since human review is currently load-bearing. What has to be true first belongs to [Assistant Workflow Design](../sprint.md), gated on Self Improvement. Decomposition neither builds one nor forbids one.
- **Agents as independently retryable units.** Operator ruling: a Tier-3 agent — independently addressable and independently retryable — is the canonical answer for a **metered API** integration, not for a **subscription-based CLI overlay**. It would need the CLI baked into worker images and a credential per pod. **The accepted trade, stated so nobody re-derives it as a gap:** agents stay inside Claude Code's process model and are therefore not independently retryable, and the parallel-narrow-then-sequential-integration pattern stays enforced by prompt discipline rather than by structure. A known limit, deliberately taken — and it rules out one shape of answer before Assistant Workflow Design's research starts.
- **Retry and resumption inside children** — that is durability, and it belongs to the Temporal port. See its retry-boundary item: `gh()` already carries a bounded retry for transient outages, and nesting that inside an activity retry multiplies attempts.
- **Claude Code's `--bare` flag, despite an upstream paper recommending it for reproducibility.** `--bare` skips hooks — and the `PreToolUse` hook is the only safety control operating during a headless run — and it refuses OAuth/keychain reads, which is the subscription credential this whole edge runs on. The recommendation is correct for an API-keyed worker and does not transfer here. Named so it is not adopted by association. Source: [`research/raw/invocation_contract.md`](research/raw/invocation_contract.md) §4.3.

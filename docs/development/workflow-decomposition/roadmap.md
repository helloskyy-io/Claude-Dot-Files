# Workflow Decomposition — Roadmap

**Status: 🟡 IN PROGRESS.** Two phases are complete and five are planned. **Phases are listed in logical rollout order. Phase numbers are creation-order identifiers and do not reflect rollout sequence; execution order across components lives in [`sprint.md`](../sprint.md).**

**This file states what each phase delivers; it is not the component's history.** Superseded checkbox wordings, the reasoning behind a figure that moved, and the corrections applied to earlier planning passes live in the phase doc that owns them and in `git log`. [Documentation Standard § Development Planning Files](../../standards/documentation/documentation_standard.md) binds this file to *one paragraph per phase*, *3-5 checkboxes per phase* and *keep concise*, and names it *"the file a PM or new team member reads first"*; § *Phase Numbering and Roadmap Ordering* licenses the placement — *"if the breadcrumb is recoverable in under two minutes from `git log` or `git blame`, it does not need to live in the live doc."* **Pruned to that shape on 2026-08-29**, after a cold read measured the file growing 47,318 → 60,759 bytes monotonically across eight planning commits in a single day with no pass net-removing anything — a cost that grows with how often the component is planned rather than with the plan.

**Three entries exceed the 3-5 checkbox ceiling, and each is an exception with a reason rather than drift.** *Family alignment*'s eight are all ticked and a completed box is a record of what was built, never erased. *Dual-mode children*'s seven and *Nothing a run relies on is invisible*'s six each reach one verifiable outcome through more criteria than five; collapsing a pair in either would hide a property a check holds.

**No completed checkbox has ever been ticked, unticked or removed here.** Boxes have been reworded twice, both on an unbuilt phase, both by operator ruling, and both times with the original preserved — the 2026-08-18/19 wordings *Nothing a run relies on is invisible* carried before its re-plan are quoted in full in [`phase4_nothing_invisible.md`](phase4_nothing_invisible.md) § *The wordings this phase's boxes replaced*. **A planning run does not normally reword a completion criterion; a scope change ruled by the operator is the exception.**

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
- **Managed configuration, both halves** — which tier wins, what a user's own tier may override, and the record of what a dispatch actually absorbed (operator ruling, 2026-08-19). It lands here rather than beside other configuration work because of the seam: `run-claude` already refuses to dispatch on an *inherited* model, and agents, skills, rules and hooks are the ambient inputs still outstanding. That is decomposition's own derive-not-inherit seam, finished.

**It does not own:** designing or building workflows that do not exist yet — that is [Assistant Workflow Design](../sprint.md), the other side of this component's seam, since decomposition takes apart what already existed and that one creates what does not. Nor durability or resumption ([Temporal Integration](../temporal-integration/temporal-integration.md)), what a run records ([PMP](../persistent-memory-protocol/roadmap.md)), or making a child better at its job ([Self Improvement](../sprint.md)).

---

## Phases

**Phases are listed in logical rollout order, and at creation the numbering was made to match it.** From here the numbers are IDENTITY, not order: a number names a phase for life, the way a ticket number does, so a re-sequencing moves a phase's entry and never its number. Execution order across components lives in [`sprint.md`](../sprint.md).

### Decompose the build families and codify the shape ✅ COMPLETE

Take the monoliths apart, then write down what the shape is. Two monoliths became the six workflow modules of the fleet's biggest family **while that family was in daily use**, the activities layer was lifted out into what is now `assistant_activities.py`, `build-phase` was absorbed as a flag rather than kept as a seventh module, and the resulting shape was written into a binding standard section.

**Est: ~34 hours** *(sized cold by `plan-verify`, 2026-08-28)* — the largest single unit of work here, and most of the distance from the phases below is the verification cost a refactor performed on a running family carries and a greenfield one does not.

This phase shipped before the component had a roadmap or a research pool, so its boxes are a **record of what was built** rather than requirements it was built against.

- [x] Split `build` into draft → refine → review-pr
- [x] Split `build-minor` on the same shape — one-lens middle child
- [x] Absorb `build-phase` into `build --phase` — one family, one set of children
- [x] Extract the activities layer — `run-claude`, `wait-for-ci`, `require-environment`
- [x] Write it down — [`workflow-scripts.md` § Composition](../../standards/workflow-scripts.md)

### Family alignment ✅ COMPLETE

**Implementation:** [`phase2_family_alignment.md`](phase2_family_alignment.md)

*Children in a family do not diverge except where they need to.* A shared-fragment pool with placeholder rendering, a duplication ratchet that fails in both directions — on new copying and on a fixed entry left behind — and the judgement half a test cannot decide: the fleet brought up to the rule, the baseline taken from 48 rows to 13 to none, and the `_minor` tier contract that existed nowhere before it. The half a test could not decide was ruled per FAMILY rather than per pair, because this phase's own blind trial measured κ = 0.000 between two raters and the phase named that as the trigger to change granularity. The procedure and the rulings are in `tests/unit/fork_vs_parameterize.py`; the trial is in [`fork_vs_parameterize_blind_trial.md`](fork_vs_parameterize_blind_trial.md).

**Est: ~28 hours** *(re-sized cold by `plan-verify`, 2026-08-28)* — the code half is 2,155 lines of test surface across the ratchet and its two complements; the judgement half is 13 baseline rows in 8 consumer-sets, each needing two prompt files and their git history read, plus a blind trial sealed before any history is consulted and scored against a co-evolution audit.

- [x] The shared-fragment mechanism — a block with two consumers lives in `modules/assistant/prompts/` and is referenced by placeholder
- [x] The duplication ratchet — a frozen baseline that fails on new copying **and** on a fixed entry left behind, so it can only shrink
- [x] The promotion rule extended to prompts, in [`workflow-scripts.md`](../../standards/workflow-scripts.md)
- [x] **Bring the fleet up to the rule** — the measured backlog, largest groups first
- [x] **Rule fork-vs-parameterize** — the half a test cannot judge: a copy that has already drifted reads as intent, not accident
- [x] **Every row in the frozen duplication baseline is either gone or carries a written ruling** — 13 rows on 2026-08-18
- [x] **The ruling method is validated before it is trusted** — classify a sample blind, then reveal the history, and record the disagreement
- [x] **What a `_minor` tier's prompt is FOR is written down where a guard can cite it** — the contract no test can supply

### Nothing a run relies on is invisible 🟠 PLANNED

**Implementation:** [`phase4_nothing_invisible.md`](phase4_nothing_invisible.md)

*A wrong flag fails at parse time; a wrong derivation runs competently against the wrong thing.* A run's context — repo root, journal root, workflow key, worktree name, pull-request number, and the target it was pointed at — is computed **once, at the dispatch boundary**, frozen, and passed down, which is [`docs/guide/workflows.md`](../../guide/workflows.md)'s own rule for worktrees (*"isolation is established once by the parent and passed down"*) applied to everything else a run works out for itself. The per-run worktree name is collapsed from eleven inline sites into a field on that object, every field carries what it was derived from and what breaks if it is wrong, and the run says the whole thing out loud before it spends anything.

**Est: ~26 hours** *(re-sized cold by `plan-verify`, 2026-08-29)* — one consolidation with a measured precedent (`base_ref` collapsed a value of the same shape at the same eleven call sites), one object, one echo; the widest line is the tail, where the suite meets eleven changed call sites, a renamed `build-minor` worktree and a new unconditional stderr line at once.

**RE-PLANNED ON 2026-08-28 BY OPERATOR RULING — a scope change, not a rewording.** This phase used to ask for an *audit* of the fleet's derived values, held honest by a check that read its population off the tree. That check ran cold and could not derive a population, and the plan offered two branches: a marker convention across the tree, or the hand-kept list the requirement existed to forbid. **The operator ruled that both are the wrong question — the requirement was an audit tool for a mess, so the mess goes instead.** Derivation should not be enumerated, because it should not happen in eight places. The enumeration is then not a document: it is the object's fields. Reasoning, the deleted fork, and the superseded box wordings are in [`phase4_nothing_invisible.md`](phase4_nothing_invisible.md).

- [ ] **A run's derived values live on ONE frozen object**, constructed once at the dispatch boundary and passed down — repo root, journal root, workflow key, worktree name, PR number, and the component or pool the run targets
- [ ] **Every field on the context states what it is, held by a check** — its marker, its algorithm, its override or none, and what else is wrong if it is wrong, over a population read from `dataclasses.fields()`
- [ ] **No entrypoint and no workflow module assembles a run-scoped derived value for itself**, held by a check — the worktree name is derived once, from the workflow key the object already carries
- [ ] **A run states its context on the live path, before the first side effect** — printed by the run that CONSTRUCTED the context, not by one that was handed it
- [ ] **The rehearsal and the live run print the same object** — `--dry-run` previews what runs, rather than its own assembly of the same values
- [ ] **A wrong derivation is demonstrated to be visible** — point a run at the wrong component and watch it say so

**The second box is new on 2026-08-29 and it closes a way this phase could have gone green while failing its own purpose.** The phase exists to add three of the five safe-derivation properties; two of them — the published algorithm and the stated scope of effect — land as field docstrings, and until this box no requirement checked them and no demonstration exercised them. **The re-plan's own argument supplies the remedy:** the reason the deleted clause was unbuildable is that derivations have no enumerable population, and a frozen dataclass's fields *are* one. Reasoning: [`phase4_nothing_invisible.md`](phase4_nothing_invisible.md) § *Requirement 6 exists because field existence is not field documentation*.

*This phase was a merge of two planned separately on 2026-08-18, and on 2026-08-28 it was SPLIT back apart — the produced half is now [Every producer names its consumer](phase6_every_producer_names_its_consumer.md), which carries three of its boxes verbatim. Filed as [`C-v4k9pz2h`](../../../tracked/candidates/C-v4k9pz2h.md).*

### Dual-mode children 🟠 PLANNED

**Implementation:** [`phase3_dual_mode_children.md`](phase3_dual_mode_children.md)

*Every child runs standalone and under a parent, equally well.* Twenty workflows exist; **eleven can be started by a person and nine cannot.** The nine are all children whose core function already works — what is missing is the outer half of the shape the other eleven have: a runner that owns the CLI contract, and a thin shim beside it. This phase rules the nine as one family, extracts the mechanism they share before writing any of them, builds the nine, widens the shim-naming guard from eleven subjects to twenty, and proves each child by running it alone.

**Est: ~36 hours** *(re-sized cold by `plan-verify`, 2026-08-29)* — the adapters are the cheap half against a re-verified 116–372 line, median-135 corpus, and the demonstrations are the expensive one, priced per child because this phase's own evidence is that a child takes several fix rounds before it behaves. **The figure prices requirement 5's demonstration at the bar requirement 5 itself states — *"the cheapest invocation that reaches real work"* — which [`phase3_dual_mode_children.md`](phase3_dual_mode_children.md) § *Runtime Verification* reads more cheaply as a `--dry-run`. That is the widest single line in this component, and it is unruled rather than settled.**

- [ ] **Every child runs standalone and under a parent, equally well**
- [ ] **`research_refresh_parent` has no entrypoint** — a parent nothing can invoke, found while counting for the box above
- [ ] **The five known divergences are ruled once, not nine times** — verbosity, exit codes, interactive prompts, stream discipline, working directory
- [ ] **The shim-naming guard covers all twenty**, extended in the same change that adds the nine
- [ ] **Each of the nine is demonstrated running alone**, end to end — constructing a runner is not the deliverable
- [ ] **The nine are ruled as ONE family, once, before the first is written** — [Family alignment](phase2_family_alignment.md)'s per-pair procedure measured κ = 0.000 and per-family is the granularity that replaced it; nine rulings after the fact is the failure
- [ ] **The mechanism the nine share is EXTRACTED before they are written, not detected afterwards** — no guard in this repo can see duplication in a Python runner, so there is nothing to detect it with

*Two boxes above are wrong as measured, and are carried verbatim because a planning run does not reword a completion criterion.* **"The box above"** in the second means the managed-config box, which now lives at [What configuration a run absorbed](phase5_configuration_a_run_absorbed.md). And its premise is false: `research_refresh_parent` **is** invocable — `run_research.py --refresh` and `research.sh <dir> --refresh` both reach it (verified 2026-08-19). The real defect is narrower: it has no entrypoint **of its own**, no `research_refresh.sh` beside the other shims. A run that decomposes the box as written will scope the wrong fix. Source: [`research/raw/invocation_contract.md`](research/raw/invocation_contract.md) §5.1. The last two boxes are new on 2026-08-28; the ruling behind them and what was rejected are in [`phase3_dual_mode_children.md`](phase3_dual_mode_children.md) § *The runner corpus has no duplication guard*, filed as [`C-7q2m4xzb`](../../../tracked/candidates/C-7q2m4xzb.md).

### What configuration a run absorbed 🟠 PLANNED

**Implementation:** [`phase5_configuration_a_run_absorbed.md`](phase5_configuration_a_run_absorbed.md)

*A dispatch reads agents, skills, rules and hooks from `~/.claude/`, so an interactive edit silently changes what every later dispatch on that machine does.* The smallest thing that fixes the visible half is one digest: record what configuration a run absorbed as a sixth `Journal-` tag in that run's bag, and write the reader that compares two of them. Divergence detection then falls out as a reader over bags that already exist, instead of a drift detector nobody has justified building. **The managed/user tier itself is this component's to build** — the first box below — and it stays open deliberately, because the precedence direction is a policy choice and the digest is what supplies the evidence for it.

**Est: ~16 hours** *(re-sized cold by `plan-verify`, 2026-08-28)* — the smallest phase with a doc, because every surface it touches already exists; the fiddly part is reading the digest's input set out of the installer's own symlink targets rather than copying it beside them, plus the check that fails when the two disagree.

- [ ] **Centrally managed config, with a user tier beside it** — agents, skills, rules and hooks are read from `~/.claude/`, so an interactive edit silently changes what every dispatch on that machine does and no two machines can be shown to match. The fleet's set becomes managed; the user keeps a tier they own and can extend. *Gate: PMP Part 1 — if the run bag records the config a run used, the divergence half shrinks to a reader.* **`run-claude` already refuses an inherited model; this is the same seam applied to everything else a dispatch absorbs.**
- [ ] **A run's bag records a digest of the configuration it ran under** — a sixth `Journal-` tag beside the five that exist
- [ ] **A reader answers "did these two runs use the same configuration"** from bags alone
- [ ] **Whether the Managed tier survives `--setting-sources` and `--safe-mode` is MEASURED** — unchecked, and nothing may be designed on it until it is

**The fourth box is INDEPENDENT of the first three and should be RUN FIRST.** The Managed-tier measurement shares no code, no surface and no dependency with the digest, and it is the **second of the four gates** on *Managed configuration, and whose tier wins*. Bundled behind the digest, a slip in the digest slips that gate for no reason and a green digest reads as phase-complete. **It stays fourth in this list because the list mirrors the phase doc's requirement order and the instruction is stated here rather than encoded in position** — see [`phase5_configuration_a_run_absorbed.md`](phase5_configuration_a_run_absorbed.md) § *Requirements for completion*, which carries the same instruction beside requirement 5. It was deliberately not split into a phase of its own: it is a live-CLI measurement against two flags with its result already routed before it runs.

*The tier half of the first box has a successor that outlives this phase* — ***Managed configuration, and whose tier wins*** below, with [`C-mq7v3z8k`](../../../tracked/candidates/C-mq7v3z8k.md) carrying its three sub-decisions. *And this phase's digest-and-reader pair is [Every producer names its consumer](phase6_every_producer_names_its_consumer.md)'s named test case rather than its exemplar: the reader is named but invoked on demand, with no cadence and no termination, which is a shape the producer definition does not yet rule on either way. Filed as [`C-k3nd8vwp`](../../../tracked/candidates/C-k3nd8vwp.md).*

### Every producer names its consumer 🟠 PLANNED

**Implementation:** [`phase6_every_producer_names_its_consumer.md`](phase6_every_producer_names_its_consumer.md)

*A surface nobody reads never goes red at all.* A surface written by one part of the system and read by no other is not neutral: it costs the run that produces it, it looks like coverage to a reader, and nothing goes red when it stops being correct. That has happened here twice — three parent-written observables shipped with no reader at all, and the directory whose README stated the rule in prose shipped a tool unread anyway. A gate exists for exactly one directory. This phase decides what the rule actually is, rules the fleet's surfaces against it, extends the gate to the ones that qualify, and proves it by breaking it on purpose in both directions.

**Est: ~23 hours** *(re-sized cold by `plan-verify`, 2026-08-29)* — the definition and the ruling pass are the bulk of it and neither is code; the variance driver is a fleet-wide producer sweep **nobody has counted**, and the figure assumes the ratchet-as-backlog shape this phase's own notes propose rather than a green-before-merge one.

- [ ] **What counts as a producer is defined** — and what is deliberately excluded, by name rather than by omission
- [ ] **Extend the producer-with-no-consumer gate** beyond `scripts/helpers/measure/`
- [ ] **The population is read off disk, never off the table** — the same property that makes the existing gate work
- [ ] **A surface read on demand by a named machine reader is ruled, one way, before the gate is written** — [What configuration a run absorbed](phase5_configuration_a_run_absorbed.md)'s two-bag reader is the test case, and this plan does not rule it
- [ ] **An unread producer is demonstrated to be visible** — add a producer with no consumer and watch the suite go red

*The first three boxes are carried verbatim from [Nothing a run relies on is invisible](phase4_nothing_invisible.md), which held them until 2026-08-28, and the last is the second clause of that phase's two-clause demonstration box.* **The fourth box is the only genuinely new criterion**, and it is unchecked with its reason stated: the ruling is an INPUT to this phase that this plan deliberately does not supply, because setting a fleet-wide conformance property from one instance is a decision a build should make with the instance in front of it. Both branches of that ruling have an owner — requirement 6 in the phase doc — so neither falls between this phase and the closed one beside it.

### Managed configuration, and whose tier wins 🔵 NOT SCHEDULED

*The fleet's configuration becomes managed, and the user keeps a tier they own and can extend.* Three sub-decisions ruled and written down, a managed tier and a user tier beside it, the fleet's own configuration set moved into the managed one, precedence demonstrated in the direction the operator rules, and the safety hook's guard still holding afterwards.

**Est: ~24 hours** *(sized cold by `plan-verify`, 2026-08-28)* — the coarsest figure here because there is no doc to read, and it prices what the work costs **when the gate opens** rather than claiming it can start.

**No phase doc and no checkboxes yet, by design** — a detailed plan for work that cannot start is a guess that ages badly, and `🔵 NOT SCHEDULED` means exactly *no plan exists*. **Gated on four things, all named:** [What configuration a run absorbed](phase5_configuration_a_run_absorbed.md)'s digest and reader existing, so the design rests on evidence rather than assumption; that phase's Managed-tier measurement; an **operator ruling on which direction precedence runs**, which is a policy call no evidence settles; and **a buy-versus-build question nothing in either research pool has answered.**

**The fourth gate opens on a research pass, not on a ruling.** [`problem-statement.md`](../../standards/architecture/problem-statement.md) § *Where we actually differ* item 5 records it in terms — *"whether the tier-policy half is better taken from managed settings **and plugins** than written. No paper in the pool covers this yet."* Plugin marketplaces distribute skills, agents, hooks and MCP servers to a whole team as versioned units through organization settings, which is most of what this phase would otherwise write from scratch. That pass starts from a question the pool has already specified — [`research/synthesis.md`](research/synthesis.md) § *Gaps* test plan **T8**, whether a `managed-settings.d/` drop-in directory exists and merges — but T8 is a starting question rather than the whole gate, since the plugin-marketplace half has no test plan at all.

**The trap this entry exists to hold:** the field runs precedence **both ways**. Vendor-package systems (git, npm, systemd) let the *local* tier win; org-policy systems — including Claude Code's own Managed tier — let the managed tier win **unconditionally, with no user override**. [What configuration a run absorbed](phase5_configuration_a_run_absorbed.md)'s first box promises the first shape, so reaching for Claude Code's Managed tier because the word matches would silently adopt the second and remove the very tier that box promises the user. Source: [`research/synthesis.md`](research/synthesis.md) § *Facet 3*. The three sub-decisions this phase must make are written out in [`C-mq7v3z8k`](../../../tracked/candidates/C-mq7v3z8k.md), which is also where triage rules whether this stays a phase here or becomes something else.

---

## The order, and what each part waits on

**Four of the five remaining phases are buildable today; one is gated and says so.** *Managed configuration, and whose tier wins* is the gate, and all four of its conditions are named in its entry.

**Two positions in the order are arguments rather than preferences.**

**[Nothing a run relies on is invisible](phase4_nothing_invisible.md) sits before [Dual-mode children](phase3_dual_mode_children.md).** That phase adds nine runners, and **nine runners written before the run context exists are nine new members of the eleven-site class the context is collapsing** — this fleet has measured what that costs, since `base_ref`'s docstring records the same consolidation at the same eleven runners, where the first hand sweep of eleven found ten. *Dual-mode children* is the *enabler* and used to sit first for that reason: a child with no standalone entrypoint can only be debugged at parent prices. **The enabler argument survives and is simply outweighed** — *Nothing a run relies on is invisible* needs nothing from the nine, because its own proof runs against `plan-feature`, which exists. **No phase number changed and no file moved**, which is what makes a re-sequencing cheap here.

**[What configuration a run absorbed](phase5_configuration_a_run_absorbed.md) sits before [Every producer names its consumer](phase6_every_producer_names_its_consumer.md), and this is the position most worth arguing with.** *Every producer* has to rule whether a surface read *on demand* by a named machine reader is a conformant producer, and *What configuration a run absorbed*'s digest-and-reader pair is the only instance of that shape anyone has designed. **Whichever lands second discovers the question, and the two discoveries are not equally good.** If *Every producer* lands first, the digest ships as a producer its own component's brand-new gate red-flags, and the pressure is to bolt on a cadence nobody asked for — inventing a schedule to satisfy a check is how a gate gets routed around. If it lands second, the instance is in the tree as a required test case when the definition is written. Ordering alone would not have been enough; *Every producer*'s fourth box is what makes the order safe. Source: [`C-k3nd8vwp`](../../../tracked/candidates/C-k3nd8vwp.md).

**A coupling in the other direction:** [Nothing a run relies on is invisible](phase4_nothing_invisible.md)'s echo is itself a producer, so [Every producer names its consumer](phase6_every_producer_names_its_consumer.md)'s gate is what should catch it if it is ever removed — satisfied by the order above.

***What configuration a run absorbed*'s stated gate is already open.** It reads *"PMP Part 1 — if the run bag records the config a run used"*; the run bag shipped with PMP's [The journal root and the run bag](../persistent-memory-protocol/phase1_the_run_bag.md) and already carries five `Journal-` tags. Adding a sixth is an addition to a mechanism that exists.

The component has a real end: when these phases close — **including *Managed configuration, and whose tier wins*, which is why it is listed rather than left in prose** — decomposition is done.

**Research:** [`research/`](research/) holds two papers. [`raw/fork_vs_parameterize_drift_signal.md`](research/raw/fork_vs_parameterize_drift_signal.md) (`Last validated: 2026-08-17`, `Revalidate: high — 6 weeks`, `Critic: PASS-WITH-FIXES`) backs [Family alignment](phase2_family_alignment.md). [`raw/invocation_contract.md`](research/raw/invocation_contract.md) (`Last validated: 2026-08-18`, `Revalidate: high — 4 weeks`, `Critic: PASS-WITH-FIXES`) backs the other four planned phases. [`synthesis.md`](research/synthesis.md) rolls both up. **Neither paper is a ruling on the item it feeds** — research is evidence, and both of the rulings this plan carries were made by the operator rather than found in a paper.

**One evidence caveat.** Both component papers are inside their revalidation windows. An upstream paper they lean on is not: [`claude_code_integration_surface.md`](../../standards/architecture/research/raw/claude_code_integration_surface.md) was due 2026-08-22, and [`synthesis.md`](research/synthesis.md) flags that its P13/P12 corroboration must be treated as unverified past that date. **Nothing in this plan rests on it** — P13 is the `--bare` recommendation this roadmap already rules *against* adopting on independent grounds, below. **[Every producer names its consumer](phase6_every_producer_names_its_consumer.md) is the phase least backed by the pool**, and it says so in its own doc: its definition rests on a ratified standard borrowed from elsewhere plus two locally-measured occurrences of one shape, not on a paper.

**Dependencies on other components:**

| This component | Depends on | Which way |
|---|---|---|
| [What configuration a run absorbed](phase5_configuration_a_run_absorbed.md) | PMP's [The journal root and the run bag](../persistent-memory-protocol/phase1_the_run_bag.md) — the run bag it adds a tag to | satisfied; that phase is complete |
| [Every producer names its consumer](phase6_every_producer_names_its_consumer.md) | [Tracked Items Standard](../../standards/documentation/tracked_items_standard.md) § 0 — the property it borrows as its definition | satisfied; the standard is vendored and ratified. **Read-only: amendments go upstream** |
| *Managed configuration, and whose tier wins* | [What configuration a run absorbed](phase5_configuration_a_run_absorbed.md), twice — its digest evidence and its Managed-tier measurement — plus an operator ruling on precedence direction, plus the unresearched buy-versus-build question | **not satisfied**; this is why it has no doc |
| [Temporal Integration](../temporal-integration/temporal-integration.md) | this whole component | it is gated on us — porting a shape still being changed means porting it twice |

**No sibling component owns any part of this one.** Managed configuration in particular is ours in full — [What configuration a run absorbed](phase5_configuration_a_run_absorbed.md) builds the record and *Managed configuration, and whose tier wins* is the tier itself.

---

## What is deliberately not built

> **The managed/user configuration TIER used to belong on this list and no longer does.** It is *Managed configuration, and whose tier wins* above — deferred with its gate named, not declined. What stays deferred is *building* it before the evidence exists.

- **A drift detector, a provenance command, or a cross-machine agreement proof.** [What configuration a run absorbed](phase5_configuration_a_run_absorbed.md) builds one digest, one tag and one reader, and stops. The field ships all three of the others; none is justified until the digest shows what actually diverges. **This is a scope decision, not an assumption about fleet size** — see that phase's § *Why one digest and not the rest*.
- **A god workflow — NOT YET, and deliberately not NEVER.** A single workflow running a long chain unattended is the eventual goal; it is blocked by child performance rather than by design, since human review is currently load-bearing. What has to be true first belongs to [Assistant Workflow Design](../sprint.md), gated on Self Improvement. Decomposition neither builds one nor forbids one.
- **Agents as independently retryable units.** Operator ruling: a Tier-3 agent — independently addressable and independently retryable — is the canonical answer for a **metered API** integration, not for a **subscription-based CLI overlay**. It would need the CLI baked into worker images and a credential per pod. **The accepted trade, stated so nobody re-derives it as a gap:** agents stay inside Claude Code's process model and are therefore not independently retryable, and the parallel-narrow-then-sequential-integration pattern stays enforced by prompt discipline rather than by structure.
- **Retry and resumption inside children** — that is durability, and it belongs to the Temporal port. See its retry-boundary item: `gh()` already carries a bounded retry for transient outages, and nesting that inside an activity retry multiplies attempts.
- **Claude Code's `--bare` flag, despite an upstream paper recommending it for reproducibility.** `--bare` skips hooks — and the `PreToolUse` hook is the only safety control operating during a headless run — and it refuses OAuth/keychain reads, which is the subscription credential this whole edge runs on. The recommendation is correct for an API-keyed worker and does not transfer here. Named so it is not adopted by association. Source: [`research/raw/invocation_contract.md`](research/raw/invocation_contract.md) §4.3.

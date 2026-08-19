# Workflow Decomposition — Roadmap

**Status: 🟡 IN PROGRESS.** Phase 1 is complete, [Phase 2](phase2_family_alignment.md) is live, and three more are planned. **Phases are listed in logical rollout order. Phase numbers are creation-order identifiers and do not reflect rollout sequence; execution order across components lives in [`sprint.md`](../sprint.md).**

**This roadmap was written after Phase 1 shipped.** The component ran for eleven days on a burn-test triage list — since deleted, its two orphaned rulings salvaged into [`cpi-decisions.md`](../cpi-decisions.md) (2026-08-17) — with no roadmap, no phase docs and an empty research pool. Phase 1's boxes below are therefore a **record of what was built**, not requirements it was built against.

**Phases 2–5 were decomposed on 2026-08-18 from [`research/synthesis.md`](research/synthesis.md), and corrected on 2026-08-19 against two operator rulings.** What used to be a single four-box phase is now three phases — 3, 4 and 5 — because its four boxes deliver separate things on separate surfaces. Every original checkbox line is carried below, unchanged, under the phase that now owns it: a completion criterion is not reworded by the run that plans against it, so where a box's wording is wrong or its cross-reference has moved, the correction sits in prose beside it rather than in the box.

**Two numbering facts a reader needs before scanning the list.** [Phase 4](#phase-4--retired-and-the-number-is-not-reused) is **retired** and is not reused. And the 2026-08-18 decomposition briefly assigned Phase 4 to new work; that was corrected here, and what it planned is now merged into [Phase 4](phase4_nothing_invisible.md).

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
- **The record of what a run absorbed** — the digest of the configuration a dispatch ran under, written into that run's own bag

**It does not own:** designing or building workflows that do not exist yet — that is [Assistant Workflow Design](../sprint.md), which is the other side of this component's seam: decomposition takes apart what already existed, that one creates what does not. Nor durability or resumption ([Temporal Integration](../temporal-integration/temporal-integration.md)), what a run records ([PMP](../persistent-memory-protocol/roadmap.md)), or making a child better at its job ([Self Improvement](../sprint.md)).

**And it DOES own managed configuration, both halves.** Which tier wins, what a user's own tier may override, and the record of what a dispatch actually absorbed are all this component's — operator ruling, 2026-08-19. The reason it lands here rather than beside other configuration work is the seam, not the subject matter: `run-claude` already refuses to dispatch on an *inherited* model, and agents, skills, rules and hooks are the ambient inputs still outstanding. That is decomposition's own derive-not-inherit seam, finished. [Phase 5](phase5_configuration_a_run_absorbed.md) builds the record first and says why the tier policy waits on it.

---

## Phases

**Phases are listed in logical rollout order, and at creation the numbering was made to match it** — 2 → 3 → 4 → 5. **From here the numbers are IDENTITY, not order**: a number names a phase for life, the way a ticket number does, so a later re-sequencing moves a phase's entry and never its number. Execution order across components lives in [`sprint.md`](../sprint.md).

### Phase 1 — Decompose the build families and codify the shape ✅ COMPLETE

Take the monoliths apart, then write down what the shape is.

**No estimate, and the absence is deliberate.** This phase shipped; its boxes are a record of what was built rather than work to be sized. Every phase below carries one figure, written by `plan-verify` reading the plan cold on 2026-08-19. Each is **hours of focused development, not elapsed time**, and each states what it rests on so it can be argued with. **No total is written here** — a total is derived from the parts, and a derived figure restated where nothing derives it goes stale in one direction only.

- [x] Split `build` into draft → refine → review-pr
- [x] Split `build-minor` on the same shape — one-lens middle child
- [x] Absorb `build-phase` into `build --phase` — one family, one set of children
- [x] Extract the activities layer — `run-claude`, `wait-for-ci`, `require-environment`
- [x] Write it down — [`workflow-scripts.md` § Composition](../../standards/workflow-scripts.md)

### [Phase 2 — Family alignment](phase2_family_alignment.md) 🟡 IN PROGRESS

*Children in a family do not diverge except where they need to.*

**Est: ~15 hours** *(sized cold by `plan-verify`, 2026-08-19)* — almost none of it is code: the mechanism, the ratchet and the standard's wording all shipped. The cost is a judgement pass over the frozen baseline's rows, grouped into eight consumer-sets, each needing two prompt files read plus the git history behind them; a blind trial that must be sealed before any history is consulted and then scored; and one document that does not exist anywhere today — the `_minor` tier contract, which is C-110's subject.

The mechanism shipped and the ratchet works — the duplication baseline fell from 48 rows to 13. What is left is the half a test was never able to decide: whether a pair that has already drifted drifted *on purpose*. This phase ends when no row in that baseline is unruled, and when the reasoning behind each ruling is written where the next reader finds it.

- [x] The shared-fragment mechanism — a block with two consumers lives in `modules/assistant/prompts/` and is referenced by placeholder
- [x] The duplication ratchet — a frozen baseline that fails on new copying **and** on a fixed entry left behind, so it can only shrink
- [x] The promotion rule extended to prompts, in [`workflow-scripts.md`](../../standards/workflow-scripts.md)
- [ ] **Bring the fleet up to the rule** — the measured backlog, largest groups first
- [ ] **Rule fork-vs-parameterize** — the half a test cannot judge: a copy that has already drifted reads as intent, not accident
- [ ] **Every row in the frozen duplication baseline is either gone or carries a written ruling** — 13 rows on 2026-08-18
- [ ] **The ruling method is validated before it is trusted** — classify a sample blind, then reveal the history, and record the disagreement
- [ ] **What a `_minor` tier's prompt is FOR is written down where a guard can cite it** — the contract no test can supply

### [Phase 3 — Dual-mode children](phase3_dual_mode_children.md) ⬜

*Every child runs standalone and under a parent, equally well.*

**Est: ~20 hours** *(sized cold by `plan-verify`, 2026-08-19)* — the adapters are the cheap half and the demonstrations are the expensive one. Nine runners written against eleven existing pairs (measured on disk: runners run 88–172 lines, shims 13–18), the five divergences ruled once rather than nine times, and a 53-line naming guard widened from eleven subjects to twenty. Then each of the nine is run alone until it behaves — and this phase's own evidence is that a child takes several fix rounds, which is why the proof outweighs the construction.

Twenty workflows exist; **eleven can be started by a person and nine cannot.** The nine are all children, and each one's core function already works — what is missing is the outer half of the shape the other eleven have: a runner that owns the CLI contract, and a thin shim beside it. This phase builds those nine and proves each by running it alone. **It sits this early because it is what makes every later change cheap to iterate on:** a child that can only be exercised through its parent is a child that can only be debugged at parent prices, and these children are not good out of the box.

- [ ] **Every child runs standalone and under a parent, equally well**
- [ ] **`research_refresh_parent` has no entrypoint** — a parent nothing can invoke, found while counting for the box above
- [ ] **The five known divergences are ruled once, not nine times** — verbosity, exit codes, interactive prompts, stream discipline, working directory
- [ ] **The shim-naming guard covers all twenty**, extended in the same change that adds the nine
- [ ] **Each of the nine is demonstrated running alone**, end to end — constructing a runner is not the deliverable

*Two notes on the second box, kept out of its text because a planning run does not reword a completion criterion.* **“The box above”** in it means the managed-config box, which now lives at [Phase 5](phase5_configuration_a_run_absorbed.md). And its premise is **wrong as measured**: `research_refresh_parent` *is* invocable — `run_research.py --refresh` and `research.sh <dir> --refresh` both reach it (verified 2026-08-19 at `scripts/workflows/temporal/scripts/run_research.py:10,70`). The real defect is narrower: it has no entrypoint **of its own**, no `research_refresh.sh` beside the other shims. A run that decomposes the box as written will scope the wrong fix. Source: [`research/raw/invocation_contract.md`](research/raw/invocation_contract.md) §5.1.

### [Phase 4 — Nothing a run relies on is invisible](phase4_nothing_invisible.md) ⬜

*A wrong flag fails at parse time; a wrong derivation runs competently against the wrong thing, and a surface nobody reads never goes red at all.*

**Est: ~24 hours** *(sized cold by `plan-verify`, 2026-08-19)* — the largest phase here, and the two halves are not alike. The derived half finishes three properties on code that already anchors on a marker and already takes an override, and is bounded by the number of derivation sites. The produced half is not bounded by anything yet: its first deliverable is a definition that does not exist, it has to be ruled across the whole fleet before a line of gate code is safe, and the phase doc says so itself. Sizing note beyond the figure: the produced half is what makes this phase large, and it is the half that could be its own.

A run depends on two classes of thing it never announces: what it worked out for itself, and what it wrote for somebody else. Derived values — the repo root, the component under plan — already anchor on real markers and already have an override, but nothing publishes how they are derived, nothing echoes them on the live path, and nothing states what breaks when one is wrong. Written surfaces have a gate in exactly one directory, built after three parent-written observables shipped with no reader at all. This phase finishes both defences and proves them the same way: make the system say the wrong thing out loud.

- [ ] **`plan-project` derives feature scope from its target** — feature scope is the project chain's tail, and a path states it rather than a flag
- [ ] **Extend the producer-with-no-consumer gate** beyond `scripts/helpers/measure/`
- [ ] **Every derived value is published with its marker, its algorithm, its override and its scope of effect** — not recoverable only by reading the call chain
- [ ] **A run echoes what it derived, and a parent can silence the echo without losing the record**
- [ ] **What counts as a producer is defined** — and what is deliberately excluded, by name rather than by omission
- [ ] **The population is read off disk, never off the table** — the same property that makes the existing gate work
- [ ] **A wrong derivation and an unread producer are both demonstrated to be visible** — point a run at the wrong component and watch it say so; add a producer with no consumer and watch the suite go red

*This phase is a merge of two that were planned separately on 2026-08-18 — a derivation audit and a producer/consumer gate. They share one shape and neither carried enough work to be its own document. **The definition in the fifth box does not exist yet and this plan does not supply it**; it is the phase's weakest point and its own doc says so.*

### [Phase 5 — What configuration a run absorbed](phase5_configuration_a_run_absorbed.md) ⬜

*A dispatch reads agents, skills, rules and hooks from `~/.claude/`, so an interactive edit silently changes what every later dispatch on that machine does.*

**Est: ~14 hours** *(sized cold by `plan-verify`, 2026-08-19)* — the smallest of the four as scoped, because every surface it touches already exists: the five tags it joins are written in one place in `journal_activities.py`, and the digest's input set is the installer's own symlink targets rather than a tree that has to be classified. The reader is a comparison over two bags with no network and no live filesystem read. The live-CLI measurement against `--setting-sources` and `--safe-mode` is a real cost and is included. **The managed/user tier half of the first box is NOT in this figure** — it is deliberately unbuilt until the record supplies the evidence for it, so it is unsized here rather than estimated.

The smallest thing that fixes the visible half is one digest: record what configuration a run absorbed as a sixth `Journal-` tag in that run's bag, and write the reader that compares two of them. Divergence detection then falls out as a reader over bags that already exist, instead of a drift detector nobody has justified building. **The managed/user tier itself is this component's to build** — the first box below — and it stays open deliberately, because the precedence direction is a policy choice and the digest is what supplies the evidence for it.

- [ ] **Centrally managed config, with a user tier beside it** — agents, skills, rules and hooks are read from `~/.claude/`, so an interactive edit silently changes what every dispatch on that machine does and no two machines can be shown to match. The fleet's set becomes managed; the user keeps a tier they own and can extend. *Gate: PMP Part 1 — if the run bag records the config a run used, the divergence half shrinks to a reader.* **`run-claude` already refuses an inherited model; this is the same seam applied to everything else a dispatch absorbs.**
- [ ] **A run's bag records a digest of the configuration it ran under** — a sixth `Journal-` tag beside the five that exist
- [ ] **A reader answers "did these two runs use the same configuration"** from bags alone
- [ ] **Whether the Managed tier survives `--setting-sources` and `--safe-mode` is MEASURED** — unchecked, and nothing may be designed on it until it is

## The order, and what each part waits on

**No phase in this component has an external gate any more.** [Phase 3](phase3_dual_mode_children.md) was blocked until 2026-08-19 on a ruling rather than on a system; that ruling was made, so every phase below is buildable today.

**The order above is 2 → 3 → 4 → 5, and only one position in it is an argument.** [Phase 3](phase3_dual_mode_children.md) sits second because it is the *enabler*: a child with no standalone entrypoint can only be exercised through its parent, and every one of the changes the later phases make has to be exercised on children. **A child earns autonomous operation; it cannot earn anything it cannot be run to demonstrate.** [Phase 4](phase4_nothing_invisible.md) and [Phase 5](phase5_configuration_a_run_absorbed.md) are independent of each other and of everything else, and could swap.

**One coupling worth knowing before either is scheduled:** [Phase 4](phase4_nothing_invisible.md) rules what a run echoes about what it derived and what a parent may silence; [Phase 3](phase3_dual_mode_children.md) creates nine new standalone callers, which are exactly the callers that want that echo loud. Neither blocks the other — but whichever lands first sets the contract, and nine adapters each inventing their own answer is the failure mode.

**Phase 5's stated gate is already open.** It reads *"PMP Part 1 — if the run bag records the config a run used"*; the run bag shipped with [PMP Phase 1](../persistent-memory-protocol/phase1_the_run_bag.md) and already carries five `Journal-` tags. Adding a sixth is an addition to a mechanism that exists.

The component has a real end: when these phases close, decomposition is done.

**Research:** [`research/`](research/) holds two papers, each with its own destination. [`raw/fork_vs_parameterize_drift_signal.md`](research/raw/fork_vs_parameterize_drift_signal.md) (`Last validated: 2026-08-17`, `Revalidate: high — 6 weeks`, `Critic: PASS-WITH-FIXES`) backs [Phase 2](phase2_family_alignment.md). [`raw/invocation_contract.md`](research/raw/invocation_contract.md) (`Last validated: 2026-08-18`, `Revalidate: high — 4 weeks`, `Critic: PASS-WITH-FIXES`) backs [Phase 4](phase4_nothing_invisible.md), [Phase 3](phase3_dual_mode_children.md) and [Phase 5](phase5_configuration_a_run_absorbed.md). [`synthesis.md`](research/synthesis.md) rolls both up. Neither paper is a ruling on the item it feeds — research is evidence, and a ruling is a separate act, and both of the rulings this plan carries were made by the operator rather than found in a paper.

**Dependencies on other components:**

| This component | Depends on | Which way |
|---|---|---|
| [Phase 5](phase5_configuration_a_run_absorbed.md) | [PMP Phase 1](../persistent-memory-protocol/phase1_the_run_bag.md) — the run bag it adds a tag to | satisfied; PMP Phase 1 is complete |
| [Temporal Integration](../temporal-integration/temporal-integration.md) | this whole component | it is gated on us — porting a shape still being changed means porting it twice |

**No sibling component owns any part of this one.** Managed configuration in particular is ours in full — see [Phase 5](phase5_configuration_a_run_absorbed.md).

---

## What is deliberately not built

- **A drift detector, a provenance command, or a cross-machine agreement proof.** [Phase 5](phase5_configuration_a_run_absorbed.md) builds one digest, one tag and one reader, and stops. The field ships all three of the others; none is justified until the digest shows what actually diverges. **This is a scope decision, not an assumption about fleet size** — see that phase's § *Why one digest and not the rest*.
- **A god workflow — NOT YET, and deliberately not NEVER.** A single workflow running a long chain unattended is the eventual goal; it is blocked by child performance rather than by design, since human review is currently load-bearing. What has to be true first belongs to [Assistant Workflow Design](../sprint.md), gated on Self Improvement. Decomposition neither builds one nor forbids one.
- **Agents as independently retryable units.** Operator ruling: a Tier-3 agent — independently addressable and independently retryable — is the canonical answer for a **metered API** integration, not for a **subscription-based CLI overlay**. It would need the CLI baked into worker images and a credential per pod. **The accepted trade, stated so nobody re-derives it as a gap:** agents stay inside Claude Code's process model and are therefore not independently retryable, and the parallel-narrow-then-sequential-integration pattern stays enforced by prompt discipline rather than by structure. A known limit, deliberately taken — and it rules out one shape of answer before Assistant Workflow Design's research starts.
- **Retry and resumption inside children** — that is durability, and it belongs to the Temporal port. See its retry-boundary item: `gh()` already carries a bounded retry for transient outages, and nesting that inside an activity retry multiplies attempts.
- **Claude Code's `--bare` flag, despite an upstream paper recommending it for reproducibility.** `--bare` skips hooks — and the `PreToolUse` hook is the only safety control operating during a headless run — and it refuses OAuth/keychain reads, which is the subscription credential this whole edge runs on. The recommendation is correct for an API-keyed worker and does not transfer here. Named so it is not adopted by association. Source: [`research/raw/invocation_contract.md`](research/raw/invocation_contract.md) §4.3.
